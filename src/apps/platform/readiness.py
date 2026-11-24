"""O que falta para vender (E5, E8): checagem de ambiente, só leitura e sem imprimir segredo.

Cada item diz se está pronto, se bloqueia a venda e qual é a ação do responsável. Nada aqui muda
configuração nem chama serviço externo; lê `settings` e a `PlatformConfiguration`.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from apps.platform.legal_versions import LEGAL_VERSION
from apps.platform.models import PlatformConfiguration
from apps.platform.subscription import selectable_plans


@dataclass(frozen=True)
class Check:
    key: str
    label: str
    ok: bool
    blocker: bool
    detail: str
    action: str


def _configuration() -> PlatformConfiguration | None:
    return PlatformConfiguration.objects.filter(key="default").first()


def run_checks() -> list[Check]:
    configuration = _configuration()
    email_ready = bool(
        configuration
        and configuration.transactional_email_host
        and configuration.transactional_email_from
        and configuration.transactional_email_password
    )
    contacts_ready = bool(
        configuration and configuration.support_email and configuration.privacy_email
    )
    key_id = str(settings.FIELD_ENCRYPTION_ACTIVE_KEY_ID or "")
    keys = (
        settings.FIELD_ENCRYPTION_KEYS if isinstance(settings.FIELD_ENCRYPTION_KEYS, dict) else {}
    )
    engine = str(settings.DATABASES["default"]["ENGINE"])
    plans = selectable_plans()
    return [
        Check(
            "developer_full_access",
            "Suporte da plataforma em somente leitura",
            not settings.PLATFORM_DEVELOPER_FULL_ACCESS,
            True,
            "sessões de suporte podem alterar dados de cliente"
            if settings.PLATFORM_DEVELOPER_FULL_ACCESS
            else "somente leitura",
            "Definir PLATFORM_DEVELOPER_FULL_ACCESS=false no ambiente (afeta o suporte atual)",
        ),
        Check(
            "debug",
            "Modo de depuração desligado",
            not settings.DEBUG,
            True,
            "DEBUG ligado" if settings.DEBUG else "desligado",
            "Usar config.settings.production",
        ),
        Check(
            "encryption",
            "Chave de cifra de campos",
            bool(key_id and key_id in keys),
            True,
            "chave ativa presente" if key_id and key_id in keys else "sem chave ativa",
            "Definir FIELD_ENCRYPTION_ACTIVE_KEY_ID e FIELD_ENCRYPTION_KEYS",
        ),
        Check(
            "database",
            "Banco PostgreSQL",
            "postgresql" in engine,
            True,
            engine.rsplit(".", 1)[-1],
            "Apontar DATABASE_URL para o PostgreSQL",
        ),
        Check(
            "broker",
            "Fila Celery em Redis ou Valkey",
            not str(settings.CELERY_BROKER_URL).startswith("memory"),
            True,
            "broker externo"
            if not str(settings.CELERY_BROKER_URL).startswith("memory")
            else "memória",
            "Definir CELERY_BROKER_URL ou REDIS_URL",
        ),
        Check(
            "email",
            "E-mail transacional configurado",
            email_ready,
            True,
            "servidor, remetente e senha presentes" if email_ready else "incompleto ou ausente",
            "Preencher o SMTP no console da plataforma (Brevo, D-77/D-78)",
        ),
        Check(
            "contacts",
            "Contatos de suporte e privacidade",
            contacts_ready,
            True,
            "presentes" if contacts_ready else "faltam e-mail de suporte ou de privacidade",
            "Preencher a configuração da plataforma",
        ),
        Check(
            "legal",
            "Termos revisados (não rascunho)",
            "draft" not in LEGAL_VERSION,
            True,
            LEGAL_VERSION,
            "Revisão jurídica dos termos, da política e do anexo de dados",
        ),
        Check(
            "plans",
            "Planos à venda cadastrados",
            bool(plans),
            True,
            f"{len(plans)} plano(s)" if plans else "nenhum plano ativo com preço",
            "Aprovar a grade de preços (D-307) e cadastrar os planos",
        ),
        Check(
            "collection",
            "Cobrança Asaas pronta",
            bool(
                settings.BILLING_COLLECTION_ENABLED
                and settings.ASAAS_API_KEY
                and settings.ASAAS_WEBHOOK_TOKEN
            ),
            True,
            f"{settings.ASAAS_ENVIRONMENT}; "
            f"chave {'ok' if settings.ASAAS_API_KEY else 'falta'}; "
            f"webhook {'ok' if settings.ASAAS_WEBHOOK_TOKEN else 'falta'}; "
            f"ligada {'sim' if settings.BILLING_COLLECTION_ENABLED else 'não'}",
            "ASAAS_API_KEY, ASAAS_WEBHOOK_TOKEN, BILLING_COLLECTION_ENABLED=true (sandbox antes)",
        ),
        Check(
            "procuracao_lane",
            "Coleta de NFS-e por procuração ligada",
            bool(
                settings.NFSE_PROCURACAO_SYNC_ENABLED
                and settings.NFSE_ADN_ENVIRONMENT == "production"
            ),
            True,
            f"fila {'ligada' if settings.NFSE_PROCURACAO_SYNC_ENABLED else 'desligada'}; "
            f"ADN {settings.NFSE_ADN_ENVIRONMENT}",
            "NFSE_PROCURACAO_SYNC_ENABLED=true e NFSE_ADN_ENVIRONMENT=production após o piloto",
        ),
        Check(
            "turnstile",
            "Desafio anti-robô no cadastro",
            bool(settings.TURNSTILE_SITE_KEY and settings.TURNSTILE_SECRET_KEY),
            False,
            "ligado"
            if settings.TURNSTILE_SITE_KEY and settings.TURNSTILE_SECRET_KEY
            else "desligado",
            "Criar o site no Turnstile e definir TURNSTILE_SITE_KEY e TURNSTILE_SECRET_KEY",
        ),
        Check(
            "sentry",
            "Monitoramento de erros (Sentry)",
            bool(getattr(settings, "SENTRY_DSN", "") or _sentry_on()),
            False,
            "ligado" if _sentry_on() else "desligado",
            "Definir SENTRY_ENABLED=true e SENTRY_DSN",
        ),
    ]


def _sentry_on() -> bool:
    try:
        import sentry_sdk
    except ImportError:  # pragma: no cover - sentry is a runtime dependency in production
        return False
    return sentry_sdk.get_client().is_active()
