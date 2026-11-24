"""Leitor de XML fiscal do Contraprova: NF-e, CT-e, eventos e recusa de XML inseguro."""

from __future__ import annotations

import pytest

from apps.crosscheck.engine import fiscal_xml as fx
from apps.crosscheck.synthetic import (
    CteSpec,
    ItemSpec,
    NfeSpec,
    build_cancel_event_xml,
    build_cte_xml,
    build_nfe_xml,
    make_cnpj,
    make_key,
)

EMPRESA = make_cnpj("12345678", "0001")
FORNECEDOR = make_cnpj("98765432", "0001")


def nfe(numero: int = 1, **campos: object) -> NfeSpec:
    chave = make_key(cnpj=FORNECEDOR, number=numero)
    return NfeSpec(key=chave, emit_cnpj=FORNECEDOR, dest_cnpj=EMPRESA, number=numero, **campos)  # type: ignore[arg-type]


def ler_nfe(spec: NfeSpec) -> fx.ParsedNfe:
    resultado = fx.parse_fiscal_xml(build_nfe_xml(spec))
    assert isinstance(resultado, fx.ParsedNfe)
    return resultado


class TestNfe:
    def test_campos_e_totais_em_centavos(self) -> None:
        spec = nfe(
            12,
            v_nf="1234.56",
            v_icms="210.00",
            v_ipi="15.30",
            v_ipi_devol="2.00",
            emit_uf="MG",
            dest_uf="SP",
        )

        doc = ler_nfe(spec)

        assert doc.key == spec.key
        assert (doc.model, doc.series, doc.number, doc.tp_nf) == ("55", "1", "12", "1")
        assert doc.issued == "2026-09-01"
        assert doc.emit_doc == FORNECEDOR
        assert doc.dest_doc == EMPRESA
        assert (doc.emit_uf, doc.dest_uf) == ("MG", "SP")
        assert doc.c_stat == "100"
        assert doc.totals["vnf"] == 123456
        assert doc.totals["vicms"] == 21000
        assert doc.totals["vipi"] == 1530
        assert doc.totals["vipi_devol"] == 200
        assert doc.totals["vprod"] == 10000
        assert doc.item_count == 1

    def test_sem_namespace(self) -> None:
        doc = ler_nfe(nfe(namespace=False))

        assert doc.totals["vnf"] == 10000

    def test_nfe_sem_protocolo_nao_tem_cstat(self) -> None:
        doc = ler_nfe(nfe(wrapper=False))
        assert doc.c_stat == ""

        doc = ler_nfe(nfe(protocol=False))
        assert doc.c_stat == ""

    def test_icms_dos_itens_agrupado_pelo_cfop(self) -> None:
        spec = nfe(
            items=[
                ItemSpec(cfop="5102", v_icms="18.00"),
                ItemSpec(cfop="5102", v_icms="7.00"),
                ItemSpec(cfop="5405", v_icms="0.00"),
            ]
        )

        doc = ler_nfe(spec)

        assert doc.icms_by_cfop == {"5102": 2500, "5405": 0}
        assert doc.item_count == 3

    @pytest.mark.parametrize("grupo", ["ICMSSN101", "ICMSSN201", "ICMSSN900"])
    def test_credito_do_simples_nacional_em_101_201_e_900(self, grupo: str) -> None:
        """Regressão do legado, que só olhava ICMSSN101 em quatro das cinco cópias."""

        spec = nfe(
            items=[ItemSpec(group=grupo, v_cred_sn="2.50"), ItemSpec(group=grupo, v_cred_sn="1.25")]
        )

        doc = ler_nfe(spec)

        assert doc.cred_sn == 375

    def test_icms_sn_sem_credito_nao_soma_nada(self) -> None:
        doc = ler_nfe(nfe(items=[ItemSpec(group="ICMSSN102")]))

        assert doc.cred_sn == 0

    def test_icms_51_traz_os_valores_do_diferimento(self) -> None:
        item = ItemSpec(
            cfop="5101",
            group="ICMS51",
            v_bc="1000.00",
            p_icms="18.0000",
            v_icms_op="180.00",
            p_dif="50.0000",
            v_icms_dif="90.00",
            v_icms="90.00",
        )

        doc = ler_nfe(nfe(items=[ItemSpec(cfop="5102"), item]))

        (achado,) = doc.icms51
        assert achado.item == 2
        assert achado.cfop == "5101"
        assert achado.v_bc == 100000
        assert achado.p_icms == 180000
        assert achado.v_icms_op == 18000
        assert achado.p_dif == 500000
        assert achado.v_icms_dif == 9000
        assert achado.v_icms == 9000
        assert achado.arithmetic_ok

    def test_icms_51_com_aritmetica_errada(self) -> None:
        item = ItemSpec(
            group="ICMS51", v_icms_op="180.00", p_dif="50.0000", v_icms_dif="90.00", v_icms="80.00"
        )

        (achado,) = ler_nfe(nfe(items=[item])).icms51

        assert not achado.arithmetic_ok

    def test_icms_51_sem_campos_de_diferimento_nao_acusa(self) -> None:
        item = fx.Icms51Item(1, "5101", 10000, 180000, None, None, None, 1800)

        assert item.arithmetic_ok

    def test_homologacao_nao_vale(self) -> None:
        resultado = fx.parse_fiscal_xml(build_nfe_xml(nfe(tp_amb="2")))

        assert isinstance(resultado, fx.Ignored)
        assert resultado.reason == "homologacao"

    def test_nfce_modelo_65(self) -> None:
        spec = nfe(model="65")
        spec.key = make_key(cnpj=FORNECEDOR, number=1, model="65")

        assert ler_nfe(spec).model == "65"


