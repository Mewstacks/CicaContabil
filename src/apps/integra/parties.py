from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError

from apps.common.cnpj import normalize_cnpj
from apps.hub.models import OfficeProfile
from apps.integra.errors import IntegraConfigurationError


def author_cnpj_for(organization: Any) -> str:
    """Return the office/procurator CNPJ used as autorPedidoDados."""

    profile = OfficeProfile.objects.filter(organization=organization).only("cnpj").first()
    if profile is None or not profile.cnpj:
        raise IntegraConfigurationError(
            "O CNPJ do escritório precisa estar confirmado antes de consultar o Serpro."
        )
    try:
        return normalize_cnpj(profile.cnpj)
    except ValidationError as exc:
        raise IntegraConfigurationError(
            "O CNPJ do escritório é inválido para autorizar pedidos no Serpro."
        ) from exc
