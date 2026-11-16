"""Agrupa los procesos del sistema por proyecto y marca los huérfanos."""

from __future__ import annotations

from collections.abc import Iterable

from qcorre.models import (
    DevProcess,
    OrphanReason,
    ProcessInfo,
    ProcessKind,
    Project,
    ProjectRoot,
    Snapshot,
)
from qcorre.projects.classify import base_name, classify, describe
from qcorre.projects.resolver import ProjectResolver

# Un proceso que lleva más de esto corriendo se marca como huérfano.
DEFAULT_LONG_RUNNING_SECONDS = 24 * 60 * 60

# Tope al subir por la cadena de padres (evita ciclos por PIDs reutilizados).
_MAX_DEPTH = 12


def group_processes(
    processes: Iterable[ProcessInfo],
    resolver: ProjectResolver,
    *,
    now: float,
    long_running_seconds: float = DEFAULT_LONG_RUNNING_SECONDS,
    init_pids: frozenset[int] = frozenset(),
    exclude_pids: frozenset[int] = frozenset(),
) -> Snapshot:
    """Convierte la lista de procesos del sistema en un ``Snapshot``.

    Pasos:

    1. Cada proceso busca su proyecto (cwd, línea de comandos, ejecutable) y,
       si no lo encuentra, hereda el de su padre.
    2. Un proceso y sus hijos con el mismo nombre (servidor + trabajadores) se
       funden en una sola fila, con los puertos de todos.
    3. Se descartan los que no son de desarrollo.
    4. Se marcan los huérfanos: sin proyecto, con demasiado tiempo corriendo o
       con el padre muerto.

    ``init_pids`` son los PIDs que adoptan procesos huérfanos (1 en Unix);
    ``exclude_pids`` son procesos que no deben aparecer (el propio qcorre).
    """
    by_pid = {p.pid: p for p in processes}

    def parent_of(proc: ProcessInfo) -> ProcessInfo | None:
        if proc.ppid is None or proc.ppid == proc.pid:
            return None
        parent = by_pid.get(proc.ppid)
        # Un "padre" más joven que el hijo es un PID reutilizado, no su padre.
        if parent is None or parent.create_time > proc.create_time:
            return None
        return parent

    direct = {pid: resolver.resolve_process(p) for pid, p in by_pid.items()}

    def root_of(proc: ProcessInfo) -> ProjectRoot | None:
        current: ProcessInfo | None = proc
        for _ in range(_MAX_DEPTH):
            if current is None:
                return None
            root = direct[current.pid]
            if root is not None:
                return root
            current = parent_of(current)
        return None

    def leader_of(proc: ProcessInfo) -> ProcessInfo:
        name = base_name(proc.name)
        current = proc
        for _ in range(_MAX_DEPTH):
            parent = parent_of(current)
            if parent is None or base_name(parent.name) != name:
                break
            current = parent
        return current

    def parent_gone(proc: ProcessInfo) -> bool:
        if proc.ppid is None or proc.ppid == 0:
            return False  # desconocido o lanzado por el propio sistema
        return proc.ppid in init_pids or parent_of(proc) is None

    # Paso 2: familias de procesos con el mismo nombre.
    families: dict[int, list[ProcessInfo]] = {}
    for proc in by_pid.values():
        families.setdefault(leader_of(proc).pid, []).append(proc)

    by_root: dict[ProjectRoot, list[DevProcess]] = {}
    unassigned: list[DevProcess] = []

    for leader_pid, members in families.items():
        if any(m.pid in exclude_pids for m in members):
            continue
        leader = by_pid[leader_pid]
        members.sort(key=lambda m: (m.create_time, m.pid))
        ports = tuple(sorted({port for m in members for port in m.ports}))
        root = root_of(leader) or next(
            (r for r in (root_of(m) for m in members) if r is not None), None
        )

        kind = classify(
            leader.name,
            has_ports=bool(ports),
            has_project=root is not None,
            access_denied=leader.access_denied,
        )
        if kind is None:
            continue

        reasons: list[OrphanReason] = []
        if root is None:
            reasons.append(OrphanReason.NO_PROJECT)
        if now - leader.create_time >= long_running_seconds:
            reasons.append(OrphanReason.LONG_RUNNING)
        # Las bases de datos son demonios: es normal que no tengan padre.
        if kind is not ProcessKind.DATABASE and parent_gone(leader):
            reasons.append(OrphanReason.PARENT_GONE)

        # El nombre lo da quien tiene los puertos (suele ser el servidor real,
        # no el lanzador que lo envuelve).
        named_after = next((m for m in members if m.ports), leader)
        dev = DevProcess(
            info=leader,
            kind=kind,
            label=describe(named_after),
            ports=ports,
            pids=tuple(m.pid for m in members),
            orphan_reasons=tuple(reasons),
        )
        if root is None:
            unassigned.append(dev)
        else:
            by_root.setdefault(root, []).append(dev)

    projects = [
        Project(root=root, processes=tuple(sorted(devs, key=_process_order)))
        for root, devs in by_root.items()
    ]
    projects.sort(key=lambda p: (p.name.casefold(), str(p.path)))
    unassigned.sort(key=_process_order)
    return Snapshot(projects=tuple(projects), unassigned=tuple(unassigned))


def _process_order(dev: DevProcess) -> tuple:
    """Primero los que tienen puertos (por puerto), luego por nombre."""
    return (not dev.ports, dev.ports, dev.label.casefold(), dev.pid)
