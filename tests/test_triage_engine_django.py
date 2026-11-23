"""AC-11.4: empresa por placar de sinais, limiar 100 e margem 50, provas duras divergentes."""

from __future__ import annotations

from typing import Any

from apps.hub.models import ClientCompany
from apps.triage.extraction import extract_item
from apps.triage.identification import ACCEPT_MARGIN, ACCEPT_SCORE, identify_company
from apps.triage.models import LearnedLink, LinkProof, TriagePolicy
from triage_v2_support import TriageV2Case, alnum_cnpj, mask_cnpj


def sources(**kw: str) -> dict[str, str]:
    base = {"nome": "", "assunto": "", "conteúdo": "", "corpo": ""}
    base.update(kw)
    return base


class ScoreboardTests(TriageV2Case):
    def setUp(self) -> None:
        super().setUp()
        self.other = ClientCompany.objects.create(
            organization=self.office,
            name="Mercado Lua Nova",
            cnpj_masked=mask_cnpj(alnum_cnpj("98ZYX76501QR")),
            dominio_code="533",
        )

    def identify(self, item: Any, **kw: str) -> Any:
        return identify_company(item, sources(**kw))

    def item(self, name: str = "doc.xml", **fields: Any) -> Any:
        item = self.released(filename=name, payload=f"<a>{name}</a>".encode())
        for key, value in fields.items():
            setattr(item, key, value)
        item.save()
        return item

    def test_thresholds_are_the_agreed_ones(self) -> None:
        self.assertEqual((ACCEPT_SCORE, ACCEPT_MARGIN), (100, 50))

    def test_cnpj_in_the_text_accepts_with_a_hard_proof(self) -> None:
        got = self.identify(self.item(), conteúdo="CNPJ 12.345.678/0001-95")
        self.assertEqual(got.status, "accepted")
        self.assertEqual(got.company, self.company)
        self.assertGreaterEqual(got.score, 100)
        self.assertEqual(got.signals[0].text, "CNPJ no conteúdo")

    def test_alphanumeric_cnpj_is_a_hard_proof_too(self) -> None:
        got = self.identify(self.item(), conteúdo=f"cnpj {alnum_cnpj('98ZYX76501QR')}")
        self.assertEqual(got.company, self.other)

    def test_two_hard_proofs_for_different_companies_go_to_a_person(self) -> None:
        got = self.identify(
            self.item(), conteúdo="12.345.678/0001-95", nome=f"{alnum_cnpj('98ZYX76501QR')}.pdf"
        )
        self.assertEqual(got.status, "conflict")
        self.assertIsNone(got.company)
        self.assertEqual(
            {s.company_id for s in got.signals if s.hard}, {self.company.pk, self.other.pk}
        )

    def test_domino_code_prefix_in_the_name_is_a_hard_proof(self) -> None:
        got = self.identify(self.item("417_extrato_2026-09.xml"), nome="417_extrato_2026-09.xml")
        self.assertEqual(got.company, self.company)
        self.assertEqual(got.signals[0].text, "Código Domínio no nome")

    def test_company_name_alone_is_not_enough(self) -> None:
        got = self.identify(self.item(), conteúdo="Extrato da empresa Padaria Sol Ltda")
        self.assertEqual(got.status, "weak")
        self.assertIsNone(got.company)
        self.assertEqual(got.candidates[0][0], self.company)

    def test_name_adds_to_other_signals(self) -> None:
        got = self.identify(self.item(), conteúdo="Padaria Sol 12.345.678/0001-95")
        self.assertGreater(got.score, 100)

    def test_learned_sender_alone_reaches_the_threshold(self) -> None:
        item = self.item(sender="contabil@padaria.example")
        link = LearnedLink.objects.create(
            organization=self.office,
            kind="sender",
            key="contabil@padaria.example",
            company=self.company,
        )
        for index in range(3):
            LinkProof.objects.create(
                organization=self.office,
                link=link,
                message_id=f"m{index}",
                content_hash=f"h{index}",
            )
        got = self.identify(item)
        self.assertEqual(got.status, "accepted")
        self.assertEqual(got.signals[0].text, "Remetente conhecido")

    def test_sender_link_below_three_emails_and_files_does_not_count(self) -> None:
        item = self.item(sender="x@padaria.example")
        link = LearnedLink.objects.create(
            organization=self.office, kind="sender", key="x@padaria.example", company=self.company
        )
        for index in range(2):
            LinkProof.objects.create(
                organization=self.office,
                link=link,
                message_id=f"m{index}",
                content_hash=f"h{index}",
            )
        self.assertEqual(self.identify(item).status, "none")

    def test_blocked_link_never_counts(self) -> None:
        item = self.item(sender="b@padaria.example")
        link = LearnedLink.objects.create(
            organization=self.office,
            kind="sender",
            key="b@padaria.example",
            company=self.company,
            blocked=True,
        )
        for index in range(3):
            LinkProof.objects.create(
                organization=self.office,
                link=link,
                message_id=f"m{index}",
                content_hash=f"h{index}",
            )
        self.assertEqual(self.identify(item).status, "none")

    def test_sender_link_against_a_cnpj_of_another_company_is_ambiguous(self) -> None:
        item = self.item(sender="c@x.example")
        link = LearnedLink.objects.create(
            organization=self.office, kind="sender", key="c@x.example", company=self.other
        )
        for index in range(3):
            LinkProof.objects.create(
                organization=self.office,
                link=link,
                message_id=f"m{index}",
                content_hash=f"h{index}",
            )
        got = self.identify(item, conteúdo="12.345.678/0001-95")
        self.assertEqual(got.status, "ambiguous")
        self.assertIsNone(got.company)

    def test_a_forwarded_original_sender_is_the_key(self) -> None:
        item = self.item(sender="ana@office.test", original_sender="cliente@padaria.example")
        link = LearnedLink.objects.create(
            organization=self.office,
            kind="sender",
            key="cliente@padaria.example",
            company=self.company,
        )
        for index in range(3):
            LinkProof.objects.create(
                organization=self.office,
                link=link,
                message_id=f"m{index}",
                content_hash=f"h{index}",
            )
        self.assertEqual(self.identify(item).company, self.company)

    def test_account_link_with_two_proofs_is_a_hard_proof(self) -> None:
        item = self.item()
        link = LearnedLink.objects.create(
            organization=self.office, kind="account", key="1:12345-6", company=self.company
        )
        for index in range(2):
            LinkProof.objects.create(
                organization=self.office,
                link=link,
                message_id=f"m{index}",
                content_hash=f"h{index}",
            )
        text = "<OFX><BANKID>001</BANKID><ACCTID>12345-6</ACCTID></OFX>"
        got = self.identify(item, conteúdo=text)
        self.assertEqual(got.company, self.company)
        self.assertTrue(got.signals[0].hard)

    def test_links_of_another_office_never_count(self) -> None:
        other_office = self.make_office("e11-engine-other")
        stranger = ClientCompany.objects.create(
            organization=other_office, name="Y", dominio_code="1"
        )
        link = LearnedLink.objects.create(
            organization=other_office, kind="sender", key="s@padaria.example", company=stranger
        )
        for index in range(3):
            LinkProof.objects.create(
                organization=other_office,
                link=link,
                message_id=f"m{index}",
                content_hash=f"h{index}",
            )
        item = self.item(sender="s@padaria.example")
        self.assertEqual(self.identify(item).status, "none")

    def test_scores_and_engine_version_are_persisted_by_extraction(self) -> None:
        TriagePolicy.objects.create(organization=self.office, engine_version=3)
        item = self.released(filename="e.xml", payload=b"<a>12.345.678/0001-95</a>")
        item = extract_item(item_id=item.pk)
        self.assertEqual(item.engine_version, 3)
        self.assertEqual(item.scores["company"]["status"], "accepted")
        self.assertGreaterEqual(item.scores["company"]["score"], 100)
        self.assertIn("margin", item.scores["company"])
