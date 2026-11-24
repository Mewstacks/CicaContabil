"""HTTP em loopback para o MCP do Dominio (M10, D-330, D-331).

Para clientes que so falam HTTP no proprio computador (um agente local, o `tunnel-client` da
OpenAI apontando para `127.0.0.1`). Nao e um servico de rede: e a mesma porta do stdio, atras de
quatro travas independentes, todas antes do SDK:

1. **So loopback.** Escuta em `127.0.0.1` ou `::1`; qualquer outro endereco e erro de
   configuracao, nao um aviso.
2. **Host fixo.** Resposta `421` para um `Host` que nao seja o proprio loopback com a porta
   (barra a religacao de DNS: um site que aponte seu nome para 127.0.0.1).
3. **Origin.** Um `Origin` presente e recusado (`403`) salvo se estiver na lista explicita
   (vazia por padrao). Navegador sempre manda `Origin` em POST entre origens; cliente local
   nao manda.
4. **Token.** `Authorization: Bearer <token>` com comparacao de tempo constante; token de 256
   bits gerado no primeiro uso e guardado em `<pasta de dados>/state/http-token`. Tentativas
   erradas tem teto por minuto (`429`); o token certo nunca e barrado pelo teto (D-331: o teto
   limita ruido e log, nao palpite, e nao pode servir para travar o cliente).

O perfil e sempre `remote` (D-326): HTTP nunca registra nem despacha L3. O corpo do pedido
tem teto de 256 KiB e o numero de sessoes e baixo. O log de acesso do servidor fica desligado
(o cabecalho de autorizacao nao pode ir parar em arquivo).
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import threading
import time
from collections import deque
from collections.abc import Iterable
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.types import ASGIApp, Receive, Scope, Send

DEFAULT_PORT = 8765
MCP_PATH = "/mcp"
TOKEN_BYTES = 32
MIN_TOKEN_CHARS = 32
MAX_BODY_BYTES = 256 * 1024
MAX_SESSIONS = 8
SESSION_IDLE_SECONDS = 600.0
AUTH_FAILURES_PER_MINUTE = 20
LOOPBACK_HOSTS = ("127.0.0.1", "::1")


class HttpConfigError(Exception):
    """Configuracao do HTTP recusada. A mensagem nunca traz o token."""


def check_bind(host: str) -> str:
    """So aceita IP de loopback literal (nada de nome, `0.0.0.0` ou endereco de rede)."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise HttpConfigError("o HTTP so escuta em 127.0.0.1 ou ::1 (IP literal)") from None
    if not address.is_loopback or str(address) not in LOOPBACK_HOSTS:
        raise HttpConfigError("o HTTP so escuta em 127.0.0.1 ou ::1")
    return str(address)


def check_port(port: int) -> int:
    if isinstance(port, bool) or not 1024 <= port <= 65535:
        raise HttpConfigError("a porta deve estar entre 1024 e 65535")
    return port


def token_path(home: Path) -> Path:
    return home / "state" / "http-token"


def load_or_create_token(path: Path) -> str:
    """Le o token (ou cria um de 256 bits) sem nunca sobrescrever um existente."""
    try:
        text = path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        text = ""
    except (OSError, UnicodeDecodeError) as exc:
        raise HttpConfigError(
            f"nao consegui ler o arquivo do token ({type(exc).__name__})"
        ) from exc
    if text:
        if len(text) < MIN_TOKEN_CHARS:
            raise HttpConfigError(
                "o token guardado e curto demais; apague o arquivo para gerar outro"
            )
        return text
    token = secrets.token_urlsafe(TOKEN_BYTES)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:  # outro processo criou entre a leitura e agora: vale o dele
        return load_or_create_token(path)
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        handle.write(token + "\n")
    return token


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8", "replace")).digest()


