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


def is_alive(proc: psutil.Process) -> bool:
    """¿El proceso sigue vivo de verdad? (un zombi ya murió: solo falta recogerlo)."""
    try:
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def with_descendants(procs: list[psutil.Process]) -> list[psutil.Process]:
    """Los procesos dados y todo lo que cuelga de ellos, sin repetir."""
    tree: dict[int, psutil.Process] = {}
    for proc in procs:
        if not is_alive(proc):
            continue
        tree[proc.pid] = proc
        try:
            for child in proc.children(recursive=True):
                tree.setdefault(child.pid, child)
        except psutil.Error:
            continue
    return list(tree.values())


def kill_marked(
    marker: str, known: tuple[psutil.Process, ...] = (), timeout: float = 10.0
) -> list[psutil.Process]:
    """Mata todos los procesos de prueba y devuelve los que sigan vivos.

    Un proceso tarda un instante en morir, y mientras muere puede no dejarse
    leer (por eso una sola pasada no basta: en macOS llegó a escaparse uno).
    Así que se repite, hasta ``timeout`` segundos:

    1. buscar el árbol completo: los marcados, los ``known`` (procesos que el
       test ya tenía identificados) y todos sus descendientes;
    2. pedirles terminar y esperar un momento;
    3. forzar a los que sigan vivos y esperar otro momento;
    4. volver a buscar, tras una pausa.

    Termina en cuanto dos búsquedas seguidas no encuentran nada. Si se agota
    el tiempo, devuelve lo que quede vivo para que el test falle con razón.
    """
    deadline = time.monotonic() + timeout
    clean_rounds = 0
    while True:
        tree = with_descendants(find_marked(marker) + list(known))
        if not tree:
            clean_rounds += 1
            if clean_rounds >= 2:
                return []
        else:
            clean_rounds = 0
            for proc in tree:
                try:
                    proc.terminate()
                except psutil.Error:
                    pass
            _, stubborn = psutil.wait_procs(tree, timeout=1.5)
            for proc in stubborn:
                try:
                    proc.kill()
                except psutil.Error:
                    pass
            psutil.wait_procs(stubborn, timeout=1.5)
        if time.monotonic() >= deadline:
            return with_descendants(find_marked(marker) + list(known))
        time.sleep(0.2)


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
    known: list[psutil.Process] = []
    try:
        known.append(psutil.Process(parent.pid))
        children = wait_for_family(parent.pid, marker)
        known.extend(children)
        yield parent, children
    finally:
        survivors = kill_marked(marker, tuple(known))
        # Se recoge al proceso lanzado por el test para que no quede como zombi.
        try:
            parent.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        assert survivors == [], f"quedaron procesos de prueba vivos: {survivors}"


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


# ── La propia limpieza de los tests ─────────────────────────────


def spawn_marked(code: str) -> tuple[str, subprocess.Popen]:
    marker = f"qcorre-test-{uuid.uuid4().hex}"
    return marker, subprocess.Popen([sys.executable, "-c", f"{code}  # {marker}"])


def wait_until_marked(marker: str) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if find_marked(marker):
            return
        time.sleep(0.05)
    raise AssertionError("el proceso de prueba no arrancó")


def test_la_limpieza_no_deja_nada_y_no_afirma_antes_de_tiempo():
    marker, proc = spawn_marked(f"import time; time.sleep({LIFETIME})")
    try:
        wait_until_marked(marker)
        assert kill_marked(marker) == []
        # Tras limpiar, una búsqueda inmediata tampoco encuentra nada vivo.
        assert [p for p in find_marked(marker) if is_alive(p)] == []
    finally:
        proc.kill()
        proc.wait(timeout=10)


def test_la_limpieza_fuerza_a_un_proceso_que_ignora_la_peticion_de_terminar():
    code = (
        "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"time.sleep({LIFETIME})"
    )
    marker, proc = spawn_marked(code)
    try:
        wait_until_marked(marker)
        time.sleep(0.3)  # que alcance a instalar su manejador de señales
        assert kill_marked(marker) == []
        proc.wait(timeout=10)
        assert proc.returncode is not None
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)


def test_la_limpieza_alcanza_a_los_hijos_aunque_no_lleven_la_marca():
    # El hijo no lleva la marca en su línea de comandos: solo se le encuentra
    # por ser descendiente de un proceso marcado.
    code = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', 'import time; time.sleep({LIFETIME})']); "
        f"time.sleep({LIFETIME})"
    )
    marker, proc = spawn_marked(code)
    try:
        wait_until_marked(marker)
        deadline = time.monotonic() + 15
        children: list[psutil.Process] = []
        while time.monotonic() < deadline and len(children) < 1:
            children = [
                c
                for c in psutil.Process(proc.pid).children(recursive=True)
                if not any(marker in arg for arg in _cmdline(c))
            ]
            time.sleep(0.05)
        assert children, "el proceso de prueba no lanzó a su hijo"
        assert kill_marked(marker) == []
        assert not any(is_alive(child) for child in children)
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)


def test_si_un_proceso_sobrevive_la_limpieza_lo_delata(monkeypatch):
    # Si de verdad quedara algo vivo, la limpieza debe decirlo, no callarlo.
    marker, proc = spawn_marked(f"import time; time.sleep({LIFETIME})")
    try:
        wait_until_marked(marker)
        monkeypatch.setattr(psutil.Process, "terminate", lambda self: None)
        monkeypatch.setattr(psutil.Process, "kill", lambda self: None)
        survivors = kill_marked(marker, timeout=1.0)
        assert [p.pid for p in survivors if any(marker in a for a in _cmdline(p))]
    finally:
        monkeypatch.undo()
        assert kill_marked(marker) == []
        proc.wait(timeout=10)
