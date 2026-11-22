"""Varredura de privacidade no catalogo REAL (A7b e preparo de A7c). Le so o pack local.

Rodar:  uv run --directory dominio-mcp pytest -q -m live tests/live/test_live_privacy_sweep.py -s
Com DOMINIO_MCP_WRITE_REPORT=1 regrava `reports/privacidade.md` (so contagens, nenhum nome de
coluna de segredo, nenhum comentario) e exporta a amostra de 300 colunas para a revisao
independente em `<pasta de dados>/review/amostra-300.csv`, **fora do git** (traz comentario do
dicionario da Thomson Reuters).
"""

from __future__ import annotations

import csv
import os
import random
from collections import Counter
from pathlib import Path

import pytest

from dominio_mcp.config import load_settings
from dominio_mcp.pack import Pack, pack_store_for
from dominio_mcp.policy import ColumnPolicy, PolicyClass, load_policy

pytestmark = pytest.mark.live

REPORT = Path(__file__).parents[2] / "reports" / "privacidade.md"
SAMPLE_QUOTA = {
    PolicyClass.SEGREDO: 40,
    PolicyClass.DOCUMENTO: 40,
    PolicyClass.PESSOAL: 80,
    PolicyClass.TEXTO_LIVRE: 60,
    PolicyClass.NAO_CLASSIFICADA: 80,
}


@pytest.fixture(scope="module")
def pack() -> Pack:
    found = pack_store_for(load_settings()).open_current()
    if found is None:
        pytest.skip("sem pack real: rode `dominio-mcp build-pack`")
    return found


def counts(pack: Pack) -> dict[str, object]:
    tables = pack.query("SELECT key, kind, blocked_reason, queryable, readable FROM tables")
    classes = Counter(r[0] for r in pack.query("SELECT klass FROM columns"))
    rules = Counter(r[0] for r in pack.query("SELECT rule FROM columns"))
    categories = Counter(
        r[0] for r in pack.query("SELECT category FROM columns WHERE category IS NOT NULL")
    )
    blocked = Counter(
        r[0]
        for r in pack.query("SELECT blocked_reason FROM columns WHERE blocked_reason IS NOT NULL")
    )
    table_reasons = Counter((t[2] or "").split(":")[0] or "livre" for t in tables)
    return {
        "tabelas": len(tables),
        "tabelas_por_motivo": dict(table_reasons),
        "consultaveis": sum(1 for t in tables if t[3]),
        "views": sum(1 for t in tables if t[1] != "BASE"),
        "colunas": sum(classes.values()),
        "por_classe": dict(classes),
        "por_regra": dict(rules),
        "pessoal_por_categoria": dict(categories),
        "bloqueios_de_coluna": dict(blocked),
    }


def test_every_object_is_accepted_with_allowed_columns_or_refused_with_a_reason(pack: Pack) -> None:
    policy = load_policy()
    for table in pack.tables():
        assert table.queryable == (table.blocked_reason is None), table.key
        columns = pack.columns(table.key)
        assert columns, table.key
        if table.blocked_reason == "tabela_de_credencial":
            assert table.comment is None
            assert all(c.klass is PolicyClass.SEGREDO for c in columns)
        for column in columns:
            access = policy.access(
                ColumnPolicy(column.klass, column.category, column.rule, column.blocked_reason),
                frozenset(),
            )
            if column.klass is PolicyClass.SEGREDO:
                assert column.comment is None and not access.select
            if column.klass is PolicyClass.PESSOAL:
                assert not access.select, "pessoal so abre com allow_pii"
            if column.klass is PolicyClass.NAO_CLASSIFICADA:
                assert not access.select and access.reason
    summary = counts(pack)
    assert summary["colunas"] == sum(summary["por_classe"].values())  # type: ignore[arg-type]


def test_report_and_review_sample(pack: Pack, capsys: pytest.CaptureFixture[str]) -> None:
    summary = counts(pack)
    with capsys.disabled():
        print("\n", {k: v for k, v in summary.items() if k != "por_regra"})
    if os.environ.get("DOMINIO_MCP_WRITE_REPORT") != "1":
        return
    settings = load_settings()
    review = settings.home / "review"
    review.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261121)
    rows: list[list[object]] = []
    by_class: dict[PolicyClass, list[tuple[str, str, str, str, str]]] = {
        c: [] for c in SAMPLE_QUOTA
    }
    for table in pack.tables():
        for c in pack.columns(table.key):
            if c.klass in by_class:
                by_class[c.klass].append(
                    (table.name, c.name, c.type, str(c.width or ""), c.comment or "")
                )
    for klass, quota in SAMPLE_QUOTA.items():
        pool = sorted(by_class[klass])
        for item in rng.sample(pool, min(quota, len(pool))):
            rows.append([*item, klass.value, "", ""])
    rng.shuffle(rows)
    with (review / "amostra-300.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "tabela",
                "coluna",
                "tipo",
                "largura",
                "comentario",
                "classe_do_programa",
                "revisor_1",
                "revisor_2",
            ]
        )
        writer.writerows(rows)
    lines = [
        "# Privacidade no catalogo real (A7b)",
        "",
        "Gerado de `%LOCALAPPDATA%\\dominio-mcp\\packs` (so contagens; nenhum nome de coluna de "
        "segredo, nenhum comentario).",
        "",
        f"- Objetos: {summary['tabelas']} ({summary['views']} views); consultaveis agora: "
        f"{summary['consultaveis']}.",
        f"- Objetos por motivo: {summary['tabelas_por_motivo']}.",
        f"- Colunas: {summary['colunas']}; por classe: {summary['por_classe']}.",
        f"- Pessoal por categoria: {summary['pessoal_por_categoria']}.",
        f"- Bloqueios de coluna: {summary['bloqueios_de_coluna']}.",
        "",
        f"A amostra de {len(rows)} colunas para a revisao independente (A7c) foi exportada fora do "
        "git. Rotulagem pelos dois revisores e falso-negativo por classe: **pendentes**.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
