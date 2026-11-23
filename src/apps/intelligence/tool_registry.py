"""Registro único de ferramentas do copiloto e do MCP (E12).

Uma ferramenta declara o que é: módulo que o escritório precisa ter contratado, capacidade do
papel, classe de efeito, custo, formato e se pode sair para um cliente MCP externo. O copiloto
do Hub, o endpoint MCP interno e o gateway externo consomem o MESMO catálogo: lista e chamada
nunca divergem, e uma ferramenta nova nasce fechada (`external=False`, `copilot=False`).

Este módulo só descreve e filtra. Executar continua com o dono de cada ferramenta (`call_tool`
em `intelligence/mcp.py`, `integra/tools.py`); o registro não chama rede nem o Serpro.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from django.core.exceptions import ValidationError

from apps.common.cnpj import cnpj_candidates, normalize_cnpj


class Effect(StrEnum):
    """O que a chamada faz do lado de fora (docs/pesquisa/serpro-integra-contador-mcp.md, 1.3)."""

    READ = "read"  # só lê
    LEGAL_READ = "legal_read"  # lê, mas registra ciência jurídica (ex.: MSGDETALHAMENTO62)
    DOCUMENT = "document"  # emite documento ou guia sem mudar situação fiscal
    WRITE = "write"  # grava ou declara: nunca sem confirmação humana


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    module: str = ""  # código do `ProductModule`; vazio = sempre disponível
    capability: str = "read"
    effect: Effect = Effect.READ
    cost_cents: int = 0  # custo efetivo por chamada em centavos de real (0 = gratuita)
    response_format: str = "json"
    copilot: bool = False
    external: bool = False
    needs_confirmation: bool = False
    tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if self.effect != Effect.READ and not self.needs_confirmation:
            raise ValueError(f"{self.name}: efeito {self.effect} exige confirmação humana")
        if self.effect in {Effect.LEGAL_READ, Effect.WRITE} and self.external:
            raise ValueError(f"{self.name}: efeito {self.effect} nunca sai para cliente externo")
        if self.cost_cents < 0:
            raise ValueError(f"{self.name}: custo negativo")

    def as_mcp(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> ToolSpec:
        if spec.name in self._tools:
            raise ValueError(f"ferramenta duplicada: {spec.name}")
        self._tools[spec.name] = spec
        return spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def all(self) -> list[ToolSpec]:
        return sorted(self._tools.values(), key=lambda spec: spec.name)

    def available(
        self,
        *,
        modules: set[str] | None,
        capabilities: set[str],
        surface: str,
        budget_cents: int | None = None,
    ) -> list[ToolSpec]:
        """Ferramentas que ESTE escritório e ESTE papel podem ver nesta superfície.

        `modules=None` é escopo completo (papel dono/admin sem fronteira explícita);
        `surface` é `"copilot"` ou `"external"`. Com `budget_cents`, ferramenta paga cujo custo
        não cabe no que resta do orçamento não aparece.
        """

        if surface not in {"copilot", "external"}:
            raise ValueError("superfície desconhecida")
        visible = []
        for spec in self.all():
            if not (spec.copilot if surface == "copilot" else spec.external):
                continue
            if spec.capability not in capabilities:
                continue
            if spec.module and modules is not None and spec.module not in modules:
                continue
            if budget_cents is not None and spec.cost_cents > budget_cents:
                continue
            visible.append(spec)
        return visible

    def allowed_names(self, **kwargs: Any) -> frozenset[str]:
        return frozenset(spec.name for spec in self.available(**kwargs))


REGISTRY = ToolRegistry()

_COMPANY = {
    "type": "object",
    "properties": {"company_id": {"type": "string"}},
    "required": ["company_id"],
    "additionalProperties": False,
}
_QUERY = {
    "type": "object",
    "properties": {"query": {"type": "string", "maxLength": 300}},
    "required": ["query"],
    "additionalProperties": False,
}
_DOCUMENT = {
    "type": "object",
    "properties": {"value": {"type": "string", "maxLength": 64}},
    "required": ["value"],
    "additionalProperties": False,
}

# Ferramentas públicas e gratuitas: não passam por Serpro nem por procuração, não carregam dado
# de cliente (a entrada é o próprio documento que o usuário digitou).
REGISTRY.register(
    ToolSpec(
        name="validate_cnpj",
        description="Valida um CNPJ numérico ou alfanumérico (dígitos verificadores).",
        input_schema=_DOCUMENT,
        copilot=True,
        external=True,
        tags=frozenset({"public"}),
    )
)
REGISTRY.register(
    ToolSpec(
        name="validate_access_key",
        description="Valida a chave de acesso de 44 dígitos de NF-e, CT-e ou NFC-e, offline.",
        input_schema=_DOCUMENT,
        copilot=True,
        external=True,
        tags=frozenset({"public"}),
    )
)
REGISTRY.register(
    ToolSpec(
        name="find_cnpjs_in_text",
        description="Acha CNPJs (inclusive alfanuméricos válidos) dentro de um texto.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string", "maxLength": 4000}},
            "required": ["text"],
            "additionalProperties": False,
        },
        copilot=True,
        external=True,
        tags=frozenset({"public"}),
    )
)

# As oito ferramentas do MCP interno (`intelligence/mcp.py`) entram no catálogo com o mesmo
# nome; a seleção externa continua sendo as seis de leitura do gateway.
for _name, _schema, _desc in (
    (
        "search_data_catalog",
        _QUERY,
        "Busca fontes de negócio autorizadas no catálogo do escritório.",
    ),
    ("retrieve_knowledge", _QUERY, "Recupera cartões curtos de fonte aprovada."),
    ("get_company_context", _COMPANY, "Contexto compacto de uma empresa permitida."),
    ("get_risk_snapshot", _COMPANY, "Resume revisões abertas de uma empresa permitida."),
    ("list_obligations", _COMPANY, "Lista obrigações a partir do espelho privado."),
    ("explain_classification", _COMPANY, "Explica a sugestão de classificação por evidência."),
):
    REGISTRY.register(
        ToolSpec(
            name=_name,
            description=_desc,
            input_schema=_schema,
            module="ai",
            copilot=True,
            external=True,
        )
    )
REGISTRY.register(
    ToolSpec(
        name="create_classification_draft",
        description="Cria só um rascunho revisável no Hub, depois de confirmação explícita.",
        input_schema={
            "type": "object",
            "properties": {
                "company_id": {"type": "string"},
                "conversation_id": {"type": "string"},
                "confirmed_by_user": {"type": "boolean"},
            },
            "required": ["company_id", "conversation_id", "confirmed_by_user"],
            "additionalProperties": False,
        },
        module="ai",
        capability="draft",
        effect=Effect.DOCUMENT,
        needs_confirmation=True,
        copilot=True,
    )
)
REGISTRY.register(
    ToolSpec(
        name="get_answer_evidence",
        description="Evidências de uma resposta do copiloto do escritório atual.",
        input_schema={
            "type": "object",
            "properties": {"message_id": {"type": "string"}},
            "required": ["message_id"],
            "additionalProperties": False,
        },
        module="ai",
        copilot=True,
    )
)

_ACCESS_KEY = re.compile(r"\d{44}")


def run_public_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Executa as ferramentas públicas (sem rede, sem banco)."""

    spec = REGISTRY.get(name)
    if spec is None or "public" not in spec.tags:
        raise ValueError("ferramenta pública desconhecida")
    if name == "validate_cnpj":
        value = str(arguments.get("value", ""))
        try:
            return {"valid": True, "cnpj": normalize_cnpj(value)}
        except ValidationError as exc:
            return {"valid": False, "reason": " ".join(exc.messages)}
    if name == "validate_access_key":
        key = re.sub(r"\D", "", str(arguments.get("value", "")))
        if not _ACCESS_KEY.fullmatch(key):
            return {"valid": False, "reason": "A chave precisa ter 44 dígitos."}
        from apps.crosscheck.engine.keys import check_digit

        valid = check_digit(key[:43]) == int(key[43])
        return {
            "valid": valid,
            "uf_code": key[:2],
            "issuer_cnpj": key[6:20],
            "model": key[20:22],
            "number": key[25:34],
        }
    if name == "find_cnpjs_in_text":
        return {"cnpjs": sorted(cnpj_candidates(str(arguments.get("text", ""))))}
    raise ValueError("ferramenta pública sem executor")


def names(specs: Iterable[ToolSpec]) -> list[str]:
    return [spec.name for spec in specs]


PublicRunner = Callable[[str, dict[str, Any]], dict[str, Any]]