class FailureLimiter:
    """Teto de tentativas erradas por minuto (global: todo cliente local e o mesmo usuario)."""

    def __init__(self, per_minute: int, clock: object = time.monotonic) -> None:
        self._per_minute = per_minute
        self._clock = clock
        self._stamps: deque[float] = deque()
        self._lock = threading.Lock()

    def _now(self) -> float:
        return float(self._clock())  # type: ignore[operator]

    def blocked(self) -> bool:
        with self._lock:
            now = self._now()
            while self._stamps and now - self._stamps[0] >= 60.0:
                self._stamps.popleft()
            return len(self._stamps) >= self._per_minute

    def record(self) -> None:
        with self._lock:
            self._stamps.append(self._now())


class LoopbackGate:
    """Middleware ASGI: Host, Origin, caminho, metodo e token, nessa ordem, antes do SDK."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        token: str,
        port: int,
        allowed_origins: Iterable[str] = (),
        limiter: FailureLimiter | None = None,
    ) -> None:
        if len(token) < MIN_TOKEN_CHARS:
            raise HttpConfigError("token curto demais")
        self._app = app
        self._token_digest = _digest(token)
        self._hosts = frozenset({f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"})
        self._origins = frozenset(allowed_origins)
        self._limiter = limiter or FailureLimiter(AUTH_FAILURES_PER_MINUTE)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)  # `lifespan` do SDK precisa passar
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        if headers.get("host", "") not in self._hosts:
            await _reply(send, 421, "host_invalido")
            return
        origin = headers.get("origin")
        if origin is not None and origin not in self._origins:
            await _reply(send, 403, "origem_recusada")
            return
        if scope["path"] != MCP_PATH:
            await _reply(send, 404, "nao_encontrado")
            return
        if scope["method"] not in ("POST", "GET", "DELETE"):
            await _reply(send, 405, "metodo_nao_aceito", {"allow": "POST, GET, DELETE"})
            return
        if self._authorized(headers.get("authorization", "")):
            # o token certo passa sempre: o teto e so para o erro, senao qualquer processo local
            # travaria o cliente legitimo (palpitar 256 bits nao e viavel de qualquer jeito)
            await self._app(scope, receive, send)
            return
        if self._limiter.blocked():
            await _reply(send, 429, "muitas_tentativas", {"retry-after": "60"})
            return
        self._limiter.record()
        await _reply(send, 401, "nao_autorizado", {"www-authenticate": "Bearer"})

    def _authorized(self, header: str) -> bool:
        scheme, _, value = header.partition(" ")
        if scheme.lower() != "bearer" or not value:
            return False
        return hmac.compare_digest(_digest(value.strip()), self._token_digest)


async def _reply(send: Send, status: int, code: str, extra: dict[str, str] | None = None) -> None:
    body = json.dumps({"erro": {"codigo": code}}, separators=(",", ":")).encode("ascii")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"cache-control", b"no-store"),
    ]
    headers += [(k.encode("ascii"), v.encode("ascii")) for k, v in (extra or {}).items()]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


def build_http_app(
    server: MCPServer, *, host: str, port: int, token: str, allowed_origins: Iterable[str] = ()
) -> ASGIApp:
    bound = check_bind(host)
    check_port(port)
    origins = list(allowed_origins)
    names = [f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"]
    inner = server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        max_request_body_size=MAX_BODY_BYTES,
        max_sessions=MAX_SESSIONS,
        session_idle_timeout=SESSION_IDLE_SECONDS,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True, allowed_hosts=names, allowed_origins=origins
        ),
        host=bound,
    )
    return LoopbackGate(inner, token=token, port=port, allowed_origins=origins)


def serve_http(server: MCPServer, *, host: str, port: int, token: str) -> None:
    import uvicorn

    app = build_http_app(server, host=host, port=port, token=token)
    config = uvicorn.Config(
        app,
        host=check_bind(host),
        port=port,
        log_level="warning",
        access_log=False,
        server_header=False,
        date_header=False,
    )
    uvicorn.Server(config).run()
