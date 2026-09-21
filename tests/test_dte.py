from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import (
    ClientCompany,
    Connector,
    DteMessage,
    DteMessageAccess,
    DteRun,
    DteRunItem,
    ProductModule,
)
from apps.organizations.models import Membership, Organization


class DteCenterTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("dte@example.test", "safe-password-123")
        self.organization = Organization.objects.create(
            name="Escrit\u00f3rio DTE", slug="escritorio-dte"
        )
        self.membership = Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OPERATOR
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa DTE", cnpj_masked="12.345.678/0001-95"
        )
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.INTEGRA, enabled=True
        )
        Connector.objects.create(
            organization=self.organization,
            kind=Connector.Kind.INTEGRA,
            enabled=True,
            status="configured",
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

    def test_dte_screen_prepares_a_local_run_without_dispatching_a_request(self) -> None:
        response = self.client.get(reverse("hub:dte-center"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mensagens por empresa")
        self.assertContains(response, reverse("hub:parcelamentos"))
        self.assertContains(response, self.company.name)
        self.assertNotContains(response, "ClientCompany object")
        self.assertContains(response, "Conexão Serpro indisponível")
        self.assertNotContains(response, "Central CICA ativa")

        prepared = self.client.post(reverse("hub:dte-center"), {"companies": [self.company.id]})

        self.assertRedirects(prepared, reverse("hub:dte-center"))
        run = DteRun.objects.get(organization=self.organization)
        self.assertEqual(run.status, DteRun.Status.AWAITING_APPROVAL)
        self.assertEqual(run.total_companies, 1)
        self.assertTrue(DteRunItem.objects.filter(run=run, company=self.company).exists())

        refused = self.client.post(
            reverse("hub:decide-dte-run", args=[run.id]), {"decision": "approve"}, follow=True
        )
        self.assertRedirects(refused, reverse("hub:dte-center"))
        self.assertContains(refused, "A conexão central Serpro ainda não está configurada")
        run.refresh_from_db()
        self.assertEqual(run.status, DteRun.Status.AWAITING_APPROVAL)

    def test_dte_scope_does_not_accept_a_company_from_another_office(self) -> None:
        another_office = Organization.objects.create(name="Outro", slug="outro-dte")
        other_company = ClientCompany.objects.create(
            organization=another_office, name="N\u00e3o permitida"
        )

        response = self.client.post(reverse("hub:dte-center"), {"companies": [other_company.id]})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A empresa selecionada n\u00e3o est\u00e1 no seu escopo")
        self.assertFalse(DteRun.objects.filter(organization=self.organization).exists())

    def test_dte_history_paginates_without_changing_the_message_page(self) -> None:
        for index in range(31):
            run = DteRun.objects.create(
                organization=self.organization, status=DteRun.Status.COMPLETED
            )
            DteRunItem.objects.create(
                organization=self.organization,
                run=run,
                company=self.company,
                status=DteRunItem.Status.COMPLETED,
                messages_found=index,
            )
        for index in range(26):
            DteMessage.objects.create(
                organization=self.organization,
                company=self.company,
                source_isn=f"message-{index}",
                subject=f"Mensagem {index}",
                sent_at=timezone.now(),
            )

        first_page = self.client.get(reverse("hub:dte-center"), {"history_page": "2"})
        second_message_page = self.client.get(
            reverse("hub:dte-center"), {"page": "2", "history_page": "2"}
        )

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context["dte_items_total"], 31)
        self.assertEqual(first_page.context["dte_items_page"].number, 2)
        self.assertEqual(first_page.context["dte_message_page"].number, 1)
        self.assertEqual(len(first_page.context["dte_items"]), 1)
        self.assertContains(first_page, "31 resultados")
        self.assertContains(
            first_page, "?history_page=2&amp;status=all&amp;company=&amp;q=&amp;page=2"
        )
        self.assertEqual(second_message_page.context["dte_items_page"].number, 2)
        self.assertEqual(second_message_page.context["dte_message_page"].number, 2)
        self.assertEqual(len(second_message_page.context["dte_message_page"].object_list), 1)
        self.assertContains(second_message_page, "Página 2 de 2")
        self.assertContains(
            second_message_page, "?history_page=2&amp;status=all&amp;company=&amp;q=&amp;page=1"
        )

    def test_operator_prepares_next_page_from_own_history_without_dispatch(self) -> None:
        first = DteRun.objects.create(
            organization=self.organization, status=DteRun.Status.COMPLETED
        )
        source = DteRunItem.objects.create(
            organization=self.organization, run=first, company=self.company,
            status=DteRunItem.Status.COMPLETED, more_available=True,
            next_page_pointer="20260912093015",
        )
        screen = self.client.get(reverse("hub:dte-center"))
        self.assertContains(screen, "Preparar próxima página de Empresa DTE")
        prepared = self.client.post(reverse("hub:dte-next-page", args=[source.id]))
        self.assertRedirects(prepared, reverse("hub:dte-center"))
        continuation = DteRunItem.objects.get(continued_from=source)
        self.assertEqual(continuation.run.status, DteRun.Status.AWAITING_APPROVAL)
        self.assertEqual(continuation.requested_page_pointer, "20260912093015")
        repeated = self.client.post(reverse("hub:dte-next-page", args=[source.id]), follow=True)
        self.assertContains(repeated, "já foi preparada")
        self.assertEqual(DteRunItem.objects.filter(continued_from=source).count(), 1)

    def test_company_without_valid_cnpj_is_excluded_before_paid_preparation(self) -> None:
        missing = ClientCompany.objects.create(
            organization=self.organization, name="Empresa sem CNPJ", cnpj_masked=""
        )

        screen = self.client.get(reverse("hub:dte-center"))
        self.assertEqual(screen.context["dte_companies_count"], 1)
        self.assertEqual(screen.context["dte_scope_count"], 2)
        self.assertContains(screen, "Revise o cadastro das empresas")

        submitted = self.client.post(reverse("hub:dte-center"), {"companies": [missing.id]})
        self.assertEqual(submitted.status_code, 200)
        self.assertFalse(DteRun.objects.filter(organization=self.organization).exists())

    def test_all_companies_without_valid_cnpj_get_a_specific_empty_state(self) -> None:
        self.company.cnpj_masked = ""
        self.company.save(update_fields=["cnpj_masked"])

        screen = self.client.get(reverse("hub:dte-center"))

        self.assertEqual(screen.context["dte_companies_count"], 0)
        self.assertContains(screen, "Nenhuma empresa deste escopo tem CNPJ")
        self.assertContains(screen, "Revisar empresas")

    def test_message_summary_never_calls_provider_and_operator_cannot_acknowledge_by_default(
        self,
    ) -> None:
        message = DteMessage.objects.create(
            organization=self.organization,
            company=self.company,
            source_isn="0000082838",
            subject="Intimação de teste",
        )

        summary = self.client.get(reverse("hub:dte-message-detail", args=[message.id]))
        refused = self.client.post(
            reverse("hub:dte-message-detail", args=[message.id]),
            {"confirm_legal_notice": "on"},
        )

        self.assertEqual(summary.status_code, 200)
        self.assertContains(summary, "Teor ainda não consultado")
        self.assertNotContains(summary, "<form class=\"dte-legal-form\"")
        self.assertEqual(refused.status_code, 403)

    def test_demo_opens_fictitious_dte_detail_without_provider_or_usage(self) -> None:
        self.organization.is_demo = True
        self.organization.save(update_fields=["is_demo"])
        self.membership.role = Membership.Role.OWNER
        self.membership.save(update_fields=["role"])
        message = DteMessage.objects.create(
            organization=self.organization,
            company=self.company,
            source_isn="DEMO-001",
            subject="Aviso fictício",
        )
        url = reverse("hub:dte-message-detail", args=[message.id])
        with patch("apps.hub.views.open_message") as provider, patch(
            "apps.hub.views.quote_usage"
        ) as usage:
            before = self.client.get(url)
            opened = self.client.post(url, {"confirm_legal_notice": "on"}, follow=True)
        self.assertContains(before, "Abrir teor fictício")
        self.assertContains(opened, "nenhuma ciência oficial foi registrada")
        self.assertContains(opened, "Mensagem fictícia para Empresa DTE")
        provider.assert_not_called()
        usage.assert_not_called()
        access = DteMessageAccess.objects.get(message=message)
        self.assertEqual(access.status, DteMessageAccess.Status.OPENED)
        self.assertTrue(access.provider_request_id.startswith("DEMO-"))

    def test_uncertain_opening_is_separate_from_actionable_unread_messages(self) -> None:
        actionable = DteMessage.objects.create(
            organization=self.organization,
            company=self.company,
            source_isn="0000082841",
            subject="Mensagem ainda a abrir",
        )
        uncertain = DteMessage.objects.create(
            organization=self.organization,
            company=self.company,
            source_isn="0000082842",
            subject="Mensagem com retorno incerto",
        )
        in_progress = DteMessage.objects.create(
            organization=self.organization,
            company=self.company,
            source_isn="0000082843",
            subject="Mensagem em andamento",
        )
        science_recorded = DteMessage.objects.create(
            organization=self.organization,
            company=self.company,
            source_isn="0000082844",
            subject="Mensagem com ciência no Serpro",
            source_science_at=timezone.now(),
        )
        DteMessageAccess.objects.create(
            organization=self.organization,
            message=uncertain,
            status=DteMessageAccess.Status.UNKNOWN,
        )
        DteMessageAccess.objects.create(
            organization=self.organization,
            message=in_progress,
            status=DteMessageAccess.Status.READING,
        )

        all_messages = self.client.get(reverse("hub:dte-center"))
        self.assertEqual(all_messages.context["dte_stats"]["unread"], 1)
        self.assertEqual(all_messages.context["dte_stats"]["uncertain"], 2)
        self.assertContains(all_messages, "Ciência a conferir")
        self.assertContains(all_messages, "Abertura em andamento")

        to_open = self.client.get(reverse("hub:dte-center"), {"status": "unread"})
        self.assertContains(to_open, actionable.subject)
        for blocked in (uncertain, in_progress, science_recorded):
            self.assertNotContains(to_open, blocked.subject)

        to_confirm = self.client.get(reverse("hub:dte-center"), {"status": "uncertain"})
        self.assertContains(to_confirm, uncertain.subject)
        self.assertContains(to_confirm, in_progress.subject)
        self.assertNotContains(to_confirm, actionable.subject)
        self.assertNotContains(to_confirm, science_recorded.subject)

        consulted = self.client.get(reverse("hub:dte-center"), {"status": "read"})
        self.assertContains(consulted, science_recorded.subject)
        self.assertNotContains(consulted, uncertain.subject)

        empty_filter = self.client.get(
            reverse("hub:dte-center"), {"status": "uncertain", "q": "semresultado"}
        )
        self.assertContains(empty_filter, "Revise os filtros")
        self.assertNotContains(
            empty_filter, "A conexão central precisa ser configurada e homologada pela Mewstack"
        )

    def test_operator_with_explicit_science_permission_reaches_configuration_gate(self) -> None:
        self.membership.can_acknowledge_dte = True
        self.membership.save(update_fields=["can_acknowledge_dte"])
        message = DteMessage.objects.create(
            organization=self.organization,
            company=self.company,
            source_isn="0000082840",
            subject="Mensagem com ciência controlada",
        )

        response = self.client.post(
            reverse("hub:dte-message-detail", args=[message.id]),
            {"confirm_legal_notice": "on"},
            follow=True,
        )

        self.assertRedirects(response, reverse("hub:dte-message-detail", args=[message.id]))
        self.assertContains(response, "A conexão central Serpro ainda não está configurada")

        self.membership.role = Membership.Role.MANAGER
        self.membership.save(update_fields=["role"])
        refused = self.client.post(
            reverse("hub:dte-message-detail", args=[message.id]),
            {"confirm_legal_notice": "on"},
        )
        self.assertEqual(refused.status_code, 403)
