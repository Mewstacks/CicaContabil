"""Shared reference data for legal deadlines (D-277).

Nothing here belongs to an office. A calendar year or a deadline rule only produces dates
after a platform reviewer approves it with its legal basis and source; drafts are inert.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class ReferenceStatus(models.TextChoices):
    DRAFT = "draft", "Rascunho"
    APPROVED = "approved", "Aprovada"
    RETIRED = "retired", "Retirada"


class BusinessCalendarYear(UUIDTimeStampedModel):
    """Days without banking business in one year, as published for the financial system."""

    scope = models.CharField(max_length=16, default="BR")
    year = models.PositiveSmallIntegerField()
    legal_basis = models.CharField(max_length=300)
    source_url = models.URLField(max_length=500)
    status = models.CharField(
        max_length=16, choices=ReferenceStatus.choices, default=ReferenceStatus.DRAFT
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("scope", "year")
        constraints = [
            models.UniqueConstraint(fields=("scope", "year"), name="fiscal_calendar_unique_year"),
            models.CheckConstraint(
                condition=~models.Q(status="approved")
                | (models.Q(approved_by__isnull=False) & models.Q(approved_at__isnull=False)),
                name="fiscal_calendar_year_approval_recorded",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.scope} {self.year}"


class NonBusinessDay(UUIDTimeStampedModel):
    calendar = models.ForeignKey(
        BusinessCalendarYear, on_delete=models.CASCADE, related_name="days"
    )
    day = models.DateField()
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ("day",)
        constraints = [
            models.UniqueConstraint(fields=("calendar", "day"), name="fiscal_calendar_unique_day")
        ]

    def clean(self) -> None:
        super().clean()
        if self.calendar_id and self.day.year != self.calendar.year:
            raise ValidationError("O dia precisa pertencer ao ano do calendário.")

    def __str__(self) -> str:
        return f"{self.day:%d/%m/%Y} {self.name}"


class TaxDeadlineRule(UUIDTimeStampedModel):
    """How the legal deadline of one obligation follows from its competência.

    Example: DCTFWeb — last business day of the month after the competência, from 01/2025.
    An approved version is frozen; a correction is a new version with its own validity.
    """

    class Anchor(models.TextChoices):
        DAY_OF_MONTH = "day_of_month", "Dia do mês"
        LAST_DAY = "last_day", "Último dia do mês"
        LAST_BUSINESS_DAY = "last_business_day", "Último dia útil do mês"

    class Shift(models.TextChoices):
        PREVIOUS = "previous", "Antecipa para o dia útil anterior"
        NEXT = "next", "Prorroga para o dia útil seguinte"
        NONE = "none", "Não ajusta"

    code = models.SlugField(max_length=64)
    version = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=120)
    month_offset = models.PositiveSmallIntegerField(default=1)
    anchor = models.CharField(max_length=24, choices=Anchor.choices)
    day = models.PositiveSmallIntegerField(null=True, blank=True)
    non_business_shift = models.CharField(max_length=16, choices=Shift.choices, default=Shift.NONE)
    valid_from = models.DateField(help_text="Primeira competência (dia 1) coberta.")
    valid_until = models.DateField(
        null=True, blank=True, help_text="Última competência coberta, quando houver."
    )
    legal_basis = models.CharField(max_length=300)
    source_url = models.URLField(max_length=500)
    source_checked_on = models.DateField()
    status = models.CharField(
        max_length=16, choices=ReferenceStatus.choices, default=ReferenceStatus.DRAFT
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("code", "-version")
        constraints = [
            models.UniqueConstraint(fields=("code", "version"), name="fiscal_rule_unique_version"),
            models.CheckConstraint(
                condition=~models.Q(status="approved")
                | (models.Q(approved_by__isnull=False) & models.Q(approved_at__isnull=False)),
                name="fiscal_rule_approval_recorded",
            ),
            models.CheckConstraint(
                condition=~models.Q(anchor="day_of_month")
                | (models.Q(day__gte=1) & models.Q(day__lte=31)),
                name="fiscal_rule_day_for_day_anchor",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.valid_from and self.valid_from.day != 1:
            raise ValidationError({"valid_from": "Informe o primeiro dia da competência."})
        if self.valid_until and self.valid_from and self.valid_until < self.valid_from:
            raise ValidationError({"valid_until": "A vigência termina antes de começar."})

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if self.pk and not self._state.adding:
            stored = type(self).objects.filter(pk=self.pk).values("status").first()
            if stored and stored["status"] != ReferenceStatus.DRAFT:
                frozen = type(self).objects.get(pk=self.pk)
                changed = [
                    field.name
                    for field in self._meta.concrete_fields
                    if field.name not in {"status", "updated_at", "valid_until"}
                    and getattr(frozen, field.attname) != getattr(self, field.attname)
                ]
                if changed:
                    raise ValidationError(
                        "Regra aprovada não muda: crie uma nova versão com vigência própria."
                    )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.title} (v{self.version})"
