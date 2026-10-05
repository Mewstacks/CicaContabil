from __future__ import annotations

import json
from contextlib import nullcontext
from datetime import timedelta
from io import StringIO
from time import sleep
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.dte_access import DteAccessError, open_message
from apps.hub.dte_activities import sync_dte_activity
from apps.hub.dte_payload import body_text
from apps.hub.models import (
    ClientCompany,
    DteMessage,
    DteMessageAccess,
    OfficeProfile,
    OperationalEvidence,
)
from apps.hub.operations import complete_activity, completion_requirements
from apps.integra.errors import IntegraTransportError
from apps.organizations.models import Membership, Organization
from apps.platform.models import (
    Plan,
    PlanServiceRate,
    TenantContract,
    TenantServiceRate,
    TenantUsagePolicy,
    UsageEvent,
)

pytestmark = pytest.mark.django_db


def _message() -> tuple[DteMessage, User]:
    office = Organization.objects.create(name="Ofício", slug="oficio")
    OfficeProfile.objects.create(organization=office, cnpj="11.222.333/0001-81")
    user = User.objects.create_user("dte-access@example.test", "SafePassword2026!")
    Membership.objects.create(organization=office, user=user, role=Membership.Role.OWNER)
    company = ClientCompany.objects.create(
        organization=office, name="Empresa", cnpj_masked="12.345.678/0001-95"
    )
    plan = Plan.objects.create(code="detail", name="Detalhe")
    PlanServiceRate.objects.create(plan=plan, action_code="caixapostal.detalhe", included_units=2)
    TenantContract.objects.create(
        organization=office, plan=plan, status=TenantContract.Status.ACTIVE
    )
    message = DteMessage.objects.create(
        organization=office,
        company=company,
        source_isn="0000082838",
        subject="Intimação",
    )
    return message, user


@pytest.mark.parametrize("fail_projection", [False, True])
@patch("apps.hub.dte_access.IntegraClient")
def test_open_dte_detail_meters_once_and_renders_official_body_as_safe_text(
    mock_client, django_capture_on_commit_callbacks, fail_projection
) -> None:
    message, user = _message()
    mock_client.return_value.call.return_value = {
        "status": 200,
        "requestId": "serpro-request-1",
        "dados": json.dumps(
            {
                "codigo": "00",
                "conteudo": [
                    {
                        "isn": "0000082838",
                        "corpoModelo": "<p>Prazo ++1++</p><p><script>alert(1)</script>Confira.</p>",
                        "variaveis": ["2026"],
                        "dataLeitura": "20260915",
                        "horaLeitura": "103000",
                        "dataCiencia": "20260915",
                    }
                ],
            }
        ),
    }

    with (
        patch(
            "apps.hub.dte_access.sync_dte_activity", side_effect=RuntimeError("projection failed")
        )
        if fail_projection
        else nullcontext(),
        django_capture_on_commit_callbacks(execute=True),
    ):
        access = open_message(message=message, actor=user)
    if fail_projection:
        access.refresh_from_db()
        assert access.status == "opened"
        call_command("sync_dte_activities", organization=message.organization_id, stdout=StringIO())
    again = open_message(message=message, actor=user)

    assert access.pk == again.pk
    assert access.status == DteMessageAccess.Status.OPENED
    assert access.provider_science_at is not None
    assert access.provider_request_id == "serpro-request-1"
    activity = message.analysis_activity
    assert activity.work_status == "pending"
    assert activity.evidence_items.count() == 1
    assert completion_requirements(activity)  # Opening is not a human analysis.
    sync_dte_activity(message.pk)
    assert activity.evidence_items.count() == 1
    content = body_text(json.loads(access.provider_payload))
    assert "Prazo 2026" in content
    assert "alert(1)" not in content
    assert (
        UsageEvent.objects.get(organization=message.organization).status
        == UsageEvent.Status.SETTLED
    )
    mock_client.return_value.call.assert_called_once_with(
        "caixapostal.detalhe",
        contribuinte="12345678000195",
        autor_pedido="11222333000181",
        dados={"isn": "0000082838"},
    )


def test_legacy_acknowledge_flag_without_company_access_does_not_reserve_or_call() -> None:
    message, user = _message()
    member = Membership.objects.get(user=user, organization=message.organization)
    member.role = Membership.Role.OPERATOR
    member.can_acknowledge_dte = True
    member.save()
    with patch("apps.hub.dte_access.IntegraClient") as client:
        with pytest.raises(DteAccessError):
            open_message(message=message, actor=user)
        client.assert_not_called()
    assert not UsageEvent.objects.exists()
    assert not DteMessageAccess.objects.exists()


