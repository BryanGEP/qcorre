"""Paletas y temas de qcorre: oscuro (por defecto) y claro.

Los colores se definen una sola vez aquí, en dos paletas. El CSS
(``theme.tcss``) los recibe como variables de Textual (``$primary``,
``$qc-border``...) y el código Python los lee como atributos de este módulo
(``theme.ACCENT``) en el momento de pintar.

Para cambiar de tema en caliente, ``use()`` reasigna esos atributos y la app
repinta. Por eso el resto del código debe leer siempre ``theme.X`` al pintar,
nunca guardarlo en una constante al importar.

Todos los colores de texto cumplen el contraste AA (4.5:1) sobre los tres
fondos donde aparecen: la pantalla, las tarjetas y las píldoras.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from textual.theme import Theme


@dataclass(frozen=True)
class Palette:
    """Los colores de un tema."""

    dark: bool
    # Fondos, del más profundo al más elevado.
    background: str  # la pantalla
    surface: str  # las tarjetas (paneles y diálogos)
    panel: str  # píldoras, chips y la fila seleccionada
    # Texto y líneas.
    foreground: str
    muted: str
    border: str
    # Acento de la marca y colores de estado (solo para comunicar estado).
    accent: str
    secondary: str
    success: str
    warning: str
    error: str
    # Colores de los carriles del gráfico de ramas.
    lanes: tuple[str, ...]


PALETTES: dict[str, Palette] = {
    "dark": Palette(
        dark=True,
        background="#16141f",
        surface="#1f1c2b",
        panel="#2a2540",
        foreground="#ece8f6",
        muted="#a29cb8",
        border="#3a3452",
        accent="#c4a7ff",
        secondary="#8cc8ff",
        success="#8be3c0",
        warning="#ffb38a",
        error="#ff8fb1",
        lanes=("#c4a7ff", "#8be3c0", "#ffb38a", "#ff8fb1", "#8cc8ff", "#f2d98c"),
    ),
    "light": Palette(
        dark=False,
        background="#f4f1fa",
        surface="#ffffff",
        panel="#ebe5f6",
        foreground="#2b2638",
        muted="#625c76",
        border="#cfc6e3",
        accent="#6a45c9",
        secondary="#1a5ea8",
        success="#1d7553",
        warning="#9a4914",
        error="#b02d57",
        lanes=("#6a45c9", "#1d7553", "#9a4914", "#b02d57", "#1a5ea8", "#7a6400"),
    ),
}

THEMES: tuple[str, ...] = tuple(PALETTES)
DEFAULT_THEME = "dark"


def textual_theme(name: str) -> Theme:
    """El tema de Textual que corresponde a una paleta (``qcorre-dark``...)."""
    palette = PALETTES[name]
    return Theme(
        name=f"qcorre-{name}",
        primary=palette.accent,
        secondary=palette.secondary,
        accent=palette.accent,
        foreground=palette.foreground,
        background=palette.background,
        surface=palette.surface,
        panel=palette.panel,
        success=palette.success,
        warning=palette.warning,
        error=palette.error,
        dark=palette.dark,
        variables=css_variables(name),
    )


def css_variables(name: str) -> dict[str, str]:
    """Variables propias del CSS (``$qc-*``) para una paleta."""
    palette = PALETTES[name]
    return {
        "qc-muted": palette.muted,
        "qc-border": palette.border,
        "qc-pill": palette.panel,
    }


# ── Tema activo ─────────────────────────────────────────────────

current = DEFAULT_THEME

BACKGROUND = SURFACE = PANEL = FOREGROUND = MUTED = BORDER = ""
ACCENT = SECONDARY = SUCCESS = WARNING = ERROR = ""
LANES: tuple[str, ...] = ()


def use(name: str) -> None:
    """Activa una paleta: los atributos de este módulo pasan a sus colores."""
    if name not in PALETTES:
        raise ValueError(f"Tema desconocido: {name!r}")
    global current, BACKGROUND, SURFACE, PANEL, FOREGROUND, MUTED, BORDER
    global ACCENT, SECONDARY, SUCCESS, WARNING, ERROR, LANES
    palette = asdict(PALETTES[name])
    current = name
    BACKGROUND, SURFACE, PANEL = palette["background"], palette["surface"], palette["panel"]
    FOREGROUND, MUTED, BORDER = palette["foreground"], palette["muted"], palette["border"]
    ACCENT, SECONDARY = palette["accent"], palette["secondary"]
    SUCCESS, WARNING, ERROR = palette["success"], palette["warning"], palette["error"]
    LANES = tuple(palette["lanes"])


def next_theme() -> str:
    """El tema que sigue al activo (para la tecla de cambiar de tema)."""
    index = THEMES.index(current)
    return THEMES[(index + 1) % len(THEMES)]


use(DEFAULT_THEME)
