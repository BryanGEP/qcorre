"""Tests de las traducciones."""

import sys

import pytest

from qcorre import i18n
from qcorre.i18n import en, es


@pytest.fixture(autouse=True)
def restore_language():
    """Deja el idioma como estaba para no contaminar otros tests."""
    previous = i18n.get_language()
    yield
    i18n.set_language(previous)


def test_los_catalogos_tienen_las_mismas_claves():
    assert set(es.MESSAGES) == set(en.MESSAGES)


def test_los_plurales_tienen_las_dos_formas():
    for catalog in (es.MESSAGES, en.MESSAGES):
        for key, entry in catalog.items():
            if not isinstance(entry, str):
                assert set(entry) == {"one", "other"}, key


def test_traduce_segun_el_idioma_activo():
    i18n.set_language("es")
    assert i18n.t("panel.projects") == "Proyectos"
    i18n.set_language("en")
    assert i18n.t("panel.projects") == "Projects"


def test_clave_inexistente_devuelve_la_clave():
    assert i18n.t("no.existe") == "no.existe"


def test_plural_y_parametros(monkeypatch):
    monkeypatch.setitem(
        i18n._CATALOGS, "es", {"x": {"one": "{n} proceso", "other": "{n} procesos"}}
    )
    i18n.set_language("es")
    assert i18n.t("x", n=1) == "1 proceso"
    assert i18n.t("x", n=3) == "3 procesos"
    assert i18n.t("x", n=0) == "0 procesos"


def test_idioma_no_soportado():
    with pytest.raises(ValueError):
        i18n.set_language("fr")


def test_next_language_alterna():
    i18n.set_language("es")
    assert i18n.next_language() == "en"
    i18n.set_language("en")
    assert i18n.next_language() == "es"


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("es_MX.UTF-8", "es"),
        ("es-419", "es"),
        ("Spanish_Mexico", "es"),
        ("en_US", "en"),
        ("English_United States", "en"),
        ("fr_FR", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_language(code, expected):
    assert i18n.normalize_language(code) == expected


def test_detect_language_respeta_la_prioridad():
    assert i18n.detect_language({"QCORRE_LANG": "es", "LANG": "en_US"}) == "es"
    assert i18n.detect_language({"LANG": "es_ES.UTF-8"}) == "es"
    assert i18n.detect_language({"LANG": "fr_FR"}) == "en"
    assert i18n.detect_language({}) == "en"


def test_en_windows_gana_el_idioma_de_la_interfaz_sobre_LANG():
    # Git Bash y VS Code fijan LANG=en_US.UTF-8 aunque Windows esté en español.
    env = {"LANG": "en_US.UTF-8"}
    assert (
        i18n.detect_language(env, platform="win32", system_locale=lambda: "es_ES") == "es"
    )
    assert (
        i18n.detect_language(env, platform="win32", system_locale=lambda: "en_US") == "en"
    )


def test_en_windows_QCORRE_LANG_sigue_mandando():
    env = {"QCORRE_LANG": "en", "LANG": "es_MX.UTF-8"}
    assert i18n.detect_language(env, platform="win32", system_locale=lambda: "es_ES") == "en"


def test_en_windows_sin_idioma_soportado_cae_a_LANG_y_luego_a_ingles():
    assert (
        i18n.detect_language(
            {"LANG": "es_MX.UTF-8"}, platform="win32", system_locale=lambda: "fr_FR"
        )
        == "es"
    )
    assert i18n.detect_language({}, platform="win32", system_locale=lambda: None) == "en"


def test_en_unix_LANG_gana_al_locale_del_sistema():
    env = {"LANG": "en_US.UTF-8"}
    assert i18n.detect_language(env, platform="linux", system_locale=lambda: "es_ES") == "en"
    assert i18n.detect_language({}, platform="darwin", system_locale=lambda: "es_MX") == "es"


@pytest.mark.skipif(sys.platform != "win32", reason="consulta la API de Windows")
def test_system_locale_en_windows_devuelve_un_codigo_de_idioma():
    code = i18n._system_locale()
    assert code is not None
    assert "_" in code  # por ejemplo es_ES o en_US
