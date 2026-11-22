# Mapa do banco do Domínio (medido em 21/11/2026)

Base da [spec do MCP do Domínio](specs/dominio-mcp.md). Fonte dos números: catálogo do SQL Anywhere 17 (`SYS.SYSTAB`, `SYSTABCOL`, `SYSREMARK`, `SYSIDX`, `SYSIDXCOL`, `SYSFKEY`) lido pelo DSN de sistema 64 bits `contabil` com o usuário Externo, mais `SELECT … WHERE 1=0` para saber o que ele consegue ler. **Nenhum dado de negócio foi lido ou impresso.** Contagens de linhas são a estimativa do catálogo (`SYSTAB.count`), não `COUNT(*)`.

Itens marcados **(terceiro)** vêm de fontes públicas de terceiros listadas na [pesquisa](pesquisa/dominio-mcp-pesquisa-externa.md) e precisam de conferência no banco antes de virar regra; os demais foram medidos aqui.

## O banco se autodocumenta

| Medida | Valor |
|---|---|
| Objetos do dono `bethadba` | 4.964 (4.862 tabelas base, 102 views) |
| Legíveis pelo usuário Externo | 4.946 (18 negados) |
| Colunas em tabelas e views de usuário | 58.745, das quais **54.472 com comentário (92,7%)** |
| Comentários de tabela | 4.860 |
| Chaves primárias / estrangeiras / índices | 4.821 / **6.803** / 12.768 |
| Tabelas base com `codi_emp` | 3.879 de 4.862 |
| Colunas com legenda no comentário (2 ou mais pares "código - rótulo") | 1.711 |
| Colunas / tabelas marcadas como não usadas no comentário | 54 / 5 |

O comentário traz a legenda dos códigos (ex.: `geempre.tins_emp`: "1 - CNPJ/2 - CPF/3 - CEI/6 - CAEPF") e avisos ("Campo nao utilizado", "Este campo nao e mais usado a partir da versao 6.1A-01"). Falha conhecida: o comentário de `situacao_sai`, `situacao_ent` e `situacao_ser` diz "Codigo do modelo do documento fiscal", mas o campo guarda a situação da nota (**terceiro**; ver legendas abaixo).

## Módulos (prefixo do nome da tabela)

| Prefixo | Módulo | Tabelas legíveis | Linhas (estimativa) |
|---|---|---|---|
| ef | Escrita Fiscal | 2732 | 9.236.756 |
| fo | Folha de Pagamento / eSocial | 745 | 9.463.721 |
| ge | Geral (cadastros comuns, atendimento, usuários) | 397 | 3.245.440 |
| ct | Contabilidade | 389 | 2.448.046 |
| hr | Honorários (atual) | 147 | 81.904 |
| lr | Lalur/LACS (novo) | 129 | 10.784 |
| pm | Patrimônio (novo) | 52 | 3.040 |
| po | Ponto Eletrônico | 42 | 2.115 |
| rg | Registro | 35 | 1.611 |
| pc | Processos | 28 | 1.147 |
| hn | Honorários (legado) | 26 | 3 |
| la | Lalur/LACS (antigo) | 24 | 1.634 |
| au | Auditoria | 17 | 25.984 |
| ho | Honorários (legado) | 12 | 0 |
| pa | Patrimônio (antigo) | 12 | 44 |
| pr | Protocolos | 11 | 1 |

Também existem `rg` Registro, `pc` Processos, `pr` Protocolos e `au` Auditoria (configuração e movimento de auditoria, **não** o dicionário). Famílias grandes: `EFSDOIMP_*` (285 tabelas, muitas por UF e obrigação estadual), `EFIMPORTADOR_FIXO_*` (configuração do importador) e `FOESOCIAL_*`.

## Tabelas centrais

Ordenadas por quantas chaves estrangeiras apontam para elas somadas ao volume, com penalidade para nome de tabela filha (`efsaidas` ganha de `efsaidas_nfp`). É o mesmo sinal que o MCP usa para não afogar a busca em tabelas auxiliares.

