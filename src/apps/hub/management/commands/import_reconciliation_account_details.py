"""Import only separate technical details; never approve or activate a bank account."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from apps.hub.account_source_contract import LIMIT
from apps.hub.account_source_details import AccountSourceDetailError, import_account_source_details
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Confere complemento privado; --apply acrescenta apenas fatos cadastrais separados."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--organization", required=True)
        parser.add_argument("--portfolio-file", required=True)
        parser.add_argument("--accounts-file", required=True)
        parser.add_argument("--details-file", required=True)
        parser.add_argument("--expected-sha256", required=True)
        parser.add_argument("--expected-size-bytes", required=True, type=int)
        parser.add_argument("--request-reference", required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            organization = Organization.objects.get(pk=UUID(options["organization"]))
            inputs = {}
            for key in ("portfolio", "accounts", "details"):
                with Path(options[f"{key}_file"]).open("rb") as stream:
                    inputs[f"{key}_raw"] = stream.read(LIMIT + 1)
            report = import_account_source_details(
                organization=organization,
                **inputs,
                expected_sha256=options["expected_sha256"],
                expected_size_bytes=options["expected_size_bytes"],
                request_reference=options["request_reference"],
                apply=options["apply"],
            )
        except AccountSourceDetailError as exc:
            raise CommandError(str(exc)) from None
        except (
            OSError,
            ValueError,
            TypeError,
            Organization.DoesNotExist,
            IntegrityError,
            ValidationError,
        ):
            raise CommandError("Confira os arquivos e o escritório; nada foi preparado.") from None
        # Service receipts intentionally contain only hashes, flags and aggregate counts.
        self.stdout.write(json.dumps(report, sort_keys=True))
