"""Ano de competência nunca leva separador de milhar ("2.026"), mesmo com USE_THOUSAND_SEPARATOR."""

from __future__ import annotations

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.fap.models import FapBatch
from apps.hub.models import ProductModule
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db


def _owner_client(modules: tuple[str, ...]) -> tuple[Client, Organization, User]:
    org = Organization.objects.create(name="Escritório Ano", slug="escritorio-ano")
    for code in modules:
        ProductModule.objects.create(organization=org, code=code, enabled=True)
    user = User.objects.create_user(email="dono@ano.test", password="uma-senha-longa-2026")
    Membership.objects.create(organization=org, user=user, role=Membership.Role.OWNER)
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(org.id)
    session.save()
    return client, org, user


def test_fgts_title_shows_the_plain_year() -> None:
    client, _, _ = _owner_client(("fgts",))
    html = client.get("/app/fgts/", {"mes": "2026-10"}).content.decode()
    assert "Apuração 10/2026" in html
    assert "2.026" not in html


def test_fap_batch_and_list_show_the_plain_year() -> None:
    client, org, user = _owner_client(("fap",))
    batch = FapBatch.objects.create(organization=org, year=2026, created_by=user)
    listing = client.get("/app/fap/").content.decode()
    detail = client.get(f"/app/fap/lotes/{batch.pk}/").content.decode()
    assert "2.026" not in listing and "2.026" not in detail
    assert "Vigência 2026" in detail
