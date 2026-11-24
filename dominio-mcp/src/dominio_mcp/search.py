"""Busca hibrida de tabelas no pack (D-318, DM-8, T3.1).

Sem embeddings: BM25 (FTS5) sobre nome, comentario e colunas + trigramas do nome + glossario do
contador + apelidos das tabelas centrais + prior estrutural do proprio banco. O prior corrige o que
a busca lexical ingenua erra (15% no top-5 sem ele, 81% com ele no prototipo): tabela referenciada
por muitas FKs, volume, tabelas filhas e nome curto sobem; objeto obsoleto ou ilegivel desce.

A consulta do usuario so vira termos `[a-z0-9]+` entre aspas: nao ha como injetar operador do FTS5.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from dominio_mcp.overlay import Overlay
from dominio_mcp.pack import Pack
from dominio_mcp.textnorm import fold, tokens

__all__ = ["SchemaSearch", "SearchHit", "fold", "tokens"]

CANDIDATES = 60


def _normalized(rows: list[tuple[Any, ...]]) -> list[tuple[str, float]]:
    """BM25 do SQLite (menor e melhor, negativo) -> 0..1 relativo ao melhor candidato."""
    if not rows:
        return []
    raw = [(str(key), -float(score)) for key, score in rows]
    best = max(value for _, value in raw)
    if best <= 0:
        return [(key, 0.0) for key, _ in raw]
    return [(key, max(value, 0.0) / best) for key, value in raw]


@dataclass(frozen=True, slots=True)
class SearchHit:
    key: str
    name: str
    kind: str
    module: str
    score: float
    comment: str | None
    approx_rows: int | None
    queryable: bool
    obsolete: bool
    blocked_reason: str | None
    titulo: str | None
    why: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Alias:
    key: str
    titulo: str
    tokens: frozenset[str]


class SchemaSearch:
    def __init__(
        self,
        pack: Pack,
        overlay: Overlay,
        *,
        a: float = 0.5,
        b: float = 0.3,
        c: float = 0.2,
        p: float = 0.6,
        trigram_weight: float = 0.6,
        alias_weight: float = 2.0,
        obsolete_factor: float = 0.3,
        unreadable_factor: float = 0.5,
    ) -> None:
        self._pack = pack
        self._a, self._b, self._c, self._p = a, b, c, p
        self._trigram_weight = trigram_weight
        self._alias_weight = alias_weight
        self._obsolete_factor = obsolete_factor
        self._unreadable_factor = unreadable_factor
        glossary = overlay.data("glossary.yaml")
        self._stop = frozenset(t for w in glossary.get("stopwords", []) for t in tokens(str(w)))
        self._synonyms: dict[str, list[str]] = {}
        for term, expansions in (glossary.get("synonyms") or {}).items():
            stems = tokens(str(term))
            if stems:
                self._synonyms.setdefault(stems[0], []).extend(str(v) for v in expansions)
        self._aliases = self._load_aliases(overlay)
        self._titles = {al.key: al.titulo for al in self._aliases}

    def _load_aliases(self, overlay: Overlay) -> list[_Alias]:
        aliases: list[_Alias] = []
        for entry in overlay.data("core_tables.yaml").get("tables", []):
            key = str(entry["name"]).lower()
            if self._pack.table(key) is None:
                continue
            for alias in entry.get("aliases", []):
                toks = frozenset(t for t in tokens(str(alias)) if t not in self._stop)
                if toks:
                    aliases.append(_Alias(key, str(entry.get("titulo", "")), toks))
        return aliases

    def terms(self, query: str) -> list[str]:
        """Termos do usuario sem palavra vazia, mais os sinonimos do glossario."""
        out: list[str] = []
        for token in tokens(query):
            if token in self._stop:
                continue
            out.append(token)
            for synonym in self._synonyms.get(token, []):
                out.extend(tokens(synonym))
        return list(dict.fromkeys(out))

    def _prior(self, fk_in: int, rows: int | None, kids: int, parts: int) -> float:
        centrality = (
            self._a * math.log10(1 + fk_in)
            + self._b * math.log10(1 + (rows or 0))
            + self._c * math.log10(1 + kids)
        )
        return (1.0 + centrality) / (1.0 + self._p * (parts - 1))

    def search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        terms = self.terms(query)
        if not terms:
            return []
        scores: dict[str, float] = {}
        why: dict[str, set[str]] = {}

        def add(key: str, amount: float, source: str) -> None:
            scores[key] = scores.get(key, 0.0) + amount
            why.setdefault(key, set()).add(source)

        match = " OR ".join(f'"{t}"' for t in terms)
        text_rows = self._pack.query(
            "SELECT table_key, bm25(fts_tables, 0.0, 8.0, 8.0, 1.0) FROM fts_tables "
            "WHERE fts_tables MATCH ? ORDER BY 2 LIMIT ?",
            (match, CANDIDATES),
        )
        for key, amount in _normalized(text_rows):
            add(key, amount, "texto")
        long_terms = [t for t in terms if len(t) >= 4]
        if long_terms:
            tri = " OR ".join(f'"{t}"' for t in long_terms)
            tri_rows = self._pack.query(
                "SELECT table_key, bm25(tri_tables) FROM tri_tables WHERE tri_tables MATCH ? "
                "ORDER BY 2 LIMIT ?",
                (tri, CANDIDATES),
            )
            for key, amount in _normalized(tri_rows):
                add(key, self._trigram_weight * amount, "nome")
        query_tokens = {t for t in tokens(query) if t not in self._stop}
        for alias in self._aliases:
            if alias.tokens <= query_tokens:
                # o apelido vale mais quanto mais da pergunta ele cobre
                coverage = len(alias.tokens) / len(query_tokens)
                add(alias.key, self._alias_weight * coverage**2, "apelido")
        if not scores:
            return []

        info = self._features(list(scores))
        for key in list(scores):
            fk_in, rows, kids, parts, obsolete, readable = info[key]
            factor = self._prior(fk_in, rows, kids, parts)
            if obsolete:
                factor *= self._obsolete_factor
            if readable == 0:
                factor *= self._unreadable_factor
            scores[key] *= factor
        ranked = sorted(scores, key=lambda k: (-scores[k], k))[: max(1, min(limit, 20))]
        return [self._hit(key, scores[key], why[key]) for key in ranked]

    def _features(self, keys: list[str]) -> dict[str, tuple[int, int | None, int, int, int, Any]]:
        marks = ",".join("?" * len(keys))
        rows = self._pack.query(
            "SELECT f.table_key, f.fk_in, f.rows, f.kids, f.parts, f.obsolete, t.readable "  # noqa: S608
            f"FROM features f JOIN tables t ON t.key = f.table_key WHERE f.table_key IN ({marks})",
            tuple(keys),
        )
        return {r[0]: (r[1], r[2], r[3], r[4], r[5], r[6]) for r in rows}

    def _hit(self, key: str, score: float, sources: set[str]) -> SearchHit:
        table = self._pack.table(key)
        assert table is not None
        return SearchHit(
            key=key,
            name=table.name,
            kind=table.kind,
            module=table.module,
            score=round(score, 6),
            comment=table.comment,
            approx_rows=table.approx_rows,
            queryable=table.queryable,
            obsolete=table.obsolete,
            blocked_reason=table.blocked_reason,
            titulo=self._titles.get(key),
            why=tuple(sorted(sources)),
        )
