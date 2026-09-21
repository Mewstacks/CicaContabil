"""Bounded Microsoft Graph delta reader for an authorized office mailbox.

This only receives named file attachments into private quarantine. The office must
choose the initial date and enable the mailbox separately. Provider calls are never
made by importing this module; tests inject synthetic transport functions.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.triage.ingest import (
    MAX_EMAIL_ATTACHMENT_BYTES,
    mailbox_accepts_message,
    receive_email_attachment,
)
from apps.triage.models import Mailbox
from apps.triage.oauth import MailboxOAuthError, MailboxOAuthTemporaryError, refresh_access_token
from apps.triage.poll_state import mark_failure, mark_success, retry_hint_seconds

_GRAPH_ORIGIN = "https://graph.microsoft.com"
_MAX_DELTA_JSON = 1_000_000
_MAX_ATTACHMENT_JSON = 2_000_000


class GraphMailboxError(ValueError):
    """Safe operational error without response body, token, or customer data."""


class GraphTemporaryError(GraphMailboxError):
    def __init__(self, message: str, *, retry_seconds: int = 0) -> None:
        super().__init__(message)
        self.retry_seconds = retry_seconds


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _validated_url(url: str, expected_path: str) -> str:
    try:
        parts = urlsplit(url)
        valid = (
            parts.scheme == "https"
            and parts.hostname == "graph.microsoft.com"
            and parts.port is None
            and not parts.username
            and not parts.password
            and not parts.fragment
            and parts.path == expected_path
        )
    except ValueError:
        valid = False
    if not valid:
        raise GraphMailboxError("O link de continuidade do Graph é inválido. Reconecte a caixa.")
    return url


def _read(url: str, access_token: str, limit: int, *, accept: str) -> bytes:
    path = urlsplit(url).path
    if not path.startswith("/v1.0/me/"):
        raise GraphMailboxError("O endereço Graph não pertence à caixa autorizada.")
    _validated_url(url, path)
    request = Request(  # noqa: S310 - verified HTTPS Graph origin above
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": accept,
            "Prefer": 'IdType="ImmutableId"',
        },
    )
    try:
        with build_opener(_NoRedirect).open(request, timeout=20) as response:
            raw = response.read(limit + 1)
    except HTTPError as exc:
        if exc.code == 429 or 500 <= exc.code < 600:
            raise GraphTemporaryError(
                "O Graph está temporariamente indisponível; a caixa tentará novamente.",
                retry_seconds=retry_hint_seconds(exc.headers.get("Retry-After")),
            ) from exc
        raise GraphMailboxError("O Graph recusou a leitura. Confira a autorização.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise GraphTemporaryError("O Graph não respondeu; a caixa tentará novamente.") from exc
    if len(raw) > limit:
        raise GraphMailboxError("Resposta Graph acima do limite seguro; sincronização pausada.")
    return cast(bytes, raw)


def _get_json(url: str, access_token: str, limit: int) -> dict[str, object]:
    try:
        result = json.loads(_read(url, access_token, limit, accept="application/json"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GraphMailboxError("O Graph retornou dados inválidos. Tente novamente.") from exc
    if not isinstance(result, dict):
        raise GraphMailboxError("O Graph retornou uma lista inválida.")
    return result


def _get_bytes(url: str, access_token: str, limit: int) -> bytes:
    return _read(url, access_token, limit, accept="application/octet-stream")


@dataclass(frozen=True)
class GraphPollResult:
    pages: int
    messages: int
    attachments_created: int
    duplicates: int
    round_complete: bool


def _folder(mailbox: Mailbox) -> str:
    folder = (
        mailbox.folder.strip().casefold() if mailbox.folder.upper() == "INBOX" else mailbox.folder
    )
    if not folder or len(folder) > 160 or any(c in folder for c in "\r\n\x00"):
        raise ValidationError("Escolha uma pasta Microsoft válida.")
    return quote(folder, safe="")


def _delta_path(mailbox: Mailbox) -> str:
    return f"/v1.0/me/mailFolders/{_folder(mailbox)}/messages/delta"


def _initial_delta_url(mailbox: Mailbox) -> str:
    assert mailbox.since is not None
    cutoff = mailbox.since.astimezone(UTC).isoformat(timespec="seconds")
    params = {
        "$select": "id,receivedDateTime,hasAttachments,from,subject",
        "$top": "20",
        "$filter": f"receivedDateTime ge {cutoff}",
    }
    return f"{_GRAPH_ORIGIN}{_delta_path(mailbox)}?{urlencode(params)}"


def _cursor(mailbox: Mailbox) -> str:
    if not mailbox.cursor:
        return _initial_delta_url(mailbox)
    since = mailbox.since
    if since is None:
        raise GraphMailboxError("A data inicial da caixa Microsoft está ausente.")
    try:
        data = json.loads(mailbox.cursor)
        valid = (
            isinstance(data, dict)
            and data.get("version") == 1
            and data.get("provider") == Mailbox.Provider.MS365_GRAPH
            and data.get("folder") == mailbox.folder
            and data.get("since") == since.isoformat()
            and isinstance(data.get("url"), str)
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        valid = False
    if not valid:
        raise GraphMailboxError("O cursor Microsoft não corresponde à pasta/data. Reconecte.")
    return _validated_url(data["url"], _delta_path(mailbox))


def _received_at(row: dict[str, object]) -> datetime:
    value = row.get("receivedDateTime")
    if not isinstance(value, str):
        raise GraphMailboxError("Uma mensagem Graph não trouxe a data de recebimento.")
    try:
        received = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GraphMailboxError("O Graph informou data de recebimento inválida.") from exc
    if timezone.is_naive(received):
        raise GraphMailboxError("O Graph informou data de recebimento sem fuso.")
    return received


def _opaque_identity(prefix: str, provider_id: str) -> str:
    if not provider_id or len(provider_id) > 2_048:
        raise GraphMailboxError("O Graph não identificou mensagem ou anexo.")
    return prefix + hashlib.sha256(provider_id.encode("utf-8")).hexdigest()


def _attachments(
    *,
    mailbox: Mailbox,
    message: dict[str, object],
    received_at: datetime,
    access_token: str,
    get_json: Callable[[str, str, int], dict[str, object]],
    get_bytes: Callable[[str, str, int], bytes],
) -> tuple[int, int]:
    message_id = message.get("id")
    if not isinstance(message_id, str):
        raise GraphMailboxError("O Graph não identificou a mensagem.")
    sender_row = message.get("from")
    email_row = sender_row.get("emailAddress") if isinstance(sender_row, dict) else None
    sender = str(email_row.get("address", "")) if isinstance(email_row, dict) else ""
    subject = str(message.get("subject", ""))
    if not mailbox_accepts_message(mailbox=mailbox, sender=sender, subject=subject):
        return 0, 0
    encoded_message_id = quote(message_id, safe="")
    path = f"/v1.0/me/messages/{encoded_message_id}/attachments"
    url = f"{_GRAPH_ORIGIN}{path}?{urlencode({'$select': 'id,name,size,contentType,isInline'})}"
    created = duplicates = pages = 0
    while url:
        pages += 1
        if pages > 10:
            raise GraphMailboxError("A lista de anexos excedeu 10 páginas; sincronização pausada.")
        _validated_url(url, path)
        data = get_json(url, access_token, _MAX_ATTACHMENT_JSON)
        rows = data.get("value")
        if not isinstance(rows, list):
            raise GraphMailboxError("O Graph retornou anexos sem lista válida.")
        for attachment in rows:
            if not isinstance(attachment, dict):
                raise GraphMailboxError("O Graph retornou metadados de anexo inválidos.")
            kind = attachment.get("@odata.type")
            if kind not in {"#microsoft.graph.fileAttachment", "microsoft.graph.fileAttachment"}:
                raise GraphMailboxError("Esta mensagem contém anexo Graph não suportado.")
            identifier, name, size = (
                attachment.get("id"),
                attachment.get("name"),
                attachment.get("size"),
            )
            if not isinstance(identifier, str) or not isinstance(name, str) or not name:
                raise GraphMailboxError("O Graph retornou anexo sem identificação/nome.")
            if (
                isinstance(size, bool)
                or not isinstance(size, int)
                or size <= 0
                or size > MAX_EMAIL_ATTACHMENT_BYTES
            ):
                raise GraphMailboxError("Anexo Graph sem tamanho válido ou acima de 25 MB.")
            part_id = _opaque_identity("", identifier)
            delivery_id = _opaque_identity("graph:", message_id)
            if mailbox.items.filter(message_id=delivery_id, part_id=part_id).exists():
                duplicates += 1
                continue
            attachment_path = f"{path}/{quote(identifier, safe='')}/$value"
            raw_url = _validated_url(f"{_GRAPH_ORIGIN}{attachment_path}", attachment_path)
            payload = get_bytes(raw_url, access_token, MAX_EMAIL_ATTACHMENT_BYTES + 1)
            if len(payload) != size:
                raise GraphMailboxError("O tamanho do anexo Graph não confere; cursor preservado.")
            receipt = receive_email_attachment(
                mailbox=mailbox,
                message_id=delivery_id,
                part_id=part_id,
                filename=name,
                payload=payload,
                sender=sender,
                subject=subject,
                received_at=received_at,
                declared_type=str(attachment.get("contentType", "")),
            )
            created += int(receipt.created)
            duplicates += int(not receipt.created)
        next_link = data.get("@odata.nextLink")
        url = _validated_url(next_link, path) if isinstance(next_link, str) else ""
    return created, duplicates


def poll_graph_mailbox(
    *,
    mailbox: Mailbox,
    max_pages: int = 3,
    get_json: Callable[[str, str, int], dict[str, object]] = _get_json,
    get_bytes: Callable[[str, str, int], bytes] = _get_bytes,
    refresh: Callable[..., tuple[str, str]] = refresh_access_token,
) -> GraphPollResult:
    """Commit the provider checkpoint after all attachments in each page are stored."""
    if mailbox.provider != Mailbox.Provider.MS365_GRAPH:
        raise ValidationError("Esta caixa não usa Microsoft Graph.")
    if not mailbox.active or mailbox.status != Mailbox.Status.ACTIVE or mailbox.since is None:
        raise ValidationError("Autorize, escolha a data inicial e ative esta caixa primeiro.")
    if not 1 <= max_pages <= 10:
        raise ValidationError("Escolha entre 1 e 10 páginas por sincronização.")
    try:
        cursor_url = _cursor(mailbox)
        access_token, rotated_credential = refresh(
            mailbox.provider, mailbox.credential, app=mailbox.oauth_app
        )
        if rotated_credential != mailbox.credential:
            mailbox.credential = rotated_credential
            mailbox.save(update_fields=["credential", "updated_at"])
        pages = messages = created = duplicates = 0
        complete = False
        for _ in range(max_pages):
            _validated_url(cursor_url, _delta_path(mailbox))
            page = get_json(cursor_url, access_token, _MAX_DELTA_JSON)
            rows = page.get("value")
            if not isinstance(rows, list):
                raise GraphMailboxError("O Graph retornou uma página de mensagens inválida.")
            for message in rows:
                if not isinstance(message, dict):
                    raise GraphMailboxError("O Graph retornou uma mensagem inválida.")
                if "@removed" in message:
                    continue
                received_at = _received_at(message)
                if received_at < mailbox.since:
                    continue
                has_attachments = message.get("hasAttachments")
                if not isinstance(has_attachments, bool):
                    raise GraphMailboxError("O Graph não informou se a mensagem possui anexos.")
                messages += 1
                # Graph hasAttachments is false for inline-only attachments; the
                # attachment list must still be inspected to avoid missing them.
                new, old = _attachments(
                    mailbox=mailbox,
                    message=message,
                    received_at=received_at,
                    access_token=access_token,
                    get_json=get_json,
                    get_bytes=get_bytes,
                )
                created += new
                duplicates += old
            next_link = page.get("@odata.nextLink")
            delta_link = page.get("@odata.deltaLink")
            if isinstance(next_link, str) == isinstance(delta_link, str):
                raise GraphMailboxError("O Graph não informou uma continuidade única da página.")
            continuation = next_link if isinstance(next_link, str) else delta_link
            assert isinstance(continuation, str)
            cursor_url = _validated_url(continuation, _delta_path(mailbox))
            complete = isinstance(delta_link, str)
            mailbox.cursor = json.dumps(
                {
                    "version": 1,
                    "provider": Mailbox.Provider.MS365_GRAPH,
                    "folder": mailbox.folder,
                    "since": mailbox.since.isoformat(),
                    "url": cursor_url,
                }
            )
            mailbox.save(update_fields=["cursor", "updated_at"])
            mark_success(mailbox)
            pages += 1
            if complete:
                break
        return GraphPollResult(pages, messages, created, duplicates, complete)
    except (GraphMailboxError, MailboxOAuthError) as exc:
        transient = isinstance(exc, (GraphTemporaryError, MailboxOAuthTemporaryError))
        mark_failure(
            mailbox,
            str(exc),
            transient=transient,
            retry_seconds=getattr(exc, "retry_seconds", 0),
        )
        raise
