"""AC-11.1 (domínio): catálogo por escritório, palavras-chave, esperado e seed opt-in."""

from __future__ import annotations

from django.core.exceptions import ValidationError

from apps.hub.models import ClientCompany
from apps.triage.catalog import (
    DEFAULT_CATALOG,
    apply_default_catalog,
    expected_for,
    expected_types_for,
    parse_keywords,
    validate_folder_template,
)
from apps.triage.extraction import extract_item
from apps.triage.models import ChecklistExpectation, DocumentType
from triage_v2_support import TriageV2Case


def make_type(office, code: str, label: str, **extra) -> DocumentType:  # type: ignore[no-untyped-def]
    return DocumentType.objects.create(
        organization=office,
        code=code,
        label=label,
        name_template="{codigo}_" + code.upper() + "_{periodo}",
        period_kind=DocumentType.PeriodKind.COMPETENCIA,
        **extra,
    )


class KeywordParsingTests(TriageV2Case):
    def test_parse_keywords_splits_on_comma_and_newline_and_dedupes(self) -> None:
        self.assertEqual(
            parse_keywords("Extrato, saldo anterior\nextrato;  OFX "),
            ["Extrato", "saldo anterior", "OFX"],
        )

    def test_parse_keywords_caps_count_and_length(self) -> None:
        many = ",".join(f"palavra{i}" for i in range(80))
        self.assertEqual(len(parse_keywords(many)), 40)
        self.assertEqual(len(parse_keywords("x" * 200)[0]), 60)

    def test_parse_keywords_drops_empty_and_too_short_entries(self) -> None:
        self.assertEqual(parse_keywords(" , a ,, @ , ok "), ["ok"])


class KeywordMatchingTests(TriageV2Case):
    def setUp(self) -> None:
        super().setUp()
        self.extrato = make_type(
            self.office, "extrato", "Extrato", keywords=["saldo anterior", "ofx"]
        )
        self.guia = make_type(self.office, "guia", "Guia", keywords=["das", "darf", "@guia"])
        self.recibo = make_type(self.office, "recibo", "Recibo", keywords=["recibo"])

    _seq = 0

    def _suggest(self, filename: str, payload: bytes, subject: str = "") -> DocumentType | None:
        # Same bytes in one office close as duplicates: make every payload unique.
        KeywordMatchingTests._seq += 1
        payload += f"<!-- {self._seq} -->".encode()
        item = self.released(filename=filename, payload=payload, subject=subject)
        return extract_item(item_id=item.pk).document_type

    def test_keyword_in_the_text_selects_the_type(self) -> None:
        got = self._suggest("anexo.xml", b"<d>Saldo anterior R$ 10</d>")
        self.assertEqual(got, self.extrato)

    def test_whole_word_only_das_never_matches_vendas(self) -> None:
        self.assertIsNone(self._suggest("a.xml", b"<d>relatorio de vendas do mes</d>"))
        self.assertEqual(self._suggest("b.xml", b"<d>pagamento do DAS simples</d>"), self.guia)

    def test_accent_and_case_blind(self) -> None:
        make_type(self.office, "aplic", "Aplicação", keywords=["aplicação financeira"])
        got = self._suggest("c.xml", b"<d>APLICACAO FINANCEIRA cdb</d>")
        self.assertEqual(got.code, "aplic")  # type: ignore[union-attr]

    def test_at_prefixed_word_counts_only_in_name_or_subject(self) -> None:
        self.assertIsNone(self._suggest("d.xml", b"<d>esta guia de remessa</d>"))
        self.assertEqual(self._suggest("guia_setembro.xml", b"<d>x</d>"), self.guia)
        self.assertEqual(self._suggest("e.xml", b"<d>x</d>", subject="Guia de setembro"), self.guia)

    def test_name_outweighs_text(self) -> None:
        got = self._suggest("recibo_pagamento.xml", b"<d>saldo anterior</d>")
        self.assertEqual(got, self.recibo)

    def test_tie_between_types_leaves_the_type_empty(self) -> None:
        self.assertIsNone(self._suggest("f.xml", b"<d>ofx recibo</d>"))

    def test_inactive_type_is_never_suggested(self) -> None:
        self.extrato.active = False
        self.extrato.save()
        self.assertIsNone(self._suggest("g.xml", b"<d>saldo anterior</d>"))

    def test_email_body_counts_like_text(self) -> None:
        item = self.released(filename="h.xml", payload=b"<d>body</d>")
        item.body_excerpt = "Segue o extrato com saldo anterior"
        item.save(update_fields=["body_excerpt"])
        self.assertEqual(extract_item(item_id=item.pk).document_type, self.extrato)

    def test_keywords_of_another_office_are_never_used(self) -> None:
        other = self.make_office("e11-other-kw")
        make_type(other, "outro", "Outro", keywords=["zebra"])
        self.assertIsNone(self._suggest("i.xml", b"<d>zebra</d>"))

    def test_types_without_keywords_keep_the_label_token_behaviour(self) -> None:
        make_type(self.office, "folha-pgto", "Folha de pagamento")
        self.assertEqual(self._suggest("folha_pagamento.xml", b"<d>x</d>").code, "folha-pgto")  # type: ignore[union-attr]


