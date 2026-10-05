"""Read-only audit of every NFS-e classification of one office.

Run inside the production shell (nothing is written):

    cat scripts/audit_nfse_classification.py | \
        flyctl ssh console -a cica-contabil -C "python manage.py shell"

Prints aggregates plus one line per classified note. Only Domínio codes, note numbers,
dates, service codes and accumulator codes/names are printed; no CNPJ, value or XML body.
"""

import re
from collections import Counter, defaultdict

from apps.hub.models import (
    AccumulatorCatalogEntry,
    AccumulatorObservation,
    AccumulatorRule,
    IntegrationArtifact,
    NfseDocument,
    ReviewCase,
)
from apps.organizations.models import Organization

SLUG = "bianchi-rizzotto"
LC116 = re.compile(r"^(\d{1,2})\.(\d{1,2})(?:\.\d+)?$")


def norm(value):
    text = str(value or "").strip()
    item = LC116.fullmatch(text)
    if item:
        return f"{int(item.group(1)):02d}{int(item.group(2)):02d}"
    if len(text) == 6 and text.isdigit():
        return text[:4]
    return text


def shape(value):
    return re.sub(r"[A-Za-z]", "a", re.sub(r"\d", "9", str(value or ""))) or "(vazio)"


org = Organization.objects.get(slug=SLUG)
print("=== TOTAIS")
docs_total = NfseDocument.objects.filter(organization=org).count()
print("notas", docs_total)
print(
    "revisões",
    dict(
        Counter(
            ReviewCase.objects.filter(organization=org).values_list("status", "resolution_source")
        )
    ),
)
print(
    "regras manuais",
    AccumulatorRule.objects.filter(organization=org).count(),
    "com match",
    AccumulatorRule.objects.filter(organization=org).exclude(match={}).count(),
)
print("observações", AccumulatorObservation.objects.filter(organization=org).count())

# Latest active catalog per company + names.
latest, active, names = {}, defaultdict(set), {}
for cid, snap, code, is_active, name in (
    AccumulatorCatalogEntry.objects.filter(organization=org)
    .order_by("company_id", "-source_snapshot_at")
    .values_list("company_id", "source_snapshot_at", "accumulator_code", "active", "name")
    .iterator(chunk_size=2000)
):
    if latest.setdefault(cid, snap) != snap:
        continue
    names[(cid, code)] = name
    if is_active:
        active[cid].add(code)
print("empresas com catálogo", len(latest))

obs_sc = defaultdict(lambda: defaultdict(set))  # company -> normalized service -> codes
obs_cp = defaultdict(lambda: defaultdict(set))
obs_shapes = Counter()
for cid, code, sc, cp in (
    AccumulatorObservation.objects.filter(organization=org)
    .values_list("company_id", "accumulator_code", "service_code", "counterparty_ref")
    .iterator(chunk_size=5000)
):
    if sc:
        obs_shapes[shape(sc)] += 1
        obs_sc[cid][norm(sc)].add(code)
    if cp:
        obs_cp[cid][cp].add(code)
raw_obs_sc = defaultdict(set)
for cid, sc in (
    AccumulatorObservation.objects.filter(organization=org)
    .exclude(service_code="")
    .values_list("company_id", "service_code")
    .iterator(chunk_size=5000)
):
    raw_obs_sc[cid].add(sc)
print("formato service_code nas observações", obs_shapes.most_common(10))
print("amostra", sorted({sc for s in list(raw_obs_sc.values())[:20] for sc in list(s)[:3]})[:30])

# Effective artifact per document (same rule as export: not superseded, newest).
artifacts = defaultdict(list)
for doc_id, art_id, code, created, evidence, payload in (
    IntegrationArtifact.objects.filter(organization=org)
    .values_list("document_id", "id", "accumulator_code", "created_at", "evidence", "payload")
    .iterator(chunk_size=2000)
):
    artifacts[doc_id].append((created, str(art_id), code, evidence or {}, payload or {}))
effective = {}
for doc_id, rows in artifacts.items():
    rows.sort()
    superseded = {
        str(c.get("previous_artifact_id"))
        for _, _, _, ev, pl in rows
        for c in (ev, pl)
        if isinstance(c, dict) and c.get("previous_artifact_id")
    }
    alive = [r for r in rows if r[1] not in superseded] or rows
    effective[doc_id] = alive[-1]
