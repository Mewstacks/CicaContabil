"""AC-11.4/11.5: aprendizado por escritório, com isolamento total entre escritórios."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.hub.models import ClientCompany
from apps.triage import learning
from apps.triage.corrections import correct_archived
from apps.triage.extraction import extract_item
from apps.triage.ingest import receive_email_attachment
from apps.triage.models import (
    ChecklistEntry,
    DocumentType,
    ExtractionRule,
    LearnedLink,
    SenderRule,
    TriageItem,
)
from apps.triage.security import scan_quarantined_item
from apps.triage.services import archive_internal, decide_item, update_review_fields
from apps.triage.transitions import TriageStatus
from triage_v2_support import CleanScanner, TriageV2Case

CNPJ = "12.345.678/0001-95"


class LearningCase(TriageV2Case):
    counter = 0

    def setUp(self) -> None:
        super().setUp()
        self.type = DocumentType.objects.create(
            organization=self.office,
            code="extrato",
            label="Extrato",
            name_template="{codigo}_E_{periodo}",
            period_kind="competencia",
        )

    def approve(self, item: TriageItem) -> TriageItem:
        """A person confirms the item: the only moment anything is learned."""
        item = update_review_fields(
            item=item,
            actor=self.owner,
            company=item.company,
            document_type=self.type,
            period_label="2026-09",
            counterparty_token="",
            final_name="x.xml",
        )
        return decide_item(item=item, actor=self.owner, decision="archive", reason="")

    def mail(
        self,
        body: str,
        *,
        sender: str,
        message: str,
        mailbox: Any = None,
        raw: bool = False,
        suffix: str | None = None,
    ) -> TriageItem:
        LearningCase.counter += 1
        number = LearningCase.counter
        ext, payload = (
            (suffix or ".csv", f"{body}\n#{number}\n".encode())
            if raw
            else (".xml", f"<a>{body} #{number}</a>".encode())
        )
        item = receive_email_attachment(
            mailbox=mailbox or self.mailbox,
            message_id=message,
            part_id=str(number),
            filename=f"doc{number}{ext}",
            payload=payload,
            sender=sender,
            received_at=timezone.now(),
        ).item
        scan_quarantined_item(item=item, scanner=CleanScanner())
        return extract_item(item_id=item.pk)


class SenderLinkTests(LearningCase):
    def teach(self, emails: int, per_email: int = 1, sender: str = "ana@padaria.example") -> None:
        for number in range(emails):
            message = f"m{sender}{number}-{LearningCase.counter}"
            for _ in range(per_email):
                self.approve(self.mail(f"CNPJ {CNPJ}", sender=sender, message=message))

    def test_three_emails_and_three_files_activate_the_sender_link(self) -> None:
        self.teach(2)
        self.assertEqual(
            learning.active_link_companies(self.office, "sender", "ana@padaria.example"), []
        )
        self.teach(3)
        self.assertEqual(
            learning.active_link_companies(self.office, "sender", "ana@padaria.example"),
            [self.company],
        )

    def test_three_files_in_one_email_are_not_three_emails(self) -> None:
        self.teach(1, per_email=3)
        self.assertEqual(
            learning.active_link_companies(self.office, "sender", "ana@padaria.example"), []
        )

    def test_replaying_the_same_item_never_double_counts(self) -> None:
        item = self.mail(f"CNPJ {CNPJ}", sender="r@padaria.example", message="m-r")
        for _ in range(3):
            learning.record_hard_proof(item, self.company)
        link = LearnedLink.objects.get(key="r@padaria.example")
        self.assertEqual(link.proofs.count(), 1)

    def test_a_later_document_without_proof_is_identified_by_the_sender(self) -> None:
        self.teach(3)
        item = self.mail("sem identificação", sender="ana@padaria.example", message="m-new")
        self.assertEqual(item.company, self.company)
        self.assertEqual(item.ai_fields["Empresa"]["evidencia"], "Remetente conhecido")

    def test_activation_reclassifies_what_was_pending(self) -> None:
        self.teach(2)
        waiting = self.mail("sem identificação", sender="ana@padaria.example", message="m-wait")
        self.assertIsNone(waiting.company)
        self.teach(1)
        waiting.refresh_from_db()
        self.assertEqual(waiting.company, self.company)
        self.assertTrue(waiting.events.filter(note__startswith="Reclassificado").exists())

    def test_a_person_s_correction_is_never_overwritten_by_reclassification(self) -> None:
        self.teach(2)
        other = ClientCompany.objects.create(
            organization=self.office, name="Outra", dominio_code="9"
        )
        waiting = self.mail("sem identificação", sender="ana@padaria.example", message="m-p")
        waiting = update_review_fields(
            item=waiting,
            actor=self.owner,
            company=other,
            document_type=None,
            period_label="",
            counterparty_token="",
            final_name="",
        )
        self.teach(1)
        waiting.refresh_from_db()
        self.assertEqual(waiting.company, other)

    def test_learning_in_one_office_never_changes_another(self) -> None:
        other_office = self.make_office("e11-learn-other")
        other_box = self.make_mailbox(other_office)
        stranger = ClientCompany.objects.create(
            organization=other_office, name="Estranha", dominio_code="1", cnpj_masked=CNPJ
        )
        self.teach(3)
        item = self.mail(
            "sem identificação", sender="ana@padaria.example", message="m-x", mailbox=other_box
        )
        self.assertIsNone(item.company)
        self.assertEqual(
            learning.active_link_companies(other_office, "sender", "ana@padaria.example"), []
        )
        self.assertFalse(
            LearnedLink.objects.filter(organization=other_office, company=stranger).exists()
        )

    def test_foreign_company_is_refused_by_the_model(self) -> None:
        other_office = self.make_office("e11-learn-other2")
        stranger = ClientCompany.objects.create(
            organization=other_office, name="Z", dominio_code="2"
        )
        link = LearnedLink(
            organization=self.office, kind="sender", key="k@x.example", company=stranger
        )
        with self.assertRaises(ValidationError):
            link.clean()


class AccountLinkTests(LearningCase):
    def ofx(self, with_cnpj: bool, message: str, *, approve: bool = False) -> TriageItem:
        text = "<OFX><BANKID>0001</BANKID><ACCTID>12345-6</ACCTID>"
        text += f"CNPJ {CNPJ}" if with_cnpj else ""
        item = self.mail(
            text + "</OFX>", sender="banco@x.example", message=message, raw=True, suffix=".ofx"
        )
        return self.approve(item) if approve else item

    def test_two_approved_proofs_teach_the_account(self) -> None:
        self.ofx(True, "o1", approve=True)
        self.assertEqual(learning.active_link_companies(self.office, "account", "1:12345-6"), [])
        self.ofx(True, "o2", approve=True)
        self.assertEqual(
            learning.active_link_companies(self.office, "account", "1:12345-6"), [self.company]
        )
        later = self.ofx(False, "o3")
        self.assertEqual(later.company, self.company)
        self.assertEqual(later.ai_fields["Empresa"]["evidencia"], "Conta bancária conhecida")

    def test_nothing_is_learned_before_a_person_approves(self) -> None:
        self.ofx(True, "p1")
        self.ofx(True, "p2")
        self.assertFalse(LearnedLink.objects.exists())

    def test_account_tags_in_a_non_ofx_file_never_count(self) -> None:
        for number in range(3):
            body = "<OFX><BANKID>0001</BANKID><ACCTID>12345-6</ACCTID></OFX>"
            self.approve(
                self.mail(f"CNPJ {CNPJ} {body}", sender="b@x.example", message=f"x{number}")
            )
        self.assertFalse(LearnedLink.objects.filter(kind="account").exists())


class PoisoningTests(LearningCase):
    def test_extraction_alone_never_teaches_a_sender_link(self) -> None:
        for number in range(4):
            self.mail(f"CNPJ {CNPJ}", sender="evil@x.example", message=f"e{number}")
        self.assertFalse(LearnedLink.objects.exists())

    def test_auto_approved_items_never_teach(self) -> None:
        item = self.mail(f"CNPJ {CNPJ}", sender="auto@x.example", message="au1")
        TriageItem.objects.filter(pk=item.pk).update(auto_decision="auto")
        item.refresh_from_db()
        self.assertFalse(learning.learn_from_approval(item))
        self.assertFalse(LearnedLink.objects.exists())

    def test_outside_sender_cannot_name_an_author_in_the_body(self) -> None:
        item = self.mail("x", sender="stranger@evil.example", message="f1")
        TriageItem.objects.filter(pk=item.pk).update(original_sender="victim@padaria.example")
        item.refresh_from_db()
        self.assertEqual(learning.item_sender_keys(item), ["stranger@evil.example"])

    def test_a_colleague_domain_alone_is_not_staff(self) -> None:
        item = self.mail("x", sender="colega@e11-office.test", message="f3")
        TriageItem.objects.filter(pk=item.pk).update(original_sender="victim@padaria.example")
        item.refresh_from_db()
        self.assertEqual(learning.item_sender_keys(item), ["colega@e11-office.test"])

    def test_staff_forward_uses_the_original_author(self) -> None:
        item = self.mail("x", sender="owner-e11@office.test", message="f2")
        TriageItem.objects.filter(pk=item.pk).update(original_sender="cliente@padaria.example")
        item.refresh_from_db()
        self.assertEqual(
            learning.item_sender_keys(item), ["cliente@padaria.example", "owner-e11@office.test"]
        )


class SenderRuleTests(LearningCase):
    def approve(self, sender: str, message: str) -> TriageItem:
        item = self.mail("conteudo livre", sender=sender, message=message)
        item = update_review_fields(
            item=item,
            actor=self.owner,
            company=self.company,
            document_type=self.type,
            period_label="2026-09",
            counterparty_token="",
            final_name="x.xml",
        )
        item = decide_item(item=item, actor=self.owner, decision="archive", reason="")
        return item

    def test_three_confirmations_activate_the_rule(self) -> None:
        for number in range(2):
            self.approve("fixo@padaria.example", f"s{number}")
        early = self.mail("conteudo livre", sender="fixo@padaria.example", message="s-early")
        self.assertIsNone(early.document_type)
        self.approve("fixo@padaria.example", "s2")
        late = self.mail("conteudo livre", sender="fixo@padaria.example", message="s-late")
        self.assertEqual(late.document_type, self.type)
        self.assertIn("remetente", late.ai_fields["Tipo"]["evidencia"])

    def test_confirming_the_same_item_twice_counts_once(self) -> None:
        item = self.approve("dup@padaria.example", "d1")
        learning.confirm_sender_rule(item)
        learning.confirm_sender_rule(item)
        self.assertEqual(
            len(SenderRule.objects.get(sender="dup@padaria.example").confirmed_items), 1
        )

    def test_rule_of_one_office_never_applies_to_another(self) -> None:
        other_office = self.make_office("e11-rule-other")
        for number in range(3):
            self.approve("fixo@padaria.example", f"o{number}")
        item = self.mail(
            "conteudo livre",
            sender="fixo@padaria.example",
            message="o-x",
            mailbox=self.make_mailbox(other_office),
        )
        self.assertIsNone(item.document_type)


class FieldRuleTests(LearningCase):
    TEXT = "Relatório\nCliente: Padaria Sol Ltda\nPeríodo: 09/2026\n"

    def item(self, text: str) -> TriageItem:
        return self.mail(text, sender="s@x.example", message=f"f{len(text)}-{text[:3]}", raw=True)

    def test_selection_after_a_label_becomes_a_colon_rule_and_fires_next_time(self) -> None:
        item = self.item("x")
        rule = learning.create_field_rule(
            item=item, company=self.company, selected="Padaria Sol Ltda", text=self.TEXT
        )
        self.assertEqual((rule.mode, rule.anchor), ("dois_pontos", "Cliente"))
        got = self.item("Cliente: Padaria Sol Ltda\nresto")
        self.assertEqual(got.company, self.company)
        self.assertTrue(got.ai_fields["Empresa"]["evidencia"].startswith("Regra de campo"))

    def test_rule_does_not_fire_for_another_value_under_the_same_label(self) -> None:
        learning.create_field_rule(
            item=self.item("y"), company=self.company, selected="Padaria Sol Ltda", text=self.TEXT
        )
        self.assertIsNone(self.item("Cliente: Mercado Lua Ltda").company)

    def test_selection_alone_on_a_line_uses_the_previous_line_as_anchor(self) -> None:
        text = "Razão social do tomador\nPadaria Sol Ltda\n"
        rule = learning.create_field_rule(
            item=self.item("z"), company=self.company, selected="Padaria Sol Ltda", text=text
        )
        self.assertEqual((rule.mode, rule.anchor), ("linha_seguinte", "Razão social do tomador"))
        got = self.item("Razão social do tomador\nPadaria Sol Ltda\n")
        self.assertEqual(got.company, self.company)

    def test_free_selection_becomes_a_contains_rule(self) -> None:
        text = "Documento emitido para a empresa Padaria Sol Ltda hoje"
        rule = learning.create_field_rule(
            item=self.item("w"), company=self.company, selected="Padaria Sol Ltda", text=text
        )
        self.assertEqual(rule.mode, "contem")

    def test_bad_selections_are_refused(self) -> None:
        item = self.item("v")
        for selected in ("ab", "123456", "x" * 300, "não está no texto"):
            with self.assertRaises(ValueError):
                learning.create_field_rule(
                    item=item, company=self.company, selected=selected, text=self.TEXT
                )

    def test_company_of_another_office_is_refused(self) -> None:
        other_office = self.make_office("e11-field-other")
        stranger = ClientCompany.objects.create(
            organization=other_office, name="Q", dominio_code="3"
        )
        with self.assertRaises(ValueError):
            learning.create_field_rule(
                item=self.item("u"), company=stranger, selected="Padaria Sol Ltda", text=self.TEXT
            )

    def test_rules_of_another_office_never_fire(self) -> None:
        other_office = self.make_office("e11-field-other2")
        stranger = ClientCompany.objects.create(
            organization=other_office, name="P", dominio_code="4"
        )
        ExtractionRule.objects.create(
            organization=other_office,
            mode="dois_pontos",
            anchor="Cliente",
            value="Padaria Sol Ltda",
            company=stranger,
        )
        self.assertIsNone(self.item("Cliente: Padaria Sol Ltda").company)


class CorrectionTests(LearningCase):
    def archived_item(self) -> TriageItem:
        document_type = self.type
        item = self.mail(f"CNPJ {CNPJ}", sender="err@padaria.example", message="c1")
        item = update_review_fields(
            item=item,
            actor=self.owner,
            company=self.company,
            document_type=document_type,
            period_label="2026-09",
            counterparty_token="",
            final_name="417_E_202609.xml",
        )
        decide_item(item=item, actor=self.owner, decision="archive", reason="")
        return archive_internal(item=item, actor=self.owner)

    def test_correcting_an_archived_company_blocks_the_wrong_link_and_moves_the_checklist(
        self,
    ) -> None:
        item = self.archived_item()
        for number in range(2, 5):
            self.approve(
                self.mail(f"CNPJ {CNPJ}", sender="err@padaria.example", message=f"c{number}")
            )
        self.assertEqual(
            learning.active_link_companies(self.office, "sender", "err@padaria.example"),
            [self.company],
        )
        right = ClientCompany.objects.create(
            organization=self.office, name="Certa", dominio_code="8"
        )
        corrected = correct_archived(
            item=item, actor=self.owner, company=right, reason="Empresa errada"
        )
        self.assertEqual(corrected.company, right)
        self.assertEqual(corrected.status, TriageStatus.ARCHIVED)
        self.assertTrue(
            LearnedLink.objects.get(key="err@padaria.example", company=self.company).blocked
        )
        self.assertEqual(
            learning.active_link_companies(self.office, "sender", "err@padaria.example"), []
        )
        self.assertFalse(
            ChecklistEntry.objects.filter(company=self.company, triage_item=item).exists()
        )
        self.assertTrue(ChecklistEntry.objects.filter(company=right, triage_item=item).exists())
        self.assertTrue(
            corrected.events.filter(note__startswith="Corrigido após arquivar").exists()
        )

    def test_reason_is_required_and_only_archived_items_qualify(self) -> None:
        item = self.archived_item()
        with self.assertRaises(ValidationError):
            correct_archived(item=item, actor=self.owner, company=self.company, reason="")
        pending = self.mail("x", sender="p@x.example", message="cp")
        with self.assertRaises(ValidationError):
            correct_archived(item=pending, actor=self.owner, company=self.company, reason="ok")

    def test_company_of_another_office_is_refused(self) -> None:
        item = self.archived_item()
        other_office = self.make_office("e11-corr-other")
        stranger = ClientCompany.objects.create(
            organization=other_office, name="K", dominio_code="5"
        )
        with self.assertRaises(ValidationError):
            correct_archived(item=item, actor=self.owner, company=stranger, reason="troca")

    def test_field_rule_born_from_the_corrected_item_is_switched_off(self) -> None:
        item = self.archived_item()
        rule = ExtractionRule.objects.create(
            organization=self.office,
            mode="contem",
            value="Padaria Sol Ltda",
            company=self.company,
            source_item=item,
        )
        right = ClientCompany.objects.create(
            organization=self.office, name="Certa2", dominio_code="7"
        )
        correct_archived(item=item, actor=self.owner, company=right, reason="errada")
        rule.refresh_from_db()
        self.assertFalse(rule.active)
