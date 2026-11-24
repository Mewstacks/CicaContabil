from __future__ import annotations

import pytest

from dominio_mcp.enums import is_unused, parse_legend


def pairs(comment: str) -> list[tuple[str, str]]:
    legend = parse_legend(comment)
    assert legend is not None, comment
    return [(e.code, e.label) for e in legend.entries]


def test_dash_style_with_slash_separator() -> None:
    comment = "Tipo da inscrição(1 - CNPJ/2 - CPF/3 - CEI/6 - CAEPF)"
    assert pairs(comment) == [("1", "CNPJ"), ("2", "CPF"), ("3", "CEI"), ("6", "CAEPF")]
    legend = parse_legend(comment)
    assert legend is not None
    assert legend.style == "traco"
    assert legend.confidence == "media"


def test_letter_codes_with_spaced_slash() -> None:
    assert pairs("Situacao (A - Ativa / I - Inativa)") == [("A", "Ativa"), ("I", "Inativa")]


def test_yes_no_pattern() -> None:
    assert pairs("Usa regime especial (1 - Sim/0 - Nao)") == [("1", "Sim"), ("0", "Nao")]


def test_equals_style_with_commas() -> None:
    legend = parse_legend("Tipo: 1=Normal, 2=Zerada, 3=Isenta")
    assert legend is not None
    assert legend.style == "igual"
    assert [(e.code, e.label) for e in legend.entries] == [
        ("1", "Normal"),
        ("2", "Zerada"),
        ("3", "Isenta"),
    ]


def test_range_style() -> None:
    legend = parse_legend("Faixa: 14-19=Honorarios, 20-29=Outros")
    assert legend is not None
    assert legend.style == "faixa"
    assert [(e.code, e.upper, e.label) for e in legend.entries] == [
        ("14", "19", "Honorarios"),
        ("20", "29", "Outros"),
    ]


def test_sn_flag_is_low_confidence() -> None:
    legend = parse_legend("Possui filial (S/N)")
    assert legend is not None
    assert legend.confidence == "baixa"
    assert [(e.code, e.label) for e in legend.entries] == [("S", "Sim"), ("N", "Nao")]


@pytest.mark.parametrize(
    "comment",
    [
        None,
        "",
        "   ",
        "Codigo da empresa",
        "Notas fiscais de saida - produtos",  # um unico par nao e legenda
        "Tipo (1 - CNPJ)",
        "Tipo (1 - /2 - )",  # codigos sem rotulo: nenhuma legenda
        "Regime pre-pago e pos-pago",
        "ISS - Servicos / IRPJ - Imposto de renda",  # codigos de 3+ letras nao sao legenda
    ],
)
def test_no_legend_when_there_is_nothing_reliable(comment: str | None) -> None:
    assert parse_legend(comment) is None


def test_entries_without_label_are_dropped_but_the_rest_survive() -> None:
    assert pairs("Tipo (1 - Normal/2 - /3 - Isenta)") == [("1", "Normal"), ("3", "Isenta")]


def test_duplicate_codes_keep_the_first() -> None:
    assert pairs("Tipo (1 - Normal/1 - Outro/2 - Zerada)") == [("1", "Normal"), ("2", "Zerada")]


def test_render_is_compact_and_bounded() -> None:
    legend = parse_legend("Tipo (1 - CNPJ/2 - CPF)")
    assert legend is not None
    assert legend.render() == "1=CNPJ; 2=CPF"
    big = "Codigo (" + "/".join(f"{i} - rotulo numero {i}" for i in range(1, 80)) + ")"
    parsed = parse_legend(big)
    assert parsed is not None
    assert len(parsed.entries) == 40
    assert all(len(e.label) <= 40 for e in parsed.entries)


def test_long_labels_are_cut() -> None:
    legend = parse_legend("Tipo (1 - " + "x" * 90 + "/2 - Curto)")
    assert legend is not None
    assert len(legend.entries[0].label) == 40


@pytest.mark.parametrize(
    "comment",
    [
        "Este campo nao e mais usado a partir da versao 6.1A-01 do Contabil",
        "Coluna não é mais utilizada, controle feito na outra tabela",
        "Campo nao utilizado",
        "(ESTA COLUNA NÃO É MAIS UTILIZADA)",
        "Tabela obsoleta",
        "campo em desuso",
    ],
)
def test_unused_markers_are_detected(comment: str) -> None:
    assert is_unused(comment) is True


@pytest.mark.parametrize("comment", [None, "", "Codigo da empresa", "Utilizado no calculo do ICMS"])
def test_ordinary_comments_are_not_marked_unused(comment: str | None) -> None:
    assert is_unused(comment) is False
