"""Customer title review, allocations and evidence; no CLI, ERP writes or inferred matches."""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any, cast
from urllib.parse import urlencode
from uuid import UUID, uuid4

from django.contrib import messages
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import (
    FinancialAccount,
    ReconciliationTitleAllocation,
    ReconciliationTitleSnapshot,
)
from apps.hub.title_contract import TitleContractError
from apps.hub.title_forms import (
    MAX_ALLOCATION_ROWS,
    AllocationFormSet,
    TitleConfirmForm,
    TitlePeriodForm,
    TitleUndoForm,
)
from apps.hub.title_labels import enrich_title_labels
from apps.hub.title_persistence import (
    confirm_title_allocations,
    latest_title_snapshot,
    prepare_title_allocations,
    undo_title_allocation,
)
from apps.hub.title_read_model import build_title_workspace
from apps.hub.title_ui import brl, has_duplicate_fields, private_response, title_workspace
from apps.hub.views import office_required

PREVIEW_SALT = "hub.title-allocation-preview.v1"
PREVIEW_MAX_AGE = 30 * 60
MAX_SELECT_OPTIONS = 200
FILTERS = (
    "account",
    "company",
    "start",
    "end",
    "q",
    "page",
    "bank_q",
    "title_q",
    "direction",
    "format",
    "history_page",
)


def _url(name: str, account: FinancialAccount, start: date, end: date, **extra: str) -> str:
    query = {"start": start.isoformat(), "end": end.isoformat(), **extra}
    if name == "reconciliation-titles":
        query["account"] = str(account.pk)
        path = reverse("hub:" + name)
    else:
        path = reverse("hub:" + name, kwargs={"account_id": account.pk})
    return path + "?" + urlencode(query)


def _error(
    context: dict[str, Any], request: HttpRequest, message: str, *, status: int = 400
) -> HttpResponse:
    context["titles_errors"] = [message]
    context.setdefault("title_data", None)
    return private_response(
        render(request, "hub/reconciliation_titles.html", context, status=status)
    )


def _period(request: HttpRequest, account: FinancialAccount) -> TitlePeriodForm:
    # Explicit boundaries must both validate; never expand an invalid or partial interval.
    if "start" in request.GET or "end" in request.GET:
        return TitlePeriodForm(request.GET)
    latest = latest_title_snapshot(account)
    end = latest.as_of if latest else timezone.localdate()
    initial = {"start": end.replace(day=1).isoformat(), "end": end.isoformat()}
    return TitlePeriodForm(initial)


def _load_page(
    request: HttpRequest,
    context: dict[str, Any],
    account: FinancialAccount,
    *,
    period: TitlePeriodForm | None = None,
) -> dict[str, Any] | None:
    try:
        period = period if period is not None else _period(request, account)
    except TitleContractError:
        context["titles_errors"] = ["A fotografia desta conta exige revisão do vínculo."]
        return None
    context["titles_period_form"] = period
    if not period.is_valid():
        context["titles_errors"] = ["Confira as duas datas do período antes de consultar."]
        return None
    start, end = period.cleaned_data["start"], period.cleaned_data["end"]
    try:
        data = build_title_workspace(
            account=account, actor=cast(User, request.user), start=start, end=end
        )
    except ValueError:
        raise PermissionDenied(
            "Seu acesso atual não permite consultar títulos desta conta."
        ) from None
    enrich_title_labels(data=data, account=account, actor=cast(User, request.user))
    context.update(
        title_data=data,
        titles_start=start,
        titles_end=end,
        titles_catalog_url=_url("reconciliation-titles", account, start, end),
        titles_plan_url=_url("reconciliation-title-plan", account, start, end),
        titles_sources_url=_url("reconciliation-native-titles", account, start, end),
        titles_report_url=_url("reconciliation-title-report", account, start, end),
        titles_csv_url=_url("reconciliation-title-report", account, start, end, format="csv"),
    )
    return data


