"""Aplicación principal de qcorre."""

from __future__ import annotations

import time
from collections.abc import Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.worker import Worker, WorkerState

from qcorre import i18n
from qcorre.models import Snapshot
from qcorre.ui.projects_panel import ProjectsPanel
from qcorre.ui.theme import QCORRE_THEME
from qcorre.ui.widgets import GitPanel, Header, HintBar

# Cada cuántos segundos se vuelve a escanear el sistema.
REFRESH_SECONDS = 3.0


class QcorreApp(App[None]):
    """Panel del desarrollador: procesos por proyecto y git amigable.

    ``scanner`` es cualquier función que devuelva un ``Snapshot``. Por defecto
    se escanea el sistema real; los tests y el modo demo pasan la suya.
    """

    TITLE = "qcorre"
    CSS_PATH = "theme.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("r", "refresh", show=False),
        Binding("i", "toggle_language", show=False),
        Binding("q", "quit", show=False),
    ]

    # Atajos que se muestran en el pie: (tecla, clave de traducción).
    HINTS = [
        ("updown", "hint.move"),
        ("tab", "hint.panel"),
        ("r", "hint.refresh"),
        ("i", "hint.language"),
        ("q", "hint.quit"),
    ]

    def __init__(
        self,
        scanner: Callable[[], Snapshot] | None = None,
        *,
        refresh_seconds: float | None = REFRESH_SECONDS,
    ) -> None:
        super().__init__()
        if scanner is None:
            from qcorre.scanner import Scanner

            scanner = Scanner()
        self.scanner = scanner
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
        if event.worker.group != "scan" or event.state is not WorkerState.SUCCESS:
            return
        snapshot = event.worker.result
        if isinstance(snapshot, Snapshot):
            self.query_one(ProjectsPanel).show_snapshot(snapshot, time.time())
            self.query_one(Header).set_counts(len(snapshot.projects), snapshot.process_count)

    def on_projects_panel_selected(self, event: ProjectsPanel.Selected) -> None:
        row = event.row
        self.query_one(GitPanel).show_project(
            row.project if row else None,
            orphans=row is not None and row.project is None,
        )

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
