"""Bounded fiscal-title metadata analysis; never a business-row or ERP adapter."""

from __future__ import annotations

import base64
import binascii
import gzip
import hashlib
import io
import json
import re
from typing import Any

from apps.hub.contad_relations import CatalogEvidenceError, _analyze_catalog, _name, _number

MAX_BYTES = 4 * 1024 * 1024
FAMILY = r"^ef(entradas|saidas|servicos)(par|pag|_lancto|pag_lancto)?$"
FLAGS = {
    "completed": True,
    "declared_metadata_only": True,
    "financial_semantics_approved": False,
    "business_values_selected": False,
    "agent_configuration_read": False,
    "erp_write_performed": False,
    "uploaded": False,
}


def _json(content: bytes) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    try:
        if not 1 <= len(content) <= MAX_BYTES:
            raise ValueError
        value = json.loads(content.decode("utf-8-sig"), object_pairs_hook=unique)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise CatalogEvidenceError("JSON do complemento fiscal incompatível.") from None


def decode_title_catalog(content: bytes) -> dict[str, Any]:
    """Accept the private original or its hash-checked, size-bounded text transport."""
    value = _json(content)
    if value.get("version") != "contad-title-catalog-transfer-v1":
        return value
    if (
        set(value) != {"version", "sha256", "bytes", "encoding", "data"}
        or value["encoding"] != "gzip-base64"
        or type(value["bytes"]) is not int
        or not 1 <= value["bytes"] <= MAX_BYTES
        or not isinstance(value["data"], str)
        or not isinstance(value["sha256"], str)
    ):
        raise CatalogEvidenceError("Transporte do complemento fiscal incompatível.")
    try:
        packed = base64.b64decode(value["data"], validate=True)
        with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) != value["bytes"] or hashlib.sha256(raw).hexdigest() != value["sha256"]:
            raise ValueError
    except (ValueError, OSError, EOFError, binascii.Error):
        raise CatalogEvidenceError("Hash ou conteúdo do complemento fiscal divergente.") from None
    return _json(raw)


def analyze_title_catalog(report: dict[str, Any]) -> dict[str, Any]:
    if (
        set(report)
        != {
            "version",
            "observed_at_utc",
            "schema",
            "family",
            "objects",
            "key_columns",
            "relation_columns",
            *FLAGS,
        }
        or report["version"] != "contad-title-catalog-v1"
        or report["schema"] != "bethadba"
        or report["family"] != FAMILY
        or any(report[k] is not v for k, v in FLAGS.items())
    ):
        raise CatalogEvidenceError("Escopo/proveniência do complemento fiscal incompatível.")
    objects = report["objects"]
    if not isinstance(objects, list) or not 1 <= len(objects) <= 15:
        raise CatalogEvidenceError("Família fiscal vazia ou acima do limite.")
    names, ids = set(), set()
    inventory = []
    tables = []
    column_count = 0
    for obj in objects:
        if not isinstance(obj, dict) or set(obj) != {"table_id", "name", "columns"}:
            raise CatalogEvidenceError("Campos de objeto fiscal incompatíveis.")
        name = _name(obj["name"])
        table_id = _number(obj["table_id"])
        if not re.fullmatch(FAMILY, name, re.I) or name.upper() in names or table_id in ids:
            raise CatalogEvidenceError("Objeto fora da família ou identidade duplicada.")
        names.add(name.upper())
        ids.add(table_id)
        columns = obj["columns"]
        if not isinstance(columns, list) or not 1 <= len(columns) <= 1000:
            raise CatalogEvidenceError("Colunas fiscais ausentes ou acima do limite.")
        seen = set()
        for col in columns:
            if not isinstance(col, dict) or set(col) != {
                "name",
                "type",
                "size",
                "nullable",
                "decimal_digits",
            }:
                raise CatalogEvidenceError("Campos de coluna fiscal incompatíveis.")
            column_name = _name(col["name"]).casefold()
            if column_name in seen:
                raise CatalogEvidenceError("Coluna fiscal duplicada.")
            seen.add(column_name)
            _name(col["type"])
            _number(col["nullable"], maximum=2)
            for field in ("size", "decimal_digits"):
                if not isinstance(col[field], str) or not re.fullmatch(r"[0-9]{0,10}", col[field]):
                    raise CatalogEvidenceError("Tipo/tamanho de coluna fiscal incompatível.")
        column_count += len(columns)
        inventory.append({"schema": "bethadba", "name": name, "columns": columns})
        tables.append({"table_id": table_id, "table_name": name, "table_type": 1})
    if column_count > 15000:
        raise CatalogEvidenceError("Colunas fiscais excedem limite global.")
    # Reuse the proven FK-pair/order/uniqueness checks. The columns here come
    # from this same catalog run: this is internal consistency, not an independent
    # observation or evidence of the business meaning of any payment table.
    normalized = {
        **FLAGS,
        "version": "contad-relations-v1",
        "observed_at_utc": report["observed_at_utc"],
        "schema": "bethadba",
        "targets": sorted(names),
        "tables": tables,
        "key_columns": report["key_columns"],
        "relation_columns": report["relation_columns"],
    }
    result = _analyze_catalog(
        normalized,
        {"version": "contad-schema-inventory-v1", "objects": inventory},
        expected_targets=frozenset(names),
        key_limit=2048,
        relation_limit=4096,
    )
    return {
        **result,
        "version": "contad-title-catalog-analysis-v1",
        "family": FAMILY,
        "column_inventory": objects,
        "column_count": column_count,
        "column_evidence": "same_catalog_run_not_independent_business_review",
        "financial_collection_enabled": False,
        "human_reviewed": False,
    }
