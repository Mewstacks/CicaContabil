from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.imports import confirm_import, create_import_preview
from apps.hub.models import (
    AccountingBalanceSnapshot,
    CashScenario,
    ClientCompany,
    DataSource,
    DreAccountMapping,
    DreMappingSet,
    ImportBatch,
    OperationalActivity,
    PayrollPeriodSnapshot,
)
from apps.organizations.models import Membership, Organization


class FinancialImportTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user("imports@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Acme", slug="acme-financial-imports")
        self.source = DataSource.objects.create(
            organization=self.organization,
            kind=DataSource.Kind.OTHER_MANUAL,
            label="Arquivos",
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization,
            data_source=self.source,
            external_key="001",
            name="Empresa importada",
        )
        self.request = RequestFactory().post("/")

    def _upload(self, name: str, content: str) -> SimpleUploadedFile:
        return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")

    def test_payroll_preview_replay_and_conflict_preserve_original(self) -> None:
        header = "codigo_empresa;competencia;referencia;pessoas;bruto;descontos;encargos;liquido\n"
        row = "001;2026-09-01;folha-09;10;1000,00;;;900,00\n"

        def import_rows(content: str) -> ImportBatch:
            batch, _ = create_import_preview(
                organization=self.organization,
                data_source=self.source,
                kind=ImportBatch.Kind.PAYROLL_TOTALS,
                upload=self._upload("folha.csv", content),
                actor=self.user,
                request=self.request,
            )
            return confirm_import(batch=batch, actor=self.user, request=self.request)

        result = import_rows(header + row)
        self.assertEqual(result.status, "completed")
        snapshot = PayrollPeriodSnapshot.objects.get()
        self.assertEqual(snapshot.gross_pay_cents, 100000)
        self.assertIsNone(snapshot.deductions_cents)
        self.assertEqual(snapshot.source_kind, "document")
        self.assertEqual(snapshot.data_source, self.source)
        replay = import_rows(header + row.replace("1000,00", "1000.00"))
        self.assertEqual(replay.ignored_count, 1)
        conflict = import_rows(header + row.replace("folha-09", "nova") + row.replace("10;", "11;"))
        self.assertEqual(conflict.status, "failed")
        self.assertEqual(conflict.created_count, 0)
        self.assertEqual(PayrollPeriodSnapshot.objects.count(), 1)

        snapshot.refresh_from_db()
        self.assertEqual(snapshot.workforce_count, 10)
        invalid = import_rows(header + row.replace("2026-09-01", "2026-09-15"))
        self.assertEqual(invalid.status, "failed")
        self.assertEqual(PayrollPeriodSnapshot.objects.count(), 1)

    def test_payroll_upload_requires_confirmation_before_company_can_read_it(self) -> None:
        Membership.objects.create(organization=self.organization, user=self.user, role="owner")
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.pk)
        session.save()
        response = self.client.post(
            reverse("hub:setup"),
            {
                "action": "upload",
                "source_id": self.source.pk,
                "import-kind": "payroll_totals",
                "import-upload": self._upload(
                    "folha.csv",
                    "codigo_empresa;competencia;referencia;bruto\n001;2026-09-01;web-09;1000,00\n",
                ),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(PayrollPeriodSnapshot.objects.exists())
        batch = ImportBatch.objects.get(kind="payroll_totals")
        self.assertContains(self.client.get(response.url), "Confirme antes de importar")
        response = self.client.post(
            reverse("hub:setup"),
            {
                "action": "confirm-import",
                "batch_id": batch.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PayrollPeriodSnapshot.objects.get().gross_pay_cents, 100000)
        page = self.client.get(reverse("hub:company-detail", args=[self.company.pk]))
        self.assertContains(page, "web-09")
        self.assertContains(page, "Documento informado")
        activity = OperationalActivity.objects.get(
            source_payroll_snapshot__source_reference="web-09"
        )
        self.assertEqual(activity.company, self.company)
        self.assertEqual(activity.work_status, "pending")
        detail = self.client.get(reverse("hub:activity-detail", args=[activity.pk]))
        self.assertContains(detail, "Conferir totais e documentos da folha")
        self.assertContains(detail, "Registrar evidência")
        review_url = detail.context["payroll_review_url"]
        self.assertIn("payroll_competence=2026-09-01", review_url)
        PayrollPeriodSnapshot.objects.create(
            organization=self.organization,
            company=self.company,
            competence="2026-08-01",
            source_kind="document",
            source_reference="another-period",
        )
        second = PayrollPeriodSnapshot.objects.create(
            organization=self.organization,
            company=self.company,
            competence="2026-09-01",
            source_kind="document",
            source_reference="second-source",
            gross_pay_cents=110000,
        )
        review = self.client.get(review_url)
        self.assertContains(review, "Voltar à atividade da folha")
        self.assertEqual(review.context["payroll_snapshots_count"], 2)
        self.assertNotContains(review, "another-period")
        self.assertContains(review, 'name="payroll_competence"')
        comparison = self.client.get(
            reverse("hub:company-detail", args=[self.company.pk]),
            {
                "payroll_competence": "2026-09-01",
                "left_snapshot": activity.source_payroll_snapshot_id,
                "right_snapshot": second.pk,
                "money_tolerance": "0",
            },
        )
        self.assertFalse(comparison.context["payroll_comparison_form"].errors)
        self.assertIsNotNone(comparison.context["payroll_comparison"])
        activity.refresh_from_db()
        self.assertEqual(activity.work_status, "pending")
        invalid = self.client.get(
            reverse("hub:company-detail", args=[self.company.pk]),
            {
                "payroll_competence": "2026-09-15",
            },
        )
        self.assertEqual(invalid.status_code, 404)
        member = Membership.objects.get(user=self.user, organization=self.organization)
        member.role = "collaborator"
        member.save(update_fields=["role"])
        self.assertEqual(self.client.get(review_url).status_code, 404)

    def test_payroll_preview_paginates_raw_values_without_writes_or_scope_leak(self) -> None:
        member = Membership.objects.create(
            organization=self.organization,
            user=self.user,
            role="owner",
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.pk)
        session.save()
        content = (
            "codigo_empresa;competencia;referencia;pessoas;bruto\n"
            + "".join(f"001;2026-09-01;line-{i};0;1000,00\n" for i in range(20))
            + "unknown;2026-09-01;<script>private-marker</script>;;\n"
        )
        batch, _ = create_import_preview(
            organization=self.organization,
            data_source=self.source,
            kind=ImportBatch.Kind.PAYROLL_TOTALS,
            upload=self._upload("preview.csv", content),
            actor=self.user,
            request=self.request,
        )
        url = reverse("hub:setup")
        first = self.client.get(url, {"preview": batch.pk, "source": self.source.pk})
        self.assertEqual(len(first.context["payroll_preview_rows"]), 20)
        self.assertContains(first, "1000,00")
        self.assertContains(first, "Próximas linhas")
        second = self.client.get(url, {"preview": batch.pk, "preview_page": "2"})
        self.assertContains(second, "Linha 22")
        self.assertContains(second, "Empresa não localizada")
        self.assertContains(second, "Não informado")
        self.assertNotContains(second, "<script>private-marker</script>")
        self.assertContains(second, "&lt;script&gt;private-marker&lt;/script&gt;")
        self.assertFalse(PayrollPeriodSnapshot.objects.exists())
        self.assertFalse(OperationalActivity.objects.exists())
        member.role = "auditor"
        member.save(update_fields=["role"])
        restricted = self.client.get(url, {"preview": batch.pk, "preview_page": "2"})
        self.assertNotContains(restricted, "private-marker")
        self.assertNotContains(restricted, 'value="confirm-import"')

    def test_balance_import_is_previewed_grouped_and_idempotent_by_source_reference(self) -> None:
        content = (
            "codigo_empresa;competencia;referencia;conta;nome_conta;saldo\n"
            "001;2026-09-01;balancete-2026-09;3.01;Receita;-1200,00\n"
            "001;2026-09-01;balancete-2026-09;4.01;Despesas;350,00\n"
        )
        batch, created = create_import_preview(
            organization=self.organization,
            data_source=self.source,
            kind=ImportBatch.Kind.ACCOUNTING_BALANCES,
            upload=self._upload("saldos.csv", content),
            actor=self.user,
            request=self.request,
        )
        confirmed = confirm_import(batch=batch, actor=self.user, request=self.request)

        snapshot = AccountingBalanceSnapshot.objects.get(source_reference="balancete-2026-09")
        self.assertTrue(created)
        self.assertEqual(confirmed.status, ImportBatch.Status.COMPLETED)
        self.assertEqual(confirmed.created_count, 1)
        self.assertEqual(snapshot.lines.count(), 2)
        self.assertEqual(snapshot.lines.get(account_code="3.01").balance_cents, -120_000)
        self.source.refresh_from_db()
        self.assertIn("accounting_balances", self.source.capabilities)

        replay_content = content.replace("Despesas", "Despesas administrativas")
        replay, _ = create_import_preview(
            organization=self.organization,
            data_source=self.source,
            kind=ImportBatch.Kind.ACCOUNTING_BALANCES,
            upload=self._upload("saldos-replay.csv", replay_content),
            actor=self.user,
            request=self.request,
        )
        replay = confirm_import(batch=replay, actor=self.user, request=self.request)
        self.assertEqual(replay.ignored_count, 1)
        self.assertEqual(AccountingBalanceSnapshot.objects.count(), 1)

    def test_dre_mapping_import_preserves_prior_version_rows(self) -> None:
        previous = DreMappingSet.objects.create(
            organization=self.organization,
            version=1,
            label="Anterior",
            is_active=True,
            created_by=self.user,
        )
        DreAccountMapping.objects.create(
            mapping_set=previous, account_code="3.00", group="Anterior", sign=-1
        )
        batch, _ = create_import_preview(
            organization=self.organization,
            data_source=self.source,
            kind=ImportBatch.Kind.DRE_MAPPING,
            upload=self._upload("novo.csv", "conta;grupo;sinal\n3.01;Receita;-1\n"),
            actor=self.user,
            request=self.request,
        )
        confirm_import(batch=batch, actor=self.user, request=self.request)
        previous.refresh_from_db()
        active = DreMappingSet.objects.get(organization=self.organization, is_active=True)
        self.assertFalse(previous.is_active)
        self.assertEqual(previous.mappings.count(), 1)
        self.assertEqual(active.version, 2)
        self.assertNotEqual(active.id, previous.id)

    def test_dre_mapping_import_creates_a_new_active_version(self) -> None:
        batch, _ = create_import_preview(
            organization=self.organization,
            data_source=self.source,
            kind=ImportBatch.Kind.DRE_MAPPING,
            upload=self._upload(
                "mapa.csv", "conta;grupo;sinal\n3.01;Receita;-1\n4.01;Despesa;-1\n"
            ),
            actor=self.user,
            request=self.request,
        )
        confirm_import(batch=batch, actor=self.user, request=self.request)
        mapping = DreMappingSet.objects.get(organization=self.organization, is_active=True)
        self.assertEqual(mapping.version, 1)
        self.assertEqual(mapping.mappings.count(), 2)

    def test_cash_import_validates_the_whole_file_before_writing(self) -> None:
        content = (
            "codigo_empresa;cenario;visao;data_referencia;saldo_inicial;data;descricao;recebimento_bruto;retencao;referencia\n"
            "001;Outubro;projection;2026-10-01;100,00;2026-10-02;Recebimento;2000,00;300,00;rec-001\n"
        )
        batch, _ = create_import_preview(
            organization=self.organization,
            data_source=self.source,
            kind=ImportBatch.Kind.CASH_SCENARIO,
            upload=self._upload("caixa.csv", content),
            actor=self.user,
            request=self.request,
        )
        confirmed = confirm_import(batch=batch, actor=self.user, request=self.request)
        scenario = CashScenario.objects.get(label="Outubro")
        movement = scenario.movements.get(source_reference="rec-001")
        self.assertEqual(confirmed.status, ImportBatch.Status.COMPLETED)
        self.assertEqual(scenario.view, CashScenario.View.PROJECTION)
        self.assertEqual(scenario.opening_balance_cents, 10_000)
        self.assertEqual(movement.gross_receipt_cents, 200_000)
        self.assertEqual(movement.retention_cents, 30_000)

        mismatched_opening_balance, _ = create_import_preview(
            organization=self.organization,
            data_source=self.source,
            kind=ImportBatch.Kind.CASH_SCENARIO,
            upload=self._upload(
                "caixa-saldo-divergente.csv",
                "codigo_empresa;cenario;visao;data_referencia;saldo_inicial;data;descricao;referencia\n"
                "001;Outubro;projection;2026-10-01;150,00;2026-10-03;Outra entrada;rec-002\n",
            ),
            actor=self.user,
            request=self.request,
        )
        mismatched_opening_balance = confirm_import(
            batch=mismatched_opening_balance, actor=self.user, request=self.request
        )
        self.assertEqual(mismatched_opening_balance.status, ImportBatch.Status.FAILED)
        self.assertEqual(scenario.movements.count(), 1)

        invalid = (
            "codigo_empresa;cenario;visao;data_referencia;saldo_inicial;data;descricao;retencao;provisao;retencao_ja_provisionada;referencia\n"
            "001;Erro;projection;2026-10-01;100,00;2026-10-02;Duplicada;100,00;100,00;sim;dup-001\n"
        )
        invalid_batch, _ = create_import_preview(
            organization=self.organization,
            data_source=self.source,
            kind=ImportBatch.Kind.CASH_SCENARIO,
            upload=self._upload("caixa-invalido.csv", invalid),
            actor=self.user,
            request=self.request,
        )
        invalid_batch = confirm_import(batch=invalid_batch, actor=self.user, request=self.request)
        self.assertEqual(invalid_batch.status, ImportBatch.Status.FAILED)
        self.assertEqual(CashScenario.objects.filter(label="Erro").count(), 0)
