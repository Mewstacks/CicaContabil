"""Customer-led ledger requests, with bank uploads independent of agent availability."""

from __future__ import annotations

import calendar
from contextlib import suppress
from datetime import date, timedelta
from functools import partial
from typing import Any, cast
from urllib.parse import urlencode
from uuid import UUID, uuid4

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.hub.ledger_request_forms import LedgerMappingForm, LedgerMonthField, LedgerRequestForm
from apps.hub.models import (
    FinancialAccount,
    ProductModule,
    ReconciliationRun,
    ReconciliationSourceFile,
)
from apps.hub.module_catalog import definition
from apps.hub.reconciliation import OfxParseError, import_ofx
from apps.hub.reconciliation_service import ReconciliationError, create_source_file
from apps.hub.title_ui import has_duplicate_fields, private_response
from apps.hub.views import _can_manage_reconciliation, _module_page_context, office_required
from apps.intelligence.models import NativeLedgerCollection
from apps.organizations.models import Organization

FILTERS = ("company", "account", "month", "bank_source", "start", "end", "page", "sources_page")
HISTORY_PAGE_SIZE = 20


class LedgerHistoryPageError(ValueError):
    pass


def _page_number(value: str) -> int:
    if not value.isascii() or not value.isdigit() or not 1 <= len(value) <= 8 or int(value) < 1:
        raise LedgerHistoryPageError("Escolha uma página válida para consultar o histórico.")
    return int(value)


def _history_page(query: Any, value: str, label: str) -> Any:
    try:
        return Paginator(query, HISTORY_PAGE_SIZE).page(_page_number(value))
    except EmptyPage:
        raise LedgerHistoryPageError(
            f"Esta página de {label} não existe. Volte à primeira página do histórico."
        ) from None


def _url(
    account: FinancialAccount, month: date, source: Any = None, *,
    page: int = 1, sources_page: int = 1,
) -> str:
    query = {
        "company": str(account.company_id),
        "account": str(account.pk),
        "month": month.strftime("%Y-%m"),
    }
    if source:
        query["bank_source"] = str(source.pk)
    if page != 1:
        query["page"] = str(page)
    if sources_page != 1:
        query["sources_page"] = str(sources_page)
    return reverse("hub:reconciliation-ledger-request") + "?" + urlencode(query)


def _workspace(request: HttpRequest, *, write: bool = False) -> dict[str, Any]:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        raise Http404
    writable = bool(context["support_can_mutate"]) and _can_manage_reconciliation(context)
    if write and (not writable or cast(Organization, context["office"]).is_demo):
        raise PermissionDenied("Seu acesso atual não permite enviar arquivos ou solicitar o Razão.")
    context.update(
        page_title="Extrato e Razão",
        ledger_can_write=writable,
        ledger_errors=[],
        ledger_back_url=reverse("hub:reconciliation-portfolio"),
    )
    return context


def _source(account: FinancialAccount, identifier: Any) -> ReconciliationSourceFile | None:
    if not identifier:
        return None
    try:
        identifier = UUID(str(identifier))
    except (ValueError, TypeError, AttributeError):
        raise Http404 from None
    return get_object_or_404(
        ReconciliationSourceFile,
        pk=identifier,
        organization_id=account.organization_id,
        company_id=account.company_id,
        financial_account=account,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )


def _conference(source: ReconciliationSourceFile | None, month: date) -> str:
    if source is None:
        return ""
    end = month.replace(day=calendar.monthrange(month.year, month.month)[1])
    return (
        reverse("hub:reconciliation-source-review", args=[source.pk])
        + "?"
        + urlencode(
            {
                "start": month.isoformat(),
                "end": end.isoformat(),
                "portfolio_return": reverse("hub:reconciliation-portfolio")
                + "?"
                + urlencode(
                    {
                        "company": str(source.company_id),
                        "account": str(source.financial_account_id),
                        "month": month.strftime("%Y-%m"),
                        "status": "all",
                    }
                ),
            }
        )
    )


