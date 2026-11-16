"""Tests del flujo "matar procesos" en la interfaz, con un Killer falso."""

import pytest
from test_app import sample_snapshot, settle

from qcorre import i18n
from qcorre.collectors.killer import KillResult, Victim
from qcorre.models import DevProcess, Snapshot
from qcorre.ui.app import QcorreApp
from qcorre.ui.confirm import ConfirmScreen
from qcorre.ui.kill_view import kill_body, result_message


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


class FakeKiller:
    """Registra lo que se le pide y nunca toca procesos reales."""

    def __init__(self, result: KillResult | None = None, gone: set[int] | None = None):
        self.killed: list[list[Victim]] = []
        self.result = result
        self.gone = gone or set()

    def preview(self, process: DevProcess) -> list[Victim]:
        if process.pid in self.gone:
            return []
        # El líder y un hijo, para comprobar que se muestra todo el árbol.
        return [
            Victim(process.pid, process.info.name, 1.0),
            Victim(process.pid + 1000, "hijo.exe", 2.0),
        ]

    def kill(self, victims) -> KillResult:
        self.killed.append(list(victims))
        return self.result or KillResult(closed=len(victims))


def make_app(killer: FakeKiller, snapshot: Snapshot | None = None) -> QcorreApp:
    snapshot = snapshot or sample_snapshot()
    return QcorreApp(scanner=lambda: snapshot, killer=killer, refresh_seconds=None)


def dialog_text(app: QcorreApp) -> str:
    assert isinstance(app.screen, ConfirmScreen)
    body = str(app.screen.query_one("#dialog-body").query_one("Static").render())
    return f"{app.screen.query_one('#dialog').border_title}\n{body}"


async def test_k_pide_confirmacion_y_mata_solo_ese_proceso():
    killer = FakeKiller()
    app = make_app(killer)
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("down", "down")  # uvicorn
        await pilot.press("k")
        await pilot.pause()
        text = dialog_text(app)
        assert "Matar proceso" in text
        assert "Se cerrarán 2 procesos del sistema" in text
        assert "Quedará libre el puerto :8000" in text
        assert "uvicorn" in text and "pid 2" in text and "hijo.exe" in text and "pid 1002" in text
        assert killer.killed == []  # nada se mata antes de confirmar

        await pilot.press("enter")
        await settle(app, pilot)
        assert not isinstance(app.screen, ConfirmScreen)
        assert [[v.pid for v in batch] for batch in killer.killed] == [[2, 1002]]


async def test_esc_cancela_y_no_mata_nada():
    killer = FakeKiller()
    app = make_app(killer)
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("down", "k")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press("escape")
        await settle(app, pilot)
        assert not isinstance(app.screen, ConfirmScreen)
        assert killer.killed == []


async def test_K_mata_todos_los_del_proyecto():
    killer = FakeKiller()
    app = make_app(killer)
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("down")  # un proceso cualquiera de tienda-api
        await pilot.press("K")
        await pilot.pause()
        text = dialog_text(app)
        assert "Matar todo en tienda-api" in text
        assert "Se cerrarán 6 procesos del sistema" in text
        assert "Quedarán libres los puertos :3000 :5432 :8000" in text
        await pilot.press("enter")
        await settle(app, pilot)
        (batch,) = killer.killed
        assert {v.pid for v in batch} == {1, 2, 3, 1001, 1002, 1003}


async def test_k_sobre_la_cabecera_equivale_a_matar_todos():
    killer = FakeKiller()
    app = make_app(killer)
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("k")  # el cursor empieza en la cabecera de tienda-api
        await pilot.pause()
        assert "Matar todo en tienda-api" in dialog_text(app)


async def test_matar_todos_los_huerfanos_avisa_de_los_sin_permiso():
    killer = FakeKiller()
    app = make_app(killer)
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("end")
        await pilot.press("K")
        await pilot.pause()
        text = dialog_text(app)
        assert "Matar todos los huérfanos" in text
        assert "sin permiso" in text


async def test_proceso_que_ya_no_existe_no_abre_dialogo():
    killer = FakeKiller(gone={2})
    app = make_app(killer)
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("down", "down", "k")
        await settle(app, pilot)
        assert not isinstance(app.screen, ConfirmScreen)
        assert killer.killed == []


async def test_con_el_dialogo_abierto_los_atajos_de_la_app_no_actuan():
    killer = FakeKiller()
    app = make_app(killer)
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("down", "k")
        await pilot.pause()
        await pilot.press("q", "i", "k")
        await pilot.pause()
        assert app.is_running
        assert i18n.get_language() == "es"
        assert len(app.screen_stack) == 2  # sigue habiendo un solo diálogo


def test_kill_body_cambia_segun_el_sistema():
    dev = sample_snapshot().projects[0].processes[1]
    group = [(dev, [Victim(2, "python", 1.0)])]
    assert "forzado e inmediato" in kill_body(group, windows=True).plain
    assert "tras 3 s se fuerza" in kill_body(group, windows=False).plain
    assert "Se cerrará 1 proceso del sistema" in kill_body(group, windows=False).plain


def test_result_message():
    assert result_message(KillResult(closed=3)) == ("Se cerraron 3 procesos", "information")
    victim = Victim(1, "x")
    message, severity = result_message(KillResult(closed=1, denied=(victim,)))
    assert message == "Se cerró 1 proceso. 1 proceso no se dejó cerrar (sin permiso)"
    assert severity == "warning"
    assert result_message(KillResult())[0] == "Ese proceso ya no existe"
