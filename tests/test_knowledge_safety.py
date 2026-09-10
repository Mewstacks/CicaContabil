from __future__ import annotations

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.intelligence.models import KnowledgeSource
from apps.knowledge.models import SharedKnowledgeSource
from apps.organizations.models import Organization


class KnowledgeSafetyTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme")

    def test_tenant_source_requires_origin_version_and_sanitized_content(self) -> None:
        with self.assertRaisesRegex(ValidationError, "origem verificável"):
            KnowledgeSource.objects.create(
                organization=self.organization,
                kind=KnowledgeSource.Kind.PROCEDURE,
                title="Sem origem",
                version="1",
                source_reference="",
                content="Conteúdo aprovado.",
                content_hash="a" * 64,
            )
        with self.assertRaisesRegex(ValidationError, "CPF"):
            KnowledgeSource.objects.create(
                organization=self.organization,
                kind=KnowledgeSource.Kind.VALIDATED_CASE,
                title="Caso identificável",
                version="1",
                source_reference="Caso interno",
                content="CPF 123.456.789-09 não pode entrar no RAG.",
                content_hash="b" * 64,
            )

    def test_global_source_rejects_identifiable_content_before_shared_rag(self) -> None:
        with self.assertRaisesRegex(ValidationError, "CNPJ"):
            SharedKnowledgeSource.objects.using("knowledge").create(
                kind=SharedKnowledgeSource.Kind.VALIDATED_CASE,
                title="Caso global inválido",
                version="1",
                source_reference="Caso anonimizado",
                content="CNPJ 12.345.678/0001-99 não deve ser promovido.",
                content_hash="c" * 64,
            )
