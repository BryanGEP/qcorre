"""Tests del modo demo: el mundo simulado y la app completa sobre él."""

import sys
import time
from pathlib import Path

import pytest
from test_app import settle

from qcorre import cli, i18n
from qcorre.demo import DemoWorld
from qcorre.git import actions
from qcorre.git.graph import layout
from qcorre.git.history import RefKind
from qcorre.git.runner import GitError
from qcorre.git.sensitive import sensitive_files
from qcorre.models import OrphanReason
from qcorre.ui.app import QcorreApp
from qcorre.ui.confirm import ConfirmScreen, InfoScreen, PromptScreen
from qcorre.ui.git_panel import GitPanel
from qcorre.ui.picker import PickerScreen
from qcorre.ui.projects_panel import ProjectsPanel


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


@pytest.fixture
def world(tmp_path: Path) -> DemoWorld:
    return DemoWorld(delay=0, home=tmp_path)


@pytest.fixture
def api(world: DemoWorld) -> Path:
    return world.root / "tienda-api"


def run(world: DemoWorld, path: Path, plan: actions.ActionPlan) -> actions.ActionResult:
    assert plan.blocked is None, plan.blocked
    result = world.execute(path, plan)
    assert result.ok
    return result


# ── El mundo simulado no toca nada real ─────────────────────────


def test_el_modo_demo_no_importa_psutil_ni_ejecuta_git(monkeypatch, tmp_path):
    import subprocess

    def forbidden(*args, **kwargs):
        raise AssertionError("el modo demo no debe ejecutar ningún programa")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    world = DemoWorld(delay=0, home=tmp_path)
    path = world.root / "tienda-api"
    world.scan()
    world.read_status(path)
    world.read_history(path)
    world.read_branches(path)
    world.execute(path, actions.plan_fetch(world.read_status(path)))
    # El módulo de la demo no depende del recolector real de procesos.
    source = Path(sys.modules["qcorre.demo"].__file__).read_text(encoding="utf-8")
    assert "import psutil" not in source and "subprocess" not in source


# ── Procesos ────────────────────────────────────────────────────


def test_el_escenario_muestra_todos_los_casos_del_panel(world):
    snapshot = world.scan()
    assert [p.name for p in snapshot.projects] == ["tienda-api", "tienda-web", "web-personal"]
    by_name = {p.name: p for p in snapshot.projects}
    assert not by_name["web-personal"].has_git and by_name["tienda-api"].has_git

    api_labels = [d.label for d in by_name["tienda-api"].processes]
    assert api_labels == ["postgres", "redis-server", "uvicorn", "celery"]  # por puerto
    celery = by_name["tienda-api"].processes[-1]
    assert set(celery.orphan_reasons) == {OrphanReason.LONG_RUNNING, OrphanReason.PARENT_GONE}
    chain = by_name["tienda-web"].processes[0]
    assert chain.label == "npm run dev → vite" and len(chain.pids) == 3

    assert [d.label for d in snapshot.unassigned] == ["node server.js", "mysqld", "http.server"]
    assert any(d.access_denied for d in snapshot.unassigned)
    assert snapshot.process_count == 9


def test_matar_un_proceso_lo_quita_del_mundo(world):
    uvicorn = next(d for d in world.scan().projects[0].processes if d.label == "uvicorn")
    victims = world.preview(uvicorn)
    assert len(victims) == 2  # el servidor y su proceso hijo
    result = world.kill(victims)
    assert result.closed == 2 and result.failed == 0
    labels = [d.label for d in world.scan().projects[0].processes]
    assert "uvicorn" not in labels and "postgres" in labels


def test_un_proceso_sin_permiso_no_se_deja_matar(world):
    mysqld = next(d for d in world.scan().unassigned if d.label == "mysqld")
    result = world.kill(world.preview(mysqld))
    assert result.closed == 0 and len(result.denied) == 1
    assert any(d.label == "mysqld" for d in world.scan().unassigned)


def test_matar_todo_un_proyecto_lo_deja_listado_sin_procesos(world):
    project = next(p for p in world.scan().projects if p.name == "tienda-api")
    victims = [v for d in project.processes for v in world.preview(d)]
    world.kill(victims)
    emptied = next(p for p in world.scan().projects if p.name == "tienda-api")
    assert emptied.processes == ()


# ── Git: estado inicial ─────────────────────────────────────────


