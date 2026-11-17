"""Estilos compartidos: una sola forma de pintar encabezados y teclas.

Todos los diálogos y el pie usan estas funciones, para que el mismo papel se
vea igual en toda la app:

- **Encabezado de sección** ("Qué va a pasar", "Comando exacto", "En tu
  compu"...): negrita en el color del texto.
- **Tecla:** dibujada como una tecla, en una píldora del color de acento (roja
  si la acción destruye algo). La etiqueta de la acción principal va en el
  color del texto; las demás, en gris tenue.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from rich.text import Text

from qcorre.ui import theme

# Separación entre una tecla y la siguiente.
KEY_GAP = "   "


def heading(label: str) -> Text:
    """Encabezado de sección."""
    return Text(label, style=f"bold {theme.FOREGROUND}")


@dataclass(frozen=True)
class Key:
    """Una tecla con su acción, tal como se muestra al usuario."""

    key: str  # ya dibujada: "enter", "esc", "↑↓"...
    label: str  # ya traducida
    primary: bool = False  # la acción principal del diálogo
    danger: bool = False  # la acción destruye algo (matar, descartar...)


def key_width(item: Key) -> int:
    """Columnas que ocupa: la píldora (con un espacio a cada lado) y la etiqueta."""
    return len(item.key) + 2 + 1 + len(item.label)


def keycap(key: str, *, danger: bool = False) -> Text:
    """Una tecla dibujada: `` c `` sobre una píldora de color."""
    color = theme.ERROR if danger else theme.ACCENT
    return Text(f" {key} ", style=f"bold {theme.BACKGROUND} on {color}")


def keys_line(items: Sequence[Key], *, justify: str = "left") -> Text:
    """Una línea de teclas: ``enter guardar   esc cancelar``."""
    text = Text(no_wrap=True, overflow="ellipsis", justify=justify)
    for index, item in enumerate(items):
        if index:
            text.append(KEY_GAP)
        text.append_text(keycap(item.key, danger=item.danger))
        label_color = theme.FOREGROUND if item.primary else theme.MUTED
        text.append(" " + item.label, style=label_color)
    return text
