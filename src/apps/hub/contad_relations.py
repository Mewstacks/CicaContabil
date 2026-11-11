"""Offline catalog evidence. Never infer financial meaning or enable collection."""

from __future__ import annotations

import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

TARGETS = frozenset(
    {
        "GEEMPRE",
        "CTCONTAS",
        "CTCONTACAIXA",
        "CTCONTACAIXA_CONTA_BANCARIA",
        "CTLANCTO",
        "CTCLANCTO",
        "CTCCUSTO",
        "EFCLIENTES",
        "EFFORNECE",
    }
)
TABLE_FIELDS = {"table_id", "table_name", "table_type"}
KEY_FIELDS = {
    "table_id",
    "index_id",
    "index_category",
    "unique_code",
    "not_enforced",
    "index_name",
    "sequence",
    "column_id",
    "column_name",
    "primary_column_id",
}
RELATION_FIELDS = {
    "foreign_table_id",
    "foreign_index_id",
    "primary_table_id",
    "primary_index_id",
    "foreign_schema",
    "foreign_table",
    "primary_schema",
    "primary_table",
    "match_type",
    "check_on_commit",
    "nulls",
    "sequence",
    "foreign_column_id",
    "foreign_column",
    "primary_column_id",
    "primary_column",
}
ROOT_FIELDS = {
    "version",
    "completed",
    "observed_at_utc",
    "schema",
    "targets",
    "tables",
    "key_columns",
    "relation_columns",
    "declared_metadata_only",
    "financial_semantics_approved",
    "business_values_selected",
    "agent_configuration_read",
    "erp_write_performed",
    "uploaded",
}


class CatalogEvidenceError(ValueError):
    """Invalid, incomplete or inconsistent catalog evidence; safe to display."""


def read_metadata_json(path: Path, *, max_bytes: int) -> dict[str, Any]:
    """Bound memory and reject duplicate JSON members rather than silently replacing them."""

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CatalogEvidenceError("JSON com membro duplicado.")
            result[key] = value
        return result

    try:
        with path.open("rb") as stream:
            content = stream.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise CatalogEvidenceError("Arquivo de metadados excede o limite.")
        value = json.loads(content.decode("utf-8-sig"), object_pairs_hook=unique)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, CatalogEvidenceError):
            raise
        raise CatalogEvidenceError("Não foi possível ler o JSON de metadados.") from None
    if not isinstance(value, dict):
        raise CatalogEvidenceError("Raiz de metadados incompatível.")
    return value


def _number(value: Any, *, maximum: int = 4294967295) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise CatalogEvidenceError("Número de catálogo incompatível.")
    return value


def _name(value: Any) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise CatalogEvidenceError("Identificador de catálogo incompatível.")
    if value != value.rstrip(" ") or any(unicodedata.category(c).startswith("C") for c in value):
        raise CatalogEvidenceError("Identificador de catálogo incompatível.")
    return value


def _rows(value: Any, fields: set[str], limit: int) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > limit:
        raise CatalogEvidenceError("Quantidade de metadados incompatível.")
    if any(not isinstance(row, dict) or set(row) != fields for row in value):
        raise CatalogEvidenceError("Campos de catálogo incompatíveis.")
    return value


def _ordered(rows: list[dict[str, Any]], column_field: str) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: row["sequence"])
    if [row["sequence"] for row in ordered] != list(range(len(ordered))):
        raise CatalogEvidenceError("Ordem de chave incompleta ou duplicada.")
    if len({row[column_field] for row in ordered}) != len(ordered):
        raise CatalogEvidenceError("Coluna repetida na chave.")
    return ordered


