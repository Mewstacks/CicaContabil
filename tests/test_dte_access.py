from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from apps.accounts.models import User
from apps.hub.dte_access import DteAccessError, open_message
from apps.hub.dte_payload import body_text
from apps.hub.models import ClientCompany, DteMessage, DteMessageAccess, OfficeProfile
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


@patch("apps.hub.dte_access.IntegraClient")
def test_open_dte_detail_meters_once_and_renders_official_body_as_safe_text(mock_client) -> None:
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

    access = open_message(message=message, actor=user)
    again = open_message(message=message, actor=user)

    assert access.pk == again.pk
    assert access.status == DteMessageAccess.Status.OPENED
    assert access.provider_science_at is not None
    assert access.provider_request_id == "serpro-request-1"
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
        "dados": json.dumps({
            "codigo": "00",
            "conteudo": [{"isn": message.source_isn, "corpoModelo": "Aviso"}],
        }),
    }
    receipt = open_message(
        message=message,
        actor=user,
        approved_overage=True,
        approved_overage_cents=75,
    )
    assert receipt.status == DteMessageAccess.Status.OPENED
    assert UsageEvent.objects.get(organization=message.organization).overage_cents == 75
