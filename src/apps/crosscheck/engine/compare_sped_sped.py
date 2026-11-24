"""SPED x SPED: duas EFD ICMS/IPI conferidas entre si (substitui o "Cruzamento Speds").

O legado ligava os documentos por texto de DataFrame, comparava o analítico só pelo conjunto
de CFOP (C190) ou pelo primeiro D190 (D100) e quebrava sem bloco D. Aqui os documentos se
ligam pela chave de acesso (ou, sem ela, pelo que identifica o documento), os campos são
comparados um a um e o analítico é comparado linha a linha por CST + CFOP + alíquota.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from typing import Any

from .findings import DIVERGENT, Finding, Kind, MatchedRow, RunCancelled, Sink
from .money import brl, rate_text
from .rules import SPED_SPED_FIELDS, RuleSet
from .stage import Stage

_PROGRESS_EVERY = 200
_ANALYTIC_VALUES = (
    ("vl_opr", "Valor da operação"),
    ("vl_bc_icms", "Base do ICMS"),
    ("vl_icms", "ICMS"),
    ("vl_bc_icms_st", "Base do ICMS ST"),
    ("vl_icms_st", "ICMS ST"),
    ("vl_red_bc", "Redução da base"),
    ("vl_ipi", "IPI"),
)

_ONLY_SQL = """
SELECT a.id, a.reg, a.ind_oper, a.num_doc, a.key, a.mkey, a.vl_doc, a.cod_sit
FROM sped_doc a
WHERE a.side = :mine AND a.ind_oper IN (:op1, :op2)
  AND a.id = (SELECT MIN(t.id) FROM sped_doc t WHERE t.side = :mine AND t.mkey = a.mkey)
  AND NOT EXISTS (SELECT 1 FROM sped_doc b WHERE b.side = :other AND b.mkey = a.mkey)
ORDER BY CAST(a.num_doc AS INTEGER), a.mkey
"""

_PAIR_SQL = """
SELECT a.id AS a_id, b.id AS b_id
FROM sped_doc a
JOIN sped_doc b ON b.side = 2 AND b.mkey = a.mkey
WHERE a.side = 1 AND a.ind_oper IN (?, ?)
  AND a.id = (SELECT MIN(t.id) FROM sped_doc t WHERE t.side = 1 AND t.mkey = a.mkey)
  AND b.id = (SELECT MIN(t.id) FROM sped_doc t WHERE t.side = 2 AND t.mkey = b.mkey)
