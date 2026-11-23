"""Triagem: Pendências. Review queue grouped by sender, side panel, shortcuts, batch.

Every query is scoped by the office of the session and by the collaborator's companies
(``context["companies"]``); unassigned items (no company yet) are the administrator's only.
Decisions go through the same services as the item page (``update_review_fields`` and
``decide_item``), so learning, evidence and audit are identical. Nothing here archives: an
approved item waits as *pronto para arquivar*.
"""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlencode
from uuid import UUID

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import (
    _can_manage_collaborators,
    _module_page_context,
    office_required,
    refuse,
)
from apps.organizations.models import Organization
from apps.triage import learning
from apps.triage.extraction import _payload_text
from apps.triage.forms import TriageFieldsForm
from apps.triage.models import TriageItem
from apps.triage.services import decide_item, update_review_fields
from apps.triage.transitions import InvalidTransition, TriageStatus

QUEUE_LIMIT = 200
BATCH_LIMIT = 50
TEXT_LIMIT = 20_000
_PREVIEW_SUFFIXES = (".pdf", ".xml", ".csv", ".ofx")


def _scoped(context: dict[str, object], office: Organization) -> QuerySet[TriageItem]:
    scope = Q(company__in=context["companies"])
    if _can_manage_collaborators(context):
        scope |= Q(company__isnull=True)
    return TriageItem.objects.filter(organization=office).filter(scope)


def _pending(context: dict[str, object], office: Organization) -> QuerySet[TriageItem]:
    return _scoped(context, office).filter(status=TriageStatus.AWAITING_REVIEW)


def _margin(item: TriageItem) -> int:
    company = (item.scores or {}).get("company")
    return int(company.get("margin", 0)) if isinstance(company, dict) else 0


def _sender(item: TriageItem) -> str:
    keys = learning.item_sender_keys(item)
    return keys[0] if keys else (item.sender or "Sem remetente")[:120]


def _can_write(context: dict[str, object], office: Organization) -> bool:
    return bool(context.get("support_can_mutate")) and not office.is_demo


def _inbox_url(item: TriageItem | None = None, **params: str) -> str:
    query = {key: value for key, value in params.items() if value}
    if item is not None:
        query["item"] = str(item.pk)
    base = reverse("hub:triage-inbox")
    return f"{base}?{urlencode(query)}" if query else base


