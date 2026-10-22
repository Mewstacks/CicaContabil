"""Achados da conferência: o contrato entre os comparadores, o banco e os relatórios."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any, Protocol

# status
DIVERGENT = "divergent"
IGNORED = "ignored"
INFO = "info"


class Kind:
    VALOR_DIVERGENTE = "valor_divergente"
    SEM_XML = "sem_xml"
    XML_NAO_ESCRITURADO = "xml_nao_escriturado"
    SITUACAO_DIVERGENTE = "situacao_divergente"
    CHAVE_DUPLICADA = "chave_duplicada"
    CHAVE_INVALIDA = "chave_invalida"
    SOMENTE_1 = "somente_1"
    SOMENTE_2 = "somente_2"
    ANALITICO_SOMENTE_1 = "analitico_somente_1"
    ANALITICO_SOMENTE_2 = "analitico_somente_2"
    ANALITICO_VALOR = "analitico_valor"
    ICMS51_CHAVE = "icms51_chave"
    ICMS51_ARITMETICA = "icms51_aritmetica"
    UF_DIVERGENTE = "uf_divergente"
    AUSENTE_DOMINIO = "ausente_dominio"
    SEM_UF_XML = "sem_uf_xml"


class RunCancelled(Exception):
    """O usuário pediu para parar; o motor interrompe no próximo ponto seguro."""


@dataclass(frozen=True, slots=True)
class Finding:
    kind: str
    status: str
    doc_key: str
    doc_type: str
    number: str = ""
    field: str = ""
    field_label: str = ""
    left_cents: int | None = None
    right_cents: int | None = None
    left_text: str = ""
    right_text: str = ""
    cfop: str = ""
    operation: str = ""
    message: str = ""
    detail: dict[str, Any] = dataclass_field(default_factory=dict)

    @property
    def delta_cents(self) -> int | None:
        if self.left_cents is None or self.right_cents is None:
            return None
        return self.left_cents - self.right_cents


@dataclass(frozen=True, slots=True)
class MatchedRow:
    """Linha que conferiu: vai só para a folha "Conferem" do relatório, nunca para o banco."""

    doc_key: str
    doc_type: str
    number: str
    operation: str
    cfop: str
    values: dict[str, tuple[int | None, int | None]] = dataclass_field(default_factory=dict)


class Sink(Protocol):
    """Quem recebe o resultado. O motor não sabe se é o banco, um arquivo ou um teste."""

    def finding(self, finding: Finding) -> None: ...

    def matched(self, row: MatchedRow) -> None: ...

    def progress(self, stage: str, done: int, total: int | None = None) -> None: ...

    def cancelled(self) -> bool: ...


class CollectingSink:
    """Sink de memória, para teste e para conferências pequenas."""

    def __init__(self, *, keep_matched: bool = True) -> None:
        self.findings: list[Finding] = []
        self.matched_rows: list[MatchedRow] = []
        self.progress_log: list[tuple[str, int, int | None]] = []
        self.cancel = False
        self._keep_matched = keep_matched

    def finding(self, finding: Finding) -> None:
        self.findings.append(finding)

    def matched(self, row: MatchedRow) -> None:
        if self._keep_matched:
            self.matched_rows.append(row)

    def progress(self, stage: str, done: int, total: int | None = None) -> None:
        self.progress_log.append((stage, done, total))

    def cancelled(self) -> bool:
        return self.cancel

    def by_kind(self, kind: str) -> list[Finding]:
        return [item for item in self.findings if item.kind == kind]
