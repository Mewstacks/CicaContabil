"""NFS-e collection by procuração (D-304, D-305).

New module. Nothing here edits the legacy A1-per-company path (`nfse_adn`, `nfse_sync`,
`tasks.poll_nfse_sync`): it reuses `AdnClient`'s transport, `parse_page` and
`process_sync_pages` exactly as they are, and only touches rows whose `credential_mode` is
`procuracao`, which the legacy dispatcher never selects (it requires a company certificate).

Source: Manual dos Contribuintes, Guia das APIs do ADN, v1.1 (03/11/2026), §1.1.1(a) and
§1.1.2. A query for another taxpayer (`cnpjConsulta` with a different CNPJ root) needs a
procuração granted by that taxpayer, in the Receita Federal service portal, to the owner of
the certificate that opens the connection; without it the ADN answers E2245.
"""

from __future__ import annotations

import base64
import json
import os
import ssl
import tempfile
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
    pkcs12,
)
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.common.cnpj import normalize_cnpj
from apps.hub.models import (
    ClientCompany,
    NfseDocument,
    NfseSync,
    OfficeCertificate,
    OfficeProfile,
)
from apps.hub.nfse_adn import (
    MAX_RESPONSE_BYTES,
    AdnAuthenticationError,
    AdnClient,
    AdnError,
    AdnPage,
    AdnPayloadError,
    AdnTransportError,
    parse_page,
)
from apps.hub.nfse_sync import process_sync_pages
from apps.hub.services import certificate_cnpjs
from apps.platform.models import TenantLifecycle

PAGES_PER_SLICE = 2
MIN_CALL_INTERVAL_SECONDS = 1.0
QUARANTINE_MINUTES = 15
CERTIFICATE_PROBLEM_QUARANTINE_MINUTES = 60
AWAITING_RECHECK_HOURS = 6
DORMANT_DAYS = 7
DORMANT_RECHECK_HOURS = 24
LEASE_SECONDS = 600
RATE_LIMIT_PAUSE_SECONDS = 60

NO_DOCUMENT_CODES = frozenset({"E2220", "E2230"})
CERTIFICATE_PROBLEM_CODES = frozenset({"E2210", "E2211", "E2212", "E2213"})
QUERY_REJECTED_CODES = frozenset({"E2243", "E2244", "E2246", "E2247"})
PROCURACAO_MISSING_CODE = "E2245"
CRL_UNAVAILABLE_CODE = "E2214"

PROCURACAO_NOTICE = (
    "Sem procuração do cliente para o CNPJ do escritório, serviço NFS-e. "
    "O cliente a cadastra no Portal de Serviços da Receita."
)


class ProcuracaoMissing(AdnError):
    code = "procuracao_missing"
    transient = False


class AdnCertificateProblem(AdnError):
    code = "certificate_problem"
    transient = False


class AdnCertificateQuarantine(AdnError):
    code = "certificate_quarantine"
    transient = True


class AdnRateLimited(AdnTransportError):
    code = "rate_limited"
    transient = True


class AdnQueryRejected(AdnError):
    code = "query_rejected"
    transient = False


def error_codes(raw: bytes) -> list[tuple[str, str]]:
    """`Erros` and `Alertas` of an ADN body, as (code, description) pairs."""

    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    found: list[tuple[str, str]] = []
    for key in ("Erros", "erros", "Alertas", "alertas"):
        items = payload.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            code = item.get("Codigo") or item.get("codigo") or ""
            description = item.get("Descricao") or item.get("descricao") or ""
            if code:
                found.append((str(code)[:20], str(description)[:300]))
    return found


def query_type(raw: bytes) -> str:
    """`TipoConsulta` of a 200 answer: InscricaoCertificado, CnpjBase or Procuracao."""

    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    value = payload.get("TipoConsulta") or payload.get("tipoConsulta") or ""
    return str(value)[:32]


