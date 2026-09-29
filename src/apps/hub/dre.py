"""Versionable, source-neutral DRE calculation without hidden account classification."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DreMapping:
    account_code: str
    group: str
    sign: int

    def __post_init__(self) -> None:
        if self.sign not in {-1, 1}:
            raise ValueError("O sinal do mapeamento DRE deve ser 1 ou -1.")


@dataclass(frozen=True)
class DreResult:
    groups_cents: dict[str, int]
    unmapped_account_codes: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.unmapped_account_codes

    @property
    def result_cents(self) -> int:
        return sum(self.groups_cents.values())


def calculate_dre(
    *, balances_cents: dict[str, int], mappings: list[DreMapping]
) -> DreResult:
    """Apply explicit account mappings; never infer an unmapped balance's DRE group."""

    mapping_by_code = {mapping.account_code: mapping for mapping in mappings}
    groups: dict[str, int] = {}
    unmapped: list[str] = []
    for account_code, balance in balances_cents.items():
        mapping = mapping_by_code.get(account_code)
        if mapping is None:
            unmapped.append(account_code)
            continue
        groups[mapping.group] = groups.get(mapping.group, 0) + balance * mapping.sign
    return DreResult(groups_cents=groups, unmapped_account_codes=tuple(sorted(unmapped)))