def _history_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {
        (r["title_key"], r["installment_key"], r["settlement_key"]): r
        for r in data["settlement_rows"]
    }
    rows = []
    for allocation in data["allocations"]:
        label = labels.get(
            (allocation.title_key, allocation.installment_key, allocation.settlement_key), {}
        )
        rows.append(
            {
                "allocation": allocation,
                "amount": "R$ " + brl(allocation.cash_cents),
                "title_label": label.get("title_label", allocation.title_key[:16]),
                "installment_label": label.get(
                    "installment_label", allocation.installment_key[:16]
                ),
                "settlement_label": label.get("settlement_label", allocation.settlement_key[:16]),
                "undo_form": TitleUndoForm(prefix="undo-" + str(allocation.pk)),
            }
        )
    return rows


def _page(rows: Any, raw: str) -> Any:
    if not raw.isascii() or not raw.isdigit() or not 1 <= len(raw) <= 8:
        raise ValueError
    return Paginator(rows, 25).page(int(raw))


@office_required
@require_http_methods(["GET"])
def titles(request: HttpRequest) -> HttpResponse:
    context, account = title_workspace(request)
    if has_duplicate_fields(request.GET, FILTERS):
        return _error(context, request, "Informe cada filtro uma única vez.")
    context["titles_errors"] = []
    if account is None:
        return private_response(render(request, "hub/reconciliation_titles.html", context))
    data = _load_page(request, context, account)
    if data is None:
        return private_response(
            render(request, "hub/reconciliation_titles.html", context, status=400)
        )
    query = request.GET.get("q", "").strip()
    if len(query) > 100:
        return _error(context, request, "Use até 100 caracteres na busca.")
    rows = data["installment_rows"]
    if query:
        rows = [row for row in rows if query.casefold() in row["label"].casefold()]
    try:
        page = _page(rows, request.GET.get("page", "1"))
        history_page = _page(_history_rows(data), request.GET.get("history_page", "1"))
    except (ValueError, EmptyPage):
        return _error(context, request, "Esta página não está disponível. Volte à primeira página.")
    visible_allocations = {r["allocation"].pk for r in history_page}
    context.update(
        titles_page=page,
        titles_query=query,
        titles_page_query=urlencode(
            {
                "account": str(account.pk),
                "start": context["titles_start"].isoformat(),
                "end": context["titles_end"].isoformat(),
                "q": query,
            }
        ),
        titles_history_rows=history_page,
        titles_history_page=history_page,
        titles_decisions=[d for d in data["decisions"] if d.allocation_id in visible_allocations],
    )
    return private_response(render(request, "hub/reconciliation_titles.html", context))


def _selections(
    request: HttpRequest, data: dict[str, Any]
) -> tuple[list[Any], list[Any], list[str]]:
    bank_query = request.GET.get("bank_q", "").strip().casefold()
    title_query = request.GET.get("title_q", "").strip().casefold()
    direction = request.GET.get("direction", "")
    if max(len(bank_query), len(title_query)) > 100 or direction not in {"", "inflow", "outflow"}:
        return [], [], ["Confira a busca e a direção dos registros."]
    movements = [
        row
        for row in data["movement_rows"]
        if row["available"]
        and (not bank_query or bank_query in row["label"].casefold())
        and (not direction or row["direction"] == direction)
    ]
    settlements = [
        row
        for row in data["settlement_rows"]
        if row["available"]
        and (not title_query or title_query in row["label"].casefold())
        and (not direction or row["direction"] == direction)
    ]
    if len(movements) > MAX_SELECT_OPTIONS or len(settlements) > MAX_SELECT_OPTIONS:
        return (
            [],
            [],
            ["Reduza o período ou refine a busca para selecionar até 200 registros de cada lado."],
        )
    return movements, settlements, []


