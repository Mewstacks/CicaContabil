# Revisão de interface e jornadas — 16/09/2026

Direção: menos texto, ações explícitas, filas compactas e recuperação no próprio fluxo. Django Templates, CSS, JavaScript e identidade CICA preservados. Alterações anteriores do workspace foram mantidas.

## Resultado e limites

As correções abaixo foram implementadas e verificadas localmente. **Não há aceite global de produção nem homologação externa nesta revisão.** Nenhuma chamada paga, publicação ou contratação foi realizada.

O servidor de QA usou bancos SQLite e arquivos separados em `.tmp/ui-review`, personas sintéticas, bloqueio de rede externa e adaptador ODBC exclusivamente sintético. A carteira extensa contém 240 empresas e 2.945 apurações. Não foi usado o banco operacional do usuário.

O Playwright MCP foi usado nas inspeções iniciais. Depois, seu transporte encerrou com `Transport closed`; os retestes continuaram com Playwright local e Chrome. Os scripts fecham os navegadores em `finally`. Esta distinção também vale para as evidências. Ao encerrar, não havia processo de navegador Playwright nem do servidor QA; os servidores existentes do usuário foram preservados.

## Problemas reproduzidos e correções

| Severidade | Problema | Correção | Reteste |
|---|---|---|---|
| Alta | Ações da tabela de apurações quebravam letra por letra; linhas enormes | Colunas dimensionadas, empresa clicável, uma ação Consultar, dados essenciais e cartões no celular | 2.945 apurações, nomes longos, 1440/1024/768/390/375, claro e escuro |
| Alta | Só as primeiras 30 apurações eram alcançáveis | Paginação de 30 com filtros na URL e alcance explícito da seleção | Páginas 1 e 2 no navegador; 61 registros sem omissões ou repetição no teste Django |
| Alta | Recuperação de senha retornava 403 no POST em navegador HTTP local | Política sem referência no endereço com token; `same-origin` somente no endereço sanitizado `set-password` | Senha alterada, token reutilizado recusado e login com nova senha |
| Alta | Cadastro podia ampliar acesso de operador além das empresas concedidas | Escopo e totais obedecem às concessões; criação só para papéis autorizados | Operador com 3 empresas, auditor e testes de autorização |
| Alta | Nova empresa desaparecia para proprietário com concessões explícitas | Criação e concessão ao proprietário/administrador na mesma transação | Regressão Django |
| Alta | Tema claro forçado no acesso e cores conflitantes no escuro | Tokens semânticos únicos; Claro/Escuro/Sistema no público, acesso, escritório e plataforma | Preferência oposta ao sistema, navegação, recarga e mudança do sistema |
| Alta | Botão de tema perdia seu valor ao ser desabilitado no envio | Preservação do submitter e restauração em `pageshow` | POST com CSRF e redirecionamento local; navegador sem erro 400 |
| Média | Erro de cadastro ficava em modal fechado | Reabertura do modal, dados preservados e foco no erro | CNPJ inválido, correção, Escape e retorno do foco |
| Média | CNPJ inválido aceito no cadastro | Validação e normalização existentes aplicadas ao formulário | Valores inválidos e válidos no teste Django |
| Média | Campo oculto obrigatório bloqueava importação OFX | Validação no seletor visível e navegação por teclado | Busca, setas, Enter e Escape |
| Média | Filtros perdiam contexto ou podiam mostrar resposta antiga | Cancelamento/geração de requisições, URL/histórico e reinicialização após troca parcial | Digitação sucessiva, nenhum resultado, detalhe, retorno e Voltar |
| Média | Seleção de permissões extensa era difícil de usar | Busca sem acentos, lista rolável e contagem independente do filtro | 240 empresas e preservação da seleção |
| Média | Menu móvel da plataforma e indicação de seção eram incompletos | Navegação equivalente e seção pai ativa nos detalhes | 390 px, teclado e navegação |
| Média | Suporte não tinha encerramento evidente no escritório | Faixa com escopo de suporte e botão Encerrar suporte | Início e encerramento como suporte |
| Média | Auditor via ações de consumo em Parcelamentos que terminavam em 403 | Ações oferecidas conforme permissão; leitura de resultados permanece disponível | Navegador claro/escuro, desktop/celular e POST forjado recusado |
| Média | Caixa DTE mostrava Parcelamentos como indisponível apesar da rota existente | Atalho funcional para a tela | Navegação real de DTE para Parcelamentos |
| Média | UUID inválido em consultas terminava em erro de servidor | Mensagem e recuperação nas entradas DCTFWeb/Parcelamentos | Regressões de parâmetros inválidos |
| Média | Envio de NFS-e perdia a ação do botão; repetição acidental possível | Ação preservada antes de desabilitar o envio | Ativação fictícia e testes do fluxo |
| Baixa | Títulos, rótulos e instruções repetidos | Texto reduzido; controles de lote das apurações aparecem após seleção | Inspeção das telas renderizadas |

