"""Tests de ramas, deshacer, respaldos y archivos sensibles (lógica y repos reales)."""

import os
import shutil
import time
from pathlib import Path

import pytest
from test_git_integration import commit, git, write

from qcorre import i18n
from qcorre.git import actions
from qcorre.git.actions import execute
from qcorre.git.backup import BACKUP_PREFIX, list_backups, parse_backups
from qcorre.git.branches import Branch, parse_branches, read_branches
from qcorre.git.parse import FileChange, RepoStatus
from qcorre.git.runner import GitRunner, _environment
from qcorre.git.sensitive import is_sensitive, sensitive_files
from qcorre.git.status import read_status

from test_git_integration import isolated_git, remote, repo  # noqa: F401  isort: skip

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git no está instalado")

OID = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


def status(**kwargs) -> RepoStatus:
    base = dict(
        branch="main", oid=OID, upstream="origin/main", ahead=0, behind=0,
        remotes=("origin",), head_subject="agrega pagos", has_parent=True,
    )  # fmt: skip
    return RepoStatus(**{**base, **kwargs})


def run(path: Path, plan: actions.ActionPlan) -> actions.ActionResult:
    return execute(plan, GitRunner(path))


# ── Archivos sensibles ──────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        ".env", "config/.env.production", "backend/prod.env", "certs/server.pem",
        "deploy/private.key", "id_rsa", ".ssh/id_ed25519", "credentials.json",
        "aws/credentials", "secrets.yaml", "client_secret_123.json", ".npmrc",
        "infra/terraform.tfvars", "C:\\proj\\.env", "service-account-prod.json",
    ],
)  # fmt: skip
def test_archivos_que_parecen_sensibles(path):
    assert is_sensitive(path)


@pytest.mark.parametrize(
    "path",
    [
        ".env.example", ".env.sample", "id_rsa.pub", "src/environment.py", "README.md",
        "keyboard.py", "docs/secrets-management.md", "tokenizer.json", "src/env.ts", "",
    ],
)  # fmt: skip
def test_archivos_normales_no_disparan_el_aviso(path):
    assert not is_sensitive(path)


def test_sensitive_files_ignora_los_borrados():
    files = (
        FileChange(".env", untracked=True),
        FileChange("viejo.pem", worktree="D"),
        FileChange("app.py", worktree="M"),
    )
    assert [f.path for f in sensitive_files(files)] == [".env"]


# ── Git nunca se queda esperando una contraseña ─────────────────


def test_git_corre_sin_preguntas_en_la_terminal():
    env = _environment()
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["LC_ALL"] == "C"
    assert env.get("PATH") == os.environ.get("PATH")  # el resto del entorno se conserva


# ── Ramas: parseo ───────────────────────────────────────────────


def ref_line(ref, oid="abc1234", upstream="", track="", head=" "):
    return "\0".join([ref, oid, upstream, track, head])


def test_parse_branches_locales_remotas_y_borradas():
    output = "\n".join(
        [
            ref_line("refs/heads/main", upstream="origin/main", head="*"),
            ref_line("refs/heads/feat/a", upstream="origin/feat/a", track="[ahead 2, behind 1]"),
            ref_line("refs/heads/feat/b", upstream="origin/feat/b", track="[behind 3]"),
            ref_line("refs/heads/feat/vieja", upstream="origin/feat/vieja", track="[gone]"),
            ref_line("refs/heads/local"),
            ref_line("refs/remotes/origin/HEAD"),
            ref_line("refs/remotes/origin/main"),
            ref_line("refs/remotes/origin/feat/a"),
            ref_line("refs/remotes/origin/feat/b"),
            ref_line("refs/remotes/origin/de-otra-persona"),
            ref_line("refs/remotes/origin/local"),  # ya existe una local con ese nombre
        ]
    )
    branches = parse_branches(output, ("origin",), frozenset({"main", "feat/vieja"}))
    by_name = {b.name: b for b in branches.local}

    assert branches.local[0].name == "main" and branches.local[0].current  # la actual, primero
    assert (by_name["main"].ahead, by_name["main"].behind) == (0, 0)
    assert (by_name["feat/a"].ahead, by_name["feat/a"].behind) == (2, 1)
    assert (by_name["feat/b"].ahead, by_name["feat/b"].behind) == (0, 3)
    assert by_name["local"].upstream is None and by_name["local"].ahead is None
    gone = by_name["feat/vieja"]
    assert gone.gone and gone.merged and gone.ahead is None
    assert gone.can_delete
    assert not by_name["main"].can_delete

    (only_remote,) = branches.remote_only
    assert only_remote.name == "de-otra-persona"
    assert only_remote.remote == "origin"
    assert only_remote.full_remote == "origin/de-otra-persona"
    assert only_remote.remote_only


