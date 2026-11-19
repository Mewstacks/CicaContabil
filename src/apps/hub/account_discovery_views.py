"""Company-scoped browsing and minimal confirmation of the full Domínio catalogue."""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.hub.account_discovery import (
    _consistent_company,
    latest_consistent_discovery,
    prepared_account_facts,
)
from apps.hub.account_discovery_forms import (
    DiscoveryFiltersForm,
    DiscoveryLinkForm,
    OfxPrefillForm,
)
from apps.hub.account_discovery_review import (
    DiscoveryReviewConflict,
    DiscoveryReviewError,
    confirm_discovered_account,
)
from apps.hub.models import (
    ClientCompany,
    ProductModule,
    ReconciliationCompanyDiscovery,
    ReconciliationDiscoveredChartAccount,
)
from apps.hub.module_catalog import definition
from apps.hub.reconciliation import OfxAccountIdentity, OfxParseError, read_ofx_account_identity
from apps.hub.reconciliation_service import MAX_BYTES
from apps.hub.views import _can_manage_reconciliation, _module_page_context, office_required, refuse

COVERAGE_LABELS = {
    "catalogued": "Contas identificadas",
    "options_only": "Plano a conferir",
    "no_accounts": "Sem contas no catálogo consultado",
}
GAP_LABELS = {
    "missing_accounting_parameters": "A consulta não encontrou parâmetros contábeis da empresa.",
    "no_observed_usage": "Não foram encontrados lançamentos na janela consultada.",
    "multiple_observed_plans": "Há referências a mais de um plano; confira a competência.",
    "multiple_observed_branches": (
        "Há mais de uma filial; o vínculo precisa preservar esse alcance."
    ),
    "no_catalogue_accounts": "Nenhuma conta foi retornada para os planos referenciados.",
}
SOURCE_LABELS = {
    "own_code_option": "Catálogo do próprio código da empresa",
    "codi_pad_option": "Referência nos parâmetros da empresa",
    "parameter_reference": "Referência nos parâmetros da empresa",
    "parameter_option": "Referência nos parâmetros da empresa",
    "observed_usage": "Plano utilizado em lançamentos",
    "configured_account": "Referência na configuração de conciliação",
    "configured_accounts": "Referência na configuração de conciliação",
    "configured_reference": "Referência na configuração de conciliação",
    "equivalent_account": "Referência em contas equivalentes",
    "equivalent_accounts": "Referência em contas equivalentes",
    "equivalent_reference": "Referência em contas equivalentes",
}


PREFILL_FIELDS = {"bank_code", "account_reference"}


def _read_prefill(form: OfxPrefillForm) -> tuple[OfxAccountIdentity | None, str]:
    """Read the bank identity of one uploaded OFX without storing or logging it (D-377)."""

    if not form.is_valid():
        return None, "Anexe um único extrato OFX ou QFX desta conta."
    upload = form.cleaned_data["statement"]
    name = str(getattr(upload, "name", "") or "")
    if not name.lower().endswith((".ofx", ".qfx")):
        return None, "Use o extrato no formato OFX ou QFX para ler banco e conta."
    if (upload.size or 0) > MAX_BYTES:
        return None, "O extrato excede 25 MB. Use o arquivo do período de uma competência."
    content = upload.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        return None, "O extrato excede 25 MB. Use o arquivo do período de uma competência."
    try:
        return read_ofx_account_identity(content), ""
    except OfxParseError as exc:
        return None, f"Não foi possível ler o extrato: {exc}"


