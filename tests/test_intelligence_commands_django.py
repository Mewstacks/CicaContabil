from __future__ import annotations

import json
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.intelligence.connectors import CatalogColumn, CatalogTable
from apps.intelligence.models import (
    AssistantSettings,
    ClaudeFallbackApproval,
    Conversation,
    IntelligenceConnector,
    KnowledgeChunk,
    KnowledgeSource,
    TrainingExample,
)
from apps.knowledge.models import SharedKnowledgeSource
from apps.organizations.models import Organization


class IntelligenceCommandTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme")

    def temporary_path(self, filename: str) -> Path:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        return Path(directory) / filename

    def training_example(self) -> TrainingExample:
        return TrainingExample.objects.create(
            organization=self.organization,
            category=TrainingExample.Category.CLASSIFICATION,
            question="Qual acumulador aplicar?",
            expected_answer="Use o acumulador validado.",
            source_references=["Procedimento aprovado § 2"],
            scenario_hash="a" * 64,
            status=TrainingExample.Status.VALIDATED,
        )

    def test_training_artifact_commands_export_manifest_and_lora_job(self) -> None:
        self.training_example()
        manifest_path = self.temporary_path("manifest.jsonl")
        lora_path = self.temporary_path("lora.json")
        manifest_output = StringIO()
        lora_output = StringIO()

        call_command(
            "export_training_manifest",
            organization=self.organization.slug,
            output=str(manifest_path),
            stdout=manifest_output,
        )
        call_command(
            "prepare_lora_job",
            organization=self.organization.slug,
            base_model="modelo-local-aprovado",
            adapter="fiscal-v1",
            template="qwen3",
            output=str(lora_path),
            stdout=lora_output,
        )

        self.assertIn("exemplo", manifest_output.getvalue())
        self.assertEqual(
            json.loads(manifest_path.read_text(encoding="utf-8"))["category"], "classification"
        )
        self.assertEqual(json.loads(lora_path.read_text(encoding="utf-8"))["method"], "qlora")
        self.assertIn("QLoRA", lora_output.getvalue())

    def test_claude_curation_command_only_writes_the_prepared_batch(self) -> None:
        self.training_example()
        AssistantSettings.objects.create(
            organization=self.organization,
            claude_offline_curation_enabled=True,
            claude_curation_max_batch_requests=10,
            claude_model="claude-sonnet-4-20250514",
        )
        ClaudeFallbackApproval.objects.create(
            organization=self.organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            valid_until=timezone.now() + timedelta(days=1),
        )
        output_path = self.temporary_path("curation.jsonl")
        stdout = StringIO()

        call_command(
            "prepare_claude_curation_batch",
            organization=self.organization.slug,
            output=str(output_path),
            stdout=stdout,
        )

        prepared = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertIn("custom_id", prepared)
        self.assertNotIn("api_key", output_path.read_text(encoding="utf-8").casefold())
        self.assertIn("curadoria", stdout.getvalue().casefold())

    def test_evaluation_command_persists_a_passing_gate(self) -> None:
        report_path = self.temporary_path("evaluation.json")
        report_path.write_text(
            json.dumps(
                {
                    "corpus_version": "corpus-v1",
                    "total_cases": 100,
                    "correct_cases": 96,
                    "sourced_cases": 100,
                    "safety_regressions": 0,
                    "tenant_isolation_passed": True,
                    "masking_passed": True,
                    "tool_policy_passed": True,
                }
            ),
            encoding="utf-8",
        )
        stdout = StringIO()

        call_command(
            "record_intelligence_evaluation",
            organization=self.organization.slug,
            report=str(report_path),
            stdout=stdout,
        )

        self.assertIn("acurácia", stdout.getvalue())

    def test_refresh_retention_and_enrollment_commands(self) -> None:
        source = KnowledgeSource.objects.create(
            organization=self.organization,
            kind=KnowledgeSource.Kind.PROCEDURE,
            title="Procedimento",
            version="1",
            source_reference="Manual aprovado",
            content="Conteúdo aprovado para recuperação.",
            content_hash="b" * 64,
            status=KnowledgeSource.Status.APPROVED,
            approved_at=timezone.now(),
        )
        old = Conversation.objects.create(organization=self.organization)
        Conversation.objects.filter(id=old.id).update(
            created_at=timezone.now() - timedelta(days=91)
        )
        refresh_output = StringIO()
        retention_output = StringIO()
        enrollment_output = StringIO()

        call_command(
            "refresh_knowledge_chunks",
            organization=self.organization.slug,
            stdout=refresh_output,
        )
        call_command("purge_intelligence_retention", stdout=retention_output)
        call_command(
            "issue_agent_enrollment",
            organization=self.organization.slug,
            minutes=30,
            stdout=enrollment_output,
        )

        self.assertTrue(KnowledgeChunk.objects.filter(source=source).exists())
        self.assertIn("simulação", retention_output.getvalue().casefold())
        self.assertTrue(Conversation.objects.filter(id=old.id).exists())
        self.assertIn("código", enrollment_output.getvalue().casefold())

    def test_shared_knowledge_refresh_command_has_no_tenant_selector(self) -> None:
        SharedKnowledgeSource.objects.using("knowledge").create(
            kind=SharedKnowledgeSource.Kind.PROCEDURE,
            title="Procedimento geral",
            version="1",
            source_reference="Manual comum",
            content="Conteúdo aprovado para RAG.",
            content_hash="c" * 64,
            status=SharedKnowledgeSource.Status.APPROVED,
        )
        output = StringIO()

        call_command("refresh_shared_knowledge_chunks", stdout=output)

        self.assertIn("conhecimento global", output.getvalue().casefold())

    @patch("apps.intelligence.management.commands.configure_claude_local_key.getpass")
    def test_claude_key_command_stores_a_local_key(self, mocked_getpass) -> None:
        mocked_getpass.return_value = "tenant-local-claude-key"
        stdout = StringIO()

        call_command(
            "configure_claude_local_key",
            organization=self.organization.slug,
            stdout=stdout,
        )

        settings = AssistantSettings.objects.get(organization=self.organization)
        self.assertEqual(settings.claude_api_key, "tenant-local-claude-key")
        self.assertIn("local", stdout.getvalue().casefold())

    @patch("apps.intelligence.management.commands.probe_dominio_odbc.ReadOnlyDominoOdbc.execute")
    def test_odbc_probe_command_can_preview_and_apply_allowlisted_companies(
        self, mocked_execute
    ) -> None:
        mocked_execute.return_value = [{"codigo": "001", "nome": "Empresa Acme"}]
        preview = StringIO()
        applied = StringIO()

        call_command(
            "probe_dominio_odbc",
            organization=self.organization.slug,
            dsn="DominioExterno",
            stdout=preview,
        )
        call_command(
            "probe_dominio_odbc",
            organization=self.organization.slug,
            dsn="DominioExterno",
            apply=True,
            stdout=applied,
        )

        self.assertIn("nada foi espelhado", preview.getvalue().casefold())
        self.assertTrue(
            IntelligenceConnector.objects.filter(organization=self.organization).exists()
        )
        self.assertIn("espelho atualizado", applied.getvalue().casefold())

    @patch("apps.intelligence.management.commands.discover_dominio_schema.ReadOnlyDominoOdbc")
    def test_schema_discovery_command_previews_and_records_only_metadata(self, mocked_odbc) -> None:
        adapter = mocked_odbc.return_value
        adapter.list_catalog_tables.return_value = [
            CatalogTable(schema_name="dbo", object_name="geempre", object_kind="table")
        ]
        adapter.list_catalog_columns.return_value = [
            CatalogColumn(name="codigo", type_name="varchar", ordinal=1, nullable=False)
        ]
        preview = StringIO()
        applied = StringIO()

        call_command(
            "discover_dominio_schema",
            organization=self.organization.slug,
            dsn="DominioExterno",
            stdout=preview,
        )
        call_command(
            "discover_dominio_schema",
            organization=self.organization.slug,
            dsn="DominioExterno",
            apply=True,
            stdout=applied,
        )

        self.assertIn("nada foi persistido", preview.getvalue().casefold())
        self.assertIn("catálogo salvo", applied.getvalue().casefold())

    def test_missing_organization_is_rejected_by_operational_commands(self) -> None:
        with self.assertRaises(CommandError):
            call_command(
                "prepare_lora_job",
                organization="absent",
                base_model="m",
                adapter="a",
                template="qwen3",
                output="x",
            )
