"""Explica el estado de un repo en lenguaje humano.

Cada función devuelve una ``Line``: la frase ya traducida al idioma activo y
un tono, para que la interfaz elija el color. No hay jerga: se habla de
"cambios sin guardar en un commit", "subir" y "bajar".
"""

from __future__ import annotations

from dataclasses import dataclass

from qcorre.git.parse import RepoStatus
from qcorre.i18n import t

# Tonos posibles de una frase.
GOOD = "good"  # todo en orden
INFO = "info"  # hay algo que saber
WARN = "warn"  # hay algo que atender
MUTED = "muted"  # nota secundaria


@dataclass(frozen=True)
class Line:
    text: str
    tone: str = INFO


def join_list(items: list[str]) -> str:
    """``["a", "b", "c"]`` -> ``"a, b y c"`` (o "and" en inglés)."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + t("list.and") + items[-1]


def explain_branch(status: RepoStatus) -> Line:
    """En qué rama está el usuario."""
    if status.detached:
        return Line(t("git.branch.detached", oid=status.short_oid or "?"), WARN)
    if not status.has_commits:
        return Line(t("git.branch.unborn", branch=status.branch), INFO)
    return Line(t("git.branch.on", branch=status.branch), INFO)


def explain_changes(status: RepoStatus) -> Line:
    """Qué cambios hay sin guardar en un commit."""
    if status.is_clean:
        return Line(t("git.changes.clean"), GOOD)
    changed, new, conflicts = len(status.changed), len(status.new), len(status.conflicts)
    parts: list[str] = []
    if changed:
        parts.append(t("git.changes.modified", n=changed))
    if new:
        # Si solo hay archivos nuevos, la frase aclara que no están en un commit.
        parts.append(t("git.changes.new" if changed else "git.changes.new_only", n=new))
    if conflicts:
        parts.append(t("git.changes.conflict", n=conflicts))
    return Line(t("git.changes.have", list=join_list(parts)), WARN if conflicts else INFO)


def explain_notes(status: RepoStatus) -> list[Line]:
    """Notas secundarias sobre los cambios."""
    notes: list[Line] = []
    if status.conflicts:
        notes.append(Line(t("git.conflicts.note"), WARN))
    staged = len(status.staged)
    if staged and staged < len(status.files):
        notes.append(Line(t("git.changes.staged", n=staged), MUTED))
    return notes


def explain_sync(status: RepoStatus) -> Line:
    """Cómo está la compu respecto al remoto."""
    if not status.remotes:
        return Line(t("git.sync.no_remote"), MUTED)
    if not status.has_commits:
        return Line(t("git.sync.unborn"), MUTED)
    if status.detached:
        return Line(t("git.sync.detached"), MUTED)
    if status.upstream is None:
        return Line(t("git.sync.no_upstream", branch=status.branch), INFO)
    if status.upstream_gone:
        return Line(t("git.sync.gone", upstream=status.upstream), WARN)

    remote = status.remote_name or status.upstream
    ahead, behind = status.ahead or 0, status.behind or 0
    if ahead and behind:
        return Line(
            t(
                "git.sync.diverged",
                remote=remote,
                push=t("git.sync.to_push", n=ahead),
                pull=t("git.sync.to_pull", n=behind),
            ),
            WARN,
        )
    if ahead:
        return Line(t("git.sync.ahead", what=t("git.sync.to_push", n=ahead)), INFO)
    if behind:
        return Line(t("git.sync.behind", n=behind, remote=remote), INFO)
    return Line(t("git.sync.even", remote=remote), GOOD)


def explain_fetch(status: RepoStatus, now: float, duration: str | None = None) -> Line | None:
    """De cuándo son los datos del remoto.

    Los conteos de commits sin subir / sin bajar valen para la última vez que
    se consultó el remoto; decirlo evita que el usuario crea que está al día
    cuando en realidad hace días que no consulta. ``duration`` es el tiempo
    transcurrido ya formateado (lo pone la interfaz).
    """
    if not status.remotes or status.upstream is None or status.upstream_gone:
        return None
    if status.last_fetch is None:
        return Line(t("git.fetch.never"), MUTED)
    return Line(t("git.fetch.when", time=duration or ""), MUTED)
