"""Panel izquierdo: árbol de proyectos con sus procesos."""

from __future__ import annotations

from dataclasses import dataclass

from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode

from qcorre import i18n
from qcorre.i18n import t
from qcorre.models import DevProcess, OrphanReason, Project, Snapshot
from qcorre.ui import theme
from qcorre.ui.format import orphan_notes, short_duration
from qcorre.ui.widgets import Panel

# Mínimo de columnas para el nombre de un proceso; lo que no cabe se corta con "…".
_MIN_LABEL = 8

# Columnas que el árbol gasta antes de cada línea: el triángulo de las
# cabeceras ("▼ ") y la sangría de los procesos y sus notas.
_GROUP_PREFIX = 2
_LEAF_PREFIX = 3

# Se deja libre la última columna, que ocupa la barra de desplazamiento
# cuando aparece: así las filas no se recortan al crecer la lista.
_SCROLLBAR = 1

# Separación entre columnas.
_GAP = 2

# Puntos de estado. Solo glifos de ancho fijo: el triángulo de aviso y
# similares se dibujan como emoji en algunas terminales y desalinean.
_DOT = "●"
_EMPTY_DOT = "○"


@dataclass(frozen=True)
class Row:
    """Lo que representa una línea del árbol."""

    project: Project | None = None  # None en el grupo de huérfanos
    process: DevProcess | None = None  # None en las cabeceras de grupo
    is_note: bool = False  # línea extra con el motivo de huérfano

    @property
    def key(self) -> tuple:
        """Identidad estable entre refrescos, para conservar el cursor."""
        group = str(self.project.path) if self.project else "<orphans>"
        return (group, self.process.pid if self.process else None, self.is_note)


class ProjectTree(Tree[Row]):
    """Árbol cuyas líneas conservan sus colores bajo el cursor.

    El árbol normal pinta toda la línea seleccionada de un solo color; aquí el
    cursor solo aporta el fondo, para que el verde/ámbar de estado y los
    puertos se sigan distinguiendo.
    """

    def render_label(self, node: TreeNode[Row], base_style: Style, style: Style) -> Text:
        return super().render_label(node, base_style, Style(bgcolor=style.bgcolor))

    def action_select_cursor(self) -> None:
        """Enter: sobre un proceso pide su detalle; sobre un grupo lo pliega."""
        node = self.cursor_node
        if node is not None and node.data is not None and node.data.process is not None:
            self.post_message(ProjectsPanel.DetailRequested(node.data))
        else:
            super().action_select_cursor()


