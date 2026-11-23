"""Minimal, attributed confirmation of immutable discovery facts; never collect data."""

from __future__ import annotations

import hmac
import re
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.account_candidate_review import CandidateReviewError, _access
from apps.hub.account_discovery_contract import Invalid
from apps.hub.account_discovery_contract import text as source_text
from apps.hub.ledger_requests import (
    LedgerRequestError,
    _code,
    _identity,
    _mapping,
    _mapping_scope,
    _stored_revision,
    discovery_mapping_month_allowed,
)
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    LedgerAccount,
    ReconciliationAccountCandidate,
    ReconciliationCompanyDiscovery,
    ReconciliationDiscoveredChartAccount,
    ReconciliationLedgerMapping,
)
from apps.hub.setup_review import account_usage_reasons
from apps.intelligence.native_ledger_contract import canonical_hash
from apps.organizations.models import Organization

CHECKS = frozenset(
    {
        "bank_association_confirmed",
        "account_active_and_postable",
        "chart_owner_confirmed",
        "branch_scope_confirmed",
    }
)
EDITABLE = CHECKS | {"bank_code", "account_reference", "bank_inflow_side", "branch_code"}
KIND = "discovered_account_review"
SOURCE_FIELDS = frozenset(
    {
        "company_code",
        "chart_company_code",
        "account_code",
        "name",
        "classification_raw",
        "account_type_raw",
        "account_status_raw",
        "inactive_on_raw",
        "branch_code",
    }
)


class DiscoveryReviewError(ValueError):
    pass


class DiscoveryReviewConflict(DiscoveryReviewError):
    pass


