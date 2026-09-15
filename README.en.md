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
| NFS-e | Certificate custody and review of received documents | Authorized ADN/NFS-e collection and supplier pilot |
| Integra Contador / guides | Entry to DTE Mailbox, Installments, and DCTFWeb. DTE has local bulk preparation and legal acknowledgement controls; Installments is unavailable; DCTFWeb currently tracks local Domínio obligations. | Implement Installments and DCTFWeb declaration consultation; validate Serpro credentials, prices, pagination, legal effect, quotas, responses, and failures with a real pilot |
| OFX × Domínio | Deterministic reconciliation and ambiguity review | Real office/company Domínio mirror validation |
| Reforma Radar | Official-source collection and linked alerts | Operational freshness, failure, and recovery evidence |
| Jornadas | Internal task board | Final functional scope; no standalone paid module |
| Copilot | Evidence-based conversations and local/Claude routing; one bounded synthetic generation confirmed through Anthropic | Limits, consent, office-facing conversation and quota validation |
| File triage | Data model, locally tested Microsoft/Google consent callback and IMAP connection wizard; pure Windows company-folder naming | Pilot real mailboxes, complete **email-only** intake/safety/review, then office-selected internal library **or** Windows folders |
| Siescon | No homologated adapter | Technical documentation and authorized pilot |

Each office can start a guided Microsoft/Google consent flow using Mewstack-owned OAuth apps; the callback, office isolation, read probe, and encrypted credential storage are implemented and locally tested. The provider apps are not registered or piloted yet. Generic IMAP now has a TLS/read-probe wizard with encrypted credentials, but still needs an authorized real-server pilot. Mailbox connection does **not** start incremental intake or archiving. The [researched connection flow](docs/planejamento/conexao-caixas-email.md) documents Mewstack app registration and Google restricted-scope verification. For Windows, the office chooses a root folder. A [local naming function](docs/planejamento/padrao-pastas-windows.md) now calculates `Company [Domínio code]` with the mandatory code; safe agent-side writing and the name/rename rule remain open. The existing Windows agent reads authorized Domínio data through ODBC; safe document writing is still to be implemented. The historical manual triage prototype cannot review or download unverified attachments from the web routes.

## Billing and production

The system records plans, contracts, allowances, usage, and invoices. Asaas was selected for standard Pix, boleto, and card billing, with individually priced manual contracts allowed. Its inbound webhook validates a dedicated token, deduplicates provider events, and updates only known Asaas payment attempts; customer/payment creation, Sandbox validation, reconciliation, and grace/read-only suspension rules remain unfinished. Deployment configurations exist for Fly.io and the Cobalchini Windows server; they do not prove a live environment. A protected, manual Cobalchini workflow is present, while the production host and environment still await operational validation.

## Verify locally

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

The latest local suite on 15 September 2026 had **512 passed, 1 skipped, and 8 subtests passed** in 38.15 seconds. The [execution record](docs/planejamento/registro-de-execucao.md) keeps dated evidence and limits. Supplier pilots, real mailbox consent, payment events, office-facing AI usage, backup restoration, SMTP, and legal/support details are needed before a commercial release.
