"""A stand-in office role for the platform admin inside a support session.

The platform owner has no ``Membership`` in any office and must not get one: a row would
outlive the session, show up in the team list and survive an offboarding. Screens that
decide by role, however, only know ``Membership``. During a support session opened by a
platform admin we therefore hand them an *unsaved* owner membership bound to that
session. It is never written; every write path that re-reads the live membership honours
it through ``support_session_may_operate`` instead, so the session's office, expiry,
mutation mode and company scope stay the single source of truth.
"""

from __future__ import annotations

from apps.accounts.models import User
from apps.organizations.models import Membership
from apps.platform.models import SupportSession
from apps.platform.services import is_platform_admin

_SESSION_ATTR = "_platform_support_session"


def build_support_membership(session: SupportSession) -> Membership | None:
    """Unsaved OWNER membership for a platform admin's session, otherwise ``None``."""

    if not is_platform_admin(session.support_user):
        return None
    membership = Membership(
        organization=session.organization,
        user=session.support_user,
        role=Membership.Role.OWNER,
        is_active=True,
        can_acknowledge_dte=False,
    )
    # Not a database row: lets related filters accept it and keeps ``save`` unreachable.
    membership._state.adding = False
    setattr(membership, _SESSION_ATTR, session)
    return membership


def support_session_of(membership: Membership | None) -> SupportSession | None:
    session = getattr(membership, _SESSION_ATTR, None)
    return session if isinstance(session, SupportSession) else None


def support_session_may_operate(
    *,
    membership: Membership | None,
    organization_id: object,
    company_id: object,
    actor: User | None,
) -> bool:
    """Re-check a virtual membership against the live session before a write."""

    session = support_session_of(membership)
    if session is None or membership is None:
        return False
    live = SupportSession.objects.filter(pk=session.pk).first()
    if live is None or not live.usable() or not live.can_mutate:
        return False
    if actor is not None and live.support_user_id != actor.pk:
        return False
    if live.organization_id != organization_id:
        return False
    if live.company_ids and str(company_id) not in {str(item) for item in live.company_ids}:
        return False
    return is_platform_admin(live.support_user)