def test_estado_inicial_del_repo_de_trabajo(world, api):
    status = world.read_status(api)
    assert status.branch == "feature/pagos"
    assert (status.ahead, status.behind) == (1, 0)
    assert len(status.changed) == 3 and len(status.new) == 2
    assert [f.path for f in sensitive_files(status.files)] == [".env"]
    assert status.remote_url == "https://github.com/ana/tienda-api.git"
    assert status.has_parent and status.head_subject == "valida montos negativos"
    assert time.time() - status.last_sync > 3600


def test_las_ramas_cubren_todos_los_casos_de_la_vista(world, api):
    branches = world.read_branches(api)
    by_name = {b.name: b for b in branches.local}
    assert branches.local[0].name == "feature/pagos" and branches.local[0].current
    assert (by_name["main"].ahead, by_name["main"].behind) == (0, 0)
    assert by_name["feat/carrito"].gone and by_name["feat/carrito"].can_delete
    assert by_name["experimento"].upstream is None and not by_name["experimento"].merged
    assert [b.full_remote for b in branches.remote_only] == ["origin/feat/buscador"]


def test_el_historial_es_un_grafo_valido_con_merges(world, api):
    history = world.read_history(api)
    position = {c.oid: i for i, c in enumerate(history.commits)}
    for commit in history.commits:
        for parent in commit.parents:
            assert position[parent] > position[commit.oid]  # hijos antes que padres
    assert sum(c.is_merge for c in history.commits) == 2
    head = next(c for c in history.commits if any(r.kind is RefKind.HEAD for r in c.refs))
    assert head.subject == "valida montos negativos"
    kinds = {ref.kind for c in history.commits for ref in c.refs}
    assert {RefKind.HEAD, RefKind.LOCAL, RefKind.REMOTE, RefKind.TAG} <= kinds
    rows = layout(history.commits)
    assert max(len(row.text) for row in rows) >= 5  # hay varias ramas en paralelo


def test_el_segundo_repo_esta_limpio_y_al_dia(world):
    status = world.read_status(world.root / "tienda-web")
    assert status.is_clean and (status.ahead, status.behind) == (0, 0)
    assert len(world.read_history(world.root / "tienda-web").commits) == 5


def test_un_proyecto_sin_repo_da_error_de_git(world):
    with pytest.raises(GitError):
        world.read_status(world.root / "web-personal")


def test_los_datos_salen_en_el_idioma_activo(tmp_path):
    i18n.set_language("en")
    world = DemoWorld(delay=0, home=tmp_path)
    assert world.read_status(world.root / "tienda-api").head_subject == "validate negative amounts"


# ── Git: el mundo responde a las acciones ───────────────────────


def test_commit_y_push(world, api):
    status = world.read_status(api)
    run(world, api, actions.plan_commit(status, "agrega webhooks"))
    after = world.read_status(api)
    assert after.is_clean and after.ahead == 2
    assert after.head_subject == "agrega webhooks"
    assert world.read_history(api).commits[0].subject == "agrega webhooks"

    run(world, api, actions.plan_push(after))
    pushed = world.read_status(api)
    assert (pushed.ahead, pushed.behind) == (0, 0)
    assert pushed.upstream_oid == pushed.short_oid
    assert time.time() - pushed.last_sync < 60
    assert actions.plan_push(pushed).blocked  # ya no hay nada que subir


def test_fetch_descubre_un_commit_ajeno_y_pull_lo_baja(world, api):
    assert world.read_branches(api).local[2].name  # sanity
    run(world, api, actions.plan_fetch(world.read_status(api)))
    main = next(b for b in world.read_branches(api).local if b.name == "main")
    assert (main.ahead, main.behind) == (0, 1)
    assert any(c.subject == "actualiza dependencias" for c in world.read_history(api).commits)
    # Un segundo fetch ya no trae nada nuevo.
    run(world, api, actions.plan_fetch(world.read_status(api)))
    assert next(b for b in world.read_branches(api).local if b.name == "main").behind == 1

    run(world, api, actions.plan_switch(world.read_status(api), main))
    assert world.read_status(api).behind == 1
    result = run(world, api, actions.plan_pull(world.read_status(api)))
    assert world.read_status(api).behind == 0
    assert result.backup is not None  # había cambios sin guardar: se respaldaron


def test_un_pull_sin_novedades_no_deja_respaldo(world):
    web = world.root / "tienda-web"
    result = run(world, web, actions.plan_pull(world.read_status(web)))
    assert result.unchanged and result.backup is None
    assert world.read_backups(web) == []


