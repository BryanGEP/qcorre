"""Tests de la preparación de versiones: comprobaciones previas y descripción para PyPI."""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

import qcorre

ROOT = Path(__file__).resolve().parent.parent

# scripts/ no es un paquete: se carga el módulo desde su ruta.
_spec = importlib.util.spec_from_file_location("release_check", ROOT / "scripts" / "release_check.py")
release_check = importlib.util.module_from_spec(_spec)
sys.modules["release_check"] = release_check
_spec.loader.exec_module(release_check)

ReleaseError = release_check.ReleaseError

CHANGELOG = """# Cambios

Texto de introducción.

## [0.2.0] - sin publicar

- algo nuevo

## [0.1.0] - 2026-11-17

Primera versión.

### Procesos

- Panel de proyectos.

[0.2.0]: https://github.com/BryanGEP/qcorre/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/BryanGEP/qcorre/releases/tag/v0.1.0
"""


def make_dist(tmp_path: Path, *names: str) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir()
    for name in names:
        (dist / name).write_bytes(b"")
    return dist


# ── Tag ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("tag", "version"), [("v0.1.0", "0.1.0"), ("v1.12.3", "1.12.3"), ("v0.2.0rc1", "0.2.0rc1")]
)
def test_version_del_tag(tag, version):
    assert release_check.version_from_tag(tag) == version


@pytest.mark.parametrize("tag", ["0.1.0", "v0.1", "version-0.1.0", "v0.1.0-beta", ""])
def test_tags_invalidos(tag):
    with pytest.raises(ReleaseError):
        release_check.version_from_tag(tag)


# ── Paquete construido ──────────────────────────────────────────


def test_dist_que_coincide_con_el_tag(tmp_path):
    dist = make_dist(tmp_path, "qcorre-0.1.0-py3-none-any.whl", "qcorre-0.1.0.tar.gz")
    release_check.check_dist(dist, "0.1.0")  # no lanza


def test_dist_con_otra_version_se_rechaza(tmp_path):
    dist = make_dist(tmp_path, "qcorre-0.1.1-py3-none-any.whl", "qcorre-0.1.1.tar.gz")
    with pytest.raises(ReleaseError, match="El tag dice 0.1.0"):
        release_check.check_dist(dist, "0.1.0")


def test_dist_mezclado_se_rechaza(tmp_path):
    dist = make_dist(tmp_path, "qcorre-0.1.0-py3-none-any.whl", "qcorre-0.0.9.tar.gz")
    with pytest.raises(ReleaseError, match="qcorre-0.0.9.tar.gz es 0.0.9"):
        release_check.check_dist(dist, "0.1.0")


@pytest.mark.parametrize(
    "names",
    [(), ("qcorre-0.1.0.tar.gz",), ("qcorre-0.1.0-py3-none-any.whl",), ("otra-0.1.0.tar.gz",)],
)
def test_dist_incompleto_se_rechaza(tmp_path, names):
    with pytest.raises(ReleaseError):
        release_check.check_dist(make_dist(tmp_path, *names), "0.1.0")


# ── Notas del CHANGELOG ─────────────────────────────────────────


def test_notas_de_una_version():
    notes = release_check.release_notes(CHANGELOG, "0.1.0")
    assert notes.startswith("Primera versión.")
    assert "### Procesos" in notes and "- Panel de proyectos." in notes
    assert "algo nuevo" not in notes  # no se cuela la versión siguiente
    assert "releases/tag" not in notes  # ni las definiciones de enlaces
    assert notes.endswith("\n")


def test_version_sin_fecha_no_se_publica():
    with pytest.raises(ReleaseError, match="no tiene fecha"):
        release_check.release_notes(CHANGELOG, "0.2.0")


def test_version_sin_entrada_no_se_publica():
    with pytest.raises(ReleaseError, match="no tiene una entrada"):
        release_check.release_notes(CHANGELOG, "9.9.9")


def test_entrada_vacia_no_se_publica():
    with pytest.raises(ReleaseError, match="está vacía"):
        release_check.release_notes("## [0.3.0] - 2027-01-01\n\n## [0.2.0] - 2026-12-01\n- x\n", "0.3.0")


# ── El script completo ──────────────────────────────────────────


def test_main_escribe_las_notas_si_todo_cuadra(tmp_path, capsys):
    dist = make_wheel(tmp_path, "# qcorre\n")
    (dist / "qcorre-0.1.0.tar.gz").write_bytes(b"")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")
    notes = tmp_path / "notas.md"
    code = release_check.main(
        ["--tag", "v0.1.0", "--dist", str(dist), "--changelog", str(changelog), "--notes", str(notes)]
    )
    assert code == 0
    assert notes.read_text(encoding="utf-8").startswith("Primera versión.")
    assert "Todo listo para publicar qcorre 0.1.0" in capsys.readouterr().out