class ProcuracaoAdnClient(AdnClient):
    """Contributor distribution client for the office certificate.

    Same request as the legacy client (`cnpjConsulta` of the client company) but it reads
    the error body, so a missing procuração, a certificate problem, a quarantine (495) and a
    throttle (429) each become their own outcome, and calls are spaced per certificate.
    """

    def __init__(
        self,
        *,
        ssl_context: ssl.SSLContext,
        transport: Any = None,
        min_interval: float = MIN_CALL_INTERVAL_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(environment="production", ssl_context=ssl_context, transport=transport)
        self.min_interval = min_interval
        self._sleep = sleep
        self._clock = clock
        self._last_call: float | None = None
        self.last_query_type = ""

    def _wait(self) -> None:
        if self._last_call is not None:
            remaining = self.min_interval - (self._clock() - self._last_call)
            if remaining > 0:
                self._sleep(remaining)

    def fetch_page(self, *, last_nsu: int, cnpj: str) -> AdnPage:
        if last_nsu < 0:
            raise ValueError("O NSU não pode ser negativo.")
        target = normalize_cnpj(cnpj)
        self._wait()
        url = (
            f"{self.base_url}/DFe/{last_nsu}?{urlencode({'lote': 'true', 'cnpjConsulta': target})}"
        )
        try:
            status, raw = self.transport(
                url,
                headers={"Accept": "application/json", "User-Agent": "CICA-NFSe/1.0"},
                context=self.ssl_context,
            )
        finally:
            self._last_call = self._clock()
        return self._interpret(status, raw, last_nsu)

    def _interpret(self, status: int, raw: bytes, last_nsu: int) -> AdnPage:
        if len(raw) > MAX_RESPONSE_BYTES:
            raise AdnPayloadError("O ADN devolveu um lote maior que o limite de segurança.")
        if status == 200:
            page = parse_page(raw, requested_nsu=last_nsu)
            self.last_query_type = query_type(raw) or self.last_query_type
            return page
        codes = {code for code, _description in error_codes(raw)}
        if status == 404 and codes & NO_DOCUMENT_CODES:
            return AdnPage(
                status="NENHUM_DOCUMENTO", documents=(), last_nsu=last_nsu, max_nsu=last_nsu
            )
        if status in {401, 403}:
            raise AdnAuthenticationError(
                "O ADN recusou o e-CNPJ do escritório. Confira titularidade e validade."
            )
        if status == 495:
            raise AdnCertificateQuarantine("O ADN bloqueou o e-CNPJ por alguns minutos (HTTP 495).")
        if status == 429:
            raise AdnRateLimited("O ADN limitou as consultas (HTTP 429).")
        if status == 404 or status >= 500 or CRL_UNAVAILABLE_CODE in codes:
            raise AdnTransportError(f"O ADN está temporariamente indisponível (HTTP {status}).")
        if PROCURACAO_MISSING_CODE in codes:
            raise ProcuracaoMissing(PROCURACAO_NOTICE)
        if codes & CERTIFICATE_PROBLEM_CODES:
            problem = sorted(codes & CERTIFICATE_PROBLEM_CODES)[0]
            raise AdnCertificateProblem(
                f"O ADN rejeitou o e-CNPJ do escritório ({problem}). Envie um certificado válido."
            )
        if codes & QUERY_REJECTED_CODES:
            rejected = sorted(codes & QUERY_REJECTED_CODES)[0]
            raise AdnQueryRejected(f"O ADN recusou a consulta desta empresa ({rejected}).")
        suffix = f", {sorted(codes)[0]}" if codes else ""
        raise AdnError(f"O ADN recusou a consulta (HTTP {status}{suffix}).")


def _tls_context(key: PrivateKeyTypes, certificate: x509.Certificate, chain: Any) -> ssl.SSLContext:
    passphrase = base64.urlsafe_b64encode(os.urandom(24))
    pem = key.private_bytes(
        Encoding.PEM,
        PrivateFormat.PKCS8,
        BestAvailableEncryption(passphrase),
    ) + certificate.public_bytes(Encoding.PEM)
    for issuer in chain or []:
        pem += issuer.public_bytes(Encoding.PEM)
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    handle, filename = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(pem)
        context.load_cert_chain(filename, password=passphrase)
    finally:
        os.unlink(filename)
    return context


def office_ssl_context(
    certificate: OfficeCertificate, *, now: datetime | None = None
) -> ssl.SSLContext:
    """TLS client context for the office's e-CNPJ. Refuses anything that could not work."""

    now = now or timezone.now()
    if certificate.revoked_at is not None:
        raise ValidationError("O e-CNPJ do escritório foi revogado.")
    if certificate.valid_from and certificate.valid_from > now:
        raise ValidationError("O e-CNPJ do escritório ainda não é válido.")
    if certificate.valid_until and certificate.valid_until <= now:
        raise ValidationError("O e-CNPJ do escritório está vencido.")
    try:
        blob = base64.b64decode(certificate.pfx_blob, validate=True)
        key, parsed, chain = pkcs12.load_key_and_certificates(
            blob, certificate.password.encode() or None
        )
    except (ValueError, TypeError) as exc:
        raise ValidationError("Não foi possível abrir o e-CNPJ armazenado.") from exc
    if key is None or parsed is None:
        raise ValidationError("O e-CNPJ armazenado não contém chave privada.")
    if certificate.cnpj[:8] not in {candidate[:8] for candidate in certificate_cnpjs(parsed)}:
        raise ValidationError("O CNPJ raiz do e-CNPJ não corresponde ao do escritório.")
    return _tls_context(key, parsed, chain)


def current_office_certificate(organization_id: Any, *, now: datetime | None = None) -> Any:
    now = now or timezone.now()
    return (
        OfficeCertificate.objects.filter(
            organization_id=organization_id,
            revoked_at__isnull=True,
            valid_until__gt=now,
        )
        .order_by("-valid_until", "-created_at")
        .first()
    )


def eligible_procuracao_syncs(*, now: datetime | None = None) -> QuerySet[NfseSync]:
    """Rows the procuração lane may work on. Never overlaps the legacy dispatcher."""

    now = now or timezone.now()
    return (
        NfseSync.objects.filter(
            credential_mode=NfseSync.CredentialMode.PROCURACAO,
            enabled=True,
            organization__is_active=True,
            organization__is_demo=False,
            organization__hub_profile__nfse_collection_mode=(
                OfficeProfile.NfseCollectionMode.PROCURACAO
            ),
            company__active=True,
            office_certificate__isnull=False,
            office_certificate__revoked_at__isnull=True,
            office_certificate__valid_until__gt=now,
        )
        .filter(
            Q(office_certificate__quarantined_until__isnull=True)
            | Q(office_certificate__quarantined_until__lte=now)
        )
        .exclude(
            organization__lifecycle__state__in=[
                TenantLifecycle.State.SUSPENDED,
                TenantLifecycle.State.ARCHIVED,
            ]
        )
    )


def seed_procuracao_syncs(*, organization_id: Any = None) -> dict[str, int]:
    """Make sure every active company of a procuração office has its sync row (idempotent).

    Offices in `certificate` mode are never touched.
    """

    now = timezone.now()
    profiles = OfficeProfile.objects.filter(
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
        organization__is_active=True,
        organization__is_demo=False,
    )
    if organization_id is not None:
        profiles = profiles.filter(organization_id=organization_id)
    created = skipped = relinked = 0
    for profile in profiles:
        certificate = current_office_certificate(profile.organization_id, now=now)
        known = set(
            NfseSync.objects.filter(organization_id=profile.organization_id).values_list(
                "company_id", flat=True
            )
        )
        fresh: list[NfseSync] = []
        for company in ClientCompany.objects.filter(
            organization_id=profile.organization_id, active=True
        ).exclude(pk__in=known):
            try:
                normalize_cnpj(company.cnpj_masked)
            except ValidationError:
                skipped += 1
                continue
            fresh.append(
                NfseSync(
                    organization_id=profile.organization_id,
                    company=company,
                    credential_mode=NfseSync.CredentialMode.PROCURACAO,
                    office_certificate=certificate,
                    enabled=True,
                    status=NfseSync.Status.IDLE,
                    next_run_at=now,
                )
            )
        # One INSERT per batch, not per company (a 500-company office was 500 queries per run).
        NfseSync.objects.bulk_create(fresh, batch_size=200, ignore_conflicts=True)
        created += len(fresh)
        if certificate is not None:
            relinked += (
                NfseSync.objects.filter(
                    organization_id=profile.organization_id,
                    credential_mode=NfseSync.CredentialMode.PROCURACAO,
                )
                .exclude(office_certificate=certificate)
                .update(office_certificate=certificate)
            )
    return {"created": created, "skipped": skipped, "relinked": relinked}


def rearm_errored_syncs(*, organization_id: Any) -> int:
    """A new e-CNPJ gives the rows that stopped on an error another chance.

    Rows waiting for a procuração, queued or running are left as they are; only a row the
    lane had given up on (`error`) goes back to the line.
    """

    return NfseSync.objects.filter(
        organization_id=organization_id,
        credential_mode=NfseSync.CredentialMode.PROCURACAO,
        status=NfseSync.Status.ERROR,
    ).update(
        status=NfseSync.Status.IDLE,
        next_run_at=timezone.now(),
        failure_count=0,
        last_error_code="",
        last_error_message="",
        last_error_at=None,
        procuracao_status=NfseSync.ProcuracaoStatus.UNKNOWN,
        lease_token=None,
        lease_until=None,
    )


def recover_stale_procuracao_syncs(*, now: datetime | None = None) -> int:
    """Put rows of this lane back in line after a worker died holding them."""

    now = now or timezone.now()
    lane = NfseSync.objects.filter(credential_mode=NfseSync.CredentialMode.PROCURACAO, enabled=True)
    running = lane.filter(status=NfseSync.Status.RUNNING).filter(
        Q(lease_until__isnull=True) | Q(lease_until__lt=now)
    )
    recovered = running.update(
        status=NfseSync.Status.RETRY,
        lease_token=None,
        lease_until=None,
        next_run_at=now,
        last_error_code="stale_lease",
        last_error_message="A coleta foi retomada automaticamente após uma interrupção.",
        last_error_at=now,
    )
    recovered += lane.filter(
        status=NfseSync.Status.QUEUED, updated_at__lt=now - timedelta(minutes=5)
    ).update(
        status=NfseSync.Status.RETRY,
        next_run_at=now,
        last_error_code="stale_queue",
        last_error_message="A empresa voltou para a fila após uma interrupção.",
        last_error_at=now,
        updated_at=now,
    )
    OfficeCertificate.objects.filter(lease_until__lt=now).update(lease_token=None, lease_until=None)
    return recovered


def next_due_sync_id(certificate_id: Any, *, now: datetime | None = None) -> Any:
    """The next company of this certificate that is due, or None while one is in flight."""

    now = now or timezone.now()
    lane = eligible_procuracao_syncs(now=now).filter(office_certificate_id=certificate_id)
    if lane.filter(status__in=[NfseSync.Status.QUEUED, NfseSync.Status.RUNNING]).exists():
        return None
    return (
        lane.filter(status__in=[NfseSync.Status.IDLE, NfseSync.Status.RETRY])
        .filter(Q(next_run_at__isnull=True) | Q(next_run_at__lte=now))
        .filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now))
        .order_by("next_run_at", "last_success_at", "pk")
        .values_list("pk", flat=True)
        .first()
    )


