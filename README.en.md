# CICA — Advanced Accounting Intelligence Center

[Português](README.md) · [Documentation](docs/README.md) · [Operational planning (Portuguese)](docs/planejamento/README.md)

CICA is Mewstack's Django system for Brazilian accounting firms. This repository contains the SaaS application, platform console, Celery jobs, fiscal integrations, and a Windows agent for authorized Domínio data access. The current objective is to make every module complete its real office workflow before selling it. A screen or a passing mock test does not prove supplier integration or production readiness. See the [operational status](docs/planejamento/estado-operacional.md), [confirmed decisions](docs/planejamento/decisoes.md), and [open questions](docs/planejamento/duvidas-abertas.md).

## Local development

Use Python 3.12–3.14 and `uv` 0.12.0. For SQLite development:

```powershell
python -m pip install uv==0.12.0
uv sync --locked --all-extras
uv run python scripts/init_local.py --sqlite
uv run python manage.py migrate
uv run python manage.py migrate --database=knowledge
uv run python manage.py runserver
```

`init_local.py` creates a `.env` with random local secrets and will not overwrite an existing file. Apply migrations to both the office database and the separate knowledge database. Redis is optional for local SQLite development; PostgreSQL, Redis, and Celery workers are needed to validate production-like jobs. The office login is at `/entrar/`, the Mewstack console at `/platform/`, the REST API at `/api/v1/`, and OpenAPI at `/api/docs/` when enabled.

## Claude now and a private local model later

Mewstack holds one deployment-wide Claude key in `.env` as `CICA_CLAUDE_API_KEY`. Anthropic accepted it through its **free token-counting API** and **one specifically approved, bounded synthetic generation** with `claude-sonnet-5` (16 input tokens, 64 output tokens; US$0.000672 calculated before exchange/taxes). This validates the API transport, not the office-facing Copilot workflow. The console controls the model, global budgets, and Copilot release; each office has its own consent, roles, and quotas. The Copilot remains hidden by default until those policies and the offer are configured and validated. The future private PC endpoint and model are already configurable; the runtime attempts the local model first when available. Another paid call requires fresh specific cost approval.

## Module status

| Area | Present in this worktree | Still required for sale |
| --- | --- | --- |
| NFS-e | NSU-based ADN collection with A1, atomic checkpoints, deduplication, retries, bulk controls, and document review | Pilot a real authorized certificate and ADN response before enabling external collection |
| Integra Contador / guides | Entry to DTE Mailbox, Installments, and DCTFWeb. DTE has local bulk preparation and legal acknowledgement controls; Installments is unavailable; DCTFWeb currently tracks local Domínio obligations. | Implement Installments and DCTFWeb declaration consultation; validate Serpro credentials, prices, pagination, legal effect, quotas, responses, and failures with a real pilot |
| OFX × Domínio | Deterministic reconciliation and ambiguity review | Real office/company Domínio mirror validation |
| Reforma Radar | Official-source collection and linked alerts | Operational freshness, failure, and recovery evidence |
| Copilot | Evidence-based conversations and local/Claude routing; one bounded synthetic generation confirmed through Anthropic | Limits, consent, office-facing conversation and quota validation |
| File triage (replaces Journeys) | Data model, locally tested Microsoft/Google consent callback and IMAP connection wizard; pure Windows company-folder naming | Pilot real mailboxes, complete **email-only** intake/safety/review, then office-selected internal library **or** Windows folders |
| Siescon | No homologated adapter | Technical documentation and authorized pilot |

An office administrator registers its own Microsoft 365/Google Workspace OAuth application using the guided steps in File Triage, saves its encrypted app secret, then authorizes the office mailbox directly with the provider. **Personal Gmail** uses a verified Mewstack Google app once registered and piloted, with consent for each office's own account. The callback, office isolation, read probe, and encrypted refresh credentials are locally tested against simulated providers. Mewstack must still set the production HTTPS redirect and verify its personal Gmail app; offices must register and pilot real Microsoft/Workspace apps. Generic IMAP has a TLS/read-probe wizard with encrypted credentials, but still needs an authorized real-server pilot. Mailbox connection does **not** start incremental intake or archiving. The [researched connection flow](docs/planejamento/conexao-caixas-email.md) documents provider setup and Google restricted-scope constraints. For Windows, the office chooses a root folder. A [local naming function](docs/planejamento/padrao-pastas-windows.md) now calculates `Company [Domínio code]` with the mandatory code; safe agent-side writing and the name/rename rule remain open. The existing Windows agent reads authorized Domínio data through ODBC; safe document writing is still to be implemented. The historical manual triage prototype cannot review or download unverified attachments from the web routes.

## Billing and production

The agreed commercial structure is a minimum monthly fee per module, a separate token allowance per module, and automatic overage up to the office's accepted monthly cap. One CICA token has the same price everywhere and is consumed in **whole numbers**; action weights vary by cost and work. The [market/cost study](docs/planejamento/precificacao-tokens-modulos.md) evaluates **R$ 0.05 per token** as the owner's suggested reference, without an approved final tariff. Integra Contador action weights must use the **most expensive current Serpro band** even when the central Mewstack account later reaches a cheaper band. The current meter still counts units per service. Asaas was selected for standard Pix, boleto, and card billing, with individually priced manual contracts allowed. Its inbound webhook validates a dedicated token, deduplicates provider events, and updates only known Asaas payment attempts; customer/payment creation, Sandbox validation, reconciliation, and grace/read-only suspension rules remain unfinished. Deployment configurations exist for Fly.io and the Cobalchini Windows server; they do not prove a live environment. A protected, manual Cobalchini workflow is present, while the production host and environment still await operational validation.

## Verify locally

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

The latest local suite on 15 September 2026 had **531 passed, 1 skipped, and 8 subtests passed** in 37.55 seconds after email attachments were stored in private quarantine, incremental IMAP/Microsoft Graph readers were exercised with synthetic servers, and a candidate local ClamAV verdict gate was tested with a synthetic socket. No real inbox or scanner is installed or approved on this PC; clean verdicts remain quarantined until the file-format/signature policy is approved. The [execution record](docs/planejamento/registro-de-execucao.md) keeps dated evidence and limits. Supplier pilots, real mailbox consent, payment events, office-facing AI usage, backup restoration, SMTP, and legal/support details are needed before a commercial release.
