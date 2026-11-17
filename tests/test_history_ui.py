"""Tests del historial en la interfaz: dibujo de cada línea y vista en el panel."""

from pathlib import Path

import pytest
from test_action_ui import FakeExecutor
from test_app import sample_snapshot, sample_status, settle

from qcorre import i18n
from qcorre.git.graph import layout
from qcorre.git.history import Commit, History, Ref, RefKind
from qcorre.git.runner import GitError
from qcorre.ui import theme
from qcorre.ui.app import QcorreApp
from qcorre.ui.git_panel import HISTORY, STATUS, GitPanel
from qcorre.ui.history_view import (
    AGE_FROM_WIDTH,
    AUTHOR_FROM_WIDTH,
    MAX_GRAPH_WIDTH,
    columns_for,
    commit_line,
    graph_text,
    history_body,
    lane_color,
    refs_text,
)
from qcorre.ui.widgets import HintBar

NOW = 1_800_000_000.0
HOUR = 3600.0


@pytest.fixture(autouse=True)
def spanish():
    previous = i18n.get_language()
    i18n.set_language("es")
    yield
    i18n.set_language(previous)


def c(oid, *parents, subject=None, refs=(), author="Ana", age=2 * HOUR):
    return Commit(
        oid=oid * 40 if len(oid) == 1 else oid,
        parents=tuple(p * 40 if len(p) == 1 else p for p in parents),
        refs=refs,
        author=author,
        time=NOW - age,
        subject=oid if subject is None else subject,
    )


def sample_history() -> History:
    return History(
        commits=(
            c("a", "b", "c", subject="Merge de feature/pagos",
              refs=(Ref(RefKind.HEAD, "main"), Ref(RefKind.REMOTE, "origin/main"))),
            c("b", "d", subject="Valida montos negativos", age=5 * HOUR),
            c("c", "d", subject="Agrega webhook de pagos",
              refs=(Ref(RefKind.LOCAL, "feature/pagos"),), author="Luis", age=3 * HOUR),
            c("d", subject="Primer commit", refs=(Ref(RefKind.TAG, "v1.0"),), age=30 * HOUR),
        )
    )  # fmt: skip


def lines(history: History, width: int = 100) -> list[str]:
    return history_body(history, NOW, width=width).plain.splitlines()


# ── Dibujo de las líneas ────────────────────────────────────────


def test_cada_commit_es_una_linea_en_columnas():
    assert lines(sample_history(), width=100) == [
        "●─╮ aaaaaaa (HEAD → main, origin/main) Merge de feature/pagos                           2h 00m  Ana",
        "● │ bbbbbbb Valida montos negativos                                                     5h 00m  Ana",
        "│ ● ccccccc (feature/pagos) Agrega webhook de pagos                                     3h 00m  Luis",
        "●─╯ ddddddd (v1.0) Primer commit                                                         1d 6h  Ana",
    ]


def test_las_columnas_de_la_derecha_quedan_alineadas():
    rendered = lines(sample_history(), width=100)
    # La antigüedad termina en la misma columna y el autor empieza en la misma.
    assert {line.index("  Ana") if "  Ana" in line else line.index("  Luis") for line in rendered} == {
        rendered[0].index("  Ana")
    }
    assert all(len(line) <= 100 for line in rendered)


def test_el_hash_y_el_mensaje_quedan_alineados_aunque_el_grafico_cambie_de_ancho():
    starts = {line.index(oid) for line, oid in zip(lines(sample_history()), "abcd")}
    assert starts == {4}


def test_sin_commits_se_explica():
    assert history_body(History(), NOW).plain == (
        "Este repo todavía no tiene commits: aún no hay historial que mostrar."
    )


def test_historial_recortado_avisa_al_final():
    history = History(commits=sample_history().commits, truncated=True)
    assert lines(history)[-1] == (
        "Se muestran los 4 commits más recientes; hay historial más antiguo."
    )


def test_mensaje_largo_se_corta_para_caber():
    long = c("a", subject="x" * 200)
    for width in (40, 60, 90):
        (line,) = lines(History((long,)), width=width)
        assert len(line) <= width, width
        assert "…" in line


def test_en_poco_ancho_primero_se_quita_el_autor_y_luego_la_antiguedad():
    commit = c("a", subject="Agrega webhook de pagos", author="Nombre Bastante Largo")
    (wide,) = lines(History((commit,)), width=AUTHOR_FROM_WIDTH)
    assert wide.endswith("2h 00m  Nombre Bastante…")  # el autor largo se corta
    (medium,) = lines(History((commit,)), width=AUTHOR_FROM_WIDTH - 1)
    assert medium.endswith("2h 00m") and "Nombre" not in medium
    (narrow,) = lines(History((commit,)), width=AGE_FROM_WIDTH - 1)
    assert narrow == "● aaaaaaa Agrega webhook de pagos"


