# Títulos e DE-PARA: preparação local de PC-19

D-311, 05/11/2026. Complementa [Razão normalizado](conciliacao-razao-normalizado.md)
e a [matriz CONTAD](planejamento/verificacao-conciliador-contad-2026-11-02.md).
Não é layout Domínio homologado nem autorização de consulta SQL, baixa ou importação ERP.

## Captura fiscal original para revisão — D-352

A candidata 1.0.9 acrescenta o contrato `dominio-title-snapshot-v1` ao agente
oficial. A captura produz uma fonte JSON privada no CICA, vinculada ao escritório,
à empresa e ao pedido auditado. O resultado exige revisão semântica e não cria
títulos normalizados, alocações bancárias ou lançamentos contábeis.

O primeiro recorte mantém a empresa 212 e setembro de 2026. Inclui parcelas com
vencimento no mês ou referenciadas por pagamentos do mês, os componentes desses
pagamentos e suas ligações contábeis. A conta 8 identifica o contexto de comparação;
os perfis reais V-371/V-374 não demonstraram vínculo bancário com esses títulos.
Não há afirmação de saldo ou cobertura completa da vida de cada título.

As doze consultas e o esquema estão em `contracts/titles`, incorporados por hash
ao binário. Duas leituras completas precisam ser idênticas. Decimais são strings
literais com duas casas; valores negativos, zeros, retenções e códigos desconhecidos
continuam presentes. Não se traduz o componente normal em principal ou caixa.
O limite é 4.000.000 bytes e 50.000 linhas por consulta, com recusa integral de
excesso, mudança da fonte ou cobertura incompatível.

O comando `queue_contad_native_titles` exige escritório, agente oficial, conta,
usuário solicitante autorizado, arquivo de escopo e referência de evidência.
Sem `--allow-financial-capture`, apenas apresenta os hashes e a prévia, sem gravar
pedido. A operação real depende da aprovação aplicável à coleta, backend compatível
publicado e pacote Windows exato verificado. Nunca usar um usuário fictício ou
atribuir o pedido a outra pessoa para contornar a autorização.

O escopo contém `capture_id`, `company_code`, `comparison_bank_account_code`,
`period_start`, `period_end_exclusive` e `expected_counts` por família
(`due_installments`, `payments`, `accounting_links`). As contagens vêm da evidência
privada conferida, sem registros de cliente no código/CI. `capture_id` é também a
identidade do pedido; reenvios preservam a fonte e geram uma única auditoria.
Uma nova captura requer outra identidade explícita e não conta como nova amostra
humana por si só.

O upgrade preparado em `agent-windows/upgrade-titles.ps1` aceita 1.0.8/1.0.9 e
confere MSI, manifesto, versão, serviço SYSTEM e preservação dos bytes DPAPI.
Não refaz pareamento ou DSN. O ensaio `test-title-upgrade.ps1` é exclusivo do CI
Windows descartável e usa configuração sintética; nunca executá-lo na CONTAD.
Preparar essa candidata não instala, implanta nem enfileira uma captura real.

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


## Comparação técnica de capturas retidas — D-355/V-381

`compare_contad_native_titles` identifica registros novos, ausentes do recorte
atual e com campos literais alterados. A comparação usa as chaves completas
de parcelas, componentes e vínculos; preserva a distinção entre empresa
contábil (`codi_emp`) e filial fiscal (`fili_lan`) nos vínculos. Não interpreta
ausência como exclusão, estorno ou quitação. Mesmo quando não há mudanças,
a revisão semântica e o vínculo bancário continuam pendentes.

Informe o escritório, um usuário operacional atualmente autorizado e os dois
UUIDs de captura. O comando lê somente fontes privadas já retidas, verifica
hash/contrato/recibo e revalida o acesso após a leitura. Não altera registros
e não consulta o ERP. O resumo mostra apenas contagens/hashes; referências
de linhas nos detalhes usam hash da chave e posição1-based na fonte original,
sem expor o identificador fiscal ou valor.

```text
python manage.py compare_contad_native_titles --organization UUID_ESCRITORIO --actor UUID_USUARIO --previous UUID_CAPTURA_ANTERIOR --current UUID_CAPTURA_ATUAL --output /local/privado/comparacao.json
```

Substitua os UUIDs e escolha um caminho novo. `--output` é opcional, privado
com modo0600 e recusa sobrescrita/symlink; sem ele, só o resumo sai no console.
Uma comparação de uma fonte consigo mesma prova apenas leitura/reenvio, sem
provar atualização real, qualidade financeira ou nova amostra D-73.


V-382: comando disponível no backend86, com CI integral aprovado. Leitura real
da fonte retida conferida duas vezes em READ ONLY, sem mudanças ou gravações.
A prova usou a mesma captura e não substitui duas fontes reais independentes
ou o confronto humano C01/C02, que permanece adiado por D-355.


## Tradução financeira explicitamente revisada — D-356 (local)

`native_title_translation.translate_reviewed_titles` liga decisões humanas à
fonte fiscal íntegra. `reconcile_titles native-import --capture UUID --input
REVISAO.json` reaproveita autorização e persistência existentes. A captura
precisa pertencer à conta selecionada; cada parcela e componente recebe
referência opaca por chave física, estável entre releituras. A trilha imutável
liga captura/hash, parcela, campo do principal e todos os componentes de cada
baixa ao snapshot normalizado. Não chama ERP nem escolhe associação bancária.

