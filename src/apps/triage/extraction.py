"""Deterministic first pass that suggests company, type, period and name for review.

Nothing here approves or archives. Every suggestion lands in ``ai_fields`` with the
text that produced it, and the item always stops in ``aguardando_revisao`` so a person
confirms or corrects before the file reaches a destination. No external service is
called: matching uses the office's own companies and naming catalogue only.
"""

from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import PurePosixPath
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.hub.models import ClientCompany
from apps.triage.models import (
    CounterpartyAlias,
    DocumentType,
    TriageEvent,
    TriageItem,
    TriageSafetyScan,
)
from apps.triage.transitions import TriageStatus

_TEXT_LIMIT = 256 * 1024
_PDF_PAGES = 3
_CNPJ = re.compile(r"(?<!\d)(\d{2})\.?(\d{3})\.?(\d{3})/?(\d{4})-?(\d{2})(?!\d)")
_MONTH_YEAR = re.compile(r"(?<!\d)(0[1-9]|1[0-2])[/._-](20\d{2})(?!\d)")
_YEAR_MONTH = re.compile(r"(?<!\d)(20\d{2})[/._-]?(0[1-9]|1[0-2])(?!\d)")
_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_MONTH_NAME = re.compile(r"\b(" + "|".join(_MONTHS) + r")\b[\s/de.-]*(20\d{2})", re.IGNORECASE)


@dataclass
class Suggestion:
    company: ClientCompany | None = None
    document_type: DocumentType | None = None
    period_label: str = ""
    counterparty_token: str = ""
    final_name: str = ""
    evidence: dict[str, dict[str, object]] = field(default_factory=dict)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def _tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", _fold(value)) if len(token) >= 3}


def _payload_text(item: TriageItem) -> str:
    """Read bounded text from formats that carry it; binary formats yield nothing."""
    suffix = PurePosixPath(item.original_name).suffix.casefold()
    with item.blob.content.open("rb") as stream:
        data: bytes = stream.read(25 * 1024 * 1024 + 1)
    if hashlib.sha256(data).hexdigest() != item.content_hash:
        raise ValidationError("O hash do anexo mudou depois da verificação.")
    if suffix in {".xml", ".csv", ".ofx"}:
        head = data[:_TEXT_LIMIT]
        for encoding in ("utf-8", "latin-1"):
            try:
                return head.decode(encoding)
            except UnicodeDecodeError:
                continue
        return ""
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            parts = []
            for page in reader.pages[:_PDF_PAGES]:
                parts.append(page.extract_text() or "")
                if sum(len(part) for part in parts) > _TEXT_LIMIT:
                    break
            return "".join(parts)[:_TEXT_LIMIT]
        except Exception:  # A malformed but format-valid PDF still goes to review.
            return ""
    return ""


def _match_company(
    item: TriageItem, sources: dict[str, str]
) -> tuple[ClientCompany | None, dict[str, object]]:
    companies = list(
        ClientCompany.objects.filter(organization=item.organization, active=True).only(
            "id", "name", "cnpj_masked", "dominio_code"
        )
    )
    by_cnpj = {
        re.sub(r"\D", "", company.cnpj_masked): company
        for company in companies
        if len(re.sub(r"\D", "", company.cnpj_masked)) == 14
    }
    for source, text in sources.items():
        found = {"".join(match.groups()) for match in _CNPJ.finditer(text)}
        hits = {by_cnpj[digits] for digits in found if digits in by_cnpj}
        if len(hits) == 1:
            company = hits.pop()
            return company, {"valor": company.name, "evidencia": f"CNPJ no {source}"}
    filename = PurePosixPath(item.original_name).stem
    prefix = re.match(r"\s*([A-Za-z0-9]+)[_\s-]", filename)
    if prefix:
        by_code = {company.dominio_code.casefold(): company for company in companies}
        coded = by_code.get(prefix.group(1).casefold())
        if coded is not None and coded.dominio_code:
            return coded, {"valor": coded.name, "evidencia": "Código Domínio no nome"}
    return None, {}


def _match_document_type(
    item: TriageItem, sources: dict[str, str]
) -> tuple[DocumentType | None, dict[str, object]]:
    types = list(DocumentType.objects.filter(organization=item.organization, active=True))
    haystack = _tokens(" ".join([sources.get("nome", ""), sources.get("assunto", "")]))
    scored: list[tuple[int, DocumentType]] = []
    for document_type in types:
        wanted = _tokens(document_type.code.replace("-", " ")) | _tokens(document_type.label)
        score = len(wanted & haystack)
        if score:
            scored.append((score, document_type))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if scored and (len(scored) == 1 or scored[0][0] > scored[1][0]):
        document_type = scored[0][1]
        return document_type, {"valor": document_type.label, "evidencia": "Palavras do nome"}
    return None, {}


def _match_period(sources: dict[str, str]) -> tuple[str, dict[str, object]]:
    for source, text in sources.items():
        found: set[str] = set()
        for match in _MONTH_YEAR.finditer(text):
            found.add(f"{match.group(2)}-{match.group(1)}")
        for match in _YEAR_MONTH.finditer(text):
            found.add(f"{match.group(1)}-{match.group(2)}")
        for match in _MONTH_NAME.finditer(_fold(text)):
            found.add(f"{match.group(2)}-{_MONTHS[match.group(1)]:02d}")
        found = {value for value in found if 2000 <= int(value[:4]) <= date.today().year + 1}
        if len(found) == 1:
            value = found.pop()
            return value, {"valor": value, "evidencia": f"Data no {source}"}
    return "", {}


