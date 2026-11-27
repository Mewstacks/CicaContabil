"""Tarefas da Folha: agenda diária (06:00, só rascunho) e gravação da planilha."""

from __future__ import annotations

from celery import shared_task
from django.conf import settings

from apps.hub.models import ProductModule
from apps.organizations.models import Organization


def _offices() -> list[Organization]:
    ids = ProductModule.objects.filter(code=ProductModule.Code.FOLHA, enabled=True).values_list(
        "organization_id", flat=True
    )
    return list(Organization.objects.filter(pk__in=ids, is_active=True))


@shared_task(name="folha.schedule_daily")  # type: ignore[untyped-decorator]
def schedule_daily() -> int:
    """Cria o RASCUNHO da competência devida. Não toca no Domínio nem confirma o cálculo."""

    from .services import run_schedule

    return sum(1 for office in _offices() if run_schedule(office) is not None)


@shared_task(name="folha.flush_sheet_marks")  # type: ignore[untyped-decorator]
def flush_sheet_marks() -> int:
    """Grava as marcações pendentes. Sem credencial configurada, adia sem erro."""

    path = getattr(settings, "PLANILHA_FOLHA_CREDENTIALS_FILE", "")
    if not path:
        return 0
    from .services import flush_marks
    from .sheets import GoogleSheetsClient, SheetError

    try:
        client = GoogleSheetsClient(path)
    except (OSError, ValueError, KeyError, SheetError):
        return 0
    return sum(flush_marks(office, client)["done"] for office in _offices())
