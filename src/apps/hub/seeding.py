"""Persona builders shared by the ``seed_personas`` command and the flow tests.

``seed_demo`` builds a single office with a single owner, which is enough to look at a
screen but not to prove that a screen refuses the wrong person. Every persona below
exists because some branch of the product only runs for it: a partial
``CompanyAccessGrant`` narrows the company switcher, an auditor must be refused on every
POST, a support session must be read-only, a second tenant turns isolation from an
assertion into an observation.

Everything is idempotent: running it twice changes nothing.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    Connector,
    OfficeProfile,
    ProductModule,
)
from apps.organizations.models import Membership, Organization
from apps.platform.models import (
    Invitation,
    Plan,
    PlatformAccess,
    TenantContract,
    TenantLifecycle,
)

# A known password is the point: these accounts only exist behind the DEBUG guard in
# seed_personas, and a generated one would have to be copied out of the terminal before
# every flow run.
DEFAULT_PASSWORD = "persona-local-password-123"  # noqa: S105

# The demo office seeded by ``seed_demo``; the personas below join it so they inherit its
# companies, documents and DTE evidence instead of duplicating them.
DEMO_SLUG = "escritorio-demo"
MFA_OFFICE_SLUG = "escritorio-mfa"
RIVAL_SLUG = "escritorio-rival"

OFFICE_PERSONAS: tuple[tuple[str, str, str], ...] = (
    ("admin@hubcontador.local", Membership.Role.ADMIN, "Administradora do escritório"),
    ("operador@hubcontador.local", Membership.Role.OPERATOR, "Operador de escopo parcial"),
    ("auditor@hubcontador.local", Membership.Role.AUDITOR, "Auditor somente leitura"),
    ("financeiro@hubcontador.local", Membership.Role.BILLING, "Financeiro"),
)

PLATFORM_PERSONAS: tuple[tuple[str, str, str], ...] = (
    ("dev@hubcontador.local", PlatformAccess.Role.DEVELOPER, "Desenvolvedora da plataforma"),
    ("suporte@hubcontador.local", PlatformAccess.Role.SUPPORT, "Analista de suporte"),
    ("comercial@hubcontador.local", PlatformAccess.Role.COMMERCIAL, "Executivo comercial"),
)

RIVAL_COMPANIES: tuple[tuple[str, str, str], ...] = (
    ("Marcenaria Três Rios ME", "90.123.456/0001-78", "0201"),
    ("Laboratório Boa Vista", "01.234.567/0001-89", "0202"),
)

# The operator sees a slice of the office, not all of it: enough companies to work, few
# enough that a switcher showing all of them is visibly a bug.
OPERATOR_COMPANY_COUNT = 3


@dataclass
class SeededWorld:
    """Everything ``build_personas`` created, so callers can assert against it."""

    demo_office: Organization
    mfa_office: Organization
    rival_office: Organization
    office_users: dict[str, User] = field(default_factory=dict)
    platform_users: dict[str, User] = field(default_factory=dict)
    plan: Plan | None = None
    contract: TenantContract | None = None
    invitation: Invitation | None = None
    invitation_token: str = ""
    password: str = DEFAULT_PASSWORD


def ensure_user(email: str, *, full_name: str, password: str) -> User:
    user = User.objects.filter(email=email.casefold()).first()
    if user is not None:
        return user
    user = User.objects.create_user(email=email, password=password)
    user.full_name = full_name
    user.save(update_fields=["full_name"])
    return user


def ensure_office(
    *, slug: str, name: str, require_mfa: bool = False, enable_modules: bool = True
) -> Organization:
    organization, _ = Organization.objects.get_or_create(slug=slug, defaults={"name": name})
    OfficeProfile.objects.get_or_create(
        organization=organization,
        defaults={
            "legal_name": f"{name} Serviços Contábeis Ltda",
            "contract_status": OfficeProfile.ContractStatus.ACTIVE,
            "require_mfa": require_mfa,
        },
    )
    if enable_modules:
        for code in ProductModule.Code.values:
            ProductModule.objects.get_or_create(
                organization=organization,
                code=code,
                defaults={"enabled": True, "enabled_at": timezone.now()},
            )
    return organization


def ensure_membership(
    organization: Organization, user: User, role: str, *, companies: list[ClientCompany]
) -> Membership:
    membership, _ = Membership.objects.get_or_create(
        organization=organization, user=user, defaults={"role": role}
    )
    for company in companies:
        CompanyAccessGrant.objects.get_or_create(
            organization=organization,
            membership=membership,
            company=company,
            defaults={
                "modules": list(ProductModule.Code.values),
                "capabilities": ["read", "write", "dispatch"],
            },
        )
    return membership


def ensure_platform_access(user: User, role: str, *, mfa_required: bool = False) -> PlatformAccess:
    access, _ = PlatformAccess.objects.get_or_create(
        user=user, defaults={"role": role, "mfa_required": mfa_required}
    )
    return access


def ensure_plan() -> Plan:
    plan, _ = Plan.objects.get_or_create(
        code="essencial",
        defaults={
            "name": "Essencial",
            "modules": list(ProductModule.Code.values),
            "limits": {"companies": 25, "users": 10, "documents": 2000},
        },
    )
    return plan


def ensure_contract(organization: Organization, plan: Plan) -> TenantContract:
    today = timezone.localdate()
    contract, _ = TenantContract.objects.get_or_create(
        organization=organization,
        reference="CTR-2026-0001",
        defaults={
            "plan": plan,
            "status": TenantContract.Status.ACTIVE,
            "starts_on": today.replace(day=1),
            "ends_on": today.replace(day=1) + dt.timedelta(days=365),
        },
    )
    return contract


def ensure_lifecycle(
    organization: Organization, state: str, *, reason: str = ""
) -> TenantLifecycle:
    lifecycle, _ = TenantLifecycle.objects.get_or_create(
        organization=organization, defaults={"state": state, "reason": reason}
    )
    return lifecycle


def ensure_invitation(
    organization: Organization, *, email: str, created_by: User | None = None
) -> tuple[Invitation, str]:
    """Return the invitation and its raw token.

    Only the digest is stored, so a token that is not returned here is unrecoverable and
    the activation screen becomes unreachable.
    """

    existing = Invitation.objects.filter(
        organization=organization, email=email, status=Invitation.Status.PENDING
    ).first()
    if existing is not None:
        # The stored digest cannot be reversed: replace the invitation so the caller holds
        # a token that actually opens the activation screen.
        existing.status = Invitation.Status.REVOKED
        existing.save(update_fields=["status", "updated_at"])
    raw_token, digest = Invitation.issue_token()
    invitation = Invitation.objects.create(
        organization=organization,
        email=email,
        full_name="Pessoa convidada",
        role=Membership.Role.OWNER,
        token_digest=digest,
        expires_at=timezone.now() + dt.timedelta(days=7),
        created_by=created_by,
    )
    return invitation, raw_token


def _rival_companies(organization: Organization) -> list[ClientCompany]:
    companies: list[ClientCompany] = []
    for name, cnpj, code in RIVAL_COMPANIES:
        company, _ = ClientCompany.objects.get_or_create(
            organization=organization,
            dominio_code=code,
            defaults={"name": name, "cnpj_masked": cnpj, "active": True},
        )
        companies.append(company)
    return companies


def build_personas(*, password: str = DEFAULT_PASSWORD) -> SeededWorld:
    """Build every persona on top of whatever ``seed_demo`` already created."""

    demo_office = ensure_office(slug=DEMO_SLUG, name="Escritório Demonstração")
    demo_companies = list(
        ClientCompany.objects.filter(organization=demo_office, active=True).order_by("dominio_code")
    )

    office_users: dict[str, User] = {}
    for email, role, full_name in OFFICE_PERSONAS:
        user = ensure_user(email, full_name=full_name, password=password)
        scope = (
            demo_companies[:OPERATOR_COMPANY_COUNT]
            if role == Membership.Role.OPERATOR
            else demo_companies
        )
        ensure_membership(demo_office, user, role, companies=scope)
        office_users[role] = user

    platform_users: dict[str, User] = {}
    for email, role, full_name in PLATFORM_PERSONAS:
        user = ensure_user(email, full_name=full_name, password=password)
        ensure_platform_access(user, role)
        platform_users[role] = user

    # A third office with the MFA requirement on: seed_demo leaves require_mfa False, so
    # without this the office-side second factor is never exercised.
    mfa_office = ensure_office(
        slug=MFA_OFFICE_SLUG, name="Escritório Segundo Fator", require_mfa=True
    )
    mfa_user = ensure_user(
        "mfa@hubcontador.local", full_name="Usuária com MFA obrigatório", password=password
    )
    ensure_membership(mfa_office, mfa_user, Membership.Role.OWNER, companies=[])
    office_users["mfa"] = mfa_user

    # A second tenant so isolation can be observed rather than asserted in the abstract.
    rival_office = ensure_office(slug=RIVAL_SLUG, name="Escritório Rival")
    rival_owner = ensure_user(
        "rival@hubcontador.local", full_name="Proprietário do outro escritório", password=password
    )
    ensure_membership(
        rival_office,
        rival_owner,
        Membership.Role.OWNER,
        companies=_rival_companies(rival_office),
    )
    Connector.objects.get_or_create(
        organization=rival_office,
        kind=Connector.Kind.DOMINIO_AGENT,
        defaults={"enabled": True, "status": "healthy"},
    )
    office_users["rival"] = rival_owner

    plan = ensure_plan()
    contract = ensure_contract(demo_office, plan)
    ensure_lifecycle(demo_office, TenantLifecycle.State.ACTIVE)
    ensure_lifecycle(mfa_office, TenantLifecycle.State.ACTIVE)
    ensure_lifecycle(
        rival_office,
        TenantLifecycle.State.SUSPENDED,
        reason="Inadimplência de demonstração",
    )

    invitation, raw_token = ensure_invitation(
        demo_office,
        email="convidado@hubcontador.local",
        created_by=platform_users.get(PlatformAccess.Role.SUPPORT),
    )

    return SeededWorld(
        demo_office=demo_office,
        mfa_office=mfa_office,
        rival_office=rival_office,
        office_users=office_users,
        platform_users=platform_users,
        plan=plan,
        contract=contract,
        invitation=invitation,
        invitation_token=raw_token,
        password=password,
    )
