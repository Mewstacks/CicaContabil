"""Achados do revisor de seguranca automatico sobre o commit 0c9ab04f (22/11/2026).

1. agregado pessoal: doze LINHAS de uma pessoa so (competencias) nao sao tres contribuicoes;
2. largura desconhecida nao pode deixar texto longo ou documento sair como coluna normal;
3. CPF preenchido com zeros ate 14 posicoes fecha como CNPJ por acaso (cerca de 1,4% dos CPFs).
"""

from __future__ import annotations

import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.odbc import RawResult
from dominio_mcp.pack import Pack
from dominio_mcp.policy import PolicyClass, is_valid_cnpj, is_valid_cpf, mask_document
from dominio_mcp.shaping import ShapeContext, shape_result
from packs import build_demo_pack, col, table
from qhelp import POLICY, compile_, refused
from test_review_r1 import custom_pack


@pytest.fixture
def pack(tmp_path: Path) -> Pack:
    return build_demo_pack(tmp_path)


# --- 1. agregado pessoal conta pessoas, nao linhas --------------------------------------------

PAYROLL_SUM = {
    "tabela": "foempregados",
    "agrupar_por": ["codi_emp"],
    "agregacoes": [{"funcao": "sum", "coluna": "salario", "alias": "total"}],
}


def test_1_a_personal_sum_counts_distinct_people_when_the_table_has_a_person_key(
    pack: Pack,
) -> None:
    sql = compile_(pack, PAYROLL_SUM, allow_pii=frozenset({"folha"})).sql
    assert (
        'COUNT(DISTINCT CASE WHEN "t0"."salario" IS NOT NULL THEN "t0"."i_empregados" END)' in sql
    )


def test_1_twelve_rows_of_one_person_do_not_pass_as_a_group(pack: Pack) -> None:
    compiled = compile_(pack, PAYROLL_SUM, allow_pii=frozenset({"folha"}))
    # [empresa, soma, linhas do grupo, pessoas distintas]: 12 linhas, mas uma pessoa so
    rows: list[list[Any]] = [[1, 9000.0, 12, 1], [2, 500.0, 40, 4]]
    raw = RawResult((), rows, False, 1.0, datetime(2026, 11, 22, tzinfo=UTC))
    out = shape_result(compiled, raw, ShapeContext(pack_version="abc"))
    assert out["linhas"] == [[2, 500.0]]


def test_1_a_personal_measure_without_a_person_key_falls_back_to_non_null_rows(
    tmp_path: Path,
) -> None:
    ficha = table(
        "ficha",
        [col("codi_emp", "integer", 4), col("id", "integer", 4), col("data_nasc", "date", 4)],
        ("codi_emp", "id"),
        50,
    )
    custom = custom_pack(tmp_path, [ficha])
    nasc = custom.column("ficha", "data_nasc")
    assert nasc is not None and nasc.klass is PolicyClass.PESSOAL
    spec = {
        "tabela": "ficha",
        "agrupar_por": ["codi_emp"],
        "agregacoes": [{"funcao": "count", "coluna": "data_nasc", "alias": "n"}],
    }
    sql = compile_(custom, spec, allow_pii=frozenset({"nascimento"})).sql
    assert 'COUNT("t0"."data_nasc") AS "__k1"' in sql and "DISTINCT CASE" not in sql


# --- 2. largura desconhecida ------------------------------------------------------------------


@pytest.mark.parametrize("width", [None, 0])
def test_2_text_and_document_of_unknown_width_are_classified_on_the_safe_side(
    width: int | None,
) -> None:
    docs = table(
        "documentos",
        [
            col("codi_emp", "integer", 4),
            col("id_doc", "integer", 4),
            col("conteudo", "long varchar", width),
            col("cgce_cli", "varchar", width),
        ],
        ("codi_emp", "id_doc"),
        100,
    )
    classes = POLICY.classify_table(docs, frozenset(), lambda _t, _c: True)
    assert classes["conteudo"].klass is PolicyClass.TEXTO_LIVRE
    assert classes["cgce_cli"].klass is PolicyClass.DOCUMENTO
    assert classes["id_doc"].klass is PolicyClass.NORMAL


