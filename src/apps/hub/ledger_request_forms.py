"""Scoped customer inputs for monthly ledger collection and an optional bank file."""

from __future__ import annotations

import calendar
import re
from datetime import date
from typing import Any, cast
from uuid import UUID

from django import forms
from django.db.models import QuerySet

from apps.hub.forms import FinancialAccountSelect
from apps.hub.models import ClientCompany, FinancialAccount, ReconciliationSourceFile
from apps.hub.reconciliation_service import MAX_BYTES
from apps.organizations.models import Organization


class LedgerMonthField(forms.CharField):
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("max_length", 7)
        kwargs.setdefault(
            "widget", forms.DateInput(format="%Y-%m", attrs={"type": "month", "min": "2026-09"})
        )
        super().__init__(**kwargs)

    def clean(self, value: Any) -> date:
        text = super().clean(value)
        if not isinstance(text, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", text):
            raise forms.ValidationError("Informe a competência no formato AAAA-MM.")
        try:
            month = date.fromisoformat(text + "-01")
        except ValueError:
            raise forms.ValidationError("Escolha uma competência válida.") from None
        if month < date(2026, 9, 1):
            raise forms.ValidationError("Escolha setembro de 2026 ou uma competência posterior.")
        return month


class LedgerRequestForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=ClientCompany.objects.none(),
        label="Empresa",
        empty_label="Escolha a empresa…",
    )
    account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.none(),
        label="Conta",
        empty_label="Escolha a conta…",
        widget=FinancialAccountSelect(attrs={"data-ledger-account": ""}),
    )
    month = LedgerMonthField(label="Competência")
    bank_source = forms.ModelChoiceField(
        queryset=ReconciliationSourceFile.objects.none(),
        required=False,
        label="Extrato recebido",
        empty_label="Sem extrato selecionado",
    )
    statement = forms.FileField(
        label="Novo extrato",
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": ".ofx,.qfx,.csv,.xlsx,.pdf"}),
    )
    request_key = forms.UUIDField(widget=forms.HiddenInput)
    expected_mapping_revision = forms.CharField(
        widget=forms.HiddenInput, max_length=64, required=False
    )

    def __init__(
        self,
        *args: Any,
        organization: Organization,
        companies: QuerySet[ClientCompany],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        companies = companies.filter(organization=organization)
        cast("forms.ModelChoiceField[ClientCompany]", self.fields["company"]).queryset = companies
        values = self.data if self.is_bound else self.initial
        accounts = FinancialAccount.objects.select_related("company").filter(
            organization=organization,
            company__in=companies,
            active=True,
        )
        account_field = cast("forms.ModelChoiceField[FinancialAccount]", self.fields["account"])
        account_field.queryset = accounts.order_by("company__name", "name", "id")
        setattr(  # noqa: B010
            account_field,
            "label_from_instance",
            lambda item: f"{item.name} · {item.account_reference}",
        )
        sources = ReconciliationSourceFile.objects.none()
        if values.get("account"):
            try:
                identifier = UUID(str(values["account"]))
                sources = ReconciliationSourceFile.objects.filter(
                    organization=organization,
                    company__in=companies,
                    financial_account__in=accounts,
                    financial_account_id=identifier,
                    origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
                ).order_by("-created_at", "-id")
            except (ValueError, TypeError, AttributeError):
                pass
        source_field = cast(
            "forms.ModelChoiceField[ReconciliationSourceFile]",
            self.fields["bank_source"],
        )
        source_field.queryset = sources
        setattr(source_field, "label_from_instance", lambda item: item.original_filename)  # noqa: B010

    def clean_statement(self) -> Any:
        upload = self.cleaned_data.get("statement")
        if upload is None:
            return None
        if not upload.size or upload.size > MAX_BYTES:
            raise forms.ValidationError("Envie um arquivo com conteúdo e até 25 MiB.")
        if upload.name.rsplit(".", 1)[-1].casefold() not in {"ofx", "qfx", "csv", "xlsx", "pdf"}:
            raise forms.ValidationError("Use OFX, QFX, CSV, XLSX ou PDF.")
        return upload

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if hasattr(self.data, "getlist") and any(
            len(self.data.getlist(key)) > 1 for key in (*self.fields, "action")
        ):
            self.add_error(None, "Informe cada campo uma única vez.")
        if hasattr(self.files, "getlist") and len(self.files.getlist("statement")) > 1:
            self.add_error("statement", "Envie um extrato por vez nesta solicitação.")
        company, account = cleaned.get("company"), cleaned.get("account")
        if company and account and account.company_id != company.pk:
            self.add_error("account", "Escolha uma conta da empresa selecionada.")
        source = cleaned.get("bank_source")
        if (
            source
            and account
            and (
                source.financial_account_id != account.pk or source.company_id != account.company_id
            )
        ):
            self.add_error("bank_source", "Escolha um extrato da empresa e conta selecionadas.")
        if source and cleaned.get("statement"):
            self.add_error("statement", "Escolha um arquivo novo ou um extrato já recebido.")
        if cleaned.get("month"):
            month = cleaned["month"]
            cleaned["start"] = month
            cleaned["end"] = month.replace(day=calendar.monthrange(month.year, month.month)[1])
        return cleaned


class LedgerMappingForm(forms.Form):
    expected_revision = forms.CharField(widget=forms.HiddenInput, max_length=64, required=False)
    chart_company_code = forms.RegexField(r"^[0-9]{1,18}$", label="Empresa do plano", max_length=18)
    branch_code = forms.RegexField(r"^[0-9]{1,18}$", label="Filial", max_length=18)
    bank_inflow_side = forms.ChoiceField(
        label="Entrada no banco",
        choices=[("", "Escolha o sentido…"), ("debit", "Débito"), ("credit", "Crédito")],
    )
    evidence_reference = forms.CharField(
        label="Evidência do vínculo",
        max_length=240,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    confirmed = forms.BooleanField(label="Conferi os dados deste vínculo com a fonte.")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if hasattr(self.data, "getlist") and any(
            len(self.data.getlist(self.add_prefix(key))) > 1 for key in self.fields
        ):
            self.add_error(None, "Informe cada campo do vínculo uma única vez.")
        return cleaned
