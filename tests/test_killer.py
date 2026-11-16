"""Tests del cierre de procesos, con procesos reales de corta vida.

Los procesos de prueba llevan una marca única en su línea de comandos. Al
terminar cada test (pase, falle o se interrumpa) se busca esa marca en todo el
sistema y se mata lo que quede, para no dejar procesos sueltos.
"""

import os
import subprocess
import sys
import time
import uuid

import psutil
import pytest

from qcorre.collectors.killer import Killer, KillResult, Victim
from qcorre.models import DevProcess, ProcessInfo, ProcessKind

# Tiempo máximo de vida de los procesos de prueba: aunque todo lo demás
# fallara (por ejemplo, si matan a pytest a la fuerza), se cierran solos.
LIFETIME = 30


def parent_code(marker: str) -> str:
    """Código de un proceso que lanza un hijo y ambos se quedan esperando."""
    child = f"import time; time.sleep({LIFETIME})  # {marker}-hijo"
    lines = [
        f"import subprocess, sys, time  # {marker}-padre",
        f"subprocess.Popen([sys.executable, '-c', {child!r}])",
        f"time.sleep({LIFETIME})",
    ]
    return "\n".join(lines)


def find_marked(marker: str) -> list[psutil.Process]:
    """Todos los procesos del sistema cuya línea de comandos lleva la marca."""
    found = []
    for proc in psutil.process_iter():
        try:
            if any(marker in arg for arg in proc.cmdline()):
                found.append(proc)
        except psutil.Error:
            continue
    return found


def kill_marked(marker: str) -> None:
    procs = find_marked(marker)
    for proc in procs:
        try:
            proc.kill()
        except psutil.Error:
            pass
    psutil.wait_procs(procs, timeout=5)


def as_dev(pid: int, create_time: float | None = None) -> DevProcess:
    if create_time is None:
        create_time = psutil.Process(pid).create_time()
    info = ProcessInfo(pid=pid, name="python", create_time=create_time)
    return DevProcess(info=info, kind=ProcessKind.TOOL, label="python", pids=(pid,))


def wait_for_family(pid: int, marker: str) -> list[psutil.Process]:
    """Espera a que el hijo marcado exista y devuelve todos los descendientes.

    No basta con esperar "algún hijo": en un venv de Windows ``python.exe`` es
    un lanzador que arranca al Python real, así que el primer descendiente
    aparece antes de que el proceso de prueba haya lanzado a su propio hijo.
    """
    deadline = time.time() + 15
    while time.time() < deadline:
        if any(f"{marker}-hijo" in " ".join(_cmdline(p)) for p in find_marked(marker)):
            return psutil.Process(pid).children(recursive=True)
        time.sleep(0.05)
    raise AssertionError("el proceso de prueba no lanzó a su hijo")


def _cmdline(proc: psutil.Process) -> list[str]:
    try:
        return proc.cmdline()
    except psutil.Error:
        return []


@pytest.fixture
def family():
    """Proceso padre con un hijo; se limpia pase lo que pase."""
    marker = f"qcorre-test-{uuid.uuid4().hex}"
    parent = subprocess.Popen([sys.executable, "-c", parent_code(marker)])
    try:
        children = wait_for_family(parent.pid, marker)
        yield parent, children
    finally:
        kill_marked(marker)
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=5)
        assert find_marked(marker) == [], "quedaron procesos de prueba vivos"


def test_preview_incluye_al_lider_y_a_sus_descendientes(family):
    parent, children = family
    victims = Killer().preview(as_dev(parent.pid))
    pids = [v.pid for v in victims]
    assert pids[0] == parent.pid
    assert {c.pid for c in children} <= set(pids)
    assert all(v.name for v in victims)


def test_kill_cierra_toda_la_familia(family):
    parent, children = family
    killer = Killer(grace_seconds=2)
    victims = killer.preview(as_dev(parent.pid))
    result = killer.kill(victims)
    assert result.closed == len(victims)
    assert result.failed == 0
    parent.wait(timeout=5)
    assert not any(c.is_running() and c.status() != psutil.STATUS_ZOMBIE for c in children)


def test_no_mata_si_el_pid_fue_reutilizado(family):
    parent, _ = family
    # La fecha de creación no coincide: es "otro" proceso con el mismo PID.
    stale = as_dev(parent.pid, create_time=psutil.Process(parent.pid).create_time() - 3600)
    assert Killer().preview(stale) == []
    assert parent.poll() is None


def test_kill_verifica_la_fecha_de_cada_victima(family):
    parent, _ = family
    impostor = Victim(pid=parent.pid, name="python", create_time=1.0)
    result = Killer().kill([impostor])
    assert parent.poll() is None  # sigue vivo: no era el que vimos
    assert result.failed == 0


def test_proceso_inexistente():
    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait(timeout=30)
    dev = as_dev(gone.pid, create_time=time.time())
    assert Killer().preview(dev) == []
    assert Killer().kill([Victim(gone.pid, "python", time.time())]) == KillResult(closed=1)


def test_nunca_se_mata_a_si_mismo():
    killer = Killer()
    assert killer.preview(as_dev(os.getpid())) == []
    me = Victim(os.getpid(), "python", psutil.Process().create_time())
    assert killer.kill([me]) == KillResult()
