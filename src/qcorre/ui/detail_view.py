"""Texto del panel de detalle de un proceso (se abre con Enter).

Responde a "¿qué es exactamente este proceso?": comando completo, carpeta,
PID, padre y hora de inicio. Sin esto, una fila como ``python -c`` no se
puede identificar.
"""

from __future__ import annotations

from datetime import datetime

from rich.text import Text

from qcorre.i18n import t
from qcorre.models import DevProcess, ProcessInfo, Project
from qcorre.ui import theme
from qcorre.ui.format import orphan_notes, short_duration
from qcorre.ui.styles import heading

# Largo máximo del comando de cada miembro en la lista de procesos incluidos.
_MEMBER_COMMAND_WIDTH = 68


def command_line(info: ProcessInfo) -> str:
    """Línea de comandos legible; pone comillas a los argumentos con espacios."""
    if not info.cmdline:
        return ""
    return " ".join(f'"{arg}"' if (" " in arg or not arg) else arg for arg in info.cmdline)


def detail_body(process: DevProcess, project: Project | None, now: float) -> Text:
    """Cuerpo del panel de detalle."""
    info = process.info
    unknown = t("detail.denied") if info.access_denied else t("detail.unknown")
    labels = [
        t(f"detail.{key}")
        for key in ("command", "cwd", "project", "pid", "parent", "started", "ports", "status")
    ]
    width = max(len(label) for label in labels) + 2

    text = Text()

    def field(key: str, value: str | None, style: str = theme.FOREGROUND) -> None:
        if text:
            text.append("\n")
        text.append(t(f"detail.{key}").ljust(width), style=theme.MUTED)
        # Los valores largos (el comando) continúan alineados bajo sí mismos.
        lines = (value or unknown).splitlines() or [unknown]
        missing = value is None or value == ""
        for index, line in enumerate(lines):
            if index:
                text.append("\n" + " " * width)
            text.append(line, style=f"italic {theme.MUTED}" if missing else style)

    # El comando suele ser largo: va en su propia línea, a todo el ancho.
    command = command_line(info)
    text.append(t("detail.command") + "\n", style=theme.MUTED)
    text.append(command or unknown, style=theme.FOREGROUND if command else f"italic {theme.MUTED}")
    text.append("\n")
    field("cwd", info.cwd)
    if project is not None:
        field("project", f"{project.name}  ({project.path})")
    else:
        field("project", t("detail.no_project"), theme.WARNING)
    field("pid", str(info.pid))
    field("parent", *_parent(process))
    field("started", _started(info, now))
    ports = " ".join(f":{port}" for port in process.ports)
    field("ports", ports or t("detail.none"), theme.SECONDARY if ports else theme.MUTED)

    notes = orphan_notes(process, now)
    if info.access_denied:
        notes.append(t("tag.denied"))
    if notes:
        field("status", " · ".join(notes), theme.WARNING)

    if len(process.members) > 1:
        text.append("\n\n")
        text.append_text(heading(t("detail.members", n=len(process.members))))
        pid_width = max(len(str(m.pid)) for m in process.members)
        for member in process.members:
            command = command_line(member) or member.name
            if len(command) > _MEMBER_COMMAND_WIDTH:
                command = "…" + command[-(_MEMBER_COMMAND_WIDTH - 1) :]
            text.append(f"\n  {str(member.pid).rjust(pid_width)}  ", style=theme.MUTED)
            text.append(command, style=theme.FOREGROUND)
    return text


def _parent(process: DevProcess) -> tuple[str | None, str]:
    """Texto y color del campo "Padre"."""
    ppid = process.info.ppid
    if ppid is None:
        return None, theme.FOREGROUND
    if process.parent_name is None:
        return t("detail.parent_gone", pid=ppid), theme.WARNING
    return f"{process.parent_name}  (pid {ppid})", theme.FOREGROUND


def _started(info: ProcessInfo, now: float) -> str | None:
    if info.create_time <= 0:
        return None
    moment = datetime.fromtimestamp(info.create_time).strftime("%Y-%m-%d %H:%M:%S")
    ago = t("detail.ago", time=short_duration(now - info.create_time))
    return f"{moment}  ({ago})"
