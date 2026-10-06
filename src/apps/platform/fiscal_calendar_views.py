"""Platform review of the legal-deadline reference data (D-277).

Offices never approve deadlines: a platform developer or administrator reads the legal basis
and the source, then approves a calendar year or a rule version. Approval is audited and an
approved rule only leaves service by retirement.
"""

from __future__ import annotations

from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.audit.services import record_event
from apps.fiscal_calendar.models import (
    BusinessCalendarYear,
    ReferenceStatus,
    TaxDeadlineRule,
)
from apps.platform.models import PlatformAccess
from apps.platform.policies import platform_required
from apps.platform.views import _platform_user, context


@platform_required(PlatformAccess.Role.DEVELOPER, PlatformAccess.Role.ADMIN)
@require_http_methods(["GET", "POST"])
def fiscal_calendar_review(request: HttpRequest) -> HttpResponse:
    user = _platform_user(request)
    if request.method == "POST":
        kind = request.POST.get("kind")
        decision = request.POST.get("decision")
        model = {"calendar": BusinessCalendarYear, "rule": TaxDeadlineRule}.get(str(kind))
        if model is None or decision not in {"approve", "retire"}:
            raise Http404
        with transaction.atomic():
            item = get_object_or_404(model.objects.select_for_update(), pk=request.POST.get("id"))
            if decision == "approve" and item.status == ReferenceStatus.DRAFT:
                item.status = ReferenceStatus.APPROVED
                item.approved_by = user
                item.approved_at = timezone.now()
                item.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
            elif decision == "retire" and item.status == ReferenceStatus.APPROVED:
                item.status = ReferenceStatus.RETIRED
                item.save(update_fields=["status", "updated_at"])
            else:
                messages.error(request, "Esta referência mudou. Confira a situação atual.")
                return redirect("platform:fiscal-calendar")
            outcome = "approved" if decision == "approve" else "retired"
            record_event(
                action=f"fiscal_calendar.{kind}_{outcome}",
                actor=user,
                request=request,
                metadata={"id": str(item.pk), "label": str(item)},
            )
        messages.success(
            request, f"{item} {'aprovada' if decision == 'approve' else 'retirada'}."
        )
        return redirect("platform:fiscal-calendar")
    ctx = context(request)
    ctx.update(
        {
            "page_title": "Agenda tributária",
            "calendars": BusinessCalendarYear.objects.prefetch_related("days").select_related(
                "approved_by"
            ),
            "rules": TaxDeadlineRule.objects.select_related("approved_by"),
        }
    )
    return render(request, "platform/fiscal_calendar.html", ctx)
