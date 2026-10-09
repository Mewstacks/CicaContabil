"""Render the NFS-e notes screen inside production and report time, queries and content.

Pipe into a Django shell on a Fly machine:
    cat scripts/validate_nfse_center.py | flyctl ssh console -a cica-contabil -C "python manage.py shell"
Read-only: it renders GET pages for an existing owner of the office; nothing is written except
the Django session row created by force_login.
"""

import re
import time

from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from apps.organizations.models import Membership, Organization

SLUG = "bianchi-rizzotto"
office = Organization.objects.get(slug=SLUG)
membership = (
    Membership.objects.filter(organization=office, role=Membership.Role.OWNER)
    .select_related("user")
    .first()
)
client = Client(HTTP_HOST="cica-contabil.fly.dev", secure=True)
client.force_login(membership.user)
session = client.session
session["hub_organization_id"] = str(office.id)
session.save()


def visit(params, label):
    with CaptureQueriesContext(connection) as queries:
        started = time.perf_counter()
        response = client.get("/app/nfse/", params)
        elapsed = time.perf_counter() - started
    body = response.content.decode()
    print(
        f"{label}: status={response.status_code} {elapsed * 1000:.0f} ms "
        f"queries={len(queries)} bytes={len(body)}"
    )
    return response, body


response, body = visit({}, "bare (previous month)")
groups = response.context["nfse_groups"]
totals = response.context["nfse_totals"]
print("competence:", response.context["nfse_filters"].competence)
print("groups:", len(groups), "notes:", totals["notes"], "pending:", totals["pending"])
print(
    "service", totals["service"], "net", totals["net"], "iss", totals["iss"], "crf",
    totals["crf"], "irrf", totals["irrf"], "inss", totals["inss"], "retained",
    totals["retained"], "closed", totals["closed"],
)
for group in groups[:5]:
    print(" -", group["name"][:40], group["notes"], group["pending"], group["service"],
          group["retained"])

visit({"competence": "", "status": "all"}, "all periods")
visit({"status": "unclassified", "competence": ""}, "para classificar, all periods")
visit({"direction": "taken"}, "entradas")
visit({"q": "ltda"}, "search ltda")
visit({"period": "issued", "issued_from": "01/09/2026", "issued_to": "30/09/2026"}, "emissao set")

busiest = max(groups, key=lambda group: group["notes"]) if groups else None
if busiest:
    response, body = visit(
        {"competence": response.context["nfse_filters"].competence or "",
         "group": str(busiest["company_id"])},
        f"group {busiest['name'][:30]} ({busiest['notes']})",
    )
    rows = response.context["group"]["rows"]
    print("rows:", len(rows), "has_more:", response.context["group"]["has_more"])
    for row in rows[:5]:
        print(
            "   ", row["issued"], row["situation_label"], row["number"],
            row["counterparty_name"][:30], row["counterparty_document"], "iss", row["iss"],
            "crf", row["crf"], "irrf", row["irrf"], "inss", row["inss"], "serv",
            row["service_amount"], "liq", row["net"], "acc", row["accumulator"],
        )
    print("event rows listed:", sum(1 for row in rows if not row["number"]))
print("template errors:", bool(re.search(r"TemplateSyntaxError|Traceback", body)))
