"""Coleta NFS-e por procuração (D-304/D-305): cliente ADN, certificado, fila e semeadura."""

from __future__ import annotations

import base64
import json
import ssl
import uuid
from datetime import timedelta
from functools import cache
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.hub.models import (
    ClientCompany,
    NfseDocument,
    NfseSync,
    OfficeCertificate,
    OfficeProfile,
)
from apps.hub.nfse_adn import (
    AdnAuthenticationError,
    AdnError,
    AdnPayloadError,
    AdnTransportError,
)
from apps.hub.nfse_procuracao import (
    AdnCertificateProblem,
    AdnCertificateQuarantine,
    AdnQueryRejected,
    AdnRateLimited,
    ProcuracaoAdnClient,
    ProcuracaoMissing,
    eligible_procuracao_syncs,
    office_ssl_context,
    run_procuracao_sync,
    seed_procuracao_syncs,
)
from apps.hub.tasks import _eligible_nfse_syncs
from apps.organizations.models import Organization
from apps.platform.models import TenantLifecycle
from pki_support import make_pfx


def cnpj_from(base12: str) -> str:
    """CNPJ (numérico ou alfanumérico) com os dígitos verificadores calculados."""

    value = base12
    for weights in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        remainder = sum((ord(c) - 48) * w for c, w in zip(value, weights, strict=True)) % 11
        value += str(0 if remainder < 2 else 11 - remainder)
    return value


OFFICE_CNPJ = cnpj_from("191312430001")
CLIENT_CNPJ = cnpj_from("112223330001")
OTHER_CLIENT_CNPJ = cnpj_from("457231740001")
ALNUM_CLIENT_CNPJ = cnpj_from("AB12CD34EF56")
PASSWORD = "s3nha-do-escritorio"


@cache
def office_pfx_b64() -> str:
    return base64.b64encode(make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ)).decode()


def xml(number: int) -> str:
    return (
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">'
        f"<nNFSe>{number}</nNFSe><cTribNac>010101</cTribNac>"
        "<vServPrest>125.50</vServPrest></NFSe>"
    )


def ok_body(*numbers: int, query: str = "Procuracao", max_nsu: int | None = None) -> dict[str, Any]:
    last = numbers[-1] if numbers else 0
    return {
        "StatusProcessamento": "DOCUMENTOS_LOCALIZADOS",
        "LoteDFe": [
            {
                "NSU": n,
                "ChaveAcesso": f"{n:050d}",
                "TipoDocumento": "NFSE",
                "ArquivoXml": xml(n),
            }
            for n in numbers
        ],
        "UltimoNSU": last,
        "MaxNSU": max_nsu if max_nsu is not None else last,
        "TipoConsulta": query,
    }


def error_body(*codes: str) -> dict[str, Any]:
    return {"Erros": [{"Codigo": code, "Descricao": f"descrição {code}"} for code in codes]}


class FakeTransport:
    def __init__(self, *responses: tuple[int, Any]) -> None:
        self.responses = list(responses)
        self.calls: list[str] = []
        self.headers: list[dict[str, str]] = []

    def __call__(
        self, url: str, *, headers: dict[str, str], context: ssl.SSLContext
    ) -> tuple[int, bytes]:
        self.calls.append(url)
        self.headers.append(headers)
        status, body = self.responses.pop(0)
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        return status, raw


def client_with(transport: FakeTransport, **extra: Any) -> ProcuracaoAdnClient:
    return ProcuracaoAdnClient(
        ssl_context=ssl.create_default_context(), transport=transport, min_interval=0, **extra
    )


# --- client ---------------------------------------------------------------------------


def test_request_targets_the_client_cnpj_with_the_production_adn() -> None:
    transport = FakeTransport((200, ok_body(5, query="Procuracao")))
    client = client_with(transport)

    page = client.fetch_page(
        last_nsu=4, cnpj=f"{CLIENT_CNPJ[:2]}.{CLIENT_CNPJ[2:5]}/{CLIENT_CNPJ[5:]}"
    )

    assert transport.calls == [
        f"https://adn.nfse.gov.br/contribuintes/DFe/4?lote=true&cnpjConsulta={CLIENT_CNPJ}"
    ]
    assert transport.headers[0] == {"Accept": "application/json", "User-Agent": "CICA-NFSe/1.0"}
    assert [d.nsu for d in page.documents] == [5]
    assert client.last_query_type == "Procuracao"


