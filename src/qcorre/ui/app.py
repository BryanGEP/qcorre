"""Aplicación principal de qcorre."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.worker import Worker, WorkerState

from qcorre import i18n
from qcorre.collectors.killer import Killer
from qcorre.git.parse import RepoStatus
from qcorre.git.runner import GitError
from qcorre.git.status import read_status
from qcorre.i18n import t
from qcorre.models import DevProcess, Snapshot
from qcorre.ui.confirm import ConfirmScreen, InfoScreen
from qcorre.ui.detail_view import detail_body
from qcorre.ui.git_panel import GitPanel
from qcorre.ui.kill_view import KillGroup, kill_body, result_message
from qcorre.ui.projects_panel import ProjectsPanel
from qcorre.ui.theme import QCORRE_THEME
from qcorre.ui.widgets import Header, HintBar

# Cada cuántos segundos se vuelve a escanear el sistema.
REFRESH_SECONDS = 3.0


class QcorreApp(App[None]):
    """Panel del desarrollador: procesos por proyecto y git amigable.

    ``scanner`` es cualquier función que devuelva un ``Snapshot``, ``killer``
    quien cierra procesos y ``git_reader`` una función que lee el estado de un
    repo. Por defecto se usa el sistema real; los tests y el modo demo pasan
    los suyos.
    """

    TITLE = "qcorre"
    CSS_PATH = "theme.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("k", "kill", show=False),
        Binding("K", "kill_all", show=False),
        Binding("r", "refresh", show=False),
        Binding("i", "toggle_language", show=False),
        Binding("q", "quit", show=False),
    ]

    # Atajos que se muestran en el pie: (tecla, clave de traducción).
    HINTS = [
        ("updown", "hint.move"),
        ("tab", "hint.panel"),
        ("enter", "hint.details"),
        ("k", "hint.kill"),
        ("K", "hint.kill_all"),
        ("r", "hint.refresh"),
        ("i", "hint.language"),
        ("q", "hint.quit"),
    ]

    def __init__(
        self,
        scanner: Callable[[], Snapshot] | None = None,
        killer: Killer | None = None,
        git_reader: Callable[[Path], RepoStatus] | None = None,
        *,
        refresh_seconds: float | None = REFRESH_SECONDS,
    ) -> None:
        super().__init__()
        if scanner is None:
            from qcorre.scanner import Scanner

            scanner = Scanner(pinned=[Path.cwd()])
        self.scanner = scanner
        self.killer = killer or Killer()
        self.git_reader = git_reader or read_status
        self.refresh_seconds = refresh_seconds
        self.register_theme(QCORRE_THEME)
        self.theme = QCORRE_THEME.name

    def get_css_variables(self) -> dict[str, str]:
        """Añade las variables propias (``$qc-*``) a las del tema.

        El CSS se parsea antes de que el tema quede activo, así que las
        variables propias deben existir siempre, sea cual sea el tema.
        """
        return {**QCORRE_THEME.variables, **super().get_css_variables()}

    def compose(self) -> ComposeResult:
        yield Header(id="header")
        with Horizontal(id="body"):
            yield ProjectsPanel(id="projects")
            yield GitPanel(id="git")
        yield HintBar(self.HINTS)

    # Atajos de la app que quedan en pausa mientras hay un diálogo abierto.
    _PAUSED_IN_DIALOGS = frozenset({"kill", "kill_all", "refresh", "toggle_language", "quit"})

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
        if event.worker.group != "scan":
            return
        snapshot = event.worker.result
        if isinstance(snapshot, Snapshot):
            self.query_one(ProjectsPanel).show_snapshot(snapshot, time.time())
            self.query_one(Header).set_counts(len(snapshot.projects), snapshot.process_count)
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

    # ── Idioma ──────────────────────────────────────────────────

    def action_toggle_language(self) -> None:
        """Alterna entre español e inglés y repinta los textos."""
        i18n.set_language(i18n.next_language())
        self.refresh_texts()

    def refresh_texts(self) -> None:
        """Pide a cada widget con textos traducibles que se actualice."""
        for widget in self.query("*"):
            update = getattr(widget, "update_texts", None)
            if callable(update):
                update()
