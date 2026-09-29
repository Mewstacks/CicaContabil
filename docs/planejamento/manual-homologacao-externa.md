# Manual de homologação externa do CICA

Este manual separa a validação real do que já foi testado localmente. Não autoriza contratação, publicação, chamadas cobradas ou uso de dados pessoais sem a aprovação correspondente.

Para a lista prática de materiais, decisões e donos, use também o [roteiro do responsável para liberação](roteiro-do-responsavel-para-liberacao.md). Este manual permanece focado no procedimento de homologação.

## Regra de liberação

Cada integração só pode ser anunciada quando houver: contrato ou autorização válida, ambiente de homologação, amostra autorizada, teste de ponta a ponta, evidência de recuperação e responsável operacional definido. Uma falha de fonte deve mostrar a última observação conhecida com data e nunca ser apresentada como ausência de pendência.

## Domínio Local

**Fornecer:** DSN somente leitura, servidor Windows homologado, duas empresas descartáveis com dados conhecidos, operador responsável e janela de teste.

1. Instalar o agente e gerar o pareamento no CICA.
2. Confirmar TLS, identidade do agente e leitura sem escrita.
3. Comparar empresas, competências, saldos, folha e obrigações com a tela do Domínio.
4. Simular indisponibilidade do DSN e confirmar estado desatualizado, sem apagar a última leitura.
5. Revogar pareamento e comprovar que sincronizações futuras falham de forma segura.

**Aceite:** contagens e amostras reconciliadas, nenhuma escrita no Domínio, auditoria completa e recuperação documentada.

## Domínio Web e NFS-e

**Fornecer:** um backup completo descartável autorizado, chave do backup, especificação técnica do layout ou apoio formal do fornecedor, XMLs NFS-e de teste e rotina automática configurada em ambiente não produtivo.

1. Enviar o backup uma única vez, sem entregar credenciais do Onvio.
2. Registrar hash, versão do extrator, empresas encontradas e acumuladores normalizados.
3. Conferir acumuladores por empresa e histórico imutável no CICA.
4. Gerar pacote de conferência por empresa e competência; conferir manifesto e hash.
5. Testar a importação pela rotina automática do Domínio e guardar retorno verificável.

**Aceite:** o layout é comprovado; o CICA não duplica acumuladores; cada resultado está vinculado a empresa, lote e competência; confirmação de importação só ocorre com retorno da rotina.

## Siescon

**Fornecer:** contrato técnico, versão instalada, mecanismo permitido, identificador de empresa, layouts, ambiente de teste e contato técnico.

1. Criar o adaptador somente para capacidades documentadas.
2. Mapear cada entidade para o modelo do CICA com proveniência.
3. Comparar uma amostra por área com a origem.
4. Simular resposta parcial, timeout e alteração de versão.

**Aceite:** capacidades ausentes seguem indisponíveis; não existe leitura presumida de tabelas; reprocessamento não duplica tarefas.

## Serpro / Integra Contador

**Fornecer:** contrato, catálogo habilitado, procurações de homologação, credenciais, tabela de custo, política de retry e empresas de teste.

1. Registrar serviço, versão, efeito legal, procuração, tarifa e idempotência no catálogo interno.
2. Testar consultas e guardar protocolo, custo e retorno.
3. Para transmissão: preparar, validar, mostrar conteúdo/custo, confirmar humano, executar a versão aprovada e consultar resultado.
4. Testar duplo clique, timeout, retorno tardio e conteúdo alterado após aprovação.
5. Reconciliar custo do fornecedor com o livro de consumo por escritório.

**Aceite:** nenhuma transmissão é repetida cegamente; ciência oficial exige ação explícita; ajustes e descontos não criam margem para o CICA.

## E-mail, OAuth e Triagem

**Fornecer:** aplicativo OAuth por escritório quando aplicável, redirect HTTPS, política de consentimento, caixa de teste, arquivos limpos/maliciosos e destino de arquivo autorizado.

1. Validar Google, Microsoft e IMAP em caixas de teste.
2. Verificar escopos mínimos, revogação de token e falha de consentimento.
3. Testar anexo duplicado, arquivo inválido, PDF múltiplo e tentativa de instrução maliciosa.
4. Confirmar que recebido não é arquivado até revisão e destino confirmado.

**Aceite:** isolamento por escritório, quarentena e trilha de auditoria comprovados; segredos não aparecem em logs.

## IA por API e processamento local

**Fornecer:** política de dados aprovada, fornecedor/conta autorizados, limites comerciais aprovados, corpus sintético e conjunto de avaliação revisado.

1. Validar mascaramento, recusa de identificadores não autorizados e isolamento por escritório.
2. Testar ausência de fonte, fonte desatualizada e tentativa de acesso entre empresas.
3. Confirmar reserva concorrente de saldo e teto mensal.
4. Medir precisão por tipo de tarefa; não usar confiança declarada pelo modelo como métrica.

**Aceite:** respostas citam origem/atualização; cálculos, permissões e confirmações legais permanecem determinísticos.

## Relatórios Node/TypeScript

**Fornecer:** URL interna, segredo ativo e anterior durante rotação, worker Celery, armazenamento privado e amostras contábeis autorizadas.

1. Gerar PDF e XLSX da mesma fotografia e comparar números.
2. Testar segredo inválido, segredo anterior durante rotação, queda do worker e artefato ausente.
3. Conferir download após revogação de acesso à empresa.

**Aceite:** nenhuma saída alternativa Python; PDF/XLSX preservam filtros, versão, fonte, pendências e hash.

## Asaas e operação comercial