def test_alphanumeric_cnpj_is_sent_as_is() -> None:
    transport = FakeTransport((200, ok_body()))

    client_with(transport).fetch_page(last_nsu=0, cnpj=ALNUM_CLIENT_CNPJ)

    assert transport.calls[0].endswith(f"cnpjConsulta={ALNUM_CLIENT_CNPJ}")


def test_invalid_client_cnpj_never_reaches_the_adn() -> None:
    transport = FakeTransport()

    with pytest.raises(ValidationError):
        client_with(transport).fetch_page(last_nsu=0, cnpj="11.111.111/1111-11")

    assert transport.calls == []


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (400, error_body("E2245"), ProcuracaoMissing),
        (400, error_body("E2243"), AdnQueryRejected),
        (400, error_body("E2244"), AdnQueryRejected),
        (400, error_body("E2246"), AdnQueryRejected),
        (400, error_body("E2247"), AdnQueryRejected),
        (400, error_body("E2210"), AdnCertificateProblem),
        (400, error_body("E2211"), AdnCertificateProblem),
        (400, error_body("E2212"), AdnCertificateProblem),
        (400, error_body("E2213"), AdnCertificateProblem),
        (400, error_body("E2214"), AdnTransportError),
        (401, b"", AdnAuthenticationError),
        (403, b"", AdnAuthenticationError),
        (404, b"", AdnTransportError),
        (404, error_body("E2240"), AdnTransportError),
        (429, b"", AdnRateLimited),
        (495, b"", AdnCertificateQuarantine),
        (500, b"", AdnTransportError),
        (503, b"<html>", AdnTransportError),
        (400, error_body("E999"), AdnError),
        (400, b"", AdnError),
    ],
)
def test_adn_answers_map_to_distinct_outcomes(
    status: int, body: Any, expected: type[AdnError]
) -> None:
    client = client_with(FakeTransport((status, body)))

    with pytest.raises(expected) as raised:
        client.fetch_page(last_nsu=0, cnpj=CLIENT_CNPJ)

    assert type(raised.value) is expected


@pytest.mark.parametrize(
    ("error_type", "transient"),
    [
        (ProcuracaoMissing, False),
        (AdnCertificateProblem, False),
        (AdnQueryRejected, False),
        (AdnCertificateQuarantine, True),
        (AdnRateLimited, True),
    ],
)
def test_outcomes_declare_whether_they_are_transient(
    error_type: type[AdnError], transient: bool
) -> None:
    assert error_type.transient is transient


@pytest.mark.parametrize("code", ["E2220", "E2230"])
def test_no_documents_from_the_nsu_is_the_end_of_the_stream_not_an_error(code: str) -> None:
    client = client_with(FakeTransport((404, error_body(code))))

    page = client.fetch_page(last_nsu=9, cnpj=CLIENT_CNPJ)

    assert page.documents == ()
    assert (page.last_nsu, page.max_nsu) == (9, 9)


def test_calls_are_spaced_by_the_minimum_interval() -> None:
    now = [100.0]
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    transport = FakeTransport((200, ok_body()), (200, ok_body()), (200, ok_body()))
    client = ProcuracaoAdnClient(
        ssl_context=ssl.create_default_context(),
        transport=transport,
        min_interval=1.0,
        sleep=sleep,
        clock=lambda: now[0],
    )
    client.fetch_page(last_nsu=0, cnpj=CLIENT_CNPJ)
    now[0] += 0.25
    client.fetch_page(last_nsu=0, cnpj=CLIENT_CNPJ)
    now[0] += 3
    client.fetch_page(last_nsu=0, cnpj=CLIENT_CNPJ)

    assert slept == [pytest.approx(0.75)]


def test_an_oversized_answer_is_refused() -> None:
    client = client_with(FakeTransport((200, b"x" * 12_000_100)))

    with pytest.raises(AdnPayloadError, match="limite"):
        client.fetch_page(last_nsu=0, cnpj=CLIENT_CNPJ)


# --- certificate ----------------------------------------------------------------------


