# Progresso — dominio-mcp (Fase 1 núcleo e Fase 1b)

Plano: [../../docs/specs/dominio-mcp-plano.md](../../docs/specs/dominio-mcp-plano.md). Gate 1 aprovado pelo responsável em 21/11/2026. Decisões em D-317 a D-330 de `DECISOES.md`. **Gate 2 aprovado pelo responsável em 22/11/2026; commit local `0c9ab04f`, sem push, merge nem deploy.**

| Marco | Estado | Prova |
|---|---|---|
| M0 registro e esqueleto | feito (21/11/2026) | T0.0 `DECISOES.md` só com acréscimos; T0.1 pacote `uv` em Python 3.12; T0.2 `config.py` |
| M1 execução no ODBC | feito (21/11/2026) | `values.py`, `odbc.py`, `watchdog.py`, `budget.py`, `quarantine.py`; teste vivo `tests/live/test_live_driver.py`: 6 passaram no banco real (cancelamento em ~2 s com conexão reutilizável, `sa_conn_info()` confirma término, acento por ponto de código, `isolation_level` 0) |
| M2 catálogo, política e pack | feito (21/11/2026) | `catalog.py`, `enums.py`, `policy.py` (+ `policy.yaml`), `readable.py`, `overlay.py`, `pack.py`, `pack_index.py`, `freshness.py`, `buildpack.py`; pack real em 20,8 a 32,9 s e 32,5 a 32,8 MB, 4.964 objetos, 18 ilegíveis, frescor sem falso positivo: [pack-real.md](pack-real.md) |
| M3 recuperação | feito, **A3 não atendido** (21/11/2026) | `textnorm.py`, `search.py`, `evaluation.py`, `joins.py`, overlay (`glossary`, `core_tables`, `modules`). Cego v1 queimado (top-5 76%, top-1 43%); cego v2 top-5 91%, top-1 50%: [recall.md](recall.md). Falta o lote da contadora |
| M4 consulta L2 e carga | feito, **T4.9 pendente da janela do dono** (21/11/2026) | `query_spec`, `compiler`, `scope`, `literals`, `admission`, `shaping`, `executor`; L2 vivo aprovado (agregados no banco real). Critérios de carga escritos antes do ensaio em [carga.md](carga.md); harness `tests/live/test_live_load.py` só roda com `DOMINIO_MCP_LOAD_WINDOW=1` |
| M5 ferramentas L0 e L1 | feito (21/11/2026) | `tools_schema.py` (L0), `verified.py` + 4 YAML; vivo: SQL roda, `movimento_fiscal` bate com L2 independente: [conferencia.md](conferencia.md). Conferência contra relatório oficial do Domínio **pendente (contadora)** |
| M6 servidor, auditoria e CLI | feito (21/11/2026) | `audit.py`, `server.py` (SDK `mcp` 2.3.0, 10 ferramentas, 3 anotações, erros estruturados, perfil), `cli.py` (`serve`, `build-pack`, `doctor`, `reset`); e2e por stdio real com ODBC falso e pelo CLI real |
| M7 prova no banco real | feito em parte (21/11/2026) | T7.1 [pack-real.md](pack-real.md); T7.2 [recall.md](recall.md) (A3 não atendido); T7.3: marcadores plantados em todas as saídas (`tests/test_markers_e2e.py`) e recusa por objeto no catálogo real ([privacidade.md](privacidade.md)) feitos, **revisão independente de 300 colunas (A7c) pendente (contadora)**; T7.4 conferência L1 × L2 viva em [conferencia.md](conferencia.md), **oficial e carga pendentes** |
| M8 guia, registros e revisão | feito em parte (21/11/2026) | T8.1 guia do dono ([docs/dominio-mcp.md](../../docs/dominio-mcp.md), [README](../README.md)) e [clientes.md](clientes.md): **nenhum cliente real testado**, SDK `mcp` 2.3.0 e 1.30.0 testados por stdio. T8.2 revisão do Codex em duas rodadas: 18 achados, todos reproduzidos por teste que falhava e corrigidos (D-328). T8.3 registros: V-308 a V-310 em `VALIDACOES.md`, `registro-de-execucao.md`, ligações em `docs/README.md` e `docs/intelligence-mcp.md` |
| M9 L3 (Fase 1b) | feito (23/11/2026) | `rawsql.py` (gramática mínima, traduz para L2), `tools_rawsql.py` (só perfil `local` com `raw_sql`, checado no registro e no despacho); `tests/test_rawsql_attack.py` (100 ataques recusados, 13 de política, 12 de junção, 13 consultas legítimas que passam), `tests/test_tools_rawsql.py`; vivo: 3 testes no banco real (D-330, V-312) |
| M10 HTTP em loopback (Fase 1b) | feito (23/11/2026) | `http_app.py`, `serve --http`, `http-token`; `tests/test_http_security.py` (33): bind, `Host`, `Origin`, token, teto de tentativas, corpo, cliente MCP real em porta efêmera |
| M11 `.mcpb` (Fase 1b) | feito em parte (23/11/2026) | `mcpb/manifest.json`, `mcpb/server/main.py`, `scripts/build_mcpb.py` (15,2 MiB, `mcpb validate` ok), `scripts/prove_mcpb.py` (instalação em pasta nova do sistema com venv vazio, `pyodbc` e `pywintypes` do pacote, 10 ferramentas, glossário empacotado). **Falta o teste manual no Claude Desktop em perfil Windows limpo**: só depois conta como entregue |