def test_la_antiguedad_se_alinea_a_la_derecha():
    history = History(
        (c("a", "b", subject="reciente", age=30), c("b", subject="viejo", age=3 * 86400 + 4 * HOUR))
    )
    recent, old = lines(history, width=60)
    assert recent.endswith("  <1m") and old.endswith("3d 4h")
    assert len(recent) == len(old) == 60


def test_commit_sin_mensaje_sin_autor_y_sin_fecha():
    (line,) = lines(History((Commit(oid="e" * 40),)))
    assert line == "● eeeeeee (sin mensaje)"


def test_fechas_en_el_futuro_no_truenan():
    # Relojes desajustados: un commit puede venir "del futuro".
    (line,) = lines(History((c("a", subject="del futuro", age=-5 * HOUR),)), width=60)
    assert line.endswith("<1m")


def test_muchas_etiquetas_se_resumen():
    refs = (
        Ref(RefKind.HEAD, "main"),
        Ref(RefKind.LOCAL, "a"),
        Ref(RefKind.LOCAL, "b"),
        Ref(RefKind.REMOTE, "origin/main"),
        Ref(RefKind.TAG, "v1"),
    )
    assert refs_text(refs).plain == "(HEAD → main, a, b, +2)"
    assert refs_text(()).plain == ""
    assert refs_text((Ref(RefKind.DETACHED, "HEAD"),)).plain == "(HEAD)"


def test_si_las_etiquetas_no_dejan_sitio_se_muestran_menos():
    refs = (
        Ref(RefKind.HEAD, "feat/una-rama-con-nombre-largo"),
        Ref(RefKind.LOCAL, "main"),
        Ref(RefKind.REMOTE, "origin/main"),
    )
    commit = c("a", subject="Agrega webhook de pagos", refs=refs)
    (wide,) = lines(History((commit,)), width=110)
    assert "(HEAD → feat/una-rama-con-nombre-largo, main, origin/main)" in wide
    (medium,) = lines(History((commit,)), width=76)
    assert "(HEAD → feat/una-rama-con-nombre-largo, +2)" in medium and "Agrega" in medium
    # Ni con una sola etiqueta cabe: la línea se corta, pero nunca desborda.
    for width in (30, 40, 50):
        (narrow,) = lines(History((commit,)), width=width)
        assert len(narrow) <= width


def test_un_grafico_muy_ancho_se_corta_sin_desalinear():
    tips = [c(f"{i:040d}", "f", subject=f"rama {i}") for i in range(20)]
    history = History((*tips, c("f", subject="base")))
    rendered = lines(history, width=120)
    base = rendered[-1]
    assert base.index("fffffff") == MAX_GRAPH_WIDTH + 1
    assert base[MAX_GRAPH_WIDTH - 1] == "…"  # el gráfico no cabe: se avisa con "…"
    assert all(len(line) <= 120 for line in rendered)
    # Las filas angostas se rellenan para que el hash empiece en la misma columna.
    assert rendered[0].index("0" * 7) == MAX_GRAPH_WIDTH + 1


# ── Colores ─────────────────────────────────────────────────────


def colors_of(text, fragment: str) -> set[str]:
    """Colores con que está pintado ``fragment`` dentro de un ``Text``."""
    start = text.plain.index(fragment)
    found = set()
    for span in text.spans:
        if span.start <= start and span.end >= start + len(fragment):
            found.add(str(span.style).split()[-1])
    return found


def test_cada_carril_tiene_su_color_y_la_paleta_se_repite_en_ciclo():
    assert lane_color(0) == theme.LANES[0]
    assert lane_color(1) == theme.LANES[1]
    assert lane_color(len(theme.LANES)) == theme.LANES[0]
    assert lane_color(None) == theme.MUTED
    assert len(set(theme.LANES)) == len(theme.LANES) >= 6


def test_el_grafico_pinta_cada_carril_con_su_color():
    rows = layout(sample_history().commits)
    merge = graph_text(rows[0], 4)
    assert merge.plain == "●─╮ "
    assert colors_of(merge, "●") == {theme.LANES[0]}
    assert colors_of(merge, "╮") == {theme.LANES[1]}
    branch = graph_text(rows[2], 4)
    assert colors_of(branch, "│") == {theme.LANES[0]}
    assert colors_of(branch, "●") == {theme.LANES[1]}


