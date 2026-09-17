"""Asynchronous, metered Integra Contador work."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.common.cnpj import normalize_cnpj
from apps.hub.dte_payload import DtePayloadError, list_rows, source_date, subject, value
from apps.hub.models import (
    DctfWebDocument,
    DteMessage,
    DteMessageObservation,
    DteMessageState,
    DteRun,
    DteRunItem,
    FiscalGuide,
    NfseSync,
    ParcelamentoOperation,
)
from apps.hub.nfse_adn import AdnClient, AdnError
from apps.hub.nfse_sync import certificate_ssl_context, process_sync_pages
from apps.hub.reconciliation_service import process_run
from apps.hub.reform import refresh_reform_sources
from apps.integra.client import IntegraClient
from apps.integra.dctfweb import extract_pdf, monthly_request_data
from apps.integra.errors import IntegraError, IntegraServiceError
from apps.integra.parcelamento import (
    ParcelamentoPayloadError,
    detalhe,
    parcelas_disponiveis,
    pdf_das,
    pedidos,
)
from apps.integra.parties import author_cnpj_for
from apps.platform.billing import settle_usage
from apps.platform.models import OperationalRun, TokenUsageEvent
from apps.platform.operations import track_scheduled_operation
from apps.platform.token_billing import settle_tokens


def _eligible_nfse_syncs():  # type: ignore[no-untyped-def]
    return NfseSync.objects.filter(
        enabled=True,
        status__in=[NfseSync.Status.IDLE, NfseSync.Status.RETRY],
        organization__is_active=True,
        organization__is_demo=False,
        company__active=True,
        certificate__isnull=False,
    )


@shared_task(name="hub.dispatch_active_nfse_syncs")  # type: ignore[untyped-decorator]
def dispatch_active_nfse_syncs() -> int:
    """Queue only company feeds explicitly activated by an office administrator."""

    if not settings.NFSE_ADN_SYNC_ENABLED:
        return 0
    now = timezone.now()
    ids = (
        _eligible_nfse_syncs()
        .filter(Q(next_run_at__isnull=True) | Q(next_run_at__lte=now))
        .filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now))
        .order_by("next_run_at", "last_success_at", "pk")
        .values_list("pk", flat=True)[:500]
    )
    queued = 0
    for sync_id in ids:
        poll_nfse_sync.delay(str(sync_id))
        queued += 1
    return queued


@shared_task(name="hub.poll_nfse_sync")  # type: ignore[untyped-decorator]
def poll_nfse_sync(sync_id: str) -> dict[str, int | str]:
    if not settings.NFSE_ADN_SYNC_ENABLED:
        return {"state": "disabled"}
    try:
        parsed_id = uuid.UUID(sync_id)
    except (ValueError, AttributeError):
        return {"state": "invalid_id"}
    now = timezone.now()
    token = uuid.uuid4()
    lease_seconds = max(600, int(settings.CELERY_TASK_TIME_LIMIT) + 60)
    acquired = (
        _eligible_nfse_syncs()
        .filter(pk=parsed_id)
        .filter(Q(next_run_at__isnull=True) | Q(next_run_at__lte=now))
        .filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now))
        .update(
            lease_token=token,
            lease_until=now + timedelta(seconds=lease_seconds),
            status=NfseSync.Status.RUNNING,
            last_run_at=now,
        )
    )
    if not acquired:
        return {"state": "inactive_or_busy"}
    try:
        sync = NfseSync.objects.select_related("company", "certificate", "organization").get(
            pk=parsed_id
        )
        if sync.certificate is None:
            raise ValidationError("A sincronização não possui certificado A1.")
        context = certificate_ssl_context(sync.certificate)
        client = AdnClient(environment=settings.NFSE_ADN_ENVIRONMENT, ssl_context=context)
        return process_sync_pages(sync=sync, client=client)
    except (AdnError, ValidationError, ValueError) as exc:
        transient = isinstance(exc, AdnError) and exc.transient
        current = NfseSync.objects.filter(pk=parsed_id).first()
        failure_count = min((current.failure_count if current else 0) + 1, 15)
        delay_minutes = min(15 * (2 ** (failure_count - 1)), 360)
        NfseSync.objects.filter(pk=parsed_id).update(
            status=NfseSync.Status.RETRY if transient else NfseSync.Status.ERROR,
            last_error_code=getattr(exc, "code", "configuration")[:80],
            last_error_message=str(exc)[:500],
            last_error_at=timezone.now(),
            failure_count=failure_count,
            next_run_at=(timezone.now() + timedelta(minutes=delay_minutes)) if transient else None,
        )
        return {"state": "retry" if transient else "error"}
    except Exception:
        NfseSync.objects.filter(pk=parsed_id).update(
            status=NfseSync.Status.ERROR,
            last_error_code="unexpected",
            last_error_message="Falha inesperada na coleta ADN. Solicite suporte.",
            last_error_at=timezone.now(),
            next_run_at=None,
        )
        return {"state": "error"}
    finally:
        NfseSync.objects.filter(pk=parsed_id, lease_token=token).update(
            lease_token=None, lease_until=None
        )


@shared_task(name="hub.refresh_reform_sources")  # type: ignore[untyped-decorator]
@track_scheduled_operation(OperationalRun.Task.REFRESH_REFORM)
def refresh_reform_sources_task() -> dict[str, int]:
    """Collect official Radar updates; each source failure remains isolated."""

    created, updated, failed = refresh_reform_sources()
    return {"created": created, "updated": updated, "failed": failed}


@shared_task(name="hub.process_reconciliation_run")  # type: ignore[untyped-decorator]
def process_reconciliation_run(run_id: str) -> dict[str, int | str]:
    """Process one durable reconciliation run. Re-delivery is safe by source keys."""
    return process_run(run_id)


@shared_task(name="hub.dispatch_waiting_reconciliation_runs")  # type: ignore[untyped-decorator]
def dispatch_waiting_reconciliation_runs() -> int:
    """Recover database-backed work that was committed before a broker delivery failed."""

    from apps.hub.models import ReconciliationRun

    run_ids = list(
        ReconciliationRun.objects.filter(state=ReconciliationRun.State.WAITING)
        .order_by("created_at")
        .values_list("id", flat=True)[:100]
    )
    for run_id in run_ids:
        process_reconciliation_run.delay(str(run_id))
    return len(run_ids)


@shared_task(name="hub.recover_reconciliation_runs")  # type: ignore[untyped-decorator]
def recover_reconciliation_runs() -> int:
    """Requeue expired work after a worker restart without mutating completed work."""
    now = timezone.now()
    from apps.hub.models import ReconciliationRun

    with transaction.atomic():
        run_ids = list(
            ReconciliationRun.objects.filter(
                state=ReconciliationRun.State.PROCESSING, lease_until__lt=now
            ).values_list("id", flat=True)
        )
        ReconciliationRun.objects.filter(id__in=run_ids).update(
            state=ReconciliationRun.State.WAITING,
            stage="recovered",
            lease_token=None,
            lease_until=None,
        )
        for run_id in run_ids:
            transaction.on_commit(
                lambda value=str(run_id): process_reconciliation_run.delay(value)
            )
    return len(run_ids)


def _value(row: dict[str, Any], *keys: str) -> str:
    return value(row, *keys)


def _save_messages(*, item: DteRunItem, payload: dict[str, Any]) -> int:
    saved = 0
    rows, _more_available = list_rows(payload)
    for row in rows:
        source_id = _value(row, "isn", "id", "identificador", "numero")
        if not source_id:
            continue
        sent_at = source_date(_value(row, "dataEnvio", "data", "sentAt"), _value(row, "horaEnvio"))
        read_at = source_date(_value(row, "dataLeitura", "readAt"), _value(row, "horaLeitura"))
        science_at = source_date(_value(row, "dataCiencia"))
        message, _created = DteMessage.objects.get_or_create(
            organization=item.organization,
            company=item.company,
            source_isn=source_id[:120],
            defaults={
                "subject": subject(row)[:500],
                "sender": _value(row, "descricaoOrigem", "remetente", "sender")[:240],
                "sent_at": sent_at,
                "read_at": read_at,
                "source_science_at": science_at,
                "raw_payload": json.dumps(row, ensure_ascii=False, sort_keys=True),
            },
        )
        observation, observation_created = DteMessageObservation.objects.get_or_create(
            organization=item.organization,
            run_item=item,
            message=message,
            defaults={
                "read_at": read_at,
                "science_at": science_at,
                "raw_payload": json.dumps(row, ensure_ascii=False, sort_keys=True),
            },
        )
        state, state_created = DteMessageState.objects.get_or_create(
            organization=item.organization,
            message=message,
            defaults={
                "read_at": read_at,
                "science_at": science_at,
                "last_observation": observation,
                "last_seen_at": observation.observed_at,
            },
        )
        if observation_created and not state_created:
            state.read_at = read_at or state.read_at
            state.science_at = science_at or state.science_at
            state.last_observation = observation
            state.last_seen_at = observation.observed_at
            state.save(update_fields=["read_at", "science_at", "last_observation", "last_seen_at"])
        saved += 1
    return saved


@shared_task(name="hub.dispatch_dte_run")  # type: ignore[untyped-decorator]
def dispatch_dte_run(run_id: str) -> None:
    """Run one approved Caixa Postal batch against the centrally contracted API."""

    with transaction.atomic():
        run = DteRun.objects.select_for_update().filter(id=run_id).first()
        if run is None or run.status != DteRun.Status.QUEUED:
            return
        if run.organization.is_demo:
            _complete_demo_dte_run(run)
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
    for item in DteRunItem.objects.select_related(
        "company", "token_usage_event", "usage_event"
    ).filter(run=run, status=DteRunItem.Status.PENDING):
        usage = item.token_usage_event or item.usage_event
        if usage is None:
            from apps.platform.models import UsageEvent

            usage = UsageEvent.objects.filter(
                idempotency_key=f"dte-run-item:{item.id}:caixapostal"
            ).first()
        if usage is None:
            failed += 1
            continue
        if client is None:
            _settle_provider_usage(event=usage, provider_http_status=503, billable=False)
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
        try:
            cnpj = normalize_cnpj(item.company.cnpj_masked)
        except ValidationError:
            _settle_provider_usage(event=usage, provider_http_status=400, billable=False)
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
            page_data = {"statusLeitura": "0", "indicadorPagina": "0"}
            if item.requested_page_pointer:
                page_data = {
                    "statusLeitura": "0",
                    "indicadorPagina": "1",
                    "ponteiroPagina": item.requested_page_pointer,
                }
            payload = client.call(
                "caixapostal.mensagens",
                contribuinte=cnpj,
                autor_pedido=author_cnpj_for(item.organization),
                dados=page_data,
            )
        except IntegraServiceError as exc:
            _settle_provider_usage(
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
            _settle_provider_usage(event=usage, provider_http_status=503, billable=False)
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
        _settle_provider_usage(
            event=usage,
            provider_http_status=int(payload.get("status", 200)),
            provider_request_id=_value(payload, "idRequisicao", "requestId"),
            billable=True,
        )
        try:
            from apps.hub.dte_payload import list_page

            _rows, more_available, next_pointer = list_page(payload)
            if next_pointer and next_pointer == item.requested_page_pointer:
                raise DtePayloadError("O Serpro repetiu o ponteiro da página atual.")
            found = _save_messages(item=item, payload=payload)
        except DtePayloadError as exc:
            item.status = DteRunItem.Status.FAILED
            item.error_code = "provider_payload"
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
        item.status = DteRunItem.Status.COMPLETED
        item.messages_found = found
        item.more_available = more_available
        item.next_page_pointer = next_pointer
        item.service_response_id = _value(payload, "idRequisicao", "requestId")[:120]
        item.completed_at = timezone.now()
        item.save(
            update_fields=[
                "status",
                "messages_found",
                "more_available",
                "next_page_pointer",
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


def _complete_demo_dte_run(run: DteRun) -> None:
    """Complete a fabricated office's list locally without Serpro or billable usage."""

    now = timezone.now()
    completed = 0
    messages_found = 0
    for item in DteRunItem.objects.filter(run=run, status=DteRunItem.Status.PENDING):
        usage = item.token_usage_event or item.usage_event
        if usage is not None:
            _settle_provider_usage(event=usage, provider_http_status=200, billable=False)
        found = DteMessage.objects.filter(
            organization=run.organization, company_id=item.company_id
        ).count()
        item.status = DteRunItem.Status.COMPLETED
        item.messages_found = found
        item.more_available = False
        item.next_page_pointer = ""
        item.service_response_id = f"DEMO-{str(item.id)[:12]}"
        item.completed_at = now
        item.save(
            update_fields=[
                "status",
                "messages_found",
                "more_available",
                "next_page_pointer",
                "service_response_id",
                "completed_at",
                "updated_at",
            ]
        )
        completed += 1
        messages_found += found
    run.status = DteRun.Status.COMPLETED
    run.started_at = now
    run.completed_at = now
    run.completed_companies = completed
    run.messages_found = messages_found
    run.save(
        update_fields=[
            "status",
            "started_at",
            "completed_at",
            "completed_companies",
            "messages_found",
            "updated_at",
        ]
    )


