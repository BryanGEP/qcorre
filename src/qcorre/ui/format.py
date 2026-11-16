"""Textos cortos para mostrar tiempos y motivos de huérfano."""

from __future__ import annotations

from qcorre.i18n import t
from qcorre.models import DevProcess, OrphanReason

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR


def short_duration(seconds: float) -> str:
    """Duración compacta, igual en todos los idiomas: ``41m``, ``2h 14m``, ``3d 4h``."""
    seconds = max(0, int(seconds))
    if seconds < MINUTE:
        return "<1m"
    if seconds < HOUR:
        return f"{seconds // MINUTE}m"
    if seconds < DAY:
        return f"{seconds // HOUR}h {seconds % HOUR // MINUTE:02d}m"
    return f"{seconds // DAY}d {seconds % DAY // HOUR}h"


def running_for(seconds: float) -> str:
    """Frase humana para un proceso que lleva mucho corriendo: "lleva 3 días"."""
    seconds = max(0, int(seconds))
    if seconds >= DAY:
        return t("orphan.days", n=seconds // DAY)
    if seconds >= HOUR:
        return t("orphan.hours", n=seconds // HOUR)
    return t("orphan.minutes", n=max(1, seconds // MINUTE))


def orphan_notes(process: DevProcess, now: float) -> list[str]:
    """Motivos visibles de por qué un proceso está marcado como huérfano.

    "Sin proyecto" no se incluye: esos procesos ya se muestran dentro del
    grupo de huérfanos, que lo dice por sí mismo.
    """
    notes: list[str] = []
    if OrphanReason.LONG_RUNNING in process.orphan_reasons:
        notes.append(running_for(process.uptime(now)))
    if OrphanReason.PARENT_GONE in process.orphan_reasons:
        notes.append(t("orphan.parent_gone"))
    return notes
