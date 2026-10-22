"""Leitor da EFD ICMS/IPI do Contraprova: leiaute, integridade e recusa de arquivo ruim."""

from __future__ import annotations

import io
from datetime import date

import pytest

from apps.crosscheck.engine import efd
from apps.crosscheck.engine.efd import EfdFormatError, EfdReader
from apps.crosscheck.synthetic import (
    AnalyticSpec,
    DocSpec,
    EfdSpec,
    build_efd,
    make_cnpj,
    make_key,
)

EMPRESA = make_cnpj("12345678", "0001")
FORNECEDOR = make_cnpj("98765432", "0001")


def ler(dados: bytes) -> tuple[list[efd.EfdDocument], efd.EfdSummary]:
    leitor = EfdReader(io.BytesIO(dados))
    documentos = list(leitor.documents())
    return documentos, leitor.summary()


def documento(numero: int = 1, **campos: object) -> DocSpec:
    chave = make_key(cnpj=FORNECEDOR, number=numero)
    return DocSpec(number=numero, key=chave, **campos)  # type: ignore[arg-type]


class TestLeiaute:
    def test_le_documentos_com_analitico_e_prova_a_integridade(self) -> None:
        spec = EfdSpec(
            cnpj=EMPRESA,
            docs=[
                documento(1),
                documento(2, analytics=[AnalyticSpec(cfop="1102"), AnalyticSpec(cfop="1403")]),
                documento(3, reg="D100", cod_mod="57"),
            ],
        )

        docs, resumo = ler(build_efd(spec))

        assert [d.reg for d in docs] == ["C100", "C100", "D100"]
        assert [len(d.analytics) for d in docs] == [1, 2, 1]
        assert docs[2].analytics[0].reg == "D190"
        assert resumo.errors == ()
        assert resumo.header is not None
        assert resumo.header.cnpj == EMPRESA
        assert resumo.header.competence == "2026-09"
        assert resumo.header.cod_ver == "019"
        assert resumo.counts["C100"] == 2
        assert resumo.counts["D100"] == 1
        assert resumo.encoding == "utf-8"
        assert resumo.line_ending == "CRLF"

    def test_campos_do_c100_seguem_o_guia_pratico(self) -> None:
        """Regressão do legado: o campo 10 do C100 é DT_DOC, nunca CFOP."""

        item = documento(
            7,
            ind_oper="0",
            ind_emit="1",
            cod_part="FORN9",
            ser="3",
            dt_doc="05092026",
            dt_es="07092026",
            vl_doc="1000,00",
            vl_desc="11,11",
            vl_merc="990,00",
            vl_bc_icms="900,00",
            vl_icms="162,00",
            vl_bc_icms_st="50,00",
            vl_icms_st="9,00",
            vl_ipi="25,50",
        )

        (doc,), _ = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[item])))

        assert (doc.ind_oper, doc.ind_emit, doc.cod_part, doc.cod_mod) == ("0", "1", "FORN9", "55")
        assert (doc.cod_sit, doc.ser, doc.num_doc) == ("00", "3", "7")
        assert doc.key == item.key
        assert doc.dt_doc == date(2026, 9, 5)
        assert doc.dt_es == date(2026, 9, 7)
        assert doc.money["vl_doc"] == 100000
        assert doc.money["vl_desc"] == 1111
        assert doc.money["vl_merc"] == 99000
        assert doc.money["vl_bc_icms"] == 90000
        assert doc.money["vl_icms"] == 16200
        assert doc.money["vl_bc_icms_st"] == 5000
        assert doc.money["vl_icms_st"] == 900
        assert doc.money["vl_ipi"] == 2550

    def test_campos_do_c190_seguem_o_guia_pratico(self) -> None:
        """Regressão do legado: campos 3/6/7/11 são CFOP/BC/ICMS/IPI e o 12 é COD_OBS."""

        analitico = AnalyticSpec(
            cst="020",
            cfop="1556",
            aliq="12,00",
            vl_opr="500,00",
            vl_bc="400,00",
            vl_icms="48,00",
            vl_bc_st="10,00",
            vl_icms_st="2,00",
            vl_red_bc="100,00",
            vl_ipi="7,25",
            cod_obs="OBS001",
        )

        (doc,), _ = ler(
            build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1, analytics=[analitico])]))
        )

        (linha,) = doc.analytics
        assert linha.reg == "C190"
        assert (linha.cst_icms, linha.cfop, linha.aliq) == ("020", "1556", 120000)
        assert linha.vl_opr == 50000
        assert linha.vl_bc_icms == 40000
        assert linha.vl_icms == 4800
        assert linha.vl_bc_icms_st == 1000
        assert linha.vl_icms_st == 200
        assert linha.vl_red_bc == 10000
        assert linha.vl_ipi == 725
        assert linha.cod_obs == "OBS001"

    def test_campos_do_d100_e_d190(self) -> None:
        item = documento(
            9,
            reg="D100",
            cod_mod="57",
            sub="1",
            dt_doc="03092026",
            dt_es="04092026",
            vl_doc="300,00",
            vl_serv="280,00",
            vl_bc_icms="280,00",
            vl_icms="33,60",
            chv_ref="",
            analytics=[AnalyticSpec(cfop="1352", vl_opr="300,00", vl_bc="280,00", vl_icms="33,60")],
        )

        (doc,), _ = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[item])))

        assert doc.reg == "D100"
        assert doc.key == item.key
        assert doc.num_doc == "9"
        assert doc.dt_doc == date(2026, 9, 3)
        assert doc.dt_es == date(2026, 9, 4)  # DT_A_P
        assert doc.money["vl_doc"] == 30000
        assert doc.money["vl_serv"] == 28000
        assert doc.money["vl_bc_icms"] == 28000
        assert doc.money["vl_icms"] == 3360
        (linha,) = doc.analytics
        assert linha.reg == "D190"
        assert (linha.cfop, linha.vl_opr, linha.vl_icms) == ("1352", 30000, 3360)
        assert linha.vl_ipi is None
        assert linha.vl_bc_icms_st is None

    def test_documento_cancelado_vem_sem_valores(self) -> None:
        item = documento(4, cod_sit="02")

        (doc,), resumo = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[item])))

        assert doc.cod_sit == "02"
        assert doc.key == item.key
        assert all(valor is None for valor in doc.money.values())
        assert doc.analytics == []
        assert resumo.errors == ()

    def test_chave_de_ligacao_sem_chave_usa_o_que_identifica_o_documento(self) -> None:
        item = DocSpec(cod_mod="01", key="", number=55, ser="2", cod_part="FORN2")

        (doc,), _ = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[item])))

        assert doc.key == ""
        assert doc.matching_key == "C100:0:1:01:2::55:FORN2"

    def test_chave_em_minuscula_vira_maiuscula(self) -> None:
        item = documento(1)
        item.key = item.key.lower()

        (doc,), _ = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[item])))

        assert doc.key == item.key.upper()


