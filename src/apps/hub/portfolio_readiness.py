"""Private offline worklist from codes/counts; no account approval or collection."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from apps.hub.contad_relations import CatalogEvidenceError
from apps.hub.portfolio_evidence import analyze_portfolio_profile, decode_portfolio_profile

GAP_GUIDANCE = {
    "bank_mapping_review": (
        "Conferir banco, referência física, plano, conta e direção com evidência."
    ),
    "account_level_counts_missing": (
        "Obter contagens por conta, competência e escopo de lotes completos; "
        "totais da empresa não preenchem o escopo da coleta."
    ),
    "no_configured_account_candidates": (
        "Identificar contas por outra evidência; "
        "ausência nesta configuração não dispensa a empresa."
    ),
    "no_ledger_rows_in_period": (
        "Não há linhas no período observado; isso não comprova ausência de conta ou de operação."
    ),
    "missing_accounting_parameters": "Conferir os parâmetros contábeis ausentes na origem.",
    "multiple_branches_complete_lots_review": (
        "Conferir o escopo das filiais e os lotes completos antes da coleta; "
        "filtrar filial isoladamente pode truncar partidas."
    ),
    "multiple_source_plans": "Conferir os planos observados e seus vínculos com a empresa.",
    "source_plan_differs_company": "Comprovar o vínculo com o plano de outra empresa.",
    "configured_plan_not_observed": (
        "Conferir o plano da candidata sem linhas observadas; "
        "não assumir plano incorreto ou inativo."
    ),
    "missing_catalogue_match": (
        "Obter correspondência da conta no catálogo antes de revisar o vínculo."
    ),
    "raw_account_flags_unreviewed": (
        "Conferir o significado de tipo/situação; não interpretar letras."
    ),
    "cash_registers_not_bank_accounts": (
        "Cadastros de caixa não comprovam contas bancárias; conferir natureza e vínculo próprios."
    ),
}


def _source(raw: bytes, report: dict[str, Any]) -> dict[str, str]:
    return {
        "version": report["version"],
        "input_file_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_report_sha256": hashlib.sha256(
            json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "observed_at_utc": report["observed_at_utc"],
    }


def _candidate(row: dict[str, Any], groups: list[dict[str, Any]]) -> dict[str, Any]:
    observed = [g for g in groups if g["source_plan_company_code"] == row["chart_company_code"]]
    return {
        **row,
        "candidate_key": ":".join(
            str(row[key]) for key in ("company_code", "chart_company_code", "account_code")
        ),
        "branches_observed_for_plan": sorted({g["branch_code"] for g in observed}),
        "periods_observed_for_plan": sorted(
            {f"{g['year']:04d}-{g['month']:02d}" for g in observed}
        ),
        "account_level_counts": None,
        "collection_scope": None,
        "review": {
            "decision": None,
            "reviewed_by": None,
            "evidence_reference": None,
            "bank_code": None,
            "account_reference": None,
            "bank_inflow_side": None,
            "bank_association_confirmed": None,
            "chart_owner_confirmed": None,
            "account_active_and_postable": None,
        },
        "ready_for_financial_capture": False,
    }


def prepare_portfolio_readiness(portfolio_raw: bytes, accounts_raw: bytes) -> dict[str, Any]:
    """Combine the original profiles, keeping every company and all human fields blank."""
    portfolio = decode_portfolio_profile(portfolio_raw)
    accounts = decode_portfolio_profile(accounts_raw)
    if (
        portfolio.get("version") != "contad-portfolio-profile-v1"
        or accounts.get("version") != "contad-reconciliation-account-profile-v1"
    ):
        raise CatalogEvidenceError("Informe os dois perfis originais de cobertura e contas.")
    coverage = analyze_portfolio_profile(portfolio)
    configured = analyze_portfolio_profile(accounts)
    company_configs = {row["company_code"]: row for row in portfolio["snapshot"]["companies"]}
    account_configs = {row["company_code"]: row for row in accounts["snapshot"]["companies"]}
    if company_configs != account_configs or any(
        portfolio[key] != accounts[key]
        for key in ("company_selector", "period_start", "period_end_exclusive")
    ):
        raise CatalogEvidenceError("Carteira, configuração ou período dos perfis divergem.")

    candidates_by_company: dict[int, list[dict[str, Any]]] = {code: [] for code in company_configs}
    for candidate in configured["configured_accounts"]:
        candidates_by_company[candidate["company_code"]].append(candidate)

    companies = []
    for item in coverage["companies"]:
        code = item["company_code"]
        groups = sorted(
            item["monthly_ledger"],
            key=lambda g: (g["year"], g["month"], g["source_plan_company_code"], g["branch_code"]),
        )
        branches = sorted({group["branch_code"] for group in groups})
        candidates = [
            _candidate(row, groups)
            for row in sorted(
                candidates_by_company[code],
                key=lambda row: (row["chart_company_code"], row["account_code"]),
            )
        ]
        gaps = ["bank_mapping_review", "account_level_counts_missing"]
        conditions = {
            "no_configured_account_candidates": not candidates,
            "no_ledger_rows_in_period": not groups,
            "missing_accounting_parameters": item["requires_review"]["missing_configuration"],
            "multiple_branches_complete_lots_review": len(branches) > 1,
            "multiple_source_plans": item["requires_review"]["multiple_source_plans"],
            "source_plan_differs_company": item["requires_review"]["source_plan_differs_company"],
            "configured_plan_not_observed": any(
                not row["periods_observed_for_plan"] for row in candidates
            ),
            "missing_catalogue_match": any(row["catalogue_matches"] == 0 for row in candidates),
            "raw_account_flags_unreviewed": bool(candidates),
            "cash_registers_not_bank_accounts": bool(item["cash_candidates"]),
        }
        gaps.extend(key for key, present in conditions.items() if present)
        companies.append(
            {
                "company_code": code,
                "status": (
                    "account_candidates_require_review"
                    if candidates
                    else "account_evidence_missing"
                ),
                "configuration_raw": dict(item["configuration_raw"]),
                "cash_candidate_count": len(item["cash_candidates"]),
                "source_plan_codes_observed": item["source_plan_codes_observed"],
                "branches_observed": branches,
                "monthly_entry_counts": item["monthly_entry_counts"],
                "monthly_ledger_groups": groups,
                "configured_account_candidates": candidates,
                "gaps": gaps,
                "next_step": (
                    "Revisar as contas candidatas e reunir a evidência de vínculo bancário."
                    if candidates
                    else "Identificar contas por evidência; não há candidatas nesta configuração."
                ),
                "company_review": {
                    "reviewed_by": None,
                    "evidence_reference": None,
                    "additional_accounts_reference": None,
                    "bank_account_coverage_confirmed": None,
                },
                "ready_for_financial_capture": False,
            }
        )

    def count_gap(gap: str) -> int:
        return sum(gap in company["gaps"] for company in companies)

    return {
        "version": "contad-portfolio-readiness-v1",
        "sources": {
            "portfolio": _source(portfolio_raw, portfolio),
            "configured_accounts": _source(accounts_raw, accounts),
        },
        "period_start": coverage["period_start"],
        "period_end_exclusive": coverage["period_end_exclusive"],
        "company_selector": "A",
        "summary": {
            "company_count": len(companies),
            "configured_account_candidate_count": configured["configured_account_count"],
            "companies_with_candidates": sum(
                bool(company["configured_account_candidates"]) for company in companies
            ),
            "companies_without_candidates": count_gap("no_configured_account_candidates"),
            "companies_without_ledger_rows": count_gap("no_ledger_rows_in_period"),
            "companies_missing_parameters": count_gap("missing_accounting_parameters"),
            "companies_with_multiple_branches": count_gap("multiple_branches_complete_lots_review"),
            "companies_without_candidates_with_ledger_rows": sum(
                not company["configured_account_candidates"]
                and bool(company["monthly_ledger_groups"])
                for company in companies
            ),
            "ready_for_financial_capture_count": 0,
        },
        "companies": companies,
        "gap_guidance": GAP_GUIDANCE.copy(),
        "existing_pilot_reference": {
            "company_code": 212,
            "chart_company_code": 212,
            "account_code": 8,
            "company_present_in_profiles": 212 in company_configs,
            "account_present_as_configured_candidate": any(
                row["company_code"] == 212
                and row["chart_company_code"] == 212
                and row["account_code"] == 8
                for row in configured["configured_accounts"]
            ),
            "assessment": "not_evaluated_by_these_profiles",
            "guidance": (
                "Preservar o piloto e suas provas próprias. Ausência nesta configuração não "
                "revoga o vínculo existente; estes perfis não o aprovam nem o alteram."
            ),
            "changes_existing_configuration": False,
        },
        "human_reviewed": False,
        "bank_association_approved": False,
        "financial_collection_enabled": False,
        "creates_accounts_rules_or_jobs": False,
        "evidence_limit": "technical_coverage_worklist_not_financial_approval_or_collection_scope",
    }
