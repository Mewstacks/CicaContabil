"""Relatórios (XLSX/CSV/TXT) e leitura do arquivo do Domínio do Contraprova."""

from __future__ import annotations

import csv
import io

import pytest
from openpyxl import Workbook, load_workbook

from apps.crosscheck.engine import dominio_file, report
from apps.crosscheck.engine.dominio_file import (
    DominioFileError,
    DominioReport,
    iter_dominio_rows,
)
from apps.crosscheck.engine.findings import Finding, Kind, MatchedRow
from apps.crosscheck.engine.rules import RuleLine
from apps.crosscheck.engine.tools import SPED_XML, TOOLS, UF_DOMINIO
from apps.crosscheck.synthetic import make_cnpj, make_key

CHAVE = make_key(cnpj=make_cnpj("98765432", "0001"), number=1)
CHAVE_2 = make_key(cnpj=make_cnpj("98765432", "0001"), number=2)


def achado(**campos: object) -> Finding:
    base: dict[str, object] = {
        "kind": Kind.VALOR_DIVERGENTE,
        "status": "divergent",
        "doc_key": CHAVE,
        "doc_type": "nfe",
        "number": "1",
        "field": "vnf",
        "field_label": "Valor do documento",
        "left_cents": 15000,
        "right_cents": 10000,
        "cfop": "1102",
        "operation": "E",
        "message": "Valor do documento: SPED 150,00 · XML 100,00",
    }
    return Finding(**{**base, **campos})  # type: ignore[arg-type]


class TestTextoSeguro:
    @pytest.mark.parametrize("texto", ["=1+1", "+cmd", "-cmd", "@SUM(A1)", "\tx", "\rx"])
    def test_texto_que_o_excel_executaria_ganha_apostrofo(self, texto: str) -> None:
        assert report.safe_text(texto) == "'" + texto

    @pytest.mark.parametrize("texto", ["normal", "", "1+1", "a=b"])
    def test_texto_comum_passa_igual(self, texto: str) -> None:
        assert report.safe_text(texto) == texto

    def test_none_vira_vazio(self) -> None:
        assert report.safe_text(None) == ""


class TestCsv:
    def test_cabecalho_usa_os_rotulos_da_ferramenta(self) -> None:
        saida = io.StringIO()
        report.write_csv(saida, TOOLS[SPED_XML], [achado()])

        linhas = list(csv.reader(io.StringIO(saida.getvalue()), delimiter=";"))

        assert linhas[0][:8] == [
            "Chave", "Número", "Tipo", "Operação", "Campo", "SPED", "XML", "Diferença",
        ]  # fmt: skip
        assert linhas[1][0] == CHAVE
        assert linhas[1][5:8] == ["150.00", "100.00", "50.00"]
        assert linhas[1][9] == "Divergente"

    def test_formula_em_campo_de_terceiro_e_neutralizada(self) -> None:
        saida = io.StringIO()
        perigoso = achado(doc_key='=HYPERLINK("http://x")', message="+cmd|' /C calc'!A0")

        report.write_csv(saida, TOOLS[SPED_XML], [perigoso])

        linha = list(csv.reader(io.StringIO(saida.getvalue()), delimiter=";"))[1]
        assert linha[0].startswith("'=")
        assert linha[10].startswith("'+")

    def test_texto_de_uf_aparece_no_lugar_do_valor(self) -> None:
        saida = io.StringIO()
        uf = achado(
            kind=Kind.UF_DIVERGENTE,
            left_cents=None,
            right_cents=None,
            left_text="SP",
            right_text="MG",
            field_label="UF",
        )

        report.write_csv(saida, TOOLS[UF_DOMINIO], [uf])

        linha = list(csv.reader(io.StringIO(saida.getvalue()), delimiter=";"))[1]
        assert linha[5:8] == ["SP", "MG", ""]


class TestTxt:
    def test_um_bloco_por_achado(self) -> None:
        texto, total = report.render_txt(TOOLS[SPED_XML], [achado(), achado(number="2")])

        assert total == 2
        assert texto.count("NF-e - ") == 2
        assert "Número: 1" in texto
        assert "CFOP: 1102" in texto

    def test_respeita_o_limite_mas_conta_tudo(self) -> None:
        texto, total = report.render_txt(TOOLS[SPED_XML], [achado() for _ in range(10)], limit=3)

        assert total == 10
        assert texto.count("NF-e - ") == 3


def abrir(dados: bytes):  # type: ignore[no-untyped-def]
    return load_workbook(io.BytesIO(dados), read_only=True)