Verificação do pacote em 23/11/2026 (da raiz do repositório): `ruff check`, `ruff format --check`, `mypy src` limpos; `pytest -q`: 835 passam, 22 vivos pulados, 2 de avaliação fora do padrão; vivos com `DOMINIO_MCP_LIVE=1`: 20 passam, 1 (carga) exige a janela do dono.

## Desvios do plano (decisão técnica, sem mudar comportamento)

- `overlay/` e `verified/` ficam dentro do pacote, em `src/dominio_mcp/data/`, para serem lidos por `importlib.resources` também no `.mcpb` (M11). Os nomes dos arquivos não mudam.
- `Limits.executions_per_minute` (padrão 20, teto 120) é o orçamento de frequência de T1.4. O valor é provisório até a calibração de T4.9.
- Cliente do SDK 1.30 contra o servidor real em `tests/compat/client_v1.py` (script manual, fora do pytest): o ambiente do pacote só tem o SDK 2.3.0.

## O que a revisão do Codex mudou (D-328)

- Texto livre **só se lê**: nenhum filtro. A busca por conteúdo em observação e histórico deixa de existir no L2.
- Junção só por chave `normal`; duas filhas do mesmo pai, e `sum`, `avg` e `count` do lado "um" de qualquer junção, são recusados (total multiplicado).
- Agregado pessoal exige 3 contribuições não nulas por expressão; `DISTINCT` exige permissão de agrupar; texto longo é cortado no servidor (`LEFT(coluna, 400)`) e só se lê.
- A execução recusa se o pack mudou entre a compilação e a execução; orçamento de frequência ilegível fecha uma janela; quarentena que não grava em disco mantém a trava de processo.
- Texto de tabela por empregado passou de `texto_livre` para `pessoal/folha`: 84 colunas no banco real (pessoal 5.007 para 5.091, texto livre 2.157 para 2.073).
- `conferir_numeracao` compara o próximo número com o maior fim acumulado, não só com a faixa vizinha.

## Revisor de segurança automático (22/11/2026, D-329)

Três pontos sobre o commit `0c9ab04f`, conferidos antes de decidir: agregado pessoal agora conta **pessoas distintas** (`i_empregados`), não linhas; largura desconhecida classifica pelo lado seguro (o banco real tem 0 colunas assim); CPF preenchido com zeros nunca vale como CNPJ (1,4% fechavam por acaso, medido). `PACK_FORMAT` subiu para 4. **Limite declarado:** com `allow_pii` ligado a subtração entre duas consultas ainda revela o valor de uma pessoa.

## Achados de execução

