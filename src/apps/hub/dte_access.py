"""Explicit, metered opening of a Caixa Postal message with legal audit evidence."""

from __future__ import annotations

import json
import re
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.cnpj import normalize_cnpj
from apps.hub.dte_payload import DtePayloadError, detail_row, source_date, value
from apps.hub.models import DteMessage, DteMessageAccess
from apps.integra.client import IntegraClient
from apps.integra.errors import IntegraConfigurationError, IntegraError, IntegraServiceError
from apps.integra.parties import author_cnpj_for
from apps.organizations.models import Membership
from apps.platform.billing import BillingError, reserve_usage, settle_usage
from apps.platform.models import TokenUsageEvent, UsageEvent
from apps.platform.token_billing import reserve_tokens, settle_tokens

DETAIL_ACTION_CODE = "caixapostal.detalhe"


class DteAccessError(RuntimeError):
    pass


def _finish(
    access: DteMessageAccess,
    *,
    status: DteMessageAccess.Status,
    error: str = "",
    row: dict[str, Any] | None = None,
    request_id: str = "",
) -> DteMessageAccess:
    with transaction.atomic():
        locked = DteMessageAccess.objects.select_for_update().get(pk=access.pk)
        locked.status = status
        locked.error_message = error[:240]
        if row is not None:
            locked.provider_payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
            locked.provider_read_at = source_date(row.get("dataLeitura"), row.get("horaLeitura"))
            locked.provider_science_at = source_date(row.get("dataCiencia"))
            locked.opened_at = timezone.now()
            locked.provider_request_id = request_id[:160]
        locked.save()
        return locked


def open_message(
    *,
    message: DteMessage,
    actor: Any,
    request: Any = None,
    approved_overage: bool = False,
    approved_overage_cents: int | None = None,
) -> DteMessageAccess:
    """Open once; a timeout stays uncertain and is never retried automatically."""

    membership = Membership.objects.filter(
        organization=message.organization, user=actor, is_active=True
    ).first()
    if membership is None or not (
        membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
        or (membership.role == Membership.Role.OPERATOR and membership.can_acknowledge_dte)
    ):
        raise DteAccessError("Seu perfil não pode confirmar ciência da Caixa Postal.")
    try:
        cnpj = normalize_cnpj(message.company.cnpj_masked)
    except ValidationError as exc:
        raise DteAccessError("CNPJ da empresa inválido para o Serpro.") from exc
    if re.fullmatch(r"\d{1,10}", message.source_isn) is None:
        raise DteAccessError("CNPJ ou identificador da mensagem inválido para o Serpro.")
    with transaction.atomic():
        access = DteMessageAccess.objects.select_for_update().filter(message=message).first()
        if access and access.status == DteMessageAccess.Status.OPENED:
            return access
        if access and access.status in {
            DteMessageAccess.Status.READING,
            DteMessageAccess.Status.UNKNOWN,
        }:
            raise DteAccessError(
                "A abertura já está em andamento ou seu resultado precisa de conferência. "
                "A Mewstack deve confirmar o retorno antes de outra tentativa."
            )
        attempt = (access.attempt_count if access else 0) + 1
        key = f"dte-message-detail:{message.id}:{attempt}"
        usage: TokenUsageEvent | UsageEvent
        try:
            usage = reserve_tokens(
                organization=message.organization,
                module_code="integra",
                action_code=DETAIL_ACTION_CODE,
                idempotency_key=key,
            )
        except BillingError:
            try:
                usage = reserve_usage(
                    organization=message.organization,
                    action_code=DETAIL_ACTION_CODE,
                    idempotency_key=key,
                    approved_overage=approved_overage,
                    approved_overage_cents=approved_overage_cents,
                    require_explicit_overage=True,
                )
            except BillingError as legacy_exc:
                raise DteAccessError(str(legacy_exc)) from legacy_exc
        if access is None:
            access = DteMessageAccess.objects.create(
                organization=message.organization,
                message=message,
                status=DteMessageAccess.Status.READING,
                attempt_count=attempt,
                requested_by=actor,
                token_usage_event=usage if isinstance(usage, TokenUsageEvent) else None,
                usage_event=None if isinstance(usage, TokenUsageEvent) else usage,
            )
        else:
            access.status = DteMessageAccess.Status.READING
            access.attempt_count = attempt
            access.requested_by = actor
            access.requested_at = timezone.now()
            access.error_message = ""
            access.save()
            if isinstance(usage, TokenUsageEvent):
                access.token_usage_event = usage
                fields = ["token_usage_event", "updated_at"]
            else:
                access.usage_event = usage
                fields = ["usage_event", "updated_at"]
            access.save(update_fields=fields)
        record_event(
            action="hub.dte.message_open_requested",
            actor=actor,
            organization=message.organization,
            target=message,
            request=request,
            metadata={"company_id": str(message.company_id), "isn": message.source_isn},
        )
    try:
        response = IntegraClient().call(
            DETAIL_ACTION_CODE,
            contribuinte=cnpj,
            autor_pedido=author_cnpj_for(message.organization),
            dados={"isn": message.source_isn},
        )
    except IntegraConfigurationError as exc:
        _settle(usage, provider_http_status=503, billable=False)
        _finish(access, status=DteMessageAccess.Status.FAILED, error=str(exc))
        raise DteAccessError("A conexão central não está configurada.") from exc
    except IntegraServiceError as exc:
        _settle(usage, provider_http_status=exc.status, billable=False)
        _finish(access, status=DteMessageAccess.Status.FAILED, error=str(exc))
        raise DteAccessError(str(exc)) from exc
    except IntegraError as exc:
        _finish(access, status=DteMessageAccess.Status.UNKNOWN, error=str(exc))
        raise DteAccessError(
            "O retorno do Serpro ficou incerto. Não repita a abertura antes de conferir a ciência."
        ) from exc

    request_id = value(response, "idRequisicao", "requestId")
    _settle(
        event=usage,
        provider_http_status=int(response.get("status", 200)),
        provider_request_id=request_id,
        billable=True,
    )
    try:
        row = detail_row(response, expected_isn=message.source_isn)
    except DtePayloadError as exc:
        _finish(access, status=DteMessageAccess.Status.UNKNOWN, error=str(exc))
        raise DteAccessError(
            "O Serpro recebeu a abertura, mas o teor não pôde ser conferido. "
            "A Mewstack deve verificar a ciência antes de qualquer nova chamada."
        ) from exc
    receipt = _finish(access, status=DteMessageAccess.Status.OPENED, row=row, request_id=request_id)
    record_event(
        action="hub.dte.message_opened",
        actor=actor,
        organization=message.organization,
        target=message,
        request=request,
        metadata={"company_id": str(message.company_id), "provider_request_id": request_id},
    )
    return receipt


def _settle(event: Any, **kwargs: Any) -> None:
    if isinstance(event, TokenUsageEvent):
        settle_tokens(event=event, **kwargs)
    else:
        settle_usage(event=event, **kwargs)