def _fail_fiscal_guide(
    *, guide: FiscalGuide, usage: Any, code: str, message: str, http_status: int
) -> None:
    _settle_provider_usage(event=usage, provider_http_status=http_status, billable=False)
    guide.status = FiscalGuide.Status.FAILED
    guide.error_code = code[:80]
    guide.error_message = message[:240]
    guide.save(update_fields=["status", "error_code", "error_message", "updated_at"])


def _settle_provider_usage(
    *, event: Any, provider_http_status: int, provider_request_id: str = "", billable: bool
) -> None:
    """Settle new token events while preserving queued legacy consultations."""

    if isinstance(event, TokenUsageEvent):
        settle_tokens(
            event=event,
            provider_http_status=provider_http_status,
            provider_request_id=provider_request_id,
            billable=billable,
        )
    else:
        settle_usage(
            event=event,
            provider_http_status=provider_http_status,
            provider_request_id=provider_request_id,
            billable=billable,
        )


@shared_task(name="hub.dispatch_dctfweb_document")  # type: ignore[untyped-decorator]
def dispatch_dctfweb_document(document_id: str) -> None:
    """Collect one approved DCTFWeb PDF and keep uncertain calls reconcilable."""

    with transaction.atomic():
        document = (
            DctfWebDocument.objects.select_for_update()
            .select_related("company", "usage_event", "token_usage_event")
            .filter(id=document_id)
            .first()
        )
        if document is None or document.status != DctfWebDocument.Status.QUEUED:
            return
        document.status = DctfWebDocument.Status.FETCHING
        document.save(update_fields=["status", "updated_at"])

    if document.organization.is_demo:
        sample_pdf = b"%PDF-1.4\n%CICA demo DCTFWeb document\n%%EOF"
        import base64

        document.provider_request_id = f"DEMO-{str(document.id)[:12]}"
        document.provider_payload = json.dumps(
            {
                "simulated": True,
                "dados": json.dumps({"PDFByteArrayBase64": base64.b64encode(sample_pdf).decode()}),
            },
            ensure_ascii=False,
        )
        document.status = DctfWebDocument.Status.AVAILABLE
        document.completed_at = timezone.now()
        document.save(
            update_fields=[
                "status",
                "provider_request_id",
                "provider_payload",
                "completed_at",
                "updated_at",
            ]
        )
        return

    usage = document.token_usage_event or document.usage_event
    if usage is None:
        document.status = DctfWebDocument.Status.FAILED
        document.error_code = "usage_missing"
        document.error_message = "A reserva de consumo não foi encontrada."
        document.save(update_fields=["status", "error_code", "error_message", "updated_at"])
        return
    try:
        cnpj = normalize_cnpj(document.company.cnpj_masked)
        payload = IntegraClient().call(
            document.service_key,
            contribuinte=cnpj,
            autor_pedido=author_cnpj_for(document.organization),
            dados=monthly_request_data(document.competence),
        )
    except IntegraServiceError as exc:
        _settle_provider_usage(event=usage, provider_http_status=exc.status, billable=False)
        document.status = DctfWebDocument.Status.FAILED
        document.error_code = (exc.code or "service")[:80]
        document.error_message = str(exc)[:240]
        document.completed_at = timezone.now()
        document.save(
            update_fields=[
                "status",
                "error_code",
                "error_message",
                "completed_at",
                "updated_at",
            ]
        )
        return
    except (ValidationError, ValueError) as exc:
        _settle_provider_usage(event=usage, provider_http_status=400, billable=False)
        document.status = DctfWebDocument.Status.FAILED
        document.error_code = "invalid_request"
        document.error_message = str(exc)[:240]
        document.completed_at = timezone.now()
        document.save(
            update_fields=[
                "status",
                "error_code",
                "error_message",
                "completed_at",
                "updated_at",
            ]
        )
        return
    except IntegraError as exc:
        # A transport failure may happen after the gateway accepted the request.
        # Keep the reservation and require reconciliation instead of retrying and
        # risking a duplicate charge.
        document.status = DctfWebDocument.Status.UNKNOWN
        document.error_code = "uncertain_result"
        document.error_message = str(exc)[:240]
        document.save(update_fields=["status", "error_code", "error_message", "updated_at"])
        return

    try:
        extract_pdf(payload)
    except IntegraError as exc:
        _settle_provider_usage(
            event=usage,
            provider_http_status=int(payload.get("status", 200)),
            provider_request_id=_value(payload, "idRequisicao", "requestId"),
            billable=True,
        )
        document.status = DctfWebDocument.Status.FAILED
        document.error_code = "invalid_document"
        document.error_message = str(exc)[:240]
        document.provider_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        document.completed_at = timezone.now()
        document.save()
        return

    request_id = _value(payload, "idRequisicao", "requestId")[:160]
    _settle_provider_usage(
        event=usage,
        provider_http_status=int(payload.get("status", 200)),
        provider_request_id=request_id,
        billable=True,
    )
    document.status = DctfWebDocument.Status.AVAILABLE
    document.provider_request_id = request_id
    document.provider_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    document.completed_at = timezone.now()
    document.save(
        update_fields=[
            "status",
            "provider_request_id",
            "provider_payload",
            "completed_at",
            "updated_at",
        ]
    )


