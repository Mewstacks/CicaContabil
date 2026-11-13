"""Read-only comparison of retained title captures, with private technical output."""

from __future__ import annotations

import json
import os
from typing import Any
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.intelligence.native_title_comparison import compare_collected_titles
from apps.intelligence.native_title_contract import MAX_BYTES


class Command(BaseCommand):
    help = "Compara fontes fiscais retidas sem interpretar ausência como estorno ou alterar dados."

    def add_arguments(self, parser: Any) -> None:
        for name in ("organization", "actor", "previous", "current"):
            parser.add_argument(f"--{name}", required=True)
        parser.add_argument("--output", help="Novo arquivo privado de detalhes; nunca sobrescreve.")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            actor = User.objects.get(pk=UUID(options["actor"]), is_active=True)
            result = compare_collected_titles(
                organization_id=UUID(options["organization"]),
                previous_id=UUID(options["previous"]),
                current_id=UUID(options["current"]),
                actor=actor,
            )
            if options["output"]:
                content = json.dumps(result, ensure_ascii=False, indent=2).encode()
                if len(content) > MAX_BYTES:
                    raise ValueError
                descriptor = os.open(options["output"], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(content)
        except (
            ValueError,
            TypeError,
            KeyError,
            OSError,
            ObjectDoesNotExist,
            PermissionDenied,
            ValidationError,
        ):
            raise CommandError(
                "Comparação recusada; confira acesso, contexto, fontes e novo caminho privado."
            ) from None
        self.stdout.write(
            json.dumps(
                {
                    "version": result["version"],
                    "previous": result["previous"],
                    "current": result["current"],
                    "same_capture": result["same_capture"],
                    "counts": result["counts"],
                    "requires_semantic_review": True,
                    "financial_actions_applied": 0,
                    "details_written": bool(options["output"]),
                }
            )
        )
