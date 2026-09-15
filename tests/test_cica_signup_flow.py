from unittest.mock import patch

import pytest
from django.test import Client

from apps.platform.billing import reserve_usage
from apps.platform.legal_versions import LEGAL_VERSION
from apps.platform.models import (
    PlatformConfiguration,
    SignupIntent,
    TenantContract,
    TenantServiceRate,
    UsageMeter,
)
from apps.platform.notifications import TransactionalEmailError
from apps.platform.signup import SignupError, issue_signup

pytestmark = pytest.mark.django_db


def configure_trial(*, allowance: int = 3) -> PlatformConfiguration:
    configuration, _ = PlatformConfiguration.objects.get_or_create(key="default")
    configuration.trial_ai_included_requests = allowance
    configuration.copilot_available_for_offices = True
    configuration.save(
        update_fields=[
            "trial_ai_included_requests",
            "copilot_available_for_offices",
            "updated_at",
        ]
    )
    return configuration


@patch("apps.platform.signup.lookup_company")
def test_confirmation_requires_a_password_before_provisioning(mock_lookup):
    configure_trial(allowance=3)
    mock_lookup.return_value = {"razao_social": "CICA Escritório Teste"}
    issued = issue_signup(
        email="novo@example.com",
        full_name="Responsável",
        cnpj="68340160000113",
        terms_accepted=True,
    )
    assert issued.intent.terms_version == LEGAL_VERSION
    assert issued.intent.privacy_version == LEGAL_VERSION
    assert issued.intent.terms_accepted_at is not None
    assert issued.intent.terms_acceptance_ip_hash == ""
    assert not issued.intent.marketing_opt_in
    client = Client()
    url = f"/comecar/verificar/{issued.token}/"

    preview = client.get(url)
    assert preview.status_code == 200
    assert b"Defina sua senha" in preview.content
    assert TenantContract.objects.count() == 0

    created = client.post(url, {"password": "correct-horse-battery-staple"})
    assert created.status_code == 302
    assert created.url == "/app/configuracao/"
    contract = TenantContract.objects.get()
    assert contract.monthly_price_cents == 0
    assert contract.selected_modules == [
        "nfse",
        "guides",
        "integra",
        "reconciliation",
        "reform",
        "journey",
        "ai",
    ]
    rate = TenantServiceRate.objects.get(contract=contract, action_code="ai.answer")
    assert rate.included_units == 3
    assert rate.overage_unit_price_cents == 0


@patch("apps.platform.signup.lookup_company")
def test_trial_ai_allowance_is_frozen_before_first_question(mock_lookup):
    mock_lookup.return_value = {"razao_social": "CICA Escritório Teste"}
    configuration = configure_trial(allowance=2)
    issued = issue_signup(
        email="quota@example.com",
        full_name="Responsável",
        cnpj="68340160000113",
        terms_accepted=True,
    )
    client = Client()
    client.post(
        f"/comecar/verificar/{issued.token}/",
        {"password": "correct-horse-battery-staple"},
    )
    issued.intent.refresh_from_db(fields=["organization"])
    contract = TenantContract.objects.get(organization=issued.intent.organization)
    configuration.trial_ai_included_requests = 12
    configuration.save(update_fields=["trial_ai_included_requests", "updated_at"])

    reserve_usage(
        organization=contract.organization,
        action_code="ai.answer",
        idempotency_key="first-trial-question",
    )

    rate = TenantServiceRate.objects.get(contract=contract, action_code="ai.answer")
    meter = UsageMeter.objects.get(organization=contract.organization, action_code="ai.answer")
    assert rate.included_units == 2
    assert meter.included_units == 2


@patch("apps.platform.signup.lookup_company", return_value={"status": "not_found"})
def test_signup_rejects_a_cnpj_that_the_registry_does_not_find(_mock_lookup):
    configure_trial()
    with pytest.raises(SignupError, match="Não encontramos este CNPJ"):
        issue_signup(
            email="novo@example.com",
            full_name="Responsável",
            cnpj="68340160000113",
            terms_accepted=True,
        )


@patch("apps.platform.signup.lookup_company", return_value={"razao_social": "CICA Teste"})
def test_signup_starts_without_the_unreleased_copilot(_mock_lookup):
    issued = issue_signup(
        email="novo@example.com",
        full_name="Responsável",
        cnpj="68340160000113",
        terms_accepted=True,
    )
    assert "ai" not in issued.intent.selected_modules
    assert issued.intent.trial_ai_included_requests == 0


@patch("apps.platform.signup.lookup_company", return_value={"razao_social": "CICA Teste"})
def test_signup_refuses_to_issue_a_trial_without_required_legal_acceptance(_mock_lookup):
    configure_trial()
    with pytest.raises(SignupError, match="Aceite os documentos"):
        issue_signup(
            email="sem-aceite@example.com",
            full_name="Responsável",
            cnpj="68340160000113",
        )


@patch("apps.platform.signup.lookup_company", return_value={"razao_social": "CICA Teste"})
def test_marketing_opt_in_is_optional_and_is_snapshotted_separately(_mock_lookup):
    configure_trial()
    issued = issue_signup(
        email="marketing@example.com",
        full_name="Responsável",
        cnpj="68340160000113",
        terms_accepted=True,
        marketing_opt_in=True,
    )
    assert issued.intent.marketing_opt_in
    assert issued.intent.marketing_opted_in_at is not None


@patch("apps.platform.signup.lookup_company", return_value={"razao_social": "CICA Teste"})
@patch("apps.hub.views.send_verification_email")
def test_public_signup_keeps_marketing_opt_in_separate_from_required_terms(
    _send_email, _mock_lookup
):
    configure_trial()
    client = Client()
    missing_terms = client.post(
        "/comecar/",
        {
            "full_name": "Responsável",
            "email": "sem-termos@example.com",
            "cnpj": "68340160000113",
        },
    )
    assert missing_terms.status_code == 200
    assert SignupIntent.objects.count() == 0

    issued = client.post(
        "/comecar/",
        {
            "full_name": "Responsável",
            "email": "com-marketing@example.com",
            "cnpj": "68340160000113",
            "accept_terms": "on",
            "accept_marketing": "on",
        },
    )
    assert issued.status_code == 202
    intent = SignupIntent.objects.get(email="com-marketing@example.com")
    assert intent.marketing_opt_in
    assert intent.marketing_opted_in_at is not None
    assert intent.terms_acceptance_ip_hash


@patch("apps.platform.signup.lookup_company", return_value={"razao_social": "CICA Teste"})
@patch("apps.hub.views.send_verification_email", side_effect=TransactionalEmailError("offline"))
def test_signup_rolls_back_the_intent_when_confirmation_delivery_fails(
    _send_email, _mock_lookup
):
    client = Client()

    response = client.post(
        "/comecar/",
        {
            "full_name": "Ana Contadora",
            "email": "ana@example.test",
            "cnpj": "68340160000113",
            "accept_terms": "on",
        },
    )

    assert response.status_code == 200
    assert "Não foi possível enviar a confirmação" in response.content.decode()
    assert not SignupIntent.objects.filter(email="ana@example.test").exists()
