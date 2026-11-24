# Spec — MCP do Domínio (`dominio-mcp`) (21/11/2026, revisada após a crítica do Codex)

Plano de execução e triagem da crítica: [dominio-mcp-plano.md](dominio-mcp-plano.md). Fase 2: [dominio-mcp-fase2.md](dominio-mcp-fase2.md). Mapa do banco: [../dominio-banco-mapa.md](../dominio-banco-mapa.md). Pesquisa externa: [Domínio e IAs](../pesquisa/dominio-mcp-pesquisa-externa.md) e [Serpro](../pesquisa/serpro-integra-contador-mcp.md). Evidência bruta das medições (só metadados): [evidencia-banco-2026-11-21/](../pesquisa/evidencia-banco-2026-11-21/00-LEIA-ME.txt), citada abaixo como E01 a E11. Base existente: [intelligence-mcp.md](../intelligence-mcp.md), D-18, etapas 03, 05 e 08 do [plano mestre](../../PLANO-MESTRE.md).

Os rótulos **DM-n** correspondem a **D-317 a D-327** em `DECISOES.md`, registrados em 21/11/2026 depois do OK do responsável (T0.0), antes de qualquer implementação.

## Problema

O dono do escritório não consegue usar Claude, ChatGPT nem o Copiloto sobre o banco do Domínio:

- O banco tem **4.964 objetos do dono `bethadba` e 58,7 mil colunas** com nomes crípticos (`vcon_sai`, `dsai_sai`, `cdeb_lan`). Uma IA sem mapa inventa tabela e código, e o dicionário despejado no contexto não cabe.
- O usuário **Externo lê quase tudo**: 4.946 dos 4.964 objetos, inclusive colunas de senha e token (83 por heurística) e folha por empregado (E03, E04). Dar ODBC cru a uma IA expõe isso.
- A D-18 (`DECISOES.md:40`) recusa SQL, DSN e credenciais no argumento de ferramenta; `docs/intelligence-mcp.md:20` acrescenta nome de tabela e DDL. O MCP interno do Hub (`apps/intelligence/mcp.py`) só devolve cartões do catálogo do Hub, não é endpoint externo e não consulta o banco.
- Existem MCPs de terceiros para o Domínio, mas nenhum junta mapa do banco gerado do próprio catálogo, camadas seguras, Serpro e o CICA (pesquisa, parte B).

## Objetivo

Um MCP **somente leitura** do Domínio que: (1) ensina o banco à IA sem estourar contexto e sem inventar nome ou código; (2) responde com número rastreável (tabela, filtro, consulta, hora da leitura); (3) roda no escritório, para o dono ligar no próprio Claude ou ChatGPT; (4) numa segunda fase, entra no CICA (gateway com OAuth, repasse pelo agente, Serpro).

## O que já existe (não duplicar)

| Peça | Estado | Como esta spec a usa |
|---|---|---|
| `apps/intelligence/mcp.py` | JSON-RPC interno, 8 ferramentas, cartões; sem ODBC; "futuro transporte externo deve usar OAuth com resource indicators" | Fase 2 estende; esta fase não o altera |
| `intelligence/connectors.py` | `QUERY_REGISTRY` de 4 consultas; descoberta só de nomes e tipos | O pack guarda muito mais (comentários, FKs, índices, views) |
| `intelligence/package_governance.py` | Pacote semântico só com objeto e coluna aprovados no catálogo | Mesma ideia: consulta verificada depende de objeto que existe no pack |
| `agent/` e `agent-windows/` | Só saída, só consultas fixas, sem SQL remoto | Fase 2 repassa consulta estruturada com contrato próprio, nunca SQL |
| `apps/integra/catalog.py` | Registro fechado de serviços Serpro | Fase 2 usa um subconjunto allowlist |
| `contracts/datasets/*.sql` | SQL validado no banco real (empresas, regime, UF da contraparte, honorários) | Semente das consultas verificadas |

## Fatos medidos no banco real (21/11/2026, somente leitura, sem imprimir dado de negócio)

Cada número tem a saída bruta em `evidencia-banco-2026-11-21/`. Item sem coluna de evidência é de terceiro e está marcado.

