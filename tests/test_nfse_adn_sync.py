from __future__ import annotations

import base64
import gzip
import json
from collections.abc import Iterator
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.hub.models import Certificate, ClientCompany, NfseDocument, NfseSync
from apps.hub.nfse_adn import AdnDocument, AdnPage, AdnPayloadError, decode_xml, parse_page
from apps.hub.nfse_sync import process_sync_pages
from apps.organizations.models import Organization


def _xml(number: int) -> str:
    return (
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">'
        f"<nNFSe>{number}</nNFSe><cTribNac>010101</cTribNac>"
        "<vServPrest>125.50</vServPrest><CNPJ>12345678000195</CNPJ></NFSe>"
    )


def test_parse_page_accepts_the_official_bounded_envelope() -> None:
    payload = {
        "StatusProcessamento": "DOCUMENTOS_LOCALIZADOS",
        "LoteDFe": [
            {
                "NSU": 11,
                "ChaveAcesso": "A" * 50,
                "TipoDocumento": "NFSE",
                "ArquivoXml": base64.b64encode(_xml(1).encode()).decode(),
            },
            {
                "NSU": 12,
                "TipoDocumento": "NFSE",
                "ArquivoXml": _xml(2),
            },
        ],
        "UltimoNSU": 12,
        "MaxNSU": 18,
    }

    page = parse_page(json.dumps(payload).encode(), requested_nsu=10)

    assert page.last_nsu == 12
    assert page.max_nsu == 18
    assert [document.nsu for document in page.documents] == [11, 12]


def test_parse_page_rejects_repeated_or_out_of_order_nsu() -> None:
    payload = {
        "LoteDFe": [
            {"NSU": 11, "ArquivoXml": _xml(1)},
            {"NSU": 11, "ArquivoXml": _xml(2)},
        ],
        "UltimoNSU": 11,
        "MaxNSU": 11,
    }

    with pytest.raises(AdnPayloadError, match="fora de ordem"):
        parse_page(json.dumps(payload).encode(), requested_nsu=10)


def test_decode_xml_accepts_gzip_base64_and_rejects_doctype() -> None:
    encoded = base64.b64encode(gzip.compress(_xml(1).encode())).decode()
    assert decode_xml(encoded) == _xml(1)
    with pytest.raises(AdnPayloadError, match="seguro"):
        decode_xml("<!DOCTYPE x><NFSe />")


class FakeClient:
    def __init__(self, pages: list[AdnPage]) -> None:
        self.pages: Iterator[AdnPage] = iter(pages)
        self.requests: list[tuple[int, str]] = []

    def fetch_page(self, *, last_nsu: int, cnpj: str) -> AdnPage:
        self.requests.append((last_nsu, cnpj))
        return next(self.pages)


@pytest.mark.django_db
def test_sync_commits_documents_before_advancing_the_company_checkpoint() -> None:
    office = Organization.objects.create(name="Office", slug="office-adn")
    company = ClientCompany.objects.create(
        organization=office,
        name="Company",
        cnpj_masked="12.345.678/0001-95",
    )
    sync = NfseSync.objects.create(
        organization=office,
        company=company,
        enabled=True,
        status=NfseSync.Status.RUNNING,
    )
    client = FakeClient(
        [
            AdnPage(
                status="DOCUMENTOS_LOCALIZADOS",
                documents=(AdnDocument(nsu=1, xml=_xml(1)),),
                last_nsu=1,
                max_nsu=1,
            )
        ]
    )

    result = process_sync_pages(sync=sync, client=client)  # type: ignore[arg-type]

    sync.refresh_from_db()
    assert result == {"state": "completed", "pages": 1, "documents_created": 1}
    assert sync.checkpoint_nsu == "1"
    assert sync.last_success_at is not None
    assert sync.next_run_at >= timezone.now() + timedelta(minutes=59)
    document = NfseDocument.objects.get(company=company)
    assert document.source_nsu == "1"
    assert document.normalized_data["service_code"] == "010101"


