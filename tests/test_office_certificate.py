"""Envio, validação e revogação do e-CNPJ do escritório (D-305)."""

from __future__ import annotations

import base64
import hashlib
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import ClientCompany, NfseSync, OfficeCertificate, OfficeProfile
from apps.hub.nfse_procuracao import eligible_procuracao_syncs
from apps.hub.office_certificate import (
    OfficeCertificateError,
    revoke_office_certificate,
    store_office_certificate,
)
from apps.organizations.models import Organization
from pki_support import make_pfx
from test_nfse_procuracao import CLIENT_CNPJ, OFFICE_CNPJ, OTHER_CLIENT_CNPJ

PASSWORD = "senha-do-escritorio"


def office(
    slug: str = "envio",
    *,
    mode: str = OfficeProfile.NfseCollectionMode.PROCURACAO,
    cnpj: str | None = OFFICE_CNPJ,
) -> Organization:
    organization = Organization.objects.create(name="Escritório Envio", slug=slug)
    OfficeProfile.objects.create(
        organization=organization, cnpj=cnpj or "", nfse_collection_mode=mode
    )
    return organization


@pytest.mark.django_db
def test_a_valid_e_cnpj_is_kept_encrypted_and_audited_without_secrets() -> None:
    organization = office()
    actor = User.objects.create_user("dono@example.test", "uma-senha-longa")
    pfx = make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ)

    certificate = store_office_certificate(
        organization=organization, pfx_bytes=pfx, password=PASSWORD, actor=actor
    )

    assert certificate.cnpj == OFFICE_CNPJ
    assert certificate.valid_until > timezone.now() + timedelta(days=300)
    assert certificate.fingerprint_sha256 == hashlib.sha256(pfx).hexdigest()
    assert certificate.uploaded_by == actor
    with connection.cursor() as cursor:
        cursor.execute("SELECT pfx_blob, password FROM hub_officecertificate")
        raw_blob, raw_password = cursor.fetchone()
    assert raw_blob.startswith("enc:v1:") and raw_password.startswith("enc:v1:")
    assert base64.b64encode(pfx).decode()[:40] not in raw_blob
    assert PASSWORD not in raw_password
    event = AuditEvent.objects.get(action="hub.office_certificate.uploaded")
    assert PASSWORD not in str(event.metadata)
    assert event.metadata == {"fingerprint_prefix": certificate.fingerprint_sha256[:12]}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("legacy_mode", "A1 de cada empresa"),
        ("no_cnpj", "CNPJ do escritório antes"),
        ("wrong_password", "abrir o arquivo"),
        ("expired", "vencido"),
        ("not_yet_valid", "ainda não é válido"),
        ("other_root", "não é o do escritório"),
        ("no_cnpj_in_certificate", "não informa um CNPJ"),
    ],
)
def test_the_upload_refuses_what_cannot_work(case: str, message: str) -> None:
    organization = office(
        mode=(
            OfficeProfile.NfseCollectionMode.CERTIFICATE
            if case == "legacy_mode"
            else OfficeProfile.NfseCollectionMode.PROCURACAO
        ),
        cnpj=None if case == "no_cnpj" else OFFICE_CNPJ,
    )
    options: dict[str, object] = {"password": PASSWORD, "cnpj": OFFICE_CNPJ}
    if case == "expired":
        options.update(starts_in_days=-10, valid_days=-2)
    if case == "not_yet_valid":
        options["starts_in_days"] = 3
    if case == "other_root":
        options["cnpj"] = OTHER_CLIENT_CNPJ
    if case == "no_cnpj_in_certificate":
        options["include_cnpj"] = False
    pfx = make_pfx(**options)  # type: ignore[arg-type]

    with pytest.raises(OfficeCertificateError, match=message):
        store_office_certificate(
            organization=organization,
            pfx_bytes=pfx,
            password="outra-senha" if case == "wrong_password" else PASSWORD,
        )

    assert not OfficeCertificate.objects.exists()


@pytest.mark.django_db
def test_garbage_is_refused_with_the_same_safe_message() -> None:
    with pytest.raises(OfficeCertificateError, match="abrir o arquivo"):
        store_office_certificate(
            organization=office(), pfx_bytes="isto não é um pfx".encode(), password=PASSWORD
        )


@pytest.mark.django_db
def test_a_branch_certificate_of_the_same_root_is_accepted() -> None:
    from test_nfse_procuracao import cnpj_from

    branch = cnpj_from(OFFICE_CNPJ[:8] + "0002")
    organization = office()

    certificate = store_office_certificate(
        organization=organization,
        pfx_bytes=make_pfx(password=PASSWORD, cnpj=branch),
        password=PASSWORD,
    )

    assert certificate.cnpj == branch


@pytest.mark.django_db
def test_uploading_prepares_the_companies_and_never_touches_another_office() -> None:
    organization = office("com-clientes")
    ClientCompany.objects.create(organization=organization, name="Cliente", cnpj_masked=CLIENT_CNPJ)
    other = office("vizinho", cnpj=OTHER_CLIENT_CNPJ)
    ClientCompany.objects.create(organization=other, name="Do vizinho", cnpj_masked=CLIENT_CNPJ)

    certificate = store_office_certificate(
        organization=organization,
        pfx_bytes=make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ),
        password=PASSWORD,
    )

    sync = NfseSync.objects.get(organization=organization)
    assert sync.office_certificate == certificate
    assert sync.credential_mode == NfseSync.CredentialMode.PROCURACAO
    assert eligible_procuracao_syncs().count() == 1
    assert not NfseSync.objects.filter(organization=other).exists()


@pytest.mark.django_db
def test_the_same_file_twice_is_idempotent_and_a_revoked_one_comes_back() -> None:
    organization = office()
    pfx = make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ)
    first = store_office_certificate(organization=organization, pfx_bytes=pfx, password=PASSWORD)

    again = store_office_certificate(organization=organization, pfx_bytes=pfx, password=PASSWORD)
    assert again.pk == first.pk and OfficeCertificate.objects.count() == 1

    revoke_office_certificate(first)
    first.refresh_from_db()
    assert first.revoked_at is not None
    back = store_office_certificate(organization=organization, pfx_bytes=pfx, password=PASSWORD)
    assert back.pk == first.pk and back.revoked_at is None


@pytest.mark.django_db
def test_a_renewed_certificate_takes_over_every_company() -> None:
    organization = office()
    for cnpj in (CLIENT_CNPJ, OTHER_CLIENT_CNPJ):
        ClientCompany.objects.create(organization=organization, name=cnpj, cnpj_masked=cnpj)
    old = store_office_certificate(
        organization=organization,
        pfx_bytes=make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ, valid_days=30),
        password=PASSWORD,
    )
    new = store_office_certificate(
        organization=organization,
        pfx_bytes=make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ, valid_days=400),
        password=PASSWORD,
    )

    assert old.pk != new.pk
    assert set(NfseSync.objects.values_list("office_certificate_id", flat=True)) == {new.pk}


@pytest.mark.django_db
def test_revoking_stops_the_collection_of_the_whole_office() -> None:
    organization = office()
    ClientCompany.objects.create(organization=organization, name="Cliente", cnpj_masked=CLIENT_CNPJ)
    certificate = store_office_certificate(
        organization=organization,
        pfx_bytes=make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ),
        password=PASSWORD,
    )
    assert eligible_procuracao_syncs().exists()

    revoke_office_certificate(certificate)

    assert not eligible_procuracao_syncs().exists()
    assert AuditEvent.objects.filter(action="hub.office_certificate.revoked").count() == 1