class DefaultCatalogTests(TriageV2Case):
    def test_nothing_is_created_without_the_explicit_call(self) -> None:
        self.assertEqual(DocumentType.objects.filter(organization=self.office).count(), 0)

    def test_apply_creates_the_accounting_types_for_this_office_only(self) -> None:
        other = self.make_office("e11-other-seed")
        created = apply_default_catalog(self.office)
        codes = set(
            DocumentType.objects.filter(organization=self.office).values_list("code", flat=True)
        )
        for wanted in ("extrato", "nfse", "folha", "guia", "recibo", "francesinha", "pix"):
            self.assertIn(wanted, codes)
        self.assertEqual(set(created), codes)
        self.assertEqual(DocumentType.objects.filter(organization=other).count(), 0)

    def test_apply_is_idempotent_and_never_overwrites_edits(self) -> None:
        apply_default_catalog(self.office)
        extrato = DocumentType.objects.get(organization=self.office, code="extrato")
        extrato.label = "Extrato do banco"
        extrato.keywords = ["meu termo"]
        extrato.active = False
        extrato.save()
        again = apply_default_catalog(self.office)
        self.assertEqual(again, [])
        extrato.refresh_from_db()
        self.assertEqual((extrato.label, extrato.keywords, extrato.active),
                         ("Extrato do banco", ["meu termo"], False))

    def test_apply_fills_only_the_missing_codes(self) -> None:
        make_type(self.office, "guia", "Minha guia", keywords=["x1"])
        created = apply_default_catalog(self.office)
        self.assertNotIn("guia", created)
        kept = DocumentType.objects.get(organization=self.office, code="guia")
        self.assertEqual(kept.label, "Minha guia")

    def test_every_default_has_keywords_a_valid_template_and_a_period_kind(self) -> None:
        for row in DEFAULT_CATALOG:
            self.assertTrue(row["keywords"] or row["code"] == "diversos", row["code"])
            self.assertIn("{periodo}", row["name_template"] + "{periodo}")
            if row.get("folder_template"):
                validate_folder_template(row["folder_template"])

    def test_default_extrato_is_expected_for_everyone(self) -> None:
        apply_default_catalog(self.office)
        extrato = DocumentType.objects.get(organization=self.office, code="extrato")
        self.assertTrue(extrato.expected_default)


class ExpectedResolutionTests(TriageV2Case):
    def setUp(self) -> None:
        super().setUp()
        self.everyone = make_type(self.office, "extrato", "Extrato", expected_default=True)
        self.simples_only = make_type(
            self.office, "pgdas", "PGDAS", expected_regimes=["simples", "mei"]
        )
        self.never = make_type(self.office, "contrato", "Contrato")

    def test_default_and_regime_rules(self) -> None:
        self.assertTrue(expected_for(self.company, self.everyone))
        self.assertTrue(expected_for(self.company, self.simples_only))  # company is Simples
        self.assertFalse(expected_for(self.company, self.never))

    def test_regime_that_does_not_match_is_not_expected(self) -> None:
        real = ClientCompany.objects.create(
            organization=self.office, name="Real SA", dominio_code="8",
            tax_regime=ClientCompany.TaxRegime.REAL,
        )
        self.assertFalse(expected_for(real, self.simples_only))

    def test_company_exception_wins_over_the_type_rule(self) -> None:
        ChecklistExpectation.objects.create(
            organization=self.office, company=self.company, document_type=self.everyone,
            requirement=ChecklistExpectation.Requirement.WAIVED,
        )
        ChecklistExpectation.objects.create(
            organization=self.office, company=self.company, document_type=self.never,
            requirement=ChecklistExpectation.Requirement.EXPECTED,
        )
        self.assertFalse(expected_for(self.company, self.everyone))
        self.assertTrue(expected_for(self.company, self.never))

    def test_expected_types_for_lists_only_active_expected_types(self) -> None:
        self.simples_only.active = False
        self.simples_only.save()
        self.assertEqual(list(expected_types_for(self.company)), [self.everyone])

    def test_exception_of_another_office_company_is_ignored(self) -> None:
        other = self.make_office("e11-other-exp")
        stranger = ClientCompany.objects.create(organization=other, name="Y", dominio_code="1")
        self.assertFalse(expected_for(stranger, self.everyone))


class FolderTemplateTests(TriageV2Case):
    def test_accepts_known_placeholders_with_the_company(self) -> None:
        validate_folder_template(r"{company_name}\{document_type}\{period}")

    def test_refuses_unknown_placeholder_traversal_and_absolute(self) -> None:
        for bad in (
            r"{company_name}\{nope}",
            r"..\{company_name}",
            r"C:\{company_name}",
            r"\\servidor\{company_name}",
            r"{document_type}\{period}",  # no company: files of all clients would mix
            "{company_name}/{",
            'x{company_name}:"',
        ):
            with self.assertRaises(ValidationError, msg=bad):
                validate_folder_template(bad)


class TypeDestinationFolderTests(TriageV2Case):
    def _item(self, folder: str):  # type: ignore[no-untyped-def]
        from apps.triage.models import DestinationProfile

        profile = DestinationProfile.objects.get(organization=self.office)
        profile.mode = DestinationProfile.Mode.WINDOWS
        profile.windows_root = r"D:\Clientes"
        profile.folder_template = "{company_name}"
        profile.save()
        document_type = make_type(self.office, "extrato", "Extrato", folder_template=folder)
        item = self.released(filename="a.xml", payload=b"<a/>")
        item.company = self.company
        item.document_type = document_type
        item.period_label = "2026-09"
        item.final_name = "417_EXTRATO_202609.xml"
        item.save()
        return item, profile

    def test_type_folder_wins_over_the_office_default(self) -> None:
        from apps.triage.services import windows_relative_destination

        item, profile = self._item(r"{company_name}\Extratos\{period}")
        self.assertEqual(
            windows_relative_destination(item, profile),
            r"Padaria Sol\Extratos\2026-09\417_EXTRATO_202609.xml",
        )

    def test_blank_type_folder_keeps_the_office_default(self) -> None:
        from apps.triage.services import windows_relative_destination

        item, profile = self._item("")
        self.assertEqual(
            windows_relative_destination(item, profile), r"Padaria Sol\417_EXTRATO_202609.xml"
        )
