"""Tests de la detección de la raíz del proyecto.

Se usa una carpeta temporal como "carpeta personal" (home) para que los tests
no dependan de la máquina donde corren.
"""

from pathlib import Path

import pytest

from qcorre.models import ProcessInfo
from qcorre.projects.resolver import ProjectResolver


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def resolver(home: Path) -> ProjectResolver:
    return ProjectResolver(home=home)


def make(path: Path, *files: str) -> Path:
    """Crea una carpeta con los archivos (vacíos) o subcarpetas indicados."""
    path.mkdir(parents=True, exist_ok=True)
    for name in files:
        target = path / name
        if name.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
    return path


def test_encuentra_el_repo_git_desde_una_subcarpeta(home, resolver):
    repo = make(home / "code" / "tienda", ".git/", "src/api/")
    root = resolver.find_root(repo / "src" / "api")
    assert root is not None
    assert root.path == repo
    assert root.has_git
    assert root.name == "tienda"


def test_git_como_archivo_cuenta_como_repo(home, resolver):
    # En worktrees y submódulos `.git` es un archivo, no una carpeta.
    worktree = make(home / "code" / "tienda-hotfix", ".git")
    root = resolver.find_root(worktree)
    assert root is not None and root.has_git


def test_el_repo_gana_a_los_marcadores_intermedios(home, resolver):
    repo = make(home / "mono", ".git/", "apps/web/package.json")
    root = resolver.find_root(repo / "apps" / "web")
    assert root is not None
    assert root.path == repo


def test_un_submodulo_es_su_propio_proyecto(home, resolver):
    repo = make(home / "padre", ".git/")
    sub = make(repo / "libs" / "hijo", ".git")
    assert resolver.find_root(sub).path == sub


def test_proyecto_sin_git_usa_el_marcador_mas_cercano(home, resolver):
    project = make(home / "scripts" / "bot", "pyproject.toml", "bot/")
    root = resolver.find_root(project / "bot")
    assert root is not None
    assert root.path == project
    assert not root.has_git


def test_carpeta_sin_nada_no_es_proyecto(home, resolver):
    folder = make(home / "Downloads" / "cosas")
    assert resolver.find_root(folder) is None


def test_la_carpeta_personal_nunca_es_un_proyecto(home, resolver):
    # Hay quien versiona sus dotfiles con un repo en la carpeta personal.
    make(home, ".git/", "package.json")
    folder = make(home / "Documents")
    assert resolver.find_root(home) is None
    assert resolver.find_root(folder) is None


def test_carpetas_ocultas_no_son_proyectos(home, resolver):
    # ~/.nvm es un clon de git, pero no es un proyecto del usuario.
    nvm = make(home / ".nvm", ".git/", "versions/node/bin/")
    assert resolver.find_root(nvm / "versions" / "node" / "bin") is None


def test_el_entorno_virtual_resuelve_al_proyecto(home, resolver):
    repo = make(home / "code" / "api", ".git/", ".venv/bin/python")
    assert resolver.find_root(repo / ".venv" / "bin" / "python").path == repo


def test_node_modules_no_es_un_proyecto(home, resolver):
    # Proyecto sin git: el package.json de una dependencia no debe ganar.
    project = make(home / "web", "package.json", "node_modules/vite/package.json")
    root = resolver.find_root(project / "node_modules" / "vite" / "bin" / "vite.js")
    assert root is not None
    assert root.path == project


def test_rutas_invalidas_o_relativas(resolver):
    assert resolver.find_root(None) is None
    assert resolver.find_root("") is None
    assert resolver.find_root("relativa/sin/raiz") is None


def test_usa_cache_y_clear_la_vacia(home, resolver):
    folder = make(home / "code" / "nuevo")
    assert resolver.find_root(folder) is None
    make(folder, ".git/")
    assert resolver.find_root(folder) is None  # sigue en caché
    resolver.clear()
    assert resolver.find_root(folder) is not None


# ── resolve_process: cascada cwd -> línea de comandos -> ejecutable ──


def test_proceso_se_resuelve_por_cwd(home, resolver):
    repo = make(home / "code" / "tienda", ".git/")
    info = ProcessInfo(pid=1, name="node", cwd=str(repo))
    assert resolver.resolve_process(info).path == repo


def test_proceso_se_resuelve_por_linea_de_comandos(home, resolver):
    repo = make(home / "code" / "tienda", ".git/", "server.js")
    info = ProcessInfo(
        pid=1,
        name="node",
        cwd=str(home),
        cmdline=("node", "--inspect", str(repo / "server.js")),
    )
    assert resolver.resolve_process(info).path == repo


def test_proceso_se_resuelve_por_opcion_con_igual(home, resolver):
    repo = make(home / "code" / "tienda", ".git/", "conf/app.toml")
    info = ProcessInfo(
        pid=1, name="server", cmdline=("server", f"--config={repo / 'conf' / 'app.toml'}")
    )
    assert resolver.resolve_process(info).path == repo


def test_proceso_se_resuelve_por_ejecutable(home, resolver):
    repo = make(home / "code" / "api", ".git/", ".venv/Scripts/python.exe")
    info = ProcessInfo(
        pid=1, name="python.exe", exe=str(repo / ".venv" / "Scripts" / "python.exe")
    )
    assert resolver.resolve_process(info).path == repo


def test_el_cwd_tiene_prioridad(home, resolver):
    repo_a = make(home / "a", ".git/")
    repo_b = make(home / "b", ".git/", "server.js")
    info = ProcessInfo(
        pid=1, name="node", cwd=str(repo_a), cmdline=("node", str(repo_b / "server.js"))
    )
    assert resolver.resolve_process(info).path == repo_a


def test_proceso_sin_datos_no_tiene_proyecto(resolver):
    assert resolver.resolve_process(ProcessInfo(pid=1, name="mysqld")) is None
