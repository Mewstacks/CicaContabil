from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.test import Client, RequestFactory, override_settings

from apps.accounts.models import User
from apps.hub.models import ClientCompany
from apps.intelligence.models import EdgeAgent
from apps.organizations.models import Organization
from apps.triage.models import (
    AgentFileJob,
    DestinationProfile,
    DocumentType,
    Mailbox,
    TriageBlob,
    TriageItem,
    TriageSafetyScan,
)
from apps.triage.services import queue_windows_archive
from apps.triage.transitions import TriageStatus

pytestmark = pytest.mark.django_db


def _headers(agent: EdgeAgent, body: bytes) -> dict[str, str]:
    timestamp = str(int(time.time()))
    signature = hmac.new(
        agent.shared_secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return {
        "X-Hub-Agent-ID": str(agent.id),
        "X-Hub-Agent-Timestamp": timestamp,
        "X-Hub-Agent-Signature": signature,
    }


def _post(client: Client, agent: EdgeAgent, path: str, payload: dict[str, object]):
    body = json.dumps(payload, separators=(",", ":")).encode()
    return client.generic(
        "POST", path, body, content_type="application/json", headers=_headers(agent, body)
    )


def _ready_item(tmp_path):
    office = Organization.objects.create(name="Escritório", slug="windows-archive")
    actor = User.objects.create_user("archive@example.test", "test-only")
    mailbox = Mailbox.objects.create(
        organization=office,
        provider=Mailbox.Provider.IMAP,
        address="arquivo@example.test",
        status=Mailbox.Status.ACTIVE,
    )
    company = ClientCompany.objects.create(
        organization=office,
        name='Cliente CON: Comércio / Sul',
        dominio_code="0321",
    )
    document_type = DocumentType.objects.create(
        organization=office,
        code="documento",
        label="Documento",
        name_template="{codigo}_DOCUMENTO_{periodo}",
        period_kind=DocumentType.PeriodKind.COMPETENCIA,
    )
    content = b"%PDF-1.4\nverified attachment\n%%EOF"
    digest = hashlib.sha256(content).hexdigest()
    item = TriageItem.objects.create(
        organization=office,
        mailbox=mailbox,
        company=company,
        document_type=document_type,
        original_name="origem.pdf",
        final_name="0321_DOCUMENTO_082026.pdf",
        content_hash=digest,
        byte_size=len(content),
        status=TriageStatus.READY_TO_ARCHIVE,
    )
    blob = TriageBlob(organization=office, triage_item=item, content_type="application/pdf")
    blob.content.save("origem.pdf", ContentFile(content), save=True)
    TriageSafetyScan.objects.create(
        organization=office,
        triage_item=item,
        verdict=TriageSafetyScan.Verdict.CLEAN,
        format_verdict=TriageSafetyScan.FormatVerdict.VALID,
        content_hash=digest,
    )
    DestinationProfile.objects.create(
        organization=office,
        mode=DestinationProfile.Mode.WINDOWS,
        windows_root=r"D:\Clientes",
        folder_template="{company_name} [Domínio {dominio_code}]",
    )
    agent = EdgeAgent.objects.create(
        organization=office,
        label="Servidor",
        fingerprint="fingerprint",
        shared_secret="secret-for-tests",
    )
    return office, actor, agent, item, content


@override_settings(EDGE_AGENT_MTLS_REQUIRED=False)
def test_windows_job_is_scoped_downloaded_and_completed_only_after_hash_proof(tmp_path) -> None:
    with override_settings(MEDIA_ROOT=tmp_path):
        _office, actor, agent, item, content = _ready_item(tmp_path)
        job = queue_windows_archive(item=item, actor=actor)
        assert job.destination_path == (
            r"Cliente CON- Comércio - Sul [Domínio 0321]\0321_DOCUMENTO_082026.pdf"
        )
        item.refresh_from_db()
        assert item.status == TriageStatus.ARCHIVING
        request = RequestFactory().get("/triagem/arquivo/")
        request.user = actor
        pending_html = render_to_string(
            "hub/triage_item.html",
            {
                "office": _office,
                "item": item,
                "support_can_mutate": True,
                "triage_destination": DestinationProfile.objects.get(organization=_office),
                "triage_agent_job": job,
                "triage_agent_online": False,
                "demo_visitor": False,
            },
            request=request,
        )
        assert "Arquivo na fila do agente Windows" in pending_html
        assert "Inicie o serviço no computador do escritório" in pending_html

        client = Client()
        claim = _post(client, agent, "/api/agent/v2/files/next", {})
        claimed = claim.json()["job"]
        assert claim.status_code == 200
        assert claimed["id"] == str(job.id)
        assert claimed["relative_path"] == job.destination_path
        assert claimed["sha256"] == item.content_hash
        expected_root_hash = hashlib.sha256(br"d:\clientes").hexdigest()
        assert claimed["root_sha256"] == expected_root_hash

        download = _post(client, agent, f"/api/agent/v2/files/{job.id}/download", {})
        assert download.status_code == 200
        assert b"".join(download.streaming_content) == content

        wrong = _post(
            client,
            agent,
            f"/api/agent/v2/files/{job.id}/complete",
            {
                "success": True,
                "relative_path": job.destination_path,
                "sha256": "0" * 64,
                "byte_size": len(content),
            },
        )
        assert wrong.status_code == 409
        item.refresh_from_db()
        assert item.status == TriageStatus.ARCHIVING

        completed = _post(
            client,
            agent,
            f"/api/agent/v2/files/{job.id}/complete",
            {
                "success": True,
                "relative_path": job.destination_path,
                "sha256": item.content_hash,
                "byte_size": len(content),
                "detail": "ok",
            },
        )
        assert completed.json() == {"status": "completed"}
        item.refresh_from_db()
        job.refresh_from_db()
        assert item.status == TriageStatus.ARCHIVED
        assert item.destination_kind == DestinationProfile.Mode.WINDOWS
        assert item.destination_path == rf"D:\Clientes\{job.destination_path}"
        assert item.destination_hash == item.content_hash
        assert job.status == AgentFileJob.Status.DONE
        completed_html = render_to_string(
            "hub/triage_item.html",
            {
                "office": _office,
                "item": item,
                "support_can_mutate": True,
                "triage_destination": DestinationProfile.objects.get(organization=_office),
                "triage_agent_job": job,
                "triage_agent_online": True,
                "demo_visitor": False,
            },
            request=request,
        )
        assert "Arquivo confirmado na pasta Windows" in completed_html
        assert item.destination_path in completed_html


@override_settings(EDGE_AGENT_MTLS_REQUIRED=False)
def test_windows_job_rejects_other_office_and_can_retry_a_reported_failure(tmp_path) -> None:
    with override_settings(MEDIA_ROOT=tmp_path):
        _office, actor, agent, item, _content = _ready_item(tmp_path)
        job = queue_windows_archive(item=item, actor=actor)
        other = Organization.objects.create(name="Outro", slug="other-windows-agent")
        intruder = EdgeAgent.objects.create(
            organization=other,
            label="Outro servidor",
            fingerprint="other",
            shared_secret="other-secret",
        )
        client = Client()
        assert (
            _post(client, intruder, f"/api/agent/v2/files/{job.id}/download", {}).status_code
            == 404
        )
        _post(client, agent, "/api/agent/v2/files/next", {})
        failed = _post(
            client,
            agent,
            f"/api/agent/v2/files/{job.id}/complete",
            {
                "success": False,
                "relative_path": job.destination_path,
                "sha256": "",
                "byte_size": -1,
                "detail": "Sem acesso à pasta",
            },
        )
        assert failed.json() == {"status": "failed"}
        item.refresh_from_db()
        assert item.status == TriageStatus.ARCHIVE_FAILED
        retry = queue_windows_archive(item=item, actor=actor)
        assert retry.id != job.id
        item.refresh_from_db()
        assert item.status == TriageStatus.ARCHIVING


def test_windows_job_requires_dominio_code_and_never_accepts_a_rooted_filename(tmp_path) -> None:
    with override_settings(MEDIA_ROOT=tmp_path):
        _office, actor, _agent, item, _content = _ready_item(tmp_path)
        item.company.dominio_code = ""
        item.company.save(update_fields=["dominio_code"])
        with pytest.raises(Exception, match="código Domínio"):
            queue_windows_archive(item=item, actor=actor)
        item.company.dominio_code = "0321"
        item.company.save(update_fields=["dominio_code"])
        item.final_name = r"..\fora.pdf"
        item.save(update_fields=["final_name"])
        with pytest.raises(Exception, match="nome final"):
            queue_windows_archive(item=item, actor=actor)