**Fornecer:** conta de sandbox, webhook assinado, política de inadimplência aprovada, catálogo/preços aprovados e contratos de teste.

1. Testar fatura, Pix, boleto, cartão, atraso, estorno e reativação.
2. Testar contrato manual isolado de qualquer webhook Asaas.
3. Conferir capacidade por usuário ativo e raiz de CNPJ; filiais não devem consumir outra unidade comercial.
4. Validar franquia de IA, adicional autorizado e teto mensal sem cobrança surpresa.

**Aceite:** valores congelados por contrato, eventos idempotentes e modo somente leitura conforme política aprovada.

## Produção e piloto

Antes do piloto: backup/restauração testados, monitoramento, procedimentos de incidente, responsáveis de suporte, termos e retenção aprovados. O piloto deve medir tempo de identificar fechamentos, retrabalho por divergência, alertas úteis e tempo de entrega gerencial contra linha de base.

**Rollback geral:** desabilitar a capacidade do escritório, preservar evidências e leituras anteriores, revogar segredos/pareamentos quando necessário e abrir incidente auditável. Não apagar documentos, consumo ou protocolos para "resolver" uma falha.

## Migração comercial: tokens legados para capacidade e IA em reais

**Decisão obrigatória antes de ativar:** tabela de cada pacote, usuários incluídos, raízes de CNPJ incluídas, franquia de IA em reais, preço do adicional, teto mensal padrão/máximo, regra para clientes legados e data de vigência. Não substitua valores por equivalência de tokens sem aprovação comercial.

1. Inventariar contratos ativos, manuais e em teste, incluindo módulos, exceções e uso histórico.
2. Definir uma versão comercial por contrato, preservando a versão anterior para auditoria e faturas históricas.
3. Recalcular capacidade com usuários ativos e raízes de CNPJ ativas; filiais continuam operacionais, mas não consomem outra raiz.
4. Mostrar previamente ao administrador a capacidade atual, registros sem raiz de CNPJ e qualquer excesso; não cobrar nem bloquear automaticamente.
5. Converter apenas após aceite explícito ou regra contratual aprovada. Contratos manuais exigem lançamento e aceite próprios.
6. Manter o livro de uso de IA em reais de uso CICA, com reserva antes da execução, adicional autorizado e teto mensal.
7. Reconciliar cada competência: capacidade medida, franquia, reservas, consumo, adicional, ajustes e fatura.

**Aceite:** nenhuma cobrança surpresa; arquivo histórico permanece legível; concorrência não ultrapassa o teto; arquivamento não altera consumo anterior; acesso do usuário não é concedido por uma filial compartilhada.


## Recorrência mensal da central operacional

Implementação local: `hub.generate_recurring_activities`, agendada no Celery Beat a cada hora. A migration `hub.0054_activity_recurrence_cursor` acrescenta apenas o cursor de próxima competência na atribuição do modelo; aplicar nas etapas de migração antes de iniciar workers com esta versão.

1. Em ambiente de homologação, criar modelo mensal e atribuição pelo administrador. A primeira execução começa no mês corrente; não fabrica histórico anterior.
2. Executar a tarefa e conferir competência, prazo, responsável, evento de geração e auditoria `hub.activity.recurrence_advanced`. Reexecutar e comprovar ausência de duplicação.
3. Interromper durante uma atribuição: atividade e cursor devem voltar juntos. A próxima execução retoma do cursor; falha isolada fica em `hub.activity.recurrence_failed`, sem conteúdo de cliente.
4. Uma parada de vários meses recupera até 12 competências por atribuição a cada execução; o restante fica para o próximo ciclo. Não avance cursores manualmente para limpar falhas.
5. Pausa/reativação pela tela reinicia a referência automática no mês corrente, preservando atividades existentes. Revisão de períodos anteriores deve ser uma geração manual explícita.
6. Revogar a carteira do responsável e confirmar que novas tarefas ficam sem responsável, com evento explicativo. A atribuição do modelo não é apagada nem concede acesso.
7. Confirmar ausência de geração para demonstração, escritório/empresa/modelo inativos, lifecycle bloqueado, autorização externa vencida e NFS-e exclusivo.
8. Testar duas execuções simultâneas no PostgreSQL e uma interrupção real do worker antes de liberar. Os testes SQLite de repetição/rollback não comprovam bloqueio concorrente em produção.

Recuperação: pausar a atribuição pela interface ou desabilitar a entrada de Beat; preservar atividades, cursor e auditoria. Corrigir a causa apontada pelo evento de falha e retomar. Nenhuma transmissão, leitura de ERP, chamada tarifada ou conclusão automática ocorre nesta tarefa.

### Conferência dos requisitos de fechamento (D-127)

Na amostra autorizada, confrontar cada fechamento com processamento na fonte, aceitação das obrigações e evidências vinculadas. Marcar tarefa como concluída sem esses requisitos não pode produzir fechamento comprovado. Transmissão pendente de retorno, fonte desatualizada ou indisponível, reabertura e rejeição devem permanecer distinguíveis. Sem ERP, integração não configurada por si só não bloqueia a comprovação humana; anexar documento não confirma sua revisão. Dispensa exige motivo, responsável, data e evidência. Guia não paga permanece atividade independente.

A validação local cobre a regra; ainda é necessário inspecionar a futura apresentação agregada e os retornos reais homologados. Nenhuma dispensa ou aceitação oficial foi criada automaticamente por essa regra.

### Conferir fechamentos na Visão geral (D-128)

