"""Red de seguridad: respaldos automáticos antes de las operaciones riesgosas.

Un respaldo es una referencia de git bajo ``refs/qcorre/backup/`` que apunta
al commit donde estaba la rama. No ensucia la lista de ramas ni se sube al
remoto, y mientras exista git no borra esos commits.

Si además hay cambios sin guardar, se respalda una foto de ellos con
``git stash create``: crea el commit de respaldo *sin tocar* los archivos ni
la lista de stashes. Limitación conocida: esa foto no incluye archivos nuevos
que git todavía no sigue.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from qcorre.git.runner import GitError, GitRunner

BACKUP_PREFIX = "refs/qcorre/backup/"

# Sufijo de la referencia que guarda la foto de los cambios sin commit.
CHANGES_SUFFIX = "-cambios"


@dataclass(frozen=True)
class Backup:
    """Un respaldo: a qué commit apuntaba la rama antes de una operación."""

    ref: str
    oid: str
    operation: str  # "pull", "undo"...
    created: float  # hora del respaldo (epoch)
    changes_ref: str | None = None  # foto de los cambios sin commit, si había


def backup_ref(operation: str, now: float | None = None) -> str:
    """Nombre de la referencia: ``refs/qcorre/backup/20261116-143210-pull``."""
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    return f"{BACKUP_PREFIX}{stamp}-{operation}"


def create_backup(runner: GitRunner, ref: str) -> Backup:
    """Crea el respaldo ``ref`` apuntando al commit actual.

    Lanza ``GitError`` si no se pudo: la operación riesgosa no debe seguir
    sin su red de seguridad.
    """
    head = runner.run("rev-parse", "HEAD", check=True).stdout.strip()
    runner.run("update-ref", ref, head, check=True)

    changes_ref: str | None = None
    snapshot = runner.run("stash", "create", f"qcorre: respaldo antes de {_operation(ref)}")
    stash_oid = snapshot.stdout.strip()
    if snapshot.ok and stash_oid:
        changes_ref = ref + CHANGES_SUFFIX
        runner.run("update-ref", changes_ref, stash_oid, check=True)

    return Backup(
        ref=ref,
        oid=head,
        operation=_operation(ref),
        created=_created(ref),
        changes_ref=changes_ref,
    )


def list_backups(runner: GitRunner) -> list[Backup]:
    """Respaldos existentes, del más reciente al más antiguo."""
    result = runner.run("for-each-ref", "--format=%(refname) %(objectname)", BACKUP_PREFIX)
    if not result.ok:
        raise GitError("failed", result.stderr.strip(), result.command)
    refs = dict(line.split(" ", 1) for line in result.stdout.splitlines() if " " in line)
    backups = [
        Backup(
            ref=ref,
            oid=oid,
            operation=_operation(ref),
            created=_created(ref),
            changes_ref=ref + CHANGES_SUFFIX if ref + CHANGES_SUFFIX in refs else None,
        )
        for ref, oid in refs.items()
        if not ref.endswith(CHANGES_SUFFIX)
    ]
    return sorted(backups, key=lambda backup: backup.ref, reverse=True)


def _operation(ref: str) -> str:
    """``refs/qcorre/backup/20261116-143210-pull`` -> ``pull``."""
    name = ref[len(BACKUP_PREFIX) :]
    parts = name.split("-", 2)
    return parts[2] if len(parts) == 3 else name


def _created(ref: str) -> float:
    name = ref[len(BACKUP_PREFIX) :]
    try:
        return time.mktime(time.strptime(name[:15], "%Y%m%d-%H%M%S"))
    except ValueError:
        return 0.0
