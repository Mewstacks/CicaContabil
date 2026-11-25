"""Tela “Fechamento do mês (simulação)” — D-413, PC-33.

Recebe as fontes do mês, roda a simulação multifontes na própria requisição e mostra o resultado.
Nada é gravado: os arquivos são lidos e descartados; não há lançamento, regra nem exportação.
"""

from __future__ import annotations

import io
import re
import zipfile
from collections import Counter
from typing import Any, cast

from django import forms
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.multisource.common import MAX_SOURCE_BYTES, MultisourceError, money
from apps.hub.multisource.matching import AUTOMATIC, FLAGGED, IDENTIFIED, STATUS_LABELS
from apps.hub.multisource.service import SimulationOutput, SimulationSources, run_simulation
from apps.hub.title_ui import private_response
from apps.hub.views import _can_manage_reconciliation, _module_page_context, office_required
from apps.organizations.models import Organization

FILE_FIELDS = {
    "statement": (".pdf", "Extrato bancário Sicredi (PDF)"),
    "collection": (".pdf", "Francesinha Sicredi (PDF)"),
    "investment": (".pdf", "Extrato da aplicação Sicredi (PDF)"),
    "receivables": (".xls", "Contas a receber do mês anterior (.xls do Domínio)"),
    "payables": (".xls", "Contas a pagar do mês anterior (.xls do Domínio)"),
    "reference_receivables": (".xls", "Contas a receber do próprio mês (para comparar)"),
    "reference_payables": (".xls", "Contas a pagar do próprio mês (para comparar)"),
    "cashbook": (".xlsx", "Caixa do cliente (.xlsx)"),
    "ledger": (".pdf,.csv", "Razão da conta bancária (PDF do Domínio ou CSV)"),
}


class MultisourceCloseForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=ClientCompany.objects.none(), label="Empresa", empty_label="Escolha a empresa"
    )
    statement = forms.FileField(label=FILE_FIELDS["statement"][1])
    collection = forms.FileField(label=FILE_FIELDS["collection"][1], required=False)
    investment = forms.FileField(label=FILE_FIELDS["investment"][1], required=False)
    receivables = forms.FileField(label=FILE_FIELDS["receivables"][1], required=False)
    payables = forms.FileField(label=FILE_FIELDS["payables"][1], required=False)
    reference_receivables = forms.FileField(
        label=FILE_FIELDS["reference_receivables"][1], required=False
    )
    reference_payables = forms.FileField(label=FILE_FIELDS["reference_payables"][1], required=False)
    cashbook = forms.FileField(label=FILE_FIELDS["cashbook"][1], required=False)
    cashbook_sheet = forms.CharField(
        label="Aba do caixa que corresponde ao extrato",
        initial="SICREDI",
        max_length=60,
        required=False,
    )
    cash_sheets = forms.CharField(
        label="Abas do caixa sem extrato (separe por vírgula)",
        help_text="Ex.: CAIXA, CEF — dinheiro em espécie e contas sem extrato enviado.",
        max_length=200,
        required=False,
    )
    ledger = forms.FileField(label=FILE_FIELDS["ledger"][1], required=False)

    def __init__(self, *args: Any, companies: Any, **kwargs: Any) -> None:
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        field = cast(forms.ModelChoiceField, self.fields["company"])  # type: ignore[type-arg]
        field.queryset = companies
        for name, (accept, _label) in FILE_FIELDS.items():
            self.fields[name].widget.attrs["accept"] = accept

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        for name, (accept, label) in FILE_FIELDS.items():
            upload = cleaned.get(name)
            if not upload:
                continue
            suffixes = tuple(accept.split(","))
            if not str(upload.name).lower().endswith(suffixes):
                self.add_error(name, f"Envie {label.lower()} no formato {accept}.")
            elif upload.size > MAX_SOURCE_BYTES:
                self.add_error(name, "Arquivo maior que 25 MiB.")
        if cleaned.get("cash_sheets") and not cleaned.get("cashbook"):
            self.add_error("cash_sheets", "Envie o caixa do cliente para usar as abas sem extrato.")
        return cleaned


def _workspace(request: HttpRequest, *, write: bool) -> dict[str, Any]:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        raise Http404
    writable = bool(
        context["support_can_mutate"]
        and _can_manage_reconciliation(context)
        and not cast(Organization, context["office"]).is_demo
    )
    if write and not writable:
        raise PermissionDenied("Seu acesso atual não permite enviar arquivos da conciliação.")
    context.update(
        page_title="Fechamento do mês (simulação)",
        multisource_can_write=writable,
        multisource_url=reverse("hub:reconciliation-multisource"),
        multisource_back_url=reverse("hub:reconciliation"),
    )
    return context


def _read(upload: UploadedFile | None) -> bytes | None:
    if not upload:
        return None
    return b"".join(upload.chunks())


def _sheets(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;]", text or "") if part.strip()]


def _tax_id(company: ClientCompany) -> str:
    digits = re.sub(r"\D", "", company.cnpj_masked or "")
    return digits if len(digits) == 14 else ""