def due_certificate_ids(*, now: datetime | None = None) -> list[Any]:
    now = now or timezone.now()
    return list(
        eligible_procuracao_syncs(now=now)
        .filter(status__in=[NfseSync.Status.IDLE, NfseSync.Status.RETRY])
        .filter(Q(next_run_at__isnull=True) | Q(next_run_at__lte=now))
        .order_by("office_certificate_id")
        .values_list("office_certificate_id", flat=True)
        .distinct()
    )


def _mark_ok(sync: NfseSync, *, query: str) -> None:
    now = timezone.now()
    values: dict[str, Any] = {
        "procuracao_status": NfseSync.ProcuracaoStatus.OK,
        "procuracao_checked_at": now,
        "procuracao_notice": "",
    }
    if sync.procuracao_ok_at is None:
        values["procuracao_ok_at"] = now
    if query:
        values["query_type"] = query
    NfseSync.objects.filter(pk=sync.pk).update(**values)


def _mark_missing(sync: NfseSync) -> None:
    now = timezone.now()
    NfseSync.objects.filter(pk=sync.pk).update(
        status=NfseSync.Status.IDLE,
        procuracao_status=NfseSync.ProcuracaoStatus.MISSING,
        procuracao_checked_at=now,
        procuracao_notice=PROCURACAO_NOTICE,
        last_error_code="",
        last_error_message="",
        last_error_at=None,
        failure_count=0,
        next_run_at=now + timedelta(hours=AWAITING_RECHECK_HOURS),
    )


