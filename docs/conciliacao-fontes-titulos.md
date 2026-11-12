# Títulos e DE-PARA: preparação local de PC-19

D-311, 05/11/2026. Complementa [Razão normalizado](conciliacao-razao-normalizado.md)
e a [matriz CONTAD](planejamento/verificacao-conciliador-contad-2026-11-02.md).
Não é layout Domínio homologado nem autorização de consulta SQL, baixa ou importação ERP.

## Contrato de títulos

`apps.hub.title_contract.validate_title_snapshot` recebe uma fotografia completa
do lote e valida antes de retornar objetos imutáveis. Não grava no banco, não
expõe endpoint e não foi conectado ao agente. O adaptador Domínio continua
dependendo do confronto de campos/chaves/semântica em Q-28/Q-46.

Campos exatos, sem tradução automática de códigos brutos:

| Objeto | Campos obrigatórios |
|---|---|
| Fotografia | `contract=titles-normalized-v1`, `company_key`, `account_reference`, `as_of`, `settlements_complete`, `titles` |
| Título | `key`, `kind=payable/receivable`, `installments` |
| Parcela | `key`, `due_on`, `principal_cents`, `outstanding_cents`, `settlements` |
| Baixa | `key`, `posted_on`, `principal_cents`, `interest_cents`, `penalty_cents`, `fees_cents`, `discount_cents`, `cash_cents`, `direction`, `reverses` |

Valores são inteiros em centavos, sem bool/float/arredondamento ou sinal
implícito; datas são ISO. `due_on` e `outstanding_cents` aceitam `null` para
desconhecido. Vencimento não cria baixa. `posted_on` é data efetiva explícita,
não pode estar após `as_of`. Parcelas futuras podem existir sem pagamento.

No contrato normalizado, o principal da baixa é a redução do principal da
parcela, incluindo a parte quitada por desconto. A identidade aritmética é
`cash = principal + interest + penalty + fees - discount`. Isso exige tradução
revisada dos campos Domínio; não atribui essa semântica a nenhuma coluna do ERP.
Não há tolerância presumida. Baixa sem movimento de caixa positivo fica fora
desta versão e exige decisão Q-46; não é inventado lançamento bancário.

Saída de pagar e entrada de receber são explícitas e revalidadas. Estorno
integral aponta uma única baixa da mesma parcela, repete seus componentes,
inverte a direção de caixa e não pode antecedê-la. Estornos parciais, cancelamentos
e outros ajustes não são transformados silenciosamente em reversão integral.
Baixas parciais preservam saldo/capacidade; múltiplas baixas são preservadas.
Pagamentos agrupados e alocação entre banco/títulos ainda dependem de Q-46.

Com `settlements_complete=true`, saldo conhecido deve fechar com o principal
reduzido pelas baixas e restaurado pelos estornos. Com cobertura incompleta,
não se inventam baixas ausentes nem saldo zero. Chaves repetidas, empresa/conta
divergentes, campos desconhecidos e inconsistências recusam o lote inteiro.
Limite global de 100 mil parcelas/baixas. Hash canônico independe da ordem
física e muda quando qualquer fato muda; a fotografia não substitui evidência
do arquivo original ou revisão da contadora.

## DE-PARA inicial

`apps.hub.depara.create_initial_depara_drafts` recebe `DeparaExample` com
referência do exemplo revisado, descrição, direção, referência da conta
financeira, contas de débito/crédito e histórico contábil explícitos.
Requer revisor ativo do mesmo escritório em papel com escrita. Não chama IA
ou outro provedor e não cria/ativa contas automaticamente.

O serviço confere plano da empresa, contas ativas que aceitam partidas e conta
financeira ativa. Agrupa somente descrição exata, direção e conta. Devolve
`draft`, `preserved`, `conflict`, `invalid_accounts` ou `insufficient` por grupo.
Conflito entre exemplos ou com regra ativa aplicável não gera novo rascunho.
Resultados de campos não representados no exemplo devem ser conferidos na
revisão; o serviço não estima regras por valor, transferência ou tributo.

Cada sugestão aceita vira `ReconciliationRule` em **rascunho**, com condição
exata e revisão de cada movimento ainda obrigatória após sua ativação humana
no fluxo existente. A trilha registra revisor, referências, hash e ausência
de chamada externa. Retry não substitui regra que alguém editou/desativou.
Ordem dos exemplos e caixa da descrição não criam cópias adicionais.
Aplicação/reaplicação de regras revalida decisões protegidas sob a trava comum
empresa→movimento, conservando revisão manual, conciliação e lançamentos.

Essa preparação não demonstra o DE-PARA **com IA** contratado. Plano real,
exemplos aprovados, egressão e custo Q-08/Q-09 precisam ser resolvidos antes
da execução real e da declaração de entrega desse item.

## Material local e limites

