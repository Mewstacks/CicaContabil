from typing import cast
from urllib.parse import urlsplit

from django import template
from django.http import HttpRequest
from django.urls import reverse

register = template.Library()


@register.inclusion_tag("hub/workspace_navigation.html", takes_context=True)
def workspace_menu(context: template.Context) -> dict[str, object]:
    from apps.hub.navigation import workspace_navigation

    return {
        "groups": workspace_navigation(context),
        "request": context["request"],
        "copilot_enabled": context.get("copilot_enabled", False),
    }


@register.simple_tag(takes_context=True)
def back_url(context: template.Context, route: str, *alternate_routes: str) -> str:
    """Keep a list's filters without allowing another host or arbitrary destination."""
    fallback = reverse(route)
    request = cast(HttpRequest, context["request"])
    candidate = request.GET.get("return_to", "")
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return fallback
    if (
        candidate.startswith("/")
        and not candidate.startswith("//")
        and not parts.netloc
        and not parts.scheme
        and parts.path in {fallback, *(reverse(name) for name in alternate_routes)}
        and "\\" not in candidate
        and not any(ord(char) < 32 for char in candidate)
    ):
        return candidate
    return fallback
