"""Textos de los diálogos de las acciones de git.

Antes de cada acción se muestra: qué va a pasar, el respaldo que se creará (si
la acción es riesgosa) y el comando exacto de git.
"""

from __future__ import annotations

from rich.text import Text

from qcorre.git.actions import ActionPlan, ActionResult, explain_failure
from qcorre.git.parse import RepoStatus
from qcorre.git.sensitive import sensitive_files
from qcorre.i18n import t
from qcorre.ui import theme
from qcorre.ui.git_view import file_list


def plan_body(plan: ActionPlan) -> Text:
    """Vista previa de una acción: efectos, respaldo y comandos."""
    text = Text()
    text.append(t("confirm.what") + "\n", style=f"bold {theme.FOREGROUND}")
    for effect in plan.effects:
        text.append("  • ", style=theme.MUTED)
        text.append(effect + "\n", style=theme.FOREGROUND)

    if plan.backup_ref:
        text.append("\n" + t("action.backup") + "\n", style=f"bold {theme.SUCCESS}")
        text.append("  " + plan.backup_ref + "\n", style=theme.SUCCESS)
        text.append("  " + t("action.backup.note") + "\n", style=theme.MUTED)

    text.append("\n" + t("action.commands", n=len(plan.commands)) + "\n", style=theme.MUTED)
    text.append_text(command_lines(plan))
    return text


def command_lines(plan: ActionPlan) -> Text:
    """Los comandos de git, uno por línea, como en una terminal."""
    text = Text()
    for index, line in enumerate(plan.command_lines):
        if index:
            text.append("\n")
        text.append("  $ ", style=theme.MUTED)
        text.append(line, style=f"bold {theme.SECONDARY}")
    return text


def blocked_body(plan: ActionPlan) -> Text:
    """Explica por qué la acción no se puede hacer ahora."""
    text = Text()
    text.append(t("action.blocked.heading") + "\n\n", style=f"bold {theme.WARNING}")
    text.append(plan.blocked or "", style=theme.FOREGROUND)
    return text


def blocked_reason(plan: ActionPlan) -> Text:
    """Solo el motivo (para la vista previa mientras se escribe un nombre)."""
    return Text(plan.blocked or "", style=theme.WARNING)


def failure_body(result: ActionResult) -> Text:
    """Explica un fallo: en humano, y debajo lo que dijo git tal cual."""
    text = Text()
    text.append(explain_failure(result), style=theme.WARNING)
    step = result.failed_step
    if step is not None:
        text.append("\n\n" + t("action.failed.command") + "\n", style=theme.MUTED)
        text.append("  $ ", style=theme.MUTED)
        text.append(step.command, style=f"bold {theme.SECONDARY}")
    output = result.output
    if output:
        text.append("\n\n" + t("action.failed.output") + "\n", style=theme.MUTED)
        for line in output.splitlines()[-12:]:
            text.append("  " + line + "\n", style=theme.FOREGROUND)
    if result.backup is not None:
        text.append("\n" + t("action.failed.backup") + "\n", style=theme.MUTED)
        text.append("  " + result.backup.base, style=theme.SUCCESS)
    return text


def commit_body(status: RepoStatus, plan: ActionPlan, *, width: int = 70) -> Text:
    """Vista previa del commit: efectos, aviso de secretos, comandos y archivos.

    Lista *todos* los archivos que ``git add -A`` va a meter (la zona tiene
    scroll), para que nada entre al commit sin haberlo visto.
    """
    text = Text()
    text.append(t("confirm.what") + "\n", style=f"bold {theme.FOREGROUND}")
    for effect in plan.effects:
        text.append("  • ", style=theme.MUTED)
        text.append(effect + "\n", style=theme.FOREGROUND)

    risky = sensitive_files(status.files)
    if risky:
        text.append("\n⚠ " + t("commit.sensitive.title", n=len(risky)) + "\n", style=f"bold {theme.WARNING}")
        for change in risky:
            text.append("    " + change.path + "\n", style=theme.WARNING)
        text.append("  " + t("commit.sensitive.advice") + "\n", style=theme.WARNING)

    text.append("\n" + t("action.commands", n=len(plan.commands)) + "\n", style=theme.MUTED)
    text.append_text(command_lines(plan))

    text.append("\n\n" + t("commit.files", n=len(status.files)), style=theme.MUTED)
    if len(status.files) > 8:
        text.append("  ·  " + t("commit.scroll"), style=theme.MUTED)
    text.append("\n")
    text.append_text(file_list(status.files, max_files=None, width=width, collapsible=False))
    return text
