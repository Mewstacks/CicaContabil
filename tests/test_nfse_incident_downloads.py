import hashlib
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ClientCompany, CompanyAccessGrant, NfseDocument
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db(databases=["default", "knowledge"])


def test_original_zip_includes_unclassified_exact_xml_and_respects_scope(client):
    office = Organization.objects.create(name="Download QA", slug="download-qa")
    user = User.objects.create_user("download-qa@example.test", "safe-password-123")
    member = Membership.objects.create(organization=office, user=user, role="owner")
    company = ClientCompany.objects.create(
        organization=office, name="Empresa QA", dominio_code="001"
    )
    xml = "<NFSe><infNFSe><valores><vLiq>123.45</vLiq></valores></infNFSe></NFSe>"
    doc = NfseDocument.objects.create(
        organization=office,
        company=company,
        original_xml=xml,
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        issued_at=timezone.make_aware(datetime(2026, 9, 15)),
        normalized_data={"direction": "taken"},
    )
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(office.pk)
    session.save()
    data = {"action": "download_original_xmls", "report_competence": "2026-09"}
    response = client.post("/app/nfse/", data)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    with ZipFile(BytesIO(response.content)) as archive:
        assert archive.namelist() == [f"Tomadas/001-/NFS-e-{doc.pk}.xml"]
        assert archive.read(archive.namelist()[0]) == xml.encode()
    assert not doc.integration_artifacts.exists()
    assert "no-store" in response["Cache-Control"]
    assert client.post("/app/nfse/", {**data, "report_competence": "2026-08"}).status_code == 302
    foreign = Organization.objects.create(name="Fora", slug="fora-download")
    other = ClientCompany.objects.create(organization=foreign, name="Outra")
    assert client.post(f"/app/nfse/?company={other.pk}", data).status_code == 404
    member.role = "auditor"
    member.save()
    # Auditors only see companies explicitly granted to them.
    CompanyAccessGrant.objects.create(
        organization=office, membership=member, company=company, modules=["nfse"]
    )
    assert client.post("/app/nfse/", data).status_code == 200
    assert client.post("/app/nfse/", {"action": "export_dominio_xml"}).status_code == 403
