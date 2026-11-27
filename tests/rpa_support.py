"""Apoio dos testes do agente RPA: escritório com módulos ligados e um agente assinado."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import ProductModule
from apps.intelligence.agents import issue_enrollment, redeem_enrollment
from apps.organizations.models import Organization


def enable(organization: Organization, *codes: str) -> None:
    for code in codes:
        ProductModule.objects.update_or_create(
            organization=organization, code=code, defaults={"enabled": True}
        )


class SignedAgent:
    """Agente HMAC inscrito num escritório; ``post`` assina como o serviço Windows."""

    def __init__(self, organization: Organization) -> None:
        credentials = redeem_enrollment(
            code=issue_enrollment(organization=organization).code,
            label="Servidor Domínio",
            fingerprint=f"device-{organization.slug}",
        )
        self.agent_id = credentials.agent_id
        self.secret = credentials.shared_secret
        self.client = Client()

    def post(self, name: str, payload: dict[str, Any], *args: Any) -> Any:
        body = json.dumps(payload).encode()
        timestamp = str(int(timezone.now().timestamp()))
        signature = hmac.new(
            self.secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        return self.client.post(
            reverse(name, args=args),
            data=body,
            content_type="application/json",
            secure=True,
            headers={
                "X-Hub-Agent-ID": str(self.agent_id),
                "X-Hub-Agent-Timestamp": timestamp,
                "X-Hub-Agent-Signature": signature,
            },
        )
