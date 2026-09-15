"""Asynchronous, metered Integra Contador work."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.hub.models import DteMessage, DteRun, DteRunItem, FiscalGuide
from apps.hub.reform import refresh_reform_sources
from apps.integra.client import IntegraClient
from apps.integra.errors import IntegraError, IntegraServiceError
from apps.platform.billing import settle_usage
from apps.platform.models import OperationalRun
from apps.platform.operations import track_scheduled_operation


@shared_task(name="hub.refresh_reform_sources")  # type: ignore[untyped-decorator]
@track_scheduled_operation(OperationalRun.Task.REFRESH_REFORM)
def refresh_reform_sources_task() -> dict[str, int]:
    """Collect official Radar updates; each source failure remains isolated."""

    created, updated, failed = refresh_reform_sources()
    return {"created": created, "updated": updated, "failed": failed}


def _messages(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    raw_data = payload.get("dados", {})
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except json.JSONDecodeError:
            return ()
    if not isinstance(raw_data, dict):
        return ()
    for key in ("mensagens", "listaMensagens", "itens"):
        values = raw_data.get(key)
        if isinstance(values, list):
            return (value for value in values if isinstance(value, dict))
    return ()


def _value(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return str(value)
    return ""


def _save_messages(*, item: DteRunItem, payload: dict[str, Any]) -> int:
    saved = 0
    for row in _messages(payload):
        source_id = _value(row, "isn", "id", "identificador", "numero")
        if not source_id:
            continue
        sent_at = parse_datetime(_value(row, "dataEnvio", "data", "sentAt"))
        read_at = parse_datetime(_value(row, "dataLeitura", "readAt"))
        DteMessage.objects.get_or_create(
            organization=item.organization,
            company=item.company,
            source_isn=source_id[:120],
            defaults={
                "subject": _value(row, "assunto", "assuntoModelo", "subject")[:500],
                "sender": _value(row, "remetente", "sender")[:240],
                "sent_at": sent_at,
                "read_at": read_at,
                "raw_payload": json.dumps(row, ensure_ascii=False, sort_keys=True),
            },
        )
        saved += 1
    return saved


@shared_task(name="hub.dispatch_dte_run")  # type: ignore[untyped-decorator]
def dispatch_dte_run(run_id: str) -> None:
    """Run one approved Caixa Postal batch against the centrally contracted API."""

    with transaction.atomic():
        run = DteRun.objects.select_for_update().filter(id=run_id).first()
        if run is None or run.status != DteRun.Status.QUEUED:
            return
        run.status = DteRun.Status.RUNNING
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at", "updated_at"])

    try:
        client: IntegraClient | None = IntegraClient()
    except IntegraError:
        client = None
    completed = 0
    failed = 0
    total_messages = 0
    for item in DteRunItem.objects.select_related("company").filter(
        run=run, status=DteRunItem.Status.PENDING
    ):
        key = f"dte-run-item:{item.id}:caixapostal"
        from apps.platform.models import UsageEvent

        usage = UsageEvent.objects.filter(idempotency_key=key).first()
        if usage is None:
            failed += 1
            continue
        if client is None:
            settle_usage(event=usage, provider_http_status=503, billable=False)
            item.status = DteRunItem.Status.FAILED
            item.error_code = "configuration"
            item.error_message = "A central Integra Contador não está configurada."
            item.completed_at = timezone.now()
            item.save(
                update_fields=[
                    "status",
                    "error_code",
                    "error_message",
                    "completed_at",
                    "updated_at",
                ]
            )
            failed += 1
            continue
        cnpj = re.sub(r"\D", "", item.company.cnpj_masked)
        if len(cnpj) != 14:
            settle_usage(event=usage, provider_http_status=400, billable=False)
            item.status = DteRunItem.Status.FAILED
            item.error_code = "invalid_cnpj"
            item.error_message = "A empresa precisa de um CNPJ válido para a consulta."
            item.completed_at = timezone.now()
            item.save(
                update_fields=[
                    "status",
                    "error_code",
                    "error_message",
                    "completed_at",
                    "updated_at",
                ]
            )
            failed += 1
            continue
        try:
            payload = client.call(
                "caixapostal.mensagens",
                contribuinte=cnpj,
                dados={"statusLeitura": 0, "indicadorPagina": 0, "indicadorFavorito": 0},
            )
        except IntegraServiceError as exc:
            settle_usage(
                event=usage,
                provider_http_status=exc.status,
                billable=False,
            )
            item.status = DteRunItem.Status.FAILED
            item.error_code = exc.code[:80]
            item.error_message = str(exc)[:240]
            item.completed_at = timezone.now()
            item.save(
                update_fields=[
                    "status",
                    "error_code",
                    "error_message",
                    "completed_at",
                    "updated_at",
                ]
            )
            failed += 1
            continue
        except IntegraError as exc:
            settle_usage(event=usage, provider_http_status=503, billable=False)
            item.status = DteRunItem.Status.FAILED
            item.error_code = "transport"
            item.error_message = str(exc)[:240]
            item.completed_at = timezone.now()
            item.save(
                update_fields=[
                    "status",
                    "error_code",
                    "error_message",
                    "completed_at",
                    "updated_at",
                ]
            )
            failed += 1
            continue
        settle_usage(
            event=usage,
            provider_http_status=int(payload.get("status", 200)),
            provider_request_id=_value(payload, "idRequisicao", "requestId"),
            billable=True,
        )
        found = _save_messages(item=item, payload=payload)
        item.status = DteRunItem.Status.COMPLETED
        item.messages_found = found
        item.service_response_id = _value(payload, "idRequisicao", "requestId")[:120]
        item.completed_at = timezone.now()
        item.save(
            update_fields=[
                "status",
                "messages_found",
                "service_response_id",
                "completed_at",
                "updated_at",
            ]
        )
        completed += 1
        total_messages += found

    with transaction.atomic():
        run = DteRun.objects.select_for_update().get(id=run_id)
        run.completed_companies = completed
        run.messages_found = total_messages
        run.completed_at = timezone.now()
        if failed and completed:
            run.status = DteRun.Status.PARTIAL
        elif failed:
            run.status = DteRun.Status.FAILED
        else:
            run.status = DteRun.Status.COMPLETED
        run.save(
            update_fields=[
                "status",
                "completed_companies",
                "messages_found",
                "completed_at",
                "updated_at",
            ]
        )


def _fail_fiscal_guide(
    *, guide: FiscalGuide, usage: Any, code: str, message: str, http_status: int
) -> None:
    settle_usage(event=usage, provider_http_status=http_status, billable=False)
    guide.status = FiscalGuide.Status.FAILED
    guide.error_code = code[:80]
    guide.error_message = message[:240]
    guide.save(update_fields=["status", "error_code", "error_message", "updated_at"])


@shared_task(name="hub.dispatch_fiscal_guide")  # type: ignore[untyped-decorator]
def dispatch_fiscal_guide(guide_id: str) -> None:
    """Issue one ready Domínio obligation with central Serpro credentials."""

    from apps.platform.models import UsageEvent

    with transaction.atomic():
        guide = (
            FiscalGuide.objects.select_for_update()
            .select_related("company")
            .filter(id=guide_id)
            .first()
        )
        if guide is None or guide.status != FiscalGuide.Status.QUEUED:
            return
        guide.status = FiscalGuide.Status.ISSUING
        guide.save(update_fields=["status", "updated_at"])
    usage = UsageEvent.objects.filter(
        idempotency_key=f"fiscal-guide:{guide.id}:{guide.issue_attempt}"
    ).first()
    if usage is None:
        guide.status = FiscalGuide.Status.FAILED
        guide.error_code = "usage_missing"
        guide.error_message = "A reserva de consumo não foi encontrada."
        guide.save(update_fields=["status", "error_code", "error_message", "updated_at"])
        return
    cnpj = re.sub(r"\D", "", guide.company.cnpj_masked)
    if len(cnpj) != 14:
        _fail_fiscal_guide(
            guide=guide,
            usage=usage,
            code="invalid_cnpj",
            message="A empresa precisa de um CNPJ válido para emitir a guia.",
            http_status=400,
        )
        return
    try:
        client = IntegraClient()
        payload = client.call(
            guide.integra_service_key,
            contribuinte=cnpj,
            dados={"competencia": guide.competence},
        )
    except IntegraServiceError as exc:
        _fail_fiscal_guide(
            guide=guide,
            usage=usage,
            code=exc.code or "service",
            message=str(exc),
            http_status=exc.status,
        )
        return
    except IntegraError as exc:
        _fail_fiscal_guide(
            guide=guide,
            usage=usage,
            code="integration",
            message=str(exc),
            http_status=503,
        )
        return
    settle_usage(
        event=usage,
        provider_http_status=int(payload.get("status", 200)),
        provider_request_id=_value(payload, "idRequisicao", "requestId"),
        billable=True,
    )
    guide.status = FiscalGuide.Status.ISSUED
    guide.provider_request_id = _value(payload, "idRequisicao", "requestId")[:160]
    guide.provider_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    guide.issued_at = timezone.now()
    guide.save(
        update_fields=[
            "status",
            "provider_request_id",
            "provider_payload",
            "issued_at",
            "updated_at",
        ]
    )