def test_las_etiquetas_se_colorean_por_tipo():
    text = refs_text(
        (
            Ref(RefKind.HEAD, "main"),
            Ref(RefKind.LOCAL, "feat/x"),
            Ref(RefKind.REMOTE, "origin/main"),
            Ref(RefKind.TAG, "v1.0"),
        )[:3]
    )
    assert colors_of(text, "HEAD → main") == {theme.SUCCESS}
    assert colors_of(text, "feat/x") == {theme.ACCENT}
    assert colors_of(text, "origin/main") == {theme.SECONDARY}
    assert colors_of(refs_text((Ref(RefKind.TAG, "v1.0"),)), "v1.0") == {theme.WARNING}


def test_los_merges_van_mas_tenues_que_los_commits_normales():
    rows = layout(sample_history().commits)
    columns = columns_for(rows, NOW, 100)
    merge = commit_line(rows[0], NOW, columns)
    normal = commit_line(rows[1], NOW, columns)
    assert colors_of(merge, "Merge de feature/pagos") == {theme.MUTED}
    assert colors_of(normal, "Valida montos negativos") == {theme.FOREGROUND}


# ── Vista en el panel ───────────────────────────────────────────


def make_app(history=None, executor=None, counter=None) -> QcorreApp:
    snapshot = sample_snapshot()
    current = sample_history() if history is None else history

    def reader(path: Path) -> History:
        if counter is not None:
            counter.append(path)
        if isinstance(current, Exception):
            raise current
        return current

    return QcorreApp(
        scanner=lambda: snapshot,
        git_reader=sample_status,
        git_executor=executor or FakeExecutor(),
        history_reader=reader,
        refresh_seconds=None,
    )


def body_text(app: QcorreApp) -> str:
    return str(app.query_one(GitPanel).query_one("#git-body").render())


def tabs_text(app: QcorreApp) -> str:
    return str(app.query_one(GitPanel).query_one("#git-tabs").render())


async def test_h_alterna_entre_estado_e_historial():
    app = make_app()
    async with app.run_test(size=(130, 34)) as pilot:
        await settle(app, pilot)
        panel = app.query_one(GitPanel)
        assert panel.mode == STATUS
        assert "Estás en la rama feature/pagos" in body_text(app)
        assert "Estado" in tabs_text(app) and "Historial" in tabs_text(app)

        await pilot.press("h")
        await settle(app, pilot)
        assert panel.mode == HISTORY
        text = body_text(app)
        assert "●─╮ aaaaaaa (HEAD → main, origin/main) Merge de feature/pagos" in text
        assert "Estás en la rama" not in text
        assert panel.border_title == "tienda-api · feature/pagos"

        await pilot.press("h")
        await settle(app, pilot)
        assert panel.mode == STATUS and "Estás en la rama feature/pagos" in body_text(app)


async def test_el_historial_solo_se_lee_cuando_se_esta_mirando():
    reads: list[Path] = []
    app = make_app(counter=reads)
    async with app.run_test(size=(130, 34)) as pilot:
        await settle(app, pilot)
        await pilot.press("r")
        await settle(app, pilot)
        assert reads == []  # en la vista de estado no se pide el historial

        await pilot.press("h")
        await settle(app, pilot)
        assert len(reads) == 1
        await pilot.press("r")  # con el historial a la vista, el refresco lo relee
        await settle(app, pilot)
        assert len(reads) == 2
        assert {path.name for path in reads} == {"tienda-api"}


async def test_historial_de_un_repo_sin_commits_y_error_de_git():
    app = make_app(History())
    async with app.run_test(size=(130, 34)) as pilot:
        await settle(app, pilot)
        await pilot.press("h")
        await settle(app, pilot)
        assert "todavía no tiene commits" in body_text(app)

    app = make_app(GitError("failed", "fatal: bad object HEAD"))
    async with app.run_test(size=(130, 34)) as pilot:
        await settle(app, pilot)
        await pilot.press("h")
        await settle(app, pilot)
        assert "Git respondió con un error" in body_text(app)
        assert "bad object HEAD" in body_text(app)
        assert app.is_running


async def test_h_sin_repo_seleccionado_no_cambia_de_vista():
    reads: list[Path] = []
    app = make_app(counter=reads)
    async with app.run_test(size=(130, 34)) as pilot:
        await settle(app, pilot)
        await pilot.press("end")  # grupo de huérfanos
        await settle(app, pilot)
        await pilot.press("h")
        await settle(app, pilot)
        assert app.query_one(GitPanel).mode == STATUS and reads == []


async def test_el_historial_se_adapta_al_ancho_del_panel():
    long = History((c("a", subject="mensaje " * 40),))
    for size in ((90, 30), (130, 34), (180, 40)):
        app = make_app(long)
        async with app.run_test(size=size) as pilot:
            await settle(app, pilot)
            await pilot.press("h")
            await settle(app, pilot)
            body = app.query_one(GitPanel).query_one("#git-body")
            assert len(body_text(app)) <= body.size.width, size
            assert body.size.height == 1, size  # un commit, un renglón


