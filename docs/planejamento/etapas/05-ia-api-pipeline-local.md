# Etapa 05 — Concluir IA por API e preparação da IA local

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Em andamento em 21/09/2026. O escopo local de fontes, exemplos e recuperação foi reforçado em V-032 e V-042; o manifesto agora recusa identificadores pessoais antes de criar artefato e não sobrescreve um artefato existente, sem mascarar registros automaticamente. V-043/V-044/V-057/V-059/V-065 também reduziram a dívida de tipos da base local, incluindo gateway, relatórios, sincronização, serviços, agente e interface, sem alterar comportamento de IA. V-071 verificou visualmente o Copiloto fictício; V-072 provou em teste que uma resposta do runtime local não chama o fallback externo e que a política sem opt-in o bloqueia. V-086 tornou recuperável por página todo o histórico aberto já autorizado do Copiloto e V-088 fez o mesmo para a atenção de egressão no detalhe administrativo, sem enviar pergunta, chamar runtime ou criar egressão. Nenhuma chamada Claude, curadoria externa, treinamento ou publicação real foi executada.

**Dependências:** 02–03; incorporar Siescon após 04.

**Decisões relacionadas:** D-16, D-20, D-47 a D-52, D-55.

## Escopo e checklist

- [-] Completar Copiloto e análise documental por API com limites, custos e falhas recuperáveis. O controle local existe, mas Q-08/Q-09/Q-11 impedem ativação e validação operacional.
- [-] Ampliar a consulta de conhecimento: fontes agora registram área, empresa e período, e a busca não cruza empresa; cobertura de conteúdo contábil, fiscal e folha ainda precisa de corpus revisado.
- [x] Estruturar dados e fontes por escritório, empresa, período e área. D-89 adicionou metadados opcionais com validação de escritório; registros existentes permanecem gerais.
- [x] Separar dados operacionais atualizados dos exemplos usados para ajuste do modelo. `KnowledgeSource` e `TrainingExample` são registros distintos e o manifesto exporta somente exemplos validados com fonte.
- [-] Completar seleção de exemplos, revisão, anonimização, versionamento e exportação QLoRA. V-042 antecipa o gate local de CPF/CNPJ/e-mail e a escrita exclusiva do manifesto, mas a seleção, a anonimização humana rastreável e o corpus revisado continuam pendentes.
- [x] Separar conjuntos de treino e avaliação para evitar avaliação contaminada. D-91 classifica cada exemplo em um único conjunto; o runner QLoRA recusa exemplos de avaliação.
- [x] Vincular avaliação ao artefato exato do modelo/adaptador, corpus e versão. D-90 exige a mesma proveniência ao publicar uma versão que declare adaptador; registros legados sem artefato permanecem apenas legados.
- [x] Preparar publicação, seleção do adaptador por escritório e retorno à versão anterior. D-90 vincula artefato/avaliação e D-92 retorna somente versão já aprovada do mesmo escritório; falta somente a prova com artefato real.
- [x] Testar o contrato do runtime local e impedir fallback externo sem autorização. V-072 exercita o contrato OpenAI-compatível local com evidência compacta; mesmo com fallback configurado e aprovado, uma resposta local não gera chamada nem auditoria de egressão. A ausência de opt-in do escritório continua bloqueando o fallback e registra a negação.

## Bloqueios e responsabilidade

Q-08, Q-09, Q-11, Q-30 e Q-34. Percentuais existentes no código não são aprovação comercial.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Isolamento de dados/adaptadores, fontes insuficientes, injeção por documentos, limites, falha/retorno incerto, separação treino-avaliação, integridade do artefato e publicação/rollback.

**Critério de aceite:** Respostas com fontes verificáveis; isolamento entre escritórios; pipeline reproduzível; etapas que exigem a GPU definitiva explicitamente identificadas.

## Evidências e próximo passo

V-032 registra as migrações de metadados/proveniência, o isolamento por empresa na recuperação, manifestos QLoRA separados e retorno de versão auditado. V-042 antecipa a recusa de CPF/CNPJ/e-mail em pergunta, resposta ou referência antes de criar manifestos de treino ou avaliação; a exportação de linha de comando também falha sem escrever artefato e recusa sobrescrever um existente. V-068 aprovou a suíte integral com 762 testes, 3 skips e 11 subtestes e zerou a dívida MyPy nos 190 arquivos verificados. V-072 executou 73 testes e 3 subtestes de IA/configuração: validou o contrato HTTP OpenAI-compatível privado, evidência compacta, prioridade efetiva do runtime local e negação auditada do fallback sem opt-in. V-086 executou 49 testes e 3 subtestes de IA, criando 13 conversas sintéticas para confirmar a segunda página, a conversa ativa e a preservação de vínculos; a demonstração vazia confirmou apenas a superfície móvel em 390 px, sem atribuir volume visual. V-088 executou 57 testes e criou 21 auditorias incertas sintéticas para confirmar a segunda página, o isolamento do escritório e a preservação do protocolo, sem chamar IA ou alterar consumo. Nenhuma homologação nova foi atribuída a esta etapa. A existência de código ou testes anteriores não prova curadoria, modelo ou ativação reais. O próximo trabalho local depende de corpus e exemplos revisados, sem inventar um modelo; Q-08, Q-09, Q-11 e Q-34 continuam necessários para ativação/curadoria. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 05. Complete a IA por API e o pipeline local para contábil, fiscal e folha, mantendo dados e ajustes isolados por escritório. Reaproveite o runner QLoRA e os controles existentes, corrigindo lacunas entre corpus, avaliação, artefato e inferência. Não declare treinamento real ou desempenho local sem execução comprovada.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