def _mark_failure(sync_id: Any, exc: Exception, *, quarantine: timedelta | None = None) -> str:
    transient = isinstance(exc, AdnError) and exc.transient
    current = NfseSync.objects.filter(pk=sync_id).first()
    failure_count = min((current.failure_count if current else 0) + 1, 15)
    delay_minutes = min(15 * (2 ** (failure_count - 1)), 360)
    now = timezone.now()
    values: dict[str, Any] = {
        "status": NfseSync.Status.RETRY if transient else NfseSync.Status.ERROR,
        # Django's ValidationError has `.code = None`, so a plain getattr default is not enough.
        "last_error_code": str(getattr(exc, "code", None) or "configuration")[:80],
        "last_error_message": str(exc)[:500],
        "last_error_at": now,
        "failure_count": failure_count,
        "next_run_at": (now + (quarantine or timedelta(minutes=delay_minutes)))
        if transient
        else None,
    }
    if not transient:
        values["procuracao_status"] = NfseSync.ProcuracaoStatus.ERROR
        values["procuracao_checked_at"] = now
    NfseSync.objects.filter(pk=sync_id).update(**values)
    return "retry" if transient else "error"


def _quarantine(certificate_id: Any, minutes: int) -> None:
    OfficeCertificate.objects.filter(pk=certificate_id).update(
        quarantined_until=timezone.now() + timedelta(minutes=minutes)
    )


