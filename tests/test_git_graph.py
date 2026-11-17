"""Tests del gráfico de ramas (lógica pura: de commits a filas dibujadas)."""

import random

import pytest

from qcorre.git.graph import NODE, GraphRow, graph_width, layout
from qcorre.git.history import Commit

# Caracteres que tienen una línea hacia arriba / hacia abajo dentro de su celda.
UP = set("│├┤╯╰┴┼")
DOWN = set("│├┤╮╭┬┼")
ALLOWED = UP | DOWN | set("─ ") | {NODE}


def c(oid: str, *parents: str) -> Commit:
    return Commit(oid=oid, parents=parents, subject=oid)


def draw(commits: list[Commit]) -> list[str]:
    return [row.text for row in layout(commits)]


# ── Casos comunes ───────────────────────────────────────────────


def test_historial_lineal_es_una_sola_columna():
    assert draw([c("C", "B"), c("B", "A"), c("A")]) == ["●", "●", "●"]


def test_sin_commits():
    assert layout([]) == []
    assert graph_width([]) == 0


def test_un_solo_commit():
    (row,) = layout([c("A")])
    assert row.text == "●" and row.column == 0


def test_rama_mergeada():
    commits = [c("M", "A2", "B1"), c("A2", "A1"), c("B1", "A1"), c("A1")]
    assert draw(commits) == [
        "●─╮",  # el merge abre el carril de la rama
        "● │",  # commit en la línea principal
        "│ ●",  # commit en la rama
        "●─╯",  # commit del que salió la rama: el carril se cierra
    ]


def test_dos_ramas_que_salen_del_mismo_commit_sin_merge():
    commits = [c("F2", "A1"), c("M2", "A1"), c("A1", "A0"), c("A0")]
    assert draw(commits) == ["●", "│ ●", "●─╯", "●"]


def test_flujo_de_pull_requests_usa_siempre_la_misma_columna():
    # main recibe un PR tras otro: merge, commit de la rama, merge, commit...
    commits = [
        c("M3", "M2", "F3"),
        c("F3", "M2"),
        c("M2", "M1", "F2"),
        c("F2", "M1"),
        c("M1", "A", "F1"),
        c("F1", "A"),
        c("A"),
    ]
    assert draw(commits) == [
        "●─╮",
        "│ ●",
        "●─┤",  # se cierra la rama de arriba y se abre la siguiente
        "│ ●",
        "●─┤",
        "│ ●",
        "●─╯",
    ]
    assert graph_width(layout(commits)) == 3


# ── Casos raros ─────────────────────────────────────────────────


def test_tres_ramas_del_mismo_commit():
    commits = [c("X", "A"), c("Y", "A"), c("Z", "A"), c("A")]
    assert draw(commits) == ["●", "│ ●", "│ │ ●", "●─┴─╯"]


def test_merge_pulpo_de_tres_padres():
    commits = [c("M", "A", "B", "C"), c("A", "R"), c("B", "R"), c("C", "R"), c("R")]
    assert draw(commits) == ["●─┬─╮", "● │ │", "│ ● │", "│ │ ●", "●─┴─╯"]


def test_merge_hacia_un_carril_que_ya_existia_a_la_izquierda():
    # X y el merge M comparten el padre P: la línea del merge se une al carril de X.
    commits = [c("X", "P"), c("M", "A", "P"), c("A", "P"), c("P")]
    assert draw(commits) == ["●", "├─●", "│ ●", "●─╯"]


def test_dos_historias_sin_relacion():
    # Dos raíces (p. ej. una rama huérfana): cada una termina en su columna.
    commits = [c("H", "G"), c("O2", "O1"), c("G"), c("O1")]
    assert draw(commits) == ["●", "│ ●", "● │", "  ●"]


def test_merge_de_historias_sin_relacion():
    assert draw([c("M", "A", "O"), c("A"), c("O")]) == ["●─╮", "● │", "  ●"]


