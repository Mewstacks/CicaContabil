# CICA — validações e evidências

## V-104 — Banco de desenvolvimento cifrado com a chave de teste

Data: 22/09/2026. Ambiente: desenvolvimento local do responsável
(`config.settings.local`, `db.sqlite3` com massa fictícia). Nenhuma chamada externa,
cobrança ou deploy. Nenhum dado de cliente envolvido.

- **Sintoma:** `/app/` quebrava com `SuspiciousOperation: Encrypted field authentication
  failed`, causado por `Field encryption key 'test-v1' is unavailable`.
- **Causa:** a massa fictícia de `db.sqlite3` foi gravada por uma execução com
  `config.settings.test`, cuja chave fixa é `test-v1`, enquanto o ambiente de
  desenvolvimento usa `local-v1`. Levantamento por tabela: `hub_nfsedocument.original_xml`
  24 linhas, `hub_certificate.password`/`pfx_blob` 3 + 3, `accounts_totpdevice.secret` 2,
  `hub_officeprofile.cnpj` 1, `platform_signupintent.cnpj` 1 e
  `intelligence_intelligenceconnector.odbc_dsn` 1 — todas em `test-v1`; apenas uma linha
  de conector já estava em `local-v1`.
- **Correção local:** `test-v1` entrou no mapa `FIELD_ENCRYPTION_KEYS` do `.env` de
  desenvolvimento, com `local-v1` mantida como chave ativa: as leituras antigas voltam a
  funcionar e toda gravação nova continua na chave local. Nada foi apagado e nenhum
  registro foi reescrito. A chave `test-v1` é a constante pública de
  `src/config/settings/test.py` e serve apenas a dados fictícios; produção valida as
  chaves em `config/settings/production.py` e não lê este arquivo.
- **Correção de raiz:** `config/settings/local.py` passou a chamar
  `load_dotenv(..., override=True)`. Sem isso, o autoreload do Django reexecuta o servidor
  herdando o ambiente do primeiro boot, e qualquer valor já presente em `os.environ`
  sobrevive a toda edição do `.env` — foi o que escondeu a demonstração em V-103 e o que
  manteria esta chave ausente.
- **Verificação:** em processo novo com as settings de desenvolvimento,
  `FIELD_ENCRYPTION_KEYS` traz `local-v1` e `test-v1`, um `NfseDocument` decifra e `/app/`
  responde 200 com a pauta. Suíte completa: 798 aprovados, 2 ignorados, 11 subtestes.
  Ruff aprovado em `src` e `tests`.

Limites: a divergência de chave continua existindo no banco; consolidar tudo em
`local-v1` exigiria reescrever os registros fictícios, o que não foi feito. Nada aqui se
aplica a produção, que não compartilha banco, chave nem `.env` com o desenvolvimento.

## V-103 — Entrada da demonstração deixa de depender do slug configurado

Data: 22/09/2026. Ambiente: servidor de desenvolvimento local do responsável
(`127.0.0.1:8000`, `config.settings.local`, banco `db.sqlite3` com massa fictícia) e
suíte no `.venv`. Nenhuma chamada externa, cobrança ou deploy.

- **Sintoma:** mesmo com `.env` corrigido para `escritorio-demo`, a home e `/demo/`
  continuavam mostrando "A demonstração separada está sendo preparada".
- **Causa:** `load_dotenv` não sobrescreve variável já presente em `os.environ`
  (`override=False` é o padrão). O processo que subiu antes da correção fixou
  `DEMO_ORGANIZATION_SLUG=cica-demo` no ambiente, e o autoreload do Django reexecuta o
  servidor herdando esse ambiente — o código novo entrava (GET `/sair/` já respondia 200),
  as settings não. Só um encerramento do processo raiz limparia o valor.
- **Correção:** `demo_office()` passou a resolver a organização pelo que ela é. O slug
  configurado continua tendo prioridade quando existe e está ativo; quando não existe, a
  entrada usa a única organização ativa marcada `is_demo`. Com duas marcadas, nada é
  devolvido: escolher uma seria adivinhação, e a entrada continua fechada.
- **Verificação no servidor do responsável, sem reiniciar o processo:** `/demo/` passou a
  responder "Iniciar demonstração fictícia" e a home voltou com "Ver demonstração",
  "Explorar demo fictícia" e "Abrir demonstração fictícia".
- **Regressão:** `tests/test_seed_demo_django.py` ganhou
  `test_a_stale_configured_slug_still_finds_the_single_demonstration_office` e
  `test_two_demonstration_offices_close_the_entry_instead_of_guessing`. Suíte completa:
  798 aprovados, 2 ignorados, 11 subtestes. Ruff aprovado em `src` e `tests`.

Limite: os gates `DEMO_ENTRY_ENABLED` e `DEMO_SESSION_ISOLATION_READY` continuam
obrigatórios e não foram afrouxados; a entrada segue fechada em qualquer ambiente onde
eles estejam desligados.

## V-102 — Landing, ondas 5 a 7 e auditoria de interface da revisão total

Data: 22/09/2026. Ambiente: servidor isolado `scripts/qa_ui_server.py` (porta 8011,
`.tmp/ui-review`, conexões externas bloqueadas), navegador local em 1440 × 1000 e
375 × 812. Nenhuma credencial real digitada, nenhuma chamada externa, cobrança, arquivo
de cliente ou deploy.

**Site público e acesso**

- A seção "POR QUE CICA" era um parágrafo sobre o significado da sigla. Virou a seção de
  problema que o plano pede, com uma frase concreta e link para os módulos.
- "UMA PAUTA, CINCO FRENTES" anunciava cinco etapas e listava quatro. Passou a "UMA
  PAUTA, QUATRO ETAPAS".
- No celular, o cabeçalho escondia "Entrar": quem já é cliente não tinha caminho de login
  a partir da home. O link voltou, com 44 px de altura.
- Cinco links da landing tinham menos de 24 px de alvo (demo, módulos, termos,
  privacidade, entrar). Todos passaram a 24 px, e 44 px no celular.
- O consentimento do cadastro tinha nome acessível quebrado ("Li e aceito os , a e o .")
  porque os links ficavam dentro do rótulo. O rótulo virou texto contínuo e os três
  documentos ficaram em uma linha de links logo abaixo, todos alcançáveis por teclado.

**Onda 5 — inteligência e conhecimento**

- Radar: filtro de período (7, 30, 90 dias), coberto por
  `tests/test_reform_radar.py::test_radar_period_filter_hides_older_publications`. Cada
  linha passou a mostrar resumo, data de publicação e de coleta, e a marcar "Publicação
  coletada · sem interpretação fiscal validada".
