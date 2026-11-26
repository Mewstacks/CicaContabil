"""Conversão do pacote do HubFedrizzi em modelos nativos: idempotente, só no escritório alvo."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from apps.accounts.models import User
from apps.fiscal_calendar.models import NonBusinessDay
from apps.hub.legacy_import import import_bundle
from apps.hub.legacy_nfse import import_nfse_documents
from apps.hub.models import (
    ActivityTemplate,
    ActivityTemplateAssignment,
    ClientCompany,
    CompanyAreaResponsible,
    CompanyPartner,
    LegacyImportRecord,
    NfseDocument,
    NfseSync,
    ObligationDelivery,
)
from apps.organizations.models import Membership, Organization
from apps.triage.models import (
    ChecklistEntry,
    DocumentType,
    ExtractionRule,
    LearnedLink,
    SenderRule,
)

pytestmark = pytest.mark.django_db

XML = (
    '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse"><infNFSe Id="NFS1">'
    "<nNFSe>10</nNFSe><dhProc>2026-07-02T12:04:55-03:00</dhProc>"
    "<emit><CNPJ>30631219000150</CNPJ><xNome>Prestadora</xNome></emit>"
    "<valores><vLiq>100.00</vLiq></valores></infNFSe></NFSe>"
)
XML2 = XML.replace("<nNFSe>10<", "<nNFSe>11<")
XML3 = XML.replace("<nNFSe>10<", "<nNFSe>12<")


def b64(text: str) -> dict[str, str]:
    return {"__b64__": base64.b64encode(text.encode()).decode()}


def make_bundle(
    root: Path, tables: dict[str, list[dict[str, Any]]], mongo: list[dict[str, Any]] | None = None
) -> Path:
    (root / "tables").mkdir(parents=True)
    manifest: dict[str, Any] = {
        "format_version": 1,
        "tables": {},
        "mongo_nfse": {"status": "ignorado"},
    }
    for name, rows in tables.items():
        data = (
            "\n".join(
                json.dumps({"pk": str(r["id"]), "row": r}, sort_keys=True, ensure_ascii=False)
                for r in rows
            )
            + "\n"
        ).encode()
        (root / "tables" / f"{name}.jsonl").write_bytes(data)
        manifest["tables"][name] = {"rows": len(rows), "sha256": hashlib.sha256(data).hexdigest()}
    if mongo is not None:
        data = (
            "\n".join(
                json.dumps({"pk": r["_id"], "row": r}, sort_keys=True, ensure_ascii=False)
                for r in mongo
            )
            + "\n"
        ).encode()
        (root / "mongo_nfse.jsonl").write_bytes(data)
        manifest["mongo_nfse"] = {
            "status": "ok",
            "rows": len(mongo),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    (root / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def empresa(pk: int, code: str, name: str, cnpj: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": pk,
        "codigo": code,
        "nome": name,
        "cnpj": cnpj,
        "regime": "SIMPLES",
        "ativa": True,
        **extra,
    }


def obrigacao(pk: int, sigla: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": pk,
        "sigla": sigla,
        "nome": sigla.upper(),
        "esfera": "FEDERAL",
        "categoria": "IMPOSTO",
        "periodicidade": "MENSAL",
        "dia_vencimento": 20,
        "meses_apos_competencia": 1,
        "ajuste_vencimento": "ANTECIPA",
        "destino_raiz": "",
        "destino_subpastas": "{empresa}\\{ano}\\{mes}",
        "sigla_integracao": "",
        "municipio": "",
        "uf": "",
        "permite_baixa_manual": True,
        "exige_conferencia_humana": True,
        "ativa": True,
        **extra,
    }


def envio(pk: int, vinculo: int, month: int, **extra: Any) -> dict[str, Any]:
    return {
        "id": pk,
        "empresa_obrigacao_id": vinculo,
        "ano": 2026,
        "mes": month,
        "status": "PENDENTE",
        "email_cliente_status": "NAO_ENVIADO",
        "data_envio": None,
        "enviado_cliente_em": None,
        "observacao": "",
        "responsavel": "",
        "email_cliente_destinatario": "",
        "email_cliente_erro": "",
        "email_cliente_por": "",
        "esocial_ok": False,
        "reinf_ok": False,
        "mit_ok": False,
        "recibo_dctfweb_ok": False,
        "guia_manual_ok": False,
        **extra,
    }


CATALOG = {
    "core_empresa": [
        empresa(1, "0001", "Alfa", "11.222.333/0001-81", dia_liberacao_email=5),
        empresa(2, "0002", "Beta", "30.631.219/0001-50", responsavel="ana@fed.test"),
    ],
    "core_obrigacao": [
        obrigacao(1, "DAS", dia_vencimento=20),
        obrigacao(2, "IRPJ QUOTAS", periodicidade="TRIMESTRAL", esfera="ESTADUAL", uf="RS"),
        obrigacao(3, "FOLHA DE PAGAMENTO", categoria="OBRIGACAO", ativa=False),
    ],
    "core_regimeobrigacao": [
        {"id": 1, "obrigacao_id": 1, "regime": "SIMPLES", "exige_inscricao_estadual": False},
        {"id": 2, "obrigacao_id": 1, "regime": "PRESUMIDO", "exige_inscricao_estadual": True},
    ],
    "core_empresaobrigacao": [
        {"id": 1, "empresa_id": 1, "obrigacao_id": 1, "ativa": True},
        {"id": 2, "empresa_id": 2, "obrigacao_id": 1, "ativa": True},
        {"id": 3, "empresa_id": 2, "obrigacao_id": 2, "ativa": False},
        {"id": 4, "empresa_id": 99, "obrigacao_id": 1, "ativa": True},
    ],
    "workflow_envio": [
        envio(1, 1, 10),
        envio(2, 1, 9, status="CONCLUIDO", data_envio="2026-10-05", guia_manual_ok=True),
        envio(
            3,
            2,
            10,
            email_cliente_status="ENVIADO",
            email_cliente_destinatario="c@x.test",
            enviado_cliente_em="2026-10-06T10:00:00+00:00",
            responsavel="Ana",
        ),
        envio(4, 99, 10, status="CONCLUIDO"),
    ],
    "core_empresainscricaoestadual": [
        {"id": 1, "empresa_id": 1, "numero": "029/0618657", "principal": True},
        {"id": 2, "empresa_id": 1, "numero": "0290618657", "principal": False},
        {"id": 3, "empresa_id": 1, "numero": "999", "principal": False},
    ],
    "triagem_socioempresa": [
        {
            "id": 7,
            "company_id": 1,
            "cpf": "123.456.789-09",
            "nome": "Maria",
            "participacao": "50.000",
            "updated_at": "2026-11-26T12:00:00+00:00",
        },
        {"id": 8, "company_id": 2, "cpf": "", "nome": "Sem CPF", "participacao": "x"},
    ],
}


@pytest.fixture
def office() -> Organization:
    return Organization.objects.create(name="Fedrizzi", slug="fedrizzi-contabilidade")


def run(office: Organization, tmp_path: Path, tables: dict[str, Any], **kwargs: Any) -> Any:
    bundle = tmp_path / "b"
    if not bundle.exists():
        make_bundle(bundle, tables)
    return import_bundle(organization=office, path=bundle, **kwargs)


def test_catalog_assignments_and_deliveries_are_native_and_idempotent(office, tmp_path):
    first = run(office, tmp_path, CATALOG)
    das = ActivityTemplate.objects.get(organization=office, code="das")
    assert (das.sphere, das.category, das.weekend_adjustment) == ("federal", "tax", "previous")
    assert das.legal_due_day == 20 and das.due_month_offset == 1 and das.active
    assert das.applicable_regimes == ["presumido", "simples"] and das.requires_state_registration
    assert das.allows_manual_completion and das.requires_human_review
    quarterly = ActivityTemplate.objects.get(organization=office, code="irpj-quotas")
    assert quarterly.periodicity == "quarterly" and quarterly.frequency == "ad_hoc"
    assert (quarterly.sphere, quarterly.state_code) == ("state", "RS")
    payroll = ActivityTemplate.objects.get(organization=office, code="folha-de-pagamento")
    assert payroll.area == "payroll" and not payroll.active

    assert ActivityTemplateAssignment.objects.filter(organization=office).count() == 3
    off = ActivityTemplateAssignment.objects.get(organization=office, active=False)
    assert off.template.code == "irpj-quotas"
    deliveries = ObligationDelivery.objects.filter(organization=office)
    assert deliveries.count() == 2  # placeholder PENDENTE e vínculo sem empresa ficam de fora
    done = deliveries.get(status="done")
    assert str(done.filed_on) == "2026-10-05" and done.checks["guia_manual_ok"] is True
    sent = deliveries.get(email_status="sent")
    assert sent.email_recipient == "c@x.test" and sent.responsible_name == "Ana"

    assert any(
        line.startswith("paridade core_empresaobrigacao") and "origem=4 nativo=3" in line
        for line in first.parity
    )
    assert any("origem=4 nativo=2" in line and "workflow_envio" in line for line in first.parity)

    counts = (
        ActivityTemplate.objects.count(),
        ActivityTemplateAssignment.objects.count(),
        ObligationDelivery.objects.count(),
        LegacyImportRecord.objects.count(),
    )
    import_bundle(organization=office, path=tmp_path / "b")
    assert counts == (
        ActivityTemplate.objects.count(),
        ActivityTemplateAssignment.objects.count(),
        ObligationDelivery.objects.count(),
        LegacyImportRecord.objects.count(),
    )


def test_hold_generation_creates_assignments_inactive(office, tmp_path):
    run(office, tmp_path, CATALOG, hold_generation=True)
    assert not ActivityTemplateAssignment.objects.filter(organization=office, active=True).exists()


def test_existing_template_is_reused_and_only_blanks_are_filled(office, tmp_path):
    mine = ActivityTemplate.objects.create(
        organization=office, code="das", title="DAS do escritório", area="fiscal", legal_due_day=10
    )
    run(office, tmp_path, CATALOG)
    mine.refresh_from_db()
    assert mine.title == "DAS do escritório" and mine.legal_due_day == 10
    assert mine.sphere == "federal"
    assert ActivityTemplate.objects.filter(organization=office, code="das").count() == 1


def test_company_extras_partners_and_state_registration(office, tmp_path):
    ana = User.objects.create(email="ana@fed.test", full_name="Ana")
    Membership.objects.create(organization=office, user=ana)
    report = run(office, tmp_path, CATALOG)
    alfa = ClientCompany.objects.get(organization=office, dominio_code="0001")
    assert alfa.email_release_day == 5 and alfa.state_registration == "029/0618657"
    beta = ClientCompany.objects.get(organization=office, dominio_code="0002")
    assert CompanyAreaResponsible.objects.get(company=beta, area="fiscal").user == ana
    maria = CompanyPartner.objects.get(company=alfa)
    assert maria.document == "12345678909" and str(maria.share_percent) == "50.000"
    assert CompanyPartner.objects.get(company=beta).document == ""
    line = next(x for x in report.parity if x.startswith("paridade core_empresainscricaoestadual"))
    assert "origem=3 nativo=2" in line and "inscrição adicional" in line


TRIAGE = {
    "core_empresa": CATALOG["core_empresa"],
    "triagem_documenttype": [
        {
            "id": 1,
            "code": "extrato",
            "label": "Extrato",
            "name_template": "{empresa_codigo:0>4}_{tipo}_{banco}_{periodo}",
            "folder_template": "{pasta_cliente}/CONTABIL/EXTRATOS/{ano}/{mes}",
            "periodicity": "mensal",
            "required_by_default": True,
            "active": True,
            "keywords": ["extrato"],
        },
        {
            "id": 2,
            "code": "societario",
            "label": "Societário",
            "name_template": "{empresa_codigo:0>4}_{tipo}_{periodo}",
            "folder_template": "C:/fora",
            "periodicity": "eventual",
            "required_by_default": False,
            "active": True,
            "keywords": [],
        },
    ],
    "triagem_senderrule": [
        {
            "id": 1,
            "sender_pattern": "A@x.test",
            "document_type_id": 1,
            "confirmations": 2,
            "active": False,
            "company_id": 1,
        },
        {
            "id": 2,
            "sender_pattern": "a@x.test",
            "document_type_id": 1,
            "confirmations": 4,
            "active": True,
            "company_id": 2,
        },
    ],
    "triagem_sendercompany": [{"id": 1, "sender": "Cli@x.test", "company_id": 1}],
    "triagem_extractionrule": [
        {
            "id": 1,
            "mode": "ofx_conta",
            "anchor": "conta",
            "active": True,
            "errors": 0,
            "company_id": None,
        },
        {
            "id": 2,
            "mode": "linha_seguinte",
            "anchor": "associado",
            "active": True,
            "errors": 1,
            "company_id": None,
        },
        {
            "id": 3,
            "mode": "dois_pontos",
            "anchor": "sem alias",
            "active": True,
            "errors": 0,
            "company_id": None,
        },
    ],
    "triagem_rulealias": [
        {"id": 1, "rule_id": 1, "company_id": 1, "value_norm": "041 0239"},
        {"id": 2, "rule_id": 2, "company_id": 2, "value_norm": "beta ltda"},
    ],
    "triagem_checklistentry": [
        {
            "id": 1,
            "company_id": 1,
            "document_type_id": 1,
            "period_label": "102026",
            "received_at": "2026-10-23T17:48:44+00:00",
        },
    ],
    "triagem_triagecorrection": [{"id": 1, "state": "feita"}],
}


def test_triage_rules_are_converted_without_duplicates(office, tmp_path):
    DocumentType.objects.create(
        organization=office,
        code="societario",
        label="Meu societário",
        name_template="x",
        period_kind="competencia",
    )
    report = run(office, tmp_path, TRIAGE)
    extrato = DocumentType.objects.get(organization=office, code="extrato")
    assert extrato.name_template == "{codigo}_EXTRATO_{contraparte}_{periodo}"
    assert extrato.period_kind == "competencia" and extrato.counterparty_kind == "banco"
    assert (
        extrato.folder_template == "{dominio_code} - {company_name}\\CONTABIL\\EXTRATOS\\{period}"
    )
    assert extrato.expected_default and extrato.keywords == ["extrato"]
    assert DocumentType.objects.get(organization=office, code="societario").label == (
        "Meu societário"
    )  # existente não é sobrescrito

    rule = SenderRule.objects.get(organization=office, sender="a@x.test")
    assert len(rule.confirmed_items) == 4 and not rule.blocked  # maior contagem das duas linhas
    link = LearnedLink.objects.get(organization=office, kind="sender")
    assert link.key == "cli@x.test"
    assert LearnedLink.objects.filter(organization=office, kind="account", key="041 0239").exists()
    extraction = ExtractionRule.objects.get(organization=office)
    assert (extraction.mode, extraction.anchor, extraction.value) == (
        "linha_seguinte",
        "associado",
        "beta ltda",
    )
    assert ChecklistEntry.objects.get(organization=office).period_label == "102026"
    assert any(
        "triagem_extractionrule" in x and "regra de layout sem empresa" in x for x in report.parity
    )
    assert any("triagem_triagecorrection: origem=1 nativo=0" in x for x in report.parity)

    before = (
        SenderRule.objects.count(),
        LearnedLink.objects.count(),
        ExtractionRule.objects.count(),
        ChecklistEntry.objects.count(),
        DocumentType.objects.count(),
    )
    import_bundle(organization=office, path=tmp_path / "b")
    assert before == (
        SenderRule.objects.count(),
        LearnedLink.objects.count(),
        ExtractionRule.objects.count(),
        ChecklistEntry.objects.count(),
        DocumentType.objects.count(),
    )


def sync_row(pk: int, empresa_id: int, **extra: Any) -> dict[str, Any]:
    return {
        "id": pk,
        "empresa_id": empresa_id,
        "ativo": True,
        "ultimo_nsu": 61,
        "procuracao": "ok",
        "origem_credencial": "escritorio",
        "procuracao_verificada_em": "2026-11-09T21:57:17+00:00",
        "ultima_execucao": "2026-11-09T21:57:17+00:00",
        "proxima_consulta_em": "2026-11-10T21:57:17+00:00",
        "status": "ok",
        "ultimo_erro": "",
        "ultimo_aviso": "",
        **extra,
    }


def test_nfse_sync_keeps_checkpoint_and_stays_off_until_cutover(office, tmp_path):
    tables = {
        "core_empresa": CATALOG["core_empresa"],
        "nfse_sincronizacaonfse": [
            sync_row(1, 1),
            sync_row(2, 2, procuracao="ausente"),
            # linha órfã: o CNPJ ainda identifica a empresa (Beta), que já tem a sua
            sync_row(3, None, cnpj="30631219000150", ultimo_nsu=99),
        ],
    }
    run(office, tmp_path, tables)
    sync = NfseSync.objects.get(organization=office, company__dominio_code="0001")
    assert sync.checkpoint_nsu == "61" and not sync.enabled and sync.status == "paused"
    assert sync.credential_mode == "procuracao" and sync.procuracao_status == "ok"
    assert sync.procuracao_ok_at is not None and sync.next_run_at is None
    other = NfseSync.objects.get(organization=office, company__dominio_code="0002")
    assert other.procuracao_status == "missing" and other.procuracao_ok_at is None
    assert NfseSync.objects.filter(organization=office).count() == 2  # órfã caiu na mesma empresa


def test_nfse_sync_can_be_enabled_for_the_cutover(office, tmp_path):
    tables = {"core_empresa": CATALOG["core_empresa"], "nfse_sincronizacaonfse": [sync_row(1, 1)]}
    run(office, tmp_path, tables, enable_nfse_sync=True)
    sync = NfseSync.objects.get(organization=office)
    assert sync.enabled and sync.status == "idle" and sync.next_run_at is not None


def test_holidays_become_inert_global_drafts(office, tmp_path):
    tables = {
        "core_feriado": [
            {
                "id": 1,
                "data": "2026-09-20",
                "nome": "Dia do Gaúcho",
                "abrangencia": "ESTADUAL",
                "uf": "RS",
                "municipio": "",
            },
            {
                "id": 2,
                "data": "2026-06-20",
                "nome": "Aniversário",
                "abrangencia": "MUNICIPAL",
                "uf": "RS",
                "municipio": "Caxias do Sul",
            },
        ]
    }
    run(office, tmp_path, tables)
    days = NonBusinessDay.objects.exclude(calendar__scope="BR").order_by("day")
    assert [d.name for d in days] == ["Aniversário", "Dia do Gaúcho"]
    assert {d.calendar.status for d in days} == {"draft"}
    assert {d.calendar.scope for d in days} == {"RS", "RS:caxias-do-sul"}


def test_other_offices_are_never_read_or_written(office, tmp_path):
    other = Organization.objects.create(name="Outro", slug="outro")
    theirs = ClientCompany.objects.create(organization=other, name="Alfa", dominio_code="0001")
    ActivityTemplate.objects.create(organization=other, code="das", title="DAS", area="fiscal")
    run(office, tmp_path, CATALOG)
    assert ActivityTemplate.objects.filter(organization=other).count() == 1
    assert not ActivityTemplateAssignment.objects.filter(organization=other).exists()
    assert not ObligationDelivery.objects.filter(organization=other).exists()
    assert not CompanyPartner.objects.filter(organization=other).exists()
    theirs.refresh_from_db()
    assert theirs.email_release_day is None and theirs.state_registration == ""
    assert not LegacyImportRecord.objects.filter(organization=other).exists()


def test_dry_run_converts_nothing(office, tmp_path):
    run(office, tmp_path, CATALOG, dry_run=True)
    assert not ActivityTemplate.objects.exists()
    assert not ActivityTemplateAssignment.objects.exists()
    assert not LegacyImportRecord.objects.exists()


def nota(pk: int, empresa_id: int, xml: str, key: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": pk,
        "empresa_id": empresa_id,
        "chave_acesso": key,
        "xml": b64(xml),
        "tipo": "emitidas",
        "situacao": "P100_GERADA",
        "cancelada": False,
        "baixada_em": "2026-08-30T16:07:00+00:00",
        **extra,
    }


def mongo_row(oid: str, cnpj: str, xml: str, key: str, nsu: int) -> dict[str, Any]:
    return {
        "_id": oid,
        "cnpj": cnpj,
        "chave_acesso": key,
        "nsu": nsu,
        "xml_content": b64(xml),
        "tipo": "tomadas",
        "situacao": "ativa",
    }


def nfse_bundle(tmp_path: Path) -> Path:
    tables = {
        "core_empresa": CATALOG["core_empresa"],
        "robo_nfse_notanfse": [
            nota(1, 1, XML, "K1"),
            nota(2, 1, XML2, "K2", cancelada=True, situacao="P104_NFSE_CANCELADA"),
            nota(3, 77, XML3, "K3"),
        ],
    }
    mongo = [
        mongo_row("a1", "11222333000181", XML, "K1", 1),  # mesma nota da tabela do robô
        mongo_row("a2", "11222333000181", XML3, "K9", 3),
        mongo_row("a3", "30631219000150", XML3, "K9", 3),  # outra empresa, mesmo NSU
        mongo_row("a4", "00000000000000", XML3, "K10", 4),  # CNPJ sem empresa
    ]
    return make_bundle(tmp_path / "n", tables, mongo)


def test_nfse_documents_stream_into_native_evidence(office, tmp_path):
    bundle = nfse_bundle(tmp_path)
    report = import_bundle(organization=office, path=bundle)
    robo = LegacyImportRecord.objects.get(
        organization=office, source_table="robo_nfse_notanfse", source_pk="1"
    )
    assert robo.payload["xml"] is None and robo.payload["chave_acesso"] == "K1"
    assert not LegacyImportRecord.objects.filter(source_table="mongo_nfse").exists()
    assert any("mongo_nfse: 4 notas" in w for w in report.warnings)

    docs = import_nfse_documents(organization=office, path=bundle)
    assert docs.created["robo"] == 2 and docs.skipped["empresa sem nativa"] == 2
    assert docs.created["mongo"] == 2 and docs.existing["mongo"] == 1
    stored = NfseDocument.objects.filter(organization=office)
    assert stored.count() == 4
    first = stored.get(document_hash=hashlib.sha256(XML.encode()).hexdigest())
    assert first.original_xml == XML and first.normalized_data["legacy"]["source"] == "robo"
    assert first.normalized_data["source"] == "hubfedrizzi"
    assert str(first.issued_at.date()) == "2026-07-02"
    cancelled = stored.get(document_hash=hashlib.sha256(XML2.encode()).hexdigest())
    assert cancelled.normalized_data["legacy"]["cancelada"] is True
    # mesmo NSU em duas empresas é permitido; na mesma empresa o segundo perde o NSU
    assert stored.filter(source_nsu="3").count() == 2

    again = import_nfse_documents(organization=office, path=bundle)
    assert again.created["robo"] == 0 and again.created["mongo"] == 0
    assert NfseDocument.objects.filter(organization=office).count() == 4


def test_nfse_measure_only_writes_nothing_and_sizes_storage(office, tmp_path):
    bundle = nfse_bundle(tmp_path)
    import_bundle(organization=office, path=bundle)
    docs = import_nfse_documents(organization=office, path=bundle, measure_only=True)
    assert not NfseDocument.objects.exists()
    assert docs.created["robo"] == 2 and docs.xml_bytes["robo"] == len(XML) + len(XML2)
    assert any("armazenamento estimado" in line for line in docs.lines())
    assert any("nada foi gravado" in line for line in docs.lines())


def test_nfse_limit_caps_each_source(office, tmp_path):
    bundle = nfse_bundle(tmp_path)
    import_bundle(organization=office, path=bundle)
    docs = import_nfse_documents(organization=office, path=bundle, sources=("robo",), limit=1)
    assert docs.read["robo"] == 1 and NfseDocument.objects.count() == 1


def test_users_count_in_the_parity_report(office, tmp_path):
    tables = {
        "auth_user": [
            {"id": 1, "email": "ana@fed.test", "is_active": True},
            {"id": 2, "email": "", "is_active": True},
        ]
    }
    report = run(office, tmp_path, tables, with_users=True)
    assert any("paridade auth_user" in x and "origem=2 nativo=1" in x for x in report.parity)