| Tabela | Descrição no banco | Linhas | FKs que apontam |
|---|---|---|---|
| `geempre` | Empresa - Cadastro | 630 | 1139 |
| `ctlancto` | Lancamentos Contabeis | 269.328 | 181 |
| `EFACUMULADOR` | Acumuladores - Cadastro | 144.807 | 164 |
| `efprodutos` | Produtos - Cadastro | 53.495 | 185 |
| `efsaidas` | Notas Fiscais de Saida | 386.290 | 82 |
| `efsdoimp` | Saldo dos Impostos | 37.539 | 136 |
| `efmvspro` | Notas Fiscais de Saida - Produtos | 917.584 | 46 |
| `efnatureza` | Naturezas - Cadastro | 1.545 | 220 |
| `ctcontas` | Contas Contabeis - Cadastro | 308.751 | 42 |
| `ctlanctolote` | Lancamento em lote | 263.873 | 43 |
| `efentradas` | Notas Fiscais de Entrada | 31.691 | 73 |
| `geimposto` | Impostos | 75.707 | 47 |
| `efmvepro` | Notas Fiscais de Entrada - Produtos | 55.421 | 50 |
| `foempregados` | Empregados - Cadastro | 995 | 135 |
| `gemunicipio` | Cadastro de municipios | 5.571 | 71 |
| `focalculos` | Calculo - Sequencia de calculos | 31.533 | 39 |
| `efclientes` | Clientes - Cadastro | 19.916 | 44 |
| `foeventos` | Eventos - Cadastro | 175.315 | 17 |
| `effornece` | Fornecedores - Cadastro | 5.789 | 45 |
| `efservicos` | Notas Fiscais de Servico | 15.534 | 33 |
| `efajustes` | Ajustes - Cadastro | 13.510 | 31 |
| `foservicos` | Servico - Cadastro | 736 | 42 |
| `fomovtoserv` | Movimentacao - Calculo | 140.977 | 7 |
| `efoutrosdados` | Outros dados | 1.108 | 32 |
| `efgrupopdi` | Grupos de Produtos - Cadastro | 526 | 35 |
| `efespecies` | Especies - Cadastro | 42 | 67 |
| `efunidades` | Unidades de medida - Cadastro | 223 | 33 |
| `gepais` | Cadastro de paises | 272 | 31 |
| `fofiliais` | Filiais - Cadastro | 619 | 24 |
| `GEATENDIMENTOACOES` | Ações a serem enviadas para o Domínio Atendimento | 606.164 | 2 |
| `efsdopro` | Saldo dos Produtos | 451.764 | 2 |
| `ctccusto` | Cadastro - Cadastro de centro de custos da contabilidade | 229 | 26 |
| `rgeventos` | Eventos - Cadastro | 557 | 19 |
| `fosindicatos` | Convenção Coletiva - Cadastro | 66 | 35 |
| `fobasesserv` | Bases - Calculo | 26.199 | 5 |
| `efinformativos` | Informativos | 82 | 31 |
| `gecnae20` | Tabela do CNAE 20 | 1.350 | 11 |
| `HRCONTRATO` | Contrato | 507 | 15 |
| `foguiainss` | Guia de INSS | 4.911 | 7 |
| `geestado` | Cadastro de estados | 28 | 36 |
| `focalculosbases` | Calculos - Bases de calculos | 436.536 | 1 |
| `FOAFASTAMENTOS` | AFASTAMENTOS DOS EMPREGADOS | 2.495 | 8 |
| `foccustos` | Centro de Custos - Cadastro | 1.718 | 9 |
| `fofilhos` | Empregados - Cadastro - Dependentes | 353 | 15 |
| `HRCLIENTE` | Clientes Fixos e Eventuais | 508 | 13 |
| `gesocios` | Socios - Cadastro | 797 | 11 |
| `HRFATURAMENTO` | Faturamento | 4.744 | 6 |
| `usConfUsuario` | usConfUsuario | 51 | 26 |

## Convenções de nome

- Prefixo de dois caracteres = módulo. Sufixo da coluna = abreviação da tabela: `_emp` (`geempre`), `_sai` (`efsaidas`), `_ent` (`efentradas`), `_ser` (`efservicos`), `_for`, `_cli`, `_lan` (`ctlancto`), `_cta` (`ctcontas`), `_par` (`efparametro_vigencia`). Tabelas novas usam nomes longos sem sufixo (`DATA_ITEM`, `HISTORICO`). **(terceiro)**
- `codi_emp` é a chave de empresa em quase tudo. Cada CNPJ, matriz ou filial, é um `codi_emp` próprio; não há vínculo entre filiais no cadastro (agrupar pela raiz de 8 dígitos). **(terceiro)**
- Em Honorários (`hr*`), `CODI_EMP` é o **escritório** (ele também é uma empresa em `geempre`) e o cliente é `I_CLIENTE`. **(terceiro)**
- Tabelas `*_VIGENCIA` têm a data de vigência na chave primária; a vigência em vigor numa data é a de maior `vigencia` menor ou igual à data, por empresa. O repo já usa isso em `contracts/datasets/taxation.v1.sql`.
- `origem_reg`: 0 Sistema, 1 Importação de tabelas, 2 Importação por leiaute, 3 Importação de tabelas concorrentes. **(terceiro)**
- Views com prefixo "V" (`FOVGUIAINSS`, `FOVBASES`) vêm sem comentário.

