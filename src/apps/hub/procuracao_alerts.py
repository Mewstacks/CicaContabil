"""Alarmes da coleta por procuração (E5): e-CNPJ a vencer, procuração que deixou de valer e fila
parada. Avisos dentro do produto, para dono e administrador (D-277: nunca e-mail, nunca cliente).

Reaproveita `notify` e os tipos `certificate_expiring` e `source_failed` que já existem: nenhum
tipo novo, nenhuma migração. Cada aviso tem chave de deduplicação: rodar de novo não repete.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.hub.models import NfseSync, Notification, OfficeCertificate, OfficeProfile
from apps.hub.nfse_procuracao import eligible_procuracao_syncs
from apps.hub.notifications import notify
from apps.organizations.models import Membership, Organization

logger = logging.getLogger(__name__)

EXPIRY_THRESHOLDS = (30, 15, 7, 3, 1)
LOST_WINDOW = timedelta(days=2)
STALLED_AFTER = timedelta(hours=6)
EXPIRED_WINDOW = timedelta(days=30)


def _administrators(organization: Organization) -> list[Any]:
    return [
        membership.user
        for membership in Membership.objects.filter(
            organization=organization,
            role__in=[Membership.Role.OWNER, Membership.Role.ADMIN],
            is_active=True,
            user__is_active=True,
        ).select_related("user")
    ]


def _threshold(days_left: int) -> int | None:
    return next((limit for limit in sorted(EXPIRY_THRESHOLDS) if days_left <= limit), None)


def notify_office_certificate_expiring(*, today: date | None = None) -> int:
    """The e-CNPJ stops collecting for the whole office the day it expires.

    One notice per certificate and threshold (30, 15, 7, 3 and 1 days), so it escalates without
    repeating every morning.
    """

    today = today or timezone.localdate()
    created = 0
    certificates = OfficeCertificate.objects.filter(
        revoked_at__isnull=True,
        valid_until__date__gte=today,
        valid_until__date__lte=today + timedelta(days=max(EXPIRY_THRESHOLDS)),
        organization__is_active=True,
        organization__is_demo=False,
        organization__hub_profile__nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
    ).select_related("organization")
    for certificate in certificates:
        assert certificate.valid_until is not None
        # `today` e o filtro `valid_until__date` usam o fuso do projeto; `.date()` de um datetime
        # em UTC dava o dia seguinte entre 21h e 24h em Brasília.
        threshold = _threshold((timezone.localtime(certificate.valid_until).date() - today).days)
        if threshold is None:
            continue
        for person in _administrators(certificate.organization):
            notice = notify(
                organization=certificate.organization,
                recipient=person,
                kind=Notification.Kind.CERTIFICATE_EXPIRING,
                title=f"e-CNPJ do escritório vence em {certificate.valid_until:%d/%m/%Y}",
                dedupe_key=f"office-cert:{certificate.pk}:{threshold}",
            )
            created += int(notice is not None)
    return created


def notify_office_certificate_expired(*, now: datetime | None = None) -> int:
    """The e-CNPJ already expired: collection stopped for the whole office and nothing said so.

    The "about to expire" notices stop on the day of the expiry. Announces once per certificate,
    for 30 days after the expiry, and only while the office has no newer valid e-CNPJ.
    """

    now = now or timezone.now()
    created = 0
    expired = OfficeCertificate.objects.filter(
        revoked_at__isnull=True,
        valid_until__lt=now,
        valid_until__gte=now - EXPIRED_WINDOW,
        organization__is_active=True,
        organization__is_demo=False,
        organization__hub_profile__nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
    ).select_related("organization")
    for certificate in expired:
        assert certificate.valid_until is not None
        if OfficeCertificate.objects.filter(
            organization_id=certificate.organization_id,
            revoked_at__isnull=True,
            valid_until__gt=now,
        ).exists():
            continue
        for person in _administrators(certificate.organization):
            notice = notify(
                organization=certificate.organization,
                recipient=person,
                kind=Notification.Kind.CERTIFICATE_EXPIRING,
                title=(
                    "e-CNPJ do escritório venceu em "
                    f"{timezone.localtime(certificate.valid_until):%d/%m/%Y}: "
                    "a coleta de NFS-e está parada"
                ),
                dedupe_key=f"office-cert-expired:{certificate.pk}",
            )
            created += int(notice is not None)
    return created


def notify_lost_procuracoes(*, now: datetime | None = None) -> int:
    """A company that had a valid procuração and now answers E2245 stopped being collected."""

    now = now or timezone.now()
    created = 0
    lost = NfseSync.objects.filter(
        credential_mode=NfseSync.CredentialMode.PROCURACAO,
        procuracao_status=NfseSync.ProcuracaoStatus.MISSING,
        procuracao_ok_at__isnull=False,
        procuracao_checked_at__gte=now - LOST_WINDOW,
        company__active=True,
        organization__is_active=True,
        organization__is_demo=False,
    ).select_related("company", "organization")
    for sync in lost:
        assert sync.procuracao_ok_at is not None
        for person in _administrators(sync.organization):
            notice = notify(
                organization=sync.organization,
                recipient=person,
                kind=Notification.Kind.SOURCE_FAILED,
                title=f"{sync.company.name} · procuração deixou de valer",
                dedupe_key=f"procuracao-lost:{sync.company_id}:{sync.procuracao_ok_at:%Y%m%d%H%M}",
                company=sync.company,
            )
            created += int(notice is not None)
    return created


def lane_health(*, now: datetime | None = None) -> dict[str, Any]:
    """How far behind the collection is. A lane that is off is healthy by definition."""

    from apps.hub.tasks_procuracao import lane_enabled, lane_paused

    now = now or timezone.now()
    if not lane_enabled():
        return {"enabled": False, "stalled": False, "overdue": 0, "oldest_minutes": 0}
    overdue = eligible_procuracao_syncs(now=now).filter(
        status__in=[NfseSync.Status.IDLE, NfseSync.Status.RETRY],
        next_run_at__lt=now - STALLED_AFTER,
    )
    count = overdue.count()
    oldest = overdue.order_by("next_run_at").values_list("next_run_at", flat=True).first()
    minutes = int((now - oldest).total_seconds() // 60) if oldest is not None else 0
    # Rows an expired or revoked e-CNPJ keeps out of the line: they are not "eligible", so the
    # count above never sees them and the lane looked healthy while collecting nothing.
    blocked = NfseSync.objects.filter(
        credential_mode=NfseSync.CredentialMode.PROCURACAO,
        enabled=True,
        organization__is_active=True,
        organization__is_demo=False,
        organization__hub_profile__nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
        company__active=True,
        office_certificate__isnull=False,
    ).filter(
        Q(office_certificate__revoked_at__isnull=False)
        | Q(office_certificate__valid_until__lte=now)
    )
    blocked_count = blocked.count()
    health = {
        "enabled": True,
        "paused": lane_paused(),
        "stalled": count > 0 or blocked_count > 0,
        "overdue": count,
        "blocked": blocked_count,
        "oldest_minutes": minutes,
    }
    if count:
        # Sentry picks a warning up once the monitoring is on (E4); until then it is in the log.
        logger.warning("procuracao.lane_stalled overdue=%s oldest_minutes=%s", count, minutes)
    if blocked_count:
        logger.warning("procuracao.lane_blocked_by_certificate rows=%s", blocked_count)
    return health
