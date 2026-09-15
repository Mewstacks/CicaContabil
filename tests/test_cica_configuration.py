import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage
from django.test import Client

from apps.accounts.mfa import SESSION_KEY
from apps.platform.models import (
    OperationalRun,
    Plan,
    PlanServiceRate,
    PlatformAccess,
    PlatformConfiguration,
    TenantContract,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", ["support", "commercial"])
def test_non_developers_cannot_change_configuration(user, role):
    before = list(PlatformConfiguration.objects.values())
    PlatformAccess.objects.create(user=user, role=role)
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()
    assert (
        client.post("/platform/configuracoes/", {"support_email": "bad@example.com"}).status_code
        == 403
    )
    assert list(PlatformConfiguration.objects.values()) == before


def test_developer_configures_public_contact_and_mfa_is_required(user):
    PlatformAccess.objects.create(user=user, role="developer", mfa_required=False)
    client = Client()
    client.force_login(user)
    assert client.get("/platform/configuracoes/").status_code == 302
    session = client.session
    session[SESSION_KEY] = True
    session.save()
    response = client.post(
        "/platform/configuracoes/",
        {
            "provider_cnpj": "68.340.160/0001-13",
            "support_email": "support@example.com",
            "privacy_email": "privacy@example.com",
            "support_hours": "Segunda a sexta, 9h às 18h",
            "legal_address": "Endereço de teste",
        },
    )
    assert response.status_code == 302
    config = PlatformConfiguration.objects.get()
    assert config.updated_by == user
    response = Client().get("/legal/privacidade/")
    assert response.status_code == 200
    assert b"privacy@example.com" in response.content
    assert b"Minuta" in response.content


def test_developer_sees_the_latest_scheduled_operation_without_customer_content(user):
    PlatformAccess.objects.create(user=user, role="developer")
    OperationalRun.objects.create(
        task=OperationalRun.Task.REFRESH_REFORM,
        state=OperationalRun.State.SUCCEEDED,
        summary={"created": 2, "updated": 1, "failed": 0},
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()

    response = client.get("/platform/configuracoes/")

    assert response.status_code == 200
    assert b"Rotinas agendadas" in response.content
    assert b"Radar da Reforma" in response.content
    assert b"created: 2" in response.content


def test_developer_syncs_verified_provider_registry(user, monkeypatch):
    PlatformAccess.objects.create(user=user, role="developer")
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()
    monkeypatch.setattr(
        "apps.platform.configuration.lookup_company",
        lambda _cnpj: {
            "status": "found",
            "source": "BrasilAPI",
            "razao_social": "MEWSTACK DESENVOLVIMENTO DE SISTEMAS LTDA",
            "nome_fantasia": "MEWSTACK",
            "descricao_situacao_cadastral": "ATIVA",
            "data_inicio_atividade": "2026-08-03",
            "cnae_fiscal_descricao": "Desenvolvimento de programas de computador sob encomenda",
            "descricao_tipo_de_logradouro": "RUA",
            "logradouro": "PRIMITIVA ZATTI",
            "numero": "297",
            "bairro": "SAO CIRO",
            "cep": "95057560",
            "municipio": "CAXIAS DO SUL",
            "uf": "RS",
        },
    )
    response = client.post(
        "/platform/configuracoes/",
        {
            "action": "provider_sync",
            "provider_cnpj": "68.340.160/0001-13",
            "support_email": "",
            "privacy_email": "",
            "support_hours": "",
            "legal_address": "",
        },
    )
    assert response.status_code == 302
    config = PlatformConfiguration.objects.get()
    assert config.provider_registration_status == "ATIVA"
    assert config.provider_opened_on.isoformat() == "2026-08-03"
    assert config.support_email == ""
    assert config.legal_address == (
        "RUA PRIMITIVA ZATTI, 297, SAO CIRO · CAXIAS DO SUL / RS · CEP 95057-560"
    )


def test_legal_document_unknown_returns_404():
    assert Client().get("/legal/unknown/").status_code == 404


def test_legal_documents_use_configured_provider_contact():
    config = PlatformConfiguration.objects.get(key="default")
    config.support_phone = "(54) 99657-3455"
    config.save(update_fields=["support_phone", "updated_at"])

    response = Client().get("/legal/termos/")

    assert response.status_code == 200
    assert b"68.340.160/0001-13" in response.content
    assert b'href="tel:+5554996573455"' in response.content


def test_developer_saves_draft_commercial_catalog(user):
    PlatformAccess.objects.create(user=user, role="developer", mfa_required=False)
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()
    response = client.post(
        "/platform/configuracoes/",
        {
            "action": "plan",
            "code": "suite-cica",
            "name": "Suíte CICA",
            "version": "1",
            "monthly_price_brl": "0.00",
            "modules": ["ai", "journey"],
            "ai_included_requests": "25",
            "ai_overage_price_brl": "0.00",
        },
    )
    assert response.status_code == 302
    plan = Plan.objects.get(code="suite-cica")
    assert plan.is_active is False
    assert plan.monthly_price_cents == 0
    assert plan.modules == ["ai", "journey"]
    rate = PlanServiceRate.objects.get(plan=plan, action_code="ai.answer")
    assert rate.included_units == 25
    assert rate.overage_unit_price_cents == 0


def test_developer_configures_the_ai_allowance_for_new_trials(user):
    PlatformAccess.objects.create(user=user, role="developer", mfa_required=False)
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()

    response = client.post(
        "/platform/configuracoes/",
        {"action": "trial", "trial_ai_included_requests": "12"},
    )

    assert response.status_code == 302
    assert PlatformConfiguration.objects.get(key="default").trial_ai_included_requests == 12


def test_developer_can_prepare_and_release_the_copilot_for_offices(user):
    PlatformAccess.objects.create(user=user, role="developer", mfa_required=False)
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()
    PlatformConfiguration.objects.update_or_create(
        key="default",
        defaults={
            "local_llm_endpoint": "http://runtime.mewstack.test",
            "local_llm_model": "qwen-local",
        },
    )

    response = client.post(
        "/platform/configuracoes/",
        {
            "action": "copilot-availability",
            "copilot_available_for_offices": "on",
            "trial_ai_included_requests": "12",
        },
    )

    assert response.status_code == 302
    config = PlatformConfiguration.objects.get(key="default")
    assert config.copilot_available_for_offices is True
    assert config.trial_ai_included_requests == 12


def test_developer_configures_the_local_runtime_without_exposing_or_clearing_its_token(
    developer_client,
):
    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "local-runtime",
            "local_llm_endpoint": "http://runtime.mewstack.test/",
            "local_llm_model": "qwen-local",
            "local_llm_api_key": "runtime-secret",
            "local_multimodal_endpoint": "http://documents.mewstack.test/",
        },
    )

    assert response.status_code == 302
    config = PlatformConfiguration.objects.get(key="default")
    assert config.local_llm_endpoint == "http://runtime.mewstack.test"
    assert config.local_llm_model == "qwen-local"
    assert config.local_llm_api_key == "runtime-secret"
    assert config.local_multimodal_endpoint == "http://documents.mewstack.test"
    page = developer_client.get("/platform/configuracoes/")
    assert b"runtime-secret" not in page.content

    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "local-runtime",
            "local_llm_endpoint": "http://runtime.mewstack.test",
            "local_llm_model": "qwen-local-v2",
            "local_llm_api_key": "",
            "local_multimodal_endpoint": "",
        },
    )
    assert response.status_code == 302
    config.refresh_from_db()
    assert config.local_llm_model == "qwen-local-v2"
    assert config.local_llm_api_key == "runtime-secret"


