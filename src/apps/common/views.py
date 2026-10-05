from __future__ import annotations

import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

_readiness_result: tuple[float, dict[str, str]] | None = None


def csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    """Return a recoverable, branded response without exposing CSRF internals."""

    del reason
    if request.path.startswith("/api/"):
        return JsonResponse({"detail": "Envio não confirmado."}, status=403)
    referer = request.META.get("HTTP_REFERER", "")
    retry_url = referer if url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ) else reverse("hub:dashboard" if request.user.is_authenticated else "hub:home")
    return render(
        request,
        "hub/csrf_failure.html",
        {"retry_url": retry_url, "theme_next": retry_url},
        status=403,
    )


def _is_api_request(request: HttpRequest) -> bool:
    return request.path.startswith("/api/")


def _secure_error_response(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _render_error_page(
    request: HttpRequest,
    *,
    status_code: int,
    eyebrow: str,
    heading: str,
    message: str,
    primary_url: str,
    primary_label: str,
    secondary_url: str = "",
    secondary_label: str = "",
) -> HttpResponse:
    response = render(
        request,
        "hub/error_page.html",
        {
            "status_code": status_code,
            "eyebrow": eyebrow,
            "heading": heading,
            "message": message,
            "primary_url": primary_url,
            "primary_label": primary_label,
            "secondary_url": secondary_url,
            "secondary_label": secondary_label,
        },
        status=status_code,
    )
    return _secure_error_response(response)


def _error_home(request: HttpRequest) -> tuple[str, str]:
    if request.user.is_authenticated:
        return reverse("hub:dashboard"), "Voltar ao escritório"
    return reverse("hub:home"), "Ir para a página inicial"


def bad_request(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Render a recoverable 400 without reflecting suspicious request details."""

    del exception
    if _is_api_request(request):
        return _secure_error_response(
            JsonResponse({"detail": "Solicitação inválida."}, status=400)
        )
    primary_url, primary_label = _error_home(request)
    return _render_error_page(
        request,
        status_code=400,
        eyebrow="SOLICITAÇÃO NÃO RECONHECIDA",
        heading="Não foi possível abrir esta solicitação",
        message="O endereço ou os dados enviados não estão em um formato que o CICA consegue usar.",
        primary_url=primary_url,
        primary_label=primary_label,
    )


def permission_denied(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Render a neutral 403 without disclosing protected-resource details."""

    del exception
    if _is_api_request(request):
        return _secure_error_response(JsonResponse({"detail": "Acesso negado."}, status=403))
    primary_url, primary_label = _error_home(request)
    return _render_error_page(
        request,
        status_code=403,
        eyebrow="ACESSO RESTRITO",
        heading="Você não pode abrir esta área",
        message="Volte ao seu espaço de trabalho ou entre com uma conta autorizada.",
        primary_url=primary_url,
        primary_label=primary_label,
    )


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Keep missing and inaccessible resources indistinguishable to the caller."""

    del exception
    if _is_api_request(request):
        return _secure_error_response(JsonResponse({"detail": "Não encontrado."}, status=404))
    primary_url, primary_label = _error_home(request)
    return _render_error_page(
        request,
        status_code=404,
        eyebrow="PÁGINA NÃO ENCONTRADA",
        heading="Não encontramos este conteúdo",
        message=(
            "O endereço pode estar incorreto, o conteúdo pode ter sido removido "
            "ou seu acesso pode ter mudado."
        ),
        primary_url=primary_url,
        primary_label=primary_label,
    )


def server_error(request: HttpRequest) -> HttpResponse:
    """Return a database-independent recovery path without exposing the exception."""

    if _is_api_request(request):
        return _secure_error_response(
            JsonResponse({"detail": "Serviço temporariamente indisponível."}, status=500)
        )
    try:
        return _render_error_page(
            request,
            status_code=500,
            eyebrow="FALHA TEMPORÁRIA",
            heading="Não foi possível concluir agora",
            message=(
                "Nada precisa ser reenviado às pressas. Tente abrir esta página novamente; "
                "se a falha continuar, informe o horário ao suporte."
            ),
            primary_url=request.path or reverse("hub:home"),
            primary_label="Tentar novamente",
            secondary_url=reverse("hub:home"),
            secondary_label="Ir para a página inicial",
        )
    except Exception:
        # The final fallback cannot depend on templates, context processors, the
        # database or URL reversing: any of them may be the source of the 500.
        response = HttpResponse(
            '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>Falha temporária · CICA</title></head><body><main>"
            "<h1>Não foi possível concluir agora</h1>"
            "<p>Tente novamente em alguns instantes.</p>"
            '<p><a href="/">Ir para a página inicial</a></p>'
            "</main></body></html>",
            status=500,
            content_type="text/html; charset=utf-8",
        )
        return _secure_error_response(response)


def _run_readiness_checks() -> dict[str, str]:
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
    return checks


def readiness_checks() -> dict[str, str]:
    """Run the dependency probes, reusing a recent result within the same worker.

    The endpoint is public by design, so without memoisation every anonymous request
    would cost a database round trip and a cache write. A per-process TTL bounds that
    without introducing a throttle, which would itself depend on the cache being up.
    """

    global _readiness_result

    ttl = settings.HEALTH_READINESS_CACHE_SECONDS
    now = time.monotonic()
    cached = _readiness_result
    if ttl > 0 and cached is not None and now - cached[0] < ttl:
        return cached[1]

    checks = _run_readiness_checks()
    _readiness_result = (now, checks)
    return checks


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
        checks = readiness_checks()
        healthy = all(result == "ok" for result in checks.values())
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
