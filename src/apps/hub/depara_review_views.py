"""Human review of already retained DE-PARA suggestions, without provider access."""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlencode

from django.contrib import messages
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.hub.depara_review_forms import DeparaChoiceForm, DeparaReviewForm
from apps.hub.models import ClientCompany, FinancialAccount, LedgerAccount
from apps.hub.setup_review import account_revision
from apps.hub.title_persistence import authorize_title_account
from apps.hub.title_ui import has_duplicate_fields, private_response, title_workspace
from apps.hub.views import office_required, refuse
from apps.intelligence.depara_ai import depara_review_packet, review_depara_ai
from apps.intelligence.models import DeparaAiBatch
from apps.intelligence.native_title_contract import canonical_hash

REVIEW_SALT = "hub.depara.retained-review.v1"
STATE_LABELS = {
    "succeeded": "Sugestões disponíveis",
    "prepared": "Sem resposta disponível",
    "calling": "Resposta em conferência",
    "unknown": "Resposta em conferência",
    "invalid": "Resposta incompatível",
}
RESULT_LABELS = {
    "draft": "Rascunho preparado",
    "preserved": "Rascunho anterior preservado",
    "invalid_accounts": "Confira as contas do plano",
    "insufficient": "Complete os dados",
    "conflict": "Conflito com outra regra; confira a configuração",
}


def _configuration(account: FinancialAccount, anchor: str = "plano-contas") -> str:
    return (
        reverse("hub:reconciliation-configuration")
        + "?"
        + urlencode(
            {
                "company": str(account.company_id),
            }
        )
        + "#"
        + anchor
    )


def _revision(batch: DeparaAiBatch, account: FinancialAccount, actor: User) -> str:
    chart = list(
        LedgerAccount.objects.filter(
            organization_id=account.organization_id,
            company_id=account.company_id,
        )
        .order_by("pk")
        .values(
            "id",
            "code",
            "name",
            "active",
            "accepts_entries",
            "updated_at",
        )
    )
    # Only a digest enters the signed browser token; private names stay server-side.
    return canonical_hash(
        {
            "batch": str(batch.pk),
            "actor": str(actor.pk),
            "account": account_revision(account),
            "fingerprint": batch.fingerprint,
            "context": batch.context,
            "suggestions": batch.suggestions,
            "state": batch.state,
            "updated_at": batch.updated_at.isoformat(),
            "chart": [{key: str(value) for key, value in row.items()} for row in chart],
        }
    )


def _packet_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    choices, items = packet["choices"], packet["context"]["items"]
    if not isinstance(choices, list) or len(choices) > 4 or not isinstance(items, list):
        raise ValueError("Sugestões incompatíveis; solicite conferência do lote.")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for choice in choices:
        reference = choice["reference"]
        if reference not in {f"item_{i}" for i in range(1, len(items) + 1)} or reference in seen:
            raise ValueError("Referência de sugestão incompatível; confira o lote.")
        seen.add(reference)
        item = items[int(reference.split("_")[1]) - 1]
        rows.append(
            {
                "reference": reference,
                "suggestion": choice,
                "description": item["description"],
                "direction": "Entrada" if item["direction"] == "inflow" else "Saída",
                "index": len(rows) + 1,
            }
        )
    return rows


def _ledger_links(
    context: dict[str, Any], account: FinancialAccount | None
) -> list[dict[str, Any]]:
    """D-391: bank accounts that have suggestions learned from the Razão."""
    from collections import Counter

    from apps.audit.models import AuditEvent
    from apps.hub.depara_ledger import SUGGESTED_ACTION

    if not context["title_can_write"]:
        return []
    counts = Counter(
        str(metadata.get("financial_account_id"))
        for metadata in AuditEvent.objects.filter(
            organization=context["office"], action=SUGGESTED_ACTION
        ).values_list("metadata", flat=True)
    )
    accounts = context["title_accounts"] if account is None else [account]
    return [
        {
            "account": item,
            "count": counts[str(item.pk)],
            "url": reverse("hub:reconciliation-depara-ledger", args=[item.pk]),
        }
        for item in accounts
        if counts.get(str(item.pk))
    ]


@office_required
@require_http_methods(["GET"])
def depara_batches(request: HttpRequest) -> HttpResponse:
    context, account = title_workspace(request)
    context.update(page_title="Revisar DE-PARA", depara_errors=[], depara_rows=[])
    status = 200
    try:
        if has_duplicate_fields(request.GET, ("account", "page")):
            raise ValueError("Informe cada filtro uma única vez.")
        page_number = request.GET.get("page", "1")
        if not page_number.isascii() or not page_number.isdecimal() or int(page_number) < 1:
            raise ValueError("Confira a página solicitada.")
        batches = (
            DeparaAiBatch.objects.filter(
                organization=context["office"],
                financial_account__in=context["title_accounts"],
            )
            .select_related("financial_account__company")
            .order_by("-created_at", "-pk")
        )
        if account:
            batches = batches.filter(financial_account=account)
        if not context["title_can_write"]:
            batches = batches.none()
        page = Paginator(batches, 25).page(int(page_number))
        for batch in page:
            authorize_title_account(batch.financial_account, cast(User, request.user))
            context["depara_rows"].append(
                {
                    "batch": batch,
                    "state_label": STATE_LABELS.get(batch.state, "Conferir lote"),
                    "url": reverse("hub:reconciliation-depara-batch", args=[batch.pk]),
                }
            )
        context["depara_page"] = page
        context["depara_ledger_links"] = _ledger_links(context, account)
        filters = {"account": str(account.pk)} if account else {}
        if company := context.get("title_company"):
            filters["company"] = str(company.pk)
        context["depara_querystring"] = urlencode(filters)
    except (ValueError, EmptyPage, PermissionDenied) as exc:
        context["depara_errors"] = [str(exc)]
        context["depara_rows"] = []
        status = 400
    return private_response(
        render(
            request,
            "hub/reconciliation_depara.html",
            context,
            status=status,
        )
    )


