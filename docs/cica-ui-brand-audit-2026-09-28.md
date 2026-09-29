# CICA — sistema visual e auditoria integral de UX/UI

## Decisão aplicada

A D-184 substitui apenas a direção cromática da D-183. Os oito SVGs de `CICA.zip` foram incorporados sem alteração de geometria em `src/apps/hub/static/hub/brand/`. Lockups verdes aparecem em superfícies claras, lockups creme em superfícies escuras e o símbolo CA ocupa os espaços compactos. As versões preta e branca permanecem disponíveis para contraste extremo e produção monocromática. O monograma HTML/CSS foi removido das superfícies ativas.

Tokens principais:

- marca/ação/seleção controlada: `#114d44`;
- base institucional: `#e3ddca`;
- texto claro: `#17211f`; texto escuro: `#f5f0e3`;
- informação: `#245e78`; atenção: `#74510d`; erro: `#92352f`; sucesso: `#246547`;
- navegação e painéis: neutros, sem grandes superfícies verdes.

Manrope local, temas claro/escuro/sistema, movimento reduzido, foco de 3 px e densidade operacional foram preservados.

## Inventário e correções estruturais

A matriz anterior de 89 rotas foi substituída por uma geração repetível a partir do URLconf. Em 28/09/2026 ela contém 145 rotas de interface classificadas como tela, estado, ação ou download, ligadas a módulo, perfis e fixture sintética. Django Admin, APIs, webhooks e agente permanecem fora. O gerador é `scripts/generate_ui_inventory.py`.

Correções desta passagem:

- marca oficial em landing, demonstração, acesso/MFA, workspace e Console Mewstack;
- tokens oficiais no shell compartilhado, landing e autenticação;
- “Visão geral” e nome acessível corrigidos;
- orientação inicial permanece acessível por “Como usar”, mas não cobre o primeiro contato com a Visão geral;
- linhas repetidas sem requisito viraram um único resumo expansível “Cobertura a configurar”, mantendo empresa e área disponíveis sob demanda;
- foco, contraste, quebra de texto, temas e estados semânticos continuam centralizados.

## Evidência de mercado adaptada

- [Karbon](https://karbonhq.com/solution/bookkeeping/): empresa, responsável, prazo e trabalho no mesmo contexto;
- [Conta Azul Mais](https://ajuda.contaazul.com/hc/pt-br/categories/115001339088-Conta-Azul-Mais): diferença entre estado inicial e ativo e indicadores navegáveis;
- Dext: entrada, processamento, revisão e saída como etapas explícitas;
- [BlackLine](https://pages.blackline.com/OA2014-02DisplayGraphics_TiredofSpreadsheets.html): exceção, evidência, autoria e auditoria como foco.

No Watermelon, Astrix orientou a leitura de revisão, Tallie a apresentação de exceções, Demostack a troca de organização e Portfolio a priorização. Foram adaptados hierarquia e comportamento; nenhuma interface, copy, ativo ou código foi copiado.

## Limites e continuidade

Esta passagem não altera URLs públicas, APIs, permissões, regras fiscais, contratos, cobrança ou integrações; não cria migração e não realiza deploy nem chamadas externas. Estados que dependem de credencial, contrato, fonte ou regra ausente continuam exibidos como indisponíveis/bloqueados, nunca inferidos. A matriz é o contrato de cobertura para inspeções incrementais e não declara que uma integração real foi homologada.
