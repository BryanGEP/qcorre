"""Decide si un proceso es "de desarrollo", de qué tipo y cómo llamarlo.

Todo se basa en el nombre del proceso, en si escucha puertos y en si pertenece
a un proyecto. Son funciones puras.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath

from qcorre.models import ProcessInfo, ProcessKind

# Bases de datos, cachés y brokers: siempre interesan, tengan proyecto o no.
DATABASES: frozenset[str] = frozenset(
    {
        "postgres", "postmaster", "mysqld", "mariadbd", "mongod", "mongos",
        "redis-server", "valkey-server", "memcached", "sqlservr", "clickhouse",
        "clickhouse-server", "cockroach", "etcd", "influxd", "minio", "surreal",
        "qdrant", "meilisearch", "nats-server", "mosquitto", "pocketbase",
        "rabbitmq-server", "consul",
    }
)  # fmt: skip

# Intérpretes: el nombre útil está en sus argumentos (`python -m uvicorn`).
INTERPRETERS: frozenset[str] = frozenset(
    {"python", "pythonw", "node", "nodejs", "ruby", "php", "java", "deno", "bun", "dotnet"}
)

# Herramientas de desarrollo conocidas por nombre propio.
DEV_TOOLS: frozenset[str] = frozenset(
    {
        "npm", "npx", "pnpm", "yarn", "uv", "poetry", "go", "cargo", "gradle", "mvn",
        "uvicorn", "gunicorn", "hypercorn", "daphne", "flask", "django-admin",
        "streamlit", "jupyter", "jupyter-lab", "jupyter-notebook", "celery",
        "rails", "puma", "unicorn", "php-fpm", "vite", "next", "nuxt", "webpack",
        "esbuild", "tsc", "tsx", "ts-node", "nodemon", "pm2", "air", "hugo",
        "jekyll", "nginx", "caddy", "httpd", "apache2", "ngrok", "docker-proxy",
        "com.docker.backend",
    }
)  # fmt: skip

# Aplicaciones de escritorio que abren puertos pero no son "tu servidor".
IGNORED: frozenset[str] = frozenset(
    {
        "code", "code helper", "code - insiders", "cursor", "electron", "chrome",
        "msedge", "firefox", "brave", "idea64", "pycharm64", "webstorm64", "slack",
        "discord", "spotify", "explorer", "windowsterminal", "claude", "git",
    }
)  # fmt: skip

KNOWN: frozenset[str] = DATABASES | INTERPRETERS | DEV_TOOLS

# Gestores de paquetes: su nombre se completa con el subcomando (`npm run dev`).
_PACKAGE_MANAGERS = frozenset({"npm", "npx", "pnpm", "yarn"})
_VERSION_SUFFIX = re.compile(r"[\d.]+$")


def base_name(name: str) -> str:
    """Nombre normalizado de un proceso: ``Python3.12.exe`` -> ``python``.

    El sufijo de versión solo se quita cuando el resultado es un nombre
    conocido, para no convertir ``pm2`` en ``pm``.
    """
    base = name.strip().lower()
    if base.endswith(".exe"):
        base = base[:-4]
    if base in KNOWN:
        return base
    stripped = _VERSION_SUFFIX.sub("", base)
    return stripped if stripped in KNOWN else base


def classify(
    name: str,
    *,
    has_ports: bool,
    has_project: bool,
    access_denied: bool = False,
) -> ProcessKind | None:
    """Tipo de proceso de desarrollo, o ``None`` si no interesa mostrarlo.

    - Bases de datos conocidas: siempre.
    - Intérpretes y herramientas conocidas: si escuchan un puerto o están
      dentro de un proyecto (un ``python`` suelto sin puertos es ruido). Si el
      sistema negó el acceso no se puede saber, así que se muestran.
    - Nombres desconocidos: solo si escuchan un puerto *y* están dentro de un
      proyecto (por ejemplo, un binario compilado de tu repo).
    """
    base = base_name(name)
    if base in IGNORED:
        return None
    if base in DATABASES:
        return ProcessKind.DATABASE
    if base in KNOWN:
        if has_ports:
            return ProcessKind.SERVER
        if has_project or access_denied:
            return ProcessKind.TOOL
        return None
    if has_ports and has_project:
        return ProcessKind.SERVER
    return None


def describe(info: ProcessInfo) -> str:
    """Nombre legible del proceso.

    Para intérpretes se mira qué están ejecutando::

        python -m uvicorn app:app          -> uvicorn
        node node_modules/vite/bin/vite.js -> vite
        node .../npm-cli.js run dev        -> npm run dev
        node server.js                     -> node server.js
    """
    base = base_name(info.name)
    if base not in INTERPRETERS:
        return base
    args = list(info.cmdline[1:])
    while args:
        arg = args.pop(0)
        if arg == "-m" and args:
            return args[0]
        if arg == "-jar" and args:
            return _file_name(args[0])
        if arg in ("-c", "-e", "--eval"):
            return f"{base} {arg}"
        if arg.startswith("-"):
            continue
        return _describe_script(base, arg, args)
    return base


def _describe_script(base: str, script: str, rest: list[str]) -> str:
    parts = _parts(script)
    file_name = parts[-1] if parts else script
    package = _node_package(parts)
    if package:
        if package in _PACKAGE_MANAGERS:
            extra = [a for a in rest if not a.startswith("-")][:2]
            return " ".join([package, *extra])
        return package
    # Scripts de consola de un entorno virtual (.venv/bin/uvicorn,
    # .venv\Scripts\uvicorn.exe): su nombre ya es el del programa.
    if len(parts) >= 2 and parts[-2].lower() in ("bin", "scripts"):
        stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        return stem.lower().removesuffix("-script")
    return f"{base} {file_name}"


def _node_package(parts: tuple[str, ...]) -> str | None:
    """Paquete npm al que pertenece una ruta dentro de ``node_modules``."""
    if "node_modules" not in parts:
        return None
    index = len(parts) - 1 - parts[::-1].index("node_modules")
    after = parts[index + 1 :]
    if not after:
        return None
    if after[0].startswith("@") and len(after) > 1:
        return f"{after[0]}/{after[1]}"
    return after[0]


def _parts(path: str) -> tuple[str, ...]:
    """Componentes de una ruta, sea de Windows o de Unix."""
    pure = PureWindowsPath(path) if "\\" in path else PurePosixPath(path)
    return pure.parts


def _file_name(path: str) -> str:
    parts = _parts(path)
    return parts[-1] if parts else path
