from __future__ import annotations

import pytest
from django.core.management import call_command

from apps.hub.models import OfficeProfile, ProductModule
from apps.organizations.models import Membership, Organization
from apps.platform.models import Entitlement, TenantContract

pytestmark = pytest.mark.django_db


def _run(**extra):
    call_command(
        "provision_office",
        name="Fedrizzi Contabilidade",
        slug="fedrizzi-contabilidade",
        owner_email="dono@fedrizzi.test",
        **extra,
    )


def test_all_modules_enabled_and_idempotent():
    other = Organization.objects.create(name="Outro", slug="outro")
    _run()
    _run()
    org = Organization.objects.get(slug="fedrizzi-contabilidade")
    codes = {c for c, _ in ProductModule.Code.choices}
    assert (
        set(
            ProductModule.objects.filter(organization=org, enabled=True).values_list(
                "code", flat=True
            )
        )
        == codes
    )
    assert (
        set(
            Entitlement.objects.filter(organization=org, enabled=True).values_list(
                "code", flat=True
            )
        )
        == codes
    )
    assert TenantContract.objects.filter(organization=org).count() == 1
    assert Membership.objects.filter(organization=org, role="owner").count() == 1
    assert OfficeProfile.objects.get(organization=org).nfse_collection_mode == "procuracao"
    assert not ProductModule.objects.filter(organization=other).exists()


def test_dry_run_writes_nothing():
    call_command("provision_office", name="X", slug="x", dry_run=True)
    assert not Organization.objects.filter(slug="x").exists()
