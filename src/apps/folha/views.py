"""Telas da Folha: ciclos, conferência, envio ao cliente e configuração do escritório."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.models import User
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.views import office_required
from apps.rpa import ui
from apps.rpa.registry import RpaError

from . import recipients, services
from .models import (
    ITEM_LABELS,
    ITEMS,
    FolhaContact,
    FolhaCycle,
    FolhaEmail,
    FolhaReport,
    FolhaSheetMark,
    FolhaTask,
)

CODE = ProductModule.Code.FOLHA
MAX_CODES = 2000


def _gate(request: HttpRequest) -> tuple[dict[str, Any], HttpResponse | None]:
    context, blocked = ui.gate(request, CODE)
    return cast("dict[str, Any]", context), blocked


def _month(value: str) -> date | None:
    try:
        year, month = value.split("-")
        return date(int(year), int(month), 1)
    except (ValueError, AttributeError):
        return None


def _day(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _authorized_companies(context: dict[str, Any]) -> list[ClientCompany]:
    org = ui.office(context)
    codes = {str(c) for c in services.settings_for(org).authorized_codes}
    return list(ui.companies(context).filter(active=True, dominio_code__in=codes))


def _cycles(context: dict[str, Any]) -> Any:
    """Ciclos com ao menos uma empresa da carteira de quem pede (administrador vê todos)."""

    base = FolhaCycle.objects.filter(organization=ui.office(context))
    if context.get("can_admin"):
        return base
    mine = FolhaTask.objects.filter(
        organization=ui.office(context), company__in=ui.companies(context)
    )
    return base.filter(pk__in=mine.values("cycle_id"))


def _whole_cycle_mine(context: dict[str, Any], cycle: FolhaCycle) -> bool:
    """Ação sobre o ciclo inteiro só para quem enxerga todas as empresas dele."""

    if context.get("can_admin"):
        return True
    return not cycle.tasks.exclude(company__in=ui.companies(context)).exists()


@office_required
@require_GET
def index(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    cycles = list(_cycles(context).order_by("-competence", "-created_at")[:30])
    context.update(
        {
            "page_title": "Folha",
            "cycles": cycles,
            "companies_choices": _authorized_companies(context),
            "item_choices": [(i, ITEM_LABELS[i]) for i in ITEMS],
            "default_month": date.today().replace(day=1).strftime("%Y-%m"),
        }
    )
    return render(request, "folha/index.html", context)


@office_required
@require_POST
def cycle_new(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_write(request, context):
        return denied
    org = ui.office(context)
    competence = _month(request.POST.get("competencia", ""))
    allowed = {str(c.pk): c for c in _authorized_companies(context)}
    chosen = [allowed[v] for v in request.POST.getlist("empresas") if v in allowed]
    if competence is None:
        messages.error(request, "Competência inválida.")
        return redirect("folha:index")
    try:
        cycle = services.create_cycle(
            organization=org,
            user=cast(User, request.user),
            competence=competence,
            companies=chosen,
            items=request.POST.getlist("itens"),
            confirm_calc=request.POST.get("confirmo_calculo") == "sim",
        )
    except services.FolhaError as exc:
        messages.error(request, str(exc))
        return redirect("folha:index")
    except RpaError as exc:
        messages.error(request, exc.message)
        return redirect("folha:index")
    return redirect("folha:cycle", cycle_id=cycle.pk)


def _cycle(context: dict[str, Any], cycle_id: UUID) -> FolhaCycle:
    return cast(FolhaCycle, get_object_or_404(_cycles(context), pk=cycle_id))


@office_required
@require_GET
def cycle(request: HttpRequest, cycle_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    item = _cycle(context, cycle_id)
    mine = item.tasks.select_related("company")
    if not context.get("can_admin"):
        mine = mine.filter(company__in=ui.companies(context))
    tasks = list(mine.order_by("company__dominio_code", "item"))
    reports = {r.task_id: r for r in FolhaReport.objects.filter(task__cycle=item)}
    for task in tasks:
        task.label = ITEM_LABELS.get(task.item, task.item)  # type: ignore[attr-defined]
        task.report_row = reports.get(task.pk)  # type: ignore[attr-defined]
    by_company: dict[UUID, dict[str, Any]] = {}
    for task in tasks:
        row = by_company.setdefault(
            task.company_id, {"company": task.company, "tasks": [], "email": None}
        )
        row["tasks"].append(task)
    for email in item.emails.all():
        if email.company_id in by_company:
            by_company[email.company_id]["email"] = email
    context.update(
        {
            "page_title": f"Folha {item.competence:%m/%Y}",
            "cycle": item,
            "rows": list(by_company.values()),
            "labels": ITEM_LABELS,
        }
    )
    return render(request, "folha/cycle.html", context)


@office_required
@require_POST
def cycle_action(request: HttpRequest, cycle_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_write(request, context):
        return denied
    item = _cycle(context, cycle_id)
    action = request.POST.get("acao", "")
    user = cast(User, request.user)
    try:
        if action in {"confirmar", "cancelar"} and not _whole_cycle_mine(context, item):
            messages.error(request, "O ciclo tem empresas fora da sua carteira.")
        elif action == "confirmar":
            services.confirm_draft(
                item, user=user, confirm_calc=request.POST.get("confirmo_calculo") == "sim"
            )
        elif action == "cancelar":
            services.cancel_cycle(item, user=user)
        elif action == "reprocessar":
            task = get_object_or_404(
                FolhaTask,
                pk=request.POST.get("tarefa"),
                cycle=item,
                company__in=ui.companies(context),
            )
            services.reprocess(
                task, user=user, confirm_calc=request.POST.get("confirmo_calculo") == "sim"
            )
        elif action == "aprovar_relatorio":
            report = get_object_or_404(
                FolhaReport,
                pk=request.POST.get("relatorio"),
                task__cycle=item,
                task__company__in=ui.companies(context),
            )
            services.approve_report(report, user=user)
        else:
            messages.error(request, "Ação desconhecida.")
    except services.FolhaError as exc:
        messages.error(request, str(exc))
    return redirect("folha:cycle", cycle_id=item.pk)


@office_required
@require_http_methods(["GET", "POST"])
def send(request: HttpRequest, cycle_id: UUID, company_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    item = _cycle(context, cycle_id)
    company = get_object_or_404(ui.companies(context), pk=company_id)
    contacts = [
        recipients.Contact(tuple(c.emails), c.note)
        for c in FolhaContact.objects.filter(organization=item.organization, company=company)
    ]
    decision = recipients.decide(contacts)
    email = FolhaEmail.objects.filter(cycle=item, company=company).first()
    if request.method == "POST":
        if denied := ui.need_write(request, context):
            return denied
        user = cast(User, request.user)
        action = request.POST.get("acao", "")
        try:
            if action == "criar":
                chosen = recipients.resolve(
                    decision,
                    chosen=request.POST.getlist("destinatario"),
                    manual=request.POST.get("manual", "").strip(),
                )
                email = services.build_email(
                    cycle=item,
                    company=company,
                    recipients=chosen,
                    sender=str(settings.DEFAULT_FROM_EMAIL),
                    payment_date=_day(request.POST.get("pagamento", "")),
                    inss_due_date=_day(request.POST.get("inss", "")),
                )
            elif email is not None and action == "aprovar":
                services.approve_email(email, user=user)
            elif email is not None and action == "enviar":
                sent = services.send_email(email)
                if sent.state == FolhaEmail.State.FAILED:
                    messages.error(request, sent.error)
            elif email is not None and action == "reconciliar":
                if denied := ui.need_admin(request, context):
                    return denied
                services.reconcile_email(
                    email,
                    user=user,
                    sent=request.POST.get("enviado") == "sim",
                    message_id=request.POST.get("mensagem", ""),
                    note=request.POST.get("justificativa", ""),
                )
        except (services.FolhaError, recipients.RecipientError) as exc:
            messages.error(request, str(exc))
        return redirect("folha:send", cycle_id=item.pk, company_id=company.pk)
    context.update(
        {
            "page_title": f"Envio · {company.name}",
            "cycle": item,
            "company": company,
            "decision": decision,
            "email": email,
        }
    )
    return render(request, "folha/send.html", context)


@office_required
@require_http_methods(["GET", "POST"])
def config(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    org = ui.office(context)
    cfg = services.settings_for(org)
    if request.method == "POST":
        if denied := ui.need_admin(request, context):
            return denied
        codes = [
            c.strip() for c in request.POST.get("autorizadas", "").replace("\n", ",").split(",")
        ]
        cfg.authorized_codes = sorted({c for c in codes if c and c != "*"})[:MAX_CODES]
        cfg.schedule_enabled = request.POST.get("agenda") == "sim"
        try:
            day = int(request.POST.get("dia", cfg.schedule_day))
        except ValueError:
            day = cfg.schedule_day
        cfg.schedule_day = min(max(day, 1), 28)
        cfg.schedule_items = [i for i in request.POST.getlist("itens") if i in ITEMS]
        sched = [
            c.strip() for c in request.POST.get("agenda_empresas", "").replace("\n", ",").split(",")
        ]
        cfg.schedule_codes = sorted({c for c in sched if c})[:MAX_CODES]
        cfg.sheets_enabled = request.POST.get("planilha") == "sim"
        cfg.sheets_spreadsheet_id = request.POST.get("planilha_id", "").strip()[:120]
        cfg.sheets_tab_template = request.POST.get("planilha_aba", "").strip()[:60]
        cfg.save()
        messages.success(request, "Guardado.")
        return redirect("folha:config")
    marks = FolhaSheetMark.objects.filter(organization=org).order_by("-updated_at")[:15]
    context.update(
        {
            "page_title": "Folha · Configuração",
            "cfg": cfg,
            "authorized_text": ", ".join(str(c) for c in cfg.authorized_codes),
            "schedule_text": ", ".join(str(c) for c in cfg.schedule_codes),
            "item_choices": [(i, ITEM_LABELS[i]) for i in ITEMS],
            "marks": marks,
        }
    )
    return render(request, "folha/config.html", context)