class TestXlsx:
    def montar(self, achados: list[Finding], conferiu: list[MatchedRow] | None = None) -> bytes:
        relatorio = report.XlsxReport(TOOLS[SPED_XML], "SPED x XML · Empresa Teste · 09/2026")
        for item in achados:
            relatorio.finding(item)
        for linha in conferiu or []:
            relatorio.matched(linha)
        saida = io.BytesIO()
        relatorio.finish(
            saida,
            facts={"Empresa": "Empresa Teste", "Competência": "09/2026"},
            rules=[RuleLine("Tolerância", "1 centavo(s)", "inclusiva")],
            files=[("sped.txt", "EFD · 09/2026")],
            counts={"conferem": 1, "divergentes": 2},
        )
        return saida.getvalue()

    def test_folhas_e_linhas_por_aba(self) -> None:
        achados = [
            achado(),
            achado(number="2", status="ignored", field="vicms", field_label="ICMS"),
            achado(kind=Kind.SEM_XML, number="3", right_cents=None),
            achado(kind=Kind.XML_NAO_ESCRITURADO, number="4", left_cents=None),
        ]
        conferiu = [
            MatchedRow(
                CHAVE_2, "nfe", "5", "E", "1102", {"vnf": (10000, 10000), "vicms": (1800, 1800)}
            )
        ]

        pasta = abrir(self.montar(achados, conferiu))

        assert pasta.sheetnames == [
            "Resumo", "Divergências", "Só no SPED", "Só no XML", "Ignoradas", "Conferem",
        ]  # fmt: skip

        def linhas(nome: str) -> list[tuple[object, ...]]:
            return list(pasta[nome].iter_rows(values_only=True))

        divergencias = linhas("Divergências")
        assert divergencias[0][:8] == (
            "Chave", "Número", "Tipo", "Operação", "Campo", "SPED", "XML", "Diferença",
        )  # fmt: skip
        assert divergencias[1][5:8] == (150.0, 100.0, 50.0)
        assert len(divergencias) == 2
        assert [r[1] for r in linhas("Só no SPED")[1:]] == ["3"]
        assert [r[1] for r in linhas("Só no XML")[1:]] == ["4"]
        ignoradas = linhas("Ignoradas")
        assert [r[1] for r in ignoradas[1:]] == ["2"]
        assert ignoradas[1][9] == "Ignorada por regra"
        conferem = linhas("Conferem")
        assert [(r[1], r[5], r[6]) for r in conferem[1:]] == [
            ("5", "Valor do documento", 100.0),
            ("5", "ICMS", 18.0),
        ]

    def test_resumo_traz_regras_arquivos_e_contagens(self) -> None:
        pasta = abrir(self.montar([achado()]))

        resumo = [tuple(r[:2]) for r in pasta["Resumo"].iter_rows(values_only=True)]

        assert ("SPED x XML · Empresa Teste · 09/2026",) in resumo
        assert ("Empresa", "Empresa Teste") in resumo
        assert ("Tolerância", "1 centavo(s) (inclusiva)") in resumo
        assert ("sped.txt", "EFD · 09/2026") in resumo
        assert ("divergentes", 2) in resumo

    def test_formula_vinda_de_arquivo_de_terceiro_e_neutralizada(self) -> None:
        perigoso = achado(doc_key="=cmd|'/c calc'!A1", message="@SUM(1+1)")

        pasta = abrir(self.montar([perigoso]))

        linha = list(pasta["Divergências"].iter_rows(values_only=True))[1]
        assert linha[0] == "'=cmd|'/c calc'!A1"
        assert linha[10] == "'@SUM(1+1)"

    def test_folha_cheia_conta_o_que_ficou_de_fora(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(report, "XLSX_MAX_ROWS", 3)

        pasta = abrir(self.montar([achado(number=str(n)) for n in range(1, 6)]))

        divergencias = list(pasta["Divergências"].iter_rows(values_only=True))
        assert len(divergencias) == 3
        resumo = [tuple(r[:2]) for r in pasta["Resumo"].iter_rows(values_only=True)]
        assert ("Linhas além do limite da folha Divergências", 3) in resumo

    def test_conferem_sem_valores_tambem_vira_linha(self) -> None:
        pasta = abrir(self.montar([], [MatchedRow(CHAVE, "nfe", "9", "S", "", {})]))

        linhas = list(pasta["Conferem"].iter_rows(values_only=True))
        assert linhas[1][:4] == (CHAVE, "9", "NF-e", "Saída")


def planilha(linhas: list[list[object]]) -> io.BytesIO:
    pasta = Workbook()
    folha = pasta.active
    for linha in linhas:
        folha.append(linha)
    saida = io.BytesIO()
    pasta.save(saida)
    saida.seek(0)
    return saida


def ler(
    dados: bytes | io.BytesIO, nome: str
) -> tuple[list[dominio_file.DominioRow], DominioReport]:
    fluxo = io.BytesIO(dados) if isinstance(dados, bytes) else dados
    relatorio = DominioReport()
    return list(iter_dominio_rows(fluxo, nome, relatorio)), relatorio


class TestArquivoDoDominio:
    def test_csv_com_cabecalho_e_direcao_por_extenso(self) -> None:
        csv_texto = f"Chave NFe;UF;Direção\n{CHAVE};sp;Saída\n{CHAVE_2};MG;entrada\n"

        linhas, relatorio = ler(csv_texto.encode("utf-8"), "dominio.csv")

        assert [(item.key, item.uf, item.direcao) for item in linhas] == [
            (CHAVE, "SP", "S"),
            (CHAVE_2, "MG", "E"),
        ]
        assert relatorio.rows_valid == 2
        assert relatorio.issues == []

    @pytest.mark.parametrize("separador", [";", ",", "\t"])
    def test_separador_e_detectado(self, separador: str) -> None:
        texto = separador.join(["chave", "uf"]) + "\n" + separador.join([CHAVE, "SP"]) + "\n"

        linhas, _ = ler(texto.encode(), "d.csv")

        assert [(item.key, item.uf, item.direcao) for item in linhas] == [(CHAVE, "SP", "")]

    def test_latin1_e_bom(self) -> None:
        texto = f"chave;uf;direcao\n{CHAVE};SP;S\n"

        com_bom, _ = ler(b"\xef\xbb\xbf" + texto.encode("utf-8"), "d.csv")
        latin, _ = ler(texto.replace("direcao", "direção").encode("latin-1"), "d.csv")

        assert len(com_bom) == len(latin) == 1

    def test_sem_cabecalho_vale_a_ordem_chave_uf_direcao(self) -> None:
        linhas, _ = ler(f"{CHAVE};RJ;E\n".encode(), "d.csv")

        assert [(item.uf, item.direcao) for item in linhas] == [("RJ", "E")]

    def test_nomes_do_domínio_para_as_colunas(self) -> None:
        texto = f"chave_nfe_sai;sigl_est\n{CHAVE};SP\n"

        # `chave_nfe_sai` não é um nome aceito: sem cabeçalho reconhecido, vale a ordem.
        linhas, _ = ler(texto.encode(), "d.csv")

        assert len(linhas) == 1

    def test_linhas_ruins_viram_aviso_e_nao_somem_em_silencio(self) -> None:
        texto = f"chave;uf;direcao\n{CHAVE};SP;S\n123;SP;S\n{CHAVE_2};ZZ;S\n{CHAVE_2};MG;X\n"

        linhas, relatorio = ler(texto.encode(), "d.csv")

        assert len(linhas) == 1
        assert relatorio.rows_read == 4
        assert relatorio.rows_valid == 1
        assert len(relatorio.issues) == 3
        assert "44" in relatorio.issues[0]
        assert "UF" in relatorio.issues[1]
        assert "direção" in relatorio.issues[2]

    def test_avisos_tem_teto(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(dominio_file, "MAX_ISSUES", 2)
        texto = "chave;uf\n" + "".join(f"{n};SP\n" for n in range(5))

        _, relatorio = ler(texto.encode(), "d.csv")

        assert len(relatorio.issues) == 2
        assert relatorio.issue_overflow == 3

    def test_xlsx(self) -> None:
        arquivo = planilha(
            [
                ["Chave", "UF", "Direção"],
                [CHAVE, "sp", "S"],
                [None, None, None],
                [CHAVE_2, "MG", None],
            ]
        )

        linhas, relatorio = ler(arquivo, "dominio.xlsx")

        assert [(item.key, item.uf, item.direcao) for item in linhas] == [
            (CHAVE, "SP", "S"),
            (CHAVE_2, "MG", ""),
        ]
        assert relatorio.issues == []

    def test_xlsx_invalido(self) -> None:
        with pytest.raises(DominioFileError):
            ler(b"isto nao e uma planilha", "dominio.xlsx")

    def test_extensao_nao_suportada(self) -> None:
        with pytest.raises(DominioFileError, match="CSV ou XLSX"):
            ler(b"x", "dominio.pdf")

    def test_limite_de_linhas(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(dominio_file, "MAX_ROWS", 3)
        texto = "chave;uf\n" + f"{CHAVE};SP\n" * 5

        with pytest.raises(DominioFileError, match="mais de 3"):
            ler(texto.encode(), "d.csv")

    def test_chave_com_espacos_e_minuscula_e_normalizada(self) -> None:
        linhas, _ = ler(f"chave;uf\n {CHAVE.lower()} ;sp\n".encode(), "d.csv")

        assert [(item.key, item.uf) for item in linhas] == [(CHAVE, "SP")]
