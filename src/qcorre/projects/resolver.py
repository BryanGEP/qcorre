"""Encuentra la raíz del proyecto al que pertenece una ruta.

Regla: se sube carpeta por carpeta buscando ``.git`` (carpeta o archivo, para
cubrir worktrees y submódulos). Si no hay repo, se usa la carpeta más cercana
que tenga un archivo marcador (``package.json``, ``pyproject.toml``...).

La búsqueda nunca llega a la carpeta personal del usuario ni más arriba, y
salta las carpetas ocultas y de dependencias: así ``~/.nvm`` (que es un clon de
git) o ``node_modules/vite`` (que tiene ``package.json``) no cuentan como
proyectos.
"""

from __future__ import annotations

from pathlib import Path

from qcorre.models import ProcessInfo, ProjectRoot

# Archivos que delatan un proyecto aunque no tenga git.
MARKERS: tuple[str, ...] = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "manage.py",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Gemfile",
    "composer.json",
    "deno.json",
    "mix.exs",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
)

# Carpetas de dependencias: lo que hay dentro no es un proyecto del usuario.
VENDORED_DIRS: frozenset[str] = frozenset(
    {"node_modules", "site-packages", "dist-packages", "venv", "vendor"}
)

# Cuántos argumentos de la línea de comandos se revisan buscando rutas.
_MAX_ARGS = 12


class ProjectResolver:
    """Resuelve rutas a raíces de proyecto, con caché.

    ``home`` es la carpeta personal del usuario (el límite superior de la
    búsqueda). Se puede inyectar para testear con carpetas temporales.
    """

    def __init__(self, home: str | Path | None = None) -> None:
        self.home = Path(home) if home is not None else Path.home()
        self._cache: dict[str, ProjectRoot | None] = {}

    def clear(self) -> None:
        """Olvida lo resuelto (por si se crearon o borraron repos)."""
        self._cache.clear()

    def find_root(self, path: str | Path | None) -> ProjectRoot | None:
        """Devuelve la raíz del proyecto que contiene ``path``, o ``None``."""
        if not path:
            return None
        key = str(path)
        if key not in self._cache:
            self._cache[key] = self._search(Path(path))
        return self._cache[key]

    def resolve_process(self, info: ProcessInfo) -> ProjectRoot | None:
        """Busca el proyecto de un proceso probando, en orden:

        1. su carpeta de trabajo (cwd),
        2. las rutas absolutas de su línea de comandos,
        3. la ruta de su ejecutable.
        """
        for candidate in self._candidates(info):
            root = self.find_root(candidate)
            if root is not None:
                return root
        return None

    # ── Internos ────────────────────────────────────────────────

    def _candidates(self, info: ProcessInfo) -> list[str]:
        candidates: list[str] = []
        if info.cwd:
            candidates.append(info.cwd)
        for arg in info.cmdline[1 : _MAX_ARGS + 1]:
            # Cubre tanto `server.js` como `--config=/ruta/al/archivo`.
            value = arg.split("=", 1)[-1] if arg.startswith("-") else arg
            if _is_absolute(value):
                candidates.append(value)
        if info.cmdline and _is_absolute(info.cmdline[0]):
            candidates.append(info.cmdline[0])
        if info.exe:
            candidates.append(info.exe)
        return candidates

    def _search(self, start: Path) -> ProjectRoot | None:
        if not start.is_absolute():
            return None
        marker_dir: Path | None = None
        for folder in (start, *start.parents):
            if self._is_boundary(folder):
                break
            if self._is_skipped(folder):
                continue
            if _exists(folder / ".git"):
                return ProjectRoot(folder, has_git=True)
            if marker_dir is None and any(_exists(folder / m) for m in MARKERS):
                marker_dir = folder
        if marker_dir is not None:
            return ProjectRoot(marker_dir, has_git=False)
        return None

    def _is_boundary(self, folder: Path) -> bool:
        """La carpeta personal, sus ancestros y la raíz del disco no son proyectos."""
        if folder.parent == folder:
            return True
        return folder == self.home or folder in self.home.parents

    def _is_skipped(self, folder: Path) -> bool:
        """Carpetas ocultas o de dependencias (y todo lo que cuelga de ellas)."""
        try:
            parts = folder.relative_to(self.home).parts
        except ValueError:
            parts = folder.parts[1:]
        return any(part.startswith(".") or part in VENDORED_DIRS for part in parts)


def _is_absolute(value: str) -> bool:
    try:
        return Path(value).is_absolute()
    except (OSError, ValueError):
        return False


def _exists(path: Path) -> bool:
    """``Path.exists`` que nunca lanza (rutas raras, permisos, discos de red)."""
    try:
        return path.exists()
    except (OSError, ValueError):
        return False
