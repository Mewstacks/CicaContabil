"""Private source → explicit human preview → cumulative reviewed titles."""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlencode
from uuid import UUID

from django.contrib import messages
from django.core.paginator import EmptyPage, Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.hub.native_title_forms import (
    NativeSettlementForm,
    NativeTitleReviewForm,
    financial_review,
)
from apps.hub.title_ui import brl, has_duplicate_fields, private_response, title_workspace
from apps.hub.views import office_required
from apps.intelligence.models import NativeTitleCollection
from apps.intelligence.native_title_review import (
    NativeReviewConflict,
    confirm_native_review,
    installment_context,
    load_native_source,
    preview_native_review,
    review_token,
    source_installments,
)


def _catalog_url(account: Any, scope: dict[str, Any] | None = None) -> str:
    values = {"company": str(account.company_id), "account": str(account.pk)}
    if scope:
        from datetime import date, timedelta

        values.update(
            start=scope["period_start"],
            end=(date.fromisoformat(scope["period_end_exclusive"]) - timedelta(days=1)).isoformat(),
        )
    return reverse("hub:reconciliation-titles") + "?" + urlencode(values)


@office_required
@require_http_methods(["GET"])
def native_titles(request: HttpRequest, account_id: UUID) -> HttpResponse:
    from apps.hub.title_requests import captures_for_account

    context, account = title_workspace(request, account_id, write=True)
    assert account is not None
    context.update(
        page_title=(
            "Fontes de títulos" if context.get("office_direct_use") else "Revisar fontes de títulos"
        ),
        native_catalog_url=_catalog_url(account),
    )
    captures = captures_for_account(account)
    context["native_captures"] = captures
    context["native_list_url"] = reverse("hub:reconciliation-native-titles", args=[account.pk])
    status = 200
    try:
        if has_duplicate_fields(request.GET, ("capture", "page")):
            raise ValueError("Informe cada filtro uma única vez.")
        selected_id = request.GET.get("capture")
        if selected_id is None and captures:
            selected_id = str(captures[0].pk)
        page_text = request.GET.get("page", "1")
        if not page_text.isascii() or not page_text.isdecimal() or not 1 <= len(page_text) <= 8:
            raise ValueError("Escolha uma página válida.")
        if selected_id:
            try:
                capture_id = UUID(selected_id)
            except (ValueError, TypeError):
                raise ValueError("Escolha uma fonte disponível para esta conta.") from None
            source = load_native_source(
                account=account, capture_id=capture_id, actor=cast(User, request.user)
            )
            rows = source_installments(source)
            page = Paginator(rows, 25).page(int(page_text))
            for row in page.object_list:
                row["url"] = reverse(
                    "hub:reconciliation-native-title-review",
                    args=[account.pk, source.capture.pk, row["reference"]],
                )
            context.update(
                native_source=source, native_page=page, native_capture_id=str(source.capture.pk)
            )
    except EmptyPage:
        context["native_error"] = "Esta página não está disponível. Volte à primeira página."
        status = 400
    except ValueError as exc:
        context["native_error"] = str(exc)
        status = 400
    return private_response(
        render(request, "hub/reconciliation_native_titles.html", context, status=status)
    )