def test_parse_branches_vacio_o_raro():
    assert parse_branches("").local == ()
    assert parse_branches("linea-sin-campos\n").local == ()


# ── Ramas: planes ───────────────────────────────────────────────


def test_plan_switch_a_rama_local():
    plan = actions.plan_switch(status(), Branch("feat/x"))
    assert plan.commands == (("switch", "feat/x"),)
    assert plan.effects[0] == "Pasas de main a feat/x"
    assert plan.backup_ref is None  # sin cambios pendientes no hay nada que respaldar


def test_plan_switch_con_cambios_crea_respaldo():
    files = (FileChange("a.py", worktree="M"),)
    plan = actions.plan_switch(status(files=files), Branch("feat/x"))
    assert plan.backup_ref is not None and plan.backup_ref.endswith("-switch")
    assert any("se viene contigo" in effect for effect in plan.effects)


def test_plan_switch_a_rama_solo_remota_crea_la_local_que_la_sigue():
    plan = actions.plan_switch(status(), Branch("feat/y", remote="origin"))
    assert plan.commands == (("switch", "-c", "feat/y", "--track", "origin/feat/y"),)
    assert "Se crea la rama local feat/y, enlazada a origin/feat/y" in plan.effects


def test_plan_switch_bloqueado_si_ya_estas_ahi():
    assert "Ya estás" in actions.plan_switch(status(), Branch("main", current=True)).blocked


@pytest.mark.parametrize(
    "name", ["", "con espacio", "-x", "a..b", "x.lock", "fin/", "raro~1", "a:b", "@", ".oculta"]
)
def test_nombres_de_rama_invalidos(name):
    assert actions.branch_name_problem(name) is not None
    assert actions.plan_new_branch(status(), name).blocked


def test_plan_new_branch():
    plan = actions.plan_new_branch(status(), "  feat/buscador ")
    assert plan.commands == (("switch", "-c", "feat/buscador"),)
    assert "a partir de main" in plan.effects[0]
    assert plan.backup_ref is None


def test_plan_delete_solo_ramas_borradas_en_el_remoto_y_ya_mergeadas():
    ok = actions.plan_delete_branch(status(), Branch("feat/vieja", gone=True, merged=True))
    assert ok.commands == (("branch", "-d", "feat/vieja"),)
    assert ok.danger

    unmerged = actions.plan_delete_branch(status(), Branch("feat/z", gone=True, merged=False))
    assert "perdería ese trabajo" in unmerged.blocked
    alive = actions.plan_delete_branch(status(), Branch("feat/z", upstream="origin/feat/z"))
    assert "todavía existe" in alive.blocked
    current = actions.plan_delete_branch(status(), Branch("main", current=True, gone=True))
    assert "en la que estás" in current.blocked
    remote_only = actions.plan_delete_branch(status(), Branch("x", remote="origin"))
    assert remote_only.blocked


def test_nunca_se_propone_branch_D():
    plan = actions.plan_delete_branch(status(), Branch("feat/vieja", gone=True, merged=True))
    assert all("-D" not in args and "--force" not in args for args in plan.commands)


# ── Deshacer: planes ────────────────────────────────────────────