def _sources(form: MultisourceCloseForm) -> SimulationSources:
    data = form.cleaned_data
    ledger = data.get("ledger")
    ledger_bytes = _read(ledger)
    is_csv = bool(ledger) and str(ledger.name).lower().endswith(".csv")
    statement = _read(data["statement"])
    assert statement is not None
    return SimulationSources(
        statement=statement,
        collection=_read(data.get("collection")),
        receivables=_read(data.get("receivables")),
        payables=_read(data.get("payables")),
        cashbook=_read(data.get("cashbook")),
        cashbook_sheet=(data.get("cashbook_sheet") or "SICREDI").strip(),
        cash_sheets=_sheets(data.get("cash_sheets", "")),
        reference_receivables=_read(data.get("reference_receivables")),
        reference_payables=_read(data.get("reference_payables")),
        investment=_read(data.get("investment")),
        ledger_pdf=None if is_csv else ledger_bytes,
        ledger_csv=ledger_bytes if is_csv else None,
        tax_id=_tax_id(data["company"]),
    )


def _view_model(output: SimulationOutput) -> dict[str, Any]:
    result = output.result
    total = len(result.lines)
    statuses = []
    for status, tone in (
        (AUTOMATIC, "is-active"),
        (IDENTIFIED, "is-muted"),
        (FLAGGED, "is-warning"),
    ):
        chosen = [r for r in result.lines if r.status == status]
        statuses.append(
            {
                "label": STATUS_LABELS[status],
                "count": len(chosen),
                "share": f"{(len(chosen) / total * 100 if total else 0):.1f}".replace(".", ","),
                "amount": money(sum(abs(r.bank.amount_cents) for r in chosen)),
                "tone": tone,
            }
        )
    flagged = [
        {
            "account": r.bank.account,
            "date": r.bank.occurred_on,
            "amount": money(r.bank.amount_cents),
            "description": r.bank.description,
            "reasons": r.reasons,
        }
        for r in result.lines
        if r.status == FLAGGED
    ]
    parts = Counter(p.kind for r in result.lines for p in r.parts)
    positions = []
    for kind, label in (("receivable", "A receber"), ("payable", "A pagar")):
        keys = [k for k in result.installments if k[0] == kind]
        if keys:
            opening = sum(result.installments[k].balance_cents for k in keys)
            closing = sum(result.closing[k] for k in keys)
            positions.append(
                {
                    "label": label,
                    "opening": money(opening),
                    "settled": money(opening - closing),
                    "closing": money(closing),
                }
            )
    differences = Counter((d.kind, d.outcome) for d in result.differences)
    investment = None
    if result.investment:
        statement = result.investment
        investment = {
            "opening": money(statement.opening_cents),
            "closing": money(statement.closing_cents),
            "income": money(statement.total("income")),
            "income_tax": money(statement.total("income_tax")),
            "matched": sum(1 for r in result.lines for p in r.parts if p.kind == "investment"),
            "unmatched": [
                f"{m.occurred_on:%d/%m/%Y} {'aplicação' if m.kind == 'application' else 'resgate'} "
                f"{money(m.amount_cents)}"
                for m in result.investment_unmatched
            ],
        }
    comparison = None
    if output.comparison:
        from apps.hub.multisource.ledger_comparison import MISSING, OTHER_SPLIT, SAME_SPLIT

        comparison = {
            "rows": [
                (label, output.comparison.count(label))
                for label in (SAME_SPLIT, OTHER_SPLIT, MISSING)
            ],
            "only_ledger": len(output.comparison.only_ledger),
            "accounts": [
                (group, ", ".join(f"{code} ({n})" for code, n in counter.most_common(5)))
                for group, counter in sorted(output.comparison.accounts.items())
            ],
        }
    return {
        "period": output.period_label,
        "total": total,
        "statuses": statuses,
        "flagged": flagged,
        "parts": {
            "receivable": parts.get("receivable", 0),
            "payable": parts.get("payable", 0),
            "interest": parts.get("interest", 0),
            "document": parts.get("document", 0),
            "nature": parts.get("nature", 0),
            "investment": parts.get("investment", 0),
            "transfer": parts.get("transfer", 0),
        },
        "unmatched_cashbook": len(result.unmatched_cashbook),
        "positions": positions,
        "differences": [
            {"kind": "A receber" if kind == "receivable" else "A pagar", "outcome": o, "count": n}
            for (kind, o), n in sorted(differences.items())
        ],
        "investment": investment,
        "comparison": comparison,
        "warnings": result.warnings,
    }


def _zip(output: SimulationOutput) -> HttpResponse:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in output.reports.items():
            archive.writestr(name, text.encode("utf-8"))
    period = output.period_start.strftime("%Y-%m")
    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="simulacao-multifontes-{period}.zip"'
    return private_response(response)


@office_required
@require_http_methods(["GET", "POST"])
def multisource_close(request: HttpRequest) -> HttpResponse:
    context = _workspace(request, write=request.method == "POST")
    form = MultisourceCloseForm(
        request.POST or None, request.FILES or None, companies=context["companies"]
    )
    context["multisource_form"] = form
    status = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                output = run_simulation(_sources(form))
            except MultisourceError as exc:
                form.add_error(None, str(exc))
                status = 400
            else:
                if request.POST.get("action") == "zip":
                    return _zip(output)
                context["multisource"] = _view_model(output)
                context["multisource_company"] = form.cleaned_data["company"]
        else:
            status = 400
    return private_response(
        render(request, "hub/reconciliation_multisource.html", context, status=status)
    )