def _job_row(
    data: dict[str, Any], source: ReconciliationSourceFile | None, *,
    page: int = 1, sources_page: int = 1,
) -> dict[str, Any]:
    job, month = data["job"], data["month"]
    source = data.get("bank_source") or source
    if isinstance(month, str):
        month = LedgerMonthField().clean(month[:7])
    status = data["status"]
    params = {"bank_source": str(source.pk)} if source else {}
    if page != 1:
        params["page"] = str(page)
    if sources_page != 1:
        params["sources_page"] = str(sources_page)
    query = "?" + urlencode(params) if params else ""
    return {
        **data,
        "month_label": month.strftime("%m/%Y"),
        "created_at": job.created_at,
        "poll": status in {"queued", "delivered"},
        "status_class": "is-active"
        if status in {"imported", "empty"}
        else "is-warning"
        if status in {"review", "failed"}
        else "is-muted",
        "conference_url": _conference(source, month) if status in {"imported", "empty"} else "",
        "status_url": reverse("hub:reconciliation-ledger-status", args=[job.pk]) + query,
        "retry_url": reverse("hub:reconciliation-ledger-retry", args=[job.pk]) + query,
        "retry_key": uuid4(),
    }


def _populate(request: HttpRequest, context: dict[str, Any], form: LedgerRequestForm) -> None:
    from apps.hub.ledger_requests import ledger_job_context, ledger_request_context

    account, month = form.cleaned_data["account"], form.cleaned_data["month"]
    data = ledger_request_context(account=account, actor=cast(User, request.user))
    source = form.cleaned_data.get("bank_source")
    current = _url(account, month, source)
    agent_state = data["agent_state"]
    context.update(
        ledger_account=account,
        ledger_month=month.strftime("%Y-%m"),
        ledger_start=month,
        ledger_end=form.cleaned_data["end"],
        ledger_current_url=current,
        ledger_mapping_revision=data["mapping_revision"],
        ledger_data=data,
        ledger_can_request=bool(context["ledger_can_write"] and data["readiness"]),
        ledger_agent_label=agent_state["label"],
        ledger_agent_detail=agent_state["detail"],
        ledger_installer_url=agent_state.get("installer_url", ""),
        ledger_agent_attention=agent_state["code"] not in {"ready", "online"},
        ledger_readiness_message=" ".join(data["errors"]),
        ledger_configuration_url=reverse(
            "hub:reconciliation-financial-account-edit", args=[account.pk]
        ),
        ledger_back_url=reverse("hub:reconciliation-portfolio")
        + "?"
        + urlencode(
            {
                "company": str(account.company_id),
                "account": str(account.pk),
                "month": month.strftime("%Y-%m"),
                "status": "all",
            }
        ),
    )
    if "ledger_mapping_form" not in context:
        context["ledger_mapping_form"] = LedgerMappingForm(
            prefix="mapping",
            initial={
                **data["mapping_fields"],
                "expected_revision": data["mapping_revision"],
            },
        )
    # Filter before paginating: newer requests in other months must never hide this month.
    jobs = NativeLedgerCollection.objects.filter(
        organization_id=account.organization_id,
        financial_account=account,
        scope__period_start=month.isoformat(),
    ).order_by("-created_at", "-id")
    sources = ReconciliationSourceFile.objects.filter(
        organization_id=account.organization_id,
        company_id=account.company_id,
        financial_account=account,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    ).order_by("-created_at", "-id")
    jobs_page = _history_page(jobs, form.data.get("page", "1"), "solicitações")
    sources_page = _history_page(sources, form.data.get("sources_page", "1"), "extratos")
    pages = {"page": jobs_page.number, "sources_page": sources_page.number}
    context.update(
        ledger_jobs_page=jobs_page,
        ledger_sources_page=sources_page,
        ledger_current_url=_url(account, month, source, **pages),
        ledger_jobs=[
            _job_row(
                ledger_job_context(job=job, actor=cast(User, request.user)), source, **pages
            )
            for job in jobs_page
        ],
    )
    for name, page, parameter, anchor in (
        ("jobs", jobs_page, "page", "ledger-requests"),
        ("sources", sources_page, "sources_page", "ledger-bank-sources"),
    ):
        for direction, available, number in (
            ("previous", page.has_previous(), page.number - 1),
            ("next", page.has_next(), page.number + 1),
        ):
            context[f"ledger_{name}_{direction}_url"] = (
                _url(account, month, source, **{**pages, parameter: number}) + "#" + anchor
                if available else ""
            )
    from apps.hub.direct_use import direct_use_enabled

    direct_use = direct_use_enabled(account.organization)
    source_rows = []
    for item in sources_page:
        run = item.runs.order_by("-created_at", "-id").first()
        label = run.get_state_display() if run else "Arquivo recebido"
        if direct_use and run and run.state == ReconciliationRun.State.REVIEW:
            label = "Importado"  # D-393/D-399: nothing waits for a review in direct use
        target, action = "", ""
        if run and run.state in {
            ReconciliationRun.State.WAITING,
            ReconciliationRun.State.PROCESSING,
        }:
            target, action = reverse("hub:reconciliation") + "#processamentos", "Ver processamento"
        elif run and run.stage == "mapping":
            target, action = reverse("hub:reconciliation-mapping", args=[item.pk]), "Mapear colunas"
        elif run and (
            run.stage in {"financial_account_review", "ocr_review"}
            or run.state in {"failed", "canceled"}
        ):
            target, action = reverse("hub:reconciliation") + "#processamentos", "Revisar importação"
        else:
            target = _conference(item, month)
            action = "Ver resultado" if direct_use else "Abrir conferência"
        source_rows.append({"source": item, "label": label, "url": target, "action": action})
    context["ledger_bank_sources"] = source_rows


