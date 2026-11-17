"""Textos de la vista de ramas y del menú de deshacer."""

from __future__ import annotations

from rich.text import Text

from qcorre.git.actions import operation_label
from qcorre.git.backup import Backup
from qcorre.git.branches import Branch, BranchList
from qcorre.git.parse import RepoStatus
from qcorre.i18n import t
from qcorre.ui import theme
from qcorre.ui.format import short_duration
from qcorre.ui.picker import Choice

# Prefijos de los ids de las opciones.
LOCAL = "local:"
REMOTE = "remote:"
UNDO_COMMIT = "undo-commit"
DISCARD = "discard"
BACKUP = "backup:"


# ── Ramas ───────────────────────────────────────────────────────


def branch_choices(branches: BranchList, now: float) -> list[Choice]:
    """Líneas de la vista de ramas: las locales y las que solo están en el remoto."""
    width = max((len(b.name) for b in branches.local), default=0)
    choices: list[Choice] = [_heading(t("branches.local"))]
    for branch in branches.local:
        choices.append(Choice(_local_line(branch, width), LOCAL + branch.name))

    if branches.remote_only:
        if branches.last_sync:
            note = t("branches.remote.asof", time=short_duration(now - branches.last_sync))
        else:
            note = t("branches.remote.never")
        choices.append(_heading(f"{t('branches.remote')}  ·  {note}"))
        for branch in branches.remote_only:
            line = Text(no_wrap=True, overflow="ellipsis")
            line.append("  " + branch.full_remote, style=theme.SECONDARY)
            choices.append(Choice(line, REMOTE + branch.full_remote))
    return choices


def find_branch(branches: BranchList, choice_id: str) -> Branch | None:
    """La rama que corresponde al id de una opción."""
    if choice_id.startswith(LOCAL):
        name = choice_id[len(LOCAL) :]
        return next((b for b in branches.local if b.name == name), None)
    if choice_id.startswith(REMOTE):
        full = choice_id[len(REMOTE) :]
        return next((b for b in branches.remote_only if b.full_remote == full), None)
    return None


def _heading(label: str) -> Choice:
    return Choice(Text(label, style=f"bold {theme.MUTED}"))


def _local_line(branch: Branch, width: int) -> Text:
    line = Text(no_wrap=True, overflow="ellipsis")
    if branch.current:
        line.append("● ", style=theme.SUCCESS)
        line.append(branch.name.ljust(width), style=f"bold {theme.ACCENT}")
        line.append("  " + t("branches.current"), style=theme.SUCCESS)
    else:
        line.append("  " + branch.name.ljust(width), style=theme.FOREGROUND)

    if branch.gone:
        line.append("  " + t("branches.gone"), style=theme.WARNING)
        note = t("branches.merged") if branch.merged else t("branches.unmerged")
        line.append(" · " + note, style=theme.MUTED if branch.merged else theme.WARNING)
    elif branch.upstream is None:
        line.append("  " + t("branches.local_only"), style=theme.MUTED)
    elif not branch.ahead and not branch.behind:
        line.append("  " + t("branches.even"), style=theme.MUTED)
    else:
        if branch.ahead:
            line.append(f"  {branch.ahead} ↑", style=f"bold {theme.ACCENT}")
        if branch.behind:
            line.append(f"  {branch.behind} ↓", style=f"bold {theme.WARNING}")
    return line


# ── Deshacer ────────────────────────────────────────────────────


def undo_choices(status: RepoStatus, backups: list[Backup], now: float) -> list[Choice]:
    """Líneas del menú de deshacer: último commit, cambios sin guardar y respaldos."""
    choices: list[Choice] = [_heading(t("undo.actions"))]

    commit = Text(no_wrap=True, overflow="ellipsis")
    commit.append("  " + t("undo.commit"), style=theme.FOREGROUND)
    if status.has_commits and status.head_subject:
        commit.append(f'  "{status.head_subject}"', style=theme.MUTED)
    else:
        commit.append("  " + t("undo.commit.none"), style=theme.MUTED)
    choices.append(Choice(commit, UNDO_COMMIT))

    tracked = sum(1 for f in status.files if not f.untracked)
    discard = Text(no_wrap=True, overflow="ellipsis")
    discard.append("  " + t("undo.discard"), style=theme.FOREGROUND)
    detail = t("undo.discard.count", n=tracked) if tracked else t("undo.discard.none")
    discard.append("  " + detail, style=theme.MUTED)
    choices.append(Choice(discard, DISCARD))

    choices.append(_heading(t("undo.backups")))
    if not backups:
        choices.append(Choice(Text("  " + t("undo.backups.none"), style=theme.MUTED)))
    for backup in backups:
        choices.append(Choice(_backup_line(backup, now), BACKUP + backup.name))
    return choices


def find_backup(backups: list[Backup], choice_id: str) -> Backup | None:
    name = choice_id[len(BACKUP) :] if choice_id.startswith(BACKUP) else None
    return next((b for b in backups if b.name == name), None)


def backup_age(backup: Backup, now: float) -> str:
    """"hace 2h 05m" (o vacío si el respaldo no tiene fecha legible)."""
    if backup.created <= 0:
        return ""
    return t("detail.ago", time=short_duration(now - backup.created))


def _backup_line(backup: Backup, now: float) -> Text:
    line = Text(no_wrap=True, overflow="ellipsis")
    line.append("  " + (backup_age(backup, now) or backup.name), style=theme.FOREGROUND)
    operation = operation_label(backup.operation)
    line.append("  " + t("undo.backup.item", operation=operation), style=theme.MUTED)
    if backup.branch:
        line.append(" · " + t("undo.backup.branch", branch=backup.branch), style=theme.SECONDARY)
    line.append(" · " + backup.oid[:7], style=theme.MUTED)
    if backup.changes_ref:
        line.append(" · " + t("undo.backup.changes"), style=theme.SUCCESS)
    return line
