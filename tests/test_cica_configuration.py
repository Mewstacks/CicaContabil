from datetime import date

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.mail import EmailMessage
from django.db import connection
from django.test import Client

from apps.accounts.mfa import SESSION_KEY
from apps.hub.management.commands.seed_demo import _self_signed_pfx
from apps.integra.client import credentials_from_settings
from apps.organizations.models import Organization
from apps.platform.models import (
    BillingCloseDeferral,
    OperationalRun,
    Plan,
    PlanServiceRate,
    PlatformAccess,
    PlatformConfiguration,
    TenantContract,
)

pytestmark = pytest.mark.django_db


def test_developer_paginates_open_billing_close_deferrals(developer_client):
    for index in range(31):
        office = Organization.objects.create(
            name=f"Escritório adiado {index:02d}", slug=f"adiado-{index:02d}"
        )
        BillingCloseDeferral.objects.create(organization=office, period_start=date(2026, 1, 1))

    first_page = developer_client.get("/platform/configuracoes/")
    second_page = developer_client.get(
        "/platform/configuracoes/", {"billing_deferrals_page": "2"}
    )

    assert first_page.status_code == 200
    assert first_page.context["billing_close_deferrals_total"] == 31
    assert first_page.context["billing_close_deferrals_page"].number == 1
    assert len(first_page.context["billing_close_deferrals"]) == 30
    assert b"31 fechamentos adiados" in first_page.content
    assert b"billing_deferrals_page=2" in first_page.content
    assert second_page.status_code == 200
    assert second_page.context["billing_close_deferrals_page"].number == 2
    assert len(second_page.context["billing_close_deferrals"]) == 1
    assert b"billing_deferrals_page=1" in second_page.content


def test_developer_uploads_encrypted_central_integra_certificate(user, settings):
    PlatformAccess.objects.create(user=user, role="developer")
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()
    pfx_bytes, password = _self_signed_pfx("MEWSTACK INTEGRA")

    response = client.post(
        "/platform/configuracoes/",
        {
            "action": "integra-certificate",
            "password": password,
            "certificate": SimpleUploadedFile(
                "mewstack-integracontador.pfx", pfx_bytes, content_type="application/x-pkcs12"
            ),
        },
    )

    assert response.status_code == 302
    config = PlatformConfiguration.objects.get(key="default")
    assert config.integra_certificate_name == "mewstack-integracontador.pfx"
    assert config.integra_certificate_fingerprint
    assert config.integra_certificate_valid_until is not None
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT integra_certificate_blob FROM platform_platformconfiguration WHERE id = %s",
            [config.id.hex],
        )
        raw = cursor.fetchone()[0]
    assert raw != config.integra_certificate_blob
    settings.INTEGRA_CONSUMER_KEY = "consumer"
    settings.INTEGRA_CONSUMER_SECRET = "secret"
    settings.INTEGRA_CONTRATANTE_CNPJ = "68340160000113"
    settings.INTEGRA_AUTOR_PEDIDO_CNPJ = ""
    settings.INTEGRA_CERTIFICATE_PATH = ""
    credentials = credentials_from_settings()
    assert credentials.certificate_blob == pfx_bytes
    assert credentials.certificate_password == password


def test_developer_can_store_write_only_integra_credentials_without_deploy(user, settings):
    PlatformAccess.objects.create(user=user, role="developer")
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()
    settings.INTEGRA_CONSUMER_KEY = ""
    settings.INTEGRA_CONSUMER_SECRET = ""
    settings.INTEGRA_CONTRATANTE_CNPJ = ""
    settings.INTEGRA_CERTIFICATE_PATH = "configured-in-environment.pfx"

    response = client.post(
        "/platform/configuracoes/",
        {
            "action": "integra-credentials",
            "consumer_key": "key-from-console",
            "consumer_secret": "secret-from-console",
            "integra_contratante_cnpj": "68.340.160/0001-13",
            "integra_autor_pedido_cnpj": "",
            "integra_environment": "trial",
        },
    )

    assert response.status_code == 302
    configuration = PlatformConfiguration.objects.get(key="default")
    assert configuration.integra_consumer_key == "key-from-console"
    assert configuration.integra_consumer_secret == "secret-from-console"
    assert configuration.integra_contratante_cnpj == "68340160000113"
    credentials = credentials_from_settings()
    assert credentials.consumer_key == "key-from-console"
    assert credentials.consumer_secret == "secret-from-console"


