"""Tests del panel de git en la interfaz y de su dibujo."""

import time
from pathlib import Path

import pytest
from test_app import HOUR, make_app, sample_snapshot, sample_status, settle
from test_kill_ui import FakeKiller

from qcorre import i18n
from qcorre.collectors.killer import Victim
from qcorre.git.parse import FileChange, RepoStatus
from qcorre.git.runner import GitError
from qcorre.ui.app import QcorreApp
from qcorre.ui.git_panel import GitPanel
from qcorre.ui.git_view import file_list, status_body, sync_map
from qcorre.ui.kill_view import kill_body

NOW = time.time()
OID = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


def panel_text(app: QcorreApp) -> str:
    """Texto visible del panel de git (el cuerpo o el mensaje centrado)."""
    panel = app.query_one(GitPanel)
    scroll = panel.query_one("#git-scroll")
    target = panel.query_one("#git-body") if scroll.display else panel.query_one(".empty")
    return str(target.render())


# ── Dibujo (funciones puras) ────────────────────────────────────


def test_status_body_reune_frases_archivos_y_mapa():
    status = sample_status()
    text = status_body(status, status.last_fetch + 2 * HOUR, width=60).plain
    assert "Estás en la rama feature/pagos" in text
    assert "Tienes 3 archivos con cambios sin guardar en un commit y 1 archivo nuevo." in text
    assert "M  app/pagos.py" in text
    assert "+  app/webhooks.py" in text
    assert "Tu compu y origin se separaron: 2 commits sin subir y 1 commit sin bajar." in text
    assert "Según la última consulta al remoto, hace 2h 00m." in text


def test_el_mapa_muestra_las_dos_cajas_y_las_flechas():
    lines = sync_map(sample_status(), width=60).plain.splitlines()
    assert len(lines) == 4
    assert "Tu compu" in lines[0] and "origin" in lines[0]
    assert lines[1].count("feature/pagos") == 2
    assert "2 ↑" in lines[1] and lines[1].count("►") == 1
    assert "a1b2c3d" in lines[2] and "9f8e7d6" in lines[2]
    assert "1 ↓" in lines[2] and lines[2].count("◄") == 1
    # Las cuatro líneas miden lo mismo: las cajas quedan alineadas.
    assert len({len(line) for line in lines}) == 1


def test_el_mapa_al_dia_no_lleva_numeros():
    status = RepoStatus(
        branch="main", oid=OID, upstream="origin/main", ahead=0, behind=0,
        remotes=("origin",), upstream_oid="a1b2c3d",
    )  # fmt: skip
    plain = sync_map(status).plain
    assert "↑" not in plain and "↓" not in plain
    assert "►" in plain and "◄" in plain


def test_el_mapa_de_una_rama_que_no_esta_en_el_remoto():
    status = RepoStatus(branch="feat/x", oid=OID, remotes=("origin",))
    plain = sync_map(status).plain
    assert "aún no existe" in plain
    assert "►" not in plain and "◄" not in plain


def test_el_mapa_de_una_rama_remota_borrada():
    status = RepoStatus(branch="feat/x", oid=OID, upstream="origin/feat/x", remotes=("origin",))
    assert "ya no existe" in sync_map(status).plain


def test_sin_remoto_no_hay_mapa():
    status = RepoStatus(branch="main", oid=OID)
    assert sync_map(status) is None
    text = status_body(status, NOW).plain
    assert "Este repo no tiene remoto" in text
    assert "╭" not in text


def test_el_mapa_cabe_en_un_panel_angosto():
    status = RepoStatus(
        branch="feature/una-rama-con-un-nombre-larguisimo", oid=OID,
        upstream="origin/feature/una-rama-con-un-nombre-larguisimo", ahead=12, behind=3,
        remotes=("origin",), upstream_oid="9f8e7d6",
    )  # fmt: skip
    for width in (40, 52, 80):
        lines = sync_map(status, width=width).plain.splitlines()
        assert max(len(line) for line in lines) <= width, width
        assert "…" in lines[1]  # el nombre se corta, no desborda


def test_la_lista_de_archivos_se_corta_y_ordena_por_urgencia():
    files = (
        *(FileChange(f"m{i}.py", worktree="M") for i in range(12)),
        FileChange("conflicto.py", "U", "U", conflict=True),
        FileChange("viejo.py", index="R", orig_path="antiguo.py"),
    )
    plain = file_list(files, max_files=5).plain
    lines = plain.splitlines()
    assert lines[0].strip() == "!  conflicto.py"  # lo urgente primero
    assert lines[-1].strip() == "… y 9 más"
    assert "antiguo.py → viejo.py" in file_list(files, max_files=20).plain


# ── Panel dentro de la app ──────────────────────────────────────


async def test_el_panel_muestra_el_estado_del_proyecto_seleccionado():
    app = make_app()
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        panel = app.query_one(GitPanel)
        assert panel.border_title == "tienda-api · feature/pagos"
        text = panel_text(app)
        assert "Estás en la rama feature/pagos" in text
        assert "Tienes 3 archivos con cambios sin guardar en un commit" in text
        assert "Tu compu" in text and "origin" in text
        assert panel.status is not None and panel.status.ahead == 2


