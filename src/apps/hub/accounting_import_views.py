"""Scoped, paginated recording of the observed ERP import receipt."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from pathlib import PurePath
from typing import Any, cast
from uuid import uuid4

from django.contrib import messages
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Prefetch, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.hub.accounting_import import (
    ImportReceiptConflict,
    ImportReceiptError,
    import_receipt_context,
    record_import_receipt,
    verify_import_receipt,
)
from apps.hub.accounting_import_forms import ImportReceiptForm, ImportReceiptItemForm
from apps.hub.models import (
    AccountingExport,
    ClientCompany,
    JournalEntry,
    JournalLine,
    ProductModule,
)
from apps.hub.module_catalog import definition
from apps.hub.views import _can_manage_reconciliation, _module_page_context, office_required, refuse

OUTCOME_LABELS = {
    "not_recorded": "Resultado ainda não registrado",
    "accepted": "Importação integral conferida",
    "partial": "Importação parcial",
    "rejected": "Importação rejeitada",
    "uncertain": "Resultado incerto",
}
ITEM_LABELS = {"accepted": "Aceito", "rejected": "Rejeitado", "uncertain": "Incerto"}


def _page_number(request: HttpRequest, name: str) -> int:
    values = request.GET.getlist(name)
    if not values:
        return 1
    if len(values) != 1 or not values[0].isascii() or not values[0].isdigit():
        raise ValueError("Página inválida. Volte à primeira página da conferência.")
    number = int(values[0])
    if not 1 <= number <= 100_000:
        raise ValueError("Página inválida. Volte à primeira página da conferência.")
    return number


def _uncertain(identifier: str) -> dict[str, str]:
    return {
        "entry_id": identifier,
        "status": "uncertain",
        "erp_reference": "",
        "evidence_reference": "",
    }


@office_required
@require_http_methods(["GET", "POST"])
def import_receipt(request: HttpRequest, export_id: str) -> HttpResponse:
    page_context, blocked = _module_page_context(
        request, definition(ProductModule.Code.RECONCILIATION)
    )
    if blocked:
        return blocked
    context = cast(dict[str, Any], page_context)
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    export = get_object_or_404(
        AccountingExport.objects.select_related("company"),
        pk=export_id,
        organization=context["office"],
        company__in=companies,
        state__in=[AccountingExport.State.READY, AccountingExport.State.CONFIRMED],
    )
    can_manage = bool(context["support_can_mutate"] and _can_manage_reconciliation(context))
    if request.method == "POST" and not can_manage:
        return refuse(
            request, "Seu perfil pode consultar, mas não registrar resultados de importação."
        )
    actor = cast(User, request.user)
    try:
        result = import_receipt_context(export=export, actor=actor)
    except ImportReceiptError as exc:
        return refuse(request, str(exc))
    original = result["original"]
    identifiers = original.entry_ids
    if not isinstance(identifiers, list) or not identifiers or len(identifiers) > 100_000:
        return refuse(
            request, "O arquivo não possui uma lista válida de lançamentos para conferir."
        )
    detail_url = reverse("hub:reconciliation-import-receipt", args=[export.pk])
    errors: list[str] = []
    response_status = 200
    try:
        page = Paginator(identifiers, 25).page(_page_number(request, "page"))
        history_page = Paginator(
            original.import_receipts.select_related("created_by").defer("items"),
            10,
        ).page(_page_number(request, "history_page"))
    except (ValueError, EmptyPage) as exc:
        errors.append(
            str(exc) if isinstance(exc, ValueError) else "Esta página não está disponível."
        )
        page = Paginator([], 25).page(1)
        history_page = Paginator([], 10).page(1)
        response_status = 400
    try:
        for historical in history_page.object_list:
            verify_import_receipt(receipt=historical, export=original)
            # The history needs metadata only; release the cumulative item snapshot.
            historical.__dict__.pop("items", None)
    except ImportReceiptError:
        errors.append(
            "Um recibo deste histórico precisa de revisão de integridade. "
            "As evidências desta página do histórico não foram exibidas."
        )
        history_page = Paginator([], 10).page(1)
        response_status = 409
    form = ImportReceiptForm(
        request.POST if request.method == "POST" else None,
        initial={
            "request_key": uuid4(),
            "content_hash": original.content_hash,
            "expected_previous_id": result["expected_previous_id"],
            "importer_version": result["importer_version"],
        },
    )
    base_items = result["items"] or [_uncertain(identifier) for identifier in identifiers]
    form_valid = False
    if request.method == "POST" and not errors:
        form_valid = form.is_valid()
        if form_valid:
            previous_id = form.cleaned_data["expected_previous_id"]
            if previous_id:
                prior = original.import_receipts.filter(pk=previous_id).first()
                if prior is None:
                    errors.append(
                        "O recibo anterior não pertence a este arquivo. Reabra a conferência."
                    )
                    response_status = 409
                else:
                    try:
                        verify_import_receipt(receipt=prior, export=original)
                    except ImportReceiptError:
                        errors.append(
                            "O recibo anterior precisa de revisão de integridade. "
                            "Reabra a conferência atual."
                        )
                        response_status = 409
                    else:
                        base_items = prior.items
            else:
                base_items = [_uncertain(identifier) for identifier in identifiers]
    by_id = {item["entry_id"]: item for item in base_items}
    entries = {
        str(entry.pk): entry
        for entry in JournalEntry.objects.filter(
            pk__in=page.object_list,
            organization=context["office"],
            company=export.company,
        ).prefetch_related(
            Prefetch(
                "lines",
                queryset=JournalLine.objects.filter(organization=context["office"]).order_by(
                    "side", "account_code", "id"
                ),
            )
        )
    }
    rows = []
    item_forms = []
    for identifier in page.object_list:
        item = by_id.get(identifier, _uncertain(identifier))
        entry = entries.get(identifier)
        lines = list(entry.lines.all()) if entry else []
        if entry is None:
            errors.append(
                "Um lançamento deste arquivo está indisponível. Solicite conferência técnica."
            )
            response_status = 409
        accepted = item["status"] == "accepted"
        item_form = (
            None
            if accepted
            else ImportReceiptItemForm(
                request.POST if request.method == "POST" else None,
                prefix=f"entry-{identifier}",
                initial=item,
            )
        )
        if item_form:
            item_forms.append((identifier, item_form))
        elif request.method == "POST" and any(
            key.startswith(f"entry-{identifier}-") for key in request.POST
        ):
            errors.append("Preserve a identificação e a evidência dos lançamentos já aceitos.")
            response_status = 409
        rows.append(
            {
                "identifier": identifier,
                "entry": entry,
                "amount_brl": Decimal(
                    sum(line.amount_cents for line in lines if line.side == JournalLine.Side.DEBIT)
                )
                / 100,
                "debits": [
                    {"account": line.account_code, "amount_brl": Decimal(line.amount_cents) / 100}
                    for line in lines
                    if line.side == JournalLine.Side.DEBIT
                ],
                "credits": [
                    {"account": line.account_code, "amount_brl": Decimal(line.amount_cents) / 100}
                    for line in lines
                    if line.side == JournalLine.Side.CREDIT
                ],
                "item": item,
                "status_label": ITEM_LABELS.get(item["status"], "Incerto"),
                "accepted": accepted,
                "form": item_form,
            }
        )
    if request.method == "POST" and not errors:
        duplicate_fields = any(len(request.POST.getlist(key)) != 1 for key in request.POST)
        valid_items = all([item_form.is_valid() for _, item_form in item_forms])
        if duplicate_fields:
            form.add_error(None, "Envie cada campo uma única vez. Reabra a conferência.")
        if form_valid and valid_items and not duplicate_fields:
            for identifier, item_form in item_forms:
                by_id[identifier] = {"entry_id": identifier, **item_form.cleaned_data}
            try:
                _, created = record_import_receipt(
                    export=export,
                    actor=actor,
                    request_key=form.cleaned_data["request_key"],
                    content_hash=form.cleaned_data["content_hash"],
                    items=[by_id[identifier] for identifier in identifiers],
                    evidence_reference=form.cleaned_data["evidence_reference"],
                    importer_version=form.cleaned_data["importer_version"],
                    review_confirmed=form.cleaned_data["review_confirmed"],
                    expected_previous_id=form.cleaned_data["expected_previous_id"],
                    request=request,
                )
            except ImportReceiptConflict as exc:
                form.add_error(None, str(exc))
                response_status = 409
            except ImportReceiptError as exc:
                form.add_error(None, str(exc))
                response_status = 400
            else:
                messages.success(
                    request,
                    "Resultado desta página registrado."
                    if created
                    else "Este resultado já estava registrado.",
                )
                return redirect(f"{detail_url}?page={page.number}")
        else:
            response_status = 400
    counts = Counter(
        item["status"]
        for item in (result["items"] or [_uncertain(identifier) for identifier in identifiers])
    )
    context.update(
        page_title="Conferir importação",
        import_export=export,
        import_original=original,
        import_filename=PurePath(export.content.name or "arquivo-contabil").name,
        import_context=result,
        import_outcome_label=OUTCOME_LABELS.get(result["outcome"], "Resultado incerto"),
        import_rows=rows,
        import_page=page,
        import_history_page=history_page,
        import_errors=errors,
        import_form=form,
        import_detail_url=detail_url,
        import_can_record=can_manage
        and result["homologated"]
        and original.state == "ready"
        and not errors,
        import_can_manage=can_manage,
        import_counts={
            "accepted": counts["accepted"],
            "rejected": counts["rejected"],
            "uncertain": counts["uncertain"],
            "total": len(identifiers),
        },
        import_has_errors=bool(
            errors or form.errors or any(item_form.errors for _, item_form in item_forms)
        ),
    )
    response = render(
        request, "hub/reconciliation_import_receipt.html", context, status=response_status
    )
    response["Cache-Control"] = "no-store, private"
    response["X-Content-Type-Options"] = "nosniff"
    return response
