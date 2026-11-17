"""Scoped, explicit human review of retained account candidates."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from typing import cast
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, Page, Paginator
from django.db.models import F, Q, QuerySet
from django.http import Http404, HttpRequest, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.hub.account_candidate_forms import (
    AccountCandidateCorrectionForm,
    AccountCandidateDismissForm,
    AccountCandidateLinkForm,
    AccountCandidateReopenForm,
)
from apps.hub.account_candidate_review import (
    CandidateReviewConflict,
    CandidateReviewError,
    dismiss_candidate,
    finalize_candidate,
    revise_candidate,
)
from apps.hub.account_source_details import latest_consistent_source_detail
from apps.hub.models import ClientCompany, ProductModule, ReconciliationAccountCandidate
from apps.hub.module_catalog import definition
from apps.hub.views import _can_manage_reconciliation, _module_page_context, office_required, refuse
from apps.organizations.models import Organization

FILTER_NAMES = ("status", "q", "company", "page")


def _filters(
    params: QueryDict,
    companies: QuerySet[ClientCompany],
) -> tuple[dict[str, str], list[str], ClientCompany | None]:
    values = {key: params.get(key, "").strip() for key in FILTER_NAMES}
    errors = []
    selected = None
    if any(len(params.getlist(key)) > 1 for key in FILTER_NAMES):
        errors.append("Informe cada filtro uma única vez.")
    if "status" not in params:
        values["status"] = "pending"
    if values["status"] not in {"all", *ReconciliationAccountCandidate.State.values}:
        errors.append("Escolha uma situação válida.")
    if len(values["q"]) > 100:
        errors.append("Use até 100 caracteres na busca.")
    if "page" not in params:
        values["page"] = "1"
    if not re.fullmatch(r"[1-9][0-9]{0,8}", values["page"]):
        errors.append("Escolha uma página válida.")
    if "company" in params:
        try:
            selected = companies.filter(pk=uuid.UUID(values["company"])).first()
        except ValueError:
            selected = None
        if selected is None:
            errors.append("Escolha uma empresa disponível para a conciliação.")
    return values, errors, selected


def _query(values: dict[str, str], *, include_page: bool = False) -> str:
    return urlencode(
        {
            key: value
            for key, value in values.items()
            if value and (key != "page" or (include_page and value != "1"))
        }
    )


def _private(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "no-store, private"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@office_required
@require_http_methods(["GET"])
def account_candidates(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    filters, errors, selected = _filters(request.GET, companies)
    candidates = (
        ReconciliationAccountCandidate.objects.filter(
            organization=cast(Organization, context["office"]),
            company__in=companies,
        )
        .filter(
            Q(financial_account__isnull=True)
            | Q(
                financial_account__organization_id=F("organization_id"),
                financial_account__company_id=F("company_id"),
            )
        )
        .select_related("company", "financial_account")
        .order_by("company__name", "account_code", "case_reference", "pk")
    )
    if selected:
        candidates = candidates.filter(company=selected)
    if filters["status"] != "all":
        candidates = candidates.filter(state=filters["status"])
    if filters["q"] and not errors:
        query = filters["q"]
        lookup = (
            Q(company__name__icontains=query)
            | Q(company__dominio_code__icontains=query)
            | Q(case_reference__icontains=query)
        )
        if query.isascii() and query.isdecimal() and 0 < int(query) <= 2147483647:
            lookup |= Q(account_code=int(query))
        candidates = candidates.filter(lookup)
    if errors:
        candidates = candidates.none()
    paginator = Paginator(candidates, 25)
    try:
        page: Page[ReconciliationAccountCandidate] = paginator.page(
            int(filters["page"]) if not errors else 1
        )
    except EmptyPage:
        errors.append("Esta página não está disponível. Escolha a primeira página.")
        page = Paginator(candidates.none(), 25).page(1)
    detail_query = _query(filters, include_page=True)
    rows = [
        {
            "candidate": candidate,
            "url": reverse("hub:reconciliation-account-candidate", args=[candidate.pk])
            + "?"
            + detail_query,
        }
        for candidate in page.object_list
    ]
    context.update(
        {
            "page_title": "Vínculos de contas",
            "candidate_rows": rows,
            "candidate_page": page,
            "candidate_filters": filters,
            "candidate_errors": errors,
            "candidate_company": selected,
            "candidate_querystring": _query(filters),
            "candidate_clear_url": reverse("hub:reconciliation-account-candidates")
            + ("?" + urlencode({"company": str(selected.pk)}) if selected else ""),
            "candidate_portfolio_url": reverse("hub:reconciliation-portfolio")
            + ("?" + urlencode({"company": str(selected.pk)}) if selected else ""),
        }
    )
    return _private(render(request, "hub/reconciliation_account_candidates.html", context))


@office_required
@require_http_methods(["GET", "POST"])
def account_candidate(request: HttpRequest, candidate_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        raise Http404
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    candidate = get_object_or_404(
        ReconciliationAccountCandidate.objects.select_related(
            "company", "financial_account", "reviewed_by"
        ),
        pk=candidate_id,
        organization=context["office"],
        company__in=companies,
    )
    if candidate.financial_account and (
        candidate.financial_account.organization_id != candidate.organization_id
        or candidate.financial_account.company_id != candidate.company_id
    ):
        raise Http404
    filters, errors, selected = _filters(request.GET, companies)
    if selected and selected.pk != candidate.company_id:
        errors.append("A empresa do filtro não corresponde a este vínculo.")
    can_manage = bool(context["support_can_mutate"]) and _can_manage_reconciliation(context)
    pending = candidate.state == ReconciliationAccountCandidate.State.PENDING
    source_detail = latest_consistent_source_detail(candidate)
    link_form = AccountCandidateLinkForm(
        request.POST if request.method == "POST" and request.POST.get("action") == "link" else None,
        candidate=candidate,
    )
    dismiss_form = AccountCandidateDismissForm(candidate=candidate)
    correction_form = AccountCandidateCorrectionForm(candidate=candidate)
    reopen_form = AccountCandidateReopenForm(candidate=candidate)
    status = 400 if errors else 200
    return_query = _query(filters, include_page=True)
    detail_url = reverse("hub:reconciliation-account-candidate", args=[candidate.pk])
    if return_query:
        detail_url += "?" + return_query
    if request.method == "POST":
        if not can_manage:
            return refuse(request, "Seu perfil pode consultar, mas não revisar vínculos de contas.")
        if errors:
            pass
        elif not pending and request.POST.get("action") not in {"correct", "reopen"}:
            errors.append("Este vínculo já foi revisado. Consulte o resultado registrado.")
            status = 409
        else:
            actions = request.POST.getlist("action")
            action = actions[0] if len(actions) == 1 else ""
            if action not in {"link", "dismiss", "correct", "reopen"}:
                errors.append("Escolha uma ação válida para este vínculo.")
                status = 400
            else:
                form_type = {
                    "link": AccountCandidateLinkForm,
                    "dismiss": AccountCandidateDismissForm,
                    "correct": AccountCandidateCorrectionForm,
                    "reopen": AccountCandidateReopenForm,
                }[action]
                form = form_type(request.POST, candidate=candidate)
                if action == "link":
                    link_form = cast(AccountCandidateLinkForm, form)
                elif action == "dismiss":
                    dismiss_form = cast(AccountCandidateDismissForm, form)
                elif action == "correct":
                    correction_form = cast(AccountCandidateCorrectionForm, form)
                else:
                    reopen_form = cast(AccountCandidateReopenForm, form)
                valid = form.is_valid()
                if any(len(request.POST.getlist(name)) > 1 for name in form.fields):
                    form.add_error(None, "Informe cada campo uma única vez.")
                    valid = False
                if valid:
                    operations: dict[str, Callable[..., ReconciliationAccountCandidate]] = {
                        "link": finalize_candidate,
                        "dismiss": dismiss_candidate,
                        "correct": revise_candidate,
                        "reopen": revise_candidate,
                    }
                    operation = operations[action]
                    try:
                        operation(
                            candidate=candidate,
                            actor=cast(User, request.user),
                            authorized_companies=companies,
                            cleaned_data=form.cleaned_data,
                            request=request,
                            **({"reopen": True} if action == "reopen" else {}),
                        )
                    except PermissionDenied:
                        return refuse(request, "Seu acesso mudou. Solicite revisão ao responsável.")
                    except CandidateReviewConflict as exc:
                        form.add_error(None, str(exc))
                        status = 409
                    except CandidateReviewError as exc:
                        form.add_error(None, str(exc))
                        status = 400
                    else:
                        messages.success(
                            request,
                            {
                                "link": "Conta vinculada.",
                                "dismiss": "Decisão registrada: não utilizar esta conta.",
                                "correct": "Vínculo corrigido. A revisão anterior foi preservada.",
                                "reopen": "Vínculo reaberto. Confira as fontes antes de vincular.",
                            }[action],
                        )
                        return _private(redirect(detail_url))
                else:
                    status = 400
    if source_detail and pending:
        if request.method == "GET" and not link_form.is_bound:
            link_form.initial["name"] = source_detail.row["account_name_raw"]
        link_form.fields["name"].help_text = (
            "O nome consultado está acima. Confira ou ajuste conforme o plano de contas."
        )
    link_form.auto_id = "candidate-link-%s"
    dismiss_form.auto_id = "candidate-dismiss-%s"
    correction_form.auto_id = "candidate-correct-%s"
    reopen_form.auto_id = "candidate-reopen-%s"
    history = []
    for review in candidate.review_history if isinstance(candidate.review_history, list) else []:
        if not isinstance(review, dict):
            continue
        raw_date = review.get("reviewed_at")
        try:
            reviewed_at = parse_datetime(raw_date) if isinstance(raw_date, str) else None
        except ValueError:
            reviewed_at = None
        history.append({**review, "reviewed_at_local": reviewed_at})
    context.update(
        {
            "page_title": "Revisar vínculo de conta",
            "candidate": candidate,
            "candidate_source_detail": source_detail,
            "candidate_source_inactive_on": parse_date(source_detail.row["inactive_on_raw"])
            if source_detail and source_detail.row["inactive_on_raw"]
            else None,
            "candidate_source_bank_references": source_detail.provenance["company_counts"][
                "bank_references"
            ]
            if source_detail
            else None,
            "candidate_history": history,
            "candidate_errors": errors,
            "review_form": link_form,
            "dismiss_form": dismiss_form,
            "correction_form": correction_form,
            "reopen_form": reopen_form,
            "can_correct_candidate": can_manage and not pending and not errors,
            "can_review_candidate": can_manage and pending and not errors,
            "candidate_is_pending": pending,
            "candidate_detail_url": detail_url,
            "candidate_list_url": reverse("hub:reconciliation-account-candidates")
            + ("?" + return_query if return_query else ""),
            "candidate_configuration_url": reverse("hub:reconciliation-configuration")
            + "?"
            + urlencode({"company": str(candidate.company_id)})
            + "#contas-financeiras",
            "candidate_inflow_label": {"debit": "Débito", "credit": "Crédito"}.get(
                candidate.review_data.get("bank_inflow_side", ""), "Não registrada"
            )
            if isinstance(candidate.review_data, dict)
            else "Não registrada",
        }
    )
    return _private(
        render(request, "hub/reconciliation_account_candidate.html", context, status=status)
    )
