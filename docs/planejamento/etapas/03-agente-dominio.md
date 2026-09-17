# Etapa 03 — Concluir agente Windows e integração Domínio

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Não iniciada nesta execução.

**Dependências:** 01–02.

**Decisões relacionadas:** D-06, D-18, D-46, D-52.

## Escopo e checklist

- [ ] Resolver a divisão atual: o agente Python sincroniza Domínio local; o nativo processa backups e arquivamento.
- [ ] Entregar um fluxo de instalação que identifique claramente os componentes necessários.
- [ ] Homologar DSNs e drivers nas arquiteturas suportadas.
- [ ] Completar pareamento, atualização, revogação, reinício, diagnóstico e recuperação de rede.
- [ ] Validar Domínio local e importação manual de backup Domínio Web.
- [ ] Substituir limites que truncam dados por leitura paginada/incremental verificável.
- [ ] Mapear os dados necessários de contabilidade, fiscal e folha, com leitura autorizada e rastreabilidade.
- [ ] Homologar escrita documental nas pastas Windows permitidas.

## Bloqueios e responsabilidade

Q-22, Q-28, Q-31 e Q-32. Registrar a arquitetura definitiva antes de unificar Python e serviço nativo.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Instalação, x86/x64 conforme suporte decidido, revogação, fila offline, repetição, volume acima dos limites atuais, atualização e escape/reparse points/UNC nas pastas autorizadas.

**Critério de aceite:** Instalar em máquina limpa, sincronizar, interromper a rede, reiniciar e retomar sem perder ou duplicar dados.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 03. Complete o serviço instalável e o conector Domínio local/Web. Apresente a decisão técnica pendente sobre Python e serviço nativo com evidências antes de alterar essa arquitetura. Homologue instalação, leitura, recuperação, atualização e pastas Windows, sem SQL arbitrário nem escrita no banco Domínio.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