1. Entrar como colaborador com carteira atribuída e selecionar a competência na seção Fechamentos da carteira.
2. Conferir as três áreas de cada empresa. A página considera os requisitos de todos os responsáveis, não apenas os itens de Meu trabalho.
3. Abrir o detalhe do requisito e confrontar o histórico/evidência com a fonte autorizada. Tarefa sem processamento obrigatório ou obrigação obrigatória não entra nesse resumo; validar a cobertura dos modelos com o responsável contábil antes de tratar o conjunto como completo.
4. Verificar empresa sem modelo, ausência de atividades na competência, obrigação transmitida ainda não aceita, processamento reaberto e fonte indisponível. Nenhum desses casos deve aparecer como fechamento comprovado.
5. Conferir pagamento separado, empresas da segunda página e revogação de acesso. Trocar competência não deve ampliar carteira.
6. Validar desktop/mobile, foco de teclado, expansão dos requisitos, filtro e retorno à ficha. Essa inspeção permanece pendente enquanto o transporte do Playwright não estiver disponível.

### Recuperar atividades de revisões NFS-e (D-129)

Após aplicar a migration 0055 no ambiente autorizado, revisões novas passam a gerar vínculo operacional e decisões novas concluem a atividade junto do caso. A entrada NFS-e exclusiva permanece própria; atividades são projeção local e não confirmam importação no Domínio.

Para registros anteriores ou reconciliação após incidente, executar no ambiente do escritório:

```powershell
uv run python manage.py sync_nfse_activities --organization UUID_DO_ESCRITORIO
```

O comando só lê casos locais e cria/atualiza a projeção daquele escritório, sem consultar provedor. Pode ser repetido; cada revisão é transacional. Se falhar em registro inconsistente, os anteriores permanecem reconciliados e o caso com falha não recebe conclusão parcial. Investigar a evidência original, sem preencher autor/data/acumulador por suposição, corrigir pelo fluxo autorizado e repetir. Demonstrações são recusadas. Não apague atividades ou evidências para recuperar.

No piloto, capturar revisão, observar atividade na carteira, resolver com acumulador permitido e conferir atividade/evidência/artefato/histórico. Testar repetição e dois cliques simultâneos em PostgreSQL. Confirmar que revisão aberta não pode ser encerrada pela central, que competência é a de emissão (inclusive virada de mês) e que revisão concluída não marca ERP fechado ou importado. O vínculo/navegação direta na interface ainda precisa de validação visual.

### Recuperar atividades de Triagem (D-130)

Aplicar a migration 0056 no ambiente autorizado. Para recompor a projeção dos arquivos já identificados de um escritório:

```powershell
uv run python manage.py sync_triage_activities --organization UUID_DO_ESCRITORIO
```

O comando usa estados locais, sem ler e-mail, chamar IA, copiar arquivos ou consultar fornecedor. Ele não revalida a existência atual da cópia arquivada: a evidência registra a confirmação persistida pela Triagem. É repetível e cada arquivo tem transação própria. Caso uma empresa não corresponda à atividade, investigar a atribuição original; o comando recusa transferir histórico. Não corrigir essa situação apagando evidências.

Validar aprovação sem arquivamento, falha de cópia, retorno Windows com hash errado, confirmação válida, repetição e arquivo sem empresa. Somente a confirmação de arquivamento gera conclusão local; não deve fechar ERP ou aceitar obrigação. Verificar existência/integridade real da cópia nos testes de armazenamento e agente já previstos. Homologação real e navegação visual permanecem pendentes.

### Navegar da atividade ao módulo e conferir perfis (D-131)

Na atividade de revisão NFS-e ou arquivamento, usar Abrir revisão/Abrir arquivo. Conferir estado e empresa no destino antes da decisão. O link não transmite, importa ou confirma arquivamento por si só. Concluir o fluxo de origem e voltar à atividade para conferir resultado/evidência. Quando o módulo não estiver liberado, revisar as permissões com o administrador; não usar alteração de URL para contorná-las.

Repetir a leitura com auditor/financeiro: consultas permitidas devem funcionar, mas POST de evidência, impedimento e conclusão não deve gravar nada. Revogar a carteira e confirmar recusa ao acesso direto. Validar tela e foco desktop/mobile quando o navegador de validação estiver disponível. Tarefas novas sem responsável ainda exigem o fluxo de atribuição em implementação; não atribuir automaticamente ao usuário que apenas abriu a tela.

### Atribuir trabalho para a agenda diária (D-132)

1. Como proprietário/administrador, abrir Carteira ou Gestão → atividade → Responsável pela atividade.
2. Escolher pessoa operacional com acesso ativo à empresa, informar motivo e salvar. Se não aparecer, corrigir a carteira/perfil na gestão de equipe; a atribuição não concede acesso.
3. Conferir a tarefa em Meu trabalho da pessoa. Para devolver à carteira compartilhada, escolher Sem responsável e registrar motivo.
4. Abrir duas abas na mesma atividade, salvar responsáveis diferentes em sequência e confirmar recusa ao segundo envio desatualizado. Recarregar antes de tentar novamente.
5. Conferir histórico/auditoria, ausência de mudança no responsável padrão do modelo e impedimento de redistribuir tarefa concluída/dispensada.

Testar teclado, foco no resumo de erros, seleção móvel e concorrência real em PostgreSQL. A operação local já tem testes de fluxo, mas o navegador de validação continua indisponível nesta sessão.

### Ordem dos retornos das fontes (D-133)

Os adaptadores devem enviar observed_at com fuso e reutilizar o instante original em tentativas repetidas. Sem instante, cada chamada é tratada como observação nova. Não substituir data de medição por data de reprocessamento.