def test_plan_undo_commit():
    plan = actions.plan_undo_commit(status(ahead=1))
    assert plan.commands == (("reset", "--soft", "HEAD~1"),)
    assert plan.effects[0] == 'Se deshace el commit "agrega pagos" (a1b2c3d)'
    assert plan.backup_ref.endswith("-undo")


def test_plan_undo_commit_bloqueado():
    assert "ya está subido" in actions.plan_undo_commit(status()).blocked
    assert "primer commit" in actions.plan_undo_commit(status(ahead=1, has_parent=False)).blocked
    assert "no tiene commits" in actions.plan_undo_commit(status(oid=None)).blocked
    # Sin rama remota (o con la remota borrada) sí se puede: nada se reescribe.
    assert actions.plan_undo_commit(status(upstream=None, ahead=None)).blocked is None


def test_plan_discard():
    files = (
        FileChange("a.py", worktree="M"),
        FileChange("b.py", index="A"),
        FileChange("nuevo.txt", untracked=True),
    )
    plan = actions.plan_discard(status(files=files))
    assert plan.commands == (("reset", "--hard", "HEAD"),)
    assert plan.danger and plan.backup_ref.endswith("-discard")
    assert plan.effects[0].startswith("Se descartan los cambios de 2 archivos")
    assert any("git add" in effect for effect in plan.effects)
    assert "Tu archivo nuevo que git aún no sigue no se toca" in plan.effects
    only_new = actions.plan_discard(status(files=(FileChange("n.txt", untracked=True),)))
    assert "No hay cambios que descartar" in only_new.blocked


# ── Respaldos: parseo ───────────────────────────────────────────


def test_parse_backups_formato_nuevo_y_anterior():
    refs = {
        BACKUP_PREFIX + "20261116-150000-undo/rama/feat/x": "a" * 40,
        BACKUP_PREFIX + "20261116-150000-undo/cambios": "b" * 40,
        BACKUP_PREFIX + "20261116-140000-switch/suelto": "c" * 40,
        BACKUP_PREFIX + "20261116-130000-pull": "d" * 40,  # formato de la primera versión
        BACKUP_PREFIX + "20261116-130000-pull-cambios": "e" * 40,
        "refs/heads/main": "f" * 40,
    }
    newest, detached, old = parse_backups(refs)
    assert (newest.operation, newest.branch) == ("undo", "feat/x")
    assert newest.changes_ref == BACKUP_PREFIX + "20261116-150000-undo/cambios"
    assert newest.base == BACKUP_PREFIX + "20261116-150000-undo"
    assert detached.branch is None and detached.changes_ref is None
    assert (old.operation, old.branch) == ("pull", None)
    assert old.changes_ref == BACKUP_PREFIX + "20261116-130000-pull-cambios"
    assert newest.created > detached.created > old.created


def test_plan_restore_solo_en_la_rama_del_respaldo():
    (backup,) = parse_backups({BACKUP_PREFIX + "20261116-150000-undo/rama/feat/x": "a" * 40})
    blocked = actions.plan_restore(status(), backup)
    assert "Este respaldo es de la rama feat/x" in blocked.blocked
    plan = actions.plan_restore(status(branch="feat/x"), backup, when="hace 2h 00m")
    assert plan.commands == (("reset", "--hard", backup.ref),)
    assert plan.danger and plan.backup_ref.endswith("-restore")
    assert plan.effects[0] == (
        "La rama feat/x vuelve al commit aaaaaaa, donde estaba antes de deshacer un commit "
        "(hace 2h 00m)"
    )


# ── Contra repos reales ─────────────────────────────────────────


def test_read_status_trae_el_ultimo_commit_y_lista_archivos_nuevos_uno_por_uno(repo):  # noqa: F811
    assert read_status(repo).has_parent is False
    commit(repo, "segundo.txt", message="segundo commit")
    write(repo, "nueva/a.txt")
    write(repo, "nueva/.env")
    current = read_status(repo)
    assert current.head_subject == "segundo commit" and current.has_parent
    assert {f.path for f in current.new} == {"nueva/a.txt", "nueva/.env"}
    assert [f.path for f in sensitive_files(current.files)] == ["nueva/.env"]


