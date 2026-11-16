"""Acciones de git: commit, push, pull y actualizar del remoto.

Cada acción se prepara primero como un ``ActionPlan``: datos puros que dicen
qué va a pasar y qué comandos exactos se van a correr. La interfaz muestra el
plan y, solo si el usuario confirma, ``execute`` lo ejecuta tal cual. Así la
vista previa y lo que se hace salen del mismo objeto y no pueden diferir.

Fuera de alcance en v1: merge, rebase y push forzado. Si una acción los
necesitaría, el plan sale bloqueado con la explicación.
"""

from __future__ import annotations

from dataclasses import dataclass

from qcorre.git.backup import Backup, backup_ref, create_backup
from qcorre.git.parse import RepoStatus
from qcorre.git.runner import GitError, GitResult, GitRunner, format_command
from qcorre.i18n import t

# Los comandos que hablan con el remoto pueden tardar bastante más.
NETWORK_TIMEOUT = 120.0

COMMIT = "commit"
PUSH = "push"
PULL = "pull"
FETCH = "fetch"


@dataclass(frozen=True)
class ActionPlan:
    """Lo que una acción va a hacer, listo para mostrar y para ejecutar."""

    action: str
    title: str
    effects: tuple[str, ...] = ()  # qué va a pasar, en lenguaje humano
    commands: tuple[tuple[str, ...], ...] = ()  # argumentos de cada `git ...`
    network: bool = False  # se conecta al remoto
    backup_ref: str | None = None  # respaldo que se crea antes (acciones riesgosas)
    blocked: str | None = None  # por qué no se puede hacer ahora

    @property
    def command_lines(self) -> tuple[str, ...]:
        """Los comandos tal como los teclearía el usuario."""
        return tuple(format_command(args) for args in self.commands)


@dataclass(frozen=True)
class ActionResult:
    """Qué pasó al ejecutar un plan."""

    plan: ActionPlan
    steps: tuple[GitResult, ...] = ()
    backup: Backup | None = None
    error: GitError | None = None  # git no pudo ni arrancar (o falló el respaldo)

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.steps) and all(s.ok for s in self.steps)

    @property
    def failed_step(self) -> GitResult | None:
        return next((step for step in self.steps if not step.ok), None)

    @property
    def output(self) -> str:
        """Lo que respondió git en el paso que falló (o en el último)."""
        if self.error is not None:
            return self.error.detail
        step = self.failed_step or (self.steps[-1] if self.steps else None)
        if step is None:
            return ""
        return (step.stderr.strip() + "\n" + step.stdout.strip()).strip()


# ── Planes ──────────────────────────────────────────────────────


def plan_commit(status: RepoStatus, message: str) -> ActionPlan:
    """Guarda *todos* los cambios (también los archivos nuevos) en un commit."""
    title = t("action.commit.title")
    if status.conflicts:
        return _blocked(COMMIT, title, t("action.blocked.conflicts"))
    if status.is_clean:
        return _blocked(COMMIT, title, t("action.commit.blocked.clean"))
    message = message.strip()

    effects = [t("action.commit.effect.files", n=len(status.files))]
    if status.branch:
        effects.append(t("action.commit.effect.branch", branch=status.branch))
    else:
        effects.append(t("action.commit.effect.detached"))
    effects.append(t("action.commit.effect.local"))
    return ActionPlan(
        action=COMMIT,
        title=title,
        effects=tuple(effects),
        commands=(("add", "-A"), ("commit", "-m", message)),
    )


def plan_push(status: RepoStatus) -> ActionPlan:
    """Sube los commits de la rama actual al remoto (nunca a la fuerza)."""
    title = t("action.push.title")
    blocked = _needs_branch(status)
    if blocked:
        return _blocked(PUSH, title, blocked)
    remote = status.push_remote
    assert remote is not None and status.branch is not None
    network = _network_effect(status, remote)

    if status.upstream is None or status.upstream_gone:
        # La rama no existe en el remoto: se crea y queda enlazada.
        return ActionPlan(
            action=PUSH,
            title=title,
            effects=(
                t("action.push.effect.new", branch=status.branch, remote=remote),
                t("action.push.effect.linked"),
                network,
            ),
            commands=(("push", "-u", remote, status.branch),),
            network=True,
        )
    if status.behind:
        return _blocked(PUSH, title, t("action.push.blocked.behind", n=status.behind, remote=remote))
    if not status.ahead:
        return _blocked(PUSH, title, t("action.push.blocked.nothing", remote=remote))
    return ActionPlan(
        action=PUSH,
        title=title,
        effects=(
            t("action.push.effect.commits", n=status.ahead, upstream=status.upstream),
            network,
        ),
        commands=(("push", remote, f"{status.branch}:{status.remote_branch}"),)
        if status.remote_branch != status.branch
        else (("push", remote, status.branch),),
        network=True,
    )


