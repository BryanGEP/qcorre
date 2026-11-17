"""Tests en la interfaz: commit con archivos, lista expandible, ramas y deshacer."""

import time
from dataclasses import replace

import pytest
from test_action_ui import FakeExecutor, dialog_text
from test_app import sample_snapshot, sample_status, settle

from qcorre import i18n
from qcorre.git.backup import BACKUP_PREFIX, Backup
from qcorre.git.branches import Branch, BranchList
from qcorre.git.parse import FileChange, RepoStatus
from qcorre.ui.app import QcorreApp
from qcorre.ui.confirm import ConfirmScreen, InfoScreen, PromptScreen
from qcorre.ui.git_panel import GitPanel
from qcorre.ui.picker import PickerScreen
from qcorre.ui.widgets import HintBar


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


BRANCHES = BranchList(
    local=(
        Branch("feature/pagos", "a1b2c3d", current=True, upstream="origin/feature/pagos",
               ahead=2, behind=1),
        Branch("feat/lista", "1111111", upstream="origin/feat/lista", gone=True, merged=True),
        Branch("feat/a-medias", "2222222", upstream="origin/feat/a-medias", gone=True),
        Branch("main", "3333333", upstream="origin/main", ahead=0, behind=0),
        Branch("pruebas", "4444444"),
    ),
    remote_only=(Branch("feat/de-otra", "5555555", remote="origin"),),
    last_sync=time.time() - 7200,
)  # fmt: skip

BACKUPS = [
    Backup(
        name=time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time() - 3600)) + "-discard",
        ref=BACKUP_PREFIX + "x-discard/rama/feature/pagos",
        oid="9" * 40,
        operation="discard",
        created=time.time() - 3600,
        branch="feature/pagos",
        changes_ref=BACKUP_PREFIX + "x-discard/cambios",
    ),
    Backup(
        name="20260101-000000-pull",
        ref=BACKUP_PREFIX + "20260101-000000-pull/rama/main",
        oid="8" * 40,
        operation="pull",
        created=1.0,
        branch="main",
    ),
]


def make_app(executor: FakeExecutor, status: RepoStatus | None = None) -> QcorreApp:
    snapshot = sample_snapshot()
    current = status or replace(sample_status(), head_subject="agrega pagos", has_parent=True)
    return QcorreApp(
        scanner=lambda: snapshot,
        git_reader=lambda path: current,
        git_executor=executor,
        branch_reader=lambda path: BRANCHES,
        backup_reader=lambda path: list(BACKUPS),
        refresh_seconds=None,
    )


def picker_lines(app: QcorreApp) -> list[str]:
    assert isinstance(app.screen, PickerScreen)
    return [str(choice.label) for choice in app.screen.choices]


def highlight(app: QcorreApp, fragment: str) -> None:
    """Pone el cursor del selector sobre la opción que contiene ``fragment``."""
    screen = app.screen
    index = next(i for i, c in enumerate(screen.choices) if fragment in str(c.label))
    screen.query_one("#picker-list").highlighted = index


# ── Commit: archivos que entran y aviso de secretos ─────────────


async def test_el_dialogo_de_commit_lista_los_archivos_que_entran():
    app = make_app(FakeExecutor())
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("c")
        await pilot.pause()
        text = dialog_text(app)
        assert "Entran 4 archivos" in text
        for path in ("app/models.py", "app/pagos.py", "tests/test_pagos.py", "app/webhooks.py"):
            assert path in text
        assert "secretos" not in text


async def test_el_dialogo_de_commit_avisa_de_archivos_sensibles():
    files = (
        FileChange("app/pagos.py", worktree="M"),
        FileChange(".env", untracked=True),
        FileChange("certs/server.pem", untracked=True),
        *(FileChange(f"src/m{i}.py", untracked=True) for i in range(20)),
    )
    app = make_app(FakeExecutor(), replace(sample_status(), files=files))
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("c")
        await pilot.pause()
        text = dialog_text(app)
        assert "Ojo: estos archivos parecen contener secretos" in text
        assert "agrégalos a tu .gitignore" in text
        assert ".env" in text and "certs/server.pem" in text
        # Se listan todos (23), no solo los primeros: la zona tiene scroll.
        assert "Entran 23 archivos" in text
        assert "src/m19.py" in text and "… y" not in text
        body = app.screen.query_one("#dialog-body")
        assert body.max_scroll_y > 0
        await pilot.press("pagedown")
        await pilot.pause()
        assert body.scroll_y > 0  # se puede recorrer sin soltar el campo de texto


