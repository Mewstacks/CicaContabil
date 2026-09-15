# Regaro landing — 12 September 2026

## Superseding iteration: spatial-v6

User rejected the previous centered editorial landing and excessive explanation. Rebuilt with a concise accounting pain point, a code-native CSS 3D layered product scene (data → IA → decision), native phase/pause buttons, a short question/answer demonstration and a compact operational module list. Removed the public calculator and all public pricing tables. Calculator now appears inside the existing authenticated Settings page, without changing contracts or enabling billing.

User approved a 14-day trial with limited AI usage. Public copy and internal simulator reflect that; numerical AI quotas remain undefined and no quota enforcement was added in this visual task.

Additional references consulted: https://www.raycast.com/ (concise product narrative), https://linear.app/ (product-first demonstration), Watermelon `fund-widget` (3D transforms, adapted into native CSS), and https://www.nngroup.com/articles/concise-scannable-and-objective-how-to-write-for-the-web/ (short, scannable copy). Refero and SaaSFrame were consulted again; no inaccessible full flow was claimed as inspected. These references inform the design, not a claim of proven conversion improvement.

V6 audit: current Vercel guidelines fetched again. Checked home.html, landing CSS/JS, plan_simulator.html, plan CSS/JS and Settings insertion. Animation uses transform/opacity, finishes rather than loops, offers phase buttons/pause, and respects reduced motion. Native controls, labels, dialog keyboard handling and visible focus retained. The mobile scene grid initially overflowed; corrected its bounds and reran four viewport checks. The simulator is a read-only estimate and communicates empty and undefined-six-module states.

V6 validation: `scripts/qa_regaro_landing.py` targets port 8038. Screenshots and keyboard/interaction checks cover the public page. `tests/test_regaro_landing_django.py` separately tests public/private placement and serves authenticated Django test-client HTML with local static assets to Playwright (not a production login session), checking calculator behavior and light/dark mobile/desktop rendering. Earlier v5 details below are historical, not the current composition.

## Scope

Replaced the public landing only. Standalone HTML shell prevents authenticated theme overrides from changing marketing contrast. Existing authenticated screens, invitation model and commercial lead handler are preserved. Temporary code-native wordmark; no paid assets, font requests, external animation dependencies or provisioning.

## Research applied

- https://contaazul.com/contadores/ — accounting-specific benefits, explain implementation and commercial next step.
- https://ramp.com/ — product-led demonstration tied to an operational outcome.
- https://attio.com/ — concrete questions about business records, not abstract AI imagery.
- https://linear.app/ — connect product narrative to a sequence of work.
- Watermelon MCP, `astrix-dashboard` — exception review, evidence and human decision. Catalog consulted; no proprietary components copied.
- Refero and SaaSFrame consulted in prior research; authenticated full flows were not accessible. They are not claimed as verified behavioral evidence.
- https://www.hubcontador.com.br/ — connected AI is also advertised by the competitor; no exclusivity claim in this page.

UI/UX Pro Max guidance applied: reduced motion, no continuous animation, native controls, readable contrast and responsive composition. Existing Django stack retained.

## Review against current Web Interface Guidelines

Source fetched: https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md

- `home.html`: semantic headings, skip link, labeled checkbox/select controls, native dialog and details, pressed states, live result/status, public demo explicitly fictional, no fake testimonials or unsupported performance metrics.
- `regaro-landing.css`: scoped standalone palette, visible focus, hover feedback, responsive grid, bounded dialog with contained scrolling, no `transition: all`, no zoom restriction, animations use transform/opacity and respect reduced motion.
- `regaro-landing.js`: textContent for scenario data, no HTML injection, cancelable 500ms transition, native dialog Escape/focus restoration, scenario deep link, Intl currency formatting. No API calls, SQL or database connection in the public demo.
- Pricing handles 0 and 6 modules explicitly; no invented six-module discount. Consumption excluded from discounts and estimates.

## Validation

`python scripts/qa_regaro_landing.py` against local server at 127.0.0.1:8037. Playwright MCP unavailable; installed Python Playwright used instead.

Checked 1440×1000, 768×1024, 390×844 and 320×700; no horizontal overflow. Inspected desktop/mobile hero, mobile demonstration and desktop pricing screenshots. Tested three scenarios, evidence modal, Escape and return focus, skip link visible focus, FAQ, calculator empty/six/full-suite states, company multiplier, reduced motion with dark OS preference, and navigation to existing lead form. Browser console clean. Demo is synchronous, so no simulated server loading/error claims. No live AI or integration security certification implied.

`python manage.py check`: passed. `pytest -q tests/test_hub_workspace_views_django.py`: 24 passed. `git diff --check`: no whitespace errors (existing CRLF warnings).

## Remaining boundaries

This iteration does not finish the entire authenticated SaaS plan. Lead form submission/error states and real connector behavior were not visually audited in this landing-only change. Commercial terms and actual module availability still require confirmation before public release. No deployment or domain purchase performed.
