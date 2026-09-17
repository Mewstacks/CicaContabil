from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from apps.organizations.models import Organization
from apps.platform.models import OperationalRun, TenantContract, TenantLifecycle
from apps.platform.tasks import advance_tenant_lifecycles, close_previous_competence


@patch("apps.platform.tasks.close_competence", return_value=[object(), object()])
@patch("apps.platform.tasks.timezone.localdate", return_value=date(2026, 9, 1))
@pytest.mark.django_db
def test_monthly_task_closes_the_previous_competence(
    _mock_date: MagicMock, mock_close: MagicMock
) -> None:
    assert close_previous_competence.run() == {
        "competencia": "08/2026", "faturas_concluidas": 2, "escritorios_adiados": 0
    }
    mock_close.assert_called_once_with(
        period_start=date(2026, 8, 1), deferred_organization_ids=[]
    )
    run = OperationalRun.objects.get(task=OperationalRun.Task.CLOSE_COMPETENCE)
    assert run.state == OperationalRun.State.SUCCEEDED
    assert run.summary == {
        "competencia": "08/2026", "faturas_concluidas": 2, "escritorios_adiados": 0
    }


@patch("apps.platform.tasks.close_competence", return_value=[])
@patch("apps.platform.tasks.timezone.localdate", return_value=date(2026, 9, 14))
@pytest.mark.django_db
def test_daily_retry_never_closes_the_current_competence(
    _mock_date: MagicMock, mock_close: MagicMock
) -> None:
    assert close_previous_competence.run()["faturas_concluidas"] == 0
    mock_close.assert_called_once_with(
        period_start=date(2026, 8, 1), deferred_organization_ids=[]
    )


@patch("apps.platform.tasks.timezone.localdate", return_value=date(2026, 9, 14))
@pytest.mark.django_db
def test_daily_close_marks_partial_when_an_office_is_deferred(
    _mock_date: MagicMock,
) -> None:
    def close_with_deferral(*, period_start: date, deferred_organization_ids: list[str]):
        assert period_start == date(2026, 8, 1)
        deferred_organization_ids.append("synthetic-office-id")
        return [object()]

    with patch("apps.platform.tasks.close_competence", side_effect=close_with_deferral):
        result = close_previous_competence.run()
    assert result == {
        "competencia": "08/2026", "faturas_concluidas": 1, "escritorios_adiados": 1
    }
    run = OperationalRun.objects.get(task=OperationalRun.Task.CLOSE_COMPETENCE)
    assert run.state == OperationalRun.State.PARTIAL
    assert run.summary["escritorios_adiados"] == 1


@pytest.mark.django_db
@patch("apps.platform.tasks.timezone.localdate", return_value=date(2026, 9, 14))
def test_trial_expiry_blocks_operations_but_never_auto_suspends_an_office(
    _mock_date: MagicMock,
) -> None:
    office = Organization.objects.create(name="Teste", slug="teste-expirado")
    contract = TenantContract.objects.create(
        organization=office,
        status=TenantContract.Status.TRIAL,
        trial_ends_on=date(2026, 9, 13),
    )
    lifecycle = TenantLifecycle.objects.create(
        organization=office, state=TenantLifecycle.State.ACTIVE
    )

    changed = advance_tenant_lifecycles()

    contract.refresh_from_db()
    lifecycle.refresh_from_db()
    assert changed == 1
    assert contract.status == TenantContract.Status.GRACE
    assert lifecycle.state == TenantLifecycle.State.GRACE
    assert "Mewstack" in lifecycle.reason
    run = OperationalRun.objects.get(task=OperationalRun.Task.ADVANCE_LIFECYCLES)
    assert run.state == OperationalRun.State.SUCCEEDED
    assert run.summary == {"processed": 1}


@pytest.mark.django_db
@patch("apps.platform.tasks.timezone.localdate", return_value=date(2026, 9, 14))
def test_grace_never_becomes_suspended_without_console_action(_mock_date: MagicMock) -> None:
    office = Organization.objects.create(name="Carência", slug="carencia-manual")
    contract = TenantContract.objects.create(
        organization=office,
        status=TenantContract.Status.GRACE,
        grace_ends_on=date(2026, 9, 1),
    )
    lifecycle = TenantLifecycle.objects.create(
        organization=office, state=TenantLifecycle.State.GRACE
    )

    changed = advance_tenant_lifecycles()

    contract.refresh_from_db()
    lifecycle.refresh_from_db()
    assert changed == 0
    assert contract.status == TenantContract.Status.GRACE
    assert lifecycle.state == TenantLifecycle.State.GRACE
