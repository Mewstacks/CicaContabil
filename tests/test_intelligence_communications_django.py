from __future__ import annotations

from django.db import connection
from django.test import TestCase

from apps.hub.models import ClientCompany
from apps.intelligence.models import DominioCommunication, IntelligenceConnector
from apps.intelligence.sync import sync_communications
from apps.organizations.models import Organization


class CommunicationSyncTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        self.connector = IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization, dominio_code="001", name="Empresa"
        )

    def test_communication_is_linked_by_company_code_and_subject_is_encrypted(self) -> None:
        result = sync_communications(
            organization=self.organization,
            connector=self.connector,
            rows=[
                {
                    "source_id": "7",
                    "company_code": "001",
                    "subject": "Recolher guia",
                    "type_code": "2",
                    "status_code": "1",
                    "is_read": 1,
                }
            ],
        )

        communication = DominioCommunication.objects.get(organization=self.organization)
        self.assertEqual(result.created, 1)
        self.assertEqual(communication.company, self.company)
        self.assertEqual(communication.subject, "Recolher guia")
        self.assertTrue(communication.is_read)
        with connection.cursor() as cursor:
            cursor.execute("SELECT subject FROM intelligence_dominiocommunication LIMIT 1")
            stored = str(cursor.fetchone()[0])
        self.assertNotIn("Recolher guia", stored)

    def test_missing_source_identifier_is_ignored(self) -> None:
        result = sync_communications(
            organization=self.organization,
            connector=self.connector,
            rows=[{"company_code": "001", "subject": "Sem chave"}],
        )

        self.assertEqual(result.ignored, 1)
        self.assertFalse(DominioCommunication.objects.exists())
