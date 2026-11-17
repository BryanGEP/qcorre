"""Tests del flujo de las acciones de git en la interfaz, con un ejecutor falso."""

from dataclasses import replace
from pathlib import Path

import pytest
from test_app import sample_snapshot, sample_status, settle

from qcorre import i18n
from qcorre.git.actions import ActionPlan, ActionResult
from qcorre.git.backup import Backup
from qcorre.git.parse import RepoStatus
from qcorre.git.runner import GitResult
from qcorre.ui.app import QcorreApp
from qcorre.ui.confirm import ConfirmScreen, InfoScreen, PromptScreen
from qcorre.ui.widgets import HintBar


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


class FakeExecutor:
    """Registra los planes que se le piden ejecutar; no toca ningún repo."""

    def __init__(self, stderr: str | None = None) -> None:
        self.calls: list[tuple[Path, ActionPlan]] = []
        self.stderr = stderr

    def __call__(self, path: Path, plan: ActionPlan) -> ActionResult:
        self.calls.append((path, plan))
        code = 1 if self.stderr else 0
        steps = tuple(GitResult(args, code, "", self.stderr or "") for args in plan.commands[:1])
        backup = None
        if plan.backup_ref:
            name = plan.backup_ref.rsplit("/", 1)[-1]
            backup = Backup(name, plan.backup_ref + "/rama/main", "a" * 40, "pull", 0.0, "main")
        return ActionResult(plan, steps, backup)


def make_app(executor: FakeExecutor, status: RepoStatus | None = None) -> QcorreApp:
    snapshot = sample_snapshot()
    current = status or sample_status()
    return QcorreApp(
        scanner=lambda: snapshot,
        git_reader=lambda path: current,
        git_executor=executor,
        refresh_seconds=None,
    )


def dialog_text(app: QcorreApp) -> str:
    title = app.screen.query_one("#dialog").border_title
    body = app.screen.query_one("#dialog-body").query_one("Static").render()
    return f"{title}\n{body}"


# sample_status está separado del remoto (2 por subir, 1 por bajar); estas
# variantes dejan un solo lado pendiente.
AHEAD = replace(sample_status(), behind=0)
BEHIND = replace(sample_status(), ahead=0)


async def test_c_pide_el_mensaje_y_muestra_el_comando_mientras_se_escribe():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 36)) as pilot:
        await settle(app, pilot)
        await pilot.press("c")
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen)
        text = dialog_text(app)
        assert "Guardar cambios (commit)" in text
        assert "Se guardarán 4 archivos en un commit nuevo" in text
        assert "$ git add -A" in text

        await pilot.press(*"arregla pagos")
        await pilot.pause()
        assert '$ git commit -m "arregla pagos"' in dialog_text(app)
        assert executor.calls == []

        await pilot.press("enter")
        await settle(app, pilot)
        assert not isinstance(app.screen, PromptScreen)
        (path, plan), = executor.calls
        assert path.name == "tienda-api"
        assert plan.commands == (("add", "-A"), ("commit", "-m", "arregla pagos"))


async def test_commit_sin_mensaje_no_se_ejecuta_y_esc_cancela():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 36)) as pilot:
        await settle(app, pilot)
        await pilot.press("c")
        await pilot.pause()
        await pilot.press("enter")  # mensaje vacío
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen)
        await pilot.press("q", "k")  # letras: se escriben, no disparan atajos
        await pilot.pause()
        assert app.is_running and isinstance(app.screen, PromptScreen)
        await pilot.press("escape")
        await settle(app, pilot)
        assert not isinstance(app.screen, PromptScreen)
        assert executor.calls == []


async def test_p_muestra_la_vista_previa_y_sube_al_confirmar():
    executor = FakeExecutor()
    app = make_app(executor, AHEAD)
    async with app.run_test(size=(120, 36)) as pilot:
        await settle(app, pilot)
        await pilot.press("p")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        text = dialog_text(app)
        assert "Subir cambios (push)" in text
        assert "Se subirán 2 commits a origin/feature/pagos" in text
        assert "Se conecta a la red" in text
        assert "$ git push origin feature/pagos" in text
        assert executor.calls == []
        await pilot.press("enter")
        await settle(app, pilot)
        (_, plan), = executor.calls
        assert plan.commands == (("push", "origin", "feature/pagos"),)


async def test_l_muestra_el_respaldo_antes_de_bajar():
    executor = FakeExecutor()
    app = make_app(executor, BEHIND)
    async with app.run_test(size=(120, 36)) as pilot:
        await settle(app, pilot)
        await pilot.press("l")
        await pilot.pause()
        text = dialog_text(app)
        assert "Bajar cambios (pull)" in text
        assert "Respaldo automático" in text
        assert "refs/qcorre/backup/" in text and "-pull" in text
        assert "$ git pull --ff-only origin feature/pagos" in text
        await pilot.press("enter")
        await settle(app, pilot)
        (_, plan), = executor.calls
        assert plan.backup_ref is not None


