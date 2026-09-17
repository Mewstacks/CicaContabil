# Etapa 06 — Concluir Triagem de Arquivos

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Não iniciada nesta execução.

**Dependências:** 03 e 05.

**Decisões relacionadas:** D-21 a D-29, D-43, D-55.

## Escopo e checklist

- [ ] Homologar Microsoft 365, Google Workspace, Gmail pessoal e IMAP conforme decisões registradas.
- [ ] Completar leitura incremental, quarentena, antimalware, extração e classificação.
- [ ] Permitir visualizar documentos liberados, corrigir empresa, tipo, competência e destino.
- [ ] Aplicar automação somente às regras aprovadas e medidas.
- [ ] Completar biblioteca interna e arquivamento Windows com confirmação de integridade.
- [ ] Atualizar checklist somente após arquivamento confirmado.
- [ ] Resolver duplicatas, colisões, múltiplos documentos e indisponibilidade do agente.

## Bloqueios e responsabilidade

Q-12 a Q-25 e Q-31: catálogo, nomenclatura, retenção, formatos, limites e checklist ainda precisam de decisões específicas.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Consentimento/revogação nos três provedores, cursor, ameaça/falha do scanner, campos incorretos, documento ambíguo, duplicatas, agente offline e prova de hash no destino.

**Critério de aceite:** E-mail → anexo seguro → classificação/revisão → arquivo localizado no destino → checklist atualizado, com recuperação de falhas.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 06. Complete a Triagem exclusivamente pelas entradas de e-mail aprovadas e pelos dois destinos definidos. Consulte o registro antes de perguntar taxonomia ou nomenclatura. Homologue todo o caminho até o arquivo final, incluindo correção humana, duplicatas, quarentena e agente indisponível.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