Na homologação, enviar retorno atual e depois retorno antigo de reabertura/falha. O histórico deve conter ambos, mas estado atual e última fotografia não podem retroceder. Repetir exatamente o mesmo retorno não cria novo evento ou evidência. Conferir dimensões separadas (processamento e obrigação) e dois valores divergentes para o mesmo instante: o valor vigente é preservado, a atualização fica desatualizada e exige conferência com a fonte. Um retorno novo da outra dimensão não resolve essa divergência.

Evidência de fonte aponta a observação aplicada e mantém sua data; não conclui atividade automaticamente. Esta rotina ainda depende da ligação dos adaptadores homologados e dos testes de concorrência no banco de produção. Não há chamada externa neste teste local.

### Atividades da Conciliação (D-134)

Após aplicar a migration 0057 no ambiente autorizado, arquivos novos alimentam a central. Para recompor arquivos existentes, executar no ambiente correto `uv run python manage.py sync_reconciliation_activities --organization UUID_DO_ESCRITORIO`. O comando lê registros locais, não importa arquivos nem chama ERP; repetições não duplicam atividades ou evidências. Corrigir eventual divergência de empresa antes de repetir, sem transferir o histórico automaticamente.

Conferir arquivo pendente, processamento com erro e leitura concluída ainda aguardando revisão. Tratar todos os movimentos: conciliação integral com evidência, lançamento aprovado da revisão vigente ou exclusão explícita documentada. Confirmar conclusão local e depois desfazer uma conciliação ou revisar um movimento: a atividade deve reabrir, preservando evidências anteriores. Atribuir o responsável pelo fluxo D-132 para entrar em Meu trabalho. Nada disso comprova importação no Domínio.

Ainda validar concorrência PostgreSQL, volume, navegação contextual até o arquivo e renderização.

### Reconfirmar uma conciliação desfeita (D-135)

Para localizar o trabalho, abrir a atividade → Abrir arquivo na Conciliação. O destino restringe processamentos e movimentos ao arquivo e mantém o filtro ao buscar/paginar. Voltar à atividade retorna à evidência; Ver todos os arquivos remove o recorte. Indicadores gerais, exportações e OFX continuam sendo da carteira, conforme aviso. Validar módulo desabilitado e revogação de acesso à empresa; links diretos não devem contornar essas restrições.

Aplicar também a migration 0058 no ambiente autorizado. Depois de desfazer, confirmar novamente a relação pelo fluxo existente, informando a evidência atual. O sistema revalida o saldo dos dois lados; não aumentar artificialmente valores para contornar uma recusa. A atividade deve concluir novamente somente se todos os movimentos estiverem tratados.

No detalhe do movimento, consultar Histórico das decisões: confirmação anterior, desfazimento e confirmação nova, com evidências preservadas. Registros anteriores à migration são identificados como legado antes da primeira alteração; data desconhecida aparece como não registrada. Expandir Consultar evidência preservada para verificar o conteúdo. Paginação exibe 20 decisões por vez, sem perder a página dos candidatos. Ainda validar interface desktop/mobile; testes de renderização Django não substituem inspeção no navegador. Repetir desfazimento não cria evento adicional e uma relação já confirmada recusa alocação duplicada. Validar concorrência PostgreSQL antes da liberação.

Repetir a consulta como auditor: histórico disponível para a empresa autorizada, sem formulários de revisão/confirmação; POST direto deve ser recusado. Ausência de autor é exibida como não registrado, sem atribuir automaticamente a decisão ao sistema.

### Importar totais da folha (D-138)

1. Aplicar a migration 0059 no ambiente autorizado. Como proprietário/administrador, abrir Configuração inicial e escolher a fonte das empresas cadastradas.
2. Selecionar Totais da folha (documento informado), baixar o modelo CSV na própria tela e substituir os dados de exemplo. Aceita CSV/XLSX com colunas `codigo_empresa;competencia;referencia;pessoas;bruto;descontos;encargos;liquido`. Para XLSX, competência deve ser texto ISO (AAAA-MM-01), não número serial de data do Excel.
3. Informar código da empresa na fonte, primeiro dia da competência, referência única e pelo menos um total. Valores financeiros são em reais; campos desconhecidos ficam vazios. Não enviar nomes, CPF ou informações individuais de trabalhadores.
4. Analisar arquivo e conferir a prévia paginada: empresa identificada, código/CNPJ, competência, referência, pessoas e totais originais. Avançar por todas as páginas antes de confirmar. Empresa não localizada exige corrigir código/fonte; campo vazio aparece como não informado. A prévia não grava dados e não substitui a validação integral. Se houver erro na confirmação, conferir a linha apontada no histórico; nenhuma fotografia daquele lote será gravada. Corrigir arquivo antes de reenviar.
5. Abrir a ficha da empresa → Conferências de folha. Comparar duas fotografias da mesma competência quando disponíveis. Uma referência repetida com valores diferentes é recusada; para retificar, enviar referência nova e preservar a anterior.

O fluxo grava documento informado, mesmo que o arquivo tenha sido exportado de um ERP. Não comprova consulta oficial, transmissão, aceite governamental ou fechamento. Homologar layouts reais, XLSX e concorrência PostgreSQL antes da liberação correspondente.

### Conferir a folha pela central (D-139)

Aplicar a migration 0060 no ambiente autorizado. Novas fotografias criam Conferir totais e documentos da folha, uma atividade por empresa/competência. Como administrador, atribuir a atividade a alguém com carteira vigente (D-132); sem atribuição, ela fica na carteira compartilhada. Não há prazo legal presumido.

