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

# Límites de la columna del nombre; lo que no cabe se corta con "…".
_MIN_LABEL = 10
_MAX_LABEL = 30

# Columnas que el árbol gasta en sangría antes de cada proceso.
_INDENT = 5


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
        if snapshot is None or snapshot.process_count == 0:
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
        """Devuelve el cursor a la misma fila; si ya no existe, a la misma altura."""
        tree = self.tree
        if tree.last_line < 0:
            return
        target = min(fallback_line, tree.last_line)
        for line in range(tree.last_line + 1):
            node = tree.get_node_at_line(line)
            if node is not None and node.data is not None and node.data.key == key:
                target = line
                break
        tree.move_cursor_to_line(target)
        self.post_message(self.Selected(self.selected))

    def _build_lines(self, snapshot: Snapshot) -> list[tuple[Row, Text]]:
        everyone = [d for p in snapshot.projects for d in p.processes] + list(snapshot.unassigned)
        ports_width = max(len(_ports(d)) for d in everyone)
        time_width = max(len(_time_text(d, self._now)) for d in everyone)
        # Lo que queda para el nombre tras la sangría, la marca y las columnas.
        available = self.content_size.width - _INDENT - 2 - 2 - ports_width - 2 - time_width
        label_width = max(len(d.label) for d in everyone)
        label_width = max(_MIN_LABEL, min(label_width, _MAX_LABEL, available))

        lines: list[tuple[Row, Text]] = []

        def add_processes(project: Project | None, processes: tuple[DevProcess, ...]) -> None:
            for dev in processes:
                lines.append(
                    (
                        Row(project, dev),
                        _process_line(dev, self._now, label_width, ports_width),
                    )
                )
                note = _note_line(dev, self._now)
                if note is not None:
                    lines.append((Row(project, dev, is_note=True), note))

        for project in snapshot.projects:
            lines.append((Row(project), _project_line(project)))
            add_processes(project, project.processes)
        if snapshot.unassigned:
            lines.append((Row(), _orphans_line(len(snapshot.unassigned))))
            add_processes(None, snapshot.unassigned)
        return lines

    # ── Eventos ─────────────────────────────────────────────────

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[Row]) -> None:
        event.stop()
        self.post_message(self.Selected(event.node.data))


def _ports(dev: DevProcess) -> str:
    return " ".join(f":{port}" for port in dev.ports)


def _is_flagged(dev: DevProcess) -> bool:
    """¿Lleva la marca ⚠? (huérfano por algo más que no tener proyecto)."""
    return any(r is not OrphanReason.NO_PROJECT for r in dev.orphan_reasons)


def _project_line(project: Project) -> Text:
    text = Text(no_wrap=True, overflow="ellipsis")
    text.append(project.name, style=f"bold {theme.FOREGROUND}")
    text.append(f"  {len(project.processes)}", style=theme.MUTED)
    if not project.has_git:
        text.append(f"  {t('tag.no_git')}", style=f"italic {theme.MUTED}")
    if any(_is_flagged(d) for d in project.processes):
        text.append("  ⚠", style=theme.WARNING)
    return text


def _orphans_line(count: int) -> Text:
    text = Text(no_wrap=True, overflow="ellipsis")
    text.append("⚠ " + t("group.orphans"), style=f"bold {theme.WARNING}")
    text.append(f"  {count}", style=theme.MUTED)
    return text


def _process_line(dev: DevProcess, now: float, label_width: int, ports_width: int) -> Text:
    text = Text(no_wrap=True, overflow="ellipsis")
    if _is_flagged(dev):
        text.append("⚠ ", style=theme.WARNING)
    elif dev.access_denied:
        text.append("○ ", style=theme.MUTED)
    else:
        text.append("● ", style=theme.SUCCESS)

    label = dev.label
    if len(label) > label_width:
        label = label[: label_width - 1] + "…"
    text.append(label.ljust(label_width), style=theme.FOREGROUND)
    text.append("  " + _ports(dev).ljust(ports_width), style=theme.SECONDARY)

    text.append("  " + _time_text(dev, now), style=theme.MUTED)
    return text


def _time_text(dev: DevProcess, now: float) -> str:
    """Última columna: cuánto lleva corriendo (si se pudo saber)."""
    if dev.info.create_time > 0:
        return short_duration(dev.uptime(now))
    return ""


def _note_line(dev: DevProcess, now: float) -> Text | None:
    """Línea extra bajo el proceso: por qué es huérfano y/o "sin permiso"."""
    pieces = [(note, theme.WARNING) for note in orphan_notes(dev, now)]
    if dev.access_denied:
        pieces.append((t("tag.denied"), f"italic {theme.MUTED}"))
    if not pieces:
        return None
    text = Text(no_wrap=True, overflow="ellipsis")
    text.append("  ╰ ", style=pieces[0][1])
    for index, (piece, style) in enumerate(pieces):
        if index:
            text.append(" · ", style=theme.MUTED)
        text.append(piece, style=style)
    return text
