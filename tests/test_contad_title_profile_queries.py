"""Execute the actual diagnostic SQL against adversarial synthetic source rows.

SQLite checks relational behavior, not SQL Anywhere driver compatibility. The
Windows harness separately checks ODBC parameters, limits and safe diagnostics.
"""

# The table names below come exclusively from the three fixed fixture parameters.
# ruff: noqa: S608
import re
import sqlite3
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "agent-windows/inspect-contad-title-profile.ps1"
SCOPE = (212, "2026-09-01", "2026-10-01")


def query(variable: str, family: str, note: str, suffix: str) -> str:
    source = SOURCE.read_text(encoding="utf-8-sig")
    match = re.search(rf"\${variable}=@'\n(.*?)\n'@", source, re.S)
    assert match
    sql = match[1].replace("{family}", family).replace("{note}", note).replace("{suffix}", suffix)
    # These are the only dialect differences used by the fixed queries.
    return sql.replace("TOP 257 ", "").replace("bethadba.", "")


@pytest.fixture(
    params=[("entradas", "ent", "entp"), ("saidas", "sai", "saip"), ("servicos", "ser", "serp")]
)
def source_db(request):
    family, note, suffix = request.param
    db = sqlite3.connect(":memory:")
    db.executescript(f"""
        CREATE TABLE ef{family} (codi_emp INTEGER, codi_{note} INTEGER,
            PRIMARY KEY(codi_emp,codi_{note}));
        CREATE TABLE ef{family}par (codi_emp INTEGER, codi_{note} INTEGER,
            parc_{suffix} INTEGER, vcto_{suffix} TEXT, tipo_{suffix} INTEGER,
            vlor_{suffix} NUMERIC, origem_reg INTEGER,
            PRIMARY KEY(codi_emp,codi_{note},parc_{suffix}));
        CREATE TABLE ef{family}pag (codi_emp INTEGER, codi_{note} INTEGER,
            parc_{suffix} INTEGER, pgto_{suffix} TEXT, tipo_{suffix} INTEGER,
            nropag_{suffix} INTEGER, vpag_{suffix} NUMERIC,
            origempg_{suffix} TEXT, origem_reg INTEGER,
            PRIMARY KEY(codi_emp,codi_{note},pgto_{suffix},tipo_{suffix},
                        parc_{suffix},nropag_{suffix}));
        CREATE TABLE ef{family}pag_lancto (codi_emp INTEGER, nume_lan INTEGER,
            fili_lan INTEGER, codi_{note} INTEGER, pgto_{suffix} TEXT,
            tipo_{suffix} INTEGER, parc_{suffix} INTEGER, nropag_{suffix} INTEGER,
            grupo INTEGER,
            PRIMARY KEY(codi_emp,nume_lan,fili_lan,codi_{note},pgto_{suffix},
                        tipo_{suffix},parc_{suffix},nropag_{suffix},grupo));
        CREATE TABLE ctlancto (codi_emp INTEGER, nume_lan INTEGER,
            CODI_EMP_PLANO INTEGER, data_lan TEXT, cdeb_lan INTEGER, ccre_lan INTEGER,
            PRIMARY KEY(codi_emp,nume_lan));
    """)
    yield db, family, note, suffix
    db.close()


def payments(fixture):
    db, family, note, suffix = fixture
    return db.execute(
        query("paymentQuery", family, note, suffix), SCOPE[1:] + SCOPE + SCOPE
    ).fetchall()


