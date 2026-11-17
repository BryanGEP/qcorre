"""Tests de las reglas de diseño: contraste, glifos, columnas, pie contextual y estilos.

Son las decisiones de docs/design/README.md convertidas en comprobaciones,
para que un cambio futuro no las deshaga sin querer.
"""

from pathlib import Path

import pytest
from rich.color import Color
from rich.style import Style
from test_app import make_app, sample_status, settle, tree_lines

from qcorre import i18n
from qcorre.demo import DemoWorld
from qcorre.git.parse import FileChange, RepoStatus
from qcorre.git.runner import GitError
from qcorre.models import Snapshot
from qcorre.ui import theme
from qcorre.ui.app import QcorreApp
from qcorre.ui.git_panel import GitPanel
from qcorre.ui.git_view import file_list, status_body
from qcorre.ui.projects_panel import ProjectsPanel
from qcorre.ui.styles import Key, heading, keys_line
from qcorre.ui.widgets import HintBar

OID = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


# ── Contraste (WCAG) ────────────────────────────────────────────


def luminance(color: str) -> float:
    channels = [int(color.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("background", [theme.BACKGROUND, theme.SURFACE, theme.PANEL])
@pytest.mark.parametrize(
    "color",
    [theme.FOREGROUND, theme.MUTED, theme.ACCENT, theme.SECONDARY,
     theme.SUCCESS, theme.WARNING, theme.ERROR],
)  # fmt: skip
def test_todo_texto_cumple_el_contraste_minimo_aa(color, background):
    assert contrast(color, background) >= 4.5, (color, background)


# ── Glifos ──────────────────────────────────────────────────────

# Se dibujan como emoji (o con una fuente de reserva) en algunas terminales y
# desalinean las columnas.
FORBIDDEN = "⚠⎇⏎⇥✓✔✗✖❌⭐"


async def test_ninguna_vista_usa_glifos_problematicos():
    world = DemoWorld(delay=0, home=Path("/home/ana"))
    app = QcorreApp(**world.as_kwargs(), refresh_seconds=None)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        screens = [app.export_screenshot()]
        for keys in (["enter"], ["k"], ["c"], ["b"], ["u"], ["question_mark"]):
            await pilot.press("down", "down", "down")
            await pilot.press(*keys)
            await pilot.pause(0.1)
            screens.append(app.export_screenshot())
            await pilot.press("escape")
            await settle(app, pilot)
        await pilot.press("h")
        await settle(app, pilot)
        screens.append(app.export_screenshot())
    for svg in screens:
        assert not set(FORBIDDEN) & set(svg)


def test_los_secretos_se_marcan_con_texto():
    files = (FileChange(".env", untracked=True), FileChange("app.py", worktree="M"))
    plain = file_list(files).plain
    assert ".env  ¿secreto?" in plain
    assert "app.py  ¿secreto?" not in plain


# ── Panel de proyectos: columnas y notas ────────────────────────


@pytest.mark.parametrize("width", [90, 110, 160])
async def test_las_filas_ocupan_todo_el_ancho_y_alinean_a_la_derecha(width):
    app = make_app()
    async with app.run_test(size=(width, 30)) as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectsPanel).tree
        lines = tree_lines(app)
        processes = [line for line in lines if line.startswith(("● ", "○ "))]
        headers = [line for line in lines if not line.startswith(("● ", "○ ", "╰"))]
        notes = [line for line in lines if line.startswith("╰")]
        # Todas las líneas de un mismo nivel miden lo mismo: llegan al borde.
        assert len({len(line) for line in processes + notes}) == 1
        assert len({len(line) for line in headers}) == 1
        # Sangría + línea = ancho del panel menos la columna de la barra de desplazamiento.
        assert tree.guide_depth + len(processes[0]) == tree.size.width - 1
        # El tiempo de cada proceso termina en la misma columna.
        assert {line.rstrip()[-1] for line in processes} <= set("0123456789mhd")
        ports_end = {line.index(":") + len(line.split(":")[1].split()[0]) + 1 for line in processes}
        assert len(ports_end) == 1  # los puertos también quedan alineados


async def test_una_fila_sin_puerto_no_pinta_fondo_en_esa_columna():
    world = DemoWorld(delay=0, home=Path("/home/ana"))
    app = QcorreApp(**world.as_kwargs(), refresh_seconds=None)
    async with app.run_test(size=(110, 34)) as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectsPanel).tree
        labels = [tree.get_node_at_line(i).label for i in range(tree.last_line + 1)]
        celery = next(label for label in labels if "celery" in label.plain)
        assert ":" not in celery.plain  # no tiene puerto
        for label in labels:
            for span in label.spans:
                assert " on " not in str(span.style), (label.plain, span.style)