def test_historial_recortado_deja_los_carriles_abiertos():
    # Los padres de A y B quedaron fuera de la ventana de commits.
    commits = [c("M", "A", "B"), c("A", "fuera1"), c("B", "fuera2")]
    assert draw(commits) == ["●─╮", "● │", "│ ●"]


def test_merges_cruzados_la_horizontal_pasa_por_detras():
    commits = [c("M2", "A", "B"), c("M1", "B", "A"), c("A", "R"), c("B", "R"), c("R")]
    assert draw(commits) == [
        "●─╮",
        "├─│─●",  # la línea hacia A cruza el carril de B sin tocarlo
        "● │ │",
        "│ ●─╯",
        "●─╯",
    ]


def test_merges_anidados():
    commits = [
        c("M2", "M1", "F2"),
        c("F2", "F1"),
        c("M1", "A2", "E1"),
        c("E1", "A1"),
        c("A2", "A1"),
        c("F1", "A1"),
        c("A1"),
    ]
    assert draw(commits) == ["●─╮", "│ ●", "●─│─╮", "│ │ ●", "● │ │", "│ ● │", "●─┴─╯"]


def test_un_carril_liberado_en_medio_se_reutiliza():
    commits = [c("X", "A"), c("Y", "A"), c("Z", "B"), c("A", "B"), c("W", "B"), c("B")]
    assert draw(commits) == ["●", "│ ●", "│ │ ●", "●─╯ │", "│ ● │", "●─┴─╯"]


def test_merge_que_abre_un_carril_a_la_izquierda():
    # El carril 0 queda libre al llegar a la raíz R1; el merge M, que está en
    # la columna 1, abre ahí el carril de su segundo padre.
    commits = [c("A", "R1"), c("B", "M"), c("R1"), c("M", "X", "Y"), c("X"), c("Y")]
    assert draw(commits) == ["●", "│ ●", "● │", "╭─●", "│ ●", "●"]


def test_padre_repetido_no_duplica_carriles():
    assert draw([c("M", "A", "A"), c("A")]) == ["●", "●"]


def test_commit_que_es_su_propio_padre_no_cuelga():
    # Dato corrupto: no debe tronar ni quedarse en un bucle.
    rows = layout([c("A", "A"), c("B")])
    assert [row.text for row in rows] == ["●", "│ ●"]


def test_orden_inesperado_padre_antes_que_hijo_no_truena():
    # Si llegaran desordenados, cada commit se dibuja igual (en carriles aparte).
    rows = layout([c("A"), c("B", "A")])
    assert len(rows) == 2 and all(NODE in row.text for row in rows)


def test_muchas_ramas_en_paralelo():
    tips = [c(f"T{i}", "R") for i in range(20)]
    rows = layout([*tips, c("R")])
    assert rows[-1].text == "●" + "─┴" * 18 + "─╯"
    assert graph_width(rows) == 39


# ── Columnas y colores ──────────────────────────────────────────


def test_column_indica_el_carril_del_commit():
    rows = layout([c("M", "A2", "B1"), c("A2", "A1"), c("B1", "A1"), c("A1")])
    assert [row.column for row in rows] == [0, 0, 1, 0]
    for row in rows:
        assert row.cells[2 * row.column].char == NODE


def test_cada_carril_conserva_su_color_y_las_ramas_tienen_el_suyo():
    rows = layout([c("M", "A2", "B1"), c("A2", "A1"), c("B1", "A1"), c("A1")])
    merge, main_commit, branch_commit, base = rows
    assert merge.color == main_commit.color == base.color == 0  # la línea principal
    assert branch_commit.color == 1
    # La curva que abre la rama, su vertical y la curva que la cierra son de su color.
    assert merge.cells[2].color == 1 and merge.cells[1].color == 1
    assert main_commit.cells[2].color == 1
    assert base.cells[2].color == 1
    # La vertical de la línea principal, a la altura del commit de la rama, es la suya.
    assert branch_commit.cells[0].color == 0


