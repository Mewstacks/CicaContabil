"""Folder model of an office: tree validation, rule resolution, provisioning plans.

No filesystem access here. The tree describes what lives under each client folder; the
Windows agent is the only writer, through ``AgentFolderJob`` (create directories) and
``AgentFileJob`` (place a file). Every path produced is relative and re-validated.

Pattern references (structure only, no code copied): paperless-ngx storage paths
(template placeholders, rejects absolute paths and ``..``, collision counters) and the
HubFedrizzi folder model this was ported from.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from collections.abc import Iterator
from datetime import date
from pathlib import PureWindowsPath
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.hub.models import ClientCompany, CompanyPartner
from apps.organizations.models import Organization
from apps.triage.models import (
    AgentFolderJob,
    ClientFolder,
    DestinationProfile,
    DocumentType,
    FolderModel,
    ObligationFolderRule,
    TriageItem,
)
from apps.triage.windows_paths import company_folder_component

MAX_NODES = 500
MAX_DEPTH = 12
MAX_PATH_LENGTH = 240
MAX_PLAN_DIRS = 400
VARIABLES = frozenset({"", "ano", "mes", "funcionario", "data"})
USES = frozenset({"", "folha", "dissidio", "decimo_terceiro", "fap", "socios"})
_FORBIDDEN = frozenset('<>:"/\\|?*')
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{n}" for n in range(1, 10)}
    | {f"LPT{n}" for n in range(1, 10)}
)

# Office PDF hierarchy (HubFedrizzi arquivos/modelo_inicial.py); names only, no restrictions.
_LINES = """
1 SOCIETARIO
1.1 DOCUMENTOS PESSOAIS
1.2 DOCUMENTOS EMPRESA
1.3 CONTRATO SOCIAL E ALTERACOES
1.4 CONTRATOS PRESTACAO SERVICOS
1.5 REGULARIDADES
1.6 PROCESSOS
1.7 REQUERIMENTOS E PROCURACOES
2 FOLHA DE PAGAMENTO
2.1 APURACOES
2.1.1 ANO
2.1.1.1 MES
2.1.1.2 DISSIDIO
2.1.1.3 DECIMO TERCEIRO
2.2 FUNCIONARIOS
2.2.1 NOME
2.2.1.1 ADMISSAO
2.2.1.1.1 DOCUMENTOS
2.2.1.2 FERIAS
2.2.1.2.1 DATA - 00.00.0000
2.2.1.3 DIVERSOS
2.2.1.4 RESCISAO
2.3 PARTICULARIDADES
2.3.1 FOLHA PONTO
2.3.1.1 ANO
2.3.1.1.1 MES
2.3.2 FAP
2.3.3 SINDICATO
2.3.4 SST - SAUDE E SEGURANCA DO TRABALHADOR
2.3.4.1 PLANO DE SAUDE
2.3.4.1.1 ANO
2.3.4.2 LAUDOS
2.3.4.2.1 ANO
2.3.4.3 CAT
2.3.4.3.1 ANO
2.3.4.4 ATESTADOS
2.3.4.4.1 ANO
2.3.7 SIMULACOES
2.3.8 ATAS ADMINISTRATIVAS
2.3.8.1 ANO
2.3.9 FISCALIZACAO
2.3.10 INFORMACOES PARA FECHAMENTO
3 FISCAL
3.1 APURACOES
3.1.1 PLANILHA FECHAMENTO ANUAL
3.1.2 RELATORIOS FECHAMENTO MENSAL
3.1.2.1 ANO
3.1.2.1.1 MES
3.2 PARTICULARIDADES
3.2.1 TRIBUTACAO E BENEFICIOS
3.2.2 ROTINAS DE FECHAMENTO
4 CONTABIL
4.1 EXTRATOS
4.1.1 ANO
4.1.1.1 MES
4.2 IMOBILIZADO
4.2.1 TERRENOS
4.2.2 PREDIOS
4.2.3 MAQUINAS E EQUIPAMENTOS
4.2.4 FERRAMENTAS
4.2.5 EQUIPAMENTOS E SISTEMA DE SEGURANCA
4.2.6 MATRIZES E MOLDES
4.2.7 INSTALACOES ELETRICAS
4.2.8 INSTALACOES TELEFONICAS
4.2.9 APARELHOS DE MEDICAO
4.2.10 MOVEIS E UTENSILIOS INDUSTRIAIS
4.2.11 MOVEIS E UTENSILIOS
4.2.12 EQUIPAMENTOS DE ENERGIA-FORCA
4.2.13 VEICULOS
4.2.14 INSTALACOES INDUSTRIAIS
4.2.15 INSTALACOES ADMINISTRATIVAS
4.2.16 TRATORES
4.2.17 COMPUTADORES E PERIFERICOS
4.2.18 APARELHOS TELEFONICOS
4.2.19 EQUIPAMENTOS PARA LABORATORIO
4.2.20 MARCAS E PATENTES
4.2.21 SISTEMAS DE DADOS SOFTWARE
4.2.22 PROGRAMAS COMPUTADORES
4.3 APURACOES
4.3.1 ANO
4.3.1.1 MES
4.4 PARTICULARIDADES
4.5 DEMONSTRACOES
4.5.1 ANO
5 PARCELAMENTOS
5.1 COMPROVANTES
5.1.1 ANO
5.2 PARCELAS
5.2.1 ANO
5.2.1.1 MES
6 COMPENSACOES E RESTITUICOES
6.1 CONTROLE
6.2 EM ANDAMENTO
6.2.1 ANO
6.3 COMPENSADO
6.3.1 ANO
6.4 RESTITUIDO
6.4.1 ANO
7 DECLARACOES E RECIBOS
7.1 ANO
7.1.1 MES
7.1.2 INFORME DE RENDIMENTOS
7.1.3 DEMAIS DECLARACOES
8 IMPOSTOS
8.1 ANO
8.1.1 MES
9 FINANCEIRO
9.1 HONORARIO
9.1.1 ANO
9.1.1.1 MES
10 TEMPORARIO
"""

Node = dict[str, Any]


def seed_tree() -> list[Node]:
    """The office's initial 111-node hierarchy, with stable node ids."""
    variables = {"ANO": "ano", "MES": "mes", "NOME": "funcionario", "DATA - 00.00.0000": "data"}
    uses = {
        "1.1": "socios",
        "2.1.1.1": "folha",
        "2.1.1.2": "dissidio",
        "2.1.1.3": "decimo_terceiro",
        "2.3.2": "fap",
    }
    roots: list[Node] = []
    index: dict[str, Node] = {}
    for line in _LINES.strip().splitlines():
        code, name = line.split(" ", 1)
        node: Node = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "cica-pastas/" + code)),
            "name": name,
            "variable": variables.get(name, ""),
            "use": uses.get(code, ""),
            "children": [],
        }
        index[code] = node
        (index[code.rsplit(".", 1)[0]]["children"] if "." in code else roots).append(node)
    return roots


