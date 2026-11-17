"""Acciones de git: commit, push, pull, ramas y deshacer.

Cada acción se prepara primero como un ``ActionPlan``: datos puros que dicen
qué va a pasar y qué comandos exactos se van a correr. La interfaz muestra el
plan y, solo si el usuario confirma, ``execute`` lo ejecuta tal cual. Así la
vista previa y lo que se hace salen del mismo objeto y no pueden diferir.

Las acciones que pueden hacer perder algo llevan ``backup_ref``: antes de
ejecutarlas se crea un respaldo (ver ``qcorre.git.backup``).

Fuera de alcance en v1: merge, rebase, push forzado y ``branch -D``. Si una
acción los necesitaría, el plan sale bloqueado con la explicación.
"""

from __future__ import annotations

from dataclasses import dataclass

from qcorre.git.backup import Backup, backup_ref, create_backup, delete_backup
from qcorre.git.branches import Branch
from qcorre.git.parse import RepoStatus
from qcorre.git.runner import GitError, GitResult, GitRunner, format_command
from qcorre.i18n import t

# Los comandos que hablan con el remoto pueden tardar bastante más.
NETWORK_TIMEOUT = 120.0

COMMIT = "commit"
PUSH = "push"
PULL = "pull"
FETCH = "fetch"
SWITCH = "switch"
NEW_BRANCH = "branch"
DELETE_BRANCH = "delete"
UNDO_COMMIT = "undo"
DISCARD = "discard"
RESTORE = "restore"

# Caracteres que git no admite en el nombre de una rama.
_FORBIDDEN_IN_BRANCH = set(" ~^:?*[\\\t")


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
    danger: bool = False  # la acción descarta o borra algo: el diálogo va en rojo

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
    unchanged: bool = False  # la rama quedó donde estaba y no había nada que respaldar

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


# ── Planes: commit ──────────────────────────────────────────────


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


