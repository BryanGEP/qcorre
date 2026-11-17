"""Tests del tema amigable: paletas, cambio en caliente, cabecera, frases y últimos commits."""

import shutil
import time
from pathlib import Path

import pytest
from rich.color import Color
from rich.style import Style
from test_app import make_app, sample_status, settle, tree_lines
from test_design import contrast
from test_git_integration import commit, git

from qcorre import cli, i18n
from qcorre.demo import DemoWorld
from qcorre.git.history import Commit, Ref, RefKind
from qcorre.git.parse import ChangeKind, FileChange, RepoStatus
from qcorre.git.status import read_status
from qcorre.ui import theme
from qcorre.ui.app import QcorreApp
from qcorre.ui.git_panel import GitPanel
from qcorre.ui.git_view import file_mark, status_body, tone_color
from qcorre.ui.history_view import ref_style
from qcorre.ui.projects_panel import ProjectsPanel
from qcorre.ui.styles import Key, keys_line
from qcorre.ui.widgets import Header

from test_git_integration import isolated_git, repo  # noqa: F401  isort: skip

OID = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"


@pytest.fixture(autouse=True)
def spanish_and_dark():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)
    theme.use(theme.DEFAULT_THEME)


def same_color(style: Style | str, color: str, *, background: bool = False) -> bool:
    style = Style.parse(str(style)) if not isinstance(style, Style) else style
    value = style.bgcolor if background else style.color
    return value is not None and value.triplet == Color.parse(color).triplet


# ── Paletas ─────────────────────────────────────────────────────


@pytest.mark.parametrize("name", theme.THEMES)
def test_cada_paleta_cumple_el_contraste_aa(name):
    p = theme.PALETTES[name]
    texts = [p.foreground, p.muted, p.accent, p.secondary, p.success, p.warning, p.error]
    for color in texts:
        for background in (p.background, p.surface, p.panel):
            assert contrast(color, background) >= 4.5, (name, color, background)
    # El texto de las teclas dibujadas y del chip DEMO va sobre un color sólido.
    for solid in (p.accent, p.error, p.warning):
        assert contrast(p.background, solid) >= 4.5, (name, solid)


@pytest.mark.parametrize("name", theme.THEMES)
def test_cada_paleta_tiene_seis_carriles_distintos(name):
    lanes = theme.PALETTES[name].lanes
    assert len(set(lanes)) == len(lanes) == 6
    for lane in lanes:
        assert contrast(lane, theme.PALETTES[name].surface) >= 3


def test_use_cambia_los_colores_que_lee_el_codigo():
    theme.use("light")
    assert theme.current == "light" and theme.ACCENT == theme.PALETTES["light"].accent
    # Las funciones leen el tema al pintar, no al importar.
    assert tone_color("good") == theme.PALETTES["light"].success
    assert file_mark(ChangeKind.MODIFIED)[1] == theme.PALETTES["light"].warning
    assert theme.PALETTES["light"].accent in ref_style(RefKind.LOCAL)
    theme.use("dark")
    assert tone_color("good") == theme.PALETTES["dark"].success
    with pytest.raises(ValueError):
        theme.use("sepia")


def test_next_theme_alterna():
    theme.use("dark")
    assert theme.next_theme() == "light"
    theme.use("light")
    assert theme.next_theme() == "dark"


# ── Elegir el tema ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("requested", "env", "expected"),
    [
        (None, {}, "dark"),
        ("light", {}, "light"),
        (None, {"QCORRE_THEME": "light"}, "light"),
        (None, {"QCORRE_THEME": " LIGHT "}, "light"),
        ("dark", {"QCORRE_THEME": "light"}, "dark"),  # --theme manda
        (None, {"QCORRE_THEME": "sepia"}, "dark"),  # valor desconocido: el de siempre
    ],
)
def test_choose_theme(requested, env, expected):
    assert cli.choose_theme(requested, env) == expected


def test_la_cli_acepta_theme(monkeypatch):
    monkeypatch.delenv("QCORRE_THEME", raising=False)
    app = cli.build_app(cli.build_parser().parse_args(["--demo", "--theme", "light"]))
    assert app.theme == "qcorre-light" and theme.current == "light"
    assert cli.THEMES == theme.THEMES  # la CLI no importa Textual, pero deben coincidir
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--theme", "sepia"])


# ── Cambiar de tema en caliente ─────────────────────────────────