class TestSeguranca:
    BOMBA = (
        b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        b'<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>'
        b"<nfeProc>&lol2;</nfeProc>"
    )

    def test_bomba_de_entidades_e_recusada(self) -> None:
        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(self.BOMBA)

        assert erro.value.code == "dtd_proibido"

    def test_entidade_externa_xxe_e_recusada(self) -> None:
        xxe = (
            b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>'
            b"<nfeProc>&e;</nfeProc>"
        )

        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(xxe)

        assert erro.value.code == "dtd_proibido"

    def test_doctype_em_minuscula_tambem(self) -> None:
        with pytest.raises(fx.FiscalXmlError):
            fx.parse_fiscal_xml(b'<?xml version="1.0"?><!doctype x><nfeProc/>')

    def test_doctype_no_arquivo_de_nfe_e_recusado(self) -> None:
        dados = build_nfe_xml(nfe(doctype="<!DOCTYPE nfeProc>"))

        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(dados)

        assert erro.value.code == "dtd_proibido"

    def test_byte_nulo(self) -> None:
        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(b"<nfeProc>\x00</nfeProc>")

        assert erro.value.code == "nul"

    def test_acima_do_teto(self) -> None:
        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(b"<a>" + b"x" * (fx.MAX_XML_BYTES + 1) + b"</a>")

        assert erro.value.code == "grande_demais"

    @pytest.mark.parametrize("dados", [b"", b"nao e xml", b"<nfeProc><NFe></nfeProc>", b"\xff\xfe"])
    def test_xml_quebrado(self, dados: bytes) -> None:
        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(dados)

        assert erro.value.code == "xml_invalido"

    def test_mensagem_de_erro_nao_vaza_o_conteudo(self) -> None:
        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(b"<a>segredo-do-cliente</b>")

        assert "segredo" not in erro.value.message


class TestChaveENumeros:
    def test_dv_invalido_e_recusado(self) -> None:
        spec = nfe()
        spec.key = spec.key[:-1] + str((int(spec.key[-1]) + 1) % 10)

        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(build_nfe_xml(spec))

        assert erro.value.code == "chave_dv_invalida"

    def test_chave_curta_e_recusada(self) -> None:
        spec = nfe()
        spec.key = spec.key[:30]

        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(build_nfe_xml(spec))

        assert erro.value.code == "chave_invalida"

    def test_valor_que_nao_e_numero_e_erro_e_nao_zero(self) -> None:
        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(build_nfe_xml(nfe(v_nf="abc")))

        assert erro.value.code == "valor_invalido"

    def test_sem_icmstot(self) -> None:
        dados = build_nfe_xml(nfe()).replace(b"ICMSTot", b"Outro")

        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(dados)

        assert erro.value.code == "sem_icmstot"

    def test_sem_infnfe(self) -> None:
        with pytest.raises(fx.FiscalXmlError) as erro:
            fx.parse_fiscal_xml(b"<NFe><x/></NFe>")

        assert erro.value.code == "sem_infnfe"


