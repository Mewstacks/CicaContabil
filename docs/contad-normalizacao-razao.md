# Preparação do Razão CONTAD

D-336/D-337, Q-28/Q-46. Esta entrega prepara normalização local e conferências
de origem. Não adiciona endpoint, persistência, leitura financeira ao agente ou
exportação. O cliente oficial continua1.0.7 e o backend publicado continua83.

## O que foi comprovado

O perfil real da empresa212 em setembro2026 trouxe1.405 registros:838 com dois
lados e567 com um lado. Os1.120 débitos e1.123 créditos não zero encontraram suas
contas no plano212, sem multiplicar registros. Os códigos de tipos/situações de
conta e parâmetros de compartilhamento permanecem brutos, sem legenda inferida.

A conferência específica da conta8 encontrou163 lotes e177 registros completos.
Todos estão no período, com cabeçalho, valor positivo, uma data, um plano e uma
filial por lote, equilíbrio débito/crédito e exatamente um efeito bancário.
Filial bruta212 em todos os efeitos bancários. Tipos brutos C/V/X não recebem
legendas. Esses agregados não contêm montantes nem históricos/documentos.

Isso sustenta conferir partidas por lote; não comprova que os históricos e
documentos reais atendem ao contrato atual. Não chamar os177 registros de
partidas já importadas/normalizadas, nem somar estas contagens à amostra D-73.

## Normalizador local

`apps.hub.dominio_journal_normalization.normalize_journal_snapshot` recebe uma
lista completa de registros e um `JournalScope` explícito. Não usa rede ou Django.

| Campo de registro | Conteúdo esperado |
| --- | --- |
| company_code/chart_company_code | IDs exatos da empresa e do plano autorizados |
| lot_code/row_code | Identidades numéricas estáveis do lote e registro |
| branch_code | Filial bruta dentro do conjunto explícito permitido |
| occurred_on | Data ISO dentro do período, com fim exclusivo |
| debit_account_code/credit_account_code | Contas explícitas, sem deduzir lado pelo valor |
| amount | Texto decimal com ponto e até duas casas, positivo, NUMERIC(14,2) |
| history/document | Textos de origem sem truncamento, substituição ou concatenação |

O contexto fornece o catálogo numérico de contas, código de lado ausente, direção
de entrada bancária, período e contagem esperada de registros de cada lote. O código
de lado ausente não pode existir no catálogo, e a conta bancária deve existir.
Não inferir essas escolhas por letra, máscara contábil ou sinal do montante.

Cada registro bilateral produz duas partidas explícitas. Um registro unilateral
produz uma partida de seu lote, sem contrapartida inventada. IDs incluem empresa,
lote, registro e lado; a ordem de chegada não muda o resultado. A função recusa
duplicação, falta de registros mesmo quando um prefixo já equilibra, empresa/plano/
filial fora do escopo e equilíbrio obtido apenas pela soma de lotes diferentes.

A saída imutável é candidata às nove colunas `ledger-csv-v1`. Mantém as restrições
atuais: um efeito bancário por lote, mesma data/histórico/documento nas partidas e
valores em centavos exatos. Variações de texto, múltiplos efeitos, controles,
históricos acima500 caracteres ou lotes fora do período são recusados, sem corrigir
os dados. Há teto técnico de50 mil registros/100 mil partidas, com recusa explícita.

`requires_source_review=true` e `financial_collection_enabled=false` permanecem na
saída. Nenhum código desta entrega chama `import_ledger_source` ou altera lançamentos.

## Próxima integração

Coletar snapshot completo pelo agente somente após contrato/escopo revisados,
incluindo contagem por lote e catálogo de contas. Conferir os valores/textos reais
antes de persistir. O normalizador não resolve legenda de tipo/situação, DE-PARA,
títulos/baixas, Q-47 ou aceite D-73. O contrato atual continua recusando lotes com
históricos/documentos distintos; eventual ampliação deve preservar as partidas e
ser documentada antes de habilitação.

Referências primárias: [lançamentos e seus tipos](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=4495),
[conferência de lotes](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=6973).

Validação:43 testes locais do normalizador,16 cenários de cada perfil Windows
e CI43091250239/2d40869 integral aprovado (1.961 SQLite/1.992 PostgreSQL).
[PR9 integrada](https://github.com/Mewstacks/CicaContabil/pull/9) na main094a93d,
sem deploy ou importação real de partidas.
