from typing import Any

from django import forms

from apps.intelligence.models import AnswerFeedback


class MultipleUploadInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleUploadField(forms.FileField):
    def clean(self, data: Any, initial: Any = None) -> list[Any]:
        if not data:
            return []
        values = data if isinstance(data, (list, tuple)) else [data]
        return [forms.FileField.clean(self, value, initial) for value in values]


class AssistantQuestionForm(forms.Form):
    question = forms.CharField(
        label="Pergunta",
        max_length=2_000,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Ex.: quais pendências merecem atenção nesta empresa?…",
                "autocomplete": "off",
            }
        ),
    )
    company_id = forms.UUIDField(required=False, widget=forms.HiddenInput())
    attachments = MultipleUploadField(
        required=False,
        widget=MultipleUploadInput(
            attrs={
                "accept": ".pdf,.png,.jpg,.jpeg,.webp,.txt,.csv",
                "aria-label": "Anexar PDF, imagem ou planilha",
            }
        ),
    )


class FeedbackForm(forms.Form):
    verdict = forms.ChoiceField(choices=AnswerFeedback.Verdict.choices, widget=forms.HiddenInput())
    comment = forms.CharField(
        required=False, max_length=800, widget=forms.Textarea(attrs={"rows": 2})
    )
