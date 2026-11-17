"""Texto de la pantalla de ayuda: todos los atajos, agrupados."""

from __future__ import annotations

from rich.text import Text

from qcorre.i18n import t
from qcorre.ui import theme
from qcorre.ui.styles import heading

# (título de la sección, [(tecla, clave de traducción de lo que hace)])
SECTIONS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "help.section.move",
        (
            ("↑ ↓", "help.move"),
            ("tab", "help.panel"),
            ("1 2", "help.jump"),
            ("enter", "help.enter"),
            ("r", "help.refresh"),
        ),
    ),
    (
        "help.section.processes",
        (
            ("k", "help.kill"),
            ("K", "help.kill_all"),
        ),
    ),
    (
        "help.section.git",
        (
            ("c", "help.commit"),
            ("p", "help.push"),
            ("l", "help.pull"),
            ("f", "help.fetch"),
            ("b", "help.branches"),
            ("u", "help.undo"),
            ("h", "help.history"),
            ("a", "help.files"),
        ),
    ),
    (
        "help.section.app",
        (
            ("i", "help.language"),
            ("?", "help.help"),
            ("q", "help.quit"),
        ),
    ),
)

# Ideas que conviene tener presentes al usar qcorre.
NOTES = ("help.note.preview", "help.note.backup", "help.note.limits")


def help_body() -> Text:
    """Cuerpo de la pantalla de ayuda."""
    key_width = max(len(key) for _, keys in SECTIONS for key, _ in keys)
    text = Text()
    for index, (title, keys) in enumerate(SECTIONS):
        if index:
            text.append("\n\n")
        text.append_text(heading(t(title)))
        for key, label in keys:
            text.append("\n  " + key.ljust(key_width), style=f"bold {theme.ACCENT}")
            text.append("  " + t(label), style=theme.FOREGROUND)
    text.append("\n")
    for note in NOTES:
        text.append("\n• ", style=theme.MUTED)
        text.append(t(note), style=theme.MUTED)
    return text
