"""Textos de los diálogos de las acciones de git.

Antes de cada acción se muestra: qué va a pasar, el respaldo que se creará (si
la acción es riesgosa) y el comando exacto de git.
"""

from __future__ import annotations

from rich.text import Text

from qcorre.git.actions import ActionPlan, ActionResult, explain_failure
from qcorre.i18n import t
from qcorre.ui import theme


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
        text.append("  " + result.backup.ref, style=theme.SUCCESS)
    return text
