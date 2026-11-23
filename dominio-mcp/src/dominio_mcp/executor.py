"""Execucao de ponta a ponta da consulta estruturada L2 (D-317, D-322, D-327, T4.8).

Ordem, do mais barato para o mais caro (cada etapa so roda se a anterior passou):

1. especificacao valida (pydantic) e pack corrente sem tocar no banco (`precheck`);
2. validacao contra o pack e a politica de dados, escopo de tabela grande e compilacao
   (`query_spec`, `scope`, `compiler`): so CPU, nenhuma trava de banco;
3. uma admissao do governador (trava entre processos, frequencia, quarentena) para tudo o que
   toca o banco: frescor do pack, `SELECT PLAN(?)` com o SQL interno como parametro ligado,
   admissao por custo e a consulta de verdade com parametros `?`;
4. moldagem da saida (`shaping`) e auditoria (so metadados, nunca valor de linha).

Qualquer recusa leva `code` estavel (`QueryRefused`); erro do banco chega como `DbError` ja sem o
texto do driver.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from pydantic import ValidationError

from dominio_mcp.admission import admit, estimate_plan
from dominio_mcp.compiler import CompiledQuery, compile_query
from dominio_mcp.config import Settings
from dominio_mcp.freshness import Executor, PackStale
from dominio_mcp.odbc import Auditor, Session
from dominio_mcp.pack import Pack
from dominio_mcp.policy import Policy
from dominio_mcp.query_spec import (
    ConsultaEstruturada,
    QueryRefused,
    ValidatedQuery,
    validate_query,
)
from dominio_mcp.scope import check_scope
from dominio_mcp.shaping import ShapeContext, shape_result


class Guard(Protocol):
    def precheck(self) -> Pack: ...

    def check(self, execute: Executor) -> Pack: ...


def args_hash(spec: ConsultaEstruturada) -> str:
    """Hash estavel da consulta (a auditoria guarda isto, nunca os valores dos filtros)."""
    canonical = json.dumps(spec.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def parse_spec(spec: dict[str, Any] | ConsultaEstruturada) -> ConsultaEstruturada:
    if isinstance(spec, ConsultaEstruturada):
        return spec
    try:
        return ConsultaEstruturada.model_validate(spec)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or 'consulta'}: {err['msg']}"
            for err in exc.errors(include_input=False, include_url=False)
        )
        raise QueryRefused(
            "especificacao_invalida", f"a consulta nao segue o formato esperado ({problems})"
        ) from None


class QueryEngine:
    def __init__(
        self,
        *,
        settings: Settings,
        policy: Policy,
        guard: Guard,
        session: Session,
        auditor: Auditor | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._settings = settings
        self._policy = policy
        self._guard = guard
        self._session = session
        self._auditor = auditor
        self._clock = clock

    def _audit(self, **fields: Any) -> None:
        if self._auditor is None:
            return
        try:
            self._auditor.event("consulta", **fields)
        except Exception:  # auditoria que falha nao derruba a consulta
            return

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def policy(self) -> Policy:
        return self._policy

    def precheck(self) -> Pack:
        return self._guard.precheck()

    def run(
        self,
        spec_input: dict[str, Any] | ConsultaEstruturada,
        *,
        tool: str = "consulta_estruturada",
        verify: Callable[[ValidatedQuery], None] | None = None,
    ) -> dict[str, Any]:
        """Valida, compila e executa. `verify` roda sobre a consulta validada (L3 confere o ON)."""
        started = self._clock()
        spec: ConsultaEstruturada | None = None
        tables: tuple[str, ...] = ()
        pack_short = ""
        try:
            spec = parse_spec(spec_input)
            pack = self._guard.precheck()
            pack_short = pack.meta.short
            vq = validate_query(spec, pack, self._settings, self._policy)
            if verify is not None:
                verify(vq)
            check_scope(vq)
            compiled = compile_query(vq, pack.meta.owner)
            tables = compiled.tables
        except QueryRefused as refusal:
            self._audit_failure(
                tool,
                None if spec is None else args_hash(spec),
                tables,
                f"recusada:{refusal.code}",
                started,
                pack_short,
            )
            raise
        except Exception as exc:
            self._audit_failure(
                tool,
                None if spec is None else args_hash(spec),
                tables,
                f"erro:{type(exc).__name__}",
                started,
                pack_short,
            )
            raise
        return self.execute_compiled(compiled, tool=tool, args=args_hash(spec), pack=pack)

    def _audit_failure(
        self,
        tool: str,
        args: str | None,
        tables: tuple[str, ...],
        outcome: str,
        started: float,
        pack_short: str,
    ) -> None:
        self._audit(
            tool=tool,
            args=args,
            tabelas=list(tables),
            resultado=outcome,
            latencia_ms=round((self._clock() - started) * 1000),
            pack=pack_short,
        )

    def execute_compiled(
        self,
        compiled: CompiledQuery,
        *,
        tool: str,
        args: str,
        pack: Pack,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Frescor, estimativa de custo, admissao, execucao e moldagem sob UMA admissao.

        `extra` sao campos que o chamador acrescenta ao envelope; entram na conta dos 12 KB.
        """
        started = self._clock()
        limits = self._settings.limits
        pack_short = pack.meta.short
        try:
            with self._session.slot() as slot:
                checked = self._guard.check(slot.execute)
                if checked.meta.version != pack.meta.version:
                    # a consulta foi compilada com a politica do pack antigo: nao executa com ela
                    raise PackStale("o pack mudou durante a consulta; tente de novo")
                estimate = estimate_plan(slot.execute, compiled.literal_sql)
                admit(
                    estimate,
                    cost_budget=limits.plan_cost_budget,
                    rows_budget=limits.plan_rows_budget,
                )
                raw = slot.execute(compiled.sql, compiled.params, max_rows=compiled.limit)
            result = shape_result(
                compiled,
                raw,
                ShapeContext(
                    pack_version=pack_short,
                    elapsed_ms=raw.elapsed_ms,
                    plan_cost=estimate.cost,
                    extra=tuple((extra or {}).items()),
                ),
            )
        except QueryRefused as refusal:
            self._audit_failure(
                tool, args, compiled.tables, f"recusada:{refusal.code}", started, pack_short
            )
            raise
        except Exception as exc:
            self._audit_failure(
                tool, args, compiled.tables, f"erro:{type(exc).__name__}", started, pack_short
            )
            raise
        self._audit(
            tool=tool,
            args=args,
            tabelas=list(compiled.tables),
            resultado="ok",
            linhas=result["quantidade"],
            truncado=result["truncado"],
            latencia_ms=round((self._clock() - started) * 1000),
            custo=round(estimate.cost, 6),
            pack=pack_short,
        )
        return result
