from __future__ import annotations

import json
import stat
from copy import deepcopy

import pytest
from scripts.analyze_contad_relations import main

from apps.hub.contad_relations import (
    TARGETS,
    CatalogEvidenceError,
    analyze_catalog,
    read_metadata_json,
)


def evidence():
    tables = [
        {"table_id": i + 100, "table_name": name, "table_type": 1}
        for i, name in enumerate(sorted(TARGETS))
    ]
    ids = {row["table_name"]: row["table_id"] for row in tables}
    keys = []
    # Target PK order deliberately differs from the FK mapping. IDs have gaps.
    for table, index, category, column_ids, names, primary_ids in [
        ("CTCONTAS", 0, 1, [7, 19], ["CODI_EMP", "CODI_CTA"], [None, None]),
        ("CTLANCTO", 2, 2, [23, 42], ["CDEB_LAN", "CODI_EMP_PLANO"], [19, 7]),
    ]:
        for seq, (column_id, name, primary_id) in enumerate(
            zip(column_ids, names, primary_ids, strict=True)
        ):
            keys.append(
                {
                    "table_id": ids[table],
                    "index_id": index,
                    "index_category": category,
                    "unique_code": 1 if category == 1 else 4,
                    "not_enforced": "N",
                    "index_name": "PRIMARY" if category == 1 else "fk_debit",
                    "sequence": seq,
                    "column_id": column_id,
                    "column_name": name,
                    "primary_column_id": primary_id,
                }
            )
    relations = [
        {
            "foreign_table_id": ids["CTLANCTO"],
            "foreign_index_id": 2,
            "primary_table_id": ids["CTCONTAS"],
            "primary_index_id": 0,
            "foreign_schema": "bethadba",
            "foreign_table": "CTLANCTO",
            "primary_schema": "bethadba",
            "primary_table": "CTCONTAS",
            "match_type": 0,
            "check_on_commit": "N",
            "nulls": "N",
            "sequence": i,
            "foreign_column_id": row["column_id"],
            "foreign_column": row["column_name"],
            "primary_column_id": row["primary_column_id"],
            "primary_column": target,
        }
        for i, (row, target) in enumerate(zip(keys[2:], ["CODI_CTA", "CODI_EMP"], strict=True))
    ]
    inventory = {
        "version": "contad-schema-inventory-v1",
        "objects": [
            {
                "schema": "bethadba",
                "name": table["table_name"],
                "columns": [
                    {"name": row["column_name"], "ordinal": seq + 1}
                    for seq, row in enumerate(keys)
                    if row["table_id"] == table["table_id"]
                ],
            }
            for table in tables
        ],
    }
    report = {
        "version": "contad-relations-v1",
        "completed": True,
        "observed_at_utc": "2026-11-11T19:00:00Z",
        "schema": "bethadba",
        "targets": sorted(TARGETS),
        "tables": tables,
        "key_columns": keys,
        "relation_columns": relations,
        "declared_metadata_only": True,
        "financial_semantics_approved": False,
        "business_values_selected": False,
        "agent_configuration_read": False,
        "erp_write_performed": False,
        "uploaded": False,
    }
    return report, inventory


def test_preserves_composite_order_and_explicit_target_mapping_without_inference():
    report, inventory = evidence()
    before = deepcopy((report, inventory))
    report["key_columns"].reverse()
    report["relation_columns"].reverse()
    result = analyze_catalog(report, inventory)
    assert result["catalog_consistent"] is True
    assert result["declared_relations"][0]["columns"] == [
        {"sequence": 0, "foreign": "CDEB_LAN", "primary": "CODI_CTA"},
        {"sequence": 1, "foreign": "CODI_EMP_PLANO", "primary": "CODI_EMP"},
    ]
    assert not result["human_reviewed"]
    assert not result["financial_collection_enabled"]
    assert "shared_chart_unapproved" in result["limitations"]
    assert inventory == before[1]


def test_absent_constraints_remain_unknown():
    report, inventory = evidence()
    report["key_columns"] = []
    report["relation_columns"] = []
    result = analyze_catalog(report, inventory)
    assert result["declared_relations"] == []
    assert all(table["keys"] == [] for table in result["tables"])
    assert "undeclared_relationships_unknown" in result["limitations"]
    assert not result["financial_collection_enabled"]


