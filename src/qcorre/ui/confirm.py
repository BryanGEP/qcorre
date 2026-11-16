"""Diálogo de confirmación: muestra qué va a pasar antes de hacerlo.

Es genérico: lo usan tanto "matar procesos" como (más adelante) las acciones
de git. Devuelve ``True`` si el usuario confirma y ``False`` si cancela.
"""

from __future__ import annotations

from rich.console import RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from qcorre.i18n import t
from qcorre.ui import theme


class ConfirmScreen(ModalScreen[bool]):
    """Ventana modal con título, cuerpo y dos salidas: confirmar o cancelar."""

    BINDINGS = [
        Binding("enter", "confirm", show=False),
        Binding("escape", "cancel", show=False),
    ]

    def __init__(
        self,
        title: str,
        body: RenderableType,
        *,
        confirm_key: str = "confirm.accept",
        danger: bool = False,
    ) -> None:
        """``confirm_key`` es la clave de traducción del verbo de confirmar;
        ``danger`` pinta el diálogo en rojo para acciones destructivas."""
        super().__init__()
        self.dialog_title = title
        self.body = body
        self.confirm_key = confirm_key
        self.danger = danger

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog", classes="danger" if self.danger else ""):
            with VerticalScroll(id="dialog-body"):
                yield Static(self.body)
            yield Static(self._keys(), id="dialog-keys")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = self.dialog_title

    def _keys(self) -> Text:
        accent = theme.ERROR if self.danger else theme.ACCENT
        line = Text(justify="right")
        line.append("enter", style=f"bold {accent}")
        line.append(" " + t(self.confirm_key), style=theme.FOREGROUND)
        line.append("     ")
        line.append("esc", style=f"bold {theme.ACCENT}")
        line.append(" " + t("confirm.cancel"), style=theme.MUTED)
        return line

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class InfoScreen(ModalScreen[None]):
    """Ventana modal de solo lectura (por ejemplo, el detalle de un proceso)."""

    BINDINGS = [
        Binding("escape", "close", show=False),
        Binding("enter", "close", show=False),
        Binding("q", "close", show=False),
    ]

    def __init__(self, title: str, body: RenderableType) -> None:
        super().__init__()
        self.dialog_title = title
        self.body = body

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            with VerticalScroll(id="dialog-body"):
                yield Static(self.body)
            keys = Text(justify="right")
            keys.append("esc", style=f"bold {theme.ACCENT}")
            keys.append(" " + t("info.close"), style=theme.MUTED)
            yield Static(keys, id="dialog-keys")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = self.dialog_title

    def action_close(self) -> None:
        self.dismiss(None)