def _private(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "no-store, private"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _filters(request: HttpRequest) -> tuple[dict[str, Any], list[str]]:
    values = request.GET.copy()
    if "month" not in values:
        values["month"] = timezone.localdate().strftime("%Y-%m")
    form = DiscoveryFiltersForm(values)
    errors = []
    if any(len(values.getlist(name)) > 1 for name in form.fields):
        errors.append("Informe cada filtro uma única vez.")
    if not form.is_valid():
        errors.extend(str(error) for field in form.errors.values() for error in field)
    filters = {
        "month": values.get("month", ""),
        "q": values.get("q", ""),
        "page": 1,
        "chart": None,
    }
    if not errors:
        filters.update(form.cleaned_data)
        filters["page"] = filters["page"] or 1
    return filters, errors


def _query(filters: dict[str, Any], *, page: bool = False, search: bool = True) -> str:
    return urlencode(
        {
            key: value
            for key, value in filters.items()
            if value and (key != "page" or (page and value != 1)) and (search or key != "q")
        }
    )


def _page(queryset: QuerySet[Any], filters: dict[str, Any], errors: list[str]) -> Any:
    if errors:
        queryset = queryset.none()
    try:
        return Paginator(queryset, 25).page(filters["page"])
    except EmptyPage:
        errors.append("Esta página não está disponível. Volte à primeira página.")
        return Paginator(queryset.none(), 25).page(1)


def _company_record(context: dict[str, Any], company_id: str, discovery: Any) -> Any:
    company = get_object_or_404(context["companies"], pk=company_id)
    if discovery is None:
        raise Http404
    record = get_object_or_404(
        ReconciliationCompanyDiscovery.objects.select_related("company", "discovery").defer(
            "discovery__source_data"
        ),
        discovery=discovery,
        organization=context["office"],
        company=company,
    )
    if not _consistent_company(record):
        raise Http404
    return record


def _links(record: ReconciliationCompanyDiscovery, month: str) -> list[dict[str, Any]]:
    links = []
    for item in record.facts.get("chart_links", []):
        observed = [
            row
            for row in item.get("observed_usage", [])
            if f"{row['year']:04d}-{row['month']:02d}" == month
        ]
        links.append(
            {
                **item,
                "label": f"Plano {item['chart_company_code']}",
                "source_labels": list(
                    dict.fromkeys(
                        SOURCE_LABELS.get(value, "Referência no cadastro")
                        for value in item["sources"]
                    )
                ),
                "observed_in_month": bool(observed),
                "branches": sorted({row["branch_code"] for row in observed}),
            }
        )
    return links


@office_required
@require_http_methods(["GET"])
def account_discovery(request: HttpRequest) -> HttpResponse:
    page_context, blocked = _module_page_context(
        request, definition(ProductModule.Code.RECONCILIATION)
    )
    context = cast(dict[str, Any], page_context)
    if blocked:
        return blocked
    discovery = latest_consistent_discovery(context["office"])
    filters, errors = _filters(request)
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    records = (
        ReconciliationCompanyDiscovery.objects.filter(
            discovery=discovery,
            organization=context["office"],
            company__in=companies,
        )
        .select_related("company")
        .order_by("company__name", "company_id")
    )
    scoped_count = records.count()
    if filters["q"] and not errors:
        records = records.filter(
            Q(company__name__icontains=filters["q"])
            | Q(company__dominio_code__icontains=filters["q"])
        )
    page = _page(records, filters, errors)
    rows = []
    for record in page.object_list:
        record.discovery = discovery
        if not _consistent_company(record):
            errors.append("Uma fonte de empresa precisa ser conferida antes de exibir suas contas.")
            continue
        links = _links(record, filters["month"])
        rows.append(
            {
                "record": record,
                "coverage_label": COVERAGE_LABELS.get(
                    record.coverage_state, "Conferência pendente"
                ),
                "plan_count": sum(1 for item in links if item["account_count"]),
                "account_count": sum(item["account_count"] for item in links),
                "url": reverse("hub:reconciliation-discovered-company", args=[record.company_id])
                + "?"
                + urlencode({"month": filters["month"]}),
            }
        )
    context.update(
        page_title="Planos e contas do Domínio",
        discovery=discovery,
        discovery_rows=rows,
        discovery_scoped_count=scoped_count,
        discovery_company_count=companies.count(),
        discovery_page=page,
        discovery_filters=filters,
        discovery_errors=errors,
        discovery_querystring=_query(filters),
        discovery_clear_url=reverse("hub:reconciliation-account-discovery")
        + "?"
        + urlencode({"month": filters["month"]}),
        discovery_portfolio_url=reverse("hub:reconciliation-portfolio")
        + "?"
        + urlencode({"month": filters["month"]}),
    )
    return _private(
        render(
            request,
            "hub/reconciliation_account_discovery.html",
            context,
            status=400 if errors else 200,
        )
    )


@office_required
@require_http_methods(["GET"])
def discovered_company(request: HttpRequest, company_id: str) -> HttpResponse:
    page_context, blocked = _module_page_context(
        request, definition(ProductModule.Code.RECONCILIATION)
    )
    context = cast(dict[str, Any], page_context)
    if blocked:
        raise Http404
    discovery = latest_consistent_discovery(context["office"])
    record = _company_record(context, company_id, discovery)
    filters, errors = _filters(request)
    links = _links(record, filters["month"])
    owners = [item["chart_company_code"] for item in links]
    if filters["chart"] and filters["chart"] not in owners:
        errors.append("Escolha um plano disponível para esta empresa.")
    accounts = ReconciliationDiscoveredChartAccount.objects.filter(
        discovery=discovery,
        organization=context["office"],
        chart_company_code__in=owners,
    ).order_by("chart_company_code", "row__classification_raw", "account_code", "pk")
    if filters["chart"]:
        accounts = accounts.filter(chart_company_code=filters["chart"])
    if filters["q"] and not errors:
        query = filters["q"]
        lookup = Q(row__account_name_raw__icontains=query) | Q(
            row__classification_raw__icontains=query
        )
        if query.isascii() and query.isdecimal() and 0 < int(query) <= 2147483647:
            lookup |= Q(account_code=int(query))
        accounts = accounts.filter(lookup)
    page = _page(accounts, filters, errors)
    query = _query(filters, page=True)
    rows = [
        {
            "account": account,
            "url": reverse(
                "hub:reconciliation-discovered-account", args=[record.company_id, account.pk]
            )
            + "?"
            + query,
        }
        for account in page.object_list
    ]
    context.update(
        page_title="Contas do Domínio",
        discovery=discovery,
        discovery_company=record.company,
        discovery_company_record=record,
        discovery_links=links,
        discovery_gaps=[
            GAP_LABELS.get(value, "Há dados de origem que precisam de conferência.")
            for value in record.gaps
        ],
        discovery_rows=rows,
        discovery_page=page,
        discovery_filters=filters,
        discovery_errors=errors,
        discovery_querystring=_query(filters),
        discovery_clear_url=reverse("hub:reconciliation-discovered-company", args=[company_id])
        + "?"
        + urlencode({"month": filters["month"]}),
        discovery_back_url=reverse("hub:reconciliation-account-discovery")
        + "?"
        + urlencode({"month": filters["month"]}),
    )
    return _private(
        render(
            request,
            "hub/reconciliation_discovered_company.html",
            context,
            status=400 if errors else 200,
        )
    )


@office_required
@require_http_methods(["GET", "POST"])
def discovered_account(request: HttpRequest, company_id: str, account_id: str) -> HttpResponse:
    page_context, blocked = _module_page_context(
        request, definition(ProductModule.Code.RECONCILIATION)
    )
    context = cast(dict[str, Any], page_context)
    if blocked:
        raise Http404
    discovery = latest_consistent_discovery(context["office"])
    record = _company_record(context, company_id, discovery)
    filters, errors = _filters(request)
    owners = [item["chart_company_code"] for item in record.facts.get("chart_links", [])]
    account = get_object_or_404(
        ReconciliationDiscoveredChartAccount,
        pk=account_id,
        discovery=discovery,
        organization=context["office"],
        chart_company_code__in=owners,
    )
    prepared = (
        prepared_account_facts(record, account, month=filters["month"])
        if not errors
        else {"valid": False, "pending_fields": []}
    )
    if not prepared.get("valid") and not errors:
        errors.append("Esta fonte precisa ser conferida. Volte às contas e reabra a ficha.")
    blocking_reason = str(prepared.get("blocking_reason") or "")
    blocking_message = {
        "unsupported_observed_branch": (
            "O Domínio informou filial zero nesta competência. A coleta desta conta "
            "precisa de ajuste técnico antes de prosseguir; nenhuma confirmação sua "
            "é necessária para resolver esse impedimento."
        ),
        "previously_dismissed_candidate": (
            "Esta conta foi descartada em uma conferência anterior. Consulte essa decisão "
            "antes de reconsiderar o vínculo."
        ),
    }.get(blocking_reason, "Esta conta precisa de revisão antes de preparar a coleta.")
    can_manage = bool(context["support_can_mutate"]) and _can_manage_reconciliation(context)
    prefilling = request.method == "POST" and request.POST.get("action") == "prefill"
    prefill: OfxAccountIdentity | None = None
    prefill_error = ""
    prefill_form = OfxPrefillForm()
    prefill_initial: dict[str, str] = {}
    if prefilling:
        if not can_manage:
            return refuse(
                request, "Seu perfil pode consultar, mas não confirmar vínculos de contas."
            )
        uploads = request.FILES.getlist("statement")
        if len(request.POST.getlist("action")) != 1 or len(uploads) > 1:
            prefill_error = "Anexe um único extrato OFX ou QFX desta conta."
        elif blocking_reason or errors or not prepared.get("valid"):
            prefill_error = "Esta ficha não aceita vínculo agora; nada foi lido."
        elif not PREFILL_FIELDS & set(prepared.get("pending_fields", [])):
            prefill_error = "Banco e conta desta ficha já foram conferidos; nada foi lido."
        else:
            prefill, prefill_error = _read_prefill(OfxPrefillForm(request.POST, request.FILES))
        if prefill is not None:
            prefill_initial = {
                "bank_code": prefill.bank_id,
                "account_reference": prefill.account_reference,
            }
    form = DiscoveryLinkForm(
        request.POST if request.method == "POST" and not prefilling else None,
        prepared=prepared,
        initial=prefill_initial,
    )
    status = 400 if errors or prefill_error else 200
    detail_url = reverse("hub:reconciliation-discovered-account", args=[company_id, account_id])
    query = _query(filters, page=True)
    if query:
        detail_url += "?" + query
    if request.method == "POST" and not prefilling:
        if not can_manage:
            return refuse(
                request, "Seu perfil pode consultar, mas não confirmar vínculos de contas."
            )
        if blocking_reason:
            errors.append(blocking_message)
            status = 409
        if not errors:
            valid = form.is_valid()
            if any(len(request.POST.getlist(name)) > 1 for name in form.fields):
                form.add_error(None, "Informe cada campo uma única vez.")
                valid = False
            if valid and form.cleaned_data["expected_revision"] != prepared.get("revision"):
                errors.append("O vínculo ou a fonte mudou. Reabra a ficha antes de confirmar.")
                valid = False
                status = 409
            if valid:
                try:
                    confirm_discovered_account(
                        company_discovery=record,
                        chart_account=account,
                        month=filters["month"],
                        actor=cast(User, request.user),
                        authorized_companies=context["companies"],
                        expected_revision=form.cleaned_data["expected_revision"],
                        confirmed_data={
                            key: value
                            for key, value in form.cleaned_data.items()
                            if key != "expected_revision"
                        },
                        request=request,
                    )
                except PermissionDenied:
                    return refuse(request, "Seu acesso mudou. Solicite revisão ao responsável.")
                except DiscoveryReviewConflict as exc:
                    form.add_error(None, str(exc))
                    status = 409
                except DiscoveryReviewError as exc:
                    form.add_error(None, str(exc))
                    status = 400
                else:
                    messages.success(
                        request,
                        "Vínculo registrado. A fonte e sua conferência foram preservadas.",
                    )
                    return redirect(detail_url)
            else:
                if status != 409:
                    status = 400
    for field in form:
        if field.is_hidden:
            continue
        attrs = field.field.widget.attrs
        ids = []
        if field.help_text:
            ids.append(f"{field.id_for_label}_helptext")
        if field.errors:
            attrs["aria-invalid"] = "true"
            ids.append(f"{field.id_for_label}_error")
        if ids:
            attrs["aria-describedby"] = " ".join(ids)
    known = prepared.get("known_fields", {})
    existing_id = prepared.get("existing_financial_account_id")
    context.update(
        page_title="Conferir vínculo da conta",
        discovery=discovery,
        discovery_company=record.company,
        discovery_account=account,
        discovery_prepared=prepared,
        discovery_known=known,
        discovery_errors=errors,
        discovery_form=form,
        discovery_prefill=prefill,
        discovery_prefill_error=prefill_error,
        discovery_prefill_form=prefill_form,
        discovery_prefill_available=bool(PREFILL_FIELDS & set(form.fields)),
        discovery_can_confirm=bool(
            can_manage
            and prepared.get("valid")
            and not prepared.get("collection_ready")
            and not blocking_reason
        ),
        discovery_blocking_message=blocking_message if blocking_reason else "",
        discovery_candidate_url=(
            reverse(
                "hub:reconciliation-account-candidate",
                args=[prepared["existing_candidate_id"]],
            )
            if blocking_reason == "previously_dismissed_candidate"
            and prepared.get("existing_candidate_id")
            else ""
        ),
        discovery_detail_url=detail_url,
        discovery_back_url=reverse("hub:reconciliation-discovered-company", args=[company_id])
        + "?"
        + query,
        discovery_month=filters["month"],
        discovery_ledger_url=(
            reverse("hub:reconciliation-ledger-request")
            + "?"
            + urlencode({"company": company_id, "account": existing_id, "month": filters["month"]})
        )
        if existing_id
        else "",
    )
    return _private(
        render(request, "hub/reconciliation_discovered_account.html", context, status=status)
    )
