# Revisão de navegação e cores — 16/09/2026

## Diagnóstico

A captura original aplica verde ao fundo, navegação, superfícies, ações e estados. Isso reduz a distinção entre estrutura, identidade e informação operacional. Não existe proibição normativa de interfaces verdes nem uma porcentagem universal de cor de marca. A crítica é à ausência de hierarquia e de papéis consistentes para a cor.

“Operação” e “Sistemas” misturavam tarefas, produtos comerciais e integrações. “Revisões” não explicitava sua relação com NFS-e. Ter notas e decisões em vistas diferentes é útil; apresentá-las como produtos independentes torna o caminho difícil de reconhecer.

## Evidência e referências

- [Microsoft Fluent — Color](https://fluent2.microsoft.design/color): base neutra para texto, superfícies e layout; evitar excesso de marca, especialmente em grandes superfícies. Adotado: fundos neutros e cores com função.
- [IBM Carbon — Color](https://carbondesignsystem.com/elements/color/overview/): predominância de cinzas, cores adicionais usadas com propósito, camadas distintas nos temas claro e escuro. Adotado: tokens semânticos de superfície, texto, interação e estado.
- [WCAG — contraste de texto](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum): 4,5:1 para texto normal e 3:1 para texto grande. [Contraste não textual](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html): 3:1 nos indicadores visuais necessários dos controles. [Uso de cor](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html): informação não pode depender exclusivamente da cor.
- [Yale — taxonomia e rótulos](https://usability.yale.edu/ux/plan/establish-structure-findability/content-taxonomy-and-labeling): organização e vocabulário orientados ao que a pessoa procura.

Exemplos de produto consultados:

| Referência | Padrão aproveitado | Limite da consulta |
| --- | --- | --- |
| [Domínio — documentação de menus](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=3054) | Menus superiores com comandos agrupados; familiaridade para o escritório | Documentação pública; aparência não copiada |
| [Wealthsimple no Refero](https://refero.design/pages/93769142-8d9e-4cb3-b2b6-02d8e171ed35?query=navigation%20menu&source=search) | Navegação superior e separação de contexto e trabalho | Prévia pública; detalhe completo exigiu login |
| [Chargetrip no Refero](https://refero.design/pages/6539820f-3143-4fa2-98a6-c1654c672618?query=navigation%20menu&source=search) | Menu superior e conta separados dos dados | Prévia pública |
| [Wise no SaaSFrame](https://www.saasframe.io/examples/wise-dashboard) | Superfícies neutras, cor concentrada em destaques, hierarquia em dados financeiros | Captura de produto; navegação lateral não adotada |

Watermelon UI MCP consultado: catálogo de dashboards e entrada `astrix-dashboard` (workspace de conformidade, classificação e revisão). Aproveitada a composição de dados e estados claros/escuros como referência de componentes; nenhum código React foi introduzido em Django.

Skill `ui-ux-pro-max`: buscas de produto financeiro/B2B, navegação, teclado e stack `html-tailwind` como referência próxima do HTML/CSS existente. A busca ampla de design system também foi executada: retornou sugestões de landing page e OLED que não se ajustam à área autenticada. Essas recomendações foram descartadas em favor do contexto do produto e das fontes primárias acima.

## Implementação

- Área de trabalho do escritório sem barra lateral. Topo: Visão geral, Cadastros, Fiscal, Contábil, Documentos, Configurações e Copiloto.
- Menus mantêm a filtragem dos módulos permitidos; Equipe continua condicionada ao perfil. A navegação não substitui a autorização das views.
- NFS-e passa a ter Notas, Revisões e Coleta automática na mesma navegação local. URLs anteriores continuam funcionando. Pesquisa e retorno ao detalhe preservam filtros; retorno limitado às duas listas permitidas.
- Claro: branco/cinza. Escuro: grafite/cinza. Azul identifica interação; verde, sucesso; âmbar, atenção; vermelho, erro. Identidade verde mantida discretamente na marca.
- Preferência de tema preservada. Cor da barra do navegador acompanha a superfície.
- Menus usam HTML nativo (`details`, `summary`, links), com Escape, setas, foco visível e fechamento ao sair. Até 960 px, abrem abaixo do topo, em uma única árvore de navegação.
- Painel inicial identifica explicitamente NFS-e recebidas e pendentes de revisão.

## Auditoria Web Interface Guidelines

Fonte atual consultada: [Vercel Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md).

Revisão de todas as categorias aplicáveis: semântica, nomes acessíveis, formulários, foco, teclado, estado na URL, cores, conteúdo longo/vazio, responsividade, carregamento e feedback. Imagens, mídia, hidratação e animações não são introduzidas por esta mudança. Formatação de datas permanece no servidor Django, no contexto pt-BR existente.

Arquivos revisados, caminhos relativos a `src/apps/hub/`:

- `templates/hub/base.html:20` — corrigido: versão do script que sincroniza a cor do navegador.
- `static/hub/theme.js:9` — corrigido: meta theme-color agora deriva da superfície efetiva.
- `templates/hub/workspace.html:7` — aprovado no recorte: topo sem sidebar, landmarks, nomes de controles e destino do skip link.
- `templates/hub/workspace_navigation.html:1` — aprovado: links reais, disclosures nativos, estado atual e SVGs decorativos ocultos da árvore acessível.
- `static/hub/workspace.js:8` — corrigido: breakpoint alinhado ao CSS; Escape, foco e teclado verificados.
- `static/hub/workspace.css:98` — corrigido: bordas dos campos distinguíveis; superfícies e foco definidos por tokens.
- `templates/hub/nfse_navigation.html:1` — aprovado: links com estado atual, abas representadas na URL.
- `templates/hub/nfse_center.html:2` — aprovado: título específico, filtros rotulados, estados vazios e retorno à pesquisa.
- `templates/hub/nfse_collection.html:1` — aprovado: seleção rotulada, tabela semântica, estado vazio, orientação quando coleta indisponível.
- `templates/hub/reviews.html:2` — aprovado: título específico, relação explícita com NFS-e, filtros e cabeçalhos de tabela.
- `templates/hub/review_detail.html:3` — aprovado no recorte: retorno seguro às duas listas e navegação local persistente.
- `templates/hub/dashboard.html:4` — corrigido: rótulos distinguem notas recebidas e revisão; contraste sem decoração verde generalizada.

Limite conhecido anterior à alteração: a lista de notas consulta até 100 documentos e não tem paginação. Esta entrega não modifica esse comportamento; deve ser tratado na evolução da consulta de carteira. A auditoria não certifica acessibilidade integral do produto.

## Verificação executada

- 85 testes aprovados: navegação por módulo/perfil, destinos de retorno, workspace e isolamento da demonstração (`test_workspace_navigation`, `test_ui_review`, `test_hub_workspace_views_django`, `test_seed_demo_django`).
- Ruff e `manage.py check` sem problemas no recorte alterado.
- Playwright MCP: inspeção visual de dashboard, notas, revisões, detalhe e coleta; desktop 1440 px e celular 390 px. Verificação de layout adicional em 320, 768, 960, 961 e 1024 px.
- Encontrado overflow da navegação em 768 px; breakpoint corrigido para 960 px e rechecado. Dashboard, NFS-e, revisões, coleta, empresas, DTE e Copiloto sem overflow horizontal de página nas larguras rechecadas.
- Teclado: abrir Fiscal, setas, Enter, Escape e retorno do foco; menu móvel fecha com Escape; skip link leva ao conteúdo sem esconder o título sob o topo.
- Pesquisa de notas, abrir detalhe e voltar mantém a consulta; busca sem resultado mostra orientação. Coleta sem seleção informa o erro e foca o checkbox.
- Estado de envio conferido pelo handler real (`disabled` e `aria-busy`), cancelando a navegação no teste. Uma tentativa anterior de atrasar a resposta pelo interceptador do teste teve timeout; o interceptador foi retirado. Não foi uma falha de console do produto.
- Probe de contraste textual nas quatro telas principais, claro e escuro, sem valores abaixo do mínimo entre os textos avaliados. Probe exclui gradientes, transparência de elemento e controles desabilitados; não substitui auditoria manual completa. Campo de pesquisa no escuro: borda 4,45:1; texto do botão principal 5,52:1.
- Console das páginas locais: nenhum erro ou aviso. Estados de falha de provedores externos e escritório realmente sem dados não foram simulados no navegador; estados vazios de filtro e validação local foram.
- Apenas ambiente local e demonstração fictícia. Nenhuma contratação, chamada fiscal real, cobrança ou deploy.

Capturas em `artifacts/ui-navigation/`, incluindo `dashboard-light.png`, `dashboard-dark.png`, `dashboard-mobile.png`, `notes-dark.png`, `reviews-mobile.png`, `review-detail-mobile.png` e `navigation-mobile.png`.
