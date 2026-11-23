"""D-384: rank the chart accounts most likely to be the bank account of an OFX.

Only a suggestion for the human link review: nothing is linked or stored here.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

# Brazilian bank codes (COMPE) and the words that usually name them in charts of accounts.
BANK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "1": ("BANCO DO BRASIL", "BCO DO BRASIL", "BCO BRASIL", "B DO BRASIL", "BB"),
    "33": ("SANTANDER",),
    "41": ("BANRISUL",),
    "70": ("BRB",),
    "77": ("INTER",),
    "85": ("AILOS", "CECRED", "VIACREDI"),
    "97": ("CREDISIS",),
    "104": ("CAIXA ECONOMICA", "CAIXA FEDERAL", "CEF"),
    "133": ("CRESOL",),
    "136": ("UNICRED",),
    "197": ("STONE",),
    "208": ("BTG",),
    "212": ("ORIGINAL",),
    "237": ("BRADESCO",),
    "260": ("NUBANK", "NU PAGAMENTOS"),
    "290": ("PAGSEGURO", "PAGBANK"),
    "323": ("MERCADO PAGO",),
    "336": ("C6",),
    "341": ("ITAU",),
    "380": ("PICPAY",),
    "389": ("MERCANTIL",),
    "403": ("CORA",),
    "422": ("SAFRA",),
    "655": ("VOTORANTIM", "NEON"),
    "745": ("CITIBANK",),
    "748": ("SICREDI",),
    "756": ("SICOOB", "BANCOOB"),
}
NOT_CHECKING = (
    "APLICAC",
    "INVEST",
    "EMPREST",
    "FINANC",
    "JUROS",
    "CAPITAL",
    "OUROCAP",
    "COTA",
    "INTEGRALIZ",
    "CONTRATO",
    "PRONAMPE",
    "LEASING",
    "COMPROMISS",
    "JUDICIAL",
    "CREDITO",
    "CONSORCIO",
    "PARCELAMENTO",
    "TITULO",
)


def plain(text: object) -> str:
    folded = unicodedata.normalize("NFKD", str(text or ""))
    return " ".join("".join(c for c in folded if not unicodedata.combining(c)).upper().split())


def bank_keywords(bank_id: str) -> tuple[str, ...]:
    code = bank_id.strip().lstrip("0") or "0"
    return BANK_KEYWORDS.get(code, ())


def _account_digits(account_id: str) -> set[str]:
    digits = re.sub(r"\D", "", account_id).lstrip("0")
    keys = {digits} if len(digits) >= 4 else set()
    if len(digits) >= 5:
        keys.add(digits[:-1])  # without the check digit
    return keys


@dataclass(frozen=True)
class Suggestion:
    account: Any
    score: int
    reasons: tuple[str, ...]


def _bank_group_prefixes(rows: Iterable[tuple[Any, dict[str, Any]]]) -> set[tuple[int, str]]:
    prefixes = set()
    for account, row in rows:
        name = plain(row.get("account_name_raw"))
        classification = str(row.get("classification_raw") or "").strip()
        if (
            str(row.get("account_type_raw") or "").strip() == "S"
            and "BANC" in name
            and classification
            and not any(word in name for word in NOT_CHECKING)
        ):
            prefixes.add((account.chart_company_code, classification))
    return prefixes


def suggest_accounts(
    accounts: Iterable[Any], *, bank_id: str, account_id: str, limit: int = 5
) -> list[Suggestion]:
    """Rank analytic, non-inactive chart accounts for one OFX bank identity."""

    rows = [(account, account.row or {}) for account in accounts]
    groups = _bank_group_prefixes(rows)
    keywords = bank_keywords(bank_id)
    numbers = _account_digits(account_id)
    ranked = []
    for account, row in rows:
        if str(row.get("account_type_raw") or "").strip() == "S":
            continue
        if str(row.get("account_status_raw") or "").strip() == "I":
            continue
        name = plain(row.get("account_name_raw"))
        classification = str(row.get("classification_raw") or "").strip()
        if any(word in name for word in NOT_CHECKING):
            continue
        score, reasons = 0, []
        in_group = any(
            plan == account.chart_company_code
            and classification.startswith(prefix)
            and classification != prefix
            for plan, prefix in groups
        )
        if not in_group and not re.sub(r"\D", "", classification).startswith("1"):
            continue
        if in_group:
            score += 10
            reasons.append("Está no grupo de bancos do plano")
        padded = " " + " ".join(re.sub(r"[^A-Z0-9]", " ", name).split()) + " "
        if keywords and any(f" {word} " in padded for word in keywords):
            score += 50
            reasons.append("O nome corresponde ao banco do extrato")
        name_digits = re.sub(r"\D", "", name)
        if numbers and any(number in name_digits for number in numbers):
            score += 30
            reasons.append("O nome contém o número da conta do extrato")
        if score and (in_group or score >= 30):
            ranked.append(Suggestion(account=account, score=score, reasons=tuple(reasons)))
    ranked.sort(
        key=lambda item: (
            -item.score,
            str((item.account.row or {}).get("classification_raw") or ""),
            item.account.account_code,
        )
    )
    return ranked[:limit]


def suggested_inflow_side(row: dict[str, Any]) -> str:
    """Asset accounts (classification starting with 1) usually receive bank inflows as debit."""

    classification = re.sub(r"\D", "", str(row.get("classification_raw") or ""))
    return "debit" if classification.startswith("1") else ""
