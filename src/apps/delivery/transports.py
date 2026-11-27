"""Transportes de envio: SMTP autenticado e Microsoft Graph (`sendMail` em MIME).

Nenhuma importação deste módulo chama provedor. Os erros carregam só mensagem operacional
curta: nunca resposta do provedor, token, senha ou endereço de cliente.
"""

from __future__ import annotations

import base64
import ipaddress
import json
import mimetypes
import smtplib
import socket
import ssl
from collections.abc import Callable
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from apps.delivery.models import DeliveryAccount

TIMEOUT_SECONDS = 30
_GRAPH = "https://graph.microsoft.com/v1.0"
_LOGIN = "https://login.microsoftonline.com"


ALLOWED_SMTP_PORTS = frozenset({25, 465, 587})


def resolve_host(host: str) -> list[str]:
    try:
        return sorted({str(info[4][0]) for info in socket.getaddrinfo(host, None)})
    except OSError:
        return []


def smtp_host_error(host: str, port: int) -> str:
    """Recusa porta fora do padrão e servidor que resolve para rede interna (SSRF)."""

    if port not in ALLOWED_SMTP_PORTS:
        return "Use a porta 465, 587 ou 25."
    addresses = resolve_host(host)
    if not addresses:
        return "Servidor não encontrado."
    for address in addresses:
        try:
            if not ipaddress.ip_address(address.split("%")[0]).is_global:
                return "O servidor precisa ser público."
        except ValueError:
            return "Servidor inválido."
    return ""


class DeliveryError(RuntimeError):
    """Falha de envio com mensagem segura para a tela."""


class PermanentDeliveryError(DeliveryError):
    """Repetir não adianta: configuração, destinatário recusado, mensagem rejeitada."""


class TemporaryDeliveryError(DeliveryError):
    """Rede ou provedor indisponível: vale tentar de novo."""


class Transport(Protocol):
    def send(self, message: EmailMessage) -> str: ...


def build_message(
    *,
    account: DeliveryAccount,
    recipients: list[str],
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes]],
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = formataddr((account.from_name, account.sender_address))
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(domain=account.sender_address.rsplit("@", 1)[-1])
    message.set_content(body)
    for filename, content in attachments:
        kind = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        maintype, _, subtype = kind.partition("/")
        message.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
    return message


class SmtpTransport:
    def __init__(self, account: DeliveryAccount) -> None:
        self.account = account

    def check(self) -> None:
        """Abre a conexão e autentica, sem enviar nada."""

        self._run(None)

    def send(self, message: EmailMessage) -> str:
        self._run(message)
        return str(message["Message-ID"])

    def _run(self, message: EmailMessage | None) -> None:
        account = self.account
        refusal = smtp_host_error(account.smtp_host, account.smtp_port)
        if refusal:
            raise PermanentDeliveryError(refusal)
        context = ssl.create_default_context()
        try:
            if account.smtp_security == DeliveryAccount.Security.SSL:
                client: smtplib.SMTP = smtplib.SMTP_SSL(
                    account.smtp_host, account.smtp_port, timeout=TIMEOUT_SECONDS, context=context
                )
            else:
                client = smtplib.SMTP(account.smtp_host, account.smtp_port, timeout=TIMEOUT_SECONDS)
            with client as session:
                if account.smtp_security == DeliveryAccount.Security.STARTTLS:
                    session.starttls(context=context)
                if account.smtp_username:
                    session.login(account.smtp_username, account.smtp_password)
                refused = session.send_message(message) if message is not None else {}
        except smtplib.SMTPAuthenticationError as exc:
            raise PermanentDeliveryError("O servidor recusou o login da conta de envio.") from exc
        except smtplib.SMTPRecipientsRefused as exc:
            raise PermanentDeliveryError("O servidor recusou todos os destinatários.") from exc
        except smtplib.SMTPResponseException as exc:
            if 400 <= exc.smtp_code < 500:
                raise TemporaryDeliveryError("O servidor adiou o envio.") from exc
            raise PermanentDeliveryError(
                f"O servidor recusou a mensagem (código {exc.smtp_code})."
            ) from exc
        except (smtplib.SMTPException, OSError, ssl.SSLError) as exc:
            raise TemporaryDeliveryError("O servidor de e-mail não respondeu.") from exc
        if refused:
            raise PermanentDeliveryError("O servidor recusou parte dos destinatários.")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


HttpPost = Callable[[str, dict[str, str], bytes], tuple[int, bytes]]


def _http_post(url: str, headers: dict[str, str], data: bytes) -> tuple[int, bytes]:
    # URLs são constantes https deste módulo; nenhum valor externo escolhe o esquema.
    request = Request(url, data=data, headers=headers, method="POST")  # noqa: S310
    try:
        with build_opener(_NoRedirect).open(request, timeout=TIMEOUT_SECONDS) as response:
            return int(response.status), response.read(200_000)
    except HTTPError as exc:
        return int(exc.code), exc.read(200_000)
    except (URLError, TimeoutError, OSError) as exc:
        raise TemporaryDeliveryError("O Microsoft 365 não respondeu.") from exc


class GraphTransport:
    """`POST /users/{caixa}/sendMail` com a mensagem MIME em base64 (aplicativo, Mail.Send)."""

    def __init__(self, account: DeliveryAccount, post: HttpPost | None = None) -> None:
        self.account = account
        self.post = post or _http_post

    def _token(self) -> str:
        account = self.account
        form = urlencode(
            {
                "client_id": account.graph_client_id,
                "client_secret": account.graph_client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            }
        ).encode()
        status, raw = self.post(
            f"{_LOGIN}/{quote(account.graph_tenant_id, safe='')}/oauth2/v2.0/token",
            {"Content-Type": "application/x-www-form-urlencoded"},
            form,
        )
        if status >= 500 or status == 429:
            raise TemporaryDeliveryError("O Microsoft 365 está indisponível.")
        try:
            token = json.loads(raw).get("access_token", "")
        except ValueError:
            token = ""
        if status != 200 or not token:
            raise PermanentDeliveryError("O Microsoft 365 recusou as credenciais do aplicativo.")
        return str(token)

    def check(self) -> None:
        self._token()

    def send(self, message: EmailMessage) -> str:
        token = self._token()
        payload = base64.b64encode(message.as_bytes())
        status, _ = self.post(
            f"{_GRAPH}/users/{quote(self.account.sender_address, safe='')}/sendMail",
            {"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
            payload,
        )
        if status == 202:
            return str(message["Message-ID"])
        if status in {429, 502, 503, 504}:
            raise TemporaryDeliveryError("O Microsoft 365 adiou o envio.")
        raise PermanentDeliveryError(f"O Microsoft 365 recusou a mensagem (código {status}).")


def transport_for(account: DeliveryAccount) -> Transport:
    if account.provider == DeliveryAccount.Provider.GRAPH:
        return GraphTransport(account)
    return SmtpTransport(account)