## Armadilhas de dado e de driver

| Armadilha | Como foi sabida |
|---|---|
| `efsaidas` e `efentradas` têm uma linha por **segmento** da nota (índice inclui `segi_sai`); somar sem tratar o segmento duplica ou divide | **terceiro**; reconferir contra relatório do Domínio antes de publicar `movimento_fiscal` |
| `cancelada_sai` (S/N) é independente de `situacao_sai`; usar as duas | **terceiro** |
| Datas com lixo (1979, 8320): filtrar faixa em `MIN`/`MAX` | **terceiro** (duas fontes) |
| `SUM(a + b)` vira NULL se uma parcela for NULL: usar `ISNULL` | **terceiro** |
| `DISTINCT` com `ORDER BY` exige os aliases do `SELECT` (erro -854); não existe `DATE_TRUNC`; existem `TOP n START AT m`, `LIST()`, `ISNULL`, `CURRENT DATE`, `DATEADD` | **terceiro** |
| `ctlancto.codi_usu` é o nome do operador, não um código | **terceiro** |
| ODBC recusa atributo de timeout de consulta (`HYC00`); `cursor.cancel()` por outra thread interrompe e a conexão continua usável | **medido** |
| `CharSet=UTF-8` com decodificação cp1252 gera "Ã§" no lugar de "çã"; a conexão padrão já entrega os acentos certos | **medido**, por ponto de código |
| Ler linha a linha pelo ODBC em base grande é lento (cerca de 60 linhas por minuto num caso de 30 GB); agregar no servidor | **terceiro** |

## Legendas

| Coluna | Legenda | Confiança |
|---|---|---|
| `geempre.stat_emp` | A Ativa, I Inativa, C Em constituição, M Ativo sem movimento, B Em processo de baixa, E Excluindo | comentário do banco (parcial) + terceiro |
| `tins_emp`, `tins_for` | 1 CNPJ, 2 CPF, 3 CEI, 6 CAEPF | comentário do banco |
| Situação da nota (leiaute de importação, Central 672) | 0 regular, 1 regular extemporâneo, 2 cancelado, 6 complementar ou referenciado, 7 denegado, 8 numeração inutilizada, 9 regime especial, 10 complementar extemporâneo, 11 regular Simples | oficial; equivalência com `situacao_*` do banco é inferida |
| `ctlancto.orig_lan` | 1 Normal, 2 Zeramento, 3 Patrimônio, 4 Escrita, 5 Saídas, 6 Entradas, 7 Serviços, 8 Ajuste, 9 Acumulador, 10 Apuração, 11 Pagamento de guia, 12 Cliente, 13 Folha, 14 a 19 Honorários | comentário do banco; 5, 6, 7, 10 e 11 confirmados por ligação 1:1 (terceiro); há valores não documentados |
| `codi_imp` globais | 1 ICMS, 2 IPI, 3 ISS, 4 PIS, 5 COFINS, 8 DIFAL, 9 Substituição Tributária, 16 IRRF, 18 ISS retido, 22 PIS retido, 23 COFINS retido, 24 CSLL retida, 26 INSS retido | terceiro |
| `ctcontas.tipo_cta`, `SITUACAO_CTA` | A analítica (recebe lançamento) ou S sintética; A ativa ou I inativa | comentário do banco |
| `EFPARAMETRO_VIGENCIA.RFED_PAR` | "1 / 2 / … / 9" **sem legenda no banco**; o repo mapeia por evidência | inferida |

## Segurança: o banco não impõe privilégio mínimo

O usuário Externo é só leitura, mas lê 4.946 de 4.964 objetos. Por regra sobre nome e comentário há 83 colunas de segredo (por exemplo senha do módulo web em `usConfUsuario`, senhas de consulta e de eSocial doméstico em `foparmto`), além de CPF, salário, endereço, contato e dados bancários. Pesquisa de terceiros cita 79 tabelas com senha ou token em texto, inclusive os tokens que o próprio Domínio usa na API do Serpro (`efdas_api_tokens_requisicao`, `fodarf_dctfweb_api_tokens_requisicao`). **Qualquer ferramenta com ODBC cru precisa de lista de bloqueio própria.** Recomendação ao escritório: pedir ao Domínio um usuário dedicado com `GRANT SELECT` por coluna para o que a IA realmente precisa.