def test_ramas_crear_seguir_una_remota_y_borrar(world, api):
    status = world.read_status(api)
    run(world, api, actions.plan_new_branch(status, "feat/reembolsos"))
    assert world.read_status(api).branch == "feat/reembolsos"
    assert world.read_status(api).upstream is None

    remote_only = world.read_branches(api).remote_only[0]
    run(world, api, actions.plan_switch(world.read_status(api), remote_only))
    tracked = world.read_status(api)
    assert tracked.branch == "feat/buscador" and tracked.upstream == "origin/feat/buscador"
    assert world.read_branches(api).remote_only == ()

    main = next(b for b in world.read_branches(api).local if b.name == "main")
    run(world, api, actions.plan_switch(world.read_status(api), main))
    old = next(b for b in world.read_branches(api).local if b.name == "feat/carrito")
    assert old.can_delete
    run(world, api, actions.plan_delete_branch(world.read_status(api), old))
    assert "feat/carrito" not in {b.name for b in world.read_branches(api).local}


def test_deshacer_un_commit_y_volver_con_el_respaldo(world, api):
    run(world, api, actions.plan_commit(world.read_status(api), "commit apresurado"))
    committed = world.read_status(api)
    result = run(world, api, actions.plan_undo_commit(committed))
    undone = world.read_status(api)
    assert undone.head_subject == "valida montos negativos"
    assert len(undone.files) == 5 and all(f.staged for f in undone.files)
    assert all(c.subject != "commit apresurado" for c in world.read_history(api).commits)

    (backup,) = world.read_backups(api)
    assert backup.operation == "undo" and backup.branch == "feature/pagos"
    assert backup == result.backup
    run(world, api, actions.plan_restore(undone, backup))
    assert world.read_status(api).head_subject == "commit apresurado"
    assert world.read_history(api).commits[0].subject == "commit apresurado"


def test_descartar_cambios_y_recuperarlos(world, api):
    before = world.read_status(api)
    run(world, api, actions.plan_discard(before))
    discarded = world.read_status(api)
    assert [f.path for f in discarded.files] == ["app/webhooks.py", ".env"]  # los sin seguir
    backup = world.read_backups(api)[0]
    assert backup.changes_ref is not None
    run(world, api, actions.plan_restore(discarded, backup))
    assert world.read_status(api).files == before.files


# ── La app completa sobre el mundo simulado ─────────────────────


def demo_app(world: DemoWorld) -> QcorreApp:
    return QcorreApp(**world.as_kwargs(), refresh_seconds=None)


def select(app: QcorreApp, fragment: str) -> None:
    """Mueve el cursor del panel de proyectos a la fila que contiene ``fragment``."""
    tree = app.query_one(ProjectsPanel).tree
    for line in range(tree.last_line + 1):
        if fragment in str(tree.get_node_at_line(line).label):
            tree.move_cursor_to_line(line)
            return
    raise AssertionError(f"no hay ninguna fila con {fragment!r}")


async def test_la_demo_se_anuncia_en_la_cabecera(world):
    app = demo_app(world)
    async with app.run_test(size=(130, 38)) as pilot:
        await settle(app, pilot)
        status = str(app.query_one("#status").render())
        assert "DEMO" in status and "3 proyectos" in status and "9 procesos" in status


async def test_recorrido_del_gif_de_punta_a_punta(world):
    """El guion de la demo: matar, commit con aviso, push, ramas e historial."""
    app = demo_app(world)
    async with app.run_test(size=(130, 38)) as pilot:
        await settle(app, pilot)

        # 1. Matar el proceso huérfano del proyecto.
        select(app, "celery")
        await pilot.press("k")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press("enter")
        await settle(app, pilot)
        assert "8 procesos" in str(app.query_one("#status").render())
        # El cursor se queda en el mismo proyecto: el panel de git no cambia.
        assert app.query_one(GitPanel).project.name == "tienda-api"

        # 2. Commit: el diálogo avisa del .env y lista los archivos.
        await pilot.press("c")
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen)
        body = str(app.screen.query_one("#dialog-preview").render())
        assert "parece contener secretos" in body and ".env" in body
        await pilot.press(*"agrega webhooks de pagos")
        await pilot.press("enter")
        await settle(app, pilot)
        panel = app.query_one(GitPanel)
        assert panel.status.is_clean and panel.status.ahead == 2

        # 3. Push: el mapa queda al día.
        await pilot.press("p")
        await pilot.pause()
        await pilot.press("enter")
        await settle(app, pilot)
        assert (panel.status.ahead, panel.status.behind) == (0, 0)

        # 4. Ramas: la vista se abre con datos coherentes.
        await pilot.press("b")
        await pilot.pause()
        assert isinstance(app.screen, PickerScreen)
        lines = [str(choice.label) for choice in app.screen.choices]
        assert any("feat/carrito" in line and "ya mergeada" in line for line in lines)
        assert any("origin/feat/buscador" in line for line in lines)
        await pilot.press("escape")
        await settle(app, pilot)

        # 5. Historial: el commit recién hecho arriba del todo.
        await pilot.press("h")
        await settle(app, pilot)
        history = str(panel.query_one("#git-body").render())
        first = history.splitlines()[0]
        assert "agrega webhooks" in first and "HEAD → feature/pagos" in first
        assert len(app.screen_stack) == 1 and app.is_running