def test_crear_rama_cambiar_y_volver(repo):  # noqa: F811
    write(repo, "README.md", "cambio sin guardar\n")
    result = run(repo, actions.plan_new_branch(read_status(repo), "feat/nueva"))
    assert result.ok
    assert read_status(repo).branch == "feat/nueva"
    assert (repo / "README.md").read_text(encoding="utf-8") == "cambio sin guardar\n"

    branches = read_branches(repo)
    assert [(b.name, b.current) for b in branches.local] == [("feat/nueva", True), ("main", False)]
    main = next(b for b in branches.local if b.name == "main")
    plan = actions.plan_switch(read_status(repo), main)
    result = run(repo, plan)
    assert result.ok and read_status(repo).branch == "main"
    # Había cambios sin guardar: quedó respaldo con la foto de esos cambios.
    assert result.backup is not None and result.backup.changes_ref is not None
    assert result.backup.branch == "feat/nueva"


def test_rama_solo_remota_se_puede_seguir(tmp_path, repo, remote):  # noqa: F811
    other = tmp_path / "otra-compu"
    git(tmp_path, "clone", "-q", str(remote), str(other))
    git(other, "switch", "-q", "-c", "feat/de-otra")
    commit(other, "otra.txt")
    git(other, "push", "-q", "-u", "origin", "feat/de-otra")

    assert read_branches(repo).remote_only == ()  # sin contacto, aún no se sabe
    git(repo, "fetch", "-q")
    branches = read_branches(repo)
    (only_remote,) = branches.remote_only
    assert only_remote.full_remote == "origin/feat/de-otra"
    assert branches.last_sync is not None

    result = run(repo, actions.plan_switch(read_status(repo), only_remote))
    assert result.ok
    after = read_status(repo)
    assert after.branch == "feat/de-otra" and after.upstream == "origin/feat/de-otra"
    assert (after.ahead, after.behind) == (0, 0)
    assert read_branches(repo).remote_only == ()


def merged_and_deleted_on_remote(repo_path: Path, name: str, merge: bool) -> None:
    """Simula un PR: rama subida, (mergeada o no) y borrada en el remoto."""
    git(repo_path, "switch", "-q", "-c", name)
    commit(repo_path, f"{name.replace('/', '-')}.txt")
    git(repo_path, "push", "-q", "-u", "origin", name)
    git(repo_path, "switch", "-q", "main")
    if merge:
        git(repo_path, "merge", "-q", "--no-ff", "-m", f"merge {name}", name)
        git(repo_path, "push", "-q")
    git(repo_path, "push", "-q", "origin", "--delete", name)
    git(repo_path, "fetch", "-q", "--prune")


def test_borrar_rama_ya_mergeada_cuya_remota_fue_borrada(repo, remote):  # noqa: F811
    merged_and_deleted_on_remote(repo, "feat/lista", merge=True)
    merged_and_deleted_on_remote(repo, "feat/a-medias", merge=False)
    by_name = {b.name: b for b in read_branches(repo).local}
    assert by_name["feat/lista"].gone and by_name["feat/lista"].merged
    assert by_name["feat/lista"].can_delete
    assert by_name["feat/a-medias"].gone and not by_name["feat/a-medias"].merged
    assert not by_name["feat/a-medias"].can_delete

    current = read_status(repo)
    result = run(repo, actions.plan_delete_branch(current, by_name["feat/lista"]))
    assert result.ok
    assert "feat/lista" not in {b.name for b in read_branches(repo).local}

    # La que tiene trabajo sin mergear ni siquiera llega a ejecutarse.
    blocked = actions.plan_delete_branch(current, by_name["feat/a-medias"])
    assert blocked.blocked and not run(repo, blocked).ok
    assert "feat/a-medias" in {b.name for b in read_branches(repo).local}


