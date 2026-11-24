"""Consultas de leitura do Contraprova: lista de conferências, abas e achados."""

from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet

from apps.organizations.models import Organization

from .engine.findings import DIVERGENT, IGNORED, INFO, Finding
from .engine.tools import TabDef, ToolDef
from .models import CrosscheckFinding, CrosscheckRun

PAGE_SIZE = 25
FINDINGS_PAGE_SIZE = 50

STATE_FILTERS = {
    "todas": None,
    "andamento": (CrosscheckRun.State.QUEUED, CrosscheckRun.State.PROCESSING),
    "divergencia": (CrosscheckRun.State.DONE,),
    "falha": (CrosscheckRun.State.FAILED,),
    "rascunho": (CrosscheckRun.State.DRAFT,),
}

KIND_LABELS = {
    "valor_divergente": "Valor diferente",
    "sem_xml": "Sem XML",
    "xml_nao_escriturado": "XML sem escrituração",
    "situacao_divergente": "Situação diferente",
    "chave_duplicada": "Chave repetida",
    "chave_invalida": "Chave inválida",
    "somente_1": "Só no SPED 1",
    "somente_2": "Só no SPED 2",
    "analitico_somente_1": "Analítico só no SPED 1",
    "analitico_somente_2": "Analítico só no SPED 2",
    "analitico_valor": "Analítico diferente",
    "icms51_chave": "ICMS 51",
    "icms51_aritmetica": "ICMS 51 não fecha",
    "uf_divergente": "UF diferente",
    "ausente_dominio": "Sem Domínio",
    "sem_uf_xml": "Sem UF no XML",
}


def visible_runs(organization: Organization, companies: QuerySet[Any]) -> QuerySet[CrosscheckRun]:
    return CrosscheckRun.objects.filter(organization=organization, company__in=companies)


def filter_runs(
    runs: QuerySet[CrosscheckRun], *, q: str, tool: str, state: str
) -> QuerySet[CrosscheckRun]:
    if q:
        runs = runs.filter(Q(company__name__icontains=q) | Q(company__cnpj_masked__icontains=q))
    if tool:
        runs = runs.filter(tool=tool)
    states = STATE_FILTERS.get(state)
    if states:
        runs = runs.filter(state__in=states)
        if state == "divergencia":
            runs = runs.filter(divergent_count__gt=0)
    return runs.select_related("company")


def tab_filter(tab: TabDef) -> Q:
    """Achados de uma aba: por tipo e situação; a aba de ignoradas olha só a situação."""

    if not tab.kinds:
        return Q(status__in=tab.statuses)
    return Q(kind__in=tab.kinds, status__in=tab.statuses)


def tab_counts(run: CrosscheckRun, tool: ToolDef) -> dict[str, int]:
    """Contagem por aba a partir do resumo gravado: certa mesmo quando o banco foi cortado."""

    by_kind: dict[str, int] = {}
    for key, total in (run.summary.get("by_kind") or {}).items():
        by_kind[str(key)] = int(total)
    counts: dict[str, int] = {}
    for tab in tool.tabs:
        total = 0
        for key, value in by_kind.items():
            kind, _, status = key.rpartition(":")
            if status not in tab.statuses:
                continue
            if tab.kinds and kind not in tab.kinds:
                continue
            total += value
        counts[tab.code] = total
    return counts


def findings_for_tab(
    run: CrosscheckRun,
    tab: TabDef,
    *,
    q: str = "",
    field: str = "",
    cfop: str = "",
    operation: str = "",
) -> QuerySet[CrosscheckFinding]:
    rows = CrosscheckFinding.objects.filter(run=run).filter(tab_filter(tab))
    if q:
        rows = rows.filter(Q(doc_key__icontains=q) | Q(number__icontains=q))
    if field:
        rows = rows.filter(field=field)
    if cfop:
        rows = rows.filter(cfop__icontains=cfop)
    if operation in {"E", "S"}:
        rows = rows.filter(operation=operation)
    return rows.order_by("seq")


def field_options(run: CrosscheckRun, tab: TabDef) -> list[tuple[str, str]]:
    """Campos que aparecem nesta aba, para o filtro."""

    rows = (
        CrosscheckFinding.objects.filter(run=run)
        .filter(tab_filter(tab))
        .exclude(field="")
        .values_list("field", "field_label")
        .distinct()
        .order_by("field_label")[:40]
    )
    return list(rows)


def to_finding(row: CrosscheckFinding) -> Finding:
    return Finding(
        kind=row.kind,
        status=row.status,
        doc_key=row.doc_key,
        doc_type=row.doc_type,
        number=row.number,
        field=row.field,
        field_label=row.field_label,
        left_cents=row.left_cents,
        right_cents=row.right_cents,
        left_text=row.left_text,
        right_text=row.right_text,
        cfop=row.cfop,
        operation=row.operation,
        message=row.message,
        detail=row.detail,
    )


STATUS_LABELS = {DIVERGENT: "Divergente", IGNORED: "Ignorada por regra", INFO: "Informativa"}
