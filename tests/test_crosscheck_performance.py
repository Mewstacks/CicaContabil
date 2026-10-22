"""Orçamento de memória e de tempo do motor do Contraprova.

O worker do Fly tem cerca de 110 MB livres (Celery já usa ~350 MB dos 512) e a tarefa morre aos
300 s. O motor guarda o preparo num SQLite em disco e lê SPED/XML em streaming; este teste
prova isso com um arquivo grande, medindo o pico de alocações do Python (`tracemalloc`) e o
tempo, sem guardar os achados na memória (o serviço grava no banco e no XLSX).
"""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path

import pytest

from apps.crosscheck.engine import runner
from apps.crosscheck.engine.findings import Finding, MatchedRow
from apps.crosscheck.engine.rules import RuleSet
from apps.crosscheck.synthetic import (
    AnalyticSpec,
    DocSpec,
    EfdSpec,
    NfeSpec,
    build_efd,
    build_nfe_xml,
    build_zip,
    make_cnpj,
    make_key,
)

EMPRESA = make_cnpj("12345678", "0001")
FORNECEDOR = make_cnpj("98765432", "0001")
DOCUMENTOS = 30_000
XMLS = 4_000
ORCAMENTO_PICO_BYTES = 32 * 1024 * 1024
ORCAMENTO_SEGUNDOS = 120


class SinkContador:
    """Só conta: guardar 100 mil achados na memória não é o que o serviço faz."""

    def __init__(self) -> None:
        self.achados = 0
        self.conferem = 0

    def finding(self, finding: Finding) -> None:
        self.achados += 1

    def matched(self, row: MatchedRow) -> None:
        self.conferem += 1

    def progress(self, stage: str, done: int, total: int | None = None) -> None:
        return None

    def cancelled(self) -> bool:
        return False


@pytest.mark.performance
def test_sped_de_90_mil_linhas_e_4_mil_xml_cabem_no_orcamento(tmp_path: Path) -> None:
    docs = [
        DocSpec(
            number=n,
            key=make_key(cnpj=FORNECEDOR, number=n),
            vl_doc="100,00",
            analytics=[AnalyticSpec(cfop="1102"), AnalyticSpec(cfop="1403", aliq="12,00")],
        )
        for n in range(1, DOCUMENTOS + 1)
    ]
    sped = build_efd(EfdSpec(cnpj=EMPRESA, docs=docs))
    del docs
    xmls = {
        f"n{n}.xml": build_nfe_xml(
            NfeSpec(
                key=make_key(cnpj=FORNECEDOR, number=n),
                emit_cnpj=FORNECEDOR,
                dest_cnpj=EMPRESA,
                number=n,
                v_nf="100.00" if n % 100 else "101.00",
            )
        )
        for n in range(1, XMLS + 1)
    }
    (tmp_path / "in").mkdir()
    (tmp_path / "work").mkdir()
    (tmp_path / "in" / "sped.txt").write_bytes(sped)
    (tmp_path / "in" / "xml.zip").write_bytes(build_zip(xmls))
    linhas = sped.count(b"\n")
    del sped, xmls
    assert linhas > 90_000

    sink = SinkContador()
    inputs = [
        runner.InputFile("sped", tmp_path / "in" / "sped.txt", "sped.txt"),
        runner.InputFile("xml", tmp_path / "in" / "xml.zip", "xml.zip"),
    ]
    tracemalloc.start()
    inicio = time.monotonic()
    try:
        resultado = runner.run_tool(
            "sped_xml",
            company_doc=EMPRESA,
            competence="2026-09",
            rules=RuleSet(),
            inputs=inputs,
            workdir=tmp_path / "work",
            sink=sink,
        )
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    segundos = time.monotonic() - inicio

    assert resultado.counts["sped_documentos"] == DOCUMENTOS
    assert resultado.counts["com_xml"] == XMLS
    assert resultado.counts["so_sped"] == DOCUMENTOS - XMLS
    assert resultado.counts["divergentes"] == XMLS // 100
    assert resultado.counts["conferem"] == XMLS - XMLS // 100
    assert sink.achados == (DOCUMENTOS - XMLS) + XMLS // 100
    assert pico < ORCAMENTO_PICO_BYTES, f"pico de {pico / 1e6:.1f} MB"
    assert segundos < ORCAMENTO_SEGUNDOS, f"{segundos:.1f} s"
    # O preparo vive em disco: o arquivo temporário cresce, a memória do processo não.
    assert (tmp_path / "work" / "stage.sqlite3").stat().st_size > 5 * 1024 * 1024
