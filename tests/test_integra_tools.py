"""Pure tool functions over the typed reads: allowlist, validation, audit, no documents."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

from apps.integra.catalog import SERVICES, service
from apps.integra.errors import IntegraRequestError
from apps.integra.governor import call_cost_cents
from apps.integra.tools import TOOLS, ToolError, run_tool, tool_schema
from apps.integra.typed_registry import TYPED
from integra_fixtures import official_payload

CONTRIBUINTE = "11444777000161"


class FakeAccess:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def call(self, service_key: str, *, contribuinte: str, dados: Any = None) -> dict[str, Any]:
        self.calls.append({"key": service_key, "contribuinte": contribuinte, "dados": dados})
        return self.payload


def test_the_tools_are_exactly_the_typed_reads_the_copilot_may_call() -> None:
    assert len(TOOLS) == 59
    assert {tool.key for tool in TOOLS.values()} == set(TYPED)
    for name, tool in TOOLS.items():
        spec = service(tool.key)
        assert spec.copilot_allowed and not spec.needs_confirmation
        assert name == "serpro_" + tool.key.replace(".", "_")
        assert tool.cost_cents == call_cost_cents(spec)
    assert len(TOOLS) == len({tool.key for tool in TOOLS.values()})


def test_services_with_effect_or_without_release_are_not_tools() -> None:
    blocked = [s.key for s in SERVICES.values() if not s.copilot_allowed]
    assert blocked and not {"serpro_" + key.replace(".", "_") for key in blocked} & set(TOOLS)
    with pytest.raises(ToolError, match="desconhecida"):
        run_tool(FakeAccess({}), "serpro_pgdasd_das", contribuinte=CONTRIBUINTE, arguments={})
    with pytest.raises(ToolError, match="desconhecida"):
        run_tool(
            FakeAccess({}), "serpro_caixapostal_detalhe", contribuinte=CONTRIBUINTE, arguments={}
        )


def test_a_tool_builds_the_request_calls_once_and_returns_plain_json() -> None:
    access = FakeAccess(official_payload("PAGTOWEB.PAGAMENTOS71.darf"))

    result = run_tool(
        access,
        "serpro_pagtoweb_pagamentos",
        contribuinte=CONTRIBUINTE,
        arguments={"numeros_documento": ["9999999999"], "tamanho_da_pagina": 10},
    )

    assert access.calls == [
        {
            "key": "pagtoweb.pagamentos",
            "contribuinte": CONTRIBUINTE,
            "dados": {
                "numeroDocumentoLista": ["9999999999"],
                "primeiroDaPagina": 0,
                "tamanhoDaPagina": 10,
            },
        }
    ]
    text = json.dumps(result.data)
    assert result.data[0]["valor_total"] == "369176.53"
    assert result.data[0]["data_arrecadacao"].startswith("2019-09-30")
    assert result.service_key == "pagtoweb.pagamentos" and result.cost_cents == 24
    assert "9999999999" in text


def test_dates_and_nested_arguments_arrive_as_json_strings() -> None:
    access = FakeAccess(official_payload("PAGTOWEB.CONTACONSDOCARRPG73.contagem"))

    result = run_tool(
        access,
        "serpro_pagtoweb_contagem",
        contribuinte=CONTRIBUINTE,
        arguments={
            "intervalo_data_arrecadacao": {"inicial": "2022-01-01", "final": "2022-12-31"},
            "intervalo_valor_total": {"inicial": "600", "final": 13000},
        },
    )

    assert result.data == 1
    assert access.calls[0]["dados"] == {
        "intervaloDataArrecadacao": {"dataInicial": "2022-01-01", "dataFinal": "2022-12-31"},
        "intervaloValorTotalDocumento": {"valorInicial": 600, "valorFinal": 13000},
    }


@pytest.mark.parametrize(
    "arguments",
    [
        {"tamanho_da_pagina": 500},
        {"numeros_documento": "abc"},
        {"nao_existe": 1},
        {"numeros_documento": [1]},
    ],
)
def test_invalid_arguments_stop_before_any_call(arguments: dict[str, Any]) -> None:
    access = FakeAccess({})

    with pytest.raises((IntegraRequestError, ToolError)):
        run_tool(
            access, "serpro_pagtoweb_pagamentos", contribuinte=CONTRIBUINTE, arguments=arguments
        )

    assert access.calls == []


def test_a_tool_without_request_takes_no_arguments() -> None:
    access = FakeAccess(official_payload("DEFIS.CONSDECLARACAO142.declaracoes"))

    run_tool(access, "serpro_defis_declaracoes", contribuinte=CONTRIBUINTE, arguments={})
    with pytest.raises(ToolError, match="argumentos"):
        run_tool(access, "serpro_defis_declaracoes", contribuinte=CONTRIBUINTE, arguments={"x": 1})


def test_pdf_and_xml_documents_are_never_returned_only_described() -> None:
    access = FakeAccess(official_payload("PGDASD.CONSEXTRATO16.extrato"))

    result = run_tool(
        access,
        "serpro_pgdasd_extrato",
        contribuinte=CONTRIBUINTE,
        arguments={"numero_das": "07202136999997159"},
    )

    text = json.dumps(result.data)
    assert '"tipo": "pdf"' in text or "'tipo': 'pdf'" in text
    assert "JVBER" not in text and "bytes" in text and "sha256" in text


def test_every_call_is_audited_without_the_taxpayer_number() -> None:
    events: list[dict[str, Any]] = []
    access = FakeAccess(official_payload("PAGTOWEB.CONTACONSDOCARRPG73.contagem"))

    run_tool(
        access,
        "serpro_pagtoweb_contagem",
        contribuinte=CONTRIBUINTE,
        arguments={},
        audit=events.append,
    )

    assert len(events) == 1
    event = events[0]
    assert event["tool"] == "serpro_pagtoweb_contagem" and event["outcome"] == "ok"
    assert event["cost_cents"] == 24
    assert CONTRIBUINTE not in json.dumps(event)
    assert event["contribuinte_ref"] == hashlib.sha256(CONTRIBUINTE.encode()).hexdigest()[:12]


def test_a_failed_call_is_audited_and_raised() -> None:
    events: list[dict[str, Any]] = []

    class Broken(FakeAccess):
        def call(self, service_key: str, **kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("falhou")

    with pytest.raises(RuntimeError):
        run_tool(
            Broken({}),
            "serpro_pagtoweb_contagem",
            contribuinte=CONTRIBUINTE,
            arguments={},
            audit=events.append,
        )

    assert events[0]["outcome"] == "error"


def test_the_schema_of_each_tool_lists_its_arguments() -> None:
    schema = tool_schema("serpro_pagtoweb_pagamentos")

    assert schema["name"] == "serpro_pagtoweb_pagamentos"
    properties = schema["input_schema"]["properties"]
    assert properties["tamanho_da_pagina"]["type"] == "integer"
    assert properties["numeros_documento"]["type"] == "array"
    assert tool_schema("serpro_defis_declaracoes")["input_schema"]["properties"] == {}
    required = tool_schema("serpro_pgdasd_extrato")["input_schema"]["required"]
    assert "numero_das" in required
