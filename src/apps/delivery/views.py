"""Telas do Envio ao cliente.

Mesmo idioma dos módulos irmãos: `office_required` na porta, `_module_page_context` no portão
do módulo e do colaborador, `hub/workspace.html` como esqueleto. Ler exige o módulo ligado e
a empresa na carteira de quem pede; escrever exige papel operacional; a conta de envio só o
dono e o administrador mexem.
"""

from __future__ import annotations

from typing import cast
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.audit.services import record_event
from apps.delivery import services
from apps.delivery.forms import AccountForm, ComposeForm
from apps.delivery.models import Delivery, DeliveryAccount
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import _module_page_context, office_required, refuse
from apps.organizations.models import Membership, Organization

WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
    Membership.Role.OPERATOR,
}
ACCOUNT_ROLES = {Membership.Role.OWNER, Membership.Role.ADMIN}
PAGE_SIZE = 25
STATUS_TONES = {
    Delivery.Status.SENT: "is-active",
    Delivery.Status.FAILED: "is-danger",
    Delivery.Status.SENDING: "is-warning",
    Delivery.Status.QUEUED: "is-warning",
    Delivery.Status.SCHEDULED: "is-muted",
    Delivery.Status.CANCELLED: "is-muted",
}


def _role_ok(context: dict[str, object], roles: set[Membership.Role]) -> bool:
    membership = context.get("membership")
    allowed = isinstance(membership, Membership) and membership.role in roles
    if context.get("support_session") is not None:
        # Suporte altera só com a concessão E com papel que já poderia fazê-lo.
        return bool(context.get("support_can_mutate")) and allowed
    return allowed


def _gate(request: HttpRequest) -> tuple[dict[str, object], HttpResponse | None]:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.DELIVERY))
    if blocked is None:
        context["can_write"] = _role_ok(context, WRITE_ROLES)
        context["can_configure"] = _role_ok(context, ACCOUNT_ROLES)
        context["status_tones"] = STATUS_TONES
    return context, blocked


def _companies(context: dict[str, object]) -> QuerySet[ClientCompany]:
    return cast("QuerySet[ClientCompany]", context["companies"])


def _load(context: dict[str, object], delivery_id: object) -> Delivery:
    return get_object_or_404(
        Delivery.objects.select_related("company", "requested_by", "resend_of").prefetch_related(
            "attachments"
        ),
        pk=delivery_id,
        organization=cast(Organization, context["office"]),
        company__in=_companies(context),
    )


@office_required
@require_GET
def index(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    base = Delivery.objects.filter(organization=office, company__in=_companies(context))
    q = request.GET.get("q", "").strip()[:100]
    status = request.GET.get("situacao", "")
    status = status if status in Delivery.Status.values else ""
    rows = base.select_related("company").order_by("-created_at")
    if q:
        rows = rows.filter(
            Q(company__name__icontains=q)
            | Q(subject__icontains=q)
            | Q(company__cnpj_masked__icontains=q)
        )
    if status:
        rows = rows.filter(status=status)
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("pagina"))
    params = {key: value for key, value in request.GET.items() if key != "pagina" and value}
    context.update(
        {
            "page_title": "Envio ao cliente",
            "page": page,
            "total": base.count(),
            "filters": {"q": q, "situacao": status},
            "filters_applied": bool(q or status),
            "query_without_page": urlencode(params),
            "status_choices": Delivery.Status.choices,
            "account_ready": DeliveryAccount.objects.filter(
                organization=office, active=True
            ).exists(),
        }
    )
    return render(request, "delivery/index.html", context)


