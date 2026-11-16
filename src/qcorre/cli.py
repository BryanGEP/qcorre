"""Punto de entrada de la línea de comandos."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from qcorre import __version__, i18n


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos."""
    parser = argparse.ArgumentParser(
        prog="qcorre",
        description="¿Qué corre en tu compu? / What's running on your machine?",
    )
    parser.add_argument(
        "--lang",
        choices=i18n.LANGUAGES,
        help="idioma de la interfaz / interface language",
    )
    parser.add_argument("--version", action="version", version=f"qcorre {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Lee los argumentos, fija el idioma y abre la interfaz."""
    args = build_parser().parse_args(argv)
    i18n.set_language(args.lang or i18n.detect_language())

    # Se importa aquí para que `--help` y `--version` no carguen Textual.
    from qcorre.ui.app import QcorreApp

    QcorreApp().run()
    return 0
