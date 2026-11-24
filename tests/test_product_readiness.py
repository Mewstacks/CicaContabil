"""Prontidão para venda (E5/E8): cada item só fica OK com o fato, e a saída não leva segredo."""

from __future__ import annotations

import io
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.platform.models import PlatformConfiguration
from apps.platform.readiness import run_checks
from billing_support import plan

pytestmark = pytest.mark.django_db

KEY_SECRET = "CHAVE-QUE-NAO-PODE-APARECER-77"


def by_key() -> dict[str, Any]:
    return {check.key: check for check in run_checks()}


def configure(**fields: Any) -> PlatformConfiguration:
    configuration, _ = PlatformConfiguration.objects.get_or_create(key="default")
    for name, value in fields.items():
        setattr(configuration, name, value)
    configuration.save()
    return configuration


def test_an_unprepared_environment_fails_every_blocker_and_warns_the_rest() -> None:
    checks = by_key()

    for key in ("email", "contacts", "legal", "plans", "collection", "procuracao_lane"):
        assert checks[key].ok is False and checks[key].blocker is True, key
    for key in ("turnstile", "sentry"):
        assert checks[key].ok is False and checks[key].blocker is False, key
    assert all(check.action for check in checks.values() if not check.ok)


def test_the_support_flag_is_a_blocker_while_support_sessions_can_change_data(
    settings: Any,
) -> None:
    settings.PLATFORM_DEVELOPER_FULL_ACCESS = True
    assert by_key()["developer_full_access"].ok is False
    settings.PLATFORM_DEVELOPER_FULL_ACCESS = False
    assert by_key()["developer_full_access"].ok is True


def test_email_needs_host_sender_and_password_together() -> None:
    configure(transactional_email_host="smtp.example.test", transactional_email_from="a@b.example")
    assert by_key()["email"].ok is False

    configure(transactional_email_password="senha")

    assert by_key()["email"].ok is True


def test_contacts_need_both_support_and_privacy_addresses() -> None:
    configure(support_email="suporte@example.test")
    assert by_key()["contacts"].ok is False

    configure(privacy_email="privacidade@example.test")

    assert by_key()["contacts"].ok is True


def test_plans_turn_ok_only_with_an_active_priced_plan() -> None:
    assert by_key()["plans"].ok is False
    plan("rascunho", price=100, is_active=False)
    assert by_key()["plans"].ok is False

    plan("a", price=19900)

    assert by_key()["plans"].ok is True and "1 plano" in by_key()["plans"].detail


def test_collection_needs_the_key_the_webhook_token_and_the_switch(settings: Any) -> None:
    settings.ASAAS_API_KEY = KEY_SECRET
    settings.ASAAS_WEBHOOK_TOKEN = "t" * 32
    assert by_key()["collection"].ok is False  # chave e webhook, mas desligada
    settings.BILLING_COLLECTION_ENABLED = True

    assert by_key()["collection"].ok is True


def test_the_procuracao_lane_needs_its_flag_and_the_production_adn(settings: Any) -> None:
    settings.NFSE_PROCURACAO_SYNC_ENABLED = True
    settings.NFSE_ADN_ENVIRONMENT = "trial"
    assert by_key()["procuracao_lane"].ok is False

    settings.NFSE_ADN_ENVIRONMENT = "production"

    assert by_key()["procuracao_lane"].ok is True


def test_turnstile_needs_both_keys(settings: Any) -> None:
    settings.TURNSTILE_SITE_KEY = "site"
    assert by_key()["turnstile"].ok is False
    settings.TURNSTILE_SECRET_KEY = "segredo"

    assert by_key()["turnstile"].ok is True


def test_the_terms_stay_a_blocker_while_the_version_is_a_draft() -> None:
    check = by_key()["legal"]

    assert check.ok is False and "draft" in check.detail


def test_the_command_prints_a_table_with_actions_and_never_a_secret(settings: Any) -> None:
    settings.ASAAS_API_KEY = KEY_SECRET
    settings.ASAAS_WEBHOOK_TOKEN = KEY_SECRET + "-webhook"
    settings.TURNSTILE_SECRET_KEY = KEY_SECRET + "-turnstile"
    configure(transactional_email_password=KEY_SECRET + "-smtp")
    out = io.StringIO()

    call_command("product_readiness", stdout=out)

    text = out.getvalue()
    assert KEY_SECRET not in text
    assert "FALTA  Planos à venda cadastrados" in text and "ação:" in text
    assert "bloqueiam a venda." in text


def test_strict_fails_while_a_blocker_remains_and_passes_when_none_does(
    settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(CommandError, match="bloqueiam a venda"):
        call_command("product_readiness", "--strict", stdout=io.StringIO())

    from apps.platform import readiness

    ready = [
        readiness.Check(check.key, check.label, True, check.blocker, "ok", "")
        for check in run_checks()
    ]
    monkeypatch.setattr(
        "apps.platform.management.commands.product_readiness.run_checks", lambda: ready
    )

    call_command("product_readiness", "--strict", stdout=io.StringIO())
