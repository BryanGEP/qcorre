"""Panel derecho: el estado de git del proyecto seleccionado, en lenguaje humano."""

from __future__ import annotations

import time
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from qcorre.git.parse import RepoStatus
from qcorre.git.runner import GitError
from qcorre.i18n import t
from qcorre.models import Project
from qcorre.ui import theme
from qcorre.ui.git_view import status_body
from qcorre.ui.widgets import Panel


class GitPanel(Panel):
    """Muestra el repo del proyecto seleccionado.

    No ejecuta git: la app le entrega el resultado con ``show_status``. Guarda
    el último estado de cada repo para mostrarlo al instante al volver a él.
    """

    title_key = "panel.git"

    def __init__(self, *, id: str) -> None:
        super().__init__(id=id)
        self.project: Project | None = None
        self._orphans = False
        self._results: dict[Path, RepoStatus | GitError] = {}

    def compose(self) -> ComposeResult:
        yield Static(classes="empty")
        with VerticalScroll(id="git-scroll"):
            yield Static(id="git-body")

    @property
    def status(self) -> RepoStatus | None:
        """Estado mostrado ahora mismo (si el proyecto es un repo ya leído)."""
        result = self._results.get(self.project.path) if self.project else None
        return result if isinstance(result, RepoStatus) else None

    def show_project(self, project: Project | None, *, orphans: bool = False) -> None:
        """Cambia el proyecto mostrado (``orphans`` = el grupo de huérfanos)."""
        self.project = project
        self._orphans = orphans
        self.update_texts()

    def show_status(self, path: Path, result: RepoStatus | GitError) -> None:
        """Recibe el estado leído (o el error) del repo en ``path``."""
        self._results[path] = result
        if self.project is not None and self.project.path == path:
            self.update_texts()

    def on_resize(self) -> None:
        self.update_texts()  # el mapa se adapta al ancho

    def update_texts(self) -> None:
        project = self.project
        if project is None:
            self.border_title = t("panel.git")
            self._message(t("git.orphans") if self._orphans else t("git.empty"))
            return
        self.border_title = project.name
        if not project.has_git:
            self._message(_project_heading(project, t("git.no_repo")))
            return

        result = self._results.get(project.path)
        if result is None:
            self._message(_project_heading(project, t("git.loading")))
        elif isinstance(result, GitError):
            self._message(_error_text(result))
        else:
            if result.branch:
                self.border_title = f"{project.name} · {result.branch}"
            # Se usa el ancho del panel (siempre visible) menos el margen del
            # área con scroll, que puede estar oculta y medir cero.
            width = max(30, self.content_size.width - 2)
            self._body(status_body(result, time.time(), width=width))

    # ── Internos ────────────────────────────────────────────────

    def _message(self, content: Text | str) -> None:
        """Mensaje centrado (sin repo, cargando, error...)."""
        empty = self.query_one(".empty", Static)
        empty.update(content)
        empty.display = True
        self.query_one("#git-scroll").display = False

    def _body(self, content: Text) -> None:
        self.query_one("#git-body", Static).update(content)
        self.query_one(".empty", Static).display = False
        self.query_one("#git-scroll").display = True


def _project_heading(project: Project, note: str) -> Text:
    text = Text(justify="center")
    text.append(project.name + "\n", style=f"bold {theme.FOREGROUND}")
    text.append(str(project.path), style=theme.MUTED)
    text.append("\n\n" + note, style=theme.MUTED)
    return text


def _error_text(error: GitError) -> Text:
    text = Text(justify="center")
    key = f"git.error.{error.reason}"
    text.append(t(key), style=theme.WARNING)
    if error.reason == "failed" and error.detail:
        text.append("\n\n" + error.detail, style=theme.MUTED)
    return text
