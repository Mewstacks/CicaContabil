"""D-391: review of the DE-PARA suggestions learned from the Razão."""

from __future__ import annotations

from typing import Any, cast

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.hub.depara_ledger import LEVEL_LABELS, RULE_PREFIX, discard_suggestion, ledger_rules
from apps.hub.models import ReconciliationRule
from apps.hub.postable_accounts import account_names
from apps.hub.title_ui import private_response, title_workspace
from apps.hub.views import office_required, refuse

DIRECTION_LABELS = {"inflow": "Entrada", "outflow": "Saída"}


@office_required
@require_http_methods(["GET", "POST"])
def depara_ledger_review(request: HttpRequest, account_id: str) -> HttpResponse:
    context, account = title_workspace(request, account_id)
    if account is None:
        raise Http404
    back = reverse("hub:reconciliation-depara-ledger", args=[account.pk])
    if request.method == "POST":
        if not context["title_can_write"]:
            return refuse(request, "Seu perfil pode consultar, mas não alterar as regras.")
        rule = (
            ReconciliationRule.objects.filter(
                pk=str(request.POST.get("rule_id", "")),
                organization=context["office"],
                company=account.company,
                name__startswith=RULE_PREFIX,
            ).first()
            if _is_uuid(request.POST.get("rule_id", ""))
            else None
        )
        if rule is None:
            raise Http404
        from apps.hub.depara_rule_activation import set_reconciliation_rule_state

        try:
            with transaction.atomic():
                if request.POST.get("action") == "discard":
                    discard_suggestion(rule=rule, actor=cast(User, request.user), request=request)
                    messages.success(request, "Sugestão descartada.")
                else:
                    updated = set_reconciliation_rule_state(
                        rule=rule,
                        actor=cast(User, request.user),
                        expected_state=request.POST.get("expected_state", ""),
                        request=request,
                    )
                    messages.success(
                        request,
                        "Regra ativada." if updated.state == "active" else "Regra desativada.",
                    )
        except (ValueError, PermissionDenied) as exc:
            messages.error(request, str(exc))
        return redirect(back)
    rows = ledger_rules(account)
    context.update(
        page_title="Sugestões DE-PARA pelo Razão",
        depara_ledger_account=account,
        depara_ledger_rows=ledger_rule_rows(account, rows),
        depara_ledger_active=sum(rule.state == "active" for rule, _ in rows),
        depara_ledger_back=reverse("hub:reconciliation-depara"),
    )
    return private_response(render(request, "hub/reconciliation_depara_ledger.html", context))


def ledger_rule_rows(account: Any, rows: list[Any] | None = None) -> list[dict[str, Any]]:
    """Razão-derived rules of one bank account, ready for display (also used by D-406)."""
    if rows is None:
        rows = ledger_rules(account)
    codes = {
        code
        for rule, _evidence in rows
        for code in (
            rule.actions.get("debit_account_code"),
            rule.actions.get("credit_account_code"),
        )
        if code
    }
    names = account_names(account.company, codes)
    return [
        {
            "rule": rule,
            "pattern": f"{LEVEL_LABELS.get(evidence.get('level', ''), 'Padrão')} "
            f"“{evidence.get('label', '')}”",
            "direction": DIRECTION_LABELS.get(evidence.get("direction", ""), "—"),
            "debit": rule.actions.get("debit_account_code", ""),
            "debit_name": names.get(str(rule.actions.get("debit_account_code", "")), ""),
            "credit": rule.actions.get("credit_account_code", ""),
            "credit_name": names.get(str(rule.actions.get("credit_account_code", "")), ""),
            "support": evidence.get("support", 0),
            "months": [f"{m[5:]}/{m[:4]}" for m in evidence.get("months", [])],
        }
        for rule, evidence in rows
    ]


def _is_uuid(value: str) -> bool:
    from uuid import UUID

    try:
        UUID(value)
    except (ValueError, TypeError, AttributeError):
        return False
    return True