async def test_la_ayuda_lista_todos_los_atajos(world):
    app = demo_app(world)
    async with app.run_test(size=(130, 44)) as pilot:
        await settle(app, pilot)
        await pilot.press("question_mark")
        await pilot.pause()
        assert isinstance(app.screen, InfoScreen)
        assert app.screen.query_one("#dialog").border_title == "Ayuda de qcorre"
        text = str(app.screen.query_one("#dialog-body").query_one("Static").render())
        # Cada atajo de la app aparece en la ayuda.
        documented = {line.split()[0] for line in text.splitlines() if line.startswith("  ")}
        bound = {b.key for b in QcorreApp.BINDINGS} - {"question_mark"} | {"?"}
        assert bound <= documented | {"tab", "enter"}
        assert "push forzado" in text
        await pilot.press("escape")
        await pilot.pause()
        assert len(app.screen_stack) == 1
        assert "? ayuda" in str(app.query_one("HintBar").render())


async def test_la_ayuda_en_ingles(world):
    i18n.set_language("en")
    app = demo_app(world)
    async with app.run_test(size=(130, 44)) as pilot:
        await settle(app, pilot)
        await pilot.press("question_mark")
        await pilot.pause()
        text = str(app.screen.query_one("#dialog-body").query_one("Static").render())
        assert "kill the selected process" in text and "Git for the selected project" in text


# ── Diálogos: sin líneas en blanco ni teclas fuera del marco ────


@pytest.mark.parametrize("size", [(90, 24), (116, 36), (160, 50)])
async def test_los_dialogos_no_dejan_hueco_bajo_las_teclas(world, size):
    app = demo_app(world)
    async with app.run_test(size=size) as pilot:
        await settle(app, pilot)
        select(app, "tienda-api")
        await settle(app, pilot)
        for key in ("c", "b", "u", "question_mark", "f"):
            await pilot.press(key)
            await pilot.pause(0.1)
            assert len(app.screen_stack) == 2, key
            dialog = app.screen.query_one("#dialog").region
            keys = app.screen.query_one("#dialog-keys").region
            # Las teclas son la última línea de contenido: debajo solo quedan
            # el margen interior y el borde del diálogo.
            assert dialog.bottom - (keys.y + 1) == 2, (size, key)
            assert dialog.y >= 0 and dialog.bottom <= size[1], (size, key)
            await pilot.press("escape")
            await settle(app, pilot)


# ── Línea de comandos ───────────────────────────────────────────


def test_cli_demo_crea_la_app_con_el_mundo_simulado():
    args = cli.build_parser().parse_args(["--demo"])
    app = cli.build_app(args)
    assert app.demo
    assert app.scanner().process_count == 9


def test_cli_normal_fija_el_proyecto_y_el_umbral_de_huerfanos(tmp_path):
    args = cli.build_parser().parse_args([str(tmp_path), "--orphan-hours", "2.5"])
    app = cli.build_app(args)
    assert not app.demo
    assert app.scanner.long_running_seconds == 2.5 * 3600
    assert app.scanner.pinned == (tmp_path.resolve(),)
    default = cli.build_app(cli.build_parser().parse_args([]))
    assert default.scanner.long_running_seconds == 24 * 3600


@pytest.mark.parametrize("value", ["0", "-3", "muchas"])
def test_cli_rechaza_umbrales_invalidos(value, capsys):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--orphan-hours", value])
    assert "mayor que cero" in capsys.readouterr().err
