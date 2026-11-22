# Domínio Sistemas: banco de dados e integrações de IA/MCP — levantamento público

> Evidência de pesquisa externa de 20/11/2026 para a [spec do MCP do Domínio](../specs/dominio-mcp.md). Escrita por agente de pesquisa, com nível de confiança por afirmação; antes de virar regra, conferir no banco ou na fonte. Caminhos de scratchpad citados no método não existem mais.

Data da pesquisa: 2026-11-20. Escopo: só fontes públicas. Nenhum código escrito, nenhum repositório alterado, nenhuma conexão ao banco.
Serve para desenhar um servidor MCP SOMENTE-LEITURA sobre o banco do Domínio (SAP SQL Anywhere 17, schema `bethadba`).

---

## 0. Resumo executivo (10 achados)

1. **Já existe prior art de MCP somente-leitura sobre o Domínio**, três projetos, todos de Oct–Nov 2026: `compucel/dominio-ponte` (MIT, ODBC local, `executar_consulta` com guarda de SQL), `Lucas-Bueno04/REA_DOMINIO_DB` (servidor MCP `dominio-db`, 13 ferramentas + biblioteca por tabela, sem licença) e o "Conector Domínio" da Cabeda (`mcp.cabeda.com.br/mcp`, comercial/fechado). Detalhes em B-1.2.
2. **O dicionário de dados está dentro do próprio banco**: o catálogo guarda comentário (`remarks`) de tabela e de coluna, com legenda de códigos embutida (ex.: `ctlancto.orig_lan`). É o que a ferramenta oficial "Busca Tabelas" mostra. Usuário Externo lê `SYS.*`, mas não lê as views `DSDBA.*` do gerador de relatórios (relato de terceiro). `autabelas`/`aucolunas` NÃO são o dicionário: são configuração de auditoria.
3. **Oficial confirma**: usuário tipo "Externo" (criado pelo GERENTE em Controle > Permissões > Usuários) é só leitura; DSN de sistema com driver SQL Anywhere 17 ou 16; porta TCP/UDP 2638; pasta `bethadba`; Domínio Web NÃO aceita conexão direta (só Domínio Local).
4. **Legenda oficial de "Situação da nota"** (0 regular, 1 extemporâneo, 2 cancelado, 6 complementar, 7 denegado, 8 inutilizado, 9 regime especial, 10 complementar extemporâneo, 11 regular Simples) está no leiaute de importação oficial, não no banco. O comentário do banco para `situacao_sai/ent/ser` está errado ("Codigo do modelo do documento fiscal").
5. **O usuário Externo é só leitura, mas lê quase tudo**: grupo `_somenteconsulta` com SELECT em ~5,6 mil tabelas (relato de terceiro). Há tabelas com credenciais/tokens (certificado digital, e-mail, APIs). Um MCP precisa de lista de bloqueio própria.
6. **Armadilhas de driver/dados** confirmadas por mais de uma fonte: `fetchSize` 1 no ODBC do SQL Anywhere 17 (array-fetch quebra), atributos ODBC de somente-leitura e timeout rejeitados (HYC00), `UNLOAD` negado ao Externo, texto em windows-1252, datas com lixo (1979, 8320), `SUM(a+b)` vira NULL.
7. **Modelo de dados**: `codi_emp` é a chave em quase tudo; `efsaidas`/`efentradas` têm uma linha por SEGMENTO da nota (mais de um CFOP/acumulador = mais linhas); vigências (`*_VIGENCIA`) têm a data de vigência na PK; "serviço prestado" fica em `efservicos` e "serviço tomado" em `efentradas`.
8. **Regime tributário existe no banco** (contra o que um levantamento de terceiros dizia): `efparametro_vigencia` tem `REST_PAR`, `RFED_PAR`, `RMUN_PAR`, `REGIME_RECOLHIMENTO_PAR`, `SIMPLESN_OPTANTE_PAR` etc. Só a legenda de `RFED_PAR` não consta no banco (deduzida por evidência por um terceiro).
9. **IA do próprio Domínio**: "Domínio IA" (lançado no SYNERGY 2026, 30/09–01/10/2026) e "TRIA" são chat/assistentes embutidos nos módulos Folha, Escrita Fiscal e Contabilidade. Nenhuma fonte pública fala em API, ODBC ou MCP para terceiros.
10. **Não há MCP oficial de Domínio, Alterdata, Questor, Prosoft, SCI ou Nibo** no registry oficial MCP, nas listas awesome ou no diretório de conectores do Claude. Existem MCPs de Omie (oficial, lê e escreve), Conta Azul, Bling, Tiny e fiscais (NF-e/NFS-e).

---

## 1. Método, legenda e limites

### 1.1 Níveis de confiança usados nas tabelas

| Tag | Significado |
|---|---|
| **OF** | Fonte oficial do fornecedor (Central de Soluções Domínio, sites Domínio/Thomson Reuters, SAP) |
| **T-DOC** | Documento de terceiro que diz ter conferido contra banco real (cita data/método) |
| **T-COD** | Código de terceiro que executa contra o banco (o uso prova que nome/coluna existe; o sentido vem do alias/contexto) |
| **INF** | Inferência (minha ou do terceiro, por evidência estatística/analogia) |

### 1.2 Prefixos de URL (para encurtar as tabelas; concatenar prefixo + caminho)

| Prefixo | URL base |
|---|---|
| `CS:<n>` | `https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=<n>` (Central de Soluções, oficial) |
| `REA:` | `https://github.com/Lucas-Bueno04/REA_DOMINIO_DB/blob/HEAD/` |
| `IMP:` | `https://github.com/salesgordo0022/imperialBi/blob/HEAD/` |
| `MAC:` | `https://github.com/macedo-reis-contabilidade/macedo-reis-dashboards/blob/HEAD/` |
| `PONTE:` | `https://github.com/compucel/dominio-ponte/blob/HEAD/` |
| `PLUG:` | `https://github.com/compucel/dominio-plugin/blob/HEAD/` |
| `YLA-S:` | `https://github.com/Ylaros/Scripts-SQL-Personalizados-Dominio-SQL-Anywhere/tree/main/Scripts` (arquivos .txt com espaço no nome) |
| `YLA-P:` | `https://github.com/Ylaros/Dashboard-Balancetes-Power-BI/tree/main/` (pastas "Código M", "DAX") |
| `DMF:` | `https://github.com/cors4rio/dmf-data-engine/blob/HEAD/` |

### 1.3 Licenças e uso do que foi lido