class TestArquivosIncompletos:
    """Regressão: o legado quebrava sem bloco D, sem C190 ou sem C100."""

    def test_sem_bloco_d_e_sem_analitico(self) -> None:
        docs, resumo = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1, analytics=[])])))

        assert len(docs) == 1
        assert docs[0].analytics == []
        assert resumo.errors == ()

    def test_sem_nenhum_documento(self) -> None:
        docs, resumo = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[])))

        assert docs == []
        assert resumo.errors == ()
        assert resumo.header is not None

    def test_sem_9999_o_arquivo_esta_incompleto(self) -> None:
        _, resumo = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1)]), omit_trailer=True))

        assert [item.code for item in resumo.errors] == ["sem_9999"]

    def test_total_do_9999_errado(self) -> None:
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1)]), wrong_total=3)

        _, resumo = ler(dados)

        assert [item.code for item in resumo.errors] == ["total_9999"]
        assert "3" in resumo.errors[0].message

    def test_contagem_do_9900_errada(self) -> None:
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1)]), wrong_count=("C100", 5))

        _, resumo = ler(dados)

        assert [item.code for item in resumo.errors] == ["contagem_9900"]
        assert "C100" in resumo.errors[0].message

    def test_arquivo_cortado_no_meio_e_detectado(self) -> None:
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(i) for i in range(1, 30)]))
        cortado = dados[: len(dados) // 2]

        _, resumo = ler(cortado)

        assert {item.code for item in resumo.errors} >= {"sem_9999"}

    def test_conteudo_depois_do_9999_e_aviso(self) -> None:
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1)])) + b"lixo\r\n"

        _, resumo = ler(dados)

        assert resumo.errors == ()
        assert [item.code for item in resumo.warnings] == ["conteudo_apos_9999"]


