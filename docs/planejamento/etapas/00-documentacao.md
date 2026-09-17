# Etapa 00 — Consolidar decisões, inventário e pendências

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Documentação materializada; conferir aceite em VALIDACOES.md.

**Dependências:** Nenhuma.

**Decisões relacionadas:** D-46 a D-60.

## Escopo e checklist

- [ ] Gravar integralmente o plano e as decisões confirmadas.
- [ ] Inventariar módulos, rotas, tarefas, APIs, serviços Windows e integrações.
- [ ] Confrontar documentação antiga com o código e decisões posteriores.
- [ ] Registrar cada pendência uma única vez, com etapa afetada e responsável pela resposta.
- [ ] Preservar o trabalho local existente; não descartar nem sobrescrever alterações.
- [ ] Agrupar as perguntas restantes por condições comerciais, regras documentais, dados autorizados para IA, ambientes de homologação e metas operacionais; perguntar somente o ainda não decidido.

## Bloqueios e responsabilidade

Nenhum bloqueio para documentar; as decisões abertas não impedem esta etapa.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Conferir links locais, IDs de decisões, cobertura de 00 a 13, inventário estático e ausência de alterações de código nesta etapa.

**Critério de aceite:** Outra pessoa consegue identificar o próximo trabalho, suas decisões e seus bloqueios sem reconstruir conversas antigas.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 00 do plano mestre da CICA. Materialize os documentos e prompts deste plano, consolide as decisões já confirmadas e elimine contradições documentais sem apagar o histórico. Confira o código atual. Não pergunte novamente decisões registradas; apresente somente lacunas ou conflitos concretos.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
