"""Check the central Claude key with Anthropic's free token-counting endpoint."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser


class Command(BaseCommand):
    help = "Valida a chave Claude sem gerar resposta nem enviar dados de cliente."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--model", default="claude-sonnet-5")

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.CICA_CLAUDE_API_KEY:
            raise CommandError("Defina CICA_CLAUDE_API_KEY no .env da Mewstack.")

        payload = json.dumps(
            {
                "model": options["model"],
                "output_config": {"effort": "low"},
                "messages": [{"role": "user", "content": "Teste sintetico CICA"}],
            }
        ).encode("utf-8")
        request = Request(
            "https://api.anthropic.com/v1/messages/count_tokens",
            data=payload,
            headers={
                "x-api-key": settings.CICA_CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed HTTPS API URL
                result = json.load(response)
        except HTTPError as exc:
            raise CommandError(
                f"A API Claude recusou a contagem gratuita de tokens (HTTP {exc.code})."
            ) from None
        except URLError:
            raise CommandError(
                "Nao foi possivel conectar a API Claude para a validacao gratuita."
            ) from None

        input_tokens = result.get("input_tokens")
        if not isinstance(input_tokens, int) or input_tokens < 0:
            raise CommandError("A API Claude retornou uma contagem de tokens invalida.")
        self.stdout.write(
            self.style.SUCCESS(
                f"Chave aceita pela API Claude; modelo {options['model']}; "
                f"{input_tokens} tokens de entrada contados sem gerar resposta.",
            )
        )
