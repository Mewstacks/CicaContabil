# Análise do Siescon como segunda fonte de dados

Levantamento feito na máquina `Maquina20` em 16/09/2026, comparando o Siescon instalado
com o que o conector já faz hoje no Domínio Sistemas.

**Conclusão em uma linha:** o Siescon **não expõe SQL**. Ele grava em arquivos Btrieve sem
dicionário relacional, então não existe hoje um `SELECT` equivalente ao do Domínio — e, mais
grave, as duas pontas que o produto precisa (**horas trabalhadas** e **honorários**) estão
com os módulos **vazios** nesta base.

---

## 1. Onde o Siescon está

| Item | Valor |
|---|---|
| Compartilhamento | `\\servidor\siescon`, mapeado em `S:` |
| Runtime | `S:\Magicxpa412\MgxpaRuntime.exe` — **Magic xpa 4.1.2** |
| Aplicação | `S:\Aplic\Siescon412.ecf` (100 MB, compilado) |
| Configuração | `S:\Magicxpa412\Magic.ini` |
| Dados | `S:\Dados\` (tabelas globais) + `S:\Dados\NNNN\` (uma pasta por empresa) |
| Empresas | **688** pastas de dados; `GER_EMPRESA.DAT` tem **679 registros** |
| Motor de banco | Pervasive PSQL v10 SP3 Workgroup (32 bits), `w3dbsmgr.exe` em execução |
| Licenciada | 26517 (ver seção `[SIESCON]` no `Magic.ini`) |

## 2. Como o Domínio é lido hoje (linha de base)

O agente `_API/agent` é genérico em cima de ODBC:

- `OdbcExtractor.cs` abre um DSN, executa o SQL do contrato com parâmetros posicionais (`?`)
  e faz streaming das linhas. Timeout fixo de 30 s.
- `DatasetCatalog.cs` carrega `contracts/datasets/manifest.json` e recusa qualquer consulta
  cujo SHA-256 não confira.
- `ConfigurationWizard.cs:55` só aceita DSNs cujo driver contenha "SQL Anywhere 16/17".

Ou seja: **o extrator não é acoplado ao Domínio, o catálogo é.** Se o Siescon fosse consultável
por ODBC/SQL, bastaria um novo conjunto de `.sql` + manifest e afrouxar o filtro do assistente.

## 3. Por que não há `SELECT` no Siescon

O `Magic.ini` mostra que só o gateway **Btrieve** está ativo:

```ini
[MAGIC_GATEWAYS]
MGDB00=Gateways\MGBtrieveAPI1.dll     ; ativo
;MGDB01=Gateways\MGPervasiveSQL.dll   ; comentado
;MGDB19=Gateways\mgodbc.dll           ; comentado
```

O Pervasive tem duas interfaces: a **transacional** (Btrieve, acesso por registro/chave — é a que
o Siescon usa) e a **relacional** (SQL/ODBC). A relacional só funciona com **DDFs**
(`FILE.DDF`, `FIELD.DDF`, `INDEX.DDF`), que descrevem nome, offset e tipo de cada coluna.

Verificações feitas:

- **Nenhum DDF em todo o share** — varredura recursiva completa de `S:\`, resultado zero.
- `DBNAMES.CFG` do Pervasive só tem `DEFAULTDB`, `DEMODATA`, `PERVASIVESYSDB`, `TEMPDB` —
  **nenhum banco nomeado do Siescon está registrado**.
- Não há servidor MySQL: o `Magic.ini` declara `racsiescon` e `escritorionaweb` (DBMS 4 = MySQL),
  mas a porta 3306 em `servidor` está fechada e não existe serviço MySQL local.
- `S:\Monitor\dados.automacao` é SQLite, mas é do **MonitorSiescon** (automação de documentos com
  OCR/OpenAI) — tabelas de regras, quase todas vazias. Não serve como fonte.

**Sem DDF, o layout dos registros é opaco.** Os arquivos existem e são legíveis (formato Btrieve
9.50, assinatura `FC`), o que foi confirmado na prática:

```
butil -stat S:\Dados\GER_EMPRESA.DAT
  Total Number of Records = 679 | Record Length = 2127 | 8 chaves
  chave 0: offset 1,   4 bytes, Integer   (código da empresa — 679 valores únicos)
  chave 1: offset 6,   120 bytes, String  (razão social)
  chave 3: offset 166, 20 bytes, String   (documento)
