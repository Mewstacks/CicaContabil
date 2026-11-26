"""Closing engine: anchor-based extraction and layout matching (pure, no database).

Behaviour ported from HubFedrizzi ``apps/fechamento/services/mapeamento.py`` (own code).
"""

from __future__ import annotations

from decimal import Decimal

from apps.closing import engine
from apps.closing.engine import FieldSpec

DAS_TEXT = """
Documento de Arrecadação do Simples Nacional
CNPJ: 12.345.678/0001-95
Período de Apuração: 08/2026
Valor Total do Documento    1.234,56
"""


def field(variable: str, anchor: str, **extra: object) -> FieldSpec:
    return FieldSpec(variable=variable, anchor=anchor, **extra)  # type: ignore[arg-type]


def test_reads_each_typed_value_after_its_anchor() -> None:
    assert engine.extract(DAS_TEXT, field("cnpj", "CNPJ:")) == "12345678000195"
    assert engine.extract(DAS_TEXT, field("competence", "Período de Apuração")) == (2026, 8)
    assert engine.extract(DAS_TEXT, field("amount", "Valor Total do Documento")) == Decimal(
        "1234.56"
    )


def test_anchor_ignores_accents_case_and_line_breaks() -> None:
    text = "PERIODO   DE\nAPURACAO  agosto/2026"
    assert engine.extract(text, field("competence", "Período de Apuração")) == (2026, 8)


def test_a_missing_anchor_reads_nothing() -> None:
    assert engine.extract(DAS_TEXT, field("amount", "Valor do ICMS")) is None


def test_money_conventions_and_negative_values() -> None:
    assert engine.parse_money("1.234,56") == Decimal("1234.56")
    assert engine.parse_money("100.00") == Decimal("100.00")
    assert engine.parse_money("-1.234,56") == Decimal("-1234.56")
    assert engine.parse_money("(1.234,56)") == Decimal("-1234.56")


def test_nth_value_and_sum_for_block_layouts() -> None:
    text = "PIS COFINS Total\n10,00 20,00 30,00"
    assert engine.extract(text, field("amount", "PIS", occurrence=2)) == Decimal("20.00")
    assert engine.extract(text, field("amount", "PIS", sum_count=2)) == Decimal("30.00")


def test_a_nullified_field_reads_nothing_even_when_the_anchor_exists() -> None:
    spec = field("ipi", "Valor Total do Documento", nullified=True)
    assert engine.extract(DAS_TEXT, spec) is None


def test_state_and_municipal_registration_keep_leading_zeros() -> None:
    assert engine.extract("IE: 029/0618657", field("state_registration", "IE:")) == "0290618657"
    assert (
        engine.extract(
            "Inscrição Municipal 0012345", field("municipal_registration", "Inscrição Municipal")
        )
        == "0012345"
    )


def test_marker_variants_match_any_alternative() -> None:
    text = "GUIA DE ARRECADAÇÃO Código 222"
    assert engine.marker_hit(text, "Código 221 || Código 222") == "Código 222"
    assert engine.marker_hit(text, "Código 379") is None


def test_numeric_marker_does_not_match_inside_a_longer_number() -> None:
    assert engine.marker_hit("receita 116201", "1162") is None
    assert engine.marker_hit("receita 1162 ok", "1162") == "1162"


def test_layout_needs_every_marker_and_the_most_specific_wins() -> None:
    text = "RECIBO DE ENTREGA DE ESCRITURAÇÃO FISCAL DIGITAL - CONTRIBUIÇÕES"
    candidates = {
        "icms": ["RECIBO DE ENTREGA DE ESCRITURAÇÃO FISCAL DIGITAL"],
        "contrib": ["RECIBO DE ENTREGA DE ESCRITURAÇÃO FISCAL DIGITAL - CONTRIBUIÇÕES"],
        "other": ["RECIBO", "CODIGO INEXISTENTE"],
    }
    assert engine.winners(text, candidates) == ["contrib"]


def test_a_tie_between_layouts_is_returned_whole_so_the_caller_can_refuse() -> None:
    candidates = {"a": ["RECIBO"], "b": ["RECIBO"]}
    assert sorted(engine.winners("RECIBO", candidates)) == ["a", "b"]


def test_no_candidate_matches_empty_text() -> None:
    assert engine.winners("", {"a": ["RECIBO"]}) == []


def test_column_header_split_over_lines_reads_the_value_below_it() -> None:
    text = "Total do      Outro\nDébito        campo\nExigível\n1.500,00      9,99\n"
    assert engine.extract(text, field("amount", "Total do Débito Exigível")) == Decimal("1500.00")


def test_reads_the_taxpayer_root_from_a_fiscal_closing_xml() -> None:
    xml = (
        "<eSocial><evtFechaEvPer><ideEmpregador><tpInsc>1</tpInsc>"
        "<nrInsc>12345678</nrInsc></ideEmpregador></evtFechaEvPer></eSocial>"
    )
    assert engine.xml_taxpayer_root(xml) == "12345678"
    assert engine.xml_taxpayer_root("<root><nrInsc>99999999000191</nrInsc></root>") == ""


def test_pdf_reader_reports_a_broken_file_instead_of_raising() -> None:
    result = engine.read_text(b"not a pdf", "x.pdf")
    assert result.text == ""
    assert result.error_code in {"pdf_invalido", "pdf_sem_texto"}


def test_text_files_decode_latin1_without_replacement_characters() -> None:
    result = engine.read_text("PERÍODO 08/2026".encode("latin-1"), "x.txt")
    assert result.text == "PERÍODO 08/2026"
