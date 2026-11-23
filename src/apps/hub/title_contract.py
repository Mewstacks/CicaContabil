"""Local normalized title contract; deliberately disconnected from ERP SQL and posting."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

CONTRACT = "titles-normalized-v1"
MAX_CENTS = 9223372036854775807
MAX_ITEMS = 100_000


class TitleContractError(ValueError):
    pass


@dataclass(frozen=True)
class Settlement:
    key: str
    posted_on: date
    principal_cents: int
    interest_cents: int
    penalty_cents: int
    fees_cents: int
    discount_cents: int
    cash_cents: int
    direction: str
    reverses: str | None


@dataclass(frozen=True)
class Installment:
    key: str
    due_on: date | None
    principal_cents: int
    outstanding_cents: int | None
    settlements: tuple[Settlement, ...]


@dataclass(frozen=True)
class Title:
    key: str
    kind: str
    installments: tuple[Installment, ...]


@dataclass(frozen=True)
class TitleSnapshot:
    company_key: str
    account_reference: str
    as_of: date
    settlements_complete: bool
    titles: tuple[Title, ...]
    fingerprint: str


def _object(value: Any, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise TitleContractError("Campos ausentes/desconhecidos no contrato de títulos.")
    return value


def _key(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 160:
        raise TitleContractError("Chave/referência de título inválida.")
    if value != value.strip() or any(ord(char) < 32 for char in value):
        raise TitleContractError("Chave/referência não normalizada.")
    return value


def _day(value: Any) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise TitleContractError("Data ISO explícita obrigatória.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise TitleContractError("Data inválida no contrato de títulos.") from exc


def _cents(value: Any, *, positive: bool = False) -> int:
    if type(value) is not int or not (1 if positive else 0) <= value <= MAX_CENTS:
        raise TitleContractError("Centavos devem ser inteiros explícitos dentro do limite.")
    return value


def _items(value: Any) -> list[Any]:
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise TitleContractError("Lista de títulos/parcelas/baixas inválida ou acima do limite.")
    return value


def validate_title_snapshot(
    payload: Any, *, company_key: str, account_reference: str
) -> TitleSnapshot:
    """Validate the entire snapshot without saving or inferring any ERP field.

    A due date is never a payment. Unknown balance stays None. Completeness is
    declared by the reviewed adapter, not inferred from an empty settlement list.
    """
    root = _object(
        payload,
        {"contract", "company_key", "account_reference", "as_of", "settlements_complete", "titles"},
    )
    if (
        root["contract"] != CONTRACT
        or _key(root["company_key"]) != company_key
        or _key(root["account_reference"]) != account_reference
        or type(root["settlements_complete"]) is not bool
    ):
        raise TitleContractError("Contrato, empresa, conta ou cobertura de baixas incompatíveis.")
    as_of = _day(root["as_of"])
    titles = []
    seen_titles: set[str] = set()
    count = 0
    canonical_titles = []
    for raw_title in _items(root["titles"]):
        item = _object(raw_title, {"key", "kind", "installments"})
        title_key = _key(item["key"])
        if (
            title_key in seen_titles
            or not isinstance(item["kind"], str)
            or item["kind"] not in {"payable", "receivable"}
        ):
            raise TitleContractError("Título repetido ou natureza não normalizada.")
        seen_titles.add(title_key)
        installments = []
        seen_installments: set[str] = set()
        canonical_installments = []
        for raw_installment in _items(item["installments"]):
            part = _object(
                raw_installment,
                {"key", "due_on", "principal_cents", "outstanding_cents", "settlements"},
            )
            part_key = _key(part["key"])
            if part_key in seen_installments:
                raise TitleContractError("Parcela repetida no título.")
            seen_installments.add(part_key)
            principal = _cents(part["principal_cents"], positive=True)
            outstanding = part["outstanding_cents"]
            if outstanding is not None and _cents(outstanding) > principal:
                raise TitleContractError("Saldo de parcela excede o principal.")
            due_on = None if part["due_on"] is None else _day(part["due_on"])
            settlements: dict[str, Settlement] = {}
            for raw_settlement in _items(part["settlements"]):
                row = _object(
                    raw_settlement,
                    {
                        "key",
                        "posted_on",
                        "principal_cents",
                        "interest_cents",
                        "penalty_cents",
                        "fees_cents",
                        "discount_cents",
                        "cash_cents",
                        "direction",
                        "reverses",
                    },
                )
                key = _key(row["key"])
                amounts = {
                    name: _cents(row[name])
                    for name in (
                        "principal_cents",
                        "interest_cents",
                        "penalty_cents",
                        "fees_cents",
                        "discount_cents",
                        "cash_cents",
                    )
                }
                expected = (
                    sum(
                        amounts[k]
                        for k in (
                            "principal_cents",
                            "interest_cents",
                            "penalty_cents",
                            "fees_cents",
                        )
                    )
                    - amounts["discount_cents"]
                )
                reversal = None if row["reverses"] is None else _key(row["reverses"])
                direction = "outflow" if item["kind"] == "payable" else "inflow"
                if reversal:
                    direction = "inflow" if direction == "outflow" else "outflow"
                posted_on = _day(row["posted_on"])
                if (
                    key in settlements
                    or amounts["cash_cents"] <= 0
                    or expected != amounts["cash_cents"]
                    or row["direction"] != direction
                    or posted_on > as_of
                ):
                    raise TitleContractError(
                        "Baixa repetida, futura, com sinal ou valores incoerentes."
                    )
                settlements[key] = Settlement(
                    key=key,
                    posted_on=posted_on,
                    **amounts,
                    direction=row["direction"],
                    reverses=reversal,
                )
            reversed_keys: set[str] = set()
            consumed = 0
            for settlement in settlements.values():
                original = settlements.get(settlement.reverses or "")
                if settlement.reverses:
                    if (
                        original is None
                        or original.reverses
                        or original.key in reversed_keys
                        or settlement.posted_on < original.posted_on
                        or any(
                            getattr(original, field) != getattr(settlement, field)
                            for field in (
                                "principal_cents",
                                "interest_cents",
                                "penalty_cents",
                                "fees_cents",
                                "discount_cents",
                                "cash_cents",
                            )
                        )
                    ):
                        raise TitleContractError(
                            "Estorno exige baixa original e reversão integral única."
                        )
                    reversed_keys.add(original.key)
                consumed += settlement.principal_cents * (-1 if settlement.reverses else 1)
            if not 0 <= consumed <= principal:
                raise TitleContractError("Principal baixado excede a capacidade da parcela.")
            if (
                root["settlements_complete"]
                and outstanding is not None
                and outstanding != principal - consumed
            ):
                raise TitleContractError("Saldo informado diverge das baixas completas.")
            if outstanding is not None and consumed > principal - outstanding:
                raise TitleContractError("Baixas excedem o principal liquidado informado.")
            installments.append(
                Installment(
                    key=part_key,
                    due_on=due_on,
                    principal_cents=principal,
                    outstanding_cents=outstanding,
                    settlements=tuple(sorted(settlements.values(), key=lambda x: x.key)),
                )
            )
            canonical_installments.append(
                {**part, "settlements": sorted(part["settlements"], key=lambda x: x["key"])}
            )
            count += 1 + len(settlements)
            if count > MAX_ITEMS:
                raise TitleContractError("Fotografia de títulos excede o limite global.")
        if not installments:
            raise TitleContractError("Título sem parcelas explícitas.")
        titles.append(
            Title(
                key=title_key,
                kind=item["kind"],
                installments=tuple(sorted(installments, key=lambda x: x.key)),
            )
        )
        canonical_titles.append(
            {**item, "installments": sorted(canonical_installments, key=lambda x: x["key"])}
        )
    canonical = {**root, "titles": sorted(canonical_titles, key=lambda x: x["key"])}
    fingerprint = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    return TitleSnapshot(
        company_key=company_key,
        account_reference=account_reference,
        as_of=as_of,
        settlements_complete=root["settlements_complete"],
        titles=tuple(sorted(titles, key=lambda x: x.key)),
        fingerprint=fingerprint,
    )
