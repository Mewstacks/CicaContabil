from __future__ import annotations

import hashlib
import zipfile
from datetime import UTC, datetime
from io import BytesIO

import pytest
from defusedxml import ElementTree
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ClientCompany, IntegrationArtifact, NfseDocument
from apps.hub.services import create_nfse_export, nfse_company_archive_folder
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


def test_nfse_export_freezes_classified_xml_and_manifest() -> None:
    organization = Organization.objects.create(name="Exportações", slug="nfse-exports")
    actor = User.objects.create_user("exports@example.test", "safe-password-123")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa XML", dominio_code="100"
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">'
        "<infNFSe><valores><vLiq>100.00</vLiq></valores></infNFSe>"
        "</NFSe>"
    )
    document = NfseDocument.objects.create(
        organization=organization,
        company=company,
        source_nsu="NFS-1",
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        original_xml=xml,
        # October in UTC, still September in the application's local timezone.
        issued_at=datetime(2026, 10, 1, 1, 30, tzinfo=UTC),
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
    assert export.adapter_version == "nfse-conference-acum-v3"
    assert export.snapshot["layout"] == "nfse-conference-acum-v3"
    assert export.snapshot["documents"] == [
        {
            "document_id": str(document.id),
            "document_hash": document.document_hash,
            "artifact_id": str(artifact.id),
            "accumulator_code": "AC-100",
            "path": (
                "NFS-e/Tipo-a-confirmar/100-/"
                f"{timezone.localtime(document.issued_at).strftime('%Y%m')}/NFS-e-NFS-1.xml"
            ),
        }
    ]
    content = export.content.read()
    assert export.content_hash == hashlib.sha256(content).hexdigest()
    with zipfile.ZipFile(BytesIO(content)) as bundle:
        exported_xml = bundle.read(export.snapshot["documents"][0]["path"]).decode()
        # Original bytes, declaration and default namespace survive; only acum is added.
        assert exported_xml == xml.replace(
            "<vLiq>100.00</vLiq></valores>", "<vLiq>100.00</vLiq><acum>AC-100</acum></valores>"
        )
        values = next(
            element
            for element in ElementTree.fromstring(exported_xml).iter()
            if element.tag.rsplit("}", 1)[-1] == "valores"
        )
        assert [child.tag.rsplit("}", 1)[-1] for child in values] == ["vLiq", "acum"]
        assert values[-1].text == "AC-100"
        assert "AC-100" in bundle.read("manifesto-classificacao.csv").decode("utf-8-sig")
    document.refresh_from_db()
    assert document.original_xml == xml


def test_nfse_company_archive_folder_uses_dominio_code_and_cannot_create_nested_paths() -> None:
    assert nfse_company_archive_folder(
        root="NFS-e",
        dominio_code="../10/01",
    ) == "NFS-e/10_01-"


def test_nfse_company_archive_folder_has_no_space_or_company_name_after_hyphen() -> None:
    assert nfse_company_archive_folder(root="Emitidas", dominio_code="0106") == "Emitidas/0106-"
    assert nfse_company_archive_folder(root="Tomadas", dominio_code=None) == "Tomadas/SEM-CODIGO-"


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


def test_nfse_export_rejects_xml_without_inf_nfse_instead_of_inventing_a_position() -> None:
    organization = Organization.objects.create(name="Sem infNFSe", slug="nfse-without-info")
    actor = User.objects.create_user("without-product@example.test", "safe-password-123")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    xml = "<nfse><numero>1</numero></nfse>"
    document = NfseDocument.objects.create(
        organization=organization,
        company=company,
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        original_xml=xml,
    )
    IntegrationArtifact.objects.create(
        organization=organization,
        document=document,
        accumulator_code="999",
        confidence=100,
    )

    with pytest.raises(ValueError, match="único grupo infNFSe"):
        create_nfse_export(organization=organization, documents=[document], actor=actor)


def test_nfse_export_uses_the_latest_immutable_accumulator_decision() -> None:
    organization = Organization.objects.create(name="Correções", slug="nfse-corrections")
    actor = User.objects.create_user("corrections@example.test", "safe-password-123")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa corrigida", dominio_code="101"
    )
    xml = "<NFSe><infNFSe><valores><vLiq>77</vLiq></valores></infNFSe></NFSe>"
    document = NfseDocument.objects.create(
        organization=organization,
        company=company,
        source_nsu="77",
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        original_xml=xml,
        issued_at=timezone.now(),
    )
    first = IntegrationArtifact.objects.create(
        organization=organization,
        document=document,
        accumulator_code="AC-ANTIGO",
        applied_rule="Decisão anterior",
        confidence=100,
    )
    latest = IntegrationArtifact.objects.create(
        organization=organization,
        document=document,
        accumulator_code="AC-CORRIGIDO",
        applied_rule="Correção humana",
        confidence=100,
        payload={"previous_artifact_id": str(first.id)},
    )

    export = create_nfse_export(organization=organization, documents=[document], actor=actor)

    snapshot = export.snapshot["documents"][0]
    assert snapshot["artifact_id"] == str(latest.id)
    assert snapshot["artifact_id"] != str(first.id)
    assert snapshot["accumulator_code"] == "AC-CORRIGIDO"
    with zipfile.ZipFile(BytesIO(export.content.read())) as bundle:
        exported_xml = bundle.read(snapshot["path"]).decode()
    assert "<acum>AC-CORRIGIDO</acum>" in exported_xml
    assert "AC-ANTIGO" not in exported_xml


def test_nfse_export_updates_only_inf_nfse_values_acum_and_removes_legacy_acu() -> None:
    organization = Organization.objects.create(name="acum correto", slug="nfse-acum-path")
    actor = User.objects.create_user("acu-anywhere@example.test", "safe-password-123")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    xml = (
        "<NFSe><infNFSe><valores><acum>ANTIGO</acum></valores></infNFSe>"
        "<grupo><ACU>LEGADO</ACU></grupo></NFSe>"
    )
    document = NfseDocument.objects.create(
        organization=organization,
        company=company,
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        original_xml=xml,
    )
    IntegrationArtifact.objects.create(
        organization=organization,
        document=document,
        accumulator_code="NOVO",
        confidence=100,
    )

    export = create_nfse_export(organization=organization, documents=[document], actor=actor)

    with zipfile.ZipFile(BytesIO(export.content.read())) as bundle:
        exported_xml = bundle.read(export.snapshot["documents"][0]["path"]).decode()
    acum_nodes = [
        element
        for element in ElementTree.fromstring(exported_xml).iter()
        if element.tag.rsplit("}", 1)[-1] == "acum"
    ]
    assert len(acum_nodes) == 1
    assert acum_nodes[0].text == "NOVO"
    assert "ACU" not in exported_xml