Na atividade, abrir Conferir folha desta competência. A ficha mostra somente as fotografias daquele mês e mantém o filtro ao comparar/paginar. Comparar fontes e tratar diferenças/dados ausentes; usar Voltar à atividade da folha para registrar evidência humana e concluir. Ver todas as competências remove o recorte explicitamente. Igualdade de valores não conclui automaticamente nem comprova obrigações aceitas. Confirmar que revogar a empresa da carteira impede o acesso pelo link salvo.

Importar uma referência nova da mesma competência deve reabrir a atividade. Evidências anteriores permanecem, mas uma nova confirmação posterior ao recebimento é obrigatória. Reenviar a mesma referência/dados não reabre nem duplica. Para recompor fotografias anteriores: `uv run python manage.py sync_payroll_activities --organization UUID_DO_ESCRITORIO`. A recomposição usa somente dados locais, conserva o responsável e não faz consultas externas. Validar concorrência real antes de liberar o fluxo.

### Atividades da Caixa Postal DTE (D-142)

D-143: depois de uma abertura comprovada, registrar uma nova análise humana. Confirmação anterior não basta, mesmo se a central ainda não recebeu a atualização. Recompor um recibo novo reabre conclusão/dispensa antiga sem confirmação posterior; uma análise válida feita após o recibo é preservada. Conferir esse percurso no piloto, incluindo resultado incerto e recuperação, sem repetir a chamada externa.

Aplicar a migration 0061 no ambiente autorizado. A listagem persistida cria Analisar comunicação da Caixa Postal; atribuir pessoa pela central sem inventar prazo a partir da data de envio. Para recompor mensagens anteriores ou recuperar uma projeção que falhou: `uv run python manage.py sync_dte_activities --organization UUID_DO_ESCRITORIO`. Esse comando não chama o Serpro e não provoca ciência.

Na atividade, usar Consultar resumo da mensagem. O resumo local permite Voltar à atividade de análise; navegar não provoca consulta externa ou conclusão. Se o resumo estiver indisponível, conferir módulo Integra e carteira com o administrador. A abertura do teor continua sendo ação explícita com aprovação/custo existentes. Teor disponível gera evidência de consulta, mas a análise exige evidência humana e conclusão própria; providências decorrentes precisam ser registradas, não presumidas como cumpridas. Validar links e acesso revogado no navegador desktop/celular antes da liberação.

Resultado incerto bloqueia conclusão: esclarecer o recibo pelo procedimento existente, sem repetir automaticamente chamada que possa ter produzido ciência/cobrança. Falha de projeção da central não deve apagar o recibo persistido; executar recomposição depois de corrigir a causa. Repetir teste sem carteira vigente, mesmo com antiga permissão de ciência: deve ser recusado antes de reservar consumo. As transmissões ampliadas continuam autorizadas no plano, mas dependem de implementação/homologação própria; esta ponte não as implementa.

### Publicações do Radar por empresa (D-145)

Aplicar migration 0062 somente no ambiente autorizado. No Radar, usar Analisar por empresa, selecionar empresa da carteira e justificar a análise. Criar ou retomar análise abre a atividade atribuída ao solicitante; repetição não duplica nem troca responsável de atividade existente. Administrador pode redistribuir pela central. Não há prazo legal ou aplicabilidade calculados automaticamente.

Consultar a fonte oficial, documentar a análise e concluir a tarefa na central. Nova versão/reclassificação da publicação reabre conclusão ou dispensa; evidências antigas continuam guardadas, mas uma confirmação anterior não satisfaz a versão nova. Publicações sem vínculo humano não geram tarefas. Na página da publicação, conferir as análises da própria carteira e a paginação.

Recuperação local: `uv run python manage.py sync_reform_activities --organization UUID_DO_ESCRITORIO`. Não faz coleta externa nem cria vínculos para novas empresas. Validar operador com/sem Radar na empresa, auditor, empresa de outro escritório e concorrência na criação/recoleta. Piloto deve validar fonte e conteúdo real; títulos coletados não são parecer tributário. Navegador/volume/PostgreSQL continuam pendentes.

### Consulta DCTFWeb e revogação na fila (D-146)

Solicitações de declaração/recibo exigem usuário identificado e acesso operacional vigente à empresa e ao módulo Guias. Rotinas internas que chamem request_dctfweb_document devem informar actor; chamadas sem responsável são recusadas antes de reservar consumo. Nenhuma nova migration nesta correção.

Em homologação com provedor simulado, enfileirar a consulta e revogar usuário, vínculo, empresa, módulo ou concessão antes de executar o worker. Conferir status Não obtido, código authorization_revoked, nenhuma chamada externa e reserva liberada. Execução repetida da mesma falha não chama o provedor. Restaurar acesso exige nova solicitação explícita na tela; não ressuscita a fila automaticamente.

Não aplicar essa liberação a chamadas de resultado incerto: elas podem ter sido executadas e cobradas e mantêm o procedimento de conciliação anterior. Conferir também revogação concorrente em PostgreSQL antes da liberação real.

D-147 amplia essa verificação para emissão de guias e PARCSN: issue_fiscal_guide e request_parcelamento_operation também exigem actor. Módulo exigido é Guias para emissão e Integra para PARCSN. Em homologação simulada, revogar perfil/vínculo/módulo entre solicitação e worker, verificar ausência de chamada, falha authorization_revoked e reserva liberada. Restaurar acesso permite uma nova solicitação explícita, sem reativação automática.