| Fato | Valor | Evidência |
|---|---|---|
| Servidor | SQL Anywhere 17.0.11.7312, banco `contabil`, charset windows-1252; DSN de sistema 64 bits `contabil` com o usuário `EXTERNO` embutido | E09 |
| Objetos de `bethadba` | 4.964 (4.862 tabelas base, 102 views); **4.946 legíveis**, 18 negados, medido com `SELECT … WHERE 1=0` e controle de objeto sabidamente negado | E03, E07 |
| Dicionário embutido | Em objetos de usuário de todos os donos: 58.745 colunas, **54.472 comentadas (92,7%)**; 4.860 comentários de tabela; 61.250 linhas em `SYS.SYSREMARK` | E07 |
| Estrutura declarada | 4.821 chaves primárias, **6.803 chaves estrangeiras** (6.955 linhas no catálogo inteiro), 12.768 índices; ex.: `IDX_DATA_SAI (codi_emp, dsai_sai)` em `efsaidas` | E07, E08 |
| Chave de empresa | `codi_emp` em 3.879 das 4.862 tabelas base | E04 |
| Legendas e obsolescência | 1.711 colunas com 2 ou mais pares "código - rótulo"; 54 colunas e 5 tabelas marcadas como não usadas | E04 |
| Sensíveis (**heurística** sobre nome e comentário, não inventário) | segredo 83, CPF 170, salário 597, endereço 187, contato 124, bancário 80, nome de pessoa 14, identidade ou nascimento 862 (com falsos positivos); terceiros citam 79 tabelas com senha ou token em texto | E04 + pesquisa |
| Módulos (base ∩ legível) | `ef` 2.732, `fo` 745, `ge` 397, `ct` 389, `hr` 147, `lr` 129 | E10 |
| Volume | Uma empresa concentra 283.871 das cerca de 386.290 notas de saída (estimativa do catálogo); leitura inteira com `fetchmany(500)` em 0,47 s e 0,66 s (duas execuções) | E01, E10 |
| Timeout ODBC | `SQL_ATTR_QUERY_TIMEOUT` recusado (`HYC00`); **`cursor.cancel()` por outra thread interrompe em 3,0 s** (`-299`) e a conexão segue usável; `cancel()` em cursor já fechado só levanta `ProgrammingError`, sem afetar cursor novo | E01, E11 |
| Estimativa de custo | **`PLAN('…')` devolve `Estimated cost` e `Estimated rows` em 2 a 19 ms sem executar a consulta**, também com o SQL interno como **parâmetro ligado** (`SELECT PLAN(?)`), para o Externo. Uma auto-junção de 917 mil linhas deu custo estimado 2,35e+06 contra 2,59 de uma agregação indexada (linhas estimadas 1, porque o resultado é uma linha): **o custo é o sinal principal** | E11, E12 |
| Frescor do catálogo | Contagem de 6 visões de catálogo e soma do tamanho das definições de view em 25 a 54 ms (medições pontuais, não custo típico). **`MAX(last_modified_at)` não serve de sinal**: passou de 14:00 para 18:00 no mesmo dia com as seis contagens iguais (atualização periódica de estatística, sem DDL) | E11, E13 |
| Conexões visíveis | `sa_conn_info()` é acessível ao Externo (78 linhas, com `Number`, `LastReqTime` e `ReqType`): permite confirmar que uma conexão descartada realmente terminou | E12 |
| Modo somente leitura do ODBC | Atributo aceito, eficácia não verificada: não é defesa | E01 |
| Sessão | `SET TEMPORARY OPTION isolation_level = 0` aceito; `TOP n START AT m` funciona | E01 |
| Acentos | Por ponto de código: a conexão padrão entrega `U+00E7 U+00E3`; **`CharSet=UTF-8` com decodificação cp1252 gera `U+00C3 U+00A7` ("Ã§")**. A tela do terminal desenha o caractere de substituição (`U+FFFD`) mesmo com o dado certo, então nunca se julga acento pelo que aparece | E02 |
| `sqlglot` | Não entende `CURRENT DATE` nem `START AT` e não tem dialeto Sybase: não serve de guarda | E06 |
| Recuperação de esquema (protótipo, 26 perguntas) | Busca lexical ingênua: top-5 em 4/26 (15%). Com sinais do próprio banco: top-5 **21/26 (81%)** e top-1 **15/26 (58%)**. As 26 perguntas foram usadas para escolher as variantes: são conjunto de desenvolvimento, não prova | E05 |

## Desenho

### Camadas de acesso (DM-1, decidida pelo responsável em 21/11/2026)

