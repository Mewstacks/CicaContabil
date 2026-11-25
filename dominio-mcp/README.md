# dominio-mcp

Servidor MCP **somente leitura** para o banco do Domínio (SAP SQL Anywhere 17). Ensina o esquema à IA sem estourar o contexto, devolve número rastreável (tabela, filtro, hora da leitura) e não deixa sair segredo nem dado pessoal. Nunca escreve no banco.

Guia completo do dono do escritório: [docs/dominio-mcp.md](../docs/dominio-mcp.md). Spec: [docs/specs/dominio-mcp.md](../docs/specs/dominio-mcp.md). Plano: [docs/specs/dominio-mcp-plano.md](../docs/specs/dominio-mcp-plano.md). Progresso: [reports/progresso.md](reports/progresso.md). Matriz por cliente: [reports/clientes.md](reports/clientes.md).

## Requisitos

- Windows com o Domínio instalado e um DSN de sistema ODBC de 64 bits (padrão `contabil`) com a credencial embutida no próprio DSN. A credencial nunca vai para arquivo de configuração nem para a saída.
- Python 3.12 a 3.14 de 64 bits e [`uv`](https://docs.astral.sh/uv/).

## Primeira vez

Da pasta `dominio-mcp` (ou de fora, com `--directory <caminho absoluto>`):

```powershell
uv run dominio-mcp doctor
uv run dominio-mcp build-pack
uv run dominio-mcp serve
```

- `doctor` confere DSN, driver, legibilidade, pack e quarentena. Rode antes de ligar um cliente: baixa as dependências e mostra o que falta.
- `build-pack` lê o catálogo do banco (≈ 33 s no banco real) e gera o pack local. **Sem `--aceitar`** as colunas que nenhuma regra classificou ficam bloqueadas; aceitar o catálogo é decisão do dono (ver o guia).
- `serve` fala MCP por stdio. É o comando que Claude Desktop, Claude Code e o túnel do ChatGPT executam.
- `serve --http` fala o mesmo MCP em `http://127.0.0.1:8765/mcp` com token (`http-token`): só loopback, sempre perfil `remote`.
- `relay-job` (stdin JSON, stdout JSON) é o repasse do gateway pelo agente: só as onze ferramentas L0 a L2, perfil `remote`, sem SQL.
- `analise_da_carteira` roda oito análises da carteira inteira (notas sem lançamento, faturamento e limite do Simples, empresas sem movimento, variação, cadastro, lançamentos contábeis, cancelamentos, numeração) e o roteiro `briefing_da_carteira` resume o mês: [pesquisa e escopo](../docs/specs/dominio-mcp-carteira.md), [validação](reports/carteira.md).
- L3 (`sql_somente_leitura`) só existe com `serve --profile local` e `raw_sql = true`: é SQL em gramática mínima convertido em consulta L2, com a mesma política.
- `scripts/build_mcpb.py` monta `dist/dominio-mcp-<versão>.mcpb` (Windows x64, Python 3.12) e `scripts/prove_mcpb.py` o instala numa pasta nova com venv vazio e conversa com ele. O teste no Claude Desktop em perfil limpo ainda é manual.

Cada cliente tem o seu passo a passo no guia. **Nenhum cliente real foi testado ainda** (só o cliente do SDK `mcp` por stdio): veja [reports/clientes.md](reports/clientes.md).

## Serviço para o CICA

`dominio-mcp agent-enroll`, `agent-run` e `agent-status` pareiam o computador com o CICA e respondem aos pedidos do escritório (só conexão de saída, mesmo `relay-job`). Como serviço do Windows: `python scripts/build_instalador.py` e o `instalar-servico.ps1` do pacote. Manual de uma página: [reports/manual-instalacao-uso.pdf](reports/manual-instalacao-uso.pdf); detalhes em [docs/dominio-mcp.md](../docs/dominio-mcp.md).

## Verificação do pacote

A partir da raiz do repositório:

```powershell
uv run --directory dominio-mcp ruff check .
uv run --directory dominio-mcp ruff format --check .
uv run --directory dominio-mcp mypy src
uv run --directory dominio-mcp pytest -q
```

Testes vivos (somente leitura, sem imprimir valor de negócio) só rodam com `DOMINIO_MCP_LIVE=1`. O ensaio de carga exige também `DOMINIO_MCP_LOAD_WINDOW=1`, que declara que o dono autorizou a janela ([reports/carga.md](reports/carga.md)). A medição de recuperação contra o conjunto cego v2 exige `DOMINIO_MCP_BLIND=1` ([reports/recall.md](reports/recall.md)).

`uv run --directory` muda o diretório de trabalho: use caminho absoluto em scripts.

## Mapa do código

| Área | Módulos em `src/dominio_mcp/` |
|---|---|
| Execução segura no ODBC | `odbc`, `values`, `watchdog`, `budget`, `quarantine` |
| Catálogo, política e pack | `catalog`, `enums`, `policy`, `readable`, `overlay`, `pack`, `pack_index`, `freshness`, `buildpack` |
| Recuperação do esquema | `textnorm`, `search`, `evaluation`, `joins` |
| Consulta estruturada (L2) | `query_spec`, `compiler`, `scope`, `literals`, `admission`, `shaping`, `executor` |
| SQL de leitura (L3, só local) | `rawsql` (gramática mínima, traduz para L2), `tools_rawsql` |
| Ferramentas | `tools_schema` (L0), `verified` (L1, YAML em `data/verified/`) |
| Servidor | `server`, `http_app` (loopback com token), `audit`, `cli`, `config` |

Conhecimento curado (política, glossário, tabelas centrais, módulos, legendas, views aprovadas) fica em `src/dominio_mcp/data/overlay/`. Mudar a política ou o overlay muda a versão do pack e exige `build-pack`.
