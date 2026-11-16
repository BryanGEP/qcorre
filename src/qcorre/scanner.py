"""Une la recolección (psutil) con la agrupación por proyecto.

La interfaz solo conoce esta pieza: la llama y recibe un ``Snapshot``. En los
tests y en el modo demo se sustituye por una función que devuelve datos fijos.
"""

from __future__ import annotations

import time

from qcorre.collectors import processes as collector
from qcorre.models import Snapshot
from qcorre.projects.grouping import DEFAULT_LONG_RUNNING_SECONDS, group_processes
from qcorre.projects.resolver import ProjectResolver

# Cada cuántos escaneos se olvida la caché de rutas, para detectar repos
# creados o borrados mientras qcorre está abierto.
_CACHE_LIFETIME = 20


class Scanner:
    """Escanea el sistema y devuelve los procesos agrupados por proyecto."""

    def __init__(
        self,
        resolver: ProjectResolver | None = None,
        long_running_seconds: float = DEFAULT_LONG_RUNNING_SECONDS,
    ) -> None:
        self.resolver = resolver or ProjectResolver()
        self.long_running_seconds = long_running_seconds
        self._scans = 0

    def __call__(self) -> Snapshot:
        self._scans += 1
        if self._scans % _CACHE_LIFETIME == 0:
            self.resolver.clear()
        return group_processes(
            collector.collect_processes(),
            self.resolver,
            now=time.time(),
            long_running_seconds=self.long_running_seconds,
            init_pids=collector.init_pids(),
            exclude_pids=collector.self_and_ancestors(),
        )