@office_required
@require_http_methods(["GET", "POST"])
def compose(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if not context["can_write"]:
        return refuse(request, "Seu acesso só consulta os envios.")
    office = cast(Organization, context["office"])
    initial = {}
    company_id = request.GET.get("empresa")
    if company_id:
        company = _companies(context).filter(pk=company_id).first()
        if company is not None:
            initial = {"company": company.pk, "recipients": company.contact_email}
    form = ComposeForm(request.POST or None, companies=_companies(context), initial=initial)
    if request.method == "POST":
        form.read_files(request.FILES.getlist("files"))
        if form.is_valid():
            try:
                delivery = services.create_delivery(
                    organization=office,
                    company=form.cleaned_data["company"],
                    recipients=form.cleaned_data["recipients"],
                    subject=form.cleaned_data["subject"],
                    body=form.cleaned_data["body"],
                    attachments=form.files_data,
                    requested_by=request.user,
                    competence=form.cleaned_data["competence"],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                return redirect("delivery:detail", delivery_id=delivery.pk)
    context.update(
        {
            "page_title": "Novo envio",
            "form": form,
            "account_ready": DeliveryAccount.objects.filter(
                organization=office, active=True
            ).exists(),
        }
    )
    return render(request, "delivery/compose.html", context)


@office_required
@require_GET
def detail(request: HttpRequest, delivery_id: str) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    delivery = _load(context, delivery_id)
    context.update(
        {
            "page_title": delivery.subject,
            "delivery": delivery,
            "tone": STATUS_TONES.get(Delivery.Status(delivery.status), "is-muted"),
            "resends": delivery.resends.order_by("-created_at")[:20],
        }
    )
    return render(request, "delivery/detail.html", context)


@office_required
@require_POST
def resend(request: HttpRequest, delivery_id: str) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if not context["can_write"]:
        return refuse(request, "Seu acesso só consulta os envios.")
    delivery = _load(context, delivery_id)
    try:
        created = services.resend(delivery, requested_by=request.user)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect("delivery:detail", delivery_id=delivery.pk)
    return redirect("delivery:detail", delivery_id=created.pk)


@office_required
@require_POST
def cancel(request: HttpRequest, delivery_id: str) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if not context["can_write"]:
        return refuse(request, "Seu acesso só consulta os envios.")
    delivery = _load(context, delivery_id)
    try:
        services.cancel(delivery, actor=request.user)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect("delivery:detail", delivery_id=delivery.pk)


@office_required
@require_http_methods(["GET", "POST"])
def account(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if not context["can_configure"]:
        return refuse(request, "Só o dono e o administrador configuram a conta de envio.")
    office = cast(Organization, context["office"])
    instance = DeliveryAccount.objects.filter(organization=office).first()
    if instance is None:
        instance = DeliveryAccount(organization=office)
    form = AccountForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        record_event(
            action="delivery.account.saved",
            actor=request.user,
            organization=office,
            target=saved,
            request=request,
            metadata={"provider": saved.provider},
        )
        if request.POST.get("action") == "test":
            error = services.check_account(saved)
            if error:
                messages.error(request, error)
            else:
                messages.success(request, "Conexão confirmada.")
        else:
            messages.success(request, "Conta guardada.")
        return redirect("delivery:account")
    context.update({"page_title": "Conta de envio", "form": form, "account": instance})
    return render(request, "delivery/account.html", context)


@office_required
@require_http_methods(["GET", "POST"])
def release_days(request: HttpRequest) -> HttpResponse:
    """Dia de liberação por empresa: o e-mail da competência só sai a partir dele."""

    context, blocked = _gate(request)
    if blocked:
        return blocked
    companies = _companies(context).filter(active=True).order_by("name")
    if request.method == "POST":
        if not context["can_write"]:
            return refuse(request, "Seu acesso só consulta os envios.")
        company = get_object_or_404(companies, pk=request.POST.get("company"))
        raw = request.POST.get("day", "").strip()
        if raw and (not raw.isdigit() or not 1 <= int(raw) <= 31):
            messages.error(request, "Informe um dia de 1 a 31.")
        else:
            company.email_release_day = int(raw) if raw else None
            company.save(update_fields=["email_release_day", "updated_at"])
            record_event(
                action="delivery.release_day.changed",
                actor=request.user,
                organization=company.organization,
                target=company,
                request=request,
                metadata={"day": company.email_release_day},
            )
            messages.success(request, "Dia guardado.")
        return redirect("delivery:release-days")
    q = request.GET.get("q", "").strip()[:100]
    if q:
        companies = companies.filter(Q(name__icontains=q) | Q(cnpj_masked__icontains=q))
    page = Paginator(companies, 50).get_page(request.GET.get("pagina"))
    context.update(
        {"page_title": "Dia de liberação", "page": page, "q": q, "filters_applied": bool(q)}
    )
    return render(request, "delivery/release_days.html", context)
