"""Modelos de datos compartidos por todas las capas.

Son dataclasses inmutables y sin dependencias: se pueden construir a mano en
los tests, sin psutil ni interfaz.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


@dataclass(frozen=True)
class ProcessInfo:
    """Foto de un proceso del sistema, tal como la entrega el recolector.

    Los campos que no se pudieron leer quedan en ``None`` o vacíos, y
    ``access_denied`` indica que el sistema negó el acceso a alguno de ellos.
    """

    pid: int
    name: str
    cmdline: tuple[str, ...] = ()
    cwd: str | None = None
    exe: str | None = None
    ports: tuple[int, ...] = ()
    create_time: float = 0.0
    ppid: int | None = None
    access_denied: bool = False


class ProcessKind(str, Enum):
    """Tipo de proceso de desarrollo."""

    SERVER = "server"  # escucha en algún puerto
    DATABASE = "database"  # base de datos, caché o broker conocido
    TOOL = "tool"  # herramienta de un proyecto sin puertos (watchers, etc.)


class OrphanReason(str, Enum):
    """Motivos por los que un proceso se marca como huérfano."""

    NO_PROJECT = "no_project"  # no pertenece a ningún proyecto
    LONG_RUNNING = "long_running"  # lleva demasiado tiempo corriendo
    PARENT_GONE = "parent_gone"  # el proceso que lo lanzó ya no existe


@dataclass(frozen=True)
class ProjectRoot:
    """Carpeta raíz de un proyecto detectado en disco."""

    path: Path
    has_git: bool

    @property
    def name(self) -> str:
        return self.path.name


@dataclass(frozen=True)
class DevProcess:
    """Proceso de desarrollo listo para mostrar.

    Puede representar varios procesos del sistema: un servidor y sus
    trabajadores con el mismo nombre se funden en una sola fila. ``info`` es el
    proceso líder (el que hay que matar para terminar con todos); ``pids`` y
    ``members`` incluyen a todos, del más viejo al más nuevo.

    ``parent_name`` es el nombre del proceso que lanzó al líder, o ``None`` si
    ya no existe o no se pudo saber.
    """

    info: ProcessInfo
    kind: ProcessKind
    label: str
    ports: tuple[int, ...] = ()
    pids: tuple[int, ...] = ()
    orphan_reasons: tuple[OrphanReason, ...] = ()
    members: tuple[ProcessInfo, ...] = ()
    parent_name: str | None = None

    @property
    def pid(self) -> int:
        return self.info.pid

    @property
    def is_orphan(self) -> bool:
        return bool(self.orphan_reasons)

    @property
    def access_denied(self) -> bool:
        return self.info.access_denied

    def uptime(self, now: float) -> float:
        """Segundos que lleva corriendo."""
        return max(0.0, now - self.info.create_time)


@dataclass(frozen=True)
class Project:
    """Un proyecto con los procesos de desarrollo que corren dentro de él."""

    root: ProjectRoot
    processes: tuple[DevProcess, ...]

    @property
    def name(self) -> str:
        return self.root.name

    @property
    def path(self) -> Path:
        return self.root.path

    @property
    def has_git(self) -> bool:
        return self.root.has_git


@dataclass(frozen=True)
class Snapshot:
    """Resultado de agrupar los procesos: proyectos y procesos sin proyecto."""

    projects: tuple[Project, ...] = ()
    unassigned: tuple[DevProcess, ...] = ()

    @property
    def process_count(self) -> int:
        return sum(len(p.processes) for p in self.projects) + len(self.unassigned)
