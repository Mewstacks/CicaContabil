# Plano — MCP do Domínio, Fase 1 (21/11/2026, revisado após a crítica do Codex)

**Estado (21/11/2026):** gate 1 aprovado pelo responsável. T0.0 feito: decisões em D-317 a D-327 de `DECISOES.md`; D-328 registra o que a revisão adversarial do código mudou (T8.2). Marcos concluídos são listados em `reports/progresso.md` do pacote.

Spec e critérios (A1 a A13): [dominio-mcp.md](dominio-mcp.md). Um gate de aprovação (spec e plano) antes de implementar, outro no diff. Tudo novo mora em `dominio-mcp/` (pacote Python próprio, `uv`), sem editar o legado nem os módulos da frente "produto vendável". Todos os caminhos das tabelas abaixo são relativos a `dominio-mcp/` (`src/…`, `tests/…`, `overlay/…`, `verified/…`, `reports/…`), exceto `DECISOES.md`, `VALIDACOES.md` e `docs/…`. Sem estimativa de calendário (AGENTS.md): P, M e G são tamanhos relativos. Cada tarefa começa pelo teste vermelho.

**Núcleo da Fase 1:** stdio, L0, quatro ferramentas L1 e L2 (M0 a M8). **Fase 1b**, cada incremento com OK próprio: L3 (M9), HTTP em loopback (M10), `.mcpb` (M11). **Fase 2** (gateway no CICA, Serpro): [dominio-mcp-fase2.md](dominio-mcp-fase2.md).

## Ordem e dependências

M0 → M1 → M2 → (M3, M4 em paralelo) → M5 → M6 → M7 → M8. M2 termina com o pack real (T2.9 traz o comando mínimo). A calibração de carga (T4.9) vem **antes** de liberar agregação em tabela grande e precisa de janela que o dono autorize. M7 depende de M3 (conjunto cego congelado) e M4.

**Verificação do pacote**, a cada tarefa e ao fim de cada marco (rodar da raiz do repo):

```powershell
uv run --directory dominio-mcp ruff check .
uv run --directory dominio-mcp ruff format --check .
uv run --directory dominio-mcp mypy src
uv run --directory dominio-mcp pytest -q <arquivos da tarefa>
```

Testes vivos (somente leitura, sem imprimir valor de negócio) só rodam com `DOMINIO_MCP_LIVE=1`:

```powershell
$env:DOMINIO_MCP_LIVE = '1'; uv run --directory dominio-mcp pytest -q -m live tests/live
```

## M0 — Registro e esqueleto (P)

| Tarefa | Arquivos | Verificação |
|---|---|---|
| T0.0 Registrar as DM aprovadas em `DECISOES.md` com o próximo ID livre, preservando o escopo de DM-1 (L3 só local, desligada) como exceção à D-18 (AGENTS.md:10: registrar antes de executar) | `DECISOES.md` | `git diff DECISOES.md` só com acréscimos; nenhum ID repetido (`grep -n "^## D-" DECISOES.md`) |
| T0.1 Pacote, ferramentas e marcadores `live` e `eval` | `pyproject.toml`, `src/dominio_mcp/__init__.py`, `tests/test_smoke.py` | `pytest -q tests/test_smoke.py`; `ruff`; `mypy src` |
| T0.2 Configuração (TOML + `DOMINIO_MCP_*`; `raw_sql` falso, `allow_pii` vazio, perfil `remote` por padrão) | `src/dominio_mcp/config.py`, `tests/test_config.py` | `pytest -q tests/test_config.py` |

## M1 — Execução no ODBC (G)

