"""Tests de las acciones de git: los planes (puros) y su ejecución en repos reales."""

import shutil
import time
from pathlib import Path

import pytest
from test_git_integration import commit, git, write

from qcorre import i18n
from qcorre.git import actions
from qcorre.git.actions import ActionResult, execute, explain_failure
from qcorre.git.backup import BACKUP_PREFIX, backup_ref, create_backup, list_backups
from qcorre.git.parse import FileChange, RepoStatus
from qcorre.git.runner import GitError, GitResult, GitRunner
from qcorre.git.status import hide_credentials, read_status

# Reutiliza el aislamiento de git y los repos temporales de los tests de integración.
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
        remotes=("origin",), remote_url="https://github.com/ana/tienda.git",
    )  # fmt: skip
    return RepoStatus(**{**base, **kwargs})


CHANGES = (FileChange("a.py", worktree="M"), FileChange("nuevo.py", untracked=True))


# ── Planes: commit ──────────────────────────────────────────────


def test_plan_commit_guarda_todo_y_muestra_el_comando_exacto():
    plan = actions.plan_commit(status(files=CHANGES), "  corrige el total  ")
    assert plan.blocked is None
    assert plan.commands == (("add", "-A"), ("commit", "-m", "corrige el total"))
    assert plan.command_lines == ("git add -A", 'git commit -m "corrige el total"')
    assert plan.effects[0] == "Se guardarán 2 archivos en un commit nuevo (también los nuevos)"
    assert "El commit queda en la rama main" in plan.effects
    assert not plan.network and plan.backup_ref is None


def test_plan_commit_bloqueado_sin_cambios_o_con_conflictos():
    assert "No hay cambios que guardar" in actions.plan_commit(status(), "x").blocked
    conflict = (FileChange("a.py", "U", "U", conflict=True),)
    assert "conflicto" in actions.plan_commit(status(files=conflict), "x").blocked


# ── Planes: push ────────────────────────────────────────────────


def test_plan_push_con_commits_por_subir():
    plan = actions.plan_push(status(ahead=2))
    assert plan.commands == (("push", "origin", "main"),)
    assert plan.effects[0] == "Se subirán 2 commits a origin/main"
    assert plan.effects[-1] == "Se conecta a la red: https://github.com/ana/tienda.git"
    assert plan.network and plan.backup_ref is None


def test_plan_push_de_una_rama_nueva_la_crea_y_la_enlaza():
    plan = actions.plan_push(status(branch="feat/x", upstream=None, ahead=None, behind=None))
    assert plan.commands == (("push", "-u", "origin", "feat/x"),)
    assert plan.effects[0] == "La rama feat/x se creará en origin"


def test_plan_push_con_rama_remota_de_otro_nombre():
    plan = actions.plan_push(status(branch="local", upstream="origin/remota", ahead=1))
    assert plan.commands == (("push", "origin", "local:remota"),)


def test_plan_push_bloqueado():
    assert "No hay commits por subir" in actions.plan_push(status()).blocked
    behind = actions.plan_push(status(ahead=1, behind=2)).blocked
    assert "origin tiene 2 commits que no has bajado" in behind
    assert "no tiene remoto" in actions.plan_push(status(remotes=(), upstream=None)).blocked
    assert "ninguna rama" in actions.plan_push(status(branch=None)).blocked
    assert "no tiene commits" in actions.plan_push(status(oid=None)).blocked


def test_nunca_se_propone_un_push_forzado():
    for current in (status(ahead=1), status(ahead=1, behind=1), status(upstream=None)):
        for args in actions.plan_push(current).commands:
            assert not any("force" in arg or arg == "-f" for arg in args)


# ── Planes: pull y fetch ────────────────────────────────────────


def test_plan_pull_avanza_sin_mezclar_y_crea_respaldo():
    now = time.mktime((2026, 11, 16, 14, 32, 10, 0, 0, -1))
    plan = actions.plan_pull(status(behind=1, files=CHANGES), now=now)
    assert plan.commands == (("pull", "--ff-only", "origin", "main"),)
    assert plan.backup_ref == "refs/qcorre/backup/20261116-143210-pull"
    assert plan.effects[0] == "Se bajará 1 commit de origin/main"
    assert "Tus 2 archivos con cambios sin guardar no se tocan" in plan.effects
    assert plan.network


def test_plan_pull_bloqueado():
    diverged = actions.plan_pull(status(ahead=1, behind=1)).blocked
    assert "se separaron" in diverged and "merge o rebase" in diverged
    assert "no está en el remoto" in actions.plan_pull(status(upstream=None)).blocked
    assert "ya no existe" in actions.plan_pull(status(ahead=None, behind=None)).blocked


