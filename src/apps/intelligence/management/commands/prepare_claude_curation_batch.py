# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.models import AssistantSettings, ClaudeFallbackApproval
from apps.intelligence.training import claude_curation_batch_spec
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Prepara JSONL de curadoria Claude; não envia lote nem usa a chave local."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument("--output", required=True, help="Arquivo JSONL local protegido")

    def handle(self, *args, **options) -> None:
        selector = options["organization"]
        organization = resolve_organization(selector)
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        assistant_settings = AssistantSettings.objects.filter(organization=organization).first()
        approval = ClaudeFallbackApproval.objects.filter(organization=organization).first()
        if assistant_settings is None:
            raise CommandError("Política Claude não configurada neste escritório.")
        try:
            spec = claude_curation_batch_spec(
                organization=organization,
                assistant_settings=assistant_settings,
                approval=approval,
            )
            output = Path(options["output"])
            output.parent.mkdir(parents=True, exist_ok=True)
            requests = spec.get("requests")
            if not isinstance(requests, list):
                raise ValueError("Especificação de curadoria sem requests válidos.")
            with output.open("w", encoding="utf-8", newline="\n") as stream:
                for request in requests:
                    stream.write(
                        json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n"
                    )
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                "Lote de curadoria preparado: "
                f"{spec['request_count']} request(s), {spec['corpus_version']}."
            )
        )