def test_2_a_known_small_width_still_classifies_by_width() -> None:
    small = table(
        "tabela_x",
        [col("codi_emp", "integer", 4), col("codigo", "varchar", 10), col("coisa", "varchar", 20)],
        ("codi_emp",),
        10,
    )
    classes = POLICY.classify_table(small, frozenset(), lambda _t, _c: True)
    assert classes["codigo"].klass is PolicyClass.NORMAL
    assert classes["coisa"].klass is PolicyClass.NORMAL


# --- 3. CPF com zeros a esquerda nao e CNPJ ----------------------------------------------------


def _cpf(base: str) -> str:
    def digit(numbers: str, start: int) -> str:
        total = sum(int(n) * w for n, w in zip(numbers, range(start, 1, -1), strict=True))
        rest = (total * 10) % 11
        return str(0 if rest == 10 else rest)

    first = digit(base, 10)
    return base + first + digit(base + first, 11)


def _cnpj_by_the_book(text: str) -> bool:
    """O algoritmo do CNPJ sem a regra nova: prova que o CPF preenchido fecha por acaso."""
    weights1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    weights2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)

    def digit(base: str, weights: tuple[int, ...]) -> int:
        rest = sum(int(c) * w for c, w in zip(base, weights, strict=True)) % 11
        return 0 if rest < 2 else 11 - rest

    first = digit(text[:12], weights1)
    return text[12:] == f"{first}{digit(text[:12] + str(first), weights2)}"


def _colliding_cpfs(count: int) -> list[str]:
    rng = random.Random(20261122)
    found: list[str] = []
    while len(found) < count:
        cpf = _cpf("".join(rng.choice("0123456789") for _ in range(9)))
        if len(set(cpf)) > 1 and _cnpj_by_the_book("000" + cpf):
            found.append(cpf)
    return found


COLLIDING = _colliding_cpfs(5)


def test_3_the_helper_finds_real_collisions() -> None:
    assert all(is_valid_cpf(c) and _cnpj_by_the_book("000" + c) for c in COLLIDING)


@pytest.mark.parametrize("cpf", COLLIDING)
def test_3_a_zero_padded_cpf_is_never_a_cnpj(cpf: str) -> None:
    assert is_valid_cnpj("000" + cpf) is False
    assert mask_document("000" + cpf, allow=False) == "***"
    numeric = str(mask_document(int(cpf), allow=False))
    assert "*" in numeric and cpf not in numeric


@pytest.mark.parametrize("cpf", COLLIDING)
def test_3_a_zero_padded_cpf_is_not_accepted_as_a_document_filter(pack: Pack, cpf: str) -> None:
    spec = {
        "tabela": "efsaidas",
        "colunas": ["codi_sai"],
        "filtros": [
            {"coluna": "codi_emp", "op": "=", "valor": 1},
            {"coluna": "cgce_cli", "op": "=", "valor": "000" + cpf},
        ],
    }
    assert refused(pack, spec).code == "documento_invalido"


def test_3_real_cnpjs_and_plain_cpfs_keep_their_treatment() -> None:
    assert is_valid_cnpj("11.222.333/0001-81") is True
    assert is_valid_cnpj("04252011000110") is True and is_valid_cnpj("11444777000161") is True
    # base 000 com cauda que tambem fecha como CPF (Banco do Brasil): ambiguo, sai mascarado
    assert is_valid_cnpj("00000000000191") is False
    assert mask_document("11222333000181", allow=False) == "11222333000181"
    assert mask_document("52998224725", allow=False) == "529.***.***-25"
    assert mask_document(11222333000181, allow=False) == "11222333000181"
    assert is_valid_cpf("529.982.247-25") is True and is_valid_cpf("52998224726") is False
    assert is_valid_cpf("11111111111") is False and is_valid_cpf("1234") is False
