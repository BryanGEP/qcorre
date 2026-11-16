"""Tests de humo de la interfaz (sin terminal real, con el Pilot de Textual)."""

import pytest

from qcorre import i18n
from qcorre.ui.app import QcorreApp
from qcorre.ui.widgets import HintBar


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


async def test_la_app_arranca_con_sus_paneles():
    app = QcorreApp()
    async with app.run_test():
        assert app.theme == "qcorre"
        assert app.query_one("#projects").border_title == "Proyectos"
        assert app.query_one("#git").border_title == "Git"
        assert app.focused is app.query_one("#projects")


async def test_tab_cambia_de_panel():
    app = QcorreApp()
    async with app.run_test() as pilot:
        await pilot.press("tab")
        assert app.focused is app.query_one("#git")


async def test_i_cambia_el_idioma_de_toda_la_interfaz():
    app = QcorreApp()
    async with app.run_test() as pilot:
        await pilot.press("i")
        assert i18n.get_language() == "en"
        assert app.query_one("#projects").border_title == "Projects"
        assert "quit" in str(app.query_one(HintBar).render())
        await pilot.press("i")
        assert app.query_one("#projects").border_title == "Proyectos"


async def test_q_cierra_la_app():
    app = QcorreApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
    assert not app.is_running
