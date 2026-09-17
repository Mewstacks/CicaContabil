"""Safe, dependency-free OFX normalization for the reconciliation workflow."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import (
    AccountingEntry,
    BankStatementImport,
    BankTransaction,
    ClientCompany,
    DominioBankEntry,
    ReconciliationMatch,
)
from apps.organizations.models import Organization

_TAG_VALUE = re.compile(r"<(?P<tag>[A-Z0-9_]+)>(?P<value>[^<\r\n]+)", re.IGNORECASE)
_TRANSACTION_START = re.compile(r"<STMTTRN(?:\s[^>]*)?>", re.IGNORECASE)
_MAX_TRANSACTIONS = 10_000


class OfxParseError(ValueError):
    """Raised when a submitted file is not a bounded, usable OFX statement."""


@dataclass(frozen=True)
class ParsedTransaction:
    external_id: str
    occurred_on: date
    description: str
    amount_cents: int


@dataclass(frozen=True)
class ParsedStatement:
    account_reference: str
    transactions: tuple[ParsedTransaction, ...]


def _tags(fragment: str) -> dict[str, str]:
    return {match["tag"].upper(): match["value"].strip() for match in _TAG_VALUE.finditer(fragment)}


def _date(value: str) -> date:
    try:
        return datetime.strptime(value[:8], "%Y%m%d").date()
    except ValueError as exc:
        raise OfxParseError("OFX sem data válida em uma transação.") from exc


def _cents(value: str) -> int:
    try:
        amount = Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise OfxParseError("OFX sem valor válido em uma transação.") from exc
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_ofx(content: bytes) -> ParsedStatement:
    """Parse OFX 1.x/2.x transaction tags without retaining the source file."""

    text = content.decode("utf-8", errors="replace")
    if "OFX" not in text.upper():
        raise OfxParseError("Envie um arquivo OFX válido.")
    header = _tags(text)
    account_reference = ":".join(
        value for value in (header.get("BANKID", ""), header.get("ACCTID", "")) if value
    )[:160]
    starts = list(_TRANSACTION_START.finditer(text))
    if not starts:
        raise OfxParseError("O OFX não contém transações bancárias.")
    if len(starts) > _MAX_TRANSACTIONS:
        raise OfxParseError("O OFX excede o limite de 10.000 transações.")
    transactions: list[ParsedTransaction] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        row = _tags(text[start.end() : end])
        date = row.get("DTPOSTED", "")
        amount = row.get("TRNAMT", "")
        description = " ".join(
            value for value in (row.get("NAME", ""), row.get("MEMO", "")) if value
        )
        if not date or not amount or not description:
            raise OfxParseError("Cada transação OFX precisa de data, valor e descrição.")
        external_id = (
            row.get("FITID")
            or hashlib.sha256(f"{date}|{amount}|{description}|{index}".encode()).hexdigest()
        )
        transactions.append(
            ParsedTransaction(
                external_id=external_id[:160],
                occurred_on=_date(date),
                description=description[:500],
                amount_cents=_cents(amount),
            )
        )
    return ParsedStatement(account_reference=account_reference, transactions=tuple(transactions))


def import_ofx(
    *,
    organization: Organization,
    company: ClientCompany,
    filename: str,
    content: bytes,
    actor: object = None,
    request: object = None,
) -> tuple[BankStatementImport, bool]:
    """Store only normalized transactions; a duplicate upload is harmless."""

    if company.organization_id != organization.id:
        raise ValueError("Empresa não pertence ao escritório informado.")
    statement = parse_ofx(content)
    content_hash = hashlib.sha256(content).hexdigest()
    with transaction.atomic():
        existing = BankStatementImport.objects.filter(
            organization=organization, company=company, content_hash=content_hash
        ).first()
        if existing is not None:
            return existing, False
        imported = BankStatementImport.objects.create(
            organization=organization,
            company=company,
            original_filename=filename[:255],
            content_hash=content_hash,
            account_reference=statement.account_reference,
            transaction_count=len(statement.transactions),
            imported_by=actor if isinstance(actor, User) else None,
        )
        BankTransaction.objects.bulk_create(
            [
                BankTransaction(
                    organization=organization,
                    statement=imported,
                    external_id=item.external_id,
                    occurred_on=item.occurred_on,
                    description=item.description,
                    amount_cents=item.amount_cents,
                )
                for item in statement.transactions
            ]
        )
        record_event(
            action="hub.reconciliation.ofx_imported",
            actor=actor,
            organization=organization,
            target=imported,
            request=request,
            metadata={"transactions": len(statement.transactions)},
        )
    rebuild_reconciliation_matches(organization=organization, company=company)
    return imported, True


def rebuild_reconciliation_matches(
    *, organization: Organization, company: ClientCompany | None = None
) -> None:
    """Only auto-match one exact Domínio bank item; every other case stays reviewable."""
    transactions = BankTransaction.objects.filter(organization=organization).select_related(
        "statement"
    )
    if company is not None:
        transactions = transactions.filter(statement__company=company)
    for transaction_item in transactions.iterator():
        existing = ReconciliationMatch.objects.filter(transaction=transaction_item).first()
        if existing is not None and existing.is_manual and (
            existing.dominio_entry_id or existing.accounting_entry_id
        ):
            continue
        candidates = AccountingEntry.objects.filter(
            organization=organization,
            company_id=transaction_item.statement.company_id,
            occurred_on=transaction_item.occurred_on,
            amount_cents=abs(transaction_item.amount_cents),
        ).order_by("id")
        count = candidates.count()
        legacy_candidates = DominioBankEntry.objects.none()
        if count == 0:
            legacy_candidates = DominioBankEntry.objects.filter(
                organization=organization,
                company_id=transaction_item.statement.company_id,
                occurred_on=transaction_item.occurred_on,
                amount_cents=abs(transaction_item.amount_cents),
            ).order_by("id")
        legacy_count = legacy_candidates.count()
        if count or legacy_count:
            # Value and date are only a suggestion. An operator confirms every
            # candidate after comparing the source evidence.
            status = ReconciliationMatch.Status.AMBIGUOUS
            entry = None
            dominio_entry = None
        else:
            status = ReconciliationMatch.Status.UNMATCHED
            entry = None
            dominio_entry = None
        ReconciliationMatch.objects.update_or_create(
            organization=organization,
            transaction=transaction_item,
            defaults={
                "status": status,
                "accounting_entry": entry,
                "dominio_entry": dominio_entry,
                "is_manual": False,
                "resolved_by": None,
                "resolved_at": None,
            },
        )


def confirm_reconciliation_match(
    *,
    match: ReconciliationMatch,
    dominio_entry: DominioBankEntry | None = None,
    accounting_entry: AccountingEntry | None = None,
    actor: object = None,
    request: object = None,
) -> ReconciliationMatch:
    """Confirm one compatible candidate and prevent later sync from replacing the decision."""
    transaction_item = match.transaction
    if (dominio_entry is None) == (accounting_entry is None):
        raise ValueError("Escolha exatamente um lançamento contábil para confirmar.")
    selected_entry = dominio_entry or accounting_entry
    assert selected_entry is not None
    if (
        selected_entry.organization_id != match.organization_id
        or selected_entry.company_id != transaction_item.statement.company_id
        or selected_entry.occurred_on != transaction_item.occurred_on
        or selected_entry.amount_cents != abs(transaction_item.amount_cents)
    ):
        raise ValueError("O item escolhido não corresponde a esta transação.")
    with transaction.atomic():
        locked = ReconciliationMatch.objects.select_for_update().get(id=match.id)
        locked.dominio_entry = dominio_entry
        locked.accounting_entry = accounting_entry
        locked.status = ReconciliationMatch.Status.MATCHED
        locked.is_manual = True
        locked.resolved_by = actor if isinstance(actor, User) else None
        locked.resolved_at = timezone.now()
        locked.save(
            update_fields=[
                "dominio_entry",
                "accounting_entry",
                "status",
                "is_manual",
                "resolved_by",
                "resolved_at",
                "updated_at",
            ]
        )
        record_event(
            action="hub.reconciliation.match_confirmed",
            actor=actor,
            organization=locked.organization,
            target=locked,
            request=request,
            metadata={
                "source_kind": "dominio" if dominio_entry is not None else "accounting",
                "source_entry_id": str(selected_entry.id),
            },
        )
    return locked
