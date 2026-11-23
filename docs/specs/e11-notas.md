# Triagem v2, fase A (E11 itens 1 a 3): estado e decisões

Base: worktree em `main` (2cc9c5c8). Spec: `docs/specs/cica-venda-v2.md` (só existe em `feat/produto-vendavel`).

## Feito e commitado (local, sem push)
- CNPJ alfanumérico na extração (`extraction.py`, `normalize_cnpj`). AC-11.4 parte.
- Migração aditiva `triage/0012`: `DocumentType` (keywords, expected_default, expected_regimes), `TriageItem` (origin, body_excerpt, original_sender, archive_parent, ocr_state, ocr_text), `TriagePolicy`, `TriageOcrUsage`.
- Catálogo por escritório: `catalog.py`, `catalog_forms.py`, `hub/views_triage_catalog.py`, template `triage_catalog.html`, `triage-v2.css`; seed contábil opt-in; exceção por empresa; pasta do tipo vale no destino Windows. AC-11.1.
- Ingestão: `intake_policy.py`, `mailtext.py`; logo ignorado, anexo estranho/grande vira Rejeitado e caixa segue (IMAP, Graph, Gmail), corpo e remetente original gravados; formato inválido no scan vira Rejeitado. AC-11.2 parcial.

## Decisões
- E11-D1 Pacote aberto fecha como Rejeitado com motivo "Pacote aberto: N arquivos" (novo status exigiria AlterField, vetado por `test_migration_safety`). Exige nova aresta `EXTRACTING -> REJECTED` em `transitions.py` (pendente).
- E11-D2 Rejeitar-e-continuar e ignorar logo valem para todos os escritórios (correção de falha); formatos extras, ZIP e OCR ficam por escritório (`TriagePolicy`, padrão desligado); OCR também exige `TRIAGE_OCR_ENABLED` global e orçamento.
- E11-D3 Graph usa só `bodyPreview` (limite de 1 MB por página de delta).
- E11-D4 Sem dependência nova: `.xls` aceito sem leitura de conteúdo (sem xlrd), HTML com `html.parser`.
- E11-D5 Sem Codex nem IA externa.

## Pendente
- ZIP: `archives.py` escrito (sem commit, testes `tests/test_triage_archives_django.py` não rodados); falta `archive_expand`, aresta de transição, ramo em `extract_item`, `file_policy` estendido (imagem, html, txt, xls, zip) passando `policy_for`.
- Upload manual (view + service pelo mesmo pipeline; `_require_verified_email_item` aceitar origin upload/archive).
- Leitores (xlsx, html, txt) e OCR em fila própria (`triage_ocr`, flag, orçamento).
- Tela de política (Entrada), link "Enviar arquivo".
- Verificação: copiar `test_legacy_contract`, `test_migration_safety`, `test_tenant_isolation_matrix` (e `legacy_baseline`, `tenant_matrix_support`, `pki_support`) de `feat/produto-vendavel` para rodar; não existem na base `main`.
- Itens 4 a 8 da seção 7 ficam para a fase B.
