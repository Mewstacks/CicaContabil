# MCP do Domínio — guia do dono do escritório

Estado em 21/11/2026: Fase 1 (núcleo por stdio) implementada e provada contra o banco real, **sem nenhum cliente real testado** (só o cliente do SDK `mcp`) e com pendências abertas na seção [Pendências e limites da prova](#pendências-e-limites-da-prova). Spec: [specs/dominio-mcp.md](specs/dominio-mcp.md). Plano: [specs/dominio-mcp-plano.md](specs/dominio-mcp-plano.md). Decisões: D-317 a D-328 em [`DECISOES.md`](../DECISOES.md). Código: [`dominio-mcp/`](../dominio-mcp/README.md).

Este MCP é **separado** do MCP interno do Hub ([intelligence-mcp.md](intelligence-mcp.md)), que continua sem SQL livre e sem endpoint externo.

## O que é

Um servidor MCP que roda **no computador do escritório**, lê o banco do Domínio (SAP SQL Anywhere 17) pelo DSN ODBC e entrega à IA:

| Camada | Ferramentas | De onde vem a resposta |
|---|---|---|
| L0 conhecimento | `mapa_do_banco`, `buscar_esquema`, `descrever_tabela`, `caminho_entre_tabelas`, `valores_do_campo` | Só do pack local (um SQLite gerado do catálogo do banco). Não consulta dado de negócio. |
| L1 rotinas verificadas | `empresas`, `empresa_perfil`, `movimento_fiscal`, `conferir_numeracao` | SQL fixo e revisado, em YAML dentro do pacote. |
| L2 consulta estruturada | `consulta_estruturada` | A IA manda JSON (tabela, colunas, filtros, agrupamento, agregação, junção por chave estrangeira); o programa valida e monta o SQL parametrizado. |

Também expõe os recursos `dominio://mapa` e `dominio://glossario` e os roteiros `conferir_empresa` e `explorar_assunto`.

- **A IA nunca envia SQL.** Nenhum texto SQL de terceiro chega ao banco. SQL livre (L3) não existe nesta fase; fica para a Fase 1b, só no perfil `local` e com decisão própria.
- Toda ferramenta declara `readOnlyHint: true`, `destructiveHint: false`, `openWorldHint: false`. Isso é dica para o cliente, não autorização: a autorização real é a do despacho.
- Todo resultado traz `lido_em`, `tabelas`, `pack`, `truncado` e `consistencia: leitura_nao_confirmada`. A leitura roda sem trava de transação (`isolation_level = 0`), então pode ver dado ainda não confirmado. **Número fiscal é diagnóstico a conferir no Domínio, não apuração.**

## O que precisa

- Windows com o Domínio instalado e um **DSN de sistema ODBC de 64 bits** (padrão `contabil`). A credencial fica embutida no próprio DSN: nunca vai para arquivo de configuração, saída ou log.
- Python 3.12 a 3.14 de 64 bits e [`uv`](https://docs.astral.sh/uv/).
- A pasta `dominio-mcp` deste repositório.

## Primeira vez

Troque `C:\caminho\HubContador` pelo caminho real. `--no-dev` evita instalar as ferramentas de teste.

1. **Conferir o ambiente.** Baixa as dependências na primeira vez e mostra o que falta. Na primeira vez `pack: AUSENTE` é esperado.

   ```powershell
   uv run --no-dev --directory C:\caminho\HubContador\dominio-mcp dominio-mcp doctor
   ```

2. **Gerar o pack.** Lê só o catálogo do banco (nomes, tipos, chaves, comentários), em cerca de 33 s no banco real, e publica o pack em `%LOCALAPPDATA%\dominio-mcp\packs\<dsn>\`. A saída só tem números.

   ```powershell
   uv run --no-dev --directory C:\caminho\HubContador\dominio-mcp dominio-mcp build-pack
   ```

3. **Decidir o aceite (decisão do dono).** Sem `--aceitar`, toda coluna que nenhuma regra classificou fica **bloqueada** (`nao_classificada`). No banco real foram 48.560 colunas, mais 2.379 de 102 views ainda não aprovadas. Nessa situação as quatro rotinas L1 funcionam (o YAML revisado faz o papel de curadoria), mas `consulta_estruturada` não alcança nenhuma coluna de negócio: o pack real sem aceite tem 0 colunas `normal` ([reports/pack-real.md](../dominio-mcp/reports/pack-real.md)).

   `--aceitar` aprova o catálogo atual como base: toda coluna sem regra passa a `normal`. **Coluna sensível (segredo, documento, pessoal, texto livre) nunca é liberada por aceite.** O risco é a classificação ser heurística sobre nome e comentário: uma coluna sensível com nome sem pista passaria como `normal`. A revisão independente de 300 colunas que mede esse risco (A7c) ainda não aconteceu ([reports/privacidade.md](../dominio-mcp/reports/privacidade.md)). Só rode depois de decidir:

   ```powershell
   uv run --no-dev --directory C:\caminho\HubContador\dominio-mcp dominio-mcp build-pack --aceitar
   ```

4. **Conferir de novo.** Com pack e sem quarentena o `doctor` termina limpo.

5. **Ligar um cliente** (próxima seção). O comando que todos executam é `dominio-mcp serve` (stdio).

## Ligar no cliente

Em todos os casos o cliente inicia o processo `dominio-mcp serve`. O perfil padrão é `remote`, o correto para qualquer processo iniciado por terceiro. Nesta fase `--profile local` não muda nenhuma ferramenta (só aparece na auditoria e prepara o L3 da Fase 1b), então não é preciso passá-lo.

Se o cliente não achar `uv`, ponha o caminho completo no lugar de `uv`: `(Get-Command uv).Source` mostra.

### Claude Desktop

Menu do Claude na barra do sistema, **Settings…**, aba **Developer**, **Edit Config**. O arquivo é `%APPDATA%\Claude\claude_desktop_config.json`. Dentro de `mcpServers`:

```json
{
  "mcpServers": {
    "dominio": {
      "command": "uv",
      "args": [
        "run", "--no-dev",
        "--directory", "C:\\caminho\\HubContador\\dominio-mcp",
        "dominio-mcp", "serve"
      ]
    }
  }
}
```

Salve, **feche o Claude Desktop por completo** e abra de novo. Logs: `%APPDATA%\Claude\logs\mcp.log` (conexão) e `mcp-server-dominio.log` (o stderr do servidor, que mostra a versão do pack e o perfil).

### Claude Code

```powershell
claude mcp add dominio -- uv run --no-dev --directory C:\caminho\HubContador\dominio-mcp dominio-mcp serve
claude mcp list
```

O `--` separa as opções do Claude do comando do servidor. Sem `--scope`, o servidor vale só para a pasta atual (escopo `local`); `--scope user` vale para todas. Remover: `claude mcp remove dominio`.

### ChatGPT (túnel seguro, não testado)

O ChatGPT na web não chama um programa do seu computador: precisa do **Secure MCP Tunnel** da OpenAI, em que o `tunnel-client` roda no escritório, só com saída HTTPS (`api.openai.com:443`), e repassa as chamadas ao servidor por stdio. Segundo a página oficial:

- precisa de organização na Plataforma OpenAI, de um `tunnel_id`, de uma chave de API de execução do `tunnel-client` e das permissões de túnel (Read e Manage para criar; Read e Use para rodar). **A página não diz qual plano do ChatGPT permite servidor MCP próprio nem o custo da conta de Plataforma: confirmar antes de prometer ao escritório.**
- o túnel precisa estar associado ao workspace do ChatGPT e o uso de servidor MCP próprio depende das permissões e restrições do workspace.
- comando (stdio), com o `tunnel-client` baixado de `github.com/openai/tunnel-client/releases/latest`:

  ```powershell
  $env:CONTROL_PLANE_API_KEY = "<chave de execução do tunnel-client>"
  tunnel-client init --sample sample_mcp_stdio_local --profile dominio --tunnel-id <tunnel_id> --mcp-command "uv run --no-dev --directory C:\caminho\HubContador\dominio-mcp dominio-mcp serve --profile remote"
  tunnel-client doctor --profile dominio --explain
  tunnel-client run --profile dominio
  ```

- no ChatGPT: `chatgpt.com/plugins`, **Add custom MCP server**, conexão **Tunnel**, escolher o túnel.
- limites da página: 600 requisições por minuto por túnel, mensagem de até 10 MiB, prazo de 120 s por requisição. Os limites do `dominio-mcp` (12 KB por resposta, 30 s por consulta) ficam abaixo.

Os passos acima vêm da documentação da OpenAI; **nada disso foi rodado**. O `tunnel-client` com caminho que tem espaço (`--mcp-command`) também não foi testado.

### Claude na web e no celular

Precisam de URL pública com OAuth. Só pelo gateway do CICA, na Fase 2 ([specs/dominio-mcp-fase2.md](specs/dominio-mcp-fase2.md)). O túnel do Claude é Enterprise, por pedido.

### Compatibilidade

Só é declarado como compatível o cliente com linha "testado em <data e versão>". Matriz completa em [reports/clientes.md](../dominio-mcp/reports/clientes.md).

| Cliente | Estado |
|---|---|
| Cliente do SDK `mcp` 2.3.0 e 1.30.0, por stdio | testado em 21/11/2026 |
| Claude Desktop | não testado |
| Claude Code | não testado |
| ChatGPT (túnel) | não testado |

## Privacidade: o que sai do computador

**Sai** tudo o que uma ferramenta devolve (no máximo 12 KB por chamada): razão social, CNPJ, totais mensais, nomes de tabela e coluna, comentários do dicionário do Domínio. Isso passa a fazer parte da conversa e é processado pelo provedor do cliente (Anthropic ou OpenAI), nas condições do plano e das configurações de dados da conta usada. **Conferir essas condições é decisão do dono**, que também responde pelos dados dos clientes do escritório.

**Não sai:**

- a credencial do DSN (fica no ODBC e nunca é lida pelo programa);
- coluna de segredo (senha, token, certificado): bloqueada sempre, sem opção de liberar, e o comentário dela nem entra no pack;
- dado pessoal enquanto o dono não liberar a categoria (`allow_pii`);
- SQL cru, valor de linha no log de auditoria e texto de erro do driver.

Como cada classe de coluna é tratada:

| Classe | Tratamento |
|---|---|
| `segredo` | Nunca sai. Tabela de credencial inteira bloqueada. |
| `documento` | Só passa, sem máscara, CNPJ válido (numérico ou alfanumérico). Nunca entra em agrupamento, ordenação ou agregação. |
| `pessoal` (cpf, folha, endereco, contato, bancario, nascimento, nome) | Bloqueada até o dono liberar a categoria em `allow_pii`. Liberada, ainda sai mascarada, não serve de filtro e só agrega (soma, média, contagem) em grupos com pelo menos 3 contribuições não nulas. Tabela com coluna `i_empregados` só deixa livres as colunas de chave: o texto dela também é `pessoal/folha`. |
| `texto_livre` | **Só se lê**: nenhum filtro (`contém` e `começa com` confirmariam por contagem o que a máscara esconde). Padrões de CPF, e-mail e telefone (inclusive sem pontuação) saem mascarados e a célula é cortada em 200 caracteres. Texto de tabela de auditoria ou log fica bloqueado. A busca por conteúdo em observação e histórico não existe no L2 (D-328). |
| `normal` | Sai como está, dentro dos limites. |
| `nao_classificada` | Bloqueada até o aceite (`build-pack --aceitar`). |

View do banco só abre depois de aprovada em `views_aprovadas.yaml`; sem aprovação todas as colunas dela ficam bloqueadas.

**Limite declarado:** a classificação é uma heurística sobre nome e comentário de coluna. O que ela não reconhece fica fora da promessa de privacidade até a revisão independente (A7c) medir o falso-negativo.

## Limites de uso

Valores padrão e teto duro (a configuração recusa valor acima do teto):

| Limite | Padrão | Teto |
|---|---|---|
| Linhas por resposta | 50 (máximo 500; 2.000 em agregação) | 500 / 2.000 |
| Colunas por consulta | 40 | 40 |
| Tamanho da resposta | 12 KB | 12 KB |
| Tempo por consulta | 30 s (depois cancela) | 30 s |
| Confirmação de cancelamento | 10 s | 60 s |
| Consultas por minuto | 20 | 120 |
| Custo estimado pelo banco (`PLAN`) | 10 | 100 |
| Linhas estimadas pelo banco | 1.000.000 | 10.000.000 |

Os limites de custo e frequência são **provisórios**: só serão calibrados depois do ensaio de carga, que precisa de janela autorizada pelo dono e aviso a quem usa o Domínio ([reports/carga.md](../dominio-mcp/reports/carga.md)).

Regras da `consulta_estruturada`:

- tabela grande (mais de 50 mil linhas) com coluna `codi_emp` exige filtro de empresa, e o filtro acompanha as junções;
- período fechado de até 13 meses (396 dias), numa coluna de data de **tabela grande** (a data de cadastro de uma tabela pequena não vale);
- no máximo 2 junções, só por chave estrangeira declarada, até 4 saltos de caminho, e só quando as colunas de chave são `normal` (a igualdade do `ON` também lê a coluna);
- junção que repete linha não soma: duas tabelas filhas do mesmo pai são recusadas, e `sum`, `avg` e `count` de coluna do lado "um" de uma junção também (o total sairia multiplicado); use a coluna da tabela filha, `max`, `min` ou `count_distinct`;
- `distinto`, `agrupar_por` e `ordenar_por` só em coluna que a política deixa agrupar e que não seja texto longo (texto longo vem cortado do servidor em 400 caracteres: só se lê);
- uma consulta por vez em todo o computador (fila de uma): dois clientes abertos dividem a mesma trava e o segundo recebe `ocupado` por alguns segundos.

## Arquivos e configuração

Pasta de dados: `%LOCALAPPDATA%\dominio-mcp` (muda com `DOMINIO_MCP_HOME`).

| Caminho | O que é |
|---|---|
| `packs\<dsn>\` | O pack atual (SQLite, ≈ 33 MB no banco real). Fica só neste computador. Traz nomes e comentários do dicionário do Domínio: não copie para fora. |
| `audit\audit.jsonl` | Um evento por linha: ferramenta, hash dos argumentos, tabelas, linhas, truncado, latência, custo estimado, versão do pack. Nunca valor de linha. Gira a cada 5 MB, 5 arquivos. |
| `state\` | Trava entre processos, orçamento de frequência e quarentena. |
| `config.toml` | Configuração opcional (abaixo). |

`config.toml` (qualquer chave desconhecida, tipo errado ou limite acima do teto é erro, nunca ignorado em silêncio):

```toml
dsn = "contabil"                 # só o nome do DSN de sistema, nunca usuário nem senha
allow_pii = []                   # cpf, folha, endereco, contato, bancario, nascimento, nome, documento
raw_sql = false                  # só tem efeito no perfil local, e o L3 ainda não existe

[limits]
default_rows = 50
max_rows = 500
executions_per_minute = 20
```

Variáveis de ambiente (vencem o arquivo): `DOMINIO_MCP_DSN`, `DOMINIO_MCP_ALLOW_PII` (separada por vírgula), `DOMINIO_MCP_RAW_SQL`, `DOMINIO_MCP_HOME`, `DOMINIO_MCP_CONFIG`. O perfil só vem de `serve --profile`.

## Manutenção

- **Atualizou o Domínio ou mudou a estrutura do banco:** a ferramenta devolve `pack_desatualizado`. Rode `build-pack`; coluna nova fica bloqueada até novo aceite.
- **Mudou a política ou o overlay** (atualização deste pacote): o `doctor` mostra `DESATUALIZADO`; rode `build-pack`.
- **Pack ausente ou ilegível:** `build-pack`.
- `dominio-mcp doctor` não imprime credencial nem valor de linha. Ele mostra o caminho da pasta de dados, que traz o nome do usuário do Windows: tire antes de colar em chamado.

## Problemas comuns

| O que aparece | Causa | O que fazer |
|---|---|---|
| `pack_ausente` ou `pack_desatualizado` | Sem pack, ou o banco, a política ou o overlay mudaram | `build-pack` (e decidir o aceite de novo, se houver coluna nova) |
| `coluna_bloqueada` ou `tabela_bloqueada` | Classe bloqueada, view não aprovada, sem aceite, ou uso que a classe não permite (filtro em texto livre, `distinto` em documento) | `descrever_tabela` mostra o motivo por coluna; liberar só categoria pessoal ou aceite, por decisão do dono |
| `juncao_bloqueada`, `juncao_multiplicadora`, `agregacao_multiplicada`, `coluna_longa` | Junção por chave que a política não libera, junção que multiplicaria as linhas, agregado do lado "um" da junção, ou texto longo usado para agrupar ou ordenar | Juntar de uma tabela de cada vez; agregar a coluna da tabela filha; só ler o texto longo |
| `sem_filtro_de_empresa`, `sem_janela_de_datas`, `janela_de_datas_longa` | Regra de escopo da tabela grande | Filtrar por `codi_emp` e por período de até 13 meses numa data da tabela grande |
| `resposta_grande_demais` | Rede de segurança dos 12 KB (não deveria aparecer) | Pedir menos colunas ou linhas e avisar quem mantém o pacote |
| `custo_estimado_alto` ou `linhas_estimadas_demais` | O banco estimou a consulta acima do orçamento | Estreitar filtro e período |
| `ocupado` | Outra consulta em andamento neste computador | Tentar de novo em alguns segundos |
| `limite_de_frequencia` | Passou de 20 consultas por minuto | Esperar `tente_em_s` |
| `tempo_esgotado` | Passou de 30 s e foi cancelada | Estreitar filtro |
| `execucao_incerta` ou `quarentena` | O cancelamento não foi confirmado pelo servidor; o programa para de executar até confirmar | Conferir no servidor do Domínio que nenhuma consulta antiga segue rodando e rodar `dominio-mcp reset`. Se a pasta de dados estava sem permissão de escrita e a quarentena só ficou em memória, o `reset` não alcança o processo vivo: feche o cliente e abra de novo |
| `odbc_indisponivel` | `pyodbc` ou o driver não carregaram | `doctor`; conferir Python de 64 bits e o DSN de sistema de 64 bits |
| `erro_do_banco` | O banco recusou a consulta (SQLSTATE e código nativo vão no detalhe) | Procurar o código; se for permissão, o usuário do DSN não lê o objeto |
| `ferramenta_desligada` | Dependência da rotina sumiu ou ficou mais restrita no pack novo | A mensagem traz o motivo; `build-pack` e reavaliar |
| `erro_interno` | Falha inesperada do programa | Ver `audit.jsonl` e o stderr do servidor |
| Cliente não lista a ferramenta | Claude Desktop não foi fechado por completo, ou `uv` fora do PATH | Reabrir por completo; caminho completo do `uv`; ver `mcp-server-dominio.log` |

## Pendências e limites da prova

Provado em 21/11/2026 contra o banco real, somente leitura: pack em cerca de 21 a 33 s (4.964 objetos, 18 ilegíveis), frescor sem falso positivo, cancelamento de consulta em cerca de 2 s com confirmação no servidor, L1 e L2 no banco real, `movimento_fiscal` igual a uma consulta L2 independente, `conferir_numeracao` sem falsa lacuna em faixas sobrepostas (linhas sintéticas no servidor real) e nenhum marcador de segredo em nenhuma saída (teste com valores plantados). Relatórios em [`dominio-mcp/reports/`](../dominio-mcp/reports/progresso.md).

Revisão adversarial do código pelo Codex (somente leitura), em duas rodadas: 18 achados, todos reproduzidos por teste que falhava e corrigidos (D-328). A rodada 2 foi a última prevista; o veredito de uma terceira leitura é do dono decidir pedir. Fica sem prova dinâmica a corrida real entre dois processos no Windows e a recuperação depois da queda do processo.

Ainda **não** provado:

- **Clientes reais** (Claude Desktop, Claude Code, ChatGPT): matriz marcada "pendente de teste real".
- **Recuperação do esquema (A3):** no conjunto cego v2, 91% no top-5 e 50% no top-1; a meta de top-1 é 70%. Falta o lote de perguntas da contadora ([reports/recall.md](../dominio-mcp/reports/recall.md)).
- **Carga no servidor do Domínio (A11, T4.9):** limites provisórios; falta o ensaio em janela autorizada.
- **Revisão independente de 300 colunas (A7c)** e **conferência de `movimento_fiscal` contra o relatório oficial do Domínio:** dependem da contadora.
- **Aceite do catálogo:** decisão do dono, ainda não tomada no banco real.
- **Planos do ChatGPT e custo do túnel:** a página oficial não os fixa.

## O que não existe nesta fase

- Escrita no Domínio (nunca).
- SQL livre (L3), HTTP em `127.0.0.1` e extensão `.mcpb` para Claude Desktop (Fase 1b, cada incremento com OK próprio).
- Gateway no CICA, OAuth, repasse pelo agente e API do Serpro (Fase 2, com spec própria e custo a confirmar antes de qualquer chamada paga).

## Fontes

Lidas em 21/11/2026: [Connect to local MCP servers](https://modelcontextprotocol.io/docs/develop/connect-local-servers) (caminho do `claude_desktop_config.json`, formato do JSON, reinício e logs), [Claude Code MCP](https://code.claude.com/docs/en/mcp) (`claude mcp add`, `--`, escopo padrão `local`), [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) (pré-requisitos, `tunnel-client`, limites). As demais referências estão na [spec](specs/dominio-mcp.md) e em [pesquisa/dominio-mcp-pesquisa-externa.md](pesquisa/dominio-mcp-pesquisa-externa.md).
