"""Immutable discovery identity only; contingency exposes no review/write service."""
from __future__ import annotations

from typing import Any

from apps.intelligence.native_ledger_contract import canonical_hash


def discovery_source_identity(company: Any, chart: Any, *, deep: bool = True) -> dict[str, Any]:
    """Bind retained facts to their immutable rows without requiring a future latest batch."""
    batch = company.discovery
    return {
        "discovery_id": str(batch.pk),
        "company_discovery_id": str(company.pk),
        "chart_account_id": str(chart.pk),
        "source_file_sha256": batch.source_file_sha256,
        "source_size_bytes": batch.source_size_bytes,
        "source_observed_at": batch.source_observed_at.isoformat(),
        "script_sha256": batch.script_sha256,
        "portfolio_file_sha256": batch.portfolio_file_sha256,
        "company_codes_sha256": batch.company_codes_sha256,
        "source_metadata_sha256": canonical_hash(batch.source_metadata),
        "source_data_sha256": (
            canonical_hash(batch.source_data) if deep else batch.provenance["source_data_sha256"]
        ),
        "source_provenance_sha256": canonical_hash(batch.provenance),
        "row_sha256": chart.row_sha256,
        "row_content_sha256": canonical_hash(chart.row),
        "facts_sha256": company.facts_sha256,
        "facts_content_sha256": canonical_hash(
            {
                "facts": company.facts,
                "gaps": company.gaps,
                "state": company.coverage_state,
            }
        ),
        "company_code": company.source_company_code,
        "chart_company_code": chart.chart_company_code,
        "account_code": chart.account_code,
    }
