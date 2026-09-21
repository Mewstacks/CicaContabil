"""Bounded read-only IMAP polling for office-authorized inboxes.

The office must explicitly set ``Mailbox.since`` and ``active`` before this runs.
No message flag is changed: SELECT is read-only and FETCH uses BODY.PEEK[].
"""

from __future__ import annotations

import imaplib
import json
import re
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from email import message_from_bytes, policy
from email.message import Message
from typing import cast

from django.core.exceptions import ValidationError

from apps.triage.imap import (
    MailboxIMAPError,
    MailboxIMAPTemporaryError,
    _PinnedIMAP4SSL,
    public_imap_address,
)
from apps.triage.ingest import (
    MAX_EMAIL_ATTACHMENT_BYTES,
    mailbox_accepts_message,
    receive_email_attachment,
)
from apps.triage.models import Mailbox
from apps.triage.poll_state import mark_failure, mark_success

# A 25 MB attachment may occupy ~33.4 MB after MIME base64 encoding.
MAX_IMAP_MESSAGE_BYTES = 40 * 1024 * 1024
_SIZE = re.compile(rb"RFC822\.SIZE\s+(\d+)", re.I)
_INTERNALDATE = re.compile(rb'INTERNALDATE\s+"([^"]+)"', re.I)


@dataclass(frozen=True)
class PollResult:
    examined: int
    attachments_created: int
    duplicates: int
    last_uid: int


def _cursor(value: str) -> tuple[int, int]:
    if not value:
        return 0, 0
    try:
        row = json.loads(value)
        if row.get("version") != 1:
            raise ValueError
        validity, uid = int(row["uidvalidity"]), int(row["last_uid"])
        if validity < 0 or uid < 0:
            raise ValueError
        return validity, uid
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise MailboxIMAPError(
            "O cursor da caixa está inválido. Reconecte antes de sincronizar."
        ) from exc


def _uidvalidity(connection: imaplib.IMAP4_SSL) -> int:
    _, values = connection.response("UIDVALIDITY")
    try:
        value = int(values[0])
    except (TypeError, ValueError, IndexError) as exc:
        raise MailboxIMAPError("O provedor não informou UIDVALIDITY da pasta.") from exc
    if value <= 0:
        raise MailboxIMAPError("O provedor informou UIDVALIDITY inválido.")
    return value


def _internal_date(meta: bytes) -> datetime:
    match = _INTERNALDATE.search(meta)
    if not match:
        raise MailboxIMAPError("A mensagem não trouxe data interna de recebimento.")
    try:
        return datetime.strptime(match.group(1).decode("ascii"), "%d-%b-%Y %H:%M:%S %z")
    except (UnicodeDecodeError, ValueError) as exc:
        raise MailboxIMAPError("A data interna da mensagem é inválida.") from exc


def _metadata(connection: imaplib.IMAP4_SSL, uid: int) -> tuple[int, datetime]:
    status, response = connection.uid("fetch", str(uid), "(RFC822.SIZE INTERNALDATE)")
    if status != "OK" or not response or not isinstance(response[0], bytes):
        raise MailboxIMAPError("Não foi possível ler o tamanho da mensagem. Tente novamente.")
    match = _SIZE.search(response[0])
    if not match:
        raise MailboxIMAPError("O provedor não informou o tamanho da mensagem.")
    return int(match.group(1)), _internal_date(response[0])


def _raw_message(connection: imaplib.IMAP4_SSL, uid: int) -> bytes:
    status, response = connection.uid("fetch", str(uid), "(BODY.PEEK[])")
    if status != "OK" or not response:
        raise MailboxIMAPError("Não foi possível ler a mensagem. Tente novamente.")
    for row in response:
        if isinstance(row, tuple) and len(row) == 2 and isinstance(row[1], bytes):
            if len(row[1]) > MAX_IMAP_MESSAGE_BYTES:
                raise MailboxIMAPError(
                    "Mensagem acima de 40 MB; sincronização pausada para revisão."
                )
            return row[1]
    raise MailboxIMAPError("O provedor não retornou o conteúdo da mensagem.")


def _named_attachments(message: Message) -> list[tuple[str, str, bytes, str]]:
    result: list[tuple[str, str, bytes, str]] = []
    for index, part in enumerate(message.walk()):
        if part.is_multipart() or not part.get_filename():
            continue
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes) or not payload:
            continue
        if len(payload) > MAX_EMAIL_ATTACHMENT_BYTES:
            raise MailboxIMAPError("Anexo acima de 25 MB; sincronização pausada para revisão.")
        result.append((str(index), str(part.get_filename()), payload, part.get_content_type()))
    return result