D-148 corrige o tratamento legado: transporte incerto ou retorno sem PDF deixa a guia em Resultado a confirmar e mantém a reserva. Migration 0063 reclassifica falhas integration anteriores para esse estado, sem recriar reserva nem recalcular cobrança histórica. Aplicar somente no ambiente autorizado.

Correção do proprietário D-149: reemissão é permitida com custo adicional por guia. O bloqueio criado em D-148 é provisório e não representa o fluxo final aprovado. Aguarda definição do adicional perguntada ao proprietário e implementação do novo fluxo, preservando cada tentativa/consumo. Não usar este estágio como versão pronta para produção. Resultado a confirmar continua significando ausência de confirmação do resultado anterior, não gratuidade nem falha comprovada.

Para homologar, simular timeout após envio e resposta HTTP 200 sem PDF. Confirmar reserva mantida, retorno/protocolo preservados quando disponíveis, nenhuma segunda chamada e nenhuma liberação por repetição do worker. A recuperação estruturada por evidência do fornecedor/custo ainda está pendente; manter o caso bloqueado e reunir comprovantes, sem alterar status/consumo diretamente no banco. Não liberar o fluxo real antes dessa recuperação e dos testes de concorrência.

### Histórico das tentativas de guia (D-150)

Migration 0064 cria o histórico imutável; aplicar somente no ambiente autorizado, junto das migrations anteriores e após procedimento de backup/restauração. O código registra a solicitação e os estados observados, incluindo falha, resultado incerto e sucesso, com retorno criptografado. Antes de nova tentativa, conserva o resultado existente e limpa protocolo/retorno/data de emissão da tentativa nova. A referência de consumo identifica a tentativa; não é prova de valor faturado ou de gratuidade.

Registros anteriores não são reconstruídos artificialmente: quando preservados antes de nova tentativa, recebem snapshot_source=current_record; solicitações acompanhadas desde a fila recebem queued_request. Histórico ausente de chamadas antigas não pode ser tratado como prova de que não aconteceram.

No ambiente de homologação, usar provedor simulado: falha e nova solicitação já permitida devem preservar o primeiro resultado e separar os protocolos; repetição do worker não pode criar outro resultado nem outra chamada. Verificar recusa de edição/exclusão pelo ORM e vínculo cruzado entre escritórios. Validar concorrência PostgreSQL antes de liberar a reemissão. O adicional comercial e a substituição do bloqueio provisório continuam pendentes de D-149. Nenhuma chamada real foi autorizada por este roteiro.

D-151 disponibiliza o histórico dentro da ficha da guia, em páginas de 20 estados, com marcação de legado e demonstração. Conferir 21 registros fictícios, navegação entre páginas, retorno à carteira, nomes/protocolos longos, estado vazio, teclado e celular. Baixar PDF de tentativa anterior deve usar somente o retorno salvo, mesmo que a situação atual da guia seja diferente. Revogar a carteira e tentar repetir o download deve impedir acesso; trocar IDs de guia/evento/escritório também. O retorno bruto não aparece no HTML. Leitura do histórico não altera consumo; download registra auditoria. Playwright permaneceu sem transporte durante implementação; essa inspeção visual ainda precisa ser executada.

### Resultados Serpro na central (D-155)

Depois de aplicar a migration 0065 no ambiente autorizado, reconstruir apenas as projeções locais já existentes:

```powershell
uv run python manage.py sync_serpro_activities --organization UUID_DO_ESCRITORIO
```

O comando não chama o Serpro, não consome saldo e não emite nem reemite guia. Ele só cria ou atualiza a atividade vinculada ao registro local. Conferir uma guia emitida, um documento DCTFWeb disponível, uma consulta PARCSN disponível/vazia e um resultado incerto. A guia/DAS deve permanecer pendente com “Guia disponível”; documento DCTFWeb disponível conclui somente a obtenção; consulta PARCSN concluída encerra apenas a consulta. Falha ou incerteza deve ficar impedida com a mensagem correspondente.

Abrir cada atividade com um usuário que tem a empresa e o módulo, confirmar o link para a origem e revogar a carteira antes de tentar acessar a URL antiga. Uma atividade com responsável manual não pode ter seu responsável substituído pelo solicitante da operação; uma atividade sem responsável pode receber o solicitante inicial. Repetir o comando e conferir que não cria atividade, evidência ou evento duplicado. Não liberar conclusão de emissão de guia até a resposta de Q-40 e não configurar reemissão antes da definição comercial de D-149.

### Recuperar toda a central sem acionar fontes (D-156)

Quando houver falha local entre o resultado persistido de um módulo e a atividade correspondente, executar uma única recomposição por escritório:

```powershell
uv run python manage.py recover_operational_center --organization UUID_DO_ESCRITORIO
```

O comando percorre somente registros locais de NFS-e, Triagem, Conciliação, folha, DTE, Radar, guias, documentos DCTFWeb e PARCSN. Ele não consulta ERP ou Serpro, não emite/reemite/transmite, não provoca ciência e não reserva ou liquida consumo. A saída informa a quantidade por domínio; se alguma projeção falhar, o processo termina com erro após continuar as demais e identifica somente o domínio e a contagem. Investigar o registro pela rotina específica do módulo, corrigir a causa e repetir o comando. Não usar esse procedimento para alimentar estados Domínio sem contrato aprovado, para criar vínculos Radar ou para resolver reemissão/custo pendente.

### Permissões distintas entre empresas (D-152)

