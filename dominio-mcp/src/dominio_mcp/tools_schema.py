"""Ferramentas L0: o conhecimento do banco, sem tocar no banco (D-318, T5.1).

`mapa_do_banco`, `buscar_esquema`, `descrever_tabela`, `caminho_entre_tabelas` e
`valores_do_campo` leem so o pack local. Toda descricao volta com `fonte` e `confianca`
(comentario do banco, overlay revisado ou inferido) para o modelo nao tratar palpite como fato.
Toda resposta cabe em 12 KB (o mapa, em 3 KB); coluna de segredo aparece so como bloqueada, sem
comentario (o pack nem o guarda).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from dominio_mcp.joins import find_path
from dominio_mcp.overlay import Overlay
from dominio_mcp.pack import ColumnRow, Pack
from dominio_mcp.policy import PolicyClass, fold
from dominio_mcp.search import SchemaSearch

MAX_BYTES = 12 * 1024
MAP_BYTES = 3 * 1024
PAGE_SIZE = 40
COMMENT_CHARS = 110
LEGEND_CHARS = 140
CARD_COMMENT = 120
MAX_FK_LISTED = 12
MAX_INDEXES_LISTED = 8


class ToolError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def size_of(body: dict[str, Any]) -> int:
    return len(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _clip(text: str | None, limit: int) -> str | None:
    if not text:
        return None
    return text if len(text) <= limit else text[: limit - 1] + "…"


class SchemaTools:
    def __init__(
        self,
        pack_provider: Callable[[], Pack],
        stale_reason: Callable[[], str | None],
        overlay: Overlay,
    ) -> None:
        self._pack_provider = pack_provider
        self._stale_reason = stale_reason
        self._overlay = overlay
        self._search_cache: tuple[str, SchemaSearch] | None = None
        legends = overlay.data("legends.yaml")
        self._legends = legends.get("legends") or {}
        self._warnings = [
            (re.compile(str(w["pattern"])), str(w["aviso"])) for w in legends.get("warnings", [])
        ]
        core = overlay.data("core_tables.yaml").get("tables", [])
        self._core = {str(c["name"]).lower(): c for c in core}
        self._modules = overlay.data("modules.yaml").get("modules", {})

    # --- utilidades -----------------------------------------------------------------------

    def _pack(self) -> Pack:
        return self._pack_provider()

    def _search(self, pack: Pack) -> SchemaSearch:
        if self._search_cache is None or self._search_cache[0] != pack.meta.version:
            self._search_cache = (pack.meta.version, SchemaSearch(pack, self._overlay))
        return self._search_cache[1]

    def _pack_info(self, pack: Pack) -> dict[str, Any]:
        info: dict[str, Any] = {"versao": pack.meta.short, "gerado_em": pack.meta.built_at}
        reason = self._stale_reason()
        if reason:
            info["desatualizado"] = reason
        return info

    def _warning_for(self, column: str) -> str | None:
        folded = fold(column)
        for pattern, aviso in self._warnings:
            if pattern.search(folded):
                return aviso
        return None

    def _legend_for(self, table_key: str, column: ColumnRow) -> tuple[str | None, str | None]:
        entry = self._legends.get(f"{table_key}.{column.key}")
        if entry:
            items = "; ".join(f"{k}={v}" for k, v in entry["valores"].items())
            return items, str(entry.get("confianca", "inferida"))
        if column.legend:
            return column.legend, "media"
        return None, None

    def _table_or_error(self, pack: Pack, name: str) -> Any:
        row = pack.table(name.strip())
        if row is None:
            raise ToolError(
                "tabela_desconhecida", f"a tabela {name!r} nao existe; use `buscar_esquema`"
            )
        return row

    def _cap(self, body: dict[str, Any], key: str, limit: int = MAX_BYTES) -> dict[str, Any]:
        """Corta a lista `body[key]` (de tras para frente) ate caber em `limit` bytes."""
        items = body[key]
        while items and size_of(body) > limit:
            items.pop()
            body["truncado"] = True
        return body

    # --- mapa_do_banco -----------------------------------------------------------------------

    def mapa_do_banco(self) -> dict[str, Any]:
        pack = self._pack()
        counts: dict[str, int] = {}
        for module, n in pack.query(
            "SELECT module, COUNT(*) FROM tables WHERE kind = 'BASE' "
            "AND COALESCE(blocked_reason, '') != 'tabela_de_credencial' GROUP BY module"
        ):
            counts[module] = n
        modules = [
            {"prefixo": m, "nome": info["nome"], "tabelas": counts.get(m, 0)}
            for m, info in self._modules.items()
            if counts.get(m)
        ]
        modules.sort(key=lambda x: -x["tabelas"])
        central = []
        for key, entry in self._core.items():
            row = pack.table(key)
            if row is None or (not row.queryable and row.blocked_reason == "tabela_de_credencial"):
                continue
            central.append(
                {
                    "tabela": row.name,
                    "titulo": entry.get("titulo"),
                    "linhas": row.approx_rows,
                }
            )
        central.sort(key=lambda x: -(x["linhas"] or 0))
        body: dict[str, Any] = {
            "banco": "Dominio (SAP SQL Anywhere 17), somente leitura",
            "pack": {
                **self._pack_info(pack),
                "tabelas": pack.meta.counts.get("tables"),
                "colunas": pack.meta.counts.get("columns"),
            },
            "modulos": modules[:14],
            "centrais": central[:22],
            "convencoes": [
                "o prefixo de 2 letras do nome da tabela e o modulo (ef, ct, fo, ge...)",
                "`codi_emp` e o codigo da empresa e filtra quase toda tabela de movimento",
                "segredo e dado pessoal nao saem; coluna nova fica bloqueada ate o dono aceitar",
                "toda descricao traz `fonte` e `confianca`: comentario do banco nao e legenda",
            ],
            "como_usar": [
                "buscar_esquema(consulta) acha tabelas por palavra do negocio",
                "descrever_tabela(tabela) lista colunas, chaves e legendas",
                "caminho_entre_tabelas(origem, destino) mostra a juncao por FK declarada",
                "consulta_estruturada(...) e as consultas verificadas leem os dados",
            ],
        }
        return self._cap(body, "centrais", MAP_BYTES) if size_of(body) > MAP_BYTES else body

    # --- buscar_esquema ---------------------------------------------------------------------

    def buscar_esquema(self, consulta: str, limite: int = 8) -> dict[str, Any]:
        if not consulta or not consulta.strip():
            raise ToolError(
                "consulta_vazia", "informe o que procura (ex.: 'notas fiscais de saida')"
            )
        pack = self._pack()
        hits = self._search(pack).search(consulta, limit=min(max(limite, 1), 8))
        cards = []
        for hit in hits:
            card: dict[str, Any] = {
                "tabela": hit.name,
                "modulo": hit.module,
                "descricao": _clip(hit.comment, CARD_COMMENT),
                "linhas_aprox": hit.approx_rows,
                "consultavel": hit.queryable,
                "fonte": "overlay" if hit.titulo else "comentario_do_banco",
                "confianca": "media",
            }
            if hit.titulo:
                card["titulo"] = hit.titulo
            if hit.kind != "BASE":
                card["tipo"] = hit.kind
            if hit.obsolete:
                card["aviso"] = "marcada como obsoleta no banco"
            if hit.blocked_reason:
                card["motivo_bloqueio"] = hit.blocked_reason
            cards.append(card)
        body: dict[str, Any] = {
            "pack": self._pack_info(pack),
            "resultados": cards,
            "proximo_passo": (
                "descrever_tabela(<tabela>) para ver colunas e chaves"
                if cards
                else "nenhuma tabela casou: tente outras palavras ou `mapa_do_banco`"
            ),
        }
        return self._cap(body, "resultados")

    # --- descrever_tabela --------------------------------------------------------------------

    def descrever_tabela(self, tabela: str, pagina: int = 1) -> dict[str, Any]:
        pack = self._pack()
        row = self._table_or_error(pack, tabela)
        if row.blocked_reason == "tabela_de_credencial":
            return {"tabela": row.name, "bloqueada": True, "motivo": "politica de dados"}
        core = self._core.get(row.key)
        columns = pack.columns(row.key)
        pk = set(row.pk)
        fk_cols: set[str] = set()
        out_fks = []
        in_fks = []
        for fk in pack.foreign_keys():
            if fk.child == row.key:
                fk_cols.update(fk.child_cols)
                out_fks.append(
                    {
                        "para": fk.parent,
                        "colunas": [
                            f"{a}->{b}" for a, b in zip(fk.child_cols, fk.parent_cols, strict=True)
                        ],
                    }
                )
            if fk.parent == row.key and fk.child != row.key:
                in_fks.append(
                    {
                        "de": fk.child,
                        "colunas": [
                            f"{a}<-{b}" for a, b in zip(fk.parent_cols, fk.child_cols, strict=True)
                        ],
                    }
                )

        def order(col: ColumnRow) -> tuple[int, int]:
            return (0 if col.key in pk else 1 if col.key in fk_cols else 2, col.position)

        columns.sort(key=order)
        page = max(1, pagina)
        window = columns[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
        items = [self._column_item(row.key, c, pk, fk_cols) for c in window]
        body: dict[str, Any] = {
            "tabela": row.name,
            "tipo": row.kind,
            "descricao": _clip(row.comment, 200),
            "titulo": core.get("titulo") if core else None,
            "modulo": row.module,
            "linhas_aprox": row.approx_rows,
            "consultavel": row.queryable,
            "chave_primaria": list(row.pk),
            "referencia": out_fks[:MAX_FK_LISTED],
            "referenciada_por": in_fks[:MAX_FK_LISTED],
            "indices": [
                {"nome": n, "colunas": list(c)}
                for n, c, _u, cat in pack.indexes(row.key)
                if cat != 2
            ][:MAX_INDEXES_LISTED],
            "colunas": {
                "pagina": page,
                "por_pagina": PAGE_SIZE,
                "total": len(columns),
                "itens": items,
            },
            "pack": self._pack_info(pack),
            "fonte": "overlay" if core else "comentario_do_banco",
            "confianca": "media",
        }
        if len(in_fks) > MAX_FK_LISTED:
            body["referenciada_por_total"] = len(in_fks)
        if row.blocked_reason:
            body["motivo_bloqueio"] = row.blocked_reason
        if row.obsolete:
            body["aviso"] = "marcada como obsoleta no banco"
        body = {k: v for k, v in body.items() if v is not None}
        more = page * PAGE_SIZE < len(columns)
        if more:
            body["proximo_passo"] = (
                f"descrever_tabela({row.name!r}, pagina={page + 1}) mostra mais colunas"
            )
        trimmed = self._cap_items(body)
        return trimmed

    def _cap_items(self, body: dict[str, Any]) -> dict[str, Any]:
        items = body["colunas"]["itens"]
        while items and size_of(body) > MAX_BYTES:
            items.pop()
            body["truncado"] = True
            body["proximo_passo"] = "resposta cortada em 12 KB: use `pagina` e `valores_do_campo`"
        return body

    def _column_item(
        self, table_key: str, column: ColumnRow, pk: set[str], fk_cols: set[str]
    ) -> dict[str, Any]:
        tipo = column.type
        if column.width:
            tipo += f"({column.width}" + (f",{column.scale}" if column.scale else "") + ")"
        item: dict[str, Any] = {"nome": column.name, "tipo": tipo}
        if column.klass is PolicyClass.SEGREDO:
            return {"nome": column.name, "classe": "segredo", "bloqueada": True}
        if column.key in pk:
            item["chave"] = "pk"
        elif column.key in fk_cols:
            item["chave"] = "fk"
        comment = _clip(column.comment, COMMENT_CHARS)
        if comment:
            item["comentario"] = comment
        legend, confidence = self._legend_for(table_key, column)
        if legend:
            item["legenda"] = _clip(legend, LEGEND_CHARS)
            item["legenda_confianca"] = confidence
        if column.klass is not PolicyClass.NORMAL:
            item["classe"] = column.klass.value + (f":{column.category}" if column.category else "")
        if column.klass in (PolicyClass.NAO_CLASSIFICADA,) or column.blocked_reason:
            item["bloqueada"] = True
            if column.blocked_reason:
                item["motivo"] = column.blocked_reason
        if column.unused:
            item["aviso"] = "marcada como nao utilizada no banco"
        warning = self._warning_for(column.name)
        if warning:
            item["aviso"] = warning
        return item

    # --- caminho_entre_tabelas ---------------------------------------------------------------

    def caminho_entre_tabelas(self, origem: str, destino: str) -> dict[str, Any]:
        pack = self._pack()
        src = self._table_or_error(pack, origem)
        dst = self._table_or_error(pack, destino)
        steps = find_path(pack, src.key, dst.key)
        if steps is None:
            return {
                "origem": src.name,
                "destino": dst.name,
                "caminho": None,
                "motivo": (
                    "nao ha juncao segura por FK declarada em ate 4 saltos; juntar por uma "
                    "tabela-pai compartilhada (subir e descer) multiplica linhas e nao e permitido"
                ),
            }
        return {
            "origem": src.name,
            "destino": dst.name,
            "saltos": len(steps),
            "caminho": [
                {
                    "de": s.from_table,
                    "para": s.to_table,
                    "colunas": [
                        f"{a} = {b}" for a, b in zip(s.from_columns, s.to_columns, strict=True)
                    ],
                    "relacao": "muitos_para_um" if s.direction == "up" else "um_para_muitos",
                }
                for s in steps
            ],
            "fonte": "chaves estrangeiras declaradas no banco",
            "confianca": "alta",
        }

    # --- valores_do_campo --------------------------------------------------------------------

    def valores_do_campo(self, tabela: str, coluna: str) -> dict[str, Any]:
        pack = self._pack()
        row = self._table_or_error(pack, tabela)
        column = pack.column(row.key, coluna.strip())
        if column is None or column.klass is PolicyClass.SEGREDO:
            raise ToolError("coluna_desconhecida", f"a coluna {coluna!r} nao existe em {row.name}")
        body: dict[str, Any] = {
            "tabela": row.name,
            "coluna": column.name,
            "tipo": column.type,
            "descricao": _clip(column.comment, 200),
        }
        legend, confidence = self._legend_for(row.key, column)
        if legend:
            body["legenda"] = legend
            body["fonte"] = (
                "overlay" if self._legends.get(f"{row.key}.{column.key}") else "comentario_do_banco"
            )
            body["confianca"] = confidence
        else:
            body["legenda"] = None
            body["proximo_passo"] = (
                "sem legenda no banco: veja os valores distintos com `consulta_estruturada` "
                "(agrupar_por na coluna, se a politica permitir)"
            )
        warning = self._warning_for(column.name)
        if warning:
            body["aviso"] = warning
        if column.unused:
            body["aviso"] = "marcada como nao utilizada no banco"
        return {k: v for k, v in body.items() if v is not None}
