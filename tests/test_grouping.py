"""Tests de la agrupación de procesos por proyecto y de los huérfanos."""

from pathlib import Path

import pytest

from qcorre.models import OrphanReason, ProcessInfo, ProcessKind
from qcorre.projects.grouping import group_processes
from qcorre.projects.resolver import ProjectResolver

NOW = 1_000_000.0
HOUR = 3600.0


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def resolver(home: Path) -> ProjectResolver:
    return ProjectResolver(home=home)


def repo(home: Path, name: str) -> str:
    path = home / "code" / name
    (path / ".git").mkdir(parents=True)
    return str(path)


def proc(pid: int, name: str, *, age: float = HOUR, ppid: int | None = 100, **kwargs):
    """Proceso de prueba. Por defecto su padre es la terminal (pid 100)."""
    return ProcessInfo(pid=pid, name=name, create_time=NOW - age, ppid=ppid, **kwargs)


# La terminal desde la que se lanzó todo: viva y sin proyecto.
SHELL = ProcessInfo(pid=100, name="bash", create_time=NOW - 48 * HOUR, ppid=0)


def group(resolver, *processes, **kwargs):
    return group_processes([SHELL, *processes], resolver, now=NOW, **kwargs)


def test_agrupa_por_repo_y_ordena(home, resolver):
    api, web = repo(home, "tienda-api"), repo(home, "Blog")
    snapshot = group(
        resolver,
        proc(1, "node", cwd=web, ports=(5173,)),
        proc(2, "redis-server", cwd=api, ports=(6379,)),
        proc(3, "python", cwd=api, ports=(8000,), cmdline=("python", "-m", "uvicorn")),
        proc(4, "python", cwd=api + "/scripts", cmdline=("python", "watch.py")),
    )
    assert [p.name for p in snapshot.projects] == ["Blog", "tienda-api"]
    api_project = snapshot.projects[1]
    assert api_project.has_git
    # Primero los que tienen puerto (por número), luego el resto.
    assert [(d.label, d.ports) for d in api_project.processes] == [
        ("redis-server", (6379,)),
        ("uvicorn", (8000,)),
        ("python watch.py", ()),
    ]
    assert [d.kind for d in api_project.processes] == [
        ProcessKind.DATABASE,
        ProcessKind.SERVER,
        ProcessKind.TOOL,
    ]
    assert snapshot.unassigned == ()
    assert snapshot.process_count == 4
    assert not any(d.is_orphan for p in snapshot.projects for d in p.processes)


def test_descarta_lo_que_no_es_de_desarrollo(home, resolver):
    snapshot = group(
        resolver,
        proc(1, "svchost.exe", ports=(135,)),
        proc(2, "python"),  # sin puerto ni proyecto: ruido
        proc(3, "chrome", cwd=repo(home, "x"), ports=(9222,)),
    )
    assert snapshot.projects == ()
    assert snapshot.unassigned == ()


def test_sin_proyecto_va_a_huerfanos(resolver):
    snapshot = group(resolver, proc(1, "node", ports=(3000,), cwd="/"))
    assert snapshot.projects == ()
    (orphan,) = snapshot.unassigned
    assert orphan.orphan_reasons == (OrphanReason.NO_PROJECT,)
    assert orphan.is_orphan


def test_mucho_tiempo_corriendo_es_huerfano_pero_sigue_en_su_proyecto(home, resolver):
    api = repo(home, "api")
    snapshot = group(
        resolver,
        proc(1, "node", cwd=api, ports=(3000,), age=30 * HOUR),
        proc(2, "node", cwd=api, ports=(3001,), age=2 * HOUR),
    )
    old, recent = snapshot.projects[0].processes
    assert old.orphan_reasons == (OrphanReason.LONG_RUNNING,)
    assert recent.orphan_reasons == ()
    assert old.uptime(NOW) == 30 * HOUR


def test_umbral_de_tiempo_configurable(home, resolver):
    api = repo(home, "api")
    snapshot = group(
        resolver, proc(1, "node", cwd=api, ports=(3000,), age=2 * HOUR), long_running_seconds=HOUR
    )
    assert snapshot.projects[0].processes[0].orphan_reasons == (OrphanReason.LONG_RUNNING,)


