# mypy: disable-error-code="no-untyped-def"
from django.core.management.base import BaseCommand, CommandError

from apps.hub.controlplane import ControlPlaneError, sync_binding
from apps.hub.models import ControlPlaneBinding


class Command(BaseCommand):
    help = "Atualiza permissÃµes e configuraÃ§Ãµes assinadas recebidas do CRMew."

    def handle(self, *args, **options):
        failures = 0
        for binding in ControlPlaneBinding.objects.select_related("organization"):
            try:
                sync_binding(binding)
            except ControlPlaneError as exc:
                failures += 1
                self.stderr.write(f"{binding.organization}: {exc}")
            else:
                self.stdout.write(f"{binding.organization}: controle atualizado")
        if failures:
            raise CommandError(f"{failures} instalaÃ§Ã£o(Ãµes) nÃ£o sincronizaram.")
