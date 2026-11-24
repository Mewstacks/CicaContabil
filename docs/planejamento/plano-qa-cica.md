# Plano de QA do CICA com três skills

Criado em 22/10/2026. Complementa o [roteiro funcional](../../CICA-QA.md); não o substitui. Fonte de verdade de escopo e critérios: [plano mestre](../../PLANO-MESTRE.md), [decisões](../../DECISOES.md), [validações](../../VALIDACOES.md).

## Skills e papel de cada uma

| Skill | Origem | Camada | Uso no CICA |
|---|---|---|---|
| `senior-qa-engineer` | javalenciacai/qaskills | Processo | Ciclo de QA: análise de risco, desenho de casos, registro de defeitos, melhoria. |
| `django-tdd` | affaan-m/ecc | Backend | pytest-django, factory_boy, mocks, DRF, cobertura. |
| `playwright-skill` | testdino-hq/playwright-skill (guias verificados no Playwright 1.64) | UI / E2E | Suíte `@playwright/test`, locators, fixtures, trace, a11y, visual, CI. |

Limite conhecido de `senior-qa-engineer`: o `SKILL.md` manda orquestrar via skills que não vieram junto (`multi-agent-orchestration`, `user-story-verifier`, `test-design-istqb`, `test-execution-manager`, `defect-lifecycle-manager`, `cicd-testing-integration`, `qa-process-improvement`, `find-skills`). Sem elas, usar só a persona, o ciclo (tabela de fases) e o princípio "nunca instalar sem aprovação". Não criar nem instalar as ausentes sem pedir.

## Regras da rodada

- Só ambiente local isolado (`scripts/qa_ui_server.py`, `127.0.0.1:8011`, SQLite de teste) e Postgres do CI. Nada em produção, nada com dado de cliente, nenhuma API paga ou Serpro/Asaas/IA externa sem autorização.
- Todo defeito vai no formato de [CICA-QA.md §6](../../CICA-QA.md). "Não testado" e "bloqueado" nunca viram "aprovado".
- Cobertura e precisão são métricas separadas (D-73). Não aplicar percentual a fluxo sem medida definida.
- Pesquisar antes de corrigir; citar fonte na proposta de correção.
- Texto renderizado segue a regra de UI copy; `tests/test_ui_copy_rule.py` continua verde.

## Fase 0: linha de base (senior-qa-engineer)

1. Registrar commit, branch (`codex/contraprova`, árvore suja), ambiente, flags.
2. Rodar e anotar resultado sem editar nada:
   - `uv run ruff check .` e `uv run python manage.py check`
   - `uv run python manage.py makemigrations --check --dry-run`
   - `uv run pytest -q` (SQLite) e `uv run pytest -m "not performance" -q`
   - `uv run pytest --ds=config.settings.test_postgresql -q` (precisa Postgres 17 em `55432`)
   - `uv run pytest --cov` (gate `fail_under = 85`)
   - `dotnet test agent-windows/tests/Cica.Agent.Tests/Cica.Agent.Tests.csproj -c Release`
3. Saída: tabela passou/falhou/pulado, cobertura por app, testes lentos. Falha pré-existente vira defeito, não é consertada em silêncio.

## Fase 1: mapa de risco (senior-qa-engineer)

Montar matriz **função × risco × camada** a partir de CICA-QA §4 e §5. Camadas: `pytest`, `playwright`, `manual`, `externo-bloqueado`. Prioridade crítica (CICA-QA §6): vazamento entre escritórios, associação errada de empresa, duplicidade fiscal/financeira, falsa conclusão, perda de dado, operação externa incerta.

Ordem de ataque:

1. Isolamento e permissão (§3): 7 papéis, vínculo revogado, módulo desligado, suporte somente leitura, outro escritório.
2. NFS-e e revisão fiscal (§4.4): idempotência, hash do original, pacote de conferência × ZIP de originais.
3. Contraprova (módulo novo, `src/apps/crosscheck`, ainda sem commit): motor, EFD, XML, chaves monetárias, ciclo de vida, agente.
4. Central Integra (DTE, DCTFWeb, parcelamentos): custo, repetição, resultado incerto.
5. Triagem, Conciliação, Rentabilidade, Radar, Copiloto, cobrança.
6. Agente Windows: autorização, catálogo por hash, checkpoints.

## Fase 2: backend (django-tdd)

Antes de escrever, ler `tests/conftest.py`, `config/settings/test.py` e um teste vizinho; copiar o molde existente. O projeto usa `pytest-django` com nome `test_*_django.py` para testes com banco. Verificar se já há `factory_boy`; se não, não introduzir sem decidir.