def _preview_context(
    context: dict[str, Any],
    data: dict[str, Any],
    plan: Any,
    requests: list[dict[str, Any]],
    token: str,
) -> None:
    movements = {row["key"]: row for row in data["movement_rows"]}
    settlements = {
        (row["title_key"], row["installment_key"], row["settlement_key"]): row
        for row in data["settlement_rows"]
    }
    selected = []
    for row in plan.preview.allocations:
        selected.append(
            {
                "movement": movements[row.movement_key],
                "settlement": settlements[
                    (
                        row.reference.title_key,
                        row.reference.installment_key,
                        row.reference.settlement_key,
                    )
                ],
                "amount": "R$ " + brl(row.cash_cents),
                "date_difference": row.date_difference,
            }
        )
    context.update(
        titles_preview_rows=selected,
        titles_preview_movements=[
            {
                "date": row.movement.occurred_on,
                "label": movements[row.movement.key]["label"],
                "allocated": "R$ " + brl(row.allocated_cents),
                "remaining": "R$ " + brl(row.remaining_cents),
            }
            for row in plan.preview.movements
        ],
        titles_preview_fingerprint=plan.fingerprint,
        titles_confirm_form=TitleConfirmForm(
            initial={"token": token},
            date_differences=any(row.date_difference for row in plan.preview.allocations),
        ),
        titles_preview_count=len(requests),
    )


@office_required
@require_http_methods(["GET", "POST"])
def title_plan(request: HttpRequest, account_id: UUID) -> HttpResponse:
    context, account = title_workspace(request, account_id, write=True)
    assert account is not None
    if has_duplicate_fields(request.GET, FILTERS) or has_duplicate_fields(
        request.POST, request.POST
    ):
        return _error(context, request, "Informe cada campo uma única vez.")
    data = _load_page(request, context, account)
    if data is None:
        return private_response(
            render(request, "hub/reconciliation_titles.html", context, status=400)
        )
    if data["blocking"] or data["snapshot"] is None:
        context["titles_history_rows"] = _history_rows(data)
        return _error(
            context,
            request,
            "Confira as fontes e os vínculos anteriores antes de preparar uma alocação.",
            status=409,
        )
    movements, settlements, errors = _selections(request, data)
    context.update(
        titles_errors=errors,
        titles_bank_query=request.GET.get("bank_q", ""),
        titles_title_query=request.GET.get("title_q", ""),
        titles_direction=request.GET.get("direction", ""),
    )
    posted = request.POST.copy() if request.method == "POST" else None
    action = request.POST.get("action", "") if posted is not None else ""
    if action == "add" and posted is not None:
        try:
            count = int(posted.get("links-TOTAL_FORMS", ""))
            if not 1 <= count < MAX_ALLOCATION_ROWS:
                raise ValueError
            posted["links-TOTAL_FORMS"] = str(count + 1)
        except ValueError:
            errors.append("Use de 1 a 20 vínculos por revisão.")
    elif posted is not None and action != "preview":
        errors.append("Escolha uma ação válida para esta revisão.")
    formset = AllocationFormSet(
        posted,
        prefix="links",
        form_kwargs={
            "movements": movements,
            "settlements": settlements,
        },
    )
    context.update(
        titles_formset=formset,
        titles_can_add=len(formset.forms) < MAX_ALLOCATION_ROWS,
        titles_movement_options=movements,
        titles_settlement_options=settlements,
    )
    status = 400 if errors else 200
    if posted is not None and action == "preview" and not errors:
        if formset.is_valid():
            requests = [form.allocation_request() for form in formset if form.cleaned_data]
            try:
                plan = prepare_title_allocations(
                    snapshot=data["snapshot"],
                    requests=requests,
                    actor=cast(User, request.user),
                    period_start=context["titles_start"],
                    period_end=context["titles_end"],
                )
                token = signing.dumps(
                    {
                        "version": 1,
                        "actor": str(request.user.pk),
                        "organization": str(account.organization_id),
                        "account": str(account.pk),
                        "snapshot": str(data["snapshot"].pk),
                        "start": context["titles_start"].isoformat(),
                        "end": context["titles_end"].isoformat(),
                        "requests": requests,
                        "fingerprint": plan.fingerprint,
                        "request_id": str(uuid4()),
                        "date_differences": any(
                            r.date_difference for r in plan.preview.allocations
                        ),
                    },
                    salt=PREVIEW_SALT,
                    compress=True,
                )
                _preview_context(context, data, plan, requests, token)
                return private_response(
                    render(request, "hub/reconciliation_titles_preview.html", context)
                )
            except TitleContractError as error:
                errors.append(str(error))
        status = 400
    return private_response(
        render(request, "hub/reconciliation_titles_plan.html", context, status=status)
    )


