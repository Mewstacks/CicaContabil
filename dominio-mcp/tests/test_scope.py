from __future__ import annotations

from pathlib import Path

import pytest

from dominio_mcp.pack import Pack
from packs import build_demo_pack
from qhelp import compile_, refused

COMPANY = {"coluna": "codi_emp", "op": "=", "valor": 560}
YEAR = {"coluna": "dsai_sai", "op": "between", "valor": ["2025-01-01", "2025-12-31"]}


@pytest.fixture
def pack(tmp_path: Path) -> Pack:
    return build_demo_pack(tmp_path)


def spec(*filters: dict[str, object], table: str = "efsaidas", column: str = "codi_sai") -> dict:  # type: ignore[type-arg]
    return {"tabela": table, "colunas": [column], "filtros": list(filters)}


def test_small_tables_are_never_scoped(pack: Pack) -> None:
    assert compile_(pack, {"tabela": "geempre", "colunas": ["codi_emp"]}, scope=True)
    assert compile_(pack, {"tabela": "efclientes", "colunas": ["codi_cli"]}, scope=True)


def test_big_table_needs_the_company_filter(pack: Pack) -> None:
    err = refused(pack, spec(YEAR), scope=True)
    assert err.code == "sem_filtro_de_empresa" and err.details["tabela"] == "efsaidas"
    assert refused(pack, spec(), scope=True).code == "sem_filtro_de_empresa"
    wrong = {"coluna": "codi_emp", "op": ">", "valor": 1}
    assert refused(pack, spec(wrong, YEAR), scope=True).code == "sem_filtro_de_empresa"


def test_big_table_needs_a_closed_window_of_at_most_13_months(pack: Pack) -> None:
    assert refused(pack, spec(COMPANY), scope=True).code == "sem_janela_de_datas"
    assert compile_(pack, spec(COMPANY, YEAR), scope=True)
    long_window = {"coluna": "dsai_sai", "op": "between", "valor": ["2024-01-01", "2025-12-31"]}
    assert refused(pack, spec(COMPANY, long_window), scope=True).code == "janela_de_datas_longa"
    only_lower = {"coluna": "dsai_sai", "op": ">=", "valor": "2025-01-01"}
    assert refused(pack, spec(COMPANY, only_lower), scope=True).code == "sem_janela_de_datas"


def test_window_by_two_bounds_and_by_the_edge_of_13_months(pack: Pack) -> None:
    low = {"coluna": "dsai_sai", "op": ">=", "valor": "2025-01-01"}
    high = {"coluna": "dsai_sai", "op": "<=", "valor": "2025-12-31"}
    assert compile_(pack, spec(COMPANY, low, high), scope=True)
    edge = {"coluna": "dsai_sai", "op": "between", "valor": ["2025-01-01", "2026-01-31"]}
    assert compile_(pack, spec(COMPANY, edge), scope=True)
    over = {"coluna": "dsai_sai", "op": "between", "valor": ["2025-01-01", "2026-03-01"]}
    assert refused(pack, spec(COMPANY, over), scope=True).code == "janela_de_datas_longa"
    one_day = {"coluna": "dsai_sai", "op": "=", "valor": "2025-06-30"}
    assert compile_(pack, spec(COMPANY, one_day), scope=True)


def test_company_in_list_is_accepted(pack: Pack) -> None:
    several = {"coluna": "codi_emp", "op": "in", "valor": [560, 561]}
    assert compile_(pack, spec(several, YEAR), scope=True)


def test_company_filter_on_the_parent_covers_the_child_through_the_fk_join(pack: Pack) -> None:
    child = {
        "tabela": "efmvspro",
        "juntar": [{"tabela": "efsaidas"}],
        "colunas": ["nume_mvs"],
        "filtros": [
            {"coluna": "efsaidas.codi_emp", "op": "=", "valor": 560},
            {"coluna": "efsaidas.dsai_sai", "op": "between", "valor": ["2025-01-01", "2025-03-31"]},
        ],
    }
    assert compile_(pack, child, scope=True)
    no_company = {**child, "filtros": child["filtros"][1:]}  # type: ignore[index]
    assert refused(pack, no_company, scope=True).code == "sem_filtro_de_empresa"


def test_date_window_may_come_from_the_joined_parent_table(pack: Pack) -> None:
    only_child = {
        "tabela": "efmvspro",
        "colunas": ["nume_mvs"],
        "filtros": [COMPANY],
    }
    assert refused(pack, only_child, scope=True).code == "sem_janela_de_datas"
