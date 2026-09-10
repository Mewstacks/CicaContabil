from __future__ import annotations

import hashlib

from django.test import TestCase
from django.utils import timezone

from apps.intelligence.connectors import CatalogColumn, CatalogTable
from apps.intelligence.models import (
    DataCatalogEntry,
    DominioSchemaObject,
    IntelligenceConnector,
    KnowledgeSource,
)
from apps.intelligence.services import DominioMcp
from apps.intelligence.sync import record_schema_snapshot, sync_companies
from apps.organizations.models import Organization


class SyncAndRagTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme")

    def test_company_sync_is_tenant_scoped_and_idempotent(self) -> None:
        connector = IntelligenceConnector.objects.create(
            organization=self.organization, mode=IntelligenceConnector.Mode.DIRECT_ODBC
        )

        first = sync_companies(
            organization=self.organization,
            connector=connector,
            rows=[{"codigo": "001", "nome": "Empresa Acme", "cnpj_masked": "12.***.***/0001-**"}],
        )
        second = sync_companies(
            organization=self.organization,
            connector=connector,
            rows=[
                {
                    "codigo": "001",
                    "nome": "Empresa Acme Atualizada",
                    "cnpj_masked": "12.***.***/0001-**",
                }
            ],
        )

        self.assertEqual((first.created, first.updated, first.ignored), (1, 0, 0))
        self.assertEqual((second.created, second.updated, second.ignored), (0, 1, 0))
        self.assertEqual(connector.mode, IntelligenceConnector.Mode.DIRECT_ODBC)

    def test_rag_returns_only_approved_compact_source_cards(self) -> None:
        content = "Procedimento para revisar pendência da obrigação fiscal."
        KnowledgeSource.objects.create(
            organization=self.organization,
            kind=KnowledgeSource.Kind.PROCEDURE,
            title="Revisão de obrigação",
            version="v1",
            source_reference="Procedimento interno § 2",
            content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            status=KnowledgeSource.Status.APPROVED,
            approved_at=timezone.now(),
        )
        cards = DominioMcp(self.organization, None).retrieve_knowledge("pendência fiscal")

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].reference, "Procedimento interno § 2")

    def test_schema_discovery_stores_no_rows_and_reopens_review_when_structure_changes(
        self,
    ) -> None:
        table = CatalogTable(schema_name="dbo", object_name="geempre", object_kind="table")
        first = record_schema_snapshot(
            organization=self.organization,
            objects=[
                (
                    table,
                    [CatalogColumn(name="codigo", type_name="varchar", ordinal=1, nullable=False)],
                )
            ],
        )
        schema_object = DominioSchemaObject.objects.get(
            organization=self.organization, object_name="geempre"
        )
        schema_object.approved_for_package = True
        schema_object.save(update_fields=["approved_for_package", "updated_at"])
        second = record_schema_snapshot(
            organization=self.organization,
            objects=[
                (
                    table,
                    [
                        CatalogColumn(
                            name="codigo", type_name="varchar", ordinal=1, nullable=False
                        ),
                        CatalogColumn(
                            name="cpf_responsavel", type_name="varchar", ordinal=2, nullable=True
                        ),
                    ],
                )
            ],
        )
        schema_object.refresh_from_db()

        self.assertEqual((first.created, first.updated, first.unchanged), (1, 0, 0))
        self.assertEqual((second.created, second.updated, second.unchanged), (0, 1, 0))
        self.assertFalse(schema_object.approved_for_package)
        self.assertEqual(schema_object.sensitivity, DataCatalogEntry.Sensitivity.PERSONAL)
        self.assertNotIn("payload", schema_object.columns[0])
