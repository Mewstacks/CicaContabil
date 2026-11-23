"""Registro único de ferramentas (E12): lista e chamada saem do mesmo catálogo."""

from __future__ import annotations

import pytest

from apps.crosscheck.engine.keys import check_digit
from apps.intelligence.tool_registry import (
    REGISTRY,
    Effect,
    ToolRegistry,
    ToolSpec,
    run_public_tool,
)

SCHEMA = {"type": "object", "properties": {}, "additionalProperties": False}
GATEWAY_EXTERNAL = {
    "search_data_catalog",
    "retrieve_knowledge",
    "get_company_context",
    "get_risk_snapshot",
    "list_obligations",
    "explain_classification",
}


def test_a_new_tool_is_born_closed() -> None:
    spec = ToolSpec(name="nova", description="x", input_schema=SCHEMA)
    assert spec.copilot is False and spec.external is False


@pytest.mark.parametrize("effect", [Effect.LEGAL_READ, Effect.DOCUMENT, Effect.WRITE])
def test_an_effect_without_confirmation_is_refused(effect: Effect) -> None:
    with pytest.raises(ValueError, match="confirmação"):
        ToolSpec(name="x", description="x", input_schema=SCHEMA, effect=effect)


@pytest.mark.parametrize("effect", [Effect.LEGAL_READ, Effect.WRITE])
def test_legal_effect_never_leaves_for_an_external_client(effect: Effect) -> None:
    with pytest.raises(ValueError, match="externo"):
        ToolSpec(
            name="x",
            description="x",
            input_schema=SCHEMA,
            effect=effect,
            needs_confirmation=True,
            external=True,
        )


def test_duplicates_and_negative_costs_are_refused() -> None:
    registry = ToolRegistry()
    registry.register(ToolSpec(name="a", description="x", input_schema=SCHEMA))
    with pytest.raises(ValueError, match="duplicada"):
        registry.register(ToolSpec(name="a", description="x", input_schema=SCHEMA))
    with pytest.raises(ValueError, match="custo"):
        ToolSpec(name="b", description="x", input_schema=SCHEMA, cost_cents=-1)


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="livre", description="x", input_schema=SCHEMA, copilot=True, external=True)
    )
    registry.register(
        ToolSpec(
            name="nfse",
            description="x",
            input_schema=SCHEMA,
            module="nfse",
            copilot=True,
            external=True,
        )
    )
    registry.register(
        ToolSpec(
            name="paga",
            description="x",
            input_schema=SCHEMA,
            module="integra",
            cost_cents=24,
            copilot=True,
        )
    )
    registry.register(
        ToolSpec(
            name="rascunho",
            description="x",
            input_schema=SCHEMA,
            capability="draft",
            effect=Effect.DOCUMENT,
            needs_confirmation=True,
            copilot=True,
        )
    )
    return registry


def test_the_office_contract_and_the_role_decide_what_is_visible() -> None:
    registry = _registry()
    full = registry.available(modules=None, capabilities={"read", "draft"}, surface="copilot")
    assert [spec.name for spec in full] == ["livre", "nfse", "paga", "rascunho"]

    without_modules = registry.available(modules=set(), capabilities={"read"}, surface="copilot")
    assert [spec.name for spec in without_modules] == ["livre"]

    read_only = registry.available(
        modules={"nfse", "integra"}, capabilities={"read"}, surface="copilot"
    )
    assert [spec.name for spec in read_only] == ["livre", "nfse", "paga"]


def test_the_external_surface_is_a_subset_and_the_budget_hides_paid_tools() -> None:
    registry = _registry()
    external = registry.allowed_names(modules=None, capabilities={"read"}, surface="external")
    assert external == {"livre", "nfse"}
    cheap = registry.allowed_names(
        modules=None, capabilities={"read"}, surface="copilot", budget_cents=10
    )
    assert "paga" not in cheap and "livre" in cheap
    with pytest.raises(ValueError):
        registry.available(modules=None, capabilities={"read"}, surface="outra")


def test_the_catalog_matches_the_gateway_and_exposes_public_tools_for_free() -> None:
    external = REGISTRY.allowed_names(
        modules=None, capabilities={"read", "draft"}, surface="external"
    )
    assert external >= GATEWAY_EXTERNAL
    assert external - GATEWAY_EXTERNAL == {
        "validate_cnpj",
        "validate_access_key",
        "find_cnpjs_in_text",
    }
    assert all(REGISTRY.get(name).cost_cents == 0 for name in external)  # type: ignore[union-attr]
    # Efeito (rascunho) fica só no copiloto do Hub, atrás de confirmação.
    draft = REGISTRY.get("create_classification_draft")
    assert draft is not None and draft.external is False and draft.needs_confirmation is True


def test_public_tools_validate_without_network() -> None:
    assert run_public_tool("validate_cnpj", {"value": "12.ABC.345/01DE-35"}) == {
        "valid": True,
        "cnpj": "12ABC34501DE35",
    }
    assert run_public_tool("validate_cnpj", {"value": "12.ABC.345/01DE-00"})["valid"] is False
    assert run_public_tool(
        "find_cnpjs_in_text", {"text": "Emitente 12ABC34501DE35 e 11222333000181."}
    ) == {"cnpjs": ["11222333000181", "12ABC34501DE35"]}
    base = "43149022211222333000181550010000000011234567890"[:43]
    key = base + str(check_digit(base))
    result = run_public_tool("validate_access_key", {"value": key})
    assert result["valid"] is True and result["issuer_cnpj"] == key[6:20]
    assert run_public_tool("validate_access_key", {"value": "123"})["valid"] is False
    with pytest.raises(ValueError):
        run_public_tool("get_company_context", {"company_id": "x"})