A busca autorizada em Downloads encontrou um plano de contas de 14 páginas.
Foram extraídas 754 linhas candidatas com código bruto, classificação, tipo,
grau e origem página/linha para JSON privado. Não se presumiu código reduzido
versus classificação, situação ativa ou permissão de lançamento; nenhum
cadastro CICA foi preenchido com esse material. A extração não é revisão humana.

Os relatórios bancários de pagamentos/liquidações e o extrato digitalizado
encontrados não comprovam títulos/parcelas/baixas do Domínio nem Razão
independente. Um balancete agregado também não fornece partidas completas.
Arquivos de demonstração não homologam Q-47. O responsável confirmou que os
relatórios solicitados ainda não existem; não solicitar novamente seus caminhos.
A observação inicial `Session Disconnected` ficou superada após cancelar o
menu nativo/elevar a janela e acessar a área de trabalho Windows já logada.
Conteúdo, nomes e identificadores ficam em `.tmp/contad-delivery-2026-11-05/`.

Desenvolvimento/contadora deve obter o Razão e relatório Domínio de títulos
do mesmo recorte, confirmar as colunas do plano e fornecer exemplos revisados
e layout/retorno de importação. Reutilizar Q-28/Q-46/Q-47; não perguntar
novamente origem dos títulos, modalidade Domínio ou tipo de saída.

## Consulta pelos relatórios do fornecedor

A orientação oficial do [Razão de uma conta](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=3132)
indica Contabilidade → Relatórios → Razão, período e seleção de conta específica.
A [emissão do Razão](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=1817)
também permite mostrar o número do lançamento/lote. Usar o recorte privado já
autorizado; não consolidar empresas ou ampliar contas/período por inferência.

Na Escrita Fiscal, a referência de [contas a pagar e receber](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=224)
é Relatórios → Contas a Pagar e Receber. Conferir filtros de emissão,
vencimento, pagamento e posição, preservando sua distinção. Documento público
não prova configuração ou dados nesta instalação. Não habilitar controle de
parcelas, mudar acumuladores, gerar lançamentos ou registrar baixas para
produzir a evidência. A navegação e os campos reais ainda exigem confronto.

Para Q-47, a documentação distingue [TXT exportado pelo próprio Domínio](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=7584)
de [importação por planilha modelo/conjunto de dados](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=4707).
Conferir no destino qual leiaute/conjunto será utilizado antes de alterar o
adaptador `dominio-3.1-pending-homologation`. O CSV local atual não se torna
compatível por essa pesquisa. Não importar conjunto, alterar parâmetros ou
gravar lançamentos durante a consulta; o gate contábil continua desligado.

## Prévia offline de alocações — D-312

`apps.hub.title_allocation.preview_title_allocations` confronta seleções
explícitas entre banco e baixas normalizadas, sem escolher associações ou
gravar decisões. Requer o contrato de títulos acima e uma fotografia bancária
`bank-cash-normalized-v1` com campos exatos:

```json
{
  "contract": "bank-cash-normalized-v1",
  "company_key": "synthetic-company",
  "account_reference": "synthetic-bank",
  "period_start": "2026-09-01",
  "period_end": "2026-09-30",
  "movements": [
    {"key": "bank-1", "occurred_on": "2026-09-12", "cash_cents": 6125, "direction": "outflow"}
  ]
}
```

As seleções são uma lista de objetos com `movement_key`, `title_key`,
`installment_key`, `settlement_key` e `cash_cents`. Todos os identificadores
acima são sintéticos. A baixa é identificada pela chave composta completa;
chaves locais iguais em títulos diferentes não são fundidas. A empresa,
conta e período esperados são confrontados com as duas fontes; a data final
não pode ultrapassar `as_of` da fotografia de títulos.

A prévia calcula capacidade utilizada e restante nos dois lados. Aceita
parciais e agrupamentos explicitamente selecionados; recusa duplicação de
par, excesso de capacidade, referência ausente e direções incompatíveis.
Usa `cash_cents` da baixa, conservando principal, juros, multa, tarifa e desconto.
Original e estorno mantêm fluxos brutos próprios; não são compensados pelo
valor líquido. Data bancária diferente da baixa fica sinalizada para revisão,
sem tolerância presumida. Vencimento não produz baixa ou associação.

Toda saída mantém `requires_review=true`. `source_settlements_complete`
conserva a declaração da fonte; não comprova completude bancária ou semântica
Domínio. O fingerprint canônico ignora ordem física e muda com os fatos ou
seleções. Não representa aprovação nem trilha persistida de decisões humanas.

A CLI `scripts/preview_title_allocations.py` recebe três arquivos JSON e grava
relatório privado com capacidades, componentes, diferenças de data e hashes
SHA-256 das fontes. Executar a partir da raiz, com fontes já normalizadas e
revisadas; não converter o PDF do Razão diretamente para este contrato:

```sh
PYTHONPATH=src python scripts/preview_title_allocations.py \
  --titles <titulos.json> --bank <banco.json> --allocations <selecoes.json> \
  --company-key <empresa> --account-reference <conta> \
  --start AAAA-MM-DD --end AAAA-MM-DD --output <pasta-privada/previa.json>
```

