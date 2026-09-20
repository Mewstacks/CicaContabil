# Etapa 07 — Concluir NFS-e, certificados e revisão fiscal

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** A demonstração local de carteira, filtro e download em lote foi implementada e revalidada em V-005/V-035. A etapa permanece em andamento para coleta e homologação reais.

**Dependências:** 03 e 05.

**Decisões relacionadas:** D-31, D-55.

## Escopo e checklist

- [x] Entregar demonstração de download em lote com ZIP fictício por empresa, `Tomadas/CÓDIGO -/` e `Emitidas/CÓDIGO -/` (D-62).
- [x] Permitir baixar toda a carteira e validar acumulador/confiança antes do ZIP: classificação acima de 95%; transitória em 0% (D-63).
- [x] Filtrar carteira por competência de emissão ou intervalo de emissão, mostrando emissão como referência da nota (D-64).
- [x] Permitir download demonstrativo sem bloqueio: transitória a 0%, decisão manual identificada e IA acima de 95% (D-65).
- [x] Oferecer uma escolha exclusiva entre filtro por competência e filtro por emissão na demonstração (D-66).
- [x] Atualizar visualmente a linha da demonstração ao definir acumulador, sem persistir decisão fictícia (D-68).
  - Implementação e inspeções locais registradas em V-005 e V-035. A etapa completa permanece aberta.
- [ ] Homologar coleta ADN, certificados, NSU, retomada e deduplicação.
- [ ] Apresentar nota legível, valores, participantes, competência e descrição dos serviços.
- [ ] Validar acumuladores contra o catálogo da empresa.
- [ ] Exibir evidência da sugestão e permitir correção.
- [ ] Garantir acesso a toda a carteira, sem cortes silenciosos nas filas.
- [ ] Documentar cobertura e limitações efetivas da fonte de coleta.

## Bloqueios e responsabilidade

Q-28 e Q-30: certificado/ambiente autorizado, corpus e métricas de aceite.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Certificado errado/expirado, retomada NSU, repetição, lote inválido, cobertura da carteira, acumulador inexistente e revisão fundamentada.

**Critério de aceite:** Nota real autorizada é coletada, conferida, classificada e rastreada sem duplicação ou associação à empresa errada.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 07. Complete e homologue NFS-e e revisão fiscal, da validade do certificado à decisão do contador. Valide o catálogo de acumuladores e a continuidade da coleta. Não confunda dados calculados, documento fiscal oficial e sugestão da IA.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