@office_required
@require_http_methods(["GET"])
def triage_inbox(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    sender_filter = request.GET.get("remetente", "").strip().casefold()[:254]
    queue = list(
        _pending(context, office)
        .select_related("company", "document_type", "safety_scan", "mailbox")
        .order_by("created_at")[:QUEUE_LIMIT]
    )
    total = len(queue)
    # Least confident first: the engine's margin is where a person's time pays most.
    queue.sort(key=lambda item: (_margin(item), item.created_at))
    if sender_filter:
        queue = [item for item in queue if sender_filter in _sender(item).casefold()]
    groups: dict[str, list[TriageItem]] = {}
    for item in queue:
        groups.setdefault(_sender(item), []).append(item)
    selected: TriageItem | None = None
    wanted = request.GET.get("item", "")
    if wanted:
        try:
            wanted_id = UUID(wanted)
        except ValueError:
            raise Http404 from None
        selected = get_object_or_404(
            _pending(context, office).select_related(
                "company", "document_type", "safety_scan", "mailbox", "blob"
            ),
            pk=wanted_id,
        )
    elif queue:
        selected = queue[0]
    previous_item = next_item = None
    if selected is not None and selected in queue:
        position = queue.index(selected)
        previous_item = queue[position - 1] if position > 0 else None
        next_item = queue[position + 1] if position + 1 < len(queue) else None
    context.update(
        {
            "page_title": "Pendências",
            "groups": [
                {"sender": sender, "items": items, "count": len(items)}
                for sender, items in groups.items()
            ],
            "total": total,
            "shown": len(queue),
            "sender_filter": sender_filter,
            "selected": selected,
            "can_write": _can_write(context, office),
            "previous_url": _inbox_url(previous_item, remetente=sender_filter)
            if previous_item
            else "",
            "next_url": _inbox_url(next_item, remetente=sender_filter) if next_item else "",
        }
    )
    if selected is not None:
        context.update(_panel_context(selected, context, office))
    return render(request, "hub/triage_inbox.html", context)


def _panel_context(
    item: TriageItem, context: dict[str, object], office: Organization
) -> dict[str, Any]:
    form = TriageFieldsForm(
        organization=office,
        companies=context["companies"],
        initial={
            "company": item.company_id,
            "document_type": item.document_type_id,
            "period_label": item.period_label,
            "counterparty_token": item.counterparty_token,
            "final_name": item.final_name,
        },
        auto_id="inbox-%s",
    )
    try:
        text = _payload_text(item)[:TEXT_LIMIT]
    except (ValidationError, OSError):
        text = ""
    why = [
        {
            "label": label,
            "value": entry.get("valor", ""),
            "why": entry.get("evidencia", ""),
            "points": entry.get("pontos"),
            "margin": entry.get("margem"),
        }
        for label, entry in (item.ai_fields or {}).items()
        if isinstance(entry, dict)
    ]
    safety = getattr(item, "safety_scan", None)
    previewable = (
        item.original_name.casefold().endswith(_PREVIEW_SUFFIXES)
        and safety is not None
        and safety.verdict == "clean"
        and safety.format_verdict == "valid"
    )
    return {
        "form": form,
        "why": why,
        "text": text,
        "previewable": previewable,
        "is_pdf": item.original_name.casefold().endswith(".pdf"),
    }


def _next_url(
    request: HttpRequest, context: dict[str, object], office: Organization, current: UUID
) -> str:
    following = _pending(context, office).exclude(pk=current).order_by("created_at").first()
    return _inbox_url(following) if following else _inbox_url()


def _writer_gate(
    request: HttpRequest, context: dict[str, object], office: Organization
) -> HttpResponse | None:
    if office.is_demo:
        return refuse(request, "A demonstração não decide arquivos.", kind="unavailable")
    if not context.get("support_can_mutate"):
        return refuse(request, "Este perfil não pode decidir o destino deste arquivo.")
    return None


@office_required
@require_http_methods(["POST"])
def triage_inbox_approve(request: HttpRequest, item_id: UUID) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    if gate := _writer_gate(request, context, office):
        return gate
    item = get_object_or_404(_pending(context, office), pk=item_id)
    form = TriageFieldsForm(request.POST, organization=office, companies=context["companies"])
    if not form.is_valid():
        messages.error(request, "Revise empresa, tipo, período e nome.")
        return redirect(_inbox_url(item))
    data = form.cleaned_data
    if data["company"] is None or data["document_type"] is None:
        messages.error(request, "Escolha empresa e tipo antes de aprovar.")
        return redirect(_inbox_url(item))
    try:
        item = update_review_fields(
            item=item,
            actor=cast(User, request.user),
            company=data["company"],
            document_type=data["document_type"],
            period_label=data["period_label"],
            counterparty_token=data["counterparty_token"],
            final_name=data["final_name"],
            reason=data["reason"],
            request=request,
        )
        decide_item(
            item=item,
            actor=cast(User, request.user),
            decision="archive",
            reason="",
            request=request,
        )
    except (ValidationError, InvalidTransition) as exc:
        messages.error(request, " ".join(getattr(exc, "messages", [str(exc)])))
        return redirect(_inbox_url(item))
    messages.success(request, "Aprovado.")
    return redirect(_next_url(request, context, office, item.pk))


@office_required
@require_http_methods(["POST"])
def triage_inbox_reject(request: HttpRequest, item_id: UUID) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    if gate := _writer_gate(request, context, office):
        return gate
    item = get_object_or_404(_pending(context, office), pk=item_id)
    reason = request.POST.get("reason", "").strip()[:500]
    if not reason:
        messages.error(request, "Informe o motivo da rejeição.")
        return redirect(_inbox_url(item))
    try:
        decide_item(
            item=item,
            actor=cast(User, request.user),
            decision="reject",
            reason=reason,
            request=request,
        )
    except (ValidationError, InvalidTransition) as exc:
        messages.error(request, " ".join(getattr(exc, "messages", [str(exc)])))
        return redirect(_inbox_url(item))
    messages.success(request, "Rejeitado.")
    return redirect(_next_url(request, context, office, item.pk))


@office_required
@require_http_methods(["POST"])
def triage_inbox_batch(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    if gate := _writer_gate(request, context, office):
        return gate
    action = request.POST.get("action", "")
    raw_ids = request.POST.getlist("ids")
    if action not in {"approve", "reject"} or not raw_ids:
        messages.error(request, "Selecione arquivos.")
        return redirect(_inbox_url())
    if len(raw_ids) > BATCH_LIMIT:
        messages.error(request, f"No máximo {BATCH_LIMIT} arquivos por vez.")
        return redirect(_inbox_url())
    ids: list[UUID] = []
    for raw in raw_ids:
        try:
            ids.append(UUID(raw))
        except ValueError:
            continue
    reason = request.POST.get("reason", "").strip()[:500]
    if action == "reject" and not reason:
        messages.error(request, "Informe o motivo da rejeição.")
        return redirect(_inbox_url())
    done = incomplete = failed = 0
    actor = cast(User, request.user)
    for item in (
        _pending(context, office).filter(pk__in=ids).select_related("company", "document_type")
    ):
        try:
            if action == "reject":
                decide_item(
                    item=item, actor=actor, decision="reject", reason=reason, request=request
                )
                done += 1
                continue
            if not (
                item.company_id and item.document_type_id and item.period_label and item.final_name
            ):
                incomplete += 1
                continue
            decide_item(item=item, actor=actor, decision="archive", reason="", request=request)
            done += 1
        except (ValidationError, InvalidTransition):
            failed += 1
    verb = "aprovado" if action == "approve" else "rejeitado"
    parts = [f"{done} {verb}{'s' if done != 1 else ''}"]
    if incomplete:
        parts.append(f"{incomplete} sem dados completos")
    if failed:
        parts.append(f"{failed} com erro")
    (messages.success if done else messages.error)(request, " · ".join(parts))
    return redirect(_inbox_url())


@office_required
@require_http_methods(["POST"])
def triage_inbox_rule(request: HttpRequest, item_id: UUID) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    if gate := _writer_gate(request, context, office):
        return gate
    # Field rules change how a company is recognised for the whole office: administrators only.
    if not _can_manage_collaborators(context):
        return refuse(request, "Somente o administrador ensina regras de campo.")
    item = get_object_or_404(_pending(context, office).select_related("blob"), pk=item_id)
    company: ClientCompany | None = None
    raw_company = request.POST.get("company", "")
    if raw_company:
        try:
            company = (
                cast("QuerySet[ClientCompany]", context["companies"])
                .filter(organization=office, pk=raw_company)
                .first()
            )
        except (ValidationError, ValueError):
            company = None
    else:
        company = item.company
    selected = request.POST.get("selected_text", "")
    if company is None:
        messages.error(request, "Escolha a empresa da regra.")
        return redirect(_inbox_url(item))
    try:
        rule = learning.create_field_rule(
            item=item, company=company, selected=selected, text=_payload_text(item)
        )
    except (ValueError, ValidationError) as exc:
        messages.error(request, " ".join(getattr(exc, "messages", [str(exc)])))
        return redirect(_inbox_url(item))
    record_event(
        action="triage.rule.created",
        actor=cast(User, request.user),
        organization=office,
        target=item,
        request=request,
        metadata={"mode": rule.mode, "company_id": str(company.pk)},
    )
    messages.success(request, "Regra guardada.")
    return redirect(_inbox_url(item))
