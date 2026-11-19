from apps.hub.templatetags.nfse_format import source_brl, source_date


def test_source_date_formats_iso_and_keeps_anything_else():
    assert source_date("2026-09-04") == "04/09/2026"
    assert source_date("20260904") == "20260904"
    assert source_date(None) == ""


def test_source_brl_formats_plain_numbers_and_keeps_anything_else():
    assert source_brl("-912") == "-R$ 912,00"
    assert source_brl("1234.5") == "R$ 1.234,50"
    assert source_brl("abc") == "abc"
    assert source_brl("NaN") == "NaN"
