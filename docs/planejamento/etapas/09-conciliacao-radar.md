# Etapa 09 — Concluir Conciliação e Radar

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Em andamento: funções e controles locais revalidados em V-037.
V-047/V-049/V-050/V-062/V-064 tiparam formulários, serviço, limites de entrada,
multipart, navegação e tarefas, preservando a integração local. V-068 completou
a tipagem da view de conciliação e sua regressão focada; V-076 eliminou o corte
silencioso da fila OFX × Domínio e V-080 fez o mesmo na trilha de auditoria.
V-081 eliminou o corte da lista de alertas do Radar. V-085 eliminou os cortes
das trilhas de processamentos e exportações da Conciliação. V-090 eliminou o
corte da lista de candidatos no detalhe de um movimento. V-092 preservou as
páginas das três trilhas da Conciliação quando se navega pela carteira de
movimentos. V-093 estendeu essa preservação de contexto à fila OFX × Domínio.
Não há homologação de
arquivo, ERP, fonte oficial ou volume.

**Dependências:** 03–05; exportação Siescon depende de 04.

**Decisões relacionadas:** D-35, D-54, D-55.

## Escopo e checklist

- [ ] Concluir OFX, CSV, XLSX e PDF/OCR com layouts e evidências.
- [x] Permitir localmente corrigir mapeamento, classificar, revisar, conciliar e tratar ausência de correspondência.
- [x] Validar localmente contas, direção, competência, saldos e lançamentos equilibrados.
- [ ] Homologar exportações Domínio e Siescon sem apresentar exportação como importação concluída.
- [ ] Validar volume com PostgreSQL e corpus representativo.
- [ ] No Radar, comprovar coleta, atualização, origem e falhas, preservando a proposta de acompanhamento de publicações.

## Bloqueios e responsabilidade

Q-28; layouts reais e amostra independente. As métricas aplicáveis estão decididas
em D-73 e ainda precisam de prova.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Reimportação, layout alterado, OCR insuficiente, lançamento desequilibrado,
ambiguidade, saldo insuficiente, partidas compostas, reexportação e fonte do
Radar indisponível. V-037 reexecutou essas proteções localmente, exceto o OCR
em português, que ficou explicitamente ignorado por ausência da dependência local.

**Critério de aceite:** Processamento auditável, nenhuma conciliação sem evidência independente e exportações conferidas nos sistemas de destino.

## Evidências e próximo passo

V-037 registra 46 testes de domínio, um skip de OCR local e quatro testes de
interface/demo, além de lint/Django/diff limpos. V-047/V-049 revalidaram
formulários e serviço com 35 testes (um skip de OCR); V-050 validou os caminhos
locais de importação com 57 testes. Ruff, Django, migrações e diff ficaram
limpos, sem tocar integrações. V-068 incluiu conciliação em 119 testes locais e
concluiu a verificação estática global, sem tocar integrações. V-076 acrescentou
paginação com 101 correspondências de teste, preservando filtros e limitando as
evidências à página visível. V-080 paginou a trilha de auditoria com 201 eventos
fictícios, preservou a ação no retorno e a exercitou em navegador local. V-081
paginou 101 alertas sintéticos do Radar, preservando seus filtros e sem alegar
coleta ou visualização em volume na demonstração. V-085 paginou 21 execuções e
21 exportações sintéticas da Conciliação, preservando as duas trilhas de forma
independente, sem importar, reprocessar ou gerar arquivo. V-090 paginou 51
candidatos sintéticos da conciliação no detalhe do movimento, mantendo a
confirmação humana e evidência obrigatória; a demonstração temporária alcançou
a segunda página em 390 px sem overflow ou erro de console. Nenhuma homologação nova é
atribuída a esta etapa. V-092 confirmou em teste a independência entre 21
processamentos, 21 exportações e 51 movimentos sintéticos, sem executar ação
operacional. V-093 confirmou que a terceira página de 101 correspondências
sintéticas mantém as demais páginas abertas. V-097 passou a recusar XLSX
corrompido antes da persistência e limitou a prévia CSV às 51 linhas exibidas;
V-098 estendeu a recusa prévia a PDF malformado, sem retirar o OCR local de
documentos digitalizados válidos. A prova continua sintética, sem layout ou
arquivo real. A existência de código ou testes
anteriores não prova conclusão.
Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no
registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 09. Complete conciliação, lançamentos revisados e exportações homologadas para os conectores aprovados. Valide documentos reais autorizados e volume. Complete também a operação do Radar, sem ampliar sua promessa para cálculo tributário individual não decidido.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
