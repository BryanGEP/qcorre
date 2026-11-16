"""Tests del cierre de procesos, con procesos reales de corta vida."""

import os
import subprocess
import sys
import time

import psutil
import pytest

from qcorre.collectors.killer import Killer, KillResult, Victim
from qcorre.models import DevProcess, ProcessInfo, ProcessKind

# Un proceso que lanza un hijo y ambos se quedan esperando.
PARENT_CODE = (
    "import subprocess, sys, time;"
    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)']);"
    "time.sleep(120)"
)


def as_dev(pid: int, create_time: float | None = None) -> DevProcess:
    if create_time is None:
        create_time = psutil.Process(pid).create_time()
    info = ProcessInfo(pid=pid, name="python", create_time=create_time)
    return DevProcess(info=info, kind=ProcessKind.TOOL, label="python", pids=(pid,))


def wait_for_children(pid: int, count: int = 1) -> list[psutil.Process]:
    deadline = time.time() + 10
    while time.time() < deadline:
        children = psutil.Process(pid).children(recursive=True)
        if len(children) >= count:
            return children
        time.sleep(0.05)
    raise AssertionError("el proceso de prueba no lanzó a su hijo")


@pytest.fixture
def family():
    """Proceso padre con un hijo; se limpia pase lo que pase."""
    parent = subprocess.Popen([sys.executable, "-c", PARENT_CODE])
    children = wait_for_children(parent.pid)
    yield parent, children
    for proc in [*children, psutil.Process(parent.pid) if parent.poll() is None else None]:
        try:
            if proc is not None:
                proc.kill()
        except psutil.Error:
            pass
    parent.wait(timeout=5)


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
    gone.wait()
    dev = as_dev(gone.pid, create_time=time.time())
    assert Killer().preview(dev) == []
    assert Killer().kill([Victim(gone.pid, "python", time.time())]) == KillResult(closed=1)


def test_nunca_se_mata_a_si_mismo():
    killer = Killer()
    assert killer.preview(as_dev(os.getpid())) == []
    me = Victim(os.getpid(), "python", psutil.Process().create_time())
    assert killer.kill([me]) == KillResult()
