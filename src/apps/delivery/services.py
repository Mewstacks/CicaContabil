"""Criar, enviar, reenviar e recuperar entregas ao cliente."""

from __future__ import annotations

import calendar
import hashlib
import uuid
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.audit.services import record_event
from apps.delivery.models import (
    MAX_ATTACHMENT_BYTES,
    Delivery,
    DeliveryAccount,
    DeliveryAttachment,
)
from apps.delivery.transports import (
    PermanentDeliveryError,
    TemporaryDeliveryError,
    Transport,
    build_message,
    transport_for,
)
from apps.hub.models import ClientCompany, ObligationDelivery
from apps.organizations.models import Organization

MAX_RECIPIENTS = 10
MAX_ATTEMPTS = 3
LEASE = timedelta(minutes=10)
BACKOFF = (timedelta(minutes=5), timedelta(minutes=30))


def parse_recipients(raw: str | Iterable[str]) -> list[str]:
    parts = raw.replace(";", ",").replace("\n", ",").split(",") if isinstance(raw, str) else raw
    seen: dict[str, str] = {}
    for part in parts:
        address = part.strip()
        if not address:
            continue
        try:
            validate_email(address)
        except ValidationError as exc:
            raise ValidationError(f"Endereço inválido: {address[:80]}") from exc
        seen.setdefault(address.casefold(), address)
    if not seen:
        raise ValidationError("Informe ao menos um destinatário.")
    if len(seen) > MAX_RECIPIENTS:
        raise ValidationError(f"No máximo {MAX_RECIPIENTS} destinatários.")
    return list(seen.values())


def release_date(company: ClientCompany, competence: date | None) -> date | None:
    """Dia a partir do qual o e-mail da competência pode sair; None = sem trava.

    Como no HubFedrizzi, o dia vale para o mês seguinte à competência (mês em que as guias
    vencem). Dia 31 vira o último dia do mês.
    """

    day = company.email_release_day
    if not day or competence is None:
        return None
    year, month = (
        (competence.year + 1, 1)
        if competence.month == 12
        else (competence.year, competence.month + 1)
    )
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _enqueue(delivery_id: Any) -> None:
    from apps.delivery.tasks import send_delivery_task

    transaction.on_commit(lambda: send_delivery_task.delay(str(delivery_id)))


def create_delivery(
    *,
    organization: Organization,
    company: ClientCompany,
    recipients: str | Iterable[str],
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes]],
    requested_by: Any = None,
    competence: date | None = None,
    obligation_delivery: ObligationDelivery | None = None,
    resend_of: Delivery | None = None,
) -> Delivery:
    if company.organization_id != organization.id:
        raise ValidationError("A empresa pertence a outro escritório.")
    addresses = parse_recipients(recipients)
    subject = subject.strip()
    if not subject or not body.strip():
        raise ValidationError("Assunto e mensagem são obrigatórios.")
    total = sum(len(content) for _, content in attachments)
    if total > MAX_ATTACHMENT_BYTES:
        raise ValidationError("Os anexos passam de 30 MB.")
    release_on = release_date(company, competence)
    held = release_on is not None and release_on > timezone.localdate()
    with transaction.atomic():
        delivery = Delivery.objects.create(
            organization=organization,
            company=company,
            obligation_delivery=obligation_delivery,
            competence=competence,
            recipients=addresses,
            subject=subject[:200],
            body=body,
            status=Delivery.Status.SCHEDULED if held else Delivery.Status.QUEUED,
            release_on=release_on if held else None,
            total_bytes=total,
            requested_by=requested_by if getattr(requested_by, "is_authenticated", False) else None,
            resend_of=resend_of,
        )
        for filename, content in attachments:
            item = DeliveryAttachment(
                organization=organization,
                delivery=delivery,
                id=uuid.uuid4(),
                filename=filename[:255],
                sha256=hashlib.sha256(content).hexdigest(),
                byte_size=len(content),
            )
            item.content.save("anexo", ContentFile(content), save=False)
            item.save()
        record_event(
            action="delivery.created",
            actor=requested_by,
            organization=organization,
            target=delivery,
            metadata={"status": delivery.status, "attachments": len(attachments)},
        )
        if not held:
            _enqueue(delivery.pk)
    return delivery


def resend(delivery: Delivery, *, requested_by: Any) -> Delivery:
    """Nova entrega com os mesmos anexos; a original fica no histórico como está."""

    if delivery.status not in {Delivery.Status.SENT, Delivery.Status.FAILED}:
        raise ValidationError("Só uma entrega enviada ou com falha pode ser reenviada.")
    files: list[tuple[str, bytes]] = []
    for item in delivery.attachments.all():
        with item.content.open("rb") as stream:
            files.append((item.filename, stream.read()))
    return create_delivery(
        organization=delivery.organization,
        company=delivery.company,
        recipients=delivery.recipients,
        subject=delivery.subject,
        body=delivery.body,
        attachments=files,
        requested_by=requested_by,
        competence=None,  # reenvio não volta a esperar o dia de liberação
        obligation_delivery=delivery.obligation_delivery,
        resend_of=delivery,
    )


def cancel(delivery: Delivery, *, actor: Any) -> None:
    updated = Delivery.objects.filter(
        pk=delivery.pk,
        status__in=[Delivery.Status.SCHEDULED, Delivery.Status.QUEUED, Delivery.Status.FAILED],
    ).update(status=Delivery.Status.CANCELLED, updated_at=timezone.now())
    if not updated:
        raise ValidationError("Esta entrega não pode mais ser cancelada.")
    record_event(
        action="delivery.cancelled",
        actor=actor,
        organization=delivery.organization,
        target=delivery,
    )


