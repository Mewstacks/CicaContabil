"""AC-11.8 e AC-11.9: Pendências por remetente, painel, por quê, lote, escopo e isolamento."""

from __future__ import annotations

from typing import Any

from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ClientCompany, CompanyAccessGrant, ProductModule
from apps.organizations.models import Membership
from apps.triage.extraction import extract_item
from apps.triage.ingest import receive_email_attachment
from apps.triage.models import DocumentType, ExtractionRule, SenderRule, TriageItem
from apps.triage.security import scan_quarantined_item
from apps.triage.transitions import TriageStatus
from triage_v2_support import CleanScanner, TriageV2Case

CNPJ = "12.345.678/0001-95"


class InboxCase(TriageV2Case):
    databases = {"default", "knowledge"}
    counter = 0

    def setUp(self) -> None:
        super().setUp()
        self.type = DocumentType.objects.create(
            organization=self.office,
            code="extrato",
            label="Extrato",
            name_template="{codigo}_E_{periodo}",
            period_kind="competencia",
            keywords=["saldo anterior"],
        )
        self.login()
        self.url = reverse("hub:triage-inbox")

    def pending(
        self, body: str = "", *, sender: str = "a@padaria.example", office: Any = None
    ) -> TriageItem:
        InboxCase.counter += 1
        mailbox = self.mailbox if office is None else self.make_mailbox(office)
        item = receive_email_attachment(
            mailbox=mailbox,
            message_id=f"in{InboxCase.counter}",
            part_id="1",
            filename=f"doc{InboxCase.counter}.csv",
            payload=f"{body}\n#{InboxCase.counter}\n".encode(),
            sender=sender,
            received_at=timezone.now(),
        ).item
        scan_quarantined_item(item=item, scanner=CleanScanner())
        return extract_item(item_id=item.pk)

    def operator(self) -> User:
        user = User.objects.create_user("op-in@office.test", "safe-password-123")
        membership = Membership.objects.create(
            organization=self.office, user=user, role=Membership.Role.OPERATOR
        )
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=membership,
            company=self.company,
            modules=[ProductModule.Code.TRIAGE],
            capabilities=["read", "write"],
        )
        return user

    def complete(self, item: TriageItem) -> TriageItem:
        item.company = self.company
        item.document_type = self.type
        item.period_label = "2026-09"
        item.final_name = "417_E_202609.csv"
        item.save()
        return item

    def approve_url(self, item: TriageItem) -> str:
        return reverse("hub:triage-inbox-approve", args=[item.pk])


class InboxPageTests(InboxCase):
    def test_groups_by_sender_and_orders_least_confident_first(self) -> None:
        sure = self.pending(f"CNPJ {CNPJ}", sender="sure@x.example")
        unsure = self.pending("sem pista", sender="unsure@x.example")
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertContains(response, "unsure@x.example")
        self.assertContains(response, "sure@x.example")
        self.assertLess(content.index(unsure.original_name), content.index(sure.original_name))

    def test_selected_item_panel_shows_fields_and_why(self) -> None:
        item = self.pending(f"CNPJ {CNPJ} saldo anterior")
        response = self.client.get(self.url, {"item": str(item.pk)})
        self.assertContains(response, "CNPJ no conteúdo")
        self.assertContains(response, 'name="period_label"')
        self.assertContains(response, self.approve_url(item))

    def test_pdf_items_get_the_embedded_reader(self) -> None:
        item = self.pending("x")
        TriageItem.objects.filter(pk=item.pk).update(original_name="doc.pdf")
        response = self.client.get(self.url, {"item": str(item.pk)})
        self.assertContains(response, reverse("hub:triage-preview", args=[item.pk]))

    def test_shortcuts_and_script_are_present(self) -> None:
        item = self.pending("x")
        response = self.client.get(self.url, {"item": str(item.pk)})
        self.assertContains(response, "triage-inbox.js")
        self.assertContains(response, "<kbd>")
        self.assertContains(response, "data-shortcut")

    def test_empty_state_has_a_way_out(self) -> None:
        response = self.client.get(self.url)
        self.assertContains(response, reverse("hub:triage-upload"))

    def test_filter_without_result_offers_clear(self) -> None:
        self.pending("x")
        response = self.client.get(self.url, {"remetente": "ninguem@nada.example"})
        self.assertContains(response, "Limpar")

    def test_other_offices_items_never_appear(self) -> None:
        other = self.make_office("e11-in-other")
        secret = self.pending("segredo", office=other)
        self.assertNotContains(self.client.get(self.url), secret.original_name)

    def test_operator_sees_only_granted_companies_and_no_unassigned(self) -> None:
        mine = self.complete(self.pending("mine", sender="m@x.example"))
        outside = ClientCompany.objects.create(
            organization=self.office, name="Fora", dominio_code="77"
        )
        theirs = self.pending("theirs", sender="t@x.example")
        TriageItem.objects.filter(pk=theirs.pk).update(company=outside)
        unassigned = self.pending("none", sender="u@x.example")
        self.login(self.operator())
        content = self.client.get(self.url).content.decode()
        self.assertIn(mine.original_name, content)
        self.assertNotIn(theirs.original_name, content)
        self.assertNotIn(unassigned.original_name, content)

    def test_selecting_an_item_outside_the_scope_is_a_404(self) -> None:
        other = self.make_office("e11-in-other2")
        foreign = self.pending("x", office=other)
        self.assertEqual(self.client.get(self.url, {"item": str(foreign.pk)}).status_code, 404)

    def test_module_and_login_are_required(self) -> None:
        ProductModule.objects.filter(organization=self.office).update(enabled=False)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)


