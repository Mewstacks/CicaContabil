# Jornadas: utilidade e decisão comercial pendente

Avaliação solicitada pelo responsável em 15/09/2026. Ele sinalizou que Jornadas é simples e comum em outros softwares, pediu para tirá-lo da oferta paga e perguntou se vale como benefício ou se deve sair. **A permanência da função, telas e dados ainda não foi decidida.**

## O que a CICA faz hoje

`ClientJourney` é um quadro interno de trabalho vinculado a empresa, responsável, título, prazo e estado. `JourneyStep` guarda etapas ordenadas com conclusão; `PortalRequest` guarda pendências com estados aberta/recebida/concluída. As views permitem criar e concluir esses registros, com escopo por escritório/empresa, permissão e auditoria. A UI em `/app/jornada/` mostra o quadro e formulários internos. O portal externo para cliente não existe nesta etapa; campos `portal_visible` ficaram por compatibilidade histórica. A lista carrega apenas as primeiras 12 jornadas. Fontes: `src/apps/hub/models.py`, `views.py`, `templates/hub/journey.html` e `tests/test_hub_workspace_views_django.py`.

Exemplo de uso real possível hoje: uma equipe abre “Fechamento de junho — Empresa A”, atribui responsável, cria “conferir extratos” e “emitir guia”, registra “falta comprovante” e marca as etapas manualmente. O quadro centraliza quem deve fazer o quê, mas não recebe comprovante, não compara checklist da Triagem, não emite guia nem solicita automaticamente o documento ao cliente.

## Comparação de mercado

- [TaxDome, visão de pipelines](https://sv.help.taxdome.com/article/1826-pipelines-overview): trabalho por etapa com modelos reutilizáveis e automações que criam tarefas, enviam e-mails e pedidos ao cliente.
- [TaxDome, pedidos ao cliente](https://help.taxdome.com/article/1597-client-requests-overview): pedidos podem ser disparados no estágio do processo e avançam quando o cliente responde.
- [Karbon, automação de workflow](https://karbonhq.com/solution/workflow-automation): modelos, tarefas recorrentes, regras condicionais, lembretes e cobrança automática de documentos.

Esses são exemplos oficiais das próprias plataformas, consultados para aferir **padrão de capacidade**, não qualidade de implantação ou resultado financeiro. A inferência é que a CICA atual oferece o componente básico de lista/etapas, enquanto produtos especializados já ligam esse componente a comunicação, documentos e trabalho recorrente. A existência de um quadro interno é útil em alguns escritórios, mas não sustenta por si só a promessa de diferencial disruptivo ou preço separado de R$ 159/mês presente em `src/apps/platform/pricing.py`.

## Recomendação para decisão

Retirar “Jornadas” como módulo e preço independentes. Se a CICA precisar preservar o conceito de pendência, incorporá-lo às operações concretas: documento faltante da Triagem, retorno DTE pendente, divergência de Conciliação, guia aguardando aprovação. Isso usa contexto e estado que a CICA já tem ou precisa construir e evita pedir que o usuário duplique trabalho num quadro manual. **É recomendação, não decisão aprovada de remoção de código.**

Há duas escolhas de produto que o responsável ainda pode fazer: manter o quadro atual como benefício incluído, com escopo claro e sem promessa de automação; ou retirar tela/módulo autônomo, preservando e migrando registros existentes conforme uma política aprovada. Em ambos os casos, contratos históricos, preço e mensagens públicas precisam de ajuste deliberado. Não apagar dados ou rota antes dessa decisão e de plano de migração.