## Matriz de jornadas

“Validado localmente” refere-se aos passos e estados indicados, não a todos os estados possíveis do módulo. O [inventário de rotas](revisao-ui-rotas-2026-09-16.csv) registra cada rota e distingue tela inspecionada, ação exercitada e cobertura pendente.

| Área / persona | Objetivo e passos | Resultado esperado | Evidência / situação |
|---|---|---|---|
| Público / visitante | Site → demonstração → iniciar | Ambiente fictício identificado | `extended-regression.json`, `local-regression.json`; validado localmente |
| Público / visitante | Site, cadastro, termos e privacidade em ambos os temas | Conteúdo legível e CTA alcançável | 48 capturas finais públicas; validado localmente |
| Cadastro / proprietário novo | Link válido → senha → primeiros passos → reutilizar link | Escritório criado uma vez; reutilização recusada | `access-regression.json`; validado localmente com confirmação sintética |
| Convite / proprietário novo | Link → senha → acesso → reutilizar | Ativação única | `access-regression.json`; validado localmente |
| Acesso / usuário | Login, link inválido, recuperação, nova senha e novo login | Erros recuperáveis e acesso com nova senha | `access-regression.json`, testes de autenticação e `reset-login.txt`; validado localmente |
| MFA / usuário e plataforma | Código inválido → TOTP → recuperação → acesso | Erro focalizado, segredo protegido nas capturas e acesso autorizado | `extended-regression.json`, `mfa-*.png`; validado localmente |
| Escritório / proprietário | Abrir primeiros passos e integrações | Próxima configuração identificável | Capturas de configuração; validado localmente para estados de teste |
| Escritório / proprietário | Trocar escritório → pesquisar → página 2 → voltar | Carteiras isoladas e contexto correto | `extended-regression.json`; validado localmente |
| Empresas / proprietário | Criar com erro → corrigir; lista → detalhe → retornar | Dados preservados e nova empresa acessível | `local-regression.json`, testes de UI; validado localmente |
| Equipe / proprietário, operador e auditor | Abrir permissões → buscar empresa → selecionar → filtrar | Seleção persistente e escopo respeitado | Carteira de 240 empresas; validado localmente. Envio externo de convite não homologado |
| Certificados / visitante demo | Simular certificado → NFS-e → ativar coleta | Estado fictício atualizado | `local-regression.json`; validado localmente. A1 e ADN reais bloqueados para homologação |
| Revisões / visitante demo | Fila filtrada → detalhe → decidir → retornar | Decisão registrada e filtro preservado | `local-regression.json`; validado localmente |
| Guias / proprietário | Buscar → selecionar página → paginar → consultar competência | Quantidade e alcance claros; contexto correto | `guides-fixed.json`; validado localmente |
| Guias / visitante demo | Simular emissão → resultado → baixar PDF | PDF identificado sem validade fiscal | `local-regression.json`; validado localmente |
| DTE / visitante demo | Mensagem → ciência fictícia → recarregar | Resultado persistido sem repetir a ação | `extended-regression.json`; validado localmente |
| DTE / operador autorizado | Preparar consulta; estados pendente/incerto/recuperação | Não repetir ciência ou consulta incerta automaticamente | Testes DTE e inspeção de detalhe; simulação visual de todos os retornos externos ainda pendente |
| Parcelamentos / visitante demo | Selecionar empresas → consulta em lote | Resultado fictício por empresa | `local-regression.json`; validado localmente |
| Parcelamentos / auditor | Abrir carteira → detalhe; tentar POST indevido | Leitura disponível, consumo recusado no servidor | `guides-fixed.json`, teste de autorização; validado localmente |
| Conciliação / usuário | Abrir importação → escolher empresa por teclado | Controle obrigatório utilizável | `local-regression.json`; validado localmente |
| Conciliação / visitante demo | Comparar candidatos → confirmar | Correspondência fictícia registrada | `local-regression.json`; validado localmente. Ciclo OFX real completo não homologado |
| Triagem / visitante demo | Lista → revisar → aprovar → arquivar → baixar | Arquivo recuperável e estado coerente | `local-regression.json`; validado localmente |
| Caixas / administrador | Abrir conexões e formulários | Ausência de configuração distinguível de ausência de arquivos | Capturas de caixas; conexão OAuth/IMAP externa bloqueada para homologação |
| Radar / usuário | Abrir radar e contexto de fontes | Fontes e estado apresentados sem prometer atualização externa | Capturas finais; frescor real depende de fornecedores |
| Copiloto / visitante demo | Escolher empresa → perguntar → ler resposta | Resultado sintético identificado | `extended-regression.json`; validado localmente para resposta fictícia |
| Aprendizado / proprietário | Abrir central vazia | Estado vazio legível em ambos os temas | `access-regression.json`; validado localmente. Curadoria com candidatos no navegador pendente |
| Plataforma / desenvolvimento | Escritórios → detalhe; MFA → seis seções de configuração | Acesso autorizado e formulários utilizáveis | 24 capturas de configuração após MFA; validado localmente para navegação |
| Plataforma / comercial e suporte | Tentar configuração restrita | 403 e saída para a área permitida | `local-regression.json`; validado localmente |
| Plataforma / suporte | Iniciar suporte → escritório → encerrar | Contexto e escopo visíveis; retorno à plataforma | `extended-regression.json`; validado localmente |