def test_main_falla_y_explica_si_algo_no_cuadra(tmp_path, capsys):
    dist = make_dist(tmp_path, "qcorre-0.1.0-py3-none-any.whl", "qcorre-0.1.0.tar.gz")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")
    notes = tmp_path / "notas.md"
    code = release_check.main(
        ["--tag", "v0.2.0", "--dist", str(dist), "--changelog", str(changelog), "--notes", str(notes)]
    )
    assert code == 1
    assert "::error::" in capsys.readouterr().err
    assert not notes.exists()


# ── El repo real, listo para la versión actual ──────────────────


def test_el_changelog_real_tiene_la_entrada_de_la_version_actual():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = release_check.release_notes(changelog, qcorre.__version__)
    assert len(notes.splitlines()) > 5


def test_la_descripcion_para_pypi_no_deja_rutas_relativas():
    """Aplica las sustituciones del pyproject al README, como hace el plugin al construir."""
    tomllib = pytest.importorskip("tomllib")  # Python 3.11+
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    hook = config["tool"]["hatch"]["metadata"]["hooks"]["fancy-pypi-readme"]
    assert [fragment["path"] for fragment in hook["fragments"]] == ["README.md"]
    assert "readme" in config["project"]["dynamic"]

    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for sub in hook["substitutions"]:
        text = re.sub(sub["pattern"], sub["replacement"], text)
    text = text.replace("$HFPR_VERSION", qcorre.__version__)

    targets = re.findall(r'(?:src|href)="([^"]+)"', text) + re.findall(r"\]\(([^)\s]+)\)", text)
    assert targets
    relative = [t for t in targets if not t.startswith(("https://", "http://", "#"))]
    assert relative == [], relative
    tag = f"v{qcorre.__version__}"
    # Las imágenes del repo apuntan al archivo crudo del tag de esta versión.
    images = [t for t in targets if "/docs/" in t]
    assert len(images) == 5
    assert all(t.startswith(f"https://raw.githubusercontent.com/BryanGEP/qcorre/{tag}/docs/") for t in images)
    # Y cada una existe en el repo.
    for image in images:
        assert (ROOT / image.split(f"/{tag}/", 1)[1]).is_file(), image


def test_el_workflow_de_publicacion_usa_trusted_publishing():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert re.search(r"tags:\s*\[\"v\*\"\]", workflow)
    assert "environment:\n      name: pypi" in workflow
    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    # Sin tokens guardados: Trusted Publishing no los necesita.
    assert "password:" not in workflow and "PYPI_API_TOKEN" not in workflow
    # El orden de los trabajos impide publicar sin pasar las comprobaciones.
    assert "uses: ./.github/workflows/ci.yml" in workflow
    assert re.search(r"publish:\n(?:.*\n)*?    needs: build", workflow)
    assert "scripts/release_check.py" in workflow and "twine check --strict" in workflow
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "workflow_call:" in ci


# ── Descripción para PyPI ───────────────────────────────────────


def make_wheel(tmp_path: Path, body: str, content_type: str = "text/markdown") -> Path:
    import zipfile

    dist = tmp_path / "dist"
    dist.mkdir(exist_ok=True)
    metadata = (
        "Metadata-Version: 2.4\nName: qcorre\nVersion: 0.1.0\n"
        f"Description-Content-Type: {content_type}\n\n{body}"
    )
    with zipfile.ZipFile(dist / "qcorre-0.1.0-py3-none-any.whl", "w") as archive:
        archive.writestr("qcorre-0.1.0.dist-info/METADATA", metadata)
    return dist


def test_descripcion_con_urls_absolutas_es_valida(tmp_path):
    body = '# qcorre\n\n<img src="https://raw.githubusercontent.com/x/y/v0.1.0/docs/a.gif" alt="a">\n\n[MIT](https://github.com/x/y/blob/v0.1.0/LICENSE)\n'
    release_check.check_description(make_wheel(tmp_path, body))  # no lanza


@pytest.mark.parametrize(
    "body",
    [
        '<img src="docs/demo.gif" alt="demo">',
        '<a href="README.es.md">Español</a>',
        "Ver [la licencia](LICENSE).",
    ],
)
def test_descripcion_con_rutas_relativas_se_rechaza(tmp_path, body):
    with pytest.raises(ReleaseError, match="rutas relativas"):
        release_check.check_description(make_wheel(tmp_path, body))


def test_los_enlaces_a_anclas_de_la_misma_pagina_se_permiten(tmp_path):
    release_check.check_description(make_wheel(tmp_path, "[Uso](#usage)\n"))


def test_descripcion_que_no_es_markdown_se_rechaza(tmp_path):
    with pytest.raises(ReleaseError, match="Markdown"):
        release_check.check_description(make_wheel(tmp_path, "hola", content_type="text/x-rst"))


def test_renderizar_la_descripcion(tmp_path):
    pytest.importorskip("readme_renderer.markdown")
    dist = make_wheel(tmp_path, "# qcorre\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    try:
        release_check.check_description(dist, render=True)
    except ReleaseError as error:
        # Sin el extra [md] no hay con qué renderizar: el script lo dice claro.
        assert "readme_renderer" in str(error) or "renderizar" in str(error)
