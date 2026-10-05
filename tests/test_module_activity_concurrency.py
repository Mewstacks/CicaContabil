from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections, connection, connections

from apps.hub.models import (
    ClientCompany,
    DctfWebDocument,
    FiscalGuide,
    OperationalActivity,
    ParcelamentoOperation,
)
from apps.hub.module_activities import (
    sync_dctfweb_document_activity,
    sync_fiscal_guide_activity,
    sync_parcelamento_operation_activity,
)
from apps.organizations.models import Organization


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", ["guide", "dctfweb", "parcelamento"])
def test_concurrent_fiscal_projections_create_one_activity_with_no_requester(kind):
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks and independent transactions.")
    office = Organization.objects.create(name="Projection concurrency", slug="projection-locks")
    company = ClientCompany.objects.create(organization=office, name="Synthetic")
    if kind == "guide":
        source = FiscalGuide.objects.create(
            organization=office,
            company=company,
            kind=FiscalGuide.Kind.DAS,
            reference="concurrent-guide",
            competence="09/2026",
            due_on=date(2026, 10, 20),
            integra_service_key="pgdasd.das",
            status=FiscalGuide.Status.READY,
        )
        project = sync_fiscal_guide_activity
    elif kind == "dctfweb":
        source = DctfWebDocument.objects.create(
            organization=office,
            company=company,
            kind=DctfWebDocument.Kind.RECEIPT,
            competence="09/2026",
            service_key="dctfweb.recibo",
            status=DctfWebDocument.Status.QUEUED,
        )
        project = sync_dctfweb_document_activity
    else:
        source = ParcelamentoOperation.objects.create(
            organization=office,
            company=company,
            kind=ParcelamentoOperation.Kind.ORDERS,
            service_key="parcsn.pedidos",
            status=ParcelamentoOperation.Status.QUEUED,
        )
        project = sync_parcelamento_operation_activity
    barrier = Barrier(4)

    def worker(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            activity = project(source.pk)
            assert activity is not None
            return activity.pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(worker, range(4)))
    assert len(set(ids)) == 1
    assert OperationalActivity.objects.filter(organization=office).count() == 1
    activity = OperationalActivity.objects.get(pk=ids[0])
    events_before = activity.events.count()
    project(source.pk)
    assert activity.events.count() == events_before
    assert activity.assigned_to_id is None
