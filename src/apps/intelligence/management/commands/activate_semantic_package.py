# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.models import SemanticPackage
from apps.intelligence.package_governance import activate_semantic_package
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Ativa um pacote semântico somente depois do gate de schema e limites."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument("--package", required=True, help="UUID do pacote semântico")

    def handle(self, *args, **options) -> None:
        selector = options["organization"]
        organization = resolve_organization(selector)
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        package = SemanticPackage.objects.filter(
            id=options["package"], organization=organization
        ).first()
        if package is None:
            raise CommandError("Pacote semântico não encontrado neste escritório.")
        validation = activate_semantic_package(package=package)
        if not validation.valid:
            raise CommandError(validation.reason)
        self.stdout.write(self.style.SUCCESS("Pacote semântico ativado após validação."))
