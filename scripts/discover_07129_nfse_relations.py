from __future__ import annotations

import getpass
import json
import os
from pathlib import Path

import pyodbc

OUTPUT = Path(".tmp/07129-extract/nfse-relations.json")


password = os.environ.pop("CICA_DOMINIO_PASSWORD", "") or getpass.getpass(
    "Senha do usuario externo CICA_NFSE: "
)
connection = pyodbc.connect(
    f"DSN=CICA07129;UID=CICA_NFSE;PWD={password};ASTART=NO;CON=Cica07129RelationReadOnly",
    timeout=15,
    readonly=True,
)
try:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT t.table_name, c.column_name, c.column_id "
        "FROM SYS.SYSTABLE t "
        "JOIN SYS.SYSCOLUMN c ON c.table_id = t.table_id "
        "WHERE t.table_id IN ("
        "SELECT a.table_id FROM SYS.SYSCOLUMN a "
        "JOIN SYS.SYSCOLUMN b ON b.table_id = a.table_id "
        "WHERE UPPER(a.column_name) = 'CODI_ACU' "
        "AND UPPER(b.column_name) IN ('CODI_CLI', 'CODI_FOR')) "
        "ORDER BY t.table_name, c.column_id"
    )
    tables: dict[str, list[str]] = {}
    for table_name, column_name, _ordinal in cursor.fetchall():
        tables.setdefault(str(table_name), []).append(str(column_name))
    likely = [
        {"table": table, "columns": columns}
        for table, columns in tables.items()
        if any(name.upper() == "CODI_ACU" for name in columns)
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(likely, ensure_ascii=False, indent=2), encoding="utf-8")
    print({"candidate_tables": len(likely), "schema_file": str(OUTPUT)})
finally:
    connection.close()
    password = ""
