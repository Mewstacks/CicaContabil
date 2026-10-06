from __future__ import annotations

from datetime import date, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.commercial_capacity import calculate_commercial_capacity, refresh_configured_capacity
from apps.hub.controlplane import (
    company_has_capability,
    company_queryset_for_membership,
    membership_has_capability,
)
from apps.hub.models import (
    ActivityTemplate,
    ActivityTemplateAssignment,
    ClientCompany,
    CompanyAccessGrant,
    DataSource,
    OperationalActivity,
    OperationalActivityEvent,
    OperationalEvidence,
    OperationalSourceObservation,
    UsageAllowance,
)
from apps.hub.operations import (
    add_human_evidence,
    assess_closing,
    assign_activity,
    block_activity,
    complete_activity,
    generate_monthly_activities,
    record_source_observation,
)
from apps.organizations.models import Membership, Organization


class OperationalCenterTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user("owner@example.test", "safe-password-123")
        self.operator = User.objects.create_user("operator@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        self.owner_membership = Membership.objects.create(
            organization=self.organization, user=self.owner, role=Membership.Role.OWNER
        )
        self.operator_membership = Membership.objects.create(
            organization=self.organization, user=self.operator, role=Membership.Role.OPERATOR
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa A"
        )
        self.other_company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa B"
        )
        CompanyAccessGrant.objects.create(
            organization=self.organization,
            membership=self.operator_membership,
            company=self.company,
            capabilities=["*"],
        )
        self.activity = OperationalActivity.objects.create(
            organization=self.organization,
            company=self.company,
            code="folha-fechamento",
            title="Conferir fechamento da folha",
            area="payroll",
            competence=date(2026, 9, 1),
            internal_due_on=timezone.localdate() - timedelta(days=1),
            evidence_requirement="human",
            assigned_to=self.operator,
        )

    def _login(self, user: User) -> None:
        self.client.force_login(user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

    def test_operator_sees_only_companies_in_own_scope(self) -> None:
        restricted = OperationalActivity.objects.create(
            organization=self.organization,
            company=self.other_company,
            code="fiscal-fechamento",
            title="Fechamento fiscal",
            area="fiscal",
            competence=date(2026, 9, 1),
        )
        self._login(self.operator)

        response = self.client.get(reverse("hub:activities"))

        self.assertContains(response, self.activity.title)
        self.assertNotContains(response, restricted.title)
        self.assertEqual(
            self.client.get(reverse("hub:activity-detail", args=[restricted.id])).status_code, 404
        )

    def test_activity_queue_defaults_to_open_work_and_invalid_filters_never_expand(self) -> None:
        completed = OperationalActivity.objects.create(
            organization=self.organization,
            company=self.company,
            code="completed-work",
            title="Atividade concluída antiga",
            area="fiscal",
            assigned_to=self.operator,
            work_status=OperationalActivity.WorkStatus.COMPLETED,
        )
        self._login(self.operator)
        url = reverse("hub:activities")

        default = self.client.get(url)
        all_states = self.client.get(url, {"status": "all"})
        invalid = self.client.get(url, {"status": "unknown"})
        invalid_competence = self.client.get(url, {"competence": "2030-13"})
        conflicting_due = self.client.get(url, {"due": "today", "overdue": "1"})

        self.assertContains(default, self.activity.title)
        self.assertNotContains(default, completed.title)
        self.assertContains(all_states, completed.title)
        self.assertContains(all_states, "Situação: Todas, inclusive encerradas")
        self.assertEqual(invalid.context["activities_page"].paginator.count, 0)
        self.assertContains(invalid, "A situação informada não existe")
        self.assertContains(invalid, "Nenhuma atividade corresponde a este recorte")
        self.assertEqual(invalid_competence.context["activities_page"].paginator.count, 0)
        self.assertContains(
            invalid_competence, "Informe uma competência válida no formato mês/ano."
        )
        self.assertEqual(conflicting_due.context["activities_page"].paginator.count, 0)
        self.assertContains(conflicting_due, "Escolha apenas um recorte de prazo por vez")

    def test_activity_queue_exposes_priority_context_and_one_filter_form(self) -> None:
        self.activity.blocked_reason = "Aguardando confirmação do cliente."
        self.activity.work_status = OperationalActivity.WorkStatus.BLOCKED
        self.activity.save(update_fields=["blocked_reason", "work_status", "updated_at"])
        self._login(self.owner)

        response = self.client.get(
            reverse("hub:activities"),
            {
                "status": "blocked",
                "area": "payroll",
                "company": self.company.id,
                "assignee": self.operator.id,
            },
        )

        self.assertContains(response, "Prioridades das atividades", html=False)
        self.assertContains(response, "Impedidas")
        self.assertContains(response, "Filtros ativos")
        self.assertContains(response, "Área: Folha")
        self.assertContains(response, f"Empresa: {self.company.name}")
        self.assertContains(response, "Responsável: operator@example.test")
        self.assertContains(response, "Aguardando confirmação do cliente.")
        self.assertContains(response, "1 dia em atraso")
        self.assertContains(response, 'aria-label="Filtrar atividades"')
        self.assertNotContains(response, 'aria-label="Filtrar responsáveis"')
        self.assertContains(response, "Conferir fechamento da folha")

    def test_activity_queue_pagination_preserves_the_active_scope(self) -> None:
        for index in range(31):
            OperationalActivity.objects.create(
                organization=self.organization,
                company=self.company,
                code=f"payroll-page-{index}",
                title=f"Conferência de folha {index}",
                area="payroll",
                assigned_to=self.operator,
                internal_due_on=timezone.localdate() + timedelta(days=index + 1),
            )
        self._login(self.operator)

        response = self.client.get(
            reverse("hub:activities"),
            {"area": "payroll", "status": "pending"},
        )

        self.assertEqual(response.context["activities_page"].paginator.count, 32)
        self.assertContains(response, "Página 1 de 2")
        self.assertContains(response, "?area=payroll&amp;status=pending&amp;page=2")

    def test_readonly_profiles_cannot_mutate_activities_through_direct_posts(self) -> None:
        for role in (Membership.Role.AUDITOR, Membership.Role.BILLING):
            with self.subTest(role=role):
                self.operator_membership.role = role
                self.operator_membership.save()
                self._login(self.operator)
                detail = self.client.get(reverse("hub:activity-detail", args=[self.activity.pk]))
                self.assertEqual(detail.status_code, 200)
                self.assertFalse(detail.context["can_manage_activity"])
                self.client.post(
                    reverse("hub:activity-add-evidence", args=[self.activity.pk]),
                    {
                        "summary": "Alteração proibida",
                        "reference": "test",
                    },
                )
                self.client.post(
                    reverse("hub:activity-block", args=[self.activity.pk]),
                    {
                        "reason": "Impedimento proibido",
                    },
                )
                self.client.post(reverse("hub:activity-complete", args=[self.activity.pk]))
                self.activity.refresh_from_db()
                self.assertEqual(self.activity.work_status, "pending")
                self.assertEqual(self.activity.events.count(), 0)
                self.assertEqual(self.activity.evidence_items.count(), 0)

    def test_activity_detail_leads_with_next_step_and_only_offers_valid_completion(self) -> None:
        self._login(self.operator)
        url = reverse("hub:activity-detail", args=[self.activity.pk])

        pending = self.client.get(url)

        self.assertContains(pending, "Cumpra a condição para concluir")
        self.assertContains(pending, "confirmação humana registrada")
        self.assertNotContains(pending, "Revisar conclusão")
        self.client.post(
            reverse("hub:activity-add-evidence", args=[self.activity.pk]),
            {"reference": "REC-2026-09", "summary": "Fechamento conferido."},
        )

        ready = self.client.get(url)

        self.assertContains(ready, "Revise e conclua a atividade")
        self.assertContains(ready, "Revisar conclusão")
        self.assertContains(ready, "Confirmar conclusão")
        self.assertContains(ready, "REC-2026-09")
        self.assertNotContains(ready, "evidence_recorded")

    def test_invalid_activity_forms_preserve_input_and_focusable_error_context(self) -> None:
        self._login(self.operator)

        evidence = self.client.post(
            reverse("hub:activity-add-evidence", args=[self.activity.pk]),
            {"reference": "REC-PRESERVADO", "summary": ""},
        )
        blocked = self.client.post(
            reverse("hub:activity-block", args=[self.activity.pk]),
            {"reason": ""},
        )

        self.assertEqual(evidence.status_code, 400)
        self.assertContains(evidence, "REC-PRESERVADO", status_code=400)
        self.assertContains(evidence, "data-activity-errors", status_code=400)
        self.assertContains(evidence, "activity-action-disclosure\" open", status_code=400)
        self.assertEqual(blocked.status_code, 400)
        self.assertContains(blocked, "Descreva o impedimento", status_code=400)
        self.assertContains(blocked, "data-activity-errors", status_code=400)

    def test_blocked_activity_makes_resolution_explicit_before_completion(self) -> None:
        OperationalEvidence.objects.create(
            organization=self.organization,
            activity=self.activity,
            kind=OperationalActivity.EvidenceKind.HUMAN,
            summary="Fechamento conferido.",
            recorded_by=self.operator,
        )
        self.activity.work_status = OperationalActivity.WorkStatus.BLOCKED
        self.activity.blocked_reason = "Aguardando documento do cliente."
        self.activity.save(update_fields=["work_status", "blocked_reason", "updated_at"])
        self._login(self.operator)

        detail = self.client.get(reverse("hub:activity-detail", args=[self.activity.pk]))

        self.assertContains(detail, "Resolva o impedimento registrado")
        self.assertContains(detail, "Revisar resolução e conclusão")
        self.assertContains(detail, "Resolver o impedimento e concluir?")
        complete_activity(
            activity=self.activity,
            membership=self.operator_membership,
            actor=self.operator,
            request=RequestFactory().post("/"),
        )
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.work_status, OperationalActivity.WorkStatus.COMPLETED)
        self.assertEqual(self.activity.blocked_reason, "")

    def test_activity_writes_revalidate_live_membership_and_actor(self) -> None:
        request = RequestFactory().post("/")
        outsider = User.objects.create_user("outsider@example.test", "safe-password-123")
        self.operator_membership.role = Membership.Role.BILLING
        self.operator_membership.save(update_fields=["role", "updated_at"])

        for operation in (
            lambda: add_human_evidence(
                activity=self.activity,
                membership=self.operator_membership,
                actor=self.operator,
                request=request,
                reference="blocked",
                summary="Nao deve ser gravada.",
            ),
            lambda: block_activity(
                activity=self.activity,
                membership=self.operator_membership,
                actor=self.operator,
                request=request,
                reason="Nao deve ser gravado.",
            ),
            lambda: complete_activity(
                activity=self.activity,
                membership=self.operator_membership,
                actor=self.operator,
                request=request,
            ),
            lambda: add_human_evidence(
                activity=self.activity,
                membership=self.operator_membership,
                actor=outsider,
                request=request,
                reference="actor-mismatch",
                summary="Nao deve ser gravada.",
            ),
        ):
            with self.subTest(operation=operation), self.assertRaises(PermissionDenied):
                operation()

        self.activity.refresh_from_db()
        self.assertEqual(self.activity.work_status, OperationalActivity.WorkStatus.PENDING)
        self.assertEqual(self.activity.events.count(), 0)
        self.assertEqual(self.activity.evidence_items.count(), 0)
    def test_assignment_revalidates_the_current_administrator_role(self) -> None:
        CompanyAccessGrant.objects.create(
            organization=self.organization,
            membership=self.owner_membership,
            company=self.company,
            capabilities=["*"],
        )
        Membership.objects.filter(pk=self.owner_membership.pk).update(role=Membership.Role.OPERATOR)

        with self.assertRaises(PermissionDenied):
            assign_activity(
                activity=self.activity,
                membership=self.owner_membership,
                actor=self.owner,
                assignee_id="",
                expected_assignee_id=str(self.operator.pk),
                reason="Nao pode redistribuir apos perder administracao.",
                request=RequestFactory().post("/"),
            )

        self.activity.refresh_from_db()
        self.assertEqual(self.activity.assigned_to, self.operator)
        self.assertFalse(self.activity.events.filter(event_type="assigned").exists())
    def test_assignment_moves_work_into_personal_agenda_and_detects_stale_submit(self) -> None:
        self.activity.assigned_to = None
        self.activity.requires_processing_closed = True
        self.activity.competence = timezone.localdate().replace(day=1)
        self.activity.save()
        self._login(self.owner)
        url = reverse("hub:activity-detail", args=[self.activity.pk])
        payload = {
            "action": "assign",
            "assignment-assignee": str(self.operator.pk),
            "assignment-expected_assignee": "",
            "assignment-reason": "Distribuição da carteira",
        }
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.assigned_to, self.operator)
        self.assertEqual(self.activity.events.filter(event_type="assigned").count(), 1)
        summary = self.activity.events.get(event_type="assigned").summary
        self.assertIn(self.operator.display_name, summary)
        self.assertNotIn(str(self.operator.pk), summary)
        stale = self.client.post(url, {**payload, "assignment-assignee": str(self.owner.pk)})
        self.assertEqual(stale.status_code, 400)
        self.assertContains(stale, "responsável mudou", status_code=400)
        self._login(self.operator)
        self.assertContains(self.client.get(reverse("hub:dashboard")), self.activity.title)
        self.assertEqual(self.client.post(url, payload).status_code, 403)
        self._login(self.owner)
        removed = self.client.post(
            url,
            {
                **payload,
                "assignment-assignee": "",
                "assignment-expected_assignee": str(self.operator.pk),
                "assignment-reason": "Retorno à carteira compartilhada",
            },
        )
        self.assertEqual(removed.status_code, 302)
        self._login(self.operator)
        self.assertEqual(
            len(self.client.get(reverse("hub:dashboard")).context["dashboard_activities"]), 0
        )
        self.assertEqual(self.activity.events.filter(event_type="assigned").count(), 2)

    def test_legacy_assignment_history_shows_names_instead_of_identifiers(self) -> None:
        OperationalActivityEvent.objects.create(
            organization=self.activity.organization,
            activity=self.activity,
            event_type="assigned",
            summary=f"Responsável: sem responsável → {self.operator.pk}. Motivo: carteira",
            actor=self.owner,
        )
        self._login(self.owner)

        response = self.client.get(reverse("hub:activity-detail", args=[self.activity.pk]))

        self.assertContains(response, f"sem responsável → {self.operator.display_name}")
        self.assertNotContains(response, str(self.operator.pk) + ".")

    def test_assignment_rejects_revoked_access_and_retains_validation_input(self) -> None:
        self._login(self.owner)
        CompanyAccessGrant.objects.filter(membership=self.operator_membership).update(
            is_active=False
        )
        url = reverse("hub:activity-detail", args=[self.activity.pk])
        response = self.client.post(
            url,
            {
                "action": "assign",
                "assignment-assignee": str(self.operator.pk),
                "assignment-expected_assignee": str(self.operator.pk),
                "assignment-reason": "Motivo preservado",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Motivo preservado", status_code=400)
        self.assertContains(response, "data-form-errors", status_code=400)
        self.assertEqual(self.activity.events.count(), 0)
        self.assertFalse(
            CompanyAccessGrant.objects.filter(
                membership=self.operator_membership, is_active=True
            ).exists()
        )
        self.activity.work_status = "completed"
        self.activity.save()
        self.assertEqual(self.client.post(url, {"action": "assign"}).status_code, 403)

    def test_dashboard_closing_includes_shared_work_without_crossing_portfolio(self) -> None:
        self.activity.requires_processing_closed = True
        self.activity.assigned_to = self.owner
        self.activity.blocked_reason = "Aguardando documentos da folha"
        self.activity.work_status = OperationalActivity.WorkStatus.BLOCKED
        self.activity.save()
        OperationalActivity.objects.create(
            organization=self.organization,
            company=self.other_company,
            code="restricted",
            title="Fechamento restrito",
            area="payroll",
            competence=date(2026, 9, 1),
            requires_processing_closed=True,
        )
        self._login(self.operator)
        response = self.client.get(reverse("hub:dashboard"), {"closing_month": "2026-09"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["closing_rows"]), 3)
        self.assertContains(response, "Aguardando documentos da folha")
        self.assertContains(response, "Impedido")
        self.assertEqual(response.context["closing_status_counts"]["attention"], 1)
        self.assertEqual(
            response.context["closing_attention_rows"][0]["next_step"],
            "Resolva o impedimento registrado para o fechamento avançar.",
        )
        self.assertContains(response, "Comece pelos fechamentos que exigem decisão")
        self.assertContains(response, "Conferir atividade")
        self.assertNotContains(response, "Fechamento restrito")
        self.assertEqual(len(response.context["dashboard_activities"]), 0)
        self.assertContains(response, "Cobertura a configurar")
        self.assertContains(response, "2 combinações de empresa e área")

    def test_dashboard_closing_separates_payment_and_competence(self) -> None:
        self.activity.requires_processing_closed = True
        self.activity.processing_status = OperationalActivity.ProcessingStatus.CLOSED
        self.activity.work_status = OperationalActivity.WorkStatus.COMPLETED
        self.activity.save()
        OperationalEvidence.objects.create(
            organization=self.organization,
            activity=self.activity,
            kind="human",
            summary="Conferência comprovada",
            recorded_by=self.operator,
        )
        OperationalActivity.objects.create(
            organization=self.organization,
            company=self.company,
            code="pay-guide",
            title="Pagamento separado",
            area="payroll",
            competence=date(2026, 9, 1),
            payment_status=OperationalActivity.PaymentStatus.EXPECTED,
        )
        self._login(self.operator)
        response = self.client.get(reverse("hub:dashboard"), {"closing_month": "2026-09"})
        payroll = response.context["closing_rows"][2]
        self.assertEqual(payroll["assessment"].status, "completed")
        self.assertEqual(payroll["assessment"].total_activities, 1)
        self.assertContains(response, "1 evidência")
        other_month = self.client.get(reverse("hub:dashboard"), {"closing_month": "2026-08"})
        self.assertTrue(
            all(r["assessment"].total_activities == 0 for r in other_month.context["closing_rows"])
        )
        invalid = self.client.get(reverse("hub:dashboard"), {"closing_month": "invalid"})
        self.assertContains(invalid, "Competência inválida")
        self.assertFalse(invalid.context["closing_filter_valid"])
        self.assertEqual(invalid.context["closing_rows"], [])
        self.assertContains(invalid, "O CICA não trocou seu filtro por outro mês")
        self.assertContains(invalid, 'class="closing-filter-field"')
        self.assertContains(invalid, "Ver competência")
        self.assertContains(invalid, 'data-busy-label="Atualizando…"')
        self.assertContains(invalid, 'aria-describedby="closing-error"')

    def test_dashboard_closing_paginates_companies_without_granting_access(self) -> None:
        ClientCompany.objects.bulk_create(
            [
                ClientCompany(organization=self.organization, name=f"Empresa adicional {i:02}")
                for i in range(10)
            ]
        )
        self._login(self.owner)
        response = self.client.get(reverse("hub:dashboard"), {"closing_page": "2"})
        self.assertEqual(response.context["closing_page"].paginator.count, 12)
        self.assertEqual(len(response.context["closing_rows"]), 6)
        self._login(self.operator)
        response = self.client.get(reverse("hub:dashboard"), {"closing_page": "2"})
        self.assertEqual(response.context["closing_page"].paginator.count, 1)

    def test_dashboard_separates_personal_portfolio_and_management(self) -> None:
        shared = OperationalActivity.objects.create(
            organization=self.organization,
            company=self.company,
            code="shared",
            title="Tarefa compartilhada",
            area="fiscal",
        )
        hidden = OperationalActivity.objects.create(
            organization=self.organization,
            company=self.other_company,
            code="hidden",
            title="Empresa fora da carteira",
            area="fiscal",
            assigned_to=self.operator,
        )
        self._login(self.operator)
        mine = self.client.get(reverse("hub:dashboard"))
        self.assertContains(mine, self.activity.title)
        self.assertNotContains(mine, shared.title)
        self.assertNotContains(mine, hidden.title)
        self.assertNotContains(mine, "Distribuição de atividades")
        portfolio = self.client.get(reverse("hub:dashboard"), {"view": "portfolio"})
        self.assertContains(portfolio, shared.title)
        self.assertContains(portfolio, self.activity.title)
        self.assertNotContains(portfolio, hidden.title)
        self.assertEqual(
            self.client.get(reverse("hub:dashboard"), {"view": "management"}).status_code, 403
        )
        self._login(self.owner)
        personal = self.client.get(reverse("hub:dashboard"))
        self.assertNotContains(personal, self.activity.title)
        self.assertContains(personal, "Meu trabalho")
        management = self.client.get(reverse("hub:dashboard"), {"view": "management"})
        self.assertContains(management, self.activity.title)
        self.assertContains(management, "Distribuição de atividades")

    def test_dashboard_explains_the_next_action_without_repeating_audit_states(self) -> None:
        self._login(self.operator)

        response = self.client.get(reverse("hub:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comece por 1 atividade em atraso")
        self.assertContains(response, "1 dia em atraso")
        self.assertContains(response, "Prazo interno")
        self.assertContains(response, "<strong>Meu trabalho</strong>", html=False)
        self.assertContains(response, "Conferir fechamento por empresa")
        self.assertNotContains(response, "Não verificado · Não aplicável · Atualizado")
        self.assertNotContains(response, 'class="dashboard-task-owner"')
        self.assertFalse(response.context["closing_expanded"])

        portfolio = self.client.get(reverse("hub:dashboard"), {"view": "portfolio"})
        self.assertContains(portfolio, 'class="dashboard-task-owner"')
        filtered = self.client.get(
            reverse("hub:dashboard"), {"view": "mine", "filter": "overdue"}
        )
        self.assertContains(filtered, "Atividades em atraso")
        self.assertContains(filtered, "Limpar filtro")
        closing = self.client.get(reverse("hub:dashboard"), {"closing_open": "1"})
        self.assertTrue(closing.context["closing_expanded"])
        self.assertContains(closing, "closing-panel closing-disclosure\" open")

    def test_agenda_today_filter_and_pagination_keep_the_personal_scope(self) -> None:
        today = timezone.localdate()
        for i in range(31):
            OperationalActivity.objects.create(
                organization=self.organization,
                company=self.company,
                code=f"daily-{i}",
                title=f"Trabalho do dia {i}",
                area="fiscal",
                assigned_to=self.operator,
                internal_due_on=today,
            )
        OperationalActivity.objects.create(
            organization=self.organization,
            company=self.company,
            code="done",
            title="Tarefa já concluída",
            area="fiscal",
            assigned_to=self.operator,
            internal_due_on=today,
            work_status=OperationalActivity.WorkStatus.COMPLETED,
        )
        self._login(self.operator)
        first = self.client.get(reverse("hub:dashboard"), {"view": "mine", "filter": "today"})
        second = self.client.get(
            reverse("hub:dashboard"), {"view": "mine", "filter": "today", "page": 2}
        )
        last = self.client.get(
            reverse("hub:dashboard"), {"view": "mine", "filter": "today", "page": 4}
        )
        self.assertEqual(first.context["agenda_page"].paginator.count, 31)
        self.assertEqual(len(first.context["dashboard_activities"]), 10)
        self.assertEqual(len(second.context["dashboard_activities"]), 10)
        self.assertEqual(len(last.context["dashboard_activities"]), 1)
        self.assertContains(first, "?view=mine&amp;filter=today&amp;page=2")
        self.assertNotContains(first, self.activity.title)
        self.assertNotContains(first, "Tarefa já concluída")
        self.assertTrue(
            all(
                a.assigned_to_id == self.operator.id for a in second.context["dashboard_activities"]
            )
        )

    def test_revoking_last_grant_never_expands_the_operator_portfolio(self) -> None:
        self._login(self.operator)
        CompanyAccessGrant.objects.filter(membership=self.operator_membership).update(
            is_active=False
        )
        self.assertFalse(company_queryset_for_membership(self.operator_membership).exists())
        self.assertFalse(
            company_has_capability(
                membership=self.operator_membership, company=self.company, capability="*"
            )
        )
        self.assertFalse(
            membership_has_capability(membership=self.operator_membership, capability="*")
        )
        response = self.client.get(reverse("hub:activities"))
        self.assertNotContains(response, self.activity.title)
        self.assertEqual(
            self.client.get(reverse("hub:activity-detail", args=[self.activity.id])).status_code,
            404,
        )

    def test_dashboard_and_queue_order_legal_only_deadline_before_future_internal_deadline(
        self,
    ) -> None:
        self.activity.internal_due_on = timezone.localdate() + timedelta(days=4)
        self.activity.save(update_fields=["internal_due_on"])
        legal_only = OperationalActivity.objects.create(
            organization=self.organization,
            company=self.company,
            code="legal-only",
            title="Obrigação legal atrasada",
            area="fiscal",
            assigned_to=self.operator,
            legal_due_on=timezone.localdate() - timedelta(days=2),
        )
        undated = OperationalActivity.objects.create(
            organization=self.organization,
            company=self.company,
            code="undated",
            title="Atividade sem prazo",
            area="fiscal",
            assigned_to=self.operator,
        )
        self._login(self.operator)
        for route in ("hub:dashboard", "hub:activities"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                html = response.content.decode()
                self.assertLess(html.index(legal_only.title), html.index(self.activity.title))
                self.assertLess(html.index(self.activity.title), html.index(undated.title))

    def test_local_owner_keeps_office_scope_even_with_an_explicit_grant(self) -> None:
        CompanyAccessGrant.objects.create(
            organization=self.organization,
            membership=self.owner_membership,
            company=self.company,
        )
        self.assertCountEqual(
            company_queryset_for_membership(self.owner_membership),
            [self.company, self.other_company],
        )
        self.assertTrue(
            company_has_capability(
                membership=self.owner_membership, company=self.other_company, capability="*"
            )
        )

    def test_inactive_membership_or_office_denies_portfolio_and_capabilities(self) -> None:
        for disabled in ("membership", "office"):
            with self.subTest(disabled=disabled):
                self.owner_membership.is_active = disabled != "membership"
                self.owner_membership.organization.is_active = disabled != "office"
                self.assertFalse(company_queryset_for_membership(self.owner_membership).exists())
                self.assertFalse(
                    company_has_capability(
                        membership=self.owner_membership, company=self.company, capability="*"
                    )
                )
                self.assertFalse(
                    membership_has_capability(membership=self.owner_membership, capability="*")
                )

    def test_completion_requires_evidence_and_records_an_immutable_history(self) -> None:
        self._login(self.operator)
        complete_url = reverse("hub:activity-complete", args=[self.activity.id])

        refused = self.client.post(complete_url, follow=True)
        self.assertContains(refused, "exige confirmação humana")
        self.assertNotContains(refused, "['Esta atividade")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.work_status, OperationalActivity.WorkStatus.PENDING)

        evidence_url = reverse("hub:activity-add-evidence", args=[self.activity.id])
        response = self.client.post(
            evidence_url,
            {"reference": "Recibo interno", "summary": "Folha conferida pelo responsável."},
            follow=True,
        )
        self.assertContains(response, "Evidência registrada")
        self.assertEqual(OperationalEvidence.objects.filter(activity=self.activity).count(), 1)

        completed = self.client.post(complete_url, follow=True)
        self.assertContains(completed, "Atividade concluída")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.work_status, OperationalActivity.WorkStatus.COMPLETED)
        self.assertTrue(
            OperationalActivityEvent.objects.filter(
                activity=self.activity, event_type="completed"
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action="hub.activity.completed", target_id=str(self.activity.id)
            ).exists()
        )
        with self.assertRaises(ValidationError):
            OperationalEvidence.objects.filter(activity=self.activity).first().delete()  # type: ignore[union-attr]

    def test_completed_activity_keeps_evidence_form_but_hides_invalid_actions(self) -> None:
        self._login(self.operator)
        self.client.post(
            reverse("hub:activity-add-evidence", args=[self.activity.id]),
            {"reference": "QA-LOCAL-001", "summary": "Comprova??o posterior."},
        )
        self.client.post(reverse("hub:activity-complete", args=[self.activity.id]))

        response = self.client.get(reverse("hub:activity-detail", args=[self.activity.id]))

        self.assertContains(response, "Atividade encerrada.")
        self.assertContains(response, "/evidencias/")
        self.assertNotContains(response, "Registrar impedimento")
        self.assertNotContains(response, "Concluir atividade")

    def test_waived_activity_keeps_evidence_form_but_hides_invalid_actions(self) -> None:
        self.activity.work_status = OperationalActivity.WorkStatus.WAIVED
        self.activity.waived_reason = "Applicable waiver evidence."
        self.activity.save(update_fields=["work_status", "waived_reason", "updated_at"])
        self._login(self.operator)

        response = self.client.get(reverse("hub:activity-detail", args=[self.activity.id]))

        self.assertContains(response, "Atividade encerrada.")
        self.assertContains(response, "/evidencias/")
        self.assertNotContains(response, "Registrar impedimento")
        self.assertNotContains(response, "Concluir atividade")

    def test_accepted_obligation_is_independent_from_human_evidence(self) -> None:
        self.activity.requires_accepted_obligation = True
        self.activity.save(update_fields=["requires_accepted_obligation", "updated_at"])
        self._login(self.operator)
        self.client.post(
            reverse("hub:activity-add-evidence", args=[self.activity.id]),
            {"summary": "Conferência concluída."},
        )

        response = self.client.post(
            reverse("hub:activity-complete", args=[self.activity.id]), follow=True
        )

        self.assertContains(response, "obrigação aplicável ainda não está aceita")
        self.activity.refresh_from_db()
        self.assertNotEqual(self.activity.work_status, OperationalActivity.WorkStatus.COMPLETED)

    def test_processing_requirement_is_independent_from_evidence(self) -> None:
        self.activity.requires_processing_closed = True
        self.activity.save(update_fields=["requires_processing_closed", "updated_at"])
        self._login(self.operator)
        self.client.post(
            reverse("hub:activity-add-evidence", args=[self.activity.id]),
            {"summary": "Conferência concluída."},
        )

        refused = self.client.post(
            reverse("hub:activity-complete", args=[self.activity.id]), follow=True
        )
        self.assertContains(refused, "processamento aplicável ainda não está confirmado")
        self.activity.refresh_from_db()
        self.assertNotEqual(self.activity.work_status, OperationalActivity.WorkStatus.COMPLETED)

        self.activity.processing_status = OperationalActivity.ProcessingStatus.CLOSED
        self.activity.save(update_fields=["processing_status", "updated_at"])
        completed = self.client.post(
            reverse("hub:activity-complete", args=[self.activity.id]), follow=True
        )
        self.assertContains(completed, "Atividade concluída")

    def test_closing_assessment_keeps_blocking_and_source_availability_distinct(self) -> None:
        OperationalEvidence.objects.create(
            organization=self.organization,
            activity=self.activity,
            kind="human",
            summary="Conferência documentada.",
            recorded_by=self.operator,
        )
        self.activity.work_status = OperationalActivity.WorkStatus.COMPLETED
        self.activity.save(update_fields=["work_status", "updated_at"])
        completed = assess_closing([self.activity])
        self.assertEqual(completed.status, "completed")

        self.activity.freshness = OperationalActivity.Freshness.UNAVAILABLE
        self.activity.save(update_fields=["freshness", "updated_at"])
        unverifiable = assess_closing([self.activity])
        self.assertEqual(unverifiable.status, "unverifiable")
        self.assertEqual(unverifiable.unavailable_sources, 1)

        self.activity.work_status = OperationalActivity.WorkStatus.BLOCKED
        self.activity.save(update_fields=["work_status", "updated_at"])
        blocked = assess_closing([self.activity])
        self.assertEqual(blocked.status, "blocked")
        self.assertEqual(blocked.pending_activities, 1)

    def test_completed_flag_does_not_replace_evidence_or_required_states(self) -> None:
        self.activity.work_status = OperationalActivity.WorkStatus.COMPLETED
        self.activity.requires_processing_closed = True
        self.activity.requires_accepted_obligation = True
        self.activity.save()
        result = assess_closing([self.activity])
        self.assertEqual((result.status, result.completed_activities), ("open", 0))
        self.assertEqual(len(result.missing_requirements[0][1]), 3)
        with self.assertRaises(ValidationError):
            complete_activity(
                activity=self.activity,
                membership=self.operator_membership,
                actor=self.operator,
                request=RequestFactory().post("/"),
            )
        OperationalEvidence.objects.create(
            organization=self.organization,
            activity=self.activity,
            kind="human",
            recorded_by=self.operator,
            summary="Conferência concluída.",
        )
        self.activity.processing_status = OperationalActivity.ProcessingStatus.CLOSED
        self.activity.obligation_status = OperationalActivity.ObligationStatus.SUBMITTED
        self.assertEqual(assess_closing([self.activity]).status, "open")
        self.activity.obligation_status = OperationalActivity.ObligationStatus.ACCEPTED
        self.activity.payment_status = OperationalActivity.PaymentStatus.EXPECTED
        self.assertEqual(assess_closing([self.activity]).status, "completed")
        self.activity.processing_status = OperationalActivity.ProcessingStatus.REOPENED
        self.assertEqual(assess_closing([self.activity]).status, "reopened")

    def test_document_alone_does_not_confirm_work_and_stale_source_prevents_completion(
        self,
    ) -> None:
        self.activity.evidence_requirement = "source_or_human"
        self.activity.work_status = OperationalActivity.WorkStatus.COMPLETED
        OperationalEvidence.objects.create(
            organization=self.organization,
            activity=self.activity,
            kind="document",
            summary="Arquivo recebido.",
        )
        self.assertEqual(assess_closing([self.activity]).status, "open")
        OperationalEvidence.objects.create(
            organization=self.organization,
            activity=self.activity,
            kind="source",
            summary="Fonte conferida.",
        )
        self.activity.evidence_requirement = "source"
        self.assertEqual(assess_closing([self.activity]).status, "open")
        self.activity.freshness = OperationalActivity.Freshness.CURRENT
        self.assertEqual(assess_closing([self.activity]).status, "completed")
        for freshness in (
            OperationalActivity.Freshness.STALE,
            OperationalActivity.Freshness.UNAVAILABLE,
        ):
            with self.subTest(freshness=freshness):
                self.activity.freshness = freshness
                self.activity.save()
                result = assess_closing([self.activity])
                self.assertEqual((result.status, result.pending_activities), ("unverifiable", 1))
                with self.assertRaises(ValidationError):
                    complete_activity(
                        activity=self.activity,
                        membership=self.operator_membership,
                        actor=self.operator,
                        request=RequestFactory().post("/"),
                    )

    def test_waiver_needs_traceable_proof_but_not_processing_or_transmission(self) -> None:
        self.assertEqual(assess_closing([]).status, "not_started")
        self.activity.work_status = OperationalActivity.WorkStatus.WAIVED
        self.activity.requires_processing_closed = True
        self.activity.requires_accepted_obligation = True
        self.activity.obligation_status = OperationalActivity.ObligationStatus.REJECTED
        self.activity.freshness = OperationalActivity.Freshness.UNAVAILABLE
        self.assertEqual(assess_closing([self.activity]).status, "open")
        self.activity.waived_reason = "Dispensa aplicável registrada."
        self.activity.completed_by = self.operator
        self.activity.completed_at = timezone.now()
        OperationalEvidence.objects.create(
            organization=self.organization,
            activity=self.activity,
            kind="document",
            summary="Comprovante de dispensa.",
        )
        self.assertEqual(assess_closing([self.activity]).status, "completed")

    def test_company_keeps_a_commercial_root_only_for_a_valid_cnpj(self) -> None:
        self.company.cnpj_masked = "68.340.160/0001-13"
        self.company.save(update_fields=["cnpj_masked", "updated_at"])
        self.company.refresh_from_db()
        self.assertEqual(self.company.commercial_root_cnpj, "68340160")

        unknown = ClientCompany.objects.create(
            organization=self.organization,
            name="Empresa sem identificação comercial",
            cnpj_masked="12.345.678/0001-00",
        )
        self.assertEqual(unknown.commercial_root_cnpj, "")

    def test_commercial_capacity_counts_active_roots_and_active_users(self) -> None:
        self.company.cnpj_masked = "68.340.160/0001-13"
        self.company.save(update_fields=["cnpj_masked", "updated_at"])
        branch = ClientCompany.objects.create(
            organization=self.organization,
            name="Filial da Empresa A",
            cnpj_masked="68.340.160/0001-13",
        )
        without_root = ClientCompany.objects.create(
            organization=self.organization, name="Empresa sem CNPJ"
        )
        allowance = UsageAllowance.objects.create(
            organization=self.organization,
            metric=UsageAllowance.Metric.COMPANIES,
            included=5,
            period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 30),
        )
        capacity = refresh_configured_capacity(
            organization=self.organization, period_start=allowance.period_start
        )
        allowance.refresh_from_db()
        self.assertEqual(capacity.active_users, 2)
        self.assertEqual(capacity.active_company_roots, 1)
        self.assertEqual(capacity.active_companies_without_root, 2)
        self.assertEqual(allowance.consumed, 1)
        branch.active = False
        branch.save(update_fields=["active", "updated_at"])
        without_root.active = False
        without_root.save(update_fields=["active", "updated_at"])
        refreshed = calculate_commercial_capacity(organization=self.organization)
        self.assertEqual(refreshed.active_company_roots, 1)

    def test_source_observation_reopens_completed_activity_and_preserves_prior_state(
        self,
    ) -> None:
        self._login(self.operator)
        self.client.post(
            reverse("hub:activity-add-evidence", args=[self.activity.id]),
            {"summary": "Fechamento confirmado antes da retificação."},
        )
        self.client.post(reverse("hub:activity-complete", args=[self.activity.id]))
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.work_status, OperationalActivity.WorkStatus.COMPLETED)
        source = DataSource.objects.create(
            organization=self.organization,
            kind=DataSource.Kind.DOMINIO_LOCAL_AGENT,
            label="Agente Domínio",
            capabilities=["activity_processing_status"],
        )
        request = RequestFactory().post("/")
        observed = record_source_observation(
            activity=self.activity,
            data_source=source,
            actor=self.owner,
            request=request,
            successful=True,
            summary="Competência reaberta pela fonte.",
            external_reference="dominio:folha:2026-09",
            source_version="2026-09-22T12:00:00Z",
            processing_status=OperationalActivity.ProcessingStatus.REOPENED,
        )

        self.assertTrue(observed.successful)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.work_status, OperationalActivity.WorkStatus.PENDING)
        self.assertIsNone(self.activity.completed_at)
        self.assertEqual(
            self.activity.processing_status, OperationalActivity.ProcessingStatus.REOPENED
        )
        self.assertEqual(self.activity.freshness, OperationalActivity.Freshness.CURRENT)
        self.assertTrue(
            OperationalActivityEvent.objects.filter(
                activity=self.activity, event_type="reopened_from_source"
            ).exists()
        )
        detail = self.client.get(reverse("hub:activity-detail", args=[self.activity.id]))
        self.assertContains(detail, "Leitura confirmada")
        self.assertContains(detail, source.label)

        failed = record_source_observation(
            activity=self.activity,
            data_source=source,
            actor=self.owner,
            request=request,
            successful=False,
            summary="Agente indisponível; última leitura preservada.",
        )
        self.assertFalse(failed.successful)
        self.activity.refresh_from_db()
        self.assertEqual(
            self.activity.processing_status, OperationalActivity.ProcessingStatus.REOPENED
        )
        self.assertEqual(self.activity.freshness, OperationalActivity.Freshness.UNAVAILABLE)
        self.assertEqual(
            OperationalSourceObservation.objects.filter(
                activity=self.activity, successful=True
            ).count(),
            1,
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action="hub.activity.source_unavailable", organization=self.organization
            ).exists()
        )

    def test_source_cannot_change_operational_state_without_declared_capability(self) -> None:
        source = DataSource.objects.create(
            organization=self.organization,
            kind=DataSource.Kind.DOMINIO_LOCAL_AGENT,
            label="Unverified source",
            capabilities=["companies"],
        )

        with self.assertRaisesRegex(ValidationError, "capacidade comprovada"):
            record_source_observation(
                activity=self.activity,
                data_source=source,
                actor=None,
                request=None,
                successful=True,
                summary="Unverified closing state.",
                processing_status=OperationalActivity.ProcessingStatus.CLOSED,
            )

        self.activity.refresh_from_db()
        self.assertEqual(
            self.activity.processing_status, OperationalActivity.ProcessingStatus.NOT_VERIFIED
        )
        self.assertEqual(self.activity.source_observations.count(), 0)

    def test_source_state_capability_is_rechecked_after_locking_current_source(self) -> None:
        source = DataSource.objects.create(
            organization=self.organization,
            kind=DataSource.Kind.DOMINIO_LOCAL_AGENT,
            label="Stale source object",
            capabilities=["activity_processing_status"],
        )
        DataSource.objects.filter(pk=source.pk).update(capabilities=[])

        with self.assertRaisesRegex(ValidationError, "capacidade comprovada"):
            record_source_observation(
                activity=self.activity,
                data_source=source,
                actor=None,
                request=None,
                successful=True,
                summary="State from stale adapter object.",
                processing_status=OperationalActivity.ProcessingStatus.CLOSED,
            )

        self.activity.refresh_from_db()
        self.assertEqual(
            self.activity.processing_status, OperationalActivity.ProcessingStatus.NOT_VERIFIED
        )
        self.assertEqual(self.activity.source_observations.count(), 0)

    def test_disabled_source_cannot_change_operational_state(self) -> None:
        source = DataSource.objects.create(
            organization=self.organization,
            kind=DataSource.Kind.DOMINIO_LOCAL_AGENT,
            label="Disabled source",
            status=DataSource.Status.DISABLED,
            capabilities=["activity_processing_status"],
        )

        with self.assertRaisesRegex(ValidationError, "desativada"):
            record_source_observation(
                activity=self.activity,
                data_source=source,
                actor=None,
                request=None,
                successful=True,
                summary="Unexpected source state.",
                processing_status=OperationalActivity.ProcessingStatus.CLOSED,
            )

        self.activity.refresh_from_db()
        self.assertEqual(
            self.activity.processing_status, OperationalActivity.ProcessingStatus.NOT_VERIFIED
        )
        self.assertEqual(self.activity.source_observations.count(), 0)

    def test_disabled_source_late_result_is_history_only_and_does_not_reactivate(self) -> None:
        prior_processing = self.activity.processing_status
        prior_obligation = self.activity.obligation_status
        source = DataSource.objects.create(
            organization=self.organization,
            kind=DataSource.Kind.DOMINIO_LOCAL_AGENT,
            label="Disabled source",
            status=DataSource.Status.DISABLED,
            source_snapshot_at=timezone.now() - timedelta(days=1),
        )

        observation = record_source_observation(
            activity=self.activity,
            data_source=source,
            actor=None,
            request=None,
            successful=True,
            summary="Late response after administrative disablement.",
            observed_at=timezone.now(),
        )

        source.refresh_from_db()
        self.activity.refresh_from_db()
        self.assertTrue(observation.successful)
        self.assertEqual(source.status, DataSource.Status.DISABLED)
        self.assertIsNotNone(source.source_snapshot_at)
        self.assertEqual(self.activity.freshness, OperationalActivity.Freshness.NOT_CONFIGURED)
        self.assertEqual(
            self.activity.processing_status, prior_processing
        )
        self.assertEqual(self.activity.obligation_status, prior_obligation)
        self.assertTrue(
            OperationalActivityEvent.objects.filter(
                activity=self.activity, event_type="source_history_only"
            ).exists()
        )

    def test_source_late_results_and_exact_replay_do_not_regress_current_state(self) -> None:
        source = DataSource.objects.create(
            organization=self.organization,
            kind=DataSource.Kind.DOMINIO_LOCAL_AGENT,
            label="Fonte",
            capabilities=["activity_processing_status", "activity_obligation_status"],
        )
        now = timezone.now()
        arguments = dict(
            activity=self.activity,
            data_source=source,
            actor=None,
            request=None,
            successful=True,
            summary="Fechado na fonte",
            processing_status="closed",
            observed_at=now,
        )
        first = record_source_observation(**arguments)
        self.activity.work_status = "completed"
        self.activity.save(update_fields=["work_status"])
        self.assertEqual(record_source_observation(**arguments).pk, first.pk)
        self.assertEqual(self.activity.events.count(), 1)
        self.assertEqual(self.activity.evidence_items.count(), 1)
        record_source_observation(
            **{**arguments, "processing_status": "reopened", "observed_at": now - timedelta(days=1)}
        )
        record_source_observation(
            **{**arguments, "successful": False, "observed_at": now - timedelta(hours=1)}
        )
        self.activity.refresh_from_db()
        source.refresh_from_db()
        self.assertEqual(self.activity.work_status, "completed")
        self.assertEqual(self.activity.processing_status, "closed")
        self.assertEqual(self.activity.freshness, "current")
        self.assertEqual(source.source_snapshot_at, now)
        self.assertEqual(source.status, DataSource.Status.READY)
        self.assertEqual(self.activity.source_observations.count(), 3)
        self.assertEqual(self.activity.evidence_items.count(), 1)

    def test_source_dimensions_are_independent_and_conflict_requires_newer_value(self) -> None:
        source = DataSource.objects.create(
            organization=self.organization,
            kind=DataSource.Kind.DOMINIO_LOCAL_AGENT,
            label="Fonte",
            capabilities=["activity_processing_status", "activity_obligation_status"],
        )
        now = timezone.now()
        base = dict(
            activity=self.activity,
            data_source=source,
            actor=None,
            request=None,
            successful=True,
            summary="Retorno observado",
        )
        record_source_observation(**base, obligation_status="accepted", observed_at=now)
        record_source_observation(
            **base, processing_status="closed", observed_at=now - timedelta(hours=1)
        )
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.processing_status, "closed")
        self.assertEqual(self.activity.obligation_status, "accepted")
        record_source_observation(
            **base, processing_status="reopened", observed_at=now - timedelta(hours=1)
        )
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.processing_status, "closed")
        self.assertEqual(self.activity.freshness, "stale")
        record_source_observation(
            **base, obligation_status="accepted", observed_at=now + timedelta(seconds=1)
        )
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.freshness, "stale")
        record_source_observation(
            **base, processing_status="closed", observed_at=now + timedelta(seconds=2)
        )
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.freshness, "current")
        with self.assertRaises(ValidationError):
            record_source_observation(**base, observed_at=now.replace(tzinfo=None))

    def test_monthly_generation_is_idempotent_and_preserves_template_versions(self) -> None:
        template = ActivityTemplate.objects.create(
            organization=self.organization,
            code="folha-fechamento",
            title="Fechar folha",
            area=ActivityTemplate.Area.PAYROLL,
            internal_due_day=8,
            legal_due_day=10,
            evidence_requirement=ActivityTemplate.EvidenceRequirement.HUMAN,
        )
        assignment = ActivityTemplateAssignment.objects.create(
            organization=self.organization,
            template=template,
            company=self.company,
            assigned_to=self.operator,
        )
        competence = date(2026, 10, 1)

        created, ignored = generate_monthly_activities(
            assignments=[assignment],
            competence=competence,
            actor=self.owner,
            request=RequestFactory().post("/"),
        )
        duplicate, duplicate_ignored = generate_monthly_activities(
            assignments=[assignment],
            competence=competence,
            actor=self.owner,
            request=RequestFactory().post("/"),
        )

        self.assertEqual(len(created), 1)
        self.assertEqual(ignored, 0)
        self.assertEqual(duplicate, [])
        self.assertEqual(duplicate_ignored, 1)
        generated = created[0]
        self.assertEqual(generated.internal_due_on, date(2026, 10, 8))
        self.assertEqual(generated.legal_due_on, date(2026, 10, 10))
        self.assertEqual(generated.template_version, 1)

        revised = ActivityTemplate.objects.create(
            organization=self.organization,
            code=template.code,
            title="Fechar folha revisado",
            area=template.area,
            version=2,
        )
        revised_assignment = ActivityTemplateAssignment.objects.create(
            organization=self.organization,
            template=revised,
            company=self.company,
        )
        revised_created, _ = generate_monthly_activities(
            assignments=[revised_assignment],
            competence=competence,
            actor=self.owner,
            request=RequestFactory().post("/"),
        )
        self.assertEqual(len(revised_created), 1)
        self.assertEqual(revised_created[0].template_version, 2)
        generated.refresh_from_db()
        self.assertEqual(generated.title, "Fechar folha")

    def test_manual_generation_drops_stale_assignee_and_preserves_assignment(self) -> None:
        unavailable_user = User.objects.create_user(
            "unavailable@example.test", "safe-password-123"
        )
        Membership.objects.create(
            organization=self.organization,
            user=unavailable_user,
            role=Membership.Role.OPERATOR,
        )
        template = ActivityTemplate.objects.create(
            organization=self.organization,
            code="unavailable-assignee",
            title="Atividade sem carteira",
            area=ActivityTemplate.Area.FISCAL,
        )
        assignment = ActivityTemplateAssignment.objects.create(
            organization=self.organization,
            template=template,
            company=self.company,
            assigned_to=unavailable_user,
        )

        created, ignored = generate_monthly_activities(
            assignments=[assignment],
            competence=date(2026, 10, 1),
            actor=self.owner,
            request=RequestFactory().post("/"),
        )

        self.assertEqual(ignored, 0)
        self.assertEqual(len(created), 1)
        self.assertIsNone(created[0].assigned_to_id)
        self.assertTrue(created[0].events.filter(event_type="assignment_unavailable").exists())
        assignment.refresh_from_db()
        self.assertEqual(assignment.assigned_to_id, unavailable_user.id)

    def test_generation_rejects_cross_office_assignment_before_creating_activity(self) -> None:
        other_office = Organization.objects.create(name="Other", slug="other-generation")
        other_company = ClientCompany.objects.create(organization=other_office, name="Other")
        template = ActivityTemplate.objects.create(
            organization=self.organization,
            code="cross-office",
            title="Invalid assignment",
            area=ActivityTemplate.Area.FISCAL,
        )
        invalid = ActivityTemplateAssignment.objects.create(
            organization=self.organization,
            template=template,
            company=other_company,
        )

        with self.assertRaisesRegex(ValidationError, "mesmo escritorio"):
            generate_monthly_activities(
                assignments=[invalid],
                competence=date(2026, 10, 1),
                actor=self.owner,
                request=RequestFactory().post("/"),
            )

        self.assertFalse(OperationalActivity.objects.filter(code="cross-office").exists())

    def test_only_administrator_can_manage_activity_models(self) -> None:
        self._login(self.operator)
        self.assertEqual(self.client.get(reverse("hub:activity-models")).status_code, 403)

        self._login(self.owner)
        response = self.client.post(
            reverse("hub:activity-models"),
            {
                "action": "template",
                "template-code": "fiscal-conferencia",
                "template-title": "Conferir fiscal",
                "template-area": "fiscal",
                "template-frequency": "monthly",
                "template-evidence_requirement": "human",
                "template-internal_due_day": "5",
            },
            follow=True,
        )
        self.assertContains(response, "Modelo fiscal-conferencia v1 criado")
        self.assertTrue(
            ActivityTemplate.objects.filter(
                organization=self.organization, code="fiscal-conferencia", version=1
            ).exists()
        )
        template = ActivityTemplate.objects.get(
            organization=self.organization, code="fiscal-conferencia", version=1
        )
        assigned = self.client.post(
            reverse("hub:activity-models"),
            {
                "action": "assignment",
                "assignment-template": str(template.id),
                "assignment-company": str(self.company.id),
                "assignment-assigned_to": str(self.operator.id),
            },
            follow=True,
        )
        self.assertContains(assigned, "Modelo atribuído à empresa")
        self.assertTrue(
            ActivityTemplateAssignment.objects.filter(
                template=template, company=self.company
            ).exists()
        )
        generated = self.client.post(
            reverse("hub:activity-models"),
            {"action": "generate", "generation-competence": "2026-10"},
            follow=True,
        )
        self.assertContains(generated, "1 atividade(s) gerada(s)")
        self.assertTrue(
            OperationalActivity.objects.filter(
                company=self.company, code=template.code, competence=date(2026, 10, 1)
            ).exists()
        )
        assignment = template.company_assignments.get()
        paused = self.client.post(
            reverse("hub:activity-models"),
            {"action": "assignment-toggle", "assignment_id": str(assignment.id)},
            follow=True,
        )
        self.assertContains(paused, "A atribuição foi pausada")
        assignment.refresh_from_db()
        self.assertFalse(assignment.active)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="hub.activity_template.assignment_toggled",
                organization=self.organization,
            ).exists()
        )

    def test_activity_model_form_rejects_assignee_without_company_portfolio(self) -> None:
        unavailable_user = User.objects.create_user(
            "form-unavailable@example.test", "safe-password-123"
        )
        Membership.objects.create(
            organization=self.organization,
            user=unavailable_user,
            role=Membership.Role.OPERATOR,
        )
        template = ActivityTemplate.objects.create(
            organization=self.organization,
            code="form-assignee-scope",
            title="Scope assignment",
            area=ActivityTemplate.Area.FISCAL,
        )
        self._login(self.owner)

        response = self.client.post(
            reverse("hub:activity-models"),
            {
                "action": "assignment",
                "assignment-template": str(template.id),
                "assignment-company": str(self.company.id),
                "assignment-assigned_to": str(unavailable_user.id),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "perfil operacional e carteira ativa", status_code=400)
        self.assertFalse(
            ActivityTemplateAssignment.objects.filter(
                template=template, company=self.company
            ).exists()
        )

    def test_activity_model_duplicate_assignment_is_recoverable(self) -> None:
        template = ActivityTemplate.objects.create(
            organization=self.organization,
            code="duplicate-assignment",
            title="Conferir rotina duplicada",
            area=ActivityTemplate.Area.FISCAL,
        )
        ActivityTemplateAssignment.objects.create(
            organization=self.organization,
            template=template,
            company=self.company,
            assigned_to=self.operator,
        )
        self._login(self.owner)

        response = self.client.post(
            reverse("hub:activity-models"),
            {
                "action": "assignment",
                "assignment-template": str(template.id),
                "assignment-company": str(self.company.id),
                "assignment-assigned_to": str(self.operator.id),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "já está atribuído", status_code=400)
        self.assertContains(response, 'id="assignment-step" open', status_code=400)
        self.assertEqual(
            ActivityTemplateAssignment.objects.filter(
                template=template, company=self.company
            ).count(),
            1,
        )

    def test_activity_model_overview_and_template_pause(self) -> None:
        template = ActivityTemplate.objects.create(
            organization=self.organization,
            code="pause-template",
            title="Conferir modelo pausável",
            area=ActivityTemplate.Area.ACCOUNTING,
        )
        ActivityTemplateAssignment.objects.create(
            organization=self.organization,
            template=template,
            company=self.company,
            assigned_to=self.operator,
        )
        self._login(self.owner)

        overview = self.client.get(reverse("hub:activity-models"))
        self.assertContains(overview, "Prontas para gerar")
        self.assertContains(overview, "Empresas cobertas")
        self.assertContains(overview, "Conferir modelo pausável")

        paused = self.client.post(
            reverse("hub:activity-models"),
            {"action": "template-toggle", "template_id": str(template.id)},
            follow=True,
        )
        self.assertContains(paused, "pause-template v1 pausado")
        template.refresh_from_db()
        self.assertFalse(template.active)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="hub.activity_template.toggled",
                organization=self.organization,
            ).exists()
        )

