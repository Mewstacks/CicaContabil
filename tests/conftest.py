from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db: object) -> User:
    return User.objects.create_user(
        email="USER@Example.COM",
        password="correct-horse-battery-staple",
        full_name="Example User",
    )


@pytest.fixture
def authenticated_client(api_client: APIClient, user: User) -> APIClient:
    api_client.force_authenticate(user)
    return api_client