def test_padre_muerto(home, resolver):
    api = repo(home, "api")
    snapshot = group(
        resolver,
        proc(11, "node", cwd=api, ports=(3000,), ppid=999),  # el padre ya no existe
        proc(12, "node", cwd=api, ports=(3001,), ppid=1),  # adoptado por init
        proc(13, "node", cwd=api, ports=(3002,), ppid=None),  # padre desconocido
        proc(14, "node", cwd=api, ports=(3003,), ppid=100),  # padre vivo
        init_pids=frozenset({1}),
    )
    reasons = [d.orphan_reasons for d in snapshot.projects[0].processes]
    assert reasons == [(OrphanReason.PARENT_GONE,), (OrphanReason.PARENT_GONE,), (), ()]


def test_pid_de_padre_reutilizado_cuenta_como_padre_muerto(home, resolver):
    api = repo(home, "api")
    snapshot = group(
        resolver,
        # El "padre" 50 nació después que el hijo: es otro proceso con el mismo PID.
        proc(50, "notepad", age=1 * HOUR),
        proc(1, "node", cwd=api, ports=(3000,), ppid=50, age=5 * HOUR),
    )
    assert snapshot.projects[0].processes[0].orphan_reasons == (OrphanReason.PARENT_GONE,)


def test_base_de_datos_sin_padre_no_es_huerfana_por_eso(home, resolver):
    api = repo(home, "api")
    snapshot = group(
        resolver, proc(1, "postgres", cwd=api, ports=(5432,), ppid=1), init_pids=frozenset({1})
    )
    assert snapshot.projects[0].processes[0].orphan_reasons == ()


def test_el_hijo_hereda_el_proyecto_del_padre(home, resolver):
    api = repo(home, "api")
    snapshot = group(
        resolver,
        proc(1, "cmd.exe", cwd=api, age=2 * HOUR),
        proc(2, "node", cwd="/", ports=(3000,), ppid=1),
    )
    (project,) = snapshot.projects
    assert [d.pid for d in project.processes] == [2]  # cmd.exe no es de desarrollo


def test_servidor_y_trabajadores_se_funden_en_una_fila(home, resolver):
    api = repo(home, "api")
    snapshot = group(
        resolver,
        # Lanzador del venv en Windows: no tiene puertos, su hijo sí.
        proc(1, "python.exe", cwd=api, age=3 * HOUR, cmdline=("python.exe", "-m", "uvicorn")),
        proc(2, "python.exe", cwd=api, age=2.9 * HOUR, ppid=1, ports=(8000,),
             cmdline=("python.exe", "-m", "uvicorn")),
        proc(3, "python.exe", cwd=api, age=2.8 * HOUR, ppid=2),
        proc(4, "python.exe", cwd=api, age=2.8 * HOUR, ppid=2),
    )  # fmt: skip
    (row,) = snapshot.projects[0].processes
    assert row.pid == 1  # el líder es a quien hay que matar
    assert row.pids == (1, 2, 3, 4)
    assert row.ports == (8000,)
    assert row.label == "uvicorn"
    assert row.kind is ProcessKind.SERVER


def test_procesos_con_el_mismo_nombre_sin_parentesco_no_se_funden(home, resolver):
    api = repo(home, "api")
    snapshot = group(
        resolver,
        proc(1, "node", cwd=api, ports=(3000,)),
        proc(2, "node", cwd=api, ports=(3001,)),
    )
    assert len(snapshot.projects[0].processes) == 2


def test_excluye_al_propio_qcorre_y_su_familia(home, resolver):
    api = repo(home, "api")
    snapshot = group(
        resolver,
        proc(1, "python", cwd=api, age=2 * HOUR),
        proc(2, "python", cwd=api, ppid=1),
        exclude_pids=frozenset({2}),
    )
    assert snapshot.projects == ()


def test_sin_permiso_se_muestra_como_huerfano(resolver):
    snapshot = group(resolver, proc(1, "mysqld.exe", ppid=None, access_denied=True))
    (row,) = snapshot.unassigned
    assert row.access_denied
    assert row.kind is ProcessKind.DATABASE
    assert row.label == "mysqld"
    assert row.orphan_reasons == (OrphanReason.NO_PROJECT,)


def test_proyecto_sin_git(home, resolver):
    folder = home / "scripts" / "bot"
    folder.mkdir(parents=True)
    (folder / "pyproject.toml").touch()
    snapshot = group(resolver, proc(1, "python", cwd=str(folder), ports=(8080,)))
    (project,) = snapshot.projects
    assert project.name == "bot"
    assert not project.has_git


def test_lista_vacia(resolver):
    snapshot = group_processes([], resolver, now=NOW)
    assert snapshot.projects == () and snapshot.unassigned == ()
    assert snapshot.process_count == 0
