"""Detecta archivos que parecen contener secretos (claves, contraseñas, tokens).

Es una heurística por nombre de archivo: sirve para avisar antes de un commit,
no para garantizar nada. Un archivo sensible que llega a un commit queda en el
historial aunque después se borre, por eso conviene avisar *antes*.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from pathlib import PurePosixPath

from qcorre.git.parse import ChangeKind, FileChange

# Patrones sobre el nombre del archivo (en minúsculas).
SENSITIVE_PATTERNS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.env",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.jks",
    "*.keystore",
    "*.kdbx",
    "*.secret",
    "*.tfvars",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials",
    "credentials.*",
    "secrets.*",
    "secret.*",
    "client_secret*.json",
    "service-account*.json",
    "service_account*.json",
    "token.json",
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".htpasswd",
)

# Plantillas sin secretos reales: es normal (y deseable) versionarlas.
_SAFE_SUFFIXES: tuple[str, ...] = (".example", ".sample", ".template", ".dist", ".pub")


def is_sensitive(path: str) -> bool:
    """¿El nombre del archivo sugiere que guarda secretos?"""
    name = PurePosixPath(path.replace("\\", "/")).name.lower()
    if not name or name.endswith(_SAFE_SUFFIXES):
        return False
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in SENSITIVE_PATTERNS)


def sensitive_files(files: Iterable[FileChange]) -> list[FileChange]:
    """Los archivos de la lista que parecen sensibles y entrarían en un commit.

    Los borrados no cuentan: quitar un secreto del repo no lo expone.
    """
    return [f for f in files if f.kind is not ChangeKind.DELETED and is_sensitive(f.path)]