| Tarefa | Arquivos | Verificação |
|---|---|---|
| T1.1 Normalização de valores (decimal, data com lixo, bytes, espaços do `char`) | `src/dominio_mcp/values.py`, `tests/test_values.py` | `pytest -q tests/test_values.py` |
| T1.2 Conexão e execução: pooling desligado, `isolation_level 0`, busca em UTF-16, **um cursor por execução**, `fetchmany` com linha-sonda de truncamento, erros mapeados | `src/dominio_mcp/odbc.py`, `tests/fake_odbc.py`, `tests/test_odbc.py` | `pytest -q tests/test_odbc.py` |
| T1.3 Vigia preso ao cursor, evento `done`, exceção do `cancel()` engolida e auditada, confirmação em 10 s, descarte da conexão | `src/dominio_mcp/watchdog.py`, `tests/test_watchdog.py` | `pytest -q tests/test_watchdog.py` (A termina no limite e o cancelamento de A chega atrasado; `cancel()` bloqueia; `cancel()` falha) |
| T1.4 Trava entre processos por DSN, fila de 1, orçamento de frequência e **quarentena compartilhada** (arquivo de estado ao lado da trava, sobrevive à queda do processo; saída só por término confirmado em `sa_conn_info()` ou `reset` explícito) | `src/dominio_mcp/budget.py`, `src/dominio_mcp/quarantine.py`, `tests/test_budget.py`, `tests/test_quarantine.py` | `pytest -q tests/test_budget.py tests/test_quarantine.py` (dois processos reais não executam juntos; com `cancel()` bloqueado por mais de 60 s nenhum dos dois admite execução; recuperação após queda) |
| T1.5 Teste vivo do driver: cancelamento em ≤ 4 s e conexão reutilizável, `cancel()` tardio em cursor fechado, confirmação de término por `sa_conn_info()`, `fetchmany`, acento por ponto de código | `tests/live/test_live_driver.py` | `pytest -q -m live tests/live/test_live_driver.py` |

## M2 — Catálogo, política e pack (G)

| Tarefa | Arquivos | Verificação |
|---|---|---|
| T2.1 Extração do catálogo (objetos, colunas, comentários, PK, FK, índices, definição de view) | `src/dominio_mcp/catalog.py`, `tests/fixtures/mini_catalog.json`, `tests/test_catalog.py` | `pytest -q tests/test_catalog.py` |
| T2.2 Legendas: "A - Ativa / I - Inativa", "(1 - Sim/0 - Nao)", "1=Normal, 2=Zer", "(S/N)", faixas "14-19=Hono"; sem rótulo = nenhuma legenda | `src/dominio_mcp/enums.py`, `tests/test_enums.py` | `pytest -q tests/test_enums.py` |
| T2.3 Classes (segredo, documento, pessoal, texto livre, normal, não classificada), lista de bloqueio, máscara por valor (só CNPJ válido passa inteiro, o resto de `documento` sai mascarado; `documento` nunca em agrupamento, ordenação ou agregação), tabelas de auditoria e log | `src/dominio_mcp/policy.py`, `overlay/policy.yaml`, `tests/test_policy.py` | `pytest -q tests/test_policy.py` |
| T2.4 Catálogo sintético com marcadores plantados (segredo em `audados.valor`, CPF em observação, view com `conteudo`, coluna nova) e teste de que nenhum marcador sai (A7a) | `tests/fixtures/synthetic_catalog.json`, `tests/test_policy_markers.py` | `pytest -q tests/test_policy_markers.py` |
| T2.5 Sonda de legibilidade em lote (`SELECT … WHERE 1=0`, com controle negado) | `src/dominio_mcp/readable.py`, `tests/test_readable.py` | `pytest -q tests/test_readable.py` |
| T2.6 Modelo do pack e **versão composta** (estrutura, views, comentários, política, overlay) | `src/dominio_mcp/pack.py`, `tests/test_pack_version.py` | `pytest -q tests/test_pack_version.py` (mudar só view, FK, comentário ou política muda a versão) |
| T2.7 Índices do pack: FTS5, trigramas do nome e features do prior estrutural | `src/dominio_mcp/pack_index.py`, `tests/test_pack_index.py` | `pytest -q tests/test_pack_index.py` |
| T2.8 Frescor: sonda barata (contagens e soma do tamanho das definições de view; `MAX(last_modified_at)` descartado, E13), re-hash completo ao iniciar e a cada 1 h, bloqueio de L1 e L2 com pack desatualizado, troca atômica; view só consultável em L2 se aprovada no overlay por nome e hash da definição | `src/dominio_mcp/freshness.py`, `overlay/views_aprovadas.yaml`, `tests/test_freshness.py` | `pytest -q tests/test_freshness.py` |
| T2.9 Comando mínimo de construção e **prova no banco real** (A1, A2) | `src/dominio_mcp/buildpack.py` (`python -m dominio_mcp.buildpack`), `reports/pack-real.md` | saída do comando com tempo, tamanho e versão |