| Camada | O que é | Canais | Fase |
|---|---|---|---|
| L0 conhecimento | `mapa_do_banco`, `buscar_esquema`, `descrever_tabela`, `caminho_entre_tabelas`, `valores_do_campo` | todos | 1 |
| L1 negócio | Ferramentas fixas com SQL versionado, parametrizado e conferido no banco real | todos | 1 |
| L2 estruturada | JSON (tabela, colunas, filtros, agrupamento, agregação, junção por FK declarada) validado contra o catálogo e compilado para SQL com `?` | todos, inclusive CICA e conectores web | 1 |
| L3 SQL cru | Gramática mínima aceita (um `SELECT`, sem CTE, subconsulta nem `UNION`), qualquer construção não reconhecida é recusada | **só o perfil `local`**, desligado por padrão | **1b** |

A D-18 continua valendo para o MCP interno do Hub e para o agente ("o agente não recebe SQL remoto"). Na Fase 2 o agente recebe consulta estruturada, com contrato próprio (versão, esquema e hash), e a compila contra o pack local: nunca SQL.

**Perfis (DM-10).** `serve --profile remote` é o **padrão** e vale para HTTP, túnel e gateway: nunca registra nem despacha L3, qualquer que seja a configuração. `--profile local` mais `raw_sql = true` só em processo stdio iniciado pelo cliente local; a checagem é feita no despacho, não só na descoberta. O túnel da OpenAI alcança "stdio or HTTP" e pode apontar para o mesmo comando: o guia manda usar `--profile remote` nele.

### Conhecimento do banco (DM-2)

