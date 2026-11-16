"""Audited corrections to manual account setup, preserving financial identities in use."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.controlplane import company_queryset_for_module
from apps.hub.models import (
    AccountingEntry,
    BankStatementImport,
    ClientCompany,
    FinancialAccount,
    JournalLine,
    LedgerAccount,
    OfxTransactionIdentity,
    ProductModule,
    ReconciliationAccountCandidate,
    ReconciliationLedgerMapping,
)
from apps.intelligence.models import AgentEnrollment, EdgeAgent
from apps.organizations.models import Membership
from apps.platform.operation_access import require_operation_access

ACCOUNT_FIELDS = ("name", "bank_code", "account_reference", "ledger_code", "active")
IDENTITY_FIELDS = ("bank_code", "account_reference", "ledger_code")


class SetupReviewError(ValueError):
    pass


class SetupReviewConflict(SetupReviewError):
    pass


def account_snapshot(account: FinancialAccount) -> dict[str, Any]:
    return {field: getattr(account, field) for field in ACCOUNT_FIELDS}


def account_revision(account: FinancialAccount) -> str:
    state = {
        **account_snapshot(account),
        "id": str(account.pk),
        "organization": str(account.organization_id),
        "company": str(account.company_id),
        "updated_at": account.updated_at.isoformat(),
        "history": account.review_history,
    }
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


def account_integrity_errors(account: FinancialAccount) -> dict[str, str]:
    """Complete setup required for new identities/activation, never retroactive to legacy use."""
    errors = {}
    if not account.bank_code.strip():
        errors["bank_code"] = "Informe o código do banco conferido."
    if not account.account_reference.strip():
        errors["account_reference"] = "Informe a agência e a conta identificadas no extrato."
    if not account.ledger_code.strip() or not LedgerAccount.objects.filter(
        organization_id=account.organization_id, company_id=account.company_id,
        code=account.ledger_code, active=True, accepts_entries=True,
    ).exists():
        errors["ledger_code"] = (
            "Escolha uma conta contábil ativa que aceite lançamentos desta empresa."
        )
    return errors


def account_usage_reasons(account: FinancialAccount) -> tuple[str, ...]:
    """Inspect associations without opening source files or reading agent credentials.

    Include all direct foreign keys so new financial consumers also protect identity.
    Candidate review has its own correction route and is checked separately.
    """
    reasons = []
    for relation in FinancialAccount._meta.related_objects:
        model = relation.related_model
        if model in (ReconciliationAccountCandidate, ReconciliationLedgerMapping):
            continue
        if model._default_manager.filter(**{relation.field.name: account.pk}).exists():
            reasons.append(model._meta.label_lower)
    scope = {"organization_id": account.organization_id, "company_id": account.company_id}
    if account.account_reference:
        for model in (AccountingEntry, BankStatementImport, OfxTransactionIdentity):
            if model.objects.filter(**scope, account_reference=account.account_reference).exists():
                reasons.append(model._meta.label_lower)
    if account.ledger_code and JournalLine.objects.filter(
        organization_id=account.organization_id, entry__company_id=account.company_id,
        entry__organization_id=account.organization_id, account_code=account.ledger_code,
    ).exists():
        reasons.append("hub.journalline")
    for model in (EdgeAgent, AgentEnrollment):
        if model.objects.filter(
            organization_id=account.organization_id,
            sync_scope__financial_account_id=str(account.pk),
        ).exists():
            reasons.append(model._meta.label_lower)
    return tuple(reasons)


def _access(account: FinancialAccount, actor: User,
            authorized_companies: QuerySet[ClientCompany], request: Any) -> None:
    if request is not None and getattr(request.user, "pk", None) != actor.pk:
        raise PermissionDenied("A correção precisa usar a identidade da sessão atual.")
    membership = Membership.objects.select_related("organization").filter(
        organization_id=account.organization_id, user=actor, user__is_active=True,
        is_active=True, role__in=["owner", "admin", "manager", "operator"],
    ).first()
    if (
        membership is None or not account.company.active
        or account.company.organization_id != account.organization_id
        or not authorized_companies.filter(
            pk=account.company_id, organization_id=account.organization_id,
        ).exists()
        or not company_queryset_for_module(membership, ProductModule.Code.RECONCILIATION)
        .filter(pk=account.company_id).exists()
    ):
        raise PermissionDenied("Seu acesso atual não permite alterar contas desta empresa.")
    try:
        require_operation_access(account.organization, ProductModule.Code.RECONCILIATION)
    except ValueError as exc:
        raise SetupReviewError(str(exc)) from exc


@transaction.atomic
def review_financial_account(*, account: FinancialAccount, actor: User,
                             authorized_companies: QuerySet[ClientCompany],
                             cleaned_data: dict[str, Any], request: Any = None,
                             ) -> FinancialAccount:
    from apps.hub.setup_forms import FinancialAccountEditForm

    try:
        ClientCompany.objects.select_for_update().get(
            pk=account.company_id, organization_id=account.organization_id,
        )
        current = FinancialAccount.objects.select_for_update(of=("self",)).select_related(
            "organization", "company",
        ).get(pk=account.pk, organization_id=account.organization_id, company_id=account.company_id)
    except (ClientCompany.DoesNotExist, FinancialAccount.DoesNotExist):
        raise SetupReviewConflict(
            "A conta mudou. Reabra a configuração antes de corrigir."
        ) from None
    _access(current, actor, authorized_companies, request)
    form = FinancialAccountEditForm(cleaned_data, account=current)
    if not form.is_valid():
        raise SetupReviewError("Confira os dados e informe o motivo da correção.")
    data = form.cleaned_data
    if not hmac.compare_digest(data["expected_revision"], account_revision(current)):
        raise SetupReviewConflict(
            "A conta foi alterada. Reabra a página para conferir a revisão atual."
        )
    linked_account = ReconciliationAccountCandidate.objects.filter(
        financial_account=current, state=ReconciliationAccountCandidate.State.LINKED,
    ).exists()
    before = account_snapshot(current)
    if linked_account and any(
        data[field] != before[field] for field in ("name", *IDENTITY_FIELDS)
    ):
        raise SetupReviewConflict(
            "Nesta tela, altere somente a situação ativa da conta. Nome e identificação "
            "devem ser corrigidos pela revisão do vínculo."
        )
    if not isinstance(current.review_history, list):
        raise SetupReviewConflict("O histórico desta conta precisa de revisão antes da correção.")
    identity_changed = any(data[field] != before[field] for field in IDENTITY_FIELDS)
    if identity_changed and account_usage_reasons(current):
        raise SetupReviewError(
            "Esta conta já possui fontes, lançamentos ou coletas. Banco, referência e conta "
            "contábil precisam ser preservados; você pode corrigir o nome."
        )
    for field in ACCOUNT_FIELDS:
        setattr(current, field, data[field])
    # A name correction/deactivation must not invalidate a previously used legacy pilot.
    if (
        identity_changed or (current.active and not before["active"])
    ) and (errors := account_integrity_errors(current)):
        raise SetupReviewError(" ".join(errors.values()))
    after = account_snapshot(current)
    if after == before:
        raise SetupReviewError("Altere ao menos um dado da conta antes de salvar.")
    current.review_history = [*current.review_history, {
        "before": before, "after": after, "reason": data["reason"],
        "actor_id": str(actor.pk), "occurred_at": timezone.now().isoformat(),
        "previous_revision": data["expected_revision"],
    }]
    try:
        with transaction.atomic():
            current.save(update_fields=[*ACCOUNT_FIELDS, "review_history", "updated_at"])
    except IntegrityError:
        raise SetupReviewError("Já existe uma conta com esta referência para a empresa.") from None
    record_event(
        action="hub.reconciliation.financial_account.corrected", actor=actor,
        organization=current.organization, target=current, request=request,
        metadata={"company_id": str(current.company_id),
                  "changed_fields": [field for field in ACCOUNT_FIELDS
                                     if before[field] != after[field]],
                  "history_count": len(current.review_history),
                  "previous_revision": data["expected_revision"],
                  "revision": account_revision(current)},
    )
    return current
