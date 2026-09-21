from __future__ import annotations

from dataclasses import dataclass

from apps.hub.models import ProductModule


@dataclass(frozen=True)
class ModuleDefinition:
    code: str
    label: str
    short_label: str
    description: str
    route_name: str
    required_capabilities: tuple[str, ...]
    icon: str


MODULES: dict[str, ModuleDefinition] = {
    ProductModule.Code.NFSE: ModuleDefinition(
        code=ProductModule.Code.NFSE,
        label="NFS-e Inteligente",
        short_label="NFS-e",
        description=(
            "Organize, classifique e acompanhe documentos recebidos pela integração homologada."
        ),
        route_name="hub:nfse-center",
        required_capabilities=("companies", "fiscal_documents"),
        icon="NF",
    ),
    ProductModule.Code.GUIDES: ModuleDefinition(
        code=ProductModule.Code.GUIDES,
        label="Guias e DCTFWeb",
        short_label="Guias",
        description="Organize vencimentos, transmissões e pendências fiscais em um só lugar.",
        route_name="hub:guides",
        required_capabilities=("companies", "obligations"),
        icon="GU",
    ),
    ProductModule.Code.INTEGRA: ModuleDefinition(
        code=ProductModule.Code.INTEGRA,
        label="Central Integra Contador",
        short_label="Integra",
        description="Acompanhe solicitações e retornos enviados ao Integra Contador.",
        route_name="hub:integra",
        # The platform, not the office, contracts and configures Serpro.
        required_capabilities=(),
        icon="IC",
    ),
    ProductModule.Code.RECONCILIATION: ModuleDefinition(
        code=ProductModule.Code.RECONCILIATION,
        label="Conciliação OFX x Domínio",
        short_label="Conciliação",
        description="Compare extratos bancários com o Domínio e trate divergências.",
        route_name="hub:reconciliation",
        required_capabilities=("bank_statements", "accounting_entries"),
        icon="OF",
    ),
    ProductModule.Code.REFORM: ModuleDefinition(
        code=ProductModule.Code.REFORM,
        label="Radar da Reforma Tributária",
        short_label="Radar",
        description="Acompanhe publicações fiscais relevantes em fontes oficiais.",
        route_name="hub:reform",
        required_capabilities=(),
        icon="RT",
    ),
    ProductModule.Code.AI: ModuleDefinition(
        code=ProductModule.Code.AI,
        label="Copiloto CICA",
        short_label="Copiloto",
        description="Analise o contexto autorizado de uma empresa com fontes e limites claros.",
        route_name="intelligence:assistant",
        required_capabilities=(),
        icon="IA",
    ),
    ProductModule.Code.TRIAGE: ModuleDefinition(
        code=ProductModule.Code.TRIAGE,
        label="Triagem de Arquivos",
        short_label="Triagem",
        description=(
            "Receba documentos por e-mail, identifique empresa e período, e arquive com revisão."
        ),
        route_name="hub:triage",
        required_capabilities=(),
        icon="TR",
    ),
}


OFFERED_MODULE_CODES: tuple[str, ...] = tuple(
    code for code in ProductModule.Code.values if code != ProductModule.Code.JOURNEY
)
OFFERED_MODULE_CHOICES: tuple[tuple[str, str], ...] = tuple(
    (str(code), str(label))
    for code, label in ProductModule.Code.choices
    if code in OFFERED_MODULE_CODES
)


def definition(code: str) -> ModuleDefinition:
    return MODULES[code]
