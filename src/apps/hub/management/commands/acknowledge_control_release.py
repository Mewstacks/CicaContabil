# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.hub.controlplane import ControlPlaneError, acknowledge_release
from apps.hub.models import ControlPlaneBinding


class Command(BaseCommand):
    help = "Confirma uma release aplicada ou revertida ao CRMew, sem dados de cliente."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--release", required=True)
        parser.add_argument(
            "--outcome", required=True, choices=["released", "failed", "rolled_back"]
        )

    def handle(self, *args, **options) -> None:
        failures = 0
        for binding in ControlPlaneBinding.objects.all():
            try:
                acknowledge_release(
                    binding,
                    version=str(options["release"]),
                    outcome=str(options["outcome"]),
                )
            except ControlPlaneError as exc:
                failures += 1
                self.stderr.write(f"{binding.organization_id}: {exc}")
        if failures:
            raise CommandError("O CRMew não confirmou a release.")
        self.stdout.write(self.style.SUCCESS("Release confirmada ao CRMew."))
