"""Textos del diálogo "matar procesos": qué se va a cerrar, exactamente."""

from __future__ import annotations

import os
from collections.abc import Sequence

from rich.text import Text

from qcorre.collectors.killer import KillResult, Victim
from qcorre.i18n import t
from qcorre.models import DevProcess, ProcessKind
from qcorre.ui import theme
from qcorre.ui.styles import heading

# Una fila del panel y los procesos del sistema que se cerrarían con ella.
KillGroup = tuple[DevProcess, list[Victim]]


def kill_body(groups: Sequence[KillGroup], *, windows: bool | None = None) -> Text:
    """Cuerpo del diálogo de confirmación."""
    if windows is None:
        windows = os.name == "nt"
    total = sum(len(victims) for _, victims in groups)
    ports = sorted({port for dev, _ in groups for port in dev.ports})

    text = Text()
    text.append_text(heading(t("confirm.what")))
    text.append("\n")
    bullets = [t("kill.summary", n=total)]
    if ports:
        bullets.append(t("kill.ports", n=len(ports), ports=" ".join(f":{p}" for p in ports)))
    bullets.append(t("kill.method.windows" if windows else "kill.method.posix"))
    for bullet in bullets:
        text.append("  • ", style=theme.MUTED)
        text.append(bullet + "\n", style=theme.FOREGROUND)
    databases = [dev.label for dev, _ in groups if dev.kind is ProcessKind.DATABASE]
    if databases:
        # Con una sola fila en el diálogo se habla en singular ("Es una base
        # de datos"); con varias se dice cuáles lo son.
        count = 1 if len(groups) == 1 else 2
        warning = t("kill.database_warning", n=count, names=", ".join(databases))
        text.append("  • ", style=theme.WARNING)
        text.append(warning + "\n", style=theme.WARNING)
    if any(dev.access_denied for dev, _ in groups):
        text.append("  • ", style=theme.WARNING)
        text.append(t("kill.denied_warning") + "\n", style=theme.WARNING)

    name_width = max((len(v.name) for _, victims in groups for v in victims), default=0)
    for dev, victims in groups:
        text.append("\n● ", style=theme.ERROR)
        text.append(dev.label, style=f"bold {theme.FOREGROUND}")
        if dev.ports:
            text.append("  " + " ".join(f":{p}" for p in dev.ports), style=theme.SECONDARY)
        for victim in victims:
            text.append("\n    " + victim.name.ljust(name_width), style=theme.MUTED)
            text.append(f"  pid {victim.pid}", style=theme.MUTED)
    return text


def result_message(result: KillResult) -> tuple[str, str]:
    """Mensaje y severidad (``information`` / ``warning``) tras cerrar."""
    parts: list[str] = []
    if result.closed:
        parts.append(t("kill.done", n=result.closed))
    if result.denied:
        parts.append(t("kill.denied", n=len(result.denied)))
    if result.survivors:
        parts.append(t("kill.survived", n=len(result.survivors)))
    if not parts:
        parts.append(t("kill.gone"))
    return ". ".join(parts), "warning" if result.failed else "information"