class TestFormato:
    def test_efd_contribuicoes_e_recusada(self) -> None:
        linha = b"|0000|006|0|||01092026|30092026|EMPRESA|12345678000195|SP|3550308||1|1|\r\n"

        with pytest.raises(EfdFormatError) as erro:
            ler(linha)

        assert erro.value.code == "nao_icms_ipi"

    def test_primeira_linha_precisa_ser_o_0000(self) -> None:
        with pytest.raises(EfdFormatError) as erro:
            ler(b"|C100|0|1|\r\n|9999|2|\r\n")

        assert erro.value.code == "sem_0000"

    def test_arquivo_qualquer_nao_e_efd(self) -> None:
        with pytest.raises(EfdFormatError):
            ler(b"isto nao e um arquivo SPED\r\n")

    def test_periodo_invalido(self) -> None:
        linha = b"|0000|019|0|31092026|30092026|EMPRESA|12345678000195||SP|1|3550308|||A|1|\r\n"

        with pytest.raises(EfdFormatError) as erro:
            ler(linha)

        assert erro.value.code in {"periodo_invalido", "nao_icms_ipi"}

    def test_0000_repetido_e_erro(self) -> None:
        dados = build_efd(
            EfdSpec(cnpj=EMPRESA, docs=[documento(1)]),
            extra_lines=(f"|0000|019|0|01092026|30092026|X|{EMPRESA}||SP|1|3550308|||A|1|",),
        )

        _, resumo = ler(dados)

        assert "0000_repetido" in {item.code for item in resumo.errors}

    def test_bom_utf8_e_aceito(self) -> None:
        dados = b"\xef\xbb\xbf" + build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1)]))

        docs, resumo = ler(dados)

        assert len(docs) == 1
        assert resumo.errors == ()
        assert [item.code for item in resumo.warnings] == ["bom"]

    def test_latin1_e_lido_sem_substituir_caracteres(self) -> None:
        spec = EfdSpec(cnpj=EMPRESA, nome="INDÚSTRIA AÇÃO LTDA", docs=[documento(1)])

        _, resumo = ler(build_efd(spec, encoding="latin-1"))

        assert resumo.encoding == "latin-1"
        assert resumo.header is not None
        assert resumo.header.nome == "INDÚSTRIA AÇÃO LTDA"
        assert "�" not in resumo.header.nome

    def test_utf8_tambem_e_aceito(self) -> None:
        spec = EfdSpec(cnpj=EMPRESA, nome="INDÚSTRIA AÇÃO LTDA", docs=[documento(1)])

        _, resumo = ler(build_efd(spec, encoding="utf-8"))

        assert resumo.encoding == "utf-8"
        assert resumo.header is not None
        assert resumo.header.nome == "INDÚSTRIA AÇÃO LTDA"

    def test_fim_de_linha_lf(self) -> None:
        _, resumo = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1)]), eol="\n"))

        assert resumo.line_ending == "LF"
        assert resumo.errors == ()

    def test_fim_de_linha_misto_e_aviso(self) -> None:
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1)]), eol="\r\n")
        dados = dados.replace(b"|0001|0|\r\n", b"|0001|0|\n")

        _, resumo = ler(dados)

        assert "fim_de_linha_misto" in {item.code for item in resumo.warnings}

    def test_linha_gigante_e_ignorada_sem_ler_tudo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(efd, "MAX_LINE_BYTES", 400)
        gigante = "|C170|" + "9" * 5000 + "|"
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1)]), extra_lines=(gigante,))

        docs, resumo = ler(dados)

        assert len(docs) == 1
        assert "linha_longa" in {item.code for item in resumo.warnings}

    def test_byte_nulo_e_aviso_e_a_linha_e_ignorada(self) -> None:
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1)]), extra_lines=("|C170|1\x00|",))

        _, resumo = ler(dados)

        assert "nul" in {item.code for item in resumo.warnings}

    def test_linha_sem_delimitadores(self) -> None:
        dados = build_efd(
            EfdSpec(cnpj=EMPRESA, docs=[documento(1)]), extra_lines=("C170 sem barras",)
        )

        _, resumo = ler(dados)

        assert "delimitadores" in {item.code for item in resumo.warnings}

    def test_valor_invalido_vira_aviso_e_o_campo_fica_vazio(self) -> None:
        item = documento(1, vl_icms="1.234,56")

        (doc,), resumo = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[item])))

        assert doc.money["vl_icms"] is None
        assert "valor_invalido" in {i.code for i in resumo.warnings}

    def test_data_invalida_vira_aviso(self) -> None:
        item = documento(1, dt_doc="31022026")

        (doc,), resumo = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[item])))

        assert doc.dt_doc is None
        assert "data_invalida" in {i.code for i in resumo.warnings}

    def test_registro_curto_e_aviso(self) -> None:
        item = documento(1)
        item.raw_override = f"|C100|0|1|FORN1|55|00|1|1|{item.key}|01092026|"

        docs, resumo = ler(build_efd(EfdSpec(cnpj=EMPRESA, docs=[item])))

        assert docs[0].money["vl_doc"] is None
        assert "campos_curtos" in {i.code for i in resumo.warnings}


