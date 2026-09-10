from __future__ import annotations

from typing import cast

from django.db.models import QuerySet
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.hub.controlplane import authorization_is_fresh, company_queryset_for_membership
from apps.hub.models import ClientCompany
from apps.organizations.models import Membership
from apps.organizations.permissions import HasOrganizationContext
from apps.organizations.viewsets import OrganizationScopedViewSet


class HasFreshHubAuthorization(HasOrganizationContext):
    """Reject a CRMew-managed installation after its signed cache expires."""

    message = "A autorização desta instalação precisa ser renovada pelo CRMew."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not super().has_permission(request, view):
            return False
        membership = cast(Membership, request.organization_membership)  # type: ignore[attr-defined]
        return authorization_is_fresh(membership.organization)


class ClientCompanySerializer(serializers.ModelSerializer[ClientCompany]):
    class Meta:
        model = ClientCompany
        fields = (
            "id",
            "name",
            "cnpj_masked",
            "dominio_code",
            "active",
            "last_dominio_sync_at",
        )
        read_only_fields = fields


class ClientCompanyViewSet(OrganizationScopedViewSet[ClientCompany]):
    """Read-only company selector API with tenant and CRMew-grant enforcement."""

    queryset = ClientCompany.objects.all().order_by("name")
    serializer_class = ClientCompanySerializer
    permission_classes = [HasFreshHubAuthorization]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self) -> QuerySet[ClientCompany]:
        queryset = super().get_queryset()
        membership = cast(Membership, self.request.organization_membership)  # type: ignore[attr-defined]
        allowed_ids = company_queryset_for_membership(membership).values("id")
        return queryset.filter(id__in=allowed_ids)
