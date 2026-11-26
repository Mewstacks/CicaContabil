"""Fechamento por recibo: receber, ler, identificar a empresa, conferir e dar baixa.

O fluxo de um arquivo: ``ingest_upload`` guarda e chama ``read_document``; a leitura acha o
layout (todos os identificadores presentes, o mais específico vence, empate vai para revisão),
lê os campos, identifica a empresa e a competência; só um documento lido por inteiro vira
``ACCEPTED`` e ganha uma ``ClosingConference``. A conferência compara o valor do documento
com a guia da Central (``hub.FiscalGuide``) ou com outro documento lido, e a baixa no checklist
só acontece quando não há dúvida: divergência e ausência de referência esperam uma pessoa.

Referências de mercado: ``invoice2data`` (modelo = palavras-chave que precisam todas casar +
campos por padrão), a baixa automática do Domínio (que não baixa quando há mais de um imposto
com o mesmo valor e vencimento) e as tolerâncias de conferência de contas a pagar (tolerância
configurável; exceção vai para uma pessoa; sobreposição fica registrada).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.closing import checklist, engine
from apps.closing.engine import FieldSpec
from apps.closing.models import (
    AMOUNT_COLUMNS,
    COMPANY_IDS,
    ClosingConference,
    ClosingDocument,
    ClosingField,
    ClosingLayout,
    Variable,
)
from apps.hub.models import ClientCompany, FiscalGuide
from apps.organizations.models import Organization

MAX_BYTES = 10 * 1024 * 1024
ACCEPTED_SUFFIXES = frozenset({".pdf", ".xml", ".txt"})
_ZERO = Decimal("0.00")


class CompanyLookup:
    """Empresa do escritório pelo identificador lido: CNPJ, raiz, IE ou IM (nunca de outro)."""

    NOT_IN_PORTFOLIO = "mas ele não é de uma empresa cadastrada na sua carteira"

    def __init__(self, organization: Organization, allowed: Any = None) -> None:
        self.organization = organization
        # Carteira de quem lê: empresa fora dela nunca é identificada (nem baixa o item dela).
        self.allowed = allowed

    def find(self, values: dict[str, Any]) -> tuple[ClientCompany | None, str]:
        companies = ClientCompany.objects.filter(organization=self.organization, active=True)
        # A carteira só vale DEPOIS de casar com o escritório inteiro: filtrar antes mudaria o
        # resultado (duplicata fora da carteira escolhida em silêncio, ou queda para um
        # identificador mais fraco que casa com outra empresa).
        in_portfolio = (
            None if self.allowed is None else set(self.allowed.values_list("pk", flat=True))
        )
        tries: list[tuple[str, str, Any]] = []
        if values.get("cnpj"):
            tries.append(("CNPJ", _mask_cnpj(str(values["cnpj"])), self._by_cnpj))
        if values.get("cnpj_root"):
            tries.append(("raiz de CNPJ", str(values["cnpj_root"]), self._by_root))
        if values.get("state_registration"):
            tries.append(("Inscrição Estadual", str(values["state_registration"]), self._by_state))
        if values.get("municipal_registration"):
            tries.append(
                ("Inscrição Municipal", str(values["municipal_registration"]), self._by_municipal)
            )
        if not tries:
            return None, ("empresa — não li CNPJ, raiz do CNPJ nem inscrição estadual ou municipal")
        for label, shown, finder in tries:
            matches = finder(companies, shown if label != "CNPJ" else str(values["cnpj"]))
            outside = in_portfolio is not None and any(c.pk not in in_portfolio for c in matches)
            if outside:
                # Uma mensagem só para "não existe", "é de fora da carteira" e "duplicado com
                # empresa de fora": quem tem carteira restrita não descobre o que há fora dela.
                return None, f"empresa — li o {label} {shown}, {self.NOT_IN_PORTFOLIO}"
            if len(matches) == 1:
                return matches[0], ""
            if len(matches) > 1:
                return None, f"empresa — {label} {shown} pertence a mais de uma empresa cadastrada"
        label, shown, _finder = tries[0]
        return None, f"empresa — li o {label} {shown}, {self.NOT_IN_PORTFOLIO}"

    @staticmethod
    def _by_cnpj(companies: Any, cnpj: str) -> list[ClientCompany]:
        from apps.common.cnpj import strip_document

        target = strip_document(cnpj)
        return [c for c in companies if c.cnpj_masked and strip_document(c.cnpj_masked) == target]

    @staticmethod
    def _by_root(companies: Any, root: str) -> list[ClientCompany]:
        found = [c for c in companies if c.commercial_root_cnpj == root]
        # A matriz desempata quando a raiz pertence também às filiais (ordem 0001).
        head = [c for c in found if re.sub(r"\D", "", c.cnpj_masked or "")[8:12] == "0001"]
        return head if len(found) > 1 and len(head) == 1 else found

    @staticmethod
    def _by_state(companies: Any, number: str) -> list[ClientCompany]:
        target = re.sub(r"\D", "", number)
        return [c for c in companies if re.sub(r"\D", "", c.state_registration) == target]

    @staticmethod
    def _by_municipal(companies: Any, number: str) -> list[ClientCompany]:
        target = re.sub(r"\D", "", number)
        return [c for c in companies if re.sub(r"\D", "", c.municipal_registration) == target]


def _mask_cnpj(digits: str) -> str:
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return digits


def _field_specs(layout: ClosingLayout) -> list[FieldSpec]:
    return [
        FieldSpec(f.variable, f.anchor, f.occurrence, f.sum_count, f.nullified)
        for f in layout.fields.all()
    ]


def _markers(layout: ClosingLayout) -> list[str]:
    return [f.anchor for f in layout.fields.all() if engine.is_marker(f.variable) and f.anchor]


# --- receiving -----------------------------------------------------------------------


def ingest_upload(
    *,
    organization: Organization,
    actor: User,
    upload: UploadedFile,
    request: object | None = None,
    allowed_companies: Any = None,
    visible_documents: Any = None,
) -> ClosingDocument:
    """Guarda o arquivo (um por conteúdo) e o lê na hora."""
    name = PurePosixPath((upload.name or "").replace("\\", "/")).name[:255]
    if not name:
        raise ValidationError("O arquivo não possui nome.")
    size = upload.size or 0
    if size <= 0:
        raise ValidationError(f"{name}: arquivo vazio.")
    if size > MAX_BYTES:
        raise ValidationError(f"{name}: arquivo acima de 10 MB.")
    suffix = PurePosixPath(name).suffix.casefold()
    if suffix not in ACCEPTED_SUFFIXES:
        raise ValidationError(f"{name}: formato {suffix or 'sem extensão'} não aceito.")
    data = b"".join(upload.chunks())
    if len(data) > MAX_BYTES:
        raise ValidationError(f"{name}: arquivo acima de 10 MB.")
    if suffix == ".pdf" and not (data.startswith(b"%PDF-") and b"%%EOF" in data[-2048:]):
        raise ValidationError(f"{name}: PDF sem estrutura inicial e final válida.")
    digest = hashlib.sha256(data).hexdigest()
    existing = (
        ClosingDocument.objects.filter(organization=organization, content_hash=digest)
        .exclude(state=ClosingDocument.State.DISCARDED)
        .first()
    )
    if existing is not None:
        if visible_documents is not None and not visible_documents.filter(pk=existing.pk).exists():
            # Mesmo conteúdo já entrou numa carteira que quem envia não vê: não revela qual.
            raise ValidationError(f"{name}: arquivo já recebido.")
        return existing
    with transaction.atomic():
        document = ClosingDocument(
            organization=organization,
            original_name=name,
            content_hash=digest,
            byte_size=len(data),
            uploaded_by=actor,
        )
        document.file.save("closing.bin", ContentFile(data), save=False)
        document.save()
    record_event(
        action="closing.document.received",
        actor=actor,
        organization=organization,
        target=document,
        request=request,
        metadata={"content_hash": digest, "byte_size": len(data)},
    )
    return read_document(document, data=data, allowed_companies=allowed_companies)


# --- reading -------------------------------------------------------------------------


def _document_bytes(document: ClosingDocument) -> bytes:
    with document.file.open("rb") as stream:
        data: bytes = stream.read(MAX_BYTES + 1)
    if hashlib.sha256(data).hexdigest() != document.content_hash:
        raise ValidationError("O arquivo mudou depois de recebido.")
    return data


def read_document(
    document: ClosingDocument, *, data: bytes | None = None, allowed_companies: Any = None
) -> ClosingDocument:
    """Lê o arquivo e decide: quarentena (com os motivos) ou aceito (com conferência)."""
    with transaction.atomic():
        document = ClosingDocument.objects.select_for_update().get(pk=document.pk)
        if document.state == ClosingDocument.State.DISCARDED:
            return document
        data = data if data is not None else _document_bytes(document)
        result = engine.read_text(data, document.original_name)
        reasons: list[str] = []
        text = result.text
        if not text.strip():
            ocr_text = _ocr_text(document, data)
            if ocr_text:
                text, document.ocr_used = ocr_text, True
            else:
                reasons.append(result.message or "arquivo sem texto legível")
        document.text = text
        _reset(document)
        if text.strip():
            _apply_layouts(document, text, reasons, allowed_companies)
        document.reasons = reasons
        document.read_at = timezone.now()
        document.state = (
            ClosingDocument.State.ACCEPTED if not reasons else ClosingDocument.State.QUARANTINE
        )
        document.save()
        conference = None
        if document.state == ClosingDocument.State.ACCEPTED:
            conference = confer(document)
    if conference is not None and document.company_id and document.competence:
        # Este documento pode ser a referência que outros esperavam.
        reevaluate_waiting(
            document.organization,
            company=document.company,
            competence=document.competence,
            exclude=document.pk,
        )
    return document


def _reset(document: ClosingDocument) -> None:
    document.layout = None
    document.company = None
    document.competence = None
    for column in AMOUNT_COLUMNS.values():
        setattr(document, column, None)
    document.read_values = {}


def _apply_layouts(
    document: ClosingDocument, text: str, reasons: list[str], allowed_companies: Any = None
) -> None:
    layouts = list(
        ClosingLayout.objects.filter(organization=document.organization).prefetch_related("fields")
    )
    active = {layout.pk: layout for layout in layouts if layout.active}
    wins = engine.winners(text, {pk: _markers(layout) for pk, layout in active.items()})
    if len(wins) > 1:
        names = ", ".join(sorted(active[pk].label for pk in wins))  # type: ignore[index]
        reasons.append(f"tipo — mais de um layout reconhece este arquivo ({names})")
        return
    if not wins:
        drafts = engine.winners(
            text, {layout.pk: _markers(layout) for layout in layouts if not layout.active}
        )
        if drafts:
            label = next(layout.label for layout in layouts if layout.pk == drafts[0])
            reasons.append(
                f"tipo — o layout {label} reconhece o arquivo, mas ainda não foi ativado"
            )
        else:
            reasons.append("tipo — nenhum layout cadastrado reconhece este arquivo")
        return
    layout = active[wins[0]]  # type: ignore[index]
    document.layout = layout
    values: dict[str, Any] = {}
    for spec in _field_specs(layout):
        if engine.is_marker(spec.variable):
            continue
        values[spec.variable] = engine.extract(text, spec)
    document.read_values = {k: _printable(v) for k, v in values.items() if v is not None}
    competence = values.get("competence")
    if isinstance(competence, tuple):
        document.competence = date(competence[0], competence[1], 1)
    else:
        reasons.append("competência (mês/ano)")
    company, reason = CompanyLookup(document.organization, allowed_companies).find(values)
    document.company = company
    if reason:
        reasons.append(reason)
    for variable, column in AMOUNT_COLUMNS.items():
        value = values.get(variable.value)
        if isinstance(value, Decimal):
            setattr(document, column, value)
    declared = {f.variable for f in layout.fields.all() if not f.nullified}
    declared_values = [v for v in AMOUNT_COLUMNS if v.value in declared]
    if _needs_value(layout) and not declared_values:
        reasons.append("valor — o layout não tem campo de valor")
    for variable in declared_values:
        if values.get(variable.value) is None:
            reasons.append(f"valor — não li {Variable(variable).label.lower()}")


def _needs_value(layout: ClosingLayout) -> bool:
    return layout.compare != ClosingLayout.Compare.NONE or layout.zero_clears


def _printable(value: object) -> str:
    if isinstance(value, tuple):
        return f"{value[1]:02d}/{value[0]}"
    return str(value)


def _ocr_text(document: ClosingDocument, data: bytes) -> str:
    """Texto por OCR local do Triagem, só quando ele está ligado e há orçamento."""
    suffix = PurePosixPath(document.original_name).suffix.casefold()
    if suffix != ".pdf":
        return ""
    from apps.triage import ocr
    from apps.triage.models import TriageOcrUsage

    pages = ocr.pdf_pages_for_ocr(data)
    if pages < 1 or ocr.ocr_blocker(document.organization, pages):
        return ""
    engine_ = ocr.get_engine()
    if engine_ is None:
        return ""
    try:
        text, used = ocr.run_ocr(data, suffix, engine_, pages)
    except Exception:
        return ""
    TriageOcrUsage.objects.create(organization=document.organization, pages=used)
    return text


# --- conferring ----------------------------------------------------------------------


def _within(declared: Decimal, reference: Decimal, tolerance: Decimal) -> bool:
    return abs(declared - reference) <= tolerance


def confer(document: ClosingDocument) -> ClosingConference:
    """Compara o documento com a referência do layout e tenta dar baixa."""
    layout = document.layout
    assert layout is not None
    Outcome = ClosingConference.Outcome
    declared = document.value_for(layout.value_source)
    conference = ClosingConference(
        organization=document.organization,
        document=document,
        layout=layout,
        declared_amount=declared,
        resolution=ClosingConference.Resolution.PENDING,
    )
    if declared is not None and declared == _ZERO and layout.zero_clears:
        conference.outcome = Outcome.ZERO
        conference.note = "Valor zerado: nada a recolher."
    elif layout.compare == ClosingLayout.Compare.NONE:
        conference.outcome = Outcome.READ
        conference.note = "Documento lido; o layout não confere valor."
    elif declared is None:
        conference.outcome = Outcome.WAITING
        conference.note = "O documento não trouxe o valor a conferir."
    else:
        _compare(conference, document, layout, declared)
    conference.save()
    _route(conference)
    return conference


def _compare(
    conference: ClosingConference,
    document: ClosingDocument,
    layout: ClosingLayout,
    declared: Decimal,
) -> None:
    Outcome = ClosingConference.Outcome
    reference, source, label, note, reference_document = _reference(document, layout)
    conference.reference_source = source
    conference.reference_label = label[:160]
    conference.reference_document = reference_document
    if reference is None:
        conference.outcome = Outcome.WAITING
        conference.note = note
        return
    conference.reference_amount = reference
    if _within(declared, reference, layout.tolerance):
        conference.outcome = Outcome.MATCHED
        conference.note = note
    else:
        conference.outcome = Outcome.DIVERGED
        conference.note = "O valor do documento não bate com a referência."


def _reference(
    document: ClosingDocument, layout: ClosingLayout
) -> tuple[Decimal | None, str, str, str, ClosingDocument | None]:
    Source = ClosingConference.Source
    if document.company_id is None or document.competence is None:
        return None, Source.NONE, "", "Sem empresa ou competência para achar a referência.", None
    if layout.compare == ClosingLayout.Compare.FISCAL_GUIDE:
        label = f"{document.competence.month:02d}/{document.competence.year}"
        guides = list(
            FiscalGuide.objects.filter(
                organization=document.organization,
                company=document.company,
                kind=layout.guide_kind,
                competence=label,
            ).exclude(status=FiscalGuide.Status.SKIPPED)
        )
        if not guides:
            return None, Source.NONE, "", f"Nenhuma guia da Central em {label}.", None
        if len(guides) > 1:
            return None, Source.NONE, "", f"Há mais de uma guia da Central em {label}.", None
        guide = guides[0]
        return (
            Decimal(guide.amount_cents) / 100,
            Source.FISCAL_GUIDE,
            f"{guide.get_kind_display()} {guide.reference}",
            f"Conferido com a guia {guide.reference} da Central.",
            None,
        )
    paired = layout.paired_layout
    if paired is None:
        return None, Source.NONE, "", "O layout não aponta o documento que o confere.", None
    candidates = list(
        ClosingDocument.objects.filter(
            organization=document.organization,
            company=document.company,
            competence=document.competence,
            layout=paired,
            state=ClosingDocument.State.ACCEPTED,
        ).exclude(pk=document.pk)
    )
    amounts = {doc.value_for(paired.value_source) for doc in candidates}
    amounts.discard(None)
    if not candidates or not amounts:
        return None, Source.NONE, "", f"Aguardando {paired.label}.", None
    if len(amounts) > 1:
        return None, Source.NONE, "", f"Há mais de um {paired.label} com valores diferentes.", None
    chosen = candidates[0]
    return (
        amounts.pop(),
        Source.DOCUMENT,
        f"{paired.label}: {chosen.original_name}",
        f"Conferido com {chosen.original_name}.",
        chosen,
    )


def _route(conference: ClosingConference) -> None:
    Outcome = ClosingConference.Outcome
    layout = conference.layout
    if conference.outcome == Outcome.DIVERGED:
        checklist.block(
            conference,
            f"Divergência: documento R$ {_money(conference.declared_amount)} "
            f"x referência R$ {_money(conference.reference_amount)}.",
        )
        return
    if conference.outcome == Outcome.WAITING:
        return
    if conference.outcome == Outcome.READ and layout is not None and layout.requires_human:
        return
    checklist.clear(conference)


def _money(value: Decimal | None) -> str:
    if value is None:
        return "—"
    whole, _, cents = f"{value:.2f}".partition(".")
    groups = f"{int(whole):,}".replace(",", ".")
    return f"{groups},{cents}"


# --- people decide ------------------------------------------------------------------


@transaction.atomic
def resolve(
    conference: ClosingConference,
    *,
    actor: User,
    accept: bool,
    reason: str,
    request: object | None = None,
) -> ClosingConference:
    """Uma pessoa aceita (baixa o item) ou rejeita (mantém o item impedido) a conferência."""
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("Informe o motivo da decisão.")
    locked = (
        ClosingConference.objects.select_for_update()
        .select_related("document", "layout")
        .get(pk=conference.pk)
    )
    if locked.resolution:
        raise ValidationError("Esta conferência já foi decidida.")
    latest = locked.document.conferences.first()
    if latest is not None and latest.pk != locked.pk:
        raise ValidationError("Há uma conferência mais recente para este documento.")
    if not (
        locked.outcome
        in {
            ClosingConference.Outcome.DIVERGED,
            ClosingConference.Outcome.WAITING,
        }
        or (
            locked.outcome == ClosingConference.Outcome.READ
            and locked.layout
            and locked.layout.requires_human
        )
    ):
        raise ValidationError("Esta conferência não precisa de decisão.")
    locked.resolution = (
        ClosingConference.Resolution.ACCEPTED if accept else ClosingConference.Resolution.REJECTED
    )
    locked.resolution_reason = reason[:500]
    locked.resolved_by = actor
    locked.resolved_at = timezone.now()
    locked.save(
        update_fields=[
            "resolution",
            "resolution_reason",
            "resolved_by",
            "resolved_at",
            "updated_at",
        ]
    )
    if accept:
        checklist.clear(locked, actor=actor, human=True)
    else:
        checklist.block(locked, f"Conferência rejeitada: {reason}")
    record_event(
        action="closing.conference.resolved",
        actor=actor,
        organization=locked.organization,
        target=locked,
        request=request,
        metadata={"accepted": accept, "outcome": locked.outcome},
    )
    return locked


@transaction.atomic
def discard(
    document: ClosingDocument, *, actor: User, request: object | None = None
) -> ClosingDocument:
    """Tira o arquivo da fila. A baixa já dada fica: o histórico da conferência é preservado."""
    locked = ClosingDocument.objects.select_for_update().get(pk=document.pk)
    locked.state = ClosingDocument.State.DISCARDED
    locked.save(update_fields=["state", "updated_at"])
    record_event(
        action="closing.document.discarded",
        actor=actor,
        organization=locked.organization,
        target=locked,
        request=request,
        metadata={"content_hash": locked.content_hash},
    )
    return locked


def reread(
    document: ClosingDocument, *, actor: User | None = None, allowed_companies: Any = None
) -> ClosingDocument:
    """Relê o arquivo com os layouts de hoje (depois de ajustar ou ativar um layout)."""
    if document.state == ClosingDocument.State.DISCARDED:
        raise ValidationError("O arquivo foi descartado.")
    return read_document(document, allowed_companies=allowed_companies)


def reevaluate_waiting(
    organization: Organization,
    *,
    company: ClientCompany | None,
    competence: date | None,
    exclude: Any = None,
) -> int:
    """Refaz a conferência dos documentos que esperavam referência da mesma empresa/mês."""
    if company is None or competence is None:
        return 0
    redone = 0
    pending = (
        ClosingDocument.objects.filter(
            organization=organization,
            company=company,
            competence=competence,
            state=ClosingDocument.State.ACCEPTED,
            layout__isnull=False,
        )
        .exclude(pk=exclude)
        .select_related("layout")
    )
    for document in pending:
        latest = document.conferences.first()
        if (
            latest is None
            or latest.outcome != ClosingConference.Outcome.WAITING
            or latest.resolution
        ):
            continue
        with transaction.atomic():
            confer(document)
        redone += 1
    return redone


# --- layouts -------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldDiagnosis:
    variable: str
    label: str
    anchor: str
    found: bool
    value: str


def diagnose(layout: ClosingLayout, text: str) -> list[FieldDiagnosis]:
    """O que cada campo do layout lê num texto: base da tela de ajuste e da ativação."""
    rows: list[FieldDiagnosis] = []
    for field in layout.fields.all():
        spec = FieldSpec(
            field.variable, field.anchor, field.occurrence, field.sum_count, field.nullified
        )
        value = engine.extract(text, spec) if text.strip() else None
        label = (
            "Identificador"
            if engine.is_marker(field.variable)
            else Variable(field.variable).label
            if field.variable in Variable.values
            else field.variable
        )
        rows.append(
            FieldDiagnosis(
                variable=field.variable,
                label=label,
                anchor=field.anchor,
                found=value is not None or field.nullified,
                value="" if value is None else _plain(value),
            )
        )
    return rows


def _plain(value: object) -> str:
    if isinstance(value, tuple):
        return f"{value[1]:02d}/{value[0]}"
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


def activation_problems(layout: ClosingLayout) -> list[str]:
    """Por que o layout ainda não pode ler documentos de verdade (vazio = pode ativar)."""
    fields: list[ClosingField] = list(layout.fields.all())
    present = {f.variable for f in fields if not f.nullified}
    problems: list[str] = []
    if not any(engine.is_marker(v) for v in present):
        problems.append("Falta o identificador do documento.")
    if Variable.COMPETENCE not in present:
        problems.append("Falta a competência.")
    if not any(v in present for v in COMPANY_IDS):
        problems.append("Falta o identificador da empresa (CNPJ, raiz, IE ou IM).")
    if _needs_value(layout) and not any(v.value in present for v in AMOUNT_COLUMNS):
        problems.append("Falta um campo de valor.")
    if layout.compare == ClosingLayout.Compare.FISCAL_GUIDE and not layout.guide_kind:
        problems.append("Falta o tipo de guia da Central.")
    if layout.compare == ClosingLayout.Compare.PAIRED and layout.paired_layout_id is None:
        problems.append("Falta o documento que confere este.")
    if not problems and layout.sample_text.strip():
        unread = [d for d in diagnose(layout, layout.sample_text) if not d.found]
        if unread:
            problems.append("A amostra não lê: " + ", ".join(d.label.lower() for d in unread) + ".")
    elif not problems:
        problems.append("Falta uma amostra para testar a leitura.")
    return problems
