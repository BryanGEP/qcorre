"""Base común de los diálogos (ventanas modales) de qcorre."""

from __future__ import annotations

from textual import events
from textual.screen import ModalScreen, ScreenResultType

# Fracción del alto de la pantalla que puede ocupar un diálogo entero. Debe
# coincidir con el ``max-height`` de ``#dialog`` en theme.tcss.
DIALOG_FRACTION = 0.85

# Filas que gasta el marco del diálogo: borde y margen interior, arriba y abajo.
_FRAME_ROWS = 4


class DialogScreen(ModalScreen[ScreenResultType]):
    """Ventana modal con título en el borde y una zona con scroll.

    Las subclases definen ``dialog_title`` y componen un contenedor ``#dialog``
    con una zona desplazable (``BODY``). Aquí se pone el título y se limita el
    alto de esa zona para que el diálogo completo quepa en la pantalla.

    El límite se fija en celdas desde el código, y no con ``max-height`` en
    porcentaje desde el CSS, porque en ese caso el diálogo reservaba alto para
    todo el contenido aunque estuviera recortado, y quedaban líneas en blanco
    bajo las teclas.
    """

    BODY = "#dialog-body"  # selector de la zona con scroll
    BODY_FRACTION = 0.6  # fracción del alto de la pantalla que puede ocupar
    FIXED_ROWS = 2  # filas del diálogo fuera de la zona con scroll (teclas y su margen)

    dialog_title = ""

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = self.dialog_title
        self._fit_body()

    def on_resize(self, event: events.Resize) -> None:
        self._fit_body()

    def body_limit(self, screen_height: int) -> int:
        """Alto máximo de la zona con scroll para una pantalla de ``screen_height`` filas."""
        by_fraction = int(screen_height * self.BODY_FRACTION)
        by_dialog = int(screen_height * DIALOG_FRACTION) - _FRAME_ROWS - self.FIXED_ROWS
        return max(3, min(by_fraction, by_dialog))

    def _fit_body(self) -> None:
        self.query_one(self.BODY).styles.max_height = self.body_limit(self.app.size.height)
