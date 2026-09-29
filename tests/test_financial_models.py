from __future__ import annotations

from datetime import date

from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.financial import (
    AccountingBalanceInput,
    calculate_snapshot_dre,
    project_cash_scenario,
    record_accounting_balance_snapshot,
)
from apps.hub.models import (
    AccountingBalanceSnapshot,
    CashScenario,
    CashScenarioMovement,
    ClientCompany,
    DreAccountMapping,
    DreMappingSet,
)
from apps.hub.reporting import cash_report_snapshot, dre_report_snapshot
from apps.organizations.models import Organization


class FinancialModelTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user("financeiro@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Acme", slug="acme-financeiro")
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa Financeira"
        )

    def test_balance_snapshot_is_idempotent_auditable_and_calculates_with_mapping(self) -> None:
        snapshot = AccountingBalanceSnapshot(
            organization=self.organization,
            company=self.company,
            competence=date(2026, 9, 1),
            source_kind=AccountingBalanceSnapshot.SourceKind.IMPORT,
            source_reference="balancete-2026-09",
        )
        recorded, created = record_accounting_balance_snapshot(
            snapshot=snapshot,
            lines=(
                AccountingBalanceInput("3.01", -120_000, "Receitas"),
                AccountingBalanceInput("4.01", 35_000, "Despesas"),
                AccountingBalanceInput("9.99", 2_000, "Sem mapa"),
            ),
            actor=self.user,
            request=RequestFactory().post("/"),
        )
        repeated, repeated_created = record_accounting_balance_snapshot(
            snapshot=AccountingBalanceSnapshot(
                organization=self.organization,
                company=self.company,
                competence=date(2026, 9, 1),
                source_kind=AccountingBalanceSnapshot.SourceKind.IMPORT,
                source_reference="balancete-2026-09",
            ),
            lines=(AccountingBalanceInput("3.01", -120_000),),
            actor=self.user,
            request=RequestFactory().post("/"),
        )
        mapping_set = DreMappingSet.objects.create(
            organization=self.organization, version=1, label="Mapa inicial", created_by=self.user
        )
        DreAccountMapping.objects.create(
            mapping_set=mapping_set, account_code="3.01", group="Receita líquida", sign=-1
        )
        DreAccountMapping.objects.create(
            mapping_set=mapping_set, account_code="4.01", group="Despesas", sign=-1
        )

        result = calculate_snapshot_dre(snapshot=recorded, mapping_set=mapping_set)

        self.assertTrue(created)
        self.assertFalse(repeated_created)
        self.assertEqual(recorded.id, repeated.id)
        self.assertEqual(recorded.lines.count(), 3)
        self.assertEqual(result.groups_cents, {"Receita líquida": 120_000, "Despesas": -35_000})
        self.assertEqual(result.unmapped_account_codes, ("9.99",))
        event = AuditEvent.objects.get(action="hub.accounting_balance_snapshot.recorded")
        self.assertEqual(event.metadata["line_count"], 3)
        self.assertNotIn("120000", str(event.metadata))

    def test_cash_scenario_separates_views_and_rejects_double_retention(self) -> None:
        scenario = CashScenario.objects.create(
            organization=self.organization,
            company=self.company,
            label="Projeção outubro",
            view=CashScenario.View.PROJECTION,
            reference_date=date(2026, 10, 1),
            opening_balance_cents=10_000,
            created_by=self.user,
        )
        CashScenarioMovement.objects.create(
            scenario=scenario,
            occurred_on=date(2026, 10, 2),
            description="Recebimento",
            gross_receipt_cents=20_000,
            retention_cents=3_000,
            source_reference="recebível-1",
        )
        CashScenarioMovement.objects.create(
            scenario=scenario,
            occurred_on=date(2026, 10, 3),
            description="Folha",
            payment_cents=18_000,
            source_reference="folha-1",
        )

        projection = project_cash_scenario(scenario=scenario)

        self.assertEqual(projection.view.value, "projection")
        self.assertEqual(
            [row.closing_balance_cents for row in projection.positions], [27_000, 9_000]
        )
        invalid = CashScenarioMovement(
            scenario=scenario,
            occurred_on=date(2026, 10, 4),
            description="Duplicidade",
            retention_cents=3_000,
            provision_cents=3_000,
            retention_already_provisioned=True,
        )
        with self.assertRaisesMessage(ValidationError, "não pode ser deduzida"):
            invalid.full_clean()


    def test_financial_report_snapshots_preserve_sources_and_incompleteness(self) -> None:
        recorded, _ = record_accounting_balance_snapshot(
            snapshot=AccountingBalanceSnapshot(
                organization=self.organization,
                company=self.company,
                competence=date(2026, 9, 1),
                source_kind=AccountingBalanceSnapshot.SourceKind.IMPORT,
                source_reference="balancete-setembro",
            ),
            lines=(
                AccountingBalanceInput("3.01", -10_000, "Receita"),
                AccountingBalanceInput("9.99", 500, "Pendente"),
            ),
            actor=self.user,
            request=RequestFactory().post("/"),
        )
        mapping_set = DreMappingSet.objects.create(
            organization=self.organization, version=1, label="Mapa", created_by=self.user
        )
        DreAccountMapping.objects.create(
            mapping_set=mapping_set, account_code="3.01", group="Receita", sign=-1
        )
        dre_snapshot = dre_report_snapshot(snapshot=recorded, mapping_set=mapping_set)

        scenario = CashScenario.objects.create(
            organization=self.organization,
            company=self.company,
            label="Outubro",
            view=CashScenario.View.PROJECTION,
            reference_date=date(2026, 10, 1),
            opening_balance_cents=1_000,
            created_by=self.user,
        )
        CashScenarioMovement.objects.create(
            scenario=scenario,
            occurred_on=date(2026, 10, 2),
            description="Recebimento",
            gross_receipt_cents=5_000,
        )
        cash_snapshot = cash_report_snapshot(scenario=scenario)

        self.assertTrue(dre_snapshot["preliminary"])
        self.assertEqual(dre_snapshot["rows"], [{"label": "Receita", "amount": "100.00"}])
        self.assertEqual(dre_snapshot["evidence"][0]["reference"], "balancete-setembro")
        self.assertIn("9.99", dre_snapshot["pendingNotes"][0])
        self.assertFalse(cash_snapshot["preliminary"])
        self.assertEqual(cash_snapshot["rows"][0], {"label": "02/10/2026", "amount": "60.00"})
        self.assertEqual(cash_snapshot["rows"][-1]["amount"], "0.00")
