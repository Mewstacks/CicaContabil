"""Caminho de juncao entre tabelas por FK declarada (D-317, T3.3).

So existe juncao por chave estrangeira **declarada** no banco (6.803 delas), com chaves compostas
na ordem declarada. BFS de ate 4 saltos, com uma regra de seguranca: depois de subir (filho para
pai) nunca se desce de novo. "Subir e descer" liga duas tabelas pelo pai que elas compartilham
(por exemplo, `efsaidas` e `efentradas` por `geempre`), o que multiplica linhas sem sentido.
Formas validas: so subir, so descer, ou descer e depois subir (estrela, com a tabela de fato no
meio). Tabela intermediaria ilegivel ou bloqueada nao serve de ponte.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

from dominio_mcp.pack import FkRow, Pack

Direction = Literal["up", "down"]
MAX_HOPS = 4


@dataclass(frozen=True, slots=True)
class JoinStep:
    from_table: str
    to_table: str
    from_columns: tuple[str, ...]
    to_columns: tuple[str, ...]
    direction: Direction  # up: filho -> pai (muitos para um); down: pai -> filho


def _edges(foreign_keys: list[FkRow]) -> dict[str, list[JoinStep]]:
    graph: dict[str, list[JoinStep]] = {}
    for fk in foreign_keys:
        graph.setdefault(fk.child, []).append(
            JoinStep(fk.child, fk.parent, fk.child_cols, fk.parent_cols, "up")
        )
        graph.setdefault(fk.parent, []).append(
            JoinStep(fk.parent, fk.child, fk.parent_cols, fk.child_cols, "down")
        )
    for steps in graph.values():
        steps.sort(key=lambda s: (s.to_table, s.from_columns, s.to_columns, s.direction))
    return graph


def find_path(
    pack: Pack, source: str, target: str, *, max_hops: int = MAX_HOPS
) -> list[JoinStep] | None:
    """Menor caminho por FK de `source` ate `target`, ou `None` se nao houver um seguro."""
    start, goal = source.lower(), target.lower()
    if start == goal:
        return []
    if pack.table(start) is None or pack.table(goal) is None:
        return None
    graph = _edges(pack.foreign_keys())
    usable: dict[str, bool] = {}

    def bridge_ok(key: str) -> bool:
        if key not in usable:
            row = pack.table(key)
            usable[key] = row is not None and row.queryable
        return usable[key]

    State = tuple[str, str]  # (tabela, ultima direcao)
    initial: State = (start, "start")
    parents: dict[State, tuple[State, JoinStep] | None] = {initial: None}
    queue: deque[tuple[State, int]] = deque([(initial, 0)])
    while queue:
        (node, last), hops = queue.popleft()
        if hops >= max_hops:
            continue
        for step in graph.get(node, []):
            if last == "up" and step.direction == "down":
                continue
            nxt = step.to_table
            if nxt != goal and not bridge_ok(nxt):
                continue
            state: State = (nxt, step.direction)
            if state in parents:
                continue
            parents[state] = ((node, last), step)
            if nxt == goal:
                return _unwind(parents, state)
            queue.append((state, hops + 1))
    return None


def _unwind(
    parents: dict[tuple[str, str], tuple[tuple[str, str], JoinStep] | None],
    state: tuple[str, str],
) -> list[JoinStep]:
    steps: list[JoinStep] = []
    cursor: tuple[str, str] | None = state
    while cursor is not None:
        link = parents[cursor]
        if link is None:
            break
        cursor, step = link
        steps.append(step)
    steps.reverse()
    return steps
