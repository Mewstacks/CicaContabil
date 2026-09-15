"""Product availability guards controlled by the Mewstack console.

An unfinished capability must be absent from office-facing surfaces and refuse
direct access.  This is deliberately separate from an office's commercial
entitlement: granting a module cannot publish a capability that Mewstack has
not released.
"""

from apps.platform.models import PlatformConfiguration


def copilot_is_available() -> bool:
    """Whether the Copilot has been released to accounting offices."""

    return PlatformConfiguration.objects.filter(
        key="default", copilot_available_for_offices=True
    ).exists()
