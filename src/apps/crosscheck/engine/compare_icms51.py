"""ICMS 51: compras de ativo e consumo cujo XML traz diferimento ("Relação Chaves ICMS51").

O legado listava a chave quando o C190 tinha CFOP 1551/1556 e o XML tinha `ICMS51` em qualquer
lugar, descartava o resto e quebrava sem TXT. Aqui a lista traz, por chave, os valores do
grupo (vICMSOp, pDif, vICMSDif, vICMS) e confere a aritmética vICMSOp - vICMSDif = vICMS.
O CFOP do C190 é o da escrituração (entrada); o do XML é o do emitente. O vínculo é o
documento, não o item.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from .findings import DIVERGENT, Finding, Kind, MatchedRow, RunCancelled, Sink
from .money import brl
from .rules import RuleSet
from .stage import Stage

_PROGRESS_EVERY = 200

_PAIR_SQL = """
SELECT s.id AS sid, s.num_doc, s.key, x.number, x.source, x.icms51, x.emit_doc, x.emit_uf
FROM sped_doc s
JOIN xml_doc x ON x.key = s.key
WHERE s.side = 1 AND s.reg = 'C100' AND s.key <> '' AND s.key_valid = 1
  AND s.cod_sit NOT IN ('02', '03', '04', '05')
  AND s.id = (SELECT MIN(t.id) FROM sped_doc t WHERE t.side = 1 AND t.key = s.key)
  AND EXISTS (
      SELECT 1 FROM sped_analytic a JOIN cfop_set c ON c.cfop = a.cfop WHERE a.doc_id = s.id
  )
ORDER BY CAST(s.num_doc AS INTEGER), s.key
"""

_NO_XML_SQL = """
SELECT s.id AS sid, s.num_doc, s.key, s.vl_icms
FROM sped_doc s
WHERE s.side = 1 AND s.reg = 'C100' AND s.key <> '' AND s.key_valid = 1
  AND s.cod_sit NOT IN ('02', '03', '04', '05')
  AND s.id = (SELECT MIN(t.id) FROM sped_doc t WHERE t.side = 1 AND t.key = s.key)
  AND NOT EXISTS (SELECT 1 FROM xml_doc x WHERE x.key = s.key)
  AND EXISTS (
      SELECT 1 FROM sped_analytic a JOIN cfop_set c ON c.cfop = a.cfop WHERE a.doc_id = s.id
  )
ORDER BY CAST(s.num_doc AS INTEGER), s.key
"""

_MATCHING_ANALYTIC_SQL = """
SELECT a.cst, a.cfop, a.aliq, a.vl_opr, a.vl_bc_icms, a.vl_icms
FROM sped_analytic a JOIN cfop_set c ON c.cfop = a.cfop
WHERE a.doc_id = ? ORDER BY a.line
"""


def _number(value: str) -> str:
    return value.lstrip("0") or "0"


def _arithmetic_ok(item: dict[str, Any]) -> bool:
    if item["v_icms_op"] is None and item["v_icms_dif"] is None:
        return True
    return (item["v_icms_op"] or 0) - (item["v_icms_dif"] or 0) == (item["v_icms"] or 0)


def compare_icms51(stage: Stage, rules: RuleSet, sink: Sink) -> Counter[str]:
    counts: Counter[str] = Counter()
    stage.set_cfops(rules.icms51_cfops)
    stage.conn.commit()
    counts["xml_documentos"] = stage.scalar("SELECT COUNT(*) FROM xml_doc")

    done = 0
    for row in stage.rows(_PAIR_SQL):
        done += 1
        if done % _PROGRESS_EVERY == 0:
            if sink.cancelled():
                raise RunCancelled
            sink.progress("Comparando", done, None)
        counts["sped_com_cfop"] += 1
        items = json.loads(row["icms51"])
        matching = stage.conn.execute(_MATCHING_ANALYTIC_SQL, (row["sid"],)).fetchall()
        cfops = sorted({item["cfop"] for item in matching})
        sped_icms = sum(item["vl_icms"] or 0 for item in matching)
        if not items:
            counts["sem_icms51"] += 1
            sink.matched(
                MatchedRow(
                    doc_key=row["key"],
                    doc_type="nfe",
                    number=_number(row["num_doc"]),
                    operation="E",
                    cfop=" ".join(cfops),
                    values={"vicms": (sped_icms, None)},
                )
            )
            continue
        counts["com_icms51"] += 1
        xml_icms = sum(item["v_icms"] or 0 for item in items)
        sink.finding(
            Finding(
                kind=Kind.ICMS51_CHAVE,
                status=DIVERGENT,
                doc_key=row["key"],
                doc_type="nfe",
                number=_number(row["num_doc"]),
                field="vicms",
                field_label="ICMS",
                left_cents=sped_icms,
                right_cents=xml_icms,
                cfop=" ".join(cfops),
                operation="E",
                message=(
                    f"{len(items)} item(ns) com ICMS 51 no XML; CFOP {', '.join(cfops)} no SPED"
                ),
                detail={
                    "source": row["source"],
                    "emit_doc": row["emit_doc"],
                    "emit_uf": row["emit_uf"],
                    "itens": items,
                    "c190": [
                        {
                            "cst": item["cst"],
                            "cfop": item["cfop"],
                            "aliq": item["aliq"],
                            "vl_opr": item["vl_opr"],
                            "vl_icms": item["vl_icms"],
                        }
                        for item in matching
                    ],
                },
            )
        )
        for item in items:
            if _arithmetic_ok(item):
                continue
            expected = (item["v_icms_op"] or 0) - (item["v_icms_dif"] or 0)
            counts["inconsistencias"] += 1
            sink.finding(
                Finding(
                    kind=Kind.ICMS51_ARITMETICA,
                    status=DIVERGENT,
                    doc_key=row["key"],
                    doc_type="nfe",
                    number=_number(row["num_doc"]),
                    field="vicms",
                    field_label=f"ICMS 51 do item {item['item']}",
                    left_cents=expected,
                    right_cents=item["v_icms"] or 0,
                    cfop=item["cfop"],
                    operation="E",
                    message=(
                        f"Item {item['item']}: vICMSOp - vICMSDif = {brl(expected)}, "
                        f"mas vICMS = {brl(item['v_icms'] or 0)}"
                    ),
                    detail={"item": item},
                )
            )

    for row in stage.rows(_NO_XML_SQL):
        counts["so_sped"] += 1
        sink.finding(
            Finding(
                kind=Kind.SEM_XML,
                status=DIVERGENT,
                doc_key=row["key"],
                doc_type="c100",
                number=_number(row["num_doc"]),
                field="vicms",
                field_label="ICMS",
                left_cents=row["vl_icms"],
                operation="E",
                message="Escriturada com CFOP do ICMS 51 e sem XML para conferir",
            )
        )
    return counts
