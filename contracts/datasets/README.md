# Catálogo de datasets do conector

Esta pasta é a fonte única consumida pelo Django e incorporada como recurso no agente Windows.
Nenhuma consulta pode ser despachada enquanto `validated` for `false`. A validação em uma base
real deve confirmar apenas nomes/tipos de colunas, contagens e duplicidade, sem valores.

## Dois sistemas de origem

O manifesto está na versão **2**: cada dataset declara `sourceSystem`, e a chave do catálogo é
`sourceSystem:code` — `dominio:companies` e `siescon:companies` são contratos diferentes, com SQL
e hash próprios. Quem escolhe a origem é **o conector**, nunca o corpo da requisição: o agente
grava o sistema na configuração local e o backend o registra na execução. Um conector do Domínio
não alcança o contrato do Siescon nem quando a nuvem manda o código certo.

Na CICA a origem vem da configuração, e não compilada no binário: por D-80 o pacote é único, e um
só serviço atende os dois ERPs. O projeto de onde estes contratos vieram publicava um instalador
por sistema.

As consultas do Siescon devolvem **os mesmos nomes de coluna** das do Domínio de propósito: assim
o processamento do backend é um código só para os dois ERPs.

Estado atual dos quatro contratos do Siescon no manifesto: `companies`, `users` e `salaries` estão
`validated: true`; `taxation` continua `false` e, por isso, não é despachado. Todos dependem de
DDFs (`FILE.DDF`/`FIELD.DDF`/`INDEX.DDF`) publicados em `S:\Dados` — sem eles o Pervasive não
aceita `SELECT`. O DDL está em [`docs/siescon/layout-v0.sql`](../../docs/siescon/layout-v0.sql) e
sua execução depende de autorização do escritório; o material completo, incluindo o que precisa
ser pedido ao escritório, está em [`docs/siescon/`](../../docs/siescon/).

O limite que acompanha esses contratos está registrado em D-117: o layout foi **inferido** por
perfilamento estrutural, não documentado pelo fornecedor. Uma atualização do Siescon pode mudar a
estrutura sem aviso, e a leitura tem de falhar de forma visível em vez de devolver número errado
em silêncio.

Diferenças conhecidas dos contratos do Siescon em relação aos do Domínio, todas pendentes de
confirmação na tela do sistema:

- `users` devolve `situacao` como constante `1`. O campo de "usuário ativo" foi isolado a dois
  candidatos (`@1485` e `@1604`) e nenhum deles está confirmado; trazer todos os usuários é
  preferível a inativar 20 ou 36 pessoas por um palpite.
- `taxation` traz a vigência mais recente, sem o corte "que já entrou em vigor" que a consulta do
  Domínio faz. `vigencia` é `CHAR(8)` no formato AAAAMMDD e chega como texto — o backend parseia.
  O `CASE` converte `LRE/SME/EPP/LPR` para os códigos de `RFED_PAR` do Domínio, e essa leitura
  também está pendente de confirmação.
- `salaries` **existe e é a fonte de folha do produto**. No Fedrizzi a folha do próprio
  escritório não está no Domínio (a empresa 1 de lá tem zero empregados), então é do Siescon
  que sai o custo/hora do colaborador. Ver `colunas de contexto` abaixo.
- Horas e honorários continuam sem contrato no Siescon: os módulos `GET_*` e `PFT_*` estão
  zerados naquela base desde a instalação — ver [a análise do Siescon](../../docs/siescon/analise-siescon.md).

## Colunas de contexto

Nem toda fonte carrega, na linha, a coordenada que a linha significa. No Siescon a folha mora
em `S:\Dados\<NNNN>\SAEC_COL.DAT`: **uma pasta por empresa**, e a empresa é o *diretório* —
não existe coluna `codi_emp` para trazer. O arquivo também guarda apenas o salário vigente,
sem histórico, então não há de onde tirar a competência.

