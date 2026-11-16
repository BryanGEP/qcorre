"""Lee los procesos del sistema y sus puertos en escucha.

Regla de oro: un proceso que no se deja leer nunca truena la recolección.

- Si el sistema niega el acceso (``AccessDenied``, muy común en Windows con
  procesos elevados o de servicio), el proceso se entrega igual, con lo que se
  pudo leer y ``access_denied=True``.
- Si el proceso muere mientras se lee, simplemente se omite.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import TypeVar

import psutil

from qcorre.models import ProcessInfo

T = TypeVar("T")

# Mapa pid -> puertos en escucha. ``None`` significa "no se pudo leer la tabla
# global", y entonces hay que preguntarle a cada proceso.
PortMap = dict[int, set[int]]


def collect_processes() -> list[ProcessInfo]:
    """Devuelve una foto de todos los procesos del sistema."""
    port_map = _global_listening_ports()
    result: list[ProcessInfo] = []
    for proc in psutil.process_iter():
        info = read_process(proc, port_map)
        if info is not None:
            result.append(info)
    return result


def read_process(proc: psutil.Process, port_map: PortMap | None) -> ProcessInfo | None:
    """Lee un proceso. Devuelve ``None`` si ya no existe."""
    try:
        with proc.oneshot():
            pid = proc.pid
            if pid == 0:
                return None  # "System Idle" en Windows, kernel en macOS
            name, _ = _read(proc.name, "")
            create_time, _ = _read(proc.create_time, 0.0)
            ppid, _ = _read(proc.ppid, None)
            cwd, cwd_denied = _read(proc.cwd, None)
            cmdline, cmd_denied = _read(proc.cmdline, [])
            exe, _ = _read(proc.exe, None)
            if port_map is not None:
                ports = port_map.get(pid, set())
            else:
                ports = _process_listening_ports(proc)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return None

    return ProcessInfo(
        pid=pid,
        name=name or "?",
        cmdline=tuple(cmdline or ()),
        cwd=cwd or None,
        exe=exe or None,
        ports=tuple(sorted(ports)),
        create_time=create_time or 0.0,
        ppid=ppid,
        access_denied=cwd_denied or cmd_denied,
    )


def self_and_ancestors() -> frozenset[int]:
    """PIDs del propio qcorre y de quienes lo lanzaron (para no listarlos)."""
    pids = {os.getpid()}
    try:
        pids.update(parent.pid for parent in psutil.Process().parents())
    except psutil.Error:
        pass
    return frozenset(pids)


def init_pids() -> frozenset[int]:
    """PIDs que adoptan a los procesos cuyo padre murió.

    En Unix un huérfano pasa a ser hijo del proceso 1. En Windows no existe
    esa adopción: el hijo conserva el PID del padre muerto.
    """
    return frozenset({1}) if os.name == "posix" else frozenset()


# ── Internos ────────────────────────────────────────────────────


def _read(getter: Callable[[], T], default: T) -> tuple[T, bool]:
    """Llama a un método de psutil sin dejar que truene.

    Devuelve ``(valor, acceso_denegado)``. ``NoSuchProcess`` sí se propaga: el
    proceso ya no existe y no tiene sentido seguir leyéndolo.
    """
    try:
        return getter(), False
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        raise
    except psutil.AccessDenied:
        return default, True
    except (OSError, SystemError, ValueError):
        # Windows a veces responde con errores crudos del sistema en procesos
        # protegidos; para el usuario es lo mismo: no se pudo leer.
        return default, True


def _global_listening_ports() -> PortMap | None:
    """Puertos TCP en escucha de todo el sistema, en una sola consulta.

    Funciona sin permisos especiales en Windows y Linux. En macOS exige ser
    root: ahí devuelve ``None`` y se consulta proceso por proceso.
    """
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError, OSError, RuntimeError):
        return None
    port_map: PortMap = {}
    for conn in connections:
        if conn.status == psutil.CONN_LISTEN and conn.pid and conn.laddr:
            port_map.setdefault(conn.pid, set()).add(conn.laddr.port)
    return port_map


def _process_listening_ports(proc: psutil.Process) -> set[int]:
    try:
        connections = proc.net_connections(kind="inet")
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        raise
    except (psutil.Error, OSError):
        return set()
    return {
        conn.laddr.port
        for conn in connections
        if conn.status == psutil.CONN_LISTEN and conn.laddr
    }
