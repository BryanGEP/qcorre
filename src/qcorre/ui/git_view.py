"""Dibuja el estado de git: frases, lista de archivos y mapa compu ↔ remoto."""

from __future__ import annotations

from rich.text import Text

from qcorre.git import explain
from qcorre.git.parse import ChangeKind, FileChange, RepoStatus
from qcorre.i18n import t
from qcorre.ui import theme
from qcorre.ui.format import short_duration

TONE_STYLES = {
    explain.GOOD: theme.SUCCESS,
    explain.INFO: theme.FOREGROUND,
    explain.WARN: theme.WARNING,
    explain.MUTED: theme.MUTED,
}

# Marca y color de cada tipo de cambio en la lista de archivos.
FILE_MARKS = {
    ChangeKind.CONFLICT: ("!", theme.ERROR),
    ChangeKind.MODIFIED: ("M", theme.WARNING),
    ChangeKind.NEW: ("+", theme.SUCCESS),
    ChangeKind.DELETED: ("-", theme.ERROR),
    ChangeKind.RENAMED: ("R", theme.SECONDARY),
}

# Orden en que se listan los archivos: primero lo que más urge.
_KIND_ORDER = list(FILE_MARKS)

# Ancho de la zona de flechas entre las dos cajas del mapa.
_ARROW_WIDTH = 12
_MIN_BOX = 6
_MAX_BOX = 28


def status_body(status: RepoStatus, now: float, *, width: int = 60, max_files: int = 10) -> Text:
    """Todo el contenido del panel de git para un repo."""
    text = Text()
    text.append_text(_styled(explain.explain_branch(status), status.branch or status.short_oid))
    text.append("\n\n")

    text.append_text(_styled(explain.explain_changes(status)))
    for note in explain.explain_notes(status):
        text.append("\n")
        text.append_text(_styled(note))
    if status.files:
        text.append("\n")
        text.append_text(file_list(status.files, max_files=max_files, width=width))

    text.append("\n\n")
    text.append_text(_styled(explain.explain_sync(status)))
    diagram = sync_map(status, width=width)
    if diagram is not None:
        text.append("\n\n")
        text.append_text(diagram)
    duration = short_duration(now - status.last_fetch) if status.last_fetch else None
    fetch = explain.explain_fetch(status, now, duration)
    if fetch is not None:
        text.append("\n")
        text.append_text(_styled(fetch))
    return text


def _styled(line: explain.Line, highlight: str | None = None) -> Text:
    """Frase con el color de su tono; ``highlight`` resalta una palabra (la rama)."""
    text = Text(line.text, style=TONE_STYLES[line.tone])
    if highlight:
        start = line.text.find(highlight)
        if start >= 0:
            text.stylize(f"bold {theme.ACCENT}", start, start + len(highlight))
    return text


def file_list(files: tuple[FileChange, ...], *, max_files: int = 10, width: int = 60) -> Text:
    """Lista de archivos con su marca: ``M`` cambiado, ``+`` nuevo, ``-`` borrado..."""
    ordered = sorted(files, key=lambda f: (_KIND_ORDER.index(f.kind), f.path.casefold()))
    text = Text()
    for index, change in enumerate(ordered[:max_files]):
        if index:
            text.append("\n")
        mark, color = FILE_MARKS[change.kind]
        path = change.path
        if change.orig_path:
            path = f"{change.orig_path} → {change.path}"
        room = max(8, width - 5)
        if len(path) > room:
            path = "…" + path[-(room - 1) :]
        text.append(f"  {mark}  ", style=f"bold {color}")
        text.append(path, style=theme.FOREGROUND)
    hidden = len(ordered) - max_files
    if hidden > 0:
        text.append("\n     " + t("git.files.more", n=hidden), style=theme.MUTED)
    return text


# ── Mapa tu compu ↔ remoto ──────────────────────────────────────


def sync_map(status: RepoStatus, *, width: int = 60) -> Text | None:
    """Dos cajas (tu compu y el remoto) unidas por flechas con los commits
    sin subir (↑) y sin bajar (↓). ``None`` si el repo no tiene remoto."""
    if not status.remotes:
        return None

    local_lines = [
        status.branch or t("map.no_branch"),
        status.short_oid or t("map.no_commits"),
    ]
    remote_exists = status.upstream is not None and not status.upstream_gone
    if status.upstream is not None:
        remote_title = status.remote_name or t("map.remote")
        remote_lines = [
            status.remote_branch or "",
            (status.upstream_oid or "") if remote_exists else t("map.gone"),
        ]
    else:
        remote_title = "origin" if "origin" in status.remotes else status.remotes[0]
        remote_lines = [status.branch or "—", t("map.missing")]

    box_width = max(_MIN_BOX, min(_MAX_BOX, (width - _ARROW_WIDTH - 2) // 2 - 4))
    local_title = t("map.local")
    inner = max(len(local_title) + 1, len(remote_title) + 1, *map(len, local_lines + remote_lines))
    inner = max(_MIN_BOX, min(inner, box_width))

    left = _box(local_title, local_lines, inner, theme.ACCENT, theme.FOREGROUND)
    remote_color = theme.SECONDARY if remote_exists else theme.MUTED
    right = _box(
        remote_title,
        remote_lines,
        inner,
        remote_color,
        theme.FOREGROUND if remote_exists else theme.MUTED,
    )
    ahead = status.ahead if remote_exists else None
    behind = status.behind if remote_exists else None
    middle = [
        Text(" " * _ARROW_WIDTH),
        _arrow(ahead, up=True),
        _arrow(behind, up=False),
        Text(" " * _ARROW_WIDTH),
    ]

    diagram = Text(no_wrap=True)
    for index in range(4):
        if index:
            diagram.append("\n")
        diagram.append_text(left[index])
        diagram.append(" ")
        diagram.append_text(middle[index])
        diagram.append(" ")
        diagram.append_text(right[index])
    return diagram


def _box(title: str, lines: list[str], inner: int, border: str, content: str) -> list[Text]:
    """Caja de 4 líneas con el título en el borde superior."""
    title = _fit(title, inner - 1)
    top = Text()
    top.append("╭─ ", style=border)
    top.append(title, style=f"bold {border}")
    top.append(" " + "─" * (inner - len(title) - 1) + "╮", style=border)
    rows = [top]
    for index, line in enumerate(lines):
        row = Text()
        row.append("│ ", style=border)
        # La primera línea (la rama) va resaltada; la segunda (el commit), tenue.
        style = f"bold {content}" if index == 0 else theme.MUTED
        row.append(_fit(line, inner).ljust(inner), style=style)
        row.append(" │", style=border)
        rows.append(row)
    rows.append(Text("╰" + "─" * (inner + 2) + "╯", style=border))
    return rows


def _arrow(count: int | None, *, up: bool) -> Text:
    """Flecha hacia el remoto (↑ subir) o hacia la compu (↓ bajar)."""
    if count is None:
        return Text("·" * _ARROW_WIDTH, style=theme.BORDER)
    if count == 0:
        line = "─" * (_ARROW_WIDTH - 1)
        return Text(line + "►" if up else "◄" + line, style=theme.BORDER)
    label = f" {count} {'↑' if up else '↓'} "
    fill = max(2, _ARROW_WIDTH - 1 - len(label))
    before, after = fill // 2, fill - fill // 2
    body = "─" * before + label + "─" * after
    color = theme.ACCENT if up else theme.WARNING
    return Text(body + "►" if up else "◄" + body, style=f"bold {color}")


def _fit(value: str, room: int) -> str:
    return value if len(value) <= room else value[: max(1, room - 1)] + "…"
