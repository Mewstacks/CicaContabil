"""Independent complete journals; normalized file contract, never inferred ERP SQL."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from datetime import date
from typing import Any

from django.db import transaction

from apps.audit.services import record_event
from apps.hub.models import (
    AccountingEntry,
    ClientCompany,
    DataSource,
    IndependentLedgerRecord,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_service import (
    MAX_ROWS,
    ReconciliationError,
    _decode_csv,
    _source_bytes,
)

LEDGER_COLUMNS = (
    "entry_key",
    "line_key",
    "date",
    "history",
    "account_code",
    "side",
    "amount_cents",
    "cash_direction",
    "document",
)


def is_ledger_csv(source: ReconciliationSourceFile) -> bool:
    if source.origin != "accounting" or source.kind != "csv":
        return False
    text = _decode_csv(_source_bytes(source))
    header = next(csv.reader(io.StringIO(text), delimiter=";"), [])
    # A damaged ledger header must fail its contract, never become bank movements.
    return bool({"entry_key", "line_key", "cash_direction"}.intersection(header))


def _rows(source: ReconciliationSourceFile) -> dict[str, list[dict[str, Any]]]:
    content = _source_bytes(source)
    if hashlib.sha256(content).hexdigest() != source.content_hash:
        raise ReconciliationError("Razão: hash do arquivo diverge; restaure a fonte original.")
    reader = csv.DictReader(io.StringIO(_decode_csv(content)), delimiter=";")
    if reader.fieldnames != list(LEDGER_COLUMNS):
        raise ReconciliationError("Razão: use as nove colunas do contrato ledger-csv-v1, na ordem.")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for number, raw in enumerate(reader, start=2):
        if number > MAX_ROWS + 1:
            raise ReconciliationError("Razão excede o limite de 100.000 partidas.")
        if None in raw or any(v is None for v in raw.values()):
            raise ReconciliationError(f"Razão: colunas incompletas na linha {number}.")
        row: dict[str, Any] = {k: v.strip() for k, v in raw.items()}
        for key, limit in {
            "entry_key": 160,
            "line_key": 160,
            "history": 500,
            "account_code": 64,
            "document": 160,
        }.items():
            if len(row[key]) > limit or (key != "document" and not row[key]):
                raise ReconciliationError(f"Razão: {key} inválido na linha {number}.")
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["date"]):
                raise ValueError("date_format")
            row["date"] = date.fromisoformat(row["date"]).isoformat()
        except ValueError as exc:
            raise ReconciliationError(f"Razão: data ISO inválida na linha {number}.") from exc
        if (
            row["side"] not in {"debit", "credit"}
            or not re.fullmatch(r"[0-9]{1,19}", row["amount_cents"])
            or not 0 < int(row["amount_cents"]) <= 9223372036854775807
        ):
            raise ReconciliationError(f"Razão: lado ou centavos inválidos na linha {number}.")
        row["amount_cents"] = int(row["amount_cents"])
        identity = row["entry_key"], row["line_key"]
        if identity in seen:
            raise ReconciliationError(f"Razão: chave de partida repetida na linha {number}.")
        seen.add(identity)
        row["source_row"] = number
        grouped[row["entry_key"]].append(row)
    if not grouped:
        raise ReconciliationError("Razão sem partidas; confira a exportação da fonte.")
    return grouped


@transaction.atomic
def import_ledger_source(source: ReconciliationSourceFile) -> dict[str, int]:
    """All-or-nothing import. Source journals remain drafts and cannot be exported."""
    if source.kind != "csv" or source.origin != "accounting":
        raise ReconciliationError("Razão independente exige CSV de origem contábil.")
    ClientCompany.objects.select_for_update().get(
        pk=source.company_id, organization_id=source.organization_id
    )
    account = source.financial_account
    if (
        account is None
        or account.organization_id != source.organization_id
        or account.company_id != source.company_id
        or not account.active
        or not account.ledger_code
        or not account.account_reference
    ):
        raise ReconciliationError(
            "Razão: selecione a conta financeira com referência e conta contábil."
        )
    catalogue = set(
        LedgerAccount.objects.filter(
            organization_id=source.organization_id, company_id=source.company_id
        ).values_list("code", flat=True)
    )
    grouped = _rows(source)
    prepared = []
    for key, rows in grouped.items():
        if any(row["account_code"] not in catalogue for row in rows):
            raise ReconciliationError("Razão contém conta ausente do plano de contas da empresa.")
        if len({(r["date"], r["history"], r["document"]) for r in rows}) != 1:
            raise ReconciliationError(
                "Razão: data, histórico e documento devem concordar nas partidas."
            )
        debit = sum(r["amount_cents"] for r in rows if r["side"] == "debit")
        credit = sum(r["amount_cents"] for r in rows if r["side"] == "credit")
        if len(rows) < 2 or debit != credit or debit > 9223372036854775807:
            raise ReconciliationError(
                "Razão: lançamento incompleto, desequilibrado ou fora do limite."
            )
        bank_rows = [r for r in rows if r["account_code"] == account.ledger_code]
        if len(bank_rows) != 1 or bank_rows[0]["cash_direction"] not in {"inflow", "outflow"}:
            raise ReconciliationError(
                "Razão: identifique um único efeito bancário e sua direção explícita."
            )
        if any(r["cash_direction"] for r in rows if r is not bank_rows[0]):
            raise ReconciliationError(
                "Razão: direção de caixa somente na partida da conta selecionada."
            )
        canonical = sorted(
            ({k: v for k, v in row.items() if k != "source_row"} for row in rows),
            key=lambda r: r["line_key"],
        )
        fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
        existing = IndependentLedgerRecord.objects.filter(
            organization_id=source.organization_id, financial_account=account, external_key=key
        ).first()
        if existing and existing.fingerprint != fingerprint:
            raise ReconciliationError(
                "Razão: chave já recebida com conteúdo diferente; revise a fonte."
            )
        prepared.append((key, rows, bank_rows[0], fingerprint, existing))
    data_source, _ = DataSource.objects.get_or_create(
        organization=source.organization,
        kind=DataSource.Kind.OTHER_MANUAL,
        defaults={"label": "Razão independente (arquivo normalizado)"},
    )
    created = 0
    for key, rows, bank, fingerprint, existing in prepared:
        if existing:
            continue
        first = rows[0]
        entry = JournalEntry.objects.create(
            organization=source.organization,
            company=source.company,
            occurred_on=first["date"],
            history=first["history"],
            purpose="source_ledger",
        )
        bank_line = None
        for row in rows:
            line = JournalLine.objects.create(
                organization=source.organization,
                entry=entry,
                account_code=row["account_code"],
                side=row["side"],
                amount_cents=row["amount_cents"],
                history=row["history"],
            )
            if row is bank:
                bank_line = line
        # Identity includes the account to avoid collapsing equal keys from different accounts.
        external_key = "ledger:" + hashlib.sha256(f"{account.pk}:{key}".encode()).hexdigest()
        accounting = AccountingEntry.objects.create(
            organization=source.organization,
            data_source=data_source,
            company=source.company,
            external_key=external_key,
            occurred_on=first["date"],
            description=first["history"],
            amount_cents=bank["amount_cents"],
            direction=bank["cash_direction"],
            account_reference=account.account_reference,
        )
        assert bank_line is not None
        IndependentLedgerRecord.objects.create(
            organization=source.organization,
            source_file=source,
            financial_account=account,
            external_key=key,
            fingerprint=fingerprint,
            entry=entry,
            accounting_entry=accounting,
            bank_line=bank_line,
            source_reference={
                "contract": "ledger-csv-v1",
                "document": first["document"],
                "rows": [r["source_row"] for r in rows],
                "content_hash": source.content_hash,
            },
        )
        created += 1
    record_event(
        action="hub.reconciliation.independent_ledger_imported",
        organization=source.organization,
        actor=source.uploaded_by,
        target=source,
        metadata={"created": created, "total": len(prepared)},
    )
    from apps.hub.reconciliation import rebuild_reconciliation_matches

    rebuild_reconciliation_matches(organization=source.organization, company=source.company)
    return {"created": created, "ignored": len(prepared) - created, "processed": len(prepared)}
