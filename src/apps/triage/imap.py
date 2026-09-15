"""Read-only IMAP consent probe with a public DNS address pinned before TLS."""

from __future__ import annotations

import imaplib
import ipaddress
import json
import socket
import ssl
from contextlib import suppress


class MailboxIMAPError(ValueError):
    """Actionable error that never includes server replies or credentials."""


def public_imap_address(host: str) -> str:
    """Resolve once and fail closed if any answer is non-public."""
    try:
        addresses = socket.getaddrinfo(host, 993, type=socket.SOCK_STREAM)
    except (socket.gaierror, TimeoutError, OSError) as exc:
        raise MailboxIMAPError(
            "Servidor não encontrado. Confira o endereço IMAP com seu provedor."
        ) from exc
    if not addresses:
        raise MailboxIMAPError("Servidor não encontrado. Confira o endereço IMAP com seu provedor.")
    public: list[str] = []
    for result in addresses:
        try:
            ip = ipaddress.ip_address(result[4][0])
        except (IndexError, ValueError) as exc:
            raise MailboxIMAPError("O servidor IMAP retornou um endereço inválido.") from exc
        if not ip.is_global:
            raise MailboxIMAPError("Use um servidor IMAP público fornecido pelo provedor.")
        public.append(str(ip))
    return public[0]


class _PinnedIMAP4SSL(imaplib.IMAP4_SSL):
    """Connect to the checked address; verify the certificate against the hostname."""

    def __init__(self, host: str, address: str, *, timeout: int = 10):
        self._checked_address = address
        super().__init__(host, 993, ssl_context=ssl.create_default_context(), timeout=timeout)

    def _create_socket(self, timeout: float | None) -> ssl.SSLSocket:
        sock = socket.create_connection((self._checked_address, self.port), timeout=timeout)
        try:
            return self.ssl_context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def probe_imap_mailbox(*, host: str, username: str, password: str, folder: str) -> None:
    """Authenticate and list identifiers without reading/changing message flags."""
    address = public_imap_address(host)
    try:
        connection = _PinnedIMAP4SSL(host, address)
    except (TimeoutError, ssl.SSLError, OSError, imaplib.IMAP4.error) as exc:
        raise MailboxIMAPError(
            "Falha na conexão TLS. Confira servidor, porta 993 e certificado com seu provedor."
        ) from exc
    try:
        try:
            status, _ = connection.login(username, password)
            if status != "OK":
                raise MailboxIMAPError(
                    "A autenticação falhou. Confira usuário e senha específica de aplicativo."
                )
        except imaplib.IMAP4.error as exc:
            raise MailboxIMAPError(
                "A autenticação falhou. Confira usuário e senha específica de aplicativo."
            ) from exc
        try:
            status, _ = connection.select(folder, readonly=True)
            if status != "OK":
                raise MailboxIMAPError("Pasta não encontrada. Confira o nome no seu provedor.")
            status, _ = connection.uid("search", None, "ALL")
            if status != "OK":
                raise MailboxIMAPError("O provedor não permitiu ler a pasta escolhida.")
        except imaplib.IMAP4.error as exc:
            raise MailboxIMAPError("O provedor não permitiu ler a pasta escolhida.") from exc
    except (TimeoutError, ssl.SSLError, OSError) as exc:
        raise MailboxIMAPError("A conexão caiu durante o teste. Tente novamente.") from exc
    finally:
        with suppress(TimeoutError, ssl.SSLError, OSError, imaplib.IMAP4.error):
            connection.logout()


def encrypted_imap_credential(*, host: str, username: str, password: str) -> str:
    """Mailbox.credential encrypts this serialized value at rest."""
    return json.dumps(
        {"version": 1, "provider": "imap", "host": host, "username": username, "password": password}
    )
