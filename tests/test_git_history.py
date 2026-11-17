"""Tests de la lectura del historial: parseo y repos reales."""

import shutil
import time

import pytest
from test_git_integration import commit, git, write

from qcorre.git import actions
from qcorre.git.actions import execute
from qcorre.git.graph import layout
from qcorre.git.history import (
    Commit,
    History,
    Ref,
    RefKind,
    parse_log,
    parse_refs,
    read_history,
)
from qcorre.git.runner import GitError, GitRunner
from qcorre.git.status import read_status

from test_git_integration import isolated_git, remote, repo  # noqa: F401  isort: skip

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git no está instalado")

F, R = "\x1f", "\x1e"


def record(oid, parents="", refs="", author="Ana", stamp="1700000000", subject="mensaje"):
    return F.join([oid, parents, refs, author, stamp, subject]) + R + "\n"


# ── Decoraciones ────────────────────────────────────────────────


def test_parse_refs_distingue_rama_actual_locales_remotas_y_tags():
    refs = parse_refs(
        "HEAD -> refs/heads/main, tag: refs/tags/v1.0, refs/remotes/origin/main, "
        "refs/remotes/origin/HEAD, refs/heads/feat/x"
    )
    assert refs == (
        Ref(RefKind.HEAD, "main"),
        Ref(RefKind.LOCAL, "feat/x"),
        Ref(RefKind.REMOTE, "origin/main"),
        Ref(RefKind.TAG, "v1.0"),
    )


def test_parse_refs_head_suelto():
    assert parse_refs("HEAD, refs/heads/main") == (
        Ref(RefKind.DETACHED, "HEAD"),
        Ref(RefKind.LOCAL, "main"),
    )


def test_parse_refs_ignora_referencias_internas():
    refs = parse_refs(
        "refs/qcorre/backup/20261116-150000-pull/rama/main, refs/stash, "
        "refs/remotes/origin/HEAD, refs/notes/commits"
    )
    assert refs == ()
    assert parse_refs("") == ()


# ── Registros de git log ────────────────────────────────────────


def test_parse_log_basico():
    output = record("a" * 40, "b" * 40 + " " + "c" * 40, "HEAD -> refs/heads/main") + record(
        "b" * 40, subject="primer commit"
    )
    merge, first = parse_log(output)
    assert merge.oid == "a" * 40 and merge.short_oid == "aaaaaaa"
    assert merge.parents == ("b" * 40, "c" * 40) and merge.is_merge
    assert merge.refs == (Ref(RefKind.HEAD, "main"),)
    assert merge.author == "Ana" and merge.time == 1700000000.0
    assert first.parents == () and not first.is_merge
    assert first.subject == "primer commit"


def test_parse_log_con_textos_raros():
    output = (
        record("a" * 40, subject="")
        + record("b" * 40, author="José Ñandú 🚀", subject='arregla "comillas", comas y → flechas')
        + record("c" * 40, stamp="no-es-fecha")
    )
    empty, fancy, bad_date = parse_log(output)
    assert empty.subject == ""
    assert fancy.author == "José Ñandú 🚀"
    assert fancy.subject == 'arregla "comillas", comas y → flechas'
    assert bad_date.time == 0.0


def test_parse_log_omite_registros_corruptos():
    output = record("a" * 40) + "basura sin campos" + R + F.join(["", "", "", "", "", ""]) + R
    assert [c.oid for c in parse_log(output)] == ["a" * 40]
    assert parse_log("") == []


# ── Repos reales ────────────────────────────────────────────────


def test_repo_sin_commits_no_tiene_historial(tmp_path):
    path = tmp_path / "vacio"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    assert read_history(path) == History()


def test_historial_lineal_del_mas_nuevo_al_mas_viejo(repo):  # noqa: F811
    commit(repo, "a.txt", message="segundo")
    commit(repo, "b.txt", message="tercero")
    history = read_history(repo)
    assert [c.subject for c in history.commits] == ["tercero", "segundo", "agrega README.md"]
    assert not history.truncated
    newest, middle, oldest = history.commits
    assert newest.parents == (middle.oid,) and middle.parents == (oldest.oid,)
    assert oldest.parents == ()
    assert newest.refs == (Ref(RefKind.HEAD, "main"),)
    assert newest.author == "Ana" and newest.time > time.time() - 600
    assert len(newest.oid) == 40


def test_rama_mergeada_se_dibuja_con_su_carril(repo):  # noqa: F811
    git(repo, "switch", "-q", "-c", "feat/x")
    commit(repo, "x.txt", message="trabajo en la rama")
    git(repo, "switch", "-q", "main")
    commit(repo, "m.txt", message="trabajo en main")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge feat/x", "feat/x")

    history = read_history(repo)
    merge = history.commits[0]
    assert merge.subject == "merge feat/x" and merge.is_merge
    # Los hijos van siempre antes que sus padres.
    position = {c.oid: i for i, c in enumerate(history.commits)}
    for item in history.commits:
        for parent in item.parents:
            assert position[parent] > position[item.oid]

    art = [row.text for row in layout(history.commits)]
    assert art[0] == "●─╮" and art[-1] == "●─╯"
    assert set(art[1:3]) == {"● │", "│ ●"}
    branch = next(c for c in history.commits if c.subject == "trabajo en la rama")
    assert branch.refs == (Ref(RefKind.LOCAL, "feat/x"),)


