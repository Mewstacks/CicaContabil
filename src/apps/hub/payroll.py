"""Explainable comparison of aggregate payroll facts from explicitly identified sources."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany, PayrollPeriodSnapshot


@dataclass(frozen=True)
class PayrollVariance:
    metric: str
    left_value: int
    right_value: int
    difference: int


@dataclass(frozen=True)
class PayrollComparison:
    left_snapshot_id: str
    right_snapshot_id: str
    variances: tuple[PayrollVariance, ...]
    missing_metrics: tuple[str, ...]

    @property
    def matches(self) -> bool:
        return not self.variances and not self.missing_metrics


_METRICS = (
    "workforce_count",
    "gross_pay_cents",
    "deductions_cents",
    "employer_charges_cents",
    "net_pay_cents",
)


def compare_payroll_snapshots(
    *,
    left: PayrollPeriodSnapshot,
    right: PayrollPeriodSnapshot,
    money_tolerance_cents: int = 0,
) -> PayrollComparison:
    """Compare the same company and competence without inventing unavailable fields."""

    if left.organization_id != right.organization_id or left.company_id != right.company_id:
        raise ValueError("Só é possível comparar fotografias da mesma empresa.")
    if left.competence != right.competence:
        raise ValueError("Só é possível comparar a mesma competência da folha.")
    if money_tolerance_cents < 0:
        raise ValueError("A tolerância monetária não pode ser negativa.")
    variances: list[PayrollVariance] = []
    missing: list[str] = []
    for metric in _METRICS:
        left_value = getattr(left, metric)
        right_value = getattr(right, metric)
        if left_value is None or right_value is None:
            missing.append(metric)
            continue
        difference = right_value - left_value
        tolerance = 0 if metric == "workforce_count" else money_tolerance_cents
        if abs(difference) > tolerance:
            variances.append(
                PayrollVariance(
                    metric=metric,
                    left_value=left_value,
                    right_value=right_value,
                    difference=difference,
                )
            )
    return PayrollComparison(
        left_snapshot_id=str(left.id),
        right_snapshot_id=str(right.id),
        variances=tuple(variances),
        missing_metrics=tuple(missing),
    )


@transaction.atomic
def record_payroll_snapshot(
    *,
    snapshot: PayrollPeriodSnapshot,
    actor: User,
    request: object,
) -> tuple[PayrollPeriodSnapshot, bool]:
    """Persist one aggregate source without logging payroll values in audit metadata."""

    if not snapshot.organization_id or not snapshot.company_id:
        raise ValueError("A fotografia exige escritório e empresa.")
    ClientCompany.objects.select_for_update().get(
        pk=snapshot.company_id, organization_id=snapshot.organization_id
    )
    snapshot.full_clean(validate_unique=False, validate_constraints=False)
    existing = PayrollPeriodSnapshot.objects.filter(
        organization=snapshot.organization,
        company=snapshot.company,
        competence=snapshot.competence,
        source_kind=snapshot.source_kind,
        source_reference=snapshot.source_reference,
    ).first()
    if existing is not None:
        if any(
            getattr(existing, field) != getattr(snapshot, field)
            for field in (
                *_METRICS,
                "data_source_id",
                "notes",
            )
        ):
            raise ValueError("A referência já possui outros dados. Informe uma nova referência.")
        from apps.hub.payroll_activities import sync_payroll_activity

        sync_payroll_activity(company_id=existing.company_id, competence=existing.competence)
        return existing, False
    snapshot.created_by = actor
    snapshot.full_clean()
    snapshot.save()
    record_event(
        action="hub.payroll_snapshot.recorded",
        actor=actor,
        organization=snapshot.organization,
        target=snapshot,
        request=request,
        metadata={
            "company_id": str(snapshot.company_id),
            "competence": snapshot.competence.isoformat(),
            "source_kind": snapshot.source_kind,
            "data_source_id": str(snapshot.data_source_id or ""),
            "reported_metrics": [
                metric for metric in _METRICS if getattr(snapshot, metric) is not None
            ],
        },
    )
    from apps.hub.payroll_activities import sync_payroll_activity

    sync_payroll_activity(company_id=snapshot.company_id, competence=snapshot.competence)
    return snapshot, True