# ── Panel: ver todos los archivos ───────────────────────────────


async def test_a_expande_y_resume_la_lista_de_archivos():
    files = tuple(FileChange(f"src/m{i:02d}.py", worktree="M") for i in range(25))
    app = make_app(FakeExecutor(), replace(sample_status(), files=files))
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        body = app.query_one(GitPanel).query_one("#git-body")
        text = str(body.render())
        assert "… y 15 más (tecla a para verlos todos)" in text
        assert "src/m24.py" not in text
        await pilot.press("a")
        await pilot.pause()
        text = str(body.render())
        assert "src/m24.py" in text and "tecla a para ver menos" in text
        await pilot.press("a")
        await pilot.pause()
        assert "src/m24.py" not in str(body.render())


# ── Ramas ───────────────────────────────────────────────────────


async def test_b_muestra_locales_remotas_y_borradas():
    app = make_app(FakeExecutor())
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("b")
        await pilot.pause()
        lines = picker_lines(app)
        assert lines[0] == "En tu compu"
        assert "feature/pagos" in lines[1] and "estás aquí" in lines[1]
        assert "2 ↑" in lines[1] and "1 ↓" in lines[1]
        lista = next(line for line in lines if "feat/lista" in line)
        assert "su rama remota ya no existe" in lista and "ya mergeada" in lista
        medias = next(line for line in lines if "feat/a-medias" in line)
        assert "con trabajo sin mergear" in medias
        assert "al día" in next(line for line in lines if line.strip().startswith("main"))
        assert "solo en tu compu" in next(line for line in lines if "pruebas" in line)
        heading = next(line for line in lines if line.startswith("Solo en el remoto"))
        assert "según el último contacto, hace 2h" in heading
        assert "origin/feat/de-otra" in lines[-1]


async def test_cambiar_a_una_rama_local():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("b")
        await pilot.pause()
        highlight(app, "main")
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        text = dialog_text(app)
        assert "Cambiar a la rama main" in text
        assert "$ git switch main" in text
        assert "Respaldo automático" in text  # hay cambios sin guardar
        await pilot.press("enter")
        await settle(app, pilot)
        (_, plan), = executor.calls
        assert plan.commands == (("switch", "main"),)


async def test_elegir_una_rama_solo_remota_crea_la_local_que_la_sigue():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("b")
        await pilot.pause()
        highlight(app, "origin/feat/de-otra")
        await pilot.press("enter")
        await pilot.pause()
        assert "$ git switch -c feat/de-otra --track origin/feat/de-otra" in dialog_text(app)
        await pilot.press("enter")
        await settle(app, pilot)
        assert executor.calls[0][1].commands == (
            ("switch", "-c", "feat/de-otra", "--track", "origin/feat/de-otra"),
        )


async def test_n_crea_una_rama_validando_el_nombre():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("b")
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen)
        await pilot.press(*"mi rama")
        await pilot.pause()
        assert "no puede llevar espacios" in dialog_text(app)
        await pilot.press("enter")  # nombre inválido: no pasa nada
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen) and executor.calls == []
        for _ in range(5):
            await pilot.press("backspace")
        await pilot.press(*"-rama")
        await pilot.pause()
        assert "$ git switch -c mi-rama" in dialog_text(app)
        await pilot.press("enter")
        await settle(app, pilot)
        assert executor.calls[0][1].commands == (("switch", "-c", "mi-rama"),)