```

Um `butil -recover` sobre `ADM_USUARIO.DAT` recuperou os **51 registros** com sucesso. Então o
acesso é tecnicamente viável — o que falta é o **mapa de colunas**.

## 4. Mapeamento dos 7 datasets para o Siescon

| Dataset (Domínio) | Equivalente no Siescon | Situação |
|---|---|---|
| `companies` (`geempre`) | `S:\Dados\GER_EMPRESA.DAT` | ✅ 679 registros, ativo |
| `users` (`usConfUsuario`) | `S:\Dados\ADM_USUARIO.DAT` | ✅ 51 registros, ativo |
| `taxation` (`EFPARAMETRO_VIGENCIA`) | `SAEC_ENQ` / `GER_EMPRESA` (campo categórico) | ❌ **`SAEC_ENQ` está com 0 registros** (reconferido em 16/09/2026 — ver 4b). Resta o campo categórico de `GER_EMPRESA`, com semântica pendente — ver 4a |
| `salaries` (`foaltesal`) | `S:\Dados\NNNN\SAEC_COL.DAT` | ✅ salário e salário-hora confirmados — ver 4a. **É a fonte de folha do produto**: no Domínio a empresa 1, o próprio escritório, tem zero empregados |
| `automatic_hours` (`geloguser`) | **não existe** | ❌ o Siescon não registra sessão por empresa/usuário |
| `f9_hours` (`geatividades`) | `GET_TAREFA_AGENDA_EXECUCAO.DAT` | ❌ **0 registros** — módulo GET nunca foi usado |
| `billing_services` (`efservicos`) | `PFT_FAT_FATURAMENTO.DAT` | ❌ **0 registros**; `ADM_CONTRATO.DAT` também 0 |

Todos os arquivos dos módulos `GET_*` (gestão de tarefas) e `PFT_*` (faturamento) estão com data
de 12/01/2018 09:15 e no tamanho de arquivo vazio — são os arquivos criados na instalação e nunca
alimentados. Os arquivos de honorários do escritório também não aparecem: `SAEC_TIT` e `SAEC_CTO`
não existem, e `SAEC_HOP`/`SAEC_LRC` estão zerados.

**Isto é o bloqueio real do projeto.** O cálculo de lucro por cliente é
`honorários − (horas × custo por hora)`. No Siescon desta base, nem o numerador nem o
denominador têm dados.

## 4a. Layout levantado para empresa, usuários, folha e tributação

Como não há DDF nem dicionário do fornecedor, o layout foi levantado aqui. A aplicação
`Siescon412.ecf` **é criptografada** (entropia 8,00 bits/byte — só o cabeçalho é legível), então
o dicionário não sai dela. O que funcionou foi combinar duas fontes:

1. `butil -stat` entrega, de graça, offset/tamanho/tipo de **todas as colunas indexadas**.
2. Para as não indexadas, perfilamento estrutural dos registros (tipo por offset, cardinalidade,
   faixa) — sem expor conteúdo.

O resultado está em [`docs/siescon/layout-v0.sql`](siescon/layout-v0.sql), como DDL do Pervasive:
executá-lo cria os DDFs e é isso que libera o `SELECT` via ODBC.

### O que ficou provado

| Campo | Tabela / offset | Como foi confirmado |
|---|---|---|
| código da empresa | `GER_EMPRESA` @1, int 4 | chave 0, 679 valores únicos = 679 empresas |
| razão social | `GER_EMPRESA` @6, char 120 | chave 1, 672 únicos |
| nome fantasia | `GER_EMPRESA` @126, char 40 | chave 2, 353 únicos |
| CNPJ | `GER_EMPRESA` @166, char 20 | chave 3, 678 únicos de 679 |
| código do usuário | `ADM_USUARIO` @1, int 2 | chave 0, 51 únicos = 51 usuários |
| nome do usuário | `ADM_USUARIO` @3, char 50 | chave 1, 51 únicos |
| código do colaborador | `SAEC_COL` @1, int 4 | chave 0 |
| nome do colaborador | `SAEC_COL` @31, char 50 | chave 1 |
| **salário mensal** | `SAEC_COL` @644, double | ver teste abaixo |
| **salário-hora** | `SAEC_COL` @652, double | ver teste abaixo |

O teste do salário vale a pena registrar porque é auto-validante: para os 29 colaboradores da
empresa `0577`, a razão entre o campo @644 e o campo @652 deu **220,0 exato na maioria dos
registros** e entre 205 e 220,05 no resto. 220 h/mês é a jornada mensal padrão — dois campos
numéricos quaisquer não caem nessa razão por acaso. Salário identificado.

### O que ficou em aberto (campos categóricos sem semântica confirmada)

O perfilamento isolou os campos que são **de fato categóricos** (domínio pequeno com todos os
valores frequentes, o que descarta bytes no meio de nomes e endereços):

| Candidato | Distribuição | Leitura provável |
|---|---|---|
| `GER_EMPRESA` @1051 | `A`=533, `I`=107, `P`=39 | situação: Ativa / Inativa / Paralisada |
| `GER_EMPRESA` @1402 | `0`=234, `1`=197, `2`=213, `3`=35 | regime tributário (4 códigos) |
| `GER_EMPRESA` @530 | espaço=137, `C`=118, `I`=39, `S`=385 | regime ou tipo de empresa |
| `ADM_USUARIO` @1485 | `0`=30, `1`=20 | usuário ativo |
| `ADM_USUARIO` @1604 | `N`=36, `S`=15 | usuário ativo ou administrador |

Tentei decidir o regime por correlação com evidência externa e **não deu**: usei a apuração do
Simples Nacional (`FIS_APSN_APURACAO_SIMPLES_NACIONAL`) como verdade, mas 113 de 120 empresas
amostradas têm registros nesse arquivo — o sinal não separa nada, e nenhum candidato superou a
taxa-base de 94,2%. A data de alteração das pastas também não serve: todas as 400 empresas
testadas aparecem com movimento em 2026, provavelmente por processo em lote.

### Como fechar isso em dois minutos

Os candidatos acima se resolvem com **uma consulta na tela do Siescon**, não com mais inferência:
abrir 3 ou 4 empresas de regimes diferentes (uma no Simples, uma no Presumido, uma no Real, uma
inativa) e me passar o código e o regime de cada uma. Eu confiro os bytes daqueles códigos e
fecho o mapeamento. O mesmo vale para o usuário: quantos usuários a tela lista como ativos —
se forem 20, é o campo @1485; se forem 15, é o @1604.

Alternativa que resolve tudo de uma vez: o Siescon exporta tabelas em texto de largura fixa
(há um exemplo em `S:\Util\SAEC_CXE.TXT`). Uma exportação do cadastro de empresas nomeia todas
as colunas de uma vez e dispensa o resto da inferência.

## 4b. Correção: `SAEC_ENQ` está vazio

Este documento afirmava, mais acima, que `SAEC_ENQ` tinha **1197 registros** e que **530
empresas** tinham enquadramento. **Isso não se confirma.** Conferido com `butil -stat`
diretamente no share, e também numa cópia do arquivo, no mesmo dia:

```
GER_EMPRESA    Record Length = 2127   Total Number of Records = 679
ADM_USUARIO    Record Length = 1796   Total Number of Records = 51
SAEC_ENQ       Record Length = 98     Total Number of Records = 0     <-- vazio
```

O arquivo existe, tem 57344 bytes alocados e foi gravado em 16/09/2026 13:19 — mas não
contém registro nenhum. Há também um `SAEC_ENW.DAT` (24 KB, de 2006) que não foi
investigado.

**Consequência:** o contrato `taxation` do Siescon
([`contracts/datasets/taxation.siescon.v1.sql`](../contracts/datasets/taxation.siescon.v1.sql))
lê `SAEC_ENQ`. Ele continua no catálogo — é fail-closed, `validated: false`, e um preflight
vai simplesmente devolver zero linhas, que é a resposta correta — mas **não vai trazer regime
tributário nenhum** nesta base.

O caminho alternativo é o campo categórico `GER_EMPRESA` @1402 (`0`=234, `1`=197, `2`=213,
`3`=35), e ele depende da confirmação das 6 empresas pedida em
[`docs/siescon/o-que-preciso.md`](siescon/o-que-preciso.md). Sem saber o que cada código
significa, escrever a conversão seria chute — e um chute aqui classifica 679 empresas no
regime errado.

## 5. Caminhos possíveis

### A. Construir os DDFs e ligar o ODBC do Pervasive — recomendado para o que existe

É o caminho que preserva a arquitetura atual: o agente continua sendo um extrator ODBC genérico.

1. Levantar o layout de cada tabela necessária (`GER_EMPRESA`, `ADM_USUARIO`,
   `FIS_PEF_PARAMETRO_FISCAL_EMPRESA`, `SAEC_COL`, `SAEC_MFO`).
2. Montar os DDFs com o **DDF Builder** (`builder.exe`) e o **PCC** (`pcc.exe`), ambos já
   instalados em `C:\Program Files (x86)\Pervasive Software\PSQL\bin`.
3. Registrar um banco nomeado apontando para `S:\Dados` e criar o DSN.
4. Escrever `contracts/datasets/*.siescon.sql` e um manifest próprio.

Custo: o levantamento de layout é o item caro. O `butil -stat` já entrega offset, tamanho e tipo
das **colunas indexadas** (foi assim que identificamos código/razão/documento em `GER_EMPRESA`),
mas as colunas não indexadas exigem inspeção. O caminho limpo é pedir o dicionário de dados ao
fornecedor do Siescon; o caminho sem fornecedor é derivar do `Siescon412.ecf`.

Complicação estrutural: o Domínio tem **um banco com `codi_emp` como coluna**; o Siescon tem
**688 diretórios**, um por empresa. Um DSN por empresa é inviável — o jeito prático é um banco
nomeado por empresa ou uma tabela DDF por diretório, com o agente iterando as empresas. Isso muda
o modelo de execução dos jobs (hoje `codi_emp` é parâmetro da consulta, não do DSN).

### B. Ler Btrieve direto no agente, sem SQL

Usar a API Btrieve (`w3btrv7.dll`) no conector .NET e fazer varredura sequencial com desserialização
por layout. Dispensa DDF e dispensa o Pervasive relacional, mas **quebra o contrato atual**: não
existiria mais "consulta SQL com hash", que é a garantia de que o agente não executa nada fora do
catálogo. Precisaria de um contrato equivalente (layout versionado por hash).

### C. Resolver as lacunas de horas e honorários fora do Siescon

Independente de A ou B, horas e honorários precisam de origem. Opções a decidir com o escritório:

- Ativar os módulos `GET_*` (tarefas) e `PFT_*` (faturamento) do Siescon e esperar acumular dados.
- Importar honorários de onde eles realmente estão hoje (planilha, financeiro, emissor de NFS-e).
- Manter o Domínio como fonte de horas onde ele existe, e o Siescon só como fonte cadastral.

## 6. Mudanças no ProjetoARD — **feitas**

O sistema não tinha o conceito de "sistema de origem". Agora tem, de ponta a ponta:

| Camada | O que passou a existir |
|---|---|
| Manifesto | versão **2**: cada dataset declara `sourceSystem`; a chave do catálogo é `origem:code` |
| Agente | `AgentProfile` — o ERP vem gravado no binário e decide serviço, pasta de estado, chave CNG, origem de log e driver ODBC aceito |
| Instalador | `Package.wxs` parametrizado; **dois MSIs**, que instalam lado a lado |
| Backend | `Connector.source_system`, `Empresa.sistema_origem`, `UsuarioDominio.sistema_origem` |
| Tela | origem na lista de conectores, no histórico de importações e na carteira, com filtro por sistema |

### O segundo binário (caminho A, resolvido sob nosso controle)

O conector do Siescon usa **serviço win-x64 e ponte ODBC win-x86**. Não é detalhe de
empacotamento: o Pervasive PSQL só publica driver ODBC de **32 bits**, então o serviço x64 delega
somente a consulta a um processo autocontido x86. O configurador consulta explicitamente a visão
de 32 bits de `HKLM\SOFTWARE\ODBC`, a mesma que a ponte usa.

O código-fonte do serviço é um só; `ArdSourceSystem` grava o perfil no binário.
`build-lab.ps1 -Sistema ambos` gera os dois MSIs internos e o assistente único.

### O que a separação por origem evita

`codi_emp` e `i_usuario` só são únicos **dentro de um sistema**. Sem a dimensão de origem, a
empresa 25 do Siescon sobrescreveria a 25 do Domínio — e, pior, a reconciliação de cada
importação marcaria como removido todo o cadastro do outro ERP, que de fato não veio naquele run.
Há teste de regressão para isso em `tests/test_connector_processing.py`.

Consequência aceita: uma empresa que existe nos dois sistemas aparece como **duas linhas** na
carteira, uma por origem. Unificar as duas é resolução de identidade entre ERPs, um problema
maior, e não foi feito aqui.

### O que ainda bloqueia os dados do Siescon chegarem na tela

A tubulação está pronta e fechada. O que falta não é código:

1. **Os DDFs não existem** em `S:\Dados`, então o Pervasive não aceita `SELECT`. O DDL está em
   `docs/siescon/layout-v0.sql` e sua execução em produção depende de autorização — ver
   `docs/siescon/o-que-preciso.md`, item 3.
2. **Não há DSN do Pervasive** configurado enquanto o item 1 não acontecer.
3. Os três contratos do Siescon estão `validated: false` e assim ficam até um **preflight** provar
   que a consulta roda naquele banco e devolve as colunas esperadas. O resultado do preflight
   aparece na tela Dados, coluna "Conferência" — é por ali que se valida.

## 7. O que precisa ser decidido antes de escrever código

1. **Horas e honorários**: de onde virão? Sem isso, integrar o Siescon entrega só cadastro de
   empresas e folha — não entrega o produto.
2. **Dicionário de dados**: dá para obter o layout das tabelas com o fornecedor do Siescon?
   É a diferença entre dias e semanas de trabalho.
3. **Modelo por empresa**: confirmar se vamos criar um banco Pervasive por empresa (688) ou
   mudar o agente para iterar diretórios.
