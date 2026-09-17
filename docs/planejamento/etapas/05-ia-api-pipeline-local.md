# Etapa 05 — Concluir IA por API e preparação da IA local

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Não iniciada nesta execução.

**Dependências:** 02–03; incorporar Siescon após 04.

**Decisões relacionadas:** D-16, D-20, D-47 a D-52, D-55.

## Escopo e checklist

- [ ] Completar Copiloto e análise documental por API com limites, custos e falhas recuperáveis.
- [ ] Ampliar a consulta de conhecimento: a busca atual por palavras não comprova cobertura das três áreas solicitadas.
- [ ] Estruturar dados e fontes por escritório, empresa, período e área.
- [ ] Separar dados operacionais atualizados dos exemplos usados para ajuste do modelo.
- [ ] Completar seleção de exemplos, revisão, anonimização, versionamento e exportação QLoRA.
- [ ] Separar conjuntos de treino e avaliação para evitar avaliação contaminada.
- [ ] Vincular avaliação ao artefato exato do modelo/adaptador, corpus e versão.
- [ ] Preparar publicação, seleção do adaptador por escritório e retorno à versão anterior.
- [ ] Testar o contrato do runtime local e impedir fallback externo sem autorização.

## Bloqueios e responsabilidade

Q-08, Q-09, Q-11, Q-30 e Q-34. Percentuais existentes no código não são aprovação comercial.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Isolamento de dados/adaptadores, fontes insuficientes, injeção por documentos, limites, falha/retorno incerto, separação treino-avaliação, integridade do artefato e publicação/rollback.

**Critério de aceite:** Respostas com fontes verificáveis; isolamento entre escritórios; pipeline reproduzível; etapas que exigem a GPU definitiva explicitamente identificadas.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 05. Complete a IA por API e o pipeline local para contábil, fiscal e folha, mantendo dados e ajustes isolados por escritório. Reaproveite o runner QLoRA e os controles existentes, corrigindo lacunas entre corpus, avaliação, artefato e inferência. Não declare treinamento real ou desempenho local sem execução comprovada.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