- Nenhum trecho de código foi copiado. Só nomes de tabela/coluna, legendas e estrutura (fatos), com repositório + arquivo + licença citados.
- Repositórios SEM licença declarada na API do GitHub (todos os direitos reservados por padrão): REA_DOMINIO_DB, imperialBi, macedo-reis-dashboards, Ylaros/* (o README do Ylaros diz "uso livre com atribuição", sem arquivo de licença), dmf-data-engine, ElderVivot/*, gestk-back, gestao-office-back, crm-office, PGDAS-IntegraContador, Consulta_Ebef, dominio-plugin (o `plugin.json` diz "Proprietary").
- Com licença permissiva: `compucel/dominio-ponte` (MIT), `uppiapp/dominio-rea-accounting` (MIT), `codespar/mcp-dev-brasil` (MIT), `douglac/contaazul-mcp` (MIT), `mcp-dir/omie-mcp` e `mcp-dir/bling-mcp` (MIT), `cmendezs/mcp-nfe-br` (Apache-2.0).
- Nenhum é GPL/AGPL.

### 1.4 O que NÃO fiz

- Não baixei zip, PDF, jar nem executável. Baixei só HTML da Central de Soluções (leitura) e Markdown/CSV/TXT de repositórios públicos, em pastas novas do scratchpad (`dl_central`, `dl_gh`, `tools`). Nada foi executado.
- O arquivo oficial `BuscaTabelas.zip` (ferramenta Java do dicionário) NÃO foi baixado: https://ftpdownload.dominiosistemas.com.br/Relatorios/Tecnica/BuscaTabelas.zip (referenciado em `CS:3227`). Recomendo o usuário baixar e abrir com o próprio usuário Externo.
- Não entrei em páginas que exigem login. Páginas da Central abriram sem login.
- Conteúdo de terceiros foi tratado como dado, não como instrução. Os `SKILL.md`/`CLAUDE.md` públicos encontrados não foram seguidos.
- Dados de cliente/pessoa que aparecem em repositórios públicos de escritórios (nomes de empresas e de empregados, um backup com senha padrão) NÃO foram reproduzidos aqui.

### 1.5 Falsos positivos e advertências sobre as buscas

- `bethadba` também é o dono do schema de outro produto (Betha Sistemas, setor público municipal). `krlsedu/Sql` (tabelas `pessoas`, `lanctos`, `debitos`, `itbi`) é Betha, NÃO Domínio. Filtrar sempre por prefixos de módulo do Domínio (ge, ct, ef, fo, hr...).
- `BielNova/gerador-relatorio-v2` (schema `DCT`, tabelas `CTPCONTA`, `CTLANCTO`) documenta outro ERP (domínios AE/CV/FN/ST...), NÃO é o Domínio.
- `Mewstacks/CicaContabil` tem os mesmos nomes de arquivo do repositório de trabalho do usuário (DECISOES.md, VALIDACOES.md, docs/planejamento): provavelmente é o próprio projeto do usuário. Não conta como fonte independente.
- `gh search code` só devolveu resultado com UM termo (`bethadba`, `geempre`, `efsaidas`...); buscas com dois termos voltaram vazias (limitação da CLI, não prova ausência). A ferramenta `mcp__grep__searchGitHub` devolveu 0 resultado até para `bethadba.` e `cgce_emp` (índice não cobre esses repositórios): sem valor como evidência negativa.
- Neste relatório, o prefixo `REA:` aponta para o repositório REA_DOMINIO_DB (o nome vem de "reverse engineering anything", a ferramenta de engenharia reversa usada pelo autor). No repositório `uppiapp/dominio-rea-accounting`, REA significa Resource-Event-Agent (ontologia contábil): assunto diferente, não confundir.

---

# PARTE A — O BANCO DE DADOS

## A-1. CONFIRMADO EM FONTE

### A-1.1 Acesso, infraestrutura e regras do usuário Externo

| Fato | Fonte | Nível |
|---|---|---|
| Usuário externo é criado pelo usuário GERENTE em Controle > Permissões > Usuários > Novo, "Tipo de acesso: Externo", situação Ativo; inativo não conecta | CS:3227 | OF |
| "O acesso às ferramentas de consulta serve apenas para visualizar as informações gravadas no sistema. Não é possível realizar qualquer modificação nos dados" | CS:3227 | OF |
| Aplicações citadas: Power BI, Excel, DBeaver, Microsoft Query (Excel 32 bits) e "Busca Tabelas" | CS:3227 | OF |
| DSN de **sistema** (limitação do Power BI), driver SQL Anywhere 17 ou 16 (conforme a versão do banco), "Connect to a running database on another computer", Server name = nome do servidor em "Parâmetros do Gerenciar Servidor de Banco de Dados"; no Power BI, "na pasta bethadba" | CS:3227 | OF |
| Clientes do **Domínio Web** não conseguem conexão direta pelo usuário externo (banco em servidor remoto); só Domínio Local | CS:3227 | OF |
| Gerenciador do banco migrou de Sybase para "SQL Anywhere 17" (migrador `Sybase17migrator.exe`, versão 10.3A-10 em diante) | CS:10444 | OF |
| Portas: TCP 2638 e UDP 2638; programas `dbsrv16/17.exe` e `dbeng16/17.exe`; cache do servidor recomendado em 70% | CS:2811 | OF |
| SQL Anywhere 17: `SYSCOLUMNS` (consolidada) tem coluna `remarks` alimentada por `ISYSREMARK`; existe a view `SYSREMARK` | https://help.sap.com/docs/SAP_SQL_Anywhere/93079d4ba8e44920ae63ffb4def91f5b/3be74eee6c5f1014a3def3d1f8953400.html | OF (SAP) |
| Connection string por driver (não DSN, que é 32 bits): `Driver={SQL Anywhere 17};Server=<srv>;DBN=<base>;UID=<u>;PWD=<s>;Host=<ip>:2638`; login integrado do Windows é recusado; erro "database server not found" = nome do servidor errado; SQLSTATE 28000 = usuário/senha | IMP:SKILL/dominio-servidor-sap/SKILL.md | T-DOC |
| O nome do usuário no banco pode ser qualquer um criado com tipo Externo (a Central usa "Externo"; terceiros usam `EXTERNO`, `EXTERNOII`) | CS:3227; REA:docs/descobertas-rea.md | OF + T-DOC |
| O usuário `EXTERNOII` (grupo `_somenteconsulta`) tem SELECT em 5.598 tabelas, também via `PUBLIC`; NÃO lê `DSDBA.*`, lê `SYS.*` | REA:docs/descobertas-rea.md | T-DOC |
| Domínio Web: um escritório relata (29/10/2026 a 02/11/2026) que o suporte liberou o banco de **produção ao vivo** para o **IP fixo** do escritório, informando Host, Porta, Engine e Banco por chamado; usuário Externo criado no Domínio. Não é caminho documentado publicamente | MAC:ponte/LEIA-ME.md | T-DOC (1 fonte) |
| Mesmo relato: atualização de usuário/senha novos pode demorar até o próximo ciclo de atualização do banco (10h, 12h, 16h, 19h ou 24 h segundo quem integra); login errado repetido bloqueia o usuário e devolve o mesmo erro -103 | MAC:ponte/LEIA-ME.md | T-DOC (1 fonte) |
| Domínio Web "leva o banco de dados para a nuvem"; backup em nuvem é automático no Web | https://www.dominiosistemas.com.br/solucoes/dominio-max/ ; CS:6994 | OF |
| Banco: SQL Anywhere 17.0.11.7312, schema/owner `bethadba`, ~4.800 tabelas base, charset windows-1252, banco de 30,84 GB num escritório | IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| Inventário de outro escritório: 4.844 fontes (4.745 BASE + 99 VIEW), 4.787 legíveis pelo Externo, 6.770 FKs declaradas no owner `bethadba` | REA:docs/descobertas-rea.md ; REA:data/raw/inventario_fontes_gerador.csv | T-DOC |

### A-1.2 Onde está o dicionário de dados (e onde NÃO está)

| Fato | Fonte | Nível |
|---|---|---|
| "Busca Tabelas" é a ferramenta oficial: "biblioteca de consulta do banco de dados ... localizar tabelas, colunas e descrições dos campos"; roda em Java, com o usuário Externo; download em `ftpdownload.dominiosistemas.com.br/Relatorios/Tecnica/BuscaTabelas.zip` | CS:3227 | OF |
| O Gerador de Relatórios do Domínio lista tabelas via `DSDBA.SYSTABLE` com a descrição vinda de `REMARKS` (cai para o nome da tabela se o comentário for vazio); tabelas/views do owner `bethadba`, exceto prefixos `AUDIT_`/`PBCAT` e ~130 tabelas internas | REA:sql/gerador_lista_tabelas.original.sql ; REA:docs/descobertas-rea.md | T-DOC (consulta extraída do executável do gerador, `geradrel.exe`) |
| Equivalências legíveis pelo Externo: `DSDBA.SYSTABLE` → `SYS.SYSTAB`/`SYS.SYSTABLE`; `DSDBA.SYSCOLUNAS` → `SYS.SYSTABCOL`/`SYS.SYSCOLUMN(S)`; `DSDBA.SYSFOREIGNKEYS` → `SYS.SYSFOREIGNKEYS`; permissões em `SYS.SYSTABLEPERM` | REA:docs/descobertas-rea.md ; REA:src/extractor/catalogo.py | T-DOC / T-COD |
| Outro escritório faz o mesmo ("é o Busca Tabelas do Domínio, sem precisar dele nem do Java"): lê só o catálogo `SYS` e obtém nomes, tipos, a descrição que o banco guarda e contagem de linhas | MAC:ponte/LEIA-ME.md | T-DOC (independente do REA) |
| Os comentários do banco trazem legenda de código dentro do texto (ex.: `ctlancto.orig_lan`: "1=Normal, 2=Zer, 3=Pat, 4=Esc, 5=Sai, 6=Ent, 7=Ser, 8=Aju, 9=Acu, 10=Apu, 11=PgtGuia, 12=Cliente, 13=Folha, 14-19=Hono") | REA:docs/colunas/ctlancto.md | T-DOC |
| Comentários às vezes estão errados ou ausentes: `situacao_sai/ent/ser` dizem "Codigo do modelo do documento fiscal"; `RFED_PAR` lista "1 / 2 / ... / 9" sem legenda; `REST_PAR` lista 1 a 4, mas os dados só têm 1 e 13 | REA:docs/colunas/efsaidas.md ; REA:docs/modelo-parametro_fiscal.md | T-DOC |
| Tabelas marcadas "** SEM USO **" ou "(Sem Uso)" no comentário: 11 no inventário (todas `fo*`, ex.: `fobasescalc`, `fointegconf`, `fodatapag`); colunas também (ex.: `DATA_CAT` em `FOAFASTAMENTOS`) | REA:data/raw/inventario_fontes_gerador.csv | T-DOC |
| `bethadba.autabelas` ("Tabelas que serao auditadas": `table_id`, `tabela`, `modulo`, `tabela_pai`, `descricao`, `seleciona`, `comentario`, `INATIVA`, 895 linhas no banco do autor) e `aucolunas` ("Comentario das colunas auditadas": `table_id`, `coluna`, `comentario`, ~15 mil linhas) são **configuração da auditoria**, não o dicionário completo. `audados` guarda o movimento auditado (`sequencial`, `table_id`, `codi_emp`, `usuario`, `data_hora`, `tipo` 1 inclusão/2 alteração/3 exclusão, `conteudo`) | REA:docs/colunas/autabelas.md, aucolunas.md, audados.md | T-DOC |
| Um terceiro usa `bethadba.autabelas.descricao` como "apelido" da tabela numa consulta de catálogo (ligando `systable.table_id`): funciona para as tabelas auditadas | YLA-S: "SQL - Relação de Tabelas e Colunas do Sistema.txt" | T-COD |
| Relatórios personalizados do Gerador (BGR) são salvos NO banco; as tabelas do próprio gerador são `RELATORIOS`, `CLASSIFICACOES_RELATORIOS`, `ARGUM_RELS`, `DEFARGUM`, `BANDAS_RELS`, `OBJETOS_RELS`, `DEFSELECT`, `COLSSELECT`, `SELSSELECT`, `ORDSELECT`, `CPTSSELECT`, `LAYOUT_ARQS`, `RELATORIOS_ATUALIZACAO` | CS:6466 ("IMPORTANDO O RELATÓRIO PARA O BANCO DE DADOS"); CS:4068 ("salvá-los no banco de dados do sistema"); nomes das tabelas do gerador: REA:docs/descobertas-rea.md | OF + T-DOC |
| Biblioteca oficial de relatórios BGR por módulo (Folha, Escrita, Honorários, Contabilidade, Protocolo): por exemplo "Relatório com Regimes Tributários das empresas", "Relatório com os regimes de apuração", "Relatório de Relação de Empresas", "Faturamento de todas as empresas" (conteúdo SQL dentro do .bgr, NÃO inspecionado) | CS:6464 ; CS:10237 ; CS:6773 ; CS:7082 ; CS:6465 ; https://suporte.dominioatendimento.com/central/faces/relatorios-personalizados.html | OF |
| Gerador de Relatórios do Domínio: abas Colunas, Argumentos e Seleção sobre "Fonte de Dados" | CS:8276 ; CS:8277 | OF |

### A-1.3 Convenção de nomes

| Convenção | Evidência | Fonte | Nível |
|---|---|---|---|
| Prefixos de módulo: `ge` Geral, `ef` Escrita Fiscal, `ct` Contabilidade, `fo` Folha, `hr` Honorários (atual; substitui `ho`/`hn`), `lr`/`la` Lalur (novo/antigo), `pm`/`pa` Patrimônio (novo/antigo), `po` Ponto, `rg` Registro, `pc` Processos, `pr` Protocolos, `au` Auditoria, `at`/`su`/`sy`/`us` suporte/sistema. No inventário: EF 2.723, FO 793, GE 390, CT 379, HR 149, LR 129, PM 52, PO 37, RG 35, PC 28, HN 26, LA 23, AU 17, PA 11, HO 11, PR 9 | inventário e tabela de módulos | REA:docs/descobertas-rea.md ; REA:data/raw/inventario_fontes_gerador.csv ; IMP:SKILL/dominio-servidor-sap/SKILL.md (ef/ct/fo/ge/hr) | T-DOC |
| Sufixo de coluna = abreviação da tabela: `_emp` (geempre), `_sai` (efsaidas), `_ent` (efentradas), `_ser` (efservicos), `_acu` (efacumulador), `_nat` (efnatureza), `_esp` (efespecies), `_for` (effornece), `_cli` (efclientes), `_pdi` (efprodutos), `_lan` (ctlancto), `_cta` (ctcontas), `_his` (cthispad), `_sim` (efsdoimp), `_par` (efparametro_vigencia), `_mep` (efmvepro), `_msp` (efmvspro), `_isa`/`_ien`/`_ise` (impostos por nota de saída/entrada/serviço). Padrão visto nas colunas documentadas; tabelas novas usam nomes longos sem sufixo (ex.: `VALOR_SERVICOS_SER` é exceção híbrida; `DATA_ITEM`, `HISTORICO` em `ctextrato_bancario_lancamento_item`) | REA:docs/colunas/*.md | T-DOC |
| Chave de empresa: `codi_emp` em quase todas as tabelas; "quase toda tabela é multiempresa via codi_emp"; em Honorários (`hr*`) `CODI_EMP` é o **escritório** (o escritório também é uma empresa em `geempre`) e o cliente é `I_CLIENTE` | REA:docs/descobertas-rea.md ; REA:docs/colunas/hrcliente.md ; REA:docs/colunas/hrfaturamento.md | T-DOC |
| Cada CNPJ (matriz e filial) é um `codi_emp` próprio; não há vínculo entre filiais no cadastro (agrupar pela raiz de 8 dígitos do CNPJ) | MAC:docs/DOMINIO-BANCO-2026-10-22.md (fontes F4/F5; uma delas foi removida do GitHub, ver A-1.9) | T-DOC (parcialmente não verificável hoje) |
| Vigências: tabelas `*_VIGENCIA` têm a data de vigência na PK: `EFACUMULADOR_VIGENCIA` (CODI_EMP, CODI_ACU, VIGENCIA_ACU), `EFACUMULADOR_VIGENCIA_CFOP`, `EFACUMULADOR_VIGENCIA_IMPOSTOS` (+ CODI_IMP), `EFPARAMETRO_VIGENCIA` (CODI_EMP, VIGENCIA_PAR; 657 colunas), `GEIMPOSTO_VIGENCIA` (CODI_EMP, CODI_IMP, VIGENCIA_IMP; 367 colunas). A vigência em vigor numa data é a de maior `vigencia` ≤ data, por empresa (validada contra apuração do Simples) | REA:docs/descobertas-rea.md ; REA:docs/modelo-parametro_fiscal.md ; REA:docs/colunas/efacumulador_vigencia*.md | T-DOC |
| Coluna `origem_reg`: 0 Sistema, 1 Importação de tabelas, 2 Importação por leiaute, 3 Importação de tabelas concorrentes (4 = Iceberg em `ctcontas`) | REA:docs/colunas/efnatureza.md ; ctcontas.md | T-DOC |
| Views com prefixo "V" (ex.: `FOVBASES`, `FOVGUIAINSS`, `EFVNOTAS_INF`, `HRVCLIENTE`): 99 views no inventário (comentário = próprio nome, sem descrição) | REA:data/raw/inventario_fontes_gerador.csv | T-DOC |
| Famílias grandes: `EFSDOIMP_*` (285 tabelas, muitas por UF/obrigação estadual), `EFIMPORTADOR_FIXO_*` (configuração do importador), `*_ENVIOS_ESOCIAL`/`FOESOCIAL_*` | REA:data/raw/inventario_fontes_gerador.csv | T-DOC |

### A-1.4 Tabelas verificadas: tabela → módulo → significado → colunas-chave → fonte

"Significado" vem do comentário da tabela no catálogo (tal como extraído em `REA:data/raw/inventario_fontes_gerador.csv`) e das colunas em `REA:docs/colunas/<tabela>.md`. Onde há uso em código de terceiros, a coluna Fonte traz também o repositório.

**GE — Geral**

| Tabela | Significado | Colunas-chave | Fonte | Nível |
|---|---|---|---|---|
| `geempre` | Empresa - Cadastro (clientes do escritório e o próprio escritório) | PK `codi_emp`; `nome_emp`, `razao_emp`, `apel_emp`, `fantasia_emp`; `cgce_emp` char(14) CNPJ/CPF; `tins_emp`; `stat_emp`; `dcad_emp`, `dina_emp`; `i_cnae20` (usar este, `cnae_emp` é double e quase vazio); `esta_emp`, `cida_emp`; flags `ucta_emp` (contabilidade), `uefi_emp` (escrita fiscal), `ufol_emp` (folha), `ucxa_emp` (livro caixa), `uhon_emp`; `rfed_emp` (regime federal da folha); `usa_dominio_web`; `GUID_ONVIO` | REA:docs/colunas/geempre.md ; YLA-P:Código M (Empresas); IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md (cnae) | T-DOC + T-COD |
| `GEIMPOSTO` / `GEIMPOSTO_VIGENCIA` | Impostos por empresa (e por vigência) | `codi_emp`, `codi_imp`, `nome_imp`, `sigl_imp`, `codi_sis` (5 Escrita Fiscal, 6 Lalur, 12 Folha) | REA:docs/colunas/geimposto.md ; IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| `GEMODULOS` | Lista dos módulos do sistema (13 linhas) | `I_MODULO`, `NOME`, `CODIGO`, `ORDEM`, `IMPORTA_DADOS` | REA:docs/colunas/gemodulos.md | T-DOC |
| `gesocios` | Sócios - Cadastro | PK `i_socio` | REA:docs/descobertas-rea.md | T-DOC |
| `genatjuridica`, `gemunicipio`, `gecnae20` | Natureza jurídica; municípios; tabela CNAE 2.0 | — | REA:data/raw/inventario_fontes_gerador.csv | T-DOC |
| `GESECUSUARIOS` | "Tabela de usuários do banco de dados"; `geusuarios` está vazia nas bases vistas | — | REA:data/raw/inventario_fontes_gerador.csv ; IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| `geloguser` | Log de sessões de uso (uma linha por sessão) | `usua_log`, `codi_emp`, `sist_log` (módulo), `data_log`+`tini_log` (entrada), `dfim_log`+`tfim_log` (saída) | IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| `GEEMPRE_CONTATO` | Contatos da empresa | — | REA:data/raw/inventario_fontes_gerador.csv ; https://github.com/LsDeveloper-IA/crm-office (Banco/consultas.py) | T-DOC + T-COD |

**CT — Contabilidade**

| Tabela | Significado | Colunas-chave | Fonte | Nível |
|---|---|---|---|---|
| `ctlancto` | Lançamentos contábeis: UMA linha por partida com conta a débito e a crédito | PK (`codi_emp`, `nume_lan`); `data_lan`; `vlor_lan`; `cdeb_lan` (conta débito), `ccre_lan` (conta crédito), conta 0 = sem conta naquele lado (lote com várias contrapartidas); `codi_his`, `chis_lan` (histórico livre, varchar 1000); `codi_usu` char(30) = NOME do operador; `orig_lan` (origem); `codi_lote`; `ndoc_lan`; `fili_lan`; `CODI_EMP_PLANO` (empresa do plano de contas) | REA:docs/colunas/ctlancto.md ; YLA-S:"SQL - Todos os Lançamentos .txt" ; YLA-P:Código M (Lançamentos) ; IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC + T-COD |
| `ctlanctolote` | Lançamento em lote | PK (`codi_emp`, `codi_lote`); `tipo` X/D/C/V | REA:docs/colunas/ctlanctolote.md | T-DOC |
| `ctcontas` | Contas contábeis - cadastro | PK (`codi_emp`, `codi_cta` = código reduzido); `clas_cta` classificação; `nome_cta`; `tipo_cta` A/S; `SITUACAO_CTA` A/I | REA:docs/colunas/ctcontas.md ; CS:672 (registro 0200: "Código reduzido", "Classificação contábil", Tipo A/S, Situação A/I) ; YLA-P:Código M (ContasContábeis) | T-DOC + OF + T-COD |
| `cthispad` | Históricos padrões | `codi_emp`, `codi_his`, `desc_his` | REA:docs/colunas/cthispad.md | T-DOC |
| `ctcontacaixa` | Parâmetros: contas caixa | `codi_emp`, `codi_cta`, `sele_cta`, `TIPO_CONTA_CAIXA` | REA:docs/colunas/ctcontacaixa.md | T-DOC |
| `ctccusto`, `ctparmto` | Centros de custo; parâmetros da contabilidade | `ctparmto`: `FECHAMENTO_DATA`, `dini_par`, `dfin_par` | REA:docs/colunas/ctparmto.md | T-DOC |
| `CTORIGEM_LANCAMENTO` | Origem dos lançamentos da contabilidade (29 linhas no banco do autor) | `I_ORIGEM`, `DESCRICAO` | REA:docs/colunas/ctorigem_lancamento.md | T-DOC |
| `ctextrato_bancario_lancamento_item` | Lançamento de extrato bancário - itens | PK (`CODI_EMP`, `I_LANCAMENTO`, `I_ITEM`); `DATA_ITEM`, `HISTORICO`, `DOCUMENTO`, `VALOR`, `TIPO` (D=Soma, C=Subtrai), `ORIGEM` (M manual / I importação), `VERSAO` (1 antigo / 2 novo) | REA:docs/colunas/ctextrato_bancario_lancamento_item.md | T-DOC |
| `CTLANCTOFCONT` | Lançamento FCONT (0 linhas no banco do autor) | — | REA:data/raw/inventario_fontes_gerador.csv | T-DOC |
| `CTLANCTO_SALDO` | Tabela Saldos Contábeis (0 linhas no banco do autor) | `CODI_EMP`, `CODI_EMP_PLANO`, `CODI_CTA`, `DATA_LAN`, `VLOR_DEB`, `VLOR_CRE`, `ORIG_LAN` | REA:docs/colunas/ctlancto_saldo.md | T-DOC |
| `efsaidas_lancto`, `efentradas_lancto`, `efservicos_lancto`, `efsdoimp_lancto`, `efpagimp_lancto` | Ligação documento fiscal/apuração/pagamento ↔ lançamento contábil | `codi_emp`, `nume_lan`, `codi_sai`/`codi_ent`... | REA:data/raw/inventario_fontes_gerador.csv ; YLA-S:"SQL - Todos os Lançamentos .txt" (efentradas_lancto) | T-DOC + T-COD |

**EF — Escrita Fiscal**

| Tabela | Significado | Colunas-chave | Fonte | Nível |
|---|---|---|---|---|
| `efsaidas` | Notas Fiscais de Saída; uma linha por SEGMENTO da nota | PK (`codi_emp`, `codi_sai`); `codi_cli`, `codi_esp`, `codi_acu`, `codi_nat`+`versao_nat` (CFOP), `nume_sai`, `seri_sai`, `segi_sai` (segmento), `dsai_sai` (data de saída), `ddoc_sai` (data de emissão), `vcon_sai` (valor contábil, o que o Domínio mostra como faturamento), `vprod_sai` (valor dos produtos), `situacao_sai`, `cancelada_sai` S/N, `chave_nfe_sai` char(44), `EMITENTE` P/T, `cifob_sai` C/F | REA:docs/colunas/efsaidas.md ; YLA-S:"SQL - Resumido com Impostos - Relatório de Saidas .txt" ; IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC + T-COD |
| `efentradas` | Notas Fiscais de Entrada; uma linha por SEGMENTO; NFS-e tomada também entra aqui (relato de terceiro, cuja fonte original foi removida do GitHub; coincide com a memória do projeto do usuário) | PK (`codi_emp`, `codi_ent`); `codi_for`, `codi_esp`, `codi_acu`, `codi_nat`+`versao_nat`, `nume_ent`, `seri_ent`, `segi_ent`, `dent_ent` (data de entrada/escrituração), `ddoc_ent` (emissão), `vcon_ent`, `vprod_ent`, `situacao_ent`, `chave_nfe_ent`, `CONFERIDO` S/N, `emitente_ent` P/T | REA:docs/colunas/efentradas.md ; MAC:docs/FILA-CODE-2026-11-03-NOTAS-DUVIDAS.md ; YLA-S:"SQL - Ficha Técnica - Notas de Entrada.txt" | T-DOC + T-COD |
| `efservicos` | Notas Fiscais de Serviço (prestados) | PK (`codi_emp`, `codi_ser`); `codi_cli`, `codi_esp`, `codi_acu`, `nume_ser`, `dser_ser`, `vcon_ser`, `VALOR_SERVICOS_SER`, `situacao_ser`, `cancelada_ser` | REA:docs/colunas/efservicos.md ; MAC:docs/DOMINIO-BANCO-2026-10-22.md | T-DOC |
| `efmvspro` / `efmvepro` | Itens (produtos) das notas de saída / entrada | PK (`codi_emp`, `codi_sai`/`codi_ent`, `nume_msp`/`nume_mep`); `codi_pdi`, `cfop_mep`, `qtde_mep`, `vpro_mep`...; o item NÃO tem NCM nem descrição própria (vêm de `efprodutos`) | REA:docs/colunas/efmvepro.md ; MAC:docs/FILA-CODE-2026-11-03-NOTAS-DUVIDAS.md | T-DOC |
| `efimpsai` / `efimpent` / `efimpser` | Impostos por nota (saída / entrada / serviço) | `codi_emp`, `codi_sai`/`codi_ent`/`codi_ser`, `codi_imp`; valores: `vlor_*` (imposto), `vise_*` (isentas), `vout_*` (outras), `bcal_isa` (base) | REA:docs/colunas/efimpsai.md, efimpent.md ; YLA-S:"SQL - Resumido com Impostos - Relatório de Saidas .txt" e "...Entradas.txt" | T-DOC + T-COD |
| `efprodutos` | Produtos - cadastro (por empresa) | `codi_pdi` char(14), `desc_pdi`, `cncm_pdi` (NCM char 8), `codigo_barras_pdi` (usar este; `ean_pdi` vem vazio fora de SE) | REA:docs/colunas/efprodutos.md ; MAC:docs/FILA-CODE-2026-11-03-NOTAS-DUVIDAS.md | T-DOC |
| `efclientes` / `effornece` | Clientes / Fornecedores - cadastro (por empresa) | `codi_cli`/`codi_for`, `nome_for` (razão social), `cgce_for`, `tins_for`, `regime_for` (N/M/E/O/S/P/U/I) | REA:docs/colunas/effornece.md, efclientes.md | T-DOC |
| `efsdoimp` | Saldo dos Impostos = apuração por imposto/competência | PK (`codi_emp`, `codi_imp`, `data_sim` = competência, `pdic_sim` = periodicidade); `sdev_sim` (saldo a recolher = o imposto), `scre_sim` (saldo credor), `bcal_sim` (base), `vime_sim` (comentário: "Valor do imposto de entradas"), `vlrpago_sim`, `USUARIO`, `DATA_HORA` | REA:docs/colunas/efsdoimp.md ; IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| `efacumulador` | Acumuladores - cadastro (view `EFACUMULADORES` existe, vazia/legado) | PK (`CODI_EMP`, `CODI_ACU`); `NOME_ACU`, `SITUACAO_ACU`, `DATA_CADASTRO_ACU` | REA:docs/colunas/efacumulador.md ; YLA-S:"SQL - Acumuladores Full.txt" | T-DOC + T-COD |
| `EFACUMULADOR_VIGENCIA` | Configuração do acumulador por vigência | PK (+ `VIGENCIA_ACU`); `IFAT_ACU` (incide sobre faturamento S/N), `IREC_ACU` (incide sobre receita bruta S/N), `CDEB_ACU`/`CCRE_ACU` (contas), `CHIS_ACU`, `PARC_ACU`, `LANCAR_SOMENTE_ENTRADA/SAIDA/SERVICO`, `SIMPLESN_*` | REA:docs/colunas/efacumulador_vigencia.md | T-DOC |
| `EFACUMULADOR_VIGENCIA_CFOP` | Acumuladores - naturezas (CFOP) permitidas | PK (`CODI_EMP`, `CODI_ACU`, `VIGENCIA_ACU`, `CODI_NAT`) | REA:docs/colunas/efacumulador_vigencia_cfop.md | T-DOC |
| `EFACUMULADOR_VIGENCIA_IMPOSTOS` | Acumuladores - impostos por vigência | PK (+ `CODI_IMP`); `ALBC_IAC`, `CODREC_PADRAO_IAC`, `DIFERENCA_IAC` (1 isentas/2 outras/3 não lançar/4 IPI/5 SUBTRI/6 não tributadas/7 parcela reduzida), `SIMPLESN_ANEXO_IAC`... | REA:docs/colunas/efacumulador_vigencia_impostos.md | T-DOC |
| `efnatureza` | Naturezas de operação (CFOP) | PK (`codi_nat`, `versao_nat`), `nome_nat`; `versao_nat = 2` é a tabela de CFOP de 4 dígitos usada nos scripts | REA:docs/colunas/efnatureza.md ; YLA-S:"SQL - Ficha Técnica - Notas de Entrada.txt" | T-DOC + T-COD |
| `efespecies` | Espécies de documento | `codi_esp`, `nome_esp`, `mode_esp` ("Modelo do documento fiscal"), `codigo_modelo` char(2) ('55','57','65'...), `tipo_esp`, `DOCUMENTO_NAO_FISCAL`, `NOTA_FISCAL_CONJUGADA` | REA:docs/colunas/efespecies.md ; IMP:SKILL/dominio-servidor-sap/SKILL.md (`mode_esp`: 36 = NF-e 55, 41 = NFC-e 65) ; MAC:docs/FILA-CODE-2026-11-03-NOTAS-DUVIDAS.md (`codigo_modelo`) | T-DOC |
| `EFPARAMETRO_VIGENCIA` | Parâmetros da Escrita Fiscal por vigência (657 colunas) | PK (`CODI_EMP`, `VIGENCIA_PAR`); `REST_PAR` (regime estadual), `RFED_PAR` (regime federal), `RMUN_PAR` (municipal 1 Normal/2 Simples), `REGIME_RECOLHIMENTO_PAR` (R/P), `FEDERAIS_REGIME_PAR` (C competência/X caixa), `SIMPLESN_OPTANTE_PAR` S/N, `SIMPLESN_ANEXO_I..V_PAR`, `SIMPLESN_REGIME_PAR` | REA:docs/colunas/efparametro_vigencia.md ; REA:docs/modelo-parametro_fiscal.md | T-DOC |
| `EFCUPOM_FISCAL_ELETRONICO` (+ `_IMPOSTOS`, `_IMPOSTOS_DETALHAMENTO`) | CF-e SAT | `CODI_EMP`, `I_CFE`, `DATA_CFE`, `VALOR_TOTAL_CFE`, `SITUACAO`, `EXTRATO`, `EXTRATO_CANCELAMENTO`, `SAT`; impostos: `VALOR_IMPOSTO`, `VALOR_ISENTAS`, `VALOR_OUTROS`, `BASE_CALCULO` | REA:docs/colunas/efcupom_fiscal_eletronico.md ; YLA-S:"SQL - Resumido com Impostos - Relatório de Cupons Fiscais.txt" | T-DOC + T-COD |
| `EFATENDIMENTO_NFE_CATALOGO` / `EFATENDIMENTO_NFE_XML_V2` | Catálogo de notas "Domínio Atendimento" / XML comprimido das NF-e | `CHAVE`, `TIPO` (1 Entrada/2 Saída/3 Cancelamento/4 Serviço/5 Outros), `XML_EXCLUIDO`; `CONTEUDO_XML` long binary (comprimido). O terceiro relata que a Domínio apaga o XML depois de ~2 meses | MAC:docs/FILA-CODE-2026-11-03-NOTAS-DUVIDAS.md | T-DOC (1 fonte) |

**FO — Folha**

| Tabela | Significado | Colunas-chave | Fonte | Nível |
|---|---|---|---|---|
| `foempregados` | Empregados - cadastro (416 colunas). O cadastro cobre empregados, **contribuintes** e estagiários | PK (`codi_emp`, `i_empregados`); `nome`, `cpf`, `admissao`, `salario`, `categoria`, `vinculo`, `tipo_contrib` (E empregador/F facultativo/A autônomo/R produtor rural/M MEI/S segurado especial/I autônomo MEI), `contrib_indiv` | REA:docs/colunas/foempregados.md ; CS:8722 ("empregados, contribuintes e estagiários") | T-DOC + OF |
| `forescisoes` | Rescisão - cálculo | `codi_emp`, `i_empregados`, `demissao`, `motivo` (código sem tabela de descrição no banco; texto está no executável); complemento de rescisão duplica a linha: usar a menor data | REA:docs/colunas/forescisoes.md ; IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| `fobasesserv` | Bases - cálculo mensal | PK inclui `competencia`, `tipo_process`, `i_calculos`; `dias_servico` (cada empregado aparece 2x por competência, uma com 0: filtrar `> 0`), `proventos`, `descontos`, `USUARIO_CALCULO`, `DATA_HORA_CALCULO`. As colunas de encargo (`val_inss_empresa`...) vieram nulas; encargo vem de `foguiainss` | REA:docs/colunas/fobasesserv.md ; IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| `foguiainss` / `foguiapis` | Guia de INSS / guia PIS | `empresa`, `acid_trab` (RAT), `terceiros`, `segurados`; `valor` (PIS) | REA:docs/colunas/foguiainss.md ; IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| `foeventos`, `fomovtoserv` | Eventos/rubricas - cadastro; movimentação - cálculo | `tipo_proces`/`prov_desc` (P/D/I) | REA:docs/modelo-folha.md | T-DOC |
| `FOAFASTAMENTOS` | Afastamentos dos empregados | PK (`CODI_EMP`, `I_EMPREGADOS`, `DATA_REAL_DN`); `DATA_REAL`, `DATA_FOLHA`, `I_AFASTAMENTOS` (→ `FOAFASTAMENTOS_TIPO`), `DATA_FIM`, `NUMERO_DIAS` | REA:docs/colunas/foafastamentos.md | T-DOC |
| `foaltesal` | Salários - processos (alterações salariais) | `codi_emp`, `i_empregados`, `competencia`, `novo_salario`, `salario_anterior`, `motivo`, `perc_aumento`, `retroativo*`, `periodo_*` | REA:docs/colunas/foaltesal.md | T-DOC |
| `FONOTA_FISCAL_SERVICOS_PRESTADOS` / `_TOMADOS` | "Nota fiscal de serviço prestado/tomado" no módulo Folha (0 linhas no banco do autor) | — | REA:data/raw/inventario_fontes_gerador.csv | T-DOC |
| `FOVGUIAINSS`, `FOVBASES` | VIEWs de Folha sobre guia de INSS e bases (sem descrição no catálogo) | — | REA:data/raw/inventario_fontes_gerador.csv | T-DOC |
| `foafastamentos`... demais `fo*` (793 no inventário) | `FOESOCIAL_*`, `*_ENVIOS_ESOCIAL`, cargos (`focargos`), departamentos (`fodepto`), sindicatos (`fosindicatos`: Convenção Coletiva), `fosefip`, etc. | — | REA:data/raw/inventario_fontes_gerador.csv ; https://github.com/ElderVivot/conversor-folha-dominio (layouts/*.TXT: dump de colunas com tipo) | T-DOC |

**HR — Honorários**

| Tabela | Significado | Colunas-chave | Fonte | Nível |
|---|---|---|---|---|
| `HRCLIENTE` | Clientes fixos e eventuais do escritório | PK (`CODI_EMP` = escritório, `I_CLIENTE`); `NOME`, `TIPO` (F fixo / E eventual), `I_CLIENTE_FIXO` (um terceiro afirma que liga a `geempre.codi_emp`), `TIPO_INSCRICAO`, `TIPO_COBRANCA` | REA:docs/colunas/hrcliente.md ; IMP:SKILL/dominio-servidor-sap/SKILL.md | T-DOC |
| `HRCONTRATO`, `HRCONTRATO_FATURAMENTO` | Contratos e faturamento de contratos | — | REA:data/raw/inventario_fontes_gerador.csv | T-DOC |
| `HRFATURAMENTO` | Faturamento (honorários emitidos) | PK (`CODI_EMP` escritório, `I_FATURAMENTO`); `I_CLIENTE`, `COMPETENCIA`, `DATA_FATURAMENTO`, `TIPO_FATURAMENTO` (T todos/C contratos/E eventos sem contrato), `I_NOTA_FISCAL`, `I_NOTA_NFSE`, `USUARIO`, `DATA_HORA` | REA:docs/colunas/hrfaturamento.md | T-DOC |
| `HREVENTO`, `HRCLASSIFICACAO`, `HRCONTA_FINANCEIRA`, `HRNOTA_NFSE_TOKEN` (token de emissão de NFS-e: sensível) | Eventos; classificações; contas financeiras; token | — | REA:data/raw/inventario_fontes_gerador.csv | T-DOC |

**Não encontrei documento público de significado** para: `ctlancto` colunas `ndoc_lan`/`dorig_lan` além do comentário; tabelas da Redução Z (existem 69 nomes com "reduc/reduz", p.ex. `EFCONTABILIZACAO_REDUCAO_Z_MEIO_PAGAMENTO`; a tabela principal não foi identificada).

### A-1.5 Legendas de códigos

| Coluna | Legenda | Fonte | Nível |
|---|---|---|---|
| "Situação da Nota" (campo do leiaute de importação, notas de entrada/saída/serviço) | 0 Documento Regular; 1 Regular Extemporâneo; 2 Cancelado; 6 Fiscal Complementar/Referenciado; 7 NF-e/NFC-e/CT-e Denegado; 8 Numeração Inutilizada; 9 Emitido com base em Regime Especial ou Norma Específica; 10 Complementar Extemporâneo; 11 Regular Simples Nacional (aparece em um dos registros) | CS:672 | OF (equivalência com `situacao_sai/ent/ser` do banco é INF, ver A-2) |
| `situacao_sai`, `situacao_ent`, `situacao_ser` (banco) | Valores observados: 0 (≈98% das notas de saída), 1, 2, 4, 6, 7, 8, 9, 10; comentário do banco ("Codigo do modelo do documento fiscal") não corresponde | REA:docs/modelo-fiscal.md (domínio `situacao_documento`, "Confirmado: não") | T-DOC |
| `cancelada_sai/ser` | S/N, independente da situação (usar as duas) | REA:docs/colunas/efsaidas.md ; MAC:docs/DOMINIO-BANCO-2026-10-22.md | T-DOC |
| `geempre.stat_emp` | A Ativa; I Inativa; C Em constituição; M Ativo sem movimento; B Em processo de baixa; E Excluindo | REA:docs/colunas/geempre.md ; REA:docs/modelo-fiscal.md | T-DOC (comentário do banco) |
| `geempre.tipoi_emp` | Motivo da inatividade: 1 Outros, 2 Baixada, 3 Transferida, 4 Inadimplente | REA:docs/modelo-fiscal.md | T-DOC |
| `tins_emp`, `tins_for`, `TIPO_INSCRICAO` | 1 CNPJ, 2 CPF, 3 CEI, 6 CAEPF | REA:docs/colunas/geempre.md, effornece.md, hrcliente.md | T-DOC |
| `geempre.HONORARIO_TIPO` | E Escritório (quem fatura) / C Cliente | REA:docs/modelo-fiscal.md | T-DOC |
| `ctcontas.tipo_cta`, `SITUACAO_CTA` | Tipo: A Analítica (recebe lançamentos) / S Sintética; Situação: A Ativa / I Inativa | REA:docs/colunas/ctcontas.md ; CS:672 | OF + T-DOC |
| Grupo da conta = 1º dígito de `clas_cta` | 1 Ativo (devedora), 2 Passivo e PL (credora), 3 Custos e despesas (devedora), 4 Receitas (credora), 5 Apuração do resultado, 6 Encerramento | IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| `ctlancto.orig_lan` | Comentário do banco: 1 Normal, 2 Zeramento, 3 Patrimônio, 4 Escrita, 5 Saídas, 6 Entradas, 7 Serviços, 8 Ajuste, 9 Acumulador, 10 Apuração, 11 Pagamento de guia, 12 Cliente, 13 Folha, 14-19 Honorários. Confirmados por ligação 1:1 com tabelas `*_lancto`: 5, 6, 7, 10, 11. Observados também: 49 (CF-e, inferido) e mais valores sem documentação (31 distintos no banco de um terceiro). Independente: `orig_lan = 13` filtra lançamentos de folha; `orig_lan = 2` é zeramento/encerramento | REA:docs/colunas/ctlancto.md ; REA:docs/modelo-contabil.md ; https://github.com/ElderVivot/bi-lanc-contabil-folha-dominio/blob/HEAD/src/dao/get_lanc_folha.py ; MAC:docs/DOMINIO-BANCO-2026-10-22.md | T-DOC + T-COD |
| `ctlanctolote.tipo` | X um débito/um crédito; D um débito/vários créditos; C um crédito/vários débitos; V vários/vários | REA:docs/colunas/ctlanctolote.md | T-DOC |
| `ctcontacaixa.TIPO_CONTA_CAIXA` | 1 Conta bancária, 2 Dinheiro/Espécie, 3 Numerários em trânsito, 4 Não gerar no LCDPR | REA:docs/colunas/ctcontacaixa.md | T-DOC |
| `efsdoimp.pdic_sim` | 1 1º decêndio, 2 2º, 3 3º, 4 1ª quinzena, 5 2ª quinzena, 6 Mensal, 7 Trimestral, 11-15 semanas, 51 Complementar, 52 13º salário | REA:docs/colunas/efsdoimp.md | T-DOC |
| `codi_imp` globais (nomes iguais em todas as empresas) | 1 ICMS, 2 IPI, 3 ISS, 4 PIS, 5 COFINS, 8 DIFALI, 9 Substituição Tributária, 16 IRRF, 18 ISS Retido, 22 PIS Retido, 23 COFINS Retido, 24 CSLL Retida, 26 INSS Retido (o cadastro por empresa está em `geimposto`) | REA:docs/modelo-fiscal.md | T-DOC |
| `geimposto.codi_sis` | 5 Escrita Fiscal; 6 Lalur; 12 Folha | IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| `geloguser.sist_log` / `GEMODULOS` | 1 Contabilidade; 3 Honorários; 4 Patrimônio; 5 Escrita Fiscal; 6 Lalur; 12 Folha; 13 Ponto Eletrônico; 15 Registro (a tabela `GEMODULOS`, 13 linhas, é a fonte autoritativa) | IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| Regimes em `EFPARAMETRO_VIGENCIA` | `REST_PAR` (comentário): 1 Normal, 2 ME, 3 Estimativa, 4 EPP; `RMUN_PAR`: 1 Normal, 2 Simples; `REGIME_RECOLHIMENTO_PAR`: R Real, P Presumido (nos dados só aparece R, não distingue presumido de real); `SIMPLESN_OPTANTE_PAR`: S/N; `FEDERAIS_REGIME_PAR`/`SIMPLESN_REGIME_PAR`: C competência, X caixa | REA:docs/colunas/efparametro_vigencia.md ; REA:docs/modelo-parametro_fiscal.md | T-DOC |
| `geempre.rfed_emp` (regime federal da FOLHA) | 1 Normal, 2 Microempresa, 3 Empresa de pequeno porte (confirmado parcialmente) | REA:docs/modelo-fiscal.md | T-DOC |
| `effornece.regime_for` e regime de apuração | N Normal; M ME; E EPP; O Outros; S ME Simples Nacional; P EPP Simples Nacional; U Imune; I Isenta | REA:docs/colunas/effornece.md | T-DOC |
| `efsaidas.EMITENTE`/`emitente_ent` | P Próprio / T Terceiros | REA:docs/colunas/efsaidas.md | T-DOC |
| `efsaidas.cifob_sai` | C CIF / F FOB | REA:docs/colunas/efsaidas.md | T-DOC |
| `fomovtoserv.tipo_proces` / `fobasesserv.tipo_process` (tipo de folha) | 11 Mensal; 31-36 semanas; 41 Adiantamento; 42 Complementar; 51 Adiant. 13º; 52 13º salário; 70 PLR; 91 Resilição de professor. Tipos 60, 61, 92 existem e não estão documentados | REA:docs/modelo-folha.md | T-DOC |
| `foeventos.prov_desc` | P Provento; D Desconto; I Informativo | REA:docs/modelo-folha.md | T-DOC |
| Cadastro de empregados (relatórios oficiais) | Situação "1 - Trabalhando"; categorias: Mensalista, Diarista, Horista, Diretor, Comissionário, Tarefeiro, Semanalista; vínculos: Celetista, Estatutário, Celetista Contrato Intermitente | CS:7 | OF (nomes de filtro da tela; os códigos numéricos no banco não são dados ali) |
| `origem_reg` | 0 Sistema, 1 Imp. Tabelas, 2 Imp. Layout, 3 Imp. Tabelas Concorrentes | REA:docs/colunas/efnatureza.md | T-DOC |

### A-1.6 Armadilhas de dados, desempenho e driver (confirmadas)

| Armadilha | Fonte | Nível |
|---|---|---|
| ODBC do SQL Anywhere 17: `fetchSize > 1` (array-fetch) dá "Invalid cursor position" e às vezes derruba o processo Node; só `fetchSize` 1 é estável ("confirmado em teste real, nov/2026") | PONTE:src/banco.ts | T-COD (comentário do código) |
| ODBC do SQL Anywhere 17 recusa conexão em modo somente-leitura e atributo de timeout de consulta ("Driver not capable", HYC00, visto em 02/11/2026); o Externo já é só leitura, então o limite de tempo precisa ser controlado por fora | MAC:ponte/LEIA-ME.md | T-DOC |
| Ler linha a linha pelo ODBC fez ~60 linhas/min numa base de 30 GB (cache insuficiente/paginação em disco); agregar no servidor; cache maior que a RAM livre piora | IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md ; IMP:SKILL/dominio-servidor-sap/SKILL.md ; MAC:docs/DOMINIO-BANCO-2026-10-22.md | T-DOC (2 fontes) |
| `UNLOAD` é negado ao Externo (exige servidor iniciado com `-gl all`): não depender dele | IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| Charset do banco é windows-1252 (`DB_PROPERTY('CharSet')`); o driver converte (UTF-16); `CHAR` tem largura fixa (`RTRIM`) | IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md ; MAC:docs/DOMINIO-BANCO-2026-10-22.md ; PONTE:src/banco.ts (`CharSet=UTF-8` na connection string) | T-DOC + T-COD |
| Datas com lixo (1979, 8320): sempre filtrar faixa (ex.: 2000-01-01 a 2035-12-31) em MIN/MAX | IMP:SKILL/dominio-servidor-sap/SKILL.md ; MAC:docs/DOMINIO-BANCO-2026-10-22.md | T-DOC (2 fontes) |
| `SUM(a + b)` vira NULL se qualquer parcela for NULL: usar ISNULL | IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| `DISTINCT` com `ORDER BY` exige aliases do SELECT (erro -854); não há `DATE_TRUNC`; parâmetros com `?`; `TOP n`, `LIST()`, `ISNULL`, `CURRENT DATE`, `DATEADD` | MAC:docs/DOMINIO-BANCO-2026-10-22.md | T-DOC |
| Colunas de nome diferente entre versões/bases: `razao_emp` vs `RAZA_EMP`; `dsai_sai` vs `ddoc_sai` vs `DATA_SAIDA`; `esta_emp` vs `uf_emp` | MAC:docs/DOMINIO-BANCO-2026-10-22.md | T-DOC (1 fonte) |
| `ctlancto.codi_usu` é o NOME do operador, não código | IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md ; REA:docs/colunas/ctlancto.md | T-DOC |
| Valor de FGTS não é gravado no banco (zero nas bases); legenda do motivo de demissão não existe no banco | IMP:SCRIPTS/DOCUMENTACAO-TECNICA.md | T-DOC |
| Usuário bloqueia por tentativas de login erradas e devolve o mesmo erro mesmo com a senha certa | MAC:ponte/LEIA-ME.md | T-DOC |

### A-1.7 Segurança e dado pessoal (relevante para o MCP)

| Fato | Fonte | Nível |
|---|---|---|
| "O banco guarda senhas, tokens e segredos em texto em 79 tabelas." O servidor MCP do terceiro bloqueia por padrão: `gecertificadosdigitais`, `geapuracao_assistida_credenciais`, `geatendimento_banking_keycloak_credentials`, `fodarf_dctfweb_api_tokens_requisicao`, `efdas_api_tokens_requisicao`, `geconfiguracao_envio_email_parametros`, `geconversao_senha_usuarios`, `gesenhainternethist`, `syslicacao`, `sysliberacao2`, `sysliberacao_historico`, `gesecusuarios`, `gesecusuariosgrupos`, `efproxy_lista`; e omite colunas cujo nome casa com senha/password/pwd/token/secret/segredo/credencial/private/arquivo_certificado/frase_secreta | REA:config/seguranca.yaml ; REA:docs/uso-mcp.md | T-DOC |
| 57 de 4.844 fontes não são legíveis para o usuário Externo do autor (ex.: `GEUSUARIOS_DBA_SENHAS_PERSONALIZADAS`, `SUPPORT_SA_CONN_INFO`) | REA:data/raw/inventario_fontes_gerador.csv | T-DOC |
| Dado pessoal em `foempregados` (nome, CPF, salário, nascimento...), `gesocios`, `geempre_contato`, `ctlancto.CPF_TITULAR_PAGAMENTO`, `CPF_BENEFICIARIO_SERVICO`: 67 campos marcados sensíveis no modelo do terceiro (sem mascaramento nessa versão) | REA:docs/uso-mcp.md | T-DOC |
| Outro escritório só deixa sair contagem/soma por empresa e recusa resultado com coluna de nome, documento pessoal, salário, nascimento, endereço ou contato | MAC:ponte/LEIA-ME.md | T-DOC |
| Tabelas de leitura grande (> 200 mil linhas) exigem filtro por coluna indexada/empresa; padrão 50 linhas, máx. 500; 40 colunas por padrão em tabelas largas (até 400 colunas); timeout 60 s | REA:config/seguranca.yaml | T-DOC |

### A-1.8 Código e queries públicos (A2): repositório → o que traz → licença

| Repositório | Arquivos relevantes | O que mostra | Licença / observação |
|---|---|---|---|
| https://github.com/Ylaros/Scripts-SQL-Personalizados-Dominio-SQL-Anywhere | `Scripts/*.txt` (10 scripts do Gerador de Relatórios) | `ctlancto`+`ctcontas`+`efentradas_lancto`+`geempre`; `efsaidas`/`efentradas` com `efimpsai`/`efimpent`+`geimposto`; acumuladores (`EFACUMULADOR*`); `EFCUPOM_FISCAL_ELETRONICO*`; `efprodutos`/`efmvepro`/`effornece`/`efnatureza`; `EFIMPORTADOR_FIXO_NFE_ENTRADA_*`; catálogo com `systable`/`syscolumn`/`autabelas` | sem licença (README: "uso livre com atribuição"); só estrutura |
| https://github.com/Ylaros/Dashboard-Balancetes-Power-BI | `Código M/*.txt`, `CONEXAO_ODBC.md`, `pbit/Dashboard PBI.pbit` | Power Query sobre `geempre`, `ctcontas` (`clas_cta` hierárquica, `tipo_cta`), `ctlancto`. ATENÇÃO: o `CONEXAO_ODBC.md` lista tabelas `eflancam`, `efplancon`, `efempresas`, `efbalancete`, `audados` como "úteis"; o próprio código M do autor usa `ctlancto`/`ctcontas`/`geempre`: os quatro primeiros nomes NÃO são do Domínio (descartar); `audados` existe mas é auditoria | sem licença |
| https://github.com/salesgordo0022/imperialBi | `SCRIPTS/DOCUMENTACAO-TECNICA.md`, `SCRIPTS/CODIGO-EXPLICADO.md`, `SKILL/dominio-servidor-sap/SKILL.md` | Extração de 30 GB com tabelas `geempre`, `ctlancto`, `ctcontas`, `ctcontacaixa`, `efsaidas`, `efentradas`, `efsdoimp`, `geimposto`, `fobasesserv`, `foguiainss`, `foguiapis`, `foempregados`, `forescisoes`, `geloguser`, `GEMODULOS`; armadilhas. O repositório também embute binários do SAP SQL Anywhere (redistribuição de software de terceiro: não usar) | sem licença |
| https://github.com/Lucas-Bueno04/REA_DOMINIO_DB | `docs/colunas/` (2.126 arquivos), `docs/modelo-*.md`, `docs/descobertas-rea.md`, `docs/uso-mcp.md`, `config/seguranca.yaml`, `data/raw/inventario_fontes_gerador.csv`, `src/server/*` | Mapa completo do banco + MCP (ver B-1.2). Obtido por engenharia reversa do `geradrel.exe` e leitura do catálogo; contém comentários do catálogo (autoria do fornecedor) | sem licença. Risco jurídico: não copiar o catálogo; ler do banco licenciado do próprio usuário em tempo de execução |
| https://github.com/macedo-reis-contabilidade/macedo-reis-dashboards | `docs/DOMINIO-BANCO-2026-10-22.md`, `docs/FILA-CODE-*.md`, `ponte/LEIA-ME.md`, `ponte/consultas/*.sql`, `CLAUDE.md` | Rascunho de pesquisa com fontes e nível de confiança; consultas agregadas por empresa/mês; conexão com Domínio Web; uso de Claude Code com filas de tarefas | sem licença; repositório de escritório pode ter dado de cliente |
| https://github.com/cors4rio/dmf-data-engine | `docs/legacy/Specs_Definitivos/CT_*.md`, `QUERY_*.md`, `docs/regras-de-negocio.md` | Specs de `ctlancto`, `ctparmto_sped_vigencia`, faturamento = `efsaidas` + `efservicos`, folha de empregados; CONFLITA com REA em `orig_lan` 5 (ver A-1.9) | sem licença |
| https://github.com/ElderVivot/conversor-folha-dominio | `layouts/*.TXT` (45 dumps: tabela, ordem, coluna, descrição, tipo, tamanho), `src/sqls/**` | Folha: `foempregados` (+`_plano_saude`, `_envios_esocial`...), `fofiliais`, `fohorarios`, `foesocial_*`, `geempre`, `gesocios`, `gecontador`... | sem licença |
| https://github.com/ElderVivot/bi-lanc-contabil-folha-dominio | `src/dao/get_lanc_folha.py`, `get_companies.py` | `ctlancto` com `orig_lan = 13`; `geempre` | sem licença |
| https://github.com/DeveloperOffice/gestk-back ; https://github.com/gabrielcsilvaa/gestao-office-back | `apps/importacao/management/commands/etl_07_notas_fiscais.py`; `get_empresas/services/*.py`; `requirements.txt` (`pyodbc==5.2.0`) | ETLs Django/DRF do Domínio por ODBC: `EFSAIDAS`/`EFENTRADAS` (`NUME_*`, `SITUACAO_*`, `SERI_*`, `CHAVE_NFE_*`), `ctlancto`, `geempre`, `efservicos` | sem licença |
| https://github.com/Renata5207418/PGDAS-IntegraContador ; https://github.com/Renata5207418/Consulta_Ebef | `database/dominio_db.py`; `database/db_conection.py` | `efsdoimp_simples_nacional` (coluna `filial`) + `geempre`; `geempre.stat_emp`, `njud_emp`, `cgce_emp` | sem licença |
| https://github.com/LsDeveloper-IA/crm-office ; https://github.com/Milsonyujiaoki/Dominio_notas | `Banco/consultas.py`; `main.js` | `GEEMPRE`, `GEEMPRE_CONTATO`; `efsaidas` x `efclientes` | sem licença |
| https://github.com/uppiapp/dominio-rea-accounting | `dominio_fo_schema.json` (413 nomes de tabelas `fo*`), `packages/interop-dominio` | Interoperabilidade por ARQUIVO (layouts posicionais "3" e "19") e lista de tabelas de Folha; REA = Resource-Event-Agent | MIT |

### A-1.9 Conflitos e discrepâncias entre fontes

| Tema | Conflito | Como tratar |
|---|---|---|
| `orig_lan = 5` | Comentário do banco e conferência por ligação 1:1 com `efsaidas_lancto` (REA): 5 = Escrita fiscal saídas. `cors4rio/dmf-data-engine` (`CT_visao_geral.md`): 5 = "Extrato Bancário" | Prevalece o comentário do banco + conferência; ler `CTORIGEM_LANCAMENTO` do banco real |
| Cancelada/denegada/inutilizada | `MAC:docs/FILA-CODE-2026-11-03-NOTAS-DUVIDAS.md` diz `situacao_ent` 2 a 5; leiaute oficial `CS:672` diz 2 cancelado, 7 denegado, 8 inutilizado | Medir `COUNT(*) GROUP BY situacao_*` no banco real e usar a legenda oficial |
| `vime_sim` | `IMP` chama de "base de ICMS"; comentário do banco: "Valor do imposto de entradas" | Usar `sdev_sim` (saldo a recolher) como o imposto; tratar `vime_sim` como imposto das entradas |
| `HRCLIENTE.I_CLIENTE_FIXO` | IMP afirma `= geempre.codi_emp`; REA só registra "Codigo do cliente fixo" | Validar por amostra no banco real |
| `autabelas` | Terceiros (Ylaros, rascunho do MAC) tratam como dicionário/"apelido"; REA mostra que é a lista de tabelas auditadas (895 de ~4,8 mil) | Não depender de `autabelas`; usar comentários do catálogo |
| Domínio Web | Central diz que não há conexão direta; um escritório relata liberação por IP fixo via chamado | Considerar caminho não documentado; exige chamado |
| Fonte removida | `AlexCaladoIntegra/portal-integra-sinc` (23 consultas, citado pelo rascunho MAC) devolve 404 | Itens apoiados só nela (ex.: `codi_imp` 44 Simples, 64 MEI, 183 IBS, 184 CBS) ficam sem fonte verificável |

---

## A-2. INFERÊNCIA (marcada como hipótese; precisa de teste no banco real)

1. **A legenda do "Situação da Nota" do leiaute oficial vale para `situacao_sai/ent/ser`.** Base: os valores observados no banco (0, 1, 2, 6, 7, 8, 9, 10) coincidem com a legenda do leiaute de importação (que alimenta essas tabelas) e com a legenda do SPED COD_SIT (REA notou a semelhança). Falta confirmar com contagem no banco do usuário.
2. **`RFED_PAR` (regime federal)**, deduzido por um terceiro a partir do que cada empresa apura (vigência mais recente): 5 ≈ Lucro Presumido, 4 ≈ Simples Nacional, 1 ≈ provável Lucro Real, 2 ≈ variante do Simples, 6/8/9 não determinados; `REST_PAR` 13 ≈ Simples Nacional. Legenda NÃO consta no banco. Fonte: REA:docs/modelo-parametro_fiscal.md. Para Simples, preferir `SIMPLESN_OPTANTE_PAR` (comentário do banco) e confirmar com a existência de apuração em `efsdoimp`/`efsdoimp_simples_nacional`.
3. **`CTORIGEM_LANCAMENTO` (29 linhas) é a legenda completa de `ctlancto.orig_lan`.** Base: nome da tabela ("Origem dos lançamentos da contabilidade", `I_ORIGEM`, `DESCRICAO`). O elo exato não foi documentado por nenhuma fonte.
4. **Separar empregado de contribuinte em `foempregados`**: candidatas `tipo_contrib` (E/F/A/R/M/S/I), `contrib_indiv`, `categoria` e `vinculo`. O comentário de `CS:8722` confirma que o cadastro mistura os três, mas nenhuma fonte diz qual coluna os separa.
5. **Pró-labore**: sai de contribuintes em `foempregados` + views `FOCONTRIBUINTES`/`FOCONTRBASES`/`FOCONTRMOVMES`; coluna do valor não identificada.
6. **Plano de contas compartilhado**: `ctlancto.CODI_EMP_PLANO` ("Empresa do plano de contas") sugere que a conta pode estar no plano de OUTRA empresa; join `ctcontas` apenas por `codi_emp` pode perder contas. Não verificado.
7. **Relatórios salvos (`RELATORIOS`, `DEFSELECT`, `COLSSELECT`...)** e os `.bgr` oficiais contêm SQL real do Domínio; poderiam servir de biblioteca de consultas validadas pelo fornecedor. Não inspecionado.
8. **HRCLIENTE ↔ geempre**: o escritório é uma `geempre`; `hr*.CODI_EMP` = código do escritório; cliente que também é empresa aparece com `I_CLIENTE_FIXO` = `codi_emp`. Só o skill do imperialBi afirma.
9. **Matriz/filial**: agrupar pela raiz do CNPJ (8 dígitos) de `cgce_emp`; fonte original (F4/F5 do rascunho MAC) em parte removida.
10. **Janela de atualização do Domínio Web (10h, 12h, 16h, 19h ou 24 h)** é dito por terceiro como "quem integra com o Domínio Web fala em"; sem fonte oficial.

## A-3. NÃO ACHEI

| O que | Busca feita |
|---|---|
| Dicionário oficial PÚBLICO (HTML/PDF) com todas as tabelas e colunas do Domínio | WebSearch "Gerador de Relatórios Domínio SQL consulta tabelas banco de dados bethadba" (domínios Domínio/TR); "Busca Tabelas Domínio dicionário de dados..." (aberta); "Treinamento Relatórios Personalizados ... apostila fonte de dados tabelas colunas" (domínios Domínio/TR); leitura de CS:3227, 6464, 10237, 6773, 7082, 6465, 8276, 8277, 7, 8722, 4068. Só a ferramenta Busca Tabelas (zip) e os comentários dentro do banco |
| PDF/manual público que descreva tabelas/colunas | Resultados com PDFs do Domínio (`ebook_dominio_web.pdf`, `ebookescritafiscalfinal.pdf`, `manualdefis.pdf`) são manuais de uso; títulos vistos, conteúdo NÃO lido |
| Legenda oficial de `RFED_PAR`, `REST_PAR` = 13, `tipo_process` 60/61/92, `forescisoes.motivo` | Não consta no banco; nenhuma página da Central lida a traz |
| Documento público sobre cópia D-1 do Domínio Web / IP fixo | WebSearch "Central de Soluções Domínio Web cópia do banco de dados IP fixo acesso ao banco Power BI Domínio Web usuário externo" (só CS:3227 e CS:6994, que dizem não haver conexão direta) |
| Conteúdo SQL dos `.bgr` oficiais | Não baixei arquivos |
| Tabela principal da Redução Z; tabela de pró-labore | Inventário: nomes `*REDUCAO_Z*` encontrados (configuração/contabilização); principal não identificada |
| Código público com `bethadba` + LLM (openai/anthropic/claude/langchain) por busca de código | `gh search code` com dois termos devolve vazio (limitação); `mcp__grep__searchGitHub` 0 resultado até para termos que existem. Achados de IA vieram de busca de repositórios e de navegação direta (B-1.2) |

---

# PARTE B — IA / MCP / LLM COM O DOMÍNIO

## B-1. CONFIRMADO EM FONTE

### B-1.1 IA do próprio Domínio / Thomson Reuters

| Produto | O que faz (conforme a fonte) | Lê o banco? Expõe API/MCP? | Fonte | Nível |
|---|---|---|---|---|
| **Domínio IA** (lançado no SYNERGY 2026, São Paulo, 30/09–01/10/2026) | IA generativa dentro de Folha, Escrita Fiscal e Contabilidade; perguntas em linguagem natural sobre relatórios, dados e documentos "sem exportar planilhas"; "Converse com o relatório" (balancetes/demonstrações), BIs personalizados, conferência de eSocial/DCTFWeb, leitura de PDF para parametrizar rubricas, mapeamento do Plano Referencial (>80% automatizado, alegação da empresa), diagnóstico da Reforma Tributária | "Opera com contexto embarcado nos módulos"; se usa banco direto, API ou apenas contexto das telas: NÃO consta. API/MCP/integração com terceiros: NÃO consta. Preço e disponibilidade: NÃO constam. LLM usado: NÃO consta | https://inforchannel.com.br/2026/10/01/dominio-ia-une-inteligencia-artificial-e-conhecimento-tributario-da-thomson-reuters/ ; https://portalerp.com/br/noticia/thomson-reuters-lanca-dominio-ia-para-automatizar-rotinas-e-analisar-dados-contabeis ; https://sitecontabil.com.br/utilitarios2/noticias-ler.php?id=15068 ; https://www.dominiosistemas.com.br/atrinca2026/ | imprensa + página comercial do fornecedor |
| **Domínio Messenger** (plano Max) | "Centralização de atendimento via WhatsApp integrado ao Domínio IA que executa mais de 25 tarefas" (tarefas não listadas) | Não detalha; a única menção a API é "Importação via API automática" na Escrita Fiscal (não é API pública para desenvolvedores) | https://www.dominiosistemas.com.br/solucoes/dominio-max/ | OF (página comercial) |
| **TRIA** (Thomson Reuters Inteligência Artificial) | Lançada em 2019 como chatbot sobre eSocial/EFD-Reinf integrado ao Domínio; em 2026 descrita como assistente de atendimento, apoio a parâmetros de cálculo, inconsistências em lançamentos fiscais, mudanças legislativas | Não menciona banco/API/MCP. Relação exata TRIA x Domínio IA NÃO esclarecida | https://www.contabeis.com.br/noticias/75989/conheca-4-sistemas-contabeis-com-inteligencia-artificial-no-brasil/ (07/04/2026) ; https://tiinside.com.br/en/29/05/2019/thomson-reuters-lanca-tria-primeira-ferramenta-de-ia-para-contadores/ (lido só pelo resumo da busca; o fetch devolveu 403) | imprensa |
| **Contabilidade Digital** (e, na mesma página, o módulo Contabilidade com "Dashboard com indicadores e análises contábeis") | Extratos bancários via Open Finance para baixa automática nos módulos Folha/Escrita Fiscal (integração nativa com bancos) | Não expõe dados a terceiros; nenhuma menção a API pública, ODBC ou MCP | https://www.dominiosistemas.com.br/solucoes/dominio-max/ ; resultado de busca da Central (CS:11689) | OF |
| **API oficial** | Envio de lote XML e lista de clientes integráveis (já conhecido; não refeito) | — | CS:8476 | OF |
| Thomson Reuters (global) | CoCounsel Legal tem conector MCP (piloto, tool única "Ask CoCounsel", termos proíbem repassar conteúdo a outra IA de terceiros) e HighQ tem servidor MCP; CoCounsel agêntico para Tax/Audit/Accounting (17/11/2026) NÃO cita MCP, Brasil, Domínio ou Onvio | Nada para Domínio/Onvio | https://www.thomsonreuters.com/en-us/help/cocounsel/legal/integrations/mcp-connector/cocounsel-legal-mcp-connector ; https://www.thomsonreuters.com/en-gb/help/highq/highq-mcp/overview ; https://www.thomsonreuters.com/en/press-releases/2026/november/thomson-reuters-brings-cocounsel-agentic-ai-to-the-tax-and-compliance-products-professionals-trust | páginas TR (as duas primeiras vistas só em resultado de busca) |

### B-1.2 Terceiros brasileiros que conectam no banco/arquivos do Domínio

**Servidores MCP / plugins para Claude sobre o Domínio**

| Projeto | O que é | Status e licença | Fonte |
|---|---|---|---|
| `compucel/dominio-ponte` (pacote `@cabeda/dominio-ponte`) | Servidor MCP local, somente leitura, stdio. Ferramentas `executar_consulta` e `status_conexao` (`readOnlyHint: true`). Travas: um comando por chamada, só `SELECT`/`WITH`, recusa INSERT/UPDATE/DELETE/MERGE/CREATE/ALTER/DROP/INTO/SET/CALL/EXECUTE/LOAD/UNLOAD/OUTPUT/OPENSTRING e `xp_`/`sa_`/`sp_`, só tabelas `bethadba.*` e `sys.*` (ou CTE), sem funções no FROM, máx. 5.000 linhas e 60 s (teto 120 s), registro local sem conteúdo das linhas, aviso de que texto dos campos é dado de terceiro. Conecta por DSN ODBC (padrão `Contabil`, `CharSet=UTF-8`). Protege com "usuário de banco somente leitura (ex.: EXTERNO)" como trava principal | MIT. Criado em 02/11/2026; 2 execuções de CI com sucesso; sem tags; **o pacote NÃO está no npm** (consulta ao registry em 20/11/2026: "Not found"), embora o plugin o invoque com `npx -y @cabeda/dominio-ponte@0.1` | https://github.com/compucel/dominio-ponte ; PONTE:src/guarda.ts ; PONTE:src/index.ts ; PONTE:src/banco.ts ; PONTE:.github/workflows/publicar.yml |
| `compucel/dominio-plugin` (marketplace `cabeda`, plugin `dominio`) | Plugin do Claude Code/Desktop: skill `auditoria-dominio` + `.mcp.json` com a ponte local e o "Conector Domínio" remoto (`https://mcp.cabeda.com.br/mcp`, HTTP). O conector (da Cabeda Contabilidade, exige cadastro e licença) fornece "mapa das tabelas e consultas prontas": ferramentas `listar_assuntos`, `obter_mapa`, `obter_consulta`; a skill manda executar SQL recebido do conector sem edição e proíbe escrever SQL próprio. A política de privacidade diz que o conector não recebe dados do banco | `plugin.json`: "Proprietary"; GitHub: sem licença. Sem página pública do produto (www.cabeda.com.br só tem formulário de contato). O endpoint `mcp.cabeda.com.br/mcp` existe (GET devolve HTTP 405) | https://github.com/compucel/dominio-plugin ; PLUG:.claude-plugin/plugin.json ; PLUG:.mcp.json ; PLUG:skills/auditoria-dominio/SKILL.md ; PLUG:PRIVACIDADE.md |
| `Lucas-Bueno04/REA_DOMINIO_DB` | "Mapear o banco do Sistema Domínio (SQL Anywhere 17, banco Contabil) por engenharia reversa e expô-lo como servidor MCP somente leitura". Servidor `dominio-db`: 13 ferramentas (descoberta: `buscar_entidades`, `descrever_entidade`, `buscar_tabelas`, `descrever_tabela`, `relacionamentos`, `caminho_entre`; consulta: `consultar_entidade`, `consultar_tabela`; prontas: `balancete`, `contas_a_receber`), 2.117 entidades de negócio (≈90-107 curadas e conciliadas com totais do Domínio, o resto gerado em lote com "fatos medidos"), biblioteca de ~4.900 tools por tabela com perfil "compacto" de 3 ferramentas de gateway (`buscar_ferramentas` → `descrever_ferramenta` → `executar_ferramenta`). Somente leitura em três camadas (só SELECT/WITH, valores sempre parametrizados e identificadores validados contra o catálogo, usuário do banco sem escrita), bloqueio de credenciais, limites (500 linhas, 40 colunas, 60 s), auditoria em JSONL, 61 testes. Modo HTTP sem autenticação (aviso explícito). Sem mascaramento de dado pessoal nesta versão | Sem licença; documento de descobertas datado de 15/10/2026, último push em 19/10/2026 | https://github.com/Lucas-Bueno04/REA_DOMINIO_DB ; REA:docs/uso-mcp.md ; REA:docs/descobertas-rea.md ; REA:config/seguranca.yaml ; REA:docs/biblioteca.md |

**Skills/fluxos com Claude Code sobre o Domínio (não são MCP)**

| Projeto | O que é | Fonte |
|---|---|---|
| `salesgordo0022/imperialBi` | Skill `dominio-servidor-sap` para o Claude conectar e extrair do banco do Domínio (kit PowerShell + Node, driver SQL Anywhere 17, 6 relatórios Excel). Ensina o fluxo, conexão, armadilhas e "onde mora cada dado" | https://github.com/salesgordo0022/imperialBi (sem licença) |
| `macedo-reis-contabilidade/macedo-reis-dashboards` | Escritório que usa Claude Code com "filas" de tarefas (`docs/FILA-CODE-*.md`, `CLAUDE.md` de 440 KB), "ponte" Python/pyodbc que lê o Domínio Web e envia só totais por empresa/mês a um sistema (Supabase) | https://github.com/macedo-reis-contabilidade/macedo-reis-dashboards (sem licença) |

**BI, ETL, RPA e arquivos**

| Tipo | Projeto/fonte | Observação |
|---|---|---|
| Power BI / Excel por ODBC | Oficial: CS:3227 (Power BI, Excel, DBeaver, Microsoft Query). Terceiros: https://github.com/Ylaros/Dashboard-Balancetes-Power-BI ; https://www.hugoventurini.com.br/post/conectando-o-power-bi-desktop-ou-o-excel-ao-banco-de-dados-sybase (04/06/2023, atualizado 27/10/2023: driver SQL Anywhere 17 do cliente SAP; 16 não funciona no conector nativo do Power BI, mas funciona no ODBC; DSN de sistema; sem nomes de tabela) | Conector nativo "Sybase" do Power BI é frágil; ODBC é o caminho (relato em https://community.fabric.microsoft.com/t5/Desktop/Conecting-DB-in-Sybase/m-p/901196, visto só em resultado de busca) |
| ETL para outro banco | https://github.com/ElderVivot/bi-lanc-contabil-folha-dominio (Mongo para BI); https://github.com/DeveloperOffice/gestk-back e https://github.com/gabrielcsilvaa/gestao-office-back (Django + pyodbc); https://github.com/LsDeveloper-IA/crm-office | Mesmo padrão: ODBC + SELECT por empresa/período |
| RPA / web scraping | https://github.com/Renata5207418/Postagem-de-Arquivos (RPA de postagem em pastas de cliente no Domínio desktop); https://github.com/imguisilva/automatizacao-esocial (RPA de eSocial dentro do Domínio); https://github.com/ElderVivot/onvio-webscraping | Automação de tela, não de banco |
| Arquivos no leiaute do Domínio | Leiaute oficial: CS:672 ("Domínio Sistemas com Separador", pipe `\|`, registros 0000 a 7170), CS:6055, CS:2095, CS:3554; terceiros que geram/consomem: https://github.com/roneferrera/Conversor-Leiautecomseparadordominio (MIT), https://github.com/convenia/dominio-employee-export (MIT), https://github.com/Brunonascm/convECD, https://github.com/EttorePaludeto/LineIN_ExportadorTxtDominio, https://github.com/uppiapp/dominio-rea-accounting (MIT, layouts posicionais) | Integração por arquivo/API de importação, não pelo banco |
| API oficial (Delphi) | https://github.com/tiagoistuque/IntegracaoDominioThomsomReuters (MIT, 2022) | Já coberto pelo que o usuário sabe |
| ERPs/fiscais que enviam ao Domínio | Conta Azul ("ERP homologado para o ecossistema Domínio", envio automático) https://contaazul.com/contadores/dominio/ ; Jettax (API leva a nota "para dentro da Domínio") https://www.jettax.com.br/?p=30045 | Integração por API/arquivo; não por banco |
| Instalação do banco | https://github.com/hudsonoli/sybase17-ubuntu22.04 ("Instalação e configuração do Sybase17 Domínio Contábil"); https://github.com/tecluizgustavo/dominio-auto-update (PowerShell) | Encontrados na busca de repositórios; NÃO lidos |

### B-1.3 MCP/registries para ERPs e sistemas contábeis brasileiros

| Servidor | Vendor / autor | Escopo | Licença / status | Fonte |
|---|---|---|---|---|
| **Omie (oficial)** | Omie | MCP remoto `https://api.omie.com.br/mcp`; leitura E escrita (baixas, inclusões, faturamento; aprovação adicional para pagamentos, negativação, exclusões); login com e-mail/senha do Omie; rótulo "Comunidade" no diretório do Claude; funciona em Claude desktop/web/mobile e Claude Code | Proprietário/hospedado; ajuda atualizada "essa semana" | https://ajuda.omie.com.br/pt-BR/articles/17173377-conectando-o-omie-ao-claude-mcp (aberta e lida) ; https://jornalcontabil.com.br/noticia/omie-integra-erp-a-chatgpt-claude-e-grok-para-automatizar-rotinas-de-pmes/ (só vista em resultado de busca) |
| Omie (terceiros) | `codespar/mcp-omie` (30 tools); `mcp-dir/omie-mcp` (pagar/receber, financeiro, NF-e) | Chave de API Omie | MIT; no registry oficial | https://github.com/codespar/mcp-dev-brasil ; https://github.com/mcp-dir/omie-mcp |
| Conta Azul | `douglac/contaazul-mcp` (35 tools, OAuth 2.0, lê e escreve); `codespar/mcp-conta-azul` (20 tools) | Vendas, clientes, financeiro, NF-e | MIT; no registry oficial | https://github.com/douglac/contaazul-mcp ; https://github.com/codespar/mcp-dev-brasil |
| Bling / Tiny | `mcp-dir/bling-mcp` (API v3, OAuth); `codespar/mcp-bling` (28 tools); `codespar/mcp-tiny` (21 tools) | Pedidos, produtos, financeiro, NF-e, estoque | MIT | https://github.com/mcp-dir/bling-mcp ; https://github.com/codespar/mcp-dev-brasil |
| Fiscal (emissão/consulta) | `BrasilNFe/brasilnfe-mcp` (NF-e/NFC-e/NFS-e/CT-e/MDF-e), `br.com.foxnfe/mcp`, `codespar/mcp-focus-nfe`, `codespar/mcp-nfe-io`, `cmendezs/mcp-nfe-br`, `SamuelMoraesF/mcp-nfse-nacional` (consulta NFS-e no portal nacional), `br.com.emissaoja/nfse`, família `mcp-dir/sefaz_*` e `receita_federal_nfse*` (consulta paga por uso) | Emissão ou consulta; não são ERPs contábeis | Variadas (MIT, Apache-2.0, "other", sem licença) | https://registry.modelcontextprotocol.io/v0/servers?search=nfse ; https://github.com/BrasilNFe/brasilnfe-mcp ; https://github.com/cmendezs/mcp-nfe-br ; https://github.com/SamuelMoraesF/mcp-nfse-nacional |
| Jettax (plataforma fiscal) | Jettax | "MCP da Jettax" para ChatGPT/Claude/Gemini sobre notas de venda, compra e serviço e cadastro das empresas da carteira, com token por escritório; 16/10/2026 (atualizado 20/10/2026). A página NÃO liga o MCP ao Domínio | Comercial; leitura/escrita não informada | https://www.jettax.com.br/?p=30045 |
| Apex ERP Contábil | `io.github.ogconstrutorasp/apex-contabil` (framework MCP: CNAEs, jurídico, obrigações, financeiro, marketing, WhatsApp) | ERP contábil próprio de um terceiro; repositório informado (`ogconstrutorasp/apex-mcp-framework`) não resolveu na API do GitHub (404) | v1.1.1 no registry oficial | https://registry.modelcontextprotocol.io/v0/servers?search=contab |
| Dados públicos BR | `SidneyBissoli/ibge-br-mcp`, `SidneyBissoli/bcb-br-mcp`, `alanpcf/brasil-data-mcp`, `Regenerating-World/pix-mcp` (lista awesome); `io.github.dan94k/brazilian-dev-mcp` (CPF/CNPJ/CEP, registry oficial) | Fontes públicas e utilitários | licenças não verificadas | https://github.com/punkpeye/awesome-mcp-servers ; https://registry.modelcontextprotocol.io/v0/servers?search=brazilian |

Verificações negativas feitas (registry oficial, `registry.modelcontextprotocol.io/v0/servers?search=<termo>`): `alterdata`, `questor`, `prosoft`, `dominio` (só resultados sem relação, ex.: "dominion"), `contabilidade`, `folha`, `escrita fiscal`, `sql anywhere`, `sybase`, `odbc`, `sped`, `esocial`: 0 resultado relevante. `nibo`: 4 resultados, nenhum é o Nibo contábil. Diretório de conectores do Claude (`mcp__mcp-registry__search_mcp_registry` com omie/dominio/contabil/alterdata/nfe brasil): só conectores sem relação.

## B-2. INFERÊNCIA

1. **Domínio IA não deve expor o banco a terceiros.** As matérias falam em "contexto embarcado" e em "sem exportar planilhas"; nenhuma menciona API/MCP. Portanto um MCP sobre o banco não conflita nem substitui o Domínio IA, mas depende do usuário Externo (Domínio Local) ou de liberação por chamado (Web).
2. **Três arquiteturas de MCP coexistem** (inferência a partir dos projetos): (a) SQL livre com guarda (`dominio-ponte`), (b) entidades/tools parametrizadas em cima de um modelo curado (`REA_DOMINIO_DB`), (c) conhecimento do banco servido como dado por um conector remoto e execução local (Cabeda). O repositório dominio-plugin sugere que o diferencial comercial é o "mapa + consultas prontas", não a ponte.
3. **O `.mcp.json` do plugin Cabeda hoje falha** na etapa `npx @cabeda/dominio-ponte@0.1` se o pacote não estiver no npm; pode haver outro canal de instalação não público.
4. **Nenhum ERP contábil BR de mesa (Domínio, Alterdata, Questor, Prosoft, SCI)** tem MCP público; os MCPs encontrados são de ERPs em nuvem com API (Omie, Conta Azul, Bling, Tiny). Por isso o banco por ODBC é o único caminho de dados do Domínio Local para IA, fora a API de lote XML.

## B-3. NÃO ACHEI

| O que | Busca feita |
|---|---|
| MCP/API oficial do Domínio ou da Onvio para IA de terceiros | WebSearch "Thomson Reuters CoCounsel MCP server ... Onvio accountants" (só CoCounsel Legal e HighQ); WebFetch das páginas Domínio Max e ATrinca 2026 (nenhuma menção a MCP/ODBC/API aberta); comunicado TR de 17/11/2026 (sem MCP/Brasil/Domínio/Onvio) |
| MCP para Alterdata, Questor, Prosoft, SCI, Nibo | WebSearch "MCP Alterdata Questor Prosoft SCI Nibo ERP contábil ..." (nenhuma menção); registry oficial por `alterdata`, `questor`, `prosoft`, `nibo`; listas awesome (punkpeye/appcypher/wong2) com busca por palavra |
| Página pública do "Conector Domínio" da Cabeda | WebSearch "Cabeda Contabilidade Conector Domínio Claude plugin" (0 resultados); www.cabeda.com.br (só formulário de contato) |
| Pacote npm `@cabeda/dominio-ponte` | `registry.npmjs.org/@cabeda%2Fdominio-ponte` ("Not found") e busca `@cabeda` (0 objetos) em 20/11/2026 |
| Metabase/Qlik/Grafana ligados ao Domínio; text-to-SQL; chatbot que consulta o banco do Domínio | WebSearch "Metabase OR Qlik OR Grafana "SQL Anywhere" "Domínio Sistemas" ..." (só conector gerenciado de SQL Anywhere da Peliqan, sem relação com Domínio); WebSearch "automação RPA integração banco de dados Domínio Sistemas ... text-to-SQL" |
| Startups/empresas BR com produto de IA conectado ao banco do Domínio | Além dos projetos de GitHub acima (de escritórios e desenvolvedores individuais), nenhuma empresa com produto próprio foi achada; Jettax e Conta Azul integram por API/arquivo |
| Fonte do guia "hugoventurini" por busca | WebSearch não achou; a URL do post (citada em rascunho de terceiro) foi aberta diretamente e confere |

---

# PARTE C — IMPLICAÇÕES PARA UM MCP SOMENTE-LEITURA (todas INFERÊNCIA, cada uma com o achado de apoio)

1. **Bootstrap do dicionário a partir do catálogo vivo** do banco do usuário (tabelas, colunas, tipos, PK, FKs declaradas ~6,7 mil, comentários de tabela e de coluna, permissões), em vez de embutir um dicionário copiado de terceiros (apoio: A-1.2; risco jurídico/licença em A-1.8). Re-gerar a cada atualização de versão do Domínio.
2. **Camada de entidades/ferramentas parametrizadas** em vez de SQL livre, ou SQL livre apenas com guarda forte; os dois modelos existem (apoio: B-1.2). Modelo em camadas do REA: descoberta (buscar entidade/tabela, relacionamentos, caminho entre tabelas) + consulta + prontas (balancete, receita) + gateway de 3 ferramentas para não inflar o contexto com milhares de tools.
3. **Denylist de tabelas e colunas de credencial** (A-1.7), porque o Externo lê quase tudo; mais denylist de pessoais por padrão (empregados, sócios, contatos, CPF) com mascaramento ou agregação.
4. **Limites no próprio MCP**: máx. linhas (50 padrão/500), máx. colunas, timeout controlado fora do driver (atributo ODBC não aceito), filtro obrigatório por `codi_emp` e por período em tabelas grandes (`ctlancto`, `efsdoimp`, `efmvspro`, `fobasesserv`, `audados`), agregar no servidor (A-1.6).
5. **Driver**: `fetchSize` 1 ou equivalente, nada de atributos de modo somente leitura/timeout do ODBC, charset windows-1252, DSN de sistema/64 bits (A-1.1, A-1.6). Testar com o driver 17 do cliente SAP.
6. **Regras de qualidade do dado embutidas nas consultas**: filtrar faixa de datas, ISNULL em somas, `dias_servico > 0`, situação/cancelada, `versao_nat`, segmentos de nota, vigência em vigor (A-1.3/A-1.6).
7. **Legendas de código lidas do banco quando existirem** (comentários, `CTORIGEM_LANCAMENTO`, `GEMODULOS`) e marcadas por nível de confiança (confirmado/parcial/hipótese), como no REA, com a legenda oficial de situação da nota do leiaute (A-1.5).
8. **Registro de auditoria** de cada chamada, sem conteúdo de linhas (padrão dos dois projetos) e saída tratada como dado de terceiro (aviso anti-injeção de prompt do `dominio-ponte`).
9. **Domínio Web**: o caminho oficial não existe; avaliar chamado ao suporte para IP fixo e testar a janela de atualização (A-1.1).
10. **Não redistribuir** catálogo copiado nem binários do SAP (A-1.8).

---

# APÊNDICE

## Buscas executadas (resumo)

- Central de Soluções (HTML baixado em `...\scratchpad\dl_central`; 10444 e 10985 lidos por WebFetch): 3227, 2811, 10444, 6994, 9889, 7159, 672, 6055, 2095, 3554, 6464, 6465, 6466, 6773, 7082, 7, 8722, 8276, 8277, 4068, 10237, 32, 4576, 10162, 10985, 1105, 2798, 9069 (inativa). As páginas 32, 4576, 10162, 10985, 1105, 2798, 7159 e 9889 não trouxeram nada sobre o banco (folha, importação NFS-e, DCTFWeb, exclusão de empresa, backup, erro de conexão); a 9889 é marcada "Uso Interno" e não foi usada como fonte.
- GitHub: `gh search code` (bethadba, geempre, efsaidas, ctlancto, foempregados, efentradas); `gh search repos` (bethadba, dominio sistemas, dominio contabil, dominiosistemas, dominio thomson reuters, onvio dominio...); leitura por `gh api` de árvores/blobs; `mcp__grep__searchGitHub` (0 resultado).
- Registry oficial MCP: termos omie, bling, nibo, alterdata, questor, prosoft, contaazul, conta-azul, dominio, contabil, contabilidade, nfe, nfse, sped, sefaz, cnpj, brasil, brazil, totvs, sankhya, asaas, onvio, thomson, odbc, sybase, sqlanywhere, esocial, contador, simples, erp, accounting, brazilian.
- Listas awesome: punkpeye, appcypher, wong2, modelcontextprotocol/servers, TensorBlock (busca por palavra).
- Web: Domínio IA/TRIA/CoCounsel/MCP/Omie/Jettax/Conta Azul; Power BI/Sybase; RPA/text-to-SQL; Metabase/Qlik/Grafana.
