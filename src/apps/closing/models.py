"""Fechamento por recibo: layouts de leitura, documentos lidos e conferências.

Todo modelo é ``OrganizationScopedModel``: um escritório nunca vê layout, documento ou
conferência de outro. A leitura e a conferência moram em ``services``; aqui só há dados.
Portado do módulo ``fechamento`` do HubFedrizzi, sem Drive, fila Redis nem Serpro próprio.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.closing.engine import MARKER_PREFIX, is_marker
from apps.organizations.models import OrganizationScopedModel
from apps.triage.storage import PrivateTriageStorage


class Variable(models.TextChoices):
    MARKER = "marker", "Identificador"
    CNPJ = "cnpj", "CNPJ"
    CNPJ_ROOT = "cnpj_root", "Raiz do CNPJ"
    STATE_REGISTRATION = "state_registration", "Inscrição estadual"
    MUNICIPAL_REGISTRATION = "municipal_registration", "Inscrição municipal"
    COMPETENCE = "competence", "Competência"
    AMOUNT = "amount", "Valor principal"
    ICMS = "icms", "ICMS"
    IPI = "ipi", "IPI"
    ISS = "iss", "ISS a pagar"
    ISS_WITHHELD = "iss_withheld", "ISS retido"
    NUMBER = "number", "Número do recibo"
    LEGAL_NAME = "legal_name", "Razão social"


#: Quem identifica a empresa no documento, em ordem de preferência.
COMPANY_IDS = (
    Variable.CNPJ,
    Variable.CNPJ_ROOT,
    Variable.STATE_REGISTRATION,
    Variable.MUNICIPAL_REGISTRATION,
)
#: Campos de valor que o documento guarda em colunas próprias.
AMOUNT_COLUMNS = {
    Variable.AMOUNT: "amount",
    Variable.ICMS: "icms",
    Variable.IPI: "ipi",
    Variable.ISS: "iss",
    Variable.ISS_WITHHELD: "iss_withheld",
}


class ClosingLayout(OrganizationScopedModel):
    """Como ler um tipo de documento (recibo de declaração ou guia) e o que ele baixa."""

    class Kind(models.TextChoices):
        RECEIPT = "receipt", "Recibo"
        GUIDE = "guide", "Guia"

    class Compare(models.TextChoices):
        NONE = "none", "Só leitura"
        FISCAL_GUIDE = "fiscal_guide", "Guia da Central"
        PAIRED = "paired", "Outro documento"

    class ValueSource(models.TextChoices):
        AMOUNT = "amount", "Valor principal"
        ICMS = "icms", "ICMS"
        IPI = "ipi", "IPI"
        ISS = "iss", "ISS (a pagar + retido)"

    code = models.SlugField(max_length=64)
    label = models.CharField(max_length=160)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.RECEIPT)
    # ``ActivityTemplate.code`` do item do checklist que este documento baixa. Vazio: o
    # documento é lido e conferido, mas nenhuma atividade é tocada.
    activity_code = models.CharField(max_length=80, blank=True, default="", db_default="")
    compare = models.CharField(max_length=16, choices=Compare.choices, default=Compare.NONE)
    guide_kind = models.CharField(max_length=16, blank=True, default="", db_default="")
    paired_layout = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    value_source = models.CharField(
        max_length=8, choices=ValueSource.choices, default=ValueSource.AMOUNT
    )
    # A diferença aceita entre recibo e guia: centavos variam entre os dois documentos.
    tolerance = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.99"), db_default=Decimal("0.99")
    )
    # Valor zero lido do documento baixa sem guia (nada a recolher).
    zero_clears = models.BooleanField(default=True, db_default=True)
    # O cadastro da obrigação pede uma pessoa antes da baixa, mesmo com a leitura limpa.
    requires_human = models.BooleanField(default=False, db_default=False)
    sample_text = models.TextField(blank=True, default="", db_default="")
    # Layout só lê depois de ativado; a ativação exige campos obrigatórios que leem a amostra.
    active = models.BooleanField(default=False, db_default=False)

    class Meta:
        ordering = ("label",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "code"), name="closing_unique_layout_code"
            )
        ]

    def __str__(self) -> str:
        return self.label

    def clean(self) -> None:
        super().clean()
        paired = self.paired_layout
        if paired is not None and paired.organization_id != self.organization_id:
            raise ValidationError({"paired_layout": "O layout pertence a outro escritório."})
        if self.compare == self.Compare.PAIRED and paired is None:
            raise ValidationError({"paired_layout": "Escolha o documento que confere este."})
        if self.compare == self.Compare.FISCAL_GUIDE and not self.guide_kind:
            raise ValidationError({"guide_kind": "Escolha o tipo de guia."})


class ClosingField(OrganizationScopedModel):
    """Âncora no texto do documento -> variável (``engine.FieldSpec`` persistido)."""

    layout = models.ForeignKey(ClosingLayout, on_delete=models.CASCADE, related_name="fields")
    variable = models.CharField(max_length=40)
    anchor = models.CharField(max_length=255)
    # 0: valor colado à âncora. N>=1: N-ésimo valor do tipo depois dela (layout em bloco).
    occurrence = models.PositiveSmallIntegerField(default=0, db_default=0)
    # N>=2: soma os N primeiros valores depois da âncora (ex.: PIS + COFINS).
    sum_count = models.PositiveSmallIntegerField(default=0, db_default=0)
    # O layout sabe que o documento não traz este valor: lê como "não existe", não como erro.
    nullified = models.BooleanField(default=False, db_default=False)
    position = models.PositiveSmallIntegerField(default=0, db_default=0)

    class Meta:
        ordering = ("position", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("layout", "variable"), name="closing_unique_field_variable"
            )
        ]

    def __str__(self) -> str:
        return f"{self.layout_id}/{self.variable}"

    @property
    def label(self) -> str:
        if is_marker(self.variable):
            suffix = self.variable.removeprefix(MARKER_PREFIX)
            return f"Identificador {suffix}" if suffix.isdigit() else "Identificador"
        return Variable(self.variable).label if self.variable in Variable.values else self.variable

    def clean(self) -> None:
        super().clean()
        if self.layout_id and self.layout.organization_id != self.organization_id:
            raise ValidationError({"layout": "O layout pertence a outro escritório."})
        valid = set(Variable.values)
        if not (self.variable in valid or self.variable.startswith(MARKER_PREFIX)):
            raise ValidationError({"variable": "Variável desconhecida."})
        if is_marker(self.variable) and not self.anchor.strip():
            raise ValidationError({"anchor": "O identificador precisa de um texto."})


def private_closing_path(instance: ClosingDocument, filename: str) -> str:
    # O nome original é metadado; nunca deixa uma extensão não confiável moldar o caminho.
    return f"private/closing/{instance.organization_id}/{instance.pk}.bin"


class ClosingDocument(OrganizationScopedModel):
    """Um arquivo recebido, o que se leu dele e em que ponto da conferência está."""

    class State(models.TextChoices):
        RECEIVED = "received", "Aguardando leitura"
        QUARANTINE = "quarantine", "Em quarentena"
        ACCEPTED = "accepted", "Lido"
        DISCARDED = "discarded", "Descartado"

    file = models.FileField(upload_to=private_closing_path, storage=PrivateTriageStorage())
    original_name = models.CharField(max_length=255)
    content_hash = models.CharField(max_length=64, db_index=True)
    byte_size = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    state = models.CharField(max_length=12, choices=State.choices, default=State.RECEIVED)
    # Por que o documento não foi aceito: uma frase por pendência, na linguagem do operador.
    reasons = models.JSONField(default=list, blank=True, db_default=[])
    layout = models.ForeignKey(
        ClosingLayout, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents"
    )
    company = models.ForeignKey(
        "hub.ClientCompany",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closing_documents",
    )
    competence = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    icms = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    ipi = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    iss = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    iss_withheld = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    # {variável: texto lido}: o que apareceu na tela de leitura, sem o texto inteiro.
    read_values = models.JSONField(default=dict, blank=True, db_default={})
    text = models.TextField(blank=True, default="", db_default="")
    ocr_used = models.BooleanField(default=False, db_default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("organization", "state")),
            models.Index(fields=("organization", "company", "competence")),
            models.Index(fields=("organization", "content_hash")),
        ]

    def __str__(self) -> str:
        return self.original_name

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        for name in ("layout", "company"):
            related = getattr(self, name, None)
            if related is not None and related.organization_id != self.organization_id:
                errors[name] = "Este registro pertence a outro escritório."
        if errors:
            raise ValidationError(errors)

    def value_for(self, source: str) -> Decimal | None:
        """Valor que a conferência compara, conforme ``ClosingLayout.value_source``."""
        if source == ClosingLayout.ValueSource.ISS:
            parts = [v for v in (self.iss, self.iss_withheld) if v is not None]
            return sum(parts, Decimal("0.00")) if parts else self.amount
        return getattr(self, source, None)


class ClosingConference(OrganizationScopedModel):
    """Resultado de uma conferência. Cada nova passada grava outra linha: o histórico fica."""

    class Outcome(models.TextChoices):
        MATCHED = "matched", "Bateu"
        DIVERGED = "diverged", "Divergência"
        ZERO = "zero", "Zerado"
        READ = "read", "Lido"
        WAITING = "waiting", "Sem referência"

    class Source(models.TextChoices):
        NONE = "", "Nenhuma"
        FISCAL_GUIDE = "fiscal_guide", "Guia da Central"
        DOCUMENT = "document", "Outro documento"

    class Resolution(models.TextChoices):
        PENDING = "", "Pendente"
        ACCEPTED = "accepted", "Aceita"
        REJECTED = "rejected", "Rejeitada"

    class Checklist(models.TextChoices):
        NONE = "", "Sem baixa"
        DONE = "done", "Baixado"
        NO_ITEM = "no_item", "Sem item no checklist"
        BLOCKED = "blocked", "Item impedido"
        OPEN = "open", "Aguardando requisito do item"

    document = models.ForeignKey(
        ClosingDocument, on_delete=models.CASCADE, related_name="conferences"
    )
    layout = models.ForeignKey(
        ClosingLayout, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    declared_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    reference_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    reference_source = models.CharField(
        max_length=14, choices=Source.choices, blank=True, default="", db_default=""
    )
    reference_label = models.CharField(max_length=160, blank=True, default="", db_default="")
    reference_document = models.ForeignKey(
        ClosingDocument, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    note = models.CharField(max_length=500, blank=True, default="", db_default="")
    resolution = models.CharField(
        max_length=10, choices=Resolution.choices, blank=True, default="", db_default=""
    )
    resolution_reason = models.CharField(max_length=500, blank=True, default="", db_default="")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    activity = models.ForeignKey(
        "hub.OperationalActivity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closing_conferences",
    )
    checklist = models.CharField(
        max_length=8, choices=Checklist.choices, blank=True, default="", db_default=""
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("organization", "document", "created_at"))]

    def __str__(self) -> str:
        return f"{self.document_id}: {self.get_outcome_display()}"

    @property
    def difference(self) -> Decimal | None:
        if self.declared_amount is None or self.reference_amount is None:
            return None
        return self.reference_amount - self.declared_amount

    @property
    def needs_person(self) -> bool:
        """A baixa espera uma decisão humana."""
        return (
            self.outcome in {self.Outcome.DIVERGED, self.Outcome.WAITING}
            or (
                self.outcome == self.Outcome.READ
                and bool(self.layout and self.layout.requires_human)
            )
        ) and self.resolution == self.Resolution.PENDING

    def clean(self) -> None:
        super().clean()
        if self.document_id and self.document.organization_id != self.organization_id:
            raise ValidationError({"document": "O documento pertence a outro escritório."})
