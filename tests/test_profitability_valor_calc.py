"""Valor gerado por colaborador: a conta pura, sem banco."""

from __future__ import annotations

from decimal import Decimal

from apps.profitability.calc import (
    EmpresaAtendida,
    pesos_dos_departamentos,
    valor_por_colaborador,
)

D = Decimal
CAP = {"fiscal": D(300), "contabil": D(300), "folha": D(300), "societario": D(100)}


def test_pesos_seguem_a_capacidade_e_somam_um() -> None:
    pesos = pesos_dos_departamentos(CAP)
    assert pesos["fiscal"] == D(3) / D(10)
    assert pesos["societario"] == D(1) / D(10)
    assert sum(pesos.values()) == D(1)


def test_departamento_sem_capacidade_fica_fora_do_peso() -> None:
    assert pesos_dos_departamentos({"fiscal": D(100), "folha": D(0)}) == {"fiscal": D(1)}
    assert pesos_dos_departamentos({}) == {}


def test_empresa_que_usa_todos_os_departamentos() -> None:
    empresa = EmpresaAtendida(
        "A",
        D(1000),
        {
            "fiscal": ("ana",),
            "contabil": ("bia",),
            "folha": ("caio",),
            "societario": ("dani",),
        },
    )
    r = valor_por_colaborador(CAP, [empresa])
    assert r.por_colaborador == {"ana": D(300), "bia": D(300), "caio": D(300), "dani": D(100)}
    assert r.sem_responsavel == {}


def test_departamento_nao_usado_renormaliza_os_demais() -> None:
    # Sem folha nem societário: fiscal e contábil dividem 50/50.
    empresa = EmpresaAtendida("A", D(1000), {"fiscal": ("ana",), "contabil": ("bia",)})
    r = valor_por_colaborador(CAP, [empresa])
    assert r.por_colaborador == {"ana": D(500), "bia": D(500)}


def test_duas_pessoas_no_mesmo_departamento_dividem_igual() -> None:
    empresa = EmpresaAtendida("A", D(600), {"fiscal": ("ana", "bia")})
    r = valor_por_colaborador(CAP, [empresa])
    assert r.por_colaborador == {"ana": D(300), "bia": D(300)}
    assert r.por_colaborador_empresa[("ana", "A")] == D(300)


def test_mesma_pessoa_repetida_no_departamento_conta_uma_vez() -> None:
    empresa = EmpresaAtendida("A", D(600), {"fiscal": ("ana", "ana")})
    assert valor_por_colaborador(CAP, [empresa]).por_colaborador == {"ana": D(600)}


def test_empresa_sem_responsavel_nao_some() -> None:
    empresa = EmpresaAtendida("A", D(800), {"fiscal": ()})
    r = valor_por_colaborador(CAP, [empresa])
    assert r.por_colaborador == {}
    assert r.sem_responsavel == {"A": D(800)}


def test_departamento_atribuido_sem_capacidade_nao_recebe() -> None:
    empresa = EmpresaAtendida("A", D(100), {"outros": ("eli",), "fiscal": ("ana",)})
    r = valor_por_colaborador(CAP, [empresa])
    assert r.por_colaborador == {"ana": D(100)}


def test_conservacao_a_soma_fecha_com_a_receita() -> None:
    empresas = [
        EmpresaAtendida("A", D("1234.56"), {"fiscal": ("ana",), "contabil": ("bia", "caio")}),
        EmpresaAtendida("B", D("777.77"), {"folha": ("caio",), "societario": ("dani",)}),
        EmpresaAtendida("C", D("500.00"), {}),
        EmpresaAtendida("D", D("0"), {"fiscal": ("ana",)}),
    ]
    r = valor_por_colaborador(CAP, empresas)
    atribuido = sum(r.por_colaborador.values(), D(0)) + sum(r.sem_responsavel.values(), D(0))
    receita = sum((e.mensalidade for e in empresas), D(0))
    assert abs(atribuido - receita) < D("0.0000001")
