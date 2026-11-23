"""Explicit financial choices, derived dates and identities stay outside user input."""

from __future__ import annotations

from typing import Any

from django import forms

from apps.hub.title_forms import BRLCentsField


class NativeTitleReviewForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput, max_length=4000)
    kind = forms.ChoiceField(
        label="Natureza do título",
        choices=[("", "Selecione"), ("payable", "A pagar"), ("receivable", "A receber")],
    )
    principal_field = forms.ChoiceField(label="Campo da fonte que representa o principal")
    evidence_reference = forms.CharField(
        label="Referência da conferência",
        max_length=240,
        help_text="Identifique o documento ou a consulta usados para conferir estas decisões.",
    )
    source_confirmed = forms.BooleanField(
        label="Conferi a natureza, o principal e todos os componentes desta parcela nas fontes."
    )
    grouping_confirmed = forms.BooleanField(
        label="Cada grupo de mesma data e número abaixo representa um único evento de baixa.",
        help_text="Se um grupo precisar ser dividido em eventos distintos, interrompa esta revisão "
        "e solicite revisão assistida. Nenhum componente pode ser omitido.",
    )
    limits_confirmed = forms.BooleanField(
        label="Entendi que o saldo continua não informado e que revisar a fonte não vincula "
        "a baixa ao banco nem comprova quitação."
    )

    def __init__(self, *args: Any, installment: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["principal_field"].choices = [  # type: ignore[attr-defined]
            ("", "Selecione o campo conferido"),
            *installment["principal_choices"],
        ]
        if not installment["events"]:
            self.fields.pop("grouping_confirmed")


class NativeSettlementForm(forms.Form):
    principal = forms.DecimalField(label="Principal (R$)")
    interest = forms.DecimalField(label="Juros (R$)")
    penalty = forms.DecimalField(label="Multa (R$)")
    fees = forms.DecimalField(label="Tarifas (R$)")
    discount = forms.DecimalField(label="Desconto (R$)")
    cash = forms.DecimalField(label="Caixa efetivo (R$)")
    direction = forms.ChoiceField(
        label="Sentido do caixa",
        choices=[("", "Selecione"), ("inflow", "Entrada"), ("outflow", "Saída")],
    )
    reverses = forms.ChoiceField(label="Este evento é um estorno?")

    def __init__(self, *args: Any, events: list[dict[str, Any]], index: int, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for name in ("principal", "interest", "penalty", "fees", "discount", "cash"):
            self.fields[name] = BRLCentsField(
                label=self.fields[name].label,
                allow_zero=name != "cash",
                help_text="Informe 0 quando não houver este componente." if name != "cash" else "",
            )
        self.fields["reverses"].choices = [  # type: ignore[attr-defined]
            ("", "Selecione"),
            ("none", "Não é estorno"),
            *[
                (event["key"], f"Estorno integral do evento {number + 1} — {event['posted_on']}")
                for number, event in enumerate(events)
                if number != index
            ],
        ]


def financial_review(
    *,
    source_hash: str,
    installment: dict[str, Any],
    form: NativeTitleReviewForm,
    events: list[NativeSettlementForm],
) -> dict[str, Any]:
    """Called only after every form is valid; server derives source grouping and dates."""
    settlements = []
    for event, form_event in zip(installment["events"], events, strict=True):
        clean = form_event.cleaned_data
        settlements.append(
            {
                "payment_references": event["references"],
                "normalized": {
                    "key": event["key"],
                    "posted_on": event["posted_on"],
                    **{
                        f"{name}_cents": clean[name]
                        for name in ("principal", "interest", "penalty", "fees", "discount", "cash")
                    },
                    "direction": clean["direction"],
                    "reverses": None if clean["reverses"] == "none" else clean["reverses"],
                },
            }
        )
    return {
        "source_sha256": source_hash,
        "evidence_reference": form.cleaned_data["evidence_reference"],
        "decisions": [
            {
                "family": installment["family"],
                "installment_reference": installment["reference"],
                "kind": form.cleaned_data["kind"],
                "principal_field": form.cleaned_data["principal_field"],
                "settlements": settlements,
            }
        ],
    }
