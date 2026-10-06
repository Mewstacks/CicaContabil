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