def test_developer_configures_transactional_email_without_exposing_or_clearing_secret(
    developer_client,
):
    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "transactional-email",
            "transactional_email_host": "smtp.mewstack.test",
            "transactional_email_port": "587",
            "transactional_email_username": "cica",
            "transactional_email_password": "smtp-secret",
            "transactional_email_use_tls": "on",
            "transactional_email_from": "acesso@cicacontabil.com.br",
        },
    )
    assert response.status_code == 302
    config = PlatformConfiguration.objects.get(key="default")
    assert config.transactional_email_host == "smtp.mewstack.test"
    assert config.transactional_email_password == "smtp-secret"
    page = developer_client.get("/platform/configuracoes/")
    assert b"smtp-secret" not in page.content

    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "transactional-email",
            "transactional_email_host": "smtp.mewstack.test",
            "transactional_email_port": "587",
            "transactional_email_username": "cica",
            "transactional_email_password": "",
            "transactional_email_use_tls": "on",
            "transactional_email_from": "acesso@cicacontabil.com.br",
        },
    )
    assert response.status_code == 302
    config.refresh_from_db()
    assert config.transactional_email_password == "smtp-secret"


def test_developer_can_test_smtp_without_saving_or_sending_email(developer_client, monkeypatch):
    class FakeBackend:
        def __init__(self):
            self.opened = False
            self.closed = False

        def open(self):
            self.opened = True

        def close(self):
            self.closed = True

    backend = FakeBackend()
    monkeypatch.setattr(
        "apps.platform.configuration.smtp_backend_for_configuration", lambda _config: backend
    )
    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "transactional-email-test",
            "transactional_email_host": "smtp.mewstack.test",
            "transactional_email_port": "587",
            "transactional_email_username": "",
            "transactional_email_password": "",
            "transactional_email_from": "acesso@cicacontabil.com.br",
        },
        follow=True,
    )
    assert response.status_code == 200
    assert backend.opened is True
    assert backend.closed is True
    assert not PlatformConfiguration.objects.filter(
        transactional_email_host="smtp.mewstack.test"
    ).exists()
    assert b"Nenhum e-mail foi enviado" in response.content