@office_required
@require_http_methods(["GET", "POST"])
def native_title_review(
    request: HttpRequest, account_id: UUID, capture_id: UUID, installment_reference: str
) -> HttpResponse:
    context, account = title_workspace(request, account_id, write=True)
    assert account is not None
    actor = cast(User, request.user)
    if context.get("office_direct_use"):
        # D-397: in direct use the CICA interprets every installment (D-394); a manual review
        # would be replaced by the next automatic reading, so it is not offered.
        return redirect(
            reverse("hub:reconciliation-native-titles", args=[account.pk])
            + "?"
            + urlencode({"capture": str(capture_id)})
        )
    back = (
        reverse("hub:reconciliation-native-titles", args=[account.pk])
        + "?"
        + urlencode({"capture": str(capture_id)})
    )
    context.update(
        page_title="Revisar parcela da fonte", native_back_url=back,
        native_company_source_url=reverse("hub:reconciliation-title-source", args=[capture_id])
        + "?" + urlencode({"account": str(account.pk)}),
    )
    try:
        source = load_native_source(account=account, capture_id=capture_id, actor=actor)
        part = installment_context(source, installment_reference)
        token = (
            review_token(source, installment_reference, actor) if request.method == "GET" else ""
        )
    except NativeTitleCollection.DoesNotExist:
        raise Http404 from None
    except ValueError as exc:
        context["native_error"] = str(exc)
        return private_response(
            render(request, "hub/reconciliation_native_title_review.html", context, status=409)
        )
    bound = request.POST if request.method == "POST" else None
    form = NativeTitleReviewForm(bound, installment=part, initial={"token": token}, prefix="review")
    event_forms = [
        NativeSettlementForm(bound, events=part["events"], index=i, prefix=f"event-{i}")
        for i in range(len(part["events"]))
    ]
    status = 200
    preview = None
    if bound is not None:
        names = {"csrfmiddlewaretoken", "action", "confirmation_token", "publication_confirmed"}
        names.update(form.add_prefix(name) for name in form.fields)
        for event_form in event_forms:
            names.update(event_form.add_prefix(name) for name in event_form.fields)
        valid = form.is_valid()
        valid_events = [event_form.is_valid() for event_form in event_forms]
        if has_duplicate_fields(bound, bound.keys()) or set(bound) - names:
            form.add_error(None, "Há campos repetidos ou incompatíveis. Reabra esta parcela.")
            valid = False
        if valid and all(valid_events):
            review = financial_review(
                source_hash=source.evidence.expected_sha256,
                installment=part,
                form=form,
                events=event_forms,
            )
            try:
                if bound.get("action") == "confirm":
                    if bound.get("publication_confirmed") != "on":
                        raise ValueError("Confirme que revisou a prévia antes de salvar a parcela.")
                    _snapshot, created = confirm_native_review(
                        account=account,
                        capture_id=capture_id,
                        actor=actor,
                        reference=installment_reference,
                        review=review,
                        confirmation_token=bound.get("confirmation_token", ""),
                        request=request,
                    )
                    messages.success(
                        request,
                        "Parcela revisada salva; as demais parcelas foram preservadas."
                        if created
                        else "Esta revisão já está salva.",
                    )
                    return private_response(redirect(_catalog_url(account, source.evidence.scope)))
                if bound.get("action") != "preview":
                    raise ValueError("Escolha a ação de revisar a prévia.")
                preview = preview_native_review(
                    source=source,
                    actor=actor,
                    reference=installment_reference,
                    review=review,
                    token=form.cleaned_data["token"],
                )
                preview["principal_display"] = brl(preview["installment"]["principal_cents"])
                for event in preview["installment"]["settlements"]:
                    event["amounts"] = [
                        (label, brl(event[f"{key}_cents"]))
                        for key, label in (
                            ("principal", "Principal"),
                            ("interest", "Juros"),
                            ("penalty", "Multa"),
                            ("fees", "Tarifas"),
                            ("discount", "Desconto"),
                            ("cash", "Caixa efetivo"),
                        )
                    ]
            except NativeReviewConflict as exc:
                form.add_error(None, str(exc))
                status = 409
            except ValueError as exc:
                form.add_error(None, str(exc))
                status = 400
        else:
            status = 400
    context.update(
        native_source=source,
        native_part=part,
        native_form=form,
        native_events=list(zip(part["events"], event_forms, strict=True)),
        native_preview=preview,
        native_review_url=reverse(
            "hub:reconciliation-native-title-review",
            args=[account.pk, capture_id, installment_reference],
        ),
        native_catalog_url=_catalog_url(account, source.evidence.scope),
    )
    return private_response(
        render(request, "hub/reconciliation_native_title_review.html", context, status=status)
    )
