"""SPED x XML: confere C100/D100 da EFD ICMS/IPI contra NF-e, NFC-e e CT-e (D-301).

Ligação pela chave de acesso. Cada documento escriturado vira uma de quatro coisas: confere,
diverge em algum campo, diverge na situação (cancelado de um lado e não do outro) ou não
tem XML; cada XML da empresa que não está no SPED vira "XML não escriturado". Nada some em
silêncio: o que uma regra rebaixa fica em `ignored` e é listado e exportado.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from typing import Any

from .findings import (
    DIVERGENT,
    IGNORED,
    Finding,
    Kind,
    MatchedRow,
    RunCancelled,
    Sink,
)
from .money import brl
from .rules import CREDIT_RELATED, SPED_XML_FIELDS, RuleSet
from .stage import Stage

#: Situações do documento (Tabela 4.1.2) em que o SPED não traz valores.
CANCELLED_SIT = frozenset({"02", "03", "04", "05"})
SIT_LABELS = {
    "00": "Regular",
    "01": "Extemporâneo",
    "02": "Cancelado",
    "03": "Cancelado extemporâneo",
    "04": "Denegado",
    "05": "Inutilizado",
    "06": "Complementar",
    "07": "Complementar extemporâneo",
    "08": "Regime especial",
}
STATUS_LABELS = {
    "autorizada": "Autorizada",
    "cancelada": "Cancelada",
    "denegada": "Denegada",
    "sem_protocolo": "Sem protocolo",
    "outro": "Outro status",
}

#: campo -> coluna do SPED
_SPED_COLUMN = {
    "vnf": "vl_doc",
    "vicms": "vl_icms",
    "vipi": "vl_ipi",
    "vbc": "vl_bc_icms",
    "vbcst": "vl_bc_icms_st",
    "vst": "vl_icms_st",
    "vprod": "vl_merc",
    "vfrete": "vl_frt",
    "vseg": "vl_seg",
    "vdesc": "vl_desc",
    "voutro": "vl_out_da",
    "vpis": "vl_pis",
    "vcofins": "vl_cofins",
}
#: Campos que existem no CT-e.
_CTE_FIELDS = frozenset({"vnf", "vicms", "vbc"})
_MAX_C190_IN_DETAIL = 20
_PROGRESS_EVERY = 200

_MATCHED_SQL = """
SELECT s.id AS sid, s.ind_oper, s.cod_sit, s.num_doc, s.key,
       s.vl_doc, s.vl_icms, s.vl_ipi, s.vl_bc_icms, s.vl_bc_icms_st, s.vl_icms_st, s.vl_merc,
       s.vl_frt, s.vl_seg, s.vl_desc, s.vl_out_da, s.vl_pis, s.vl_cofins,
       x.kind, x.c_stat, x.status_group, x.source,
       x.vnf, x.vicms, x.vipi, x.vipi_devol, x.vcred_sn, x.vbc, x.vbcst, x.vst, x.vprod,
       x.vfrete, x.vseg, x.vdesc, x.voutro, x.vpis, x.vcofins, x.vtprest, x.icms_by_cfop
FROM sped_doc s
JOIN xml_doc x ON x.key = s.key
WHERE s.side = 1 AND s.key <> '' AND s.key_valid = 1 AND s.ind_oper IN (?, ?)
  AND s.id = (SELECT MIN(t.id) FROM sped_doc t WHERE t.side = 1 AND t.key = s.key)
ORDER BY CAST(s.num_doc AS INTEGER), s.key
"""

_NO_XML_SQL = """
SELECT s.ind_oper, s.cod_sit, s.num_doc, s.key, s.vl_doc
FROM sped_doc s
WHERE s.side = 1 AND s.key <> '' AND s.key_valid = 1 AND s.ind_oper IN (?, ?)
  AND NOT EXISTS (SELECT 1 FROM xml_doc x WHERE x.key = s.key)
  AND s.id = (SELECT MIN(t.id) FROM sped_doc t WHERE t.side = 1 AND t.key = s.key)
ORDER BY CAST(s.num_doc AS INTEGER), s.key
"""

_XML_ONLY_SQL = """
SELECT x.key, x.kind, x.number, x.direction, x.status_group, x.source, x.vnf, x.vtprest
FROM xml_doc x
WHERE x.direction IN (?, ?)
  AND NOT EXISTS (SELECT 1 FROM sped_doc s WHERE s.side = 1 AND s.key = x.key)