def _match_counterparty(
    item: TriageItem, document_type: DocumentType | None, sources: dict[str, str]
) -> tuple[str, dict[str, object]]:
    if document_type is None or document_type.counterparty_kind == "nenhuma":
        return "", {}
    text = _fold(" ".join(sources.values()))
    tokens = {
        alias.token
        for alias in CounterpartyAlias.objects.filter(
            organization=item.organization, kind=document_type.counterparty_kind
        )
        if _fold(alias.alias) in text
    }
    if len(tokens) == 1:
        token = tokens.pop()
        return token, {"valor": token, "evidencia": "Apelido cadastrado no documento"}
    return "", {}


def render_final_name(
    *,
    template: str,
    company: ClientCompany | None,
    period_label: str,
    counterparty_token: str,
    suffix: str,
) -> str:
    """Fill the office template; missing parts stay visible so review can fix them."""
    period = period_label.replace("-", "") if period_label else "PERIODO"
    values = {
        "codigo": (company.dominio_code if company and company.dominio_code else "CODIGO"),
        "periodo": period,
        "contraparte": counterparty_token or "CONTRAPARTE",
    }
    try:
        stem = template.format(**values)
    except (KeyError, IndexError, ValueError):
        return ""
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", stem).strip(" .")[:200]
    return f"{stem}{suffix}" if stem else ""


def suggest(item: TriageItem) -> Suggestion:
    sources = {
        "nome": item.original_name,
        "assunto": item.subject,
        "conteúdo": _payload_text(item),
    }
    result = Suggestion()
    result.company, evidence = _match_company(item, sources)
    if evidence:
        result.evidence["Empresa"] = evidence
    result.document_type, evidence = _match_document_type(item, sources)
    if evidence:
        result.evidence["Tipo"] = evidence
    result.period_label, evidence = _match_period(sources)
    if evidence:
        result.evidence["Período"] = evidence
    result.counterparty_token, evidence = _match_counterparty(item, result.document_type, sources)
    if evidence:
        result.evidence["Contraparte"] = evidence
    if result.document_type is not None:
        result.final_name = render_final_name(
            template=result.document_type.name_template,
            company=result.company,
            period_label=result.period_label,
            counterparty_token=result.counterparty_token,
            suffix=PurePosixPath(item.original_name).suffix.casefold(),
        )
    return result


def extract_item(*, item_id: UUID | str) -> TriageItem:
    """Move a scanned item through extraction into human review. Idempotent."""
    with transaction.atomic():
        item = (
            TriageItem.objects.select_for_update(of=("self",))
            .select_related("blob", "organization")
            .get(pk=item_id)
        )
        if item.status != TriageStatus.AWAITING_EXTRACTION:
            return item
        released = TriageSafetyScan.objects.filter(
            triage_item=item,
            verdict=TriageSafetyScan.Verdict.CLEAN,
            format_verdict=TriageSafetyScan.FormatVerdict.VALID,
            content_hash=item.content_hash,
        ).exists()
        if not released:
            return item
        previous = item.status
        item.transition_to(TriageStatus.EXTRACTING)
        item.save(update_fields=["status", "updated_at"])
        TriageEvent.objects.create(
            organization=item.organization,
            triage_item=item,
            from_status=previous,
            to_status=item.status,
            note="Identificação automática iniciada",
        )
        try:
            result = suggest(item)
        except ValidationError as exc:
            item.transition_to(TriageStatus.FAILED)
            item.save(update_fields=["status", "updated_at"])
            TriageEvent.objects.create(
                organization=item.organization,
                triage_item=item,
                from_status=TriageStatus.EXTRACTING,
                to_status=item.status,
                note=exc.messages[0][:500],
            )
            return item
        updates = ["status", "ai_fields", "updated_at"]
        if item.company_id is None and result.company is not None:
            item.company = result.company
            updates.append("company")
        if item.document_type_id is None and result.document_type is not None:
            item.document_type = result.document_type
            updates.append("document_type")
        if not item.period_label and result.period_label:
            item.period_label = result.period_label
            updates.append("period_label")
        if not item.counterparty_token and result.counterparty_token:
            item.counterparty_token = result.counterparty_token
            updates.append("counterparty_token")
        if not item.final_name and result.final_name:
            item.final_name = result.final_name
            updates.append("final_name")
        item.ai_fields = result.evidence
        item.transition_to(TriageStatus.AWAITING_REVIEW)
        item.save(update_fields=updates)
        found = ", ".join(result.evidence) or "nenhum campo"
        TriageEvent.objects.create(
            organization=item.organization,
            triage_item=item,
            from_status=TriageStatus.EXTRACTING,
            to_status=item.status,
            note=f"Sugestão automática: {found}. Revisão humana necessária",
        )
    from apps.hub.module_activities import sync_triage_activity

    sync_triage_activity(item.pk)
    return item
