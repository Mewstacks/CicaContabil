# Perguntas para concluir o conciliador do contrato

Data: 27/10/2026. Escopo D-301; validação V-301. Esta análise detalha a etapa
09/PC-19 e Q-28/Q-46/Q-47. Não é novo plano para a suíte inteira.

## O que o contrato já define

Fonte: PDF de quatro páginas fornecido pelo responsável nesta conversa, mantido
fora do controle de versão. Leitura textual das quatro páginas e inspeção visual
integral das páginas renderizadas. Esta análise é de requisitos do produto,
sem validação criptográfica das assinaturas ou parecer jurídico.

- Página 2, item 01: conciliador para comparar automaticamente extrato bancário
  e lançamentos contábeis; cadastro inicial do DE-PARA com apoio de IA;
  levantamento, desenvolvimento, implantação e ajustes dentro da carga contratada.
- Página 2: entrega funcionando e testada até **09/11/2026**; **3 horas**
  contratadas. Triagem e suporte remoto estão expressamente fora desse contrato.
- Páginas 2–3: projeto de **R$ 600**, mensalidade de **R$ 200**, vencimento no
  dia **07**; hospedagem/disponibilidade e correção de erros de responsabilidade
  da fornecedora incluídas. Treinamento inicial e acompanhamento dos primeiros
  usos incluídos. Adicionais/mudanças externas e suporte posterior têm condições
  próprias, com hora de R$ 250 e aprovação quando prevista no documento.

Não perguntar de novo valores, vencimento, data de entrega ou inclusão de
treinamento inicial. São condições deste contrato, não uma alteração global
do modelo comercial CICA/D-79/D-109.

O pedido atual acrescenta a intenção de confrontar contas a pagar e receber,
apontar faltas e usar o módulo fiscal como alternativa quando necessário. O
contrato não detalha fontes de títulos, regras ou operação fiscal. Esses
detalhes precisam ser fechados; não concluir que é necessário construir um
sistema financeiro completo, nem presumir que a alternativa fiscal entregue
o mesmo resultado de uma operação contábil.

## Modelo de conferência a esclarecer

Há três fatos distintos: **título previsto**, **movimentação bancária realizada**
e **registro existente no ERP**. Quando o terceiro for fiscal, mostrar qual
documento/estado foi consultado; não apresentá-lo automaticamente como
lançamento contábil ou prova de quitação.

Exemplos de resultados a validar com a contadora:

| Situação | O que precisa ser distinguido |
|---|---|
| Título existe, sem movimento bancário | Pode estar em aberto, ainda não vencido, pago por outro meio ou fora do intervalo; não chamar automaticamente de falta de lançamento. |
| Movimento existe, sem título encontrado | Pode ser título ausente, transferência, tarifa, aplicação ou outra operação; precisa de classificação e evidência. |
| Título e movimento correspondem, sem registro esperado no ERP | Mostrar o registro que falta e sua origem, sem criar ou baixar automaticamente. |
| Registro no ERP sem movimento bancário correspondente | Pode ser pendência, duplicidade, pagamento em espécie ou compensação; precisa de explicação. |
| Valores ou datas divergem | Separar pagamento parcial, agrupamento, juros, desconto, retenção, tarifa e erro efetivo. |

São hipóteses para a entrevista, não regras aprovadas ou estados implementados.

## Roteiro prioritário para a cliente

As perguntas têm numeração apenas de leitura. Q-28/Q-46/Q-47 continuam sendo os
registros canônicos; o roteiro não cria outro controle de pendências.

| Ordem / referência | Pergunta pronta para fazer | O que a resposta destrava |
|---|---|---|
| 1 · Q-28 | **Qual sistema vocês usam e em quais módulos ficam as informações? É Domínio local, servidor remoto ou Web/Onvio? Qual versão e quem cuida do acesso técnico?** | Identificar a instalação desta cliente. D-74 é de outro escritório e não responde esta pergunta. Pedir informação técnica, nunca senha no chat. |
| 2 · Q-28 | **Onde estão as contas a pagar e receber hoje: no Domínio, sistema financeiro dos clientes ou planilhas? Conseguem mostrar/exportar a lista com parcelas, vencimentos, baixas e valores ainda em aberto?** | Encontrar a fonte real dos títulos e sua atualização. Sem isso, extrato × Razão não mostra todo o contas a pagar/receber. |
| 3 · Q-28 | **Quais empresas e contas bancárias entram na primeira entrega, quais formatos de extrato fornecem e qual o volume mensal?** | Fechar cobertura inicial, conta por empresa, arquivos e dimensionamento. Não presumir a carteira inteira ou todos os bancos. |
| 4 · Q-46 | **Quando vocês dizem “apontar o que falta”, precisam identificar título sem pagamento/recebimento, pagamento sem título, lançamento ausente, documento ausente ou todas essas situações?** | Definir o resultado esperado e impedir que estados diferentes recebam a mesma conclusão. Solicitar um exemplo real de cada situação desejada. |
| 5 · Q-46 | **O que vocês usam para reconhecer que um pagamento pertence a um título: documento/parcela, cliente ou fornecedor, identificação PIX/boleto, histórico, data ou valor?** | Definir chaves e evidência independente. Mesmo valor e data não bastam para resolver ambiguidade. |
| 6 · Q-46 | **Como tratam diferença de dias ou valores, pagamento parcial, um pagamento para vários títulos, tarifas, juros, descontos, retenções, estornos e transferências entre contas?** | Estabelecer regra de agrupamento/alocação e exceções, com exemplos revisados. Não inventar tolerância ou tratar vencimento como data de pagamento. |
| 7 · Q-46 | **O DE-PARA liga exatamente o quê a quê: conta bancária, descrição/categoria, cliente/fornecedor e conta contábil? Já existe plano de contas ou mapa que devemos aproveitar? Quem confere o cadastro inicial sugerido pela IA?** | Determinar entradas e saídas do DE-PARA, códigos permitidos, abrangência por empresa e validação contábil. Se o destino for fiscal, esclarecer separadamente se envolve acumulador ou outro código. |
| 8 · Q-47 | **Depois de conferir, o sistema deve só mostrar as diferenças, gerar arquivo para importar ou executar uma ação no sistema de vocês? Qual ação exatamente?** | Separar relatório, sugestão, geração de arquivo, importação e baixa. Confirmação de conciliação não autoriza movimento no ERP. |
| 9 · Q-47 | **Se a integração precisar ser pelo Fiscal, qual resultado vocês precisam nessa tela: consultar documentos/títulos, escriturar documento, informar recebimento/pagamento ou outra operação? Conseguem mostrar como fazem isso hoje?** | Especificar a alternativa fiscal. A viabilidade, importador e retorno serão conferidos pelo desenvolvimento com o técnico do ERP. Não prometer equivalência sem prova. |
| 10 · Q-28/Q-46 | **Quem vai revisar divergências e usar a ferramenta? Em qual período a equipe terá os dados e estará disponível para testar e receber o treinamento inicial?** | Organizar configuração, revisão e implantação até a data contratual. O aprovador do módulo e as métricas gerais já estão em D-72/D-73; não reabri-los. |

