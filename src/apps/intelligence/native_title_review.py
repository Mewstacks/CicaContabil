"""Human, one-installment review of retained native facts; no ERP or bank writes."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    ReconciliationTitleAllocation,
    ReconciliationTitleSnapshot,
)
from apps.hub.native_title_capacity import (
    persist_native_provenance,
    proposed_provenance,
    validate_native_revision,
)
from apps.hub.title_contract import TitleContractError, validate_title_snapshot
from apps.hub.title_persistence import (
    _load as load_snapshot,
)
from apps.hub.title_persistence import (
    authorize_title_account,
    import_title_snapshot,
    latest_title_snapshot,
)
from apps.intelligence.models import CompanyTitleCollection, NativeTitleCollection
from apps.intelligence.native_title_comparison import TitleSourceEvidence, _key, _load, _validated
from apps.intelligence.native_title_contract import canonical_hash, manifest
from apps.intelligence.native_title_translation import translate_reviewed_titles

SALT = "cica.native-title-human-review.v1"
ACTION = "hub.reconciliation.native_title_ui_reviewed"
MAX_EVENTS = 100


class NativeReviewConflict(TitleContractError):
    """The human must reopen the current source before deciding again."""


@dataclass(frozen=True)
class NativeReviewSource:
    account: FinancialAccount
    capture: NativeTitleCollection | CompanyTitleCollection
    evidence: TitleSourceEvidence
    raw: dict[str, Any]


def load_native_source(
    *, account: FinancialAccount, capture_id: Any, actor: User
) -> NativeReviewSource:
    """Check both route scope and current write authority before opening private bytes."""
    current = FinancialAccount.objects.select_related("company", "organization").get(
        pk=account.pk, organization_id=account.organization_id, company_id=account.company_id
    )
    authorize_title_account(current, actor)
    legacy = NativeTitleCollection.objects.filter(
        pk=capture_id,
        organization_id=current.organization_id,
        financial_account=current,
        state="captured",
    ).exists()
    modern = CompanyTitleCollection.objects.filter(
        pk=capture_id,
        organization_id=current.organization_id,
        company_id=current.company_id,
        state="captured",
    ).exists()
    if not legacy and not modern:
        raise TitleContractError("Esta fonte não está disponível para a conta selecionada.")
    job, evidence = _load(capture_id, current.organization_id, actor)
    if isinstance(job, NativeTitleCollection):
        if job.financial_account_id != current.pk:
            raise PermissionDenied
    elif job.company_id != current.company_id:
        raise PermissionDenied
    return NativeReviewSource(current, job, evidence, _validated(evidence))


def load_company_title_source(
    *, job_id: Any, organization_id: Any, actor: User
) -> tuple[Any, TitleSourceEvidence, dict[str, Any]]:
    job, evidence = _load(job_id, organization_id, actor)
    return job, evidence, _validated(evidence)


def source_installments(source: NativeReviewSource) -> list[dict[str, Any]]:
    result = []
    contract = manifest()
    labels = {"entradas": "Entradas", "saidas": "Saídas", "servicos": "Serviços"}
    for family in source.raw["families"]:
        name = family["name"]
        spec = contract["families"][name]
        for part in family["installments"]:
            result.append(
                {
                    "reference": canonical_hash(
                        [name, "installments", _key(part, spec, "installments")]
                    ),
                    "family": name,
                    "family_label": labels[name],
                    "note": part[spec["note_field"]],
                    "number": part[spec["installment_field"]],
                    "due_on": part[spec["due_field"]],
                    "raw": part,
                }
            )
    return result


def installment_context(source: NativeReviewSource, reference: str) -> dict[str, Any]:
    selected = next((p for p in source_installments(source) if p["reference"] == reference), None)
    if selected is None:
        raise TitleContractError("Parcela ausente nesta fonte. Volte à lista de parcelas.")
    spec = manifest()["families"][selected["family"]]
    family = next(f for f in source.raw["families"] if f["name"] == selected["family"])
    identity = _key(selected["raw"], spec, "installments")
    groups: dict[tuple[Any, Any], dict[str, Any]] = {}
    for row in family["payments"]:
        if _key(row, spec, "installments") != identity:
            continue
        pair = (row[spec["payment_date_field"]], row[spec["payment_number_field"]])
        group = groups.setdefault(
            pair, {"posted_on": pair[0], "number": pair[1], "rows": [], "references": []}
        )
        group["rows"].append(list(row.items()))
        group["references"].append(
            canonical_hash([selected["family"], "payments", _key(row, spec, "payments")])
        )
    events = sorted(groups.values(), key=lambda g: (g["posted_on"], g["number"]))
    if len(events) > MAX_EVENTS:
        raise TitleContractError(
            "Esta parcela possui mais de 100 eventos. Solicite revisão assistida da fonte."
        )
    for event in events:
        event["references"].sort()
        event["key"] = canonical_hash(event["references"])
    selected["events"] = events
    selected["raw_fields"] = list(selected["raw"].items())
    selected["principal_choices"] = [
        (key, f"{key}: {value} (valor literal da fonte)")
        for key, value in selected["raw"].items()
        if key.startswith(("vlor_", "vbru_")) and isinstance(value, str)
    ]
    return selected


def latest_snapshot(account: FinancialAccount) -> ReconciliationTitleSnapshot | None:
    return latest_title_snapshot(account)


def _binding(source: NativeReviewSource, reference: str, actor: User) -> dict[str, Any]:
    return {
        "actor": str(actor.pk),
        "organization": str(source.account.organization_id),
        "company": str(source.account.company_id),
        "account": str(source.account.pk),
        "account_reference": source.account.account_reference,
        "ledger_code": source.account.ledger_code,
        "company_code": source.account.company.dominio_code,
        "capture": str(source.capture.pk),
        "source": source.evidence.expected_sha256,
        "installment": reference,
    }


def review_token(source: NativeReviewSource, reference: str, actor: User) -> str:
    installment_context(source, reference)
    latest = latest_snapshot(source.account)
    if latest:
        load_snapshot(latest, source.account)
    return signing.dumps(
        {**_binding(source, reference, actor), "latest": latest.fingerprint if latest else ""},
        salt=SALT,
        compress=True,
    )


def _token(token: str, source: NativeReviewSource, reference: str, actor: User) -> dict[str, Any]:
    try:
        result = signing.loads(token, salt=SALT, max_age=3600)
    except (signing.BadSignature, TypeError, ValueError):
        raise NativeReviewConflict("A revisão expirou ou mudou. Reabra esta parcela.") from None
    if not isinstance(result, dict) or any(
        result.get(key) != value for key, value in _binding(source, reference, actor).items()
    ):
        raise NativeReviewConflict("A fonte, conta ou responsável mudou. Reabra esta parcela.")
    return result


def _accumulate(
    source: NativeReviewSource, review: dict[str, Any], latest: ReconciliationTitleSnapshot | None
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    payload, provenance = translate_reviewed_titles(
        evidence=source.evidence,
        review=review,
        company_key=str(source.account.company_id),
        account_reference=source.account.account_reference,
    )
    proposed = proposed_provenance(
        account=source.account, job=source.capture, payload=payload, provenance=provenance
    )
    try:
        validate_native_revision(
            account=source.account,
            proposed=proposed,
            installments={(item["title_key"], item["installment_key"]) for item in provenance},
        )
    except TitleContractError as error:
        raise NativeReviewConflict(str(error)) from error
    if len(provenance) != 1:
        raise TitleContractError("Revise uma parcela por vez.")
    if latest is None:
        return payload, provenance, 0
    previous, _ = load_snapshot(latest, source.account)
    if payload["as_of"] < previous["as_of"]:
        raise NativeReviewConflict(
            "Esta fonte é anterior à fotografia vigente. Solicite uma fonte atualizada; "
            "a fotografia mais recente será preservada."
        )
    incoming = payload["titles"][0]
    chosen = incoming["installments"][0]
    merged = deepcopy(previous)
    prior_count = sum(len(t["installments"]) for t in previous["titles"])
    target = next((t for t in merged["titles"] if t["key"] == incoming["key"]), None)
    replaced = None
    kind_changed = False
    if target is None:
        merged["titles"].append(incoming)
    else:
        if target["kind"] != incoming["kind"] and any(
            p["key"] != chosen["key"] for p in target["installments"]
        ):
            raise TitleContractError(
                "A natureza diverge de outras parcelas deste título. Revise o título com o suporte."
            )
        for position, part in enumerate(target["installments"]):
            if part["key"] == chosen["key"]:
                replaced = deepcopy(part)
                target["installments"][position] = chosen
                break
        else:
            target["installments"].append(chosen)
        kind_changed = target["kind"] != incoming["kind"]
        target["kind"] = incoming["kind"]
    if (replaced != chosen or kind_changed) and ReconciliationTitleAllocation.objects.filter(
        organization_id=source.account.organization_id,
        financial_account=source.account,
        title_key=incoming["key"],
        installment_key=chosen["key"],
        state=ReconciliationTitleAllocation.State.CONFIRMED,
    ).exists():
        raise NativeReviewConflict(
            "Esta parcela tem baixas vinculadas ao banco. Desfaça esses vínculos antes "
            "de corrigir os fatos da parcela."
        )
    merged["as_of"] = payload["as_of"]
    merged["settlements_complete"] = False
    validate_title_snapshot(
        merged,
        company_key=str(source.account.company_id),
        account_reference=source.account.account_reference,
    )
    return merged, provenance, prior_count - int(replaced is not None)


def preview_native_review(
    *, source: NativeReviewSource, actor: User, reference: str, review: dict[str, Any], token: str
) -> dict[str, Any]:
    binding = _token(token, source, reference, actor)
    if binding.get("phase"):
        raise NativeReviewConflict("Reabra a parcela para preparar uma nova revisão.")
    if (
        len(review.get("decisions", [])) != 1
        or review["decisions"][0].get("installment_reference") != reference
    ):
        raise TitleContractError("A decisão deve corresponder à parcela aberta.")
    latest = latest_snapshot(source.account)
    if binding.get("latest") != (latest.fingerprint if latest else ""):
        raise NativeReviewConflict("Outra revisão atualizou os títulos. Reabra esta parcela.")
    payload, provenance, preserved = _accumulate(source, review, latest)
    parsed = validate_title_snapshot(
        payload,
        company_key=str(source.account.company_id),
        account_reference=source.account.account_reference,
    )
    confirmation = signing.dumps(
        {
            **binding,
            "phase": "confirm",
            "review_hash": canonical_hash(review),
            "fingerprint": parsed.fingerprint,
        },
        salt=SALT,
        compress=True,
    )
    selected = next(t for t in payload["titles"] if t["key"] == provenance[0]["title_key"])
    part = next(p for p in selected["installments"] if p["key"] == reference)
    return {
        "confirmation_token": confirmation,
        "fingerprint": parsed.fingerprint,
        "preserved_count": preserved,
        "kind": selected["kind"],
        "installment": part,
        "as_of": payload["as_of"],
    }


def confirm_native_review(
    *,
    account: FinancialAccount,
    capture_id: Any,
    actor: User,
    reference: str,
    review: dict[str, Any],
    confirmation_token: str,
    request: Any = None,
) -> tuple[ReconciliationTitleSnapshot, bool]:
    """Serialize account publication, recheck facts and clean storage on outer rollback."""
    saved = None
    try:
        with transaction.atomic():
            ClientCompany.objects.select_for_update().get(
                pk=account.company_id, organization_id=account.organization_id
            )
            current = (
                FinancialAccount.objects.select_for_update(of=("self",))
                .select_related("company", "organization")
                .get(
                    pk=account.pk,
                    organization_id=account.organization_id,
                    company_id=account.company_id,
                )
            )
            source = load_native_source(account=current, capture_id=capture_id, actor=actor)
            binding = _token(confirmation_token, source, reference, actor)
            if (
                binding.get("phase") != "confirm"
                or binding.get("review_hash") != canonical_hash(review)
                or len(review.get("decisions", [])) != 1
                or review["decisions"][0].get("installment_reference") != reference
            ):
                raise NativeReviewConflict("A decisão mudou depois da prévia. Revise-a novamente.")
            latest = latest_snapshot(current)
            if latest and latest.fingerprint == binding.get("fingerprint"):
                load_snapshot(latest, current)
                if AuditEvent.objects.filter(
                    organization_id=current.organization_id,
                    actor=actor,
                    action=ACTION,
                    target_id=str(latest.pk),
                    metadata__review_sha256=canonical_hash(review),
                    metadata__capture_id=str(capture_id),
                ).exists():
                    return latest, False
            if binding.get("latest") != (latest.fingerprint if latest else ""):
                raise NativeReviewConflict(
                    "Outra revisão atualizou os títulos. Reabra esta parcela."
                )
            payload, provenance, _ = _accumulate(source, review, latest)
            parsed = validate_title_snapshot(
                payload,
                company_key=str(current.company_id),
                account_reference=current.account_reference,
            )
            if parsed.fingerprint != binding.get("fingerprint"):
                raise NativeReviewConflict("A prévia mudou. Reabra esta parcela.")
            previous_event = (
                AuditEvent.objects.filter(
                    organization_id=current.organization_id,
                    target_id=str(latest.pk),
                    action__in=[ACTION, "hub.reconciliation.native_titles_translated"],
                ).first()
                if latest
                else None
            )
            snapshot, created = import_title_snapshot(
                financial_account=current,
                content=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
                actor=actor,
                evidence_reference=review["evidence_reference"],
                activate_existing=True,
            )
            if created:
                saved = snapshot.source_file
            proposed = proposed_provenance(
                account=current, job=source.capture, payload=payload, provenance=provenance
            )
            persist_native_provenance(
                account=current,
                snapshot=snapshot,
                proposed=proposed,
                installments={(item["title_key"], item["installment_key"]) for item in provenance},
                previous=latest,
            )
            restored = latest is not None and snapshot.pk != latest.pk and not created
            if created or restored:
                record_event(
                    action=ACTION,
                    actor=actor,
                    organization=current.organization,
                    target=snapshot,
                    request=request,
                    metadata={
                        "capture_id": str(capture_id),
                        "source_sha256": source.evidence.expected_sha256,
                        "review_sha256": canonical_hash(review),
                        "provenance": provenance,
                        "previous_snapshot_id": str(latest.pk) if latest else None,
                        "previous_fingerprint": latest.fingerprint if latest else None,
                        "previous_review_event_id": str(previous_event.pk)
                        if previous_event
                        else None,
                        "activated_existing": restored,
                        "evidence_reference": review["evidence_reference"],
                        "bank_linkage": "unproven",
                        "settlements_complete": False,
                    },
                )
            return snapshot, created or restored
    except Exception:
        if saved is not None:
            saved.content.delete(save=False)
        raise
