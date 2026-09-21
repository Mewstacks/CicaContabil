from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import patch
from urllib.error import HTTPError

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.hub.models import ClientCompany
from apps.intelligence.gateway import generate_claude_fallback_completion, select_provider
from apps.intelligence.models import (
    AssistantSettings,
    ClaudeFallbackApproval,
    IntelligenceArea,
    ModelVersion,
    TrainingExample,
)
from apps.intelligence.releases import publish_model, rollback_model
from apps.intelligence.training import (
    claude_curation_batch_spec,
    compare_evaluation_runs,
    evaluation_fingerprint,
    evaluation_manifest,
    qlora_job_spec,
    record_evaluation,
    stable_hash,
    training_manifest,
)
from apps.organizations.models import Organization
from apps.platform.models import PlatformConfiguration


class TrainingAndGatewayTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme")

    def test_manifest_only_exports_validated_examples_with_sources(self) -> None:
        TrainingExample.objects.create(
            organization=self.organization,
            category=TrainingExample.Category.RISK,
            question="Caso sem fonte",
            expected_answer="Não exportar",
            source_references=[],
            scenario_hash=stable_hash("no-source"),
            status=TrainingExample.Status.VALIDATED,
        )
        TrainingExample.objects.create(
            organization=self.organization,
            category=TrainingExample.Category.RISK,
            question="Caso aprovado",
            expected_answer="Resposta com fonte",
            source_references=["Manual v1 § 2"],
            scenario_hash=stable_hash("sourced"),
            status=TrainingExample.Status.VALIDATED,
        )

        manifest = training_manifest(organization=self.organization)

        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["source_references"], ["Manual v1 § 2"])

    def test_manifest_keeps_tenant_company_period_and_area_metadata(self) -> None:
        company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa", dominio_code="001"
        )
        TrainingExample.objects.create(
            organization=self.organization,
            company=company,
            area=IntelligenceArea.PAYROLL,
            reference_period="2026-09",
            category=TrainingExample.Category.OBLIGATION,
            question="Qual obrigação da folha revisar?",
            expected_answer="Revise a obrigação com a fonte aprovada.",
            source_references=["Folha § 2"],
            scenario_hash=stable_hash("manifest-scope"),
            status=TrainingExample.Status.VALIDATED,
        )

        item = training_manifest(organization=self.organization)[0]

        self.assertEqual(item["company_id"], str(company.id))
        self.assertEqual(item["area"], IntelligenceArea.PAYROLL)
        self.assertEqual(item["reference_period"], "2026-09")

    def test_manifest_rejects_personal_identifiers_before_artifact_export(self) -> None:
        for field, sensitive_value in (
            ("question", "O CPF é 123.456.789-09?"),
            ("expected_answer", "Use o CNPJ 12.345.678/0001-99 somente na origem."),
            ("source_references", ["Contato: pessoa@example.test"]),
        ):
            with self.subTest(field=field):
                organization = Organization.objects.create(
                    name=f"Office {field}", slug=f"office-{field}"
                )
                payload: dict[str, object] = {
                    "organization": organization,
                    "category": TrainingExample.Category.SAFETY,
                    "question": "Qual procedimento revisar?",
                    "expected_answer": "Consulte a fonte aprovada.",
                    "source_references": ["Manual § 1"],
                    "scenario_hash": stable_hash("personal-data", field),
                    "status": TrainingExample.Status.VALIDATED,
                }
                payload[field] = sensitive_value
                TrainingExample.objects.create(**payload)

                with self.assertRaisesRegex(ValueError, "identificador pessoal"):
                    training_manifest(organization=organization)

    def test_training_example_rejects_company_from_another_office(self) -> None:
        other = Organization.objects.create(name="Outra", slug="outra")
        foreign_company = ClientCompany.objects.create(
            organization=other, name="Estrangeira", dominio_code="999"
        )

        with self.assertRaisesRegex(ValidationError, "mesmo escritório"):
            TrainingExample.objects.create(
                organization=self.organization,
                company=foreign_company,
                category=TrainingExample.Category.SAFETY,
                question="Exemplo indevido",
                expected_answer="Não deve persistir.",
                source_references=["Teste"],
                scenario_hash=stable_hash("foreign-company"),
                status=TrainingExample.Status.VALIDATED,
            )

    def test_training_and_evaluation_manifests_are_disjoint(self) -> None:
        common = {
            "organization": self.organization,
            "category": TrainingExample.Category.OBLIGATION,
            "question": "Qual obrigação revisar?",
            "expected_answer": "Consulte a fonte aprovada.",
            "source_references": ["Manual § 1"],
            "status": TrainingExample.Status.VALIDATED,
        }
        training = TrainingExample.objects.create(
            **common,
            scenario_hash=stable_hash("training-split"),
            dataset_split=TrainingExample.DatasetSplit.TRAINING,
        )
        evaluation = TrainingExample.objects.create(
            **common,
            scenario_hash=stable_hash("evaluation-split"),
            dataset_split=TrainingExample.DatasetSplit.EVALUATION,
        )

        train_manifest = training_manifest(organization=self.organization)
        evaluation_set = evaluation_manifest(organization=self.organization)
        _version, evaluation_hash, evaluation_count = evaluation_fingerprint(
            organization=self.organization
        )

        self.assertEqual([item["id"] for item in train_manifest], [str(training.id)])
        self.assertEqual([item["id"] for item in evaluation_set], [str(evaluation.id)])
        self.assertEqual(evaluation_count, 1)
        self.assertEqual(len(evaluation_hash), 64)

    def test_evaluation_gate_requires_quality_sources_and_security(self) -> None:
        _, failed = record_evaluation(
            organization=self.organization,
            report={
                "total_cases": 100,
                "correct_cases": 96,
                "sourced_cases": 99,
                "safety_regressions": 0,
                "tenant_isolation_passed": True,
                "masking_passed": True,
                "tool_policy_passed": True,
            },
        )
        _, passed = record_evaluation(
            organization=self.organization,
            report={
                "total_cases": 100,
                "correct_cases": 95,
                "sourced_cases": 100,
                "safety_regressions": 0,
                "tenant_isolation_passed": True,
                "masking_passed": True,
                "tool_policy_passed": True,
            },
        )

        self.assertFalse(failed.passed)
        self.assertTrue(passed.passed)

    def test_regression_comparison_requires_same_frozen_suite_and_no_quality_loss(self) -> None:
        baseline, _ = record_evaluation(
            organization=self.organization,
            report={
                "suite_name": "regressao-v1",
                "total_cases": 100,
                "correct_cases": 96,
                "sourced_cases": 100,
                "safety_regressions": 0,
                "tenant_isolation_passed": True,
                "masking_passed": True,
                "tool_policy_passed": True,
            },
        )
        regressed, _ = record_evaluation(
            organization=self.organization,
            report={
                "suite_name": "regressao-v1",
                "total_cases": 100,
                "correct_cases": 95,
                "sourced_cases": 100,
                "safety_regressions": 0,
                "tenant_isolation_passed": True,
                "masking_passed": True,
                "tool_policy_passed": True,
            },
        )

        result = compare_evaluation_runs(baseline=baseline, candidate=regressed)

        self.assertFalse(result.passed)
        self.assertIn("reduziu", result.reason)

        improved, _ = record_evaluation(
            organization=self.organization,
            report={
                "suite_name": "regressao-v1",
                "total_cases": 100,
                "correct_cases": 97,
                "sourced_cases": 100,
                "safety_regressions": 0,
                "tenant_isolation_passed": True,
                "masking_passed": True,
                "tool_policy_passed": True,
            },
        )
        mismatched_suite, _ = record_evaluation(
            organization=self.organization,
            report={
                "suite_name": "regressao-v2",
                "total_cases": 100,
                "correct_cases": 97,
                "sourced_cases": 100,
                "safety_regressions": 0,
                "tenant_isolation_passed": True,
                "masking_passed": True,
                "tool_policy_passed": True,
            },
        )
        failed_baseline, _ = record_evaluation(
            organization=self.organization,
            report={
                "suite_name": "regressao-v1",
                "total_cases": 100,
                "correct_cases": 94,
                "sourced_cases": 100,
                "safety_regressions": 0,
                "tenant_isolation_passed": True,
                "masking_passed": True,
                "tool_policy_passed": True,
            },
        )

        self.assertTrue(compare_evaluation_runs(baseline=baseline, candidate=improved).passed)
        self.assertFalse(
            compare_evaluation_runs(baseline=baseline, candidate=mismatched_suite).passed
        )
        self.assertFalse(
            compare_evaluation_runs(baseline=failed_baseline, candidate=improved).passed
        )

    def test_qlora_job_is_reproducible_and_requires_sourced_examples(self) -> None:
        TrainingExample.objects.create(
            organization=self.organization,
            category=TrainingExample.Category.CLASSIFICATION,
            question="Classificar serviço",
            expected_answer="Use a regra aprovada.",
            source_references=["Procedimento 2.1"],
            scenario_hash=stable_hash("qlora-sourced"),
            status=TrainingExample.Status.VALIDATED,
        )

        first = qlora_job_spec(
            organization=self.organization,
            base_model="qwen-14b",
            adapter_name="acme-2026-09",
            chat_template="qwen3",
        )
        second = qlora_job_spec(
            organization=self.organization,
            base_model="qwen-14b",
            adapter_name="acme-2026-09",
            chat_template="qwen3",
        )

        self.assertEqual(first["corpus_version"], second["corpus_version"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["method"], "qlora")
        self.assertEqual(first["chat_template"], "qwen3")
        self.assertEqual(first["required_evaluation"]["source_coverage_percent"], 100)

        with self.assertRaisesRegex(ValueError, "modelo base local"):
            qlora_job_spec(
                organization=self.organization,
                base_model="../remote-model",
                adapter_name="acme-2026-09",
                chat_template="qwen3",
            )

    def test_claude_curation_batch_is_tenant_bound_and_requires_anonymized_examples(self) -> None:
        TrainingExample.objects.create(
            organization=self.organization,
            category=TrainingExample.Category.RISK,
            question="Quando revisar a obrigação?",
            expected_answer="Revise a fonte aprovada antes do vencimento.",
            source_references=["Manual aprovado § 3"],
            scenario_hash=stable_hash("curation-safe"),
            status=TrainingExample.Status.VALIDATED,
        )
        assistant_settings = AssistantSettings.objects.create(
            organization=self.organization,
            claude_model="claude-sonnet-4-20250514",
            claude_offline_curation_enabled=True,
            claude_curation_max_batch_requests=10,
        )
        approval = ClaudeFallbackApproval.objects.create(
            organization=self.organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=500,
            monthly_limit_cents=4_000,
            valid_until=timezone.now() + timedelta(days=1),
        )

        batch = claude_curation_batch_spec(
            organization=self.organization,
            assistant_settings=assistant_settings,
            approval=approval,
        )

        serialized = json.dumps(batch, ensure_ascii=False)
        self.assertEqual(batch["format"], "hubcontador.claude-curation-batch.v1")
        self.assertEqual(batch["request_count"], 1)
        self.assertIn("curation-", batch["requests"][0]["custom_id"])
        self.assertNotIn("claude_api_key", serialized)
        self.assertNotIn("local-key", serialized)

        TrainingExample.objects.create(
            organization=self.organization,
            category=TrainingExample.Category.RISK,
            question="Revisar CPF 123.456.789-09?",
            expected_answer="Não enviar identificador.",
            source_references=["Manual aprovado § 4"],
            scenario_hash=stable_hash("curation-personal"),
            status=TrainingExample.Status.VALIDATED,
        )
        with self.assertRaisesRegex(ValueError, "identificador pessoal"):
            claude_curation_batch_spec(
                organization=self.organization,
                assistant_settings=assistant_settings,
                approval=approval,
            )

    def test_claude_can_start_before_local_pc_and_requires_timeout_afterward(self) -> None:
        platform_configuration, _ = PlatformConfiguration.objects.update_or_create(
            key="default",
            defaults={
                "cloud_fallback_enabled": True,
                "cloud_fallback_api_key": "mewstack-test-key",
                "cloud_fallback_model": "claude-sonnet-4-5",
            },
        )
        settings = AssistantSettings.objects.create(
            organization=self.organization,
            claude_fallback_enabled=True,
            claude_allowed_roles=["owner"],
        )
        approval = ClaudeFallbackApproval.objects.create(
            organization=self.organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=1_000,
            monthly_limit_cents=10_000,
        )

        before_pc = select_provider(
            settings=settings,
            approval=approval,
            platform_configuration=platform_configuration,
            role="owner",
            local_available=False,
            local_timed_out=False,
        )
        allowed = select_provider(
            settings=settings,
            approval=approval,
            platform_configuration=platform_configuration,
            role="owner",
            local_available=False,
            local_timed_out=True,
        )

        self.assertEqual(before_pc.provider, "claude")
        self.assertEqual(allowed.provider, "claude")
        platform_configuration.local_llm_endpoint = "http://private-model.test/v1"
        blocked = select_provider(
            settings=settings,
            approval=approval,
            platform_configuration=platform_configuration,
            role="owner",
            local_available=False,
            local_timed_out=False,
        )
        self.assertIsNone(blocked.provider)

    def test_cloud_fallback_requires_a_mewstack_provider_key(self) -> None:
        settings = AssistantSettings.objects.create(
            organization=self.organization,
            claude_fallback_enabled=True,
            claude_allowed_roles=["owner"],
        )
        approval = ClaudeFallbackApproval.objects.create(
            organization=self.organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=1_000,
            monthly_limit_cents=10_000,
        )

        decision = select_provider(
            settings=settings,
            approval=approval,
            platform_configuration=None,
            role="owner",
            local_available=False,
            local_timed_out=True,
        )

        self.assertIsNone(decision.provider)
        self.assertIn("Mewstack", decision.reason)

    def test_model_publication_requires_a_passing_matching_evaluation(self) -> None:
        version = ModelVersion.objects.create(
            organization=self.organization, name="local-v2", corpus_version="corpus-v2"
        )
        evaluation, _ = record_evaluation(
            organization=self.organization,
            report={
                "corpus_version": "corpus-v2",
                "total_cases": 100,
                "correct_cases": 98,
                "sourced_cases": 100,
                "safety_regressions": 0,
                "tenant_isolation_passed": True,
                "masking_passed": True,
                "tool_policy_passed": True,
            },
        )

        publish_model(
            organization=self.organization, version=version, evaluation=evaluation, actor=None
        )

        version.refresh_from_db()
        self.assertTrue(version.is_active)

    def test_model_publication_rejects_an_evaluation_for_a_different_adapter_artifact(self) -> None:
        manifest_hash = "a" * 64
        artifact_hash = "b" * 64
        version = ModelVersion.objects.create(
            organization=self.organization,
            name="local-v3",
            corpus_version="corpus-v3",
            manifest_sha256=manifest_hash,
            base_model="qwen3-14b",
            adapter_version="acme-v3",
            adapter_artifact_sha256=artifact_hash,
        )
        report = {
            "corpus_version": "corpus-v3",
            "manifest_sha256": manifest_hash,
            "evaluation_manifest_sha256": "d" * 64,
            "base_model": "qwen3-14b",
            "adapter_version": "acme-v3",
            "adapter_artifact_sha256": "c" * 64,
            "total_cases": 100,
            "correct_cases": 98,
            "sourced_cases": 100,
            "safety_regressions": 0,
            "tenant_isolation_passed": True,
            "masking_passed": True,
            "tool_policy_passed": True,
        }
        mismatched, _ = record_evaluation(organization=self.organization, report=report)

        with self.assertRaisesRegex(ValueError, "não corresponde"):
            publish_model(
                organization=self.organization,
                version=version,
                evaluation=mismatched,
                actor=None,
            )

        report["adapter_artifact_sha256"] = artifact_hash
        matching, _ = record_evaluation(organization=self.organization, report=report)
        publish_model(
            organization=self.organization, version=version, evaluation=matching, actor=None
        )
        version.refresh_from_db()
        self.assertTrue(version.is_active)

    def test_model_rollback_reactivates_a_previously_approved_version(self) -> None:
        previous = ModelVersion.objects.create(
            organization=self.organization,
            name="local-v1",
            corpus_version="corpus-v1",
        )
        evaluation, _ = record_evaluation(
            organization=self.organization,
            report={
                "corpus_version": previous.corpus_version,
                "total_cases": 100,
                "correct_cases": 96,
                "sourced_cases": 100,
                "safety_regressions": 0,
                "tenant_isolation_passed": True,
                "masking_passed": True,
                "tool_policy_passed": True,
            },
        )
        current = ModelVersion.objects.create(
            organization=self.organization,
            name="local-v2",
            corpus_version="corpus-v2",
            is_active=True,
        )

        rollback_model(
            organization=self.organization, version=previous, evaluation=evaluation, actor=None
        )

        previous.refresh_from_db()
        current.refresh_from_db()
        self.assertTrue(previous.is_active)
        self.assertFalse(current.is_active)

    def test_model_publication_rejects_a_regression_against_the_active_model(self) -> None:
        active = ModelVersion.objects.create(
            organization=self.organization,
            name="local-v1",
            corpus_version="corpus-v1",
            is_active=True,
        )
        record_evaluation(
            organization=self.organization,
            report={
                "suite_name": "regressao-v1",
                "corpus_version": active.corpus_version,
                "total_cases": 100,
                "correct_cases": 98,
                "sourced_cases": 100,
                "safety_regressions": 0,
                "tenant_isolation_passed": True,
                "masking_passed": True,
                "tool_policy_passed": True,
            },
        )
        candidate = ModelVersion.objects.create(
            organization=self.organization, name="local-v2", corpus_version="corpus-v2"
        )
        evaluation, _ = record_evaluation(
            organization=self.organization,
            report={
                "suite_name": "regressao-v1",
                "corpus_version": candidate.corpus_version,
                "total_cases": 100,
                "correct_cases": 95,
                "sourced_cases": 100,
                "safety_regressions": 0,
                "tenant_isolation_passed": True,
                "masking_passed": True,
                "tool_policy_passed": True,
            },
        )

        with self.assertRaisesRegex(ValueError, "reduziu o número de acertos"):
            publish_model(
                organization=self.organization,
                version=candidate,
                evaluation=evaluation,
                actor=None,
            )

        active.refresh_from_db()
        candidate.refresh_from_db()
        self.assertTrue(active.is_active)
        self.assertFalse(candidate.is_active)

    @patch("apps.intelligence.gateway.urlopen")
    def test_claude_fallback_masks_payload_and_caches_only_the_stable_policy(
        self, mocked_urlopen
    ) -> None:
        mocked_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
            {
                "model": "claude-sonnet-4-5",
                "content": [{"type": "text", "text": "Resposta com fonte."}],
            }
        ).encode()

        completion = generate_claude_fallback_completion(
            api_key="test-local-key",
            model="claude-sonnet-4-5",
            question="Verifique CPF 123.456.789-09 e email pessoa@example.test; senha=nao-enviar",
            company_name="Empresa Protegida",
            conversation_context="Usuário informou 12.345.678/0001-99",
            evidence=[
                {
                    "label": "Espelho",
                    "reference": "Fonte pessoa@example.test",
                    "detail": "CPF 123.456.789-09",
                }
            ],
            allow_full_data=False,
        )

        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertEqual(completion.content, "Resposta com fonte.")
        self.assertEqual(payload["system"][0]["cache_control"], {"type": "ephemeral", "ttl": "5m"})
        self.assertEqual(
            json.loads(payload["messages"][0]["content"])["empresa"], "empresa selecionada"
        )
        self.assertNotIn("123.456.789-09", serialized)
        self.assertNotIn("pessoa@example.test", serialized)
        self.assertNotIn("nao-enviar", serialized)
        self.assertIn("[documento oculto]", serialized)
        self.assertIn("[segredo oculto]", serialized)

    @patch("apps.intelligence.gateway.urlopen")
    def test_sonnet_5_http_contract_is_validated_without_paid_api_call(
        self, mocked_urlopen
    ) -> None:
        mocked_urlopen.return_value.__enter__.return_value.headers = {
            "request-id": "req_12345678abc"
        }
        mocked_urlopen.return_value.__enter__.return_value.status = 200
        mocked_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
            {
                "model": "claude-sonnet-5",
                "content": [{"type": "text", "text": "Resposta fundamentada."}],
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 45,
                    "cache_creation_input_tokens": 20,
                    "cache_read_input_tokens": 10,
                },
            }
        ).encode()

        metadata = []
        completion = generate_claude_fallback_completion(
            api_key="only-a-mocked-test-key",
            model="claude-sonnet-5",
            question="O que mudou?",
            company_name="Empresa de teste",
            conversation_context="",
            evidence=[{"label": "Fonte", "reference": "ref", "detail": "dado"}],
            allow_full_data=False,
            on_response_metadata=lambda request_id, status: metadata.append((request_id, status)),
        )

        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
        self.assertEqual(payload["model"], "claude-sonnet-5")
        self.assertEqual(payload["max_tokens"], 900)
        self.assertEqual(payload["output_config"], {"effort": "low"})
        self.assertNotIn("temperature", payload)
        self.assertEqual(completion.content, "Resposta fundamentada.")
        self.assertEqual(completion.input_tokens, 120)
        self.assertEqual(completion.output_tokens, 45)
        self.assertEqual(completion.cache_creation_input_tokens, 20)
        self.assertEqual(completion.cache_read_input_tokens, 10)
        self.assertEqual(completion.request_id, "req_12345678abc")
        self.assertEqual(metadata, [("req_12345678abc", 200)])
        self.assertEqual(mocked_urlopen.call_count, 1)

    @patch("apps.intelligence.gateway.urlopen")
    def test_claude_http_error_keeps_request_id_for_support(self, mocked_urlopen) -> None:
        mocked_urlopen.side_effect = HTTPError(
            "https://api.anthropic.com/v1/messages",
            429,
            "rate limit",
            {"request-id": "req_12345678error"},
            None,
        )
        metadata = []
        completion = generate_claude_fallback_completion(
            api_key="only-a-mocked-test-key",
            model="claude-sonnet-5",
            question="Teste sem custo",
            company_name="Empresa de teste",
            conversation_context="",
            evidence=[],
            allow_full_data=False,
            on_response_metadata=lambda request_id, status: metadata.append((request_id, status)),
        )
        self.assertIsNone(completion)
        self.assertEqual(metadata, [("req_12345678error", 429)])
