# Etapa 12 — Homologação integrada e liberação comercial

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Não iniciada nesta execução.

**Dependências:** 01–11.

**Decisões relacionadas:** D-03, D-46, D-51, D-56, D-77, D-81, D-86, D-87.

## Escopo e checklist

- [ ] Configurar Brevo SMTP, remetente e autenticação de domínio/DNS da CICA; testar confirmação, convite e recuperação, incluindo falha de entrega (D-77/D-78).

- [ ] Identificar ambiente de produção e capacidade necessária, sem presumir provedor ou contratar recursos.
- [ ] Reunir toda dependência de site em produção preparada nas etapas 01–11: domínio/HTTPS/DNS, credenciais e consentimentos externos, serviços hospedados, chamadas reais a provedores, pilotos e homologação comercial (D-87).
- [ ] Validar deploy, migrações, workers, agendador, storage e conectividade dos agentes.
- [ ] Executar o piloto operacional do agente CICA: instalação limpa x64, DSN/driver, pareamento HTTPS/mTLS, revogação, atualização distribuída, queda/retomada de rede, backup `.dom` autorizado e escrita documental na raiz Windows real. Definir Q-22/Q-31 no contexto do piloto (D-86).
- [ ] Executar restauração de banco e documentos, recuperação de falhas e retorno de versão.
- [ ] Homologar retenção, exportação, exclusão, termos e contatos de suporte.
- [ ] Executar piloto por módulo, com critérios e amostra aprovados.
- [ ] Entregar manuais de instalação, operação e suporte, matriz de compatibilidade e limitações.
- [ ] Produzir relatório final de liberação por módulo.

## Bloqueios e responsabilidade

Q-24, Q-28 a Q-30 e Q-35. Recursos pagos exigem aprovação específica.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Instalação integrada, carga aprovada, queda de serviços, restauração verificável, rollback compatível com migrations, retenção e piloto por módulo.

**Critério de aceite:** Todos os módulos da oferta possuem evidência de funcionamento e operação sustentável; nenhuma pendência crítica é escondida como concluída.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 12. Faça a homologação integrada da CICA e reúna evidências por módulo, incluindo restauração, filas, integrações, instalação e suporte. Confirme com o responsável ambiente, metas e critérios ainda pendentes. Não libere venda nem contrate infraestrutura por inferência.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
