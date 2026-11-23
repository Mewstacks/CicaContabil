"""Independent complete journals; normalized file contract, never inferred ERP SQL."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import PurePath
from typing import Any

from django.db import transaction

from apps.audit.services import record_event
from apps.hub.models import (
    AccountingEntry,
    ClientCompany,
    DataSource,
    FinancialAccount,
    IndependentLedgerRecord,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_service import (
    MAX_BYTES,
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
LEDGER_CONTRACT_HELP = (
    "Envie CSV separado por ponto e vírgula, com as nove colunas do modelo na mesma ordem.",
    "Cada lançamento precisa de todas as partidas: débitos iguais aos créditos "
    "e um único efeito bancário.",
    "Use datas AAAA-MM-DD, valores positivos em centavos e lados debit ou credit; "
    "não arredonde valores.",
    "Informe inflow ou outflow somente na partida da conta bancária selecionada, conforme a fonte.",
    "Cadastre no plano da empresa todas as contas reais presentes nas partidas antes de enviar.",
    "O modelo contém dados fictícios: substitua todas as linhas "
    "por partidas comprovadas da sua fonte.",
    "PDF, XLSX e CSV genéricos não geram este Razão independente.",
)


def ledger_csv_template() -> bytes:
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    writer.writerow(LEDGER_COLUMNS)
    writer.writerow(
        [
            "EXEMPLO-FICTICIO-1",
            "banco",
            "2026-09-12",
            "EXEMPLO FICTÍCIO — substituir",
            "CONTA_BANCO",
            "debit",
            10000,
            "inflow",
            "DOCUMENTO-FICTICIO",
        ]
    )
    writer.writerow(
        [
            "EXEMPLO-FICTICIO-1",
            "contrapartida",
            "2026-09-12",
            "EXEMPLO FICTÍCIO — substituir",
            "CONTRAPARTIDA",
            "credit",
            10000,
            "",
            "DOCUMENTO-FICTICIO",
        ]
    )
    return output.getvalue().encode("utf-8")


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
    return _content_rows(content)


def _content_rows(content: bytes) -> dict[str, list[dict[str, Any]]]:
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


def _validate_account(*, account: Any, organization_id: Any, company_id: Any) -> None:
    if (
        account is None
        or account.organization_id != organization_id
        or account.company_id != company_id
        or not account.active
        or not account.ledger_code
        or not account.account_reference
    ):
        raise ReconciliationError(
            "Razão: selecione a conta financeira com referência e conta contábil."
        )


def _prepare_rows(
    grouped: dict[str, list[dict[str, Any]]],
    *,
    account: FinancialAccount,
    organization_id: Any,
    company_id: Any,
) -> list[tuple[str, list[dict[str, Any]], dict[str, Any], str, IndependentLedgerRecord | None]]:
    catalogue = set(
        LedgerAccount.objects.filter(
            organization_id=organization_id,
            company_id=company_id,
            active=True,
            accepts_entries=True,
        ).values_list("code", flat=True)
    )
    missing = sorted({row["account_code"] for rows in grouped.values() for row in rows} - catalogue)
    if missing:
        listed = ", ".join(missing[:20])
        remainder = f" e mais {len(missing) - 20}" if len(missing) > 20 else ""
        raise ReconciliationError(
            f"Razão: contas ausentes ou indisponíveis no plano da empresa: {listed}{remainder}. "
            "Confira e cadastre as contas reais em Configuração → Plano de contas "
            "antes de reenviar."
        )
    prepared = []
    for key, rows in grouped.items():
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
            organization_id=organization_id, financial_account=account, external_key=key
        ).first()
        if existing and existing.fingerprint != fingerprint:
            raise ReconciliationError(
                "Razão: chave já recebida com conteúdo diferente; revise a fonte."
            )
        prepared.append((key, rows, bank_rows[0], fingerprint, existing))
    return prepared


def preview_ledger_uploads(
    *,
    organization: Any,
    company: ClientCompany,
    financial_account: FinancialAccount | None,
    uploads: list[Any],
) -> list[dict[str, Any]]:
    """Validate the entire human upload batch with SELECTs only, preserving file positions."""
    if (
        company.organization_id != organization.pk
        or not ClientCompany.objects.filter(
            pk=company.pk,
            organization=organization,
            active=True,
        ).exists()
    ):
        raise ReconciliationError("Razão: escolha uma empresa ativa do escritório atual.")
    if financial_account is None:
        raise ReconciliationError("Razão: selecione a conta financeira antes de enviar.")
    account = FinancialAccount.objects.filter(
        pk=financial_account.pk,
        organization=organization,
        company=company,
        active=True,
    ).first()
    _validate_account(account=account, organization_id=organization.pk, company_id=company.pk)
    assert account is not None
    if any(
        not getattr(account, field).strip()
        for field in (
            "name",
            "bank_code",
            "account_reference",
            "ledger_code",
        )
    ):
        raise ReconciliationError(
            "Razão: complete o nome e o banco da conta financeira antes de enviar."
        )
    if not 1 <= len(uploads) <= 20:
        raise ReconciliationError("Envie entre 1 e 20 arquivos de Razão por lote.")
    results = []
    seen: dict[str, str] = {}
    for upload in uploads:
        filename = str(getattr(upload, "name", "") or "")
        if PurePath(filename).suffix.casefold() != ".csv":
            raise ReconciliationError(
                "Razão independente aceita somente CSV de partidas completas. "
                "Use o modelo; PDF, XLSX e outros arquivos pertencem à importação geral."
            )
        position = upload.tell()
        try:
            upload.seek(0)
            content = upload.read(MAX_BYTES + 1)
        finally:
            upload.seek(position)
        if not content or len(content) > MAX_BYTES or b"\x00" in content:
            raise ReconciliationError("Razão: arquivo vazio, binário ou maior que 25 MiB.")
        digest = hashlib.sha256(content).hexdigest()
        prior = ReconciliationSourceFile.objects.filter(
            organization=organization,
            company=company,
            content_hash=digest,
        ).first()
        if prior and (
            prior.origin != "accounting"
            or prior.kind != "csv"
            or prior.financial_account_id != account.pk
        ):
            raise ReconciliationError(
                "Este arquivo já foi recebido com outra origem ou conta. Confira a fonte existente."
            )
        try:
            grouped = _content_rows(content)
        except csv.Error:
            raise ReconciliationError(
                "Razão: CSV inválido ou com campo maior que o permitido."
            ) from None
        if any(key.startswith("EXEMPLO-FICTICIO-") for key in grouped):
            raise ReconciliationError(
                "Substitua as linhas fictícias do modelo pelas partidas reais "
                "da fonte antes de enviar."
            )
        prepared = _prepare_rows(
            grouped,
            account=account,
            organization_id=organization.pk,
            company_id=company.pk,
        )
        new = 0
        for key, _rows_in_entry, _bank, fingerprint, existing in prepared:
            if key in seen and seen[key] != fingerprint:
                raise ReconciliationError(
                    "O lote repete uma chave de lançamento com conteúdo diferente. "
                    "Confira os arquivos."
                )
            if key not in seen and existing is None:
                new += 1
            seen[key] = fingerprint
        results.append(
            {
                "processed": len(prepared),
                "new": new,
                "ignored": len(prepared) - new,
                "content_hash": digest,
            }
        )
    return results


@transaction.atomic
def import_ledger_source(source: ReconciliationSourceFile) -> dict[str, int]:
    """All-or-nothing import. Source journals remain drafts and cannot be exported."""
    if source.kind != "csv" or source.origin != "accounting":
        raise ReconciliationError("Razão independente exige CSV de origem contábil.")
    ClientCompany.objects.select_for_update().get(
        pk=source.company_id, organization_id=source.organization_id
    )
    account = source.financial_account
    _validate_account(
        account=account, organization_id=source.organization_id, company_id=source.company_id
    )
    assert account is not None
    prepared = _prepare_rows(
        _rows(source),
        account=account,
        organization_id=source.organization_id,
        company_id=source.company_id,
    )
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
