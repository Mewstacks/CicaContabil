# CICA — validações e evidências

## V-008 — E-mail transacional CICA

Data: 18/09/2026. Implementação local autorizada por D-76; nenhuma conexão SMTP ou envio externo foi realizado.

- Adicionadas versões HTML responsivas de confirmação de cadastro, convite de equipe e recuperação de senha. Os e-mails usam estrutura de tabela compatível com clientes de e-mail, CTA explícita, texto de reserva e `suporte@mewstack.com.br` (D-76).
- A recuperação de senha usa `html_email_template_name`; convite e confirmação geram `html_message` pela mesma entrega transacional. Links continuam sendo os mesmos links seguros e temporários já existentes.
- `.venv/Scripts/python.exe -m pytest tests/test_cica_password_reset.py tests/test_cica_signup_flow.py tests/test_hub_workspace_views_django.py -q`: **62 aprovados em 52,30 s**. Ruff dos arquivos Python alterados: aprovado.
- UI/UX Pro Max orientou hierarquia de título, tipografia e CTA; Watermelon não possui bloco de e-mail transacional correspondente. Revisão conforme Web Interface Guidelines: contraste, hierarquia, texto alternativo de reserva e ação explícita. Limite: renderização local/teste, sem entrega SMTP em clientes reais. D-77 transfere configuração, DNS e homologação de entrega para a etapa 12.

## V-007 — Etapa 02: auditoria inicial de acesso e administração

Data: 18/09/2026. Ambiente: checkout local, sem envio de e-mail, mudança de contrato, chamada de API externa ou dados de cliente.

