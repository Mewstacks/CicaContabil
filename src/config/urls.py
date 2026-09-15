from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns: list[URLPattern | URLResolver] = [
    path("", include("apps.hub.urls")),
    path("app/ia/", include("apps.intelligence.urls")),
    path("mfa/", include("apps.accounts.urls")),
    path("platform/", include("apps.platform.urls")),
    path("api/v1/", include("config.urls_api")),
    path("api/agent/v2/", include("config.urls_agent_v2")),
]

if settings.API_DOCS_ENABLED:
    urlpatterns.extend(
        [
            path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
            path(
                "api/docs/",
                SpectacularSwaggerView.as_view(url_name="api-schema"),
                name="api-docs",
            ),
        ]
    )

if settings.ADMIN_ENABLED:
    urlpatterns.append(path("admin/", admin.site.urls))
