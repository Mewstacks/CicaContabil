"""Audited activation of existing rules after checking current accounting references."""

from __future__ import annotations

import re
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.controlplane import company_queryset_for_module
from apps.hub.models import (
    ClientCompany,
    CostCenter,
    FinancialAccount,
    LedgerAccount,
    NormalizedMovement,
    ProductModule,
    ReconciliationRule,
)
from apps.hub.reconciliation_service import _matches_condition
from apps.organizations.models import Membership
from apps.platform.operation_access import require_operation_access

TEXT_ACTIONS = {
    "debit_account_code": 64, "credit_account_code": 64,
    "cost_center_code": 64, "accounting_history": 500,
}
BOOL_ACTIONS = {"ignore", "review", "require_review"}
CONDITION_FIELDS = {
    "financial_account", "description", "counterparty", "document", "direction", "amount_cents",
}


class RuleActivationConflict(ValueError):
    pass


def _conditions(rule: ReconciliationRule) -> None:
    if (
        not isinstance(rule.all_conditions, list) or not isinstance(rule.any_conditions, list)
        or not 1 <= len(rule.all_conditions) + len(rule.any_conditions) <= 32
    ):
        raise ValueError("Confira as condições da regra antes de ativar.")
    for condition in [*rule.all_conditions, *rule.any_conditions]:
        if (
            not isinstance(condition, dict)
            or set(condition) != {"field", "operator", "value"}
            or not isinstance(condition["field"], str)
            or condition["field"] not in CONDITION_FIELDS
            or not isinstance(condition["operator"], str)
            or condition["operator"] not in {"equals", "contains", "regex", "range"}
        ):
            raise ValueError("A regra contém uma condição incompatível. Confira sua configuração.")
        value, operator, field = condition["value"], condition["operator"], condition["field"]
        if operator == "range":
            if (
                field != "amount_cents" or not isinstance(value, dict)
                or set(value) != {"min", "max"}
                or any(type(value[key]) is not int for key in ("min", "max"))
                or not 0 <= value["min"] <= value["max"]
            ):
                raise ValueError("Confira a faixa de valores da regra.")
        elif not isinstance(value, str) or not value.strip() or len(value) > 1000:
            raise ValueError("Confira o texto de cada condição da regra.")
        elif operator == "regex":
            if len(value) > 160 or re.search(r"\(\?[:=!<].*[+*].*\)[+*]", value):
                raise ValueError("Confira a expressão regular da regra.")
            try:
                re.compile(value)
            except re.error:
                raise ValueError("A expressão regular da regra não é válida.") from None
        if field == "financial_account" and operator == "equals" and not (
            FinancialAccount.objects.filter(
                organization_id=rule.organization_id, company_id=rule.company_id,
                account_reference=value, active=True,
            ).exists()
        ):
            raise ValueError("A referência bancária da regra precisa de uma conta ativa.")


def _actions(rule: ReconciliationRule) -> None:
    actions = rule.actions
    if (
        not isinstance(actions, dict) or not actions or not any(actions.values())
        or set(actions) - {*TEXT_ACTIONS, *BOOL_ACTIONS}
    ):
        raise ValueError("Confira as ações da regra antes de ativar.")
    for key, value in actions.items():
        if key in BOOL_ACTIONS:
            if type(value) is not bool:
                raise ValueError("As opções de revisão e descarte devem ser explícitas.")
        elif not isinstance(value, str) or not value.strip() or len(value) > TEXT_ACTIONS[key]:
            raise ValueError("Confira os códigos e o histórico da regra.")
    debit, credit = actions.get("debit_account_code"), actions.get("credit_account_code")
    if debit and debit == credit:
        raise ValueError("Débito e crédito precisam ser contas diferentes.")
    for code in {debit, credit} - {None, ""}:
        if not LedgerAccount.objects.filter(
            organization_id=rule.organization_id, company_id=rule.company_id,
            code=code, active=True, accepts_entries=True,
        ).exists():
            raise ValueError("As contas contábeis precisam estar ativas e aceitar lançamentos.")
    if (code := actions.get("cost_center_code")) and not CostCenter.objects.filter(
        organization_id=rule.organization_id, company_id=rule.company_id, code=code, active=True,
    ).exists():
        raise ValueError("Confira o centro de custo da regra: ele precisa estar ativo.")


def _conflicts(rule: ReconciliationRule) -> None:
    exact = {
        item["field"]: item["value"] for item in rule.all_conditions
        if item["operator"] == "equals"
    }
    probe = None
    if {"description", "direction", "financial_account"} <= exact.keys():
        account = FinancialAccount.objects.filter(
            organization_id=rule.organization_id, company_id=rule.company_id,
            account_reference=exact["financial_account"], active=True,
        ).first()
        if account:
            probe = NormalizedMovement(
                organization_id=rule.organization_id, company_id=rule.company_id,
                financial_account=account, description=exact["description"],
                direction=exact["direction"],
            )
    for other in ReconciliationRule.objects.filter(
        organization_id=rule.organization_id, company_id=rule.company_id, state="active",
    ).exclude(pk=rule.pk):
        overlap = (
            other.all_conditions == rule.all_conditions
            and other.any_conditions == rule.any_conditions
        )
        if probe is not None and isinstance(other.all_conditions, list) and isinstance(
            other.any_conditions, list,
        ) and all(isinstance(c, dict) for c in [*other.all_conditions, *other.any_conditions]):
            overlap = overlap or (
                all(_matches_condition(c, probe) for c in other.all_conditions)
                and (not other.any_conditions or any(
                    _matches_condition(c, probe) for c in other.any_conditions
                ))
            )
        if not overlap or not isinstance(other.actions, dict):
            continue
        if bool(other.actions.get("ignore")) != bool(rule.actions.get("ignore")) or any(
            other.actions.get(key) and rule.actions.get(key)
            and other.actions[key] != rule.actions[key]
            for key in TEXT_ACTIONS
        ):
            raise ValueError("Há uma regra ativa conflitante. Confira as regras antes de ativar.")


@transaction.atomic
def set_reconciliation_rule_state(
    *, rule: ReconciliationRule, actor: User, expected_state: str, request: Any = None,
) -> ReconciliationRule:
    company = ClientCompany.objects.select_for_update().get(
        pk=rule.company_id, organization_id=rule.organization_id,
    )
    current = ReconciliationRule.objects.select_for_update().get(
        pk=rule.pk, organization_id=company.organization_id, company=company,
    )
    membership = Membership.objects.select_for_update(of=("self",)).select_related(
        "organization",
    ).filter(
        organization_id=current.organization_id, user=actor, is_active=True,
        user__is_active=True, role__in=["owner", "admin", "manager", "operator"],
    ).first()
    if membership is None or not company_queryset_for_module(
        membership, ProductModule.Code.RECONCILIATION,
    ).filter(pk=company.pk).exists():
        raise PermissionDenied("Seu acesso mudou; reabra a configuração da empresa.")
    require_operation_access(membership.organization, ProductModule.Code.RECONCILIATION)
    if expected_state not in ReconciliationRule.State.values or current.state != expected_state:
        raise RuleActivationConflict("A regra mudou. Reabra a configuração antes de continuar.")
    target = "disabled" if current.state == "active" else "active"
    if target == "active":
        _conditions(current)
        _actions(current)
        _conflicts(current)
    current.state = target
    current.save(update_fields=["state", "updated_at"])
    record_event(
        action="hub.reconciliation.rule.state_changed", actor=actor,
        organization=membership.organization, target=current, request=request,
        metadata={"state": target},
    )
    return current
