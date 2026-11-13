"""Offline coverage of active-company codes/counts; never authorize financial jobs."""

from __future__ import annotations

import base64
import binascii
import gzip
import hashlib
import io
import json
from datetime import date, datetime
from typing import Any

from apps.hub.contad_relations import CatalogEvidenceError

MAX_BYTES = 4 * 1024 * 1024
MAX_TRANSFER_BYTES = 6 * 1024 * 1024
FLAGS = {
    "completed": True,
    "two_reads_identical": True,
    "account_meanings_approved": False,
    "chart_owner_mapping_approved": False,
    "bank_association_approved": False,
    "financial_values_selected": False,
    "names_or_documents_selected": False,
    "agent_configuration_read": False,
    "erp_write_performed": False,
    "financial_collection_enabled": False,
    "uploaded": False,
}


def _document(raw: bytes, limit: int) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    try:
        if not 1 <= len(raw) <= limit:
            raise ValueError
        result = json.loads(
            raw.decode("utf-8-sig"),
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        if not isinstance(result, dict):
            raise ValueError
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise CatalogEvidenceError("JSON de cobertura incompatível.") from None


def decode_portfolio_profile(raw: bytes) -> dict[str, Any]:
    value = _document(raw, MAX_TRANSFER_BYTES)
    if value.get("version") != "contad-portfolio-profile-transfer-v1":
        if len(raw) > MAX_BYTES:
            raise CatalogEvidenceError("Perfil excede limite.")
        return value
    if (
        set(value) != {"version", "sha256", "bytes", "encoding", "data"}
        or value["encoding"] != "gzip-base64"
        or type(value["bytes"]) is not int
        or not 1 <= value["bytes"] <= MAX_BYTES
        or not isinstance(value["sha256"], str)
        or not isinstance(value["data"], str)
    ):
        raise CatalogEvidenceError("Transporte de cobertura incompatível.")
    try:
        packed = base64.b64decode(value["data"], validate=True)
        with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
            content = stream.read(MAX_BYTES + 1)
        if len(content) != value["bytes"] or hashlib.sha256(content).hexdigest() != value["sha256"]:
            raise ValueError
    except (ValueError, OSError, EOFError, binascii.Error):
        raise CatalogEvidenceError("Hash ou tamanho da cobertura divergente.") from None
    return _document(content, MAX_BYTES)


def _number(value: Any, minimum: int = 0, maximum: int = 2147483647) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise CatalogEvidenceError("Código ou contagem incompatível.")
    return value


def _rows(snapshot: dict[str, Any], key: str, limit: int, fields: set[str]) -> list[dict[str, Any]]:
    rows = snapshot[key]
    if not isinstance(rows, list) or len(rows) > limit:
        raise CatalogEvidenceError("Cobertura excede limite de linhas.")
    if any(not isinstance(row, dict) or set(row) != fields for row in rows):
        raise CatalogEvidenceError("Campos de cobertura incompatíveis.")
    return rows


def analyze_portfolio_profile(report: dict[str, Any]) -> dict[str, Any]:
    accounts_only = report.get("version") == "contad-reconciliation-account-profile-v1"
    if (
        set(report)
        != {
            "version",
            "observed_at_utc",
            "period_start",
            "period_end_exclusive",
            "company_selector",
            "snapshot",
            *FLAGS,
        }
        or report["version"]
        not in ("contad-portfolio-profile-v1", "contad-reconciliation-account-profile-v1")
        or report["company_selector"] != "A"
        or any(report[key] is not value for key, value in FLAGS.items())
    ):
        raise CatalogEvidenceError("Escopo ou proveniência de cobertura incompatível.")
    try:
        observed = datetime.fromisoformat(report["observed_at_utc"])
        offset = observed.utcoffset()
        start, end = (
            date.fromisoformat(report[key]) for key in ("period_start", "period_end_exclusive")
        )
        if (
            offset is None
            or offset.total_seconds() != 0
            or start != date(2026, 9, 1)
            or end.day != 1
            or not start < end <= date(2028, 9, 1)
            or end > observed.date()
            or end > date(observed.year, observed.month, 1)
        ):
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise CatalogEvidenceError("Período ou data de cobertura incompatível.") from None
    snapshot = report["snapshot"]
    expected_snapshot = (
        {"companies", "configured_accounts"}
        if accounts_only
        else {
            "companies",
            "cash_candidates",
            "monthly_ledger",
        }
    )
    if not isinstance(snapshot, dict) or set(snapshot) != expected_snapshot:
        raise CatalogEvidenceError("Fontes de cobertura incompatíveis.")
    companies = _rows(
        snapshot,
        "companies",
        500,
        {
            "company_code",
            "configuration_rows",
            "codi_pad_raw",
            "comp_pad_raw",
            "i_planocontas_raw",
        },
    )
    cash = (
        []
        if accounts_only
        else _rows(
            snapshot,
            "cash_candidates",
            5000,
            {
                "company_code",
                "cash_account_code",
                "selection_raw",
                "cash_type_raw",
                "bank_reference_count",
            },
        )
    )
    ledger = (
        []
        if accounts_only
        else _rows(
            snapshot,
            "monthly_ledger",
            10000,
            {
                "company_code",
                "source_plan_company_code",
                "branch_code",
                "year",
                "month",
                "entry_count",
                "zero_debit_rows",
                "zero_credit_rows",
                "rows_without_lot",
            },
        )
    )
    by_company: dict[int, dict[str, Any]] = {}
    for row in companies:
        code = _number(row["company_code"], 1)
        count = _number(row["configuration_rows"], maximum=1)
        if code in by_company:
            raise CatalogEvidenceError("Empresa duplicada na cobertura.")
        for key in ("codi_pad_raw", "i_planocontas_raw"):
            if row[key] is not None:
                _number(row[key])
        text = row["comp_pad_raw"]
        if text is not None and (
            not isinstance(text, str)
            or len(text) > 1
            or not text.isascii()
            or (text and not text.isprintable())
        ):
            raise CatalogEvidenceError("Código bruto de configuração incompatível.")
        if count == 0 and any(
            row[key] is not None for key in ("codi_pad_raw", "comp_pad_raw", "i_planocontas_raw")
        ):
            raise CatalogEvidenceError("Configuração inexistente com campos preenchidos.")
        by_company[code] = {
            "company_code": code,
            "configuration_raw": row,
            "cash_candidates": [],
            "monthly_ledger": [],
        }
    if accounts_only:
        return _configured_accounts(report, snapshot, by_company)
    cash_keys: set[tuple[int, int]] = set()
    for row in cash:
        company = _number(row["company_code"], 1)
        cash_key = (company, _number(row["cash_account_code"]))
        _number(row["bank_reference_count"], maximum=10000)
        if row["cash_type_raw"] is not None:
            _number(row["cash_type_raw"])
        text = row["selection_raw"]
        if text is not None and (
            not isinstance(text, str)
            or len(text) > 1
            or not text.isascii()
            or (text and not text.isprintable())
        ):
            raise CatalogEvidenceError("Código bruto de seleção incompatível.")
        if company not in by_company or cash_key in cash_keys:
            raise CatalogEvidenceError(
                "Conta candidata repetida ou fora das empresas selecionadas."
            )
        cash_keys.add(cash_key)
        by_company[company]["cash_candidates"].append(row)
    ledger_keys: set[tuple[int, ...]] = set()
    total = 0
    for row in ledger:
        company = _number(row["company_code"], 1)
        plan = _number(row["source_plan_company_code"], 1)
        branch = _number(row["branch_code"])
        year, month = _number(row["year"], 2026, 2100), _number(row["month"], 1, 12)
        ledger_key = (company, plan, branch, year, month)
        if (
            company not in by_company
            or ledger_key in ledger_keys
            or not start <= date(year, month, 1) < end
        ):
            raise CatalogEvidenceError("Grupo contábil repetido ou fora do recorte.")
        count = _number(row["entry_count"], 1, 1000000)
        for field in ("zero_debit_rows", "zero_credit_rows", "rows_without_lot"):
            _number(row[field], maximum=count)
        total += count
        ledger_keys.add(ledger_key)
        by_company[company]["monthly_ledger"].append(row)
    if total > 5000000:
        raise CatalogEvidenceError("Volume de cobertura excede limite global.")
    months = []
    cursor = start
    while cursor < end:
        months.append(cursor.strftime("%Y-%m"))
        cursor = date(cursor.year + cursor.month // 12, cursor.month % 12 + 1, 1)
    result = []
    for code, item in sorted(by_company.items()):
        groups = item["monthly_ledger"]
        plans = sorted({row["source_plan_company_code"] for row in groups})
        monthly_counts = {month: 0 for month in months}
        for row in groups:
            monthly_counts[f"{row['year']:04d}-{row['month']:02d}"] += row["entry_count"]
        result.append(
            {
                **item,
                "source_plan_codes_observed": plans,
                "monthly_entry_counts": monthly_counts,
                "requires_review": {
                    "missing_configuration": item["configuration_raw"]["configuration_rows"] == 0,
                    "no_cash_candidate": not item["cash_candidates"],
                    "multiple_source_plans": len(plans) > 1,
                    "source_plan_differs_company": any(plan != code for plan in plans),
                    "rows_without_lot": any(row["rows_without_lot"] for row in groups),
                    "cash_account_meanings": True,
                    "bank_to_ledger_mapping": True,
                },
                "ready_for_financial_capture": False,
            }
        )
    return {
        "version": "contad-portfolio-profile-analysis-v1",
        "source_sha256": hashlib.sha256(
            json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "observed_at_utc": report["observed_at_utc"],
        "period_start": start.isoformat(),
        "period_end_exclusive": end.isoformat(),
        "company_selector": "A",
        "company_count": len(companies),
        "cash_candidate_count": len(cash),
        "entry_count": total,
        "companies_without_ledger_rows": sum(not row["monthly_ledger"] for row in result),
        "companies": result,
        "financial_collection_enabled": False,
        "bank_association_approved": False,
        "human_reviewed": False,
        "acceptance_distinct_facts": 0,
        "evidence_limit": "technical_codes_and_counts_only_not_transactions_or_approval",
    }


def _configured_accounts(
    report: dict[str, Any], snapshot: dict[str, Any], companies: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    rows = _rows(
        snapshot,
        "configured_accounts",
        5000,
        {
            "company_code",
            "chart_company_code",
            "account_code",
            "account_type_raw",
            "account_status_raw",
            "catalogue_matches",
        },
    )
    seen: set[tuple[int, int, int]] = set()
    for row in rows:
        key = tuple(
            _number(row[field], 1)
            for field in ("company_code", "chart_company_code", "account_code")
        )
        if key[0] not in companies or key in seen:
            raise CatalogEvidenceError("Conta configurada repetida ou fora do recorte.")
        matches = _number(row["catalogue_matches"], maximum=1)
        for field in ("account_type_raw", "account_status_raw"):
            text = row[field]
            if text is not None and (
                not isinstance(text, str)
                or len(text) > 1
                or not text.isascii()
                or (text and not text.isprintable())
                or matches == 0
            ):
                raise CatalogEvidenceError(
                    "Tipo/situação ou correspondência de conta incompatível."
                )
        seen.add((key[0], key[1], key[2]))
    return {
        "version": "contad-reconciliation-account-analysis-v1",
        "observed_at_utc": report["observed_at_utc"],
        "company_selector": "A",
        "company_count": len(companies),
        "configured_accounts": rows,
        "configured_account_count": len(rows),
        "companies_without_configured_accounts": sorted(
            set(companies) - {row["company_code"] for row in rows}
        ),
        "missing_catalogue_accounts": sum(row["catalogue_matches"] == 0 for row in rows),
        "account_meanings_approved": False,
        "bank_association_approved": False,
        "financial_collection_enabled": False,
        "human_reviewed": False,
        "evidence_limit": "configuration_codes_and_raw_flags_not_bank_transactions_or_approval",
    }
