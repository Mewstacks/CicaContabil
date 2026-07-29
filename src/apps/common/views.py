from __future__ import annotations

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class LivenessView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]
    throttle_classes: list[type] = []

    @extend_schema(
        responses=inline_serializer(
            name="Liveness",
            fields={"status": serializers.CharField()},
        )
    )
    def get(self, request: object) -> Response:
        return Response({"status": "ok"})


class ReadinessView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]
    throttle_classes: list[type] = []

    @extend_schema(
        responses=inline_serializer(
            name="Readiness",
            fields={
                "status": serializers.CharField(),
                "checks": serializers.DictField(
                    child=serializers.CharField(),
                ),
            },
        )
    )
    def get(self, request: object) -> Response:
        checks: dict[str, str] = {}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "unavailable"

        try:
            cache.set("health:ready", "ok", timeout=10)
            checks["cache"] = "ok" if cache.get("health:ready") == "ok" else "unavailable"
        except Exception:
            checks["cache"] = "unavailable"

        healthy = all(result == "ok" for result in checks.values())
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
