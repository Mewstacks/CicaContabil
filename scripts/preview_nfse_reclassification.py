"""Read-only preview of the NFS-e reclassification with per-note sanity checks.

    cat scripts/preview_nfse_reclassification.py | \
        flyctl ssh console -a cica-contabil -C "python manage.py shell"

Flags accumulators whose Domínio name contradicts the note side (e.g. "PRESTAÇÃO DE SERVIÇO"
on a serviço tomado). Prints codes, names and note numbers only.
"""

import re
from collections import Counter

from apps.hub.models import (
    AccumulatorCatalogEntry,
    AccumulatorObservation,
    AccumulatorRule,
    ClientCompany,
    NfseDocument,
)
from apps.hub.nfse_reclassification import _effective_artifact, _is_human_decision
from apps.hub.nfse_sync import nfse_match_data
from apps.hub.services import active_catalog_codes, classify_nfse_from_candidates
from apps.organizations.models import Organization

SLUG = "bianchi-rizzotto"
PROVIDED_WORDS = re.compile(r"PRESTA|VENDA|RECEITA|FATURAMENTO|EMITID", re.I)
TAKEN_WORDS = re.compile(
    r"PAGOS|TOMAD|AQUISI|COMPRA|PLANO DE SA|ALUGUE|ENERGIA|TELEF|INTERNET|VALE TRANS|"
    r"MANUTEN|FRETE|CONSUMO|DESPESA|SEGURO|ASSIST|TERCEIROS|IMOBILIZ",
    re.I,
)

org = Organization.objects.get(slug=SLUG)
names = {}
for cid, code, name in (
    AccumulatorCatalogEntry.objects.filter(organization=org)
    .order_by("company_id", "accumulator_code", "-source_snapshot_at")
    .values_list("company_id", "accumulator_code", "name")
):
    names.setdefault((cid, code), name)
companies = list(
    ClientCompany.objects.filter(organization=org, nfse_documents__isnull=False).distinct()
)
catalogs = active_catalog_codes(companies)

stats = Counter()
reasons = Counter()
suspicious = []
held = []
changes = []
by_direction = Counter()
current_company = None
rules, observations = [], []


def pages(size=150):
    base = NfseDocument.objects.filter(organization=org).order_by("company_id", "pk")
    ids = list(base.values_list("pk", flat=True))
    for start in range(0, len(ids), size):
        yield from (
            base.filter(pk__in=ids[start : start + size])
            .select_related("company", "review_case")
            .prefetch_related("integration_artifacts")
        )


for document in pages():
    if document.company_id != current_company:
        current_company = document.company_id
        rules = list(
            AccumulatorRule.objects.filter(
                organization=org, company_id=current_company, active=True
            ).order_by("priority", "pk")
        )
        observations = list(
            AccumulatorObservation.objects.filter(
                organization=org, company_id=current_company
            ).order_by("pk")
        )
    stats["notas"] += 1
    artifacts = sorted(document.integration_artifacts.all(), key=lambda item: item.created_at)
    effective = _effective_artifact(artifacts)
    review = getattr(document, "review_case", None)
    data = nfse_match_data(document)
    direction = data.get("direction") or "?"
    by_direction[direction] += 1
    if _is_human_decision(review, effective):
        stats["humanas_preservadas"] += 1
        continue
    result = classify_nfse_from_candidates(
        document,
        rules=rules,
        observations=observations,
        catalog_codes=catalogs.get(document.company_id),
        match_data=data,
        on_date=document.issued_at.date() if document.issued_at else None,
    )
    if result.needs_review or not result.accumulator_code:
        stats["revisao"] += 1
        evidence = result.evidence
        reason = (
            "sem_correspondencia"
            if evidence.get("source") == "none"
            else "ambiguo"
            if evidence.get("ambiguous")
            else "conflito"
            if evidence.get("conflict")
            else "sem_direcao"
            if evidence.get("unknown_note_direction")
            else "pontuacao_baixa"
        )
        reasons[(direction, reason)] += 1
        if effective is not None:
            stats["revisao_mas_ja_tem_artefato"] += 1
            held.append(
                f"emp={document.company.dominio_code} "
                f"nota={(document.normalized_data or {}).get('number', '')} dir={direction} "
                f"atual={effective.accumulator_code} "
                f"[{names.get((document.company_id, effective.accumulator_code), '?')}] "
                f"motivo={reason} sugestao={result.accumulator_code} "
                f"[{names.get((document.company_id, result.accumulator_code), '?')}] "
                f"origem={(effective.evidence or {}).get('source')}"
            )
        continue
    stats["classificadas"] += 1
    name = names.get((document.company_id, result.accumulator_code), "?")
    number = str((document.normalized_data or {}).get("number", ""))
    line = (
        f"emp={document.company.dominio_code} nota={number} dir={direction} "
        f"acum={result.accumulator_code} [{name}] conf={result.confidence} "
        f"unanime={result.evidence.get('unanimous_counterparty')}"
    )
    if effective is None:
        stats["novas"] += 1
    elif effective.accumulator_code != result.accumulator_code:
        stats["trocam_acumulador"] += 1
        previous_name = names.get((document.company_id, effective.accumulator_code), "?")
        changes.append(f"{line} antes={effective.accumulator_code} [{previous_name}]")
    else:
        stats["iguais"] += 1
    if (direction == "taken" and PROVIDED_WORDS.search(name) and not TAKEN_WORDS.search(name)) or (
        direction == "provided" and TAKEN_WORDS.search(name) and not PROVIDED_WORDS.search(name)
    ):
        suspicious.append(line)

print("direção derivada", dict(by_direction))
print("resultado", dict(stats))
print("motivos de revisão", sorted(reasons.items(), key=lambda kv: -kv[1]))
print(f"\nSUSPEITAS nome x direção ({len(suspicious)})")
for line in suspicious[:80]:
    print(line)
print(f"\nTROCAM ACUMULADOR ({len(changes)})")
for line in changes[:80]:
    print(line)

print()
print(f"JA CLASSIFICADAS QUE A LOGICA NOVA MANDA PARA REVISAO ({len(held)})")
for line in held:
    print(line)
