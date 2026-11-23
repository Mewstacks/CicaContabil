"""D-304: escritório criado agora nasce em `procuracao`; o que já existe segue em `certificate`."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import OfficeProfile
from apps.organizations.models import Organization
from apps.platform.models import PlatformAccess, PlatformConfiguration
from apps.platform.signup import issue_signup
from conftest import complete_mfa

pytestmark = pytest.mark.django_db


@patch("apps.platform.signup.lookup_company")
def test_a_self_service_signup_starts_in_procuracao_mode(mock_lookup: object) -> None:
    mock_lookup.return_value = {"razao_social": "CICA Escritório Novo"}  # type: ignore[attr-defined]
    PlatformConfiguration.objects.get_or_create(key="default")
    issued = issue_signup(
        email="novo@example.com",
        full_name="Responsável",
        cnpj="68340160000113",
        terms_accepted=True,
    )

    created = Client().post(
        f"/comecar/verificar/{issued.token}/", {"password": "correct-horse-battery-staple"}
    )

    assert created.status_code == 302
    profile = OfficeProfile.objects.get(cnpj_hash=issued.intent.cnpj_hash)
    assert profile.nfse_collection_mode == OfficeProfile.NfseCollectionMode.PROCURACAO


def test_an_office_provisioned_by_the_console_starts_in_procuracao_mode(client: Client) -> None:
    developer = User.objects.create_user(email="dev@example.test", password="safe-password-123")
    PlatformAccess.objects.create(user=developer, role=PlatformAccess.Role.DEVELOPER)
    client.force_login(developer)
    complete_mfa(client)

    client.post(reverse("platform:tenants"), {"name": "Novo escritório", "slug": "novo-console"})

    profile = OfficeProfile.objects.get(organization__slug="novo-console")
    assert profile.nfse_collection_mode == OfficeProfile.NfseCollectionMode.PROCURACAO


def test_an_office_without_an_explicit_mode_is_a_legacy_office() -> None:
    office = Organization.objects.create(name="Legado", slug="legado-padrao")

    profile = OfficeProfile.objects.create(organization=office)

    assert profile.nfse_collection_mode == OfficeProfile.NfseCollectionMode.CERTIFICATE
