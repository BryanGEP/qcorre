"""Lista las ramas de un repo: las locales y las que solo están en el remoto."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from qcorre.git.runner import GitRunner

# Un campo por dato, separados por NUL (los nombres de rama no pueden llevarlo).
_FORMAT = "%00".join(
    ["%(refname)", "%(objectname:short)", "%(upstream:short)", "%(upstream:track)", "%(HEAD)"]
)
_HEADS = "refs/heads/"
_REMOTES = "refs/remotes/"
_AHEAD = re.compile(r"ahead (\d+)")
_BEHIND = re.compile(r"behind (\d+)")


@dataclass(frozen=True)
class Branch:
    """Una rama, local o solo remota."""

    name: str  # sin el remoto: "feat/x" (también en las que solo están en el remoto)
    oid: str = ""
    current: bool = False
    upstream: str | None = None  # p. ej. "origin/feat/x"
    ahead: int | None = None  # commits sin subir (None = sin rama remota)
    behind: int | None = None  # commits sin bajar
    gone: bool = False  # su rama remota ya no existe
    merged: bool = False  # todo su trabajo ya está en la rama actual
    remote: str | None = None  # solo en las ramas remotas: "origin"

    @property
    def remote_only(self) -> bool:
        return self.remote is not None

    @property
    def full_remote(self) -> str:
        """``origin/feat/x`` (para las ramas que solo están en el remoto)."""
        return f"{self.remote}/{self.name}"

    @property
    def can_delete(self) -> bool:
        """¿Se ofrece borrarla? Solo si su remota ya no existe y ya está mergeada."""
        return self.gone and self.merged and not self.current and not self.remote_only


@dataclass(frozen=True)
class BranchList:
    local: tuple[Branch, ...] = ()
    remote_only: tuple[Branch, ...] = ()
    last_sync: float | None = None  # de cuándo es lo que se sabe del remoto


def parse_branches(
    output: str, remotes: tuple[str, ...] = (), merged: frozenset[str] = frozenset()
) -> BranchList:
    """Interpreta la salida de ``git for-each-ref`` con ``_FORMAT``. Función pura.

    ``remotes`` son los nombres de los remotos (para separar ``origin/feat/x``)
    y ``merged`` las ramas locales ya contenidas en la rama actual.
    """
    local: list[Branch] = []
    remote_refs: list[tuple[str, str]] = []  # (nombre completo, oid)

    for line in output.splitlines():
        fields = line.split("\0")
        if len(fields) != 5:
            continue
        ref, oid, upstream, track, head = fields
        if ref.startswith(_HEADS):
            name = ref[len(_HEADS) :]
            has_upstream = bool(upstream)
            gone = "gone" in track
            ahead = _count(_AHEAD, track) if has_upstream and not gone else None
            behind = _count(_BEHIND, track) if has_upstream and not gone else None
            local.append(
                Branch(
                    name=name,
                    oid=oid,
                    current=head.strip() == "*",
                    upstream=upstream or None,
                    ahead=ahead,
                    behind=behind,
                    gone=gone,
                    merged=name in merged,
                )
            )
        elif ref.startswith(_REMOTES) and not ref.endswith("/HEAD"):
            remote_refs.append((ref[len(_REMOTES) :], oid))

    local_names = {branch.name for branch in local}
    followed = {branch.upstream for branch in local if branch.upstream}
    remote_only: list[Branch] = []
    for full, oid in remote_refs:
        remote, name = _split_remote(full, remotes)
        # Si ya hay una rama local que la sigue (o con su nombre), no es "solo remota".
        if full in followed or name in local_names:
            continue
        remote_only.append(Branch(name=name, oid=oid, remote=remote))

    local.sort(key=lambda b: (not b.current, b.name.casefold()))
    remote_only.sort(key=lambda b: (b.remote or "", b.name.casefold()))
    return BranchList(local=tuple(local), remote_only=tuple(remote_only))


def read_branches(repo: str | Path, runner: GitRunner | None = None) -> BranchList:
    """Ramas del repo en ``repo``. No toca la red: las ramas remotas son las
    que git conoce desde el último contacto con el remoto."""
    from qcorre.git.status import last_contact

    git = runner or GitRunner(repo)
    listing = git.run("for-each-ref", f"--format={_FORMAT}", _HEADS, _REMOTES, check=True)
    remotes = tuple(git.run("remote").stdout.split())
    # En un repo sin commits esto falla: entonces no hay nada mergeado.
    merged = git.run("for-each-ref", "--format=%(refname:short)", "--merged=HEAD", _HEADS)
    merged_names = frozenset(merged.stdout.split()) if merged.ok else frozenset()

    branches = parse_branches(listing.stdout, remotes, merged_names)
    return BranchList(
        local=branches.local,
        remote_only=branches.remote_only,
        last_sync=last_contact(git) if remotes else None,
    )


def _count(pattern: re.Pattern[str], track: str) -> int:
    match = pattern.search(track)
    return int(match.group(1)) if match else 0


def _split_remote(full: str, remotes: tuple[str, ...]) -> tuple[str, str]:
    """``origin/feat/x`` -> ``("origin", "feat/x")``. Gana el remoto conocido más largo."""
    for remote in sorted(remotes, key=len, reverse=True):
        if full.startswith(remote + "/"):
            return remote, full[len(remote) + 1 :]
    remote, _, name = full.partition("/")
    return remote, name
