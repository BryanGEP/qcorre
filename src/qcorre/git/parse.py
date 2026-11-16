"""Convierte la salida de git en modelos. Funciones puras, sin ejecutar nada."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ChangeKind(str, Enum):
    """Qué le pasó a un archivo, en términos que entiende cualquiera."""

    CONFLICT = "conflict"
    MODIFIED = "modified"
    NEW = "new"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass(frozen=True)
class FileChange:
    """Un archivo con cambios.

    ``index`` y ``worktree`` son los códigos de git (``M``, ``A``, ``D``,
    ``R``... o ``.`` si no hay cambio): el primero es lo ya preparado con
    ``git add`` y el segundo lo que aún no.
    """

    path: str
    index: str = "."
    worktree: str = "."
    orig_path: str | None = None  # nombre anterior, si fue renombrado
    untracked: bool = False
    conflict: bool = False

    @property
    def staged(self) -> bool:
        """¿Tiene cambios ya preparados para el próximo commit?"""
        return self.index != "." and not self.conflict

    @property
    def kind(self) -> ChangeKind:
        if self.conflict:
            return ChangeKind.CONFLICT
        if self.untracked or "A" in (self.index, self.worktree):
            return ChangeKind.NEW
        if "D" in (self.index, self.worktree):
            return ChangeKind.DELETED
        if self.index in ("R", "C"):
            return ChangeKind.RENAMED
        return ChangeKind.MODIFIED


@dataclass(frozen=True)
class RepoStatus:
    """Estado de un repositorio: rama, relación con el remoto y archivos.

    Los campos de la segunda mitad no salen de ``git status``: los completa
    ``qcorre.git.status.read_status`` con consultas adicionales.
    """

    branch: str | None = None  # None = HEAD suelto (sin rama)
    oid: str | None = None  # commit actual; None = repo sin commits
    upstream: str | None = None  # p. ej. "origin/main"
    ahead: int | None = None  # commits sin subir (None = no se sabe)
    behind: int | None = None  # commits sin bajar
    files: tuple[FileChange, ...] = ()

    remotes: tuple[str, ...] = ()
    upstream_oid: str | None = None
    last_fetch: float | None = None  # cuándo se consultó el remoto por última vez

    # ── Rama ────────────────────────────────────────────────────

    @property
    def detached(self) -> bool:
        return self.branch is None

    @property
    def has_commits(self) -> bool:
        return self.oid is not None

    @property
    def short_oid(self) -> str | None:
        return self.oid[:7] if self.oid else None

    # ── Remoto ──────────────────────────────────────────────────

    @property
    def upstream_gone(self) -> bool:
        """La rama tiene un remoto configurado, pero esa rama remota ya no existe."""
        return self.upstream is not None and self.ahead is None

    @property
    def remote_name(self) -> str | None:
        """Nombre del remoto del upstream (``origin`` en ``origin/main``)."""
        if self.upstream is None:
            return None
        # Se prefiere el remoto conocido más largo: los nombres pueden llevar "/".
        for remote in sorted(self.remotes, key=len, reverse=True):
            if self.upstream.startswith(remote + "/"):
                return remote
        return self.upstream.split("/", 1)[0]

    @property
    def remote_branch(self) -> str | None:
        """Nombre de la rama en el remoto (``main`` en ``origin/main``)."""
        remote = self.remote_name
        if self.upstream is None or remote is None:
            return None
        return self.upstream[len(remote) + 1 :]

    # ── Archivos ────────────────────────────────────────────────

    @property
    def is_clean(self) -> bool:
        return not self.files

    @property
    def conflicts(self) -> tuple[FileChange, ...]:
        return tuple(f for f in self.files if f.kind is ChangeKind.CONFLICT)

    @property
    def new(self) -> tuple[FileChange, ...]:
        return tuple(f for f in self.files if f.kind is ChangeKind.NEW)

    @property
    def changed(self) -> tuple[FileChange, ...]:
        """Archivos que git ya seguía y cambiaron (editados, borrados, renombrados)."""
        skip = (ChangeKind.NEW, ChangeKind.CONFLICT)
        return tuple(f for f in self.files if f.kind not in skip)

    @property
    def staged(self) -> tuple[FileChange, ...]:
        return tuple(f for f in self.files if f.staged)


def parse_status(output: str) -> RepoStatus:
    """Interpreta ``git status --porcelain=v2 --branch -z``.

    Con ``-z`` cada registro termina en NUL y las rutas vienen sin escapar.
    Los renombrados ocupan dos registros: el segundo es el nombre anterior.
    """
    branch: str | None = None
    oid: str | None = None
    upstream: str | None = None
    ahead: int | None = None
    behind: int | None = None
    files: list[FileChange] = []

    records = output.split("\0")
    position = 0
    while position < len(records):
        record = records[position]
        position += 1
        if not record:
            continue

        if record.startswith("# "):
            key, _, value = record[2:].partition(" ")
            if key == "branch.oid":
                oid = None if value == "(initial)" else value
            elif key == "branch.head":
                branch = None if value == "(detached)" else value
            elif key == "branch.upstream":
                upstream = value
            elif key == "branch.ab":
                ahead, behind = _parse_ahead_behind(value)
        elif record.startswith("1 "):
            fields = record.split(" ", 8)
            if len(fields) == 9:
                files.append(FileChange(fields[8], fields[1][0], fields[1][1]))
        elif record.startswith("2 "):
            fields = record.split(" ", 9)
            orig = records[position] if position < len(records) else None
            position += 1
            if len(fields) == 10:
                files.append(FileChange(fields[9], fields[1][0], fields[1][1], orig_path=orig))
        elif record.startswith("u "):
            fields = record.split(" ", 10)
            if len(fields) == 11:
                files.append(FileChange(fields[10], fields[1][0], fields[1][1], conflict=True))
        elif record.startswith("? "):
            files.append(FileChange(record[2:], untracked=True))
        # Los ignorados ("! ") y cualquier registro desconocido se omiten.

    return RepoStatus(
        branch=branch, oid=oid, upstream=upstream, ahead=ahead, behind=behind, files=tuple(files)
    )


def _parse_ahead_behind(value: str) -> tuple[int | None, int | None]:
    """``"+2 -1"`` -> ``(2, 1)``."""
    try:
        ahead, behind = value.split()
        return int(ahead.lstrip("+")), int(behind.lstrip("-"))
    except ValueError:
        return None, None
