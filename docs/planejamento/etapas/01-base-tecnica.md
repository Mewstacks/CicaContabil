# Etapa 01 — Estabilizar a base técnica

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Não iniciada nesta execução.

**Dependências:** 00.

**Decisões relacionadas:** D-03, D-56, D-57.

## Escopo e checklist

- [ ] Resolver as 66 violações atuais do Ruff e demais falhas verificadas.
- [ ] Consolidar migrações e revisar compatibilidade com dados existentes.
- [ ] Executar testes com PostgreSQL, Redis e workers reais em ambiente isolado.
- [ ] Verificar concorrência em consumo, faturamento, filas e publicação de modelos.
- [ ] Validar builds da aplicação, runtime multimodal, treinamento e agente.
- [ ] Revisar dependências, configuração de produção e tratamento de segredos.

## Bloqueios e responsabilidade

Q-28 e Q-30 para ambientes e aceite; disponibilidades técnicas devem ser inspecionadas, sem instalar ou contratar infraestrutura por inferência.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Ruff, Django check, migrations dry-run, suíte, concorrência PostgreSQL, workers/Redis e builds; registrar separadamente qualquer ambiente indisponível.

**Critério de aceite:** CI aprovado e instalação reproduzível; testes com SQLite não substituem testes concorrentes em PostgreSQL.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 01. Estabilize o estado atual preservando alterações existentes, faça o CI passar e valide banco, filas, migrações e builds em ambiente isolado. Registre resultados e limitações reais; não considere testes simulados prova de produção.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
