"""Aplicación principal de qcorre."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal

from qcorre import i18n
from qcorre.ui.theme import QCORRE_THEME
from qcorre.ui.widgets import Header, HintBar, Panel


class QcorreApp(App[None]):
    """Panel del desarrollador: procesos por proyecto y git amigable."""

    TITLE = "qcorre"
    CSS_PATH = "theme.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("i", "toggle_language", show=False),
        Binding("q", "quit", show=False),
    ]

    # Atajos que se muestran en el pie: (tecla, clave de traducción).
    HINTS = [
        ("tab", "hint.panel"),
        ("i", "hint.language"),
        ("q", "hint.quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(id="header")
        with Horizontal(id="body"):
            yield Panel("panel.projects", "projects.empty", id="projects")
            yield Panel("panel.git", "git.empty", id="git")
        yield HintBar(self.HINTS)

    def __init__(self) -> None:
        super().__init__()
        self.register_theme(QCORRE_THEME)
        self.theme = QCORRE_THEME.name

    def get_css_variables(self) -> dict[str, str]:
        """Añade las variables propias (``$qc-*``) a las del tema.

        El CSS se parsea antes de que el tema quede activo, así que las
        variables propias deben existir siempre, sea cual sea el tema.
        """
        return {**QCORRE_THEME.variables, **super().get_css_variables()}

    def on_mount(self) -> None:
        self.query_one("#projects").focus()

    def action_toggle_language(self) -> None:
        """Alterna entre español e inglés y repinta los textos."""
        i18n.set_language(i18n.next_language())
        self.refresh_texts()

    def refresh_texts(self) -> None:
        """Pide a cada widget con textos traducibles que se actualice."""
        for widget in self.query("*"):
            update = getattr(widget, "update_texts", None)
            if callable(update):
                update()
