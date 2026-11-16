"""Tests de la explicación de git en lenguaje humano."""

import pytest

from qcorre import i18n
from qcorre.git import explain
from qcorre.git.parse import FileChange, RepoStatus

OID = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


def status(**kwargs) -> RepoStatus:
    """Repo normal: rama main, al día con origin, sin cambios."""
    base = dict(
        branch="main", oid=OID, upstream="origin/main", ahead=0, behind=0, remotes=("origin",)
    )
    return RepoStatus(**{**base, **kwargs})


def modified(n: int) -> tuple[FileChange, ...]:
    return tuple(FileChange(f"archivo{i}.py", worktree="M") for i in range(n))


def new(n: int) -> tuple[FileChange, ...]:
    return tuple(FileChange(f"nuevo{i}.py", untracked=True) for i in range(n))


# ── Rama ────────────────────────────────────────────────────────


def test_rama():
    assert explain.explain_branch(status()).text == "Estás en la rama main"


def test_rama_sin_commits():
    line = explain.explain_branch(status(oid=None))
    assert line.text == "Estás en la rama main, que todavía no tiene commits"


def test_head_suelto():
    line = explain.explain_branch(status(branch=None))
    assert line.text == "No estás en ninguna rama: estás viendo el commit a1b2c3d directamente"
    assert line.tone == explain.WARN


# ── Cambios ─────────────────────────────────────────────────────


def test_sin_cambios():
    line = explain.explain_changes(status())
    assert line.text == "No tienes cambios pendientes: todo está guardado en commits."
    assert line.tone == explain.GOOD


def test_el_ejemplo_del_plan():
    line = explain.explain_changes(status(files=modified(3)))
    assert line.text == "Tienes 3 archivos con cambios sin guardar en un commit."


def test_singular():
    line = explain.explain_changes(status(files=modified(1)))
    assert line.text == "Tienes 1 archivo con cambios sin guardar en un commit."


def test_cambios_y_nuevos():
    line = explain.explain_changes(status(files=modified(3) + new(1)))
    assert line.text == (
        "Tienes 3 archivos con cambios sin guardar en un commit y 1 archivo nuevo."
    )


def test_solo_nuevos():
    line = explain.explain_changes(status(files=new(2)))
    assert line.text == "Tienes 2 archivos nuevos que aún no están en ningún commit."


def test_con_conflictos():
    conflict = (FileChange("x.py", "U", "U", conflict=True),)
    current = status(files=modified(1) + new(1) + conflict)
    line = explain.explain_changes(current)
    assert line.text == (
        "Tienes 1 archivo con cambios sin guardar en un commit, 1 archivo nuevo "
        "y 1 archivo en conflicto."
    )
    assert line.tone == explain.WARN
    notes = [note.text for note in explain.explain_notes(current)]
    assert "Resolver conflictos queda fuera de lo que qcorre hace por ahora." in notes


def test_nota_de_archivos_ya_preparados():
    files = (FileChange("a.py", index="M"),) + modified(2)
    notes = [note.text for note in explain.explain_notes(status(files=files))]
    assert notes == ["1 ya está preparado para el próximo commit (git add)."]
    # Si todos están preparados (o ninguno), la nota sobra.
    assert explain.explain_notes(status(files=(FileChange("a.py", index="M"),))) == []
    assert explain.explain_notes(status(files=modified(2))) == []


# ── Tu compu y el remoto ────────────────────────────────────────


def test_al_dia():
    line = explain.explain_sync(status())
    assert line.text == "Tu compu y origin tienen lo mismo."
    assert line.tone == explain.GOOD


def test_commits_sin_subir():
    assert explain.explain_sync(status(ahead=2)).text == "Tienes 2 commits sin subir."
    assert explain.explain_sync(status(ahead=1)).text == "Tienes 1 commit sin subir."


def test_commits_sin_bajar():
    assert explain.explain_sync(status(behind=1)).text == (
        "Hay 1 commit en origin que no has bajado."
    )
    assert explain.explain_sync(status(behind=4)).text == (
        "Hay 4 commits en origin que no has bajado."
    )


def test_ramas_separadas():
    line = explain.explain_sync(status(ahead=2, behind=1))
    assert line.text == (
        "Tu compu y origin se separaron: 2 commits sin subir y 1 commit sin bajar."
    )
    assert line.tone == explain.WARN


def test_sin_remoto():
    line = explain.explain_sync(status(upstream=None, ahead=None, behind=None, remotes=()))
    assert line.text == "Este repo no tiene remoto: solo existe en tu compu."


def test_rama_que_aun_no_esta_en_el_remoto():
    line = explain.explain_sync(status(branch="feat/x", upstream=None, ahead=None, behind=None))
    assert line.text == "La rama feat/x todavía no está en el remoto: solo existe en tu compu."


def test_rama_remota_borrada():
    line = explain.explain_sync(status(ahead=None, behind=None))
    assert "origin/main ya no existe" in line.text
    assert line.tone == explain.WARN


def test_sin_commits_o_sin_rama_no_habla_de_subir():
    assert "primer commit" in explain.explain_sync(status(oid=None, upstream=None)).text
    assert "Sin una rama" in explain.explain_sync(status(branch=None, upstream=None)).text


# ── De cuándo son los datos del remoto ──────────────────────────


def test_ultima_consulta_al_remoto():
    line = explain.explain_fetch(status(last_sync=1000.0), now=8200.0, duration="2h 00m")
    assert line.text == "Según el último contacto con el remoto, hace 2h 00m."
    assert explain.explain_fetch(status(), now=0).text == (
        "Aún no ha habido contacto con el remoto desde esta compu."
    )
    # Sin rama remota no hay conteos que matizar.
    assert explain.explain_fetch(status(upstream=None), now=0) is None
    assert explain.explain_fetch(status(remotes=(), upstream=None), now=0) is None


# ── Idioma y utilidades ─────────────────────────────────────────


def test_en_ingles():
    i18n.set_language("en")
    current = status(ahead=2, behind=1, files=modified(3) + new(1))
    assert explain.explain_branch(current).text == "You are on branch main"
    assert explain.explain_changes(current).text == (
        "You have 3 files with changes not saved in a commit and 1 new file."
    )
    assert explain.explain_sync(current).text == (
        "Your machine and origin have diverged: 2 commits to push and 1 commit to pull."
    )


def test_join_list():
    assert explain.join_list([]) == ""
    assert explain.join_list(["a"]) == "a"
    assert explain.join_list(["a", "b"]) == "a y b"
    assert explain.join_list(["a", "b", "c"]) == "a, b y c"
