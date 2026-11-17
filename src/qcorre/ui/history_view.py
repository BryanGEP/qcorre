"""Dibuja el historial: el gráfico de ramas con colores y los datos de cada commit.

Cada commit ocupa exactamente una línea, en columnas::

    ●─╮ a1b2c3d (HEAD → main) Merge de feature/pagos      2h 00m  Ana
    ● │ 4d5e6f7 Valida montos negativos                   5h 00m  Ana
    │ ● 9f8e7d6 (feature/pagos) Agrega webhook de pagos   3h 00m  Luis

A la izquierda, el gráfico y el hash; en medio, las ramas y el mensaje (que se
corta si no cabe); a la derecha, hace cuánto se hizo y quién. En paneles
angostos se sacrifican primero el autor, luego la antigüedad y por último
parte de las etiquetas de rama.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text

from qcorre.git.graph import GraphRow, graph_width, layout
from qcorre.git.history import Commit, History, Ref, RefKind
from qcorre.i18n import t
from qcorre.ui import theme
from qcorre.ui.format import short_duration

# Ancho máximo del gráfico (12 carriles); lo que no cabe se corta con "…".
MAX_GRAPH_WIDTH = 24

# Cuántas etiquetas (ramas, tags) se muestran por commit antes de resumir.
MAX_REFS = 3

# Lo mínimo que debe quedar para el mensaje del commit.
MIN_SUBJECT = 16

# Ancho máximo de la columna del autor, y desde qué ancho de panel se muestra.
MAX_AUTHOR = 16
AUTHOR_FROM_WIDTH = 96

# Desde qué ancho de panel se muestra la columna de antigüedad.
AGE_FROM_WIDTH = 56

REF_STYLES = {
    RefKind.HEAD: f"bold {theme.SUCCESS}",
    RefKind.DETACHED: f"bold {theme.WARNING}",
    RefKind.LOCAL: f"bold {theme.ACCENT}",
    RefKind.REMOTE: theme.SECONDARY,
    RefKind.TAG: theme.WARNING,
}


@dataclass(frozen=True)
class Columns:
    """Anchos de las columnas del historial para un panel dado."""

    width: int  # ancho total disponible
    graph: int  # ancho del gráfico
    age: int = 0  # columna "hace cuánto" (0 = no se muestra)
    author: int = 0  # columna del autor (0 = no se muestra)

    @property
    def right(self) -> int:
        """Espacio que ocupan las columnas de la derecha, con sus separadores."""
        return (self.age + 2 if self.age else 0) + (self.author + 2 if self.author else 0)


def lane_color(index: int | None) -> str:
    """Tono de un carril. Los carriles reutilizan la paleta en ciclo."""
    if index is None:
        return theme.MUTED
    return theme.LANES[index % len(theme.LANES)]


def age_text(commit: Commit, now: float) -> str:
    """Hace cuánto se hizo el commit: ``2h 00m`` (vacío si no tiene fecha)."""
    return short_duration(now - commit.time) if commit.time > 0 else ""


def columns_for(rows: list[GraphRow], now: float, width: int) -> Columns:
    """Decide qué columnas caben en ``width`` y con qué ancho."""
    graph = min(graph_width(rows), MAX_GRAPH_WIDTH)
    age = max((len(age_text(row.commit, now)) for row in rows), default=0)
    author = min(MAX_AUTHOR, max((len(row.commit.author) for row in rows), default=0))
    return Columns(
        width=width,
        graph=graph,
        age=age if width >= AGE_FROM_WIDTH else 0,
        author=author if width >= AUTHOR_FROM_WIDTH else 0,
    )


def history_body(history: History, now: float, *, width: int = 70) -> Text:
    """El historial completo, una línea por commit."""
    if not history.commits:
        return Text(t("history.empty"), style=theme.MUTED)

    rows = layout(history.commits)
    columns = columns_for(rows, now, width)
    text = Text(no_wrap=True, overflow="ellipsis")
    for index, row in enumerate(rows):
        if index:
            text.append("\n")
        text.append_text(commit_line(row, now, columns))
    if history.truncated:
        note = t("history.truncated", n=len(history.commits))
        text.append("\n\n" + note, style=theme.MUTED)
    return text


def commit_line(row: GraphRow, now: float, columns: Columns) -> Text:
    """Una línea: gráfico, hash corto, ramas, mensaje, antigüedad y autor."""
    commit = row.commit
    line = graph_text(row, columns.graph)
    line.append(" " + commit.short_oid + " ", style=theme.MUTED)
    start = len(line.plain)
    room = columns.width - start - columns.right

    # Si las etiquetas no dejan sitio al mensaje, se muestran menos ("+N").
    refs = refs_text(commit.refs)
    for limit in range(MAX_REFS - 1, 0, -1):
        if len(refs.plain) + 1 + MIN_SUBJECT <= room:
            break
        refs = refs_text(commit.refs, limit=limit)
    if refs.plain:
        line.append_text(refs)
        line.append(" ")
        room -= len(refs.plain) + 1

    subject = commit.subject or t("history.no_subject")
    style = theme.FOREGROUND
    if not commit.subject:
        style = f"italic {theme.MUTED}"
    elif commit.is_merge:
        style = theme.MUTED  # los merges son "pegamento": van más tenues
    room = max(room, 1)
    if len(subject) > room:
        subject = subject[: room - 1] + "…"
    line.append(subject, style=style)

    # Columnas de la derecha, alineadas en todas las filas.
    if columns.right:
        line.append(" " * (room - len(subject)))
    if columns.age:
        line.append("  " + age_text(commit, now).rjust(columns.age), style=theme.MUTED)
    if columns.author:
        author = commit.author
        if len(author) > columns.author:
            author = author[: columns.author - 1] + "…"
        line.append("  " + author, style=theme.MUTED)

    # Último recurso (p. ej. un nombre de rama larguísimo): cortar la línea.
    if len(line.plain) > columns.width:
        line.truncate(columns.width, overflow="ellipsis")
    line.rstrip()
    return line


def graph_text(row: GraphRow, columns: int) -> Text:
    """El dibujo del gráfico de una fila, coloreado y ajustado a ``columns``."""
    text = Text(no_wrap=True)
    cells = row.cells
    cut = len(row.text) > columns
    visible = cells[: columns - 1] if cut else cells[:columns]
    for cell in visible:
        style = lane_color(cell.color)
        if cell.char == "●":
            style = f"bold {style}"
        text.append(cell.char, style=style)
    if cut:
        text.append("…", style=theme.MUTED)
    text.append(" " * max(0, columns - len(text.plain)))
    return text


def refs_text(refs: tuple[Ref, ...], *, limit: int = MAX_REFS) -> Text:
    """Las ramas y etiquetas de un commit: ``(HEAD → main, origin/main, v1.0)``.

    Se muestran como mucho ``limit``; el resto se resume como ``+N``.
    """
    text = Text(no_wrap=True)
    if not refs:
        return text
    text.append("(", style=theme.MUTED)
    for index, ref in enumerate(refs[:limit]):
        if index:
            text.append(", ", style=theme.MUTED)
        label = f"HEAD → {ref.name}" if ref.kind is RefKind.HEAD else ref.name
        text.append(label, style=REF_STYLES[ref.kind])
    hidden = len(refs) - limit
    if hidden > 0:
        text.append(f", +{hidden}", style=theme.MUTED)
    text.append(")", style=theme.MUTED)
    return text