# ── Planes: remoto ──────────────────────────────────────────────


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
        reason = t("action.push.blocked.behind", n=status.behind, remote=remote)
        return _blocked(PUSH, title, reason)
    if not status.ahead:
        return _blocked(PUSH, title, t("action.push.blocked.nothing", remote=remote))
    target = status.branch
    if status.remote_branch != status.branch:
        target = f"{status.branch}:{status.remote_branch}"
    return ActionPlan(
        action=PUSH,
        title=title,
        effects=(
            t("action.push.effect.commits", n=status.ahead, upstream=status.upstream),
            network,
        ),
        commands=(("push", remote, target),),
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


# ── Planes: ramas ───────────────────────────────────────────────


def plan_switch(status: RepoStatus, branch: Branch, now: float | None = None) -> ActionPlan:
    """Cambia a otra rama. Si solo existe en el remoto, crea la local que la sigue."""
    title = t("action.switch.title", branch=branch.name)
    if branch.current:
        return _blocked(SWITCH, title, t("action.switch.blocked.current", branch=branch.name))
    if status.conflicts:
        return _blocked(SWITCH, title, t("action.blocked.conflicts"))

    here = status.branch or status.short_oid or "?"
    effects = [t("action.switch.effect.move", origin=here, branch=branch.name)]
    if branch.remote_only:
        effects.append(
            t("action.switch.effect.track", branch=branch.name, upstream=branch.full_remote)
        )
        commands: tuple[tuple[str, ...], ...] = (
            ("switch", "-c", branch.name, "--track", branch.full_remote),
        )
    else:
        commands = (("switch", branch.name),)
    effects.append(t("action.switch.effect.files"))

    dirty = not status.is_clean
    if dirty:
        effects.append(t("action.switch.effect.changes", n=len(status.files)))
    return ActionPlan(
        action=SWITCH,
        title=title,
        effects=tuple(effects),
        commands=commands,
        # Solo hay algo que respaldar si hay cambios sin guardar (y commits).
        backup_ref=backup_ref(SWITCH, now) if dirty and status.has_commits else None,
    )


def branch_name_problem(name: str) -> str | None:
    """Por qué ``name`` no sirve como nombre de rama (o ``None`` si sirve)."""
    if not name:
        return t("action.branch.invalid.empty")
    if any(ch in _FORBIDDEN_IN_BRANCH or ord(ch) < 32 for ch in name):
        return t("action.branch.invalid.chars")
    bad_edges = name.startswith(("-", "/", ".")) or name.endswith(("/", ".", ".lock"))
    if bad_edges or ".." in name or "//" in name or "@{" in name or name == "@":
        return t("action.branch.invalid.format")
    return None


def plan_new_branch(status: RepoStatus, name: str) -> ActionPlan:
    """Crea una rama nueva desde donde estás y te cambia a ella."""
    name = name.strip()
    title = t("action.branch.title")
    problem = branch_name_problem(name)
    if problem:
        return _blocked(NEW_BRANCH, title, problem)

    here = status.branch or status.short_oid or "?"
    effects = [t("action.branch.effect.create", branch=name, origin=here)]
    if not status.is_clean:
        effects.append(t("action.branch.effect.changes", n=len(status.files)))
    effects.append(t("action.branch.effect.local"))
    return ActionPlan(
        action=NEW_BRANCH,
        title=title,
        effects=tuple(effects),
        commands=(("switch", "-c", name),),
    )


def plan_delete_branch(status: RepoStatus, branch: Branch) -> ActionPlan:
    """Borra una rama local ya mergeada cuya rama remota ya no existe.

    Se usa ``git branch -d``, que se niega a borrar trabajo sin mergear. Nunca
    se usa ``-D``.
    """
    title = t("action.delete.title", branch=branch.name)
    if branch.current:
        return _blocked(DELETE_BRANCH, title, t("action.delete.blocked.current"))
    if branch.remote_only:
        return _blocked(DELETE_BRANCH, title, t("action.delete.blocked.remote"))
    if not branch.gone:
        return _blocked(DELETE_BRANCH, title, t("action.delete.blocked.not_gone"))
    if not branch.merged:
        here = status.branch or status.short_oid or "?"
        return _blocked(
            DELETE_BRANCH, title, t("action.delete.blocked.unmerged", branch=branch.name, here=here)
        )
    return ActionPlan(
        action=DELETE_BRANCH,
        title=title,
        effects=(
            t("action.delete.effect.local", branch=branch.name),
            t("action.delete.effect.merged", here=status.branch or status.short_oid or "?"),
            t("action.delete.effect.safe"),
        ),
        commands=(("branch", "-d", branch.name),),
        danger=True,
    )


# ── Planes: deshacer ────────────────────────────────────────────


def plan_undo_commit(status: RepoStatus, now: float | None = None) -> ActionPlan:
    """Deshace el último commit conservando sus cambios como "sin guardar"."""
    title = t("action.undo.title")
    if not status.has_commits:
        return _blocked(UNDO_COMMIT, title, t("action.undo.blocked.no_commits"))
    if status.conflicts:
        return _blocked(UNDO_COMMIT, title, t("action.blocked.conflicts"))
    if not status.has_parent:
        return _blocked(UNDO_COMMIT, title, t("action.undo.blocked.first"))
    if status.upstream and not status.upstream_gone and not status.ahead:
        # Deshacer algo ya subido obligaría a reescribir el remoto (push forzado).
        return _blocked(UNDO_COMMIT, title, t("action.undo.blocked.pushed"))
    return ActionPlan(
        action=UNDO_COMMIT,
        title=title,
        effects=(
            t("action.undo.effect.commit", subject=status.head_subject or "", oid=status.short_oid),
            t("action.undo.effect.keep"),
            t("action.undo.effect.local"),
        ),
        commands=(("reset", "--soft", "HEAD~1"),),
        backup_ref=backup_ref(UNDO_COMMIT, now),
    )


def plan_discard(status: RepoStatus, now: float | None = None) -> ActionPlan:
    """Descarta los cambios sin guardar: todo vuelve al último commit."""
    title = t("action.discard.title")
    if not status.has_commits:
        return _blocked(DISCARD, title, t("action.undo.blocked.no_commits"))
    tracked = [f for f in status.files if not f.untracked]
    untracked = [f for f in status.files if f.untracked]
    if not tracked:
        return _blocked(DISCARD, title, t("action.discard.blocked.nothing"))

    effects = [t("action.discard.effect.files", n=len(tracked))]
    if any("A" in (f.index, f.worktree) for f in tracked):
        effects.append(t("action.discard.effect.added"))
    if untracked:
        effects.append(t("action.discard.effect.untracked", n=len(untracked)))
    effects.append(t("action.discard.effect.backup"))
    return ActionPlan(
        action=DISCARD,
        title=title,
        effects=tuple(effects),
        commands=(("reset", "--hard", "HEAD"),),
        backup_ref=backup_ref(DISCARD, now),
        danger=True,
    )


def plan_restore(
    status: RepoStatus, backup: Backup, now: float | None = None, when: str = ""
) -> ActionPlan:
    """Devuelve la rama al punto de un respaldo.

    ``when`` es hace cuánto se creó el respaldo, ya formateado por la interfaz.
    """
    title = t("action.restore.title")
    if not status.has_commits:
        return _blocked(RESTORE, title, t("action.undo.blocked.no_commits"))
    if status.conflicts:
        return _blocked(RESTORE, title, t("action.blocked.conflicts"))
    if backup.branch and backup.branch != status.branch:
        return _blocked(
            RESTORE, title, t("action.restore.blocked.branch", branch=backup.branch)
        )

    here = status.branch or status.short_oid or "?"
    effects = [
        t(
            "action.restore.effect.move",
            branch=here,
            oid=backup.oid[:7],
            operation=operation_label(backup.operation),
            when=when,
        )
    ]
    commands: list[tuple[str, ...]] = [("reset", "--hard", backup.ref)]
    if backup.changes_ref:
        effects.append(t("action.restore.effect.changes"))
        commands.append(("stash", "apply", backup.changes_ref))
    if not status.is_clean:
        effects.append(t("action.restore.effect.replace", n=len(status.files)))
    effects.append(t("action.restore.effect.backup"))
    return ActionPlan(
        action=RESTORE,
        title=title,
        effects=tuple(effects),
        commands=tuple(commands),
        backup_ref=backup_ref(RESTORE, now),
        danger=True,
    )


# ── Utilidades de los planes ────────────────────────────────────


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

    Si al terminar la rama sigue en el mismo commit y no había cambios sin
    guardar que respaldar, el respaldo no protege nada y se borra (por
    ejemplo, un pull que no trajo novedades).
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

    unchanged = False
    if backup is not None and backup.changes_ref is None:
        try:
            head = runner.run("rev-parse", "HEAD").stdout.strip()
            if head == backup.oid:
                delete_backup(runner, backup)
                backup, unchanged = None, True
        except GitError:
            pass  # ante la duda, el respaldo se queda
    return ActionResult(plan, tuple(steps), backup, unchanged=unchanged)


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
            "could not read password",
            "terminal prompts disabled",
            "permission denied",
            "host key verification failed",
            "invalid credentials",
            "returned error: 401",
            "returned error: 403",
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
    (("not fully merged",), "failure.unmerged"),
    (("already exists",), "failure.exists"),
    (("not a valid branch name", "is not a valid"), "failure.branch_name"),
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


def operation_label(operation: str) -> str:
    """Nombre humano de la operación de un respaldo ("pull" -> "bajar cambios")."""
    key = f"backup.op.{operation}"
    label = t(key)
    return operation if label == key else label


def success_message(result: ActionResult) -> str:
    """Frase corta para avisar que la acción salió bien."""
    if result.plan.action == PULL and result.unchanged:
        return t("action.pull.nothing")
    return t(f"action.{result.plan.action}.done")