async def test_las_notas_van_en_gris_tenue_y_el_aviso_en_el_punto():
    app = make_app()
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectsPanel).tree
        labels = [tree.get_node_at_line(i).label for i in range(tree.last_line + 1)]
        for label in labels:
            if label.plain.startswith("╰"):
                assert {str(span.style) for span in label.spans} | {str(label.style)} <= {
                    theme.MUTED,
                    "",
                }
        flagged = next(label for label in labels if "node server.js" in label.plain)
        assert str(flagged.spans[0].style) == theme.WARNING  # el punto
        healthy = next(label for label in labels if "postgres" in label.plain)
        assert str(healthy.spans[0].style) == theme.SUCCESS


async def test_los_proyectos_se_distinguen_de_los_procesos():
    app = make_app()
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        header = app.query_one(ProjectsPanel).tree.get_node_at_line(0).label
        assert header.plain.startswith("tienda-api")
        assert str(header.spans[0].style) == f"bold {theme.ACCENT}"


@pytest.mark.parametrize("lang", ["es", "en"])
async def test_las_notas_caben_en_el_panel_a_100_columnas(lang):
    i18n.set_language(lang)
    app = make_app()
    async with app.run_test(size=(100, 30)) as pilot:
        await settle(app, pilot)
        for line in tree_lines(app):
            if line.startswith("╰"):
                assert "…" not in line, line


# ── Pie contextual ──────────────────────────────────────────────


def footer(app: QcorreApp) -> str:
    """El pie con los espacios normalizados (las teclas son píldoras: " c  commit")."""
    return " ".join(str(app.query_one(HintBar).render()).split())


async def select_line(app: QcorreApp, pilot, fragment: str) -> None:
    tree = app.query_one(ProjectsPanel).tree
    for line in range(tree.last_line + 1):
        if fragment in str(tree.get_node_at_line(line).label):
            tree.move_cursor_to_line(line)
            await pilot.pause()
            return
    raise AssertionError(fragment)


async def test_el_pie_cambia_segun_lo_seleccionado():
    app = make_app()
    async with app.run_test(size=(140, 30)) as pilot:
        await settle(app, pilot)
        await select_line(app, pilot, "uvicorn")
        on_process = footer(app)
        assert "enter detalle" in on_process and "k matar" in on_process
        assert "c commit" in on_process  # el proyecto tiene repo

        await select_line(app, pilot, "tienda-api")
        on_project = footer(app)
        assert "enter plegar" in on_project and "K matar todos" in on_project
        assert "k matar " not in on_project + " "

        await select_line(app, pilot, "Huérfanos")
        on_orphans = footer(app)
        assert "K matar todos" in on_orphans
        assert "c commit" not in on_orphans  # los huérfanos no tienen repo

        await pilot.press("2")
        await pilot.pause()
        on_git = footer(app)
        assert "k matar" not in on_git and "1 ir a proyectos" in on_git


async def test_el_pie_siempre_es_una_linea_y_conserva_ayuda_y_salir():
    for width in (60, 80, 100, 140):
        app = make_app()
        async with app.run_test(size=(width, 30)) as pilot:
            await settle(app, pilot)
            for keys in ([], ["2"]):
                await pilot.press(*keys) if keys else None
                await pilot.pause()
                bar = app.query_one(HintBar)
                raw = str(bar.render())
                assert "\n" not in raw and bar.size.height == 1
                assert len(raw) <= bar.content_size.width, (width, raw)
                assert footer(app).endswith("? ayuda q salir"), (width, raw)


