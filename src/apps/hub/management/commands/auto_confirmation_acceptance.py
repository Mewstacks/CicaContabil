"""D-390: read-only D-73 measurement of the owner-reviewed D-388 automatic confirmations."""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.hub.auto_confirmation_review import acceptance_report
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Mede a precisão das confirmações automáticas revisadas pela proprietária (D-390)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--organization", required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            organization = Organization.objects.get(pk=options["organization"])
        except (Organization.DoesNotExist, ValueError) as exc:
            raise CommandError("Escritório não encontrado.") from exc
        report = acceptance_report(organization.pk)
        self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
