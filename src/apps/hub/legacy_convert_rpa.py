"""Second conversion stage: closing, RPA modules (FAP, FGTS, DET), payroll and folder tree.

Same rules as ``legacy_convert``: one organization, natural keys before ``create``, ``mapped_to``
stamped on every legacy row that found a native home, and one parity line per table.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from django.db import transaction

from apps.closing.models import ClosingConference, ClosingDocument, ClosingField, ClosingLayout
from apps.closing.services import activation_problems
from apps.det.models import DetQuery, DetResult
from apps.fap.models import FapBatch, FapItem
from apps.fgts.models import FgtsBatch, FgtsItem
from apps.folha.models import FolhaSheetMark, FolhaTitle
from apps.hub.legacy_convert import (
    PARITY_TARGETS,
    Stats,
    _date,
    _datetime,
    _digits,
    _int,
    _Marks,
    _records,
    _slug,
    _text,
    mapped_ids,
)
from apps.hub.models import ActivityTemplate, ClientCompany, LegacyImportRecord
from apps.organizations.models import Organization
from apps.triage.models import FolderModel

FIELD_VARIABLES = {
    "MARCADOR": "marker",
    "MARCADOR_2": "marker_2",
    "MARCADOR_3": "marker_3",
    "MARCADOR_4": "marker_4",
    "COMPETENCIA": "competence",
    "CNPJ": "cnpj",
    "CNPJ_RAIZ": "cnpj_root",
    "INSCRICAO_ESTADUAL": "state_registration",
    "INSCRICAO_MUNICIPAL": "municipal_registration",
    "VALOR_PRINCIPAL": "amount",
    "ICMS": "icms",
    "IPI": "ipi",
    "ISSQN": "iss",
    "ISSQN_RETIDO": "iss_withheld",
    "NUM_RECIBO": "number",
    "RAZAO_SOCIAL": "legal_name",
}
CONFERENCE_OUTCOME = {
    "OK": ClosingConference.Outcome.MATCHED,
    "BAIXA_AUTOMATICA": ClosingConference.Outcome.ZERO,
    "DIVERGENCIA": ClosingConference.Outcome.DIVERGED,
    "LEITURA": ClosingConference.Outcome.READ,
}
FAP_BATCH_STATE = {"atencao": FapBatch.State.ATTENTION, "concluido": FapBatch.State.DONE}
FAP_ITEM_STATE = {
    "raiz_ausente": FapItem.State.ROOT_MISSING,
    "concluido": FapItem.State.DONE,
    "existente": FapItem.State.DONE,
    "cadastro": FapItem.State.REGISTRY,
    "sem_relatorio": FapItem.State.NO_REPORT,
    "sem_permissao": FapItem.State.NO_PERMISSION,
    "revisao": FapItem.State.REVIEW,
    "falha": FapItem.State.FAILED,
}
FGTS_ITEM_STATE = {
    "falha": FgtsItem.State.FAILED,
    "divergencia": FgtsItem.State.DIVERGENCE,
    "incerto": FgtsItem.State.UNCERTAIN,
    "revisao": FgtsItem.State.REVIEW,
    "preparado": FgtsItem.State.PREPARED,
}
DET_STATE = {
    "falha": DetQuery.State.FAILED,
    "concluida": DetQuery.State.DONE,
    "cancelada": DetQuery.State.CANCELLED,
}
DET_SITUATION = {str(label): value for value, label in DetResult.Situation.choices}
SHEET_STAGE = {
    "calculo": FolhaSheetMark.Stage.CALC,
    "relatorios": FolhaSheetMark.Stage.REPORTS,
    "email": FolhaSheetMark.Stage.EMAIL,
}

PARITY_TARGETS.update(
    {
        "fechamento_mapeamentorecibo": "closing.ClosingLayout",
        "fechamento_campomapeado": "closing.ClosingField",
        "fechamento_recibo": "closing.ClosingDocument",
        "fechamento_conferencia": "closing.ClosingConference",
        "fap_lotefap": "fap.FapBatch",
        "fap_itemfap": "fap.FapItem",
        "fgts_lote": "fgts.FgtsBatch",
        "fgts_item": "fgts.FgtsItem",
        "det_consulta": "det.DetQuery (+ DetResult)",
        "relatorios_folha_titulorelatoriofolha": "folha.FolhaTitle",
        "relatorios_folha_atualizacaoplanilhafolha": "folha.FolhaSheetMark",
        "arquivos_modelopastas": "triage.FolderModel",
    }
)
EXTRA_NO_HOME = {
    "fechamento_arquivofiscal": "fila de arquivamento do Drive antigo",
    "fechamento_ingestaoarquivo": "eventos de vigia de pasta do worker antigo",
    "fechamento_operacaoarquivo": "fila de operações de arquivo do worker antigo",
    "fechamento_controleacervo": "chave liga/desliga do worker antigo",
    "fechamento_triagemempresa": "estado do robô por empresa e mês (o motor novo recalcula)",
    "fechamento_pastaclientearquivo": "pasta de cliente do Drive antigo",
    "fap_eventofap": "log de ações do lote FAP (não há tabela de eventos no módulo novo)",
    "fap_estadoworker": "estado do worker (heartbeat)",
    "fgts_estadoworker": "estado do worker (heartbeat)",
    "det_estadoworker": "estado do worker (heartbeat)",
    "admissoes_controlefila": "estado do worker (heartbeat)",
    "admissoes_admissao": (
        "21 execuções de teste na empresa EXEMPLO do Domínio, com dados pessoais fictícios; "
        "não migradas de propósito"
    ),
    "arquivos_regraarquivo": "regra por obrigação sem tipo de documento (a nova exige um)",
    "arquivos_acervopreservado": "caminho do acervo do servidor antigo",
    "arquivos_documentoarquivo": "fila de arquivamento do servidor antigo (sem os arquivos)",
    "arquivos_uploadarquivo": "uploads de teste do fluxo antigo de arquivos",
    "triagem_clientfolderindex": "cache de leitura da pasta do servidor antigo",
    "triagem_triageconfig": "caixa de e-mail IMAP: a senha não vem no pacote; recadastrar a caixa",
    "core_vagavm": "controle de VM do HubFedrizzi",
}


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _live(model: Any, record: LegacyImportRecord, prefix: str) -> Any:
    """The native row this record already points to, if it still exists."""

    if record.mapped_to.startswith(prefix):
        return model.objects.filter(pk=UUID(record.mapped_to[len(prefix) :])).first()
    return None


# ---- closing --------------------------------------------------------------------------------


def convert_closing(organization: Organization, stats: Stats, *, activate: bool) -> None:
    companies = mapped_ids(organization, "core_empresa", "hub.ClientCompany:")
    marks = _Marks()
    template_codes = set(
        ActivityTemplate.objects.filter(organization=organization).values_list("code", flat=True)
    )
    layouts: dict[str, ClosingLayout] = {}
    layout_by_sigla: dict[str, ClosingLayout] = {}
    prefix = "closing.ClosingLayout:"
    for record in _records(organization, "fechamento_mapeamentorecibo"):
        data = record.payload
        sigla = _text(data.get("obrigacao_sigla"), 80)
        code = _slug(sigla or str(data.get("nome") or ""), 64)
        if not code:
            stats.skip("fechamento_mapeamentorecibo", "sem sigla nem nome")
            continue
        layout = (
            _live(ClosingLayout, record, prefix)
            or ClosingLayout.objects.filter(organization=organization, code=code).first()
        )
        if layout is None:
            activity = _slug(sigla, 80)
            layout = ClosingLayout.objects.create(
                organization=organization,
                code=code,
                label=_text(data.get("nome") or sigla, 160),
                kind=ClosingLayout.Kind.RECEIPT,
                activity_code=activity if activity in template_codes else "",
                sample_text=str(data.get("amostra_texto") or ""),
                active=False,
            )
            stats.created["layouts de fechamento"] += 1
        else:
            stats.reused["layouts de fechamento"] += 1
        layouts[record.source_pk] = layout
        if sigla:
            layout_by_sigla.setdefault(sigla, layout)
        marks.set(record, f"{prefix}{layout.pk}")
    marks.flush()

    for record in _records(organization, "fechamento_campomapeado"):
        data = record.payload
        layout = layouts.get(str(data.get("mapeamento_id")))
        variable = FIELD_VARIABLES.get(str(data.get("variavel") or "").upper())
        if layout is None or variable is None:
            stats.skip(
                "fechamento_campomapeado",
                "layout sem nativo" if layout is None else "variável personalizada sem equivalente",
            )
            continue
        field, made = ClosingField.objects.get_or_create(
            organization=organization,
            layout=layout,
            variable=variable,
            defaults={
                "anchor": _text(data.get("localizador"), 255),
                "occurrence": min(max(_int(data.get("ocorrencia")) or 0, 0), 32000),
                "sum_count": min(max(_int(data.get("somar")) or 0, 0), 32000),
                "nullified": bool(data.get("anulado")),
                "position": min(max(_int(data.get("position")) or 0, 0), 32000),
            },
        )
        stats.created["campos de fechamento"] += int(made)
        stats.reused["campos de fechamento"] += int(not made)
        marks.set(record, f"closing.ClosingField:{field.pk}")
    marks.flush()
    ready = 0
    for layout in layouts.values():
        if not activation_problems(layout):
            ready += 1
            if activate and not layout.active:
                layout.active = True
                layout.save(update_fields=["active", "updated_at"])
    if layouts:
        stats.warnings.append(
            f"{ready} de {len(layouts)} layouts de fechamento já leem a própria amostra "
            f"({'ativados' if activate else 'ativação é do escritório; ou use --activate-layouts'})"
        )

    documents: dict[str, ClosingDocument] = {}
    for record in _records(organization, "fechamento_recibo"):
        data = record.payload
        company = companies.get(str(data.get("empresa_id")))
        year, month = _int(data.get("ano")), _int(data.get("mes"))
        name = _text(data.get("nome_original") or data.get("arquivo"), 255)
        digest = _text(data.get("hash_arquivo"), 64)
        if not digest or not name:
            stats.skip("fechamento_recibo", "sem hash ou nome do arquivo")
            continue
        competence = date(year, month, 1) if year and month and 1 <= month <= 12 else None
        document = _live(ClosingDocument, record, "closing.ClosingDocument:")
        if document is None:
            document = ClosingDocument.objects.filter(
                organization=organization,
                content_hash=digest,
                company_id=company,
                competence=competence,
            ).first()
        if document is None:
            document = ClosingDocument.objects.create(
                organization=organization,
                # The PDF itself did not travel in the bundle: only what was read is kept.
                file="",
                original_name=name,
                content_hash=digest,
                state=(
                    ClosingDocument.State.ACCEPTED
                    if data.get("parseado_ok")
                    else ClosingDocument.State.QUARANTINE
                ),
                layout=layout_by_sigla.get(_text(data.get("obrigacao_sigla"), 80)),
                company_id=company,
                competence=competence,
                amount=_decimal(data.get("valor_principal")),
                icms=_decimal(data.get("valor_icms")),
                ipi=_decimal(data.get("valor_ipi")),
                iss=_decimal(data.get("valor_issqn")),
                iss_withheld=_decimal(data.get("valor_issqn_retido")),
                read_values=data.get("extras") if isinstance(data.get("extras"), dict) else {},
                text=str(data.get("texto_extraido") or ""),
                read_at=_datetime(data.get("criado_em")),
            )
            stats.created["documentos de fechamento"] += 1
        else:
            stats.reused["documentos de fechamento"] += 1
        documents[record.source_pk] = document
        marks.set(record, f"closing.ClosingDocument:{document.pk}")
    marks.flush()

    for record in _records(organization, "fechamento_conferencia"):
        data = record.payload
        document = documents.get(str(data.get("recibo_id")))
        if document is None:
            stats.skip(
                "fechamento_conferencia", "conferência sem recibo no pacote (recibo_id vazio)"
            )
            continue
        conference = _live(ClosingConference, record, "closing.ClosingConference:")
        if conference is None:
            conference = ClosingConference.objects.create(
                organization=organization,
                document=document,
                layout=document.layout,
                outcome=CONFERENCE_OUTCOME.get(
                    str(data.get("resultado") or "").upper(), ClosingConference.Outcome.READ
                ),
                declared_amount=_decimal(data.get("valor_declarado")),
                reference_amount=_decimal(data.get("valor_guia")),
                reference_source=(
                    ClosingConference.Source.DOCUMENT
                    if str(data.get("fonte_valor_guia")).upper() == "DOCUMENTO"
                    else ""
                ),
                note=_text(data.get("observacao"), 500),
            )
            stats.created["conferências de fechamento"] += 1
        else:
            stats.reused["conferências de fechamento"] += 1
        marks.set(record, f"closing.ClosingConference:{conference.pk}")
    marks.flush()


# ---- FAP / FGTS / DET -----------------------------------------------------------------------


def convert_fap(organization: Organization, stats: Stats) -> None:
    companies = mapped_ids(organization, "core_empresa", "hub.ClientCompany:")
    marks = _Marks()
    batches: dict[str, FapBatch] = {}
    for record in _records(organization, "fap_lotefap"):
        data = record.payload
        year = _int(data.get("ano"))
        if not year:
            stats.skip("fap_lotefap", "sem ano")
            continue
        batch = _live(FapBatch, record, "fap.FapBatch:")
        if batch is None:
            batch = FapBatch.objects.create(
                organization=organization,
                year=year,
                state=FAP_BATCH_STATE.get(str(data.get("estado")), FapBatch.State.ATTENTION),
                notice=_text(data.get("aviso"), 500),
            )
            stats.created["lotes FAP"] += 1
        else:
            stats.reused["lotes FAP"] += 1
        batches[record.source_pk] = batch
        marks.set(record, f"fap.FapBatch:{batch.pk}")
    marks.flush()
    pending: list[FapItem] = []
    pairs: dict[tuple[Any, str], str] = {}
    for record in _records(organization, "fap_itemfap"):
        data = record.payload
        batch = batches.get(str(data.get("lote_id")))
        code = _text(data.get("codigo_dominio"), 64)
        if batch is None or not code:
            stats.skip("fap_itemfap", "lote sem nativo ou sem código")
            continue
        key = (batch.pk, code)
        known = pairs.get(key)
        if known is None:
            existing = FapItem.objects.filter(batch=batch, code=code).first()
            if existing is None:
                made = FapItem(
                    organization=organization,
                    batch=batch,
                    company_id=companies.get(str(data.get("empresa_id"))),
                    code=code,
                    name=_text(data.get("nome_empresa"), 255),
                    cnpj=_digits(data.get("cnpj"))[:14],
                    year=batch.year,
                    state=FAP_ITEM_STATE.get(str(data.get("estado")), FapItem.State.FAILED),
                    message=_text(data.get("mensagem"), 500),
                    generation=max(_int(data.get("geracao")) or 1, 1),
                    sha256=_text(data.get("sha256_pdf"), 64),
                    validated_at=_datetime(data.get("validado_em")),
                )
                pending.append(made)
                known = str(made.pk)
                stats.created["itens FAP"] += 1
            else:
                known = str(existing.pk)
                stats.reused["itens FAP"] += 1
            pairs[key] = known
        marks.set(record, f"fap.FapItem:{known}")
        if len(pending) >= 500:
            FapItem.objects.bulk_create(pending)
            pending = []
    if pending:
        FapItem.objects.bulk_create(pending)
    marks.flush()


def convert_fgts(organization: Organization, stats: Stats) -> None:
    companies = mapped_ids(organization, "core_empresa", "hub.ClientCompany:")
    marks = _Marks()
    batches: dict[str, FgtsBatch] = {}
    for record in _records(organization, "fgts_lote"):
        data = record.payload
        year, month = _int(data.get("ano")), _int(data.get("mes"))
        if not year or not month or not 1 <= month <= 12:
            stats.skip("fgts_lote", "competência inválida")
            continue
        batch = _live(FgtsBatch, record, "fgts.FgtsBatch:")
        if batch is None:
            batch = FgtsBatch.objects.create(
                organization=organization,
                year=year,
                month=month,
                deadline=_date(data.get("data_limite")) or date(year, month, 20),
            )
            stats.created["lotes FGTS"] += 1
        else:
            stats.reused["lotes FGTS"] += 1
        batches[record.source_pk] = batch
        marks.set(record, f"fgts.FgtsBatch:{batch.pk}")
    marks.flush()
    for record in _records(organization, "fgts_item"):
        data = record.payload
        batch = batches.get(str(data.get("lote_id")))
        root = _digits(data.get("raiz_cnpj"))[:8]
        if batch is None or not root:
            stats.skip("fgts_item", "lote sem nativo ou sem raiz")
            continue
        item = (
            _live(FgtsItem, record, "fgts.FgtsItem:")
            or FgtsItem.objects.filter(batch=batch, root=root).first()
        )
        if item is None:
            expected = _decimal(data.get("valor_esperado")) or Decimal("0")
            portal = _decimal(data.get("valor_portal"))
            item = FgtsItem.objects.create(
                organization=organization,
                batch=batch,
                root=root,
                year=batch.year,
                month=batch.month,
                company_id=companies.get(str(data.get("empresa_id"))),
                company_name=_text(data.get("nome_empresa"), 255),
                representative_cnpj=_digits(data.get("cnpj_representante"))[:14],
                codes=list(data.get("codigos_empresa") or []),
                expected_cents=int(expected * 100),
                portal_cents=int(portal * 100) if portal is not None else None,
                portal_due=_date(data.get("vencimento_portal")),
                state=FGTS_ITEM_STATE.get(str(data.get("estado")), FgtsItem.State.FAILED),
                message=_text(data.get("mensagem"), 500),
                sha256=_text(data.get("sha256_pdf"), 64),
            )
            stats.created["itens FGTS"] += 1
        else:
            stats.reused["itens FGTS"] += 1
        marks.set(record, f"fgts.FgtsItem:{item.pk}")
    marks.flush()


def convert_det(organization: Organization, stats: Stats) -> None:
    marks = _Marks()
    for record in _records(organization, "det_consulta"):
        data = record.payload
        query = _live(DetQuery, record, "det.DetQuery:")
        if query is None:
            companies = [
                {
                    "code": _text(c.get("codigo"), 64),
                    "name": _text(c.get("razao_social"), 255),
                    "cnpj": _digits(c.get("cnpj"))[:14],
                }
                for c in (data.get("empresas") or [])
                if isinstance(c, dict)
            ]
            query = DetQuery.objects.create(
                organization=organization,
                state=DET_STATE.get(str(data.get("estado")), DetQuery.State.FAILED),
                companies=companies,
                total_messages=max(_int(data.get("total_mensagens")) or 0, 0),
                notice=_text(data.get("erro") or data.get("aviso"), 500),
            )
            seen: set[str] = set()
            results: list[DetResult] = []
            for item in data.get("resultados") or []:
                company = item.get("empresa") if isinstance(item, dict) else None
                if not isinstance(company, dict):
                    continue
                code = _text(company.get("codigo"), 64)
                if not code or code in seen:
                    continue
                seen.add(code)
                results.append(
                    DetResult(
                        organization=organization,
                        query=query,
                        company_code=code,
                        company_name=_text(company.get("razao_social"), 255),
                        cnpj=_digits(company.get("cnpj"))[:14],
                        situation=DET_SITUATION.get(
                            str(item.get("situacao")), DetResult.Situation.ERROR
                        ),
                        messages=item.get("mensagens") or [],
                        detail=_text(item.get("detalhe"), 1000),
                    )
                )
            DetResult.objects.bulk_create(results, batch_size=200)
            stats.created["consultas DET"] += 1
            stats.created["resultados DET"] += len(results)
        else:
            stats.reused["consultas DET"] += 1
        marks.set(record, f"det.DetQuery:{query.pk}")
    marks.flush()


# ---- payroll sheet and folder tree ----------------------------------------------------------


def _competence(value: Any) -> date | None:
    parts = str(value or "").split("/")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        month, year = int(parts[0]), int(parts[1])
        if 1 <= month <= 12 and year > 1999:
            return date(year, month, 1)
    return None


def convert_folha(organization: Organization, stats: Stats) -> None:
    marks = _Marks()
    for record in _records(organization, "relatorios_folha_titulorelatoriofolha"):
        data = record.payload
        key = _text(data.get("chave"), 24)
        if not key:
            stats.skip("relatorios_folha_titulorelatoriofolha", "sem chave")
            continue
        title, made = FolhaTitle.objects.get_or_create(
            organization=organization, key=key, defaults={"name": _text(data.get("nome"), 120)}
        )
        stats.created["títulos da folha"] += int(made)
        stats.reused["títulos da folha"] += int(not made)
        marks.set(record, f"folha.FolhaTitle:{title.pk}")
    for record in _records(organization, "relatorios_folha_atualizacaoplanilhafolha"):
        data = record.payload
        code = _text(data.get("empresa_codigo"), 64)
        competence = _competence(data.get("competencia"))
        stage = SHEET_STAGE.get(str(data.get("etapa") or ""))
        company = ClientCompany.objects.filter(organization=organization, dominio_code=code).first()
        if not code or competence is None or stage is None or company is None:
            stats.skip(
                "relatorios_folha_atualizacaoplanilhafolha", "empresa, mês ou etapa sem nativo"
            )
            continue
        done = str(data.get("estado")) == "feito"
        mark, made = FolhaSheetMark.objects.get_or_create(
            organization=organization,
            competence=competence,
            company_code=code,
            stage=stage,
            defaults={
                "company": company,
                "state": FolhaSheetMark.State.DONE if done else FolhaSheetMark.State.ERROR,
                "attempts": min(max(_int(data.get("tentativas")) or 0, 0), 32000),
                "error": _text(data.get("erro"), 300),
                "tab": _text(data.get("aba"), 60),
                "cell": _text(data.get("celula"), 20),
                "written_at": _datetime(data.get("gravado_em")),
            },
        )
        stats.created["marcas da planilha da folha"] += int(made)
        stats.reused["marcas da planilha da folha"] += int(not made)
        marks.set(record, f"folha.FolhaSheetMark:{mark.pk}")
    marks.flush()


def _tree(nodes: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        out.append(
            {
                "id": str(node.get("id") or ""),
                "name": str(node.get("nome") or ""),
                "variable": str(node.get("variavel") or ""),
                "use": str(node.get("uso") or ""),
                "children": _tree(node.get("filhos")),
            }
        )
    return out


def convert_folder_model(organization: Organization, stats: Stats) -> None:
    marks = _Marks()
    for record in _records(organization, "arquivos_modelopastas"):
        data = record.payload
        model = FolderModel.objects.filter(organization=organization).first()
        if model is None:
            model = FolderModel.objects.create(
                organization=organization,
                tree=_tree(data.get("arvore")),
                revision=max(_int(data.get("revisao")) or 1, 1),
                active=bool(data.get("ativo")),
            )
            stats.created["modelo de pastas"] += 1
        else:
            stats.reused["modelo de pastas"] += 1
        marks.set(record, f"triage.FolderModel:{model.pk}")
    marks.flush()


def convert_extra(
    organization: Organization, stats: Stats, *, activate_layouts: bool = False
) -> None:
    steps: list[Callable[[], None]] = [
        lambda: convert_closing(organization, stats, activate=activate_layouts),
        lambda: convert_fap(organization, stats),
        lambda: convert_fgts(organization, stats),
        lambda: convert_det(organization, stats),
        lambda: convert_folha(organization, stats),
        lambda: convert_folder_model(organization, stats),
    ]
    for step in steps:
        with transaction.atomic():
            step()