def poll_imap_mailbox(
    *,
    mailbox: Mailbox,
    max_messages: int = 10,
    connection_factory: Callable[[str, str], imaplib.IMAP4_SSL] = _PinnedIMAP4SSL,
) -> PollResult:
    """Advance the UID checkpoint after each fully processed message, never before."""
    if mailbox.provider != Mailbox.Provider.IMAP:
        raise ValidationError("Esta caixa não usa IMAP.")
    if not mailbox.active or mailbox.status != Mailbox.Status.ACTIVE:
        raise ValidationError("Ative e autorize a caixa antes de sincronizar.")
    if mailbox.since is None:
        raise ValidationError("Escolha a data inicial de leitura antes de sincronizar.")
    if not 1 <= max_messages <= 50:
        raise ValidationError("O lote deve ter entre 1 e 50 mensagens.")
    try:
        credentials = json.loads(mailbox.credential)
        if credentials.get("version") != 1 or credentials.get("provider") != "imap":
            raise ValueError
        host, username, password = (credentials[key] for key in ("host", "username", "password"))
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise MailboxIMAPError("A credencial IMAP está inválida. Reconecte a caixa.") from exc
    connection = None
    try:
        address = public_imap_address(host)
        connection = connection_factory(host, address)
        if connection.login(username, password)[0] != "OK":
            raise MailboxIMAPError("Falha na autenticação IMAP. Reconecte a caixa.")
        if connection.select(mailbox.folder, readonly=True)[0] != "OK":
            raise MailboxIMAPError("Pasta IMAP não encontrada. Confira a configuração.")
        validity = _uidvalidity(connection)
        previous_validity, last_uid = _cursor(mailbox.cursor)
        if previous_validity and previous_validity != validity:
            last_uid = 0
        # Search one extra day to avoid server-local date boundaries; compare exact
        # INTERNALDATE below against the office's approved timezone-aware cutoff.
        since_date = (mailbox.since - timedelta(days=1)).strftime("%d-%b-%Y")
        criteria = (["UID", f"{last_uid + 1}:*"] if last_uid else []) + ["SINCE", since_date]
        status, response = connection.uid("search", cast(str, None), *criteria)
        if status != "OK" or not response:
            raise MailboxIMAPError("O provedor não permitiu buscar mensagens da pasta.")
        ids = sorted({int(value) for value in response[0].split() if value.isdigit()})
        examined = created = duplicates = 0
        for uid in (value for value in ids if value > last_uid):
            if examined >= max_messages:
                break
            size, received_at = _metadata(connection, uid)
            if size > MAX_IMAP_MESSAGE_BYTES:
                raise MailboxIMAPError(
                    "Mensagem acima de 40 MB; sincronização pausada para revisão."
                )
            if received_at >= mailbox.since:
                message = message_from_bytes(_raw_message(connection, uid), policy=policy.default)
                sender = str(message.get("From", ""))
                subject = str(message.get("Subject", ""))
                attachments = (
                    _named_attachments(message)
                    if mailbox_accepts_message(
                        mailbox=mailbox, sender=sender, subject=subject
                    )
                    else []
                )
                for part_id, filename, payload, declared_type in attachments:
                    receipt = receive_email_attachment(
                        mailbox=mailbox,
                        message_id=f"imap:{validity}:{uid}",
                        part_id=part_id,
                        filename=filename,
                        payload=payload,
                        sender=sender,
                        subject=subject,
                        received_at=received_at,
                        declared_type=declared_type,
                    )
                    created += int(receipt.created)
                    duplicates += int(not receipt.created)
            last_uid = uid
            examined += 1
            mailbox.cursor = json.dumps(
                {"version": 1, "uidvalidity": validity, "last_uid": last_uid}
            )
            mailbox.save(update_fields=["cursor", "updated_at"])
            mark_success(mailbox)
        mark_success(mailbox)
        return PollResult(examined, created, duplicates, last_uid)
    except (MailboxIMAPError, ValidationError) as exc:
        mark_failure(mailbox, str(exc), transient=isinstance(exc, MailboxIMAPTemporaryError))
        raise
    except (OSError, TimeoutError) as exc:
        error_message = "A conexão IMAP falhou; a caixa tentará novamente."
        mark_failure(mailbox, error_message, transient=True)
        raise MailboxIMAPTemporaryError(error_message) from exc
    except imaplib.IMAP4.error as exc:
        error_message = "O provedor IMAP recusou a leitura. Confira a configuração."
        mark_failure(mailbox, error_message, transient=False)
        raise MailboxIMAPError(error_message) from exc
    finally:
        if connection is not None:
            with suppress(OSError, TimeoutError, imaplib.IMAP4.error):
                connection.logout()
