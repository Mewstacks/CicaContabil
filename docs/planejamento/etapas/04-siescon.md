# Etapa 04 — Implementar e homologar Siescon

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Não iniciada nesta execução.

**Dependências:** 02–03.

**Decisões relacionadas:** D-53, D-54.

## Escopo e checklist

- [ ] Identificar versão, banco, mecanismo permitido de acesso e ambiente disponibilizado.
- [ ] Obter schema e arquivos de referência por acesso autorizado.
- [ ] Implementar leitura, sincronização e diagnóstico.
- [ ] Mapear empresas, contas, lançamentos e demais dados necessários aos fluxos contratados.
- [ ] Preparar exportação revisada no layout efetivamente suportado.
- [ ] Generalizar vínculos hoje dependentes exclusivamente do código Domínio.
- [ ] Registrar matriz de capacidades: o que funciona com Domínio, Siescon ou ambos.

## Bloqueios e responsabilidade

Q-28 e Q-33. Banco disponível foi confirmado; versão, meio de acesso e layout não foram fornecidos.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Leitura autorizada, escopo por empresa, cursor/repetição, revogação, exportação revisada e importação conferida no Siescon; sem gravação direta.

**Critério de aceite:** Dados sincronizados conferem com o Siescon; arquivo exportado é importado e conferido no ambiente de homologação. Gerar arquivo não basta.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 04 usando o servidor/banco Siescon disponibilizado pelo responsável. Descubra e documente o contrato técnico antes de programar o adaptador. Entregue leitura e exportação revisada, valide identificação das empresas e homologue a importação. Não invente endpoints, layouts ou permissões.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
