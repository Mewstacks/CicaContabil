from __future__ import annotations

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.triage.windows_paths import company_folder_component


class WindowsCompanyFolderTests(SimpleTestCase):
    def test_name_preserves_unicode_and_required_leading_zero_code(self) -> None:
        self.assertEqual(
            company_folder_component(company_name="São José Ltda.", dominio_code="0017"),
            "São José Ltda [Domínio 0017]",
        )

    def test_name_removes_windows_separators_and_controls_without_changing_code(self) -> None:
        component = company_folder_component(
            company_name="  Acme/Serviços: Fiscal\n ", dominio_code="A-07"
        )
        self.assertEqual(component, "Acme Serviços Fiscal [Domínio A-07]")
        self.assertNotIn("/", component)
        self.assertNotIn("\\", component)

    def test_invalid_or_absent_dominio_code_fails_before_any_path_is_made(self) -> None:
        for code in ("", " ", "..", " 001", "001/2026", "001\x00"):
            with self.subTest(code=code), self.assertRaises(ValidationError):
                company_folder_component(company_name="Acme", dominio_code=code)

    def test_long_name_is_bounded_in_windows_utf16_units(self) -> None:
        component = company_folder_component(
            company_name="Empresa " + "😀" * 140, dominio_code="001"
        )
        self.assertLessEqual(len(component.encode("utf-16-le")) // 2, 160)
        self.assertTrue(component.endswith(" [Domínio 001]"))

    def test_only_invalid_company_name_requires_correction(self) -> None:
        with self.assertRaises(ValidationError):
            company_folder_component(company_name="/\\:*?", dominio_code="001")
