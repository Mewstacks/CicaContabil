"""T10.6: Serpro screens of the office. Flag off by default; scope, roles and copy."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany, ProductModule
from apps.integra.models import IntegraCall, OfficeSerproIdentity, RadarSignal
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db

ON = override_settings(INTEGRA_SCREENS_ENABLED=True)


def _login(user: User, office: Organization) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(office.id)
    session.save()
    return client


def _office(slug: str, *, module: bool = True) -> Organization:
    office = Organization.objects.create(name=f"Escritório {slug}", slug=slug)
    if module:
        ProductModule.objects.create(
            organization=office, code=ProductModule.Code.INTEGRA, enabled=True
        )
    return office


def _member(office: Organization, role: str, email: str) -> User:
    user = User.objects.create_user(email=email, password="uma-senha-longa")
    Membership.objects.create(organization=office, user=user, role=role)
    return user


def test_the_screens_are_off_by_default() -> None:
    office = _office("desligado")
    owner = _member(office, Membership.Role.OWNER, "dono@example.test")
    client = _login(owner, office)

    assert client.get(reverse("hub:serpro")).status_code == 404
    assert client.get(reverse("hub:serpro-radar")).status_code == 404


@ON
def test_an_anonymous_visitor_is_sent_to_login() -> None:
    response = Client().get(reverse("hub:serpro"))

    assert response.status_code == 302 and reverse("hub:login") in response["Location"]


@ON
def test_the_status_shows_mode_termo_and_the_cost_per_month_to_the_owner() -> None:
    office = _office("custo")
    owner = _member(office, Membership.Role.OWNER, "dono@example.test")
    OfficeSerproIdentity.objects.create(organization=office, monthly_cap_cents=1000)
    for cost in (24, 24):
        IntegraCall.objects.create(
            organization=office, service_key="pgdasd.declaracoes", http_status=200,
            charged=True, cost_cents=cost, request_tag="t",
        )

    response = _login(owner, office).get(reverse("hub:serpro"))

    html = response.content.decode()
    assert response.status_code == 200
    assert "Custo por mês" in html and "R$ 0,48" in html and "Limite R$ 10,00" in html
    assert "5%" in html
    assert "Padrão" in html and "Desligado" in html


@ON
def test_cost_is_hidden_from_roles_that_do_not_manage_the_office() -> None:
    office = _office("papel")
    operator = _member(office, Membership.Role.OPERATOR, "operador@example.test")
    IntegraCall.objects.create(
        organization=office, service_key="x", http_status=200, charged=True,
        cost_cents=24, request_tag="t",
    )

    html = _login(operator, office).get(reverse("hub:serpro")).content.decode()

    assert "Custo por mês" not in html and "R$ 0,24" not in html


@ON
def test_the_radar_lists_only_the_companies_of_this_office() -> None:
    mine_office, other_office = _office("meu"), _office("outro")
    owner = _member(mine_office, Membership.Role.OWNER, "dono@example.test")
    now = datetime(2026, 11, 23, tzinfo=UTC)
    mine = ClientCompany.objects.create(
        organization=mine_office, name="Padaria Central", cnpj_masked="11222333000181"
    )
    other = ClientCompany.objects.create(
        organization=other_office, name="Empresa Alheia", cnpj_masked="11444777000161"
    )
    RadarSignal.objects.create(
        organization=mine_office, company=mine, evento="E0301",
        event_date=date(2026, 11, 10), observed_at=now,
    )
    RadarSignal.objects.create(
        organization=mine_office, company=mine, evento="E0601",
        sem_procuracao=True, observed_at=now,
    )
    RadarSignal.objects.create(
        organization=other_office, company=other, evento="E0301",
        event_date=date(2026, 11, 11), observed_at=now,
    )

    html = _login(owner, mine_office).get(reverse("hub:serpro-radar")).content.decode()

    assert "Padaria Central" in html and "Empresa Alheia" not in html
    assert "10/11/2026" in html and "Sem procuração" in html and "Sem novidade" in html
    assert "1 empresa" in html and "1 sem procuração" in html


@ON
def test_the_screens_carry_no_explanatory_paragraph() -> None:
    office = _office("copy")
    owner = _member(office, Membership.Role.OWNER, "dono@example.test")
    client = _login(owner, office)

    for name in ("hub:serpro", "hub:serpro-radar"):
        html = client.get(reverse(name)).content.decode()
        main = html.split('id="conteudo"', 1)[1]
        assert not re.search(r"<p[ >]", main), name


@ON
def test_empty_states_offer_a_way_out() -> None:
    office = _office("vazio")
    owner = _member(office, Membership.Role.OWNER, "dono@example.test")
    client = _login(owner, office)

    radar = client.get(reverse("hub:serpro-radar")).content.decode()
    status = client.get(reverse("hub:serpro")).content.decode()

    assert "Radar desligado" in radar and reverse("hub:serpro") in radar
    assert "Nenhuma chamada ao Serpro" in status and reverse("hub:serpro-radar") in status
