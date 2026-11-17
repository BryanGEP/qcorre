"""Lee el historial de commits de un repo (solo lectura).

Se piden los commits alcanzables desde la rama actual, las demás ramas locales
y las ramas remotas conocidas: lo que el usuario entiende por "el historial
del proyecto". Las referencias internas (respaldos de qcorre, stash) no entran.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from qcorre.git.runner import GitError, GitRunner

# Cuántos commits se muestran como máximo.
DEFAULT_LIMIT = 300

# Cuántos se muestran en "Últimos commits" (vista Estado).
RECENT_LIMIT = 5

# Separadores que no pueden aparecer en los datos de un commit.
_FIELD = "\x1f"
_RECORD = "\x1e"
_FORMAT = _FIELD.join(["%H", "%P", "%D", "%an", "%ct", "%s"]) + _RECORD

_HEADS = "refs/heads/"
_REMOTES = "refs/remotes/"
_TAGS = "refs/tags/"


class RefKind(str, Enum):
    """Tipo de etiqueta que acompaña a un commit."""

    HEAD = "head"  # la rama en la que estás
    DETACHED = "detached"  # HEAD suelto (sin rama)
    LOCAL = "local"  # otra rama local
    REMOTE = "remote"  # rama del remoto
    TAG = "tag"


@dataclass(frozen=True)
class Ref:
    kind: RefKind
    name: str  # "main", "origin/main", "v1.0"...


@dataclass(frozen=True)
class Commit:
    """Un commit del historial."""

    oid: str
    parents: tuple[str, ...] = ()
    refs: tuple[Ref, ...] = ()
    author: str = ""
    time: float = 0.0  # fecha del commit (epoch)
    subject: str = ""

    @property
    def short_oid(self) -> str:
        return self.oid[:7]

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1


@dataclass(frozen=True)
class History:
    commits: tuple[Commit, ...] = ()
    truncated: bool = False  # hay commits más antiguos que no se muestran


def parse_refs(decoration: str) -> tuple[Ref, ...]:
    """Interpreta las decoraciones de ``git log --decorate=full`` (campo ``%D``).

    Ejemplo: ``HEAD -> refs/heads/main, refs/remotes/origin/main, tag: refs/tags/v1``.
    Se descartan ``origin/HEAD`` (un alias) y cualquier referencia que no sea
    rama o etiqueta. El orden de salida es fijo: primero dónde estás, luego
    ramas locales, remotas y etiquetas.
    """
    refs: list[Ref] = []
    for token in decoration.split(", "):
        token = token.strip()
        if not token:
            continue
        if token == "HEAD":
            refs.append(Ref(RefKind.DETACHED, "HEAD"))
        elif token.startswith("HEAD -> "):
            target = token[len("HEAD -> ") :]
            name = target[len(_HEADS) :] if target.startswith(_HEADS) else target
            refs.append(Ref(RefKind.HEAD, name))
        elif token.startswith("tag: "):
            target = token[len("tag: ") :]
            refs.append(Ref(RefKind.TAG, target.removeprefix(_TAGS)))
        elif token.startswith(_HEADS):
            refs.append(Ref(RefKind.LOCAL, token[len(_HEADS) :]))
        elif token.startswith(_REMOTES):
            name = token[len(_REMOTES) :]
            if not name.endswith("/HEAD"):
                refs.append(Ref(RefKind.REMOTE, name))
    order = list(RefKind)
    return tuple(sorted(refs, key=lambda ref: (order.index(ref.kind), ref.name)))


def parse_log(output: str) -> list[Commit]:
    """Interpreta la salida de ``git log`` con el formato de este módulo.

    Los registros incompletos o corruptos se omiten en vez de tronar.
    """
    commits: list[Commit] = []
    for record in output.split(_RECORD):
        record = record.strip("\n")
        if not record:
            continue
        fields = record.split(_FIELD)
        if len(fields) != 6 or not fields[0]:
            continue
        oid, parents, decoration, author, stamp, subject = fields
        try:
            when = float(stamp)
        except ValueError:
            when = 0.0
        commits.append(
            Commit(
                oid=oid,
                parents=tuple(parents.split()),
                refs=parse_refs(decoration),
                author=author,
                time=when,
                subject=subject,
            )
        )
    return commits


def recent_commits(git: GitRunner, limit: int = RECENT_LIMIT) -> tuple[Commit, ...]:
    """Los últimos commits de la rama actual, del más nuevo al más viejo.

    Sigue solo el primer padre de cada commit: es la línea de la rama, sin los
    commits que entraron con cada merge. Es una consulta ligera (``-n``), apta
    para hacerse en cada refresco. Devuelve ``()`` si aún no hay commits.
    """
    result = git.run(
        "log",
        "--first-parent",
        "--decorate=full",
        f"--max-count={limit}",
        f"--format={_FORMAT}",
        "HEAD",
    )
    if not result.ok:
        return ()
    return tuple(parse_log(result.stdout))


def read_history(
    repo: str | Path, runner: GitRunner | None = None, *, limit: int = DEFAULT_LIMIT
) -> History:
    """Historial del repo en ``repo``: hasta ``limit`` commits, los más nuevos primero.

    El orden es topológico (un commit siempre va antes que sus padres), que es
    lo que necesita el gráfico. Lanza ``GitError`` si git falla.
    """
    git = runner or GitRunner(repo)
    revisions = ["--branches", "--remotes"]
    # En un repo recién creado HEAD todavía no apunta a ningún commit.
    if git.run("rev-parse", "--verify", "--quiet", "HEAD").ok:
        revisions.append("HEAD")

    # Se pide uno de más para saber si quedó historial sin mostrar.
    result = git.run(
        "log",
        "--topo-order",
        "--decorate=full",
        f"--max-count={limit + 1}",
        f"--format={_FORMAT}",
        *revisions,
    )
    if not result.ok:
        raise GitError("failed", result.stderr.strip() or result.stdout.strip(), result.command)
    commits = parse_log(result.stdout)
    return History(commits=tuple(commits[:limit]), truncated=len(commits) > limit)