- A auditoria estática encontrou cadastro, recuperação de senha, convites com expiração/revogação, MFA, escopo de empresas e módulos, bloqueio por contrato/teste, isolamento de locatários e console de plataforma.
- `.venv/Scripts/python.exe -m pytest tests/test_cica_signup_security.py tests/test_cica_signup_flow.py tests/test_mfa.py tests/test_permissions_and_lockout.py tests/test_tenant_isolation.py tests/test_invitation_takeover.py tests/test_cica_contract_mfa.py tests/test_cica_operation_access.py tests/test_platform_tenant_django.py -q`: **83 aprovados em 54,47 s**.
- Playwright local: cadastro em desktop e móvel 390×844, sem overflow horizontal, com foco visível de 3 px no primeiro campo e console sem erros. Capturas: `stage02-signup-desktop.png` e `stage02-signup-mobile.png`. Sessão fechada.
- Revisão de interface: UI/UX Pro Max indicou validação inline, resumo focalizável em falha de formulário, foco visível e autenticação compatível com gestores de senha. Watermelon não retornou bloco correspondente para formulário de autenticação; composição existente foi preservada. Referências de produto: [SaaSFrame Invite Team](https://www.saasframe.io/patterns/invite-friends), [Roles & Permissions](https://www.saasframe.io/patterns/roles-permissions) e [Login](https://www.saasframe.io/categories/login), adaptadas como evidência de padrão, sem cópia. Auditoria dos templates de autenticação contra as [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md): campos possuem rótulos, tipos e `autocomplete`; não foi aplicada mudança nesta auditoria.
- Limites: teste local não homologa SMTP, domínio/DNS, termos, condições comerciais, e-mail entregue/falho nem todas as jornadas visuais. Q-01–Q-06 e Q-29 permanecem abertos; etapa 02 não está concluída.

## V-006 — Retomada da etapa 01 em 18/09/2026

Pedido D-70 e decisão D-71. Inspeção confirmou que `runtime/trainer/Dockerfile` exige imagem externa e `runtime/trainer/runner.py` chama `llamafactory-cli` para executar treinamento. Mantida a ferramenta somente para esse runtime; a imagem oficial foi fixada por digest. Corrigido o Dockerfile: a cópia de `runner.py` apontava para a raiz inexistente do contexto e agora usa `runtime/trainer/runner.py`.

- `docker build --file runtime/trainer/Dockerfile --build-arg LLAMAFACTORY_IMAGE=hiyouga/llamafactory@sha256:46b6969e444681829294ed1fce2c4e8848613e654b682dc0359ba94357a0267b --tag cica-trainer:stage01 .`: aprovado; imagem local `sha256:f0c956…`, 26.4 GB.
- `docker run --rm --entrypoint llamafactory-cli cica-trainer:stage01 version/env`: CLI 0.9.6.dev0 iniciou; PyTorch 2.6.0+cu124; ambiente WSL detectou CPU, sem GPU disponível.
- `runtime/trainer/image.env` guarda o digest; o CI agora constrói `runtime/trainer/Dockerfile` com a mesma referência. A leitura do arquivo e o rebuild local por ele passaram usando cache.
- `.venv/Scripts/python.exe -m pytest tests/test_training_runner.py tests/test_deployment_config_django.py -q`: 12 aprovados.
- `.venv/Scripts/python.exe -m ruff check . --output-format concise`: aprovado.
- Limite: não houve download de modelo, dataset ou treino; CPU detectada não é avaliação de GPU. A configuração do CI foi testada localmente, mas a execução remota ainda depende do próximo push. Q-28 e Q-30 impedem homologação e mantêm a etapa 01 aberta conforme D-61.

Atualização D-72: Fedrizzi Contabilidade é o ambiente disponível e o proprietário aprova cada módulo. Não houve acesso externo nesta execução. A prova ainda depende da amostra e do acesso seguro de cada integração, além das metas de aceite.

Atualização D-73: metas de liberação aprovadas para uso em todas as etapas. Elas ainda não foram medidas nesta execução; a primeira evidência depende da amostra e do acesso seguro Fedrizzi.

Validação local posterior à D-73: `.venv/Scripts/python.exe -m pytest -q` resultou em **742 aprovados, 2 ignorados e 8 subtestes aprovados em 85,31 s**. Os ignorados são o Playwright Python opcional e o teste de lock que exige PostgreSQL; ambos têm cobertura específica registrada anteriormente. `manage.py check`, `makemigrations --check --dry-run` e Ruff continuam aprovados. A inspeção sem valores de `.env` e do ambiente local não encontrou configuração global de Siescon, Serpro, NFS-e, Asaas ou SMTP/e-mail. Em seguida, a inspeção segura do banco confirmou para Fedrizzi um `IntelligenceConnector` em modo `direct_odbc` e uma `DataSource` Domínio local em estado `ready`; DSN, credenciais, empresas e documentos não foram lidos. Isso corrige o registro anterior: Domínio já está conectado, conforme D-74.

## 18/09/2026 — complemento V-005: período simplificado (D-69)

Refinamento visual solicitado em seguida (“mais bonito”): busca/situação na primeira linha, período agrupado em superfície discreta, atalhos sem bordas pesadas, campos de 44px e ações alinhadas. UI/UX Pro Max consultado para espaçamento e reflow; Watermelon Astrix consultado como referência de composição de ferramenta fiscal. Preservadas as referências de produto anteriormente registradas. Template e CSS auditados com a fonte atual das Web Interface Guidelines. Playwright: 24 resultados após aplicar mês; erro de data, alternância exclusiva e mobile sem overflow; console sem erros. Inspecionadas capturas `nfse-polish-desktop.png` (escuro), `nfse-polish-light.png` e `nfse-polish-mobile.png`. Apenas refinamento visual da demo; etapa permanece aberta.

- Emissão usa digitação DD/MM/AAAA, aceita oito números e oferece Este mês, Mês anterior e Limpar datas. Campos inativos são desabilitados; competência continua exclusiva.
- Datas inválidas e intervalo invertido apresentam erro próximo aos campos; submissão inválida coloca foco no campo. Servidor também valida e preserva valores. URLs ISO anteriores continuam aceitas.
- Corrigida a filtragem da demo antiga: usa a mesma emissão do payload normalizado exibida na tabela, antes de limitar resultados. Setembro/2026 retornou 24 notas; agosto retornou zero; competência setembro retornou 24.
- Playwright local em localhost:8000: desktop 1440×1000 claro/escuro e mobile 390×844, sem overflow horizontal; atalhos, digitação sem barras, erro, alternância de critério, Tab e foco visível verificados. Console: zero erros. Sessão fechada após inspeção.
- Evidências: `nfse-simple-dates-desktop.png`, `nfse-simple-dates-mobile.png`, `nfse-simple-dates-dark.png`. Ruff focado aprovado. Auditoria dos arquivos de template, JS e CSS conforme fonte atual das Web Interface Guidelines: rótulos, teclado, mensagens, contraste de tema, responsividade e estado em URL revisados.
- Pesquisa: [GOV.UK Date input](https://design-system.service.gov.uk/components/date-input/) fundamenta entrada por teclado para datas conhecidas; adaptada para dois campos brasileiros em vez de seis campos separados. UI/UX Pro Max: formato local, teclado numérico e validação. Watermelon consultado por filtro, sem bloco correspondente; mantida a composição existente, anteriormente informada por SaaSFrame (Remote, June e Intercom).
- Limite: demonstração local, sem homologação fiscal ou conclusão da etapa 07.

Atualizado em 17/09/2026. Registro na raiz conforme D-59. Leia com [PLANO-MESTRE.md](PLANO-MESTRE.md) e [DECISOES.md](DECISOES.md).

**Escopo atual:** etapa 00 concluída; etapa 01 aberta e bloqueada em 18/09/2026 apenas pela imagem-base aprovada do runtime de treinamento (Q-37). Decisões do responsável ficam em DECISOES.md; este arquivo registra verificações técnicas, sem confundir decisão, teste e homologação.

## V-001 — Base técnica observada antes da edição documental

Data: 17/09/2026, nesta conversa. Ambiente: checkout Windows local, Python da `.venv`, configurações Django de teste; `TEST_USE_EXTERNAL_SERVICES=false` e `TEST_SQLITE_PATH` vazio. Banco de teste SQLite em memória. Sem homologação externa nesta análise.

| Verificação | Resultado observado | Limite |
|---|---|---|
| `python -m pytest -q` | 740 aprovados, 1 ignorado, 8 subtestes aprovados; 74,48 s | Não demonstra concorrência PostgreSQL nem operação real de serviços externos |
| Teste ignorado | `tests/test_cica_auth_flow.py:155`: Python Playwright opcional | Não equivale a navegação validada; não houve inspeção Playwright nesta etapa |
| `python manage.py check` | Sem problemas (0 silenciados) | Configurações de teste, não certificação de produção |
| `python manage.py makemigrations --check --dry-run` | No changes detected | Nenhuma migration aplicada por esta etapa; não prova migração de base produtiva |
| `python -m ruff check . --output-format concise` | 66 violações: comprimento de linha e ordenação de imports | CI ainda bloqueado; não corrigidas por restrição à etapa 00 |
| Inventário inicial Git | 291 entradas em `git status --short` antes da documentação | Trabalho local anterior preservado; não é uma release consolidada |

Os comandos acima foram executados na análise anterior à materialização dos documentos. A leitura de Ruff foi repetida em JSON antes da restrição final de escopo e manteve 66 achados. Não foram refeitos testes funcionais após mudanças exclusivamente documentais.

## V-002 — Evidência estática por área

| Área | Implementado / observado no código | Testado localmente nesta análise | Homologação real / venda |
|---|---|---|---|
| Cadastro, acesso, organizações, auditoria e privacidade | Modelos, rotas, serviços e testes no checkout | Suíte V-001; não atribuir cobertura integral a cada fluxo | Jornadas externas/produção não homologadas por esta análise |
| Domínio | Consultas fixas e limites 1.000/10.000/5.000; agente Python, fila, sync e descoberta | Suíte V-001 e leitura do código | Há registros históricos de sondagens ODBC; não comprovam cobertura completa ou instalação vendável |
| Agente Windows nativo | Heartbeat, backup e arquivamento; sincronização local ainda depende de Python | Leitura de `Worker.cs` e README; build não executado nesta etapa | Instalação limpa, atualização e destino real ainda pendentes |
| Siescon | Referência no modelo/UI; adaptador não encontrado | Busca estática; não há teste de conector real | Banco disponível confirmado pelo responsável; acesso e layout ainda não inspecionados |
| IA | API, roteamento local, corpus, runner QLoRA, avaliação e publicação; busca lexical | Suíte V-001; sem chamada de IA nesta etapa | Pipeline completo e hardware definitivo não homologados; geração histórica isolada não é aceite de produto |
| Triagem | OAuth/IMAP, leitores, quarentena, revisão/arquivo e trabalho Windows | Suíte V-001 | Caixas, scanner, análise e arquivamento reais ainda requerem piloto |
| NFS-e | Cliente ADN, mTLS, checkpoints e área operacional | Suíte V-001, respostas simuladas | Não houve consulta ADN nesta análise |
| Integra | DTE, DCTFWeb, PARCSN, filas e consumo | Suíte V-001, transporte simulado | Não houve consulta/ciência/emissão Serpro nesta análise |
| Conciliação | Fontes preservadas, layouts, movimentos, lançamentos e exportação | Suíte V-001, fixtures | Layouts reais, importação nos ERPs, OCR e volume ainda exigem prova |
| Radar | Coleta e tarefas existentes | Suíte V-001 | Agenda e relevância operacional não homologadas nesta análise |
| Cobrança | Medidores/faturas e receptor Asaas | Suíte V-001 | Cliente de cobrança e ciclo completo Asaas ainda pendentes |
| Infraestrutura | Compose, workflows, imagens e runbooks | Inspeção estática | Não houve build/deploy, PostgreSQL/Redis reais ou restauração nesta etapa |

## V-003 — Etapa 00: documentação e continuidade

Estado: **concluída em 17/09/2026**. Aceite documental atendido; não equivale a conclusão funcional dos módulos.

Entregas: plano e decisões na raiz, registro de validações, 14 arquivos de etapa com prompts, inventário estático, dúvidas com responsáveis/dependências, ponteiros dos endereços anteriores e instrução de continuidade em AGENTS.md.

Conferência realizada por script local de leitura, sem importar Django ou acessar bancos:

- 23 arquivos centrais/etapas conferidos; 135 destinos de links locais existentes.
- 14 etapas numeradas de 00 a 13, cada uma com dependências, decisões, escopo/checklist, bloqueios, testes/aceite, evidências/próximo passo e prompt.
- 60 IDs de decisão únicos (D-01–D-60), preservando o grau de confirmação dos registros históricos.
- 36 IDs de perguntas únicos (Q-01–Q-36); resolvidas permanecem identificadas, sem reabrir Q-07/Q-10.
- Nenhum caractere Unicode de substituição nos 23 arquivos conferidos.
- `git diff --check -- '*.md'`: aprovado, apenas avisos Git de conversão futura LF/CRLF.

A primeira execução do verificador textual recebeu acentos substituídos pelo pipe PowerShell e reportou títulos ausentes; corrigido o verificador para comparar texto normalizado. A segunda execução passou. Os arquivos estavam em UTF-8 e não foram alterados para contornar a validação.

Não houve edição de código da aplicação, migração, instalação de dependências, conexão a banco de cliente, execução de treino, chamada paga, deploy ou publicação nesta etapa. Não foram alterados arquivos `.env`, credenciais ou dados de clientes.

## Como acrescentar evidência

## V-009 — Etapa 02: acesso e administração locais

Data: 18/09/2026. Ambiente: checkout local Windows e aplicação em `127.0.0.1:8000`; sem SMTP, DNS, API paga, envio externo ou acesso a dado de cliente.

- `.venv/Scripts/python.exe -m pytest tests/test_accounts_api.py tests/test_hub_api.py tests/test_tenant_isolation.py tests/test_permissions_and_lockout.py -q`: **22 aprovados em 21,04 s**. Cobrem login/CSRF, API somente leitura, isolamento por organização e recusa de acesso sem contexto.
- `.venv/Scripts/python.exe -m pytest tests/test_seed_demo_django.py -k "separate_demo_link or visitor_cannot_mutate or copilot_conversation or nfse_review_decision" -q`: **4 aprovados em 22,58 s**. A sessão demo é privada, não altera administração/empresas e não persiste conversa ou decisão compartilhada.
- Playwright autenticado: o login local levou uma administradora ao cadastro obrigatório de MFA; o código de uso único abriu o painel. Equipe, empresas e configurações responderam 200; a viewport 390×844 não teve overflow horizontal, o foco era visível e o console tinha zero erros. A sessão foi fechada ao fim.
- A tentativa de `seed_demo` foi recusada porque o slug de demonstração já pertence a um escritório operacional local. Nenhum dado foi sobrescrito. Isso confirma a proteção contra criação de massa fictícia sobre escritório operacional; os testes isolados acima usam banco de teste.

Limites: as regras D-79 serão operacionalizadas e homologadas na etapa 10. SMTP Brevo, DNS e entrega real são da etapa 12 por D-77/D-78. Esta validação não é homologação externa nem liberação comercial.

## V-010 — Etapa 03: contrato ODBC Domínio Fedrizzi

Data: 18/09/2026. Ambiente: conexão ODBC Domínio já registrada para Fedrizzi (D-74), com autorização de homologação D-72. Nenhum DSN, credencial, empresa, documento ou conteúdo de origem foi exibido.

- `validate_dominio_odbc_contract` foi executado usando a referência de DSN protegida do conector: **4 consultas allowlisted, 5 objetos obrigatórios, 13.875 linhas lidas e 0 coluna ausente**. A execução registrou auditoria de contrato e não escreveu no Domínio.
- `discover_dominio_schema --limit 500 --apply` examinou e registrou somente metadados: **500 objetos, 4.733 colunas, 0 objeto novo/alterado e 500 inalterados**. Isso confirma que o catálogo já persistido corresponde ao ambiente consultado.

Limites: as consultas atuais não estabelecem ainda a cobertura integral de dados contábeis, fiscais e de folha, nem provam o agente nativo, paginação/incremental, interrupção de rede, instalação limpa ou importação Web. Esses itens seguem abertos na etapa 03.

Complemento: a rota v2 `dominio/companies` e o processador nativo paginado foram implementados. `tests/test_intelligence_agent_django.py` teve **5 aprovados em 28,29 s**, incluindo autenticação e espelhamento da página local. `dotnet build agent-windows/src/CICA.Agent.Service/CICA.Agent.Service.csproj -c Release --no-restore` concluiu sem avisos nem erros. A paginação é por código Domínio, 500 linhas por página, e nunca desativa empresas em página parcial. Ainda falta executar o binário com DSN Fedrizzi, testar fila/rede/reinício e completar as projeções contábil, fiscal e folha.

## V-011 — Etapa 03: máquina Fedrizzi e pacote instalável

Data: 18/09/2026. Ambiente: estação Windows na rede Fedrizzi. Sem instalar serviço ainda, para não registrar um processo destinado a falhar.

- DSN de sistema `contabil` encontrado em 32 e 64 bits, ambos sobre SQL Anywhere 17; o conector Fedrizzi no CICA está saudável e tem DSN protegido configurado.
- Não havia serviço ou diretório de dados CICA/HubContador/CICA prévio. A conta atual pertence ao grupo Administradores; .NET SDK 10 e WiX 6 estão instalados.
- `agent-windows/build.ps1` produziu MSI, checksum e inventário de dependências em `agent-windows/artifacts/`. O MSI tem 79.285.770 bytes. Ele ainda usa identidade de instalador legada no nome interno; a renomeação externa para CICA continua na etapa 03.
- A instalação/pareamento não foi executada porque o checkout só aceita `localhost`, não há URL HTTPS pública, CA de agente nem chave de CA configuradas. O configurador exige URL HTTPS e o endpoint v2 exige CA para emitir o certificado do agente. Instalar nesse estado criaria um serviço sem configuração funcional.

Próxima ação necessária: disponibilizar o endpoint HTTPS da CICA e configurar sua CA de agente no ambiente que o atende; então gerar o enrollment, instalar o MSI e validar conexão, reinício, corte de rede e retomada nesta mesma máquina. Não há custo estimado para a instalação local; uma publicação/hospedagem, se necessária, exige orçamento e autorização específicos.

## V-005 — Demonstração NFS-e: carteira e download em lote

### Revisão visual adicional — 18/09/2026

Complemento: substituído input month nativo por mês (select com nomes completos) e ano digitável; preservado parâmetro legado de competência no servidor. Intervalo de emissão fixado em duas colunas, com cache CSS v4. Playwright confirmou campos De/Até no mesmo eixo e altura 44 px em desktop; mês/ano selecionáveis e sem overflow a 390 px. Inspeção visual salva em `nfse-period-fixed.png` e `nfse-month-mobile.png`.

CSS específico `nfse.css` corrige conflitos do grid genérico: filtros alinhados, apenas período ativo visível, campo de acumulador de 42 px com bordas arredondadas, ícone de edição decorativo, foco e estados hover/seleção. JS versionado evita reaproveitamento da versão anterior pelo navegador. Limpar acumulador agora mostra revisão e Transitória 0%, inclusive numa linha originalmente classificada.

Playwright em `127.0.0.1:8000`: desktop 1440×1000 claro/escuro e móvel 390×844 escuro inspecionados por screenshots. Sem overflow horizontal. Digitar `501` mudou situação para Classificada; Enter selecionou uma nota; limpar mostrou Transitória 0%; alternar para emissão ocultou competência e mostrou somente o intervalo. Console: zero erros e avisos. Auditoria dos arquivos alterados conforme [Vercel Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md), com correção do rótulo móvel Situação e dos blocos vazios provocados por content-visibility.

Referências mantidas da pesquisa desta tarefa: Watermelon Gridline para organização operacional; [Remote](https://www.saasframe.io/examples/remote-empty-employee-table), [June](https://www.saasframe.io/examples/june-dashboard) e [Intercom](https://www.saasframe.io/examples/intercom-users-table) para barra de ações e tabela densa. UI/UX Pro Max consultado para edição inline e dimensões consistentes de input. Sem redesenhar a navegação geral.

Data: 18/09/2026. Ambiente: demonstração local `http://127.0.0.1:8001`, dados fictícios; sem consulta ADN, certificado, escrita em pasta Windows ou alteração da classificação persistida.

- A carteira exibe data de emissão extraída do payload normalizado da NFS-e; a massa nova de demonstração inclui `dhEmi` no XML e persiste `issued_at` ao criar o documento.
- O filtro permite escolher competência de emissão ou intervalo de emissão. A interface alterna o único critério ativo sem combinar ambos.
- Download demonstrativo gera ZIP com `Emitidas/CÓDIGO -/` ou `Tomadas/CÓDIGO -/`, XMLs e `manifesto-classificacao.csv`. Uma nota sem acumulador segue como Transitória a 0%; classificadas da demonstração mostram acumulador e 97%. Acumulador digitado é decisão manual no manifesto.
- `Enter` em um acumulador seleciona a nota e avança o foco, sem submeter um download vazio. Verificado no navegador local.
- Digitar acumulador foi inspecionado no navegador: a linha passou para Classificada e exibiu `Definida pelo contador · 100%` (D-68).
- Ruff focado e `git diff --check` passaram. Playwright inspecionou a lista, a alternância de filtro, seleção por teclado e viewport móvel 390×844; console sem erros.

Limites: esta é somente demonstração local. A etapa 07 permanece aberta: coleta ADN, certificados, deduplicação real, catálogo de acumuladores e homologação de importação Domínio não foram concluídos.

Use ID V único, data, etapa, ambiente, comando/procedimento, resultado, caminho da evidência e limites. Diferencie resultado observado nesta execução de relato histórico. Registre falhas e skips. Só avance de teste local para homologação após prova no ambiente correspondente e de homologação para liberação com o aceite aplicável.

Histórico detalhado anterior: [registro de execução](docs/planejamento/registro-de-execucao.md). [Próxima etapa preparada](docs/planejamento/etapas/01-base-tecnica.md), ainda não autorizada pela última instrução de escopo.

## V-004 — Etapa 01: estabilização técnica em andamento

Data: 17–18/09/2026. Ambiente: Windows local, Python .venv, Docker Desktop 4.91.0, WSL 2.7.1, PostgreSQL 17 e Redis 7.4 em volumes locais isolados. Sem conexão a banco de cliente, ERP, API paga, deploy ou alteração de dados de clientes.

| Verificação | Resultado | Limite |
|---|---|---|
| Ruff | 66 achados iniciais eliminados; ruff check aprovado | ruff format --check encontra 95 arquivos fora do formato, mas esse comando não integra o CI e não foi aplicado em massa para não reformatar trabalho local alheio |
| Migrações e Django | manage.py check aprovado; makemigrations --check --dry-run sem alterações | Validado nas configurações de teste |
| Suíte completa | 740 aprovados, 2 ignorados, 8 subtestes; 72,61 s | SQLite em memória; o teste concorrente é corretamente ignorado nesse backend e executado em PostgreSQL |
| Testes de risco em PostgreSQL | 95 aprovados em token billing, faturamento, treinamento IA, fila de triagem, conciliação, MCP e privacidade; 69,67 s | Bancos `test_saas` e `test_knowledge` isolados; não é homologação externa |
| Concorrência de consumo | 4 chamadas paralelas com a mesma chave de idempotência produziram 1 evento e 8 tokens reservados; 1 teste aprovado em PostgreSQL | Não é teste de carga; faturamento, filas e publicação foram exercitados na suíte de risco com locks/transações PostgreSQL |
| Dependências | pypdf atualizado de 6.9.2 para 6.16.1; uv lock, uv sync --locked --all-extras, pip check e pip_audit aprovados | O projeto local não é auditável no PyPI, mas todas as dependências publicadas estão sem vulnerabilidades conhecidas |
| Agente Windows | Service, configurador e MSI foram compilados; agent-windows/artifacts/CICAAgent.msi gerado com SHA-256 6ed0a1592fc3f0b5c5277e9dfc3ce8f27c000c6ca493cb3f5c245ac94c23f9b9 | Não instalado nem exercitado em máquina limpa |
| Docker/WSL e serviços | Docker Desktop 4.91.0 e WSL 2.7.1 operacionais; Compose iniciou PostgreSQL 17 e Redis 7.4 saudáveis | Serviços locais persistem em volumes Docker; não equivalem a ambiente de produção |
| Worker real | Celery com pool `solo` no Windows consumiu `platform.advance_tenant_lifecycles` via Redis e retornou `SUCCESS` com resultado `0` | O pool padrão `prefork` falha no Windows com `WinError 5`; produção Linux deve manter pool próprio e ser homologada na etapa 12 |
| Imagens Docker | `cica-backend:stage01` e `cica-multimodal:stage01` construídas, respectivamente `sha256:5c9a3b3…105d2` e `sha256:59e292a…80cdc` | O runtime de treinamento não foi construído: falta referência LlamaFactory aprovada por digest (Q-37) |

Nenhuma alteração de migração foi gerada. As correções de lint foram mecânicas: ordenação de imports e formatação das nove unidades que apresentavam os 66 achados. A validação PostgreSQL revelou e corrigiu dois locks inválidos de `JournalEntry` com joins opcionais: aprovação e exportação agora travam somente a linha principal (`of=("self",)`). A atualização de pypdf é fixa e reproduzida em pyproject.toml, requirements.txt e uv.lock.

Próximo procedimento: receber e registrar a referência LlamaFactory aprovada em Q-37, construir o runtime de treinamento e registrar o resultado. Conforme D-61, a etapa permanece aberta até esse item terminar; nenhuma imagem, modelo ou treinamento será escolhido por inferência.
## V-012 — Marca CICA no agente e tela de entrada

Data: 18/09/2026. Toda referência textual e de caminho à marca anterior foi removida do código-fonte ativo. O serviço é `CicaAgent`, o configurador e o pacote usam CICA, e o instalador recompilado está em `agent-windows/artifacts/CicaAgent.msi` (SHA-256 `5e111919be1751997239955a3435756a3cb26c2d06fe00fe4f2ed4c03b85a2ec`). `manage.py check` passou; a resposta local de `/entrar/` contém os assets `cica-auth.css` e `cica-auth.js`; os dois projetos .NET compilaram sem avisos ou erros. A inspeção visual automatizada não foi possível porque não há navegador disponível nesta estação nesta sessão; esta limitação não afeta a validação do template e dos assets.

## V-013 — Leitura integral de backup Domínio no agente nativo

Data: 18/09/2026. Foram removidos os limites silenciosos de 10.000 empresas e 100.000 lançamentos do `BackupProcessor`. A leitura do backup continua paginada em lotes de 500 no envio à API, mas não descarta linhas por teto fixo. O projeto `Cica.Agent.Service` compilou em Release, sem avisos ou erros. Isto valida somente o código e o build; a execução contra um backup autorizado, retomada após falha e prova de não duplicação continuam pendentes na etapa 03.

## V-014 — Instalação local do agente CICA

Data: 18/09/2026. O MSI `CicaAgent.msi` foi instalado com privilégio administrativo nesta estação. O Windows registrou o serviço `CicaAgent` com nome exibido `CICA Agent`, inicialização automática e estado `Running`. Os arquivos foram instalados em `C:\Program Files\CICA Agent\Service` e o diretório de configuração foi criado em `C:\ProgramData\CICA\Agent`. Sem `agent.config`, o serviço permaneceu ativo sem tentativa de Domínio ou rede, como previsto. Uma tentativa não elevada retornou erro 1925; a instalação elevada retornou código 0. O reinício pós-instalação ainda requer um terminal administrativo nesta estação; pareamento HTTPS e comunicação externa ficam para a etapa 12 por D-81.

## V-015 — Recuperação do ambiente local e catálogo Domínio

Data: 18/09/2026. O banco local de desenvolvimento `db.sqlite3` não era legível pelo SQLite. Foi substituído pela cópia íntegra local `.tmp/ui-review/db.sqlite3`, migrações e `manage.py check` passaram. O escritório local Fedrizzi e seu conector ODBC foram recriados sem sincronização de dados. A validação ODBC leu 13.875 linhas por quatro consultas allowlisted, confirmou cinco objetos e zero colunas ausentes. A descoberta persistiu somente metadados: 500 objetos gerais, 49 de folha com prefixo `FOV` e 387 contábeis com prefixo `CT`; não foram impressos dados de origem. Não havia backup `.dom` acessível nas pastas locais verificadas, portanto a importação Domínio Web real permanece pendente de um arquivo autorizado e sua chave correspondente.

## V-016 — Conector oficial Domínio / Onvio preparado

Data: 18/09/2026. A pesquisa oficial confirmou o contrato ERP Domínio v3 (ativação, envio e consulta de lote XML) e o contrato Onvio BR Accounting v2 (OAuth por código, refresh token, lista paginada de clientes e estado da integração). `apps.hub.dominio_api` implementa esses contratos sem credenciais embutidas e sem chamada externa durante o teste. Quatro testes automatizados aprovaram token, ativação, `integrationKey`, multipart XML, consulta de lote, OAuth, paginação de clientes e estado da integração; Ruff e `manage.py check` passaram. A documentação pública consultada não descreve leitura de lançamentos, escrita fiscal ou folha do Domínio Web: essa capacidade somente poderá ser adicionada se a Thomson Reuters entregar Swagger e escopos específicos à CICA.

## V-017 — Reinício administrativo do agente instalado

Data: 18/09/2026. O serviço `CicaAgent` foi reiniciado com privilégio administrativo nesta estação e retornou ao estado `Running`, mantendo início `Automatic`. Sem configuração de rede, o serviço não possui `agent.config` e permanece aguardando configuração. Isso prova instalação e reinício local; não prova pareamento, revogação, atualização distribuída ou recuperação de rede, que dependem do ambiente hospedado da etapa 12.

## V-018 — Limites comerciais da integração Domínio Web documentados

Data: 18/09/2026. A referência [docs/dominio-web-limitacoes-comerciais.md](docs/dominio-web-limitacoes-comerciais.md) consolidou a linguagem comercial para API Domínio/Onvio, agente local e backup de contingência. Ela usa somente os contratos oficiais registrados em `docs/dominio-api-oficial.md` e aponta, de forma explícita, que OAuth, API oficial, pareamento público e backup `.dom` real ainda não foram homologados.

Limite: este registro documenta a promessa permitida; não é teste de backup e não libera divulgação, ambiente hospedado ou integração externa.

## V-019 — Preparação segura do backup Domínio Web

Data: 18/09/2026. O processador nativo passou a conferir SHA-256 antes de abrir o backup, baixar em arquivo temporário com troca atômica e aceitar URL de download somente do mesmo servidor CICA configurado. A extração valida todos os caminhos antes de gravar qualquer entrada e recusa arquivo absoluto, nulo ou que saia da fila temporária. O envio continua paginado em 500 registros e não possui os antigos limites silenciosos de leitura.

Conforme instrução do responsável, **não foi executado teste, build ou validação de backup nesta alteração**. A comprovação com arquivo `.dom` autorizado, chave, interrupção de rede, retomada e não duplicação permanece obrigatória na etapa 12. Este marco é somente implementação preparada.

## V-020 — Diagnóstico operacional local do agente preparado

Data: 18/09/2026. O serviço nativo passou a validar a configuração antes de iniciar o ciclo e a escrever `C:\ProgramData\CICA\Agent\agent-status.json` por substituição atômica. O arquivo informa somente estado, detalhe seguro, data UTC e versão; não registra senha, certificado, segredo, DSN ou dado do Domínio. Os estados previstos são `awaiting_configuration`, `configuration_error`, `synchronizing`, `ready` e `temporary_error`. Falhas transitórias de HTTP ou tempo limite passam a esperar progressivamente de um a cinco minutos; uma falha ao gravar o diagnóstico não interrompe o serviço.

Conforme instrução vigente, **não foram executados build, teste ou validação do agente nesta alteração**. A inspeção do arquivo, a recuperação após indisponibilidade de rede e a validação de instalação limpa continuam obrigatórias na etapa 12. Este marco é somente implementação preparada.

## V-021 — Renovação local de certificado do agente preparada

Data: 18/09/2026. O agente nativo passou a inspecionar o vencimento do certificado protegido no PFX local. Com menos de 30 dias para expirar, depois de concluir um ciclo já autenticado, ele cria um CSR com a chave privada existente, chama a rota já exposta `api/agent/v2/certificate/renew` e substitui de forma protegida somente o certificado local. O endpoint pode recusar o agente revogado; nesse caso o estado local passa a `authorization_error` e a configuração não é apagada automaticamente. A chave privada não é enviada ao servidor.

Conforme instrução vigente, **não foram executados build, teste ou validação do agente nesta alteração**. A renovação real depende de HTTPS publicado, proxy com mTLS, CA configurada e um agente pareado; todos são itens da etapa 12 por D-81. Este marco é somente implementação preparada.

## V-022 — Versionamento e aviso de atualização do agente preparados

Data: 18/09/2026. `agent-windows/build.ps1` passou a receber uma versão explícita e a propagá-la para serviço, configurador e MSI, por exemplo `./build.ps1 -Version 1.2.3`. O artefato inclui `release.json` com versão, nome e SHA-256, além do checksum separado. O heartbeat compara a versão instalada com a versão devolvida pelo servidor e registra `update_available` no diagnóstico local quando houver uma mais nova. O agente não baixa, não executa e não instala MSI automaticamente; a publicação do pacote, assinatura, URL, checksum e atualização em estação real permanecem para a etapa 12.

Conforme instrução vigente, **não foram executados build, teste ou validação do agente nesta alteração**. Este marco é somente implementação preparada.

## V-023 — Comando de diagnóstico local preparado

Data: 18/09/2026. Foi incluído `agent-windows/diagnosticar.ps1` para suporte técnico local. O comando inspeciona a instalação do serviço e configurador, presença da configuração protegida, estado seguro escrito pelo runtime, quantidade de DSNs de sistema e presença de driver SQL Anywhere. Ele não abre `agent.config`, não tenta conexão, não consulta dados Domínio e não imprime nomes de DSN, senhas, certificados ou segredos. Retorna código 2 para instalação incompleta e 3 para estado de configuração/autorização que exige correção.

Conforme instrução vigente, **não foram executados build, teste ou validação do agente nesta alteração**. A execução no computador do escritório, os cenários x86/x64, rede indisponível, revogação e atualização real continuam obrigatórios na etapa 12. Este marco é somente implementação preparada.

## V-024 — Compatibilidade ODBC x64 do configurador preparada

Data: 18/09/2026. A inspeção local encontrou ao menos um DSN de sistema e dois drivers SQL Anywhere em cada arquitetura, sem registrar seus nomes ou qualquer dado da conexão. Como o serviço CICA Agent instalado é x64, o configurador passou a listar somente DSNs e drivers SQL Anywhere de 64 bits. Quando não houver um DSN compatível, ele desativa o teste de conexão e informa a ação necessária. Isso impede configurar uma fonte 32 bits que o processo x64 não poderia abrir.

UI/UX Pro Max foi consultado para validação junto à escolha da fonte: a correção usa erro no próprio ponto da escolha e não depende de falha no envio. Watermelon UI não esteve disponível nesta sessão. As diretrizes Web Interface Guidelines foram consultadas; são voltadas a HTML e não possuem violação aplicável ao controle nativo WinForms alterado. Não foi possível usar Playwright porque o configurador é um aplicativo Windows não navegável.

Conforme instrução vigente, **não foram executados build, teste ou validação do agente nesta alteração**. A execução visual e funcional do configurador, inclusive teclado, foco e a conexão ODBC real, continua obrigatória na etapa 12. Este marco é somente implementação preparada.
## V-025 — Destino Windows configurável por escritório preparado

Data: 18/09/2026. A configuração de Triagem passou a salvar, por escritório, a raiz Windows e um formato de subpastas. O formato aceita apenas `{company_name}`, `{dominio_code}`, `{document_type}` e `{period}`; exige empresa ou código Domínio, bloqueia caminho absoluto, subida de diretório e caracteres inválidos do Windows. Cada fila recebe o caminho relativo já resolvido, então mudanças futuras não alteram documentos que já estão em processamento. A raiz é restrita a caminho local absoluto nesta fase: serviços Windows não devem depender de unidade mapeada; UNC só será liberado depois de conta de serviço e permissão homologadas.

Referência técnica: [Microsoft Learn — Services and Redirected Drives](https://learn.microsoft.com/en-us/windows/win32/services/services-and-redirected-drives). UI/UX Pro Max orientou validação no próprio campo da configuração. Watermelon UI não estava disponível nesta sessão. As Web Interface Guidelines foram revisadas; o formulário usa rótulos, erro junto ao campo e resumo focável. Não foi possível usar Playwright: esta sessão não dispõe de navegador ou página CICA aberta.

Conforme instrução vigente, **não foram executados testes, build ou validação de escrita Windows nesta alteração**. A confirmação pelo agente, permissões na raiz e recuperação de indisponibilidade permanecem obrigatórias antes da liberação comercial.
## V-026 — Sincronização da raiz Windows a partir da CICA preparada

Data: 18/09/2026. A API v2 recebeu `configuration/next`, autenticada pelo agente e isolada por organização. Ela devolve somente a raiz do `DestinationProfile` do escritório do agente; quando o destino não for Windows, devolve vazio. O agente consulta essa configuração após o heartbeat, valida a raiz local, salva a cópia protegida por DPAPI e usa a alteração no próprio ciclo. UNC e unidades mapeadas são recusados nesta fase; a conta `LocalSystem` não deve depender de unidades mapeadas para acesso a arquivos.

Conforme instrução vigente, **não foram executados testes, build ou escrita Windows real nesta alteração**. Pareamento HTTPS, validação da raiz pelo agente instalado, permissões e recuperação de falha de rede seguem para a etapa de homologação final.
## V-027 — Sincronização nativa de extratos Domínio preparada

Data: 18/09/2026. O agente nativo passou a enviar extratos bancários pela rota v2, em páginas de até 500 registros e com chave externa composta do Domínio. A API aceita somente páginas limitadas, autenticadas e pertencentes ao escritório do agente, usando o espelho normalizado já existente. Não há SQL remoto nem escrita no banco Domínio.

Conforme instrução vigente, **não foram executados build, testes ou sincronização contra dados reais nesta alteração**. A prova de paginação, vínculo de lançamento, retomada e não duplicação permanece na homologação final.

## V-028 — Organização das dependências de produção

Data: 18/09/2026. Por D-87, as etapas 01–11 ficam limitadas a implementação, configuração sem segredos, testes locais/isolados e documentação. Deploy, domínio/HTTPS/DNS, credenciais externas de produção, chamadas reais, pilotos e homologação comercial foram centralizados na etapa 12. Nenhum deploy, serviço hospedado, chamada externa real ou validação foi executado neste registro.

## V-029 — Descoberta local Siescon

Data: 18/09/2026. A inspeção segura de metadados desta estação encontrou 26 drivers ODBC e 5 DSNs. Há drivers SQL Anywhere 16/17 nas arquiteturas 32 e 64 bits, mas nenhum DSN, driver ou diretório de instalação identificado como Siescon. Não houve conexão, listagem de bancos/tabelas, leitura de dados ou exposição de DSN/credencial. Resultado: o servidor/banco disponível em D-53 não está configurado localmente; versão, mecanismo autorizado e layout de Q-33 seguem necessários antes de programar um adaptador.

## V-030 — Base segura de exportação por destino

Data: 18/09/2026. Por D-88, `AccountingExport` passou a registrar o destino (`dominio` ou `siescon`) e o adaptador selecionado passou a ser explícito e versionado. O adaptador Domínio existente foi preservado. Siescon não possui adaptador registrado: a solicitação é recusada antes de consultar lançamentos ou gerar arquivo. A fonte Siescon também foi incluída no modelo de fontes, inicialmente sem configuração. Foram aprovados `36` testes em `tests/test_reconciliation_module.py` (27,19 s); `makemigrations --check --dry-run` não detectou alterações e Ruff passou nos arquivos alterados. Não houve conexão Siescon, arquivo de exportação Siescon, leitura externa ou homologação.
