"""Tela do radar Simples/MEI (E14): flag, isolamento entre escritórios, planilha e aba."""

from __future__ import annotations

import hashlib
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ClientCompany, NfseDocument, NfseDocumentSide, ProductModule
from apps.organizations.models import Membership, Organization
from test_nfse_procuracao_views import World, login

URL = "hub:radar-teto"


def revenue(company: ClientCompany, amount: str) -> None:
    digest = hashlib.sha256(f"{company.pk}{amount}".encode()).hexdigest()
    document = NfseDocument.objects.create(
        organization=company.organization,
        company=company,
        document_hash=digest,
        original_xml="<x/>",
        source_nsu=digest[:20],
    )
    NfseDocumentSide.objects.create(
        organization=company.organization,
        document=document,
        direction="provided",
        issued_on=timezone.localdate().replace(month=1, day=2),
        service_amount=Decimal(amount),
    )


@pytest.fixture
def world(db: object) -> World:
    built = World()
    built.padaria.tax_regime = "mei"
    built.padaria.save(update_fields=["tax_regime"])
    revenue(built.padaria, "72900.00")
    return built


def test_the_screen_does_not_exist_for_anyone_while_the_flag_is_off(
    world: World, settings: object
) -> None:
    settings.SIMPLES_RADAR_ENABLED = False  # type: ignore[attr-defined]
    client = login(world.owner, world.office)

    assert client.get(reverse(URL)).status_code == 404
    page = client.get(reverse("hub:nfse-center")).content.decode()
    assert reverse(URL) not in page


def test_the_owner_sees_the_company_at_the_alert_level_and_the_tab_appears(
    world: World, settings: object
) -> None:
    settings.SIMPLES_RADAR_ENABLED = True  # type: ignore[attr-defined]
    client = login(world.owner, world.office)

    response = client.get(reverse(URL))
    page = response.content.decode()

    assert response.status_code == 200
    assert "Padaria Central" in page and "alerta 90%" in page and "Só NFS-e" in page
    assert "Oficina Norte" not in page  # sem regime MEI/Simples
    assert reverse(URL) in client.get(reverse("hub:nfse-center")).content.decode()


def test_another_office_never_sees_this_office_companies(world: World, settings: object) -> None:
    settings.SIMPLES_RADAR_ENABLED = True  # type: ignore[attr-defined]
    other_office = Organization.objects.create(name="Outro", slug="outro")
    ProductModule.objects.create(
        organization=other_office, code=ProductModule.Code.NFSE, enabled=True
    )
    user = User.objects.create_user(email="x@outro.example", password="uma-senha-longa")
    Membership.objects.create(organization=other_office, user=user, role=Membership.Role.OWNER)

    page = login(user, other_office).get(reverse(URL)).content.decode()

    assert "Padaria Central" not in page


def test_the_spreadsheet_filters_and_neutralises_formulas(world: World, settings: object) -> None:
    settings.SIMPLES_RADAR_ENABLED = True  # type: ignore[attr-defined]
    world.padaria.name = "=HYPERLINK(1)"
    world.padaria.save(update_fields=["name"])
    client = login(world.owner, world.office)

    response = client.get(reverse(URL), {"export": "csv", "filtro": "alert"})
    text = response.content.decode("utf-8-sig")

    assert response["Content-Type"].startswith("text/csv")
    assert "'=HYPERLINK(1)" in text and "72.900,00" in text and "90%" in text
    empty = client.get(reverse(URL), {"export": "csv", "filtro": "simples"}).content.decode(
        "utf-8-sig"
    )
    assert "Padaria" not in empty and "HYPERLINK" not in empty