@pytest.mark.parametrize("previous_status", ["completed", "waived"])
def test_new_dte_receipt_requires_later_human_review_even_before_projection(previous_status):
    message, user = _message()
    member = Membership.objects.get(user=user, organization=message.organization)
    activity = sync_dte_activity(message.pk)
    OperationalEvidence.objects.create(
        organization=message.organization,
        activity=activity,
        kind="human",
        recorded_by=user,
        summary="Análise anterior",
    )
    # Windows can expose a coarse wall-clock resolution; keep the temporal
    # contract deterministic instead of letting both facts share one instant.
    sleep(0.05)
    activity.work_status = previous_status
    activity.completed_at = timezone.now()
    activity.completed_by = user
    activity.waived_reason = "Dispensa anterior" if previous_status == "waived" else ""
    activity.save()
    DteMessageAccess.objects.create(
        organization=message.organization,
        message=message,
        status="opened",
        opened_at=timezone.now(),
        provider_payload='{"conteudo":"Teste"}',
    )
    with pytest.raises(ValidationError, match="após a abertura"):
        complete_activity(activity=activity, membership=member, actor=user, request=None)
    activity = sync_dte_activity(message.pk)
    assert activity.work_status == "pending"
    assert activity.completed_by is None
    assert activity.completed_at is None
    assert activity.waived_reason == ""
    assert activity.events.filter(event_type="dte_analysis_reopened").count() == 1
    assert activity.evidence_items.count() == 2
    sleep(0.05)
    OperationalEvidence.objects.create(
        organization=message.organization,
        activity=activity,
        kind="human",
        recorded_by=user,
        summary="Teor analisado após abertura",
    )
    activity = complete_activity(activity=activity, membership=member, actor=user, request=None)
    assert activity.work_status == "completed"
    assert sync_dte_activity(message.pk).work_status == "completed"
    assert activity.events.filter(event_type="dte_analysis_reopened").count() == 1


def test_dte_recovery_preserves_review_after_receipt_and_rejects_missing_body():
    message, user = _message()
    activity = sync_dte_activity(message.pk)
    access = DteMessageAccess.objects.create(
        organization=message.organization,
        message=message,
        status="opened",
        opened_at=timezone.now() - timedelta(seconds=1),
        provider_payload='{"conteudo":"Teste"}',
    )
    OperationalEvidence.objects.create(
        organization=message.organization,
        activity=activity,
        kind="human",
        recorded_by=user,
        summary="Análise posterior ao recibo",
    )
    member = Membership.objects.get(user=user, organization=message.organization)
    complete_activity(activity=activity, membership=member, actor=user, request=None)
    assert sync_dte_activity(message.pk).work_status == "completed"
    assert not activity.events.filter(event_type="dte_analysis_reopened").exists()
    access.provider_payload = ""
    access.save()
    assert "comprovante" in completion_requirements(activity)[0]


def test_uncertain_dte_access_blocks_human_completion_without_duplicate_events() -> None:
    message, user = _message()
    access = DteMessageAccess.objects.create(
        organization=message.organization,
        message=message,
        status="unknown",
        requested_by=user,
    )
    activity = sync_dte_activity(message.pk)
    assert activity.work_status == "blocked"
    count = activity.events.count()
    sync_dte_activity(message.pk)
    assert activity.events.count() == count
    assert "resultado" in completion_requirements(activity)[0]
    from django.utils import timezone

    access.status = "opened"
    access.opened_at = timezone.now()
    access.provider_payload = '{"conteudo":"Teste"}'
    access.save()
    activity = sync_dte_activity(message.pk)
    assert activity.work_status == "pending"
    assert activity.evidence_items.count() == 1
    assert activity.obligation_status == "not_applicable"


@patch("apps.hub.dte_access.IntegraClient", side_effect=IntegraTransportError("timeout"))
def test_transport_uncertainty_blocks_automatic_second_legal_call(_mock_client) -> None:
    message, user = _message()

    with pytest.raises(DteAccessError, match="incerto"):
        open_message(message=message, actor=user)
    with pytest.raises(DteAccessError, match="conferência"):
        open_message(message=message, actor=user)

    assert DteMessageAccess.objects.get(message=message).status == DteMessageAccess.Status.UNKNOWN
    assert (
        UsageEvent.objects.get(organization=message.organization).status
        == UsageEvent.Status.RESERVED
    )


@patch("apps.hub.dte_access.IntegraClient")
def test_operator_without_explicit_science_permission_cannot_consume_or_open(mock_client) -> None:
    message, user = _message()
    membership = Membership.objects.get(organization=message.organization, user=user)
    membership.role = Membership.Role.OPERATOR
    membership.save(update_fields=["role"])

    with pytest.raises(DteAccessError, match="não pode confirmar ciência"):
        open_message(message=message, actor=user)

    assert not UsageEvent.objects.filter(organization=message.organization).exists()
    mock_client.assert_not_called()


@patch("apps.hub.dte_access.IntegraClient")
def test_detail_overage_needs_separate_exact_amount_before_legal_request(mock_client) -> None:
    message, user = _message()
    PlanServiceRate.objects.filter(plan__code="detail").update(
        included_units=0, overage_unit_price_cents=75
    )
    TenantServiceRate.objects.filter(contract__organization=message.organization).update(
        included_units=0, overage_unit_price_cents=75
    )
    TenantUsagePolicy.objects.create(
        organization=message.organization,
        action_code="caixapostal.detalhe",
        overage_mode=TenantUsagePolicy.OverageMode.ALLOW,
        monthly_overage_cap_cents=75,
    )

    with pytest.raises(DteAccessError, match="valor exato"):
        open_message(message=message, actor=user)
    assert not UsageEvent.objects.filter(organization=message.organization).exists()
    mock_client.assert_not_called()

    mock_client.return_value.call.return_value = {
        "status": 200,
        "dados": json.dumps(
            {
                "codigo": "00",
                "conteudo": [{"isn": message.source_isn, "corpoModelo": "Aviso"}],
            }
        ),
    }
    receipt = open_message(
        message=message,
        actor=user,
        approved_overage=True,
        approved_overage_cents=75,
    )
    assert receipt.status == DteMessageAccess.Status.OPENED
    assert UsageEvent.objects.get(organization=message.organization).overage_cents == 75