async def test_ninguna_linea_del_historial_se_parte_en_dos_renglones():
    long_refs = (
        Ref(RefKind.HEAD, "feat/una-rama-con-nombre-largo"),
        Ref(RefKind.LOCAL, "main"),
        Ref(RefKind.REMOTE, "origin/main"),
    )
    history = History(
        (
            c("a", "b", subject="Merge pull request #6 from alguien/feat/una-rama", refs=long_refs),
            c("b", subject="feat: " + "palabra " * 30),
        )
    )
    for size in ((80, 30), (100, 30), (130, 34)):
        app = make_app(history)
        async with app.run_test(size=size) as pilot:
            await settle(app, pilot)
            await pilot.press("h")
            await settle(app, pilot)
            body = app.query_one(GitPanel).query_one("#git-body")
            assert body.size.height == 2, size
            assert all(len(line) <= body.size.width for line in body_text(app).splitlines())


async def test_un_refresco_sin_cambios_conserva_la_posicion_del_scroll():
    many = History(tuple(c(f"{i:040d}", f"{i + 1:040d}", subject=f"commit {i}") for i in range(120)))
    app = make_app(many)
    async with app.run_test(size=(130, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("h")
        await settle(app, pilot)
        scroll = app.query_one("#git-scroll")
        assert scroll.max_scroll_y > 0  # hay más commits de los que caben
        scroll.scroll_to(y=40, animate=False)
        await pilot.pause()
        assert scroll.scroll_y == 40
        await pilot.press("r")
        await settle(app, pilot)
        assert scroll.scroll_y == 40


async def test_al_volver_al_historial_se_empieza_desde_arriba():
    many = History(tuple(c(f"{i:040d}", f"{i + 1:040d}", subject=f"commit {i}") for i in range(120)))
    app = make_app(many)
    async with app.run_test(size=(130, 30)) as pilot:
        await settle(app, pilot)
        await pilot.press("h")
        await settle(app, pilot)
        scroll = app.query_one("#git-scroll")
        scroll.scroll_to(y=40, animate=False)
        await pilot.pause()
        await pilot.press("h", "h")
        await settle(app, pilot)
        assert scroll.scroll_y == 0


async def test_el_historial_cambia_de_idioma():
    app = make_app()
    async with app.run_test(size=(130, 34)) as pilot:
        await settle(app, pilot)
        await pilot.press("h")
        await settle(app, pilot)
        await pilot.press("i")
        await pilot.pause()
        assert "History" in tabs_text(app) and "Status" in tabs_text(app)
        assert "switches view" in tabs_text(app)


async def test_tras_una_accion_de_git_el_historial_se_actualiza():
    reads: list[Path] = []
    executor = FakeExecutor()
    app = make_app(executor=executor, counter=reads)
    async with app.run_test(size=(130, 34)) as pilot:
        await settle(app, pilot)
        await pilot.press("h")
        await settle(app, pilot)
        before = len(reads)
        await pilot.press("f")  # las acciones siguen disponibles en esta vista
        await pilot.pause()
        await pilot.press("enter")
        await settle(app, pilot)
        assert len(executor.calls) == 1
        assert len(reads) == before + 1


async def test_el_pie_incluye_el_historial():
    app = make_app()
    async with app.run_test(size=(130, 34)) as pilot:
        await settle(app, pilot)
        second = str(app.query_one(HintBar).render()).splitlines()[1]
        assert "h historial" in second



def test_en_un_panel_angosto_el_mensaje_manda_sobre_etiquetas_y_fecha():
    refs = (Ref(RefKind.HEAD, "feature/pagos"), Ref(RefKind.REMOTE, "origin/feature/pagos"))
    newest = c("a", "b", subject="add payment webhooks", refs=refs)
    plain = c("b", subject="validate negative amounts")
    first, second = lines(History((newest, plain)), width=54)
    # La fila con etiquetas cede su columna de antigüedad y recorta la etiqueta,
    # pero el mensaje se lee entero.
    assert "add payment webhooks" in first
    assert "(HEAD → feature/" in first and "…)" in first
    assert "origin/feature/pagos" not in first
    assert not first.endswith("2h 00m")
    # Las filas sin ese problema conservan su columna.
    assert second.endswith("2h 00m")
    assert len(first) <= 54 and len(second) <= 54


def test_si_no_queda_sitio_ni_para_una_etiqueta_recortada_se_omite():
    refs = (Ref(RefKind.HEAD, "feature/pagos"),)
    (line,) = lines(History((c("a", subject="add payment webhooks", refs=refs),)), width=34)
    assert "HEAD" not in line and "add payment webhooks" in line
