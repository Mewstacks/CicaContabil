# Etapa 09 — Concluir Conciliação e Radar

**Revisão 02/11/2026 — D-302/D-303/V-302:** [verificação CONTAD](../verificacao-conciliador-contad-2026-11-02.md).
As lacunas OFX de V-300 receberam correções e testes locais. A etapa permanece aberta para
Razão independente, títulos a pagar/receber incluídos pelo responsável, DE-PARA com IA e piloto.
O agente ficará no computador da cliente; o acesso ainda será fornecido.

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Revisão em 26/10/2026 — D-300/V-300:** [diagnóstico do conciliador](../diagnostico-conciliador-2026-10-26.md)
verificou `aad2f5a` e reproduziu quatro lacunas na fila OFX. Os controles de
alocação do fluxo novo não cobrem automaticamente essa fila. O conector lê
itens de extrato Domínio; ainda falta comprovar a fonte de Razão e sua ligação
ao fluxo avançado. Não há homologação contábil nova. O aceite NFS-e D-295 não
se estende ao arquivo de exportação contábil.

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

- [x] Confrontar o contrato fornecido em 27/10/2026 e a intenção de contas a pagar/receber e alternativa fiscal, sem ampliar o aceite para a suíte inteira (D-301/V-301).
- [ ] Resolver Q-46/Q-47: fonte de títulos em Q-28, significado de faltas, regras, DE-PARA inicial assistido por IA e operação contábil/fiscal de destino; comprovar execução no recorte da cliente.
- [x] Diagnosticar em 26/10/2026 a comparação extrato × registros disponíveis e detalhar Q-28 para entrevista, com provas sintéticas em V-300.
- [x] Corrigir localmente reutilização do candidato, conta/natureza não comprovadas e sobreposição OFX; compartilhar a identidade e validar a conta antes das duas filas (D-303/V-302).
- [x] Validar concorrência PostgreSQL de confirmação, upload e reconstrução sem apagar decisão humana; preparar auditoria de legado somente leitura.
- [ ] Homologar semântica/contas reais, revisar o legado existente e integrar o resultado das duas cadeias sobre fonte independente.
- [ ] Implementar e homologar títulos a pagar/receber da fonte autorizada, com parcelas/baixas e regras Q-46; inclusão já confirmada em D-302.
- [ ] Demonstrar o DE-PARA inicial assistido por IA do contrato, com revisão humana e controles Q-08/Q-09.
- [ ] Validar fonte independente de lançamentos do Razão, vínculo real do ERP e integração entre `AccountingEntry` e o fluxo de `JournalEntry`, sem assumir que item de extrato seja partida contábil.
- [ ] Concluir OFX, CSV, XLSX e PDF/OCR com layouts e evidências.
- [x] Permitir localmente corrigir mapeamento, classificar, revisar, conciliar e tratar ausência de correspondência.
- [x] Validar localmente cadastros, direção da normalização, competência, capacidade de alocação e partidas equilibradas no fluxo novo; isso não valida natureza/conta na fila OFX nem saldo inicial/final contra o Razão (V-300).
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
arquivo real. V-099 abriu a demonstração isolada em banco temporário e revisou
a Conciliação em desktop e celular, sem overflow horizontal ou erro de console,
sem envio de arquivo ou integração. A existência de código ou testes
anteriores não prova conclusão.
Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no
registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

### Radar ligado à central (D-145)

- [x] Escolha explícita de publicação/empresa, justificativa, atribuição ao solicitante e tarefa idempotente.
- [x] Versão e URL preservadas; coleta atualiza somente vínculos existentes. Mudança/reclassificação reabre análise concluída sem presumir obrigação.
- [x] Recuperação local por escritório, sem coleta; confirmação humana posterior à versão atual.
- [x] Percurso Radar → seleção → atividade → publicação/análises da carteira, com recusa de perfis consultivos.
- [ ] Validar navegador, concorrência PostgreSQL, volume de publicações/vínculos e coleta real autorizada.
- [x] Saúde das fontes prioriza erro da coleta atual, preservando data do último sucesso.

### Extensão operacional D-134 / V-153 (24/09/2026)

- [x] Projetar arquivo na central, distinguindo processamento, tratamento comprovado e importação não confirmada.
- [x] Reavaliar após confirmação, desfazimento, aprovação, revisão e retomada; comando de recuperação por escritório.
- [x] Testar confirmação → conclusão → desfazimento e aprovação → revisão de origem, preservando evidência.
- [x] Reconfirmar relação desfeita com preservação histórica (D-135); revalidar saldo e manter decisões anteriores.
- [x] Navegação contextual por arquivo autorizada com filtros persistidos (D-136).
- [x] Expor histórico detalhado de decisões com paginação e acesso consultivo (D-137).
- [ ] Validar interface no navegador, concorrência e volume.
- [ ] Homologar concorrência, documentos/layouts autorizados e volume. V-153 comprova apenas ambiente local sintético.

> Execute a etapa 09. Complete conciliação, lançamentos revisados e exportações homologadas para os conectores aprovados. Valide documentos reais autorizados e volume. Complete também a operação do Radar, sem ampliar sua promessa para cálculo tributário individual não decidido.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
