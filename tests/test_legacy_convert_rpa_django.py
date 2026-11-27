"""Conversão do pacote do HubFedrizzi, 2ª etapa: fechamento, FAP, FGTS, DET, folha, pastas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.test_legacy_convert_django import empresa, make_bundle, obrigacao

from apps.closing.models import ClosingConference, ClosingDocument, ClosingField, ClosingLayout
from apps.det.models import DetQuery, DetResult
from apps.fap.models import FapBatch, FapItem
from apps.fgts.models import FgtsBatch, FgtsItem
from apps.folha.models import FolhaSheetMark, FolhaTitle
from apps.hub.legacy_import import import_bundle
from apps.hub.models import ActivityTemplate, LegacyImportRecord
from apps.organizations.models import Organization
from apps.triage.models import FolderModel

pytestmark = pytest.mark.django_db


def field(pk: int, layout: int, variable: str, locator: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": pk,
        "mapeamento_id": layout,
        "variavel": variable,
        "localizador": locator,
        "ocorrencia": 0,
        "somar": 0,
        "anulado": False,
        "position": pk,
        **extra,
    }


SAMPLE = "RECIBO GIA\nCNPJ: 11.222.333/0001-81\nCompetência: 08/2026\nValor: 39,83"
TABLES: dict[str, list[dict[str, Any]]] = {
    "core_empresa": [empresa(1, "0001", "Alfa", "11.222.333/0001-81")],
    "core_obrigacao": [obrigacao(1, "EFD-ICMS-IPI")],
    "fechamento_mapeamentorecibo": [
        {
            "id": 1,
            "nome": "EFD ICMS IPI",
            "obrigacao_sigla": "EFD-ICMS-IPI",
            "amostra_texto": SAMPLE,
        },
        {"id": 2, "nome": "Sem campos", "obrigacao_sigla": "", "amostra_texto": ""},
    ],
    "fechamento_campomapeado": [
        field(1, 1, "MARCADOR", "RECIBO GIA"),
        field(2, 1, "CNPJ", "CNPJ:"),
        field(3, 1, "COMPETENCIA", "Competência:"),
        field(4, 1, "VALOR_PRINCIPAL", "Valor:"),
        field(6, 2, "NUM_RECIBO", "Número", ocorrencia=1, somar=2),
        field(5, 1, "CUSTOM_DCTFWEB_RECEBIDA", "x"),
    ],
    "fechamento_recibo": [
        {
            "id": 11,
            "empresa_id": 1,
            "ano": 2026,
            "mes": 8,
            "nome_original": "SPED FISCAL.pdf",
            "hash_arquivo": "a" * 64,
            "obrigacao_sigla": "EFD-ICMS-IPI",
            "parseado_ok": True,
            "valor_principal": "39.83",
            "valor_icms": "0.00",
            "valor_ipi": None,
            "valor_issqn": None,
            "valor_issqn_retido": None,
            "extras": {"Inscrição estadual": "029/0618657"},
            "texto_extraido": "Lido 100%",
        },
        {
            "id": 12,
            "empresa_id": 1,
            "ano": 2026,
            "mes": 8,
            "nome_original": "x.pdf",
            "hash_arquivo": "",
            "obrigacao_sigla": "X",
        },
    ],
    "fechamento_conferencia": [
        {
            "id": 2,
            "recibo_id": 11,
            "resultado": "BAIXA_AUTOMATICA",
            "valor_declarado": "0.00",
            "valor_guia": "0.00",
            "fonte_valor_guia": "DOCUMENTO",
            "observacao": "ICMS zerado",
        },
        {"id": 3, "recibo_id": 99, "resultado": "LEITURA"},
    ],
    "fechamento_triagemempresa": [{"id": 1, "empresa_id": 1, "estado": "PENDENTE"}],
    "fap_lotefap": [{"id": 1, "ano": 2027, "estado": "atencao", "aviso": "x"}],
    "fap_itemfap": [
        {
            "id": 1,
            "lote_id": 1,
            "empresa_id": 1,
            "codigo_dominio": "2",
            "nome_empresa": "Alfa",
            "cnpj": "11222333000181",
            "estado": "concluido",
            "geracao": 1,
            "sha256_pdf": "b" * 64,
            "validado_em": "2026-10-23T15:20:04+00:00",
            "mensagem": "ok",
        },
        {
            "id": 2,
            "lote_id": 1,
            "empresa_id": 1,
            "codigo_dominio": "3",
            "nome_empresa": "Beta",
            "cnpj": "",
            "estado": "raiz_ausente",
        },
        {"id": 3, "lote_id": 7, "codigo_dominio": "4"},
    ],
    "fgts_lote": [{"id": 1, "ano": 2026, "mes": 9, "data_limite": "2026-10-26"}],
    "fgts_item": [
        {
            "id": 1,
            "lote_id": 1,
            "empresa_id": 1,
            "raiz_cnpj": "00408837",
            "estado": "falha",
            "nome_empresa": "157 · X",
            "cnpj_representante": "00408837000174",
            "codigos_empresa": ["157/1"],
            "valor_esperado": "1274.18",
            "valor_portal": None,
            "vencimento_portal": None,
            "mensagem": "m",
        },
    ],
    "det_consulta": [
        {
            "id": 1,
            "estado": "falha",
            "erro": "login",
            "total_mensagens": 5,
            "empresas": [{"cnpj": "30631219000150", "codigo": "1", "razao_social": "Fed"}],
            "resultados": [
                {
                    "empresa": {"cnpj": "30631219000150", "codigo": "1", "razao_social": "Fed"},
                    "situacao": "Erro na consulta",
                    "mensagens": [],
                    "detalhe": "d",
                },
                {
                    "empresa": {"cnpj": "30631219000150", "codigo": "1", "razao_social": "Fed"},
                    "situacao": "Sem procuração",
                    "mensagens": [],
                    "detalhe": "repetida",
                },
            ],
        },
    ],
    "relatorios_folha_titulorelatoriofolha": [{"id": 1, "chave": "calculo", "nome": "Cálculo"}],
    "relatorios_folha_atualizacaoplanilhafolha": [
        {
            "id": 6,
            "competencia": "10/2026",
            "empresa_codigo": "0001",
            "etapa": "relatorios",
            "estado": "feito",
            "aba": "10/2026",
            "celula": "M85",
            "tentativas": 1,
            "erro": "",
            "gravado_em": "2026-10-22T13:47:38+00:00",
        },
    ],
    "arquivos_modelopastas": [
        {
            "id": 1,
            "revisao": 2,
            "ativo": True,
            "arvore": [
                {
                    "id": "n1",
                    "nome": "FISCAL",
                    "variavel": "",
                    "uso": "",
                    "filhos": [
                        {"id": "n2", "nome": "ANO", "variavel": "ano", "uso": "", "filhos": []}
                    ],
                }
            ],
        },
    ],
    "admissoes_admissao": [{"id": 1, "estado": "falha"}],
}


@pytest.fixture
def office() -> Organization:
    return Organization.objects.create(name="Fedrizzi", slug="fedrizzi-contabilidade")


def go(office: Organization, tmp_path: Path, **kwargs: Any) -> Any:
    bundle = tmp_path / "b"
    if not bundle.exists():
        make_bundle(bundle, TABLES)
    return import_bundle(organization=office, path=bundle, **kwargs)


def test_closing_layouts_fields_documents_and_conferences(office, tmp_path):
    report = go(office, tmp_path)
    layout = ClosingLayout.objects.get(organization=office, code="efd-icms-ipi")
    assert layout.activity_code == "efd-icms-ipi" and not layout.active
    assert layout.sample_text == SAMPLE
    variables = set(ClosingField.objects.filter(layout=layout).values_list("variable", flat=True))
    assert variables == {"marker", "cnpj", "competence", "amount"}
    number = ClosingField.objects.get(variable="number")
    assert (number.anchor, number.occurrence, number.sum_count) == ("Número", 1, 2)
    document = ClosingDocument.objects.get(organization=office)
    assert document.state == "accepted" and document.layout == layout
    assert str(document.competence) == "2026-08-01" and str(document.amount) == "39.83"
    assert document.company.dominio_code == "0001" and document.content_hash == "a" * 64
    assert document.read_values == {"Inscrição estadual": "029/0618657"}
    conference = ClosingConference.objects.get(organization=office)
    assert conference.outcome == "zero" and conference.reference_source == "document"
    assert any(
        "paridade fechamento_campomapeado" in x and "origem=6 nativo=5" in x for x in report.parity
    )
    assert any(
        "paridade fechamento_recibo" in x and "origem=2 nativo=1" in x for x in report.parity
    )
    assert any("paridade fechamento_triagemempresa: origem=1 nativo=0" in x for x in report.parity)


def test_layout_activation_only_on_request(office, tmp_path):
    go(office, tmp_path, activate_layouts=True)
    assert ClosingLayout.objects.get(organization=office, code="efd-icms-ipi").active
    assert not ClosingLayout.objects.get(organization=office, label="Sem campos").active


def test_rpa_modules_fap_fgts_det_folha_and_folders(office, tmp_path):
    report = go(office, tmp_path)
    batch = FapBatch.objects.get(organization=office)
    assert batch.year == 2027 and batch.state == "attention"
    items = {i.code: i for i in FapItem.objects.filter(organization=office)}
    assert set(items) == {"2", "3"} and items["2"].state == "done"
    assert items["2"].sha256 == "b" * 64 and items["3"].state == "root_missing"
    fgts = FgtsItem.objects.get(organization=office)
    assert fgts.expected_cents == 127418 and fgts.state == "failed" and fgts.portal_cents is None
    assert str(FgtsBatch.objects.get(organization=office).deadline) == "2026-10-26"
    query = DetQuery.objects.get(organization=office)
    assert query.state == "failed" and query.companies[0]["cnpj"] == "30631219000150"
    result = DetResult.objects.get(query=query)  # a repetida da mesma empresa não duplica
    assert result.situation == "error"
    assert FolhaTitle.objects.get(organization=office, key="calculo").name == "Cálculo"
    mark = FolhaSheetMark.objects.get(organization=office)
    assert (str(mark.competence), mark.stage, mark.state, mark.cell) == (
        "2026-10-01",
        "reports",
        "done",
        "M85",
    )
    folder = FolderModel.objects.get(organization=office)
    assert folder.revision == 2 and folder.active
    assert folder.tree[0]["name"] == "FISCAL"
    assert folder.tree[0]["children"][0] == {
        "id": "n2",
        "name": "ANO",
        "variable": "ano",
        "use": "",
        "children": [],
    }
    assert any("paridade fap_itemfap" in x and "origem=3 nativo=2" in x for x in report.parity)
    assert any("paridade admissoes_admissao: origem=1 nativo=0" in x for x in report.parity)


def test_second_run_creates_nothing(office, tmp_path):
    go(office, tmp_path)
    models = (
        ClosingLayout,
        ClosingField,
        ClosingDocument,
        ClosingConference,
        FapBatch,
        FapItem,
        FgtsBatch,
        FgtsItem,
        DetQuery,
        DetResult,
        FolhaTitle,
        FolhaSheetMark,
        FolderModel,
        LegacyImportRecord,
        ActivityTemplate,
    )
    before = [m.objects.count() for m in models]
    second = go(office, tmp_path)
    assert before == [m.objects.count() for m in models]
    assert not any(x.startswith("nativo criado") for x in second.parity)


def test_other_office_is_untouched(office, tmp_path):
    other = Organization.objects.create(name="Outro", slug="outro")
    FolderModel.objects.create(organization=other, tree=[], active=False)
    go(office, tmp_path)
    assert FolderModel.objects.get(organization=other).tree == []
    for model in (ClosingLayout, ClosingDocument, FapBatch, FgtsBatch, DetQuery, FolhaTitle):
        assert not model.objects.filter(organization=other).exists()
