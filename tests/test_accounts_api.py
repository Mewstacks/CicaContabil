from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.mark.django_db
def test_user_email_is_normalized() -> None:
    user = User.objects.create_user("Mixed.Case@Example.COM", "a-strong-test-password")
    assert user.email == "mixed.case@example.com"


@pytest.mark.django_db
def test_session_login_requires_csrf_and_returns_user(user: User) -> None:
    client = APIClient(enforce_csrf_checks=True)
    missing_csrf = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "correct-horse-battery-staple"},
        format="json",
    )
    assert missing_csrf.status_code == 403

    csrf_response = client.get("/api/v1/auth/csrf/")
    token = csrf_response.data["csrf_token"]
    login_response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "correct-horse-battery-staple"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert login_response.status_code == 200
    assert login_response.data["email"] == "user@example.com"

    me_response = client.get("/api/v1/auth/me/")
    assert me_response.status_code == 200
    assert me_response.data["id"] == str(user.id)


@pytest.mark.django_db
def test_login_error_does_not_reveal_account_existence(user: User) -> None:
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/v1/auth/csrf/").data["csrf_token"]
    response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "wrong-password"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 401
    assert response.data["error"]["code"] == "invalid_credentials"
    assert user.email not in str(response.data)


@pytest.mark.django_db
def test_session_login_accepts_a_unique_full_name(user: User) -> None:
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/v1/auth/csrf/").data["csrf_token"]
    response = client.post(
        "/api/v1/auth/login/",
        {"identifier": user.full_name, "password": "correct-horse-battery-staple"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
    assert response.data["id"] == str(user.id)


@pytest.mark.django_db
def test_session_login_rejects_an_ambiguous_full_name(user: User) -> None:
    User.objects.create_user(
        "another@example.test", "correct-horse-battery-staple", full_name=user.full_name
    )
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/v1/auth/csrf/").data["csrf_token"]
    response = client.post(
        "/api/v1/auth/login/",
        {"identifier": user.full_name, "password": "correct-horse-battery-staple"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_me_patch_updates_full_name_only(user: User) -> None:
    client = APIClient()
    client.force_authenticate(user)
    response = client.patch(
        "/api/v1/auth/me/",
        {
            "full_name": "Renamed User",
            "email": "attacker@evil.example",  # read-only
            "is_staff": True,  # not a serializer field
        },
        format="json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.full_name == "Renamed User"
    assert user.email == "user@example.com"
    assert user.is_staff is False


@pytest.mark.django_db
def test_logout_ends_the_session(user: User) -> None:
    client = APIClient(enforce_csrf_checks=True)
    login_token = client.get("/api/v1/auth/csrf/").data["csrf_token"]
    client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "correct-horse-battery-staple"},
        format="json",
        HTTP_X_CSRFTOKEN=login_token,
    )
    assert client.get("/api/v1/auth/me/").status_code == 200

    logout_token = client.get("/api/v1/auth/csrf/").data["csrf_token"]
    logout_response = client.post("/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=logout_token)
    assert logout_response.status_code == 204
    assert client.get("/api/v1/auth/me/").status_code == 403


@pytest.mark.django_db
def test_an_unknown_identifier_costs_the_same_password_hash_as_a_known_one() -> None:
    """Returning before check_password would make the login form an enumeration oracle."""

    from unittest.mock import patch

    from apps.accounts.backends import IdentifierBackend

    User.objects.create_user(email="known@example.test", password="safe-password-123456")
    backend = IdentifierBackend()

    with patch.object(User, "set_password") as dummy_hash:
        assert backend.authenticate(None, username="nobody@example.test", password="guess") is None

    assert dummy_hash.call_count == 1
