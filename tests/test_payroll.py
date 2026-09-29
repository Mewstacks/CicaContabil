from __future__ import annotations

from datetime import date
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import RequestFactory, TestCase

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import ClientCompany, OperationalActivity, PayrollPeriodSnapshot
from apps.hub.operations import add_human_evidence, complete_activity, completion_requirements
from apps.hub.payroll import compare_payroll_snapshots, record_payroll_snapshot
from apps.organizations.models import Membership, Organization


class PayrollComparisonTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user("owner@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Acme", slug="acme-payroll")
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa A"
        )

    def snapshot(self, **overrides: object) -> PayrollPeriodSnapshot:
        values: dict[str, object] = {
            "organization": self.organization,
            "company": self.company,
            "competence": date(2026, 9, 1),
            "source_kind": PayrollPeriodSnapshot.SourceKind.ERP,
            "source_reference": "erp-2026-09",
            "workforce_count": 10,
            "gross_pay_cents": 100_000,
            "deductions_cents": 10_000,
            "employer_charges_cents": 20_000,
            "net_pay_cents": 90_000,
        }
        values.update(overrides)
        return PayrollPeriodSnapshot.objects.create(**values)

    def test_compares_aggregate_sources_without_worker_data(self) -> None:
        erp = self.snapshot()
        document = self.snapshot(
            source_kind=PayrollPeriodSnapshot.SourceKind.DOCUMENT,
            source_reference="documento-2026-09",
            gross_pay_cents=100_050,
            employer_charges_cents=20_300,
        )

        comparison = compare_payroll_snapshots(left=erp, right=document, money_tolerance_cents=100)

        self.assertEqual([item.metric for item in comparison.variances], ["employer_charges_cents"])
        self.assertEqual(comparison.variances[0].difference, 300)
        self.assertEqual(comparison.missing_metrics, ())

    def test_keeps_absent_values_explicit_and_refuses_cross_company_comparison(self) -> None:
        erp = self.snapshot()
        incomplete = self.snapshot(
            source_kind=PayrollPeriodSnapshot.SourceKind.OFFICIAL,
            source_reference="official-2026-09",
            net_pay_cents=None,
        )
        comparison = compare_payroll_snapshots(left=erp, right=incomplete)
        self.assertIn("net_pay_cents", comparison.missing_metrics)
        self.assertFalse(comparison.matches)

        other = ClientCompany.objects.create(organization=self.organization, name="Empresa B")
        other_snapshot = PayrollPeriodSnapshot.objects.create(
            organization=self.organization,
            company=other,
            competence=date(2026, 9, 1),
            source_kind=PayrollPeriodSnapshot.SourceKind.MANUAL,
            source_reference="manual-2026-09",
        )
        with self.assertRaisesRegex(ValueError, "mesma empresa"):
            compare_payroll_snapshots(left=erp, right=other_snapshot)

    def test_records_one_aggregate_snapshot_with_audit_and_no_value_metadata(self) -> None:
        draft = PayrollPeriodSnapshot(
            organization=self.organization,
            company=self.company,
            competence=date(2026, 9, 1),
            source_kind=PayrollPeriodSnapshot.SourceKind.DOCUMENT,
            source_reference="recibo-folha-09",
            gross_pay_cents=123_450,
        )
        request = RequestFactory().post("/")

        recorded, created = record_payroll_snapshot(
            snapshot=draft, actor=self.user, request=request
        )
        repeated, repeated_created = record_payroll_snapshot(
            snapshot=PayrollPeriodSnapshot(
                organization=self.organization,
                company=self.company,
                competence=date(2026, 9, 1),
                source_kind=PayrollPeriodSnapshot.SourceKind.DOCUMENT,
                source_reference="recibo-folha-09",
                gross_pay_cents=123_450,
            ),
            actor=self.user,
            request=request,
        )

        self.assertTrue(created)
        self.assertFalse(repeated_created)
        self.assertEqual(recorded.id, repeated.id)
        event = AuditEvent.objects.get(action="hub.payroll_snapshot.recorded")
        self.assertEqual(event.metadata["reported_metrics"], ["gross_pay_cents"])
        self.assertNotIn("123450", str(event.metadata))

    def test_new_payroll_snapshot_reopens_review_and_requires_new_human_proof(self) -> None:
        member = Membership.objects.create(
            organization=self.organization,
            user=self.user,
            role="owner",
        )
        request = RequestFactory().post("/")

        def receive(reference: str) -> None:
            record_payroll_snapshot(
                snapshot=PayrollPeriodSnapshot(
                    organization=self.organization,
                    company=self.company,
                    competence=date(2026, 9, 1),
                    source_kind="document",
                    source_reference=reference,
                    gross_pay_cents=10000,
                ),
                actor=self.user,
                request=request,
            )

        receive("v1")
        activity = OperationalActivity.objects.get()
        self.assertEqual(activity.area, "payroll")
        self.assertIsNone(activity.assigned_to)
        self.assertIsNone(activity.internal_due_on)
        self.assertTrue(completion_requirements(activity))
        add_human_evidence(
            activity=activity,
            membership=member,
            actor=self.user,
            request=request,
            reference="conferencia-v1",
            summary="Conferido com o documento.",
        )
        complete_activity(activity=activity, membership=member, actor=self.user, request=request)
        count = activity.events.count()
        receive("v1")
        activity.refresh_from_db()
        self.assertEqual(activity.work_status, "completed")
        self.assertEqual(activity.events.count(), count)
        receive("v2")
        activity.refresh_from_db()
        self.assertEqual(activity.work_status, "pending")
        self.assertEqual(activity.evidence_items.count(), 1)
        self.assertEqual(activity.obligation_status, "not_applicable")
        with self.assertRaises(ValidationError):
            complete_activity(
                activity=activity, membership=member, actor=self.user, request=request
            )
        add_human_evidence(
            activity=activity,
            membership=member,
            actor=self.user,
            request=request,
            reference="conferencia-v2",
            summary="Nova fotografia conferida.",
        )
        complete_activity(activity=activity, membership=member, actor=self.user, request=request)
        call_command(
            "sync_payroll_activities", organization=self.organization.pk, stdout=StringIO()
        )
        activity.refresh_from_db()
        self.assertEqual(activity.work_status, "completed")
        self.assertEqual(activity.evidence_items.count(), 2)
        self.assertEqual(OperationalActivity.objects.count(), 1)
