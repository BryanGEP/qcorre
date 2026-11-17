"""Diálogo de confirmación: muestra qué va a pasar antes de hacerlo.

Es genérico: lo usan tanto "matar procesos" como (más adelante) las acciones
de git. Devuelve ``True`` si el usuario confirma y ``False`` si cancela.
"""

from __future__ import annotations

from collections.abc import Callable

from rich.console import RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Input, Static

from qcorre.i18n import t
from qcorre.ui import theme
from qcorre.ui.dialog import DialogScreen
from qcorre.ui.styles import Key, keys_line


class ConfirmScreen(DialogScreen[bool]):
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

    def _keys(self) -> Text:
        return keys_line(
            [
                Key("enter", t(self.confirm_key), primary=True, danger=self.danger),
                Key("esc", t("confirm.cancel")),
            ]
        )

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class InfoScreen(DialogScreen[None]):
    """Ventana modal de solo lectura (por ejemplo, el detalle de un proceso)."""

    # Solo lleva una línea de teclas: puede aprovechar más alto de la pantalla.
    BODY_FRACTION = 0.7

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
            yield Static(keys_line([Key("esc", t("info.close"))]), id="dialog-keys")

    def action_close(self) -> None:
        self.dismiss(None)


class PromptScreen(DialogScreen[str | None]):
    """Pide un texto (el mensaje del commit) con la vista previa debajo.

    ``preview`` recibe lo escrito hasta el momento y devuelve el cuerpo del
    diálogo: así el comando exacto se actualiza mientras se teclea. Enter
    confirma (solo si hay texto) y Esc cancela.
    """

    # Además de las teclas lleva el rótulo, el campo de texto y su margen.
    FIXED_ROWS = 7

    BINDINGS = [
        Binding("escape", "cancel", show=False),
        # El foco está en el campo de texto: estas teclas recorren la vista previa.
        Binding("pagedown", "scroll_body(1)", show=False),
        Binding("pageup", "scroll_body(-1)", show=False),
    ]

    def __init__(
        self,
        title: str,
        prompt: str,
        preview: Callable[[str], RenderableType],
        *,
        placeholder: str = "",
        confirm_key: str = "confirm.accept",
        validate: Callable[[str], str | None] | None = None,
    ) -> None:
        """``validate`` recibe el texto y devuelve por qué no sirve (o ``None``)."""
        super().__init__()
        self.dialog_title = title
        self.prompt = prompt
        self.preview = preview
        self.placeholder = placeholder
        self.confirm_key = confirm_key
        self.validate = validate

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(Text(self.prompt, style=f"bold {theme.FOREGROUND}"), id="dialog-prompt")
            yield Input(placeholder=self.placeholder, id="dialog-input")
            with VerticalScroll(id="dialog-body"):
                yield Static(self.preview(""), id="dialog-preview")
            yield Static(self._keys(), id="dialog-keys")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def _keys(self) -> Text:
        return keys_line(
            [Key("enter", t(self.confirm_key), primary=True), Key("esc", t("confirm.cancel"))]
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one("#dialog-preview", Static).update(self.preview(event.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        problem = self.validate(value) if self.validate else None
        if problem:
            self.app.notify(problem, severity="warning")
        elif value:
            self.dismiss(value)

    def action_scroll_body(self, direction: int) -> None:
        body = self.query_one("#dialog-body", VerticalScroll)
        if direction > 0:
            body.scroll_page_down(animate=False)
        else:
            body.scroll_page_up(animate=False)

    def action_cancel(self) -> None:
        self.dismiss(None)
