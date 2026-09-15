from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.platform.models import PlatformConfiguration
from apps.platform.signup import SignupError, issue_signup, provision_signup

pytestmark = pytest.mark.django_db


def configure_trial() -> None:
    configuration, _ = PlatformConfiguration.objects.get_or_create(key="default")
    configuration.trial_ai_included_requests = 3
    configuration.copilot_available_for_offices = True
    configuration.save(
        update_fields=[
            "trial_ai_included_requests",
            "copilot_available_for_offices",
            "updated_at",
        ]
    )


def issue():
    configure_trial()
    return issue_signup(
        email="owner@example.com",
        full_name="Proprietário",
        password="correct-horse-battery-staple",
        office_name="Escritório",
        cnpj="68340160000113",
        company_count=1,
        module_codes=["ai"],
        terms_accepted=True,
    )


def test_confirmation_cannot_be_replayed_to_authenticate_owner():
    issued = issue()
    provision_signup(token=issued.token)
    with pytest.raises(SignupError):
        provision_signup(token=issued.token)
    client = Client()
    response = client.get(f"/comecar/verificar/{issued.token}/")
    assert response.status_code == 410
    assert "_auth_user_id" not in client.session


def test_expired_confirmation_cannot_create_office():
    issued = issue()
    issued.intent.expires_at = timezone.now() - timedelta(seconds=1)
    issued.intent.save(update_fields=["expires_at"])
    with pytest.raises(SignupError):
        provision_signup(token=issued.token)
    issued.intent.refresh_from_db()
    assert issued.intent.organization_id is None
