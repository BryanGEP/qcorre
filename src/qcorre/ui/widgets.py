"""Widgets base de la interfaz.

Convención de idioma: todo widget que muestra texto traducible implementa
``update_texts()``. Al cambiar de idioma la app llama a ese método en cada
widget, sin reconstruir la pantalla (así no se pierde el foco ni la selección).
"""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from qcorre import i18n
from qcorre.i18n import t
from qcorre.ui import theme

# Cómo se dibuja cada tecla en el pie.
# Solo se usan símbolos que se ven bien en cualquier terminal: las flechas
# de tabulador y de enter, por ejemplo, salen como otro carácter en la
# terminal de VS Code, así que esas teclas se escriben con su nombre.
KEY_GLYPHS = {"updown": "↑↓", "escape": "esc"}


class Header(Horizontal):
    """Cabecera: marca a la izquierda; conteos e idioma a la derecha."""

    def __init__(self, *, id: str) -> None:
        super().__init__(id=id)
        self._counts: tuple[int, int] | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="brand")
        yield Static(id="status")

    def on_mount(self) -> None:
        self.update_texts()

    def set_counts(self, projects: int, processes: int) -> None:
        self._counts = (projects, processes)
        self.update_texts()

    def update_texts(self) -> None:
        brand = Text()
        brand.append("▍", style=theme.ACCENT)
        brand.append("qcorre", style=f"bold {theme.FOREGROUND}")
        brand.append("  " + t("app.tagline"), style=theme.MUTED)
        self.query_one("#brand", Static).update(brand)

        status = Text()
        if self._counts is not None:
            projects, processes = self._counts
            status.append(t("status.projects", n=projects), style=theme.MUTED)
            status.append("  ·  ", style=theme.MUTED)
            status.append(t("status.processes", n=processes), style=theme.MUTED)
            status.append("  ·  ", style=theme.MUTED)
        status.append(i18n.get_language().upper(), style=f"bold {theme.ACCENT}")
        self.query_one("#status", Static).update(status)


class Panel(Vertical):
    """Panel con borde redondeado y título en el borde."""

    title_key = ""

    def on_mount(self) -> None:
        self.update_texts()

    def update_texts(self) -> None:
        self.border_title = t(self.title_key)


class HintBar(Static):
    """Pie con los atajos de teclado disponibles."""

    def __init__(self, hints: list[tuple[str, str]]) -> None:
        """``hints`` es una lista de pares (tecla, clave de traducción)."""
        super().__init__()
        self.hints = hints

    def on_mount(self) -> None:
        self.update_texts()

    def set_hints(self, hints: list[tuple[str, str]]) -> None:
        """Reemplaza los atajos mostrados (cambian según el panel activo)."""
        self.hints = hints
        self.update_texts()

    def update_texts(self) -> None:
        line = Text(no_wrap=True, overflow="ellipsis")
        for index, (key, label_key) in enumerate(self.hints):
            if index:
                line.append("   ")
            line.append(KEY_GLYPHS.get(key, key), style=f"bold {theme.ACCENT}")
            line.append(" " + t(label_key), style=theme.MUTED)
        self.update(line)
