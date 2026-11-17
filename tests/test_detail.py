"""Tests del panel de detalle de un proceso."""

import time
from pathlib import Path

import pytest
from test_app import make_app, settle

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
from qcorre.ui.confirm import InfoScreen
from qcorre.ui.detail_view import command_line, detail_body
from qcorre.ui.widgets import HintBar

NOW = time.time()


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


PROJECT = Project(ProjectRoot(Path("/home/ana/code/devdeck"), has_git=True), ())


def mystery(**kwargs) -> DevProcess:
    """Un "python -c" como los que no se podían identificar."""
    launcher = ProcessInfo(
        pid=7500,
        name="python.exe",
        cmdline=("C:\\proj\\.venv\\Scripts\\python.exe", "-c", "import time; time.sleep(120)"),
        cwd="C:\\proj",
        create_time=NOW - 90,
        ppid=22268,
    )
    real = ProcessInfo(
        pid=33924,
        name="python.exe",
        cmdline=("C:\\Python312\\python.exe", "-c", "import time; time.sleep(120)"),
        cwd="C:\\proj",
        create_time=NOW - 89,
        ppid=7500,
    )
    defaults = dict(
        info=launcher,
        kind=ProcessKind.TOOL,
        label="python -c",
        pids=(7500, 33924),
        members=(launcher, real),
        orphan_reasons=(OrphanReason.PARENT_GONE,),
    )
    return DevProcess(**{**defaults, **kwargs})


def test_command_line_pone_comillas_a_los_argumentos_con_espacios():
    info = ProcessInfo(pid=1, name="python", cmdline=("python", "-c", "import time; x = 1", ""))
    assert command_line(info) == 'python -c "import time; x = 1" ""'
    assert command_line(ProcessInfo(pid=1, name="python")) == ""


def test_el_detalle_muestra_todo_lo_necesario_para_identificar_el_proceso():
    text = detail_body(mystery(), PROJECT, NOW).plain
    assert 'python.exe -c "import time; time.sleep(120)"' in text  # comando completo
    assert "C:\\proj" in text  # carpeta
    assert "devdeck" in text  # proyecto
    assert "7500" in text  # PID
    assert "ya cerró (era el pid 22268)" in text  # padre
    assert "(hace 1m)" in text  # inicio
    assert "sin padre" in text  # por qué es huérfano
    assert "Incluye 2 procesos" in text and "33924" in text


def test_el_detalle_con_padre_vivo_y_puertos():
    process = mystery(parent_name="bash.exe", orphan_reasons=(), ports=(8000, 8001))
    text = detail_body(process, PROJECT, NOW).plain
    assert "bash.exe  (pid 22268)" in text
    assert ":8000 :8001" in text
    assert "Aviso" not in text


def test_el_detalle_de_un_proceso_sin_permiso_no_truena():
    info = ProcessInfo(pid=4321, name="mysqld.exe", access_denied=True)
    process = DevProcess(
        info=info,
        kind=ProcessKind.DATABASE,
        label="mysqld",
        pids=(4321,),
        members=(info,),
        orphan_reasons=(OrphanReason.NO_PROJECT,),
    )
    text = detail_body(process, None, NOW).plain
    assert text.count("sin permiso para leerlo") >= 3  # comando, carpeta, padre, inicio
    assert "sin proyecto" in text
    assert "4321" in text


def test_el_detalle_en_ingles():
    i18n.set_language("en")
    text = detail_body(mystery(), PROJECT, NOW).plain
    assert "Command" in text and "Folder" in text and "Parent" in text and "Started" in text
    assert "already exited (was pid 22268)" in text
    assert "(1m ago)" in text


async def test_enter_sobre_un_proceso_abre_el_detalle_y_esc_lo_cierra():
    snapshot = Snapshot(projects=(Project(PROJECT.root, (mystery(),)),))
    app = make_app(snapshot)
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("down", "enter")
        await pilot.pause()
        assert isinstance(app.screen, InfoScreen)
        assert app.screen.query_one("#dialog").border_title == "python -c"
        body = str(app.screen.query_one("#dialog-body").query_one("Static").render())
        assert "time.sleep(120)" in body
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, InfoScreen)


async def test_enter_sobre_una_cabecera_pliega_el_proyecto_sin_abrir_detalle():
    app = make_app()
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        tree = app.query_one("#tree")
        before = tree.last_line
        await pilot.press("enter")
        await pilot.pause()
        assert not isinstance(app.screen, InfoScreen)
        assert tree.last_line < before


async def test_el_pie_nombra_las_teclas_con_texto_simple():
    app = make_app()
    async with app.run_test(size=(120, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("down")  # un proceso: el pie ofrece ver su detalle
        await pilot.pause()
        hints = " ".join(str(app.query_one(HintBar).render()).split())
        assert "enter detalle" in hints and "k matar" in hints
        assert "⇥" not in hints and "⏎" not in hints
