"""Red de seguridad: respaldos automáticos antes de las operaciones riesgosas.

Un respaldo son referencias de git bajo ``refs/qcorre/backup/<fecha>-<operación>/``:

- ``.../rama/<nombre>``: el commit donde estaba la rama (``.../suelto`` si no
  había rama).
- ``.../cambios``: una foto de los cambios sin guardar, si los había.

No ensucian la lista de ramas ni se suben al remoto, y mientras existan git no
borra esos commits.

La foto de los cambios se toma con ``git stash create``: crea el commit de
respaldo *sin tocar* los archivos ni la lista de stashes. Limitación conocida:
no incluye archivos nuevos que git todavía no sigue.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from qcorre.git.runner import GitError, GitRunner

BACKUP_PREFIX = "refs/qcorre/backup/"

_BRANCH_DIR = "rama/"
_DETACHED = "suelto"
_CHANGES = "cambios"

# Formato anterior (un solo nivel): ``<fecha>-<op>`` y ``<fecha>-<op>-cambios``.
_OLD_CHANGES_SUFFIX = "-cambios"


@dataclass(frozen=True)
class Backup:
    """Un respaldo: dónde estaba la rama antes de una operación."""

    name: str  # "20261116-143210-pull": identifica el respaldo
    ref: str  # referencia que apunta al commit respaldado
    oid: str
    operation: str  # "pull", "undo"...
    created: float  # hora del respaldo (epoch)
    branch: str | None = None  # rama respaldada (None = desconocida o sin rama)
    changes_ref: str | None = None  # foto de los cambios sin commit, si había

    @property
    def base(self) -> str:
        """Prefijo común de sus referencias (lo que se muestra al usuario)."""
        return BACKUP_PREFIX + self.name

    @property
    def refs(self) -> tuple[str, ...]:
        return (self.ref, self.changes_ref) if self.changes_ref else (self.ref,)


def backup_ref(operation: str, now: float | None = None) -> str:
    """Base de un respaldo nuevo: ``refs/qcorre/backup/20261116-143210-pull``."""
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    return f"{BACKUP_PREFIX}{stamp}-{operation}"


def create_backup(runner: GitRunner, base: str) -> Backup:
    """Crea el respaldo ``base`` con la posición actual de la rama.

    Lanza ``GitError`` si no se pudo: la operación riesgosa no debe seguir
    sin su red de seguridad.
    """
    name = base[len(BACKUP_PREFIX) :]
    head = runner.run("rev-parse", "HEAD", check=True).stdout.strip()
    current = runner.run("symbolic-ref", "--short", "-q", "HEAD")
    branch = current.stdout.strip() if current.ok and current.stdout.strip() else None

    ref = f"{base}/{_BRANCH_DIR}{branch}" if branch else f"{base}/{_DETACHED}"
    runner.run("update-ref", ref, head, check=True)

    changes_ref: str | None = None
    snapshot = runner.run("stash", "create", f"qcorre: respaldo antes de {_operation(name)}")
    stash_oid = snapshot.stdout.strip()
    if snapshot.ok and stash_oid:
        changes_ref = f"{base}/{_CHANGES}"
        runner.run("update-ref", changes_ref, stash_oid, check=True)

    return Backup(
        name=name,
        ref=ref,
        oid=head,
        operation=_operation(name),
        created=_created(name),
        branch=branch,
        changes_ref=changes_ref,
    )


def delete_backup(runner: GitRunner, backup: Backup) -> None:
    """Borra las referencias de un respaldo (los commits siguen en el repo)."""
    for ref in backup.refs:
        runner.run("update-ref", "-d", ref)


def list_backups(runner: GitRunner) -> list[Backup]:
    """Respaldos existentes, del más reciente al más antiguo."""
    result = runner.run("for-each-ref", "--format=%(refname) %(objectname)", BACKUP_PREFIX)
    if not result.ok:
        raise GitError("failed", result.stderr.strip(), result.command)
    refs = dict(line.split(" ", 1) for line in result.stdout.splitlines() if " " in line)
    return parse_backups(refs)


def parse_backups(refs: dict[str, str]) -> list[Backup]:
    """Agrupa referencias (``ref -> oid``) en respaldos. Función pura."""
    heads: dict[str, tuple[str, str, str | None]] = {}  # nombre -> (ref, oid, rama)
    changes: dict[str, str] = {}  # nombre -> ref de la foto de cambios

    for ref, oid in refs.items():
        if not ref.startswith(BACKUP_PREFIX):
            continue
        name, _, rest = ref[len(BACKUP_PREFIX) :].partition("/")
        if rest == _CHANGES:
            changes[name] = ref
        elif rest == _DETACHED:
            heads[name] = (ref, oid, None)
        elif rest.startswith(_BRANCH_DIR):
            heads[name] = (ref, oid, rest[len(_BRANCH_DIR) :])
        elif not rest and name.endswith(_OLD_CHANGES_SUFFIX):
            changes[name[: -len(_OLD_CHANGES_SUFFIX)]] = ref
        elif not rest:
            heads[name] = (ref, oid, None)

    backups = [
        Backup(
            name=name,
            ref=ref,
            oid=oid,
            operation=_operation(name),
            created=_created(name),
            branch=branch,
            changes_ref=changes.get(name),
        )
        for name, (ref, oid, branch) in heads.items()
    ]
    return sorted(backups, key=lambda backup: backup.name, reverse=True)


def _operation(name: str) -> str:
    """``20261116-143210-pull`` -> ``pull``."""
    parts = name.split("-", 2)
    return parts[2] if len(parts) == 3 else name


def _created(name: str) -> float:
    try:
        return time.mktime(time.strptime(name[:15], "%Y%m%d-%H%M%S"))
    except ValueError:
        return 0.0
