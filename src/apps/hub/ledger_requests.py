"""Reviewed monthly ledger requests; no financial payloads or ERP writes here."""

from __future__ import annotations

import hashlib
import hmac
import re
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    ReconciliationAccountCandidate,
    ReconciliationLedgerMapping,
    ReconciliationSourceFile,
)
from apps.hub.title_persistence import _account, authorize_title_account
from apps.hub.title_read_model import authorize_title_read
from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
from apps.intelligence.native_ledger_contract import (
    MAX_BYTES,
    canonical_hash,
    contract_hash,
    is_automatic_scope,
    normalize_snapshot,
    validate_scope,
    validate_snapshot,
)

MAPPING_FIELDS = (
    "company_code",
    "chart_company_code",
    "branch_code",
    "bank_account_code",
    "absent_account_code",
    "bank_inflow_side",
)


class LedgerRequestError(ValueError):
    pass


class LedgerRequestConflict(LedgerRequestError):
    pass


def _code(value: Any, label: str) -> int:
    if isinstance(value, bool) or not re.fullmatch(r"[1-9][0-9]{0,9}", str(value)):
        raise LedgerRequestError(f"Confira {label}: use o código numérico do Domínio.")
    result = int(value)
    if result > 2147483647:
        raise LedgerRequestError(f"Confira {label}: o código excede o limite do Domínio.")
    return result


def _identity(account: FinancialAccount) -> dict[str, Any]:
    return {
        "organization_id": str(account.organization_id),
        "company_id": str(account.company_id),
        "account_id": str(account.pk),
        "company_code": account.company.dominio_code,
        "bank_code": account.bank_code,
        "account_reference": account.account_reference,
        "ledger_code": account.ledger_code,
    }


def _base_fields(account: FinancialAccount) -> dict[str, Any]:
    return {
        "company_code": _code(account.company.dominio_code, "o código da empresa"),
        "bank_account_code": _code(account.ledger_code, "a conta contábil cadastrada"),
        "absent_account_code": 0,
    }


def _mapping_scope(fields: dict[str, Any]) -> dict[str, Any]:
    """Use the existing contract to enforce mapping semantics, not technical counts."""
    scope = validate_scope(
        {
            **fields,
            "capture_id": str(uuid4()),
            "period_start": "2026-09-01",
            "period_end_exclusive": "2026-10-01",
        }
    )
    return {key: scope[key] for key in MAPPING_FIELDS}


def _stored_revision(mapping: ReconciliationLedgerMapping) -> str:
    return canonical_hash(
        {
            "scope": mapping.scope,
            "account_identity": mapping.account_identity,
            "evidence_reference": mapping.evidence_reference,
            "reviewed_by": str(mapping.reviewed_by_id),
            "reviewed_at": mapping.reviewed_at.isoformat(),
            "provenance": mapping.provenance,
        }
    )