def plan_pull(status: RepoStatus, now: float | None = None) -> ActionPlan:
    """Baja los commits del remoto, solo si se puede avanzar sin mezclar."""
    title = t("action.pull.title")
    blocked = _needs_branch(status)
    if blocked:
        return _blocked(PULL, title, blocked)
    if status.upstream is None:
        return _blocked(PULL, title, t("action.pull.blocked.no_upstream", branch=status.branch))
    if status.upstream_gone:
        return _blocked(PULL, title, t("action.pull.blocked.gone", upstream=status.upstream))
    if status.conflicts:
        return _blocked(PULL, title, t("action.blocked.conflicts"))
    remote = status.remote_name
    assert remote is not None and status.remote_branch is not None
    if status.ahead and status.behind:
        return _blocked(PULL, title, t("action.pull.blocked.diverged", remote=remote))

    effects = []
    if status.behind:
        effects.append(t("action.pull.effect.commits", n=status.behind, upstream=status.upstream))
    else:
        effects.append(t("action.pull.effect.maybe_nothing"))
    effects.append(t("action.pull.effect.ff_only"))
    if not status.is_clean:
        effects.append(t("action.pull.effect.changes", n=len(status.files)))
    effects.append(_network_effect(status, remote))
    return ActionPlan(
        action=PULL,
        title=title,
        effects=tuple(effects),
        commands=(("pull", "--ff-only", remote, status.remote_branch),),
        network=True,
        backup_ref=backup_ref(PULL, now),
    )


def plan_fetch(status: RepoStatus) -> ActionPlan:
    """Pregunta al remoto qué hay de nuevo, sin cambiar ningún archivo."""
    title = t("action.fetch.title")
    remote = status.push_remote
    if remote is None:
        return _blocked(FETCH, title, t("action.blocked.no_remote"))
    return ActionPlan(
        action=FETCH,
        title=title,
        effects=(
            t("action.fetch.effect.ask", remote=remote),
            t("action.fetch.effect.safe"),
            _network_effect(status, remote),
        ),
        commands=(("fetch", "--prune", remote),),
        network=True,
    )


def _blocked(action: str, title: str, reason: str) -> ActionPlan:
    return ActionPlan(action=action, title=title, blocked=reason)


def _needs_branch(status: RepoStatus) -> str | None:
    """Motivos comunes por los que no se puede subir ni bajar."""
    if not status.remotes:
        return t("action.blocked.no_remote")
    if not status.has_commits:
        return t("action.blocked.no_commits")
    if status.detached:
        return t("action.blocked.detached")
    return None


def _network_effect(status: RepoStatus, remote: str) -> str:
    """Aviso de que la acción se conecta a la red, y a dónde."""
    where = status.remote_url or remote
    return t("action.effect.network", where=where)


# ── Ejecución ───────────────────────────────────────────────────


def execute(plan: ActionPlan, runner: GitRunner) -> ActionResult:
    """Ejecuta un plan: primero el respaldo (si lo pide) y luego sus comandos.

    Se detiene en el primer comando que falle. Nunca lanza: los errores
    vuelven dentro del ``ActionResult``.
    """
    if plan.blocked or not plan.commands:
        return ActionResult(plan, error=GitError("failed", plan.blocked or ""))
    backup: Backup | None = None
    steps: list[GitResult] = []
    timeout = NETWORK_TIMEOUT if plan.network else None
    try:
        if plan.backup_ref:
            backup = create_backup(runner, plan.backup_ref)
        for args in plan.commands:
            step = runner.run(*args, timeout=timeout)
            steps.append(step)
            if not step.ok:
                break
    except GitError as error:
        return ActionResult(plan, tuple(steps), backup, error)
    return ActionResult(plan, tuple(steps), backup)


# ── Errores explicados ──────────────────────────────────────────

# (fragmentos del mensaje de git, clave de traducción). Gana el primero.
_KNOWN_FAILURES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("not possible to fast-forward", "diverging branches"), "failure.diverged"),
    (("would be overwritten",), "failure.overwrite"),
    (("fetch first", "non-fast-forward", "[rejected]"), "failure.rejected"),
    (
        (
            "authentication failed",
            "could not read username",
            "permission denied",
            "terminal prompts disabled",
            "403",
        ),
        "failure.auth",
    ),
    (
        (
            "could not resolve host",
            "unable to access",
            "connection timed out",
            "could not read from remote",
            "network is unreachable",
        ),
        "failure.network",
    ),
    (("please tell me who you are", "user.email", "user.name"), "failure.identity"),
    (("nothing to commit",), "failure.nothing_to_commit"),
    (("index.lock",), "failure.locked"),
)


def explain_failure(result: ActionResult) -> str:
    """Explica en lenguaje humano por qué falló una acción."""
    if result.error is not None and result.error.reason in ("not_installed", "timeout"):
        return t(f"git.error.{result.error.reason}")
    output = result.output.lower()
    for fragments, key in _KNOWN_FAILURES:
        if any(fragment in output for fragment in fragments):
            return t(key)
    return t("failure.unknown")


def success_message(result: ActionResult) -> str:
    """Frase corta para avisar que la acción salió bien."""
    return t(f"action.{result.plan.action}.done")

