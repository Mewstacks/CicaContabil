"""Shared request scope and presentation for customer title review."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from apps.hub.models import FinancialAccount, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.title_persistence import authorize_title_account
from apps.hub.views import _can_manage_reconciliation, _module_page_context


def private_response(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "no-store, private"
    response["X-Content-Type-Options"] = "nosniff"
    response["Referrer-Policy"] = "same-origin"
    return response


def brl(cents: int | None) -> str:
    if cents is None:
        return "Não informado"
    if type(cents) is not int:
        raise ValueError("O valor monetário exige centavos inteiros.")
    absolute = abs(cents)
    whole = f"{absolute // 100:,}".replace(",", ".")
    return f"{'-' if cents < 0 else ''}{whole},{absolute % 100:02d}"


def has_duplicate_fields(data: Any, names: Any) -> bool:
    return any(len(data.getlist(name)) > 1 for name in names)


def title_workspace(
    request: HttpRequest, account_id: Any = None, *, write: bool = False
) -> tuple[dict[str, Any], FinancialAccount | None]:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        raise Http404
    accounts = (
        FinancialAccount.objects.select_related("company", "organization")
        .filter(organization=context["office"], company__in=context["companies"])
        .order_by("company__name", "name", "pk")
    )
    selected_company = None
    if len(request.GET.getlist("company")) > 1 or len(request.GET.getlist("account")) > 1:
        raise Http404
    if request.GET.get("company"):
        try:
            company_id = UUID(request.GET["company"])
        except (ValueError, TypeError, AttributeError):
            raise Http404 from None
        selected_company = get_object_or_404(context["companies"], pk=company_id)
        accounts = accounts.filter(company=selected_company)
    selected = account_id if account_id is not None else request.GET.get("account")
    account = None
    if selected:
        try:
            identifier = UUID(str(selected))
        except (ValueError, TypeError, AttributeError):
            raise Http404 from None
        account = get_object_or_404(accounts, pk=identifier)
    can_write = bool(context["support_can_mutate"]) and _can_manage_reconciliation(context)
    if account is not None and can_write:
        try:
            authorize_title_account(account, request.user)
        except (PermissionDenied, ValueError):
            can_write = False
    if write and (account is None or not can_write):
        raise PermissionDenied("Seu acesso atual não permite revisar títulos desta conta.")
    back = reverse("hub:reconciliation-portfolio")
    if account is not None:
        back += "?" + urlencode({"company": str(account.company_id), "status": "all"})
    context.update(
        {
            "page_title": "Títulos e baixas",
            "title_accounts": accounts,
            "title_account": account,
            "title_company": selected_company,
            "title_can_write": can_write,
            "title_back_url": back,
        }
    )
    return context, account
