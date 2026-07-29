from __future__ import annotations

from django.test import RequestFactory, override_settings

from apps.common.network import client_ip


@override_settings(FLY_APP_NAME="test-app")
def test_client_ip_prefers_valid_fly_header_and_rejects_invalid_values() -> None:
    request = RequestFactory().get(
        "/",
        HTTP_FLY_CLIENT_IP="203.0.113.9",
        REMOTE_ADDR="10.0.0.2",
    )
    assert client_ip(request) == "203.0.113.9"

    invalid_edge = RequestFactory().get(
        "/",
        HTTP_FLY_CLIENT_IP="not-an-ip",
        REMOTE_ADDR="2001:db8::1",
    )
    assert client_ip(invalid_edge) == "2001:db8::1"


def test_client_ip_does_not_trust_fly_header_outside_fly() -> None:
    request = RequestFactory().get(
        "/",
        HTTP_FLY_CLIENT_IP="203.0.113.9",
        REMOTE_ADDR="127.0.0.1",
    )
    assert client_ip(request) == "127.0.0.1"
