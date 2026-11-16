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
from collections.abc import Mapping

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


def detect_language(environ: Mapping[str, str] | None = None) -> str:
    """Elige el idioma inicial.

    Orden: variable ``QCORRE_LANG``, variables de locale estándar, idioma del
    sistema y, si nada coincide, inglés.
    """
    env = os.environ if environ is None else environ
    for var in ("QCORRE_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        lang = normalize_language(env.get(var))
        if lang:
            return lang
    # Solo se consulta al sistema cuando se usa el entorno real, para que los
    # tests que pasan su propio ``environ`` sean deterministas.
    if environ is None:
        lang = normalize_language(_system_locale())
        if lang:
            return lang
    return DEFAULT_LANGUAGE


def _system_locale() -> str | None:
    """Idioma configurado en el sistema operativo, si se puede averiguar."""
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