class TestVinculoDoAnalitico:
    def test_registro_filho_desconhecido_nao_fecha_o_documento(self) -> None:
        item = documento(1, analytics=[])
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[item]))
        dados = dados.replace(
            b"|C990|",
            b"|C195|OBS|\r\n|C190|000|1102|18,00|100,00|100,00|18,00|0,00|0,00|0,00|0,00||\r\n|C990|",
        )

        (doc,), _ = ler(dados)

        assert len(doc.analytics) == 1

    def test_registro_de_outro_nivel_fecha_o_documento(self) -> None:
        item = documento(1, analytics=[])
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[item]))
        dados = dados.replace(
            b"|C990|",
            b"|C300|1|1|01092026|\r\n|C190|000|1102|18,00|100,00|100,00|18,00|0,00|0,00|0,00|0,00||\r\n|C990|",
        )

        docs, resumo = ler(dados)

        assert docs[0].analytics == []
        assert "analitico_orfao" in {i.code for i in resumo.warnings}

    def test_d190_nao_gruda_em_c100(self) -> None:
        item = documento(1, analytics=[])
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[item]))
        dados = dados.replace(b"|C990|", b"|D190|000|1352|12,00|1,00|1,00|0,12|0,00|\r\n|C990|")

        docs, resumo = ler(dados)

        assert docs[0].analytics == []
        assert "analitico_orfao" in {i.code for i in resumo.warnings}

    def test_cada_documento_leva_so_o_seu_analitico(self) -> None:
        spec = EfdSpec(
            cnpj=EMPRESA,
            docs=[
                documento(1, analytics=[AnalyticSpec(cfop="1101")]),
                documento(2, analytics=[AnalyticSpec(cfop="2102"), AnalyticSpec(cfop="2556")]),
                documento(3, analytics=[]),
            ],
        )

        docs, _ = ler(build_efd(spec))

        assert [[a.cfop for a in d.analytics] for d in docs] == [["1101"], ["2102", "2556"], []]


class TestLeituraRapida:
    def test_peek_header_le_so_a_primeira_linha(self) -> None:
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1)]))
        fluxo = io.BytesIO(dados)

        cabecalho = efd.peek_header(fluxo)

        assert cabecalho.cnpj == EMPRESA
        assert fluxo.tell() == 0

    def test_peek_trailer_acha_o_total_no_fim(self) -> None:
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(i) for i in range(1, 50)]))

        total = efd.peek_trailer(io.BytesIO(dados))

        assert total == dados.count(b"\n")

    def test_peek_trailer_sem_9999(self) -> None:
        dados = build_efd(EfdSpec(cnpj=EMPRESA, docs=[documento(1)]), omit_trailer=True)

        assert efd.peek_trailer(io.BytesIO(dados)) is None

    def test_peek_header_recusa_o_que_nao_e_efd(self) -> None:
        with pytest.raises(EfdFormatError):
            efd.peek_header(io.BytesIO(b"<xml/>"))

    def test_summary_antes_do_fim_e_erro_de_uso(self) -> None:
        leitor = EfdReader(io.BytesIO(b""))

        with pytest.raises(RuntimeError):
            leitor.summary()
