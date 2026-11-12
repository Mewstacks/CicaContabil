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
    DataSource,
    DominioBankEntry,
    FinancialAccount,
    NormalizedMovement,
    OfxTransactionIdentity,
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
        if not amount.is_finite() or not amount or abs(amount) > Decimal("92233720368547758.07"):
            raise InvalidOperation
        cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if not cents:
            raise InvalidOperation
        return cents
    except InvalidOperation as exc:
        raise OfxParseError("OFX sem valor válido em uma transação.") from exc


def parse_ofx(content: bytes) -> ParsedStatement:
    """Parse OFX 1.x/2.x transaction tags without retaining the source file."""

    text = content.decode("utf-8", errors="replace")
    if "OFX" not in text.upper():
        raise OfxParseError("Envie um arquivo OFX válido.")
    header = _tags(text)
    if (
        not header.get("BANKID")
        or not header.get("ACCTID")
        or len(re.findall(r"<ACCTID>", text, re.IGNORECASE)) != 1
    ):
        raise OfxParseError("O OFX precisa identificar um único banco e uma única conta.")
    account_reference = ":".join(
        value
        for value in (header.get("BANKID", ""), header.get("BRANCHID", ""), header["ACCTID"])
        if value
    )
    if len(account_reference) > 160:
        raise OfxParseError("A identificação da conta OFX excede o limite suportado.")
    starts = list(_TRANSACTION_START.finditer(text))
    if not starts:
        raise OfxParseError("O OFX não contém transações bancárias.")
    if len(starts) > _MAX_TRANSACTIONS:
        raise OfxParseError("O OFX excede o limite de 10.000 transações.")
    transactions: list[ParsedTransaction] = []
    identifiers: set[str] = set()
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
        external_id = row.get("FITID", "")
        if not external_id or len(external_id) > 160 or external_id in identifiers:
            raise OfxParseError(
                "Cada transação OFX precisa de FITID único, com até 160 caracteres."
            )
        identifiers.add(external_id)
        transactions.append(
            ParsedTransaction(
                external_id=external_id[:160],
                occurred_on=_date(date),
                description=description[:500],
                amount_cents=_cents(amount),
            )
        )
    return ParsedStatement(account_reference=account_reference, transactions=tuple(transactions))


def validate_ofx_account(
    statement: ParsedStatement,
    *,
    organization: Organization,
    company: ClientCompany,
    financial_account: FinancialAccount | None,
) -> None:
    if financial_account is not None and (
        financial_account.organization_id != organization.pk
        or financial_account.company_id != company.pk
        or not financial_account.active
        or financial_account.account_reference.strip() != statement.account_reference
    ):
        raise OfxParseError(
            "A conta informada pelo OFX não corresponde à conta financeira selecionada."
        )


@transaction.atomic
def claim_ofx_transactions(
    *, organization: Organization, company: ClientCompany, statement: ParsedStatement, digest: str
) -> None:
    """Serialize both intake paths; reject overlapping files atomically, including old rows."""
    ClientCompany.objects.select_for_update().get(pk=company.pk, organization=organization)
    identifiers = [item.external_id for item in statement.transactions]
    legacy_overlap = BankTransaction.objects.filter(
        organization=organization,
        statement__company=company,
        statement__account_reference=statement.account_reference,
        external_id__in=identifiers,
    ).exclude(statement__content_hash=digest)
    movement_overlap = NormalizedMovement.objects.filter(
        organization=organization,
        company=company,
        source_reference__account=statement.account_reference,
        source_key__in=[f"ofx:{identifier}" for identifier in identifiers],
    ).exclude(source_file__content_hash=digest)
    claims = OfxTransactionIdentity.objects.filter(
        organization=organization, company=company, account_reference=statement.account_reference
    )
    if (
        legacy_overlap.exists()
        or movement_overlap.exists()
        or claims.filter(external_id__in=identifiers).exclude(content_hash=digest).exists()
    ):
        raise OfxParseError(
            "Este OFX contém transações já recebidas em outro arquivo desta conta. "
            "Confira o original e envie um intervalo sem sobreposição; nenhuma linha foi importada."
        )
    claimed = set(claims.filter(external_id__in=identifiers).values_list("external_id", flat=True))
    OfxTransactionIdentity.objects.bulk_create(
        [
            OfxTransactionIdentity(
                organization=organization,
                company=company,
                account_reference=statement.account_reference,
                external_id=identifier,
                content_hash=digest,
            )
            for identifier in identifiers
            if identifier not in claimed
        ]
    )