async def test_f_avisa_de_la_red_antes_de_actualizar_y_esc_no_conecta():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 36)) as pilot:
        await settle(app, pilot)
        await pilot.press("f")
        await pilot.pause()
        text = dialog_text(app)
        assert "Actualizar del remoto (fetch)" in text
        assert "Se conecta a la red" in text
        assert "$ git fetch --prune origin" in text
        await pilot.press("escape")
        await settle(app, pilot)
        assert executor.calls == []  # sin confirmar no se toca la red

        await pilot.press("f")
        await pilot.pause()
        await pilot.press("enter")
        await settle(app, pilot)
        (_, plan), = executor.calls
        assert plan.commands == (("fetch", "--prune", "origin"),)


async def test_accion_bloqueada_explica_por_que_y_no_ejecuta():
    executor = FakeExecutor()
    app = make_app(executor)  # separado del remoto: ni push ni pull
    async with app.run_test(size=(120, 36)) as pilot:
        await settle(app, pilot)
        await pilot.press("p")
        await pilot.pause()
        assert isinstance(app.screen, InfoScreen)
        assert "Ahora no se puede" in dialog_text(app)
        assert "no has bajado" in dialog_text(app)
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()
        assert "se separaron" in dialog_text(app)
        assert executor.calls == []


async def test_un_fallo_se_explica_con_el_comando_y_el_respaldo():
    executor = FakeExecutor(stderr="fatal: Not possible to fast-forward, aborting.")
    app = make_app(executor, BEHIND)
    async with app.run_test(size=(120, 36)) as pilot:
        await settle(app, pilot)
        await pilot.press("l")
        await pilot.pause()
        await pilot.press("enter")
        await settle(app, pilot)
        assert isinstance(app.screen, InfoScreen)
        text = dialog_text(app)
        assert "No se pudo completar" in text
        assert "se separaron" in text
        assert "$ git pull --ff-only origin feature/pagos" in text
        assert "Not possible to fast-forward" in text
        assert "refs/qcorre/backup/" in text


async def test_tras_una_accion_se_relee_el_repo():
    reads: list[Path] = []
    executor = FakeExecutor()

    def reader(path: Path) -> RepoStatus:
        reads.append(path)
        return AHEAD

    snapshot = sample_snapshot()
    app = QcorreApp(
        scanner=lambda: snapshot, git_reader=reader, git_executor=executor, refresh_seconds=None
    )
    async with app.run_test(size=(120, 36)) as pilot:
        await settle(app, pilot)
        before = len(reads)
        await pilot.press("p")
        await pilot.pause()
        await pilot.press("enter")
        await settle(app, pilot)
        assert len(reads) == before + 1


async def test_sin_repo_seleccionado_las_acciones_no_hacen_nada():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 36)) as pilot:
        await settle(app, pilot)
        await pilot.press("end")  # grupo de huérfanos: no hay repo
        await settle(app, pilot)
        for key in ("c", "p", "l", "f"):
            await pilot.press(key)
            await settle(app, pilot)
            assert len(app.screen_stack) == 1
        assert executor.calls == []


async def test_con_el_panel_de_git_activo_el_pie_muestra_sus_acciones():
    app = make_app(FakeExecutor())
    async with app.run_test(size=(120, 36)) as pilot:
        await settle(app, pilot)
        await pilot.press("2")
        await pilot.pause()
        bar = app.query_one(HintBar)
        line = str(bar.render())
        assert "\n" not in line and bar.size.height == 1
        for hint in ("c commit", "p push", "l pull", "b ramas", "? ayuda", "q salir"):
            assert hint in line
        assert "k matar" not in line  # matar es del panel de proyectos

async def test_commit_de_punta_a_punta_con_git_real(tmp_path, monkeypatch):
    """La app completa contra un repo real: tecla c, mensaje, Enter y hay commit."""
    import os
    import shutil

    if shutil.which("git") is None:
        pytest.skip("git no está instalado")
    from test_git_integration import commit, git, write

    from qcorre.models import Project, ProjectRoot, Snapshot
    from qcorre.ui.git_panel import GitPanel

    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for var in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(var, "Ana")
    for var in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(var, "ana@example.com")

    repo = tmp_path / "mi-proyecto"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    commit(repo, "README.md")
    write(repo, "README.md", "editado\n")
    write(repo, "nuevo.txt")

    snapshot = Snapshot(projects=(Project(ProjectRoot(repo, has_git=True), ()),))
    app = QcorreApp(scanner=lambda: snapshot, refresh_seconds=None)  # git real
    async with app.run_test(size=(120, 36)) as pilot:
        await settle(app, pilot)
        assert len(app.query_one(GitPanel).status.files) == 2
        await pilot.press("c")
        await pilot.pause()
        await pilot.press(*"guarda todo")
        await pilot.press("enter")
        await settle(app, pilot)
        assert len(app.screen_stack) == 1  # sin diálogo de error
        assert app.query_one(GitPanel).status.is_clean
    assert git(repo, "log", "-1", "--format=%s").strip() == "guarda todo"
