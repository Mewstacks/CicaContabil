"""Existing account correction within the reconciliation company/module boundary."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, cast
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.hub.models import ClientCompany, FinancialAccount, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.setup_forms import FinancialAccountEditForm
from apps.hub.setup_review import (
    SetupReviewConflict,
    SetupReviewError,
    account_usage_reasons,
    review_financial_account,
)
from apps.hub.views import _can_manage_reconciliation, _module_page_context, office_required, refuse
from apps.organizations.models import Membership


def _private(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "no-store, private"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _history(account: FinancialAccount) -> list[dict[str, Any]]:
    rows = []
    labels = {"name": "Nome da conta", "bank_code": "Código do banco",
              "account_reference": "Agência e conta", "ledger_code": "Conta contábil",
              "active": "Ativa para novos usos"}
    raw = account.review_history if isinstance(account.review_history, list) else []
    for item in reversed(raw):
        if not isinstance(item, dict):
            continue
        try:
            actor_id = uuid.UUID(item["actor_id"])
            occurred_at = datetime.fromisoformat(item["occurred_at"])
            before, after = item["before"], item["after"]
            if not isinstance(before, dict) or not isinstance(after, dict):
                continue
        except (ValueError, TypeError, KeyError):
            continue
        changes = []
        for field, label in labels.items():
            previous, current = before.get(field), after.get(field)
            if previous == current:
                continue
            if field == "active":
                previous, current = ("Sim" if value else "Não" for value in (previous, current))
            changes.append({"label": label, "before": previous, "after": current})
        rows.append({"actor_id": actor_id, "occurred_at": occurred_at,
                     "reason": item.get("reason", ""), "changes": changes})
    authors = {
        member.user_id: member.user.full_name or "Responsável registrado"
        for member in Membership.objects.filter(
            organization_id=account.organization_id,
            user_id__in={row["actor_id"] for row in rows},
        ).select_related("user")
    }
    for row in rows:
        row["actor"] = authors.get(row["actor_id"], "Responsável registrado")
    return rows


@office_required
@require_http_methods(["GET", "POST"])
def financial_account_edit(request: HttpRequest, account_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        raise Http404
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    account = get_object_or_404(
        FinancialAccount.objects.select_related("company", "organization"),
        pk=account_id, organization=context["office"], company__in=companies,
    )
    back_url = reverse("hub:reconciliation-configuration") + "?" + urlencode(
        {"company": str(account.company_id)},
    ) + "#contas-financeiras"
    linked = account.source_candidates.filter(state="linked")
    candidate = linked.filter(
        organization_id=account.organization_id, company_id=account.company_id,
    ).first()
    linked_account = linked.exists()
    can_manage = bool(context["support_can_mutate"]) and _can_manage_reconciliation(context)
    identity_locked = bool(account_usage_reasons(account))
    form = FinancialAccountEditForm(
        request.POST if request.method == "POST" else None,
        account=account, identity_locked=identity_locked,
    )
    status = 200
    errors = []
    if request.method == "POST":
        if not can_manage:
            return _private(refuse(request, "Seu perfil pode consultar, mas não corrigir contas."))
        if linked_account:
            errors.append("Esta conta tem um vínculo revisado. Abra a revisão para corrigi-lo.")
            status = 409
        else:
            valid = form.is_valid()
            if any(len(request.POST.getlist(field)) > 1 for field in form.fields):
                form.add_error(None, "Informe cada campo uma única vez.")
                valid = False
            if valid:
                try:
                    review_financial_account(
                        account=account, actor=cast(User, request.user),
                        authorized_companies=companies, cleaned_data=form.cleaned_data,
                        request=request,
                    )
                except PermissionDenied:
                    return _private(refuse(
                        request, "Seu acesso mudou. Solicite revisão ao responsável."
                    ))
                except SetupReviewError as exc:
                    form.add_error(None, str(exc))
                    status = 409 if isinstance(exc, SetupReviewConflict) else 400
                else:
                    messages.success(
                        request, "Conta corrigida. O motivo foi registrado no histórico."
                    )
                    return _private(redirect(back_url))
            else:
                status = 400
    context.update({
        "page_title": "Corrigir conta financeira", "setup_account": account,
        "setup_form": form, "setup_errors": errors,
        "setup_can_edit": can_manage and not linked_account,
        "setup_identity_locked": identity_locked, "setup_back_url": back_url,
        "setup_linked_account": linked_account,
        "setup_history": _history(account),
        "setup_candidate_url": reverse("hub:reconciliation-account-candidate", args=[candidate.pk])
        if candidate else "",
    })
    return _private(render(request, "hub/reconciliation_account_edit.html", context, status=status))
