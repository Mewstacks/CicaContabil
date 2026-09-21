"""One bounded, billable Anthropic transport smoke test after cost approval."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser


class Command(BaseCommand):
    help = "Testa uma resposta real do Sonnet 5 com texto sintetico e ate 64 tokens."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--cost-approved",
            action="store_true",
            help="Exige aprovacao especifica do custo antes desta chamada cobrada.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not options["cost_approved"]:
            raise CommandError("A chamada cobrada exige --cost-approved apos aprovacao de custo.")
        if not settings.CICA_CLAUDE_API_KEY:
            raise CommandError("Defina CICA_CLAUDE_API_KEY no .env da Mewstack.")

        payload = {
            "model": "claude-sonnet-5",
            "max_tokens": 64,
            "output_config": {"effort": "low"},
            "messages": [{"role": "user", "content": "Teste sintetico CICA"}],
        }
        request = Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": settings.CICA_CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS API URL
                result = json.loads(response.read(64_000))
        except HTTPError as exc:
            raise CommandError(f"A API Claude recusou a geracao (HTTP {exc.code}).") from None
        except (URLError, TimeoutError, OSError, json.JSONDecodeError):
            raise CommandError("Nao foi possivel validar uma resposta Claude real.") from None

        content = result.get("content") if isinstance(result, dict) else None
        usage = result.get("usage") if isinstance(result, dict) else None
        text_blocks = (
            [block for block in content if isinstance(block, dict) and block.get("type") == "text"]
            if isinstance(content, list)
            else []
        )
        if not text_blocks or not isinstance(usage, dict):
            raise CommandError("A API Claude respondeu sem texto ou uso mensuravel.")
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
            raise CommandError("A API Claude respondeu sem contagem de uso valida.")
        self.stdout.write(
            self.style.SUCCESS(
                "Resposta Sonnet 5 recebida com texto; "
                f"entrada={input_tokens} tokens, saida={output_tokens} tokens."
            )
        )
