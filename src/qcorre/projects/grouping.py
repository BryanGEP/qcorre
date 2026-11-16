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
from qcorre.projects.classify import (
    base_name,
    classify,
    describe,
    is_command_shell,
    is_launcher,
)
from qcorre.projects.resolver import ProjectResolver

# Un proceso que lleva más de esto corriendo se marca como huérfano.
DEFAULT_LONG_RUNNING_SECONDS = 24 * 60 * 60

# Tope al subir por la cadena de padres (evita ciclos por PIDs reutilizados).
_MAX_DEPTH = 12

# Separador entre el lanzador y lo que lanzó: "npm run dev → vite".
CHAIN_ARROW = " → "


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
    3. Un lanzador sin puertos (``npm run dev``) se funde con los servidores
       del mismo proyecto que cuelgan de él: "npm run dev → vite".
    4. Se descartan los que no son de desarrollo.
    5. Se marcan los huérfanos: sin proyecto, con demasiado tiempo corriendo o
       con el padre muerto.

    ``init_pids`` son los PIDs que adoptan procesos huérfanos (1 en Unix);
    ``exclude_pids`` son procesos que no deben aparecer (el propio qcorre).
    """
    by_pid = {p.pid: p for p in processes}

    def parent_of(proc: ProcessInfo) -> ProcessInfo | None:
        """Padre vivo y verdadero de ``proc``, o ``None``.

        Los PIDs se reutilizan (sobre todo en Windows): el padre solo es válido
        si nació antes que el hijo. Si es más joven, es otro proceso que heredó
        el número, y el padre real ya murió.
        """
        if proc.ppid is None or proc.ppid == proc.pid:
            return None
        parent = by_pid.get(proc.ppid)
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

    def parent_gone(proc: ProcessInfo) -> bool:
        if proc.ppid is None or proc.ppid == 0:
            return False  # desconocido o lanzado por el propio sistema
        return proc.ppid in init_pids or parent_of(proc) is None

    # ── Paso 2: familias de procesos con el mismo nombre ────────
    leader_pid: dict[int, int] = {}
    for proc in by_pid.values():
        name = base_name(proc.name)
        current = proc
        for _ in range(_MAX_DEPTH):
            parent = parent_of(current)
            if parent is None or base_name(parent.name) != name:
                break
            current = parent
        leader_pid[proc.pid] = current.pid

    families: dict[int, _Family] = {}
    for proc in by_pid.values():
        leader = by_pid[leader_pid[proc.pid]]
        family = families.get(leader.pid)
        if family is None:
            family = families[leader.pid] = _Family(leader)
        family.members.append(proc)
    for family in families.values():
        family.root = root_of(family.leader) or next(
            (r for r in map(root_of, family.members) if r is not None), None
        )

    # ── Paso 3: lanzador + servidores que cuelgan de él ─────────
    # Se procesa de los más viejos a los más nuevos para que las cadenas
    # anidadas (npm → nodemon → node) se resuelvan en orden.
    absorbed: set[int] = set()
    for family in sorted(families.values(), key=lambda f: f.leader.create_time):
        if family.leader.pid in absorbed or not family.ports or family.root is None:
            continue
        head = _find_launcher(family, families, leader_pid, parent_of)
        while head is not None:
            head.chained.append(family)
            absorbed.add(family.leader.pid)
            if head.leader.pid in absorbed:
                break  # el lanzador ya estaba colgado de otro más arriba
            family = head
            head = _find_launcher(family, families, leader_pid, parent_of)

    # ── Pasos 4 y 5: clasificar y marcar huérfanos ──────────────
    by_root: dict[ProjectRoot, list[DevProcess]] = {}
    unassigned: list[DevProcess] = []

    for family in families.values():
        if family.leader.pid in absorbed:
            continue
        everyone = family.all_members()
        if any(m.pid in exclude_pids for m in everyone):
            continue
        leader, root, ports = family.leader, family.root, family.ports

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

        members = sorted(everyone, key=lambda m: (m.create_time, m.pid))
        parent = parent_of(leader)
        dev = DevProcess(
            info=leader,
            kind=kind,
            label=family.label(),
            ports=ports,
            pids=tuple(m.pid for m in members),
            orphan_reasons=tuple(reasons),
            members=tuple(members),
            parent_name=parent.name if parent is not None else None,
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


def with_pinned(snapshot: Snapshot, roots: Iterable[ProjectRoot]) -> Snapshot:
    """Añade al ``Snapshot`` proyectos fijos, aunque no tengan procesos.

    Sirve para que el proyecto desde el que se abrió qcorre aparezca siempre:
    así se puede ver su git aunque no haya nada corriendo.
    """
    present = {project.root for project in snapshot.projects}
    extra = [Project(root=root, processes=()) for root in dict.fromkeys(roots) if root not in present]
    if not extra:
        return snapshot
    projects = sorted(
        [*snapshot.projects, *extra], key=lambda p: (p.name.casefold(), str(p.path))
    )
    return Snapshot(projects=tuple(projects), unassigned=snapshot.unassigned)


class _Family:
    """Procesos que se muestran como una sola fila."""

    def __init__(self, leader: ProcessInfo) -> None:
        self.leader = leader
        self.members: list[ProcessInfo] = []
        self.root: ProjectRoot | None = None
        # Familias con puertos que cuelgan de esta (si esta es un lanzador).
        self.chained: list[_Family] = []
        # Shells intermedios (`cmd /c`, `sh -c`) entre esta familia y su lanzador.
        self.shells: list[ProcessInfo] = []

    def all_members(self) -> list[ProcessInfo]:
        """Los miembros propios más los de las familias colgadas y sus shells."""
        everyone = list(self.members)
        for family in self.chained:
            everyone.extend(family.shells)
            everyone.extend(family.all_members())
        return everyone

    @property
    def has_own_ports(self) -> bool:
        return any(m.ports for m in self.members)

    @property
    def ports(self) -> tuple[int, ...]:
        return tuple(sorted({port for m in self.all_members() for port in m.ports}))

    def label(self) -> str:
        head = describe(self.leader)
        if self.chained:
            chained = sorted(self.chained, key=lambda f: f.ports)
            targets = list(dict.fromkeys(f.label() for f in chained))
            return head + CHAIN_ARROW + ", ".join(targets)
        # El nombre lo da quien tiene los puertos (suele ser el servidor real,
        # no el proceso que lo envuelve).
        owner = describe(next((m for m in self.members if m.ports), self.leader))
        if owner != head and is_launcher(self.leader):
            return head + CHAIN_ARROW + owner
        return owner


def _find_launcher(family, families, leader_pid, parent_of) -> _Family | None:
    """Busca hacia arriba un lanzador sin puertos del mismo proyecto.

    Entre la familia y su lanzador solo puede haber shells de un solo comando
    (``cmd /c ...``, ``sh -c ...``), que es lo que usan npm y compañía para
    lanzar scripts. No se atraviesan shells interactivos ni otros programas,
    para no tragarse la terminal o el editor desde donde se lanzó todo.
    """
    shells: list[ProcessInfo] = []
    ancestor = parent_of(family.leader)
    for _ in range(_MAX_DEPTH):
        if ancestor is None:
            return None
        candidate = families[leader_pid[ancestor.pid]]
        if candidate is family or candidate.root != family.root:
            return None
        if candidate.has_own_ports:
            return None
        if is_launcher(candidate.leader):
            family.shells = shells
            return candidate
        if not is_command_shell(ancestor):
            return None
        shells.append(ancestor)
        ancestor = parent_of(ancestor)
    return None


def _process_order(dev: DevProcess) -> tuple:
    """Primero los que tienen puertos (por puerto), luego por nombre."""
    return (not dev.ports, dev.ports, dev.label.casefold(), dev.pid)
