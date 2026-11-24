"""Recuperacao do esquema: conjunto de desenvolvimento e conjunto cego (A3).

- `test_blind_set_is_frozen` roda sempre: falha se `blind.yaml` mudar depois de congelado.
- Os testes `eval` usam o pack REAL do escritorio (`DOMINIO_MCP_EVAL_PACK` aponta outro arquivo) e
  reportam dev e cego **separados**. O cego conta UMA medicao por versao do overlay: registre cada
  uma em `reports/recall.md`; se falhar, o lote esta queimado e o ajuste usa so o desenvolvimento.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dominio_mcp.config import load_settings
from dominio_mcp.evaluation import EvalResult, evaluate, file_sha256, load_questions
from dominio_mcp.overlay import load_overlay
from dominio_mcp.pack import Pack, pack_store_for
from dominio_mcp.search import SchemaSearch

HERE = Path(__file__).parent
DEV_FLOOR_RECALL5 = 0.80  # piso contra regressao; o objetivo (A3) vale para o cego
BLIND_RECALL5 = 0.90
BLIND_RECALL1 = 0.70


FROZEN_SETS = ("blind", "blind2")
CURRENT_BLIND = "blind2.yaml"  # o v1 foi medido e falhou: queimado (reports/recall.md)


@pytest.mark.parametrize("name", FROZEN_SETS)
def test_blind_sets_are_frozen(name: str) -> None:
    frozen = (HERE / f"{name}.sha256").read_text(encoding="utf-8").strip()
    assert file_sha256(HERE / f"{name}.yaml") == frozen, (
        f"{name}.yaml mudou depois de congelado: o lote esta queimado; escreva um lote novo e "
        "independente e registre em reports/recall.md"
    )


def test_blind_set_is_big_enough_and_stratified() -> None:
    questions = load_questions(HERE / "blind.yaml")
    assert len(questions) >= 40
    modules = {q.module for q in questions}
    families = {q.family for q in questions}
    assert {"ef", "ct", "fo", "ge", "hr", "lr"} <= modules
    assert {
        "cadastro",
        "movimento",
        "apuracao",
        "parametro",
        "tabela_apoio",
        "obrigacao",
    } <= families


def test_blind_and_dev_sets_do_not_share_questions_or_tables() -> None:
    dev = load_questions(HERE / "dev.yaml")
    dev_texts = {q.text for q in dev}
    dev_tables = {t for q in dev for t in q.expected}
    for name in FROZEN_SETS:
        blind = load_questions(HERE / f"{name}.yaml")
        assert not dev_texts & {q.text for q in blind}
        # o v1 (queimado) repete a tabela ctconciliacao_bancaria do desenvolvimento; o v2 nao
        if name == "blind2":
            assert not dev_tables & {t for q in blind for t in q.expected}, name


def real_pack() -> Pack:
    override = os.environ.get("DOMINIO_MCP_EVAL_PACK")
    if override:
        return Pack(Path(override))
    pack = pack_store_for(load_settings()).open_current()
    if pack is None:
        pytest.skip("sem pack real: rode `python -m dominio_mcp.buildpack`")
    return pack


def run(name: str) -> tuple[EvalResult, Pack]:
    pack = real_pack()
    search = SchemaSearch(pack, load_overlay())
    known = {t.key for t in pack.tables()}
    result = evaluate(search, load_questions(HERE / name), known)
    print(
        f"\n[{name}] perguntas={result.total} top1={result.top1} ({result.recall1:.0%}) "
        f"top5={result.top5} ({result.recall5:.0%}) invalidas={result.invalid}"
    )
    print("  por modulo:", {m: f"{h}/{n}" for m, (h, n) in result.by_module.items()})
    print("  por familia:", {f: f"{h}/{n}" for f, (h, n) in result.by_family.items()})
    for question, got in result.failures:
        print("  falha:", question.encode("ascii", "replace").decode(), "->", got)
    return result, pack


@pytest.mark.eval
def test_dev_set_has_no_regression() -> None:
    result, _ = run("dev.yaml")
    assert result.invalid == 0
    assert result.recall5 >= DEV_FLOOR_RECALL5


@pytest.mark.eval
def test_blind_set_meets_the_a3_targets() -> None:
    if os.environ.get("DOMINIO_MCP_BLIND") != "1":
        pytest.skip("o cego conta uma medicao por versao do overlay: defina DOMINIO_MCP_BLIND=1")
    result, _ = run(CURRENT_BLIND)
    assert result.invalid == 0, "pergunta cega sem nenhuma tabela valida no pack"
    assert result.recall5 >= BLIND_RECALL5
    assert result.recall1 >= BLIND_RECALL1
