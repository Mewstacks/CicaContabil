"""Read-only validation after a reclassification (no export file is written).

    cat scripts/validate_nfse_classification.py | \
        flyctl ssh console -a cica-contabil -C "python manage.py shell"
"""

import random
import re
from collections import Counter

from defusedxml import ElementTree

from apps.hub.models import AccumulatorCatalogEntry, IntegrationArtifact, NfseDocument, ReviewCase
from apps.hub.nfse_reclassification import _effective_artifact
from apps.hub.nfse_sync import nfse_match_data
from apps.hub.services import _xml_with_dominio_accumulator, active_catalog_codes
from apps.organizations.models import Organization

org = Organization.objects.get(slug="bianchi-rizzotto")
PROVIDED_WORDS = re.compile(r"PRESTA|VENDA|RECEITA|FATURAMENTO", re.I)
TAKEN_WORDS = re.compile(
    r"PAGOS|TOMAD|AQUISI|COMPRA|PLANO DE SA|ALUGUE|ENERGIA|FRETE|DESPESA|TERCEIROS", re.I
)

classified_ids = list(
    IntegrationArtifact.objects.filter(organization=org)
    .values_list("document_id", flat=True)
    .distinct()
)
print(
    "notas com acumulador",
    len(classified_ids),
    "de",
    NfseDocument.objects.filter(organization=org).count(),
)
print(
    "revisões",
    dict(
        Counter(
            ReviewCase.objects.filter(organization=org).values_list("status", "resolution_source")
        )
    ),
)

names = {}
for cid, code, name in AccumulatorCatalogEntry.objects.filter(organization=org).values_list(
    "company_id", "accumulator_code", "name"
):
    names.setdefault((cid, code), name)

random.seed(20261005)
sample = random.sample(classified_ids, min(400, len(classified_ids)))
catalogs = None
problems = Counter()
checked = 0
for start in range(0, len(sample), 100):
    documents = list(
        NfseDocument.objects.filter(pk__in=sample[start : start + 100])
        .select_related("company")
        .prefetch_related("integration_artifacts")
    )
    catalogs = active_catalog_codes(list({d.company for d in documents}))
    for document in documents:
        artifact = _effective_artifact(
            sorted(document.integration_artifacts.all(), key=lambda a: a.created_at)
        )
        code = artifact.accumulator_code
        checked += 1
        if document.company_id in catalogs and code not in catalogs[document.company_id]:
            problems["fora_do_catalogo"] += 1
        direction = nfse_match_data(document).get("direction")
        name = names.get((document.company_id, code), "")
        if (
            direction == "taken" and PROVIDED_WORDS.search(name) and not TAKEN_WORDS.search(name)
        ) or (
            direction == "provided" and TAKEN_WORDS.search(name) and not PROVIDED_WORDS.search(name)
        ):
            problems["nome_contra_direcao"] += 1
            print(
                "  suspeita",
                document.company.dominio_code,
                (document.normalized_data or {}).get("number"),
                direction,
                code,
                name,
            )
        try:
            rendered = _xml_with_dominio_accumulator(document.original_xml, code)
        except ValueError as exc:
            problems[f"xml_erro: {exc}"] += 1
            continue
        root = ElementTree.fromstring(rendered)
        info = [
            n
            for n in root.iter()
            if isinstance(n.tag, str) and n.tag.rsplit("}", 1)[-1] == "infNFSe"
        ]
        values = [c for c in info[0] if c.tag.rsplit("}", 1)[-1] == "valores"]
        acums = [c.text for c in values[0] if c.tag.rsplit("}", 1)[-1] == "acum"]
        if acums != [code]:
            problems["acum_errado"] += 1
        stripped = re.sub(r"<(\w+:)?acum>[^<]*</(\w+:)?acum>", "", rendered, count=1)
        original_without_acum = re.sub(
            r"<(\w+:)?acum>[^<]*</(\w+:)?acum>", "", document.original_xml, count=1
        )
        if stripped != original_without_acum:
            problems["xml_alterado_alem_do_acum"] += 1
print("amostra validada", checked, "problemas", dict(problems))

print("\nemp 57 (antes COMPRA DE MERCADORIA em nota de serviço prestado):")
for document in NfseDocument.objects.filter(
    organization=org,
    company__dominio_code="57",
    normalized_data__number__in=["864", "866", "870", "874"],
).prefetch_related("integration_artifacts"):
    artifact = _effective_artifact(
        sorted(document.integration_artifacts.all(), key=lambda a: a.created_at)
    )
    print(
        "  nota",
        document.normalized_data.get("number"),
        "->",
        artifact.accumulator_code,
        names.get((document.company_id, artifact.accumulator_code)),
    )
