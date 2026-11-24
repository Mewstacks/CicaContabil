"""Tela de procurações da NFS-e (D-304, D-305).

Escritório em modo `procuracao`: envia o próprio e-CNPJ, vê o estado da procuração de cada
empresa, pede procuração ao cliente por e-mail e força uma nova verificação. Escritório do
modo legado (A1 por empresa) nunca chega aqui: é devolvido à página de certificados.
"""

from __future__ import annotations

import io
import uuid
from typing import Any, cast
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Case, Count, IntegerField, OuterRef, Q, QuerySet, Subquery, Value, When
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.audit.services import record_event
from apps.hub.models import (
    ClientCompany,
    NfseDocument,
    NfseProcuracaoRequest,
    NfseSync,
    OfficeCertificate,
    ProductModule,
)
from apps.hub.nfse_procuracao import current_office_certificate, seed_procuracao_syncs
from apps.hub.office_certificate import (
    OfficeCertificateError,
    revoke_office_certificate,
    store_office_certificate,
    uses_procuracao,
)
from apps.hub.procuracao_requests import request_procuracao
from apps.hub.tasks_procuracao import lane_enabled, lane_paused
from apps.hub.views import (
    collaborator_can_use_module,
    office_required,
    refuse,
    workspace_context,
)
from apps.hub.views_roster import _blocked_reason
from apps.organizations.models import Membership, Organization

PAGE_SIZE = 25
MAX_PFX_BYTES = 512_000
EXPIRING_DAYS = 30
STATUS_TABS = (
    ("all", "Todas"),
    ("missing", "Sem procuração"),
    ("unknown", "A verificar"),
    ("ok", "Em dia"),
    ("error", "Com erro"),
)
STATUS_BADGE = {
    NfseSync.ProcuracaoStatus.OK: "is-active",
    NfseSync.ProcuracaoStatus.MISSING: "is-warning",
    NfseSync.ProcuracaoStatus.UNKNOWN: "is-muted",
    NfseSync.ProcuracaoStatus.ERROR: "is-danger",
}
CERTIFICATE_MANAGERS = {Membership.Role.OWNER, Membership.Role.ADMIN}
REQUESTERS = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
    Membership.Role.OPERATOR,
}


def _mask(cnpj: str) -> str:
    digits = "".join(ch for ch in cnpj if ch.isalnum())
    if len(digits) != 14:
        return cnpj
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _lane(request: HttpRequest) -> dict[str, str]:
    from django.conf import settings

    if not settings.NFSE_PROCURACAO_SYNC_ENABLED:
        return {"label": "Coleta desligada", "tone": "is-muted"}
    if settings.NFSE_ADN_ENVIRONMENT != "production":
        return {"label": "Coleta só em produção", "tone": "is-warning"}
    if lane_paused():
        return {"label": "Coleta em pausa", "tone": "is-warning"}
    return {"label": "Coleta ligada", "tone": "is-active"}


def _certificate_summary(office: Organization, now: Any) -> dict[str, Any]:
    current = current_office_certificate(office.pk, now=now)
    if current is not None:
        days = (current.valid_until - now).days
        return {
            "certificate": current,
            "state": "expiring" if days <= EXPIRING_DAYS else "valid",
            "label": "vence em breve" if days <= EXPIRING_DAYS else "válido",
            "tone": "is-warning" if days <= EXPIRING_DAYS else "is-active",
            "days_left": days,
            "cnpj": _mask(current.cnpj),
            "quarantined": bool(current.quarantined_until and current.quarantined_until > now),
        }
    latest = OfficeCertificate.objects.filter(organization=office).order_by("-valid_until").first()
    if latest is None:
        return {"certificate": None, "state": "none", "label": "ausente", "tone": "is-danger"}
    revoked = latest.revoked_at is not None
    return {
        "certificate": None,
        "state": "revoked" if revoked else "expired",
        "label": "revogado" if revoked else "vencido",
        "tone": "is-danger",
        "cnpj": _mask(latest.cnpj),
    }


def _return_url(request: HttpRequest) -> str:
    allowed = {key: request.POST.get(key, "") for key in ("status", "q", "page")}
    query = urlencode({key: value for key, value in allowed.items() if value})
    base = reverse("hub:procuracoes")
    return f"{base}?{query}" if query else base


def _selected(request: HttpRequest, scope: QuerySet[ClientCompany]) -> QuerySet[ClientCompany]:
    """Only companies inside the member's own portfolio, whatever ids the form sends."""

    ids = []
    for raw in request.POST.getlist("company"):
        try:
            ids.append(uuid.UUID(raw))
        except ValueError:
            continue
    return scope.filter(active=True, pk__in=ids) if ids else scope.none()


def _pending(scope: QuerySet[ClientCompany], office: Organization) -> QuerySet[ClientCompany]:
    waiting = NfseSync.objects.filter(
        organization=office,
        credential_mode=NfseSync.CredentialMode.PROCURACAO,
        procuracao_status__in=[
            NfseSync.ProcuracaoStatus.MISSING,
            NfseSync.ProcuracaoStatus.UNKNOWN,
        ],
    ).values("company_id")
    return scope.filter(active=True, pk__in=waiting)