## Evidências principais

As capturas usam dados sintéticos. O screenshot enviado na conversa é a evidência anterior da tabela quebrada; não foi recriado como se fosse uma captura original em disco.

- [Apurações — desktop claro](../../.playwright-mcp/ui-review/guides-fixed-light-1440.png), [desktop escuro](../../.playwright-mcp/ui-review/guides-fixed-dark-1440.png), [celular](../../.playwright-mcp/ui-review/guides-fixed-light-390.png), [lote selecionado](../../.playwright-mcp/ui-review/guides-selected-mobile.png).
- [Parcelamentos — auditor](../../.playwright-mcp/ui-review/parcelamentos-auditor-dark-1440.png).
- [Recuperação de senha](../../.playwright-mcp/ui-review/access-reset-light-1440.png), [MFA com erro e segredo oculto](../../.playwright-mcp/ui-review/mfa-light-390.png).
- [Regressão geral](../../.playwright-mcp/ui-review/local-regression.json), [jornadas adicionais](../../.playwright-mcp/ui-review/extended-regression.json), [acesso](../../.playwright-mcp/ui-review/access-regression.json), [carteira extensa](../../.playwright-mcp/ui-review/guides-fixed.json).

Regressão geral final: 17 jornadas e 84 combinações de telas, temas e largura; sem erro de página registrado, rolagem horizontal indevida, controles visíveis sem rótulo ou ações espremidas detectadas. As capturas de `/platform/configuracoes/` que redirecionaram para MFA não são evidência da configuração; o aceite dessa tela usa as 24 capturas `config-section-*` após MFA.

Testes Django: 687 passaram, 1 teste opcional de Playwright Python foi pulado e 8 subtestes passaram. A correção posterior de recuperação de senha passou nos 3 testes específicos, incluindo CSRF. Ruff, `manage.py check`, `makemigrations --check --dry-run` e `git diff --check` passaram. Nenhuma migration adicional foi necessária nesta revisão.

## Auditoria das diretrizes

Aplicadas as skills `ui-ux-pro-max` e `web-design-guidelines`. A fonte atual da [Vercel](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) foi consultada em 16/09/2026. O [inventário de arquivos de UI](revisao-ui-arquivos-2026-09-16.csv) inclui também arquivos previamente alterados no workspace, sem atribuir essas alterações a esta revisão.

Regras aplicáveis verificadas: semântica e rótulos; foco e teclado; formulários e erros; animação reduzida; números tabulares; conteúdo longo; dimensões de imagens; listas; URL/histórico; confirmação de efeitos; toque; responsividade; temas; português e formatação Django; estados hover e mensagens. Regras de hidratação React e mídia não utilizada não se aplicam. Não foi adotado Title Case inglês nos rótulos em português.

Achados corrigidos, no formato da skill:

```text
src/apps/hub/static/hub/operations.css:141 — coluna de ações sem espaço intrínseco; links agora não quebram letra por letra.
src/apps/hub/templates/hub/guides_center.html:28 — seleção sem alcance e fila truncada; seleção da página e paginação explícitas.
src/apps/hub/static/hub/hub.js — modal, filtros assíncronos, estado de seleção e seletor OFX corrigidos.
src/apps/hub/static/hub/cica-auth.js — submitter preservado e estado restaurado no histórico.
src/apps/hub/static/hub/theme.css — superfícies, texto, foco, controles nativos e estados nos dois temas.
src/apps/hub/templates/hub/auth_base.html — tema claro fixo removido.
src/apps/platform/templates/platform/base.html — navegação móvel disponível.
src/apps/hub/templates/hub/parcelamentos.html — ações de consumo removidas do perfil somente leitura.
```

As sondas de contraste não encontraram texto abaixo dos limites nas capturas finais verificadas. O token de borda claro foi ajustado para `#7d8b7f`: contraste de 3,52:1 na superfície e 3,05:1 na superfície secundária. A carteira foi reinspecionada após esse ajuste. As sondas não cobrem integralmente gradientes, opacidade, gráficos, todos os estados de foco ou todos os limites de elementos não textuais; isto **não é certificação WCAG**. O teste de reflow em 720 CSS px representa a largura útil de 1440 a 200%; zoom nativo de 200% ainda precisa de inspeção própria.

## Referências e decisões adotadas

| Fonte | Padrão utilizado |
|---|---|
| [Linear Inbox](https://linear.app/docs/inbox) | Continuidade da fila ao detalhe, ação ligada ao contexto e retorno preservado |
| [TaxDome](https://help.taxdome.com/article/1216-mr-2503-docs-basic-bulk-actions) | Seleção explícita, quantidade e alcance do lote |
| [Karbon](https://karbonhq.com/en-GB/solution/email-management/) | Documentos e decisões no contexto da empresa |
| [Wise / SaaSFrame](https://www.saasframe.io/examples/wise-dashboard) | Resumo compacto, tarefa principal e histórico separados |
| Watermelon UI MCP — Astrix, Agndex e Demostack | Composições administrativas e contraste de superfícies, adaptados ao CSS existente |
| Refero | Busca por padrões operacionais; detalhes exigiam login e não foram considerados fluxos inspecionados |

Buscas da skill orientaram densidade de SaaS contábil, modo escuro, acessibilidade de formulários, teclado e tabelas responsivas. Não houve substituição da stack por componentes React.

## Bloqueios para liberação

| Módulo | Situação | Requisito restante |
|---|---|---|
| Base visual e navegação | Validado localmente nos estados registrados | Zoom nativo, leitor de tela e revisão integral dos elementos não textuais |
| Público, cadastro, convite, login e MFA | Validado localmente com tokens e entrega sintéticos | Entrega real de e-mail e configuração de domínio; convite de usuário já existente no navegador |
| Empresas, equipe e certificados | Validado localmente nas jornadas descritas | A1 real, configuração e permissões finais do escritório |
| NFS-e, DTE, DCTFWeb e parcelamentos | Bloqueado para homologação externa | Credenciais, procurações, respostas reais e tarifa/contrato definidos; autorização específica antes de chamada paga |
| Conciliação e arquivos | Validação local parcial | Importação OFX real completa, IMAP/OAuth, agente de arquivos e recuperação após interrupção externa |
| Radar e Copiloto | Validação local parcial | Frescor externo, evidências/exportação reais, limites e falhas do provedor; curadoria com candidatos |
| Plataforma e cobrança | Navegação e suporte validados localmente; cobrança externa bloqueada | Contratos, preços e políticas finais; emissão e conciliação de fatura no provedor |
| Regressão de falhas | Parcial | Demora, queda de rede, sessão expirada e conclusão parcial em cada módulo, não apenas nos componentes comuns/testes de backend |

Não foram inventados preços, carência, retenção ou políticas. Nenhum item desta tabela está marcado como homologado externamente. Os bloqueios são requisitos de aceite, não funcionalidades consideradas prontas por inferência.

## Repetição local

`scripts/qa_ui_server.py` prepara o ambiente isolado na porta 8011. Os scripts `qa_ui_browser.cjs`, `qa_ui_extended.cjs` e `qa_ui_guides.cjs` usam uma instalação local de Playwright via `PLAYWRIGHT_MODULE`. `qa_ui_access.cjs` requer links descartáveis de fixtures locais; os links utilizados nesta revisão já foram consumidos. Arquivos em `.tmp` e `.playwright-mcp` são artefatos locais, não dependências de execução da aplicação.