## M3 — Recuperação (M)

| Tarefa | Arquivos | Verificação |
|---|---|---|
| T3.1 Busca híbrida (BM25, trigramas, sinônimos, prior estrutural) e overlay inicial | `src/dominio_mcp/search.py`, `overlay/glossary.yaml`, `overlay/core_tables.yaml`, `overlay/modules.yaml`, `tests/test_search.py` | `pytest -q tests/test_search.py` |
| T3.2 Dois conjuntos: **desenvolvimento** (as 26 já medidas, mais as derivadas dos contratos) e **cego** (≥ 40 perguntas novas de contadora e dos relatórios oficiais, estratificadas por módulo e família de intenção, relevância = conjunto de tabelas aceitas, congelado por hash **antes** de qualquer ajuste; medido uma vez por versão do overlay e queimado se falhar) | `tests/eval/dev.yaml`, `tests/eval/blind.yaml`, `tests/eval/blind.sha256`, `tests/eval/test_retrieval_eval.py` | `pytest -q -m eval tests/eval` reporta dev e cego separados; o teste falha se o hash do cego mudar |
| T3.3 Caminho de junção por FK declarada (BFS, até 4 saltos, chaves compostas) | `src/dominio_mcp/joins.py`, `tests/test_joins.py` | `pytest -q tests/test_joins.py` |

## M4 — Consulta estruturada L2 e orçamento de carga (G)

| Tarefa | Arquivos | Verificação |
|---|---|---|
| T4.1 Modelo da consulta e validação contra o pack (objeto legível e classificado, colunas, funções, operadores, limites) | `src/dominio_mcp/query_spec.py`, `tests/test_query_spec.py` | `pytest -q tests/test_query_spec.py` |
| T4.2 Compilador, parte 1: filtros e operadores (`=`, `in`, `between`, prefixo, nulo), aspas e parâmetros `?` | `src/dominio_mcp/compiler.py`, `tests/test_compiler_filters.py` | `pytest -q tests/test_compiler_filters.py` |
| T4.3 Compilador, parte 2: agregação, agrupamento, ordenação, `TOP`/`START AT` e a regra de `DISTINCT` com `ORDER BY` | `src/dominio_mcp/compiler.py`, `tests/test_compiler_aggregates.py` | `pytest -q tests/test_compiler_aggregates.py` |
| T4.4 Compilador, parte 3: junção por FK declarada, resolução de alias e junção até a coluna de origem, classe da origem em filtro, ordenação e agrupamento | `src/dominio_mcp/compiler.py`, `tests/test_compiler_joins.py` | `pytest -q tests/test_compiler_joins.py` (A6) |
| T4.5 Escopo: filtro de empresa em tabela grande, janela ≤ 13 meses, no máximo 2 junções, coluna líder de índice | `src/dominio_mcp/scope.py`, `tests/test_scope.py` | `pytest -q tests/test_scope.py` |
| T4.6 Admissão por custo: `SELECT PLAN(?)` com o SQL interno como **parâmetro ligado**, codificador de literais tipados testado com entrada adversarial (aspas, `;`, comentário, texto com cara de comando, unicode, valor enorme) que recusa estimativa **e** execução quando não consegue codificar com segurança, validação da resposta do `PLAN`, leitura de `Estimated cost` (principal) e `Estimated rows` | `src/dominio_mcp/admission.py`, `src/dominio_mcp/literals.py`, `tests/fixtures/plans/*.txt`, `tests/test_admission.py`, `tests/test_literals.py` | `pytest -q tests/test_admission.py tests/test_literals.py` (planos gravados do banco real, incluindo a auto-junção patológica) |
| T4.7 Moldagem da saída: teto de 12 KB, colunas, células, máscara por valor (documento; CPF, e-mail e telefone dentro de texto livre), `consistencia` e `lido_em`, supressão de grupos < 3, `texto_livre` | `src/dominio_mcp/shaping.py`, `tests/test_shaping.py` | `pytest -q tests/test_shaping.py` |
| T4.8 Execução de ponta a ponta com ODBC falso e teste vivo agregado | `src/dominio_mcp/executor.py`, `tests/test_executor.py`, `tests/live/test_live_query.py` | `pytest -q tests/test_executor.py`; `pytest -q -m live tests/live/test_live_query.py` |
| T4.9 **Calibração de carga em janela autorizada pelo dono**, com critérios escritos e commitados em `reports/carga.md` **antes** do ensaio (p95 da sonda de interferência ≤ 2× a linha de base e ≤ 250 ms) e tabela estimado × real de ≥ 10 consultas para fixar o orçamento com fator de segurança | `tests/live/test_live_load.py`, `reports/carga.md` | `pytest -q -m live tests/live/test_live_load.py` (A11) |

