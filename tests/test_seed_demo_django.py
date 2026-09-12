from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.hub.models import ClientCompany, DteMessage, NfseDocument
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


def _seed() -> None:
    call_command("seed_demo", "--password", "seed-only-password-9f2c", verbosity=0)


@override_settings(DEBUG=True)
def test_seed_populates_every_screen_with_data() -> None:
    _seed()

    organization = Organization.objects.get(slug="escritorio-demo")
    assert ClientCompany.objects.filter(organization=organization).count() == 8
    assert NfseDocument.objects.filter(organization=organization).exists()
    assert DteMessage.objects.filter(organization=organization, read_at=None).exists()


@override_settings(DEBUG=True)
def test_seed_is_idempotent() -> None:
    _seed()
    first = NfseDocument.objects.count()
    _seed()

    assert NfseDocument.objects.count() == first
    assert Organization.objects.filter(slug="escritorio-demo").count() == 1


@override_settings(DEBUG=False, SEED_DEMO_ALLOWED=False)
def test_seed_refuses_to_fabricate_evidence_outside_debug() -> None:
    with pytest.raises(CommandError):
        _seed()