def validate_component(name: str) -> str:
    """One portable Windows folder name: no separators, controls, reserved names."""
    value = unicodedata.normalize("NFC", str(name)).strip()
    if (
        not value
        or value != value.rstrip(". ")
        or value in {".", ".."}
        or len(value) > 120
        or any(c in _FORBIDDEN or unicodedata.category(c).startswith("C") for c in value)
        or value.split(".", 1)[0].upper() in _RESERVED
    ):
        raise ValidationError("Nome de pasta inválido.")
    return value


def iter_nodes(
    tree: list[Node], parents: tuple[Node, ...] = ()
) -> Iterator[tuple[Node, tuple[Node, ...]]]:
    for node in tree:
        yield node, parents
        yield from iter_nodes(node.get("children", []), (*parents, node))


def validate_tree(tree: object) -> list[Node]:
    """Reject anything that could escape the client folder or collide on disk."""
    if not isinstance(tree, list):
        raise ValidationError("Modelo de pastas inválido.")
    seen_ids: set[str] = set()
    count = 0

    def walk(nodes: object, depth: int) -> None:
        nonlocal count
        if not isinstance(nodes, list) or depth > MAX_DEPTH:
            raise ValidationError("Modelo de pastas inválido.")
        names: set[str] = set()
        for node in nodes:
            if not isinstance(node, dict):
                raise ValidationError("Modelo de pastas inválido.")
            count += 1
            if count > MAX_NODES:
                raise ValidationError("Pastas demais no modelo.")
            node_id = str(node.get("id", ""))
            try:
                uuid.UUID(node_id)
            except ValueError as exc:
                raise ValidationError("Identificador de pasta inválido.") from exc
            if node_id in seen_ids:
                raise ValidationError("Identificador de pasta repetido.")
            seen_ids.add(node_id)
            if node.get("variable", "") not in VARIABLES or node.get("use", "") not in USES:
                raise ValidationError("Variável de pasta inválida.")
            if not node.get("variable"):
                validate_component(node.get("name", ""))
            folded = str(node.get("name", "")).casefold()
            if folded in names:
                raise ValidationError("Nome de pasta repetido no mesmo nível.")
            names.add(folded)
            walk(node.get("children", []), depth + 1)

    walk(tree, 1)
    return tree