def analyze_catalog(report: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    """Cross-check explicit catalog IDs/names with the earlier column inventory.

    SQL Anywhere column IDs may have gaps: ODBC ordinal positions must never be
    used as column IDs. FK target columns follow primary_column_id, not the order
    of a guessed primary key. Unreported relationships remain unknown.
    """
    if set(report) != ROOT_FIELDS or report.get("version") != "contad-relations-v1":
        raise CatalogEvidenceError("Versão do complemento incompatível.")
    for flag, expected in {
        "completed": True,
        "declared_metadata_only": True,
        "financial_semantics_approved": False,
        "business_values_selected": False,
        "agent_configuration_read": False,
        "erp_write_performed": False,
        "uploaded": False,
    }.items():
        if report[flag] is not expected:
            raise CatalogEvidenceError("Proveniência do complemento incompatível.")
    if report["schema"] != "bethadba" or not isinstance(report["targets"], list):
        raise CatalogEvidenceError("Seleção de catálogo incompatível.")
    targets = [_name(value).upper() for value in report["targets"]]
    if len(targets) != len(TARGETS) or set(targets) != TARGETS:
        raise CatalogEvidenceError("Seleção de catálogo incompatível.")
    if inventory.get("version") != "contad-schema-inventory-v1":
        raise CatalogEvidenceError("Versão do inventário incompatível.")
    objects = inventory.get("objects")
    if not isinstance(objects, list) or len(objects) > 1500:
        raise CatalogEvidenceError("Inventário incompatível.")
    columns: dict[tuple[str, str], set[str]] = {}
    for obj in objects:
        if not isinstance(obj, dict):
            raise CatalogEvidenceError("Objeto do inventário incompatível.")
        inventory_identity = (
            _name(obj.get("schema")).casefold(),
            _name(obj.get("name")).casefold(),
        )
        if inventory_identity in columns:
            raise CatalogEvidenceError("Objeto duplicado no inventário.")
        source_columns = obj.get("columns")
        if not isinstance(source_columns, list) or len(source_columns) > 50000:
            raise CatalogEvidenceError("Colunas do inventário incompatíveis.")
        names = [
            _name(col.get("name")).casefold() for col in source_columns if isinstance(col, dict)
        ]
        if len(names) != len(source_columns) or len(set(names)) != len(names):
            raise CatalogEvidenceError("Coluna duplicada ou incompatível no inventário.")
        columns[inventory_identity] = set(names)

    tables = _rows(report["tables"], TABLE_FIELDS, 9)
    if len(tables) != len(TARGETS):
        raise CatalogEvidenceError("Conjunto de tabelas incompleto.")
    by_id: dict[int, str] = {}
    for selected_table in tables:
        table_id = _number(selected_table["table_id"])
        name = _name(selected_table["table_name"])
        if selected_table["table_type"] != 1 or type(selected_table["table_type"]) is not int:
            raise CatalogEvidenceError("Objeto não é tabela base.")
        if table_id in by_id or name.upper() not in TARGETS:
            raise CatalogEvidenceError("Identidade de tabela incompatível.")
        by_id[table_id] = name
    if {name.upper() for name in by_id.values()} != TARGETS:
        raise CatalogEvidenceError("Tabela duplicada ou ausente.")
    if any(("bethadba", name.casefold()) not in columns for name in by_id.values()):
        raise CatalogEvidenceError("Tabela não confrontada com o inventário.")

    def check_column(schema: str, table: str, column: str) -> None:
        # One-hop external references need not be in the original inventory.
        known = columns.get((schema.casefold(), table.casefold()))
        if known is not None and column.casefold() not in known:
            raise CatalogEvidenceError("Coluna diverge do inventário recebido.")

    key_groups: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    column_ids: dict[tuple[int, int], str] = {}
    column_names: dict[tuple[int, str], int] = {}

    def bind_column(table_id: int, column_id: int, name: str) -> None:
        identity = (table_id, column_id)
        reverse = (table_id, name.casefold())
        if column_ids.get(identity, name.casefold()) != name.casefold():
            raise CatalogEvidenceError("ID de coluna com nomes conflitantes.")
        if column_names.get(reverse, column_id) != column_id:
            raise CatalogEvidenceError("Nome de coluna com IDs conflitantes.")
        column_ids[identity] = name.casefold()
        column_names[reverse] = column_id

    for row in _rows(report["key_columns"], KEY_FIELDS, 1024):
        for field in ("table_id", "index_id", "column_id"):
            _number(row[field])
        _number(row["sequence"], maximum=32767)
        if row["table_id"] not in by_id:
            raise CatalogEvidenceError("Chave fora da seleção.")
        if _number(row["index_category"], maximum=3) not in {1, 2, 3}:
            raise CatalogEvidenceError("Categoria de índice incompatível.")
        unique = _number(row["unique_code"], maximum=5)
        if row["index_category"] == 3 and unique not in {1, 2, 5}:
            raise CatalogEvidenceError("Índice secundário sem unicidade selecionado.")
        if row["primary_column_id"] is not None:
            _number(row["primary_column_id"])
        if row["not_enforced"] is not None:
            _name(row["not_enforced"])
        _name(row["index_name"])
        name = _name(row["column_name"])
        bind_column(row["table_id"], row["column_id"], name)
        check_column("bethadba", by_id[row["table_id"]], name)
        key_groups[(row["table_id"], row["index_id"])].append(row)
    for identity, rows in key_groups.items():
        for field in ("index_category", "unique_code", "not_enforced", "index_name"):
            if len({row[field] for row in rows}) != 1:
                raise CatalogEvidenceError("Definição de índice inconsistente.")
        key_groups[identity] = _ordered(rows, "column_id")
        if rows[0]["index_category"] == 1 and rows[0]["unique_code"] not in {1, 2, 5}:
            raise CatalogEvidenceError("Chave primária sem unicidade.")
    for table_id in by_id:
        if (
            sum(
                identity[0] == table_id and rows[0]["index_category"] == 1
                for identity, rows in key_groups.items()
            )
            > 1
        ):
            raise CatalogEvidenceError("Mais de uma chave primária para a tabela.")

    relations: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    table_names = {table_id: ("bethadba", name.casefold()) for table_id, name in by_id.items()}
    table_ids = {identity: table_id for table_id, identity in table_names.items()}
    for row in _rows(report["relation_columns"], RELATION_FIELDS, 2048):
        for field in (
            "foreign_table_id",
            "foreign_index_id",
            "primary_table_id",
            "primary_index_id",
            "foreign_column_id",
            "primary_column_id",
        ):
            _number(row[field])
        _number(row["sequence"], maximum=32767)
        if _number(row["match_type"], maximum=255) not in {0, 1, 2, 129, 130}:
            raise CatalogEvidenceError("Modo de relação incompatível.")
        for flag in ("check_on_commit", "nulls"):
            if not isinstance(row[flag], str) or row[flag] not in {"Y", "N"}:
                raise CatalogEvidenceError("Flags da relação incompatíveis.")
        for side in ("foreign", "primary"):
            schema, table, column = (
                _name(row[f"{side}_{part}"]) for part in ("schema", "table", "column")
            )
            table_id = row[f"{side}_table_id"]
            table_identity = (schema.casefold(), table.casefold())
            if (
                table_names.get(table_id, table_identity) != table_identity
                or table_ids.get(table_identity, table_id) != table_id
            ):
                raise CatalogEvidenceError("Identidade de tabela conflitante na relação.")
            table_names[table_id] = table_identity
            table_ids[table_identity] = table_id
            if table_id in by_id and (
                schema != "bethadba" or table.casefold() != by_id[table_id].casefold()
            ):
                raise CatalogEvidenceError("Identidade da relação diverge das tabelas.")
            if (
                schema.casefold() == "bethadba"
                and table.upper() in TARGETS
                and table_id not in by_id
            ):
                raise CatalogEvidenceError("Tabela da relação com ID conflitante.")
            bind_column(table_id, row[f"{side}_column_id"], column)
            check_column(schema, table, column)
        if row["foreign_table_id"] not in by_id and row["primary_table_id"] not in by_id:
            raise CatalogEvidenceError("Relação fora da seleção.")
        relations[(row["foreign_table_id"], row["foreign_index_id"])].append(row)

    relation_output = []
    for identity, rows in sorted(relations.items()):
        for field in RELATION_FIELDS - {
            "sequence",
            "foreign_column_id",
            "foreign_column",
            "primary_column_id",
            "primary_column",
        }:
            if len({row[field] for row in rows}) != 1:
                raise CatalogEvidenceError("Definição de relação inconsistente.")
        ordered = _ordered(rows, "foreign_column_id")
        head = ordered[0]
        if len({row["primary_column_id"] for row in ordered}) != len(ordered):
            raise CatalogEvidenceError("Coluna alvo repetida na relação.")
        if head["foreign_table_id"] in by_id:
            source_key = key_groups.get(identity, [])
            if (
                not source_key
                or source_key[0]["index_category"] != 2
                or [(r["column_id"], r["primary_column_id"]) for r in source_key]
                != [(r["foreign_column_id"], r["primary_column_id"]) for r in ordered]
            ):
                raise CatalogEvidenceError("Relação diverge do índice estrangeiro.")
        target_key = key_groups.get((head["primary_table_id"], head["primary_index_id"]))
        if head["primary_table_id"] in by_id and (
            not target_key
            or target_key[0]["unique_code"] not in {1, 2, 5}
            or {r["column_id"] for r in target_key} != {r["primary_column_id"] for r in ordered}
        ):
            raise CatalogEvidenceError("Relação sem chave alvo única correspondente.")
        relation_output.append(
            {
                "foreign_schema": head["foreign_schema"],
                "foreign_table": head["foreign_table"],
                "foreign_index_id": head["foreign_index_id"],
                "primary_schema": head["primary_schema"],
                "primary_table": head["primary_table"],
                "primary_index_id": head["primary_index_id"],
                "match_type": head["match_type"],
                "check_on_commit": head["check_on_commit"],
                "nulls": head["nulls"],
                "target_key_in_selection": target_key is not None,
                "columns": [
                    {
                        "sequence": r["sequence"],
                        "foreign": r["foreign_column"],
                        "primary": r["primary_column"],
                    }
                    for r in ordered
                ],
            }
        )
    for identity, rows in key_groups.items():
        if rows[0]["index_category"] == 2 and identity not in relations:
            raise CatalogEvidenceError("Índice estrangeiro sem relação correspondente.")

    return {
        "version": "contad-relations-analysis-v1",
        "catalog_consistent": True,
        "tables": [
            {
                "name": by_id[table_id],
                "keys": [
                    {
                        "index_id": identity[1],
                        "name": rows[0]["index_name"],
                        "category": rows[0]["index_category"],
                        "unique_code": rows[0]["unique_code"],
                        "not_enforced_raw": rows[0]["not_enforced"],
                        "columns": [r["column_name"] for r in rows],
                    }
                    for identity, rows in sorted(key_groups.items())
                    if identity[0] == table_id
                ],
            }
            for table_id in sorted(by_id)
        ],
        "declared_relations": relation_output,
        "human_reviewed": False,
        "financial_collection_enabled": False,
        "limitations": [
            "undeclared_relationships_unknown",
            "financial_semantics_unapproved",
            "shared_chart_unapproved",
            "titles_source_unapproved",
            "status_M_unclassified",
            "metadata_is_not_financial_acceptance",
        ],
    }
