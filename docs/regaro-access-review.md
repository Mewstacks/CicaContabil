# Regaro: access and registration review

## Delivered scope

- Shared, independent light auth shell eliminates the legacy light-card/dark-text-token conflict. Regaro branding across login, invitation creation/acceptance/wrong-account/expired-link states, MFA enrollment/verification/recovery, no-office, forbidden, commercial trial form and browser lockout.
- Password visibility, native password-manager/paste support, explicit loading button, field hints, inline errors and focused linked error summary. No decorative scene controls or technical caption on landing. Product copy positions Regaro as an operational hub; IA and Domínio are differentiators, Siescon is labeled in preparation.
- Fixed MFA enrollment regenerating its key during POST. Recovery continuation retains the safe destination; second-factor pages disable caching. Existing codes remain valid despite issuer branding change (existing authenticator labels do not automatically rename).
- Recorded trial start on first office activation, without restarting on later invitations. Explicit recorded 14-day trials bypass office MFA; expiry and paid offices require MFA. Platform MFA remains enforced. Legacy offices use original profile creation as the upper bound and retain explicit MFA requirements until a trial is recorded; no blanket fresh trial is granted. Shared accounts touching paid offices remain subject to MFA.
- Registration request contains only contact name, email and CNPJ. Account provisioning remains invitation-based. Automatic lookup calls BrasilAPI through a fixed backend endpoint: validated CNPJ, CSRF, POST-only, per-IP rate limit, bounded timeout, short failure cache, public-data minimization and encrypted lead fields. No partner/shareholder data retained. Provider failure does not block a valid request.
- Added migrations hub 0015 and platform 0009; applied locally (hub 0014 prerequisite also applied). No data deleted, no paid resources or messaging service enabled.

## References and decisions

- Watermelon MCP `auth-01`: coherent authentication compositions, adapted to existing Django forms.
- https://www.saasframe.io/categories/login — login and Wise MFA examples catalog: focus on one access task per screen. Refero consulted, full flows unavailable; not claimed as observed.
- https://linear.app/login — restrained access entry; no unsupported SSO providers added.
- UI/UX Pro Max searches: accessible authentication, password-manager/paste support, native controls and visible focus. Web Interface Guidelines fetched at https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md and applied to changed templates/CSS/JS.
- https://brasilapi.com.br/docs and official implementation https://github.com/BrasilAPI/BrasilAPI/blob/main/pages/api/cnpj/v1/%5Bcnpj%5D.js — public CNPJ registry. Read-only sample verified endpoint response; runtime lookup tested with controlled provider responses, not private customer data.
- Receita Federal CNPJ DV specification: https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj/manual-dv-cnpj.pdf — numeric and alphanumeric validation. Provider coverage for a particular new alphanumeric registration is not guaranteed; fallback remains available.

## Audit and validation

Auth templates reviewed as a family: one main/h1, named inputs, no external fonts/theme overrides, no automatic focus on mobile arrival, explicit error focus, no zoom restrictions, wrapping invitation names and MFA secrets, QR dimensions, keyboard-native actions and bounded animation. Error text duplication removed. Public scene technical footer and pause/phase controls removed; remaining motion finishes in under two seconds and honors reduced motion.

`tests/test_regaro_auth_flow.py` renders 16 auth states in desktop/mobile (1440/390) with dark OS preference, verifying no overflow, title/brand, error focus, password toggle and CNPJ success/failure/stale-clear. Uses authenticated Django test-client HTML and local static assets in Playwright, not a live production session. No QR or real recovery secrets captured. Inspected screenshots of desktop login, mobile registration and invalid MFA, among other state artifacts. Local Playwright used because no callable Playwright MCP was available.

`scripts/qa_regaro_landing.py` validates the running landing at port 8044: desktop, tablet and 390/320 mobile widths, native evidence dialog/Escape/focus return, scenarios, FAQ, no-JS content, reduced motion, trial CTA navigation; no console errors.

45 focused tests passed (auth flow, CNPJ, MFA, lockout, existing workspace). Django check and migration drift check passed. One existing paid-contract fixture was updated to complete MFA, reflecting the new required policy rather than weakening it.

## Boundaries

Trial IA quotas and billable usage enforcement remain a separate pending implementation; no quota number was invented. This is still a guided-test request, not automatic public signup. Password reset by email is not configured in the existing application; login help directs users to the office administrator. No outbound recovery email service was enabled. Siescon runtime adapter remains unfinished and is not advertised as live. No deployment performed.