class InboxActionTests(InboxCase):
    def fields(self, **over: Any) -> dict[str, Any]:
        data = {
            "company": str(self.company.pk),
            "document_type": str(self.type.pk),
            "period_label": "2026-09",
            "counterparty_token": "",
            "final_name": "417_E_202609.csv",
            "reason": "",
        }
        data.update(over)
        return data

    def test_approve_saves_the_fields_decides_and_goes_to_the_next(self) -> None:
        first = self.pending(f"CNPJ {CNPJ}", sender="a@x.example")
        second = self.pending("outro", sender="b@x.example")
        response = self.client.post(self.approve_url(first), self.fields())
        first.refresh_from_db()
        self.assertEqual(first.status, TriageStatus.READY_TO_ARCHIVE)
        self.assertEqual(first.document_type, self.type)
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(second.pk), response["Location"])

    def test_approving_counts_toward_the_sender_rule(self) -> None:
        item = self.pending(f"CNPJ {CNPJ}", sender="rule@x.example")
        self.client.post(self.approve_url(item), self.fields())
        self.assertEqual(len(SenderRule.objects.get(sender="rule@x.example").confirmed_items), 1)

    def test_approve_without_company_or_type_is_refused(self) -> None:
        item = self.pending("sem pista")
        response = self.client.post(
            self.approve_url(item), self.fields(company="", document_type="")
        )
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(response.status_code, 302)

    def test_company_of_another_office_is_refused(self) -> None:
        other = self.make_office("e11-in-act-other")
        stranger = ClientCompany.objects.create(organization=other, name="Z", dominio_code="2")
        item = self.pending("x")
        self.client.post(self.approve_url(item), self.fields(company=str(stranger.pk)))
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertIsNone(item.company)

    def test_item_of_another_office_is_a_404_and_untouched(self) -> None:
        other = self.make_office("e11-in-act-other2")
        foreign = self.pending("x", office=other)
        response = self.client.post(self.approve_url(foreign), self.fields())
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.status, TriageStatus.AWAITING_REVIEW)

    def test_reject_needs_a_reason(self) -> None:
        item = self.pending("x")
        url = reverse("hub:triage-inbox-reject", args=[item.pk])
        self.client.post(url, {"reason": ""})
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.client.post(url, {"reason": "Documento ilegível"})
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.REJECTED)
        self.assertEqual(item.rejection_reason, "Documento ilegível")

    def test_operator_cannot_act_outside_the_grant(self) -> None:
        outside = ClientCompany.objects.create(
            organization=self.office, name="Fora", dominio_code="77"
        )
        item = self.pending("x")
        TriageItem.objects.filter(pk=item.pk).update(company=outside)
        self.login(self.operator())
        self.assertEqual(self.client.post(self.approve_url(item), self.fields()).status_code, 404)

    def test_demo_office_refuses_actions(self) -> None:
        item = self.pending("x")
        self.office.is_demo = True
        self.office.save()
        self.assertEqual(self.client.post(self.approve_url(item), self.fields()).status_code, 403)

    def test_get_is_not_allowed_on_actions(self) -> None:
        item = self.pending("x")
        self.assertEqual(self.client.get(self.approve_url(item)).status_code, 405)


