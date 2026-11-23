"""D-394: automatic interpretation of captured Domínio titles and payments (direct use only).

Domínio payment types (official import sets 6168/6169, V-370/V-415):
type 1 = amount paid/received (cash, already including interest — C02), 2 = interest,
3 = penalty, 4 = discount; 6-10 (Entradas) / 6-9 (Saídas) = withholdings (C01), kept in the
settlement's provenance but never in cash. Installment principal = ``vlor_*`` (net of
withholdings), ``vbru_*`` only when ``vlor_*`` is empty. Anything outside this reading stays as a
received source, uninterpreted. The technical author is never a person.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction

from apps.audit.services import record_event
from apps.hub.direct_use import direct_use_enabled
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    ReconciliationTitleAllocation,
)
from apps.hub.title_contract import TitleContractError, validate_title_snapshot

logger = logging.getLogger(__name__)
DECISION = "D-394"
ACTION = "hub.reconciliation.native_titles_auto_interpreted"
EVIDENCE = "Interpretação automática D-394 (tipos oficiais Domínio 6168/6169)"
RULES: dict[str, dict[str, Any]] = {
    "entradas": {"kind": "payable", "retentions": {"6", "7", "8", "9", "10"}},
    "saidas": {"kind": "receivable", "retentions": {"6", "7", "8", "9"}},
}
CASH, INTEREST, PENALTY, DISCOUNT = "1", "2", "3", "4"
CHUNK = 100


def _cents(value: Any) -> int | None:
    """Literal decimal string → integer cents; anything else is not interpretable."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        cents = Decimal(value) * 100
    except InvalidOperation:
        return None
    if cents != cents.to_integral_value():
        return None
    return int(cents)


def _as_of(evidence: Any) -> str:
    end = date.fromisoformat(evidence.scope["period_end_exclusive"])
    return (end - timedelta(days=1)).isoformat()


def account_for_company(company: ClientCompany) -> FinancialAccount | None:
    """The company's bank account for titles: linked to the Razão first, then the oldest."""
    accounts = list(
        FinancialAccount.objects.filter(
            organization_id=company.organization_id, company=company, active=True
        )
        .exclude(account_reference="")
        .select_related("company", "organization")
        .order_by("created_at", "id")
    )
    linked = [account for account in accounts if hasattr(account, "ledger_mapping")]
    candidates = linked or accounts
    return candidates[0] if candidates else None


def _decision(
    family: str,
    spec: dict[str, Any],
    part: dict[str, Any],
    reference: str,
    payments: dict[str, dict[str, Any]],
    as_of: str,
) -> dict[str, Any] | None:
    from apps.intelligence.native_title_contract import canonical_hash

    rule = RULES[family]
    suffix = spec["payment_type_field"].split("_", 1)[1]
    principal_field = next(
        (
            field
            for field in (f"vlor_{suffix}", f"vbru_{suffix}")
            if (_cents(part.get(field)) or 0) > 0
        ),
        None,
    )
    if principal_field is None:
        return None
    principal = _cents(part[principal_field]) or 0
    groups: dict[tuple[Any, Any], list[str]] = defaultdict(list)
    for ref, row in payments.items():
        groups[(row[spec["payment_date_field"]], row[spec["payment_number_field"]])].append(ref)
    direction = "outflow" if rule["kind"] == "payable" else "inflow"
    allowed = {CASH, INTEREST, PENALTY, DISCOUNT, *rule["retentions"]}
    settlements, consumed = [], 0
    for (posted_on, _number), refs in sorted(groups.items(), key=lambda item: str(item[0])):
        totals: dict[str, int] = defaultdict(int)
        for ref in refs:
            row = payments[ref]
            kind = str(row.get(spec["payment_type_field"]))
            amount = _cents(row.get(f"vpag_{suffix}"))
            if kind not in allowed or amount is None or amount < 0:
                return None  # unknown type or reversal not proven
            totals[kind] += amount
        cash = totals[CASH]
        amount_principal = cash - totals[INTEREST] - totals[PENALTY] + totals[DISCOUNT]
        if cash <= 0 or amount_principal < 0 or not isinstance(posted_on, str):
            return None
        if posted_on > as_of:
            return None
        consumed += amount_principal
        settlements.append(
            {
                "payment_references": sorted(refs),
                "normalized": {
                    "key": canonical_hash(sorted(refs)),
                    "posted_on": posted_on,
                    "principal_cents": amount_principal,
                    "interest_cents": totals[INTEREST],
                    "penalty_cents": totals[PENALTY],
                    "fees_cents": 0,
                    "discount_cents": totals[DISCOUNT],
                    "cash_cents": cash,
                    "direction": direction,
                    "reverses": None,
                },
            }
        )
    if consumed > principal:
        return None
    return {
        "family": family,
        "installment_reference": reference,
        "kind": rule["kind"],
        "principal_field": principal_field,
        "settlements": settlements,
    }


