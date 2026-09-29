# CICA — revisão da landing em 24/09/2026

Escopo: página pública em `src/apps/hub/templates/hub/home.html`, estilos em `src/apps/hub/static/hub/cica-landing.css` e sincronização da cor do navegador em `src/apps/hub/static/hub/theme.js`. Esta versão substitui as direções anteriores da mesma data conforme D-168 e D-169. A validação final está em V-197 de [VALIDACOES.md](../VALIDACOES.md).

## Direção final

A landing foi refeita do zero. A composição usa papel quente, grafite e terracota; verde aparece somente em um ponto de estado positivo dentro da demonstração do produto. Não há gradientes, flechas decorativas, cards genéricos em excesso, depoimentos inventados, métricas comerciais ou preço não aprovado.

O hero apresenta uma promessa concreta: “Feche o mês sem caçar informação.” A oferta explica em seguida que a CICA reúne tarefas, documentos, responsáveis e revisões por empresa. O CTA principal é sempre o teste de 14 dias; a demonstração é secundária e só aparece quando o gate real está habilitado.

A principal prova visual é uma central de fechamento criada em HTML/CSS para esta página. Ela mostra fila de trabalho, responsáveis, progresso e próxima decisão. Empresas, pessoas e atividades são fictícias, e a legenda declara que nenhum dado real é consultado. A composição não reutiliza `cica_motion.html` nem depende de JavaScript para revelar conteúdo.

## Estrutura adotada

1. Promessa e oferta curta, com um único CTA dominante.
2. Visão do produto em largura útil, antes da explicação longa.
3. Problema reconhecível da rotina: o atraso começa quando falta contexto.
4. Benefícios organizados por pessoa, empresa e gestão.
5. Recursos agrupados pelo trabalho realizado, em uma superfície grafite.
6. Fontes conectadas apresentadas como uma parte única da rotina, sem cards de disponibilidade ou roadmap.
7. FAQ antes do CTA final.

Por orientação expressa do proprietário em D-169, a landing apresenta Domínio, Integra Contador, e-mail e Siescon como partes prontas da mesma rotina. Foram removidos “Disponível por configuração”, “Em preparação” e as ressalvas de ativação das FAQs. O teste mantém “sem cartão” e “sem cobrança automática” conforme a decisão comercial existente.

## Pesquisa e padrões adaptados

| Fonte consultada | Padrão aproveitado | Adaptação para a CICA |
| --- | --- | --- |
| [Front — Operations](https://front.com/teams/operations) | Uma promessa operacional curta apoiada por uma visão concreta do produto. | A central de fechamento aparece imediatamente depois do hero e mostra o que precisa andar. Nenhuma marca, tela ou texto foi copiado. |
| [Karbon — Accounting workflow management](https://karbonhq.com/resources/introduction-to-accounting-workflow-management/) e [Monthly accounting](https://karbonhq.com/templates/monthly-accounting/) | Trabalho em andamento, bloqueios, prazo e responsável como unidade de compreensão. | A prova visual usa uma fila de 3 situações fictícias e uma próxima decisão, sem importar métricas ou alegações do concorrente. |
| [Pennylane — Expert-comptable](https://www.pennylane.com/fr/expert-comptable) | Produto apresentado como fonte de contexto comum, com capacidades agrupadas por rotina. | Os módulos são descritos por Fiscal, Contábil, Documentos e Atualizações, respeitando a disponibilidade real da CICA. |
| Watermelon UI MCP: `hero-11`, `hero-16` e `landing-01`; buscas posteriores por workflow e integrações sem correspondência | Separação clara entre proposta, produto e ação. | Foram rejeitados o verde dominante, vidro, brilho, hero escuro, bento, cards de status e prova social do catálogo. A página usa composição editorial neutra e uma faixa própria para as fontes. |

As skills `landing-page-design`, `design`, `design-system`, `ui-styling`, `brand`, `ui-ux-pro-max`, `landing-page-conversion-audit`, `landing-page-guide-v2` e `web-design-guidelines` foram consultadas nas decisões aplicáveis. Sugestões genéricas de azul/índigo, glassmorphism, gradientes, animações de entrada e arquitetura React/ShadCN foram descartadas por não servirem à marca, à simplicidade solicitada ou ao stack Django existente.

## Auditoria de interface

A fonte Manrope é local, possui preload e `font-display: swap`. O conteúdo usa HTML semântico, link de salto, hierarquia de títulos, `details`/`summary` nativos, foco visível, alvos de toque, quebra de texto, `scroll-margin`, cores de estado acompanhadas por texto e `prefers-reduced-motion`. O `theme-color` acompanha o fundo real nos temas claro e escuro.

A auditoria atual das [Vercel Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) encontrou contrastes abaixo de 4,5:1 em textos auxiliares da demonstração e no fechamento terracota. As cores foram corrigidas e a repetição da verificação não encontrou falhas nos textos visíveis dos temas claro e escuro.

O Playwright MCP inspecionou a página realmente servida em `http://127.0.0.1:8000/` nos tamanhos 320, 375, 390, 768, 1024 e 1440 px. Não houve overflow horizontal. Foram verificados desktop e celular, temas claro/escuro, navegação por teclado, link de salto, foco visível, abertura da FAQ por Enter e Space, links internos, carregamento sem JavaScript, rede e console. Capturas finais: `.playwright-mcp/landing-review/from-scratch-desktop-final.png`, `from-scratch-mobile-final.png`, `from-scratch-mobile-hero.png`, `from-scratch-mobile-product.png` e `from-scratch-dark.png`. Todas as abas do Playwright foram fechadas após a inspeção; o servidor local do usuário foi preservado.

## Limites

Esta revisão não mede vendas. Não foram fornecidos dados de tráfego, origem, cadastro concluído, ativação, receita ou abandono. O resultado resolve problemas observáveis de clareza, hierarquia, prova de produto, consistência e acessibilidade, mas qualquer efeito comercial precisa ser comparado em uma janela real de uso.

A apresentação solicitada em D-169 não executou nem verificou provedores, integrações externas, Siescon, Copiloto, pagamento, publicação ou produção. Nenhum serviço pago, rastreamento, mensagem ou deploy foi acionado.
