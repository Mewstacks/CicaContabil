"""A7a (parte da politica): marcadores plantados no catalogo sintetico nao podem sair.

A prova completa sobre todas as saidas (ferramentas, erro, recurso e auditoria) roda em
`test_markers_e2e.py`, depois das ferramentas. Aqui vale a classificacao e a regra de que
comentario de coluna ou tabela bloqueada nem entra no que o pack guarda.
"""

from __future__ import annotations

import json
from pathlib import Path

from dominio_mcp.catalog import Catalog, build_catalog
from dominio_mcp.policy import ColumnPolicy, PolicyClass, load_policy

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_catalog.json"
NEW_COLUMNS = {("efnovas", "coluna_nova")}


def synthetic() -> Catalog:
    return build_catalog(json.loads(FIXTURE.read_text(encoding="utf-8")))


def classify() -> dict[tuple[str, str], ColumnPolicy]:
    policy = load_policy()
    return policy.classify_catalog(synthetic(), lambda t, c: (t, c) not in NEW_COLUMNS)


def test_planted_secret_columns_and_tables_are_blocked() -> None:
    result = classify()
    assert result[("geempre", "senha_modulo_web")].klass is PolicyClass.SEGREDO
    for column in ("codi_emp", "nome", "conteudo"):
        assert result[("gecertificadosdigitais", column)].klass is PolicyClass.SEGREDO


def test_audit_text_is_blocked_with_a_reason() -> None:
    cp = classify()[("audados", "valor")]
    assert cp.klass is PolicyClass.TEXTO_LIVRE
    assert cp.blocked_reason == "auditoria_log"


def test_free_text_stays_readable_but_masked() -> None:
    policy = load_policy()
    cp = classify()[("efobservacoes", "observacao")]
    assert cp.klass is PolicyClass.TEXTO_LIVRE and cp.blocked_reason is None
    assert policy.access(cp, frozenset()).mask == "texto"


def test_new_column_is_unclassified_and_blocked_until_accepted() -> None:
    policy = load_policy()
    cp = classify()[("efnovas", "coluna_nova")]
    assert cp.klass is PolicyClass.NAO_CLASSIFICADA
    access = policy.access(cp, frozenset({"cpf", "documento", "folha"}))
    assert not access.select and access.reason == "nao_classificada"


def test_view_columns_stay_blocked_until_the_view_is_approved() -> None:
    """A view que encapsula `audados.valor` nao herda classe nenhuma: so entra aprovada (T2.8)."""
    cat = synthetic()
    assert cat.tables["vw_dados"].kind == "VIEW"
    assert "audados" in (cat.tables["vw_dados"].view_definition or "")
    policy = load_policy()
    result = policy.classify_catalog(cat, lambda t, c: True)
    for column in ("codi_emp", "conteudo"):
        cp = result[("vw_dados", column)]
        assert cp.klass is PolicyClass.NAO_CLASSIFICADA
        assert cp.blocked_reason == "view_nao_aprovada"
        assert not policy.access(cp, frozenset({"cpf", "documento"})).select
    approved = policy.classify_catalog(cat, lambda t, c: True, lambda tbl: tbl.key == "vw_dados")
    assert approved[("vw_dados", "conteudo")].klass is PolicyClass.TEXTO_LIVRE
