"""Calcula el gráfico de ramas del historial. Lógica pura, sin interfaz.

Cada commit ocupa una fila. El gráfico se arma con "carriles": columnas
verticales, una por cada línea de trabajo que está abierta en ese punto.

Recorriendo los commits del más nuevo al más viejo:

- Un carril "espera" a un commit concreto (el padre del último que dibujó).
- Cuando llega ese commit, se dibuja en su carril. Si varios carriles lo
  esperaban (ramas que salieron del mismo commit), los demás se cierran ahí
  y se unen con una curva.
- El primer padre sigue por el mismo carril. Cada padre adicional (un merge)
  abre un carril nuevo, o se une a uno existente si ya lo estaba esperando.

Cada fila se entrega como una lista de celdas (carácter + color), dos por
carril: el carril y el hueco a su derecha, por donde pasan las líneas
horizontales. El color es un número de carril: la interfaz le pone el tono.

Ejemplo (una rama mergeada)::

    ●─╮   merge
    ● │   commit en main
    │ ●   commit en la rama
    ●─╯   commit del que salió la rama
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from qcorre.git.history import Commit

NODE = "●"

# Direcciones que tiene una línea dentro de una celda.
_UP, _DOWN, _LEFT, _RIGHT = 1, 2, 4, 8

# Carácter de caja para cada combinación de direcciones.
_BOX = {
    0: " ",
    _UP: "│",
    _DOWN: "│",
    _LEFT: "─",
    _RIGHT: "─",
    _UP | _DOWN: "│",
    _LEFT | _RIGHT: "─",
    _UP | _LEFT: "╯",
    _UP | _RIGHT: "╰",
    _DOWN | _LEFT: "╮",
    _DOWN | _RIGHT: "╭",
    _UP | _DOWN | _LEFT: "┤",
    _UP | _DOWN | _RIGHT: "├",
    _UP | _LEFT | _RIGHT: "┴",
    _DOWN | _LEFT | _RIGHT: "┬",
    _UP | _DOWN | _LEFT | _RIGHT: "┼",
}


@dataclass(frozen=True)
class Cell:
    """Una celda del gráfico: un carácter y el color (número de carril) que lleva."""

    char: str
    color: int | None = None


@dataclass(frozen=True)
class GraphRow:
    """La fila del gráfico de un commit."""

    commit: Commit
    column: int  # carril donde va el commit
    color: int  # color de su carril
    cells: tuple[Cell, ...]

    @property
    def text(self) -> str:
        """El dibujo de la fila como texto simple (para tests y depuración)."""
        return "".join(cell.char for cell in self.cells).rstrip()


@dataclass
class _Lane:
    """Un carril abierto: qué commit espera y de qué color es."""

    oid: str
    color: int


def layout(commits: Iterable[Commit]) -> list[GraphRow]:
    """Calcula las filas del gráfico.

    ``commits`` debe venir del más nuevo al más viejo, con cada commit antes
    que sus padres (el orden de ``git log --topo-order``). Si faltan commits
    (historial recortado), sus carriles simplemente siguen abiertos hacia abajo.
    """
    lanes: list[_Lane | None] = []
    next_color = 0
    rows: list[GraphRow] = []

    for commit in commits:
        waiting = [i for i, lane in enumerate(lanes) if lane and lane.oid == commit.oid]
        before = list(lanes)

        if waiting:
            column = waiting[0]
            lane = lanes[column]
            assert lane is not None
            color = lane.color
        else:
            # Nadie lo esperaba: es la punta de una rama. Abre un carril nuevo.
            column = _free_slot(lanes)
            color = next_color
            next_color += 1
            before = list(lanes)  # el carril nuevo no tiene nada arriba

        # (carril, direcciones verticales en ese carril, color de la línea)
        edges: list[tuple[int, int, int]] = []

        # Los demás carriles que lo esperaban terminan aquí y se unen al commit.
        closing = waiting[1:]
        for index in closing:
            closed = lanes[index]
            assert closed is not None
            edges.append((index, _UP, closed.color))
            lanes[index] = None

        parents = list(dict.fromkeys(commit.parents))  # sin repetidos
        lanes[column] = _Lane(parents[0], color) if parents else None

        joined: set[int] = set()
        for parent in parents[1:]:
            existing = next(
                (i for i, lane in enumerate(lanes) if lane and lane.oid == parent and i != column),
                None,
            )
            if existing is not None:
                # Ya hay un carril esperando a ese padre: la línea se une a él.
                target = lanes[existing]
                assert target is not None
                edges.append((existing, _UP | _DOWN, target.color))
                joined.add(existing)
            else:
                # Puede reutilizar un carril que se acaba de cerrar en esta
                # misma fila: entonces la celda muestra "┤" (una línea que
                # llega desde arriba y otra que sale hacia abajo). Así, en el
                # flujo típico de PRs, la rama de turno ocupa siempre la
                # misma columna en vez de zigzaguear.
                slot = _free_slot(lanes)
                lanes[slot] = _Lane(parent, next_color)
                edges.append((slot, _DOWN, next_color))
                next_color += 1

        rows.append(GraphRow(commit, column, color, _draw(before, column, color, closing, edges)))

        while lanes and lanes[-1] is None:
            lanes.pop()

    return rows


def graph_width(rows: Sequence[GraphRow]) -> int:
    """Ancho, en caracteres, de la fila más ancha del gráfico."""
    return max((len(row.text) for row in rows), default=0)


def _free_slot(lanes: list[_Lane | None]) -> int:
    """Índice del primer carril libre (creándolo al final si no hay ninguno)."""
    for index, lane in enumerate(lanes):
        if lane is None:
            return index
    lanes.append(None)
    return len(lanes) - 1


def _draw(
    before: list[_Lane | None],
    column: int,
    color: int,
    closing: list[int],
    edges: list[tuple[int, int, int]],
) -> tuple[Cell, ...]:
    """Dibuja una fila: carriles que pasan de largo, el commit y sus uniones."""
    width = max([column, len(before) - 1, *(index for index, _, _ in edges)]) + 1
    masks = [0] * (2 * width)
    colors: list[int | None] = [None] * (2 * width)
    passing = [False] * (2 * width)

    # Carriles que solo pasan por esta fila, sin relación con el commit.
    for index, lane in enumerate(before):
        if lane is not None and index != column and index not in closing:
            masks[2 * index] = _UP | _DOWN
            colors[2 * index] = lane.color
            passing[2 * index] = True

    for index, vertical, edge_color in edges:
        toward_node = _LEFT if index > column else _RIGHT
        end = 2 * index
        masks[end] |= vertical | toward_node
        colors[end] = edge_color
        passing[end] = False

        low, high = sorted((2 * column, end))
        for position in range(low + 1, high):
            # Sobre un carril que pasa de largo, la horizontal va "por detrás":
            # se deja la vertical para no sugerir que están conectados.
            if passing[position]:
                continue
            masks[position] |= _LEFT | _RIGHT
            colors[position] = edge_color

    cells = [Cell(_BOX[mask], tone) for mask, tone in zip(masks, colors, strict=True)]
    cells[2 * column] = Cell(NODE, color)
    return tuple(cells)
