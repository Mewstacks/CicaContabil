# Etapa 04 — Implementar e homologar Siescon

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Em andamento em 21/09/2026. V-041 revalidou a preparação local: a fonte e o destino Siescon são modelados, mas não existe adaptador registrado e a exportação falha de modo explícito antes de ler lançamentos ou gerar arquivo. A inspeção local anterior não encontrou instalação, DSN ou driver identificado como Siescon; portanto o servidor/banco disponibilizado em D-53 ainda não está acessível nesta estação. A implementação do adaptador permanece condicionada ao contrato técnico de Q-33.

**Dependências:** 02–03.

**Decisões relacionadas:** D-53, D-54.

## Escopo e checklist

- [ ] Identificar versão, banco, mecanismo permitido de acesso e ambiente disponibilizado.
- [ ] Obter schema e arquivos de referência por acesso autorizado.
- [-] Preparar leitura, sincronização e diagnóstico. O espelho idempotente existente pode receber um adaptador revisado, mas não há contrato Siescon para implementar leitura específica (Q-33).
- [ ] Mapear empresas, contas, lançamentos e demais dados necessários aos fluxos contratados.
- [-] Preparar exportação revisada no layout efetivamente suportado. D-88 separou destino e adaptador; Siescon é recusado até existir layout revisado, sem gerar arquivo fictício.
- [x] Generalizar vínculos hoje dependentes exclusivamente do código Domínio. `AccountingExport` passou a registrar destino/versionamento e a fonte Siescon existe no modelo; a compatibilidade permanece bloqueada até a revisão do adaptador.
- [x] Registrar [matriz de capacidades](../../siescon-matriz-capacidades.md): o que funciona com Domínio, Siescon ou ambos.

## Bloqueios e responsabilidade

Q-28 e Q-33. Banco disponível foi confirmado; versão, meio de acesso e layout não foram fornecidos. A inspeção de 18/09 verificou somente metadados locais e não encontrou instalação, DSN ou driver Siescon nesta estação; não houve tentativa de conexão nem leitura de dados.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Leitura autorizada, escopo por empresa, cursor/repetição, revogação, exportação revisada e importação conferida no Siescon; sem gravação direta.

**Critério de aceite:** Dados sincronizados conferem com o Siescon; arquivo exportado é importado e conferido no ambiente de homologação. Gerar arquivo não basta.

## Evidências e próximo passo

V-029 registra que esta estação possui 26 drivers ODBC e 5 DSNs, mas nenhum identificado como Siescon e nenhuma instalação Siescon nas pastas locais usuais. V-030 registra a base de destino/adaptador versionado. V-041 revalidou em macOS local o código que recusa Siescon sem adaptador, 35 testes focados (um skip de OCR), a suíte integral, lint, Django e migrações; não alterou o bloqueio e não realizou conexão, leitura ou exportação Siescon. A [análise consolidada de 21/09](../analise-projeto-2026-09-21.md) lista o material mínimo de Q-33 por canal seguro. Nenhuma homologação nova foi atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 04 usando o servidor/banco Siescon disponibilizado pelo responsável. Descubra e documente o contrato técnico antes de programar o adaptador. Entregue leitura e exportação revisada, valide identificação das empresas e homologue a importação. Não invente endpoints, layouts ou permissões.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
