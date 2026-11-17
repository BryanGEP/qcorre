"""Punto de entrada de la línea de comandos."""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from qcorre import __version__, i18n

# Los nombres de los temas (sin importar Textual: --help debe ser instantáneo).
THEMES = ("dark", "light")


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos."""
    parser = argparse.ArgumentParser(
        prog="qcorre",
        description="¿Qué corre en tu compu? / What's running on your machine?",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help=(
            "carpeta del proyecto que siempre se muestra (por defecto, la actual) / "
            "project folder that is always shown (default: current)"
        ),
    )
    parser.add_argument(
        "--lang",
        choices=i18n.LANGUAGES,
        help="idioma de la interfaz / interface language",
    )
    parser.add_argument(
        "--theme",
        choices=THEMES,
        help=(
            "tema de colores (por defecto, el de QCORRE_THEME u oscuro) / "
            "color theme (default: QCORRE_THEME or dark)"
        ),
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help=(
            "abre la interfaz con procesos y repos simulados; nada real se toca / "
            "opens the interface with simulated processes and repos; nothing real is touched"
        ),
    )
    parser.add_argument(
        "--orphan-hours",
        type=_positive_hours,
        default=24.0,
        metavar="H",
        help=(
            "horas tras las que un proceso se marca como huérfano (por defecto 24) / "
            "hours after which a process is flagged as an orphan (default 24)"
        ),
    )
    parser.add_argument("--version", action="version", version=f"qcorre {__version__}")
    return parser


def _positive_hours(value: str) -> float:
    """Valida ``--orphan-hours``: un número mayor que cero."""
    try:
        hours = float(value)
    except ValueError:
        hours = 0.0
    if hours <= 0:
        raise argparse.ArgumentTypeError(
            "debe ser un número mayor que cero / must be a number greater than zero"
        )
    return hours


def choose_theme(requested: str | None, environ: Mapping[str, str] | None = None) -> str:
    """El tema a usar: el pedido con ``--theme``, el de ``QCORRE_THEME`` u oscuro."""
    if requested:
        return requested
    env = os.environ if environ is None else environ
    from_env = env.get("QCORRE_THEME", "").strip().lower()
    return from_env if from_env in THEMES else "dark"


def build_app(args: argparse.Namespace):
    """Crea la aplicación según los argumentos (real o en modo demo)."""
    # Se importa aquí para que `--help` y `--version` no carguen Textual.
    from qcorre.ui.app import QcorreApp

    theme_name = choose_theme(args.theme)
    if args.demo:
        from qcorre.demo import DemoWorld

        return QcorreApp(**DemoWorld().as_kwargs(), theme_name=theme_name)

    from qcorre.scanner import Scanner

    scanner = Scanner(
        pinned=[Path(args.path).resolve()],
        long_running_seconds=args.orphan_hours * 3600,
    )
    return QcorreApp(scanner=scanner, theme_name=theme_name)


def main(argv: Sequence[str] | None = None) -> int:
    """Lee los argumentos, fija el idioma y abre la interfaz."""
    args = build_parser().parse_args(argv)
    i18n.set_language(args.lang or i18n.detect_language())
    build_app(args).run()
    return 0