def _text(value: Any, maximum: int, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise DiscoveryReviewError("Confira os dados da conta antes de confirmar.")
    value = value.strip()
    if (
        (required and not value)
        or len(value) > maximum
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise DiscoveryReviewError("Confira a identificação da conta e os limites dos campos.")
    return str(value)


def _source_name(value: Any) -> str:
    """Validate a source fact without trimming or replacing its literal text."""
    try:
        source_text(value, 150)
    except Invalid:
        raise DiscoveryReviewError("O nome consultado está fora do contrato da fonte.") from None
    if not value.strip() or "\0" in value:
        raise DiscoveryReviewError(
            "O nome consultado exige tratamento da fonte antes de cadastrar esta conta."
        )
    return str(value)


def _data(prepared: dict[str, Any], supplied: Any) -> dict[str, Any]:
    pending = prepared.get("pending_fields")
    if (
        not isinstance(pending, list)
        or len(set(pending)) != len(pending)
        or not set(pending) <= EDITABLE
        or not isinstance(supplied, dict)
        or set(supplied) - set(pending) - {"evidence_reference"}
    ):
        raise DiscoveryReviewError("Os campos de conferência mudaram. Reabra a conta.")
    result = {}
    for field in pending:
        value = supplied.get(field)
        if field in CHECKS:
            if value is not True:
                raise DiscoveryReviewError("Complete as confirmações indicadas para esta conta.")
        elif field == "branch_code":
            try:
                value = _code(value, "a filial")
            except LedgerRequestError as exc:
                raise DiscoveryReviewError(str(exc)) from exc
            branches = [branch for branch in prepared.get("branches", []) if branch > 0]
            if branches and value not in branches:
                raise DiscoveryReviewError("Escolha uma das filiais observadas nesta competência.")
        elif field == "bank_inflow_side":
            if not isinstance(value, str) or value not in {"debit", "credit"}:
                raise DiscoveryReviewError("Confira o lado das entradas no Razão.")
        else:
            value = _text(value, 20 if field == "bank_code" else 160)
        result[field] = value
    # An optional note is not evidence invented by the application. Store it separately.
    note = supplied.get("evidence_reference", "")
    if (
        not isinstance(note, str)
        or len(note.strip()) > 1000
        or any((ord(char) < 32 and char not in "\n\r\t") or ord(char) == 127 for char in note)
    ):
        raise DiscoveryReviewError("Confira a observação da conferência.")
    result["evidence_reference"] = note.strip()
    return result


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


def _result(
    account: FinancialAccount, mapping: Any, *, created: bool = False, replayed: bool = False
) -> dict[str, Any]:
    return {
        "financial_account": account,
        "mapping": mapping,
        "created": created,
        "replayed": replayed,
        "reused_existing": not created,
    }


def _replay(
    mapping: Any, company: Any, chart: Any, month: str, revision: str, supplied: Any
) -> bool:
    if mapping is None or not isinstance(mapping.provenance, dict):
        return False
    provenance = mapping.provenance
    if provenance.get("kind") != KIND or not isinstance(supplied, dict):
        return False
    for review in provenance.get("confirmations", []):
        if (
            review.get("month") == month
            and review.get("prepared_revision") == revision
            and review.get("source_identity") == discovery_source_identity(company, chart)
        ):
            data = _data(
                {
                    "pending_fields": review["confirmed_fields"],
                    "branches": review["observed_branches"],
                },
                supplied,
            )
            return bool(review.get("submission_sha256") == canonical_hash(data))
    return False


@transaction.atomic
def confirm_discovered_account(
    *,
    company_discovery: ReconciliationCompanyDiscovery,
    chart_account: ReconciliationDiscoveredChartAccount,
    month: str,
    actor: User,
    authorized_companies: QuerySet[ClientCompany],
    expected_revision: str,
    confirmed_data: dict[str, Any],
    request: Any = None,
) -> dict[str, Any]:
    """Derive facts again under locks; only the current session actor confirms missing facts."""
    from apps.hub.account_discovery import _consistent_discovery, prepared_account_facts

    if not isinstance(month, str) or not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month):
        raise DiscoveryReviewError("Confira a competência da conta.")
    if not "2026-09" <= month < "9999-01":
        raise DiscoveryReviewError("Escolha uma competência a partir de setembro de 2026.")
    if not isinstance(expected_revision, str) or not re.fullmatch(
        "[0-9a-f]{64}", expected_revision
    ):
        raise DiscoveryReviewConflict("Reabra a conta para conferir a fonte atual.")
    try:
        Organization.objects.select_for_update(no_key=True).get(
            pk=company_discovery.organization_id,
        )
        company = (
            ClientCompany.objects.select_for_update()
            .select_related("organization")
            .get(
                pk=company_discovery.company_id,
                organization_id=company_discovery.organization_id,
            )
        )
        access_scope = ReconciliationAccountCandidate(
            organization=company.organization,
            company=company,
        )
        _access(access_scope, actor, authorized_companies, request)
        coverage = ReconciliationCompanyDiscovery.objects.select_related(
            "discovery", "company"
        ).get(
            pk=company_discovery.pk,
            company=company,
            organization=company.organization,
        )
        chart = ReconciliationDiscoveredChartAccount.objects.select_related("discovery").get(
            pk=chart_account.pk,
            discovery=coverage.discovery,
            organization=company.organization,
        )
    except (
        Organization.DoesNotExist,
        ClientCompany.DoesNotExist,
        ReconciliationCompanyDiscovery.DoesNotExist,
        ReconciliationDiscoveredChartAccount.DoesNotExist,
    ):
        raise DiscoveryReviewError(
            "A conta não está disponível neste escritório e empresa."
        ) from None
    except CandidateReviewError as exc:
        raise DiscoveryReviewError(str(exc)) from exc
    prepared = prepared_account_facts(coverage, chart, month=month)
    if not prepared.get("valid") or not _consistent_discovery(coverage.discovery, deep=True):
        raise DiscoveryReviewConflict("A fonte mudou ou está inconsistente. Reabra a conta.")
    if prepared.get("blocking_reason") == "previously_dismissed_candidate":
        raise DiscoveryReviewError(
            "Esta candidata já foi descartada. Reconsidere a decisão na ficha existente "
            "antes de preparar um novo vínculo."
        )
    if not prepared.get("collection_ready") and (
        prepared.get("blocking_reason") or prepared.get("branches") == [0]
    ):
        raise DiscoveryReviewError(
            "A origem informou filial zero nesta competência. "
            "O agente atual não suporta esse escopo; o catálogo foi preservado."
        )
    code = str(chart.account_code)
    existing = list(
        FinancialAccount.objects.select_for_update()
        .filter(
            company=company,
            ledger_code=code,
        )
        .select_related("company", "organization")
    )
    if len(existing) > 1 or any(row.organization_id != company.organization_id for row in existing):
        raise DiscoveryReviewConflict(
            "Há contas divergentes para este código. Confira os vínculos."
        )
    account = existing[0] if existing else None
    mapping = (
        ReconciliationLedgerMapping.objects.select_for_update()
        .filter(
            financial_account=account,
        )
        .first()
        if account
        else None
    )
    current = _mapping(account) if account else None
    if account and current and current["ready"] and account.active:
        if current["fields"].get("chart_company_code") != chart.chart_company_code:
            raise DiscoveryReviewConflict(
                "A conta já utiliza outro plano. A revisão foi preservada."
            )
        if discovery_mapping_month_allowed(account, mapping, month):
            if _replay(mapping, coverage, chart, month, expected_revision, confirmed_data):
                return _result(account, mapping, replayed=True)
            if (
                prepared.get("collection_ready")
                and not prepared["pending_fields"]
                and hmac.compare_digest(prepared["revision"], expected_revision)
                and not (set(confirmed_data) - {"evidence_reference"})
            ):
                _data(prepared, confirmed_data)
                return _result(account, mapping)
            raise DiscoveryReviewConflict(
                "Este vínculo já foi confirmado. A revisão foi preservada."
            )
    if not hmac.compare_digest(prepared["revision"], expected_revision):
        raise DiscoveryReviewConflict(
            "A fonte ou o vínculo mudou. Reabra a conta antes de confirmar."
        )
    try:
        data = _data(prepared, confirmed_data)
        known = prepared["known_fields"]
        values = {**known, **data}
        name = _source_name(known["name"])
        bank_code = _text(values.get("bank_code"), 20)
        reference = _text(values.get("account_reference"), 160)
        scope = _mapping_scope(
            {
                "company_code": _code(company.dominio_code, "a empresa"),
                "chart_company_code": chart.chart_company_code,
                "branch_code": _code(values.get("branch_code"), "a filial"),
                "bank_account_code": chart.account_code,
                "absent_account_code": 0,
                "bank_inflow_side": values.get("bank_inflow_side"),
            }
        )
        if known["company_code"] != scope["company_code"] or (
            known["chart_company_code"],
            known["account_code"],
        ) != (chart.chart_company_code, chart.account_code):
            raise DiscoveryReviewConflict("A identidade da conta mudou. Reabra a conferência.")
    except DiscoveryReviewError:
        raise
    except (ValueError, KeyError, TypeError) as exc:
        raise DiscoveryReviewError("Confira os dados e as confirmações da conta.") from exc
    conflicts = list(
        FinancialAccount.objects.select_for_update().filter(
            Q(account_reference=reference) | Q(ledger_code=code),
            company=company,
        )
    )
    if len(conflicts) > 1 or any(
        row.organization_id != company.organization_id
        or not row.active
        or row.ledger_code != code
        or row.bank_code != bank_code
        or row.account_reference != reference
        for row in conflicts
    ):
        raise DiscoveryReviewConflict(
            "A conta existente diverge da conferência. Nada foi alterado."
        )
    if account and (not current or not current["ready"]) and account_usage_reasons(account):
        raise DiscoveryReviewConflict("Esta conta já tem movimentos. Confira o vínculo existente.")
    if mapping and (
        not current
        or not current["ready"]
        or mapping.provenance.get("kind") != KIND
        or mapping.scope != scope
    ):
        raise DiscoveryReviewConflict(
            "O vínculo existente diverge. A revisão anterior foi preservada."
        )
    ledgers = list(LedgerAccount.objects.select_for_update().filter(company=company, code=code))
    if len(ledgers) > 1 or any(
        row.organization_id != company.organization_id or not row.active or not row.accepts_entries
        for row in ledgers
    ):
        raise DiscoveryReviewConflict("Confira a conta contábil já cadastrada antes de vincular.")
    now = timezone.now()
    source = discovery_source_identity(coverage, chart)
    confirmation = {
        "month": month,
        "prepared_revision": prepared["revision"],
        "source_identity": source,
        "proof": prepared["proof"],
        "source_fields": sorted(set(known) & SOURCE_FIELDS),
        "retained_review_fields": sorted(set(known) - SOURCE_FIELDS),
        "confirmed_fields": sorted(prepared["pending_fields"]),
        "observed_branches": prepared.get("branches", []),
        "submission_sha256": canonical_hash(data),
        "note": data["evidence_reference"],
        "actor_id": str(actor.pk),
        "confirmed_at": now.isoformat(),
    }
    created = account is None
    try:
        with transaction.atomic():
            if not ledgers:
                LedgerAccount.objects.create(
                    organization=company.organization,
                    company=company,
                    code=code,
                    name=name,
                    active=True,
                    accepts_entries=True,
                )
            if account is None:
                account = FinancialAccount.objects.create(
                    organization=company.organization,
                    company=company,
                    name=name,
                    bank_code=bank_code,
                    account_reference=reference,
                    ledger_code=code,
                    active=True,
                )
            history = list(mapping.review_history) if mapping else []
            previous = list(mapping.provenance["confirmations"]) if mapping else []
            if mapping:
                history.append(
                    {
                        "scope": mapping.scope,
                        "account_identity": mapping.account_identity,
                        "revision": mapping.revision,
                        "evidence_reference": mapping.evidence_reference,
                        "reviewed_by": str(mapping.reviewed_by_id),
                        "reviewed_at": mapping.reviewed_at.isoformat(),
                        "provenance": mapping.provenance,
                    }
                )
            else:
                mapping = ReconciliationLedgerMapping(
                    organization=company.organization,
                    financial_account=account,
                )
            confirmations = [*previous, confirmation]
            mapping.scope = scope
            mapping.account_identity = _identity(account)
            mapping.reviewed_by = actor
            mapping.reviewed_at = now
            mapping.evidence_reference = (
                f"Vínculo confirmado na ficha do Domínio; competência {month}; "
                f"fonte SHA256 {source['source_file_sha256']}."
            )
            mapping.provenance = {
                "kind": KIND,
                "confirmations": confirmations,
                "source_fields": confirmation["source_fields"],
                "confirmed_fields": confirmation["confirmed_fields"],
                "period_scope": {
                    "version": 1,
                    "allowed_months": sorted({item["month"] for item in confirmations}),
                    "branches": [scope["branch_code"]],
                },
            }
            mapping.review_history = history
            mapping.revision = _stored_revision(mapping)
            mapping.save()
            if not discovery_mapping_month_allowed(account, mapping, month):
                raise DiscoveryReviewConflict("A conferência não preservou a fonte e o período.")
            record_event(
                action="hub.reconciliation.discovered_account_confirmed",
                actor=actor,
                organization=company.organization,
                target=mapping,
                request=request,
                metadata={
                    "account_id": str(account.pk),
                    "revision": mapping.revision,
                    "source_file_sha256": source["source_file_sha256"],
                    "month": month,
                    "created": created,
                    "source_fields": confirmation["source_fields"],
                    "confirmed_fields": confirmation["confirmed_fields"],
                },
            )
    except IntegrityError as exc:
        raise DiscoveryReviewConflict("O vínculo mudou durante a revisão. Reabra a conta.") from exc
    return _result(account, mapping, created=created)