def build_decisions(evidence: Any) -> tuple[list[dict[str, Any]], int]:
    from apps.intelligence.native_title_comparison import _key, _validated
    from apps.intelligence.native_title_contract import canonical_hash, manifest

    raw = _validated(evidence)
    contract = manifest()
    as_of = _as_of(evidence)
    decisions, skipped = [], 0
    for family in raw["families"]:
        name = family["name"]
        if name not in RULES:
            skipped += len(family["installments"])
            continue
        spec = contract["families"][name]
        by_installment: dict[Any, dict[str, dict[str, Any]]] = defaultdict(dict)
        for row in family["payments"]:
            ref = canonical_hash([name, "payments", _key(row, spec, "payments")])
            by_installment[_key(row, spec, "installments")][ref] = row
        for part in family["installments"]:
            identity = _key(part, spec, "installments")
            reference = canonical_hash([name, "installments", identity])
            decision = _decision(
                name, spec, part, reference, by_installment.get(identity, {}), as_of
            )
            if decision is None:
                skipped += 1
            else:
                decisions.append(decision)
    return decisions, skipped


def _translate(
    evidence: Any, decisions: list[dict[str, Any]], account: FinancialAccount
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """Translate in chunks; a chunk the contract refuses is split until the culprit is left out."""
    from apps.intelligence.native_title_translation import translate_reviewed_titles

    if not decisions:
        return [], [], 0
    try:
        payload, provenance = translate_reviewed_titles(
            evidence=evidence,
            review={
                "source_sha256": evidence.expected_sha256,
                "evidence_reference": EVIDENCE,
                "decisions": decisions,
            },
            company_key=str(account.company_id),
            account_reference=account.account_reference,
        )
        return payload["titles"], provenance, 0
    except TitleContractError:
        if len(decisions) == 1:
            return [], [], 1
        middle = len(decisions) // 2
        left = _translate(evidence, decisions[:middle], account)
        right = _translate(evidence, decisions[middle:], account)
        return left[0] + right[0], left[1] + right[1], left[2] + right[2]


def interpret_capture(capture_id: Any, organization_id: Any) -> dict[str, Any]:
    """Interpret one captured month into the company's title snapshot; idempotent."""
    from apps.hub.native_title_capacity import (
        persist_native_provenance,
        proposed_provenance,
        validate_native_revision,
    )
    from apps.hub.title_persistence import _load as load_snapshot
    from apps.hub.title_persistence import import_title_snapshot, latest_title_snapshot
    from apps.hub.title_requests import title_job_company
    from apps.hub.title_robot import title_robot
    from apps.intelligence.models import NativeTitleCollection
    from apps.intelligence.native_title_comparison import load_capture_for_routine

    job, evidence = load_capture_for_routine(capture_id, organization_id)
    company = title_job_company(job)
    account = (
        job.financial_account
        if isinstance(job, NativeTitleCollection)
        else account_for_company(company)
    )
    if account is None:
        return {"status": "sem_conta"}
    decisions, skipped = build_decisions(evidence)
    robot = title_robot()
    saved = None
    try:
        with transaction.atomic():
            ClientCompany.objects.select_for_update().get(
                pk=company.pk, organization_id=organization_id
            )
            account = FinancialAccount.objects.select_related("company", "organization").get(
                pk=account.pk
            )
            confirmed = set(
                ReconciliationTitleAllocation.objects.filter(
                    organization_id=organization_id,
                    financial_account__company_id=company.pk,
                    state=ReconciliationTitleAllocation.State.CONFIRMED,
                ).values_list("installment_key", flat=True)
            )
            kept = [d for d in decisions if d["installment_reference"] not in confirmed]
            skipped += len(decisions) - len(kept)
            titles, provenance, refused = _translate(evidence, kept, account)
            skipped += refused
            as_of = _as_of(evidence)
            latest = latest_title_snapshot(account)
            merged: dict[str, Any] = {
                "contract": "titles-normalized-v1",
                "company_key": str(account.company_id),
                "account_reference": account.account_reference,
                "as_of": as_of,
                "settlements_complete": False,
                "titles": [],
            }
            if latest is not None:
                previous, _ = load_snapshot(latest, account)
                if as_of < previous["as_of"]:
                    return {"status": "competencia_anterior", "skipped": skipped}
                merged["titles"] = deepcopy(previous["titles"])
            incoming: list[dict[str, Any]] = []
            for title in titles:
                target = next((t for t in merged["titles"] if t["key"] == title["key"]), None)
                if target is None:
                    merged["titles"].append(title)
                    incoming.extend(title["installments"])
                    continue
                if target["kind"] != title["kind"]:
                    skipped += len(title["installments"])
                    continue
                for part in title["installments"]:
                    position = next(
                        (
                            i
                            for i, p in enumerate(target["installments"])
                            if p["key"] == part["key"]
                        ),
                        None,
                    )
                    if position is None:
                        target["installments"].append(part)
                    else:
                        target["installments"][position] = part
                    incoming.append(part)
            incoming_keys = {part["key"] for part in incoming}
            provenance = [p for p in provenance if p["installment_key"] in incoming_keys]
            if not provenance:
                return {"status": "nada_a_interpretar", "skipped": skipped}
            validate_title_snapshot(
                merged,
                company_key=str(account.company_id),
                account_reference=account.account_reference,
            )
            proposed = proposed_provenance(
                account=account, job=job, payload=merged, provenance=provenance
            )
            installments = {(p["title_key"], p["installment_key"]) for p in provenance}
            validate_native_revision(account=account, proposed=proposed, installments=installments)
            snapshot, created = import_title_snapshot(
                financial_account=account,
                content=json.dumps(merged, sort_keys=True, separators=(",", ":")).encode(),
                actor=robot,
                evidence_reference=EVIDENCE,
                activate_existing=True,
                routine=True,
            )
            if created:
                saved = snapshot.source_file
            persist_native_provenance(
                account=account,
                snapshot=snapshot,
                proposed=proposed,
                installments=installments,
                previous=latest if latest is not None and latest.pk != snapshot.pk else None,
            )
            if created:
                record_event(
                    action=ACTION,
                    actor=robot,
                    organization=account.organization,
                    target=snapshot,
                    metadata={
                        "decision": DECISION,
                        "capture_id": str(job.pk),
                        "source_sha256": evidence.expected_sha256,
                        "interpreted": len(provenance),
                        "skipped": skipped,
                        "provenance": provenance,  # D-396: readable note/installment labels
                        "previous_snapshot_id": str(latest.pk) if latest else None,
                        "bank_linkage": "unproven",
                        "settlements_complete": False,
                    },
                )
            return {
                "status": "interpretado" if created else "ja_interpretado",
                "snapshot": str(snapshot.pk),
                "interpreted": len(provenance),
                "skipped": skipped,
            }
    except Exception:
        if saved is not None:
            saved.content.delete(save=False)
        raise


def _captures(company: ClientCompany) -> list[Any]:
    from apps.intelligence.models import CompanyTitleCollection, NativeTitleCollection

    jobs = [
        *CompanyTitleCollection.objects.filter(
            organization_id=company.organization_id, company=company, state="captured"
        ),
        *NativeTitleCollection.objects.filter(
            organization_id=company.organization_id,
            financial_account__company=company,
            state="captured",
        ),
    ]
    return sorted(
        jobs, key=lambda job: (str((job.scope or {}).get("period_start", "")), job.completed_at)
    )


def interpret_company(company: ClientCompany) -> list[dict[str, Any]]:
    """Every captured month of one company, oldest first; one failure never stops the rest."""
    if not direct_use_enabled(company.organization):
        return []
    results = []
    for job in _captures(company):
        try:
            result = interpret_capture(job.pk, company.organization_id)
            results.append({"capture": str(job.pk), **result})
        except Exception as exc:
            logger.exception("Interpretação D-394 falhou na captura %s", job.pk)
            results.append({"capture": str(job.pk), "status": "erro", "error": str(exc)[:200]})
    return results


def schedule_company(company_id: Any) -> None:
    """After commit, interpret the company's captured titles in the worker (never raises)."""

    def run() -> None:
        try:
            from apps.hub.tasks import interpret_company_titles

            interpret_company_titles.delay(str(company_id))
        except Exception:
            logger.exception("Interpretação D-394 não agendada para a empresa %s", company_id)

    transaction.on_commit(run)