async def test_d_borra_solo_ramas_borradas_en_el_remoto_y_mergeadas():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        # Con trabajo sin mergear: se explica y no se borra.
        await pilot.press("b")
        await pilot.pause()
        highlight(app, "feat/a-medias")
        await pilot.press("d")
        await pilot.pause()
        assert isinstance(app.screen, InfoScreen)
        assert "perdería ese trabajo" in dialog_text(app)
        await pilot.press("escape")
        await settle(app, pilot)
        assert executor.calls == []

        # Ya mergeada: pide confirmación y usa -d.
        await pilot.press("b")
        await pilot.pause()
        highlight(app, "feat/lista")
        await pilot.press("d")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        text = dialog_text(app)
        assert "Borrar la rama feat/lista" in text
        assert "$ git branch -d feat/lista" in text
        assert executor.calls == []  # nada sin confirmar
        await pilot.press("enter")
        await settle(app, pilot)
        assert executor.calls[0][1].commands == (("branch", "-d", "feat/lista"),)


async def test_esc_en_la_vista_de_ramas_no_hace_nada():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("b")
        await pilot.pause()
        await pilot.press("escape")
        await settle(app, pilot)
        assert len(app.screen_stack) == 1 and executor.calls == []


# ── Deshacer ────────────────────────────────────────────────────


async def test_u_ofrece_commit_cambios_y_respaldos():
    app = make_app(FakeExecutor())
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("u")
        await pilot.pause()
        lines = picker_lines(app)
        assert 'El último commit  "agrega pagos"' in lines[1]
        assert "Los cambios sin guardar  3 archivos" in lines[2]
        assert lines[3] == "Volver a un respaldo"
        assert "hace 1h 00m" in lines[4] and "antes de descartar cambios" in lines[4]
        assert "rama feature/pagos" in lines[4] and "con cambios sin guardar" in lines[4]
        assert "antes de bajar cambios" in lines[5] and "rama main" in lines[5]


async def test_deshacer_el_ultimo_commit_desde_el_menu():
    executor = FakeExecutor()
    status = replace(sample_status(), behind=0, head_subject="agrega pagos", has_parent=True)
    app = make_app(executor, status)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("u")
        await pilot.pause()
        await pilot.press("enter")  # primera opción: el último commit
        await pilot.pause()
        text = dialog_text(app)
        assert 'Se deshace el commit "agrega pagos"' in text
        assert "$ git reset --soft HEAD~1" in text
        assert "Respaldo automático" in text
        await pilot.press("enter")
        await settle(app, pilot)
        assert executor.calls[0][1].commands == (("reset", "--soft", "HEAD~1"),)


async def test_descartar_cambios_va_en_rojo_y_con_respaldo():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("u")
        await pilot.pause()
        highlight(app, "Los cambios sin guardar")
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen) and app.screen.danger
        text = dialog_text(app)
        assert "Se descartan los cambios de 3 archivos" in text
        assert "$ git reset --hard HEAD" in text and "Respaldo automático" in text
        await pilot.press("escape")
        await settle(app, pilot)
        assert executor.calls == []


async def test_restaurar_un_respaldo_de_la_rama_actual():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("u")
        await pilot.pause()
        highlight(app, "antes de descartar cambios")
        await pilot.press("enter")
        await pilot.pause()
        text = dialog_text(app)
        assert "Volver a un respaldo" in text
        assert "La rama feature/pagos vuelve al commit 9999999" in text
        assert "hace 1h 00m" in text
        assert "$ git stash apply" in text
        await pilot.press("enter")
        await settle(app, pilot)
        assert executor.calls[0][1].commands[0] == ("reset", "--hard", BACKUPS[0].ref)


async def test_un_respaldo_de_otra_rama_no_se_restaura_aqui():
    executor = FakeExecutor()
    app = make_app(executor)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("u")
        await pilot.pause()
        highlight(app, "rama main")
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, InfoScreen)
        assert "Este respaldo es de la rama main" in dialog_text(app)
        assert executor.calls == []


async def test_el_pie_incluye_ramas_y_deshacer():
    app = make_app(FakeExecutor())
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        await pilot.press("2")
        await pilot.pause()
        line = str(app.query_one(HintBar).render())
        assert "b ramas" in line and "u deshacer" in line
