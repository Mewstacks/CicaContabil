# Etapa 11 — Validar todas as jornadas e interfaces

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Não iniciada nesta execução.

**Dependências:** Módulos implementados.

**Decisões relacionadas:** D-07, D-38, D-57.

## Escopo e checklist

- [ ] Revisar site comercial, cadastro, aplicação do escritório, central de aprendizado e console Mewstack.
- [ ] Corrigir ações sem saída, tabelas incompletas, estados confusos e ausência de evidência.
- [ ] Validar desktop, celular, teclado, foco, erros, carregamento e estados vazios.
- [ ] Aplicar ui-ux-pro-max, Watermelon, referências reais de produto e web-design-guidelines.
- [ ] Inspecionar as jornadas com Playwright MCP; registrar exatamente os estados alcançados e fechar as sessões.
- [ ] Conferir que oferta comercial e demonstração refletem capacidades homologadas.

## Bloqueios e responsabilidade

Q-30; estados inacessíveis devem ser registrados, nunca presumidos validados.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Por perfil e módulo: desktop/celular, navegação, foco, teclado, carregamento/erro/vazio, recuperação, console do navegador e evidência visual.

**Critério de aceite:** O usuário conclui tarefas representativas sem intervenção interna não prevista.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 11 em todas as áreas da CICA, preservando o design existente. Siga integralmente o fluxo de UI do AGENTS.md, registre referências e valide tarefas completas com Playwright em desktop e celular. Corrija bloqueios funcionais e de acessibilidade e feche as sessões abertas.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
