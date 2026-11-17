"""Strict byte contract for the approved cadastral reader; no source paths or ERP calls."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Any, NoReturn

LIMIT = 4_194_304
SCRIPT_SHA = "dc9895816ec645a2cb6cdc49343c653e62a55bd17010687310d88dfa901998c3"
FALSE_FLAGS = (
    "cash_to_ledger_mapping_inferred",
    "bank_association_approved",
    "account_meanings_approved",
    "human_reviewed",
    "financial_collection_enabled",
    "financial_values_selected",
    "agent_configuration_read",
    "erp_write_performed",
    "uploaded",
)
PROVENANCE = {
    "configured_accounts": (
        "CTCONCILIACAO_CONTA.(CODI_EMP_PLANO,CODI_CTA) -> CTCONTAS.(codi_emp,codi_cta)"
    ),
    "bank_references": (
        "CTCONTACAIXA_CONTA_BANCARIA.(CODI_EMP,I_CONTA_CAIXA) -> CTCONTACAIXA.(codi_emp,codi_cta)"
    ),
    "bank_catalogue": "CTCONTACAIXA_CONTA_BANCARIA.I_BANCO -> CTLISTA_BANCOS_BANCO_CENTRAL.I_BANCO",
    "bank_code_storage": "CODIGO_BANCO is an integer in the retained catalog; no padding inferred.",
    "integration_account_configurations": {
        "source": "CTPARMTO_CONTAS_ICEBERG",
        "selected_columns": [
            "CODI_EMP",
            "CODI_CTA",
            "CODI_FIL",
            "I_BANCO",
            "DATA_INICIO_INTEGRACAO",
        ],
        "comparison_key_columns": ["CODI_EMP", "CODI_CTA", "CODI_FIL", "I_BANCO"],
        "declared_foreign_keys_verified": False,
        "chart_owner_mapping_inferred": False,
        "bank_catalogue_link_inferred": False,
        "interpretation": (
            "Literal cadastral codes and date only; comparison key does not assert a database "
            "primary key."
        ),
    },
}
CONFIG_FIELDS = {
    "company_code",
    "chart_company_code",
    "account_code",
    "catalogue_account_code",
    "account_name_raw",
    "classification_raw",
    "account_type_raw",
    "account_status_raw",
    "inactive_on_raw",
    "catalogue_matches",
}
CASH_FIELDS = {
    "company_code",
    "cash_account_code",
    "selection_raw",
    "cash_type_raw",
    "bank_reference_count",
}
BANK_FIELDS = {
    "company_code",
    "cash_account_code",
    "bank_reference_sequence",
    "agency_raw",
    "account_identifier_raw",
    "bank_id_raw",
    "bank_catalogue_id",
    "bank_code_raw",
    "bank_name_raw",
    "cash_key_present",
    "bank_catalogue_matches",
}
INTEGRATION_FIELDS = {
    "company_code",
    "integration_account_code_raw",
    "integration_branch_code_raw",
    "integration_bank_id_raw",
    "integration_started_on_raw",
}
CONFIG_KEY = ("company_code", "chart_company_code", "account_code")
CASH_KEY = ("company_code", "cash_account_code")
BANK_KEY = ("company_code", "cash_account_code", "bank_reference_sequence")
INTEGRATION_KEY = (
    "company_code",
    "integration_account_code_raw",
    "integration_branch_code_raw",
    "integration_bank_id_raw",
)


class Invalid(Exception):
    """Only a fixed, non-sensitive reason code may leave the validator."""


def require(condition: Any, code: str) -> None:
    if not condition:
        raise Invalid(code)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in items:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def reject_constant(_: str) -> NoReturn:
    raise Invalid("NONFINITE_JSON_NUMBER")


def keys(obj: Any, expected: Iterable[str], code: str = "SCHEMA_KEYS") -> None:
    require(type(obj) is dict and set(obj) == set(expected), code)


def integer(value: Any, nullable: bool = False, positive: bool = False) -> None:
    if nullable and value is None:
        return
    require(
        type(value) is int and (1 if positive else 0) <= value <= 2_147_483_647, "INTEGER_CONTRACT"
    )


def text(value: Any, length: int, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    require(
        type(value) is str
        and len(value.encode("utf-16-le", errors="surrogatepass")) // 2 <= length
        and not any(unicodedata.category(ch).startswith("C") for ch in value),
        "TEXT_CONTRACT",
    )


def day(value: Any) -> None:
    if value is None:
        return
    require(
        type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None,
        "DATE_CONTRACT",
    )
    try:
        date.fromisoformat(value)
    except ValueError:
        raise Invalid("DATE_CONTRACT") from None


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def scope_hash(codes: Iterable[int]) -> str:
    return sha(",".join(str(code) for code in sorted(codes)).encode("ascii"))


def table(
    snapshot: dict[str, Any],
    name: str,
    fields: set[str],
    key_fields: tuple[str, ...],
    limit: int,
    companies: set[int],
) -> dict[tuple[int, ...], dict[str, Any]]:
    rows = snapshot[name]
    require(type(rows) is list and len(rows) <= limit, "TABLE_CARDINALITY")
    indexed = {}
    for row in rows:
        keys(row, fields)
        integer(row["company_code"], positive=True)
        require(row["company_code"] in companies, "COMPANY_SCOPE")
        for field in key_fields:
            integer(row[field])
        identity = tuple(row[field] for field in key_fields)
        require(identity not in indexed, "DUPLICATE_SOURCE_KEY")
        indexed[identity] = row
    return indexed


def validate_configured_row(row: dict[str, Any]) -> None:
    keys(row, CONFIG_FIELDS)
    integer(row["company_code"], positive=True)
    integer(row["chart_company_code"], positive=True)
    integer(row["account_code"], positive=True)
    integer(row["catalogue_account_code"], nullable=True)
    for field, length in [
        ("account_name_raw", 150),
        ("classification_raw", 20),
        ("account_type_raw", 1),
        ("account_status_raw", 1),
    ]:
        text(row[field], length, nullable=True)
    day(row["inactive_on_raw"])
    integer(row["catalogue_matches"])
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


def validate(data: dict[str, Any], companies: set[int], portfolio_sha256: str) -> dict[str, Any]:
    root_keys = {
        "version",
        "completed",
        "observed_at_utc",
        "decision",
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
    }
    keys(data, root_keys)
    require(
        data["version"] == "contad-account-details-v1"
        and data["decision"] == "D-372"
        and data["company_selector"] == "A",
        "REPORT_IDENTITY",
    )
    for flag in (
        "completed",
        "two_reads_identical",
        "cadastral_names_and_bank_references_selected",
    ):
        require(data[flag] is True, "POSITIVE_FLAG")
    for flag in FALSE_FLAGS:
        require(data[flag] is False, "FORBIDDEN_FLAG")
    integer(data["expected_company_count"])
    require(data["expected_company_count"] == len(companies), "EXPECTED_COMPANY_COUNT")
    require(
        data["script_sha256"] == SCRIPT_SHA
        and data["retained_portfolio_sha256"] == portfolio_sha256
        and data["company_codes_sha256"] == scope_hash(companies),
        "REPORT_PROVENANCE_HASH",
    )
    require(canonical(data["provenance"]) == canonical(PROVENANCE), "PROVENANCE_CONTRACT")
    observed = data["observed_at_utc"]
    require(
        type(observed) is str
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z", observed) is not None,
        "OBSERVED_AT",
    )
    try:
        stamp = datetime.fromisoformat(observed.replace("Z", "+00:00"))
    except ValueError:
        raise Invalid("OBSERVED_AT") from None
    require(stamp <= datetime.now(UTC), "OBSERVED_IN_FUTURE")
    snapshot = data["snapshot"]
    keys(
        snapshot,
        {
            "companies",
            "configured_accounts",
            "cash_accounts",
            "bank_references",
            "integration_account_configurations",
        },
    )
    codes = table(snapshot, "companies", {"company_code"}, ("company_code",), 500, companies)
    require(
        len(codes) == len(companies)
        and {key[0] for key in codes} == companies
        and scope_hash(key[0] for key in codes) == scope_hash(companies),
        "EXACT_COMPANY_SCOPE",
    )
    configured = table(snapshot, "configured_accounts", CONFIG_FIELDS, CONFIG_KEY, 5000, companies)
    for row in configured.values():
        validate_configured_row(row)
    cash = table(snapshot, "cash_accounts", CASH_FIELDS, CASH_KEY, 5000, companies)
    for row in cash.values():
        text(row["selection_raw"], 1, nullable=True)
        integer(row["cash_type_raw"], nullable=True)
        integer(row["bank_reference_count"])
    banks = table(snapshot, "bank_references", BANK_FIELDS, BANK_KEY, 20000, companies)
    bank_counts: Counter[tuple[int, ...]] = Counter()
    for row in banks.values():
        text(row["agency_raw"], 10)
        text(row["account_identifier_raw"], 30)
        text(row["bank_name_raw"], 100, nullable=True)
        for field in ("bank_id_raw", "bank_catalogue_id", "bank_code_raw"):
            integer(row[field], nullable=True)
        cash_key = tuple(row[field] for field in CASH_KEY)
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
    integrations = table(
        snapshot,
        "integration_account_configurations",
        INTEGRATION_FIELDS,
        INTEGRATION_KEY,
        5000,
        companies,
    )
    for row in integrations.values():
        day(row["integration_started_on_raw"])
    return data


def decode_account_details(
    raw: bytes,
    *,
    expected_sha256: str,
    expected_size_bytes: int,
    companies: set[int],
    portfolio_sha256: str,
) -> dict[str, Any]:
    """The caller pins transferred bytes and supplies the already verified original scope."""
    require(type(raw) is bytes and 2 <= len(raw) <= LIMIT, "FILE_SIZE")
    require(type(expected_size_bytes) is int and len(raw) == expected_size_bytes, "FILE_SIZE")
    require(
        type(expected_sha256) is str
        and re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
        and sha(raw) == expected_sha256,
        "FILE_HASH",
    )
    try:
        value = json.loads(
            raw.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=reject_constant
        )
        return validate(value, companies, portfolio_sha256)
    except (UnicodeError, ValueError, RecursionError, TypeError, KeyError, OverflowError):
        raise Invalid("INVALID_SOURCE_CONTRACT") from None