@shared_task(name="hub.dispatch_parcelamento_operation")  # type: ignore[untyped-decorator]
def dispatch_parcelamento_operation(operation_id: str) -> None:
    """Execute one approved PARCSN request without unsafe automatic replay."""

    with transaction.atomic():
        operation = (
            ParcelamentoOperation.objects.select_for_update()
            .select_related("company", "token_usage_event", "organization")
            .filter(id=operation_id)
            .first()
        )
        if operation is None or operation.status != ParcelamentoOperation.Status.QUEUED:
            return
        operation.status = ParcelamentoOperation.Status.FETCHING
        operation.save(update_fields=["status", "updated_at"])

    if operation.organization.is_demo:
        operation.status = ParcelamentoOperation.Status.EMPTY
        operation.provider_request_id = f"DEMO-{str(operation.id)[:12]}"
        operation.provider_payload = json.dumps({"simulated": True}, ensure_ascii=False)
        operation.completed_at = timezone.now()
        operation.save()
        return

    usage = operation.token_usage_event
    if usage is None:
        operation.status = ParcelamentoOperation.Status.FAILED
        operation.error_code = "usage_missing"
        operation.error_message = "A reserva de tokens não foi encontrada."
        operation.completed_at = timezone.now()
        operation.save()
        return

    if operation.kind == ParcelamentoOperation.Kind.DETAIL:
        dados: dict[str, Any] = {"numeroParcelamento": operation.agreement_number}
    elif operation.kind == ParcelamentoOperation.Kind.DAS:
        dados = {"parcelaParaEmitir": int(operation.competence)}
    else:
        dados = {}
    try:
        payload = IntegraClient().call(
            operation.service_key,
            contribuinte=normalize_cnpj(operation.company.cnpj_masked),
            autor_pedido=author_cnpj_for(operation.organization),
            dados=dados,
        )
    except IntegraServiceError as exc:
        _settle_provider_usage(event=usage, provider_http_status=exc.status, billable=False)
        operation.status = ParcelamentoOperation.Status.FAILED
        operation.error_code = (exc.code or "service")[:80]
        operation.error_message = str(exc)[:240]
        operation.completed_at = timezone.now()
        operation.save()
        return
    except ValidationError as exc:
        _settle_provider_usage(event=usage, provider_http_status=400, billable=False)
        operation.status = ParcelamentoOperation.Status.FAILED
        operation.error_code = "invalid_request"
        operation.error_message = str(exc)[:240]
        operation.completed_at = timezone.now()
        operation.save()
        return
    except IntegraError as exc:
        operation.status = ParcelamentoOperation.Status.UNKNOWN
        operation.error_code = "uncertain_result"
        operation.error_message = str(exc)[:240]
        operation.save(update_fields=["status", "error_code", "error_message", "updated_at"])
        return

    try:
        if operation.kind == ParcelamentoOperation.Kind.ORDERS:
            parsed = pedidos(payload)
            empty = not parsed
        elif operation.kind == ParcelamentoOperation.Kind.DETAIL:
            detalhe(payload, numero_esperado=int(operation.agreement_number or 0))
            empty = False
        elif operation.kind == ParcelamentoOperation.Kind.INSTALLMENTS:
            parsed = parcelas_disponiveis(payload)
            empty = not parsed
        else:
            pdf_das(payload)
            empty = False
    except ParcelamentoPayloadError as exc:
        request_id = _value(payload, "idRequisicao", "requestId")[:160]
        _settle_provider_usage(
            event=usage,
            provider_http_status=int(payload.get("status", 200)),
            provider_request_id=request_id,
            billable=True,
        )
        operation.status = ParcelamentoOperation.Status.FAILED
        operation.error_code = "invalid_provider_payload"
        operation.error_message = str(exc)[:240]
        operation.provider_request_id = request_id
        operation.provider_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        operation.completed_at = timezone.now()
        operation.save()
        return

    request_id = _value(payload, "idRequisicao", "requestId")[:160]
    _settle_provider_usage(
        event=usage,
        provider_http_status=int(payload.get("status", 200)),
        provider_request_id=request_id,
        billable=True,
    )
    operation.status = (
        ParcelamentoOperation.Status.EMPTY if empty else ParcelamentoOperation.Status.AVAILABLE
    )
    operation.provider_request_id = request_id
    operation.provider_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    operation.completed_at = timezone.now()
    operation.save()


