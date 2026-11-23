"""Atomic human enrollment of a retained account candidate; never collect ERP data."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.account_candidate_forms import AccountCandidateDismissForm, AccountCandidateLinkForm
from apps.hub.controlplane import company_queryset_for_module
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    LedgerAccount,
    ProductModule,
    ReconciliationAccountCandidate,
)
from apps.organizations.models import Membership
from apps.platform.operation_access import require_operation_access

CHECKS = ("bank_association_confirmed", "chart_owner_confirmed", "account_active_and_postable")
LINK_FIELDS = ("name", "bank_code", "account_reference", "bank_inflow_side", *CHECKS)


class CandidateReviewError(ValueError):
    pass


class CandidateReviewConflict(CandidateReviewError):
    pass


def _locked_candidate(candidate: ReconciliationAccountCandidate) -> ReconciliationAccountCandidate:
    try:
        current = ReconciliationAccountCandidate.objects.only(
            "organization_id",
            "company_id",
        ).get(pk=candidate.pk)
        if (current.organization_id, current.company_id) != (
            candidate.organization_id,
            candidate.company_id,
        ):
            raise CandidateReviewError("A origem da candidata mudou. Reabra a conferência.")
        # Company first serializes different candidates sharing an account/reference.
        ClientCompany.objects.select_for_update().get(
            pk=current.company_id,
            organization_id=current.organization_id,
        )
        return (
            ReconciliationAccountCandidate.objects.select_for_update(of=("self",))
            .select_related(
                "company",
                "organization",
                "financial_account",
            )
            .get(
                pk=current.pk,
                organization_id=current.organization_id,
                company_id=current.company_id,
            )
        )
    except (ReconciliationAccountCandidate.DoesNotExist, ClientCompany.DoesNotExist):
        raise CandidateReviewError("A candidata não está disponível para revisão.") from None


def _access(
    candidate: ReconciliationAccountCandidate,
    actor: User,
    authorized_companies: QuerySet[ClientCompany],
    request: Any,
) -> None:
    if request is not None and getattr(request.user, "pk", None) != actor.pk:
        raise PermissionDenied("A revisão precisa usar a identidade da sessão atual.")
    membership = (
        Membership.objects.select_related("organization")
        .filter(
            organization_id=candidate.organization_id,
            user=actor,
            user__is_active=True,
            is_active=True,
            role__in=["owner", "admin", "manager", "operator"],
        )
        .first()
    )
    if (
        membership is None
        or candidate.company.organization_id != candidate.organization_id
        or not candidate.company.active
        or not authorized_companies.filter(
            pk=candidate.company_id,
            organization_id=candidate.organization_id,
        ).exists()
        or not company_queryset_for_module(membership, ProductModule.Code.RECONCILIATION)
        .filter(pk=candidate.company_id)
        .exists()
    ):
        raise PermissionDenied("Seu acesso atual não permite revisar contas desta empresa.")
    try:
        require_operation_access(candidate.organization, ProductModule.Code.RECONCILIATION)
    except ValueError as exc:
        raise CandidateReviewError(str(exc)) from exc


def _source(candidate: ReconciliationAccountCandidate, data: dict[str, Any]) -> None:
    expected_codes = {
        "company_code": candidate.source_company_code,
        "chart_company_code": candidate.chart_company_code,
        "account_code": candidate.account_code,
    }
    try:
        evidence = candidate.evidence
        retained = evidence["candidate"]
        sources = evidence["sources"]
        observed = datetime.fromisoformat(sources["configured_accounts"]["observed_at_utc"])
        valid = (
            data["expected_source_hash"] == candidate.source_file_sha256
            and data["expected_state"] == "pending"
            and candidate.company.dominio_code == str(candidate.source_company_code)
            and all(type(code) is int and code > 0 for code in expected_codes.values())
            and candidate.source_key == ":".join(str(code) for code in expected_codes.values())
            and evidence["version"] == "reconciliation-account-candidates-v1"
            and all(retained[key] == value for key, value in expected_codes.items())
            and retained["candidate_key"] == candidate.source_key
            and sources["configured_accounts"]["input_file_sha256"] == candidate.source_file_sha256
            and sources["portfolio"]["input_file_sha256"] == candidate.portfolio_file_sha256
            and observed == candidate.source_observed_at
            and all(
                re.fullmatch(r"[0-9a-f]{64}", value)
                for value in (
                    candidate.source_file_sha256,
                    candidate.portfolio_file_sha256,
                )
            )
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        valid = False
    if not valid:
        raise CandidateReviewError(
            "A fonte ou a empresa mudou. Reabra a candidata antes de revisar."
        )


def _form_data(
    form_class: Any, candidate: ReconciliationAccountCandidate, cleaned_data: dict[str, Any]
) -> dict[str, Any]:
    form = form_class(cleaned_data, candidate=candidate)
    if not form.is_valid():
        raise CandidateReviewError("Complete os dados e as confirmações da revisão.")
    if form_class is AccountCandidateLinkForm and any(
        cleaned_data.get(field) is not True for field in CHECKS
    ):
        raise CandidateReviewError("Confirme explicitamente os três vínculos antes de cadastrar.")
    return dict(form.cleaned_data)


def _financial_matches(
    account: FinancialAccount, candidate: ReconciliationAccountCandidate, data: dict[str, Any]
) -> bool:
    return bool(
        account.organization_id == candidate.organization_id
        and account.company_id == candidate.company_id
        and account.active
        and account.ledger_code == str(candidate.account_code)
        and all(
            getattr(account, key) == data[key]
            for key in (
                "name",
                "bank_code",
                "account_reference",
            )
        )
    )


def _review_data(candidate: ReconciliationAccountCandidate, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": "linked",
        **{field: data[field] for field in LINK_FIELDS},
        "source_company_code": candidate.source_company_code,
        "chart_company_code": candidate.chart_company_code,
        "account_code": candidate.account_code,
        "source_file_sha256": candidate.source_file_sha256,
        "portfolio_file_sha256": candidate.portfolio_file_sha256,
    }


def _pending(candidate: ReconciliationAccountCandidate) -> None:
    if (
        candidate.state != "pending"
        or candidate.financial_account_id
        or candidate.reviewed_by_id
        or candidate.reviewed_at
        or candidate.review_data
        or candidate.review_evidence
    ):
        raise CandidateReviewError(
            "Esta revisão já foi encerrada. Os dados anteriores foram preservados."
        )


@transaction.atomic
def finalize_candidate(
    *,
    candidate: ReconciliationAccountCandidate,
    actor: User,
    authorized_companies: QuerySet[ClientCompany],
    cleaned_data: dict[str, Any],
    request: Any = None,
) -> ReconciliationAccountCandidate:
    candidate = _locked_candidate(candidate)
    _access(candidate, actor, authorized_companies, request)
    data = _form_data(AccountCandidateLinkForm, candidate, cleaned_data)
    _source(candidate, data)
    reviewed = _review_data(candidate, data)
    existing_ledger = list(
        LedgerAccount.objects.select_for_update().filter(
            company_id=candidate.company_id,
            code=str(candidate.account_code),
        )
    )
    if len(existing_ledger) > 1 or any(
        row.organization_id != candidate.organization_id
        or not row.active
        or not row.accepts_entries
        or row.name != data["name"]
        for row in existing_ledger
    ):
        raise CandidateReviewError(
            "A conta contábil existente diverge da revisão. Nenhum dado foi alterado."
        )
    existing_accounts = list(
        FinancialAccount.objects.select_for_update().filter(
            Q(account_reference=data["account_reference"])
            | Q(ledger_code=str(candidate.account_code)),
            company_id=candidate.company_id,
        )
    )
    if len(existing_accounts) > 1 or any(
        not _financial_matches(row, candidate, data) for row in existing_accounts
    ):
        raise CandidateReviewError(
            "A conta financeira existente diverge da revisão. Nenhum dado foi alterado."
        )
    if candidate.state == "linked":
        if (
            candidate.review_data == reviewed
            and candidate.review_evidence == data["evidence_reference"]
            and candidate.reviewed_by_id
            and candidate.reviewed_at
            and len(existing_ledger) == len(existing_accounts) == 1
            and existing_accounts[0].pk == candidate.financial_account_id
        ):
            return candidate
        raise CandidateReviewError(
            "Esta candidata já foi vinculada. A revisão anterior foi preservada."
        )
    _pending(candidate)
    try:
        with transaction.atomic():
            ledger = (
                existing_ledger[0]
                if existing_ledger
                else LedgerAccount.objects.create(
                    organization_id=candidate.organization_id,
                    company_id=candidate.company_id,
                    code=str(candidate.account_code),
                    name=data["name"],
                    active=True,
                    accepts_entries=True,
                )
            )
            account = (
                existing_accounts[0]
                if existing_accounts
                else FinancialAccount.objects.create(
                    organization_id=candidate.organization_id,
                    company_id=candidate.company_id,
                    name=data["name"],
                    bank_code=data["bank_code"],
                    account_reference=data["account_reference"],
                    ledger_code=str(candidate.account_code),
                    active=True,
                )
            )
            candidate.state = ReconciliationAccountCandidate.State.LINKED
            candidate.financial_account = account
            candidate.reviewed_by = actor
            candidate.reviewed_at = timezone.now()
            candidate.review_data = reviewed
            candidate.review_evidence = data["evidence_reference"]
            candidate.save(
                update_fields=[
                    "state",
                    "financial_account",
                    "reviewed_by",
                    "reviewed_at",
                    "review_data",
                    "review_evidence",
                    "updated_at",
                ]
            )
            record_event(
                action="hub.reconciliation.account_candidate.linked",
                organization=candidate.organization,
                actor=actor,
                target=candidate,
                request=request,
                metadata={
                    "company_id": str(candidate.company_id),
                    "financial_account_id": str(account.pk),
                    "ledger_account_id": str(ledger.pk),
                    "source_file_sha256": candidate.source_file_sha256,
                    "portfolio_file_sha256": candidate.portfolio_file_sha256,
                    "created_financial_account": not existing_accounts,
                    "created_ledger_account": not existing_ledger,
                },
            )
    except IntegrityError:
        raise CandidateReviewError(
            "O cadastro foi alterado simultaneamente. Reabra e confira os dados."
        ) from None
    return candidate


@transaction.atomic
def dismiss_candidate(
    *,
    candidate: ReconciliationAccountCandidate,
    actor: User,
    authorized_companies: QuerySet[ClientCompany],
    cleaned_data: dict[str, Any],
    request: Any = None,
) -> ReconciliationAccountCandidate:
    candidate = _locked_candidate(candidate)
    _access(candidate, actor, authorized_companies, request)
    data = _form_data(AccountCandidateDismissForm, candidate, cleaned_data)
    _source(candidate, data)
    reviewed = {"decision": "dismissed", "reason": data["reason"]}
    if candidate.state == "dismissed":
        if (
            candidate.review_data == reviewed
            and candidate.review_evidence == data["reason"]
            and candidate.reviewed_by_id
            and candidate.reviewed_at
            and not candidate.financial_account_id
        ):
            return candidate
        raise CandidateReviewError(
            "Esta revisão já foi encerrada. A decisão anterior foi preservada."
        )
    _pending(candidate)
    candidate.state = ReconciliationAccountCandidate.State.DISMISSED
    candidate.reviewed_by = actor
    candidate.reviewed_at = timezone.now()
    candidate.review_data = reviewed
    candidate.review_evidence = data["reason"]
    candidate.save(
        update_fields=[
            "state",
            "reviewed_by",
            "reviewed_at",
            "review_data",
            "review_evidence",
            "updated_at",
        ]
    )
    record_event(
        action="hub.reconciliation.account_candidate.dismissed",
        organization=candidate.organization,
        actor=actor,
        target=candidate,
        request=request,
        metadata={
            "company_id": str(candidate.company_id),
            "source_file_sha256": candidate.source_file_sha256,
            "portfolio_file_sha256": candidate.portfolio_file_sha256,
        },
    )
    return candidate


def candidate_revision(candidate: ReconciliationAccountCandidate) -> str:
    from apps.hub.setup_review import account_revision

    account = candidate.financial_account if candidate.financial_account_id else None
    ledger = (
        LedgerAccount.objects.filter(
            organization_id=candidate.organization_id,
            company_id=candidate.company_id,
            code=str(candidate.account_code),
        )
        .values("id", "name", "active", "accepts_entries", "updated_at")
        .first()
    )
    state = {
        "id": str(candidate.pk),
        "state": candidate.state,
        "organization_id": str(candidate.organization_id),
        "company_id": str(candidate.company_id),
        "reviewed_by_id": str(candidate.reviewed_by_id) if candidate.reviewed_by_id else None,
        "reviewed_at": candidate.reviewed_at.isoformat() if candidate.reviewed_at else None,
        "updated_at": candidate.updated_at.isoformat(),
        "review_data": candidate.review_data,
        "review_evidence": candidate.review_evidence,
        "history": candidate.review_history,
        "source": candidate.source_file_sha256,
        "ledger": ledger,
        "account": account_revision(account) if account is not None else None,
    }
    return hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest()


@transaction.atomic
def revise_candidate(
    *,
    candidate: ReconciliationAccountCandidate,
    actor: User,
    authorized_companies: QuerySet[ClientCompany],
    cleaned_data: dict[str, Any],
    reopen: bool = False,
    request: Any = None,
) -> ReconciliationAccountCandidate:
    from apps.hub.account_candidate_forms import (
        AccountCandidateCorrectionForm,
        AccountCandidateReopenForm,
    )
    from apps.hub.setup_review import account_snapshot, account_usage_reasons

    candidate = _locked_candidate(candidate)
    _access(candidate, actor, authorized_companies, request)
    form_type = AccountCandidateReopenForm if reopen else AccountCandidateCorrectionForm
    data = _form_data(form_type, candidate, cleaned_data)
    _source(candidate, data)
    expected = "dismissed" if reopen else "linked"
    if candidate.state != expected:
        raise CandidateReviewConflict("A situação mudou. Reabra o vínculo para conferir.")
    account = None
    ledger = None
    if not reopen:
        if candidate.financial_account_id is None:
            raise CandidateReviewError("O cadastro vinculado não está disponível nesta empresa.")
        account = (
            FinancialAccount.objects.select_for_update()
            .filter(
                pk=candidate.financial_account_id,
                organization_id=candidate.organization_id,
                company_id=candidate.company_id,
            )
            .first()
        )
        if account is None:
            raise CandidateReviewError("O cadastro vinculado não está disponível nesta empresa.")
        candidate.financial_account = account
        ledger = (
            LedgerAccount.objects.select_for_update()
            .filter(
                organization_id=candidate.organization_id,
                company_id=candidate.company_id,
                code=str(candidate.account_code),
            )
            .first()
        )
    if not hmac.compare_digest(data["expected_revision"], candidate_revision(candidate)):
        raise CandidateReviewConflict("A revisão mudou. Reabra a página antes de corrigir.")
    previous = {
        "state": candidate.state,
        "review_data": candidate.review_data,
        "review_evidence": candidate.review_evidence,
        "reviewed_by_id": str(candidate.reviewed_by_id) if candidate.reviewed_by_id else None,
        "reviewed_at": candidate.reviewed_at.isoformat() if candidate.reviewed_at else None,
        "financial_account_id": str(candidate.financial_account_id)
        if candidate.financial_account_id
        else None,
        "reason": data["reason"],
        "changed_by_id": str(actor.pk),
        "changed_at": timezone.now().isoformat(),
    }
    if not reopen:
        if any(cleaned_data.get(field) is not True for field in CHECKS):
            raise CandidateReviewError("Confira novamente os três vínculos antes de corrigir.")
        assert account is not None
        if account_usage_reasons(account):
            raise CandidateReviewError(
                "Esta conta já possui fontes, lançamentos ou coletas. O vínculo usado precisa "
                "ser preservado; solicite ao responsável a análise dos registros existentes."
            )
        if (
            ReconciliationAccountCandidate.objects.filter(financial_account=account)
            .exclude(pk=candidate.pk)
            .exists()
        ):
            raise CandidateReviewError(
                "Esta conta é compartilhada com outro vínculo. Revise os cadastros."
            )
        previous["financial_account"] = account_snapshot(account)
        if (
            ledger is None
            or not ledger.active
            or not ledger.accepts_entries
            or account.ledger_code != str(candidate.account_code)
        ):
            raise CandidateReviewError(
                "O plano ou o cadastro diverge da revisão. Confira a configuração."
            )
        if (
            ledger.name != data["name"]
            and FinancialAccount.objects.filter(
                company_id=candidate.company_id,
                ledger_code=account.ledger_code,
            )
            .exclude(pk=account.pk)
            .exists()
        ):
            raise CandidateReviewError(
                "A conta contábil é compartilhada; seu nome precisa ser preservado."
            )
        if (
            FinancialAccount.objects.filter(
                company_id=candidate.company_id, account_reference=data["account_reference"]
            )
            .exclude(pk=account.pk)
            .exists()
        ):
            raise CandidateReviewError("Já existe uma conta com esta referência para a empresa.")
        previous["ledger_name"] = ledger.name
        for field in ("name", "bank_code", "account_reference"):
            setattr(account, field, data[field])
        account.active = True
        account.save(
            update_fields=["name", "bank_code", "account_reference", "active", "updated_at"]
        )
        ledger.name = data["name"]
        ledger.save(update_fields=["name", "updated_at"])
    elif candidate.financial_account_id:
        raise CandidateReviewError(
            "A candidata possui uma conta vinculada. Confira a revisão atual."
        )
    candidate.review_history = [*candidate.review_history, previous]
    candidate.state = "pending"
    candidate.financial_account = None
    candidate.reviewed_by = None
    candidate.reviewed_at = None
    candidate.review_data = {}
    candidate.review_evidence = ""
    candidate.save(
        update_fields=[
            "review_history",
            "state",
            "financial_account",
            "reviewed_by",
            "reviewed_at",
            "review_data",
            "review_evidence",
            "updated_at",
        ]
    )
    if not reopen:
        candidate = finalize_candidate(
            candidate=candidate,
            actor=actor,
            authorized_companies=authorized_companies,
            cleaned_data=data,
            request=request,
        )
    record_event(
        action="hub.reconciliation.account_candidate.reopened"
        if reopen
        else "hub.reconciliation.account_candidate.corrected",
        organization=candidate.organization,
        actor=actor,
        target=candidate,
        request=request,
        metadata={
            "company_id": str(candidate.company_id),
            "reason": data["reason"],
            "previous_revision": data["expected_revision"],
            "history_count": len(candidate.review_history),
        },
    )
    return candidate