No ambiente de homologação, cadastrar um operador com Guias na empresa A e somente NFS-e na empresa B. A carteira de Guias deve conter apenas A; abrir diretamente a ficha, o PDF atual ou PDF histórico de B deve ser recusado. Repetir com auditor: consulta autorizada continua disponível, sem permitir execução. Repetir com Integra em A e outro módulo em B: contadores de empresas, mensagens e consultas pendentes não devem incluir B. Revogar a concessão e conferir novamente com a mesma sessão.

Essa correção não altera contratação nem concede novos módulos. Administradores continuam dentro da carteira autorizada; suporte continua limitado pela sessão própria. Executar cenários de suporte e concessões vindas do controlador no piloto. O teste local não comprova atualização real do controlador ou a visualização no navegador.

### Nova resolução de revisão NFS-e (D-153)

Quando uma revisão existente voltar legitimamente ao estado aberto, a nova resolução deve preservar a evidência e o acumulador da decisão anterior, registrar o novo instante/responsável/acumulador e concluir novamente somente o trabalho local. A correção não adiciona botão ou autorização de reabertura. Não alterar status diretamente no banco de produção para simular o fluxo.

Em teste controlado, duas resoluções com acumuladores diferentes devem produzir duas entradas no histórico de acumuladores e duas evidências na atividade. A recomposição `uv run python manage.py sync_nfse_activities --organization UUID_DO_ESCRITORIO` não chama serviços externos; repetição da mesma resolução não deve acrescentar prova duplicada. Registros legados são mantidos. Os arquivos exportados e a importação no Domínio continuam exigindo conferência independente.

### Reproduzir validação PostgreSQL local isolada

Existe configuração `config.settings.test_postgresql`: ela substitui somente os bancos de teste por PostgreSQL em loopback, preservando cache/e-mail locais e as demais proteções de `test`. Exige porta não padrão em `CICA_TEST_POSTGRES_PORT` e recusa `TEST_USE_EXTERNAL_SERVICES=true`. Não usa as URLs de banco do ambiente para executar testes. Credencial local fixa abaixo é exclusiva do contêiner descartável, sem dados reais.

Usar apenas Docker local e imagem já disponível. Confirmar antes que não existe contêiner chamado `cica-goal-pg-validation`; não remover uma instância desconhecida. Comandos PowerShell:

```powershell
docker run --pull=never --rm --detach --name cica-goal-pg-validation --label cica.task=goal-validation --publish 127.0.0.1::5432 --tmpfs /var/lib/postgresql/data:rw --env POSTGRES_USER=cica_test --env POSTGRES_PASSWORD=local-test-only --env POSTGRES_DB=cica_test postgres:17-bookworm
docker port cica-goal-pg-validation 5432/tcp
docker exec cica-goal-pg-validation pg_isready -U cica_test -d cica_test
```

Depois de obter a porta e confirmar que o banco aceita conexões, definir `$env:CICA_TEST_POSTGRES_PORT` com a porta retornada e executar:

```powershell
uv run pytest --ds=config.settings.test_postgresql --tb=short -q
```

Ao terminar, conferir identidade/rótulo e encerrar somente o contêiner criado para esta validação:

```powershell
docker inspect --format '{{.Config.Image}} {{.Config.Labels}}' cica-goal-pg-validation
docker stop cica-goal-pg-validation
```

`--rm` e tmpfs eliminam o contêiner e os dados descartáveis. Não apontar esse teste para o PostgreSQL existente do projeto nem para produção. Passar no teste concorrente local não substitui prova de queda real de worker, restauração ou desempenho com volume do escritório.


## Repetir inspe??o local da central (V-173)

Somente dados sint?ticos. Em um terminal PowerShell na raiz:

```powershell
$env:QA_REVIEW_SUITE = 'central'
uv run python scripts/qa_ui_server.py
```

Em outro terminal, defina PLAYWRIGHT_MODULE para a instala??o local existente do pacote Playwright e QA_BROWSER_EXECUTABLE para o execut?vel do navegador instalado. Execute `node scripts/qa_central_browser.cjs`. N?o use perfil pessoal. O script bloqueia destinos externos, fecha os contextos/navegador e grava resultados em `.playwright-mcp/central-review`. Ao terminar, encerre o servidor do primeiro terminal com Ctrl+C. N?o distribua `.tmp/central-review`: cont?m sess?es fict?cias reutiliz?veis. Os testes preservam o banco sint?tico entre execu??es.

52 combina??es passaram em V-173. Ainda ? necess?rio testar envios/altera??es, falhas e recupera??o, al?m do piloto real. Este procedimento n?o gera chamadas a fornecedores nem homologa integra??es. N?o instalar ou contratar servi?os por infer?ncia.

### Capacidades para observacoes operacionais (D-157)

Antes de ativar um adaptador que envie estados para a central, registre somente a capacidade que foi comprovada no contrato homologado: `activity_processing_status` para processamento e `activity_obligation_status` para obrigacao. A aplicacao recusa a alteracao sem essa declaracao ou quando a fonte estiver `disabled`; falha sem estado continua permitida para deixar indisponibilidade visivel. A declaracao nao basta por si: anexar objeto/consulta aprovado, chave empresa/competencia, valores de origem, exemplos mascarados e mapeamento para cada estado CICA. Nao usar `obligations`, `companies`, `accumulator_catalog` ou capacidade generica como substituto; elas nao autorizam mudar estados de fechamento.

### D-159 — Fonte desativada e retorno tardio

Ao desativar uma fonte, valide uma observacao tardia bem-sucedida e uma falha tardia: a primeira deve permanecer apenas no historico, sem reativar a fonte ou atualizar estados da atividade; a segunda pode registrar indisponibilidade, mas deve conservar `disabled`. A reativacao deve ser uma acao administrativa expressa e auditada. Este procedimento nao autoriza consulta Domínio/Siescon nem concede capacidade de estado a um adaptador.