A revisão contém `source_sha256`, `evidence_reference` e `decisions`. Cada
decisão informa família, referência da parcela, natureza, campo literal do
principal (`vlor_*`/`vbru_*`, escolhido pelo revisor) e eventos com referências
dos componentes e campos do contrato `titles-normalized-v1`. A chave de cada
evento é o hash da lista ordenada de referências dos componentes. Data e
número de pagamento vêm da origem; uma decisão não mistura pagamentos nem
omite componentes zero/retenções. Todas as baixas da parcela selecionada
precisam de decisão. Componentes e reversão são explícitos, nunca derivados
da legenda do código, sinal, ausência, igualdade ou saldo aparente.

O contrato valida baixas parciais, aritmética e estorno integral vinculado;
o caminho integrado foi exercitado até alocação bancária parcial, capacidade
remanescente e desfazimento, somente com dados sintéticos. A fonte mensal
não prova história completa: `settlements_complete=false` e saldo desconhecido
permanecem obrigatórios. Vínculo bancário continua `unproven` até a decisão
com evidência bancária própria. Isso não substitui C01/C02 nem comprova saldos.

## Sugestões de DE-PARA com IA e revisão separada — D-356 (local)

O comando administrativo `depara_ai` oferece `prepare`, `generate`,
`review-packet` e `review`. As opções comuns são organização, conta e ator.
A preparação recebe JSON com `items` (referência, descrição, direção) e
`candidate_codes` (2–12 contas ativas/analíticas do plano da própria empresa,
incluindo a conta contábil do banco). Cada lote admite até quatro descrições.
Não se usa o catálogo bruto como plano aprovado nem se cria conta por inferência.

A chamada única exige `--max-request-cents` positivo, `--allow-data-egress`,
política Claude vigente, papel permitido, chave central e reserva de cota
configurada. A transação confirma a reserva antes do HTTP. O payload usa
referências opacas, descrições limitadas/mascaradas e nomes/códigos candidatos;
não manda nome da empresa, valores ou identificadores bancários/fiscais do
contexto. Mascaramento não é autorização de egressão: Q-08/Q-09 continuam
exigindo decisão sobre o conteúdo concreto e teto. “Menor custo possível”
não foi convertido em orçamento numérico nem em permissão de dados.

Resposta só aceita referências e contas candidatas, sem contas iguais no
débito/crédito ou ausência da conta bancária. Dados do modelo nunca ativam
regra. `review-packet --batch UUID --output CAMINHO_NOVO.json` cria arquivo
privado0600, sem sobrescrita/symlink, com contexto e escolhas editáveis. O
revisor corrige contas, preenche histórico e submete `review --input ARQUIVO`.
A regra resultante fica em rascunho para ativação humana no fluxo existente.
Alteração do plano/acesso é revalidada. Tentativa incerta/inválida não repete
consumo automaticamente; resposta válida e revisão repetida são reaproveitadas.

O mecanismo não liga o Copiloto nem altera contratação/cobrança do escritório.
Nenhuma chamada real ou classificação da CONTAD foi executada nesta entrega.

## Aferição D-73 por fatos e revisão do proprietário — D-356 (local)

`reconciliation_acceptance prepare` congela contas previstas e origem da
classificação antes da revisão. Recebe `--release`, arquivo com `movement_ids`
e `--output` novo. O JSON privado contém fatos e campos em branco para a
referência humana, sem mostrar a previsão. Somente o proprietário pode
registrar `review --sample UUID --input ARQUIVO`, com contas/centro de custo
esperados e evidência. A trilha é imutável; correção posterior do movimento
não reescreve a previsão medida. Revisão de fonte alterada é recusada.

`report --release IDENTIFICACAO [--run UUID ...]` conta identidades bancárias
distintas e revisadas: FITID/conta para OFX; arquivo/chave/conta nos demais.
Sobreposição/releitura não aumenta amostra; respostas conflitantes impedem
aprovação. Precisão compara débito/crédito/centro de custo previstos com os
revisados, usando limite95% exato e ao menos200 previsões automáticas revisadas
naquele recorte. Confiança da IA, exemplos manuais e amostra não revisada não
viram precisão. O relatório é por conta/recorte; não exige200 eventos em cada
empresa como nova regra comercial nem substitui o desenho representativo
por fluxo exigido em D-73.

Os tempos vêm de processamentos reais identificados, encerrados e com início/
fim válidos. A soma do recorte da empresa é comparada com300s; o proprietário
ainda confirma se a carga representa a rotina completa. Ausência de medição
não é desempenho aprovado. `release_accepted=false` conserva integridade,
retomada/restore, importação no destino e assinatura do proprietário como
provas separadas. Os200 itens dos testes são sintéticos, não aceite CONTAD.

## Retorno contábil Q-47 nesta execução

O responsável pediu pular agora o teste no Domínio. O adaptador publicado
continua `dominio-3.1-pending-homologation`, sem promoção de layout. Sua
candidata atual usa dez colunas CSV separadas por ponto e vírgula, UTF-8 com
BOM, CRLF, dataDD/MM/AAAA e valor decimal com ponto. Conta/histórico/matriz/
centros de custo e tratamento de multipartidas precisam do conjunto aceito
no destino. A prévia privada existente só admite lançamentos novos aprovados
e exclui `source_ledger`/exportações anteriores. Não reutilizar o Razão já
escriturado, alterar parâmetros ou ligar o gate para fabricar essa prova.