def _verify(office: Organization, companies: QuerySet[ClientCompany]) -> int:
    now = timezone.now()
    due = NfseSync.objects.filter(
        organization=office,
        company__in=companies,
        credential_mode=NfseSync.CredentialMode.PROCURACAO,
        enabled=True,
        status__in=[NfseSync.Status.IDLE, NfseSync.Status.RETRY, NfseSync.Status.ERROR],
    )
    changed = due.update(status=NfseSync.Status.IDLE, next_run_at=now, failure_count=0)
    if changed and lane_enabled():
        from apps.hub.tasks_procuracao import dispatch_procuracao_syncs

        transaction.on_commit(dispatch_procuracao_syncs.delay)
    return int(changed)


def _safe_cell(value: object) -> str:
    """Neutralize spreadsheet formulas coming from names and e-mail addresses."""

    text = "" if value is None else str(value)
    return f"'{text}" if text[:1] in {"=", "+", "-", "@", "\t", "\r"} else text


def _pending_workbook(rows: Any) -> bytes:
    from openpyxl import Workbook  # type: ignore[import-untyped]

    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Pendentes"
    sheet.append(["Empresa", "CNPJ", "Código Domínio", "E-mail", "Situação", "Último pedido"])
    for row in rows:
        sheet.append(
            [
                _safe_cell(row.company.name),
                _safe_cell(_mask(row.company.cnpj_masked)),
                _safe_cell(row.company.dominio_code),
                _safe_cell(row.company.contact_email),
                _safe_cell(row.get_procuracao_status_display()),
                row.requested_at.strftime("%d/%m/%Y") if row.requested_at else "",
            ]
        )
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _plural(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _report(request: HttpRequest, outcome: Any) -> None:
    if outcome.stopped and not outcome.sent:
        messages.error(request, outcome.stopped)
        return
    parts = []
    if outcome.sent:
        parts.append(_plural(outcome.sent, "pedido enviado", "pedidos enviados"))
    if outcome.recent:
        parts.append(f"{outcome.recent} já pedido(s) há menos de 3 dias")
    if outcome.no_email:
        parts.append(f"{outcome.no_email} sem e-mail")
    if outcome.over_limit:
        parts.append(f"{outcome.over_limit} ficaram para o próximo envio")
    if outcome.failed:
        parts.append(outcome.stopped or "falha no envio")
    text = " · ".join(parts) or "Nenhuma empresa para pedir."
    (messages.success if outcome.sent and not outcome.failed else messages.warning)(request, text)


@office_required
@require_http_methods(["GET", "POST"])
def nfse_procuracoes(request: HttpRequest) -> HttpResponseBase:
    context = workspace_context(request)
    if not collaborator_can_use_module(context, ProductModule.Code.NFSE):
        return refuse(request, "Seu acesso não inclui NFS-e Inteligente.")
    office = context["office"]
    assert isinstance(office, Organization)
    if not uses_procuracao(office):
        return redirect("hub:certificates")
    membership = context["membership"]
    member = isinstance(membership, Membership) and context["support_session"] is None
    can_manage_certificate = bool(
        member and cast(Membership, membership).role in CERTIFICATE_MANAGERS
    )
    can_request = bool(
        member and context["support_can_mutate"] and cast(Membership, membership).role in REQUESTERS
    )
    scope = cast("QuerySet[ClientCompany]", context["companies"])

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action in {"upload-certificate", "revoke-certificate"}:
            if not can_manage_certificate:
                return refuse(request, "Somente owners e administradores cuidam do e-CNPJ.")
            if action == "revoke-certificate":
                certificate = current_office_certificate(office.pk)
                if certificate is not None:
                    revoke_office_certificate(certificate, actor=request.user, request=request)
                    messages.success(request, "e-CNPJ revogado. A coleta do escritório parou.")
                return redirect(_return_url(request))
            upload = request.FILES.get("pfx")
            if upload is None or not (upload.name or "").lower().endswith((".pfx", ".p12")):
                messages.error(request, "Selecione o arquivo .pfx ou .p12 do e-CNPJ.")
            elif (upload.size or 0) > MAX_PFX_BYTES:
                messages.error(request, "O arquivo é maior que o esperado para um e-CNPJ A1.")
            else:
                try:
                    stored = store_office_certificate(
                        organization=office,
                        pfx_bytes=upload.read(),
                        password=request.POST.get("password", ""),
                        actor=request.user,
                        request=request,
                    )
                except OfficeCertificateError as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(
                        request, f"e-CNPJ enviado, válido até {stored.valid_until:%d/%m/%Y}."
                    )
            return redirect(_return_url(request))
        if action in {"request", "request-pending", "verify", "verify-all"}:
            if not can_request:
                return refuse(request, "Seu perfil não pede procurações.")
            if action in {"request", "request-pending"}:
                picked = _pending(scope, office) if action == "request-pending" else None
                companies = picked if picked is not None else _selected(request, scope)
                _report(
                    request,
                    request_procuracao(
                        organization=office,
                        companies=companies.order_by("name"),
                        actor=request.user,
                        request=request,
                    ),
                )
            else:
                everyone = scope.filter(active=True) if action == "verify-all" else None
                changed = _verify(
                    office, everyone if everyone is not None else _selected(request, scope)
                )
                if changed:
                    messages.success(
                        request, f"Verificação agendada: {_plural(changed, 'empresa', 'empresas')}."
                    )
                else:
                    messages.warning(request, "Nenhuma empresa para verificar.")
            return redirect(_return_url(request))
        return redirect(_return_url(request))

    if request.GET.get("export") == "pendentes":
        if not can_request:
            return refuse(request, "Seu perfil não baixa a lista de pendências.")
        pending = (
            NfseSync.objects.filter(
                organization=office,
                company__in=scope,
                company__active=True,
                credential_mode=NfseSync.CredentialMode.PROCURACAO,
                procuracao_status__in=[
                    NfseSync.ProcuracaoStatus.MISSING,
                    NfseSync.ProcuracaoStatus.UNKNOWN,
                ],
            )
            .select_related("company")
            .annotate(
                requested_at=Subquery(
                    NfseProcuracaoRequest.objects.filter(
                        company=OuterRef("company_id"),
                        status=NfseProcuracaoRequest.Status.SENT,
                    )
                    .order_by("-sent_at")
                    .values("sent_at")[:1]
                )
            )
            .order_by("company__name")
        )
        record_event(
            action="hub.nfse.procuracao_exported",
            actor=request.user,
            organization=office,
            target=office,
            request=request,
            metadata={"rows": pending.count()},
        )
        response = HttpResponse(
            _pending_workbook(pending),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="procuracoes-pendentes.xlsx"'
        response["Cache-Control"] = "no-store"
        return response

    now = timezone.now()
    synced = NfseSync.objects.filter(
        organization=office, credential_mode=NfseSync.CredentialMode.PROCURACAO
    )
    if scope.filter(active=True).count() > synced.filter(company__in=scope).count():
        seed_procuracao_syncs(organization_id=office.pk)
    rows_all = synced.filter(company__in=scope, company__active=True)
    counts = {
        item["procuracao_status"]: item["n"]
        for item in rows_all.values("procuracao_status").annotate(n=Count("pk"))
    }
    tab = request.GET.get("status", "all")
    if tab not in {key for key, _label in STATUS_TABS}:
        tab = "all"
    search = request.GET.get("q", "").strip()[:100]
    rows = rows_all
    if tab != "all":
        rows = rows.filter(procuracao_status=tab)
    if search:
        digits = "".join(ch for ch in search if ch.isalnum())
        rows = rows.filter(
            Q(company__name__icontains=search)
            | Q(company__cnpj_masked__icontains=search)
            | (Q(company__cnpj_masked__icontains=digits) if len(digits) >= 4 else Q(pk__in=[]))
        )
    document_count = (
        NfseDocument.objects.filter(company=OuterRef("company_id"))
        .order_by()
        .values("company")
        .annotate(total=Count("pk"))
        .values("total")
    )
    last_request = (
        NfseProcuracaoRequest.objects.filter(
            company=OuterRef("company_id"), status=NfseProcuracaoRequest.Status.SENT
        )
        .order_by("-sent_at")
        .values("sent_at")[:1]
    )
    rows = (
        rows.select_related("company")
        .annotate(
            documents=Subquery(document_count, output_field=IntegerField()),
            requested_at=Subquery(last_request),
            priority=Case(
                When(procuracao_status=NfseSync.ProcuracaoStatus.MISSING, then=Value(0)),
                When(procuracao_status=NfseSync.ProcuracaoStatus.ERROR, then=Value(1)),
                When(procuracao_status=NfseSync.ProcuracaoStatus.UNKNOWN, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            ),
        )
        .order_by("priority", "company__name")
    )
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    for row in page.object_list:
        row.badge = STATUS_BADGE[NfseSync.ProcuracaoStatus(row.procuracao_status)]
        row.cnpj_display = _mask(row.company.cnpj_masked)
    summary = _certificate_summary(office, now)
    context.update(
        {
            "page_title": "Procurações",
            "nfse_view": "collection",
            "certificate_summary": summary,
            "lane": _lane(request),
            "can_manage_certificate": can_manage_certificate,
            "can_request": can_request,
            "roster_available": not _blocked_reason(context, office),
            "tabs": [
                {
                    "key": key,
                    "label": label,
                    "count": sum(counts.values()) if key == "all" else counts.get(key, 0),
                    "current": key == tab,
                }
                for key, label in STATUS_TABS
            ],
            "tab": tab,
            "search": search,
            "page": page,
            "total_rows": sum(counts.values()),
            "filtered": bool(search or tab != "all"),
        }
    )
    return render(request, "hub/nfse_procuracao.html", context)