## M5 — Ferramentas L0 e L1 (G)

| Tarefa | Arquivos | Verificação |
|---|---|---|
| T5.1 L0: `mapa_do_banco`, `buscar_esquema`, `descrever_tabela`, `caminho_entre_tabelas`, `valores_do_campo` | `src/dominio_mcp/tools_schema.py`, `tests/test_tools_schema.py` | `pytest -q tests/test_tools_schema.py` (A4: ≤ 12 KB; sem segredo nem pessoal) |
| T5.2 Consultas verificadas: carregador YAML, dependências conferidas no pack, desliga com o motivo se o esquema mudou | `src/dominio_mcp/verified.py`, `verified/README.md`, `tests/test_verified.py` | `pytest -q tests/test_verified.py` |
| T5.3 L1 `empresas` e `empresa_perfil` (semente: `contracts/datasets/companies.v1.sql`, `taxation.v1.sql`) | `verified/empresas.yaml`, `verified/empresa_perfil.yaml`, `src/dominio_mcp/tools_business.py`, `tests/test_tools_business.py` | `pytest -q tests/test_tools_business.py` |
| T5.4 L1 `movimento_fiscal` (segmento da nota, `cancelada_*`, situação), conferida por L2 independente e contra um relatório do Domínio | `verified/movimento_fiscal.yaml`, `tests/live/test_live_movimento.py` | `pytest -q -m live tests/live/test_live_movimento.py` |
| T5.5 L1 `conferir_numeracao` (lacunas e duplicidades) | `verified/conferir_numeracao.yaml`, `tests/test_numeracao.py` | `pytest -q tests/test_numeracao.py` |

## M6 — Servidor, auditoria e CLI (M)

| Tarefa | Arquivos | Verificação |
|---|---|---|
| T6.1 Auditoria em JSONL sem valor de linha, com versão do pack | `src/dominio_mcp/audit.py`, `tests/test_audit.py` | `pytest -q tests/test_audit.py` |
| T6.2 Servidor FastMCP por stdio: registro, três anotações, `instructions` autocontidas, recursos (`dominio://mapa`, `dominio://glossario`), prompts, ordem determinística, perfil e autorização no despacho | `src/dominio_mcp/server.py`, `tests/test_server_contract.py` | `pytest -q tests/test_server_contract.py` (A10) |
| T6.3 e2e por stdio com cliente do SDK e backend falso | `tests/test_e2e_stdio.py` | `pytest -q tests/test_e2e_stdio.py` |
| T6.4 CLI: `doctor`, `build-pack` (`--aceitar` para colunas novas), `serve --profile` | `src/dominio_mcp/cli.py`, `tests/test_cli.py` | `pytest -q tests/test_cli.py` |

## M7 — Prova no banco real (M)

| Tarefa | Arquivos | Verificação |
|---|---|---|
| T7.1 `doctor` e `build-pack` no banco real (A1, A2) | `reports/pack-real.md` | saída dos dois comandos com tempo, tamanho e versão |
| T7.2 Recall no pack real: ajustar o overlay **só** com o conjunto de desenvolvimento e medir o cego uma vez (A3) | `overlay/*.yaml`, `reports/recall.md` | `pytest -q -m eval tests/eval` |
| T7.3 Privacidade em três provas: marcadores sintéticos, recusa explícita por objeto no catálogo real, revisão independente de 300 colunas estratificadas, falso-negativo por classe (A7) | `tests/live/test_live_privacy_sweep.py`, `reports/privacidade.md` | `pytest -q -m live tests/live/test_live_privacy_sweep.py`; falso-negativo de segredo = 0 e de pessoal < 2% |
| T7.4 Conferência L1 × L2 e `consistencia` (A9), com a carga medida em T4.9 | `reports/conferencia.md` | `pytest -q -m live tests/live` |

