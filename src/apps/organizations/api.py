from __future__ import annotations

from typing import cast

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import serializers, viewsets
from rest_framework.throttling import BaseThrottle, UserRateThrottle

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.organizations.models import Membership, Organization


class OrganizationCreateThrottle(UserRateThrottle):
    scope = "organization_create"


class OrganizationSerializer(serializers.ModelSerializer[Organization]):
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "is_active", "current_user_role", "created_at")
        read_only_fields = ("id", "is_active", "current_user_role", "created_at")

    def get_current_user_role(self, organization: Organization) -> str | None:
        request = self.context["request"]
        membership = next(
            (
                item
                for item in organization.memberships.all()
                if item.user_id == request.user.id and item.is_active
            ),
            None,
        )
        return membership.role if membership else None

    @transaction.atomic
    def create(self, validated_data: dict[str, object]) -> Organization:
        organization = Organization.objects.create(**validated_data)
        Membership.objects.create(
            organization=organization,
            user=self.context["request"].user,
            role=Membership.Role.OWNER,
        )
        record_event(
            action="organization.created",
            actor=self.context["request"].user,
            organization=organization,
            target=organization,
        )
        return organization


class OrganizationViewSet(viewsets.ModelViewSet[Organization]):
    queryset = Organization.objects.none()
    serializer_class = OrganizationSerializer
    http_method_names = ["get", "post", "head", "options"]
    lookup_value_converter = "uuid"

    def get_queryset(self) -> QuerySet[Organization]:
        if getattr(self, "swagger_fake_view", False):
            return Organization.objects.none()
        user = cast(User, self.request.user)
        return (
            Organization.objects.filter(
                memberships__user=user,
                memberships__is_active=True,
            )
            .prefetch_related("memberships")
            .distinct()
        )

    def get_throttles(self) -> list[BaseThrottle]:
        if self.action == "create":
            return [OrganizationCreateThrottle()]
        return super().get_throttles()
