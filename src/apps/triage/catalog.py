"""The office's own catalogue of document types: keywords, expectation, destination folder.

Everything here is scoped by office. A type is created, edited and deactivated by the office
itself; the accounting starter set is opt-in (``apply_default_catalog``) and never overwrites
what the office already changed. Matching is deterministic and local: no external service.

Pattern (structure only, no code copied): HubFedrizzi ``triagem/catalogo.py`` and
``services._ranking_de_tipos``; Paperless-ngx (GPL-3.0) document types with matching rules.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from pathlib import PureWindowsPath
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage.models import ChecklistExpectation, DocumentType

MAX_KEYWORDS = 40
MAX_KEYWORD_LENGTH = 60
FOLDER_PLACEHOLDERS = frozenset({"company_name", "dominio_code", "document_type", "period"})

_GLUED = re.compile(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])")
_NON_WORD = re.compile(r"[^a-z0-9]+")


def fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def words(value: str) -> str:
    """Lower, accent-free text where letters and digits are separated and only words remain."""

    return _NON_WORD.sub(" ", _GLUED.sub(" ", fold(value))).strip()


def parse_keywords(raw: str) -> list[str]:
    """Split a typed list on comma, semicolon or newline. Order kept, duplicates dropped."""

    found: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[,;\n\r]+", raw or ""):
        word = " ".join(part.split())[:MAX_KEYWORD_LENGTH]
        key = word.lstrip("@").strip()
        if len(key) < 2 or fold(word) in seen:
            continue
        seen.add(fold(word))
        found.append(word)
        if len(found) == MAX_KEYWORDS:
            break
    return found


def prepare_haystack(value: str) -> tuple[str, str]:
    """(padded words, same without spaces) so OCR-glued phrases still match."""

    padded = f" {words(value)} "
    return padded, padded.replace(" ", "")


def keyword_score(
    keywords: Iterable[object], *, name_subject: str, text: str
) -> tuple[int, list[str]]:
    """Whole-word score: 2 per keyword in the name/subject, 1 in the text.

    ``@word`` counts only in the name and subject: in a document body it shows up everywhere.
    """

    name_h, name_c = prepare_haystack(name_subject)
    text_h, text_c = prepare_haystack(text)

    def found(key: str, padded: str, compact: str) -> bool:
        return f" {key} " in padded or (" " in key and key.replace(" ", "") in compact)

    total = 0
    matched: list[str] = []
    for raw in keywords:
        value = str(raw)
        key = words(value.lstrip("@"))
        if not key:
            continue
        points = 0
        if found(key, name_h, name_c):
            points += 2
        if not value.startswith("@") and found(key, text_h, text_c):
            points += 1
        if points:
            total += points
            matched.append(value.lstrip("@"))
    return total, matched


def validate_folder_template(template: str) -> str:
    """The Windows folder of a type: known placeholders, relative, and per company."""

    template = template.strip()
    fields = set(re.findall(r"{([^{}]+)}", template))
    literal = re.sub(r"{[^{}]+}", "", template)
    path = PureWindowsPath(template)
    if (
        not template
        or fields - FOLDER_PLACEHOLDERS
        or "{" in literal
        or "}" in literal
        or any(char in literal for char in ':*?"<>|')
        or template.startswith(("\\\\", "//"))
        or path.is_absolute()
        or path.drive
        or ".." in path.parts
    ):
        raise ValidationError("Use as variáveis informadas, em pasta relativa.")
    if not ({"company_name", "dominio_code"} & fields):
        raise ValidationError("Inclua a empresa ou o código Domínio na pasta.")
    return template


# code, label, name template, period kind, counterparty kind, keywords, expected for all,
# expected regimes, destination folder (blank: the office's default folder format)
DEFAULT_CATALOG: list[dict[str, Any]] = [
    {
        "code": "extrato", "label": "Extrato bancário",
        "name_template": "{codigo}_EXTRATO_{contraparte}_{periodo}",
        "period_kind": DocumentType.PeriodKind.COMPETENCIA,
        "counterparty_kind": DocumentType.CounterpartyKind.BANCO,
        "keywords": [
            "extrato", "extrato bancario", "extrato de conta", "conta corrente",
            "saldo anterior", "saldo disponivel", "ofx", "stmttrn",
        ],
        "expected_default": True, "expected_regimes": [],
    },
    {
        "code": "nfse", "label": "NFS-e",
        "name_template": "{codigo}_NFSE_{periodo}",
        "period_kind": DocumentType.PeriodKind.COMPETENCIA,
        "keywords": [
            "nfse", "nfs-e", "nota fiscal de servico", "nota fiscal de servicos eletronica",
            "tomador de servicos", "codigo de verificacao",
        ],
    },
    {
        "code": "folha", "label": "Folha de pagamento",
        "name_template": "{codigo}_FOLHA_{periodo}",
        "period_kind": DocumentType.PeriodKind.COMPETENCIA,
        "keywords": [
            "folha de pagamento", "folha", "holerite", "contracheque", "recibo de salario",
            "esocial",
        ],
    },
    {
        "code": "guia", "label": "Guia de imposto",
        "name_template": "{codigo}_GUIA_{periodo}",
        "period_kind": DocumentType.PeriodKind.COMPETENCIA,
        "keywords": [
            "das", "darf", "dae", "gps", "pgdas", "dctfweb", "fgts",
            "documento de arrecadacao", "@guia",
        ],
        "expected_regimes": ["mei", "simples", "presumido", "real"],
    },
    {
        "code": "recibo", "label": "Recibo",
        "name_template": "{codigo}_RECIBO_{periodo}",
        "period_kind": DocumentType.PeriodKind.COMPETENCIA,
        "keywords": ["recibo", "recibo de pagamento", "@recibo"],
    },
    {
        "code": "francesinha", "label": "Francesinha (cobrança)",
        "name_template": "{codigo}_FRANCESINHA_{contraparte}_{periodo}",
        "period_kind": DocumentType.PeriodKind.COMPETENCIA,
        "counterparty_kind": DocumentType.CounterpartyKind.BANCO,
        "keywords": [
            "francesinha", "relatorio de cobranca", "titulos liquidados", "cobranca bancaria",
            "cobranca registrada", "movimento de cobranca", "liquidacao de cobranca",
            "quantidade de titulos",
        ],
    },
    {
        "code": "pix", "label": "Movimentações Pix",
        "name_template": "{codigo}_PIX_{contraparte}_{periodo}",
        "period_kind": DocumentType.PeriodKind.COMPETENCIA,
        "counterparty_kind": DocumentType.CounterpartyKind.BANCO,
        "keywords": ["pix", "movimentacoes pix", "relatorio pix", "pix recebidos", "pix enviados"],
    },
    {
        "code": "fatura-cartao", "label": "Fatura de cartão",
        "name_template": "{codigo}_FATURA_{contraparte}_{periodo}",
        "period_kind": DocumentType.PeriodKind.COMPETENCIA,
        "counterparty_kind": DocumentType.CounterpartyKind.INSTITUICAO,
        "keywords": [
            "fatura", "fatura do cartao", "cartao de credito", "pagamento minimo",
            "limite disponivel", "vencimento da fatura",
        ],
    },
    {
        "code": "comprovante", "label": "Comprovante de pagamento",
        "name_template": "{codigo}_COMPROVANTE_{periodo}",
        "period_kind": DocumentType.PeriodKind.COMPETENCIA,
        "keywords": [
            "comprovante", "comprovante de pagamento", "comprovante de transferencia",
            "autenticacao bancaria", "@pagamento", "@transferencia",
        ],
    },
    {
        "code": "societario", "label": "Societário",
        "name_template": "{codigo}_SOCIETARIO_{periodo}",
        "period_kind": DocumentType.PeriodKind.ANUAL,
        "keywords": [
            "contrato social", "alteracao contratual", "cartao cnpj", "cartao do cnpj",
            "requerimento de empresario", "@alvara", "@procuracao",
        ],
    },
]


def apply_default_catalog(organization: Organization) -> list[str]:
    """Create the starter types this office does not have yet. Returns the created codes.

    Opt-in: only an explicit call (the office's button or command) runs it. A code the office
    already has is left exactly as it is, label, keywords and active flag included.
    """

    have = set(
        DocumentType.objects.filter(organization=organization).values_list("code", flat=True)
    )
    created: list[str] = []
    for row in DEFAULT_CATALOG:
        if row["code"] in have:
            continue
        DocumentType.objects.create(
            organization=organization,
            code=row["code"],
            label=row["label"],
            name_template=row["name_template"],
            folder_template=row.get("folder_template", ""),
            period_kind=row["period_kind"],
            counterparty_kind=row.get("counterparty_kind", DocumentType.CounterpartyKind.NONE),
            keywords=list(row["keywords"]),
            expected_default=bool(row.get("expected_default", False)),
            expected_regimes=list(row.get("expected_regimes", [])),
        )
        created.append(row["code"])
    return created


_NOT_EXPECTED = {
    ChecklistExpectation.Requirement.OPTIONAL,
    ChecklistExpectation.Requirement.WAIVED,
    ChecklistExpectation.Requirement.NOT_APPLICABLE,
}


def expected_for(company: ClientCompany, document_type: DocumentType) -> bool:
    """Is this document expected from this company? The company's own exception wins."""

    if company.organization_id != document_type.organization_id:
        return False
    exception = ChecklistExpectation.objects.filter(
        organization_id=company.organization_id, company=company, document_type=document_type
    ).first()
    if exception is not None:
        return exception.requirement not in _NOT_EXPECTED
    regimes = document_type.expected_regimes or []
    return bool(
        document_type.expected_default
        or (company.tax_regime and company.tax_regime in regimes)
    )


def expected_types_for(company: ClientCompany) -> QuerySet[DocumentType]:
    """Active types of the company's office that it is expected to deliver."""

    types = DocumentType.objects.filter(organization_id=company.organization_id, active=True)
    wanted = [dt.pk for dt in types if expected_for(company, dt)]
    return types.filter(pk__in=wanted)
