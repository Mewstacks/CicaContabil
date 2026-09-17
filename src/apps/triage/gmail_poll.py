"""Bounded Gmail/Workspace attachment reader with resumable history checkpoints."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
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
from apps.triage.poll_state import mark_failure, retry_hint_seconds

_ORIGIN = "https://gmail.googleapis.com"
_BASE = "/gmail/v1/users/me"
_MAX_JSON = 36_000_000  # 25 MB attachments can be base64-encoded inside JSON.


class GmailMailboxError(ValueError):
    """Operational error without credential, response body or customer data."""


class GmailHistoryExpired(GmailMailboxError):
    """Google discarded the incremental checkpoint; a full resync is needed."""


class GmailTemporaryError(GmailMailboxError):
    def __init__(self, message: str, *, retry_seconds: int = 0) -> None:
        super().__init__(message)
        self.retry_seconds = retry_seconds


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _get_json(url: str, access_token: str, limit: int) -> dict[str, object]:
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname != "gmail.googleapis.com"
        or parts.port is not None
        or parts.username
        or parts.password
        or parts.fragment
        or not parts.path.startswith(_BASE + "/")
    ):
        raise GmailMailboxError("Endereço Gmail fora da caixa autorizada.")
    request = Request(  # noqa: S310 - origin and path validated above
        url, headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    )
    try:
        with build_opener(_NoRedirect).open(request, timeout=20) as response:
            raw = response.read(limit + 1)
    except HTTPError as exc:
        if exc.code == 404 and parts.path == _BASE + "/history":
            raise GmailHistoryExpired(
                "Histórico Gmail expirou; será feita nova sincronização."
            ) from exc
        if exc.code == 429 or 500 <= exc.code < 600:
            raise GmailTemporaryError(
                "Gmail está temporariamente indisponível; a caixa tentará novamente.",
                retry_seconds=retry_hint_seconds(exc.headers.get("Retry-After")),
            ) from exc
        raise GmailMailboxError(
            "Gmail não respondeu. Confira a conexão e tente novamente."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise GmailTemporaryError("Gmail não respondeu; a caixa tentará novamente.") from exc
    if len(raw) > limit:
        raise GmailMailboxError("Resposta Gmail acima do limite seguro; sincronização pausada.")
    try:
        result = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GmailMailboxError("Gmail retornou dados inválidos.") from exc
    if not isinstance(result, dict):
        raise GmailMailboxError("Gmail retornou resposta inválida.")
    return result


@dataclass(frozen=True)
class GmailPollResult:
    pages: int
    messages: int
    attachments_created: int
    duplicates: int
    round_complete: bool


def _url(path: str, **params: object) -> str:
    return _ORIGIN + _BASE + path + ("?" + urlencode(params) if params else "")


def _cursor(mailbox: Mailbox) -> dict[str, object]:
    if not mailbox.cursor:
        return {"mode": "new"}
    try:
        data = json.loads(mailbox.cursor)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise GmailMailboxError("Cursor Gmail inválido; reconecte a caixa.") from exc
    if (
        not isinstance(data, dict)
        or data.get("version") != 1
        or data.get("provider") != Mailbox.Provider.GMAIL_API
        or data.get("folder") != mailbox.folder
        or data.get("since") != mailbox.since.isoformat()
        or data.get("mode") not in {"full", "history"}
        or not isinstance(data.get("history_id"), str)
        or not data["history_id"].isdigit()
        or not isinstance(data.get("page_token", ""), str)
        or len(data.get("page_token", "")) > 4_096
    ):
        raise GmailMailboxError("Cursor Gmail não corresponde à pasta/data; reconecte.")
    return data


def _checkpoint(mailbox: Mailbox, *, mode: str, history_id: str, page_token: str = "") -> None:
    mailbox.cursor = json.dumps(
        {
            "version": 1,
            "provider": Mailbox.Provider.GMAIL_API,
            "folder": mailbox.folder,
            "since": mailbox.since.isoformat(),
            "mode": mode,
            "history_id": history_id,
            "page_token": page_token,
        }
    )
    mailbox.last_polled_at = timezone.now()
    mailbox.last_error = ""
    mailbox.poll_retry_after = None
    mailbox.poll_failure_count = 0
    mailbox.save(
        update_fields=[
            "cursor",
            "last_polled_at",
            "last_error",
            "poll_retry_after",
            "poll_failure_count",
            "updated_at",
        ]
    )


def _history_id(value: object) -> str:
    if not isinstance(value, str) or not value.isdigit() or len(value) > 40:
        raise GmailMailboxError("Gmail não informou um identificador de histórico válido.")
    return value


def _page_token(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or not value or len(value) > 4_096:
        raise GmailMailboxError("Gmail retornou paginação inválida.")
    return value


def _identity(prefix: str, value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 2_048:
        raise GmailMailboxError("Gmail não identificou mensagem ou anexo.")
    return prefix + hashlib.sha256(value.encode()).hexdigest()


def _payload(
    body: dict[str, object],
    *,
    message_id: str,
    token: str,
    get_json: Callable[[str, str, int], dict[str, object]],
) -> bytes:
    size = body.get("size")
    if (
        isinstance(size, bool)
        or not isinstance(size, int)
        or not 0 < size <= MAX_EMAIL_ATTACHMENT_BYTES
    ):
        raise GmailMailboxError("Anexo Gmail sem tamanho válido ou acima de 25 MB.")
    attachment_id = body.get("attachmentId")
    if isinstance(attachment_id, str) and attachment_id:
        attachment_path = (
            f"/messages/{quote(message_id, safe='')}/attachments/{quote(attachment_id, safe='')}"
        )
        body = get_json(
            _url(attachment_path),
            token,
            _MAX_JSON,
        )
        if body.get("size") != size:
            raise GmailMailboxError("O tamanho do anexo Gmail mudou; cursor preservado.")
    encoded = body.get("data")
    if not isinstance(encoded, str) or len(encoded) > (MAX_EMAIL_ATTACHMENT_BYTES * 4 // 3 + 8):
        raise GmailMailboxError("Gmail não entregou os bytes do anexo.")
    try:
        raw = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise GmailMailboxError("Anexo Gmail contém codificação inválida.") from exc
    if len(raw) != size:
        raise GmailMailboxError("O tamanho do anexo Gmail não confere; cursor preservado.")
    return raw


def _parts(part: dict[str, object], path: str = "root") -> list[tuple[str, dict[str, object]]]:
    found: list[tuple[str, dict[str, object]]] = []
    if isinstance(part.get("filename"), str) and part["filename"]:
        found.append((str(part.get("partId") or path), part))
    children = part.get("parts", [])
    if not isinstance(children, list) or len(children) > 100:
        raise GmailMailboxError("Estrutura de anexos Gmail acima do limite.")
    for index, child in enumerate(children):
        if not isinstance(child, dict):
            raise GmailMailboxError("Gmail retornou parte de anexo inválida.")
        if path.count("/") >= 12:
            raise GmailMailboxError("Estrutura de anexo Gmail profunda demais.")
        found.extend(_parts(child, f"{path}/{index}"))
    return found


def _message(
    mailbox: Mailbox,
    message_id: str,
    token: str,
    get_json: Callable[[str, str, int], dict[str, object]],
) -> tuple[int, int, bool]:
    data = get_json(
        _url(f"/messages/{quote(message_id, safe='')}", format="full"), token, _MAX_JSON
    )
    if data.get("id") != message_id:
        raise GmailMailboxError("Gmail retornou mensagem diferente da solicitada.")
    labels = data.get("labelIds")
    if not isinstance(labels, list) or mailbox.folder not in labels:
        return 0, 0, False  # Message moved out of the selected label during this round.
    timestamp = data.get("internalDate")
    if not isinstance(timestamp, str) or not timestamp.isdigit():
        raise GmailMailboxError("Gmail não informou data interna válida.")
    try:
        received_at = datetime.fromtimestamp(int(timestamp) / 1_000, UTC)
    except (OverflowError, ValueError, OSError) as exc:
        raise GmailMailboxError("Gmail informou data fora do intervalo.") from exc
    if received_at < mailbox.since:
        return 0, 0, False
    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise GmailMailboxError("Gmail não trouxe estrutura da mensagem.")
    headers = payload.get("headers", [])
    if not isinstance(headers, list) or len(headers) > 200:
        raise GmailMailboxError("Gmail retornou cabeçalhos inválidos.")
    header_map = {
        str(h.get("name", "")).lower(): str(h.get("value", ""))
        for h in headers
        if isinstance(h, dict)
    }
    if not mailbox_accepts_message(
        mailbox=mailbox,
        sender=header_map.get("from", ""),
        subject=header_map.get("subject", ""),
    ):
        return 0, 0, True
    created = duplicates = 0
    delivery_id = _identity("gmail:", message_id)
    for part_id, part in _parts(payload):
        item_part = _identity("", part_id)
        if mailbox.items.filter(message_id=delivery_id, part_id=item_part).exists():
            duplicates += 1
            continue
        body = part.get("body")
        if not isinstance(body, dict):
            raise GmailMailboxError("Gmail não trouxe dados do anexo.")
        raw = _payload(body, message_id=message_id, token=token, get_json=get_json)
        receipt = receive_email_attachment(
            mailbox=mailbox,
            message_id=delivery_id,
            part_id=item_part,
            filename=str(part["filename"]),
            payload=raw,
            sender=header_map.get("from", ""),
            subject=header_map.get("subject", ""),
            received_at=received_at,
            declared_type=str(part.get("mimeType", "")),
        )
        created += int(receipt.created)
        duplicates += int(not receipt.created)
    return created, duplicates, True


def poll_gmail_mailbox(
    *,
    mailbox: Mailbox,
    max_pages: int = 3,
    get_json: Callable[[str, str, int], dict[str, object]] = _get_json,
    refresh: Callable[..., tuple[str, str]] = refresh_access_token,
) -> GmailPollResult:
    """Store each page only after every named attachment has reached quarantine."""
    if mailbox.provider != Mailbox.Provider.GMAIL_API:
        raise ValidationError("Esta caixa não usa a API Gmail.")
    if not mailbox.active or mailbox.status != Mailbox.Status.ACTIVE or mailbox.since is None:
        raise ValidationError("Autorize, escolha a data inicial e ative esta caixa primeiro.")
    if (
        not mailbox.folder
        or len(mailbox.folder) > 160
        or any(c in mailbox.folder for c in "\r\n\x00")
    ):
        raise ValidationError("Escolha uma etiqueta Gmail válida.")
    if not 1 <= max_pages <= 10:
        raise ValidationError("Escolha entre 1 e 10 páginas por sincronização.")
    try:
        cursor = _cursor(mailbox)
        token, rotated = refresh(mailbox.provider, mailbox.credential, app=mailbox.oauth_app)
        if rotated != mailbox.credential:
            mailbox.credential = rotated
            mailbox.save(update_fields=["credential", "updated_at"])
        if cursor["mode"] == "new":
            profile = get_json(_url("/profile"), token, 64_000)
            history_id = _history_id(profile.get("historyId"))
            _checkpoint(mailbox, mode="full", history_id=history_id)
            cursor = _cursor(mailbox)
        pages = messages = created = duplicates = 0
        complete = False
        for _ in range(max_pages):
            mode = str(cursor["mode"])
            history_id = str(cursor["history_id"])
            params: dict[str, object] = {"maxResults": 20}
            if cursor["page_token"]:
                params["pageToken"] = cursor["page_token"]
            if mode == "full":
                params.update(
                    {"labelIds": mailbox.folder, "q": f"after:{int(mailbox.since.timestamp()) - 1}"}
                )
                url = _url("/messages", **params)
            else:
                params.update({"startHistoryId": history_id, "labelId": mailbox.folder})
                url = _url("/history", **params)
            try:
                page = get_json(url, token, 1_000_000)
            except GmailHistoryExpired:
                profile = get_json(_url("/profile"), token, 64_000)
                _checkpoint(mailbox, mode="full", history_id=_history_id(profile.get("historyId")))
                break
            rows = page.get("messages" if mode == "full" else "history", [])
            if not isinstance(rows, list) or len(rows) > 20:
                raise GmailMailboxError("Gmail retornou página de mensagens inválida.")
            ids: list[str] = []
            for row in rows:
                if not isinstance(row, dict):
                    raise GmailMailboxError("Gmail retornou registro inválido.")
                if mode == "full":
                    ids.append(str(row.get("id", "")))
                else:
                    for event_name in ("messagesAdded", "labelsAdded"):
                        events = row.get(event_name, [])
                        if not isinstance(events, list) or len(events) > 100:
                            raise GmailMailboxError("Gmail retornou histórico inválido.")
                        for event in events:
                            item = event.get("message") if isinstance(event, dict) else None
                            if not isinstance(item, dict):
                                raise GmailMailboxError("Gmail retornou evento inválido.")
                            ids.append(str(item.get("id", "")))
            if len(ids) > 2_000:
                raise GmailMailboxError("Histórico Gmail acima do limite por página.")
            for message_id in dict.fromkeys(ids):
                _identity("", message_id)
                new, old, included = _message(mailbox, message_id, token, get_json)
                created += new
                duplicates += old
                messages += int(included)
            next_page = _page_token(page.get("nextPageToken"))
            if mode == "history" and not next_page:
                history_id = _history_id(page.get("historyId"))
            next_mode = mode if next_page else "history"
            _checkpoint(mailbox, mode=next_mode, history_id=history_id, page_token=next_page)
            cursor = _cursor(mailbox)
            pages += 1
            complete = not next_page
            if complete:
                break
        return GmailPollResult(pages, messages, created, duplicates, complete)
    except (GmailMailboxError, MailboxOAuthError) as exc:
        mark_failure(
            mailbox,
            str(exc),
            transient=isinstance(exc, (GmailTemporaryError, MailboxOAuthTemporaryError)),
            retry_seconds=getattr(exc, "retry_seconds", 0),
        )
        raise