1. Lacunas de cobertura por app abaixo do gate, priorizadas pela Fase 1.
2. Matriz de acesso parametrizada: para cada rota `/app/...` e `/api/v1/...`, papel × recurso próprio/alheio/módulo desligado. Esperado: sem leitura ou mutação fora do escopo, erro sem revelar existência do recurso (D-226). Cobrir POST, download e tarefa em fila.
3. Idempotência e concorrência (Postgres): NSU repetido, evento de webhook repetido/fora de ordem, geração mensal de atividades, lote de até 50 itens.
4. Contraprova: casos de borda do motor (chave repetida, centavos, ZIP corrompido, EFD truncado), orçamento de desempenho com marcador `performance`.
5. Mocks só nas fronteiras externas (Serpro, Asaas, IMAP/Graph/Gmail, IA); app própria nunca mockada.
6. Regressão: cada defeito corrigido ganha teste que falha antes da correção.

## Fase 3: UI e E2E (playwright-skill)

Abrir o guia do tema antes de cada decisão (o próprio skill exige). Estado atual: não há `package.json`; existem `scripts/qa_*.cjs` rodando Playwright por `PLAYWRIGHT_MODULE`.

1. Decidir pasta (`e2e/` fora de `src`), `package.json` mínimo com `@playwright/test` fixado, `playwright.config` com `baseURL` `http://127.0.0.1:8011`, `trace: 'on-first-retry'`, retries `2` só em CI, projetos: desktop 1440, 768, 375.
2. Fixtures de login por perfil com `storageState` (personas de `seed_personas`, só com DEBUG). Credenciais só de seed local.
3. Migrar os fluxos de `qa_ui_access.cjs`, `qa_ui_browser.cjs`, `qa_ui_extended.cjs`, `qa_ui_guides.cjs`, `qa_ui_contrast.cjs` para specs com locators por papel, sem `waitForTimeout`. Preservar a rota que bloqueia tudo fora de `127.0.0.1:8011`.
4. Jornadas críticas: cadastro e login com MFA, equipe e carteira, atividade (filtro, lote, concluir), NFS-e (filtro, seleção, pacote), DTE/guias em modo demo, Triagem, Conciliação, Rentabilidade, landing e demo (PDF fictício identificável).
5. Matriz de interface (CICA-QA §5): 375 e paisagem, claro/escuro, foco visível, Escape, teclado, sem rolagem horizontal, console sem erro, contraste AA com número, alvo de toque.
6. Dados extremos: nome longo, vazio, zero itens, emoji, homônimos, carteira extensa.
7. Acessibilidade com axe; regressão visual só onde o desenho estiver estável (baselines por projeto).
8. Screenshots e traces ficam fora do git e são apagados no fim da rodada.

## Fase 4: exploratório e registro (senior-qa-engineer)

Sessões cronometradas de 45 min por módulo seguindo CICA-QA §4, com charter de uma linha. Cada achado vira registro §6 com release exata, passos, evidência (teste ou trace), impacto. Retestar na mesma release.

## Fase 5: CI

Estender `.github/workflows/ci.yml` sem afrouxar nada existente:

- job `e2e` em `ubuntu-24.04`, ações fixadas por SHA como as demais, sobe `qa_ui_server.py`, roda Playwright, publica trace só em falha;
- manter `--cov` e `fail_under = 85`;
- suíte Postgres continua separada.

## Critérios de saída

- Linha de base verde ou cada falha com defeito aberto.
- Matriz de acesso (Fase 2.2) completa e verde nas rotas críticas.
- Zero defeito crítico aberto; sem vazamento, duplicidade ou associação errada.
- Jornadas da Fase 3.4 verdes em 375 e desktop, console limpo.
- D-73: 200 itens por fluxo automatizado, 95% de precisão onde houver medida, retomada em até 15 min, processamento por empresa em até 5 min. Fluxos sem medida definida ficam listados como "sem critério".
- Relatório final: o que foi executado, onde, com qual release e o que ficou **não testado** ou **bloqueado** (integrações reais: Serpro, Asaas, Domínio, Siescon, caixas de e-mail).

## Ordem sugerida de sessões

1. Fase 0 + 1 (leitura e execução, sem edição).
2. Fase 2.1–2.3.
3. Fase 3.1–3.3 (infra e migração dos scripts).
4. Fase 3.4–3.7.
5. Fase 2.4 (Contraprova) depois que o módulo for commitado.
6. Fase 4 e 5, relatório.