def test_payment_identity_preserves_company_type_and_partial_sequence(source_db):
    db, family, _note, _suffix = source_db
    db.executemany(f"INSERT INTO ef{family} VALUES (?,?)", [(212, 1), (999, 1)])
    db.executemany(
        f"INSERT INTO ef{family}par VALUES (?,?,?,?,?,?,?)",
        [(212, 1, 1, "2026-10-12", 0, 100, 0), (999, 1, 1, "2026-09-12", 0, 100, 0)],
    )
    # Same date/parcela: distinct component type and partial sequence are distinct
    # source facts. Their codes deliberately have no assigned financial meaning.
    db.executemany(
        f"INSERT INTO ef{family}pag VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (212, 1, 1, "2026-09-12", 0, 1, 50, "M", 0),
            (212, 1, 1, "2026-09-12", 0, 2, 20, "M", 0),
            (212, 1, 1, "2026-09-12", 3, 1, 5, "M", 0),
            (999, 1, 1, "2026-09-12", 0, 1, 99, "M", 0),
            (212, 1, 1, "2026-08-31", 0, 1, 99, "M", 0),
            (212, 1, 1, "2026-10-01", 0, 1, 99, "M", 0),
        ],
    )
    db.executemany(
        "INSERT INTO ctlancto VALUES (?,?,?,?,?,?)",
        [
            (212, 100, 212, "2026-09-12", 0, 8),
            (999, 101, 999, "2026-09-12", 0, 8),
            (212, 102, 212, "2026-10-01", 0, 9),
            (212, 103, 999, "2026-09-12", 0, 8),
        ],
    )
    db.executemany(
        f"INSERT INTO ef{family}pag_lancto VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (212, 100, 212, 1, "2026-09-12", 0, 1, 1, 1),
            (999, 101, 212, 1, "2026-09-12", 0, 1, 1, 1),
            (212, 102, 212, 1, "2026-09-12", 3, 1, 1, 1),
            (212, 103, 212, 1, "2026-09-12", 3, 1, 1, 2),
            # A link belonging to another fiscal company must not contaminate212.
            (212, 100, 999, 1, "2026-09-12", 0, 1, 2, 1),
        ],
    )
    rows = payments(source_db)
    assert len(rows) == 2
    # type/origin/origin_reg,count,null,+,zero,-,missing installment/header,
    # no link,one,multiple,total links,bank,foreign company,missing ledger,outside
    assert rows[0] == (0, "M", 0, 2, 0, 2, 0, 0, 0, 0, 1, 0, 1, 2, 1, 1, 0, 0)
    assert rows[1] == (3, "M", 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 2, 0, 0, 0, 1)


def test_missing_parents_signs_and_missing_ledger_are_counts_only(source_db):
    db, family, _, _ = source_db
    db.executemany(
        f"INSERT INTO ef{family}pag VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (212, 7, 1, "2026-09-01", 8, 1, None, None, None),
            (212, 7, 1, "2026-09-02", 8, 1, -4, None, None),
            (212, 7, 1, "2026-09-30", 8, 1, 0, None, None),
        ],
    )
    db.execute(
        f"INSERT INTO ef{family}pag_lancto VALUES (?,?,?,?,?,?,?,?,?)",
        (212, 998, 212, 7, "2026-09-02", 8, 1, 1, 1),
    )
    assert payments(source_db) == [(8, None, None, 3, 1, 0, 1, 1, 3, 3, 2, 1, 0, 1, 0, 0, 1, 0)]


def test_due_dates_are_separate_from_payment_dates_and_period_is_half_open(source_db):
    db, family, note, suffix = source_db
    db.execute(f"INSERT INTO ef{family} VALUES (212,1)")
    db.executemany(
        f"INSERT INTO ef{family}par VALUES (?,?,?,?,?,?,?)",
        [
            (212, 1, 1, "2026-09-01", 2, 100, 0),
            (212, 2, 1, "2026-09-30", 2, 0, 0),
            (212, 2, 2, "2026-09-30", 2, -5, 0),
            (212, 2, 3, "2026-09-30", 2, None, 0),
            (212, 2, 4, "2026-10-01", 2, 100, 0),
            (212, 2, 5, "2026-08-31", 2, 100, 0),
            (999, 1, 1, "2026-09-01", 2, 100, 0),
        ],
    )
    assert db.execute(query("parcelQuery", family, note, suffix), SCOPE).fetchall() == [
        (2, 0, 4, 1, 1, 1, 1, 3)
    ]
    assert payments(source_db) == []
