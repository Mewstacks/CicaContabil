"""AC-11.4 (parte): CNPJ alfanumérico reconhecido pela extração da triagem."""

from __future__ import annotations

from apps.hub.models import ClientCompany
from apps.triage.extraction import extract_item
from triage_v2_support import TriageV2Case, alnum_cnpj, mask_cnpj


class AlphanumericCnpjExtractionTests(TriageV2Case):
    def setUp(self) -> None:
        super().setUp()
        self.alnum = alnum_cnpj("12ABC34501DE")
        self.alnum_company = ClientCompany.objects.create(
            organization=self.office,
            name="Oficina Letra",
            cnpj_masked=mask_cnpj(self.alnum),
            dominio_code="900",
        )

    def test_fixture_is_a_valid_alphanumeric_cnpj(self) -> None:
        from apps.common.cnpj import normalize_cnpj

        self.assertEqual(normalize_cnpj(mask_cnpj(self.alnum)), self.alnum)

    def test_formatted_alphanumeric_cnpj_in_the_text_finds_the_company(self) -> None:
        payload = f"<doc><cnpj>{mask_cnpj(self.alnum)}</cnpj></doc>".encode()
        item = extract_item(item_id=self.released(filename="doc.xml", payload=payload).pk)
        self.assertEqual(item.company, self.alnum_company)
        self.assertEqual(item.ai_fields["Empresa"]["evidencia"], "CNPJ no conteúdo")

    def test_unformatted_alphanumeric_cnpj_in_the_text_finds_the_company(self) -> None:
        payload = f"<doc><cnpj>{self.alnum}</cnpj></doc>".encode()
        item = extract_item(item_id=self.released(filename="doc2.xml", payload=payload).pk)
        self.assertEqual(item.company, self.alnum_company)

    def test_lowercase_letters_still_match(self) -> None:
        payload = f"<doc>cnpj: {self.alnum.lower()}</doc>".encode()
        item = extract_item(item_id=self.released(filename="doc3.xml", payload=payload).pk)
        self.assertEqual(item.company, self.alnum_company)

    def test_numeric_cnpj_keeps_working(self) -> None:
        payload = b"<doc><cnpj>12.345.678/0001-95</cnpj></doc>"
        item = extract_item(item_id=self.released(filename="doc4.xml", payload=payload).pk)
        self.assertEqual(item.company, self.company)

    def test_alphanumeric_string_with_bad_check_digits_never_matches(self) -> None:
        wrong = self.alnum[:-1] + str((int(self.alnum[-1]) + 1) % 10)
        payload = f"<doc><cnpj>{wrong}</cnpj></doc>".encode()
        item = extract_item(item_id=self.released(filename="doc5.xml", payload=payload).pk)
        self.assertIsNone(item.company)

    def test_a_longer_token_containing_the_cnpj_does_not_match(self) -> None:
        payload = f"<doc>X{self.alnum}Y</doc>".encode()
        item = extract_item(item_id=self.released(filename="doc6.xml", payload=payload).pk)
        self.assertIsNone(item.company)

    def test_two_companies_in_the_same_text_stay_ambiguous(self) -> None:
        payload = f"<doc>{self.alnum} 12.345.678/0001-95</doc>".encode()
        item = extract_item(item_id=self.released(filename="doc7.xml", payload=payload).pk)
        self.assertIsNone(item.company)

    def test_other_office_company_is_never_matched(self) -> None:
        other = self.make_office("e11-other")
        ClientCompany.objects.create(
            organization=other, name="Outra", cnpj_masked=mask_cnpj(alnum_cnpj("98ZYX76501QR"))
        )
        payload = f"<doc>{alnum_cnpj('98ZYX76501QR')}</doc>".encode()
        item = extract_item(item_id=self.released(filename="doc8.xml", payload=payload).pk)
        self.assertIsNone(item.company)
