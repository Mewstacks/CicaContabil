"""Avisos do radar Simples/MEI (E14): empresa chegando ao teto, para dono e administrador.

Aviso dentro do produto (D-277: nunca e-mail, nunca para o cliente). Um aviso por pessoa,
empresa, ano e nível (80, 90, 100): rodar de novo não repete e a escalada aparece sozinha.
"""

from __future__ import annotations

from datetime import date

from django.utils import timezone

from apps.hub import simples_radar
from apps.hub.models import ProductModule
from apps.hub.notifications import notify
from apps.hub.procuracao_alerts import _administrators
from apps.organizations.models import Organization

# Valor fora de `Notification.Kind`: o enum novo exige migração de `choices` (AlterField),
# que a guarda L1 barra sem OK do dono. O campo aceita qualquer valor de até 32 caracteres; o
# rótulo aparece cru na lista até o enum entrar.
KIND = "simples_ceiling"


def notify_simples_radar(*, today: date | None = None) -> int:
    """Cria os avisos novos e devolve quantos criou."""

    today = today or timezone.localdate()
    created = 0
    offices = Organization.objects.filter(
        is_active=True,
        is_demo=False,
        pk__in=ProductModule.objects.filter(code=ProductModule.Code.NFSE, enabled=True).values(
            "organization_id"
        ),
    )
    for office in offices:
        administrators = _administrators(office)
        if not administrators:
            continue
        for row in simples_radar.portfolio(office, today):
            if row.alert is None:
                continue
            for person in administrators:
                notice = notify(
                    organization=office,
                    recipient=person,
                    kind=KIND,
                    title=f"{row.company_name} a {row.alert}% do teto",
                    dedupe_key=f"simples-ceiling:{row.company_id}:{today.year}:{row.alert}",
                )
                created += int(notice is not None)
    return created
