# Etapa 05 — Concluir IA por API e preparação da IA local

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Em andamento em 19/09/2026. O escopo local de fontes, exemplos e recuperação foi reforçado em V-032; nenhuma chamada Claude, curadoria externa, treinamento ou publicação real foi executada.

**Dependências:** 02–03; incorporar Siescon após 04.

**Decisões relacionadas:** D-16, D-20, D-47 a D-52, D-55.

## Escopo e checklist

- [-] Completar Copiloto e análise documental por API com limites, custos e falhas recuperáveis. O controle local existe, mas Q-08/Q-09/Q-11 impedem ativação e validação operacional.
- [-] Ampliar a consulta de conhecimento: fontes agora registram área, empresa e período, e a busca não cruza empresa; cobertura de conteúdo contábil, fiscal e folha ainda precisa de corpus revisado.
- [x] Estruturar dados e fontes por escritório, empresa, período e área. D-89 adicionou metadados opcionais com validação de escritório; registros existentes permanecem gerais.
- [x] Separar dados operacionais atualizados dos exemplos usados para ajuste do modelo. `KnowledgeSource` e `TrainingExample` são registros distintos e o manifesto exporta somente exemplos validados com fonte.
- [ ] Completar seleção de exemplos, revisão, anonimização, versionamento e exportação QLoRA.
- [x] Separar conjuntos de treino e avaliação para evitar avaliação contaminada. D-91 classifica cada exemplo em um único conjunto; o runner QLoRA recusa exemplos de avaliação.
- [x] Vincular avaliação ao artefato exato do modelo/adaptador, corpus e versão. D-90 exige a mesma proveniência ao publicar uma versão que declare adaptador; registros legados sem artefato permanecem apenas legados.
- [x] Preparar publicação, seleção do adaptador por escritório e retorno à versão anterior. D-90 vincula artefato/avaliação e D-92 retorna somente versão já aprovada do mesmo escritório; falta somente a prova com artefato real.
- [ ] Testar o contrato do runtime local e impedir fallback externo sem autorização.

## Bloqueios e responsabilidade

Q-08, Q-09, Q-11, Q-30 e Q-34. Percentuais existentes no código não são aprovação comercial.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Isolamento de dados/adaptadores, fontes insuficientes, injeção por documentos, limites, falha/retorno incerto, separação treino-avaliação, integridade do artefato e publicação/rollback.

**Critério de aceite:** Respostas com fontes verificáveis; isolamento entre escritórios; pipeline reproduzível; etapas que exigem a GPU definitiva explicitamente identificadas.

## Evidências e próximo passo

V-032 registra as migrações de metadados/proveniência, o isolamento por empresa na recuperação, manifestos QLoRA separados e retorno de versão auditado. A suíte focada aprovou 17 testes de publicação/retorno e 34 de escopo, divisão de conjuntos, exportação, avaliação e runner; nenhuma homologação nova foi atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. O próximo trabalho local depende de corpus e exemplos revisados, sem inventar um modelo; Q-08, Q-09, Q-11 e Q-34 continuam necessários para ativação/curadoria. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 05. Complete a IA por API e o pipeline local para contábil, fiscal e folha, mantendo dados e ajustes isolados por escritório. Reaproveite o runner QLoRA e os controles existentes, corrigindo lacunas entre corpus, avaliação, artefato e inferência. Não declare treinamento real ou desempenho local sem execução comprovada.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
