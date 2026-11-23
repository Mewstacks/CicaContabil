"""Catalog-only extension preserves exact key mappings and bounded text transport."""

import base64
import gzip
import hashlib
import json
import stat
from copy import deepcopy

import pytest
from scripts.analyze_contad_titles import main

from apps.hub.contad_relations import CatalogEvidenceError
from apps.hub.title_catalog import FAMILY, FLAGS, analyze_title_catalog, decode_title_catalog
from test_contad_relations import evidence


def catalog():
    original, inventory = evidence()
    names = {"CTCONTAS": "efentradas", "CTLANCTO": "efentradaspar"}
    table_ids = {row["table_id"] for row in original["tables"] if row["table_name"] in names}
    objects = []
    for table in original["tables"]:
        if table["table_id"] not in table_ids:
            continue
        cols = next(o["columns"] for o in inventory["objects"] if o["name"] == table["table_name"])
        objects.append(
            {
                "table_id": table["table_id"],
                "name": names[table["table_name"]],
                "columns": [
                    {
                        "name": c["name"],
                        "type": "integer",
                        "size": "10",
                        "nullable": 0,
                        "decimal_digits": "0",
                    }
                    for c in cols
                ],
            }
        )
    relations = deepcopy(original["relation_columns"])
    for row in relations:
        row["foreign_table"] = names[row["foreign_table"]]
        row["primary_table"] = names[row["primary_table"]]
    return {
        "version": "contad-title-catalog-v1",
        "observed_at_utc": "2026-11-12T16:00:00Z",
        "schema": "bethadba",
        "family": FAMILY,
        "objects": objects,
        "key_columns": original["key_columns"],
        "relation_columns": relations,
        **FLAGS,
    }


def test_fiscal_catalog_keeps_composite_pairs_and_does_not_approve_financial_source():
    payload = catalog()
    result = analyze_title_catalog(payload)
    assert result["catalog_consistent"] and result["column_count"] == 4
    assert result["financial_collection_enabled"] is result["human_reviewed"] is False
    assert result["column_evidence"] == "same_catalog_run_not_independent_business_review"
    assert result["declared_relations"][0]["columns"] == [
        {"sequence": 0, "foreign": "CDEB_LAN", "primary": "CODI_CTA"},
        {"sequence": 1, "foreign": "CODI_EMP_PLANO", "primary": "CODI_EMP"},
    ]


def transport(payload):
    content = json.dumps(payload).encode()
    return {
        "version": "contad-title-catalog-transfer-v1",
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "encoding": "gzip-base64",
        "data": base64.b64encode(gzip.compress(content)).decode(),
    }


def test_compact_transport_round_trip_is_hash_checked_and_private(tmp_path):
    payload = catalog()
    source, destination = tmp_path / "transport.json", tmp_path / "analysis.json"
    source.write_text(json.dumps(transport(payload)))
    assert decode_title_catalog(source.read_bytes()) == payload
    assert main(["--input", str(source), "--output", str(destination)]) == 0
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert json.loads(destination.read_text())["column_count"] == 4
    before = destination.read_bytes()
    assert main(["--input", str(source), "--output", str(destination)]) == 1
    assert destination.read_bytes() == before


@pytest.mark.parametrize(
    "key,value",
    [
        ("sha256", "0" * 64),
        ("bytes", 0),
        ("bytes", True),
        ("bytes", 4194305),
        ("data", "***"),
        ("encoding", "other"),
    ],
)
def test_transport_rejects_mismatch_or_invalid_limits(key, value):
    payload = transport(catalog())
    payload[key] = value
    with pytest.raises(CatalogEvidenceError):
        decode_title_catalog(json.dumps(payload).encode())


@pytest.mark.parametrize("flag", list(FLAGS))
def test_financial_or_incomplete_reports_cannot_enter_catalog_analysis(flag):
    payload = catalog()
    payload[flag] = not FLAGS[flag]
    with pytest.raises(CatalogEvidenceError):
        analyze_title_catalog(payload)


def test_unknown_family_column_and_broken_fk_mapping_are_rejected():
    payload = catalog()
    payload["objects"][0]["name"] = "HRLANCAMENTO_PAGAR"
    with pytest.raises(CatalogEvidenceError):
        analyze_title_catalog(payload)
    payload = catalog()
    payload["objects"][0]["columns"][0]["name"] = "unknown_column"
    with pytest.raises(CatalogEvidenceError):
        analyze_title_catalog(payload)
    payload = catalog()
    payload["relation_columns"][0]["primary_column_id"] = 123
    with pytest.raises(CatalogEvidenceError):
        analyze_title_catalog(payload)


def test_duplicate_json_members_and_truncated_gzip_are_rejected():
    with pytest.raises(CatalogEvidenceError):
        decode_title_catalog(b'{"version":"a","version":"b"}')
    payload = transport(catalog())
    payload["data"] = base64.b64encode(gzip.compress(b"synthetic")[:5]).decode()
    with pytest.raises(CatalogEvidenceError):
        decode_title_catalog(json.dumps(payload).encode())
