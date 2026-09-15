"""Withdraw unrelated official headlines from the tax-reform radar without deleting them."""

from __future__ import annotations

import re

from django.db import migrations

_REFORM_TERMS = (
    "reforma tribut",
    "ibs",
    "cbs",
    "imposto sobre bens",
    "tributação do consumo",
    "tributacao do consumo",
)
_FISCAL_TERMS = (
    "tribut",
    "imposto",
    "benefícios fiscais",
    "beneficios fiscais",
    "crédito fiscal",
    "credito fiscal",
    "simples nacional",
)
_ACRONYMS = re.compile(r"\b(?:pis|cofins|irrf|itr|dctf|sped)\b", re.IGNORECASE)


def reclassify_alerts(apps, schema_editor) -> None:
    alert_model = apps.get_model("hub", "ReformAlert")
    database = schema_editor.connection.alias
    for alert in (
        alert_model.objects.using(database)
        .only("id", "title", "relevance")
        .iterator(chunk_size=500)
    ):
        title = alert.title.casefold()
        if any(term in title for term in _REFORM_TERMS):
            relevance = "reform"
        elif any(term in title for term in _FISCAL_TERMS) or _ACRONYMS.search(title):
            relevance = "fiscal"
        else:
            relevance = "general"
        if relevance != alert.relevance:
            alert_model.objects.using(database).filter(pk=alert.pk).update(relevance=relevance)


class Migration(migrations.Migration):
    dependencies = [("hub", "0021_alter_productmodule_code_triage")]

    operations = [migrations.RunPython(reclassify_alerts, migrations.RunPython.noop)]
