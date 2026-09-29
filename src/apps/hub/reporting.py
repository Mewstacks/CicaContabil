"""Restricted JavaScript-renderer snapshots for persisted financial facts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.utils import timezone

from apps.hub.financial import calculate_snapshot_dre, project_cash_scenario
from apps.hub.models import AccountingBalanceSnapshot, CashScenario, DreMappingSet


def _amount(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    absolute = abs(cents)
    return f"{sign}{absolute // 100}.{absolute % 100:02d}"


def _timestamp(value: datetime | None) -> str:
    return (value or timezone.now()).isoformat()


def dre_report_snapshot(
    *,
    snapshot: AccountingBalanceSnapshot,
    mapping_set: DreMappingSet,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a renderer-only DRE picture from one immutable source observation."""

    result = calculate_snapshot_dre(snapshot=snapshot, mapping_set=mapping_set)
    pending_notes = [
        f"Conta sem mapeamento DRE: {account_code}."
        for account_code in result.unmapped_account_codes
    ]
    return {
        "organizationId": str(snapshot.organization_id),
        "reportName": "DRE gerencial",
        "generatedAt": _timestamp(generated_at),
        "sourceUpdatedAt": _timestamp(snapshot.observed_at),
        "templateVersion": f"dre-mapping-v{mapping_set.version}",
        "periodLabel": snapshot.competence.strftime("%m/%Y"),
        "preliminary": not result.complete,
        "pendingNotes": pending_notes,
        "filters": [
            {"label": "Empresa", "value": snapshot.company.name},
            {"label": "Origem", "value": snapshot.get_source_kind_display()},
            {"label": "Mapa DRE", "value": mapping_set.label},
        ],
        "rows": [
            {"label": group, "amount": _amount(amount)}
            for group, amount in sorted(result.groups_cents.items())
        ],
        "evidence": [
            {
                "label": "Fotografia cont?bil",
                "reference": snapshot.source_reference,
                "detail": f"Observada em {snapshot.observed_at.isoformat()}.",
            }
        ],
    }


def cash_report_snapshot(
    *, scenario: CashScenario, generated_at: datetime | None = None
) -> dict[str, Any]:
    """Build a clearly labelled cash scenario picture without treating it as a bank feed."""

    projection = project_cash_scenario(scenario=scenario)
    rows = [
        {
            "label": position.occurred_on.strftime("%d/%m/%Y"),
            "amount": _amount(position.closing_balance_cents),
        }
        for position in projection.positions
    ]
    rows.extend(
        [
            {
                "label": "Menor saldo no horizonte",
                "amount": _amount(projection.lowest_balance_cents),
            },
            {
                "label": "Capital de giro estimado",
                "amount": _amount(projection.estimated_working_capital_cents),
            },
        ]
    )
    return {
        "organizationId": str(scenario.organization_id),
        "reportName": "Caixa gerencial",
        "generatedAt": _timestamp(generated_at),
        "templateVersion": "cash-scenario-v1",
        "periodLabel": f"A partir de {scenario.reference_date.strftime('%d/%m/%Y')}",
        "preliminary": False,
        "pendingNotes": [],
        "filters": [
            {"label": "Empresa", "value": scenario.company.name},
            {"label": "Vis?o", "value": scenario.get_view_display()},
            {"label": "Cen?rio", "value": scenario.label},
        ],
        "rows": rows,
        "evidence": [
            {
                "label": "Cen?rio de caixa",
                "reference": str(scenario.id),
                "detail": (
                    "Dados cadastrados, importados ou provenientes de fonte homologada; "
                    "n?o representa consulta banc?ria autom?tica."
                ),
            }
        ],
    }
