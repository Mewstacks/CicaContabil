from __future__ import annotations

import getpass
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time
from pathlib import Path

import pyodbc

OUTPUT = Path(".tmp/07129-extract/accumulator-observations.json")
CATALOG = Path(".tmp/07129-extract/normalized.json")
SNAPSHOT_AT = "2026-09-23T23:00:00+00:00"
SOURCES = (
    (
        "nfse_taken",
        "EFIMPORTADOR_FIXO_NFSE_ENTRADA_ACUMULADOR",
        "EFIMPORTADOR_FIXO_NFSE_ENTRADA_ACUMULADOR_ITEM_SERVICO",
        "EFIMPORTADOR_FIXO_NFSE_ENTRADA_ACUMULADOR_FORNECEDOR",
        "EFFORNECE",
        "CODI_FOR",
        "CGCE_FOR",
    ),
    (
        "nfse_national_taken",
        "EFIMPORTADOR_FIXO_NFSE_NACIONAL_ENTRADA_ACUMULADOR",
        "EFIMPORTADOR_FIXO_NFSE_NACIONAL_ENTRADA_ACUMULADOR_ITEM_SERVICO",
        "EFIMPORTADOR_FIXO_NFSE_NACIONAL_ENTRADA_ACUMULADOR_FORNECEDOR",
        "EFFORNECE",
        "CODI_FOR",
        "CGCE_FOR",
    ),
    (
        "nfse_issued",
        "EFIMPORTADOR_FIXO_NFSE_SERVICO_ACUMULADOR",
        "EFIMPORTADOR_FIXO_NFSE_SERVICO_ACUMULADOR_ITEM_SERVICO",
        "EFIMPORTADOR_FIXO_NFSE_SERVICO_ACUMULADOR_CLIENTE",
        "EFCLIENTES",
        "CODI_CLI",
        "CGCE_CLI",
    ),
    (
        "nfse_national_issued",
        "EFIMPORTADOR_FIXO_NFSE_NACIONAL_SERVICO_ACUMULADOR",
        "EFIMPORTADOR_FIXO_NFSE_NACIONAL_SERVICO_ACUMULADOR_ITEM_SERVICO",
        "EFIMPORTADOR_FIXO_NFSE_NACIONAL_SERVICO_ACUMULADOR_CLIENTE",
        "EFCLIENTES",
        "CODI_CLI",
        "CGCE_CLI",
    ),
)


def _counterparty_ref(value: object) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) not in {11, 14}:
        return ""
    return hashlib.sha256(digits.encode()).hexdigest()[:24]


def _observed_at(value: object) -> str:
    if isinstance(value, datetime):
        observed = value
    elif isinstance(value, date):
        observed = datetime.combine(value, time.min)
    else:
        return SNAPSHOT_AT
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)
    return observed.astimezone(UTC).isoformat()


