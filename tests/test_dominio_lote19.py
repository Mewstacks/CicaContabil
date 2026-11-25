"""D-380: official Domínio importer dataset 19 (fixed width) and plan-based accounts."""

from __future__ import annotations

from datetime import date

import pytest

from apps.hub.models import ClientCompany, JournalEntry, JournalLine, LedgerAccount
from apps.hub.postable_accounts import account_accepts_entries, invalid_account_codes
from apps.hub.reconciliation_service import (
    DOMINIO_LOTE19_WIDTHS,
    ReconciliationError,
    get_accounting_export_adapter,
    render_dominio_lote19,
)
from apps.organizations.models import Organization
from test_account_discovery import discovered as discovered_fixture
from test_account_discovery import discovered_profile as discovered_profile_fixture
from test_account_discovery import sources as sources_fixture
from test_accounting_preview import case as case_fixture
from test_accounting_preview import generate

sources = sources_fixture
discovered_profile = discovered_profile_fixture
discovered = discovered_fixture
case = case_fixture
pytestmark = pytest.mark.django_db


def field(record: str, start: int, end: int) -> str:
    """Official layout positions are 1-based and inclusive."""
    return record[start - 1 : end]


@pytest.fixture
def company():
    organization = Organization.objects.create(name="Leiaute", slug="leiaute")
    return ClientCompany.objects.create(
        organization=organization,
        name="Empresa sintética",
        dominio_code="212",
        dominio_registration_raw="12345678000190",
    )


def entry(company, lines, *, history="Pagamento fornecedor", on=date(2026, 9, 12)):
    item = JournalEntry.objects.create(
        organization=company.organization,
        company=company,
        occurred_on=on,
        history=history,
        state=JournalEntry.State.APPROVED,
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                organization=company.organization,
                entry=item,
                account_code=code,
                side=side,
                amount_cents=amount,
            )
            for code, side, amount in lines
        ]
    )
    return item


def records(content: bytes) -> list[str]:
    assert content.endswith(b"\r\n") and b"\n" not in content.replace(b"\r\n", b"")
    return content.decode("cp1252").split("\r\n")[:-1]


def test_adapter_is_the_official_fixed_width_dataset():
    adapter = get_accounting_export_adapter("dominio")
    assert adapter.version == "dominio-lote19-v1"
    assert adapter.extension == "txt"
    assert adapter.render is render_dominio_lote19


def test_header_lote_partida_and_trailer_follow_official_positions(company):
    first = entry(company, [("8", "debit", 123456), ("41", "credit", 123456)])
    second = entry(
        company,
        [("8", "credit", 990), ("512", "debit", 990)],
        history="Tarifa\nbancária\tset/26",
        on=date(2026, 9, 30),
    )
    rows = records(render_dominio_lote19([second, first]))
    assert [row[:2] for row in rows] == ["01", "02", "03", "02", "03", "99"]
    for row in rows:
        assert len(row) == DOMINIO_LOTE19_WIDTHS[row[:2]]
    header = rows[0]
    assert field(header, 3, 9) == "0000212"
    assert field(header, 10, 23) == "12345678000190"
    assert field(header, 24, 33) == "12/09/2026"
    assert field(header, 34, 43) == "30/09/2026"
    assert field(header, 44, 44) == "N"
    assert field(header, 45, 46) == "05"
    assert field(header, 47, 51) == "00000"
    assert field(header, 52, 52) == "1"
    assert field(header, 53, 54) == "17"
    lote, partida = rows[1], rows[2]
    assert field(lote, 3, 9) == "0000001"
    assert field(lote, 10, 10) == "X"
    assert field(lote, 11, 20) == "12/09/2026"
    assert field(lote, 21, 50).rstrip() == "CICA"
    assert field(partida, 3, 9) == "0000002"
    assert field(partida, 10, 16) == "0000008"
    assert field(partida, 17, 23) == "0000041"
    assert field(partida, 24, 38) == "000000000123456"
    assert field(partida, 39, 45) == "0000000"
    assert field(partida, 46, 557).rstrip() == "Pagamento fornecedor"
    assert field(partida, 558, 564) == "0000212"
    later = rows[4]
    assert field(rows[3], 11, 20) == "30/09/2026"
    assert field(later, 10, 16) == "0000512" and field(later, 17, 23) == "0000008"
    assert field(later, 24, 38) == "000000000000990"
    assert field(later, 46, 557).rstrip() == "Tarifa bancária set/26"
    assert rows[5] == "99" + "9" * 98


def test_equal_pairs_become_separate_x_lotes_and_other_compositions_are_refused(company):
    paired = entry(
        company,
        [("8", "debit", 500), ("41", "credit", 500), ("9", "debit", 300), ("42", "credit", 300)],
    )
    rows = records(render_dominio_lote19([paired]))
    assert [row[:2] for row in rows] == ["01", "02", "03", "02", "03", "99"]
    assert [field(row, 3, 9) for row in rows[1:5]] == [f"000000{n}" for n in range(1, 5)]
    # D-421: um lado único contra várias partidas vira um par X por partida.
    split = entry(company, [("8", "debit", 1000), ("41", "credit", 800), ("42", "credit", 200)])
    split_rows = [row for row in records(render_dominio_lote19([split])) if row[:2] == "03"]
    assert [(field(r, 10, 16), field(r, 17, 23), field(r, 24, 38)) for r in split_rows] == [
        ("0000008", "0000041", "000000000000800"),
        ("0000008", "0000042", "000000000000200"),
    ]
    loan = entry(
        company, [("117", "debit", 885094), ("231", "debit", 12239), ("8", "credit", 897333)]
    )
    loan_rows = [row for row in records(render_dominio_lote19([loan])) if row[:2] == "03"]
    assert [(field(r, 10, 16), field(r, 17, 23)) for r in loan_rows] == [
        ("0000117", "0000008"),
        ("0000231", "0000008"),
    ]
    mixed = entry(
        company,
        [("8", "debit", 700), ("9", "debit", 300), ("41", "credit", 600), ("42", "credit", 400)],
    )
    with pytest.raises(ReconciliationError, match="pares de débito e crédito"):
        render_dominio_lote19([mixed])


