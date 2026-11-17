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
from qcorre.ui.styles import KEY_GAP, Key, key_width, keys_line

# Cómo se dibuja cada tecla en el pie.
# Solo se usan símbolos que se ven bien en cualquier terminal: las flechas
# de tabulador y de enter, por ejemplo, salen como otro carácter en la
# terminal de VS Code, así que esas teclas se escriben con su nombre.
KEY_GLYPHS = {"updown": "↑↓", "escape": "esc"}


class Header(Horizontal):
    """Cabecera: marca a la izquierda; conteos e idioma a la derecha."""

    def __init__(self, *, id: str, demo: bool = False) -> None:
        super().__init__(id=id)
        self._counts: tuple[int, int] | None = None
        self.demo = demo  # los datos son simulados: se avisa para que nadie se confunda

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
        if self.demo:
            badge = f"bold {theme.BACKGROUND} on {theme.WARNING}"
            status.append(f" {t('status.demo')} ", style=badge)
            status.append("  ")
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
    """Pie de una sola línea con los atajos que sirven *ahora*.

    La app le pasa dos listas: los atajos del contexto (según el panel con el
    foco y lo que hay seleccionado), por orden de importancia, y los que van
    siempre al final (ayuda y salir). Si no caben, se quitan atajos del
    contexto empezando por el último: los fijos no se pierden nunca, y la
    ayuda (``?``) lista todos los demás.
    """

    def __init__(self) -> None:
        super().__init__()
        self.hints: list[tuple[str, str]] = []
        self.tail: list[tuple[str, str]] = []

    def on_mount(self) -> None:
        self.update_texts()

    def on_resize(self) -> None:
        self.update_texts()

    def set_hints(self, hints: list[tuple[str, str]], tail: list[tuple[str, str]]) -> None:
        """Cambia los atajos mostrados: pares (tecla, clave de traducción)."""
        if (hints, tail) != (self.hints, self.tail):
            self.hints, self.tail = list(hints), list(tail)
            self.update_texts()

    def visible(self, width: int) -> list[Key]:
        """Los atajos que caben en ``width`` columnas."""
        main = [Key(KEY_GLYPHS.get(k, k), t(label)) for k, label in self.hints]
        tail = [Key(KEY_GLYPHS.get(k, k), t(label)) for k, label in self.tail]

        def total(items: list[Key]) -> int:
            gaps = len(KEY_GAP) * max(0, len(items) - 1)
            return sum(key_width(item) for item in items) + gaps

        while main and total(main + tail) > width:
            main.pop()
        return main + tail

    def update_texts(self) -> None:
        # Antes del primer dibujo el ancho aún es cero: se asume que todo cabe.
        width = self.content_size.width or 10_000
        self.update(keys_line(self.visible(width)))