def test_database_email_backend_uses_configured_sender_and_rejects_missing_transport(monkeypatch):
    from apps.common.database_email import DatabaseEmailBackend

    backend = DatabaseEmailBackend()
    monkeypatch.setattr(backend, "_configuration", lambda: None)
    with pytest.raises(ImproperlyConfigured):
        backend.send_messages([EmailMessage("subject", "body", None, ["person@example.test"])])


def test_database_email_backend_applies_the_console_sender_without_exposing_secret(monkeypatch):
    from apps.common.database_email import DatabaseEmailBackend

    configuration, _ = PlatformConfiguration.objects.get_or_create(key="default")
    configuration.transactional_email_host = "smtp.mewstack.test"
    configuration.transactional_email_username = "cica"
    configuration.transactional_email_password = "smtp-secret"
    configuration.transactional_email_from = "acesso@cicacontabil.com.br"
    configuration.save()
    captured: list[EmailMessage] = []

    class FakeBackend:
        def send_messages(self, messages):
            captured.extend(messages)
            return len(messages)

    backend = DatabaseEmailBackend()
    monkeypatch.setattr(backend, "_configuration", lambda: configuration)
    monkeypatch.setattr(
        "apps.common.database_email.smtp_backend_for_configuration",
        lambda _configuration, *, fail_silently: FakeBackend(),
    )
    message = EmailMessage("subject", "body", None, ["person@example.test"])
    assert backend.send_messages([message]) == 1
    assert captured == [message]
    assert message.from_email == "acesso@cicacontabil.com.br"
    assert "smtp-secret" not in repr(captured)


def test_copilot_cannot_be_released_before_a_local_runtime_is_configured(developer_client):
    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "copilot-availability",
            "copilot_available_for_offices": "on",
            "trial_ai_included_requests": "12",
        },
    )

    assert response.status_code == 200
    assert b"Configure o endpoint e o modelo locais" in response.content
    assert PlatformConfiguration.objects.get(key="default").copilot_available_for_offices is False


def test_new_plan_page_has_no_unsaved_uuid_or_editing_label(developer_client):
    response = developer_client.get("/platform/configuracoes/")
    assert response.status_code == 200
    assert b'name="plan_id"' not in response.content
    assert b"Configurar plano" in response.content
    assert b">Cancelar<" not in response.content
    assert b'value="68.340.160/0001-13"' in response.content
    assert b">68.340.160/0001-13<" in response.content


def test_provider_registry_failure_does_not_save_partial_data(user, monkeypatch):
    PlatformAccess.objects.create(user=user, role="developer")
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()
    monkeypatch.setattr(
        "apps.platform.configuration.lookup_company",
        lambda _cnpj: {"status": "unavailable"},
    )

    response = client.post(
        "/platform/configuracoes/",
        {
            "action": "provider_sync",
            "provider_cnpj": "68.340.160/0001-13",
            "support_email": "partial@example.com",
            "support_phone": "(54) 99999-9999",
            "privacy_email": "",
            "support_hours": "horário parcial",
            "legal_address": "endereço parcial",
        },
    )

    assert response.status_code == 200
    assert b"consulta cadastral" in response.content
    assert not PlatformConfiguration.objects.filter(
        support_email="partial@example.com"
    ).exists()


