"""Task-based workspace navigation, independent of commercial module names."""

from __future__ import annotations

from typing import Any

from django.urls import reverse


def workspace_navigation(context: Any) -> list[dict[str, Any]]:
    request = context["request"]
    route = request.resolver_match.url_name if request.resolver_match else ""
    codes = {module.code for module in context.get("enabled_modules", [])}
    membership = context.get("membership")

    def link(
        label: str,
        name: str,
        description: str = "",
        *,
        routes: tuple[str, ...] = (),
        fragment: str = "",
    ) -> dict[str, Any]:
        return {
            "label": label,
            "url": reverse(name) + fragment,
            "description": description,
            "active": route in (name.split(":")[-1], *routes) and not fragment,
        }

    groups: list[dict[str, Any]] = []

    def group(key: str, label: str, links: list[dict[str, Any]]) -> None:
        if links:
            groups.append(
                {
                    "key": key,
                    "label": label,
                    "links": links,
                    "active": any(item["active"] for item in links),
                }
            )

    group(
        "registry",
        "Cadastros",
        [
            link(
                "Empresas",
                "hub:companies",
                "Carteira e dados de cada empresa",
                routes=("company-detail",),
            ),
            link("Certificados", "hub:certificates", "Validade e acesso por empresa"),
        ],
    )
    fiscal = []
    if "nfse" in codes:
        fiscal.append(
            link(
                "NFS-e",
                "hub:nfse-center",
                "Notas, revisões e coleta automática",
                routes=("reviews", "review-detail"),
            )
        )
    if "guides" in codes:
        fiscal.append(
            link(
                "Guias e DCTFWeb",
                "hub:guides",
                "Apurações, documentos e vencimentos",
                routes=("guide-detail", "dctfweb-consult", "dctfweb-bulk-consult"),
            )
        )
    if "integra" in codes:
        fiscal.extend(
            [
                link(
                    "Caixa DTE",
                    "hub:dte-center",
                    "Abrir mensagens, prazos e consultas por empresa",
                    routes=("dte-message-detail",),
                ),
                link("Parcelamentos", "hub:parcelamentos", "Acordos, parcelas e guias"),
                link(
                    "Central Integra Contador",
                    "hub:integra",
                    "Escolher outra rotina da Receita: DTE, parcelamentos ou DCTFWeb",
                ),
            ]
        )
    if "reform" in codes:
        fiscal.append(link("Reforma tributária", "hub:reform", "Publicações e mudanças fiscais"))
    group("fiscal", "Fiscal", fiscal)
    group(
        "accounting",
        "Contábil",
        [link("Conciliação bancária", "hub:reconciliation", "Conferir extratos OFX com o Domínio")]
        if "reconciliation" in codes
        else [],
    )
    group(
        "documents",
        "Documentos",
        [
            link(
                "Triagem de arquivos",
                "hub:triage",
                "Conferir e organizar anexos recebidos",
                routes=("triage-item",),
            ),
            link("Caixas de e-mail", "hub:triage-connections", "Origens dos arquivos da triagem"),
        ]
        if "triage" in codes
        else [],
    )
    settings = [
        link("Integrações", "hub:settings", "Conexões e configuração do escritório"),
        link(
            "Consumo e contrato",
            "hub:settings",
            "Franquias, limites e contratação",
            fragment="#consumo",
        ),
    ]
    if membership and membership.role in {"owner", "admin"}:
        settings.append(link("Equipe e acessos", "hub:team", "Pessoas e permissões"))
    settings.append(link("Primeiros passos", "hub:setup", "Preparar o escritório para operar"))
    group("settings", "Configurações", settings)
    return groups
