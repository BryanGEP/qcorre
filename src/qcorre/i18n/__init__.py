"""Traducciones de la interfaz (español / inglés).

Uso::

    from qcorre.i18n import t
    t("app.tagline")
    t("procs.count", n=3)   # elige singular o plural según ``n``

Cada catálogo es un diccionario ``clave -> texto``. Para plurales el valor es
un diccionario ``{"one": ..., "other": ...}``. Los textos admiten campos de
``str.format`` (por ejemplo ``{n}``).
"""

from __future__ import annotations

import locale
import os
import sys
from collections.abc import Callable, Mapping

from qcorre.i18n import en, es

Catalog = Mapping[str, "str | Mapping[str, str]"]

LANGUAGES: tuple[str, ...] = ("es", "en")
DEFAULT_LANGUAGE = "en"

_CATALOGS: dict[str, Catalog] = {"es": es.MESSAGES, "en": en.MESSAGES}
_current = DEFAULT_LANGUAGE


def get_language() -> str:
    """Devuelve el idioma activo (``"es"`` o ``"en"``)."""
    return _current


def set_language(lang: str) -> None:
    """Cambia el idioma activo. Lanza ``ValueError`` si no está soportado."""
    global _current
    if lang not in _CATALOGS:
        raise ValueError(f"Idioma no soportado: {lang!r}")
    _current = lang


def next_language() -> str:
    """Devuelve el idioma que sigue al activo (para el atajo de cambiar idioma)."""
    index = LANGUAGES.index(_current)
    return LANGUAGES[(index + 1) % len(LANGUAGES)]


def t(key: str, **params: object) -> str:
    """Traduce ``key`` al idioma activo.

    Si la clave no existe en el idioma activo se usa el español, y si tampoco
    existe se devuelve la clave tal cual: así un texto faltante se nota en
    pantalla pero nunca truena la app.
    """
    entry = _CATALOGS[_current].get(key)
    if entry is None:
        entry = es.MESSAGES.get(key)
    if entry is None:
        return key
    if not isinstance(entry, str):
        form = "one" if params.get("n") == 1 else "other"
        entry = entry[form]
    return entry.format(**params) if params else entry


def normalize_language(code: str | None) -> str | None:
    """Convierte un código de locale en un idioma soportado, o ``None``.

    Acepta formatos de los tres sistemas: ``es_MX.UTF-8``, ``es-419``,
    ``Spanish_Mexico`` (Windows), ``en_US``...
    """
    if not code:
        return None
    code = code.strip().lower()
    if code.startswith(("es", "spanish")):
        return "es"
    if code.startswith(("en", "english")):
        return "en"
    return None


def detect_language(
    environ: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
    system_locale: Callable[[], str | None] | None = None,
) -> str:
    """Elige el idioma inicial.

    Orden de prioridad:

    1. La variable ``QCORRE_LANG`` (elección explícita del usuario).
    2. En Windows, el idioma de la interfaz del sistema. Va *antes* que
       ``LANG``/``LC_*`` porque en Windows esas variables no reflejan el
       idioma del usuario: las fijan herramientas como Git Bash o VS Code
       (casi siempre a ``en_US.UTF-8``).
    3. Las variables de locale estándar (``LC_ALL``, ``LC_MESSAGES``, ``LANG``).
    4. En los demás sistemas, el locale del sistema.
    5. Inglés.

    ``environ``, ``platform`` y ``system_locale`` se pueden inyectar para
    testear; por defecto se usan los reales.
    """
    env = os.environ if environ is None else environ
    platform = sys.platform if platform is None else platform
    if system_locale is None:
        # Con un entorno inyectado no se consulta al sistema real, para que
        # los tests sean deterministas.
        system_locale = _system_locale if environ is None else (lambda: None)

    explicit = normalize_language(env.get("QCORRE_LANG"))
    if explicit:
        return explicit

    windows = platform == "win32"
    if windows:
        lang = normalize_language(system_locale())
        if lang:
            return lang
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        lang = normalize_language(env.get(var))
        if lang:
            return lang
    if not windows:
        lang = normalize_language(system_locale())
        if lang:
            return lang
    return DEFAULT_LANGUAGE


def _system_locale() -> str | None:
    """Idioma del sistema operativo, si se puede averiguar.

    En Windows es el idioma de la interfaz del usuario (el de los menús), no
    el formato regional: alguien puede tener Windows en español con formato
    de fechas de otro país.
    """
    if sys.platform == "win32":
        try:
            import ctypes

            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return locale.windows_locale.get(lang_id)
        except Exception:
            return None
    try:
        return locale.getlocale()[0]
    except Exception:
        return None