@pytest.mark.parametrize(
    "case",
    [
        "duplicate_table_id",
        "duplicate_table_name",
        "missing_table",
        "wrong_table_kind",
        "extra_target",
        "duplicate_target",
        "wrong_version",
        "partial",
        "false_approval",
        "business_values",
        "extra_field",
        "column_name_conflict",
        "missing_inventory_column",
        "duplicate_inventory_object",
        "duplicate_inventory_column",
        "gap_sequence",
        "duplicate_sequence",
        "duplicate_key_column",
        "inconsistent_index",
        "missing_relation",
        "missing_foreign_index",
        "foreign_index_mismatch",
        "missing_target_key",
        "nonunique_primary",
        "duplicate_primary_key",
        "wrong_target_key",
        "null_target_column",
        "inconsistent_relation",
        "relation_name_conflict",
        "table_name_conflict",
        "foreign_flag",
        "invalid_match",
        "bool_number",
        "oversized_keys",
        "oversized_relations",
        "control_name",
    ],
)
def test_refuses_incomplete_or_conflicting_catalog(case):
    report, inventory = evidence()
    keys, relations, tables = (report["key_columns"], report["relation_columns"], report["tables"])
    if case == "duplicate_table_id":
        tables[1]["table_id"] = tables[0]["table_id"]
    elif case == "duplicate_table_name":
        tables[1]["table_name"] = tables[0]["table_name"]
    elif case == "missing_table":
        tables.pop()
    elif case == "wrong_table_kind":
        tables[0]["table_type"] = 21
    elif case == "extra_target":
        report["targets"].append("OTHER")
    elif case == "duplicate_target":
        report["targets"][0] = report["targets"][1]
    elif case == "wrong_version":
        report["version"] = "unknown"
    elif case == "partial":
        report["completed"] = False
    elif case == "false_approval":
        report["financial_semantics_approved"] = True
    elif case == "business_values":
        report["business_values_selected"] = True
    elif case == "extra_field":
        report["password"] = "synthetic-secret"
    elif case == "column_name_conflict":
        relations[0]["primary_column"] = "CODI_EMP"
    elif case == "missing_inventory_column":
        next(o for o in inventory["objects"] if o["name"] == "CTCONTAS")["columns"] = []
    elif case == "duplicate_inventory_object":
        inventory["objects"].append(inventory["objects"][0])
    elif case == "duplicate_inventory_column":
        next(o for o in inventory["objects"] if o["name"] == "CTCONTAS")["columns"] *= 2
    elif case == "gap_sequence":
        keys[0]["sequence"] = 9
    elif case == "duplicate_sequence":
        keys[1]["sequence"] = 0
    elif case == "duplicate_key_column":
        keys[1]["column_id"] = keys[0]["column_id"]
    elif case == "inconsistent_index":
        keys[1]["index_name"] = "other"
    elif case == "missing_relation":
        report["relation_columns"] = []
    elif case == "missing_foreign_index":
        del keys[2:]
    elif case == "foreign_index_mismatch":
        keys[2]["primary_column_id"] = 7
    elif case == "missing_target_key":
        del keys[:2]
    elif case == "nonunique_primary":
        keys[0]["unique_code"] = keys[1]["unique_code"] = 4
    elif case == "duplicate_primary_key":
        keys.extend([{**row, "index_id": 1} for row in keys[:2]])
    elif case == "wrong_target_key":
        relations[0]["primary_index_id"] = relations[1]["primary_index_id"] = 1
    elif case == "null_target_column":
        relations[0]["primary_column_id"] = None
    elif case == "inconsistent_relation":
        relations[1]["match_type"] = 1
    elif case == "relation_name_conflict":
        relations[0]["foreign_column"] = "CODI_EMP_PLANO"
    elif case == "table_name_conflict":
        relations[0]["primary_table"] = "GEEMPRE"
    elif case == "foreign_flag":
        relations[0]["nulls"] = []
    elif case == "invalid_match":
        relations[0]["match_type"] = 3
    elif case == "bool_number":
        keys[0]["column_id"] = True
    elif case == "oversized_keys":
        report["key_columns"] *= 300
    elif case == "oversized_relations":
        report["relation_columns"] *= 1100
    elif case == "control_name":
        keys[0]["column_name"] = "bad\nname"
    with pytest.raises(CatalogEvidenceError):
        analyze_catalog(report, inventory)


def test_one_hop_reference_outside_inventory_is_explicitly_unchecked():
    report, inventory = evidence()
    for row in report["relation_columns"]:
        row.update(primary_table_id=900, primary_table="external_chart", primary_schema="other")
    result = analyze_catalog(report, inventory)
    assert not result["declared_relations"][0]["target_key_in_selection"]
    assert not result["financial_collection_enabled"]


@pytest.mark.parametrize(
    "content,limit",
    [
        (b'{"version":1,"version":2}', 100),
        (b"{} " * 30, 10),
        (b"[]", 100),
        (b"\xff", 100),
        (b"{", 100),
        (b"[" * 2000, 4000),
    ],
)
def test_bounded_json_refuses_duplicates_invalid_encoding_and_depth(tmp_path, content, limit):
    path = tmp_path / "metadata.json"
    path.write_bytes(content)
    with pytest.raises(CatalogEvidenceError):
        read_metadata_json(path, max_bytes=limit)


def test_cli_private_report_never_overwrites_or_echoes_rejected_values(tmp_path, capsys):
    report, inventory = evidence()
    catalog, source, output = [
        tmp_path / name for name in ("catalog.json", "inventory.json", "out.json")
    ]
    catalog.write_text(json.dumps(report))
    source.write_text(json.dumps(inventory))
    args = ["--catalog", str(catalog), "--inventory", str(source), "--output", str(output)]
    assert main(args) == 0
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    before = output.read_bytes()
    assert main(args) == 1
    assert output.read_bytes() == before
    report["password"] = "synthetic-hidden-password"
    catalog.write_text(json.dumps(report))
    assert main(args) == 1
    captured = capsys.readouterr()
    assert "synthetic-hidden-password" not in captured.out + captured.err
    assert output.read_bytes() == before