def test_cada_rama_nueva_recibe_un_color_distinto():
    commits = [c("M2", "M1", "F2"), c("F2", "M1"), c("M1", "A", "F1"), c("F1", "A"), c("A")]
    rows = layout(commits)
    by_oid = {row.commit.oid: row.color for row in rows}
    assert by_oid["M2"] == by_oid["M1"] == by_oid["A"]
    assert len({by_oid["M2"], by_oid["F2"], by_oid["F1"]}) == 3


def test_las_celdas_vacias_no_llevan_color():
    rows = layout([c("H", "G"), c("O2", "O1"), c("G"), c("O1")])
    assert rows[-1].cells[0].char == " " and rows[-1].cells[0].color is None


# ── Propiedades que deben cumplirse en cualquier historial ──────


def random_history(seed: int, size: int = 60) -> list[Commit]:
    """Historial aleatorio (con merges, raíces múltiples y padres fuera de la
    ventana), del más nuevo al más viejo y con los hijos antes que los padres."""
    rng = random.Random(seed)
    commits: list[Commit] = []
    for index in range(size):
        older = [f"c{j}" for j in range(index + 1, size)]
        count = rng.choice([0, 1, 1, 1, 1, 2, 2, 3])
        parents = rng.sample(older, min(count, len(older)))
        if rng.random() < 0.05:
            parents.append(f"fuera{index}")  # padre que no está en la lista
        commits.append(Commit(oid=f"c{index}", parents=tuple(parents)))
    return commits


def has_up(row: GraphRow, column: int, waited: set[str]) -> bool:
    if 2 * column >= len(row.cells):
        return False
    char = row.cells[2 * column].char
    if char == NODE:
        return row.commit.oid in waited
    return char in UP


def has_down(row: GraphRow, column: int) -> bool:
    if 2 * column >= len(row.cells):
        return False
    char = row.cells[2 * column].char
    if char == NODE:
        return bool(row.commit.parents)
    return char in DOWN


@pytest.mark.parametrize("seed", range(40))
def test_propiedades_del_grafico_en_historiales_aleatorios(seed):
    commits = random_history(seed)
    rows = layout(commits)
    assert [row.commit for row in rows] == commits  # una fila por commit, en orden

    waited = {parent for commit in commits for parent in commit.parents}
    for row in rows:
        text = "".join(cell.char for cell in row.cells)
        assert set(text) <= ALLOWED
        assert text.count(NODE) == 1
        assert row.cells[2 * row.column].char == NODE
        assert len(row.cells) % 2 == 0
        for cell in row.cells:
            assert (cell.color is None) == (cell.char == " ")

    # Continuidad vertical: toda línea que baja de una fila llega a la siguiente,
    # y toda línea que entra por arriba viene de la fila anterior.
    for upper, lower in zip(rows, rows[1:]):
        width = max(len(upper.cells), len(lower.cells)) // 2
        for column in range(width):
            assert has_down(upper, column) == has_up(lower, column, waited), (
                seed,
                upper.commit.oid,
                column,
            )

    # La primera fila no tiene nada arriba.
    assert not any(has_up(rows[0], col, waited) for col in range(len(rows[0].cells) // 2))


@pytest.mark.parametrize("seed", range(10))
def test_un_commit_esperado_por_varios_hijos_cierra_todos_sus_carriles(seed):
    commits = random_history(seed)
    rows = layout(commits)
    # Tras el último commit con padres dentro de la lista no quedan carriles
    # abiertos salvo los que esperan a commits que no están.
    known = {commit.oid for commit in commits}
    last = rows[-1]
    open_below = sum(has_down(last, col) for col in range(len(last.cells) // 2))
    missing = {p for commit in commits for p in commit.parents if p not in known}
    assert open_below <= len(missing) + len(last.commit.parents)
