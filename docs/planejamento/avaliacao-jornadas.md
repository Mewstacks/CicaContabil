# Jornadas: avaliação histórica, substituída pela Triagem

Avaliação solicitada pelo responsável em 15/09/2026. A decisão posterior [D-43](decisoes.md) substituiu Jornadas pela Triagem de Arquivos em oferta, navegação e rotas do escritório. O responsável confirmou que **não há contratos comerciais antigos**; o banco local tinha zero jornadas. O schema e o código legado permanecem temporariamente para evitar remoção de tabelas sem revisão de migração, sem rota de produto acessível.

## O que o protótipo fazia antes da substituição

`ClientJourney` é um quadro interno de trabalho vinculado a empresa, responsável, título, prazo e estado. `JourneyStep` guarda etapas ordenadas com conclusão; `PortalRequest` guarda pendências com estados aberta/recebida/concluída. As views permitem criar e concluir esses registros, com escopo por escritório/empresa, permissão e auditoria. A UI em `/app/jornada/` mostra o quadro e formulários internos. O portal externo para cliente não existe nesta etapa; campos `portal_visible` ficaram por compatibilidade histórica. A lista carrega apenas as primeiras 12 jornadas. Fontes: `src/apps/hub/models.py`, `views.py`, `templates/hub/journey.html` e `tests/test_hub_workspace_views_django.py`.

Exemplo de uso real possível hoje: uma equipe abre “Fechamento de junho — Empresa A”, atribui responsável, cria “conferir extratos” e “emitir guia”, registra “falta comprovante” e marca as etapas manualmente. O quadro centraliza quem deve fazer o quê, mas não recebe comprovante, não compara checklist da Triagem, não emite guia nem solicita automaticamente o documento ao cliente.

## Comparação de mercado

- [TaxDome, visão de pipelines](https://sv.help.taxdome.com/article/1826-pipelines-overview): trabalho por etapa com modelos reutilizáveis e automações que criam tarefas, enviam e-mails e pedidos ao cliente.
- [TaxDome, pedidos ao cliente](https://help.taxdome.com/article/1597-client-requests-overview): pedidos podem ser disparados no estágio do processo e avançam quando o cliente responde.
- [Karbon, automação de workflow](https://karbonhq.com/solution/workflow-automation): modelos, tarefas recorrentes, regras condicionais, lembretes e cobrança automática de documentos.

Esses são exemplos oficiais das próprias plataformas, consultados para aferir **padrão de capacidade**, não qualidade de implantação ou resultado financeiro. A inferência histórica era que a CICA oferecia o componente básico de lista/etapas, enquanto produtos especializados já ligavam esse componente a comunicação, documentos e trabalho recorrente. O preço separado de R$ 159/mês constava no simulador legado, removido depois da decisão de substituir Jornadas pela Triagem.

## Recomendação histórica

Retirar “Jornadas” como módulo e preço independentes. Se a CICA precisar preservar o conceito de pendência, incorporá-lo às operações concretas: documento faltante da Triagem, retorno DTE pendente, divergência de Conciliação, guia aguardando aprovação. Isso usa contexto e estado que a CICA já tem ou precisa construir e evita pedir que o usuário duplique trabalho num quadro manual. **É recomendação, não decisão aprovada de remoção de código.**

Essa bifurcação foi encerrada pela decisão D-43. A Triagem ocupa a posição de módulo no produto; preço e franquia aguardam pesquisa/aprovação. O schema legado pode ser removido em uma migração posterior quando nenhuma dependência de código/teste o usar.