class ProjectsPanel(Panel):
    """Árbol de proyectos → procesos. Avisa qué está seleccionado."""

    title_key = "panel.projects"

    class Selected(Message):
        """El cursor se movió a otra línea."""

        def __init__(self, row: Row | None) -> None:
            super().__init__()
            self.row = row

    class DetailRequested(Message):
        """El usuario pulsó Enter sobre un proceso."""

        def __init__(self, row: Row) -> None:
            super().__init__()
            self.row = row

    def __init__(self, *, id: str) -> None:
        super().__init__(id=id)
        self.snapshot: Snapshot | None = None
        self._now = 0.0
        self._signature: tuple | None = None

    def compose(self) -> ComposeResult:
        yield Static(classes="empty")
        tree = ProjectTree("", id="tree")
        tree.show_root = False
        tree.show_guides = False
        tree.guide_depth = 3
        yield tree

    @property
    def tree(self) -> ProjectTree:
        return self.query_one("#tree", ProjectTree)

    @property
    def selected(self) -> Row | None:
        """La línea bajo el cursor (o ``None`` si el árbol está vacío)."""
        node = self.tree.cursor_node
        return node.data if node is not None else None

    def show_snapshot(self, snapshot: Snapshot, now: float) -> None:
        """Muestra una foto nueva. Solo redibuja si algo visible cambió."""
        self.snapshot = snapshot
        self._now = now
        self._render_tree()

    def update_texts(self) -> None:
        super().update_texts()
        self._render_tree()

    def on_resize(self) -> None:
        # El ancho de las columnas depende del ancho del panel.
        self._render_tree()

    # ── Dibujo ──────────────────────────────────────────────────

    def _render_tree(self) -> None:
        empty = self.query_one(".empty", Static)
        tree = self.tree
        snapshot = self.snapshot
        if snapshot is None or snapshot.is_empty:
            empty.update(t("projects.scanning" if snapshot is None else "projects.empty"))
            empty.display = True
            tree.display = False
            if self._signature != ():
                self._signature = ()
                tree.clear()
                self.post_message(self.Selected(None))
            return

        lines = self._build_lines(snapshot)
        signature = (i18n.get_language(), tuple((row.key, text.plain) for row, text in lines))
        if signature == self._signature:
            return
        self._signature = signature

        had_focus = self.screen.focused is None or self.screen.focused is tree
        cursor_key = self.selected.key if self.selected else None
        cursor_line = max(0, tree.cursor_line)
        collapsed = {
            node.data.key
            for node in tree.root.children
            if node.data is not None and not node.is_expanded
        }

        tree.clear()
        group: TreeNode[Row] | None = None
        for row, text in lines:
            if row.process is None:
                group = tree.root.add(text, data=row, expand=row.key not in collapsed)
            else:
                assert group is not None
                group.add_leaf(text, data=row)

        empty.display = False
        tree.display = True
        if had_focus:
            tree.focus()
        # El árbol calcula sus líneas al refrescar: el cursor se coloca después.
        self.call_after_refresh(self._restore_cursor, cursor_key, cursor_line)

    def _restore_cursor(self, key: tuple | None, fallback_line: int) -> None:
        """Devuelve el cursor a la misma fila tras redibujar el árbol.

        Si la fila ya no existe (el proceso murió), se queda en su proyecto:
        primero se prueba con la fila del proceso (si el cursor estaba en su
        nota) y luego con la cabecera del grupo. Así, tras matar un proceso,
        el panel de git sigue mostrando el mismo proyecto. Solo si el grupo
        entero desapareció se cae a la misma altura de antes.
        """
        tree = self.tree
        if tree.last_line < 0:
            return
        lines = {}
        for line in range(tree.last_line + 1):
            node = tree.get_node_at_line(line)
            if node is not None and node.data is not None:
                lines.setdefault(node.data.key, line)

        target = min(fallback_line, tree.last_line)
        if key is not None:
            group, pid, _ = key
            for candidate in (key, (group, pid, False), (group, None, False)):
                if candidate in lines:
                    target = lines[candidate]
                    break
        tree.move_cursor_to_line(target)
        self.post_message(self.Selected(self.selected))

    def _build_lines(self, snapshot: Snapshot) -> list[tuple[Row, Text]]:
        """Las líneas del árbol, todas a lo ancho del panel.

        Ocupar todo el ancho tiene dos efectos: la selección pinta la fila
        entera, y los puertos, tiempos y conteos quedan alineados a la derecha
        en columnas, como en una tabla.
        """
        everyone = [d for p in snapshot.projects for d in p.processes] + list(snapshot.unassigned)
        width = max(_MIN_LABEL + 10, (self.content_size.width or 40) - _SCROLLBAR)
        columns = _Columns(
            group=width - _GROUP_PREFIX,
            leaf=width - _LEAF_PREFIX,
            ports=max((len(_ports(d)) for d in everyone), default=0),
            time=max((len(_time_text(d, self._now)) for d in everyone), default=0),
        )

        lines: list[tuple[Row, Text]] = []

        def add_processes(project: Project | None, processes: tuple[DevProcess, ...]) -> None:
            for dev in processes:
                lines.append((Row(project, dev), _process_line(dev, self._now, columns)))
                note = _note_line(dev, self._now, columns.leaf)
                if note is not None:
                    lines.append((Row(project, dev, is_note=True), note))

        for project in snapshot.projects:
            lines.append((Row(project), _project_line(project, columns.group)))
            add_processes(project, project.processes)
        if snapshot.unassigned:
            lines.append((Row(), _orphans_line(len(snapshot.unassigned), columns.group)))
            add_processes(None, snapshot.unassigned)
        return lines

    # ── Eventos ─────────────────────────────────────────────────

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[Row]) -> None:
        event.stop()
        self.post_message(self.Selected(event.node.data))