`contextColumns` declara essas colunas: elas fazem parte da linha lógica que o backend
processa, mas **não virão do `SELECT`**. O backend as preenche uma vez por run:

| Coluna | De onde sai |
|---|---|
| `codi_emp` | a empresa armada com o papel de `requiresSourceRole`, **no ERP daquele conector** |
| `ultima_competencia` | o mês da execução |

Duas consequências que valem registrar. A primeira: o contrato fica **sem parâmetro nenhum**,
o que significa que nada é pedido ao operador a cada execução e o ciclo automático consegue
agendá-lo sozinho. A segunda: como a competência é a da execução, o histórico salarial se
forma por acumulação — reexecutar no mesmo mês converge no mesmo registro, e no mês seguinte
nasce a leitura daquele mês. Quem precisa do histórico retroativo não o encontra aqui: a fonte
não o tem.

Uma coluna de contexto não pode estar em `identityColumns`: a identidade é calculada pelo
agente sobre o que o `SELECT` devolveu, antes de o backend existir na história. O carregador
do catálogo recusa o manifesto que viole isso.

`billing_services` usa o fallback seguro empresa-fonte x cliente x competência: a consulta agrega
os serviços e a identidade é derivada dessa chave composta. Ela só poderá ser validada após o
preflight confirmar os tipos e a semântica de `codi_emp`.

`taxation` lê `EFPARAMETRO_VIGENCIA` e usa `ROW_NUMBER()` por `codi_emp` para enviar somente a
vigência mais recente **que já entrou em vigor** (`VIGENCIA_PAR <= CURRENT DATE`): uma mudança de
regime cadastrada com vigência futura não pode aparecer como o regime atual do cliente. Os códigos
de `RFED_PAR` são convertidos para os nomes exibidos na carteira pelo processador do backend.
`EFPARAMETRO_VIGENCIA` traz empresas que `geempre` não traz — essas linhas são rejeitadas
individualmente e contadas em `rejected_count`, sem derrubar o run.

## Procedimento de validação num servidor Domínio real

1. Instale o agente e rode um job `preflight` para cada dataset (o preflight executa a consulta
   real, mas envia apenas `{columns, row_count, duplicate_count}` — nenhum dado de origem sai).
2. Compare os nomes/tipos de coluna do resumo de preflight com o `manifest.json` (a caixa dos
   nomes precisa ser idêntica: o backend exige igualdade exata do conjunto de colunas).
3. Para `salaries`, confirme o formato real de `foaltesal.competencia` (o backend aceita
   `AAAA-MM`, `AAAA/MM`, `AAAAMM`, `MM/AAAA` e `MM-AAAA`).
4. Para `salaries` e `billing_services`, arme a empresa-fonte no sistema: papel
   `payroll_source`/`billing_source` no cadastro da empresa (tela Clientes) e a confirmação da
   semântica de `codi_emp` em Configurações. Sem isso os jobs `full`/`incremental` são rejeitados.
5. Só então marque `validated: true` nos datasets aprovados, atualize o `querySha256` se algum
   `.sql` mudou (`shasum -a 256 <arquivo>`), e faça rebuild/redeploy do **backend e do agente em
   conjunto** — o agente aborta o ciclo se o hash do manifest divergir do servido pela nuvem.

## Observações operacionais conhecidas

- `automatic_hours` ignora sessões sem `tfim_log` (sessões abertas) e `f9_hours` ignora
  atividades sem `hori_atv`/`horf_atv` — uma linha incompleta não deve derrubar o run inteiro.
- O timeout ODBC do agente é fixo em 30s (`OdbcExtractor.cs`): janelas grandes de
  `automatic_hours`/`f9_hours` (até 500 mil linhas) podem exigir janelas menores por job.
- O assistente de configuração exige BitLocker e lista apenas os DSNs do driver do seu perfil:
  "SQL Anywhere 16/17" no conector do Domínio, "Pervasive"/"PSQL" no do Siescon. Servidores com
  SQL Anywhere mais antigo pedem ajuste do wizard.