async def test_en_un_pie_angosto_se_recortan_los_menos_importantes():
    app = make_app()
    async with app.run_test(size=(60, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("2")
        await pilot.pause()
        text = footer(app)
        # El orden es de importancia: lo primero sobrevive, lo último se cae.
        assert "↑↓ desplazar" in text and "h historial" in text
        assert "1 ir a proyectos" not in text


async def test_el_pie_se_traduce():
    app = make_app()
    async with app.run_test(size=(140, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("i")
        await pilot.pause()
        assert footer(app).endswith("? help q quit")


async def test_1_y_2_saltan_entre_paneles():
    app = make_app()
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("2")
        assert app.focused is app.query_one("#git-scroll")
        await pilot.press("1")
        assert app.focused is app.query_one(ProjectsPanel).tree


# ── Estilos unificados ──────────────────────────────────────────


def test_un_solo_estilo_de_encabezado():
    assert str(heading("Qué va a pasar").style) == f"bold {theme.FOREGROUND}"


def test_un_solo_estilo_de_teclas():
    line = keys_line([Key("enter", "matar", primary=True, danger=True), Key("esc", "cancelar")])
    assert line.plain == " enter  matar    esc  cancelar"
    styles = [str(span.style) for span in line.spans]
    assert styles == [
        f"bold {theme.BACKGROUND} on {theme.ERROR}",  # tecla de una acción destructiva
        theme.FOREGROUND,  # la acción principal
        f"bold {theme.BACKGROUND} on {theme.ACCENT}",  # tecla dibujada
        theme.MUTED,  # las demás acciones
    ]


async def test_los_dialogos_usan_los_estilos_unificados():
    world = DemoWorld(delay=0, home=Path("/home/ana"))
    app = QcorreApp(**world.as_kwargs(), refresh_seconds=None)
    async with app.run_test(size=(120, 40)) as pilot:
        await settle(app, pilot)
        for key, primary in (("b", "cambiar"), ("u", "elegir"), ("p", "subir")):
            await pilot.press(key)
            await pilot.pause(0.1)
            keys = app.screen.query_one("#dialog-keys").render()
            spans = {keys.plain[s.start : s.end]: Style.parse(str(s.style)) for s in keys.spans}
            assert spans[" " + primary].color.triplet == Color.parse(theme.FOREGROUND).triplet, key
            assert spans[" esc "].bgcolor.triplet == Color.parse(theme.ACCENT).triplet, key
            assert spans[" esc "].bold, key
            await pilot.press("escape")
            await settle(app, pilot)


# ── Panel de git sin redundancias ───────────────────────────────


def test_la_rama_no_se_repite_en_el_cuerpo():
    text = status_body(sample_status(), 0).plain
    assert "feature/pagos" not in text.split("\n")[0]
    assert "Estás en la rama" not in text


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (RepoStatus(branch=None, oid=OID), "No estás en ninguna rama"),
        (RepoStatus(branch="main", oid=None), "que todavía no tiene commits"),
    ],
)
def test_la_rama_se_explica_cuando_hay_algo_raro(status, expected):
    assert expected in status_body(status, 0).plain


# ── Estados vacíos y de error con acción ────────────────────────


async def test_estado_vacio_sugiere_el_modo_demo():
    app = make_app(Snapshot())
    async with app.run_test(size=(110, 30)) as pilot:
        await settle(app, pilot)
        projects = str(app.query_one(ProjectsPanel).query_one(".empty").render())
        assert "qcorre --demo" in projects
        git = str(app.query_one(GitPanel).query_one(".empty").render())
        assert "Selecciona un proyecto" not in git
        assert "carpeta" in git


@pytest.mark.parametrize(
    ("error", "hint"),
    [
        (GitError("failed", "fatal: not a git repository (or any of the parent directories)"),
         "ya no es un repositorio git"),
        (GitError("not_installed"), "git-scm.com"),
        (GitError("timeout"), "Pulsa r para volver a intentarlo"),
        (GitError("failed", "fatal: algo raro"), "Pulsa r para volver a intentarlo"),
    ],
)  # fmt: skip
async def test_los_errores_de_git_sugieren_que_hacer(error, hint):
    def broken(path):
        raise error

    app = make_app(git_reader=broken)
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        body = app.query_one(GitPanel).query_one("#git-body").render()
        assert hint in str(body)