def make_office(
    slug: str = "escritorio-novo",
    *,
    mode: str = OfficeProfile.NfseCollectionMode.PROCURACAO,
    valid_days: int = 365,
    with_certificate: bool = True,
    cnpj: str = OFFICE_CNPJ,
) -> tuple[Organization, OfficeCertificate | None]:
    office = Organization.objects.create(name=slug, slug=slug)
    OfficeProfile.objects.create(organization=office, nfse_collection_mode=mode)
    certificate = None
    if with_certificate:
        now = timezone.now()
        certificate = OfficeCertificate.objects.create(
            organization=office,
            label="e-CNPJ do escritório",
            cnpj=cnpj,
            pfx_blob=office_pfx_b64(),
            password=PASSWORD,
            fingerprint_sha256=uuid.uuid4().hex * 2,
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=valid_days),
        )
    return office, certificate


def make_company(office: Organization, cnpj: str = CLIENT_CNPJ, **extra: Any) -> ClientCompany:
    return ClientCompany.objects.create(
        organization=office, name=f"Cliente {cnpj[:4]}", cnpj_masked=cnpj, **extra
    )


@pytest.mark.django_db
def test_office_context_accepts_a_current_certificate_of_the_office_root() -> None:
    _office, certificate = make_office()
    assert certificate is not None

    assert isinstance(office_ssl_context(certificate), ssl.SSLContext)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"revoked_at": timezone.now()}, "revogado"),
        ({"valid_until": timezone.now() - timedelta(days=1)}, "vencido"),
        ({"valid_from": timezone.now() + timedelta(days=1)}, "ainda não é válido"),
        ({"cnpj": OTHER_CLIENT_CNPJ}, "raiz"),
        ({"password": "senha-errada"}, "abrir"),
        ({"pfx_blob": "não é base64!"}, "abrir"),
    ],
)
def test_office_context_refuses_what_cannot_work(change: dict[str, Any], message: str) -> None:
    _office, certificate = make_office()
    assert certificate is not None
    for field, value in change.items():
        setattr(certificate, field, value)

    with pytest.raises(ValidationError, match=message):
        office_ssl_context(certificate)


# --- lane isolation -------------------------------------------------------------------


@pytest.mark.django_db
def test_the_two_lanes_never_select_each_others_rows() -> None:
    new_office, certificate = make_office("lane-novo")
    new_company = make_company(new_office)
    new_sync = NfseSync.objects.create(
        organization=new_office,
        company=new_company,
        credential_mode=NfseSync.CredentialMode.PROCURACAO,
        office_certificate=certificate,
        enabled=True,
        status=NfseSync.Status.IDLE,
        next_run_at=timezone.now() - timedelta(minutes=1),
    )
    legacy_office, _ = make_office(
        "lane-legado", mode=OfficeProfile.NfseCollectionMode.CERTIFICATE, with_certificate=False
    )
    legacy_company = make_company(legacy_office, OTHER_CLIENT_CNPJ)
    from apps.hub.models import Certificate

    legacy_certificate = Certificate.objects.create(
        organization=legacy_office,
        company=legacy_company,
        label="A1",
        pfx_blob="dummy",
        password="dummy",
        fingerprint_sha256="d" * 64,
        valid_until=timezone.now() + timedelta(days=30),
    )
    legacy_sync = NfseSync.objects.create(
        organization=legacy_office,
        company=legacy_company,
        certificate=legacy_certificate,
        enabled=True,
        status=NfseSync.Status.IDLE,
        next_run_at=timezone.now() - timedelta(minutes=1),
    )

    assert list(eligible_procuracao_syncs().values_list("pk", flat=True)) == [new_sync.pk]
    assert list(_eligible_nfse_syncs().values_list("pk", flat=True)) == [legacy_sync.pk]
    assert run_procuracao_sync(str(legacy_sync.pk))["state"] == "inactive_or_busy"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "case",
    ["demo", "inactive_org", "inactive_company", "revoked", "expired", "quarantined", "suspended",
     "archived", "legacy_mode", "disabled_row"],
)  # fmt: skip
def test_rows_that_must_not_collect_are_not_eligible(case: str) -> None:
    mode = (
        OfficeProfile.NfseCollectionMode.CERTIFICATE
        if case == "legacy_mode"
        else OfficeProfile.NfseCollectionMode.PROCURACAO
    )
    office, certificate = make_office(f"inel-{case}".replace("_", "-"), mode=mode)
    assert certificate is not None
    company = make_company(office)
    NfseSync.objects.create(
        organization=office,
        company=company,
        credential_mode=NfseSync.CredentialMode.PROCURACAO,
        office_certificate=certificate,
        enabled=case != "disabled_row",
        status=NfseSync.Status.IDLE,
    )
    now = timezone.now()
    if case == "demo":
        Organization.objects.filter(pk=office.pk).update(is_demo=True)
    if case == "inactive_org":
        Organization.objects.filter(pk=office.pk).update(is_active=False)
    if case == "inactive_company":
        ClientCompany.objects.filter(pk=company.pk).update(active=False)
    if case == "revoked":
        OfficeCertificate.objects.filter(pk=certificate.pk).update(revoked_at=now)
    if case == "expired":
        OfficeCertificate.objects.filter(pk=certificate.pk).update(valid_until=now)
    if case == "quarantined":
        OfficeCertificate.objects.filter(pk=certificate.pk).update(
            quarantined_until=now + timedelta(minutes=5)
        )
    if case in {"suspended", "archived"}:
        TenantLifecycle.objects.create(organization=office, state=case)

    assert not eligible_procuracao_syncs().exists()


