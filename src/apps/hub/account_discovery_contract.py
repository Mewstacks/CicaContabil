"""Strict, bounded public contract for the D-373 read-only chart discovery."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any, cast

from apps.hub import account_source_contract as details
from apps.hub.contad_relations import KEY_FIELDS, RELATION_FIELDS, TABLE_FIELDS

Invalid = details.Invalid
require = details.require
integer = details.integer
keys = details.keys


def text(value: Any, length: int, nullable: bool = False) -> None:
    """Preserve well-formed source Unicode, including controls; count UTF-16 units."""
    if nullable and value is None:
        return
    require(type(value) is str, "TEXT_TYPE")
    try:
        encoded = value.encode("utf-16-le", errors="strict")
    except UnicodeError:
        raise Invalid("INVALID_SURROGATE") from None
    require(len(encoded) // 2 <= length, "TEXT_LENGTH")


def digest(value: Any) -> str:
    return hashlib.sha256(details.canonical(value).encode()).hexdigest()


LIMIT = 67_108_864
VERSION = "contad-chart-discovery-v1"
SCRIPT_SHA = "b114b0c612e23c0d535be3f4177b08f055ea4a08b560381e10f96436bc116ba2"
PERIOD_START = "2026-09-01"
PERIOD_END = "2026-12-01"
FALSE_FLAGS = (*details.FALSE_FLAGS, "nature_interpreted", "chart_owner_mapping_inferred")
PROVENANCE = {
    **details.PROVENANCE,
    "observed_chart_usage": (
        "CTLANCTO.(codi_emp,CODI_EMP_PLANO,fili_lan,YEAR(data_lan),MONTH(data_lan)); "
        "grouped codes and counts within declared period only"
    ),
    "chart_accounts": (
        "Complete CTCONTAS per union of own/CODI_PAD/observed/configured/equivalent chart owners; "
        "no name/type/status filtering"
    ),
    "company_parameters": (
        "CTPARMTO literal CODI_PAD,COMP_PAD,I_PLANOCONTAS,CCXA_PAR,FILI_PAR; "
        "no active-plan or cash mapping inferred"
    ),
    "plan_template_accounts": (
        "CTPLANOCONTAS literal accounts per owner/I_PLANOCONTAS; not substituted for CTCONTAS"
    ),
    "nature_rules": (
        "CTNATUREZA_CONTA literal codi_emp,ordem,clas_cta,natureza,grupo; "
        "no prefix, precedence or debit/credit interpretation"
    ),
    "equivalent_accounts": (
        "CTCONTAS_EQUIVALENTES.(CODI_EMP_PLANO,CODI_CTA) -> CTCONTAS.(codi_emp,codi_cta); "
        "company reference only"
    ),
}
COMPANY_FIELDS = {
    "company_code",
    "configuration_rows",
    "codi_pad_raw",
    "comp_pad_raw",
    "i_planocontas_raw",
    "cash_account_parameter_raw",
    "branch_parameter_raw",
}
CHART_FIELDS = {
    "chart_company_code",
    "account_code",
    "account_name_raw",
    "classification_raw",
    "account_type_raw",
    "account_status_raw",
    "inactive_on_raw",
}
USAGE_FIELDS = {
    "company_code",
    "chart_company_code",
    "branch_code",
    "year",
    "month",
    "entry_count",
}
TARGETS = {
    "CTPARMTO",
    "CTPLANOCONTAS",
    "CTNATUREZA_CONTA",
    "CTCONTACAIXA",
    "CTCONTACAIXA_CONTA_BANCARIA",
    "CTPARMTO_CONTAS_ICEBERG",
    "CTCONTAS_EQUIVALENTES",
}
SNAPSHOT_FIELDS = {
    "companies",
    "observed_chart_usage",
    "chart_owners",
    "chart_accounts",
    "plan_template_accounts",
    "nature_rules",
    "configured_accounts",
    "equivalent_accounts",
    "cash_accounts",
    "bank_references",
    "integration_account_configurations",
    "metadata",
}


def rows(value: Any, fields: set[str], key: tuple[str, ...], limit: int) -> list[dict[str, Any]]:
    require(type(value) is list and len(value) <= limit, "TABLE_LIMIT")
    seen = set()
    for row in value:
        keys(row, fields)
        identity = tuple(row[field] for field in key)
        require(all(type(item) in (int, str) for item in identity), "TABLE_KEY_TYPE")
        require(identity not in seen, "TABLE_DUPLICATE")
        seen.add(identity)
    return cast(list[dict[str, Any]], value)


def validate_chart_row(row: Any, *, template: bool = False) -> None:
    keys(row, CHART_FIELDS | ({"plan_id_raw"} if template else set()))
    integer(row["chart_company_code"], positive=True)
    integer(row["account_code"], positive=True)
    if template:
        integer(row["plan_id_raw"])
    for field, length in (
        ("account_name_raw", 60 if template else 150),
        ("classification_raw", 20),
        ("account_type_raw", 1),
        ("account_status_raw", 1),
    ):
        text(row[field], length)
    details.day(row["inactive_on_raw"])


def validate_metadata(value: Any) -> None:
    keys(value, {"targets", "tables", "key_columns", "relation_columns"})
    require(
        type(value["targets"]) is list
        and len(value["targets"]) == len(TARGETS)
        and all(type(item) is str for item in value["targets"])
        and set(value["targets"]) == TARGETS,
        "METADATA_TARGETS",
    )
    tables = rows(value["tables"], TABLE_FIELDS, ("table_id",), 7)
    require(len(tables) == 7, "METADATA_TABLES")
    for name, fields, key, limit in (
        ("tables", TABLE_FIELDS, ("table_id",), 7),
        ("key_columns", KEY_FIELDS, ("table_id", "index_id", "sequence"), 1024),
        (
            "relation_columns",
            RELATION_FIELDS,
            ("foreign_table_id", "foreign_index_id", "sequence"),
            4096,
        ),
    ):
        for row in rows(value[name], fields, key, limit):
            for field, item in row.items():
                if item is None:
                    require(
                        field in {"primary_column_id", "primary_column", "not_enforced"},
                        "METADATA_NULL",
                    )
                elif re.search(r"(_id|_category|_code|sequence|table_type|match_type)$", field):
                    require(type(item) is int and 0 <= item <= 4_294_967_295, "METADATA_NUMBER")
                else:
                    details.text(item, 128)
                    require(bool(item) and item == item.rstrip(" "), "METADATA_NAME")
    require(
        {row["table_name"].upper() for row in tables} == TARGETS
        and all(row["table_type"] == 1 for row in tables),
        "METADATA_TABLES",
    )
    table_ids = {row["table_id"] for row in tables}
    require(all(row["table_id"] in table_ids for row in value["key_columns"]), "METADATA_KEY_SCOPE")
    require(
        all(
            row["foreign_table_id"] in table_ids or row["primary_table_id"] in table_ids
            for row in value["relation_columns"]
        ),
        "METADATA_RELATION_SCOPE",
    )


def _reference_tables(data: dict[str, Any], companies: set[int], portfolio_sha256: str) -> None:
    # The D-372 source remains immutable. This new contract keeps its keys and
    # cardinality rules while allowing literal, well-formed business Unicode.
    for flag in (
        "completed",
        "two_reads_identical",
        "cadastral_names_and_bank_references_selected",
    ):
        require(data[flag] is True, "POSITIVE_FLAG")
    integer(data["expected_company_count"])
    require(data["expected_company_count"] == len(companies), "EXPECTED_COMPANY_COUNT")
    require(
        data["company_selector"] == "A"
        and data["company_codes_sha256"] == details.scope_hash(companies)
        and data["retained_portfolio_sha256"] == portfolio_sha256,
        "REPORT_SCOPE",
    )
    observed = data["observed_at_utc"]
    require(
        type(observed) is str
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z", observed) is not None,
        "OBSERVED_AT",
    )
    snapshot = data["snapshot"]
    configured = details.table(
        snapshot, "configured_accounts", details.CONFIG_FIELDS, details.CONFIG_KEY, 5000, companies
    )
    for row in configured.values():
        integer(row["chart_company_code"], positive=True)
        integer(row["account_code"], positive=True)
        integer(row["catalogue_account_code"], nullable=True)
        integer(row["catalogue_matches"])
        for field, limit in (
            ("account_name_raw", 150),
            ("classification_raw", 20),
            ("account_type_raw", 1),
            ("account_status_raw", 1),
        ):
            text(row[field], limit, nullable=True)
        details.day(row["inactive_on_raw"])
        if row["catalogue_account_code"] is None:
            require(
                row["catalogue_matches"] == 0
                and all(
                    row[field] is None
                    for field in (
                        "account_name_raw",
                        "classification_raw",
                        "account_type_raw",
                        "account_status_raw",
                        "inactive_on_raw",
                    )
                ),
                "ACCOUNT_LOOKUP",
            )
        else:
            require(
                row["catalogue_matches"] == 1
                and row["catalogue_account_code"] == row["account_code"]
                and all(
                    row[field] is not None
                    for field in (
                        "account_name_raw",
                        "classification_raw",
                        "account_type_raw",
                        "account_status_raw",
                    )
                ),
                "ACCOUNT_LOOKUP",
            )
    cash = details.table(
        snapshot, "cash_accounts", details.CASH_FIELDS, details.CASH_KEY, 5000, companies
    )
    for row in cash.values():
        text(row["selection_raw"], 1, nullable=True)
        integer(row["cash_type_raw"], nullable=True)
        integer(row["bank_reference_count"])
    banks = details.table(
        snapshot, "bank_references", details.BANK_FIELDS, details.BANK_KEY, 20000, companies
    )
    bank_counts: Counter[tuple[int, ...]] = Counter()
    for row in banks.values():
        text(row["agency_raw"], 10)
        text(row["account_identifier_raw"], 30)
        text(row["bank_name_raw"], 100, nullable=True)
        for field in ("bank_id_raw", "bank_catalogue_id", "bank_code_raw"):
            integer(row[field], nullable=True)
        cash_key = tuple(row[field] for field in details.CASH_KEY)
        require(
            type(row["cash_key_present"]) is bool and row["cash_key_present"] == (cash_key in cash),
            "CASH_REFERENCE_FLAG",
        )
        bank_counts[cash_key] += 1
        integer(row["bank_catalogue_matches"])
        if row["bank_catalogue_id"] is None:
            require(
                row["bank_catalogue_matches"] == 0
                and row["bank_code_raw"] is None
                and row["bank_name_raw"] is None,
                "BANK_LOOKUP",
            )
        else:
            require(
                row["bank_catalogue_matches"] == 1
                and row["bank_id_raw"] == row["bank_catalogue_id"]
                and row["bank_code_raw"] is not None
                and row["bank_name_raw"] is not None,
                "BANK_LOOKUP",
            )
    require(
        all(row["bank_reference_count"] == bank_counts[key] for key, row in cash.items()),
        "BANK_REFERENCE_COUNT",
    )
    integrations = details.table(
        snapshot,
        "integration_account_configurations",
        details.INTEGRATION_FIELDS,
        details.INTEGRATION_KEY,
        5000,
        companies,
    )
    for row in integrations.values():
        details.day(row["integration_started_on_raw"])


def validate(data: Any, companies: set[int], portfolio_sha256: str) -> dict[str, Any]:
    keys(
        data,
        {
            "version",
            "completed",
            "observed_at_utc",
            "decision",
            "period_start",
            "period_end_exclusive",
            "company_selector",
            "expected_company_count",
            "two_reads_identical",
            "company_codes_sha256",
            "retained_portfolio_sha256",
            "script_sha256",
            "provenance",
            "snapshot",
            "cadastral_names_and_bank_references_selected",
            *FALSE_FLAGS,
        },
    )
    require(data["version"] == VERSION and data["decision"] == "D-373", "REPORT_IDENTITY")
    require(data["script_sha256"] == SCRIPT_SHA, "READER_HASH")
    require(
        data["period_start"] == PERIOD_START and data["period_end_exclusive"] == PERIOD_END,
        "PERIOD_CONTRACT",
    )
    require(
        details.canonical(data["provenance"]) == details.canonical(PROVENANCE),
        "PROVENANCE_CONTRACT",
    )
    for flag in FALSE_FLAGS:
        require(data[flag] is False, "FORBIDDEN_FLAG")
    require(bool(companies), "EMPTY_SCOPE")
    snapshot = data["snapshot"]
    keys(snapshot, SNAPSHOT_FIELDS)
    company_rows = rows(snapshot["companies"], COMPANY_FIELDS, ("company_code",), 500)
    require({row["company_code"] for row in company_rows} == companies, "EXACT_COMPANY_SCOPE")
    for row in company_rows:
        integer(row["company_code"], positive=True)
        require(
            type(row["configuration_rows"]) is int and row["configuration_rows"] in (0, 1),
            "PARAMETER_CARDINALITY",
        )
        for field in ("codi_pad_raw", "i_planocontas_raw", "cash_account_parameter_raw"):
            integer(row[field], nullable=True)
        for field in ("comp_pad_raw", "branch_parameter_raw"):
            text(row[field], 1, nullable=True)
        if row["configuration_rows"] == 0:
            require(
                all(
                    row[field] is None
                    for field in COMPANY_FIELDS - {"company_code", "configuration_rows"}
                ),
                "MISSING_PARAMETERS",
            )
        else:
            require(row["i_planocontas_raw"] is not None, "PARAMETER_NULL")
    _reference_tables(data, companies, portfolio_sha256)
    usage = rows(
        snapshot["observed_chart_usage"],
        USAGE_FIELDS,
        ("company_code", "chart_company_code", "branch_code", "year", "month"),
        10000,
    )
    for row in usage:
        for field in USAGE_FIELDS:
            integer(row[field], positive=field not in {"branch_code"})
        require(row["company_code"] in companies, "USAGE_SCOPE")
        require(row["year"] == 2026 and 9 <= row["month"] <= 11, "USAGE_PERIOD")
    equivalents = rows(
        snapshot["equivalent_accounts"], set(details.CONFIG_KEY), details.CONFIG_KEY, 20000
    )
    for row in equivalents:
        for field in details.CONFIG_KEY:
            integer(row[field], positive=True)
        require(row["company_code"] in companies, "EQUIVALENT_SCOPE")
    owners = rows(snapshot["chart_owners"], {"chart_company_code"}, ("chart_company_code",), 600)
    owner_codes = {row["chart_company_code"] for row in owners}
    for code in owner_codes:
        integer(code, positive=True)
    expected_owners = companies | {
        row["codi_pad_raw"] for row in company_rows if row["codi_pad_raw"]
    }
    expected_owners |= {
        row["chart_company_code"] for row in usage + equivalents + snapshot["configured_accounts"]
    }
    require(owner_codes == expected_owners, "EXACT_CHART_SCOPE")
    charts = rows(
        snapshot["chart_accounts"], CHART_FIELDS, ("chart_company_code", "account_code"), 100000
    )
    chart_index = {}
    for row in charts:
        validate_chart_row(row)
        require(row["chart_company_code"] in owner_codes, "CATALOGUE_SCOPE")
        chart_index[(row["chart_company_code"], row["account_code"])] = row
    for row in rows(
        snapshot["plan_template_accounts"],
        CHART_FIELDS | {"plan_id_raw"},
        ("chart_company_code", "plan_id_raw", "account_code"),
        100000,
    ):
        validate_chart_row(row, template=True)
        require(row["chart_company_code"] in owner_codes, "TEMPLATE_SCOPE")
    for row in rows(
        snapshot["nature_rules"],
        {"chart_company_code", "rule_order", "classification_raw", "nature_raw", "group_raw"},
        ("chart_company_code", "rule_order"),
        10000,
    ):
        integer(row["chart_company_code"], positive=True)
        integer(row["rule_order"])
        require(
            row["chart_company_code"] in owner_codes and row["rule_order"] <= 255, "NATURE_SCOPE"
        )
        text(row["classification_raw"], 20)
        text(row["nature_raw"], 1)
        text(row["group_raw"], 1)
    for row in snapshot["configured_accounts"]:
        chart = chart_index.get((row["chart_company_code"], row["account_code"]))
        require(bool(chart) == (row["catalogue_matches"] == 1), "CONFIGURED_CATALOGUE_DRIFT")
        if chart:
            require(
                all(chart[field] == row[field] for field in CHART_FIELDS),
                "CONFIGURED_CATALOGUE_DRIFT",
            )
    validate_metadata(snapshot["metadata"])
    return cast(dict[str, Any], data)


def decode_discovery(
    raw: bytes,
    *,
    expected_sha256: str,
    expected_size_bytes: int,
    companies: set[int],
    portfolio_sha256: str,
) -> dict[str, Any]:
    require(type(raw) is bytes and 2 <= len(raw) <= LIMIT, "FILE_SIZE")
    require(type(expected_size_bytes) is int and expected_size_bytes == len(raw), "FILE_SIZE")
    require(
        type(expected_sha256) is str
        and re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
        and hashlib.sha256(raw).hexdigest() == expected_sha256,
        "FILE_HASH",
    )
    try:
        data = json.loads(
            raw.decode("utf-8-sig"),
            object_pairs_hook=details.pairs,
            parse_constant=details.reject_constant,
        )
        validated = validate(data, companies, portfolio_sha256)
        require(
            datetime.fromisoformat(data["observed_at_utc"].replace("Z", "+00:00"))
            <= datetime.now(UTC),
            "OBSERVED_IN_FUTURE",
        )
        return validated
    except (UnicodeError, ValueError, TypeError, KeyError, RecursionError, OverflowError):
        raise Invalid("INVALID_DISCOVERY_CONTRACT") from None