catalog_payload = json.loads(CATALOG.read_text(encoding="utf-8"))
catalog_keys = {
    (str(row["company_key"]), str(row["accumulator_code"]))
    for row in catalog_payload["accumulator_catalog"]
}
password = os.environ.pop("CICA_DOMINIO_PASSWORD", "") or getpass.getpass(
    "Senha do usuario externo CICA_NFSE: "
)
connection = pyodbc.connect(
    f"DSN=CICA07129;UID=CICA_NFSE;PWD={password};ASTART=NO;CON=Cica07129RuleReadOnly",
    timeout=15,
    readonly=True,
)
try:
    cursor = connection.cursor()
    observations: dict[tuple[str, str, str, str], dict[str, object]] = {}
    source_counts: Counter[str] = Counter()
    raw_rows = 0
    missing_catalog = 0
    for source, parent, item_table, party_table, master, party_code, document in SOURCES:
        query = (
            f"SELECT p.CODI_EMP, p.CODI_ACU, i.ITEM_SERVICO, m.{document} "  # noqa: S608
            f"FROM bethadba.{parent} p "
            f"LEFT JOIN bethadba.{item_table} i ON i.CODI_EMP = p.CODI_EMP "
            "AND i.I_ACUMULADOR = p.I_ACUMULADOR "
            f"LEFT JOIN bethadba.{party_table} x ON x.CODI_EMP = p.CODI_EMP "
            "AND x.I_ACUMULADOR = p.I_ACUMULADOR "
            f"LEFT JOIN bethadba.{master} m ON m.CODI_EMP = x.CODI_EMP "
            f"AND m.{party_code} = x.{party_code} "
            "WHERE p.CODI_ACU IS NOT NULL"
        )
        cursor.execute(query)
        for company, accumulator, service, party_document in cursor.fetchall():
            raw_rows += 1
            company_key = str(company).strip()
            accumulator_code = str(accumulator).strip()
            service_code = str(service or "").strip()[:60]
            counterparty_ref = _counterparty_ref(party_document)
            if not service_code and not counterparty_ref:
                continue
            if (company_key, accumulator_code) not in catalog_keys:
                missing_catalog += 1
                continue
            key = (company_key, accumulator_code, service_code, counterparty_ref)
            observations[key] = {
                "company_key": company_key,
                "accumulator_code": accumulator_code,
                "service_code": service_code,
                "counterparty_ref": counterparty_ref,
                "frequency": 20,
                "last_used_at": SNAPSHOT_AT,
            }
            source_counts[source] += 1

    history_queries = (
        (
            "issued_history",
            "SELECT s.codi_emp, s.codi_acu, s.RN_CODIGO_TRIBUTACAO, c.cgce_cli, "
            "COUNT(*), MAX(COALESCE(s.DATA_SERVICO, s.dser_ser, s.ddoc_ser)) "
            "FROM bethadba.efservicos s "
            "JOIN bethadba.efclientes c ON c.codi_emp = s.codi_emp AND c.codi_cli = s.codi_cli "
            "WHERE s.codi_acu IS NOT NULL "
            "GROUP BY s.codi_emp, s.codi_acu, s.RN_CODIGO_TRIBUTACAO, c.cgce_cli",
        ),
        (
            "taken_history",
            "SELECT e.codi_emp, e.codi_acu, NULL, f.cgce_for, COUNT(*), "
            "MAX(COALESCE(e.DATA_ENTRADA, e.dent_ent, e.ddoc_ent)) "
            "FROM bethadba.efentradas e "
            "JOIN bethadba.effornece f ON f.codi_emp = e.codi_emp AND f.codi_for = e.codi_for "
            "WHERE e.codi_acu IS NOT NULL AND ("
            "(e.CHAVE_NFSE_ENT IS NOT NULL AND TRIM(e.CHAVE_NFSE_ENT) <> '') "
            "OR e.TIPO_SERVICO IS NOT NULL) "
            "GROUP BY e.codi_emp, e.codi_acu, f.cgce_for",
        ),
    )
    for source, query in history_queries:
        cursor.execute(query)
        for (
            company,
            accumulator,
            service,
            party_document,
            frequency,
            last_used,
        ) in cursor.fetchall():
            raw_rows += 1
            company_key = str(company).strip()
            accumulator_code = str(accumulator).strip()
            service_code = str(service or "").strip()[:60]
            counterparty_ref = _counterparty_ref(party_document)
            if not service_code and not counterparty_ref:
                continue
            if (company_key, accumulator_code) not in catalog_keys:
                missing_catalog += 1
                continue
            key = (company_key, accumulator_code, service_code, counterparty_ref)
            existing = observations.get(key)
            normalized_frequency = max(1, int(frequency or 1))
            normalized_last_used = _observed_at(last_used)
            if existing:
                existing["frequency"] = int(existing["frequency"]) + normalized_frequency
                existing["last_used_at"] = max(str(existing["last_used_at"]), normalized_last_used)
            else:
                observations[key] = {
                    "company_key": company_key,
                    "accumulator_code": accumulator_code,
                    "service_code": service_code,
                    "counterparty_ref": counterparty_ref,
                    "frequency": normalized_frequency,
                    "last_used_at": normalized_last_used,
                }
            source_counts[source] += 1

    mapping = defaultdict(set)
    for company, accumulator, service, counterparty in observations:
        mapping[(company, service, counterparty)].add(accumulator)
    conflicts = sum(len(accumulators) > 1 for accumulators in mapping.values())
    rows = sorted(
        observations.values(),
        key=lambda row: (
            str(row["company_key"]),
            str(row["accumulator_code"]),
            str(row["service_code"]),
            str(row["counterparty_ref"]),
        ),
    )
    payload = {
        "tenant": "bianchi-rizzotto",
        "source": "dominio-backup-07129",
        "captured_at_utc": SNAPSHOT_AT,
        "kind": "accumulator_observations",
        "rows": rows,
        "integrity": {
            "raw_rule_combinations": raw_rows,
            "normalized_observations": len(rows),
            "ambiguous_match_keys": conflicts,
            "missing_catalog": missing_catalog,
            "source_counts": dict(sorted(source_counts.items())),
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print({"schema_file": str(OUTPUT), **payload["integrity"]})
finally:
    connection.close()
    password = ""
