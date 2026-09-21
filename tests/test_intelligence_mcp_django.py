from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.controlplane import generate_device_private_key, public_key_for_private
from apps.hub.models import (
    AccumulatorRule,
    ClientCompany,
    CompanyAccessGrant,
    ControlPlaneBinding,
    OfficeProfile,
    ProductModule,
)
from apps.intelligence.gateway import ClaudeCompletion
from apps.intelligence.mirror import sync_mirror_rows
from apps.intelligence.models import (
    AssistantSettings,
    ChatAttachment,
    ClaudeFallbackApproval,
    Conversation,
    DataCatalogEntry,
    DominioSchemaObject,
    EgressAudit,
    KnowledgeChunk,
    KnowledgeSource,
    Message,
    SemanticPackage,
)
from apps.intelligence.retrieval import refresh_knowledge_chunks
from apps.intelligence.services import answer_question, reconcile_stale_claude_attempts
from apps.knowledge.models import SharedKnowledgeSource
from apps.organizations.models import Membership, Organization
from apps.platform.billing import reserve_usage
from apps.platform.models import (
    Plan,
    PlanServiceRate,
    PlatformConfiguration,
    TenantContract,
    TokenActionWeight,
    TokenModuleRate,
    TokenPriceBook,
    TokenUsageEvent,
    UsageEvent,
)


class CentralDemoCopilotTests(TestCase):
    databases = {"default", "knowledge"}

    def test_demo_answers_from_fabricated_local_data_without_provider_or_usage(self) -> None:
        PlatformConfiguration.objects.update_or_create(
            key="default",
            defaults={"copilot_available_for_offices": False, "cloud_fallback_enabled": True},
        )
        user = User.objects.create_user("central-demo@example.test", "test-only-password")
        organization = Organization.objects.create(
            name="Escritório Demo Central", slug="central-demo-copilot", is_demo=True
        )
        Membership.objects.create(
            organization=organization, user=user, role=Membership.Role.OWNER
        )
        ProductModule.objects.create(
            organization=organization, code=ProductModule.Code.AI, enabled=True
        )
        with (
            patch("apps.intelligence.services.generate_local_completion") as local,
            patch("apps.intelligence.services.generate_claude_fallback_completion") as cloud,
        ):
            _, response, _ = answer_question(
                organization=organization,
                actor=user,
                question="Mostre as pendências fictícias",
                company=None,
                request=None,
            )
        local.assert_not_called()
        cloud.assert_not_called()
        self.assertTrue(response.content.startswith("Demonstração fictícia:"))
        self.assertEqual(response.model_version, "demo-simulado-v1")
        self.assertFalse(UsageEvent.objects.filter(organization=organization).exists())
        self.client.force_login(user)
        session = self.client.session
        session["hub_organization_id"] = str(organization.id)
        session.save()
        page = self.client.get(reverse("intelligence:assistant"))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Demonstração fictícia")

    def test_demo_rejects_real_uploaded_files_before_storing_them(self) -> None:
        user = User.objects.create_user("central-demo-upload@example.test", "test-only-password")
        organization = Organization.objects.create(
            name="Demo Upload", slug="central-demo-upload", is_demo=True
        )
        with self.assertRaisesRegex(ValueError, "não envie arquivos"):
            answer_question(
                organization=organization,
                actor=user,
                question="Analise este arquivo",
                company=None,
                request=None,
                uploads=[
                    SimpleUploadedFile("real.pdf", b"sensitive", content_type="application/pdf")
                ],
            )
        self.assertFalse(ChatAttachment.objects.filter(organization=organization).exists())