@shared_task(name="hub.dispatch_fiscal_guide")  # type: ignore[untyped-decorator]
def dispatch_fiscal_guide(guide_id: str) -> None:
    """Issue one ready Domínio obligation with central Serpro credentials."""

    from apps.platform.models import TokenUsageEvent, UsageEvent

    with transaction.atomic():
        guide = (
            FiscalGuide.objects.select_for_update()
            .select_related("company")
            .filter(id=guide_id)
            .first()
        )
        if guide is None or guide.status != FiscalGuide.Status.QUEUED:
            return
        if guide.organization.is_demo:
            usage = TokenUsageEvent.objects.filter(
                idempotency_key=f"fiscal-guide:{guide.id}:{guide.issue_attempt}"
            ).first()
            if usage is None:
                usage = UsageEvent.objects.filter(
                    idempotency_key=f"fiscal-guide:{guide.id}:{guide.issue_attempt}"
                ).first()
            if usage is not None:
                _settle_provider_usage(event=usage, provider_http_status=200, billable=False)
            guide.status = FiscalGuide.Status.ISSUED
            guide.provider_request_id = f"DEMO-{str(guide.id)[:12]}"
            guide.provider_payload = json.dumps(
                {"simulated": True, "source": "CICA demonstração fictícia"},
                ensure_ascii=False,
            )
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
            return
        guide.status = FiscalGuide.Status.ISSUING
        guide.save(update_fields=["status", "updated_at"])
    usage = TokenUsageEvent.objects.filter(
        idempotency_key=f"fiscal-guide:{guide.id}:{guide.issue_attempt}"
    ).first()
    if usage is None:
        usage = UsageEvent.objects.filter(
            idempotency_key=f"fiscal-guide:{guide.id}:{guide.issue_attempt}"
        ).first()
    if usage is None:
        guide.status = FiscalGuide.Status.FAILED
        guide.error_code = "usage_missing"
        guide.error_message = "A reserva de consumo não foi encontrada."
        guide.save(update_fields=["status", "error_code", "error_message", "updated_at"])
        return
    try:
        cnpj = normalize_cnpj(guide.company.cnpj_masked)
    except ValidationError:
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
            autor_pedido=author_cnpj_for(guide.organization),
            dados=monthly_request_data(guide.competence),
        )
        extract_pdf(payload)
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
    _settle_provider_usage(
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