open_reviews = set(
    ReviewCase.objects.filter(organization=org, status="open").values_list("document_id", flat=True)
)

print("\n=== NOTAS")
direction = Counter()
doc_shapes = Counter()
match = Counter()
classified_lines = []
outside = []
for doc_id, cid, dcode, nsu, issued, data in (
    NfseDocument.objects.filter(organization=org)
    .values_list(
        "id", "company_id", "company__dominio_code", "source_nsu", "issued_at", "normalized_data"
    )
    .iterator(chunk_size=1000)
):
    data = data or {}
    d = str(data.get("direction") or "?")
    direction[d] += 1
    sc, cp = str(data.get("service_code") or ""), str(data.get("counterparty_ref") or "")
    doc_shapes[shape(sc)] += 1
    raw_hit = bool(sc) and sc in raw_obs_sc[cid]
    norm_hit = bool(sc) and norm(sc) in obs_sc[cid]
    cp_hit = bool(cp) and cp in obs_cp[cid]
    candidates = set()
    if norm_hit:
        candidates |= obs_sc[cid][norm(sc)]
    if cp_hit:
        candidates |= obs_cp[cid][cp]
    if cid in active:
        candidates &= active[cid]
    both = (
        (obs_sc[cid].get(norm(sc), set()) & obs_cp[cid].get(cp, set()))
        if (norm_hit and cp_hit)
        else set()
    )
    if cid in active:
        both &= active[cid]
    match[
        (
            d,
            "srv_bruto" if raw_hit else "-",
            "srv_norm" if norm_hit else "-",
            "forn" if cp_hit else "-",
            f"cand={min(len(candidates), 3)}",
            f"ambos={min(len(both), 2)}",
        )
    ] += 1
    eff = effective.get(doc_id)
    if eff:
        _, _, code, evidence, _ = eff
        in_cat = (
            "sem-catalogo"
            if cid not in latest
            else ("ok" if code in active[cid] else "FORA-DO-CATALOGO")
        )
        line = (
            (
                f"emp={dcode} nota={data.get('number', '')} nsu={nsu} "
                f"data={issued:%Y-%m-%d} dir={d} "
                f"srv={sc} acum={code} [{names.get((cid, code), '?')}] cat={in_cat} "
                f"origem={evidence.get('source', '?')} conf_score={evidence.get('score', '')} "
                f"revisao_aberta={'sim' if doc_id in open_reviews else 'nao'} "
                f"candidatos={sorted(candidates)[:6]}"
            )
            if issued
            else f"emp={dcode} nota={data.get('number', '')} acum={code} cat={in_cat}"
        )
        classified_lines.append(line)
        if in_cat == "FORA-DO-CATALOGO":
            outside.append(line)

print("direção", dict(direction))
print("formato service_code nas notas", doc_shapes.most_common(10))
print(
    "\ncasamento (dir, serviço bruto, serviço normalizado, fornecedor, nº candidatos, "
    "serviço+fornecedor):"
)
for key, value in sorted(match.items(), key=lambda kv: -kv[1])[:40]:
    print(" ", value, key)

print(f"\n=== CLASSIFICADAS ({len(classified_lines)})")
for line in classified_lines:
    print(line)
print(f"\n=== ACUMULADOR FORA DO CATÁLOGO ATIVO ({len(outside)})")
for line in outside:
    print(line)

print("\n=== NOTA 453")
for doc in NfseDocument.objects.filter(
    organization=org, normalized_data__number="453"
).select_related("company"):
    data = doc.normalized_data or {}
    print(
        "emp",
        doc.company.dominio_code,
        "dir",
        data.get("direction"),
        "srv",
        data.get("service_code"),
        "contraparte",
        data.get("counterparty_name"),
    )
    for _, _art_id, code, evidence, _ in sorted(artifacts.get(doc.id, [])):
        print(
            "  artefato",
            code,
            names.get((doc.company_id, code), "?"),
            evidence.get("source"),
            "no catálogo ativo"
            if code in active.get(doc.company_id, set())
            else "FORA do catálogo ativo",
        )
    xml = doc.original_xml
    for tag in ("cMun", "cLocEmi", "cLocPrestacao", "cLocIncid", "UF", "cPais", "CEP"):
        print("  ", tag, re.findall(rf"<(?:\w+:)?{tag}>([^<]*)<", xml)[:6])
