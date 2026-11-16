"""Cierra procesos junto con todos sus descendientes.

Se trabaja en dos tiempos para que la interfaz pueda mostrar *exactamente* qué
se va a cerrar antes de hacerlo:

1. ``preview`` devuelve las víctimas: el proceso líder y todo lo que cuelga
   de él en ese momento.
2. ``kill`` las cierra: primero pide terminar (SIGTERM) y, tras un tiempo de
   gracia, fuerza a las que sigan vivas (SIGKILL). En Windows no existe el
   cierre amable: terminar ya es forzar.

Protecciones: nunca se toca al propio qcorre ni a sus ancestros, y cada PID se
verifica contra su fecha de creación para no matar a otro proceso que haya
reutilizado el número.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import psutil

from qcorre.collectors.processes import self_and_ancestors
from qcorre.models import DevProcess

# PIDs del sistema que jamás se tocan (kernel/idle, init, System de Windows).
_SYSTEM_PIDS = frozenset({0, 1, 4})

# Margen al comparar fechas de creación (segundos).
_TIME_TOLERANCE = 1.0


@dataclass(frozen=True)
class Victim:
    """Un proceso del sistema que se va a cerrar."""

    pid: int
    name: str
    create_time: float = 0.0  # 0 = no se pudo leer; no se verifica


@dataclass(frozen=True)
class KillResult:
    """Qué pasó al cerrar."""

    closed: int = 0
    denied: tuple[Victim, ...] = ()  # el sistema no dio permiso
    survivors: tuple[Victim, ...] = ()  # siguen vivos pese a forzarlos

    @property
    def failed(self) -> int:
        return len(self.denied) + len(self.survivors)


class Killer:
    """Cierra procesos del sistema. La interfaz recibe uno (real o falso)."""

    def __init__(self, grace_seconds: float = 3.0) -> None:
        self.grace_seconds = grace_seconds

    def preview(self, process: DevProcess) -> list[Victim]:
        """Lo que se cerraría al matar ``process``: el líder y sus descendientes.

        Devuelve una lista vacía si el proceso ya no existe (o su PID ahora
        pertenece a otro).
        """
        protected = self_and_ancestors() | _SYSTEM_PIDS
        try:
            leader = psutil.Process(process.pid)
        except psutil.Error:
            return []
        if not _same_process(leader, process.info.create_time):
            return []
        try:
            family = [leader, *leader.children(recursive=True)]
        except psutil.Error:
            family = [leader]

        victims: list[Victim] = []
        for proc in family:
            if proc.pid in protected:
                continue
            victim = _to_victim(proc, fallback_name=process.info.name)
            if victim is not None:
                victims.append(victim)
        return victims

    def kill(self, victims: Sequence[Victim]) -> KillResult:
        """Cierra las víctimas (los hijos primero) y cuenta el resultado."""
        protected = self_and_ancestors() | _SYSTEM_PIDS
        alive: dict[int, tuple[psutil.Process, Victim]] = {}
        closed = 0
        for victim in victims:
            if victim.pid in protected:
                continue
            try:
                proc = psutil.Process(victim.pid)
            except psutil.NoSuchProcess:
                closed += 1  # ya no estaba: objetivo cumplido
                continue
            except psutil.Error:
                continue
            if not _same_process(proc, victim.create_time):
                closed += 1  # el original murió y otro heredó el PID
                continue
            alive[victim.pid] = (proc, victim)

        denied: list[Victim] = []
        pending: list[psutil.Process] = []
        for proc, victim in reversed(list(alive.values())):
            try:
                proc.terminate()
                pending.append(proc)
            except psutil.NoSuchProcess:
                closed += 1
            except (psutil.AccessDenied, OSError):
                denied.append(victim)

        gone, stubborn = psutil.wait_procs(pending, timeout=self.grace_seconds)
        closed += len(gone)
        for proc in stubborn:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass
            except (psutil.AccessDenied, OSError):
                pass
        gone, stubborn = psutil.wait_procs(stubborn, timeout=1.0)
        closed += len(gone)
        survivors = [alive[proc.pid][1] for proc in stubborn]
        return KillResult(closed=closed, denied=tuple(denied), survivors=tuple(survivors))


def _same_process(proc: psutil.Process, expected_create_time: float) -> bool:
    """¿Sigue siendo el mismo proceso que vimos, y no otro con su PID?"""
    if expected_create_time <= 0:
        return True  # no hay con qué comparar
    try:
        return abs(proc.create_time() - expected_create_time) <= _TIME_TOLERANCE
    except psutil.NoSuchProcess:
        return False
    except psutil.Error:
        return True  # sin permiso para leerla: no se puede descartar


def _to_victim(proc: psutil.Process, fallback_name: str) -> Victim | None:
    try:
        name = proc.name()
    except psutil.NoSuchProcess:
        return None
    except psutil.Error:
        name = fallback_name
    try:
        create_time = proc.create_time()
    except psutil.NoSuchProcess:
        return None
    except psutil.Error:
        create_time = 0.0
    return Victim(pid=proc.pid, name=name, create_time=create_time)
