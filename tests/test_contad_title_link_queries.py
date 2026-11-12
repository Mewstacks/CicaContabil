"""Relational checks for the actual fixed lot diagnostic SQL, using synthetic rows."""

# Table names are exclusively the three fixed fixture parameters.
# ruff: noqa: S608
import re
from pathlib import Path

import pytest

from test_contad_title_profile_queries import SCOPE, source_db  # noqa: F401

SOURCE = Path(__file__).resolve().parents[1] / "agent-windows/inspect-contad-title-links.ps1"


def query(variable, family, note, suffix):
    match = re.search(rf"\${variable}=@'\n(.*?)\n'@", SOURCE.read_text(encoding="utf-8-sig"), re.S)
    assert match
    sql = match[1].replace("{family}", family).replace("{note}", note).replace("{suffix}", suffix)
    return sql.replace("TOP 257 ", "").replace("TOP 129 ", "").replace("bethadba.", "")


@pytest.fixture
def linked_db(source_db):  # noqa: F811 - dependency on the imported parametrized fixture
    db, family, note, suffix = source_db
    db.execute("ALTER TABLE ctlancto ADD COLUMN codi_lote INTEGER")
    db.execute(
        "CREATE TABLE ctlanctolote(codi_emp INTEGER,codi_lote INTEGER,"
        "PRIMARY KEY(codi_emp,codi_lote))"
    )
    return db, family, note, suffix


def payment(fixture, sequence=1, component=1, company=212, day="2026-09-12"):
    db, family, _, _ = fixture
    db.execute(
        f"INSERT INTO ef{family}pag VALUES (?,?,?,?,?,?,?,?,?)",
        (company, 1, 1, day, component, sequence, 90, "B", 0),
    )


def link(fixture, entry, *, sequence=1, component=1, company=212, fiscal=212, group=1):
    db, family, _, _ = fixture
    db.execute(
        f"INSERT INTO ef{family}pag_lancto VALUES (?,?,?,?,?,?,?,?,?)",
        (company, entry, fiscal, 1, "2026-09-12", component, 1, sequence, group),
    )


def entry(fixture, number, lot, *, debit=501, credit=0, company=212, chart=212, day="2026-09-12"):
    fixture[0].execute(
        "INSERT INTO ctlancto VALUES (?,?,?,?,?,?,?)",
        (company, number, chart, day, debit, credit, lot),
    )


def coverage(fixture):
    db, family, note, suffix = fixture
    return db.execute(query("coverageQuery", family, note, suffix), SCOPE + SCOPE[1:]).fetchall()


def accounts(fixture):
    db, family, note, suffix = fixture
    return db.execute(query("accountQuery", family, note, suffix), SCOPE).fetchall()


def test_bank_in_other_lot_line_does_not_multiply_component_or_partial_payment(linked_db):
    db = linked_db[0]
    db.execute("INSERT INTO ctlanctolote VALUES(212,10)")
    payment(linked_db)
    payment(linked_db, sequence=2)
    payment(linked_db, component=2)
    entry(linked_db, 100, 10)
    entry(linked_db, 101, 10)
    entry(linked_db, 102, 10, credit=8)
    link(linked_db, 100)
    link(linked_db, 101)
    # A second accounting group points to the same entry; do not count it as
    # another payment or another bank lot. Raw link multiplicity is preserved.
    link(linked_db, 100, group=2)
    link(linked_db, 100, component=2)
    # Same identifiers in another fiscal company cannot match the pilot.
    payment(linked_db, sequence=2, company=999)
    link(linked_db, 102, sequence=2, fiscal=999)
    assert coverage(linked_db) == [
        (1, "B", 0, 2, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (2, "B", 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    ]
    assert accounts(linked_db) == [(1, 212, 212, 501, 0, 3, 2), (2, 212, 212, 501, 0, 1, 1)]


def test_foreign_company_wrong_chart_and_outside_period_are_separate(linked_db):
    db = linked_db[0]
    for company in (212, 999):
        db.execute("INSERT INTO ctlanctolote VALUES(?,10)", (company,))
    for i in range(1, 4):
        payment(linked_db, sequence=i)
    # Identical lot IDs in different companies are different lots.
    entry(linked_db, 100, 10, company=999)
    entry(linked_db, 101, 10, company=999, credit=8)
    link(linked_db, 100, company=999)
    entry(linked_db, 200, 10)
    entry(linked_db, 201, 10, credit=8, chart=999)
    entry(linked_db, 202, 10, credit=8, day="2026-10-01")
    link(linked_db, 200, sequence=2)
    # Another payment's accounting line is the bank line itself; no header
    # inference is needed to count a direct link, including a NULL lot.
    entry(linked_db, 300, None, credit=8)
    link(linked_db, 300, sequence=3)
    assert coverage(linked_db) == [(1, "B", 0, 3, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1)]


def test_ambiguous_bank_lots_effects_and_missing_sources_remain_explicit(linked_db):
    db = linked_db[0]
    for lot in (10, 11, 12):
        db.execute("INSERT INTO ctlanctolote VALUES(212,?)", (lot,))
    for i in range(1, 5):
        payment(linked_db, sequence=i)
    entry(linked_db, 100, 10)
    entry(linked_db, 101, 11)
    entry(linked_db, 102, 10, debit=8)
    entry(linked_db, 103, 11, credit=8)
    entry(linked_db, 104, 10, debit=8, day="2026-08-31")
    link(linked_db, 100)
    link(linked_db, 101)
    entry(linked_db, 200, 12)
    entry(linked_db, 201, 12, debit=8, credit=8)
    entry(linked_db, 202, 12, debit=8)
    link(linked_db, 200, sequence=2)
    link(linked_db, 9999, sequence=3)
    entry(linked_db, 400, 99)
    link(linked_db, 400, sequence=4)
    assert coverage(linked_db) == [(1, "B", 0, 4, 0, 0, 2, 1, 1, 1, 1, 0, 1, 0, 1, 0)]
    # A missing ledger row contributes a link with unknown accounts and zero
    # existing entries, not a made-up account or a dropped relation.
    assert (1, 212, None, None, None, 1, 0) in accounts(linked_db)


def test_empty_source_and_half_open_payment_period(linked_db):
    assert coverage(linked_db) == []
    assert accounts(linked_db) == []
    payment(linked_db, day="2026-08-31")
    payment(linked_db, day="2026-10-01")
    payment(linked_db, day="2026-09-01")
    payment(linked_db, day="2026-09-30")
    assert coverage(linked_db) == [(1, "B", 0, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)]
    assert accounts(linked_db) == []
