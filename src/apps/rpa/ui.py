"""Portão comum das telas dos blocos RPA (Folha, FGTS, DET, FAP, Admissões).

Mesmo idioma do Fechamento: ``office_required`` na porta, ``_module_page_context`` no portão do
módulo e do colaborador, escrita só para quem tem papel operacional. Cada bloco passa o código
do seu módulo; módulo desligado no escritório responde 403 com a tela de indisponível.
"""

from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from apps.hub.models import ClientCompany
from apps.hub.module_catalog import definition
from apps.hub.views import _module_page_context, refuse
from apps.organizations.models import Membership, Organization

WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
    Membership.Role.OPERATOR,
}
ADMIN_ROLES = {Membership.Role.OWNER, Membership.Role.ADMIN}


def gate(request: HttpRequest, module_code: str) -> tuple[dict[str, object], HttpResponse | None]:
    context, blocked = _module_page_context(request, definition(module_code))
    if blocked is None:
        context["can_write"] = has_role(context, WRITE_ROLES)
        context["can_admin"] = has_role(context, ADMIN_ROLES)
    return context, blocked


def has_role(context: dict[str, object], roles: set[Any]) -> bool:
    if context.get("support_session") is not None:
        return bool(context.get("support_can_mutate"))
    membership = context.get("membership")
    return isinstance(membership, Membership) and membership.role in roles


def need_write(request: HttpRequest, context: dict[str, object]) -> HttpResponse | None:
    if not context.get("can_write"):
        return refuse(request, "Seu acesso só consulta.")
    return None


def need_admin(request: HttpRequest, context: dict[str, object]) -> HttpResponse | None:
    if not context.get("can_admin"):
        return refuse(request, "Só o administrador do escritório altera isto.")
    return None


def office(context: dict[str, object]) -> Organization:
    return cast(Organization, context["office"])


def companies(context: dict[str, object]) -> QuerySet[ClientCompany]:
    return cast("QuerySet[ClientCompany]", context["companies"])
