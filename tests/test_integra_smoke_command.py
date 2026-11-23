from __future__ import annotations

from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.integra.client import Credentials


@pytest.fixture
def credentials() -> Credentials:
    return Credentials(
        consumer_key="consumer-key",
        consumer_secret="consumer-secret",
        certificate_path=Path(__file__),
        certificate_password="",
        contratante="11.111.111/1111-11",
        autor_pedido="11.111.111/1111-11",
        environment="trial",
    )


@patch("apps.integra.management.commands.integra_smoke.credentials_from_settings")
@patch("apps.integra.management.commands.integra_smoke.IntegraClient")
def test_smoke_command_is_a_preflight_until_execute_is_explicit(
    client: MagicMock, configured_credentials: MagicMock, credentials: Credentials
) -> None:
    configured_credentials.return_value = credentials
    output = StringIO()

    call_command("integra_smoke", "--contribuinte", "11.111.111/1111-11", stdout=output)

    client.assert_not_called()
    assert "Prévia concluída sem chamada externa" in output.getvalue()


@patch("apps.integra.management.commands.integra_smoke.credentials_from_settings")
@patch("apps.integra.management.commands.integra_smoke.IntegraClient")
def test_smoke_command_requires_production_cost_confirmation(
    client: MagicMock, configured_credentials: MagicMock, credentials: Credentials
) -> None:
    configured_credentials.return_value = replace(credentials, environment="production")

    with pytest.raises(CommandError, match="approve-billable-production"):
        call_command(
            "integra_smoke",
            "--contribuinte",
            "11.111.111/1111-11",
            "--service",
            "dctfweb.guia",
            "--execute",
        )

    client.assert_not_called()


@patch("apps.integra.management.commands.integra_smoke.credentials_from_settings")
@patch("apps.integra.management.commands.integra_smoke.IntegraClient")
def test_smoke_command_calls_only_after_explicit_confirmation(
    client: MagicMock, configured_credentials: MagicMock, credentials: Credentials
) -> None:
    configured_credentials.return_value = credentials
    client.return_value.call.return_value = {"status": 200}

    call_command(
        "integra_smoke",
        "--contribuinte",
        "11.111.111/1111-11",
        "--execute",
    )

    client.return_value.call.assert_called_once_with(
        "dte.situacao", contribuinte="11.111.111/1111-11", dados=None
    )


@pytest.mark.parametrize("key", ["pgdasd.transmitir", "pgmei.beneficio", "mit.encerrar"])
@pytest.mark.parametrize("environment", ["trial", "production"])
@patch("apps.integra.management.commands.integra_smoke.credentials_from_settings")
@patch("apps.integra.management.commands.integra_smoke.IntegraClient")
def test_smoke_command_never_declares_or_records_anything(
    client: MagicMock,
    configured_credentials: MagicMock,
    credentials: Credentials,
    key: str,
    environment: str,
) -> None:
    configured_credentials.return_value = replace(credentials, environment=environment)

    with pytest.raises(CommandError, match="altera a situação fiscal"):
        call_command(
            "integra_smoke",
            "--contribuinte",
            "11.111.111/1111-11",
            "--service",
            key,
            "--execute",
            "--approve-billable-production",
            "--confirm-effect",
        )

    client.assert_not_called()


@patch("apps.integra.management.commands.integra_smoke.credentials_from_settings")
@patch("apps.integra.management.commands.integra_smoke.IntegraClient")
def test_smoke_command_asks_for_a_confirmation_before_registering_a_ciencia_in_production(
    client: MagicMock, configured_credentials: MagicMock, credentials: Credentials
) -> None:
    configured_credentials.return_value = replace(credentials, environment="production")
    client.return_value.call.return_value = {"status": 200}
    arguments = [
        "integra_smoke",
        "--contribuinte",
        "11.111.111/1111-11",
        "--service",
        "caixapostal.detalhe",
        "--execute",
        "--approve-billable-production",
    ]

    with pytest.raises(CommandError, match="confirm-effect"):
        call_command(*arguments)
    client.assert_not_called()

    call_command(*arguments, "--confirm-effect", stdout=StringIO())
    client.return_value.call.assert_called_once()


@patch("apps.integra.management.commands.integra_smoke.credentials_from_settings")
@patch("apps.integra.management.commands.integra_smoke.IntegraClient")
def test_smoke_command_previews_a_declaration_service_without_calling(
    client: MagicMock, configured_credentials: MagicMock, credentials: Credentials
) -> None:
    configured_credentials.return_value = credentials
    output = StringIO()

    call_command(
        "integra_smoke",
        "--contribuinte",
        "11.111.111/1111-11",
        "--service",
        "pgdasd.transmitir",
        stdout=output,
    )

    client.assert_not_called()
    assert "Classe:      F" in output.getvalue()