def test_plan_pull_sin_novedades_conocidas_pregunta_igual():
    plan = actions.plan_pull(status())
    assert plan.blocked is None
    assert "por si acaso" in plan.effects[0]


def test_plan_fetch_avisa_que_se_conecta_a_la_red():
    plan = actions.plan_fetch(status())
    assert plan.commands == (("fetch", "--prune", "origin"),)
    assert plan.network and plan.backup_ref is None
    assert plan.effects[-1] == "Se conecta a la red: https://github.com/ana/tienda.git"
    assert "No cambia tus archivos ni tu rama" in plan.effects[1]
    assert "no tiene remoto" in actions.plan_fetch(status(remotes=(), upstream=None)).blocked


def test_la_url_del_remoto_nunca_muestra_credenciales():
    assert hide_credentials("https://ana:ghp_secreto@github.com/ana/x.git") == (
        "https://github.com/ana/x.git"
    )
    assert hide_credentials("https://github.com/ana/x.git") == "https://github.com/ana/x.git"
    assert hide_credentials("git@github.com:ana/x.git") == "git@github.com:ana/x.git"


# ── Errores explicados ──────────────────────────────────────────


def failed(stderr: str, action: str = actions.PULL) -> ActionResult:
    plan = actions.ActionPlan(action=action, title="x", commands=(("pull",),))
    return ActionResult(plan, (GitResult(("pull",), 1, "", stderr),))


@pytest.mark.parametrize(
    ("stderr", "expected"),
    [
        ("fatal: Not possible to fast-forward, aborting.", "se separaron"),
        ("error: Your local changes would be overwritten by merge", "cambios sin guardar"),
        (" ! [rejected] main -> main (fetch first)", "rechazó la subida"),
        ("fatal: Authentication failed for 'https://...'", "credenciales"),
        ("fatal: unable to access 'https://x/': Could not resolve host: x", "conexión"),
        ("Author identity unknown\n*** Please tell me who you are.", "Git no sabe quién eres"),
        ("fatal: Unable to create '.git/index.lock': File exists.", "Otro programa"),
        ("fatal: algo inesperado", "Git no pudo completar la acción"),
    ],
)
def test_explain_failure(stderr, expected):
    assert expected in explain_failure(failed(stderr))


def test_explain_failure_sin_git_o_por_tiempo():
    plan = actions.ActionPlan(action=actions.PUSH, title="x", commands=(("push",),))
    assert "No encontré git" in explain_failure(
        ActionResult(plan, error=GitError("not_installed"))
    )
    assert "tardó demasiado" in explain_failure(ActionResult(plan, error=GitError("timeout")))


# ── Ejecución contra repos reales ───────────────────────────────


def run(repo_path: Path, plan: actions.ActionPlan) -> ActionResult:
    return execute(plan, GitRunner(repo_path))


def test_commit_real_incluye_modificados_y_nuevos(repo):  # noqa: F811
    write(repo, "README.md", "editado\n")
    write(repo, "nuevo.txt")
    result = run(repo, actions.plan_commit(read_status(repo), "guarda todo"))
    assert result.ok
    assert [step.command for step in result.steps] == ["git add -A", 'git commit -m "guarda todo"']
    after = read_status(repo)
    assert after.is_clean
    assert git(repo, "log", "-1", "--format=%s").strip() == "guarda todo"
    assert "nuevo.txt" in git(repo, "show", "--stat", "--format=", "HEAD")


def test_push_real_y_el_ultimo_contacto_se_actualiza(repo, remote):  # noqa: F811
    commit(repo, "a.txt")
    # Simula que el último fetch fue hace horas.
    fetch_head = repo / ".git" / "FETCH_HEAD"
    fetch_head.touch()
    old = time.time() - 4 * 3600
    import os

    os.utime(fetch_head, (old, old))
    for log in (repo / ".git" / "logs" / "refs" / "remotes" / "origin").glob("*"):
        os.utime(log, (old, old))
    before = read_status(repo)
    assert before.ahead == 1
    assert before.last_sync < time.time() - 3 * 3600

    result = run(repo, actions.plan_push(before))
    assert result.ok
    after = read_status(repo)
    assert (after.ahead, after.behind) == (0, 0)
    # Recién subido: el último contacto con el remoto es de ahora, no de hace horas.
    assert after.last_sync > time.time() - 60


def test_push_real_de_una_rama_nueva(repo, remote):  # noqa: F811
    git(repo, "switch", "-q", "-c", "feat/nueva")
    commit(repo, "b.txt")
    result = run(repo, actions.plan_push(read_status(repo)))
    assert result.ok
    after = read_status(repo)
    assert after.upstream == "origin/feat/nueva"
    assert (after.ahead, after.behind) == (0, 0)