async def test_t_cambia_el_tema_y_repinta_todo():
    app = make_app()
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        assert app.theme == "qcorre-dark"
        header = app.query_one(ProjectsPanel).tree.get_node_at_line(0).label
        assert same_color(header.spans[0].style, theme.PALETTES["dark"].accent)

        await pilot.press("t")
        await pilot.pause()
        assert app.theme == "qcorre-light" and theme.current == "light"
        light = theme.PALETTES["light"]
        header = app.query_one(ProjectsPanel).tree.get_node_at_line(0).label
        assert same_color(header.spans[0].style, light.accent)
        # El panel de git, la cabecera y el pie también se repintan.
        body = app.query_one(GitPanel).query_one("#git-body").render()
        assert any(same_color(span.style, light.warning) for span in body.spans)
        chips = app.query_one(Header).query_one("#status").render()
        assert any(same_color(span.style, light.panel, background=True) for span in chips.spans)
        footer = app.query_one("HintBar").render()
        assert any(same_color(span.style, light.accent, background=True) for span in footer.spans)
        # El texto no cambia, solo los colores.
        assert tree_lines(app)[0].startswith("tienda-api")

        await pilot.press("t")
        await pilot.pause()
        assert app.theme == "qcorre-dark"


async def test_con_un_dialogo_abierto_t_no_cambia_el_tema():
    app = make_app()
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        await pilot.press("question_mark")
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()
        assert app.theme == "qcorre-dark"


async def test_la_app_arranca_con_el_tema_pedido():
    app = QcorreApp(**DemoWorld(delay=0, home=Path("/home/ana")).as_kwargs(),
                    refresh_seconds=None, theme_name="light")  # fmt: skip
    async with app.run_test(size=(120, 34)) as pilot:
        await settle(app, pilot)
        assert app.theme == "qcorre-light"
        assert app.get_css_variables()["qc-pill"] == theme.PALETTES["light"].panel


# ── Cabecera con chips ──────────────────────────────────────────


def chips(app: QcorreApp) -> str:
    return str(app.query_one(Header).query_one("#status").render())


async def test_los_chips_resumen_lo_que_corre():
    world = DemoWorld(delay=0, home=Path("/home/ana"))
    app = QcorreApp(**world.as_kwargs(), refresh_seconds=None)
    async with app.run_test(size=(130, 34)) as pilot:
        await settle(app, pilot)
        text = chips(app)
        for chip in (" DEMO ", " 3 proyectos ", " 9 procesos ", " 4 huérfanos ", " ES "):
            assert chip in text
        rendered = app.query_one(Header).query_one("#status").render()
        orphans = next(s for s in rendered.spans if "huérfanos" in rendered.plain[s.start : s.end])
        assert same_color(orphans.style, theme.WARNING)


async def test_sin_huerfanos_no_hay_chip_de_huerfanos():
    from qcorre.models import Snapshot

    base = make_app().scanner()
    healthy = Snapshot(projects=base.projects[1:])  # tienda-web: sin avisos
    app = make_app(healthy)
    async with app.run_test(size=(130, 34)) as pilot:
        await settle(app, pilot)
        assert "huérfano" not in chips(app)


# ── Frases con números destacados ───────────────────────────────


def colored(text, fragment: str, within: str | None = None) -> Style:
    """Estilo con que está pintado ``fragment`` (buscado dentro de ``within``, si se da)."""
    start = text.plain.index(within or fragment) + (within or fragment).index(fragment)
    styles = [s.style for s in text.spans if s.start <= start and s.end >= start + len(fragment)]
    return Style.parse(str(styles[-1]))


def test_los_numeros_de_las_frases_van_destacados():
    status = RepoStatus(
        branch="main", oid=OID, upstream="origin/main", ahead=2, behind=0, remotes=("origin",),
        files=(FileChange("a.py", worktree="M"), FileChange("b.py", untracked=True)),
    )  # fmt: skip
    text = status_body(status, time.time())
    changed = colored(text, "1 archivo")
    assert changed.bold and same_color(changed, theme.WARNING)
    new = colored(text, "1 archivo", within="1 archivo nuevo")
    assert same_color(new, theme.SUCCESS)
    ahead = colored(text, "2 commits")
    assert ahead.bold and same_color(ahead, theme.ACCENT)
    # La puntuación que sigue al número no se colorea.
    sentence_end = text.plain.index("2 commits sin subir.") + len("2 commits")
    assert text.plain[sentence_end:].startswith(" sin subir.")


def test_ramas_separadas_destacan_subir_y_bajar_con_su_color():
    status = RepoStatus(branch="main", oid=OID, upstream="origin/main", ahead=2, behind=1,
                        remotes=("origin",))  # fmt: skip
    text = status_body(status, time.time())
    assert same_color(colored(text, "2 commits"), theme.ACCENT)
    assert same_color(colored(text, "1 commit", within="1 commit sin bajar"), theme.WARNING)


# ── Últimos commits bajo el mapa ────────────────────────────────


def recent(*subjects: str) -> tuple[Commit, ...]:
    oids = [f"{i:040d}" for i in range(len(subjects))]
    return tuple(
        Commit(oid=oid, parents=(oids[i + 1],) if i + 1 < len(oids) else (),
               subject=subject, author="Ana", time=time.time() - (i + 1) * 3600,
               refs=(Ref(RefKind.HEAD, "main"),) if i == 0 else ())
        for i, (oid, subject) in enumerate(zip(oids, subjects, strict=True))
    )  # fmt: skip


