from __future__ import annotations

from typing import Any

from django import forms

from apps.closing import engine
from apps.closing.models import ClosingField, ClosingLayout, Variable
from apps.hub.models import FiscalGuide
from apps.organizations.models import Organization

MARKER_CHOICES = [(f"{engine.MARKER_PREFIX}{n}", f"Identificador {n}") for n in range(2, 6)]
VARIABLE_CHOICES = [(v.value, v.label) for v in Variable] + MARKER_CHOICES


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": ".pdf,.xml,.txt"}))
        super().__init__(*args, **kwargs)

    def clean(self, data: Any, initial: Any = None) -> Any:
        single = super().clean
        if isinstance(data, list | tuple):
            return [single(item, initial) for item in data]
        return [single(data, initial)]


class UploadForm(forms.Form):
    documents = MultipleFileField(label="Arquivos")


class DecisionForm(forms.Form):
    reason = forms.CharField(
        label="Motivo", max_length=500, widget=forms.Textarea(attrs={"rows": 2})
    )


class LayoutForm(forms.ModelForm):  # type: ignore[type-arg]
    guide_kind = forms.ChoiceField(
        label="Tipo de guia", required=False, choices=[("", "—"), *FiscalGuide.Kind.choices]
    )

    class Meta:
        model = ClosingLayout
        fields = (
            "label",
            "code",
            "kind",
            "activity_code",
            "compare",
            "guide_kind",
            "paired_layout",
            "value_source",
            "tolerance",
            "zero_clears",
            "requires_human",
        )
        labels = {
            "label": "Nome",
            "code": "Código",
            "kind": "Documento",
            "activity_code": "Item do checklist",
            "compare": "Conferir com",
            "paired_layout": "Documento par",
            "value_source": "Valor conferido",
            "tolerance": "Tolerância (R$)",
            "zero_clears": "Zero baixa",
            "requires_human": "Exige pessoa",
        }

    def __init__(self, *args: Any, organization: Organization, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.organization = organization
        paired = self.fields["paired_layout"]
        paired.queryset = ClosingLayout.objects.filter(organization=organization).exclude(  # type: ignore[attr-defined]
            pk=self.instance.pk
        )
        paired.required = False
        if not self.instance._state.adding:
            self.fields["code"].disabled = True

    def clean_code(self) -> str:
        code: str = self.cleaned_data["code"]
        if (
            self.instance._state.adding
            and ClosingLayout.objects.filter(organization=self.organization, code=code).exists()
        ):
            raise forms.ValidationError("Já existe um layout com este código.")
        return code

    def clean(self) -> dict[str, Any]:
        data: dict[str, Any] = super().clean() or {}
        self.instance.organization = self.organization
        if data.get("compare") != ClosingLayout.Compare.FISCAL_GUIDE:
            data["guide_kind"] = ""
        if data.get("compare") != ClosingLayout.Compare.PAIRED:
            data["paired_layout"] = None
        return data


class FieldForm(forms.ModelForm):  # type: ignore[type-arg]
    variable = forms.ChoiceField(label="Campo", choices=VARIABLE_CHOICES)

    class Meta:
        model = ClosingField
        fields = ("variable", "anchor", "occurrence", "sum_count", "nullified")
        labels = {
            "anchor": "Texto de referência",
            "occurrence": "Ocorrência",
            "sum_count": "Somar",
            "nullified": "Sem valor",
        }

    def __init__(self, *args: Any, layout: ClosingLayout, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.layout = layout
        self.instance.layout = layout
        self.instance.organization = layout.organization

    def clean_variable(self) -> str:
        variable: str = self.cleaned_data["variable"]
        taken = ClosingField.objects.filter(layout=self.layout, variable=variable).exclude(
            pk=self.instance.pk
        )
        if taken.exists():
            raise forms.ValidationError("Este campo já existe no layout.")
        return variable


class SampleForm(forms.Form):
    sample = forms.FileField(label="Amostra", required=False)
    sample_text = forms.CharField(
        label="Texto da amostra", required=False, widget=forms.Textarea(attrs={"rows": 6})
    )
