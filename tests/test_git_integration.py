"""Tests de git contra repos reales creados en carpetas temporales.

Usan el git del sistema, aislado de la configuración del usuario para que el
resultado no dependa de su ``.gitconfig``.
"""

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from qcorre.git.parse import ChangeKind
from qcorre.git.runner import GitError, GitRunner
from qcorre.git.status import read_status

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git no está instalado")


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch, tmp_path):
    """Git sin configuración global ni del sistema, con una identidad fija."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Ana")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "ana@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Ana")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "ana@example.com")
    monkeypatch.setenv("HOME", str(tmp_path))


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return done.stdout


def write(repo: Path, name: str, content: str = "hola\n") -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def commit(repo: Path, name: str, content: str = "hola\n", message: str | None = None) -> None:
    write(repo, name, content)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message or f"agrega {name}")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repo con un commit en la rama main."""
    path = tmp_path / "proyecto"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    commit(path, "README.md")
    return path


@pytest.fixture
def remote(tmp_path: Path, repo: Path) -> Path:
    """Remoto (repo desnudo) al que ``repo`` ya subió main."""
    path = tmp_path / "remoto.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(path))
    git(repo, "remote", "add", "origin", str(path))
    git(repo, "push", "-q", "-u", "origin", "main")
    return path


def test_repo_recien_creado_sin_commits(tmp_path):
    path = tmp_path / "vacio"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    status = read_status(path)
    assert status.branch == "main"
    assert not status.has_commits
    assert status.is_clean
    assert status.remotes == ()
    assert status.last_fetch is None


def test_repo_limpio_sin_remoto(repo):
    status = read_status(repo)
    assert status.branch == "main"
    assert status.has_commits and len(status.oid) == 40
    assert status.is_clean
    assert status.upstream is None
    assert status.remotes == ()


def test_cambios_de_todo_tipo(repo):
    commit(repo, "borrar.txt")
    commit(repo, "renombrar.txt", "contenido suficientemente largo para detectar el renombre\n")
    write(repo, "README.md", "editado\n")
    write(repo, "docs/guía de uso.md")
    (repo / "borrar.txt").unlink()
    git(repo, "mv", "renombrar.txt", "renombrado.txt")

    status = read_status(repo)
    kinds = {f.path: f.kind for f in status.files}
    assert kinds["README.md"] is ChangeKind.MODIFIED
    assert kinds["borrar.txt"] is ChangeKind.DELETED
    assert kinds["renombrado.txt"] is ChangeKind.RENAMED
    # Una carpeta nueva se lista como carpeta, con su nombre tal cual (sin escapar).
    assert kinds["docs/"] is ChangeKind.NEW
    renamed = next(f for f in status.files if f.path == "renombrado.txt")
    assert renamed.orig_path == "renombrar.txt"
    assert renamed.staged
    assert len(status.changed) == 3 and len(status.new) == 1


def test_al_dia_con_el_remoto(repo, remote):
    status = read_status(repo)
    assert status.upstream == "origin/main"
    assert (status.ahead, status.behind) == (0, 0)
    assert status.remotes == ("origin",)
    assert status.remote_name == "origin" and status.remote_branch == "main"
    assert status.upstream_oid == status.short_oid


def test_commits_sin_subir(repo, remote):
    commit(repo, "a.txt")
    commit(repo, "b.txt")
    status = read_status(repo)
    assert (status.ahead, status.behind) == (2, 0)
    assert status.upstream_oid != status.short_oid


def test_commits_sin_bajar_y_ramas_separadas(tmp_path, repo, remote):
    # Otra persona clona, hace un commit y lo sube.
    other = tmp_path / "otra-compu"
    git(tmp_path, "clone", "-q", str(remote), str(other))
    commit(other, "de-otra-persona.txt")
    git(other, "push", "-q")

    # Sin consultar el remoto, git todavía no lo sabe.
    assert read_status(repo).behind == 0

    before = time.time()
    git(repo, "fetch", "-q")
    status = read_status(repo)
    assert (status.ahead, status.behind) == (0, 1)
    assert status.last_fetch is not None and status.last_fetch >= before - 5

    commit(repo, "mio.txt")
    status = read_status(repo)
    assert (status.ahead, status.behind) == (1, 1)


def test_rama_nueva_que_aun_no_esta_en_el_remoto(repo, remote):
    git(repo, "switch", "-q", "-c", "feat/nueva")
    status = read_status(repo)
    assert status.branch == "feat/nueva"
    assert status.upstream is None
    assert status.remotes == ("origin",)


def test_rama_remota_borrada(repo, remote):
    git(repo, "switch", "-q", "-c", "feat/temporal")
    git(repo, "push", "-q", "-u", "origin", "feat/temporal")
    git(repo, "push", "-q", "origin", "--delete", "feat/temporal")
    git(repo, "fetch", "-q", "--prune")
    status = read_status(repo)
    assert status.upstream == "origin/feat/temporal"
    assert status.upstream_gone
    assert status.upstream_oid is None


def test_head_suelto(repo):
    commit(repo, "segundo.txt")
    git(repo, "checkout", "-q", "--detach", "HEAD~1")
    status = read_status(repo)
    assert status.detached
    assert status.short_oid is not None


def test_funciona_desde_una_subcarpeta(repo):
    write(repo, "src/app.py")
    status = read_status(repo / "src")
    assert status.branch == "main"
    assert len(status.new) == 1


def test_carpeta_que_no_es_repo(tmp_path):
    folder = tmp_path / "suelta"
    folder.mkdir()
    with pytest.raises(GitError) as error:
        read_status(folder)
    assert error.value.reason == "failed"
    assert "not a git repository" in error.value.detail


def test_carpeta_que_no_existe(tmp_path):
    with pytest.raises(GitError):
        read_status(tmp_path / "no-existe")


def test_git_no_instalado(repo):
    with pytest.raises(GitError) as error:
        GitRunner(repo, git="git-que-no-existe").run("status")
    assert error.value.reason == "not_installed"


def test_el_runner_devuelve_el_comando_exacto(repo):
    result = GitRunner(repo).run("log", "--oneline", "-1")
    assert result.ok
    assert result.command == "git log --oneline -1"
    assert "agrega README.md" in result.stdout


def test_leer_el_estado_no_modifica_el_repo(repo, remote):
    write(repo, "README.md", "editado\n")
    before = git(repo, "status", "--porcelain=v2", "--branch")
    index_before = (repo / ".git" / "index").stat().st_mtime_ns
    read_status(repo)
    # Se mide antes de volver a llamar a git: un `git status` normal sí
    # reescribe el índice; las lecturas de qcorre no deben hacerlo.
    assert (repo / ".git" / "index").stat().st_mtime_ns == index_before
    assert git(repo, "status", "--porcelain=v2", "--branch") == before
