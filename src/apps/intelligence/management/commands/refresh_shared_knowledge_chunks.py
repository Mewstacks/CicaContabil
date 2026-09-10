# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.intelligence.retrieval import refresh_shared_knowledge_chunks


class Command(BaseCommand):
    help = "Atualiza o RAG global aprovado no banco separado de conhecimento."

    def handle(self, *args, **options) -> None:
        result = refresh_shared_knowledge_chunks()
        self.stdout.write(
            "conhecimento global: "
            f"{result.created} criado(s), {result.removed} removido(s), "
            f"{result.unchanged} mantido(s)."
        )