### D-160 — Reativar fonte por ação administrativa

1. Entre como owner ou administrador, sem sessão de suporte, abra Configurações e selecione uma fonte `disabled`.
2. Verifique o aviso: reativar não consulta fonte nem torna os dados atuais.
3. Tente enviar sem marcar a confirmação: a fonte deve permanecer `disabled`.
4. Marque a confirmação e envie. A fonte deve passar a `not_configured`, preservar fotografia/capacidades e criar auditoria com ator e estados anterior/posterior.
5. Entre como auditor e confirme que não há controle nem POST autorizado.
6. Somente após contrato técnico e fonte autorizada, execute a nova sincronização separadamente; não atribua estado de fechamento/obrigação sem capacidade aprovada.

Validação local V-184: dois testes isolados de view passaram; Playwright local/Edge percorreu tela em desktop e 390 px, foco do checkbox, 66 telas/24 verificações sem overflow ou console error. Servidor QA e navegador foram encerrados. Nenhuma chamada externa, custo ou reativação de fonte real ocorreu.

### D-161 — Recorrência e carteira do responsável

1. Crie ou selecione um modelo e uma empresa do mesmo escritório.
2. Tente atribuí-lo a membro operacional sem concessão dessa empresa: o formulário deve recusar e não persistir a atribuição.
3. Revogue a carteira de um responsável já atribuído e gere a competência: a atividade deve ficar sem responsável, com evento explicando a indisponibilidade, sem alterar a atribuição anterior durante a geração manual.
4. Tente materializar uma atribuição com empresa de outro escritório somente no ambiente isolado: deve falhar antes de criar atividade.
5. Verifique no ambiente autorizado a renovação de carteira/control plane antes de testar uma geração real. Não transforme esse teste em sincronização de ERP.

Validação local V-185: central 36 aprovados/8 subtestes; recorrência 7 aprovados, 1 ignorado por locks PostgreSQL e 4 subtestes. Playwright local/Edge: 70 telas/28 verificações incluindo modelos em desktop/celular, sem overflow ou console error; QA encerrado.

### D-162 — Escrita recusada após mudança de vínculo

Se uma pessoa relatar que não conseguiu registrar evidência, impedimento, conclusão ou redistribuição após alteração de acesso, conferir o vínculo atual, o papel e a carteira da empresa. O CICA recusa a escrita quando o membro foi desativado, rebaixado para auditor/faturamento, perdeu a carteira ou não corresponde ao autor autenticado. Não recriar concessões nem alterar a atividade para contornar a recusa; corrigir a autorização pela fonte administrativa aprovada e pedir que a pessoa reabra a atividade. A validação local não comprova o controlador externo.

### D-165 — Sequência do agente Domínio Local: empresas e extratos

Antes do piloto, instalar o MSI que contém a V-189 ou uma versão posterior e confirmar a identidade do agente pareado. Em um DSN Domínio autorizado e com dados mascarados para conferência, solicite uma sincronização e acompanhe os eventos/auditoria da fonte. O esperado é: páginas de empresas até a página final ou vazia; em seguida, páginas de extratos bancários; nenhuma leitura de fechamento, obrigação, pagamento ou dados pessoais adicionais.

Interrompa o serviço depois de registrar ao menos uma página de empresas e antes do término dos extratos. Reinicie-o e confirme que empresas e extratos persistidos são atualizados pela chave externa, sem duplicar empresas, lançamentos, atividades ou evidências. Revogue o agente e confira que a próxima chamada autenticada é recusada. Colete somente contagens, timestamps, versões e códigos de resultado; não copie DSN, senha, extratos ou linhas da base para tickets ou documentação.

O teste prova a sequência e a recuperação do agente. Ele não homologa estados de fechamento/reabertura/obrigação, não autoriza capacidades `activity_processing_status` ou `activity_obligation_status`, nem substitui o contrato semântico de cada fonte.

### Pesquisa atualizada — estados Domínio e contrato Siescon (24/09/2026)

A documentação pública do Domínio confirma duas dimensões independentes que o adaptador não pode colapsar: o fechamento interno da competência impede alteração de cálculo e não equivale ao envio do S-1299; o eSocial usa S-1298 para reabertura e S-1299 para fechamento, ambos dependentes de validação no painel. Referências: [fechamento interno da folha](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=32), [reabertura S-1298](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=4577) e [manual de eventos periódicos](https://suporte.dominioatendimento.com/ctsfiles/ebook_esocial_fase_3.pdf?id=8969187). Isso reforça o modelo CICA com processamento e obrigação separados, mas não prova uma consulta programática autorizada nem os nomes/semânticas das colunas Domínio.

A página pública do Siescon confirma que seu gerenciador acompanha prazos, inconformidades, documentos e tarefas automáticas; as páginas públicas consultadas não disponibilizam contrato de API ou layout para leitura dessas situações. Referência: [Gerenciador de tarefas Siescon](https://www.siescon.com.br/portal/modulo?modulo=21-gerenciadordetarefas). Portanto, antes de criar adaptador, obter do fornecedor por escrito: versão e mecanismo autorizado; permissão de leitura; chave de escritório, empresa, estabelecimento e competência; lista exata de valores; paginação/limites; mecanismo de atualização; exemplos mascarados; e regra de revogação. Só depois registrar capacidades CICA e implementar o mapeamento, com testes de reabertura, retorno tardio e indisponibilidade.