def import_ofx(
    *,
    organization: Organization,
    company: ClientCompany,
    filename: str,
    content: bytes,
    financial_account: FinancialAccount | None = None,
    actor: object = None,
    request: object = None,
) -> tuple[BankStatementImport, bool]:
    """Store only normalized transactions; a duplicate upload is harmless."""

    if company.organization_id != organization.id:
        raise ValueError("Empresa não pertence ao escritório informado.")
    statement = parse_ofx(content)
    validate_ofx_account(
        statement, organization=organization, company=company, financial_account=financial_account
    )
    content_hash = hashlib.sha256(content).hexdigest()
    with transaction.atomic():
        claim_ofx_transactions(
            organization=organization, company=company, statement=statement, digest=content_hash
        )
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
    """Suggest independent, compatible candidates; confirmation remains a separate decision."""
    companies = (
        ClientCompany.objects.filter(
            organization=organization, bank_statement_imports__transactions__isnull=False
        )
        .distinct()
        .order_by("pk")
    )
    if company is not None:
        companies = companies.filter(pk=company.pk)
    for selected_company in companies:
        _rebuild_company_matches(organization=organization, company=selected_company)


@transaction.atomic
def _rebuild_company_matches(*, organization: Organization, company: ClientCompany) -> None:
    # Use the same lock order as confirmation. A sync must not erase a human
    # decision made after its first read of the match.
    ClientCompany.objects.select_for_update().get(pk=company.pk, organization=organization)
    transactions = (
        BankTransaction.objects.filter(organization=organization)
        .select_related("statement")
        .filter(statement__company=company)
    )
    for transaction_item in transactions.iterator():
        existing = ReconciliationMatch.objects.filter(transaction=transaction_item).first()
        if (
            existing is not None
            and existing.is_manual
            and (existing.dominio_entry_id or existing.accounting_entry_id)
        ):
            continue
        candidates = (
            AccountingEntry.objects.filter(
                organization=organization,
                company_id=transaction_item.statement.company_id,
                occurred_on=transaction_item.occurred_on,
                amount_cents=abs(transaction_item.amount_cents),
                direction="inflow" if transaction_item.amount_cents > 0 else "outflow",
                account_reference=transaction_item.statement.account_reference,
            )
            .exclude(
                data_source__kind__in=[
                    DataSource.Kind.DOMINIO_LOCAL_AGENT,
                    DataSource.Kind.DOMINIO_WEB_BACKUP,
                ],
                independent_source__isnull=True,
            )
            .exclude(reconciliation_matches__status=ReconciliationMatch.Status.MATCHED)
            .exclude(independent_source__entry__movement_reconciliations__state="confirmed")
            .order_by("id")
        )
        if candidates.exists():
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
        # A later upload to the old view must recover the existing allocation,
        # instead of presenting a second, apparently available bank transaction.
        from apps.hub.reconciliation_bridge import movement_for_legacy, project_confirmed_allocation

        current = ReconciliationMatch.objects.get(transaction=transaction_item)
        movement = movement_for_legacy(current)
        if movement is not None:
            project_confirmed_allocation(movement)