## O que solicitar como material

Por canal protegido, após autorização do recorte:

1. Uma empresa e um mês já conferido manualmente, com conta bancária identificada.
2. Extrato original, lista de contas a pagar/receber e o registro contábil ou
   fiscal usado na rotina atual, todos do mesmo recorte. Trazer também baixas
   e títulos de meses anteriores quando expliquem o movimento do mês.
3. Plano de contas e eventual DE-PARA existente; exemplos de resultado esperado,
   inclusive sobras e divergências. Se a empresa não usa controle formal de
   títulos, registrar isso antes de definir o que o conciliador pode apontar.
4. Demonstração da rotina do ERP e, se existir, seu layout de importação com
   campos obrigatórios, identificadores, regras de duplicidade e retorno.

Esse conjunto inicial ajuda a fechar a especificação. Não substitui a amostra
independente de 200 itens nem os demais critérios aplicáveis de D-73.

## O que cabe ao desenvolvimento, sem transferir à cliente

- Confirmar, com o técnico indicado, a rota permitida e os campos disponíveis
  do ERP. A cliente explica o trabalho e o resultado; não precisa escolher API,
  SQL ou arquitetura.
- Corrigir as quatro lacunas reproduzidas em V-300 antes de um piloto confiável:
  reutilização de candidato, natureza não validada, duplicação entre arquivos e
  bloqueio de conta incoerente entre os fluxos.
- Garantir uma fonte independente para cada fato comparado. O agente atual
  envia itens de extrato Domínio; isso não comprova títulos ou partidas do Razão.
- Completar a ligação entre espelho e conciliação avançada. O rótulo de origem
  “Títulos ou obrigações” não é prova de modelo completo de contas a pagar/receber.
  A importação `ImportBatch.Kind.OBLIGATIONS` inspecionada trata guias fiscais
  DAS/MEI/DCTFWeb, não fornecedores/clientes com parcelas e baixas genéricas.
- Demonstrar o DE-PARA inicial **com apoio de IA** exigido no contrato. O serviço
  de conciliação inspecionado aplica regras e correções manuais; não foi encontrado
  nele um fluxo completo de geração inicial de mapa por IA. Enum de sugestão ou
  existência do Copiloto não provam essa entrega. Levantar catálogo e exemplos,
  preservar revisão humana e resolver Q-08/Q-09 antes de chamada paga ou envio
  de conteúdo à IA externa. Não perguntar se IA faz parte: já está no contrato.
- Validar relatório de diferenças, estados, atualização e recuperação. Se houver
  retorno ao ERP, registrar importação/baixa somente mediante retorno verificável;
  não habilitar exportação contábil usando o aceite anterior de NFS-e.
- Conferir o recorte contra a carga e data contratadas antes de assumir novas
  funcionalidades. Dados e viabilidade ainda não conhecidos impedem afirmar
  que todos os requisitos adicionais cabem nas três horas; o documento não
  autoriza automaticamente cobrança ou horas adicionais.

## O que não deve bloquear esta entrega por inferência

Triagem, Radar, DTE, Parcelamentos, DCTFWeb, Rentabilidade, treinamento de modelo
local e demais módulos da suíte não integram automaticamente o contrato do
conciliador. Suas pendências gerais permanecem registradas, mas não devem virar
perguntas obrigatórias a esta cliente. Precificação SaaS geral, integração de
cobrança e novas vendas também não devem desviar o levantamento funcional.

## Evidência desta revisão

- PDF: quatro páginas extraídas e quatro páginas inspecionadas visualmente.
  Campos de assinatura observados sem validação criptográfica.
- Inspeção local de `src/apps/hub/models.py`, `imports.py` e
  `reconciliation_service.py`, confrontada com D-300/V-300 e registros canônicos.
- Não foram repetidos os testes de V-300: continuam evidência de 26/10, não
  execução de 27/10. Esta entrega é somente documental e de análise estática.
- Nenhum dado de ERP/cliente, credencial, IA externa, custo, deploy ou interface
  foi alterado. O PDF, assinaturas e identificadores não foram adicionados ao Git.
