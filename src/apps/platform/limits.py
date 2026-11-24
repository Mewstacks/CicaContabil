"""Limites do plano contratado (E3): empresas, usuários e e-CNPJ do escritório.

Fonte única: `Plan.limits` do contrato vigente (teste, ativo ou em carência). Chave ausente, nula
ou que não seja inteiro positivo = sem limite, que é o que todo plano e todo escritório de hoje
têm: nada muda para quem não tem limite configurado (L2 de docs/specs/produto-vendavel.md).

O limite é duro onde uma pessoa cria o registro (cadastro manual de empresa, carteira por
planilha, convite) e só informativo onde o dado chega por sincronização (Domínio): ali o uso
pode passar de 100% e o aviso aparece. Aviso em 80% e em 100%, como no Accurit (MIT).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.common.cnpj import normalize_cnpj
from apps.hub.commercial_capacity import calculate_commercial_capacity
from apps.hub.models import ClientCompany, OfficeCertificate
from apps.organizations.models import Membership, Organization
from apps.platform.models import Invitation, TenantContract

COMPANIES = "companies"
USERS = "users"
OFFICE_CERTIFICATES = "office_certificates"
LIMIT_KEYS = (COMPANIES, USERS, OFFICE_CERTIFICATES)
LABELS = {
    COMPANIES: "Empresas",
    USERS: "Usuários",
    OFFICE_CERTIFICATES: "e-CNPJ",
}
WARN_AT_PERCENT = 80

Level = Literal["ok", "warn", "full"]


@dataclass(frozen=True)
class LimitState:
    key: str
    limit: int | None
    used: int

    @property
    def label(self) -> str:
        return LABELS[self.key]

    @property
    def remaining(self) -> int | None:
        return None if self.limit is None else max(self.limit - self.used, 0)

    @property
    def percent(self) -> int | None:
        if self.limit is None:
            return None
        return min(round(self.used * 100 / self.limit), 999)

    @property
    def level(self) -> Level:
        if self.limit is None:
            return "ok"
        if self.used >= self.limit:
            return "full"
        return "warn" if self.used * 100 >= self.limit * WARN_AT_PERCENT else "ok"

    @property
    def message(self) -> str:
        if self.limit is None or self.level == "ok":
            return ""
        if self.level == "full":
            return f"{self.label}: limite do plano atingido ({self.used} de {self.limit})."
        return f"{self.label}: {self.used} de {self.limit} do plano."


def current_contract(organization: Organization) -> TenantContract | None:
    return (
        TenantContract.objects.filter(
            organization=organization,
            status__in=[
                TenantContract.Status.TRIAL,
                TenantContract.Status.ACTIVE,
                TenantContract.Status.GRACE,
            ],
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )


def plan_limits(organization: Organization) -> dict[str, int]:
    contract = current_contract(organization)
    raw = contract.plan.limits if contract is not None and contract.plan is not None else {}
    if not isinstance(raw, dict):
        return {}
    found: dict[str, int] = {}
    for key in LIMIT_KEYS:
        value = raw.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            found[key] = value
    return found


def active_company_roots(organization: Organization) -> int:
    """Empresas ativas por **raiz de CNPJ**: a filial não conta (D-109, `proposta-precos.md`).

    A contagem de raízes é a de `calculate_commercial_capacity` (a mesma do consumo em
    Configurações). Empresa sem raiz preenchida (CNPJ ausente ou inválido) entra aqui uma a uma:
    o contador de consumo as mostra à parte e não inventa raiz, mas o limite não pode ser
    contornado deixando o CNPJ em branco.
    """

    capacity = calculate_commercial_capacity(organization=organization)
    return capacity.active_company_roots + capacity.active_companies_without_root


def company_roots_in_use(organization: Organization) -> set[str]:
    return set(
        ClientCompany.objects.filter(organization=organization, active=True)
        .exclude(commercial_root_cnpj="")
        .values_list("commercial_root_cnpj", flat=True)
    )


def adds_company_root(organization: Organization, cnpj_raw: str) -> bool:
    """Whether a new company with this CNPJ takes plan room (a new root) or is just a branch."""

    try:
        root = normalize_cnpj(cnpj_raw)[:8]
    except ValidationError:
        return True
    return root not in company_roots_in_use(organization)


def usage(organization: Organization, key: str) -> int:
    if key == COMPANIES:
        return active_company_roots(organization)
    if key == USERS:
        seats = Membership.objects.filter(organization=organization, is_active=True).count()
        pending = Invitation.objects.filter(
            organization=organization,
            status=Invitation.Status.PENDING,
            expires_at__gt=timezone.now(),
        ).count()
        return seats + pending
    if key == OFFICE_CERTIFICATES:
        return OfficeCertificate.objects.filter(
            organization=organization, revoked_at__isnull=True, valid_until__gt=timezone.now()
        ).count()
    raise KeyError(key)


def state(organization: Organization, key: str) -> LimitState:
    limit = plan_limits(organization).get(key)
    # No limit, nothing to count: every page of an office without a limit stays as cheap as before.
    return LimitState(key=key, limit=limit, used=usage(organization, key) if limit else 0)


def states(organization: Organization) -> list[LimitState]:
    """Só as medidas que têm limite no plano; sem limite, a lista fica vazia."""

    limits = plan_limits(organization)
    return [
        LimitState(key=key, limit=limits[key], used=usage(organization, key))
        for key in LIMIT_KEYS
        if key in limits
    ]


def room(organization: Organization, key: str) -> int | None:
    """Quantos registros ainda cabem; `None` = sem limite."""

    return state(organization, key).remaining


def notices(organization: Organization) -> list[str]:
    return [item.message for item in states(organization) if item.message]
