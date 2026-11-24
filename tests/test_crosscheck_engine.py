"""Comparadores e orquestração do motor do Contraprova, com arquivos sintéticos.

Cada defeito do legado catalogado na etapa 15 tem aqui um teste que falharia no comportamento
antigo: crash sem bloco D, CFOP_IGNORAR suprimindo o valor do documento, UF do destinatário na
entrada, float com tolerância de 0,01, chave duplicada engolida, XML de outra empresa
aparecendo como "não escriturado", etc.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from apps.crosscheck.engine import runner
from apps.crosscheck.engine.dominio_file import DominioRow
from apps.crosscheck.engine.findings import CollectingSink, Finding, Kind, RunCancelled
from apps.crosscheck.engine.keys import format_cnpj
from apps.crosscheck.engine.rules import (
    DEFAULT_SPED_SPED_FIELDS,
    ICMS_ONLY_FIELDS,
    RuleSet,
)
from apps.crosscheck.engine.runner import InputFile, RunOutcome, RunRejected
from apps.crosscheck.synthetic import (
    AnalyticSpec,
    CteSpec,
    DocSpec,
    EfdSpec,
    ItemSpec,
    NfeSpec,
    build_cancel_event_xml,
    build_cte_xml,
    build_efd,
    build_nfe_xml,
    build_zip,
    make_cnpj,
    make_key,
)

EMPRESA = make_cnpj("12345678", "0001")
FORNECEDOR = make_cnpj("98765432", "0001")
OUTRA = make_cnpj("55555555", "0001")


def chave(numero: int, *, emit: str = FORNECEDOR, model: str = "55") -> str:
    return make_key(cnpj=emit, number=numero, model=model)


def doc(numero: int, **campos: Any) -> DocSpec:
    return DocSpec(number=numero, key=chave(numero), **campos)


def nfe(numero: int, **campos: Any) -> NfeSpec:
    campos.setdefault("emit_cnpj", FORNECEDOR)
    campos.setdefault("dest_cnpj", EMPRESA)
    return NfeSpec(key=chave(numero, emit=campos["emit_cnpj"]), number=numero, **campos)


class Cenario:
    """Monta os arquivos de uma conferência numa pasta temporária e a executa."""

    def __init__(self, raiz: Path) -> None:
        self.raiz = raiz
        (raiz / "entrada").mkdir()
        (raiz / "trabalho").mkdir()
        self.arquivos: list[InputFile] = []

    def _gravar(self, nome: str, dados: bytes, papel: str) -> InputFile:
        caminho = self.raiz / "entrada" / f"{len(self.arquivos)}-{nome}"
        caminho.write_bytes(dados)
        item = InputFile(papel, caminho, nome)
        self.arquivos.append(item)
        return item

    def sped(
        self, docs: list[DocSpec], *, papel: str = "sped", cnpj: str = EMPRESA, **opcoes: Any
    ) -> Cenario:
        spec_kwargs = {k: opcoes.pop(k) for k in ("dt_ini", "dt_fin") if k in opcoes}
        dados = build_efd(EfdSpec(cnpj=cnpj, docs=docs, **spec_kwargs), **opcoes)
        self._gravar(f"{papel}.txt", dados, papel)
        return self

    def xml(self, *itens: NfeSpec | CteSpec | bytes, zip: bool = True) -> Cenario:
        arquivos: dict[str, bytes] = {}
        for posicao, item in enumerate(itens):
            if isinstance(item, NfeSpec):
                dados = build_nfe_xml(item)
            elif isinstance(item, CteSpec):
                dados = build_cte_xml(item)
            else:
                dados = item
            arquivos[f"nota-{posicao}.xml"] = dados
        if zip:
            self._gravar("xmls.zip", build_zip(arquivos), "xml")
        else:
            for nome, dados in arquivos.items():
                self._gravar(nome, dados, "xml")
        return self

    def rodar(
        self,
        ferramenta: str = "sped_xml",
        regras: RuleSet | None = None,
        *,
        empresa: str = EMPRESA,
        competencia: str = "2026-09",
        dominio: Iterable[DominioRow] | None = None,
        sink: CollectingSink | None = None,
    ) -> tuple[RunOutcome, CollectingSink]:
        sink = sink or CollectingSink()
        resultado = runner.run_tool(
            ferramenta,
            company_doc=empresa,
            competence=competencia,
            rules=regras or RuleSet(),
            inputs=self.arquivos,
            workdir=self.raiz / "trabalho",
            sink=sink,
            dominio_rows=dominio,
        )
        return resultado, sink


@pytest.fixture
def cenario(tmp_path: Path) -> Cenario:
    return Cenario(tmp_path)


def resumo(achados: list[Finding]) -> list[tuple[str, str, str, str]]:
    return [(a.kind, a.status, a.number, a.field) for a in achados]


class TestSpedXmlConferem:
    def test_documento_igual_ao_xml_nao_gera_achado(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)]).xml(nfe(1))

        resultado, sink = cenario.rodar()

        assert sink.findings == []
        assert resultado.counts["conferem"] == 1
        assert resultado.counts["com_xml"] == 1
        (linha,) = sink.matched_rows
        assert linha.values["vnf"] == (10000, 10000)
        assert linha.cfop == "1102"

    def test_xml_solto_e_zip_dao_o_mesmo_resultado(self, tmp_path: Path) -> None:
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        a, b = Cenario(tmp_path / "a"), Cenario(tmp_path / "b")
        a.sped([doc(1), doc(2, vl_doc="90,00")]).xml(nfe(1), nfe(2), zip=True)
        b.sped([doc(1), doc(2, vl_doc="90,00")]).xml(nfe(1), nfe(2), zip=False)

        resultado_a, sink_a = a.rodar()
        resultado_b, sink_b = b.rodar()

        assert resumo(sink_a.findings) == resumo(sink_b.findings)
        assert resultado_a.counts == resultado_b.counts

    def test_ordem_dos_achados_e_pelo_numero_do_documento(self, cenario: Cenario) -> None:
        cenario.sped([doc(10, vl_doc="1,00"), doc(2, vl_doc="1,00"), doc(1, vl_doc="1,00")])
        cenario.xml(nfe(10), nfe(2), nfe(1))

        _, sink = cenario.rodar()

        assert [a.number for a in sink.findings] == ["1", "2", "10"]

    def test_repetir_a_conferencia_da_o_mesmo_resultado(self, cenario: Cenario) -> None:
        cenario.sped([doc(1, vl_doc="1,00"), doc(2)]).xml(nfe(1), nfe(2), nfe(3))

        _, primeiro = cenario.rodar()
        (cenario.raiz / "trabalho" / "stage.sqlite3").unlink()
        _, segundo = cenario.rodar()

        assert resumo(primeiro.findings) == resumo(segundo.findings)


class TestValoresEDinheiro:
    def test_valor_do_documento_diferente(self, cenario: Cenario) -> None:
        cenario.sped([doc(1, vl_doc="150,00")]).xml(nfe(1))

        _, sink = cenario.rodar()

        (achado,) = sink.findings
        assert achado.kind == Kind.VALOR_DIVERGENTE
        assert (achado.field, achado.left_cents, achado.right_cents) == ("vnf", 15000, 10000)
        assert achado.delta_cents == 5000
        assert achado.status == "divergent"
        assert achado.doc_key == chave(1)
        assert achado.cfop == "1102"
        assert achado.operation == "E"
        assert achado.detail["c190"][0]["cfop"] == "1102"

    @pytest.mark.parametrize(
        ("sped", "tolerancia", "diverge"),
        [("100,01", 1, False), ("100,02", 1, True), ("100,01", 0, True), ("99,99", 1, False)],
    )
    def test_tolerancia_inclusiva_em_centavos(
        self, cenario: Cenario, sped: str, tolerancia: int, diverge: bool
    ) -> None:
        """No legado, 100,03 contra 100,02 acusava e 10,02 contra 10,01 passava (float)."""

        cenario.sped([doc(1, vl_doc=sped)]).xml(nfe(1))

        _, sink = cenario.rodar(regras=RuleSet(tolerance_cents=tolerancia))

        assert bool(sink.findings) is diverge

    def test_o_caso_do_float_100_03_contra_100_02(self, cenario: Cenario) -> None:
        cenario.sped([doc(1, vl_doc="100,03"), doc(2, vl_doc="10,02")])
        cenario.xml(nfe(1, v_nf="100.02"), nfe(2, v_nf="10.01"))

        _, sink = cenario.rodar()

        assert sink.findings == []

    def test_ipi_soma_o_ipi_devolvido(self, cenario: Cenario) -> None:
        cenario.sped([doc(1, vl_ipi="15,00"), doc(2, vl_ipi="10,00")])
        cenario.xml(
            nfe(1, v_ipi="10.00", v_ipi_devol="5.00"), nfe(2, v_ipi="10.00", v_ipi_devol="5.00")
        )

        _, sink = cenario.rodar()

        (achado,) = sink.findings
        assert achado.number == "2"
        assert (achado.field, achado.left_cents, achado.right_cents) == ("vipi", 1000, 1500)

    def test_icms_diferente(self, cenario: Cenario) -> None:
        cenario.sped([doc(1, vl_icms="17,00")]).xml(nfe(1, v_icms="18.00"))

        _, sink = cenario.rodar()

        (achado,) = sink.findings
        assert (achado.field, achado.left_cents, achado.right_cents) == ("vicms", 1700, 1800)

    def test_somente_icms_e_valor_do_documento_como_no_legado_simplificado(
        self, cenario: Cenario
    ) -> None:
        cenario.sped([doc(1, vl_ipi="9,00")]).xml(nfe(1, v_ipi="0.00"))

        _, completo = cenario.rodar()
        (cenario.raiz / "trabalho" / "stage.sqlite3").unlink()
        _, simplificado = cenario.rodar(regras=RuleSet(fields=ICMS_ONLY_FIELDS))

        assert [a.field for a in completo.findings] == ["vipi"]
        assert simplificado.findings == []

    def test_campos_opcionais_sao_conferidos_quando_pedidos(self, cenario: Cenario) -> None:
        cenario.sped([doc(1, vl_merc="95,00")]).xml(nfe(1))

        _, padrao = cenario.rodar()
        (cenario.raiz / "trabalho" / "stage.sqlite3").unlink()
        _, com_mercadorias = cenario.rodar(regras=RuleSet(fields=("vnf", "vprod")))

        assert padrao.findings == []
        assert [(a.field, a.left_cents, a.right_cents) for a in com_mercadorias.findings] == [
            ("vprod", 9500, 10000)
        ]

    def test_campo_vazio_no_sped_conta_como_zero_e_diverge(self, cenario: Cenario) -> None:
        item = doc(1)
        item.vl_icms = ""
        cenario.sped([item]).xml(nfe(1, v_icms="18.00"))

        _, sink = cenario.rodar()

        (achado,) = sink.findings
        assert achado.left_cents is None
        assert achado.right_cents == 1800
        assert achado.detail["sped_vazio"] is True


class TestSimplesNacional:
    @pytest.mark.parametrize("grupo", ["ICMSSN101", "ICMSSN201", "ICMSSN900"])
    def test_credito_do_sn_vale_como_icms_do_sped(self, cenario: Cenario, grupo: str) -> None:
        """Regressão do legado, que só reconhecia o crédito em alguns grupos e arquivos."""

        xml = nfe(1, v_icms="0.00", items=[ItemSpec(group=grupo, v_cred_sn="3.75")])
        cenario.sped([doc(1, vl_icms="3,75")]).xml(xml)

        _, sink = cenario.rodar()

        assert sink.findings == []

    def test_sped_diferente_do_icms_e_do_credito_diverge(self, cenario: Cenario) -> None:
        xml = nfe(1, v_icms="0.00", items=[ItemSpec(group="ICMSSN101", v_cred_sn="3.75")])
        cenario.sped([doc(1, vl_icms="4,00")]).xml(xml)

        _, sink = cenario.rodar()

        (achado,) = sink.findings
        assert achado.field == "vicms"
        assert achado.detail["cred_sn"] == 375

    def test_sped_igual_ao_icms_destacado_tambem_confere(self, cenario: Cenario) -> None:
        xml = nfe(1, v_icms="12.00", items=[ItemSpec(group="ICMSSN101", v_cred_sn="3.75")])
        cenario.sped([doc(1, vl_icms="12,00")]).xml(xml)

        _, sink = cenario.rodar()

        assert sink.findings == []


class TestEntradaSemCredito:
    def sem_credito(self, **campos: Any) -> DocSpec:
        analitico = AnalyticSpec(cfop="1556", vl_opr="100,00", vl_bc="0,00", vl_icms="0,00")
        return doc(1, vl_icms="0,00", analytics=[analitico], **campos)

    def test_icms_esperado_vira_ignorada_e_continua_listada(self, cenario: Cenario) -> None:
        cenario.sped([self.sem_credito()]).xml(nfe(1, v_icms="18.00"))

        resultado, sink = cenario.rodar()

        (achado,) = sink.findings
        assert (achado.field, achado.status) == ("vicms", "ignored")
        assert achado.detail["reason"] == "cfop_sem_credito"
        assert "sem crédito" in achado.message
        assert resultado.counts["ignorados"] == 1
        assert resultado.counts.get("divergentes", 0) == 0

    def test_o_valor_do_documento_nunca_e_ignorado(self, cenario: Cenario) -> None:
        """Regressão do CFOP_IGNORAR, que suprimia até o vNF."""

        cenario.sped([self.sem_credito(vl_doc="90,00")]).xml(nfe(1, v_icms="18.00"))

        resultado, sink = cenario.rodar()

        por_campo = {a.field: a.status for a in sink.findings}
        assert por_campo == {"vnf": "divergent", "vicms": "ignored"}
        assert resultado.counts["divergentes"] == 1

    def test_mistura_de_cfop_com_e_sem_credito_nao_ignora(self, cenario: Cenario) -> None:
        analiticos = [AnalyticSpec(cfop="1556"), AnalyticSpec(cfop="1102")]
        item = doc(1, vl_icms="0,00", analytics=analiticos)
        cenario.sped([item]).xml(nfe(1, v_icms="18.00"))

        _, sink = cenario.rodar()

        assert [a.status for a in sink.findings] == ["divergent"]

    def test_conjunto_de_cfop_e_configuravel(self, cenario: Cenario) -> None:
        item = doc(1, vl_icms="0,00", analytics=[AnalyticSpec(cfop="1102")])
        cenario.sped([item]).xml(nfe(1, v_icms="18.00"))

        _, sink = cenario.rodar(regras=RuleSet(no_credit_cfops=frozenset({"1102"})))

        assert [a.status for a in sink.findings] == ["ignored"]

    def test_saida_nunca_e_rebaixada(self, cenario: Cenario) -> None:
        item = DocSpec(
            number=1,
            key=chave(1, emit=EMPRESA),
            ind_oper="1",
            ind_emit="0",
            vl_icms="0,00",
            analytics=[AnalyticSpec(cfop="1556")],
        )
        cenario.sped([item]).xml(nfe(1, emit_cnpj=EMPRESA, dest_cnpj=FORNECEDOR, v_icms="18.00"))

        _, sink = cenario.rodar(regras=RuleSet(operation="S"))

        assert [a.status for a in sink.findings] == ["divergent"]


class TestSemXmlESemSped:
    def test_escriturado_sem_xml(self, cenario: Cenario) -> None:
        cenario.sped([doc(1), doc(2)]).xml(nfe(1))

        resultado, sink = cenario.rodar()

        (achado,) = sink.findings
        assert achado.kind == Kind.SEM_XML
        assert achado.number == "2"
        assert achado.left_cents == 10000
        assert resultado.counts["so_sped"] == 1

    def test_cancelado_no_sped_sem_xml_nao_e_achado(self, cenario: Cenario) -> None:
        cenario.sped([doc(1), doc(2, cod_sit="02")]).xml(nfe(1))

        resultado, sink = cenario.rodar()

        assert sink.findings == []
        assert resultado.counts["cancelados_sem_xml"] == 1

    def test_xml_da_empresa_que_nao_esta_no_sped(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)]).xml(nfe(1), nfe(2, v_nf="55.00"))

        resultado, sink = cenario.rodar()

        (achado,) = sink.findings
        assert achado.kind == Kind.XML_NAO_ESCRITURADO
        assert achado.number == "2"
        assert achado.right_cents == 5500
        assert achado.detail["source"].endswith(".xml")
        assert resultado.counts["so_xml"] == 1

    def test_so_xml_de_saida_so_aparece_se_a_operacao_inclui_saidas(self, cenario: Cenario) -> None:
        saida = nfe(7, emit_cnpj=EMPRESA, dest_cnpj=FORNECEDOR)
        cenario.sped([doc(1)]).xml(nfe(1), saida)

        _, entradas = cenario.rodar()
        (cenario.raiz / "trabalho" / "stage.sqlite3").unlink()
        _, ambas = cenario.rodar(regras=RuleSet(operation="A"))

        assert entradas.findings == []
        assert [a.number for a in ambas.findings] == ["7"]
        assert ambas.findings[0].operation == "S"

    def test_documento_de_saida_no_sped_so_entra_com_a_operacao_certa(
        self, cenario: Cenario
    ) -> None:
        """Regressão: o legado descartava `|C100|1|` (saída) por engano, sem dizer."""

        saida = DocSpec(
            number=3, key=chave(3, emit=EMPRESA), ind_oper="1", ind_emit="0", vl_doc="80,00"
        )
        cenario.sped([doc(1), saida]).xml(nfe(1), nfe(3, emit_cnpj=EMPRESA, dest_cnpj=FORNECEDOR))

        _, so_entradas = cenario.rodar()
        (cenario.raiz / "trabalho" / "stage.sqlite3").unlink()
        _, ambas = cenario.rodar(regras=RuleSet(operation="A"))

        assert so_entradas.findings == []
        assert [(a.number, a.field, a.operation) for a in ambas.findings] == [("3", "vnf", "S")]

    def test_xml_de_outra_empresa_nao_e_so_xml(self, cenario: Cenario) -> None:
        """Regressão: XML sem relação com a empresa não pode aparecer como não escriturado."""

        alheio = nfe(9, emit_cnpj=OUTRA, dest_cnpj=make_cnpj("77777777", "0001"))
        cenario.sped([doc(1)]).xml(nfe(1), alheio)

        resultado, sink = cenario.rodar()

        assert sink.findings == []
        assert resultado.ingest["outra_empresa"] == 1


class TestSituacao:
    def test_cancelada_no_sped_e_xml_autorizado_sem_evento(self, cenario: Cenario) -> None:
        cenario.sped([doc(1, cod_sit="02")]).xml(nfe(1))

        _, sink = cenario.rodar()

        (achado,) = sink.findings
        assert achado.kind == Kind.SITUACAO_DIVERGENTE
        assert achado.left_text.startswith("02")
        assert achado.right_text.startswith("100")

    def test_cancelada_no_sped_com_evento_de_cancelamento_confere(self, cenario: Cenario) -> None:
        evento = build_cancel_event_xml(chave(1))
        cenario.sped([doc(1, cod_sit="02")]).xml(nfe(1), evento)

        resultado, sink = cenario.rodar()

        assert sink.findings == []
        assert resultado.counts["cancelados_conferem"] == 1

    def test_regular_no_sped_e_cancelada_pelo_evento(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)]).xml(nfe(1), build_cancel_event_xml(chave(1)))

        _, sink = cenario.rodar()

        (achado,) = sink.findings
        assert achado.kind == Kind.SITUACAO_DIVERGENTE
        assert "cancelada" in achado.message.lower()

    def test_regular_no_sped_e_xml_denegado(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)]).xml(nfe(1, c_stat="110"))

        _, sink = cenario.rodar()

        assert [a.kind for a in sink.findings] == [Kind.SITUACAO_DIVERGENTE]

    def test_cancelado_pelo_evento_e_fora_do_sped_nao_e_achado(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)]).xml(nfe(1), nfe(2), build_cancel_event_xml(chave(2)))

        resultado, sink = cenario.rodar()

        assert sink.findings == []
        assert resultado.counts["xml_cancelados_fora_do_sped"] == 1

    def test_complementar_so_compara_campo_preenchido(self, cenario: Cenario) -> None:
        item = doc(1, cod_sit="06")
        item.vl_icms = ""
        item.vl_ipi = ""
        cenario.sped([item]).xml(nfe(1, v_icms="18.00", v_ipi="3.00"))

        _, sink = cenario.rodar()

        assert sink.findings == []


class TestChaves:
    def test_chave_duplicada_e_apontada_e_comparada_uma_vez(self, cenario: Cenario) -> None:
        cenario.sped([doc(1, vl_doc="1,00"), doc(1, vl_doc="1,00")]).xml(nfe(1))

        _, sink = cenario.rodar()

        assert sorted(a.kind for a in sink.findings) == [
            Kind.CHAVE_DUPLICADA,
            Kind.VALOR_DIVERGENTE,
        ]
        duplicada = sink.by_kind(Kind.CHAVE_DUPLICADA)[0]
        assert duplicada.detail["vezes"] == 2

    def test_chave_com_dv_invalido_no_sped(self, cenario: Cenario) -> None:
        errada = chave(1)[:-1] + str((int(chave(1)[-1]) + 1) % 10)
        item = DocSpec(number=1, key=errada)
        cenario.sped([item, doc(2)]).xml(nfe(2))

        _, sink = cenario.rodar()

        (achado,) = sink.findings
        assert achado.kind == Kind.CHAVE_INVALIDA
        assert achado.doc_key == errada

    def test_documento_sem_chave_e_contado_e_nao_conferido(self, cenario: Cenario) -> None:
        papel = DocSpec(number=5, cod_mod="01", key="", cod_part="FORN1")
        cenario.sped([papel, doc(1)]).xml(nfe(1))

        resultado, sink = cenario.rodar()

        assert sink.findings == []
        assert resultado.counts["sped_sem_chave"] == 1


class TestCte:
    def cte(self, **campos: Any) -> CteSpec:
        chave_cte = chave(4, model="57")
        return CteSpec(
            key=chave_cte, emit_cnpj=FORNECEDOR, tomador_cnpj=EMPRESA, number=4, **campos
        )

    def doc_d100(self, **campos: Any) -> DocSpec:
        return DocSpec(
            reg="D100",
            number=4,
            key=chave(4, model="57"),
            cod_mod="57",
            vl_doc="350,00",
            vl_icms="42,00",
            vl_serv="350,00",
            **campos,
        )

    def test_cte_confere(self, cenario: Cenario) -> None:
        cenario.sped([self.doc_d100()]).xml(self.cte(v_tprest="350.00", v_icms="42.00"))

        resultado, sink = cenario.rodar()

        assert sink.findings == []
        assert resultado.counts["conferem"] == 1

    def test_cte_com_valor_da_prestacao_diferente(self, cenario: Cenario) -> None:
        cenario.sped([self.doc_d100()]).xml(self.cte(v_tprest="360.00", v_icms="42.00"))

        _, sink = cenario.rodar()

        (achado,) = sink.findings
        assert achado.doc_type == "cte"
        assert (achado.field, achado.left_cents, achado.right_cents) == ("vnf", 35000, 36000)

    def test_cte_nao_acusa_ipi_que_ele_nao_tem(self, cenario: Cenario) -> None:
        cenario.sped([self.doc_d100()]).xml(self.cte(v_tprest="350.00", v_icms="42.00"))

        _, sink = cenario.rodar(regras=RuleSet(fields=("vnf", "vicms", "vipi")))

        assert sink.findings == []


class TestEntradasInvalidas:
    def test_sped_de_outra_empresa_e_recusado(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)], cnpj=OUTRA).xml(nfe(1))

        with pytest.raises(RunRejected) as erro:
            cenario.rodar()

        (problema,) = erro.value.problems
        assert problema.code == "empresa_diferente"
        assert format_cnpj(OUTRA) in problema.message

    def test_outro_estabelecimento_da_mesma_raiz_e_aviso(self, cenario: Cenario) -> None:
        filial = make_cnpj("12345678", "0002")
        cenario.sped([doc(1)], cnpj=filial).xml(nfe(1, dest_cnpj=filial))

        resultado, sink = cenario.rodar()

        assert sink.findings == []
        assert "outro_estabelecimento" in {w.code for w in resultado.warnings}

    def test_competencia_diferente_e_aviso(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)]).xml(nfe(1))

        resultado, _ = cenario.rodar(competencia="2026-08")

        assert "competencia_diferente" in {w.code for w in resultado.warnings}

    def test_sped_truncado_e_recusado(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)], omit_trailer=True).xml(nfe(1))

        with pytest.raises(RunRejected) as erro:
            cenario.rodar()

        assert [p.code for p in erro.value.problems] == ["sem_9999"]

    def test_arquivo_que_nao_e_efd(self, cenario: Cenario) -> None:
        cenario._gravar("lixo.txt", b"isto nao e SPED\r\n", "sped")
        cenario.xml(nfe(1))

        with pytest.raises(RunRejected) as erro:
            cenario.rodar()

        assert erro.value.problems[0].code == "sem_0000"

    def test_nenhum_xml_aproveitavel(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)]).xml(b"nao e xml", nfe(2, emit_cnpj=OUTRA, dest_cnpj=OUTRA))

        with pytest.raises(RunRejected) as erro:
            cenario.rodar()

        (problema,) = erro.value.problems
        assert problema.code == "sem_xml_util"

    def test_xml_ruim_nao_derruba_os_outros(self, cenario: Cenario) -> None:
        bomba = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><nfeProc>&a;</nfeProc>'
        homologacao = build_nfe_xml(nfe(8, tp_amb="2"))
        cenario.sped([doc(1)]).xml(nfe(1), bomba, b"<x", homologacao, b"<resNFe/>")

        resultado, sink = cenario.rodar()

        assert sink.findings == []
        assert resultado.ingest["invalidos"] == 2
        assert resultado.ingest["ignorados"] == 2
        assert resultado.ingest["nfe"] == 1
        assert resultado.ingest["ignorado_dtd_proibido"] == 1
        assert resultado.ingest["ignorado_homologacao"] == 1

    def test_xml_duplicado_vale_o_primeiro(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)]).xml(nfe(1), nfe(1))

        resultado, _ = cenario.rodar()

        assert resultado.ingest["duplicados"] == 1
        assert resultado.ingest["nfe"] == 1

    def test_zip_com_arquivo_que_nao_e_xml(self, cenario: Cenario) -> None:
        pacote = build_zip({"a.xml": build_nfe_xml(nfe(1)), "leia-me.txt": b"oi"})
        cenario.sped([doc(1)])
        cenario._gravar("lote.zip", pacote, "xml")

        resultado, sink = cenario.rodar()

        assert sink.findings == []
        assert resultado.ingest["nao_xml"] == 1

    def test_zip_invalido_e_recusado(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)])
        cenario._gravar("quebrado.zip", b"PK\x03\x04 isto esta quebrado", "xml")

        with pytest.raises(RunRejected) as erro:
            cenario.rodar()

        assert erro.value.problems[0].code.startswith("zip_")

    def test_teto_de_xml_por_conferencia(
        self, cenario: Cenario, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(runner, "MAX_XML_DOCUMENTS", 2)
        cenario.sped([doc(1)]).xml(nfe(1), nfe(2), nfe(3))

        with pytest.raises(RunRejected) as erro:
            cenario.rodar()

        assert erro.value.problems[0].code == "xml_demais"


class TestControle:
    def test_cancelar_interrompe_no_proximo_ponto_seguro(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)]).xml(nfe(1))
        sink = CollectingSink()
        sink.cancel = True

        with pytest.raises(RunCancelled):
            cenario.rodar(sink=sink)

    def test_o_andamento_e_informado(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)]).xml(nfe(1))

        _, sink = cenario.rodar()

        etapas = [etapa for etapa, _, _ in sink.progress_log]
        assert etapas[0] == "Preparando"
        assert "Comparando" in etapas

    def test_o_resultado_traz_as_regras_usadas(self, cenario: Cenario) -> None:
        cenario.sped([doc(1)]).xml(nfe(1))

        resultado, _ = cenario.rodar(regras=RuleSet(tolerance_cents=3, operation="A"))

        assert resultado.rules["tolerance_cents"] == 3
        assert resultado.rules["operation"] == "A"
        assert RuleSet.from_snapshot(resultado.rules) == RuleSet(tolerance_cents=3, operation="A")

    def test_relatorio_dos_arquivos(self, cenario: Cenario) -> None:
        cenario.sped([doc(1), doc(2, analytics=[])]).xml(nfe(1))

        resultado, _ = cenario.rodar()

        sped = next(f for f in resultado.files if f.kind == "efd")
        assert sped.details["cnpj"] == EMPRESA
        assert sped.details["competencia"] == "2026-09"
        assert sped.details["c100"] == 2
        assert sped.details["c190"] == 1
        assert sped.details["finalidade"] == "original"
        xml = next(f for f in resultado.files if f.kind == "xml")
        assert xml.details["nfe"] == 1


class TestSpedSped:
    def regras(self, **campos: Any) -> RuleSet:
        base: dict[str, Any] = {"operation": "A", "fields": DEFAULT_SPED_SPED_FIELDS}
        return RuleSet(**{**base, **campos})

    def rodar(self, cenario: Cenario, um: list[DocSpec], dois: list[DocSpec], **campos: Any) -> Any:
        cenario.sped(um, papel="sped1").sped(dois, papel="sped2")
        return cenario.rodar("sped_sped", self.regras(**campos))

    def test_documentos_so_em_um_dos_arquivos(self, cenario: Cenario) -> None:
        _, sink = self.rodar(cenario, [doc(1), doc(2)], [doc(2), doc(3)])

        por_tipo = {a.kind: a.number for a in sink.findings}
        assert por_tipo == {Kind.SOMENTE_1: "1", Kind.SOMENTE_2: "3"}

    def test_campo_do_documento_diferente(self, cenario: Cenario) -> None:
        resultado, sink = self.rodar(cenario, [doc(1, vl_icms="18,00")], [doc(1, vl_icms="17,50")])

        (achado,) = sink.findings
        assert achado.kind == Kind.VALOR_DIVERGENTE
        assert (achado.field, achado.left_cents, achado.right_cents) == ("vl_icms", 1800, 1750)
        assert resultado.counts["divergentes_docs"] == 1

    def test_arquivos_iguais_nao_geram_achado(self, cenario: Cenario) -> None:
        resultado, sink = self.rodar(cenario, [doc(1), doc(2)], [doc(1), doc(2)])

        assert sink.findings == []
        assert resultado.counts["conferem"] == 2

    def test_situacao_diferente_e_comparada_como_texto(self, cenario: Cenario) -> None:
        _, sink = self.rodar(cenario, [doc(1)], [doc(1, cod_sit="02")])

        textos = [(a.field, a.left_text, a.right_text) for a in sink.findings if a.left_text]
        assert ("cod_sit", "00", "02") in textos

    def test_analitico_so_em_um_dos_lados_e_valor_diferente(self, cenario: Cenario) -> None:
        um = doc(1, analytics=[AnalyticSpec(cfop="1102", vl_icms="18,00")])
        dois = doc(
            1,
            analytics=[
                AnalyticSpec(cfop="1102", vl_icms="17,00"),
                AnalyticSpec(cfop="1403", aliq="12,00"),
            ],
        )

        _, sink = self.rodar(cenario, [um], [dois])

        tipos = {a.kind for a in sink.findings}
        assert tipos == {Kind.ANALITICO_VALOR, Kind.ANALITICO_SOMENTE_2}
        valor = sink.by_kind(Kind.ANALITICO_VALOR)[0]
        assert (valor.left_cents, valor.right_cents) == (1800, 1700)
        assert "CST 000 · CFOP 1102 · 18,00%" in valor.field_label

    def test_analitico_pode_ser_desligado(self, cenario: Cenario) -> None:
        um = doc(1, analytics=[AnalyticSpec(cfop="1102")])
        dois = doc(1, analytics=[AnalyticSpec(cfop="2102")])

        _, sink = self.rodar(cenario, [um], [dois], include_analytic=False)

        assert sink.findings == []

    def test_sem_bloco_d_nos_dois_arquivos_nao_quebra(self, cenario: Cenario) -> None:
        """Regressão: o Cruzamento Speds quebrava (KeyError/UnboundLocalError) sem bloco D."""

        resultado, sink = self.rodar(cenario, [doc(1)], [doc(1)])

        assert sink.findings == []
        assert resultado.counts["nos_dois"] == 1

    def test_arquivo_sem_documento_nenhum(self, cenario: Cenario) -> None:
        _, sink = self.rodar(cenario, [], [doc(1)])

        assert [a.kind for a in sink.findings] == [Kind.SOMENTE_2]

    def test_d100_tambem_e_comparado(self, cenario: Cenario) -> None:
        def d100(valor: str) -> DocSpec:
            return DocSpec(reg="D100", number=4, key=chave(4, model="57"), cod_mod="57",
                           vl_doc=valor, vl_serv=valor)  # fmt: skip

        _, sink = self.rodar(cenario, [d100("350,00")], [d100("360,00")])

        campos = sorted(a.field for a in sink.findings)
        assert campos == ["vl_doc", "vl_serv"]

    def test_documento_sem_chave_liga_pelo_que_o_identifica(self, cenario: Cenario) -> None:
        papel1 = DocSpec(number=5, cod_mod="01", key="", cod_part="F1", vl_doc="10,00")
        papel2 = DocSpec(number=5, cod_mod="01", key="", cod_part="F1", vl_doc="12,00")

        _, sink = self.rodar(cenario, [papel1], [papel2])

        (achado,) = sink.findings
        assert achado.kind == Kind.VALOR_DIVERGENTE
        assert achado.doc_key.startswith("C100:")

    def test_tolerancia_em_centavos(self, cenario: Cenario) -> None:
        _, sink = self.rodar(
            cenario, [doc(1, vl_doc="100,01")], [doc(1, vl_doc="100,00")], tolerance_cents=0
        )

        assert [a.field for a in sink.findings] == ["vl_doc"]

    def test_chave_duplicada_em_um_dos_arquivos(self, cenario: Cenario) -> None:
        _, sink = self.rodar(cenario, [doc(1), doc(1)], [doc(1)])

        duplicadas = sink.by_kind(Kind.CHAVE_DUPLICADA)
        assert len(duplicadas) == 1
        assert duplicadas[0].detail["arquivo"] == 1


class TestIcms51:
    def xml51(self, numero: int, **item: Any) -> NfeSpec:
        padrao = {
            "cfop": "5101",
            "group": "ICMS51",
            "v_bc": "1000.00",
            "p_icms": "18.0000",
            "v_icms_op": "180.00",
            "p_dif": "50.0000",
            "v_icms_dif": "90.00",
            "v_icms": "90.00",
        }
        return nfe(numero, items=[ItemSpec(**{**padrao, **item})])

    def doc_cfop(self, numero: int, cfop: str, **campos: Any) -> DocSpec:
        return doc(numero, analytics=[AnalyticSpec(cfop=cfop, vl_icms="0,00")], **campos)

    def test_lista_a_chave_com_os_valores_do_grupo(self, cenario: Cenario) -> None:
        cenario.sped([self.doc_cfop(1, "1556")]).xml(self.xml51(1))

        resultado, sink = cenario.rodar("icms51")

        (achado,) = sink.findings
        assert achado.kind == Kind.ICMS51_CHAVE
        assert achado.cfop == "1556"
        (item,) = achado.detail["itens"]
        assert (item["v_icms_op"], item["p_dif"], item["v_icms_dif"], item["v_icms"]) == (
            18000, 500000, 9000, 9000,
        )  # fmt: skip
        assert resultado.counts["com_icms51"] == 1

    def test_aritmetica_errada_vira_inconsistencia(self, cenario: Cenario) -> None:
        cenario.sped([self.doc_cfop(1, "1551")]).xml(self.xml51(1, v_icms="80.00"))

        _, sink = cenario.rodar("icms51")

        assert sorted(a.kind for a in sink.findings) == [Kind.ICMS51_ARITMETICA, Kind.ICMS51_CHAVE]
        inconsistencia = sink.by_kind(Kind.ICMS51_ARITMETICA)[0]
        assert (inconsistencia.left_cents, inconsistencia.right_cents) == (9000, 8000)

    def test_xml_sem_icms51_nao_e_listado(self, cenario: Cenario) -> None:
        cenario.sped([self.doc_cfop(1, "1556")]).xml(nfe(1))

        resultado, sink = cenario.rodar("icms51")

        assert sink.findings == []
        assert resultado.counts["sem_icms51"] == 1

    def test_so_considera_os_cfop_configurados(self, cenario: Cenario) -> None:
        cenario.sped([self.doc_cfop(1, "1102")]).xml(self.xml51(1))

        _, padrao = cenario.rodar("icms51")
        (cenario.raiz / "trabalho" / "stage.sqlite3").unlink()
        _, com_cfop = cenario.rodar("icms51", RuleSet(icms51_cfops=frozenset({"1102"})))

        assert padrao.findings == []
        assert [a.kind for a in com_cfop.findings] == [Kind.ICMS51_CHAVE]

    def test_icms51_so_na_nota_que_o_sped_escriturou(self, cenario: Cenario) -> None:
        cenario.sped([self.doc_cfop(1, "1556")]).xml(self.xml51(1), self.xml51(2))

        _, sink = cenario.rodar("icms51")

        assert [a.number for a in sink.findings] == ["1"]

    def test_escriturado_sem_xml_nao_da_para_conferir(self, cenario: Cenario) -> None:
        cenario.sped([self.doc_cfop(1, "1556"), self.doc_cfop(2, "1551")]).xml(self.xml51(1))

        _, sink = cenario.rodar("icms51")

        assert [(a.kind, a.number) for a in sink.findings] == [
            (Kind.ICMS51_CHAVE, "1"),
            (Kind.SEM_XML, "2"),
        ]

    def test_documento_cancelado_nao_entra(self, cenario: Cenario) -> None:
        cenario.sped([self.doc_cfop(1, "1556", cod_sit="02")]).xml(self.xml51(1))

        _, sink = cenario.rodar("icms51")

        assert sink.findings == []


class TestUfDominio:
    def linha(self, numero: int, direcao: str, uf: str, *, emit: str = FORNECEDOR) -> DominioRow:
        return DominioRow(chave(numero, emit=emit), direcao, uf)

    def saida(self, numero: int, uf: str = "SP", **campos: Any) -> NfeSpec:
        return nfe(numero, emit_cnpj=EMPRESA, dest_cnpj=FORNECEDOR, dest_uf=uf, **campos)

    def test_saida_usa_a_uf_do_destinatario(self, cenario: Cenario) -> None:
        cenario.xml(self.saida(1, "SP"), self.saida(2, "RJ"))
        dominio = [self.linha(1, "S", "SP", emit=EMPRESA), self.linha(2, "S", "MG", emit=EMPRESA)]

        resultado, sink = cenario.rodar("uf_dominio", dominio=dominio)

        (achado,) = sink.findings
        assert achado.kind == Kind.UF_DIVERGENTE
        assert (achado.number, achado.left_text, achado.right_text) == ("2", "RJ", "MG")
        assert resultado.counts["conferem"] == 1

    def test_entrada_usa_a_uf_do_emitente_e_nao_a_do_destinatario(self, cenario: Cenario) -> None:
        """Regressão: o legado comparava a UF do destinatário (a nossa) com a do fornecedor."""

        entrada = nfe(1, emit_uf="MG", dest_uf="SP")
        cenario.xml(entrada)

        resultado, sink = cenario.rodar("uf_dominio", dominio=[self.linha(1, "E", "MG")])

        assert sink.findings == []
        assert resultado.counts["conferem"] == 1

    def test_chave_que_o_dominio_nao_tem_nao_e_uf_diferente(self, cenario: Cenario) -> None:
        cenario.xml(self.saida(1), self.saida(2))

        _, sink = cenario.rodar("uf_dominio", dominio=[self.linha(1, "S", "SP", emit=EMPRESA)])

        (achado,) = sink.findings
        assert achado.kind == Kind.AUSENTE_DOMINIO
        assert achado.number == "2"

    def test_xml_sem_uf_da_contraparte_tem_categoria_propria(self, cenario: Cenario) -> None:
        cenario.xml(self.saida(1, ""))

        resultado, sink = cenario.rodar(
            "uf_dominio", dominio=[self.linha(1, "S", "SP", emit=EMPRESA)]
        )

        (achado,) = sink.findings
        assert achado.kind == Kind.SEM_UF_XML
        assert achado.status == "info"
        assert resultado.counts["sem_uf"] == 1

    def test_chave_nas_duas_direcoes_vale_a_da_mesma_direcao(self, cenario: Cenario) -> None:
        cenario.xml(self.saida(1, "SP"))
        dominio = [
            self.linha(1, "E", "MG", emit=EMPRESA),
            self.linha(1, "S", "SP", emit=EMPRESA),
        ]

        _, sink = cenario.rodar("uf_dominio", dominio=dominio)

        assert sink.findings == []

    def test_xml_de_outra_empresa_nao_entra(self, cenario: Cenario) -> None:
        alheio = nfe(9, emit_cnpj=OUTRA, dest_cnpj=make_cnpj("77777777", "0001"))
        cenario.xml(self.saida(1), alheio)

        resultado, sink = cenario.rodar(
            "uf_dominio", dominio=[self.linha(1, "S", "SP", emit=EMPRESA)]
        )

        assert sink.findings == []
        assert resultado.ingest["outra_empresa"] == 1

    def test_dominio_vazio_e_recusado(self, cenario: Cenario) -> None:
        cenario.xml(self.saida(1))

        with pytest.raises(RunRejected) as erro:
            cenario.rodar("uf_dominio", dominio=[])

        assert erro.value.problems[0].code == "dominio_vazio"

    def test_sem_fonte_do_dominio(self, cenario: Cenario) -> None:
        cenario.xml(self.saida(1))

        with pytest.raises(RunRejected) as erro:
            cenario.rodar("uf_dominio")

        assert erro.value.problems[0].code == "sem_dominio"

    def test_dominio_por_arquivo_csv(self, cenario: Cenario) -> None:
        cenario.xml(self.saida(1, "SP"), self.saida(2, "RJ"))
        csv = (
            "chave;uf;direcao\n"
            f"{chave(1, emit=EMPRESA)};SP;saida\n"
            f"{chave(2, emit=EMPRESA)};MG;S\n"
            "lixo;SP;S\n"
        )
        cenario._gravar("dominio.csv", csv.encode("latin-1"), "dominio")

        resultado, sink = cenario.rodar("uf_dominio")

        assert [(a.kind, a.number) for a in sink.findings] == [(Kind.UF_DIVERGENTE, "2")]
        assert any(w.code == "dominio_linha" for w in resultado.warnings)
        dominio = next(f for f in resultado.files if f.kind == "dominio")
        assert dominio.details == {"linhas": 3, "validas": 2}
