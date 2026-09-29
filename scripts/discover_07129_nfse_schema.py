from __future__ import annotations

import getpass
import json
import os
from pathlib import Path

import pyodbc

OUTPUT = Path(".tmp/07129-extract/nfse-schema.json")
TARGET_TABLES = (
    "EFACUMULADOR",
    "EFCLIENTES",
    "EFCLIENTE",
    "EFFORNECE",
    "EFFORNECEDOR",
    "EFFORNECEDORES",
)


password = os.environ.pop("CICA_DOMINIO_PASSWORD", "") or getpass.getpass(
    "Senha do usuario externo CICA_NFSE: "
)
connection = pyodbc.connect(
    f"DSN=CICA07129;UID=CICA_NFSE;PWD={password};ASTART=NO;CON=Cica07129SchemaReadOnly",
    timeout=15,
    readonly=True,
)
try:
    cursor = connection.cursor()
    placeholders = ", ".join("?" for _ in TARGET_TABLES)
    cursor.execute(
        "SELECT t.table_name, c.column_name, d.domain_name, c.width, c.nulls, c.column_id "  # noqa: S608
        "FROM SYS.SYSTABLE t "
        "JOIN SYS.SYSCOLUMN c ON c.table_id = t.table_id "
        "JOIN SYS.SYSDOMAIN d ON d.domain_id = c.domain_id "
        f"WHERE t.table_name IN ({placeholders}) "
        "ORDER BY t.table_name, c.column_id",
        *TARGET_TABLES,
    )
    grouped = {name.casefold(): [] for name in TARGET_TABLES}
    for table_name, column_name, type_name, size, nullable, ordinal in cursor.fetchall():
        grouped[str(table_name).casefold()].append(
            {
                "name": str(column_name),
                "type": str(type_name),
                "size": int(size or 0),
                "nullable": str(nullable).upper() == "Y",
                "ordinal": int(ordinal or 0),
            }
        )
    result = [
        {"owner": "bethadba", "table": name, "columns": grouped[name.casefold()]}
        for name in TARGET_TABLES
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print({"matching_tables": len(result), "schema_file": str(OUTPUT)})
finally:
    connection.close()
    password = ""
