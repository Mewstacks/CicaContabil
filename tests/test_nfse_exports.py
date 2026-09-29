from __future__ import annotations

import hashlib
import zipfile
from io import BytesIO

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ClientCompany, IntegrationArtifact, NfseDocument
from apps.hub.services import create_nfse_export
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


def test_nfse_export_freezes_classified_xml_and_manifest() -> None:
    organization = Organization.objects.create(name="Exportações", slug="nfse-exports")
    actor = User.objects.create_user("exports@example.test", "safe-password-123")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa XML", dominio_code="100"
    )
    xml = "<nfse><numero>1</numero></nfse>"
    document = NfseDocument.objects.create(
        organization=organization,
        company=company,
        source_nsu="NFS-1",
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        original_xml=xml,
        issued_at=timezone.now(),
    )
    artifact = IntegrationArtifact.objects.create(
        organization=organization,
        document=document,
        accumulator_code="AC-100",
        applied_rule="Decisão humana",
        confidence=100,
    )

    export = create_nfse_export(organization=organization, documents=[document], actor=actor)

    assert export.document_count == 1
    assert export.snapshot["documents"] == [
        {
            "document_id": str(document.id),
            "document_hash": document.document_hash,
            "artifact_id": str(artifact.id),
            "accumulator_code": "AC-100",
            "path": (
                "NFS-e/100 -/"
                f"{timezone.localtime(document.issued_at).strftime('%Y%m')}/NFS-e-NFS-1.xml"
            ),
        }
    ]
    content = export.content.read()
    assert export.content_hash == hashlib.sha256(content).hexdigest()
    with zipfile.ZipFile(BytesIO(content)) as bundle:
        assert bundle.read(export.snapshot["documents"][0]["path"]).decode() == xml
        assert "AC-100" in bundle.read("manifesto-classificacao.csv").decode("utf-8-sig")


def test_nfse_export_rejects_document_without_confirmed_accumulator() -> None:
    organization = Organization.objects.create(name="Bloqueio", slug="nfse-export-block")
    actor = User.objects.create_user("block@example.test", "safe-password-123")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    xml = "<nfse />"
    document = NfseDocument.objects.create(
        organization=organization,
        company=company,
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        original_xml=xml,
    )

    with pytest.raises(ValueError, match="acumulador confirmado"):
        create_nfse_export(organization=organization, documents=[document], actor=actor)