def test_los_ultimos_commits_van_debajo_del_mapa():
    status = sample_status()
    status = RepoStatus(**{**status.__dict__, "recent": recent("tercero", "segundo", "primero")})
    lines = status_body(status, time.time(), width=90).plain.splitlines()
    heading = lines.index("Últimos commits")
    assert heading > next(i for i, line in enumerate(lines) if "Tu compu" in line)
    assert "(HEAD → main) tercero" in lines[heading + 1]
    assert "segundo" in lines[heading + 2] and "primero" in lines[heading + 3]
    assert all(line.startswith("● ") for line in lines[heading + 1 : heading + 4])


def test_sin_commits_no_hay_seccion_de_ultimos_commits():
    text = status_body(RepoStatus(branch="main", oid=None), time.time()).plain
    assert "Últimos commits" not in text


@pytest.mark.skipif(shutil.which("git") is None, reason="git no está instalado")
def test_read_status_trae_los_ultimos_commits_de_la_rama(repo):  # noqa: F811
    git(repo, "switch", "-q", "-c", "feat/x")
    commit(repo, "x.txt", message="en la rama")
    git(repo, "switch", "-q", "main")
    for index in range(6):
        commit(repo, f"m{index}.txt", message=f"main {index}")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge feat/x", "feat/x")

    status = read_status(repo)
    subjects = [c.subject for c in status.recent]
    # Los 5 más recientes de la rama; el commit de la rama mergeada no se cuela.
    assert subjects == ["merge feat/x", "main 5", "main 4", "main 3", "main 2"]
    assert status.head_subject == "merge feat/x" and status.has_parent
    assert status.recent[0].refs[0] == Ref(RefKind.HEAD, "main")


async def test_el_panel_muestra_los_ultimos_commits():
    def reader(path):
        base = sample_status()
        return RepoStatus(**{**base.__dict__, "recent": recent("valida montos", "modelo de pagos")})

    app = make_app(git_reader=reader)
    async with app.run_test(size=(130, 40)) as pilot:
        await settle(app, pilot)
        body = str(app.query_one(GitPanel).query_one("#git-body").render())
        assert "Últimos commits" in body and "valida montos" in body


# ── Teclas dibujadas ────────────────────────────────────────────


def test_las_teclas_se_dibujan_como_pildoras():
    line = keys_line([Key("c", "commit"), Key("enter", "matar", danger=True)])
    caps = [s for s in line.spans if Style.parse(str(s.style)).bgcolor is not None]
    assert [line.plain[s.start : s.end] for s in caps] == [" c ", " enter "]
    assert same_color(caps[0].style, theme.ACCENT, background=True)
    assert same_color(caps[1].style, theme.ERROR, background=True)


def test_los_ultimos_commits_son_una_sola_columna_aunque_haya_merges():
    commits = list(recent("merge de la rama", "commit en main", "inicio"))
    # El primero es un merge: su segundo padre no está en la lista.
    commits[0] = Commit(**{**commits[0].__dict__, "parents": (commits[1].oid, "f" * 40)})
    status = RepoStatus(branch="main", oid=OID, recent=tuple(commits))
    text = status_body(status, time.time(), width=90)
    lines = text.plain.splitlines()
    heading = lines.index("Últimos commits")
    graph = [line[:2] for line in lines[heading + 1 : heading + 4]]
    assert graph == ["● ", "● ", "● "]  # sin carriles laterales
    # El merge sigue viéndose tenue, como en el historial.
    assert same_color(colored(text, "merge de la rama"), theme.MUTED)


@pytest.mark.parametrize("lang", ["es", "en"])
@pytest.mark.parametrize("size", [(100, 30), (108, 30), (140, 40)])
async def test_los_ultimos_commits_nunca_se_parten_en_dos_lineas(lang, size):
    i18n.set_language(lang)
    app = QcorreApp(**DemoWorld(delay=0, home=Path("/home/ana")).as_kwargs(), refresh_seconds=None)
    async with app.run_test(size=size) as pilot:
        await settle(app, pilot)
        body = app.query_one(GitPanel).query_one("#git-body")
        lines = str(body.render()).splitlines()
        start = next(i for i, line in enumerate(lines) if line in ("Últimos commits", "Latest commits"))
        recent_lines = lines[start + 1 :]
        assert len(recent_lines) == 5
        # Cada commit es una línea que empieza por su punto y cabe en el panel.
        assert all(line.startswith("● ") for line in recent_lines), recent_lines
        # Cada una cabe en el ancho real del cuerpo, así que no se parte.
        assert all(len(line) <= body.size.width for line in recent_lines), (
            body.size.width, recent_lines)