@dataclass(frozen=True)
class _Columns:
    """Anchos de las líneas del árbol."""

    group: int  # ancho de una cabecera de grupo
    leaf: int  # ancho de la línea de un proceso o de una nota
    ports: int  # columna de puertos
    time: int  # columna del tiempo corriendo


def _ports(dev: DevProcess) -> str:
    return " ".join(f":{port}" for port in dev.ports)


def _is_flagged(dev: DevProcess) -> bool:
    """¿Va en color de aviso? (huérfano por algo más que no tener proyecto)."""
    return any(r is not OrphanReason.NO_PROJECT for r in dev.orphan_reasons)


def _fit(text: Text, width: int, right: Text | None = None) -> Text:
    """Ajusta ``text`` a ``width`` columnas, con ``right`` pegado al borde derecho."""
    right = right or Text()
    room = width - len(right.plain)
    if len(text.plain) > room:
        text.truncate(max(1, room - 1))
        text.append("…", style=theme.MUTED)
    text.append(" " * (room - len(text.plain)))
    text.append_text(right)
    return text


def _project_line(project: Project, width: int) -> Text:
    """Cabecera de un proyecto: nombre a la izquierda, número de procesos a la derecha."""
    text = Text(no_wrap=True)
    text.append(project.name, style=f"bold {theme.ACCENT}")
    if not project.has_git:
        text.append(f"  {t('tag.no_git')}", style=f"italic {theme.MUTED}")
    if not project.processes:
        text.append(f"  {t('tag.idle')}", style=f"italic {theme.MUTED}")
    if any(_is_flagged(d) for d in project.processes):
        # Si el proyecto está plegado, este punto es la única pista del aviso.
        text.append(f"  {_DOT}", style=theme.WARNING)
    count = Text(str(len(project.processes)), style=theme.MUTED) if project.processes else None
    return _fit(text, width, count)


def _orphans_line(count: int, width: int) -> Text:
    # El estilo va en el tramo, no en el Text: si no, el conteo lo heredaría.
    text = Text(no_wrap=True)
    text.append(t("group.orphans"), style=f"bold {theme.WARNING}")
    return _fit(text, width, Text(str(count), style=theme.MUTED))


def _process_line(dev: DevProcess, now: float, columns: _Columns) -> Text:
    """``● nombre ............ :8000   2h 14m``: puertos y tiempo a la derecha.

    El estado lo da solo el color del punto: verde (bien), ámbar (huérfano) o
    un círculo vacío (el sistema no deja leerlo).
    """
    text = Text(no_wrap=True)
    if dev.access_denied:
        text.append(f"{_EMPTY_DOT} ", style=theme.MUTED)
    elif _is_flagged(dev):
        text.append(f"{_DOT} ", style=theme.WARNING)
    else:
        text.append(f"{_DOT} ", style=theme.SUCCESS)
    text.append(dev.label, style=theme.FOREGROUND)

    right = Text(no_wrap=True)
    if columns.ports:
        # Una fila sin puerto deja la columna en blanco, sin color de fondo.
        right.append(" " * _GAP + _ports(dev).rjust(columns.ports), style=theme.SECONDARY)
    if columns.time:
        right.append(" " * _GAP + _time_text(dev, now).rjust(columns.time), style=theme.MUTED)
    return _fit(text, columns.leaf, right)


def _time_text(dev: DevProcess, now: float) -> str:
    """Última columna: cuánto lleva corriendo (si se pudo saber)."""
    if dev.info.create_time > 0:
        return short_duration(dev.uptime(now))
    return ""


def _note_line(dev: DevProcess, now: float, width: int) -> Text | None:
    """Línea extra bajo el proceso: por qué es huérfano y/o "sin permiso".

    Va en gris tenue: es un detalle. El aviso ya lo da el color del punto.
    """
    pieces = orphan_notes(dev, now)
    if dev.access_denied:
        pieces.append(t("tag.denied"))
    if not pieces:
        return None
    text = Text("╰ " + " · ".join(pieces), style=theme.MUTED, no_wrap=True)
    return _fit(text, width)