- `MAX(last_modified_at)` anda sem DDL (14:00 para 18:00 com as seis contagens iguais): saiu da sonda de frescor (evidência 13; spec e plano corrigidos).
- Aceite de colunas (`build-pack --aceitar`) é decisão do dono: a construção real foi **sem** aceite, então `consulta_estruturada` não alcança coluna nenhuma (0 colunas `normal`) até ele decidir; L0 e as quatro rotinas L1 já funcionam (conferido no pack real, 21/11/2026).
- O pack real ficou desatualizado quando o overlay mudou depois da primeira construção e o guarda de frescor acusou; reconstruído três vezes no mesmo dia.
- View não aprovada bloqueia todas as suas colunas (`view_nao_aprovada`), mesmo com aceite.
- Tabela com coluna `i_empregados` (295 medidas) só deixa livres as colunas de chave; o resto é `pessoal/folha`.
- `SELECT COUNT(*) FROM sa_conn_info() WHERE Number = ?` funciona no banco real e distingue conexão aberta de encerrada (teste vivo).
- Quando o cancelamento não é confirmado, a conexão descartada é fechada por uma thread de limpeza assim que a thread da consulta termina de fato; só então a sonda vê o término e a quarentena pode sair sozinha.
- Erros do driver nunca viajam: `DbError` só tem tipo, SQLSTATE e código nativo, e é levantado fora do `except` para não deixar o texto do driver como contexto encadeado.
- No SQL Anywhere 17.0.11 o `[` do `LIKE` abre classe de caracteres (`[5][2][9]` casa '529'); `!` escapa o `[`, e `]`, `^` e `-` fora de classe são literais.
- `MAX(...) OVER (... ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` existe no 17.0.11 (conferido com constantes), embora `LAG` e `LEAD` não.

- Recuperação: o desenvolvimento (97% no top-5) enganou: o cego v1 deu 76%. Radical do português no índice e na consulta e apelido proporcional à cobertura da pergunta foram as melhorias gerais; o top-1 de 50% no v2 segue abaixo da meta de 70%.
- `ruff format` troca escape unicode (`"ç"`) por o caractere literal nos testes; para o caractere de substituição use `chr(0xFFFD)`.
- `uv run --directory dominio-mcp` muda o diretório: caminho relativo em script quebra, use caminho absoluto.

- O SQL Anywhere 17.0.11 não tem `LAG`/`LEAD` (erro -131 em `OVER`); lacunas de numeração saem do pareamento por `ROW_NUMBER`. `ROW_NUMBER() OVER (PARTITION BY ...)` funciona.
- `conferir_numeracao` cobre só saídas e serviços (notas emitidas): na entrada a numeração é do fornecedor, então lacuna e duplicidade não fazem sentido (desvio da spec, que citava `efentradas`).
- `empresas` e `empresa_perfil` tratam `razao_emp` como texto livre (a regra de largura a classifica assim): sai mascarado por padrão de valor e cortado em 200 caracteres.
- SDK `mcp` 2.3.0 (não o 1.29 da spec): a classe é `MCPServer`, o resultado usa `is_error`; um servidor 2.x conversa com cliente 1.30 (protocolo 2025-11-25 negociado, testado também contra o servidor real do pacote).
- A resposta das ferramentas é JSON compacto em texto: o SDK indentaria um `dict` e estouraria o teto de 12 KB medido em compacto.

## Depende de você ou da contadora

- Aceitar o catálogo (`build-pack --aceitar`)? Sem isso `consulta_estruturada` fica fechada.
- Janela autorizada para o ensaio de carga (T4.9) e aviso a quem usa o Domínio.
- Lote cego da contadora (A3), revisão independente de 300 colunas (A7c) e conferência de `movimento_fiscal` contra o relatório oficial.
- OK para a Fase 1b (L3 local, HTTP em loopback, `.mcpb`) e para a Fase 2 (gateway no CICA, Serpro); plano do ChatGPT e custo do túnel a confirmar.
- Teste real de Claude Desktop, Claude Code e ChatGPT (usa cota; matriz em [clientes.md](clientes.md)).

## Fase 1b (23/11/2026, D-330)

- L3 não é filtro de SQL: é uma gramática mínima que **converte** o `SELECT` em consulta L2, então herda a política inteira e não abre nada que L2 não abra. O `ON` tem que ser exatamente a FK declarada.
- O HTTP só escuta em `127.0.0.1` ou `::1`, é sempre perfil `remote` e fica atrás de `Host` fixo, recusa de `Origin`, token de 256 bits e teto de tentativas.
- A prova de instalação do `.mcpb` achou um defeito que nenhum teste de manifesto acharia: `PYTHONPATH` não lê `.pth` e o SDK exige `pywintypes` no Windows. `main.py` passou a chamar `site.addsitedir`.
- Pendente: teste manual do `.mcpb` no Claude Desktop em perfil limpo; cliente HTTP real (só o SDK foi testado).