def _unpack(token: str, request: HttpRequest, account: FinancialAccount) -> dict[str, Any]:
    try:
        payload = signing.loads(token, salt=PREVIEW_SALT, max_age=PREVIEW_MAX_AGE)
        if (
            not isinstance(payload, dict)
            or set(payload)
            != {
                "version",
                "actor",
                "organization",
                "account",
                "snapshot",
                "start",
                "end",
                "requests",
                "fingerprint",
                "request_id",
                "date_differences",
            }
            or payload["version"] != 1
            or (payload["actor"], payload["organization"], payload["account"])
            != (str(request.user.pk), str(account.organization_id), str(account.pk))
        ):
            raise ValueError
        period = TitlePeriodForm({"start": payload["start"], "end": payload["end"]})
        if (
            not period.is_valid()
            or not isinstance(payload["requests"], list)
            or not 1 <= len(payload["requests"]) <= MAX_ALLOCATION_ROWS
        ):
            raise ValueError
        payload["start"], payload["end"] = period.cleaned_data["start"], period.cleaned_data["end"]
        if type(payload["date_differences"]) is not bool:
            raise ValueError
        payload["request_id"] = UUID(payload["request_id"])
        payload["snapshot"] = UUID(payload["snapshot"])
        return payload
    except (signing.BadSignature, ValueError, TypeError, KeyError):
        raise TitleContractError(
            "A prévia expirou ou foi alterada. Prepare uma nova revisão."
        ) from None


@office_required
@require_http_methods(["POST"])
def title_confirm(request: HttpRequest, account_id: UUID) -> HttpResponse:
    context, account = title_workspace(request, account_id, write=True)
    assert account is not None
    if has_duplicate_fields(request.POST, request.POST):
        return _error(context, request, "Informe cada campo uma única vez.")
    token = request.POST.get("token", "")
    if not token or len(token) > 32000:
        return _error(context, request, "Prepare uma prévia válida antes de confirmar.")
    try:
        payload = _unpack(token, request, account)
        snapshot = get_object_or_404(
            ReconciliationTitleSnapshot,
            pk=payload["snapshot"],
            organization_id=account.organization_id,
            company_id=account.company_id,
            financial_account=account,
        )
        form = TitleConfirmForm(request.POST, date_differences=payload["date_differences"])
        if not form.is_valid():
            data = _load_page(
                request,
                context,
                account,
                period=TitlePeriodForm(
                    {
                        "start": payload["start"].isoformat(),
                        "end": payload["end"].isoformat(),
                    }
                ),
            )
            if data is None or data["blocking"]:
                raise TitleContractError("As fontes mudaram. Prepare uma nova revisão.")
            plan = prepare_title_allocations(
                snapshot=snapshot,
                requests=payload["requests"],
                actor=cast(User, request.user),
                period_start=payload["start"],
                period_end=payload["end"],
            )
            if plan.fingerprint != payload["fingerprint"]:
                raise TitleContractError(
                    "Os valores disponíveis mudaram. Prepare uma nova revisão."
                )
            _preview_context(context, data, plan, payload["requests"], token)
            context["titles_confirm_form"] = form
            return private_response(
                render(request, "hub/reconciliation_titles_preview.html", context, status=400)
            )
        _batch, created = confirm_title_allocations(
            snapshot=snapshot,
            requests=payload["requests"],
            actor=cast(User, request.user),
            period_start=payload["start"],
            period_end=payload["end"],
            request_id=payload["request_id"],
            preview_fingerprint=payload["fingerprint"],
            evidence_reference=form.cleaned_data["evidence_reference"],
            accept_date_differences=form.cleaned_data["accept_date_differences"],
        )
    except TitleContractError as error:
        return _error(context, request, str(error), status=409)
    messages.success(
        request, "Vínculos confirmados." if created else "Esta confirmação já estava registrada."
    )
    return redirect(
        _url("reconciliation-titles", account, payload["start"], payload["end"]) + "#titles-history"
    )


