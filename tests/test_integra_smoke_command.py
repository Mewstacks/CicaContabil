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