class InboxBatchTests(InboxCase):
    def batch(self, action: str, items: list[TriageItem], **extra: Any) -> Any:
        data = {"action": action, "ids": [str(i.pk) for i in items], **extra}
        return self.client.post(reverse("hub:triage-inbox-batch"), data)

    def test_batch_approves_only_complete_items_and_reports(self) -> None:
        ready = self.complete(self.pending("a", sender="a@x.example"))
        incomplete = self.pending("b", sender="b@x.example")
        response = self.batch("approve", [ready, incomplete])
        ready.refresh_from_db()
        incomplete.refresh_from_db()
        self.assertEqual(ready.status, TriageStatus.READY_TO_ARCHIVE)
        self.assertEqual(incomplete.status, TriageStatus.AWAITING_REVIEW)
        follow = self.client.get(response["Location"])
        self.assertContains(follow, "1 aprovado")
        self.assertContains(follow, "1 sem dados completos")

    def test_batch_reject_needs_a_reason_and_applies_to_all(self) -> None:
        one, two = self.pending("a"), self.pending("b")
        self.batch("reject", [one, two])
        one.refresh_from_db()
        self.assertEqual(one.status, TriageStatus.AWAITING_REVIEW)
        self.batch("reject", [one, two], reason="Fora de escopo")
        one.refresh_from_db()
        two.refresh_from_db()
        self.assertEqual((one.status, two.status), (TriageStatus.REJECTED, TriageStatus.REJECTED))

    def test_batch_never_touches_other_offices_or_scopes(self) -> None:
        other = self.make_office("e11-in-batch-other")
        foreign = self.pending("x", office=other)
        TriageItem.objects.filter(pk=foreign.pk).update(
            company=ClientCompany.objects.create(organization=other, name="Q", dominio_code="3"),
            document_type=DocumentType.objects.create(
                organization=other,
                code="t",
                label="T",
                name_template="{codigo}",
                period_kind="competencia",
            ),
            period_label="2026-09",
            final_name="x.csv",
        )
        mine = self.complete(self.pending("m"))
        self.batch("approve", [foreign, mine])
        foreign.refresh_from_db()
        self.assertEqual(foreign.status, TriageStatus.AWAITING_REVIEW)

    def test_batch_limits_and_empty_selection(self) -> None:
        response = self.batch("approve", [])
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            reverse("hub:triage-inbox-batch"),
            {"action": "approve", "ids": ["x"] * 200},
        )
        self.assertEqual(response.status_code, 302)

    def test_operator_batch_cannot_reach_items_outside_the_grant(self) -> None:
        outside = ClientCompany.objects.create(
            organization=self.office, name="Fora", dominio_code="77"
        )
        item = self.complete(self.pending("x"))
        TriageItem.objects.filter(pk=item.pk).update(company=outside)
        self.login(self.operator())
        self.batch("approve", [item])
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)


class InboxRuleTests(InboxCase):
    def rule_url(self, item: TriageItem) -> str:
        return reverse("hub:triage-inbox-rule", args=[item.pk])

    def test_selection_becomes_a_field_rule(self) -> None:
        item = self.pending("Cliente: Padaria Sol Ltda\nresto")
        self.client.post(
            self.rule_url(item),
            {"selected_text": "Padaria Sol Ltda", "company": str(self.company.pk)},
        )
        rule = ExtractionRule.objects.get()
        self.assertEqual(
            (rule.mode, rule.anchor, rule.company), ("dois_pontos", "Cliente", self.company)
        )
        self.assertEqual(rule.source_item_id, item.pk)

    def test_text_not_in_the_document_creates_nothing(self) -> None:
        item = self.pending("Cliente: Padaria Sol Ltda")
        self.client.post(
            self.rule_url(item),
            {"selected_text": "inventado aqui", "company": str(self.company.pk)},
        )
        self.assertFalse(ExtractionRule.objects.exists())

    def test_company_of_another_office_is_refused(self) -> None:
        other = self.make_office("e11-in-rule-other")
        stranger = ClientCompany.objects.create(organization=other, name="W", dominio_code="4")
        item = self.pending("Cliente: Padaria Sol Ltda")
        self.client.post(
            self.rule_url(item), {"selected_text": "Padaria Sol Ltda", "company": str(stranger.pk)}
        )
        self.assertFalse(ExtractionRule.objects.exists())

    def test_operator_cannot_teach_rules(self) -> None:
        item = self.complete(self.pending("Cliente: Padaria Sol Ltda"))
        self.login(self.operator())
        response = self.client.post(
            self.rule_url(item),
            {"selected_text": "Padaria Sol Ltda", "company": str(self.company.pk)},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ExtractionRule.objects.exists())
