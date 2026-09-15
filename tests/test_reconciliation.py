from __future__ import annotations

import pytest

from apps.hub.models import BankTransaction, ClientCompany, DominioBankEntry, ReconciliationMatch
from apps.hub.reconciliation import (
    OfxParseError,
    confirm_reconciliation_match,
    import_ofx,
    parse_ofx,
    rebuild_reconciliation_matches,
)
from apps.organizations.models import Organization

_OFX = b"""OFXHEADER:100
<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKACCTFROM><BANKID>001<ACCTID>123</BANKACCTFROM>
<BANKTRANLIST><STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260912<TRNAMT>-12.34<FITID>fit-1<NAME>Fornecedor
</STMTTRN></BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"""


def test_parse_ofx_normalizes_a_transaction() -> None:
    statement = parse_ofx(_OFX)

    assert statement.account_reference == "001:123"
    assert statement.transactions[0].amount_cents == -1234
    assert statement.transactions[0].external_id == "fit-1"


def test_parse_ofx_rejects_invalid_content() -> None:
    with pytest.raises(OfxParseError, match="OFX válido"):
        parse_ofx(b"not a statement")


@pytest.mark.django_db
def test_ofx_import_is_idempotent() -> None:
    organization = Organization.objects.create(name="OFX", slug="ofx")
    company = ClientCompany.objects.create(organization=organization, name="Cliente")

    first, created = import_ofx(
        organization=organization, company=company, filename="extrato.ofx", content=_OFX
    )
    repeated, repeated_created = import_ofx(
        organization=organization, company=company, filename="extrato.ofx", content=_OFX
    )

    assert created is True
    assert repeated_created is False
    assert repeated.id == first.id
    assert BankTransaction.objects.filter(statement=first).count() == 1


@pytest.mark.django_db
def test_reconciliation_matches_only_one_exact_dominio_item() -> None:
    organization = Organization.objects.create(name="Conciliação", slug="conciliacao")
    company = ClientCompany.objects.create(organization=organization, name="Cliente")
    statement, _ = import_ofx(
        organization=organization, company=company, filename="extrato.ofx", content=_OFX
    )
    transaction = statement.transactions.get()
    DominioBankEntry.objects.create(
        organization=organization,
        company=company,
        source_id="1|2|3",
        occurred_on=transaction.occurred_on,
        amount_cents=1234,
    )

    rebuild_reconciliation_matches(organization=organization)

    match = ReconciliationMatch.objects.get(transaction=transaction)
    assert match.status == ReconciliationMatch.Status.MATCHED
    assert match.dominio_entry is not None


@pytest.mark.django_db
def test_manual_confirmation_preserves_an_ambiguous_choice_after_sync() -> None:
    organization = Organization.objects.create(name="Revisão", slug="revisao")
    company = ClientCompany.objects.create(organization=organization, name="Cliente")
    statement, _ = import_ofx(
        organization=organization, company=company, filename="extrato.ofx", content=_OFX
    )
    transaction = statement.transactions.get()
    first = DominioBankEntry.objects.create(
        organization=organization,
        company=company,
        source_id="1|2|3",
        occurred_on=transaction.occurred_on,
        amount_cents=1234,
    )
    selected = DominioBankEntry.objects.create(
        organization=organization,
        company=company,
        source_id="1|2|4",
        occurred_on=transaction.occurred_on,
        amount_cents=1234,
    )

    rebuild_reconciliation_matches(organization=organization)
    match = ReconciliationMatch.objects.get(transaction=transaction)
    assert match.status == ReconciliationMatch.Status.AMBIGUOUS

    confirm_reconciliation_match(match=match, dominio_entry=selected)
    rebuild_reconciliation_matches(organization=organization)

    match.refresh_from_db()
    assert match.is_manual is True
    assert match.dominio_entry == selected
    assert match.dominio_entry != first


@pytest.mark.django_db
def test_manual_confirmation_rejects_an_entry_from_another_company() -> None:
    organization = Organization.objects.create(name="Isolamento", slug="isolamento")
    company = ClientCompany.objects.create(organization=organization, name="Cliente")
    other_company = ClientCompany.objects.create(organization=organization, name="Outro")
    statement, _ = import_ofx(
        organization=organization, company=company, filename="extrato.ofx", content=_OFX
    )
    transaction = statement.transactions.get()
    entry = DominioBankEntry.objects.create(
        organization=organization,
        company=other_company,
        source_id="2|2|2",
        occurred_on=transaction.occurred_on,
        amount_cents=1234,
    )
    match = ReconciliationMatch.objects.get(transaction=transaction)

    with pytest.raises(ValueError, match="não corresponde"):
        confirm_reconciliation_match(match=match, dominio_entry=entry)
