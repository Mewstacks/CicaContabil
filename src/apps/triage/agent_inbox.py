"""Agent endpoint for the watched intake folder (same HMAC/mTLS gate as every agent route)."""

from __future__ import annotations

from urllib.parse import unquote

from django.core.exceptions import ValidationError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.intelligence.agent_v2 import agent_error, authenticated_agent
from apps.triage.inbox import INBOX_MAX_BYTES, receive_inbox_file


@csrf_exempt
@require_POST
def upload_inbox_file(request: HttpRequest) -> JsonResponse:
    """Body = raw file bytes; name and sha256 travel in headers so the signature covers both."""

    agent = authenticated_agent(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    try:
        declared = int(request.headers.get("Content-Length") or 0)
    except ValueError:
        declared = 0
    if declared > INBOX_MAX_BYTES:
        return agent_error("Arquivo acima do limite da pasta de entrada.", 413)
    try:
        result = receive_inbox_file(
            organization=agent.organization,
            filename=unquote(request.headers.get("X-Inbox-Filename", "")),
            payload=request.body,
            claimed_sha256=request.headers.get("X-Inbox-Sha256", ""),
        )
    except ValidationError as exc:
        # 422: refused for good; the agent moves the file to _quarentena and does not retry.
        return agent_error("; ".join(exc.messages), 422)
    response = JsonResponse(
        {"status": "duplicate" if result.duplicate else "received", "item": str(result.item.pk)}
    )
    response["Cache-Control"] = "no-store"
    return response
