"""Leitura de ZIP de XMLs do Contraprova: sem extrair em disco e contra bomba."""

from __future__ import annotations

import io

import pytest

from apps.crosscheck.engine.zipreader import (
    ZipLimits,
    ZipRejected,
    display_name,
    iter_zip_items,
    summarize_zip,
)
from apps.crosscheck.synthetic import build_zip


def itens(dados: bytes, limites: ZipLimits | None = None) -> list[tuple[str, bool, str]]:
    return [
        (item.name, item.data is not None, item.problem)
        for item in iter_zip_items(io.BytesIO(dados), limites)
    ]


class TestLeitura:
    def test_le_xml_e_marca_o_que_nao_e_xml(self) -> None:
        dados = build_zip({"a.xml": b"<a/>", "sub/b.XML": b"<b/>", "leia-me.txt": b"oi"})

        assert itens(dados) == [
            ("a.xml", True, ""),
            ("b.XML", True, ""),
            ("leia-me.txt", False, "nao_xml"),
        ]

    def test_ruido_de_sistema_e_diretorios_sao_pulados(self) -> None:
        dados = build_zip(
            {"__MACOSX/._a.xml": b"x", "pasta/": b"", "pasta/._b.xml": b"x", ".DS_Store": b"x"}
        )

        assert itens(dados) == []

    def test_nome_exibido_nunca_traz_caminho(self) -> None:
        assert display_name("../../evil.xml") == "evil.xml"
        assert display_name("C:\\pasta\\nota.xml") == "nota.xml"
        assert display_name("nota.xml") == "nota.xml"

    def test_resumo_usa_so_o_diretorio_central(self) -> None:
        dados = build_zip({"a.xml": b"<a/>" * 10, "b.xml": b"<b/>", "c.pdf": b"%PDF"})

        resumo = summarize_zip(io.BytesIO(dados))

        assert (resumo.entries, resumo.xml_entries) == (3, 2)
        assert resumo.uncompressed_bytes == 40 + 4 + 4


class TestDefesas:
    def test_arquivo_que_nao_e_zip(self) -> None:
        with pytest.raises(ZipRejected) as erro:
            list(iter_zip_items(io.BytesIO(b"isto nao e zip")))

        assert erro.value.code == "nao_zip"

    def test_entradas_demais(self) -> None:
        dados = build_zip({f"{i}.xml": b"<a/>" for i in range(6)})

        with pytest.raises(ZipRejected) as erro:
            list(iter_zip_items(io.BytesIO(dados), ZipLimits(max_entries=5)))

        assert erro.value.code == "entradas_demais"

    def test_tamanho_total_acima_do_teto(self) -> None:
        dados = build_zip({"a.xml": b"a" * 1000, "b.xml": b"b" * 1000})

        with pytest.raises(ZipRejected) as erro:
            summarize_zip(io.BytesIO(dados), ZipLimits(max_total_bytes=1500))

        assert erro.value.code == "tamanho_total"

    def test_entrada_grande_demais_e_recusada_so_ela(self) -> None:
        dados = build_zip({"grande.xml": b"<a>" + b"x" * 5000 + b"</a>", "pequena.xml": b"<a/>"})

        resultado = itens(dados, ZipLimits(max_entry_bytes=1000))

        assert resultado == [("grande.xml", False, "grande_demais"), ("pequena.xml", True, "")]

    def test_razao_de_compressao_suspeita(self) -> None:
        dados = build_zip({"bomba.xml": b"0" * 100_000, "normal.xml": b"<a/>"})

        resultado = itens(dados, ZipLimits(max_ratio=50, max_entry_bytes=200_000))

        assert resultado[0] == ("bomba.xml", False, "razao_suspeita")
        assert resultado[1] == ("normal.xml", True, "")

    def test_tamanho_declarado_que_mente_nao_estoura_a_memoria(self) -> None:
        """O cabeçalho diz 10 bytes, o conteúdo tem 5 mil: a leitura para no teto."""

        dados = bytearray(build_zip({"a.xml": b"<a>" + b"x" * 5000 + b"</a>"}, compress=False))
        # file_size no cabeçalho local (offset 22) e no diretório central (offset 24).
        central = dados.find(b"PK\x01\x02")
        dados[central + 24 : central + 28] = (10).to_bytes(4, "little")

        resultado = itens(bytes(dados), ZipLimits(max_entry_bytes=100))

        assert resultado[0][2] in {"grande_demais", "corrompido"}

    def test_entrada_criptografada(self) -> None:
        dados = bytearray(build_zip({"a.xml": b"<a/>"}))
        central = dados.find(b"PK\x01\x02")
        dados[central + 8] |= 0x1

        assert itens(bytes(dados)) == [("a.xml", False, "criptografado")]

    def test_entrada_corrompida_nao_derruba_as_outras(self) -> None:
        dados = bytearray(
            build_zip({"a.xml": b"<a>" + b"abc" * 50 + b"</a>", "b.xml": b"<b/>"}, compress=False)
        )
        posicao = dados.find(b"abcabc")
        dados[posicao] ^= 0xFF  # quebra o CRC da primeira entrada

        resultado = itens(bytes(dados))

        assert resultado[0] == ("a.xml", False, "corrompido")
        assert resultado[1] == ("b.xml", True, "")

    def test_zip_aninhado_nao_e_aberto(self) -> None:
        interno = build_zip({"x.xml": b"<x/>"})
        dados = build_zip({"interno.zip": interno})

        assert itens(dados) == [("interno.zip", False, "nao_xml")]