def other_person_pushes(tmp_path: Path, remote_path: Path, name: str = "de-otra.txt") -> None:
    other = tmp_path / "otra-compu"
    if not other.exists():
        git(tmp_path, "clone", "-q", str(remote_path), str(other))
    commit(other, name)
    git(other, "push", "-q")


def test_fetch_real_descubre_commits_sin_tocar_archivos(tmp_path, repo, remote):  # noqa: F811
    other_person_pushes(tmp_path, remote)
    write(repo, "README.md", "mi cambio sin guardar\n")
    head = git(repo, "rev-parse", "HEAD")
    result = run(repo, actions.plan_fetch(read_status(repo)))
    assert result.ok
    after = read_status(repo)
    assert after.behind == 1
    assert git(repo, "rev-parse", "HEAD") == head  # la rama no se movió
    assert (repo / "README.md").read_text(encoding="utf-8") == "mi cambio sin guardar\n"


def test_pull_real_avanza_crea_respaldo_y_conserva_cambios(tmp_path, repo, remote):  # noqa: F811
    other_person_pushes(tmp_path, remote)
    git(repo, "fetch", "-q")
    write(repo, "README.md", "mi cambio sin guardar\n")
    head_before = git(repo, "rev-parse", "HEAD").strip()

    plan = actions.plan_pull(read_status(repo))
    result = run(repo, plan)
    assert result.ok
    assert (repo / "de-otra.txt").exists()
    assert (repo / "README.md").read_text(encoding="utf-8") == "mi cambio sin guardar\n"

    # El respaldo apunta a donde estaba la rama antes de bajar.
    assert result.backup is not None and result.backup.ref == plan.backup_ref
    assert git(repo, "rev-parse", plan.backup_ref).strip() == head_before
    # Y hay una foto de los cambios sin guardar.
    assert result.backup.changes_ref is not None
    snapshot = git(repo, "show", f"{result.backup.changes_ref}:README.md")
    assert snapshot == "mi cambio sin guardar\n"
    # Crear el respaldo no tocó la lista de stashes del usuario.
    assert git(repo, "stash", "list") == ""


def test_pull_real_con_ramas_separadas_falla_sin_cambiar_nada(tmp_path, repo, remote):  # noqa: F811
    other_person_pushes(tmp_path, remote)
    commit(repo, "mio.txt")
    head = git(repo, "rev-parse", "HEAD")
    # El plan se arma con datos viejos (sin fetch): cree que no hay nada raro.
    stale = read_status(repo)
    assert stale.behind == 0
    plan = actions.plan_pull(stale)
    assert plan.blocked is None
    result = run(repo, plan)
    assert not result.ok
    assert "se separaron" in explain_failure(result)
    assert git(repo, "rev-parse", "HEAD") == head
    assert result.backup is not None  # el respaldo quedó de todos modos


def test_un_plan_bloqueado_no_ejecuta_nada(repo):  # noqa: F811
    plan = actions.plan_push(read_status(repo))  # sin remoto
    assert plan.blocked
    result = run(repo, plan)
    assert not result.ok and result.steps == ()


# ── Respaldos ───────────────────────────────────────────────────


def test_backup_ref_tiene_fecha_y_operacion():
    now = time.mktime((2026, 1, 2, 3, 4, 5, 0, 0, -1))
    assert backup_ref("pull", now) == BACKUP_PREFIX + "20260102-030405-pull"


def test_crear_y_listar_respaldos(repo):  # noqa: F811
    runner = GitRunner(repo)
    first = create_backup(runner, backup_ref("pull", time.time() - 100))
    assert first.changes_ref is None  # sin cambios pendientes no hay foto
    write(repo, "README.md", "cambio\n")
    second = create_backup(runner, backup_ref("undo", time.time()))
    assert second.changes_ref is not None

    backups = list_backups(runner)
    assert [b.operation for b in backups] == ["undo", "pull"]  # el más reciente primero
    assert backups[0].oid == git(repo, "rev-parse", "HEAD").strip()
    assert backups[0].changes_ref == second.changes_ref
    assert backups[1].changes_ref is None
    assert backups[0].created > backups[1].created
    # Los respaldos no aparecen como ramas.
    assert "qcorre" not in git(repo, "branch", "-a")


def test_sin_commits_no_se_puede_respaldar(tmp_path):
    path = tmp_path / "vacio"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    with pytest.raises(GitError):
        create_backup(GitRunner(path), backup_ref("pull"))
