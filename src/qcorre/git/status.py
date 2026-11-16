"""Lee el estado completo de un repositorio (solo lectura, nunca toca la red)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from qcorre.git.parse import RepoStatus, parse_status
from qcorre.git.runner import GitRunner

# Comando principal: una sola llamada da rama, remoto, conteos y archivos.
STATUS_ARGS = ("status", "--porcelain=v2", "--branch", "-z")


def read_status(repo: str | Path, runner: GitRunner | None = None) -> RepoStatus:
    """Estado del repo en ``repo``. Lanza ``GitError`` si git falla.

    Los conteos de commits sin subir / sin bajar son los que git conoce desde
    la última vez que se consultó el remoto (``last_fetch``): aquí no se hace
    ``fetch`` para no tocar la red ni pedir contraseñas sin avisar.
    """
    git = runner or GitRunner(repo)
    status = parse_status(git.run(*STATUS_ARGS, check=True).stdout)

    remotes = tuple(git.run("remote").stdout.split())

    upstream_oid: str | None = None
    if status.upstream and not status.upstream_gone:
        result = git.run("rev-parse", "--short=7", status.upstream)
        if result.ok:
            upstream_oid = result.stdout.strip() or None

    return replace(
        status,
        remotes=remotes,
        upstream_oid=upstream_oid,
        last_fetch=_last_fetch(git) if remotes else None,
    )


def _last_fetch(git: GitRunner) -> float | None:
    """Fecha del último ``fetch``/``pull``: la del archivo ``FETCH_HEAD``."""
    result = git.run("rev-parse", "--git-path", "FETCH_HEAD")
    if not result.ok or not result.stdout.strip():
        return None
    path = Path(result.stdout.strip())
    if not path.is_absolute():
        path = git.repo / path
    try:
        return path.stat().st_mtime
    except OSError:
        return None