def test_provider_registry_removes_duplicated_address_complement(user, monkeypatch):
    PlatformAccess.objects.create(user=user, role="developer")
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()
    monkeypatch.setattr(
        "apps.platform.configuration.lookup_company",
        lambda _cnpj: {
            "status": "found",
            "source": "BrasilAPI",
            "razao_social": "MEWSTACK DESENVOLVIMENTO DE SISTEMAS LTDA",
            "descricao_situacao_cadastral": "ATIVA",
            "data_inicio_atividade": "2026-08-03",
            "descricao_tipo_de_logradouro": "RUA",
            "logradouro": "PRIMITIVA ZATTI",
            "numero": "297",
            "complemento": "FUNDOSFUNDOS",
            "bairro": "SAO CIRO",
            "cep": "95057560",
            "municipio": "CAXIAS DO SUL",
            "uf": "RS",
        },
    )

    response = client.post(
        "/platform/configuracoes/",
        {
            "action": "provider_sync",
            "provider_cnpj": "68.340.160/0001-13",
            "support_email": "admin@mewstack.com",
            "support_phone": "(54) 99657-3455",
            "privacy_email": "",
            "support_hours": "Segunda a sexta, 09:00-19:00",
            "legal_address": "",
        },
    )

    assert response.status_code == 302
    address = PlatformConfiguration.objects.get().legal_address
    assert "FUNDOSFUNDOS" not in address
    assert "FUNDOS" in address


def test_active_ai_plan_requires_a_positive_quota(developer_client):
    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "plan",
            "code": "invalid-ai",
            "name": "Invalid AI",
            "version": "1",
            "monthly_price_brl": "100.00",
            "modules": ["ai"],
            "ai_included_requests": "0",
            "ai_overage_price_brl": "0.00",
        },
    )
    assert response.status_code == 200
    assert b"Informe ao menos uma pergunta" in response.content
    assert not Plan.objects.filter(code="invalid-ai").exists()


def test_developer_edits_only_uncontracted_plan_and_ai_rate(developer_client):
    plan = Plan.objects.create(code="editable", name="Editable", modules=["ai"])
    PlanServiceRate.objects.create(plan=plan, action_code="ai.answer", included_units=10)
    page = developer_client.get(f"/platform/configuracoes/?plan={plan.pk}")
    assert page.status_code == 200
    assert b'value="10"' in page.content
    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "plan",
            "plan_id": str(plan.pk),
            "code": "editable",
            "name": "Editable revised",
            "version": "2",
            "monthly_price_brl": "149.90",
            "modules": ["ai"],
            "ai_included_requests": "40",
            "ai_overage_price_brl": "0.25",
        },
    )
    assert response.status_code == 302
    plan.refresh_from_db()
    rate = plan.service_rates.get(action_code="ai.answer")
    assert plan.name == "Editable revised"
    assert plan.monthly_price_cents == 14990
    assert rate.included_units == 40
    assert rate.overage_unit_price_cents == 25


@pytest.fixture
def developer_client(user):
    PlatformAccess.objects.create(user=user, role="developer")
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()
    return client


@pytest.mark.parametrize("plan_id", ["invalid", "00000000-0000-0000-0000-000000000000"])
def test_catalog_invalid_target_does_not_create_plan(developer_client, plan_id):
    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "plan",
            "plan_id": plan_id,
            "code": "unexpected",
            "name": "Unexpected",
            "version": "1",
            "monthly_price_brl": "99.00",
        },
    )
    assert response.status_code == 404
    assert not Plan.objects.filter(code="unexpected").exists()


@pytest.mark.parametrize("status", ["trial", "active", "archived"])
def test_catalog_cannot_rewrite_contracted_version(developer_client, organization, status):
    plan = Plan.objects.create(code="agreed", name="Agreed", modules=["ai"])
    TenantContract.objects.create(organization=organization, plan=plan, status=status)
    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "plan",
            "plan_id": str(plan.pk),
            "code": "agreed",
            "name": "Rewritten",
            "version": "2",
            "monthly_price_brl": "99.00",
            "modules": ["journey"],
        },
    )
    assert response.status_code == 409
    plan.refresh_from_db()
    assert plan.name == "Agreed"
    assert plan.modules == ["ai"]
    assert plan.monthly_price_cents == 0


def test_zero_contract_snapshot_is_not_repriced(organization):
    from apps.platform.billing import snapshot_contract_pricing

    plan = Plan.objects.create(code="free", name="Free", monthly_price_cents=0)
    contract = TenantContract.objects.create(organization=organization, plan=plan)
    plan.monthly_price_cents = 9900
    plan.save()
    snapshot_contract_pricing(contract)
    snapshot_contract_pricing(contract)
    contract.refresh_from_db()
    assert contract.monthly_price_cents == 0
    new_contract = TenantContract.objects.create(organization=organization, plan=plan)
    new_contract.refresh_from_db()
    assert new_contract.monthly_price_cents == 9900
