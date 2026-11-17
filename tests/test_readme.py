"""Tests de la documentación: enlaces, imágenes y paridad entre idiomas.

Un README con una imagen rota o un enlace que no existe se ve mal justo donde
más gente mira; estos tests lo detectan antes de publicar.
"""

import re
from pathlib import Path

import pytest

from qcorre.ui.app import QcorreApp

ROOT = Path(__file__).resolve().parent.parent
READMES = ("README.md", "README.es.md")

# Tamaño máximo razonable de una imagen para que GitHub la cargue rápido.
MAX_IMAGE_BYTES = 5_000_000

_MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_HTML_TARGET = re.compile(r'(?:href|src)="([^"]+)"')


def targets(name: str) -> list[str]:
    """Destinos de todos los enlaces e imágenes de un README."""
    text = (ROOT / name).read_text(encoding="utf-8")
    return _MARKDOWN_LINK.findall(text) + _HTML_TARGET.findall(text)


def local_targets(name: str) -> list[str]:
    return [t for t in targets(name) if not t.startswith(("http://", "https://", "#", "mailto:"))]


def headings(name: str, level: str) -> list[str]:
    text = (ROOT / name).read_text(encoding="utf-8")
    return re.findall(rf"^{level} (.+)$", text, flags=re.MULTILINE)


@pytest.mark.parametrize("name", READMES)
def test_los_enlaces_e_imagenes_locales_existen(name):
    found = local_targets(name)
    assert found, "el README debería enlazar archivos del repo"
    for target in found:
        assert (ROOT / target).is_file(), f"{name} apunta a {target}, que no existe"


@pytest.mark.parametrize("name", READMES)
def test_los_enlaces_locales_son_relativos_y_respetan_mayusculas(name):
    for target in local_targets(name):
        assert not target.startswith(("/", "\\")) and "\\" not in target, target
        # GitHub distingue mayúsculas: el nombre debe coincidir exactamente.
        path = ROOT / target
        assert path.name in {p.name for p in path.parent.iterdir()}, target


@pytest.mark.parametrize("name", READMES)
def test_las_imagenes_pesan_poco_y_tienen_texto_alternativo(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    images = re.findall(r"<img\s[^>]*>", text)
    assert len(images) >= 5  # el GIF y las cuatro capturas (más los badges)
    for tag in images:
        assert re.search(r'alt="[^"]+"', tag), f"imagen sin texto alternativo: {tag}"
        source = re.search(r'src="([^"]+)"', tag).group(1)
        if not source.startswith("http"):
            assert (ROOT / source).stat().st_size < MAX_IMAGE_BYTES, source


def test_el_gif_y_las_capturas_existen_en_los_dos_idiomas():
    for suffix in ("", ".es"):
        gif = ROOT / "docs" / f"demo{suffix}.gif"
        assert gif.is_file() and gif.read_bytes()[:6] in (b"GIF87a", b"GIF89a")
        for shot in ("processes", "git-status", "commit", "history"):
            png = ROOT / "docs" / "screenshots" / f"{shot}{suffix}.png"
            assert png.is_file() and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", png


def test_cada_readme_usa_las_imagenes_de_su_idioma():
    english = [t for t in local_targets("README.md") if t.startswith("docs/")]
    spanish = [t for t in local_targets("README.es.md") if t.startswith("docs/")]
    assert english and all(".es." not in target for target in english)
    assert spanish and all(".es." in target for target in spanish)
    assert len(english) == len(spanish)


def test_los_dos_readme_tienen_la_misma_estructura():
    for level in ("##", "###"):
        assert len(headings("README.md", level)) == len(headings("README.es.md", level)), level
    assert len(targets("README.md")) == len(targets("README.es.md"))
    # Mismo número de filas en las tablas y de bloques de código.
    for marker in ("\n|", "```"):
        english = (ROOT / "README.md").read_text(encoding="utf-8").count(marker)
        spanish = (ROOT / "README.es.md").read_text(encoding="utf-8").count(marker)
        assert english == spanish, marker


def test_los_readme_se_enlazan_entre_si():
    assert "README.es.md" in local_targets("README.md")
    assert "README.md" in local_targets("README.es.md")


@pytest.mark.parametrize("name", READMES)
def test_la_tabla_de_atajos_cubre_todas_las_teclas_de_la_app(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    # Las teclas son lo que va entre acentos graves en la primera celda de
    # cada fila de la tabla: "| `k` / `K` | ... |".
    documented: set[str] = set()
    for row in re.findall(r"^\| (`[^|]+) \|", text, flags=re.MULTILINE):
        documented.update(re.findall(r"`([^`]+)`", row))
    for binding in QcorreApp.BINDINGS:
        key = "?" if binding.key == "question_mark" else binding.key
        assert key in documented, f"{name} no documenta la tecla {key!r}"


@pytest.mark.parametrize("name", READMES)
def test_las_opciones_de_la_linea_de_comandos_estan_documentadas(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    for option in ("--demo", "--lang", "--orphan-hours"):
        assert option in text


def test_el_paquete_usa_el_readme_principal():
    # La descripción para PyPI se arma a partir de README.md (ver test_release.py).
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    fragment = '[[tool.hatch.metadata.hooks.fancy-pypi-readme.fragments]]\npath = "README.md"'
    assert fragment in pyproject
