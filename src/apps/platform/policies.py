from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Concatenate, cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.platform.services import has_platform_role


def platform_required[**ViewParams](
    *roles: str,
) -> Callable[
    [Callable[Concatenate[HttpRequest, ViewParams], HttpResponse]],
    Callable[Concatenate[HttpRequest, ViewParams], HttpResponse],
]:
    def decorator(
        view: Callable[Concatenate[HttpRequest, ViewParams], HttpResponse],
    ) -> Callable[Concatenate[HttpRequest, ViewParams], HttpResponse]:
        @wraps(view)
        def wrapped(
            request: HttpRequest,
            *args: ViewParams.args,
            **kwargs: ViewParams.kwargs,
        ) -> HttpResponse:
            if not request.user.is_authenticated:
                return redirect(f"{reverse('hub:login')}?next={request.path}")
            if not has_platform_role(request.user, *roles):
                return render(request, "hub/forbidden.html", status=403)
            return view(request, *args, **kwargs)

        return cast(
            Callable[Concatenate[HttpRequest, ViewParams], HttpResponse],
            wrapped,
        )

    return cast(
        Callable[
            [Callable[Concatenate[HttpRequest, ViewParams], HttpResponse]],
            Callable[Concatenate[HttpRequest, ViewParams], HttpResponse],
        ],
        decorator,
    )