@office_required
@require_http_methods(["GET", "POST"])
def depara_batch(request: HttpRequest, batch_id: str) -> HttpResponse:
    context, selected = title_workspace(request)
    batches = DeparaAiBatch.objects.filter(
        organization=context["office"],
        financial_account__company__in=context["companies"],
    )
    if selected:
        batches = batches.filter(financial_account=selected)
    batch = get_object_or_404(batches, pk=batch_id)
    context, account = title_workspace(request, batch.financial_account_id)
    assert account is not None
    if not context["title_can_write"]:
        return private_response(
            refuse(
                request,
                "Um responsável autorizado pode revisar sugestões.",
            )
        )
    context.update(
        page_title="Revisar DE-PARA",
        depara_batch=batch,
        depara_errors=[],
        depara_choices=[],
        depara_chart_url=_configuration(account),
        depara_rules_url=_configuration(account, "regras-layouts"),
        depara_list_url=reverse("hub:reconciliation-depara")
        + "?"
        + urlencode(
            {
                "account": str(account.pk),
            }
        ),
    )
    status = 200
    try:
        if has_duplicate_fields(request.GET, ("account",)):
            raise ValueError("Informe a conta uma única vez.")
        packet = depara_review_packet(batch=batch, actor=cast(User, request.user))
        rows = _packet_rows(packet)
        accounts = list(
            LedgerAccount.objects.filter(
                organization=context["office"],
                company=account.company,
                active=True,
                accepts_entries=True,
            ).order_by("code")
        )
        codes = {row.code for row in accounts}
        ready = account.ledger_code in codes and len(codes) >= 2
        context["depara_chart_ready"] = ready
        context["depara_native_chart"] = packet["requires_chart_review"]
        token = signing.dumps(
            {"revision": _revision(batch, account, cast(User, request.user))},
            salt=REVIEW_SALT,
        )
        data = request.POST if request.method == "POST" else None
        form = DeparaReviewForm(data, initial={"expected_token": token})
        for index, row in enumerate(rows):
            row["form"] = DeparaChoiceForm(
                data,
                prefix=f"choice-{index}",
                accounts=accounts,
                suggestion=row["suggestion"],
                bank_code=account.ledger_code,
            )
        context.update(depara_form=form, depara_choices=rows)
        if request.method == "POST":
            valid = form.is_valid()
            for row in rows:
                valid = row["form"].is_valid() and valid
            names = [*form.fields, "action"] + [
                row["form"].add_prefix(name) for row in rows for name in row["form"].fields
            ]
            if has_duplicate_fields(request.POST, request.POST) or set(request.POST) - {
                *names,
                "csrfmiddlewaretoken",
            }:
                form.add_error(None, "Há campos repetidos ou incompatíveis. Reabra o lote.")
                valid = False
            if request.POST.get("action") != "review":
                form.add_error(None, "Ação de revisão inválida.")
                valid = False
            choices = [
                {
                    "reference": row["reference"],
                    **{
                        key: row["form"].cleaned_data.get(key, "")
                        for key in ("debit", "credit", "history")
                    },
                }
                for row in rows
                if row["form"].cleaned_data.get("selected")
            ]
            if not choices:
                form.add_error(None, "Selecione ao menos uma sugestão após conferir os dados.")
                valid = False
            if not ready:
                form.add_error(None, "Confira as contas do plano antes de preparar regras.")
                valid = False
            if valid:
                try:
                    signed = signing.loads(
                        form.cleaned_data["expected_token"],
                        salt=REVIEW_SALT,
                        max_age=3600,
                    )
                    with transaction.atomic():
                        ClientCompany.objects.select_for_update().get(
                            pk=account.company_id,
                            organization=context["office"],
                        )
                        current = DeparaAiBatch.objects.select_for_update().get(pk=batch.pk)
                        current_account = FinancialAccount.objects.select_for_update().get(
                            pk=account.pk,
                            organization=context["office"],
                        )
                        if signed != {
                            "revision": _revision(
                                current,
                                current_account,
                                cast(User, request.user),
                            )
                        }:
                            raise signing.BadSignature
                        results = review_depara_ai(
                            batch=current,
                            actor=cast(User, request.user),
                            choices=choices,
                        )
                    context["depara_results"] = [
                        {
                            "label": RESULT_LABELS.get(result.status, "Confira a revisão"),
                            "rule_id": result.rule_id,
                        }
                        for result in results
                    ]
                    if any(result.status == "draft" for result in results):
                        messages.success(request, "Rascunhos preparados para revisão e ativação.")
                except signing.BadSignature:
                    form.add_error(
                        None,
                        "A revisão mudou ou expirou. Atualize e confira novamente.",
                    )
                    status = 409
                except (ValueError, PermissionDenied) as exc:
                    form.add_error(None, str(exc))
                    status = 400 if isinstance(exc, ValueError) else 403
            else:
                status = 400
    except (ValueError, TypeError, KeyError) as exc:
        context["depara_errors"] = [
            str(exc)
            if isinstance(exc, ValueError)
            else ("Dados do lote incompatíveis; solicite conferência antes de preparar regras.")
        ]
        status = 400
    except PermissionDenied:
        raise Http404 from None
    return private_response(
        render(
            request,
            "hub/reconciliation_depara.html",
            context,
            status=status,
        )
    )
