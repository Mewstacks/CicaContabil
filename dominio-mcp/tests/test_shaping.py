from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.compiler import CompiledQuery
from dominio_mcp.odbc import RawResult
from dominio_mcp.pack import Pack
from dominio_mcp.shaping import MAX_CELL_CHARS, ShapeContext, shape_result
from packs import build_demo_pack
from qhelp import compile_

NOW = datetime(2026, 11, 21, 14, 30, 0, tzinfo=UTC)


@pytest.fixture
def pack(tmp_path: Path) -> Pack:
    return build_demo_pack(tmp_path)


def raw(rows: list[list[Any]], *, truncated: bool = False) -> RawResult:
    return RawResult((), rows, truncated, 12.0, NOW)


def shape(compiled: CompiledQuery, rows: list[list[Any]], **kw: Any) -> dict[str, Any]:
    truncated = kw.pop("truncated", False)
    ctx = ShapeContext(pack_version="abc123def456", elapsed_ms=12.4, **kw)
    return shape_result(compiled, raw(rows, truncated=truncated), ctx)


def test_envelope_has_consistency_label_time_and_source(pack: Pack) -> None:
    c = compile_(pack, {"tabela": "geempre", "colunas": ["codi_emp", "nome_emp"]})
    out = shape(c, [[1, "ACME"], [2, "BETA"]])
    assert out["colunas"] == ["codi_emp", "nome_emp"]
    assert out["linhas"] == [[1, "ACME"], [2, "BETA"]]
    assert out["quantidade"] == 2 and out["truncado"] is False
    assert out["consistencia"] == "leitura_nao_confirmada"
    assert out["lido_em"] == "2026-11-21T14:30:00+00:00"
    assert out["tabelas"] == ["geempre"] and out["pack"] == "abc123def456"
    assert out["consulta_ms"] == 12
    assert "avisos" not in out and "texto_livre" not in out and "proximo_passo" not in out


def test_probe_row_is_dropped_and_truncation_is_reported(pack: Pack) -> None:
    c = compile_(pack, {"tabela": "geempre", "colunas": ["codi_emp"], "limite": 2})
    out = shape(c, [[1], [2], [3]], truncated=True)
    assert out["linhas"] == [[1], [2]] and out["truncado"] is True
    assert "deslocamento" in out["proximo_passo"]


def test_document_pessoal_and_free_text_are_masked_by_class(pack: Pack) -> None:
    c = compile_(
        pack,
        {"tabela": "efsaidas", "colunas": ["codi_sai", "cgce_cli", "obs_sai"]},
    )
    rows = [
        [1, "11.222.333/0001-81", "entregar ao Joao, cpf 529.982.247-25 ou joao@exemplo.com"],
        [2, "529.982.247-25", None],
        [3, "texto qualquer", "fone (11) 91234-5678"],
        [4, None, "x" * 500],
    ]
    out = shape(c, rows)
    assert out["linhas"][0] == [
        1,
        "11.222.333/0001-81",
        "entregar ao Joao, cpf [cpf] ou [email]",
    ]
    assert out["linhas"][1] == [2, "529.***.***-25", None]
    assert out["linhas"][2] == [3, "***", "fone [telefone]"]
    assert out["linhas"][3][1] is None
    assert len(out["linhas"][3][2]) == MAX_CELL_CHARS and out["linhas"][3][2].endswith("…")
    assert out["texto_livre"] == ["obs_sai"]
    flat = json.dumps(out, ensure_ascii=False)
    for secret in ("529.982.247-25", "joao@exemplo.com", "91234-5678"):
        assert secret not in flat


def test_released_personal_columns_are_masked_and_released_documents_are_not(pack: Pack) -> None:
    c = compile_(
        pack,
        {"tabela": "geempre", "colunas": ["codi_emp", "ende_emp", "cgce_emp"]},
        allow_pii=frozenset({"endereco", "documento"}),
    )
    out = shape(c, [[1, "Rua das Flores, 10", "529.982.247-25"]])
    assert out["linhas"] == [[1, "***", "529.982.247-25"]]


def test_small_groups_of_personal_data_are_suppressed_and_the_helper_column_hidden(
    pack: Pack,
) -> None:
    c = compile_(
        pack,
        {
            "tabela": "foempregados",
            "agrupar_por": ["codi_emp"],
            "agregacoes": [{"funcao": "avg", "coluna": "salario", "alias": "media"}],
        },
        allow_pii=frozenset({"folha"}),
    )
    assert c.count_index == 2 and c.contrib_indexes == (3,)
    out = shape(c, [[1, 3500.5, 10, 10], [2, 9000.0, 2, 2], [3, 1200.0, 3, 3]])
    assert out["colunas"] == ["codi_emp", "media"]
    assert out["linhas"] == [[1, 3500.5], [3, 1200.0]]
    assert any("1 grupo(s) com menos de 3" in w for w in out["avisos"])
    assert "__k" not in json.dumps(out)


def test_implausible_dates_get_a_warning_without_the_value(pack: Pack) -> None:
    c = compile_(pack, {"tabela": "geempre", "colunas": ["codi_emp", "dina_emp"]})
    out = shape(c, [[1, "2024-01-01"], [2, "1979-03-04"], [3, "8320-01-01"]])
    assert out["avisos"] == ["a coluna dina_emp tem data fora de 1980-2100: confira o dado"]
    assert "1979" not in out["avisos"][0]
    clean = shape(c, [[1, "2024-01-01"], [2, None]])
    assert "avisos" not in clean


def test_response_is_cut_at_the_byte_cap_keeping_whole_rows(pack: Pack) -> None:
    c = compile_(pack, {"tabela": "efsaidas", "colunas": ["codi_sai", "obs_sai"], "limite": 500})
    rows = [[i, f"observacao numero {i} " + "x" * 150] for i in range(500)]
    out = shape(c, rows)
    size = len(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    assert size <= 12 * 1024
    assert out["truncado"] is True and 0 < out["quantidade"] < 500
    assert out["linhas"][-1][0] == out["quantidade"] - 1
    assert "12 KB" in out["proximo_passo"]


def test_custom_byte_cap_and_empty_result(pack: Pack) -> None:
    c = compile_(pack, {"tabela": "geempre", "colunas": ["codi_emp"]})
    assert shape(c, [])["linhas"] == []
    tiny = shape(c, [[i] for i in range(50)], max_bytes=400)
    assert tiny["truncado"] is True and tiny["quantidade"] < 50


def test_property_every_shape_stays_under_the_cap(pack: Pack) -> None:
    c = compile_(
        pack,
        {"tabela": "efsaidas", "colunas": ["codi_sai", "cgce_cli", "obs_sai"], "limite": 500},
    )
    for n in (0, 1, 7, 99, 500):
        rows = [[i, "11.222.333/0001-81", "y" * (i % 300)] for i in range(n)]
        out = shape(c, rows)
        assert len(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode()) <= 12288
