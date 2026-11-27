"""e-CNPJ do escritório em Configurações: estado, permissão, senha e isolamento."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import OfficeCertificate, OfficeProfile
from apps.organizations.models import Membership, Organization
from pki_support import make_pfx
from test_nfse_procuracao import OFFICE_CNPJ
from test_nfse_procuracao_views import PASSWORD, World, login, texts

SETTINGS = "hub:settings"


@pytest.fixture
def world(db: object) -> World:
    return World()


def page(client: Any) -> str:
    return client.get(reverse(SETTINGS)).content.decode()


def post(client: Any, **fields: Any) -> Any:
    return client.post(reverse(SETTINGS), fields, follow=True)


def pfx_file(name: str = "e.pfx", **kwargs: Any) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ, **kwargs))


@pytest.mark.django_db
def test_no_certificate_shows_the_empty_state_with_send(world: World) -> None:
    html = page(login(world.owner, world.office))

    assert 'id="ecnpj"' in html and "Sem certificado" in html and "Ausente" in html
    assert 'data-modal-open="ecnpj-upload"' in html and "ecnpj-revoke" not in html


@pytest.mark.django_db
def test_upload_then_state_valid_with_swap_and_revoke(world: World) -> None:
    client = login(world.owner, world.office)

    response = post(client, action="upload-certificate", pfx=pfx_file(), password=PASSWORD)

    assert any("e-CNPJ enviado" in text for text in texts(response))
    html = response.content.decode()
    assert "Válido" in html and "Trocar" in html and 'data-modal-open="ecnpj-revoke"' in html
    assert OfficeCertificate.objects.get().organization_id == world.office.pk


@pytest.mark.django_db
def test_expiring_expired_revoked_and_quarantine_are_drawn(world: World) -> None:
    client = login(world.owner, world.office)
    post(client, action="upload-certificate", pfx=pfx_file(), password=PASSWORD)
    certificate = OfficeCertificate.objects.get()

    OfficeCertificate.objects.filter(pk=certificate.pk).update(
        valid_until=timezone.now() + timedelta(days=5),
        quarantined_until=timezone.now() + timedelta(minutes=5),
    )
    html = page(client)
    assert "Vence em breve" in html and "Bloqueado por alguns minutos" in html

    OfficeCertificate.objects.filter(pk=certificate.pk).update(
        valid_until=timezone.now() - timedelta(days=1), quarantined_until=None
    )
    assert "Vencido" in page(client)

    OfficeCertificate.objects.filter(pk=certificate.pk).update(revoked_at=timezone.now())
    assert "Revogado" in page(client)


@pytest.mark.django_db
def test_wrong_password_and_invalid_file_store_nothing(world: World) -> None:
    client = login(world.owner, world.office)

    wrong = post(client, action="upload-certificate", pfx=pfx_file(), password="errada")
    junk = post(
        client,
        action="upload-certificate",
        pfx=SimpleUploadedFile("lixo.pfx", b"nao e pkcs12"),
        password=PASSWORD,
    )
    wrong_kind = post(
        client,
        action="upload-certificate",
        pfx=SimpleUploadedFile("nota.txt", b"x"),
        password=PASSWORD,
    )

    assert any("Não foi possível abrir" in text for text in texts(wrong))
    assert any("Não foi possível abrir" in text for text in texts(junk))
    assert any("Selecione o arquivo" in text for text in texts(wrong_kind))
    assert not OfficeCertificate.objects.exists()


@pytest.mark.django_db
def test_the_password_never_comes_back_or_gets_logged(
    world: World, caplog: pytest.LogCaptureFixture
) -> None:
    client = login(world.owner, world.office)
    caplog.set_level(logging.DEBUG)

    wrong = post(client, action="upload-certificate", pfx=pfx_file(), password="segredo-errado-77")
    ok = post(client, action="upload-certificate", pfx=pfx_file(), password=PASSWORD)

    for response in (wrong, ok):
        body = response.content.decode()
        assert "segredo-errado-77" not in body and PASSWORD not in body
        assert all(PASSWORD not in text for text in texts(response))
    assert "segredo-errado-77" not in caplog.text and PASSWORD not in caplog.text
    assert not any(PASSWORD in str(event.metadata) for event in AuditEvent.objects.all())


@pytest.mark.django_db
def test_only_owner_and_admin_manage_and_others_see_state_only(world: World) -> None:
    admin = world.member(Membership.Role.ADMIN, "admin@example.test")
    post(
        login(world.owner, world.office),
        action="upload-certificate",
        pfx=pfx_file(),
        password=PASSWORD,
    )

    for user in (world.operator, world.auditor):
        client = login(user, world.office)
        html = page(client)
        assert "Válido" in html and "ecnpj-upload" not in html and "ecnpj-revoke" not in html
        assert post(client, action="revoke-certificate").status_code == 403
        assert (
            post(client, action="upload-certificate", pfx=pfx_file(), password=PASSWORD).status_code
            == 403
        )
    assert OfficeCertificate.objects.get().revoked_at is None

    post(login(admin, world.office), action="revoke-certificate")
    assert OfficeCertificate.objects.get().revoked_at is not None


@pytest.mark.django_db
def test_revoke_audits_and_stops(world: World) -> None:
    client = login(world.owner, world.office)
    post(client, action="upload-certificate", pfx=pfx_file(), password=PASSWORD)

    response = post(client, action="revoke-certificate")

    assert any("revogado" in text for text in texts(response))
    assert AuditEvent.objects.filter(action="hub.office_certificate.revoked").count() == 1


@pytest.mark.django_db
def test_legacy_office_has_no_section_and_upload_is_refused(world: World) -> None:
    OfficeProfile.objects.filter(organization=world.office).update(
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.CERTIFICATE
    )
    client = login(world.owner, world.office)

    assert 'id="ecnpj"' not in page(client)
    response = post(client, action="upload-certificate", pfx=pfx_file(), password=PASSWORD)
    assert not OfficeCertificate.objects.exists()
    assert any("A1 de cada empresa" in text for text in texts(response))


@pytest.mark.django_db
def test_a_user_without_membership_gets_a_refusal_page_not_a_404(db: object) -> None:
    from django.test import Client

    stray = User.objects.create_user(email="solto@example.test", password="uma-senha-longa")
    client = Client()
    client.force_login(stray)

    for method in (client.get, client.post):
        assert method(reverse(SETTINGS)).status_code == 403


@pytest.mark.django_db
def test_procuracoes_shows_state_and_points_to_settings(world: World) -> None:
    client = login(world.owner, world.office)
    post(client, action="upload-certificate", pfx=pfx_file(), password=PASSWORD)

    html = client.get(reverse("hub:procuracoes")).content.decode()

    assert "e-CNPJ válido" in html
    assert reverse(SETTINGS) + "#ecnpj" in html
    assert 'type="file"' not in html and "office-certificate-dialog" not in html

    stale = client.post(reverse("hub:procuracoes"), {"action": "revoke-certificate"})
    assert stale.status_code == 302 and stale["Location"] == reverse(SETTINGS) + "#ecnpj"
    assert OfficeCertificate.objects.get().revoked_at is None


@pytest.mark.django_db
def test_another_office_never_sees_or_revokes_this_certificate(world: World) -> None:
    client = login(world.owner, world.office)
    post(client, action="upload-certificate", pfx=pfx_file(), password=PASSWORD)
    other = Organization.objects.create(name="Outro", slug="outro")
    OfficeProfile.objects.create(
        organization=other,
        cnpj="11222333000181",
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
    )
    boss = User.objects.create_user(email="outro@example.test", password="uma-senha-longa")
    Membership.objects.create(organization=other, user=boss, role=Membership.Role.OWNER)
    foreign = login(boss, other)

    assert "Sem certificado" in page(foreign)
    post(foreign, action="revoke-certificate")
    assert OfficeCertificate.objects.get(organization=world.office).revoked_at is None