def _sync_obligation(delivery: Delivery, *, ok: bool, error: str = "") -> None:
    linked = delivery.obligation_delivery
    if linked is None:
        return
    linked.email_status = (
        ObligationDelivery.EmailStatus.SENT if ok else ObligationDelivery.EmailStatus.FAILED
    )
    linked.email_recipient = ", ".join(delivery.recipients)[:254]
    linked.email_error = "" if ok else error[:500]
    requester = delivery.requested_by
    linked.email_sent_by = (requester.get_full_name() if requester else "")[:120]
    fields = ["email_status", "email_recipient", "email_error", "email_sent_by", "updated_at"]
    if ok:
        linked.sent_to_client_at = delivery.sent_at
        fields.append("sent_to_client_at")
    linked.save(update_fields=fields)


def process_delivery(delivery_id: str, *, transport: Transport | None = None) -> str:
    """Envia uma entrega. O arrendamento torna a reentrega do Celery inofensiva."""

    now = timezone.now()
    token = uuid.uuid4()
    candidates = (
        Delivery.objects.filter(pk=delivery_id)
        .filter(status__in=[Delivery.Status.QUEUED, Delivery.Status.SENDING])
        .exclude(lease_until__gt=now)
        .exclude(next_attempt_at__gt=now)
    )
    if not candidates.update(
        status=Delivery.Status.SENDING,
        lease_token=token,
        lease_until=now + LEASE,
        attempts=F("attempts") + 1,
        updated_at=now,
    ):
        return "skipped"
    delivery = Delivery.objects.select_related(
        "organization", "company", "obligation_delivery", "requested_by"
    ).get(pk=delivery_id)
    try:
        account = DeliveryAccount.objects.filter(
            organization=delivery.organization, active=True
        ).first()
        if account is None:
            raise PermanentDeliveryError("Configure a conta de envio do escritório.")
        files: list[tuple[str, bytes]] = []
        for item in delivery.attachments.all():
            with item.content.open("rb") as stream:
                content = stream.read()
            if hashlib.sha256(content).hexdigest() != item.sha256:
                raise PermanentDeliveryError("Um anexo mudou depois de guardado.")
            files.append((item.filename, content))
        message = build_message(
            account=account,
            recipients=list(delivery.recipients),
            subject=delivery.subject,
            body=delivery.body,
            attachments=files,
        )
        (transport or transport_for(account)).send(message)
    except TemporaryDeliveryError as exc:
        return _fail(delivery, token, str(exc), retry=True)
    except PermanentDeliveryError as exc:
        return _fail(delivery, token, str(exc), retry=False)
    sent_at = timezone.now()
    updated = Delivery.objects.filter(pk=delivery.pk, lease_token=token).update(
        status=Delivery.Status.SENT,
        sent_at=sent_at,
        sender=account.sender_address,
        last_error="",
        lease_until=None,
        lease_token=None,
        next_attempt_at=None,
        updated_at=sent_at,
    )
    if updated:
        delivery.refresh_from_db()
        _sync_obligation(delivery, ok=True)
        record_event(
            action="delivery.sent",
            organization=delivery.organization,
            target=delivery,
            metadata={"recipients": len(delivery.recipients)},
        )
    return "sent"


def _fail(delivery: Delivery, token: uuid.UUID, error: str, *, retry: bool) -> str:
    delivery.refresh_from_db(fields=["attempts"])
    final = not retry or delivery.attempts >= MAX_ATTEMPTS
    now = timezone.now()
    values: dict[str, Any] = {
        "last_error": error[:500],
        "lease_until": None,
        "lease_token": None,
        "updated_at": now,
    }
    if final:
        values.update(status=Delivery.Status.FAILED, next_attempt_at=None)
    else:
        values.update(
            status=Delivery.Status.QUEUED, next_attempt_at=now + BACKOFF[delivery.attempts - 1]
        )
    if not Delivery.objects.filter(pk=delivery.pk, lease_token=token).update(**values):
        return "skipped"
    if final:
        delivery.refresh_from_db()
        _sync_obligation(delivery, ok=False, error=error)
        record_event(
            action="delivery.failed",
            organization=delivery.organization,
            target=delivery,
            success=False,
            metadata={"attempts": delivery.attempts},
        )
        return "failed"
    return "retry"


def dispatch_due(now: datetime | None = None) -> int:
    """Libera o que chegou ao dia de liberação e reenfileira o que ficou sem trabalhador."""

    from apps.delivery.tasks import send_delivery_task

    now = now or timezone.now()
    today = timezone.localdate(now)
    Delivery.objects.filter(status=Delivery.Status.SCHEDULED, release_on__lte=today).update(
        status=Delivery.Status.QUEUED, release_on=None, updated_at=now
    )
    due = list(
        Delivery.objects.filter(status__in=[Delivery.Status.QUEUED, Delivery.Status.SENDING])
        .exclude(lease_until__gt=now)
        .exclude(next_attempt_at__gt=now)
        .values_list("pk", flat=True)[:200]
    )
    for pk in due:
        send_delivery_task.delay(str(pk))
    return len(due)


def check_account(account: DeliveryAccount) -> str:
    """Confere credenciais sem enviar e-mail; devolve o erro seguro ou texto vazio."""

    from apps.delivery.transports import DeliveryError, GraphTransport, SmtpTransport

    checker: SmtpTransport | GraphTransport = (
        GraphTransport(account)
        if account.provider == DeliveryAccount.Provider.GRAPH
        else SmtpTransport(account)
    )
    try:
        checker.check()
        error = ""
    except DeliveryError as exc:
        error = str(exc)[:500]
    account.last_test_at = timezone.now()
    account.last_test_error = error
    account.save(update_fields=["last_test_at", "last_test_error", "updated_at"])
    return error
