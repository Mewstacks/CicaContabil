"""D-381: suggest the branch of each bank account in the six CONTAD head offices.

Reads the transfer text produced by ``agent-windows/inspect-contad-branch-accounts.ps1``
and the retained Domínio chart catalogue (``chart-accounts.jsonl``). Bank accounts are
the analytic accounts under each plan's "DEPÓSITOS BANCÁRIOS" group. Output is a
suggestion for the link screen: it never approves a bank association.

Usage: python3 -I scripts/analyze_contad_branch_accounts.py TRANSFER.txt CHART.jsonl OUT.json
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

COMPANIES = (25, 42, 129, 147, 280, 293)
BANK_GROUP = re.compile(r"^DEPOSITOS BANCARIOS$")


def _plain(text: str | None) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in folded if not unicodedata.combining(c)).upper().strip()


def load_profile(path: Path) -> dict:
    transfer = json.loads(path.read_text(encoding="utf-8-sig").strip())
    if transfer.get("version") != "contad-branch-accounts-transfer-v1":
        raise SystemExit("Arquivo não é a saída do leitor de filiais.")
    raw = gzip.decompress(base64.b64decode(transfer["data"], validate=True))
    if len(raw) != transfer["bytes"] or hashlib.sha256(raw).hexdigest() != transfer["sha256"]:
        raise SystemExit("Integridade da transferência recusada.")
    profile = json.loads(raw.decode("utf-8"))
    if not profile.get("completed") or not profile.get("two_reads_identical"):
        raise SystemExit("Leitura incompleta ou instável.")
    if tuple(profile["company_codes"]) != COMPANIES:
        raise SystemExit("Escopo de empresas diferente do D-381.")
    return profile


def bank_accounts(chart_path: Path, plans: set[int]) -> dict[tuple[int, int], dict]:
    rows = []
    with chart_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["chart_company_code"] in plans:
                rows.append(row)
    prefixes: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        if row["account_type_raw"] == "S" and BANK_GROUP.match(_plain(row["account_name_raw"])):
            prefixes[row["chart_company_code"]].append(row["classification_raw"])
    result = {}
    for row in rows:
        plan = row["chart_company_code"]
        classification = row["classification_raw"] or ""
        if row["account_type_raw"] != "A":
            continue
        if any(classification.startswith(p) and classification != p for p in prefixes[plan]):
            result[(plan, row["account_code"])] = row
    return result


def analyse(profile: dict, chart_path: Path) -> dict:
    snapshot = profile["snapshot"]
    usage: dict[tuple[int, int, int], dict] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    plans: set[int] = set()
    for side, key in (("debit", "debit_counts"), ("credit", "credit_counts")):
        for r in snapshot[key]:
            plans.add(r["chart_company_code"])
            month = f"{r['year']:04d}-{r['month']:02d}"
            usage[(r["company_code"], r["chart_company_code"], r["account_code"])][r["branch_code"]][
                f"{month}:{side}"
            ] += r["entry_count"]
    banks = bank_accounts(chart_path, plans)
    companies = []
    for company in COMPANIES:
        accounts = []
        for (comp, plan, account), branches in sorted(usage.items()):
            if comp != company or (plan, account) not in banks:
                continue
            meta = banks[(plan, account)]
            per_branch = {
                str(branch): dict(sorted(counts.items())) for branch, counts in sorted(branches.items())
            }
            september = {
                b: sum(v for k, v in c.items() if k.startswith("2026-09")) for b, c in per_branch.items()
            }
            used = [b for b, n in september.items() if n]
            accounts.append(
                {
                    "chart_company_code": plan,
                    "account_code": account,
                    "account_name": meta["account_name_raw"],
                    "classification": meta["classification_raw"],
                    "entries_by_branch": per_branch,
                    "september_branches": used,
                    "suggested_branch": int(used[0]) if len(used) == 1 else None,
                    "needs_choice": len(used) > 1,
                }
            )
        companies.append({"company_code": company, "bank_accounts": accounts})
    return {
        "version": "contad-branch-accounts-analysis-v1",
        "decision": "D-381",
        "source_observed_at_utc": profile["observed_at_utc"],
        "bank_association_approved": False,
        "human_reviewed": False,
        "companies": companies,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    profile = load_profile(Path(argv[1]))
    result = analyse(profile, Path(argv[2]))
    out = Path(argv[3])
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    out.chmod(0o600)
    for company in result["companies"]:
        print(f"Empresa {company['company_code']}:")
        if not company["bank_accounts"]:
            print("  nenhuma conta do grupo Depósitos Bancários com lançamento no período")
        for a in company["bank_accounts"]:
            choice = a["suggested_branch"] if a["suggested_branch"] is not None else (
                "mais de uma: " + ", ".join(a["september_branches"]) if a["needs_choice"] else "sem uso em setembro"
            )
            print(f"  conta {a['account_code']} {a['account_name']}: filial {choice}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
