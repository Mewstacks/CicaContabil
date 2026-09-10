# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

import os

from django.core.management.base import BaseCommand

from apps.hub.controlplane import ControlPlaneError, send_heartbeat
from apps.hub.models import ControlPlaneBinding
from apps.intelligence.models import IntelligenceConnector


class Command(BaseCommand):
    help = "Envia saúde e atraso de sync ao CRMew, sem conteúdo de cliente."

    def handle(self, *args, **options) -> None:
        release = os.environ.get("SENTRY_RELEASE", "unknown")
        failures = 0
        for binding in ControlPlaneBinding.objects.select_related("organization"):
            connectors = IntelligenceConnector.objects.filter(organization=binding.organization)
            lag = max((connector.sync_lag_seconds for connector in connectors), default=0)
            unhealthy = connectors.filter(status__in=["error", "revoked"]).exists()
            try:
                send_heartbeat(
                    binding,
                    release=release,
                    health="degraded" if unhealthy else "healthy",
                    sync_lag_seconds=lag,
                    error_fingerprint="connector-unhealthy" if unhealthy else "",
                )
            except ControlPlaneError as exc:
                failures += 1
                self.stderr.write(f"{binding.organization_id}: {exc}")
        if failures:
            self.stderr.write(self.style.WARNING(f"{failures} heartbeat(s) não enviados."))
        else:
            self.stdout.write(self.style.SUCCESS("Heartbeats enviados."))
