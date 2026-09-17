# Conciliação e lançamentos: decisões verificáveis

## Escopo entregue nesta iteração

O domínio novo é paralelo à conciliação OFX legada. Ele preserva arquivos de origem,
execuções persistidas, layouts versionados, movimentos normalizados, regras, lançamentos,
alocações e exportações. A migração `0034_reconciliation_module` cria somente estruturas
aditivas; não reclassifica nem inventa evidências para o histórico.

## Decisões operacionais

- Um hash no escopo do escritório e da empresa trata o mesmo arquivo como reenvio; ele não
  apaga o original nem cria uma segunda execução.
- O layout de CSV/XLSX só é reutilizado se a assinatura dos cabeçalhos continuar igual.
- O mapeamento enviado pela tela usa controles HTML nomeados e é revalidado contra os
  cabeçalhos da própria prévia. Isso permite salvar o layout sem depender de JavaScript e
  rejeita colunas inexistentes ou reutilizadas em campos normalizados diferentes.
- Um envio inválido retorna o próprio assistente com todos os contextos operacionais, preserva
  os valores permitidos, mostra erros junto aos campos e desloca o foco para o resumo de erro.
- Um PDF textual preserva página e linha. Um PDF sem texto tenta Tesseract local, quando o
  executável e o idioma português estiverem instalados; caso contrário vai para revisão.
- A evidência de PDF inclui página e região de origem: em PDF textual a região é registrada
  em pontos do PDF; no OCR, em pixels da imagem renderizada a 2x. O operador pode abrir o
  PDF privado na página indicada, sem expor uma URL pública ou manter o binário em logs.
- Leitura local de OCR abaixo de 90 não pode terminar pronta por causa de uma regra. O item
  segue para revisão com o motivo e o limiar registrados; qualidade de leitura não é tratada
  como certeza de classificação contábil.
- Regra criada por correção manual é deliberadamente estreita: descrição exata e natureza,
  sempre dentro da empresa. Regras contraditórias ficam como conflito.
- Conciliação confirmada requer evidência, empresa comum, lançamento equilibrado e saldo
  disponível nos dois lados. O lançamento gerado pelo próprio movimento não é evidência
  independente.
- A exportação Domínio grava bytes e hash imutáveis. O adaptador está marcado
  `pending-homologation`: gerar arquivo não confirma importação no Domínio.
- Reexportação exige motivo e preserva o vínculo ao arquivo original. Partidas compostas
  que não podem ser pareadas pelo formato oficial ficam bloqueadas, sem truncamento.
- Reaplicar regras cria uma execução persistida separada, informa quantos itens foram
  atualizados e não altera decisões manuais, conciliações confirmadas nem lançamentos
  aprovados/exportados. Um despachante periódico recupera execuções aguardando depois de
  uma interrupção entre o commit do banco e a entrega ao worker.

## Limites que ainda impedem uma declaração de produção

- O adaptador de exportação para Domínio continua bloqueado por configuração até existir
  homologação real com arquivo de referência e importação conferida no Domínio. Os testes
  internos verificam estrutura e imutabilidade, não compatibilidade homologada.
- Os parsers e o OCR foram exercitados com fixtures sintéticas. A matriz de layouts de
  clientes, o corpus independente de documentos físicos e a medição em PostgreSQL com
  100 mil movimentos ainda precisam de execução no ambiente de homologação.
- A operação aceita PDFs produzidos por scanner ou celular; integração direta com scanner,
  separação automática de lotes físicos e captura nativa não fazem parte desta iteração.
- A configuração e a visão geral foram validadas em servidor isolado com Playwright em 1440 e
  390 px, nos temas claro e escuro, incluindo erro de formulário, foco, campos rotulados,
  overflow e console. A validação visual ainda precisa cobrir estados com movimentos, mapeamento,
  PDF e exportação antes de habilitar o recurso para uso operacional.
- Nenhum deploy foi realizado. O destino CICA, a versão candidata e as condições de
  capacidade para armazenamento e OCR precisam ser identificados antes de publicar; não há
  autorização implícita para provisionar recursos ou assumir custos.

## Navegação Integra Contador

`Caixa DTE` é o atalho para uma tarefa conhecida: abrir mensagens, acompanhar prazos e
preparar consultas por empresa. `Central Integra Contador` é a entrada de descoberta para
quem precisa escolher entre DTE, parcelamentos e DCTFWeb. Essa separação evita que uma
caixa operacional seja escondida atrás de uma página de catálogo, sem duplicar funções.

## Configuração central

O console da plataforma separa credenciais Serpro e certificado A1. Ambos são alteráveis
somente por desenvolvedor com MFA; chaves, senha e arquivo são cifrados e de escrita única.
O cliente Integra usa os valores do console quando presentes e mantém as variáveis de ambiente
como compatibilidade para instalações existentes. Salvar a configuração não dispara consulta
ao Serpro; uma operação externa continua exigindo o fluxo e a autorização próprios.

## Referências consultadas

- OFX Banking Specification 2.3, Financial Data Exchange.
- [Domínio: importação de lançamentos](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=4707).
- [ofxtools parser](https://ofxtools.readthedocs.io/en/latest/parser.html),
  [openpyxl optimized mode](https://openpyxl.readthedocs.io/en/stable/optimized.html),
  [pdfplumber](https://github.com/jsvine/pdfplumber) e
  [Tesseract quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html).
- [Mercury transactions dashboard](https://www.saasframe.io/examples/mercury-transactions-dashboard?733a3d33_page=2),
  [SaaSFrame inbox patterns](https://www.saasframe.io/patterns/inbox) e
  [Refero SaaS app workflow guidance](https://styles.refero.design/ai-agents/saas-app-design-prompts).

As referências orientam hierarquia de fluxo e interação. Nenhum ativo visual, texto,
dado de cliente ou implementação proprietária foi copiado.
