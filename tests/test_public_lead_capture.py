from __future__ import annotations

import pytest
from django.core.cache import cache
from django.db import connection
from django.test import Client, override_settings
from django.urls import reverse

from apps.platform.models import Lead

pytestmark = pytest.mark.django_db

PAYLOAD = {
    "office_name": "Contabilidade Exemplo",
    "contact_name": "Pessoa Responsável",
    "contact_email": "contato@exemplo.test",
    "company_count": 12,
    "message": "Queremos conhecer o produto.",
}


def test_contact_details_are_encrypted_at_rest() -> None:
    cache.clear()
    Client().post(reverse("hub:proposal"), PAYLOAD)

    lead = Lead.objects.get()
    assert lead.contact_email == PAYLOAD["contact_email"]

    with connection.cursor() as cursor:
        cursor.execute("SELECT contact_email, contact_name, message FROM platform_lead")
        stored = cursor.fetchone()

    assert PAYLOAD["contact_email"] not in stored
    assert all(column.startswith("enc:") for column in stored)


@override_settings(LEAD_RATE_LIMIT_PER_HOUR=2)
def test_one_address_cannot_flood_the_public_form() -> None:
    cache.clear()
    client = Client()

    responses = [client.post(reverse("hub:proposal"), PAYLOAD) for _ in range(4)]

    assert responses[-1].status_code == 429
    assert Lead.objects.count() == 2
