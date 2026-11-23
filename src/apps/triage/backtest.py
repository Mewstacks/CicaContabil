"""Backtest of the engine over a labelled set: accuracy of what it answered, and coverage.

Rows are plain dicts (name, text, optional subject, body, sender, original_sender) with the
expected answers (company as Domínio code or CNPJ, type code, period AAAA-MM). Nothing is
stored: the engine runs over an unsaved item with the office's own companies, types and
learned links. No external service.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from apps.common.cnpj import normalize_cnpj
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage.extraction import suggest_text
from apps.triage.models import TriageItem

FIELDS = ("company", "type", "period")


@dataclass
class FieldStats:
    total: int = 0
    answered: int = 0
    correct: int = 0

    @property
    def accuracy(self) -> float:
        return self.correct / self.answered if self.answered else 0.0

    @property
    def coverage(self) -> float:
        return self.answered / self.total if self.total else 0.0


@dataclass
class BacktestReport:
    fields: dict[str, FieldStats] = field(default_factory=lambda: {k: FieldStats() for k in FIELDS})
    wrong_company: int = 0
    rows: int = 0


def _same_company(company: ClientCompany, expected: str) -> bool:
    expected = expected.strip()
    if not expected:
        return False
    if company.dominio_code and company.dominio_code.casefold() == expected.casefold():
        return True
    try:
        return normalize_cnpj(company.cnpj_masked) == normalize_cnpj(expected)
    except Exception:
        return False


def run_backtest(organization: Organization, rows: Iterable[Mapping[str, Any]]) -> BacktestReport:
    report = BacktestReport()
    for row in rows:
        report.rows += 1
        item = TriageItem(
            organization=organization,
            original_name=str(row.get("name", "documento"))[:255],
            subject=str(row.get("subject", ""))[:500],
            body_excerpt=str(row.get("body", ""))[:6000],
            sender=str(row.get("sender", ""))[:255],
            original_sender=str(row.get("original_sender", ""))[:254],
        )
        result = suggest_text(item, str(row.get("text", "")))
        expected = row.get("expected") or {}
        answers = {
            "company": (
                result.company is not None,
                result.company is not None
                and _same_company(result.company, str(expected.get("company", ""))),
            ),
            "type": (
                result.document_type is not None,
                result.document_type is not None
                and result.document_type.code == expected.get("type"),
            ),
            "period": (bool(result.period_label), result.period_label == expected.get("period")),
        }
        for key, (answered, correct) in answers.items():
            stats = report.fields[key]
            stats.total += 1
            stats.answered += int(answered)
            stats.correct += int(answered and correct)
        if answers["company"][0] and not answers["company"][1]:
            report.wrong_company += 1
    return report
