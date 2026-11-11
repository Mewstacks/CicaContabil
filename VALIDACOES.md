## V-140 - Distribuicao administrativa de atividades

Data: 23/09/2026. Proprietario e administrador agora veem, somente no proprio escritorio,
a distribuicao de atividades abertas por membro ativo, com contagens separadas de atraso e
impedimento. Cada pessoa abre a fila filtrada por responsavel; atividades sem responsavel tem
recorte proprio. Membros sem atividade seguem exibidos. A superficie afirma explicitamente
que atribuicao e estado nao medem produtividade, disponibilidade ou qualidade individual.

Validacao: 81 testes focados em 52,78 s, incluindo administrador, equipe, atribuicao,
sem responsavel e filtros; Ruff, MyPy, `manage.py check` e migracoes limpas; regressao
integral com 863 aprovados, 2 ignorados e 11 subtestes em 79,33 s. A referencia publica do
Karbon para dashboards de trabalho pendente e planejamento de recursos, junto da referencia
publica do Asana para clicar em pessoa e ver atribuicoes, orientou a navegacao de detalhe;
o CICA nao infere horas, pontos, capacidade maxima ou avaliacao de desempenho. Watermelon nao
retornou bloco ou dashboard pertinente. A auditoria pelas Web Interface Guidelines atualizadas
nao encontrou violacao material: links e tabelas sao semanticos, filtros mantem URL, controles
tem rotulos e a tabela usa a responsividade existente. O Playwright MCP retornou `Transport
closed` antes de abrir aba; nao houve inspecao desktop/mobile, teclado, console ou captura.
Nenhuma fonte externa, custo ou publicacao foi acionado.

## V-139 - Prioridades completas na area de trabalho

Data: 23/09/2026. A tela inicial passou a calcular sobre todas as atividades abertas e
autorizadas, e nao somente as seis exibidas, os grupos de atraso, vencimento hoje, proximos
sete dias, impedidas e fonte indisponivel. Cada grupo abre a fila pelo filtro correspondente;
os grupos nao sao somados porque podem se sobrepor. A tabela da area de trabalho exibe os
estados de trabalho, processamento, obrigacao e atualizacao. A central recebeu filtro proprio
de atualizacao da fonte e a paginacao preserva os recortes.

Validacao: 80 testes focados em 53,80 s, incluindo escopo, atraso, vencimento, fonte
indisponivel e filtros; Ruff, MyPy, `manage.py check` e migracoes limpas; regressao integral
com 862 aprovados, 2 ignorados e 11 subtestes em 81,47 s. O padrao de filtro por data e
contexto foi comparado com a documentacao publica do Karbon, e o resumo agregado de folha do
Xero confirmou a separacao de valores e fontes. Watermelon nao retornou bloco ou dashboard
pertinente. A auditoria pelas Web Interface Guidelines atualizadas nao encontrou violacao
material: links preservam URL, tabela e filtros usam elementos semanticos, campos tem rotulos
e a tabela usa a adaptacao responsiva existente. O Playwright MCP retornou `Transport closed`
antes de abrir aba; nao houve inspecao desktop/mobile, teclado, console ou captura nesta
entrega. Nenhuma fonte externa, custo ou publicacao foi acionado.

## V-138 - Da divergencia de folha para a atividade responsavel

Data: 23/09/2026. A comparacao de folha ganhou um destino operacional explicito: abre a
fila com empresa, area `payroll` e competencia da fotografia, todos na URL. A comparacao
nao altera atividade. A fila aceita filtro mensal, preserva esse recorte entre paginas e
mostra erro em linha para competencia invalida, sem interpretar outro mes nem alterar o
recorte solicitado.

Validacao: 79 testes focados em 57,78 s, incluindo o link de tratamento, filtro valido e
competencia invalida; Ruff, MyPy, `manage.py check` e migracoes limpas; regressao integral
com 861 aprovados, 2 ignorados e 11 subtestes em 92,53 s. A referencia oficial do Karbon
para prazos internos/externos e filtros de trabalho confirmou a escolha de manter o contexto
na URL; a referencia oficial do Xero confirmou o uso de filtros para recortes de folha. A
consulta Watermelon nao retornou bloco ou dashboard aplicavel. Auditoria das Web Interface
Guidelines atualizadas: controles tem rotulos e autocomplete, filtro e paginacao preservam
estado na URL, o erro indica correcao e o link usa elemento semantico; sem violacao material.
O Playwright MCP retornou `Transport closed` antes de abrir aba; nao houve inspecao
desktop/mobile, teclado, console ou captura nesta entrega. Nenhuma fonte externa, custo ou
publicacao foi acionado.

## V-137 - Comparacao explicavel de fontes da folha

Data: 23/09/2026. A ficha da empresa passou a permitir a selecao de duas fotografias de
folha da mesma empresa e competencia. A comparacao mostra fonte, totais agregados,
metricas ausentes e diferencas acima da tolerancia; nao calcula folha, nao inclui dado
individual de trabalhador e nao consulta fonte externa. A escolha fica limitada ao
portfolio ja autorizado. A tabela recebeu a classe responsiva da ficha da empresa e o
botao passa para `Comparando...` enquanto a nova pagina e carregada.

Validacao: 72 testes focados em 53,27 s, cobrindo a comparacao, o escopo e os fluxos
relacionados; Ruff, MyPy, `manage.py check` e migracoes limpas; regressao integral com
861 aprovados, 2 ignorados e 11 subtestes em 80,06 s. A pesquisa de produto usou a
referencia oficial do Xero para relatorio agregado de folha e reconciliacao de valores,
adaptada a fontes do CICA sem copiar interface. UI/UX Pro Max orientou a escolha explicita
das fontes e a tabela densa; Watermelon nao devolveu bloco pertinente. A auditoria contra
as Web Interface Guidelines atualizadas nao encontrou violacao material: campos tem
rotulos, erros ficam em linha e recebem foco, estado esta na URL e a tabela e semantica e
responsiva. O Playwright MCP retornou `Transport closed` antes de abrir aba nas duas
tentativas; nao houve inspecao desktop/mobile, teclado, console ou captura nesta entrega.
Nenhuma folha real, ERP, fonte externa, custo ou publicacao foi acionado.

## V-136 - Exportacao do Copiloto pelo renderizador JavaScript

Data: 23/09/2026. A exportacao PDF/XLSX de uma resposta do Copiloto agora prepara uma
fotografia restrita, chama somente o renderizador Node/TypeScript e persiste a trilha de
auditoria com solicitante, empresa, hashes de fotografia e arquivo. A falta de URL interna
ou segredo torna a operacao explicitamente indisponivel; nao ha fallback de geracao Python.
`apps.intelligence.reports` deixou de importar ou gerar com ReportLab/OpenPyXL. Leitura de
planilhas e arquivos em outros modulos nao foi removida por esta mudanca.

Validacao: 21 testes Django focados em 51,84 s, incluindo escopo, CSRF, fotografia,
imutabilidade, hash, erro do renderizador e indisponibilidade sem configuracao; 8 testes
Node/TypeScript aprovados; Ruff, MyPy, `manage.py check` e migracoes limpas; busca sem
ocorrencia das bibliotecas legadas no caminho do Copiloto; regressao integral com 860
aprovados, 2 ignorados e 11 subtestes em 82,24 s. Nenhum renderizador, segredo, chamada
externa, publicacao ou ambiente real foi configurado nesta entrega.

## V-135 - Editor visual versionado do mapa DRE

Data: 23/09/2026. Proprietario e administrador agora configuram conta, grupo e sinal do
mapa DRE pela interface. O formulario exige pelo menos uma conta e recusa conta repetida,
grupo ausente e sinal invalido. Um salvamento cria uma versao completa nova em transacao,
preserva as linhas anteriores, deixa somente a nova ativa e registra o evento de auditoria.
O formulario tem rotulos acessiveis, erros em linha, foco no primeiro erro retornado e aviso
para navegacao com edicao pendente. A pesquisa de interface usou UI/UX Pro Max; Watermelon
nao retornou entrada pertinente para tabela de configuracao financeira; a referencia oficial
do QuickBooks para plano de contas orientou a tabela por conta sem copiar interface.

Validacao: 2 testes diretos de criacao/versionamento e duplicidade; 70 testes focados de
editor e workspace em 55,95 s; Ruff, MyPy, `manage.py check` e migracoes limpas; regressao
integral com 860 aprovados, 2 ignorados e 11 subtestes em 82,86 s. Auditoria manual contra
as Web Interface Guidelines atualizadas nao encontrou violacao material no arquivo alterado.
O Playwright MCP retornou `Transport closed` antes de abrir uma aba; portanto nao houve
inspecao visual desktop/mobile nem captura de tela nesta entrega.

## V-134 - Fila duravel de relatorios financeiros

Data: 23/09/2026. DRE e caixa agora enfileiram uma solicitacao persistida antes de
chamar o renderizador Node. A fotografia criptografada e seu hash ficam fixados no
pedido; Celery usa lease, retoma trabalho abandonado e revalida a associacao ativa do
solicitante e o acesso atual a empresa. O PDF/XLSX e salvo em armazenamento privado, e
o download revalida a permissao; arquivo ausente muda o pedido para falha em vez de
expor erro interno.

Validacao: 5 testes focados cobriram enfileiramento, renderizacao, revogacao de acesso,
download privado e indisponibilidade; Ruff, MyPy, `manage.py check` e migracoes limpas
passaram. A regressao integral aprovou 858 testes, ignorou 2 e executou 11 subtestes em
86,79 s. UI/UX Pro Max orientou retorno explicito apos envio e estados contextuais; a
busca Watermelon nao encontrou referencia verificavel. A estrutura de estados e
fotografia foi inspirada na administracao de relatorios do Google Analytics
(https://support.google.com/analytics/answer/13722168?hl=pt-BR), adaptada ao CICA.
A auditoria Web Interface Guidelines nao encontrou violacao material no template:
formularios mantem CSRF e botoes semanticos, o download e link e a tabela tem cabecalhos.
O Playwright MCP retornou `Transport closed`; desktop, mobile, teclado e console nao
foram inspecionados nesta entrega. Nenhuma URL interna, segredo, navegador ou chamada
real foi configurado ou acionado.

## V-133 - Rota??o segura do segredo do renderizador

Data: 23/09/2026. O servi?o Node de relat?rios agora aceita o segredo ativo e, somente durante a rota??o, um segredo anterior. As compara??es permanecem em tempo constante para cada segredo configurado; cabe?alho ausente, m?ltiplo ou desconhecido continua recusado. Django usa exclusivamente `CICA_REPORTING_SHARED_SECRET`, mesmo quando `CICA_REPORTING_PREVIOUS_SHARED_SECRET` estiver definido.

Valida??o: TypeScript e 8 testes Node aprovados; 6 testes do cliente Django, Ruff e MyPy aprovados. Regress?o integral: 855 aprovados e 2 ignorados em 82,28 s. Nenhuma URL interna, segredo, navegador ou renderiza??o de produ??o foi configurado ou acionado. A fila Celery de relat?rios continua pendente.

## V-132 - Assinatura exclusiva NFS-e

Data: 23/09/2026. Uma assinatura com somente o m?dulo NFS-e habilitado explicitamente passa a abrir diretamente a central NFS-e. A navega??o remove vis?o geral, atividades e modelos operacionais; o acesso direto ? fila e aos seus detalhes ? recusado. Empresas, certificados, equipe e configura??o inicial permanecem como apoio necess?rio ao NFS-e.

Valida??o focal: Ruff e MyPy aprovados; 80 testes de workspace, permiss?es e navega??o aprovados. Regress?o integral: 854 aprovados e 2 ignorados em 79,79 s. A auditoria manual contra as Web Interface Guidelines consultadas em 23/09/2026 n?o encontrou viola??o material nos templates e na navega??o alterados: os destinos seguem links sem?nticos e n?o foram criados controles novos. Refer?ncias de dire??o: navega??o por fun??o do Microsoft Dynamics, separa??o entre acesso a produto e permiss?es no Atlassian, e o fluxo de trabalho por cliente/prazo do Karbon. Watermelon n?o retornou bloco ou dashboard equivalente. O Playwright MCP retornou `Transport closed`; a inspe??o visual desktop/mobile permanece pendente e nenhuma foi alegada.

## V-131 - Acumulador manual n?o classifica NFS-e por omiss?o

Data: 23/09/2026. Conforme D-113, uma regra de acumulador sem crit?rios passa a ser somente cat?logo e hist?rico: ela n?o pode ser usada como curinga para classificar todas as NFS-e da empresa. A classifica??o autom?tica exige correspond?ncia expl?cita; uma nota sem crit?rio continua em revis?o humana. A prova de integra??o cria o acumulador pela tela, confirma o hist?rico manual e verifica que uma NFS-e posterior sem crit?rio n?o ganha acumulador sugerido.

Valida??o focal: Ruff e MyPy aprovados; 94 testes NFS-e, intelig?ncia e telas Hub aprovados. Regress?o integral: 852 aprovados e 2 ignorados em 76,03 s. A valida??o visual continua pendente porque o transporte Playwright MCP est? indispon?vel. N?o houve backup, banco Dom?nio, rotina autom?tica, arquivo ou credencial real.

## V-130 - Historico completo de pacotes NFS-e

Data: 23/09/2026. A aba de pacotes de conferencia NFS-e deixou de limitar a consulta aos 100 registros mais recentes. A paginacao conserva a aba na URL, mostra navegacao explicita e foi exercitada com 101 pacotes sinteticos. Validacao focal: 69 testes aprovados; Ruff e MyPy aprovados. Watermelon nao retornou referencia equivalente; UI/UX Pro Max orientou a manutencao da tabela responsiva existente. A inspe??o visual continua pendente pelo transporte Playwright MCP indisponivel.

## V-128 - Pacote NFS-e classificado como conferencia

Data: 23/09/2026. Pesquisa oficial confirmou a existencia de rotinas automaticas e importadores no DomÃ­nio, mas nao revelou o schema `.dom`, o layout de XML NFS-e com acumuladores nem um retorno de importacao. Conforme D-112 e Q-39, o ZIP NFS-e foi reclassificado como pacote privado de conferencia: preserva XML, manifesto, classificacoes e hash, mas nao e anunciado como importavel. A rota de confirmacao de importacao retorna indisponibilidade e preserva o estado do pacote; a tela nao oferece confirmacao.

Validacao focal: 68 testes aprovados; Ruff e MyPy aprovados. Referencias oficiais: [importacao por rotina](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=7247) e [rotinas automaticas da Escrita](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=4364). Nenhuma fonte, backup, rotina, arquivo ou credencial real foi usada. A repeticao visual continua pendente enquanto o transporte Playwright MCP estiver indisponivel.

## V-127 - Historico unico de acumuladores NFS-e

Data: 23/09/2026. O historico da aba NFS-e Acumuladores passou a reunir registros imutaveis da fotografia DomÃ­nio Web, do cadastro manual e da decisao humana. Cada item mantem empresa, codigo, origem, instante e referencia de origem; a regra operacional e a observacao agregada permanecem separadas do evento historico. Registros antigos de fotografia ainda aparecem como compatibilidade, mesmo se tiverem sido criados antes do novo evento.

Validacao focal: 70 testes aprovados para NFS-e, backup e exportacao; Ruff e MyPy aprovados; migracoes sem alteracoes pendentes. Watermelon UI nao retornou composicao equivalente. A auditoria manual contra as Web Interface Guidelines revisou o formulario rotulado, a tabela semantica, a paginacao por URL, o estado vazio e o anuncio contextual de contagem; nao encontrou violacao material nos arquivos alterados. O Playwright MCP continua com transporte encerrado, portanto a repeticao visual desktop/mobile desta alteracao segue pendente. Nenhum backup ou DomÃ­nio real foi acessado.

## V-126 - NFS-e Dom?nio Web: catalogo, historico e pacote auditavel

Data: 23/09/2026. O CICA agora recebe o catalogo normalizado de acumuladores extraido uma unica vez pelo agente controlado do backup Dom?nio Web, com empresa, lote, origem e instante da fotografia. O usuario pode incluir acumuladores para classificacoes futuras pela tela; uma decisao humana cria evidencia de classificacao e atualiza a observacao historica.

A exportacao cria um ZIP privado imutavel com XMLs e manifesto de classificacao, fotografia dos documentos e hash. Os estados `arquivo gerado`, `arquivo baixado` e `importacao confirmada` sao independentes e auditados. Confirmacao continua humana: nao representa retorno automatico do Dom?nio. Caso o arquivo privado nao exista mais, o sistema nao marca download nem falha com erro interno; solicita a geracao de outro pacote.

Validacao local: 68 testes focados aprovados e regressao integral com 851 aprovados e 2 ignorados; Ruff e MyPy aprovados; `makemigrations --check --dry-run` sem alteracoes. A inspe??o Playwright desktop confirmou a aba Exportacoes, seus estados e controles; a sessao do MCP encerrou inesperadamente antes da nova interacao de download e da inspe??o mobile, portanto essa parte segue pendente de repeticao. Nenhum backup real, banco Dom?nio, rotina Windows, chamada externa ou importacao autom?tica foi executado.

## V-125 - Fotografia de acumuladores do Dominio Web (23/09/2026)

- O agente de backup aceita somente a capacidade allowlisted `accumulator_catalog`. Cada registro e imutavel, vinculado a empresa, fonte, lote e data da fotografia; o catalogo passa a ser elegivel para a decisao humana de NFS-e da mesma empresa.
- Uma fotografia de backup DomÃ­nio Web concluida bloqueia novo envio para a mesma fonte. O arquivo e a chave continuam descartados ao termino; ficam lote, hash, capacidades, contagens, erros e catalogo normalizado.
- A navegacao NFS-e ganhou a aba Acumuladores. Ela pagina o catalogo historico e aplica a mesma carteira do usuario antes de renderizar cada registro.
- Validacao: 65 testes das pontas de backup e workspace aprovados; regressao integral anterior com 845 aprovados e 2 ignorados; Ruff, MyPy, Django e migracoes aprovados. Playwright conferiu o catalogo em desktop e 375 px, sem overflow ou erro de console, e encerrou navegador e servidor isolado.
- Limite: o extrator real do arquivo DomÃ­nio Web, o formato de exportacao para a rotina automatica e a confirmacao da importacao dependem de layout/arquivo autorizado e homologacao externa. Nenhum backup real, chamada DomÃ­nio ou rotina automatica foi executada.

## V-124 - Mapa DRE versionado por importacao (23/09/2026)

- A importacao de mapa DRE cria uma versao nova e ativa somente depois de validar todas as contas, grupos e sinais. O conjunto anterior e suas linhas permanecem preservados, apenas deixa de ser ativo. O bloqueio transacional da organizacao tambem protege a primeira versao contra importacoes concorrentes que ainda nao teriam linhas de mapa para bloquear.
- A criacao trava os mapas existentes do escritorio dentro da transacao antes de calcular a proxima versao e trocar a versao ativa.
- Validacao: quatro testes de importacao financeira aprovados, incluindo preservacao de linhas da versao anterior; Ruff e MyPy aprovados.
- A tela de onboarding documenta o formato `conta`, `grupo` e `sinal`; a revisao por Playwright confirmou leitura, abertura por teclado, foco, desktop e 375 px sem overflow ou erros de console. A revisao pelas Web Interface Guidelines nao encontrou violacao material no trecho alterado.
- Regressao final: `uv run pytest` concluiu com 845 aprovados e 2 ignorados; `reporting`: TypeScript, 6 testes Node e `npm audit --omit=dev` aprovados.
- Limite: a configuracao e feita por CSV/XLSX no onboarding; a edicao visual por conta ainda nao foi criada.

## V-123 - Importacao financeira verificada no onboarding (23/09/2026)

- O onboarding aceita CSV/XLSX para `Saldos para DRE` e `Cenario de caixa`, preservando a previa e a confirmacao do arquivo antes de qualquer alteracao.
- Saldos sao agrupados por empresa, competencia e referencia; repeticao da mesma origem nao duplica fotografia. Caixa exige saldo inicial e movimento identificado, mantem as tres visoes separadas e recusa arquivo inteiro se houver dupla deducao, divergencia de saldo inicial ou linha invalida.
- Validacao: 67 testes focados aprovados; Ruff, MyPy, Django check e conferencia de migracoes aprovados.
- UI: instrucao de colunas e valores permitidos validada em Playwright desktop e 375 px, sem overflow nem erro de console; navegador e servidor isolado encerrados. Watermelon ja havia sido consultado nesta frente e nao retornou catalogo verificavel; aplicados os mesmos padroes de divulgacao progressiva e texto tecnico contextual da V-122.
- Limite: importacao nao homologou layouts Dom?nio/Siescon nem executou conexao externa; cada fonte continua dependente do adaptador e contrato autorizados.

## V-122 - Consulta e exportacao financeira na ficha da empresa (23/09/2026)

- A ficha da empresa agora apresenta fotografias contabeis para DRE e cenarios de caixa em visoes separadas, com origem, referencia, mapa DRE ativo e estado de dados insuficientes.
- A exportacao PDF/XLSX e somente POST, verifica a carteira da empresa novamente no servidor, exige o mapa ativo para DRE, gera pelo servico Node e registra hashes de entrada e saida sem valores no evento de auditoria.
- Validacao funcional: 62 testes de telas Hub aprovados; regressao completa `uv run pytest` - 841 aprovados, 2 ignorados em 73,95 s; GET de exportacao devolve 405, acesso cruzado devolve 404, ausencia do mapa devolve 409 e renderer ausente devolve 503.
- Validacao visual: Playwright no servidor isolado, desktop e 375 px; sem rolagem horizontal no celular, quatro controles de exportacao com 44 px de altura, foco visivel herdado e nenhum erro de console ao carregar a ficha. A tentativa de exportacao no ambiente sem renderer produziu o 503 esperado. Navegador e servidor foram encerrados.
- UX: aplicado `ui-ux-pro-max` (dados financeiros densos, tabela responsiva e foco visivel); a consulta Watermelon foi repetida para dashboards e blocos e nao encontrou entrada verificavel. Foram usadas como referencia estrutural as telas de relatorios e dashboards de Checkout.com e June pesquisadas no SaaSFrame: resumo contextual, tabelas compactas, acoes locais e estados vazios, adaptados a identidade existente.
- Auditoria Web Interface Guidelines: sem violacao material nos trechos adicionados; botoes semanticos em formul?rios POST, rotulos acessiveis por texto oculto, hierarquia h2/h3, estados vazios e foco `:focus-visible` global.

## V-121 - Contratos Node para DRE e caixa (23/09/2026)

- Adicionado o adaptador financeiro que converte fotografias contabeis e cenarios de caixa persistidos no contrato restrito do renderizador JavaScript.
- A DRE carrega a versao do mapa, a fonte e a lista de contas sem mapeamento; nestes casos sai como preliminar. O caixa identifica explicitamente a visao e nao o apresenta como consulta bancaria automatica.
- Validacao: 17 testes focados aprovados; regressao completa `uv run pytest` - 839 aprovados, 2 ignorados em 73,11 s. `ruff`, `mypy`, `manage.py check`, conferencia de migracoes, `npm run check`, `npm test` e validacao direta do contrato TypeScript aprovados.
- Limite: a solicitacao/exportacao dessas fotografias pela interface depende da proxima entrega de UI e de regras de permissao para os novos recursos.

## V-120 - Persistencia auditavel para saldos contabeis, DRE e cenarios de caixa (23/09/2026)

- Implementados registros aditivos por escritorio para fotografias de saldos contabeis, linhas de saldo, versoes de mapeamento da DRE, mapeamentos por conta e cenarios/movimentos de caixa.
- O servico financeiro grava a fotografia por origem e referencia de modo idempotente, registra auditoria sem expor valores monetarios, calcula a DRE somente com mapeamento do mesmo escritorio e usa o motor deterministico de caixa para projecoes persistidas.
- O modelo de movimentos impede dupla deducao quando uma retencao ja esta coberta pela provisao, mantendo simulacao, projecao e realizado como visoes distintas.
- Validacao: `uv run pytest tests/test_financial_models.py tests/test_dre.py tests/test_cash_projection.py tests/test_operational_center.py` - 16 aprovados; `uv run pytest` - 838 aprovados, 2 ignorados em 72,46 s. `ruff`, `mypy`, `manage.py check` e `makemigrations --check --dry-run` aprovados.
- Limite: ainda faltam a interface, a importacao homologada e a renderizacao Node desses dados; esta entrega estabelece o contrato persistente e os calculos verificaveis que elas consumirao.

## V-119 â€” Cadeia de dependÃªncias XLSX corrigida

Data: 23/09/2026. A auditoria de produÃ§Ã£o do renderizador Node deixou de apontar
vulnerabilidades. O lockfile fixa `uuid` 11.1.1 por `overrides`, mantendo ExcelJS 4.4.0.
A versÃ£o corrigida oferece entrada CommonJS, compatÃ­vel com o `require('uuid')` que
ExcelJS usa para gerar identificadores de formataÃ§Ã£o condicional.

- **Pesquisa:** o repositÃ³rio do ExcelJS continua em 4.4.0 e suas issues abertas ainda
  registram a dependÃªncia antiga; o advisory GHSA-w5hq-g745-h8pq informa correÃ§Ã£o a
  partir de uuid 11.1.1. A cadeia instalada tambÃ©m confirmou `tmp` 0.2.7, jÃ¡ acima da
  versÃ£o vulnerÃ¡vel citada em issues do ExcelJS.
- **Automatizado:** `npm ls exceljs uuid tmp --all` mostrou ExcelJS 4.4.0 com uuid
  11.1.1 aplicado; `npm audit --omit=dev` retornou **0 vulnerabilidades**. TypeScript e
  os seis testes Node, incluindo geraÃ§Ã£o XLSX e API autenticada, passaram.
- **Limites:** a atualizaÃ§Ã£o nÃ£o libera produÃ§Ã£o. Ainda faltam fila Celery e
  rotaÃ§Ã£o/revogaÃ§Ã£o do segredo; qualquer alteraÃ§Ã£o futura de ExcelJS, uuid ou lockfile
  precisa repetir a auditoria e as provas de renderizaÃ§Ã£o.

## V-118 â€” AÃ§Ã£o explÃ­cita para exportar relatÃ³rio

Data: 23/09/2026. A exportaÃ§Ã£o do Copiloto deixou de ser um link `GET`: cada formato
Ã© um botÃ£o em formulÃ¡rio `POST` com CSRF. Assim, uma navegaÃ§Ã£o, prÃ©-carregamento ou
verificador de links nÃ£o gera arquivo, fotografia ou evento de auditoria. O `GET` Ã©
recusado com 405 e a exportaÃ§Ã£o sÃ³ Ã© auditada depois do `POST` autorizado concluir.

- **Automatizado:** `tests/test_intelligence_views_django.py` e
  `tests/test_reporting_client.py` formam 17 cenÃ¡rios para o Copiloto e seu canal
  interno; cobrem formulÃ¡rio renderizado, `GET` sem registro, PDF/XLSX via `POST`,
  bloqueios de mÃ³dulo/escopo, renderer indisponÃ­vel e registros imutÃ¡veis. Ruff,
  MyPy, Django e `makemigrations --check --dry-run` passaram.
- **Interface:** `ui-ux-pro-max` recomendou confirmaÃ§Ã£o de submissÃ£o e foco visÃ­vel;
  o catÃ¡logo Watermelon nÃ£o retornou bloco pertinente. A referÃªncia de Asana orientou
  formatos explÃ­citos de exportaÃ§Ã£o. A Web Interface Guidelines atual foi revisada:
  botÃµes sem Ã­cone possuem rÃ³tulo, formulÃ¡rios preservam foco visÃ­vel, feedback de
  hover e sem `transition: all`.
- **Playwright:** com conta nÃ£o-demo e resposta sintÃ©tica em banco isolado, a tela foi
  inspecionada em desktop e 375 px. Os botÃµes PDF/XLSX tÃªm ao menos 44Ã—44 px, nÃ£o
  hÃ¡ overflow horizontal, `Tab` mostra foco de 3 px e o PDF foi baixado pelo `POST`;
  o registro gerado preservou fotografia e hashes de 64 caracteres. Navegador e
  servidor foram encerrados. O erro 404 observado antes de liberar o Copiloto na
  conta sintÃ©tica nÃ£o reapareceu na tela validada.

## V-117 â€” Fotografia imutÃ¡vel da exportaÃ§Ã£o de relatÃ³rios

Data: 23/09/2026. Cada PDF ou XLSX exportado pelo Copiloto agora cria um registro
imutÃ¡vel, restrito ao escritÃ³rio e criptografado, ligado Ã  resposta, empresa,
solicitante, formato e versÃ£o do modelo. A fotografia canÃ´nica dos dados enviados ao
renderizador e os hashes SHA-256 dela e do arquivo permitem verificar qual conteÃºdo foi
exportado sem gravar texto ou valores nos metadados de auditoria.

- **Automatizado:** `tests/test_intelligence_views_django.py` e
  `tests/test_reporting_client.py` aprovaram 17 cenÃ¡rios, incluindo PDF, XLSX,
  escopo entre escritÃ³rios, planilha sem fÃ³rmula, hash da fotografia, imutabilidade
  e ausÃªncia de registro quando o renderizador configurado responde indisponÃ­vel.
  Ruff, MyPy, `manage.py check` e `makemigrations --check --dry-run` passaram.
  A regressÃ£o integral fechou com **836 aprovados e 2 ignorados** em 70,38 s.
- **Limites:** a fotografia Ã© persistida depois da geraÃ§Ã£o bem-sucedida; ainda falta
  colocar solicitaÃ§Ãµes em Celery, definir rotaÃ§Ã£o/revogaÃ§Ã£o do segredo interno e
  resolver a dependÃªncia transitiva vulnerÃ¡vel do ExcelJS antes da ativaÃ§Ã£o em
  produÃ§Ã£o. NÃ£o houve chamada externa, arquivo de produÃ§Ã£o ou custo nesta prova.

# CICA â€” validaÃ§Ãµes e evidÃªncias

## V-116 â€” Base agregada para conferÃªncia de folha

Data: 23/09/2026. A central recebeu fotografias agregadas de folha por empresa,
competÃªncia e origem (ERP, documento, retorno oficial ou confirmaÃ§Ã£o humana). NÃ£o
hÃ¡ matrÃ­cula, CPF, nome ou rubrica individual nesse modelo. A comparaÃ§Ã£o determinÃ­stica
mostra diferenÃ§a em quadro, bruto, descontos, encargos e lÃ­quido; campo ausente fica
explÃ­cito e impede declarar igualdade. Fotografias de empresas ou competÃªncias distintas
nÃ£o podem ser comparadas.

- **Automatizado:** `tests/test_payroll.py` aprovou duas provas de tolerÃ¢ncia,
  diferenÃ§a, ausÃªncia de dado e isolamento por empresa. Ruff e MyPy dos modelos e
  motor passaram; a migraÃ§Ã£o aditiva `0046_payroll_period_snapshots` foi gerada e
  `makemigrations --check --dry-run` nÃ£o encontrou diferenÃ§a. O teste dirigido da
  ficha da empresa passou apÃ³s conferir a origem e a moeda formatada.
- **Interface:** em servidor Django isolado, com fotografia sintÃ©tica, Playwright
  inspecionou a ficha em desktop e 375 px. A tabela vira cartÃ£o no celular sem
  rolagem horizontal, preserva rÃ³tulos, totais e referÃªncia; o foco visÃ­vel e o
  console permaneceram sem erros. Navegador e servidor foram encerrados. A revisÃ£o
  da Web Interface Guidelines confirmou tabela semÃ¢ntica, cabeÃ§alhos com escopo,
  texto longo quebrÃ¡vel, Ã¢ncora com `scroll-margin-top`, estado textual alÃ©m da cor
  e nÃºmeros tabulares.
- **RegressÃ£o:** `uv run pytest` fechou com **834 aprovados e 2 ignorados** em
  71,10 s. Os skips permanecem restritos Ã  cobertura Python Playwright opcional e
  Ã  concorrÃªncia de locks conferida em PostgreSQL.
- **Entrada auditÃ¡vel:** `record_payroll_snapshot` valida a fotografia, registra uma
  Ãºnica vez a combinaÃ§Ã£o empresa/competÃªncia/origem/referÃªncia e retorna o mesmo
  registro em repetiÃ§Ã£o. A auditoria conserva origem, competÃªncia e quais mÃ©tricas
  existem, mas nÃ£o grava totais. Os trÃªs testes de `tests/test_payroll.py`, Ruff e
  MyPy passaram.
- **Limites:** ainda nÃ£o existe importador, tela, vÃ­nculo automÃ¡tico com atividade,
  leitura DomÃ­nio ou consulta eSocial/FGTS. Retorno oficial sÃ³ poderÃ¡ entrar quando
  houver fonte homologada; atÃ© lÃ¡, documento e confirmaÃ§Ã£o humana permanecem assim
  identificados e nÃ£o sÃ£o apresentados como consulta oficial.

## V-115 â€” Canal autenticado para o renderizador JavaScript

Data: 23/09/2026. Django e o renderizador Node passaram a exigir um segredo
compartilhado configurado, enviado somente no cabeÃ§alho interno e comparado em tempo
constante no serviÃ§o. URL ausente preserva a migraÃ§Ã£o aditiva; URL configurada sem
segredo, esquema nÃ£o HTTP(S), erro de serviÃ§o, MIME divergente ou hash divergente
interrompem a exportaÃ§Ã£o de forma explÃ­cita. NÃ£o hÃ¡ troca silenciosa para ReportLab
ou OpenPyXL depois que o motor JavaScript foi configurado.

- **Automatizado:** `npm run check` e `npm test` aprovaram seis testes no serviÃ§o,
  incluindo credencial ausente/incorreta. `tests/test_reporting_client.py` aprovou
  cinco testes de configuraÃ§Ã£o, esquema, segredo, tipo e hash; as 11 provas de
  exportaÃ§Ã£o do Copiloto permanecem aprovadas.
- **IntegraÃ§Ã£o local:** com segredo fictÃ­cio e serviÃ§o em `127.0.0.1:3082`, Django
  gerou XLSX pelo cliente interno e recebeu 6.806 bytes com assinatura `PK`. O
  processo e seu listener foram encerrados apÃ³s a prova; nÃ£o houve chamada externa,
  custo ou segredo real.
- **Limites:** o segredo de produÃ§Ã£o ainda depende do ambiente de homologaÃ§Ã£o e nÃ£o
  foi criado. Falta registrar a fotografia e o hash como evidÃªncia persistente,
  executar por Celery, definir rotaÃ§Ã£o/revogaÃ§Ã£o do segredo e resolver a dependÃªncia
  transitiva vulnerÃ¡vel do ExcelJS antes de ativar PDF/XLSX em produÃ§Ã£o.

## V-114 â€” Renderizador JavaScript de PDF e XLSX validado isoladamente

Data: 23/09/2026. O serviÃ§o Node/TypeScript de relatÃ³rios foi separado entre API
loopback e motor de renderizaÃ§Ã£o. Ele valida a fotografia antes de renderizar, mantÃ©m
filtros, versÃ£o, atualizaÃ§Ã£o da fonte e pendÃªncias no PDF/XLSX, gera o grÃ¡fico por
ECharts e devolve um hash auditÃ¡vel da solicitaÃ§Ã£o. A planilha neutraliza texto que
comece com operadores de fÃ³rmula e o PDF bloqueia requisiÃ§Ãµes de rede do navegador.

- **Automatizado:** `npm run check` e `npm test` passaram em `reporting/`: cinco
  testes cobrem SVG, fotografia invÃ¡lida, proteÃ§Ã£o de fÃ³rmula XLSX, narrativa e
  evidÃªncias, alÃ©m de corpo JSON com BOM na API. `tests/test_reporting_client.py`
  passou com quatro testes de URL, tipo e hash; `tests/test_intelligence_views_django.py`
  passou com 11 testes: o Copiloto usa o renderizador quando ele Ã© explicitamente
  configurado e devolve 503 se esse motor configurado falhar, sem trocar de motor.
  A prova local de PDF, com Edge jÃ¡ instalado indicado por
  `CICA_REPORTING_BROWSER_PATH`, retornou 57.445 bytes e hash
  `23da971b0a0e377937c90f03ddf87e89997995aab5a8d98f19bf12449a741a38`; o XLSX
  retornou 6.995 bytes e hash
  `4c905559667629dff2bc6e66751d4214643583da0f8e08eb2c69bae95c84568e`.
- **RegressÃ£o:** `uv run pytest` fechou com **830 aprovados e 2 ignorados** em
  70,51 s. Os dois skips continuam sendo Playwright Python opcional e concorrÃªncia
  de locks validada em PostgreSQL.
- **InspeÃ§Ã£o de arquivos:** o PDF fictÃ­cio de uma pÃ¡gina foi aberto localmente no
  navegador e exibiu tÃ­tulo, contexto, pendÃªncia, tabela e grÃ¡fico sem corte. O XLSX
  foi reaberto por ExcelJS no teste e por OpenPyXL na prova local; continha a aba
  `RelatÃ³rio CICA` e os valores esperados. O Ãºnico erro de console observado veio do
  servidor HTTP local de inspeÃ§Ã£o ao buscar um favicon inexistente, nÃ£o do arquivo.
- **Limites:** por padrÃ£o, Django ainda mantÃ©m ReportLab e OpenPyXL atÃ© que
  `CICA_REPORTING_URL` seja configurada; nessa configuraÃ§Ã£o, o cliente interno jÃ¡
  envia a fotografia restrita e verifica tipo e hash da resposta. Ainda nÃ£o hÃ¡
  autenticaÃ§Ã£o entre serviÃ§os, persistÃªncia da fotografia, autorizaÃ§Ã£o de download
  especÃ­fica do arquivo nem fila Celery integrada para este serviÃ§o. Nenhuma fonte,
  ERP, Serpro ou chamada cobrada foi usada. `npm audit --omit=dev` mantÃ©m duas vulnerabilidades
  moderadas transitivas de `uuid` por ExcelJS 4.4.0; o `audit fix --force` oferecido
  reduziria ExcelJS para 3.4.0, mudanÃ§a incompatÃ­vel. PDF/XLSX nÃ£o estÃ£o liberados
  para produÃ§Ã£o atÃ© atualizaÃ§Ã£o compatÃ­vel e integraÃ§Ã£o auditada.

## V-113 â€” Ficha da empresa integrada Ã  central e Ã  Triagem

Data: 23/09/2026. A ficha da empresa passou a reunir o trabalho operacional local
e os anexos da Triagem que pertencem Ã quela empresa. Atividades exibem prazo,
responsÃ¡vel e os estados independentes de trabalho, processamento, obrigaÃ§Ã£o e
atualizaÃ§Ã£o. A Triagem sÃ³ aparece quando o mÃ³dulo estÃ¡ habilitado e autorizado
para o perfil; cada registro mantÃ©m seu vÃ­nculo para o detalhe original.

- **Automatizado:** `tests/test_hub_workspace_views_django.py` fechou com **59
  aprovados** em 44,66 s, incluindo atividade visÃ­vel na ficha e Triagem oculta
  enquanto o mÃ³dulo nÃ£o estÃ¡ autorizado. Ruff, `manage.py check` e a verificaÃ§Ã£o
  de migraÃ§Ãµes passaram.
- **Interface:** Playwright, em SQLite temporÃ¡rio com dados fictÃ­cios, conferiu
  desktop e 375 px. No celular, as tabelas novas se apresentam como cartÃµes com
  rÃ³tulo por campo e aÃ§Ãµes de 44 px, sem rolagem horizontal da pÃ¡gina; o atalho de
  conteÃºdo manteve foco visÃ­vel e o console nÃ£o registrou erros. Navegador e
  servidor foram encerrados.
- **RevisÃ£o de interface:** `company_detail.html` e `operations.css` foram
  conferidos contra as Web Interface Guidelines atualizadas: cabeÃ§alhos de tabela
  tÃªm escopo, aÃ§Ãµes sÃ£o links semÃ¢nticos, estados preservam texto, conteÃºdo longo
  pode quebrar em telas estreitas e a paginaÃ§Ã£o permanece na URL. Watermelon nÃ£o
  retornou componente aplicÃ¡vel; a composiÃ§Ã£o preserva o padrÃ£o de painÃ©is e
  tabelas do CICA, com referÃªncia de hierarquia operacional de SaaSFrame.
- **Limites:** esta ligaÃ§Ã£o nÃ£o deduz que um anexo resolve uma atividade nem altera
  o estado da Triagem. NFS-e, ConciliaÃ§Ã£o, Radar, Copiloto, folha, DRE e caixa ainda
  precisam de vÃ­nculos explÃ­citos e das respectivas evidÃªncias.

## V-112 â€” Fundamentos locais de fechamento, capacidade, caixa, DRE e relatÃ³rios

Data: 23/09/2026. A central passou a consolidar estados de fechamento sem reduzir
fonte indisponÃ­vel a ausÃªncia de pendÃªncia. O modelo de atividade pode exigir
processamento fechado. A capacidade comercial conta membros ativos e raÃ­zes de CNPJ
ativas, preservando empresas sem raiz vÃ¡lida como pendÃªncia de cadastro. O motor de
caixa separa simulaÃ§Ã£o, projeÃ§Ã£o e realizado em centavos e recusa dupla deduÃ§Ã£o de
retenÃ§Ã£o. O motor de DRE exige mapeamento explÃ­cito e apresenta contas sem grupo.

- **RelatÃ³rios JavaScript:** o serviÃ§o Node/TypeScript compilou e respondeu localmente
  Ã  geraÃ§Ã£o SVG com fotografia validada e hash de saÃ­da. ECharts e Puppeteer foram
  atualizados. O audit ainda aponta duas vulnerabilidades moderadas transitivas do
  ExcelJS; a correÃ§Ã£o oferecida exige downgrade incompatÃ­vel, portanto PDF/XLSX nÃ£o
  estÃ£o liberados para produÃ§Ã£o nesta evidÃªncia.
- **Automatizado:** testes focados de central, caixa e DRE aprovados; Ruff, MyPy dos
  novos motores, Django e migraÃ§Ãµes sem diferenÃ§as aprovados. A regressÃ£o integral
  fechou com **823 aprovados e 2 ignorados** em 69,25 s.
- **ConfiguraÃ§Ã£o:** o diagnÃ³stico inicial passou a separar a operaÃ§Ã£o independente
  das condiÃ§Ãµes de fonte, equipe e limites. A pÃ¡gina foi inspecionada por Playwright
  em 1440 px e 375 px, com foco visÃ­vel no atalho de conteÃºdo, sem rolagem horizontal
  e sem erros de console. A tela usa dados fictÃ­cios em SQLite; navegador e servidor
  locais foram encerrados ao fim da prova.
- **Limites:** estes sÃ£o motores e contratos locais. NÃ£o provam preÃ§os, cobranÃ§a,
  extraÃ§Ã£o DomÃ­nio, Siescon, Serpro, transmissÃ£o, recebÃ­veis bancÃ¡rios, cÃ¡lculo fiscal
  oficial ou DRE homologada contra relatÃ³rios do ERP.

## V-111 â€” ObservaÃ§Ãµes de fonte e reabertura da central operacional

Data: 23/09/2026. A central agora preserva cada resultado de leitura de fonte em
registro imutÃ¡vel, separado de confirmaÃ§Ã£o humana. Uma leitura bem-sucedida atualiza
os estados informados; uma indisponibilidade nÃ£o os substitui por ausÃªncia de
pendÃªncia, apenas marca a atividade como indisponÃ­vel. Se uma leitura confiÃ¡vel
indicar reabertura ou obrigaÃ§Ã£o rejeitada depois da conclusÃ£o, a atividade volta a
pendente e a conclusÃ£o anterior permanece na trilha operacional.

- **Automatizado:** 6 testes de `tests.test_operational_center` aprovados; `ruff`,
  `mypy` de modelos e operaÃ§Ãµes, Django e migraÃ§Ãµes sem diferenÃ§as aprovados.
- **Interface:** Playwright exibiu fonte, referÃªncia, versÃ£o e momento da leitura no
  detalhe da atividade; em 375 px a pÃ¡gina nÃ£o teve rolagem horizontal e o console
  permaneceu sem erros. A aba e o servidor local foram encerrados.
- **Limites:** nÃ£o houve leitura externa. DomÃ­nio, Siescon e Serpro ainda precisam
  alimentar este contrato somente apÃ³s suas respectivas homologaÃ§Ãµes tÃ©cnicas.

## V-110 â€” Modelos versionados e geraÃ§Ã£o auditÃ¡vel da central operacional

Data: 23/09/2026. Em base SQLite temporÃ¡ria e fictÃ­cia, sem rede externa, foram
validados os modelos de atividade mensais, a atribuiÃ§Ã£o explÃ­cita por empresa e a
geraÃ§Ã£o idempotente por competÃªncia. Cada ocorrÃªncia mantÃ©m a versÃ£o e a fotografia
do modelo usada na criaÃ§Ã£o; uma nova versÃ£o nÃ£o altera o histÃ³rico nem passa a gerar
atividades sem atribuiÃ§Ã£o explÃ­cita. A atribuiÃ§Ã£o pode ser pausada ou retomada, com
evento de auditoria e sem apagar as ocorrÃªncias jÃ¡ criadas.

- **Automatizado:** `tests.test_operational_center` aprovou 5 testes, cobrindo acesso
  administrativo, geraÃ§Ã£o repetida, versÃµes e pausa auditÃ¡vel. `ruff`, `mypy`,
  `manage.py check`, `makemigrations --check --dry-run` e `git diff --check` foram
  aprovados. A regressÃ£o integral fechou com **814 aprovados e 2 ignorados**.
- **Interface:** Playwright no servidor Django local e isolado, usando dados
  fictÃ­cios: modelo, atribuiÃ§Ã£o, geraÃ§Ã£o e repetiÃ§Ã£o; pausa exibindo retomada; desktop
  e 375 px em tema escuro e movimento reduzido. Foco inicial no atalho de conteÃºdo,
  foco visÃ­vel, largura da pÃ¡gina igual Ã  largura do cliente e console sem erros. A
  aba e o servidor temporÃ¡rios foram encerrados.
- **Auditoria de interface:** revisÃ£o de `activity_models.html` e `activities.css`
  contra as Web Interface Guidelines atuais: controles tÃªm rÃ³tulos, aÃ§Ãµes usam
  botÃµes, formulÃ¡rios tÃªm erros no campo, estrutura usa regiÃµes e tabela semÃ¢nticas,
  e a aÃ§Ã£o reversÃ­vel oferece retomada explÃ­cita.
- **Limites:** a geraÃ§Ã£o Ã© local e intencionalmente nÃ£o pressupÃµe prazo legal,
  obrigaÃ§Ã£o, ERP ou fonte externa. Reabertura por retificaÃ§Ã£o, observaÃ§Ãµes de fonte,
  fechamento completo, DRE, caixa, folha, integraÃ§Ãµes e assistente de configuraÃ§Ã£o
  permanecem pendentes nesta frente.

## V-109 â€” Base local da central operacional

Data: 23/09/2026. Em base SQLite temporÃ¡ria e fictÃ­cia, sem rede externa, foram validados a central de atividades e o detalhe operacional. A atividade trouxe prazo, empresa, competÃªncia e os cinco estados independentes; a conclusÃ£o exigiu evidÃªncia humana quando nÃ£o havia fonte integrada, registrou evento imutÃ¡vel e auditoria. A permissÃ£o foi exercida por empresa atribuÃ­da, sem acesso de teste a outra empresa.

- **Automatizado:** `tests.test_operational_center` e `tests.test_dte`: 13 testes aprovados. `ruff` nos arquivos Python alterados, `mypy` de `models.py` e `operations.py`, `manage.py check` e `makemigrations --check --dry-run` aprovados. A migraÃ§Ã£o 0041 protege atividades sem competÃªncia de duplicaÃ§Ã£o no reprocessamento.
- **Interface:** Playwright no servidor Django local, com usuÃ¡rio e empresa fictÃ­cios: lista em 1440 px, detalhe, registro de evidÃªncia e conclusÃ£o; detalhe em 375 px, navegaÃ§Ã£o inicial por teclado, tema escuro e movimento reduzido. Console sem erros. A aba e o servidor temporÃ¡rios foram encerrados.
- **SeguranÃ§a da renderizaÃ§Ã£o:** o esqueleto interno Node/TypeScript aceita apenas uma fotografia validada e nÃ£o usa `--no-sandbox`; ainda nÃ£o foi instalado, executado ou conectado ao Django. Portanto nÃ£o substitui os relatÃ³rios Python existentes nesta evidÃªncia.
- **RegressÃ£o integral:** `uv run pytest` aprovou 812 testes, com 2 ignorados jÃ¡ documentados (Playwright Python opcional e concorrÃªncia PostgreSQL). NÃ£o houve nova falha depois da correÃ§Ã£o de navegaÃ§Ã£o mÃ­nima.
- **Limites:** nÃ£o houve ERP, Siescon, Serpro, e-mail, IA, arquivo real, transmissÃ£o, cobranÃ§a, piloto ou homologaÃ§Ã£o. Modelos de atividades, fontes, DRE, caixa, folha, integraÃ§Ãµes e assistente de configuraÃ§Ã£o seguem como frentes posteriores do plano.

## V-106 â€” Parcelamentos de ponta a ponta e importaÃ§Ã£o Ãºnica da ConciliaÃ§Ã£o

Data: 22/09/2026. Ambiente: servidor isolado de revisÃ£o (`scripts/qa_ui_server.py`, porta
8011, sem rede externa), dados fictÃ­cios, sessÃ£o local criada por script (sem senha
digitada). Nenhum deploy, chamada Serpro, cobranÃ§a ou dado de cliente. DecisÃ£o: D-108.

- **Parcelamentos â€” o que estava quebrado:** o detalhe do acordo era consultado e
  cobrado, mas nunca exibido; a empresa em foco nÃ£o tinha botÃ£o de consulta; a carteira da
  demonstraÃ§Ã£o seguia "Nunca consultada" apÃ³s consultar; "resultado a confirmar" travava
  a operaÃ§Ã£o sem saÃ­da; DAS com falha nÃ£o podia ser emitido de novo; fila sem atualizaÃ§Ã£o.
- **Verificado:** consulta em lote de uma empresa abre a empresa (`#company-heading`);
  acordo com consolidado, "N pagas de M", parcela bÃ¡sica e demonstrativo de pagamentos;
  parcela em atraso e mÃªs atual marcadas com palavra, nÃ£o sÃ³ cor; 375 px sem rolagem
  horizontal da pÃ¡gina (tabelas rolam no prÃ³prio contÃªiner).
- **ConciliaÃ§Ã£o â€” o que estava quebrado:** dois importadores OFX paralelos; perÃ­odo
  obrigatÃ³rio coletado e descartado; campo Empresa com altura diferente dos vizinhos;
  trÃªs botÃµes de importaÃ§Ã£o na mesma tela; etapa exibida como cÃ³digo interno (`review`);
  demonstraÃ§Ã£o podia gravar arquivo no escritÃ³rio compartilhado; tabela OFX quebrando data
  e aÃ§Ã£o em uma letra por linha.
- **Verificado:** envio de `.ofx` + `.txt` bloqueia antes do envio com "formato nÃ£o
  aceito"; envio do `.ofx` cria o processamento, abre em Processamentos e alimenta a fila
  OFX Ã— DomÃ­nio (2 itens); reenvio nÃ£o duplica; modal alinhado em 1366 px e 375 px.
- **Limites:** sem chamada Serpro real (PARCSN continua dependente de homologaÃ§Ã£o); sem
  leitor de tela; tema claro nÃ£o comparado lado a lado nesta rodada. SuÃ­te: 809 aprovados,
  2 ignorados; Ruff e `makemigrations --check` limpos.

## V-105 â€” NFS-e: classificaÃ§Ã£o binÃ¡ria e filtros que aplicam sozinhos

Data: 22/09/2026. Ambiente: servidor isolado de revisÃ£o (`scripts/qa_ui_server.py`, porta
8011, banco e mÃ­dia em `.tmp/ui-review`, sem rede externa). Dados fictÃ­cios da
demonstraÃ§Ã£o. Nenhum deploy, cobranÃ§a ou dado de cliente.

- **OrientaÃ§Ã£o guiada:** o passo do diÃ¡logo deixou de receber foco programÃ¡tico. Pela
  especificaÃ§Ã£o de `:focus-visible` (teste `focus-visible-010`), um foco programÃ¡tico em
  elemento com `tabindex="-1"` casa com o seletor, e o anel aparecia em volta do texto a
  cada tela aberta. O texto agora Ã© anunciado por `aria-live="polite"`, o foco inicial vai
  para â€œAvanÃ§arâ€ e sÃ³ se move quando o botÃ£o em uso desaparece com o passo.
- **ConfianÃ§a saiu da interface:** a coluna de porcentagem nÃ£o descrevia estado
  acionÃ¡vel. A NFS-e passou a ter a coluna **ClassificaÃ§Ã£o** (Classificada / NÃ£o
  classificada), colocada antes do acumulador; â€œSituaÃ§Ã£oâ€ ficou com o estado do documento
  (Em revisÃ£o / Recebida). A fila de revisÃµes e a VisÃ£o geral perderam a porcentagem e o
  filtro por faixa de confianÃ§a; o manifesto CSV da demonstraÃ§Ã£o tambÃ©m.
- **Filtros em uma linha, sem botÃ£o:** a barra da carteira virou uma linha sÃ³ (busca
  elÃ¡stica, situaÃ§Ã£o, perÃ­odo e datas) e aplica a cada mudanÃ§a, trocando apenas a regiÃ£o
  de resultados. Substituir um trecho da pÃ¡gina Ã© atualizaÃ§Ã£o local, nÃ£o mudanÃ§a de
  contexto (WCAG 3.2.2): o formulÃ¡rio mantÃ©m controles, foco e cursor. Sem JavaScript o
  botÃ£o â€œPesquisar carteiraâ€ continua no lugar.
- **Verificado no servidor isolado:** 24 â†’ 14 resultados ao trocar a situaÃ§Ã£o e 3 ao
  digitar a busca, sem recarregar, com foco e cursor preservados no campo; barra em uma
  linha a 1440 px (altura 95 px, bordas inferiores alinhadas) nos dois modos de perÃ­odo;
  375 px sem rolagem horizontal; console sem erros.
- **Limites:** sem passagem de leitor de tela nesta rodada; a paginaÃ§Ã£o dentro da regiÃ£o
  trocada continua sendo navegaÃ§Ã£o normal (recarrega a pÃ¡gina).

## V-104 â€” Banco de desenvolvimento cifrado com a chave de teste

Data: 22/09/2026. Ambiente: desenvolvimento local do responsÃ¡vel
(`config.settings.local`, `db.sqlite3` com massa fictÃ­cia). Nenhuma chamada externa,
cobranÃ§a ou deploy. Nenhum dado de cliente envolvido.

- **Sintoma:** `/app/` quebrava com `SuspiciousOperation: Encrypted field authentication
  failed`, causado por `Field encryption key 'test-v1' is unavailable`.
- **Causa:** a massa fictÃ­cia de `db.sqlite3` foi gravada por uma execuÃ§Ã£o com
  `config.settings.test`, cuja chave fixa Ã© `test-v1`, enquanto o ambiente de
  desenvolvimento usa `local-v1`. Levantamento por tabela: `hub_nfsedocument.original_xml`
  24 linhas, `hub_certificate.password`/`pfx_blob` 3 + 3, `accounts_totpdevice.secret` 2,
  `hub_officeprofile.cnpj` 1, `platform_signupintent.cnpj` 1 e
  `intelligence_intelligenceconnector.odbc_dsn` 1 â€” todas em `test-v1`; apenas uma linha
  de conector jÃ¡ estava em `local-v1`.
- **CorreÃ§Ã£o local:** `test-v1` entrou no mapa `FIELD_ENCRYPTION_KEYS` do `.env` de
  desenvolvimento, com `local-v1` mantida como chave ativa: as leituras antigas voltam a
  funcionar e toda gravaÃ§Ã£o nova continua na chave local. Nada foi apagado e nenhum
  registro foi reescrito. A chave `test-v1` Ã© a constante pÃºblica de
  `src/config/settings/test.py` e serve apenas a dados fictÃ­cios; produÃ§Ã£o valida as
  chaves em `config/settings/production.py` e nÃ£o lÃª este arquivo.
- **CorreÃ§Ã£o de raiz:** `config/settings/local.py` passou a chamar
  `load_dotenv(..., override=True)`. Sem isso, o autoreload do Django reexecuta o servidor
  herdando o ambiente do primeiro boot, e qualquer valor jÃ¡ presente em `os.environ`
  sobrevive a toda ediÃ§Ã£o do `.env` â€” foi o que escondeu a demonstraÃ§Ã£o em V-103 e o que
  manteria esta chave ausente.
- **VerificaÃ§Ã£o:** em processo novo com as settings de desenvolvimento,
  `FIELD_ENCRYPTION_KEYS` traz `local-v1` e `test-v1`, um `NfseDocument` decifra e `/app/`
  responde 200 com a pauta. SuÃ­te completa: 798 aprovados, 2 ignorados, 11 subtestes.
  Ruff aprovado em `src` e `tests`.

Limites: a divergÃªncia de chave continua existindo no banco; consolidar tudo em
`local-v1` exigiria reescrever os registros fictÃ­cios, o que nÃ£o foi feito. Nada aqui se
aplica a produÃ§Ã£o, que nÃ£o compartilha banco, chave nem `.env` com o desenvolvimento.

## V-103 â€” Entrada da demonstraÃ§Ã£o deixa de depender do slug configurado

Data: 22/09/2026. Ambiente: servidor de desenvolvimento local do responsÃ¡vel
(`127.0.0.1:8000`, `config.settings.local`, banco `db.sqlite3` com massa fictÃ­cia) e
suÃ­te no `.venv`. Nenhuma chamada externa, cobranÃ§a ou deploy.

- **Sintoma:** mesmo com `.env` corrigido para `escritorio-demo`, a home e `/demo/`
  continuavam mostrando "A demonstraÃ§Ã£o separada estÃ¡ sendo preparada".
- **Causa:** `load_dotenv` nÃ£o sobrescreve variÃ¡vel jÃ¡ presente em `os.environ`
  (`override=False` Ã© o padrÃ£o). O processo que subiu antes da correÃ§Ã£o fixou
  `DEMO_ORGANIZATION_SLUG=cica-demo` no ambiente, e o autoreload do Django reexecuta o
  servidor herdando esse ambiente â€” o cÃ³digo novo entrava (GET `/sair/` jÃ¡ respondia 200),
  as settings nÃ£o. SÃ³ um encerramento do processo raiz limparia o valor.
- **CorreÃ§Ã£o:** `demo_office()` passou a resolver a organizaÃ§Ã£o pelo que ela Ã©. O slug
  configurado continua tendo prioridade quando existe e estÃ¡ ativo; quando nÃ£o existe, a
  entrada usa a Ãºnica organizaÃ§Ã£o ativa marcada `is_demo`. Com duas marcadas, nada Ã©
  devolvido: escolher uma seria adivinhaÃ§Ã£o, e a entrada continua fechada.
- **VerificaÃ§Ã£o no servidor do responsÃ¡vel, sem reiniciar o processo:** `/demo/` passou a
  responder "Iniciar demonstraÃ§Ã£o fictÃ­cia" e a home voltou com "Ver demonstraÃ§Ã£o",
  "Explorar demo fictÃ­cia" e "Abrir demonstraÃ§Ã£o fictÃ­cia".
- **RegressÃ£o:** `tests/test_seed_demo_django.py` ganhou
  `test_a_stale_configured_slug_still_finds_the_single_demonstration_office` e
  `test_two_demonstration_offices_close_the_entry_instead_of_guessing`. SuÃ­te completa:
  798 aprovados, 2 ignorados, 11 subtestes. Ruff aprovado em `src` e `tests`.

Limite: os gates `DEMO_ENTRY_ENABLED` e `DEMO_SESSION_ISOLATION_READY` continuam
obrigatÃ³rios e nÃ£o foram afrouxados; a entrada segue fechada em qualquer ambiente onde
eles estejam desligados.

## V-102 â€” Landing, ondas 5 a 7 e auditoria de interface da revisÃ£o total

Data: 22/09/2026. Ambiente: servidor isolado `scripts/qa_ui_server.py` (porta 8011,
`.tmp/ui-review`, conexÃµes externas bloqueadas), navegador local em 1440 Ã— 1000 e
375 Ã— 812. Nenhuma credencial real digitada, nenhuma chamada externa, cobranÃ§a, arquivo
de cliente ou deploy.

**Site pÃºblico e acesso**

- A seÃ§Ã£o "POR QUE CICA" era um parÃ¡grafo sobre o significado da sigla. Virou a seÃ§Ã£o de
  problema que o plano pede, com uma frase concreta e link para os mÃ³dulos.
- "UMA PAUTA, CINCO FRENTES" anunciava cinco etapas e listava quatro. Passou a "UMA
  PAUTA, QUATRO ETAPAS".
- No celular, o cabeÃ§alho escondia "Entrar": quem jÃ¡ Ã© cliente nÃ£o tinha caminho de login
  a partir da home. O link voltou, com 44 px de altura.
- Cinco links da landing tinham menos de 24 px de alvo (demo, mÃ³dulos, termos,
  privacidade, entrar). Todos passaram a 24 px, e 44 px no celular.
- O consentimento do cadastro tinha nome acessÃ­vel quebrado ("Li e aceito os , a e o .")
  porque os links ficavam dentro do rÃ³tulo. O rÃ³tulo virou texto contÃ­nuo e os trÃªs
  documentos ficaram em uma linha de links logo abaixo, todos alcanÃ§Ã¡veis por teclado.

**Onda 5 â€” inteligÃªncia e conhecimento**

- Radar: filtro de perÃ­odo (7, 30, 90 dias), coberto por
  `tests/test_reform_radar.py::test_radar_period_filter_hides_older_publications`. Cada
  linha passou a mostrar resumo, data de publicaÃ§Ã£o e de coleta, e a marcar "PublicaÃ§Ã£o
  coletada Â· sem interpretaÃ§Ã£o fiscal validada".
- Copiloto: toda resposta recebeu a linha de limite ("Rascunho para conferÃªncia. A CICA
  nÃ£o altera o DomÃ­nio"), e uma resposta sem evidÃªncia passa a ser marcada como "Sem
  fonte verificÃ¡vel" com aviso para conferir na Ã¡rea operacional.
- Central de aprendizado: o vazio virou explicaÃ§Ã£o com saÃ­da ("Abrir Copiloto"), e cada
  candidato mostra resposta anterior, escopo do escritÃ³rio, data e responsÃ¡vel pela
  revisÃ£o.

**Onda 6 â€” administraÃ§Ã£o e console**

- O console Mewstack autenticado foi inspecionado visualmente pela primeira vez, em base
  fictÃ­cia isolada, criando a sessÃ£o de uma persona sintÃ©tica direto no banco de revisÃ£o;
  nenhuma senha foi digitada e nenhum controle de MFA foi contornado (a tela
  `/platform/configuracoes/` continua exigindo segundo fator e nÃ£o foi inspecionada).
- O painel do console passou a ser orientado a exceÃ§Ã£o: suspensos, ativaÃ§Ãµes pendentes,
  integraÃ§Ã£o DomÃ­nio com falha, egressÃ£o incerta e suporte ativo, cada um com link.
- O detalhe do escritÃ³rio abria com o tÃ­tulo do navegador apenas "CICA"; agora nomeia o
  escritÃ³rio.
- Equipe: a demonstraÃ§Ã£o listava as contas descartÃ¡veis de todos os outros visitantes.
  Passou a mostrar apenas as personas semeadas e quem estÃ¡ olhando, coberto por
  `tests/test_seed_demo_django.py::test_demo_team_page_hides_the_accounts_of_other_visitors`.
- Segredos do console usam `PasswordInput(render_value=False)` em todos os formulÃ¡rios:
  nenhum valor existente Ã© reexibido.

**Onda 7 â€” tutorial guiado**

- CatÃ¡logo declarativo em `src/apps/hub/onboarding.py`: boas-vindas mais nove orientaÃ§Ãµes
  por Ã¡rea, no mÃ¡ximo trÃªs passos cada, ancoradas ao nome da rota da tela principal â€”
  detalhe, confirmaÃ§Ã£o e formulÃ¡rio iniciado nunca abrem orientaÃ§Ã£o.
- PreferÃªncia versionada por pessoa em `hub.OnboardingProgress` (usuÃ¡rio, identificador,
  versÃ£o, data). Nenhum conteÃºdo fiscal, empresa ou resposta Ã© gravado. A demonstraÃ§Ã£o
  guarda o progresso apenas em `sessionStorage`.
- DiÃ¡logo HTML nativo com foco contido, Pular, Voltar, Fechar e "Como usar" permanente;
  ao fechar, o foco volta ao acionador. SessÃ£o de suporte nÃ£o abre orientaÃ§Ã£o.
- Seis testes em `tests/test_onboarding_tour.py` cobrem primeira abertura, conclusÃ£o,
  nova versÃ£o, tela de detalhe, catÃ¡logo e recusa de identificador desconhecido.
- Limite: o envio sintÃ©tico de teclas nÃ£o chega Ã  pÃ¡gina neste ambiente, entÃ£o a
  ativaÃ§Ã£o por Enter/EspaÃ§o nÃ£o foi confirmada por automaÃ§Ã£o. A operaÃ§Ã£o por teclado Ã©
  garantida pela estrutura (botÃµes nativos, diÃ¡logo nativo, foco movido para o passo) e
  foi verificada por ordem de foco; falta confirmaÃ§Ã£o com teclado real e leitor de tela.

**Onda 8 â€” auditoria de interface**

- Vercel Web Interface Guidelines consultadas em 22/09/2026
  (<https://vercel.com/design/guidelines>). CorreÃ§Ãµes aplicadas nas superfÃ­cies alteradas:
  alvos de 24 px (44 px no celular) em links de indicador, links de linha, links da fila
  de Triagem e caixas de seleÃ§Ã£o; rÃ³tulo de texto em Ã­cone; `aria-live` nos contadores de
  seleÃ§Ã£o.
- Varredura final em 375 px: VisÃ£o geral, Empresas, Certificados, NFS-e, RevisÃµes, Guias,
  Central Integra, Parcelamentos, Caixa DTE, ConciliaÃ§Ã£o, Radar, Triagem, Caixas,
  IntegraÃ§Ãµes, Primeiros passos, Equipe, Copiloto e Aprendizado â€” nenhum overflow
  horizontal. Console do navegador limpo em aba nova.
- SuÃ­te completa no `.venv`: 796 aprovados, 2 ignorados, 11 subtestes. Ruff aprovado em
  `src` e `tests`. `makemigrations --check` sem alteraÃ§Ãµes pendentes.

Limites: a onda 8 do plano previa tambÃ©m regressÃ£o por perfil, leitor de tela e tema
escuro comparados lado a lado, viewports 1024 e 768, e a tela de configuraÃ§Ã£o do console
sob MFA â€” nada disso foi feito. Nenhuma integraÃ§Ã£o real, homologaÃ§Ã£o ou deploy.

## V-101 â€” Ondas 1 a 4 da revisÃ£o total de telas

Data: 22/09/2026. Ambiente: servidor isolado `scripts/qa_ui_server.py` (porta 8011,
`.tmp/ui-review`, conexÃµes externas bloqueadas), navegador local em 1440 Ã— 1000 e
375 Ã— 812. Nenhuma credencial real, chamada externa, cobranÃ§a, arquivo de cliente ou
deploy.

**Onda 1 â€” fundaÃ§Ã£o compartilhada**

- `.inline-alert` nÃ£o tinha estilo algum: os 15 avisos em linha das telas de Guias,
  NFS-e, Parcelamentos, ConciliaÃ§Ã£o e Radar apareciam como texto solto, e as variantes
  `-warning` e `-danger` eram indistinguÃ­veis. Passaram a ter bloco, borda de acento e
  tÃ­tulo colorido, sempre com a palavra do estado junto da cor. Contrastes calculados
  nos dois temas: azul 6,82:1 (claro) e 6,57:1 (escuro); Ã¢mbar 6,01 e 7,46; vermelho
  6,13 e 7,61 â€” todos acima de 4,5:1.
- AÃ§Ãµes em lote passaram a aparecer sÃ³ depois de existir seleÃ§Ã£o em Parcelamentos,
  coleta NFS-e, download NFS-e da demonstraÃ§Ã£o e fila de movimentos da ConciliaÃ§Ã£o
  (Guias jÃ¡ seguia esse contrato). Sem JavaScript, os botÃµes continuam renderizados e o
  servidor segue validando a seleÃ§Ã£o.
- `USE_THOUSAND_SEPARATOR = True`: valores em pt-BR passaram a usar o ponto de milhar
  (`R$ 1.943,24`). Duas asserÃ§Ãµes de teste foram ajustadas para o formato correto.
- Texto repetido removido: os avisos de demonstraÃ§Ã£o de Parcelamentos, ConciliaÃ§Ã£o e
  Radar deixaram de repetir a faixa global e ficaram com a consequÃªncia especÃ­fica do
  mÃ³dulo; a fila da Triagem perdeu a linha "Consulte a etapa e a auditoria antes de
  agir".

**Onda 3 â€” nÃºcleo diÃ¡rio**

- RevisÃµes de NFS-e: a tabela misturava caso pendente e caso decidido quando o filtro
  era "Todas". Ganhou coluna **SituaÃ§Ã£o** (aguardando decisÃ£o / decidida, com data e
  responsÃ¡vel) e a coluna de acumulador passou a rotular a origem â€” "SugestÃ£o da CICA"
  ou "Decidido por pessoa". Os rÃ³tulos mÃ³veis (`::before`) foram corrigidos para a nova
  ordem das colunas.
- Empresas: filtros de **certificado** (vÃ¡lido, vence em 30 dias, sem certificado) e de
  **pendÃªncia** (com/sem revisÃ£o aberta), com as duas colunas correspondentes. Coberto
  por `tests/test_company_registry_django.py::CompanyRegistryTests::test_the_registry_filters_by_certificate_and_open_review`.
- Caixa DTE: a fila mostra a idade da mensagem ("recebida hÃ¡ 6 dias"). O Serpro nÃ£o
  devolve prazo na listagem, entÃ£o prazo continua ausente â€” idade Ã© o que existe sem
  inventar dado.
- VisÃ£o geral: cada linha da fila de decisÃ£o mostra hÃ¡ quanto tempo o documento estÃ¡
  parado.

**Onda 4 â€” processamento documental**

- ConciliaÃ§Ã£o: o detalhe do movimento perdia filtro e pÃ¡gina ao voltar (era um link
  fixo para `#movimentos`). Passou a usar `return_to` e `back_url`, como o resto do
  sistema. Verificado no navegador: `?movement_state=ambiguous&movement_page=1`
  sobrevive Ã  ida e volta.
- ConciliaÃ§Ã£o: os indicadores passaram a mostrar os dois lados com valor â€” importados do
  extrato e lanÃ§amentos no DomÃ­nio, alÃ©m do valor pendente.
- Triagem: o painel de destino Windows mostra saÃºde do agente (conectado / sem sinal,
  Ãºltimo sinal) e prova da gravaÃ§Ã£o (Ãºltimo caminho gravado e Ãºltima falha), nÃ£o sÃ³ o
  caminho configurado. Coberto por
  `tests/test_triage_oauth_django.py::TriageMailboxOAuthTests::test_windows_destination_shows_agent_health_and_the_last_write`.

**VerificaÃ§Ã£o**

- 20 telas autenticadas responderam 200; nenhuma das telas alteradas apresentou overflow
  horizontal em 375 px e o console ficou limpo em aba nova.
- SuÃ­te completa no `.venv`: 788 aprovados, 2 ignorados, 11 subtestes. Ruff aprovado em
  `src` e `tests`.

Limites: ondas 5 a 8 continuam abertas (Radar/Copiloto/aprendizado, administraÃ§Ã£o e
console Mewstack, tutorial guiado e auditoria final). NÃ£o houve inspeÃ§Ã£o de todos os
perfis, leitor de tela, tema escuro comparado lado a lado, viewports 1024/768, console
Mewstack autenticado, integraÃ§Ã£o real nem homologaÃ§Ã£o externa.

## V-100 â€” Ondas 0 a 2 da revisÃ£o total de telas: matriz, contrato de recusa e demonstraÃ§Ã£o restaurada

Data: 22/09/2026. Ambiente: servidor de revisÃ£o isolado `scripts/qa_ui_server.py`
(porta 8011, banco e mÃ­dia em `.tmp/ui-review`, conexÃµes externas bloqueadas) e
navegador local. Nenhuma credencial real, chamada externa, cobranÃ§a, arquivo de
cliente ou deploy.

- **Matriz (onda 0).** O URLconf foi inventariado: 89 rotas de interface â€” 49
  telas/estados e 40 aÃ§Ãµes ou downloads â€”, registradas em
  [`docs/planejamento/matriz-telas-2026-09-22.md`](docs/planejamento/matriz-telas-2026-09-22.md).
  Rotas de API REST, webhooks e agente ficam fora da matriz.
- **Varredura GET autenticada** (owner do escritÃ³rio fictÃ­cio) das 31 telas sem
  parÃ¢metro: todas responderam 200 ou redirecionaram para o destino esperado; as
  trÃªs telas do console Mewstack responderam 403 por perfil, como previsto. As
  telas de detalhe com id semeado (empresa, guia, revisÃ£o, mensagem DTE, item de
  Triagem, movimento da conciliaÃ§Ã£o, documentos legais) responderam 200.
- **Mobile 375 x 812:** 20 telas autenticadas percorridas sem overflow
  horizontal (`scrollWidth == clientWidth` em todas) e sem erro de console.
- **DemonstraÃ§Ã£o (onda 2).** O ambiente local apontava para `cica-demo` enquanto
  a organizaÃ§Ã£o fictÃ­cia Ã© `escritorio-demo`: o `.env` local foi corrigido e
  "Ver demonstraÃ§Ã£o", "Explorar demo fictÃ­cia" e "Abrir demonstraÃ§Ã£o fictÃ­cia"
  voltaram Ã  home. A faixa de demonstraÃ§Ã£o da Ã¡rea de trabalho ganhou saÃ­da
  explÃ­cita ("Sair da demonstraÃ§Ã£o"), que encerra a sessÃ£o e descarta o progresso
  do visitante. Os 21 testes de isolamento da demonstraÃ§Ã£o e os 2 da landing
  continuam passando.
- **Recusa que nÃ£o Ã© permissÃ£o (onda 1).** `refuse()` passou a aceitar
  `kind="unavailable"`: 24 recusas de estado ou validaÃ§Ã£o (formato sem
  mapeamento, aÃ§Ã£o invÃ¡lida, limite de lote, caso jÃ¡ decidido, bloqueios da
  demonstraÃ§Ã£o) deixaram de ser apresentadas como "ACESSO RESTRITO / Sem
  permissÃ£o". O status HTTP continua 403.
- **Estado vazio (onda 1).** Criado o parcial Ãºnico
  `hub/partials/empty_state.html` (tÃ­tulo, uma frase, saÃ­da). Os dois estados
  vazios fora do contrato â€” filtro sem resultado em Empresas e em Parcelamentos â€”
  passaram a usÃ¡-lo e agora oferecem "Ver todas".
- **AÃ§Ã£o quebrada corrigida.** `GET /sair/` respondia 405 sem corpo: o Django 5.0
  removeu logout por GET ([release notes](https://docs.djangoproject.com/en/5.0/releases/5.0/))
  e o projeto usa Django 6.0.8. `hub:logout` passou a ser `SignOutView`, que
  responde GET com a confirmaÃ§Ã£o ("Sair da CICA?" ou "SessÃ£o encerrada") e mantÃ©m
  o logout em POST. RegressÃ£o em `tests/test_cica_auth_flow.py`
  (`test_bookmarked_logout_url_answers_with_a_page_and_still_needs_a_post`).
- SuÃ­te completa executada no interpretador do projeto (`.venv`): 781 aprovados,
  2 ignorados, 11 subtestes. Ruff aprovado nos arquivos alterados.

Limites: as ondas 3 a 8 do plano nÃ£o foram executadas. NÃ£o houve inspeÃ§Ã£o de
todos os perfis, leitor de tela, teclado completo, tema escuro, viewports 1440 /
1024 / 768, console Mewstack autenticado, integraÃ§Ã£o real nem homologaÃ§Ã£o
externa. Nenhuma simulaÃ§Ã£o local Ã© registrada como homologaÃ§Ã£o.

## V-099 â€” DemonstraÃ§Ã£o isolada da ConciliaÃ§Ã£o revisada no navegador

Data: 21/09/2026. Ambiente: banco SQLite temporÃ¡rio, migrado e semeado somente
com dados fictÃ­cios; navegador local. NÃ£o houve credencial real, upload,
processamento, consulta externa, cobranÃ§a, arquivo de cliente ou deploy.

- A entrada `/demo/` informou explicitamente que os dados sÃ£o fictÃ­cios e que
  nÃ£o hÃ¡ consulta externa ou cobranÃ§a. A sessÃ£o abriu a VisÃ£o geral do
  escritÃ³rio demonstrativo e a ConciliaÃ§Ã£o sem acessar o banco local de
  desenvolvimento.
- Em 1440 Ã— 1000 e 390 Ã— 844, a tela de ConciliaÃ§Ã£o nÃ£o teve overflow
  horizontal nem erros/avisos no console. O modal de importaÃ§Ã£o expÃ´s empresa,
  conta financeira, origem, perÃ­odo, identificaÃ§Ã£o de lote e os limites de 20
  arquivos / 25 MiB, sem enviar arquivo.
- O servidor e a aba temporÃ¡rios foram encerrados ao fim da inspeÃ§Ã£o. A base e
  os artefatos fictÃ­cios foram movidos para a Lixeira de forma recuperÃ¡vel.

Limites: nÃ£o substitui inspeÃ§Ã£o de todos os perfis, teclado/foco completo,
upload real, OCR, ERP, Serpro, Asaas ou homologaÃ§Ã£o comercial.

## V-098 â€” PDF corrompido recusado antes da conciliaÃ§Ã£o

Data: 21/09/2026. Ambiente: macOS local e banco de testes. NÃ£o houve arquivo
real de cliente, OCR, ERP, exportaÃ§Ã£o, integraÃ§Ã£o, custo ou deploy.

- A validaÃ§Ã£o de PDF agora abre o documento e confirma o limite de 500 pÃ¡ginas
  antes de persistir a fonte. Um PDF malformado Ã© recusado com mensagem clara e
  nÃ£o cria lote ou processamento invÃ¡lido; a ausÃªncia opcional de `pdfplumber`
  mantÃ©m o caminho de OCR local.
- **42 testes** focados de ConciliaÃ§Ã£o passaram, com um skip de OCR local. Ruff
  e MyPy do serviÃ§o aprovaram a alteraÃ§Ã£o. A regressÃ£o integral fechou com
  **784 testes aprovados, 3 skips e 11 subtestes** em 29,23 s.

Limites: a prova usa um PDF sintÃ©tico corrompido; nÃ£o homologa OCR, arquivos,
ERP ou exportaÃ§Ã£o reais.

## V-097 â€” XLSX corrompido recusado antes da conciliaÃ§Ã£o

Data: 21/09/2026. Ambiente: macOS local e banco de testes. NÃ£o houve arquivo
real de cliente, OCR, ERP, exportaÃ§Ã£o, integraÃ§Ã£o, custo ou deploy.

- A entrada XLSX agora abre a planilha antes de persistir a fonte. Uma extensÃ£o
  vÃ¡lida com assinatura `PK`, mas arquivo corrompido, retorna uma mensagem
  operacional clara e nÃ£o cria fonte, lote ou processamento invÃ¡lido.
- A prÃ©via CSV lÃª somente as 51 linhas necessÃ¡rias, em vez de materializar o
  arquivo inteiro para exibir suas primeiras linhas.
- **41 testes** focados de ConciliaÃ§Ã£o passaram, com um skip de OCR local. Ruff
  e MyPy do serviÃ§o aprovaram a alteraÃ§Ã£o. A regressÃ£o integral fechou com
  **783 testes aprovados, 3 skips e 11 subtestes** em 29,13 s.

Limites: a prova usa uma planilha sintÃ©tica corrompida; nÃ£o homologa layouts,
arquivos, OCR, ERP ou exportaÃ§Ã£o reais.

## V-096 â€” CÃ³digo operacional de Jornadas removido

Data: 21/09/2026. Ambiente: macOS local e banco de testes. NÃ£o houve oferta,
contrato, cobranÃ§a, convite, arquivo, integraÃ§Ã£o, custo, deploy ou dado de
cliente.

- Em complemento Ã  V-095 e conforme D-43, foram removidos os formulÃ¡rios,
  views e template operacionais Ã³rfÃ£os de Jornadas. O enum, os modelos, tabelas
  e migraÃ§Ãµes histÃ³ricos continuam preservados; nÃ£o houve migraÃ§Ã£o destrutiva.
- A busca de referÃªncias confirmou que nÃ£o hÃ¡ rota, vÃ­nculo de navegaÃ§Ã£o,
  formulÃ¡rio, view ou template ativo de Jornadas; o teste segue cobrindo as
  cinco rotas legadas como 404 em GET e POST e sua ausÃªncia do catÃ¡logo.
- **73 testes** focados de acesso, workspace e operaÃ§Ã£o passaram. Ruff, MyPy
  global, Django e migraÃ§Ãµes aprovaram os **190 arquivos**. A regressÃ£o integral
  fechou com **781 testes aprovados, 3 skips e 11 subtestes** em 29,43 s.
- ApÃ³s `git fetch origin --prune`, `HEAD` permanece **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**; nÃ£o houve pull, commit ou push. As 102 alteraÃ§Ãµes
  locais existentes foram preservadas.

Limites: a prova Ã© local; nÃ£o comprova contrato comercial, uso histÃ³rico por
cliente, migraÃ§Ã£o jÃ¡ aplicada em produÃ§Ã£o ou homologaÃ§Ã£o de venda.

## V-095 â€” Jornadas removida do catÃ¡logo de produto

Data: 21/09/2026. Ambiente: macOS local e banco de testes. NÃ£o houve oferta,
contrato, cobranÃ§a, convite, arquivo, integraÃ§Ã£o, custo, deploy ou dado de
cliente.

- A definiÃ§Ã£o de mÃ³dulo Jornadas foi retirada do catÃ¡logo usado pelo produto,
  alinhando-o Ã  D-43. O enum, schema e migraÃ§Ãµes legados foram preservados para
  compatibilidade histÃ³rica, mas Jornadas nÃ£o tem rota, navegaÃ§Ã£o ou oferta.
- O teste confirmou que as cinco rotas legadas retornam 404 em GET e POST, que
  a navegaÃ§Ã£o nÃ£o as expÃµe e que o cÃ³digo nÃ£o estÃ¡ no catÃ¡logo.
- **73 testes** focados de acesso, workspace e operaÃ§Ã£o passaram. Ruff, MyPy
  global, Django e migraÃ§Ãµes aprovaram os **190 arquivos**. A regressÃ£o integral
  fechou com **781 testes aprovados, 3 skips e 11 subtestes** em 28,56 s.
- ApÃ³s `git fetch origin --prune`, `HEAD` permanece **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**; nÃ£o houve pull, commit ou push. As 101 alteraÃ§Ãµes
  locais existentes foram preservadas.

Limites: a prova Ã© local; nÃ£o comprova contrato comercial, uso histÃ³rico por
cliente, migraÃ§Ã£o jÃ¡ aplicada em produÃ§Ã£o ou homologaÃ§Ã£o de venda.

## V-094 â€” Caixa DTE mantÃ©m mensagens e histÃ³rico independentes

Data: 21/09/2026. Ambiente: macOS local e banco de testes. NÃ£o houve consulta
Serpro, credencial, consumo, cobranÃ§a, arquivo, dado de cliente ou deploy.

- A paginaÃ§Ã£o da Caixa Postal agora preserva a pÃ¡gina do histÃ³rico de consultas
  DTE, filtros e empresa selecionada; a paginaÃ§Ã£o do histÃ³rico jÃ¡ preservava a
  pÃ¡gina de mensagens. As duas listas podem ser percorridas sem se reiniciarem.
- O teste criou **31 resultados DTE e 26 mensagens** sintÃ©ticas, confirmou a
  segunda pÃ¡gina de cada lista e ambos os vÃ­nculos de retorno, sem preparar ou
  enviar uma consulta.
- **10 testes** focados de DTE passaram. Ruff, MyPy global, Django e migraÃ§Ãµes
  aprovaram os **190 arquivos**. A regressÃ£o integral fechou com **781 testes
  aprovados, 3 skips e 11 subtestes** em 28,67 s.
- ApÃ³s `git fetch origin --prune`, `HEAD` permanece **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**; nÃ£o houve pull, commit ou push. As 99 alteraÃ§Ãµes
  locais existentes foram preservadas.

Limites: a prova Ã© local e sintÃ©tica; nÃ£o comprova Serpro, certificado,
representaÃ§Ã£o, consumo, cobranÃ§a, PostgreSQL em volume ou homologaÃ§Ã£o.

## V-093 â€” Fila OFX sem perder o contexto da ConciliaÃ§Ã£o

Data: 21/09/2026. Ambiente: macOS local e banco de testes. NÃ£o houve arquivo,
importaÃ§Ã£o, confirmaÃ§Ã£o, reprocessamento, exportaÃ§Ã£o, ERP, OCR, custo, deploy
ou dado de cliente.

- A paginaÃ§Ã£o da fila OFX Ã— DomÃ­nio agora mantÃ©m as pÃ¡ginas de Processamentos,
  Movimentos e ExportaÃ§Ãµes, alÃ©m dos filtros da prÃ³pria fila. AvanÃ§ar ou voltar
  na fila nÃ£o reinicia as outras trÃªs Ã¡reas da ConciliaÃ§Ã£o.
- O teste percorreu a terceira pÃ¡gina de 101 correspondÃªncias sintÃ©ticas com
  as trÃªs pÃ¡ginas independentes selecionadas e confirmou o vÃ­nculo de retorno,
  sem criar ou alterar uma conciliaÃ§Ã£o.
- **39 testes** focados de ConciliaÃ§Ã£o passaram, com **1 skip** de OCR local.
  Ruff, MyPy global, Django e migraÃ§Ãµes aprovaram os **190 arquivos**. A
  regressÃ£o integral fechou com **781 testes aprovados, 3 skips e 11 subtestes**
  em 28,11 s.
- ApÃ³s `git fetch origin --prune`, `HEAD` permanece **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**; nÃ£o houve pull, commit ou push. As 99 alteraÃ§Ãµes
  locais existentes foram preservadas.

Limites: a prova Ã© local e sintÃ©tica; nÃ£o comprova arquivo, OCR, layout real,
ERP, PostgreSQL em volume, exportaÃ§Ã£o ou homologaÃ§Ã£o operacional.

## V-092 â€” PÃ¡ginas independentes na carteira de ConciliaÃ§Ã£o

Data: 21/09/2026. Ambiente: macOS local e banco de testes. NÃ£o houve arquivo,
importaÃ§Ã£o, reprocessamento, confirmaÃ§Ã£o, exportaÃ§Ã£o, ERP, OCR, custo, deploy
ou dado de cliente.

- A paginaÃ§Ã£o dos movimentos normalizados agora conserva as pÃ¡ginas jÃ¡ abertas
  de Processamentos e ExportaÃ§Ãµes, bem como filtros e contexto da ConciliaÃ§Ã£o.
  Trocar a carteira de movimentos nÃ£o desloca mais as outras duas trilhas.
- O teste criou **21 processamentos, 21 exportaÃ§Ãµes e 51 movimentos** sintÃ©ticos
  e confirmou a segunda pÃ¡gina de cada Ã¡rea e o vÃ­nculo de retorno do movimento,
  sem executar nenhuma aÃ§Ã£o operacional.
- **39 testes** focados de ConciliaÃ§Ã£o passaram, com **1 skip** de OCR local.
  Ruff, MyPy global, Django e migraÃ§Ãµes aprovaram os **190 arquivos**. A
  regressÃ£o integral fechou com **781 testes aprovados, 3 skips e 11 subtestes**
  em 28,33 s.
- ApÃ³s `git fetch origin --prune`, `HEAD` permanece **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**; nÃ£o houve pull, commit ou push. As 99 alteraÃ§Ãµes
  locais existentes foram preservadas.

Limites: a prova Ã© local e sintÃ©tica; nÃ£o comprova arquivo, OCR, layout real,
ERP, PostgreSQL em volume, exportaÃ§Ã£o ou homologaÃ§Ã£o operacional.

## V-091 â€” HistÃ³rico da Triagem sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local e banco de testes. NÃ£o houve caixa de
e-mail, arquivo, antimalware, OCR, destino Windows, integraÃ§Ã£o, custo, deploy
ou dado de cliente.

- O detalhe de um arquivo em Triagem agora percorre a trilha persistida de
  eventos em pÃ¡ginas de 20, informa o total e preserva a ordem cronolÃ³gica e
  os parÃ¢metros de retorno; nÃ£o carrega a trilha inteira para exibi-la.
- O teste criou **21 eventos** sintÃ©ticos e confirmou as duas pÃ¡ginas (20/1),
  o total, as evidÃªncias inicial e final e os vÃ­nculos de ida e volta, sem
  mudar o estado do item, aprovar arquivamento ou produzir arquivo.
- A demonstraÃ§Ã£o permanece isolada por sessÃ£o e nÃ£o Ã© usada como prova visual
  do histÃ³rico persistido em volume. A inspeÃ§Ã£o autenticada no navegador nÃ£o
  foi automatizada para nÃ£o inserir credenciais.
- **57 testes** focados do espaÃ§o de trabalho passaram; Ruff, MyPy global,
  Django e migraÃ§Ãµes aprovaram os **190 arquivos**. A regressÃ£o integral fechou
  com **781 testes aprovados, 3 skips e 11 subtestes** em 28,86 s.
- ApÃ³s `git fetch origin --prune`, `HEAD` permanece **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**; nÃ£o houve pull, commit ou push. As 99 alteraÃ§Ãµes
  locais existentes foram preservadas.

Limites: a prova Ã© local e sintÃ©tica; nÃ£o comprova caixa, scanner, OCR,
classificaÃ§Ã£o, arquivo, agente Windows, PostgreSQL em volume ou homologaÃ§Ã£o
operacional.

## V-090 â€” Candidatos de conciliaÃ§Ã£o sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporÃ¡rio e demonstraÃ§Ã£o
fictÃ­cia. NÃ£o houve arquivo real, importaÃ§Ã£o, exportaÃ§Ã£o, ERP, OCR, integraÃ§Ã£o,
custo, deploy ou dado de cliente.

- O detalhe do movimento agora percorre todos os lanÃ§amentos candidatos no
  recorte jÃ¡ existente de seis dias: mostra 25 por pÃ¡gina, informa o total de
  lanÃ§amentos avaliados e conserva a confirmaÃ§Ã£o humana com evidÃªncia.
- O teste criou **51 candidatos** sintÃ©ticos, confirmou as trÃªs pÃ¡ginas
  (25/25/1) e verificou que todos apareceram; nÃ£o confirmou conciliaÃ§Ã£o nem
  gerou lanÃ§amento, arquivo ou exportaÃ§Ã£o.
- A demonstraÃ§Ã£o temporÃ¡ria percorreu a segunda pÃ¡gina e a superfÃ­cie de 390
  px sem overflow horizontal ou erro de console. Servidor, navegador e banco
  temporÃ¡rio foram encerrados; o banco foi movido Ã  Lixeira de forma
  recuperÃ¡vel.
- **39 testes** de ConciliaÃ§Ã£o passaram, com **1 skip** de OCR local; Ruff,
  MyPy global, Django e migraÃ§Ãµes aprovaram os **190 arquivos**. A regressÃ£o
  integral fechou com **780 testes aprovados, 3 skips e 11 subtestes** em
  29,92 s.
- ApÃ³s `git fetch origin --prune`, `HEAD` permanece **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**; nÃ£o houve pull, commit ou push.

Limites: a prova Ã© local e sintÃ©tica; nÃ£o comprova arquivo, OCR, ERP, DomÃ­nio,
Siescon, importaÃ§Ã£o no destino, PostgreSQL em volume ou homologaÃ§Ã£o operacional.

## V-089 â€” Acumulador NFS-e validado no catÃ¡logo da empresa

Data: 21/09/2026. Ambiente: macOS local e banco de testes. NÃ£o houve coleta,
certificado, ADN, lanÃ§amento, integraÃ§Ã£o, custo, deploy ou dado de cliente.

- A decisÃ£o humana de uma revisÃ£o NFS-e agora sÃ³ aceita acumulador presente em
  regra ativa e vigente ou no histÃ³rico observado da mesma empresa; cÃ³digo
  inexistente ou de outra empresa Ã© recusado. A tela sugere o catÃ¡logo local.
- **95 testes** de espaÃ§o de trabalho, fiscal e IA passaram; Ruff e MyPy global
  aprovaram os **190 arquivos** de cÃ³digo. A regressÃ£o integral fechou com
  **779 testes aprovados, 3 skips e 11 subtestes** em 28,73 s; Django e
  migraÃ§Ãµes nÃ£o apontaram drift.
- A demonstraÃ§Ã£o fictÃ­cia confirmou em desktop e em 390 px o campo da decisÃ£o,
  sua lista nativa de acumuladores e a ausÃªncia de overflow horizontal ou erro
  de console. A sessÃ£o e seu banco temporÃ¡rio foram encerrados; o banco foi
  movido Ã  Lixeira de forma recuperÃ¡vel.
- ApÃ³s `git fetch origin --prune`, `HEAD` permanece **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**; nÃ£o houve pull, commit ou push.

Limites: a prova Ã© local e sintÃ©tica; nÃ£o comprova catÃ¡logo DomÃ­nio, regra
fiscal, ADN, documento real ou homologaÃ§Ã£o. A medida nÃ£o cria regra nem
lanÃ§amento.

## V-088 â€” AtenÃ§Ã£o de egressÃ£o sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local e banco de testes, com auditorias de
egressÃ£o exclusivamente sintÃ©ticas. NÃ£o houve pergunta enviada, chamada Claude,
liberaÃ§Ã£o ou liquidaÃ§Ã£o de consumo, credencial externa, custo, deploy ou dado de
cliente.

- O detalhe do escritÃ³rio no console da plataforma deixou de limitar as
  tentativas Claude que exigem verificaÃ§Ã£o Ã s 20 mais recentes: agora pagina 20
  itens, informa o total e mantÃ©m os parÃ¢metros correntes do detalhe.
- O teste criou 21 auditorias incertas sintÃ©ticas no mesmo escritÃ³rio, alcanÃ§ou
  a segunda pÃ¡gina e preservou o protocolo da ocorrÃªncia mais antiga sem
  repetir chamada, liberar reserva ou alterar consumo.
- **57 testes** de detalhe de escritÃ³rio, IA e isolamento passaram; Ruff e MyPy
  global aprovaram os **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **778 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,40 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- ApÃ³s `git fetch origin --prune`, `HEAD` permaneceu **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**. As 96 alteraÃ§Ãµes locais existentes foram
  preservadas antes do registro desta entrega.

Limites: a evidÃªncia usa somente auditorias sintÃ©ticas locais; nÃ£o comprova
provedor Claude, resposta real, confirmaÃ§Ã£o externa, custo, concorrÃªncia
PostgreSQL ou homologaÃ§Ã£o operacional. A inspeÃ§Ã£o visual autenticada do console
nÃ£o foi automatizada porque exigiria inserir uma credencial no navegador; nenhum
ambiente externo foi acessado.

## V-087 â€” Fechamentos adiados sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local e banco de testes, com ocorrÃªncias de
fechamento exclusivamente sintÃ©ticas. NÃ£o houve fechamento, reserva, cobranÃ§a,
contato Asaas, credencial externa, custo, deploy ou dado de cliente.

- O console da plataforma deixou de limitar a lista de fechamentos ainda
  adiados Ã s 30 ocorrÃªncias mais antigas: agora pagina 30 itens, informa o
  total e conserva os parÃ¢metros correntes da configuraÃ§Ã£o.
- O teste criou 31 escritÃ³rios e ocorrÃªncias sintÃ©ticas, alcanÃ§ou a segunda
  pÃ¡gina e confirmou os vÃ­nculos de retorno sem executar operaÃ§Ã£o de
  faturamento, mudar contrato, preÃ§o ou status.
- **65 testes** de configuraÃ§Ã£o, console e cobranÃ§a passaram, com **1 skip**
  de concorrÃªncia em PostgreSQL; Ruff e MyPy global aprovaram os **190
  arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **777 testes aprovados, 3 skips e 11
  subtestes aprovados** em 37,81 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- ApÃ³s `git fetch origin --prune`, `HEAD` permaneceu **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**. As 96 alteraÃ§Ãµes locais existentes foram
  preservadas antes do registro desta entrega.

Limites: a evidÃªncia cobre somente ocorrÃªncias sintÃ©ticas locais; nÃ£o comprova
fechamento mensal, reserva em concorrÃªncia PostgreSQL, Pix, boleto, cartÃ£o,
Asaas, contrato comercial ou homologaÃ§Ã£o. A inspeÃ§Ã£o visual autenticada do
console nÃ£o foi automatizada porque ela exigiria inserir uma credencial no
navegador; nenhum ambiente externo foi acessado.

## V-086 â€” HistÃ³rico do Copiloto sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporÃ¡rio e demonstraÃ§Ã£o
fictÃ­cia. NÃ£o houve pergunta enviada, chamada de IA, curadoria, treinamento,
upload, credencial externa, custo, deploy ou dado de cliente.

- O Copiloto deixou de exibir somente as 12 conversas abertas mais recentes:
  agora pagina 12 registros, informa o total e preserva tanto a conversa ativa
  quanto a pÃ¡gina do histÃ³rico ao navegar.
- O teste com 13 conversas sintÃ©ticas confirmou a segunda pÃ¡gina, a conversa
  mais antiga selecionada e os vÃ­nculos de pÃ¡gina, sem criar mensagem nem
  acionar runtime, fallback ou egressÃ£o.
- A demonstraÃ§Ã£o local confirmou, em 390 px, a superfÃ­cie mÃ³vel do Copiloto
  sem overflow horizontal ou erro de console. Como ela nÃ£o contÃ©m conversas,
  nÃ£o foi usada como prova visual de paginaÃ§Ã£o em volume.
- **49 testes** de IA passaram, com **3 subtestes** aprovados; Ruff e MyPy
  global aprovaram os **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **776 testes aprovados, 3 skips e 11
  subtestes aprovados** em 38,46 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- ApÃ³s `git fetch origin --prune`, `HEAD` permaneceu **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**. As 94 alteraÃ§Ãµes locais existentes foram
  preservadas antes do registro desta entrega.

Limites: a evidÃªncia usa apenas conversas sintÃ©ticas locais; nÃ£o comprova
chamada Claude, runtime local definitivo, curadoria, treinamento, dados reais,
PostgreSQL, latÃªncia ou homologaÃ§Ã£o operacional. O banco, servidor, navegador e
diretÃ³rios temporÃ¡rios de QA foram encerrados; os artefatos temporÃ¡rios foram
movidos Ã  Lixeira de forma recuperÃ¡vel.

## V-085 â€” Trilhas de ConciliaÃ§Ã£o sem cortes silenciosos

Data: 21/09/2026. Ambiente: macOS local, SQLite temporÃ¡rio e demonstraÃ§Ã£o
fictÃ­cia. NÃ£o houve importaÃ§Ã£o, reprocessamento, geraÃ§Ã£o, download ou
confirmaÃ§Ã£o de arquivo, conexÃ£o a ERP, custo, deploy ou dado de cliente.

- As trilhas de processamentos e de exportaÃ§Ãµes da ConciliaÃ§Ã£o deixaram de
  cortar os 12 e 8 registros mais recentes: cada uma agora pagina 20 itens,
  informa seu total e mantÃ©m os parÃ¢metros e a pÃ¡gina da outra trilha.
- O teste criou 21 execuÃ§Ãµes e 21 exportaÃ§Ãµes sintÃ©ticas, chegou Ã  pÃ¡gina 2 de
  cada histÃ³rico e confirmou que trocar uma pÃ¡gina nÃ£o desloca a outra nem
  executa qualquer aÃ§Ã£o operacional.
- A demonstraÃ§Ã£o local confirmou, em 390 px, as Ã¡reas de Processamentos e
  ExportaÃ§Ãµes sem overflow horizontal ou erro de console. Ela nÃ£o representa
  21 registros nas trilhas e nÃ£o foi usada como prova visual de volume.
- **93 testes** de ConciliaÃ§Ã£o e espaÃ§o de trabalho passaram, com **1 skip** de
  OCR local, em 21,74 s; Ruff e MyPy global aprovaram os **190 arquivos** de
  cÃ³digo.
- A regressÃ£o integral fechou com **775 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,25 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- ApÃ³s `git fetch origin --prune`, `HEAD` permaneceu **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**. As 91 alteraÃ§Ãµes locais foram preservadas antes do
  registro desta entrega.

Limites: a evidÃªncia usa somente execuÃ§Ãµes e exportaÃ§Ãµes sintÃ©ticas locais; nÃ£o
comprova arquivos reais, OFX, OCR, DomÃ­nio, Siescon, importaÃ§Ã£o no destino,
PostgreSQL, latÃªncia ou homologaÃ§Ã£o operacional. O banco, servidor, navegador e
diretÃ³rio temporÃ¡rios de QA foram encerrados; os artefatos temporÃ¡rios foram
movidos Ã  Lixeira de forma recuperÃ¡vel.

## V-084 â€” HistÃ³rico de importaÃ§Ãµes sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporÃ¡rio e demonstraÃ§Ã£o
fictÃ­cia. NÃ£o houve envio, confirmaÃ§Ã£o ou processamento de arquivo, conexÃ£o
DomÃ­nio, credencial externa, custo, deploy ou dado de cliente.

- A seÃ§Ã£o de importaÃ§Ãµes do onboarding deixou de exibir somente os oito lotes
  mais recentes: agora pagina 20 registros, informa o total e preserva fonte e
  prÃ©via selecionadas na navegaÃ§Ã£o.
- O teste com 21 lotes sintÃ©ticos alcanÃ§ou a pÃ¡gina 2, conservou a fonte e
  conferiu total, vÃ­nculos e pÃ¡gina sem alterar lote ou dados importados.
- A demonstraÃ§Ã£o local contÃ©m zero importaÃ§Ãµes; ela confirmou somente a seÃ§Ã£o
  vazia em 390 px, sem overflow horizontal ou erros de console, e nÃ£o foi usada
  como prova visual da paginaÃ§Ã£o em volume.
- **57 testes** de espaÃ§o de trabalho e backup passaram em 19,20 s; Ruff e MyPy
  global aprovaram os **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **774 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,59 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- ApÃ³s `git fetch origin --prune`, `HEAD` permaneceu **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**. As 90 alteraÃ§Ãµes locais foram preservadas antes do
  registro desta entrega.

Limites: a evidÃªncia usa apenas lotes sintÃ©ticos locais; nÃ£o comprova upload,
backup `.dom`, chave, extraÃ§Ã£o, DomÃ­nio, agente Windows, volume em PostgreSQL,
latÃªncia ou homologaÃ§Ã£o operacional. O banco, servidor, navegador e diretÃ³rio
temporÃ¡rios de QA foram encerrados; os artefatos temporÃ¡rios foram movidos Ã 
Lixeira de forma recuperÃ¡vel.

## V-083 â€” HistÃ³rico DTE sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporÃ¡rio e demonstraÃ§Ã£o
fictÃ­cia. NÃ£o houve preparaÃ§Ã£o de consulta, acesso ao Serpro, certificado,
credencial externa, consumo, custo, deploy ou dado de cliente.

- O histÃ³rico de resultados DTE deixou de cortar os 30 registros mais recentes:
  agora pagina 30 itens, informa o total e conserva a pÃ¡gina atual da fila de
  mensagens, filtros e empresa na navegaÃ§Ã£o prÃ³pria.
- O teste com 31 itens e execuÃ§Ãµes DTE sintÃ©ticos alcanÃ§ou a pÃ¡gina 2, manteve a
  fila de mensagens na pÃ¡gina 1 e conferiu total, navegaÃ§Ã£o e parÃ¢metros sem
  alterar resultado ou autorizaÃ§Ã£o.
- Na demonstraÃ§Ã£o local, a tela DTE vazia e a Ã¡rea de histÃ³rico renderizaram em
  390 px sem overflow horizontal ou erros de console. Como ela contÃ©m zero
  resultados preparados, nÃ£o foi usada como prova visual de paginaÃ§Ã£o em volume.
- **75 testes** de DTE e espaÃ§o de trabalho passaram em 14,80 s; Ruff e MyPy
  global aprovaram os **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **773 testes aprovados, 3 skips e 11
  subtestes aprovados** em 36,37 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- ApÃ³s `git fetch origin --prune`, `HEAD` permaneceu **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**. As 89 alteraÃ§Ãµes locais foram preservadas antes do
  registro desta entrega.

Limites: a evidÃªncia usa apenas estado DTE sintÃ©tico e local; nÃ£o comprova
consulta, ciÃªncia, certificado, Serpro, consumo, retorno de produÃ§Ã£o,
PostgreSQL, latÃªncia ou homologaÃ§Ã£o fiscal. O banco, servidor, navegador e
diretÃ³rio temporÃ¡rios de QA foram encerrados; os artefatos temporÃ¡rios foram
movidos Ã  Lixeira de forma recuperÃ¡vel.

## V-082 â€” HistÃ³rico de cobranÃ§a manual sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local e banco de testes, com faturas
exclusivamente sintÃ©ticas. NÃ£o houve criaÃ§Ã£o de cobranÃ§a, Asaas, chave,
cartÃ£o, Pix, boleto, credencial externa, custo, deploy ou dado de cliente.

- O console da plataforma deixou de limitar o histÃ³rico Ã s 12 faturas mais
  recentes: ele agora pagina 12 registros, informa o total e mantÃ©m os dados
  restritos ao escritÃ³rio aberto.
- O teste com 25 faturas sintÃ©ticas alcanÃ§ou a pÃ¡gina 3, preservou o vÃ­nculo de
  retorno e conferiu o total sem alterar fatura, contrato ou status.
- **41 testes** de console, cobranÃ§a e contratos passaram em 12,67 s; Ruff e
  MyPy global aprovaram os **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **772 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,26 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- ApÃ³s `git fetch origin --prune`, `HEAD` permaneceu **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**. As 87 alteraÃ§Ãµes locais foram preservadas.

Limites: a evidÃªncia cobre registros locais sintÃ©ticos e nÃ£o comprova cobranÃ§a
real, Asaas, Pix, boleto, cartÃ£o, estorno, concorrÃªncia em PostgreSQL ou
homologaÃ§Ã£o comercial. A inspeÃ§Ã£o visual autenticada do console nÃ£o foi
automatizada porque ela exigiria inserir uma credencial; isso permanece aberto
na etapa 11.

## V-081 â€” Radar da Reforma sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporÃ¡rio e navegador interno,
com alertas exclusivamente fictÃ­cios. NÃ£o houve coleta de fontes, navegaÃ§Ã£o a
URLs oficiais, credencial, custo, deploy ou dado de cliente.

- A consulta local do Radar deixou de exibir apenas os primeiros 80 alertas:
  agora pagina 50 registros, preservando termo, fonte e tema, e mantÃ©m o total
  correspondente ao filtro.
- O teste criou 101 alertas sintÃ©ticos, alcanÃ§ou a pÃ¡gina 3 e verificou os
  totais e o vÃ­nculo de retorno com os trÃªs filtros preservados.
- A demonstraÃ§Ã£o deliberadamente contÃ©m somente trÃªs exemplos; sua busca por
  IBS exibiu o aviso de conteÃºdo fictÃ­cio e um resultado, sem erro de console
  ou overflow horizontal em 390 px. Ela nÃ£o foi usada para alegar inspeÃ§Ã£o
  visual da paginaÃ§Ã£o em volume.
- **77 testes** de espaÃ§o de trabalho, Radar e demonstraÃ§Ã£o passaram em 20,62
  s; Ruff e MyPy global aprovaram os **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **771 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,73 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- ApÃ³s `git fetch origin --prune`, `HEAD` permaneceu **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**. As 85 alteraÃ§Ãµes locais foram preservadas.

Limites: a prova contÃ©m somente alertas sintÃ©ticos e filtros locais; nÃ£o
comprova fonte oficial, atualizaÃ§Ã£o, classificaÃ§Ã£o, disponibilidade, volume em
PostgreSQL, latÃªncia ou homologaÃ§Ã£o do Radar. O banco, servidor, navegador e
diretÃ³rio temporÃ¡rios de QA foram encerrados; o diretÃ³rio foi movido para a
Lixeira de forma recuperÃ¡vel.

## V-080 â€” Auditoria de conciliaÃ§Ã£o sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, SQLite temporÃ¡rio e navegador interno,
com eventos de auditoria exclusivamente fictÃ­cios. NÃ£o houve OFX, DomÃ­nio,
ERP, fonte externa, credencial, custo, deploy ou dado de cliente.

- A trilha de auditoria da conciliaÃ§Ã£o deixou de limitar a consulta aos
  primeiros 200 eventos: ela agora pagina 100 registros, mantÃ©m a aÃ§Ã£o filtrada
  na navegaÃ§Ã£o e informa o total que corresponde ao filtro.
- O teste criou 201 eventos sintÃ©ticos, alcanÃ§ou a pÃ¡gina 3 e confirmou tanto
  o total quanto os vÃ­nculos que preservam a aÃ§Ã£o ao retornar de pÃ¡gina.
- A inspeÃ§Ã£o da demonstraÃ§Ã£o temporÃ¡ria abriu a pÃ¡gina 3 de 3 com o filtro
  aplicado, voltou Ã  pÃ¡gina 2 e manteve os 201 eventos; nÃ£o houve erro de
  console ou overflow horizontal em 390 px.
- **90 testes** de conciliaÃ§Ã£o e espaÃ§o de trabalho passaram em 15,60 s; Ruff
  e MyPy global aprovaram os **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **770 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,37 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- ApÃ³s `git fetch origin --prune`, `HEAD` permaneceu **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**. As 84 alteraÃ§Ãµes locais foram preservadas.

Limites: a prova contÃ©m somente auditoria sintÃ©tica; nÃ£o comprova importaÃ§Ã£o
OFX, OCR, fonte DomÃ­nio, ERP, volume em PostgreSQL, latÃªncia ou homologaÃ§Ã£o de
exportaÃ§Ã£o. O banco, servidor, navegador e diretÃ³rio temporÃ¡rios de QA foram
encerrados; o diretÃ³rio foi movido para a Lixeira de forma recuperÃ¡vel.

## V-079 â€” Ficha da empresa sem cortes de histÃ³rico

Data: 21/09/2026. Ambiente: macOS local, SQLite temporÃ¡rio e navegador interno,
com NFS-e, revisÃµes e mensagens DTE exclusivamente fictÃ­cias. NÃ£o houve ADN,
Serpro, certificado real, credencial externa, custo, deploy ou dado de cliente.

- A ficha da empresa passou a paginar independentemente os documentos NFS-e,
  revisÃµes abertas e mensagens DTE, todos em pÃ¡ginas de 20 itens; parÃ¢metros de
  retorno e pÃ¡ginas das demais seÃ§Ãµes permanecem intactos.
- O teste criou 21 itens em cada histÃ³rico, chegou Ã  pÃ¡gina 2 e verificou os
  totais e os vÃ­nculos de navegaÃ§Ã£o entre as seÃ§Ãµes.
- A inspeÃ§Ã£o do escritÃ³rio-demo temporÃ¡rio abriu a pÃ¡gina 2 das trÃªs seÃ§Ãµes,
  retornou a DTE Ã  pÃ¡gina 1 sem perder as demais, nÃ£o registrou erro de console
  e nÃ£o apresentou overflow horizontal em 390 px.
- **72 testes** de registro de empresas e espaÃ§o de trabalho passaram em 14,94
  s; Ruff e MyPy global aprovaram os **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **769 testes aprovados, 3 skips e 11
  subtestes aprovados** em 29,38 s.
- ApÃ³s `git fetch origin --prune`, `HEAD` permaneceu **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**. As 83 alteraÃ§Ãµes locais foram preservadas.

Limites: a prova usa apenas estado sintÃ©tico; nÃ£o comprova coleta ADN, acesso
DTE/Serpro, certificados, protocolos, representaÃ§Ã£o, PostgreSQL, latÃªncia ou
homologaÃ§Ã£o fiscal. O banco, servidor, navegador e diretÃ³rio temporÃ¡rios de QA
foram encerrados; o diretÃ³rio foi movido para a Lixeira de forma recuperÃ¡vel.

## V-078 â€” Cobertura de certificados paginada sem ocultar empresas

Data: 21/09/2026. Ambiente: macOS local, SQLite temporÃ¡rio e navegador interno,
com empresas e identificadores exclusivamente fictÃ­cios. NÃ£o houve certificado
real, ADN, credencial externa, custo, deploy ou dado de cliente.

- A cobertura de empresas sem certificado A1 vÃ¡lido deixou de cortar apÃ³s 20
  registros: a lista e o seletor da demonstraÃ§Ã£o agora seguem pÃ¡ginas prÃ³prias,
  separadas da carteira de certificados.
- O teste criou 21 empresas sem A1, abriu a pÃ¡gina 2 e comprovou a preservaÃ§Ã£o
  de busca e situaÃ§Ã£o na volta para a pÃ¡gina 1.
- A inspeÃ§Ã£o visual no escritÃ³rio-demo temporÃ¡rio alcanÃ§ou a pÃ¡gina 2 de 2 de
  uma cobertura com 25 empresas, retornou Ã  pÃ¡gina 1, nÃ£o registrou erro de
  console e nÃ£o apresentou overflow horizontal em 390 px.
- **70 testes** de espaÃ§o de trabalho e fiscal passaram em 16,66 s; Ruff e
  MyPy global aprovaram os **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **768 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,57 s.
- ApÃ³s `git fetch origin --prune`, `HEAD` permaneceu **0 commits Ã  frente e 0
  atrÃ¡s de `origin/main`**. As 81 alteraÃ§Ãµes locais foram preservadas.

Limites: a prova usa somente estado sintÃ©tico; nÃ£o comprova validade/custÃ³dia
de A1, coleta ADN, NSU, mTLS, catÃ¡logo de acumuladores, PostgreSQL, latÃªncia ou
homologaÃ§Ã£o fiscal. O banco, servidor, navegador e diretÃ³rio temporÃ¡rios de QA
foram encerrados; o diretÃ³rio foi movido para a Lixeira de forma recuperÃ¡vel.

## V-077 â€” HistÃ³rico de Parcelamentos recuperÃ¡vel por pÃ¡gina

Data: 21/09/2026. Ambiente: macOS local, banco SQLite temporÃ¡rio e navegador
interno, com operaÃ§Ãµes PARCSN exclusivamente fictÃ­cias. NÃ£o houve Serpro,
credencial externa, custo, deploy ou dado de cliente.

- O histÃ³rico da empresa em Parcelamentos deixou de cortar silenciosamente apÃ³s
  20 operaÃ§Ãµes: ele agora pagina o histÃ³rico sem interferir na paginaÃ§Ã£o da
  carteira.
- A inspeÃ§Ã£o visual criou 21 operaÃ§Ãµes sintÃ©ticas de resultado incerto, abriu a
  pÃ¡gina 2 e retornou Ã  pÃ¡gina 1 preservando a empresa em foco, sem erro de
  console. O aviso de recuperaÃ§Ã£o permaneceu visÃ­vel em cada tentativa.
- **77 testes** de Parcelamentos, espaÃ§o de trabalho e Guias passaram em 16,17
  s; Ruff e MyPy global aprovaram os **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **767 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,64 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- A consulta remota apÃ³s `git fetch origin --prune` confirmou **0 commits Ã 
  frente e 0 atrÃ¡s de `origin/main`**. O diretÃ³rio local permanece com 80
  alteraÃ§Ãµes de trabalho, preservadas nesta verificaÃ§Ã£o.

Limites: a prova usa apenas estado sintÃ©tico; nÃ£o comprova PARCSN/Serpro,
protocolos reais, consumo, representaÃ§Ã£o, volume em PostgreSQL, latÃªncia ou
homologaÃ§Ã£o fiscal. O banco e o servidor temporÃ¡rios foram encerrados, e o
diretÃ³rio de QA foi movido para a Lixeira de forma recuperÃ¡vel.

## V-076 â€” Fila de conciliaÃ§Ã£o paginada sem ocultar evidÃªncias

Data: 21/09/2026. Ambiente: macOS local e banco de testes. NÃ£o houve OFX de
cliente, DomÃ­nio, OCR, fonte externa, credencial, custo ou deploy.

- A fila OFX Ã— DomÃ­nio deixou de cortar silenciosamente nos primeiros 100
  resultados: ela agora pagina 50 linhas, preservando busca e situaÃ§Ã£o.
- A busca de candidatos e a composiÃ§Ã£o das evidÃªncias continuam restritas aos
  itens visÃ­veis na pÃ¡gina, sem ampliar consultas desnecessÃ¡rias Ã  carteira.
- O teste de integraÃ§Ã£o renderizou 101 correspondÃªncias sem par, alcanÃ§ou a
  pÃ¡gina 3 e confirmou o retorno Ã  pÃ¡gina 2 com filtros preservados.
- **95 testes** de conciliaÃ§Ã£o, espaÃ§o de trabalho e Parcelamentos passaram,
  com um skip esperado de OCR em portuguÃªs; Ruff e MyPy global aprovaram os
  **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **766 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,14 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- `git fetch origin --prune` e `HEAD...origin/main` retornaram **0/0**: nÃ£o hÃ¡
  commit do GitHub ausente localmente nem commit local Ã  frente.

Limites: a demonstraÃ§Ã£o contÃ©m deliberadamente apenas duas conciliaÃ§Ãµes e nÃ£o
permite provar visualmente a terceira pÃ¡gina sem uma sessÃ£o nÃ£o demonstrativa.
O teste autenticado de integraÃ§Ã£o cobre a renderizaÃ§Ã£o dessa pÃ¡gina; isto nÃ£o
comprova volume em PostgreSQL, importaÃ§Ã£o OFX real, OCR, fonte DomÃ­nio ou
homologaÃ§Ã£o de exportaÃ§Ã£o. O checkout preserva 80 alteraÃ§Ãµes locais ainda nÃ£o
commitadas.

## V-075 â€” Carteira de Parcelamentos paginada por lote autorizado

Data: 21/09/2026. Ambiente: macOS local, banco SQLite temporÃ¡rio e navegador
interno, com empresas exclusivamente fictÃ­cias. NÃ£o houve Serpro, PARCSN real,
DomÃ­nio, credencial externa, custo, deploy ou dado de cliente.

- A carteira de Parcelamentos deixou de esconder empresas apÃ³s os primeiros 100
  registros: ela agora pagina 30 empresas por pÃ¡gina e preserva a pesquisa.
- O limite de 30 por pÃ¡gina foi escolhido para coincidir com o mÃ¡ximo do lote
  jÃ¡ imposto pelo backend; portanto, â€œSelecionar todas desta pÃ¡ginaâ€ nÃ£o monta
  uma solicitaÃ§Ã£o invÃ¡lida por excesso de empresas.
- A inspeÃ§Ã£o com 101 empresas sintÃ©ticas alcanÃ§ou a pÃ¡gina 4 de 4, exibiu o
  Ãºltimo registro e retornou Ã  pÃ¡gina 3 mantendo a busca, sem erro de console.
- **76 testes** de Parcelamentos, espaÃ§o de trabalho e Guias passaram em 15,11
  s; Ruff e MyPy global aprovaram, este Ãºltimo nos **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **765 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,37 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- `git fetch origin --prune` e `HEAD...origin/main` retornaram **0/0**: nÃ£o hÃ¡
  commit do GitHub ausente localmente nem commit local Ã  frente.

Limites: a prova usa empresas e sessÃ£o sintÃ©ticas; nÃ£o comprova PARCSN/Serpro,
protocolos, representaÃ§Ã£o, consumo real, volume em PostgreSQL, latÃªncia ou
homologaÃ§Ã£o fiscal. O banco e o servidor temporÃ¡rios foram encerrados, e o
diretÃ³rio de QA foi movido para a Lixeira de forma recuperÃ¡vel. O checkout
preserva 78 alteraÃ§Ãµes locais ainda nÃ£o commitadas.

## V-074 â€” Carteira de guias sem corte silencioso

Data: 21/09/2026. Ambiente: macOS local, banco SQLite temporÃ¡rio e navegador
interno, com guias exclusivamente fictÃ­cias. NÃ£o houve Serpro, DCTFWeb real,
DomÃ­nio, credencial externa, custo, deploy ou dado de cliente.

- A lista de Guias e DCTFWeb agora pagina resultados acima de 100 itens e
  preserva busca, situaÃ§Ã£o e vencimento nos links de navegaÃ§Ã£o.
- O teste de interface criou 101 guias sintÃ©ticas: a pÃ¡gina 2 de 2 exibiu a
  guia final, e o retorno Ã  pÃ¡gina 1 manteve os filtros. NÃ£o houve erro no
  console do navegador.
- **88 testes** de guias, espaÃ§o de trabalho e demonstraÃ§Ã£o passaram em 21,08
  s; Ruff e MyPy global aprovaram, este Ãºltimo nos **190 arquivos** de cÃ³digo.
- A regressÃ£o integral fechou com **764 testes aprovados, 3 skips e 11
  subtestes aprovados** em 29,19 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- `git fetch origin --prune` e `HEAD...origin/main` retornaram **0/0**: nÃ£o hÃ¡
  commit do GitHub ausente localmente nem commit local Ã  frente.

Limites: a prova usa dados e sessÃ£o sintÃ©ticos; nÃ£o comprova DCTFWeb/Serpro,
protocolos, representaÃ§Ã£o, catÃ¡logo real de acumuladores, volume em PostgreSQL,
latÃªncia ou homologaÃ§Ã£o fiscal. O banco e o servidor temporÃ¡rios foram
encerrados, e o diretÃ³rio de QA foi movido para a Lixeira de forma recuperÃ¡vel.
O checkout preserva 76 alteraÃ§Ãµes locais ainda nÃ£o commitadas.

## V-073 â€” RevisÃ£o NFS-e completa e carteira paginada localmente

Data: 21/09/2026. Ambiente: macOS local, banco SQLite temporÃ¡rio e navegador
interno, com documentos exclusivamente fictÃ­cios. NÃ£o houve ADN, certificado,
Serpro, DomÃ­nio, credencial externa, custo, deploy ou dado de cliente.

- O detalhe de revisÃ£o passou a exibir nÃºmero, emissÃ£o/competÃªncia, cÃ³digo e
  descriÃ§Ã£o do serviÃ§o, valor em moeda e referÃªncia pseudonimizada da
  contraparte, alÃ©m de sugestÃ£o, confianÃ§a, XML e decisÃ£o humana jÃ¡ existentes.
- A semente de demonstraÃ§Ã£o agora preenche nÃºmero e descriÃ§Ã£o explicitamente
  fictÃ­cios, sem representar coleta fiscal real.
- A carteira NFS-e deixou de cortar silenciosamente nos primeiros 100 itens:
  paginaÃ§Ã£o preserva a busca e expÃµe a quantidade total. A inspeÃ§Ã£o no navegador
  alcanÃ§ou a pÃ¡gina 2 de 2 e retornou Ã  pÃ¡gina 1 com o filtro preservado. O
  detalhe de revisÃ£o nÃ£o teve overflow em 390 px, nem houve erro de console.
- **79 testes** fiscais/demonstraÃ§Ã£o passaram em 21,63 s; Ruff e MyPy global
  aprovaram, este Ãºltimo nos **190 arquivos** de cÃ³digo-fonte.
- A regressÃ£o integral fechou com **763 testes aprovados, 3 skips e 11
  subtestes aprovados** em 28,04 s; Django e migraÃ§Ãµes nÃ£o apontaram erro ou
  drift.
- `git fetch origin --prune` e `HEAD...origin/main` retornaram **0/0**: nÃ£o hÃ¡
  commit do GitHub ausente localmente nem commit local Ã  frente.

Limites: a prova usa XML e sessÃ£o sintÃ©ticos; nÃ£o comprova coleta ADN,
certificados, cobertura de fonte, catÃ¡logo real de acumuladores, volume em
PostgreSQL, latÃªncia ou homologaÃ§Ã£o fiscal. O banco e o servidor temporÃ¡rios
foram encerrados, e o diretÃ³rio de QA foi movido para a Lixeira. O checkout
preserva 74 alteraÃ§Ãµes locais ainda nÃ£o commitadas.

## V-072 â€” Runtime privado priorizado e fallback externo negado sem opt-in

Data: 21/09/2026. Ambiente: macOS local, banco de testes e respostas HTTP
simuladas; nÃ£o houve runtime de modelo, chamada Claude, credencial real, custo,
deploy ou dado de cliente.

- O contrato OpenAI-compatÃ­vel do runtime privado recebeu pergunta e evidÃªncia
  compacta; a resposta simulada foi usada pelo Copiloto.
- Mesmo com fallback externo configurado e aprovado no cenÃ¡rio de teste, a
  resposta local nÃ£o chamou o provedor nem criou auditoria de egressÃ£o.
- A suÃ­te tambÃ©m mantÃ©m a prova complementar: sem opt-in do escritÃ³rio, o
  fallback Ã© negado, nÃ£o chama o provedor e registra a negaÃ§Ã£o para auditoria.
- `pytest` focado aprovou **73 testes e 3 subtestes** em 15,17 s; Ruff e MyPy
  global aprovaram, este Ãºltimo nos **190 arquivos** de cÃ³digo-fonte.
- `git fetch origin --prune` e `HEAD...origin/main` retornaram **0/0**: nÃ£o hÃ¡
  commit do GitHub ausente localmente nem commit local Ã  frente.

Limites: a resposta HTTP foi simulada; nÃ£o mede modelo, GPU, rede privada,
latÃªncia, credenciais, custo, autorizaÃ§Ã£o real de egressÃ£o ou homologaÃ§Ã£o. O
checkout preserva 70 alteraÃ§Ãµes locais ainda nÃ£o commitadas.

## V-071 â€” MÃ³dulos fictÃ­cios e Copiloto inspecionados ponta a ponta

Data: 21/09/2026. Ambiente: navegador interno e base SQLite temporÃ¡ria com
semente fictÃ­cia. NÃ£o houve API Claude, Serpro, e-mail, DomÃ­nio, arquivo ou
dado de cliente.

- Guias/DCTFWeb, Caixa DTE, Parcelamentos, ConciliaÃ§Ã£o, Radar e Copiloto
  renderizaram com tÃ­tulo correto, aviso de demonstraÃ§Ã£o e sem erro de console.
- O Copiloto recusou o envio sem empresa; apÃ³s escolher empresa fictÃ­cia e usar
  uma pergunta sugerida, entregou resposta simulada com fontes expandÃ­veis que
  identificam carteira, DTE e Triagem como dados sintÃ©ticos.

Limites: esta Ã© uma jornada simulada por sessÃ£o; nÃ£o prova egressÃ£o, modelo,
autorizaÃ§Ã£o real, consumo, identidade de fonte externa, latÃªncia ou produÃ§Ã£o.

## V-070 â€” Auditoria local de revisÃ£o fiscal e isolamento do console

Data: 21/09/2026. Ambiente: navegador interno e base SQLite temporÃ¡ria, com
sementes fictÃ­cias de demonstraÃ§Ã£o e personas. NÃ£o houve conta, documento,
credencial ou serviÃ§o externo.

- A demonstraÃ§Ã£o isolada abriu a fila de revisÃµes NFS-e, exibiu empresa,
  documento, hash, motivo, evidÃªncia, confianÃ§a, XML e a decisÃ£o explÃ­cita sem
  prometer alteraÃ§Ã£o no DomÃ­nio. O retorno Ã  fila permaneceu disponÃ­vel.
- A tentativa da mesma sessÃ£o de abrir `/platform/` recebeu a pÃ¡gina de acesso
  restrito; assim, o ambiente de demonstraÃ§Ã£o nÃ£o ganhou acesso ao console
  Mewstack. NÃ£o houve erro de console nas jornadas adicionais.

Limites: a inspeÃ§Ã£o visual do console autenticado permanece pendente porque ela
exigiria inserir credencial, e nÃ£o foi automatizada. A evidÃªncia prova somente
o bloqueio da persona fictÃ­cia, nÃ£o todos os papÃ©is de plataforma nem produÃ§Ã£o.

## V-069 â€” Auditoria visual local de jornadas pÃºblicas e fictÃ­cias

Data: 21/09/2026. Ambiente: navegador interno e base SQLite temporÃ¡ria migrada
e sem dados reais. NÃ£o houve credencial externa, envio de e-mail, chamada a
provedor, custo, deploy ou alteraÃ§Ã£o em banco persistente.

- A pÃ¡gina comercial carregou com seus recursos estÃ¡ticos em servidor local de
  QA; a demonstraÃ§Ã£o alternou abas por clique e teclado, atualizou a URL e
  expandiu a FAQ. O cadastro pÃºblico expÃ´s rÃ³tulos e impedimento nativo para
  campo obrigatÃ³rio vazio.
- Em viewport mÃ³vel de 390Ã—844, a pÃ¡gina nÃ£o teve overflow horizontal, manteve
  21 controles focÃ¡veis e preservou a aba/painel selecionados. NÃ£o houve erro
  de console nas superfÃ­cies verificadas.
- Com semente exclusivamente fictÃ­cia e isolamento de sessÃ£o habilitado no
  servidor de QA, a entrada chegou ao dashboard, Ã  navegaÃ§Ã£o de Documentos e Ã 
  Triagem. Um anexo em quarentena informou de forma explÃ­cita que nÃ£o pode ser
  aberto ou baixado.

Limites: o Mac estava bloqueado para automaÃ§Ã£o nativa e a auditoria nÃ£o cobre
console Mewstack, todos os perfis, todos os estados de falha, leitor de tela
nativo, integraÃ§Ãµes ou ambiente publicado. O servidor de QA usou `DEBUG` e
arquivos estÃ¡ticos servidos localmente; isto nÃ£o Ã© prova de produÃ§Ã£o.

## V-068 â€” View Hub integralmente tipada e regressÃ£o local focada

Data: 21/09/2026. Ambiente: macOS local, banco de testes e dados sintÃ©ticos.
NÃ£o houve Serpro, ADN, caixa de e-mail, DomÃ­nio, credencial, custo, deploy ou
alteraÃ§Ã£o operacional.

- Os fluxos de conciliaÃ§Ã£o, Triagem, certificados, setup e aceite de tokens
  passaram a estreitar usuÃ¡rio autenticado, identificadores opcionais,
  apresentaÃ§Ãµes e respostas de arquivo de forma explÃ­cita. NÃ£o houve alteraÃ§Ã£o
  de regra de negÃ³cio, integraÃ§Ã£o ou persistÃªncia adicional.
- Ruff e MyPy passaram em `apps/hub/views.py`; **119 testes passaram** em
  **14,93 s**, com **1 skip** esperado de OCR local em portuguÃªs. `mypy .`
  passou nos **190 arquivos** verificados; `git diff --check` passou.
- A regressÃ£o integral repetiu `manage.py check`, migraÃ§Ãµes sem alteraÃ§Ãµes e
  **762 testes aprovados, 3 skips e 11 subtestes aprovados em 27,70 s**.
- `git fetch origin --prune` e a comparaÃ§Ã£o `HEAD...origin/main` retornaram
  **0/0**: nÃ£o hÃ¡ commit remoto ausente localmente, nem commit local Ã  frente.
  O checkout preserva 68 alteraÃ§Ãµes locais nÃ£o commitadas desta execuÃ§Ã£o.

Limites: os skips permanecem Playwright Python opcional, OCR local em portuguÃªs
indisponÃ­vel e concorrÃªncia de locks exclusiva de PostgreSQL. O resultado Ã©
exclusivamente local e nÃ£o homologa provedores de e-mail, ADN, Serpro, DomÃ­nio,
layouts reais, fontes Radar ou conectores.

## V-067 â€” NFS-e e DCTFWeb da view Hub refinados localmente

Data: 21/09/2026. Ambiente: macOS local. Sem Serpro, ADN, DomÃ­nio, credencial,
custo, deploy ou alteraÃ§Ã£o operacional.

- A view passou a explicitar coleÃ§Ãµes NFS-e, contexto do escritÃ³rio, campos
  numÃ©ricos heterogÃªneos, expoente decimal, UUID e cotaÃ§Ãµes DCTFWeb.
- Ruff passou; **20 testes** de NFS-e/DCTFWeb passaram em **13,49 s** e `git
  diff --check` estÃ¡ limpo.

Limites: as integraÃ§Ãµes fiscais seguem sem homologaÃ§Ã£o externa.

## V-066 â€” Primeira seÃ§Ã£o da view do Hub tipada e retestada

Data: 21/09/2026. Ambiente: macOS local, banco de testes. NÃ£o houve conexÃ£o
externa, credencial, custo, deploy ou alteraÃ§Ã£o operacional.

- As rotas de demonstraÃ§Ã£o, dashboard, convites, permissÃµes de mÃ³dulo, despacho
  NFS-e e filtros receberam contratos estÃ¡ticos explÃ­citos, sem mudar seus
  fluxos de negÃ³cio.
- Ruff e MyPy passaram na seÃ§Ã£o alterada; **86 testes** de workspace,
  demonstraÃ§Ã£o, convite e NFS-e passaram em **20,69 s**. `git diff --check`
  passou. A dÃ­vida da view do Hub reduziu de 131 para **114 erros**.

Limites: toda evidÃªncia Ã© local e sintÃ©tica; integraÃ§Ãµes e homologaÃ§Ãµes externas
das etapas 07â€“12 permanecem pendentes.

## V-065 â€” ServiÃ§os, agente e interface de IA com contratos tipados

Data: 21/09/2026. Ambiente: macOS local, banco e transportes sintÃ©ticos. NÃ£o
houve Claude, DomÃ­nio, agente Windows, credencial, custo, deploy ou alteraÃ§Ã£o
operacional.

- A reserva do Copiloto declara os livros token/legado e exige reserva antes do
  fallback; a API do agente tipa chave da CA, respostas de arquivo e lote de
  backup; e a tela do Copiloto conserva o estado transitÃ³rio de entrega apenas
  na apresentaÃ§Ã£o, sem acrescentÃ¡-lo ao modelo persistido.
- Ruff e MyPy passaram nos trÃªs mÃ³dulos. As suÃ­tes de Copiloto, agente,
  backup e interface fecharam com **68 aprovados em 28,13 s**. `git diff
  --check` passou. MyPy global baixou para **131 erros em 1 arquivo**.

Limites: nenhuma chave, saÃ­da Claude, agente, documento ou dado de cliente foi
usado. Curadoria, egressÃ£o autorizada e homologaÃ§Ãµes das etapas 05/12 continuam
pendentes.

## V-064 â€” OperaÃ§Ãµes Integra e sincronizaÃ§Ã£o ADN com contratos tipados

Data: 21/09/2026. Ambiente: macOS local, banco e transportes sintÃ©ticos. NÃ£o
houve Serpro, ADN, DomÃ­nio, credencial, custo, deploy ou alteraÃ§Ã£o operacional.

- Os mapas de operaÃ§Ã£o PARCSN/DCTFWeb aceitam chaves de entrada validadas; a
  aprovaÃ§Ã£o DTE separa cotaÃ§Ã£o e reserva dos livros token/legado; tarefas
  tipam sua queryset NFS-e, despacho pÃ³s-commit e resultados PARCSN; e a
  validaÃ§Ã£o NFS-e confirma explicitamente o expoente decimal.
- Ruff e MyPy passaram nos trÃªs mÃ³dulos. As suÃ­tes de DTE, guias, DCTFWeb,
  PARCSN e NFS-e fecharam com **57 aprovados em 15,62 s**. `git diff --check`
  passou. MyPy global baixou para **143 erros em 4 arquivos**.

Limites: conexÃµes, certificados, documentos e respostas eram sintÃ©ticos. As
homologaÃ§Ãµes Serpro, ADN e DomÃ­nio das etapas 07, 08, 09 e 12 continuam pendentes.

## V-063 â€” RegressÃ£o integral apÃ³s os lotes locais V-060 a V-062

Data: 21/09/2026. Ambiente: macOS local. NÃ£o houve conexÃ£o externa,
credencial, custo, deploy ou alteraÃ§Ã£o operacional.

- `manage.py check` e `makemigrations --check --dry-run` nÃ£o encontraram
  pendÃªncias. A suÃ­te integral fechou com **762 aprovados, 3 skips e 11
  subtestes aprovados em 27,52 s**; `git diff --check` passou. `git fetch
  origin --prune` e a comparaÃ§Ã£o `HEAD...origin/main` retornaram **0/0**:
  nÃ£o hÃ¡ commits remotos ausentes localmente nem commits locais Ã  frente.

Limites: os skips continuam limitados a Playwright Python opcional, OCR local
em portuguÃªs indisponÃ­vel e concorrÃªncia de locks exclusiva de PostgreSQL. A
regressÃ£o local nÃ£o homologa integraÃ§Ãµes externas.

## V-062 â€” SeguranÃ§a de anexos, DomÃ­nio multipart e acesso DTE tipados

Data: 21/09/2026. Ambiente: macOS local, banco e transportes sintÃ©ticos. NÃ£o
houve consulta DomÃ­nio, Serpro, caixa de e-mail, credencial, custo, deploy ou
alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- A leitura de `FieldFile` Ã© convertida ao contrato binÃ¡rio do scanner e da
  polÃ­tica; o multipart separa valores textuais de conteÃºdo binÃ¡rio; navegaÃ§Ã£o
  recebe a requisiÃ§Ã£o tipada; e a reserva DTE aceita explicitamente os dois
  livros locais de consumo.
- Ruff e MyPy passaram nos quatro mÃ³dulos. Os testes de seguranÃ§a/ingestÃ£o,
  polÃ­tica de arquivos, API DomÃ­nio local, navegaÃ§Ã£o e DTE fecharam com **40
  aprovados em 14,49 s**. `git diff --check` passou. MyPy global baixou para
  **160 erros em 7 arquivos**.

Limites: nÃ£o houve antimalware, mensagem, conexÃ£o DomÃ­nio ou requisiÃ§Ã£o Serpro
real. As homologaÃ§Ãµes das etapas 06, 08, 09 e 12 permanecem pendentes.

## V-061 â€” Plataforma administrativa com contratos tipados

Data: 21/09/2026. Ambiente: macOS local, banco de testes e webhooks sintÃ©ticos.
NÃ£o houve Asaas, cobranÃ§a, credencial, custo, deploy ou alteraÃ§Ã£o de condiÃ§Ãµes
comerciais.

- A tarefa de competÃªncia declara o mapa heterogÃªneo retornado; o snapshot de
  contrato confirma o plano antes de congelar mÃ³dulos; o webhook lida com
  `Content-Type` ausente; e a pÃ¡gina legal possui contrato HTTP explÃ­cito.
- Ruff e MyPy passaram nos quatro mÃ³dulos. As suÃ­tes de tarefas, pagamentos,
  configuraÃ§Ã£o e contratos fecharam com **69 aprovados em 8,04 s**. `git diff
  --check` passou. MyPy global baixou para **168 erros em 11 arquivos**.

Limites: eventos de pagamento e webhooks eram sintÃ©ticos. Nenhuma cobranÃ§a,
evento Asaas ou mudanÃ§a de preÃ§o/contrato foi criada; Q-08/Q-28 continuam
pendentes para a etapa 10.

## V-060 â€” Coletores e fila de Triagem com contratos tipados

Data: 21/09/2026. Ambiente: macOS local, transportes sintÃ©ticos e banco de
testes local. NÃ£o houve OAuth, caixa de e-mail, DNS, scanner, credencial,
custo, deploy ou alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- O cursor Graph materializa a data inicial e a continuidade validadas antes de
  persistir; a leitura IMAP declara o conteÃºdo binÃ¡rio e a fÃ¡brica de conexÃ£o;
  a fila declara sua queryset elegÃ­vel e nÃ£o mistura tipos de resultados de
  provedores. NÃ£o houve mudanÃ§a de protocolo ou de chamadas de rede.
- Ruff e MyPy passaram em Graph, IMAP e tarefas. Os testes de Graph, IMAP,
  retentativa, ingestÃ£o e fila fecharam com **22 aprovados em 14,40 s**.
  `git diff --check` passou. MyPy global baixou para **172 erros em 15 arquivos**.

Limites: todas as mensagens/conexÃµes eram sintÃ©ticas. OAuth, provedores,
antimalware e destinos reais continuam pendentes nas etapas 06 e 12.

## V-059 â€” RelatÃ³rios e sincronizaÃ§Ã£o bancÃ¡ria com contratos estÃ¡ticos

Data: 21/09/2026. Ambiente: macOS local, banco de testes local. NÃ£o houve
chamada a DomÃ­nio, Claude, provedores, credencial, custo, deploy ou alteraÃ§Ã£o
de configuraÃ§Ã£o operacional.

- A estrutura normalizada da sincronizaÃ§Ã£o bancÃ¡ria passou a declarar os tipos
  de cada campo antes das escritas idempotentes em `DominioBankEntry` e
  `AccountingEntry`. As bibliotecas de geraÃ§Ã£o XLSX/PDF, jÃ¡ dependÃªncias do
  projeto, receberam exceÃ§Ãµes locais e explÃ­citas para a falta de stubs MyPy.
- Ruff e MyPy passaram nos dois mÃ³dulos. Os **7 testes** de sincronizaÃ§Ã£o
  passaram em **13,26 s**. NÃ£o hÃ¡ teste dedicado de exportaÃ§Ã£o de relatÃ³rio no
  repositÃ³rio; isso Ã© um limite de cobertura, nÃ£o uma aprovaÃ§Ã£o adicional.
  `git diff --check` passou. MyPy global baixou para **185 erros em 18 arquivos**.

Limites: nÃ£o houve documento, lanÃ§amento bancÃ¡rio, planilha ou PDF de cliente
real. IntegraÃ§Ã£o DomÃ­nio, curadoria e homologaÃ§Ãµes da etapa 05/09 continuam
pendentes.

## V-058 â€” RegressÃ£o local integral apÃ³s os lotes de contratos

Data: 21/09/2026. Ambiente: macOS local. NÃ£o houve conexÃ£o externa,
credencial, custo, deploy ou alteraÃ§Ã£o operacional.

- `manage.py check` nÃ£o encontrou problemas e `makemigrations --check --dry-run`
  nÃ£o encontrou mudanÃ§as. A suÃ­te integral fechou com **762 aprovados, 3 skips
  e 11 subtestes aprovados em 27,46 s**; `git diff --check` passou.

Limites: os skips permanecem limitados a Playwright Python opcional, OCR local
em portuguÃªs indisponÃ­vel e concorrÃªncia de locks exclusiva de PostgreSQL. A
regressÃ£o local nÃ£o homologa serviÃ§os externos.

## V-057 â€” Gateway e comandos de IA com contratos tipados

Data: 21/09/2026. Ambiente: macOS local, comandos e transporte Claude
substituÃ­dos nos testes. NÃ£o houve chamada Anthropic, chave, dado de cliente,
custo, deploy ou alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- O payload do gateway foi declarado como mapa de objetos heterogÃªneos e os
  comandos de configuraÃ§Ã£o/verificaÃ§Ã£o ganharam assinaturas de parser/opÃ§Ãµes
  explÃ­citas. O comando que exige custo continua exigindo `--cost-approved`;
  a alteraÃ§Ã£o nÃ£o o executou.
- Ruff e MyPy passaram nos quatro mÃ³dulos. As suÃ­tes de comandos, escopo IA e
  acesso operacional fecharam com **32 aprovados em 13,42 s**. `git diff
  --check` passou. MyPy global baixou para **197 erros em 20 arquivos**.

Limites: a evidÃªncia nÃ£o valida egressÃ£o, modelo, custo, resposta Claude ou
treinamento. Q-08/Q-09/Q-11/Q-34 permanecem exigÃªncias da etapa 05.

## V-056 â€” ConfiguraÃ§Ã£o de plataforma com contratos locais completos

Data: 21/09/2026. Ambiente: macOS local, banco de testes e transportes
substituÃ­dos. NÃ£o houve Serpro, SMTP, Claude, Asaas, BrasilAPI, credencial, custo,
deploy ou alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- Os formulÃ¡rios de plataforma agora tipam seus limites dinÃ¢micos de Django,
  retornos de `clean`, persistÃªncia de `ModelForm` e usuÃ¡rio de auditoria. O
  manipulador de plano nÃ£o mistura manager e queryset com lock. Os mÃ³dulos de
  pagamento/notificaÃ§Ã£o e aprovaÃ§Ã£o de fallback tambÃ©m preservam valores
  verificados antes de persistir ou notificar.
- Ruff e MyPy passaram em `configuration.py`, `payments.py`, `notifications.py`
  e `views.py`. As suÃ­tes de configuraÃ§Ã£o, faturamento, pagamentos e tokens
  fecharam com **55 aprovados, 1 skip de concorrÃªncia PostgreSQL e 8,02 s**.
  `git diff --check` passou. MyPy global baixou para **205 erros em 24 arquivos**.

Limites: os testes usam dados/transportes locais. NÃ£o houve validaÃ§Ã£o SMTP,
chamada Claude/Serpro/Asaas nem alteraÃ§Ã£o de preÃ§o ou contrato comercial.

## V-055 â€” Coletor Gmail e ingestÃ£o com prÃ©-condiÃ§Ãµes explÃ­citas

Data: 21/09/2026. Ambiente: macOS local, mensagens e respostas Gmail sintÃ©ticas.
NÃ£o houve OAuth, caixa Google real, credencial, conexÃ£o externa, custo, deploy ou
alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- O cursor, checkpoint e leitura Gmail exigem explicitamente a data inicial da
  caixa antes de comparar ou persistir datas. A decodificaÃ§Ã£o base64 usa a
  exceÃ§Ã£o do mÃ³dulo padrÃ£o e o caminho do blob em quarentena Ã© normalizado para
  texto antes da limpeza apÃ³s falha.
- Ruff e MyPy passaram em `apps/triage/gmail_poll.py` e `apps/triage/ingest.py`.
  Testes de ingestÃ£o e retentativa fecharam com **14 aprovados em 7,16 s**;
  `git diff --check` passou. MyPy global baixou a **291 erros em 28 arquivos**.

Limites: nenhuma caixa Google foi autenticada ou consultada. OAuth, scanner e
destinos reais permanecem pendentes da etapa 06/12.

## V-054 â€” Cliente IMAP local com respostas tipadas

Data: 21/09/2026. Ambiente: macOS local, DNS e IMAP sintÃ©ticos. NÃ£o houve caixa
real, credencial de provedor, conexÃ£o externa, custo, deploy ou alteraÃ§Ã£o de
configuraÃ§Ã£o operacional.

- O socket TLS Ã© retornado com o tipo explÃ­cito; cada resposta IMAP recebe uma
  variÃ¡vel prÃ³pria, e a ausÃªncia de charset no `UID SEARCH` Ã© preservada com
  conversÃ£o de tipo sem mudar o argumento entregue ao protocolo.
- Ruff e MyPy passaram em `apps/triage/imap.py`. Testes de conexÃ£o e
  retentativa passaram com **12 aprovados em 14,07 s**; `git diff --check`
  passou. MyPy global baixou para **296 erros em 30 arquivos**.

Limites: nenhuma caixa IMAP foi conectada, lida ou alterada. OAuth, provedor,
scanner e destino real seguem pendentes da etapa 06/12.

## V-053 â€” Livros de tokens e faturamento tipados sem mudanÃ§a comercial

Data: 21/09/2026. Ambiente: macOS local, banco de testes e sem transporte de
pagamentos. NÃ£o houve Asaas, cobranÃ§a, preÃ§o novo, credencial, custo, deploy ou
alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- A competÃªncia de fechamento passa a usar variÃ¡vel distinta para o medidor
  legado, preservando a separaÃ§Ã£o de `UsageMeter` e `TokenMeter`. O medidor de
  tokens materializa franquia/preÃ§o nÃ£o nulos antes de criar o livro, e a
  ativaÃ§Ã£o recebe o usuÃ¡rio autenticado esperado pelo modelo.
- Ruff e MyPy passaram em `apps/platform/billing.py` e
  `apps/platform/token_billing.py`. A suÃ­te de faturamento, pagamentos e tokens
  fechou com **22 aprovados, 1 skip de concorrÃªncia PostgreSQL e 7,75 s**.
  `git diff --check` passou. MyPy global baixou a **300 erros em 31 arquivos**.

Limites: nÃ£o houve fatura, cobranÃ§a ou pagamento real. A orquestraÃ§Ã£o Asaas e
homologaÃ§Ã£o de meios de pagamento continuam abertas na etapa 10.

## V-052 â€” Transporte de e-mail local com contrato tipado

Data: 21/09/2026. Ambiente: macOS local, banco de testes e backend SMTP
substituÃ­do. NÃ£o houve conexÃ£o SMTP, DNS, Brevo, credencial, custo, deploy ou
alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- O backend de e-mail passou a declarar a configuraÃ§Ã£o de plataforma, backend
  SMTP e sequÃªncia de mensagens com as assinaturas esperadas pelo Django. O
  carregamento do modelo permanece tardio para nÃ£o afetar a inicializaÃ§Ã£o do
  registro de aplicaÃ§Ãµes.
- Ruff e MyPy passaram em `apps/common/database_email.py`. A suÃ­te de
  configuraÃ§Ã£o fechou com **33 aprovados em 7,66 s**; `git diff --check`
  passou. MyPy global baixou para **311 erros em 33 arquivos**.

Limites: isto confirma somente o transporte local substituÃ­do. A configuraÃ§Ã£o e
entrega SMTP/DNS/Brevo reais continuam para a etapa 12 por D-77/D-78.

## V-051 â€” PARCSN e operaÃ§Ãµes agendadas com contratos de tipo explÃ­citos

Data: 21/09/2026. Ambiente: macOS local, banco de testes e respostas sintÃ©ticas.
NÃ£o houve chamada Serpro, credencial, certificado, documento real, custo, deploy
ou alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- O parser PARCSN agora valida que o expoente decimal Ã© numÃ©rico antes de
  comparar casas decimais e retorna inteiro explÃ­cito para campos positivos. O
  registrador de tarefas agendadas reconhece as duas formas previstas de
  resultado e expÃµe a assinatura completa do decorador.
- Ruff e MyPy passaram em `apps/integra/parcelamento.py` e
  `apps/platform/operations.py`. `test_integra_parcelamento.py`,
  `test_parcelamento_operations.py` e `test_platform_tasks.py` fecharam com
  **20 aprovados em 13,70 s**; `git diff --check` passou.
- MyPy global caiu para **316 erros em 34 arquivos**. A reduÃ§Ã£o nÃ£o equivale Ã 
  homologaÃ§Ã£o dos serviÃ§os ou ao fim da dÃ­vida tÃ©cnica restante.

Limites: PARCSN continua limitado ao transporte simulado; credenciais, custo,
representaÃ§Ã£o e prova Serpro permanecem dependÃªncias da etapa 08.

## V-050 â€” ImportaÃ§Ã£o local: limites de entrada explÃ­citos

Data: 21/09/2026. Ambiente: macOS local e arquivos sintÃ©ticos. NÃ£o houve backup
DomÃ­nio real, ERP, arquivo de cliente, credencial, custo, deploy ou alteraÃ§Ã£o de
configuraÃ§Ã£o operacional.

- A criaÃ§Ã£o de prÃ©via de importaÃ§Ã£o agora exige nome de arquivo antes de
  persistir metadados, reutiliza esse nome validado para salvar/identificar o
  conteÃºdo e tipa o mapa de capacidades por tipo de importaÃ§Ã£o. A leitura de
  upload Ã© declarada como bytes e o aviso de `defusedxml` fica restrito ao
  import sem stubs.
- Ruff passou em `apps/hub/imports.py`. A checagem direta reporta apenas erros
  de mÃ³dulos transitivamente importados; a tentativa de isolÃ¡-los com
  `--follow-imports=skip` atingiu um erro interno do MyPy 1.19.1 em
  `django-stubs`, portanto nÃ£o Ã© contada como aprovaÃ§Ã£o. A auditoria global
  ainda concluiu e baixou para **328 erros em 37 arquivos**.
- `tests/test_hub.py`, `test_hub_api.py` e `test_hub_workspace_views_django.py`
  fecharam com **57 aprovados em 14,41 s**; `git diff --check` passou.

Limites: nÃ£o houve teste de backup `.dom` real, layout autorizado, leitura de
ERP, fonte externa ou homologaÃ§Ã£o de importaÃ§Ã£o. O erro interno do MyPy exige
atualizaÃ§Ã£o/diagnÃ³stico separado do verificador, nÃ£o supressÃ£o global.

## V-049 â€” ServiÃ§o de conciliaÃ§Ã£o com contratos de tipo explÃ­citos

Data: 21/09/2026. Ambiente: macOS local, banco de testes, arquivos sintÃ©ticos e
OCR local indisponÃ­vel. NÃ£o houve acesso a ERP, fonte Radar, arquivo de cliente,
credencial, custo, deploy ou alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- O serviÃ§o agora declara o checkpoint heterogÃªneo de uma execuÃ§Ã£o, o contrato
  de dialeto CSV, bytes do armazenamento, chave TSV de OCR e relaÃ§Ãµes opcionais
  de conta/movimento. A regra de faixa somente tenta converter limites textuais
  ou numÃ©ricos vÃ¡lidos e retorna nÃ£o correspondÃªncia para forma invÃ¡lida,
  mantendo a regra restritiva.
- `openpyxl` e `pypdfium2` continuam dependÃªncias de runtime sem stubs; as
  exceÃ§Ãµes de tipo sÃ£o locais aos imports e nÃ£o alteram o uso das bibliotecas.
  Ruff e MyPy passaram em `apps/hub/reconciliation_service.py`.
- A suÃ­te de conciliaÃ§Ã£o fechou com **35 aprovados, 1 skip de OCR portuguÃªs e
  7,91 s**. `manage.py check`, `makemigrations --check --dry-run` e `git diff
  --check` passaram. MyPy global baixou para **334 erros em 38 arquivos**.

Limites: layouts, OCR, volumes, fontes Radar e exportaÃ§Ãµes para ERPs seguem
sem homologaÃ§Ã£o externa. A contagem global Ã© diagnÃ³stico, nÃ£o aceite global.

## V-048 â€” FormulÃ¡rios de contrataÃ§Ã£o tipados e retestados

Data: 21/09/2026. Ambiente: macOS local, banco de testes e dublÃªs de serviÃ§os.
NÃ£o houve consulta CNPJ, Asaas, cobranÃ§a, credencial, custo, deploy ou alteraÃ§Ã£o
de configuraÃ§Ã£o operacional.

- `LeadForm` tipa o objeto salvo pelo `ModelForm`; os formulÃ¡rios de plano e
  proposta de tokens tratam o retorno nulo previsto de `clean`; a remoÃ§Ã£o de
  mÃ³dulo IA usa variÃ¡vel prÃ³pria, sem ambiguidade com a taxa criada no ramo
  oposto. O comportamento de cobranÃ§a e a regra comercial permanecem iguais.
- Ruff e MyPy passaram em `apps/platform/forms.py`. A suÃ­te de CNPJ, cobranÃ§a,
  pagamentos e tokens fechou com **26 aprovados, 1 skip de concorrÃªncia restrita
  a PostgreSQL e 7,43 s**. `git diff --check` passou.
- A auditoria MyPy global, executada de `src/`, baixou para **348 erros em 39
  arquivos**. O nÃºmero Ã© dÃ­vida tÃ©cnica remanescente, nÃ£o aprovaÃ§Ã£o global.

Limites: esta rodada nÃ£o criou cobranÃ§a, nÃ£o acessou Asaas/BrasilAPI e nÃ£o
homologou pagamentos ou concorrÃªncia em PostgreSQL.

## V-047 â€” FormulÃ¡rios do Hub e cache CNPJ tipados sem regressÃ£o

Data: 21/09/2026. Ambiente: macOS local, banco de testes e arquivos sintÃ©ticos.
NÃ£o houve consulta externa ao cadastro CNPJ, ERP, arquivo de cliente,
credencial, custo, deploy ou alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- Foram corrigidas as interfaces de tipo dos formulÃ¡rios de acesso, importaÃ§Ã£o
  e conciliaÃ§Ã£o: escolhas dinÃ¢micas do Django, campos de modelo, widgets de
  conta financeira, validaÃ§Ãµes `clean` e o campo mÃºltiplo de arquivos. As
  conversÃµes genÃ©ricas foram mantidas como referÃªncias adiadas, pois as classes
  Django nÃ£o sÃ£o subscritÃ¡veis em runtime; a suÃ­te de integraÃ§Ã£o confirmou que
  a pÃ¡gina de conciliaÃ§Ã£o continua sendo construÃ­da normalmente.
- O cache de consulta de CNPJ agora sÃ³ reutiliza um dicionÃ¡rio de textos; valor
  invÃ¡lido no cache Ã© tratado como ausente, evitando confiar em um objeto de
  tipo inesperado. NÃ£o houve chamada Ã  BrasilAPI nesta validaÃ§Ã£o.
- Ruff e MyPy passaram em `apps/hub/forms.py` e `apps/common/cnpj.py`. A suÃ­te
  de conciliaÃ§Ã£o fechou com **35 aprovados, 1 skip de OCR em portuguÃªs e 8,22
  s**. `manage.py check`, `makemigrations --check --dry-run` e `git diff
  --check` passaram.
- A auditoria MyPy global, a partir de `src/`, baixou de 399 para **356 erros
  em 40 arquivos**. Isso Ã© progresso de dÃ­vida tÃ©cnica, nÃ£o aprovaÃ§Ã£o global.

Limites: nÃ£o foram homologados OCR, layouts reais, ERP, Radar, exportaÃ§Ã£o ou
qualquer fonte externa. As 356 ocorrÃªncias restantes seguem visÃ­veis para
revisÃ£o modular.

## V-046 â€” PrÃ©-condiÃ§Ãµes de serviÃ§o da Triagem explicitadas

Data: 21/09/2026. Ambiente: macOS local, banco de testes e anexos sintÃ©ticos.
NÃ£o houve caixa real, arquivo de cliente, credencial, provedor, custo, deploy ou
alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- `apps.triage.services` agora materializa as prÃ©-condiÃ§Ãµes que o fluxo jÃ¡
  aplicava: empresa e tipo precisam existir antes da aprovaÃ§Ã£o; upload precisa
  ter nome e tamanho vÃ¡lido; caminho de destino precisa existir antes de abrir
  a cÃ³pia; os retornos de armazenamento sÃ£o streams binÃ¡rios. Isto nÃ£o altera
  os estados, a polÃ­tica de seguranÃ§a, nem cria uma integraÃ§Ã£o externa.
- O lote removeu **9 ocorrÃªncias MyPy**. A nova auditoria global, executada a
  partir de `src/`, encontrou **399 erros em 42 arquivos** (antes, 408 em 43);
  o valor continua sendo diagnÃ³stico de dÃ­vida tÃ©cnica, nÃ£o aprovaÃ§Ã£o global.
- Ruff e MyPy passaram em `apps/triage/services.py`. A suÃ­te de domÃ­nio,
  ingestÃ£o e agente Windows fechou com **35 aprovados em 7,47 s**. `manage.py
  check`, `makemigrations --check --dry-run` e `git diff --check` passaram.

Limites: esta evidÃªncia nÃ£o homologa e-mail, scanner, agente instalado ou
escrita Windows. As 399 ocorrÃªncias restantes permanecem para lotes revisÃ¡veis
e nÃ£o sÃ£o suprimidas por configuraÃ§Ã£o global.

## V-045 â€” FormulÃ¡rios da Triagem tipados sem mudanÃ§a funcional

Data: 21/09/2026. Ambiente: macOS local, banco de testes e transporte de e-mail
sintÃ©tico. NÃ£o houve caixa real, arquivo de cliente, credencial, provedor,
custo, deploy ou alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- A interface dos seis formulÃ¡rios de Triagem passou a aceitar os argumentos
  dinÃ¢micos do Django com `Any` restrito Ã s fronteiras do framework. Os dois
  campos de escolha foram convertidos explicitamente para seus respectivos
  tipos de modelo e os mÃ©todos `clean` preservam um dicionÃ¡rio nÃ£o nulo. A
  validaÃ§Ã£o de data agora tambÃ©m confirma o tipo antes da comparaÃ§Ã£o.
- Isto elimina **127 ocorrÃªncias MyPy** sistemÃ¡ticas de `forms.py`, sem trocar
  campo, rÃ³tulo, regra de validaÃ§Ã£o, fluxo de tela, persistÃªncia ou migraÃ§Ã£o.
  Nova auditoria `uv run mypy .` resultou em **408 erros em 43 arquivos**;
  portanto, ainda Ã© diagnÃ³stico de dÃ­vida tÃ©cnica, nÃ£o aprovaÃ§Ã£o global.
- Ruff e MyPy passaram nos trÃªs mÃ³dulos de Triagem alterados. `manage.py
  check` e `makemigrations --check --dry-run` passaram. A suÃ­te consolidada de
  polÃ­tica de arquivo, IMAP, domÃ­nio e ingestÃ£o fechou com **51 aprovados em
  14,77 s**. `git diff --check` passou.

Limites: a evidÃªncia nÃ£o homologa OAuth, IMAP, antimalware, arquivamento ou
qualquer destino Windows. Os 408 erros restantes exigem revisÃ£o em lotes; nÃ£o
devem ser ocultados por uma regra global de MyPy.

## V-044 â€” DiagnÃ³stico global e primeiro lote de tipagem da Triagem

Data: 21/09/2026. Ambiente: macOS local, sem conexÃ£o externa, dado de cliente,
credencial, custo, deploy ou alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- `uv run mypy .`, executado a partir de `src/`, encontrou **535 erros em 46
  arquivos**. A execuÃ§Ã£o Ã© um diagnÃ³stico da dÃ­vida tÃ©cnica existente, nÃ£o uma
  aprovaÃ§Ã£o global; inclui anotaÃ§Ãµes incompatÃ­veis em formulÃ¡rios/views e duas
  dependÃªncias sem stubs (`defusedxml` e `reportlab`).
- Como primeiro lote sem alterar comportamento, `presentation.py` declara o
  mapa de Ã¢ncoras de provedores com o tipo de chave correto e `file_policy.py`
  documenta a ausÃªncia de stubs de `defusedxml`. Assim, MyPy nÃ£o confunde o
  enum de provedor com a chave de texto do dicionÃ¡rio e a anÃ¡lise preserva a
  validaÃ§Ã£o XML existente em tempo de execuÃ§Ã£o.
- `uv run ruff check apps/triage/presentation.py apps/triage/file_policy.py` e
  `uv run mypy apps/triage/presentation.py apps/triage/file_policy.py`
  passaram. `uv run pytest ../tests/test_triage_file_policy.py
  ../tests/test_triage_domain.py ../tests/test_triage_email_ingest_django.py
  -q` fechou com **44 aprovados em 7,12 s**. `git diff --check` passou.

Limites: ainda hÃ¡ 533 ou mais ocorrÃªncias globais a revisar, pois esta rodada
somente removeu as duas ocorrÃªncias dos mÃ³dulos citados. NÃ£o houve migraÃ§Ã£o,
mudanÃ§a de regra de negÃ³cio, chamada de provedor ou homologaÃ§Ã£o de caixa de
e-mail/antimalware.

## V-043 â€” Qualidade de tipos da base local

Data: 21/09/2026. Ambiente: macOS local, sem conexÃ£o externa, dado de cliente,
credencial, custo, deploy ou alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- A execuÃ§Ã£o MyPy de V-042 encontrou 21 erros em quatro mÃ³dulos. Foram
  corrigidas somente anotaÃ§Ãµes e assinaturas compatÃ­veis com Django: armazenamento
  privado da Triagem, guarda nula do aplicativo OAuth, protocolo de caminho de
  arquivo de conciliaÃ§Ã£o e assinaturas de `save`/`delete` dos livros de tokens.
  NÃ£o houve alteraÃ§Ã£o de regra comercial, persistÃªncia, migraÃ§Ã£o ou chamada de
  provedor.
- A partir de `src/`, `uv run mypy apps/triage/storage.py
  apps/triage/models.py apps/hub/models.py apps/platform/models.py
  apps/intelligence/training.py
  apps/intelligence/management/commands/export_training_manifest.py` retornou
  **Success: no issues found in 6 source files**. Ruff dos mesmos arquivos
  passou.
- `uv run python manage.py check`, `makemigrations --check --dry-run` e
  `git diff --check` passaram. A suÃ­te focada de Triagem, conciliaÃ§Ã£o, cobranÃ§a
  e IA fechou com **125 aprovados, 1 ignorado e 3 subtestes aprovados em
  14,35 s**; o skip Ã© OCR portuguÃªs indisponÃ­vel.

Limites: esta execuÃ§Ã£o resolve os erros MyPy observados nesses mÃ³dulos, mas nÃ£o
equivale a uma auditoria de tipos de todo o projeto, homologaÃ§Ã£o externa ou
liberaÃ§Ã£o comercial. A suÃ­te integral posterior foi iniciada, mas a captura de
terminal nÃ£o reteve seu resumo apÃ³s exceder a janela interativa; ela nÃ£o Ã©
contabilizada como aprovaÃ§Ã£o nesta evidÃªncia. NÃ£o havia processo Pytest ativo e
o cache `lastfailed` estava vazio apÃ³s o tÃ©rmino. As validaÃ§Ãµes focadas acima
sÃ£o a evidÃªncia desta mudanÃ§a.

## V-042 â€” Etapa 05: gate local de privacidade antes do manifesto QLoRA

Data: 21/09/2026. Ambiente: macOS local, banco de testes e artefatos
temporÃ¡rios. NÃ£o houve dado de cliente, chamada Claude, egressÃ£o, credencial,
download de modelo, treinamento, GPU, custo, deploy ou publicaÃ§Ã£o.

- Por D-94, `training_manifest` e `evaluation_manifest` agora recusam, antes de
  retornar qualquer item, exemplo validado que contenha CPF, CNPJ ou e-mail em
  pergunta, resposta ou referÃªncias. O padrÃ£o Ã© o mesmo que o runner QLoRA jÃ¡
  recusava posteriormente; o controle agora impede que o artefato seja criado.
- A recusa nÃ£o edita nem mascara o exemplo original. A anonimizaÃ§Ã£o precisa ser
  uma revisÃ£o humana no registro de origem, para nÃ£o alterar silenciosamente
  uma evidÃªncia contÃ¡bil. O comando `export_training_manifest` converte a
  recusa em erro controlado e nÃ£o cria o arquivo de saÃ­da. Por D-95, ele tambÃ©m
  usa criaÃ§Ã£o exclusiva e recusa substituir um JSONL jÃ¡ existente.
- `uv run ruff check src/apps/intelligence/training.py
  src/apps/intelligence/management/commands/export_training_manifest.py
  tests/test_intelligence_training_django.py
  tests/test_intelligence_commands_django.py` passou. `manage.py check` e
  `makemigrations --check --dry-run` passaram. A suÃ­te focada de treinamento,
  comandos e runner fechou com **39 aprovados e 3 subtestes aprovados em
  13,03 s**.
- RevalidaÃ§Ã£o integral: `uv run pytest -q` fechou com **762 aprovados, 3
  ignorados e 11 subtestes aprovados em 27,90 s**. Os skips sÃ£o Playwright
  Python opcional, OCR portuguÃªs indisponÃ­vel e concorrÃªncia de locks coberta
  na evidÃªncia PostgreSQL histÃ³rica.

A checagem MyPy nÃ£o constitui evidÃªncia verde: a partir de `src/`, ela alcanÃ§ou
os arquivos alterados, mas terminou com 21 erros preexistentes em
`apps/triage/storage.py`, `apps/triage/models.py`, `apps/hub/models.py` e
`apps/platform/models.py`; eles nÃ£o foram alterados nesta entrega e permanecem
como dÃ­vida da base tÃ©cnica.

Limites: os gates nÃ£o constituem corpus revisado, anonimizaÃ§Ã£o de material real,
curadoria, autorizaÃ§Ã£o de egressÃ£o, treinamento ou publicaÃ§Ã£o de adaptador.
Q-08, Q-09, Q-11 e Q-34 continuam necessÃ¡rios; a etapa 05 permanece em
andamento.

## V-041 â€” AnÃ¡lise integral, continuidade segura da etapa 04 e sincronizaÃ§Ã£o Git

Data: 21/09/2026. Ambiente: macOS local, dependÃªncias travadas pelo projeto e
checkout inicialmente limpo. A anÃ¡lise nÃ£o usou credencial, dado de cliente,
conexÃ£o Siescon, arquivo de ERP, chamada externa de provedor, custo, deploy ou
alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- Foram relidos os registros canÃ´nicos, o checklist da etapa 04, a matriz de
  capacidades, o inventÃ¡rio e a anÃ¡lise anterior. O objetivo confirmado Ã© um
  SaaS multiempresa da Mewstack para escritÃ³rios contÃ¡beis, com agente Windows,
  operaÃ§Ã£o auditÃ¡vel e evidÃªncia recuperÃ¡vel; cÃ³digo ou teste local nÃ£o Ã©
  homologaÃ§Ã£o nem liberaÃ§Ã£o de venda.
- A leitura do cÃ³digo confirma o limite de D-54/D-88: `AccountingExport`
  modela `siescon`, mas `ACCOUNTING_EXPORT_ADAPTERS` registra apenas DomÃ­nio.
  `get_accounting_export_adapter("siescon")` recusa a solicitaÃ§Ã£o antes de
  consultar lanÃ§amentos ou gerar conteÃºdo. NÃ£o hÃ¡ adaptador, SQL, endpoint,
  credencial ou layout Siescon inventado nesta execuÃ§Ã£o.
- `uv run ruff check .`, `uv run python manage.py check` e
  `uv run python manage.py makemigrations --check --dry-run` passaram.
  `uv run pytest tests/test_reconciliation_module.py -q` fechou com **35
  aprovados e 1 ignorado em 7,67 s**; o skip Ã© OCR local em portuguÃªs
  indisponÃ­vel. `uv run pytest -q` fechou com **759 aprovados, 3 ignorados e
  8 subtestes aprovados em 27,82 s**. Os demais skips sÃ£o Playwright Python
  opcional e concorrÃªncia de locks coberta na evidÃªncia PostgreSQL histÃ³rica.
- `git fetch origin --prune` concluiu e `git rev-list --left-right --count
  HEAD...origin/main` retornou **0\t0**. NÃ£o havia commit remoto ausente,
  commit local nÃ£o enviado ou alteraÃ§Ã£o no diretÃ³rio de trabalho antes desta
  documentaÃ§Ã£o.

Limites: a revalidaÃ§Ã£o nÃ£o torna Siescon conectado, nÃ£o substitui o contrato
tÃ©cnico de Q-33 e nÃ£o avanÃ§a o aceite de importaÃ§Ã£o conferida exigido por D-73.
A etapa 04 permanece em andamento. Para implementar com seguranÃ§a, o tÃ©cnico
Siescon deve disponibilizar por canal seguro versÃ£o, banco/driver e acesso de
leitura; schema/campos permitidos; identificador de empresa e cursor; ambiente
de homologaÃ§Ã£o/revogaÃ§Ã£o; e layout versionado com amostra sintÃ©tica de
exportaÃ§Ã£o/importaÃ§Ã£o. O prÃ³ximo passo Ã© revisar esse material e sÃ³ entÃ£o
registrar um adaptador versionado, mantendo a escrita direta proibida.

## V-040 â€” Etapa 10: contrato local do cliente Asaas

Data: 20/09/2026. Ambiente: macOS local, chave de exemplo injetada somente
nos testes e transporte substituÃ­do por dublÃªs em memÃ³ria. NÃ£o houve leitura de
configuraÃ§Ã£o, segredo real, conexÃ£o de rede, conta/sandbox Asaas, cliente,
cobranÃ§a, dado de cliente, custo ou deploy.

- O cliente local seleciona de modo explÃ­cito `sandbox` ou `production`, envia
  `access_token`, `Content-Type` e `User-Agent`, e permite transportar a
  requisiÃ§Ã£o apenas por injeÃ§Ã£o. Ele nÃ£o procura chave em `settings`, arquivos
  locais ou variÃ¡veis de ambiente.
- Antes de criar cliente, consulta `externalReference`; a criaÃ§Ã£o de cliente e
  de cobranÃ§a avulsa nÃ£o tem retentativa automÃ¡tica apÃ³s falha ou resultado
  incerto. A cobranÃ§a aceita PIX, boleto ou cartÃ£o sem receber dados de cartÃ£o;
  o retorno Ã© validado antes de ser exposto ao chamador.
- `uv run pytest tests/test_asaas_client.py tests/test_platform_billing.py tests/test_platform_payments.py tests/test_token_billing.py tests/test_cica_contract_mfa.py tests/test_cica_operation_access.py -q`: **49 aprovados e 1 ignorado em 13,54 s**. O skip cobre concorrÃªncia de locks exclusiva do PostgreSQL.
- Ruff dos mÃ³dulos/testes de Asaas e cobranÃ§a, `uv run python manage.py check`,
  `uv run python manage.py makemigrations --check --dry-run` e `git diff --check`
  passaram.
- RevalidaÃ§Ã£o integral: `uv run pytest -q` fechou com **759 aprovados, 3
  ignorados e 8 subtestes aprovados em 28,99 s**; `uv run ruff check .`, Django,
  dry-run de migraÃ§Ãµes e diff tambÃ©m passaram. Os skips permanecem: Playwright
  Python opcional, OCR portuguÃªs indisponÃ­vel e concorrÃªncia de locks coberta
  na evidÃªncia PostgreSQL histÃ³rica.

O contrato foi alinhado Ã  [autenticaÃ§Ã£o](https://docs.asaas.com/docs/authentication),
ao [cliente](https://docs.asaas.com/reference/create-new-customer) e Ã 
[cobranÃ§a](https://docs.asaas.com/reference/create-new-payment) documentados
pela Asaas. Limites: nÃ£o hÃ¡ orquestraÃ§Ã£o entre contrato comercial, cliente,
`PaymentAttempt` e ambiente autorizado; tambÃ©m nÃ£o hÃ¡ teste de Pix, boleto,
cartÃ£o, atraso, estorno, webhook real ou evento fora de ordem. Q-08/Q-28 e a
etapa 12 de D-87 continuam obrigatÃ³rios. A etapa 10 permanece em andamento.

## V-039 â€” Etapa 11: jornadas e interfaces locais, inspeÃ§Ã£o parcial

Data: 19/09/2026. Ambiente: servidor de QA descartÃ¡vel em `127.0.0.1:8011`,
SQLite e mÃ­dia sob `.tmp/ui-review`, massa sintÃ©tica e sockets externos
bloqueados pelo prÃ³prio servidor de QA. A inspeÃ§Ã£o iniciou e fechou uma sessÃ£o
de demonstraÃ§Ã£o fictÃ­cia; nÃ£o usou conta, dado ou serviÃ§o externo.

- NavegaÃ§Ã£o interativa em navegador local percorreu VisÃ£o geral, Empresas,
  NFS-e, Guias, Central Integra/DTE/Parcelamentos, ConciliaÃ§Ã£o, Radar, Triagem,
  Caixas, ConfiguraÃ§Ã£o, Equipe e Copiloto. Nos 14 caminhos, em desktop e em
  390 Ã— 844, a verificaÃ§Ã£o DOM encontrou um Ãºnico `h1`, nenhum campo visÃ­vel
  sem rÃ³tulo e nenhum overflow horizontal.
- A inspeÃ§Ã£o visual do fluxo fictÃ­cio de Triagem confirmou no celular e desktop
  a fila, bloqueio explÃ­cito de item em quarentena, revisÃ£o, transiÃ§Ã£o para
  â€œPronto para arquivarâ€, arquivamento fictÃ­cio e link privado de download. O
  progresso permaneceu na sessÃ£o e a tela declarou que nenhuma pasta real seria
  alterada. O console do navegador nÃ£o registrou erros.
- `uv run pytest tests/test_hub_workspace_views_django.py tests/test_seed_demo_django.py tests/test_cica_auth_flow.py -q`: **77 aprovados e 1 ignorado em 21,08 s**. O skip Ã© o Playwright Python opcional; a inspeÃ§Ã£o interativa acima nÃ£o depende desse pacote.
- Ruff dos mÃ³dulos/testes envolvidos, `uv run python manage.py check`,
  `uv run python manage.py makemigrations --check --dry-run` e `git diff --check`
  passaram.

Limites: a inspeÃ§Ã£o nÃ£o conclui o site comercial, cadastro, central de
aprendizado ou console Mewstack; tambÃ©m nÃ£o cobre todos os perfis, estados de
carga/erro/vazio, navegaÃ§Ã£o exclusivamente por teclado, contraste por elemento
ou tarefas reais autorizadas. Ã‰ uma auditoria local parcial, nÃ£o homologaÃ§Ã£o e
nem prova de que a oferta comercial corresponde a integraÃ§Ãµes ainda pendentes.
A etapa 11 permanece em andamento.

## V-038 â€” Etapa 06: Triagem de Arquivos local

Data: 19/09/2026. Ambiente: macOS local, banco de testes, armazenamento
temporÃ¡rio e provedores/antimalware/agente substituÃ­dos por dublÃªs de teste. Sem
OAuth, caixa de e-mail, ClamAV, agente Windows, arquivo de cliente, escrita em
pasta real, chamada externa, custo ou deploy.

- A entrada local mantÃ©m o binÃ¡rio em quarentena privada, normaliza nome,
  preserva procedÃªncia por mensagem/parte e Ã© idempotente apenas para a mesma
  entrega. Pollers simulados exercitam cursor, corte e leitura sem marcar a
  mensagem como lida; anexo grande ou caixa pausada nÃ£o persiste binÃ¡rio.
- Arquivo nÃ£o verificado nÃ£o pode ser revisado, baixado ou arquivado. Um scanner
  limpo ainda exige formato permitido; detecÃ§Ã£o rejeita e indisponibilidade do
  scanner conserva a quarentena. A cÃ³pia da biblioteca privada Ã© relida e tem
  SHA-256 conferido antes do estado final, que volta a falhar se adulterada.
- O contrato local do agente Windows vincula escritÃ³rio, raiz, caminho relativo,
  tamanho e hash; sÃ³ confirma o arquivamento apÃ³s a prova correspondente. Outra
  organizaÃ§Ã£o recebe 404, falha fica recuperÃ¡vel e nome/caminho invÃ¡lido Ã©
  recusado. Isso Ã© teste de protocolo, nÃ£o escrita no Windows.
- `uv run pytest tests/test_triage_domain.py tests/test_triage_oauth_django.py tests/test_triage_email_ingest_django.py tests/test_triage_gmail_poll_django.py tests/test_triage_graph_poll_django.py tests/test_triage_poll_retry_django.py tests/test_triage_windows_paths.py tests/test_triage_windows_agent.py -q`: **72 aprovados e 6 subtestes aprovados em 14,40 s**.
- `uv run pytest tests/test_hub_workspace_views_django.py tests/test_seed_demo_django.py -k 'triage' -q`: **6 aprovados, 64 desmarcados em 14,04 s**. Cobre escopo por empresa, fila, bloqueio de nÃ£o verificado, cÃ³pia privada e demo isolada por sessÃ£o.
- Ruff dos mÃ³dulos e testes envolvidos, `uv run python manage.py check`,
  `uv run python manage.py makemigrations --check --dry-run` e `git diff --check`
  passaram.

Limites: nÃ£o hÃ¡ consentimento/revogaÃ§Ã£o, redirect ou leitura real em Microsoft,
Google/Gmail/IMAP; nÃ£o hÃ¡ ClamAV instalado/atualizado, catÃ¡logo/nomenclatura,
retenÃ§Ã£o, Ã¡rvore de destino, regra de checklist ou raiz/conta Windows aprovadas.
Q-12 a Q-25 e Q-31 continuam abertas, e D-73 exige amostra e recuperaÃ§Ã£o no
destino autorizado. A etapa 06 permanece em andamento.

## V-037 â€” Etapa 09: ConciliaÃ§Ã£o e Radar locais

Data: 19/09/2026. Ambiente: macOS local e banco de testes; entradas e respostas
sintÃ©ticas controladas pelos testes. NÃ£o houve arquivo bancÃ¡rio, lanÃ§amento,
exportaÃ§Ã£o, acesso a DomÃ­nio/Siescon, coleta HTTP real, dado de cliente, custo,
deploy ou configuraÃ§Ã£o operacional.

- A conciliaÃ§Ã£o local aceita somente OFX, CSV, XLSX ou PDF com limites de
  tamanho/linhas/pÃ¡ginas, identifica o tipo pelo conteÃºdo, guarda fonte privada
  com hash e trata reenvio idempotente. HÃ¡ mapeamento revisÃ¡vel, conta financeira,
  regras, movimentos normalizados, partidas equilibradas, conciliaÃ§Ã£o parcial ou
  desfeita e evidÃªncia obrigatÃ³ria para a confirmaÃ§Ã£o. Ambiguidade permanece em
  revisÃ£o; nÃ£o hÃ¡ confirmaÃ§Ã£o automÃ¡tica apenas por data e valor.
- O processamento persiste execuÃ§Ã£o, checkpoint, erros e retomada de trabalho
  pendente/expirado. A exportaÃ§Ã£o local mantÃ©m hash, reexportaÃ§Ã£o ligada Ã  origem
  e estado explÃ­cito, mas nÃ£o foi importada em qualquer ERP nesta execuÃ§Ã£o.
- O Radar limita a coleta a trÃªs pÃ¡ginas oficiais fixas, conserva URL/origem e
  relevÃ¢ncia, Ã© idempotente e registra falha por fonte sem expor erro interno na
  interface. As coletas foram simuladas pelos testes; a disponibilidade das
  pÃ¡ginas oficiais nÃ£o foi exercitada.
- `uv run pytest tests/test_reconciliation.py tests/test_reconciliation_module.py tests/test_reform_radar.py -q`: **46 aprovados e 1 ignorado em 7,84 s**. O skip Ã© o caso de OCR local em portuguÃªs, pois Tesseract/modelo `por` nÃ£o estÃ¡ disponÃ­vel nesta estaÃ§Ã£o.
- `uv run pytest tests/test_hub_workspace_views_django.py tests/test_seed_demo_django.py -k 'reform_radar or reconciliation_confirmation' -q`: **4 aprovados, 66 desmarcados em 14,29 s**. Cobre filtro/estado seguro de falha do Radar e confirmaÃ§Ã£o de conciliaÃ§Ã£o fictÃ­cia isolada por sessÃ£o.
- Ruff dos mÃ³dulos e testes envolvidos, `uv run python manage.py check`,
  `uv run python manage.py makemigrations --check --dry-run` e `git diff --check`
  passaram.

Limites: nÃ£o hÃ¡ layout bancÃ¡rio/contÃ¡bil aprovado, OCR portuguÃªs disponÃ­vel,
amostra independente de 200 itens, volume em PostgreSQL, fonte Radar real
exercitada, importaÃ§Ã£o conferida no DomÃ­nio ou adaptador/layout Siescon. D-54
proÃ­be escrita direta no Siescon; D-73 exige a conferÃªncia no destino antes de
aprovar exportaÃ§Ã£o. A etapa 09 permanece em andamento.

## V-036 â€” Matriz auditÃ¡vel de evidÃªncias do plano

Data: 19/09/2026. Ambiente: checkout local e documentaÃ§Ã£o canÃ´nica. Sem execuÃ§Ã£o de integraÃ§Ã£o externa, dado de cliente, segredo, custo, deploy ou alteraÃ§Ã£o de configuraÃ§Ã£o operacional.

- A matriz `docs/planejamento/matriz-evidencias-2026-09-19.md` confronta as 14 etapas, seus checklists, as evidÃªncias V-001 a V-035, o inventÃ¡rio e as decisÃµes/dÃºvidas abertas. Para cada etapa, registra somente o maior nÃ­vel demonstrado e o bloqueio que impede o nÃ­vel seguinte.
- A conclusÃ£o documental confirma que implementaÃ§Ã£o ou teste local nÃ£o basta para homologaÃ§Ã£o nem liberaÃ§Ã£o comercial. Q-33/Siescon Ã© a primeira dependÃªncia tÃ©cnica sequencial; governanÃ§a da IA e contratos/autorizaÃ§Ã£o dos provedores continuam condicionando os demais pilotos.
- `git diff --check`, `uv run python manage.py check` e `uv run python manage.py makemigrations --check --dry-run` passaram apÃ³s a atualizaÃ§Ã£o documental.

Limites: a matriz sintetiza evidÃªncias existentes e nÃ£o executa qualquer piloto ou integraÃ§Ãµes. Ela nÃ£o fecha etapas com checklist pendente nem substitui os aceites de D-73 e da etapa 12.

## V-035 â€” Etapa 07: demonstraÃ§Ã£o NFS-e local

Data: 19/09/2026. Ambiente: banco SQLite temporÃ¡rio, migrado e semeado exclusivamente com dados fictÃ­cios, removido ao final da inspeÃ§Ã£o. NÃ£o houve certificado, chamada ADN, consulta fiscal, dado de cliente, escrita em pasta Windows, egressÃ£o, cobranÃ§a ou custo.

- A verificaÃ§Ã£o de servidor confirmou a geraÃ§Ã£o de ZIP por empresa em `Tomadas/CÃ“DIGO -/` e `Emitidas/CÃ“DIGO -/`, a seleÃ§Ã£o da carteira inteira e o manifesto que separa sugestÃ£o acima de 95%, decisÃ£o manual e TransitÃ³ria em 0%. `uv run pytest tests/test_seed_demo_django.py -k 'nfse' tests/test_hub_workspace_views_django.py -k 'nfse_center' -q`: **4 aprovados, 66 desmarcados em 13,45 s**. Ruff de `views.py` e dos testes: aprovado.
- InspeÃ§Ã£o interativa com navegador local na demonstraÃ§Ã£o isolada: filtro exclusivo mudou de competÃªncia para emissÃ£o; `01092026` e `30092026` foram normalizados para `01/09/2026` e `30/09/2026`; a busca preservou os 24 itens no intervalo e refletiu os parÃ¢metros na URL. Um acumulador digitado atualizou a linha para â€œClassificadaâ€, â€œDefinida pelo contador Â· 100%â€ e o rÃ³tulo manual; ao limpar, a linha retornou para â€œEm revisÃ£oâ€, â€œTransitÃ³ria Â· 0%â€ e sem acumulador. Console sem erros.

Limites: ZIP e notas sÃ£o fictÃ­cios e nÃ£o comprovam importaÃ§Ã£o, classificaÃ§Ã£o fiscal, catÃ¡logo de acumuladores, coleta ADN, certificado, NSU, retomada ou deduplicaÃ§Ã£o real. Q-28 e a amostra/aceite do mÃ³dulo continuam necessÃ¡rios; a etapa 07 permanece em andamento.

## V-034 â€” Etapa 08: Central Integra Contador local

Data: 19/09/2026. Ambiente: macOS local, banco de teste e transporte simulado. Sem credencial, certificado, representaÃ§Ã£o, chamada Serpro, ciÃªncia DTE, emissÃ£o, guia, DAS, custo ou dado real.

- DTE cobre preparaÃ§Ã£o local sem despacho, empresas aptas, paginaÃ§Ã£o com nova autorizaÃ§Ã£o, leitura de teor com permissÃ£o especÃ­fica, auditoria e estado separado para resultado incerto. DCTFWeb preserva declaraÃ§Ã£o, recibo e guia sem transmissÃ£o. PARCSN cobre carteira, seleÃ§Ã£o, cotaÃ§Ã£o, autorizaÃ§Ã£o, pedido, parcelas e PDF validado.
- Reserva/liquidaÃ§Ã£o vinculam operaÃ§Ãµes ao consumo; indisponibilidade ou retorno incerto mantÃªm uma evidÃªncia conservadora e bloqueiam repetiÃ§Ã£o automÃ¡tica.
- `uv run pytest tests/test_dte.py tests/test_dte_access.py tests/test_dte_dispatch.py tests/test_integra_client.py tests/test_integra_dctfweb.py tests/test_integra_parcelamento.py tests/test_parcelamento_operations.py -q`: **63 aprovados em 13,98 s**. Ruff dos mÃ³dulos e testes envolvidos passou.

Limites: mocks e documentos sintÃ©ticos nÃ£o homologam contrato, credenciais centrais, certificado, representaÃ§Ã£o, tarifas ou serviÃ§os Serpro. Q-28 e uma autorizaÃ§Ã£o de custo imediatamente anterior sÃ£o necessÃ¡rios para o piloto; Q-36 impede ampliar PARCSN. A etapa 08 permanece em andamento.

## V-033 â€” Etapa 10: contrataÃ§Ã£o, tokens e cobranÃ§a local

Data: 19/09/2026. Ambiente: macOS local e banco de teste. Sem conta, credencial, sandbox, cliente, cobranÃ§a, webhook ou custo Asaas real.

- D-76/D-79 resolvem Q-01â€“Q-06 para implementaÃ§Ã£o: 7 dias de carÃªncia, somente leitura, reativaÃ§Ã£o apÃ³s pagamento, retorno a somente leitura por estorno/disputa, teste de 14 dias, fechamento no dia 1, vencimento no dia 10 e contrato manual operado pela Mewstack com auditoria.
- O cÃ³digo local contÃ©m livro de preÃ§os congelado por contrato, franquia/peso de token inteiro por mÃ³dulo, teto mensal, reserva/liquidaÃ§Ã£o idempotentes, fatura por competÃªncia e eventos de pagamento duplicados/fora de ordem. O webhook Asaas nÃ£o altera contratos manuais.
- `uv run pytest tests/test_platform_billing.py tests/test_platform_payments.py tests/test_token_billing.py tests/test_cica_contract_mfa.py tests/test_cica_operation_access.py -q`: **44 aprovados e 1 ignorado em 13,37 s**. O skip Ã© o cenÃ¡rio de concorrÃªncia de locks, coberto na validaÃ§Ã£o PostgreSQL histÃ³rica. `uv run ruff check src/apps/platform tests/test_platform_billing.py tests/test_platform_payments.py tests/test_token_billing.py`: aprovado.

Limites: nÃ£o hÃ¡ cliente Asaas para criar clientes/cobranÃ§as nem prova de Pix, boleto, cartÃ£o, atraso, estorno ou evento real. Q-08 ainda precisa fixar limites de IA/Triagem; sandbox/contrato e amostra autorizada estÃ£o em Q-28. A etapa 10 permanece em andamento.

## V-032 â€” Etapa 05: proveniÃªncia e escopo do conhecimento

Data: 19/09/2026. Ambiente: macOS local, CPython 3.12.13 e banco de teste. Sem dados de cliente, egressÃ£o Claude, credenciais, download de modelo, GPU, treinamento ou custo externo.

- D-89 autoriza os metadados de Ã¡rea, empresa e perÃ­odo nas fontes de conhecimento e exemplos de treinamento, como implementaÃ§Ã£o direta da cobertura contÃ¡bil, fiscal e folha de D-52. A migraÃ§Ã£o `intelligence.0027` preenche registros existentes com Ã¡rea geral; empresa e perÃ­odo permanecem opcionais.
- A recuperaÃ§Ã£o agora filtra fontes aprovadas para o escritÃ³rio e, quando hÃ¡ empresa na conversa, aceita somente fontes globais ou dessa empresa, priorizando as especÃ­ficas. Sem empresa, fontes especÃ­ficas sÃ£o excluÃ­das. A validaÃ§Ã£o impede relacionar fonte ou exemplo a empresa de outro escritÃ³rio.
- O manifesto QLoRA inclui os metadados de proveniÃªncia no hash do corpus. O runner os valida, mas nÃ£o os coloca no texto enviado ao treinamento; apenas pergunta, resposta e referÃªncias aprovadas compÃµem o dataset.
- `uv run ruff check src/apps/intelligence runtime/trainer tests/test_intelligence_sync_django.py tests/test_intelligence_training_django.py`: aprovado. `uv run python manage.py makemigrations --check --dry-run`: sem alteraÃ§Ãµes. `uv run pytest tests/test_intelligence_sync_django.py tests/test_intelligence_training_django.py tests/test_training_runner.py -q`: **26 aprovados em 12,53 s**.
- D-90 adicionou os hashes SHA-256 de manifesto e adaptador, o modelo base e a versÃ£o do adaptador a `EvaluationRun` e `ModelVersion`. A publicaÃ§Ã£o exige correspondÃªncia integral se a versÃ£o declarar um artefato; uma avaliaÃ§Ã£o de hash diferente Ã© recusada. `uv run pytest tests/test_intelligence_training_django.py tests/test_training_runner.py -q`: **20 aprovados em 6,99 s**.
- D-91 acrescentou `dataset_split` aos exemplos e `evaluation_manifest_sha256` Ã  avaliaÃ§Ã£o. O exportador seleciona `training` por padrÃ£o ou `evaluation` explicitamente; o runner QLoRA recusa qualquer linha fora de `training`. `uv run pytest tests/test_intelligence_training_django.py tests/test_intelligence_commands_django.py tests/test_training_runner.py -q`: **34 aprovados em 13,18 s**.
- D-92 acrescentou `rollback_model`, que sÃ³ reativa uma versÃ£o do mesmo escritÃ³rio apÃ³s validar sua avaliaÃ§Ã£o e a proveniÃªncia declarada; a operaÃ§Ã£o grava auditoria e nunca inicia treino. `uv run pytest tests/test_intelligence_training_django.py -q`: **17 aprovados em 7,01 s**.
- RevalidaÃ§Ã£o integral: `uv run ruff check .`, `uv run python manage.py check`, `uv run python manage.py makemigrations --check --dry-run` e `uv run pytest -q` passaram. A suÃ­te fechou em **754 aprovados, 3 ignorados e 8 subtestes em 28,01 s**; os skips continuam sendo Playwright Python opcional, OCR portuguÃªs local indisponÃ­vel e concorrÃªncia de locks coberta no PostgreSQL histÃ³rico.

Limites: isto nÃ£o comprova cobertura de corpus para as trÃªs Ã¡reas, curadoria humana, anonimizaÃ§Ã£o de todos os casos, conjunto independente de avaliaÃ§Ã£o, artefato de adaptador treinado, publicaÃ§Ã£o/rollback real ou egressÃ£o autorizada. Q-08, Q-09, Q-11 e Q-34 continuam abertos; a etapa 05 permanece em andamento.

## V-031 â€” AnÃ¡lise consolidada e revalidaÃ§Ã£o local

Data: 19/09/2026. Ambiente: macOS local, CPython 3.12.13 criado por `uv sync --locked --all-extras`; checkout inicialmente limpo. NÃ£o houve deploy, conexÃ£o a fornecedor, leitura de dado de cliente, uso de credencial, cobranÃ§a ou custo externo.

- A anÃ¡lise de documentaÃ§Ã£o e cÃ³digo estÃ¡ em [docs/planejamento/analise-projeto-2026-09-19.md](docs/planejamento/analise-projeto-2026-09-19.md). Ela confirma que as etapas 00â€“03 encerraram somente a implementaÃ§Ã£o/validaÃ§Ã£o local e que a etapa 04 depende do contrato Siescon Q-33.
- `uv run ruff check .` inicialmente reportou 16 E501 em `agent_v2.py`, `triage/forms.py`, `triage/services.py` e `urls_agent_v2.py`. Foram aplicadas quebras de linha sem mudanÃ§a de regra. A primeira suÃ­te completa revelou ainda que o modo de biblioteca interna apagava `folder_template`, embora o padrÃ£o deva ser preservado para a configuraÃ§Ã£o futura de Windows. O formulÃ¡rio agora mantÃ©m o padrÃ£o; nenhuma rota, modelo ou decisÃ£o de produto foi alterado. A reexecuÃ§Ã£o do Ruff retornou `All checks passed!`.
- `uv run python manage.py check`: sem problemas (0 silenciados). `uv run python manage.py makemigrations --check --dry-run`: `No changes detected`.
- `uv run pytest tests/test_edge_agent.py tests/test_triage_windows_paths.py tests/test_reconciliation_module.py -q`: **51 aprovados, 1 ignorado e 6 subtestes aprovados em 7,46 s**. O skip Ã© o OCR em portuguÃªs indisponÃ­vel nesta estaÃ§Ã£o, nÃ£o uma integraÃ§Ã£o externa.
- ReexecuÃ§Ã£o integral: `uv run pytest -q`: **747 aprovados, 3 ignorados e 8 subtestes aprovados em 26,90 s**. Os skips sÃ£o Playwright Python opcional, OCR portuguÃªs local indisponÃ­vel e concorrÃªncia de locks, que possui validaÃ§Ã£o PostgreSQL histÃ³rica prÃ³pria.

Limites: a revalidaÃ§Ã£o macOS nÃ£o repete as provas histÃ³ricas com PostgreSQL, Redis, Docker/WSL ou instalador Windows. Testes locais nÃ£o homologam Siescon nem substituem o piloto da etapa 12.

## V-008 â€” E-mail transacional CICA

Data: 18/09/2026. ImplementaÃ§Ã£o local autorizada por D-76; nenhuma conexÃ£o SMTP ou envio externo foi realizado.

- Adicionadas versÃµes HTML responsivas de confirmaÃ§Ã£o de cadastro, convite de equipe e recuperaÃ§Ã£o de senha. Os e-mails usam estrutura de tabela compatÃ­vel com clientes de e-mail, CTA explÃ­cita, texto de reserva e `suporte@mewstack.com.br` (D-76).
- A recuperaÃ§Ã£o de senha usa `html_email_template_name`; convite e confirmaÃ§Ã£o geram `html_message` pela mesma entrega transacional. Links continuam sendo os mesmos links seguros e temporÃ¡rios jÃ¡ existentes.
- `.venv/Scripts/python.exe -m pytest tests/test_cica_password_reset.py tests/test_cica_signup_flow.py tests/test_hub_workspace_views_django.py -q`: **62 aprovados em 52,30 s**. Ruff dos arquivos Python alterados: aprovado.
- UI/UX Pro Max orientou hierarquia de tÃ­tulo, tipografia e CTA; Watermelon nÃ£o possui bloco de e-mail transacional correspondente. RevisÃ£o conforme Web Interface Guidelines: contraste, hierarquia, texto alternativo de reserva e aÃ§Ã£o explÃ­cita. Limite: renderizaÃ§Ã£o local/teste, sem entrega SMTP em clientes reais. D-77 transfere configuraÃ§Ã£o, DNS e homologaÃ§Ã£o de entrega para a etapa 12.

## V-007 â€” Etapa 02: auditoria inicial de acesso e administraÃ§Ã£o

Data: 18/09/2026. Ambiente: checkout local, sem envio de e-mail, mudanÃ§a de contrato, chamada de API externa ou dados de cliente.

- A auditoria estÃ¡tica encontrou cadastro, recuperaÃ§Ã£o de senha, convites com expiraÃ§Ã£o/revogaÃ§Ã£o, MFA, escopo de empresas e mÃ³dulos, bloqueio por contrato/teste, isolamento de locatÃ¡rios e console de plataforma.
- `.venv/Scripts/python.exe -m pytest tests/test_cica_signup_security.py tests/test_cica_signup_flow.py tests/test_mfa.py tests/test_permissions_and_lockout.py tests/test_tenant_isolation.py tests/test_invitation_takeover.py tests/test_cica_contract_mfa.py tests/test_cica_operation_access.py tests/test_platform_tenant_django.py -q`: **83 aprovados em 54,47 s**.
- Playwright local: cadastro em desktop e mÃ³vel 390Ã—844, sem overflow horizontal, com foco visÃ­vel de 3 px no primeiro campo e console sem erros. Capturas: `stage02-signup-desktop.png` e `stage02-signup-mobile.png`. SessÃ£o fechada.
- RevisÃ£o de interface: UI/UX Pro Max indicou validaÃ§Ã£o inline, resumo focalizÃ¡vel em falha de formulÃ¡rio, foco visÃ­vel e autenticaÃ§Ã£o compatÃ­vel com gestores de senha. Watermelon nÃ£o retornou bloco correspondente para formulÃ¡rio de autenticaÃ§Ã£o; composiÃ§Ã£o existente foi preservada. ReferÃªncias de produto: [SaaSFrame Invite Team](https://www.saasframe.io/patterns/invite-friends), [Roles & Permissions](https://www.saasframe.io/patterns/roles-permissions) e [Login](https://www.saasframe.io/categories/login), adaptadas como evidÃªncia de padrÃ£o, sem cÃ³pia. Auditoria dos templates de autenticaÃ§Ã£o contra as [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md): campos possuem rÃ³tulos, tipos e `autocomplete`; nÃ£o foi aplicada mudanÃ§a nesta auditoria.
- Limites: teste local nÃ£o homologa SMTP, domÃ­nio/DNS, termos, condiÃ§Ãµes comerciais, e-mail entregue/falho nem todas as jornadas visuais. Q-01â€“Q-06 e Q-29 permanecem abertos; etapa 02 nÃ£o estÃ¡ concluÃ­da.

## V-006 â€” Retomada da etapa 01 em 18/09/2026

Pedido D-70 e decisÃ£o D-71. InspeÃ§Ã£o confirmou que `runtime/trainer/Dockerfile` exige imagem externa e `runtime/trainer/runner.py` chama `llamafactory-cli` para executar treinamento. Mantida a ferramenta somente para esse runtime; a imagem oficial foi fixada por digest. Corrigido o Dockerfile: a cÃ³pia de `runner.py` apontava para a raiz inexistente do contexto e agora usa `runtime/trainer/runner.py`.

- `docker build --file runtime/trainer/Dockerfile --build-arg LLAMAFACTORY_IMAGE=hiyouga/llamafactory@sha256:46b6969e444681829294ed1fce2c4e8848613e654b682dc0359ba94357a0267b --tag cica-trainer:stage01 .`: aprovado; imagem local `sha256:f0c956â€¦`, 26.4 GB.
- `docker run --rm --entrypoint llamafactory-cli cica-trainer:stage01 version/env`: CLI 0.9.6.dev0 iniciou; PyTorch 2.6.0+cu124; ambiente WSL detectou CPU, sem GPU disponÃ­vel.
- `runtime/trainer/image.env` guarda o digest; o CI agora constrÃ³i `runtime/trainer/Dockerfile` com a mesma referÃªncia. A leitura do arquivo e o rebuild local por ele passaram usando cache.
- `.venv/Scripts/python.exe -m pytest tests/test_training_runner.py tests/test_deployment_config_django.py -q`: 12 aprovados.
- `.venv/Scripts/python.exe -m ruff check . --output-format concise`: aprovado.
- Limite: nÃ£o houve download de modelo, dataset ou treino; CPU detectada nÃ£o Ã© avaliaÃ§Ã£o de GPU. A configuraÃ§Ã£o do CI foi testada localmente, mas a execuÃ§Ã£o remota ainda depende do prÃ³ximo push. Q-28 e Q-30 impedem homologaÃ§Ã£o e mantÃªm a etapa 01 aberta conforme D-61.

AtualizaÃ§Ã£o D-72: Fedrizzi Contabilidade Ã© o ambiente disponÃ­vel e o proprietÃ¡rio aprova cada mÃ³dulo. NÃ£o houve acesso externo nesta execuÃ§Ã£o. A prova ainda depende da amostra e do acesso seguro de cada integraÃ§Ã£o, alÃ©m das metas de aceite.

AtualizaÃ§Ã£o D-73: metas de liberaÃ§Ã£o aprovadas para uso em todas as etapas. Elas ainda nÃ£o foram medidas nesta execuÃ§Ã£o; a primeira evidÃªncia depende da amostra e do acesso seguro Fedrizzi.

ValidaÃ§Ã£o local posterior Ã  D-73: `.venv/Scripts/python.exe -m pytest -q` resultou em **742 aprovados, 2 ignorados e 8 subtestes aprovados em 85,31 s**. Os ignorados sÃ£o o Playwright Python opcional e o teste de lock que exige PostgreSQL; ambos tÃªm cobertura especÃ­fica registrada anteriormente. `manage.py check`, `makemigrations --check --dry-run` e Ruff continuam aprovados. A inspeÃ§Ã£o sem valores de `.env` e do ambiente local nÃ£o encontrou configuraÃ§Ã£o global de Siescon, Serpro, NFS-e, Asaas ou SMTP/e-mail. Em seguida, a inspeÃ§Ã£o segura do banco confirmou para Fedrizzi um `IntelligenceConnector` em modo `direct_odbc` e uma `DataSource` DomÃ­nio local em estado `ready`; DSN, credenciais, empresas e documentos nÃ£o foram lidos. Isso corrige o registro anterior: DomÃ­nio jÃ¡ estÃ¡ conectado, conforme D-74.

## 18/09/2026 â€” complemento V-005: perÃ­odo simplificado (D-69)

Refinamento visual solicitado em seguida (â€œmais bonitoâ€): busca/situaÃ§Ã£o na primeira linha, perÃ­odo agrupado em superfÃ­cie discreta, atalhos sem bordas pesadas, campos de 44px e aÃ§Ãµes alinhadas. UI/UX Pro Max consultado para espaÃ§amento e reflow; Watermelon Astrix consultado como referÃªncia de composiÃ§Ã£o de ferramenta fiscal. Preservadas as referÃªncias de produto anteriormente registradas. Template e CSS auditados com a fonte atual das Web Interface Guidelines. Playwright: 24 resultados apÃ³s aplicar mÃªs; erro de data, alternÃ¢ncia exclusiva e mobile sem overflow; console sem erros. Inspecionadas capturas `nfse-polish-desktop.png` (escuro), `nfse-polish-light.png` e `nfse-polish-mobile.png`. Apenas refinamento visual da demo; etapa permanece aberta.

- EmissÃ£o usa digitaÃ§Ã£o DD/MM/AAAA, aceita oito nÃºmeros e oferece Este mÃªs, MÃªs anterior e Limpar datas. Campos inativos sÃ£o desabilitados; competÃªncia continua exclusiva.
- Datas invÃ¡lidas e intervalo invertido apresentam erro prÃ³ximo aos campos; submissÃ£o invÃ¡lida coloca foco no campo. Servidor tambÃ©m valida e preserva valores. URLs ISO anteriores continuam aceitas.
- Corrigida a filtragem da demo antiga: usa a mesma emissÃ£o do payload normalizado exibida na tabela, antes de limitar resultados. Setembro/2026 retornou 24 notas; agosto retornou zero; competÃªncia setembro retornou 24.
- Playwright local em localhost:8000: desktop 1440Ã—1000 claro/escuro e mobile 390Ã—844, sem overflow horizontal; atalhos, digitaÃ§Ã£o sem barras, erro, alternÃ¢ncia de critÃ©rio, Tab e foco visÃ­vel verificados. Console: zero erros. SessÃ£o fechada apÃ³s inspeÃ§Ã£o.
- EvidÃªncias: `nfse-simple-dates-desktop.png`, `nfse-simple-dates-mobile.png`, `nfse-simple-dates-dark.png`. Ruff focado aprovado. Auditoria dos arquivos de template, JS e CSS conforme fonte atual das Web Interface Guidelines: rÃ³tulos, teclado, mensagens, contraste de tema, responsividade e estado em URL revisados.
- Pesquisa: [GOV.UK Date input](https://design-system.service.gov.uk/components/date-input/) fundamenta entrada por teclado para datas conhecidas; adaptada para dois campos brasileiros em vez de seis campos separados. UI/UX Pro Max: formato local, teclado numÃ©rico e validaÃ§Ã£o. Watermelon consultado por filtro, sem bloco correspondente; mantida a composiÃ§Ã£o existente, anteriormente informada por SaaSFrame (Remote, June e Intercom).
- Limite: demonstraÃ§Ã£o local, sem homologaÃ§Ã£o fiscal ou conclusÃ£o da etapa 07.

Atualizado em 17/09/2026. Registro na raiz conforme D-59. Leia com [PLANO-MESTRE.md](PLANO-MESTRE.md) e [DECISOES.md](DECISOES.md).

**Escopo atual:** etapa 00 concluÃ­da; etapa 01 aberta e bloqueada em 18/09/2026 apenas pela imagem-base aprovada do runtime de treinamento (Q-37). DecisÃµes do responsÃ¡vel ficam em DECISOES.md; este arquivo registra verificaÃ§Ãµes tÃ©cnicas, sem confundir decisÃ£o, teste e homologaÃ§Ã£o.

## V-001 â€” Base tÃ©cnica observada antes da ediÃ§Ã£o documental

Data: 17/09/2026, nesta conversa. Ambiente: checkout Windows local, Python da `.venv`, configuraÃ§Ãµes Django de teste; `TEST_USE_EXTERNAL_SERVICES=false` e `TEST_SQLITE_PATH` vazio. Banco de teste SQLite em memÃ³ria. Sem homologaÃ§Ã£o externa nesta anÃ¡lise.

| VerificaÃ§Ã£o | Resultado observado | Limite |
|---|---|---|
| `python -m pytest -q` | 740 aprovados, 1 ignorado, 8 subtestes aprovados; 74,48 s | NÃ£o demonstra concorrÃªncia PostgreSQL nem operaÃ§Ã£o real de serviÃ§os externos |
| Teste ignorado | `tests/test_cica_auth_flow.py:155`: Python Playwright opcional | NÃ£o equivale a navegaÃ§Ã£o validada; nÃ£o houve inspeÃ§Ã£o Playwright nesta etapa |
| `python manage.py check` | Sem problemas (0 silenciados) | ConfiguraÃ§Ãµes de teste, nÃ£o certificaÃ§Ã£o de produÃ§Ã£o |
| `python manage.py makemigrations --check --dry-run` | No changes detected | Nenhuma migration aplicada por esta etapa; nÃ£o prova migraÃ§Ã£o de base produtiva |
| `python -m ruff check . --output-format concise` | 66 violaÃ§Ãµes: comprimento de linha e ordenaÃ§Ã£o de imports | CI ainda bloqueado; nÃ£o corrigidas por restriÃ§Ã£o Ã  etapa 00 |
| InventÃ¡rio inicial Git | 291 entradas em `git status --short` antes da documentaÃ§Ã£o | Trabalho local anterior preservado; nÃ£o Ã© uma release consolidada |

Os comandos acima foram executados na anÃ¡lise anterior Ã  materializaÃ§Ã£o dos documentos. A leitura de Ruff foi repetida em JSON antes da restriÃ§Ã£o final de escopo e manteve 66 achados. NÃ£o foram refeitos testes funcionais apÃ³s mudanÃ§as exclusivamente documentais.

## V-002 â€” EvidÃªncia estÃ¡tica por Ã¡rea

| Ãrea | Implementado / observado no cÃ³digo | Testado localmente nesta anÃ¡lise | HomologaÃ§Ã£o real / venda |
|---|---|---|---|
| Cadastro, acesso, organizaÃ§Ãµes, auditoria e privacidade | Modelos, rotas, serviÃ§os e testes no checkout | SuÃ­te V-001; nÃ£o atribuir cobertura integral a cada fluxo | Jornadas externas/produÃ§Ã£o nÃ£o homologadas por esta anÃ¡lise |
| DomÃ­nio | Consultas fixas e limites 1.000/10.000/5.000; agente Python, fila, sync e descoberta | SuÃ­te V-001 e leitura do cÃ³digo | HÃ¡ registros histÃ³ricos de sondagens ODBC; nÃ£o comprovam cobertura completa ou instalaÃ§Ã£o vendÃ¡vel |
| Agente Windows nativo | Heartbeat, backup e arquivamento; sincronizaÃ§Ã£o local ainda depende de Python | Leitura de `Worker.cs` e README; build nÃ£o executado nesta etapa | InstalaÃ§Ã£o limpa, atualizaÃ§Ã£o e destino real ainda pendentes |
| Siescon | ReferÃªncia no modelo/UI; adaptador nÃ£o encontrado | Busca estÃ¡tica; nÃ£o hÃ¡ teste de conector real | Banco disponÃ­vel confirmado pelo responsÃ¡vel; acesso e layout ainda nÃ£o inspecionados |
| IA | API, roteamento local, corpus, runner QLoRA, avaliaÃ§Ã£o e publicaÃ§Ã£o; busca lexical | SuÃ­te V-001; sem chamada de IA nesta etapa | Pipeline completo e hardware definitivo nÃ£o homologados; geraÃ§Ã£o histÃ³rica isolada nÃ£o Ã© aceite de produto |
| Triagem | OAuth/IMAP, leitores, quarentena, revisÃ£o/arquivo e trabalho Windows | SuÃ­te V-001 | Caixas, scanner, anÃ¡lise e arquivamento reais ainda requerem piloto |
| NFS-e | Cliente ADN, mTLS, checkpoints e Ã¡rea operacional | SuÃ­te V-001, respostas simuladas | NÃ£o houve consulta ADN nesta anÃ¡lise |
| Integra | DTE, DCTFWeb, PARCSN, filas e consumo | SuÃ­te V-001, transporte simulado | NÃ£o houve consulta/ciÃªncia/emissÃ£o Serpro nesta anÃ¡lise |
| ConciliaÃ§Ã£o | Fontes preservadas, layouts, movimentos, lanÃ§amentos e exportaÃ§Ã£o | SuÃ­te V-001, fixtures | Layouts reais, importaÃ§Ã£o nos ERPs, OCR e volume ainda exigem prova |
| Radar | Coleta e tarefas existentes | SuÃ­te V-001 | Agenda e relevÃ¢ncia operacional nÃ£o homologadas nesta anÃ¡lise |
| CobranÃ§a | Medidores/faturas e receptor Asaas | SuÃ­te V-001 | Cliente de cobranÃ§a e ciclo completo Asaas ainda pendentes |
| Infraestrutura | Compose, workflows, imagens e runbooks | InspeÃ§Ã£o estÃ¡tica | NÃ£o houve build/deploy, PostgreSQL/Redis reais ou restauraÃ§Ã£o nesta etapa |

## V-003 â€” Etapa 00: documentaÃ§Ã£o e continuidade

Estado: **concluÃ­da em 17/09/2026**. Aceite documental atendido; nÃ£o equivale a conclusÃ£o funcional dos mÃ³dulos.

Entregas: plano e decisÃµes na raiz, registro de validaÃ§Ãµes, 14 arquivos de etapa com prompts, inventÃ¡rio estÃ¡tico, dÃºvidas com responsÃ¡veis/dependÃªncias, ponteiros dos endereÃ§os anteriores e instruÃ§Ã£o de continuidade em AGENTS.md.

ConferÃªncia realizada por script local de leitura, sem importar Django ou acessar bancos:

- 23 arquivos centrais/etapas conferidos; 135 destinos de links locais existentes.
- 14 etapas numeradas de 00 a 13, cada uma com dependÃªncias, decisÃµes, escopo/checklist, bloqueios, testes/aceite, evidÃªncias/prÃ³ximo passo e prompt.
- 60 IDs de decisÃ£o Ãºnicos (D-01â€“D-60), preservando o grau de confirmaÃ§Ã£o dos registros histÃ³ricos.
- 36 IDs de perguntas Ãºnicos (Q-01â€“Q-36); resolvidas permanecem identificadas, sem reabrir Q-07/Q-10.
- Nenhum caractere Unicode de substituiÃ§Ã£o nos 23 arquivos conferidos.
- `git diff --check -- '*.md'`: aprovado, apenas avisos Git de conversÃ£o futura LF/CRLF.

A primeira execuÃ§Ã£o do verificador textual recebeu acentos substituÃ­dos pelo pipe PowerShell e reportou tÃ­tulos ausentes; corrigido o verificador para comparar texto normalizado. A segunda execuÃ§Ã£o passou. Os arquivos estavam em UTF-8 e nÃ£o foram alterados para contornar a validaÃ§Ã£o.

NÃ£o houve ediÃ§Ã£o de cÃ³digo da aplicaÃ§Ã£o, migraÃ§Ã£o, instalaÃ§Ã£o de dependÃªncias, conexÃ£o a banco de cliente, execuÃ§Ã£o de treino, chamada paga, deploy ou publicaÃ§Ã£o nesta etapa. NÃ£o foram alterados arquivos `.env`, credenciais ou dados de clientes.

## Como acrescentar evidÃªncia

## V-009 â€” Etapa 02: acesso e administraÃ§Ã£o locais

Data: 18/09/2026. Ambiente: checkout local Windows e aplicaÃ§Ã£o em `127.0.0.1:8000`; sem SMTP, DNS, API paga, envio externo ou acesso a dado de cliente.

- `.venv/Scripts/python.exe -m pytest tests/test_accounts_api.py tests/test_hub_api.py tests/test_tenant_isolation.py tests/test_permissions_and_lockout.py -q`: **22 aprovados em 21,04 s**. Cobrem login/CSRF, API somente leitura, isolamento por organizaÃ§Ã£o e recusa de acesso sem contexto.
- `.venv/Scripts/python.exe -m pytest tests/test_seed_demo_django.py -k "separate_demo_link or visitor_cannot_mutate or copilot_conversation or nfse_review_decision" -q`: **4 aprovados em 22,58 s**. A sessÃ£o demo Ã© privada, nÃ£o altera administraÃ§Ã£o/empresas e nÃ£o persiste conversa ou decisÃ£o compartilhada.
- Playwright autenticado: o login local levou uma administradora ao cadastro obrigatÃ³rio de MFA; o cÃ³digo de uso Ãºnico abriu o painel. Equipe, empresas e configuraÃ§Ãµes responderam 200; a viewport 390Ã—844 nÃ£o teve overflow horizontal, o foco era visÃ­vel e o console tinha zero erros. A sessÃ£o foi fechada ao fim.
- A tentativa de `seed_demo` foi recusada porque o slug de demonstraÃ§Ã£o jÃ¡ pertence a um escritÃ³rio operacional local. Nenhum dado foi sobrescrito. Isso confirma a proteÃ§Ã£o contra criaÃ§Ã£o de massa fictÃ­cia sobre escritÃ³rio operacional; os testes isolados acima usam banco de teste.

Limites: as regras D-79 serÃ£o operacionalizadas e homologadas na etapa 10. SMTP Brevo, DNS e entrega real sÃ£o da etapa 12 por D-77/D-78. Esta validaÃ§Ã£o nÃ£o Ã© homologaÃ§Ã£o externa nem liberaÃ§Ã£o comercial.

## V-010 â€” Etapa 03: contrato ODBC DomÃ­nio Fedrizzi

Data: 18/09/2026. Ambiente: conexÃ£o ODBC DomÃ­nio jÃ¡ registrada para Fedrizzi (D-74), com autorizaÃ§Ã£o de homologaÃ§Ã£o D-72. Nenhum DSN, credencial, empresa, documento ou conteÃºdo de origem foi exibido.

- `validate_dominio_odbc_contract` foi executado usando a referÃªncia de DSN protegida do conector: **4 consultas allowlisted, 5 objetos obrigatÃ³rios, 13.875 linhas lidas e 0 coluna ausente**. A execuÃ§Ã£o registrou auditoria de contrato e nÃ£o escreveu no DomÃ­nio.
- `discover_dominio_schema --limit 500 --apply` examinou e registrou somente metadados: **500 objetos, 4.733 colunas, 0 objeto novo/alterado e 500 inalterados**. Isso confirma que o catÃ¡logo jÃ¡ persistido corresponde ao ambiente consultado.

Limites: as consultas atuais nÃ£o estabelecem ainda a cobertura integral de dados contÃ¡beis, fiscais e de folha, nem provam o agente nativo, paginaÃ§Ã£o/incremental, interrupÃ§Ã£o de rede, instalaÃ§Ã£o limpa ou importaÃ§Ã£o Web. Esses itens seguem abertos na etapa 03.

Complemento: a rota v2 `dominio/companies` e o processador nativo paginado foram implementados. `tests/test_intelligence_agent_django.py` teve **5 aprovados em 28,29 s**, incluindo autenticaÃ§Ã£o e espelhamento da pÃ¡gina local. `dotnet build agent-windows/src/CICA.Agent.Service/CICA.Agent.Service.csproj -c Release --no-restore` concluiu sem avisos nem erros. A paginaÃ§Ã£o Ã© por cÃ³digo DomÃ­nio, 500 linhas por pÃ¡gina, e nunca desativa empresas em pÃ¡gina parcial. Ainda falta executar o binÃ¡rio com DSN Fedrizzi, testar fila/rede/reinÃ­cio e completar as projeÃ§Ãµes contÃ¡bil, fiscal e folha.

## V-011 â€” Etapa 03: mÃ¡quina Fedrizzi e pacote instalÃ¡vel

Data: 18/09/2026. Ambiente: estaÃ§Ã£o Windows na rede Fedrizzi. Sem instalar serviÃ§o ainda, para nÃ£o registrar um processo destinado a falhar.

- DSN de sistema `contabil` encontrado em 32 e 64 bits, ambos sobre SQL Anywhere 17; o conector Fedrizzi no CICA estÃ¡ saudÃ¡vel e tem DSN protegido configurado.
- NÃ£o havia serviÃ§o ou diretÃ³rio de dados CICA/HubContador/CICA prÃ©vio. A conta atual pertence ao grupo Administradores; .NET SDK 10 e WiX 6 estÃ£o instalados.
- `agent-windows/build.ps1` produziu MSI, checksum e inventÃ¡rio de dependÃªncias em `agent-windows/artifacts/`. O MSI tem 79.285.770 bytes. Ele ainda usa identidade de instalador legada no nome interno; a renomeaÃ§Ã£o externa para CICA continua na etapa 03.
- A instalaÃ§Ã£o/pareamento nÃ£o foi executada porque o checkout sÃ³ aceita `localhost`, nÃ£o hÃ¡ URL HTTPS pÃºblica, CA de agente nem chave de CA configuradas. O configurador exige URL HTTPS e o endpoint v2 exige CA para emitir o certificado do agente. Instalar nesse estado criaria um serviÃ§o sem configuraÃ§Ã£o funcional.

PrÃ³xima aÃ§Ã£o necessÃ¡ria: disponibilizar o endpoint HTTPS da CICA e configurar sua CA de agente no ambiente que o atende; entÃ£o gerar o enrollment, instalar o MSI e validar conexÃ£o, reinÃ­cio, corte de rede e retomada nesta mesma mÃ¡quina. NÃ£o hÃ¡ custo estimado para a instalaÃ§Ã£o local; uma publicaÃ§Ã£o/hospedagem, se necessÃ¡ria, exige orÃ§amento e autorizaÃ§Ã£o especÃ­ficos.

## V-005 â€” DemonstraÃ§Ã£o NFS-e: carteira e download em lote

### RevisÃ£o visual adicional â€” 18/09/2026

Complemento: substituÃ­do input month nativo por mÃªs (select com nomes completos) e ano digitÃ¡vel; preservado parÃ¢metro legado de competÃªncia no servidor. Intervalo de emissÃ£o fixado em duas colunas, com cache CSS v4. Playwright confirmou campos De/AtÃ© no mesmo eixo e altura 44 px em desktop; mÃªs/ano selecionÃ¡veis e sem overflow a 390 px. InspeÃ§Ã£o visual salva em `nfse-period-fixed.png` e `nfse-month-mobile.png`.

CSS especÃ­fico `nfse.css` corrige conflitos do grid genÃ©rico: filtros alinhados, apenas perÃ­odo ativo visÃ­vel, campo de acumulador de 42 px com bordas arredondadas, Ã­cone de ediÃ§Ã£o decorativo, foco e estados hover/seleÃ§Ã£o. JS versionado evita reaproveitamento da versÃ£o anterior pelo navegador. Limpar acumulador agora mostra revisÃ£o e TransitÃ³ria 0%, inclusive numa linha originalmente classificada.

Playwright em `127.0.0.1:8000`: desktop 1440Ã—1000 claro/escuro e mÃ³vel 390Ã—844 escuro inspecionados por screenshots. Sem overflow horizontal. Digitar `501` mudou situaÃ§Ã£o para Classificada; Enter selecionou uma nota; limpar mostrou TransitÃ³ria 0%; alternar para emissÃ£o ocultou competÃªncia e mostrou somente o intervalo. Console: zero erros e avisos. Auditoria dos arquivos alterados conforme [Vercel Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md), com correÃ§Ã£o do rÃ³tulo mÃ³vel SituaÃ§Ã£o e dos blocos vazios provocados por content-visibility.

ReferÃªncias mantidas da pesquisa desta tarefa: Watermelon Gridline para organizaÃ§Ã£o operacional; [Remote](https://www.saasframe.io/examples/remote-empty-employee-table), [June](https://www.saasframe.io/examples/june-dashboard) e [Intercom](https://www.saasframe.io/examples/intercom-users-table) para barra de aÃ§Ãµes e tabela densa. UI/UX Pro Max consultado para ediÃ§Ã£o inline e dimensÃµes consistentes de input. Sem redesenhar a navegaÃ§Ã£o geral.

Data: 18/09/2026. Ambiente: demonstraÃ§Ã£o local `http://127.0.0.1:8001`, dados fictÃ­cios; sem consulta ADN, certificado, escrita em pasta Windows ou alteraÃ§Ã£o da classificaÃ§Ã£o persistida.

- A carteira exibe data de emissÃ£o extraÃ­da do payload normalizado da NFS-e; a massa nova de demonstraÃ§Ã£o inclui `dhEmi` no XML e persiste `issued_at` ao criar o documento.
- O filtro permite escolher competÃªncia de emissÃ£o ou intervalo de emissÃ£o. A interface alterna o Ãºnico critÃ©rio ativo sem combinar ambos.
- Download demonstrativo gera ZIP com `Emitidas/CÃ“DIGO -/` ou `Tomadas/CÃ“DIGO -/`, XMLs e `manifesto-classificacao.csv`. Uma nota sem acumulador segue como TransitÃ³ria a 0%; classificadas da demonstraÃ§Ã£o mostram acumulador e 97%. Acumulador digitado Ã© decisÃ£o manual no manifesto.
- `Enter` em um acumulador seleciona a nota e avanÃ§a o foco, sem submeter um download vazio. Verificado no navegador local.
- Digitar acumulador foi inspecionado no navegador: a linha passou para Classificada e exibiu `Definida pelo contador Â· 100%` (D-68).
- Ruff focado e `git diff --check` passaram. Playwright inspecionou a lista, a alternÃ¢ncia de filtro, seleÃ§Ã£o por teclado e viewport mÃ³vel 390Ã—844; console sem erros.

Limites: esta Ã© somente demonstraÃ§Ã£o local. A etapa 07 permanece aberta: coleta ADN, certificados, deduplicaÃ§Ã£o real, catÃ¡logo de acumuladores e homologaÃ§Ã£o de importaÃ§Ã£o DomÃ­nio nÃ£o foram concluÃ­dos.

Use ID V Ãºnico, data, etapa, ambiente, comando/procedimento, resultado, caminho da evidÃªncia e limites. Diferencie resultado observado nesta execuÃ§Ã£o de relato histÃ³rico. Registre falhas e skips. SÃ³ avance de teste local para homologaÃ§Ã£o apÃ³s prova no ambiente correspondente e de homologaÃ§Ã£o para liberaÃ§Ã£o com o aceite aplicÃ¡vel.

HistÃ³rico detalhado anterior: [registro de execuÃ§Ã£o](docs/planejamento/registro-de-execucao.md). [PrÃ³xima etapa preparada](docs/planejamento/etapas/01-base-tecnica.md), ainda nÃ£o autorizada pela Ãºltima instruÃ§Ã£o de escopo.

## V-004 â€” Etapa 01: estabilizaÃ§Ã£o tÃ©cnica em andamento

Data: 17â€“18/09/2026. Ambiente: Windows local, Python .venv, Docker Desktop 4.91.0, WSL 2.7.1, PostgreSQL 17 e Redis 7.4 em volumes locais isolados. Sem conexÃ£o a banco de cliente, ERP, API paga, deploy ou alteraÃ§Ã£o de dados de clientes.

| VerificaÃ§Ã£o | Resultado | Limite |
|---|---|---|
| Ruff | 66 achados iniciais eliminados; ruff check aprovado | ruff format --check encontra 95 arquivos fora do formato, mas esse comando nÃ£o integra o CI e nÃ£o foi aplicado em massa para nÃ£o reformatar trabalho local alheio |
| MigraÃ§Ãµes e Django | manage.py check aprovado; makemigrations --check --dry-run sem alteraÃ§Ãµes | Validado nas configuraÃ§Ãµes de teste |
| SuÃ­te completa | 740 aprovados, 2 ignorados, 8 subtestes; 72,61 s | SQLite em memÃ³ria; o teste concorrente Ã© corretamente ignorado nesse backend e executado em PostgreSQL |
| Testes de risco em PostgreSQL | 95 aprovados em token billing, faturamento, treinamento IA, fila de triagem, conciliaÃ§Ã£o, MCP e privacidade; 69,67 s | Bancos `test_saas` e `test_knowledge` isolados; nÃ£o Ã© homologaÃ§Ã£o externa |
| ConcorrÃªncia de consumo | 4 chamadas paralelas com a mesma chave de idempotÃªncia produziram 1 evento e 8 tokens reservados; 1 teste aprovado em PostgreSQL | NÃ£o Ã© teste de carga; faturamento, filas e publicaÃ§Ã£o foram exercitados na suÃ­te de risco com locks/transaÃ§Ãµes PostgreSQL |
| DependÃªncias | pypdf atualizado de 6.9.2 para 6.16.1; uv lock, uv sync --locked --all-extras, pip check e pip_audit aprovados | O projeto local nÃ£o Ã© auditÃ¡vel no PyPI, mas todas as dependÃªncias publicadas estÃ£o sem vulnerabilidades conhecidas |
| Agente Windows | Service, configurador e MSI foram compilados; agent-windows/artifacts/CICAAgent.msi gerado com SHA-256 6ed0a1592fc3f0b5c5277e9dfc3ce8f27c000c6ca493cb3f5c245ac94c23f9b9 | NÃ£o instalado nem exercitado em mÃ¡quina limpa |
| Docker/WSL e serviÃ§os | Docker Desktop 4.91.0 e WSL 2.7.1 operacionais; Compose iniciou PostgreSQL 17 e Redis 7.4 saudÃ¡veis | ServiÃ§os locais persistem em volumes Docker; nÃ£o equivalem a ambiente de produÃ§Ã£o |
| Worker real | Celery com pool `solo` no Windows consumiu `platform.advance_tenant_lifecycles` via Redis e retornou `SUCCESS` com resultado `0` | O pool padrÃ£o `prefork` falha no Windows com `WinError 5`; produÃ§Ã£o Linux deve manter pool prÃ³prio e ser homologada na etapa 12 |
| Imagens Docker | `cica-backend:stage01` e `cica-multimodal:stage01` construÃ­das, respectivamente `sha256:5c9a3b3â€¦105d2` e `sha256:59e292aâ€¦80cdc` | O runtime de treinamento nÃ£o foi construÃ­do: falta referÃªncia LlamaFactory aprovada por digest (Q-37) |

Nenhuma alteraÃ§Ã£o de migraÃ§Ã£o foi gerada. As correÃ§Ãµes de lint foram mecÃ¢nicas: ordenaÃ§Ã£o de imports e formataÃ§Ã£o das nove unidades que apresentavam os 66 achados. A validaÃ§Ã£o PostgreSQL revelou e corrigiu dois locks invÃ¡lidos de `JournalEntry` com joins opcionais: aprovaÃ§Ã£o e exportaÃ§Ã£o agora travam somente a linha principal (`of=("self",)`). A atualizaÃ§Ã£o de pypdf Ã© fixa e reproduzida em pyproject.toml, requirements.txt e uv.lock.

PrÃ³ximo procedimento: receber e registrar a referÃªncia LlamaFactory aprovada em Q-37, construir o runtime de treinamento e registrar o resultado. Conforme D-61, a etapa permanece aberta atÃ© esse item terminar; nenhuma imagem, modelo ou treinamento serÃ¡ escolhido por inferÃªncia.
## V-012 â€” Marca CICA no agente e tela de entrada

Data: 18/09/2026. Toda referÃªncia textual e de caminho Ã  marca anterior foi removida do cÃ³digo-fonte ativo. O serviÃ§o Ã© `CicaAgent`, o configurador e o pacote usam CICA, e o instalador recompilado estÃ¡ em `agent-windows/artifacts/CicaAgent.msi` (SHA-256 `5e111919be1751997239955a3435756a3cb26c2d06fe00fe4f2ed4c03b85a2ec`). `manage.py check` passou; a resposta local de `/entrar/` contÃ©m os assets `cica-auth.css` e `cica-auth.js`; os dois projetos .NET compilaram sem avisos ou erros. A inspeÃ§Ã£o visual automatizada nÃ£o foi possÃ­vel porque nÃ£o hÃ¡ navegador disponÃ­vel nesta estaÃ§Ã£o nesta sessÃ£o; esta limitaÃ§Ã£o nÃ£o afeta a validaÃ§Ã£o do template e dos assets.

## V-013 â€” Leitura integral de backup DomÃ­nio no agente nativo

Data: 18/09/2026. Foram removidos os limites silenciosos de 10.000 empresas e 100.000 lanÃ§amentos do `BackupProcessor`. A leitura do backup continua paginada em lotes de 500 no envio Ã  API, mas nÃ£o descarta linhas por teto fixo. O projeto `Cica.Agent.Service` compilou em Release, sem avisos ou erros. Isto valida somente o cÃ³digo e o build; a execuÃ§Ã£o contra um backup autorizado, retomada apÃ³s falha e prova de nÃ£o duplicaÃ§Ã£o continuam pendentes na etapa 03.

## V-014 â€” InstalaÃ§Ã£o local do agente CICA

Data: 18/09/2026. O MSI `CicaAgent.msi` foi instalado com privilÃ©gio administrativo nesta estaÃ§Ã£o. O Windows registrou o serviÃ§o `CicaAgent` com nome exibido `CICA Agent`, inicializaÃ§Ã£o automÃ¡tica e estado `Running`. Os arquivos foram instalados em `C:\Program Files\CICA Agent\Service` e o diretÃ³rio de configuraÃ§Ã£o foi criado em `C:\ProgramData\CICA\Agent`. Sem `agent.config`, o serviÃ§o permaneceu ativo sem tentativa de DomÃ­nio ou rede, como previsto. Uma tentativa nÃ£o elevada retornou erro 1925; a instalaÃ§Ã£o elevada retornou cÃ³digo 0. O reinÃ­cio pÃ³s-instalaÃ§Ã£o ainda requer um terminal administrativo nesta estaÃ§Ã£o; pareamento HTTPS e comunicaÃ§Ã£o externa ficam para a etapa 12 por D-81.

## V-015 â€” RecuperaÃ§Ã£o do ambiente local e catÃ¡logo DomÃ­nio

Data: 18/09/2026. O banco local de desenvolvimento `db.sqlite3` nÃ£o era legÃ­vel pelo SQLite. Foi substituÃ­do pela cÃ³pia Ã­ntegra local `.tmp/ui-review/db.sqlite3`, migraÃ§Ãµes e `manage.py check` passaram. O escritÃ³rio local Fedrizzi e seu conector ODBC foram recriados sem sincronizaÃ§Ã£o de dados. A validaÃ§Ã£o ODBC leu 13.875 linhas por quatro consultas allowlisted, confirmou cinco objetos e zero colunas ausentes. A descoberta persistiu somente metadados: 500 objetos gerais, 49 de folha com prefixo `FOV` e 387 contÃ¡beis com prefixo `CT`; nÃ£o foram impressos dados de origem. NÃ£o havia backup `.dom` acessÃ­vel nas pastas locais verificadas, portanto a importaÃ§Ã£o DomÃ­nio Web real permanece pendente de um arquivo autorizado e sua chave correspondente.

## V-016 â€” Conector oficial DomÃ­nio / Onvio preparado

Data: 18/09/2026. A pesquisa oficial confirmou o contrato ERP DomÃ­nio v3 (ativaÃ§Ã£o, envio e consulta de lote XML) e o contrato Onvio BR Accounting v2 (OAuth por cÃ³digo, refresh token, lista paginada de clientes e estado da integraÃ§Ã£o). `apps.hub.dominio_api` implementa esses contratos sem credenciais embutidas e sem chamada externa durante o teste. Quatro testes automatizados aprovaram token, ativaÃ§Ã£o, `integrationKey`, multipart XML, consulta de lote, OAuth, paginaÃ§Ã£o de clientes e estado da integraÃ§Ã£o; Ruff e `manage.py check` passaram. A documentaÃ§Ã£o pÃºblica consultada nÃ£o descreve leitura de lanÃ§amentos, escrita fiscal ou folha do DomÃ­nio Web: essa capacidade somente poderÃ¡ ser adicionada se a Thomson Reuters entregar Swagger e escopos especÃ­ficos Ã  CICA.

## V-017 â€” ReinÃ­cio administrativo do agente instalado

Data: 18/09/2026. O serviÃ§o `CicaAgent` foi reiniciado com privilÃ©gio administrativo nesta estaÃ§Ã£o e retornou ao estado `Running`, mantendo inÃ­cio `Automatic`. Sem configuraÃ§Ã£o de rede, o serviÃ§o nÃ£o possui `agent.config` e permanece aguardando configuraÃ§Ã£o. Isso prova instalaÃ§Ã£o e reinÃ­cio local; nÃ£o prova pareamento, revogaÃ§Ã£o, atualizaÃ§Ã£o distribuÃ­da ou recuperaÃ§Ã£o de rede, que dependem do ambiente hospedado da etapa 12.

## V-018 â€” Limites comerciais da integraÃ§Ã£o DomÃ­nio Web documentados

Data: 18/09/2026. A referÃªncia [docs/dominio-web-limitacoes-comerciais.md](docs/dominio-web-limitacoes-comerciais.md) consolidou a linguagem comercial para API DomÃ­nio/Onvio, agente local e backup de contingÃªncia. Ela usa somente os contratos oficiais registrados em `docs/dominio-api-oficial.md` e aponta, de forma explÃ­cita, que OAuth, API oficial, pareamento pÃºblico e backup `.dom` real ainda nÃ£o foram homologados.

Limite: este registro documenta a promessa permitida; nÃ£o Ã© teste de backup e nÃ£o libera divulgaÃ§Ã£o, ambiente hospedado ou integraÃ§Ã£o externa.

## V-019 â€” PreparaÃ§Ã£o segura do backup DomÃ­nio Web

Data: 18/09/2026. O processador nativo passou a conferir SHA-256 antes de abrir o backup, baixar em arquivo temporÃ¡rio com troca atÃ´mica e aceitar URL de download somente do mesmo servidor CICA configurado. A extraÃ§Ã£o valida todos os caminhos antes de gravar qualquer entrada e recusa arquivo absoluto, nulo ou que saia da fila temporÃ¡ria. O envio continua paginado em 500 registros e nÃ£o possui os antigos limites silenciosos de leitura.

Conforme instruÃ§Ã£o do responsÃ¡vel, **nÃ£o foi executado teste, build ou validaÃ§Ã£o de backup nesta alteraÃ§Ã£o**. A comprovaÃ§Ã£o com arquivo `.dom` autorizado, chave, interrupÃ§Ã£o de rede, retomada e nÃ£o duplicaÃ§Ã£o permanece obrigatÃ³ria na etapa 12. Este marco Ã© somente implementaÃ§Ã£o preparada.

## V-020 â€” DiagnÃ³stico operacional local do agente preparado

Data: 18/09/2026. O serviÃ§o nativo passou a validar a configuraÃ§Ã£o antes de iniciar o ciclo e a escrever `C:\ProgramData\CICA\Agent\agent-status.json` por substituiÃ§Ã£o atÃ´mica. O arquivo informa somente estado, detalhe seguro, data UTC e versÃ£o; nÃ£o registra senha, certificado, segredo, DSN ou dado do DomÃ­nio. Os estados previstos sÃ£o `awaiting_configuration`, `configuration_error`, `synchronizing`, `ready` e `temporary_error`. Falhas transitÃ³rias de HTTP ou tempo limite passam a esperar progressivamente de um a cinco minutos; uma falha ao gravar o diagnÃ³stico nÃ£o interrompe o serviÃ§o.

Conforme instruÃ§Ã£o vigente, **nÃ£o foram executados build, teste ou validaÃ§Ã£o do agente nesta alteraÃ§Ã£o**. A inspeÃ§Ã£o do arquivo, a recuperaÃ§Ã£o apÃ³s indisponibilidade de rede e a validaÃ§Ã£o de instalaÃ§Ã£o limpa continuam obrigatÃ³rias na etapa 12. Este marco Ã© somente implementaÃ§Ã£o preparada.

## V-021 â€” RenovaÃ§Ã£o local de certificado do agente preparada

Data: 18/09/2026. O agente nativo passou a inspecionar o vencimento do certificado protegido no PFX local. Com menos de 30 dias para expirar, depois de concluir um ciclo jÃ¡ autenticado, ele cria um CSR com a chave privada existente, chama a rota jÃ¡ exposta `api/agent/v2/certificate/renew` e substitui de forma protegida somente o certificado local. O endpoint pode recusar o agente revogado; nesse caso o estado local passa a `authorization_error` e a configuraÃ§Ã£o nÃ£o Ã© apagada automaticamente. A chave privada nÃ£o Ã© enviada ao servidor.

Conforme instruÃ§Ã£o vigente, **nÃ£o foram executados build, teste ou validaÃ§Ã£o do agente nesta alteraÃ§Ã£o**. A renovaÃ§Ã£o real depende de HTTPS publicado, proxy com mTLS, CA configurada e um agente pareado; todos sÃ£o itens da etapa 12 por D-81. Este marco Ã© somente implementaÃ§Ã£o preparada.

## V-022 â€” Versionamento e aviso de atualizaÃ§Ã£o do agente preparados

Data: 18/09/2026. `agent-windows/build.ps1` passou a receber uma versÃ£o explÃ­cita e a propagÃ¡-la para serviÃ§o, configurador e MSI, por exemplo `./build.ps1 -Version 1.2.3`. O artefato inclui `release.json` com versÃ£o, nome e SHA-256, alÃ©m do checksum separado. O heartbeat compara a versÃ£o instalada com a versÃ£o devolvida pelo servidor e registra `update_available` no diagnÃ³stico local quando houver uma mais nova. O agente nÃ£o baixa, nÃ£o executa e nÃ£o instala MSI automaticamente; a publicaÃ§Ã£o do pacote, assinatura, URL, checksum e atualizaÃ§Ã£o em estaÃ§Ã£o real permanecem para a etapa 12.

Conforme instruÃ§Ã£o vigente, **nÃ£o foram executados build, teste ou validaÃ§Ã£o do agente nesta alteraÃ§Ã£o**. Este marco Ã© somente implementaÃ§Ã£o preparada.

## V-023 â€” Comando de diagnÃ³stico local preparado

Data: 18/09/2026. Foi incluÃ­do `agent-windows/diagnosticar.ps1` para suporte tÃ©cnico local. O comando inspeciona a instalaÃ§Ã£o do serviÃ§o e configurador, presenÃ§a da configuraÃ§Ã£o protegida, estado seguro escrito pelo runtime, quantidade de DSNs de sistema e presenÃ§a de driver SQL Anywhere. Ele nÃ£o abre `agent.config`, nÃ£o tenta conexÃ£o, nÃ£o consulta dados DomÃ­nio e nÃ£o imprime nomes de DSN, senhas, certificados ou segredos. Retorna cÃ³digo 2 para instalaÃ§Ã£o incompleta e 3 para estado de configuraÃ§Ã£o/autorizaÃ§Ã£o que exige correÃ§Ã£o.

Conforme instruÃ§Ã£o vigente, **nÃ£o foram executados build, teste ou validaÃ§Ã£o do agente nesta alteraÃ§Ã£o**. A execuÃ§Ã£o no computador do escritÃ³rio, os cenÃ¡rios x86/x64, rede indisponÃ­vel, revogaÃ§Ã£o e atualizaÃ§Ã£o real continuam obrigatÃ³rios na etapa 12. Este marco Ã© somente implementaÃ§Ã£o preparada.

## V-024 â€” Compatibilidade ODBC x64 do configurador preparada

Data: 18/09/2026. A inspeÃ§Ã£o local encontrou ao menos um DSN de sistema e dois drivers SQL Anywhere em cada arquitetura, sem registrar seus nomes ou qualquer dado da conexÃ£o. Como o serviÃ§o CICA Agent instalado Ã© x64, o configurador passou a listar somente DSNs e drivers SQL Anywhere de 64 bits. Quando nÃ£o houver um DSN compatÃ­vel, ele desativa o teste de conexÃ£o e informa a aÃ§Ã£o necessÃ¡ria. Isso impede configurar uma fonte 32 bits que o processo x64 nÃ£o poderia abrir.

UI/UX Pro Max foi consultado para validaÃ§Ã£o junto Ã  escolha da fonte: a correÃ§Ã£o usa erro no prÃ³prio ponto da escolha e nÃ£o depende de falha no envio. Watermelon UI nÃ£o esteve disponÃ­vel nesta sessÃ£o. As diretrizes Web Interface Guidelines foram consultadas; sÃ£o voltadas a HTML e nÃ£o possuem violaÃ§Ã£o aplicÃ¡vel ao controle nativo WinForms alterado. NÃ£o foi possÃ­vel usar Playwright porque o configurador Ã© um aplicativo Windows nÃ£o navegÃ¡vel.

Conforme instruÃ§Ã£o vigente, **nÃ£o foram executados build, teste ou validaÃ§Ã£o do agente nesta alteraÃ§Ã£o**. A execuÃ§Ã£o visual e funcional do configurador, inclusive teclado, foco e a conexÃ£o ODBC real, continua obrigatÃ³ria na etapa 12. Este marco Ã© somente implementaÃ§Ã£o preparada.
## V-025 â€” Destino Windows configurÃ¡vel por escritÃ³rio preparado

Data: 18/09/2026. A configuraÃ§Ã£o de Triagem passou a salvar, por escritÃ³rio, a raiz Windows e um formato de subpastas. O formato aceita apenas `{company_name}`, `{dominio_code}`, `{document_type}` e `{period}`; exige empresa ou cÃ³digo DomÃ­nio, bloqueia caminho absoluto, subida de diretÃ³rio e caracteres invÃ¡lidos do Windows. Cada fila recebe o caminho relativo jÃ¡ resolvido, entÃ£o mudanÃ§as futuras nÃ£o alteram documentos que jÃ¡ estÃ£o em processamento. A raiz Ã© restrita a caminho local absoluto nesta fase: serviÃ§os Windows nÃ£o devem depender de unidade mapeada; UNC sÃ³ serÃ¡ liberado depois de conta de serviÃ§o e permissÃ£o homologadas.

ReferÃªncia tÃ©cnica: [Microsoft Learn â€” Services and Redirected Drives](https://learn.microsoft.com/en-us/windows/win32/services/services-and-redirected-drives). UI/UX Pro Max orientou validaÃ§Ã£o no prÃ³prio campo da configuraÃ§Ã£o. Watermelon UI nÃ£o estava disponÃ­vel nesta sessÃ£o. As Web Interface Guidelines foram revisadas; o formulÃ¡rio usa rÃ³tulos, erro junto ao campo e resumo focÃ¡vel. NÃ£o foi possÃ­vel usar Playwright: esta sessÃ£o nÃ£o dispÃµe de navegador ou pÃ¡gina CICA aberta.

Conforme instruÃ§Ã£o vigente, **nÃ£o foram executados testes, build ou validaÃ§Ã£o de escrita Windows nesta alteraÃ§Ã£o**. A confirmaÃ§Ã£o pelo agente, permissÃµes na raiz e recuperaÃ§Ã£o de indisponibilidade permanecem obrigatÃ³rias antes da liberaÃ§Ã£o comercial.
## V-026 â€” SincronizaÃ§Ã£o da raiz Windows a partir da CICA preparada

Data: 18/09/2026. A API v2 recebeu `configuration/next`, autenticada pelo agente e isolada por organizaÃ§Ã£o. Ela devolve somente a raiz do `DestinationProfile` do escritÃ³rio do agente; quando o destino nÃ£o for Windows, devolve vazio. O agente consulta essa configuraÃ§Ã£o apÃ³s o heartbeat, valida a raiz local, salva a cÃ³pia protegida por DPAPI e usa a alteraÃ§Ã£o no prÃ³prio ciclo. UNC e unidades mapeadas sÃ£o recusados nesta fase; a conta `LocalSystem` nÃ£o deve depender de unidades mapeadas para acesso a arquivos.

Conforme instruÃ§Ã£o vigente, **nÃ£o foram executados testes, build ou escrita Windows real nesta alteraÃ§Ã£o**. Pareamento HTTPS, validaÃ§Ã£o da raiz pelo agente instalado, permissÃµes e recuperaÃ§Ã£o de falha de rede seguem para a etapa de homologaÃ§Ã£o final.
## V-027 â€” SincronizaÃ§Ã£o nativa de extratos DomÃ­nio preparada

Data: 18/09/2026. O agente nativo passou a enviar extratos bancÃ¡rios pela rota v2, em pÃ¡ginas de atÃ© 500 registros e com chave externa composta do DomÃ­nio. A API aceita somente pÃ¡ginas limitadas, autenticadas e pertencentes ao escritÃ³rio do agente, usando o espelho normalizado jÃ¡ existente. NÃ£o hÃ¡ SQL remoto nem escrita no banco DomÃ­nio.

Conforme instruÃ§Ã£o vigente, **nÃ£o foram executados build, testes ou sincronizaÃ§Ã£o contra dados reais nesta alteraÃ§Ã£o**. A prova de paginaÃ§Ã£o, vÃ­nculo de lanÃ§amento, retomada e nÃ£o duplicaÃ§Ã£o permanece na homologaÃ§Ã£o final.

## V-028 â€” OrganizaÃ§Ã£o das dependÃªncias de produÃ§Ã£o

Data: 18/09/2026. Por D-87, as etapas 01â€“11 ficam limitadas a implementaÃ§Ã£o, configuraÃ§Ã£o sem segredos, testes locais/isolados e documentaÃ§Ã£o. Deploy, domÃ­nio/HTTPS/DNS, credenciais externas de produÃ§Ã£o, chamadas reais, pilotos e homologaÃ§Ã£o comercial foram centralizados na etapa 12. Nenhum deploy, serviÃ§o hospedado, chamada externa real ou validaÃ§Ã£o foi executado neste registro.

## V-029 â€” Descoberta local Siescon

Data: 18/09/2026. A inspeÃ§Ã£o segura de metadados desta estaÃ§Ã£o encontrou 26 drivers ODBC e 5 DSNs. HÃ¡ drivers SQL Anywhere 16/17 nas arquiteturas 32 e 64 bits, mas nenhum DSN, driver ou diretÃ³rio de instalaÃ§Ã£o identificado como Siescon. NÃ£o houve conexÃ£o, listagem de bancos/tabelas, leitura de dados ou exposiÃ§Ã£o de DSN/credencial. Resultado: o servidor/banco disponÃ­vel em D-53 nÃ£o estÃ¡ configurado localmente; versÃ£o, mecanismo autorizado e layout de Q-33 seguem necessÃ¡rios antes de programar um adaptador.

## V-030 â€” Base segura de exportaÃ§Ã£o por destino

Data: 18/09/2026. Por D-88, `AccountingExport` passou a registrar o destino (`dominio` ou `siescon`) e o adaptador selecionado passou a ser explÃ­cito e versionado. O adaptador DomÃ­nio existente foi preservado. Siescon nÃ£o possui adaptador registrado: a solicitaÃ§Ã£o Ã© recusada antes de consultar lanÃ§amentos ou gerar arquivo. A fonte Siescon tambÃ©m foi incluÃ­da no modelo de fontes, inicialmente sem configuraÃ§Ã£o. Foram aprovados `36` testes em `tests/test_reconciliation_module.py` (27,19 s); `makemigrations --check --dry-run` nÃ£o detectou alteraÃ§Ãµes e Ruff passou nos arquivos alterados. NÃ£o houve conexÃ£o Siescon, arquivo de exportaÃ§Ã£o Siescon, leitura externa ou homologaÃ§Ã£o.

## V-141 ? Configuracao inicial retomavel

23/09/2026. O assistente mostra oito etapas persistidas e leva owner/admin para a superficie concreta de cada pendencia, inclusive fonte, empresas, modelos, equipe, limites e MFA. A validacao focalizada do workspace passou com 72 testes; a regressao completa passou com 864 testes, 2 ignorados e 11 subtestes em 79,74 s. Watermelon nao retornou referencias para onboarding/checklist; inspiracao adotada: etapas resumidas, proxima acao explicita e retomada pelo estado salvo. A validacao Playwright permanece indisponivel nesta maquina por transporte encerrado; nao houve inspecao visual automatizada.


## V-142 â€” Roteiro operacional do responsÃ¡vel

Data: 23/09/2026. Foi criado `docs/planejamento/roteiro-do-responsavel-para-liberacao.md`, ligado ao manual de homologaÃ§Ã£o externa. Ele consolida os materiais, decisÃµes, responsÃ¡veis, testes de aceite e sequÃªncia necessÃ¡ria para DomÃ­nio Local/Web, NFS-e, Siescon, Serpro, e-mail/OAuth, folha, relatÃ³rios, caixa/reforma, comercial/Asaas e piloto. A revisÃ£o conferiu as dependÃªncias abertas Q-08, Q-09, Q-11 a Q-25, Q-29, Q-33 a Q-36, Q-38 e Q-39 e atualizou a orientaÃ§Ã£o de OAuth com fontes oficiais Google e Microsoft. Esta Ã© documentaÃ§Ã£o de transiÃ§Ã£o: nenhuma credencial, backup, contrato, chamada externa, cobranÃ§a, publicaÃ§Ã£o, dado de cliente ou homologaÃ§Ã£o foi executado; portanto nÃ£o hÃ¡ nova prova funcional a registrar.

## V-143 â€” Carteira explÃ­cita e prioridade por prazo efetivo

24/09/2026. D-123 remove o fallback que concedia todas as empresas a colaborador sem atribuiÃ§Ãµes ou apÃ³s revogar a Ãºltima. Membro/escritÃ³rio inativo e empresa inativa nÃ£o recebem capacidades. Owner/admin mantÃ©m carteira total local; controle externo conserva validade e escopo. D-124 alinha a ordenaÃ§Ã£o da prÃ©via e fila ao prazo interno, ou legal quando interno ausente, deixando sem prazo ao final. Testes cobrem revogaÃ§Ã£o da Ãºltima atribuiÃ§Ã£o, acesso direto recusado, administrador com atribuiÃ§Ã£o parcial, inatividade e obrigaÃ§Ã£o legal atrasada antes de prazo interno futuro. Fixtures DTE/Parcelamentos receberam atribuiÃ§Ãµes explÃ­citas; testes de ciÃªncia preservam a recusa ao auditor e refletem D-109 para colaborador atribuÃ­do.

ValidaÃ§Ã£o: suÃ­te integral `uv run pytest -q --tb=short`: 869 aprovados, 2 ignorados, 15 subtestes, 77,61 s. Ruff passou nos cinco arquivos Python envolvidos; MyPy passou em controlplane/views; Django check e makemigrations --check --dry-run com settings de teste passaram. Os skips continuam sendo navegador Python opcional e concorrÃªncia de locks que exige PostgreSQL. Playwright MCP retornou Transport closed ao listar abas; nenhuma aba foi aberta e nÃ£o hÃ¡ nova prova visual. NÃ£o houve alteraÃ§Ã£o de template, chamada paga, produÃ§Ã£o, integraÃ§Ã£o real ou atribuiÃ§Ã£o criada no banco operacional. Agenda pessoal, fechamentos agregados, recorrÃªncia automÃ¡tica e ligaÃ§Ã£o dos mÃ³dulos permanecem em implementaÃ§Ã£o.

## V-144 â€” VisÃ£o geral com agenda pessoal e recortes explÃ­citos

24/09/2026. D-125 implementado: Meu trabalho Ã© a entrada padrÃ£o para todos os perfis e contÃ©m somente atividades atribuÃ­das Ã  pessoa dentro da carteira autorizada. Carteira expÃµe trabalho compartilhado; GestÃ£o exige owner/admin e concentra a distribuiÃ§Ã£o de equipe. Indicadores abrem o mesmo recorte com filtro na URL; a agenda contÃ©m somente atividades abertas, agrupadas por prazo efetivo (atrasadas, hoje, prÃ³ximos sete dias, posteriores e sem prazo), com 30 por pÃ¡gina e responsÃ¡vel visÃ­vel. MÃ©tricas genÃ©ricas e filas de mÃ³dulos saÃ­ram do recorte pessoal. O vazio explica que ausÃªncia de atividade nÃ£o comprova fechamento.

Testes: 89 focados e 4 subtestes passaram; regressÃ£o integral com 871 aprovados, 2 ignorados e 15 subtestes em 80,16 s. Ruff, MyPy, Django check e migraÃ§Ãµes passaram. Uma indicaÃ§Ã£o aria-current foi acrescentada aos filtros apÃ³s iniciar a regressÃ£o e recebeu revalidaÃ§Ã£o focal posterior. Testes novos cobrem agenda do administrador, carteira do operador sem acesso a outra empresa, tarefa sem responsÃ¡vel fora da agenda pessoal, gestÃ£o proibida a colaborador, 31 tarefas paginadas e filtro diÃ¡rio excluindo concluÃ­das/atrasadas.

UI/UX Pro Max consultado para produto de produtividade. Watermelon portfolio-dashboard e documentaÃ§Ã£o pÃºblica Karbon orientaram responsabilidade pessoal e agrupamento; Refero nÃ£o expÃ´s telas e SaaSFrame foi consultado apenas no catÃ¡logo pÃºblico. Web Interface Guidelines atuais revisadas no template e CSS: navegaÃ§Ã£o por links com estado na URL, foco explÃ­cito, alvos de 44 px, estado vazio contextual, tokens existentes e quebra mÃ³vel. Playwright MCP retornou Transport closed antes de abrir aba: renderizaÃ§Ã£o, teclado e console em desktop/mobile permanecem sem validaÃ§Ã£o nova. Sem publicaÃ§Ã£o, custo ou dados reais. Fechamentos agregados, recorrÃªncia e conexÃ£o de mÃ³dulos ainda nÃ£o estÃ£o concluÃ­dos.

## V-145 â€” GeraÃ§Ã£o recorrente mensal com retomada

24/09/2026. Implementado D-126 em recurrence.py, tarefa Celery hub.generate_recurring_activities e Beat horÃ¡rio. Migration aditiva 0054 guarda prÃ³xima competÃªncia por atribuiÃ§Ã£o; geraÃ§Ã£o e cursor sÃ£o transacionais. Primeira execuÃ§Ã£o parte do mÃªs corrente; interrupÃ§Ã£o posterior retoma meses pendentes em lotes de atÃ© 12. Pausa/reativaÃ§Ã£o administrativa reinicia cursor no mÃªs corrente. ResponsÃ¡vel sem acesso ativo gera tarefa sem responsÃ¡vel com evento explÃ­cito; empresas/escritÃ³rios inativos, demo, lifecycle bloqueado, controle externo vencido e NFS-e exclusivo nÃ£o geram tarefas. Uma falha mantÃ©m cursor e registra somente classe tÃ©cnica/ID, permitindo avanÃ§ar outras atribuiÃ§Ãµes. Nenhum autor humano Ã© simulado e nenhum processamento/obrigaÃ§Ã£o Ã© marcado como concluÃ­do.

ValidaÃ§Ã£o: 22 testes focados com 8 subtestes na primeira execuÃ§Ã£o; apÃ³s acrescentar teste da aÃ§Ã£o administrativa de pausa/retomada, regressÃ£o integral de 878 aprovados, 2 ignorados e 19 subtestes em 79,67 s. Ruff nos arquivos envolvidos, MyPy em recurrence/operations/tasks/views, Django check e makemigrations --check --dry-run passaram. Os testes exercitam repetiÃ§Ã£o, virada de ano, recuperaÃ§Ã£o de competÃªncias, rollback, falha isolada, revogaÃ§Ã£o de carteira, limite de 12 e exclusÃµes. Migration aplicada somente em banco de testes; nÃ£o houve execuÃ§Ã£o em base operacional, worker publicado ou chamada externa. Bloqueio concorrente PostgreSQL e queda real de worker/Beat permanecem homologaÃ§Ãµes obrigatÃ³rias; operaÃ§Ã£o/recuperaÃ§Ã£o registradas no manual externo. NÃ£o houve mudanÃ§a visual nesta entrega.

## V-146 â€” RevalidaÃ§Ã£o da comprovaÃ§Ã£o de fechamento

24/09/2026. D-127 implementado em operations.py: complete_activity e assess_closing compartilham os requisitos de evidÃªncia, processamento obrigatÃ³rio fechado, obrigaÃ§Ã£o obrigatÃ³ria aceita e atualizaÃ§Ã£o da fonte. Estado concluÃ­do isolado nÃ£o comprova fechamento. Documento sozinho nÃ£o substitui confirmaÃ§Ã£o humana em source_or_human; dispensa exige motivo, responsÃ¡vel, data e evidÃªncia, sem exigir execuÃ§Ã£o da obrigaÃ§Ã£o dispensada. Pagamento permanece independente. AvaliaÃ§Ã£o retorna causas por atividade e nÃ£o altera histÃ³rico.

ValidaÃ§Ã£o: 19 testes focados e 6 subtestes; regressÃ£o integral com 881 aprovados, 2 ignorados e 21 subtestes em 84,29 s. Ruff, MyPy de operations.py, Django check e makemigrations --check --dry-run passaram. Novos cenÃ¡rios verificam conclusÃ£o sem evidÃªncia, processamento ausente, obrigaÃ§Ã£o somente transmitida, reabertura, fonte nÃ£o configurada/desatualizada/indisponÃ­vel, documento sem confirmaÃ§Ã£o, dispensa e pagamento separado. Os skips permanecem navegador Python opcional e concorrÃªncia PostgreSQL. Nenhum template foi alterado, nenhuma fonte externa consultada e nenhuma nova validaÃ§Ã£o visual realizada. Fechamentos agregados ainda nÃ£o foram ligados Ã  agenda: a entrega corrige a regra de domÃ­nio antes de sua exposiÃ§Ã£o; a meta permanece ativa.

## V-147 â€” Requisitos de fechamento expostos na agenda

24/09/2026. D-128 implementado: closing_dashboard.py agrega empresas autorizadas (10 por pÃ¡gina), competÃªncia selecionÃ¡vel e Ã¡reas contÃ¡bil/fiscal/folha. Resumo inclui todos os responsÃ¡veis, sem ampliar a carteira. Somente atividades com processamento fechado ou obrigaÃ§Ã£o aceita exigidos entram no conjunto; pagamento isolado nÃ£o bloqueia. Estados e causas usam assess_closing; detalhes mostram responsÃ¡vel, prazo, atualizaÃ§Ã£o e quantidade de evidÃªncias, com acesso ao histÃ³rico. Sem requisito cadastrado nÃ£o significa concluÃ­do. NavegaÃ§Ã£o preserva competÃªncia e recortes. NFS-e exclusivo mantÃ©m redirecionamento prÃ©vio.

ValidaÃ§Ã£o: 22 focados e 6 subtestes; suÃ­te integral de 884 aprovados, 2 ignorados e 21 subtestes em 83,77 s. Ruff, MyPy, Django check e ausÃªncia de migraÃ§Ãµes pendentes passaram. Casos novos: tarefa de outro responsÃ¡vel visÃ­vel no fechamento e fora da agenda pessoal, empresa proibida omitida, pagamento independente, evidÃªncia vÃ¡lida, competÃªncia sem registros, entrada invÃ¡lida e segunda pÃ¡gina administrativa sem ampliaÃ§Ã£o da carteira de colaborador.

UI/UX Pro Max e Watermelon consultados; limitaÃ§Ãµes das referÃªncias e auditoria das guidelines atuais registradas na etapa 11. Playwright MCP retornou Transport closed em listagem e fechamento, sem abrir sessÃ£o; nÃ£o se alega validaÃ§Ã£o renderizada de desktop/mobile, foco ou console. Nenhuma integraÃ§Ã£o externa, custo ou publicaÃ§Ã£o. Ainda faltam alimentaÃ§Ã£o dos estados pelos mÃ³dulos, homologaÃ§Ã£o da cobertura dos modelos e prova visual; o rÃ³tulo Requisitos comprovados nÃ£o afirma completude legal da empresa. Meta permanece ativa.

## V-148 â€” RevisÃµes NFS-e alimentam atividades transacionalmente

24/09/2026. D-129 implementado com vÃ­nculo Ãºnico source_nfse_review (migration aditiva 0055), ponte module_activities.py e chamadas na captura/repetiÃ§Ã£o e decisÃ£o. RevisÃ£o aberta gera atividade fiscal sem responsÃ¡vel/prazo inventados; a conclusÃ£o humana registra evidÃªncia e autor/data da decisÃ£o, mantendo processamento apenas Processado e obrigaÃ§Ã£o NÃ£o aplicÃ¡vel. A conclusÃ£o independente Ã© recusada enquanto o caso estÃ¡ aberto. Caso, histÃ³rico do acumulador, artefato e atividade passam a integrar uma transaÃ§Ã£o com bloqueio do caso. RepetiÃ§Ã£o nÃ£o duplica registros; revisÃ£o aberta reavalia conclusÃ£o anterior. CompetÃªncia usa a emissÃ£o original, inclusive virada de mÃªs. Comando sync_nfse_activities recupera casos locais de escritÃ³rio explÃ­cito, sem provedores.

ValidaÃ§Ã£o: 29 focados e 6 subtestes antes do cenÃ¡rio de recuperaÃ§Ã£o; suÃ­te final com 889 aprovados, 2 ignorados e 21 subtestes em 85,95 s. Ruff passou nos arquivos envolvidos; MyPy em ponte/comando/operations/services/views, Django check e makemigrations --check --dry-run passaram. Testes percorrem captura â†’ POST real de decisÃ£o â†’ atividade/evidÃªncia/artefato, repetiÃ§Ã£o, rollback por falha da ponte, resoluÃ§Ã£o invÃ¡lida, reavaliaÃ§Ã£o, demonstraÃ§Ã£o e comando de recuperaÃ§Ã£o. A Ãºnica alteraÃ§Ã£o durante a regressÃ£o foi anotaÃ§Ã£o cast no comando, sem mudanÃ§a de execuÃ§Ã£o. Migration somente no banco de testes; nÃ£o houve comando de recuperaÃ§Ã£o em banco operacional, provedor, custo ou publicaÃ§Ã£o. ConcorrÃªncia PostgreSQL e interface renderizada continuam sem prova. NavegaÃ§Ã£o direta ao caso e demais mÃ³dulos seguem pendentes; esta entrega nÃ£o Ã© homologaÃ§Ã£o da importaÃ§Ã£o DomÃ­nio.

## V-149 â€” Triagem projeta o estado de arquivamento

24/09/2026. D-130 implementado com source_triage_item Ãºnico (migration 0056) e sync_triage_activity. TransiÃ§Ãµes humanas, antimalware e agente atualizam a projeÃ§Ã£o na transaÃ§Ã£o de origem. Sem empresa/demonstraÃ§Ã£o nÃ£o hÃ¡ atividade; vÃ­nculo de outra empresa Ã© recusado. AprovaÃ§Ã£o fica pendente; falha/rejeiÃ§Ã£o ou estado arquivado sem comprovaÃ§Ã£o impedem a atividade. Arquivamento exige data, destino e hash igual ao conteÃºdo; evidencia confirmaÃ§Ã£o persistida pelo mÃ³dulo, nÃ£o existÃªncia atual da cÃ³pia nem fechamento de ERP. RepetiÃ§Ã£o nÃ£o duplica evidÃªncias/eventos e comando sync_triage_activities recompÃµe registros por escritÃ³rio.

ValidaÃ§Ã£o: 33 focados passaram, incluindo teste do protocolo Windows existente estendido para conferir atividade/evidÃªncia apÃ³s retorno vÃ¡lido. RegressÃ£o completa: 891 aprovados, 2 ignorados e 21 subtestes em 81,64 s. ApÃ³s essa regressÃ£o, a verificaÃ§Ã£o ampliada de tipos identificou acesso anterior a socket.AF_UNIX incompatÃ­vel em plataforma sem suporte; substituÃ­do por detecÃ§Ã£o explÃ­cita que mantÃ©m ScannerUnavailable e orienta porta local, sem chamada externa. RevalidaÃ§Ã£o final de 17 testes de ponte/ingestÃ£o passou em 26,97 s, incluindo ausÃªncia de AF_UNIX. Ruff de todos os arquivos envolvidos e MyPy de seis serviÃ§os/comando passaram; Django check e ausÃªncia de novas migraÃ§Ãµes pendentes verificados antes da correÃ§Ã£o de socket, que nÃ£o altera modelos.

Sem mudanÃ§a de template, nova validaÃ§Ã£o visual, agente real, armazenamento operacional ou provedor. Migration executada sÃ³ em banco de testes. ConcorrÃªncia PostgreSQL, identificaÃ§Ã£o/reatribuiÃ§Ã£o de documentos, navegaÃ§Ã£o ao mÃ³dulo e demais pontes continuam abertas. NÃ£o hÃ¡ evidÃªncia de jornada externa homologada.

## V-150 â€” AÃ§Ã£o contextual e restriÃ§Ã£o de escrita por perfil

24/09/2026. D-131: detalhe da atividade vinculada apresenta estado e link para revisÃ£o NFS-e/arquivo da Triagem, condiciona link Ã  permissÃ£o de mÃ³dulo e deixa decisÃµes na origem. VÃ­nculo divergente nÃ£o gera link. Mensagem sem observaÃ§Ãµes externas nÃ£o contradiz evidÃªncias locais. FormulÃ¡rios genÃ©ricos continuam nas atividades independentes; perfil consultivo nÃ£o recebe aÃ§Ãµes de escrita. Corrigida falha em can_operate_activity que permitia auditor/financeiro nos serviÃ§os: agora exige perfil de alteraÃ§Ã£o e carteira atual via company_queryset_for_membership. Consulta usa escopo autorizado independentemente da permissÃ£o de alteraÃ§Ã£o; endpoints tambÃ©m recusam suporte somente leitura.

ValidaÃ§Ã£o: 31 focados e 8 subtestes; regressÃ£o integral 893 aprovados, 2 ignorados e 23 subtestes em 80,74 s. Testes percorrem detalhe â†’ revisÃ£o NFS-e, verificam link da Triagem e ausÃªncia de conclusÃ£o genÃ©rica; auditor/financeiro consultam, mas POSTs diretos de evidÃªncia/impedimento/conclusÃ£o nÃ£o gravam eventos nem alteram tarefa. Ruff, MyPy de views/operations, Django check e migraÃ§Ãµes passaram.

UI/UX Pro Max, Watermelon e Web Interface Guidelines atuais consultados; fontes/limitaÃ§Ãµes e auditoria registradas na etapa 11. Playwright MCP retornou Transport closed em listagem e fechamento; nenhuma sessÃ£o aberta nem nova prova visual. Sem integraÃ§Ã£o externa, custo ou publicaÃ§Ã£o. AtribuiÃ§Ã£o de atividades avulsas/de mÃ³dulo, demais pontes, observaÃ§Ãµes homologadas e validaÃ§Ã£o visual continuam pendentes. Meta permanece ativa.

## V-151 â€” AtribuiÃ§Ã£o e redistribuiÃ§Ã£o com histÃ³rico

24/09/2026. D-132 implementado: detalhe recebe formulÃ¡rio de responsÃ¡vel para proprietÃ¡rio/admin e serviÃ§o assign_activity transacional. DestinatÃ¡rio exige usuÃ¡rio/membro ativos, perfil operacional e carteira vigente; remoÃ§Ã£o deixa tarefa compartilhada. NÃ£o muda permissÃµes/modelos/prazos. Motivo obrigatÃ³rio, evento com responsÃ¡vel anterior/novo e auditoria preservam a alteraÃ§Ã£o. ResponsÃ¡vel anterior esperado detecta envio desatualizado e tarefa encerrada recusa redistribuiÃ§Ã£o. Erros mantÃªm valores e resumo focÃ¡vel com links aos campos.

ValidaÃ§Ã£o: primeira rodada encontrou falha de template em tarefa sem responsÃ¡vel; corrigida no formulÃ¡rio e no resumo de fechamento. Segunda rodada: 33 aprovados e 8 subtestes. RegressÃ£o final com 895 aprovados, 2 ignorados, 23 subtestes em 83,14 s. Testes cobrem atribuiÃ§Ã£o â†’ Meu trabalho, remoÃ§Ã£o â†’ carteira, envio desatualizado, acesso revogado, perfil sem administraÃ§Ã£o, preservaÃ§Ã£o de valores e recusa em tarefa encerrada. Ruff, MyPy de forms/views/operations, Django check e migraÃ§Ãµes passaram. Durante a regressÃ£o foi removido aria-label anterior incorreto do campo de evidÃªncia; atributo final conferido separadamente em Django shell sem operaÃ§Ãµes de banco.

UI/UX Pro Max, Watermelon e guidelines consultados; auditoria/fontes na etapa 11. Playwright retornou Transport closed em listagem e fechamento; sem sessÃ£o aberta, sem prova visual de desktop/mobile/foco. Sem publicaÃ§Ã£o, custos ou dados reais. ConcorrÃªncia PostgreSQL, demais pontes, observaÃ§Ãµes oficiais e homologaÃ§Ã£o continuam pendentes; a meta permanece ativa.

## V-152 â€” Retornos temporais e evidÃªncia da observaÃ§Ã£o aplicada

24/09/2026. D-133 implementado em record_source_observation. Bloqueios da fonte e atividade serializam a aplicaÃ§Ã£o local; repetiÃ§Ã£o exata de conteÃºdo e instante devolve o registro existente. Processamento e obrigaÃ§Ã£o comparam seus prÃ³prios histÃ³ricos bem-sucedidos. Retorno anterior nÃ£o reabre atividade nem recua a fotografia; falha nÃ£o aplica valores. Empate conflitante mantÃ©m o valor e sinaliza desatualizaÃ§Ã£o, que nÃ£o Ã© removida apenas por retorno da outra dimensÃ£o. ObservaÃ§Ã£o efetivamente aplicada cria evidÃªncia com referÃªncia ao ID e data original, sem concluir trabalho. Autor pode ser de sistema; datas sem fuso e referÃªncias acima do limite sÃ£o recusadas.

ValidaÃ§Ã£o: primeira rodada encontrou erro de preparaÃ§Ã£o do teste, que salvava instÃ¢ncia antiga inteira depois da observaÃ§Ã£o; corrigido para salvar somente work_status. Uma regressÃ£o jÃ¡ em andamento ainda usou a versÃ£o antiga desse teste (896 aprovados, 1 falha). RegressÃ£o final concluÃ­da com 897 aprovados, 2 ignorados, 23 subtestes em 80,73 s. Ruff, MyPy de operations, Django check e migraÃ§Ãµes passaram. Novos cenÃ¡rios cobrem repetiÃ§Ã£o sem duplicar evidÃªncia/evento, reabertura/falha atrasadas, dimensÃµes independentes, conflito persistente e data sem fuso. Os skips permanecem navegador Python opcional e concorrÃªncia PostgreSQL.

NÃ£o houve mudanÃ§a de template, integraÃ§Ã£o real, provedor, custo ou publicaÃ§Ã£o. A rotina ainda exige ligaÃ§Ã£o aos adaptadores homologados; testes locais nÃ£o comprovam estados de DomÃ­nio/Siescon/Serpro. Demais pontes e validaÃ§Ã£o visual continuam pendentes.

## V-153 â€” Tratamento da ConciliaÃ§Ã£o alimenta a central

24/09/2026. D-134: vÃ­nculo Ãºnico de atividade por arquivo (migration 0057), sincronizaÃ§Ã£o em captura/repetiÃ§Ã£o, tÃ©rmino de processamento com lease vÃ¡lido, confirmaÃ§Ã£o/desfazimento, aprovaÃ§Ã£o de lanÃ§amento, revisÃ£o de movimento e retomada. Leitura processada Ã© separada de trabalho concluÃ­do. Todos os movimentos precisam de conciliaÃ§Ã£o integral com evidÃªncia, lanÃ§amento aprovado/exportado da revisÃ£o vigente ou exclusÃ£o explÃ­cita com autor/regra. Erro e arquivo sem movimentos nÃ£o comprovam conclusÃ£o. EvidÃªncias anteriores sobrevivem Ã  reabertura; resultado local nÃ£o confirma importaÃ§Ã£o no ERP. Comando sync_reconciliation_activities recompÃµe por escritÃ³rio sem leitura externa.

ValidaÃ§Ã£o: 55 testes focados passaram antes do reforÃ§o final de comprovaÃ§Ã£o. RegressÃ£o final: 898 aprovados, 2 ignorados, 23 subtestes em 83,41 s. Teste novo percorre arquivo â†’ processamento â†’ confirmaÃ§Ã£o â†’ recuperaÃ§Ã£o idempotente â†’ desfazimento; ampliado teste de lanÃ§amento aprovado para pendÃªncia do segundo movimento, exclusÃ£o explÃ­cita, conclusÃ£o e reabertura por revisÃ£o. Ruff, MyPy dos serviÃ§os/views/comando, Django check e verificaÃ§Ã£o de migrations passaram. Migration executada apenas no banco de testes. Skips continuam Playwright Python opcional e concorrÃªncia PostgreSQL.

Sem alteraÃ§Ã£o de templates ou nova inspeÃ§Ã£o visual, integraÃ§Ã£o externa, custo ou publicaÃ§Ã£o. Permanecem navegaÃ§Ã£o contextual da nova origem, concorrÃªncia/volume e demais pontes. Identificado gap anterior na reconfirmaÃ§Ã£o de uma relaÃ§Ã£o desfeita; necessita correÃ§Ã£o que preserve histÃ³rico. A meta permanece ativa e a jornada completa ainda nÃ£o estÃ¡ homologada.

## V-154 â€” ReconfirmaÃ§Ã£o e histÃ³rico preservado

24/09/2026. D-135: confirmaÃ§Ã£o apÃ³s desfazimento reutiliza a relaÃ§Ã£o, revalida capacidade/evidÃªncia e registra decisÃµes em ReconciliationDecision, com proteÃ§Ã£o ORM contra alteraÃ§Ã£o/exclusÃ£o. ConfirmaÃ§Ã£o, desfazimento e projeÃ§Ã£o da central sÃ£o transacionais. Desfazimento repetido nÃ£o cria registro; relaÃ§Ã£o confirmada recusa duplicaÃ§Ã£o. RelaÃ§Ã£o legada sem decisÃµes recebe fotografia explicitamente marcada, mantendo ausÃªncia de data quando desconhecida. Bloqueios de desfazimento seguem ordem movimento â†’ lanÃ§amento â†’ relaÃ§Ã£o. Migration 0058 apenas em testes; documentos/evidÃªncias nÃ£o foram copiados para logs genÃ©ricos.

ValidaÃ§Ã£o: 47 testes focados passaram antes da ampliaÃ§Ã£o para legado. RegressÃ£o final: 899 aprovados, 2 ignorados, 23 subtestes em 84,26 s. CenÃ¡rios percorrem conclusÃ£o, desfazimento, recusa de excesso, reconfirmaÃ§Ã£o, preservaÃ§Ã£o da evidÃªncia original e proteÃ§Ã£o do histÃ³rico, tanto em relaÃ§Ã£o nova quanto legada. ApÃ³s ajuste de tipagem no clean dos vÃ­nculos opcionais da atividade, 8 testes das pontes passaram em 26,52 s. Ruff, MyPy de models/reconciliation_service, Django check e migrations passaram; discrepÃ¢ncia inicial de Ã­ndice da migration foi corrigida antes do aceite. Skips continuam navegador Python opcional e locks PostgreSQL.

Sem nova tela, validaÃ§Ã£o visual, dados reais, custo ou publicaÃ§Ã£o. ExposiÃ§Ã£o visual das decisÃµes, navegaÃ§Ã£o contextual, concorrÃªncia PostgreSQL, demais pontes e homologaÃ§Ã£o externa continuam pendentes. A proteÃ§Ã£o ORM nÃ£o equivale a impedir alteraÃ§Ã£o por administrador do banco. Meta ativa.

## V-155 â€” Da atividade ao arquivo da ConciliaÃ§Ã£o

24/09/2026. D-136 implementado: detalhe direciona ao arquivo e estado da execuÃ§Ã£o, sem formulÃ¡rio genÃ©rico de conclusÃ£o. Destino valida UUID, escritÃ³rio e carteira, restringe processamentos/movimentos e preserva source_file na busca/paginaÃ§Ã£o. Aviso identifica empresa/arquivo e alcance dos indicadores gerais, com retorno Ã  atividade e saÃ­da explÃ­cita do filtro. MÃ³dulo desabilitado nÃ£o oferece link operacional.

Primeira rodada encontrou mÃ³dulo ausente no cenÃ¡rio de teste (56 passaram, 1 falhou); corrigida preparaÃ§Ã£o e checagem da disponibilidade no link. Segunda rodada: 57 testes de pontes/ConciliaÃ§Ã£o aprovados em 30,29 s. Depois de acrescentar movimentos de dois arquivos para verificar o recorte, 9 testes de pontes passaram em 27,12 s. Ruff, MyPy de views e Django check passaram. NÃ£o houve nova regressÃ£o integral nesta entrega; a Ãºltima integral Ã© V-154. Testes verificam percurso atividade â†’ origem, ausÃªncia da conclusÃ£o genÃ©rica, recorte de execuÃ§Ãµes/movimentos, busca mantendo arquivo e 404 para arquivo invÃ¡lido/de outro escritÃ³rio.

UI/UX Pro Max, Watermelon e guidelines atuais consultados; auditoria e referÃªncias/limites na etapa 11. Playwright retornou Transport closed em listagem e fechamento, sem sessÃ£o aberta ou prova visual. ExposiÃ§Ã£o das decisÃµes, validaÃ§Ã£o desktop/mobile, concorrÃªncia e demais pontes permanecem pendentes. Nenhuma chamada externa operacional, custo ou publicaÃ§Ã£o.

## V-156 â€” HistÃ³rico das decisÃµes acessÃ­vel no movimento

24/09/2026. D-137: decisÃµes paginadas de 20 em 20, restritas ao movimento/escritÃ³rio/empresa, com estado, valor, autor/data disponÃ­veis, legenda de legado e evidÃªncia escapada em expansÃ£o nativa. PÃ¡gina dos candidatos Ã© preservada na navegaÃ§Ã£o. Consulta nÃ£o altera decisÃµes. Auditoria encontrou formulÃ¡rios indevidos para perfil consultivo; agora a tela respeita a mesma condiÃ§Ã£o de escrita do servidor e mantÃ©m consulta dos dados/histÃ³rico.

ValidaÃ§Ã£o: primeira rodada de 57 testes passou em 32,05 s; apÃ³s corrigir apresentaÃ§Ã£o consultiva e adicionar verificaÃ§Ãµes de auditor, 57 testes passaram em 35,37 s. Testes percorrem origem â†’ movimento â†’ 21 decisÃµes em duas pÃ¡ginas, ausÃªncia explÃ­cita de autor/data, identificaÃ§Ã£o legada, escape de script, persistÃªncia da pÃ¡gina de candidatos, consulta de auditor sem aÃ§Ãµes e recusa do POST. Ruff, MyPy de views e Django check passaram. Ãšltima regressÃ£o integral permanece V-154.

UI/UX Pro Max, Watermelon e guidelines consultados; auditoria de cÃ³digo/referÃªncias na etapa 11. Playwright segue Transport closed, sem sessÃ£o aberta e sem inspeÃ§Ã£o renderizada. Sem chamada real ou publicaÃ§Ã£o. Demais pontes, concorrÃªncia PostgreSQL, volume e homologaÃ§Ãµes permanecem pendentes; objetivo ativo.

## V-157 â€” Entrada operacional para conferÃªncias de folha

24/09/2026. InspeÃ§Ã£o identificou que record_payroll_snapshot nÃ£o era chamado pela entrada de arquivos; a ficha comparava somente dados inseridos por outros meios. D-138 conecta CSV/XLSX ao fluxo existente de prÃ©via/confirmaÃ§Ã£o, com migration 0059, modelo CSV e instruÃ§Ãµes. Documentos informados preservam empresa/fonte/referÃªncia e campos ausentes. CompetÃªncia deve iniciar no dia 1 e pelo menos um total nÃ£o negativo Ã© obrigatÃ³rio. Lote usa savepoint: erro desfaz fotografias e auditoria daquele lote. Registro serializa pela empresa e rejeita conteÃºdo diferente sob referÃªncia existente; replay idÃªntico Ã© reutilizado.

ValidaÃ§Ã£o: 8 testes focados passaram inicialmente; depois do percurso web, 9 passaram em 26,13 s. RegressÃ£o integral final: 902 aprovados, 2 ignorados, 23 subtestes em 86,88 s. Testes cobrem upload â†’ prÃ©via sem gravaÃ§Ã£o â†’ confirmaÃ§Ã£o â†’ ficha, valores ausentes, replay, conflito que desfaz linha anterior e competÃªncia invÃ¡lida. Ruff, MyPy de imports/payroll/forms, Django check e migrations passaram. Migration aplicada sÃ³ no banco de testes; skips continuam navegador Python opcional e locks PostgreSQL.

UI/UX Pro Max/Watermelon/guidelines consultados, evidÃªncias na etapa 11. Playwright sem transporte em listagem/fechamento; sem nova prova visual. XLSX usa leitor existente, sem novo arquivo real homologado. PrÃ©via ainda mostra identificaÃ§Ã£o/contagem, sem conferÃªncia linha a linha; vÃ­nculo das fotografias/conferÃªncias Ã  central ainda pendente. Nenhuma transmissÃ£o, fechamento ERP, aceite governamental, custo ou publicaÃ§Ã£o alegado.

## V-158 â€” Recebimento da folha gera conferÃªncia na central

24/09/2026. D-139 e migration 0060: fotografia recebida passa a alimentar atividade Ãºnica por empresa/competÃªncia. VÃ­nculo aponta o cadastro mais recente; nÃ£o usa data de observaÃ§Ã£o antiga para ignorar documento recÃ©m-recebido. Replay preserva estado/histÃ³rico; nova fotografia reabre concluÃ­da/dispensada e exige evidÃªncia humana posterior ao evento de recebimento, com autor registrado. EvidÃªncias antigas continuam disponÃ­veis. NÃ£o inventa responsÃ¡vel/prazo nem marca processamento fechado ou obrigaÃ§Ã£o aceita. Comando sync_payroll_activities recompÃµe por escritÃ³rio, excluindo demonstraÃ§Ã£o e vÃ­nculos de empresa fora do escritÃ³rio.

ValidaÃ§Ã£o: 37 focados e 8 subtestes passaram em 29,30 s. ApÃ³s ampliar o teste web para conferir criaÃ§Ã£o/acesso da atividade, regressÃ£o integral: 903 aprovados, 2 ignorados, 23 subtestes em 81,97 s. CenÃ¡rios cobrem importaÃ§Ã£o â†’ ficha/atividade, revisÃ£o humana â†’ conclusÃ£o, replay sem reabertura, novos dados â†’ reabertura, recusa de evidÃªncia antiga, nova evidÃªncia â†’ conclusÃ£o e recomposiÃ§Ã£o idempotente. Ruff, MyPy dos serviÃ§os/modelos/comando, Django check e migrations passaram. Migration aplicada somente no banco de testes; skips continuam navegador Python opcional e locks PostgreSQL.

Nenhum template alterado nesta entrega, inspeÃ§Ã£o visual nova, integraÃ§Ã£o real, custo ou publicaÃ§Ã£o. Atalho contextual Ã  comparaÃ§Ã£o e prÃ©via detalhada continuam pendentes, assim como outras pontes, PostgreSQL e homologaÃ§Ã£o externa. Manual/checklist atualizados; objetivo ativo.

## V-159 â€” CompetÃªncia preservada entre atividade e comparaÃ§Ã£o

24/09/2026. D-140: atividade abre ficha/seletores restritos Ã  competÃªncia. Filtro explÃ­cito persiste na paginaÃ§Ã£o e comparaÃ§Ã£o; ficha oferece retorno Ã  atividade e remoÃ§Ã£o do filtro. NavegaÃ§Ã£o/comparaÃ§Ã£o nÃ£o conclui tarefa; evidÃªncia humana continua na atividade. Datas invÃ¡lidas e acesso sem carteira sÃ£o recusados.

106 testes focados e 8 subtestes passaram em 55,88 s. Percurso web cobre atividade â†’ ficha filtrada â†’ comparaÃ§Ã£o â†’ tarefa ainda pendente, exclusÃ£o de outro mÃªs, campo de competÃªncia preservado e recusa 404. Ruff, MyPy de views e Django check passaram; Ãºltima regressÃ£o integral V-158. Sem migration nova.

UI/UX Pro Max/Watermelon/guidelines atuais consultados; auditoria na etapa 11. Playwright sem transporte em listagem/fechamento, sem sessÃ£o aberta ou prova visual. PrÃ©via detalhada, outras pontes e homologaÃ§Ãµes continuam pendentes; meta ativa.

## V-160 â€” PrÃ©via da folha linha a linha

24/09/2026. D-141: prÃ©via mostra 20 linhas por pÃ¡gina com numeraÃ§Ã£o, empresa resolvida na fonte, competÃªncia/referÃªncia e totais originais. Campos ausentes e empresa desconhecida sÃ£o explÃ­citos. Consulta lÃª o payload protegido, sem gravar fotografia/atividade; somente administradores autorizados recebem os valores. ConfirmaÃ§Ã£o conserva validaÃ§Ã£o integral/rollback existentes; formulÃ¡rio de confirmaÃ§Ã£o tambÃ©m fica oculto no perfil consultivo.

80 testes focados passaram em 50,87 s. Novo teste cobre 21 linhas, segunda pÃ¡gina/linha 22, ausÃªncia de valor, empresa desconhecida, escape de script, nenhuma persistÃªncia e recusa de exposiÃ§Ã£o ao auditor. Ruff, MyPy de imports/views e Django check passaram. Ãšltima regressÃ£o integral permanece V-158.

UI/UX Pro Max/Watermelon/guidelines atuais consultados; auditoria na etapa 11. Playwright retornou Transport closed em listagem/fechamento; CUA alternativo retornou nenhum navegador/app habilitado. Nenhuma sessÃ£o aberta ou prova visual alegada. Fontes reais/XLSX, outras pontes e homologaÃ§Ãµes seguem pendentes; objetivo ativo.

## V-161 â€” Caixa Postal gera anÃ¡lise na central

24/09/2026. D-142 e migration 0061: mensagem persistida gera uma atividade de anÃ¡lise sem prazo legal presumido. Listagem repetida nÃ£o duplica atividade nem provoca ciÃªncia. Abertura comprovada acrescenta evidÃªncia de consulta, sem concluir anÃ¡lise; resultado incerto impede conclusÃ£o humana. Carteira vigente Ã© revalidada antes de consumo/chamada. ProjeÃ§Ã£o apÃ³s commit protege o recibo contra falha da central, recuperÃ¡vel por comando local.

RegressÃ£o final: `uv run pytest --tb=short`, 907 aprovados e 2 ignorados em 80,59 s. Teste de falha da projeÃ§Ã£o inicialmente revelou erro no callback parcial; corrigido com funÃ§Ã£o nomeada e cenÃ¡rio aprovado na regressÃ£o final. Cobertos recibo preservado, recomposiÃ§Ã£o, deduplicaÃ§Ã£o, ausÃªncia de carteira e resultado incerto. Ruff, MyPy de cinco arquivos, Django check e verificaÃ§Ã£o de migrations passaram. Migration aplicada apenas nos testes. Skips: navegador Python opcional e locks PostgreSQL.

Nenhuma alteraÃ§Ã£o de template, nova inspeÃ§Ã£o visual, consulta real, transmissÃ£o, custo ou publicaÃ§Ã£o. Atalho contextual DTE, demais pontes, PostgreSQL, volume e homologaÃ§Ã£o externa permanecem pendentes; meta ativa.

## V-162 â€” EvidÃªncia DTE deve acompanhar a abertura

24/09/2026. D-143 corrige conclusÃ£o com confirmaÃ§Ã£o humana anterior Ã  abertura. A exigÃªncia consulta diretamente o recibo, mesmo antes da projeÃ§Ã£o. Novo comprovante reabre concluÃ­da/dispensada sem anÃ¡lise posterior identificada; preserva evidÃªncias e exige nova confirmaÃ§Ã£o. RecomposiÃ§Ã£o mantÃ©m anÃ¡lise posterior vÃ¡lida. Recibo aberto sem data ou conteÃºdo nÃ£o permite concluir.

48 testes e 8 subtestes passaram em 27,31 s (`tests/test_dte_access.py`, `tests/test_dte_dispatch.py`, `tests/test_operational_center.py`). Novos cenÃ¡rios verificam recusa antes da projeÃ§Ã£o, conclusÃ£o/dispensa reaberta, nova anÃ¡lise, replay sem duplicaÃ§Ã£o, recuperaÃ§Ã£o com anÃ¡lise jÃ¡ posterior e comprovante sem conteÃºdo. Ruff, MyPy dos dois serviÃ§os e Django check passaram. Sem migration ou template novo; Ãºltima regressÃ£o integral V-161. Nenhuma validaÃ§Ã£o visual/externa ou chamada real. Meta ativa; navegaÃ§Ã£o contextual, demais pontes e homologaÃ§Ãµes continuam pendentes.

## V-163 â€” Ida e volta entre atividade e mensagem DTE

24/09/2026. D-144 implementado: atividade exibe link ao resumo autorizado e mantÃ©m registro humano; resumo retorna Ã  atividade da mesma empresa/escritÃ³rio. MÃ³dulo indisponÃ­vel tem orientaÃ§Ã£o explÃ­cita. GET nÃ£o provoca abertura, consumo ou conclusÃ£o.

Rodada conjunta DTE/workspace: 83 testes passaram e um falhou apenas na expectativa 404 versus 403 da recusa pelo mÃ³dulo. Corrigida a expectativa para o contrato existente e acrescentada ausÃªncia do assunto no retorno recusado. Rodada final DTE: 11 aprovados em 48,10 s. Ruff, MyPy de views e Django check passaram. Sem migration; regressÃ£o integral anterior V-161.

UI/UX Pro Max, Watermelon e guidelines atuais consultados; referÃªncias/auditoria na etapa 11. Playwright indisponÃ­vel (Transport closed em listagem e fechamento), sem sessÃ£o aberta ou prova visual. Desktop/mobile, teclado/console, demais pontes e homologaÃ§Ã£o continuam pendentes. Nenhuma chamada real, custo ou publicaÃ§Ã£o; meta ativa.

## V-164 â€” Radar gera anÃ¡lise por seleÃ§Ã£o humana

24/09/2026. D-145 e migration 0062: publicaÃ§Ã£o vinculada explicitamente a empresa autorizada, com justificativa e responsÃ¡vel. PÃ¡gina permite retomar anÃ¡lises da carteira, sem nova coleta. ServiÃ§o valida usuÃ¡rio, perfil operacional, empresa e mÃ³dulo. Coleta/reclassificaÃ§Ã£o atualiza somente vÃ­nculos existentes, conserva tÃ­tulo/URL/classificaÃ§Ã£o como evidÃªncia e reabre conclusÃ£o/dispensa apÃ³s mudanÃ§a. ConclusÃ£o exige versÃ£o vigente e evidÃªncia humana posterior. Comando sync_reform_activities recompÃµe por escritÃ³rio sem rede.

RegressÃ£o completa: 915 aprovados, 2 ignorados, 23 subtestes em 81,33 s. ApÃ³s corrigir a apresentaÃ§Ã£o de falha da coleta com sucesso anterior, 9 testes Radar passaram em 26,27 s. CenÃ¡rios cobrem percurso web, justificativa invÃ¡lida, idempotÃªncia, ausÃªncia de efeito em GET, recusa consultiva/cross-office, reabertura, prova antiga insuficiente, recuperaÃ§Ã£o sem rede e coleta sem tarefas para empresas nÃ£o vinculadas. Ruff, MyPy de seis arquivos, Django check, migrations e node --check do novo script passaram. Migration aplicada somente no banco de testes.

UI/UX Pro Max, Watermelon e guidelines consultados; auditoria na etapa 11. Playwright sem transporte em listagem/fechamento; nenhum navegador aberto ou validaÃ§Ã£o visual alegada. Skips continuam navegador Python opcional e locks PostgreSQL. Volume, fontes reais, desempenho/concorrÃªncia e demais pontes permanecem pendentes. Nenhuma publicaÃ§Ã£o, custo ou chamada real; objetivo ativo.

## V-165 â€” Consulta DCTFWeb revalida autorizaÃ§Ã£o na fila

24/09/2026. D-146: serviÃ§o exige solicitante atual antes de reservar consumo; worker verifica usuÃ¡rio, vÃ­nculo, perfil, empresa, carteira e mÃ³dulo Guias antes da chamada externa. RevogaÃ§Ã£o/ausÃªncia registra authorization_revoked e libera somente a reserva ainda nÃ£o executada. Resultado incerto permanece reservado e sem repetiÃ§Ã£o automÃ¡tica.

29 testes DCTFWeb passaram em 50,54 s. Novos cenÃ¡rios: ausÃªncia de solicitante antes da reserva; revogaÃ§Ã£o de usuÃ¡rio, vÃ­nculo, empresa, mÃ³dulo, carteira, perfil e perda de responsÃ¡vel enquanto na fila; execuÃ§Ã£o repetida sem chamada; reserva liberada. Testes existentes mantÃªm sucesso, incerteza e percurso web individual/lote. Duas rodadas iniciais falharam no fixture de tela que duplicava mÃ³dulo jÃ¡ criado pelo fixture comum; removida duplicaÃ§Ã£o, sem alterar regra de produÃ§Ã£o para acomodar o teste. Ruff, MyPy dos trÃªs arquivos, Django check e migrations passaram. Sem migration ou alteraÃ§Ã£o de interface; Ãºltima regressÃ£o integral V-164.

Nenhuma chamada real, custo ou publicaÃ§Ã£o. EmissÃ£o de guias/parcelamentos, ligaÃ§Ã£o de documentos aos fechamentos, concorrÃªncia real e homologaÃ§Ã£o permanecem pendentes. Objetivo ativo.

## V-166 â€” Guias e PARCSN revalidam autorizaÃ§Ã£o

24/09/2026. D-147: verificaÃ§Ã£o compartilhada de acesso atual aplicada aos serviÃ§os e workers de emissÃ£o de guias e PARCSN. Exige ator identificado, perfil operacional, usuÃ¡rio/vÃ­nculo/empresa ativos, carteira e mÃ³dulo especÃ­fico. RevogaÃ§Ã£o anterior ao envio registra authorization_revoked e libera reserva nÃ£o executada. Fixtures positivos passaram a informar ator/mÃ³dulo explicitamente; chamadas sem ator sÃ£o testadas como recusadas.

51 testes existentes passaram em 50,77 s. ApÃ³s acrescentar seis casos de ausÃªncia/revogaÃ§Ã£o e reserva, regressÃ£o completa: 929 aprovados, 2 ignorados, 23 subtestes em 81,44 s. Ruff, MyPy dos trÃªs arquivos, Django check e migrations passaram. Sem migration ou mudanÃ§a de UI. Skips permanecem navegador Python opcional e concorrÃªncia PostgreSQL.

RevisÃ£o encontrou falha distinta na emissÃ£o de guias: transporte/retorno sem PDF ainda tratado como falha reemitÃ­vel, com reserva liberada. Checklist antes genÃ©rico foi corrigido para pendente; prÃ³xima implementaÃ§Ã£o deve preservar incerteza e comprovaÃ§Ã£o antes de liberar o fluxo. Esta entrega nÃ£o corrige nem homologa esse comportamento. Demais pontes/fechamentos, navegador, volume e fontes reais continuam pendentes. Nenhuma chamada real, custo ou publicaÃ§Ã£o; meta ativa.

## V-167 â€” Resultado incerto e correÃ§Ã£o de regra pelo proprietÃ¡rio

24/09/2026. EstÃ¡gio provisÃ³rio D-148 acrescentou status unknown, preservaÃ§Ã£o de reserva/retorno, migration 0063 para falhas integration legadas e apresentaÃ§Ã£o de estado/filtro. RegressÃ£o tÃ©cnica: 932 aprovados, 2 ignorados e 23 subtestes em 87,53 s; apÃ³s ocultar emissÃ£o alternativa da mesma competÃªncia, 23 testes de guias passaram em 54,66 s. Ruff/MyPy/check/migrations passaram. Migration apenas em testes. Playwright indisponÃ­vel em listagem/fechamento; nenhuma inspeÃ§Ã£o visual alegada.

Durante a execuÃ§Ã£o, o proprietÃ¡rio corrigiu a regra: reemissÃ£o Ã© permitida com custo adicional por guia (D-149). O bloqueio implementado nÃ£o representa o comportamento aprovado e os testes que o exigem terÃ£o de ser revistos. Adicional perguntado ao proprietÃ¡rio, sem valor/modo presumido. NÃ£o considerar esta validaÃ§Ã£o tÃ©cnica como aceite funcional nem liberar essa versÃ£o. Plano/checklist/manual corrigidos; meta ativa. Nenhuma chamada real, custo ou publicaÃ§Ã£o.

## V-168 â€” HistÃ³rico tÃ©cnico das tentativas de guia

24/09/2026. D-150 e migration 0064: fotografias imutÃ¡veis por tentativa/estado, solicitante identificado por referÃªncia, solicitaÃ§Ã£o preservada, protocolo/retorno criptografado, erro e chave de consumo. ServiÃ§o conserva o resultado anterior antes de limpar campos para outra tentativa jÃ¡ permitida. Worker registra estados junto da gravaÃ§Ã£o da guia. Legado conserva apenas o registro disponÃ­vel, identificado como current_record; nÃ£o fabrica eventos nem cobranÃ§a histÃ³rica.

26 testes de guias passaram em 56,65 s. ApÃ³s acrescentar identificaÃ§Ã£o da origem da fotografia e asserÃ§Ãµes para resultado incerto, regressÃ£o completa: 935 aprovados, 2 ignorados e 23 subtestes em 92,03 s. Novos cenÃ¡rios verificam separaÃ§Ã£o entre duas tentativas, protocolo anterior preservado, retorno criptografado no banco, referÃªncia ao consumo, worker repetido, imutabilidade no ORM, recusa de escritÃ³rio divergente e rollback da solicitaÃ§Ã£o/reserva em falha da gravaÃ§Ã£o. Ruff, MyPy de quatro arquivos, Django check e migrations passaram. Migration aplicada somente no banco de testes; provedores simulados.

Sem alteraÃ§Ã£o de interface nesta frente. Skips permanecem navegador Python opcional e locks PostgreSQL; validaÃ§Ã£o visual acumulada nÃ£o foi resolvida. HistÃ³rico ainda precisa de apresentaÃ§Ã£o autorizada. D-149 continua pendente de modalidade/valor do adicional e implementaÃ§Ã£o da reemissÃ£o; os testes do bloqueio provisÃ³rio nÃ£o constituem aceite dessa regra. Demais pontes, recuperaÃ§Ã£o estruturada, fontes reais e homologaÃ§Ã£o permanecem abertas. Nenhuma chamada real, custo ou publicaÃ§Ã£o; meta ativa.

## V-169 â€” HistÃ³rico de guias consultÃ¡vel e PDF anterior

24/09/2026. D-151: ficha mostra 20 estados por pÃ¡gina, com solicitante do escritÃ³rio, datas, protocolo e indicaÃ§Ã£o de legado/fictÃ­cio. Retorno bruto fica fora do HTML e da consulta da listagem. Download por tentativa emitida usa PDF salvo, registra auditoria e revalida guia/escritÃ³rio/carteira/mÃ³dulo. NÃ£o reserva consumo nem chama fornecedor; nÃ£o modifica a regra comercial pendente.

Rodada conjunta de guias/workspace: 100 passaram e 1 falhou por fixture usando Role.STAFF inexistente. Corrigido para OPERATOR; rodada final de guias: 28 aprovados em 58,62 s. CenÃ¡rios novos verificam 21 eventos paginados, preservaÃ§Ã£o de parÃ¢metros, texto escapado, ausÃªncia de retorno bruto/consumo, PDF de tentativa anterior apesar do estado atual, escritÃ³rio divergente e revogaÃ§Ã£o da carteira. Ruff, MyPy de views, Django check e migrations passaram. Sem nova migration; Ãºltima regressÃ£o integral V-168.

UI/UX Pro Max, Watermelon e Web Interface Guidelines consultados; registro de referÃªncias/auditoria na etapa 11. Playwright retornou Transport closed na listagem e no fechamento; nenhum navegador aberto, nenhuma inspeÃ§Ã£o visual alegada. Desktop/celular, teclado/foco e estados renderizados permanecem pendentes. CobranÃ§a/reemissÃ£o de D-149, recuperaÃ§Ã£o estruturada, demais pontes e homologaÃ§Ã£o continuam abertas; objetivo ativo. Nenhum custo, publicaÃ§Ã£o ou chamada real.

## V-170 â€” Consulta respeita mÃ³dulo na mesma empresa

24/09/2026. D-152 corrige combinaÃ§Ã£o indevida de permissÃµes: uma concessÃ£o do mÃ³dulo em A e uma concessÃ£o de outro mÃ³dulo em B nÃ£o autorizam consulta do primeiro mÃ³dulo em B. company_queryset_for_module intersecta carteira vigente e concessÃ£o especÃ­fica; contexto de Guias/Integra aplica o resultado em listagens, fichas, consultas e downloads. Contador de consultas DTE pendentes passou a filtrar itens da carteira autorizada, sem multiplicar consultas por quantidade de empresas.

29 testes de guias e 2 subtestes passaram em 60,26 s. ApÃ³s acrescentar cenÃ¡rio da central Integra e corrigir seu contador, regressÃ£o integral: 939 aprovados, 2 ignorados, 25 subtestes em 90,38 s. Casos novos verificam operador/auditor, concessÃµes diferentes em duas empresas, listagem, ficha, PDF atual e histÃ³rico, e contadores de empresas/mensagens/consultas pendentes. Ruff, MyPy, Django check e migrations passaram. Sem migration nova ou alteraÃ§Ãµes de templates/estilos. Skips permanecem navegador opcional e locks PostgreSQL; nÃ£o constituem validaÃ§Ã£o visual ou concorrÃªncia real.

Demais lacunas continuam abertas: reemissÃ£o/cobranÃ§a D-149, recuperaÃ§Ã£o estruturada, resultados Serpro ligados Ã  central, adaptadores com observaÃ§Ãµes homologadas, navegador e piloto. Busca atual encontrou record_source_observation implementado e usado por testes, sem ligaÃ§Ã£o produtiva de adaptador; nÃ£o considerar a existÃªncia dessa rotina como integraÃ§Ã£o completa. Nenhuma chamada real, custo ou publicaÃ§Ã£o; meta ativa.

## V-171 â€” Auditoria de cobertura e evidÃªncia de nova resoluÃ§Ã£o NFS-e

24/09/2026. Inspecionados pontos de chamada das pontes NFS-e, Triagem, ConciliaÃ§Ã£o, folha, DTE e Radar, recorrÃªncia/Beat, agregaÃ§Ã£o de fechamentos e rotina de observaÃ§Ãµes. Etapa 11 ganhou matriz atual por requisito, distinguindo implementaÃ§Ã£o local e homologaÃ§Ã£o. Confirmado: resultados de guias/DCTFWeb/PARCSN ainda nÃ£o projetam atividades; record_source_observation sÃ³ tem chamadas nos testes. As pendÃªncias histÃ³ricas nÃ£o foram apagadas nem tratadas como conclusÃ£o.

D-153 corrige evidÃªncia reutilizada entre resoluÃ§Ãµes da mesma revisÃ£o. Primeira rodada revelou tambÃ©m conflito UNIQUE no histÃ³rico de acumuladores, cujo identificador usava apenas o ID da revisÃ£o. Ambos agora usam referÃªncia estÃ¡vel da resoluÃ§Ã£o exata (revisÃ£o, instante, responsÃ¡vel e acumulador), dentro do tamanho de 80 caracteres do histÃ³rico. Registros antigos nÃ£o sÃ£o alterados. NÃ£o foi criado fluxo de reabertura.

Rodada inicial: 11 passaram/1 falhou pelo conflito real acima. ApÃ³s correÃ§Ã£o, 85 testes de pontes, exportaÃ§Ãµes NFS-e e workspace passaram em 58,95 s. CenÃ¡rio novo percorre resoluÃ§Ã£o, reabertura controlada, nova resoluÃ§Ã£o e replay, verificando duas provas, dois acumuladores e preservaÃ§Ã£o da primeira decisÃ£o. Ruff, MyPy, Django check e migrations passaram. Sem nova migration ou mudanÃ§a de interface; Ãºltima regressÃ£o integral V-170. Provedores reais, destino ERP, navegador e PostgreSQL nÃ£o homologados nesta entrega.

D-149 continua pendente. Objetivo permanece ativo, com prioridades atuais na matriz da etapa 11 e manual atualizado. Nenhuma chamada real, custo ou publicaÃ§Ã£o.

## V-174 â€” Resultados Serpro projetados na central operacional

24/09/2026. D-155 adiciona vÃ­nculos exclusivos entre atividade e guia fiscal, documento DCTFWeb ou operaÃ§Ã£o PARCSN, por migration aditiva 0065. ServiÃ§os criam a projeÃ§Ã£o jÃ¡ na solicitaÃ§Ã£o; wrappers dos workers recompÃµem o estado persistido no encerramento, inclusive apÃ³s falha ou resultado incerto. Se a projeÃ§Ã£o local falhar, o worker registra o erro e nÃ£o repete uma operaÃ§Ã£o de fornecedor jÃ¡ iniciada. `sync_serpro_activities --organization UUID` recompÃµe guias, documentos e operaÃ§Ãµes existentes sem chamadas externas.

Guia emitida e DAS disponÃ­vel mostram somente â€œGuia disponÃ­velâ€, evidÃªncia da fonte e atividade pendente; nÃ£o inferem pagamento, aceite, fechamento nem custo. Documento DCTFWeb disponÃ­vel conclui apenas sua obtenÃ§Ã£o e registra que nÃ£o prova transmissÃ£o/aceite. Consulta PARCSN disponÃ­vel ou vazia conclui somente a consulta; DAS segue pendente. Falhas/incertezas sÃ£o impedimentos com motivo. Quem solicitou passa a ser responsÃ¡vel apenas quando a atividade ainda nÃ£o tem responsÃ¡vel, sem substituir atribuiÃ§Ã£o do escritÃ³rio.

ApÃ³s a primeira regressÃ£o, foi encontrada e corrigida a ausÃªncia dessa atribuiÃ§Ã£o tardia quando uma guia jÃ¡ observada era solicitada depois. RegressÃ£o final: 944 aprovados, 3 ignorados e 25 subtestes em 93,65 s. Os 14 testes especÃ­ficos das pontes passaram em 29,95 s; Ruff, MyPy, Django check e migrations limpas passaram. Navegador local repetiu 64 combinaÃ§Ãµes e 21 verificaÃ§Ãµes, com zero erro de console/overflow; a atividade de guia foi inspecionada em celular e abriu a origem por link sem confundir pagamento. Contextos, Edge e servidor sintÃ©tico foram encerrados.

Auditoria das Web Interface Guidelines atualizadas: `views.py` usa links semÃ¢nticos para navegar, o template usa controles nativos existentes e nÃ£o introduz formulÃ¡rio, Ã­cone, animaÃ§Ã£o ou aÃ§Ã£o destrutiva; foco visÃ­vel e alvo do botÃ£o de origem foram verificados no navegador. Watermelon portfolio-dashboard foi consultado como referÃªncia de hierarquia de tarefas; a direÃ§Ã£o adotada mantÃ©m o painel de prÃ³ximo passo existente, sem redesenho. ReferÃªncias pÃºblicas de Karbon/SaaSFrame nÃ£o foram usadas como cÃ³pia e a busca nÃ£o retornou fluxo acessÃ­vel adicional nesta rodada.

NÃ£o houve chamada Serpro, uso de credencial, custo, transmissÃ£o, reemissÃ£o ou homologaÃ§Ã£o. D-149 e Q-40 continuam pendentes. A ponte usa resultados que jÃ¡ existem localmente; nÃ£o comprova a semÃ¢ntica de uma fonte real, recuperaÃ§Ã£o do fornecedor, concorrÃªncia de cliques, pagamento ou fechamento. Meta ativa.

## V-175 â€” Contrato faltante para observaÃ§Ãµes reais do DomÃ­nio

24/09/2026. InspeÃ§Ã£o estÃ¡tica confirmou que o agente em `agent/runner.py` envia somente empresas ao endpoint legado; o endpoint v2 recebe empresas, extratos e pÃ¡ginas de backup. A fila legada de obrigaÃ§Ãµes usa guias calculadas. Nenhuma rota efetiva lÃª ou envia processamento/fechamento, reabertura ou aceite para `record_source_observation`; os Ãºnicos chamadores continuam nos testes. A consulta ODBC allowlisted `FOVGUIAINSS` expÃµe `SITUACAO`, mas o contrato local registra que seus cÃ³digos nÃ£o tÃªm equivalÃªncia semÃ¢ntica aprovada.

Pesquisa em documentaÃ§Ã£o oficial confirmou a distinÃ§Ã£o de negÃ³cio: fechar/reabrir competÃªncia bloqueia o cÃ¡lculo e nÃ£o equivale ao envio S-1299; a transmissÃ£o DCTFWeb depende de S-1299 e/ou R-2099 enviados. Fontes: [fechamento da competÃªncia](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=32) e [DCTFWeb por API](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=10985). Isso sustenta a modelagem separada, mas nÃ£o fornece API, esquema ou cÃ³digos de leitura.

Atualizado `agent-windows/CONTRATOS-DOMINIO.md` e a matriz da etapa 11 com o contrato obrigatÃ³rio antes de extrair: objeto/consulta aprovado, chave empresa/competÃªncia, cÃ³digos, exemplos mascarados e mapeamento explÃ­cito para os estados CICA. NÃ£o foi criado parser ou consulta fictÃ­cia, nem executada leitura ODBC, chamada de fornecedor, custo ou homologaÃ§Ã£o. O bloqueio Ã© tÃ©cnico e externo: validar o contrato no ambiente DomÃ­nio autorizado. Meta ativa.

## V-176 â€” RecuperaÃ§Ã£o local unificada da central

24/09/2026. D-156 adicionou `recover_operational_center --organization UUID`, que recompÃµe em sequÃªncia as atividades jÃ¡ derivadas de NFS-e, Triagem, ConciliaÃ§Ã£o, folha, DTE, Radar, guias, DCTFWeb e PARCSN. O comando exige escritÃ³rio existente nÃ£o demonstrativo, nÃ£o recebe credenciais nem dados de fonte e nÃ£o executa chamadas externas, emissÃµes, transmissÃµes, ciÃªncia ou consumo. Cada execuÃ§Ã£o cria auditoria consolidada com contagens e falhas, sem atribuir usuÃ¡rio humano inexistente. Cada ponte segue transacional e idempotente; uma falha isolada nÃ£o impede a recomposiÃ§Ã£o das demais, mas termina o comando com contagem por domÃ­nio para investigaÃ§Ã£o.

O percurso focal criou uma revisÃ£o NFS-e local, executou o comando e conferiu a atividade projetada, a contagem `nfse=1`, a ausÃªncia de guias, a auditoria de recuperaÃ§Ã£o e a declaraÃ§Ã£o explÃ­cita de nenhuma chamada externa. Novo cenÃ¡rio forÃ§ou falha de uma projeÃ§Ã£o NFS-e: o comando percorreu os demais domÃ­nios, retornou erro com `nfse=1` e gravou auditoria consolidada com falha, sem reportar sucesso. `tests/test_module_activities.py` passou com 16 testes em 26,43 s; Ruff do comando/teste, MyPy do comando, Django check e migraÃ§Ãµes limpas passaram. MyPy do arquivo de testes continua com erros de tipagem preexistentes e nÃ£o Ã© usado como aprovaÃ§Ã£o dessa entrega. NÃ£o houve interface, migration, fornecedor, custo ou homologaÃ§Ã£o externa.

## V-173 â€” Navegador local disponÃ­vel para a central

24/09/2026. Playwright MCP continua sem transporte. Foi possÃ­vel usar Playwright jÃ¡ existente no cache local com Microsoft Edge instalado, perfil temporÃ¡rio, servidor sintÃ©tico em 127.0.0.1:8012 e bloqueio de rede externa. Nenhuma instalaÃ§Ã£o, custo ou dado real. scripts/qa_ui_server.py aceita QA_REVIEW_SUITE=central, com banco e mÃ­dia separados; qa_central_fixture.py cria carteira fictÃ­cia e sessÃµes locais; qa_central_browser.cjs torna a verificaÃ§Ã£o repetÃ­vel.

Rodada final: 52 combinaÃ§Ãµes de pÃ¡ginas/perfis/temas/viewports, 17 verificaÃ§Ãµes registradas e zero erros de console. Conferidos agenda pessoal, carteira, filtro de impedidas vazio, detalhe de atividade e gestÃ£o administrativa, claro/escuro, 1440 e 390 px. Agenda do operador exclui tarefas de terceiros e sem responsÃ¡vel; carteira inclui compartilhadas autorizadas e exclui outra empresa; acesso direto de operador/auditor Ã  outra carteira retorna 404; auditor nÃ£o recebe controle de conclusÃ£o. Details de fechamento abre por Enter com foco e outline visÃ­veis. Nenhum overflow horizontal detectado. Capturas desktop de gestÃ£o e celular da agenda inspecionadas visualmente. Primeira execuÃ§Ã£o falhou por seletor ambÃ­guo no teste; seletor corrigido para regiÃ£o acessÃ­vel, sem alteraÃ§Ã£o de produto.

Resultados/capturas locais: .playwright-mcp/central-review/results.json. SessÃµes sintÃ©ticas ficam em .tmp/central-review, ignoradas pelo Git; nÃ£o publicar. Watermelon consultado novamente (portfolio-dashboard), mantendo a direÃ§Ã£o jÃ¡ documentada de tarefas por prioridade; guidelines atuais consultadas. NÃ£o houve mudanÃ§a de UI nesta entrega. Ruff dos scripts Python aprovado. Navegadores/contextos fechados no finally; servidor de QA encerrado apÃ³s inspeÃ§Ã£o.

Limites: essa rodada nÃ£o percorreu envio de evidÃªncia/conclusÃ£o, carregamento/falha de rede, todos os controles de teclado, nem todas as telas do sistema. NÃ£o substitui piloto, fontes reais ou aceite D-73. A indisponibilidade do MCP jÃ¡ nÃ£o impede testes locais de navegador. D-149 e Q-40 continuam sem resposta; nenhuma regra comercial ou de conclusÃ£o foi presumida. Meta ativa.

## V-172 â€” SuÃ­te executada em PostgreSQL 17 descartÃ¡vel

24/09/2026. Docker local tinha postgres:17-bookworm disponÃ­vel. Criado contÃªiner exclusivo cica-goal-pg-validation, rÃ³tulo cica.task=goal-validation, porta dinÃ¢mica 51331 limitada a 127.0.0.1 e dados em tmpfs. NÃ£o foram usados o banco existente, dados reais, download de imagem ou serviÃ§os pagos. ConfiguraÃ§Ã£o test_postgresql substitui somente os bancos, exige porta explÃ­cita nÃ£o padrÃ£o e recusa ativaÃ§Ã£o de serviÃ§os externos; demais serviÃ§os preservam o modo de teste.

Teste de reserva concorrente antes ignorado no SQLite passou em 34,40 s. Acrescentado teste de recorrÃªncia com quatro conexÃµes independentes: trÃªs competÃªncias produzidas uma Ãºnica vez e cursor avanÃ§ado somente pela execuÃ§Ã£o efetiva. A primeira suÃ­te PostgreSQL terminou com 24 falhas, 918 aprovados, 1 ignorado e 25 subtestes em 182,22 s. D-154 corrigiu locks sobre relaÃ§Ãµes opcionais nos workers DCTFWeb/PARCSN e rotinas de Triagem, preservando lock da linha principal. ReferÃªncia: [Django 6.0, select_for_update](https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update).

RepetiÃ§Ã£o dos casos: 20 passaram e 4 falharam em 58,62 s. Falhas restantes decorreram do fechamento manual de respostas streaming nos testes, que encerrava a conexÃ£o da transaÃ§Ã£o de TestCase e contaminava os testes seguintes. Corrigidos os testes para consumir o conteÃºdo pelo cliente Django, verificar o arquivo e confirmar o fechamento automÃ¡tico; nenhuma alteraÃ§Ã£o no serviÃ§o de relatÃ³rios para esconder o problema.

RegressÃ£o PostgreSQL final: 942 aprovados, 1 ignorado, 25 subtestes em 177,22 s. Ruff e MyPy passaram; Django check e migrations passaram. Houve inicialmente aviso de ausÃªncia do banco-base knowledge na checagem de migrations; criado banco vazio somente no contÃªiner descartÃ¡vel e repetida checagem sem aviso. Sem migrations novas. Ao final, identidade/rÃ³tulo conferidos e contÃªiner encerrado/removido; nenhum recurso de validaÃ§Ã£o ficou em execuÃ§Ã£o.

O Ãºnico skip Ã© Python Playwright opcional. PostgreSQL local comprova os cenÃ¡rios exercitados, incluindo concorrÃªncia de reserva e recorrÃªncia; nÃ£o comprova todos os cliques concorrentes, queda de Beat/worker, recuperaÃ§Ã£o em produÃ§Ã£o, restauraÃ§Ã£o, volume real ou aceite de D-73. Provedores continuaram simulados. Q-40 enviada para confirmar conclusÃ£o da atividade de emissÃ£o; D-149 continua pendente. Meta ativa.

## V-177 - Completed activity state matches available actions

24/09/2026. Browser inspection found that a completed activity still showed block and complete forms, even though services reject those writes. The detail preserves the evidence form for append-only audited corrections and, after `completed` or `waived`, shows a closing note while hiding the invalid actions. Reopening remains tied to a review or applicable source; no closing rule changed.

The server test completes an activity with evidence and verifies the closing note, evidence form, and absence of both invalid controls. The synthetic Edge/Playwright run covered reference/evidence, completion, trail, return to agenda, and 390 px viewport: 64 screens, 23 checks, zero console errors and zero overflow. The visual inspection confirmed visible focus in the evidence field and readable mobile content. Context, browser, and server were closed.

Manual current Web Interface Guidelines audit: forms and buttons remain native; the new note is noninteractive; observed focus is visible; no async update, animation, keyboard shortcut, or destructive action was added. `ui-ux-pro-max` was consulted for completed state and focus. Direct Watermelon consultation was unavailable in this execution, while the documented `portfolio-dashboard` reference remains the agenda hierarchy source. Focused tests `test_operational_center.py` and `test_module_activities.py`: 44 passed, 8 subtests in 27.22 s. Ruff, Django check, `makemigrations --check`, and `node --check scripts/qa_central_browser.cjs` passed.

Limits: fully synthetic scenario, without ERP/Serpro source, network failure, real reopening, concurrent clicks, volume, or pilot. D-149 still awaits a commercial definition for reissue; no price or consumption rule was inferred.

## V-178 - Regressao integral apos a revisao da central

24/09/2026. `uv run pytest -q` terminou com 948 aprovados, 3 ignorados e 25 subtestes em 81,08 s. Os tres skips sao conhecidos: Python Playwright opcional, recorrencia que exige locks PostgreSQL e concorrencia de cobranca que exige PostgreSQL. A cobertura de navegador da central continua no Edge/Playwright local, registrada em V-177.

A regressao demonstra consistencia local entre os modulos exercitados; nao comprova fonte Dominio/Serpro, chamadas reais, contrato de observacoes, reemissao, transmissao, recuperacao cronometrada, volume ou piloto. Nenhuma chamada externa, custo ou publicacao ocorreu.

## V-179 - Capacidade da fonte exigida para mudar estado

24/09/2026. A revisao encontrou que `record_source_observation` validava o valor do estado, mas nao se a fonte podia fornecer aquele estado. D-157 exige `activity_processing_status` para processamento e `activity_obligation_status` para obrigacao, conferidos apos lock da fonte. Uma fonte com somente `companies` foi recusada ao tentar fechar processamento; a atividade permaneceu `not_verified` e sem observacao. Um objeto de fonte carregado antes da remocao da capacidade tambem foi recusado, pois a verificacao usa a linha bloqueada atual. Fonte `disabled` com capacidade declarada tambem foi recusada; a atividade permaneceu sem observacao. Fontes com as capacidades corretas continuam cobrindo reabertura, ordem temporal, conflito e indisponibilidade nos testes existentes.

`tests/test_operational_center.py` passou com 32 testes e 8 subtestes em 26,46 s; Ruff, MyPy do servico, Django check e migracoes limpas passaram. Nao houve migration, chamada externa, custo ou homologacao. Capacidade declarada nao e evidencia de fornecedor: o contrato Dominio/Siescon, os valores de origem e o mapeamento semantico ainda precisam ser aprovados antes de ativar adaptador. Regressao integral apos a mudanca: 949 aprovados, 3 ignorados e 25 subtestes em 80,61 s.

## V-180 - Recuperacao unificada cobre resultados Serpro persistidos

24/09/2026. O teste de `recover_operational_center` agora cria uma revisao NFS-e, guia emitida, documento DCTFWeb disponivel e consulta PARCSN vazia. Uma unica execucao informou `nfse=1`, `guides=1`, `dctfweb=1` e `parcelamento=1`, projetou quatro atividades e a segunda execucao preservou a mesma quantidade. Nenhum mock de fornecedor foi usado porque o comando nao tem chamadas externas.

`tests/test_module_activities.py` passou com 17 testes em 26,19 s; Ruff do teste/comando, MyPy do comando, Django check e migracoes limpas passaram. Ainda faltam prova conjunta de Triagem, Conciliacao, folha, DTE e Radar, alem de recuperacao cronometrada, fontes reais, volume e piloto.

## D-158 - Regra de custo exige definicao expressa do proprietario

24/09/2026. Sempre que um fluxo puder criar cobranca, alterar valor, escolher entre tarifa propria e repasse de fornecedor, ou atribuir custo a escritorio/empresa, o CICA deve solicitar definicao expressa do proprietario antes de implementar o comportamento. A autorizacao de reemissao com custo adicional por guia em D-149 nao autoriza inferir valor, base de calculo, moeda, impostos, momento de cobranca, reembolso ou modelo de repasse. Enquanto esses parametros nao existirem, preservar as tentativas e o estado incerto, sem habilitar emissao cobrada nem criar lancamento financeiro.

**V-181 (24/09/2026):** ampliada a prova automatizada do comando `recover_operational_center`: oito fatos locais persistidos no mesmo escritorio (NFS-e, Triagem, Conciliacao, folha, DTE, guia, DCTFWeb e PARCSN) recompoem exatamente oito atividades no primeiro replay e nao duplicam no segundo. A configuracao inicial das projecoes e isolada por mocks locais; nao ha provedor, transmissao, emissao, ciencia, consumo ou custo. `tests/test_module_activities.py`: 17 aprovados. `ruff`, `manage.py check` e `makemigrations --check --dry-run` passaram. Radar, fontes reais, falha interdominio, tempo D-73, volume e piloto permanecem pendentes.

**V-182 (24/09/2026):** teste adicional confirma a recuperacao do Radar sem coleta: somente o vinculo previamente escolhido por pessoa e reprojetado, com `radar=1`, sem atividade ou evento duplicado quando a versao da publicacao e a mesma. `tests/test_module_activities.py`: 18 aprovados. Ruff, check, migrations e diff-check passaram. A cobertura local nao prova fonte oficial, falha de coleta, carga, tempo D-73 ou piloto.

**V-183 (24/09/2026):** corrigido retorno tardio de fonte desativada: a observacao bem-sucedida e mantida como historico, sem reativar a fonte nem alterar frescor, processamento ou obrigacao; falha tardia preserva `disabled` e pode sinalizar indisponibilidade. Testes `test_operational_center.py` e `test_module_activities.py`: 51 aprovados, 8 subtestes. Ruff, MyPy do servico, Django check, migrations e diff-check passaram. Nenhuma fonte externa, adaptador homologado ou chamada real foi usada.

**V-184 (24/09/2026):** a reativacao administrativa de fonte desativada foi entregue conforme D-160: owner/admin confirma explicitamente, auditor nao pode executar, a fonte volta a `not_configured`, conserva fotografia/capacidades e gera auditoria de antes/depois; nao ha consulta ou nova confianca nos dados. Dois testes de view executados isoladamente passaram (cada um com 1 aprovado, 74 desmarcados). Validacao visual local Playwright/Edge: 66 telas, 24 verificacoes, desktop e 390 px, foco de checkbox, sem overflow/erros de console; servidor e navegador encerrados. Ruff, check, migrations, compileall e diff-check passaram. Fontes reais, adaptadores, carga, D-73 e piloto continuam pendentes.

**V-185 (24/09/2026):** D-161 protege geracao recorrente manual e worker contra responsavel sem carteira e relacoes entre escritorios: o primeiro caso cria atividade sem responsavel com evento, preservando a atribuicao para auditoria; o segundo e recusado antes de criar atividade. O formulario administrativo tambem recusa nova atribuicao incompativel. `test_operational_center.py`: 36 aprovados/8 subtestes; `test_activity_recurrence.py`: 7 aprovados, 1 skip PostgreSQL, 4 subtestes. Ruff, MyPy, check, migrations e diff-check passaram. Playwright Edge local: 70 telas/28 verificacoes, incluindo modelos em 1440/390 px, sem overflow/console; QA encerrado. Ainda nao prova contratos ERP, fontes reais, carga, PostgreSQL de concorrencia nesta alteracao ou piloto.

**V-186 (24/09/2026):** corrigida a divergencia entre a agenda e a ficha da empresa: esta ultima usava o `Meta.ordering` do modelo, que nao expressava D-124 e podia colocar prazo legal mais proximo depois de um prazo interno futuro. `company_detail` agora ordena por `Coalesce(internal_due_on, legal_due_on)`, depois criacao e identificador. O teste cria os tres casos (legal vencido, interno futuro com legal anterior e sem prazo) e confirma a ordem renderizada. `tests/test_hub_workspace_views_django.py -k company_detail_orders_activities_by_the_effective_due_date`: 1 aprovado, 75 desmarcados, 53,44 s. Ruff, MyPy, Django check, migrations e diff-check passaram. Playwright/Edge local: 82 telas, 40 verificacoes, incluindo a ficha em desktop/390 px para tres perfis, sem overflow ou erro de console; a captura conferida mostra os prazos em ordem. Servidor QA e navegador foram encerrados. Sem fonte ERP, custo, reemissao, transmissao ou homologacao externa.

**V-187 (24/09/2026):** a auditoria do motor encontrou que `can_operate_activity` confiava nos campos do objeto `Membership` recebido, e que os tres serviços de escrita nao vinculavam explicitamente `actor` ao membro. D-162 reconsulta o vínculo ativo no mesmo escritório, usuário ativo, perfil operacional e carteira antes de escrever evidência, impedimento ou conclusão. `assign_activity` também consulta o papel administrativo atual. Os testes cobrem membro rebaixado após carregar o objeto, autor externo e proprietário rebaixado mantendo concessão de carteira; não há evento, evidência, conclusão ou redistribuição. `tests/test_operational_center.py`: 38 aprovados e 12 subtestes em 30,68 s. Ruff, MyPy, Django check, migrations e diff-check passaram. Esta validação local não substitui revogação por controlador externo, concorrência PostgreSQL ou piloto.

**Complemento V-187 (24/09/2026):** regressão HTTP da área do escritório: `tests/test_hub_workspace_views_django.py` aprovou 76 testes em 59,27 s, cobrindo carteira, detalhes e POSTs das atividades após a revalidação de vínculo.

**Regressao integral V-187 (24/09/2026):** `pytest -q` passou com 962 aprovados, 3 skips conhecidos e 29 subtestes em 91,62 s. Os skips permanecem Playwright Python opcional e cenarios de locks PostgreSQL cobertos no ambiente proprio; o resultado nao homologa fontes externas, recuperacao cronometrada, volume, piloto ou D-149.

## V-188 â€” Landing simples, orientada Ã  rotina e validada no navegador

24/09/2026. Escopo D-163: revisÃ£o completa da pÃ¡gina pÃºblica inicial. `home.html` agora comeÃ§a com â€œSaiba o que falta. E quem resolve.â€ e uma pauta estÃ¡tica com tarefas, responsÃ¡veis e estados explicitamente fictÃ­cios. BenefÃ­cios precedem recursos; navegaÃ§Ã£o reduzida, FAQ antes do CTA final, teste consistente, integraÃ§Ãµes contextualizadas e seletor de tema Ãºnico. `cica-landing.css` foi reescrito com os tokens existentes; a home deixou de carregar CSS de campanha e scripts de cena/revelaÃ§Ã£o. NÃ£o hÃ¡ mudanÃ§a em backend, preÃ§o, contrato, disponibilidade dos mÃ³dulos, publicaÃ§Ã£o ou integraÃ§Ã£o.

Pesquisa: `ui-ux-pro-max` lido integralmente; buscas de produto/direÃ§Ã£o, minimalismo editorial, foco nÃ£o obscurecido e HTML. SugestÃ£o automÃ¡tica de glassmorphism/azul descartada por incompatibilidade com a marca. Watermelon MCP funcionou: catÃ¡logo hero e `hero-11`, navegaÃ§Ãµes 1/2/3 e `landing-01`; aproveitados tipografia editorial e hierarquia, nÃ£o os templates completos. ReferÃªncias reais: Karbon (contexto de fechamento), Pennylane (central antes do portfÃ³lio), Basecamp (linguagem direta), Front/SaaSFrame (contexto compartilhado). Refero foi consultado, mas nÃ£o forneceu telas acessÃ­veis; SaaSFrame forneceu catÃ¡logo, nÃ£o comparaÃ§Ã£o visual completa. URLs, padrÃµes adotados e diagnÃ³stico em [revisÃ£o da landing](docs/cica-landing-review-2026-09-24.md).

Auditoria completa dos dois arquivos UI pela skill `web-design-guidelines` e fonte atual https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md: sem violaÃ§Ã£o material identificada. Corrigidos feedback de hover da marca e explicitaÃ§Ã£o de backup manual apÃ³s revisÃ£o independente. HTML semÃ¢ntico, headings, skip link focÃ¡vel, FAQ nativa, contraste, foco, conteÃºdo sem JS, alvos, temas, motion e responsividade conferidos. Sem mÃ­dia externa, carrossel, arraste, modal, formulÃ¡rio de dados novo, atualizaÃ§Ã£o assÃ­ncrona ou conteÃºdo de usuÃ¡rio nessa pÃ¡gina; regras especÃ­ficas desses recursos nÃ£o se aplicam. FormulÃ¡rio de aparÃªncia compartilhado preservado e exercitado.

ValidaÃ§Ã£o automatizada: `pytest -q tests/test_cica_landing_django.py tests/test_seed_demo_django.py` â€” 27 aprovados em 63,60 s. Assertions antigas de slogan/cena atualizadas, preservando gates, identificaÃ§Ã£o fictÃ­cia, ausÃªncia de preÃ§os e limites comerciais. Ruff do teste, `python manage.py check --settings=config.settings.test` e diff-check dos arquivos da entrega passaram. NÃ£o houve alteraÃ§Ã£o de modelo/migration nem motivo para repetir a suÃ­te integral.

Playwright MCP funcionou nesta sessÃ£o, usando `scripts/qa_ui_server.py`, banco sintÃ©tico e rede externa bloqueada pelo servidor em 127.0.0.1:8011. Conferidas 12 combinaÃ§Ãµes: 320, 375, 390, 768, 1024 e 1440 px, em claro/escuro, altura 844 no celular e 960 nos demais. Todas retornaram 200, sem overflow horizontal e sem alvos visÃ­veis menores que 24 px; CTA do hero permaneceu dentro do primeiro viewport em todas. Foram inspecionadas visualmente pÃ¡gina inteira desktop clara/escura, hero mÃ³vel, pauta, benefÃ­cios, recursos, integraÃ§Ãµes, FAQ e CTA final mÃ³veis, alÃ©m de foco no rodapÃ© escuro. Capturas locais em `.playwright-mcp/landing-review/`, incluindo `desktop-final.png`, `mobile-final.png` e `dark-desktop-final.png`.

Percurso de teclado: 21 focos sequenciais em 1440/390, skip link com Enter leva ao main, FAQ abre por Enter e fecha por EspaÃ§o; foco de 3 px visÃ­vel. Uma leitura imediata do botÃ£o Sistema ocorreu antes da acomodaÃ§Ã£o do scroll; reinspeÃ§Ã£o confirmou controle inteiro no viewport, e Tab percorreu Claro/Escuro com foco visÃ­vel. Troca real dos trÃªs temas por POST preservou escolha e aria-pressed. Links do CTA e demo abriram `/comecar/` e `/demo/`; a pÃ¡gina de entrada da demo explicou dados fictÃ­cios e ausÃªncia de consultas/cobranÃ§as. Entrar, Termos e Privacidade retornaram 200. NÃ£o foi enviada ficha de cadastro nem iniciado serviÃ§o externo.

Contraste calculado sobre os estilos renderizados de 130 elementos textuais em cada tema, incluindo FAQ aberta: mÃ­nimo 5,45:1 no claro e 5,71:1 no escuro, sem item abaixo do limiar aplicÃ¡vel. Contexto separado sem JavaScript confirmou hero/pauta visÃ­veis, abertura da FAQ e navegaÃ§Ã£o ao cadastro; foi fechado em finally. Movimento reduzido: transiÃ§Ãµes de CTA em 0 s, nenhuma animaÃ§Ã£o ativa. Console final da sessÃ£o: zero erros e zero avisos; recursos observados retornaram 200/304. NÃ£o hÃ¡ busca remota ou estado vazio/carregamento prÃ³prio na landing; gates de demo/Copiloto indisponÃ­veis foram cobertos no servidor, sem atribuir a eles inspeÃ§Ã£o visual. Falha de rede total, submissÃ£o de cadastro, leitor de tela, Safari/Firefox, dispositivos fÃ­sicos e mÃ©tricas de campo nÃ£o foram exercitados.

A primeira tentativa do contexto sem JS teve erro no roteiro de QA (`URL` indisponÃ­vel no executor); o filtro foi corrigido e o cenÃ¡rio completou. Uma chamada inicial de check apontou para `src/manage.py`, caminho inexistente; o comando correto acima passou. Nenhum erro foi ocultado como validaÃ§Ã£o do produto. Browser MCP terminou com â€œNo open tabsâ€; o contexto adicional foi fechado e o servidor de QA foi encerrado. NÃ£o houve custo, envio de mensagem, rastreador, deploy ou homologaÃ§Ã£o comercial. Sem trÃ¡fego/conversÃµes, nÃ£o hÃ¡ evidÃªncia para prometer aumento de vendas; etapa 11 e liberaÃ§Ã£o de produÃ§Ã£o conservam seus limites anteriores.

## V-189 â€” Agente DomÃ­nio Local: continuidade entre empresas e extratos

24/09/2026. InspeÃ§Ã£o de `DominioLocalProcessor.RunOnce` confirmou que os `return` ao concluir empresas tornavam `SendBankEntries` inalcanÃ§Ã¡vel. O fluxo agora encerra apenas o laÃ§o de empresas e, se nÃ£o houver cancelamento, executa a leitura de extratos jÃ¡ allowlisted. `AgentClient.DownloadAsync` tambÃ©m passou a enviar o `PathAndQuery` da URL autenticada e previamente validada, eliminando o erro de compilaÃ§Ã£o `CS1503`.

Evidências locais: `dotnet build agent-windows/src/Cica.Agent.Service/Cica.Agent.Service.csproj --configuration Release --no-restore` concluiu com êxito, sem avisos. `pytest tests/test_intelligence_agent_django.py tests/test_operational_center.py -q` aprovou 43 testes e 12 subtestes em 32,43 s. Ruff e MyPy dos arquivos Python relacionados, `manage.py check`, `makemigrations --check --dry-run` e `git diff --check` passaram; o diff-check reporta apenas avisos históricos de conversão LF/CRLF. Nenhuma conexão ODBC, agente real, serviço externo ou arquivo de cliente foi usado. A validação de execução, retomada e não duplicação no ambiente Domínio continua na etapa 12.


## V-190 — Reconciliação do checklist da central

24/09/2026. Revisão cruzada de docs/planejamento/etapas/11-jornadas-interfaces.md com os testes e entregas V-125 a V-189 removeu pendências históricas já atendidas da agenda, fechamento, recorrência, pontes locais e validação sintética de navegador. Não alterou produto nem executou fonte externa. As pendências restantes foram mantidas explicitamente: adaptadores com semântica comprovada, pilotos, contratos, concorrência/volume, recuperação medida e D-149. Esta atualização documental não trata testes sintéticos como homologação real.

### Complemento V-190 — pesquisa oficial Domínio

Pesquisa atualizada em 24/09/2026 nas publicações oficiais confirma a separação entre fechamento/reabertura da competência, validação S-1299 e transmissão DCTFWeb. Não foi localizado contrato público de leitura desses estados pelo agente ou equivalência para os estados CICA. A evidência reforça a recusa atual de declarar capacidades de processamento/obrigação por inferência; não houve chamada, credencial, consulta ODBC ou mudança de integração.

## V-191 — Recuperação e recorrência: revisão de regressão local

24/09/2026. A revisão do comando de recuperação confirmou que o Radar é deliberadamente recuperável somente depois de uma pessoa vincular a publicação à empresa: a seleção humana é o próprio registro persistido da atividade e não há regra que infira aplicabilidade para todas as empresas. O comando recompõe somente essas projeções; NFS-e, Triagem, Conciliação, folha, DTE, guias, DCTFWeb e PARCSN continuam percorrendo suas origens locais persistidas. A recorrência permanece agendada de hora em hora e é idempotente pela atribuição e competência.

Validação: `tests/test_module_activities.py tests/test_operational_center.py tests/test_activity_recurrence.py -q` aprovou 63 testes e 16 subtestes em 34,62 s; um skip conhecido exige locks PostgreSQL e transações independentes. Ruff, `manage.py check` e `makemigrations --check --dry-run` passaram. A revisão não consultou fontes, não reativou integrações, não executou transmissão, não gerou consumo nem custo. Ela não substitui a medição de recuperação D-73, carga, contratos semânticos Domínio/Siescon ou piloto.

## V-192 — Inspeção visual da central operacional

24/09/2026. A revisão de `dashboard.html`, `closing_dashboard.html` e estilos da central confirmou a separação visual entre agenda pessoal, carteira, gestão e fechamentos. A navegação preserva o estado relevante em URL; tabelas passam para cartões rotulados no celular; os controles de fechamento, links e `details` usam elementos nativos e foco visível. Não foram encontrados desvios materiais nas regras atuais das Web Interface Guidelines para esses arquivos. `ui-ux-pro-max` foi consultado para foco não oculto e conteúdo denso responsivo; o primeiro resultado de stack não teve correspondência e a nova busca confirmou tratamento de textos longos/linhas compactas. Watermelon não estava disponível nesta sessão.

O servidor isolado bloqueou conexões externas. Playwright/Edge executou 82 telas e 40 verificações em perfis operator/owner/auditor, claro/escuro, 1440 e 390 px, sem overflow ou erro de console. A revisão visual confirmou a agenda móvel e a área administrativa desktop; um cenário adicional 844×390 em tema escuro, com `prefers-reduced-motion`, confirmou foco inteiro visível com contorno sólido de 3 px, sem overflow ou erro. A jornada incluiu filtros pessoais/carteira, acesso recusado, ações do auditor, evidência, conclusão, retorno à agenda, modelos, reativação de fonte e `details` por teclado. Contextos, navegador e servidor de QA foram encerrados.

A validação usa banco e sessões sintéticos. Não prova fonte real, acessibilidade com leitor de tela, navegador Safari/Firefox, volume de escritório, recuperação cronometrada ou piloto. Nenhuma chamada a fornecedor, transmissão, emissão, consumo, custo ou publicação ocorreu.

## V-193 — Pesquisa de contratos para observações de fonte

24/09/2026. Pesquisa em documentação pública atualizada confirmou que o Domínio separa fechamento interno da competência e fechamento/reabertura eSocial via S-1299/S-1298; assim, o CICA não pode derivar processamento e obrigação de uma única marca. Não foi localizado contrato público que autorize o agente a ler esses estados ou defina sua semântica para mapeamento CICA. No Siescon, a página pública do Gerenciador de tarefas confirma prazos, inconformidades, documentos e geração automática de tarefas, mas não expõe API, layout ou contrato de leitura dos respectivos estados. O adaptador continua corretamente bloqueado até receber contrato técnico e exemplos autorizados.

Nenhuma integração, chamada autenticada, leitura de banco, custo ou alteração de capacidade foi realizada. O manual externo agora lista o conjunto verificável que o fornecedor precisa entregar; isso não substitui homologação, nem permite marcar processamento/obrigação como atuais.

## V-194 — Regressão integrada da central

24/09/2026. Após a revisão de integridade do motor de observações e dos vínculos entre atividade, fonte, evento e evidência, `pytest -q` terminou com 962 testes aprovados, 3 skips conhecidos e 29 subtestes aprovados em 101,79 s. Os skips permanecem a cobertura Python Playwright opcional e os dois cenários que exigem locks PostgreSQL, cuja validação isolada existe em V-172. A regressão cobre o estado atual do código local e não converte testes em homologação de Domínio/Siescon, fonte real, recuperação cronometrada, carga, piloto ou reemissão D-149.

## V-195 — Landing corrigida no servidor usado e ai-design-skills aplicada

24/09/2026. Complementa D-164/D-166 e corrige o limite de V-188: a revisão anterior verificou um servidor de QA na porta 8011, enquanto a instância acessada pelo proprietário em 8000 continuava servindo HTML antigo com CSS novo. A investigação por netstat confirmou dois listeners na mesma 127.0.0.1:8000; Get-NetTCPConnection mostrava apenas um. Encerrados exclusivamente os processos antigos 8120/2424, previamente identificados no workspace. O runserver atual Python 3.12, PID 16660, permaneceu ativo. Verificação final HTTP 200: título novo e CSS `?v=20260924-3`, um único listener. Nenhum dado, integração ou processo alheio foi alterado.

A configuração local agora usa loaders filesystem/app_directories sem cache de template, inclusive sob --noreload, sem mutar TEMPLATES da configuração base. Prova isolada em um mesmo processo confirmou a atualização de um template temporário após edição; configuração de produção preservada.

Aplicadas as skills design (com design-system/ui-styling), ui-ux-pro-max e a nova landing-page-design de elayadesign/ai-design-skills, instalada pelo helper oficial em C:/Users/gege/.codex/skills/landing-page-design. Watermelon consultado novamente (hero11/hero24/footer15) e referências de produto preservadas no relatório. Manrope única, sem itálicos; fonte WOFF2 local de 24.836 bytes, licença OFL, preload e font-display:swap. Removidas todas as flechas, unificadas dimensões/padding/raios dos botões, escala e espaçamentos; seis perguntas fixas de FAQ mais os condicionais existentes. Conteúdo permanece estático, sem revelações que ocultem a mensagem. Os tokens de marca e o pedido de simplicidade prevalecem sobre padrões de vidro/gradientes/animação da skill. Não foram inventadas provas comerciais.

Auditoria final de home.html e cica-landing.css contra o conteúdo completo atualizado das Vercel Web Interface Guidelines, com revisão independente: sem violações materiais estáticas encontradas. Verificação de Django local, Ruff e diff-check dos arquivos de escopo aprovados (somente avisos históricos LF/CRLF). `pytest tests/test_cica_landing_django.py -q`: 4 aprovados em 54,47 s, incluindo disponibilidade da demo e ausência de condições comerciais inventadas. A suíte de 27 testes anterior permanece registrada em V-188, não foi repetida como se fosse evidência desta rodada.

Playwright MCP na porta real 8000: 320/375/390/768/1024/1440 px, temas claro e escuro; 12 combinações sem overflow, CTA principal dentro da primeira viewport, ambos botões do hero com 48 px, nenhum itálico ou flecha. Inspecionadas capturas completas desktop claro/escuro e segmentos móveis de pauta, rotina, recursos, integrações, FAQ e fechamento. Conferidos tabulação, skip link com foco no main, contorno visível de 3 px, Enter/Space na FAQ, âncora Como funciona, troca efetiva de tema, navegação até cadastro e entrada de demo. Em mobile com movimento reduzido, foco permaneceu inteiro e transição foi 0 s. Contexto separado sem JavaScript confirmou conteúdo, CTA e FAQ nativa. Contexto final limpo confirmou fonte carregada e zero warning, error, pageerror ou requestfailed; a sessão antiga tinha warning de preload durante a edição, não reproduzido após carga limpa com a versão final.

Capturas finais: `.playwright-mcp/landing-review/live-desktop-final.png`, `live-mobile-final.png`, `live-manrope-dark.png`, `live-mobile-connections-final.png` e `live-mobile-start-final.png`. Contextos adicionais foram fechados e browser_close retornou No open tabs. O servidor do usuário em 8000 foi preservado em execução.

Diretriz global solicitada pelo proprietário adicionada em C:/Users/gege/.codex/AGENTS.md:34, preservando integralmente as regras anteriores. Landing-page-design passa a ser obrigatória em toda criação, revisão, modificação ou refatoração de landing, complementando o fluxo de pesquisa, UI/UX, auditoria e navegador. A skill já foi lida/aplicada neste trabalho e estará disponível para descoberta no próximo turno.

Limites: a landing real exibia demo disponível e Copiloto desativado; a nova aparência do bloco Copiloto foi auditada no código, não ativada/renderizada nesta rodada. Página estática não tem carregamento de dados, erro de consulta ou lista vazia a simular. Não houve cadastro concluído, pagamento, fonte externa, consumo, envio, publicação ou medição de conversão. Não foi criado og:image/campanha social nem certificado acessibilidade universal. V-188 não comprovava a versão servida ao usuário; esta evidência acrescenta a verificação que faltou.

## V-196 — Landing reconstruída do zero com paleta neutra

24/09/2026. D-168 substitui a direção visual das revisões anteriores: `home.html` e `cica-landing.css` foram reconstruídos sem reutilizar `cica_motion.html`. A página usa papel quente, grafite e terracota; a inspeção computada encontrou verde somente no ponto que representa um estado positivo na demonstração. O hero passa a prometer “Feche o mês sem caçar informação.”, seguido por uma central de fechamento criada em HTML/CSS, identificada como exemplo ilustrativo com dados fictícios. A narrativa segue por problema, rotina, recursos, integrações, FAQ e CTA final. Não há flechas decorativas, gradientes, prova social, métrica, preço ou homologação inventada.

Foram consultadas as skills `landing-page-design`, `design`, `design-system`, `ui-styling`, `brand`, `art-direction`, `ui-ux-pro-max`, `landing-page-conversion-audit`, `landing-page-guide-v2` e `web-design-guidelines` nos pontos aplicáveis. Watermelon UI foi pesquisado em hero/landing; os padrões de verde dominante, vidro, brilho, bento e depoimentos foram rejeitados. A pesquisa pública usou Front Operations, Karbon workflow/monthly accounting e Pennylane expert-comptable para extrair hierarquia, prova de produto, trabalho em andamento, responsáveis, bloqueios e agrupamento por rotina. Fontes, padrões adotados e limites estão no [relatório](docs/cica-landing-review-2026-09-24.md).

A fonte atual das Vercel Web Interface Guidelines foi lida integralmente. A primeira auditoria renderizada encontrou contraste abaixo de 4,5:1 em textos auxiliares da central, no eyebrow/fine print terracota e no estado selecionado do tema claro. As cores foram corrigidas; a repetição computada em claro e escuro retornou zero texto visível abaixo do limiar aplicável. `theme.js` passou a obter `--canvas` do `body`, e a versão final confirmou `theme-color` `#f3efe7` sobre fundo `rgb(243,239,231)` no claro e `#181715` sobre `rgb(24,23,21)` no escuro. Mantidos skip link, foco de 3 px, elementos nativos, alvos de toque, `scroll-margin`, quebra de texto e movimento reduzido.

Playwright MCP validou a página efetivamente servida em `http://127.0.0.1:8000/`. Em 320, 375, 390, 768, 1024 e 1440 px não houve overflow horizontal; o CTA principal permaneceu na primeira viewport. Tabulação confirmou skip link e oito primeiros alvos com contorno sólido de 3 px. A FAQ abriu com Enter e fechou com Space. Um contexto separado com JavaScript desativado retornou HTTP 200, H1, demonstração, 7 FAQs e CTA final presentes. Home, login, cadastro, demo, termos e privacidade responderam 200; não há IDs duplicados. Temas claro/escuro, cor do navegador, foco, navegação e movimento reduzido foram inspecionados. A rodada final registrou zero warning e zero erro no console e todos os recursos estáticos responderam 200/304.

Capturas finais: `.playwright-mcp/landing-review/from-scratch-desktop-final.png` e `.playwright-mcp/landing-review/from-scratch-mobile-final.png`, além dos recortes `from-scratch-mobile-hero.png`, `from-scratch-mobile-product.png` e `from-scratch-dark.png`. A inspeção visual cobriu a página completa em desktop/celular e o detalhamento da prova do produto. `browser_close` retornou `No open tabs`; o servidor local do usuário na porta 8000 foi preservado.

Validação automatizada: `pytest tests/test_cica_landing_django.py tests/test_seed_demo_django.py -q` aprovou 27 testes em 69,92 s após atualizar as expectativas da copy e do link de demo. `manage.py check --settings=config.settings.local` retornou zero problemas. Ruff aprovou os testes e a configuração local. `git diff --check` dos arquivos de escopo passou com somente avisos de conversão LF/CRLF. A configuração local continua sem cache de templates para impedir a divergência já diagnosticada, sem alteração da configuração de produção.

Limites: esta validação não mede conversão, receita, ativação, funil ou tráfego. Não conclui cadastro, pagamento, integração externa, piloto, publicação, Copiloto ou Siescon. A reconstrução resolve os problemas observáveis de identidade, clareza, hierarquia, responsividade e acessibilidade, mas resultado comercial exige dados reais comparáveis.

## V-197 — Rotina concreta e fontes apresentadas como produto completo

24/09/2026. D-169 atende ao retorno visual do proprietário sobre dois blocos da landing. A lista numerada de três benefícios foi removida por parecer uma composição genérica; em seu lugar, a seção da rotina mostra uma única atividade concreta, com empresa, competência, responsável, origem, decisão e histórico. Os três cards de integração e seus estados “Disponível por configuração”/“Em preparação” foram removidos. Domínio, Integra Contador, e-mail e Siescon agora aparecem em uma faixa única, e a copy adjacente e a FAQ apresentam as fontes como parte pronta da rotina.

UI/UX Pro Max foi consultado para feature proof e rail responsivo. A busca reforçou demonstração concreta do produto; padrões de cards e bento foram rejeitados. Watermelon UI não retornou blocos ou templates correspondentes a workflow/integration rail, portanto a composição foi criada no sistema visual da CICA. A fonte atual das Vercel Web Interface Guidelines foi relida; a auditoria detectou contraste 4,15:1 no rótulo “Central” da demonstração. O tom foi corrigido e a repetição em claro/escuro retornou zero texto visível abaixo do limiar aplicável.

Playwright MCP na porta 8000 verificou 320, 375, 390, 768, 1024 e 1440 px em claro e escuro: 12 combinações sem overflow, sem a lista antiga e sem linguagem de roadmap. A inspeção computada confirmou o verde restrito ao único `status-dot is-review`. Capturas desktop e mobile em tema escuro de `#rotina` e `#integracoes` foram inspecionadas: `.playwright-mcp/landing-review/routine-ready-dark.png`, `integrations-ready-dark.png`, `routine-ready-mobile-dark.png` e `integrations-ready-mobile-dark.png`. FAQ abriu com Enter e fechou com Space. Contexto sem JavaScript respondeu 200 e preservou a nova copy e as quatro fontes. Console final: zero warning e zero erro. `browser_close` retornou `No open tabs`; o servidor do usuário permaneceu ativo.

`pytest tests/test_cica_landing_django.py -q` aprovou 4 testes em 53,29 s. Django check, Ruff e `git diff --check` dos arquivos de escopo passaram, com apenas avisos históricos de LF/CRLF. A apresentação pública solicitada não executa nem homologa as integrações, não publica a página e não mede resultado comercial.

## V-198 — Fedrizzi: leitura real e bloqueio comercial verificável

25/09/2026. No ambiente autorizado Fedrizzi, a consulta ODBC `contabil` foi executada somente por consultas allowlisted. O probe de empresas retornou 576 registros; a sincronização local espelhou 576 empresas e 10.000 lançamentos/extratos normalizados no CICA. A leitura allowlisted de cálculos de guias retornou 3.335 registros, todos com identificador de empresa e valor, mas sem vencimento disponível no contrato atual. Não foi impressa informação identificável, nem houve escrita no Domínio, emissão, transmissão, ciência oficial, consumo Serpro/IA ou cobrança.

O acesso local de desenvolvimento recebeu vínculo owner específico para a homologação Fedrizzi, sem convite ou e-mail e com evento de auditoria. Pelo Console de desenvolvimento, os sete módulos da suíte foram habilitados para o escritório; habilitar o módulo IA não habilitou provedor, modelo, política, limite ou chamada externa. Playwright/Edge abriu a configuração em 1440 px sem erro de console e confirmou os sete módulos selecionados. A área do escritório foi verificada em 1440 e 390 px: permanece corretamente bloqueada em “Ativação pendente”, pois não há contrato vigente. Esse bloqueio impede configurar modelos, abrir agenda ou exercer a carteira real antes de existir contrato, e não foi burlado.

A próxima ação depende de uma escolha comercial explícita do responsável: criar no Console um contrato de homologação sem cobrança, com status e prazo definidos, ou informar o contrato real a usar. Sem isso, não há como validar a agenda e os fluxos autenticados com os dados Fedrizzi sem inventar preço, prazo ou cobrança. Também continuam pendentes contratos semânticos para estados de fechamento/obrigações Domínio, Siescon e qualquer chamada externa cobrada.

## V-199 — Parceiro interno de homologação Fedrizzi

25/09/2026. D-170 introduziu `Organization.is_internal_test_partner`, separado do escritório-demo e de qualquer contrato comercial. Pelo Console de desenvolvimento, apenas Developer/Admin pode ativar a condição para escritório sem controle remoto: a ativação torna o ciclo operacional ativo sem criar `TenantContract`, fatura, assinatura, preço, franquia, credencial ou chamada externa. O encerramento exige confirmação explícita e devolve o escritório sem contrato à ativação pendente. A transição e a condição ficam na auditoria. IA continua bloqueada pelo controle de operação e nenhuma tela passa a emitir, transmitir ou abrir ciência oficial.

A condição foi aplicada pela própria tela à Fedrizzi. Estado observado: parceiro interno ativo, ciclo `active`, zero contratos comerciais, sete módulos habilitados e 576 empresas ativas. Playwright/Edge conferiu Console e área operacional em 1440×1000, 390×844 e 844×390 com movimento reduzido: painel, estado, teclado/foco de 3 px, versão de Integrações, agenda e configuração renderizaram sem overflow ou erro de console. A Integrações deixou de apresentar a mensagem incorreta de teste de 14 dias e informa a condição interna real. Capturas: `.playwright-mcp/fedrizzi-partner-desktop.png`, `fedrizzi-partner-mobile.png`, `fedrizzi-dashboard-live.png` e `fedrizzi-partner-enabled.png`.

UI/UX Pro Max orientou feedback explícito, confirmação antes de encerrar e foco visível. A revisão da fonte atual das Web Interface Guidelines confirmou controles nativos rotulados, mensagens já anunciadas, foco visível e confirmação para a ação que bloqueia acesso. Watermelon MCP não estava disponível. Referências de separação de ambiente e de não movimentar dinheiro em testes: documentação de ambientes do Sentry e testes em sandbox da Stripe. Regressão: `tests/test_platform_tenant_django.py tests/test_hub_workspace_views_django.py -q` — 103 aprovados em 60,13 s; Ruff, MyPy, `manage.py check` e `makemigrations --check --dry-run` passaram.

A validação não cria modelos de atividades ou prazos legais: com a fonte atual, os 3.335 cálculos de guia não trazem vencimento e o CICA não inventa cronograma. Também não homologa estados de fechamento/obrigações do Domínio, Siescon, serviços externos, carga, recuperação cronometrada ou piloto.

## V-200 — Prévia navegável das áreas da landing

25/09/2026. D-171 tornou a prova de produto da landing uma demonstração navegável. `home.html` agora apresenta tabs nativas para Central, Meu trabalho, Empresas, Documentos, Fiscal e Conciliação; cada uma exibe um recorte de trabalho consistente, inteiramente fictício. `cica-product-demo.js` controla o estado acessível, as setas Home/End/esquerda/direita, a âncora compartilhável `#demonstracao-*` e o retorno pelo histórico do navegador. Sem JavaScript, Meu trabalho continua renderizado como a tela inicial. A demonstração não autentica, não consulta a Fedrizzi nem qualquer outra fonte, e não tem ações que escrevem ou geram consumo.

UI/UX Pro Max foi aplicado para estado ativo, URL refletindo a tela e foco de teclado. Watermelon MCP não estava exposto nesta sessão. A pesquisa de referências usou [Karbon](https://karbonhq.com/solution/project-management) para a pauta por responsável, cliente e prazo, [SaaSFrame](https://www.saasframe.io/examples/latitude-project-dashboard) para a hierarquia de navegação lateral, e [Asana](https://help.asana.com/s/article/reporting-with-dashboards) para a leitura de tarefas e estados. Foram adaptados somente hierarquia, densidade e feedback; nenhuma interface, texto proprietário ou dado externo foi copiado.

A fonte atual das Web Interface Guidelines foi relida e a auditoria de `home.html`, `cica-landing.css` e `cica-product-demo.js` não encontrou violação material: buttons nativos, `tablist`/`tabpanel`, foco visível de 3 px, hover, movimento reduzido, texto com quebra e URL do estado. O MCP Playwright não estava disponível; a validação equivalente local em Edge percorreu as seis telas em 1440 e 390 px, clique, teclado, deep-link, retorno do histórico, contexto sem JavaScript e console. Não houve overflow horizontal nem erro de console. Capturas inspecionadas: `.playwright-mcp/landing-review/demo-desktop.png` e `demo-mobile.png`; contextos e browser foram fechados.

`pytest tests/test_cica_landing_django.py -q`: 4 aprovados em 65,30 s. `manage.py check --settings=config.settings.local`, sintaxe Node e `git diff --check` dos arquivos de escopo passaram. Limites: isto valida uma apresentação fictícia, não permissões, dados, operações ou resultados dos módulos autenticados.

## V-201 — Camada visual autenticada alinhada à landing

25/09/2026. D-172 substituiu a linguagem visual compartilhada das telas autenticadas sem tocar seus comportamentos. `cica-auth.css` e `cica-brand.css` agora aplicam Manrope local, papel quente, grafite, terracota, campos, botões, foco e feedback coerentes em login, cadastro, convites, recuperação e MFA. `workspace.css` aplica os mesmos tokens a todo o shell autenticado: cabeçalho, navegação, formulários, painéis, tabs, mensagens, setup e módulos que herdavam o tema anterior. Verde segue restrito a estados positivos. As URLs, forms, permissões, dados, integrações e gates operacionais foram preservados.

UI/UX Pro Max orientou hierarquia de onboarding, foco e configuração responsiva. Watermelon MCP não estava disponível. Referências: [Karbon](https://karbonhq.com/resources/videos/karbon-practice-management-best-practices-how-other-firms-are-using-karbon/) para setup de prática, [Asana](https://asana.com/resources/collections/getting-started-with-asana) para onboarding guiado e [SaaSFrame](https://www.saasframe.io/examples/latitude-project-dashboard) para hierarquia de workspace. Foram adaptados apenas padrões de densidade, orientação e estados, dentro da identidade CICA.

A validação local em Edge abriu login, cadastro, visão geral e configuração da Fedrizzi em 1440 e 390 px. Em todas as oito combinações: sem overflow horizontal, foco visível de 3 px e console sem erros. A configuração e a área de trabalho usaram o escritório parceiro interno Fedrizzi e não chamaram fonte, IA, Serpro ou cobrança. Capturas: `.playwright-mcp/d172-login-final.png`, `d172-final-signup-desktop.png`, `d172-final-workspace-desktop.png` e `d172-final-setup-mobile.png`. A fonte atual das Web Interface Guidelines foi aplicada: controles nativos, foco, responsividade, texto longo, movimento reduzido e estado de navegação na URL permanecem cobertos. O MCP Playwright não estava exposto; os contextos equivalentes locais foram fechados.

Validação automatizada em andamento nesta entrada: `test_cica_auth_flow.py`, `test_cica_signup_flow.py` e `test_hub_workspace_views_django.py`; `manage.py check --settings=config.settings.local` e `git diff --check` passaram. Limite: a camada compartilhada transforma a aparência de todas as telas que a consomem; refinamentos de estrutura específica continuam necessários se uma tela especializada revelar um problema em uso real.

## V-202 — Produto NFS-e isolado, contrato de acumuladores e preparação do Fly.io

28/09/2026. D-175 autoriza oferecer somente NFS-e a um escritório, mantendo apenas os apoios indispensáveis de empresas, certificados, equipe e configuração. A revisão encontrou um vazamento de navegação: as views já redirecionavam ou recusavam módulos não contratados, mas a inclusion tag não encaminhava ao menu a condição `is_nfse_only_subscription`. O contexto foi corrigido e a regressão passou a exigir que “Visão geral” também não seja renderizada. Playwright verificou o escritório sintético NFS-e em 1440×1000 e 390×844: `/app/` direciona a `/app/nfse/`, o menu contém somente Cadastros, Fiscal e Configurações, URLs diretas de atividades, modelos e guias respondem 403, não há overflow, o menu móvel expõe `aria-expanded`, o foco tem 3 px e uma carga limpa encerrou sem warning ou erro. Capturas: `.playwright-mcp/nfse-only-desktop.png` e `.playwright-mcp/nfse-only-mobile.png`; não ficaram abas nem servidor de QA abertos.

O arquivo autorizado `07129_20260923_2000C.dom` foi identificado com 4.761.540.834 bytes e SHA-256 `E35B0D86E7171628538E6EB8DCA58DEE26941C887A7DB4A5A3F63C4D9A1FC899`. A chave do contêiner foi validada e a cópia temporária abriu no SQL Anywhere 17, mas `DBA/sql`, login integrado e a credencial de outro escritório foram corretamente recusados. Portanto, nenhum registro interno do escritório 07129 foi lido: falta a credencial de “Usuário Externo” do banco Domínio desse escritório. O servidor temporário foi encerrado e os 17 GB extraídos foram removidos; o `.dom` original permanece intacto em Downloads.

Metadados e agregados não identificáveis do DSN de homologação já autorizado confirmaram `bethadba.EFACUMULADOR` como catálogo básico, com chave por empresa/código, nome e inativação. O agente Windows agora consulta somente esses campos, pagina em lotes de 500 e envia a capacidade `accumulator_catalog`, sem inferir tratamento tributário nem ler parâmetros fiscais. Build Release do agente passou sem warnings/erros; os dois testes do endpoint de backup passaram em 29,65 s. O contrato foi documentado em `agent-windows/CONTRATOS-DOMINIO.md`.

Validação local: 13 testes de isolamento/navegação passaram em 56,95 s; Ruff, MyPy, Django check, validação do `fly.toml` e `git diff --check` do escopo passaram. UI/UX Pro Max foi consultado para permissão mínima e feedback; o Watermelon foi pesquisado em dashboards, blocks, templates e showcases, sem composição correspondente. Referências de produto pesquisadas: SaaSFrame (papéis/permissões e configurações), Pageflows (convite/permissões) e Refero (sem análogo próximo); adotaram-se somente isolamento explícito, escopo visível e navegação mínima. A fonte atual das Web Interface Guidelines foi auditada sem violação material nos arquivos alterados.

No Fly.io foram criados, sem máquina ou banco cobrado, a organização `cica` e o app pendente `cica-contabil`; `fly.toml` aponta ao app e é válido. A publicação permanece bloqueada antes da contratação: a arquitetura recomendada supera US$ 1/mês e exige aprovação específica do custo. Também permanecem necessários os segredos de produção e a credencial externa do backup; nenhum preço de venda, contrato do escritório, tráfego real ou homologação fiscal foi inventado.

## V-203 — Produção Fly.io operacional e nova tentativa do backup 07129

28/09/2026. Após D-177, foram provisionados `cica-contabil`, `cica-contabil-db` e `cica-contabil-valkey` em `gru`, com Tigris privado. Migrações principal e knowledge concluíram; `manage.py check --deploy` não apontou problemas. A imagem passou a gerar o manifesto WhiteNoise durante o build e a atribuir os estáticos ao usuário sem privilégio. Em produção, `/`, `/api/v1/health/ready/` e o favicon versionado responderam 200; o health confirmou banco e cache, o check Fly ficou passing, o worker respondeu `pong` e o armazenamento privado passou por criar, ler e apagar um objeto temporário. O MCP de navegador não ofereceu browser nesta sessão, portanto não há alegação de nova inspeção visual de produção.

Topologia efetiva: web 512 MB, worker/beat 512 MB, Postgres não gerenciado 256 MB/3 GB com três checks passing, Valkey 256 MB/1 GB e bucket privado. O endereço público é `cica-contabil.fly.dev`, IPv4 compartilhado `66.241.125.197` e IPv6 dedicado `2a09:8280:1::19f:191b:0`. O domínio próprio ainda depende do hostname exato para emissão do certificado e inclusão explícita em allowed hosts/CSRF. Sentry está desabilitado por ausência de DSN; o agente mantém HMAC/HTTPS, mas mTLS ainda não está configurado. Uma única instância por serviço de dados e snapshots sem WAL não constituem alta disponibilidade nem restauração homologada.

O backup 07129 foi novamente descompactado em cópia temporária com a chave padrão documentada do Domínio Web. O SQL Anywhere abriu localmente apenas em `127.0.0.1`, mas recusou tanto o e-mail informado quanto sua forma literal com barra usando a senha fornecida (`Invalid user ID or password`). Isso confirma que as credenciais usadas no portal/geração do backup não são necessariamente o “Usuário Externo” interno do banco. Nenhuma linha de empresa ou acumulador foi lida ou enviada à produção; a extração normalizada continua bloqueada até receber UID/senha de Usuário Externo válidos.

## V-204 — Tenant Bianchi & Rizzotto preparado para NFS-e

28/09/2026. Em produção foi criado de forma idempotente o tenant `bianchi-rizzotto`, com perfil que exige código Domínio, sete registros explícitos de módulos e somente `nfse` habilitado; os outros seis estão desabilitados. A fonte `Backup Domínio Web 07129` foi vinculada ao tenant com capacidades `companies` e `accumulator_catalog` e estado `attention`, sem contrato, usuário, empresa ou acumulador inventado. A verificação final mostrou 0 empresas, 0 acumuladores, `nfse` como único módulo habilitado e fonte aguardando credencial externa.

Na cópia local também foram testados `Externo`, o e-mail sem barra e o e-mail literalmente com barra, todos com a senha fornecida; o SQL Anywhere devolveu `-103 Invalid user ID or password`. O servidor local foi encerrado. A extração de 17 GB foi preservada temporariamente com ACL restrita ao usuário atual e SYSTEM para evitar nova espera quando a credencial correta chegar. Nenhum dado do backup foi enviado à produção.

## V-204 — Revalidação após `ERR_CONNECTION_RESET`

28/09/2026. Após o proprietário apresentar uma captura do navegador com `ERR_CONNECTION_RESET`, a produção foi inspecionada sem reinício, deploy ou alteração de recurso. `flyctl status`, `flyctl checks list` e `flyctl machine list` mostraram web e worker em estado `started`, host `ok` e o check HTTP da web passando. A página inicial e `/api/v1/health/ready/` responderam 200 pelo IPv4 público; o health informou banco e cache `ok`. DNS A/AAAA, TCP/443, certificado TLS e o redirecionamento HTTP 301 para HTTPS também passaram.

Vinte requisições consecutivas à página inicial retornaram 200, com 19.778 bytes e duração entre 62 e 196 ms. Os logs disponíveis mostraram os checks de prontidão em 200 e tarefas periódicas concluídas, sem reinício, OOM, traceback ou erro da aplicação. O histórico de releases contém uma primeira release falha durante a publicação e cinco releases posteriores concluídas; a captura é compatível com uma indisponibilidade transitória nessa janela, mas os dados retidos não permitem atribuir causalidade definitiva. A falha não foi reproduzida, portanto nenhuma intervenção destrutiva foi feita. A tentativa de inspeção por navegador não pôde avançar porque o MCP não ofereceu browser nesta sessão.

## V-205 — Domínio próprio configurado no app e bloqueado pela zona DNS

28/09/2026. D-179 definiu `cicacontabil.com.br` e `www.cicacontabil.com.br` como hostnames públicos. Foram criados certificados para ambos no app `cica-contabil` e configurados `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS` explicitamente. A atualização controlada levou web e worker à versão 7; ambos retornaram a `started`, o check HTTP passou e o endpoint de prontidão confirmou banco e cache `ok`.

A consulta pública e os nameservers autoritativos HostGator mostraram dois registros A simultâneos para o domínio raiz: o Fly correto `66.241.125.197` e o legado `162.240.81.81`. O AAAA já aponta ao Fly e `www` é CNAME para a raiz. O Fly recusou verificar ambos os certificados enquanto o destino incompatível permanecer, e o handshake pelo hostname próprio ainda não pode ser validado. É necessário remover somente o A `162.240.81.81` no painel DNS, preservando A `66.241.125.197`, AAAA `2a09:8280:1::19f:191b:0` e o CNAME de `www`; depois, repetir a verificação e os testes HTTP/TLS. Não havia conector ou browser disponível para alterar a zona HostGator nesta sessão.

Na repetição posterior, `dns3.hostgator.com.br`, `dns4.hostgator.com.br`, 1.1.1.1 e 8.8.8.8 já retornavam somente `66.241.125.197`; o AAAA e o CNAME de `www` permaneciam corretos. O Fly informou certificados Let's Encrypt RSA/ECDSA `Issued` e ativos para apex e `www`. A máquina Windows ainda guardava `162.240.81.81` no cache local com o TTL anterior, explicando a continuidade do `ERR_CONNECTION_RESET`. Após `ipconfig /flushdns` e `Clear-DnsClientCache`, cinco acessos ao apex e três ao `www` responderam 200 pelo IPv4 correto, com verificação TLS sem erro. O health da aplicação permaneceu passing.

O Edge já aberto continuou exibindo `ERR_CONNECTION_TIMED_OUT` mesmo depois da limpeza do resolvedor do Windows. A instância estava em execução desde antes da alteração DNS. Uma sessão headless isolada do mesmo Edge, com perfil temporário limpo, carregou o HTML completo de `https://cicacontabil.com.br/`; o IPv4 direto também continuou respondendo 200 e o proxy WinHTTP estava desativado. Isso isola a falha restante ao cache DNS/socket da sessão antiga do navegador, não ao domínio, certificado, Fly ou Django. As abas existentes não foram encerradas à força.

## V-206 — Perfil isolado preparado para login Gerente no backup 07129

28/09/2026. A documentação oficial da Thomson Reuters confirma que a janela intitulada `Conectando ...` é a tela de conexão/login, que a conexão local deve apontar ao arquivo restaurado e que a autenticação inicial usa usuário `Gerente` e senha `gerente`. A instalação local possui executável Domínio de 32 bits, mas o DSN de sistema `Contabil` estava configurado com `dbodbc17.dll` de 64 bits. O DSN de sistema não foi alterado. Foi criado o DSN de usuário `CICA07129` com o driver SQL Anywhere 17 de 32 bits, servidor `srvContabil`, banco `Contabil` e TCP restrito a `127.0.0.1:2638`; o `contabil.ini` do usuário foi temporariamente apontado a ele.

A cópia extraída em `%LOCALAPPDATA%\Temp\cica-backup-07129-20260928\contabil.db` iniciou, concluiu recovery e ficou aceitando conexões somente no loopback. O Domínio abriu a tela `Conectando ...` com o usuário `GERENTE` previamente registrado no perfil. A automação disponível não controla aplicativos nativos, portanto a digitação da senha e o clique em OK dependem do proprietário na janela já aberta. Até esse login ocorrer, permanecem 0 empresas e 0 acumuladores importados em produção; não há alegação de leitura concluída.

## V-207 — Limite da senha padrão na base restaurada 07129

28/09/2026. O proprietário confirmou que `gerente` foi recusada como senha do usuário `GERENTE`. A central oficial documenta `Gerente/gerente` para instalação demonstrativa, mas a recuperação de senha informa separadamente que, quando o usuário GERENTE não consegue usar pergunta/resposta, é necessário acionar o suporte para avaliar a recuperação ou troca da senha do banco. Isso confirma que a restauração preserva a credencial da base do escritório e que não há segunda senha padrão oficial aplicável a este backup. Nenhuma nova tentativa automatizada, alteração de credencial ou contorno foi realizado; produção continua com 0 empresas e 0 acumuladores desse backup.

## V-208 — Primeiro administrador criado e login real validado em produção

28/09/2026. A consulta direta ao banco principal do app `cica-contabil` encontrou 0 usuários, 0 superusuários e 0 registros de `PlatformAccess`; por isso `suporte@mewstack.com.br` nunca poderia autenticar. Foi criado um único usuário ativo com esse endereço, nome `Administrador Mewstack`, papel `admin`, senha inicial aleatória utilizável e MFA obrigatório. Uma tentativa anterior do mesmo identificador foi limpa no django-axes. O bootstrap ficou registrado pelo evento append-only `platform.access.bootstrapped`, sem organização, empresa, contrato ou dado fiscal criado.

O fluxo HTTPS real foi testado contra `https://cicacontabil.com.br/entrar/`, com CSRF e cookies normais. O GET respondeu 200; o POST com a credencial criada foi aceito, gerou sessão e terminou em `https://cicacontabil.com.br/mfa/configurar/?next=/platform/`, sem mensagem de credencial inválida. A verificação posterior confirmou um usuário total, papel `admin` ativo, `mfa_required=True` e hash compatível com a senha entregue. O navegador MCP não estava disponível; a validação foi feita pelo fluxo HTTP de produção, sem alegar inspeção visual.

## V-209 — Backup 07129 integralmente lido e importado em produção

28/09/2026. O aviso de atualização apontava para o compartilhamento antigo `\\sonia\atual\contabil`; a causa era a base no ajuste 10.6A-08.10 e os executáveis locais em ajuste anterior. O pacote oficial `C106A0810.exe` apresentou MD5 `631ae38b903eccab6199449be971be09` idêntico ao checksum oficial e assinatura Authenticode válida de Thomson Reuters Corporation. Após a atualização, `GERENTE`/`lua` abriu a cópia isolada e permitiu cadastrar pelo fluxo suportado um usuário de tipo `Externo`.

A leitura ODBC encontrou 208 empresas — 72 ativas, 135 inativas e 1 com status distinto — e 15.701 acumuladores distribuídos por 202 empresas. Foram confirmados zero acumuladores órfãos, zero chaves empresa/código duplicadas e zero nomes vazios. O lote de produção `d4578c99-7258-490e-aa99-c992cf5d9703`, ligado exclusivamente a `bianchi-rizzotto`, terminou como `completed` com `row_count=15909`, `created_count=15909`, `updated_count=0`, `ignored_count=0` e nenhuma mensagem de erro.

No destino ficaram 208 empresas, 15.701 acumuladores e 15.701 entradas append-only de histórico. A fonte `Backup Domínio Web 07129` está `ready`, com capacidades `companies` e `accumulator_catalog` e fotografia `2026-09-23T23:00:00Z`. Os sete registros de produto continuam explícitos e somente `nfse` está habilitado. Durante a primeira passagem, o Postgres legado de 256 MB atingiu temporariamente limites de memória/I/O após 9.000 acumuladores; o lote permaneceu em processamento e foi retomado de modo idempotente em páginas de 100, sem duplicação ou aumento de recurso. Ao final, web, banco e cache responderam `ok`, o check HTTP passou e os três checks do Postgres ficaram `passing`. O servidor SQL Anywhere temporário foi encerrado, o DSN e o perfil do Domínio foram revertidos, a cópia de 17 GB, o instalador e os arquivos intermediários locais/remotos foram eliminados; o `.dom` original de 4.761.540.834 bytes permanece em Downloads.

Limite operacional verificado: o backup entregou cadastro de empresas e catálogo de acumuladores, não os certificados privados nem as autorizações municipais/ADN necessárias para baixar notas. Produção ainda possui 0 certificados, 0 sincronizações NFS-e e 0 documentos NFS-e, e `NFSE_ADN_SYNC_ENABLED=False`. Portanto, o catálogo está pronto para configuração, mas a baixa real não deve ser anunciada como homologada até cadastrar os certificados/credenciais autorizados, habilitar a integração e executar uma sincronização piloto.

## V-210 — Vínculos compactos de acumuladores importados

28/09/2026. A leitura somente leitura da cópia temporária identificou as tabelas fiscais reais `efservicos` e `efentradas`, seus vínculos com `efclientes`/`effornece` e as configurações explícitas dos importadores NFS-e. A extração agregou na origem somente empresa, acumulador, código de serviço disponível, hash truncado da contraparte, frequência e último uso. Número, valor, nome, endereço, descrição, documento bruto e XML históricos não foram transmitidos nem persistidos.

Foram produzidas e importadas 49.199 observações únicas de 188 empresas: 16.414 combinações de serviços emitidos e 32.785 de serviços tomados. A origem continha zero acumuladores fora do catálogo, zero critérios vazios e zero chaves duplicadas. A análise encontrou 9.379 chaves com mais de um acumulador histórico; o classificador local agora exige correspondência real e mantém concorrentes próximos em revisão humana. O lote `b4551285-7f15-4c20-9a13-7bbba68ba3ff` concluiu em produção com 49.199 criados, zero atualizados e zero ignorados. A conferência posterior confirmou 49.199 linhas, 49.199 chaves distintas, zero órfãos, fonte `ready` e capacidade `accumulator_observations`. Health de banco/cache e check HTTP permaneceram passando.

O agente Windows foi ampliado para agregar as mesmas tabelas na máquina de origem, pseudonimizar CNPJ/CPF antes da transmissão e paginar a capacidade nova; build Release passou com zero avisos e zero erros. Nove testes focados de classificação e ponte de backup passaram, assim como Ruff nos arquivos alterados. A proteção de ambiguidade está implementada e validada localmente, mas não foi publicada nesta entrega; a coleta ADN continua desabilitada e não há certificados ou documentos reais em produção. Antes de ativar a coleta, é obrigatório publicar e revalidar essa proteção.

## V-211 — MFA temporariamente removido do administrador

29/09/2026. Em produção, `suporte@mewstack.com.br` permaneceu ativo e com papel `admin`, mas passou a ter `mfa_required=False`. O único dispositivo TOTP vinculado foi removido e a conta ficou com zero dispositivos e zero códigos de recuperação; a alteração foi registrada em auditoria como `accounts.mfa.temporarily_disabled`. Nenhuma outra conta, permissão ou política global foi modificada.

O fluxo real em `https://cicacontabil.com.br/entrar/` foi percorrido pelo Playwright com a credencial definida pelo proprietário. O formulário autenticou e abriu diretamente `https://cicacontabil.com.br/platform/`, sem passar por configuração ou verificação de segundo fator. A aba foi fechada ao final, encerrando a sessão isolada de validação. Esta evidência confirma somente a exceção temporária dessa conta; não desativa MFA no produto.

## V-212 — Detalhe do escritório e convite simplificados

29/09/2026. O detalhe do escritório foi reorganizado em sistemas, administração e configurações avançadas sob demanda. Cobrança e tentativas Claude vazias deixaram de gerar painéis; contexto de contrato, operação e homologção permanece disponível sem repetir explicações. O modal agora identifica a pessoa, oferece seis papéis vigentes e apresenta erros de campo e de entrega com motivo e próxima ação.

`tests/test_platform_tenant_django.py` aprovou 29 testes, incluindo todos os papéis, rollback do convite e mensagem de entrega. Ruff, `manage.py check --settings=config.settings.test` e `git diff --check` passaram. Playwright local inspecionou 1440×1000 claro, 1024×768 sistema e 390×844 escuro com movimento reduzido: sem overflow, controle sem nome ou erro de console; foco inicial, resumo de validação, Escape e retorno do foco passaram. Capturas e resultado ficaram em `.playwright-mcp/tenant-detail/`, e o navegador foi encerrado. O MCP exigido não ofereceu browser nesta sessão; a inspeção foi executada pelo Playwright local do mesmo projeto.

Consulta somente leitura em produção confirmou uma configuração transacional existente, mas sem host SMTP, remetente, usuário ou senha, e zero convite para `adm@brcontabil.net.br`. Portanto a captura não representa perda de convite: a transação foi revertida como projetado. A entrega real continua bloqueada até o responsável informar credenciais SMTP válidas no Console. Nenhum segredo foi exibido, convite criado, e-mail enviado ou deploy executado.

## V-213 — Fluxo do administrador sem MFA duplicado

29/09/2026. D-190 eliminou os gates divergentes. A configuração do Console agora consulta a política central de MFA e as rotas diretas de cadastro, verificação e QR não criam TOTP quando existe dispensa explícita de plataforma e nenhuma exigência de escritório. O segredo mostrado na captura foi tratado como comprometido; o dispositivo não confirmado reaparecido antes da publicação foi removido. `suporte@mewstack.com.br` terminou com MFA não exigido, zero dispositivos e zero códigos de recuperação. Demais contas continuam sob a política normal.

Regressão: 973 testes e 29 subtestes aprovados; 2 testes foram pulados por exigirem locks reais do PostgreSQL e 1 teste visual ficou separado. Ruff, MyPy, Django check e migrations check passaram. A release 12 deixou web e worker na mesma imagem. Health HTTP, banco, cache e os três checks do PostgreSQL passaram. No código publicado, uma sessão autenticada da conta dispensada obteve Console 200 e Configurações 200; `/mfa/configurar/` redirecionou a `/platform/` sem criar dispositivo e o QR respondeu 404.

Snapshots dos volumes de PostgreSQL e Valkey, com retenção de cinco dias, precederam a publicação. A tentativa de backup contínuo da Fly gerou pressão transitória de I/O e foi revertida; o banco voltou a 256 MB e todos os checks passaram. Não há alegação de restauração homologada. A fonte atual das Web Interface Guidelines foi relida e não houve mudança visual no fluxo de MFA. O browser/Playwright MCP não estava disponível; a tela pública de login e o health foram validados por HTTPS, sem alegação de nova inspeção visual renderizada.

## V-214 — Corretor removido do nome no convite

29/09/2026. O campo `invite-full_name` passou a renderizar `spellcheck="false"`, removendo o sublinhado e o indicador do corretor do navegador sem retirar autocomplete, rótulo ou foco. Os 29 testes do detalhe do escritório, Ruff e diff check passaram. A fonte atual das Web Interface Guidelines foi auditada sem achado material no arquivo alterado; Watermelon não retornou bloco próximo para a correção pontual. O rolling deploy terminou com web e worker saudáveis. O browser Playwright não estava disponível nesta sessão, portanto não há alegação de inspeção renderizada.

## V-215 — Importação simples e em lote de certificados

29/09/2026. D-192 removeu a escolha manual de empresa e o rótulo obrigatório. A tela aceita um ou vários `.pfx`/`.p12` por seleção ou arraste; o serviço abre cada PKCS#12 localmente, exige chave privada, extrai prioritariamente o CNPJ do `otherName` ICP-Brasil `2.16.76.1.3.3` e usa somente uma correspondência exata e válida entre as empresas acessíveis. A senha pode ser comum ao lote ou inferida por regras determinísticas e limitadas (`senha=`, `password=`, `pwd=`, sufixo após `__` ou valor entre colchetes). IA e serviços externos não são usados. Arquivos inválidos, grandes, duplicados, ambíguos ou sem empresa ficam como não reconhecidos, não são persistidos e não têm nome ou senha reproduzidos em sessão, mensagens ou auditoria.

## V-216 — Fila sem limite artificial e senha assistida

29/09/2026. D-193 cobre o padrão real `Empresa - SENHA.pfx` e o sufixo numérico separado por espaço. A interface processa o lote no navegador, um arquivo por requisição, sem o teto anterior de 50. Falha de abertura pausa apenas o item atual e oferece senha, nova tentativa ou pular; o resumo final agrupa reconhecidos, duplicados e itens que precisam de atenção sem repetir dezenas de mensagens. O browser local percorreu dois arquivos inválidos em 390×844, confirmou as duas pausas, o avanço após “Pular” e o resumo final, sem erro de console. Nenhum nome ou segredo foi exibido pela resposta do servidor.

A release Fly 15 foi publicada após snapshots agendados de PostgreSQL e Valkey. Web e worker usam a mesma imagem; health externo respondeu 200 com banco e cache `ok`, o worker conectou ao Valkey e anunciou `ready`, e os novos identificadores de cache chegaram à página pública. A barreira final teve 114 testes aprovados e 1 ignorado opcional, além de Ruff, MyPy, Django check, migrations check, sintaxe Node e diff check aprovados.

A solução foi baseada na documentação oficial do ITI para os campos ICP-Brasil, na API PKCS#12/X.509 do `cryptography`, nas alternativas acessíveis ao arraste descritas por MDN/W3C e em referências de revisão de importação do Customer.io/Productboard. O Watermelon não retornou componente pertinente após busca focada e refinada; a pesquisa externa exigida foi então executada. As Web Interface Guidelines atuais foram relidas e motivaram associação de ajuda, foco visível, estado ocupado e respeito a movimento reduzido.

Foram aprovados 5 testes novos de certificados e 76 testes de regressão do workspace, além de Ruff, MyPy, Django check, migrations check e diff check. A suíte completa aprovou 977 testes, ignorou 2 e executou 29 subtestes; dois testes alheios falharam nessa passagem e passaram isoladamente logo depois, portanto a execução integral não é declarada verde. Playwright inspecionou desktop claro e celular escuro com movimento reduzido, seleção múltipla, lote misto reconhecido/não reconhecido, foco, Escape, retorno de foco, responsividade, ausência de segredo visível e console sem erros; todas as abas e o servidor de QA foram encerrados. Nenhum deploy, certificado real, ativação ADN ou homologação fiscal foi realizado.
## V-218 — Fila NFS-e sequencial e classificação unificada em produção

29/09/2026. A release 21 publicou a migration `0066`, a fila durável e a nova tela principal de notas. Web e worker ficaram na mesma imagem, o check HTTP passou e `/api/v1/health/ready/` confirmou banco e cache `ok`. A regressão focada aprovou 95 testes; Ruff, Django check, migrations check, sintaxe Node e diff check passaram.

Na Bianchi & Rizzotto, a fila recuperou um lease antigo interrompido pelo rolling deploy sem duplicar documentos. O dispatcher manteve exatamente uma empresa ativa por vez. A coleta oficial aumentou o acervo observado de 1.327 para 1.746 NFS-e; a execução de RESTAURANTE ZAPPAROLI LTDA terminou com lote de 50 documentos, `checkpoint_nsu=50`, `max_nsu=50`, zero sincronizações em erro e zero em retry. Certificados vencidos ou revogados continuam fora da seleção sem bloquear empresas elegíveis.

A interface foi validada localmente em 1440×1000 e 390×844, com movimento reduzido, teclado, foco, classificação real de demonstração, agrupamento por empresa, filtro binário e competência anterior (08/2026 em 09/2026), sem overflow ou erro de console. A tela de revisões deixou a navegação e sua URL antiga redireciona para as notas não classificadas. A tentativa adicional de abrir a produção pelo navegador MCP não avançou porque nenhum browser estava disponível; portanto a evidência visual é da mesma release local, enquanto deploy, health, migration, banco, fila e coleta foram verificados na produção. O ZIP segue identificado como pacote de conferência até o layout do Domínio pendente em Q-39 ser fornecido e homologado.

## V-219 — Correção automática do acumulador e lote filtrado de NFS-e

29/09/2026. A lista passou a identificar cada documento pelo número fiscal normalizado, sem exibir NSU ou hash. Um acumulador classificado pode ser corrigido na própria linha: valor válido é salvo automaticamente por AJAX, sem recarregar, e produz novo artefato imutável, histórico e auditoria; os downloads seguintes escolhem a correção terminal mais recente. A seleção cobre nota, empresa, página e todos os classificados do filtro, inclusive entre páginas e empresas, com contagem antes da ação. O ZIP continua explicitamente denominado pacote de conferência enquanto Q-39 estiver aberto.

Playwright MCP conferiu a tela local em 1239 px e 390 px: alteração `23` → `24` confirmou `Salvo` sem navegação, seleção global habilitou o download com contagem singular correta, não houve overflow horizontal nem erro de console, o foco por teclado ficou visível e movimento reduzido zerou transições. Ruff, sintaxe Node, Django check e migrations check passaram. A regressão focal terminou com 19 aprovados e 69 não selecionados em 56,52 s. A suíte integral terminou com 991 aprovados, 3 ignorados e 29 subtestes; duas asserções antigas ainda esperam a tela separada de revisões substituída por D-202 e não pertencem ao novo fluxo de acumulador/lote. Nenhuma importação no Domínio ou homologação de Q-39 foi alegada.

## V-220 — Migração Neon, ACU e release de produção 27

30/09/2026. Os bancos `cica_main` e `cica_knowledge` do Fly foram congelados, exportados e restaurados no projeto Neon `raspy-river-46466568`, branch `production`. Antes do corte, origem e destino tiveram contagens e hashes de conteúdo idênticos em todas as tabelas: principal `33B79A8EC27464DDA34EFEFF4EB3CABB968AAED690023B685820B3D7F82E1DBE` e knowledge `147888225D4AD3E6F8B14462065E6B9580D1C50CEBE5E6C18B5F3A855FF709F5`. Os dois aliases Django foram verificados no Neon; runtime usa pooler e a release usa conexão direta. O PostgreSQL antigo do Fly permanece ligado e intocado para rollback.

A release 27 concluiu migrations nos dois bancos e está `complete`: web e worker estão iniciados, o check Fly passa e `/api/v1/health/ready/` responde 200. O smoke autenticado no tenant Bianchi retornou 200 para certificados, NFS-e, empresas e o detalhe aberto a partir da própria lista; o 404 de empresa pausada foi corrigido. A coleta preservou os 56 checkpoints e cresceu de 3.238 para 14.452 documentos, com sucesso registrado nas 56 sincronizações. Uma falha 404 legada foi convertida para retentativa; 404, 429, falhas de transporte e 5xx usam backoff sem bloquear as demais empresas.

O exportador foi exercitado em produção sobre um XML fiscal real: encontrou/criou exatamente uma tag local `ACU`, conferiu o código e manteve o hash do XML original. Casos sintéticos cobriram `ACU` aninhada em profundidade arbitrária, namespace, `prod` e XML sem `prod`. Regressão integral: 993 aprovados, 3 skips conhecidos e 29 subtestes; regressão posterior do detalhe: 33 aprovados e 2 subtestes. Ruff, MyPy, Django check, migrations check e sintaxe JavaScript passaram. O pacote continua sem homologação de importação no Domínio enquanto Q-39 estiver aberta.

## V-221 — PostgreSQL legado do Fly desligado

30/09/2026. Após reconfirmar dentro da máquina web que `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `KNOWLEDGE_DATABASE_URL` e `KNOWLEDGE_DATABASE_URL_UNPOOLED` apontam ao Neon, a máquina `7817961a377e68` de `cica-contabil-db` foi parada. Ela não foi destruída e o volume foi preservado. Depois do desligamento, `/` e `/api/v1/health/ready/` responderam 200, web e worker permaneceram iniciados, `SELECT 1` passou nos aliases `default` e `knowledge`, 14.552 NFS-e foram lidas do Neon e os logs não apresentaram erro de conexão, traceback ou HTTP 500.

## V-231 — Regressão PostgreSQL preparada no CI e configuração isolada testada

01/10/2026. O workflow `verify` passa a preparar serviço PostgreSQL 17 com digest da imagem local validada em V-230, credenciais exclusivamente sintéticas, health check e porta 55432. Após SQLite e antes de construir imagens, executa toda a suíte com `config.settings.test_postgresql`, sem `continue-on-error`. Não se alteraram gatilhos, permissões de repositório, credenciais de produção ou publicação. Referência: [GitHub — serviço PostgreSQL em runner Linux](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers).

Sete testes novos passaram (2,68 s): porta ausente, padrão, fora do intervalo ou inválida é recusada; modo de serviços externos é recusado; URLs de banco de produção são ignoradas em favor do loopback explícito, com cache/e-mail locais e tarefas eager. YAML foi parseado e verificadas a porta coincidente, a imagem fixada, ausência de tolerância a falha e ordem antes dos builds. Isso não é validação pelo motor do GitHub Actions: actionlint não estava instalado e nenhum pipeline remoto foi disparado. A regressão de execução PostgreSQL de V-230 continua a evidência local; primeira execução Linux/CI publicada permanece pendente. Sem custo externo gerado e sem deploy.

## V-230 — Regressão PostgreSQL, locks fiscais e migração com histórico

Regressão integral após correções: **1.012 testes e 39 subtestes aprovados**, um skip (Playwright Python opcional), em 193,77 s. As provas de concorrência de reserva de tokens e geração recorrente executaram sem skip. A migração de histórico 0066→0067→0066→0067 também passou no PostgreSQL. Ruff global, MyPy (221 arquivos) e diff check passaram. Os **três testes adicionais de projeção simultânea passaram** em execução separada (32,18 s), com quatro conexões por cenário. Identidade/rótulo do contêiner reconfirmados; contêiner encerrado e ausência confirmada. Somente os dados sintéticos em tmpfs foram descartados; nenhum arquivo ou banco do projeto foi removido.

01/10/2026. Docker local e imagem PostgreSQL 17 já disponíveis. Criado somente `cica-goal-pg-v230`, rótulo `cica.task=goal-validation-v230`, dados em tmpfs e porta dinâmica 58429 vinculada a 127.0.0.1. Usada a configuração `test_postgresql`, que mantém cache/e-mail locais e substitui somente bancos de teste. Sem Neon, dados reais ou fornecedores.

A primeira regressão PostgreSQL encontrou 65 falhas, 946 aprovações e um skip. Causa de aplicação confirmada: as projeções de Guias, DCTFWeb e Parcelamentos para atividades usavam FOR UPDATE também sobre o solicitante opcional carregado por outer join. Aplicado D-154 às três consultas: lock explícito da linha fiscal, preservando transação e lock separado da atividade. [Django — select_for_update](https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update) confirma a restrição de relações opcionais. Não foi alterado resultado fiscal ou autorização.

Outras falhas eram do teste: fechar FileResponse diretamente encerrava a conexão PostgreSQL dentro do TestCase; agora o teste consome o streaming pelo cliente Django e verifica o cabeçalho ZIP. O teste de ativação futura de tokens passou a fixar a data de referência, pois a virada para outubro invalidava sua premissa. A regra comercial permanece intacta.

Novo teste de migração usa MigrationExecutor para ir de 0066 a 0067 com 1.001 notas históricas, verificar vínculo completo e preservação de manifesto/hash/caminho, reverter e verificar que o registro original permanece. A preparação inicialmente esqueceu os estados mais recentes de outros apps; corrigida para conservar seus leaf nodes. SQLite e PostgreSQL aprovaram esse teste. Adicionada e aprovada prova PostgreSQL parametrizada para quatro projeções simultâneas sem solicitante em cada módulo fiscal, verificando atividade única e idempotência de eventos.

Limites: esta entrega não altera telas, não aciona Serpro, não homologa fiscalmente e não publica. Restaurar schema de teste não é ensaio de restauração/rollback de produção nem prova de capacidade sob carga real.

## V-229 — Pacotes NFS-e: lista e download na mesma fronteira de acesso

Regressão final desta rodada: `pytest -q` aprovou **1.009 testes e 39 subtestes**, com três skips, em 105,89 s. Skips: Playwright Python opcional (MCP usado nesta rodada), locks PostgreSQL em recorrência e em cobrança de tokens. `ruff check src runtime tests`, `mypy src runtime` (221 arquivos), `makemigrations --check --dry-run --settings=config.settings.test` e `git diff --check` passaram. Isso não substitui os dois testes de concorrência PostgreSQL nem homologações externas.

30/09/2026. Encontrada exposição de metadados de pacotes fora da carteira: o download revalidava o escopo, mas a listagem consultava todos os pacotes do tenant. D-212 adiciona vínculo relacional pacote/notas e aplica contagens de notas acessíveis e vinculadas no SQL antes da paginação. Pacotes mistos, sem vínculo completo ou com nota fora do tenant não são listados nem baixados. Acesso é reavaliado a cada requisição; criação também recusa seleção vazia, duplicada ou de outro escritório. O download trata IDs de manifesto malformados com 404. A consulta da lista não carrega os snapshots completos.

A migração 0067 reconstrói vínculos de manifestos legados em lotes de 500 IDs, somente no banco principal, sem tocar conteúdo fiscal. Casos inválidos/missing/cross-tenant ficam fechados. Migração aplicada no SQLite QA e nas bases de teste; backfill testado com dados válidos, malformados, inexistentes e de outro tenant, além de repetição idempotente. Antes de publicar, coordenar a troca dos escritores: impedir novos pacotes pelo código antigo durante o backfill ou repetir a reconstrução após a troca. PostgreSQL publicado ainda não recebeu a migração.

UI/UX Pro Max orientou estado vazio com caminho de saída; Watermelon não retornou bloco pertinente para `permission filtered history`/`download history`. Referências: [Karbon — privacidade de contatos](https://help.karbonhq.com/en/articles/2848946-overview-of-privacy) (conteúdo consultado na pesquisa anterior; nova abertura retornou 403) e [Django — migrações e múltiplos bancos](https://docs.djangoproject.com/en/5.2/howto/writing-migrations/). Sem mudança de layout: o vazio diz `Nenhum pacote disponível nesta carteira` e explica a abrangência, sem afirmar que nenhum pacote existe no escritório. Guidelines Vercel atuais auditadas: texto de estado, ação nativa, foco, conteúdo responsivo e paginação de estado na URL.

Verificação focal: 12 testes/sete subtestes de exportação existentes e quatro novos testes/três subtestes de autorização passaram. MyPy, Ruff e detecção de migrações passaram. Playwright MCP com colaborador sintético limitado confirmou dois pacotes permitidos e download por teclado em 1440/390 px; após trocar sua carteira, nenhum pacote foi mostrado e o estado vazio levou à aba Notas. Foco de 3 px, sem overflow ou erro de console no percurso autorizado. Um acesso inicial sem módulo NFS-e corretamente retornou 403, antes de configurar o cenário sintético. Browser/servidor encerrados e permissões QA restauradas. Sem deploy nem homologação fiscal.

## V-228 — Histórico NFS-e de empresa pausada sem reativar operação

30/09/2026. D-207/D-211: cadastro, detalhe, recorte explícito de NFS-e e recuperação de pacote usam o mesmo limite de visibilidade histórica. Proprietário/administrador sem restrição pode consultar a empresa pausada e baixar suas notas classificadas; a carteira operacional permanece somente ativa. CRMew, colaborador e suporte restrito não ganham escopo adicional. A tela identifica a pausa, explica consulta/download, oferece retorno ao cadastro e não oferece edição do acumulador que seria recusada pelo servidor. Limpar filtros preserva a empresa; sair dela continua uma ação explícita.

Pesquisa: Watermelon sem resultado pertinente em `archived records`/`archive`; UI/UX Pro Max não trouxe padrão específico de arquivo, e a busca focada seguinte orientou feedback de estado (não adotadas sugestões móveis fora de contexto). [Shopify — arquivar pedidos](https://help.shopify.com/en/manual/products/inventory/purchase-orders/creating-purchase-orders) fundamentou separar registro histórico de operação ativa e identificar o estado. Sem redesign. Web Interface Guidelines atuais revisadas para o template alterado: links nativos, foco visível, estado na URL, mensagem contextual, nomes de ações e estado vazio sem prometer nova coleta.

Validação: 61 testes e nove subtestes de empresas/NFS-e passaram; após ocultar edição em pausadas, o teste específico foi reexecutado e passou. Cobertura inclui consulta/download histórico e novo ZIP, manutenção da empresa pausada, recusa de ativação de coleta e 404 para colaborador restrito. Ruff e MyPy passaram. Playwright MCP confirmou 1440/390 px, 83 notas sintéticas, download concluído em ambos, novo download pelo histórico, foco de 3 px, navegação por teclado ao cadastro, filtro sem resultado e limpeza preservando o ID. Sem overflow ou novos erros de console no percurso final. Uma primeira tentativa com proprietário restrito devolveu 404 esperado; o cenário de proprietário irrestrito foi validado separadamente. Browser e servidor QA encerrados; fixture local restaurada.

Limites: sem deploy, sem acesso a dados reais e sem nova homologação Q-39. O estado sem nenhum documento total tem cobertura de template, mas não foi percorrido no navegador nesta rodada. Demais telas e ampliação de histórico para perfis restritos não foram declaradas concluídas.

## V-227 — Atalhos de empresa com recorte exato de NFS-e

30/09/2026. Links de revisões da lista e detalhe de Empresas deixaram de pesquisar pelo nome e passam um ID de empresa validado dentro do escopo autorizado. A NFS-e identifica o recorte, preserva-o no formulário, nos atalhos de situação e na paginação, e aplica a mesma restrição ao download. A ação `Ver toda a carteira` remove explicitamente o recorte. Na demonstração, a seleção global passa a dizer `Todas desta empresa` quando aplicável.

UI/UX Pro Max: deep linking, estado ativo e filtros; Watermelon sem correspondência em `contextual navigation` e `filtered list`. Referências: [Shopify — perfil de cliente](https://help.shopify.com/en/manual/customers/manage-customers?lang=en-US) e [NN/g — navegação contextual](https://www.nngroup.com/articles/local-navigation/), adotando identificação da entidade e estado na URL. Web Interface Guidelines atuais auditadas: links nativos com nome acessível, filtro identificado e persistido, anúncio da abrangência e caminho explícito de saída.

Playwright MCP percorreu o atalho por teclado em 1440 e 390 px, confirmou um único grupo de empresa, mudança de situação mantendo ID, seleção global com escopo correto e retorno à carteira completa. Atalho `Ver classificadas` preservou o ID. Sem overflow ou erros de console. Três testes e sete subtestes passaram: duas empresas homônimas permanecem separadas no resultado e no ZIP; ID inválido e empresa de outro escritório retornam 404. Ruff, MyPy e sintaxe JS passaram. Browser e servidor encerrados. Limites: empresas pausadas fora do escopo operacional ainda precisam de revisão específica; sem publicação ou nova validação com dados reais.

## V-226 — Empresas: busca tolerante e erros de cadastro visíveis

30/09/2026. D-211 reabriu a tela de Empresas. A busca aceita CNPJ numérico e alfanumérico sem pontuação; continua limitada à carteira autorizada. O contador mostra resultados/total quando há filtro, empresa pausada recebe rótulo na lista, e os filtros de certificado descrevem a regra real (`Válido por mais de 30 dias` e `Sem A1 válido`). Adicionado submit explícito como alternativa à busca automática. Erro de cadastro agora mantém modal aberto, preserva valores, foca campo inválido e associa a mensagem via aria-describedby; o CNPJ inválido já era recusado pelo formulário e o defeito era ocultar o erro.

Pesquisa prévia: UI/UX Pro Max para busca sem resultado e recuperação; Watermelon sem correspondência em `customer directory` e `directory`. Referências: [Shopify — busca de clientes](https://help.shopify.com/en/manual/customers/customer-search), [Karbon — busca de clientes](https://developers.karbonhq.com/guides/searching-clients/) e [Receita — CNPJ alfanumérico](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico). Mantidos layout e componentes existentes, tolerância à pontuação e retorno ao filtro. Web Interface Guidelines atuais auditadas: controles nativos, anúncio de contagem, erro associado, foco, teclado e responsividade.

Playwright MCP percorreu desktop 1440 e celular 390 px: CNPJ só com números retorna uma empresa, abrir/voltar preserva pesquisa, vazio mostra zero/total e caminho Ver todas. Cadastro inválido no celular mantém modal, foca CNPJ, mostra mensagem, fecha por Escape e retorna foco ao botão. Captura mobile do filtro inspecionada: sem overflow, IDs duplicados ou erro de console. CNPJ alfanumérico e isolamento cobertos por testes, sem alegação de nova prova visual de empresa pausada. Resultado final: 22 testes e dois subtestes aprovados; Ruff, MyPy e diff check aprovados. Browser e servidor QA encerrados. Mudanças locais, sem deploy.

## V-225 — Histórico de downloads e falha de abertura do ZIP

30/09/2026. O histórico passou a usar nomes de tarefa, esconder o código interno de destino, recolher identificação técnica e oferecer `Preparar novo download` com destino direto à seleção. A situação visível `Download solicitado` evita afirmar que o navegador concluiu a transferência. A leitura do arquivo agora precede a marcação de download; `OSError` e arquivo ausente retornam ao histórico com orientação de tentar novamente ou preparar novo pacote.

UI/UX Pro Max orientou recuperação com próxima ação. Watermelon não retornou `download history` nem `file list`. Pesquisa: [Shopify](https://help.shopify.com/en/manual/your-account/users/csv-exports) e [Google Takeout](https://support.google.com/accounts/answer/3024190?hl=en-GB), adotando distinção entre arquivo e dados e caminho explícito para obter novo arquivo, sem copiar prazos de expiração. Web Interface Guidelines atuais auditadas: controles nativos, nome acessível por pacote, detalhe recolhido, teclado, foco de 3px e erro com próxima ação.

Playwright MCP validou histórico com dados sintéticos em 1440 e 390 px, novo download do ZIP, destino do link para seleção e abertura da identificação por Enter; sem overflow ou erro de console. Navegador e servidor QA encerrados. Ruff de src/tests, MyPy, Django check e migrations check passaram. Fly somente consultado: web e worker versão 31, web check passando; publicação não realizada.

A primeira regressão integral terminou com 1.000 aprovados, três skips conhecidos e 36 subtestes, mas duas falhas: asserção do título antigo do histórico e divergência da emissão de guia pelo proprietário demo. A asserção foi alinhada ao novo título; o proprietário demo agora usa a mesma emissão fictícia por sessão que o visitante, sem chamar o serviço persistente. Teste percorre emissão e PDF, confere que a guia compartilhada permanece READY e que o PDF exige progresso da sessão. Os quatro testes focados passaram. Regressão integral final: 1.002 testes e 36 subtestes aprovados em 109,97 s; três skips conhecidos (browser opcional e dois casos de locks PostgreSQL), sem alegar sua execução.

MyPy ampliado para src/runtime encontrou tipagem ambígua no validador de corpus. A normalização de company_id/reference_period passou a usar variáveis textuais explícitas, preservando os limites e comportamento. Seis testes do runner passaram; MyPy aprovou 221 arquivos e Ruff aprovou src/runtime/tests. Sem execução de treinamento, chamada de IA ou alteração de dados externos.

## V-224 — Lote NFS-e entre páginas e recusa de seleção inválida

30/09/2026. A continuação de D-211 verificou a implementação em tenant local comum, com 165 notas sintéticas classificadas em duas empresas e duas páginas. Playwright MCP validou 1440 e 390 px, seleção parcial por empresa, limpeza dessa seleção ao escolher todos os resultados e download iniciado na segunda página: ZIP gerado com 165 documentos, também confirmado no histórico. O checkbox parcial revelou que a atualização anterior havia sido inserida em outro handler; o código foi corrigido e o asset versionado novamente. Removido também um bloco NFS-e indevido no handler de guias. O botão de empresa agora declara expressamente que inclui as notas desta página. Sem overflow nos estados inspecionados e console atual sem erros. Navegador e servidores QA encerrados.

O servidor agora recusa datas impossíveis, intervalo invertido, competência inválida, modo desconhecido, UUID inválido e seleção parcialmente indisponível, em vez de ampliar o filtro ou gerar lote parcial silencioso. O erro mantém a URL e orienta a conferir período e seleção; a mensagem foi percorrida pelo navegador. Dois testes focados e sete subtestes passaram, assim como Ruff, MyPy e sintaxe JavaScript. A regressão mais ampla NFS-e concluiu com 23 testes e sete subtestes aprovados em 58,73 s, incluindo recuperação de arquivo privado ausente.

A pesquisa complementar consultou [seleção em lote da Shopify](https://help.shopify.com/en/manual/shopify-admin/productivity-tools/bulk-actions?lang=en-US), mantendo a distinção página/resultados. As referências e a consulta Watermelon da mesma tela constam em V-223; as Web Interface Guidelines atuais foram consultadas novamente. Limites: dados exclusivamente sintéticos, sem publicação ou homologação no Domínio. Falha de rede durante transferência e desempenho de carteiras maiores continuam sem validação.

## V-223 — Descoberta do download NFS-e e reauditoria de usabilidade

30/09/2026. D-211 reabre todas as telas pelo critério de facilidade de uso. Primeira passagem: acesso `Baixar notas em lote` no cabeçalho, seção com orientação contextual, ação `Baixar selecionadas (ZIP)`, explicação para filtro vazio ou sem notas classificadas, uma única aba ativa e seleção por empresa sincronizada com seleção parcial/página/filtro. Q-39 permanece aberto; o ZIP continua um pacote de conferência.

Pesquisa prévia: UI/UX Pro Max recomendou seleção múltipla, barra de ações e feedback. Watermelon não encontrou `table bulk actions` nem `data table`; buscas Refero/SaaSFrame não trouxeram exemplo útil. Referências: [Conta Azul](https://ajuda.contaazul.com/hc/pt-br/articles/115007774727-NF-e-como-acessar-e-fazer-o-download), [Conexa](https://ajuda.conexa.app/pt/articles/4843030-como-baixar-xml-e-pdf-da-nota-fiscal) e [Carbon](https://v10.carbondesignsystem.com/components/data-table/usage/). Adotados acesso no cabeçalho, operação junto à lista e seleção explícita. Busca de stack HTML sem correspondência; preservados os componentes existentes. Web Interface Guidelines atuais auditadas: links nativos, destino focável, foco visível, margem da âncora, alvo de 44px e anúncio da seleção.

Playwright MCP local: desktop 1440×900 e celular 390×900/844; teclado Enter, foco de 3px, seleção/desmarcação, filtro vazio e limpeza, abas e downloads fictícios de emitidas/tomadas concluídos. Sem overflow ou erros de console; sem IDs duplicados no desktop. Captura mobile inspecionada; navegador encerrado. Não houve nova inspeção visual do lote por empresa em tenant real ou falha de rede no download; não é homologação fiscal nem teste de carga.

Regressão encontrou pasta mensal calculada em UTC antes da virada do mês local. Exportador corrigido com conversão local e teste determinístico setembro/outubro. Resultado final: 29 testes aprovados; Ruff, sintaxe JavaScript e diff check do escopo aprovados. Mudanças locais, sem publicação nesta passagem.

## V-222 — Compute Neon orientado por trabalho real

30/09/2026. Antes da mudança, o endpoint `ep-late-sun-b6qhbv1r` permanecia ativo com `suspend_timeout_seconds=0` e consumia aproximadamente 900 CU-segundos por hora, o equivalente ao mínimo de 0,25 CU continuamente. Produção confirmou triagem desativada, modelo multimodal desativado, zero anexos pendentes, zero reconciliações esperando e zero relatórios esperando; NFS-e era o único trabalho contínuo real, com 59 sincronizações habilitadas.

O check Fly passou de readiness para liveness, sem remover `/api/v1/health/ready/`. Recuperação de reconciliação e relatórios, retry de anexos e coleta NFS-e foram alinhados em janelas de 15 minutos; os fluxos normais continuam enfileirando imediatamente após commit. Triagem e reconciliação Claude desativadas deixaram de entrar no beat. O retry de anexos sem analisador retorna antes de criar `OperationalRun`. O Neon foi configurado para suspender após 300 segundos, mantendo autoscaling 0,25–1 CU.

Validação local: 62 testes focados e depois 61 testes focados aprovados; Ruff, MyPy, Django check, migrations check e diff check passaram. A suíte integral teve 999 aprovados, 3 skips conhecidos, 29 subtestes e uma falha alheia: o teste legado ainda espera o PDF fictício de guia removido pela tela atual. A release 30 comprovou o novo health. Na release 31, o builder remoto perdeu autenticação, repetiu o build e o `flyctl` terminou com erro interno depois de aplicar a versão; a máquina principal do worker foi explicitamente iniciada e validada. Estado final: web e worker na versão 31, check liveness passando, readiness com banco/cache `ok`, Celery `pong` e `SELECT 1` nos aliases `default` e `knowledge`.

A medição horária do Neon após a mudança registrou 708, 702, 833, 608, 883 e 387 CU-segundos entre 19:00 e 01:00 UTC, período que incluiu dois deploys e coleta NFS-e real. A hora mais tranquila caiu de cerca de 900 para 387 CU-segundos, redução observada de aproximadamente 57%. O resultado não é promessa de fatura fixa: backlog, usuários e sincronizações legitimamente mantêm o banco ativo; a economia aparece somente na ociosidade.

## V-232 — Demo de Parcelamentos e confirmação DCTFWeb

01/10/2026, continuação local D-211. Visitante e membro autorizado demo agora usam simulações por sessão em Parcelamentos e lote DCTFWeb, sem serviços persistentes, tokens ou alteração de registros compartilhados. Permissões de execução preservadas e operações restritas à carteira. O formulário enviava acordo localizado (480.523), recusado pelo servidor; campos de identificador usam agora unlocalize. Ação fictícia oculta para perfis sem execução.

Pesquisa anterior: UI/UX Pro Max (feedback), Watermelon sandbox simulation/demo sem correspondência, [Stripe testing](https://docs.stripe.com/testing) e [simulação de assinaturas](https://docs.stripe.com/billing/testing/test-clocks/simulate-subscriptions). Adotados isolamento, aviso inequívoco e confirmação sem promessa de documento oficial, preservando layout. Web Interface Guidelines atuais consultadas e ambos os templates auditados: controles nativos, rótulos explícitos, feedback de envio e foco visível.

Playwright MCP: consulta/emissão pela conta demo em desktop 1440px e estado resultante mobile 390px; Enter e foco de 3px. Confirmação DCTFWeb inspecionada nos dois tamanhos, sem overflow, confirmação por teclado e mensagem final. Aberta por POST local controlado: descoberta na carteira não validada nesta passagem. Console final sem erros; sessão registrou 404 da rota digitada incorretamente durante QA e favicon dessa página de erro. Navegador encerrado.

64 testes focados passaram antes do ajuste de identificador; quatro casos repetidos depois passaram usando valor extraído do HTML para emitir. Ruff global e MyPy em 221 arquivos passaram. Sem publicação, fornecedor ou homologação. Consulta individual DCTFWeb, descoberta do lote e estados reais de fila/erro ainda exigem reauditoria.

## V-233 — Consulta DCTFWeb individual e descoberta na carteira

01/10/2026, D-211. A consulta individual demo passou a usar o mesmo progresso por sessão do lote, para visitante e membro autorizado, sem chamar o serviço persistente. Registros compartilhados não aparecem como resultado da sessão. O botão agora descreve simulação; a tela não promete PDF inexistente nem efeito oficial. Competência inválida é recusada antes de efeitos; custo enviado usa identificador numérico não localizado. A carteira ganhou acesso “Consultar documentos” na linha das guias DCTFWeb, preservando empresa e competência.

Pesquisa prévia: UI/UX Pro Max submit feedback (carregamento e resultado); busca de stack HTML sem correspondência após repetição. Watermelon document status não encontrou bloco; status retornou footer não pertinente, descartado. Refero/SaaSFrame não forneceram analogia útil; referência concreta [Stripe testing](https://docs.stripe.com/testing) orientou isolamento e explicação de simulação, preservando os componentes existentes. Auditoria dos dois templates contra Web Interface Guidelines atuais: ações/links nativos, contexto acessível por documento/empresa, feedback de envio, números enviados sem localização, estado final e erro com próxima ação. Sem redesenho ou novas dependências.

Playwright MCP local: login demo, carteira → Consultar documentos → declaração simulada por Enter → recibo simulado → retorno à carteira → estado conservado. Desktop 1440px e mobile 375px; foco de 3px e sem overflow. Captura móvel inspecionada; competência 13/2026 redireciona com orientação. Console sem erros. Navegador e servidor QA encerrados. Não percorreu estados reais de fila/erro/incerteza, tema escuro ou o caminho do lote.

Regressão final: 50 testes aprovados em 72,25 s, incluindo visitante público, membro, auditor, isolamento entre sessões, ausência de documento persistido e competência inválida. Primeira execução teve uma falha de configuração do teste (flags de demo não habilitadas); corrigida e suíte repetida integralmente. Ruff global e MyPy em 221 arquivos aprovados. Sem publicação, Serpro, consumo ou homologação fiscal.

## V-234 — Descoberta e revisão de lote DCTFWeb

01/10/2026, D-211. A revisão do lote fica visível sem seleção; a tela explica limite de 30, escopo da página e perda da seleção ao trocar de página. Perfis somente de consulta não recebem seleção/envio. Correção de centavos localizados no formulário de autorização; UUIDs canonicalizados antes de deduplicar e competência /0000 recusada.

Referências prévias: UI/UX Pro Max bulk selection e grid gaps; [Shopify](https://help.shopify.com/en/manual/shopify-admin/productivity-tools/bulk-actions?lang=en-US) e [Helios](https://helios.hashicorp.design/patterns/table-multi-select). Adotados contagem, escopo explícito e ação junto à tabela; sem copiar seleção global, pois o lote mantém limite 30. Watermelon bulk actions/table sem resultados; Refero/SaaSFrame sem exemplo útil. Web Interface Guidelines atuais aplicadas ao escopo alterado em guides_center.html, dctfweb_bulk.html, hub.js, operations.css e versões de assets no workspace: semântica, rótulos, feedback, foco e layout responsivo. A inspeção visual encontrou sobreposição no mobile; grid passou a uma coluna e a captura foi repetida, com separação geométrica comprovada.

Playwright MCP em QA não-demo, sem sockets externos, fonte sintética de 2.945 apurações: desktop 1440px e mobile 375px, ação visível antes da seleção, erro sem seleção, 30 selecionadas, parcial 29, Enter/foco 3px e prévia correta. No mobile, um recibo selecionado chega à revisão de um item. Ausência de contrato bloqueia autorização e não exibe botão de execução; nenhum contrato/preço foi inventado. Sem overflow ou erros de console nos estados inspecionados. Navegador e servidor QA encerrados.

110 testes/11 subtestes passaram em 62,38 s, incluindo custo 1234 preservado, UUID duplicado com caixa diferente e recusa de lote inválido sem serviço/consumo. Ruff global, MyPy 221 arquivos e sintaxe JS passaram. A última mudança CSS foi repetida no navegador. Sem publicação, consulta paga, tema escuro ou estados de provedor inspecionados nesta rodada. Fila/erro/incerteza e documento disponível continuam pendentes de QA renderizado; homologação real permanece separada.

## V-235 — Estados DCTFWeb, atualização e regressão completa

01/10/2026, D-211. Fixture reutilizável scripts/qa_dctfweb_states.py restrita ao SQLite .tmp/ui-review e escritório QA não-demo cria cinco estados sintéticos sem fornecedor. Processamento ganhou “Atualizar resultado”, link GET que mantém empresa/competência, sem serviço ou consumo. Fila e processamento têm mensagens distintas. Retorno incerto mantém bloqueio de nova consulta e exibe registro para conciliação. Download ganhou nome acessível com tipo do documento.

UI/UX Pro Max orientou feedback de estado; [GitHub workflow history](https://docs.github.com/en/actions/how-tos/monitor-workflows/view-workflow-run-history) serviu de referência para acompanhar uma execução sem iniciar outra. Watermelon loading status vazio/status retornou footer descartado; Refero/SaaSFrame sem analogia útil. Layout existente preservado. Web Interface Guidelines atuais auditadas no template: link nativo, contexto na URL, nome acessível, estado anunciado, erro orientado, sem repetição automática ou nova animação.

Playwright MCP: cinco estados (fila, consultando, disponível, falha e incerto), cada um em 1440 e 375px, sem overflow/erro de console. Download efetivo de PDF sintético de 1390 bytes, resposta 200 e assinatura PDF. Atualização por Enter, foco 3px, estado preservado; modo escuro/movimento reduzido inspecionados adicionalmente na fila mobile, não em todos os estados. Capturas de disponível claro e fila escura revisadas. A falha de certificado é mensagem sintética, sem contrato para repetir; não houve execução de recuperação paga. Uma chamada de verificação inicialmente usou URL relativa sem base e foi corrigida para URL local absoluta. Navegador e servidor QA encerrados.

Regressão completa antes do último ajuste de acompanhamento: 1.025 testes e 43 subtestes aprovados em 112,39 s; seis skips explícitos (um browser opcional, cinco casos que requerem PostgreSQL). Após ajuste: 23 testes DCTFWeb e quatro subtestes aprovados em 55,52 s, incluindo atualização sem serviço/mutação/consumo e incerto sem form de repetição. Ruff global/fixture, MyPy 221 arquivos e diff check passaram. Não representa teste de carga, homologação Serpro, publicação ou nova regressão PostgreSQL.

## V-245 — Aparência resiliente a token CSRF renovado (01/10/2026)

D-214. Os logs de produção registraram três POSTs em `/app/aparencia/` recusados por token
incorreto, descartando a hipótese de domínio ausente ou origem não confiável. Uma sessão nova
no domínio público completou a troca de tema, isolando o defeito a uma aba com token anterior.
O seletor agora solicita ao endpoint CSRF existente um valor atual antes do POST; a política
`HttpOnly`, o middleware e o método POST permanecem. A falha residual usa resposta CICA 403,
sem motivo interno, com retorno validado ao mesmo host; referer externo é descartado e `/api/`
continua JSON.

Pesquisa prévia: UI/UX Pro Max já aplicada na rodada; Watermelon não encontrou bloco para
`error 403 session expired retry` nem template `error page`. A documentação oficial do Django
confirma a rotação no login e recomenda `CSRF_FAILURE_VIEW`; GOV.UK orientou título direto,
linguagem sem jargão, efeito sobre os dados e próxima ação clara. As Web Interface Guidelines
atuais foram reaplicadas ao template, bases e script alterados: título específico, um H1,
link real de recuperação, alvos de 44 px, foco existente, sem animação nova ou conteúdo técnico.

Playwright local adulterou deliberadamente o campo para `stale-token`: o navegador obteve
`GET /api/v1/auth/csrf/` 200, enviou `/app/aparencia/` com 302 e voltou à Visão geral com o
tema escuro. O fallback forçado preservou 403 e exibiu a recuperação CICA em 375×911 e
1440×900; o retorno apontou para `/app/`, sem overflow. O único erro de console foi o próprio
documento 403 intencional. A repetição final aprovou 18 testes de UI/API em 59,61 s, `node
--check`, Ruff, MyPy e diff check.

Publicação Fly versão 34 concluída com release command, web/worker iniciados e check passing.
No domínio real, um campo deliberadamente trocado por `stale-token` produziu refresh CSRF 200,
POST 302 e tema escuro aplicado sem sair da landing. Um POST artificial sem a correção do
cliente comprovou o fallback CICA 403 e retorno para a origem; o seletor dentro do fallback
renovou o token, aplicou tema claro e voltou à landing. Liveness e readiness responderam 200,
com banco/cache `ok`. O warning CSRF adicional nos logs é a simulação 403 intencional desta
validação, não uma falha espontânea posterior.

## V-244 — Filtro de competência dos fechamentos recomposto (01/10/2026)

D-211. O filtro mensal da Visão geral deixou de alinhar rótulo, input nativo e botão como três
itens concorrentes. Rótulo, controle e erro agora formam um campo vertical; no desktop o campo
fica limitado a 260 px e a ação curta acompanha sua base, enquanto no celular ambos ocupam a
largura disponível. O `input type=month` recebeu contorno completo, raio e cores explícitas em
vez do acabamento nativo inconsistente. A ação informa `Atualizando…` e bloqueia repetição
somente depois do submit.

Pesquisa anterior à decisão: UI/UX Pro Max retornou rótulo visível e dimensões consistentes de
input/botão; Watermelon não encontrou bloco após `date filter form` e retry `date range filter`.
As orientações do [GOV.UK para inputs](https://design-system.service.gov.uk/components/text-input/)
reforçaram rótulo curto acima do controle e erro junto ao campo; o
[Atlassian Date Picker](https://atlassian.design/components/calendar/usage) confirmou preservar
entrada nativa/teclado em formulários, sem transformar o mês em um rótulo interativo. O design
system e os tokens existentes do CICA foram preservados.

Auditoria de `closing_dashboard.html`, trecho de `operations.css` e versão do asset em
`workspace.html` contra a fonte atual das Web Interface Guidelines: label associado, nome e
autocomplete, estado na URL, erro descritivo preservado, submit habilitado até a requisição,
feedback de envio, foco visível por teclado, alvos de 44 px, hover do botão e ausência de
overflow. Nenhuma violação material observada no recorte alterado.

Playwright MCP: desktop 1440×900 claro/escuro e mobile 375×812 escuro com movimento reduzido.
Desktop resultou em campo 260×44 px e botão 133×44 px; mobile em 309×44 px para ambos, uma
coluna e sem overflow. Tab alcançou o mês com outline de 3 px. Competência inválida manteve
`aria-invalid`, `aria-describedby`, valor corrente e próximo passo; `Enter` em 09/2026 atualizou
a URL e o resumo para setembro. Console sem erros. Não houve mutação operacional ou fonte
externa.

Validação automatizada: 38 testes e 12 subtestes de `test_operational_center.py` passaram em
32,43 s; depois da asserção final de markup/feedback, o teste específico passou em 31,54 s.
`git diff --check` aprovado. A chamada acidental de Ruff sobre HTML produziu somente erros de
parser esperados e não é registrada como validação do template. Sem publicação.

## V-243 — Conciliação encontrável em carteiras extensas (01/10/2026)

D-211. A central não-demo agora expõe a jornada real como **1. Importar, 2. Processar,
3. Revisar e 4. Exportar**, mantém a entrada de importação visível mesmo quando já há dados e
preserva as restrições por papel. Configuração, importação, filtro de movimentos e exportação
passaram a usar busca progressiva por nome ou código Domínio. Digitar nunca escolhe a primeira
correspondência: somente clique ou `Enter` confirma; sem JavaScript, o `select` nativo permanece
disponível. O resultado anuncia total e limite exibido, aceita setas, `Enter` e `Esc`, mantém o
foco no combobox e não troca o contexto silenciosamente.

Pesquisa prévia: UI/UX Pro Max para autocomplete, teclado e progressive disclosure; Watermelon
sem composição pertinente após `searchable select`/`combobox` e `import export workflow`/`import`.
Refero e SaaSFrame não devolveram um fluxo verificável nas buscas focadas. Foram então usados o
[WAI-ARIA APG Combobox](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/), a sequência oficial
de importação e revisão do [Xero](https://central.xero.com/0/article/Import-an-OFX-bank-statement),
a conciliação orientada pelo extrato do [QuickBooks](https://quickbooks.intuit.com/learn-support/en-us/help-article/statement-reconciliation/reconcile-account-quickbooks-online/L3XzsllsK_US_en_US)
e a separação entre relatório e fluxo contábil da [Ramp](https://support.ramp.com/exporting-your-data-to-csv/).
Deles foram adotados seleção explícita de conta/empresa, importação antes da revisão, etapa de
conferência e distinção explícita da exportação operacional, sem copiar marca ou composição.

Auditoria dos oito arquivos de interface contra a fonte atual das Web Interface Guidelines.
O botão de importar deixou de ficar desabilitado antes da tentativa: continua acionável e leva
o foco ao campo ausente com instrução concreta; durante o envio real, continua bloqueado com
`aria-busy`. Não foram observadas outras violações materiais nos arquivos alterados.

Playwright MCP no escritório QA sintético de 240 empresas, desktop 1440×1000 e mobile 375×812,
tema claro/escuro, movimento reduzido, teclado e fallback sem JavaScript. Foram percorridos os
quatro passos, abertura persistente da importação, busca/seleção explícita, zero resultado,
filtro preservado na URL, bloqueio Q-39 da exportação e configuração válida/inválida. O primeiro
`Esc` fecha somente a lista e o segundo fecha o modal. A tentativa sem arquivo mantém o botão
acionável, explica os formatos e foca o input de arquivo. Não houve overflow; o console teve
somente o 400 intencional da empresa inválida, sem exceção JavaScript.

Validação automatizada: **51 testes e 24 subtestes** do módulo passaram em 35,13 s; `node
--check`, Ruff, MyPy e diff check aprovados. A regressão integral imediatamente anterior (V-242)
permanece em 1.039 testes/139 subtestes, mas não foi repetida após os ajustes exclusivamente de
interface desta rodada. Nenhum arquivo bancário foi enviado, nenhuma exportação Domínio foi
gerada, não houve homologação Q-39, teste de carga, banco real ou publicação.

## V-242 — Configuração da Conciliação: empresa inequívoca e recuperação segura (01/10/2026)

D-211. A configuração não-demo deixou de substituir silenciosamente uma empresa inválida,
inacessível ou repetida pela primeira empresa da carteira. O GET inicial sem filtro ainda abre
a primeira empresa autorizada; qualquer seleção explícita inválida devolve 400, mantém apenas
o seletor e explica que nada foi alterado. POST exige exatamente uma empresa autorizada no
corpo e não herda a query string. Ações desconhecidas e identificadores ausentes, malformados
ou repetidos são recusados antes de consultar ou alterar registros. Erros de formulário agora
incluem razões gerais, links para os campos, associação por `aria-describedby` e preservação
dos valores informados.

Pesquisa prévia: UI/UX Pro Max completa, buscas Error Recovery e select overflow; Watermelon
sem composição para recuperação após busca focada, com retry `error` e referência `error-1`
para explicar o problema e oferecer recuperação. Refero não trouxe exemplo verificável;
SaaSFrame apresentou agrupamento de configurações em Luma, Formcarry, Meiro, Claude e fluxo
de importação/exportação do Pirsch. [Stripe Dashboard basics](https://docs.stripe.com/dashboard/basics)
reforçou dados e filtros no contexto da conta; [GOV.UK Error summary](https://design-system.service.gov.uk/components/error-summary/)
orientou resumo focável, erro em linha, instrução de correção e preservação da entrada. A
composição CICA existente foi mantida.

Auditoria integral dos arquivos alterados contra a fonte atual das Web Interface Guidelines:
template principal, partial dos cadastros e CSS específico. Foram corrigidos estouro do select
com nomes longos no celular, alvo de recuperação para 44 px, resumo do período e erro geral de
duplicidade. Não restou violação material observada; controles continuam nativos, rotulados,
com foco visível e funcionamento sem JavaScript.

Playwright MCP no escritório QA sintético de 240 empresas: desktop 1440×1000 e mobile 375×812,
tema escuro e movimento reduzido. Empresa inválida devolveu 400, título e próximo passo claros,
foco de 3 px, seletor 309×44 px, nenhum formulário mutável nem overflow. Período invertido
preservou datas, marcou o fim com `aria-invalid`, associou o texto de erro, e o link do resumo
moveu o foco ao campo. Fluxo sem JavaScript e paisagem 812×375 já haviam sido percorridos na
mesma rodada. Console apresentou apenas o 400 intencional, sem exceção JavaScript. Browser e
servidor QA foram encerrados ao final.

Validação automatizada: 96 testes e 96 subtestes de Conciliação/seed demo passaram; após o
ajuste final de erros gerais e associação do período, quatro testes focados e 24 subtestes
passaram em 29,66 s. Ruff, MyPy da view e diff check passaram. Regressão SQLite completa:
**1.039 testes e 139 subtestes aprovados, seis skips explícitos, em 108,81 s**. Os skips são
um navegador Python opcional e cinco provas de locks/transações que exigem PostgreSQL; a suíte
não substitui essas provas. Não houve banco real, arquivo bancário, publicação ou homologação
externa.

## V-241 — Conciliação demo: limites também por URL direta (01/10/2026)

D-211. Guard comum recusa leitura e escrita da família avançada `reconciliation_*` no escritório demo, antes de entrar nas views e consultar configuração, auditoria, fontes, execuções, movimentos ou exportações. Vale para membro e visitante; central e confirmação fictícias continuam separadas e isoladas por sessão. Resposta 403 explica o limite e oferece link nativo direto “Voltar à conciliação demo”, sem sugerir renovação de permissão, integrações ou nova tentativa. Escritório não-demo mantém seus fluxos.

Pesquisa prévia: UI/UX Pro Max completa e Error Recovery (próximo passo claro); stack sem correspondência específica após retry, não adotado. Watermelon `access denied` sem resultado; retry `error` e entrada `error-1` confirmaram padrão de explicação/recuperação (catálogo não forneceu código). Refero/SaaSFrame sem analogia verificável. [Stripe Sandboxes](https://docs.stripe.com/sandboxes) orienta separação da simulação e [GOV.UK páginas de problema](https://design-system.service.gov.uk/patterns/problem-with-the-service-pages/) orienta alternativa concreta, sem copiar mensagem de falha temporária para um limite permanente. Layout CICA preservado.

Teste inicialmente vermelho comprovou entrada na view de configuração GET (mock de contexto acionado; não foi falha real de produção). Após o guard: **94 testes aprovados e 72 subtestes**, 50,83 s, cobrindo Conciliação e seed demo. Novos casos descobrem as 12 rotas avançadas e verificam GET/POST para visitante, proprietário e auditor; contexto operacional não é chamado e central permanece 200. Ruff, MyPy de views e diff check aprovados. **Regressão completa SQLite: 1.037 testes e 115 subtestes aprovados, seis skips, 115,01 s.** Skips: um browser Python opcional e cinco testes de locks/transações PostgreSQL. PostgreSQL não foi reexecutado nesta rodada.

Auditoria da skill Web Design Guidelines, fonte Vercel atual lida integralmente: `src/apps/hub/templates/hub/forbidden.html:1` — sem violação material após revisão completa. Novo retorno usa link semântico, nome específico e URL interna fixa; demais ramos preservados. Título, hierarquia, skip link, foco, hover, quebra e tokens herdados conferidos. Não há novo formulário, animação ou estado assíncrono.

Playwright MCP local: recusa 403 para membro demo, retorno por Tab/Enter à comparação em desktop 1440 e mobile 375, foco 3px; landscape 812×375 com foco inteiramente visível; sem overflow. Tema claro e escuro/reduced-motion inspecionados, capturas desktop/mobile vistas. Contraste medido no tema claro: texto 6,17:1, botão 9,68:1. Console apresentou somente os 403 esperados das navegações bloqueadas, sem exceção JavaScript observada. Escritório QA não-demo abriu Configuração com status 200 e seis formulários; sem envio. Browser e servidor QA encerrados. Fluxos reais completos, suporte no navegador e todas as demais páginas de erro não foram reexecutados visualmente. Sem publicação, arquivo bancário real ou homologação.

## V-240 — Conciliação demo por sessão e comparação acessível (01/10/2026)

D-211. Listagem, confirmação fictícia e recusa de upload agora dependem de office.is_demo, preservando autorização por perfil. Membro não segue para confirmação persistente; auditor não ganha botão nem POST. A demo abre a comparação disponível diretamente, sem abas vazias ou carregar `_reconciliation_v2_context` compartilhado. Limite de importação/exportação explícito; navegação completa continua no escritório não-demo. Estado de busca sem resultados conserva a existência de extratos fictícios e orienta filtros; perfil somente leitura não recebe a falsa indicação “Evidência registrada” para correspondência ainda não confirmada.

Pesquisa anterior: UI/UX Pro Max completa, confirmation feedback pertinente; stack forms sem correspondência após retry. Watermelon reconciliation/confirmation sem resultados; Refero/SaaSFrame sem analogia verificável. [Stripe testing](https://docs.stripe.com/testing) e [automated testing](https://docs.stripe.com/automated-testing) como referências de simulação explícita sem efeito real. Sem novo estilo; componentes existentes preservados. Web Interface Guidelines atuais lidas integralmente e template completo auditado: hierarquia, semântica, labels, confirmação contextual, foco, estados, navegação e limites de simulação. Endpoints avançados ainda exigem revisão separada.

5 casos de isolamento primeiro aprovados; depois 91 testes de Conciliação e seed demo passaram em 47,48 s. Após ajuste final “Apenas consulta”/formatação, repetidos cinco casos de membro/visitante/auditor/upload em 31,52 s, todos aprovados. Mock confirmou ausência de chamada ao serviço de confirmação compartilhado; DB sem matches persistidos, segunda sessão sem progresso, auditor POST 403, upload 403 sem fonte criada. Ruff dos arquivos Python, MyPy de views e diff check passaram. Não foi repetida a suíte integral nesta rodada (última V-239).

Playwright MCP: demo membro em desktop 1440 e mobile 375; abrir comparação por Enter/foco 3px, cancelar com restauração de foco, confirmar fictícia e consultar evidência; segunda sessão da mesma conta permanece sem confirmação. Busca vazia inicialmente mostrou código antigo no servidor QA sem autoreload; reiniciado e confirmado o texto orientado. Escritório QA não-demo preservou cinco abas e Nova importação visível. Sem overflow/erros de console nos estados inspecionados. Segundo contexto usou dark/reduced-motion, mas sem auditoria visual completa de contraste; não declarar cobertura de todos os estados/temas. Contextos e servidor encerrados. Sem arquivo bancário real, Domínio, publicação ou homologação.

## V-239 — Indicador da Central Integra consistente com DTE (01/10/2026)

Repetição final completa SQLite: **1.031 testes aprovados, 43 subtestes aprovados, seis skips explícitos**, em 108,98 s. Skips: um browser Python opcional e cinco casos de locks/transações PostgreSQL; não é nova regressão PostgreSQL. Nenhuma falha restante nessa execução.

D-212: Central Integra aceitava lotes parcialmente visíveis no contador e só usava sessão para visitante demo. Corrigida para `_visible_pending_dte_runs` no escritório real e mesmo helper de sessão da fila para qualquer membro demo autorizado. Preparo demo misto/duplicado/malformado/vazio não vira lote parcial impossível de confirmar. A Central não calcula histórico concluído para obter apenas o contador, evitando as consultas de mensagens por resultado nesse caminho. Sem template/CSS novo.

Pesquisa: UI/UX Pro Max completa, busca de feedback de status pertinente apenas à coerência da resposta; stack semantic html/structure não trouxe correspondência específica. Watermelon status count sem resultado, status trouxe footer descartado. Refero sem exemplo pertinente, SaaSFrame permissões sem analogia de contador adotada. Referência funcional [Stripe Dashboard search](https://docs.stripe.com/dashboard/search): escopo dos dados corresponde às contas acessíveis. Sem nova direção visual. Guidelines Vercel atuais lidas integralmente; template existente da Central e seu CSS inspecionados, links semânticos e foco preservados.

Playwright MCP: membro demo desktop 1440 e mobile 375; Central → Abrir Caixa DTE por Enter/foco 3px → preparar → Central contador 1 → retirar → contador 0. Duas sessões da mesma conta confirmaram 1 na primeira/0 na segunda. Sem overflow ou erro de console. Contextos e servidor QA encerrados. Casos de carteira não-demo restrita e progresso inválido são testes de integração, não homologação externa nem login restrito no navegador.

Regressão inicial completa: 1.030 aprovados, 43 subtestes, seis skips (um browser Python opcional/cinco dependentes de PostgreSQL), uma falha de fixture que declarava zero empresas para um item. Corrigida a fixture para total_companies=1, mantendo o requisito de escopo consistente; suíte completa repetida. Ruff global e MyPy dos 218 arquivos de src passaram. Sem produção, migração, consumo ou Serpro.

## V-238 — Descoberta da preparação DTE (01/10/2026)

D-211: ações essenciais estavam após a lista e recolhidas. Adicionados atalhos nativos no topo para escolher empresas e revisar consultas existentes; preparo sempre aberto, etapas 1/2 identificadas, alvos com foco e margem para cabeçalho fixo. Âncoras preservam filtros e seleção sem GET/POST. Perfil somente leitura não recebe atalho de preparo e tem orientação explícita. Demo anuncia seleção fictícia sem Serpro/consumo/cobrança. Busca/atalhos auxiliares só aparecem quando o JS está disponível; checkboxes e envio continuam nativos. Estado Preparando… usa mecanismo existente de bloqueio de dupla submissão.

Pesquisa anterior à edição: UI/UX Pro Max lida integralmente, buscas discovery/action sem correspondência específica; stack flex-wrap usada somente para adaptação responsiva. Watermelon page header/toolbar sem resultados; Refero/SaaSFrame sem analogia verificada. [GOV.UK Details](https://design-system.service.gov.uk/components/details/) fundamentou não esconder informação essencial; [GitHub execução manual](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow) exemplifica entrada acima da lista, seleção de escopo e execução separadas; [Shopify Polaris Page](https://shopify.dev/docs/api/app-home/latest/web-components/layout-and-structure/page) orientou ação principal e secundária no cabeçalho, sem importar componentes. Web Interface Guidelines atuais lidas integralmente; template, CSS e JS revistos: links nativos, rótulos/etapas, foco, estados, cores existentes, wrapping, nenhum movimento novo e funcionamento progressivo.

Playwright MCP: desktop 1440, mobile 375 e paisagem 812×375; atalho por Enter transfere foco, mantém status=unread e checkbox; preparo → revisão por atalho → simulação → histórico. Seleção vazia foca mensagem orientadora. Demo mobile escura/movimento reduzido e capturas claras/escuras inspecionadas, sem overflow/erros de console. Contexto sem JS: atalho e seleção por Tab/Espaço funcionam; busca auxiliar escondida. Busy state verificado por evento submit local (disabled/aria-busy/texto), não por transporte lento ponta a ponta. Duas tentativas de interceptar POST no harness falharam (setTimeout indisponível/espera de navegação); interceptações removidas, estado recarregado e contextos encerrados. Espera inicial de âncora pressupunha topo <200px, mas padding global + margem deixam ~220px visíveis abaixo do cabeçalho; critério corrigido por evidência visual, sem ajuste artificial do layout.

Novo teste cobre CTA antes da caixa, preparo não recolhido mesmo com mensagens, GET sem consulta criada, revisão após preparo e ausência de CTA para auditor. Primeira asserção inspecionava todos os details do shell e foi limitada à seção correta; depois 13 testes DTE passaram. Ruff do teste, sintaxe Node e diff check aprovados. Sem produção, fornecedor, consumo ou homologação. Servidor QA e sessões do navegador encerrados.

## V-237 — Fila DTE e carteira atual (01/10/2026)

Confirmada consulta da fila pendente somente por tenant, sem exigir carteira completa no GET/POST. Corrigidos lista, contador e decisão por helper SQL comum: todos os itens precisam pertencer ao escritório e ao escopo atual, com quantidade positiva consistente. Lote misto não é exposto parcialmente. Teste cobre empresa alheia, lote misto/vazio, total inconsistente, revogação entre requisições, ausência de botões/nomes e POST direto 404 sem chamar serviços de aprovação/cancelamento.

`pytest tests/test_dte.py -q`: 12 aprovados em 56,49 s. Ruff dos dois arquivos Python e MyPy da view passaram; diff check sem erro (avisos preexistentes CRLF). Não alterados templates, CSS ou layout. UI/UX Pro Max lida; busca permissions sem correspondência específica, retry disabled states pertinente; stack sem resultado verificado. Watermelon permissions vazio e access retornou autenticação, não autorização de lotes. Refero/SaaSFrame sem exemplo pertinente; referência adotada de separação de capacidades: https://docs.stripe.com/get-started/account/teams/roles. Guidelines atuais Vercel lidas integralmente e template DTE existente inspecionado; não há novo controle visual nesta alteração.

Playwright MCP local: inbox demo e escritório QA não-demo com 240 empresas sintéticas, desktop 1440 e mobile 375; filtro Enter com foco 3px, estado vazio e bloqueio sem CNPJ/credenciais, sem overflow nem console errors. Restrição da carteira validada no teste de integração, não em sessão restrita no navegador; nenhuma aprovação externa ou estado real de fornecedor exercitado. Navegador e servidor QA encerrados. Continua pendente a descoberta da preparação e auditoria dos indicadores em outras entradas. Sem publicação, consumo ou homologação Serpro.

## V-236 — DTE demo: isolamento e confirmação

Repetição após o último ajuste de centavos no template da central: 11 testes test_dte.py aprovados em 55,19 s; diff check do escopo aprovado.

01/10/2026, D-211. Preparação, decisão de fila, exibição de histórico/teor e bloqueio de paginação externa usam escritório is_demo, não apenas visitante. Removida gravação de DteMessageAccess compartilhado pela conta demo. A abertura exige permissão e confirmação; progresso fica na sessão. Histórico vazio deixa de afirmar ausência de consulta preparada quando há uma esperando autorização. Custos ocultos dos dois formulários DTE usam unlocalize para preservar centavos.

Pesquisa: UI/UX Pro Max confirmation messages, [MOJ Confirm an action](https://design-patterns.service.justice.gov.uk/patterns/confirm-an-action/) como inspiração experimental de contexto antes da confirmação, [GOV.UK Button](https://design-system.service.gov.uk/components/button/) e [Stripe testing](https://docs.stripe.com/testing). Preservados resumo, confirmação explícita e aviso de simulação; sem mudança da regra jurídica. Watermelon confirmation dialog/dialog sem resultados; SaaSFrame retornou catálogo, sem copiar layout. Busca de stack forms/form validation sem resultado verificado; usadas semântica HTML e convenções locais. Web Interface Guidelines atuais aplicadas aos dois templates: controles rotulados, required, feedback Abrindo…, foco, estados vazios e valores de máquina.

Playwright MCP: conta demo em desktop 1440px e mobile 375px, resumo → checkbox obrigatório → abertura por Enter com foco 3px, retorno, preparação de uma empresa, simulação e retirada. Segundo contexto com a mesma conta confirmou teor ainda fechado e fila privada; histórico vazio correto com consulta pendente. Sem overflow ou erro de console nos estados inspecionados. A primeira tentativa de selecionar empresa encontrou details recolhido; fluxo continuou pela abertura do summary nativo. Ambos os contextos e servidor QA encerrados.

65 testes focados DTE/demo passaram em 70,37 s; primeira execução revelou asserção legada que exigia o registro compartilhado, substituída por ausência de persistência e progresso de sessão. Novos casos exercitam entrada pública/membro, duas sessões, recusa de sessão alheia, confirmação ausente e auditor. Ruff global e MyPy 221 arquivos passaram. Sem produção, Serpro, ciência, consumo ou homologação real. Campos de excedente não foram exercitados com contrato real; descoberta e escopo das consultas pendentes não-demo continuam na reauditoria.

## V-246 — Demo operacional povoada em produção (01/10/2026)

D-213. Release Fly **33**, imagem `registry.fly.io/cica-contabil:deployment-01M3VWWSRMJWTN25TFTEKX0H3Y`, publicada por canary sobre a imagem exata da release 32 e somente seis arquivos desta entrega. O comando de release `python manage.py seed_demo_operations --slug escritorio-demo` concluiu com sucesso. Web e worker iniciados, health passing, standby preservado. Nenhuma migração, recurso recorrente novo ou consulta a fornecedor foi necessária.

Inventário do tenant demo antes: oito empresas, 24 NFS-e, dez mensagens DTE, três guias e zero atividades/modelos/evidências. Depois: **84 atividades, seis modelos, 42 atribuições, três personas sintéticas, 60 evidências e 168 eventos**; empresas e registros fiscais existentes mantiveram suas contagens. Repetição publicada retornou `created: 0`. A rotina é transacional e recusa tenant operacional; não redefine senhas, não sobrescreve evidência e não chama serviço externo. Cenários abrangem setembro e outubro/2026, quatro áreas e cinco estados de trabalho. Os prazos são internos ilustrativos. Não foi criado agendamento de renovação automática.

Meu trabalho passa a representar Ana Martins para visitante/administrador demo, respeitando o recorte autorizado: nove atividades abertas na entrada, 33 na Carteira/Gestão. Visitantes temporários não aparecem nos filtros/distribuição. O detalhe informa que as atividades são cenários de consulta; POSTs ficam bloqueados também para membro demo. Isso não amplia nem homologa operações fiscais reais.

Validação: 43 testes focados e 72 subtestes; regressão integral final **1.046 testes e 139 subtestes aprovados, cinco skips PostgreSQL, 145,80 s**. A primeira regressão revelou fixture que supunha operador único (corrigida para a identidade explícita); uma falha de paginação do Console passou na repetição isolada e integral sem mudança de produto. Ruff do escopo, MyPy, Django check, migrações e diff check passaram. PostgreSQL concorrente não foi reexecutado nesta entrega.

Skills UI/UX Pro Max, landing-page-design e Web Design Guidelines consultadas. Watermelon `portfolio-dashboard` reforçou a organização por prioridade/categoria; SaaSFrame Latitude e Karbon Tasks orientaram hierarquia/responsável/prazo, preservando o design da CICA. Refero não expôs exemplo verificável; buscas stack HTML/Tailwind não tiveram resultado. Fonte Vercel atual lida integralmente e os dois templates alterados auditados, sem violação material nova. [Resumo, referências e limites](docs/cica-demo-population-2026-10-01.md).

Playwright MCP local e publicado: Meu trabalho, Carteira, Gestão, filtro de impedidas, detalhe, evidência de conclusão, vazio e erro de competência. Produção respondeu 200 nas seis combinações 1440/375 px, sem overflow, console errors ou contas de outros visitantes na Gestão. Teclado/Enter e foco de 3 px verificados. Tema escuro/movimento reduzido e capturas publicadas desktop/mobile inspecionados. Sem JavaScript e paisagem 812 px foram verificados localmente, não reexecutados em produção. Não há nova operação assíncrona; carga, fontes e permissões externas não são abrangidas. Capturas `.playwright-mcp/demo-production-1440.png`, `demo-production-375.png` e `demo-production-dark.png`. Todas as abas/contextos abertos para a tarefa foram fechados; o servidor QA exclusivo 8015 foi encerrado.
## V-247 — Página inicial orientada à próxima ação (01/10/2026)

D-215. A Visão geral deixou de repetir estados técnicos em uma tabela densa. O topo agora explica
o recorte e a próxima ação; escopos descrevem o que incluem; os quatro indicadores são filtros
inteiramente acionáveis; e a agenda responde atividade, empresa, prazo relativo/exato e exceção
útil. Responsável aparece somente em Carteira/Gestão. A lista mostra dez itens por página e os
fechamentos ficam recolhidos, com abertura e paginação preservadas na URL. Nenhuma prioridade,
permissão ou estado de negócio foi alterado.

Pesquisa prévia: UI/UX Pro Max (hierarquia, legibilidade e responsividade); Watermelon sem
correspondência após busca focada e retry; Linear My Issues/Display options, Asana My Tasks,
Karbon My Week/cards e Pageflows Process Street. Refero e SaaSFrame foram consultados, sem fluxo
equivalente verificável fora do acesso pago. As decisões adotadas foram foco diário, Today/
Upcoming, detalhe sob demanda, propriedades essenciais e recuperação contextual. A fonte atual
das Web Interface Guidelines foi lida integralmente; os arquivos finais foram auditados quanto
a semântica, nomes acessíveis, foco, alvos, texto real no DOM, URL, reflow e estados.

Playwright MCP percorreu o escritório QA sintético em desktop 1280/1440, mobile 375, tema escuro
e movimento reduzido: visão pessoal, Carteira, filtro Hoje, paginação 10/4, detalhe nativo de
fechamentos por teclado, erro de competência e estado vazio. Não houve overflow; alvos ficaram
com pelo menos 44 px, título/contexto mobile com 17/15 px, foco visível de 3 px e console sem
erros. Capturas desktop, mobile e dark foram inspecionadas. O browser já não estava disponível
na retomada final; o servidor QA foi encerrado. Loading segue a navegação nativa, pois não foi
introduzida operação assíncrona.

Validação automatizada final: **1.047 testes e 139 subtestes aprovados**, seis skips explícitos,
em 125,92 s; cinco skips exigem locks/transações PostgreSQL e um usa Playwright Python opcional.
Depois do isolamento do CSS, 137 testes e 19 subtestes focados passaram em 58,64 s. Ruff, MyPy,
Django check e `makemigrations --check --dry-run` passaram. Sem consulta fiscal, mutação de
tenant real ou homologação externa. Publicação será registrada separadamente se executada.

Publicação concluída na Fly como release **37**, imagem mínima
`registry.fly.io/cica-contabil:dashboard-v247`, derivada da release 34 e contendo somente view,
template, partial e CSS da dashboard. Release command concluiu; web e worker iniciaram, health
passing, standby preservado e readiness retornou banco/cache `ok`. No domínio real, a entrada
demo respondeu POST 302 → `/app/` 200; o HTML confirmou “Meu trabalho”, resumo “Comece por…”,
prazo relativo, fechamento recolhido, ausência da tríade técnica e o CSS versionado respondeu
200. A validação visual publicada não foi repetida porque nenhum browser estava disponível na
retomada; a renderização equivalente foi inspecionada localmente antes da publicação.

## V-248 — NFS-e em lote legível e pacote por empresa (01/10/2026)

D-216. A reauditoria começou na produção e confirmou que a ação “Baixar notas em lote”, os
filtros, a seleção por página/carteira e os dois downloads já estavam publicados. O defeito
funcional encontrado estava dentro do ZIP: os diretórios eram gravados como `0106 -`, sem o
nome prometido da empresa. Pacotes novos da demonstração e do fluxo não-demo agora usam
`código - nome da empresa`, com código/nome normalizados contra separadores, segmentos vazios e
caracteres de controle. Manifesto e fotografia usam o mesmo caminho; XML, acumulador, escopo e
o bloqueio de homologação Q-39 não mudaram.

No celular, a central recebeu tipografia mínima legível no cabeçalho, abas, filtros, instruções,
resumo da seleção, grupos e tabela; inputs usam 16 px, ações principais 44 px e a composição
continua sem overflow. A pesquisa prévia usou UI/UX Pro Max e os padrões públicos de seleção em
massa do Linear, Google Drive, Carbon e MUI: checkbox explícito, barra contextual após seleção,
contagem/escopo antes da ação e distinção entre página e conjunto completo. Watermelon não
retornou composição pertinente na busca focada nem no retry estreito; as referências foram
adaptadas ao design, às permissões e à linguagem da CICA. A fonte atual das Web Interface
Guidelines foi lida integralmente e os dois arquivos de interface foram reauditados.

Playwright MCP local percorreu desktop 1280, celular 375, paisagem 812, claro/escuro, movimento
reduzido, teclado/foco, filtro vazio, loading, falha de rede com fallback, seleção e downloads de
emitidas/tomadas. Produção repetiu desktop/mobile, tema escuro, seleção de 24 notas/6 empresas e
os dois ZIPs; os diretórios e `manifesto-classificacao.csv` exibiram, por exemplo,
`0106 - Oficina Motor Forte`. Não houve overflow nem aviso/erro de console nas superfícies
inspecionadas. Capturas de produção: `.playwright-mcp/nfse-v248-production-mobile.png` e
`.playwright-mcp/nfse-v248-production-dark.png`. Browser e servidor QA foram encerrados.

Validação automatizada: **147 testes e 82 subtestes focados**; regressão integral com **1.048
testes e 139 subtestes aprovados**, seis skips explícitos, em 137,15 s. Ruff, MyPy, Django check
e `makemigrations --check --dry-run` passaram. Release Fly **38**, imagem mínima
`registry.fly.io/cica-contabil:nfse-v248`, derivada da release 37 com quatro arquivos; release
command, web, worker, health, liveness e readiness passaram, com banco/cache `ok`. Nenhuma fonte
fiscal, tenant operacional, cobrança ou homologação Domínio foi acionada.

## V-249 — Coleta NFS-e orientada à ação (01/10/2026)

D-217. A tela de coleta agora apresenta uma única situação operacional: o topo distingue a
simulação, resume prontas/em operação/precisando de ação e oferece o próximo passo; a fila separa
aguardando, coletando e exceções; certificado ausente é bloqueio explícito; configuração fica
secundária e expansível. Na demo, ativar/pausar/repetir altera somente a sessão e uma empresa sem
A1 válido não pode ser ativada. O endpoint da fila expõe `simulated` e `requires_action`.

Pesquisa: UI/UX Pro Max; Watermelon sem resultado em uma busca focada e um retry estreito;
GitHub Actions, Microsoft Power Platform e AWS Step Functions para estado, falha e repetição.
A fonte atual das Web Interface Guidelines foi lida e os arquivos alterados foram auditados.
Playwright local cobriu desktop/mobile, claro/escuro, movimento reduzido, teclado, foco, falha e
recuperação, sem overflow. O browser automatizado ficou indisponível após a publicação; portanto,
a produção foi validada por sessão demo HTTP, HTML e assets, sem alegar inspeção visual final.

Testes focados: 11 aprovados; Ruff, MyPy, Node, Django check e migrações passaram. Release Fly
**43**, imagem `registry.fly.io/cica-contabil:nfse-v249-assets`: release command, web, worker,
liveness e readiness responderam corretamente. A demo publicada confirmou dashboard com nove
abertas, fila 200 com 3 aguardando e 4 bloqueadas por A1, CSS/JS novos e ausência do antigo
`content-visibility:auto`. Releases 39–41 revelaram manifesto estático incompleto; houve rollback
imediato para a 42 e a build completa da 43 recompôs 218 arquivos/634 pós-processados. Q-39,
fonte fiscal real, carga e piloto permanecem fora desta evidência.

## V-251 — Política de senha mínima de 8 caracteres (01/10/2026)

D-219. Cadastro, ativação e redefinição agora aceitam oito caracteres no servidor e no
navegador; sete continuam recusados. Argon2, bloqueio de tentativas e os demais validadores
permanecem ativos. Playwright local conferiu desktop 1280 e mobile 375, tema escuro, movimento
reduzido, `minLength=8`, erro com sete e sucesso com oito, sem overflow; browser encerrado.

## V-252 — NFS-e com movimento, retenções e `infNFSe/valores/acum` (01/10/2026)

D-220 a D-222. A central agora diferencia **Saída · serviço prestado**, **Entrada · serviço
tomado** e **Tipo a confirmar**, com filtro próprio, contraparte conforme o papel fiscal, emissão,
competência, serviço, valor, retenções explícitas e acumulador. A demo contém os dois movimentos;
o lote único separa automaticamente `Emitidas/CÓDIGO-/` e `Tomadas/CÓDIGO-/`. O parser de novas
coletas só define o movimento quando o CNPJ da empresa coincide inequivocamente com prestador ou
tomador, prioriza `dhProc`, lê `acum` e não inventa tipo ou tributo ausente.

O exportador derivado usa somente a tag minúscula `acum` em `infNFSe/valores`, preserva namespace,
elimina `ACU` legado da cópia e rejeita XML sem um único `infNFSe`. O original criptografado
permanece imutável. O adaptador passa a `nfse-conference-acum-v2`; Q-39 continua aberto, portanto
o ZIP segue sendo pacote de conferência, não importação Domínio homologada.

Pesquisa e auditoria: UI/UX Pro Max; Watermelon sem resultado após busca focada e retry; Domínio
para prestados/tomados, leiaute nacional para `prest`/`toma`, Xero para separação compra/venda e o
projeto autorizado HubCobalchini para papéis, `dhProc`, competência e retenções. A fonte atual das
Web Interface Guidelines foi reaplicada aos arquivos finais.

Playwright MCP validou desktop 1440/1280, mobile 375, tema escuro, movimento reduzido, teclado e
foco, filtro de entradas (12/12 linhas), retenções expansíveis, seleção/lote, estado vazio e
ausência de overflow ou erros de console. Capturas: `.playwright-mcp/nfse-accountant-mobile.png`
e `.playwright-mcp/nfse-accountant-desktop-dark.png`. Abas e servidor QA na porta 8010 foram
encerrados; o servidor preexistente do usuário na porta 8000 não foi alterado.

Validação final: **1.066 testes e 139 subtestes aprovados**, seis skips explícitos, em 138,38 s.
A primeira regressão revelou nove fixtures sintéticas ainda no formato NFe/raiz; elas foram
convertidas à estrutura NFS-e válida e os nove percursos passaram antes da repetição integral.
Ruff, MyPy, Django check, `makemigrations --check --dry-run` e `git diff --check` passaram. Nenhuma
fonte fiscal, tenant real, publicação ou cobrança foi acionada.

## V-253 — Acumuladores localizáveis e histórico de pacotes operacional (01/10/2026)

D-223. A aba Acumuladores passou a pesquisar empresa, código, descrição e origem no banco,
paginar 50 registros e explicar que cadastro manual disponibiliza uma escolha sem criar regra
automática. A demonstração remove o formulário sem efeito e mantém o catálogo legível. A aba
Exportações agora mostra quantidade de notas e empresas, período, gerador, primeiro download,
código de conferência, busca, situação e recuperação quando o arquivo privado não existe.

Playwright MCP cobriu catálogo e exportações com estado vazio e povoado, filtros, download,
arquivo ausente, desktop 1440, celular 390, escuro, movimento reduzido, teclado/foco e zero
overflow ou erro de console. Captura inspecionada: `artifacts/nfse-exports-desktop-v223.png`.
Validação automatizada: **1.067 testes, 139 subtestes e seis skips**; Ruff, MyPy, Django check e
migrações passaram. A evidência é local; nenhum pacote, tenant ou infraestrutura real mudou.

## V-254 — Relatórios de retenções NFS-e em PDF e XLSX (01/10/2026)

D-224. A área de notas ganhou um bloco direto de “Relatório para conferência fiscal”, com PDF e
Excel aplicados à empresa, busca, situação, movimento e período visíveis. O recorte aceita até
5.000 notas e inclui documentos ainda não classificados. Os dois formatos trazem empresa, nota,
entrada/saída, emissão, competência, contraparte, serviço, valor, ISS, PIS, COFINS, CSLL, IRRF,
INSS e total. O total é sempre a soma dos seis valores explicitamente normalizados; o valor
agregado legado não decompõe nem substitui tributos. Texto fiscal iniciado por `=`, `+`, `-` ou
`@` é neutralizado no XLSX. Geração e download são locais, privados, sem cache e auditados.

O PDF foi renderizado e inspecionado em todas as páginas; uma página final vazia encontrada na
primeira composição foi eliminada. Amostras finais: `artifacts/nfse-retencoes-sample.pdf`,
`artifacts/nfse-retencoes-final-page-1.png` e `artifacts/nfse-retencoes-final-page-2.png`. O XLSX
foi reaberto e validado com abas Resumo/Notas, filtros, cabeçalho congelado, datas/moedas tipadas
e fórmulas de total; `@oai/artifact-tool` e LibreOffice não estavam disponíveis, portanto não se
alega renderização visual da planilha. Amostra: `artifacts/nfse-retencoes-sample.xlsx`.

UI/UX Pro Max, referências oficiais da NFS-e Nacional e o HubCobalchini autorizado orientaram a
entrega; Watermelon não encontrou composição após busca focada e retry. A fonte atual das Web
Interface Guidelines foi relida e os arquivos finais passaram na auditoria. Playwright MCP
inspecionou o bloco renderizado em 1440/390 px, claro/escuro, movimento reduzido, foco de 3 px,
alvos de 44 px e ausência de overflow. Ações de download foram provadas pelo cliente Django e
pela leitura real dos binários; a página visual foi servida como fotografia autenticada porque a
sessão do servidor QA não pôde ser reutilizada pelo browser. Nenhum erro/aviso surgiu na página
limpa; abas e servidor QA foram encerrados.

Validação focada: **41 testes e sete subtestes aprovados**. A regressão integral terminou com
**1.068 testes, 139 subtestes e seis skips aprovados em 137,74 s**. Ruff, MyPy, Django check e
`makemigrations --check --dry-run` passaram. Nenhuma fonte fiscal, cálculo tributário implícito,
tenant real, publicação ou cobrança foi acionada. Q-39 e a homologação fiscal/contábil com amostra
real continuam abertas.

## V-255 — Histórico NFS-e de empresa pausada em consulta segura (02/10/2026)

D-225. A rota explícita pela empresa agora apresenta um aviso curto de histórico somente para
consulta, mantém notas, pacotes e relatórios baixáveis e aponta ao cadastro para consultar a
situação. Coleta, classificação e edição de acumulador continuam bloqueadas. O indicador deixou de
prometer “Classificar” nesse estado e uma revisão aberta legada já acompanhada de acumulador não é
mais contada como “para classificar”. A empresa pausada segue ausente da carteira operacional sem
filtro explícito; proprietário/administrador sem escopo restrito conserva o histórico, enquanto
operador com carteira explícita recebe 404 e também não consegue baixar pacote antigo.

Pesquisa prévia: UI/UX Pro Max orientou estado por texto além de cor, semântica e texto curto;
Watermelon não encontrou composição após busca focada e retry. GitHub (repositório arquivado),
Slack (canal arquivado), Jira (espaço arquivado) e QuickBooks (cliente inativo em relatórios)
fundamentaram o padrão de histórico pesquisável e sem nova atividade. A fonte atual das Web
Interface Guidelines foi relida; template e CSS finais foram auditados sem achado material.

Playwright MCP percorreu a página sintética em 1440 e 390 px, tema escuro, movimento reduzido,
teclado/foco de 3 px, aviso responsivo, filtro vazio, seleção e download ZIP real. Não houve
overflow na tela válida nem erro/aviso no console de uma aba limpa; ações de classificação não
existiam e PDF/Excel continuavam disponíveis. O 404 técnico de `DEBUG=True` não foi usado como
prova visual de produção. Capturas: `.playwright-mcp/nfse-paused-desktop.png` e
`.playwright-mcp/nfse-paused-mobile-dark.png`. Abas e servidor QA foram encerrados. Evidência
exclusivamente sintética. Validação focada: **27 testes e sete subtestes aprovados**; regressão
integral: **1.068 testes, 139 subtestes e seis skips aprovados em 152,28 s**. Ruff, MyPy, Django
check e `makemigrations --check --dry-run` passaram. Nenhuma fonte fiscal, tenant real, publicação
ou cobrança foi acionada.

## V-256 — Recuperação global segura para erros web (02/10/2026)

D-226. Os handlers 400, 403, 404 e 500 foram registrados na URL raiz e agora devolvem páginas CICA
com status HTTP correto e ação de recuperação. O 404 não confirma se um recurso protegido existe;
o 403 não reflete a exceção; o 500 não expõe detalhe interno e possui um fallback HTML final que
não depende de template, contexto, banco ou reversão de URL. Caminhos `/api/` permanecem JSON.
Todas as respostas recebem `Cache-Control: private, no-store` e `X-Content-Type-Options: nosniff`.

Pesquisa prévia: UI/UX Pro Max orientou recuperação, próximo passo e foco; Watermelon não retornou
template na busca inicial, mas ofereceu sete blocos de erro no retry, dos quais três foram
inspecionados. GitHub Docs fundamentou o 404 neutro para conteúdo privado; MDN, o status HTTP real;
Slack e Atlassian, mensagem curta e ação direta. A fonte atual das Web Interface Guidelines foi
reaplicada a `error_page.html`, `auth_base.html` e `cica-auth.css`; sem achado material.

Playwright MCP percorreu 404 em 1440 × 900 e 403/500 em 390 px, claro/escuro, movimento reduzido,
teclado, foco visível de 3 px, alvos de 49 px, retorno por Enter e ausência de overflow. A página
inicial respondeu 200 após a recuperação e todos os assets responderam 200. O único registro de
console foi o status esperado do próprio documento 403/404/500; não houve falha JavaScript ou de
asset. Browser e servidor QA foram encerrados, e os scripts temporários foram removidos.

Validação focada: **sete testes aprovados em 32,01 s**. Regressão integral: **1.075 testes e 139
subtestes aprovados, seis skips explícitos, em 149,97 s**. Ruff, MyPy, Django check,
`makemigrations --check --dry-run` e a auditoria de interface passaram. Nenhum tenant, dado real,
fonte externa, publicação ou cobrança foi acionado.

## V-257 — Conciliação recupera importações interrompidas (02/10/2026)

D-227. A próxima ação da Conciliação não-demo agora prioriza execução parada em mapeamento, conta
financeira, OCR ou falha antes de conflitos e pendências já normalizados. Cada processamento mostra
uma orientação segura derivada do estado e da etapa, com destino específico para mapear, configurar
conta, abrir movimentos ou reprocessar. A exceção bruta persistida nunca é renderizada. Execução
falha sem movimentos oferece somente “Reprocessar arquivo”; “Reaplicar regras” aparece apenas quando
houve movimento criado ou atualizado.

O salvamento de um layout passou a distinguir dois resultados: quando uma execução elegível voltou
à fila, confirma processamento iniciado; quando o arquivo já estava concluído, confirma somente o
layout para arquivos futuros e afirma que nada foi iniciado. O layout permanece versionado e o
arquivo original não muda.

Pesquisa prévia: UI/UX Pro Max orientou resumo focável, erro em linha e próximo passo. Watermelon
não encontrou bloco após busca focada e retry. Xero e QuickBooks fundamentaram mapear → revisar
resultado → corrigir; BlackLine, o trabalho por exceção; SaaSFrame, progresso e resumo de importação.
A fonte atual das Web Interface Guidelines foi aplicada a `reconciliation.html`, `workspace.html` e
`operations.css`; sem achado material após as correções.

Playwright MCP percorreu a prioridade do mapeamento em 1440 px, o formulário e seu erro em 390 px
escuro/movimento reduzido e a execução falha em desktop/mobile. A inspeção encontrou campos de 40 px,
links de erro de 32 px e a tabela espremida no celular; os controles passaram a 44 px e a tabela virou
cartões rotulados abaixo de 620 px. Estado final: largura 356 px em viewport 390, zero overflow, foco
de 3 px, erro focado com escolhas preservadas, somente ação aplicável, nenhum segredo no HTML e zero
erro/aviso no console. Capturas finais: `.playwright-mcp/reconciliation-v257-overview-desktop.png`,
`.playwright-mcp/reconciliation-v257-mapping-mobile-dark.png` e
`.playwright-mcp/reconciliation-v257-failed-mobile-dark-final.png`. Browser e servidor QA encerrados.

Validação focada: **64 testes e 24 subtestes aprovados em 37,05 s**. Regressão integral: **1.077
testes e 139 subtestes aprovados, seis skips explícitos, em 146,27 s**. Ruff, MyPy, Django check,
Node syntax, `makemigrations --check --dry-run` e diff-check passaram. Nenhum arquivo bancário,
tenant, integração, publicação ou cobrança real foi acionado; Q-39 e a homologação do destino
continuam abertas.

## V-258 — Revisão individual e entrega contábil verificável (02/10/2026)

D-228. A tela de movimento passou a derivar uma orientação única de `incompleto`, `revisado`,
`rascunho`, `aprovado`, `exportado` ou `ignorado`. A data importada usa o formato ISO esperado pelo
controle nativo; o resumo de erros recebe foco e liga cada erro ao campo. “Gerar lançamento
rascunho” não aparece antes de data, débito, crédito e valor válidos. Regra, ignorar e restaurar
ficam em “Outras ações”, sem competir com o próximo passo.

O download de exportação agora relê o conteúdo, confere SHA-256 em tempo de uso e audita download ou
falha de integridade. Quando o gate de homologação estiver habilitado, a confirmação exige checkbox,
hash integral apresentado, permissão atual e nova conferência do arquivo sob lock; registra pessoa e
instante, aceita repetição sem duplicar evento e mantém o download disponível. Conteúdo alterado é
recusado sem avançar o estado. Q-39 continua desabilitada no ambiente normal, portanto nenhum destino
real foi declarado homologado.

Pesquisa prévia: UI/UX Pro Max orientou estado explícito, alvo de 44 px e prevenção de envio duplo;
Watermelon não encontrou composição após busca focada e retry. QuickBooks fundamentou a separação
entre revisar, corresponder e categorizar sem duplicar; Xero, revisão e lote antes de reconciliar;
Ramp, distinção entre estado contábil e falha de sincronização, histórico, filtro e retry. A fonte
atual das Web Interface Guidelines foi relida e aplicada aos templates, CSS e JavaScript alterados.

Playwright MCP percorreu a revisão e as exportações em desktop e 390 × 844, tema escuro e movimento
reduzido. A inspeção encontrou data vazia por formato incompatível, ação de geração oferecida cedo,
hash quebrando caractere a caractere, painel lateral esticado e botão de 39 px; todos foram corrigidos.
O estado final preservou a data e o valor inválido após erro, focou o resumo, removeu a ação inválida,
confirmou um arquivo sintético com ator/instante, manteve o download, bloqueou reenvio, usou alvos de
44 px, não gerou overflow e terminou sem erro ou aviso no console da página inspecionada. Capturas:
`.playwright-mcp/reconciliation-v258-movement-mobile-dark-final.png`,
`.playwright-mcp/reconciliation-v258-movement-desktop.png`,
`.playwright-mcp/reconciliation-v258-movement-error-mobile-dark.png` e
`.playwright-mcp/reconciliation-v258-export-confirmed-mobile-dark.png`.

Validação focada: **60 testes e 24 subtestes aprovados em 33,36 s**. Regressão integral:
**1.080 testes e 145 subtestes aprovados, seis skips explícitos, em 132,86 s**. Ruff, MyPy, Django
check, Node syntax, `makemigrations --check --dry-run` e auditoria de interface passaram. Nenhum
arquivo bancário, tenant, integração, publicação ou cobrança real foi acionado.

## V-259 — Configuração contábil progressiva e escalável (03/10/2026)

D-229. A inspeção renderizada encontrou uma contradição operacional: “PRONTO PARA IMPORTAR” aparecia
com zero contas contábeis, enquanto período aberto e automação eram apresentados como etapas
necessárias embora o serviço só bloqueie datas cobertas por período explicitamente fechado. A página
também mostrava cinco formulários simultâneos e carregava seis coleções inteiras sem paginação.

A configuração agora deriva uma próxima ação: cadastrar conta contábil quando falta a referência
essencial; recomendar conta financeira, sem bloquear arquivos gerais, quando apenas a origem bancária
falta; ou voltar para importar quando ambas existem. O resumo identifica “Essencial”, “Para extratos”,
“Proteção opcional” e “Opcional”. Formulários usam `details`, abrem por deep-link e somente o essencial
incompleto começa expandido; erro do servidor mantém o painel aberto, preserva os valores e foca o
resumo vinculado. Edição não salva aciona o aviso nativo de saída. Bloquear/reabrir período exige abrir
a ação, registrar motivo e confirmar. Salvamentos e alterações retornam à seção afetada.

Contas financeiras, plano de contas, centros de custo, períodos, layouts e regras agora usam
paginação independente de 25 itens, preservando empresa e âncora. Em 390 px, tabelas viram cartões
rotulados. Perfil Auditor com `CompanyAccessGrant` e capacidades do módulo consulta os cadastros sem
formulário ou ação de escrita; POST permanece 403 e não altera estado.

Pesquisa prévia: UI/UX Pro Max confirmou resumo de erro focável, feedback de envio e bloqueio de
ativação duplicada; a busca de formulário extenso não encontrou resultado e foi repetida com termos
mais específicos. Watermelon não encontrou bloco nem dashboard pertinente em uma busca focada e um
retry. Foram adaptados: [QuickBooks](https://quickbooks.intuit.com/learn-support/en-us/help-article/chart-accounts/add-account-chart-accounts-quickbooks-online/L0mCv3AKn_US_en_US)
para criação do plano de contas antes de uso e desativação sem apagar histórico;
[Xero](https://central.xero.com/s/article/Start-using-Xero-UK) para distinguir preparação essencial de
configurações posteriores; [Xero Financial Settings](https://central.xero.com/0/article/Set-up-your-organisation-s-financial-details-SG)
para lock date como proteção explícita e auditável; e
[SAP Manage Posting Periods](https://help.sap.com/docs/SAP_S4HANA_ON-PREMISE_UPA/e55549ee96814207af9232a7688dd64a/98bd1b5825b0a107e10000000a441470.html?version=2022.3_UPA)
para separar visualização de períodos e ações autorizadas de abertura/fechamento. A fonte atual das
Web Interface Guidelines foi relida; a auditoria final confirmou semântica nativa, foco visível,
estado na URL, alerta de edição, alvo de 44 px, loading, vazio, quebra de texto e redução de movimento.

Playwright MCP percorreu 1440 × 900 e 390 × 844, tema escuro e movimento reduzido. Validou próximo
passo com base vazia, formulário essencial único, abertura/foco a partir do vazio, deep-link direto,
erro de nome obrigatório com código preservado, prevenção de saída, foco de teclado de 3 px, todos os
alvos locais em 44 px, ausência de overflow e zero erro/aviso de console. Capturas finais:
`.playwright-mcp/reconciliation-v259-configuration-desktop-final2.png`,
`.playwright-mcp/reconciliation-v259-configuration-mobile-dark-final.png` e
`.playwright-mcp/reconciliation-v259-configuration-error-mobile.png`.

Validação focada: **62 testes e 24 subtestes aprovados em 36,75 s**. Regressão integral:
**1.082 testes e 145 subtestes aprovados, seis skips explícitos, em 136,66 s**. Ruff, MyPy, Django
check, Node syntax e `makemigrations --check --dry-run` passaram. Nenhum dado real, integração,
publicação ou cobrança foi acionado; Q-39 permanece inalterada.

## V-260 — Auditoria da Conciliação orientada à investigação (03/10/2026)

D-230. A tela anterior oferecia apenas um filtro por código, exibia `hub.reconciliation.*` e UUIDs
como conteúdo principal e não explicava o que cada evento significava. Agora cada registro apresenta
atividade e categoria legíveis, explicação curta, responsável ou Sistema, instante, tipo de registro
afetado e resultado. Motivo, situação, contagens, revisão, origem, tamanho e valor só aparecem por uma
lista explícita de metadados seguros. JSON, request id, hash de IP, hashes de arquivo e chaves não
permitidas não são renderizados; código e UUIDs ficam recolhidos em “Detalhes técnicos”.

Busca por pessoa/referência, atividade amigável, resultado e intervalo de datas podem ser combinados
e permanecem na URL e na paginação. Atividade, resultado ou data inválidos geram orientação focada e
zero resultados, em vez de remover o filtro silenciosamente. Datas usam limites indexáveis sobre
`occurred_at`; páginas contêm 50 eventos. Resumo separa histórico total, resultado atual e falhas;
vazio inicial e busca sem correspondência têm mensagens e recuperação próprias. Permissões continuam
restritas a Owner, Admin e Manager do escritório atual.

Pesquisa prévia: UI/UX Pro Max confirmou orientação em vazio e reflow; a primeira busca foi
irrelevante e o retry específico foi usado. Watermelon não encontrou dashboard para `audit log` nem
bloco para `activity log` após a busca e o retry exigidos. Foram adaptados: [GitHub](https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/reviewing-the-audit-log-for-your-organization)
para filtro temporal persistente; [Microsoft Purview](https://learn.microsoft.com/en-us/purview/audit-search)
para atividade amigável, pessoa, item e detalhe; [Cloudflare](https://developers.cloudflare.com/fundamentals/account/account-security/audit-logs/)
para ator, ação, recurso e sucesso/falha; [Atlassian](https://support.atlassian.com/security-and-access-policies/docs/audit-log-activities-database/)
para nomes e descrições por categoria; e [GitLab](https://docs.gitlab.com/administration/compliance/audit_event_reports/)
para filtros por pessoa, escopo e período. A fonte atual das Web Interface Guidelines foi relida e a
auditoria final corrigiu placeholder, foco, alvos, texto longo, tema e sobreposição do erro mobile.

Playwright MCP percorreu 1280 × 720 e 390 × 844, tema escuro e movimento reduzido. Validou filtros
combinados e persistidos, intervalo invertido com foco no alerta, limpeza, detalhe técnico, navegação
por teclado com foco de 3 px, controles de 44 px, ausência de overflow e zero erro/aviso no console da
página final. A inspeção encontrou e corrigiu a sobreposição entre título e orientação do erro no
celular. Capturas: `.playwright-mcp/reconciliation-v260-audit-desktop.png` e
`.playwright-mcp/reconciliation-v260-audit-mobile-dark.png`.

Validação focada: **63 testes e 24 subtestes aprovados em 35,11 s**. Regressão integral:
**1.083 testes e 145 subtestes aprovados, seis skips explícitos, em 137,47 s**. Ruff, MyPy, Django
check, migrações, diff-check e auditoria de interface passaram. Nenhum dado real, integração,
publicação ou cobrança foi acionado; retenção/exportação da auditoria e Q-39 permanecem inalteradas.

## V-261 — Importação e prévia operacional da folha (03/10/2026)

D-231. A entrada manual agora separa escolha do conteúdo, envio e revisão. A ajuda muda conforme o tipo, o modelo da folha fica junto da decisão e o nome/tamanho do arquivo é anunciado. A prévia explica que ainda não gravou dados e o botão final informa quantidade e efeito operacional.

Todas as linhas da folha são pré-validadas sem criar fotografias ou atividades. Empresa, competência `AAAA-MM-01`, referência, pessoas e totais recebem diagnóstico por linha; qualquer pendência oculta a confirmação. A confirmação ainda revalida o lote em transação. Duplicata já processada volta ao histórico. POST de importação não vincula nem marca como inválidos os formulários independentes de identidade e fonte. O histórico vira cartões no celular e não excede o viewport.

Pesquisa prévia: UI/UX Pro Max confirmou resumo de erro focável, feedback contextual e reflow; Watermelon não encontrou resultado para upload/importação após busca e retry. Foram adaptados padrões de HubSpot, Salesforce, QuickBooks e Google Workspace para preparação, modelo, análise e erro por linha. As Web Interface Guidelines atuais foram relidas e aplicadas a labels, ajuda associada, `aria-invalid`, anúncio de arquivo, foco visível, alvos de 44 px, texto longo, tema e responsividade.

Playwright percorreu desktop e 390 × 844, tema escuro e movimento reduzido. Validou orientação dinâmica, seleção de arquivo, prévia inválida, bloqueio da confirmação, resumo de dois erros focado, teclado, foco de 3 px, controles de 44 px, histórico em cartão, zero overflow e zero erro/aviso no console. Capturas: `.playwright-mcp/payroll-import-v261-desktop.png`, `payroll-import-v261-invalid-desktop.png`, `payroll-import-v261-mobile-dark.png` e `payroll-import-v261-mobile-history.png`. Nenhum dado real, integração, publicação ou cobrança foi acionado. Homologação de layouts reais CSV/XLSX permanece pendente.

Validação automatizada final: **10 testes focados aprovados em 24,41 s** e **568 testes integrais aprovados em 8,77 s, com um skip explícito**, usando quatro processos e bancos SQLite isolados de teste. Ruff, MyPy (221 arquivos), Django check, migrações e `git diff --check` passaram.

## V-262 — Conferência agregada da folha por competência (03/10/2026)

D-232. A ficha da empresa passou a iniciar a conferência pela competência e não carrega mais todo o histórico em dois seletores irrestritos. A lista paginada mostra pessoas, bruto, descontos, encargos do empregador e líquido, preserva cada ausência como “Não informado” e oferece uma única ação por mês quando existem pelo menos duas fontes. A competência aberta limita as escolhas ao mesmo mês; duas fontes ficam pré-selecionadas sem disparar a conferência.

O resultado compara a fonte conferida com a principal, usa “a mais”/“a menos”, separa totais indisponíveis e oferece o próximo passo para a atividade sem mudar seu estado. A tolerância continua somente monetária. A consulta foi corrigida para remover ordenação antes da agregação por competência; o fluxo continua isolado por escritório, somente leitura e sem dados individuais de trabalhador.

Pesquisa prévia: UI/UX Pro Max reforçou período explícito, tabela responsiva e recuperação contextual. Watermelon não encontrou composição para conferência de folha nem para tabela comparativa após busca e retry. Materiais públicos de QuickBooks, Rippling, Gusto e ADP foram inspecionados como referência de relatórios de folha; foram adaptados apenas período, origem, resumo de totais e tratamento de exceções. A versão atual das Web Interface Guidelines foi relida e aplicada a labels, ajuda descrita, `aria-invalid`, foco do resumo de erros, foco visível, números tabulares, alvos de 44 px, URL como estado, tema e movimento reduzido.

Playwright MCP percorreu 1440 × 900 e 390 × 844, claro/escuro e movimento reduzido. Validou descoberta pela visão geral, seleção limitada ao mês, comparação válida, fontes iguais com resumo focado, ajuda/erro associados, foco de 3 px, controles de 44 px, tabela em cartões no celular, ausência de overflow e zero erro/aviso no console final. A inspeção encontrou e corrigiu corte horizontal do resultado mobile, coluna redundante quebrando letra por letra no desktop, ação duplicada por competência e foco tardio do erro. Capturas finais: `.playwright-mcp/payroll-comparison-v262-desktop-final.png` e `.playwright-mcp/payroll-comparison-v262-mobile-final.png`.

Validação automatizada: **16 testes focados aprovados em 54,09 s** e **568 testes integrais aprovados em 8,338 s, com um skip explícito**, usando quatro processos e bancos SQLite isolados. Ruff, MyPy dos três módulos alterados, Django check, migrações e sintaxe JavaScript passaram. Nenhum dado real, integração, publicação ou cobrança foi acionado; a segunda fonte usada no Playwright existe apenas no banco descartável de QA. A homologação com resumos reais autorizados permanece pendente.

## V-263 — Caixa Postal DTE orientada à leitura segura (03/10/2026)

D-233. A caixa deixou de repetir o assunto como dois links e passou a oferecer uma única ação “Abrir resumo” por mensagem. Filtros, metadados e ações ganharam hierarquia e alvos mínimos de 44 px; o histórico vira cartões rotulados no celular. O resumo continua separado do teor: a abertura potencialmente capaz de registrar ciência exige confirmação própria. Na demo, teor e protocolo ficam apenas na sessão e declaram que não produzem ciência oficial.

Pesquisa prévia: UI/UX Pro Max reforçou feedback contextual, prioridade e estados legíveis. Watermelon não encontrou composição após buscas amplas e retries específicos para inbox e detalhe de mensagem. Foram adaptados padrões da [Caixa Postal da Receita Federal](https://www.gov.br/receitafederal/pt-br/canais_atendimento/atendimento-virtual/minha-caixa-postal), [Caixa de Mensagens do DET](https://det.sit.trabalho.gov.br/manual/caixaPostal/caixaDeMensagens/indexCaixaDeMensagens.html), [Microsoft 365 Message Center](https://learn.microsoft.com/en-ca/microsoft-365/admin/manage/message-center?view=o365-worldwide) e [Outlook na Web](https://support.microsoft.com/en-us/office/mail-in-outlook-web-app-ed7b1cb9-ef40-4fbd-a302-278cc7f4dcf5?ad=us&rs=en-us&ui=en-us): recentes primeiro, lido/não lido, origem/empresa/data, filtros explícitos e ação distinta do conteúdo juridicamente sensível. A fonte atual das Web Interface Guidelines foi relida e aplicada a alvos, foco, números tabulares, texto longo, tradução de identificadores e interação por toque.

Playwright MCP validou a central e o detalhe em 1440 × 900 e 390 × 844, claro/escuro e movimento reduzido. Foram exercitados filtro sem resultado, recuperação, erro sem empresa com foco, preparo/revisão/simulação local, abertura fictícia, teclado, foco de 3 px, controles de 44 px, cartões sem rolagem horizontal e console sem erro/aviso. Capturas finais: `.playwright-mcp/dte-v263-desktop-final.png`, `.playwright-mcp/dte-v263-mobile-final.png` e `.playwright-mcp/dte-detail-v263-mobile-final.png`.

Validação focada: **13 testes aprovados em 54,79 s**. A regressão integral aprovou **568 testes em 8,394 s, com um skip explícito**, em quatro processos e bancos SQLite isolados. Ruff, Django check, sintaxe JavaScript, migrações e diff-check passaram. Nenhum Serpro, tenant real, publicação ou cobrança foi acionado; credenciais, contrato e piloto real autorizado continuam pendentes.

## V-264 — Radar como fila de triagem fiscal (03/10/2026)

D-234. A tabela antiga media 650 px no viewport de 390 px e escondia na rolagem horizontal justamente “Abrir na fonte” e “Analisar por empresa”; metadados e ações usavam 11/34 px. A página agora usa uma fila recente com fonte, tema, data, resumo, limite de interpretação e duas ações explícitas em cada cartão. A saúde das fontes fica em divulgação compacta e abre automaticamente na falha, sem expor a exceção bruta. Filtros, vazio e paginação mantêm recuperação e URL canônica.

O detalhe separa publicação e decisão humana. A carteira de 240 empresas foi exercitada com filtro local progressivo, mantendo o `select` nativo e funcionamento sem JavaScript. O motivo explica o que registrar e o CTA informa que cria ou retoma uma atividade. O filtro local não dispara aviso falso de edição; empresa/motivo reais continuam protegidos pelo aviso de saída. Análises existentes aparecem como trabalho retomável. Owner criou uma atividade idempotente; Auditor viu “Ver análises”, não recebeu formulário e o POST segue recusado pelo servidor.

Pesquisa prévia: UI/UX Pro Max encontrou orientação para vazio recuperável, feedback e cartões; a busca de stack para tabela responsiva não encontrou correspondência após retry. Watermelon não encontrou dashboard nem bloco após buscas amplas e retries. Foram adaptados padrões do [Feedly AI Feeds](https://docs.feedly.com/article/807-how-to-create-ai-feeds), [PolicyNote Alerts](https://fiscalnotepolicynote.zendesk.com/hc/en-us/articles/46767812717979-The-Alerts-Page), [Thomson Reuters Checkpoint Edge](https://www.thomsonreuters.com/en-us/help/checkpoint-edge/quick-reference/read-news-and-updates), [Lexis+ Alerts](https://supportcenter.lexisnexis.com/app/answers/answer_view/a_id/1090734/~/viewing-and-working-with-alert-results-on-lexis-advance) e [Google Alerts](https://support.google.com/websearch/answer/4815696): fila consolidada, fonte/tópico/data, triagem contextual e transformação explícita de conteúdo em trabalho.

A fonte atual das Web Interface Guidelines foi relida. A auditoria corrigiu alvo de recuperação de 39 px, foco translúcido dos campos, rótulo consultivo, URL de retorno e aviso indevido ao apenas filtrar empresas. Playwright MCP percorreu 1440 × 900 e 390 × 844, claro/escuro e movimento reduzido; validou filtros, vazio, falha de fonte, filtro 240/1/0, erro 400 focado, loading, criação, retorno, Owner/Auditor, teclado, foco, 44 px, zero overflow e console final limpo. Capturas: `.playwright-mcp/radar-v264-desktop-final.png`, `.playwright-mcp/radar-v264-mobile-final.png`, `.playwright-mcp/radar-analysis-v264-desktop-final.png` e `.playwright-mcp/radar-analysis-v264-mobile-dark.png`.

Validação focada: **12 testes aprovados em 53,55 s**. Regressão integral: **568 testes aprovados em 8,714 s, com um skip explícito**, em quatro processos e bancos SQLite isolados. Ruff, Django check, sintaxe JavaScript, migrações e diff-check passaram. Nenhuma coleta externa, publicação, tenant real ou cobrança foi acionada; cobertura/completude das fontes e aplicabilidade fiscal real permanecem dependências externas.

## V-265 — Fechamento dos relatórios de retenções NFS-e (03/10/2026)

D-224/D-235. A implementação foi comparada novamente com o HubCobalchini autorizado. O CICA
mantém a seleção pelo recorte visível, resumo e detalhe; corrige o comportamento legado que podia
tratar CSLL como todo o CRF e soma somente ISS, PIS, COFINS, CSLL, IRRF e INSS explicitamente
normalizados. A lista mostra o total retido por nota e abre cada tributo; os botões geram PDF e Excel
`.xlsx`. O detalhamento passou de 32/12 px para alvo de 44 px e texto de 14 px, com valores em 13 px.

Pesquisa final: UI/UX Pro Max reforçou reflow e feedback; Watermelon não encontrou composição para
relatório tributário/exportação após busca e retry. A documentação de produção da
[NFS-e Nacional](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-atual/documentacao-atual)
e o [Guia do Emissor](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-em-homologacao/guia-emissorpubliconacionalweb_snnfse-ern-1.pdf)
confirmam os campos de retenção e orientaram a separação. A fonte atual das Web Interface Guidelines
foi relida; sem violação material nos arquivos alterados após o ajuste de alvo, foco, rótulo, reflow,
tema e movimento reduzido.

Playwright MCP efetuou os dois downloads em sessão autenticada e confirmou o `.xlsx` depois da
mudança de rótulo. Inspeção desktop e 390 × 844, claro/escuro, movimento reduzido, expansão dos
tributos, vazio com ações desabilitadas, teclado, foco de 3 px, alvos de 44 px, zero overflow e zero
erro/aviso no console. O PDF baixado possui três páginas; todas foram renderizadas e inspecionadas,
sem corte, sobreposição ou página vazia. A planilha foi reaberta com abas `Resumo`/`Notas`, 17
colunas, tabela filtrável, cabeçalho congelado, datas/moedas tipadas e fórmulas de total. Não há
LibreOffice nem `@oai/artifact-tool` disponível nesta sessão, portanto não se alega renderização
visual nova do XLSX; a estrutura e os valores foram conferidos diretamente.

Validação focada: **41 testes e sete subtestes aprovados em 55,92 s**. Regressão integral:
**568 testes aprovados em 8,762 s, com um skip explícito**. Ruff, Django check, migrações e diff-check
passaram. Browser e servidor QA foram encerrados. Nenhum tenant real, fonte externa, publicação ou
cobrança foi acionado. A única validação fiscal pendente é confrontar os valores com uma amostra real
autorizada e homologar o destino/retorno Domínio de Q-39.

## V-266 — Guias e DCTFWeb orientadas ao próximo passo (03/10/2026)

D-236. A carteira deixou de tratar apurações locais, documentos e guia como uma lista única. Sem
guia oficial, um bloco de próximo passo aparece antes do resumo e leva às apurações; com guia,
a fila oficial fica prioritária. Cada estado oferece uma ação principal e orientação própria.
O detalhe não promete resultado antes da emissão e o histórico preserva referências em divulgação.

A consulta DCTFWeb mostra progresso `0–2 de 2`, declaração e recibo por nome. Chaves como
`dctfweb.recibo`, exceções do conector e mensagens brutas do fornecedor não são renderizadas.
Falha orienta a revisão; resultado incerto diz para não repetir e oferece somente registro/código para
suporte. A confirmação em lote vira cartões no celular e a carteira preserva lote de 30/paginação.

Pesquisa prévia: UI/UX Pro Max reforçou feedback após ação, estado compreensível e estrutura
consistente de cartão. Watermelon não encontrou composição para `tax payment status history` nem
`payment history` após busca e retry. Foram adaptados o
[Manual DCTFWeb 2025](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/manuais/manual-dctfweb/manual-dctfweb-atualizacao-janeiro2025_versao_final.pdf),
para período, saldo, documentos e emissão em lote; o
[Tax Center do QuickBooks](https://quickbooks.intuit.com/learn-support/en-global/help-article/sales-taxes/manage-sales-tax-payments-quickbooks-online/L91njDRsj_ROW_en),
para separar períodos, pagamentos e ação; e a
[idempotência/erros do Stripe](https://docs.stripe.com/api/errors/handling), para não sugerir
repetição em resultado desconhecido. A fonte atual das Web Interface Guidelines foi relida; a
auditoria corrigiu nome acessível do progresso, alvos, overflow da tabela em lote e próximo passo.

Playwright MCP percorreu 1440 × 900, 390 × 844 e 844 × 390, claro/escuro e movimento reduzido.
Validou seleção de duas empresas, revisão sem contrato, filtros/vazio/limpeza, modal com foco inicial,
Escape e restauração, âncora, teclado/foco de 3 px, controles de 44 px, documento falho e incerto,
ausência de erro bruto/chave interna, PDF demo, zero overflow e zero erro/aviso no console. Capturas:
`artifacts/guides-v266-final-desktop.png`, `artifacts/guides-v266-final-mobile-dark.png`,
`artifacts/guides-v266-bulk-mobile-dark.png` e
`artifacts/guides-v266-dctfweb-failed-unknown-mobile.png`.

Validação focada: **26 testes aprovados**. Regressão integral: **569 testes aprovados em 8,589 s,
com um skip explícito**. Ruff,
MyPy do módulo, Django check, migrações e diff-check passaram. Browser e servidor QA foram
encerrados. Nenhum Serpro, dado real, publicação ou cobrança foi acionado. Contrato/credenciais,
transições reais, D-149 e Q-40 permanecem dependências externas.
## V-268 — Fechamento técnico dos relatórios de retenções NFS-e (03/10/2026)

- A suíte focada de NFS-e aprovou 111 testes e 7 subtestes, incluindo normalização ADN,
  entrada/saída, retenções explícitas, filtros, limite de 5.000 notas e leitura real dos arquivos
  PDF/XLSX gerados.
- Ruff, MyPy do núcleo de relatórios, `manage.py check`, `makemigrations --check --dry-run` e
  `git diff --check` passaram sem erro.
- A regressão integral final aprovou 1.087 testes e 145 subtestes; 6 testes foram ignorados de
  forma explícita por dependerem de Playwright Python opcional ou de locks reais no PostgreSQL.
- O MCP de navegador obrigatório não expôs Chrome nem navegador interno nesta sessão. Portanto,
  não se alega nova inspeção renderizada nesta rodada; permanecem como evidência visual os
  artefatos e a validação V-265. Não houve publicação nem chamada a fornecedor fiscal.
## V-267 — Parcelamentos orientados ao trabalho contábil (03/10/2026)

- Empresa em foco, acordos, parcelas pagas, parcelas disponíveis para DAS e carteira foram ordenados pela decisão do contador; uma ação principal é exibida por estado.
- Consulta individual, detalhe, parcelas, emissão e lote mostram revisão anterior à operação. A demo declara ausência de consumo e mantém resultado somente na sessão.
- Mensagens brutas do fornecedor não são exibidas. Falha e incerteza recebem próximo passo seguro; liberar nova tentativa após estado incerto exige confirmação de conferência no e-CAC.
- O DAS demo é um PDF privado à sessão, com empresa, acordo, competência, vencimento, valor e protocolo, marcado repetidamente como fictício e sem validade fiscal.
- Playwright: desktop 1440 px; mobile 390×844 em tema escuro e movimento reduzido; landscape 844×390; modal, Escape, retorno de foco, Tab, lote de 2 empresas, busca vazia/limpeza, download, zero overflow horizontal e zero erro no console.
- Evidências: `artifacts/parcelamentos-v267-desktop.png`, `artifacts/parcelamentos-v267-mobile-dark-final.png`, `artifacts/parcelamentos-v267-mobile-table.png`, `artifacts/parcelamentos-v267-landscape.png` e `artifacts/parcelamentos-v267-das-ficticio.pdf`.
- Watermelon não retornou resultado após busca ampla e refinada. Manuais/perguntas da Receita e padrões de estado/ação de Stripe, QuickBooks e Xero orientaram a solução. A auditoria Web Interface Guidelines não deixou violação material.
- 19 testes focados passaram; Ruff, MyPy das views/URLs, JavaScript syntax check, Django check, migrações e diff-check passaram. A regressão integral final aprovou 1.088 testes e 145 subtestes; 5 skips explícitos dependem de locks reais no PostgreSQL.
- Limites: sem chamada, custo ou homologação Serpro; sem validação de contrato/credenciais; sem publicação.

## V-269 — Ficha de atividade orientada à decisão (03/10/2026)

- A ficha começa pelo contexto e próximo passo; condições de conclusão, responsabilidade e evidências vêm antes dos estados técnicos e do histórico recolhido. O título duplicado foi removido.
- Evidência, impedimento e conclusão são ações separadas. Erros retornam HTTP 400, preservam a entrada, mantêm a ação aberta e recebem foco. A conclusão exige revisão; no estado impedido, a revisão explica a resolução e a limpeza do motivo sem apagar a trilha.
- Eventos técnicos recebem rótulos humanos. Auditor enxerga o mesmo contexto sem formulários, redistribuição ou conclusão.
- UI/UX Pro Max orientou ação principal, feedback e alvo. Watermelon não retornou composição em duas buscas. Foram adaptados detalhes/propriedades, responsabilidade e histórico de Asana, Linear e ClickUp; a fonte atual das Web Interface Guidelines foi relida e a auditoria não deixou violação material.
- Playwright MCP validou 1440×900, 390×844 e 844×390; claro/escuro, movimento reduzido, pendente/vazio/pronta/impedida/erro, Owner/Auditor, modal, Tab/Escape/retorno de foco, histórico, 44 px, zero overflow e console limpo após navegação válida. Capturas: `artifacts/activity-detail-v268-desktop-final.png`, `artifacts/activity-detail-v268-mobile-dark.png` e `artifacts/activity-detail-v268-landscape.png`.
- Validação focada: 77 testes e 12 subtestes aprovados. Ruff, MyPy, JavaScript, Django check, migrações e diff-check passaram. Nenhum dado real, fonte externa, publicação ou cobrança foi acionado; a homologação de atividades alimentadas por integrações reais continua pendente.
- Regressão integral final: **1.090 testes e 145 subtestes aprovados**, com 6 skips explícitos por Playwright Python opcional ou locks reais do PostgreSQL.

## V-270 — Central de atividades como fila de decisão (03/10/2026)

- A fila padrão contém somente trabalho em aberto. Encerradas continuam acessíveis por situação explícita; prioridades mostram contagens agregadas em uma única consulta e preservam os filtros de contexto.
- Os dois formulários anteriores viraram um refinamento. Filtros ativos podem ser removidos individualmente, parâmetros vazios não poluem a URL e o retorno pelo navegador restaura controles habilitados.
- Valores inválidos, empresa/responsável fora do escopo e prazo conflitante produzem recorte vazio, erro anunciado e foco; nunca ampliam silenciosamente a carteira.
- Cada atividade expõe empresa/área/competência, próximo passo, prazo relativo/exato, responsável, estado e uma ação “Conferir”. Em 390 px, todas as células viram cartões rotulados; o primeiro ensaio revelou cartões vazios por `min-width` global e foi corrigido antes da validação final.
- UI/UX Pro Max confirmou reflow de filtros; a busca de stack ficou sem correspondência após retry. Watermelon não encontrou dashboard nem bloco em duas buscas. Foram adaptados filtros/URL do Linear, dimensões de prazo/situação/responsável do ClickUp, ordenação do Asana e separação entre filtro e mutação do Microsoft Planner.
- A fonte atual das Web Interface Guidelines foi relida. Auditoria de `activities.html`, `activities.css`, `hub.js`, cache-bust do workspace/platform e estados renderizados não encontrou violação material após números tabulares, quebra de conteúdo longo e restauração dos campos no histórico.
- Playwright MCP validou 1440×900, 390×844 e 844×390, claro/escuro, movimento reduzido, prioridade, refinamento, chips, URL limpa, filtro vazio/inválido, foco de erro, teclado, Owner/Auditor, cartões, back/forward, alvos de 44 px, zero overflow e console limpo. Capturas: `artifacts/activities-v270-desktop-final.png`, `artifacts/activities-v270-mobile-dark.png` e `artifacts/activities-v270-landscape.png`.
- Validação focada: **135 testes e 19 subtestes aprovados**. Regressão integral: **1.093 testes e 145 subtestes aprovados**, com 6 skips explícitos por Playwright Python opcional ou locks reais do PostgreSQL. Ruff, MyPy, JavaScript, Django check, migrações e diff-check passaram. Sem fonte externa, dado real, custo ou publicação.
## V-271 — Modelos de atividades como biblioteca operacional (03/10/2026)

- A tela passou a começar por modelos ativos, atribuições ativas, empresas cobertas e rotinas mensais aptas, indicando uma única próxima ação conforme o estado do escritório.
- Definição, atribuição e geração viraram etapas progressivas recolhíveis. A biblioteca aparece antes dos formulários e explica versão, área, periodicidade, prazos, comprovação e cobertura.
- Modelos e atribuições agora paginam em 20/30 registros. A listagem não materializa todas as empresas por modelo; usa contagens agregadas e uma revisão separada da cobertura.
- Atribuição repetida do mesmo modelo à mesma empresa retorna HTTP 400, preserva dados, abre a etapa correta e foca o resumo de erro. Pausar/retomar modelo ou atribuição preserva atividades e histórico. A geração mensal considera apenas modelos mensais ativos e mantém idempotência.
- UI/UX Pro Max orientou feedback de formulário e layout responsivo; não houve correspondência específica para recorrência após retry. Watermelon não encontrou dashboard/bloco após as duas buscas exigidas. Foram adaptadas a biblioteca contábil e separação entre modelo/agendamento do Karbon e Financial Cents, e a configuração de modelos/recorrência de Asana, ClickUp e Monday.
- A fonte atual das Web Interface Guidelines foi relida. A auditoria de `activity_models.html`, `activities.css`, `forms.py` e `views.py` corrigiu a compressão da ação desktop, a altura indevida do cartão mobile, pluralização, foco, alvos, reflow, tema e movimento reduzido; não restou violação material no escopo alterado.
- Playwright MCP percorreu criação, atribuição, duplicidade, geração, desktop 1280 px, celular 390 × 844 escuro/reduzido e paisagem 844 × 390. Houve foco visível de 3 px, controles aplicáveis de 44 px, zero overflow e console final limpo. Capturas: `artifacts/activity-models-v271-desktop-final.png` e `artifacts/activity-models-v271-mobile-dark-final.png`.
- Validação focada: **144 testes e 23 subtestes aprovados**, com um skip explícito que exige locks reais do PostgreSQL. Regressão integral: **1.095 testes e 145 subtestes aprovados**, com seis skips explícitos por Playwright Python opcional ou locks reais do PostgreSQL. Ruff, MyPy, Django check, migrações e diff-check passaram. Nenhuma fonte externa, dado real, publicação ou cobrança foi acionado.

## V-272 — Fechamentos por competência como fila contábil (03/10/2026)

- O painel mostra, para a página atual, fechamentos que exigem atenção, comprovados, áreas sem requisitos e empresas; os totais não se apresentam como agregação da carteira inteira.
- Impedimentos, reaberturas, fontes não verificáveis e pendências são priorizados. Cada empresa/área expõe progresso, próximo passo e ação direta; atividades, evidências e requisitos ficam em detalhe acessível por teclado.
- Concluídos ficam em grupo secundário e lacunas de cobertura nunca aparecem como fechamento ou dispensa. Administradores recebem atalho para os modelos; demais perfis recebem orientação explícita.
- Competência inválida exibe zero fechamentos, mantém o painel aberto, anuncia o erro, move o foco para ele e não substitui o recorte por outro mês.
- UI/UX Pro Max orientou feedback e reflow; Watermelon não encontrou composição após duas buscas. FloQast, Financial Cents e QuickBooks Books Review orientaram progresso, exceções, próxima tarefa e revisão por período. A fonte atual das Web Interface Guidelines foi reaplicada; o `autofocus` móvel e a variante de botão incorreta foram removidos.
- Playwright MCP validou 1280 × 900 e 390 × 844, claro/escuro, movimento reduzido, teclado/Enter, foco de 3 px, detalhe, ação para a atividade, estado inválido, zero overflow e console final sem erro/aviso. Capturas: `artifacts/closing-v272-desktop-final.png` e `artifacts/closing-v272-mobile-dark-final.png`.
- Testes focados: 47 testes e 12 subtestes aprovados. Regressão integral: **1.095 testes e 145 subtestes aprovados**, com seis skips explícitos por Playwright Python opcional ou locks reais do PostgreSQL. Ruff, MyPy, Django check, migrações e diff-check passaram. Browser e servidor QA foram encerrados; não houve fonte externa, dado real, custo ou publicação.

## V-273 — Cadastro de empresas como carteira de ação (03/10/2026)

- A entrada da carteira mostra todas as empresas autorizadas, as que precisam de atenção, revisões
  NFS-e, pendências de A1 e ausência de código Domínio. Empresas pausadas continuam consultáveis,
  mas não são contadas como pendência operacional.
- Busca e prioridades permanecem visíveis; situação, vínculo, certificado e revisão ficam em um
  refinamento progressivo. Cada linha apresenta identidade, integrações, próximo passo e uma ação
  coerente: revisão NFS-e, vencimento/A1 ou ficha da empresa.
- O filtro de vínculo agora isola empresas sem código. Valores inválidos em qualquer filtro retornam
  zero empresas, orientação recuperável e foco; não ampliam silenciosamente a carteira. Formulário
  inválido preserva os dados, abre o modal e foca o resumo; duplicidade retorna HTTP 400.
- UI/UX Pro Max orientou reflow, legibilidade e feedback. Watermelon não encontrou composição após
  busca ampla e refinada. QuickBooks Accountant, TaxDome, Karbon e Financial Cents orientaram
  prioridades, tarefas por cliente, filtros explícitos e agrupamento operacional. A fonte atual das
  Web Interface Guidelines foi relida; a auditoria corrigiu foco do refinamento, tamanho dos alvos,
  tipografia e destino específico de certificado vencendo.
- Playwright MCP validou 1280 × 900, 390 × 844 e 844 × 390, claro/escuro, movimento reduzido,
  prioridades, busca, refinamento assíncrono, vazio, filtro inválido/foco, modal, duplicidade,
  Escape/retorno de foco, alvos de 44 px, zero overflow e console final limpo. Capturas:
  `artifacts/companies-v273-desktop-final.png` e
  `artifacts/companies-v273-mobile-dark-final.png`.
- Validação focada: **24 testes e 2 subtestes aprovados**. Regressão integral:
  **1.097 testes e 145 subtestes aprovados**, com seis skips explícitos por Playwright Python
  opcional ou locks reais do PostgreSQL. Ruff, MyPy, Django check, migrações e diff-check passaram.
  Browser e servidor QA foram encerrados. Não houve dado real, integração externa, custo, deploy ou
  publicação. Edição do cadastro e homologação da origem Domínio continuam na revisão subsequente.

## V-274 — Reclassificação NFS-e pelo backup e contrato `acum` em produção (05/10/2026)

- Os conjuntos Krek são leiautes do importador, não notas. O contrato confirmado é uma única tag
  `infNFSe/valores/acum` na cópia derivada; o XML fiscal original continua imutável e `ACU` não é
  aceito para NFS-e.
- A rotina usa a fotografia composta pelos lotes `d4578c99-7258-490e-aa99-c992cf5d9703` (catálogo)
  e `b4551285-7f15-4c20-9a13-7bbba68ba3ff` (observações), ambos de 23/09/2026. A prévia é somente
  leitura; `--apply` registra evidência append-only e nunca substitui decisão humana.
- Antes da escrita foi criada a ramificação Neon `pre-nfse-reclass-20261005`, sem compute e com
  expiração em 12/10/2026. Foram avaliadas 29.042 notas: 4.656 tiveram correspondência segura,
  4.640 já estavam corretas, 16 exigiam nova evidência e 24.386 permaneceram em revisão.
- A aplicação registrou 16 artefatos, resolveu 16 revisões com origem `backup`, criou 39 revisões e
  atualizou 666 sugestões. A segunda passagem retornou zero criação, resolução ou atualização. O
  evento auditável usa o run id `17162261-af2d-4cc5-b387-562dafff88a0`.
- Os 16 XMLs derivados foram analisados: exatamente um `acum`, filho direto de `valores`, valor
  igual ao artefato e zero `ACU`. A release Fly 45, web/worker, liveness, readiness, banco e cache
  terminaram saudáveis; a memória temporária de 2 GB foi devolvida a 512 MB.
- Validação local: 1.106 testes e 145 subtestes aprovados, seis skips explícitos; Ruff, MyPy, Django,
  migrações e diff-check passaram. Playwright validou desktop e 390 px escuro/reduced-motion,
  teclado, foco, alvos, expansão, zero overflow e console limpo; browser e QA foram encerrados.
  A homologação de importação e retorno do Domínio continua dependência externa de Q-39.
## V-275 — Auditoria integral e plano de conclusão do produto (05/10/2026)

Escopo D-275: análise e planejamento, sem implementação de funcionalidades ou publicação.
O topo de PLANO-MESTRE.md recebeu a revisão vigente com estado reconciliado das etapas 00–13,
31 pacotes de trabalho, prioridades, dependências, responsáveis, ondas, critérios e próximo prompt.
O diagnóstico, a matriz de telas, os achados e as fontes estão em
[auditoria-produto-2026-10-05.md](docs/planejamento/auditoria-produto-2026-10-05.md).

Foram confrontados documentação, código produtivo, testes existentes e capacidades de concorrentes.
Os achados incluem Triagem sem percurso completo de scan/extração/checklist e sem prévia/correção;
curadoria de IA incompleta; cobrança sem alinhamento integral a D-109 e sem ponte completa para
acesso; predicados de onboarding, calendário recorrente limitado e ergonomia de carteira extensa.
A inspeção NFS-e encontrou 24 no indicador “Total no período” contra 12 na lista de setembro;
o código confirma contagens globais e links que descartam contexto nos modos real e demo.
Isso é um defeito localizado a corrigir em PC-02, não uma correção implementada nesta entrega.

Pesquisa online: Domínio/Gestta, Nibo, Acessórias, SIEG, Qive, Karbon, TaxDome, Financial Cents,
FloQast, Ramp, Linear e documentação oficial NFS-e. Cinco fluxos foram examinados em documentação
pública; não houve sessão autenticada de concorrente. Refero foi consultado primeiro e SaaSFrame
depois, com limitações de acesso registradas. Watermelon MCP não retornou composição em uma busca
de dashboards e um retry de blocos. UI/UX Pro Max, landing-page-design e a fonte atual completa
das Web Interface Guidelines foram consultadas. A auditoria é de planejamento, sem alegação de
conformidade integral de todo o aplicativo e sem alteração de UI.

Playwright MCP: servidor exclusivo 8055, bancos/mídia em `.tmp/product-audit-20261005`, fixtures
sintéticas e conexões de saída bloqueadas. A varredura percorreu 27 URLs/recortes em 1440×960 e
390×844: 54 combinações, das quais 50 responderam 200 e quatro foram os 403 esperados da demo
em configuração/auditoria da Conciliação. Nenhum overflow horizontal ou `pageerror` foi encontrado.
O console registrou essas recusas esperadas; a última página de operação terminou sem erro/aviso.
Não se infere aprovação interna das páginas recusadas nem testes completos de cada interação.

Percursos complementares: detalhe de documento Triagem; atividade sem evidência e ficha de
empresa; filtro inválido retornando recorte vazio/orientação; pesquisa de empresa sem resultado;
abertura de evidência e Tab com foco visível de 3 px; Owner, Auditor e Operator sintéticos. Auditor
abriu a atividade sem formulários de alteração; Operator teve menu móvel aberto/fechado por Escape
e lista em 844×390 sem overflow. Não foram feitas operações fiscais ou envios reais.

Evidência legível por máquina:
[product-audit-20261005-rendered.json](artifacts/product-audit-20261005-rendered.json).
Capturas `artifacts/product-audit-20261005-current-*`: dashboard desktop, NFS-e móvel, setup móvel,
Triagem desktop, detalhe Triagem e ficha da empresa. As quatro primeiras foram abertas para
inspeção visual. A exploração preliminar em 8012 foi excluída da contagem por haver um QA anterior;
um 404 de URL exploratória incorreta não foi classificado como defeito do sistema.

Todos os tabs desta tarefa foram encerrados pelo Playwright, que retornou “No open tabs”. Os
processos QA iniciados nesta tarefa foram encerrados; processos preexistentes foram preservados.
Não foram reexecutados testes da aplicação: a entrega alterou documentação e produziu evidências,
sem mudanças de código. V-274 continua sendo a referência histórica da regressão, não nova prova.
Verificação documental concluída: 31 pacotes únicos, 14 etapas, 14 achados e 13 links locais dos
documentos principais conferidos, sem destino ausente; IDs D-275/V-275 únicos e JSON com as 54
combinações consistente. `git diff --check` dos arquivos documentais de escopo passou. Houve apenas
avisos de conversão LF/CRLF do Git. Revisão independente do conteúdo corrigiu posição do resumo
vigente, limites de fonte indisponível, escopo de máquina/dados, transmissões e linguagem do piloto.

Limites: não houve avaliação com usuários reais, reprodução de todos os estados/perfis, teste de
carga/restore, inspeção autenticada de produção, homologação ERP/Serpro/e-mail/IA, contratação,
consumo ou deploy. As etapas funcionais continuam abertas conforme seus aceites. V-275 conclui
a revisão documental solicitada, não a implementação dos pacotes nem a conclusão do sistema.

## V-277 — Rotina diária: nomes, papéis e notas legíveis em produção (06/10/2026)

- Origem D-277, fase 1. Revisão prévia da demonstração publicada mostrou e-mail interno como
  responsável, papéis em inglês na Gestão, NSU/hash no lugar do número da NFS-e, trio de estados
  padrão ("Não verificado · Não aplicável · Atualizado") e UUID no histórico de atribuição.
- Entrega: `User.display_name`; rótulos de papel em português (migração só de choices); ficha da
  empresa lista NFS-e por número, emissão e contraparte; um único qualificador acionável ao lado
  da situação; histórico de atribuição com nomes (UUID antigo traduzido na exibição, histórico
  imutável preservado); resumo duplicado da central de atividades removido; teste-catraca de
  texto explicativo sob títulos (`tests/test_ui_copy_rule.py`, 88 ocorrências em 34 templates,
  só pode diminuir).
- Local: 1.149 testes e 145 subtestes aprovados, seis skips explícitos; Ruff e
  `makemigrations --check` limpos; testes novos para nomes/nota/papéis/histórico.
- Produção: release Fly v55 (build local, canário), web e worker saudáveis, logs sem erro. Na
  demonstração publicada: ficha da Clínica Odonto Sorriso sem e-mail, hash ou trio de estados,
  notas `DEMO-0103-001..004`; Gestão com "Operador"/"Dono"; Atividades sem o resumo duplicado.

Limites: conferência na demonstração fictícia; conta de teste real ainda não aberta pelo
proprietário. Prazos (competência × vencimento) seguem na fase 2.

## V-278 — D-277 fases 2 a 5, limpeza de texto e nova tela de NFS-e (06/10/2026)

- **Prazos (fase 2):** app `fiscal_calendar` com anos de calendário (CMN 4.880/2020, art. 6º, e
  lista nacional ANBIMA; 2026 conferido em 13 datas) e regras versionadas em rascunho (DCTFWeb,
  contribuições previdenciárias, DAS) com base legal, fonte e aprovação na plataforma. Modelos
  ganham mês do prazo, regra legal e antecedência; recorrência abre M em M+offset; demonstração
  com janela rolante. Produção: demo passou a mostrar competência 09/2026 com prazos em outubro
  e guias DCTFWeb 09/2026 vencendo 20/10/2026; guias 08/2026 retiradas.
- **Atividades (fase 3):** filtros visíveis, seleção e ação em lote (atribuir, mudar prazo,
  concluir o que está pronto), próximo passo específico, "Assumir", mudança de prazo com motivo,
  observações; celular com linha média 301→181 px e toolbar 349→138 px.
- **Empresas (fase 4):** regime, IE, IM, contato e responsável por área; filtro por regime;
  perfil editável com identidade vinda da fonte. Demo pública: cadastro somente leitura.
- **Busca e avisos (fase 5):** busca por carteira/módulo (Ctrl+K), avisos deduplicados de
  atribuição, prazo, fonte, DTE e certificado; tarefas diárias no Beat.
- **Texto (fase 8):** 45 parágrafos explicativos removidos; 44 mantidos com
  `data-copy="required"` (limite real, custo, ciência DTE, demonstração, formato); catraca zerada.
- **NFS-e:** primeira nota de 1.343 px para 688 px no desktop (demo); um único botão primário
  ("Classificar"); abas de situação e segmentos de movimento com contagens; um "Baixar" com XML
  originais, pacote Domínio e retenções; filtro ao vivo mantido. Referências: Stripe Invoices,
  Linear, NN/g (tabelas de dados), Qive. Detector Impeccable: 0 ocorrências.
- Local: 1.180 testes e 145 subtestes aprovados, seis skips; Ruff e `makemigrations --check`
  limpos. Produção: releases sucessivas com web/worker saudáveis.
- **Triagem (fase 7, verificação sem mudança):** prévia, correção e quarentena prontas; faltam
  motivo nas correções, destino exibido antes de aprovar, limite de tentativas/reprocesso de
  FAILED, uso de `ChecklistExpectation` e deduplicação por conteúdo. Em produção a leitura de
  caixas está desligada e não há ClamAV configurado, então a cadeia fica parada.

Limites: validação em produção feita na demonstração; conta de teste real ainda não aberta pelo
proprietário; regras de vencimento e calendários continuam rascunho até aprovação no console
(`/platform/agenda-tributaria/`); notificações e busca não foram exercitadas com dados reais.

## V-279 — Varredura crítica em produção com Playwright e corte de texto (06/10/2026)

- **Método:** Playwright em `https://cica-contabil.fly.dev` (demo pública), 22 telas em 1440 e
  375 px; métricas de posição da primeira linha de dados, rolagem lateral, erros de console e
  inventário de todo texto renderizado com 40+ caracteres. Zero erro de JS; zero rolagem lateral.
- **Achados sistêmicos corrigidos:** "Como usar" em linha própria (agora no cabeçalho; no celular
  na linha do título); 100 eyebrows literais acima de títulos; títulos secundários repetindo o
  `h1`; avisos de demonstração duplicando a faixa global; ~70 frases explicativas (descrições de
  seção, passos, status que repetiam o rótulo, segunda linha de estados vazios); "Nenhuma …
  selecionada" ocupando linha; abas Meu trabalho/Carteira/Gestão como cartões vazios.
- **Equipe:** lista primeiro, convite recolhido; demo sem e-mails sintéticos. Primeira pessoa de
  1.077→367 px (desktop) e 1.621→415 px (celular).
- **Primeira linha de dados (desktop → celular, antes→depois):** Modelos 794→485 / 1.342→652;
  Radar 698→472 / 1.115→878; Triagem 651→556 / 901→731; Atividades 724→703 / 754→584;
  Guias 838→721 / 1.267→1.132; NFS-e 688→651 / 963→894.
- **Texto restante:** só fatos (contagens, datas, motivo de impedimento), custo, limite, formato de
  arquivo e efeito legal (ciência DTE). Fontes: Microsoft UX Guide "User Interface Text"; Krug.
- **Triagem (fase 7):** reprocessar com limite de 3 tentativas automáticas, deduplicação por
  SHA-256 dentro do escritório, motivo obrigatório ao trocar empresa/tipo; correção de empresa
  move a atividade sem evidência para a empresa certa (antes a troca era recusada).
- **Infra:** gunicorn 26 registrava `Control server error: Permission denied` a cada boot;
  `--no-control-socket` no `fly.toml` e `Dockerfile`.
- Local: 1.192 testes aprovados, seis skips; Ruff e `makemigrations --check` limpos.

## V-280 — Visão geral e download NFS-e mais diretos na operação (07/10/2026)

Registrada em paralelo como V-277 e renumerada na integração de 09/10/2026; a parte NFS-e foi
substituída pela tela de V-278 já em produção.

Escopo de D-280, verificado em localhost com `seed_demo`, SQLite e os gates `DEMO_ENTRY_ENABLED` e
`DEMO_SESSION_ISOLATION_READY` ligados. Perfil exercitado na interface: visitante da demonstração.

Visão geral (`/app/`): os cartões de prioridade renderizaram agrupados em "Prazo" (Em atraso, Para
hoje, Próximos 7 dias) e "Exceções" (Impedidas, Fonte indisponível). Tamanhos computados do número
confirmados em 40px para "Em atraso" com contagem, 32px para os demais prazos e 26px para as
exceções. Os cartões deixaram de exibir verbo próprio e passaram a declarar "Filtrar a fila" ou
"Filtrando a fila". O acionador "Como usar" foi confirmado dentro de `.page-header`, com
`aria-haspopup="dialog"`, e o diálogo abriu pelo clique.

NFS-e (`/app/nfse/`): os dois downloads renderizaram como cartões irmãos com escopo próprio. A
associação de formulários foi conferida no DOM: o botão do XML original resolve para
`nfse-original-xml-form` com os sete campos `report_*` mais `action`, está fisicamente dentro do
formulário de seleção sem gerar formulário aninhado (`form form` ausente), e o botão do pacote
resolve para o formulário de seleção. Ida e volta real dos dois downloads: `download_original_xmls`
retornou 200 `application/zip`, 1.735 bytes, `nfse-xmls-originais.zip`; `demo_download_selected` com
uma nota marcada retornou 200 `application/zip`, 519 bytes, `nfse-demonstracao-separadas.zip`. Os
nomes distintos preservam a separação exigida pela D-276.

Estados de seleção: sem seleção, a ação em lote permanece com `hidden` e o resumo exibe "Nenhuma
nota selecionada. Marque as notas na lista abaixo."; "selecionar a página" marcou as 6 notas, abriu
os 6 grupos de empresa — contra 1 aberto no início — e revelou a ação; desmarcar voltou ao estado
inicial; uma nota isolada produziu "1 nota de 1 empresa selecionada.". O resumo é `aria-live` polite.
Ordem de foco no bloco: botão do XML original, seleção da página, carteira inteira.

Filtro sem resultado (`?status=all&q=inexistente-zzz`): o bloco de download não é renderizado, o
atalho do cabeçalho não aparece e a âncora `#nfse-bulk-download` deixa de existir junto com ele,
restando o estado vazio com "Limpar filtros". Com notas no filtro, o atalho existe e a âncora
resolve.

Responsividade: em 390×844, `.nfse-download-options` colapsa para uma coluna e os grupos da Visão
geral empilham com cartões em duas colunas; `scrollWidth` igual a `clientWidth` nas duas telas, sem
overflow horizontal.

Automação: `ruff check` sem apontamentos; `manage.py check` sem issues; `makemigrations --check
--dry-run` sem mudanças; suíte integral com 1.136 testes aprovados, 145 subtests e 7 pulados por
limitação de ambiente preexistente (Playwright opcional, OCR local, locks de PostgreSQL).
`ruff format --check` acusa 144 arquivos, condição confirmada como anterior a esta entrega
comparando `views.py` contra `HEAD`; nenhuma reformatação foi feita.

Limites: não houve captura de tela — o painel do navegador não desenhou durante a sessão e a
verificação visual foi feita por DOM e estilo computado. UI/UX Pro Max, Watermelon e Playwright não
estavam disponíveis e não foram consultados. A variante de escritório não-demo, com seleção por
empresa e exportação Domínio, foi coberta apenas pela suíte automatizada, sem inspeção visual. Não
foram exercitados os demais perfis, temas claro/escuro, volumes de múltiplas páginas nem leitor de
tela. Dados fictícios e locais; não houve deploy, consumo externo, custo ou homologação. V-280 cobre
os pontos pedidos em D-280, não a auditoria integral da etapa 11.

### V-280.1 — Segunda rodada, sobre a validação acima (07/10/2026)

Escopo de D-280.1. Medições em 1920×950, a largura relatada pelo proprietário, com a faixa da
demonstração presente.

Altura até as notas: topo da lista de 995 px para 686 px e primeira nota de cerca de 1.120 px para
811 px, com duas empresas visíveis dentro da dobra de 950 px. Alturas por bloco após a mudança:
indicadores 49 px (antes 121), cabeçalho do painel 96 px (antes 131), filtros 91 px inalterados e
barra do pacote 66 px, contra cerca de 210 px do bloco de cartões que ela substitui. Os relatórios
saíram de antes para depois da lista, confirmado por `compareDocumentPosition`.

"Como usar" foi conferido com a mesma cor de fundo computada da ação principal do dia,
`rgb(168, 208, 196)` nos dois elementos.

Função preservada após a reorganização: seleção nos quatro estados, com a ação em lote oculta sem
seleção, 6 notas marcando os 6 grupos de empresa e abrindo todos, e retorno ao estado inicial ao
desmarcar. Ida e volta dos dois downloads novamente em 200 `application/zip`, com 1.735 e 519 bytes.
Nenhum formulário aninhado. Barra `sticky` no desktop e `static` em 390×844, sem overflow
horizontal. Filtro sem resultado não renderiza botão do XML original, barra do pacote nem a âncora
`#nfse-bulk-download`, restando o estado vazio com recuperação.

Testes: `test_paused_company_nfse_history_and_download_preserve_access_boundaries` falhou porque
assertava a frase anterior do painel para empresa pausada. A asserção foi atualizada para o novo
texto e reforçada com `assertNotContains` da chamada operacional, passando a garantir o
enquadramento em vez de uma substring frouxa. Foi acrescentado
`test_nfse_center_places_each_download_where_its_scope_lives`, que fixa a ordem barra do pacote →
lista → relatórios, a declaração do formulário do XML original antes do botão que o aciona, a
concordância no singular do rótulo e a ausência da ação em lote sem seleção. Esse teste roda sobre
escritório não-demo com exportação Domínio, cobrindo por asserção a variante que não pôde ser
inspecionada visualmente.

Limite revisto: a tentativa de inspecionar visualmente o escritório não-demo falhou porque
`seed_personas` vincula as personas ao mesmo escritório de demonstração; a variante continua sem
captura, agora com cobertura estrutural explícita. Permanecem válidos os demais limites de V-280:
sem capturas de tela, sem Playwright, sem leitor de tela, sem temas claro/escuro, sem volume de
múltiplas páginas, dados fictícios e locais, sem deploy, consumo externo, custo ou homologação.

### V-280.2 — Ancoragem do download no cabeçalho da NFS-e (07/10/2026)

Escopo de D-280.2. Em 1920×950: título termina em x=409 e o contador começa em x=419, a 10 px dele;
a ação termina em x=1630 contra x=1652 da borda do cabeçalho, dentro do respiro de 22 px. A altura
do cabeçalho permanece 96 px e o topo da lista permanece em 686 px, ou seja, a ancoragem não
devolveu altura à tela.

Em 390×844 a ação passa a ocupar a largura inteira, 312 px dentro do respiro lateral, contra 208 px
antes da correção; `scrollWidth` igual a `clientWidth`, sem overflow. A regra de largura que não
produzia efeito foi corrigida em vez de removida, com a causa anotada no próprio arquivo.

Filtro sem resultado continua sem renderizar a ação, com o contador exibindo "0 resultados".
Limites de V-280 e V-280.1 permanecem; em especial, segue sem captura de tela e sem Playwright.

## V-281 — Motor de cálculo do Lucrums portado e conferido contra o contrato

Registrada na branch `codex/lucrums`/`codex/siescon-adapter` com outra numeração e renumerada na
integração ao `main` de 09/10/2026, porque os números já existiam lá: D-108…D-121 → D-281…D-294,
V-105…V-116 → V-281…V-292 e Q-39…Q-43 → Q-41…Q-45. Mensagens de commit antigas mantêm os números
originais.

Data: 22/09/2026. Ambiente: desenvolvimento local (`config.settings.test`, SQLite em
memória). Nenhuma chamada externa, cobrança, deploy ou dado de cliente. Escopo: fase 1
da etapa 14, conforme D-281 a D-285 — domínio, motor e serviços, sem interface e sem
ingestão.

- **O que foi portado:** `calc.py` e `normalize.py` sem alteração de conta; onze modelos
  de domínio e métrica; o casador de pessoas; e `recompute_competencia` com os serviços
  de custo, agrupamento por raiz de CNPJ, deduplicação entre ERPs e códigos de ERP. Cerca
  de 10.300 linhas de Python existiam na origem; entraram as que compõem essas partes.
- **O que sustenta a fidelidade:** `contracts/calculations/v1.json` veio junto, com os
  treze contratos de consulta cujos SHA-256 do manifesto foram conferidos um a um e não
  divergiram. O teste de cálculo lê cada vetor do contrato e compara valor a valor, sem
  editar nenhum. Um teste adicional ancora o custo horário vigente em 37,09/h para o
  exemplo de referência e recusa a conta aposentada pela auditoria de setembro
  (`salário × 1,40 ÷ 176`, que dá 23,86/h — 37% a menos), inclusive verificando que as
  constantes não voltaram ao módulo.
- **Diferenças deliberadas em relação à origem, todas registradas em D-282 e D-285:** a
  entidade `Empresa` não foi portada e a carteira continua sendo `hub.ClientCompany`, com
  `CompanyErpProfile` carregando os campos de ERP; a coluna cifrada de razão social não
  veio, porque `ClientCompany.name` é coluna em claro por desenho anterior da CICA e
  cifrar aqui deixaria o nome exposto lá do mesmo jeito; as duas colunas aposentadas pela
  auditoria não foram criadas, já que a tabela nasce vazia; e `last_seen_run` está ausente
  em todos os modelos porque depende do ciclo de ingestão, que é a fase 3.
- **Consequência verificada:** a carteira deste módulo são as empresas com perfil de ERP.
  Empresa cadastrada apenas no hub, sem perfil, não ganha linha de métrica — mesmo destino
  que a origem dava à empresa sem documento.
- **Testes:** 65 aprovados nos quatro arquivos `tests/test_profitability_*`, com 89% de
  cobertura no app (piso de 85%). A suíte inteira ficou em 863 aprovados e 3 ignorados,
  sem regressão. `ruff check .` limpo no repositório, `mypy src` sem apontamentos no app,
  `manage.py check` sem problemas e `makemigrations --check --dry-run` sem alterações
  pendentes.
- **Limites desta validação:** nada foi executado contra ERP real, agente, rede ou
  navegador. Não há tela, não há ingestão e o módulo ainda não aparece no catálogo nem na
  navegação — isso é fase 2. A margem depende de Q-41, que segue aberta: o levantamento de
  origem não encontrou fonte de honorários em nenhum dos dois ERPs, então com dado real o
  módulo apura custo e horas, não rentabilidade. Q-42 permanece necessária antes de a
  margem ir à tela como número.

## V-282 — Ingestão do ERP para Rentabilidade, no protocolo do agente vigente

Data: 22/09/2026. Ambiente: desenvolvimento local (`config.settings.test`, SQLite em
memória, Celery síncrono). Nenhuma chamada externa, agente real, rede, cobrança ou dado
de cliente. Escopo: fase 3 da etapa 14, conforme D-281, D-282, D-284 e D-287.

- **O que entrou:** o catálogo de consultas fixado por SHA-256 vindo do Lucrums; o
  processamento por conjunto de dados, com identidade de linha por hash mais ordinal,
  reconciliação que marca em vez de apagar e orçamento de rejeição; os modelos de
  execução e página; e quatro pontos de entrada no protocolo `api/agent/v2` — catálogo,
  abertura, página e fechamento — mais a declaração de falha pelo agente.
- **O que não entrou, e por quê (D-287):** a cifra de envelope da origem. O agente da
  CICA já se autentica por mTLS com assinatura do corpo e a CICA já cifra em repouso com
  chave rotacionável; um segundo sistema de chaves cobriria um trecho já coberto, ao
  custo de ser operado, girado e auditado. A página fica cifrada em repouso pelo campo da
  própria CICA, com soma de verificação do conteúdo em claro conferida antes de aplicar.
  Também não entrou o preflight por escritório: o indicador de contrato validado continua
  vindo do manifesto, o que mantém os três contratos ainda não validados fora de despacho.
- **A ponte de D-282 verificada em comportamento:** a linha do ERP procura a empresa que a
  carteira já tem — por documento, por `dominio_code` e por fim na gêmea do outro ERP —
  antes de cadastrar uma nova. Só o Domínio escreve `dominio_code`; o Siescon numera o seu
  próprio cadastro, e gravar esse número no campo que NFS-e, conciliação e DTE usam para
  casar empresa faria uma delas achar a empresa errada. Quando o escritório exige código
  Domínio, uma empresa existente apenas no Siescon é recusada em vez de entrar por um
  caminho que o formulário não atravessa.
- **Dois defeitos próprios encontrados e corrigidos, ambos com teste:** o perfil de ERP
  era relação um-para-um, o que impedia duas gêmeas de apontarem para a mesma empresa; e o
  `distinct` das métricas não valia, porque a ordenação padrão do modelo entra no SELECT e
  a distinção passava a ser por empresa e código — duas linhas de métrica para a mesma
  empresa violam a chave única.
- **Autenticação:** não foi reimplementada. As três funções do `agent_v2` ganharam nome
  público e são importadas; há teste provando que um agente revogado deixa de ser aceito
  também por este caminho.
- **Desligada por padrão:** `PROFITABILITY_SYNC_ENABLED=false`. Nesse estado o catálogo
  volta vazio e nenhuma execução é aberta. O conector não é criado sob demanda.
- **Testes:** 51 aprovados nos dois arquivos novos (`ingest` e `agent`), 118 no módulo,
  916 na suíte inteira sem regressão, 86% de cobertura no app. `ruff check .` limpo,
  `mypy src` sem apontamentos no app, `manage.py check` e `makemigrations --check` limpos.
- **Limites desta validação:** nenhum agente real, nenhum ODBC, nenhum ERP, nenhuma rede.
  O ciclo foi exercitado com páginas construídas no teste, não lidas do Domínio ou do
  Siescon. Os três contratos não validados no manifesto seguem fora de despacho, e o perfil
  Siescon do conector depende de Q-44. Nada de tela ainda: o módulo continua sem aparecer
  no catálogo e na navegação.

## V-283 — Módulo Rentabilidade declarado e visão geral da carteira

Data: 22/09/2026. Ambiente: desenvolvimento local (`config.settings.test`, SQLite em
memória). Nenhuma chamada externa, agente, cobrança ou dado de cliente. Escopo: primeira
parte da fase 2 da etapa 14, conforme D-281, D-282, D-283 e D-288.

- **Declaração:** código `profitability` no catálogo de módulos, migração de escolhas,
  entrada em `module_catalog` apontando para `profitability:overview`, grupo "Gestão" na
  navegação e azulejo no painel com os clientes de margem negativa ou em atenção. A rota
  foi conferida por `reverse`, porque entrada de catálogo com rota que não reverte quebra
  a navegação inteira.
- **Tela:** visão geral por competência, com totais de honorário, custo e resultado da
  carteira e a lista da menor margem para a maior, paginada de 20 em 20.
- **O fecho de D-282 do lado da interface:** a tela lê `context["companies"]`, que é a
  carteira filtrada por `CompanyAccessGrant`, e não a do escritório. Há teste provando que
  um colaborador com acesso a uma empresa vê só a linha dela, e que o inquilino vizinho não
  aparece. Era exatamente isso que a decisão de não criar uma segunda entidade de empresa
  preservou.
- **Falta de dado não vira margem:** cliente sem hora no mês aparece como "Sem horas no
  mês", não como margem cheia, e o cabeçalho diz quantos estão nessa situação. Na lista,
  "sem dados" e "custo incompleto" usam borda tracejada em vez da cor das faixas, para não
  serem lidos como resultado. Isso atende a regra de D-98 a D-106 no que já é possível sem
  Q-42, que segue necessária para o limiar de cobertura da carteira como um todo.
- **Por D-288 o módulo fica fora dos módulos padrão do cadastro** enquanto Q-41 e Q-43
  estiverem abertas. O teste de cadastro existente continua passando sem alteração.
- **Restrições respeitadas:** nenhuma dependência de front foi introduzida — sem build,
  sem Tailwind, sem HTMX, sem CDN e sem script inline, conforme D-283 e a CSP vigente. O
  CSS do módulo usa os tokens do workspace.
- **Testes:** 12 aprovados em `tests/test_profitability_module_django.py`, cobrindo módulo
  desligado, colaborador fora do escopo, escopo de carteira, isolamento entre inquilinos,
  acesso anônimo e a navegação. Suíte inteira em 928 aprovados e 3 ignorados, sem
  regressão. `ruff check .`, `mypy src`, `manage.py check` e `makemigrations --check`
  limpos.
- **Limites desta validação:** a tela foi renderizada em teste com massa fictícia, não em
  navegador contra ambiente real. Faltam as demais telas da fase 2 — ficha do cliente,
  colaboradores, horas, análises e configuração do módulo — e os gráficos de D-286. A
  margem exibida continua dependendo de Q-41 para ter honorário de verdade.

## V-284 — Telas do módulo Rentabilidade portadas para templates

Data: 22/09/2026. Ambiente: desenvolvimento local (`config.settings.test`, SQLite em
memória). Nenhuma chamada externa, agente, navegador, cobrança ou dado de cliente.
Escopo: fase 2 da etapa 14, conforme D-281, D-282, D-283, D-286 e D-288.

- **Telas entregues:** visão geral da carteira (V-283), colaboradores com a seção de
  vínculos do ERP, ficha da pessoa com a composição do custo anual, horas, análises por
  recorte, configuração do cálculo e a seção de rentabilidade dentro da ficha de empresa
  que o hub já tinha. As telas de lista de clientes e de conectores do projeto de origem
  não foram portadas: a CICA já as tem em `hub:companies` e `hub:settings`.
- **Fidelidade ao cálculo, verificada na tela:** a ficha do colaborador exibe R$ 64.690,00
  de custo anual, R$ 37,09 de valor-hora e R$ 46,37 de valor-hora produtivo para o
  exemplo de referência — os mesmos valores do vetor de `contracts/calculations/v1.json`,
  agora conferidos pela interface e não só pelo serviço.
- **Por D-286 o gráfico de evolução é SVG desenhado por script próprio** servido de
  `static/`, sem biblioteca externa, sem build, sem CDN e sem script inline, respeitando a
  CSP vigente. A mesma série sai como tabela ao lado — é ela que leitor de tela percorre e
  que sobrevive à impressão —, e por isso o SVG é `aria-hidden`. Mês sem dado é desenhado
  vazio em vez de omitido.
- **Falta de dado não vira número em nenhuma tela:** sem horas suficientes, custo,
  resultado, margem e honorário sugerido saem como travessão, com a explicação ao lado;
  sem salário vigente o custo do colaborador também é travessão, e não zero.
- **Restrições de papel:** salário e custo aparecem somente para administrador, e somente
  administrador decide um vínculo do ERP ou altera um parâmetro de custo. Sessão de
  suporte somente-leitura não grava. Há teste para cada uma.
- **Gravar um parâmetro reprojeta todas as competências na hora.** Sem esse passo, a
  carteira só mudaria na importação seguinte enquanto a ficha do cliente, que recalcula a
  cada pedido, mudaria na hora, e as duas telas passariam a se contradizer.
- **Por D-288, ampliado nesta entrega:** o módulo ficou fora também da demonstração, não
  só do cadastro. Uma demonstração que abre o módulo já o está anunciando, e
  `docs/cica-module-truth.md` não autoriza texto público sobre ele enquanto Q-41 e Q-42
  seguirem abertas. A lista passou a viver em um lugar só,
  `module_catalog.self_service_module_codes()`.
- **Testes:** 25 em `tests/test_profitability_screens_django.py` e 14 em
  `tests/test_profitability_module_django.py`. Suíte inteira em 955 aprovados e 3
  ignorados, sem regressão. `ruff check .`, `mypy src`, `manage.py check` e
  `makemigrations --check` limpos.
- **Limites desta validação:** as telas foram exercitadas por requisição em teste, com
  massa fictícia, e não em navegador contra ambiente publicado — inspeção visual,
  responsividade real, leitor de tela e temas lado a lado continuam pendentes e pertencem
  à etapa 11. O gráfico foi verificado pelo dado que a página emite, não pelo desenho
  renderizado. A margem exibida continua dependendo de Q-41 para ter honorário de verdade,
  e Q-42 segue necessária para o limiar de cobertura da carteira.

## V-285 — Conector Windows unificado, com catálogo fixado por hash

Data: 22/09/2026. Ambiente: desenvolvimento local em macOS, com o SDK .NET 10 compilando
os alvos `net8.0` e `net8.0-windows`. Nenhum Windows, nenhum ODBC, nenhum ERP, nenhuma
rede e nenhum agente instalado. Escopo: fase 4 da etapa 14, conforme D-80, D-284, D-287,
D-289 e D-290.

- **Achado anterior ao porte, e o mais importante desta entrega:** o agente Windows **não
  compilava**. `AgentClient` passava um `Uri` para um parâmetro `string` desde o commit
  `0ac1038`, e nenhum fluxo de integração contínua construía esse projeto — por isso o erro
  sobreviveu no ramo principal sem ninguém notar. Corrigido com uma sobrecarga, e os quatro
  projetos do agente entraram no CI, que é o que teria apanhado isso. `EnableWindowsTargeting`
  permite compilá-los em Linux; o pacote continua sendo gerado e assinado no Windows.
- **O que veio do conector do Lucrums:** o catálogo de consultas incorporado no binário e
  conferido por SHA-256. Até aqui o SQL do agente da CICA vivia solto no código-fonte e
  nada garantia que a consulta executada na máquina do escritório fosse a que a nuvem
  espera. Agora a nuvem manda o código do contrato e o hash que espera, o SQL sai do
  catálogo, e os dois lados conferem antes de executar. Divergência derruba o serviço na
  subida, com a razão no log, em vez de falhar calado num ciclo noturno.
- **O catálogo ficou numa biblioteca separada** (`Cica.Agent.Contracts`), sem Windows e sem
  identificador de runtime, para ser testável em qualquer máquina — inclusive num CI que
  não seja Windows. O projeto do serviço é autocontido para `win-x64` e não podia ser
  referenciado por um teste fora do Windows.
- **Por D-289 tudo permanece em `net8.0-windows`:** `Convert.ToHexStringLower`, que é do
  .NET 9, virou `ToHexString` com `ToLowerInvariant`.
- **Por D-80 o pacote continua único:** o ERP vem da configuração em vez de compilado no
  binário, como o conector de origem fazia com dois instaladores. Instalação antiga sem o
  campo é do Domínio, que era o único perfil que existia.
- **A ponte ODBC de 32 bits entrou, autorizada por D-290.** O serviço é x64 e continua
  sendo; o Pervasive, que o Siescon usa, só publica driver de 32 bits. A ponte fala por
  entrada e saída padrão, sem rede e sem arquivo temporário, e a credencial nunca vai pela
  linha de comando. A conversão de valores é a mesma do serviço: na origem havia duas
  cópias, uma de cada lado da ponte, e duas cópias de uma regra de conversão concordam até
  alguém corrigir uma delas. Newtonsoft ficou de fora — `System.Text.Json` atende, e uma
  dependência a menos é uma a menos para acompanhar num binário que roda dentro do cliente.
- **Nesta entrega, as checagens de registro de 64 bits passaram a valer só para o perfil
  Domínio.** Aplicá-las ao Siescon recusaria justamente a instalação que a ponte existe
  para atender. V-287 completou esse ponto ao validar o DSN Siescon na visão de 32 bits.
- **Testes:** 17 aprovados em `agent-windows/tests/Cica.Agent.Tests`, cobrindo a carga do
  catálogo com os contratos reais, o recorte por ERP quando o código da consulta é o mesmo
  nos dois, a recusa de consulta não validada e de modo fora do contrato, e a conversão de
  valores, inclusive decimal em máquina com região em português. Os quatro projetos
  compilam sem erro. A suíte Python seguiu em 955 aprovados.
- **Limites desta validação:** nada foi executado contra Windows, ODBC, Domínio, Siescon ou
  agente instalado. A ponte de 32 bits foi compilada, não exercitada — não há Pervasive
  aqui. O envio de páginas ao servidor foi escrito contra os pontos de entrada validados em
  V-282, mas não exercitado ponta a ponta com um agente real. A revisão do instalador WiX
  que faltava nesta entrega foi feita em V-287; o atualizador automático do conector de
  origem foi excluído por D-291 e não é pendência deste porte. A instalação real, a
  assinatura do pacote e o piloto permanecem na etapa 12 por D-86.

## V-286 — Ficha analítica do cliente no módulo Rentabilidade

Data: 22/09/2026. Ambiente: desenvolvimento local (`config.settings.test`, SQLite em
memória) em macOS. Nenhuma chamada externa, agente, ERP, cobrança ou dado real de cliente.
Escopo: continuidade da fase 2 da etapa 14, conforme D-281 a D-288.

- **A linha da carteira agora abre uma análise própria do cliente**, preservando
  `hub.ClientCompany` como entidade única. A ficha reúne competência, honorário, horas,
  custo, resultado, margem e honorário sugerido; depois abre o mesmo fato em evolução,
  horas automáticas × F9 por dia, atividades manuais, equipe, unidades do grupo,
  comparações e histórico. O resumo transversal continua na ficha da empresa do Hub.
- **A ausência de dado permanece explícita:** sem base de custo não são calculados margem
  nem honorário sugerido; custo incompleto mostra a quantidade de horas sem custo. O
  histórico remove apenas competências totalmente vazias e mantém até doze meses úteis.
- **A autorização foi aplicada também aos dados derivados.** A empresa da rota precisa
  pertencer a `context["companies"]`; horas, atividades, unidades e médias usam somente a
  carteira permitida por `CompanyAccessGrant`. Um cliente fora desse recorte responde 404,
  e sua métrica não entra na média mostrada. Custo individual da equipe permanece visível
  apenas a dono ou administrador, como nas telas de colaboradores já validadas em V-284.
- **A interface segue D-283 e D-286:** template Django, CSS e o mesmo gráfico SVG próprio,
  sem SPA, build, CDN ou biblioteca externa. A série visual também sai como tabela, e as
  diferenças de horas preservam sinal positivo, negativo ou zero.
- **Testes específicos:** 37 aprovados em
  `tests/test_profitability_screens_django.py`, incluindo detalhe completo, navegação da
  carteira, recusa por empresa, média limitada ao acesso, ausência de sugestão sem custo e
  ocultação de custo individual para operador. A suíte integral ficou em 967 aprovados,
  3 ignorados e 11 subtestes aprovados. `ruff check`, `ruff format --check` no recorte,
  `mypy`, `manage.py check`, `makemigrations --check --dry-run` e `git diff --check`
  ficaram limpos.
- **Limites:** o caminho foi renderizado por requisição com massa fictícia, não inspecionado
  em navegador ou leitor de tela; essa prova continua na etapa 11. A margem ainda depende
  da fonte de honorários de Q-41 e do limiar de cobertura de Q-42, e o módulo permanece
  fora do cadastro e da demonstração por D-288. Nenhum Windows, ODBC ou ERP real foi
  exercitado; a homologação operacional continua na etapa 12.

## V-287 — Configurador Domínio/Siescon e revisão do MSI único

Data: 22/09/2026. Ambiente: desenvolvimento local em macOS, com SDK .NET 10
compilando alvos .NET 8 e validação estática do WiX/YAML. Nenhum Windows, driver ODBC,
ERP, rede, pacote assinado ou instalação foi exercitado. Escopo: continuidade da fase 4
da etapa 14, conforme D-80, D-284, D-289, D-290 e D-291.

- **A ponte x86 deixou de ser um arquivo sem caminho de configuração.** O configurador
  único agora oferece Domínio Web, Domínio Local e Siescon Local. Domínio lê apenas DSN
  SQL Anywhere na visão de 64 bits; Siescon lê apenas DSN Pervasive/PSQL na visão de
  32 bits e testa a conexão executando a ponte instalada. Usuário e senha viajam no JSON
  pela entrada padrão da ponte, não pela linha de comando nem pelo log.
- **O perfil de fonte virou contrato compartilhado** entre serviço e configurador:
  `dominio` exige SQL Anywhere de 64 bits; `siescon` exige ponte de 32 bits e dispensa
  esse driver. Fonte desconhecida continua recusada. A configuração DPAPI passa a gravar
  explicitamente `SourceSystem`, mantendo Domínio como compatibilidade para configuração
  antiga que não tenha o campo.
- **O WiX permanece um único produto e foi revisto:** descrição genérica para os sistemas
  locais, reparo da mesma versão permitido, compressão alta, atalho permanente
  **CICA → Configurar CICA Agent** e abertura automática do configurador somente em
  instalação interativa — instalação silenciosa não abre interface. O diagnóstico agora
  considera a ponte x86 parte obrigatória do pacote.
- **O build ficou falha-fechada:** limpa somente suas pastas controladas de publicação,
  confere serviço, configurador, ponte e script antes do WiX e verifica cada retorno do
  `dotnet`. Um job `windows-latest` passou a gerar o MSI e comparar o SHA-256 real com
  `release.json`; o autoatualizador do ProjetoARD não foi portado, em conformidade com
  D-291.
- **Provas locais:** serviço, configurador e ponte compilaram em Release com zero aviso e
  zero erro; 20 testes .NET passaram, incluindo os dois perfis e a recusa de fonte
  desconhecida. `dotnet format --verify-no-changes` passou nos arquivos/projetos tocados,
  o XML do WiX e dos projetos passou em `xmllint`, e o workflow passou no parser YAML.
  A regressão Python permaneceu em 967 aprovados, 3 ignorados e 11 subtestes aprovados.
- **Limite decisivo:** o WiX informa que só suporta Windows. A tentativa deliberada de
  gerar o MSI em macOS parou nesse limite e não é contada como falha do pacote nem como
  prova de construção. O novo job Windows ainda precisa executar; instalação, assinatura,
  DSN, ponte real e sincronização com ERP continuam para a etapa 12. O layout Siescon
  permanece inferido e requer o adaptador/homologação da etapa 04.

## V-288 — Revalidação local da etapa 14 e correção da herança visual

Data: 28/09/2026. Ambiente: macOS, branch local `etapa-14-rentabilidade`, servidor
de revisão isolado com SQLite e dados fictícios. Os `pull --ff-only` de CICA e
ProjetoARD confirmaram `main == origin/main`, respectivamente em `d501fbe` e
`d9d4ebb`; não havia commit remoto novo. A branch da etapa 14 segue com 20 commits
à frente da `main` da CICA e alterações locais preservadas.

- O contrato `contracts/calculations/v1.json` é idêntico ao do ProjetoARD
  (`e37dc1e14ab7281fa8a3dff0a752edcbefb8dca73152368a9635da5241e1972f`).
  `ruff check .`, MyPy (207 arquivos), `manage.py check`, conferência de migrações
  e `git diff --check` passaram. Serviço, configurador e ponte x86 compilaram em
  Release sem avisos; os 20 testes .NET passaram. A checagem de formatação .NET
  revelou e corrigiu somente espaços e quebras de linha em dois arquivos do serviço.
- A suíte Python aprovou 967 testes, ignorou 3 e aprovou 11 subtestes. **O portão
  documental de cobertura global de 85% falhou:** 80,11%; o pacote
  `src/apps/profitability` atingiu 87%. `ruff format --check` nos sete arquivos
  Python alterados passou; a checagem de todo o repositório encontra 92 arquivos
  antigos fora do formato tanto nesta worktree quanto na `main` atual.
- A revisão em navegador encontrou que todos os templates de Rentabilidade
  substituíam `extra_head` e omitiam os estilos herdados de `hub/workspace.html`.
  A ficha do Hub tinha a mesma omissão. Foi acrescentado `{{ block.super }}` aos
  oito templates afetados. Após a correção, visão geral e ficha do cliente foram
  inspecionadas visualmente em 1280 px e 390 px, sem overflow horizontal nem erro
  de console; Colaboradores, Horas, Análises e Configuração também foram abertas
  nos dois tamanhos, com estilo do workspace e sem overflow. Os 169 testes
  específicos de Rentabilidade passaram após a correção. Não houve teste com
  leitor de tela nem homologação de toda a jornada da etapa 11.
- O catálogo ainda marca como não validados `dominio/salaries`,
  `dominio/billing_services` e `siescon/taxation`. A sincronização de Rentabilidade
  segue desligada por padrão. O MSI não pôde ser construído em macOS e o job
  Windows continua sem execução observada; não houve ODBC, ERP, agente instalado,
  assinatura, piloto, publicação nem dados reais. Q-41 a Q-43 seguem abertas.

**Resultado:** a implementação local avançou e a regressão funcional passou, mas
a etapa 14 não está concluída nem pronta para uso operacional ou oferta. Permanecem
o portão de cobertura global, a prova do MSI em Windows, o adaptador Siescon da
etapa 04, a validação visual/acessível integral da etapa 11 e a homologação da
etapa 12, além das decisões Q-41 a Q-43.

## V-289 — Branch Lucrums e identidade de empresas com documento repetido

Data: 28/09/2026. Ambiente: branch local `codex/lucrums`, derivada da etapa 14;
`main` da CICA permanece separada em `d501fbe`. A revisão do ramo de laboratório
do ProjetoARD identificou um caso que a incorporação ainda não protegia:
matriz e filial podem chegar com o mesmo documento. A correção foi implementada
na CICA, sem substituir o corte de origem `d9d4ebb` fixado por D-281.

- Três testes de regressão cobrem códigos distintos do Domínio com documento
  repetido, correspondência das duas gêmeas no Siescon e lançamento de honorário
  à empresa certa. Um quarto garante que, quando documento e razão são ambíguos,
  o honorário fica sem empresa em vez de ser atribuído arbitrariamente.
- A ingestão conserva todos os perfis de um mesmo documento/razão no contexto.
  Um perfil com código ERP já ocupado não é reaproveitado para outro código;
  gêmeas de outro ERP são escolhidas por razão quando há mais de uma candidata.
- `pytest -q` com cobertura: 971 aprovados, 3 ignorados, 11 subtestes; os 36
  testes focados da ingestão também passaram. `ruff check`,
  formatação dos arquivos Python alterados e MyPy em 207 arquivos passaram.
  `manage.py check` e `makemigrations --check --dry-run` passaram. Os 20 testes
  .NET passaram. A última execução global com cobertura marcou **80,09%**, ainda
  abaixo do piso de 85%; o pacote Rentabilidade marcou **87,10%**. A cobertura
  global mede toda a CICA, inclusive módulos de outras etapas.

**Limites:** o MSI ainda precisa de execução observada no CI Windows. Os
contratos de dados pendentes, ERP/ODBC real, instalação, piloto e aceite da etapa
12 não foram exercitados. Q-41 a Q-43 continuam abertas; portanto, não há
afirmação validada de margem ou oferta comercial do Lucrums.

## V-290 — Primeiro MSI único construído no CI Windows

Data: 28/09/2026. Branch `codex/lucrums`, PR em rascunho #1. O primeiro job
`agent-package` encontrou ICE38/ICE43/ICE57 no atalho do configurador:
o componente usava chave HKLM para um atalho não anunciado no menu de programas.
O KeyPath foi corrigido para HKCU conforme a regra do Windows Installer. Na
execução [36450694685](https://github.com/Mewstacks/CicaContabil/actions/runs/36450694685),
o job Windows **passou**: publicou serviço x64, configurador x64 e ponte ODBC x86,
gerou `CicaAgent.msi` e conferiu no `release.json` a versão e o SHA-256 do MSI.
O job `agent` no Linux também passou. O WiX emitiu WIX1076 (upgrade da mesma
versão permitido por configuração); foi aviso, sem falha de construção.

**Limite:** isto comprova construção e consistência do pacote no CI, não
instalação, execução do serviço, conexão ODBC/ERP, assinatura ou piloto. O job
geral `verify` ainda estava nos builds Docker no momento deste registro.

## V-291 — Prioridade do código Domínio e receita ausente na Rentabilidade

Data: 28/09/2026. Ambiente: branch `codex/lucrums`, dados fictícios em SQLite.
O teste de regressão mostrou que a ingestão contrariava a prioridade declarada
em D-282: ao encontrar o mesmo documento num perfil Siescon, ligava a linha
Domínio a ele antes de consultar o `dominio_code` já existente no Hub. A busca
foi reordenada; o cadastro com código Domínio prevalece sem mover o perfil do
outro ERP. Essa divergência entre os cadastros ainda requer reconciliação humana.

A ficha do cliente também apresentava resultado negativo e margem de 0% quando
as horas tinham custo, mas o honorário mensal não havia chegado. O campo
`mensalidade_nao_disponivel` agora impede que a interface trate ausência como
valor zero confirmado: ficha, histórico e carteira mostram traço e explicação;
custos e horas continuam disponíveis. A série JSON usa `null` para margem sem
receita e o SVG interrompe a linha nesses meses, sem conectar pontos vizinhos.

- Testes focados: 37 de ingestão e 38 de telas; regressão integral: **973
  aprovados, 3 ignorados e 11 subtestes**. Ruff, MyPy em 207 arquivos, Django,
  migrações, `git diff --check` e sintaxe JavaScript passaram. Um ensaio Node
  confirmou dois segmentos separados por um mês sem honorário. Cobertura global
  **80,09%** (piso 85%); pacote Rentabilidade **87,11%**.
- D-282 ainda descreve a relação de perfil ERP como um-para-um, enquanto a
  implementação e os testes permitem um perfil por ERP no mesmo cliente. Foi
  pedido esclarecimento ao responsável antes de alterar essa decisão.

**Limites:** não houve nova inspeção visual em navegador, leitor de tela,
instalação/ERP real ou dado autorizado. Q-41 a Q-43 e o aceite das etapas 11/12
continuam pendentes.

## V-292 — Contrato de leitura Siescon e isolamento do conector

Data: 28/09/2026. Ambiente: macOS local, branch `codex/siescon-adapter`
partindo de `codex/lucrums`; testes Python com SQLite de teste e compilação
.NET 8 dos alvos Windows. Nenhuma conexão a ERP/ODBC, DSN, share, dado de
cliente ou script DDF foi executada.

- O agente agora compara as colunas retornadas com o manifesto antes de emitir
  a primeira linha. A comparação inclui a ponte x86 Siescon e o caminho x64
  Domínio; colunas preenchidas pelo contexto, como empresa e competência da
  folha, ficam fora da expectativa SQL. Divergência produz falha visível.
- A API só despacha uma origem com seu próprio `Connector` habilitado. Um
  conector Domínio não habilita Siescon nem abre execução dessa origem.
- `siescon/users` foi marcado não validado: seu SQL devolvia `situacao=1` para
  todos os usuários, sem confirmação dos campos @1485/@1604. `taxation`
  permanece não validado. `companies` e `salaries` seguem como contratos
  exercitados na origem, ainda sem prova no ambiente autorizado da CICA.
- Suíte Python integral: **975 aprovados, 3 ignorados e 11 subtestes** antes
  da inclusão de um teste adicional de isolamento; a suíte focada de ingestão
  e API passou com 58 testes, e a API foi reexecutada após esse teste.
  Os **23 testes .NET** do catálogo/contrato passaram, e serviço e ponte compilaram
  sem avisos. MyPy do arquivo alterado, Ruff, Django, migrações sem alterações,
  `dotnet format` e `git diff --check` passaram.

**Limites:** o layout Btrieve é inferido; estrutura de colunas não prova
semântica ou tamanho de registro. Faltam ensaio dos DDFs em cópia autorizada,
conferência com a tela do Siescon, fonte de contas/lançamentos e layout de
importação contábil. A exportação Siescon continua recusada. A etapa 04 segue
em andamento; não há homologação, deploy ou liberação comercial.

## V-293 — Guia funcional de QA (09/10/2026)

Pedido: documentar o CICA para QA na raiz. Foi criado `CICA-QA.md` com visão do sistema, perfis,
ambientes, funções por área, percursos, casos negativos, matriz transversal, critérios D-73,
modelo de registro de defeito e limites de homologação. O README aponta ao guia; a checklist da
etapa 00 e o registro de execução receberam a entrega.

Fontes lidas: plano mestre vigente, decisões D-109/D-275/D-277/D-280/D-281–294, dúvidas únicas,
validações anteriores, etapa 00 e etapas funcionais, README, arquitetura, rotas Django e índice
do manual de homologação externa. O conteúdo distingue implementação local, demo, produção e liberação.

Validação desta entrega: conferência estática de links relativos e `git diff --check` dos arquivos
alterados. Nenhum teste de aplicação, navegação, integração externa, dado de cliente ou deploy foi
executado: a alteração é somente documental. V-293 não substitui as provas por release nem fecha
Q/PC/etapa funcional.

## V-294 — Inventário de fluxos e plano de finalização (10/10/2026)

Pedido: revisar código, botões, fluxos e conexões Serpro para planejar a conclusão. D-295 registra a confirmação do responsável de que a validação externa de importação NFS-e está concluída; não foi solicitado comprovante nem repetido o teste.

Foram gerados `docs/planejamento/inventario-rotas-2026-10-10.csv` (366 rotas Django, 191 do admin) e `docs/planejamento/inventario-controles-2026-10-10.csv` (1.216 controles em 111 dos 116 templates examinados). As 307 referências estáticas a `{% url %}` encontradas foram comparadas aos nomes de rota, sem nome ausente. A extração não executa os controles, não inclui toda a UI dinâmica e não comprova permissão, acessibilidade ou efeito.

O catálogo Integra contém 19 operações. Inspeção de `tasks.py` mostrou revalidação de acesso nos workers DCTFWeb/PARCSN e ausência aparente no worker de lote DTE depois da aprovação (F-01). O token usa chave global de cache (F-02); ambos são riscos para reprodução/correção, sem incidente observado. Não houve chamada real ao Serpro, emissão, ciência ou consumo pago.

Regressão `.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider`: 1.376 aprovados, 6 ignorados, 145 subtestes aprovados e 4 erros de setup por `PermissionError` no temporário padrão do pytest. Repetição dos arquivos afetados com `--basetemp .pytest_tmp_audit`: 6 aprovados. Os cinco arquivos de teste focados de DTE/Integra haviam aprovado 54 testes. Testes simulados não homologam integração externa. Não houve inspeção renderizada nesta entrega nem alteração de UI, código de produção ou deploy.

Plano e critérios por jornada/serviço em `docs/planejamento/auditoria-fluxos-serpro-finalizacao-2026-10-10.md`. A etapa 11 segue aberta para execução dos controles; a etapa 12 segue aberta para homologação e aceite por módulo. PC-03/Q-39 deixam de bloquear por D-295; os outros gates do plano mestre permanecem.

## V-295 — Proteções locais de despacho DTE e cache OAuth Serpro (10/10/2026)

Implementadas D-296 e D-297. Antes de cada consulta de Caixa Postal, `dispatch_dte_run` revalida a associação ativa do solicitante, sua carteira, o módulo Integra e a empresa. Se qualquer condição foi revogada após a aprovação, o item recebe `authorization_revoked`, a reserva é liberada como não faturável e `IntegraClient.call` não é acionado. O cache OAuth passou a ter chave derivada por hash de ambiente, credenciais, contratante e certificado configurado; a chave não contém segredo e impede reutilização entre identidades diferentes.

Validação: 38 testes de DTE/Integra aprovados em 43,56 s, incluindo revogação entre fila e execução e duas credenciais/ambientes. Ruff dos quatro arquivos alterados, MyPy de `tasks.py`/`client.py` e `git diff --check` aprovados. Não houve Serpro real, custo, produção ou navegador. A concorrência em PostgreSQL e a rotação em ambiente autorizado permanecem pendentes; V-295 não homologa as 19 operações externas.

## V-296 — Confirmação do comando administrativo Serpro (10/10/2026)

Implementada D-298. `integra_smoke` faz somente prévia por padrão e não instancia o cliente de rede. A chamada externa exige `--execute`; quando o ambiente é produção e o serviço do catálogo é faturável, exige também `--approve-billable-production`. O catálogo continua fechado e não foi criada rota livre.

Validação: 41 testes de DTE/Integra/smoke aprovados em 40,81 s; os três novos cenários verificam prévia, bloqueio de custo e execução explícita. Ruff e MyPy dos arquivos envolvidos passaram. Nenhuma chamada Serpro, dado real, custo, produção ou deploy foi realizado. O comando administrativo não substitui reserva de consumo, autorização por empresa ou homologação por serviço.

## V-297 — Regressão completa após proteções Serpro (10/10/2026)

Com `--basetemp .pytest_tmp_full_goal` dentro da área de trabalho, a regressão completa aprovou 1.385 testes e 145 subtestes em 184,02 s. Seis testes foram ignorados: um depende do Playwright Python, quatro dependem de locks/transações independentes em PostgreSQL e um é o cenário de concorrência de token também limitado a PostgreSQL. O temporário controlado evita o `PermissionError` do diretório padrão do pytest visto em V-294.

Esse resultado cobre regressão local da árvore atual, inclusive as proteções D-296–298. Não executa botões renderizados, serviços Serpro reais, custos, produção, restauração ou homologação externa.

## V-298 — Tentativa de abrir a matriz renderizada (10/10/2026)

Foram aplicadas as orientações de `ui-ux-pro-max` para foco visível, foco não encoberto e rótulo acessível de botões de ícone. O catálogo Watermelon foi consultado duas vezes, para dashboard contábil e tabela, sem correspondência. A referência de produtos reais usada para a futura execução preserva filtros por carteira/responsável, seleção em lote com escopo explícito e tarefas com dono/prazo/checklist; ela não muda a interface atual sem achado concreto.

O navegador integrado falhou antes de abrir aba (`windows sandbox failed: helper_unknown_error`). O checkout não tem o módulo Node `playwright`; a suíte Python já declara esse suporte opcional. Foram localizados `scripts/qa_ui_server.py`, `qa_ui_browser.cjs` e `qa_ui_extended.cjs`, que usam dados sintéticos, bloqueiam rede externa e fecham o navegador, mas não puderam iniciar sem o módulo. A inspeção estática não encontrou `outline: none`, `transition: all` ou `href="#"` nos arquivos pesquisados; as imagens de template encontradas têm `alt`, largura e altura. Isso não substitui navegador, teclado, viewport ou console.

O gate de execução por rota/botão da etapa 11 segue aberto. Nenhuma dependência foi instalada e nenhuma tela foi alterada nesta tentativa.

## V-299 — Reexecução renderizada isolada e correção de acessibilidade (10/10/2026)

Foi executado Playwright Node temporário contra `scripts/qa_ui_server.py`, com banco e mídia
sintéticos, rede externa bloqueada e Chrome local em modo sem interface. O navegador foi fechado
ao fim de cada cenário. A varredura alcançou 84 estados renderizados de 16 rotas em desktop e
celular, temas claro/escuro, sem overflow horizontal, controles sem nome acessível detectado,
ações de tabela comprimidas ou erros JavaScript de página. A persistência de tema foi exercitada
em login e página pública e passou após o roteiro aguardar a navegação assíncrona do formulário.

A inspeção renderizada achou dois `input` com o mesmo `id` em formulários concorrentes da
configuração da plataforma. D-299 separou os `auto_id` de franquia e disponibilidade, preservando
nomes e `POST`. O teste Django específico passou em 41,28 s; a inspeção Playwright autenticada
confirmou `id_copilot_trial_ai_included_requests` associado ao seu rótulo. Ruff e MyPy dos
arquivos Python alterados passaram.

A execução ampla ainda não é aceite de todos os botões: o roteiro encontrou seletores que não
correspondem à composição atual, cenários sem módulos habilitados na massa sintética e uma rota
`/app/ia/` que já não existe. O roteiro foi corrigido para esperar filtros via History API, usar o
menu da área de trabalho, aguardar a troca de tema e remover a rota obsoleta. A próxima execução
deve habilitar módulos e construir estados próprios por jornada antes de considerar DTE, OFX,
parcelamentos, NFS-e, guias ou triagem validados. Não houve chamada Serpro, dados reais, custo,
produção, deploy ou homologação externa.

## V-300 — Pull e diagnóstico do conciliador (26/10/2026)

Escopo D-300: atualizar o projeto local e verificar a comparação de extrato
bancário com os registros contábeis, detalhando o levantamento com a cliente em
Q-28/PC-19. Ambiente: macOS, interpretador `.venv`, settings de teste, SQLite
descartável e entradas exclusivamente fictícias. Nenhum ERP, banco de cliente,
servidor publicado, API paga ou instalação Windows foi acessado.

- `git status --short` inicial vazio, branch `main`. `git pull --ff-only`
  concluiu por fast-forward de `d501fbe` até `aad2f5a`: **59 commits**. Comparação
  `git rev-list --left-right --count HEAD...origin/main`: **0/0**. Não houve
  reset, descarte, commit ou push. As alterações finais são a documentação desta auditoria.
- Relidos plano/decisões/validações/etapas após a atualização, incluindo
  D-108/D-134–137/D-218/D-227–230/D-295, e inspecionados importação, duas cadeias
  de conciliação, modelos, sincronização, consultas e agente nativo. A fonte
  enviada pelo agente e backup é `CTEXTRATO_BANCARIO_LANCAMENTO_ITEM`, não uma
  extração independente de partidas do Razão. `AccountingEntry` não alimenta
  automaticamente os candidatos `JournalEntry` do fluxo avançado.
- `.venv/bin/python -m pytest tests/test_reconciliation.py tests/test_reconciliation_module.py tests/test_intelligence_sync_django.py tests/test_module_activities.py -q`:
  **94 testes e 24 subtestes aprovados, 1 ignorado**, em **30,84 s**. Skip:
  Tesseract/idioma português indisponível. Não é nova regressão integral.
- Quatro sondas em `.tmp/auditoria-conciliador-2026-10-26/test_diagnostico.py`
  confirmaram: dois movimentos usando o mesmo candidato sem controle de
  capacidade; confirmação sem validar `direction`; o mesmo FITID duplicado em
  arquivos diferentes; e upload de conta divergente bloqueado no fluxo novo,
  mas ainda confirmável pela fila OFX. **4 reproduções confirmadas em 15,47 s**.
  São testes de observação do comportamento inadequado, não provas de correção.
  Primeira rodada: 3 falhas na própria fixture, por comparar data textual de um
  objeto recém-criado com `date` lida do banco; após recarregar o objeto da
  fixture, os quatro cenários confirmaram as lacunas. Nenhum código de aplicação
  foi alterado para obter esse resultado.
- `.venv/bin/python manage.py check --settings=config.settings.test`: sem
  problemas. `makemigrations --check --dry-run` com as mesmas settings: sem
  alterações. A primeira tentativa usou o caminho inexistente `src/manage.py`;
  somente a execução corrigida na raiz conta como validação. Nenhuma migração
  foi aplicada no banco de desenvolvimento.
- [Diagnóstico e roteiro](docs/planejamento/diagnostico-conciliador-2026-10-26.md)
  registram capacidades, lacunas, impactos, perguntas e material mínimo. Plano,
  checklist da etapa 09, Q-28 e registro de execução foram atualizados.
  `git diff --check` passou; os caminhos/links locais do material foram conferidos.

Limites: não foi exercitado navegador, OCR real, worker/Redis, PostgreSQL,
volume, instalação/upgrade .NET, conexão ODBC, importação no ERP, chamada
externa de negócio, custo, produção ou deploy. Não houve mudança de interface
ou aplicação. Exportação contábil Domínio permanece com gate próprio, falso por
padrão; o aceite NFS-e de D-295 não o substitui. As correções, fonte de Razão,
fotografia por conta/período e homologação contábil de PC-19 continuam pendentes.
A etapa 09 permanece aberta. D-74 dispensa repetir a pergunta local/Web para a
Fedrizzi já registrada; outro ambiente ou mudança precisa ser identificado.

## V-301 — Contrato do conciliador e perguntas de conclusão (27/10/2026)

Escopo D-301: confrontar o contrato fornecido e o esclarecimento sobre contas
a pagar/receber e alternativa fiscal com as capacidades já inspecionadas.

- PDF original lido no caminho informado pelo responsável em Downloads: quatro
  páginas extraídas com pypdf; páginas 1–4 renderizadas localmente com Poppler
  e integralmente inspecionadas. As páginas 2–3 confirmam escopo, DE-PARA inicial
  assistido por IA, implantação/testes e treinamento inicial. A data de entrega
  é 09/11/2026. Contrato e identificadores/assinaturas não foram adicionados
  ao Git. Assinaturas não tiveram validação criptográfica nesta análise.
- Identificada cliente diferente da Fedrizzi de D-74. A decisão anterior não
  autoriza nem comprova fonte, acesso, versão ou modalidade local/Web desta
  instalação. Q-28 recebeu esse detalhamento, sem solicitar credencial.
- Inspeção de `models.py`, `imports.py` e `reconciliation_service.py` confirmou
  origem genérica “Títulos ou obrigações” em arquivos e movimentos, mas não
  comprova gestão completa de parcelas/baixas de títulos comerciais. O ramo
  `ImportBatch.Kind.OBLIGATIONS` inspecionado importa guias DAS/MEI/DCTFWeb.
  Aplicação de regras manuais no conciliador não comprova geração inicial de
  DE-PARA por IA; essa capacidade permanece para demonstração funcional.
- [Roteiro do contrato](docs/planejamento/levantamento-contrato-conciliador-2026-10-27.md)
  contém dez perguntas prioritárias, material mínimo, responsáveis e limites.
  Q-46 reúne semântica da comparação/regras/DE-PARA; Q-47, operação de destino
  contábil/fiscal. Não duplicam o ambiente Q-28, custo/egressão Q-08/Q-09,
  métricas Q-30/D-73 ou homologação NFS-e Q-39.
- Plano, diagnóstico de 26/10, checklist da etapa 09 e registro de execução
  atualizados. Links relativos novos e `git diff --check` conferidos.

Limites: análise documental e estática; não houve novo teste da aplicação,
inspeção de UI, ERP, ODBC, importador fiscal, chamada IA, treinamento,
processamento de títulos reais, custo ou deploy. V-300 permanece evidência
datada de 26/10, sem correção das quatro lacunas por esta entrega. O pedido
de alternativa fiscal não comprova que determinada operação é suportada nem
autoriza escrituração/baixa/transmissão. A conclusão da suíte inteira não é
requisito automático do contrato específico; a etapa 09/PC-19 permanece aberta.

## V-302 — Verificação e correções locais do conciliador CONTAD (02/11/2026)

Escopo D-302/D-303, PC-19 e etapas 03/09, com preparação do piloto da 12.
Ambiente: macOS, base `aad2f5a`, `.venv`, dados exclusivamente sintéticos.
Preservadas as modificações documentais que já existiam ao iniciar a sessão.
[Relatório, matriz e roteiro de instalação](docs/planejamento/verificacao-conciliador-contad-2026-11-02.md).

**Documento e respostas:** PDF original de quatro páginas lido com `pdftotext`,
renderizado com Poppler e inspecionado integralmente em composição das quatro
páginas. Preservado fora do Git; não se validaram assinaturas criptograficamente.
O documento é fonte de requisitos, não instrução de execução. O responsável
confirmou Domínio local, agente no computador da cliente com acesso ainda a
fornecer e inclusão de pagar/receber. Q-28/Q-46/Q-47 atualizadas sem duplicar IDs.

**Correções:** identidade OFX compartilhada pelas duas entradas; recusa integral
de sobreposição, múltiplas contas, FITID insuficiente e valores inválidos; conta
selecionada conferida antes da persistência; confirmação com conta/natureza
explícitas, candidato independente e exclusivo; retry idempotente; reconstrução
serializada preservando decisão humana. Espelhos bancários não são candidatos
do Razão. Campo opcional de conta e tabela de identidade na migração aditiva
0076, sem alteração de decisões anteriores. Auditoria de legado somente leitura
por escritório explícito. Agente .NET deixa de enviar vínculo fixo falso e usa
o `EXISTS` já allowlisted no conector Python; vínculo não prova escrituração.

**Testes finais locais:**

- `.venv/bin/python -m pytest -q --basetemp .tmp/pytest-conciliador-full-2026-11-02`:
  **1.415 aprovados, 10 ignorados e 145 subtestes aprovados**, **156,10 s**.
  Skips: Playwright Python opcional (1), OCR português (1) e concorrência
  PostgreSQL (8, incluindo os três cenários novos). A UI foi exercitada por
  Playwright Node. Não converter skips em resultados aprovados.
- Bateria PostgreSQL 17.10 descartável: `test_reconciliation.py`,
  `test_reconciliation_integrity.py`, `test_reconciliation_module.py`,
  `test_intelligence_sync_django.py`, `test_intelligence_agent_django.py` e
  `test_edge_agent.py`: **125 aprovados, 1 skip OCR e 24 subtestes**, **67,58 s**.
  Cenários com conexões independentes provaram exclusividade do candidato,
  atomicidade dos uploads sobrepostos e preservação da confirmação humana
  diante de reconstrução concorrente. Instância própria via socket Unix em
  `.tmp/conciliador-pg`, sem usar PostgreSQL de outro projeto ou serviço externo.
- Regressão **integral PostgreSQL**, mesmos dados/serviços de teste e settings
  descartável: **1.423 aprovados, 2 skips e 145 subtestes aprovados**, **178,68 s**.
  Os dois skips foram somente Playwright Python opcional e OCR português;
  todas as concorrências da suíte foram executadas. Log `postgres-full-tests.log`.
- Ensaio sintético de 200 transações: **200 movimentos, 200 transações bancárias,
  200 identidades; zero erros**, **0,974 s** no SQLite local; todos ficaram em
  revisão, sem falsa conciliação automática. Reenvio sobreposto recusado, sem
  aumentar contagens. Não é a amostra independente nem prova de precisão D-73.
- Serviço, configurador e ponte x86: `dotnet build ... -c Release --no-restore
  -p:EnableWindowsTargeting=true`, todos **sem avisos/erros**. Testes de
  `agent-windows/tests/Cica.Agent.Tests`: **23 aprovados**. Compilação cruzada
  não executa ODBC, DPAPI, serviço ou instalador no Windows; MSI novo não gerado.
- Ruff dos arquivos Python alterados passou. MyPy passou em `reconciliation.py`,
  `reconciliation_service.py`, `imports.py` e `audit_ofx_integrity.py`.
  `views.py` conserva **dez erros anteriores fora do recorte**; a comparação
  com o conteúdo de HEAD via `--shadow-file` reproduziu os mesmos dez. Nenhum
  erro novo das alterações de conciliação permaneceu.
- Django check sem problemas, `makemigrations --check --dry-run` sem alteração
  pendente e `git diff --check` aprovado. Migrações executadas somente nos
  bancos sintéticos descartáveis; desenvolvimento e produção não foram tocados.

**Navegador:** UI/UX Pro Max aplicada a feedback/erro/foco e revisão da UI existente;
referência Xero consultada e Web Interface Guidelines atuais lidas. Watermelon
não estava exposto e Playwright MCP não estava disponível. Playwright Node do
runtime + Chrome local abriu aplicação não-demo sintética, com rede externa
bloqueada, e confirmou: rejeição de conta errada, importação válida, erro acionável
para sobreposição, candidato independente e confirmação; auditor com consulta
sem upload; 1440×960, 375×812 e 812×375, claro/escuro, teclado, foco visível,
movimento reduzido e ausência de overflow. Uma segunda passagem de seis estados
na aba OFX não encontrou erro de console ou de página. Contextos/browser fechados.
Capturas desktop e celular foram inspecionadas visualmente.

Evidências temporárias em `.tmp/auditoria-conciliador-2026-11-02/`:
`full-tests.log`, `postgres-tests.log`, `postgres-full-tests.log`, `ui-results.json`, `ui-console.json`,
`volume-results.json`, `overlap-desktop.png`, `light-*.png` e `dark-*.png`.
Os roteiros/fixtures temporários não são dados da cliente e não entram no Git.

**Ocorrências intermediárias corrigidas:** a primeira bateria apontou três
fixtures de confirmação que aceitavam espelho bancário sem conta/natureza e um
caso que esperava bloqueio somente no worker. Foram mantidos testes negativos
desses caminhos e preparados candidatos independentes explícitos para o caso
positivo; a proteção histórica do worker continua testada. O primeiro MyPy
precisou de `PYTHONPATH=src`. A primeira invocação do settings PostgreSQL
isolado precisou de chave artificial de teste; nenhum segredo real foi usado.
A primeira regressão ampla teve dois erros porque o teste NFS-e de migração
restaurava o banco apenas até 0067: corrigido seu `finally` para restaurar todas
as folhas atuais do grafo. A regressão final passou. Dois seletores do roteiro
Playwright foram ajustados ao nome real do botão e ao contêiner do modal;
nenhuma falha de produto foi ocultada para obter o resultado.

**Limites e estado:** etapa 09/PC-19 permanece aberta. Faltam fonte independente
de partidas do Razão via Domínio, integração integral das duas cadeias, títulos
comerciais com parcelas/baixas, DE-PARA inicial com IA, diferença/saldos nos dois
sentidos, layouts reais e aceite CONTAD. O acesso ao PC ainda será fornecido;
não houve instalação, DSN/ODBC real, dado de cliente, importação contábil no
ERP, worker/rede reais, recuperação/restore cronometrados, treinamento inicial,
IA externa, chamada paga, deploy, envio a terceiros ou liberação comercial.

## V-303 — Preparação do envio GitHub e lista de conclusão (02/11/2026)

Escopo D-304: consolidar e enviar todas as alterações pendentes do projeto ao
remoto GitHub já configurado, sem publicar aplicação, acessar ERP ou gerar custo
externo de negócio. Branch `main`, base `aad2f5a`, remoto `Mewstacks/CicaContabil`.
`git fetch origin` confirmou `HEAD...origin/main = 0/0` antes do novo commit.

- Relidos plano, decisões e validações vigentes, etapa 00 e os estados/checklists
  das etapas 00–14. A [lista de pendências](docs/planejamento/pendencias-conclusao-2026-11-02.md)
  diferencia o contrato CONTAD, a conclusão da suíte e a IA local posterior,
  respeitando Q-39/D-295 e as decisões Siescon já resolvidas.
- Incluídos diagnóstico/contrato anteriores ainda locais, correções, testes,
  migração 0076 e documentação V-302, preservando o trabalho existente.
- Workflows conferidos: push em `main` aciona `CI`; `Deploy Cobalchini` requer
  dispatch próprio. Não foi acionado workflow de deploy.
- Ruff global encontrou uma única linha longa no docstring de um script de
  diagnóstico de produção. A quebra de linha corrige apenas documentação;
  o script não foi executado. Ruff global, verificação de whitespace/links e
  inspeção do conjunto preparado para commit são as verificações desta entrega.
- Os testes de aplicação e agente não foram repetidos por esse ajuste textual:
  V-302 mantém a evidência mais recente (1.423 testes/145 subtestes PostgreSQL,
  23 testes .NET e UI Node); não tratá-la como homologação remota nova.

Temporários, bancos, dados de cliente, credenciais, PDF e assinaturas não fazem
parte do envio. Push/CI não aplica a migração em produção nem instala o agente.
**Confirmação de envio:** `git push origin main` concluiu de `aad2f5a` para
`1b978d4882a3308cb76fd5e325574749c8a653ed`. `git ls-remote --heads origin main`
retornou esse mesmo SHA e `HEAD...origin/main = 0/0`; árvore de trabalho limpa
após o envio. Sem force push, deploy, instalação ou acesso ao ERP. O registro
dessa confirmação segue em commit documental adicional; CI remoto é evidência
separada e não é declarado aprovado por sucesso do push.

## V-304 — Razão independente, ponte das filas e conferência Sicredi (03/11/2026)

Escopo D-305, PC-19, etapas 03/09 e preparação da 12. Base inicial
`b499cd12d158fc33f68b39a365f70044aa31d7e5`, árvore inicialmente limpa.
[Contrato e operação](docs/conciliacao-razao-normalizado.md) e
[matriz CONTAD atualizada](docs/planejamento/verificacao-conciliador-contad-2026-11-02.md).

**Fontes e decisões:** PDF Sicredi de seis páginas extraído com pdfplumber,
renderizado com Poppler e inspecionado em composição integral. OFX lido localmente;
ambos têm **163 movimentos**, iguais em data/valor/multiplicidade, zero sobras
nessa comparação bancária. Sequência de saldos conferida: **100 → 0 centavos**.
Não comprovam Razão ou equivalência dos formatos de conta. A imagem é assinatura
de e-mail, sem regras de negócio. O responsável confirmou títulos de origem
**Domínio** e saída de **relatório + arquivo para importação**; D-305 e Q atuais
atualizadas antes do comportamento dependente. Anexos tratados como dados,
mantidos fora do Git e sem envio externo.

**Implementação:** contrato CSV de partidas completas, hash/fingerprint/chaves,
idempotência e recusa atômica de inconsistências; migração aditiva 0077. Fonte
permanece rascunho e não pode ser reexportada como novo lançamento. Ponte das
duas filas com trava comum por empresa, capacidade do efeito bancário em
partidas compostas, confirmação/desfazimento, projeção em upload tardio e trilha
de decisão. Auditoria somente leitura detecta alocação compartilhada ausente.
Relatório CSV privado por fonte/conta/período, sobras nos dois sentidos e saldos
desconhecidos; recusa processamento incompleto e arquivo com hash alterado.
Sicredi textual conserva documento, página/região e saldo por linha, valida a
sequência e exclui lançamentos futuros.

**Verificações finais locais:**

- PostgreSQL 17.10 descartável em socket Unix próprio `.tmp/conciliador-pg/socket`,
  porta 55439, settings isolado e chave artificial. Comando: `PYTHONPATH=src:.tmp/conciliador-pg
  DJANGO_SETTINGS_MODULE=integrity_postgres_settings DJANGO_SECRET_KEY=...
  .venv/bin/python -m pytest -q --basetemp .tmp/pytest-ledger-full-pg-2026-11-03`.
  **1.452 aprovados, 2 skips e 151 subtestes aprovados em 212,71 s**.
  Skips somente Playwright Python opcional e OCR português. Concorrências
  executadas, inclusive disputa entre as duas filas pela mesma fonte e
  importações simultâneas de Razão sem duplicar partidas.
- Ensaio versionado com **200 lançamentos independentes sintéticos**, 400
  partidas, 200 movimentos OFX e 200 confirmações compartilhadas. Retry reutiliza
  as 200 chaves; relatório com zero sobras/diferença. Não é piloto CONTAD nem
  prova de precisão/cobertura/tempo operacional D-73. Primeira bateria SQLite:
  23 testes novos passaram em 36,38 s; os casos posteriores foram cobertos na
  regressão final PostgreSQL. Não houve nova suíte integral SQLite nesta entrega.
- Ruff global aprovado. MyPy aprovado nos seis serviços afetados: `ledger_import.py`,
  `bank_evidence.py`, `reconciliation_bridge.py`, `reconciliation_report.py`,
  `reconciliation.py` e `reconciliation_service.py`. `views.py` mantém os mesmos
  dez erros anteriores, reproduzidos com `--shadow-file` usando HEAD; nenhum
  novo erro. Django check sem problemas; `makemigrations --check --dry-run`
  sem pendência. Migrações somente em bancos de teste, sem tocar desenvolvimento/produção.
- Playwright Node/runtime + Chrome local, servidor não-demo sintético em
  127.0.0.1:8013, mídia/banco descartáveis e rede externa bloqueada: upload do
  Razão, estágio correto sem reaplicar regras, OFX, confirmação antiga refletida
  no fluxo avançado, download e desfazimento refletido na fila OFX. Auditor com
  carteira atribuída consulta sem upload. 1440×960, 375×812 e 812×375, claro/escuro
  efetivos, teclado, foco visível, movimento reduzido e ausência de overflow.
  Zero erros de console/página. Capturas desktop/celular claro/escuro inspecionadas;
  contextos/browser encerrados.
- UI/UX Pro Max aplicada; pesquisa local de design, referência oficial de
  [conferência Xero](https://central.xero.com/0/article/Bank-Reconciliation-Summary)
  e [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
  consultadas. Watermelon e Playwright MCP não estavam expostos; a inspeção
  executada foi Playwright Node. Identidade visual CICA preservada.

**Ocorrências corrigidas:** fixture de permissão usava `user` em vez de
`membership`; execução PostgreSQL isolada precisou de `DJANGO_SECRET_KEY`
artificial; MyPy identificou opcionais/variáveis reutilizadas/kwargs corrigidos.
O roteiro de navegador precisou recarregar navegação por hash para aplicar
cookies de tema/perfil e atribuir carteira ao auditor sintético. Nenhuma permissão
de produto foi alterada para obter resultado. Teste isolado e regressão final passaram.

Evidências ignoradas pelo Git em `.tmp/conciliador-2026-11-03/`:
`bank-pair-result.json`, `ledger-tests.log`, `postgres-focused.log`,
`postgres-full.log`, `mypy*.log`, `ui-results.json`, `conference-ui.csv` e capturas.
Os binários da cliente e reproduções visuais permanecem locais.

**Limites:** entrada normalizada não é adaptador direto Domínio homologado.
Não houve acesso ao PC, instalação/pareamento, SQL/ODBC real novo, implementação
de títulos/parcelas/baixas, execução IA/DE-PARA, importação/escrita ERP, worker/rede
reais, restore cronometrado, treinamento, aceite, envio, custo, push ou deploy.
Faltam campos/amostras/regras Q-28/Q-46, plano/mapa e gates Q-08/Q-09, layout e
importação contábil Q-47 e piloto D-73. Fonte Domínio e tipo de saída já estão
decididos; não perguntar novamente. Etapa 09/PC-19 e entrega contratual abertas.

Encerramento: servidor de QA e PostgreSQL descartável desta sessão foram
parados após a regressão. `git diff --check`, Ruff global, links novos e
comparação byte a byte dos logs MyPy de views atual/HEAD aprovados. Alterações
permanecem locais e revisáveis, sem commit/push; nenhum arquivo da cliente no diff.

## V-305 — MSI do agente testado em Windows descartável (03/11/2026)

Escopo D-306, etapa 03 e preparação da 12, pedido explícito para gerar/testar
agente após conferência de ausência do MSI local. Base `b499cd1`; alterações
D-305 preservadas. Código de empacotamento isolado em worktree/branch
`codex/agent-windows-validation`, sem merge em main, deploy ou dados da cliente.

**Evidência final Windows:** [run 41664064414](https://github.com/Mewstacks/CicaContabil/actions/runs/41664064414),
concluído com sucesso, SHA **`57acd4f9738209842f4d3be546859c164adcba88`**.
Runner padrão `windows-2022` (Windows Server 2022, build 10.0.20348), repositório
público; guard recusa instalar em máquina cliente/self-hosted ou com agente/configuração
preexistentes. Foram executados **23 testes .NET e 25 verificações de instalação**:
MSI/hash/manifesto, serviço automático LocalSystem, presença/arquitetura dos binários,
estado sem configuração, ACL, abertura/fechamento do configurador, execução da
ponte x86 com entrada recusada antes de ODBC, diagnóstico instalado, DPAPI sob
LocalSystem, recusa de servidor HTTP, reparo preservando configuração cifrada,
reinício após correção e remoção de serviço/binário. O teste não fornece DSN,
credenciais, certificado de cliente ou servidor de negócio real.

**Falha real corrigida:** run [41662010680](https://github.com/Mewstacks/CicaContabil/actions/runs/41662010680)
gerou/instalou/iniciou/removeu o MSI, mas reprovou a ACL herdada na pasta de
configuração. `Package.wxs` agora usa DACL protegida com `PermissionEx` para
SYSTEM/Administradores antes de gravar credenciais. O segundo run
[41663104581](https://github.com/Mewstacks/CicaContabil/actions/runs/41663104581)
comprovou ACL/configurador/ponte/diagnóstico e parou no timeout do estado seguinte.
O roteiro convertia uma data ISO já desserializada pelo PowerShell em string
local, perdendo frações de segundo e recusando estado recente. Corrigida a
conversão direta para DateTimeOffset, adicionado teste de precisão e captura
do estado em timeout; os critérios de estado/frescura foram mantidos. A rodada
final passou integralmente, inclusive DPAPI e recuperação. Pacotes reprovados
não foram disponibilizados como instaladores aprovados.

**Artefatos e conferência local:** MSI versão **1.0.0**, **97.790.959 bytes**;
SHA-256 **`0f2877a5872452506d94b770e51f8d95c03f9dec908da2af907ab0da54612393`**.
Após download, igualdade entre bytes locais, `.sha256`, `release.json` e
`installer-test.json` novamente conferida. Artefatos GitHub 13246525259 (pacote)
e 13246670242 (evidência), retenção de um dia. Cópia local preservada em
`agent-windows/artifacts/`, ignorada pelo Git; ZIP de transferência
`CicaAgent-1.0.0-teste-windows-x64.zip` com MSI, checksum, manifesto, inventário,
relatório de ensaio e instruções. ZIP **97.800.096 bytes**, CRC conferido;
SHA-256 `ae7bc7751eaea7c7b8a593e8b4aa71fc47cbca1dc3cf6c639cf1781a175d4c01`.

**Verificações locais adicionais:** `dotnet test ... -c Release --no-restore`
repetiu os **23 testes**, zero falhas/skips. Builds Release de serviço,
configurador e ponte passaram sem avisos/erros. Bateria Python
`tests/test_edge_agent.py tests/test_intelligence_agent_django.py
tests/test_intelligence_sync_django.py`: **23 testes aprovados em 58,32 s**, SQLite
sintético. Não repetir a regressão financeira V-304 como se fosse nova nesta entrega.
O build MSI conserva o aviso anterior WIX1076/ICE61 de upgrade na mesma versão;
zero erros e instalação/reparo efetivamente testados. Não alegar MSI sem avisos.

**Integridade do trabalho:** correção/teste/workflow/instruções copiados de volta
à árvore principal somente após sucesso, recusando sobrescrever edição prévia.
Hashes de 15 arquivos de aplicação/testes já modificados em D-305 foram conferidos
inalterados. Segredos, anexos, binários, logs de runtime e configuração não foram
commitados. Evidência temporária em `.tmp/agent-windows-2026-11-03/`, com TRX,
logs/JSON das três execuções e bateria Python. Arquivos transferidos permanecem
locais e não exigem que a cliente possua o repositório.

**Limites:** `Authenticode=NotSigned`. Checksum/proveniência CI não equivalem
à assinatura de editor; nenhuma compra/geração de identidade comercial foi
presumida. Pacote é para instalação de teste controlada. Não houve instalação
no PC da cliente, pareamento externo real, teste real SQL Anywhere/DSN/ODBC,
leitura/escrita no ERP, rede/restore reais ou homologação CONTAD. Razão/títulos
com parcelas/baixas e DE-PARA continuam nos gates próprios. Q-28 aguarda o
acesso prometido; o responsável não precisa repetir a origem Domínio nem a
inclusão de pagar/receber. Infraestrutura de produção não foi alterada.

Encerramento D-306: branch de teste enviada sem merge, confirmação remota em
`158e4ae3974af4294762244f7c72a7977bdb8443` (registro documental após o código
testado `57acd4f`). MSI/ZIP/relatório preservados na árvore principal; hashes
dos 15 arquivos de aplicação/teste preexistentes continuam idênticos. Ruff
global, diff e CRC/hash finais aprovados. Worktree isolada arquivada após a
cópia e confirmação do push (`archived_worktree` conferido); nenhum binário versionado.


## V-306 — Mesmo MSI testado em Windows 11 Desktop ARM64 (03/11/2026)

**Pedido/escopo:** D-307, “teste agora em windows 11 normal”. Resultado do
Windows 11 cliente separado do ensaio Server 2022 V-305. Não há declaração de
homologação do PC Intel/AMD ou do Domínio.

**Execução real:** [run 41669715057](https://github.com/Mewstacks/CicaContabil/actions/runs/41669715057),
job 126034515875, workflow `agent-windows-11-validation.yml`, commit
`57427c76dbc04edf4b8455c4ee721f0a276511e7`, sucesso. SO conferido antes da
instalação por CIM: **Microsoft Windows 11 Enterprise**, versão **10.0.26200**,
build **26200**, **ProductType=1** (cliente), SO/processo/runner **ARM64**.
A edição Enterprise é Windows Desktop; o runner não é Windows Server. MSI x64
com ponte x86 executado pela compatibilidade/emulação do Windows ARM64.

**Mesmos bytes:** baixado o artefato do run 41664064414 (código do pacote
`57acd4f9738209842f4d3be546859c164adcba88`), sem rebuild. MSI 1.0.0, SHA-256
`0f2877a5872452506d94b770e51f8d95c03f9dec908da2af907ab0da54612393`;
conferência fixa antes da execução e igualdade com relatório/copias locais.
Checksum/manifesto e os bytes do pacote anterior foram preservados.

**25 verificações aprovadas:** instalação silenciosa com saída 0; serviço
LocalSystem automático e em execução; binários x64/ponte x86 presentes; espera
sem configuração e sem ERP; ACL protegido para Administradores/SYSTEM; abertura,
loop de mensagens e fechamento normal do configurador; execução da ponte x86
com rejeição de entrada inválida antes de ODBC; diagnóstico instalado; DPAPI
LocalMachine lido pelo serviço e rejeição de HTTP; reparo MSI com saída 0 e
preservação da configuração cifrada; recuperação após correção e reinício;
remoção com saída 0 e ausência de serviço/executável. Inclui guard de precisão
de data e conferência MSI/hash/manifesto. Não houve alteração do código do
produto ou da proteção do ensaio para aprová-lo. Não repetidos .NET/backend:
as contagens 23/23 continuam evidência V-305, não novos testes desta execução.

**Evidências preservadas:** artefato GitHub **13248051379**,
`CicaAgent-windows-11-arm-validation`, **409.075 bytes**, digest do arquivo ZIP
`sha256:99ecf370b2d8f3e092328991e632d60e7e3ab69643ef54fd7724f77b69986c93`,
retido até 04/11/2026 16:02:16 UTC. Download local conferido:
`.tmp/agent-windows-11-2026-11-03/passed-run/` (logs instalação/reparo/remoção,
ambiente e relatório); cópia dos JSONs em `agent-windows/artifacts/windows-11-arm/`.
Relatório `passed=true`, 25 checks, `pairing_tested=false`, `real_odbc_tested=false`,
assinatura `NotSigned`. Diagnóstico confirma serviço Running, zero DSNs e nenhum
driver SQL Anywhere. O script não executou consulta de ERP ou pareamento.

**PC por RDP:** o responsável confirmou PC de teste e RDP, depois informou
sessão aberta e controle habilitado. A chamada de interface ainda retornou
**“Computer Use permissions are not granted”**, inclusive depois de reset do
runtime e nova tentativa. Nenhuma tela, SO/arquitetura ou instalação desse PC
foi inspecionada; não confundir a confirmação do usuário com uma ação realizada.
Orientação oficial de permissões consultada por OpenAI Docs (Acessibilidade,
Gravação de Tela e acesso do aplicativo no controle do computador); não houve
contorno do bloqueio. Teste Windows 11 **Intel/AMD via RDP permanece pendente**
até a ferramenta reconhecer o acesso. Não pedir novamente se há PC ou qual
ferramenta, nem solicitar senha no chat.

**Integridade e limites:** YAML/guardas/diff conferidos; os 15 arquivos de
aplicação/teste de D-305 continuam com os hashes preservados. Nenhum dado/anexo
ou binário versionado, merge em main, deploy, assinatura comercial, custo ou
acesso a ERP. Teste ARM64 não homologa drivers ODBC, o PC da cliente, interface
visual completa, queda de rede, pares mTLS ou piloto/aceite CONTAD.


## V-307 — Agente instalado e testado no Windows 11 Pro x64 por RDP (03/11/2026)

**Escopo/decisão:** continuidade D-307 após o responsável habilitar o helper.
Captura/controle liberados, conferidos por UI `Codex Computer Use` ligado em
Gravação de Tela e Acessibilidade. A evidência nova resolve a pendência de
Windows 11 Intel/AMD descrita em V-306, sem substituir as limitações de ERP.

**Ambiente real:** PC de teste disponibilizado pelo responsável por RDP;
CIM mostrou **Microsoft Windows 11 Pro**, versão **10.0.26200**, build **26200**,
**ProductType=1**, **AMD64**. Antes da instalação, serviço, configuração e
binário do CicaAgent estavam ausentes. Nenhuma instalação anterior foi alterada.
Não é o PC CONTAD nem prova de acesso ao Domínio da cliente.

**Pacote idêntico:** MSI 1.0.0 do run 41664064414, SHA-256
`0f2877a5872452506d94b770e51f8d95c03f9dec908da2af907ab0da54612393`, conferido
novamente no PC antes de executar. Download HTTPS temporário do artefato pelo
conector GitHub; nenhuma credencial enviada, listener, compartilhamento ou regra
de firewall criados. A colagem de arquivos/retorno por clipboard não estava
utilizável nessa sessão; não houve contorno de política de redirecionamento.
Anexos/dados de cliente não foram transferidos.

**24 verificações aprovadas:** guard de precisão de data, pin dos bytes e
MSI/hash/manifesto; instalação `msiexec /i` com saída 0; serviço automático
LocalSystem Running; quatro arquivos instalados; arquiteturas x64/x64/x86;
espera sem configuração; ACL protegido para SYSTEM/Administradores; inicialização,
abertura e fechamento do configurador; ponte x86 recusando entrada inválida antes
de ODBC; diagnóstico instalado via Windows PowerShell; DPAPI LocalMachine lido
pelo serviço com rejeição de HTTP antes de rede; reparo `/fa` com saída 0 e
preservação da configuração cifrada; recuperação após remoção apenas da própria
configuração sintética e reinício; agente conservado sem configuração ERP.
Relatório `passed=true`, `failure=null`, **24 checks**; `Get-Service` após o teste
confirmou **Running**. Não houve remoção do produto neste PC; os 25 checks de
V-305/V-306 incluem remoção nos runners, portanto as contagens são distintas.

**Roteiro específico de PC:** `agent-windows/test-windows11-pc.ps1` exige Windows
11 AMD64/admin/hash e recusa serviço/pastas/configuração existentes. Não usa o
guard GitHub nem falsifica variáveis de CI. Configuração sintética criada com
CreateNew e removida somente se seu hash continuar idêntico; conserva a instalação.
Primeira execução administrativa parou ao resolver `PSScriptRoot` nos padrões,
antes de instalar. Resolver caminhos pelo arquivo invocado e permitir caminhos
explícitos corrigiu a compatibilidade com Windows PowerShell. Parser aprovou
zero erros antes da repetição. SHA do roteiro efetivamente executado:
`d9ab1e87bd3c738ac1357273dc5f8f2897f524b822b18bc7e68405f5ce8f29e9`.
Política já existente `LocalMachine=RemoteSigned` foi conferida e mantida.
Nenhum bypass, alteração de segurança ou dependência nova foi necessário.

**Evidência:** relatório original, diagnóstico e logs de instalação/reparo
preservados em `%USERPROFILE%\Downloads\CicaAgent-PC-test-20261103-1330\validation\`
no PC. SHA-256 do JSON original, lido pela sessão:
`9e7f912d0b971404292686a6a57f6d942dbc7b06db6c2b3678342dde98f8943b`.
Cópia local de resumo transcrito da leitura do relatório em
`agent-windows/artifacts/windows-11-x64/windows-11-pc-summary.json`; não é alegada
cópia byte a byte do JSON original. Os campos passado/contagem/SO/hashes/limites
e serviço foram conferidos na tela. O MSI local original permaneceu intacto.

**Operação da sessão:** mudança temporária de Keyboard Mode para Unicode foi
explicitamente autorizada, registrada em D-307 e resolveu caixa/símbolos no
Windows Terminal. O console legado elevado não recebeu essa digitação; os
comandos foram preparados no terminal compatível e executados por RunAs normal.
Nenhum comando financeiro ou SQL foi executado. Configuração e credenciais do
ERP continuam ausentes. Manter o agente instalado em `awaiting_configuration`.

**Limites:** MSI **sem assinatura Authenticode**. Pareamento HTTPS/mTLS, DSN,
SQL Anywhere, consultas reais, rede/retomada e homologação CONTAD seguem pendentes.
Não inferir Razão/títulos/parcelas/baixas, importação ou aceite pelo sucesso do
instalador. Testes .NET/backend anteriores não foram repetidos nem recontados.
Sem deploy, merge, publicação do binário ou nova despesa nesta continuidade.


Encerramento V-307: configurador instalado aberto como administrador e
inspecionado visualmente, com endereço/código de pareamento vazios, sem salvar
ou testar conexão. Modo RDP devolvido a **Scancode** e visualização **tela cheia**
restaurada; captura final confirmou o configurador aberto na sessão. Conferência
local final confirmou SHA do MSI/roteiro e os 15 hashes preexistentes do
conciliador preservados. Artefatos de execução continuam fora do Git. Nenhum
push/merge/deploy adicional foi necessário para o ensaio no PC.

## V-308 — Conexão do conciliador no PC e travessia local da API (03/11/2026)

**Escopo:** D-308, pedido para testar o conciliador usando o agente instalado.
PC RDP de teste de V-307, distinto da cliente CONTAD. Código do MSI não foi
alterado/reinstalado. Preservadas todas as mudanças anteriores do conciliador.

**Verificação real Windows:** configurador instalado aberto, selecionado
Domínio Local. Encontrou DSN de sistema compatível e driver SQL Anywhere 16.
O botão `Testar conexão` tentou a conexão ODBC do próprio configurador e recebeu
**SQLSTATE 28000, Invalid user ID or password**. O código usa conexão com timeout
de dez segundos e `SELECT TOP 1 codi_emp FROM bethadba.geempre`; a autenticação
foi recusada antes da leitura. Não foi declarada leitura de empresa/lançamentos.
Não modificar/exibir credenciais ou repetir tentativas com senhas alternativas.
Solicitado ao responsável preencher os valores corretos diretamente no
configurador RDP e conferir o teste, sem senha pelo chat. Resposta pendente.

Nenhum `Conectar à CICA`, gravação de `agent.config`, pareamento, lote enviado,
SQL novo, escrita Domínio ou alteração de segurança. O estado Running sem
configuração do serviço permanece evidência de V-307, não nova consulta do
serviço nesta entrega. RDP devolvido à tela cheia; configurador conservado
em Domínio Local com o resultado visível. Scancode não foi alterado.

**Travessia nova com dados sintéticos:**
`tests/test_agent_reconciliation_pipeline.py`, sete cenários, exerce o endpoint
HTTP real Django `agent-v2-dominio-bank-entries` em banco isolado, usando HMAC
do contrato do cliente. Não executa o binário Windows nem uma conexão TLS/ODBC.

- Página com 500 itens, página final com um, repetição sem duplicar e mudança
  de vínculo no espelho. Exatamente 501 itens, sem desativar os da primeira
  página e sem atingir escritório alheio com o mesmo código de empresa.
- Recusa antes da persistência para página com 501 itens, tipos inválidos,
  assinatura incorreta, agente revogado e ausência de mTLS quando obrigatório.
  O caso mTLS verifica recusa, não autenticação TLS de ponta a ponta.
- OFX com valor/data iguais ao espelho não ganha Razão automaticamente.
  Confirmação é recusada e relatório mostra ausência de fonte independente.
  Após importar partidas independentes equilibradas pelo contrato local,
  confirmação humana compartilha alocação nas duas filas. Reenvio do agente
  preserva essa decisão; relatório termina sem sobras/diferença e conserva
  cobertura/aceite falsos e saldo contábil desconhecido explícito.

**Execuções:** PostgreSQL 17.10 existente de QA, reiniciado somente no socket
Unix próprio `.tmp/conciliador-pg/socket`, porta 55439, sem TCP. Settings
`integrity_postgres_settings`, `PYTHONPATH=src:.tmp/conciliador-pg` e chave
artificial, sem serviços externos. Bateria nova: **7 aprovados em 16,69 s**.
Regressão dirigida: **157 aprovados, 24 subtestes e 1 skip em 30,32 s**.
Os sete novos estão incluídos nos 157, não devem ser somados outra vez.
Arquivos: `test_agent_reconciliation_pipeline`, `test_independent_ledger`,
`test_reconciliation_integrity`, `test_reconciliation`,
`test_reconciliation_module`, `test_bank_evidence`,
`test_intelligence_agent_django`, `test_edge_agent` e
`test_fedrizzi_dominio_setup_django`. Inclui os cenários concorrentes PostgreSQL
e os 200 lançamentos independentes **sintéticos** de V-304. Skip exclusivamente
OCR português indisponível. Não foi repetida a suíte integral de 1.452 testes.
XMLs: `.tmp/agent-reconciliation-results.xml` e
`.tmp/agent-conciliador-pg-results.xml`. Ruff do teste novo e diff-check aprovados.

**Anexos autorizados:** `compare_bank_files` executado novamente localmente,
somente leitura, sobre os originais PDF/OFX Sicredi: **163 movimentos em cada**,
zero sobras por data/valor considerando multiplicidade, sequência de saldos
válida, R$ 1,00 inicial/R$ 0,00 final. Relação entre as contas ainda exige
confirmação, e os dois documentos são fonte bancária, não Razão independente.
Resultado com hashes em `.tmp/agent-conciliador-2026-11-03/sicredi-check.json`,
fora do Git; não houve transferência desses anexos para o Windows ou IA.

**Limites e próximo passo:** corrigir autenticação no RDP, definir destino e
recorte do pareamento antes de enviar dados e então comprovar o ciclo do serviço
Windows. Razão/títulos diretos, parcelas/baixas, layout/importação Domínio,
DE-PARA com IA revisado e piloto/treinamento/aceite reais D-73 continuam abertos.
Não houve deploy, push, merge, chamada cobrada ou homologação CONTAD.

Encerramento V-308: PostgreSQL de QA parado após os testes. Ruff e diff-check
finais aprovados; os 15 arquivos preexistentes de aplicação/teste mantiveram
os hashes de referência. Resumo do resultado observado e da bateria em
`.tmp/agent-conciliador-2026-11-03/summary.json`, sem segredos ou dados bancários.

## V-309 — Conexão Domínio corrigida no Windows 11 (03/11/2026)

**Escopo/causa:** continuidade D-308, mesmo PC de teste autorizado de V-307.
O responsável esclareceu que a confirmação anterior foi no ODBC do Windows
ou no Domínio. O erro 28000 do configurador 1.0.0 ainda era reproduzível.
Teste .NET somente leitura com autenticação do DSN retornou `connected=true`,
`minimum_query_passed=true`, sem SQLSTATE. Mesma consulta mínima já existente,
sem imprimir registro. O configurador acrescentava UID/PWD e sobrescrevia a
autenticação do DSN, diferentemente do adaptador Python de D-74.

**Correção:** opção explícita para usar autenticação do DSN em Domínio Local,
marcada em configuração nova, com campos não utilizados desabilitados e
credenciais vazias salvas nesse modo. Configuração antiga sem o indicador
`UseDsnAuthentication` conserva o modo explícito. Sem fallback de identidade.
Helper comum com OdbcConnectionStringBuilder no teste/processadores locais,
incluindo substituições vazias no modo explícito e escape de valores. Backup
Domínio Web/Siescon conservam seus modos. Controles ficam bloqueados no teste.

**Código/testes:** branch `codex/agent-windows-validation`, código no commit
`605436b85f8a4bf50b519faab3938693b2c19a5c`, roteiro de atualização no commit
`50c0463d5d042b1261eb92ce8f278f3cbe0be732`. Código copiado à raiz após conferir
igualdade dos arquivos anteriores com a base. Builds locais de serviço e
configurador: zero avisos/erros; 28 testes .NET aprovados.
[CI 41706460758](https://github.com/Mewstacks/CicaContabil/actions/runs/41706460758):
**28 testes .NET e 25 verificações do instalador aprovados** em Windows Server
2022 descartável, incluindo DPAPI/configuração antiga, reparo, reinício e
remoção. Contagens local/CI não se somam. Cinco casos novos verificam DSN sem
substituição, escape, DSN vazio e credenciais explícitas vazias sem fallback.
Expectativas iniciais incorretas dos testes foram corrigidas; primeiro build
sem restore exigiu restauração normal. Rodadas finais sem falhas.

**Pacote:** MSI 1.0.1, **97.795.055 bytes**, SHA-256
`33063a23d26eafc4865193da01db629d580df44006c3c3c46ec16c38ff8b9b28`,
conferido no Mac/PC antes de executar. **Sem assinatura Authenticode**.
Artefatos MSI/manifesto/inventário/CI/TRX em
`agent-windows/artifacts/windows-1.0.1/`, ignorados pelo Git; versão 1.0.0
anterior preservada. Não incluiu dados de cliente em CI.

**PC real:** Windows 11 Pro AMD64 de V-307. Roteiro específico
`test-upgrade-windows11-pc.ps1`, SHA-256
`530c3a4e3e4e51d07f715f0084e606daaa8dba3134a4357db43150b1d007bd75`,
conferido no PC e parser PowerShell com zero erros. Guards exigem versão
anterior 1.0.0, configuração ausente, GUI fechada e hash/manifesto aprovados.
RunAs normal, sem alterar/contornar política de execução. Cinco verificações
aprovadas: origem/hash, saída MSI 0, versão instalada 1.0.1.0, serviço automático
LocalSystem Running e `awaiting_configuration` sem ERP/pareamento. Sem reinício
do PC ou remoção explícita ao terminar; agente mantido instalado.

Relatório original/log no PC em
`%USERPROFILE%\Downloads\CicaAgent-1.0.1-DSN-test\validation\`.
SHA-256 de `windows-11-upgrade.json`:
`0dee73a08811ee8a9b045ac8424b270ddc9d89d91cd3a9427bd8dac09e2089bf`.
O original registra `gui_odbc_tested=false`, pois antecede o teste visual.
Não foi reescrito. Resumo local transcrito, identificado como tal, em
`agent-windows/artifacts/windows-1.0.1/windows-11-upgrade-summary.json`, separa
essa execução da observação posterior; não é cópia byte a byte do original.

**Conexão/UI real:** configurador instalado 1.0.1 aberto como administrador,
Domínio Local, autenticação do DSN marcada/campos desabilitados. Teste mostrou
**“Conexão confirmada. O Domínio está pronto para sincronizar.”**, reconferido
na captura final. Desmarcar habilitou campos; Tab/foco e Espaço em Scancode
permitiram remarcar. Em Unicode, Espaço não alternou o controle nesta sessão;
Scancode restaurado. Configurador maximizado no Windows, RDP mantido na
apresentação encontrada nesta continuidade; endereço/código/pasta vazios, sem
salvar. Senha armazenada no DSN não foi lida/copiada/exibida. Conexão mínima
usa contexto interativo administrativo; **ODBC sob LocalSystem não testado**.

Aplicados ui-ux-pro-max, pesquisa Watermelon e diretrizes de interface:
controle nativo, rótulo/AccessibleName, teclado/estado ocupado. Catálogo React
Watermelon não fornece controle WinForms; nenhum componente instalado.
Playwright não controla essa janela WinForms; teste nativo via CUA no Windows,
sem espelho web ou declaração de auditoria completa de acessibilidade.
Referências: [SAP, parâmetros ODBC](https://help.sap.com/docs/SAP_SQL_Anywhere/88bc65cec07241c5928ecd297d15cf13/811d64756ce2101485cda41548aba922.html?version=17.0),
[Microsoft, acessibilidade WinForms](https://learn.microsoft.com/dotnet/desktop/winforms/advanced/walkthrough-creating-an-accessible-windows-based-application),
[Watermelon](https://ui.watermelon.sh/home) e
[diretrizes web](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md).

**Bloqueio hospedado:** POST vazio no endpoint HTTPS de cadastro retornou
**503 — “A autoridade certificadora do agente não está configurada.”** Sem
CSR/código/identidade/dados financeiros; não criou agente. Evidência em
`server-enrollment-readiness.json` nos artefatos locais. `_sign_csr` exige
arquivos em `EDGE_AGENT_CA_CERT_PATH`/`EDGE_AGENT_CA_KEY_PATH`. Não geramos CA
ou alteramos produção. Fly CLI somente leitura retornou saída 1, sem fornecer
configuração utilizável; não afirmar nomes/valores dos segredos remotos.
Configurar emissão não comprova mTLS de ponta a ponta; sem reduzir TLS.

**Limites:** nenhuma gravação ERP, configuração salva, pareamento ou lote
financeiro enviado; sem merge/deploy, infraestrutura ou custo novo. Backend
não repetido: V-308 conserva 157 testes/24 subtestes e limites sintéticos.
Os 15 arquivos financeiros preexistentes conservaram seus hashes. Conexão
não comprova sincronização do serviço, Razão, títulos/parcelas/baixas,
importação, piloto de 200 itens reais, recuperação, treinamento ou aceite.
Próximo passo: autorização da mudança hospedada e destino/recorte antes de
parear/enviar dados, conforme procedimento da etapa 12.

Encerramento V-309: TRX local de 28 testes preservado em
`agent-windows/artifacts/windows-1.0.1/local-dsn-auth.trx`; resumo transcrito
gravado e confrontado com os campos observados. Hashes do MSI/roteiro e dos
15 arquivos financeiros conferidos novamente; diff-check aprovado. Worktree
isolada arquivada com confirmação, após preservar código na raiz, commits na
branch e evidência necessária fora do checkout. Sem PR/merge/deploy. A janela
do configurador foi deixada com conexão confirmada, sem salvar ou parear.

## V-310 — Implementação do plano de testes CONTAD (04/11/2026)

Escopo D-309, PC-19/etapas 03/09/12. Alterações locais anteriores preservadas;
base `b499cd12` em main, sem merge/deploy. Aprovação do plano não foi tratada
como autorização para transmitir a carteira, consumir IA ou importar no ERP.

Implementado:

- Geração, aprovação e exportação recusam movimento com alocação confirmada,
  inclusive parcial e história OFX anterior. Trava comum de empresa serializa
  com confirmação/revisão. Confirmar invalida rascunho/aprovação derivados;
  lançamento exportado exige conferência explícita antes de conciliar.
  Desfazer não reaproveita aprovação invalidada. Auditoria não reescreve legado.
- Manifesto financeiro persistido, validado na emissão/resgate/configuração,
  protocolo compatível, recusa de sync financeiro sem recorte. Agente filtra
  empresa, IDs de extrato e datas antes de enviar; backend recusa página mista
  inteira fora de empresa/conta/competência/revisão. Piloto não aciona módulos
  de backup/arquivos/rentabilidade/IA ou sync v1/genérico. Migração 0031 aditiva.
- CA/CSR/chave/validade/renovação endurecidas; backend exige segredo privado
  de gateway além de identidade verificada e HMAC quando mTLS é obrigatório.
  Template Nginx cobre bootstrap e rotas autenticadas v1/v2 e sobrescreve
  cabeçalhos externos. Segredo/configuração de produção não foram criados.
- Movimento conciliado fica somente leitura, conduz à evidência e conserva
  desfazimento autorizado. Rótulo de candidatos disponíveis corrigido.
  Runtime Linux recebe OCR português e fonte; teste usa fonte portátil.

Validação automatizada:

- **1.502 testes Python aprovados + 151 subtestes, um skip**, PostgreSQL 17.10
  local isolado, 509,55 s. O único skip é Python Playwright opcional; CUA/
  Playwright exercitou a interface. OCR antes ignorado agora foi executado.
- Inclui concorrência PostgreSQL entre conciliar e gerar/aprovar/exportar,
  revisão individual/lote, auditoria histórica sem escrita; páginas
  0/1/499/500/501, replay, mudança/inativação do recorte, isolamento de
  escritórios, protocolo antigo, código ausente/expirado/reutilizado,
  CA ausente/malformada/expirada/incorreta, CSR/chave inválida, certificado
  incorreto/expirado, renovação/revogação e cabeçalhos forjados.
- **38 testes .NET aprovados**, serviço/configurador compilados sem avisos ou
  erros. MSI 1.0.2 e **25 checks** de instalação/reparo/DPAPI/ACL/diagnóstico/
  reinício/remoção aprovados em runner Windows Server 2022 descartável.
  [Run 41845516300](https://github.com/Mewstacks/CicaContabil/actions/runs/41845516300),
  commit `fc7b378c101350f5bb4c1e6324eb01aebb834201`, hash MSI
  `e5bef0da853b740d3286087a863ad74922e2252ab6d969a2d8e2e333512158cc`.
- Django check e ausência de migrações não geradas aprovados; Ruff global e
  whitespace aprovados. MyPy dos sete módulos críticos aprovado. Format-check
  global detectou 153 arquivos divergentes; não foi usado para reformatar
  trabalho anterior nem é apresentado como aprovado. Não substitui o pass
  do lint. A checagem ampliada de cinco módulos repetiu os dez erros anteriores de views (linhas fora das alterações), sem erro nos demais módulos; `mypy-expanded.log` preserva a saída.

Ensaios operacionais sintéticos separados:

- HTTPS real Nginx/Django em contêineres descartáveis: oito cenários aprovados,
  incluindo CSR/pareamento, certificado + HMAC, falta de certificado com
  cabeçalhos forjados, replay idempotente, página fora do recorte, renovação,
  sobrescrita de cabeçalhos e interrupção/reinício sem duplicação. Recuperação
  local do backend: **5,86 s**. Cliente de teste foi Python; não Windows.
- Redis/Celery reais, eager desativado, rede de teste sem saída externa:
  200 movimentos bancários sintéticos, três entregas do mesmo run, uma decisão
  anterior preservada. Execução: **11,84 s**; reinício/retry: **7,02 s**.
  Não é queda no meio de tarefa nem amostra independente de aceite.
- Restauração de cópia SQLite + media: **0,02 s**, sete tabelas equivalentes,
  três arquivos/hashes íntegros e integrity_check aprovado. Não é restore
  Neon/objetos, RPO aprovado ou retorno de produção. Não substituir D-73.
- Docker runtime: OCR português extraiu data/valor/região de PDF digitalizado
  sintético. Imagem Linux `sha256:3ced2f077f34a45844d50bda6cc8e50f32cdbba04f1aa3d9bec4fe8ada9db288`
  construída; não publicada. O ensaio Nginx usou a imagem anterior indicada
  no seu JSON; os hashes/limites estão separados.
- CUA/Playwright: confirmar conciliação conduz à evidência, sem ação de gerar/
  aprovar/editar; auditor consulta sem botões de escrita. Seis combinações
  1440×900, 390×844, 844×390 nos temas claro/escuro sem overflow global no DOM;
  foco visível pelo teclado e zero avisos/erros de console na jornada. Captura
  do painel pode apresentar escala/margens; não equivale a homologação em
  dispositivos físicos. Viewport temporário restaurado e aba de teste fechada.

Pesquisa real e limites:

- O responsável autorizou buscar/escolher na Fedrizzi somente leitura.
  Uma página bancária existente permitiu escolher empresa/competência;
  metadados e dois cabeçalhos confirmaram códigos brutos de conta. O recorte
  escolhido de janeiro/2026 contém **115 itens** no extrato selecionado.
  Sem saldos/históricos coletados nessa consulta de cabeçalho e sem envio CICA.
  Identificadores só em `private-pilot-candidate.json`, fora do Git, modo 0600.
  Fechamento contábil e equivalência com a conta bancária/Razão não comprovados.
  **Zero itens reais independentes homologados**, sem precisão/cobertura
  D-73 inventadas. Não habilitado contrato SQL novo no agente.
- Windows/RDP: versão 1.0.1.0 e ausência de agent.config conferidas. Transferência
  temporária do MSI 1.0.2 por rede local não respondeu; nenhuma instalação foi
  executada, firewall/DSN/credenciais preservados. O configurador anterior
  continua disponível. Teclado Scancode restaurado e terminal criado fechado.
- Endpoint hospedado de cadastro continua **503 por CA ausente**. CLI Mac e
  Windows não acessam `cica-contabil`; responsável confirmou que ainda não tem
  esse acesso. Não houve login/alteração Fly, criação de CA ou deploy.
- ODBC sob LocalSystem, pareamento e mTLS Windows/hospedado, contratos reais de
  Razão/títulos/parcelas/baixas, Q-46/Q-47, DE-PARA/IA Q-08/Q-09, importação
  conferida Domínio, restauração/rollback publicados, 200 itens reais,
  treinamento e aceite CONTAD permanecem abertos. RPO/janela ainda a definir.

Evidências: `.tmp/contad-implementation-2026-11-04/` (JUnit, TRX, logs, JSONs
TLS/fila/OCR, seis medições DOM e capturas); pacote/CI preservados em
`agent-windows/artifacts/windows-1.0.2/`. Baseline de hashes e verificação de
preservação não identificaram arquivo anterior removido. Worktree isolada do
agente foi arquivada com confirmação após preservar fonte/pacote/CI. Main e
alterações financeiras não foram enviados a produção. Checklists 03/09/12,
Q-28, matriz CONTAD, pendências e execução atualizados sem concluir PC-19.

Complemento V-310: a revisão de entrada mTLS acrescentou recusa segura de
cabeçalho de gateway com caracteres não ASCII. A regressão final de cinco
módulos aprovou **80 testes PostgreSQL em 58,71 s**, sem skips, depois dessa
alteração; não se soma esse número aos testes únicos da suíte integral.
A persistência DPAPI recebeu arquivo temporário criptografado, flush e troca
atômica, mantendo o arquivo anterior em caso de falha; ciclos sem mudança de
recorte/destino não regravam configuração. Serviço/configurador compilaram com
zero avisos/erros. Mac: 37 testes .NET aprovados e um skip explicitamente Windows;
revalidação do pacote Windows preparada no commit `fc7b378`.

Fechamento do pacote V-310: run **41845516300** concluído com **38 testes .NET
sem skips e 25 checks MSI aprovados**; checksum final `e5bef0da853b740d3286087a863ad74922e2252ab6d969a2d8e2e333512158cc`
conferido contra o arquivo, manifesto e relatório CI. Artefato final em
`agent-windows/artifacts/windows-1.0.2/run-41845516300/`; candidato anterior
preservado por run. O CI registrou avisos não bloqueantes de runtime Node das
ações e ICE61 de atualização da mesma versão; os builds .NET tiveram zero
avisos/erros. Não houve execução do MSI no PC. Worktree arquivada, serviços de
QA próprios encerrados e alterações anteriores preservadas.

Conferência final V-310: 7.187 arquivos do baseline continuam presentes; as
40 alterações em arquivos anteriores pertencem ao escopo executado. Os 41
arquivos do agente foram comparados byte a byte ao commit CI final: somente a
documentação de instalação difere, com os resultados desta rodada. Código do
MSI confere com o workspace. `test-results.json` consolida testes e limites.

## V-311 — Pareamento HTTPS/HMAC sem CA privada (04/11/2026)

D-310 substitui a exigência mTLS do piloto em D-309 por decisão expressa do
responsável. Implementado localmente, sem deploy, instalação no PC ou envio.

- API v2 aceita modo `hmac` explícito por HTTPS, sem CSR, emissão de certificado
  ou consulta à CA. Código continua de uso único/expirável; segredo individual,
  HMAC/timestamp, revogação, isolamento e manifesto D-309 permanecem obrigatórios.
- HTTP, modo desconhecido, código inválido/reusado/expirado, assinatura inválida/
  não ASCII e identidade ausente/UUID inválido são recusados sem erro 500.
- Servidor com mTLS explicitamente obrigatório recusa HMAC sem consumir o código.
  Cliente antigo conserva fluxo certificado; CA inválida não causa fallback.
  Produção usa HMAC como padrão; `EDGE_AGENT_MTLS_REQUIRED=true` continua opcional.
- Configurador 1.0.3 não gera CSR/PFX, salva modo HMAC explícito com DPAPI/ACL e
  gravação atômica. Pasta é restringida antes de gravar. Serviço não carrega PFX
  nem renova certificado nesse modo. Configuração antiga continua `mtls`.
- HTTPS do servidor mantém validação normal do sistema; redirecionamentos não
  recebem corpo assinado/credenciais do agente. Nenhuma validação TLS desativada.

Resultados:

- PostgreSQL isolado: **1.522 testes + 151 subtestes aprovados**, um skip do
  Python Playwright opcional, **108,56 s**. Inclui 20 casos novos de pareamento
  HMAC e todos os casos anteriores. Antes deles, 71 regressões dos sete módulos
  de agente/backup/triagem/rentabilidade também passaram. Não somar repetições.
- .NET local Mac: 43 aprovados/um skip Windows; serviço/configurador compilados
  com zero avisos/erros após correção do contrato do configurador.
- Windows CI: **44 testes .NET sem skips e 26 verificações MSI aprovados**.
  O novo check executa serviço LocalSystem com configuração DPAPI HMAC sem PFX;
  chega ao transporte HTTPS de loopback inacessível e mantém retentativa, sem
  ler ERP ou chamar serviço externo. Não equivale a sincronização Windows real.
  [Run 41854423194](https://github.com/Mewstacks/CicaContabil/actions/runs/41854423194),
  commit `1bf854958cecae319abc050241f7b83753903265`, MSI **1.0.3**, SHA-256
  `5850a351f9ea54f4b72131c840af5a34534ce9bbe521c62ec605a32695fd8253`. Conferido contra arquivo,
  manifesto e relatório; assinatura de editor ainda ausente. Avisos não
  bloqueantes de runtime das Actions e ICE61 permanecem separados do build .NET.
- HTTPS real local com proxy de terminação: **dez cenários aprovados** sem
  certificado/CA de cliente ou gateway mTLS. Cadastro/uso único, heartbeat,
  assinatura/credenciais inválidas, certificado HTTPS de servidor não confiável
  recusado, recorte, replay, renovação dispensada e interrupção/reinício sem
  duplicação. Retomada sintética: **1,70 s**. Certificado HTTPS de servidor é
  exclusivamente fixture; não houve instalação de raiz no sistema do usuário.
- Django check, migrações sem alterações pendentes, Ruff, MyPy dos dois módulos
  Python alterados e whitespace aprovados. Sem migração nova nesta decisão.

Correções durante validação: contrato duplicado do configurador ajustado para
persistir o modo; CA fixtures antigas mantidas somente para testes legados;
proxy sintético passou a reproduzir o `SECURE_PROXY_SSL_HEADER` da produção;
UUID inválido/ausente passou a resultar em 401. CI inicial 41853259140 falhou
na compilação do configurador; run final acima aprovou o pacote corrigido.
Falha inicial do caso de assinatura vazia era do helper que assinava o vazio,
corrigida antes da regressão integral aprovada. Não apresentar essas tentativas
como validação do pacote final.

Evidências ignoradas: `.tmp/contad-auth-hmac-2026-11-04/` (`test-results.json`,
JUnit/TRX, logs, `https-hmac-results.json`); artefato preservado em
`agent-windows/artifacts/windows-1.0.3/run-41854423194/`. Versões anteriores intactas.
Worktree arquivada após preservar fonte/pacote; PostgreSQL e contêineres/rede de
QA próprios encerrados. Nenhum recurso de terceiros foi modificado.

Limites: PC conserva 1.0.1.0 sem configuração. Falta publicar o backend e
instalar o novo MSI para usar esse modo no ambiente real; o responsável ainda
não possui acesso Fly, e não foi solicitado novamente. Nenhuma nova coleta,
transmissão, escrita ERP, consumo de IA ou contratação. CA/mTLS deixam de ser
gate do piloto; acesso/publicação, recorte real conferido, Razão/títulos,
Q-46/Q-47, recuperação operacional, treinamento e aceite CONTAD continuam
abertos. RPO e métricas reais D-73 não foram inventados.

## V-312 — Snapshots contábeis, preparação de títulos/DE-PARA e release CONTAD (05/11/2026)

D-311 autoriza continuidade local de PC-19 nas etapas 03/09/12. Base main
`b499cd1`, alterações anteriores preservadas; nenhum commit/push/deploy nesta
rodada. Baseline privado de 7.199 arquivos preparado antes das alterações.

Implementado:

- Aprovar lançamento exportado é recusado antes de qualquer transição de estado.
  Histórico de exportação também impede nova aprovação/exportação se o estado
  do lançamento regredir. Concorrência aprovação/exportação exercitada em PostgreSQL.
- Reexportação exige original da empresa, mesmo destino/período, estado válido,
  motivo e integridade; copia bytes/hash/IDs/versão originais. Não renderiza
  registros atuais mutáveis. Arquivo ausente/corrompido ou escopo divergente
  recusa a operação sem novo registro. Gate contábil continua desligado.
- Aplicação/reaplicação de regras usa trava empresa→movimento, recarrega fatos
  e revalida revisão manual, conciliação e lançamentos antes de alterar a
  classificação. Testes determinísticos de duas transações preservaram decisão
  humana/rascunho surgidos após a seleção inicial de trabalho.
- Contrato offline `titles-normalized-v1`: títulos, parcelas e baixas imutáveis,
  conta/empresa, datas, componentes e centavos explícitos, saldo desconhecido,
  cobertura declarada, parcialidade e reversão integral vinculada. Hash canônico
  independente de ordem; inconsistência rejeita lote inteiro. Sem SQL, gravação,
  endpoint ou ligação ao agente; não homologa semântica do Domínio.
- DE-PARA determinístico cria somente rascunhos a partir de exemplos humanos,
  com contas ativas da empresa, autorização do revisor, conflito/insuficiência
  explícitos, trilha e retry que preserva correção/desativação humana. Não
  classifica movimentos na preparação nem chama IA. Não atende sozinho a IA
  contratual ou as regras reais ainda pendentes em Q-46/Q-08/Q-09.

Validação final da versão de domínio entregue:

- **1.578 testes Python aprovados + 151 subtestes, um skip opcional**, PostgreSQL
  local descartável, **430,32 s**. `final-full-pytest.xml`/log. O skip é Python
  Playwright opcional; não foi contabilizado como interface testada nesta rodada.
  Abrange parsers/arquivos/OCR, HMAC/recorte, banco e proteção das duas cadeias,
  além dos testes novos de snapshots, títulos, DE-PARA e corrida de regras.
- **43 testes .NET aprovados/um skip Windows no Mac**, TRX desta rodada. Fonte
  do agente comparada a `1bf854958cecae319abc050241f7b83753903265`: 43 arquivos,
  somente instalação/documentação difere. MSI 1.0.3 reconferido SHA-256
  `5850a351f9ea54f4b72131c840af5a34534ce9bbe521c62ec605a32695fd8253`.
  Não repetir como atuais os 44 testes/26 checks Windows históricos V-311.
- Ruff global, MyPy dos três módulos Python alterados, Django check,
  ausência de migrações pendentes e whitespace aprovados. Nenhuma nova migração
  criada. Sem alteração de templates/JS/CSS ou nova jornada visual; não houve
  validação nova desktop/mobile/temas/teclado via Playwright nesta rodada.
- Rodadas intermediárias focadas e suíte de 1.576 testes foram preservadas,
  mas não somadas aos testes únicos da regressão final. A suíte foi repetida
  após a guarda final de aplicação de regras e os dois testes adicionais.

Operação sintética separada: aplicação de migrações em PostgreSQL descartável,
seguida de dump/restore em outro banco e cópia de arquivos. **182 tabelas**
confrontadas por contagem/hash de todas as linhas, **15 sequências** com estado
igual e **dois arquivos** com SHA-256 igual. Preservados **200 movimentos,
200 registros independentes e dez alocações confirmadas**. Restore/conferência
**5,726 s**, geração da fixture **5,557 s**. Não é restore Neon/objetos/knowledge,
falha de worker no meio da tarefa, rollback da aplicação anterior, RPO definido
ou recuperação CONTAD. `postgres-restore-results.json` delimita a evidência.

Release local revisável: ZIP com **806 arquivos**, 2.014.294 bytes, SHA-256
`14b04f6d034fb9224494e81b05295a080932b4d6b6d6fcbc3a49edcdedb62429`.
Manifesto por arquivo reconferido contra ZIP e workspace. O empacotador recusa
sobrescrita, segredos/links inesperados e exclui dependências node_modules.
A primeira tentativa encontrou essa dependência e foi corrigida antes de
gerar o ZIP final. Não é imagem publicada. [Roteiro de configuração/retorno](docs/contad-release-2026-11-05.md)
mantém hub.0076/0077 e intelligence.0031 aditivas e os gates existentes.

Material real/autorização: Downloads continha plano de contas de 14 páginas;
754 linhas candidatas extraídas privadamente, sem importar cadastros ou inferir
situação ativa/código reduzido. Relatórios bancários/um balancete agregado e
arquivos demonstrativos não viraram Razão/títulos Domínio ou layout homologado.
O responsável confirmou que os relatórios solicitados ainda não existem;
não solicitar novamente seus caminhos. [Contrato e limites](docs/conciliacao-fontes-titulos.md).

RDP: primeira leitura transitória mostrou sessão desconectada; após cancelar
menu nativo/elevar janela, Windows logado ficou acessível. O responsável fez
login no Domínio Contabilidade e autorizou atualização oficial. O aplicativo
falhou por não localizar `atualiza.exe` no compartilhamento configurado; não
houve instalação/conversão de base, escrita contábil ou nova consulta SQL.
Isso é falha do caminho de atualização, não ausência de RDP ou defeito do DSN.
Processos de outros trabalhos foram preservados.

Evidências privadas ignoradas em `.tmp/contad-delivery-2026-11-05/`, diretório
0700 e arquivos reais restritos; fontes/pacote em `release/`, JUnit/TRX, logs,
inventários, backup sintético e hashes. Identificadores não foram adicionados
ao Git/CI. Nenhuma transmissão CICA, importação ERP, IA externa, custo ou
alteração hospedada. Publicação, fonte real/regras Q-46/Q-47, IA autorizada,
ODBC LocalSystem, D-73, recuperação operacional, treinamento e aceite CONTAD
permanecem abertos; PC-19 não está concluído/homologado/liberado.

Conferência operacional V-312: o contêiner efetivo usa **PostgreSQL 17.11**
(comando `postgres --version`), não o 17.10 histórico que o script de restore
inicialmente colocou como metadado fixo. JSON consolidado corrigido após a
verificação direta; contagens/hashes/tempos não mudaram. Backup/evidências
preservados e contêiner próprio encerrado/removido, sem tocar os demais serviços.
O compartilhamento de atualização Domínio responde e contém dois setups
C106A1001/C106A1002, mas não o `atualiza.exe` solicitado pelo lançamento
automático. Assinatura listada do fornecedor em inspeção, sem execução dos
setups ou conclusão de atualização nesta observação.

Continuidade operacional V-312: C106A1002 foi inspecionado e o Windows confirmou
assinatura digital válida Thomson Reuters Corporation. O assistente recusou a
aplicação na estação 10.6A-09 por exigir a versão completa 10.6A-10; não foi
forçado. O responsável confirmou backup atual concluído e recuperável. Baixado
`Atualiza.exe` do [repositório oficial 106a10](https://download.dominiosistemas.com.br/atualizacao/contabil/106a10/),
salvo como `Atualiza (1).exe`, 1.324.901.936 bytes. Propriedades confirmaram
assinatura digital válida do mesmo fornecedor, carimbo 21/10/2026 23:27:54.
O assistente completo confirmou **Atualização Terminada**, em `C:\Contabil`.
Apenas Domínio Contábil selecionado; extras de drivers/utilitários/Busca NF-e,
backup em nuvem e LogMeIn desmarcados. Não houve novo termo, fechamento forçado
ou componente adicional de acesso remoto. Isso comprova a instalação base,
não a abertura da aplicação, conversão de base ou obtenção dos relatórios.
MD5 público do fornecedor preservado como referência; não houve comparação
MD5 do executável Windows, e não se alega essa verificação.

O ajuste **C106A1002 — Atualização 2 de 05/11/2026** aceitou o pré-requisito
após a instalação completa, manteve `C:\Contabil` e também confirmou
**Atualização Terminada**. Nenhum novo termo ou encerramento forçado exigido.
Aplicação reaberta para conferir acesso e relatórios; essa instalação não
atualiza o agente CICA nem comprova ODBC sob LocalSystem.

Reabertura observada: tela de autenticação Domínio, senha vazia. Login direto
solicitado ao responsável, sem credenciais no chat; janela mantida pronta.
Teclado RDP restaurado de Unicode para Scancode. Nenhuma consulta nova, relatório
obtido, importação contábil ou conversão de base observada nesta continuação.

## V-313 — Prévia offline de alocações e consulta ERP (05/11/2026)

D-312, PC-19/03/09/12. Implementados núcleo sem ORM/rede e CLI sobre contratos
normalizados, com seleção explícita, escopo, chaves compostas, capacidade de
caixa dos dois lados, parciais/agrupamentos, componentes e estornos brutos.
Diferenças de data sinalizadas; toda saída exige revisão. Não escolhe vínculos,
aplica tolerância, persiste decisão ou conecta títulos ao agente/UI.

Validação desta versão: **85 testes focados aprovados** (56 de alocação/CLI e
29 do contrato de títulos), Python 3.12.13/Django 6.0.8 no Mac, sem banco de dados.
Cobertura do módulo de alocação 100%; combinada com CLI **97,44%**. Casos incluem
escopo errado nas duas fontes, duplicação/limites, excesso acumulado dos dois
lados, pagar/receber, parciais, agrupamento, estorno, JSON repetido/corrompido,
destino existente/symlink e falha de escrita antes da publicação atômica.
Ruff global, MyPy dos dois módulos e `git diff --check` passaram. MyPy inicial
sem PYTHONPATH não encontrou config; reexecutado corretamente com PYTHONPATH=src.
CLI executada também fora do pytest com fontes sintéticas, relatório 0600 e
hashes conferidos. Nenhuma migração/alteração de UI/novo teste Windows necessário
para esses módulos offline. Não reapresentar 1.578 testes/151 subtestes V-312
como regressão completa desta alteração; nem somar rodadas repetidas.

Nova candidata local em `.tmp/contad-delivery-2026-11-05/release-title-preview/`:
**809 arquivos**, 2.022.148 bytes, SHA-256
`db4085a89ff9215893478c51cae78c556284a303a2a013ed0b5e30040991b2e8`.
809 hashes conferidos contra ZIP e workspace; inclui núcleo, testes e CLI.
Base `b499cd12d158fc33f68b39a365f70044aa31d7e5`, alterações locais preservadas,
sem commit/push/deploy. Pacote anterior de V-312 preservado. MSI/agente não mudaram.

Consulta somente leitura no Windows: login concluído pelo responsável e versão
10.6A-10 -02 confirmada. Movimentos → Lançamentos de Extrato Bancário identifica
a conta do candidato no campo “Conta contábil do banco” e carrega janeiro/2026.
Razão emitido para essa conta/mês, com Data/Número/Histórico/Cta.C.Part./Débito/
Crédito/Saldo/Saldo-Exercício; PDF observado em Downloads do Windows, 141 KB.
A transferência para Mac não foi confirmada; zero linhas extraídas/normalizadas
ou exemplos aprovados. Relatório de uma conta não prova partidas compostas completas.

“Fechamento atual” contábil original exibe 11/2023; Escrita Fiscal da mesma empresa
mostra controle de títulos desmarcado, vigência exibida 09/2021 e período inicial/
atual 10/2026. Parâmetros fechados sem gravar. Não se conclui ausência histórica
absoluta de títulos. Responsável autorizou pesquisa alternativa somente leitura.
Alternativa consultada possui menu de títulos e fechamento fiscal 09/2026,
mas fechamento contábil 11/2014. Nenhum desses fatos homologa período contábil.
Identificadores e observações em JSONs privados 0600; nenhuma alteração de
parâmetros, baixa, fechamento, consulta SQL nova, importação ou transmissão CICA.

Na alternativa, A Pagar por emissão 01–30/09/2026 e posição 30/09, situação
Todas/tipo Todos, gerou relatório. PDF conferido no Explorer (116 KB exibidos)
e aberto para verificar o cabeçalho; sem cópia Mac, hash, extração ou contagem
de páginas verificados. Colunas observadas: Documento, Emissão, Entrada,
Vencimento, V. Parcela, Valor Pago, Juros, Multa, Outras, Desconto, Devolução,
Saldo e Situação. Sem conta bancária, chave de baixa ou data de pagamento nessa
visão; repetição do documento não identifica parcela/baixa. Não houve mapeamento
semântico desses componentes ao contrato nem aprovação contábil.

Cinco consultas delimitadas retornaram “Sem dados para emitir”: A Receber por
emissão/posição de setembro; A Receber por recebimento em setembro com posição
30/09; A Pagar por pagamento em setembro com posição 30/09; o mesmo filtro de
pagamento sem posição; e A Pagar em situação Pagamento parcial por emissão
em setembro, sem posição. Tipo Todos nas cinco. A última consulta não filtra
data de pagamento. Ausência restrita a esses filtros, sem inferir inexistência
geral de títulos/baixas. Janelas próprias de consulta fechadas, Domínio mantido
logado e teclado RDP restaurado para Scancode. Nenhuma mudança de parâmetros
ou lançamentos, nova seleção homologada ou ampliação de transmissão.

Evidências: `title-allocation-pytest.xml`, `title-allocation-coverage.json`,
`title-allocation-example/`, `title-preview-release-verification.json`,
`private-erp-observation.json` e `private-alternative-candidate.json` no diretório
ignorado de 05/11. Q-28/Q-46 ainda exigem fonte real revisada, adaptação e fluxo
persistido; Q-47 layout/importação; Q-08/Q-09 IA; publicação/serviço real/D-73,
recuperação operacional, treinamento e aceite continuam abertos.

Conferência final V-313: os 809 hashes do ZIP e workspace continuam iguais
após os registros documentais. Os 7.199 arquivos do inventário inicial continuam
presentes, base Git inalterada; evidências reais e prévia sintética em 0600.
`git diff --check` aprovado. Nenhuma publicação, commit ou push realizado.

## V-314 — Publicação autorizada do código na main (05/11/2026)

D-313 registra a autorização expressa do responsável. Preflight: `origin`
aponta para `Mewstacks/CicaContabil` público, branch padrão main; `ls-remote`
confirmou a mesma base local b499cd1. Inventário explícito de 84 arquivos de
fonte/testes/configuração de exemplo/documentação, sem dados, relatórios,
artefatos binários ou arquivos privados. Busca de padrões de chaves privadas,
tokens e URLs com credenciais não encontrou ocorrência nesse inventário;
isso não é uma garantia universal de detecção de segredos.

Ruff global e `git diff --check` aprovados nesta rodada. Os 809 hashes de fonte
da candidata V-313 continuam iguais ao workspace; 40 arquivos não Markdown do
agente comparados ao commit Windows 1bf8549 têm bytes idênticos. Resultados de
testes V-312/V-313 e Windows V-311 conservam datas/ambientes próprios; não houve
nova regressão completa local. O push main aciona CI, sem workflow de deploy
automático nesse evento. Resultado remoto será registrado após envio/verificação.

Evidências de preflight em `.tmp/contad-main-publication-2026-11-05/`, ignoradas.
Aplicação hospedada, PC real, transmissão, importação e homologação permanecem
fora desta autorização de publicação do código; gates PC-19 não encerrados.

Publicação executada: commit `4fede1e7f5b1bcfaec8b430a3b0f0d8c4d579b1d`, 84
arquivos, push normal b499cd1→4fede1e. `ls-remote origin refs/heads/main`
confirmou o mesmo SHA; árvore de trabalho limpa imediatamente após o envio.
[CI 42067809017](https://github.com/Mewstacks/CicaContabil/actions/runs/42067809017)
iniciado para esse SHA. Nada de `.tmp`, PDFs, MSI, dados ou configuração real
foi incluído. Sem deploy, migração hospedada, transmissão ou escrita ERP.

CI remoto **42067809017 concluído com sucesso** para o commit 4fede1e:

- Python 3.12/Ubuntu 24.04, SQLite: **1.617 testes e 151 subtestes aprovados**,
  18 skips, 175,94 s. Dezesseis skips exigem PostgreSQL; os outros dois são
  Playwright Python opcional e OCR local português indisponível no runner.
- PostgreSQL 17 do serviço isolado CI: **1.633 testes e 151 subtestes aprovados**,
  dois skips (os mesmos Playwright/OCR), 225,01 s. Concorrência não foi omitida.
  Não somar as duas baterias como testes únicos ou extrapolar os tempos a D-73.
- .NET/Linux: serviço, configurador e ponte ODBC compilados; **43 testes
  aprovados e um skip Windows**, zero falhas. Job Windows construiu MSI e
  conferiu manifesto pelo workflow existente (versão de build CI 1.0.0).
  Não executa instalação real nem substitui o MSI 1.0.3/CI Windows V-311.
- Ruff, Django check, ausência de migrações pendentes e builds Docker do
  backend, multimodal e trainer aprovados. Imagens construídas no runner,
  sem publicação em registry, deploy ou execução de treinamento.

Conferência adicional por `git archive` do commit publicado: os mesmos **809
arquivos de fonte** têm hashes idênticos à candidata V-313. Logs e JSON de jobs
preservados no diretório privado de publicação. Registros Markdown do resultado
seguem em commit separado; o CI acima identifica o commit de implementação.
Sem Playwright novo ou OCR português executado no runner; evidências anteriores
conservam seus limites. Aplicação/ERP/PC/CONTAD continuam sem nova homologação.

## V-315 — Reconferência dos anexos bancários CONTAD (05/11/2026)

Pergunta do responsável sobre testar com o PDF/OFX Sicredi e a imagem fornecidos.
Escopo de leitura local já previsto em D-305/D-311, base 8aeeff5, sem mudança de
implementação ou regra contábil. Executados `parse_ofx` e `compare_bank_files`
da versão publicada sobre os dois originais indicados em Downloads, com settings
de teste sem serviços externos e guarda para recusar SQL. Nenhuma escrita em
banco, importação ERP, IA, transmissão ou homologação.

- Período 01–30/09/2026, **163 movimentos no PDF e 163 no OFX**.
- Mesma multiplicidade de data/valor; zero movimentos exclusivos em cada lado.
- Sequência de saldos válida; saldo inicial mais movimentos igual ao final;
  saldo final informado no OFX igual ao PDF.
- FITIDs presentes e únicos nas 163 transações do OFX.
- PDF textual de seis páginas renderizado com Poppler e composição integral
  inspecionada; imagem anexa é assinatura de e-mail, sem fonte contábil adicional.

Isso permite iniciar testes reais da entrada bancária e preparar cenários de
reenvio/revisão/relatório; esta reconferência executou leitura/comparação, não
novo percurso persistido ou de interface. Corrobora V-304/V-308, sem somar uma
repetição ao número de testes ou contar PDF e OFX como 326 itens independentes.
São 163 eventos bancários representados em dois formatos, abaixo da amostra
de 200 itens por fluxo de D-73; isso não impede os testes iniciais.

Razão independente, títulos/parcelas/baixas, equivalência da conta e exemplos
revisados continuam necessários para validar conciliação contábil, DE-PARA e
retorno ao Domínio. Não se conclui que a leitura bancária está impedida por
essas dependências. Q-28/Q-46/Q-47 e homologação permanecem abertos.

Evidência privada ignorada: `.tmp/contad-files-review-2026-11-05/`, diretório
0700, `bank-comparison.json` e PNGs 0600. Hashes dos originais preservados no
JSON, conteúdo/identificadores fora do Git. Sem alteração de código ou novo CI.

## V-316 — Percurso bancário persistido com anexos CONTAD (05/11/2026)

D-314, base 8aeeff5 com registros V-315 preservados. Executado em SQLite novo
e mídia privados, settings de teste, saída de rede externa bloqueada, Celery
eager/memory. Escritório, usuários e duas empresas de cenário são artificiais;
os 163 eventos bancários vêm dos originais autorizados. OFX e PDF em cenários
separados, sem somá-los como 326 eventos independentes. Nenhuma escrita no ERP,
banco de desenvolvimento/produção, chamada de IA ou transmissão financeira.

Percurso final run-03: **42 verificações aprovadas**, 22,086 s incluindo setup
e migrações; não é medição de processamento por empresa D-73. Cobriu:

- Upload HTTP autenticado e persistência de 163 movimentos exatos por formato;
  OFX também alimenta 163 transações da outra fila e suas identidades compartilhadas.
- Despacho OFX suspenso pelo harness após persistir e recuperado pelo dispatcher;
  fila em modo eager, sem alegar novo ensaio de broker/worker real.
- Reenvio idêntico e renomeado mantém arquivo, IDs e contagens; OFX com hash
  diferente e FITIDs sobrepostos é recusado integralmente. Conta errada e
  conta de outra empresa recusadas antes de nova normalização.
- Salvar fatos originais sem contas inventadas, recusar revisão obsoleta,
  ignorar/restaurar com trilha, reaplicar regras e retomar sem perder a decisão.
- Relatórios HTTP privados: 163 pendências bancárias, zero Razão independente,
  cobertura/aceite falsos e saldo inicial contábil desconhecido; nenhuma partida,
  alocação ou exportação contábil criada. Originais inalterados.
- Auditor autorizado consulta/download, mas não altera; outro escritório não
  acessa o relatório. Grants sintéticos incluem explicitamente o módulo.

Falhas reais encontradas e corrigidas: `edited_by` humano agora protege
aplicação/reaplicação mesmo sem marcador de classificação manual, inclusive
após espera da trava. Aviso único e consistente `protected_movements` em
`rules_reapplied` permite relatório com aviso; erros reais, mistura, formato ou
contagem inválidos e estado falho continuam bloqueados. Sem migração ou mudança
de template/CSS/JS. Não reescreve histórico nem aprova classificação contábil.

Regressão sintética **PostgreSQL 17.11/Python 3.12.13/Django 6.0.8 no Mac**:
**134 testes e 24 subtestes aprovados, zero skips, 46,71 s**, nos cinco módulos
focados de conciliação/fontes/integridade. Inclui 19 casos novos: oito de decisão
humana sem marcador manual, nove de limites do aviso no relatório e duas novas
corridas PostgreSQL. Ruff global, MyPy dos dois módulos e whitespace aprovados.
Não é regressão completa nova, teste Windows ou repetição dos CIs V-314.

Tentativas anteriores preservadas: setup inicial recusado pela guarda de
SECRET_KEY do módulo privado, corrigido antes de executar o cenário; run-01
reproduziu duas perdas do ignorar e parou por grant sintético sem organização.
Run-02 passou 39/42: dois bloqueios indevidos do relatório e grant do auditor
sem módulo. Corrigidas as duas falhas de produto e os fixtures. Não apresentar
tentativas intermediárias como aprovação nem somar suas repetições ao total.

Navegador CUA/Playwright, viewport padrão 727×982, tema escuro: login técnico,
filtro por empresa/arquivo, página 1→2 de quatro, salvar revisão com fatos
originais, download real de CSV com 163 linhas bancárias/zero contábeis e zero
erros de console. Não houve varredura responsiva completa ou novo design.
Limite observado de navegação: após salvar, o link de retorno perde o filtro
de arquivo/busca; comportamento existente não alterado nem declarado validado.
Captura de confirmação preservada. Aba e servidor loopback próprios encerrados.
Contêiner PostgreSQL exclusivamente sintético encerrado/removido; demais serviços
preservados. Banco/mídia reais do piloto local conservados em pasta privada.

Nova candidata de fonte: **809 arquivos**, 2.023.175 bytes, SHA-256
`a3cd63af4679d0e3067657ffaa6a1f6361a57e4dedea2e50b2a0ce5d2ec6e88c`;
ZIP e workspace confrontados. Evidências ignoradas/restritas em
`.tmp/contad-bank-pilot-2026-11-05/`: `run-03/results.json`, checks, relatórios,
banco/mídia, captura/browser-results, JUnit/log PostgreSQL e `release-candidate/`.
Gate contábil desligado. Q-28/Q-46/Q-47, D-73, deploy, PC/serviço e aceite abertos.

Publicação corretiva executada sob D-313/D-314: commit
`700b496fc6b3ae0e521a11ca21ed6b65efbe7246`, 15 arquivos revisados, push normal
8aeeff5→700b496 e SHA remoto idêntico. [CI 42079806454](https://github.com/Mewstacks/CicaContabil/actions/runs/42079806454)
iniciado para essa implementação; não é declarado aprovado por sucesso do push.
Registro documental do envio segue separado, com as mesmas fontes executáveis.
Dados, banco/mídia, scripts privados, sessões, relatórios e captura fora do Git.


## V-317 — Retorno à fila e CI da correção anterior (05/11/2026)

D-315, PC-19/03/09/12; base 162d73c. Corrigidos os dez redirecionamentos de
ação do detalhe do movimento para usar `detail_redirect`, preservando origem
após sucesso ou recusa. `back_url` mantém a validação existente de host/caminho.
Empresa, arquivo, busca com acentos/ampersand/percentual, revisão, classificação
e página permanecem codificados na URL. Sem origem, comportamento padrão igual.
Sem mudança de template/CSS/JS, regra contábil, permissão, migração ou agente.

Regressão focada desta versão: **93 testes e 24 subtestes aprovados**, zero
skips, **31,80 s**, Python 3.12.13/Django 6.0.8/SQLite em bancos temporários de
pytest no Mac. Três módulos: conciliação, revisão UI e navegação. Inclui oito
novos casos de sucesso/recusa preservando fila e os testes existentes de
retorno externo/caminho arbitrário recusados. Não somar a execução inicial
isolada dos mesmos oito casos. Ruff global, Django check, ausência de migrações
e `git diff --check` aprovados. Não é nova regressão integral/PostgreSQL/Windows.

CUA/Playwright em banco e mídia novos privados, somente **61 movimentos
sintéticos**: salvar revisão e voltar conserva empresa/arquivo/busca/página
2 de 2, com 11 itens visíveis; contas contábeis vazias, sem partidas inventadas.
Desktop 1440×900 e celular 390×844; temas claro/escuro; salvar, ignorar/restaurar
e retorno por teclado/Enter com foco de 3 px conferidos. Sem overflow horizontal
ou erros de console observados. Capturas desktop escuro e detalhe mobile claro
inspecionadas; a captura full-page do desktop mantém o cabeçalho sticky na
posição da rolagem. Não é evidência de layout novo ou auditoria integral de UI.
Aba/servidor próprios encerrados e override de viewport restaurado.

UI/UX Pro Max local orientou navegação previsível/deep link. Watermelon não
exposto no inventário de ferramentas. Aplicadas as [Web Design Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
e referência primária de [filtros/vistas Asana](https://help.asana.com/s/article/project-customization-and-views),
sem copiar interface. O limite V-316 de perda do filtro após salvar foi corrigido.
Limite adicional observado: trocar o tema na fila conserva a query, mas perde
o painel definido no hash; foi necessário abrir “3. Revisar”. Não alterado nesta
rodada. Paisagem/tablet e emulação de movimento reduzido não repetidos.

CI **42079806454 aprovado para 700b496**, a implementação anterior D-314:
SQLite **1.634 testes/151 subtestes aprovados, 20 skips**, 205,82 s; PostgreSQL
17.11 **1.652 testes/151 subtestes aprovados, dois skips**, 249,14 s. Os dois
skips são Playwright Python opcional/OCR português indisponível no runner;
os outros 18 em SQLite exigem PostgreSQL. Agente Linux 43 aprovados/um skip
Windows, build/manifesto MSI e três builds Docker aprovados, sem implantação.
Esse CI não contém a alteração de retorno D-315 e não é sua regressão remota.
O CI 42080045517 do commit documental 162d73c também terminou aprovado.

Nova candidata de **809 arquivos**, **2.023.623 bytes**, SHA-256
`bc293cc85bbf3191d6f0d5e0c8f27171c72508c4b47d76ab2572c34b9f8d4542`;
ZIP reaberto e 809 hashes confrontados com o workspace. Evidências ignoradas
em `.tmp/contad-navigation-2026-11-05/`: JUnit, browser-checks/results, capturas,
banco/mídia sintéticos, log CI 700b496 e release-candidate. Pastas/arquivos
privados; a cópia real V-316 não foi alterada. Q-28/Q-46/Q-47, IA Q-08/Q-09,
implantação, serviço real, D-73, treinamento e aceite permanecem abertos.

Publicação D-315 concluída: `ed01dd51293be441ef7011763799ae557608cd5f` na main, push normal
162d73c→ed01dd5 e SHA remoto conferido. Confronto por `git archive`: 809 hashes
de fonte do commit iguais à candidata acima. [CI 42082634894](https://github.com/Mewstacks/CicaContabil/actions/runs/42082634894)
em execução na última consulta: agente Linux aprovado, pytest/build Windows
ainda em andamento; sem atribuir aprovação remota a esta correção. Confirmação
documental em commit separado; fontes executáveis preservadas.

Observação de disponibilidade do RDP existente: alerta 0x5 informa desconexão
porque outra conexão assumiu o computador. Nenhuma reconexão, encerramento de
terceiro ou consulta ERP realizada; a sessão AnyDesk CONTAD ainda não está aberta.
Captura adicional normal de viewport do QA sintético em
`retorno-fila-confirmado.png` evita o artefato de cabeçalho sticky da full-page.
Servidor/aba exclusivos dessa captura também encerrados.

## V-320 — Inspeção de leitura dos conjuntos do importador Domínio (15/10/2026)

Foram lidos, sem alteração, três conjuntos de dados fornecidos pelo cliente e mantidos **fora do
repositório** (`conjuntos Krek/conjunto de dados`): `NFSE sem itens no estoque e tag acumulador -
SEM ARGUMENTOS V4`, `NFSE com itens no estoque e tag acumulador - SEM ARGUMENTOS V4` e
`NFSE PRESTADOS - SEM ARGUMENTOS V2`. Nessa primeira leitura nada foi editado.

Verificado nos três: a coluna `codi_esp` está com `origem_coluna = F` e `valor_fixo = 1`. No conjunto
de tomados, a coluna pertence à tabela `efentradas`, identificação "Grava Nota". A busca por
"espécie" não retorna ocorrência: o campo existe apenas sob o nome de coluna do banco. Os conjuntos
são despejos das tabelas `dw_importador_importa_*` do próprio Domínio.

Verificado também que os arquivos declaram `encoding="UTF-16LE"` mas contêm bytes de byte único, e
que o marcador de 19 bytes logo após `<dados>` é idêntico nos três arquivos — ou seja, é constante do
formato e não resumo do conteúdo. Isso descreve o formato observado; não autoriza editar o arquivo.

Correspondência de pasta: o caminho observado na tela do cliente (`...\XML\NFS-e\Tomadas\29-\202609`)
corresponde à estrutura gerada por `create_nfse_export` em `src/apps/hub/services.py`
(`NFS-e/{Emitidas|Tomadas}/{código Domínio}-/{AAAAMM}/NFS-e-*.xml`). Isso indica que o pacote da CICA
é a fonte dos arquivos importados por essa rota.

Limites desta validação:

- Não foi aberta nenhuma nota **efetivamente importada** para confirmar a espécie resultante. A nota
  inspecionada nas capturas anteriores tinha `Origem: Lançamento Manual` e não comprova o importador.
- Não foi verificado a que descrição ou modelo corresponde a espécie 1 na base do cliente, nem
  confirmado que 39 é aceito por aquele conjunto.
- Nada foi alterado no Domínio, nenhum conjunto foi gerado ou reimportado, nenhuma nota foi
  reimportada e nenhuma importação foi homologada. Q-39 não é encerrada por esta leitura.
- O código da CICA não foi alterado; o contrato de exportação permanece o de D-274.

Em 15/10/2026, com a espécie 39 informada pelo responsável, foram geradas versões novas a partir dos
conjuntos então vigentes (`TOMADOS SEM ITENS V5`, `TOMADOS COM ITENS V5`, `PRESTADOS V3`), sem tocar
nos originais: `...V6` e `...V4`, com `nome_conjunto` sufixado `ESP39`. Em cada arquivo foram
alterados exatamente dois pontos: o `valor_fixo` da coluna `codi_esp` (1 para 39) e o nome exibido.

A conferência reverteu as duas edições e comparou byte a byte com o original: idêntico nos três. A
declaração XML, o marcador de 19 bytes, a contagem de CRLF e as ocorrências de `acum` ficaram
inalteradas; nenhum outro `valor_fixo>1<` foi tocado.

Observação não resolvida: `PRESTADOS` e `TOMADOS SEM ITENS` compartilham `codi_conjunto = 65` nos
arquivos do cliente. Isso é anterior a esta geração. Não foi verificado se a importação de um
substitui o outro.

Limite desta geração: os arquivos foram apenas escritos em disco. Não foram importados no Domínio,
nenhuma nota foi reimportada, a espécie 39 não foi observada em nota alguma e nada foi homologado.

## V-321 — Carteira de origem backup com ativação manual e corte por fotografia (05/11/2026)

Escopo de D-319. Mudança local, sem migração, sem deploy e sem tocar em produção.

- **Testes:** `tests/test_backup_portfolio.py`, 14 aprovados. Cobrem listagem com código do
  Domínio, filtro de situação, desativar e reativar com evento de auditoria, filtros preservados no
  redirecionamento, recusa de membro (403) e de ação inválida (400), 404 quando um conector Domínio
  passa a mandar no cadastro, e o vínculo na tela de Configurações só no escritório de backup. Do
  lado do corte: backup limpo desativa o ausente, o ausente continua existindo, lote com erro de
  linha não corta e lote sem a capacidade `companies` não corta.
- **Regressão dirigida:** `test_self_service_backup.py`, `test_company_registry_django.py` e
  `test_company_profile.py` — 35 aprovados e 2 subtestes. `manage.py check`, `makemigrations
  --check` e `git diff --check` limpos; Ruff limpo nos arquivos alterados.
- **Verificação real no navegador** (servidor QA isolado na porta 8011, banco descartável em
  `.tmp/ui-review`, escritório sintético `qa-backup` com seis empresas): a página listou as seis,
  o filtro `situacao=inativa` devolveu só as duas inativas e o clique real em Desativar gravou,
  avisou "saiu da carteira" e moveu o contador de 5 para 4 de 6 ativas. Desktop 1440 e celular 375:
  sem rolagem lateral, botão de 44 px e nenhum erro novo de console.
- **Dois defeitos encontrados e corrigidos nessa verificação, não pelos testes:** o rótulo do botão
  quebrava letra a letra, porque a célula de ação herda `overflow-wrap:anywhere` da tabela — foi
  preciso um recorte de CSS próprio (`backup-portfolio-table`) e o `?v=` de `operations.css` subiu
  para `cica-62`. E o `action` viajava no próprio botão de envio: `hub.js` desabilita esse botão ao
  submeter, e botão desabilitado não envia valor, então com JavaScript ligado a ação chegava vazia
  e a resposta era 400. Passou para campo oculto, como já fazem os modelos de atividade, com teste
  de regressão que impede a volta.

Limites: a verificação usou dados sintéticos em banco descartável. O corte por ausência não foi
exercitado contra um `.dom` real nem contra a carteira da Bianchi; o que existe é o teste do
`complete_backup` e o caminho do agente Windows lido no código (`BackupProcessor` já traz
`stat_emp` como coluna). Nada foi publicado e nenhuma empresa real foi alterada.

Complemento (10/11/2026): com a entrada movida para o menu Configurações, 16 testes do módulo
passaram, incluindo três novos que conferem o menu renderizado — presente no escritório de backup,
ausente sem fonte de backup e ausente quando existe conector Domínio. Conferência real no servidor
QA isolado: no escritório sintético de backup o menu Configurações mostra "Empresas atendidas"
logo abaixo de "Integrações", apontando para `/app/configuracoes/carteira/`. O rodapé interno da
página de Integrações deixou de exibir o link, que agora vive em um lugar só.

Complemento (10/11/2026, parte 2): 18 testes do módulo e 3 do fluxo ADN aprovados. O teste novo da
varredura confirma que a empresa inativa conserva `running` sem mensagem de erro e que, ao voltar
a ativa, a varredura seguinte a recupera com `stale_lease`.

Correção do que eu havia afirmado antes: eu disse ao proprietário que a tela de coleta poderia
mostrar um estado enganoso para a empresa desativada. Não mostra. A verificação pelo teste revelou
que o escopo operacional dessa tela já é somente de empresas ativas
(`company_queryset_for_membership` filtra `active=True`), então a empresa simplesmente sai da
lista. A mudança na varredura continua valendo, porque o estado falso era gravado no registro e
reapareceria se a empresa fosse reativada; mas o alcance é menor do que o descrito.

## V-322 — Prévia privada CONTAD e instalação guiada no PC (06/11/2026)

Escopo D-320, PC-19/etapas 03/09/12. Não conclui o conciliador contratado.

**Implementação local:** `AccountingExportPreview` imutável separado de
`AccountingExport`, migração aditiva hub.0078, fotografia das partidas/fatos,
versão do adaptador, autor, arquivo privado e SHA-256. Geração protegida por
POST/CSRF, papel e carteira; somente lançamentos novos aprovados da conta/período,
com validação contábil e revalidação após trava da empresa. Repetição conserva
os bytes; mudança de fatos/aprovações torna a fotografia obsoleta e exige outra.
Download confere integridade e atualidade, limita carteira/escritório e usa
private/no-store. Gerar prévia não registra exportação, altera lançamento,
importa no ERP ou habilita o gate contábil. Lista explícita de UUIDs vazia por
padrão; demo excluída. Arquivo continua **não homologado**.

**Verificações:** 40 testes da prévia mais dois da regra de texto aprovados em
PostgreSQL 17 descartável, sem skips. Cobrem isolamento, papéis, CSRF, arquivo
corrompido/ausente, fotografia obsoleta, persistência/limpeza, capacidade e
concorrência de geração/decisão após trava. A regressão completa anterior à
última correção de auditoria aprovou **1.715 testes e 163 subtestes**, um skip
opcional Python Playwright, em 252,32 s. A primeira execução revelou um texto
explicativo contrário a D-277: removido, sem afrouxar baseline. Revisão adicional
encontrou auditoria de integridade revertida pelo 404 dentro de transação:
registro movido para depois da transação, teste passou a exigir sua persistência;
42 testes focados aprovados novamente, 21,93 s. **Regressão final após a
correção: 1.715 testes e 163 subtestes aprovados**, um skip opcional, em
291,22 s. Percurso de entrada Conciliação → Prévia e reenvio conferidos também
no navegador após retirar o texto explicativo do atalho. Ruff global, Django check, makemigrations --check e MyPy do
módulo novo aprovados. MyPy do forms completo encontrou erro anterior em
forms.py:523, fora da mudança; não declarar tipagem global aprovada.

Conferência adicional na mesma versão principal/minor de produção: migrações
e os **42 testes focados passaram em PostgreSQL 18.6**, 21,62 s, contêiner
descartável sem dados reais. Imagem oficial fixada em
`sha256:f1ea2a1a4fb7b68d4836be1fdcb8a6466a89b072158bf9d97663600538c294c5`.
Não é restauração Neon/Tigris nem substitui o gate operacional de backup.

**Navegador sintético:** CUA/Playwright em 1440×900 e 390×844, temas claro e
escuro, envio válido/repetido, período inválido com campos preservados, foco
no erro e Tab/Enter até a data, download real e console sem erros. Ajustado o
histórico no celular para exibir cada período/situação/ação sem rolagem lateral.
Download sintético SHA-256 preservado; não é arquivo financeiro da cliente.
Capturas e logs em `.tmp/contad-development-2026-11-06/`. Frontend Design aplicado;
UI/UX Pro Max não encontrado e Watermelon não exposto, portanto não alegar seu
uso. [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
orientaram rótulos nativos, foco, alvos, erros e responsividade. Pesquisa primária
[Xero](https://central.xero.com/0/article/Reconcile-your-bank-account) e
[QuickBooks](https://quickbooks.intuit.com/learn-support/en-us/help-article/bank-transactions/match-transactions-quickbooks-online/L0MF3Fn6y_US_en_US)
conferiu o padrão de revisão humana antes da conclusão, sem copiar interface
ou presumir que sugestão vira escrituração.

**PC CONTAD — resultados informados pelo operador:** Windows/PowerShell x64,
SQL Anywhere 16/17 x64, três DSNs de usuário x64, um de sistema x86 usando
SQL Anywhere 17, zero DSNs de sistema x64 e agente inicialmente ausente.
AnyDesk não pôde ser lido pela ferramenta nativa, apesar de nova janela/instância;
responsável escolheu execução guiada, sem AppleScript/System Events. Não houve
controle remoto automatizado bem-sucedido. Pasta MSI transferida pelo operador;
Get-FileHash no Windows igual a
`5850a351f9ea54f4b72131c840af5a34534ce9bbe521c62ec605a32695fd8253`.
Depois da instalação, Get-Service informou **Running / Automatic**, ProductVersion
`1.0.3+1bf854958cecae319abc050241f7b83753903265` e estado
`awaiting_configuration` no PowerShell administrativo. Leitura sem elevação
negada pela pasta protegida; permissões preservadas. Os 44 testes .NET/26 checks
Windows são a evidência histórica do pacote V-311, não reexecutados no PC.
Pacote sem assinatura Authenticode. Responsável informou que não possui a
credencial de integração somente leitura: nenhum DSN recriado, senha extraída,
pareamento, ODBC LocalSystem, leitura ou envio ERP comprovados.

**Hospedado:** acesso Fly confirmado para pedro@mewstack.com.br, app
cica-contabil/mewstack-629, release 71/imagem e configuração preservadas em
metadados privados. Ambos os aliases respondem no Neon; hub.0075 e
intelligence.0030 ainda aplicadas, exportação Domínio false e mTLS false.
Produção usa PostgreSQL **18.6**, enquanto regressão local usa 17. Bancos medidos
em 589.570.048/8.175.616 bytes. Storage Tigris não informou versionamento
habilitado; nenhuma credencial API Neon no ambiente remoto ou .env local.
Isso não comprova ausência geral de backups, mas não confirma recuperação.
Nenhum dump de produção baixado para o Mac ou backup/restauração executados.

Cadastro próprio **CONTAD** criado após confirmação do responsável:
`ae13d06f-6461-43a8-a9cc-3e0e0eafde50`, slug contad, lifecycle
activation_pending, zero membros, sem demo/parceiro interno e com auditoria.
E-mail do futuro login fornecido diretamente, mantido em evidência privada;
nenhum convite enviado, senha criada ou acesso liberado. Não associado aos
outros escritórios. Lista da prévia continua vazia. Cadastro não é deploy.

**Integração documental:** main remota incorporada por fast-forward até
`d338abc`; aplicação das mudanças preservadas exigiu resolver três apêndices.
Escolha humana: IDs locais D-316/D-317 e V-318/V-319 preservados; registros
remotos e referências por origem passaram a D-318/D-319 e V-320/V-321.
Stash de recuperação `0a48fb863b5f888d505f93c6b4c03dfe9d72569c` e cópias/hashes
privados mantidos, sem descarte de conteúdo. Nenhum ID foi substituído globalmente.

Candidata final após correção de auditoria em
`.tmp/contad-development-2026-11-06/release-candidate-final/`, 816 arquivos,
SHA-256 `ced90f343ddbb08c82c7950cc7125a68d712e086708d9f317f06c203834a3eaa`;
ZIP reaberto e hashes conferidos. Manifesto preserva hub.0076/0077/**0078** e
intelligence.0031 no retorno. Candidata anterior preservada separadamente.
Sem deploy, migração remota, habilitação da prévia ou chamada IA paga.
Q-28/Q-46/Q-47, recuperação/backup, acesso/ativação, D-73, treinamento e aceite
continuam pendentes. Credencial ODBC deve ser fornecida pelo técnico por canal
local; não pedir senha no chat ou usar credencial da aplicação por inferência.

**Publicação da fonte V-322:** commit f86ae4d7630bc707be2f407a1a9c12c5582110b9
na main, SHA remoto conferido e 816 hashes do commit iguais à candidata.
[CI 42231907397](https://github.com/Mewstacks/CicaContabil/actions/runs/42231907397)
concluído com sucesso: verify, agent e agent-package aprovados. SQLite 1.694
testes/163 subtestes, 22 skips; PostgreSQL 1.714/163, dois skips (Python
Playwright opcional e OCR português ausente no runner). .NET Linux 43 aprovados,
um skip Windows; build/manifesto Windows e três builds Docker aprovados.
Não é nova instalação Windows 1.0.3; o job de pacote CI usa versão 1.0.0.
Implementação publicada, sem deploy da aplicação até esta observação.

**Recuperação em continuidade:** acesso ao Neon confirmado pelo seletor da
organização compartilhada; CICA/raspy-river-46466568, branch production
br-odd-tree-b6vhgfnv. Ambos os aliases correspondem ao endpoint do painel,
LSN 0/BE42A1F8 às 14:16:49 UTC. Janela existente de seis horas, sem snapshots
ou agenda. Tigris cica-contabil-media privado, snapshot false, 53 objetos e
2.901.052 bytes; hash apenas de metadados do inventário, não dos conteúdos.
Responsável aprovou até US$ 1,00 para backup pontual/ensaio isolado/retenção de
sete dias. Cópia protegida preparada com quatro verificações sintéticas; primeira
tentativa recusada pelo limite de 36 caracteres no ID de lifecycle, antes de
copiar objetos; corrigido para 35 caracteres e retentativa em andamento. Não
confundir uma requisição recusada com backup concluído ou restore testado.

**Backup/ensaio pontual final, 06/11/2026:** snapshot Neon
snap-hidden-tree-b6xt5ssj de 14:29:44 UTC/648.298.496 bytes, expiração
13/11/2026 14:29:44 UTC confirmada por API e painel. Restore isolado
br-soft-pond-b6b07dau, sem finalize/migração de conexões. Consultas somente
leitura via endpoint direto, desde Fly: default 180 tabelas/356.077 linhas,
knowledge quatro tabelas/193 linhas; esquemas, migrações e todas as contagens
iguais à produção na observação, hashes de sete tabelas críticas do default
e todas as quatro do knowledge iguais. Tentativa inicial pelo pooler recusou
statement_timeout no startup, antes de consultar; conexão direta resolveu.
Não é comparação por hash de cada linha de todas as 180 tabelas.

Todos os 53 arquivos referenciados cobertos pelo manifesto Tigris; 53 objetos/
2.901.052 bytes recuperados em pasta temporária no Fly e hashes iguais,
limpeza concluída. Manifesto final pareado ao snapshot e verificado,
SHA-256 9cb388132280969bf4e43ef03cd8c60a82684f3a8782b1df613c5577d9453443.
Originais/inventário preservados; lifecycle só no novo prefixo, sete dias.
Compute do ensaio idle e branch com expiração de sete dias; produção segue
default/ready no endpoint original. Chave limitada ao projeto revogada,
API retornou 401 e tokens locais removidos. Sem dump no Mac, agenda nova ou retenção global alterada; recursos
limitados ao escopo aprovado. Cobrança final não medida. Gate pontual atendido; D-73/RPO/agenda recorrente
continuam abertos. Logs/capturas privados em .tmp/contad-development-2026-11-06.

**Deploy e pós-verificação finais:** release Fly **72** concluída em 06/11/2026,
imagem contad-f86ae4d-20261106, digest
sha256:3f5f91ec176db121531a1e26176a1054f8001088fb273eea88e99b11ede832eb.
Build local Colima para linux/amd64; release command/canários e deploy passaram.
Web 891e63ef665e58 e worker 1857691da097e8 started/512 MB, mesma imagem;
reserva 287e35db920e48 stopped e imagem anterior preservada. Sem ampliar tamanho
ou manter novo builder/compute. Hashes de todos os **645 arquivos de fonte do
runtime** iguais ao ZIP aprovado nas duas máquinas; agregado
f00613a9dca60643a99f49efb16e8c784ecb78a18115c028141190ae88974f8d.
Ambos os aliases preservam o endpoint Neon original e aplicaram hub.0078 e
intelligence.0031_agent_sync_scope. Health nos dois domínios HTTP 200 com banco/
cache ok; Celery worker ready às 14:50:54 UTC, check Fly passing, sem erro no
buffer de 100 entradas observado. Requisição sem identidade/assinatura válidas
401; prévia/download anônimos 302 para login. Não prova pareamento válido ou
isolamento com dados reais novos; testes sintéticos anteriores cobrem esses controles.
Lista de prévia só contém o UUID CONTAD; exportação homologada false/mTLS false.
CONTAD segue activation_pending/zero membros/zero prévias. Sem ODBC, pareamento,
sincronização, importação Domínio, treinamento, IA paga ou aceite novos.
Logs privados: fly-deploy-v2.log, deployed-web-verification.log,
deployed-worker-verification.log, production-http-checks.json e fly-after-*.json.
Código implantado f86ae4d/CI 42231907397 aprovado; registro posterior documental
não muda os hashes da aplicação. PC-19/Q-28/Q-46/Q-47/D-73 continuam abertos.

**Continuidade informada pelo operador, 06/11/2026:** responsável afirmou possuir
agora a credencial EXTERNO. Nenhuma senha recebida/registrada ou tentativa ODBC
executada nesta mensagem; DSN de sistema x64, validação de tipo/permissões,
conexão do configurador/LocalSystem e recorte/pareamento permanecem pendentes.
Orientação guiada conferida com código do configurador e documentação oficial:
administrador ODBC x64 e SQL Anywhere 17; sem mudar conexão existente, inferir
parâmetros do banco ou usar valores padrão de credenciais.

Operador informou abertura da configuração SQL Anywhere 17; não houve captura
ou controle remoto automatizado. Próxima instrução preparada para consultar
somente o Server name da conexão x86 atual pela interface ODBC, com Cancelar.
Nome proposto para o novo DSN: CICA_CONTAD. Nenhum DSN salvo/testado, parâmetro
real de servidor confirmado ou segredo recebido nesta etapa da execução guiada.

Operador informou Server name srvContabil a partir da conexão x86 existente.
É parâmetro informado, não resolução de rede ou autenticação comprovada. Próxima
instrução: preencher o novo DSN x64 com esse servidor/EXTERNO e testar conexão;
resultado ainda pendente, sem senha recebida ou pareamento executado.

**ODBC interativo informado no PC CONTAD:** operador respondeu "deu successful"
ao Test Connection do novo DSN CICA_CONTAD x64/SQL Anywhere 17, com srvContabil
informado e EXTERNO digitado localmente. Sem senha recebida ou teste automatizado.
Resultado comprova somente o sucesso informado dessa conexão interativa;
salvamento do DSN, permissões de consulta, teste do configurador/LocalSystem,
pareamento e envio permanecem sem evidência própria. Próxima instrução: salvar
novo DSN sem senha e testar credenciais explícitas no configurador instalado,
sem executar Conectar à CICA ou persistir configuração do serviço.

Imagem recebida do configurador confirma Domínio Local, DSN CICA_CONTAD
visível e SQL Anywhere 17 selecionado; autenticação por DSN ainda marcada na
captura, campos desabilitados. Orientada desmarcação e EXTERNO explícito.
Depois, operador relatou clique em Testar sem resultado percebido. Nenhuma
mensagem final recebida: teste do configurador permanece inconclusivo.
Inspeção do código da mesma versão confirma status textual abaixo dos botões,
sem janela modal; não é diagnóstico de travamento. Próxima verificação é ler
a última linha da área rolável, sem repetir o teste ou Conectar à CICA.

**Configurador no PC CONTAD — relato final:** operador informou "conexao
confirmada" após localizar o status abaixo dos botões. Pelo caminho do código
1.0.3 conferido, essa mensagem vem após abertura ODBC e consulta fixa mínima
SELECT TOP 1 codi_emp; nenhum dado dessa consulta foi recebido no chat. É
resultado informado pelo operador, sem captura posterior que comprove o modo
de autenticação efetivamente selecionado. Não prova LocalSystem, permissões
somente leitura completas, pareamento/sincronização ou consulta do Razão/títulos.

**Preparação do recorte SURIA, 06/11/2026:** responsável indicou 09/2026 e arquivos
em Downloads; confirmou SURIA após diferença no nome inicial URIA, sem saber
código Domínio. PDF bancário primeiro cabeçalho renderizado/conferido; titular,
período conferido. OFX tem identificador de conta mais longo e mesmo sufixo,
sem normalizar por hipótese; relação bancária ainda requer confirmação, como
já previsto em bank_evidence.compare_bank_files. SHA-256 PDF
41d723873b6752263ccf2f154f2e5a759aeaaba6892423e526c39bb7119839d8 e OFX
30c48e34223ee5bac3935556b6e547f50bcf478d055fa036d1adab0a40426bfd
iguais ao piloto V-316. Duplicatas com (1) têm os mesmos bytes. Reutilizados
42 checks/163 eventos como evidência histórica, sem repetir o processamento.
Plano de contas encontrado pertence a outra empresa, não utilizado como fonte
contábil SURIA; intermediários dessa inspeção removidos, original preservado.
Preparação privada contad-suria-pilot-request.json com pendências explícitas.

Preflight Fly em transação READ ONLY: CONTAD activation_pending; zero membros,
empresas, contas financeiras, contratos, códigos e agentes. Resultado em
contad-pairing-preflight.log. Nenhuma alteração remota nesta rodada, código de
pareamento, envio de arquivo financeiro, SQL novo do ERP ou IA paga.
Faltam código Domínio, referência/IDs revisados, acesso/ativação e prova
LocalSystem/pareamento. Consulta do código orientada por documentação oficial
Controle > Empresas, sem editar/gravar/excluir qualquer cadastro.

**Continuidade do recorte Q-28/D-320:** operador informou código Domínio
**212** para SURIA/09-2026. Preparação privada atualizada e pendência desse
código removida; informação humana, sem nova consulta ao ERP ou alteração
remota. Conta/referência e IDs internos revisados ainda não obtidos. Próxima
consulta guiada limitada à conta existente em Movimentos > Lançamentos de
Extrato Bancário; sem inclusão, gravação ou importação. Não houve novo teste,
pareamento ou transmissão nesta atualização documental.

**Consulta guiada do extrato:** captura inicial era do módulo Escrita Fiscal;
nova captura do operador mostra a janela Lançamentos de Extrato Bancário,
conta/filial vazias, Mês/Ano 11/2026 e grade vazia. Não confirma empresa ativa,
conta, ausência de movimentos de setembro ou IDs internos. Preparada consulta
do cadastro existente pelo F2 (solução oficial 6705) e filtro 09/2026, sem
gravação/importação. Nenhuma operação remota ou consulta SQL executada.

**Extrato Sicredi/09-2026 visível:** nova captura recebida mostra descrição
BANCO SICREDI, competência 09/2026, movimentos de origem Importação e todas as
linhas visíveis com Conciliado marcado. Imagem ampliada localmente apenas para
inspeção do campo da conta, sem conseguir ler com segurança o código selecionado.
Não comprova empresa ativa, total de movimentos, conciliação integral do mês,
relação com a conta do PDF/OFX, referência técnica ou IDs internos. Preparação
privada atualizada apenas com observações e pendências, sem dados da grade nos
registros versionados. Nenhuma consulta SQL, alteração ERP, pareamento ou envio.

**Código da conta transcrito:** operador informou **8**, resolvendo a leitura
do campo BANCO SICREDI na captura de 09/2026. Registrado como código contábil
do recorte SURIA/212; não é agência/conta bancária ou ID interno de extrato.
Preparação privada atualizada, sem substituir account_reference por 8 nem
remover pendências de vínculo financeiro/IDs/acesso. Próximo levantamento:
Razão local dessa conta em 01–30/09/2026, consulta orientada pelas soluções
oficiais 1817/3132, sem relatório recebido/emitido comprovado nesta rodada.
Nenhuma alteração remota, consulta SQL nova, pareamento, transmissão ou teste.

**Razão real recebido/conferido — Q-28/D-320:** Downloads/Razão.pdf, 268.602
bytes, quatro páginas, SHA-256
af1ca6b11f558765531bb8009538ce585bbe781629732b281d355427273889d9.
Cabeçalhos das quatro páginas corroboram SURIA, conta 8 — BANCO SICREDI e
01–30/09/2026; código da empresa 212 continua informado pelo operador.
Renderização das quatro páginas inspecionada. Extração privada dos campos
numéricos por posição no PDF, em ordem vertical, obteve 45/45/49/24 linhas:
163 números impressos distintos, todas as datas no período, sequência dos
163 saldos e totais de débito/crédito iguais aos impressos. Metadados e
derivados em .tmp/contad-development-2026-11-06/suria-razao-review, sem alterar
o original ou o código do produto.

Hashes dos PDF/OFX bancários reconferidos contra V-316; reutilizada a
normalização bancária histórica, sem repetir aqueles 42 checks. Comparação
local das datas e débito menos crédito no Razão contra valores assinados do
banco: multiconjuntos de 163 linhas iguais, sem sobras nessa chave e saldos
inicial/final dos PDFs iguais. Há 159 chaves singulares e duas chaves repetidas
com quatro linhas; não equivale a alocação confirmada ou correspondência
semântica/documental. Seis linhas têm campo de contrapartida vazio; o relatório
de uma conta não comprova partidas completas. Nenhuma partida foi inventada,
importada ou confirmada; 163 eventos não se tornam 326 ou atendem os 200 de D-73.

Conflito observado Q-28: captura da janela de extrato Domínio apresenta saldos
inicial/final distintos dos dois PDFs; valores/diferenças estão na evidência
privada. Empresa ativa não aparece na captura, causa não determinada.
Solicitada conferência da empresa selecionada e confirmação do vínculo entre
conta contábil e bancária, sem corrigir saldos. Isso bloqueia fechar o recorte;
IDs de extrato, acesso/ativação, LocalSystem e demais gates seguem pendentes.
Nenhum SQL novo, envio de arquivo financeiro, alteração remota ou ERP, IA paga,
pareamento ou teste funcional do agente nesta rodada.

**Respostas e sonda restrita Q-28/D-320:** operador confirmou SURIA/212 também
na janela de extrato, mas não sabe confirmar a relação da conta contábil 8 com
a conta bancária dos arquivos. Empresa ativa resolvida por relato; diferença de
saldos e vínculo permanecem pendentes. Documentação oficial Domínio 1878/238
descreve saldo informado na rotina e escolha da conta contábil ao importar;
não determina a causa da diferença desta instalação. Nenhum saldo foi alterado.

Preparado Downloads/CICA-Consulta-Recorte-SURIA.ps1 para PowerShell x64.
Responsável autorizou especificamente a execução manual guiada, somente leitura,
empresa 212/conta 8/09-2026, metadados de dois objetos, cabeçalhos candidatos e
contagem de itens, sem históricos/valores ou envio ao CICA. Roteiro valida
schema/tabela/colunas exatos, usa dois SELECTs fixos parametrizados, limita
a 20 candidatos (busca 21 para detectar excesso), recusa IDs repetidos/fora
do recorte, usa senha EXTERNO local e não imprime conexão/segredo nem grava
arquivos/configuração. APIs GetSchema/ConnectionTimeout conferidas em fonte
Microsoft. Guardas e SQL revisados estaticamente; PowerShell não disponível
no Mac, sem parse/execução PowerShell, consulta ODBC ou resultado do PC ainda.
SHA-256 do roteiro final:
054d736be382097ad6c76d15eb240d7aeff84895c7e097603c12e632c1f4ed4a.
Proposta/evidência privada em contad-diagnostic-proposal.json. Aprovação não é
execução, prova do schema, revisão dos IDs, pareamento ou solução dos saldos.

**Primeira tentativa guiada da sonda:** retorno Windows PowerShell 5.1 mostra
ObjectNotFound no Get-FileHash do caminho esperado em Downloads. O comando de
execução ficou protegido pela condição: roteiro/ODBC não executados nessa
tentativa. Não é erro de credencial, schema ou serviço. Mac conserva original
de 7.093 bytes com SHA-256 final idêntico. Próxima orientação: localizar pelo
nome nas subpastas de Downloads e conferir hash antes da execução autorizada;
se não encontrado, transferir o mesmo arquivo. Sem mudança do roteiro/ERP/backend.

**Resultado posterior da sonda — informado pelo operador:** após resolver a
localização, recebido JSON do roteiro com header_count=1, empresa 212,
ledger_code=8, competence=2026-09-01 e item_count_in_period=163. ID do cabeçalho
guardado na evidência privada. Retorno do caminho de sucesso do script implica
checagem de metadados exatos dos dois objetos, datas/empresa/conta e unicidade
do ID antes da contagem. É relato do PC, sem captura de controle independente;
não comprova tipo/permissões EXTERNO ou execução sob LocalSystem.

Revisão local: candidato único e seus limites/contagem consistentes com o recorte
e os 163 movimentos do banco/Razão. Não confundir o ID do cabeçalho com código
da conta ou números de lançamento do Razão. Preservado scope_reviewed=false;
associação bancária e divergência de saldos não resolvidas pela sonda. Nenhum
histórico/valor retornado, senha recebida, dado enviado ao CICA, alteração ERP,
configuração, pareamento ou ativação. Não repetir consulta aprovada sem necessidade.

**Consulta guiada dos dois pontos Q-28:** pesquisa oficial confirmou Arquivos >
Contas Contábeis para localizar conta existente (43); não confirmou campos
obrigatórios de agência/conta nesse cadastro. Preparada conferência somente de
identificação explicitamente registrada da conta 8, sem alterar dados. Solução
1878 descreve saldo inicial informado na rotina de extrato, sem esclarecer
causa da divergência desta instalação. Nenhum caminho de log, regra de transporte
de saldo ou equivalência bancária foi presumido. Ainda não recebida captura do
cadastro; consulta guiada não é revisão concluída nem nova execução SQL/ERP.

**Cadastro da conta 8 — captura recebida:** código 8, descrição BANCO SICREDI,
tipo Analítica e situação Ativa visíveis; classificação compatível com o Razão.
Tela enviada não mostra agência/conta bancária, nem origem do saldo inicial.
Isso corrobora a identificação contábil, sem confirmar vínculo bancário ou
causa da divergência. Imagem referenciada na preparação privada; não houve
edição, gravação ou nova consulta SQL executada pelo agente.

**Entrega documental de continuidade D-320:** resumo simples salvo em
docs/contad-continuidade-2026-11-06.md e prompt privado em
Downloads/CONTAD-prompt-continuidade.txt. Conferidos contra os registros canônicos
e preparação privada: release/fonte, estado do PC, recorte, resultado da sonda,
limites da comparação, diferença de saldos e próximos passos. Caminhos locais e
links relativos verificados; prompt com acesso restrito, sem senhas/tokens e
fora do Git. Identificador do extrato, conta bancária, valores e login não foram
incluídos no novo resumo versionável. Sem novo teste funcional, consulta ERP,
deploy, commit/push, sessão criada ou conclusão dos gates por essa documentação.

## V-323 — Corpus aceito e confronto repetível banco × Razão PDF (06/11/2026)

Continuidade D-320, PC-19/etapas 03/09/12. Responsável afirmou que a empresa
está fechada e os arquivos foram fornecidos para teste; corpus aceito como
evidência local. Origem do saldo da captura Domínio deixa de ser condição para
esses testes. Não reabrir essa pergunta nem declarar a causa esclarecida.

**Implementação:** `apps.hub.ledger_evidence` lê o layout textual do Razão
Domínio observado, com cabeçalho de empresa/CNPJ/conta/período constante,
sequência das folhas, posições explícitas de débito/crédito/saldo, IDs impressos,
limites de tamanho/páginas/linhas, sequência dos saldos e totais. Tolerância
vertical preserva a camada numérica apesar de históricos sobrepostos; não remove
glifos numéricos por deduplicação. Conserva contrapartida vazia e referência de
página/posição; não cria `JournalEntry`, `IndependentLedgerRecord` ou alocações.

CLI `scripts/compare_bank_ledger.py` reutiliza os leitores bancários existentes,
confere titular/período/conta contábil solicitados e preserva multiplicidade e
grupos ambíguos. Relatório JSON com SHA-256 das três fontes, dados/referências
das linhas e saldos; publicação atômica 0600 sem sobrescrever destino/symlink,
sem valores financeiros no stdout. Inicialização standalone usa settings de
teste isolados, sem carregar `.env`.

**Teste automatizado final:**
`.venv/bin/pytest tests/test_ledger_evidence.py tests/test_bank_evidence.py tests/test_independent_ledger.py tests/test_title_allocation.py -q`:
**139 aprovados, cinco skips**, em 19,64 s. Os skips são os testes anteriores
de concorrência entre filas/retry/escrituração que exigem PostgreSQL, não
executados nesta rodada SQLite; não alegar regressão integral/PostgreSQL atual.
O novo arquivo inclui 39 testes de leitura/escopo/ambiguidade, sinais D/C,
camadas sobrepostas, limites, arquivos incompletos/corrompidos, preservação de
fontes, falha de gravação, 0600, symlink e ausência de rede/banco.
Ruff global, MyPy dos dois módulos novos, Django check e makemigrations --check
aprovados, sem migração nova. JUnit em `.tmp/contad-ledger-evidence-2026-11-06/`.

**Corpus real:** as três fontes de Downloads mantêm os hashes de V-322;
conferidas as quatro imagens já renderizadas do Razão e executada a CLI final
com bloqueio explícito de socket.connect/connect_ex e conexão Django durante
todo o bootstrap/percurso. Resultado: 163 linhas no banco e 163 no Razão,
multiconjuntos de data/valor iguais, zero sobras, 159 candidatos únicos e dois
grupos ambíguos contendo quatro linhas de cada fonte. Saldo inicial/final dos
PDFs coincide; seis linhas mantêm contrapartida ausente. Cada linha numérica,
ID impresso, conta de contrapartida disponível e página conferidos contra a
extração independente anterior de V-322, sem diferenças nas 163 linhas.
Originais reconferidos após execução; relatório 0600/ignorado pelo Git.
Evidências privadas: `conferencia-final.json` e `verification.json` na pasta
acima, incluindo hashes da fonte de implementação e do relatório.

**Limites:** são os mesmos 163 eventos, sem aumento de amostra D-73.
Correspondência data/valor não confirma alocação; a rotina é conferência local
do efeito da conta, não importador de partidas completas ou adaptador ODBC.
Nenhuma alteração de interface, SQL/consulta ERP, pareamento, envio remoto,
IA paga, ativação comercial, deploy, commit/push ou homologação nesta rodada.
Acima da discrepância histórica, prevalece a aceitação humana para teste;
pareamento/serviço real, fontes de títulos, DE-PARA e aceite conservam seus gates.

## V-324 — Release 73, ativação e integração real CONTAD (06/11/2026)

D-321 autoriza deploy e conclusão das pendências CONTAD. Preflight real somente
leitura confirma release 72/fonte f86ae4d em web/worker e CONTAD em
activation_pending, zero membros/contratos/módulos/empresas/contas/agentes/códigos.
Exportação Domínio false. Primeira tentativa de preflight parou no import de
nome de modelo incorreto, antes da transação/consulta; corrigido para
AgentEnrollment e consulta final concluída, sem alteração remota nessa leitura.

Responsável confirmou PC disponível e escolheu ativação somente Conciliação,
perfil Proprietária e contrato existente R$ 200/mês, **sem enviar convite** ou
iniciar cobrança automática. Execução/estado final ainda dependem da ação própria.
O cadastro do contrato individual sem plano de catálogo mantém o fechamento
automático de faturas fora desse contrato, conforme caminho existente do código;
não criar plano reutilizável, invoice, Asaas, convite, senha ou teste gratuito.

Preparado comando administrativo `manage.py compare_bank_ledger` na imagem,
reutilizando o leitor/comparador e escrita atômica 0600 no módulo da aplicação.
CLI sem dependência de scripts externos ao runtime; manifesto inclui a CLI.
**100 testes focados aprovados**, sem skips, 0,58 s (leitor/comando/CLI/banco/
alocação de títulos); Ruff global e MyPy dos três módulos aprovados.
Sem alteração de interface, endpoint ou migração. CI/candidata/deploy e
ativação/pareamento permanecem em andamento; não tratar a preparação como conclusão.

**Ativação efetivamente executada:** transação no escritório próprio mudou
lifecycle para active, habilitou somente reconciliation e registrou contrato
individual ativo, R$ 200/mês travado, sem plano/IDs Asaas e sem vigência inventada.
Nenhuma fatura, convite, senha ou usuário criados; login informado não existe,
logo zero membros permanece. Papel Proprietária aprovado para vínculo posterior
por fluxo seguro; não houve acesso pessoal liberado. Dois testes adicionais
isolados (com/sem usuário existente), 14,61 s, comprovaram acesso ao módulo,
recusa de IA, exclusão do fechamento automático e repetição sem contrato duplicado.
Primeiro ensaio local recusou chave de metadados `authorization`; corrigida para
`decision` antes de qualquer execução remota, sem relaxar auditoria.

**Artefato:** fonte 651368c101bec5b8b0bb9a75b4fb1268029dd220 publicada na main,
SHA remoto idêntico. Candidata: 820 arquivos, ZIP SHA-256
600af5819f7cd90f61bafbafc586f4f168bbe1e56acff2d1f7ecfb7cbb58c2b6;
todos os blobs do commit conferidos. Trabalhos locais D-316/D-317/V-318/V-319
preservados fora do índice/commit; histórico do workspace não foi reescrito.
Imagem linux/amd64 registry.fly.io/cica-contabil:contad-651368c-20261106,
digest sha256:20f01b3888c8fa02395a876e6b4597fbf49db7a29a0919e288d3a9b78979717a.
Ensaio da imagem com rede desabilitada e conexão Django bloqueada: comando
administrativo com três fontes sintéticas aprovado, arquivo 0600 e zero
confirmações. Todos os 647 arquivos de fonte runtime iguais à candidata,
hash agregado be6a65a2754a42c4e63f77c4ea1b8e9b26e149243eb20b63763c2aeb43a08772.
Imagem enviada ao registro, sem deploy até esta observação.

Backup existente D-320 reconferido somente por metadados: manifesto Tigris final
com hash original idêntico, 53 objetos presentes/tamanhos iguais e regra de
sete dias preservada, mesma referência de snapshot Neon. Não criou backup,
chave/recurso/retencão ou repetiu restore; snapshot continua apoiado na prova
de V-322, não em consulta API Neon nova. Evidências privadas nesta rodada em
`.tmp/contad-deployment-2026-11-06/`.


**CI concluído:** [42282953292](https://github.com/Mewstacks/CicaContabil/actions/runs/42282953292),
head 651368c, três jobs aprovados. SQLite: **1.735 testes/163 subtestes**, 22 skips,
312,49 s; PostgreSQL: **1.755 testes/163 subtestes**, dois skips, 398,78 s.
Skips PostgreSQL: Python Playwright opcional e OCR português indisponível no
runner; concorrência executada. Agente/pacote Windows e imagens backend/
multimodal/trainer aprovados. Build do CI não muda o MSI 1.0.3 instalado no PC.

**Deploy concluído:** release Fly **73**, 06/11/2026 20:06:46 UTC, imagem pelo
digest acima. Release command aprovado; web 891e63ef665e58 e worker
1857691da097e8 iniciados, 512 MB cada. Reserva 287e35db920e48 continua parada,
configuração igual à anterior. As três máquinas finais são as originais;
canários/release machine transitórios destruídos. Ambiente, portas, recursos,
processos e políticas comparados antes/depois, preservados. Fonte runtime:
647 arquivos/hash agregado esperado conferidos por SSH em **ambas** as máquinas.
Comando administrativo disponível; aliases default/knowledge no endpoint Neon
original com hub.0078/intelligence.0031. Celery/beat iniciou e worker ready.

Readiness nos domínios público e Fly **200**, banco/cache ok; liveness **200**.
Prévia/download anônimos **302** para login, heartbeat sem autenticação **401**.
Exportação false e allowlist de prévia somente CONTAD reconferidas. Lifecycle
active/Conciliação/contrato individual sem cobrança automática/zero convites e
faturas também reconferidos no runtime. Evidências postdeploy-web.log,
postdeploy-worker.log, postdeploy-http.json, fly-after-*.json e worker-postdeploy.log
na pasta privada desta rodada. Primeira tentativa HTTP usou Python do sistema
sem cadeia CA local disponível; repetida com ambiente/CA da aplicação e TLS
verificado, sem desabilitar validação de certificado.

**Recorte autorizado e preparado:** resposta humana “Autorizar somente esse
recorte” registrada em D-321 para SURIA/212, conta contábil 8/Sicredi,
09/2026 e somente cabeçalho da sonda. Empresa/conta financeira cadastradas
pelas fontes aceitas; manifesto validado, código de uso único/60 minutos
entregue em arquivo privado 0600. Três testes isolados de ativação/recorte
aprovados, 14,33 s. Não é código genérico nem autorização de outros dados.

**Tentativa real do PC:** captura mostra HTTPS correto, Domínio Local,
CICA_CONTAD/SQL Anywhere 17, EXTERNO explícito, senha mascarada e autenticação
herdada do DSN desmarcada. Erro “Não foi possível restringir a pasta de
configuração”. Backend confirma código consumido/agente criado, mas zero
heartbeat/conector/linhas. Fonte Save executa icacls antes da gravação DPAPI;
a falha não comprova credencial local salva nem serviço autenticado. Orientada
abertura como administrador e substituição apenas dessa credencial órfã pelo
mesmo recorte. Não arquivar captura com código em Git. Consulta metadata inicial
usou campo inexistente last_sync_at; falhou em transação somente leitura e foi
corrigida para last_checked_at, sem mudança de dados nessa inspeção.


**Prova real concluída:** operador retornou “Recorte configurado” e backend
confirmou novo agente/heartbeat/163 itens. Credencial órfã anterior revogada,
sem uso; código substituto consumido e removido do arquivo privado ao concluir.
PowerShell do PC: Running/LocalSystem/ready em 20:13:55 UTC; após Restart-Service,
Running/Auto/LocalSystem/ready em 20:15:14 UTC. Presença de campo de senha no
novo DSN informada como true não provava valor preenchido. Removidos apenas
PWD/Password/Senha no CICA_CONTAD x64, sem ler/exportar valores; após segundo
reinício: **CampoDeSenhaNoDsn=false, Running/ready**, 20:17:39 UTC.
MSI/DSN original/servidor/usuário e senha do ERP não foram alterados.

Conferência final somente leitura no backend, posterior ao segundo reinício:
agente ativo, heartbeat/ciclo posterior a 20:17 UTC, conector **healthy** sem
código de erro; empresa única 212, **163 DominioBankEntry e 163 AccountingEntry**
da fonte local, **zero source_id duplicado/linha fora de recorte**. Manifesto
novamente validado no escritório/conta. Hash dos multiconjuntos de data/módulo
do valor igual ao corpus aceito. No recorte, C=108 saídas e D=55 entradas reproduz
também o multiconjunto de data/valor assinado do banco, sem alterar dados ou
promover essa observação a regra genérica de partidas. 151 is_linked refletem
vínculos existentes do extrato, não conciliações aprovadas por este teste.
**Zero IndependentLedgerRecord/JournalEntry**: o espelho bancário não fabrica
Razão independente. Repetição/reinício não aumentou contagem. Evidência privada:
agent-final-verification.json e agent-sync-final.log na pasta desta rodada.

**Limites remanescentes:** resultado do PC é execução guiada informada pelo
operador, cruzada com recepção real no backend; não houve controle automatizado.
163 itens cabem numa página, sem prova real de várias páginas ou falha de rede.
Ausência dos campos de senha foi conferida no DSN dedicado, sem leitura ampla
ou extração de registro. Acesso pessoal não foi criado por escolha de não
emitir convite. Fontes completas/títulos/baixas/regras/DE-PARA, Q-47, 200 eventos
D-73, recuperação recorrente/RPO, treinamento e aceite continuam abertos.
Não declarar homologação integral ou importação ERP. Nenhum provedor de IA,
nova cobrança/recurso recorrente ou convite foi acionado.

## V-325 — Acesso pessoal da Grazi na CONTAD (06/11/2026)

Autorização humana posterior em D-321: configurar conta com o e-mail já
informado e senha simples, mantendo ausência de convite. Preflight somente
leitura confirmou login inexistente, zero membros/convites/faturas, escritório
active/Conciliação/contrato individual R$ 200 e 163 movimentos do agente.
Identidade/credenciais permanecem em arquivos privados, sem Git.

Primeiro roteiro aprovado em quatro testes, 14,85 s, mas o processo extra no
web foi encerrado por OOM. Log Fly confirmou apenas processo administrativo
python morto; health e agente continuaram com HTTP 200. Leitura posterior em
worker confirmou zero usuário/membro/auditoria parcial. Roteiro ajustado para
gerar/validar senha e Argon2 localmente, transmitir só hash à transação no
worker existente, sem alterar política, parâmetros, recurso ou código hospedado.

**Quatro testes finais com Argon2 real aprovados**, 15,01 s: criação e login por
senha, escritório/empresa e ação de importação, nenhuma mensagem/convite/fatura,
preservação de credencial existente, recusa de repetição sem reset/duplicação
e rollback integral diante de falha de auditoria. Política vigente com mínimo
oito caracteres e demais validadores preservada. Roteiro privado, não nova
funcionalidade ou migração da aplicação; não foi necessária regressão/deploy.

**Execução remota:** usuário ativo Grazi, vínculo único owner/Proprietária na
CONTAD, senha inicial Argon2, sem staff/superusuário/grupo/permissão direta ou
acesso à plataforma. Auditoria de criação persistida, sem e-mail/senha em
metadados. Contrato individual/Conciliação/163 movimentos mantidos, zero convite,
fatura ou arquivo importado pela verificação.

**HTTP real por HTTPS/TLS verificado:** GET login 200, POST com senha e CSRF
302 para /app/; Conciliação autenticada **200**, identidade Grazi/escritório
CONTAD/SURIA 212 visíveis e formulário Nova importação/campo de arquivos/origem
Extrato bancário disponíveis. Sessão encerrou por POST com CSRF, acesso anônimo
posterior retornou 302 ao login. Não houve force_login, bypass MFA, convite,
e-mail, upload ou confirmação contábil. Não é QA visual de navegador nem prova
de arquivo efetivamente importado nessa conta.

Credencial entregue em `/Users/pedromachado/Downloads/CICA-Grazi-acesso.txt`,
0600, sem senha literal em argumentos ou saídas de ferramentas. Não foi
implementada expiração/troca obrigatória; não alegar essas propriedades para
a senha inicial. Evidências privadas em `.tmp/contad-grazi-access-2026-11-06/`:
tests-argon2.xml, account-created-receipt.json, https-access-verification.json,
account-final-state.log. Duplicatas transitórias da credencial/hash removidas
após verificação; arquivo de entrega preservado.

Acesso pessoal concluído. Restam fontes completas/títulos/baixas/regras/DE-PARA,
Q-47, D-73/200 eventos, provas operacionais/recuperação recorrente, treinamento
e aceite. Release continua 73/fonte 651368c; exportação Domínio false.

## V-327 — Carteira: protocolo publicado, inventário real pendente (06/11/2026)

D-323/PC-19, etapas 03/09/12. Responsável definiu histórico financeiro desde
setembro/2026 e posteriormente confirmou operador ainda indisponível. Cadastros
e contas integrais fazem parte do objetivo. Fonte **e9311eb**, CI
[42294764025](https://github.com/Mewstacks/CicaContabil/actions/runs/42294764025)
aprovado; backend publicado na **release Fly 74**. Isso é uma entrega parcial:
manifesto real continua piloto, zero varredura de carteira, sem fontes novas.

**Implementação:** manifesto `dominio-portfolio-v1` ligado ao escritório,
revisão integral SHA-256 e fonte companies explicitamente selecionada. Agente
novo usa scoped-v1 no piloto e scoped-v2 na carteira; configuração permite
transição, mas recepção de carteira e consumo de código rejeitam cliente antigo.
Páginas de até 500, cursor numérico persistido com os cadastros em transação,
replay/retomada, validação atômica e trava do agente com revalidação de revogação.
Situação bruta preservada em dominio_status, mapa obrigatório, desconhecida
rejeitada; ausentes não são apagadas/desativadas. Contagens/fim explícitos,
abandono de scan se a contagem mudar e releitura periódica dos cadastros.
Não é snapshot transacional ERP; mudanças com mesma contagem durante a leitura
podem exigir o ciclo seguinte. Contrato técnico em
[carteira](docs/contad-carteira-protocolo.md). Migrações aditivas hub.0079 e
intelligence.0032/0033; nenhuma fonte de conta/Razão/títulos foi presumida.

**Verificações:** regressão local final PostgreSQL 17 descartável, **1.788
aprovados/163 subtestes, um skip**, 286,91 s; skip de navegador Python opcional.
CI exato: SQLite 1.766/163, 23 skips; PostgreSQL **1.787/163, dois skips**,
239,90 s (Playwright Python opcional e OCR português ausente no runner).
Concorrência foi executada: uma abertura e um commit para requisições paralelas,
replay, 501 empresas, paginação numérica, inativas, alteração de origem,
rollback após escrita e isolamento. Ruff global/MyPy dos cinco módulos/Django/
migrações sem pendências aprovados. .NET local/Linux: 51 aprovados/um skip
Windows; Windows: **52 aprovados, zero skips**. Serviço, GUI e ponte compilados;
três builds Docker aprovados no CI. Nenhuma interface foi alterada; verificação
HTTPS de login/HTML não é QA visual nem execução de Playwright nesta rodada.

**Tentativas descartadas:** foco anterior PostgreSQL teve 49 aprovados e aviso
no teardown por sobreposição indevida com início da regressão, interrompida.
A primeira regressão sequencial caiu por disco interno Docker cheio: 1.638
aprovados/163 subtestes, 8 falhas/166 erros, um skip; log PostgreSQL mostra
PANIC/No space left on device. Não foi resultado aprovado. Removidos somente
container/volume desta tarefa. Bind mount local recusado pelo Docker/macOS;
repetição aprovada usou tmpfs descartável de 1 GiB e foi limpa ao terminar.
Não foram removidos caches, imagens ou volumes de outros projetos.

**Artefatos e publicação:** candidata com **825 blobs iguais ao commit**, ZIP
SHA-256 edb6538c07e21dd3dee332ae0305b448b966dd9295950b8cbc50b48a0fc7afef.
Imagem sha256:080f24c0b055a0f4d8e8271a6cdd7112b035309bc5824feeddc4b4157920951e:
base imutável 73 mais camada de onze arquivos Python do commit; Dockerfile,
dependências/lock e assets iguais à fonte 651368c. Configuração runtime e todas
as camadas anteriores preservadas; 651 hashes runtime iguais à candidata,
agregado 118830444f5b2da7fe2fe911cf8012de11389e0f7e63fb405c3d7cc4023807d8,
conferidos com rede/banco bloqueados. Primeiro bootstrap offline não definiu a
chave de build e foi recusado antes do Django; repetição com chave sintética
passou. Esta imagem empacotada sobre a base 73 é distinta das imagens construídas
integralmente no CI, sem alegar que seus digests sejam iguais.

Deploy rolling no app original, --ha=false/--update-only, reserva excluída.
Release 74 concluída; 651 arquivos/hash agregado conferidos **em web e worker**,
migrações dos dois aliases/Neon original conferidas. Máquinas originais/512 MB,
reserva parada e configuração preservadas. Worker registrou ready às 18:25:18
BRT; readiness dos dois domínios 200, banco/cache ok. Agente inválido recusado
401 nas rotas antiga/nova; workspace anônimo redireciona ao login. Fingerprints
e contagens de **doze conjuntos CONTAD** iguais antes/depois, incluindo arquivos,
movimentos, decisões e manifesto/agentes. Login real Grazi/CSRF aprovado,
Conciliação 200/empresa/campo de arquivo presentes, zero upload/decisão; sessão
encerrada. Contrato individual/módulos/perfil/credenciais e gates mantidos,
zero convite/fatura. Não houve extração de segredo ou credencial em logs/Git.

**Windows e limite real:** MSI **1.0.4**, SHA-256
331402999beb42dec54270d5ef7bee6421db58c21b86847a332140704d786c92,
mesma fonte/CI; 26 checks de instalação/reparo/DPAPI/HMAC/ACL/reinício/remoção
aprovados em Windows descartável, sem ODBC/pareamento real. Sem Authenticode.
Roteiros novos passaram no parser PowerShell 5.1, sem consulta ERP executada.
Cópia do inventário em Downloads/CICA-CONTAD-Inventario-e9311eb.ps1, SHA-256
7515657a6d4b43e0d0b86f6cb4259c437d223fc541f1776a7126482db88757a2;
pacote em Downloads/CICA-CONTAD-1.0.4-e9311eb. Operador ainda indisponível;
**PC continua 1.0.3, sem upgrade/inventário/coleta ampliada comprovados**.
Último heartbeat registrado: 20:31:25 UTC/17:31:25 BRT, anterior ao deploy;
não afirmar ciclo real posterior ou causa dessa ausência. Piloto conserva uma
empresa/conta, 163 movimentos/espelhos, um arquivo/163 movimentos normalizados,
zero JournalEntry/IndependentLedgerRecord/decisão/saída, sem alteração dos fatos.
A/I dos testes não é mapa homologado do ERP.

**Recuperação e aceite:** manifesto original do backup/53 objetos/tamanhos e
retenção de sete dias reconferidos; validade até 13/11/2026 14:29:44 UTC. Sem
nova consulta API Neon, cópia, restore, chave ou recurso. Restore V-322 permanece
histórico, não teste desta candidata nem RPO recorrente aprovado. Retorno:
imagem 73 original, conservando migrações aditivas/dados. Guia de treinamento
[preparado](docs/pt-BR/contad-conciliacao.md), **não executado/aceito**.
Contas/referências, Razão/títulos/baixas reais, IA Q-08/Q-09, Q-46/Q-47,
200 eventos/revisão humana/precisão e demais métricas D-73 continuam abertos.
Próximo insumo necessário é o inventário real no PC. Projeto não concluído.

Evidências privadas: `.tmp/contad-finalization-2026-11-06/`, incluindo CI,
artefatos, snapshot antes/depois, pós-deploy, acesso HTTPS, recursos e delivery-final.
Trabalhos locais anteriores foram preservados fora dos commits desta execução.

## V-328 — Recuperação de cobertura publicada na release 75 (07/11/2026)

Continuidade D-323/PC-19. **Fonte c8b0c50**, CI
[42355490505](https://github.com/Mewstacks/CicaContabil/actions/runs/42355490505)
aprovado e **release Fly 75** publicada/verificada. Corrigido scan que podia
permanecer no cursor inconsistente se a contagem retornasse ao valor original.
Agora a recusa por cobertura/contagem abandona somente a leitura aberta, na
mesma transação; páginas/cadastros anteriores são preservados e a próxima
abertura reinicia do zero. Requisição atrasada não abandona progresso alheio;
recibo concluído continua íntegro/repetível. Código e horário do erro ficam
persistidos sem texto/dados de origem, pela migração aditiva intelligence.0034.

**Diagnóstico:** portfolio_sync_status consulta apenas escritório/agentes
selecionados, heartbeat/idade, estado, contagens, erros e histórico limitado
(1–100 scans por agente, no máximo cem agentes ou seleção explícita). Indica
quantos scans antigos foram omitidos. Sem credencial, DSN, nomes/documentos ou
valores financeiros; testes inspecionam inclusive a projeção SQL. PostgreSQL
usa transação própria REPEATABLE READ/READ ONLY. Chamador já em transação é
recusado antes da consulta, sem alterar sua capacidade de escrita. Comando
executado em produção somente leitura: agentes nos estados anteriores, manifesto
piloto, **zero scans reais**. Isso não prova recuperação de carga real no PC.

**Testes:** foco PostgreSQL **62 aprovados, zero skips**, incluindo retorno da
contagem original, preservação dos registros e corrida entre conclusão e página
inconsistente. Primeira rodada: quatro falhas no diagnóstico por tentativa de
mudar isolamento dentro da transação dos testes; corrigidos contrato/guarda e
cenário transacional, sem mascarar a falha. Regressão local final PostgreSQL 17
em tmpfs descartável: **1.801 testes/163 subtestes aprovados, um skip**, 357,02 s.
Skip de Playwright Python opcional. CI exato: SQLite 1.778/163, 24 skips;
PostgreSQL **1.800/163, dois skips**, 415,26 s (Playwright Python/OCR português
indisponíveis). .NET Linux 51/um skip Windows; Windows 52/zero skips e pacote
aprovados; três builds Docker aprovados. Ruff global, MyPy dos dois módulos,
Django e ausência de migrações faltantes aprovados. Sem alteração de UI/agente
ou novo teste visual alegado. Container temporário desta rodada removido;
recursos/caches/volumes de outros projetos preservados.

**Artefato:** 828 blobs iguais ao commit, ZIP SHA-256
e33c3475e599dda6cad9bfc7e0d99b580857de91955f44da15b9d8016b4eeba6.
Imagem sha256:61e035af2a18ff57b122cd1b1f5b13c7b5dee79f70a7bd8b87d16f581ed5af80,
base imutável 74 e camada de quatro arquivos Python. Dockerfile, dependências,
assets e agente sem mudanças. Configuração runtime/camadas anteriores iguais;
653 hashes iguais à candidata, agregado
041267a56203a500405389bceebb053f04d44c17952e084124d59f73ac7300c7,
conferidos offline com rede/banco bloqueados e comando de diagnóstico presente.
Imagem empacotada sobre a base anterior é distinta das três builds de CI;
não alegar igualdade dos digests. Pacote MSI 1.0.4 anterior continua compatível,
sem novo upgrade ou substituição dos arquivos entregues ao operador.

**Publicação e operação:** rolling/--ha=false/--update-only e reserva excluída.
Configuração salva mudou somente deploy.strategy de canary para rolling, como
resultado da publicação 74 já registrada; ambiente/serviços/recursos iguais.
Release 75 complete, 653 hashes conferidos em web/worker, hub.0079/intelligence.0034
nos dois aliases Neon originais, worker ready e readiness 200/banco/cache ok
nos dois domínios. Agente inválido 401 nas rotas antiga/nova, login HTTPS/CSRF
Grazi/Conciliação 200 e campo de arquivo conferidos, zero upload/decisão, sessão
encerrada. Máquinas originais/512 MB e reserva parada preservadas. Comparação
final: **doze conjuntos CONTAD com contagens/hashes iguais antes/depois**,
incluindo arquivos, movimentos, decisões e manifesto/agentes.

Na verificação final, duas tentativas SSH falharam antes da leitura (consulta
de organizações recusada e depois timeout do túnel). Identidade/listagem da
organização continuaram válidas. Concluída a mesma leitura pela API autenticada
Fly Machines exec, sem credencial nova ou mudança de acesso/infraestrutura;
resultados guardados separadamente. Não repetir deploy por falha de observação.
Leitura inicial do backup também excedeu a janela; processo remoto foi conferido
como ausente antes da repetição, que passou com timeouts limitados e quatro
leituras paralelas. Manifesto/53 objetos/tamanhos/retenção original conferidos,
validade até 13/11/2026 14:29:44 UTC; nenhum backup, chave, recurso ou restore novo.
Retorno: imagem original 74, mantendo intelligence.0034 aditiva e todos os dados.

**Limite do objetivo:** manifesto real continua piloto, zero scans da carteira,
163 eventos preservados, nenhum Razão/título novo obtido. Último relato do
operador segue indisponível; resultado do inventário ainda não foi recebido.
Sem upgrade no PC, SQL ERP, IA paga ou egressão novos. Q-28/Q-46/Q-47,
Q-08/Q-09, D-73, recuperação recorrente, treinamento e aceite permanecem abertos.
Fonte e publicação da correção estão concluídas; projeto CONTAD completo não.
Evidências privadas em `.tmp/contad-recovery-2026-11-07/`.

## V-329 — Plano Windows Server e substituição oficial local (09/11/2026)

D-324/PC-19, etapas 03/09/12. Responsável solicitou adaptar o plano anexado,
instalar novamente em outro computador Windows Server, torná-lo o oficial e
iniciar desenvolvimento. Depois informou AnyDesk já disponibilizado e pediu
conferir se o Server provavelmente antigo suporta a proposta .NET 10.

**Entrega documental:** atualizado o prompt canônico existente, sem segundo
plano de execução: estado V-328/release 75, instalação nova antes de ampliar
carteira, candidato sem coleta, corte explícito/revogação, retorno sem reativar
segredo revogado, preservação de dados e gates. Criado procedimento técnico
`docs/contad-agente-oficial-windows-server.md`. Original/cópias anteriores
preservados privadamente; três cópias atualizadas em Downloads, idênticas ao
canônico e 0600. Histórico financeiro desde 01/09/2026 permanece decidido.

**Implementação local:** migração aditiva intelligence.0035 acrescenta vínculo
de substituição, estado pending e oficial único por escritório, obrigatório
ativo. Emissão exige anterior ativo do mesmo escritório, manifesto validado
idêntico e ausência de outro código válido/candidato pendente. Novo arquivo
de entrega 0600/O_EXCL; código não vai ao stdout nem sobrescreve arquivo/symlink.
Pareamento staged-v1 gera UUID/segredo próprios e candidato que só autentica
heartbeat/configuração; cliente antigo não consome código de substituição.

Worker 1.0.5 respeita collection_enabled=false antes de qualquer processador,
grava awaiting_activation e continua heartbeat; preserva compatibilidade com
backend anterior. Ativação administrativa exige IDs distintos do mesmo
escritório, predecessor ativo vinculado, mesmo manifesto/revisão e heartbeat
dos últimos cinco minutos. Transação revoga anterior e ativa novo/oficial com
auditoria; repetição idêntica é idempotente e falha na auditoria reverte ambos.
Revogação limpa flag oficial. Dados/scans anteriores permanecem; candidato
reinicia scan próprio, sem duplicar identidades cadastrais/financeiras.
Diagnóstico somente leitura agora inclui oficial e predecessor, sem segredos.

**Concorrência:** ingestões piloto e carteira travam somente a linha do agente;
corte/emissão/revogação serializam pelo escritório com FOR NO KEY UPDATE,
compatível com as verificações de FK. Requisição em andamento termina antes do
corte, depois o anterior é recusado. Testes exercitam simultaneidade de emissão,
ativação repetida e corte durante ingestão de extrato **e carteira**, preservando
scan concluído e iniciando outro no novo agente. Não é prova de operação real.

**Verificações finais:** regressão integral PostgreSQL 17 descartável em tmpfs:
**1.837 testes/163 subtestes aprovados, um skip**, 357,06 s. Skip de Playwright
Python opcional, não executado como QA visual. Testes abrangem isolamento,
manifesto/fingerprint, heartbeat ausente/antigo/futuro, cliente incompatível,
segredo diferente, rollback, restrições do banco, código privado e replay.
Foco final SQLite: **30 aprovados/seis skips**, 16,31 s; os seis casos de
concorrência foram executados no PostgreSQL integral. Não somar repetições à
amostra. Ruff global, MyPy de seis módulos, Django check e migrações sem pendências
aprovados. Container temporário desta rodada removido; demais projetos intactos.

.NET no Mac: **59 aprovados/um skip Windows**; alvo net8.0 com RollForward
LatestMajor, execução no runtime 10.0.11/SDK 10.0.400 instalado. Não é execução
no runtime Windows ou validação de .NET 10 no Server. Serviço, configurador e
ponte win-x64/x86 compilados Release, zero erros/avisos. Fonte/workflows
preparam versão **1.0.5**; MSI novo/instalação/reparo/DPAPI/ACL/ODBC reais e CI
da candidata ainda não foram executados. Pacote 1.0.4 anterior não ganha o
protocolo staged-v1 por esta alteração dos fontes. Sem mudança de layout/fluxo
de tela; não foi alegada revisão visual do configurador ou do site.

**Tentativas anteriores:** primeira rodada SQLite teve duas falhas por nome
incorreto da rota no teste, 26 aprovados/quatro skips. Primeiro foco PostgreSQL
teve três falhas/135 aprovados/um skip: duas da mesma rota e um deadlock real
na troca por trava excessiva do escritório. Corrigidos nome, escopo das travas
e FOR NO KEY UPDATE. Foco intermediário: 138 aprovados/um skip, 246,26 s,
anterior à inclusão do cenário de corrida da carteira e demais casos finais;
não somar essa repetição à regressão final. Primeira chamada MyPy não encontrou
config sem PYTHONPATH=src; chamada final com contexto correto passou.

**Compatibilidade/acesso:** AnyDesk encontrado aberto no Mac. Obter janela por
nome, bundle ID e caminho completo retornou timeout **-10005**, sem binding
utilizável ou observação do Server. Solicitado somente texto do winver; edição,
versão, arquitetura e condições locais ainda desconhecidas. Não invalidar o
acesso disponibilizado pelo responsável nem atribuir causa ao Server.
Política Microsoft consultada confirma fim do .NET 8 em 10/11/2026; matriz
.NET 10 inclui Server 2016/2019/2022/2025 x64 e 2012/R2 sob ESU. Essa consulta
não confirma o sistema real. D-289 preservada; nenhuma migração de alvo ou
instalação inferida da resposta humana de verificar a compatibilidade.

Sem commit/push, CI remoto, deploy, código real de pareamento emitido, ação no
Server, revogação/promoção real, SQL ERP ou IA paga. Última publicação provada
continua V-328/release 75; não foi reconferida live nesta entrega. Piloto e
credenciais/dados reais não alterados. Q-28/Q-46/Q-47, IA, D-73, recuperação,
treinamento e aceite permanecem. Evidências privadas:
`.tmp/contad-official-agent-2026-11-09/` (logs/XML/TRX, hashes e preservação).
Snapshot prévio reconstruído em pasta isolada a partir de HEAD+diff confirmou
conteúdo anterior preservado nos dez arquivos já modificados; dezenove arquivos
de fonte/workflow/testes possuem SHA-256 no manifesto privado. Nenhum arquivo
foi colocado no índice. A comparação preexistente e etapa 00 seguem preservadas.

## V-330 — Roteiro do operador no Windows Server (10/11/2026)

Continuidade D-324/Q-28, etapas 03/12: responsável pediu passo a passo para
instalar/testar no Server. Acrescentado ao procedimento técnico existente o
roteiro do operador: inventário somente leitura, instalação/configuração
preexistentes, DSN de sistema x64, gate de pacote/backend, MSI sem reinício,
campos do configurador, teste ODBC interativo, pareamento candidato, reinício
somente do serviço, estados/diagnóstico seguros e verificação do corte.

Conferidos diretamente Package.wxs, AgentConfig.cs, Worker.cs, configurador,
LocalOdbcConnection.cs, diagnosticar.ps1 e instalação documentada: serviço
CicaAgent/Auto/LocalSystem, pastas reais em Program Files/ProgramData, arquivo
protegido agent.config (corrigida referência imprecisa anterior agent-config.bin),
campos/botões e distinção de ODBC interativo versus leitura sob LocalSystem.
Estado awaiting_activation não executa processadores ERP e não prova essa leitura.

Pacote em Downloads/CICA-CONTAD-1.0.4-e9311eb continua identificado 1.0.4 pelo
release.json. Manifesto genérico em agent-windows/artifacts ainda indica 1.0.0;
nenhum deles foi apresentado como MSI 1.0.5. HEAD local permanece b65dfe7,
implementação da substituição não publicada. Guia permite preparação agora,
sem instruir pareamento oficial em release 75 ou com pacote incompatível.

Reconsultadas documentação Microsoft de .NET/PowerShell e política de suporte;
.NET 8 tem fim de suporte em 10/11/2026. Isso não identifica o Windows real nem
aprova outro alvo. Versão/edição do Server ainda não recebidas. Roteiro entregue
é documental: comandos Windows não foram executados nesta rodada, sem inspeção
AnyDesk, teste PowerShell/ODBC no cliente, instalação, emissão de código,
ativação/revogação, CI, deploy, custos ou chamadas de IA. Não foi repetida a
regressão de aplicação por esta edição documental; V-329 mantém seus limites.
Conferência de referências/fontes e git diff --check realizados.

## V-331 — Identificação do Windows Server por imagem (10/11/2026)

Continuidade Q-28/D-324. Captura winver recebida do responsável mostra Windows
Server **2022 Standard**, versão **21H2**, compilação **20348.5761**. É evidência
visual fornecida pelo operador, não execução de comando ou controle AnyDesk.
Matriz Microsoft .NET 10 reconsultada: Windows Server 2022 x64 está incluído.
Compatibilidade da versão do SO não comprova pacote/ODBC/agente ou autorização
de trocar o alvo .NET 8 de D-289. Imagem preservada privadamente em
`.tmp/contad-server-identification-2026-11-10/winver.png`.

Atualizados estado corrente, guia, Q-28 e checklists sem concluir arquitetura
do processo, privilégios, driver/DSN, instalação ou corte. Próximos comandos
guiados verificam PowerShell x64, serviço CicaAgent e presença de agent.config,
sem ler o conteúdo protegido. Sem execução Windows, alteração de código/runtime,
novos testes de aplicação, pacote/CI/publicação ou pareamento nesta rodada.
Conferência documental e git diff --check; gates operacionais preservados.

## V-332 — PowerShell x64 e catálogo DSN observados (10/11/2026)

Segunda captura fornecida pelo operador no Server: título Administrador no
PowerShell, Is64BitProcess=True, consulta de serviço sem listagem visível e
Test-Path da configuração False. Resultado completo de OSArchitecture e
PSVersion está encoberto pela janela ODBC: não transcrever valores não visíveis.
ODBC (64 bits), aba DSN de Sistema, mostra Contabil 32/SQL Anywhere 17,
Contabil 64/SQL Anywhere 16, e-Robo 64/SQL Anywhere 16, e-Robo 17 64/SQL Anywhere 17.
Selecionada a linha Contabil 32, cujo painel informa que só pode ser configurada
no administrador de 32 bits. CICA_CONTAD não está listado na captura.

Identificação de servidor/banco dos DSNs e conexão ainda não verificadas.
Roteiro seguinte é inspeção somente leitura da configuração Contabil 64,
sem mudar DSNs originais, ler senha ou presumir equivalência das conexões.
Sem executar teste ODBC, instalar agente, parear ou alterar runtime/backend.
Imagem preservada privadamente em
`.tmp/contad-server-identification-2026-11-10/powershell-odbc.png`.
Registros/checklists atualizados; conferência documental/git diff --check.

## V-333 — Destino da conexão Contabil recebido (10/11/2026)

Captura fornecida no percurso de Contabil 64/SQL Anywhere 16 mostra Login:
Authentication Database, usuário/senha vazios, ação de conexão a banco já em
execução em outro computador, Host/Port vazios, servidor SrvContabil e banco
Contabil. Não há senha visível; isso não é inspeção de campos no registro nem
prova de ausência de senha em todo DSN. Network/Advanced e teste autenticado
não foram observados. Imagem privada em
`.tmp/contad-server-identification-2026-11-10/contabil64-login.png`.

Recebidos os identificadores, próxima orientação prepara DSN dedicado
CICA_CONTAD de sistema x64 com driver SQL Anywhere 16 e esses parâmetros,
sem modificar o original, inventar host/porta ou salvar credencial. Criação e
conexão continuam pendentes de execução/resultado humano. Sem ação remota,
instalação, pareamento, coleta, runtime/deploy ou teste de aplicação novo.
Registros/guia/checklists atualizados; git diff --check como conferência documental.

## V-334 — Teste ODBC recusado por login integrado (10/11/2026)

Operador informou erro ao testar conexão. Captura mostra exatamente:
Connection failed: Login mode 'Integrated' not permitted by login_mode setting.
A imagem contém apenas a mensagem, sem identificar DSN/driver ou os campos
Login usados nesse teste. Não comprova senha errada, driver incompatível,
parâmetro persistido, DSN dedicado criado ou leitura de dados. Evidência privada:
`.tmp/contad-server-identification-2026-11-10/odbc-integrated-rejected.png`.

Reconsultada documentação SAP SQL Anywhere: Authentication Database usa
usuário/senha; Test Connection exige ambos na aba Login. Orientação confere
Database no DSN dedicado e usa EXTERNO/senha somente no Windows durante o teste,
limpando campos antes de salvar. Não instruída mudança de login_mode no banco,
credencial ou DSN original. Reteste segue pendente, sem resultado inferido.
Sem execução remota, instalação, pareamento, alteração de código/runtime/deploy
ou teste de aplicação novo; registro/guia/checklist e git diff --check documentais.

## V-335 — Sucesso ODBC informado pelo operador (10/11/2026)

Responsável respondeu “sucesso” ao reteste orientado após recusa de Integrated.
Evidência é relato humano de Test Connection, sem nova imagem ou execução da
ferramenta. Resolve o resultado interativo de autenticação dessa rodada;
não comprova o conteúdo persistido do DSN, ausência de campos de senha,
conexão LocalSystem, agente instalado, sincronização ou aceite do projeto.

Orientação seguinte limpa User ID/Password antes de salvar CICA_CONTAD,
preservando Authentication Database e servidor/banco já recebidos. Não declarar
limpeza/salvamento concluídos antes da confirmação. Mantidos MSI 1.0.5/CI/backend
não entregues e alvo .NET 8 conforme D-289. Sem acesso remoto, leitura de senha,
SQL/dados novos, alteração de código/runtime/deploy ou teste de aplicação novo.
Registros/checklists/guia e git diff --check atualizados; não repetir ODBC por
mera atualização documental. Falha V-334 permanece histórica com seu contexto.

## V-336 — Salvamento do DSN confirmado pelo operador (10/11/2026)

Responsável respondeu “foi” à instrução de limpar User ID/Password e salvar
CICA_CONTAD após Test Connection bem-sucedido. Registrar limpeza/salvamento
informados, mantendo Authentication Database. Não houve leitura do registro,
coleta de senha, ação remota, instalação ou teste sob LocalSystem. Não repetir
preparação por falta de atualização documental. Demais gates de D-324/Q-28
continuam abertos.

## V-337 — Migração local do agente para .NET 10 LTS (10/11/2026)

D-325 registra aprovação humana antes da mudança, revisando D-289 para novas
compilações. Serviço, configurador e ponte usam net10.0-windows; contratos e
testes net10.0. CI prepara SDK 10.0.x. Pacotes Microsoft WindowsServices, Odbc
e ProtectedData atualizados para **10.0.15**, estável no feed oficial NuGet
consultado nesta data; runtime autocontido fixado na mesma versão. Versão
candidata do produto preservada em 1.0.5, x64 para serviço/configurador e x86
para ponte. Carregamento PKCS#12 adaptado para X509CertificateLoader mantendo
MachineKeySet/EphemeralKeySet e validação HTTPS normal.

Verificação local macOS, SDK 10.0.400/runtime de testes 10.0.11:

- `dotnet test ... -c Release`: **59 aprovados, zero falhas, três skips Windows**.
  Dois novos testes verificam chave privada utilizável/HTTPS e rejeição de PFX
  inválido; o terceiro cobre substituição de arquivo bloqueado. Os três exigem
  execução no Windows CI. Tentativa inicial dos testes novos no Mac expôs
  PlatformNotSupportedException para EphemeralKeySet; classificados como Windows
  sem enfraquecer as flags de produção. Logs dessa tentativa preservados.
- `dotnet publish -c Release` dos três executáveis: sucesso, sem avisos ou erros.
  Conferidos PE x64/x64/x86 e runtimeconfig net10.0/includedFrameworks 10.0.15;
  configurador inclui também WindowsDesktop 10.0.15. Ponte em arquivo único,
  runtimeconfig conferido na saída intermediária da mesma publicação.
- Inventários transitivos e auditoria `dotnet list ... package --vulnerable
  --include-transitive --format json` dos três projetos: sucesso, nenhum pacote
  vulnerável apontado pelo NuGet nesta consulta. Não é garantia de ausência de
  vulnerabilidades futuras ou não catalogadas.

Evidências em `.tmp/contad-net10-2026-11-10/`: TRX/logs, publicações locais,
inventários, consulta de versões, verification.json e manifesto SHA-256 das
fontes. Testes Python V-329 não repetidos: esta alteração não modifica backend
ou migrações. Plano, continuidade, prompt/cópias, checklists e execução atualizados.

Compatibilidade Server 2022 x64 reconsultada na [matriz Microsoft](https://github.com/dotnet/core/blob/main/release-notes/10.0/supported-os.md).
O pacote autocontido dispensa instalar SDK/runtime na cliente. **Não foram
gerados MSI novo, CI remoto, assinatura, release, deploy, instalação, pareamento
ou corte real.** Não homologados ODBC/DPAPI/serviço no Server; três testes
Windows continuam pendentes. Última publicação comprovada continua release 75.

## V-338 — MSI .NET 10 validado no Windows e preservado (10/11/2026)

D-326 autorizou branch técnica e CI Windows sem deploy em produção. Criada
`codex/contad-official-agent-net10` em worktree isolada, excluindo os trabalhos
locais anteriores D-316/D-317/etapa 00/comparação Pandolfo. Os 26 arquivos de
código/workflows/testes conferem com o manifesto SHA-256 da fonte local.

Primeiro CI 42862054949/fonte 67d5f82 aprovou 62 testes e 26 checks, mas apontou
NU1510 para ProtectedData explícito no configurador WinForms. Referência
redundante removida; DPAPI fornecido pelo WindowsDesktop, dependência do serviço
preservada. Publicação local e auditoria do configurador novamente aprovadas.
O artefato inicial fica apenas como evidência intermediária, não como entrega final.

**Fonte final do pacote: 53b834b12318ed5177e4d736929ab58f2c31559a.**
[CI Windows aprovado — 42863201809](https://github.com/Mewstacks/CicaContabil/actions/runs/42863201809),
runner Windows Server 2022 (NT 10.0.20348.0), repositório público/runner padrão:

- **62 testes .NET aprovados, zero falhas/skips**, incluindo os três pendentes
  no Mac (chave privada/HTTPS, PFX inválido e substituição de arquivo bloqueado).
- MSI **1.0.5**, runtime autocontido **10.0.15**, x64/x64/x86. **26 checks**
  instalados aprovados: instalação, serviço Automatic/LocalSystem, arquiteturas,
  ACL SYSTEM/Administradores, GUI sem crash, ponte executável, diagnóstico,
  DPAPI sob LocalSystem, HMAC sem certificado, reparo preservando configuração,
  reinício/recuperação e remoção. Usados somente dados sintéticos/loopback.
- Artefatos ZIP baixados pelo conector GitHub e digests SHA-256 conferidos com a
  API. MSI, release.json, checksum e installer-test.json concordam no SHA-256:
  `f89127453589a5721dd1dd392144b3beed17eebef0e0a33a023bbf7f6283882f`.
  Tamanho do MSI: **68.110.164 bytes**. Fonte/run do relatório conferidos.
- NU1510 eliminado no CI final. Permanecem aviso preexistente WiX ICE61 por
  AllowSameVersionUpgrades e avisos de execução Node 20/24 das actions fixadas.
  Não foram suprimidos ou tratados como falha de instalação. MSI **NotSigned**,
  sem assinatura de editor; nenhuma contratação de certificado.

Evidências locais: `.tmp/contad-net10-2026-11-10/ci-42863201809/`, logs, TRX,
JSON dos artefatos e windows-final-verification.json. Artefatos GitHub expiram
em 11/11; cópia de entrega preservada em Downloads/CICA-CONTAD-Agente-1.0.5-NET10-2026-11-10,
com MSI, checksum, manifesto, inventário, relatório e roteiro. ZIP correspondente
preparado para transferência manual, sem credenciais ou scripts de remoção do CI.

**Limites:** sem merge em main, release pública, deploy/backend, instalação na
cliente, pareamento, ODBC real, corte ou agente oficial efetivo. Backend release
75 continua a última publicação comprovada e não aceita staged-v1. Aguardar
backend compatível e código novo antes de instalar/parear no Server. CI do
instalador não homologa Q-28/Q-46/Q-47, carteira completa, D-73, rede real,
recuperação, treinamento ou aceite. Regressão backend V-329 não repetida:
código Python/migrações idênticos, sem alterações nesta migração de runtime.

## V-339 — Backend liberado e código privado do Server emitido (10/11/2026)

D-327 autoriza os processos para o responsável instalar/executar o novo agente.
Fonte **03ed5b0bae49706a02f8f9c1d3225acddd6b4bc6**, [CI completo aprovado
42865006431](https://github.com/Mewstacks/CicaContabil/actions/runs/42865006431):
SQLite **1.808 testes/163 subtestes**, 30 skips; PostgreSQL **1.836/163**, dois
skips (Playwright Python/OCR português indisponíveis); .NET Linux 59/três skips
Windows, Windows 62/zero skips; três imagens, Ruff, Django e migrations check
aprovados. Código de aplicação/agente idêntico ao validado anteriormente; novos
commits de autorização/documentação não alteram o MSI entregue em V-338.

Preflight encontrou release **76** externa, posterior à evidência 75. Runtime
sem protocolo de substituição, intelligence.0034 nos dois aliases; 653 arquivos
rastreados iguais à 75 após normalizar CRLF e cinco egg-info gerados. Configuração
76 usa um worker Gunicorn, exportação efetiva false e prévia sem escritórios
habilitados; esses estados foram preservados. Não restaurada prévia por inferência.
Imagem/configuração 76 preservadas como base e retorno. Backup original/53
objetos/tamanhos/retencão de sete dias reconferidos, válido até 13/11; sem nova
cópia, chave, recurso ou restore. Doze fingerprints CONTAD registrados antes.

Publicada **release 77**, imagem imutável
`registry.fly.io/cica-contabil@sha256:25f5b23d85cb160a221b36b120bd3f0275a668c906c6f76149840af04451ea7b`,
base 76 mais oito arquivos Python alterados/aditivos. Configuração e camadas da
imagem-base iguais, 661 hashes brutos conferidos offline sem rede/banco, agregado
`8a35f1f16afa622996c22c7877a265a07eea4c650f21936bfc5fd18c5358c504`.
Essa imagem empacotada é distinta da build Docker de CI; não confundir digests.
Primeiro ensaio offline usou módulo build sem chave sintética; corrigido somente
o ambiente de teste para config.settings.test, sem chave/flag de produção.

Release command aplicou intelligence.0035 aditiva. Pós-deploy: 661 hashes em
web/worker, comandos de preparação/ativação disponíveis, migrations em default
/knowledge nos endpoints Neon originais, ciclo Celery ready após a release,
readiness 200/banco/cache nos dois domínios e agentes inválidos recusados 401.
Doze conjuntos CONTAD com contagens/hashes iguais antes/depois, manifesto piloto,
163 eventos, usuários/contrato e agente anterior ativo preservados. Machines
originais/512 MB e reserva parada preservadas; somente deploy.strategy passou
canary → rolling, com --ha=false/--update-only e reserva excluída. Retorno de
aplicação na imagem 76 conservando schema aditivo. Leituras de inspeção ajustadas
para campo existente e JSON multilinha dos logs; não houve novo deploy por isso.

Emitido **um código de substituição de uso único**, validade até **10/11/2026
15:48:07, horário de Brasília**. Arquivo privado 0600 em
Downloads/CICA-CONTAD-Codigo-Servidor-2026-11-10.txt, fora de Git/ZIP público;
conteúdo não exibido em chat/log. Cópia temporária remota removida após gravação
local durável. Conferidos código ainda não usado, referência ao anterior ativo
e manifesto idêntico; emissão não cria candidato nem revoga/promove agente.

MSI 1.0.5 de V-338 mantém SHA-256 f89127453589a5721dd1dd392144b3beed17eebef0e0a33a023bbf7f6283882f,
sem assinatura de editor. Pasta/ZIP/roteiro e prompt/cópias atualizados para
backend pronto. Pode instalar/configurar como candidato no Server 2022 com
CICA_CONTAD/SQL Anywhere 16 x64 e credencial EXTERNO somente no Windows.
Esperado após pareamento/reinício: Running/Auto/LocalSystem e awaiting_activation.

**Limites:** sem instalação ou comando remoto no Windows nesta entrega,
pareamento/candidato, ODBC sob LocalSystem, corte ou coleta nova. ODBC interativo
continua relato V-335/V-336. Aguardam provas reais; não deduzir ODBC sob SYSTEM
ou agente oficial de heartbeat/awaiting_activation. Carteira completa/fontes,
Q-46/Q-47, D-73, recuperação recorrente, treinamento e aceite permanecem abertos.
Evidências privadas em `.tmp/contad-server-release-2026-11-10/`.

## V-340 — Configurador do Server confirma conexão; backend foi substituído (10/11/2026)

Captura fornecida pelo responsável mostra configurador no servidor **SVAPL02**,
HTTPS correto, Domínio Local/DSN CICA_CONTAD, SQL Anywhere 16 x64, autenticação
do DSN desmarcada, EXTERNO, senha mascarada e pasta opcional vazia. Mensagem
“Conexão confirmada. O Domínio está pronto para sincronizar.” Código vazio.
Comprova teste ODBC interativo do configurador, sem provar versão instalada,
serviço/LocalSystem, pareamento, candidato ou coleta. Não repetir o teste ou
pedir senha. Captura privada em .tmp/contad-server-release-2026-11-10/configurator-connection-confirmed.png.

Às 15:59 (Brasília), código V-339 já expirado às 15:48:07. Consulta de renovação
falhou antes de obter o estado porque o ORM atual não possui is_official.
Reconciliado estado real: releases 78/79 publicadas após 77, atual 79/imagem
3e0c3e1c4a0af56599afe6241ef15d241b0fe8866b533b1be32354ecea11a284, sem recurso
do agente; uso do código anterior ainda não reconfirmado. Nenhum novo código,
pareamento, corte ou SQL de alteração foi executado nesta inspeção.

Main avançou de b65dfe7 para 77e0ca7 com worker web único, navegação e recuperação
NFS-e. Sem sobreposição dos arquivos de aplicação com o agente, mas colisões
D-324/V-329 nos registros. Perguntado conforme AGENTS.md; responsável aprovou
consolidar/integrar em D-329. V-339 permanece prova histórica da release 77;
não tratar backend 79 como portador do protocolo ou o código vencido como válido.
Próximo gate: fonte consolidada/CI/main/publicação, depois código privado novo.

## V-341 — Diagnóstico do 502 por OOM e redução para um worker (10/11/2026)

Escopo de D-328 (antigo D-324 da main).

- **Sintoma:** `GET /entrar/` respondia 200, mas o envio da senha devolvia 502. `fly status` mostrava
  a máquina `started` e o check `/api/v1/health/live/` passando, porque quem morria era o worker
  dentro da máquina, não a máquina; ela não reinicia desde 07/11.
- **Causa observada nos logs:** três `Out of memory: Killed process ... (gunicorn)` entre 17:13:53 e
  17:14:44 UTC, com `anon-rss` de 216.696, 215.832 e 219.852 kB. Cada morte coincide com
  `error.message="could not complete HTTP request to instance ... connection closed before message
  completed"` no proxy. Máquina web: `shared-cpu-1x`, 512 MB, `--workers 2`.
- **Mudança:** `--workers 2` para `--workers 1` no `fly.toml`. Nenhum código de aplicação alterado.

Limites: a verificação pós-publicação observa ausência de OOM e o login real. Não houve teste de
carga, então o efeito de um worker só sob concorrência real não está medido. O consumo de ~216 MB
por worker não foi investigado nem reduzido.

Registro renumerado na consolidação D-329; evidência histórica anteriormente
V-329 na main. O V-329 do agente (09/11) permanece canônico.

## V-342 — Integração na main, backend consolidado e novo código do Server (10/11/2026)

Escopo D-329/D-327, PC-19/etapas 03/09/12. [PR 3](https://github.com/Mewstacks/CicaContabil/pull/3) integrado:
fonte 5c20766, árvore bb600d07b630b86b1fa6fbfe47e7b1a93579b15c, main 272f97797c9183fa14491882d8962663c8fb0a3b com árvore idêntica.
Colisões consolidadas: agente D-324/V-329; contenção de memória D-328/V-341.
Correções da main 77e0ca7 preservadas, incluindo worker web único, menu e NFS-e.
Trabalhos locais anteriores D-316/D-317/etapa 00/Pandolfo excluídos dos commits.
Oito arquivos locais da main só foram atualizados após conferir que não tinham
edições próprias; snapshots guardados. HEAD da cópia original não foi resetado.

CI exato [42882756516](https://github.com/Mewstacks/CicaContabil/actions/runs/42882756516) aprovado: SQLite 1813 testes,
163 subtestes e 30 skips; PostgreSQL
1841/163, 2 skips.
.NET Linux 59 aprovados/três exclusivos de Windows pulados; Windows 62/zero
skips e ciclo do instalador aprovados. Lint, Django, migrações e três builds
aprovados. Skips opcionais Playwright Python/OCR PT não provam homologação visual
ou OCR real. MSI entregue continua o 1.0.5 de V-338, SHA-256
f89127453589a5721dd1dd392144b3beed17eebef0e0a33a023bbf7f6283882f;
sem alteração de binário/assinatura e sem exigir reinstalação.

Base real era release 79, sem protocolo, apesar da migração 0035 já aplicada.
Comparação normalizada encontrou somente cinco arquivos alterados e três novos
do agente; preservados os demais arquivos e cinco metadados egg-info. Imagem
registry.fly.io/cica-contabil@sha256:1d6d6ee6081e92c7ebc1aa65836fb74fab22a00d8821faa36c79f73c272260a2 construída sobre a 79, configuração/camadas-base idênticas mais
uma camada. Conferência offline dos 661 hashes, rede/banco bloqueados, comandos
e estado pending aprovados. Hash bruto agregado
7658466a786e24b17226d6431f34580095c6c493a83e2121a2602a52fd59ed28.

Release **80** publicada nas duas Machines ativas: hashes, comandos,
0035/default/knowledge, endpoints HTTPS/readiness/banco/cache, recusa de chamadas
de agente sem assinatura e worker ready conferidos. Doze fingerprints CONTAD
antes/depois idênticos; mesmo manifesto/piloto, anterior ativo, zero candidato/
oficial/scan. Configuração preservada, exceto estratégia registrada como rolling;
512 MB/CPU compartilhada, IDs/região e reserva parada mantidos. Exportação false
e prévia desabilitada preservadas. Retorno é imagem imutável da release 79;
esquema aditivo não é removido. Manifesto/53 objetos/retencão original conferidos,
snapshot válido até 13/11/2026 14:29:44 UTC; sem novo recurso, restore ou custo.

Código antigo 14cccaae expirado sem uso, sem candidato. Novo código de uso único
para SVAPL02 emitido por 60 minutos, validade **17:30:50 de 10/11 (Brasília)**,
arquivo local 0600 separado do ZIP/Git; temporário remoto removido após entrega
local persistida. Recorte herdado e anterior preservados; código nunca impresso.
Roteiros, pacote, prompt/cópias e checklists atualizados. Evidências privadas em
.tmp/contad-server-integration-2026-11-10/.

**Limites:** captura V-340 prova apenas ODBC interativo. Não houve controle ou
comando no Windows, confirmação de versão/serviço instalado, pareamento,
ODBC sob LocalSystem, corte oficial ou nova coleta. Próximo passo no Server é
colar o código e Conectar à CICA, reiniciar só CicaAgent e devolver estados
seguros; completar provas faltantes antes do corte. Q-28/Q-46/Q-47, D-73,
carteira/fontes completas, recuperação recorrente, treinamento e aceite abertos.

## V-343 — Candidato real no Server e serviço aguardando ativação (10/11/2026)

Captura humana de SVAPL02 mostra Restart-Service CicaAgent, serviço Running /
Auto / LocalSystem e awaiting_activation. Configurador mostra recorte herdado
(empresa 212, conta do piloto, setembro/2026), CICA_CONTAD/SQL Anywhere 16 x64.
Código temporário aparece na imagem; é tratado como segredo, não transcrito ou
copiado ao Git. Senha mascarada. Saída combinada do PowerShell ocultou colunas
de versão/horário/detail: não afirmar esses valores a partir da captura.

Consulta backend somente leitura, 19:46:28 UTC: código 1017ef5d consumido às
19:44:58 UTC, candidato 0086bcf7-45a3-486b-b3ff-8b8f5e456385 pending, não oficial,
referencia anterior 3cf6e4fb-c268-49e8-8905-be3afe7fa2e6 ativo; heartbeat recente.
Fingerprint diferente e mesmo manifesto/revisão ad932af6, hash 1fbaf927. Release
80 continua corrente. Não emitir outro código, revogar ou parear novamente.
awaiting_activation comprova configuração DPAPI/registro de DSN e comunicação
HMAC no serviço após reinício, mas não abertura ODBC ou leitura ERP sob SYSTEM.
D-330 prepara prova separada; corte, nova coleta e demais gates pendentes.
Evidências privadas .tmp/contad-server-pairing-2026-11-10/; imagem somente 0600.

## V-344 — Ferramenta de prova LocalSystem validada e entregue (10/11/2026)

Escopo D-330/D-324/D-327. Fonte 05fc97d85ca18370939a3ed421d958199e81611f,
[CI Windows 42890385615](https://github.com/Mewstacks/CicaContabil/actions/runs/42890385615) aprovado e [PR 4](https://github.com/Mewstacks/CicaContabil/pull/4)
integrado na main ff501af349d34961d1ccae320d4a940a52a90601 com árvore idêntica. Windows Server
2022/10.0.20348 e PowerShell 5.1.20348.5773. Prova real de tarefa SYSTEM/x64,
DPAPI/ACL privada, recusa IM002 para DSN inexistente, nenhuma leitura ERP,
nenhuma credencial no relatório/saída, tarefa/arquivos removidos, relatório
Administradores/SYSTEM e recusa de Worker sob conta interativa. Primeiro CI
42889888743 falhou na asserção com nome sintético longo; nome encurtado em
274f2fd/CI 42890124669 aprovado. Versão final 05fc97d preserva UTF-8 com BOM
para Windows PowerShell e inclui SID explícito; novamente aprovada. O job MSI
foi intencionalmente pulado: sem alteração do binário, runtime ou backend.

Script separado testar-odbc-system.ps1, SHA-256 64dcc5ef12098edd1755ca54eb2d55851411b54d2d5ff0abf6c83e844296c9fb,
com consulta mínima idêntica ao configurador. A senha será digitada somente
no Windows, protegida para transporte em arquivo temporário privado; não lê
agent.config/DSN/registro de senha. Relatório não contém valores da consulta.
Também lê apenas os campos seguros do status e ACL, para comprovar versão,
horário e permissões sem expor configuração. Pasta/roteiro/hash em Downloads/
CICA-CONTAD-Teste-LocalSystem-2026-11-10; pacote MSI anterior atualizado com a
ferramenta e instruções, sem alterar CicaAgent.msi. Prompt/cópias/checklists
atualizados para próximo passo único: executar o teste e enviar relatório.

Inspeção backend confirma candidato com label SVAPL02/pending e heartbeat,
mesmo manifesto, anterior ativo. Onze conjuntos de dados anteriores idênticos
às provas V-342; agentes agora três, pela inclusão do candidato. Código já
consumido; não emitir outro ou parear novamente. Release 80 permanece corrente.
**Limites:** CI não dispõe do ERP da cliente. ODBC/ACL/versão reais aguardam
relatório do SVAPL02; sem corte, nova coleta, reinstalação, deploy ou custo novo.
Q-28 e demais fontes/carteira/Q-46/Q-47/D-73/recuperação/treinamento/aceite abertos.
Evidências privadas .tmp/contad-server-pairing-2026-11-10/.

## V-345 — ODBC real sob SYSTEM e pré-requisitos Windows comprovados (10/11/2026)

Relatório humano b0401de2d22a4cf6b2eae21c9e5695e8 recebido sem credenciais:
SYSTEM/SID S-1-5-18, processo x64, conexão ODBC true, SELECT mínimo true/com linha,
sem erro/SQLState/código nativo. agent_config_acl_private=true, versão 1.0.5,
awaiting_activation observado 20:03:21 UTC; teste 20:04:19 UTC. Tarefa e arquivos
temporários removidos. Relatório seguro no Windows em ProgramData/CICA/OdbcChecks.
Soma-se à captura V-343: Running/Auto/LocalSystem após reinício, configuração
DPAPI reaberta pelo serviço, HMAC e recorte confirmado no backend. Não repetir
ODBC/senha/pareamento/instalação; prova prévia Windows satisfeita. Nenhuma senha
foi enviada ou lida do registro/configuração. Evidência privada em
.tmp/contad-server-cutover-2026-11-10/windows-system-proof.json.

Conferência live do candidato/manifesto/heartbeat e corte são os próximos passos
D-324/D-330; este registro ainda não afirma oficial/ready/recepção ou aceite.
Carteira/fontes completas e demais gates contratuais permanecem pendentes.

## V-346 — SVAPL02 oficial, primeiro ciclo e dados preservados (10/11/2026)

Escopo D-324/D-327/D-330. V-345 satisfez ODBC/SELECT mínimo real sob SYSTEM/x64,
ACL privada, versão 1.0.5 e limpeza; V-343 comprovou serviço Auto/Running/
LocalSystem após reinício e configuração DPAPI/HMAC. Preflight live confirmou
novo fingerprint, mesmo manifesto e heartbeat recente. Comando transacional
activate_official_agent executado em 10/11 às **17:08:35 Brasília**
(20:08:35 UTC): SVAPL02/0086bcf7-45a3-486b-b3ff-8b8f5e456385 active/is_official=true;
CONTAD16/3cf6e4fb-c268-49e8-8905-be3afe7fa2e6 revoked/is_official=false. Único oficial,
zero pending e uma auditoria intelligence.agent.official_replaced,
ID f1e04ce5-7df8-4349-ae84-062d9a7f5482. Mesma revisão ad932af6/manifesto piloto.
Sem copiar segredo/cursor/configuração entre máquinas ou apagar histórico.

Prova HTTPS com assinaturas válidas mantidas apenas na memória do backend:
antes, anterior 200/coleta true e candidato 200/coleta false; depois, anterior
401 e novo 200/coleta true. Nenhuma chave exportada, heartbeat ou ingestão
artificiais enviados. Auditorias reais depois do corte: companies_synced às
20:09:22 UTC (zero criação/uma atualização), bank_entries_synced às 20:09:25
(zero criação/alteração/ignorados, sem truncamento); conector healthy.
Relato humano do Windows confirmou **ready/1.0.5 às 20:09:33 UTC**, detalhe
“Último ciclo concluído com sucesso.” Prova recepção/ciclo; não inferir o número
total de linhas relidas dos 163 registros existentes, pois auditoria de delta
não registra input_count. Somente o novo oficial está autorizado a coletar.

Onze conjuntos anteriores (exceto estado de agentes) idênticos em contagens/
hashes antes/depois do primeiro ciclo: uma empresa/conta, 163 movimentos,
163 DominioBankEntry e 163 AccountingEntry de vínculo bancário. Zero exportação,
JournalEntry/IndependentLedgerRecord; arquivos, vínculo de usuário e demais dados
preservados. Agentes continuam três, único ativo é SVAPL02 e nenhum scan real
de carteira. Readiness/banco/cache nos dois domínios, imagens/512 MB/Machines/
reserva parada e configuração preservados. MSI e release 80 mantidos, sem deploy.

**Teste complementar pós-corte ainda pendente:** solicitado reiniciar somente
CicaAgent e conferir outro ready/Auto/LocalSystem. Primeira colagem chegou como
linha única sem separadores; PowerShell falhou no binding antes do reinício.
Versão em linha única com separadores enviada; JSON de retorno ainda não
recebido. Não declarar esse segundo reinício comprovado. AnyDesk consultado
novamente via ferramenta nativa: timeout -10005, sem observar/controlar Server;
isso não nega o acesso humano. Serviço antigo não foi fisicamente parado nesta
sessão, mas sua credencial já é recusada. Não reativá-la automaticamente.

Relatório de entrega, pacote, prompt/cópias e checklists atualizados para oficial
ativo/primeiro ready, distinguindo o segundo teste ainda aberto. Evidências
privadas .tmp/contad-server-cutover-2026-11-10/. Instalação e corte operacionais;
Q-28 permanece para inventário/fontes/carteira, além desse retorno do teste.
Carteira/fontes completas, IA, Q-46/Q-47, D-73, recuperação recorrente, treinamento
e aceite não homologados por essa operação.

## V-347 — Retomada do SVAPL02 após reinício pós-corte (10/11/2026)

Fecha somente a prova complementar pendente em V-346, sob D-324/D-330.
Operador executou no PowerShell administrador a linha com separadores:
Restart-Service CicaAgent; espera de 90 segundos; consulta do serviço/status.
Resultado real: **Running / Auto / LocalSystem**, **ready / 1.0.5**,
observed_at_utc **2026-11-10T20:23:26.9265491+00:00**, detalhe
“Último ciclo concluído com sucesso.” O Ctrl+C ocorreu no prompt depois dos
dois JSONs; não representa falha do teste nem parada do serviço. A primeira
colagem sem separadores registrada em V-346 havia falhado antes da ação;
o retorno atual comprova a execução corrigida, sem reescrever a prova anterior.

Conferência live somente leitura em transações REPEATABLE READ/READ ONLY:
companies_synced às 20:24:27/20:25:40 UTC (zero criação, uma atualização),
bank_entries_synced às 20:24:29/20:25:42 UTC (zero criação/alteração/ignorados,
sem truncamento), conector healthy/sem erro e heartbeat SVAPL02 20:26:50 UTC.
Único active/is_official, anterior revoked/is_official=false com last_seen
inalterado em 20:07:40 UTC, uma única auditoria de corte e mesmo manifesto.
Recepção real após reinício confirmada; não inferir quantidade de linhas
relidas a partir de auditorias de delta ou dos 163 movimentos já existentes.

Onze conjuntos de dados não relacionados ao estado dos agentes continuam com
contagens/hashes idênticos ao preflight: uma empresa/conta, 163 movimentos,
163 DominioBankEntry/AccountingEntry de vínculo bancário, arquivo/vínculo de
usuário preservados; zero JournalEntry/IndependentLedgerRecord/decisão/exportação.
Três agentes mantidos como histórico, zero scan de carteira. Release 80,
configuração completa, imagens, recursos e estados das três Machines idênticos,
incluindo reserva parada. Sem escrita ERP, novo deploy, reinstalação ou reboot
do servidor; apenas o serviço CICA foi reiniciado pelo operador.

Instalação/troca oficial/teste pós-corte concluídos. Relatório, entrega.json,
pacotes/ZIPs, prompt/cópias, plano e checklists atualizados; MSI/script preservados.
Evidências privadas .tmp/contad-server-cutover-2026-11-10/windows-post-restart.json,
operational-after-restart.json, official-state-after-restart.json,
integrity-after-restart.json e final-verification.json. Sem senhas/chaves/códigos
em Git ou pacote público. Serviço do computador anterior não foi fisicamente
parado nesta sessão; sua credencial permanece revogada no backend.

**Limites:** prova cobre reinício do serviço e o piloto autorizado, sem ampliar
carteira/fontes. Q-28 segue para inventário/fontes/carteira; Q-46/Q-47, Razão/títulos,
D-73 (inclusive falha de rede/restauração), IA, exportação ERP, treinamento e
aceite contratual permanecem nas etapas próprias. Não é homologação integral.

## V-348 — Preparação da carteira e diagnóstico do inventário (10/11/2026)

Escopo D-331/D-323, PC-19/03/09/12. Agente oficial SVAPL02 permanece validado
em V-347; nenhuma reinstalação, pareamento, SQL financeiro ou ampliação real.
Implementada prévia sem escrita e aplicação administrativa explícita piloto →
companies, vinculada a inventário SHA-256, escritório/agente, versão compatível,
mapa de situações inteiramente revisado e dono/administrador ativo. CAS da revisão
anterior, travas organização/agente na ordem do corte, recusa de substituição
pendente e replay pela auditoria original. Preserva UUID/segredo/dados e informa
que a coleta financeira do piloto é pausada ao trocar para companies. Não
configura carteira de fontes financeiras ainda não implementadas/homologadas.

Verificações locais: 112 testes focados PostgreSQL aprovados em 22,23 s,
incluindo replay, revogação e mudança durante ingestão; regressão integral
PostgreSQL 17 descartável em tmpfs: **1.881 testes/163 subtestes aprovados**,
um skip opcional de Playwright Python, 264,23 s. Não é QA visual. SQLite inicial
32 aprovados/dois skips de lock (executados depois no PostgreSQL); não somar
repetições à amostra. Ruff global, MyPy dos dois módulos, Django/migrações e
diff check aprovados. Sem mudanças de UI/fluxo que exijam nova homologação visual.

Windows 2022/PowerShell 5.1: CI 42897681292/f52aaab aprovou cinco cenários do
inventário: sucesso de metadados sintéticos, ausência de coluna, limite de objetos,
limite de situações e DSN realmente inexistente; ACL privada e nenhuma senha
na saída/JSON. O primeiro harness 42896886618 mascarava exit do filho; corrigido.
42897306850 passou as asserções, mas herdou exit 1 esperado do último filho;
final 42897681292 corrigiu o exit do harness. Esses testes não possuem ERP real.
Bytes CRLF/BOM executados diferem do checkout LF somente em final de linha,
SHA de entrega 8fe116a26d6563ac2b2d096386f8ac9c3a4c4752e999e80e936f41e607e8627c.

**Tentativa real Q-28:** operador executou no SVAPL02 e retornou
MethodInvocationException, sem etapa/código e sem inventário concluído. Não
atribuir causa a timeout/DSN/driver/credencial. Documentação/código Microsoft
confirmaram que OdbcConnection.ConnectionTimeout permite escrita; hipótese de
propriedade somente leitura foi descartada sem alterar esse comportamento.
AnyDesk novamente falhou -10005, sem observar/controlar a sessão Windows.

Acrescentado diagnóstico seguro: etapa constante/índice, tipos de exceção,
SQLStates validados e códigos nativos; não imprime Message/ToString, senha ou
connection string. CI **42898977773**, fonte **32070be**, novamente aprovou
os cinco cenários e conferiu etapa/IM002 real. SHA dos bytes Windows entregues:
**dc5e9b19989763541162762ba045afa0de1a747f03678ca4744f8600b3260506**.
Pasta/ZIP Downloads/CICA-CONTAD-Inventario-Diagnostico-2026-11-10. Nova execução
pontual solicitada ao operador; retorno do diagnóstico/inventário ainda pendente.

Candidata sobre imagem release 80: somente dois módulos Python adicionados;
663 hashes completos conferidos offline, rede/banco bloqueados, comando presente,
configuração/camadas anteriores iguais. CI integral/integração/publicação desta
fonte ainda em andamento; não descrever candidata como backend publicado.
Backup original/53 objetos/tamanhos/retenção até 13/11 reconferidos, sem novo
recurso/restore/chave. Agente oficial, manifesto piloto e dados reais preservados.

Evidências privadas .tmp/contad-portfolio-finalization-2026-11-10/. PR 5 anexada.
**Limites:** sem inventário, revisão de situações ou scan real da carteira. Contas/
referências/Razão/títulos, Q-28/Q-46/Q-47, IA Q-08/Q-09, D-73, recuperação,
treinamento e aceite continuam necessários; nenhuma homologação presumida.

Complemento V-348/D-331: diagnóstico real recebido em reading_tables/índice 0,
MethodInvocationException → ArgumentException, sem SQLState/nativo, conexão já
aberta. Código Microsoft confirma limite de três restrições em Tables/Views;
a sonda usava quatro. Corrigida chamada e incluída Views separadamente, mesmos
filtros/limites. CI 42900001117/d39acd0 passou os cinco cenários e conferiu os
limites no XML do provedor System.Data real do Windows, detectando a chamada
antiga. Pasta Downloads/CICA-CONTAD-Inventario-Corrigido-2026-11-10 entregue;
aguarda retorno real corrigido. A falha do script não é falha de ODBC/DSN do
agente oficial. Nenhuma nova fonte ou semântica habilitada.

## V-349 — Inventário concluído no SVAPL02 e backend publicado (11/11/2026)

Continuidade D-331/PC-19/03/09/12. Operador executou a sonda corrigida após
reading_tables/ArgumentException: **601 objetos, 5.674 colunas, 502 empresas**.
Arquivo Windows em Downloads/CICA-CONTAD-Inventario-a40d4f3235ee4b99b6d0397b7a129490/
inventario.json, SHA informado **4b7be104b2225b19cc922528d8d1cb65734f02d0b9f463f9e9d0d965652e3c69**.
Isso comprova a execução/conclusão relatada; conteúdo JSON ainda não recebido,
hash não recalculado no Mac, situações/chaves/relações/semântica não revisadas.
Nenhum mapa A/I sintético foi aplicado. Não pedir outra execução sem motivo.

Fonte final d39acd0c586b1bbfeb459ea7476445070e07f9f3, CI 42900012334 aprovado:
SQLite **1.849/163 subtestes, 33 skips**; PostgreSQL **1.880/163, dois skips**;
.NET Linux **59/três skips Windows**, Windows **62/zero**; inventário/diagnóstico,
instalação/contratos e três builds Docker aprovados. Esses testes reutilizam a
mesma amostra; não somar às 1.881/163 locais de V-348. Correção Tables/Views=3,
Columns=4 e regressão da chamada antiga conferidas no System.Data real do runner
Windows 2022 em CI 42900001117. Script Windows final SHA-256
6e9006593bdfc315a97a940a0b52e73998406d2f19928b054b6fcc160aa2bc1b.

PR 5 integrado em main **5cfa462b10b66180aed4bb98e29565eda9323a4c**, árvore
idêntica à fonte validada. Imagem sobre release 80, somente dois módulos Python
novos; 663 hashes completos conferidos offline e no runtime web/worker,
agregado a0cf56d8f2a1c2ef51c089c547d200f0e82c5139cd11acff5983edbe40a7439a.
Configuração/camadas/dependências anteriores iguais. Imagem imutável
registry.fly.io/cica-contabil@sha256:a3b99dd712904e2be318b0ccf30a0746a2b8511adbd9a92c1b492fe9012f35a0.

Publicada/verificada **release 81**, sem migração ou mudança do MSI. Configuração
Fly completa igual, mesmos três IDs/512 MB/região, dois processos ativos e reserva
parada/imagem anterior preservada. Doze contagens/hashes anteriores idênticos,
incluindo agentes e piloto/163 movimentos; banco default/knowledge originais e
migrações preservados. Backend confirma único oficial SVAPL02, anterior revogado,
mesmo manifesto piloto, zero scan de carteira e conector healthy. Ciclo real
pós-publicação: companies 15:49:58 UTC, banco 15:50:00 UTC (zero criação/alteração
bancária/ignorados, sem truncamento), heartbeat 15:49:57 UTC. Não inferir total
relido dessas auditorias de delta. Nenhum lote ou heartbeat artificial enviado.

Readiness 200/banco/cache ok nos dois domínios; autenticação inválida recusada
401 nas rotas de empresas/extratos; worker pronto após release, zero erro runtime
no recorte observado. Prévia/exportação permanecem desabilitadas. Backup original/
53 objetos/tamanhos/retenção até 13/11 reconferidos, sem novo recurso/restore/chave.
Primeiro push da imagem falhou por autenticação expirada do registro; autenticação
existente renovada pelo flyctl e push concluído, sem criar outro repositório/app.
Um download de logs GitHub retornou 502; repetido com sucesso, sem falha do CI.

Comando configure_agent_portfolio disponível com prévia sem escrita por padrão;
não foi aplicado no ambiente real. Publicação não é carga da carteira nem
homologação de contas/Razão/títulos. Ainda necessário receber JSON/revisar
situações/fontes, aplicar escopo compatível e conferir cobertura real; Q-46/Q-47,
IA Q-08/Q-09, D-73, recuperação, treinamento e aceite seguem abertos.
Plano/contrato de integração/prompt/cópias/checklists e entrega atualizados.
MSI 1.0.5 oficial e scripts SYSTEM preservados; não instalar artefato novo de
mesma versão produzido pelo CI desta rodada. Evidências privadas
.tmp/contad-portfolio-finalization-2026-11-10/, inclusive resumo humano sem JSON bruto.

## V-350 — Inventário recebido, seleção de ativas e atualização 1.0.6 (11/11/2026)

Continuidade D-332/PC-19/03/09/12. JSON original recebido: 2.851.946 bytes,
SHA-256 **4b7be104b2225b19cc922528d8d1cb65734f02d0b9f463f9e9d0d965652e3c69**
recalculado; 601 objetos (596 tabelas/cinco views), 5.674 colunas e 502 empresas.
Situações A=146/I=346/M=10. Estrutura, limites, tipos e colunas GEEMPRE conferidos;
isto não confirma relações, PK/FK ou semântica financeira. Original privado,
sem nomes/documentos/valores em Git. CTCONTAS, CTCONTACAIXA e relação bancária,
CTLANCTO/CTCLANCTO e CTCCUSTO são candidatos observados. CODI_EMP_PLANO exige
conferir plano próprio/compartilhado; objetos EF tributários não comprovam títulos.

Responsável pediu todas as ativas e não sabe conferir total A/M. Primeiro recorte
usa apenas A, seletor existente; M permanece não classificado/não selecionado.
Nenhum M foi gravado inativo. A revisão técnica é restrita a flags explícitas,
mapa A=true, referência D-332 e reviewer_id=null; auditoria não atribui aprovação
à Grazi. Outros mapas exigem revisão humana integral. Não afirmar carteira
completa enquanto M/semântica e cobertura real não forem resolvidos.

Implementação: dominio-portfolio-v2/scoped-v3/active_only, condição parametrizada
igual na contagem e paginação ODBC, seleção vinculada à revisão, rejeição de
linha fora do recorte antes do envio e na recepção. V1/piloto preservados;
configuração/heartbeat anteriores permitem transição, ingestão exige v3.
Validação estrutural independente de revisão humana; novo comando somente leitura
inspect_agent_inventory. Sem migração, dependência, fonte financeira ou UI nova.

Fonte final **11147d4bdc040e2ed2d4b80ee2942f2516f758aa**, CI **43061206044**
aprovado: SQLite **1.861/163 subtestes, 33 skips**; PostgreSQL **1.892/163,
dois skips**; .NET Linux **64/três skips Windows**, Windows **67/zero**;
três builds Docker aprovados. Local PostgreSQL final **1.893/163, um skip
opcional**, 504,34 s, em execução isolada; focados 127 e seletor 51 reutilizam
casos e não se somam à regressão. Uma tentativa anterior sofreu remoção da base
de teste por outra suíte local concorrente; descartada como validação final,
conferida a causa e repetida integralmente sozinha. Contêiner temporário próprio
removido, sem tocar os demais. Ruff/MyPy/check/makemigrations e três builds .NET
aprovados; sem novas migrations.

CI Windows Server 2022 **43061211615** da fonte exata: **67 testes, 26 checks
MSI**, instalação/reparo/retomada/desinstalação e upgrade configurado real de
MSI baseline1.0.5 (fonte53b834b) para1.0.6 aprovados. Bytes DPAPI/ACL preservados,
SYSTEM reabriu configuração e retomou após reinício, sem rede/ERP no ensaio.
Primeira execução CI detectou caminho de executável incorreto no harness;
corrigido para Program Files/CICA Agent/Service. Comparação de frescor usa cast
DateTimeOffset, preservando precisão subsegundo após JSON. Resultados antigos
não foram usados para liberar MSI. Pacote final autocontido/.NET10.0.15,
MSI **14473e84bc4101a257e0a626078ab75963fccfc792094eb066e4218370df2588**,
NotSigned como o anterior. Script de cliente confere hash/manifesto/serviço,
bytes criptografados, versão e ciclo novo; não descriptografa nem refaz pareamento.
Entregue Downloads/CICA-CONTAD-Agente-1.0.6-2026-11-11.zip e solicitada execução
pontual. **Ainda sem prova de atualização real no SVAPL02.**

PR6 integrado em main **7a0277504696a999abab061feb32b70547563e23**, árvore igual
à fonte validada. Imagem sobre release81 com oito arquivos Python alterados/novos,
**664 hashes** completos iguais offline e em web/worker; agregado
**6a684baa54cd76e123512b78213182ba2fafa480ccfe84b8230dff9c3dfb7c16**.
Mesmas camadas/configuração/dependências da base. Imagem imutável
registry.fly.io/cica-contabil@sha256:01a1799e2d43d43cf2dceef08d97f507dea6613ca7bb8fbc49a24336ad35a27b.
**Release82** publicada/verificada, dois processos/512MB/mesmos IDs e reserva
parada/imagem anterior, configuração Fly integral igual, aliases Neon e migrations
originais. Doze contagens/hashes iguais, único oficial e anterior revogado,
mesmo piloto/163 movimentos e zero scan ampliado. Readiness/banco/cache200 nos
dois domínios, assinatura inválida401, worker pronto/sem erros no recorte pós-release.
Backup original/53 objetos/tamanhos/retenção até13/11 reconferidos, sem novo recurso.
Ciclo real após publicação: empresas16:57:31 UTC e banco16:57:33 UTC, conector
healthy. Auditoria bancária: zero criação/alteração/ignorados e sem truncamento;
não inferir total relido do delta. Nenhum heartbeat/lote artificial; nenhum
manifesto ampliado aplicado.

AnyDesk permitiu observar o desktop/Downloads do servidor; entrada remota não
funcionou de forma verificável e aviso de limite de licença foi respeitado.
Não houve leitura de credenciais, assinatura/subscrição ou consulta ERP confirmada.
A instrução pendente ao operador é executar somente a atualização e devolver JSON,
sem exigir que saiba decodificar A/M. Próximo passo: versão1.0.6 real e heartbeat,
prévia/--apply administrativo do seletor A e scan real confrontado com146 observadas,
sem antecipar sucesso. Depois relações/fontes, Q-46/Q-47, D-73 e aceite.
Evidências privadas em .tmp/contad-active-companies-2026-11-11/; plano, checklists,
execução, prompt/cópias e entrega atualizados; alterações locais anteriores preservadas.