def test_production_integra_credentials_require_explicit_confirmation(user):
    PlatformAccess.objects.create(user=user, role="developer")
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()

    response = client.post(
        "/platform/configuracoes/",
        {
            "action": "integra-credentials",
            "consumer_key": "production-key",
            "consumer_secret": "production-secret",
            "integra_contratante_cnpj": "68.340.160/0001-13",
            "integra_environment": "production",
        },
    )

    assert response.status_code == 200
    assert "Confirme a mudança para produção" in response.content.decode()
    assert not PlatformConfiguration.objects.filter(
        integra_consumer_key="production-key"
    ).exists()


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


def test_configuration_is_split_into_focused_deep_linked_sections(user):
    PlatformAccess.objects.create(user=user, role="developer")
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = True
    session.save()

    response = client.get("/platform/configuracoes/")

    assert response.status_code == 200
    content = response.content.decode()
    assert 'class="configuration-nav"' in content
    assert 'href="#config-integra"' in content
    assert 'data-config-group="integra"' in content
    assert 'data-config-group="copilot"' in content
    assert "Identidades usadas em cada consulta" in content
    assert "Acesso da Mewstack ao Serpro" in content
    assert "Salvar credenciais centrais" in content
    assert 'class="credential-status"' in content
    assert 'aria-label="Situação das credenciais"' in content
    assert 'class="integra-setup-status"' in content
    assert "Estado da conex" in content
    assert "A primeira consulta externa continua sendo preparada" in content
    assert "Se??es" not in content


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
            "modules": ["ai", "triage"],
            "ai_included_requests": "25",
            "ai_overage_price_brl": "0.00",
        },
    )
    assert response.status_code == 302
    plan = Plan.objects.get(code="suite-cica")
    assert plan.is_active is False
    assert plan.monthly_price_cents == 0
    assert plan.modules == ["ai", "triage"]
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


def test_developer_configures_mewstack_cloud_fallback_without_exposing_its_secret(
    developer_client,
):
    PlatformConfiguration.objects.update_or_create(
        key="default",
        defaults={
            "local_llm_endpoint": "http://runtime.mewstack.test",
            "local_llm_model": "qwen-local",
        },
    )

    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "cloud-fallback",
            "cloud_fallback_enabled": "on",
            "cloud_fallback_api_key": "mewstack-cloud-secret",
            "cloud_fallback_model": "claude-sonnet-4-5",
            "cloud_fallback_max_request_cents": "35",
            "cloud_fallback_daily_limit_cents": "500",
            "cloud_fallback_monthly_limit_cents": "5000",
        },
    )

    assert response.status_code == 302
    config = PlatformConfiguration.objects.get(key="default")
    assert config.cloud_fallback_enabled is True
    assert config.cloud_fallback_api_key == "mewstack-cloud-secret"
    assert config.cloud_fallback_model == "claude-sonnet-4-5"
    page = developer_client.get("/platform/configuracoes/")
    assert b"mewstack-cloud-secret" not in page.content


def test_claude_env_key_releases_copilot_before_local_pc(developer_client, settings):
    settings.CICA_CLAUDE_API_KEY = "env-only-secret"
    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "cloud-fallback",
            "cloud_fallback_enabled": "on",
            "cloud_fallback_api_key": "",
            "cloud_fallback_model": "claude-sonnet-5",
            "cloud_fallback_max_request_cents": "15",
            "cloud_fallback_daily_limit_cents": "1000",
            "cloud_fallback_monthly_limit_cents": "7500",
        },
    )
    assert response.status_code == 302
    configuration = PlatformConfiguration.objects.get(key="default")
    assert configuration.cloud_fallback_api_key == ""
    assert configuration.cloud_fallback_enabled is True
    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "copilot-availability",
            "copilot_available_for_offices": "on",
            "trial_ai_included_requests": "12",
        },
    )
    assert response.status_code == 302
    configuration.refresh_from_db()
    assert configuration.copilot_available_for_offices is True
    assert b"env-only-secret" not in developer_client.get("/platform/configuracoes/").content


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


def test_copilot_cannot_be_released_without_local_or_claude_runtime(developer_client):
    response = developer_client.post(
        "/platform/configuracoes/",
        {
            "action": "copilot-availability",
            "copilot_available_for_offices": "on",
            "trial_ai_included_requests": "12",
        },
    )

    assert response.status_code == 200
    assert b"Configure Claude com chave e limites ou o runtime local" in response.content
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
            "modules": ["triage"],
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
