"""Diálogo para elegir una opción de una lista (ramas, cosas por deshacer...).

Devuelve ``(acción, id de la opción)`` o ``None`` si se cierra. La acción por
defecto (Enter) es ``"select"``; cada pantalla puede añadir teclas propias,
como ``n`` para "nueva rama" o ``d`` para "borrar".
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from qcorre.i18n import t
from qcorre.ui.dialog import DialogScreen
from qcorre.ui.styles import Key, keys_line


@dataclass(frozen=True)
class Choice:
    """Una línea de la lista. Sin ``id`` es un encabezado (no se puede elegir)."""

    label: Text
    id: str | None = None


@dataclass(frozen=True)
class PickerKey:
    """Tecla adicional del diálogo."""

    key: str
    action: str  # lo que se devuelve junto con la opción resaltada
    label_key: str  # clave de traducción de su nombre
    needs_choice: bool = True  # ¿actúa sobre la opción resaltada?


PickerResult = tuple[str, str | None]


class PickerScreen(DialogScreen[PickerResult | None]):
    BODY = "#picker-list"

    BINDINGS = [Binding("escape", "close", show=False)]

    def __init__(
        self,
        title: str,
        choices: list[Choice],
        *,
        select_key: str = "confirm.accept",
        keys: tuple[PickerKey, ...] = (),
        note: Text | None = None,
    ) -> None:
        super().__init__()
        self.dialog_title = title
        self.choices = choices
        self.select_key = select_key
        self.keys = keys
        self.note = note

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            if self.note is not None:
                yield Static(self.note, id="picker-note")
            options = [
                Option(choice.label, id=choice.id, disabled=choice.id is None)
                for choice in self.choices
            ]
            yield OptionList(*options, id="picker-list")
            yield Static(self._keys(), id="dialog-keys")

    def on_mount(self) -> None:
        options = self.query_one(OptionList)
        options.focus()
        first = next((i for i, c in enumerate(self.choices) if c.id is not None), None)
        if first is not None:
            options.highlighted = first

    def _keys(self) -> Text:
        items = [Key("enter", t(self.select_key), primary=True)]
        items += [Key(key.key, t(key.label_key)) for key in self.keys]
        items.append(Key("esc", t("picker.close")))
        return keys_line(items)

    @property
    def highlighted_id(self) -> str | None:
        """Id de la opción bajo el cursor."""
        index = self.query_one(OptionList).highlighted
        if index is None or not 0 <= index < len(self.choices):
            return None
        return self.choices[index].id

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        if event.option.id is not None:
            self.dismiss(("select", event.option.id))

    def on_key(self, event: events.Key) -> None:
        for key in self.keys:
            if event.character == key.key or event.key == key.key:
                event.stop()
                chosen = self.highlighted_id
                if key.needs_choice and chosen is None:
                    return
                self.dismiss((key.action, chosen if key.needs_choice else None))
                return

    def action_close(self) -> None:
        self.dismiss(None)
