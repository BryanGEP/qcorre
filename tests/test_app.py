"""Tests de la interfaz sin terminal real (con el Pilot de Textual).

La app recibe un escáner falso que devuelve datos fijos: así no depende de los
procesos que haya en la máquina.
"""

import time
from pathlib import Path

import pytest

from qcorre import i18n
from qcorre.models import (
    DevProcess,
    OrphanReason,
    ProcessInfo,
    ProcessKind,
    Project,
    ProjectRoot,
    Snapshot,
)
from qcorre.ui.app import QcorreApp
from qcorre.ui.projects_panel import ProjectsPanel
from qcorre.git.parse import FileChange, RepoStatus
from qcorre.ui.git_panel import GitPanel
from qcorre.ui.widgets import Header, HintBar

HOUR = 3600.0


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


def dev(pid, label, *ports, age=HOUR, reasons=(), denied=False, kind=ProcessKind.SERVER):
    info = ProcessInfo(
        pid=pid, name=label, create_time=time.time() - age, ppid=1, access_denied=denied
    )
    return DevProcess(
        info=info, kind=kind, label=label, ports=ports, pids=(pid,), orphan_reasons=reasons
    )


def sample_snapshot() -> Snapshot:
    api = Project(
        ProjectRoot(Path("/home/ana/code/tienda-api"), has_git=True),
        (
            dev(1, "postgres", 5432, kind=ProcessKind.DATABASE),
            dev(2, "uvicorn", 8000),
            dev(3, "node server.js", 3000, age=75 * HOUR,
                reasons=(OrphanReason.LONG_RUNNING, OrphanReason.PARENT_GONE)),
        ),
    )  # fmt: skip
    web = Project(
        ProjectRoot(Path("/home/ana/code/tienda-web"), has_git=False),
        (dev(4, "npm run dev → vite", 5173, age=0.7 * HOUR),),
    )
    orphans = (
        dev(5, "http.server", 8888, reasons=(OrphanReason.NO_PROJECT,)),
        dev(6, "mysqld", 3306, reasons=(OrphanReason.NO_PROJECT,), denied=True,
            kind=ProcessKind.DATABASE),
    )  # fmt: skip
    return Snapshot(projects=(api, web), unassigned=orphans)


def sample_status(path=None) -> RepoStatus:
    """Estado de git fijo: los proyectos de prueba no existen en disco."""
    return RepoStatus(
        branch="feature/pagos",
        oid="a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
        upstream="origin/feature/pagos",
        ahead=2,
        behind=1,
        files=(
            FileChange("app/pagos.py", worktree="M"),
            FileChange("app/models.py", index="M"),
            FileChange("tests/test_pagos.py", worktree="M"),
            FileChange("app/webhooks.py", untracked=True),
        ),
        remotes=("origin",),
        upstream_oid="9f8e7d6",
        last_sync=time.time() - 2 * HOUR,
    )


def make_app(snapshot: Snapshot | None = None, git_reader=sample_status) -> QcorreApp:
    snapshot = sample_snapshot() if snapshot is None else snapshot
    return QcorreApp(scanner=lambda: snapshot, git_reader=git_reader, refresh_seconds=None)


async def settle(app: QcorreApp, pilot) -> None:
    """Espera a que terminen los trabajos en segundo plano y se pinte todo.

    Un trabajo puede lanzar otro al terminar (el escaneo relee git), así que
    se repite hasta que no quede ninguno corriendo.
    """
    calm = 0
    for _ in range(40):
        await app.workers.wait_for_complete()
        await pilot.pause()
        await pilot.pause(0.02)
        # Hacen falta dos rondas seguidas sin trabajos: el aviso de que uno
        # terminó (que es lo que lanza el siguiente) puede llegar con retraso.
        calm = 0 if any(worker.is_running for worker in app.workers) else calm + 1
        if calm >= 2:
            break


def tree_lines(app: QcorreApp) -> list[str]:
    tree = app.query_one(ProjectsPanel).tree
    return [str(tree.get_node_at_line(i).label) for i in range(tree.last_line + 1)]


