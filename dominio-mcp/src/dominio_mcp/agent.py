"""Agente do computador do escritorio (Fase 2, peca 3, D-332).

Roda onde o ODBC do Dominio esta. So faz conexao de SAIDA para o CICA: puxa o proximo trabalho
da fila do proprio escritorio, executa no `relay-job` (perfil remote fixo, so as onze ferramentas,
sem campo de SQL) e devolve o envelope. Nao abre porta, nao guarda resultado.

Identidade e assinatura sao as do agente de sincronizacao do Hub: cabecalhos `X-Hub-Agent-ID`,
`X-Hub-Agent-Timestamp` e `X-Hub-Agent-Signature` (HMAC-SHA256 de `timestamp.corpo`). O segredo
fica em `agent.json` na pasta do servico, protegido pelo DPAPI do Windows (escopo da maquina); o
arquivo so e legivel por SYSTEM e Administradores (o instalador aplica a ACL).

Falhas de rede nunca derrubam o laco: espera crescente (2 s ate 60 s) e tenta de novo. Um trabalho
que o agente nao consegue devolver e abandonado; o Hub o expira em 120 s.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import platform
import socket
import ssl
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

CONFIG_NAME = "agent.json"
CLAIM_PATH = "/api/agent/mcp/claim"
RESULT_PATH = "/api/agent/mcp/result"
ENROLL_PATH = "/api/v1/intelligence/agent/enroll/"
MAX_REPLY_BYTES = 64 * 1024
LONG_POLL_SECONDS = 10
HTTP_TIMEOUT = LONG_POLL_SECONDS + 15
BACKOFF_START, BACKOFF_MAX = 2.0, 60.0
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def _on_windows() -> bool:
    # `platform` (e nao `sys.platform`) para o mypy nao tratar o ramo do outro sistema como morto
    return platform.system() == "Windows"


class AgentError(Exception):
    """Falha que o instalador ou o log mostra em portugues, sem segredo."""


@dataclass(frozen=True)
class AgentConfig:
    hub_url: str
    agent_id: str
    shared_secret: str
    client_cert: str = ""
    client_key: str = ""
    ca_file: str = ""


class Transport(Protocol):
    def __call__(
        self, url: str, body: bytes, headers: dict[str, str], config: AgentConfig | None
    ) -> dict[str, Any]: ...


# --- protecao do segredo em repouso -------------------------------------------------------------


def _dpapi(data: bytes, *, protect: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    local_machine = 0x4  # CRYPTPROTECT_LOCAL_MACHINE: o servico (SYSTEM) abre, qualquer conta nao
    buffer = ctypes.create_string_buffer(data, len(data))
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    target = Blob()
    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined,unused-ignore]
    call = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    flags = local_machine if protect else 0
    ok = call(ctypes.byref(source), None, None, None, None, flags, ctypes.byref(target))
    if not ok:
        raise AgentError("o Windows recusou proteger ou abrir o segredo do agente")
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(target.pbData)  # type: ignore[attr-defined,unused-ignore]


def protect_secret(secret: str) -> dict[str, str]:
    if _on_windows():
        blob = _dpapi(secret.encode("utf-8"), protect=True)
        return {"scheme": "dpapi-machine", "secret": base64.b64encode(blob).decode("ascii")}
    return {"scheme": "plain", "secret": secret}


def unprotect_secret(stored: dict[str, str]) -> str:
    scheme = stored.get("scheme")
    if scheme == "dpapi-machine" and _on_windows():
        return _dpapi(base64.b64decode(stored["secret"]), protect=False).decode("utf-8")
    if scheme == "plain":
        return str(stored["secret"])
    raise AgentError("segredo do agente em formato que este computador nao abre")


def config_path(home: Path) -> Path:
    return home / CONFIG_NAME


def save_config(home: Path, config: AgentConfig) -> Path:
    home.mkdir(parents=True, exist_ok=True)
    data = asdict(config)
    data.update(protect_secret(data.pop("shared_secret")))
    path = config_path(home)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    if not _on_windows():
        path.chmod(0o600)
    return path


def load_config(home: Path) -> AgentConfig:
    path = config_path(home)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AgentConfig(
            hub_url=str(data["hub_url"]),
            agent_id=str(data["agent_id"]),
            shared_secret=unprotect_secret(data),
            client_cert=str(data.get("client_cert", "")),
            client_key=str(data.get("client_key", "")),
            ca_file=str(data.get("ca_file", "")),
        )
    except FileNotFoundError:
        raise AgentError("agente nao pareado: rode `dominio-mcp agent-enroll`") from None
    except (KeyError, ValueError, json.JSONDecodeError):
        raise AgentError(f"{path} esta ilegivel; pareie de novo") from None


# --- HTTP ---------------------------------------------------------------------------------------


def _checked_base(hub_url: str) -> str:
    parts = urlsplit(hub_url.strip())
    secure = parts.scheme == "https"
    local = parts.scheme == "http" and (parts.hostname or "") in _LOOPBACK
    if not (secure or local) or not parts.hostname or parts.username or parts.password:
        raise AgentError("o endereco do Hub precisa ser https://")
    return f"{parts.scheme}://{parts.netloc}"


def sign(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def _context(config: AgentConfig | None) -> ssl.SSLContext | None:
    if config is None:
        return None
    if not (config.client_cert or config.ca_file):
        return None
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=config.ca_file or None)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    if config.client_cert:
        context.load_cert_chain(config.client_cert, config.client_key or None)
    return context


def http_transport(
    url: str, body: bytes, headers: dict[str, str], config: AgentConfig | None
) -> dict[str, Any]:
    request = Request(  # noqa: S310 - `_checked_base` so deixa https (ou loopback em teste)
        url, data=body, headers={"Content-Type": "application/json", **headers}, method="POST"
    )
    try:
        with urlopen(  # noqa: S310 - idem
            request, timeout=HTTP_TIMEOUT, context=_context(config)
        ) as response:
            raw = response.read(MAX_REPLY_BYTES + 1)
    except HTTPError as exc:
        raise AgentError(f"o Hub respondeu {exc.code}") from None
    except (URLError, TimeoutError, OSError, ssl.SSLError):
        raise AgentError("sem conexao com o Hub") from None
    if len(raw) > MAX_REPLY_BYTES:
        raise AgentError("resposta do Hub grande demais")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise AgentError("resposta do Hub nao e JSON") from None
    if not isinstance(payload, dict):
        raise AgentError("resposta do Hub fora do formato")
    return payload


def machine_fingerprint() -> str:
    seed = f"{socket.gethostname()}|{uuid.getnode()}"
    return hashlib.sha256(seed.encode()).hexdigest()[:32]


def enroll(
    *,
    hub_url: str,
    code: str,
    label: str,
    transport: Transport = http_transport,
    client_cert: str = "",
    client_key: str = "",
    ca_file: str = "",
) -> AgentConfig:
    """Troca o codigo de uso unico pela identidade do agente; a chave privada nunca viaja."""
    base = _checked_base(hub_url)
    payload: dict[str, str] = {
        "code": code.strip(),
        "label": label.strip() or socket.gethostname(),
        "fingerprint": machine_fingerprint(),
    }
    if client_cert:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes

        certificate = x509.load_pem_x509_certificate(Path(client_cert).read_bytes())
        payload["mtls_certificate_sha256"] = certificate.fingerprint(hashes.SHA256()).hex()
    draft = AgentConfig(base, "", "", client_cert, client_key, ca_file)
    reply = transport(base + ENROLL_PATH, json.dumps(payload).encode(), {}, draft)
    agent_id, secret = reply.get("agent_id"), reply.get("shared_secret")
    if not isinstance(agent_id, str) or not isinstance(secret, str) or not agent_id or not secret:
        raise AgentError("o Hub nao devolveu a identidade do agente")
    return AgentConfig(base, agent_id, secret, client_cert, client_key, ca_file)


def signed_post(
    config: AgentConfig, path: str, payload: dict[str, Any], transport: Transport
) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    headers = {
        "X-Hub-Agent-ID": config.agent_id,
        "X-Hub-Agent-Timestamp": timestamp,
        "X-Hub-Agent-Signature": sign(config.shared_secret, timestamp, body),
    }
    return transport(_checked_base(config.hub_url) + path, body, headers, config)


# --- laco ---------------------------------------------------------------------------------------

JobRunner = Callable[[bytes], dict[str, Any]]


class Agent:
    def __init__(
        self,
        config: AgentConfig,
        runner: JobRunner,
        *,
        transport: Transport = http_transport,
        log: Callable[[str], None] = lambda message: None,
    ) -> None:
        self.config = config
        self._runner = runner
        self._transport = transport
        self._log = log

    def step(self, wait: float = LONG_POLL_SECONDS) -> bool:
        """Um ciclo: puxa, executa, devolve. `True` quando havia trabalho."""
        reply = signed_post(self.config, CLAIM_PATH, {"wait": wait}, self._transport)
        job = reply.get("job")
        if not isinstance(job, dict):
            return False
        envelope = self._runner(json.dumps(job).encode("utf-8"))
        signed_post(
            self.config,
            RESULT_PATH,
            {"id": str(job.get("id", "")), "envelope": envelope},
            self._transport,
        )
        self._log(f"trabalho {job.get('ferramenta')} {'ok' if envelope.get('ok') else 'recusado'}")
        return True

    def run(self, stop: threading.Event) -> None:
        delay = BACKOFF_START
        while not stop.is_set():
            try:
                self.step()
                delay = BACKOFF_START
            except AgentError as exc:
                self._log(f"falha: {exc}; nova tentativa em {delay:.0f}s")
                stop.wait(delay)
                delay = min(delay * 2, BACKOFF_MAX)
            except Exception:
                self._log("erro inesperado no agente; nova tentativa")
                stop.wait(delay)
                delay = min(delay * 2, BACKOFF_MAX)


def relay_runner() -> JobRunner:
    """Executa no `relay-job` real: perfil remote, banco pelo DSN de sistema."""
    from dominio_mcp.config import Profile, load_settings
    from dominio_mcp.relay import run_job
    from dominio_mcp.server import build_deps

    deps = build_deps(load_settings(profile=Profile.REMOTE))
    return lambda raw: run_job(deps, raw)
