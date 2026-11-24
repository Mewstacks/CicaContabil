"""Regras (D-301) e catálogo das quatro ferramentas do Contraprova."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

from apps.crosscheck.engine import rules, stage
from apps.crosscheck.engine.efd import DOCUMENT_MONEY_FIELDS
from apps.crosscheck.engine.findings import Kind
from apps.crosscheck.engine.rules import (
    DEFAULT_NO_CREDIT_CFOPS,
    RuleSet,
    build_rules,
    describe,
    parse_cfop_list,
)
from apps.crosscheck.engine.tools import ICMS51, SPED_SPED, SPED_XML, TOOLS, UF_DOMINIO


class TestPadroesDeD301:
    def test_valores_padrao(self) -> None:
        padrao = RuleSet()

        assert padrao.tolerance_cents == 1
        assert padrao.operation == "E"
        assert padrao.fields == ("vnf", "vicms", "vipi")
        assert padrao.no_credit_cfops == frozenset(
            {"1406", "1407", "1551", "1556", "2406", "2407", "2551", "2556"}
        )
        assert padrao.icms51_cfops == frozenset({"1551", "1556"})
        assert padrao.no_credit_cfops == DEFAULT_NO_CREDIT_CFOPS

    def test_o_valor_do_documento_nunca_e_credito(self) -> None:
        assert "vnf" not in rules.CREDIT_RELATED
        assert {"vicms", "vipi"} <= rules.CREDIT_RELATED

    @pytest.mark.parametrize(
        ("operacao", "sped", "xml"),
        [
            ("E", ("0", "0"), ("E", "E")),
            ("S", ("1", "1"), ("S", "S")),
            ("A", ("0", "1"), ("E", "S")),
        ],
    )
    def test_filtros_de_operacao(
        self, operacao: str, sped: tuple[str, str], xml: tuple[str, str]
    ) -> None:
        regras = RuleSet(operation=operacao)

        assert regras.operation_filter() == sped
        assert regras.direction_filter() == xml


class TestSnapshot:
    def test_ida_e_volta(self) -> None:
        original = RuleSet(
            tolerance_cents=5,
            operation="A",
            fields=("vnf", "vprod"),
            no_credit_cfops=frozenset({"1102"}),
            icms51_cfops=frozenset({"2556"}),
            include_analytic=False,
        )

        assert RuleSet.from_snapshot(original.snapshot()) == original

    def test_snapshot_e_json_puro(self) -> None:
        import json

        assert json.loads(json.dumps(RuleSet().snapshot())) == RuleSet().snapshot()

    def test_snapshot_incompleto_usa_os_padroes(self) -> None:
        assert RuleSet.from_snapshot({"tolerance_cents": 3}) == RuleSet(tolerance_cents=3)


class TestFormulario:
    def test_sem_nada_vale_o_padrao_da_ferramenta(self) -> None:
        regras, erros = build_rules({})
        assert (regras, erros) == (RuleSet(), [])

        sped_sped, erros = build_rules({}, tool=SPED_SPED)
        assert erros == []
        assert sped_sped.operation == "A"
        assert sped_sped.fields == rules.DEFAULT_SPED_SPED_FIELDS

    def test_valores_validos(self) -> None:
        regras, erros = build_rules(
            {
                "tolerance_cents": "2",
                "operation": "a",
                "fields": ["vnf", "vicms"],
                "no_credit_cfops": "1556, 1551;2556\n1406",
                "icms51_cfops": ["1551", "2551"],
            }
        )

        assert erros == []
        assert regras.tolerance_cents == 2
        assert regras.operation == "A"
        assert regras.fields == ("vnf", "vicms")
        assert regras.no_credit_cfops == frozenset({"1556", "1551", "2556", "1406"})
        assert regras.icms51_cfops == frozenset({"1551", "2551"})

    @pytest.mark.parametrize(
        ("dados", "trecho"),
        [
            ({"tolerance_cents": "abc"}, "Tolerância inválida"),
            ({"tolerance_cents": "-1"}, "fora do limite"),
            ({"tolerance_cents": "100000"}, "fora do limite"),
            ({"operation": "Z"}, "Operação inválida"),
            ({"fields": ["vnf", "inexistente"]}, "Campo desconhecido"),
            ({"fields": []}, "ao menos um campo"),
            ({"no_credit_cfops": "55"}, "CFOP inválido"),
            ({"icms51_cfops": "abcd"}, "CFOP inválido"),
            ({"icms51_cfops": ""}, "ao menos um CFOP"),
        ],
    )
    def test_erros_em_portugues_e_valor_seguro(self, dados: dict[str, object], trecho: str) -> None:
        regras, erros = build_rules(dados)

        assert any(trecho in erro for erro in erros), erros
        assert regras.tolerance_cents <= rules.MAX_TOLERANCE_CENTS

    def test_campos_de_sped_sped_sao_outros(self) -> None:
        _, erros = build_rules({"fields": ["vl_doc", "cod_sit"]}, tool=SPED_SPED)
        assert erros == []

        _, erros = build_rules({"fields": ["vl_doc"]}, tool=SPED_XML)
        assert erros

    def test_lista_de_cfop(self) -> None:
        assert parse_cfop_list(" 1551 ,1556;1551\n") == (frozenset({"1551", "1556"}), [])
        valores, erros = parse_cfop_list("1551 x 15")
        assert valores == frozenset({"1551"})
        assert len(erros) == 2

    def test_descricao_para_o_relatorio(self) -> None:
        linhas = describe(RuleSet(), SPED_XML)
        rotulos = {linha.label: linha.value for linha in linhas}

        assert rotulos["Tolerância"] == "1 centavo(s)"
        assert rotulos["Operação"] == "Entradas"
        assert "1556" in rotulos["CFOP sem crédito"]
        assert "Valor do documento" in rotulos["Campos"]
        assert {linha.label for linha in describe(RuleSet(), ICMS51)} >= {"CFOP do ICMS 51"}
        assert "Analítico" in {linha.label for linha in describe(RuleSet(), SPED_SPED)}
        assert describe(RuleSet(), UF_DOMINIO)[0].label == "Tolerância"


class TestCatalogoDeFerramentas:
    def test_quatro_ferramentas_com_nomes_do_legado(self) -> None:
        assert list(TOOLS) == [SPED_XML, SPED_SPED, ICMS51, UF_DOMINIO]
        assert [t.label for t in TOOLS.values()] == [
            "SPED x XML",
            "SPED x SPED",
            "ICMS 51",
            "UF x Domínio",
        ]

    def test_todo_tipo_de_achado_tem_aba_na_ferramenta_que_o_produz(self) -> None:
        produzidos = {
            SPED_XML: {
                Kind.VALOR_DIVERGENTE, Kind.SEM_XML, Kind.XML_NAO_ESCRITURADO,
                Kind.SITUACAO_DIVERGENTE, Kind.CHAVE_DUPLICADA, Kind.CHAVE_INVALIDA,
            },
            SPED_SPED: {
                Kind.VALOR_DIVERGENTE, Kind.SOMENTE_1, Kind.SOMENTE_2, Kind.ANALITICO_VALOR,
                Kind.ANALITICO_SOMENTE_1, Kind.ANALITICO_SOMENTE_2, Kind.CHAVE_DUPLICADA,
                Kind.CHAVE_INVALIDA,
            },
            ICMS51: {Kind.ICMS51_CHAVE, Kind.ICMS51_ARITMETICA, Kind.SEM_XML},
            UF_DOMINIO: {Kind.UF_DIVERGENTE, Kind.AUSENTE_DOMINIO, Kind.SEM_UF_XML},
        }  # fmt: skip
        for codigo, tipos in produzidos.items():
            abas = {tipo for aba in TOOLS[codigo].tabs for tipo in aba.kinds}
            assert tipos <= abas, f"{codigo}: sem aba para {tipos - abas}"

    def test_papeis_e_abas_tem_codigos_unicos(self) -> None:
        for ferramenta in TOOLS.values():
            papeis = [p.code for p in ferramenta.roles]
            abas = [a.code for a in ferramenta.tabs]
            assert len(set(papeis)) == len(papeis)
            assert len(set(abas)) == len(abas)
            assert len({a.label for a in ferramenta.tabs}) == len(ferramenta.tabs)

    def test_busca_de_papel_e_aba(self) -> None:
        sped_xml = TOOLS[SPED_XML]

        assert sped_xml.role("xml").kind == "xml"
        assert sped_xml.tab("ignoradas").statuses == ("ignored",)
        assert sped_xml.tab("inexistente") is sped_xml.tabs[0]
        with pytest.raises(KeyError):
            sped_xml.role("nao-existe")

    def test_ferramentas_com_sped_pedem_arquivo_efd(self) -> None:
        for ferramenta in TOOLS.values():
            tem_efd = any(papel.kind == "efd" for papel in ferramenta.roles)
            assert tem_efd is ferramenta.uses_sped

    def test_rotulos_curtos_sem_frase(self) -> None:
        for ferramenta in TOOLS.values():
            for aba in ferramenta.tabs:
                assert len(aba.label.split()) <= 4
                assert not aba.label.endswith(".")


class TestPreparo:
    def test_colunas_do_sql_cobrem_todos_os_valores_do_leiaute(self, tmp_path: Path) -> None:
        """Se o leitor ganhar um campo de valor e o preparo não, o valor sumiria em silêncio."""

        with stage.Stage(tmp_path) as preparo:
            colunas = {
                linha["name"] for linha in preparo.conn.execute("PRAGMA table_info(sped_doc)")
            }
        assert set(DOCUMENT_MONEY_FIELDS) <= colunas

        texto = re.sub(r"\s+", " ", stage._INSERT_SPED_DOC)
        for campo in DOCUMENT_MONEY_FIELDS:
            assert f":{campo}" in texto

    def test_o_preparo_vive_em_disco(self, tmp_path: Path) -> None:
        with stage.Stage(tmp_path) as preparo:
            preparo.finish_loading()
            assert (tmp_path / "stage.sqlite3").exists()
            assert isinstance(preparo.conn, sqlite3.Connection)
