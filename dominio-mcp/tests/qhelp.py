"""Atalhos para os testes de L2: valida e compila a partir de dicionarios JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.compiler import CompiledQuery, compile_query
from dominio_mcp.config import Limits, Settings
from dominio_mcp.pack import Pack
from dominio_mcp.policy import load_policy
from dominio_mcp.query_spec import ConsultaEstruturada, QueryRefused, ValidatedQuery, validate_query
from dominio_mcp.scope import check_scope

POLICY = load_policy()
VALID_CNPJ = "11.222.333/0001-81"
OTHER_VALID_CNPJ = "00000000000191"


def settings(allow_pii: frozenset[str] = frozenset(), **limits: int) -> Settings:
    return Settings(dsn="contabil", home=Path("."), allow_pii=allow_pii, limits=Limits(**limits))


def validate(pack: Pack, spec: dict[str, Any], **kw: Any) -> ValidatedQuery:
    return validate_query(ConsultaEstruturada.model_validate(spec), pack, settings(**kw), POLICY)


def compile_(pack: Pack, spec: dict[str, Any], *, scope: bool = False, **kw: Any) -> CompiledQuery:
    vq = validate(pack, spec, **kw)
    if scope:
        check_scope(vq)
    return compile_query(vq, "bethadba")


def refused(pack: Pack, spec: dict[str, Any], *, scope: bool = False, **kw: Any) -> QueryRefused:
    with pytest.raises(QueryRefused) as exc:
        compile_(pack, spec, scope=scope, **kw)
    return exc.value
