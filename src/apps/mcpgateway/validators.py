"""Validador OAuth do gateway: o refresh tambem respeita a conta desativada (D-333)."""

from __future__ import annotations

from typing import Any

from oauth2_provider.oauth2_validators import OAuth2Validator


class McpValidator(OAuth2Validator):
    def validate_refresh_token(
        self, refresh_token: str, client: Any, request: Any, *args: Any, **kwargs: Any
    ) -> bool:
        if not super().validate_refresh_token(refresh_token, client, request, *args, **kwargs):
            return False
        user = getattr(request, "user", None)
        return bool(user is not None and user.is_active)
