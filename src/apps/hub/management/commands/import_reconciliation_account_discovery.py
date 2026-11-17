"""Import a pinned, private discovery into separate immutable technical evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from apps.hub.account_discovery import AccountDiscoveryError, import_account_discovery
from apps.hub.account_discovery_contract import LIMIT
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Confere descoberta de planos; --apply registra fatos técnicos imutáveis."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--organization", required=True)
        for name in ("portfolio", "accounts", "discovery"):
            parser.add_argument(f"--{name}-file", required=True)
        parser.add_argument("--expected-sha256", required=True)
        parser.add_argument("--expected-size-bytes", required=True, type=int)
        parser.add_argument("--request-reference", required=True)
        parser.add_argument("--expected-manifest")
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            organization = Organization.objects.get(pk=UUID(options["organization"]))
            inputs = {}
            for key in ("portfolio", "accounts", "discovery"):
                with Path(options[f"{key}_file"]).open("rb") as stream:
                    inputs[f"{key}_raw"] = stream.read(LIMIT + 1)
            if options["apply"] and not options["expected_manifest"]:
                raise AccountDiscoveryError("Informe o manifesto da prévia antes de aplicar.")
            result = import_account_discovery(
                organization=organization,
                **inputs,
                expected_sha256=options["expected_sha256"],
                expected_size_bytes=options["expected_size_bytes"],
                expected_manifest=options["expected_manifest"],
                request_reference=options["request_reference"],
                apply=options["apply"],
            )
        except AccountDiscoveryError as exc:
            raise CommandError(str(exc)) from None
        except (
            OSError,
            ValueError,
            TypeError,
            Organization.DoesNotExist,
            IntegrityError,
            ValidationError,
        ):
            raise CommandError("Confira a descoberta e o escritório; nada foi preparado.") from None
        self.stdout.write(json.dumps(result, sort_keys=True))