def test_equal_pairs_are_matched_by_value_whatever_the_line_order(company):
    # O banco não garante a ordem das linhas (PostgreSQL difere do SQLite); o pareamento
    # débito/crédito não pode depender dela.
    shuffled = entry(
        company,
        [("9", "debit", 300), ("41", "credit", 500), ("8", "debit", 500), ("42", "credit", 300)],
    )
    rows = records(render_dominio_lote19([shuffled]))
    assert [row[:2] for row in rows] == ["01", "02", "03", "02", "03", "99"]


@pytest.mark.parametrize("code", ["1.1", "ABC", "12345678"])
def test_account_codes_must_be_domínio_reduced_codes(company, code):
    item = entry(company, [(code, "debit", 100), ("41", "credit", 100)])
    with pytest.raises(ReconciliationError, match="Conta débito"):
        render_dominio_lote19([item])


def test_company_code_is_required_and_files_hold_one_company(company):
    other = ClientCompany.objects.create(
        organization=company.organization, name="Outra", dominio_code="213"
    )
    with pytest.raises(ReconciliationError, match="única empresa"):
        render_dominio_lote19(
            [
                entry(company, [("8", "debit", 100), ("41", "credit", 100)]),
                entry(other, [("8", "debit", 100), ("41", "credit", 100)]),
            ]
        )
    company.dominio_code = ""
    company.save(update_fields=["dominio_code"])
    item = entry(company, [("8", "debit", 100), ("41", "credit", 100)])
    item.company.refresh_from_db()
    with pytest.raises(ReconciliationError, match="código Domínio"):
        render_dominio_lote19([item])


def test_cnpj_is_left_blank_unless_the_literal_registration_has_14_digits(company):
    company.dominio_registration_raw = "12345678901"
    company.save(update_fields=["dominio_registration_raw"])
    item = entry(company, [("8", "debit", 100), ("41", "credit", 100)])
    item.company.refresh_from_db()
    header = records(render_dominio_lote19([item]))[0]
    assert field(header, 10, 23) == " " * 14


def test_history_is_windows_1252_without_controls_and_unencodable_text_is_replaced(company):
    item = entry(
        company,
        [("8", "debit", 100), ("41", "credit", 100)],
        history="Ação nº 5 \u2013 juros € \U0001f600" + "x" * 600,
    )
    partida = records(render_dominio_lote19([item]))[2]
    history = field(partida, 46, 557)
    assert history.startswith("Ação nº 5 \u2013 juros € ?")
    assert len(history) == 512 and len(partida) == 664


def test_plan_accounts_accept_entries_by_company_link(discovered):
    by_code = {
        row.source_company_code: row.company
        for row in discovered.company_coverage.select_related("company")
    }
    own, shared = by_code[212], by_code[213]
    assert account_accepts_entries(own, "8")
    assert not account_accepts_entries(own, "9"), "plan 99 is not linked to company 212"
    assert account_accepts_entries(shared, "9"), "company 213 also uses plan 99"
    assert not account_accepts_entries(shared, "77"), "synthetic/inactive in the source"
    assert invalid_account_codes(shared, ["8", "9", "77", "0", "x", ""]) == {"77", "0", "x"}
    assert not account_accepts_entries(by_code[214], "8")
    LedgerAccount.objects.create(
        organization=own.organization, company=own, code="1.1", name="Manual", active=True
    )
    assert account_accepts_entries(own, "1.1")


def test_homologation_command_is_dry_run_by_default_then_enables_and_revokes(case, tmp_path):
    import json
    from io import StringIO

    from django.core.management import call_command

    from apps.hub.accounting_import import export_homologated
    from apps.platform.models import TenantContract

    TenantContract.objects.create(
        organization=case["organization"], status="active", selected_modules=["reconciliation"]
    )
    preview, _ = generate(case)
    organization = case["organization"]
    base = [
        "record_dominio_homologation",
        f"--organization={organization.pk}",
        f"--preview={preview.pk}",
        "--importer-version=Domínio 10.6A-10 atualização 08",
        "--decision=Synthetic test: no real ERP import",
    ]

    def run(*extra):
        out = StringIO()
        call_command(*base, *extra, stdout=out)
        return json.loads(out.getvalue())

    dry = run()
    assert dry["applied"] is False and dry["homologated_before"] is False
    assert not export_homologated(organization, "dominio", "dominio-lote19-v1")
    applied = run("--apply")
    assert applied["created"] is True and applied["homologated_after"] is True
    assert applied["artifact_sha256"] == preview.content_hash
    assert run("--apply")["created"] is False, "same decision is idempotent"
    revoked = run("--apply", "--revoke")
    assert revoked["homologated_after"] is False