@pytest.mark.django_db
def test_sync_rolls_back_the_whole_page_when_one_xml_is_invalid() -> None:
    office = Organization.objects.create(name="Rollback", slug="rollback-adn")
    company = ClientCompany.objects.create(
        organization=office,
        name="Company",
        cnpj_masked="12.345.678/0001-95",
    )
    sync = NfseSync.objects.create(
        organization=office,
        company=company,
        enabled=True,
        status=NfseSync.Status.RUNNING,
    )
    client = FakeClient(
        [
            AdnPage(
                status="DOCUMENTOS_LOCALIZADOS",
                documents=(
                    AdnDocument(nsu=1, xml=_xml(1)),
                    AdnDocument(nsu=2, xml="<NFSe>"),
                ),
                last_nsu=2,
                max_nsu=2,
            )
        ]
    )

    with pytest.raises(AdnPayloadError, match="malformado"):
        process_sync_pages(sync=sync, client=client)  # type: ignore[arg-type]

    sync.refresh_from_db()
    assert sync.checkpoint_nsu == ""
    assert not NfseDocument.objects.filter(company=company).exists()


@pytest.mark.django_db
def test_same_xml_is_deduplicated_per_company_not_across_the_office() -> None:
    office = Organization.objects.create(name="Branches", slug="branches-adn")
    first = ClientCompany.objects.create(organization=office, name="First")
    second = ClientCompany.objects.create(organization=office, name="Second")

    from apps.hub.services import create_document_and_artifact

    first_document, _, _ = create_document_and_artifact(
        company=first, original_xml=_xml(1), normalized_data={}
    )
    second_document, _, _ = create_document_and_artifact(
        company=second, original_xml=_xml(1), normalized_data={}
    )

    assert first_document.id != second_document.id


@pytest.mark.django_db
@override_settings(NFSE_ADN_SYNC_ENABLED=True)
def test_dispatcher_queues_only_due_active_non_demo_syncs() -> None:
    office = Organization.objects.create(name="Dispatch", slug="dispatch-adn")
    company = ClientCompany.objects.create(organization=office, name="Company")
    certificate = Certificate.objects.create(
        organization=office,
        company=company,
        label="A1",
        pfx_blob="dummy",
        password="dummy",
        fingerprint_sha256="a" * 64,
        valid_until=timezone.now() + timedelta(days=30),
    )
    due = NfseSync.objects.create(
        organization=office,
        company=company,
        certificate=certificate,
        enabled=True,
        status=NfseSync.Status.IDLE,
        next_run_at=timezone.now() - timedelta(minutes=1),
    )
    from apps.hub.tasks import dispatch_active_nfse_syncs

    with patch("apps.hub.tasks.poll_nfse_sync.delay") as queued:
        assert dispatch_active_nfse_syncs() == 1
        queued.assert_called_once_with(str(due.id))


@pytest.mark.django_db
@override_settings(NFSE_ADN_SYNC_ENABLED=True, NFSE_ADN_ENVIRONMENT="trial")
def test_worker_releases_lease_after_a_completed_collection() -> None:
    office = Organization.objects.create(name="Worker", slug="worker-adn")
    company = ClientCompany.objects.create(organization=office, name="Company")
    certificate = Certificate.objects.create(
        organization=office,
        company=company,
        label="A1",
        pfx_blob="dummy",
        password="dummy",
        fingerprint_sha256="b" * 64,
        valid_until=timezone.now() + timedelta(days=30),
    )
    sync = NfseSync.objects.create(
        organization=office,
        company=company,
        certificate=certificate,
        enabled=True,
        status=NfseSync.Status.IDLE,
        next_run_at=timezone.now() - timedelta(minutes=1),
    )
    from apps.hub.tasks import poll_nfse_sync

    with (
        patch("apps.hub.tasks.certificate_ssl_context", return_value=object()),
        patch("apps.hub.tasks.AdnClient", return_value=object()),
        patch(
            "apps.hub.tasks.process_sync_pages",
            return_value={"state": "completed", "pages": 1, "documents_created": 0},
        ) as process,
    ):
        assert poll_nfse_sync(str(sync.id))["state"] == "completed"
    sync.refresh_from_db()
    assert sync.lease_token is None
    assert sync.lease_until is None
    process.assert_called_once()