def _upload(request: HttpRequest, form: LedgerRequestForm) -> tuple[ReconciliationSourceFile, bool]:
    account = form.cleaned_data["account"]
    upload = form.cleaned_data["statement"]
    content = upload.read()
    source, run, created = create_source_file(
        organization=account.organization,
        company=account.company,
        financial_account=account,
        filename=upload.name,
        content=content,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
        actor=cast(User, request.user),
        request=request,
    )
    if source.kind == ReconciliationSourceFile.Kind.OFX:
        with suppress(OfxParseError):
            import_ofx(
                organization=account.organization,
                company=account.company,
                financial_account=account,
                filename=upload.name,
                content=content,
                actor=cast(User, request.user),
                request=request,
            )
    if created:
        from apps.hub.tasks import process_reconciliation_run

        transaction.on_commit(partial(process_reconciliation_run.delay, str(run.pk)))
    return source, created


def _render(request: HttpRequest, context: dict[str, Any], status: int = 200) -> HttpResponse:
    return private_response(
        render(request, "hub/reconciliation_ledger_request.html", context, status=status)
    )


@office_required
@require_http_methods(["GET", "POST"])
def ledger_request(request: HttpRequest) -> HttpResponse:
    context = _workspace(request, write=request.method == "POST")
    values = request.POST.copy() if request.method == "POST" else request.GET.copy()
    if has_duplicate_fields(
        values, (*FILTERS, "action", "request_key", "expected_mapping_revision")
    ):
        context["ledger_errors"] = ["Informe cada campo uma única vez."]
        context["ledger_form"] = LedgerRequestForm(
            organization=context["office"], companies=context["companies"]
        )
        return _render(request, context, 400)
    action = values.get("action", "")
    if request.method == "GET" or action == "mapping":
        values["request_key"] = str(uuid4())
    if "month" not in values:
        # D-397: the last closed month; the current one is still being booked in Domínio.
        values["month"] = (timezone.localdate().replace(day=1) - timedelta(days=1)).strftime(
            "%Y-%m"
        )
    form = LedgerRequestForm(
        values if values.get("account") or request.method == "POST" else None,
        request.FILES or None,
        organization=context["office"],
        companies=context["companies"],
        initial={**values.dict(), "request_key": uuid4()},
    )
    context["ledger_form"] = form
    if not form.is_bound:
        return _render(request, context)
    if not form.is_valid():
        return _render(request, context, 400)
    try:
        _populate(request, context, form)
    except LedgerHistoryPageError as exc:
        context["ledger_errors"] = [str(exc)]
        context["ledger_history_error"] = True
        return _render(request, context, 400)
    except ValueError:
        raise PermissionDenied(
            "Seu acesso atual não permite consultar a coleta desta conta."
        ) from None
    account, month = form.cleaned_data["account"], form.cleaned_data["month"]
    if request.method == "GET":
        form_data = cast(QueryDict, form.data).copy()
        form_data["expected_mapping_revision"] = context["ledger_mapping_revision"]
        form.data = form_data
        return _render(request, context)
    if action == "mapping":
        from apps.hub.ledger_requests import save_ledger_mapping

        mapping = LedgerMappingForm(request.POST, prefix="mapping")
        context["ledger_mapping_form"] = mapping
        if mapping.is_valid():
            try:
                save_ledger_mapping(
                    account=account,
                    actor=cast(User, request.user),
                    request=request,
                    **mapping.cleaned_data,
                )
            except ValueError as exc:
                mapping.add_error(None, str(exc))
            else:
                messages.success(request, "Vínculo salvo.")
                return redirect(context["ledger_current_url"])
        return _render(request, context, 400)
    if action not in {"request", "upload"}:
        context["ledger_errors"] = ["Escolha enviar o extrato ou buscar o Razão."]
        return _render(request, context, 400)
    source = form.cleaned_data.get("bank_source")
    if form.cleaned_data.get("statement"):
        try:
            source, created = _upload(request, form)
        except ReconciliationError as exc:
            form.add_error("statement", str(exc))
            return _render(request, context, 400)
        context["ledger_upload_notice"] = (
            "Extrato recebido." if created else "Extrato já recebido; não foi duplicado."
        )
        data = cast(QueryDict, form.data).copy()
        data["bank_source"] = str(source.pk)
        form = LedgerRequestForm(
            data, organization=context["office"], companies=context["companies"]
        )
        assert form.is_valid()
        context["ledger_form"] = form
        _populate(request, context, form)
    if action == "upload":
        if source is None:
            form.add_error("statement", "Escolha o extrato que deseja enviar.")
            return _render(request, context, 400)
        messages.success(request, context.get("ledger_upload_notice", "Extrato selecionado."))
        return redirect(_url(account, month, source))
    from apps.hub.ledger_requests import request_ledger

    try:
        _job, created = request_ledger(
            account=account,
            actor=cast(User, request.user),
            month=month,
            request_key=form.cleaned_data["request_key"],
            expected_mapping_revision=form.cleaned_data["expected_mapping_revision"],
            bank_source=source,
            request=request,
        )
    except ValueError as exc:
        context["ledger_errors"] = [str(exc)]
        return _render(request, context, 409)
    messages.success(
        request, "Busca do Razão solicitada." if created else "Esta solicitação já está registrada."
    )
    return redirect(_url(account, month, source) + "#ledger-requests")