# --- seeding --------------------------------------------------------------------------


@pytest.mark.django_db
def test_seeding_creates_one_row_per_valid_active_company_and_is_idempotent() -> None:
    office, certificate = make_office("semente")
    good = make_company(office)
    make_company(office, OTHER_CLIENT_CNPJ, active=False)
    ClientCompany.objects.create(organization=office, name="Sem CNPJ")
    ClientCompany.objects.create(
        organization=office, name="CNPJ ruim", cnpj_masked="11.111.111/1111-11"
    )

    first = seed_procuracao_syncs()
    second = seed_procuracao_syncs()

    assert first == {"created": 1, "skipped": 2, "relinked": 0}
    assert second == {"created": 0, "skipped": 2, "relinked": 0}
    sync = NfseSync.objects.get(organization=office)
    assert sync.company == good
    assert sync.credential_mode == NfseSync.CredentialMode.PROCURACAO
    assert sync.office_certificate == certificate
    assert sync.enabled and sync.status == NfseSync.Status.IDLE
    assert sync.procuracao_status == NfseSync.ProcuracaoStatus.UNKNOWN


@pytest.mark.django_db
def test_seeding_never_touches_legacy_demo_or_inactive_offices() -> None:
    legacy, _ = make_office(
        "semente-legado", mode=OfficeProfile.NfseCollectionMode.CERTIFICATE, with_certificate=False
    )
    make_company(legacy)
    demo, _ = make_office("semente-demo")
    Organization.objects.filter(pk=demo.pk).update(is_demo=True)
    make_company(demo)

    assert seed_procuracao_syncs() == {"created": 0, "skipped": 0, "relinked": 0}
    assert NfseSync.objects.count() == 0


@pytest.mark.django_db
def test_seeding_waits_for_the_certificate_and_relinks_when_it_is_replaced() -> None:
    office, _ = make_office("semente-sem-a1", with_certificate=False)
    make_company(office)

    seed_procuracao_syncs()
    sync = NfseSync.objects.get(organization=office)
    assert sync.office_certificate is None
    assert not eligible_procuracao_syncs().exists()

    now = timezone.now()
    renewed = OfficeCertificate.objects.create(
        organization=office,
        label="renovado",
        cnpj=OFFICE_CNPJ,
        pfx_blob=office_pfx_b64(),
        password=PASSWORD,
        fingerprint_sha256="r" * 64,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=300),
    )
    result = seed_procuracao_syncs(organization_id=office.pk)

    sync.refresh_from_db()
    assert result["relinked"] == 1
    assert sync.office_certificate == renewed
    assert eligible_procuracao_syncs().count() == 1


# --- one company of the lane ----------------------------------------------------------


def due_sync(slug: str = "execucao") -> tuple[NfseSync, OfficeCertificate]:
    office, certificate = make_office(slug)
    assert certificate is not None
    sync = NfseSync.objects.create(
        organization=office,
        company=make_company(office),
        credential_mode=NfseSync.CredentialMode.PROCURACAO,
        office_certificate=certificate,
        enabled=True,
        status=NfseSync.Status.QUEUED,
        next_run_at=timezone.now() - timedelta(minutes=1),
    )
    return sync, certificate


