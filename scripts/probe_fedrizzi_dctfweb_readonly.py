"""Bounded aggregate ODBC diagnostics for Domínio DCTFWeb source selection.

No row, customer identifier, XML, JSON, credential or tax amount is printed.
The fixed SQL statements only summarize known tables; there is no --apply.
"""

from __future__ import annotations

import argparse
from datetime import date

from apps.intelligence.connectors import ReadOnlyDominoOdbc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", default="contabil", help="System DSN name only")
    args = parser.parse_args()
    adapter = ReadOnlyDominoOdbc(args.dsn)
    queries = {
        "sent_files": (
            "SELECT COUNT(*), COUNT(DISTINCT CODI_EMP), MAX(DATA_ENVIO) "
            "FROM bethadba.FODARF_DCTFWEB_API_ENVIO_ARQUIVOS"
        ),
        "recorded_payments": (
            "SELECT COUNT(*), COUNT(DISTINCT CODI_EMP), MAX(COMPETENCIA) "
            "FROM bethadba.GEDCTF_WEB_PAGAMENTO"
        ),
        "folha_guide_calculations": (
            "SELECT COUNT(*), COUNT(DISTINCT CODI_EMP), MAX(COMPETENCIA), "
            "MAX(VENCIMENTO) FROM bethadba.foguiainss"
        ),
        "escrita_tax_calculations": (
            "SELECT COUNT(*), COUNT(DISTINCT CODI_EMP), MAX(DATA_SIM), "
            "MAX(DVCT_SIM) FROM bethadba.efsdoimp"
        ),
        "escrita_federal_2026": (
            "SELECT COUNT(*), COUNT(DISTINCT s.CODI_EMP), MAX(s.DATA_SIM), "
            "MAX(s.DVCT_SIM) FROM bethadba.efsdoimp s "
            "JOIN (SELECT DISTINCT i.CODI_EMP, i.CODI_IMP FROM bethadba.EFIMPOSTO i "
            "WHERE "
            "(UPPER(i.NOME_IMP) LIKE '%PIS%' OR UPPER(i.NOME_IMP) LIKE '%COFINS%' "
            "OR UPPER(i.NOME_IMP) LIKE '%IRPJ%' OR UPPER(i.NOME_IMP) LIKE '%CSLL%')) i "
            "ON i.CODI_EMP = s.CODI_EMP AND i.CODI_IMP = s.CODI_IMP "
            "WHERE s.DATA_SIM >= '2026-01-01'"
        ),
    }
    with adapter._connect() as connection:  # private diagnostic, not exposed to API/MCP
        cursor = connection.cursor()
        for name, sql in queries.items():
            values = cursor.execute(sql).fetchone()
            summary = tuple(
                value.isoformat() if isinstance(value, date) else value for value in values
            )
            print(f"{name}: {summary}")
        grouped = {
            "sent_file_codes": (
                "SELECT TOP 20 TIPO_ENVIO, SITUACAO, COUNT(*) "
                "FROM bethadba.FODARF_DCTFWEB_API_ENVIO_ARQUIVOS "
                "GROUP BY TIPO_ENVIO, SITUACAO ORDER BY COUNT(*) DESC"
            ),
            "folha_guide_codes": (
                "SELECT TOP 20 TIPO_GUIA, SITUACAO, COUNT(*) "
                "FROM bethadba.foguiainss GROUP BY TIPO_GUIA, SITUACAO "
                "ORDER BY COUNT(*) DESC"
            ),
        }
        for name, sql in grouped.items():
            print(f"{name}: {[tuple(row) for row in cursor.execute(sql).fetchall()]}")


if __name__ == "__main__":
    main()