def test_deshacer_el_ultimo_commit_conserva_los_cambios(repo):  # noqa: F811
    commit(repo, "pagos.py", "total = 1\n", message="agrega pagos")
    first = git(repo, "rev-parse", "HEAD~1").strip()
    plan = actions.plan_undo_commit(read_status(repo))
    assert plan.effects[0].startswith('Se deshace el commit "agrega pagos"')
    result = run(repo, plan)
    assert result.ok
    assert git(repo, "rev-parse", "HEAD").strip() == first
    assert (repo / "pagos.py").read_text(encoding="utf-8") == "total = 1\n"
    after = read_status(repo)
    assert [f.path for f in after.files] == ["pagos.py"] and after.files[0].staged
    assert result.backup is not None  # y se puede volver al commit deshecho


def test_no_se_deshace_un_commit_ya_subido(repo, remote):  # noqa: F811
    commit(repo, "subido.txt")
    git(repo, "push", "-q")
    assert "ya está subido" in actions.plan_undo_commit(read_status(repo)).blocked
    commit(repo, "local.txt")
    assert actions.plan_undo_commit(read_status(repo)).blocked is None


def test_descartar_cambios_y_recuperarlos_desde_el_respaldo(repo):  # noqa: F811
    commit(repo, "app.py", "version = 1\n")
    write(repo, "app.py", "version = 2  # trabajo de toda la tarde\n")
    write(repo, "sin-seguir.txt", "no se toca\n")

    result = run(repo, actions.plan_discard(read_status(repo)))
    assert result.ok
    assert (repo / "app.py").read_text(encoding="utf-8") == "version = 1\n"
    assert (repo / "sin-seguir.txt").exists()

    # Arrepentimiento: el respaldo trae de vuelta el trabajo descartado.
    (backup,) = list_backups(GitRunner(repo))
    assert backup.operation == "discard" and backup.changes_ref is not None
    restore = actions.plan_restore(read_status(repo), backup)
    assert restore.commands[-1] == ("stash", "apply", backup.changes_ref)
    result = run(repo, restore)
    assert result.ok, result.output
    assert (repo / "app.py").read_text(encoding="utf-8") == (
        "version = 2  # trabajo de toda la tarde\n"
    )


def test_restaurar_devuelve_la_rama_al_commit_respaldado(repo):  # noqa: F811
    commit(repo, "a.txt", message="commit que se va a deshacer")
    undone = git(repo, "rev-parse", "HEAD").strip()
    run(repo, actions.plan_undo_commit(read_status(repo)))
    assert git(repo, "rev-parse", "HEAD").strip() != undone

    backup = next(b for b in list_backups(GitRunner(repo)) if b.operation == "undo")
    time.sleep(1.1)  # los respaldos se nombran por segundo
    result = run(repo, actions.plan_restore(read_status(repo), backup))
    assert result.ok, result.output
    assert git(repo, "rev-parse", "HEAD").strip() == undone
    assert read_status(repo).is_clean
    # Restaurar también deja su propio respaldo del estado anterior.
    assert {b.operation for b in list_backups(GitRunner(repo))} == {"undo", "restore"}


def test_un_pull_sin_novedades_borra_su_respaldo(repo, remote):  # noqa: F811
    result = run(repo, actions.plan_pull(read_status(repo)))
    assert result.ok
    assert result.unchanged and result.backup is None
    assert git(repo, "for-each-ref", "refs/qcorre") == ""
    assert actions.success_message(result) == "Ya estabas al día: no había nada que bajar"


def test_un_pull_sin_novedades_pero_con_cambios_conserva_el_respaldo(repo, remote):  # noqa: F811
    write(repo, "README.md", "cambio sin guardar\n")
    result = run(repo, actions.plan_pull(read_status(repo)))
    assert result.ok
    assert result.backup is not None and result.backup.changes_ref is not None
    assert not result.unchanged