## M8 — Guia, registros e revisão (M)

| Tarefa | Arquivos | Verificação |
|---|---|---|
| T8.1 Guia do dono (Claude Desktop, Claude Code, ChatGPT por túnel com `--profile remote`, privacidade, limites, problemas comuns) e **matriz real por cliente** (A12) | `README.md`, `docs/dominio-mcp.md`, `reports/clientes.md` | revisão do texto; links conferidos; matriz marcada "pendente de teste real" até ser rodada; o guia só declara compatibilidade para cliente "testado em <data e versão>" |
| T8.2 Revisão adversarial pelo Codex do código (segurança e privacidade), no máximo 2 rodadas; cada achado vira teste que falha antes da correção | — | skill `codex-review`; testes novos verdes |
| T8.3 Registros: `VALIDACOES.md` (V-3xx), `docs/planejamento/registro-de-execucao.md`, ligação em `docs/intelligence-mcp.md` e `docs/README.md` (só acréscimos; as decisões já entraram em T0.0) | `VALIDACOES.md`, `docs/planejamento/registro-de-execucao.md`, `docs/intelligence-mcp.md`, `docs/README.md` | `git diff` mostra só acréscimos nesses arquivos |

## Fase 1b (cada incremento com OK próprio)

| Marco | Tarefas e arquivos | Verificação |
|---|---|---|
| M9 L3 (perfil `local`) | gramática mínima e recusa do desconhecido (`src/dominio_mcp/rawsql.py`); suíte de ataque ≥ 60 casos **e** consultas legítimas que precisam passar (`tests/test_rawsql_attack.py`); ferramenta `sql_somente_leitura` só no perfil `local` com `raw_sql` e checada no despacho (`src/dominio_mcp/tools_rawsql.py`, `tests/test_tools_rawsql.py`) | `pytest -q tests/test_rawsql_attack.py tests/test_tools_rawsql.py` (A5) |
| M10 HTTP em loopback | `src/dominio_mcp/http_app.py`, `tests/test_http_security.py`: `127.0.0.1`, token, `Origin` | `pytest -q tests/test_http_security.py` |
| M11 `.mcpb` | `mcpb/manifest.json`, `scripts/build_mcpb.py`, dados por `importlib.resources`; prova: instalar o artefato final em venv limpa **fora do checkout** e listar ferramentas com backend falso; perfil Windows limpo = teste manual, e o `.mcpb` só conta como entregue depois dele | `npx -y @anthropic-ai/mcpb validate mcpb/manifest.json` + prova de instalação |

## Fim de marco e fim de fase

Fim de marco: os quatro comandos do pacote verdes. Fim do núcleo: `pytest -q` do pacote inteiro, testes vivos e relatórios de M7 anexados, `git diff --stat` mostrando que só `dominio-mcp/`, `docs/` e os registros de T0.0 e T8.3 mudaram (nenhum arquivo de código do legado) e o portão do repo (`scripts/quality_gate.py`) sem regressão.

## O que depende de você

- OK da spec e deste plano (gate 1) e do diff (gate 2). Merge e qualquer publicação só com OK explícito.
- Ordem da entrega (DM-4): o plano assume núcleo por stdio primeiro, depois 1b e Fase 2.
- **Janela autorizada** para a calibração de carga (T4.9) e para a conferência viva de M7.
- Contadora para o conjunto cego (A3), para a revisão independente das 300 colunas (A7c) e para conferir `movimento_fiscal` contra um relatório do Domínio.
- Fase 2: nenhuma chamada paga ao Serpro, nenhuma VM nova e nenhum deploy sem confirmação com valor.

## Triagem da crítica do Codex (rodada 1, 21/11/2026)

Crítica somente leitura (`gpt-6.1-sol`, esforço alto) sobre spec, plano e a evidência real; repositório idêntico antes e depois. Veredito dela: **não aprova nesta rodada**. Cada achado foi conferido por citação exata ou por sonda no banco antes de aceitar.