def run_with(sync: NfseSync, *responses: tuple[int, Any]) -> tuple[dict[str, Any], FakeTransport]:
    transport = FakeTransport(*responses)
    result = run_procuracao_sync(
        str(sync.pk), client_factory=lambda ctx: client_with(transport), max_pages=1
    )
    return result, transport


@pytest.mark.django_db
def test_a_granted_procuracao_collects_and_marks_the_company_up_to_date() -> None:
    sync, certificate = due_sync()

    result, transport = run_with(sync, (200, ok_body(1, 2, query="Procuracao")))

    sync.refresh_from_db()
    certificate.refresh_from_db()
    assert result["state"] == "completed"
    assert result["documents_created"] == 2
    assert sync.checkpoint_nsu == "2"
    assert sync.procuracao_status == NfseSync.ProcuracaoStatus.OK
    assert sync.procuracao_ok_at is not None and sync.procuracao_checked_at is not None
    assert sync.query_type == "Procuracao"
    assert sync.procuracao_notice == ""
    assert sync.status == NfseSync.Status.IDLE
    assert sync.next_run_at >= timezone.now() + timedelta(minutes=59)
    assert (sync.lease_token, certificate.lease_token) == (None, None)
    assert certificate.last_call_at is not None
    assert NfseDocument.objects.filter(company=sync.company).count() == 2
    assert transport.calls[0].endswith(f"DFe/0?lote=true&cnpjConsulta={CLIENT_CNPJ}")


@pytest.mark.django_db
def test_the_same_root_needs_no_procuracao_and_is_up_to_date() -> None:
    sync, _certificate = due_sync("mesma-raiz")

    result, _ = run_with(sync, (200, ok_body(query="CnpjBase")))

    sync.refresh_from_db()
    assert result["state"] == "completed"
    assert sync.procuracao_status == NfseSync.ProcuracaoStatus.OK
    assert sync.query_type == "CnpjBase"


@pytest.mark.django_db
def test_no_procuracao_is_a_waiting_state_not_an_error() -> None:
    sync, _ = due_sync("sem-procuracao")

    result, _ = run_with(sync, (400, error_body("E2245")))

    sync.refresh_from_db()
    assert result["state"] == "awaiting_procuracao"
    assert sync.procuracao_status == NfseSync.ProcuracaoStatus.MISSING
    assert sync.status == NfseSync.Status.IDLE
    assert sync.last_error_code == "" and sync.failure_count == 0
    assert "procuração" in sync.procuracao_notice
    assert timezone.now() + timedelta(hours=5, minutes=55) <= sync.next_run_at
    assert sync.next_run_at <= timezone.now() + timedelta(hours=6, minutes=1)
    assert sync.lease_token is None


@pytest.mark.django_db
def test_a_granted_procuracao_is_picked_up_on_the_next_probe() -> None:
    sync, _ = due_sync("depois-outorga")
    run_with(sync, (400, error_body("E2245")))
    NfseSync.objects.filter(pk=sync.pk).update(next_run_at=timezone.now() - timedelta(seconds=1))

    result, _ = run_with(sync, (200, ok_body(1, query="Procuracao")))

    sync.refresh_from_db()
    assert result["state"] == "completed"
    assert sync.procuracao_status == NfseSync.ProcuracaoStatus.OK
    assert sync.checkpoint_nsu == "1"


@pytest.mark.django_db
def test_a_495_quarantines_the_certificate_and_retries_later() -> None:
    sync, certificate = due_sync("quarentena")

    result, _ = run_with(sync, (495, b""))

    sync.refresh_from_db()
    certificate.refresh_from_db()
    assert result["state"] == "retry" and result["quarantined"] is True
    assert certificate.quarantined_until is not None
    assert certificate.quarantined_until >= timezone.now() + timedelta(minutes=14)
    assert sync.status == NfseSync.Status.RETRY
    assert sync.next_run_at >= timezone.now() + timedelta(minutes=14)
    assert not eligible_procuracao_syncs().exists()


