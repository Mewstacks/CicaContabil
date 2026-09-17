from __future__ import annotations

import hashlib
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.hub.models import ClientCompany, DominioBankEntry
from apps.intelligence.connectors import CatalogColumn, CatalogTable
from apps.intelligence.models import (
    DataCatalogEntry,
    DominioSchemaObject,
    IntelligenceConnector,
    KnowledgeSource,
)
from apps.intelligence.services import DominioMcp
from apps.intelligence.sync import record_schema_snapshot, sync_bank_entries, sync_companies
from apps.organizations.models import Organization


class SyncAndRagTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme")

    def test_company_sync_is_tenant_scoped_and_idempotent(self) -> None:
        connector = IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="error",
            last_error_code="odbc_sync",
            last_error_message="ODBC indisponível",
            last_error_at=timezone.now(),
        )

        first = sync_companies(
            organization=self.organization,
            connector=connector,
            rows=[{"codigo": "001", "nome": "Empresa Acme", "cnpj_masked": "12.345.678/0001-90"}],
        )
        second = sync_companies(
            organization=self.organization,
            connector=connector,
            rows=[
                {
                    "codigo": "001",
                    "nome": "Empresa Acme Atualizada",
                    "cnpj_masked": "12.345.678/0001-90",
                }
            ],
        )

        self.assertEqual((first.created, first.updated, first.ignored), (1, 0, 0))
        self.assertEqual((second.created, second.updated, second.ignored), (0, 1, 0))
        self.assertEqual(connector.mode, IntelligenceConnector.Mode.DIRECT_ODBC)
        connector.refresh_from_db()
        self.assertEqual(connector.status, "healthy")
        self.assertFalse(connector.last_error_code)
        self.assertIsNone(connector.last_error_at)

    def test_full_snapshot_pauses_missing_dominio_companies_without_touching_manual_ones(
        self,
    ) -> None:
        connector = IntelligenceConnector.objects.create(
            organization=self.organization, mode=IntelligenceConnector.Mode.EDGE_AGENT
        )
        synced = ClientCompany.objects.create(
            organization=self.organization, name="Sincronizada", dominio_code="001"
        )
        manual = ClientCompany.objects.create(organization=self.organization, name="Manual")

        result = sync_companies(
            organization=self.organization,
            connector=connector,
            rows=[],
            full_snapshot=True,
        )
        synced.refresh_from_db()
        manual.refresh_from_db()

        self.assertEqual(result.deactivated, 1)
        self.assertFalse(synced.active)
        self.assertTrue(manual.active)

    def test_bank_entry_sync_keeps_the_verified_source_link_state(self) -> None:
        connector = IntelligenceConnector.objects.create(
            organization=self.organization, mode=IntelligenceConnector.Mode.DIRECT_ODBC
        )
        company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa", dominio_code="001"
        )

        result = sync_bank_entries(
            organization=self.organization,
            connector=connector,
            rows=[
                {
                    "source_id": "001|10|20",
                    "company_code": "001",
                    "occurred_on": "2026-08-31",
                    "description": "Recebimento",
                    "amount": "12.34",
                    "direction": "C",
                    "is_linked": 1,
                }
            ],
        )

        entry = DominioBankEntry.objects.get(organization=self.organization)
        self.assertEqual((result.created, result.updated, result.ignored), (1, 0, 0))
        self.assertEqual(entry.company, company)
        self.assertEqual(entry.amount_cents, 1234)
        self.assertTrue(entry.is_linked)

    def test_bank_entry_sync_reports_when_the_source_limit_is_reached(self) -> None:
        connector = IntelligenceConnector.objects.create(
            organization=self.organization, mode=IntelligenceConnector.Mode.DIRECT_ODBC
        )
        ClientCompany.objects.create(
            organization=self.organization, name="Empresa", dominio_code="001"
        )

        with patch("apps.intelligence.sync.MAX_BANK_ENTRY_ROWS", 1):
            result = sync_bank_entries(
                organization=self.organization,
                connector=connector,
                rows=[
                    {
                        "source_id": "001|10|20",
                        "company_code": "001",
                        "occurred_on": "2026-08-31",
                        "amount": "12.34",
                    }
                ],
            )

        self.assertTrue(result.may_be_truncated)

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