@office_required
@require_http_methods(["POST"])
def title_undo(request: HttpRequest, account_id: UUID, allocation_id: UUID) -> HttpResponse:
    context, account = title_workspace(request, account_id, write=True)
    assert account is not None
    if has_duplicate_fields(request.POST, request.POST) or has_duplicate_fields(
        request.GET, FILTERS
    ):
        return _error(context, request, "Informe cada campo uma única vez.")
    allocation = get_object_or_404(
        ReconciliationTitleAllocation,
        pk=allocation_id,
        organization_id=account.organization_id,
        financial_account=account,
        movement__organization_id=account.organization_id,
        movement__company_id=account.company_id,
        movement__financial_account=account,
        batch__organization_id=account.organization_id,
        batch__financial_account=account,
    )
    period = TitlePeriodForm(request.POST)
    if not period.is_valid():
        return _error(context, request, "Confira as duas datas do período antes de desfazer.")
    form = TitleUndoForm(request.POST, prefix="undo-" + str(allocation.pk))
    if not form.is_valid():
        return _error(context, request, "Informe o motivo para desfazer este vínculo.")
    try:
        changed = undo_title_allocation(
            allocation=allocation,
            actor=cast(User, request.user),
            reason=form.cleaned_data["reason"],
        )
    except TitleContractError as error:
        return _error(context, request, str(error), status=409)
    messages.success(
        request,
        "Vínculo desfeito; o histórico foi preservado."
        if changed
        else "Este vínculo já estava desfeito.",
    )
    return redirect(
        _url(
            "reconciliation-titles",
            account,
            period.cleaned_data["start"],
            period.cleaned_data["end"],
        )
        + "#titles-history"
    )


def _csv_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return (
        "'" + text
        if text.startswith(("\t", "\r", "\n")) or text.lstrip().startswith(("=", "+", "-", "@"))
        else text
    )