Valida o lote antes de publicar o arquivo; recusa campos JSON repetidos,
fontes acima de 25 MiB e destino existente, inclusive symlink. Grava primeiro
em temporário 0600 e publica atomicamente sem sobrescrita. A pasta deve existir.
Não usa ORM, rede, IA ou ERP. Integração persistente, seleção automática e
homologação real de Q-46 continuam abertas.

Consulta nesta continuidade: Domínio aberto em 10.6A-10 -02 e Razão do candidato
emitido por conta em janeiro/2026, com PDF observado em Downloads do Windows.
Cópia para o Mac e extração de linhas ainda não confirmadas. Fechamento
contábil exibido 11/2023; controle fiscal de títulos desmarcado, período inicial
10/2026. Parâmetros fechados sem gravação. O responsável autorizou pesquisar
outro recorte somente leitura. Esses fatos não homologam o primeiro candidato
nem provam ausência histórica absoluta de títulos.

### Campos observados na alternativa fiscal

O relatório A Pagar foi emitido com emissão 01–30/09/2026, posição 30/09/2026,
situação Todas e tipo Todos, sem filtro bancário. Exibe Documento, Emissão,
Entrada, Vencimento, V. Parcela, Valor Pago, Juros, Multa, Outras, Desconto,
Devolução, Saldo e Situação. Não usar esse filtro como cobertura de todas as
baixas do mês: ele delimita títulos pela emissão, inclusive parcelas futuras.

| Observação | Limite para o adaptador |
|---|---|
| Documento repetido em várias linhas de vencimento | Não é chave única de parcela ou baixa |
| Vencimento e posição separados | Não são data efetiva de pagamento |
| V. Parcela e Valor Pago | Não assumir principal reduzido versus caixa sem exemplos revisados |
| Juros, Multa, Outras e Desconto | Componentes visíveis não aprovam sua tradução ao contrato normalizado |
| Devolução | Não converter automaticamente em estorno integral com vínculo à baixa |
| Saldo/Situação | Não provam completude das baixas nem fechamento contábil |
| Ausência de conta bancária/chave da baixa na visão exibida | Impede associar o relatório diretamente à conta do piloto |

Consulta A Receber pela mesma emissão/posição retornou “Sem dados para emitir”.
Isso só descreve esse filtro; não prova inexistência de títulos ou recebimentos
na empresa. A Receber por recebimento em setembro/posição 30/09 também retornou
sem dados. A Pagar por pagamento em setembro retornou sem dados com posição
30/09 e sem posição; situação Pagamento parcial por emissão em setembro, sem
posição e sem filtro de pagamento, também. Não repetir esses filtros como
prova de ausência geral ou usar o último como caixa do mês. Tipo Todos nas
consultas. PDF A Pagar conferido no Windows (116 KB exibidos), sem cópia Mac,
extração ou hash verificados. Identificadores e conteúdo real ficam apenas nas
evidências privadas. Fechamento fiscal 09/2026 e contábil 11/2014 da alternativa
não homologam a competência; os parâmetros foram fechados sem gravar.


## Descoberta fiscal real — D-345/D-348/D-349, V-368–370

O catálogo real já comprovou notas → parcelas → pagamentos e as ligações
contábeis das três famílias fiscais. Não solicitar novo inventário. A chave
física de pagamento inclui empresa, nota, parcela, data, tipo e número de
pagamento; tipo ou número de pagamento não podem ser descartados ao agrupar.
A ligação contábil usa `fili_lan` como empresa fiscal e `codi_emp` como empresa
contábil, preservando os dois identificadores.

O perfil `agent-windows/inspect-contad-title-profile.ps1` conta apenas o piloto
212/conta8/plano212/setembro2026. Recortes de vencimento e pagamento são
separados. Não retorna montantes, participantes ou documentos. Exige duas
leituras idênticas, cobertura completa dentro dos limites e não habilita
coleta financeira. Windows5.1:12 cenários aprovados em a560b7d/CI43270180630;
resultado real do perfil ainda aguardado. O script não lê configuração do agente,
não altera DSN/parâmetros e não executa baixas ou lançamentos.

Conjuntos oficiais de [Entradas](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=6168)
e [Saídas](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=6169)
fornecem referência de componentes, com limites registrados em D-349/V-370:

| Código bruto | Entradas | Saídas |
|---|---|---|
| 1 | Normal/valor pago | Normal/valor recebido |
| 2/3/4 | Juros/multa/desconto | Juros/multa/desconto |
| 6/7/8 | PIS/COFINS/CSLL | PIS/COFINS/CSLL |
| 9 | CRF | IRRF |
| 10 | IRRF | Sem referência nesse conjunto |

Não estender esses mapas a Serviços, códigos ausentes ou principal/líquido.
Retenção, estorno/exclusão, composição do saldo e efeito no banco ainda exigem
confronto real Q-46. Não importar os conjuntos para produzir a prova.