async def test_muestra_los_proyectos_con_sus_procesos():
    app = make_app()
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        assert app.theme == "qcorre"
        lines = tree_lines(app)
        assert lines[0].startswith("tienda-api  3")
        assert lines[1].startswith("● postgres") and ":5432" in lines[1]
        assert lines[2].startswith("● uvicorn") and "1h 00m" in lines[2]
        assert any(line.startswith("tienda-web  1  sin git") for line in lines)
        assert any("npm run dev → vite" in line and ":5173" in line for line in lines)
        assert any(line.startswith("⚠ Huérfanos  2") for line in lines)
        status = str(app.query_one("#status").render())
        assert "2 proyectos" in status and "6 procesos" in status


async def test_huerfano_dentro_del_proyecto_muestra_su_razon():
    app = make_app()
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        lines = tree_lines(app)
        index = next(i for i, line in enumerate(lines) if "node server.js" in line)
        assert lines[index].startswith("⚠ ")
        assert "lleva 3 días" in lines[index + 1]
        assert "su padre ya cerró" in lines[index + 1]
        # La cabecera del proyecto también avisa.
        assert "⚠" in lines[0]


async def test_sin_permiso_se_muestra_sin_tronar():
    app = make_app()
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        lines = tree_lines(app)
        index = next(i for i, line in enumerate(lines) if "mysqld" in line)
        assert lines[index].startswith("○ ")
        assert "sin permiso" in lines[index + 1]


async def test_mover_el_cursor_cambia_el_proyecto_seleccionado():
    app = make_app()
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        git = app.query_one(GitPanel)
        assert git.border_title == "tienda-api · feature/pagos"
        for _ in range(5):  # baja hasta la cabecera de tienda-web
            await pilot.press("down")
        await pilot.pause()
        assert git.border_title == "tienda-web"
        assert "no es un repositorio git" in str(git.query_one(".empty").render())


async def test_el_refresco_conserva_el_cursor():
    snapshots = [sample_snapshot()]
    app = QcorreApp(
        scanner=lambda: snapshots[-1], git_reader=sample_status, refresh_seconds=None
    )
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        panel = app.query_one(ProjectsPanel)
        await pilot.press("down", "down")
        assert panel.selected.process.label == "uvicorn"

        # Aparece un proceso nuevo antes del seleccionado.
        base = sample_snapshot()
        api = base.projects[0]
        grown = Project(api.root, (dev(9, "redis-server", 6379), *api.processes))
        snapshots.append(Snapshot((grown, base.projects[1]), base.unassigned))
        await pilot.press("r")
        await settle(app, pilot)
        assert any("redis-server" in line for line in tree_lines(app))
        assert panel.selected.process.label == "uvicorn"


async def test_estado_vacio():
    app = make_app(Snapshot())
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        panel = app.query_one(ProjectsPanel)
        assert not panel.tree.display
        assert "No hay procesos" in str(panel.query_one(".empty").render())
        assert app.query_one(GitPanel).border_title == "Git"


async def test_un_escaner_que_falla_no_cierra_la_app():
    def broken() -> Snapshot:
        raise RuntimeError("psutil explotó")

    app = QcorreApp(scanner=broken, refresh_seconds=None)
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        assert app.is_running


async def test_tab_cambia_de_panel():
    app = make_app()
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        assert app.focused is app.query_one(ProjectsPanel).tree
        await pilot.press("tab")
        assert app.focused is app.query_one("#git-scroll")


async def test_i_cambia_el_idioma_de_toda_la_interfaz():
    app = make_app()
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("i")
        await pilot.pause()
        assert i18n.get_language() == "en"
        assert app.query_one("#projects").border_title == "Projects"
        assert "quit" in str(app.query_one(HintBar).render())
        assert "2 projects" in str(app.query_one(Header).query_one("#status").render())
        lines = tree_lines(app)
        assert any(line.startswith("⚠ Orphans") for line in lines)
        assert any("running for 3 days" in line for line in lines)
        await pilot.press("i")
        await pilot.pause()
        assert app.query_one("#projects").border_title == "Proyectos"


async def test_q_cierra_la_app():
    app = make_app()
    async with app.run_test() as pilot:
        await pilot.press("q")
    assert not app.is_running
