"""Ratchet for D-277: product screens do not explain themselves in prose.

A paragraph (or long ``<small>``) placed right under a heading or section kicker is the shape
explanatory copy takes in these templates. Each template may only keep fewer of them than the
recorded baseline; new templates start at zero. Text that must stay (DTE resumo x ciência,
cost confirmation, demo disclaimer, irreversible action) carries ``data-copy="required"``.
"""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = Path(__file__).with_name("ui_copy_baseline.json")
APPS = ROOT / "src" / "apps"

# Public, authentication and e-mail pages follow the landing/auth voice, not the workspace rule.
OUTSIDE_WORKSPACE = re.compile(
    r"^(hub/(home|proposal|plan_simulator|legal|signup\w*|password_reset\w*|login\w*|logout\w*|"
    r"activat\w*|csrf_failure|forbidden|demo_entry|office_activation_pending|auth_base)\.html"
    r"|hub/emails/.*|platform/.*|accounts/.*)$"
)
EXPLANATION = re.compile(
    r'(?:</h[1-3]>|<p class="section-kicker">[^<]*</p>)\s*(?:</div>\s*)?'
    r'(<p(?![^>]*data-copy="required")(?![^>]*class="section-kicker")[^>]*>'
    r'|<small(?![^>]*data-copy="required")[^>]*>)(.*?)</(?:p|small)>',
    re.S,
)
MARKUP = re.compile(r"<[^>]+>|\{[{%].*?[%}]\}", re.S)


def explanatory_copy_counts() -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in sorted(APPS.glob("*/templates/**/*.html")):
        name = path.as_posix().split("/templates/", 1)[1]
        if OUTSIDE_WORKSPACE.match(name):
            continue
        for match in EXPLANATION.finditer(path.read_text(encoding="utf-8")):
            # Short lines ("12 notas", "Prazo interno") are data, not explanation.
            if len(MARKUP.sub("", match.group(2)).split()) >= 6:
                counts[name] += 1
    return counts


def test_explanatory_copy_only_shrinks():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    current = explanatory_copy_counts()
    grown = {
        name: f"{count} > {baseline.get(name, 0)}"
        for name, count in current.items()
        if count > baseline.get(name, 0)
    }
    assert not grown, f"Texto explicativo novo sob título (D-277): {grown}"


def test_baseline_is_tightened_when_copy_is_removed():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    current = explanatory_copy_counts()
    stale = {
        name: f"{baseline[name]} → {current.get(name, 0)}"
        for name in baseline
        if current.get(name, 0) < baseline[name]
    }
    assert not stale, f"Atualize tests/ui_copy_baseline.json para o valor menor: {stale}"
