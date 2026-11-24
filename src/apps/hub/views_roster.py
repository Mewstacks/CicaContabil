"""Carteira por planilha (D-304, E2): enviar, ver a prévia, confirmar e baixar os erros.

Só escritório em modo `procuracao`. Respeita as mesmas travas do cadastro manual de empresa:
perfil que pode mexer na carteira, escritório de demonstração, empresas controladas pelo Domínio
ou pelo controle central da Mewstack.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import cast

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub import company_roster
from apps.hub.imports import ImportValidationError
from apps.hub.models import ClientCompany, ControlPlaneBinding, ImportBatch, ProductModule
from apps.hub.nfse_procuracao import seed_procuracao_syncs
from apps.hub.office_certificate import uses_procuracao
from apps.hub.views import (
    _can_manage_companies,
    _sees_every_company,
    collaborator_can_use_module,
    office_required,
    refuse,
    workspace_context,
)
from apps.intelligence.models import IntelligenceConnector
from apps.organizations.models import Membership, Organization
from apps.platform import limits as plan_limits

PAGE_SIZE = 50
HISTORY_SIZE = 8


@dataclass
class _Scope:
    context: dict[str, object]
    office: Organization
    membership: Membership | None
    can_import: bool
    reason: str
    # None = the member reaches every company of the office; otherwise only these ids. A CNPJ the
    # office has outside this set is reported without a name and never changed by the roster.
    visible_ids: frozenset[str] | None = None


def _blocked_reason(context: dict[str, object], office: Organization) -> str:
    """Why the member cannot add companies right now; empty when they can."""

    if office.is_demo:
        return "A demonstração não recebe empresas."
    if not _can_manage_companies(context):
        return "Seu perfil não altera a carteira."
    if (
        IntelligenceConnector.objects.filter(organization=office)
        .exclude(status="not_configured")
        .exists()
    ):
        return "As empresas deste escritório são sincronizadas pelo Domínio."
    if ControlPlaneBinding.objects.filter(organization=office).exists():
        return "As empresas desta instalação são controladas pelo controle central da Mewstack."
    return ""


def visible_company_ids(context: dict[str, object]) -> frozenset[str] | None:
    """Which companies the member reaches; `None` = the whole office.

    Mirrors `company_queryset_for_membership`: owner and admin reach the whole office, and so does
    a support session without a company list. Today only those profiles pass
    `_can_manage_companies`, so a partial portfolio cannot reach the roster; this stays as a
    seatbelt for the day that gate is relaxed (security review, 20/11/2026): the roster must not
    become a way to see or change a company the member's portfolio does not include.
    """

    membership = context.get("membership")
    if context.get("support_session") is not None:
        return None if _sees_every_company(context) else frozenset()
    if isinstance(membership, Membership) and membership.role in {
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
    }:
        return None
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    return frozenset(str(pk) for pk in companies.values_list("pk", flat=True))


def _scope(request: HttpRequest) -> _Scope | HttpResponseBase:
    context = workspace_context(request)
    if not collaborator_can_use_module(context, ProductModule.Code.NFSE):
        return refuse(request, "Seu acesso não inclui NFS-e Inteligente.")
    office = context["office"]
    assert isinstance(office, Organization)
    if not uses_procuracao(office):
        return redirect("hub:companies")
    membership = context["membership"]
    reason = _blocked_reason(context, office)
    visible = visible_company_ids(context)
    return _Scope(
        context=context,
        office=office,
        membership=membership if isinstance(membership, Membership) else None,
        can_import=not reason,
        reason=reason,
        visible_ids=visible,
    )


def _batch(office: Organization, batch_id: uuid.UUID) -> ImportBatch:
    batch = (
        ImportBatch.objects.filter(
            pk=batch_id, organization=office, kind=ImportBatch.Kind.COMPANIES
        )
        .select_related("data_source")
        .first()
    )
    if batch is None or not company_roster.is_roster_batch(batch):
        raise Http404("Lote inexistente.")
    return batch


def _room(office: Organization) -> int | None:
    """New companies the plan still allows; `None` when the plan has no company limit."""

    return plan_limits.room(office, plan_limits.COMPANIES)


def _plural(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _summary(result: company_roster.RosterResult) -> str:
    parts = [_plural(result.created, "empresa importada", "empresas importadas")]
    if result.updated:
        parts.append(_plural(result.updated, "e-mail atualizado", "e-mails atualizados"))
    if result.problems:
        parts.append(f"{result.problems} com problema")
    return " · ".join(parts)


@office_required
@require_http_methods(["GET", "POST"])
def roster(request: HttpRequest) -> HttpResponseBase:
    scope = _scope(request)
    if isinstance(scope, HttpResponseBase):
        return scope
    if request.method == "POST":
        if not scope.can_import:
            return refuse(request, scope.reason)
        upload = request.FILES.get("planilha")
        if upload is None:
            messages.error(request, "Selecione a planilha .csv ou .xlsx.")
            return redirect("hub:roster")
        try:
            batch, created = company_roster.create_roster_batch(
                organization=scope.office,
                upload=upload,
                actor=cast(User, request.user),
                request=request,
            )
        except ImportValidationError as exc:
            messages.error(request, str(exc))
            return redirect("hub:roster")
        if not created and batch.status == ImportBatch.Status.COMPLETED:
            messages.info(request, "Esta planilha já foi importada.")
        return redirect("hub:roster-batch", batch_id=batch.pk)
    history = list(
        ImportBatch.objects.filter(
            organization=scope.office, kind=ImportBatch.Kind.COMPANIES, mapping__roster=True
        ).order_by("-created_at")[:HISTORY_SIZE]
    )
    context = dict(scope.context)
    context.update(
        {
            "page_title": "Carteira",
            "nfse_view": "collection",
            "mode": "upload",
            "can_import": scope.can_import,
            "blocked_reason": scope.reason,
            "history": history,
            "plan_notice": plan_limits.state(scope.office, plan_limits.COMPANIES).message,
        }
    )
    return render(request, "hub/nfse_carteira.html", context)


@office_required
@require_http_methods(["GET", "POST"])
def roster_batch(request: HttpRequest, batch_id: uuid.UUID) -> HttpResponseBase:
    scope = _scope(request)
    if isinstance(scope, HttpResponseBase):
        return scope
    batch = _batch(scope.office, batch_id)
    if request.method == "POST":
        if not scope.can_import:
            return refuse(request, scope.reason)
        action = request.POST.get("action", "")
        if action == "confirm":
            result = company_roster.apply_roster(
                batch=batch,
                actor=cast(User, request.user),
                membership=scope.membership,
                max_new=_room(scope.office),
                visible_ids=scope.visible_ids,
                request=request,
            )
            if result is None:
                messages.info(request, "Este lote já foi processado.")
            else:
                if result.created:
                    seed_procuracao_syncs(organization_id=scope.office.pk)
                (messages.success if result.created or result.updated else messages.warning)(
                    request, _summary(result)
                )
        elif action == "discard" and batch.status == ImportBatch.Status.PREVIEW:
            record_event(
                action="hub.roster.discarded",
                actor=request.user,
                organization=scope.office,
                target=batch,
                request=request,
            )
            batch.delete()
            messages.info(request, "Planilha descartada.")
            return redirect("hub:roster")
        return redirect("hub:roster-batch", batch_id=batch_id)

    preview_mode = batch.status == ImportBatch.Status.PREVIEW
    if preview_mode:
        preview = company_roster.analyse_roster(
            organization=scope.office,
            rows=company_roster.batch_rows(batch),
            data_source=batch.data_source,
            max_new=_room(scope.office),
            visible_ids=scope.visible_ids,
        )
        lines = preview.lines
        counts = {
            "create": preview.create,
            "update": preview.update,
            "same": preview.same,
            "problem": preview.problems,
            "without_email": preview.without_email,
            "importable": preview.importable,
        }
    else:
        lines = company_roster.stored_report_lines(batch)
        counts = {
            "create": batch.created_count,
            "update": batch.updated_count,
            "same": 0,
            "problem": sum(1 for line in lines if line.problems),
            "without_email": sum(1 for line in lines if "Sem e-mail" in line.notes),
            "importable": 0,
        }
    tab = request.GET.get("situacao", "todas")
    if tab not in {"todas", "problemas"}:
        tab = "todas"
    shown = [line for line in lines if line.problems] if tab == "problemas" else lines
    page = Paginator(shown, PAGE_SIZE).get_page(request.GET.get("page"))
    context = dict(scope.context)
    context.update(
        {
            "page_title": "Carteira",
            "nfse_view": "collection",
            "mode": "preview" if preview_mode else "result",
            "batch": batch,
            "can_import": scope.can_import,
            "blocked_reason": scope.reason,
            "counts": counts,
            "page": page,
            "tab": tab,
            "has_report": any(line.problems or line.notes for line in lines),
            "errors_url": reverse("hub:roster-errors", args=[batch.pk]),
            "total_lines": len(lines),
            "problem_lines": counts["problem"],
        }
    )
    return render(request, "hub/nfse_carteira.html", context)


@office_required
@require_GET
def roster_errors(request: HttpRequest, batch_id: uuid.UUID) -> HttpResponseBase:
    scope = _scope(request)
    if isinstance(scope, HttpResponseBase):
        return scope
    if not scope.can_import:
        return refuse(request, scope.reason)
    batch = _batch(scope.office, batch_id)
    if batch.status == ImportBatch.Status.PREVIEW:
        lines = company_roster.analyse_roster(
            organization=scope.office,
            rows=company_roster.batch_rows(batch),
            data_source=batch.data_source,
            max_new=_room(scope.office),
            visible_ids=scope.visible_ids,
        ).reportable()
    else:
        lines = company_roster.stored_report_lines(batch)
    response = HttpResponse(
        company_roster.error_report_csv(lines), content_type="text/csv; charset=utf-8"
    )
    response["Content-Disposition"] = 'attachment; filename="carteira-erros.csv"'
    response["Cache-Control"] = "no-store"
    return response


@office_required
@require_GET
def roster_template(request: HttpRequest) -> HttpResponseBase:
    scope = _scope(request)
    if isinstance(scope, HttpResponseBase):
        return scope
    response = HttpResponse(company_roster.template_csv(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="carteira-modelo.csv"'
    return response