ORDER BY CAST(x.number AS INTEGER), x.key
"""

_DUPLICATE_SQL = """
SELECT key, COUNT(*) AS n, MIN(num_doc) AS num_doc, MIN(ind_oper) AS ind_oper
FROM sped_doc
WHERE side = 1 AND key <> '' AND ind_oper IN (?, ?)
GROUP BY key HAVING COUNT(*) > 1
ORDER BY CAST(MIN(num_doc) AS INTEGER), key
"""

_INVALID_KEY_SQL = """
SELECT key, num_doc, ind_oper FROM sped_doc
WHERE side = 1 AND key <> '' AND key_valid = 0 AND ind_oper IN (?, ?)
ORDER BY CAST(num_doc AS INTEGER), key
"""


def _operation(ind_oper: str) -> str:
    return "E" if ind_oper == "0" else "S"


def _xml_value(code: str, row: sqlite3.Row) -> int:
    if code == "vnf":
        value = row["vtprest"] if row["kind"] == "cte" else row["vnf"]
        return int(value or 0)
    if code == "vipi":
        return int(row["vipi"] or 0) + int(row["vipi_devol"] or 0)
    return int(row[code] or 0)


def _analytic_detail(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [
        {
            "cst": item["cst"],
            "cfop": item["cfop"],
            "aliq": item["aliq"],
            "vl_opr": item["vl_opr"],
            "vl_bc_icms": item["vl_bc_icms"],
            "vl_icms": item["vl_icms"],
            "vl_ipi": item["vl_ipi"],
        }
        for item in rows[:_MAX_C190_IN_DETAIL]
    ]


def _number(value: str) -> str:
    return value.lstrip("0") or "0"


def _check_cancelled(sink: Sink) -> None:
    if sink.cancelled():
        raise RunCancelled


def compare_sped_xml(stage: Stage, rules: RuleSet, sink: Sink) -> Counter[str]:
    counts: Counter[str] = Counter()
    operation = rules.operation_filter()
    directions = rules.direction_filter()
    cancelled_by_event = stage.event_cancelled_keys()
    fields = [code for code in rules.fields if code in SPED_XML_FIELDS]
    tolerance = rules.tolerance_cents

    counts["sped_documentos"] = stage.scalar(
        "SELECT COUNT(*) FROM sped_doc WHERE side = 1 AND ind_oper IN (?, ?)", operation
    )
    counts["sped_sem_chave"] = stage.scalar(
        "SELECT COUNT(*) FROM sped_doc WHERE side = 1 AND key = '' AND ind_oper IN (?, ?)",
        operation,
    )
    counts["xml_documentos"] = stage.scalar("SELECT COUNT(*) FROM xml_doc")

    # 1) documentos escriturados que têm XML
    for done, row in enumerate(stage.rows(_MATCHED_SQL, operation), start=1):
        if done % _PROGRESS_EVERY == 0:
            _check_cancelled(sink)
            sink.progress("Comparando", done, counts["sped_documentos"])
        _compare_pair(stage, rules, row, fields, tolerance, cancelled_by_event, sink, counts)

    # 2) escriturados sem XML
    for row in stage.rows(_NO_XML_SQL, operation):
        if row["cod_sit"] in CANCELLED_SIT:
            counts["cancelados_sem_xml"] += 1
            continue
        counts["so_sped"] += 1
        sink.finding(
            Finding(
                kind=Kind.SEM_XML,
                status=DIVERGENT,
                doc_key=row["key"],
                doc_type="c100",
                number=_number(row["num_doc"]),
                field="vnf",
                field_label=SPED_XML_FIELDS["vnf"],
                left_cents=row["vl_doc"],
                operation=_operation(row["ind_oper"]),
                message="Escriturada no SPED e sem XML na conferência",
            )
        )

    # 3) XML da empresa que não está no SPED
    for row in stage.rows(_XML_ONLY_SQL, directions):
        if row["status_group"] in {"cancelada", "denegada"} or row["key"] in cancelled_by_event:
            counts["xml_cancelados_fora_do_sped"] += 1
            continue
        counts["so_xml"] += 1
        value = row["vtprest"] if row["kind"] == "cte" else row["vnf"]
        sink.finding(
            Finding(
                kind=Kind.XML_NAO_ESCRITURADO,
                status=DIVERGENT,
                doc_key=row["key"],
                doc_type=row["kind"],
                number=_number(row["number"]),
                field="vnf",
                field_label=SPED_XML_FIELDS["vnf"],
                right_cents=value,
                operation=row["direction"],
                message="XML da empresa que não está escriturado no SPED",
                detail={"source": row["source"]},
            )
        )

    # 4) chaves repetidas e chaves com DV errado no SPED
    for row in stage.rows(_DUPLICATE_SQL, operation):
        counts["chaves_duplicadas"] += 1
        sink.finding(
            Finding(
                kind=Kind.CHAVE_DUPLICADA,
                status=DIVERGENT,
                doc_key=row["key"],
                doc_type="c100",
                number=_number(row["num_doc"]),
                operation=_operation(row["ind_oper"]),
                message=f"Chave escriturada {row['n']} vezes no SPED",
                detail={"vezes": row["n"]},
            )
        )
    for row in stage.rows(_INVALID_KEY_SQL, operation):
        counts["chaves_invalidas"] += 1
        sink.finding(
            Finding(
                kind=Kind.CHAVE_INVALIDA,
                status=DIVERGENT,
                doc_key=row["key"],
                doc_type="c100",
                number=_number(row["num_doc"]),
                operation=_operation(row["ind_oper"]),
                message="Chave de acesso com dígito verificador inválido no SPED",
            )
        )
    return counts


def _compare_pair(
    stage: Stage,
    rules: RuleSet,
    row: sqlite3.Row,
    fields: list[str],
    tolerance: int,
    cancelled_by_event: set[str],
    sink: Sink,
    counts: Counter[str],
) -> None:
    key = row["key"]
    doc_type = row["kind"]
    number = _number(row["num_doc"])
    operation = _operation(row["ind_oper"])
    counts["com_xml"] += 1
    xml_cancelled = row["status_group"] in {"cancelada", "denegada"} or key in cancelled_by_event
    sped_cancelled = row["cod_sit"] in CANCELLED_SIT

    if sped_cancelled:
        if xml_cancelled or row["status_group"] not in {"autorizada"}:
            counts["cancelados_conferem"] += 1
            return
        counts["situacao_divergente"] += 1
        sink.finding(
            Finding(
                kind=Kind.SITUACAO_DIVERGENTE,
                status=DIVERGENT,
                doc_key=key,
                doc_type=doc_type,
                number=number,
                left_text=f"{row['cod_sit']} · {SIT_LABELS.get(row['cod_sit'], 'Situação')}",
                right_text=f"{row['c_stat']} · {STATUS_LABELS[row['status_group']]}",
                operation=operation,
                message="Cancelada no SPED, mas o XML está autorizado e sem evento de cancelamento",
                detail={"source": row["source"]},
            )
        )
        return
    if xml_cancelled:
        counts["situacao_divergente"] += 1
        label = "Cancelada" if key in cancelled_by_event else STATUS_LABELS[row["status_group"]]
        sink.finding(
            Finding(
                kind=Kind.SITUACAO_DIVERGENTE,
                status=DIVERGENT,
                doc_key=key,
                doc_type=doc_type,
                number=number,
                left_text=f"{row['cod_sit']} · {SIT_LABELS.get(row['cod_sit'], 'Situação')}",
                right_text=label,
                operation=operation,
                message=f"Escriturada no SPED, mas o XML está {label.lower()}",
                detail={"source": row["source"]},
            )
        )
        return

    applicable = [code for code in fields if doc_type != "cte" or code in _CTE_FIELDS]
    mismatches: list[tuple[str, int | None, int]] = []
    compared: dict[str, tuple[int | None, int | None]] = {}
    for code in applicable:
        sped = row[_SPED_COLUMN[code]]
        # Campos de valor do SPED em branco só valem como zero fora de C100/D100 cancelados.
        if sped is None and row["cod_sit"] in {"06", "07", "08"}:
            continue  # situações em que o campo é facultativo
        xml = _xml_value(code, row)
        value = sped or 0
        accepted = abs(value - xml) <= tolerance
        if not accepted and code == "vicms":
            credit = int(row["vcred_sn"] or 0)
            accepted = credit > 0 and abs(value - credit) <= tolerance
        compared[code] = (sped, xml)
        if not accepted:
            mismatches.append((code, sped, xml))

    if not mismatches:
        counts["conferem"] += 1
        analytics = stage.analytics(row["sid"])
        sink.matched(
            MatchedRow(
                doc_key=key,
                doc_type=doc_type,
                number=number,
                operation=operation,
                cfop=" ".join(sorted({item["cfop"] for item in analytics})),
                values=compared,
            )
        )
        return

    analytics = stage.analytics(row["sid"])
    cfops = {item["cfop"] for item in analytics}
    no_credit = bool(cfops) and cfops <= rules.no_credit_cfops
    icms_by_cfop = json.loads(row["icms_by_cfop"])
    any_divergent = False
    for code, sped, xml in mismatches:
        ignored = no_credit and row["ind_oper"] == "0" and code in CREDIT_RELATED
        status = IGNORED if ignored else DIVERGENT
        any_divergent = any_divergent or not ignored
        label = SPED_XML_FIELDS[code]
        message = (
            f"{label}: SPED {brl(sped or 0)} · XML {brl(xml)}"
            if not ignored
            else f"{label} sem crédito (CFOP {', '.join(sorted(cfops))}): diferença esperada"
        )
        sink.finding(
            Finding(
                kind=Kind.VALOR_DIVERGENTE,
                status=status,
                doc_key=key,
                doc_type=doc_type,
                number=number,
                field=code,
                field_label=label,
                left_cents=sped,
                right_cents=xml,
                cfop=" ".join(sorted(cfops)),
                operation=operation,
                message=message,
                detail={
                    "source": row["source"],
                    "reason": "cfop_sem_credito" if ignored else "",
                    "sped_vazio": sped is None,
                    "cred_sn": int(row["vcred_sn"] or 0),
                    "icms_por_cfop": icms_by_cfop,
                    "c190": _analytic_detail(analytics),
                },
            )
        )
    counts["divergentes" if any_divergent else "ignorados"] += 1