1. **Pack por escritório**, gerado do catálogo vivo (`SYS.SYSTAB`, `SYSTABCOL`, `SYSREMARK`, `SYSIDX`, `SYSIDXCOL`, `SYSFKEY`, `SYSVIEW`) em `%LOCALAPPDATA%\dominio-mcp\`. Fica fora do git e não é redistribuído (o dicionário é texto da Thomson Reuters e cada escritório o gera do próprio banco).
2. **Versão composta** do pack: hash da estrutura (objetos, colunas, tipos, larguras, PK, FK, índices), das definições de view, dos comentários, da política e do overlay. Antes de executar, uma sonda barata compara as contagens do catálogo e a soma do tamanho das definições de view (`MAX(last_modified_at)` foi descartado: anda sem DDL, E13) se a última tem mais de 60 s; o re-hash completo roda ao iniciar e **a cada 1 h**. Divergência marca o pack como **desatualizado** e L1 e L2 recusam até `build-pack`; a troca do arquivo é atômica. **View não é consultável em L2** até ser aprovada no overlay por nome e hash da definição (hash mudou, volta a bloqueada); segue descritível em L0. Limite conhecido: contagem igual com conteúdo diferente só é pega no re-hash completo (até 1 h), por isso nada novo nasce autorizado (coluna nova e view nova ficam bloqueadas).
3. **Overlay curado**, versionado no git: glossário PT-BR (faturamento, compras, regime, honorários…) para tabelas e colunas, módulos, tabelas centrais, legendas confirmadas com nível de confiança, regras de qualidade de dado e consultas verificadas. Só nomes técnicos e frases próprias, sem copiar o dicionário.
4. **Recuperação híbrida**: SQLite FTS5 (BM25 sobre nome, comentário e colunas) + trigramas do nome + sinônimos do glossário + prior estrutural (FKs que apontam, volume, tabela-pai × filhas, nome curto). Sem embeddings na v1 (DM-8).
5. **Contra invenção**: toda descrição volta com `fonte` (comentário do banco, overlay verificado, inferido) e `confianca`; legenda não confirmada vem marcada; campo "não utilizado" e tabela obsoleta saem com aviso e perdem posição; `situacao_*` leva o aviso de que o comentário do banco está errado (a legenda oficial está no leiaute de importação, Central 672).
6. **Contra estouro de contexto**: `mapa_do_banco` cabe em 3 KB; `buscar_esquema` devolve até 8 cartões de cerca de 250 caracteres; `descrever_tabela` mostra colunas-chave primeiro e pagina o resto (a `EFPARAMETRO_VIGENCIA` tem 657 colunas); toda saída ≤ 12 KB, com `truncado` e `proximo_passo`.

### Segurança e privacidade (DM-3, DM-6, DM-7, DM-11)

- **Independente do banco.** O Externo lê quase tudo, então a lista de bloqueio é do MCP. Tabelas de credencial conhecidas (`gecertificadosdigitais`, `geapuracao_assistida_credenciais`, `fodarf_dctfweb_api_tokens_requisicao`, `efdas_api_tokens_requisicao`, `geconfiguracao_envio_email_parametros`, `gesenhainternethist`, `syslicacao`, `gesecusuarios`…) e colunas por regra (senha, password, pwd, token, secret, segredo, credencial, private, certificado, frase_secreta) **nunca** saem em nenhuma camada, nem em erro, recurso ou auditoria. `SELECT *` é recusado em tabela com coluna bloqueada. Os tokens da API do Serpro que o próprio Domínio guarda estão nessa lista.
- **Classes**: segredo, documento, pessoal (CPF, folha por empregado, endereço, contato, conta bancária, nascimento), texto livre, normal e **não classificada**. Coluna não classificada, ou nova desde o último pack, fica **bloqueada em L2** até `build-pack --aceitar`. Texto livre de tabela de auditoria e de log (`au*`, `*LOG*`, `audados`, `GEATENDIMENTO*`) é bloqueado por padrão.
- **Documento** (`cgce_*`, CPF, inscrição): pode guardar CPF (`tins_emp = 2` é CPF) ou valor fora do padrão. **Só passa inteiro um CNPJ válido** (14 dígitos com dígito verificador); todo o resto (11 dígitos, outros tamanhos, formato estranho) sai mascarado (`123.***.***-45` para CPF, `***` para o restante) salvo `allow_pii` com `documento`. Pode ser selecionado (mascarado) e filtrado só por igualdade ou `in` com CNPJ válido; **nunca** agrupado, ordenado nem agregado. Em texto livre a máscara por padrão de valor (CPF, e-mail, telefone) é aplicada na moldagem da saída: heurística, não garantia.
- **Origem antes da autorização.** Alias, junção, ordenação e agrupamento são resolvidos até a coluna de origem; a classe vai junto. Selecionar, filtrar e agregar são permissões separadas. Coluna pessoal **nunca** entra em filtro (sem oráculo) e, com `allow_pii`, só sai mascarada; agregação sobre coluna pessoal suprime grupos com menos de 3 contribuições não nulas por expressão, contadas como **pessoas distintas** quando a tabela tem `i_empregados` (D-328, D-329). O corte vale por consulta: duas consultas que diferem por uma pessoa permitem subtração, limite declarado (D-329). **Limite da promessa**: com `allow_pii` ligado o dono aceita que o provedor da IA veja esse dado.
- **Texto livre só se lê (D-328).** Sem nenhum operador de filtro: `contains` e `prefix` confirmariam por contagem o que a máscara esconde (CPF pontuado, janelas curtas de dígitos, o curinga `[` do `LIKE` no SQL Anywhere). Texto de tabela por empregado é `pessoal/folha`. Texto longo vem cortado do servidor em 400 caracteres e não agrupa, ordena nem entra em `distinto`.
- **Mitigação, não garantia**: truncar célula a 200 caracteres, listar `texto_livre` e instruir o modelo a tratar linhas como dado reduzem a injeção de prompt, mas não a impedem.
- **Escopo e custo (DM-11).** Tabela com `codi_emp` e mais de 50 mil linhas exige filtro de empresa; janela de datas ≤ 13 meses em tabela grande; no máximo 2 junções, só por chave `normal` e sem multiplicar linhas (D-328). **Admissão por custo**: antes de executar L1 ou L2 roda `SELECT PLAN(?)` com o SQL interno como **parâmetro ligado** (sem aninhar aspas) e recusa se `Estimated cost` (principal) ou `Estimated rows` passam do orçamento. O SQL interno sai só do compilador, com literais de codificação tipada (inteiro, data ISO, texto com aspas duplicadas) testada com entrada adversarial; se um valor não puder ser codificado com segurança, recusa a estimativa **e** a execução; a resposta do `PLAN` é validada antes de ser lida. O orçamento nasce de critérios registrados antes do ensaio (T4.9). **Trava entre processos** por DSN (um cliente stdio e outro não executam juntos), fila de 1 e orçamento de frequência. `TOP` limita saída, não trabalho: por isso a admissão olha o plano.
- **Execução.** Um cursor por execução; o vigia está preso a ele e engole e audita a exceção do `cancel()`. Se o cancelamento não for confirmado em 10 s, a conexão é descartada e o serviço entra em **quarentena compartilhada por DSN** (arquivo de estado ao lado da trava, que sobrevive à queda do processo): **nenhum processo admite nova execução enquanto o término da anterior for incerto**. A saída é a confirmação de término (a conexão descartada some de `sa_conn_info()` ou seu `ReqType` deixa de ser consulta em andamento, lido por conexão nova) ou `dominio-mcp reset` explícito; expirar um prazo sozinho não libera. **O limite de 30 s é alvo, não garantia absoluta.** Padrão do servidor: 50 linhas, no máximo 500 (2.000 agregadas), 40 colunas, resposta ≤ 12 KB, `isolation_level = 0`.
- **Consistência.** A leitura sem confirmação pode ver alteração que será desfeita e combinar cabeçalho e itens de um lançamento em andamento. Todo resultado leva `consistencia: leitura_nao_confirmada` e `lido_em`; número fiscal é diagnóstico a conferir contra relatório do Domínio, não apuração.
- **Auditoria** em JSONL local (ferramenta, hash dos argumentos, tabelas, linhas, truncado, latência, política aplicada, versão do pack). Sem valor de linha.
- **Anotações são dica, não autorização.** Toda ferramenta traz `readOnlyHint: true`, `destructiveHint: false`, `openWorldHint: false`. A documentação da OpenAI diz que o ChatGPT trata como escrita a ferramenta sem a dica e pede que os primeiros 512 caracteres de `instructions` sejam autocontidos; a autorização real é a do despacho.

### Entrega

**Fase 1 (núcleo, esta spec): `dominio-mcp` por stdio.** Pacote Python no repo (`dominio-mcp/`), SDK oficial `mcp` 1.29 (protocolo até 2025-11-25; a revisão 2026-07-28 removeu sessões e `initialize`, acompanhar o SDK). L0, quatro ferramentas L1 e L2.

| Cliente | Como conecta | Fonte |
|---|---|---|
| Claude Desktop | `claude_desktop_config.json` com `uv run … dominio-mcp serve` (stdio) | claude.com/docs/connectors/custom/add-unlisted |
| Claude Code | `claude mcp add` | — |
| ChatGPT (web) | **Secure MCP Tunnel**: `tunnel-client` no escritório, só saída HTTPS, repassa a stdio ou HTTP local (`--profile remote`); exige conta de Plataforma e permissão de workspace, planos a confirmar | developers.openai.com/api/docs/guides/secure-mcp-tunnels |
| Claude web e celular | URL pública com OAuth: só pelo gateway da Fase 2 (o túnel do Claude é Enterprise, por pedido) | claude.com/docs/connectors/mcp-tunnels |

**Fase 1b (feita em 23/11/2026 por autorização do responsável, D-330; `.mcpb` falta o teste manual no Claude Desktop):** L3 no perfil `local`, como SQL traduzido para L2 (`rawsql.py`); HTTP em `127.0.0.1` com token e checagem de `Origin`; extensão `.mcpb` para Claude Desktop (dados do pacote por `importlib.resources`; prova de instalação em ambiente limpo fora do checkout).

**Fase 2 (spec própria): gateway no CICA.** Rascunho em [dominio-mcp-fase2.md](dominio-mcp-fase2.md). É a peça mais sensível de segurança: revisão adversarial obrigatória.

### Rotinas autônomas, somente leitura

Cada rotina é uma ferramenta L1 que devolve **achados estruturados**; o modelo explica e prioriza, não calcula imposto. Servem a Claude, ao ChatGPT e, na Fase 2, a tarefas agendadas do CICA.

| Rotina | O que verifica | Tabelas (existem no catálogo medido) | Fase |
|---|---|---|---|
| `empresas` | Carteira, situação decodificada (A/I/C/M/B/E) e regime vigente | `geempre`, `efparametro_vigencia` | 1 |
| `empresa_perfil` | Cadastro sem dado pessoal, módulos usados, volumes dos últimos 12 meses | `geempre`, `efsaidas`, `efentradas`, `efservicos`, `ctlancto` | 1 |
| `movimento_fiscal` | Totais mensais de entradas, saídas e serviços; exclui canceladas; trata o segmento da nota | `efsaidas`, `efentradas`, `efservicos` | 1 |
| `conferir_numeracao` | Lacunas e duplicidades por espécie e série | `efsaidas`, `efentradas` | 1 |
| Reserva | balancete e razão; extrato bancário sem lançamento; guias de folha sem pagamento; honorários em aberto; empresas sem movimento; nota sem acumulador; vigência de regime futura | `ctlancto`, `ctcontas`, `ctextrato_bancario_lancamento_item`, `FOVGUIAINSS`, `HR*`, `EFPARAMETRO_VIGENCIA` | depois |
| Cruzadas com o Serpro | faturamento × PGDAS-D (começa pelo índice: declarou, DAS pago, malha); débitos do SITFIS × guias; mensagens DTE; situação cadastral do fornecedor; DCTFWeb × folha; MIT; parcelamentos; vigência da procuração | Domínio + Integra Contador | 2 |

### Serpro (Fase 2): o que a pesquisa fixa

- **Allowlist por `idServico`**, nunca por tipo (68 serviços somente consulta; `MSGDETALHAMENTO62` é "Consultar" mas registra ciência legal; `ATUBENEFICIO23` é "Emitir" e grava). Lista em [Serpro, apêndice A](../pesquisa/serpro-integra-contador-mcp.md). `apps/integra/catalog.py` já é registro fechado: o gateway usa um subconjunto dele.
- **Custo**: 200, 202 e 403 são cobrados; consulta de R$ 0,24 a R$ 0,06 por faixa. Checar procuração antes (403 cobra), usar o evento gratuito para decidir se vale consultar, teto por tenant e por conversa, nunca laço de modelo. Qualquer chamada paga precisa do seu OK (regra de custo).
- **Formato**: declaração PGDAS-D, DEFIS, SITFIS e DCTFWeb completa voltam em PDF; o índice JSON já responde "declarou, pagou, está em malha". Parser de PDF só com amostra real.
- **Termos**: o contrato do Integra Contador não é público; repasse a LLM de terceiros e persistência de resposta estão em aberto. Contexto mínimo (achados, não documentos), persistir só índices e resultados.
- **Procuração** é por cliente e manual (IN RFB 2.320/2026, art. 13 veda automação para outorgar).

## Critérios de aceitação (Fase 1, núcleo)

| # | Critério | Prova |
|---|---|---|
| A1 | `dominio-mcp doctor` verifica DSN, driver, versão e legibilidade e nunca imprime segredo ou valor de linha | execução no banco real + teste de saída |
| A2 | `build-pack` gera o pack real em ≤ 5 min e ≤ 100 MB; a versão composta muda ao mudar coluna, FK, índice, definição de view, comentário, política ou overlay; pack desatualizado bloqueia L1 e L2 e a troca é atômica | execução real + testes com catálogo falso |
| A3 | Recuperação **cega**: ≥ 40 perguntas novas, independentes das 26 de desenvolvimento, **estratificadas por módulo e família de intenção**, congeladas por hash antes do ajuste (≥ 100 no total); relevância = conjunto de tabelas aceitas; **recall@5 ≥ 90% e recall@1 ≥ 70% no conjunto cego** (objetivo, não previsão). O cego é medido **uma vez por versão do overlay**: se falhar, o ajuste usa só o desenvolvimento e o lote fica queimado, substituído por outro independente de ≥ 20 perguntas; toda medição é registrada (data, versão do overlay, resultado). Dev e cego reportados separados | `pytest -m eval` |
| A4 | Nenhuma ferramenta passa de 12 KB, nem `descrever_tabela` da tabela de 657 colunas | teste de propriedade |
| A5 | **(Fase 1b)** L3: gramática mínima; suíte de ataque (≥ 60 casos: DML, DDL, `CALL`, `INTO`, `;`, comentário, string, `UNION`, CTE que sombreia tabela, alias de coluna bloqueada, identificador entre aspas, view que encapsula origem bloqueada, unicode) **100% recusados**, mais consultas legítimas que **precisam passar** | `pytest tests/test_rawsql_attack.py` |
| A6 | L2 recusa coluna ou tabela fora do catálogo ou não classificada, junção sem FK declarada, filtro em coluna pessoal, função fora da lista, alias que renomeia coluna bloqueada, `ORDER BY` e `GROUP BY` sensíveis, coluna sensível alcançada pela segunda tabela de uma FK | testes do compilador com fixtures |
| A7 | Privacidade em três provas: (a) catálogo sintético com marcadores plantados (segredo em `audados.valor`, CPF em observação, view com coluna `conteudo`, coluna nova não classificada) e **nenhum marcador aparece em nenhuma saída**, inclusive erro, recurso e auditoria; (b) no catálogo real, cada objeto legível ou é aceito só com colunas permitidas ou é **recusado com motivo**, com a contagem de recusas; (c) amostra estratificada de 300 colunas (segredo, documento, pessoal, texto livre, normal) rotulada por duas revisões independentes, com falso-negativo medido **por classe**: segredo = 0 e pessoal abaixo de 2%, com a contagem; o que ficar fora da amostra é o limite declarado da promessa; mais teste de que CPF, e-mail e telefone dentro de texto livre saem mascarados por padrão de valor | testes + relatório |
| A8 | Execução: cancelamento atrasado não atinge a consulta seguinte (ODBC falso com barreira); `cancel()` que falha ou trava por mais de 60 s mantém a quarentena e **nenhum de dois processos admite nova execução** (driver falso); só a confirmação de término (`sa_conn_info()`) ou `reset` libera, inclusive após queda do processo; consulta lenta real é cancelada em ≤ 31 s e a conexão segue utilizável. **Sem promessa de limite absoluto** | testes + teste vivo com `WAITFOR` |
| A9 | L1 `empresas`, `empresa_perfil`, `movimento_fiscal`, `conferir_numeracao`: contrato com ODBC falso, conferência viva contra consulta independente do L2, `consistencia` e `lido_em` presentes | testes + relatório |
| A10 | Auditoria sem valor de linha; perfil `remote` nunca registra nem despacha L3; `tools/list` determinístico; todas as ferramentas com as três anotações | testes de contrato e e2e stdio |
| A11 | Carga: `PLAN(?)` recusa o que passa do orçamento; trava entre processos (dois processos não executam juntos); **critérios registrados antes do ensaio** em `reports/carga.md`: sonda de interferência (consulta indexada trivial em outra conexão durante a pesada) com p95 ≤ 2× a linha de base e ≤ 250 ms, e tabela **estimado × real** de ≥ 10 consultas para fixar o orçamento com fator de segurança; medido **em janela autorizada pelo dono** | testes + relatório |
| A12 | Guia para Claude Desktop, Claude Code e ChatGPT (túnel) e **matriz real por cliente** (inicialização, descoberta, execução, confirmação, resposta truncada, reconexão), marcada "pendente de teste real" até ser rodada; **o guia declara compatibilidade só para cliente com linha "testado em <data e versão>"**, os demais ficam "não testado" | revisão do guia + `reports/clientes.md` |
| A13 | Nenhum arquivo de código do legado alterado (os únicos acréscimos fora de `dominio-mcp/` e `docs/` são os registros de T0.0 e T8.3); `ruff`, `mypy` e `pytest` do pacote verdes; portão do repo sem regressão | saída dos comandos |

## Fora de escopo

Escrita no Domínio (nunca). Domínio Web (a Central confirma que não há conexão direta). Gateway OAuth, repasse pelo agente e Serpro (Fase 2). Embeddings (só se A3 falhar). Treino ou ajuste fino de modelo. Painel de interface. Assinatura de código do `.mcpb`. Leitura consistente por snapshot (exige opção do banco que só o administrador liga).

## Decisões

| ID | Decisão | Estado |
|---|---|---|
| DM-1 | Camadas L0/L1/L2 em todos os canais; L3 só no MCP local, desligado | **Decidida** pelo responsável (seletor, 21/11/2026); D-317 |
| DM-2 | Conhecimento gerado do catálogo do próprio escritório + overlay curado; pack fora do git, não redistribuído, com versão composta e troca atômica | Aprovada em 21/11/2026; D-318 |
| DM-3 | Bloqueio de segredo sempre; pessoal e não classificado bloqueados por padrão; liberação por categoria só pelo dono; origem resolvida antes de autorizar | Aprovada em 21/11/2026; D-319 |
| DM-4 | Fase 1 núcleo por stdio; Fase 1b com L3, HTTP e `.mcpb`; Fase 2 gateway CICA com spec própria | Aprovada em 21/11/2026 (o seletor de ordem foi interrompido; vale o plano); D-320 |
| DM-5 | Serpro só pelo gateway, allowlist por `idServico`, teto de custo, sem guia, declaração ou ciência | Aprovada em 21/11/2026 para a Fase 2, sem autorizar custo; D-321 |
| DM-6 | Execução com vigia e `cancel()`, um cursor por execução, quarentena compartilhada com saída por término confirmado, limite como alvo, `isolation_level = 0` com `consistencia` | Aprovada em 21/11/2026, medida; D-322 |
| DM-7 | Anotações como dica; saída ≤ 12 KB; até 16 ferramentas; ordem determinística | Aprovada em 21/11/2026; D-323 |
| DM-8 | Sem embeddings na v1; só se A3 falhar | Aprovada em 21/11/2026; D-324 |
| DM-9 | Distribuição: `uv`/JSON na Fase 1; `.mcpb` na 1b; ChatGPT por túnel; Claude web na Fase 2 | Aprovada em 21/11/2026; D-325 |
| DM-10 | Perfis `remote` (padrão) e `local`; L3 só em `local` com flag, checada no despacho | Aprovada em 21/11/2026; D-326 |
| DM-11 | Orçamento de carga por custo estimado (`SELECT PLAN(?)`, parâmetro ligado), trava entre processos, janela de datas e junções limitadas | Aprovada em 21/11/2026, medida; D-327 |
| DM-12 | Revisão adversarial do código: texto livre só se lê; junção só por chave normal e sem multiplicar linhas; agregado pessoal com 3 contribuições; execução presa ao pack da compilação; quarentena que não grava mantém a trava | Registrada em 21/11/2026 depois da revisão do Codex (duas rodadas, 18 achados); D-328 |
| DM-14 | Fase 1b: L3 é SQL traduzido para L2 (herda a política), HTTP só loopback com token, `.mcpb` só Windows x64 | Autorizada em 23/11/2026 ("faz tudo"); D-330 |

## Riscos

- **Usuário Externo amplo.** Mitigado por lista de bloqueio própria e classe "não classificada". Recomendação ao escritório: pedir ao Domínio um usuário dedicado com `GRANT SELECT` por coluna (o SQL Anywhere suporta).
- **Carga no servidor de produção.** `TOP` não limita trabalho: admissão por custo estimado (`PLAN`), trava entre processos, quarentena compartilhada e janela autorizada para calibrar. O cancelamento só foi provado com `WAITFOR`; consulta pesada real pode demorar mais, e a quarentena só libera com término confirmado.
- **Atualização do Domínio muda o esquema.** A versão composta invalida o pack; coluna nova nasce bloqueada.
- **Dados vão para o provedor da conta do dono** (Anthropic ou OpenAI). Por isso o padrão bloqueia pessoal; o guia diz o que sai.
- **Planos do ChatGPT e túnel.** A página oficial não fixa o plano que permite servidor MCP próprio nem o custo da conta de Plataforma; confirmar antes de prometer.
- **Segmento da nota.** `efsaidas` e `efentradas` têm uma linha por segmento; somar sem entender duplica ou divide. `movimento_fiscal` só vale depois de conferida contra um relatório do Domínio.
- **Legenda de `RFED_PAR`** não está no banco; o repo já mapeia por evidência. Vai para o overlay com confiança "inferida".
- **Compatibilidade com clientes** não está provada além do cliente do SDK; a matriz real (A12) fecha isso.

## Fontes

MCP: [changelog da revisão 2026-07-28](https://modelcontextprotocol.io/specification/latest/changelog), [autorização 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization). Claude: [conector por URL](https://claude.com/docs/connectors/custom/add-unlisted), [autenticação de conectores](https://claude.com/docs/connectors/building/authentication), [MCP tunnels](https://claude.com/docs/connectors/mcp-tunnels/overview), [MCPB](https://www.anthropic.com/engineering/desktop-extensions). OpenAI: [servidor MCP próprio](https://developers.openai.com/api/docs/guides/developer-mode) (`readOnlyHint` e 512 caracteres, lida em 21/11/2026), [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels). Referências de desenho (padrão, não código): [bytebase/dbhub](https://github.com/bytebase/dbhub) (MIT: `search_objects` em níveis, `readonly` e `max_rows`), [googleapis/mcp-toolbox](https://github.com/googleapis/mcp-toolbox) (Apache-2.0: ferramentas parametrizadas, sem `execute_sql` para IA de aplicação), [vanna-ai/vanna](https://github.com/vanna-ai/vanna) (MIT: recuperação de DDL, documentação e pares pergunta-SQL), [Canner/WrenAI](https://github.com/Canner/WrenAI) (AGPL: só estrutura; `get_context` troca esquema inteiro por recuperação acima de 30 mil caracteres), [compucel/dominio-ponte](https://github.com/compucel/dominio-ponte) (MIT, MCP do Domínio com guarda de SQL), [Lucas-Bueno04/REA_DOMINIO_DB](https://github.com/Lucas-Bueno04/REA_DOMINIO_DB) (sem licença: só estrutura). Banco: Central de Soluções do Domínio (3227 usuário Externo, 672 leiaute de importação, 2811 portas), [SAP SQL Anywhere 17](https://help.sap.com/docs/SAP_SQL_Anywhere). Serpro: [catálogo do Integra Contador](https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/catalogo_de_servicos/), [Loja Serpro](https://loja.serpro.gov.br/product/integracontador).
