# Razão independente: contrato local de entrada

D-305, etapa 09/PC-19, 03/11/2026. Este contrato prepara o CICA para receber
partidas completas antes da homologação do adaptador Domínio. **Não é um
layout oficial Domínio, consulta ODBC aprovada ou prova de completude da fonte.**
O agente Windows único continua sendo o da etapa 03; nenhuma consulta nova foi
habilitada nesta entrega. Não usar a tabela FCONT como Razão por inferência.

## Entrada pelo CICA

Em Conciliação → Nova importação, selecionar empresa, conta financeira, origem
**Registros contábeis** e CSV. A conta financeira deve ter referência bancária
e conta contábil; as contas das partidas devem existir no plano da empresa.
O arquivo é reconhecido como `ledger-csv-v1`, sem passar pelo mapeamento de
movimentos bancários. O formato genérico anterior continua existindo, mas não
gera partidas completas nem essa nova evidência independente.

CSV com separador `;`, UTF-8 ou codificação local já suportada pelo importador,
estas nove colunas na ordem, uma linha por partida:

```csv
entry_key;line_key;date;history;account_code;side;amount_cents;cash_direction;document
exemplo-1;banco;2026-09-12;Recebimento demonstrativo;1.1;debit;10000;inflow;DOC-1
exemplo-1;cliente;2026-09-12;Recebimento demonstrativo;2.1;credit;10000;;DOC-1
```

Todos os dados do exemplo são fictícios. Os códigos de conta são ilustrativos;
não são cadastrados automaticamente e não constituem DE-PARA aprovado.

| Campo | Contrato |
|---|---|
| `entry_key` | Chave estável do lançamento na fonte, até 160 caracteres |
| `line_key` | Chave estável da partida dentro do lançamento, até 160 caracteres |
| `date` | Data `AAAA-MM-DD`, igual em todas as partidas do lançamento |
| `history` | Histórico completo, obrigatório, até 500 caracteres, igual nas partidas |
| `account_code` | Código existente no plano da empresa, até 64 caracteres |
| `side` | `debit` ou `credit` explicitamente normalizado; não aceitar código bruto D/C/TIPO |
| `amount_cents` | Inteiro positivo em centavos, sem arredondamento, sinal ou notação científica |
| `cash_direction` | `inflow` ou `outflow` somente na partida da conta financeira selecionada; não inferir do lado contábil |
| `document` | Referência documental até 160 caracteres, igual nas partidas; vazio é permitido |

São exigidos ao menos duas partidas, débitos iguais aos créditos e um único
efeito na conta bancária selecionada por lançamento. Contrapartidas compostas
são preservadas integralmente. Múltiplos efeitos bancários, contas ausentes,
valores fora do limite, chaves repetidas ou linhas incompletas são recusados
sem gravar parte dos lançamentos. Limites existentes: 25 MiB e 100 mil partidas.

## Identidade, revisão e recuperação

A chave é escritório + conta financeira + chave externa. O fingerprint inclui
as partidas normalizadas completas e ignora sua ordem física. Reenvio idêntico
reutiliza o registro; alteração na mesma chave exige revisão da fonte, sem
substituir histórico. Arquivo com hash divergente é recusado. A referência
conserva arquivo, hash, contrato, linhas e documento.

Cada lançamento cria `JournalEntry` de fonte (`purpose=source_ledger`), partidas,
`AccountingEntry` do efeito bancário e `IndependentLedgerRecord` ligando ambos.
Permanece rascunho de fonte: não é novo lançamento aprovado e não entra na
exportação contábil. Aprovar/reexportar fatos já escriturados seria duplicação.
O estado **Conferir Razão independente** encaminha para a revisão humana do OFX;
não reaplica classificação sobre as partidas recebidas.

As duas filas usam uma mesma alocação quando a fonte possui esse vínculo.
Confirmar pelo OFX requer que o mesmo OFX esteja processado em Movimentos;
confirmação, reconstrução, retry e desfazimento preservam a decisão canônica.
Um upload posterior do mesmo OFX à fila antiga recupera a confirmação existente.
Conta, data e direção são explícitas; o limite é o efeito bancário, mesmo quando
a soma dos débitos do lançamento composto for maior. Alocações parciais ficam
representadas no fluxo avançado; a fila antiga projeta apenas a relação integral
1:1. Registros históricos sem partidas não recebem vínculo artificial.

A auditoria somente leitura existente `audit_ofx_integrity` também aponta uma
projeção que não possui a correspondente alocação compartilhada. Não a corrige.

## Relatório de conferência

Na trilha Processar, **Baixar conferência** gera CSV privado para um único
arquivo bancário com conta selecionada. Mostra movimentos e registros do Razão,
valores alocados/pendentes, diferença líquida do período e limites de cobertura.
Requer processamento sem erro e hash original íntegro; usa os mesmos controles
de escritório/empresa/módulo do download da fonte. Perfis de consulta podem ler.
Os valores monetários do CSV são centavos inteiros, explicitados nos cabeçalhos.

O período padrão é o declarado no PDF Sicredi suportado ou o intervalo dos
movimentos importados. O segundo caso não comprova cobertura mensal. A rota
`/app/conciliacao/arquivos/UUID/conferencia/` também aceita `start` e `end`
em formato ISO para recorte explícito. Saldo não informado fica **não informado**,
nunca zero por conveniência. Igualdade de totais não concede fechamento/aceite.

O PDF textual Sicredi conserva documento, página/região e saldo por movimento,
validando a sequência desde o saldo anterior. Lançamentos futuros ficam fora
dos movimentos efetivos. Saldo inconsistente interrompe a leitura para revisão.
PDF e OFX do mesmo banco são duas representações bancárias; não são evidências
contábeis independentes. A equivalência entre os formatos de conta precisa de
conferência humana. Não importar ambos como se fossem movimentação adicional.

## Dependências ainda abertas

Q-28/Q-46: acesso ao PC, amostra do Razão e títulos reais do **Domínio**, contrato
de chaves/campos/parcelas/baixas e revisão da contadora. A origem dos títulos já
foi confirmada, sem necessidade de perguntar novamente. Q-47: saída inclui
relatório **e arquivo de importação**, mas o layout e a importação contábil
ainda precisam de homologação. O gate de exportação continua desligado.

DE-PARA inicial com IA exige plano de contas/mapa, revisão e gates de custo e
egressão Q-08/Q-09; não houve execução externa nesta entrega. Instalação Windows,
recuperação operacional, 200 itens reais independentes, treinamento e aceite
permanecem no piloto da etapa 12. Os testes sintéticos não os substituem.