class TestCte:
    def spec(self, **campos: object) -> CteSpec:
        chave = make_key(cnpj=FORNECEDOR, number=5, model="57")
        return CteSpec(key=chave, emit_cnpj=FORNECEDOR, tomador_cnpj=EMPRESA, number=5, **campos)  # type: ignore[arg-type]

    def test_campos(self) -> None:
        resultado = fx.parse_fiscal_xml(build_cte_xml(self.spec(v_tprest="350.00", v_icms="42.00")))

        assert isinstance(resultado, fx.ParsedCte)
        assert resultado.model == "57"
        assert resultado.number == "5"
        assert resultado.v_tprest == 35000
        assert resultado.v_icms == 4200
        assert resultado.v_bc == 10000
        assert resultado.emit_doc == FORNECEDOR
        assert EMPRESA in resultado.party_docs
        assert resultado.c_stat == "100"

    def test_direcao(self) -> None:
        cte = fx.parse_fiscal_xml(build_cte_xml(self.spec()))
        assert isinstance(cte, fx.ParsedCte)

        assert fx.company_direction(cte, EMPRESA) == "E"
        assert fx.company_direction(cte, FORNECEDOR) == "S"
        assert fx.company_direction(cte, make_cnpj("11111111", "0001")) == "X"


class TestEventosEOutros:
    def test_cancelamento_registrado(self) -> None:
        chave = make_key(cnpj=FORNECEDOR, number=1)

        evento = fx.parse_fiscal_xml(build_cancel_event_xml(chave))

        assert isinstance(evento, fx.ParsedEvent)
        assert evento.key == chave
        assert evento.tp_evento == "110111"
        assert evento.cancels

    def test_cancelamento_nao_registrado_nao_cancela(self) -> None:
        chave = make_key(cnpj=FORNECEDOR, number=1)

        evento = fx.parse_fiscal_xml(build_cancel_event_xml(chave, c_stat="573"))

        assert isinstance(evento, fx.ParsedEvent)
        assert not evento.cancels

    def test_resumo_da_sefaz_e_ignorado(self) -> None:
        resultado = fx.parse_fiscal_xml(b"<resNFe><chNFe>1</chNFe></resNFe>")

        assert isinstance(resultado, fx.Ignored)
        assert resultado.reason == "resumo"

    def test_tipo_desconhecido_e_ignorado_com_motivo(self) -> None:
        resultado = fx.parse_fiscal_xml(b"<MDFe/>")

        assert isinstance(resultado, fx.Ignored)
        assert resultado.reason == "tipo_nao_suportado"
        assert "MDFe" in resultado.detail


class TestDirecaoEUf:
    def test_saida_propria(self) -> None:
        doc = ler_nfe(
            NfeSpec(key=make_key(cnpj=EMPRESA, number=1), emit_cnpj=EMPRESA, dest_cnpj=FORNECEDOR)
        )

        assert fx.company_direction(doc, EMPRESA) == "S"

    def test_entrada_propria_tpnf_zero(self) -> None:
        spec = NfeSpec(
            key=make_key(cnpj=EMPRESA, number=1), emit_cnpj=EMPRESA, dest_cnpj=FORNECEDOR, tp_nf="0"
        )

        assert fx.company_direction(ler_nfe(spec), EMPRESA) == "E"

    def test_entrada_de_terceiro(self) -> None:
        assert fx.company_direction(ler_nfe(nfe()), EMPRESA) == "E"

    def test_nota_de_outra_empresa(self) -> None:
        assert fx.company_direction(ler_nfe(nfe()), make_cnpj("55555555", "0001")) == "X"

    def test_a_uf_da_contraparte_depende_da_direcao(self) -> None:
        """Regressão do legado, que sempre usava a UF do destinatário, mesmo na entrada."""

        doc = ler_nfe(nfe(emit_uf="MG", dest_uf="SP"))

        assert fx.counterpart_uf(doc, "E") == "MG"
        assert fx.counterpart_uf(doc, "S") == "SP"

    @pytest.mark.parametrize(
        ("codigo", "grupo"),
        [
            ("100", "autorizada"),
            ("150", "autorizada"),
            ("110", "denegada"),
            ("301", "denegada"),
            ("302", "denegada"),
            ("101", "cancelada"),
            ("", "sem_protocolo"),
            ("999", "outro"),
        ],
    )
    def test_grupo_de_status(self, codigo: str, grupo: str) -> None:
        assert fx.status_group(codigo) == grupo