def run_procuracao_sync(
    sync_id: str,
    *,
    client_factory: Callable[[ssl.SSLContext], ProcuracaoAdnClient] | None = None,
    max_pages: int = PAGES_PER_SLICE,
) -> dict[str, Any]:
    """Work one company of the lane. Returns what the task wrapper needs to chain."""

    try:
        parsed_id = uuid.UUID(sync_id)
    except (ValueError, AttributeError):
        return {"state": "invalid_id"}
    now = timezone.now()
    token = uuid.uuid4()
    lease_until = now + timedelta(seconds=LEASE_SECONDS)
    acquired = (
        eligible_procuracao_syncs(now=now)
        .filter(pk=parsed_id)
        .filter(status__in=[NfseSync.Status.IDLE, NfseSync.Status.RETRY, NfseSync.Status.QUEUED])
        .filter(Q(next_run_at__isnull=True) | Q(next_run_at__lte=now))
        .filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now))
        .update(
            lease_token=token,
            lease_until=lease_until,
            status=NfseSync.Status.RUNNING,
            last_run_at=now,
        )
    )
    if not acquired:
        return {"state": "inactive_or_busy"}
    sync = NfseSync.objects.select_related("company", "office_certificate").get(pk=parsed_id)
    certificate = sync.office_certificate
    certificate_id = certificate.pk if certificate is not None else None
    holder = (
        OfficeCertificate.objects.filter(pk=certificate_id)
        .filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now))
        .update(lease_token=token, lease_until=lease_until)
        if certificate_id is not None
        else 0
    )
    if not holder:
        NfseSync.objects.filter(pk=parsed_id, lease_token=token).update(
            status=NfseSync.Status.IDLE,
            lease_token=None,
            lease_until=None,
            next_run_at=now + timedelta(seconds=30),
        )
        return {"state": "certificate_busy", "certificate_id": certificate_id}
    result: dict[str, Any] = {"certificate_id": certificate_id}
    try:
        if certificate is None:
            raise ValidationError("A empresa ainda não tem o e-CNPJ do escritório vinculado.")
        context = office_ssl_context(certificate)
        client = (client_factory or (lambda ctx: ProcuracaoAdnClient(ssl_context=ctx)))(context)
        outcome = process_sync_pages(sync=sync, client=client, max_pages=max_pages)
        _mark_ok(sync, query=client.last_query_type)
        result.update(outcome)
        result["caught_up"] = NfseSync.objects.filter(
            pk=parsed_id, next_run_at__gt=timezone.now()
        ).exists()
        if (
            result["caught_up"]
            and not NfseDocument.objects.filter(
                company_id=sync.company_id,
                captured_at__gte=timezone.now() - timedelta(days=DORMANT_DAYS),
            ).exists()
        ):
            # A company with no notes for a week is asked once a day, not every hour.
            NfseSync.objects.filter(pk=parsed_id).update(
                next_run_at=timezone.now() + timedelta(hours=DORMANT_RECHECK_HOURS)
            )
    except ProcuracaoMissing:
        _mark_missing(sync)
        result.update(state="awaiting_procuracao")
    except AdnCertificateQuarantine as exc:
        _quarantine(certificate_id, QUARANTINE_MINUTES)
        result.update(
            state=_mark_failure(parsed_id, exc, quarantine=timedelta(minutes=QUARANTINE_MINUTES)),
            quarantined=True,
        )
    except AdnRateLimited as exc:
        result.update(state=_mark_failure(parsed_id, exc), pause_seconds=RATE_LIMIT_PAUSE_SECONDS)
    except (AdnCertificateProblem, AdnAuthenticationError) as exc:
        # A refused e-CNPJ (401/403) is refused for every company of the office: the chain must
        # stop instead of testing the whole portfolio with it, one company per second.
        _quarantine(certificate_id, CERTIFICATE_PROBLEM_QUARANTINE_MINUTES)
        result.update(state=_mark_failure(parsed_id, exc), quarantined=True)
    except (AdnError, ValidationError, ValueError) as exc:
        result.update(state=_mark_failure(parsed_id, exc))
    except Exception:
        NfseSync.objects.filter(pk=parsed_id).update(
            status=NfseSync.Status.ERROR,
            procuracao_status=NfseSync.ProcuracaoStatus.ERROR,
            last_error_code="unexpected",
            last_error_message="Falha inesperada na coleta por procuração. Solicite suporte.",
            last_error_at=timezone.now(),
            next_run_at=None,
        )
        result.update(state="error")
    finally:
        with transaction.atomic():
            NfseSync.objects.filter(pk=parsed_id, lease_token=token).update(
                lease_token=None, lease_until=None
            )
            if certificate_id is not None:
                OfficeCertificate.objects.filter(pk=certificate_id, lease_token=token).update(
                    lease_token=None, lease_until=None, last_call_at=timezone.now()
                )
    return result