class ClaudeReservationTransactionTests(TransactionTestCase):
    databases = {"default", "knowledge"}

    @patch("apps.intelligence.services.generate_claude_fallback_completion")
    @patch("apps.intelligence.services.generate_local_completion", return_value=None)
    def test_reservation_is_committed_before_provider_call(self, _local, provider) -> None:
        PlatformConfiguration.objects.update_or_create(
            key="default",
            defaults={
                "copilot_available_for_offices": True,
                "cloud_fallback_enabled": True,
                "cloud_fallback_api_key": "test-key-only",
                "cloud_fallback_model": "claude-sonnet-4-5",
                "cloud_fallback_max_request_cents": 35,
                "cloud_fallback_daily_limit_cents": 100,
                "cloud_fallback_monthly_limit_cents": 1000,
            },
        )
        user = User.objects.create_user("reservation@example.test", "safe-password-123")
        organization = Organization.objects.create(
            name="Reservation office", slug="reservation-office"
        )
        Membership.objects.create(
            organization=organization, user=user, role=Membership.Role.OWNER
        )
        InternalMcpTests.enable_trial(organization)
        AssistantSettings.objects.create(
            organization=organization,
            claude_fallback_enabled=True,
            claude_allowed_roles=[Membership.Role.OWNER],
            claude_max_request_cents=35,
        )
        ClaudeFallbackApproval.objects.create(
            organization=organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=70,
            monthly_limit_cents=350,
        )

        def inspect_provider_boundary(**kwargs):
            self.assertFalse(connection.in_atomic_block)
            audit = EgressAudit.objects.get(organization=organization, allowed=True)
            self.assertEqual(audit.call_state, EgressAudit.CallState.RESERVED)
            self.assertIsNone(audit.completed_at)
            self.assertEqual(audit.user_message.role, Message.Role.USER)
            self.assertEqual(audit.usage_event.status, UsageEvent.Status.RESERVED)
            kwargs["on_response_metadata"]("req_12345678abc", 200)
            audit.refresh_from_db()
            self.assertEqual(audit.provider_request_id, "req_12345678abc")
            self.assertEqual(audit.provider_http_status, 200)
            self.assertEqual(
                Message.objects.filter(organization=organization, role=Message.Role.USER).count(),
                1,
            )
            EgressAudit.objects.filter(pk=audit.pk).update(
                created_at=timezone.now() - timedelta(minutes=11)
            )
            self.assertEqual(reconcile_stale_claude_attempts(), 1)
            audit.refresh_from_db()
            self.assertEqual(audit.call_state, EgressAudit.CallState.UNKNOWN)
            audit.usage_event.refresh_from_db()
            self.assertEqual(audit.usage_event.status, UsageEvent.Status.RESERVED)
            return ClaudeCompletion(
                "Resposta validada.", "claude-sonnet-4-5", request_id="req_12345678abc"
            )

        provider.side_effect = inspect_provider_boundary
        _, response, _ = answer_question(
            organization=organization,
            actor=user,
            question="Qual a pendência?",
            company=None,
            request=None,
        )
        self.assertEqual(response.content, "Resposta validada.")
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(
            EgressAudit.objects.get(organization=organization).call_state,
            EgressAudit.CallState.SUCCEEDED,
        )
        stranded_usage = reserve_usage(
            organization=organization,
            action_code="ai.answer",
            idempotency_key="stale-claude-test-only",
        )
        stranded = EgressAudit.objects.create(
            organization=organization,
            provider="anthropic",
            purpose="technical_fallback",
            payload_hash="a" * 64,
            actor=user,
            role=Membership.Role.OWNER,
            allowed=True,
            model="claude-sonnet-4-5",
            estimated_cost_cents=35,
            call_state=EgressAudit.CallState.RESERVED,
            user_message=Message.objects.get(organization=organization, role=Message.Role.USER),
            usage_event=stranded_usage,
        )
        EgressAudit.objects.filter(pk=stranded.pk).update(
            created_at=timezone.now() - timedelta(minutes=11)
        )
        self.assertEqual(reconcile_stale_claude_attempts(), 1)
        stranded.refresh_from_db()
        stranded_usage.refresh_from_db()
        self.assertEqual(stranded.call_state, EgressAudit.CallState.UNKNOWN)
        self.assertEqual(stranded_usage.status, UsageEvent.Status.RESERVED)
        self.assertEqual(reconcile_stale_claude_attempts(), 0)


class InternalMcpTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        PlatformConfiguration.objects.update_or_create(
            key="default", defaults={"copilot_available_for_offices": True}
        )
        self.user = User.objects.create_user("mcp@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        self.enable_trial(self.organization)
        self.client = Client()
        self.client.force_login(self.user)

    @staticmethod
    def enable_trial(organization):
        plan = Plan.objects.create(code=f"ai-{organization.pk}", name="AI test")
        PlanServiceRate.objects.create(plan=plan, action_code="ai.answer", included_units=100)
        OfficeProfile.objects.create(organization=organization, trial_started_at=timezone.now())
        ProductModule.objects.create(organization=organization, code="ai", enabled=True)
        TenantContract.objects.create(
            organization=organization,
            plan=plan,
            status="trial",
            starts_on=timezone.localdate(),
            trial_ends_on=timezone.localdate() + timedelta(days=14),
            selected_modules=["ai"],
        )

    @staticmethod
    def configure_local_runtime(
        *, endpoint: str = "http://private-model.test", model: str = "qwen-local", api_key: str = ""
    ) -> None:
        PlatformConfiguration.objects.filter(key="default").update(
            local_llm_endpoint=endpoint,
            local_llm_model=model,
            local_llm_api_key=api_key,
        )

    @staticmethod
    def configure_mewstack_cloud_fallback() -> None:
        PlatformConfiguration.objects.filter(key="default").update(
            cloud_fallback_enabled=True,
            cloud_fallback_api_key="mewstack-test-key",
            cloud_fallback_model="claude-sonnet-4-5",
            cloud_fallback_max_request_cents=35,
            cloud_fallback_daily_limit_cents=100,
            cloud_fallback_monthly_limit_cents=1_000,
        )

    @patch("apps.intelligence.services.generate_claude_fallback_completion")
    @patch("apps.intelligence.services.generate_local_completion", return_value=None)
    def test_active_ai_token_terms_meter_answer_and_link_claude_audit(
        self, _local, cloud
    ) -> None:
        self.configure_mewstack_cloud_fallback()
        AssistantSettings.objects.create(
            organization=self.organization,
            claude_fallback_enabled=True,
            claude_allowed_roles=[Membership.Role.OWNER],
            claude_max_request_cents=35,
        )
        ClaudeFallbackApproval.objects.create(
            organization=self.organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=100,
            monthly_limit_cents=1_000,
        )
        contract = TenantContract.objects.get(organization=self.organization)
        book = TokenPriceBook.objects.create(
            contract=contract,
            version=1,
            token_price_cents=5,
            monthly_overage_cap_cents=500,
            effective_from=timezone.localdate(),
            accepted_by=self.user,
            accepted_at=timezone.now(),
            activated_at=timezone.now(),
        )
        rate = TokenModuleRate.objects.create(
            book=book,
            module_code="ai",
            monthly_base_cents=14_900,
            included_tokens=100,
        )
        TokenActionWeight.objects.create(
            module_rate=rate,
            action_code="ai.answer",
            tokens=7,
        )
        book.status = TokenPriceBook.Status.ACTIVE
        book.save(update_fields=["status"])
        cloud.return_value = ClaudeCompletion(
            "Resposta Sonnet auditada.", "claude-sonnet-5", request_id="req-token-ai"
        )

        _, response, _ = answer_question(
            organization=self.organization,
            actor=self.user,
            question="Quais pendências exigem atenção?",
            company=None,
            request=None,
        )

        event = TokenUsageEvent.objects.get(organization=self.organization)
        audit = EgressAudit.objects.get(organization=self.organization)
        self.assertEqual(response.content, "Resposta Sonnet auditada.")
        self.assertEqual(event.module_code, "ai")
        self.assertEqual(event.action_code, "ai.answer")
        self.assertEqual(event.tokens, 7)
        self.assertEqual(event.status, TokenUsageEvent.Status.SETTLED)
        self.assertEqual(audit.token_usage_event, event)
        self.assertIsNone(audit.usage_event)
        self.assertFalse(UsageEvent.objects.filter(organization=self.organization).exists())

    @patch("apps.intelligence.services.generate_claude_fallback_completion")
    @patch("apps.intelligence.services.generate_local_completion", return_value=None)
    def test_claude_works_by_platform_api_key_before_local_pc_arrives(
        self, mocked_local, mocked_claude
    ) -> None:
        self.configure_mewstack_cloud_fallback()
        AssistantSettings.objects.create(
            organization=self.organization,
            claude_fallback_enabled=True,
            claude_allowed_roles=[Membership.Role.OWNER],
            claude_max_request_cents=35,
        )
        ClaudeFallbackApproval.objects.create(
            organization=self.organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=70,
            monthly_limit_cents=350,
        )
        mocked_claude.return_value = ClaudeCompletion(
            "Resposta com fonte.", "claude-sonnet-4-5",
            input_tokens=120, output_tokens=45, cache_read_input_tokens=10,
            request_id="req_12345678abc",
        )

        _, first, _ = answer_question(
            organization=self.organization, actor=self.user,
            question="Qual a pendência?", company=None, request=None,
        )
        self.assertEqual(first.content, "Resposta com fonte.")
        self.assertEqual(mocked_claude.call_args.kwargs["api_key"], "mewstack-test-key")
        self.assertTrue(mocked_local.called)

        answer_question(
            organization=self.organization, actor=self.user,
            question="E outra?", company=None, request=None,
        )
        self.assertEqual(mocked_claude.call_count, 2)
        answer_question(
            organization=self.organization, actor=self.user,
            question="Mais uma?", company=None, request=None,
        )
        self.assertEqual(mocked_claude.call_count, 2)
        self.assertEqual(
            EgressAudit.objects.filter(organization=self.organization, allowed=True).count(), 2
        )
        self.assertEqual(
            set(EgressAudit.objects.filter(organization=self.organization).values_list(
                "call_state", flat=True
            )),
            {EgressAudit.CallState.SUCCEEDED, EgressAudit.CallState.DENIED},
        )
        successful = EgressAudit.objects.filter(
            organization=self.organization, call_state=EgressAudit.CallState.SUCCEEDED
        ).first()
        self.assertEqual(successful.input_tokens, 120)
        self.assertEqual(successful.output_tokens, 45)
        self.assertEqual(successful.cache_read_input_tokens, 10)
        self.assertEqual(successful.provider_request_id, "req_12345678abc")

    @patch("apps.intelligence.services.generate_claude_fallback_completion", return_value=None)
    @patch("apps.intelligence.services.generate_local_completion", return_value=None)
    def test_uncertain_claude_response_keeps_conservative_budget_evidence(
        self, mocked_local, mocked_claude
    ) -> None:
        self.configure_mewstack_cloud_fallback()
        AssistantSettings.objects.create(
            organization=self.organization, claude_fallback_enabled=True,
            claude_allowed_roles=[Membership.Role.OWNER], claude_max_request_cents=35,
        )
        ClaudeFallbackApproval.objects.create(
            organization=self.organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=35, monthly_limit_cents=35,
        )
        answer_question(
            organization=self.organization, actor=self.user,
            question="Pergunta sem retorno", company=None, request=None,
        )
        self.assertTrue(mocked_local.called)
        self.assertEqual(mocked_claude.call_count, 1)
        audit = EgressAudit.objects.get(organization=self.organization)
        self.assertEqual(audit.call_state, EgressAudit.CallState.UNKNOWN)
        self.assertEqual(audit.estimated_cost_cents, 35)
        self.assertIsNotNone(audit.completed_at)
        answer_question(
            organization=self.organization, actor=self.user,
            question="Outra pergunta", company=None, request=None,
        )
        self.assertEqual(mocked_claude.call_count, 1)

    def post_rpc(self, method: str, params: dict[str, object] | None = None):
        return self.client.post(
            reverse("intelligence-mcp"),
            data=json.dumps(
                {"jsonrpc": "2.0", "id": "request-1", "method": method, "params": params or {}}
            ),
            content_type="application/json",
        )

    @staticmethod
    def approved_dependency(
        organization: Organization, *, object_name: str, columns: list[str]
    ) -> dict[str, object]:
        DominioSchemaObject.objects.create(
            organization=organization,
            schema_name="dbo",
            object_name=object_name,
            object_kind=DominioSchemaObject.ObjectKind.TABLE,
            columns=[
                {"name": column, "type": "varchar", "ordinal": index, "nullable": True}
                for index, column in enumerate(columns)
            ],
            structure_hash=(object_name * 64)[:64],
            sensitivity="restricted",
            approved_for_package=True,
        )
        return {
            "schema_name": "dbo",
            "object_name": object_name,
            "object_kind": "table",
            "columns": columns,
        }

    def test_initialize_and_tools_list_are_jsonrpc(self) -> None:
        initialized = self.post_rpc("initialize")
        listed = self.post_rpc("tools/list")

        self.assertEqual(initialized.status_code, 200)
        self.assertEqual(initialized.json()["result"]["protocolVersion"], "2025-06-18")
        tool_names = {tool["name"] for tool in listed.json()["result"]["tools"]}
        self.assertIn("get_risk_snapshot", tool_names)
        self.assertIn("create_classification_draft", tool_names)
        self.assertNotIn("run_sql", tool_names)

        rejected = self.post_rpc(
            "tools/call", {"name": "get_risk_snapshot", "arguments": {"sql": "SELECT *"}}
        )
        self.assertEqual(rejected.json()["error"]["code"], -32602)

    def test_mcp_audit_keeps_hashes_latency_and_failure_without_tool_content(self) -> None:
        DataCatalogEntry.objects.create(
            organization=self.organization,
            module="Fiscal",
            business_name="Obrigações",
            description="Dados aprovados para revisão.",
            sensitivity="restricted",
            source_reference="Manual interno 2026 § 2",
            enabled=True,
        )
        completed = self.post_rpc(
            "tools/call", {"name": "search_data_catalog", "arguments": {"query": "obrigações"}}
        )
        rejected = self.post_rpc("tools/call", {"name": "run_sql", "arguments": {}})
        events = list(
            AuditEvent.objects.filter(action="intelligence.mcp.tool_called").order_by("occurred_at")
        )

        self.assertEqual(completed.status_code, 200)
        self.assertEqual(rejected.json()["error"]["code"], -32602)
        self.assertEqual(len(events), 2)
        self.assertTrue(events[0].success)
        self.assertIn("result_hash", events[0].metadata)
        self.assertIn("source_hashes", events[0].metadata)
        self.assertIn("latency_ms", events[0].metadata)
        self.assertNotIn("Manual interno", json.dumps(events[0].metadata))
        self.assertFalse(events[1].success)
        self.assertEqual(events[1].metadata["failure_class"], "tool_validation")

    def test_company_scope_and_answer_evidence_cannot_cross_tenants(self) -> None:
        company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa Acme", dominio_code="001"
        )
        visible = self.post_rpc(
            "tools/call",
            {"name": "get_company_context", "arguments": {"company_id": str(company.id)}},
        )
        self.assertEqual(
            visible.json()["result"]["structuredContent"]["company"]["name"], "Empresa Acme"
        )

        other = Organization.objects.create(name="Globex", slug="globex")
        other_user = User.objects.create_user("other@example.test", "safe-password-123")
        Membership.objects.create(organization=other, user=other_user, role=Membership.Role.OWNER)
        self.enable_trial(other)
        _, other_answer, _ = answer_question(
            organization=other,
            actor=other_user,
            question="Segredo de outro escritório",
            company=None,
            request=None,
        )
        denied = self.post_rpc(
            "tools/call",
            {"name": "get_answer_evidence", "arguments": {"message_id": str(other_answer.id)}},
        )

        self.assertEqual(denied.json()["error"]["code"], -32602)
        self.assertEqual(Message.objects.filter(organization=self.organization).count(), 0)

    def test_mcp_creates_only_a_confirmed_draft_and_returns_scoped_evidence(self) -> None:
        company = ClientCompany.objects.create(
            organization=self.organization, name="Classificação", dominio_code="draft"
        )
        AccumulatorRule.objects.create(
            organization=self.organization,
            company=company,
            name="Regra fiscal aprovada",
            priority=1,
            accumulator_code="AC-100",
        )
        conversation = Conversation.objects.create(organization=self.organization, company=company)
        answer = Message.objects.create(
            organization=self.organization,
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Resposta com fonte.",
            evidence=[{"label": "Regra", "reference": "Manual", "detail": "Aprovada"}],
        )

        explanation = self.post_rpc(
            "tools/call",
            {"name": "explain_classification", "arguments": {"company_id": str(company.id)}},
        )
        unconfirmed = self.post_rpc(
            "tools/call",
            {
                "name": "create_classification_draft",
                "arguments": {
                    "company_id": str(company.id),
                    "conversation_id": str(conversation.id),
                    "confirmed_by_user": False,
                },
            },
        )
        created = self.post_rpc(
            "tools/call",
            {
                "name": "create_classification_draft",
                "arguments": {
                    "company_id": str(company.id),
                    "conversation_id": str(conversation.id),
                    "confirmed_by_user": True,
                },
            },
        )
        evidence = self.post_rpc(
            "tools/call",
            {"name": "get_answer_evidence", "arguments": {"message_id": str(answer.id)}},
        )

        self.assertEqual(
            explanation.json()["result"]["structuredContent"]["suggested_code"], "AC-100"
        )
        self.assertEqual(unconfirmed.json()["error"]["code"], -32602)
        self.assertEqual(created.json()["result"]["structuredContent"]["suggested_code"], "AC-100")
        self.assertEqual(
            evidence.json()["result"]["structuredContent"]["message_id"], str(answer.id)
        )

    def test_managed_mcp_requires_draft_capability_for_a_classification_draft(self) -> None:
        company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa restrita", dominio_code="draft"
        )
        AccumulatorRule.objects.create(
            organization=self.organization,
            company=company,
            name="Regra fiscal aprovada",
            priority=1,
            accumulator_code="AC-200",
        )
        conversation = Conversation.objects.create(organization=self.organization, company=company)
        membership = Membership.objects.get(organization=self.organization, user=self.user)
        private_key = generate_device_private_key()
        ControlPlaneBinding.objects.create(
            organization=self.organization,
            remote_installation_id="5fb9d795-7bf0-4a73-95cd-a4fc288a8f61",
            controller_url="https://crmew.example.test",
            device_private_key=private_key,
            controller_public_key=public_key_for_private(private_key),
            cache_expires_at=timezone.now() + timedelta(minutes=10),
        )
        CompanyAccessGrant.objects.create(
            organization=self.organization,
            membership=membership,
            company=company,
            modules=["guides"],
            capabilities=["read"],
        )

        blocked = self.post_rpc(
            "tools/call",
            {
                "name": "create_classification_draft",
                "arguments": {
                    "company_id": str(company.id),
                    "conversation_id": str(conversation.id),
                    "confirmed_by_user": True,
                },
            },
        )

        self.assertEqual(blocked.json()["error"]["code"], -32602)
        self.assertIn("capacidade", blocked.json()["error"]["message"])

    def test_crmew_grant_blocks_an_unassigned_company(self) -> None:
        allowed = ClientCompany.objects.create(
            organization=self.organization, name="Permitida", dominio_code="001"
        )
        blocked = ClientCompany.objects.create(
            organization=self.organization, name="Bloqueada", dominio_code="002"
        )
        membership = Membership.objects.get(organization=self.organization, user=self.user)
        private_key = generate_device_private_key()
        binding = ControlPlaneBinding.objects.create(
            organization=self.organization,
            remote_installation_id="493c7a48-8ac1-4d51-8d64-3c741c12f2fd",
            controller_url="https://crmew.example.test",
            device_private_key=private_key,
            controller_public_key=public_key_for_private(private_key),
            cache_expires_at=timezone.now() + timedelta(minutes=10),
        )
        CompanyAccessGrant.objects.create(
            organization=self.organization,
            membership=membership,
            company=allowed,
            modules=["nfse"],
            capabilities=["intelligence:use"],
        )

        visible = self.post_rpc(
            "tools/call",
            {"name": "get_company_context", "arguments": {"company_id": str(allowed.id)}},
        )
        denied = self.post_rpc(
            "tools/call",
            {"name": "get_company_context", "arguments": {"company_id": str(blocked.id)}},
        )

        self.assertEqual(visible.status_code, 200)
        self.assertEqual(denied.json()["error"]["code"], -32602)
        self.assertEqual(binding.organization_id, self.organization.id)

    def test_text_attachment_is_encrypted_and_becomes_answer_evidence(self) -> None:
        company = ClientCompany.objects.create(
            organization=self.organization, name="Com anexo", dominio_code="003"
        )
        _, response, _ = answer_question(
            organization=self.organization,
            actor=self.user,
            question="Analise o anexo.",
            company=company,
            request=None,
            uploads=[
                SimpleUploadedFile(
                    "pendencias.txt", b"DARF vence em 20/09", content_type="text/plain"
                )
            ],
        )
        attachment = ChatAttachment.objects.get(conversation=response.conversation)

        self.assertEqual(attachment.status, ChatAttachment.Status.ANALYZED)
        self.assertNotEqual(attachment.encrypted_content_b64, "REFSRiB2ZW5jZSBtIDIwLzA5")
        self.assertTrue(any(item["label"] == "Anexo analisado" for item in response.evidence))

    @patch("apps.intelligence.gateway.urlopen")
    def test_local_model_receives_only_compact_evidence_cards(self, mocked_urlopen) -> None:
        self.configure_local_runtime(api_key="local-only-token")
        self.configure_mewstack_cloud_fallback()
        AssistantSettings.objects.create(
            organization=self.organization,
            claude_fallback_enabled=True,
            claude_allowed_roles=[Membership.Role.OWNER],
            claude_max_request_cents=35,
        )
        ClaudeFallbackApproval.objects.create(
            organization=self.organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=100,
            monthly_limit_cents=1_000,
        )
        company = ClientCompany.objects.create(
            organization=self.organization, name="Modelo local", dominio_code="004"
        )
        mocked_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
            {
                "model": "qwen-local-v2",
                "choices": [{"message": {"content": "Resposta baseada nas fontes."}}],
            }
        ).encode()

        with patch("apps.intelligence.services.generate_claude_fallback_completion") as cloud:
            _, response, _ = answer_question(
                organization=self.organization,
                actor=self.user,
                question="Quais riscos existem?",
                company=company,
                request=None,
            )

        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "http://private-model.test/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer local-only-token")
        self.assertEqual(payload["model"], "qwen-local")
        self.assertNotIn("sql", payload["messages"][1]["content"].casefold())
        self.assertEqual(response.content, "Resposta baseada nas fontes.")
        self.assertEqual(response.model_version, "qwen-local-v2")
        cloud.assert_not_called()
        self.assertFalse(EgressAudit.objects.filter(organization=self.organization).exists())

    def test_approved_sources_are_refreshed_as_bounded_rag_chunks(self) -> None:
        source = KnowledgeSource.objects.create(
            organization=self.organization,
            kind=KnowledgeSource.Kind.PROCEDURE,
            title="Fechamento previdenciário",
            version="2026-09",
            source_reference="Procedimento aprovado 4.2",
            content="INSS deve ser conferido antes do fechamento. " * 80,
            content_hash="a" * 64,
            status=KnowledgeSource.Status.APPROVED,
        )

        refresh = refresh_knowledge_chunks(organization=self.organization)
        _, response, _ = answer_question(
            organization=self.organization,
            actor=self.user,
            question="INSS",
            company=None,
            request=None,
        )

        self.assertGreater(refresh.created, 0)
        self.assertTrue(KnowledgeChunk.objects.filter(source=source).exists())
        evidence = next(
            item for item in response.evidence if item["reference"] == source.source_reference
        )
        self.assertLessEqual(len(evidence["detail"]), 281)

    def test_obligations_come_from_fresh_private_mirror_as_reviewed_cards(self) -> None:
        company = ClientCompany.objects.create(
            organization=self.organization, name="Espelho fiscal", dominio_code="005"
        )
        dependency = self.approved_dependency(
            self.organization,
            object_name="obligations_source",
            columns=["company_code", "obligation_id", "description", "due_date", "status"],
        )
        package = SemanticPackage.objects.create(
            organization=self.organization,
            module="Fiscal",
            tool_name="list_obligations",
            query_name="obligations_snapshot",
            source_reference="Domínio Fiscal · obrigações",
            data_classification="restricted",
            company_key="company_code",
            primary_key="obligation_id",
            update_strategy=SemanticPackage.UpdateStrategy.SNAPSHOT_HASH,
            max_rows=20,
            max_period_days=90,
            max_staleness_seconds=3600,
            schema_dependencies=[dependency],
            test_specification={"card_fields": ["description", "due_date", "status"]},
            enabled=True,
        )
        sync_mirror_rows(
            organization=self.organization,
            package=package,
            rows=[
                {
                    "obligation_id": "ob-42",
                    "company_code": "005",
                    "description": "DCTFWeb setembro",
                    "due_date": "2026-09-20",
                    "status": "pending",
                    "cpf": "000.000.000-00",
                }
            ],
        )

        response = self.post_rpc(
            "tools/call",
            {
                "name": "list_obligations",
                "arguments": {"company_id": str(company.id), "period_days": 31},
            },
        )

        result = response.json()["result"]["structuredContent"]
        self.assertEqual(result["freshness"], "fresh")
        self.assertEqual(len(result["evidence"]), 1)
        self.assertIn("DCTFWeb setembro", result["evidence"][0]["detail"])
        self.assertNotIn("000.000.000-00", result["evidence"][0]["detail"])

    def test_stale_mirror_never_falls_through_to_live_database(self) -> None:
        company = ClientCompany.objects.create(
            organization=self.organization, name="Espelho vencido", dominio_code="006"
        )
        dependency = self.approved_dependency(
            self.organization,
            object_name="stale_source",
            columns=["company_code", "obligation_id", "description"],
        )
        package = SemanticPackage.objects.create(
            organization=self.organization,
            module="Fiscal",
            tool_name="list_obligations",
            query_name="stale_snapshot",
            source_reference="Domínio Fiscal · obrigações",
            data_classification="restricted",
            company_key="company_code",
            primary_key="obligation_id",
            update_strategy=SemanticPackage.UpdateStrategy.SNAPSHOT_HASH,
            max_rows=20,
            max_staleness_seconds=1,
            schema_dependencies=[dependency],
            test_specification={"card_fields": ["description"]},
            enabled=True,
        )
        sync_mirror_rows(
            organization=self.organization,
            package=package,
            rows=[{"obligation_id": "old", "company_code": "006", "description": "Não expor"}],
        )
        package.last_synced_at = timezone.now() - timedelta(seconds=2)
        package.save(update_fields=["last_synced_at"])

        response = self.post_rpc(
            "tools/call", {"name": "list_obligations", "arguments": {"company_id": str(company.id)}}
        )

        result = response.json()["result"]["structuredContent"]
        self.assertEqual(result["freshness"], "stale")
        self.assertEqual(result["evidence"], [])

    def test_mirror_sync_rejects_package_from_another_office(self) -> None:
        other = Organization.objects.create(name="Outro", slug="outro")
        dependency = self.approved_dependency(
            other,
            object_name="other_source",
            columns=["company_code", "obligation_id"],
        )
        package = SemanticPackage.objects.create(
            organization=other,
            module="Fiscal",
            tool_name="list_obligations",
            query_name="other_snapshot",
            source_reference="Teste",
            data_classification="restricted",
            company_key="company_code",
            primary_key="obligation_id",
            update_strategy=SemanticPackage.UpdateStrategy.SNAPSHOT_HASH,
            max_rows=20,
            schema_dependencies=[dependency],
            enabled=True,
        )

        with self.assertRaisesMessage(ValueError, "fora do escritório"):
            sync_mirror_rows(
                organization=self.organization,
                package=package,
                rows=[{"obligation_id": "attempt", "company_code": "001"}],
            )

    def test_shared_knowledge_uses_the_separate_database_without_tenant_data(self) -> None:
        source = SharedKnowledgeSource.objects.using("knowledge").create(
            kind=SharedKnowledgeSource.Kind.REGULATION,
            title="Regra geral DCTFWeb",
            version="2026.09",
            source_reference="Norma geral 2026",
            content="A DCTFWeb deve ser revisada antes do vencimento.",
            content_hash="b" * 64,
            status=SharedKnowledgeSource.Status.APPROVED,
        )
        from apps.intelligence.retrieval import refresh_shared_knowledge_chunks

        refresh_shared_knowledge_chunks()
        _, response, _ = answer_question(
            organization=self.organization,
            actor=self.user,
            question="Como revisar a DCTFWeb?",
            company=None,
            request=None,
        )

        self.assertEqual(source._state.db, "knowledge")
        self.assertNotIn(
            "organization", {field.name for field in SharedKnowledgeSource._meta.fields}
        )
        self.assertTrue(any(item["reference"] == "Norma geral 2026" for item in response.evidence))

    def test_chat_continues_only_the_selected_company_conversation(self) -> None:
        company = ClientCompany.objects.create(
            organization=self.organization, name="Conversa contínua", dominio_code="007"
        )
        first = self.client.post(
            "/app/ia/", {"question": "Quais riscos existem?", "company_id": str(company.id)}
        )
        conversation = Conversation.objects.get(organization=self.organization)
        second = self.client.post(
            "/app/ia/",
            {
                "question": "E o que devo priorizar?",
                "company_id": str(company.id),
                "conversation_id": str(conversation.id),
            },
        )

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertIn(f"conversation={conversation.id}", second["Location"])
        self.assertEqual(Message.objects.filter(conversation=conversation).count(), 4)
        conversation.refresh_from_db()
        self.assertIn("priorizar", conversation.summary.casefold())

    @patch("apps.intelligence.services.generate_claude_fallback_completion")
    @patch("apps.intelligence.services.generate_local_completion", return_value=None)
    def test_claude_is_used_only_after_local_failure_and_audited(
        self, mocked_local, mocked_claude
    ) -> None:
        self.configure_local_runtime()
        self.configure_mewstack_cloud_fallback()
        AssistantSettings.objects.create(
            organization=self.organization,
            claude_fallback_enabled=True,
            claude_allowed_roles=[Membership.Role.OWNER],
            claude_max_request_cents=35,
        )
        ClaudeFallbackApproval.objects.create(
            organization=self.organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=100,
            monthly_limit_cents=1_000,
        )
        mocked_claude.return_value = ClaudeCompletion("Resposta de fallback.", "claude-sonnet-4-5")

        _, response, _ = answer_question(
            organization=self.organization,
            actor=self.user,
            question="Quais riscos existem?",
            company=None,
            request=None,
        )

        self.assertEqual(response.content, "Resposta de fallback.")
        self.assertEqual(response.model_version, "claude-sonnet-4-5")
        self.assertTrue(mocked_local.called)
        self.assertTrue(mocked_claude.called)
        self.assertEqual(mocked_claude.call_args.kwargs["api_key"], "mewstack-test-key")
        self.assertFalse(mocked_claude.call_args.kwargs["allow_full_data"])
        audit = EgressAudit.objects.get(organization=self.organization)
        self.assertTrue(audit.allowed)
        self.assertEqual(audit.estimated_cost_cents, 35)
        self.assertEqual(audit.call_state, EgressAudit.CallState.SUCCEEDED)

    @patch("apps.intelligence.services.generate_claude_fallback_completion")
    @patch("apps.intelligence.services.generate_local_completion", return_value=None)
    def test_claude_egress_is_audited_and_blocked_without_office_opt_in(
        self, mocked_local, mocked_claude
    ) -> None:
        self.configure_local_runtime()
        self.configure_mewstack_cloud_fallback()
        AssistantSettings.objects.create(
            organization=self.organization,
            claude_fallback_enabled=False,
            claude_allowed_roles=[Membership.Role.OWNER],
            claude_api_key="office-owned-test-key",
            claude_model="claude-sonnet-4-5",
            claude_max_request_cents=35,
        )
        ClaudeFallbackApproval.objects.create(
            organization=self.organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=100,
            monthly_limit_cents=1_000,
        )

        _, response, _ = answer_question(
            organization=self.organization,
            actor=self.user,
            question="Quais riscos existem?",
            company=None,
            request=None,
        )

        self.assertTrue(mocked_local.called)
        mocked_claude.assert_not_called()
        self.assertNotEqual(response.model_version, "claude-sonnet-4-5")
        audit = EgressAudit.objects.get(organization=self.organization)
        self.assertFalse(audit.allowed)
        self.assertEqual(audit.call_state, EgressAudit.CallState.DENIED)
        self.assertEqual(audit.payload_hash, audit.payload_hash.lower())
        self.assertEqual(len(audit.payload_hash), 64)
