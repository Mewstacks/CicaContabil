from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class ModulePrice:
    code: str
    label: str
    monthly_cents: int
    usage_note: str = ""


@dataclass(frozen=True)
class SubscriptionQuote:
    module_subtotal_cents: int
    discount_percent: int
    company_multiplier: Decimal
    monthly_cents: int


MODULE_PRICES: tuple[ModulePrice, ...] = (
    ModulePrice("nfse", "NFS-e Inteligente", 16_900),
    ModulePrice("guides", "Guias e DCTFWeb", 9_900),
    ModulePrice("integra", "Central Integra Contador", 7_900, "Consumo cobrado separadamente"),
    ModulePrice("reconciliation", "Conciliação OFX", 12_900),
    ModulePrice("reform", "Radar Reforma", 5_900),
    ModulePrice("journey", "Jornadas", 15_900),
    ModulePrice("ai", "Copiloto CICA", 24_900),
    ModulePrice("triage", "Triagem de Arquivos", 14_900),
)
MODULE_PRICE_BY_CODE = {item.code: item for item in MODULE_PRICES}


def discount_percent(module_count: int) -> int:
    if module_count >= len(MODULE_PRICES):
        return 25
    if module_count >= 4:
        return 20
    if module_count == 3:
        return 15
    if module_count == 2:
        return 10
    return 0


def company_multiplier(company_count: int) -> Decimal:
    if company_count < 1:
        raise ValueError("Informe ao menos uma empresa.")
    if company_count <= 20:
        return Decimal("1.00")
    if company_count <= 50:
        return Decimal("1.34")
    return Decimal("1.82")


def quote_subscription(*, module_codes: list[str], company_count: int) -> SubscriptionQuote:
    unique_codes = list(dict.fromkeys(module_codes))
    if not unique_codes or any(code not in MODULE_PRICE_BY_CODE for code in unique_codes):
        raise ValueError("Escolha ao menos um módulo válido.")
    subtotal = sum(MODULE_PRICE_BY_CODE[code].monthly_cents for code in unique_codes)
    discount = discount_percent(len(unique_codes))
    multiplier = company_multiplier(company_count)
    monthly = (Decimal(subtotal) * (Decimal(100 - discount) / Decimal(100)) * multiplier).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return SubscriptionQuote(subtotal, discount, multiplier, int(monthly))
