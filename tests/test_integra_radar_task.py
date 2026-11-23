"""T10.5: the radar task does nothing unless the flag is on and the office chose a mode."""

from __future__ import annotations

import pytest
from django.test import override_settings

from apps.integra import tasks
from apps.integra.models import OfficeSerproIdentity, RadarRequest
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


def test_the_task_is_a_no_op_while_the_flag_is_off(organization: Organization) -> None:
    OfficeSerproIdentity.objects.create(organization=organization)

    assert tasks.radar_tick() == {"offices": 0, "requested": 0, "collected": 0}
    assert not RadarRequest.objects.exists()


@override_settings(INTEGRA_RADAR_ENABLED=True)
def test_an_office_without_identity_row_is_never_called(
    organization: Organization, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("no office should be called")

    monkeypatch.setattr(tasks, "office_access", refuse)

    assert tasks.radar_tick() == {"offices": 0, "requested": 0, "collected": 0}


@override_settings(INTEGRA_RADAR_ENABLED=True)
def test_an_office_that_chose_a_mode_is_visited_and_a_failure_does_not_stop_the_others(
    organization: Organization, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.integra.errors import IntegraConfigurationError

    other = Organization.objects.create(name="Outro", slug="outro")
    OfficeSerproIdentity.objects.create(organization=organization)
    OfficeSerproIdentity.objects.create(organization=other)
    seen: list[str] = []

    def access(office: Organization) -> object:
        seen.append(office.slug)
        if office.pk == organization.pk:
            raise IntegraConfigurationError("sem e-CNPJ")
        return object()

    monkeypatch.setattr(tasks, "office_access", access)
    monkeypatch.setattr(tasks, "collect_events", lambda *a, **k: 2)
    monkeypatch.setattr(tasks, "request_events", lambda *a, **k: [1, 2, 3])

    assert tasks.radar_tick() == {"offices": 1, "requested": 3, "collected": 2}
    assert sorted(seen) == sorted([organization.slug, "outro"])