def _scoped_job(request: HttpRequest, identifier: UUID, *, write: bool = False) -> tuple[Any, Any]:
    context = _workspace(request, write=write)
    job = get_object_or_404(
        NativeLedgerCollection.objects.select_related("financial_account__company"),
        pk=identifier,
        organization=context["office"],
        financial_account__company__in=context["companies"],
        financial_account__organization=context["office"],
    )
    return context, job


@office_required
@require_http_methods(["GET"])
def ledger_status(request: HttpRequest, job_id: UUID) -> HttpResponse:
    from apps.hub.ledger_requests import ledger_job_context

    context, job = _scoped_job(request, job_id)
    if has_duplicate_fields(request.GET, ("bank_source", "page", "sources_page")):
        return private_response(
            JsonResponse({"detail": "Informe cada filtro uma única vez."}, status=400)
        )
    source = _source(job.financial_account, request.GET.get("bank_source"))
    try:
        pages = {key: _page_number(request.GET.get(key, "1")) for key in ("page", "sources_page")}
        data = _job_row(
            ledger_job_context(job=job, actor=cast(User, request.user)), source, **pages
        )
    except LedgerHistoryPageError as exc:
        return private_response(JsonResponse({"detail": str(exc)}, status=400))
    except ValueError:
        return private_response(
            JsonResponse(
                {"detail": "Reabra a solicitação para conferir seu acesso e a fonte."}, status=409
            )
        )
    data["can_retry"] = bool(data["can_retry"] and context["ledger_can_write"])
    result = {
        key: data[key]
        for key in ("status", "label", "detail", "poll", "conference_url", "can_retry")
    }
    if data["can_retry"]:
        from apps.hub.ledger_requests import ledger_request_context

        current = ledger_request_context(
            account=job.financial_account, actor=cast(User, request.user)
        )
        result.update(
            retry_url=data["retry_url"],
            retry_key=str(data["retry_key"]),
            mapping_revision=current["mapping_revision"],
        )
    return private_response(JsonResponse(result))


