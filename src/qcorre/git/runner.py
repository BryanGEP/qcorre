"""Ejecuta el git del sistema. Es el único módulo que lanza ``git``.

Se usa el git instalado (y no una librería) para poder enseñar al usuario el
comando exacto que se corre: lo que qcorre hace es lo mismo que podría teclear.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# Tiempo máximo de un comando de lectura, en segundos.
DEFAULT_TIMEOUT = 15.0


class GitError(Exception):
    """Git no pudo ejecutarse o respondió con error.

    ``reason`` permite a la interfaz elegir un mensaje amable:
    ``"not_installed"``, ``"timeout"`` o ``"failed"``.
    """

    def __init__(self, reason: str, detail: str = "", command: str = "") -> None:
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail
        self.command = command


@dataclass(frozen=True)
class GitResult:
    """Resultado de un comando de git."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def command(self) -> str:
        """El comando tal como lo teclearía el usuario."""
        return format_command(self.args)


def format_command(args: Sequence[str]) -> str:
    """``("commit", "-m", "mi mensaje")`` -> ``git commit -m "mi mensaje"``."""
    return " ".join(["git", *(_quote(arg) for arg in args)])


def _quote(arg: str) -> str:
    if arg and not any(ch in arg for ch in ' \t"\'&|<>;$`*?()'):
        return arg
    return '"' + arg.replace('"', '\\"') + '"'


class GitRunner:
    """Corre comandos de git dentro de un repositorio."""

    def __init__(
        self, repo: str | Path, *, git: str = "git", timeout: float = DEFAULT_TIMEOUT
    ) -> None:
        self.repo = Path(repo)
        self.git = git
        self.timeout = timeout

    def run(self, *args: str, check: bool = False) -> GitResult:
        """Ejecuta ``git <args>`` en el repo.

        Con ``check=True`` lanza ``GitError`` si git devuelve un código de
        error. Siempre lanza ``GitError`` si git no está instalado o tarda
        demasiado.
        """
        command = format_command(args)
        try:
            completed = subprocess.run(
                [self.git, "-c", "core.quotepath=false", *args],
                cwd=self.repo,
                env=_environment(),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                creationflags=_creation_flags(),
            )
        except FileNotFoundError as error:
            raise GitError("not_installed", str(error), command) from error
        except NotADirectoryError as error:
            raise GitError("failed", str(error), command) from error
        except subprocess.TimeoutExpired as error:
            raise GitError("timeout", f"{command} ({self.timeout:.0f}s)", command) from error
        except OSError as error:
            raise GitError("failed", str(error), command) from error

        result = GitResult(
            args=tuple(args),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        if check and not result.ok:
            raise GitError("failed", result.stderr.strip() or result.stdout.strip(), command)
        return result


def _environment() -> dict[str, str]:
    """Entorno para git: mensajes estables y sin preguntas interactivas."""
    env = dict(os.environ)
    env.update(
        {
            # Mensajes en inglés y con formato fijo, para poder interpretarlos.
            "LC_ALL": "C",
            "LANGUAGE": "en",
            # Si hace falta una contraseña, que falle en vez de quedarse esperando.
            "GIT_TERMINAL_PROMPT": "0",
            # Las lecturas en segundo plano no deben bloquear al git del usuario.
            "GIT_OPTIONAL_LOCKS": "0",
        }
    )
    return env


def _creation_flags() -> int:
    """En Windows evita que cada git abra una ventana de consola."""
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)
