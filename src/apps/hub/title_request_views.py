"""Customer requests and retained company sources, independent of bank registration."""

from __future__ import annotations

from datetime import date
from typing import Any, cast
from urllib.parse import urlencode
from uuid import UUID, uuid4

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, Paginator
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.hub.models import FinancialAccount, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.title_request_forms import TitleMonthField, TitleRequestForm
from apps.hub.title_ui import has_duplicate_fields, private_response
from apps.hub.views import _can_manage_reconciliation, _module_page_context, office_required
from apps.intelligence.models import CompanyTitleCollection, NativeTitleCollection
from apps.organizations.models import Organization


def _workspace(request: HttpRequest, *, write: bool = False) -> dict[str, Any]:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        raise Http404
    writable = bool(
        context["support_can_mutate"]
        and _can_manage_reconciliation(context)
        and not cast(Organization, context["office"]).is_demo
    )
    if write and not writable:
        raise PermissionDenied("Seu acesso atual não permite solicitar títulos e baixas.")
    context.update(
        page_title="Buscar títulos e baixas",
        collection_can_write=writable,
        collection_errors=[],
        collection_back_url=reverse("hub:reconciliation-titles"),
        collection_url=reverse("hub:reconciliation-title-requests"),
    )
    return context


def _querysets(context: dict[str, Any]) -> tuple[Any, Any]:
    return (
        CompanyTitleCollection.objects.select_related("company", "agent", "source_file").filter(
            organization=context["office"],
            company__in=context["companies"],
            company__organization=context["office"],
        ),
        NativeTitleCollection.objects.select_related(
            "financial_account__company", "agent", "source_file"
        ).filter(
            organization=context["office"],
            financial_account__company__in=context["companies"],
            financial_account__organization=context["office"],
            financial_account__company__organization=context["office"],
        ),
    )


def _job(context: dict[str, Any], identifier: UUID) -> Any:
    current, legacy = _querysets(context)
    found = list(current.filter(pk=identifier)) + list(legacy.filter(pk=identifier))
    if len(found) != 1:
        raise Http404
    return found[0]


