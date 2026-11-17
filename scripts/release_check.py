"""Comprobaciones previas a publicar una versión de qcorre.

Lo usa el workflow ``release.yml`` antes de subir nada a PyPI::

    python scripts/release_check.py --tag v0.1.0 --dist dist --notes release-notes.md

Verifica que:

1. el tag tenga la forma ``vX.Y.Z`` y coincida con la versión de *todos* los
   archivos construidos en ``dist/`` (wheel y paquete fuente);
2. el CHANGELOG tenga una entrada para esa versión, con fecha, y no esté vacía;
3. la descripción que verá PyPI sea Markdown sin rutas relativas (con
   ``--render``, además, que ``readme_renderer`` la dibuje sin avisos).

Si todo cuadra, escribe en ``--notes`` las notas de esa versión (tal cual
aparecen en el CHANGELOG) para usarlas en el GitHub Release. Si algo falla,
explica qué y termina con código 1: el workflow se detiene antes de publicar.
"""

from __future__ import annotations

import argparse
import re
import sys
import warnings
import zipfile
from pathlib import Path

# Archivos de distribución: qcorre-0.1.0-py3-none-any.whl, qcorre-0.1.0.tar.gz
_DIST_NAME = re.compile(r"^qcorre-(?P<version>[^-]+?)(?:-.+\.whl|\.tar\.gz)$")
_TAG = re.compile(r"^v(?P<version>\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?)$")
_SECTION = re.compile(r"^## \[(?P<version>[^\]]+)\](?P<rest>.*)$", re.MULTILINE)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_HTML_TARGET = re.compile(r'(?:src|href)="([^"]+)"')
_MARKDOWN_TARGET = re.compile(r"\]\(([^)\s]+)\)")


class ReleaseError(Exception):
    """Algo no cuadra: no se debe publicar."""


def version_from_tag(tag: str) -> str:
    """``v0.1.0`` -> ``0.1.0``."""
    match = _TAG.match(tag.strip())
    if not match:
        raise ReleaseError(f"El tag {tag!r} no tiene la forma vX.Y.Z (por ejemplo v0.1.0).")
    return match.group("version")


def dist_versions(dist: Path) -> dict[str, str]:
    """Versión de cada archivo construido en ``dist`` (nombre -> versión)."""
    found = {}
    for path in sorted(dist.iterdir()) if dist.is_dir() else []:
        match = _DIST_NAME.match(path.name)
        if match:
            found[path.name] = match.group("version")
    return found


def check_dist(dist: Path, version: str) -> None:
    files = dist_versions(dist)
    if not any(name.endswith(".whl") for name in files):
        raise ReleaseError(f"No hay ningún wheel de qcorre en {dist}.")
    if not any(name.endswith(".tar.gz") for name in files):
        raise ReleaseError(f"No hay ningún paquete fuente (.tar.gz) de qcorre en {dist}.")
    wrong = {name: found for name, found in files.items() if found != version}
    if wrong:
        detail = ", ".join(f"{name} es {found}" for name, found in wrong.items())
        raise ReleaseError(
            f"El tag dice {version}, pero el paquete construido no: {detail}. "
            "Actualiza __version__ en src/qcorre/__init__.py o corrige el tag."
        )


def long_description(dist: Path) -> tuple[str, str]:
    """Descripción larga del wheel (lo que PyPI muestra) y su tipo de contenido."""
    wheels = sorted(dist.glob("qcorre-*.whl"))
    if not wheels:
        raise ReleaseError(f"No hay ningún wheel de qcorre en {dist}.")
    with zipfile.ZipFile(wheels[0]) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        metadata = archive.read(name).decode("utf-8")
    headers, _, body = metadata.partition("\n\n")
    content_type = next(
        (line.split(":", 1)[1].strip() for line in headers.splitlines()
         if line.lower().startswith("description-content-type:")),
        "",
    )
    return body, content_type


def check_description(dist: Path, *, render: bool = False) -> None:
    """La descripción para PyPI debe ser Markdown, sin rutas relativas y renderizable.

    En PyPI una ruta relativa (``docs/demo.gif``, ``LICENSE``) no lleva a
    ningún lado: la imagen se ve rota. Con ``render`` se dibuja además con
    ``readme_renderer``, el mismo que usa PyPI, y cualquier aviso es un fallo.
    """
    body, content_type = long_description(dist)
    if not content_type.startswith("text/markdown"):
        raise ReleaseError(f"La descripción no se declara como Markdown ({content_type!r}).")
    if not body.strip():
        raise ReleaseError("La descripción para PyPI está vacía.")
    targets = _HTML_TARGET.findall(body) + _MARKDOWN_TARGET.findall(body)
    relative = sorted({t for t in targets if not t.startswith(("https://", "http://", "#"))})
    if relative:
        raise ReleaseError(
            "La descripción para PyPI tiene rutas relativas, que ahí no funcionan: "
            + ", ".join(relative)
        )
    if render:
        try:
            from readme_renderer.markdown import render as render_markdown
        except ImportError as error:
            hint = "Falta readme_renderer: pip install 'readme-renderer[md]'"
            raise ReleaseError(hint) from error
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # p. ej. "Markdown renderers are not available"
            try:
                html = render_markdown(body, variant="GFM")
            except Warning as warning:
                raise ReleaseError(f"No se pudo renderizar la descripción: {warning}") from None
        if not html:
            raise ReleaseError("readme_renderer no pudo renderizar la descripción.")


def release_notes(changelog: str, version: str) -> str:
    """Las notas de ``version`` en el CHANGELOG, sin su título."""
    sections = list(_SECTION.finditer(changelog))
    for index, section in enumerate(sections):
        if section.group("version") != version:
            continue
        if not _DATE.search(section.group("rest")):
            raise ReleaseError(
                f"La entrada {version} del CHANGELOG no tiene fecha "
                f"(dice {section.group(0).strip()!r}). Ponle la fecha de publicación."
            )
        end = sections[index + 1].start() if index + 1 < len(sections) else len(changelog)
        body = changelog[section.end() : end]
        # Las definiciones de enlaces del final ("[0.1.0]: https://...") no son notas.
        body = re.sub(r"^\[[^\]]+\]: \S+\s*$", "", body, flags=re.MULTILINE).strip()
        if not body:
            raise ReleaseError(f"La entrada {version} del CHANGELOG está vacía.")
        return body + "\n"
    raise ReleaseError(f"El CHANGELOG no tiene una entrada para la versión {version}.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Comprueba que se puede publicar una versión.")
    parser.add_argument("--tag", required=True, help="tag de git, p. ej. v0.1.0")
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    parser.add_argument("--notes", type=Path, help="dónde escribir las notas de la versión")
    parser.add_argument(
        "--render",
        action="store_true",
        help="renderizar la descripción con readme_renderer, como hace PyPI",
    )
    args = parser.parse_args(argv)

    try:
        version = version_from_tag(args.tag)
        check_dist(args.dist, version)
        check_description(args.dist, render=args.render)
        notes = release_notes(args.changelog.read_text(encoding="utf-8"), version)
    except (ReleaseError, OSError) as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1

    if args.notes:
        args.notes.write_text(notes, encoding="utf-8")
    print(f"Todo listo para publicar qcorre {version}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
