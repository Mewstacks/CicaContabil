"""O motor de cálculo portado do Lucrums, conferido contra o contrato que veio com ele.

Por D-281 o cálculo atravessou sem alterar uma conta, e `contracts/calculations/v1.json`
é a prova: cada vetor foi escrito do outro lado e é lido aqui sem edição. Se uma
fórmula mudar, este teste falha antes de qualquer tela.

A auditoria de setembro de 2026 no projeto de origem removeu uma segunda conta de
custo horário que divergia 37% da que restou. Existe uma só, e o teste ao final
deste arquivo recusa a volta da antiga.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from apps.profitability import calc
from apps.profitability.normalize import (
    cnpj_ordem,
    cnpj_raiz,
    document_kind,
    only_digits,
    strip_accents_upper,
)

D = Decimal

CONTRACT = Path(__file__).resolve().parents[1] / "contracts" / "calculations" / "v1.json"
TOLERANCIA = D("0.0001")


def _contrato() -> dict[str, list[dict[str, object]]]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_contrato_de_calculo_esta_presente_e_versionado() -> None:
    """O contrato tem de vir junto com o código, ou o resto deste arquivo não prova nada."""

    fixture = _contrato()
    assert fixture["version"] == 1
    assert fixture["vectors"], "o contrato perdeu os vetores de margem"
    assert fixture["custoAnualVectors"], "o contrato perdeu os vetores de custo anual"


def test_resultado_margem_e_mensalidade_sugerida_seguem_o_contrato() -> None:
    for vector in _contrato()["vectors"]:
        mensalidade = D(str(vector["monthlyFee"]))
        custo = D(str(vector["cost"]))
        resultado = calc.resultado(mensalidade, custo)
        assert resultado == D(str(vector["expectedResult"]))
        assert calc.margem(resultado, mensalidade) == pytest.approx(
            D(str(vector["expectedMargin"])), rel=D("0.000000001")
        )
        assert calc.mensalidade_sugerida(custo, D(str(vector["targetMargin"]))) == D(
            str(vector["expectedSuggestedFee"])
        )


def test_custo_anual_segue_o_contrato_parcela_a_parcela() -> None:
    campos = {
        "salarios_anuais": "expectedSalariosAnuais",
        "terco_ferias": "expectedTercoFerias",
        "encargos_anuais": "expectedEncargosAnuais",
        "beneficios_anuais": "expectedBeneficiosAnuais",
        "vt_excedente_mensal": "expectedVtExcedenteMensal",
        "vt_empresa_anual": "expectedVtEmpresaAnual",
        "outros_custos_anuais": "expectedOutrosCustosAnuais",
        "custo_anual_total": "expectedCustoAnualTotal",
        "horas_anuais": "expectedHorasAnuais",
        "horas_produtivas": "expectedHorasProdutivas",
        "valor_hora": "expectedValorHora",
        "valor_hora_produtivo": "expectedValorHoraProdutivo",
    }
    for vector in _contrato()["custoAnualVectors"]:
        custo = calc.custo_anual_colaborador(
            D(str(vector["salario"])),
            beneficios_mensais=D(str(vector["beneficiosMensais"])),
            vt_mensal=D(str(vector["vtMensal"])),
            outros_custos_mensais=D(str(vector["outrosCustosMensais"])),
            dias_ferias=int(vector["diasFerias"]),
            folgas_dias=int(vector["folgasDias"]),
            ausencias_dias=int(vector["ausenciasDias"]),
            encargos_percentual=D(str(vector["encargosPercentual"])),
            dias_uteis_ano=int(vector["diasUteisAno"]),
            feriados_dias_ano=int(vector["feriadosDiasAno"]),
            horas_dia=D(str(vector["horasDia"])),
            indice_produtividade=D(str(vector["indiceProdutividade"])),
        )
        assert custo.dias_uteis == vector["expectedDiasUteis"], vector["name"]
        for atributo, esperado in campos.items():
            assert getattr(custo, atributo) == pytest.approx(
                D(str(vector[esperado])), abs=TOLERANCIA
            ), f"{vector['name']}.{atributo}"


def test_margem_e_zero_sem_mensalidade_para_nao_virar_prejuizo() -> None:
    """Empresa sem honorário é problema de dado, não de rentabilidade negativa."""

    assert calc.margem(D("5"), D("0")) == 0
    assert calc.margem(D("-5"), D("0")) == 0


def test_faixa_sem_horas_nao_e_margem() -> None:
    """Sem horas não há custo, e a margem leria 100% — a empresa lideraria a carteira."""

    assert calc.faixa_margem(D("0.2"), tem_horas=False) == "sem_dados"
    assert calc.faixa_margem(D("-0.1"), tem_horas=True) == "negativa"
    assert calc.faixa_margem(D("0"), tem_horas=True) == "atencao"
    assert calc.faixa_margem(D("0.1499"), tem_horas=True) == "atencao"
    assert calc.faixa_margem(D("0.15"), tem_horas=True) == "saudavel"


def test_margem_alvo_impossivel_devolve_o_proprio_custo() -> None:
    assert calc.mensalidade_sugerida(D("10"), D("1")) == 10
    assert calc.mensalidade_sugerida(D("10"), D("1.5")) == 10


def test_vale_transporte_so_conta_o_que_excede_seis_por_cento() -> None:
    assert calc.vt_excedente_mensal(D("300"), D("3000")) == 120
    assert calc.vt_excedente_mensal(D("180"), D("3000")) == 0
    assert calc.vt_excedente_mensal(D("100"), D("3000")) == 0
    assert calc.vt_excedente_mensal(D("0"), D("3000")) == 0


def test_dias_uteis_e_custo_hora_tem_piso_em_zero() -> None:
    assert calc.dias_uteis_efetivos(250, 10, 22, 0, 0) == 218
    assert calc.dias_uteis_efetivos(10, 10, 22, 5, 3) == 0
    assert calc.valor_hora(D("64690"), D("0")) == 0

    # Férias maiores que o ano útil: a conta zera em vez de estourar.
    custo = calc.custo_anual_colaborador(
        D("3000"),
        dias_ferias=250,
        encargos_percentual=D("0.35"),
        dias_uteis_ano=250,
        feriados_dias_ano=10,
        horas_dia=D("8"),
        indice_produtividade=D("0.8"),
    )
    assert custo.dias_uteis == 0
    assert custo.horas_anuais == 0
    assert custo.valor_hora == 0
    assert custo.valor_hora_produtivo == 0


def test_custo_de_minutos_usa_minuto_como_unidade_canonica() -> None:
    assert calc.custo_de_minutos(90, D("20")) == 30
    assert calc.custo_de_minutos(0, D("20")) == 0


def test_a_conta_antiga_de_custo_hora_nao_voltou() -> None:
    """Guarda contra a regressão que a auditoria de set/2026 removeu.

    A conta antiga era `salário x 1,40 / 176`. Para um salário de 3.000 ela dá
    23,86/h; a conta vigente, com os mesmos parâmetros, dá 37,09/h. São 37% de
    diferença sobre o custo de cada cliente, então o teste ancora o valor certo
    e recusa o errado, além de garantir que as constantes não voltaram ao módulo.
    """

    custo = calc.custo_anual_colaborador(
        D("3000"),
        beneficios_mensais=D("800"),
        vt_mensal=D("300"),
        encargos_percentual=D("0.35"),
        dias_uteis_ano=250,
        feriados_dias_ano=10,
        horas_dia=D("8"),
        indice_produtividade=D("0.8"),
    )
    conta_antiga = D("3000") * D("1.40") / D("176")
    assert custo.valor_hora == pytest.approx(D("37.0929"), abs=TOLERANCIA)
    assert custo.valor_hora != pytest.approx(conta_antiga, abs=D("1"))
    assert not hasattr(calc, "custo_hora_colaborador")


def test_normalizacao_espelha_o_sql_e_nada_alem() -> None:
    """Os 23 acentos que o SQL dobra, e só eles: NFKD dobraria Ñ e Ø e quebraria o par."""

    assert only_digits("12.345-6") == "123456"
    assert only_digits(" 12.345.678/0001-99 ") == "12345678000199"
    assert only_digits(None) == ""
    assert strip_accents_upper("  São  Tomé ") == "SAO  TOME"
    assert strip_accents_upper("Ação & Cia") == "ACAO & CIA"
    assert strip_accents_upper(None) == ""
    # Fora da tabela do SQL: tem de permanecer, ou os dois lados divergem.
    assert strip_accents_upper("Muñoz") == "MUÑOZ"


def test_classificacao_e_raiz_de_documento() -> None:
    assert document_kind("12345678901") == "cpf"
    assert document_kind("12345678000199") == "cnpj"
    assert document_kind("123") == ""
    assert document_kind("1234567800019X") == ""
    assert cnpj_raiz("12345678000199") == "12345678"
    assert cnpj_raiz("12345678901") == ""
    assert cnpj_ordem("12345678000199") == "0001"
    assert cnpj_ordem("12345678000299") == "0002"
    assert cnpj_ordem("12345678901") == ""