def test_incluye_ramas_que_no_estan_en_la_actual(repo):  # noqa: F811
    git(repo, "switch", "-q", "-c", "experimento")
    commit(repo, "e.txt", message="experimento sin mergear")
    git(repo, "switch", "-q", "main")
    commit(repo, "m.txt", message="sigue main")
    history = read_history(repo)
    assert {c.subject for c in history.commits} == {
        "experimento sin mergear",
        "sigue main",
        "agrega README.md",
    }
    assert [row.text for row in layout(history.commits)][-1] == "●─╯"


def test_ramas_remotas_y_commits_sin_bajar(tmp_path, repo, remote):  # noqa: F811
    other = tmp_path / "otra-compu"
    git(tmp_path, "clone", "-q", str(remote), str(other))
    commit(other, "de-otra.txt", message="commit de otra persona")
    git(other, "push", "-q")
    git(repo, "fetch", "-q")

    history = read_history(repo)
    remote_tip, local_tip = history.commits
    assert remote_tip.subject == "commit de otra persona"
    assert remote_tip.refs == (Ref(RefKind.REMOTE, "origin/main"),)
    assert local_tip.refs == (Ref(RefKind.HEAD, "main"),)


def test_head_suelto_y_etiquetas(repo):  # noqa: F811
    git(repo, "tag", "v1.0")
    commit(repo, "a.txt", message="segundo")
    git(repo, "checkout", "-q", "--detach", "HEAD~1")
    history = read_history(repo)
    by_subject = {c.subject: c for c in history.commits}
    assert Ref(RefKind.DETACHED, "HEAD") in by_subject["agrega README.md"].refs
    assert Ref(RefKind.TAG, "v1.0") in by_subject["agrega README.md"].refs
    # La rama main sigue en el historial aunque HEAD esté en otro commit.
    assert by_subject["segundo"].refs == (Ref(RefKind.LOCAL, "main"),)


def test_rama_huerfana_son_dos_historias(repo):  # noqa: F811
    git(repo, "switch", "-q", "--orphan", "docs")  # rama sin historia en común
    commit(repo, "index.md", message="inicio de docs")
    git(repo, "switch", "-q", "main")
    history = read_history(repo)
    assert len(history.commits) == 2
    assert all(c.parents == () for c in history.commits)
    assert [row.text for row in layout(history.commits)] in (["●", "  ●"], ["●", "●"])


def test_el_limite_recorta_y_avisa(repo):  # noqa: F811
    for index in range(6):
        commit(repo, f"f{index}.txt", message=f"commit {index}")
    history = read_history(repo, limit=4)
    assert len(history.commits) == 4 and history.truncated
    assert history.commits[0].subject == "commit 5"
    # Con el límite justo no hay nada más antiguo que avisar.
    exact = read_history(repo, limit=7)
    assert len(exact.commits) == 7 and not exact.truncated


def test_los_respaldos_y_el_stash_no_ensucian_el_historial(repo):  # noqa: F811
    commit(repo, "a.txt", message="commit que se deshace")
    execute(actions.plan_undo_commit(read_status(repo)), GitRunner(repo))
    write(repo, "README.md", "en el stash\n")
    git(repo, "stash", "-q")
    assert git(repo, "for-each-ref", "refs/qcorre") != ""

    history = read_history(repo)
    # Ni el commit deshecho (solo alcanzable desde el respaldo) ni el stash aparecen.
    assert [c.subject for c in history.commits] == ["agrega README.md"]
    assert history.commits[0].refs == (Ref(RefKind.HEAD, "main"),)


def test_mensajes_con_caracteres_especiales(repo):  # noqa: F811
    commit(repo, "a.txt", message='añade "soporte" para ñ, emojis 🚀 y → flechas\n\ncuerpo largo')
    newest = read_history(repo).commits[0]
    assert newest.subject == 'añade "soporte" para ñ, emojis 🚀 y → flechas'


def test_carpeta_que_no_es_repo(tmp_path):
    folder = tmp_path / "suelta"
    folder.mkdir()
    with pytest.raises(GitError):
        read_history(folder)


def test_leer_el_historial_no_modifica_el_repo(repo):  # noqa: F811
    before = git(repo, "for-each-ref")
    read_history(repo)
    assert git(repo, "for-each-ref") == before
    assert git(repo, "status", "--porcelain") == ""


def test_commit_es_inmutable_y_comparable():
    assert Commit("a", ("b",)) == Commit("a", ("b",))
    assert History((Commit("a"),)) != History()