@office_required
@require_http_methods(["POST"])
def ledger_retry(request: HttpRequest, job_id: UUID) -> HttpResponse:
    from apps.hub.ledger_requests import ledger_job_context, retry_ledger_request

    _context, job = _scoped_job(request, job_id, write=True)
    if has_duplicate_fields(
        request.POST, ("request_key", "expected_mapping_revision")
    ) or has_duplicate_fields(request.GET, ("bank_source", "page", "sources_page")):
        return private_response(HttpResponse("Informe cada campo uma única vez.", status=400))
    source = _source(job.financial_account, request.GET.get("bank_source"))
    try:
        pages = {key: _page_number(request.GET.get(key, "1")) for key in ("page", "sources_page")}
        key = UUID(request.POST.get("request_key", ""))
        month = ledger_job_context(job=job, actor=cast(User, request.user))["month"]
        if isinstance(month, str):
            month = LedgerMonthField().clean(month[:7])
        # A malformed return page must not create a new collection before being rejected.
        _history_page(
            NativeLedgerCollection.objects.filter(
                organization=job.organization, financial_account=job.financial_account,
                scope__period_start=month.isoformat(),
            ).order_by("-created_at", "-id"),
            str(pages["page"]), "solicitações",
        )
        _history_page(
            ReconciliationSourceFile.objects.filter(
                organization=job.organization, company=job.financial_account.company,
                financial_account=job.financial_account, origin="bank_statement",
            ).order_by("-created_at", "-id"),
            str(pages["sources_page"]), "extratos",
        )
        retry_ledger_request(
            job=job,
            actor=cast(User, request.user),
            request_key=key,
            expected_mapping_revision=request.POST.get("expected_mapping_revision", ""),
            request=request,
        )
    except LedgerHistoryPageError as exc:
        return private_response(
            HttpResponse(str(exc), status=400, content_type="text/plain; charset=utf-8")
        )
    except (ValueError, TypeError) as exc:
        return private_response(
            HttpResponse(str(exc), status=409, content_type="text/plain; charset=utf-8")
        )
    messages.success(request, "Solicitação retomada. A nova tentativa aparece na primeira página.")
    return redirect(_url(job.financial_account, month, source, **pages) + "#ledger-requests")