| # | Achado | Veredito | Onde ficou resolvido |
|---|---|---|---|
| 1 | A7 mede a política contra ela mesma | aceito | A7 em três provas; coluna não classificada bloqueada; T2.4, T7.3 |
| 2 | Política por origem e contexto da linha | aceito | classe `documento` com máscara por valor, origem resolvida, permissões separadas; T2.3, T4.4, T4.7 |
| 3 | Guarda léxica de L3 sem contrato | aceito, L3 adiado | M9 na Fase 1b, A5 com consultas legítimas |
| 4 | Impressão não cobre dependências | aceito | versão composta, frescor, troca atômica; T2.6, T2.8 |
| 5 | Vigia pode cancelar a consulta seguinte | aceito em parte | `cancel()` em cursor fechado é inofensivo (sonda); um cursor por execução e, depois da rodada 2, quarentena compartilhada; T1.3, T1.4 |
| 6 | Sem orçamento de carga | aceito, com achado novo | `PLAN()` estima custo sem executar (sonda); T1.4, T4.5, T4.6, T4.9 |
| 7 | L3 local × túnel | aceito | perfis `remote`/`local`, checagem no despacho; T6.2 |
| 8 | `isolation_level = 0` e consistência | aceito em parte | `consistencia` e `lido_em` em todo resultado; T4.7 |
| 9 | Conjunto dourado contaminado | aceito | dev × cego congelado por hash; T3.2 |
| 10 | M2 exige entrega que só existe em M8 | aceito | T2.9 comando mínimo |
| 11 | Fatos medidos sem evidência ou com erro | aceito | números reconciliados e ligados a E01–E11 |
| 12 | `mcpb validate` não prova instalação | aceito | M11 com prova em venv limpa; perfil limpo = manual |
| 13 | Compatibilidade com clientes | aceito em parte | matriz real (A12); a parte "não demonstrado" sobre `readOnlyHint` e 512 caracteres foi descartada: a doc oficial da OpenAI diz isso |
| 14 | Decisões registradas depois do comportamento | aceito | T0.0 antes de M0; texto de D-18 corrigido |

Perguntas de tamanho e de desenho mais simples: aceitas. T1.2, T2.5, T4.2 e T6.1 foram subdivididas; L3, HTTP e `.mcpb` saíram do núcleo.

### Rodada 2 (verificação, `gpt-6.1-terra`, esforço alto)

Repositório idêntico antes e depois. Veredito do Codex: **não aprova nesta rodada** ("lacunas na autorização de dados, no controle de carga e na construção segura da consulta usada por `PLAN()`"). Fechados por ele: 3, 7, 8, 10 e 14. Os nove "parciais" e os três achados novos foram aceitos; os dois pontos que dependiam do banco foram provados antes (E12). Pelo skill não há rodada 3: se ainda houver dúvida, desempata revisão por Claude em sessão nova e você decide.

| Item | Estado na rodada 2 | Veredito | Onde ficou resolvido |
|---|---|---|---|
| 1 A7 só mede segredo | parcial | aceito | A7c por classe (pessoal < 2%) e máscara por padrão de valor em texto livre; T4.7, T7.3 |
| 2 Classe `documento` | parcial | aceito | só CNPJ válido passa inteiro, o resto é mascarado, nunca em agrupamento, ordenação ou agregação; T2.3 |
| 4 Janela de 6 h sem detectar | parcial | aceito | re-hash a cada 1 h, soma das definições de view, view só em L2 se aprovada por hash; T2.8 |
| 5 e novo 2: retomada com execução incerta | parcial + alta | aceito, provado | quarentena compartilhada por DSN, saída só por término confirmado (`sa_conn_info()` é acessível ao Externo, E12) ou `reset`; T1.4 |
| 6 Interferência e estimado × real | parcial | aceito | critérios registrados antes do ensaio e tabela estimado × real; T4.9, A11 |
| 9 Famílias e reavaliação | parcial | aceito | estratificação e lote cego queimado; T3.2, A3 |
| 11 e novo 3: tempos transcritos | parcial + baixa | aceito | faixas "2 a 19 ms" e "26 a 54 ms", medições pontuais; spec |
| 12 `.mcpb` em perfil limpo | parcial | aceito (redação) | só conta como entregue após o teste manual; M11 |
| 13 Matriz pendente | parcial | aceito (redação) | guia só declara compatibilidade com "testado em"; A12 |
| Novo 1: escape do `PLAN()` | alta | aceito, provado | `SELECT PLAN(?)` com parâmetro ligado (E12) e codificador de literais testado; T4.6 |