def _retained_mapping(account: FinancialAccount) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Reuse intact imported evidence, without inventing a reviewer for legacy captures."""
    matches = []
    for job in (
        NativeLedgerCollection.objects.filter(
            organization_id=account.organization_id,
            financial_account=account,
            state=NativeLedgerCollection.State.IMPORTED,
            source_file__isnull=False,
        )
        .select_related("source_file")
        .order_by("created_at", "id")
    ):
        # New jobs refer to a reviewed mapping; they do not independently replace that review.
        if is_automatic_scope(job.scope):
            continue
        try:
            scope = validate_scope(job.scope)
            if (
                job.scope_revision != canonical_hash(scope)
                or job.contract_hash != contract_hash()
                or scope["company_code"] != _code(account.company.dominio_code, "a empresa")
                or scope["bank_account_code"] != _code(account.ledger_code, "a conta contábil")
            ):
                continue
            source = job.source_file
            if source is None or (
                source.organization_id != account.organization_id
                or source.company_id != account.company_id
                or source.financial_account_id != account.pk
                or source.origin != "accounting"
                or source.kind != "json"
                or source.content_hash != job.content_hash
                or not job.content_hash
                or not 1 <= source.size_bytes <= MAX_BYTES
            ):
                continue
            with source.content.open("rb") as stream:
                content = stream.read(MAX_BYTES + 1)
            if (
                len(content) != source.size_bytes
                or hashlib.sha256(content).hexdigest() != job.content_hash
            ):
                continue
            data = validate_snapshot(content, scope)
            normalize_snapshot(data, scope)
            fields = {key: scope[key] for key in MAPPING_FIELDS}
            matches.append(
                (
                    fields,
                    {
                        "kind": "imported_source",
                        "job_id": str(job.pk),
                        "source_id": str(source.pk),
                        "content_hash": job.content_hash,
                        "scope_revision": job.scope_revision,
                        "requested_by_id": str(job.requested_by_id)
                        if job.requested_by_id
                        else None,
                        "evidence_reference": job.evidence_reference,
                    },
                )
            )
        except (OSError, ValueError, KeyError, TypeError):
            continue
    if not matches:
        return None
    if len({canonical_hash(fields) for fields, _ in matches}) != 1:
        raise LedgerRequestError("As fontes anteriores têm vínculos diferentes. Confira o vínculo.")
    return matches[0]


def _candidate_defaults(account: FinancialAccount) -> dict[str, Any]:
    candidate = ReconciliationAccountCandidate.objects.filter(
        organization_id=account.organization_id,
        company_id=account.company_id,
        financial_account=account,
        state="linked",
        reviewed_at__isnull=False,
        reviewed_by__isnull=False,
    ).first()
    if candidate is None or not isinstance(candidate.review_data, dict):
        return {}
    data = candidate.review_data
    if (
        str(candidate.source_company_code) != account.company.dominio_code
        or str(candidate.account_code) != account.ledger_code
        or data.get("bank_code") != account.bank_code
        or data.get("account_reference") != account.account_reference
        or data.get("bank_inflow_side") not in {"debit", "credit"}
        or any(
            data.get(field) is not True
            for field in (
                "bank_association_confirmed",
                "chart_owner_confirmed",
                "account_active_and_postable",
            )
        )
    ):
        return {}
    return {
        "chart_company_code": candidate.chart_company_code,
        "bank_inflow_side": data["bank_inflow_side"],
    }


def _mapping(account: FinancialAccount) -> dict[str, Any]:
    identity = _identity(account)
    empty_revision = canonical_hash({"identity": identity, "mapping": None})
    fields: dict[str, Any] = {}
    errors = []
    try:
        fields = _base_fields(account)
    except LedgerRequestError as exc:
        errors.append(str(exc))
    stored = ReconciliationLedgerMapping.objects.filter(financial_account=account).first()
    if stored is not None:
        revision = canonical_hash({"identity": identity, "stored": stored.revision})
        try:
            valid_fields = _mapping_scope(stored.scope)
            if (
                stored.organization_id != account.organization_id
                or stored.account_identity != identity
                or stored.revision != _stored_revision(stored)
                or not stored.evidence_reference.strip()
                or any(valid_fields[key] != fields.get(key) for key in _base_fields(account))
            ):
                raise ValueError
            return dict(
                fields=valid_fields,
                revision=revision,
                source="Vínculo revisado",
                provenance=stored.provenance,
                ready=True,
                errors=[],
            )
        except (ValueError, TypeError, KeyError):
            return dict(
                fields=fields,
                revision=revision,
                source="Vínculo precisa de revisão",
                provenance={},
                ready=False,
                errors=[*errors, "A identificação da conta mudou. Confira o vínculo novamente."],
            )
    if not errors:
        try:
            retained = _retained_mapping(account)
            if retained is not None:
                valid_fields, provenance = retained
                return dict(
                    fields=valid_fields,
                    revision=canonical_hash(
                        {"identity": identity, "provenance": provenance, "fields": valid_fields}
                    ),
                    source="Vínculo da fonte já importada",
                    provenance=provenance,
                    ready=True,
                    errors=[],
                )
        except LedgerRequestError as exc:
            errors.append(str(exc))
    fields.update(_candidate_defaults(account))
    return dict(
        fields=fields,
        revision=empty_revision,
        source="Conferência do vínculo",
        provenance={},
        ready=False,
        errors=errors,
    )


def _lock_account(account: FinancialAccount) -> FinancialAccount:
    ClientCompany.objects.select_for_update().get(
        pk=account.company_id,
        organization_id=account.organization_id,
    )
    current = _account(account.pk, lock=True)
    if (
        current.company_id != account.company_id
        or current.organization_id != account.organization_id
    ):
        raise LedgerRequestConflict("A conta mudou. Reabra a solicitação.")
    return current


def _write_access(account: FinancialAccount, actor: User, request: Any = None) -> None:
    if request is not None and getattr(request.user, "pk", None) != actor.pk:
        raise PermissionDenied("Use a identidade da sessão atual para solicitar o Razão.")
    authorize_title_account(account, actor)


@transaction.atomic
def save_ledger_mapping(
    *,
    account: FinancialAccount,
    actor: User,
    expected_revision: str,
    chart_company_code: Any,
    branch_code: Any,
    bank_inflow_side: str,
    evidence_reference: str,
    confirmed: bool,
    request: Any = None,
) -> ReconciliationLedgerMapping:
    account = _lock_account(account)
    _write_access(account, actor, request)
    if not account.bank_code.strip():
        raise LedgerRequestError("Informe o código do banco na configuração da conta.")
    current = _mapping(account)
    if not isinstance(expected_revision, str) or not hmac.compare_digest(
        current["revision"],
        expected_revision,
    ):
        raise LedgerRequestConflict("O vínculo mudou. Reabra a página antes de salvar.")
    if (
        confirmed is not True
        or not isinstance(evidence_reference, str)
        or not evidence_reference.strip()
        or len(evidence_reference) > 240
    ):
        raise LedgerRequestError("Confira o vínculo e informe a referência usada na revisão.")
    fields = _mapping_scope(
        {
            **_base_fields(account),
            "chart_company_code": _code(chart_company_code, "a empresa do plano de contas"),
            "branch_code": _code(branch_code, "a filial"),
            "bank_inflow_side": bank_inflow_side,
        }
    )
    mapping = ReconciliationLedgerMapping.objects.filter(financial_account=account).first()
    history = []
    if mapping is not None:
        if not isinstance(mapping.review_history, list):
            raise LedgerRequestError("O histórico do vínculo precisa de revisão.")
        history = [
            *mapping.review_history,
            {
                "scope": mapping.scope,
                "account_identity": mapping.account_identity,
                "revision": mapping.revision,
                "evidence_reference": mapping.evidence_reference,
                "reviewed_by_id": str(mapping.reviewed_by_id),
                "reviewed_at": mapping.reviewed_at.isoformat(),
                "provenance": mapping.provenance,
            },
        ]
    else:
        mapping = ReconciliationLedgerMapping(
            organization=account.organization, financial_account=account
        )
    mapping.scope = fields
    mapping.account_identity = _identity(account)
    mapping.reviewed_by = actor
    mapping.reviewed_at = timezone.now()
    mapping.evidence_reference = evidence_reference.strip()
    mapping.provenance = {"kind": "human_review", "previous_source": current["provenance"]}
    mapping.review_history = history
    mapping.revision = _stored_revision(mapping)
    mapping.save()
    record_event(
        action="hub.reconciliation.ledger_mapping_reviewed",
        actor=actor,
        organization=account.organization,
        target=mapping,
        request=request,
        metadata={"account_id": str(account.pk), "revision": mapping.revision},
    )
    return mapping


def _month(month: date) -> tuple[date, date]:
    if type(month) is not date or month.day != 1 or month < date(2026, 9, 1):
        raise LedgerRequestError("Escolha uma competência mensal a partir de setembro de 2026.")
    if month.year >= 9999:
        raise LedgerRequestError("Confira a competência solicitada.")
    end = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    return month, end


def _source(account: FinancialAccount, source: Any) -> ReconciliationSourceFile | None:
    if source is None:
        return None
    found = ReconciliationSourceFile.objects.filter(
        pk=getattr(source, "pk", source),
        organization_id=account.organization_id,
        company_id=account.company_id,
        financial_account=account,
        origin="bank_statement",
    ).first()
    if found is None:
        raise LedgerRequestError("Escolha um extrato desta empresa e conta.")
    return found


@transaction.atomic
def request_ledger(
    *,
    account: FinancialAccount,
    actor: User,
    month: date,
    request_key: UUID,
    expected_mapping_revision: str,
    bank_source: ReconciliationSourceFile | None = None,
    request: Any = None,
) -> tuple[NativeLedgerCollection, bool]:
    start, end = _month(month)
    try:
        key = UUID(str(request_key))
    except (ValueError, TypeError, AttributeError):
        raise LedgerRequestError("Reabra a página para preparar uma nova solicitação.") from None
    agent = (
        EdgeAgent.objects.select_for_update()
        .filter(
            organization_id=account.organization_id,
            is_official=True,
            status=EdgeAgent.Status.ACTIVE,
        )
        .first()
    )
    if agent is None:
        raise LedgerRequestError("Ative o agente oficial do escritório para buscar o Razão.")
    account = _lock_account(account)
    _write_access(account, actor, request)
    source = _source(account, bank_source)
    mapping = _mapping(account)
    existing = NativeLedgerCollection.objects.filter(
        organization_id=account.organization_id,
        request_key=key,
    ).first()
    if existing is not None:
        if (
            existing.financial_account_id != account.pk
            or existing.requested_by_id != actor.pk
            or existing.scope.get("period_start") != start.isoformat()
            or existing.mapping_revision != expected_mapping_revision
            or existing.bank_source_id != (source.pk if source else None)
        ):
            raise LedgerRequestConflict("Esta solicitação já foi usada. Reabra a página.")
        return existing, False
    if not isinstance(expected_mapping_revision, str) or not hmac.compare_digest(
        mapping["revision"],
        expected_mapping_revision,
    ):
        raise LedgerRequestConflict("O vínculo mudou. Confira os dados antes de solicitar.")
    if not mapping["ready"]:
        raise LedgerRequestError("Confira o vínculo com o Domínio antes de buscar o Razão.")
    identifier = uuid4()
    scope = validate_scope(
        {
            **mapping["fields"],
            "capture_id": str(identifier),
            "period_start": start.isoformat(),
            "period_end_exclusive": end.isoformat(),
        }
    )
    job = NativeLedgerCollection.objects.create(
        pk=identifier,
        organization=account.organization,
        agent=agent,
        financial_account=account,
        requested_by=actor,
        evidence_reference="Solicitação mensal pela interface; vínculo " + mapping["revision"],
        scope=scope,
        scope_revision=canonical_hash(scope),
        contract_hash=contract_hash(),
        request_key=key,
        mapping_revision=mapping["revision"],
        bank_source=source,
    )
    record_event(
        action="hub.reconciliation.ledger_requested",
        actor=actor,
        organization=account.organization,
        target=job,
        request=request,
        metadata={
            "account_id": str(account.pk),
            "scope_revision": job.scope_revision,
            "mapping_revision": job.mapping_revision,
        },
    )
    return job, True


def validate_job_mapping(job: NativeLedgerCollection) -> bool:
    try:
        job = NativeLedgerCollection.objects.get(pk=job.pk)
        account = _account(job.financial_account_id)
        mapping = _mapping(account)
        return bool(
            job.organization_id == account.organization_id
            and mapping["ready"]
            and job.mapping_revision == mapping["revision"]
            and all(job.scope.get(key) == mapping["fields"].get(key) for key in MAPPING_FIELDS)
            and (job.bank_source_id is None or _source(account, job.bank_source_id) is not None)
        )
    except (
        ValueError,
        FinancialAccount.DoesNotExist,
        NativeLedgerCollection.DoesNotExist,
        KeyError,
        TypeError,
    ):
        return False


def _agent_state(agent: EdgeAgent | None) -> dict[str, str]:
    if agent is None or not agent.is_official or agent.status != EdgeAgent.Status.ACTIVE:
        return dict(
            code="missing",
            label="Agente não configurado",
            detail="Ative o agente oficial do escritório para buscar o Razão.",
        )
    capabilities = agent.ledger_capabilities
    if (
        not isinstance(capabilities, dict)
        or type(capabilities.get("automatic_counts")) is not bool
        or agent.ledger_capabilities_observed_at is None
    ):
        return dict(
            code="unknown",
            label="Aguardando confirmação do agente",
            detail="Confira se o agente CICA está em execução no computador do Domínio.",
        )
    if capabilities["automatic_counts"] is not True:
        return dict(
            code="outdated",
            label="Agente precisa de atualização",
            detail="Atualize o agente CICA no computador do Domínio. O pedido fica na fila.",
            installer_url=getattr(settings, "EDGE_AGENT_INSTALLER_URL", ""),
        )
    if agent.last_seen_at is None or agent.last_seen_at < timezone.now() - timedelta(minutes=5):
        return dict(
            code="offline",
            label="Agente sem conexão recente",
            detail="Confira se o computador do Domínio está ligado e conectado à internet.",
        )
    return dict(code="online", label="Agente conectado", detail="Aguardando a próxima verificação.")


def ledger_request_context(*, account: FinancialAccount, actor: User) -> dict[str, Any]:
    account = _account(account.pk)
    authorize_title_read(account, actor)
    mapping = _mapping(account)
    agent = EdgeAgent.objects.filter(
        organization_id=account.organization_id, is_official=True, status=EdgeAgent.Status.ACTIVE
    ).first()
    errors = list(mapping["errors"])
    if not mapping["ready"] and not account.bank_code.strip():
        errors.append("Informe o código do banco na configuração da conta.")
    if not account.active:
        errors.append("Ative esta conta na configuração antes de solicitar o Razão.")
    if not account.account_reference:
        errors.append("Confira a agência e conta na configuração.")
    return {
        "account": account,
        "readiness": mapping["ready"] and agent is not None and not errors,
        "needs_mapping": not mapping["ready"],
        "mapping_fields": mapping["fields"],
        "mapping_revision": mapping["revision"],
        "mapping_source": mapping["source"],
        "errors": errors,
        "agent_state": _agent_state(agent),
        "current_jobs": [
            ledger_job_context(job=job, actor=actor)
            for job in NativeLedgerCollection.objects.filter(
                organization_id=account.organization_id,
                financial_account=account,
            ).order_by("-created_at", "-id")[:20]
        ],
    }


def ledger_job_context(*, job: NativeLedgerCollection, actor: User) -> dict[str, Any]:
    job = NativeLedgerCollection.objects.select_related(
        "financial_account__company",
        "financial_account__organization",
        "agent",
        "source_file",
        "bank_source",
    ).get(pk=job.pk)
    account = job.financial_account
    authorize_title_read(account, actor)
    if (
        job.organization_id != account.organization_id
        or job.agent.organization_id != account.organization_id
    ):
        raise PermissionDenied("Solicitação fora do escritório desta conta.")
    scope = validate_scope(job.scope)
    if job.scope_revision != canonical_hash(scope):
        raise LedgerRequestError("A solicitação precisa de revisão de integridade.")
    if job.source_file is not None and (
        job.source_file.organization_id != account.organization_id
        or job.source_file.company_id != account.company_id
        or job.source_file.financial_account_id != account.pk
        or job.source_file.origin != "accounting"
        or job.source_file.kind != "json"
        or job.source_file.content_hash != job.content_hash
    ):
        raise LedgerRequestError("A fonte recebida precisa de revisão do vínculo com a conta.")
    if not isinstance(job.result, dict):
        raise LedgerRequestError("O resultado da solicitação precisa de revisão de integridade.")
    status = job.state
    detail = "O agente buscará o Razão quando estiver conectado."
    label = "Na fila"
    requester_valid = True
    if status == "queued" and is_automatic_scope(scope):
        try:
            if job.requested_by is None:
                raise PermissionDenied
            authorize_title_account(account, job.requested_by)
        except (PermissionDenied, ValueError):
            requester_valid = False
    if status == "queued" and is_automatic_scope(scope) and not validate_job_mapping(job):
        status, label = "review", "Vínculo alterado"
        detail = "Confira o vínculo atual e faça uma nova solicitação; esta coleta será preservada."
    elif status == "queued" and not requester_valid:
        status, label = "review", "Acesso do solicitante alterado"
        detail = "Faça uma nova solicitação com seu acesso atual para retomar a busca do Razão."
    elif status == "queued" and (
        not job.agent.is_official or job.agent.status != EdgeAgent.Status.ACTIVE
    ):
        status, label = "review", "Agente desta solicitação desativado"
        detail = "Faça uma nova solicitação para usar o agente oficial atual do escritório."
    elif status == "queued" and job.error_code:
        label = "Nova tentativa automática"
        detail = (
            "O agente não concluiu a leitura e tentará novamente. Confira sua conexão ao Domínio."
        )
    elif status == "queued" and job.claimed_at:
        status, label = "delivered", "Solicitação entregue ao agente"
        detail = "Aguardando o resultado da leitura do Domínio."
    elif status == "imported":
        if job.result.get("source_rows") == 0:
            status, label = "empty", "Sem lançamentos neste período"
            detail = "A fonte recebida não contém lançamentos para este vínculo e competência."
        else:
            label, detail = (
                "Razão recebido",
                "Os dados recebidos estão disponíveis para conferência.",
            )
    elif status == "review":
        label = "Revisão necessária"
        detail = {
            "ledger_records_removed": (
                "Lotes anteriores não aparecem nesta leitura. Confira a fonte no Domínio."
            ),
            "ledger_content_conflict": (
                "Lotes anteriores mudaram. Confira a fonte; o histórico foi preservado."
            ),
        }.get(
            job.error_code, "Confira o vínculo e a fonte do Domínio antes de solicitar novamente."
        )
    elif status == "failed":
        label, detail = "Coleta não concluída", "Confira o agente e solicite novamente."
    can_write = True
    try:
        authorize_title_account(account, actor)
    except (PermissionDenied, ValueError):
        can_write = False
    source_url = ""
    if job.bank_source_id:
        bank_source = _source(account, job.bank_source_id)
        if bank_source is not None:
            source_url = (
                reverse("hub:reconciliation-source-review", args=[bank_source.pk])
                + "?"
                + urlencode(
                    {
                        "start": scope["period_start"],
                        "end": (
                            date.fromisoformat(scope["period_end_exclusive"]) - timedelta(days=1)
                        ).isoformat(),
                    }
                )
            )
    return {
        "job": job,
        "status": status,
        "label": label,
        "detail": detail,
        "can_retry": can_write and status in {"review", "failed"},
        "source_file": job.source_file,
        "bank_source": job.bank_source,
        "source_url": source_url,
        "resultcounts": {
            key: value
            for key, value in job.result.items()
            if key in {"created", "ignored", "source_rows", "bank_effects"} and type(value) is int
        },
        "month": date.fromisoformat(scope["period_start"]),
        "mapping_revision": job.mapping_revision,
        "agent_state": _agent_state(job.agent),
    }


def retry_ledger_request(
    *,
    job: NativeLedgerCollection,
    actor: User,
    request_key: UUID,
    expected_mapping_revision: str,
    request: Any = None,
) -> tuple[NativeLedgerCollection, bool]:
    current = NativeLedgerCollection.objects.select_related("financial_account", "bank_source").get(
        pk=job.pk,
    )
    context = ledger_job_context(job=current, actor=actor)
    if not context["can_retry"]:
        raise LedgerRequestError(
            "Acompanhe a solicitação atual; ela não precisa de retomada manual."
        )
    return request_ledger(
        account=current.financial_account,
        actor=actor,
        month=context["month"],
        request_key=request_key,
        expected_mapping_revision=expected_mapping_revision,
        bank_source=current.bank_source,
        request=request,
    )
