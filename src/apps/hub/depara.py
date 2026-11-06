"""Prepare reviewable initial DE-PARA drafts from explicit human examples, offline."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    LedgerAccount,
    NormalizedMovement,
    ReconciliationRule,
)
from apps.hub.reconciliation_service import _matches_condition
from apps.organizations.models import Membership


@dataclass(frozen=True)
class DeparaExample:
    reference: str
    description: str
    direction: str
    account_reference: str
    debit_account_code: str
    credit_account_code: str
    accounting_history: str


@dataclass(frozen=True)
class DeparaResult:
    references: tuple[str, ...]
    status: str
    rule_id: str | None = None


@transaction.atomic
def create_initial_depara_drafts(
    *, company: ClientCompany, examples: Iterable[DeparaExample], reviewed_by: User
) -> tuple[DeparaResult, ...]:
    """No provider calls, activation or classification. Existing rules are never replaced.

    Callers must supply examples already reviewed by the named human. The drafts
    still require separate review/activation through the existing rule workflow.
    """
    ClientCompany.objects.select_for_update().get(
        pk=company.pk, organization_id=company.organization_id
    )
    if not Membership.objects.filter(
        organization_id=company.organization_id,
        user=reviewed_by,
        is_active=True,
        user__is_active=True,
        role__in=[
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.MANAGER,
            Membership.Role.OPERATOR,
        ],
    ).exists():
        raise PermissionDenied("DE-PARA exige revisor autorizado no escritório da empresa.")
    account_codes = set(
        LedgerAccount.objects.filter(
            company=company,
            organization_id=company.organization_id,
            active=True,
            accepts_entries=True,
        ).values_list("code", flat=True)
    )
    banks = {
        account.account_reference: account
        for account in FinancialAccount.objects.filter(
            company=company, organization_id=company.organization_id, active=True
        ).exclude(account_reference="")
    }
    active_rules = list(
        ReconciliationRule.objects.filter(
            company=company,
            organization_id=company.organization_id,
            state=ReconciliationRule.State.ACTIVE,
        )
    )
    groups: dict[tuple[str, str, str], list[DeparaExample]] = defaultdict(list)
    seen_references: set[str] = set()
    for example in examples:
        if len(seen_references) >= 100_000:
            raise ValueError("DE-PARA excede 100.000 exemplos.")
        if example.reference in seen_references:
            raise ValueError("DE-PARA exige referências de exemplo únicas.")
        seen_references.add(example.reference)
        groups[
            (example.description.casefold(), example.direction, example.account_reference)
        ].append(example)
    results = []
    for (_description, direction, account_reference), group in sorted(groups.items()):
        references = tuple(sorted(e.reference for e in group))
        if any(
            not e.reference.strip()
            or len(e.reference) > 160
            or not e.description.strip()
            or len(e.description) > 1000
            or not e.accounting_history.strip()
            or len(e.accounting_history) > 500
            for e in group
        ) or direction not in {"inflow", "outflow"}:
            results.append(DeparaResult(references, "insufficient"))
            continue
        if account_reference not in banks or any(
            e.debit_account_code not in account_codes or e.credit_account_code not in account_codes
            for e in group
        ):
            results.append(DeparaResult(references, "invalid_accounts"))
            continue
        actions = [
            {
                "debit_account_code": e.debit_account_code,
                "credit_account_code": e.credit_account_code,
                "accounting_history": e.accounting_history,
                "require_review": True,
            }
            for e in group
        ]
        if len({json.dumps(action, sort_keys=True) for action in actions}) != 1:
            results.append(DeparaResult(references, "conflict"))
            continue
        probe = NormalizedMovement(
            organization_id=company.organization_id,
            company=company,
            financial_account=banks[account_reference],
            description=group[0].description,
            direction=direction,
        )
        conflicting = False
        for active in active_rules:
            if (
                all(_matches_condition(c, probe) for c in active.all_conditions)
                and (
                    not active.any_conditions
                    or any(_matches_condition(c, probe) for c in active.any_conditions)
                )
                and (
                    active.actions.get("ignore")
                    or any(
                        active.actions.get(key) and active.actions[key] != actions[0][key]
                        for key in (
                            "debit_account_code",
                            "credit_account_code",
                            "accounting_history",
                        )
                    )
                )
            ):
                conflicting = True
                break
        if conflicting:
            results.append(DeparaResult(references, "conflict"))
            continue
        # Use the same exact, case-insensitive comparison as the existing engine.
        conditions = [
            {"field": "description", "operator": "equals", "value": _description},
            {"field": "direction", "operator": "equals", "value": direction},
            {"field": "financial_account", "operator": "equals", "value": account_reference},
        ]
        canonical = json.dumps(
            {
                "conditions": conditions,
                "actions": actions[0],
                "references": references,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        name = f"DE-PARA inicial {digest[:32]}"
        existing = ReconciliationRule.objects.filter(
            company=company,
            organization_id=company.organization_id,
            name=name,
        ).first()
        if existing:
            # A human may have edited or disabled it. A retry keeps that decision.
            results.append(DeparaResult(references, "preserved", str(existing.pk)))
            continue
        rule = ReconciliationRule.objects.create(
            organization_id=company.organization_id,
            company=company,
            name=name,
            state=ReconciliationRule.State.DRAFT,
            all_conditions=conditions,
            actions=actions[0],
            created_by=reviewed_by,
        )
        record_event(
            action="hub.reconciliation.depara_draft_created",
            organization=company.organization,
            actor=reviewed_by,
            target=rule,
            metadata={
                "contract": "depara-examples-v1",
                "fingerprint": digest,
                "example_references": list(references),
                "provider_called": False,
            },
        )
        results.append(DeparaResult(references, "draft", str(rule.pk)))
    return tuple(results)
