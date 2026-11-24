"""Dinheiro em centavos e chave de acesso do Contraprova (motor puro, sem banco)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.crosscheck.engine import keys, money


class TestDinheiro:
    @pytest.mark.parametrize(
        ("texto", "centavos"),
        [("1234,56", 123456), ("0,5", 50), ("0", 0), ("-10,25", -1025), ("100,005", 10001)],
    )
    def test_sped_usa_virgula_e_arredonda_meio_para_cima(self, texto: str, centavos: int) -> None:
        assert money.sped_cents(texto) == centavos

    @pytest.mark.parametrize(("texto", "centavos"), [("1234.56", 123456), ("0.005", 1), ("7", 700)])
    def test_xml_usa_ponto(self, texto: str, centavos: int) -> None:
        assert money.xml_cents(texto) == centavos

    def test_campo_vazio_nao_e_zero(self) -> None:
        """Vazio é 'não informado'; tratar como zero esconderia a diferença."""

        assert money.sped_cents("") is None
        assert money.sped_cents("   ") is None
        assert money.xml_cents(None) is None
        assert money.xml_cents("") is None

    @pytest.mark.parametrize("texto", ["1.234,56", "12,3,4", "abc", "1e5", "--1", "1,", ",5"])
    def test_sped_recusa_formato_fora_do_leiaute(self, texto: str) -> None:
        with pytest.raises(money.MoneyError):
            money.sped_cents(texto)

    @pytest.mark.parametrize("texto", ["1,5", "1.2.3", "NaN", "Infinity", "0x10"])
    def test_xml_recusa_formato_fora_do_leiaute(self, texto: str) -> None:
        with pytest.raises(money.MoneyError):
            money.xml_cents(texto)

    def test_o_caso_que_o_float_do_legado_errava(self) -> None:
        """100,03 x 100,02 e 10,02 x 10,01 têm a mesma diferença: 1 centavo."""

        assert (money.sped_cents("100,03") or 0) - (money.sped_cents("100,02") or 0) == 1
        assert (money.sped_cents("10,02") or 0) - (money.sped_cents("10,01") or 0) == 1
        assert 100.03 - 100.02 > 0.01  # o que acusava no legado
        assert 10.02 - 10.01 < 0.01  # o que passava no legado

    def test_soma_de_centavos_e_exata(self) -> None:
        assert sum(money.sped_cents("0,10") or 0 for _ in range(200)) == 2000

    def test_aliquota_tem_quatro_casas(self) -> None:
        assert money.sped_rate("18,00") == 180000
        assert money.xml_rate("17.5000") == 175000
        assert money.to_rate(Decimal("12.34567")) == 123457

    @pytest.mark.parametrize(
        ("centavos", "maquina", "exibicao"),
        [
            (123456, "1234.56", "1.234,56"),
            (5, "0.05", "0,05"),
            (-100050, "-1000.50", "-1.000,50"),
            (0, "0.00", "0,00"),
            (100000000, "1000000.00", "1.000.000,00"),
        ],
    )
    def test_formatos_de_saida(self, centavos: int, maquina: str, exibicao: str) -> None:
        assert money.plain(centavos) == maquina
        assert money.brl(centavos) == exibicao

    def test_vazio_formata_vazio(self) -> None:
        assert money.plain(None) == ""
        assert money.brl(None) == ""
        assert money.rate_text(None) == ""

    @pytest.mark.parametrize(
        ("taxa", "texto"),
        [(180000, "18,00"), (175000, "17,50"), (1200, "0,12"), (123456, "12,3456")],
    )
    def test_aliquota_para_texto(self, taxa: int, texto: str) -> None:
        assert money.rate_text(taxa) == texto


class TestChave:
    def test_dv_modulo_11_pesos_2_a_9(self) -> None:
        # Exemplo do Manual de Orientação do Contribuinte: DV calculado sobre 43 posições.
        base = "3526081234567800019555001000001234112345678"
        assert len(base) == 43
        dv = keys.check_digit(base)
        assert keys.with_check_digit(base) == base + str(dv)
        assert keys.is_valid_key(base + str(dv))
        assert not keys.is_valid_key(base + str((dv + 1) % 10))

    def test_resto_zero_ou_um_vira_dv_zero(self) -> None:
        # Procura bases cujo resto cai em 0 e 1 e confirma o DV 0.
        encontrados = set()
        for numero in range(1, 4000):
            base = f"3526081234567800019555001{numero:09d}112345678"
            soma = 0
            peso = 2
            for caractere in reversed(base):
                soma += int(caractere) * peso
                peso = 2 if peso == 9 else peso + 1
            resto = soma % 11
            if resto in (0, 1):
                encontrados.add(resto)
                assert keys.check_digit(base) == 0
        assert encontrados == {0, 1}

    def test_aceita_letras_nas_doze_primeiras_posicoes_do_cnpj(self) -> None:
        """NT Conjunta 2025.001: letra vale ASCII - 48 (A = 17)."""

        base = (
            "3526"
            + "08"
            + "12ABC345000195"[:12]
            + "95"
            + "55"
            + "001"
            + "000001234"
            + "1"
            + "12345678"
        )
        assert len(base) == 43
        chave = keys.with_check_digit(base)
        assert keys.is_valid_key(chave)
        manual = sum(
            (ord(c) - 48) * w
            for c, w in zip(reversed(base), [2, 3, 4, 5, 6, 7, 8, 9] * 6, strict=False)
        )
        resto = manual % 11
        assert int(chave[-1]) == (0 if resto in (0, 1) else 11 - resto)

    def test_letras_fora_do_cnpj_sao_recusadas(self) -> None:
        assert not keys.is_well_formed("A" + "5" * 43)
        assert not keys.is_well_formed("35260812345678000195550010000012341123456A85")
        assert not keys.is_well_formed("35260812345678000195550010000012341123456")
        assert not keys.is_well_formed("")
        assert not keys.is_well_formed("3526081234567800019555001000001234112345678 5")

    def test_decompoe_a_chave(self) -> None:
        base = "3526081234567800019555001000001234112345678"
        chave = keys.with_check_digit(base)
        partes = keys.split_key(chave)
        assert partes.uf_code == "35"
        assert partes.aamm == "2608"
        assert partes.cnpj == "12345678000195"
        assert partes.model == "55"
        assert partes.series == "001"
        assert partes.number == "000001234"
        assert partes.emission_type == "1"
        assert partes.numeric_code == "12345678"
        assert partes.check_digit == chave[-1]

    def test_decompor_chave_invalida_levanta(self) -> None:
        with pytest.raises(ValueError, match="44"):
            keys.split_key("123")
