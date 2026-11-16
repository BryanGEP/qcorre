"""Tests del recolector: procesos reales y procesos simulados que niegan acceso."""

import os
import socket
from contextlib import contextmanager

import psutil

from qcorre.collectors import processes as collector
from qcorre.models import Snapshot
from qcorre.scanner import Scanner


class FakeProc:
    """Imita a ``psutil.Process``; cada método puede lanzar una excepción."""

    def __init__(self, pid=42, **behaviour):
        self.pid = pid
        self._behaviour = {
            "name": "node.exe",
            "create_time": 123.0,
            "ppid": 7,
            "cwd": "C:\\proyecto",
            "cmdline": ["node.exe", "server.js"],
            "exe": "C:\\node\\node.exe",
            **behaviour,
        }

    @contextmanager
    def oneshot(self):
        yield

    def __getattr__(self, attr):
        value = self._behaviour[attr]

        def method(*args, **kwargs):
            if isinstance(value, BaseException):
                raise value
            return value

        return method


def test_lee_un_proceso_normal():
    info = collector.read_process(FakeProc(), {42: {3000, 9229}})
    assert info.pid == 42
    assert info.name == "node.exe"
    assert info.cwd == "C:\\proyecto"
    assert info.cmdline == ("node.exe", "server.js")
    assert info.ports == (3000, 9229)
    assert info.ppid == 7
    assert not info.access_denied


def test_acceso_denegado_no_truena_y_se_marca():
    denied = psutil.AccessDenied(42)
    proc = FakeProc(name="mysqld.exe", cwd=denied, cmdline=denied, exe=denied)
    info = collector.read_process(proc, {42: {3306}})
    assert info is not None
    assert info.access_denied
    assert info.name == "mysqld.exe"
    assert info.cwd is None and info.cmdline == () and info.exe is None
    assert info.ports == (3306,)  # los puertos vienen de la tabla global


def test_todo_denegado_incluso_el_nombre():
    denied = psutil.AccessDenied(42)
    proc = FakeProc(
        name=denied, create_time=denied, ppid=denied, cwd=denied, cmdline=denied, exe=denied
    )
    info = collector.read_process(proc, {})
    assert info.name == "?"
    assert info.ppid is None
    assert info.access_denied


def test_errores_crudos_del_sistema_cuentan_como_sin_permiso():
    info = collector.read_process(FakeProc(cwd=PermissionError(5, "Access is denied")), {})
    assert info.access_denied
    assert info.cwd is None


def test_proceso_que_muere_a_media_lectura_se_omite():
    assert collector.read_process(FakeProc(cwd=psutil.NoSuchProcess(42)), {}) is None
    assert collector.read_process(FakeProc(name=psutil.ZombieProcess(42)), {}) is None


def test_el_pid_cero_se_omite():
    assert collector.read_process(FakeProc(pid=0), {}) is None


def test_puertos_por_proceso_cuando_no_hay_tabla_global():
    # Así es en macOS sin root: se pregunta a cada proceso y puede negarse.
    proc = FakeProc(net_connections=psutil.AccessDenied(42))
    info = collector.read_process(proc, None)
    assert info.ports == ()


# ── Contra el sistema real ──────────────────────────────────────


def test_collect_processes_incluye_a_este_proceso():
    infos = {info.pid: info for info in collector.collect_processes()}
    me = infos[os.getpid()]
    assert me.cwd is not None
    assert os.path.samefile(me.cwd, os.getcwd())
    assert me.create_time > 0


def test_detecta_un_puerto_en_escucha():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]
        infos = {info.pid: info for info in collector.collect_processes()}
    assert port in infos[os.getpid()].ports


def test_self_and_ancestors_incluye_a_este_proceso():
    pids = collector.self_and_ancestors()
    assert os.getpid() in pids
    assert os.getppid() in pids


def test_scanner_devuelve_un_snapshot_y_no_lista_a_qcorre():
    snapshot = Scanner()()
    assert isinstance(snapshot, Snapshot)
    shown = {pid for p in snapshot.projects for d in p.processes for pid in d.pids}
    shown |= {pid for d in snapshot.unassigned for pid in d.pids}
    assert os.getpid() not in shown


def test_scanner_siempre_muestra_el_proyecto_fijado(tmp_path):
    from qcorre.projects.resolver import ProjectResolver

    project = tmp_path / "code" / "mi-proyecto"
    (project / ".git").mkdir(parents=True)
    (project / "src").mkdir()
    scanner = Scanner(resolver=ProjectResolver(home=tmp_path), pinned=[project / "src"])
    snapshot = scanner()
    pinned = [p for p in snapshot.projects if p.name == "mi-proyecto"]
    assert len(pinned) == 1
    assert pinned[0].processes == () and pinned[0].has_git


def test_scanner_ignora_una_carpeta_fijada_que_no_es_proyecto(tmp_path):
    from qcorre.projects.resolver import ProjectResolver

    folder = tmp_path / "suelta"
    folder.mkdir()
    snapshot = Scanner(resolver=ProjectResolver(home=tmp_path), pinned=[folder])()
    assert all(p.name != "suelta" for p in snapshot.projects)
