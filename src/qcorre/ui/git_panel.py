"""Panel derecho: el git del proyecto seleccionado, en lenguaje humano.

Tiene dos vistas, que se alternan con una tecla: el estado (cambios y mapa con
el remoto) y el historial (gráfico de ramas).
"""

from __future__ import annotations

import time
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from qcorre.git.history import History
from qcorre.git.parse import RepoStatus
from qcorre.git.runner import GitError
from qcorre.i18n import t
from qcorre.models import Project
from qcorre.ui import theme
from qcorre.ui.git_view import status_body
from qcorre.ui.history_view import history_body
from qcorre.ui.widgets import Panel

STATUS = "status"
HISTORY = "history"


class GitPanel(Panel):
    """Muestra el repo del proyecto seleccionado.

    No ejecuta git: la app le entrega los resultados con ``show_status`` y
    ``show_history``. Guarda lo último de cada repo para mostrarlo al instante
    al volver a él.
    """

    title_key = "panel.git"

    def __init__(self, *, id: str) -> None:
        super().__init__(id=id)
        self.project: Project | None = None
        self.mode = STATUS
        self._orphans = False
        self._results: dict[Path, RepoStatus | GitError] = {}
        self._histories: dict[Path, History | GitError] = {}
        self._expanded = False  # ¿se listan todos los archivos?
        self._shown: Text | None = None  # lo último pintado en el cuerpo

    def compose(self) -> ComposeResult:
        yield Static(classes="empty")
        yield Static(id="git-tabs")
        with VerticalScroll(id="git-scroll"):
            yield Static(id="git-body")

    @property
    def status(self) -> RepoStatus | None:
        """Estado del repo mostrado (si el proyecto es un repo ya leído)."""
        result = self._results.get(self.project.path) if self.project else None
        return result if isinstance(result, RepoStatus) else None

    @property
    def has_repo(self) -> bool:
        return self.project is not None and self.project.has_git

    def toggle_files(self) -> None:
        """Alterna entre ver los primeros archivos y verlos todos."""
        self._expanded = not self._expanded
        self.update_texts()

    def toggle_history(self) -> None:
        """Alterna entre la vista de estado y la de historial."""
        self.mode = STATUS if self.mode == HISTORY else HISTORY
        self.update_texts()
        self.query_one("#git-scroll", VerticalScroll).scroll_home(animate=False)

    def show_project(self, project: Project | None, *, orphans: bool = False) -> None:
        """Cambia el proyecto mostrado (``orphans`` = el grupo de huérfanos)."""
        if project is None or self.project is None or project.path != self.project.path:
            self._expanded = False  # cada proyecto empieza con la lista resumida
        self.project = project
        self._orphans = orphans
        self.update_texts()

    def show_status(self, path: Path, result: RepoStatus | GitError) -> None:
        """Recibe el estado leído (o el error) del repo en ``path``."""
        self._results[path] = result
        if self.project is not None and self.project.path == path:
            self.update_texts()

    def show_history(self, path: Path, result: History | GitError) -> None:
        """Recibe el historial leído (o el error) del repo en ``path``."""
        self._histories[path] = result
        if self.project is not None and self.project.path == path:
            self.update_texts()

    def on_resize(self) -> None:
        self.update_texts()  # el mapa y el historial se adaptan al ancho

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

        status = self._results.get(project.path)
        if isinstance(status, RepoStatus) and status.branch:
            self.border_title = f"{project.name} · {status.branch}"
        width = self._body_width()

        if self.mode == HISTORY:
            history = self._histories.get(project.path)
            if history is None:
                self._body(Text(t("history.loading"), style=theme.MUTED))
            elif isinstance(history, GitError):
                self._body(_error_text(history))
            else:
                self._body(history_body(history, time.time(), width=width))
        elif status is None:
            self._body(Text(t("git.loading"), style=theme.MUTED))
        elif isinstance(status, GitError):
            self._body(_error_text(status))
        else:
            self._body(status_body(status, time.time(), width=width, expanded=self._expanded))

    # ── Internos ────────────────────────────────────────────────

    def _body_width(self) -> int:
        """Columnas disponibles para el contenido de la vista activa."""
        scroll = self.query_one("#git-scroll", VerticalScroll)
        width = scroll.scrollable_content_region.width if scroll.display else 0
        if width <= 0:
            # El área con scroll está oculta (mide cero): se estima con el
            # ancho del panel menos sus márgenes y la barra de scroll.
            width = self.content_size.width - 3
        return max(30, width)

    def _message(self, content: Text | str) -> None:
        """Mensaje centrado, sin pestañas (no hay repo que mostrar)."""
        empty = self.query_one(".empty", Static)
        empty.update(content)
        empty.display = True
        self.query_one("#git-tabs").display = False
        self.query_one("#git-scroll").display = False
        self._shown = None

    def _body(self, content: Text) -> None:
        """Contenido de la vista activa, bajo las pestañas."""
        self.query_one("#git-tabs", Static).update(self._tabs())
        self.query_one("#git-tabs").display = True
        # Si no cambió nada no se repinta: así no se pierde la posición del scroll.
        body = self.query_one("#git-body", Static)
        # En el historial cada commit ocupa exactamente un renglón: si una línea
        # no cabe se corta, nunca se parte (desalinearía el gráfico).
        body.set_class(self.mode == HISTORY, "one-line")
        if content != self._shown:
            body.update(content)
            self._shown = content
        self.query_one(".empty", Static).display = False
        self.query_one("#git-scroll").display = True

    def _tabs(self) -> Text:
        """Pestañas: la vista activa resaltada y la tecla que las alterna."""
        text = Text(no_wrap=True, overflow="ellipsis")
        for index, (mode, key) in enumerate(((STATUS, "git.tab.status"), (HISTORY, "git.tab.history"))):
            if index:
                text.append("   ")
            active = mode == self.mode
            style = f"bold underline {theme.ACCENT}" if active else theme.MUTED
            text.append(t(key), style=style)
        text.append("     h ", style=f"bold {theme.ACCENT}")
        text.append(t("git.tab.switch"), style=theme.MUTED)
        return text


def _project_heading(project: Project, note: str) -> Text:
    text = Text(justify="center")
    text.append(project.name + "\n", style=f"bold {theme.FOREGROUND}")
    text.append(str(project.path), style=theme.MUTED)
    text.append("\n\n" + note, style=theme.MUTED)
    return text


def _error_text(error: GitError) -> Text:
    text = Text()
    key = f"git.error.{error.reason}"
    text.append(t(key), style=theme.WARNING)
    if error.reason == "failed" and error.detail:
        text.append("\n\n" + error.detail, style=theme.MUTED)
    return text
