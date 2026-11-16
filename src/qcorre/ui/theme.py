"""Paleta y tema oscuro de qcorre.

Los colores se definen una sola vez aquí. El CSS (``theme.tcss``) los usa como
variables (``$primary``, ``$qc-border``...) y el código Python los importa
cuando necesita pintar texto a mano.
"""

from __future__ import annotations

from textual.theme import Theme

# Fondos, del más profundo al más elevado.
BACKGROUND = "#0a0d13"
SURFACE = "#10141c"
PANEL = "#171c26"

# Texto y líneas.
FOREGROUND = "#d7dde8"
MUTED = "#6b7689"
BORDER = "#262d3a"

# Acento de la marca y colores de estado (solo para comunicar estado).
ACCENT = "#8b9cff"
SECONDARY = "#6fd3f2"
SUCCESS = "#7ee2a8"
WARNING = "#f5c56b"
ERROR = "#ff7a85"

# Colores para los carriles del gráfico de ramas.
LANES = ("#8b9cff", "#7ee2a8", "#f5c56b", "#ff9bd2", "#6fd3f2", "#ff7a85")

QCORRE_THEME = Theme(
    name="qcorre",
    primary=ACCENT,
    secondary=SECONDARY,
    accent=ACCENT,
    foreground=FOREGROUND,
    background=BACKGROUND,
    surface=SURFACE,
    panel=PANEL,
    success=SUCCESS,
    warning=WARNING,
    error=ERROR,
    dark=True,
    variables={
        "qc-muted": MUTED,
        "qc-border": BORDER,
    },
)