def _month_text(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def _row(data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    job, month, status = data["job"], data["month"], data["status"]
    return {
        **data,
        "month_label": f"{month.month:02d}/{month.year:04d}",
        "poll": status in {"queued", "delivered"},
        "status_class": "is-active"
        if status in {"captured", "empty"}
        else ("is-warning" if status in {"review", "failed"} else "is-muted"),
        "source_url": reverse("hub:reconciliation-title-source", args=[job.pk])
        if data["source_available"]
        else "",
        "can_retry": bool(data["can_retry"] and context["collection_can_write"]),
        "retry_url": reverse("hub:reconciliation-title-request-retry", args=[job.pk]),
        "retry_key": str(uuid4()),
        "connection_detail": " · ".join(
            (data["agent_state"]["label"], data["agent_state"]["detail"])
        )
        if status in {"queued", "delivered"}
        else "",
    }


def _initial(context: dict[str, Any], request: HttpRequest) -> TitleRequestForm:
    month = _month_text(timezone.localdate())
    return TitleRequestForm(
        companies=context["companies"],
        initial={
            "companies": [request.GET["company"]] if request.GET.get("company") else [],
            "start_month": request.GET.get("month", month),
            "end_month": request.GET.get("month", month),
            "request_key": uuid4(),
        },
    )


def _history(request: HttpRequest, context: dict[str, Any]) -> None:
    from apps.hub.title_requests import title_job_context

    if has_duplicate_fields(request.GET, ("company", "month", "page", "batch")):
        raise ValueError("Informe cada filtro uma única vez.")
    current, legacy = _querysets(context)
    company = None
    if request.GET.get("company"):
        try:
            identifier = UUID(request.GET["company"])
        except (ValueError, TypeError, AttributeError):
            raise Http404 from None
        company = get_object_or_404(context["companies"], pk=identifier)
        current = current.filter(company=company)
        legacy = legacy.filter(financial_account__company=company)
    month = request.GET.get("month", "")
    if month:
        from django.core.exceptions import ValidationError

        try:
            month = _month_text(TitleMonthField().clean(month))
        except ValidationError as exc:
            raise ValueError(" ".join(exc.messages)) from None
        current = current.filter(scope__period_start=month + "-01")
        legacy = legacy.filter(scope__period_start=month + "-01")
    batch = request.GET.get("batch", "")
    if batch:
        try:
            identifier = UUID(batch)
        except (ValueError, TypeError, AttributeError):
            raise ValueError("O lote informado é inválido.") from None
        current = current.filter(batch_key=identifier)
        legacy = legacy.none()
    page_value = request.GET.get("page", "1")
    if not page_value.isascii() or not page_value.isdigit() or not 1 <= len(page_value) <= 8:
        raise ValueError("Escolha uma página válida.")
    # The union is paginated in SQL; a large portfolio is not silently truncated.
    identifiers = (
        current.order_by()
        .values("pk", "created_at")
        .union(legacy.order_by().values("pk", "created_at"))
        .order_by("-created_at", "-pk")
    )
    try:
        page = Paginator(identifiers, 25).page(int(page_value))
    except EmptyPage:
        raise ValueError("Esta página não existe. Volte à primeira página das buscas.") from None
    ids = [item["pk"] for item in page.object_list]
    found = list(current.filter(pk__in=ids)) + list(legacy.filter(pk__in=ids))
    jobs = {job.pk: job for job in found}
    if len(jobs) != len(ids) or len(found) != len(jobs):
        raise ValueError(
            "O histórico contém uma referência ambígua. Solicite a revisão desta busca."
        )
    context.update(
        collection_jobs=[
            _row(title_job_context(job=jobs[item], actor=cast(User, request.user)), context)
            for item in ids
        ],
        collection_page=page,
        collection_company=company,
        collection_month=month,
        collection_batch=batch,
        collection_query=urlencode(
            {
                key: value
                for key, value in {
                    "company": str(company.pk) if company else "",
                    "month": month,
                    "batch": batch,
                }.items()
                if value
            }
        ),
    )


def _render(request: HttpRequest, context: dict[str, Any], status: int = 200) -> HttpResponse:
    try:
        _history(request, context)
    except ValueError as exc:
        context["collection_errors"].append(str(exc))
        status = 400
    return private_response(
        render(request, "hub/reconciliation_title_requests.html", context, status=status)
    )


@office_required
@require_http_methods(["GET", "POST"])
def title_requests(request: HttpRequest) -> HttpResponse:
    from apps.hub.title_requests import preview_title_requests, request_title_batch

    context = _workspace(request, write=request.method == "POST")
    form = (
        TitleRequestForm(request.POST, companies=context["companies"])
        if request.method == "POST"
        else _initial(context, request)
    )
    context["collection_form"] = form
    if request.method == "GET":
        return _render(request, context)
    if not form.is_valid():
        return _render(request, context, 400)
    action = request.POST.get("action", "")
    if action not in {"preview", "request"}:
        form.add_error(None, "Confira o lote antes de solicitar a busca.")
        return _render(request, context, 400)
    params = {
        "companies": list(form.cleaned_data["companies"]),
        "actor": cast(User, request.user),
        "start_month": form.cleaned_data["start_month"],
        "end_month": form.cleaned_data["end_month"],
        "request_key": form.cleaned_data["request_key"],
    }
    try:
        if action == "request":
            _jobs, created = request_title_batch(
                **params, expected_revision=form.cleaned_data["expected_revision"], request=request
            )
            messages.success(
                request,
                "Busca de títulos e baixas solicitada."
                if created
                else "Este lote já está registrado.",
            )
            return redirect(
                context["collection_url"]
                + "?"
                + urlencode({"batch": str(params["request_key"])})
                + "#title-requests"
            )
        preview = preview_title_requests(**params)
    except ValueError as exc:
        form.add_error(None, str(exc))
        return _render(request, context, 409)
    context.update(
        collection_preview=preview,
        collection_selected=params["companies"],
        collection_start=_month_text(params["start_month"]),
        collection_end=_month_text(params["end_month"]),
        collection_start_label=f"{params['start_month'].month:02d}/{params['start_month'].year:04d}",
        collection_end_label=f"{params['end_month'].month:02d}/{params['end_month'].year:04d}",
        collection_month_count=(params["end_month"].year - params["start_month"].year) * 12
        + params["end_month"].month
        - params["start_month"].month
        + 1,
    )
    return _render(request, context)


@office_required
@require_http_methods(["GET"])
def title_request_status(request: HttpRequest) -> HttpResponse:
    from apps.hub.title_requests import title_job_context

    context = _workspace(request)
    ids = request.GET.getlist("job")
    if not 1 <= len(ids) <= 25 or len(ids) != len(set(ids)):
        return private_response(
            JsonResponse({"detail": "Consulte de uma a 25 buscas distintas."}, status=400)
        )
    try:
        identifiers = [UUID(value) for value in ids]
    except (ValueError, TypeError, AttributeError):
        return private_response(
            JsonResponse({"detail": "A busca informada é inválida."}, status=400)
        )
    rows = []
    for identifier in identifiers:
        job = _job(context, identifier)
        try:
            row = _row(title_job_context(job=job, actor=cast(User, request.user)), context)
        except ValueError:
            return private_response(
                JsonResponse(
                    {"detail": "Reabra as buscas para conferir seu acesso e a fonte."}, status=409
                )
            )
        rows.append(
            {
                "id": str(job.pk),
                **{
                    key: row[key]
                    for key in (
                        "status",
                        "label",
                        "detail",
                        "poll",
                        "source_url",
                        "can_retry",
                        "retry_url",
                        "retry_key",
                        "connection_detail",
                    )
                },
            }
        )
    return private_response(JsonResponse({"jobs": rows}))


@office_required
@require_http_methods(["POST"])
def title_request_retry(request: HttpRequest, job_id: UUID) -> HttpResponse:
    from apps.hub.title_requests import retry_title_request

    context = _workspace(request, write=True)
    job = _job(context, job_id)
    try:
        if has_duplicate_fields(request.POST, ("request_key",)):
            raise ValueError("Informe uma única retomada.")
        key = UUID(request.POST.get("request_key", ""))
        new_job, created = retry_title_request(
            job=job, actor=cast(User, request.user), request_key=key, request=request
        )
    except (ValueError, TypeError, AttributeError) as exc:
        context["collection_form"] = _initial(context, request)
        context["collection_errors"] = [
            str(exc)
            if isinstance(exc, ValueError) and str(exc)
            else "Reabra a busca antes de tentar novamente."
        ]
        return _render(request, context, 409)
    messages.success(
        request,
        "Nova tentativa registrada; a busca anterior foi preservada."
        if created
        else "Esta retomada já está registrada.",
    )
    return redirect(
        context["collection_url"]
        + "?"
        + urlencode({"batch": str(new_job.batch_key)})
        + "#title-requests"
    )


def _source_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    from apps.intelligence.native_title_comparison import _key
    from apps.intelligence.native_title_contract import canonical_hash, manifest

    spec = manifest()["families"]
    labels = {"entradas": "Entradas", "saidas": "Saídas", "servicos": "Serviços"}
    rows = []
    for family in raw["families"]:
        family_spec = spec[family["name"]]
        payments: dict[Any, list[Any]] = {}
        for payment in family["payments"]:
            payments.setdefault(_key(payment, family_spec, "installments"), []).append(
                list(payment.items())
            )
        for part in family["installments"]:
            identity = _key(part, family_spec, "installments")
            rows.append(
                {
                    "family_label": labels[family["name"]],
                    "note": part[family_spec["note_field"]],
                    "number": part[family_spec["installment_field"]],
                    "due_on": date.fromisoformat(part[family_spec["due_field"]])
                    if part[family_spec["due_field"]]
                    else None,
                    "reference": canonical_hash([family["name"], "installments", identity]),
                    "fields": list(part.items()),
                    "payments": payments.get(identity, []),
                }
            )
    return rows


@office_required
@require_http_methods(["GET"])
def title_source(request: HttpRequest, job_id: UUID) -> HttpResponse:
    from apps.hub.title_requests import title_job_company
    from apps.intelligence.native_title_review import load_company_title_source

    context = _workspace(request)
    job = _job(context, job_id)
    company = title_job_company(job)
    if has_duplicate_fields(request.GET, ("account", "page")):
        raise Http404
    accounts = FinancialAccount.objects.filter(
        organization=context["office"], company=company, active=True
    ).order_by("name", "pk")
    account = None
    if request.GET.get("account"):
        try:
            identifier = UUID(request.GET["account"])
        except (ValueError, TypeError, AttributeError):
            raise Http404 from None
        account = get_object_or_404(accounts, pk=identifier)
    context.update(
        page_title="Fonte de títulos e baixas",
        collection_job=job,
        collection_source_company=company,
        collection_accounts=accounts,
        collection_account=account,
        collection_source_month=(
            f"{job.scope['period_start'][5:7]}/{job.scope['period_start'][:4]}"
            if isinstance(job.scope, dict) and isinstance(job.scope.get("period_start"), str)
            else "Não informado"
        ),
    )
    status = 200
    try:
        _capture, _evidence, raw = load_company_title_source(
            job_id=job.pk, organization_id=context["office"].pk, actor=cast(User, request.user)
        )
        page_text = request.GET.get("page", "1")
        if not page_text.isascii() or not page_text.isdigit() or not 1 <= len(page_text) <= 8:
            raise ValueError("Escolha uma página válida.")
        page = Paginator(_source_rows(raw), 25).page(int(page_text))
        if account and context["collection_can_write"]:
            for item in page.object_list:
                item["url"] = reverse(
                    "hub:reconciliation-native-title-review",
                    args=[account.pk, job.pk, item["reference"]],
                )
        context.update(
            collection_source_available=True,
            collection_source_page=page,
            collection_source_scope=job.scope,
            collection_source_counts=[
                {
                    "label": {"entradas": "Entradas", "saidas": "Saídas", "servicos": "Serviços"}[
                        family["name"]
                    ],
                    "installments": len(family["installments"]),
                    "payments": len(family["payments"]),
                }
                for family in raw["families"]
            ],
        )
    except EmptyPage:
        context["collection_errors"] = ["Esta página não existe. Volte à primeira página da fonte."]
        status = 400
    except ValueError as exc:
        context["collection_errors"] = [str(exc)]
        status = 409
    return private_response(
        render(request, "hub/reconciliation_title_source.html", context, status=status)
    )
