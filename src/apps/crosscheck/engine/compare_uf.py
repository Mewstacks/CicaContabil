"""UF x Domínio: a UF da contraparte no XML contra a UF cadastrada no Domínio.

Regra (D-301, item 8): na saída vale a UF do destinatário; na entrada, a do emitente. O
legado comparava sempre a do destinatário, então toda entrada de fornecedor de outro estado
aparecia como divergência. Chave que o Domínio não tem não é "UF diferente": é ausência.
"""

from __future__ import annotations

from collections import Counter
from itertools import groupby

from .findings import DIVERGENT, INFO, Finding, Kind, MatchedRow, RunCancelled, Sink
from .rules import RuleSet
from .stage import Stage

_PROGRESS_EVERY = 500

_SQL = """
SELECT x.key, x.number, x.direction, x.cp_uf, x.source,
       d.uf AS dom_uf, d.direcao AS dom_dir
FROM xml_doc x
LEFT JOIN dominio_uf d ON d.key = x.key
WHERE x.kind = 'nfe' AND x.direction IN ('E', 'S')
ORDER BY CAST(x.number AS INTEGER), x.key, d.direcao
"""


def _number(value: str) -> str:
    return value.lstrip("0") or "0"


def compare_uf_dominio(stage: Stage, rules: RuleSet, sink: Sink) -> Counter[str]:
    del rules  # a ferramenta não tem regras de valor: a UF é igual ou não é
    counts: Counter[str] = Counter()
    counts["xml_documentos"] = stage.scalar("SELECT COUNT(*) FROM xml_doc WHERE kind = 'nfe'")
    counts["dominio_linhas"] = stage.scalar("SELECT COUNT(*) FROM dominio_uf")

    done = 0
    for key, group in groupby(stage.rows(_SQL), key=lambda row: row["key"]):
        rows = list(group)
        first = rows[0]
        done += 1
        if done % _PROGRESS_EVERY == 0:
            if sink.cancelled():
                raise RunCancelled
            sink.progress("Comparando", done, counts["xml_documentos"])
        counts["com_xml"] += 1
        # Se o Domínio tem a chave como saída e como entrada, vale a de mesma direção.
        match = next((r for r in rows if r["dom_dir"] == first["direction"]), None)
        if match is None:
            match = next((r for r in rows if r["dom_uf"] is not None), None)
        xml_uf = first["cp_uf"]
        number = _number(first["number"])
        operation = first["direction"]
        if not xml_uf:
            counts["sem_uf"] += 1
            sink.finding(
                Finding(
                    kind=Kind.SEM_UF_XML,
                    status=INFO,
                    doc_key=key,
                    doc_type="nfe",
                    number=number,
                    field="uf",
                    field_label="UF",
                    left_text="",
                    right_text=match["dom_uf"] if match is not None else "",
                    operation=operation,
                    message="O XML não traz a UF da contraparte (consumidor final)",
                    detail={"source": first["source"]},
                )
            )
            continue
        if match is None:
            counts["sem_dominio"] += 1
            sink.finding(
                Finding(
                    kind=Kind.AUSENTE_DOMINIO,
                    status=DIVERGENT,
                    doc_key=key,
                    doc_type="nfe",
                    number=number,
                    field="uf",
                    field_label="UF",
                    left_text=xml_uf,
                    operation=operation,
                    message="A chave não foi encontrada no Domínio",
                    detail={"source": first["source"]},
                )
            )
            continue
        if match["dom_uf"].upper() != xml_uf.upper():
            counts["divergentes"] += 1
            sink.finding(
                Finding(
                    kind=Kind.UF_DIVERGENTE,
                    status=DIVERGENT,
                    doc_key=key,
                    doc_type="nfe",
                    number=number,
                    field="uf",
                    field_label="UF",
                    left_text=xml_uf,
                    right_text=match["dom_uf"],
                    operation=operation,
                    message=f"UF no XML: {xml_uf} · UF no Domínio: {match['dom_uf']}",
                    detail={"source": first["source"]},
                )
            )
            continue
        counts["conferem"] += 1
        sink.matched(
            MatchedRow(
                doc_key=key,
                doc_type="nfe",
                number=number,
                operation=operation,
                cfop="",
                values={},
            )
        )
    return counts
