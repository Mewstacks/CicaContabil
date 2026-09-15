# CICA — direção pública antes de nova implementação

Status: pesquisa e crítica concluídas em 2026-09-13; esta é a referência para a próxima reconstrução, não uma aprovação de marca ou lançamento.

## O que a pesquisa mostrou

- A Omie apresenta para contadores uma combinação de gestão financeira, conciliação, tarefas, integrações e contratos; também separa Painel do Contador, OneFlow e ferramentas de processo. Isso confirma que a CICA não pode se vender como “mais uma IA”: a promessa deve ser a condução integrada da operação. Fonte: [Painel do Contador Omie](https://www.omie.com.br/funcionalidades/painel-do-contador/).
- A mesma referência usa prova, integração e ganhos operacionais, mas seu volume de mensagens e portfólio fragmentado deixam espaço para uma suíte com uma única visão de fechamento. Fonte: [Omie para contadores](https://www.omie.com.br/contadores/).
- StackAI é útil como referência de demonstração visual de fluxo e controles de enterprise, não como direção estética: dados, integração e resultado precisam aparecer juntos e sem chamar tudo de “IA”. Fonte: [StackAI / Framer](https://www.framer.com/stories/stackai/).
- A busca pública também encontra escritórios contábeis menores usando “Cica”. Isto não é uma análise marcária nem impede o uso decidido, mas exige assinatura constante do nome completo e uma consulta formal ao INPI antes do lançamento. Exemplo: [Cica Assessoria Contábil](https://www.contabilidades.org/sobre/cica-assessoria-contabil-praia-grande-sp).

## Diagnóstico da landing atual

O primeiro viewport foi inspecionado em desktop e 390 px. A página tem boa legibilidade e CTA visível, porém falha no que deve vender:

1. A frase “tem muito para ficar solto” é abstrata e não entrega uma consequência operacional concreta.
2. O hero parece uma interface de IA genérica; “uma guia vence amanhã” reduz a CICA a alerta pontual e esconde fiscal, financeiro, cliente, documentos e integrações.
3. A marca é uma letra C em um quadrado. Não diferencia CICA nem torna a sigla compreensível.
4. Há dois CTAs com a mesma função no primeiro viewport e o caminho de “teste” não é narrado de modo direto.
5. Não há prova real disponível ainda; não serão inventados clientes, estatísticas ou depoimentos.
6. O navegador requisita `/favicon.ico` e recebe 404; corrigir no refactor.

## Direção aprovada para construir

### Conceito

**A mesa de fechamento.** Em vez de uma tela de chat, a imagem principal será uma composição espacial de uma mesa de trabalho contábil: documentos, pendências, clientes e integrações entram por camadas e se organizam em uma única pauta de fechamento. A animação depende da rolagem e da interação — não é um loop decorativo.

O que o usuário deve entender em cinco segundos: “Esta é a central do meu escritório. Ela põe em ordem o que eu precisaria procurar em vários lugares.”

### Marca temporária

- Assinatura: **CICA** com a linha de apoio fixa **Central de Inteligência Contábil Avançada** em superfícies de descoberta: hero, rodapé, título social e tela inicial. Depois a abreviação pode funcionar sozinha no ambiente autenticado.
- Símbolo: monograma circular construído por dois arcos concêntricos e uma marca de pauta/controle; não usar mais uma letra branca dentro de quadrado arredondado.
- Paleta: marfim quente, verde floresta e verde sálvia claro. Sem azul elétrico, neon, vidro, gradiente roxo ou “orb” de IA.
- Tipografia: uma serif editorial só nos títulos de campanha e sans muito legível no produto. O sistema autenticado continua prioritariamente sans.

### Arquitetura da landing

1. Hero: promessa operacional curta + CTA “Começar teste de 14 dias” + confiança objetiva (“sem cartão; franquia de IA visível”).
2. Cena “mesa de fechamento”: visual de produto que revela a central, não um chat.
3. Faixa de capacidade: Fiscal, Financeiro, Clientes, Integrações, Inteligência — nomes de áreas, não lista de funcionalidades.
4. Bloco “Por que CICA?”: uma frase que abre a sigla e duas frases de benefício, sem manifesto longo.
5. Linha de operação: receber → organizar → revisar → decidir, cada passo associado a módulos reais.
6. Copiloto CICA como uma capacidade dentro da central: consulta, classificação, relatório e preparação de ação; fontes, somente leitura e aprovação humana.
7. Integrações: Domínio e Siescon com estados honestos. Siescon só é apresentado como ativo depois da homologação.
8. Segurança e implantação: leitura autorizada, evidência, responsável humano e início em 14 dias.
9. FAQ curto e CTA final. Preço detalhado e calculadora permanecem no ambiente autenticado.

### Motion

- Entrada única e curta no hero (opacidade/transform), seguida por composição espacial acionada por scroll; no mobile a cena é estática/interativa por toque.
- `prefers-reduced-motion` mostra a composição final, sem movimento contínuo e sem controle “Pausar”.
- Sem carrossel automático, ticker, números animados ou testemunhos fictícios.

### Critério de rejeição

Reprovar qualquer versão que possa ser confundida com: dashboard com chat de IA; grade genérica de três cards; landing preta/azul de tecnologia; ou página que prometa reduzir equipe/erros sem uma demonstração verificável.

## Skills e referências utilizados

- `ui-ux-pro-max`: sistema “editorial / Swiss”, landing de operação em tempo real e motion com alternativa reduzida.
- `watermelon-ui`: Astrix e Tallie; adotado o princípio de exceções/auditoria e não o visual ou copy.
- `landing-page-guide-v2`: usar hierarquia, CTA e narrativa de produto sem padrões genéricos.
- `landing-page-conversion-audit`: auditoria do primeiro viewport, fricção e CTA; não há tráfego ou métricas, então nenhuma conclusão quantitativa é feita.
- `art-direction`: conceito, constraints e qualidade da cena espacial.

## Pendências antes de publicar

- Pesquisa marcária formal no INPI e confirmação de titularidade do domínio escolhido.
- Prova social verificável, dados de implantação e contato de suporte — não inventar.
- Homologação Siescon antes de apresentá-lo como conectado.
