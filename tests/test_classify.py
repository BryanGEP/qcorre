"""Tests de la clasificación y el nombre legible de los procesos."""

import pytest

from qcorre.models import ProcessInfo, ProcessKind
from qcorre.projects.classify import base_name, classify, describe


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("node", "node"),
        ("Node.EXE", "node"),
        ("python3.12", "python"),
        ("Python3.exe", "python"),
        ("php8.2", "php"),
        ("pm2", "pm2"),  # el número es parte del nombre
        ("redis-server", "redis-server"),
        ("mi-servidor2", "mi-servidor2"),
    ],
)
def test_base_name(name, expected):
    assert base_name(name) == expected


@pytest.mark.parametrize(
    ("name", "has_ports", "has_project", "expected"),
    [
        # Bases de datos: siempre.
        ("postgres", False, False, ProcessKind.DATABASE),
        ("redis-server.exe", True, False, ProcessKind.DATABASE),
        # Conocidos: con puerto o con proyecto.
        ("node", True, False, ProcessKind.SERVER),
        ("node", True, True, ProcessKind.SERVER),
        ("python3.11", False, True, ProcessKind.TOOL),
        ("python", False, False, None),
        # Desconocidos: solo con puerto y proyecto.
        ("mi-api", True, True, ProcessKind.SERVER),
        ("mi-api", True, False, None),
        ("mi-api", False, True, None),
        # Apps de escritorio: nunca.
        ("Code.exe", True, True, None),
        ("chrome", True, False, None),
    ],
)
def test_classify(name, has_ports, has_project, expected):
    assert classify(name, has_ports=has_ports, has_project=has_project) == expected


def test_conocido_sin_permiso_se_muestra_aunque_no_sepamos_nada():
    assert (
        classify("python.exe", has_ports=False, has_project=False, access_denied=True)
        is ProcessKind.TOOL
    )
    assert (
        classify("svchost.exe", has_ports=False, has_project=False, access_denied=True) is None
    )


@pytest.mark.parametrize(
    ("name", "cmdline", "expected"),
    [
        ("postgres", ("postgres", "-D", "/var/lib/pg"), "postgres"),
        ("python3.12", ("python3.12", "-m", "uvicorn", "app:app"), "uvicorn"),
        ("python", ("python", "-m", "http.server", "8000"), "http.server"),
        ("python", ("python", "manage.py", "runserver"), "python manage.py"),
        ("python", ("python", "-c", "print(1)"), "python -c"),
        ("python", ("python",), "python"),
        ("python", (), "python"),
        ("node", ("node", "server.js"), "node server.js"),
        ("node", ("node", "--inspect", "/p/node_modules/vite/bin/vite.js"), "vite"),
        (
            "node.exe",
            ("node.exe", r"C:\p\node_modules\@nestjs\cli\bin\nest.js", "start"),
            "@nestjs/cli",
        ),
        (
            "node",
            ("node", "/usr/lib/node_modules/npm/bin/npm-cli.js", "run", "dev"),
            "npm run dev",
        ),
        ("python", ("python", "/p/.venv/bin/uvicorn", "app:app"), "uvicorn"),
        (
            "python.exe",
            ("python.exe", r"C:\p\.venv\Scripts\gunicorn-script.py", "app"),
            "gunicorn",
        ),
        (
            "python.exe",
            ("python.exe", r"C:\p\.venv\Scripts\mi-cli.exe", "--demo"),
            "mi-cli",
        ),
        ("java", ("java", "-Xmx1g", "-jar", "/opt/app/servicio.jar"), "servicio.jar"),
        ("mi-api.exe", ("mi-api.exe", "--port", "8080"), "mi-api"),
    ],
)
def test_describe(name, cmdline, expected):
    assert describe(ProcessInfo(pid=1, name=name, cmdline=cmdline)) == expected
