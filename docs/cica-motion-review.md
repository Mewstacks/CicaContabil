# CICA: revisão do hero e motion

Estado: implementação local em avaliação, 13/09/2026. Não representa aprovação da landing nem conclusão do objetivo SaaS.

## Referências observadas

As páginas foram abertas no Playwright, além da consulta às fontes:

- [Ramp](https://ramp.com/): narrativa de processamento documental; vídeo grande com etapas associadas ao produto. Adotada a sequência de tarefa; sem copiar vídeo, assets ou estatísticas.
- [Linear](https://linear.app/): separação entre chamada e produto, com hierarquia de leitura. Adotada a clareza de título/descrição/ação.
- [Mercury](https://mercury.com/): cena única de campanha ocupa espaço significativo. Adotado o princípio de composição única, sem reproduzir a paisagem.
- Watermelon `animated-components/tags`: continuidade entre estados; consultado como referência de transição, sem usar código React.

UI/UX Pro Max: buscas `financial SaaS product storytelling` (design-system), `responsive animation layout` (html-tailwind), `lighting performance responsive canvas` (threejs). Foram mantidos marfim/verde da marca; descartadas sugestões de paleta roxa e estatísticas sem comprovação.

## Direção e execução

Chamada em avaliação: **Menos retrabalho. Mais contabilidade.** A descrição identifica notas, conciliação, documentos, clientes e IA como parte da suíte.

Cena WebGL com Three.js 0.180.0, câmera, luzes, materiais, geometrias extrudadas, sombras e textura documental em alta resolução. Dependência MIT servida localmente em `static/hub/vendor/three`, com licença preservada. Sem serviços pagos ou chamadas de IA.

O exemplo se baseia na comparação OFX/lançamento contábil existente em `reconciliation.py`: empresa, data e valor. Não anuncia cruzamento NFS-e/OFX que não foi comprovado. Os dados de R$ 1.250,00 são ilustrativos, identificados como exemplo. Não são métricas reais.

Loop de 12 segundos: entrada (0–3s), comparação (3–7s), resultado disponível para revisão (7–12s). Repete enquanto visível. Controle acessível “Animação” permite desligar. Preferência de movimento reduzido apresenta o resultado estático. Página oculta e cena fora do viewport suspendem o desenho. Sem WebGL, aparece a ilustração SVG e os dados do exemplo continuam acessíveis.

## Evidências desta revisão

- Servidor utilizado: `http://127.0.0.1:8000/`, preservando o processo do túnel do usuário.
- Playwright: desktop 1366×768 e mobile 390×844; capturas inspecionadas; sem overflow horizontal nesses tamanhos. CTA principal visível no primeiro viewport.
- Loop confirmado após `data-motion-cycle >= 1`, ainda em execução.
- Checkbox desligou a execução; Space com foco voltou a iniciar.
- Mudança dinâmica para `prefers-reduced-motion: reduce` confirmou `running=false` e controle oculto.
- Perda de contexto WebGL foi simulada durante a revisão inicial da cena e mostrou o fallback SVG. Alterações posteriores do exemplo textual não revalidam por si só todos os navegadores/dispositivos.
- Console após carregamento atual: zero erros e zero avisos.
- Conteúdo textual não depende mais de JavaScript para ficar visível. Removido o código das abas de demonstração descartadas.

## Auditoria Web Interface Guidelines

Fonte consultada novamente: https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md

- `home.html`: título curto, CTA real, significado CICA mantido; legibilidade do primeiro bloco conferida.
- `cica_motion.html`: figura com descrição, exemplo identificado, controle nativo rotulado; dados legíveis fora da superfície 3D.
- `cica-campaign.css`: foco visível herdado, controles por toque, responsividade, alternativa reduced-motion; conteúdo permanece visível sem JS.
- `cica-scene.js`: loop controlável, suspensão fora da área visível, reduced-motion, perda de contexto e liberação de recursos. Não altera dados do SaaS.
- `cica-landing.js`: animação de entrada progressiva, cancelável com mudança de preferência; sem esconder previamente o conteúdo.

Não foram medidos FPS em hardware do público, Web Vitals de produção ou conversão. A aprovação visual do usuário permanece pendente. Demais telas, cobrança, catálogo, homologação das integrações e auditoria integral continuam no objetivo ativo.