def confirm_reconciliation_match(
    *,
    match: ReconciliationMatch,
    dominio_entry: DominioBankEntry | None = None,
    accounting_entry: AccountingEntry | None = None,
    actor: object = None,
    request: object = None,
) -> ReconciliationMatch:
    """Confirm one compatible candidate and prevent later sync from replacing the decision."""
    if (dominio_entry is None) == (accounting_entry is None):
        raise ValueError("Escolha exatamente um lançamento contábil para confirmar.")
    with transaction.atomic():
        company_id = BankTransaction.objects.get(pk=match.transaction_id).statement.company_id
        ClientCompany.objects.select_for_update().get(
            pk=company_id, organization_id=match.organization_id
        )
        locked = ReconciliationMatch.objects.select_for_update().get(id=match.id)
        transaction_item = locked.transaction
        if dominio_entry is not None:
            raise ValueError("O espelho de extrato Domínio não comprova um lançamento do Razão.")
        assert accounting_entry is not None
        selected_entry = AccountingEntry.objects.select_for_update().get(pk=accounting_entry.pk)
        if (
            selected_entry.organization_id != locked.organization_id
            or selected_entry.data_source.organization_id != locked.organization_id
            or selected_entry.company_id != company_id
            or selected_entry.occurred_on != transaction_item.occurred_on
            or selected_entry.amount_cents != abs(transaction_item.amount_cents)
        ):
            raise ValueError("O item escolhido não corresponde a esta transação.")
        if selected_entry.data_source.kind in {
            DataSource.Kind.DOMINIO_LOCAL_AGENT,
            DataSource.Kind.DOMINIO_WEB_BACKUP,
        } and not hasattr(selected_entry, "independent_source"):
            raise ValueError("O espelho de extrato Domínio não comprova um lançamento do Razão.")
        expected_direction = "inflow" if transaction_item.amount_cents > 0 else "outflow"
        if selected_entry.direction != expected_direction:
            raise ValueError(
                "A natureza da fonte precisa estar normalizada e corresponder à transação."
            )
        if (
            not selected_entry.account_reference
            or selected_entry.account_reference != transaction_item.statement.account_reference
        ):
            raise ValueError("A conta da fonte contábil não corresponde à conta do OFX.")
        if (
            BankTransaction.objects.filter(
                organization_id=locked.organization_id,
                statement__company_id=company_id,
                statement__account_reference=transaction_item.statement.account_reference,
                external_id=transaction_item.external_id,
            )
            .exclude(pk=transaction_item.pk)
            .exists()
        ):
            raise ValueError(
                "Esta transação está duplicada no histórico; confira os arquivos de origem."
            )
        if (
            ReconciliationMatch.objects.filter(
                accounting_entry=selected_entry, status=ReconciliationMatch.Status.MATCHED
            )
            .exclude(pk=locked.pk)
            .exists()
        ):
            raise ValueError("Este lançamento já foi utilizado em outra conciliação.")
        if locked.status == ReconciliationMatch.Status.MATCHED:
            if locked.accounting_entry_id == selected_entry.pk and locked.is_manual:
                return locked
            raise ValueError("Esta transação já possui uma confirmação; a decisão foi preservada.")
        from apps.hub.models import IndependentLedgerRecord
        from apps.hub.reconciliation_bridge import movement_for_legacy
        from apps.hub.reconciliation_service import confirm_reconciliation

        try:
            record = selected_entry.independent_source
        except IndependentLedgerRecord.DoesNotExist:
            record = None
        if record is not None:
            movement = movement_for_legacy(locked)
            if movement is None:
                raise ValueError(
                    "Processe o mesmo OFX na importação de movimentos antes de confirmar o Razão."
                )
            confirm_reconciliation(
                movement=movement,
                entry=record.entry,
                amount_cents=selected_entry.amount_cents,
                evidence={
                    "method": "reviewed_independent_ledger",
                    "legacy_match": str(locked.pk),
                    "source_file": str(record.source_file_id),
                    "source_hash": record.source_file.content_hash,
                    "source_key": record.external_key,
                },
                actor=actor if isinstance(actor, User) else None,
            )
        else:
            movement = movement_for_legacy(locked)
            if movement is not None:
                movement = type(movement).objects.select_for_update().get(pk=movement.pk)
                from apps.hub.models import JournalEntry

                if movement.journal_entries.filter(state=JournalEntry.State.EXPORTED).exists():
                    raise ValueError(
                        "O movimento já foi exportado; confira a importação e a retificação."
                    )
                movement.journal_entries.filter(
                    state__in=[JournalEntry.State.DRAFT, JournalEntry.State.APPROVED]
                ).update(state=JournalEntry.State.INVALID, updated_at=timezone.now())
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