@office_required
@require_http_methods(["GET"])
def title_report(request: HttpRequest, account_id: UUID) -> HttpResponse:
    context, account = title_workspace(request, account_id)
    assert account is not None
    if has_duplicate_fields(request.GET, FILTERS):
        return _error(context, request, "Informe cada filtro uma única vez.")
    if request.GET.get("format", "print") not in {"print", "csv"}:
        return _error(context, request, "Escolha relatório para impressão ou CSV.")
    data = _load_page(request, context, account)
    if data is None or data["blocking"] or data["snapshot"] is None:
        return _error(
            context,
            request,
            "Confira o período e a integridade das fontes antes de emitir o relatório.",
            status=409,
        )
    current_review = (
        AuditEvent.objects.filter(
            organization_id=account.organization_id,
            action="hub.reconciliation.native_title_ui_reviewed",
            target_type="hub.reconciliationtitlesnapshot",
            target_id=str(data["snapshot"].pk),
            success=True,
        )
        .select_related("actor")
        .order_by("-occurred_at", "-id")
        .first()
    )
    activation: dict[str, Any] | None = None
    if current_review and current_review.metadata.get("activated_existing") is True:
        activation = {
            "event_id": str(current_review.pk),
            "occurred_at": current_review.occurred_at,
            "actor": current_review.actor.display_name if current_review.actor else "Não informado",
            "evidence": current_review.metadata.get("evidence_reference") or "Não informado",
        }
    history = {row["allocation"].pk: row for row in _history_rows(data)}
    context.update(
        titles_current_review=activation,
        titles_generated_at=timezone.now(),
        titles_report_decisions=[
            {"decision": decision, **history[decision.allocation_id]}
            for decision in data["decisions"]
        ],
    )
    if request.GET.get("format") != "csv":
        return private_response(render(request, "hub/reconciliation_titles_report.html", context))
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(["Empresa", _csv_text(account.company.name), "Conta", _csv_text(account.name)])
    writer.writerow(
        ["Período", context["titles_start"].isoformat(), context["titles_end"].isoformat()]
    )
    writer.writerow(
        ["Fotografia", str(data["snapshot"].pk), "SHA-256", data["snapshot"].fingerprint]
    )
    writer.writerow(["Arquivo SHA-256", data["snapshot"].source_file.content_hash])
    writer.writerow(["Emitido em", context["titles_generated_at"].isoformat()])
    writer.writerow(
        [
            "Revisão original da fonte",
            _csv_text(data["snapshot"].evidence_reference),
            _csv_text(data["snapshot"].reviewed_by.display_name),
            data["snapshot"].created_at.isoformat(),
        ]
    )
    if activation:
        writer.writerow(
            [
                "Revisão que tornou a fotografia vigente",
                _csv_text(activation["evidence"]),
                _csv_text(activation["actor"]),
                activation["occurred_at"].isoformat(),
                "Evento",
                activation["event_id"],
            ]
        )
    writer.writerow(
        [
            "Escopo",
            "Baixas e movimentos do período; parcelas da fotografia; "
            "histórico completo de vínculos; sem escrita no ERP.",
        ]
    )
    for warning in data["warnings"]:
        writer.writerow(["Aviso", _csv_text(warning)])
    writer.writerow(
        [
            "Tipo",
            "Data",
            "Título",
            "Parcela",
            "Baixa",
            "Histórico ou referência",
            "Direção",
            "Valor R$",
            "Alocado R$",
            "Disponível R$",
            "Saldo informado R$",
            "Estado",
            "Autor",
            "Evidência",
            "Principal R$",
            "Juros R$",
            "Multa R$",
            "Tarifas R$",
            "Desconto R$",
        ]
    )
    for row in data["installment_rows"]:
        writer.writerow(
            [
                "Parcela",
                row["due_on"],
                _csv_text(row["title_key"]),
                _csv_text(row["installment_key"]),
                "",
                "",
                row["kind_label"],
                brl(row["principal_cents"]),
                "",
                "",
                brl(row["outstanding_cents"]),
                "",
                "",
                "",
                brl(row["principal_cents"]),
                "",
                "",
                "",
                "",
            ]
        )
    for row in data["settlement_rows"]:
        writer.writerow(
            [
                "Baixa",
                row["posted_on"],
                _csv_text(row["title_key"]),
                _csv_text(row["installment_key"]),
                _csv_text(row["settlement_key"]),
                "",
                row["direction_label"],
                brl(row["cash_cents"]),
                brl(row["allocated_cents"]),
                brl(row["remaining_cents"]),
                "",
                "Estorno" if row["is_reversal"] else "Baixa",
                "",
                "",
            ]
            + [
                brl(row[key + "_cents"])
                for key in ("principal", "interest", "penalty", "fees", "discount")
            ]
        )
    for row in data["movement_rows"]:
        writer.writerow(
            [
                "Extrato",
                row["occurred_on"],
                "",
                "",
                "",
                _csv_text(row["description"]),
                row["direction_label"],
                brl(row["cash_cents"]),
                brl(row["allocated_cents"]),
                brl(row["remaining_cents"]),
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )
    for decision in data["decisions"]:
        allocation = decision.allocation
        writer.writerow(
            [
                "Decisão",
                decision.created_at.isoformat(),
                _csv_text(allocation.title_key),
                _csv_text(allocation.installment_key),
                _csv_text(allocation.settlement_key),
                str(allocation.movement_id),
                "",
                brl(allocation.cash_cents),
                "",
                "",
                "",
                decision.get_state_display(),
                _csv_text(decision.actor.display_name),
                _csv_text(decision.reason),
                "",
                "",
                "",
                "",
                "",
            ]
        )
    response = HttpResponse("\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="titulos-e-baixas.csv"'
    return private_response(response)
