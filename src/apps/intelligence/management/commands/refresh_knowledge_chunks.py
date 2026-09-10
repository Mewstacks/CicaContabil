# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.retrieval import refresh_knowledge_chunks
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = (
        "Atualiza os blocos RAG criptografados de fontes aprovadas, "
        "sem enviar conteúdo a provedores."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--organization", help="Slug de um escritório; omita para todos os ativos."
        )

    def handle(self, *args, **options) -> None:
        organizations = Organization.objects.filter(is_active=True)
        if slug := options.get("organization"):
            organizations = organizations.filter(slug=slug)
            if not organizations.exists():
                raise CommandError("Escritório não encontrado ou inativo.")
        for organization in organizations:
            result = refresh_knowledge_chunks(organization=organization)
            self.stdout.write(
                f"{organization.slug}: {result.created} criado(s), "
                f"{result.removed} removido(s), {result.unchanged} mantido(s)."
            )