def find_node(tree: list[Node], node_id: str) -> tuple[Node, tuple[Node, ...]]:
    for node, parents in iter_nodes(tree):
        if node["id"] == node_id:
            return node, parents
    raise ValidationError("Pasta do modelo não encontrada.")


def active_model(organization: Organization) -> FolderModel | None:
    return FolderModel.objects.filter(organization=organization, active=True).first()


def ensure_model(organization: Organization) -> FolderModel:
    model, _ = FolderModel.objects.get_or_create(
        organization=organization, defaults={"tree": seed_tree()}
    )
    return model


def save_tree(model: FolderModel, tree: object, *, active: bool | None = None) -> FolderModel:
    """Replace the tree and bump the revision."""
    model.tree = validate_tree(tree)
    model.revision += 1
    if active is not None:
        model.active = active
    model.save(update_fields=["tree", "revision", "active", "updated_at"])
    return model


def _variable_value(
    node: Node, *, year: int | None, month: int | None, employee: str, day: date | None
) -> str:
    kind = node["variable"]
    if kind == "ano" and year:
        return f"{year:04d}"
    if kind == "mes" and month:
        return f"{month:02d}"
    if kind == "funcionario" and employee:
        return validate_component(_UNSAFE.sub("-", employee).strip(" ."))
    if kind == "data" and day:
        return day.strftime("%d.%m.%Y")
    raise ValidationError("Faltam dados do arquivo para montar a pasta.")


def _checked(path: str) -> str:
    relative = PureWindowsPath(path)
    if (
        relative.is_absolute()
        or relative.drive
        or ".." in relative.parts
        or any(not part for part in relative.parts)
        or len(path) > MAX_PATH_LENGTH
    ):
        raise ValidationError("Destino de pasta inválido.")
    return str(relative)


def node_relative_path(
    tree: list[Node],
    node_id: str,
    company: ClientCompany,
    *,
    year: int | None = None,
    month: int | None = None,
    employee: str = "",
    day: date | None = None,
) -> str:
    """``<company folder>\\<node path>`` with variable levels filled; always relative."""
    node, parents = find_node(tree, node_id)
    parts = [company_folder_component(company_name=company.name, dominio_code=company.dominio_code)]
    for step in (*parents, node):
        if step["variable"]:
            parts.append(_variable_value(step, year=year, month=month, employee=employee, day=day))
        else:
            parts.append(validate_component(step["name"]))
    return _checked("\\".join(parts))


def document_kind(document_type: DocumentType | None) -> str:
    code = (document_type.code if document_type else "").casefold()
    if "recibo" in code:
        return ObligationFolderRule.Kind.RECEIPT
    if "guia" in code or "darf" in code or "das" in code.split("-"):
        return ObligationFolderRule.Kind.GUIDE
    return ObligationFolderRule.Kind.OTHER


def _rule_for(item: TriageItem) -> ObligationFolderRule | None:
    if item.document_type is None:
        return None
    kind = document_kind(item.document_type)
    rules = ObligationFolderRule.objects.filter(
        organization=item.organization, document_type=item.document_type, enabled=True
    )
    # An exact manual rule beats a learned one, which beats the "other" fallback.
    for candidate in (
        rules.filter(kind=kind, source="manual"),
        rules.filter(kind=kind, source="learned"),
        rules.filter(kind="other", source="manual"),
        rules.filter(kind="other", source="learned"),
    ):
        found = candidate.first()
        if found:
            return found
    return None


def resolve_destination(
    item: TriageItem,
    profile: DestinationProfile,
    *,
    explicit_node_id: str = "",
    employee: str = "",
) -> str | None:
    """Relative folder (no file name) from the folder model, or ``None`` to fall back.

    Precedence: node chosen by a person > manual rule > learned rule.
    """
    if not profile.folder_model_enabled or item.company is None:
        return None
    model = active_model(item.organization)
    if model is None:
        return None
    if not explicit_node_id:
        rule = _rule_for(item)
        if rule is None:
            return None
        explicit_node_id = rule.node_id
    day = item.period_start or item.period_end
    return node_relative_path(
        model.tree,
        explicit_node_id,
        item.company,
        year=day.year if day else None,
        month=day.month if day else None,
        employee=employee,
        day=day,
    )