async def test_cada_proyecto_muestra_su_propio_repo():
    def reader(path: Path) -> RepoStatus:
        return RepoStatus(branch=f"rama-de-{path.name}", oid=OID)

    base = sample_snapshot()
    # Dos proyectos con git, para comprobar que no se mezclan.
    from qcorre.models import Project, ProjectRoot, Snapshot

    web = Project(ProjectRoot(base.projects[1].path, has_git=True), base.projects[1].processes)
    app = make_app(Snapshot((base.projects[0], web)), git_reader=reader)
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        assert "rama-de-tienda-api" in panel_text(app)
        for _ in range(5):
            await pilot.press("down")
        await settle(app, pilot)
        assert app.query_one(GitPanel).border_title == "tienda-web · rama-de-tienda-web"
        assert "rama-de-tienda-web" in panel_text(app)
        assert "rama-de-tienda-api" not in panel_text(app)


async def test_solo_se_lee_git_al_cambiar_de_proyecto():
    calls: list[Path] = []

    def reader(path: Path) -> RepoStatus:
        calls.append(path)
        return sample_status()

    app = make_app(git_reader=reader)
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        first = len(calls)
        assert first >= 1
        await pilot.press("down", "down")  # se mueve dentro del mismo proyecto
        await settle(app, pilot)
        assert len(calls) == first
        await pilot.press("r")  # un refresco sí relee el repo
        await settle(app, pilot)
        assert len(calls) == first + 1


async def test_proyecto_sin_git_y_grupo_de_huerfanos_no_llaman_a_git():
    calls: list[Path] = []

    def reader(path: Path) -> RepoStatus:
        calls.append(path)
        return sample_status()

    app = make_app(git_reader=reader)
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        for _ in range(5):  # cabecera de tienda-web (sin git)
            await pilot.press("down")
        await settle(app, pilot)
        assert "no es un repositorio git" in panel_text(app)
        await pilot.press("end")
        await settle(app, pilot)
        assert "no pertenecen a ningún proyecto" in panel_text(app)
        assert {path.name for path in calls} == {"tienda-api"}


async def test_un_error_de_git_se_muestra_sin_tronar():
    def broken(path: Path) -> RepoStatus:
        raise GitError("failed", "fatal: not a git repository")

    app = make_app(git_reader=broken)
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        text = panel_text(app)
        assert "Git respondió con un error" in text
        assert "not a git repository" in text
        assert app.is_running


async def test_git_no_instalado():
    def missing(path: Path) -> RepoStatus:
        raise GitError("not_installed")

    app = make_app(git_reader=missing)
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        assert "No encontré git en esta compu" in panel_text(app)


async def test_el_panel_de_git_cambia_de_idioma():
    app = make_app()
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        await pilot.press("i")
        await pilot.pause()
        text = panel_text(app)
        assert "You are on branch feature/pagos" in text
        assert "Your machine" in text


async def test_el_mapa_no_desborda_el_panel():
    app = make_app()
    for size in ((100, 30), (120, 34), (160, 40)):
        async with app.run_test(size=size) as pilot:
            await settle(app, pilot)
            width = app.query_one("#git-scroll").content_size.width
            lines = sync_map(sample_status(), width=width).plain.splitlines()
            assert max(len(line) for line in lines) <= width, size
        app = make_app()


# ── Advertencia de base de datos al matar ───────────────────────


def groups_for(*indexes: int):
    processes = sample_snapshot().projects[0].processes
    return [(processes[i], [Victim(processes[i].pid, "x", 1.0)]) for i in indexes]


def test_matar_una_base_de_datos_avisa():
    plain = kill_body(groups_for(0), windows=True).plain  # postgres
    assert (
        "Es una base de datos: cerrarla a la fuerza puede interrumpir operaciones en curso"
        in plain
    )


def test_matar_varios_dice_cuales_son_bases_de_datos():
    plain = kill_body(groups_for(0, 1), windows=False).plain  # postgres + uvicorn
    assert "Incluye bases de datos (postgres)" in plain
    assert "Es una base de datos" not in plain


def test_sin_bases_de_datos_no_hay_aviso():
    plain = kill_body(groups_for(1), windows=True).plain  # uvicorn
    assert "base de datos" not in plain and "bases de datos" not in plain


async def test_el_dialogo_de_matar_muestra_el_aviso():
    snapshot = sample_snapshot()
    app = QcorreApp(
        scanner=lambda: snapshot, killer=FakeKiller(), git_reader=sample_status,
        refresh_seconds=None,
    )  # fmt: skip
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        await pilot.press("down", "k")  # postgres
        await pilot.pause()
        body = str(app.screen.query_one("#dialog-body").query_one("Static").render())
        assert "Es una base de datos" in body



async def test_proyecto_sin_procesos_se_lista_y_muestra_su_git():
    from qcorre.models import Project, ProjectRoot, Snapshot

    idle = Project(ProjectRoot(Path("/home/ana/code/blog"), has_git=True), ())
    app = make_app(Snapshot(projects=(idle,)))
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        tree = app.query_one("#tree")
        assert tree.display
        assert str(tree.get_node_at_line(0).label) == "blog  nada corriendo"
        assert app.query_one(GitPanel).border_title == "blog · feature/pagos"
        # Sin procesos no hay nada que matar: no debe abrirse ningún diálogo.
        await pilot.press("k")
        await settle(app, pilot)
        assert len(app.screen_stack) == 1