@pytest.mark.django_db
def test_a_429_asks_the_lane_to_pause_and_retries_the_company() -> None:
    sync, _ = due_sync("limite")

    result, _ = run_with(sync, (429, b""))

    sync.refresh_from_db()
    assert result["state"] == "retry" and result["pause_seconds"] == 60
    assert sync.status == NfseSync.Status.RETRY and sync.failure_count == 1


@pytest.mark.django_db
def test_a_certificate_problem_blocks_the_office_with_an_actionable_error() -> None:
    sync, certificate = due_sync("cert-problema")

    result, _ = run_with(sync, (400, error_body("E2213")))

    sync.refresh_from_db()
    certificate.refresh_from_db()
    assert result["state"] == "error"
    assert sync.status == NfseSync.Status.ERROR
    assert sync.procuracao_status == NfseSync.ProcuracaoStatus.ERROR
    assert sync.last_error_code == "certificate_problem"
    assert certificate.quarantined_until is not None


@pytest.mark.django_db
def test_a_transient_failure_backs_off_without_changing_the_procuracao_state() -> None:
    sync, _ = due_sync("transitorio")

    result, _ = run_with(sync, (503, b""))

    sync.refresh_from_db()
    assert result["state"] == "retry"
    assert sync.status == NfseSync.Status.RETRY and sync.failure_count == 1
    assert sync.procuracao_status == NfseSync.ProcuracaoStatus.UNKNOWN
    assert sync.next_run_at >= timezone.now() + timedelta(minutes=14)


@pytest.mark.django_db
def test_a_stored_certificate_that_cannot_be_opened_never_calls_the_adn() -> None:
    sync, certificate = due_sync("ilegivel")
    OfficeCertificate.objects.filter(pk=certificate.pk).update(password="senha-errada")

    result, transport = run_with(sync)

    sync.refresh_from_db()
    assert result["state"] == "error"
    assert transport.calls == []
    assert sync.status == NfseSync.Status.ERROR
    assert sync.procuracao_status == NfseSync.ProcuracaoStatus.ERROR
    assert sync.lease_token is None


@pytest.mark.django_db
def test_one_call_in_flight_per_certificate() -> None:
    first, certificate = due_sync("um-por-certificado")
    second = NfseSync.objects.create(
        organization=first.organization,
        company=make_company(first.organization, OTHER_CLIENT_CNPJ),
        credential_mode=NfseSync.CredentialMode.PROCURACAO,
        office_certificate=certificate,
        enabled=True,
        status=NfseSync.Status.QUEUED,
        next_run_at=timezone.now() - timedelta(minutes=1),
    )
    OfficeCertificate.objects.filter(pk=certificate.pk).update(
        lease_token=uuid.uuid4(), lease_until=timezone.now() + timedelta(minutes=5)
    )

    result, transport = run_with(second)

    second.refresh_from_db()
    assert result["state"] == "certificate_busy"
    assert transport.calls == []
    assert second.status == NfseSync.Status.IDLE and second.lease_token is None


@pytest.mark.django_db
def test_a_lease_held_by_another_worker_blocks_the_row() -> None:
    sync, _ = due_sync("lease")
    NfseSync.objects.filter(pk=sync.pk).update(
        lease_token=uuid.uuid4(), lease_until=timezone.now() + timedelta(minutes=5)
    )

    result, transport = run_with(sync)

    assert result["state"] == "inactive_or_busy"
    assert transport.calls == []


def test_an_invalid_identifier_is_refused() -> None:
    assert run_procuracao_sync("não-é-uuid")["state"] == "invalid_id"


@pytest.mark.django_db
def test_a_company_without_notes_for_a_week_is_asked_once_a_day() -> None:
    sync, _ = due_sync("dormente")

    run_with(sync, (200, ok_body(query="Procuracao")))

    sync.refresh_from_db()
    assert timezone.now() + timedelta(hours=23) <= sync.next_run_at
    assert sync.next_run_at <= timezone.now() + timedelta(hours=24, minutes=1)


@pytest.mark.django_db
def test_a_company_with_recent_notes_is_asked_every_hour() -> None:
    sync, _ = due_sync("ativa")

    run_with(sync, (200, ok_body(1, query="Procuracao")))

    sync.refresh_from_db()
    assert timezone.now() + timedelta(minutes=59) <= sync.next_run_at
    assert sync.next_run_at <= timezone.now() + timedelta(minutes=61)