- Copiloto: toda resposta recebeu a linha de limite ("Rascunho para conferência. A CICA
  não altera o Domínio"), e uma resposta sem evidência passa a ser marcada como "Sem
  fonte verificável" com aviso para conferir na área operacional.
- Central de aprendizado: o vazio virou explicação com saída ("Abrir Copiloto"), e cada
  candidato mostra resposta anterior, escopo do escritório, data e responsável pela
  revisão.

**Onda 6 — administração e console**

- O console Mewstack autenticado foi inspecionado visualmente pela primeira vez, em base
  fictícia isolada, criando a sessão de uma persona sintética direto no banco de revisão;
  nenhuma senha foi digitada e nenhum controle de MFA foi contornado (a tela
  `/platform/configuracoes/` continua exigindo segundo fator e não foi inspecionada).
- O painel do console passou a ser orientado a exceção: suspensos, ativações pendentes,
  integração Domínio com falha, egressão incerta e suporte ativo, cada um com link.
- O detalhe do escritório abria com o título do navegador apenas "CICA"; agora nomeia o
  escritório.
- Equipe: a demonstração listava as contas descartáveis de todos os outros visitantes.
  Passou a mostrar apenas as personas semeadas e quem está olhando, coberto por
  `tests/test_seed_demo_django.py::test_demo_team_page_hides_the_accounts_of_other_visitors`.
- Segredos do console usam `PasswordInput(render_value=False)` em todos os formulários:
  nenhum valor existente é reexibido.

**Onda 7 — tutorial guiado**

- Catálogo declarativo em `src/apps/hub/onboarding.py`: boas-vindas mais nove orientações
  por área, no máximo três passos cada, ancoradas ao nome da rota da tela principal —
  detalhe, confirmação e formulário iniciado nunca abrem orientação.
- Preferência versionada por pessoa em `hub.OnboardingProgress` (usuário, identificador,
  versão, data). Nenhum conteúdo fiscal, empresa ou resposta é gravado. A demonstração
  guarda o progresso apenas em `sessionStorage`.
- Diálogo HTML nativo com foco contido, Pular, Voltar, Fechar e "Como usar" permanente;
  ao fechar, o foco volta ao acionador. Sessão de suporte não abre orientação.
- Seis testes em `tests/test_onboarding_tour.py` cobrem primeira abertura, conclusão,
  nova versão, tela de detalhe, catálogo e recusa de identificador desconhecido.
- Limite: o envio sintético de teclas não chega à página neste ambiente, então a
  ativação por Enter/Espaço não foi confirmada por automação. A operação por teclado é
  garantida pela estrutura (botões nativos, diálogo nativo, foco movido para o passo) e
  foi verificada por ordem de foco; falta confirmação com teclado real e leitor de tela.

**Onda 8 — auditoria de interface**

- Vercel Web Interface Guidelines consultadas em 22/09/2026
  (<https://vercel.com/design/guidelines>). Correções aplicadas nas superfícies alteradas:
  alvos de 24 px (44 px no celular) em links de indicador, links de linha, links da fila
  de Triagem e caixas de seleção; rótulo de texto em ícone; `aria-live` nos contadores de
  seleção.
- Varredura final em 375 px: Visão geral, Empresas, Certificados, NFS-e, Revisões, Guias,
  Central Integra, Parcelamentos, Caixa DTE, Conciliação, Radar, Triagem, Caixas,
  Integrações, Primeiros passos, Equipe, Copiloto e Aprendizado — nenhum overflow
  horizontal. Console do navegador limpo em aba nova.
- Suíte completa no `.venv`: 796 aprovados, 2 ignorados, 11 subtestes. Ruff aprovado em
  `src` e `tests`. `makemigrations --check` sem alterações pendentes.

Limites: a onda 8 do plano previa também regressão por perfil, leitor de tela e tema
escuro comparados lado a lado, viewports 1024 e 768, e a tela de configuração do console
sob MFA — nada disso foi feito. Nenhuma integração real, homologação ou deploy.

## V-101 — Ondas 1 a 4 da revisão total de telas

Data: 22/09/2026. Ambiente: servidor isolado `scripts/qa_ui_server.py` (porta 8011,
`.tmp/ui-review`, conexões externas bloqueadas), navegador local em 1440 × 1000 e
375 × 812. Nenhuma credencial real, chamada externa, cobrança, arquivo de cliente ou
deploy.

**Onda 1 — fundação compartilhada**

- `.inline-alert` não tinha estilo algum: os 15 avisos em linha das telas de Guias,
  NFS-e, Parcelamentos, Conciliação e Radar apareciam como texto solto, e as variantes
  `-warning` e `-danger` eram indistinguíveis. Passaram a ter bloco, borda de acento e
  título colorido, sempre com a palavra do estado junto da cor. Contrastes calculados
  nos dois temas: azul 6,82:1 (claro) e 6,57:1 (escuro); âmbar 6,01 e 7,46; vermelho
  6,13 e 7,61 — todos acima de 4,5:1.
- Ações em lote passaram a aparecer só depois de existir seleção em Parcelamentos,
  coleta NFS-e, download NFS-e da demonstração e fila de movimentos da Conciliação
  (Guias já seguia esse contrato). Sem JavaScript, os botões continuam renderizados e o
  servidor segue validando a seleção.
- `USE_THOUSAND_SEPARATOR = True`: valores em pt-BR passaram a usar o ponto de milhar
  (`R$ 1.943,24`). Duas asserções de teste foram ajustadas para o formato correto.
- Texto repetido removido: os avisos de demonstração de Parcelamentos, Conciliação e
  Radar deixaram de repetir a faixa global e ficaram com a consequência específica do
  módulo; a fila da Triagem perdeu a linha "Consulte a etapa e a auditoria antes de
  agir".

**Onda 3 — núcleo diário**

- Revisões de NFS-e: a tabela misturava caso pendente e caso decidido quando o filtro
  era "Todas". Ganhou coluna **Situação** (aguardando decisão / decidida, com data e
  responsável) e a coluna de acumulador passou a rotular a origem — "Sugestão da CICA"
  ou "Decidido por pessoa". Os rótulos móveis (`::before`) foram corrigidos para a nova
  ordem das colunas.
- Empresas: filtros de **certificado** (válido, vence em 30 dias, sem certificado) e de
  **pendência** (com/sem revisão aberta), com as duas colunas correspondentes. Coberto
  por `tests/test_company_registry_django.py::CompanyRegistryTests::test_the_registry_filters_by_certificate_and_open_review`.
- Caixa DTE: a fila mostra a idade da mensagem ("recebida há 6 dias"). O Serpro não
  devolve prazo na listagem, então prazo continua ausente — idade é o que existe sem
  inventar dado.
- Visão geral: cada linha da fila de decisão mostra há quanto tempo o documento está
  parado.

**Onda 4 — processamento documental**

- Conciliação: o detalhe do movimento perdia filtro e página ao voltar (era um link
  fixo para `#movimentos`). Passou a usar `return_to` e `back_url`, como o resto do
  sistema. Verificado no navegador: `?movement_state=ambiguous&movement_page=1`
  sobrevive à ida e volta.
- Conciliação: os indicadores passaram a mostrar os dois lados com valor — importados do
  extrato e lançamentos no Domínio, além do valor pendente.
- Triagem: o painel de destino Windows mostra saúde do agente (conectado / sem sinal,
  último sinal) e prova da gravação (último caminho gravado e última falha), não só o
  caminho configurado. Coberto por
  `tests/test_triage_oauth_django.py::TriageMailboxOAuthTests::test_windows_destination_shows_agent_health_and_the_last_write`.

**Verificação**

- 20 telas autenticadas responderam 200; nenhuma das telas alteradas apresentou overflow
  horizontal em 375 px e o console ficou limpo em aba nova.
- Suíte completa no `.venv`: 788 aprovados, 2 ignorados, 11 subtestes. Ruff aprovado em
  `src` e `tests`.

Limites: ondas 5 a 8 continuam abertas (Radar/Copiloto/aprendizado, administração e
console Mewstack, tutorial guiado e auditoria final). Não houve inspeção de todos os
perfis, leitor de tela, tema escuro comparado lado a lado, viewports 1024/768, console
Mewstack autenticado, integração real nem homologação externa.

## V-100 — Ondas 0 a 2 da revisão total de telas: matriz, contrato de recusa e demonstração restaurada

Data: 22/09/2026. Ambiente: servidor de revisão isolado `scripts/qa_ui_server.py`
(porta 8011, banco e mídia em `.tmp/ui-review`, conexões externas bloqueadas) e
navegador local. Nenhuma credencial real, chamada externa, cobrança, arquivo de
cliente ou deploy.

- **Matriz (onda 0).** O URLconf foi inventariado: 89 rotas de interface — 49
  telas/estados e 40 ações ou downloads —, registradas em
  [`docs/planejamento/matriz-telas-2026-09-22.md`](docs/planejamento/matriz-telas-2026-09-22.md).
  Rotas de API REST, webhooks e agente ficam fora da matriz.
- **Varredura GET autenticada** (owner do escritório fictício) das 31 telas sem
  parâmetro: todas responderam 200 ou redirecionaram para o destino esperado; as
  três telas do console Mewstack responderam 403 por perfil, como previsto. As
  telas de detalhe com id semeado (empresa, guia, revisão, mensagem DTE, item de
  Triagem, movimento da conciliação, documentos legais) responderam 200.
- **Mobile 375 x 812:** 20 telas autenticadas percorridas sem overflow
  horizontal (`scrollWidth == clientWidth` em todas) e sem erro de console.
- **Demonstração (onda 2).** O ambiente local apontava para `cica-demo` enquanto
  a organização fictícia é `escritorio-demo`: o `.env` local foi corrigido e
  "Ver demonstração", "Explorar demo fictícia" e "Abrir demonstração fictícia"
  voltaram à home. A faixa de demonstração da área de trabalho ganhou saída
  explícita ("Sair da demonstração"), que encerra a sessão e descarta o progresso
  do visitante. Os 21 testes de isolamento da demonstração e os 2 da landing
  continuam passando.
- **Recusa que não é permissão (onda 1).** `refuse()` passou a aceitar
  `kind="unavailable"`: 24 recusas de estado ou validação (formato sem
  mapeamento, ação inválida, limite de lote, caso já decidido, bloqueios da
  demonstração) deixaram de ser apresentadas como "ACESSO RESTRITO / Sem
  permissão". O status HTTP continua 403.
- **Estado vazio (onda 1).** Criado o parcial único
  `hub/partials/empty_state.html` (título, uma frase, saída). Os dois estados
  vazios fora do contrato — filtro sem resultado em Empresas e em Parcelamentos —
  passaram a usá-lo e agora oferecem "Ver todas".
- **Ação quebrada corrigida.** `GET /sair/` respondia 405 sem corpo: o Django 5.0
  removeu logout por GET ([release notes](https://docs.djangoproject.com/en/5.0/releases/5.0/))
  e o projeto usa Django 6.0.8. `hub:logout` passou a ser `SignOutView`, que
  responde GET com a confirmação ("Sair da CICA?" ou "Sessão encerrada") e mantém
  o logout em POST. Regressão em `tests/test_cica_auth_flow.py`
  (`test_bookmarked_logout_url_answers_with_a_page_and_still_needs_a_post`).
- Suíte completa executada no interpretador do projeto (`.venv`): 781 aprovados,
  2 ignorados, 11 subtestes. Ruff aprovado nos arquivos alterados.

Limites: as ondas 3 a 8 do plano não foram executadas. Não houve inspeção de
todos os perfis, leitor de tela, teclado completo, tema escuro, viewports 1440 /
1024 / 768, console Mewstack autenticado, integração real nem homologação
externa. Nenhuma simulação local é registrada como homologação.

## V-099 — Demonstração isolada da Conciliação revisada no navegador

Data: 21/09/2026. Ambiente: banco SQLite temporário, migrado e semeado somente
com dados fictícios; navegador local. Não houve credencial real, upload,
processamento, consulta externa, cobrança, arquivo de cliente ou deploy.

- A entrada `/demo/` informou explicitamente que os dados são fictícios e que
  não há consulta externa ou cobrança. A sessão abriu a Visão geral do
  escritório demonstrativo e a Conciliação sem acessar o banco local de
  desenvolvimento.
- Em 1440 × 1000 e 390 × 844, a tela de Conciliação não teve overflow
  horizontal nem erros/avisos no console. O modal de importação expôs empresa,
  conta financeira, origem, período, identificação de lote e os limites de 20
  arquivos / 25 MiB, sem enviar arquivo.
- O servidor e a aba temporários foram encerrados ao fim da inspeção. A base e
  os artefatos fictícios foram movidos para a Lixeira de forma recuperável.

Limites: não substitui inspeção de todos os perfis, teclado/foco completo,
upload real, OCR, ERP, Serpro, Asaas ou homologação comercial.

## V-098 — PDF corrompido recusado antes da conciliação

Data: 21/09/2026. Ambiente: macOS local e banco de testes. Não houve arquivo
real de cliente, OCR, ERP, exportação, integração, custo ou deploy.

- A validação de PDF agora abre o documento e confirma o limite de 500 páginas
  antes de persistir a fonte. Um PDF malformado é recusado com mensagem clara e
  não cria lote ou processamento inválido; a ausência opcional de `pdfplumber`
  mantém o caminho de OCR local.
- **42 testes** focados de Conciliação passaram, com um skip de OCR local. Ruff
  e MyPy do serviço aprovaram a alteração. A regressão integral fechou com
  **784 testes aprovados, 3 skips e 11 subtestes** em 29,23 s.

Limites: a prova usa um PDF sintético corrompido; não homologa OCR, arquivos,
ERP ou exportação reais.

## V-097 — XLSX corrompido recusado antes da conciliação

Data: 21/09/2026. Ambiente: macOS local e banco de testes. Não houve arquivo
real de cliente, OCR, ERP, exportação, integração, custo ou deploy.

- A entrada XLSX agora abre a planilha antes de persistir a fonte. Uma extensão
  válida com assinatura `PK`, mas arquivo corrompido, retorna uma mensagem
  operacional clara e não cria fonte, lote ou processamento inválido.
- A prévia CSV lê somente as 51 linhas necessárias, em vez de materializar o
  arquivo inteiro para exibir suas primeiras linhas.
- **41 testes** focados de Conciliação passaram, com um skip de OCR local. Ruff
  e MyPy do serviço aprovaram a alteração. A regressão integral fechou com
  **783 testes aprovados, 3 skips e 11 subtestes** em 29,13 s.

Limites: a prova usa uma planilha sintética corrompida; não homologa layouts,
arquivos, OCR, ERP ou exportação reais.

## V-096 — Código operacional de Jornadas removido

Data: 21/09/2026. Ambiente: macOS local e banco de testes. Não houve oferta,
contrato, cobrança, convite, arquivo, integração, custo, deploy ou dado de
cliente.

- Em complemento à V-095 e conforme D-43, foram removidos os formulários,
  views e template operacionais órfãos de Jornadas. O enum, os modelos, tabelas
  e migrações históricos continuam preservados; não houve migração destrutiva.
- A busca de referências confirmou que não há rota, vínculo de navegação,
  formulário, view ou template ativo de Jornadas; o teste segue cobrindo as
  cinco rotas legadas como 404 em GET e POST e sua ausência do catálogo.
- **73 testes** focados de acesso, workspace e operação passaram. Ruff, MyPy
  global, Django e migrações aprovaram os **190 arquivos**. A regressão integral
  fechou com **781 testes aprovados, 3 skips e 11 subtestes** em 29,43 s.
- Após `git fetch origin --prune`, `HEAD` permanece **0 commits à frente e 0
  atrás de `origin/main`**; não houve pull, commit ou push. As 102 alterações
  locais existentes foram preservadas.

Limites: a prova é local; não comprova contrato comercial, uso histórico por
cliente, migração já aplicada em produção ou homologação de venda.

## V-095 — Jornadas removida do catálogo de produto

Data: 21/09/2026. Ambiente: macOS local e banco de testes. Não houve oferta,
contrato, cobrança, convite, arquivo, integração, custo, deploy ou dado de
cliente.

- A definição de módulo Jornadas foi retirada do catálogo usado pelo produto,
  alinhando-o à D-43. O enum, schema e migrações legados foram preservados para
  compatibilidade histórica, mas Jornadas não tem rota, navegação ou oferta.
- O teste confirmou que as cinco rotas legadas retornam 404 em GET e POST, que
  a navegação não as expõe e que o código não está no catálogo.
- **73 testes** focados de acesso, workspace e operação passaram. Ruff, MyPy
  global, Django e migrações aprovaram os **190 arquivos**. A regressão integral
  fechou com **781 testes aprovados, 3 skips e 11 subtestes** em 28,56 s.
- Após `git fetch origin --prune`, `HEAD` permanece **0 commits à frente e 0
  atrás de `origin/main`**; não houve pull, commit ou push. As 101 alterações
  locais existentes foram preservadas.

Limites: a prova é local; não comprova contrato comercial, uso histórico por
cliente, migração já aplicada em produção ou homologação de venda.

## V-094 — Caixa DTE mantém mensagens e histórico independentes

Data: 21/09/2026. Ambiente: macOS local e banco de testes. Não houve consulta
Serpro, credencial, consumo, cobrança, arquivo, dado de cliente ou deploy.

- A paginação da Caixa Postal agora preserva a página do histórico de consultas
  DTE, filtros e empresa selecionada; a paginação do histórico já preservava a
  página de mensagens. As duas listas podem ser percorridas sem se reiniciarem.
- O teste criou **31 resultados DTE e 26 mensagens** sintéticas, confirmou a
  segunda página de cada lista e ambos os vínculos de retorno, sem preparar ou
  enviar uma consulta.
- **10 testes** focados de DTE passaram. Ruff, MyPy global, Django e migrações
  aprovaram os **190 arquivos**. A regressão integral fechou com **781 testes
  aprovados, 3 skips e 11 subtestes** em 28,67 s.
- Após `git fetch origin --prune`, `HEAD` permanece **0 commits à frente e 0
  atrás de `origin/main`**; não houve pull, commit ou push. As 99 alterações
  locais existentes foram preservadas.

Limites: a prova é local e sintética; não comprova Serpro, certificado,
representação, consumo, cobrança, PostgreSQL em volume ou homologação.

## V-093 — Fila OFX sem perder o contexto da Conciliação

Data: 21/09/2026. Ambiente: macOS local e banco de testes. Não houve arquivo,
importação, confirmação, reprocessamento, exportação, ERP, OCR, custo, deploy
ou dado de cliente.

- A paginação da fila OFX × Domínio agora mantém as páginas de Processamentos,
  Movimentos e Exportações, além dos filtros da própria fila. Avançar ou voltar
  na fila não reinicia as outras três áreas da Conciliação.
- O teste percorreu a terceira página de 101 correspondências sintéticas com
  as três páginas independentes selecionadas e confirmou o vínculo de retorno,
  sem criar ou alterar uma conciliação.
- **39 testes** focados de Conciliação passaram, com **1 skip** de OCR local.
  Ruff, MyPy global, Django e migrações aprovaram os **190 arquivos**. A
  regressão integral fechou com **781 testes aprovados, 3 skips e 11 subtestes**
  em 28,11 s.
- Após `git fetch origin --prune`, `HEAD` permanece **0 commits à frente e 0
  atrás de `origin/main`**; não houve pull, commit ou push. As 99 alterações
  locais existentes foram preservadas.

Limites: a prova é local e sintética; não comprova arquivo, OCR, layout real,
ERP, PostgreSQL em volume, exportação ou homologação operacional.

## V-092 — Páginas independentes na carteira de Conciliação

Data: 21/09/2026. Ambiente: macOS local e banco de testes. Não houve arquivo,
importação, reprocessamento, confirmação, exportação, ERP, OCR, custo, deploy
ou dado de cliente.

- A paginação dos movimentos normalizados agora conserva as páginas já abertas
  de Processamentos e Exportações, bem como filtros e contexto da Conciliação.
  Trocar a carteira de movimentos não desloca mais as outras duas trilhas.
- O teste criou **21 processamentos, 21 exportações e 51 movimentos** sintéticos
  e confirmou a segunda página de cada área e o vínculo de retorno do movimento,
  sem executar nenhuma ação operacional.
- **39 testes** focados de Conciliação passaram, com **1 skip** de OCR local.
  Ruff, MyPy global, Django e migrações aprovaram os **190 arquivos**. A
  regressão integral fechou com **781 testes aprovados, 3 skips e 11 subtestes**
  em 28,33 s.
- Após `git fetch origin --prune`, `HEAD` permanece **0 commits à frente e 0
  atrás de `origin/main`**; não houve pull, commit ou push. As 99 alterações
  locais existentes foram preservadas.

Limites: a prova é local e sintética; não comprova arquivo, OCR, layout real,
ERP, PostgreSQL em volume, exportação ou homologação operacional.

## V-091 — Histórico da Triagem sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local e banco de testes. Não houve caixa de
e-mail, arquivo, antimalware, OCR, destino Windows, integração, custo, deploy
ou dado de cliente.

- O detalhe de um arquivo em Triagem agora percorre a trilha persistida de
  eventos em páginas de 20, informa o total e preserva a ordem cronológica e
  os parâmetros de retorno; não carrega a trilha inteira para exibi-la.
- O teste criou **21 eventos** sintéticos e confirmou as duas páginas (20/1),
  o total, as evidências inicial e final e os vínculos de ida e volta, sem
  mudar o estado do item, aprovar arquivamento ou produzir arquivo.
- A demonstração permanece isolada por sessão e não é usada como prova visual
  do histórico persistido em volume. A inspeção autenticada no navegador não
  foi automatizada para não inserir credenciais.
- **57 testes** focados do espaço de trabalho passaram; Ruff, MyPy global,
  Django e migrações aprovaram os **190 arquivos**. A regressão integral fechou
  com **781 testes aprovados, 3 skips e 11 subtestes** em 28,86 s.
- Após `git fetch origin --prune`, `HEAD` permanece **0 commits à frente e 0
  atrás de `origin/main`**; não houve pull, commit ou push. As 99 alterações
  locais existentes foram preservadas.

Limites: a prova é local e sintética; não comprova caixa, scanner, OCR,
classificação, arquivo, agente Windows, PostgreSQL em volume ou homologação
operacional.

## V-090 — Candidatos de conciliação sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporário e demonstração
fictícia. Não houve arquivo real, importação, exportação, ERP, OCR, integração,
custo, deploy ou dado de cliente.

- O detalhe do movimento agora percorre todos os lançamentos candidatos no
  recorte já existente de seis dias: mostra 25 por página, informa o total de
  lançamentos avaliados e conserva a confirmação humana com evidência.
- O teste criou **51 candidatos** sintéticos, confirmou as três páginas
  (25/25/1) e verificou que todos apareceram; não confirmou conciliação nem
  gerou lançamento, arquivo ou exportação.
- A demonstração temporária percorreu a segunda página e a superfície de 390
  px sem overflow horizontal ou erro de console. Servidor, navegador e banco
  temporário foram encerrados; o banco foi movido à Lixeira de forma
  recuperável.
- **39 testes** de Conciliação passaram, com **1 skip** de OCR local; Ruff,
  MyPy global, Django e migrações aprovaram os **190 arquivos**. A regressão
  integral fechou com **780 testes aprovados, 3 skips e 11 subtestes** em
  29,92 s.
- Após `git fetch origin --prune`, `HEAD` permanece **0 commits à frente e 0
  atrás de `origin/main`**; não houve pull, commit ou push.

Limites: a prova é local e sintética; não comprova arquivo, OCR, ERP, Domínio,
Siescon, importação no destino, PostgreSQL em volume ou homologação operacional.

## V-089 — Acumulador NFS-e validado no catálogo da empresa

Data: 21/09/2026. Ambiente: macOS local e banco de testes. Não houve coleta,
certificado, ADN, lançamento, integração, custo, deploy ou dado de cliente.

- A decisão humana de uma revisão NFS-e agora só aceita acumulador presente em
  regra ativa e vigente ou no histórico observado da mesma empresa; código
  inexistente ou de outra empresa é recusado. A tela sugere o catálogo local.
- **95 testes** de espaço de trabalho, fiscal e IA passaram; Ruff e MyPy global
  aprovaram os **190 arquivos** de código. A regressão integral fechou com
  **779 testes aprovados, 3 skips e 11 subtestes** em 28,73 s; Django e
  migrações não apontaram drift.
- A demonstração fictícia confirmou em desktop e em 390 px o campo da decisão,
  sua lista nativa de acumuladores e a ausência de overflow horizontal ou erro
  de console. A sessão e seu banco temporário foram encerrados; o banco foi
  movido à Lixeira de forma recuperável.
- Após `git fetch origin --prune`, `HEAD` permanece **0 commits à frente e 0
  atrás de `origin/main`**; não houve pull, commit ou push.

Limites: a prova é local e sintética; não comprova catálogo Domínio, regra
fiscal, ADN, documento real ou homologação. A medida não cria regra nem
lançamento.

## V-088 — Atenção de egressão sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local e banco de testes, com auditorias de
egressão exclusivamente sintéticas. Não houve pergunta enviada, chamada Claude,
liberação ou liquidação de consumo, credencial externa, custo, deploy ou dado de
cliente.

- O detalhe do escritório no console da plataforma deixou de limitar as
  tentativas Claude que exigem verificação às 20 mais recentes: agora pagina 20
  itens, informa o total e mantém os parâmetros correntes do detalhe.
- O teste criou 21 auditorias incertas sintéticas no mesmo escritório, alcançou
  a segunda página e preservou o protocolo da ocorrência mais antiga sem
  repetir chamada, liberar reserva ou alterar consumo.
- **57 testes** de detalhe de escritório, IA e isolamento passaram; Ruff e MyPy
  global aprovaram os **190 arquivos** de código.
- A regressão integral fechou com **778 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,40 s; Django e migrações não apontaram erro ou
  drift.
- Após `git fetch origin --prune`, `HEAD` permaneceu **0 commits à frente e 0
  atrás de `origin/main`**. As 96 alterações locais existentes foram
  preservadas antes do registro desta entrega.

Limites: a evidência usa somente auditorias sintéticas locais; não comprova
provedor Claude, resposta real, confirmação externa, custo, concorrência
PostgreSQL ou homologação operacional. A inspeção visual autenticada do console
não foi automatizada porque exigiria inserir uma credencial no navegador; nenhum
ambiente externo foi acessado.

## V-087 — Fechamentos adiados sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local e banco de testes, com ocorrências de
fechamento exclusivamente sintéticas. Não houve fechamento, reserva, cobrança,
contato Asaas, credencial externa, custo, deploy ou dado de cliente.

- O console da plataforma deixou de limitar a lista de fechamentos ainda
  adiados às 30 ocorrências mais antigas: agora pagina 30 itens, informa o
  total e conserva os parâmetros correntes da configuração.
- O teste criou 31 escritórios e ocorrências sintéticas, alcançou a segunda
  página e confirmou os vínculos de retorno sem executar operação de
  faturamento, mudar contrato, preço ou status.
- **65 testes** de configuração, console e cobrança passaram, com **1 skip**
  de concorrência em PostgreSQL; Ruff e MyPy global aprovaram os **190
  arquivos** de código.
- A regressão integral fechou com **777 testes aprovados, 3 skips e 11
  subtestes aprovados** em 37,81 s; Django e migrações não apontaram erro ou
  drift.
- Após `git fetch origin --prune`, `HEAD` permaneceu **0 commits à frente e 0
  atrás de `origin/main`**. As 96 alterações locais existentes foram
  preservadas antes do registro desta entrega.

Limites: a evidência cobre somente ocorrências sintéticas locais; não comprova
fechamento mensal, reserva em concorrência PostgreSQL, Pix, boleto, cartão,
Asaas, contrato comercial ou homologação. A inspeção visual autenticada do
console não foi automatizada porque ela exigiria inserir uma credencial no
navegador; nenhum ambiente externo foi acessado.

## V-086 — Histórico do Copiloto sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporário e demonstração
fictícia. Não houve pergunta enviada, chamada de IA, curadoria, treinamento,
upload, credencial externa, custo, deploy ou dado de cliente.

- O Copiloto deixou de exibir somente as 12 conversas abertas mais recentes:
  agora pagina 12 registros, informa o total e preserva tanto a conversa ativa
  quanto a página do histórico ao navegar.
- O teste com 13 conversas sintéticas confirmou a segunda página, a conversa
  mais antiga selecionada e os vínculos de página, sem criar mensagem nem
  acionar runtime, fallback ou egressão.
- A demonstração local confirmou, em 390 px, a superfície móvel do Copiloto
  sem overflow horizontal ou erro de console. Como ela não contém conversas,
  não foi usada como prova visual de paginação em volume.
- **49 testes** de IA passaram, com **3 subtestes** aprovados; Ruff e MyPy
  global aprovaram os **190 arquivos** de código.
- A regressão integral fechou com **776 testes aprovados, 3 skips e 11
  subtestes aprovados** em 38,46 s; Django e migrações não apontaram erro ou
  drift.
- Após `git fetch origin --prune`, `HEAD` permaneceu **0 commits à frente e 0
  atrás de `origin/main`**. As 94 alterações locais existentes foram
  preservadas antes do registro desta entrega.

Limites: a evidência usa apenas conversas sintéticas locais; não comprova
chamada Claude, runtime local definitivo, curadoria, treinamento, dados reais,
PostgreSQL, latência ou homologação operacional. O banco, servidor, navegador e
diretórios temporários de QA foram encerrados; os artefatos temporários foram
movidos à Lixeira de forma recuperável.

## V-085 — Trilhas de Conciliação sem cortes silenciosos

Data: 21/09/2026. Ambiente: macOS local, SQLite temporário e demonstração
fictícia. Não houve importação, reprocessamento, geração, download ou
confirmação de arquivo, conexão a ERP, custo, deploy ou dado de cliente.

- As trilhas de processamentos e de exportações da Conciliação deixaram de
  cortar os 12 e 8 registros mais recentes: cada uma agora pagina 20 itens,
  informa seu total e mantém os parâmetros e a página da outra trilha.
- O teste criou 21 execuções e 21 exportações sintéticas, chegou à página 2 de
  cada histórico e confirmou que trocar uma página não desloca a outra nem
  executa qualquer ação operacional.
- A demonstração local confirmou, em 390 px, as áreas de Processamentos e
  Exportações sem overflow horizontal ou erro de console. Ela não representa
  21 registros nas trilhas e não foi usada como prova visual de volume.
- **93 testes** de Conciliação e espaço de trabalho passaram, com **1 skip** de
  OCR local, em 21,74 s; Ruff e MyPy global aprovaram os **190 arquivos** de
  código.
- A regressão integral fechou com **775 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,25 s; Django e migrações não apontaram erro ou
  drift.
- Após `git fetch origin --prune`, `HEAD` permaneceu **0 commits à frente e 0
  atrás de `origin/main`**. As 91 alterações locais foram preservadas antes do
  registro desta entrega.

Limites: a evidência usa somente execuções e exportações sintéticas locais; não
comprova arquivos reais, OFX, OCR, Domínio, Siescon, importação no destino,
PostgreSQL, latência ou homologação operacional. O banco, servidor, navegador e
diretório temporários de QA foram encerrados; os artefatos temporários foram
movidos à Lixeira de forma recuperável.

## V-084 — Histórico de importações sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporário e demonstração
fictícia. Não houve envio, confirmação ou processamento de arquivo, conexão
Domínio, credencial externa, custo, deploy ou dado de cliente.

- A seção de importações do onboarding deixou de exibir somente os oito lotes
  mais recentes: agora pagina 20 registros, informa o total e preserva fonte e
  prévia selecionadas na navegação.
- O teste com 21 lotes sintéticos alcançou a página 2, conservou a fonte e
  conferiu total, vínculos e página sem alterar lote ou dados importados.
- A demonstração local contém zero importações; ela confirmou somente a seção
  vazia em 390 px, sem overflow horizontal ou erros de console, e não foi usada
  como prova visual da paginação em volume.
- **57 testes** de espaço de trabalho e backup passaram em 19,20 s; Ruff e MyPy
  global aprovaram os **190 arquivos** de código.
- A regressão integral fechou com **774 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,59 s; Django e migrações não apontaram erro ou
  drift.
- Após `git fetch origin --prune`, `HEAD` permaneceu **0 commits à frente e 0
  atrás de `origin/main`**. As 90 alterações locais foram preservadas antes do
  registro desta entrega.

Limites: a evidência usa apenas lotes sintéticos locais; não comprova upload,
backup `.dom`, chave, extração, Domínio, agente Windows, volume em PostgreSQL,
latência ou homologação operacional. O banco, servidor, navegador e diretório
temporários de QA foram encerrados; os artefatos temporários foram movidos à
Lixeira de forma recuperável.

## V-083 — Histórico DTE sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporário e demonstração
fictícia. Não houve preparação de consulta, acesso ao Serpro, certificado,
credencial externa, consumo, custo, deploy ou dado de cliente.

- O histórico de resultados DTE deixou de cortar os 30 registros mais recentes:
  agora pagina 30 itens, informa o total e conserva a página atual da fila de
  mensagens, filtros e empresa na navegação própria.
- O teste com 31 itens e execuções DTE sintéticos alcançou a página 2, manteve a
  fila de mensagens na página 1 e conferiu total, navegação e parâmetros sem
  alterar resultado ou autorização.
- Na demonstração local, a tela DTE vazia e a área de histórico renderizaram em
  390 px sem overflow horizontal ou erros de console. Como ela contém zero
  resultados preparados, não foi usada como prova visual de paginação em volume.
- **75 testes** de DTE e espaço de trabalho passaram em 14,80 s; Ruff e MyPy
  global aprovaram os **190 arquivos** de código.
- A regressão integral fechou com **773 testes aprovados, 3 skips e 11
  subtestes aprovados** em 36,37 s; Django e migrações não apontaram erro ou
  drift.
- Após `git fetch origin --prune`, `HEAD` permaneceu **0 commits à frente e 0
  atrás de `origin/main`**. As 89 alterações locais foram preservadas antes do
  registro desta entrega.

Limites: a evidência usa apenas estado DTE sintético e local; não comprova
consulta, ciência, certificado, Serpro, consumo, retorno de produção,
PostgreSQL, latência ou homologação fiscal. O banco, servidor, navegador e
diretório temporários de QA foram encerrados; os artefatos temporários foram
movidos à Lixeira de forma recuperável.

## V-082 — Histórico de cobrança manual sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local e banco de testes, com faturas
exclusivamente sintéticas. Não houve criação de cobrança, Asaas, chave,
cartão, Pix, boleto, credencial externa, custo, deploy ou dado de cliente.

- O console da plataforma deixou de limitar o histórico às 12 faturas mais
  recentes: ele agora pagina 12 registros, informa o total e mantém os dados
  restritos ao escritório aberto.
- O teste com 25 faturas sintéticas alcançou a página 3, preservou o vínculo de
  retorno e conferiu o total sem alterar fatura, contrato ou status.
- **41 testes** de console, cobrança e contratos passaram em 12,67 s; Ruff e
  MyPy global aprovaram os **190 arquivos** de código.
- A regressão integral fechou com **772 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,26 s; Django e migrações não apontaram erro ou
  drift.
- Após `git fetch origin --prune`, `HEAD` permaneceu **0 commits à frente e 0
  atrás de `origin/main`**. As 87 alterações locais foram preservadas.

Limites: a evidência cobre registros locais sintéticos e não comprova cobrança
real, Asaas, Pix, boleto, cartão, estorno, concorrência em PostgreSQL ou
homologação comercial. A inspeção visual autenticada do console não foi
automatizada porque ela exigiria inserir uma credencial; isso permanece aberto
na etapa 11.

## V-081 — Radar da Reforma sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporário e navegador interno,
com alertas exclusivamente fictícios. Não houve coleta de fontes, navegação a
URLs oficiais, credencial, custo, deploy ou dado de cliente.

- A consulta local do Radar deixou de exibir apenas os primeiros 80 alertas:
  agora pagina 50 registros, preservando termo, fonte e tema, e mantém o total
  correspondente ao filtro.
- O teste criou 101 alertas sintéticos, alcançou a página 3 e verificou os
  totais e o vínculo de retorno com os três filtros preservados.
- A demonstração deliberadamente contém somente três exemplos; sua busca por
  IBS exibiu o aviso de conteúdo fictício e um resultado, sem erro de console
  ou overflow horizontal em 390 px. Ela não foi usada para alegar inspeção
  visual da paginação em volume.
- **77 testes** de espaço de trabalho, Radar e demonstração passaram em 20,62
  s; Ruff e MyPy global aprovaram os **190 arquivos** de código.
- A regressão integral fechou com **771 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,73 s; Django e migrações não apontaram erro ou
  drift.
- Após `git fetch origin --prune`, `HEAD` permaneceu **0 commits à frente e 0
  atrás de `origin/main`**. As 85 alterações locais foram preservadas.

Limites: a prova contém somente alertas sintéticos e filtros locais; não
comprova fonte oficial, atualização, classificação, disponibilidade, volume em
PostgreSQL, latência ou homologação do Radar. O banco, servidor, navegador e
diretório temporários de QA foram encerrados; o diretório foi movido para a
Lixeira de forma recuperável.

## V-080 — Auditoria de conciliação sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporário e navegador interno,
com eventos de auditoria exclusivamente fictícios. Não houve OFX, Domínio,
ERP, fonte externa, credencial, custo, deploy ou dado de cliente.

- A trilha de auditoria da conciliação deixou de limitar a consulta aos
  primeiros 200 eventos: ela agora pagina 100 registros, mantém a ação filtrada
  na navegação e informa o total que corresponde ao filtro.
- O teste criou 201 eventos sintéticos, alcançou a página 3 e confirmou tanto
  o total quanto os vínculos que preservam a ação ao retornar de página.
- A inspeção da demonstração temporária abriu a página 3 de 3 com o filtro
  aplicado, voltou à página 2 e manteve os 201 eventos; não houve erro de
  console ou overflow horizontal em 390 px.
- **90 testes** de conciliação e espaço de trabalho passaram em 15,60 s; Ruff
  e MyPy global aprovaram os **190 arquivos** de código.
- A regressão integral fechou com **770 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,37 s; Django e migrações não apontaram erro ou
  drift.
- Após `git fetch origin --prune`, `HEAD` permaneceu **0 commits à frente e 0
  atrás de `origin/main`**. As 84 alterações locais foram preservadas.

Limites: a prova contém somente auditoria sintética; não comprova importação
OFX, OCR, fonte Domínio, ERP, volume em PostgreSQL, latência ou homologação de
exportação. O banco, servidor, navegador e diretório temporários de QA foram
encerrados; o diretório foi movido para a Lixeira de forma recuperável.

## V-079 — Ficha da empresa sem cortes de histórico

Data: 21/09/2026. Ambiente: macOS local, SQLite temporário e navegador interno,
com NFS-e, revisões e mensagens DTE exclusivamente fictícias. Não houve ADN,
Serpro, certificado real, credencial externa, custo, deploy ou dado de cliente.

- A ficha da empresa passou a paginar independentemente os documentos NFS-e,
  revisões abertas e mensagens DTE, todos em páginas de 20 itens; parâmetros de
  retorno e páginas das demais seções permanecem intactos.
- O teste criou 21 itens em cada histórico, chegou à página 2 e verificou os
  totais e os vínculos de navegação entre as seções.
- A inspeção do escritório-demo temporário abriu a página 2 das três seções,
  retornou a DTE à página 1 sem perder as demais, não registrou erro de console
  e não apresentou overflow horizontal em 390 px.
- **72 testes** de registro de empresas e espaço de trabalho passaram em 14,94
  s; Ruff e MyPy global aprovaram os **190 arquivos** de código.
- A regressão integral fechou com **769 testes aprovados, 3 skips e 11
  subtestes aprovados** em 29,38 s.
- Após `git fetch origin --prune`, `HEAD` permaneceu **0 commits à frente e 0
  atrás de `origin/main`**. As 83 alterações locais foram preservadas.

Limites: a prova usa apenas estado sintético; não comprova coleta ADN, acesso
DTE/Serpro, certificados, protocolos, representação, PostgreSQL, latência ou
homologação fiscal. O banco, servidor, navegador e diretório temporários de QA
foram encerrados; o diretório foi movido para a Lixeira de forma recuperável.

## V-078 — Cobertura de certificados paginada sem ocultar empresas

Data: 21/09/2026. Ambiente: macOS local, SQLite temporário e navegador interno,
com empresas e identificadores exclusivamente fictícios. Não houve certificado
real, ADN, credencial externa, custo, deploy ou dado de cliente.

- A cobertura de empresas sem certificado A1 válido deixou de cortar após 20
  registros: a lista e o seletor da demonstração agora seguem páginas próprias,
  separadas da carteira de certificados.
- O teste criou 21 empresas sem A1, abriu a página 2 e comprovou a preservação
  de busca e situação na volta para a página 1.
- A inspeção visual no escritório-demo temporário alcançou a página 2 de 2 de
  uma cobertura com 25 empresas, retornou à página 1, não registrou erro de
  console e não apresentou overflow horizontal em 390 px.
- **70 testes** de espaço de trabalho e fiscal passaram em 16,66 s; Ruff e
  MyPy global aprovaram os **190 arquivos** de código.
- A regressão integral fechou com **768 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,57 s.
- Após `git fetch origin --prune`, `HEAD` permaneceu **0 commits à frente e 0
  atrás de `origin/main`**. As 81 alterações locais foram preservadas.

Limites: a prova usa somente estado sintético; não comprova validade/custódia
de A1, coleta ADN, NSU, mTLS, catálogo de acumuladores, PostgreSQL, latência ou
homologação fiscal. O banco, servidor, navegador e diretório temporários de QA
foram encerrados; o diretório foi movido para a Lixeira de forma recuperável.

## V-077 — Histórico de Parcelamentos recuperável por página

Data: 21/09/2026. Ambiente: macOS local, banco SQLite temporário e navegador
interno, com operações PARCSN exclusivamente fictícias. Não houve Serpro,
credencial externa, custo, deploy ou dado de cliente.

- O histórico da empresa em Parcelamentos deixou de cortar silenciosamente após
  20 operações: ele agora pagina o histórico sem interferir na paginação da
  carteira.
- A inspeção visual criou 21 operações sintéticas de resultado incerto, abriu a
  página 2 e retornou à página 1 preservando a empresa em foco, sem erro de
  console. O aviso de recuperação permaneceu visível em cada tentativa.
- **77 testes** de Parcelamentos, espaço de trabalho e Guias passaram em 16,17
  s; Ruff e MyPy global aprovaram os **190 arquivos** de código.
- A regressão integral fechou com **767 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,64 s; Django e migrações não apontaram erro ou
  drift.
- A consulta remota após `git fetch origin --prune` confirmou **0 commits à
  frente e 0 atrás de `origin/main`**. O diretório local permanece com 80
  alterações de trabalho, preservadas nesta verificação.

Limites: a prova usa apenas estado sintético; não comprova PARCSN/Serpro,
protocolos reais, consumo, representação, volume em PostgreSQL, latência ou
homologação fiscal. O banco e o servidor temporários foram encerrados, e o
diretório de QA foi movido para a Lixeira de forma recuperável.

## V-076 — Fila de conciliação paginada sem ocultar evidências

Data: 21/09/2026. Ambiente: macOS local e banco de testes. Não houve OFX de
cliente, Domínio, OCR, fonte externa, credencial, custo ou deploy.

- A fila OFX × Domínio deixou de cortar silenciosamente nos primeiros 100
  resultados: ela agora pagina 50 linhas, preservando busca e situação.
- A busca de candidatos e a composição das evidências continuam restritas aos
  itens visíveis na página, sem ampliar consultas desnecessárias à carteira.
- O teste de integração renderizou 101 correspondências sem par, alcançou a
  página 3 e confirmou o retorno à página 2 com filtros preservados.
- **95 testes** de conciliação, espaço de trabalho e Parcelamentos passaram,
  com um skip esperado de OCR em português; Ruff e MyPy global aprovaram os
  **190 arquivos** de código.
- A regressão integral fechou com **766 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,14 s; Django e migrações não apontaram erro ou
  drift.
- `git fetch origin --prune` e `HEAD...origin/main` retornaram **0/0**: não há
  commit do GitHub ausente localmente nem commit local à frente.

Limites: a demonstração contém deliberadamente apenas duas conciliações e não
permite provar visualmente a terceira página sem uma sessão não demonstrativa.
O teste autenticado de integração cobre a renderização dessa página; isto não
comprova volume em PostgreSQL, importação OFX real, OCR, fonte Domínio ou
homologação de exportação. O checkout preserva 80 alterações locais ainda não
commitadas.

## V-075 — Carteira de Parcelamentos paginada por lote autorizado

Data: 21/09/2026. Ambiente: macOS local, banco SQLite temporário e navegador
interno, com empresas exclusivamente fictícias. Não houve Serpro, PARCSN real,
Domínio, credencial externa, custo, deploy ou dado de cliente.

- A carteira de Parcelamentos deixou de esconder empresas após os primeiros 100
  registros: ela agora pagina 30 empresas por página e preserva a pesquisa.
- O limite de 30 por página foi escolhido para coincidir com o máximo do lote
  já imposto pelo backend; portanto, “Selecionar todas desta página” não monta
  uma solicitação inválida por excesso de empresas.
- A inspeção com 101 empresas sintéticas alcançou a página 4 de 4, exibiu o
  último registro e retornou à página 3 mantendo a busca, sem erro de console.
- **76 testes** de Parcelamentos, espaço de trabalho e Guias passaram em 15,11
  s; Ruff e MyPy global aprovaram, este último nos **190 arquivos** de código.
- A regressão integral fechou com **765 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,37 s; Django e migrações não apontaram erro ou
  drift.
- `git fetch origin --prune` e `HEAD...origin/main` retornaram **0/0**: não há
  commit do GitHub ausente localmente nem commit local à frente.

Limites: a prova usa empresas e sessão sintéticas; não comprova PARCSN/Serpro,
protocolos, representação, consumo real, volume em PostgreSQL, latência ou
homologação fiscal. O banco e o servidor temporários foram encerrados, e o
diretório de QA foi movido para a Lixeira de forma recuperável. O checkout
preserva 78 alterações locais ainda não commitadas.

## V-074 — Carteira de guias sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, banco SQLite temporário e navegador
interno, com guias exclusivamente fictícias. Não houve Serpro, DCTFWeb real,
Domínio, credencial externa, custo, deploy ou dado de cliente.

- A lista de Guias e DCTFWeb agora pagina resultados acima de 100 itens e
  preserva busca, situação e vencimento nos links de navegação.
- O teste de interface criou 101 guias sintéticas: a página 2 de 2 exibiu a
  guia final, e o retorno à página 1 manteve os filtros. Não houve erro no
  console do navegador.
- **88 testes** de guias, espaço de trabalho e demonstração passaram em 21,08
  s; Ruff e MyPy global aprovaram, este último nos **190 arquivos** de código.
- A regressão integral fechou com **764 testes aprovados, 3 skips e 11
  subtestes aprovados** em 29,19 s; Django e migrações não apontaram erro ou
  drift.
- `git fetch origin --prune` e `HEAD...origin/main` retornaram **0/0**: não há
  commit do GitHub ausente localmente nem commit local à frente.

Limites: a prova usa dados e sessão sintéticos; não comprova DCTFWeb/Serpro,
protocolos, representação, catálogo real de acumuladores, volume em PostgreSQL,
latência ou homologação fiscal. O banco e o servidor temporários foram
encerrados, e o diretório de QA foi movido para a Lixeira de forma recuperável.
O checkout preserva 76 alterações locais ainda não commitadas.

## V-073 — Revisão NFS-e completa e carteira paginada localmente

Data: 21/09/2026. Ambiente: macOS local, banco SQLite temporário e navegador
interno, com documentos exclusivamente fictícios. Não houve ADN, certificado,
Serpro, Domínio, credencial externa, custo, deploy ou dado de cliente.

- O detalhe de revisão passou a exibir número, emissão/competência, código e
  descrição do serviço, valor em moeda e referência pseudonimizada da
  contraparte, além de sugestão, confiança, XML e decisão humana já existentes.
- A semente de demonstração agora preenche número e descrição explicitamente
  fictícios, sem representar coleta fiscal real.
- A carteira NFS-e deixou de cortar silenciosamente nos primeiros 100 itens:
  paginação preserva a busca e expõe a quantidade total. A inspeção no navegador
  alcançou a página 2 de 2 e retornou à página 1 com o filtro preservado. O
  detalhe de revisão não teve overflow em 390 px, nem houve erro de console.
- **79 testes** fiscais/demonstração passaram em 21,63 s; Ruff e MyPy global
  aprovaram, este último nos **190 arquivos** de código-fonte.
- A regressão integral fechou com **763 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,04 s; Django e migrações não apontaram erro ou
  drift.
- `git fetch origin --prune` e `HEAD...origin/main` retornaram **0/0**: não há
  commit do GitHub ausente localmente nem commit local à frente.

Limites: a prova usa XML e sessão sintéticos; não comprova coleta ADN,
certificados, cobertura de fonte, catálogo real de acumuladores, volume em
PostgreSQL, latência ou homologação fiscal. O banco e o servidor temporários
foram encerrados, e o diretório de QA foi movido para a Lixeira. O checkout
preserva 74 alterações locais ainda não commitadas.

## V-072 — Runtime privado priorizado e fallback externo negado sem opt-in

Data: 21/09/2026. Ambiente: macOS local, banco de testes e respostas HTTP
simuladas; não houve runtime de modelo, chamada Claude, credencial real, custo,
deploy ou dado de cliente.

- O contrato OpenAI-compatível do runtime privado recebeu pergunta e evidência
  compacta; a resposta simulada foi usada pelo Copiloto.
- Mesmo com fallback externo configurado e aprovado no cenário de teste, a
  resposta local não chamou o provedor nem criou auditoria de egressão.
- A suíte também mantém a prova complementar: sem opt-in do escritório, o
  fallback é negado, não chama o provedor e registra a negação para auditoria.
- `pytest` focado aprovou **73 testes e 3 subtestes** em 15,17 s; Ruff e MyPy
  global aprovaram, este último nos **190 arquivos** de código-fonte.
- `git fetch origin --prune` e `HEAD...origin/main` retornaram **0/0**: não há
  commit do GitHub ausente localmente nem commit local à frente.

Limites: a resposta HTTP foi simulada; não mede modelo, GPU, rede privada,
latência, credenciais, custo, autorização real de egressão ou homologação. O
checkout preserva 70 alterações locais ainda não commitadas.

## V-071 — Módulos fictícios e Copiloto inspecionados ponta a ponta

Data: 21/09/2026. Ambiente: navegador interno e base SQLite temporária com
semente fictícia. Não houve API Claude, Serpro, e-mail, Domínio, arquivo ou
dado de cliente.

- Guias/DCTFWeb, Caixa DTE, Parcelamentos, Conciliação, Radar e Copiloto
  renderizaram com título correto, aviso de demonstração e sem erro de console.
- O Copiloto recusou o envio sem empresa; após escolher empresa fictícia e usar
  uma pergunta sugerida, entregou resposta simulada com fontes expandíveis que
  identificam carteira, DTE e Triagem como dados sintéticos.

Limites: esta é uma jornada simulada por sessão; não prova egressão, modelo,
autorização real, consumo, identidade de fonte externa, latência ou produção.

## V-070 — Auditoria local de revisão fiscal e isolamento do console

Data: 21/09/2026. Ambiente: navegador interno e base SQLite temporária, com
sementes fictícias de demonstração e personas. Não houve conta, documento,
credencial ou serviço externo.

- A demonstração isolada abriu a fila de revisões NFS-e, exibiu empresa,
  documento, hash, motivo, evidência, confiança, XML e a decisão explícita sem
  prometer alteração no Domínio. O retorno à fila permaneceu disponível.
- A tentativa da mesma sessão de abrir `/platform/` recebeu a página de acesso
  restrito; assim, o ambiente de demonstração não ganhou acesso ao console
  Mewstack. Não houve erro de console nas jornadas adicionais.

Limites: a inspeção visual do console autenticado permanece pendente porque ela
exigiria inserir credencial, e não foi automatizada. A evidência prova somente
o bloqueio da persona fictícia, não todos os papéis de plataforma nem produção.

## V-069 — Auditoria visual local de jornadas públicas e fictícias

Data: 21/09/2026. Ambiente: navegador interno e base SQLite temporária migrada
e sem dados reais. Não houve credencial externa, envio de e-mail, chamada a
provedor, custo, deploy ou alteração em banco persistente.

- A página comercial carregou com seus recursos estáticos em servidor local de
  QA; a demonstração alternou abas por clique e teclado, atualizou a URL e
  expandiu a FAQ. O cadastro público expôs rótulos e impedimento nativo para
  campo obrigatório vazio.
- Em viewport móvel de 390×844, a página não teve overflow horizontal, manteve
  21 controles focáveis e preservou a aba/painel selecionados. Não houve erro
  de console nas superfícies verificadas.
- Com semente exclusivamente fictícia e isolamento de sessão habilitado no
  servidor de QA, a entrada chegou ao dashboard, à navegação de Documentos e à
  Triagem. Um anexo em quarentena informou de forma explícita que não pode ser
  aberto ou baixado.

Limites: o Mac estava bloqueado para automação nativa e a auditoria não cobre
console Mewstack, todos os perfis, todos os estados de falha, leitor de tela
nativo, integrações ou ambiente publicado. O servidor de QA usou `DEBUG` e
arquivos estáticos servidos localmente; isto não é prova de produção.

## V-068 — View Hub integralmente tipada e regressão local focada

Data: 21/09/2026. Ambiente: macOS local, banco de testes e dados sintéticos.
Não houve Serpro, ADN, caixa de e-mail, Domínio, credencial, custo, deploy ou
alteração operacional.

- Os fluxos de conciliação, Triagem, certificados, setup e aceite de tokens
  passaram a estreitar usuário autenticado, identificadores opcionais,
  apresentações e respostas de arquivo de forma explícita. Não houve alteração
  de regra de negócio, integração ou persistência adicional.
- Ruff e MyPy passaram em `apps/hub/views.py`; **119 testes passaram** em
  **14,93 s**, com **1 skip** esperado de OCR local em português. `mypy .`
  passou nos **190 arquivos** verificados; `git diff --check` passou.
- A regressão integral repetiu `manage.py check`, migrações sem alterações e
  **762 testes aprovados, 3 skips e 11 subtestes aprovados em 27,70 s**.
- `git fetch origin --prune` e a comparação `HEAD...origin/main` retornaram
  **0/0**: não há commit remoto ausente localmente, nem commit local à frente.
  O checkout preserva 68 alterações locais não commitadas desta execução.

Limites: os skips permanecem Playwright Python opcional, OCR local em português
indisponível e concorrência de locks exclusiva de PostgreSQL. O resultado é
exclusivamente local e não homologa provedores de e-mail, ADN, Serpro, Domínio,
layouts reais, fontes Radar ou conectores.

## V-067 — NFS-e e DCTFWeb da view Hub refinados localmente

Data: 21/09/2026. Ambiente: macOS local. Sem Serpro, ADN, Domínio, credencial,
custo, deploy ou alteração operacional.

- A view passou a explicitar coleções NFS-e, contexto do escritório, campos
  numéricos heterogêneos, expoente decimal, UUID e cotações DCTFWeb.
- Ruff passou; **20 testes** de NFS-e/DCTFWeb passaram em **13,49 s** e `git
  diff --check` está limpo.

Limites: as integrações fiscais seguem sem homologação externa.

## V-066 — Primeira seção da view do Hub tipada e retestada

Data: 21/09/2026. Ambiente: macOS local, banco de testes. Não houve conexão
externa, credencial, custo, deploy ou alteração operacional.

- As rotas de demonstração, dashboard, convites, permissões de módulo, despacho
  NFS-e e filtros receberam contratos estáticos explícitos, sem mudar seus
  fluxos de negócio.
- Ruff e MyPy passaram na seção alterada; **86 testes** de workspace,
  demonstração, convite e NFS-e passaram em **20,69 s**. `git diff --check`
  passou. A dívida da view do Hub reduziu de 131 para **114 erros**.

Limites: toda evidência é local e sintética; integrações e homologações externas
das etapas 07–12 permanecem pendentes.

## V-065 — Serviços, agente e interface de IA com contratos tipados

Data: 21/09/2026. Ambiente: macOS local, banco e transportes sintéticos. Não
houve Claude, Domínio, agente Windows, credencial, custo, deploy ou alteração
operacional.

- A reserva do Copiloto declara os livros token/legado e exige reserva antes do
  fallback; a API do agente tipa chave da CA, respostas de arquivo e lote de
  backup; e a tela do Copiloto conserva o estado transitório de entrega apenas
  na apresentação, sem acrescentá-lo ao modelo persistido.
- Ruff e MyPy passaram nos três módulos. As suítes de Copiloto, agente,
  backup e interface fecharam com **68 aprovados em 28,13 s**. `git diff
  --check` passou. MyPy global baixou para **131 erros em 1 arquivo**.

Limites: nenhuma chave, saída Claude, agente, documento ou dado de cliente foi
usado. Curadoria, egressão autorizada e homologações das etapas 05/12 continuam
pendentes.

## V-064 — Operações Integra e sincronização ADN com contratos tipados

Data: 21/09/2026. Ambiente: macOS local, banco e transportes sintéticos. Não
houve Serpro, ADN, Domínio, credencial, custo, deploy ou alteração operacional.

- Os mapas de operação PARCSN/DCTFWeb aceitam chaves de entrada validadas; a
  aprovação DTE separa cotação e reserva dos livros token/legado; tarefas
  tipam sua queryset NFS-e, despacho pós-commit e resultados PARCSN; e a
  validação NFS-e confirma explicitamente o expoente decimal.
- Ruff e MyPy passaram nos três módulos. As suítes de DTE, guias, DCTFWeb,
  PARCSN e NFS-e fecharam com **57 aprovados em 15,62 s**. `git diff --check`
  passou. MyPy global baixou para **143 erros em 4 arquivos**.

Limites: conexões, certificados, documentos e respostas eram sintéticos. As
homologações Serpro, ADN e Domínio das etapas 07, 08, 09 e 12 continuam pendentes.

## V-063 — Regressão integral após os lotes locais V-060 a V-062

Data: 21/09/2026. Ambiente: macOS local. Não houve conexão externa,
credencial, custo, deploy ou alteração operacional.

- `manage.py check` e `makemigrations --check --dry-run` não encontraram
  pendências. A suíte integral fechou com **762 aprovados, 3 skips e 11
  subtestes aprovados em 27,52 s**; `git diff --check` passou. `git fetch
  origin --prune` e a comparação `HEAD...origin/main` retornaram **0/0**:
  não há commits remotos ausentes localmente nem commits locais à frente.

Limites: os skips continuam limitados a Playwright Python opcional, OCR local
em português indisponível e concorrência de locks exclusiva de PostgreSQL. A
regressão local não homologa integrações externas.

## V-062 — Segurança de anexos, Domínio multipart e acesso DTE tipados

Data: 21/09/2026. Ambiente: macOS local, banco e transportes sintéticos. Não
houve consulta Domínio, Serpro, caixa de e-mail, credencial, custo, deploy ou
alteração de configuração operacional.

- A leitura de `FieldFile` é convertida ao contrato binário do scanner e da
  política; o multipart separa valores textuais de conteúdo binário; navegação
  recebe a requisição tipada; e a reserva DTE aceita explicitamente os dois
  livros locais de consumo.
- Ruff e MyPy passaram nos quatro módulos. Os testes de segurança/ingestão,
  política de arquivos, API Domínio local, navegação e DTE fecharam com **40
  aprovados em 14,49 s**. `git diff --check` passou. MyPy global baixou para
  **160 erros em 7 arquivos**.

Limites: não houve antimalware, mensagem, conexão Domínio ou requisição Serpro
real. As homologações das etapas 06, 08, 09 e 12 permanecem pendentes.

## V-061 — Plataforma administrativa com contratos tipados

Data: 21/09/2026. Ambiente: macOS local, banco de testes e webhooks sintéticos.
Não houve Asaas, cobrança, credencial, custo, deploy ou alteração de condições
comerciais.

- A tarefa de competência declara o mapa heterogêneo retornado; o snapshot de
  contrato confirma o plano antes de congelar módulos; o webhook lida com
  `Content-Type` ausente; e a página legal possui contrato HTTP explícito.
- Ruff e MyPy passaram nos quatro módulos. As suítes de tarefas, pagamentos,
  configuração e contratos fecharam com **69 aprovados em 8,04 s**. `git diff
  --check` passou. MyPy global baixou para **168 erros em 11 arquivos**.

Limites: eventos de pagamento e webhooks eram sintéticos. Nenhuma cobrança,
evento Asaas ou mudança de preço/contrato foi criada; Q-08/Q-28 continuam
pendentes para a etapa 10.

## V-060 — Coletores e fila de Triagem com contratos tipados

Data: 21/09/2026. Ambiente: macOS local, transportes sintéticos e banco de
testes local. Não houve OAuth, caixa de e-mail, DNS, scanner, credencial,
custo, deploy ou alteração de configuração operacional.

- O cursor Graph materializa a data inicial e a continuidade validadas antes de
  persistir; a leitura IMAP declara o conteúdo binário e a fábrica de conexão;
  a fila declara sua queryset elegível e não mistura tipos de resultados de
  provedores. Não houve mudança de protocolo ou de chamadas de rede.
- Ruff e MyPy passaram em Graph, IMAP e tarefas. Os testes de Graph, IMAP,
  retentativa, ingestão e fila fecharam com **22 aprovados em 14,40 s**.
  `git diff --check` passou. MyPy global baixou para **172 erros em 15 arquivos**.

Limites: todas as mensagens/conexões eram sintéticas. OAuth, provedores,
antimalware e destinos reais continuam pendentes nas etapas 06 e 12.

## V-059 — Relatórios e sincronização bancária com contratos estáticos

Data: 21/09/2026. Ambiente: macOS local, banco de testes local. Não houve
chamada a Domínio, Claude, provedores, credencial, custo, deploy ou alteração
de configuração operacional.

- A estrutura normalizada da sincronização bancária passou a declarar os tipos
  de cada campo antes das escritas idempotentes em `DominioBankEntry` e
  `AccountingEntry`. As bibliotecas de geração XLSX/PDF, já dependências do
  projeto, receberam exceções locais e explícitas para a falta de stubs MyPy.
- Ruff e MyPy passaram nos dois módulos. Os **7 testes** de sincronização
  passaram em **13,26 s**. Não há teste dedicado de exportação de relatório no
  repositório; isso é um limite de cobertura, não uma aprovação adicional.
  `git diff --check` passou. MyPy global baixou para **185 erros em 18 arquivos**.

Limites: não houve documento, lançamento bancário, planilha ou PDF de cliente
real. Integração Domínio, curadoria e homologações da etapa 05/09 continuam
pendentes.

## V-058 — Regressão local integral após os lotes de contratos

Data: 21/09/2026. Ambiente: macOS local. Não houve conexão externa,
credencial, custo, deploy ou alteração operacional.

- `manage.py check` não encontrou problemas e `makemigrations --check --dry-run`
  não encontrou mudanças. A suíte integral fechou com **762 aprovados, 3 skips
  e 11 subtestes aprovados em 27,46 s**; `git diff --check` passou.

Limites: os skips permanecem limitados a Playwright Python opcional, OCR local
em português indisponível e concorrência de locks exclusiva de PostgreSQL. A
regressão local não homologa serviços externos.

## V-057 — Gateway e comandos de IA com contratos tipados

Data: 21/09/2026. Ambiente: macOS local, comandos e transporte Claude
substituídos nos testes. Não houve chamada Anthropic, chave, dado de cliente,
custo, deploy ou alteração de configuração operacional.

- O payload do gateway foi declarado como mapa de objetos heterogêneos e os
  comandos de configuração/verificação ganharam assinaturas de parser/opções
  explícitas. O comando que exige custo continua exigindo `--cost-approved`;
  a alteração não o executou.
- Ruff e MyPy passaram nos quatro módulos. As suítes de comandos, escopo IA e
  acesso operacional fecharam com **32 aprovados em 13,42 s**. `git diff
  --check` passou. MyPy global baixou para **197 erros em 20 arquivos**.

Limites: a evidência não valida egressão, modelo, custo, resposta Claude ou
treinamento. Q-08/Q-09/Q-11/Q-34 permanecem exigências da etapa 05.

## V-056 — Configuração de plataforma com contratos locais completos

Data: 21/09/2026. Ambiente: macOS local, banco de testes e transportes
substituídos. Não houve Serpro, SMTP, Claude, Asaas, BrasilAPI, credencial, custo,
deploy ou alteração de configuração operacional.

- Os formulários de plataforma agora tipam seus limites dinâmicos de Django,
  retornos de `clean`, persistência de `ModelForm` e usuário de auditoria. O
  manipulador de plano não mistura manager e queryset com lock. Os módulos de
  pagamento/notificação e aprovação de fallback também preservam valores
  verificados antes de persistir ou notificar.
- Ruff e MyPy passaram em `configuration.py`, `payments.py`, `notifications.py`
  e `views.py`. As suítes de configuração, faturamento, pagamentos e tokens
  fecharam com **55 aprovados, 1 skip de concorrência PostgreSQL e 8,02 s**.
  `git diff --check` passou. MyPy global baixou para **205 erros em 24 arquivos**.

Limites: os testes usam dados/transportes locais. Não houve validação SMTP,
chamada Claude/Serpro/Asaas nem alteração de preço ou contrato comercial.

## V-055 — Coletor Gmail e ingestão com pré-condições explícitas

Data: 21/09/2026. Ambiente: macOS local, mensagens e respostas Gmail sintéticas.
Não houve OAuth, caixa Google real, credencial, conexão externa, custo, deploy ou
alteração de configuração operacional.

- O cursor, checkpoint e leitura Gmail exigem explicitamente a data inicial da
  caixa antes de comparar ou persistir datas. A decodificação base64 usa a
  exceção do módulo padrão e o caminho do blob em quarentena é normalizado para
  texto antes da limpeza após falha.
- Ruff e MyPy passaram em `apps/triage/gmail_poll.py` e `apps/triage/ingest.py`.
  Testes de ingestão e retentativa fecharam com **14 aprovados em 7,16 s**;
  `git diff --check` passou. MyPy global baixou a **291 erros em 28 arquivos**.

Limites: nenhuma caixa Google foi autenticada ou consultada. OAuth, scanner e
destinos reais permanecem pendentes da etapa 06/12.

## V-054 — Cliente IMAP local com respostas tipadas

Data: 21/09/2026. Ambiente: macOS local, DNS e IMAP sintéticos. Não houve caixa
real, credencial de provedor, conexão externa, custo, deploy ou alteração de
configuração operacional.

- O socket TLS é retornado com o tipo explícito; cada resposta IMAP recebe uma
  variável própria, e a ausência de charset no `UID SEARCH` é preservada com
  conversão de tipo sem mudar o argumento entregue ao protocolo.
- Ruff e MyPy passaram em `apps/triage/imap.py`. Testes de conexão e
  retentativa passaram com **12 aprovados em 14,07 s**; `git diff --check`
  passou. MyPy global baixou para **296 erros em 30 arquivos**.

Limites: nenhuma caixa IMAP foi conectada, lida ou alterada. OAuth, provedor,
scanner e destino real seguem pendentes da etapa 06/12.

## V-053 — Livros de tokens e faturamento tipados sem mudança comercial

Data: 21/09/2026. Ambiente: macOS local, banco de testes e sem transporte de
pagamentos. Não houve Asaas, cobrança, preço novo, credencial, custo, deploy ou
alteração de configuração operacional.

- A competência de fechamento passa a usar variável distinta para o medidor
  legado, preservando a separação de `UsageMeter` e `TokenMeter`. O medidor de
  tokens materializa franquia/preço não nulos antes de criar o livro, e a
  ativação recebe o usuário autenticado esperado pelo modelo.
- Ruff e MyPy passaram em `apps/platform/billing.py` e
  `apps/platform/token_billing.py`. A suíte de faturamento, pagamentos e tokens
  fechou com **22 aprovados, 1 skip de concorrência PostgreSQL e 7,75 s**.
  `git diff --check` passou. MyPy global baixou a **300 erros em 31 arquivos**.

Limites: não houve fatura, cobrança ou pagamento real. A orquestração Asaas e
homologação de meios de pagamento continuam abertas na etapa 10.

## V-052 — Transporte de e-mail local com contrato tipado

Data: 21/09/2026. Ambiente: macOS local, banco de testes e backend SMTP
substituído. Não houve conexão SMTP, DNS, Brevo, credencial, custo, deploy ou
alteração de configuração operacional.

- O backend de e-mail passou a declarar a configuração de plataforma, backend
  SMTP e sequência de mensagens com as assinaturas esperadas pelo Django. O
  carregamento do modelo permanece tardio para não afetar a inicialização do
  registro de aplicações.
- Ruff e MyPy passaram em `apps/common/database_email.py`. A suíte de
  configuração fechou com **33 aprovados em 7,66 s**; `git diff --check`
  passou. MyPy global baixou para **311 erros em 33 arquivos**.

Limites: isto confirma somente o transporte local substituído. A configuração e
entrega SMTP/DNS/Brevo reais continuam para a etapa 12 por D-77/D-78.

## V-051 — PARCSN e operações agendadas com contratos de tipo explícitos

Data: 21/09/2026. Ambiente: macOS local, banco de testes e respostas sintéticas.
Não houve chamada Serpro, credencial, certificado, documento real, custo, deploy
ou alteração de configuração operacional.

- O parser PARCSN agora valida que o expoente decimal é numérico antes de
  comparar casas decimais e retorna inteiro explícito para campos positivos. O
  registrador de tarefas agendadas reconhece as duas formas previstas de
  resultado e expõe a assinatura completa do decorador.
- Ruff e MyPy passaram em `apps/integra/parcelamento.py` e
  `apps/platform/operations.py`. `test_integra_parcelamento.py`,
  `test_parcelamento_operations.py` e `test_platform_tasks.py` fecharam com
  **20 aprovados em 13,70 s**; `git diff --check` passou.
- MyPy global caiu para **316 erros em 34 arquivos**. A redução não equivale à
  homologação dos serviços ou ao fim da dívida técnica restante.

Limites: PARCSN continua limitado ao transporte simulado; credenciais, custo,
representação e prova Serpro permanecem dependências da etapa 08.

## V-050 — Importação local: limites de entrada explícitos

Data: 21/09/2026. Ambiente: macOS local e arquivos sintéticos. Não houve backup
Domínio real, ERP, arquivo de cliente, credencial, custo, deploy ou alteração de
configuração operacional.

- A criação de prévia de importação agora exige nome de arquivo antes de
  persistir metadados, reutiliza esse nome validado para salvar/identificar o
  conteúdo e tipa o mapa de capacidades por tipo de importação. A leitura de
  upload é declarada como bytes e o aviso de `defusedxml` fica restrito ao
  import sem stubs.
- Ruff passou em `apps/hub/imports.py`. A checagem direta reporta apenas erros
  de módulos transitivamente importados; a tentativa de isolá-los com
  `--follow-imports=skip` atingiu um erro interno do MyPy 1.19.1 em
  `django-stubs`, portanto não é contada como aprovação. A auditoria global
  ainda concluiu e baixou para **328 erros em 37 arquivos**.
- `tests/test_hub.py`, `test_hub_api.py` e `test_hub_workspace_views_django.py`
  fecharam com **57 aprovados em 14,41 s**; `git diff --check` passou.

Limites: não houve teste de backup `.dom` real, layout autorizado, leitura de
ERP, fonte externa ou homologação de importação. O erro interno do MyPy exige
atualização/diagnóstico separado do verificador, não supressão global.

## V-049 — Serviço de conciliação com contratos de tipo explícitos

Data: 21/09/2026. Ambiente: macOS local, banco de testes, arquivos sintéticos e
OCR local indisponível. Não houve acesso a ERP, fonte Radar, arquivo de cliente,
credencial, custo, deploy ou alteração de configuração operacional.

- O serviço agora declara o checkpoint heterogêneo de uma execução, o contrato
  de dialeto CSV, bytes do armazenamento, chave TSV de OCR e relações opcionais
  de conta/movimento. A regra de faixa somente tenta converter limites textuais
  ou numéricos válidos e retorna não correspondência para forma inválida,
  mantendo a regra restritiva.
- `openpyxl` e `pypdfium2` continuam dependências de runtime sem stubs; as
  exceções de tipo são locais aos imports e não alteram o uso das bibliotecas.
  Ruff e MyPy passaram em `apps/hub/reconciliation_service.py`.
- A suíte de conciliação fechou com **35 aprovados, 1 skip de OCR português e
  7,91 s**. `manage.py check`, `makemigrations --check --dry-run` e `git diff
  --check` passaram. MyPy global baixou para **334 erros em 38 arquivos**.

Limites: layouts, OCR, volumes, fontes Radar e exportações para ERPs seguem
sem homologação externa. A contagem global é diagnóstico, não aceite global.

## V-048 — Formulários de contratação tipados e retestados

Data: 21/09/2026. Ambiente: macOS local, banco de testes e dublês de serviços.
Não houve consulta CNPJ, Asaas, cobrança, credencial, custo, deploy ou alteração
de configuração operacional.

- `LeadForm` tipa o objeto salvo pelo `ModelForm`; os formulários de plano e
  proposta de tokens tratam o retorno nulo previsto de `clean`; a remoção de
  módulo IA usa variável própria, sem ambiguidade com a taxa criada no ramo
  oposto. O comportamento de cobrança e a regra comercial permanecem iguais.
- Ruff e MyPy passaram em `apps/platform/forms.py`. A suíte de CNPJ, cobrança,
  pagamentos e tokens fechou com **26 aprovados, 1 skip de concorrência restrita
  a PostgreSQL e 7,43 s**. `git diff --check` passou.
- A auditoria MyPy global, executada de `src/`, baixou para **348 erros em 39
  arquivos**. O número é dívida técnica remanescente, não aprovação global.

Limites: esta rodada não criou cobrança, não acessou Asaas/BrasilAPI e não
homologou pagamentos ou concorrência em PostgreSQL.

## V-047 — Formulários do Hub e cache CNPJ tipados sem regressão

Data: 21/09/2026. Ambiente: macOS local, banco de testes e arquivos sintéticos.
Não houve consulta externa ao cadastro CNPJ, ERP, arquivo de cliente,
credencial, custo, deploy ou alteração de configuração operacional.

- Foram corrigidas as interfaces de tipo dos formulários de acesso, importação
  e conciliação: escolhas dinâmicas do Django, campos de modelo, widgets de
  conta financeira, validações `clean` e o campo múltiplo de arquivos. As
  conversões genéricas foram mantidas como referências adiadas, pois as classes
  Django não são subscritáveis em runtime; a suíte de integração confirmou que
  a página de conciliação continua sendo construída normalmente.
- O cache de consulta de CNPJ agora só reutiliza um dicionário de textos; valor
  inválido no cache é tratado como ausente, evitando confiar em um objeto de
  tipo inesperado. Não houve chamada à BrasilAPI nesta validação.
- Ruff e MyPy passaram em `apps/hub/forms.py` e `apps/common/cnpj.py`. A suíte
  de conciliação fechou com **35 aprovados, 1 skip de OCR em português e 8,22
  s**. `manage.py check`, `makemigrations --check --dry-run` e `git diff
  --check` passaram.
- A auditoria MyPy global, a partir de `src/`, baixou de 399 para **356 erros
  em 40 arquivos**. Isso é progresso de dívida técnica, não aprovação global.

Limites: não foram homologados OCR, layouts reais, ERP, Radar, exportação ou
qualquer fonte externa. As 356 ocorrências restantes seguem visíveis para
revisão modular.

## V-046 — Pré-condições de serviço da Triagem explicitadas

Data: 21/09/2026. Ambiente: macOS local, banco de testes e anexos sintéticos.
Não houve caixa real, arquivo de cliente, credencial, provedor, custo, deploy ou
alteração de configuração operacional.

- `apps.triage.services` agora materializa as pré-condições que o fluxo já
  aplicava: empresa e tipo precisam existir antes da aprovação; upload precisa
  ter nome e tamanho válido; caminho de destino precisa existir antes de abrir
  a cópia; os retornos de armazenamento são streams binários. Isto não altera
  os estados, a política de segurança, nem cria uma integração externa.
- O lote removeu **9 ocorrências MyPy**. A nova auditoria global, executada a
  partir de `src/`, encontrou **399 erros em 42 arquivos** (antes, 408 em 43);
  o valor continua sendo diagnóstico de dívida técnica, não aprovação global.
- Ruff e MyPy passaram em `apps/triage/services.py`. A suíte de domínio,
  ingestão e agente Windows fechou com **35 aprovados em 7,47 s**. `manage.py
  check`, `makemigrations --check --dry-run` e `git diff --check` passaram.

Limites: esta evidência não homologa e-mail, scanner, agente instalado ou
escrita Windows. As 399 ocorrências restantes permanecem para lotes revisáveis
e não são suprimidas por configuração global.

## V-045 — Formulários da Triagem tipados sem mudança funcional

Data: 21/09/2026. Ambiente: macOS local, banco de testes e transporte de e-mail
sintético. Não houve caixa real, arquivo de cliente, credencial, provedor,
custo, deploy ou alteração de configuração operacional.

- A interface dos seis formulários de Triagem passou a aceitar os argumentos
  dinâmicos do Django com `Any` restrito às fronteiras do framework. Os dois
  campos de escolha foram convertidos explicitamente para seus respectivos
  tipos de modelo e os métodos `clean` preservam um dicionário não nulo. A
  validação de data agora também confirma o tipo antes da comparação.
- Isto elimina **127 ocorrências MyPy** sistemáticas de `forms.py`, sem trocar
  campo, rótulo, regra de validação, fluxo de tela, persistência ou migração.
  Nova auditoria `uv run mypy .` resultou em **408 erros em 43 arquivos**;
  portanto, ainda é diagnóstico de dívida técnica, não aprovação global.
- Ruff e MyPy passaram nos três módulos de Triagem alterados. `manage.py
  check` e `makemigrations --check --dry-run` passaram. A suíte consolidada de
  política de arquivo, IMAP, domínio e ingestão fechou com **51 aprovados em
  14,77 s**. `git diff --check` passou.

Limites: a evidência não homologa OAuth, IMAP, antimalware, arquivamento ou
qualquer destino Windows. Os 408 erros restantes exigem revisão em lotes; não
devem ser ocultados por uma regra global de MyPy.

## V-044 — Diagnóstico global e primeiro lote de tipagem da Triagem

Data: 21/09/2026. Ambiente: macOS local, sem conexão externa, dado de cliente,
credencial, custo, deploy ou alteração de configuração operacional.

- `uv run mypy .`, executado a partir de `src/`, encontrou **535 erros em 46
  arquivos**. A execução é um diagnóstico da dívida técnica existente, não uma
  aprovação global; inclui anotações incompatíveis em formulários/views e duas
  dependências sem stubs (`defusedxml` e `reportlab`).
- Como primeiro lote sem alterar comportamento, `presentation.py` declara o
  mapa de âncoras de provedores com o tipo de chave correto e `file_policy.py`
  documenta a ausência de stubs de `defusedxml`. Assim, MyPy não confunde o
  enum de provedor com a chave de texto do dicionário e a análise preserva a
  validação XML existente em tempo de execução.
- `uv run ruff check apps/triage/presentation.py apps/triage/file_policy.py` e
  `uv run mypy apps/triage/presentation.py apps/triage/file_policy.py`
  passaram. `uv run pytest ../tests/test_triage_file_policy.py
  ../tests/test_triage_domain.py ../tests/test_triage_email_ingest_django.py
  -q` fechou com **44 aprovados em 7,12 s**. `git diff --check` passou.

Limites: ainda há 533 ou mais ocorrências globais a revisar, pois esta rodada
somente removeu as duas ocorrências dos módulos citados. Não houve migração,
mudança de regra de negócio, chamada de provedor ou homologação de caixa de
e-mail/antimalware.

## V-043 — Qualidade de tipos da base local

Data: 21/09/2026. Ambiente: macOS local, sem conexão externa, dado de cliente,
credencial, custo, deploy ou alteração de configuração operacional.

- A execução MyPy de V-042 encontrou 21 erros em quatro módulos. Foram
  corrigidas somente anotações e assinaturas compatíveis com Django: armazenamento
  privado da Triagem, guarda nula do aplicativo OAuth, protocolo de caminho de
  arquivo de conciliação e assinaturas de `save`/`delete` dos livros de tokens.
  Não houve alteração de regra comercial, persistência, migração ou chamada de
  provedor.
- A partir de `src/`, `uv run mypy apps/triage/storage.py
  apps/triage/models.py apps/hub/models.py apps/platform/models.py
  apps/intelligence/training.py
  apps/intelligence/management/commands/export_training_manifest.py` retornou
  **Success: no issues found in 6 source files**. Ruff dos mesmos arquivos
  passou.
- `uv run python manage.py check`, `makemigrations --check --dry-run` e
  `git diff --check` passaram. A suíte focada de Triagem, conciliação, cobrança
  e IA fechou com **125 aprovados, 1 ignorado e 3 subtestes aprovados em
  14,35 s**; o skip é OCR português indisponível.

Limites: esta execução resolve os erros MyPy observados nesses módulos, mas não
equivale a uma auditoria de tipos de todo o projeto, homologação externa ou
liberação comercial. A suíte integral posterior foi iniciada, mas a captura de
terminal não reteve seu resumo após exceder a janela interativa; ela não é
contabilizada como aprovação nesta evidência. Não havia processo Pytest ativo e
o cache `lastfailed` estava vazio após o término. As validações focadas acima
são a evidência desta mudança.

## V-042 — Etapa 05: gate local de privacidade antes do manifesto QLoRA

Data: 21/09/2026. Ambiente: macOS local, banco de testes e artefatos
temporários. Não houve dado de cliente, chamada Claude, egressão, credencial,
download de modelo, treinamento, GPU, custo, deploy ou publicação.

- Por D-94, `training_manifest` e `evaluation_manifest` agora recusam, antes de
  retornar qualquer item, exemplo validado que contenha CPF, CNPJ ou e-mail em
  pergunta, resposta ou referências. O padrão é o mesmo que o runner QLoRA já
  recusava posteriormente; o controle agora impede que o artefato seja criado.
- A recusa não edita nem mascara o exemplo original. A anonimização precisa ser
  uma revisão humana no registro de origem, para não alterar silenciosamente
  uma evidência contábil. O comando `export_training_manifest` converte a
  recusa em erro controlado e não cria o arquivo de saída. Por D-95, ele também
  usa criação exclusiva e recusa substituir um JSONL já existente.
- `uv run ruff check src/apps/intelligence/training.py
  src/apps/intelligence/management/commands/export_training_manifest.py
  tests/test_intelligence_training_django.py
  tests/test_intelligence_commands_django.py` passou. `manage.py check` e
  `makemigrations --check --dry-run` passaram. A suíte focada de treinamento,
  comandos e runner fechou com **39 aprovados e 3 subtestes aprovados em
  13,03 s**.
- Revalidação integral: `uv run pytest -q` fechou com **762 aprovados, 3
  ignorados e 11 subtestes aprovados em 27,90 s**. Os skips são Playwright
  Python opcional, OCR português indisponível e concorrência de locks coberta
  na evidência PostgreSQL histórica.

A checagem MyPy não constitui evidência verde: a partir de `src/`, ela alcançou
os arquivos alterados, mas terminou com 21 erros preexistentes em
`apps/triage/storage.py`, `apps/triage/models.py`, `apps/hub/models.py` e
`apps/platform/models.py`; eles não foram alterados nesta entrega e permanecem
como dívida da base técnica.

Limites: os gates não constituem corpus revisado, anonimização de material real,
curadoria, autorização de egressão, treinamento ou publicação de adaptador.
Q-08, Q-09, Q-11 e Q-34 continuam necessários; a etapa 05 permanece em
andamento.

## V-041 — Análise integral, continuidade segura da etapa 04 e sincronização Git

Data: 21/09/2026. Ambiente: macOS local, dependências travadas pelo projeto e
checkout inicialmente limpo. A análise não usou credencial, dado de cliente,
conexão Siescon, arquivo de ERP, chamada externa de provedor, custo, deploy ou
alteração de configuração operacional.

- Foram relidos os registros canônicos, o checklist da etapa 04, a matriz de
  capacidades, o inventário e a análise anterior. O objetivo confirmado é um
  SaaS multiempresa da Mewstack para escritórios contábeis, com agente Windows,
  operação auditável e evidência recuperável; código ou teste local não é
  homologação nem liberação de venda.
- A leitura do código confirma o limite de D-54/D-88: `AccountingExport`
  modela `siescon`, mas `ACCOUNTING_EXPORT_ADAPTERS` registra apenas Domínio.
  `get_accounting_export_adapter("siescon")` recusa a solicitação antes de
  consultar lançamentos ou gerar conteúdo. Não há adaptador, SQL, endpoint,
  credencial ou layout Siescon inventado nesta execução.
- `uv run ruff check .`, `uv run python manage.py check` e
  `uv run python manage.py makemigrations --check --dry-run` passaram.
  `uv run pytest tests/test_reconciliation_module.py -q` fechou com **35
  aprovados e 1 ignorado em 7,67 s**; o skip é OCR local em português
  indisponível. `uv run pytest -q` fechou com **759 aprovados, 3 ignorados e
  8 subtestes aprovados em 27,82 s**. Os demais skips são Playwright Python
  opcional e concorrência de locks coberta na evidência PostgreSQL histórica.
- `git fetch origin --prune` concluiu e `git rev-list --left-right --count
  HEAD...origin/main` retornou **0\t0**. Não havia commit remoto ausente,
  commit local não enviado ou alteração no diretório de trabalho antes desta
  documentação.

Limites: a revalidação não torna Siescon conectado, não substitui o contrato
técnico de Q-33 e não avança o aceite de importação conferida exigido por D-73.
A etapa 04 permanece em andamento. Para implementar com segurança, o técnico
Siescon deve disponibilizar por canal seguro versão, banco/driver e acesso de
leitura; schema/campos permitidos; identificador de empresa e cursor; ambiente
de homologação/revogação; e layout versionado com amostra sintética de
exportação/importação. O próximo passo é revisar esse material e só então
registrar um adaptador versionado, mantendo a escrita direta proibida.

## V-040 — Etapa 10: contrato local do cliente Asaas

Data: 20/09/2026. Ambiente: macOS local, chave de exemplo injetada somente
nos testes e transporte substituído por dublês em memória. Não houve leitura de
configuração, segredo real, conexão de rede, conta/sandbox Asaas, cliente,
cobrança, dado de cliente, custo ou deploy.

- O cliente local seleciona de modo explícito `sandbox` ou `production`, envia
  `access_token`, `Content-Type` e `User-Agent`, e permite transportar a
  requisição apenas por injeção. Ele não procura chave em `settings`, arquivos
  locais ou variáveis de ambiente.
- Antes de criar cliente, consulta `externalReference`; a criação de cliente e
  de cobrança avulsa não tem retentativa automática após falha ou resultado
  incerto. A cobrança aceita PIX, boleto ou cartão sem receber dados de cartão;
  o retorno é validado antes de ser exposto ao chamador.
- `uv run pytest tests/test_asaas_client.py tests/test_platform_billing.py tests/test_platform_payments.py tests/test_token_billing.py tests/test_cica_contract_mfa.py tests/test_cica_operation_access.py -q`: **49 aprovados e 1 ignorado em 13,54 s**. O skip cobre concorrência de locks exclusiva do PostgreSQL.
- Ruff dos módulos/testes de Asaas e cobrança, `uv run python manage.py check`,
  `uv run python manage.py makemigrations --check --dry-run` e `git diff --check`
  passaram.
- Revalidação integral: `uv run pytest -q` fechou com **759 aprovados, 3
  ignorados e 8 subtestes aprovados em 28,99 s**; `uv run ruff check .`, Django,
  dry-run de migrações e diff também passaram. Os skips permanecem: Playwright
  Python opcional, OCR português indisponível e concorrência de locks coberta
  na evidência PostgreSQL histórica.

O contrato foi alinhado à [autenticação](https://docs.asaas.com/docs/authentication),
ao [cliente](https://docs.asaas.com/reference/create-new-customer) e à
[cobrança](https://docs.asaas.com/reference/create-new-payment) documentados
pela Asaas. Limites: não há orquestração entre contrato comercial, cliente,
`PaymentAttempt` e ambiente autorizado; também não há teste de Pix, boleto,
cartão, atraso, estorno, webhook real ou evento fora de ordem. Q-08/Q-28 e a
etapa 12 de D-87 continuam obrigatórios. A etapa 10 permanece em andamento.

## V-039 — Etapa 11: jornadas e interfaces locais, inspeção parcial

Data: 19/09/2026. Ambiente: servidor de QA descartável em `127.0.0.1:8011`,
SQLite e mídia sob `.tmp/ui-review`, massa sintética e sockets externos
bloqueados pelo próprio servidor de QA. A inspeção iniciou e fechou uma sessão
de demonstração fictícia; não usou conta, dado ou serviço externo.

- Navegação interativa em navegador local percorreu Visão geral, Empresas,
  NFS-e, Guias, Central Integra/DTE/Parcelamentos, Conciliação, Radar, Triagem,
  Caixas, Configuração, Equipe e Copiloto. Nos 14 caminhos, em desktop e em
  390 × 844, a verificação DOM encontrou um único `h1`, nenhum campo visível
  sem rótulo e nenhum overflow horizontal.
- A inspeção visual do fluxo fictício de Triagem confirmou no celular e desktop
  a fila, bloqueio explícito de item em quarentena, revisão, transição para
  “Pronto para arquivar”, arquivamento fictício e link privado de download. O
  progresso permaneceu na sessão e a tela declarou que nenhuma pasta real seria
  alterada. O console do navegador não registrou erros.
- `uv run pytest tests/test_hub_workspace_views_django.py tests/test_seed_demo_django.py tests/test_cica_auth_flow.py -q`: **77 aprovados e 1 ignorado em 21,08 s**. O skip é o Playwright Python opcional; a inspeção interativa acima não depende desse pacote.
- Ruff dos módulos/testes envolvidos, `uv run python manage.py check`,
  `uv run python manage.py makemigrations --check --dry-run` e `git diff --check`
  passaram.

Limites: a inspeção não conclui o site comercial, cadastro, central de
aprendizado ou console Mewstack; também não cobre todos os perfis, estados de
carga/erro/vazio, navegação exclusivamente por teclado, contraste por elemento
ou tarefas reais autorizadas. É uma auditoria local parcial, não homologação e
nem prova de que a oferta comercial corresponde a integrações ainda pendentes.
A etapa 11 permanece em andamento.

## V-038 — Etapa 06: Triagem de Arquivos local

Data: 19/09/2026. Ambiente: macOS local, banco de testes, armazenamento
temporário e provedores/antimalware/agente substituídos por dublês de teste. Sem
OAuth, caixa de e-mail, ClamAV, agente Windows, arquivo de cliente, escrita em
pasta real, chamada externa, custo ou deploy.

- A entrada local mantém o binário em quarentena privada, normaliza nome,
  preserva procedência por mensagem/parte e é idempotente apenas para a mesma
  entrega. Pollers simulados exercitam cursor, corte e leitura sem marcar a
  mensagem como lida; anexo grande ou caixa pausada não persiste binário.
- Arquivo não verificado não pode ser revisado, baixado ou arquivado. Um scanner
  limpo ainda exige formato permitido; detecção rejeita e indisponibilidade do
  scanner conserva a quarentena. A cópia da biblioteca privada é relida e tem
  SHA-256 conferido antes do estado final, que volta a falhar se adulterada.
- O contrato local do agente Windows vincula escritório, raiz, caminho relativo,
  tamanho e hash; só confirma o arquivamento após a prova correspondente. Outra
  organização recebe 404, falha fica recuperável e nome/caminho inválido é
  recusado. Isso é teste de protocolo, não escrita no Windows.
- `uv run pytest tests/test_triage_domain.py tests/test_triage_oauth_django.py tests/test_triage_email_ingest_django.py tests/test_triage_gmail_poll_django.py tests/test_triage_graph_poll_django.py tests/test_triage_poll_retry_django.py tests/test_triage_windows_paths.py tests/test_triage_windows_agent.py -q`: **72 aprovados e 6 subtestes aprovados em 14,40 s**.
- `uv run pytest tests/test_hub_workspace_views_django.py tests/test_seed_demo_django.py -k 'triage' -q`: **6 aprovados, 64 desmarcados em 14,04 s**. Cobre escopo por empresa, fila, bloqueio de não verificado, cópia privada e demo isolada por sessão.
- Ruff dos módulos e testes envolvidos, `uv run python manage.py check`,
  `uv run python manage.py makemigrations --check --dry-run` e `git diff --check`
  passaram.

Limites: não há consentimento/revogação, redirect ou leitura real em Microsoft,
Google/Gmail/IMAP; não há ClamAV instalado/atualizado, catálogo/nomenclatura,
retenção, árvore de destino, regra de checklist ou raiz/conta Windows aprovadas.
Q-12 a Q-25 e Q-31 continuam abertas, e D-73 exige amostra e recuperação no
destino autorizado. A etapa 06 permanece em andamento.

## V-037 — Etapa 09: Conciliação e Radar locais

Data: 19/09/2026. Ambiente: macOS local e banco de testes; entradas e respostas
sintéticas controladas pelos testes. Não houve arquivo bancário, lançamento,
exportação, acesso a Domínio/Siescon, coleta HTTP real, dado de cliente, custo,
deploy ou configuração operacional.

- A conciliação local aceita somente OFX, CSV, XLSX ou PDF com limites de
  tamanho/linhas/páginas, identifica o tipo pelo conteúdo, guarda fonte privada
  com hash e trata reenvio idempotente. Há mapeamento revisável, conta financeira,
  regras, movimentos normalizados, partidas equilibradas, conciliação parcial ou
  desfeita e evidência obrigatória para a confirmação. Ambiguidade permanece em
  revisão; não há confirmação automática apenas por data e valor.
- O processamento persiste execução, checkpoint, erros e retomada de trabalho
  pendente/expirado. A exportação local mantém hash, reexportação ligada à origem
  e estado explícito, mas não foi importada em qualquer ERP nesta execução.
- O Radar limita a coleta a três páginas oficiais fixas, conserva URL/origem e
  relevância, é idempotente e registra falha por fonte sem expor erro interno na
  interface. As coletas foram simuladas pelos testes; a disponibilidade das
  páginas oficiais não foi exercitada.
- `uv run pytest tests/test_reconciliation.py tests/test_reconciliation_module.py tests/test_reform_radar.py -q`: **46 aprovados e 1 ignorado em 7,84 s**. O skip é o caso de OCR local em português, pois Tesseract/modelo `por` não está disponível nesta estação.
- `uv run pytest tests/test_hub_workspace_views_django.py tests/test_seed_demo_django.py -k 'reform_radar or reconciliation_confirmation' -q`: **4 aprovados, 66 desmarcados em 14,29 s**. Cobre filtro/estado seguro de falha do Radar e confirmação de conciliação fictícia isolada por sessão.
- Ruff dos módulos e testes envolvidos, `uv run python manage.py check`,
  `uv run python manage.py makemigrations --check --dry-run` e `git diff --check`
  passaram.

Limites: não há layout bancário/contábil aprovado, OCR português disponível,
amostra independente de 200 itens, volume em PostgreSQL, fonte Radar real
exercitada, importação conferida no Domínio ou adaptador/layout Siescon. D-54
proíbe escrita direta no Siescon; D-73 exige a conferência no destino antes de
aprovar exportação. A etapa 09 permanece em andamento.

## V-036 — Matriz auditável de evidências do plano

Data: 19/09/2026. Ambiente: checkout local e documentação canônica. Sem execução de integração externa, dado de cliente, segredo, custo, deploy ou alteração de configuração operacional.

- A matriz `docs/planejamento/matriz-evidencias-2026-09-19.md` confronta as 14 etapas, seus checklists, as evidências V-001 a V-035, o inventário e as decisões/dúvidas abertas. Para cada etapa, registra somente o maior nível demonstrado e o bloqueio que impede o nível seguinte.
- A conclusão documental confirma que implementação ou teste local não basta para homologação nem liberação comercial. Q-33/Siescon é a primeira dependência técnica sequencial; governança da IA e contratos/autorização dos provedores continuam condicionando os demais pilotos.
- `git diff --check`, `uv run python manage.py check` e `uv run python manage.py makemigrations --check --dry-run` passaram após a atualização documental.

Limites: a matriz sintetiza evidências existentes e não executa qualquer piloto ou integrações. Ela não fecha etapas com checklist pendente nem substitui os aceites de D-73 e da etapa 12.

## V-035 — Etapa 07: demonstração NFS-e local

Data: 19/09/2026. Ambiente: banco SQLite temporário, migrado e semeado exclusivamente com dados fictícios, removido ao final da inspeção. Não houve certificado, chamada ADN, consulta fiscal, dado de cliente, escrita em pasta Windows, egressão, cobrança ou custo.

- A verificação de servidor confirmou a geração de ZIP por empresa em `Tomadas/CÓDIGO -/` e `Emitidas/CÓDIGO -/`, a seleção da carteira inteira e o manifesto que separa sugestão acima de 95%, decisão manual e Transitória em 0%. `uv run pytest tests/test_seed_demo_django.py -k 'nfse' tests/test_hub_workspace_views_django.py -k 'nfse_center' -q`: **4 aprovados, 66 desmarcados em 13,45 s**. Ruff de `views.py` e dos testes: aprovado.
- Inspeção interativa com navegador local na demonstração isolada: filtro exclusivo mudou de competência para emissão; `01092026` e `30092026` foram normalizados para `01/09/2026` e `30/09/2026`; a busca preservou os 24 itens no intervalo e refletiu os parâmetros na URL. Um acumulador digitado atualizou a linha para “Classificada”, “Definida pelo contador · 100%” e o rótulo manual; ao limpar, a linha retornou para “Em revisão”, “Transitória · 0%” e sem acumulador. Console sem erros.

Limites: ZIP e notas são fictícios e não comprovam importação, classificação fiscal, catálogo de acumuladores, coleta ADN, certificado, NSU, retomada ou deduplicação real. Q-28 e a amostra/aceite do módulo continuam necessários; a etapa 07 permanece em andamento.

## V-034 — Etapa 08: Central Integra Contador local

Data: 19/09/2026. Ambiente: macOS local, banco de teste e transporte simulado. Sem credencial, certificado, representação, chamada Serpro, ciência DTE, emissão, guia, DAS, custo ou dado real.

- DTE cobre preparação local sem despacho, empresas aptas, paginação com nova autorização, leitura de teor com permissão específica, auditoria e estado separado para resultado incerto. DCTFWeb preserva declaração, recibo e guia sem transmissão. PARCSN cobre carteira, seleção, cotação, autorização, pedido, parcelas e PDF validado.
- Reserva/liquidação vinculam operações ao consumo; indisponibilidade ou retorno incerto mantêm uma evidência conservadora e bloqueiam repetição automática.
- `uv run pytest tests/test_dte.py tests/test_dte_access.py tests/test_dte_dispatch.py tests/test_integra_client.py tests/test_integra_dctfweb.py tests/test_integra_parcelamento.py tests/test_parcelamento_operations.py -q`: **63 aprovados em 13,98 s**. Ruff dos módulos e testes envolvidos passou.

Limites: mocks e documentos sintéticos não homologam contrato, credenciais centrais, certificado, representação, tarifas ou serviços Serpro. Q-28 e uma autorização de custo imediatamente anterior são necessários para o piloto; Q-36 impede ampliar PARCSN. A etapa 08 permanece em andamento.

## V-033 — Etapa 10: contratação, tokens e cobrança local

Data: 19/09/2026. Ambiente: macOS local e banco de teste. Sem conta, credencial, sandbox, cliente, cobrança, webhook ou custo Asaas real.

- D-76/D-79 resolvem Q-01–Q-06 para implementação: 7 dias de carência, somente leitura, reativação após pagamento, retorno a somente leitura por estorno/disputa, teste de 14 dias, fechamento no dia 1, vencimento no dia 10 e contrato manual operado pela Mewstack com auditoria.
- O código local contém livro de preços congelado por contrato, franquia/peso de token inteiro por módulo, teto mensal, reserva/liquidação idempotentes, fatura por competência e eventos de pagamento duplicados/fora de ordem. O webhook Asaas não altera contratos manuais.
- `uv run pytest tests/test_platform_billing.py tests/test_platform_payments.py tests/test_token_billing.py tests/test_cica_contract_mfa.py tests/test_cica_operation_access.py -q`: **44 aprovados e 1 ignorado em 13,37 s**. O skip é o cenário de concorrência de locks, coberto na validação PostgreSQL histórica. `uv run ruff check src/apps/platform tests/test_platform_billing.py tests/test_platform_payments.py tests/test_token_billing.py`: aprovado.

Limites: não há cliente Asaas para criar clientes/cobranças nem prova de Pix, boleto, cartão, atraso, estorno ou evento real. Q-08 ainda precisa fixar limites de IA/Triagem; sandbox/contrato e amostra autorizada estão em Q-28. A etapa 10 permanece em andamento.

## V-032 — Etapa 05: proveniência e escopo do conhecimento

Data: 19/09/2026. Ambiente: macOS local, CPython 3.12.13 e banco de teste. Sem dados de cliente, egressão Claude, credenciais, download de modelo, GPU, treinamento ou custo externo.

- D-89 autoriza os metadados de área, empresa e período nas fontes de conhecimento e exemplos de treinamento, como implementação direta da cobertura contábil, fiscal e folha de D-52. A migração `intelligence.0027` preenche registros existentes com área geral; empresa e período permanecem opcionais.
- A recuperação agora filtra fontes aprovadas para o escritório e, quando há empresa na conversa, aceita somente fontes globais ou dessa empresa, priorizando as específicas. Sem empresa, fontes específicas são excluídas. A validação impede relacionar fonte ou exemplo a empresa de outro escritório.
- O manifesto QLoRA inclui os metadados de proveniência no hash do corpus. O runner os valida, mas não os coloca no texto enviado ao treinamento; apenas pergunta, resposta e referências aprovadas compõem o dataset.
- `uv run ruff check src/apps/intelligence runtime/trainer tests/test_intelligence_sync_django.py tests/test_intelligence_training_django.py`: aprovado. `uv run python manage.py makemigrations --check --dry-run`: sem alterações. `uv run pytest tests/test_intelligence_sync_django.py tests/test_intelligence_training_django.py tests/test_training_runner.py -q`: **26 aprovados em 12,53 s**.
- D-90 adicionou os hashes SHA-256 de manifesto e adaptador, o modelo base e a versão do adaptador a `EvaluationRun` e `ModelVersion`. A publicação exige correspondência integral se a versão declarar um artefato; uma avaliação de hash diferente é recusada. `uv run pytest tests/test_intelligence_training_django.py tests/test_training_runner.py -q`: **20 aprovados em 6,99 s**.
- D-91 acrescentou `dataset_split` aos exemplos e `evaluation_manifest_sha256` à avaliação. O exportador seleciona `training` por padrão ou `evaluation` explicitamente; o runner QLoRA recusa qualquer linha fora de `training`. `uv run pytest tests/test_intelligence_training_django.py tests/test_intelligence_commands_django.py tests/test_training_runner.py -q`: **34 aprovados em 13,18 s**.
- D-92 acrescentou `rollback_model`, que só reativa uma versão do mesmo escritório após validar sua avaliação e a proveniência declarada; a operação grava auditoria e nunca inicia treino. `uv run pytest tests/test_intelligence_training_django.py -q`: **17 aprovados em 7,01 s**.
- Revalidação integral: `uv run ruff check .`, `uv run python manage.py check`, `uv run python manage.py makemigrations --check --dry-run` e `uv run pytest -q` passaram. A suíte fechou em **754 aprovados, 3 ignorados e 8 subtestes em 28,01 s**; os skips continuam sendo Playwright Python opcional, OCR português local indisponível e concorrência de locks coberta no PostgreSQL histórico.

Limites: isto não comprova cobertura de corpus para as três áreas, curadoria humana, anonimização de todos os casos, conjunto independente de avaliação, artefato de adaptador treinado, publicação/rollback real ou egressão autorizada. Q-08, Q-09, Q-11 e Q-34 continuam abertos; a etapa 05 permanece em andamento.

## V-031 — Análise consolidada e revalidação local

Data: 19/09/2026. Ambiente: macOS local, CPython 3.12.13 criado por `uv sync --locked --all-extras`; checkout inicialmente limpo. Não houve deploy, conexão a fornecedor, leitura de dado de cliente, uso de credencial, cobrança ou custo externo.

- A análise de documentação e código está em [docs/planejamento/analise-projeto-2026-09-19.md](docs/planejamento/analise-projeto-2026-09-19.md). Ela confirma que as etapas 00–03 encerraram somente a implementação/validação local e que a etapa 04 depende do contrato Siescon Q-33.
- `uv run ruff check .` inicialmente reportou 16 E501 em `agent_v2.py`, `triage/forms.py`, `triage/services.py` e `urls_agent_v2.py`. Foram aplicadas quebras de linha sem mudança de regra. A primeira suíte completa revelou ainda que o modo de biblioteca interna apagava `folder_template`, embora o padrão deva ser preservado para a configuração futura de Windows. O formulário agora mantém o padrão; nenhuma rota, modelo ou decisão de produto foi alterado. A reexecução do Ruff retornou `All checks passed!`.
- `uv run python manage.py check`: sem problemas (0 silenciados). `uv run python manage.py makemigrations --check --dry-run`: `No changes detected`.
- `uv run pytest tests/test_edge_agent.py tests/test_triage_windows_paths.py tests/test_reconciliation_module.py -q`: **51 aprovados, 1 ignorado e 6 subtestes aprovados em 7,46 s**. O skip é o OCR em português indisponível nesta estação, não uma integração externa.
- Reexecução integral: `uv run pytest -q`: **747 aprovados, 3 ignorados e 8 subtestes aprovados em 26,90 s**. Os skips são Playwright Python opcional, OCR português local indisponível e concorrência de locks, que possui validação PostgreSQL histórica própria.

Limites: a revalidação macOS não repete as provas históricas com PostgreSQL, Redis, Docker/WSL ou instalador Windows. Testes locais não homologam Siescon nem substituem o piloto da etapa 12.

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
