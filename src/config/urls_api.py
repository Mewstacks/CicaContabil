from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.api import CsrfTokenView, LoginView, LogoutView, MeView
from apps.common.views import LivenessView, ReadinessView
from apps.hub.api import ClientCompanyViewSet
from apps.intelligence.agent_api import enroll as agent_enroll
from apps.intelligence.agent_api import sync as agent_sync
from apps.intelligence.api import mcp_endpoint
from apps.organizations.api import OrganizationViewSet
from apps.privacy.api import ConsentViewSet, DataSubjectRequestViewSet, ProcessingPurposeViewSet

router = DefaultRouter(use_regex_path=False)
router.register("companies", ClientCompanyViewSet, basename="company")
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("privacy/purposes", ProcessingPurposeViewSet, basename="privacy-purpose")
router.register("privacy/consents", ConsentViewSet, basename="privacy-consent")
router.register("privacy/requests", DataSubjectRequestViewSet, basename="privacy-request")

urlpatterns = [
    path("health/live/", LivenessView.as_view(), name="health-live"),
    path("health/ready/", ReadinessView.as_view(), name="health-ready"),
    path("intelligence/mcp/", mcp_endpoint, name="intelligence-mcp"),
    path("intelligence/agent/enroll/", agent_enroll, name="intelligence-agent-enroll"),
    path("intelligence/agent/sync/", agent_sync, name="intelligence-agent-sync"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("", include(router.urls)),
]
