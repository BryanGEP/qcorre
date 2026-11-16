"""Lee el estado completo de un repositorio (solo lectura, nunca toca la red)."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from qcorre.git.parse import RepoStatus, parse_status
from qcorre.git.runner import GitRunner

# Comando principal: una sola llamada da rama, remoto, conteos y archivos.
STATUS_ARGS = ("status", "--porcelain=v2", "--branch", "-z")

# Usuario y contraseña incrustados en una URL: https://usuario:token@host/...
_URL_CREDENTIALS = re.compile(r"^(\w+://)[^/@]+@")


def read_status(repo: str | Path, runner: GitRunner | None = None) -> RepoStatus:
    """Estado del repo en ``repo``. Lanza ``GitError`` si git falla.

    Los conteos de commits sin subir / sin bajar son los que git conoce desde
    el último contacto con el remoto (``last_sync``): aquí no se hace
    ``fetch`` para no tocar la red ni pedir contraseñas sin avisar.
    """
    git = runner or GitRunner(repo)
    status = parse_status(git.run(*STATUS_ARGS, check=True).stdout)
    status = replace(status, remotes=tuple(git.run("remote").stdout.split()))

    upstream_oid: str | None = None
    if status.upstream and not status.upstream_gone:
        result = git.run("rev-parse", "--short=7", status.upstream)
        if result.ok:
            upstream_oid = result.stdout.strip() or None

    remote_url: str | None = None
    if status.push_remote:
        result = git.run("remote", "get-url", status.push_remote)
        if result.ok:
            remote_url = hide_credentials(result.stdout.strip()) or None

    return replace(
        status,
        upstream_oid=upstream_oid,
        remote_url=remote_url,
        last_sync=_last_sync(git, status) if status.remotes else None,
    )


def hide_credentials(url: str) -> str:
    """Quita usuario y contraseña de una URL para poder mostrarla en pantalla."""
    return _URL_CREDENTIALS.sub(r"\1", url)


def _last_sync(git: GitRunner, status: RepoStatus) -> float | None:
    """Cuándo fue el último contacto con el remoto para esta rama.

    Cuenta lo más reciente entre:

    - ``FETCH_HEAD``: lo escriben ``fetch`` y ``pull``.
    - El registro (reflog) de la rama remota, p. ej.
      ``logs/refs/remotes/origin/main``: se actualiza también al hacer
      ``push``. Sin esto, justo después de subir se diría que los datos del
      remoto son de hace horas.
    """
    args = ["rev-parse", "--git-path", "FETCH_HEAD"]
    if status.upstream and not status.upstream_gone:
        args += ["--git-path", f"logs/refs/remotes/{status.upstream}"]
    result = git.run(*args)
    if not result.ok:
        return None
    times: list[float] = []
    for line in result.stdout.splitlines():
        path = Path(line.strip())
        if not path.is_absolute():
            path = git.repo / path
        try:
            times.append(path.stat().st_mtime)
        except OSError:
            continue
    return max(times, default=None)
