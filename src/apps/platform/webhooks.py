"""Provider-facing webhook endpoints kept separate from the authenticated console."""

from __future__ import annotations

import hmac
import json
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponseNotFound, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.platform.payments import AsaasWebhookPayloadError, process_asaas_webhook


@csrf_exempt
@require_POST
def asaas(request: HttpRequest) -> JsonResponse | HttpResponseNotFound:
    """Accept one authenticated Asaas delivery and return quickly for its retry queue."""

    expected_token = str(settings.ASAAS_WEBHOOK_TOKEN)
    if not expected_token:
        return HttpResponseNotFound()
    observed_token = request.headers.get("asaas-access-token", "")
    if not hmac.compare_digest(observed_token, expected_token):
        return JsonResponse({"detail": "Unauthorized."}, status=401)
    if not request.content_type.lower().startswith("application/json"):
        return JsonResponse({"detail": "Expected JSON."}, status=415)
    if len(request.body) > 64_000:
        return JsonResponse({"detail": "Payload too large."}, status=413)
    try:
        payload: Any = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    try:
        outcome = process_asaas_webhook(payload=payload)
    except AsaasWebhookPayloadError:
        return JsonResponse({"detail": "Invalid payment event."}, status=400)
    return JsonResponse(
        {
            "status": "duplicate" if outcome.duplicate else outcome.processing_status,
            "error_code": outcome.error_code,
        }
    )