def learn_rule(item: TriageItem, node_id: str) -> ObligationFolderRule | None:
    """Remember the node a person chose for this type; never overrides a manual rule."""
    if item.document_type is None:
        return None
    model = active_model(item.organization)
    if model is None:
        return None
    node, parents = find_node(model.tree, node_id)
    if any(step["variable"] == "funcionario" for step in (*parents, node)):
        return None
    rule, created = ObligationFolderRule.objects.get_or_create(
        organization=item.organization,
        document_type=item.document_type,
        kind=document_kind(item.document_type),
        defaults={"node_id": node_id, "source": ObligationFolderRule.Source.LEARNED},
    )
    if not created and rule.source == ObligationFolderRule.Source.LEARNED:
        rule.node_id = node_id
        rule.save(update_fields=["node_id", "updated_at"])
    return rule


def provision_plan(company: ClientCompany, tree: list[Node]) -> list[str]:
    """Directories to create for a company: the client folder, every fixed branch (no
    variable level above it) and one folder per partner under the ``socios`` node."""
    base = company_folder_component(company_name=company.name, dominio_code=company.dominio_code)
    out = [base]
    partner_roots: list[str] = []
    for node, parents in iter_nodes(tree):
        chain = (*parents, node)
        if any(step["variable"] for step in chain):
            continue
        path = "\\".join([base, *(step["name"] for step in chain)])
        out.append(_checked(path))
        if node["use"] == "socios":
            partner_roots.append(path)
    if partner_roots:
        for partner in CompanyPartner.objects.filter(company=company).order_by("name"):
            try:
                folder = validate_component(
                    re.sub(r"\s+", " ", _UNSAFE.sub(" ", partner.name)).strip(" .")
                )
            except ValidationError:
                continue
            out.extend(_checked(f"{root}\\{folder}") for root in partner_roots)
    if len(out) > MAX_PLAN_DIRS:
        raise ValidationError("Plano de pastas grande demais.")
    return out


def queue_provision(
    organization: Organization, *, company: ClientCompany | None = None, apply: bool = False
) -> list[tuple[ClientCompany, list[str]]]:
    """Plan (and with ``apply`` queue) folder creation. Idempotent: a company with a queued
    or claimed job, or already created with the same plan, is not queued twice."""
    model = active_model(organization)
    if model is None:
        raise ValidationError("Ative o modelo de pastas antes de provisionar.")
    companies = ClientCompany.objects.filter(organization=organization, active=True)
    if company is not None:
        companies = companies.filter(pk=company.pk)
    plans: list[tuple[ClientCompany, list[str]]] = []
    for item in companies.exclude(dominio_code="").order_by("name"):
        try:
            plan = provision_plan(item, model.tree)
        except ValidationError:
            continue
        plans.append((item, plan))
        if not apply:
            continue
        with transaction.atomic():
            folder, _ = ClientFolder.objects.get_or_create(
                organization=organization, company=item, defaults={"relative_path": plan[0]}
            )
            jobs = AgentFolderJob.objects.filter(
                organization=organization, company=item, kind=AgentFolderJob.Kind.PROVISION
            )
            if jobs.filter(
                status__in=[AgentFolderJob.Status.QUEUED, AgentFolderJob.Status.CLAIMED]
            ).exists():
                continue
            if (
                folder.state == ClientFolder.State.CREATED
                and jobs.filter(status=AgentFolderJob.Status.DONE, paths=plan).exists()
            ):
                continue
            folder.relative_path = plan[0]
            folder.state = ClientFolder.State.PENDING
            folder.last_error = ""
            folder.save(update_fields=["relative_path", "state", "last_error", "updated_at"])
            AgentFolderJob.objects.create(
                organization=organization,
                company=item,
                kind=AgentFolderJob.Kind.PROVISION,
                paths=plan,
            )
    return plans


def queue_inventory(organization: Organization) -> AgentFolderJob:
    """Read-only listing of what sits under the root (reorganization dry run)."""
    existing = AgentFolderJob.objects.filter(
        organization=organization,
        kind=AgentFolderJob.Kind.INVENTORY,
        status__in=[AgentFolderJob.Status.QUEUED, AgentFolderJob.Status.CLAIMED],
    ).first()
    return existing or AgentFolderJob.objects.create(
        organization=organization, kind=AgentFolderJob.Kind.INVENTORY, paths=["."]
    )


def mark_job_result(job: AgentFolderJob, *, success: bool, detail: str) -> None:
    if job.company_id and job.kind == AgentFolderJob.Kind.PROVISION:
        ClientFolder.objects.filter(
            organization=job.organization, company_id=job.company_id
        ).update(
            state=ClientFolder.State.CREATED if success else ClientFolder.State.FAILED,
            last_error="" if success else detail[:500],
            provisioned_at=timezone.now() if success else None,
        )
