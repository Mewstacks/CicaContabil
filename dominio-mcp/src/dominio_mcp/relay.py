"""Repasse pelo agente (Fase 2, peca 3, D-332): um trabalho do gateway vira uma chamada.

O gateway na nuvem nao fala com o banco nem manda SQL: manda um **trabalho** (`contrato`, `id`,
`ferramenta`, `argumentos`). O agente do escritorio executa `dominio-mcp relay-job` (JSON no stdin,
JSON no stdout), que valida o trabalho, chama a ferramenta **no proprio servidor MCP, em
processo**, no perfil `remote`, e devolve o resultado ja moldado (politica, mascara, 12 KB).

O que este caminho garante, cada item com teste (`tests/test_relay.py`):

- so as dez ferramentas L0, L1 e L2; L3 (`sql_somente_leitura`) nao existe aqui, nem com
  `raw_sql` ligado e perfil `local` no arquivo de configuracao: o perfil e fixo em `remote`;
- o trabalho nao tem campo de SQL: chave desconhecida e recusada (`extra=forbid`);
- contrato de outra versao, `id` fora do formato, argumentos grandes demais ou aninhados
  demais sao recusados antes de qualquer chamada;
- resposta limitada (o servidor ja corta em 12 KB; o envelope acrescenta pouco) e sempre JSON.
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Any, Literal

import anyio
from mcp.client import Client
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from dominio_mcp.config import Profile
from dominio_mcp.server import TOOL_NAMES, Deps, build_server

RELAY_CONTRACT = 1
MAX_JOB_BYTES = 32 * 1024
MAX_ARGUMENT_DEPTH = 8
MAX_RESULT_BYTES = 16 * 1024
_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

ToolName = Literal[
    "mapa_do_banco",
    "buscar_esquema",
    "descrever_tabela",
    "caminho_entre_tabelas",
    "valores_do_campo",
    "empresas",
    "empresa_perfil",
    "movimento_fiscal",
    "conferir_numeracao",
    "consulta_estruturada",
]
assert set(ToolName.__args__) == set(TOOL_NAMES)  # type: ignore[attr-defined]


class RelayRefused(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Job(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contrato: int
    id: Annotated[str, Field(pattern=_ID.pattern)]
    ferramenta: ToolName
    argumentos: dict[str, Any] = Field(default_factory=dict)


def _depth(value: Any, level: int = 0) -> int:
    if level > MAX_ARGUMENT_DEPTH:
        return level
    if isinstance(value, dict):
        return max((_depth(v, level + 1) for v in value.values()), default=level + 1)
    if isinstance(value, list):
        return max((_depth(v, level + 1) for v in value), default=level + 1)
    return level


def parse_job(raw: bytes | str) -> Job:
    """Texto JSON do gateway -> `Job`; qualquer desvio e `RelayRefused` (nunca excecao crua)."""
    data = raw.encode("utf-8") if isinstance(raw, str) else raw
    if len(data) > MAX_JOB_BYTES:
        raise RelayRefused("trabalho_grande_demais", f"o trabalho passa de {MAX_JOB_BYTES} bytes")
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RelayRefused("json_invalido", "o trabalho nao e JSON") from None
    if not isinstance(payload, dict):
        raise RelayRefused("trabalho_invalido", "o trabalho precisa ser um objeto JSON")
    if payload.get("contrato") != RELAY_CONTRACT:
        raise RelayRefused(
            "contrato_desconhecido", f"so o contrato {RELAY_CONTRACT} e aceito neste agente"
        )
    try:
        job = Job.model_validate(payload)
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in e["loc"][:1]) for e in exc.errors()})
        raise RelayRefused(
            "trabalho_invalido", f"campos fora do contrato: {', '.join(fields)[:120]}"
        ) from None
    if _depth(job.argumentos) > MAX_ARGUMENT_DEPTH:
        raise RelayRefused("argumentos_fundos_demais", "argumentos aninhados demais")
    return job


def _envelope(job_id: str | None, **fields: Any) -> dict[str, Any]:
    return {"contrato": RELAY_CONTRACT, "id": job_id, **fields}


def refusal_envelope(job_id: str | None, refused: RelayRefused) -> dict[str, Any]:
    return _envelope(job_id, ok=False, erro={"codigo": refused.code, "mensagem": refused.message})


async def _call(deps: Deps, job: Job) -> dict[str, Any]:
    # perfil fixo em remote: o do arquivo de configuracao nunca abre L3 por este caminho
    async with Client(build_server(deps, Profile.REMOTE)) as client:
        result = await client.call_tool(job.ferramenta, job.argumentos)
    text = result.content[0].text if result.content else "{}"  # type: ignore[union-attr]
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        body = {"erro": {"codigo": "resposta_invalida", "mensagem": "resposta fora do formato"}}
    if result.is_error:
        return _envelope(job.id, ok=False, **(body if "erro" in body else {"erro": body}))
    return _envelope(job.id, ok=True, resultado=body)


def run_job(deps: Deps, raw: bytes | str) -> dict[str, Any]:
    """Executa um trabalho e devolve o envelope; nao levanta para entrada ruim."""
    job_id: str | None = None
    try:
        job = parse_job(raw)
        job_id = job.id
        envelope = anyio.run(_call, deps, job)
    except RelayRefused as refused:
        return refusal_envelope(job_id, refused)
    except Exception:
        return refusal_envelope(
            job_id, RelayRefused("erro_interno", "falha ao executar o trabalho")
        )
    encoded = json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_RESULT_BYTES:
        return refusal_envelope(
            job_id, RelayRefused("resposta_grande_demais", "o resultado passou do teto do repasse")
        )
    return envelope
