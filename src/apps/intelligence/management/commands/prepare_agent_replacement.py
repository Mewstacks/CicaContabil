"""Prepare a single-use replacement code without printing credentials."""

from __future__ import annotations

import json
import os
from argparse import ArgumentParser
from pathlib import Path
from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.intelligence.agents import issue_enrollment
from apps.intelligence.models import EdgeAgent
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Prepara candidato a agente oficial; preserva manifesto e agente anterior."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--organization", required=True)
        parser.add_argument("--previous", required=True, help="UUID do agente anterior ativo")
        parser.add_argument("--output", required=True, help="Novo arquivo privado para o código")
        parser.add_argument("--minutes", type=int, default=30)

    def handle(self, *args: Any, **options: Any) -> None:
        organization = resolve_organization(options["organization"])
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        try:
            previous_id = UUID(options["previous"])
        except (ValueError, TypeError) as exc:
            raise CommandError("Identificador do agente anterior inválido.") from exc
        previous = EdgeAgent.objects.filter(pk=previous_id, organization=organization).first()
        if previous is None:
            raise CommandError("Agente anterior não encontrado neste escritório.")
        destination = Path(options["output"])
        created = False
        try:
            with transaction.atomic():
                credentials = issue_enrollment(
                    organization=organization,
                    replaces_agent=previous,
                    sync_scope=previous.sync_scope,
                    valid_for_minutes=options["minutes"],
                )
                # Never follow a symlink or overwrite a delivery from another operation.
                descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                created = True
                with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                    json.dump(
                        {
                            "code": credentials.code,
                            "expires_at": credentials.expires_at.isoformat(),
                            "previous_agent_id": str(previous.pk),
                            "scope_revision": previous.sync_scope["revision"],
                            "replacement_protocol": "staged-v1",
                        },
                        output,
                    )
                    output.write("\n")
        except (ValueError, OSError) as exc:
            if created:
                destination.unlink(missing_ok=True)
            raise CommandError("Não foi possível preparar a substituição: " + str(exc)) from exc
        except Exception:
            # A failed database commit must not leave an apparently valid delivery.
            if created:
                destination.unlink(missing_ok=True)
            raise
        self.stdout.write("Código salvo em arquivo privado; agente anterior permanece ativo.")
