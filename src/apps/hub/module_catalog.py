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
    connector_kind: str | None
    icon: str


MODULES: dict[str, ModuleDefinition] = {
    ProductModule.Code.NFSE: ModuleDefinition(
        code=ProductModule.Code.NFSE,
        label="NFS-e Inteligente",
        short_label="NFS-e",
        description="Capture, classifique e acompanhe documentos de serviço desta empresa.",
        route_name="hub:nfse-center",
        connector_kind="dominio_agent",
        icon="NF",
    ),
    ProductModule.Code.GUIDES: ModuleDefinition(
        code=ProductModule.Code.GUIDES,
        label="Guias e DCTFWeb",
        short_label="Guias",
        description="Organize vencimentos, transmissões e pendências fiscais em um só lugar.",
        route_name="hub:guides",
        connector_kind="dominio_agent",
        icon="GU",
    ),
    ProductModule.Code.INTEGRA: ModuleDefinition(
        code=ProductModule.Code.INTEGRA,
        label="Central Integra Contador",
        short_label="Integra",
        description="Acompanhe solicitações e retornos enviados ao Integra Contador.",
        route_name="hub:integra",
        connector_kind="integra",
        icon="IC",
    ),
    ProductModule.Code.RECONCILIATION: ModuleDefinition(
        code=ProductModule.Code.RECONCILIATION,
        label="Conciliação OFX x Domínio",
        short_label="Conciliação",
        description="Compare extratos bancários com o Domínio e trate divergências.",
        route_name="hub:reconciliation",
        connector_kind="dominio_agent",
        icon="OF",
    ),
    ProductModule.Code.REFORM: ModuleDefinition(
        code=ProductModule.Code.REFORM,
        label="Radar da Reforma Tributária",
        short_label="Radar",
        description="Veja mudanças relevantes e o impacto potencial para esta empresa.",
        route_name="hub:reform",
        connector_kind=None,
        icon="RT",
    ),
}


def definition(code: str) -> ModuleDefinition:
    return MODULES[code]