## O que muda a cada escritório

Quase todo contrato é igual em qualquer base do mesmo ERP. As exceções são poucas e todas
saem de **configuração**, nunca de literal no `.sql` — um número cravado funciona num cliente
e devolve zero, calado, no próximo.

| O quê | Onde se configura | Quem usa |
|---|---|---|
| `codi_emp` do escritório | papel `billing_source` / `payroll_source` no cadastro da empresa (tela Clientes) + confirmação da semântica em Configurações | `billing_services`, `salaries` |
| `i_evento` da mensalidade | campo **Evento de mensalidade** em Configurações (`OrganizacaoConfig.evento_mensalidade`) | `billing_honorarios` |
| De qual módulo vem a receita | campo **Fonte da receita** em Configurações (`OrganizacaoConfig.fonte_receita`) | escolhe entre `billing_services` e `billing_honorarios` |

O `codi_emp` é o mesmo número em todos os módulos do Domínio, mas muda de escritório para
escritório. O código do evento não é constante do produto: cada escritório numera o seu
cadastro de eventos, então descobrir qual é o de mensalidade faz parte da implantação — a
consulta que revela isso (o evento de mensalidade vem disparado na frente em total) está em
[`docs/dominio/achar-honorarios.sql`](../../docs/dominio/achar-honorarios.sql).

Enquanto qualquer um deles estiver em branco, o ciclo diário **pula** o dataset em vez de
adivinhar. É de propósito: faturar pelo evento errado produz um número plausível, e número
plausível e errado ninguém confere.

Os dois contratos de receita são mutuamente exclusivos por escritório. O mesmo valor pode
estar lançado no Honorários num escritório e na escrita fiscal noutro — e às vezes um está
preenchido e o outro não. Carregar os dois contaria a mesma mensalidade duas vezes, porque
`_rebuild_mensalidades` soma todo `ServicoFaturado` da competência sem olhar de qual contrato
veio. O **preflight dos dois continua liberado**: é com ele que se descobre qual dos módulos
está preenchido antes de escolher.

## Os contratos de honorários (Domínio Honorários)

O módulo do Domínio onde o escritório fatura os próprios clientes usa tabelas com prefixo
`HR`. Não confundir com `ef*`, que é **Escrita Fiscal** — ali estão as notas que cada
*cliente* emitiu, e foi lendo aquilo que `billing_services` media zero na empresa do
escritório e milhares de linhas espalhadas pelos clientes.

| Contrato | Para quê |
|---|---|
| `billing_events.v1.sql` | **Descoberta.** Volume e total por evento de faturamento, por competência. Não alimenta receita: existe para revelar, na tela Dados, qual código de evento é a mensalidade. Devolve só código, contagem e soma — nenhum nome ou documento de cliente. |
| `billing_honorarios.v1.sql` | **Carga.** A mensalidade por cliente × competência, agregada, ancorada em `HRFATURAMENTO.COMPETENCIA`. |

Duas escolhas dentro de `billing_honorarios` que não são óbvias no SQL:

- **A data de corte é a competência, não o vencimento da parcela.** Parcela de agosto que
  vence em setembro tem de pesar na margem de agosto.
- **`codi_cli` é `HRCLIENTE.I_CLIENTE_FIXO`**, e não o `I_CLIENTE` usado no join. O FIXO é o
  código que aparece no Extrato por Cliente, e portanto a coordenada com que o escritório
  confere uma linha nossa contra a tela do Domínio.

A ordem dos `?` é contrato: o agente vincula os parâmetros **posicionalmente**, na ordem em
que o manifest os declara. Em `billing_honorarios` a ordem é `codi_emp, i_evento, start_date,
end_date` — trocar dois passaria uma data como código de evento.

Os arquivos `.sql` não podem ter cabeçalho de comentário: o catálogo recusa qualquer arquivo
que não comece em `SELECT`/`WITH`. É por isso que esta documentação mora aqui.
