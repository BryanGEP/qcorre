"""Aplicación principal de qcorre."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.worker import Worker, WorkerState

from qcorre import i18n
from qcorre.collectors.killer import Killer
from qcorre.git import actions
from qcorre.git.actions import ActionPlan, ActionResult
from qcorre.git.backup import Backup, list_backups
from qcorre.git.branches import BranchList, read_branches
from qcorre.git.history import History, read_history
from qcorre.git.parse import RepoStatus
from qcorre.git.runner import GitError, GitRunner
from qcorre.git.status import read_status
from qcorre.i18n import t
from qcorre.models import DevProcess, Snapshot
from qcorre.ui import theme
from qcorre.ui.action_view import (
    blocked_body,
    blocked_reason,
    commit_body,
    failure_body,
    plan_body,
)
from qcorre.ui.branch_view import (
    DISCARD,
    UNDO_COMMIT,
    backup_age,
    branch_choices,
    find_backup,
    find_branch,
    undo_choices,
)
from qcorre.ui.confirm import ConfirmScreen, InfoScreen, PromptScreen
from qcorre.ui.detail_view import detail_body
from qcorre.ui.git_panel import HISTORY, GitPanel
from qcorre.ui.help_view import help_body
from qcorre.ui.kill_view import KillGroup, kill_body, result_message
from qcorre.ui.picker import PickerKey, PickerScreen
from qcorre.ui.projects_panel import ProjectsPanel
from qcorre.ui.widgets import Header, HintBar

# Cada cuántos segundos se vuelve a escanear el sistema.
REFRESH_SECONDS = 3.0


class QcorreApp(App[None]):
    """Panel del desarrollador: procesos por proyecto y git amigable.

    Cada pieza que toca el sistema se puede sustituir: ``scanner`` (devuelve
    un ``Snapshot``), ``killer`` (cierra procesos) y las de git (``git_reader``,
    ``git_executor``, ``branch_reader``, ``backup_reader``, ``history_reader``).
    Por defecto se usa el sistema real; los tests y el modo demo
    (``qcorre.demo.DemoWorld``) pasan las suyas. ``demo`` solo añade el
    distintivo "DEMO" en la cabecera.
    """

    TITLE = "qcorre"
    CSS_PATH = "theme.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("k", "kill", show=False),
        Binding("K", "kill_all", show=False),
        Binding("c", "git('commit')", show=False),
        Binding("p", "git('push')", show=False),
        Binding("l", "git('pull')", show=False),
        Binding("f", "git('fetch')", show=False),
        Binding("b", "branches", show=False),
        Binding("u", "undo", show=False),
        Binding("a", "toggle_files", show=False),
        Binding("h", "toggle_history", show=False),
        Binding("question_mark", "help", show=False),
        Binding("1", "focus_panel('projects')", show=False),
        Binding("2", "focus_panel('git')", show=False),
        Binding("r", "refresh", show=False),
        Binding("i", "toggle_language", show=False),
        Binding("t", "toggle_theme", show=False),
        Binding("q", "quit", show=False),
    ]

    # Atajos que van siempre al final del pie: (tecla, clave de traducción).
    # El resto del pie cambia según el contexto (ver ``footer_hints``).
    FOOTER_TAIL = [("?", "hint.help"), ("q", "hint.quit")]

    def __init__(
        self,
        scanner: Callable[[], Snapshot] | None = None,
        killer: Killer | None = None,
        git_reader: Callable[[Path], RepoStatus] | None = None,
        git_executor: Callable[[Path, ActionPlan], ActionResult] | None = None,
        branch_reader: Callable[[Path], BranchList] | None = None,
        backup_reader: Callable[[Path], list[Backup]] | None = None,
        history_reader: Callable[[Path], History] | None = None,
        *,
        refresh_seconds: float | None = REFRESH_SECONDS,
        demo: bool = False,
        theme_name: str = theme.DEFAULT_THEME,
    ) -> None:
        super().__init__()
        self.demo = demo
        for name in theme.THEMES:
            self.register_theme(theme.textual_theme(name))
        self.use_theme(theme_name)
        if scanner is None:
            from qcorre.scanner import Scanner

            scanner = Scanner(pinned=[Path.cwd()])
        self.scanner = scanner
        self.killer = killer or Killer()
        self.git_reader = git_reader or read_status
        self.git_executor = git_executor or _execute_with_git
        self.branch_reader = branch_reader or read_branches
        self.backup_reader = backup_reader or _read_backups
        self.history_reader = history_reader or read_history
        self.refresh_seconds = refresh_seconds

    def get_css_variables(self) -> dict[str, str]:
        """Añade las variables propias (``$qc-*``) a las del tema.

        El CSS se parsea antes de que el tema quede activo, así que las
        variables propias deben existir siempre, sea cual sea el tema.
        """
        return {**theme.css_variables(theme.current), **super().get_css_variables()}

    def use_theme(self, name: str) -> None:
        """Activa un tema: la paleta de Python y el tema de Textual (CSS)."""
        theme.use(name)
        self.theme = f"qcorre-{name}"

    def compose(self) -> ComposeResult:
        yield Header(id="header", demo=self.demo)
        with Horizontal(id="body"):
            yield ProjectsPanel(id="projects")
            yield GitPanel(id="git")
        yield HintBar()

    # Atajos de la app que quedan en pausa mientras hay un diálogo abierto.
    _PAUSED_IN_DIALOGS = frozenset(
        {
            "kill",
            "kill_all",
            "refresh",
            "toggle_language",
            "quit",
            "git",
            "branches",
            "undo",
            "toggle_files",
            "toggle_history",
            "help",
            "focus_panel",
            "toggle_theme",
        }
    )

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if len(self.screen_stack) > 1 and action in self._PAUSED_IN_DIALOGS:
            return False
        return True

    def on_mount(self) -> None:
        self.action_refresh()
        if self.refresh_seconds:
            self.set_interval(self.refresh_seconds, self.action_refresh)

    # ── Escaneo de procesos ─────────────────────────────────────

    def action_refresh(self) -> None:
        """Escanea el sistema en un hilo aparte para no congelar la interfaz."""
        if any(w.group == "scan" and w.is_running for w in self.workers):
            return  # el escaneo anterior sigue en curso
        self.run_worker(self.scanner, thread=True, group="scan", exit_on_error=False)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state is not WorkerState.SUCCESS:
            return
        if event.worker.group == "kill":
            message, severity = result_message(event.worker.result)
            self.notify(message, severity=severity)
            self.action_refresh()
            return
        if event.worker.group == "git":
            path, result = event.worker.result
            self.query_one(GitPanel).show_status(path, result)
            return
        if event.worker.group == "history":
            path, result = event.worker.result
            self.query_one(GitPanel).show_history(path, result)
            return
        if event.worker.group == "gitop":
            self._action_finished(event.worker.result)
            return
        if event.worker.group != "scan":
            return
        snapshot = event.worker.result
        if isinstance(snapshot, Snapshot):
            self.query_one(ProjectsPanel).show_snapshot(snapshot, time.time())
            orphans = sum(
                dev.is_orphan
                for dev in (
                    *(d for p in snapshot.projects for d in p.processes),
                    *snapshot.unassigned,
                )
            )
            self.query_one(Header).set_counts(
                len(snapshot.projects), snapshot.process_count, orphans
            )
            # Con cada refresco se relee también el repo que se está mirando.
            self._load_git()

    def on_projects_panel_selected(self, event: ProjectsPanel.Selected) -> None:
        row = event.row
        panel = self.query_one(GitPanel)
        previous = panel.project.path if panel.project else None
        panel.show_project(
            row.project if row else None,
            orphans=row is not None and row.project is None,
        )
        current = panel.project.path if panel.project else None
        if current != previous:
            self._load_git()
        self.update_footer()

    # ── Pie contextual y foco ───────────────────────────────────

    def on_descendant_focus(self) -> None:
        self.update_footer()

    def action_focus_panel(self, panel: str) -> None:
        """Salta al panel de proyectos (1) o al de git (2)."""
        if panel == "projects":
            self.query_one(ProjectsPanel).tree.focus()
        else:
            self.query_one("#git-scroll").focus()

    def footer_hints(self) -> list[tuple[str, str]]:
        """Los atajos útiles ahora mismo, del más al menos importante."""
        git = self.query_one(GitPanel)
        has_repo = git.has_repo
        focused = self.focused
        if focused is not None and git in focused.ancestors_with_self:
            hints = [("updown", "hint.scroll")]
            if has_repo:
                toggle = "hint.status" if git.mode == HISTORY else "hint.history"
                hints += [
                    ("h", toggle),
                    ("c", "hint.commit"),
                    ("p", "hint.push"),
                    ("l", "hint.pull"),
                    ("b", "hint.branches"),
                    ("u", "hint.undo"),
                    ("f", "hint.fetch"),
                ]
            return [*hints, ("1", "hint.to_projects")]

        row = self.query_one(ProjectsPanel).selected
        if row is None:
            return [("r", "hint.refresh")]
        hints = [("updown", "hint.move")]
        if row.process is not None:
            hints += [("enter", "hint.details"), ("k", "hint.kill")]
        else:
            hints.append(("enter", "hint.collapse"))
            processes = row.project.processes if row.project else self._orphans()
            if processes:
                hints.append(("K", "hint.kill_all"))
        if has_repo:
            hints += [("c", "hint.commit"), ("p", "hint.push"), ("2", "hint.to_git")]
        return hints

    def _orphans(self) -> tuple[DevProcess, ...]:
        snapshot = self.query_one(ProjectsPanel).snapshot
        return snapshot.unassigned if snapshot else ()

    def update_footer(self) -> None:
        self.query_one(HintBar).set_hints(self.footer_hints(), self.FOOTER_TAIL)

    # ── Git ─────────────────────────────────────────────────────

    def _load_git(self) -> None:
        """Lee en un hilo aparte el repo del proyecto seleccionado."""
        project = self.query_one(GitPanel).project
        if project is None or not project.has_git:
            return
        path = project.path

        def read() -> tuple[Path, RepoStatus | GitError]:
            try:
                return path, self.git_reader(path)
            except GitError as error:
                return path, error

        # ``exclusive`` descarta la lectura anterior si el usuario ya se movió
        # a otro proyecto.
        self.run_worker(read, thread=True, group="git", exclusive=True, exit_on_error=False)
        # El historial solo se lee mientras se está mirando.
        if self.query_one(GitPanel).mode == HISTORY:
            self._load_history()

    def _load_history(self) -> None:
        """Lee en un hilo aparte el historial del proyecto seleccionado."""
        project = self.query_one(GitPanel).project
        if project is None or not project.has_git:
            return
        path = project.path

        def read() -> tuple[Path, History | GitError]:
            try:
                return path, self.history_reader(path)
            except GitError as error:
                return path, error

        self.run_worker(read, thread=True, group="history", exclusive=True, exit_on_error=False)

    def action_toggle_history(self) -> None:
        """Alterna el panel de git entre el estado y el historial."""
        panel = self.query_one(GitPanel)
        if not panel.has_repo:
            self.notify(t("action.no_repo"), severity="warning")
            return
        panel.toggle_history()
        if panel.mode == HISTORY:
            self._load_history()
        self.update_footer()

    # ── Acciones de git ─────────────────────────────────────────

    def _repo(self) -> tuple[RepoStatus, Path] | None:
        """Estado y carpeta del repo seleccionado (avisa si no hay ninguno)."""
        panel = self.query_one(GitPanel)
        if panel.status is None or panel.project is None:
            self.notify(t("action.no_repo"), severity="warning")
            return None
        return panel.status, panel.project.path

    @work
    async def action_git(self, action: str) -> None:
        """Prepara una acción de git, la muestra y, si se confirma, la ejecuta."""
        repo = self._repo()
        if repo is None:
            return
        status, path = repo
        if action == actions.COMMIT:
            plan = await self._ask_commit(status)
            if plan is not None:
                self._run_plan(plan, path)
            return
        builders = {
            actions.PUSH: actions.plan_push,
            actions.PULL: actions.plan_pull,
            actions.FETCH: actions.plan_fetch,
        }
        await self._confirm_and_run(builders[action](status), path)

    async def _confirm_and_run(self, plan: ActionPlan, path: Path) -> None:
        """Muestra la vista previa del plan y lo ejecuta si el usuario confirma."""
        if plan.blocked:
            self.push_screen(InfoScreen(plan.title, blocked_body(plan)))
            return
        dialog = ConfirmScreen(
            plan.title,
            plan_body(plan),
            confirm_key=f"action.confirm.{plan.action}",
            danger=plan.danger,
        )
        if await self.push_screen_wait(dialog):
            self._run_plan(plan, path)

    def _run_plan(self, plan: ActionPlan, path: Path) -> None:
        self.notify(t("action.running"), timeout=2)
        self.run_worker(lambda: self.git_executor(path, plan), thread=True, group="gitop")

    async def _ask_commit(self, status: RepoStatus) -> ActionPlan | None:
        """Pide el mensaje del commit mostrando el comando exacto mientras se escribe."""
        empty = actions.plan_commit(status, "")
        if empty.blocked:
            self.push_screen(InfoScreen(empty.title, blocked_body(empty)))
            return None

        def preview(message: str) -> Text:
            shown = message.strip() or t("action.commit.message")
            return commit_body(status, actions.plan_commit(status, shown))

        message = await self.push_screen_wait(
            PromptScreen(
                empty.title,
                t("action.commit.prompt"),
                preview,
                placeholder=t("action.commit.placeholder"),
                confirm_key="action.confirm.commit",
                validate=lambda value: None if value else t("action.commit.empty"),
            )
        )
        return actions.plan_commit(status, message) if message else None

    def _action_finished(self, result: ActionResult) -> None:
        if result.ok:
            self.notify(actions.success_message(result))
        else:
            self.push_screen(InfoScreen(t("action.failed.title"), failure_body(result)))
        self._load_git()

    def action_toggle_files(self) -> None:
        """Alterna entre ver los primeros archivos con cambios y verlos todos."""
        self.query_one(GitPanel).toggle_files()

    # ── Ramas ───────────────────────────────────────────────────

    @work
    async def action_branches(self) -> None:
        """Vista de ramas: cambiar a una, crear una nueva o borrar una ya mergeada."""
        repo = self._repo()
        if repo is None:
            return
        status, path = repo
        try:
            branches = await asyncio.to_thread(self.branch_reader, path)
        except GitError as error:
            self.notify(error.detail or t("git.error.failed"), severity="error")
            return

        picked = await self.push_screen_wait(
            PickerScreen(
                t("branches.title"),
                branch_choices(branches, time.time()),
                select_key="branches.key.switch",
                keys=(
                    PickerKey("n", "new", "branches.key.new", needs_choice=False),
                    PickerKey("d", "delete", "branches.key.delete"),
                ),
            )
        )
        if picked is None:
            return
        action, choice = picked
        if action == "new":
            await self._ask_new_branch(status, path)
            return
        branch = find_branch(branches, choice or "")
        if branch is None:
            return
        if action == "delete":
            plan = actions.plan_delete_branch(status, branch)
        else:
            plan = actions.plan_switch(status, branch)
        await self._confirm_and_run(plan, path)

    async def _ask_new_branch(self, status: RepoStatus, path: Path) -> None:
        """Pide el nombre de la rama nueva, validándolo mientras se escribe."""

        def preview(name: str) -> Text:
            plan = actions.plan_new_branch(status, name)
            return blocked_reason(plan) if plan.blocked else plan_body(plan)

        name = await self.push_screen_wait(
            PromptScreen(
                t("action.branch.title"),
                t("action.branch.prompt"),
                preview,
                placeholder=t("action.branch.placeholder"),
                confirm_key="action.confirm.branch",
                validate=actions.branch_name_problem,
            )
        )
        if name:
            self._run_plan(actions.plan_new_branch(status, name), path)

    # ── Deshacer y respaldos ────────────────────────────────────

    @work
    async def action_undo(self) -> None:
        """Menú de deshacer: último commit, cambios sin guardar o volver a un respaldo."""
        repo = self._repo()
        if repo is None:
            return
        status, path = repo
        try:
            backups = await asyncio.to_thread(self.backup_reader, path)
        except GitError:
            backups = []

        now = time.time()
        picked = await self.push_screen_wait(
            PickerScreen(
                t("undo.title"),
                undo_choices(status, backups, now),
                select_key="undo.key.select",
            )
        )
        if picked is None or picked[1] is None:
            return
        choice = picked[1]
        if choice == UNDO_COMMIT:
            plan = actions.plan_undo_commit(status)
        elif choice == DISCARD:
            plan = actions.plan_discard(status)
        else:
            backup = find_backup(backups, choice)
            if backup is None:
                return
            plan = actions.plan_restore(status, backup, when=backup_age(backup, now))
        await self._confirm_and_run(plan, path)

    # ── Detalle de un proceso ───────────────────────────────────

    def on_projects_panel_detail_requested(self, event: ProjectsPanel.DetailRequested) -> None:
        process = event.row.process
        if process is None:
            return
        body = detail_body(process, event.row.project, time.time())
        self.push_screen(InfoScreen(process.label, body))

    # ── Matar procesos ──────────────────────────────────────────

    def action_kill(self) -> None:
        """Mata el proceso bajo el cursor (o todo el grupo, si es una cabecera)."""
        row = self.query_one(ProjectsPanel).selected
        if row is None:
            return
        if row.process is None:
            self.action_kill_all()
        else:
            self._confirm_kill(t("kill.title.process"), [row.process])

    def action_kill_all(self) -> None:
        """Mata todos los procesos del proyecto (o grupo) bajo el cursor."""
        panel = self.query_one(ProjectsPanel)
        row = panel.selected
        if row is None or panel.snapshot is None:
            return
        if row.project is None:
            title, processes = t("kill.title.orphans"), panel.snapshot.unassigned
        else:
            # Se toma el proyecto de la foto más reciente, no el de la fila.
            current = next(
                (p for p in panel.snapshot.projects if p.root == row.project.root), row.project
            )
            title, processes = t("kill.title.project", name=current.name), current.processes
        self._confirm_kill(title, processes)

    @work
    async def _confirm_kill(self, title: str, processes: Sequence[DevProcess]) -> None:
        """Muestra qué se va a cerrar y, si el usuario confirma, lo cierra."""
        groups: list[KillGroup] = []
        for process in processes:
            victims = self.killer.preview(process)
            if victims:
                groups.append((process, victims))
        if not groups:
            self.notify(t("kill.gone"), severity="warning")
            self.action_refresh()
            return

        dialog = ConfirmScreen(title, kill_body(groups), confirm_key="kill.confirm", danger=True)
        if not await self.push_screen_wait(dialog):
            return
        victims = [victim for _, group in groups for victim in group]
        self.run_worker(lambda: self.killer.kill(victims), thread=True, group="kill")

    # ── Ayuda ───────────────────────────────────────────────────

    def action_help(self) -> None:
        """Muestra todos los atajos de teclado."""
        self.push_screen(InfoScreen(t("help.title"), help_body()))

    # ── Idioma ──────────────────────────────────────────────────

    def action_toggle_language(self) -> None:
        """Alterna entre español e inglés y repinta los textos."""
        i18n.set_language(i18n.next_language())
        self.refresh_texts()

    def action_toggle_theme(self) -> None:
        """Alterna entre el tema oscuro y el claro, y repinta todo."""
        self.use_theme(theme.next_theme())
        self.refresh_texts()

    def refresh_texts(self) -> None:
        """Pide a cada widget con textos traducibles que se actualice."""
        for widget in self.query("*"):
            update = getattr(widget, "update_texts", None)
            if callable(update):
                update()


def _execute_with_git(path: Path, plan: ActionPlan) -> ActionResult:
    """Ejecuta un plan con el git del sistema en el repo ``path``."""
    return actions.execute(plan, GitRunner(path))


def _read_backups(path: Path) -> list[Backup]:
    """Respaldos del repo ``path``, con el git del sistema."""
    return list_backups(GitRunner(path))