ORDER BY CAST(a.num_doc AS INTEGER), a.mkey
"""

_DUPLICATE_SQL = """
SELECT key, COUNT(*) AS n, MIN(num_doc) AS num_doc, MIN(ind_oper) AS ind_oper, MIN(reg) AS reg
FROM sped_doc
WHERE side = ? AND key <> '' AND ind_oper IN (?, ?)
GROUP BY key HAVING COUNT(*) > 1
ORDER BY CAST(MIN(num_doc) AS INTEGER), key
"""

_INVALID_KEY_SQL = """
SELECT key, num_doc, ind_oper, reg FROM sped_doc
WHERE side = ? AND key <> '' AND key_valid = 0 AND ind_oper IN (?, ?)
ORDER BY CAST(num_doc AS INTEGER), key
"""


def _number(value: str) -> str:
    return value.lstrip("0") or "0"


def _operation(ind_oper: str) -> str:
    return "E" if ind_oper == "0" else "S"


def _doc_type(reg: str) -> str:
    return reg.lower()


def _analytic_label(row: sqlite3.Row | dict[str, Any]) -> str:
    return f"CST {row['cst']} · CFOP {row['cfop']} · {rate_text(row['aliq'])}%"


def _index_analytic(rows: list[sqlite3.Row]) -> dict[tuple[str, str, int | None], dict[str, Any]]:
    """Linhas do analítico por CST + CFOP + alíquota (somadas, se o arquivo repetir)."""

    grouped: dict[tuple[str, str, int | None], dict[str, Any]] = {}
    for row in rows:
        key = (row["cst"], row["cfop"], row["aliq"])
        target = grouped.setdefault(
            key, {"cst": row["cst"], "cfop": row["cfop"], "aliq": row["aliq"]}
        )
        for column, _ in _ANALYTIC_VALUES:
            value = row[column]
            if value is not None:
                target[column] = (target.get(column) or 0) + value
            else:
                target.setdefault(column, None)
    return grouped


def compare_sped_sped(stage: Stage, rules: RuleSet, sink: Sink) -> Counter[str]:
    counts: Counter[str] = Counter()
    op1, op2 = rules.operation_filter()
    tolerance = rules.tolerance_cents
    fields = [code for code in rules.fields if code in SPED_SPED_FIELDS]
    counts["sped1_documentos"] = stage.scalar(
        "SELECT COUNT(*) FROM sped_doc WHERE side = 1 AND ind_oper IN (?, ?)", (op1, op2)
    )
    counts["sped2_documentos"] = stage.scalar(
        "SELECT COUNT(*) FROM sped_doc WHERE side = 2 AND ind_oper IN (?, ?)", (op1, op2)
    )

    # 1) só em um dos arquivos
    for mine, other, kind, name in ((1, 2, Kind.SOMENTE_1, "so_1"), (2, 1, Kind.SOMENTE_2, "so_2")):
        params = {"mine": mine, "other": other, "op1": op1, "op2": op2}
        for row in stage.rows(_ONLY_SQL, params):
            counts[name] += 1
            sink.finding(
                Finding(
                    kind=kind,
                    status=DIVERGENT,
                    doc_key=row["key"] or row["mkey"],
                    doc_type=_doc_type(row["reg"]),
                    number=_number(row["num_doc"]),
                    field="vl_doc",
                    field_label=SPED_SPED_FIELDS["vl_doc"][0],
                    left_cents=row["vl_doc"] if mine == 1 else None,
                    right_cents=row["vl_doc"] if mine == 2 else None,
                    operation=_operation(row["ind_oper"]),
                    message=f"Documento só no SPED {mine}",
                )
            )

    # 2) nos dois: campos do documento e analítico
    for done, pair in enumerate(stage.rows(_PAIR_SQL, (op1, op2)), start=1):
        if done % _PROGRESS_EVERY == 0:
            if sink.cancelled():
                raise RunCancelled
            sink.progress("Comparando", done, counts["sped1_documentos"])
        left = stage.conn.execute("SELECT * FROM sped_doc WHERE id = ?", (pair["a_id"],)).fetchone()
        right = stage.conn.execute(
            "SELECT * FROM sped_doc WHERE id = ?", (pair["b_id"],)
        ).fetchone()
        counts["nos_dois"] += 1
        before = counts["divergentes_docs"]
        diverged = _compare_documents(stage, rules, left, right, fields, tolerance, sink, counts)
        if diverged:
            counts["divergentes_docs"] = before + 1
        else:
            counts["conferem"] += 1

    # 3) chaves repetidas ou inválidas em cada arquivo
    for side in (1, 2):
        for row in stage.rows(_DUPLICATE_SQL, (side, op1, op2)):
            counts["chaves_duplicadas"] += 1
            sink.finding(
                Finding(
                    kind=Kind.CHAVE_DUPLICADA,
                    status=DIVERGENT,
                    doc_key=row["key"],
                    doc_type=_doc_type(row["reg"]),
                    number=_number(row["num_doc"]),
                    operation=_operation(row["ind_oper"]),
                    message=f"Chave escriturada {row['n']} vezes no SPED {side}",
                    detail={"arquivo": side, "vezes": row["n"]},
                )
            )
        for row in stage.rows(_INVALID_KEY_SQL, (side, op1, op2)):
            counts["chaves_invalidas"] += 1
            sink.finding(
                Finding(
                    kind=Kind.CHAVE_INVALIDA,
                    status=DIVERGENT,
                    doc_key=row["key"],
                    doc_type=_doc_type(row["reg"]),
                    number=_number(row["num_doc"]),
                    operation=_operation(row["ind_oper"]),
                    message=f"Chave com dígito verificador inválido no SPED {side}",
                    detail={"arquivo": side},
                )
            )
    return counts


def _compare_documents(
    stage: Stage,
    rules: RuleSet,
    left: sqlite3.Row,
    right: sqlite3.Row,
    fields: list[str],
    tolerance: int,
    sink: Sink,
    counts: Counter[str],
) -> bool:
    key = left["key"] or left["mkey"]
    doc_type = _doc_type(left["reg"])
    number = _number(left["num_doc"])
    operation = _operation(left["ind_oper"])
    diverged = False
    values: dict[str, tuple[int | None, int | None]] = {}

    for code in fields:
        label, kind = SPED_SPED_FIELDS[code]
        a, b = left[code], right[code]
        if kind == "money":
            if a is None and b is None:
                continue
            values[code] = (a, b)
            if abs((a or 0) - (b or 0)) <= tolerance:
                continue
            counts["campos_divergentes"] += 1
            diverged = True
            sink.finding(
                Finding(
                    kind=Kind.VALOR_DIVERGENTE,
                    status=DIVERGENT,
                    doc_key=key,
                    doc_type=doc_type,
                    number=number,
                    field=code,
                    field_label=label,
                    left_cents=a,
                    right_cents=b,
                    operation=operation,
                    message=f"{label}: SPED 1 {brl(a or 0)} · SPED 2 {brl(b or 0)}",
                )
            )
        else:
            a_text, b_text = (a or "").strip(), (b or "").strip()
            if a_text == b_text:
                continue
            counts["campos_divergentes"] += 1
            diverged = True
            sink.finding(
                Finding(
                    kind=Kind.VALOR_DIVERGENTE,
                    status=DIVERGENT,
                    doc_key=key,
                    doc_type=doc_type,
                    number=number,
                    field=code,
                    field_label=label,
                    left_text=a_text,
                    right_text=b_text,
                    operation=operation,
                    message=f"{label}: SPED 1 {a_text or '—'} · SPED 2 {b_text or '—'}",
                )
            )

    if rules.include_analytic:
        diverged = (
            _compare_analytic(
                stage, left, right, key, doc_type, number, operation, tolerance, sink, counts
            )
            or diverged
        )
    if not diverged:
        sink.matched(
            MatchedRow(
                doc_key=key,
                doc_type=doc_type,
                number=number,
                operation=operation,
                cfop="",
                values=values,
            )
        )
    return diverged


def _compare_analytic(
    stage: Stage,
    left: sqlite3.Row,
    right: sqlite3.Row,
    key: str,
    doc_type: str,
    number: str,
    operation: str,
    tolerance: int,
    sink: Sink,
    counts: Counter[str],
) -> bool:
    diverged = False
    mine = _index_analytic(stage.analytics(left["id"]))
    other = _index_analytic(stage.analytics(right["id"]))
    for item_key, row in mine.items():
        if item_key not in other:
            diverged = True
            counts["analitico_somente_1"] += 1
            sink.finding(
                Finding(
                    kind=Kind.ANALITICO_SOMENTE_1,
                    status=DIVERGENT,
                    doc_key=key,
                    doc_type=doc_type,
                    number=number,
                    field="analitico",
                    field_label="Analítico",
                    left_cents=row.get("vl_opr"),
                    left_text=_analytic_label(row),
                    cfop=row["cfop"],
                    operation=operation,
                    message=f"{_analytic_label(row)} só no SPED 1",
                )
            )
            continue
        twin = other[item_key]
        for column, label in _ANALYTIC_VALUES:
            a, b = row.get(column), twin.get(column)
            if a is None and b is None:
                continue
            if abs((a or 0) - (b or 0)) <= tolerance:
                continue
            diverged = True
            counts["analitico_valor"] += 1
            sink.finding(
                Finding(
                    kind=Kind.ANALITICO_VALOR,
                    status=DIVERGENT,
                    doc_key=key,
                    doc_type=doc_type,
                    number=number,
                    field=f"analitico.{column}",
                    field_label=f"{label} ({_analytic_label(row)})",
                    left_cents=a,
                    right_cents=b,
                    cfop=row["cfop"],
                    operation=operation,
                    message=(
                        f"{label} em {_analytic_label(row)}: "
                        f"SPED 1 {brl(a or 0)} · SPED 2 {brl(b or 0)}"
                    ),
                )
            )
    for item_key, row in other.items():
        if item_key in mine:
            continue
        diverged = True
        counts["analitico_somente_2"] += 1
        sink.finding(
            Finding(
                kind=Kind.ANALITICO_SOMENTE_2,
                status=DIVERGENT,
                doc_key=key,
                doc_type=doc_type,
                number=number,
                field="analitico",
                field_label="Analítico",
                right_cents=row.get("vl_opr"),
                right_text=_analytic_label(row),
                cfop=row["cfop"],
                operation=operation,
                message=f"{_analytic_label(row)} só no SPED 2",
            )
        )
    return diverged
