from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.hub.models import ClientCompany, DominioBankEntry, OfficeProfile
from apps.intelligence.models import DominioCommunication, IntelligenceConnector
from apps.organizations.models import Organization


class FedrizziDominioSetupTests(TestCase):
    def test_setup_creates_the_local_test_office_idempotently(self) -> None:
        output = StringIO()

        call_command("setup_fedrizzi_dominio", stdout=output)
        call_command("setup_fedrizzi_dominio", stdout=output)

        office = Organization.objects.get(slug="fedrizzi-contabilidade")
        self.assertEqual(office.name, "Fedrizzi Contabilidade")
        self.assertTrue(OfficeProfile.objects.filter(organization=office).exists())
        self.assertTrue(
            IntelligenceConnector.objects.filter(
                organization=office, mode=IntelligenceConnector.Mode.DIRECT_ODBC
            ).exists()
        )
        self.assertIn("Nenhuma leitura ODBC", output.getvalue())

    def test_sync_requires_a_dsn(self) -> None:
        with self.assertRaisesRegex(CommandError, "Informe --dsn"):
            call_command("setup_fedrizzi_dominio", sync=True)

    @patch("apps.intelligence.management.commands.setup_fedrizzi_dominio.ReadOnlyDominoOdbc")
    def test_sync_uses_allowlisted_queries_and_mirrors_their_results(self, mocked_odbc) -> None:
        mocked_odbc.return_value.execute.side_effect = [
            [
                {
                    "codigo": "001",
                    "nome": "Empresa Domínio",
                    "cnpj_masked": "12.345.678/0001-90",
                }
            ],
            [
                {
                    "source_id": "7",
                    "company_code": "001",
                    "subject": "Prazo",
                    "type_code": "2",
                    "status_code": "1",
                    "is_read": 0,
                }
            ],
            [
                {
                    "source_id": "001|1|1",
                    "company_code": "001",
                    "occurred_on": "2026-08-31",
                    "description": "Recebimento",
                    "amount": "12.34",
                    "direction": "C",
                    "is_linked": 1,
                }
            ],
        ]
        output = StringIO()

        call_command("setup_fedrizzi_dominio", dsn="contabil", sync=True, stdout=output)

        office = Organization.objects.get(slug="fedrizzi-contabilidade")
        company = ClientCompany.objects.get(organization=office, dominio_code="001")
        self.assertEqual(company.cnpj_masked, "12.345.678/0001-90")
        self.assertEqual(DominioCommunication.objects.get(organization=office).source_id, "7")
        self.assertEqual(DominioBankEntry.objects.get(organization=office).amount_cents, 1234)
        mocked_odbc.assert_called_once_with("contabil")
        self.assertEqual(
            IntelligenceConnector.objects.get(
                organization=office, mode=IntelligenceConnector.Mode.DIRECT_ODBC
            ).odbc_dsn,
            "contabil",
        )
        self.assertEqual(mocked_odbc.return_value.execute.call_args_list[0].args, ("companies",))
        self.assertEqual(
            mocked_odbc.return_value.execute.call_args_list[1].args,
            ("communications",),
        )
        self.assertEqual(
            mocked_odbc.return_value.execute.call_args_list[2].args,
            ("bank_entries",),
        )
        self.assertIn("Cadastros sincronizados", output.getvalue())
        self.assertIn("Comunicados sincronizados", output.getvalue())
        self.assertIn("Itens bancários sincronizados", output.getvalue())
