## V-140 - Visao administrativa de distribuicao de atividades

Proprietario e administrador passaram a ver atribuicoes abertas por membro ativo, com atrasos
e impedimentos separados, e podem abrir a fila exata de cada pessoa ou as atividades sem
responsavel. A interface deixa claro que isso nao e metrica de produtividade. Validacao: 81
testes focados em 52,78 s, Ruff, MyPy, Django, migracoes e regressao integral com 863
aprovados, 2 ignorados e 11 subtestes em 79,33 s. Inspiracao: dashboards de recursos do
Karbon e navegacao de atribuicoes do Asana; Watermelon sem resultado pertinente. Web Interface
Guidelines sem violacao material. Playwright MCP indisponivel por `Transport closed`, sem
inspecao visual alegada.

## 28/09/2026 — proteção do adaptador Siescon (V-292)

- D-294 registrou a branch `codex/siescon-adapter` sobre `codex/lucrums`.
  O agente confere colunas do SQL antes de transmitir linhas e o backend exige
  o conector da origem. Usuários Siescon ficam fora de despacho até confirmar
  o campo de atividade, evitando marcar todos como ativos por suposição.
- Testes .NET, Python focados e regressão integral passaram; MyPy, Ruff,
  Django, migrações e builds Windows .NET 8 também. Ver números e ambiente em
  V-292. Nenhum script DDF, ODBC, ERP ou dado real foi acessado.
- Faltam layout de importação contábil, schema de contas/lançamentos e prova
  no Siescon autorizado. Exportação permanece bloqueada; etapa 04 aberta.

## 28/09/2026 — vínculo Domínio e margem sem honorário corrigidos (V-291)

- O código Domínio da carteira agora prevalece sobre documento coincidente de
  outro ERP, como D-282 já determinava. Ficha, carteira e gráfico não apresentam
  resultado ou margem como zero confirmado quando falta honorário.
- 973 testes Python passaram; Ruff, MyPy, Django, migrações e sintaxe do
  gráfico passaram. Cobertura global de 80,09% segue abaixo dos 85% exigidos.
- A cardinalidade escrita em D-282 diverge do modelo de dois perfis ERP;
  esclarecimento solicitado. Q-41 a Q-43 e homologação real seguem abertas.

## 28/09/2026 — MSI único construído no CI Windows (V-290)

- O PR em rascunho #1 executou o novo job Windows. A primeira tentativa expôs
  ICE38/ICE43/ICE57 no atalho; a chave HKCU corrigiu o componente. A execução
  36450694685 gerou `CicaAgent.msi` e validou versão e SHA-256 do manifesto.
- Construção não substitui instalação ou homologação com ERP real. O job geral
  ainda concluía builds Docker quando esta evidência foi registrada.

## 28/09/2026 — branch dedicada e correção da identidade do Lucrums (V-289)

- D-293 moveu o trabalho da etapa 14 para `codex/lucrums`, preservando a
  `main` como linha principal. A revisão do ProjetoARD encontrou o risco de
  matriz e filial com documento repetido; a CICA agora conserva os códigos e
  exige correspondência inequívoca para gêmeas de ERP e honorários.
- 971 testes Python, 36 testes de ingestão e 20 testes .NET passaram. Ruff,
  MyPy, Django e migrações passaram. Cobertura global de 80,09% ficou abaixo
  dos 85% exigidos.
- Faltam prova do MSI no CI Windows, decisões Q-41 a Q-43 e homologação real.

## V-139 - Prioridade operacional por prazo, bloqueio e fonte

A area de trabalho agora conta todas as atividades abertas no escopo permitido e mostra atraso,
hoje, proximos sete dias, impedidas e fonte indisponivel como dimensoes independentes. Cada
indicador abre a fila filtrada; a fila ganhou filtro de atualizacao da fonte e a tabela mostra
as quatro situacoes operacionais. Validacao: 80 testes focados em 53,80 s, Ruff, MyPy, Django,
migracoes e regressao integral com 862 aprovados, 2 ignorados e 11 subtestes em 81,47 s.
Inspiracao: filtros contextuais de prazo do Karbon e resumo agregado de folha do Xero;
Watermelon sem resultado pertinente. Web Interface Guidelines sem violacao material.
Playwright MCP indisponivel por `Transport closed`, sem inspecao visual alegada.

## V-138 - Tratamento de divergencia no mesmo contexto operacional

A comparacao de folha agora abre a fila filtrada pela empresa, competencia e area de folha;
o link nao encerra, reatribui ou presume causa da atividade. A fila ganhou filtro mensal
com URL preservada na paginacao e erro para competencia invalida. Validacao: 79 testes
focados em 57,78 s, Ruff, MyPy, Django, migracoes e regressao integral com 861 aprovados,
2 ignorados e 11 subtestes em 92,53 s. Inspiracao: filtros de prazo/trabalho do Karbon e
relatorios de folha filtraveis do Xero, adaptados ao CICA; Watermelon sem resultado
pertinente. Web Interface Guidelines sem violacao material. Playwright MCP indisponivel por
`Transport closed`, sem inspecao visual alegada.

## V-137 - Comparacao de fontes agregadas da folha

A ficha de empresa agora permite comparar duas fotografias de folha da mesma competencia,
com fonte, totais, metricas ausentes e diferencas acima da tolerancia. A implementacao
mantem dados agregados, nao calcula folha nem chama fonte externa; o botao sinaliza
`Comparando...` enquanto a pagina e recarregada e a tabela usa a composicao responsiva ja
existente na ficha. Validacao: 72 testes focados em 53,27 s, Ruff, MyPy, Django,
migracoes e regressao integral com 861 aprovados, 2 ignorados e 11 subtestes em 80,06 s.
Web Interface Guidelines: sem violacao material. Inspiracao: Xero Payroll Activity Summary
para totais agregados e reconciliacao, adaptada ao CICA; Watermelon sem resultado
pertinente. Playwright MCP indisponivel por `Transport closed`, sem inspecao visual alegada.

## V-136 - Exportacao do Copiloto pelo renderizador JavaScript

Removida a geracao de PDF/XLSX do Copiloto por ReportLab/OpenPyXL. A exportacao usa somente
o contrato Node/TypeScript, preserva fotografia, permissao, hash e auditoria. Ausencia de URL
interna ou segredo devolve indisponibilidade explicita, sem arquivo alternativo. Validacao: 21
testes Django em 51,84 s, 8 testes Node, Ruff, MyPy, Django, migracoes e regressao integral
com 860 aprovados, 2 ignorados e 11 subtestes em 82,24 s. Nenhum servico interno ou externo
foi configurado ou chamado; a homologacao publicada continua na etapa 12.

## V-135 - Editor visual versionado do mapa DRE

O mapa DRE agora e editavel por proprietario ou administrador: cada linha informa conta,
grupo e sinal, e salvar valida o conjunto inteiro antes de criar uma versao nova e imutavel.
A versao anterior continua consultavel, somente a nova fica ativa e a alteracao gera auditoria.
O formulario oferece erro em linha, foco no primeiro erro retornado e aviso de edicao nao
salva. Validacao: 70 testes focados em 55,95 s, Ruff, MyPy, Django, migracoes e regressao
integral com 860 aprovados, 2 ignorados e 11 subtestes em 82,86 s. Revisao Web Interface
Guidelines sem achado material. Playwright MCP indisponivel por `Transport closed`; nao houve
inspecao visual desktop/mobile nesta entrega.

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

## V-133 - Rota??o do segredo de relat?rios

O renderizador Node aceita o segredo ativo e o anterior durante uma janela controlada; Django envia apenas o ativo. README documenta a sequ?ncia de rota??o e remo??o. Valida??o: TypeScript, 8 testes Node, 6 testes Django, Ruff e MyPy aprovados; regress?o integral com 855 aprovados e 2 ignorados em 82,28 s. Celery continua pendente; nenhum segredo ou chamada real foi usado.

## V-132 - Produto NFS-e exclusivo

A assinatura explicitamente limitada a NFS-e abre a central do m?dulo, remove a fila/modelos da navega??o e nega suas URLs diretas. Empresas, certificados, equipe e configura??o inicial permanecem porque s?o necess?rios ao pr?prio NFS-e. Valida??o: Ruff, MyPy e 80 testes de workspace/navega??o aprovados; regress?o integral com 854 aprovados e 2 ignorados em 79,79 s. Watermelon n?o encontrou refer?ncia equivalente; a dire??o usou navega??o por fun??o e superf?cies m?nimas. Playwright MCP indispon?vel, portanto a inspe??o visual desktop/mobile continua pendente.

## V-131 - Regra manual NFS-e sem efeito curinga

O cadastro manual de acumulador agora preserva cat?logo e hist?rico sem classificar NFS-e por aus?ncia de crit?rio. A classifica??o autom?tica s? ocorre com correspond?ncia expl?cita; a nota sem regra continua em revis?o humana. A prova cria o cadastro pela tela e confirma esse comportamento. Valida??o: Ruff, MyPy e 94 testes focados aprovados; regress?o integral com 852 aprovados e 2 ignorados em 76,03 s. Inspe??o visual pendente por indisponibilidade do Playwright MCP.

## V-130 - Historico completo de pacotes NFS-e

A carteira de pacotes NFS-e agora pagina acima de 100 registros, preservando a aba e exibindo navegacao por URL. A prova criou 101 pacotes e confirmou as duas paginas. Validacao focal: 69 testes, Ruff e MyPy.

## V-129 - Contrato tecnico NFS-e/Dominio para Q-39

Foi adicionado `docs/planejamento/nfse-dominio-import-contract.md`, com o material tecnico necessario, contrato do extrator allowlisted, requisitos do futuro exportador e roteiro de homologacao. O documento nao define layout nem consulta fontes; prepara o trabalho do desenvolvedor sem transferir backup, credencial ou dado de cliente.

## V-128 - Pacote NFS-e classificado como conferencia

A pesquisa oficial nao forneceu layout do backup nem contrato de XML/acumulador para a rotina DomÃ­nio. Por D-112/Q-39, o ZIP NFS-e agora e pacote de conferencia privado; a confirmacao de importacao esta bloqueada e nao ha alegacao de importacao. Validacao focal: 68 testes, Ruff e MyPy. Resta obter layout autorizado, amostra descartavel e retorno verificavel pela etapa 12.

## V-127 - Historico unico de acumuladores NFS-e

Implementado historico imutavel que unifica fotografia DomÃ­nio Web, cadastro manual e decisao humana, exibido por empresa com origem e instante e paginado. Validacao focal: 70 testes, Ruff, MyPy e migracoes limpas. Falta repetir a inspecao visual desktop/mobile quando o Playwright MCP estiver disponivel; nenhuma fonte real foi acessada.

## V-126 - NFS-e Dom?nio Web: catalogo, historico e pacote auditavel

Implementado localmente o catalogo de acumuladores extraido pelo agente controlado, inclusao de acumuladores pela tela, historico de uso por decisao humana e pacote ZIP privado de NFS-e com manifesto/hash. O pacote separa geracao, download e confirmacao humana de importacao; ausencia de arquivo privado e recuperavel sem avancar estado. Validacao focal: 68 testes focados e regressao integral com 851 aprovados e 2 ignorados; Ruff, MyPy e migracoes limpas. Resta repetir a validacao visual mobile e do download apos a interrupcao do transporte Playwright, alem da homologacao do layout e da rotina Dom?nio.

## 23/09/2026 - V-125 - Catalogo NFS-e do backup Dominio Web

- Criada evidencia imutavel de acumulador por empresa, fonte, lote e fotografia. O agente so pode enviar a capacidade allowlisted `accumulator_catalog`; a revisao NFS-e aceita esse catalogo apenas para a propria empresa.
- Uma fotografia concluida impede novo backup para a fonte. Arquivo e chave continuam removidos ao termino, preservando metadados e catalogo normalizado.
- A aba Acumuladores exibe esse historico por carteira, com paginaÃ§Ã£o e estado vazio explicito.
- Validacao: 65 testes focados, regressao integral anterior com 845 aprovados e 2 ignorados, Ruff, MyPy, checks Django e migracoes aprovados. Playwright validou desktop e 375 px sem overflow ou erros e encerrou o ambiente de QA.
- Limite: extrator real, layout da rotina automatica e retorno de importacao aguardam arquivo autorizado e homologacao DomÃ­nio.

## 23/09/2026 - V-124 - Versionamento do mapa DRE

- Adicionado tipo de importacao de mapa DRE: valida contas, grupos e sinais, bloqueia a organizacao e o conjunto anterior na transacao, cria uma versao e a torna ativa sem apagar linhas antigas.
- Validacao: quatro testes financeiros, Ruff e MyPy aprovados.
- O assistente passou a explicar o layout do mapa DRE junto aos layouts de saldos e caixa. A validacao visual em desktop e 375 px confirmou abertura por teclado, foco visivel, ausencia de overflow e console sem erros; a revisao pelas Web Interface Guidelines nao encontrou violacao material no trecho alterado.
- Regressao final: 845 testes Python aprovados e 2 ignorados; TypeScript, seis testes Node e auditoria de dependencias do servico de relatorios aprovados.
- Limite: configuracao atual por arquivo; editor visual de mapeamento permanece pendente.

## 23/09/2026 - V-123 - Importacao de saldos e caixa

- Acrescentados dois tipos de importacao CSV/XLSX no assistente: saldos para DRE e cenarios de caixa. A pagina explica o layout antes do envio.
- O importador valida o arquivo inteiro antes de gravar dados financeiros, agrupa saldos por fotografia e impede duplicacao por referencia; caixa exige saldo inicial e referencia de movimento, e bloqueia dupla deducao ou divergencia de saldo inicial.
- Validacao: 67 testes focados, Ruff, MyPy, checks Django e migracoes aprovados. Playwright desktop/celular validou o detalhamento de layout, sem overflow nem erros de console; navegador e QA encerrados.
- Limite: os layouts sao manuais documentados, sem alegar compatibilidade de Dom?nio/Siescon antes de contrato e homologacao.

## 23/09/2026 - V-122 - DRE e caixa na ficha da empresa

- A ficha unica ganhou bloco financeiro com fotografias DRE e cenarios de caixa, sem alegar consulta bancaria e sem criar DRE quando faltam dados ou mapa ativo.
- Adicionada rota POST de exportacao que reaplica escopo por empresa, exige renderizador Node, devolve PDF/XLSX com `no-store` e audita hashes sem valores.
- Validacao: 62 testes de telas Hub; regressao completa `uv run pytest` com 841 aprovados e 2 ignorados em 73,95 s; Playwright desktop e celular em servidor isolado. Controles com altura minima de 44 px, sem overflow em 375 px e sem erros de console ao abrir a ficha. Browser e servidor de QA encerrados.
- Pesquisa e direcao: ui-ux-pro-max, Watermelon (nenhum catalogo relevante verificado), Checkout.com e June no SaaSFrame; adotados tabelas de relatorio compactas, acoes contextuais e estados vazios sem copiar interfaces. Auditoria Web Interface Guidelines concluida sem achados materiais.
- Limite: renderer Node ainda precisa de configuracao interna para gerar arquivo real; sem ele a rota retorna 503 explicitamente e nao cai para bibliotecas Python.

## 23/09/2026 - V-121 - Contratos Node para DRE e caixa

- Implementado adaptador que traduz DRE e caixa persistidos para a fotografia restrita consumida pelo servico Node/TypeScript.
- A fotografia DRE preserva fonte, versao de mapeamento, valores decimais exatos e contas sem mapa; a de caixa deixa clara a visao selecionada e a ausencia de consulta bancaria automatica.
- Validacao: 17 testes focados, regressao completa com 839 aprovados e 2 ignorados em 73,11 s, `ruff`, `mypy`, verificacoes Django e os seis testes Node aprovados; o contrato TypeScript tambem foi validado diretamente com uma fotografia DRE representativa.
- Proximo: definir e implementar os pontos autorizados de consulta/exportacao, com isolamento por empresa e validacao integral de UX.

## 23/09/2026 - V-120 - Persistencia financeira para DRE e caixa

- Criados modelos e migracao aditiva para fotografias de saldos, linhas, versoes de mapeamento da DRE e cenarios/movimentos de caixa, isolados por escritorio e empresa.
- Criado servico financeiro idempotente para registrar saldos com proveniencia, auditar sem registrar valores, calcular DRE pelo mapeamento do escritorio e projetar caixa com as regras deterministicas ja validadas.
- Validacao: 16 testes focados aprovados; regressao completa `uv run pytest`: 838 aprovados, 2 ignorados em 72,46 s. `ruff`, `mypy`, `check` e conferencia de migracoes aprovados.
- Proximo: transformar estas fotografias em contratos do servico Node de relatorios e, depois, construir importacao e interface seguindo o fluxo obrigatorio de UX.

## 23/09/2026 â€” dependÃªncias XLSX sem vulnerabilidades conhecidas (V-119)

- O lockfile do renderizador fixa uuid 11.1.1 por `overrides`, mantendo a entrada
  CommonJS requerida pelo ExcelJS 4.4.0.
- `npm ls`, `npm audit --omit=dev`, TypeScript e seis testes Node passaram; a auditoria
  retornou zero vulnerabilidades. Celery e rotaÃ§Ã£o/revogaÃ§Ã£o do segredo continuam
  pendentes para produÃ§Ã£o.

## 23/09/2026 â€” exportaÃ§Ã£o confirmada por POST (V-118)

- PDF e XLSX deixaram de usar `GET`; os botÃµes agora enviam `POST` com CSRF e um
  `GET` devolve 405 sem criar fotografia, arquivo ou auditoria.
- Os 17 testes dirigidos de exportaÃ§Ã£o e canal interno passaram. A revisÃ£o aplicou
  UI/UX Pro Max, Watermelon, referÃªncia Asana e Web Interface Guidelines.
- Playwright usou conta nÃ£o-demo e resposta sintÃ©tica: desktop e 375 px sem overflow,
  foco visÃ­vel, botÃµes com pelo menos 44Ã—44 px e download PDF com fotografia/hash
  persistidos. Navegador e servidor isolado foram encerrados.

## 23/09/2026 â€” fotografia persistida de exportaÃ§Ã£o (V-117)

- PDF e XLSX do Copiloto agora preservam uma fotografia criptografada e imutÃ¡vel do
  contrato enviado ao renderizador, junto de hashes do insumo e do arquivo.
- O registro carrega autor, empresa, resposta, formato e versÃ£o; evento de auditoria
  armazena somente hashes e contagem de evidÃªncias.
- As 17 provas dirigidas de exportaÃ§Ã£o e cliente interno passaram, assim como Ruff,
  MyPy, Django e verificaÃ§Ã£o de migraÃ§Ãµes. Ainda faltam Celery, rotaÃ§Ã£o do segredo e
  atualizaÃ§Ã£o compatÃ­vel da cadeia ExcelJS para produÃ§Ã£o. A regressÃ£o integral fechou
  com **836 aprovados e 2 ignorados** em 70,38 s.

# Registro de execuÃ§Ã£o da meta operacional

## 23/09/2026 â€” base agregada de folha (V-116)

- Fotografias de folha agora registram totais por empresa, competÃªncia e fonte,
  preservando o carÃ¡ter informado, documental, ERP ou oficial sem guardar PII de
  trabalhador.
- O comparador recusa empresa/competÃªncia incompatÃ­vel e torna lacunas explÃ­citas;
  testes, migraÃ§Ã£o e verificaÃ§Ãµes estÃ¡ticas passaram.
- A ficha de empresa passou a exibir as fotografias. A prova em desktop e celular
  usou dados sintÃ©ticos, sem overflow ou erros de console; navegador e servidor foram
  encerrados.
- A regressÃ£o completa fechou com **834 aprovados e 2 ignorados** em 71,10 s.
- A entrada local de fotografia passou a ser idempotente e auditÃ¡vel sem incluir
  valores de folha na trilha de eventos.
- ImportaÃ§Ã£o, interface, vÃ­nculo com atividades e fontes homologadas continuam
  pendentes.

## 23/09/2026 â€” autenticaÃ§Ã£o local Django â†’ renderizador (V-115)

- Django e Node exigem segredo compartilhado configurado; URL sem segredo, hash ou
  MIME invÃ¡lido e resposta indisponÃ­vel sÃ£o recusados sem fallback silencioso.
- O caminho completo local gerou XLSX com segredo fictÃ­cio em loopback. ServiÃ§o e
  listener foram encerrados ao fim da validaÃ§Ã£o.
- Ainda faltam evidÃªncia persistida, execuÃ§Ã£o Celery, rotaÃ§Ã£o de segredo e a correÃ§Ã£o
  compatÃ­vel da cadeia do ExcelJS antes de produÃ§Ã£o.

## 23/09/2026 â€” renderizaÃ§Ã£o local PDF/XLSX em JavaScript (V-114)

- O componente Node/TypeScript passou a separar a API loopback do motor que valida
  fotografias e gera SVG, PDF e XLSX. Filtros, versÃ£o, atualizaÃ§Ã£o, pendÃªncias e hash
  acompanham o resultado; o navegador do PDF nÃ£o tem acesso a rede e o XLSX trata
  texto iniciado por fÃ³rmula como texto.
- TypeScript, cinco testes do serviÃ§o, quatro testes do cliente interno e 11 testes de
  exportaÃ§Ã£o do Copiloto passaram.
  O Django sÃ³ usa o novo motor quando a URL interna for configurada; se essa operaÃ§Ã£o
  falhar, responde 503 em vez de alternar silenciosamente entre geradores. PDF e XLSX fictÃ­cios foram gerados e
  inspecionados localmente usando navegador jÃ¡ instalado, sem download de binÃ¡rios ou
  qualquer chamada externa.
- AutenticaÃ§Ã£o entre serviÃ§os, auditoria persistida e fila Celery ainda sÃ£o
  obrigatÃ³rias antes de ativar a URL interna em produÃ§Ã£o. A dependÃªncia transitiva vulnerÃ¡vel de ExcelJS
  impede liberar PDF/XLSX para produÃ§Ã£o nesta etapa.
- A regressÃ£o local completa fechou com **830 aprovados e 2 ignorados** em 70,51 s.

## 23/09/2026 â€” ficha da empresa com central operacional e Triagem (V-113)

- A ficha Ãºnica passou a reunir atividades e anexos de Triagem por empresa, sem
  contornar a autorizaÃ§Ã£o do mÃ³dulo nem modificar o resultado de nenhum fluxo.
- Em celular, as novas tabelas passam a cartÃµes com rÃ³tulos e aÃ§Ã£o contextual;
  desktop preserva a tabela compacta para leitura comparativa.
- 59 testes dirigidos passaram; a inspeÃ§Ã£o Playwright local em desktop/celular nÃ£o
  encontrou overflow horizontal, perda de foco ou erro de console.

## 23/09/2026 â€” fundamentos de fechamento, comercial, caixa e DRE (V-112)

- A conclusÃ£o pode exigir processamento fechado; a agregaÃ§Ã£o do fechamento mantÃ©m
  bloqueio, reabertura e indisponibilidade como situaÃ§Ãµes distintas.
- Raiz de CNPJ vÃ¡lida passou a identificar capacidade comercial; membros ativos e
  raÃ­zes ativas alimentam somente os limites jÃ¡ configurados.
- Caixa e DRE ganharam motores determinÃ­sticos, com dupla retenÃ§Ã£o bloqueada e contas
  nÃ£o mapeadas explÃ­citas. O serviÃ§o de relatÃ³rio JS compilou e gerou SVG local.
- O assistente de configuraÃ§Ã£o ganhou diagnÃ³stico que deixa explÃ­cito o que opera sem
  ERP e o que ainda depende de fonte, equipe ou limites. A inspeÃ§Ã£o visual ocorreu
  em desktop e celular, com foco visÃ­vel, sem overflow e console limpo.
- A regressÃ£o integral fechou com **823 aprovados e 2 ignorados** em 69,25 s; a prova
  dirigida das views do espaÃ§o de trabalho fechou com **58 aprovados** em 43,58 s.
- Nenhuma integraÃ§Ã£o externa, cobranÃ§a ou geraÃ§Ã£o PDF/XLSX produtiva foi ativada.

## 23/09/2026 â€” observaÃ§Ãµes e reabertura por fonte (V-111)

- Leitura de fonte passou a manter sucesso, falha, referÃªncia, versÃ£o, momento e
  estados retornados sem registrar conteÃºdo bruto desnecessÃ¡rio.
- RetificaÃ§Ã£o ou reabertura devolve uma atividade concluÃ­da para pendente, preservando
  a conclusÃ£o na trilha. Indisponibilidade mantÃ©m o Ãºltimo processamento conhecido.
- A tela de detalhe mostra a origem e atualizaÃ§Ã£o. A prova foi local, com dados
  fictÃ­cios; nenhuma integraÃ§Ã£o real foi acionada.

## 23/09/2026 â€” modelos e geraÃ§Ã£o mensal da central (V-110)

- Modelos de atividade passaram a ter periodicidade, prazo legal e interno explÃ­citos,
  tipo de comprovaÃ§Ã£o e versÃ£o. A atribuiÃ§Ã£o Ã© por empresa e responsÃ¡vel padrÃ£o, sem
  inferir que todas as filiais usam a mesma regra.
- A geraÃ§Ã£o mensal Ã© idempotente e armazena a versÃ£o aplicada na ocorrÃªncia. Uma
  revisÃ£o nÃ£o muda competÃªncias anteriores nem ativa uma nova empresa por efeito
  colateral. A administraÃ§Ã£o pode pausar e retomar atribuiÃ§Ãµes, com auditoria.
- ValidaÃ§Ã£o local: fluxo administrativo completo em desktop e celular, foco e tema
  escuro; 814 testes aprovados, 2 ignorados. Nenhum ERP, Serpro, e-mail, IA, cobranÃ§a
  ou transmissÃ£o real foi acionado. Limites e prova detalhada estÃ£o em V-110.

## 23/09/2026 â€” base da central operacional (V-109)

- Foram adicionados, sem reaproveitar Jornadas, modelos de atividade, evidÃªncia e evento imutÃ¡vel; a conclusÃ£o valida evidÃªncia e aceitaÃ§Ã£o de obrigaÃ§Ã£o quando aplicÃ¡vel.
- A central lista a carteira autorizada, tem filtros por empresa/Ã¡rea/situaÃ§Ã£o e um detalhe que permite comprovar, impedir ou concluir com trilha auditÃ¡vel. O acesso Ã© novamente conferido na API de cada operaÃ§Ã£o.
- A prova local cobriu o fluxo completo em 1440 px e 375 px, teclado inicial, tema escuro e console sem erros. NÃ£o houve fonte externa, custo, transmissÃ£o, documento real ou homologaÃ§Ã£o; os limites completos estÃ£o em V-109.

## 21/09/2026 â€” demonstraÃ§Ã£o isolada da ConciliaÃ§Ã£o revisada no navegador (V-099)

- Uma base SQLite temporÃ¡ria, migrada e semeada exclusivamente com dados
  fictÃ­cios permitiu abrir `/demo/`, a VisÃ£o geral e a ConciliaÃ§Ã£o sem tocar o
  banco local de desenvolvimento. A sessÃ£o declarou ausÃªncia de consulta
  externa e cobranÃ§a.
- Em 1440 Ã— 1000 e 390 Ã— 844, a ConciliaÃ§Ã£o nÃ£o apresentou overflow horizontal
  ou erros/avisos de console. O modal de importaÃ§Ã£o expÃ´s empresa, conta,
  origem, perÃ­odo, lote e limites, sem enviar arquivo.
- Servidor e aba temporÃ¡rios foram encerrados; a base e os artefatos fictÃ­cios
  foram movidos para a Lixeira de forma recuperÃ¡vel. A evidÃªncia nÃ£o cobre todos
  os perfis, teclado/foco completo, upload real, integraÃ§Ãµes ou homologaÃ§Ã£o.

## 21/09/2026 â€” PDF corrompido recusado antes da conciliaÃ§Ã£o (V-098)

- A validaÃ§Ã£o passou a abrir PDF e a verificar o limite de 500 pÃ¡ginas antes de
  persistir a fonte. Arquivo malformado retorna mensagem clara sem criar lote ou
  processamento invÃ¡lido; o caminho de OCR local continua disponÃ­vel quando o
  parser opcional nÃ£o estÃ¡ instalado.
- Foram aprovados 42 testes focados (um skip de OCR), Ruff e MyPy do serviÃ§o; a
  suÃ­te integral fechou com 784 testes, trÃªs skips e 11 subtestes. NÃ£o houve
  OCR, arquivo real, ERP, integraÃ§Ã£o ou serviÃ§o externo.

## 21/09/2026 â€” XLSX corrompido recusado antes da conciliaÃ§Ã£o (V-097)

- A validaÃ§Ã£o de entrada passou a abrir XLSX antes de criar a fonte. Arquivo com
  extensÃ£o e assinatura compatÃ­veis, mas corrompido, Ã© rejeitado com mensagem
  clara, sem fonte, lote ou processamento persistido.
- A prÃ©via CSV passou a ler apenas as 51 linhas que exibe, sem materializar todo
  o conteÃºdo somente para cortar a amostra visual.
- Foram aprovados 41 testes focados (um skip de OCR), Ruff e MyPy do serviÃ§o; a
  suÃ­te integral fechou com 783 testes, trÃªs skips e 11 subtestes. NÃ£o houve
  arquivo real, OCR, ERP, integraÃ§Ã£o ou serviÃ§o externo.

## 21/09/2026 â€” cÃ³digo operacional de Jornadas removido (V-096)

- Em complemento Ã  V-095 e conforme D-43, formulÃ¡rios, views e template
  operacionais Ã³rfÃ£os de Jornadas foram removidos. Enum, modelos, tabelas e
  migraÃ§Ãµes histÃ³ricos permaneceram intactos; nÃ£o houve migraÃ§Ã£o destrutiva.
- A busca de referÃªncias confirmou que nÃ£o hÃ¡ rota, vÃ­nculo de navegaÃ§Ã£o,
  formulÃ¡rio, view ou template ativo. O teste mantÃ©m as cinco rotas legadas
  como 404 em GET e POST e confirma a ausÃªncia do mÃ³dulo no catÃ¡logo.
- Foram aprovados 73 testes focados, Ruff, MyPy global, Django e migraÃ§Ãµes; a
  suÃ­te integral fechou com 781 testes, trÃªs skips e 11 subtestes. NÃ£o houve
  cobranÃ§a, integraÃ§Ã£o ou serviÃ§o externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 102 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” Jornadas removida do catÃ¡logo do produto (V-095)

- A definiÃ§Ã£o de Jornadas foi removida do catÃ¡logo efetivo da CICA em
  conformidade com D-43. Enum, tabelas e migraÃ§Ãµes ficaram preservados para
  histÃ³rico, sem rota, navegaÃ§Ã£o ou oferta acessÃ­vel.
- Os testes confirmaram as cinco rotas legadas como 404 para GET e POST, a
  ausÃªncia na navegaÃ§Ã£o e a ausÃªncia no catÃ¡logo, sem alterar contrato ou dado.
- Foram aprovados 73 testes focados, Ruff, MyPy global, Django e migraÃ§Ãµes; a
  suÃ­te integral fechou com 781 testes, trÃªs skips e 11 subtestes. NÃ£o houve
  cobranÃ§a, integraÃ§Ã£o ou serviÃ§o externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 101 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” pÃ¡ginas independentes na Caixa DTE (V-094)

- A paginaÃ§Ã£o de mensagens passou a preservar a pÃ¡gina do histÃ³rico DTE,
  filtros e empresa; o histÃ³rico jÃ¡ preservava a pÃ¡gina de mensagens. As duas
  listas nÃ£o se reiniciam mais ao navegar.
- O teste com 31 resultados DTE e 26 mensagens sintÃ©ticas confirmou a segunda
  pÃ¡gina e os vÃ­nculos de ida e volta de ambas, sem preparar, enviar ou cobrar
  consulta.
- Foram aprovados 10 testes focados, Ruff, MyPy global, Django e migraÃ§Ãµes; a
  suÃ­te integral fechou com 781 testes, trÃªs skips e 11 subtestes. NÃ£o houve
  Serpro, arquivo, consumo, cobranÃ§a ou serviÃ§o externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 99 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” fila OFX preserva o contexto da ConciliaÃ§Ã£o (V-093)

- A fila OFX Ã— DomÃ­nio passou a conservar pÃ¡ginas de Processamentos, Movimentos
  e ExportaÃ§Ãµes, alÃ©m de seus prÃ³prios filtros; percorrÃª-la nÃ£o reinicia as
  outras trÃªs Ã¡reas.
- O teste chegou Ã  terceira pÃ¡gina de 101 correspondÃªncias sintÃ©ticas com as
  demais pÃ¡ginas selecionadas e validou o retorno, sem importar, conciliar,
  reprocessar ou exportar arquivo.
- Foram aprovados 39 testes focados (um skip de OCR), Ruff, MyPy global, Django
  e migraÃ§Ãµes; a suÃ­te integral fechou com 781 testes, trÃªs skips e 11
  subtestes. NÃ£o houve ERP, arquivo, OCR real ou serviÃ§o externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 99 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” pÃ¡ginas independentes na ConciliaÃ§Ã£o (V-092)

- A paginaÃ§Ã£o dos movimentos normalizados agora preserva as pÃ¡ginas abertas de
  Processamentos e ExportaÃ§Ãµes e o contexto da ConciliaÃ§Ã£o, sem deslocar uma
  trilha quando a outra Ã© percorrida.
- O teste com 21 processamentos, 21 exportaÃ§Ãµes e 51 movimentos sintÃ©ticos
  confirmou a segunda pÃ¡gina de cada Ã¡rea e o retorno do movimento, sem importar,
  confirmar, reprocessar ou exportar arquivo.
- Foram aprovados 39 testes focados (um skip de OCR), Ruff, MyPy global, Django
  e migraÃ§Ãµes; a suÃ­te integral fechou com 781 testes, trÃªs skips e 11
  subtestes. NÃ£o houve ERP, arquivo, OCR real ou serviÃ§o externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 99 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” histÃ³rico de Triagem recuperÃ¡vel por pÃ¡gina (V-091)

- O detalhe de arquivo passou a paginar 20 eventos persistidos por vez, mostrar
  o total e manter ordem cronolÃ³gica e parÃ¢metros de retorno, sem ocultar
  evidÃªncia antiga nem carregar toda a trilha no detalhe.
- O teste com 21 eventos sintÃ©ticos confirmou as duas pÃ¡ginas, os vÃ­nculos de
  navegaÃ§Ã£o e os eventos dos extremos sem decidir, arquivar ou gerar arquivo.
  A demonstraÃ§Ã£o continua isolada por sessÃ£o e nÃ£o foi usada como prova visual
  de volume; nÃ£o houve autenticaÃ§Ã£o inserida no navegador.
- Foram aprovados 57 testes focados, Ruff, MyPy global, Django e migraÃ§Ãµes; a
  suÃ­te integral fechou com 781 testes, trÃªs skips e 11 subtestes. NÃ£o houve
  caixa, scanner, OCR, agente, serviÃ§o externo ou custo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 99 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” candidatos de conciliaÃ§Ã£o recuperÃ¡veis por pÃ¡gina (V-090)

- O detalhe de movimento nÃ£o limita mais a 50 os candidatos de conciliaÃ§Ã£o:
  percorre o recorte existente em pÃ¡ginas de 25 e informa o total avaliado,
  mantendo confirmaÃ§Ã£o humana e evidÃªncia obrigatÃ³ria.
- O teste com 51 candidatos sintÃ©ticos confirmou as trÃªs pÃ¡ginas; a sessÃ£o
  fictÃ­cia percorreu a segunda em 390 px, sem overflow horizontal ou erro de
  console. NÃ£o houve conciliaÃ§Ã£o confirmada, arquivo, ERP ou serviÃ§o externo.
- Foram aprovados 39 testes focados (um skip de OCR), Ruff, MyPy global, Django
  e migraÃ§Ãµes; a suÃ­te integral fechou com 780 testes, trÃªs skips e 11
  subtestes. O banco temporÃ¡rio foi movido Ã  Lixeira de forma recuperÃ¡vel.
- O fetch final manteve `HEAD` e `origin/main` no mesmo commit (0/0), sem pull,
  commit ou push; as 98 alteraÃ§Ãµes locais foram preservadas.

## 21/09/2026 â€” acumulador NFS-e validado por empresa (V-089)

- A decisÃ£o da revisÃ£o NFS-e agora aceita somente cÃ³digo jÃ¡ cadastrado em regra
  vigente ou histÃ³rico observado da mesma empresa; cÃ³digos inexistentes e de
  outras empresas sÃ£o recusados, sem criar regra ou lanÃ§amento.
- Foram aprovados 95 testes focados, Ruff, MyPy global e a suÃ­te integral com
  779 testes, trÃªs skips e 11 subtestes. NÃ£o houve ADN, certificado, custo ou
  serviÃ§o externo; o banco temporÃ¡rio foi movido Ã  Lixeira de forma recuperÃ¡vel.
- A demonstraÃ§Ã£o fictÃ­cia confirmou a lista local de acumuladores na decisÃ£o
  NFS-e em desktop e 390 px, sem overflow horizontal nem erro de console; ela
  nÃ£o foi usada como prova de catÃ¡logo real. O fetch final manteve `HEAD` e
  `origin/main` no mesmo commit (0/0), sem pull, commit ou push.

## 21/09/2026 â€” atenÃ§Ã£o de egressÃ£o recuperÃ¡vel por pÃ¡gina (V-088)

- O detalhe do escritÃ³rio passou a paginar 20 tentativas Claude incertas e a
  exibir seu total, no lugar de ocultar protocolos antigos; os parÃ¢metros da
  tela permanecem nos vÃ­nculos entre pÃ¡ginas.
- O teste com 21 auditorias fictÃ­cias confirmou a segunda pÃ¡gina e o protocolo
  mais antigo sem chamar IA, liberar reserva ou alterar consumo. A inspeÃ§Ã£o
  visual autenticada nÃ£o foi automatizada para nÃ£o inserir credenciais.
- Foram aprovados 57 testes focados, Ruff, MyPy global e a suÃ­te integral com
  778 testes, trÃªs skips e 11 subtestes. NÃ£o houve provedor, custo ou serviÃ§o
  externo; o banco temporÃ¡rio foi movido Ã  Lixeira de forma recuperÃ¡vel.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 96 alteraÃ§Ãµes locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 â€” fechamentos adiados recuperÃ¡veis por pÃ¡gina (V-087)

- A configuraÃ§Ã£o da plataforma passou a paginar 30 fechamentos ainda adiados
  e a exibir seu total, no lugar de cortar a lista em 30 ocorrÃªncias; os
  parÃ¢metros da tela permanecem nos vÃ­nculos entre pÃ¡ginas.
- O teste com 31 escritÃ³rios e ocorrÃªncias fictÃ­cias confirmou a segunda pÃ¡gina
  sem executar fechamento, reserva, faturamento ou mudar contratos. A inspeÃ§Ã£o
  visual autenticada nÃ£o foi automatizada para nÃ£o inserir credenciais.
- Foram aprovados 65 testes focados, com um skip de concorrÃªncia PostgreSQL,
  Ruff, MyPy global e a suÃ­te integral com 777 testes, trÃªs skips e 11
  subtestes. NÃ£o houve Asaas, custo ou serviÃ§o externo; o banco temporÃ¡rio foi
  movido Ã  Lixeira de forma recuperÃ¡vel.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 96 alteraÃ§Ãµes locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 â€” histÃ³rico do Copiloto recuperÃ¡vel por pÃ¡gina (V-086)

- O histÃ³rico aberto do Copiloto passou a paginar 12 conversas e a exibir seu
  total, no lugar de ocultar todas as conversas anteriores; a conversa em foco
  e a pÃ¡gina continuam presentes nos vÃ­nculos entre as navegaÃ§Ãµes.
- O teste com 13 conversas fictÃ­cias confirmou a segunda pÃ¡gina e a seleÃ§Ã£o da
  conversa mais antiga sem enviar pergunta, criar mensagem ou chamar IA. A
  demonstraÃ§Ã£o vazia confirmou a superfÃ­cie mÃ³vel sem overflow ou erro de
  console, sem alegar volume visual.
- Foram aprovados 49 testes focados, Ruff, MyPy global e a suÃ­te integral com
  776 testes, trÃªs skips e 11 subtestes. NÃ£o houve runtime, fallback, egressÃ£o,
  custo ou serviÃ§o externo; o ambiente temporÃ¡rio foi encerrado e movido Ã 
  Lixeira de forma recuperÃ¡vel.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 94 alteraÃ§Ãµes locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 â€” trilhas de ConciliaÃ§Ã£o recuperÃ¡veis (V-085)

- Processamentos e exportaÃ§Ãµes passaram a paginar 20 registros de forma
  independente, em vez dos cortes de 12 e 8, preservando os parÃ¢metros da tela
  e a outra trilha.
- O teste com 21 execuÃ§Ãµes e 21 exportaÃ§Ãµes fictÃ­cias confirmou a segunda pÃ¡gina
  de cada uma sem importar, reprocessar, exportar ou baixar arquivos. A
  demonstraÃ§Ã£o confirmou apenas as Ã¡reas mÃ³veis, sem overflow ou erro de console.
- Foram aprovados 93 testes focados, com um skip de OCR local, Ruff, MyPy global
  e a suÃ­te integral com 775 testes, trÃªs skips e 11 subtestes. NÃ£o houve ERP,
  arquivo real, custo ou serviÃ§o externo; o ambiente temporÃ¡rio foi encerrado e
  movido Ã  Lixeira de forma recuperÃ¡vel.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 91 alteraÃ§Ãµes locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 â€” histÃ³rico de importaÃ§Ãµes recuperÃ¡vel no onboarding (V-084)

- A Ã¡rea de onboarding passou a paginar 20 lotes de importaÃ§Ã£o e a exibir o
  total, no lugar do corte nos oito mais recentes; a fonte e a prÃ©via continuam
  presentes nos vÃ­nculos entre pÃ¡ginas.
- O teste com 21 lotes fictÃ­cios confirmou a segunda pÃ¡gina sem enviar,
  confirmar ou alterar arquivo. A demonstraÃ§Ã£o vazia confirmou a superfÃ­cie
  mÃ³vel sem overflow ou erro de console, sem alegar volume visual.
- Foram aprovados 57 testes focados, Ruff, MyPy global e a suÃ­te integral com
  774 testes, trÃªs skips e 11 subtestes. NÃ£o houve arquivo real, DomÃ­nio,
  agente, credencial, custo ou serviÃ§o externo; o ambiente temporÃ¡rio foi
  encerrado e movido Ã  Lixeira de forma recuperÃ¡vel.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 90 alteraÃ§Ãµes locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 â€” histÃ³rico DTE recuperÃ¡vel por pÃ¡gina prÃ³pria (V-083)

- O histÃ³rico de resultados da Caixa DTE passou a paginar 30 itens, informar o
  total e preservar a pÃ¡gina independente da fila de mensagens e os parÃ¢metros
  correntes da tela.
- O teste com 31 itens DTE fictÃ­cios confirmou a segunda pÃ¡gina sem preparar
  consulta, alterar resultado ou autorizaÃ§Ã£o. A demonstraÃ§Ã£o vazia confirmou a
  superfÃ­cie mÃ³vel sem overflow ou erro de console, sem alegar volume visual.
- Foram aprovados 75 testes focados, Ruff, MyPy global e a suÃ­te integral com
  773 testes, trÃªs skips e 11 subtestes. NÃ£o houve Serpro, certificado,
  consumo, cobranÃ§a, custo ou serviÃ§o externo; o ambiente temporÃ¡rio foi
  encerrado e movido Ã  Lixeira de forma recuperÃ¡vel.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 89 alteraÃ§Ãµes locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 â€” histÃ³rico de cobranÃ§a manual recuperÃ¡vel (V-082)

- O console da plataforma passou a paginar as faturas internas em pÃ¡ginas de
  12, expondo o total sem ocultar competÃªncias antigas.
- O teste com 25 faturas sintÃ©ticas confirmou a pÃ¡gina 3 e o vÃ­nculo de retorno
  sem alterar valores, contratos ou status.
- Foram aprovados 41 testes focados, Ruff, MyPy global e a suÃ­te integral com
  772 testes, trÃªs skips e 11 subtestes. NÃ£o houve cobranÃ§a, Asaas, cartÃ£o,
  Pix, boleto ou serviÃ§o externo. A inspeÃ§Ã£o visual autenticada permanece
  pendente por nÃ£o inserir credenciais no navegador.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 87 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” Radar da Reforma recuperÃ¡vel por pÃ¡gina (V-081)

- A lista de alertas do Radar passou a paginar 50 registros, no lugar do corte
  nos 80 primeiros, mantendo termo, fonte e tema em cada retorno.
- O teste com 101 alertas sintÃ©ticos confirmou a terceira pÃ¡gina e os filtros.
  A demonstraÃ§Ã£o, que contÃ©m somente trÃªs exemplos, confirmou o filtro IBS e a
  apresentaÃ§Ã£o mÃ³vel, sem alegar visualizaÃ§Ã£o em volume.
- Foram aprovados 77 testes focados, Ruff, MyPy global e a suÃ­te integral com
  771 testes, trÃªs skips e 11 subtestes. NÃ£o houve coleta, URL oficial, ERP ou
  serviÃ§o externo; o ambiente temporÃ¡rio foi encerrado e movido Ã  Lixeira.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 85 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” auditoria de conciliaÃ§Ã£o recuperÃ¡vel por pÃ¡gina (V-080)

- A trilha de auditoria deixou de ocultar eventos depois dos primeiros 200:
  agora apresenta 100 por pÃ¡gina, total do filtro e navegaÃ§Ã£o que conserva a
  aÃ§Ã£o selecionada.
- O teste com 201 eventos e a demonstraÃ§Ã£o local temporÃ¡ria confirmaram a
  terceira pÃ¡gina e o retorno Ã  segunda; em 390 px nÃ£o houve overflow
  horizontal ou erro de console.
- Foram aprovados 90 testes focados, Ruff, MyPy global e a suÃ­te integral com
  770 testes, trÃªs skips e 11 subtestes. NÃ£o houve arquivo bancÃ¡rio, ERP,
  DomÃ­nio ou serviÃ§o externo; o ambiente temporÃ¡rio foi encerrado e movido Ã 
  Lixeira de modo recuperÃ¡vel.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 84 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” ficha da empresa com histÃ³ricos recuperÃ¡veis (V-079)

- A ficha passou a paginar documentos NFS-e, revisÃµes abertas e mensagens DTE
  em seÃ§Ãµes independentes de 20 registros, preservando o retorno Ã  carteira.
- O teste com 21 itens de cada tipo e a demonstraÃ§Ã£o temporÃ¡ria confirmaram a
  pÃ¡gina 2 das trÃªs seÃ§Ãµes; o retorno da DTE manteve as outras pÃ¡ginas. Em 390
  px nÃ£o houve overflow horizontal nem erro de console.
- Foram aprovados 72 testes focados, Ruff, MyPy global e a suÃ­te integral com
  769 testes, trÃªs skips e 11 subtestes. NÃ£o houve ADN, Serpro, A1 ou serviÃ§o
  externo; o ambiente temporÃ¡rio foi encerrado e movido Ã  Lixeira.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 83 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” cobertura de certificados recuperÃ¡vel (V-078)

- A lista de empresas sem certificado A1 vÃ¡lido passou a paginar 20 itens, sem
  interferir na paginaÃ§Ã£o da carteira de certificados; a navegaÃ§Ã£o preserva os
  parÃ¢metros de busca e situaÃ§Ã£o existentes.
- O teste com 21 empresas e a demonstraÃ§Ã£o temporÃ¡ria com 25 pendÃªncias
  confirmaram a segunda pÃ¡gina e o retorno Ã  primeira. Em 390 px nÃ£o houve
  overflow horizontal ou erro de console.
- Foram aprovados 70 testes focados, Ruff, MyPy global e a suÃ­te integral com
  768 testes, trÃªs skips e 11 subtestes. NÃ£o houve A1, ADN ou serviÃ§o externo;
  o ambiente temporÃ¡rio foi encerrado e movido Ã  Lixeira de modo recuperÃ¡vel.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 81 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” histÃ³rico de Parcelamentos recuperÃ¡vel (V-077)

- O histÃ³rico por empresa passou a paginar as operaÃ§Ãµes, em vez de cortar apÃ³s
  20 tentativas, preservando a empresa em foco na navegaÃ§Ã£o.
- A demonstraÃ§Ã£o temporÃ¡ria com 21 operaÃ§Ãµes fictÃ­cias percorreu as duas
  pÃ¡ginas e preservou o aviso de recuperaÃ§Ã£o para resultado incerto, sem erro
  de console. Foram aprovados 77 testes focados, Ruff, MyPy global e a suÃ­te
  integral com 767 testes, trÃªs skips e 11 subtestes.
- NÃ£o houve chamada PARCSN/Serpro; o ambiente temporÃ¡rio foi encerrado.
- ApÃ³s atualizar as referÃªncias remotas, `HEAD` permaneceu sincronizado com
  `origin/main` (0 Ã  frente, 0 atrÃ¡s); as 80 alteraÃ§Ãµes locais foram
  preservadas.

## 21/09/2026 â€” fila de conciliaÃ§Ã£o sem corte silencioso (V-076)

- A fila OFX Ã— DomÃ­nio passou a paginar 50 resultados, mantendo busca e
  situaÃ§Ã£o; a montagem de candidatos continua limitada Ã  pÃ¡gina apresentada.
- O teste autenticado criou 101 correspondÃªncias sem par, alcanÃ§ou a pÃ¡gina 3
  e manteve os filtros no retorno. A demonstraÃ§Ã£o possui somente duas linhas,
  portanto nÃ£o foi usada para alegar inspeÃ§Ã£o visual da paginaÃ§Ã£o em volume.
- Foram aprovados 95 testes focados, Ruff, MyPy global e a suÃ­te integral com
  766 testes, trÃªs skips e 11 subtestes, sem arquivo bancÃ¡rio ou serviÃ§o externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 80 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” carteira de Parcelamentos por lote autorizado (V-075)

- A carteira deixou de ocultar empresas acima de 100 registros e agora pagina
  30 por pÃ¡gina, preservando a pesquisa.
- O seletor em massa passou a declarar o escopo da pÃ¡gina e cada pÃ¡gina respeita
  o limite de 30 empresas jÃ¡ validado pelo backend. A jornada com 101 empresas
  fictÃ­cias alcanÃ§ou a pÃ¡gina 4, retornou Ã  3 e nÃ£o apresentou erro de console.
- Foram aprovados 76 testes focados, Ruff, MyPy global e a suÃ­te integral com
  765 testes, trÃªs skips e 11 subtestes. NÃ£o houve Serpro, PARCSN, DomÃ­nio ou
  outro serviÃ§o externo; o ambiente temporÃ¡rio foi encerrado.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 78 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” carteira de guias sem corte silencioso (V-074)

- Guias/DCTFWeb passou a paginar listas maiores que 100 resultados, mantendo
  busca, situaÃ§Ã£o e vencimento ao navegar entre as pÃ¡ginas.
- A demonstraÃ§Ã£o temporÃ¡ria com 101 guias fictÃ­cias confirmou pÃ¡gina 2, retorno
  Ã  pÃ¡gina 1 e ausÃªncia de erros de console. Foram aprovados 88 testes focados,
  Ruff, MyPy global e a suÃ­te integral com 764 testes, trÃªs skips e 11
  subtestes.
- O banco e servidor locais de QA foram encerrados; o diretÃ³rio temporÃ¡rio foi
  movido de forma recuperÃ¡vel para a Lixeira. NÃ£o houve chamada Serpro,
  DCTFWeb, DomÃ­nio ou outro serviÃ§o externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 76 alteraÃ§Ãµes locais existentes foram preservadas.

## 21/09/2026 â€” revisÃ£o NFS-e e carteira sem corte silencioso (V-073)

- O detalhe local passou a mostrar os fatos normalizados necessÃ¡rios Ã  decisÃ£o;
  a demonstraÃ§Ã£o os preenche como fictÃ­cios e mantÃ©m a referÃªncia da contraparte
  pseudonimizada.
- A carteira agora pagina mais de 100 documentos sem perder o filtro. A pÃ¡gina
  2 e o retorno Ã  pÃ¡gina 1 foram confirmados em celular no navegador interno,
  sem overflow ou erro de console. Foram aprovados 79 testes focados, Ruff,
  MyPy e a suÃ­te integral com 763 testes, trÃªs skips e 11 subtestes.
- O banco e servidor locais de QA foram encerrados; o diretÃ³rio temporÃ¡rio foi
  movido de forma recuperÃ¡vel para a Lixeira.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push.

## 21/09/2026 â€” contrato do runtime de IA e guarda de fallback verificados (V-072)

- O runtime privado OpenAI-compatÃ­vel respondeu em teste com evidÃªncia compacta;
  uma resposta local nÃ£o acionou fallback nem criou egressÃ£o, mesmo com a rota
  externa configurada.
- A ausÃªncia de opt-in continuou bloqueando o provedor e registrando a negaÃ§Ã£o.
  Foram aprovados 73 testes, 3 subtestes, Ruff e MyPy global; o ambiente foi
  totalmente simulado, sem modelo ou provedor real.
- O fetch final manteve `HEAD` e `origin/main` no mesmo commit (0/0), sem pull,
  commit ou push; as alteraÃ§Ãµes locais foram preservadas.

## 21/09/2026 â€” mÃ³dulos fictÃ­cios e Copiloto validados visualmente (V-071)

- Guias, DTE, Parcelamentos, ConciliaÃ§Ã£o, Radar e Copiloto renderizaram na
  demonstraÃ§Ã£o, com aviso explÃ­cito e sem erro de console.
- O Copiloto exigiu empresa e apresentou resposta simulada com fontes marcadas
  como sintÃ©ticas, sem egressÃ£o ou chamada externa.

## 21/09/2026 â€” revisÃ£o fiscal e isolamento de console verificados (V-070)

- A fila e o detalhe NFS-e fictÃ­cios apresentaram contexto, hash, evidÃªncia,
  confianÃ§a, XML e decisÃ£o explÃ­cita com retorno Ã  fila.
- A sessÃ£o de demonstraÃ§Ã£o recebeu acesso restrito ao abrir o console Mewstack;
  nenhum erro de console foi observado. A inspeÃ§Ã£o do console autenticado segue
  pendente por nÃ£o inserir credenciais automaticamente.

## 21/09/2026 â€” auditoria visual pÃºblica e demonstraÃ§Ã£o fictÃ­cia (V-069)

- A home, cadastro, abas/FAQ, viewport mÃ³vel e console foram verificados no
  navegador interno com base temporÃ¡ria; nÃ£o houve overflow nem erro de console.
- A demonstraÃ§Ã£o isolada alcanÃ§ou dashboard e Triagem, onde o anexo em
  quarentena permaneceu explicitamente bloqueado para abertura e download.
- A auditoria Ã© parcial: o Mac bloqueado impediu automaÃ§Ã£o nativa e nÃ£o houve
  acesso a console, integraÃ§Ãµes, dados reais ou ambiente publicado.

## 21/09/2026 â€” view Hub integralmente tipada e regressÃ£o focada (V-068)

- Os contratos locais de conciliaÃ§Ã£o, Triagem, certificados, setup e tokens
  foram explicitados sem chamar serviÃ§os externos ou modificar fluxos.
- Ruff, MyPy da view e MyPy global passaram; 119 testes locais passaram, com
  um Ãºnico skip esperado de OCR em portuguÃªs. A suÃ­te integral repetiu 762
  testes aprovados, 3 skips conhecidos e 11 subtestes aprovados.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0); as
  alteraÃ§Ãµes locais da execuÃ§Ã£o foram preservadas, sem commit ou push.

## 21/09/2026 â€” NFS-e e DCTFWeb da view Hub refinados (V-067)

- ColeÃ§Ãµes, contexto, nÃºmeros, UUID e cotaÃ§Ãµes receberam contratos explÃ­citos;
  20 testes NFS-e/DCTFWeb passaram sem integraÃ§Ã£o externa.

## 21/09/2026 â€” primeira seÃ§Ã£o da view do Hub tipada (V-066)

- DemonstraÃ§Ã£o, dashboard, convites, mÃ³dulo, despacho NFS-e e filtros receberam
  contratos explÃ­citos; 86 testes locais passaram sem alteraÃ§Ã£o de integraÃ§Ã£o.
- A dÃ­vida da view do Hub caiu a 114 erros; nenhuma homologaÃ§Ã£o externa foi
  realizada.

## 21/09/2026 â€” serviÃ§os, agente e interface de IA tipados (V-065)

- Reserva do Copiloto, API do agente e estado transitÃ³rio de entrega da
  interface receberam contratos explÃ­citos, sem persistir novos campos nem
  acionar fallback externo.
- Ruff, MyPy e 68 testes passaram. A dÃ­vida global ficou em 131 erros de uma
  Ãºnica view do Hub; curadoria e egressÃ£o real continuam pendentes.

## 21/09/2026 â€” operaÃ§Ãµes Integra e NFS-e tipadas (V-064)

- ServiÃ§os, tarefas, reserva entre livros, despacho pÃ³s-commit e validaÃ§Ã£o
  decimal NFS-e receberam contratos explÃ­citos, mantendo as integraÃ§Ãµes sem
  execuÃ§Ã£o real.
- Ruff, MyPy e 57 testes DTE/DCTFWeb/PARCSN/NFS-e passaram. A dÃ­vida global
  caiu a 143 erros em 4 arquivos; Serpro, ADN e DomÃ­nio seguem nÃ£o homologados.

## 21/09/2026 â€” regressÃ£o integral atualizada (V-063)

- Django, migraÃ§Ãµes, diff e suÃ­te integral foram reexecutados apÃ³s V-060â€“V-062:
  762 testes, 3 skips conhecidos e 11 subtestes passaram em 27,52 s. O fetch
  final confirmou `HEAD` e `origin/main` no mesmo commit (0/0).
- NÃ£o houve integraÃ§Ã£o externa. Os limites dos skips permanecem Playwright
  Python opcional, OCR local e concorrÃªncia PostgreSQL.

## 21/09/2026 â€” seguranÃ§a, multipart e acesso DTE tipados (V-062)

- Scanner/polÃ­tica receberam fluxo binÃ¡rio explÃ­cito; multipart separou campos e
  bytes; e navegaÃ§Ã£o/reserva DTE receberam contratos estÃ¡ticos de requisiÃ§Ã£o e
  consumo.
- Quarenta testes locais passaram com Ruff/MyPy; a dÃ­vida global caiu a 160
  erros em 7 arquivos. Nenhum scanner, DomÃ­nio, Serpro ou dado real foi usado.

## 21/09/2026 â€” plataforma administrativa tipada e retestada (V-061)

- Tarefa de competÃªncia, snapshot contratual, validaÃ§Ã£o de conteÃºdo de webhook
  e contrato HTTP legal receberam tipos explÃ­citos, preservando regras e dados
  comerciais existentes.
- Ruff, MyPy e 69 testes de plataforma passaram; a dÃ­vida global caiu a 168
  erros em 11 arquivos. Nenhuma cobranÃ§a, evento Asaas ou alteraÃ§Ã£o comercial
  foi realizada.

## 21/09/2026 â€” coletores e fila de Triagem tipados (V-060)

- Cursor Graph, conteÃºdo IMAP, fÃ¡brica de conexÃ£o e consulta elegÃ­vel da fila
  receberam contratos explÃ­citos, preservando as leituras e checkpoints locais.
- Ruff, MyPy e 22 testes de Graph, IMAP, retentativa, ingestÃ£o e tarefas
  passaram. A dÃ­vida global caiu a 172 erros em 15 arquivos, sem OAuth, DNS,
  caixa, antimalware ou destino real.

## 21/09/2026 â€” regressÃ£o integral e relatÃ³rios/sincronizaÃ§Ã£o tipados (V-058/V-059)

- A verificaÃ§Ã£o Django, migraÃ§Ãµes e suÃ­te integral passaram: 762 testes, 3
  skips e 11 subtestes. Os skips continuam sendo limitaÃ§Ãµes conhecidas de
  Playwright Python, OCR local e concorrÃªncia PostgreSQL.
- RelatÃ³rios XLSX/PDF e a normalizaÃ§Ã£o da sincronizaÃ§Ã£o bancÃ¡ria receberam
  contratos estÃ¡ticos explÃ­citos; 7 testes de sincronizaÃ§Ã£o passaram. NÃ£o hÃ¡
  teste especÃ­fico de exportaÃ§Ã£o no repositÃ³rio. A dÃ­vida MyPy caiu para 185
  erros em 18 arquivos, sem consulta DomÃ­nio ou geraÃ§Ã£o com dados reais.

## 21/09/2026 â€” gateway e comandos de IA tipados (V-057)

- Payload do gateway e interfaces de comandos passaram a ter tipos explÃ­citos.
  Trinta e dois testes de comandos, escopo e acesso de IA passaram sem chamada
  Anthropic; comandos de custo continuam bloqueados por aprovaÃ§Ã£o especÃ­fica.
- Ruff, MyPy e diff passaram; a dÃ­vida global caiu a 197 erros em 20 arquivos.
  Curadoria, egressÃ£o, treino e prova de artefato seguem pendentes.

## 21/09/2026 â€” configuraÃ§Ã£o de plataforma tipada e retestada (V-056)

- FormulÃ¡rios, persistÃªncia, usuÃ¡rio de auditoria e seleÃ§Ã£o de plano passaram a
  ter contratos estÃ¡ticos explÃ­citos. Pagamentos, notificaÃ§Ãµes e aprovaÃ§Ã£o de
  fallback foram retestados sem chamar fornecedores.
- Ruff, MyPy e 55 testes passaram, com um skip PostgreSQL; a dÃ­vida global caiu
  para 205 erros em 24 arquivos. Nenhuma credencial, SMTP, Claude, Serpro ou
  Asaas real foi utilizado.

## 21/09/2026 â€” coletor Gmail e ingestÃ£o tipados (V-055)

- Cursor, checkpoint, data inicial, base64 e caminho de blob receberam
  prÃ©-condiÃ§Ãµes explÃ­citas. Quatorze testes de ingestÃ£o/retentativa, Ruff e
  MyPy passaram; a dÃ­vida global reduziu a 291 erros em 28 arquivos.
- Nenhuma caixa Google, OAuth ou provedor foi acessado. A etapa 06 continua
  aguardando homologaÃ§Ãµes externas.

## 21/09/2026 â€” cliente IMAP local tipado (V-054)

- Socket e respostas IMAP receberam contratos explÃ­citos, preservando busca
  somente leitura sem charset. Doze testes de conexÃ£o/retentativa sintÃ©tica,
  Ruff e MyPy passaram; a dÃ­vida global caiu a 296 erros em 30 arquivos.
- Nenhuma caixa, credencial ou provedor foi acessado. A homologaÃ§Ã£o segue nas
  etapas 06 e 12.

## 21/09/2026 â€” livros de tokens e faturamento tipados (V-053)

- Medidores legado e de tokens foram separados explicitamente no fechamento;
  franquia/preÃ§o e usuÃ¡rio de aceite sÃ£o materializados antes da persistÃªncia.
  Vinte e dois testes passaram, com concorrÃªncia PostgreSQL mantida como skip.
- Ruff, MyPy e diff passaram nos mÃ³dulos; a dÃ­vida global reduziu a 300 erros em
  31 arquivos. NÃ£o houve cobranÃ§a, Asaas, preÃ§o novo ou pagamento real.

## 21/09/2026 â€” transporte de e-mail local tipado (V-052)

- O backend passou a declarar configuraÃ§Ã£o, SMTP e sequÃªncia de mensagens sem
  alterar o carregamento tardio do modelo. Ruff, MyPy e 33 testes de
  configuraÃ§Ã£o passaram; a dÃ­vida global reduziu para 311 erros em 33 arquivos.
- NÃ£o houve conexÃ£o SMTP/DNS/Brevo, segredo ou envio real. A homologaÃ§Ã£o segue
  exclusivamente na etapa 12 conforme D-77/D-78.

## 21/09/2026 â€” PARCSN e tarefas agendadas tipados (V-051)

- O parser local passou a validar explicitamente o expoente decimal e os
  inteiros do payload; o decorador de tarefa tem contrato de retorno completo.
  Vinte testes de PARCSN/operaÃ§Ãµes passaram sem transporte Serpro.
- Ruff, MyPy e diff passaram nos mÃ³dulos; a dÃ­vida global chegou a 316 erros em
  34 arquivos. Credenciais, representaÃ§Ã£o, custo e prova Serpro seguem abertas.

## 21/09/2026 â€” limites de entrada da importaÃ§Ã£o explicitados (V-050)

- A prÃ©via local exige nome de arquivo antes de persistir e usa esse valor
  validado nos fluxos tabular e de backup; o mapa de capacidades foi tipado.
  NÃ£o houve arquivo ou backup real.
- Ruff e 57 testes do Hub passaram; o MyPy global caiu a 328 ocorrÃªncias. A
  tentativa de isolaÃ§Ã£o de imports expÃ´s erro interno do MyPy/django-stubs, nÃ£o
  mascarado como aprovaÃ§Ã£o. A etapa 09 continua sem layout/ERP/OCR homologado.

## 21/09/2026 â€” serviÃ§o de conciliaÃ§Ã£o tipado e retestado (V-049)

- Foram explicitados contratos locais de parser, checkpoint, armazenamento,
  relaÃ§Ãµes opcionais e regra de faixa, preservando a recusa de dados invÃ¡lidos.
  Bibliotecas de XLSX/PDF seguem sem stubs, com exceÃ§Ã£o limitada aos imports.
- Ruff e MyPy do serviÃ§o, 35 testes de conciliaÃ§Ã£o (um skip de OCR), Django,
  migraÃ§Ãµes e diff passaram. MyPy global caiu para 334 erros em 38 arquivos.
- NÃ£o houve ERP, arquivo real, OCR disponÃ­vel, fonte Radar ou exportaÃ§Ã£o
  homologada; a etapa 09 continua aberta por esses requisitos.

## 21/09/2026 â€” formulÃ¡rios de contrataÃ§Ã£o retestados (V-048)

- Ajustadas fronteiras de tipos de `LeadForm`, plano e proposta de tokens sem
  mudar preÃ§o, contrato, consumo ou cobranÃ§a. A suÃ­te focada aprovou 26 testes,
  com um skip de concorrÃªncia reservado ao PostgreSQL.
- Ruff, MyPy e diff passaram; MyPy global passou a 348 erros em 39 arquivos.
  NÃ£o houve chamada CNPJ, Asaas, criaÃ§Ã£o de cobranÃ§a ou qualquer custo.

## 21/09/2026 â€” formulÃ¡rios do Hub e cache CNPJ tipados (V-047)

- FormulÃ¡rios de escopo, importaÃ§Ã£o e conciliaÃ§Ã£o receberam tipos seguros para
  escolhas dinÃ¢micas, modelos, widgets e validaÃ§Ãµes. ReferÃªncias genÃ©ricas de
  Django sÃ£o adiadas para nÃ£o tentar subscrever classes em execuÃ§Ã£o.
- A suÃ­te de conciliaÃ§Ã£o aprovou 35 testes, com um skip esperado por OCR local;
  Ruff, MyPy, Django, migraÃ§Ãµes e diff passaram. O cache de CNPJ tambÃ©m sÃ³
  reutiliza dicionÃ¡rio de textos e nÃ£o chamou a fonte externa.
- A dÃ­vida MyPy global reduziu para 356 ocorrÃªncias em 40 arquivos. OCR,
  layouts, ERP, Radar, fontes e homologaÃ§Ãµes continuam fora desta evidÃªncia.

## 21/09/2026 â€” prÃ©-condiÃ§Ãµes de serviÃ§o da Triagem explicitadas (V-046)

- As verificaÃ§Ãµes jÃ¡ esperadas pelo serviÃ§o foram tornadas explÃ­citas para os
  tipos: relaÃ§Ãµes de empresa/tipo, nome e tamanho do upload, caminho interno e
  stream binÃ¡rio. NÃ£o houve mudanÃ§a de fluxo, regra de seguranÃ§a, banco,
  provedor, arquivo real ou migraÃ§Ã£o.
- Ruff e MyPy passaram no serviÃ§o; 35 testes de domÃ­nio, ingestÃ£o e agente
  Windows passaram em 7,47 s. Django, dry-run de migraÃ§Ãµes e diff passaram.
  A linha de base global reduziu para 399 erros em 42 arquivos.

## 21/09/2026 â€” formulÃ¡rios da Triagem tipados sem mudanÃ§a funcional (V-045)

- Foram eliminadas 127 ocorrÃªncias MyPy dos seis formulÃ¡rios. As fronteiras
  dinÃ¢micas do Django foram tipadas com precisÃ£o pragmÃ¡tica, os campos de
  empresa/documento ganharam tipos de modelo explÃ­citos e o tratamento de data
  preserva a validaÃ§Ã£o existente.
- Ruff e MyPy passaram nos mÃ³dulos alterados; 51 testes de polÃ­tica, IMAP,
  domÃ­nio e ingestÃ£o sintÃ©tica passaram em 14,77 s, e `git diff --check` ficou limpo. MyPy global
  reduziu de 535 erros em 46 arquivos para 408 em 43 arquivos.
- NÃ£o houve modificaÃ§Ã£o de tela, fluxo, banco, provedor, caixa real, destino ou
  migraÃ§Ã£o. A etapa 06 continua aberta pelas dependÃªncias Q-12 a Q-25/Q-31 e
  pela homologaÃ§Ã£o externa.

## 21/09/2026 â€” diagnÃ³stico global e primeiro lote de tipos da Triagem (V-044)

- A auditoria `uv run mypy .` achou 535 ocorrÃªncias em 46 arquivos. O nÃºmero Ã©
  uma linha de base de dÃ­vida tÃ©cnica, nÃ£o uma validaÃ§Ã£o verde nem um bloqueio
  de funcionamento local.
- O primeiro lote eliminou a divergÃªncia entre enum e chave de texto no mapa de
  apresentaÃ§Ã£o de caixas e tornou explÃ­cita a ausÃªncia de stubs de `defusedxml`.
  NÃ£o houve mudanÃ§a de fluxo, banco, provedor, dado operacional ou migraÃ§Ã£o.
- Ruff e MyPy passaram nos dois mÃ³dulos; 44 testes de polÃ­tica, domÃ­nio e
  ingestÃ£o de e-mail passaram em 7,12 s, e o diff nÃ£o tem espaÃ§o invÃ¡lido.
  A retomada segura Ã© reduzir a dÃ­vida em lotes revisÃ¡veis, preservando o
  diagnÃ³stico global atÃ© que cada mÃ³dulo tenha evidÃªncia prÃ³pria.

## 21/09/2026 â€” qualidade de tipos local (V-043)

- Corrigidas as 21 ocorrÃªncias MyPy encontradas durante V-042 em armazenamento
  privado da Triagem, validaÃ§Ã£o OAuth, caminho privado de conciliaÃ§Ã£o e modelos
  de livros de tokens. As alteraÃ§Ãµes preservam as assinaturas Django e nÃ£o
  mudam regra de negÃ³cio, migraÃ§Ã£o, provedor ou dado operacional.
- MyPy e Ruff passaram nos seis mÃ³dulos envolvidos. Django, dry-run de
  migraÃ§Ãµes e diff tambÃ©m passaram; 125 testes focados (um skip de OCR) e trÃªs
  subtestes cobriram Triagem, conciliaÃ§Ã£o, cobranÃ§a e IA.
- A suÃ­te integral iniciada posteriormente excedeu a janela de captura da
  sessÃ£o, sem resumo recuperÃ¡vel; ela nÃ£o Ã© apresentada como aprovaÃ§Ã£o. NÃ£o
  restou processo Pytest e `lastfailed` estava vazio. O ponto de retomada Ã©
  repetir a suÃ­te integral em terminal com captura persistente antes de usar
  esta alteraÃ§Ã£o como revalidaÃ§Ã£o global.

## 21/09/2026 â€” etapa 05: gate de identificadores pessoais no manifesto (V-042)

- D-94 formalizou o controle local: CPF, CNPJ ou e-mail reconhecÃ­vel em
  pergunta, resposta ou referÃªncia bloqueia o manifesto de treino e avaliaÃ§Ã£o
  antes de qualquer gravaÃ§Ã£o. O registro nÃ£o Ã© mascarado automaticamente; a
  anonimizaÃ§Ã£o exige revisÃ£o humana para preservar seu sentido contÃ¡bil.
- O comando de exportaÃ§Ã£o transforma a recusa em erro controlado e nÃ£o cria o
  JSONL. D-95 acrescentou criaÃ§Ã£o exclusiva: ele tambÃ©m recusa sobrescrever um
  artefato existente. Testes cobrem os trÃªs locais possÃ­veis do identificador,
  a ausÃªncia de artefato apÃ³s a falha e a preservaÃ§Ã£o do arquivo jÃ¡ existente.
- Ruff, Django, dry-run de migraÃ§Ãµes e 39 testes focados/3 subtestes passaram.
  A suÃ­te integral fechou com 762 aprovados, 3 skips esperados e 11 subtestes.
  NÃ£o houve egressÃ£o, Claude, dado de cliente, modelo, treino, GPU, custo ou
  deploy. A etapa 05 segue em andamento por curadoria, corpus e aprovaÃ§Ãµes
  Q-08/Q-09/Q-11/Q-34. MyPy nÃ£o fechou: a execuÃ§Ã£o a partir de `src/` reportou
  21 erros em quatro mÃ³dulos nÃ£o alterados (`triage`, `hub` e `platform`), que
  ficam registrados como dÃ­vida tÃ©cnica separada.

## 21/09/2026 â€” anÃ¡lise integral, etapa 04 e comparaÃ§Ã£o com GitHub (V-041)

- A documentaÃ§Ã£o canÃ´nica, o inventÃ¡rio, a matriz de evidÃªncias e o cÃ³digo
  atual foram confrontados. O produto permanece um SaaS multiempresa da
  Mewstack com agente Windows e mÃ³dulos operacionais; a condiÃ§Ã£o de venda
  continua sendo operaÃ§Ã£o verificÃ¡vel e recuperÃ¡vel, nÃ£o a existÃªncia de tela
  ou teste isolado.
- A prÃ³xima etapa do plano continua sendo Siescon. A preparaÃ§Ã£o correta jÃ¡
  modela o destino, mas o registro de adaptadores contÃ©m apenas DomÃ­nio; pedir
  Siescon Ã© recusado antes de ler lanÃ§amentos ou criar arquivo. NÃ£o foi criado
  SQL, endpoint, credencial ou layout especulativo. Q-33 continua exigindo
  versÃ£o/banco/mÃ©todo de leitura, schema, chave empresarial/cursor, ambiente e
  layout de importaÃ§Ã£o por canal seguro.
- Ruff, Django, dry-run de migraÃ§Ãµes, 35 testes focados (1 skip de OCR) e a
  suÃ­te completa (759 aprovados, 3 skips e 8 subtestes) passaram. Nenhuma
  integraÃ§Ã£o externa foi executada. `git fetch origin --prune` e a comparaÃ§Ã£o
  `HEAD...origin/main` retornaram 0 commits de cada lado; nÃ£o havia mudanÃ§a do
  GitHub a trazer.
- A etapa 04 fica em andamento e bloqueada, nÃ£o concluÃ­da. ApÃ³s receber o
  contrato Q-33, revisar o material antes de escrever adaptador, entÃ£o validar
  leitura idempotente e exportaÃ§Ã£o importada/conferida no ambiente autorizado.

## 20/09/2026 â€” etapa 11: pausa da auditoria local de interaÃ§Ã£o

- A continuidade segura selecionada foi a auditoria local de teclado, foco e
  estados de erro/vazio, em servidor descartÃ¡vel com SQLite e egressÃ£o externa
  bloqueada. O servidor e a aba de demonstraÃ§Ã£o foram encerrados ao parar.
- A regressÃ£o automatizada existente nÃ£o pÃ´de ser executada porque o pacote
  Node `playwright` nÃ£o estÃ¡ instalado neste checkout. A inspeÃ§Ã£o com navegador
  nativo tambÃ©m nÃ£o iniciou: o aplicativo Codex aguarda a concessÃ£o Ãºnica de
  Acessibilidade e GravaÃ§Ã£o de Tela. NÃ£o foram inferidos resultados de UI.
- Ponto de retomada: apÃ³s essa permissÃ£o, executar as jornadas sintÃ©ticas de
  teclado/foco/erro/vazio da etapa 11 e registrar apenas os estados de fato
  observados. NÃ£o hÃ¡ alteraÃ§Ã£o de cÃ³digo, configuraÃ§Ã£o, dados ou provedor neste
  registro.

## 20/09/2026 â€” etapa 10: contrato local do cliente Asaas (V-040)

- Implementado `apps.platform.asaas` com ambientes explÃ­citos, chave e
  transporte injetados, consulta por `externalReference`, criaÃ§Ã£o de cliente e
  cobranÃ§a avulsa sem dados de cartÃ£o. Falha ou retorno incerto nÃ£o faz nova
  tentativa automÃ¡tica de `POST`.
- `uv run pytest tests/test_asaas_client.py tests/test_platform_billing.py tests/test_platform_payments.py tests/test_token_billing.py tests/test_cica_contract_mfa.py tests/test_cica_operation_access.py -q` fechou com 49 aprovados e um skip de concorrÃªncia exclusivo do PostgreSQL. Ruff, Django, dry-run de migraÃ§Ãµes e diff passaram.
- A revalidaÃ§Ã£o integral fechou com 759 aprovados, 3 ignorados e 8 subtestes em
  28,99 s; os skips sÃ£o Playwright Python opcional, OCR portuguÃªs ausente e a
  concorrÃªncia de locks jÃ¡ coberta em PostgreSQL histÃ³rico.
- O contrato foi conferido na documentaÃ§Ã£o oficial Asaas e nÃ£o fez conexÃ£o,
  usou chave real, alterou configuraÃ§Ã£o ou criou objeto no provedor. Ainda falta
  orquestrar dados comerciais, cliente e `PaymentAttempt`, alÃ©m da homologaÃ§Ã£o
  autorizada de Pix, boleto, cartÃ£o e eventos na etapa 12.

## 19/09/2026 â€” etapa 11: inspeÃ§Ã£o local de jornadas e interfaces (V-039)

- Em servidor isolado com banco, mÃ­dia e massa sintÃ©ticos, 14 caminhos da Ã¡rea
  de trabalho foram verificados em desktop e 390 Ã— 844: cada um exibiu um `h1`,
  nÃ£o apresentou overflow horizontal nem campo visÃ­vel sem rÃ³tulo na checagem
  DOM. A Triagem fictÃ­cia percorreu fila, revisÃ£o, preparo e arquivamento
  privado na sessÃ£o; o console nÃ£o reportou erro.
- 77 testes de workspace, demonstraÃ§Ã£o e autenticaÃ§Ã£o passaram; um teste
  Playwright Python opcional foi ignorado porque o navegador interativo local
  foi usado nesta auditoria. Ruff, Django, migraÃ§Ãµes em dry-run e diff passaram.
- A inspeÃ§Ã£o nÃ£o cobre todas as Ã¡reas pÃºblicas, console, perfis, teclado/foco,
  contraste, carga/erro/vazio nem tarefas externas. Etapa em andamento; nÃ£o hÃ¡
  alegaÃ§Ã£o de aceite integrado ou aderÃªncia comercial final.

## 19/09/2026 â€” etapa 06: Triagem de Arquivos local (V-038)

- Revalidados quarentena privada, idempotÃªncia por entrega, cursor/leitura
  incremental simulados, bloqueio de binÃ¡rio nÃ£o verificado, scan/formato,
  revisÃ£o, cÃ³pia interna com hash e protocolo de agente Windows com escopo,
  hash, falha recuperÃ¡vel e repetiÃ§Ã£o. Nenhuma confirmaÃ§Ã£o ocorre sÃ³ pela
  intenÃ§Ã£o de arquivar.
- 72 testes de domÃ­nio e seis subtestes de protocolo Windows passaram; seis
  testes de interface/demo cobriram escopo de empresa, fila, bloqueio de arquivo
  nÃ£o verificado, cÃ³pia privada e isolamento por sessÃ£o. Ruff, Django,
  migraÃ§Ãµes em dry-run e diff passaram.
- Nenhuma caixa, OAuth, ClamAV, agente Windows, arquivo de cliente ou pasta
  real foi usada. Q-12â€“Q-25/Q-31, regras de catÃ¡logo/retenÃ§Ã£o/checklist e o
  piloto com prova no destino seguem pendentes; a etapa fica em andamento.

## 19/09/2026 â€” etapa 09: ConciliaÃ§Ã£o e Radar locais (V-037)

- Revalidado o processamento local de OFX/CSV/XLSX/PDF, hash e reimportaÃ§Ã£o,
  mapeamento, contas, movimentos, lanÃ§amentos equilibrados, evidÃªncia de
  conciliaÃ§Ã£o, exportaÃ§Ã£o/reexportaÃ§Ã£o auditÃ¡vel e retomada de execuÃ§Ã£o. A
  ambiguidade nÃ£o Ã© confirmada sÃ³ por data e valor.
- O Radar preserva fontes oficiais prÃ©-definidas, origem, atualizaÃ§Ã£o
  idempotente e falha isolada por fonte; a interface nÃ£o mostra o erro bruto.
  As fontes foram substituÃ­das por respostas controladas nos testes, portanto
  nÃ£o hÃ¡ alegaÃ§Ã£o de disponibilidade operacional.
- 46 testes de domÃ­nio passaram; o cenÃ¡rio de OCR em portuguÃªs foi ignorado
  porque Tesseract/modelo local nÃ£o existe. Quatro testes de interface/demo,
  Ruff, Django, dry-run de migraÃ§Ãµes e diff passaram. Sem dado de cliente,
  arquivo real, ERP, HTTP externo, custo ou deploy.
- Layouts aprovados, corpus/volume PostgreSQL, OCR, amostra de D-73, importaÃ§Ã£o
  conferida no destino e fontes reais do Radar continuam necessÃ¡rios. A etapa
  fica em andamento.

## 19/09/2026 â€” anÃ¡lise auditÃ¡vel de conclusÃ£o (V-036)

- Criada a matriz de evidÃªncias que liga as 14 etapas ao maior nÃ­vel provado, Ã s validaÃ§Ãµes e aos bloqueios concretos. O documento torna explÃ­cita a diferenÃ§a entre implementaÃ§Ã£o, validaÃ§Ã£o local, homologaÃ§Ã£o e venda.
- A matriz foi vinculada ao plano mestre e ao Ã­ndice de planejamento. A checagem de diff, Django e migraÃ§Ãµes passou; nÃ£o houve acesso externo, alteraÃ§Ã£o de ambiente ou custo.
- A anÃ¡lise mantÃ©m Q-33 como primeiro bloqueio de sequÃªncia e nÃ£o reclassifica nenhuma etapa incompleta como concluÃ­da.

## 19/09/2026 â€” etapa 07: demonstraÃ§Ã£o NFS-e local (V-035)

- Reconciliado o checklist com o comportamento que jÃ¡ existia desde V-005: ZIP fictÃ­cio por empresa, carteira inteira, manifesto de classificaÃ§Ãµes, filtro exclusivo por competÃªncia/emissÃ£o e atualizaÃ§Ã£o visual de acumulador permanecem restritos Ã  demonstraÃ§Ã£o e nÃ£o gravam decisÃ£o fiscal.
- Reexecutados 4 testes focados de NFS-e e a inspeÃ§Ã£o interativa da demonstraÃ§Ã£o criada em SQLite temporÃ¡rio. Datas DD/MM/AAAA foram normalizadas, o intervalo de setembro retornou os 24 itens da carteira, o acumulador manual transitou para 100% e a limpeza restaurou TransitÃ³ria a 0%; console sem erros.
- O banco e a conta temporÃ¡rios foram descartados apÃ³s a inspeÃ§Ã£o. Nenhum certificado, ADN, XML real, dado de cliente, pasta Windows ou provedor externo foi utilizado. A coleta e a homologaÃ§Ã£o fiscal seguem pendentes na etapa 07.

## 19/09/2026 â€” etapa 08: Central Integra Contador local (V-034)

- O checkout implementa DTE, DCTFWeb e PARCSN sob as decisÃµes D-38â€“D-42, com seleÃ§Ã£o de empresas aptas, autorizaÃ§Ã£o especÃ­fica de ciÃªncia, paginaÃ§Ã£o, cotaÃ§Ã£o/reserva/liquidaÃ§Ã£o e documento persistido. O transporte incerto nÃ£o Ã© repetido automaticamente.
- `uv run pytest tests/test_dte.py tests/test_dte_access.py tests/test_dte_dispatch.py tests/test_integra_client.py tests/test_integra_dctfweb.py tests/test_integra_parcelamento.py tests/test_parcelamento_operations.py -q`: 63 aprovados em 13,98 s. Ruff dos mÃ³dulos e testes envolvidos passou.
- NÃ£o houve configuraÃ§Ã£o de segredo, credencial, certificado, representaÃ§Ã£o, consulta, ciÃªncia DTE, declaraÃ§Ã£o, guia ou DAS real. O piloto Serpro, contrato/ambiente Q-28 e autorizaÃ§Ã£o de custo continuam obrigatÃ³rios; Q-36 mantÃ©m PARCSN como recorte Ãºnico.

## 19/09/2026 â€” etapa 10: controles locais de contrataÃ§Ã£o e cobranÃ§a (V-033)

- Auditoria confirmou que D-76/D-79 resolveram as regras Q-01â€“Q-06. O checkout separa contrato manual e Asaas, mede tokens inteiros por mÃ³dulo, reserva/liquida consumo de modo idempotente e fecha fatura por competÃªncia com preÃ§o congelado.
- `uv run pytest tests/test_platform_billing.py tests/test_platform_payments.py tests/test_token_billing.py tests/test_cica_contract_mfa.py tests/test_cica_operation_access.py -q`: 44 aprovados e 1 skip de concorrÃªncia PostgreSQL coberta em evidÃªncia histÃ³rica. Ruff dos arquivos de plataforma passou.
- NÃ£o houve conta, sandbox, credencial, cliente, cobranÃ§a, Pix, boleto, cartÃ£o ou webhook Asaas real. O cliente de criaÃ§Ã£o/operaÃ§Ã£o Asaas ainda nÃ£o existe; Q-08 e o ambiente Q-28 continuam bloqueando a homologaÃ§Ã£o.

## 19/09/2026 â€” etapa 05: escopo de conhecimento e treinamento (V-032)

- D-89 formalizou a estrutura tÃ©cnica de Ã¡rea (`geral`, contÃ¡bil, fiscal ou folha), empresa e perÃ­odo para fontes e exemplos. Registros existentes recebem o padrÃ£o geral; nÃ£o houve reclassificaÃ§Ã£o, exportaÃ§Ã£o ou exposiÃ§Ã£o de conteÃºdo.
- Fontes de uma empresa sÃ³ podem pertencer ao mesmo escritÃ³rio. A recuperaÃ§Ã£o por empresa recebe apenas suas fontes e as globais do escritÃ³rio, priorizando as especÃ­ficas; o contexto sem empresa exclui fontes de qualquer empresa. O manifesto QLoRA guarda esses metadados para manter sua proveniÃªncia auditÃ¡vel, mas o runner continua treinando somente com pergunta, resposta e fontes aprovadas.
- D-90 acrescentou modelo base, versÃ£o e hashes de manifesto/artefato Ã s avaliaÃ§Ãµes e versÃµes locais. Quando uma versÃ£o declara artefato, a publicaÃ§Ã£o recusa qualquer avaliaÃ§Ã£o com proveniÃªncia diferente; registros legados continuam legÃ­veis sem alegar vÃ­nculo. Vinte testes focados passaram.
- D-91 separou exemplos validados entre treino e avaliaÃ§Ã£o. O exportador seleciona um conjunto por vez, o hash da avaliaÃ§Ã£o Ã© registrado junto da avaliaÃ§Ã£o do adaptador e o runner QLoRA recusa o conjunto de avaliaÃ§Ã£o. Trinta e quatro testes focados passaram.
- D-92 adicionou retorno auditado de versÃ£o local: uma versÃ£o anterior sÃ³ Ã© reativada com avaliaÃ§Ã£o aprovada e proveniÃªncia compatÃ­vel, sem novo treino. Dezessete testes focados de publicaÃ§Ã£o/retorno passaram.
- `ruff` focado, migraÃ§Ãµes em dry-run e 26 testes de recuperaÃ§Ã£o, treinamento e runner passaram; a revalidaÃ§Ã£o integral fechou em 754 aprovados, 3 ignorados e 8 subtestes. NÃ£o houve chamada Claude, curadoria externa, modelo baixado, treino, GPU, publicaÃ§Ã£o ou custo. GovernanÃ§a de egressÃ£o e curadoria continuam em Q-08/Q-09/Q-11/Q-34.

## 19/09/2026 â€” anÃ¡lise integral e continuidade da etapa 04 (V-031)

- Revisados plano mestre, decisÃµes, validaÃ§Ãµes, inventÃ¡rio, documentaÃ§Ã£o de produto/tÃ©cnica, etapas e checkout. A anÃ¡lise consolidada registra objetivo, arquitetura, capacidades e limites em [analise-projeto-2026-09-19.md](analise-projeto-2026-09-19.md).
- A etapa 04 continua sendo o prÃ³ximo trabalho habilitado, mas nÃ£o pode receber adaptador Siescon sem o contrato Q-33. O material necessÃ¡rio Ã© versÃ£o/banco/mecanismo de leitura, ambiente e revogaÃ§Ã£o, schema/campos autorizados, identificador/cursor de empresa e layout de exportaÃ§Ã£o/importaÃ§Ã£o por canal seguro. NÃ£o houve conexÃ£o, solicitaÃ§Ã£o de segredo, leitura de dados ou arquivo fictÃ­cio Siescon.
- A estaÃ§Ã£o macOS recriou `.venv/` ignorado pelo Git com `uv sync --locked --all-extras`. A revalidaÃ§Ã£o encontrou 16 E501 e os corrigiu apenas com quebras de linha nos fluxos jÃ¡ existentes do agente e destino Windows. A primeira suÃ­te integral expÃ´s que o modo de biblioteca interna apagava o padrÃ£o de pastas Windows; o formulÃ¡rio passou a preservÃ¡-lo. Ruff, Django, dry-run de migraÃ§Ãµes e a suÃ­te integral passaram com 747 aprovados, 3 ignorados e 8 subtestes. V-031 contÃ©m os comandos e limites.
- Corrigidos os ponteiros vigentes que ainda apresentavam o escopo histÃ³rico da etapa 00 ou a etapa 01 como prÃ³ximo trabalho. NÃ£o foram alterados documentos histÃ³ricos nem inferidas regras de produto.

## 18/09/2026 â€” etapa 02: auditoria inicial de acesso e administraÃ§Ã£o

Etapa iniciada apÃ³s a conclusÃ£o tÃ©cnica da etapa 01. Auditoria local localizou cadastro, recuperaÃ§Ã£o, convite, MFA, escopo, contrato/teste, isolamento e console jÃ¡ implementados. A suÃ­te especÃ­fica fechou com 83 aprovados em 54,47 s (V-007). NÃ£o houve envio de e-mail, alteraÃ§Ã£o de cobranÃ§a nem integraÃ§Ã£o externa. Q-01â€“Q-06/Q-29 continuam condicionando as regras comerciais e a homologaÃ§Ã£o de e-mail; etapa segue aberta.

Cadastro inspecionado por Playwright em desktop e mÃ³vel: sem overflow, foco visÃ­vel e console limpo; sessÃµes fechadas. UI/UX Pro Max, Watermelon, referÃªncias SaaSFrame e Web Interface Guidelines aplicados conforme V-007. Sem mudanÃ§a de UI nesta auditoria.

D-76 aprovou as regras documentadas para implementaÃ§Ã£o e definiu `suporte@mewstack.com.br`. Implementados e-mails HTML de confirmaÃ§Ã£o, convite e recuperaÃ§Ã£o com texto de reserva; 62 testes e Ruff passaram (V-008). D-77 transferiu SMTP real, DNS e homologaÃ§Ã£o de entrega para a etapa 12; nenhum envio foi feito nesta fase.

Brevo definido como provedor SMTP transacional (D-78). A decisÃ£o nÃ£o configura conta, crÃ©dito, credenciais, domÃ­nio nem envio; tudo isso fica para a etapa 12.

## 18/09/2026 â€” retomada do plano (D-70)

Identificado o primeiro item pendente: build de treinamento na etapa 01. Corrigido o resumo desatualizado do plano mestre. D-71 manteve LlamaFactory como ferramenta interna e fixou a imagem oficial por digest. Corrigida a cÃ³pia invÃ¡lida do executor no Dockerfile; `cica-trainer:stage01` foi construÃ­do e o CLI iniciou (V-006). O digest tambÃ©m foi centralizado em `runtime/trainer/image.env` e incluÃ­do no CI; seu rebuild local passou. Sem modelo, treino ou GPU. Etapa segue aberta por Q-28/Q-30 e D-61.

Fedrizzi Contabilidade confirmado como ambiente disponÃ­vel para homologaÃ§Ã£o e proprietÃ¡rio definido como aprovador de cada mÃ³dulo (D-72). Faltam apenas acessos/amostras concretos por integraÃ§Ã£o e metas mensurÃ¡veis de aceite; etapa 01 continua aberta.

CritÃ©rios recomendados foram aprovados e registrados em D-73. Metas de aceite deixam de ser bloqueio; primeira homologaÃ§Ã£o Fedrizzi ainda depende da amostra e do acesso seguro da integraÃ§Ã£o que serÃ¡ exercitada. Etapa 01 segue aberta por D-61.

ValidaÃ§Ã£o integral posterior: 742 testes aprovados, 2 ignorados e 8 subtestes em 85,31 s; Django check, migrations dry-run e Ruff aprovados. CorreÃ§Ã£o D-74: inspeÃ§Ã£o segura do banco confirmou conector Fedrizzi `direct_odbc` e fonte DomÃ­nio local `ready`; nenhuma credencial, DSN ou dado empresarial foi exposto. A etapa 01 estÃ¡ concluÃ­da como validaÃ§Ã£o tÃ©cnica local; conexÃµes externas restantes pertencem Ã s prÃ³ximas etapas. EvidÃªncia V-006.

## 18/09/2026 â€” demonstraÃ§Ã£o NFS-e em ajuste

Pedido â€œmais bonitoâ€: refinado agrupamento, hierarquia, espaÃ§amento e estados visuais do filtro, mantendo D-69. InspeÃ§Ã£o desktop/mobile e evidÃªncias no complemento V-005. Sem nova regra de negÃ³cio.

Complemento D-69: substituÃ­do calendÃ¡rio nativo de emissÃ£o por digitaÃ§Ã£o brasileira e atalhos mensais. ValidaÃ§Ã£o cliente/servidor e filtragem dos dados antigos da demo corrigidas. EvidÃªncias e pesquisa no complemento V-005 de VALIDACOES.md. Etapa 07 continua aberta.

- RevisÃ£o visual posterior: CSS especÃ­fico da carteira, filtros em linha, acumulador com Ã­cone de ediÃ§Ã£o e foco, seleÃ§Ã£o destacada, adaptaÃ§Ã£o mÃ³vel e cache do JS atualizado. Playwright verificou claro/escuro, desktop/mobile, digitar/limpar/Enter e troca exclusiva do perÃ­odo. EvidÃªncia detalhada em V-005; nenhuma etapa homologada por esta revisÃ£o.

- Carteira demonstrativa passou a usar a emissÃ£o da NFS-e, com escolha exclusiva entre competÃªncia e intervalo de emissÃ£o.
- Download em lote separado em `Emitidas/CÃ“DIGO -/` ou `Tomadas/CÃ“DIGO -/`, com manifesto de classificaÃ§Ã£o; acumulador manual, TransitÃ³ria a 0% e classificadas da demonstraÃ§Ã£o a 97%.
- Corrigido Enter no acumulador: seleciona a nota e avanÃ§a o foco, sem tentar baixar uma seleÃ§Ã£o vazia.
- EvidÃªncia local, limites e inspeÃ§Ã£o Playwright em [V-005](../../VALIDACOES.md). Etapa 07 continua aberta.

## 17/09/2026 â€” etapa 01: estabilizaÃ§Ã£o tÃ©cnica parcial

- Ruff: 66 achados eliminados com formataÃ§Ã£o mecÃ¢nica e ordenaÃ§Ã£o de imports nas nove unidades apontadas.
- SeguranÃ§a de dependÃªncia: pypdf passou de 6.9.2 para 6.16.1; lockfile e requisitos foram atualizados. pip check e pip_audit aprovados; o pacote local Ã© ignorado pelo auditor por nÃ£o estar no PyPI.
- Base Django: check e dry-run de migrations aprovados; suÃ­te completa: **740 aprovados, 1 ignorado e 8 subtestes** em 70,07 s. Testes focados de token/faturamento/IA/fila/conciliaÃ§Ã£o: 66 aprovados.
- Agente Windows: service, configurador e MSI compilados; MSI de 79.285.770 bytes e checksum SHA-256 6ed0a1592fc3f0b5c5277e9dfc3ce8f27c000c6ca493cb3f5c245ac94c23f9b9 gerados em agent-windows/artifacts/.
- Ambiente atualizado em 18/09: Docker Desktop 4.91.0 e WSL 2.7.1 operacionais; PostgreSQL 17 e Redis 7.4 saudÃ¡veis por Compose. Migrations dos bancos principal e de conhecimento sem operaÃ§Ãµes pendentes. Worker Celery com pool `solo` consumiu tarefa via Redis; o pool `prefork` apresentou `WinError 5` no Windows, limitaÃ§Ã£o que nÃ£o representa o worker Linux de produÃ§Ã£o.
- CorreÃ§Ã£o PostgreSQL: aprovaÃ§Ã£o e exportaÃ§Ã£o de lanÃ§amentos usavam `FOR UPDATE` sobre joins opcionais; PostgreSQL rejeitava a consulta. Os locks foram restringidos ao `JournalEntry` principal, e 35 testes de conciliaÃ§Ã£o passaram no banco real. A suÃ­te crÃ­tica PostgreSQL fechou com 95 aprovados; uma regressÃ£o de quatro chamadas concorrentes com mesma chave confirmou um Ãºnico evento de consumo.
- Builds: `cica-backend:stage01` e `cica-multimodal:stage01` foram construÃ­das. O MSI do agente continua validado pelo checksum jÃ¡ registrado. A etapa 01 permanece aberta e bloqueada apenas por Q-37: referÃªncia LlamaFactory aprovada por digest para construir o runtime de treinamento. D-61 impede o encerramento antes disso. Ver [V-004](../../VALIDACOES.md) e [checklist](etapas/01-base-tecnica.md).

## 17/09/2026 â€” etapa 00: documentaÃ§Ã£o Ãºnica na raiz

Escopo limitado pelo responsÃ¡vel a **somente a primeira etapa (00)**. NÃ£o iniciadas correÃ§Ãµes de cÃ³digo ou demais etapas.

- Materializados [PLANO-MESTRE.md](../../PLANO-MESTRE.md), [DECISOES.md](../../DECISOES.md) e [VALIDACOES.md](../../VALIDACOES.md) na raiz, conforme solicitado.
- Registro D-01â€“D-45 preservado, inclusive distinÃ§Ã£o entre confirmado e apenas registrado; adicionados D-46â€“D-60 com fonte e alcance.
- Criados [14 arquivos de etapa com prompts](etapas/README.md), dependÃªncias, checklist, testes, aceite e limites; [inventÃ¡rio estÃ¡tico](inventario-conclusao.md) cobre mÃ³dulos, modelos, rotas/API, tarefas e serviÃ§os.
- Q-10 encerrada por D-50/D-51; demais perguntas agrupadas por dono/etapa e vinculadas sem duplicar decisÃµes. Nenhuma decisÃ£o comercial nova foi presumida.
- Corrigidas referÃªncias concorrentes e contradiÃ§Ãµes documentais: titularidade Serpro, coleta ADN, OAuth por escritÃ³rio, escopo da ConciliaÃ§Ã£o, disponibilidade Siescon e preparo da IA local.
- Resultados tÃ©cnicos anteriores Ã  ediÃ§Ã£o: 740 testes aprovados, 1 ignorado, 8 subtestes; Django e migrations dry-run sem pendÃªncias; 66 violaÃ§Ãµes Ruff ainda presentes. Ver V-001; nÃ£o sÃ£o novos testes de implementaÃ§Ã£o desta etapa.
- ConferÃªncia de documentos e conclusÃ£o: ver V-003 em VALIDACOES.md. Sem chamada paga, deploy, conexÃ£o a ERP, alteraÃ§Ã£o de banco ou treinamento real.

## HistÃ³rico anterior â€” preservar data e limites de cada entrada

Atualizado em 15/09/2026. A meta Ã© concluir cada mÃ³dulo da CICA pela tarefa real do escritÃ³rio, homologar dependÃªncias externas e sÃ³ entÃ£o liberar a oferta. Esta pÃ¡gina distingue trabalho local, teste simulado, validaÃ§Ã£o com fornecedor e aceite comercial. Cada linha descreve o estado **naquele marco**; resultados posteriores na mesma data substituem limites antigos. Para a fotografia atual, leia [estado operacional](estado-operacional.md), [decisÃµes](decisoes.md) e [dÃºvidas](duvidas-abertas.md).

| Data | Ãrea | MudanÃ§a ou prova local | Resultado e limite |
| --- | --- | --- | --- |
| 15/09 | Copiloto | Chave central `CICA_CLAUDE_API_KEY` lida do `.env`; polÃ­tica global e por escritÃ³rio; rota Claude disponÃ­vel antes do PC local e runtime local configurÃ¡vel para depois | 125 testes focados aprovados; transporte Claude ainda simulado. Chave nÃ£o estava configurada na Ãºltima inspeÃ§Ã£o e nenhuma chamada cobrada foi executada. Modelo completo, cotas, consentimento e egressÃ£o permanecem abertos. |
| 15/09 | Triagem | Entrada vendÃ¡vel definida como e-mail; rota principal mostra estado vazio, sem upload manual; provedor Gmail reconhecido no schema; cursor longo cifrado; revisÃ£o/download filtrados pelas empresas autorizadas do colaborador | 23 testes de domÃ­nio e 3 testes focados de rota aprovados. O serviÃ§o manual presente na Ã¡rvore de trabalho nÃ£o Ã© o fluxo aprovado; leitores Graph/Gmail/IMAP, quarentena antimalware, classificaÃ§Ã£o, destino Windows e checklist ainda faltam. |
| 15/09 | Oferta | PreÃ§o de Triagem removido do catÃ¡logo automÃ¡tico enquanto ela nÃ£o executa a entrada por e-mail e o arquivamento | As trÃªs regressÃµes comerciais do primeiro teste completo foram resolvidas. PreÃ§o final e franquias continuam decisÃ£o do responsÃ¡vel. |
| 15/09 | SuÃ­te completa | `uv run pytest -q` apÃ³s schema Gmail, escopo de revisÃ£o/download e textos de interface | **469 aprovados, 1 ignorado, 1 falha** em 29,45 s. Falta `.github/workflows/deploy-cobalchini.yml`; os testes dependem tambÃ©m de `.github/workflows/ci.yml`. |
| 15/09 | Lint e migrations | Ruff nos arquivos Python alterados; `manage.py check`; `makemigrations --check --dry-run`; `manage.py migrate triage` | Ruff, check e detecÃ§Ã£o de migrations passaram; a migration 0003 de provedor Gmail/cursor cifrado foi aplicada no banco local. |
| 15/09 | SeguranÃ§a da Triagem | POST de aprovaÃ§Ã£o e download do protÃ³tipo manual bloqueados nas rotas; detalhe informa que o anexo depende de e-mail e verificaÃ§Ã£o de seguranÃ§a | Testes focados 4/4; nenhum binÃ¡rio nÃ£o verificado pode ser servido por essas rotas. O serviÃ§o interno manual ainda existe em trabalho local e nÃ£o deve ser tratado como fluxo aprovado. |
| 15/09 | Interface | Estado vazio de e-mail, polÃ­tica Claude e detalhe de arquivo revisados pelas diretrizes web; inspeÃ§Ã£o Playwright em desktop/mobile, teclado, foco, erro e overflow | [Auditoria de interface](auditoria-ui-2026-09-15.md) registra telas e limites. Nome de arquivo longo e alvos mÃ³veis foram corrigidos; OAuth/conexÃ£o em carga nÃ£o pÃ´de ser alcanÃ§ado. |
| 15/09 | SuÃ­te completa apÃ³s bloquear o protÃ³tipo | `uv run pytest -q`; `manage.py check`; `makemigrations --check --dry-run`; Ruff focado; `git diff --check` | **470 aprovados, 1 ignorado, 1 falha** em 29,22 s. A Ãºnica falha continua sendo o workflow `.github/workflows/deploy-cobalchini.yml` ausente. Check, migrations, Ruff e whitespace passaram. |
| 15/09 | Contrato HTTP Sonnet | Teste com `urlopen` inteiramente simulado para `/v1/messages`, cabeÃ§alhos Anthropic, `claude-sonnet-5`, limite de saÃ­da, esforÃ§o baixo e ausÃªncia de `temperature` | 1 teste focado aprovado, Ruff passou. Nenhuma chamada externa cobrada foi feita; a chave real, resposta do fornecedor, uso e custo ainda dependem de um piloto autorizado. |
| 15/09 | SuÃ­te completa apÃ³s contrato Sonnet | `uv run pytest -q` | **471 aprovados, 1 ignorado, 1 falha** em 29,91 s. Permanece somente o workflow Cobalchini ausente. |
| 15/09 | Entrega Cobalchini preparada | Workflows CI e deploy manual protegido; imagem por digest, verificaÃ§Ã£o Cosign, Compose com arquivo de ambiente externo, migration, readiness, rollback e confirmaÃ§Ã£o ao CRMew | `tests/test_deployment_config_django.py`: 7 aprovados. NÃ£o houve deploy; Docker nÃ£o estÃ¡ instalado neste PC, portanto o Compose nÃ£o foi executado localmente. O host, as variÃ¡veis protegidas, a chave pÃºblica e a aprovaÃ§Ã£o de ambiente ainda precisam de validaÃ§Ã£o operacional. |
| 15/09 | SuÃ­te completa apÃ³s automaÃ§Ã£o de entrega | `uv run pytest -q` | **472 aprovados, 1 ignorado, 2 subtests aprovados** em 36,72 s. A ausÃªncia do workflow Cobalchini deixou de falhar; o teste de navegador Python Ã© opcional porque a inspeÃ§Ã£o visual usa Playwright MCP. |
| 15/09 | Webhook Asaas | Endpoint sem CSRF, oculto sem token, valida `asaas-access-token`, JSON e identificador do evento; deduplica pelo ID do Asaas e nÃ£o altera contrato manual ou ciclo de acesso | 13 testes focados de cobranÃ§a passaram; migration 0026 foi aplicada no banco local. Nenhum cliente, cobranÃ§a, webhook ou chamada ao Asaas foi criado externamente. |
| 15/09 | SuÃ­te completa apÃ³s receptor Asaas | `uv run pytest -q` | **475 aprovados, 1 ignorado, 2 subtests aprovados** em 36,96 s. O teste de navegador Python permanece opcional; as telas alteradas foram exercitadas pelo Playwright MCP conforme auditoria registrada. |
| 15/09 | Claude, chave real sem geraÃ§Ã£o | `configure_claude_local_key` e novo `verify_claude_token_endpoint` com texto sintÃ©tico e endpoint **gratuito** `/v1/messages/count_tokens` | Ambos passaram: chave aceita para `claude-sonnet-5`, 16 tokens contados. NÃ£o houve resposta da IA, uso de dado de cliente ou chamada cobrada. ConfiguraÃ§Ã£o global e cotas ainda precisam de ativaÃ§Ã£o/validaÃ§Ã£o. |
| 15/09 | Claude, teste pago preparado | `verify_claude_messages` usa uma mensagem sintÃ©tica, 64 tokens de saÃ­da no mÃ¡ximo e exige `--cost-approved`; transporte e bloqueio sem aprovaÃ§Ã£o tÃªm teste simulado | Comando sem flag foi recusado antes de qualquer acesso Ã  API. Ainda **nÃ£o foi executado com a chave real**; estimativa e condiÃ§Ã£o de aprovaÃ§Ã£o constam em [operaÃ§Ã£o da IA](ia-operacao.md). |
| 15/09 | ConexÃ£o das caixas | Pesquisa de documentaÃ§Ã£o oficial Microsoft, Google e Exchange; [jornada simples](conexao-caixas-email.md) documentada | A hipÃ³tese inicial de app OAuth central foi substituÃ­da pelo esclarecimento D-23: cada escritÃ³rio configura seu prÃ³prio aplicativo e consente sua caixa. IMAP genÃ©rico usa assistente TLS. Google pessoal requer decisÃ£o de verificaÃ§Ã£o do escopo restrito. |
| 15/09 | SuÃ­te completa apÃ³s a validaÃ§Ã£o da chave | `uv run pytest -q`, Ruff focado, `manage.py check` e `makemigrations --check --dry-run` | **478 aprovados, 1 ignorado, 2 subtests aprovados** em 30,83 s; check/migrations passaram. Esse marco antecede a chamada paga autorizada e o OAuth local registrados abaixo. |
| 15/09 | Claude, geraÃ§Ã£o autorizada | **Uma** chamada sintÃ©tica a `/v1/messages` com `claude-sonnet-5`, esforÃ§o baixo e atÃ© 64 tokens de saÃ­da, apÃ³s aprovaÃ§Ã£o especÃ­fica de custo do responsÃ¡vel | A Anthropic retornou texto, 16 tokens de entrada e 64 de saÃ­da; custo calculado US$ 0,000672 antes de cÃ¢mbio/impostos. Nenhum dado de cliente foi enviado; polÃ­ticas de cotas e uso do Copiloto por escritÃ³rio ainda nÃ£o foram homologados. NÃ£o repetir sem nova aprovaÃ§Ã£o especÃ­fica de custo. |
| 15/09 | OAuth da Triagem, trabalho local | BotÃµes Microsoft/Google, callback com `state`/PKCE, prova de leitura, credential cifrada por escritÃ³rio e desconexÃ£o; fluxo mantÃ©m sincronizaÃ§Ã£o desligada | 5 testes de OAuth passaram. Sem aplicativos de provedor registrados e sem caixas reais de teste; IMAP e leitura incremental ainda faltam. A autorizaÃ§Ã£o da caixa nÃ£o Ã© a prova de processamento dos anexos. |
| 15/09 | SuÃ­te e interface apÃ³s OAuth | `uv run pytest -q`, Ruff focado, `manage.py check`, `makemigrations --check --dry-run`, `git diff --check`; Playwright MCP em 1689 Ã— 1005 e 390 Ã— 844 | **483 aprovados, 1 ignorado, 2 subtests aprovados** em 29,61 s; checagens passaram. Estado vazio, caixa autorizada e desconectada, guia, confirmaÃ§Ã£o, teclado, foco, overflow e console foram inspecionados. [RevisÃ£o crÃ­tica](auditoria-triagem-oauth-2026-09-15.md) delimita estados externos nÃ£o alcanÃ§ados. |
| 15/09 | CorreÃ§Ã£o do estado de erro | Um erro da caixa aparecia como â€œCaixa autorizadaâ€ na faixa de status; agora indica erro/recebimento indisponÃ­vel e passo de reconexÃ£o/suporte | Estado reinspecionado em desktop/celular; 6 testes OAuth passaram, incluindo a regressÃ£o de status. SuÃ­te completa final: **484 aprovados, 1 ignorado, 2 subtests aprovados** em 31,61 s. |
| 15/09 | ConexÃ£o IMAP local | FormulÃ¡rio guiado, DNS pÃºblico com IP fixado, TLS com certificado/hostname verificados, `select(readonly=True)`/UID, credencial cifrada, throttling e recebimento desligado apÃ³s conectar | 7 testes IMAP focados passaram, incluindo DNS misto/privado e pinagem do socket. FormulÃ¡rio vazio/erro e espera sintÃ©tica inspecionados em desktop/mobile; sem servidor real nem anexos. [RevisÃ£o crÃ­tica](auditoria-triagem-oauth-2026-09-15.md). |
| 15/09 | SuÃ­te apÃ³s assistente IMAP | `uv run pytest -q`, Ruff focado, format dos arquivos novos, `node --check`, Django check e migrations | **490 aprovados, 1 ignorado, 2 subtests aprovados** em 29,49 s. A suÃ­te antecede somente um novo teste de pinagem de socket, que passou nos 7 testes IMAP focados; nÃ£o houve alteraÃ§Ã£o do cÃ³digo de produÃ§Ã£o depois. |
| 15/09 | RenovaÃ§Ã£o OAuth preparatÃ³ria | Refresh Microsoft/Google com segredo cifrado por escritÃ³rio e rotaÃ§Ã£o quando o provedor devolve novo refresh token; credencial desconectada/incompatÃ­vel bloqueada antes do transporte | 8 testes OAuth focados passaram com transporte simulado. Sem app registrado, token real, polling ou persistÃªncia de rotaÃ§Ã£o pelo leitor. Fontes oficiais registradas em [conexÃ£o de caixas](conexao-caixas-email.md). |
| 15/09 | SuÃ­te apÃ³s renovaÃ§Ã£o OAuth | `uv run pytest -q`, Ruff/format focados, Django check e migrations | **493 aprovados, 1 ignorado, 2 subtests aprovados** em 33,73 s; nenhum arquivo de migration novo. |
| 15/09 | PadrÃ£o Windows por empresa | FunÃ§Ã£o pura `Nome [DomÃ­nio cÃ³digo]`, sem escrita, com cÃ³digo exato obrigatÃ³rio, limpeza de caracteres invÃ¡lidos no nome e limite de 160 unidades UTF-16 | 5 testes focados e 6 subtests passaram. Falta confirmar fonte do nome/renomeaÃ§Ã£o, raiz no agente, Ã¡rvore abaixo da empresa, caminho absoluto, colisÃµes case-insensitive, links/junctions e hash. [PadrÃ£o](padrao-pastas-windows.md). |
| 15/09 | SuÃ­te e confirmaÃ§Ã£o da desconexÃ£o | `uv run pytest -q` apÃ³s o padrÃ£o Windows; confirmaÃ§Ã£o da caixa passou a modal com consequÃªncia e aÃ§Ã£o de manter conexÃ£o em primeiro foco. Playwright MCP em desktop/mobile e teclado | **498 aprovados, 1 ignorado, 8 subtestes aprovados** em 42,71 s. Modal, Tab/Enter/Escape, foco de retorno, POST real local, flash, largura mÃ³vel e console sem erro foram vistos em caixa sintÃ©tica. QA removido, aba e servidor fechados. Sem revogaÃ§Ã£o no provedor ou caixa real. [Auditoria](auditoria-triagem-oauth-2026-09-15.md). |

| 15/09 | Fedrizzi e console | Consulta local da organizaÃ§Ã£o `fedrizzi-contabilidade`, ordenaÃ§Ã£o dos 8 recentes e Playwright no painel/detalhe | Fedrizzi permanecia ativa; a ordenaÃ§Ã£o alfabÃ©tica a excluÃ­a apÃ³s QA. Recentes agora ordena por criaÃ§Ã£o. SÃ³ a organizaÃ§Ã£o QA sintÃ©tica `qa-operacional-20260915` foi desativada; os dados fiscais protegidos foram preservados. |
| 15/09 | Segundo fator e configuraÃ§Ã£o | Testes de saÃ­da com e sem `next`; Playwright em conta sintÃ©tica: confirmaÃ§Ã£o MFA, saÃ­da dos cÃ³digos e abertura de `/platform/configuracoes/` | Link de continuar passa a ser rota resolvida; cenÃ¡rio com destino explÃ­cito chegou Ã s configuraÃ§Ãµes. A configuraÃ§Ã£o mostra quais quatro variÃ¡veis Serpro centrais faltam. CÃ³digos/segredos MFA nÃ£o foram registrados em evidÃªncia. |
| 15/09 | Central Integra e caixa DTE | Escolha DTE/Parcelamentos/DCTFWeb, busca por DomÃ­nio e seleÃ§Ã£o em carteira Fedrizzi de 562 empresas; Playwright desktop/mobile e testes locais | A primeira iteraÃ§Ã£o selecionava as 562. A inspeÃ§Ã£o de dados revelou 8 sem CNPJ; a versÃ£o atual marca sÃ³ as **554 aptas** com 20 linhas visÃ­veis e mostra a exclusÃ£o/cadastro. Busca `DomÃ­nio 323` mostrou 1 resultado. O preparo nÃ£o chamou Serpro. Parcelamentos e consulta DCTFWeb seguem sem implementaÃ§Ã£o externa. |
| 15/09 | Guias/DCTFWeb primeiro uso | Playwright com sessÃ£o de suporte Fedrizzi em desktop e 390 Ã— 844, Tab/foco, link da conexÃ£o | Estado vazio corrigido aparece com caminho `/app/configuracoes/#dominio`, que abriu no navegador; sem overflow. Dados sÃ£o obrigaÃ§Ãµes locais DomÃ­nio, nÃ£o declaraÃ§Ã£o Serpro. NFS-e e ConciliaÃ§Ã£o vazias tambÃ©m ganharam prÃ³ximos passos; estados corrigidos precisam de reinspeÃ§Ã£o separada. |
| 16/09 | Carteiras operacionais de Guias, NFS-e e Radar | Pesquisa global, filtros de pendÃªncia/situaÃ§Ã£o, atalhos para filas e links ao caso exato; formulÃ¡rio compartilhado refeito para largura Ãºtil e celular | **611 testes aprovados, 1 ignorado e 8 subtestes aprovados**. Playwright confirmou controles de 44 px e reorganizaÃ§Ã£o responsiva em Guias, NFS-e e Radar, sem erros de console nos estados fictÃ­cios alcanÃ§ados. IntegraÃ§Ãµes externas continuam dependendo de homologaÃ§Ã£o real. |
| 16/09 | Certificados e cadastro mÃ³vel de empresas | Fila de vencimento/cobertura da carteira, pesquisa por empresa e DomÃ­nio, empresa exata como prÃ³ximo passo; tabelas viram cartÃµes no celular | A demo passou a simular cobertura somente na sessÃ£o, sem aceitar PFX/senha nem gravar na organizaÃ§Ã£o central. Playwright confirmou desktop, 390 Ã— 844, modal, foco, recarga da sessÃ£o, controles de 44 px e zero erro de console. **613 testes aprovados, 1 ignorado e 8 subtestes aprovados** antes do Ãºltimo ajuste apenas estrutural de cartÃµes. |
| 15/09 | SuÃ­te apÃ³s Central, MFA e estados vazios | `uv run pytest -q`; Ruff Python focado; `manage.py check` | **512 aprovados, 1 ignorado, 8 subtestes aprovados** em 38,15 s; Ruff e Django check passaram. Testes simulados e telas vazias nÃ£o homologam Serpro, ADN ou escritÃ³rios reais. |
| 15/09 | Triagem substitui Jornadas no catÃ¡logo e contratos de teste | MigraÃ§Ã£o local; `uv run pytest -q`, `manage.py check`, `makemigrations --check --dry-run`; consulta read-only do banco local | **515 aprovados, 1 ignorado, 8 subtestes aprovados** em 32,16 s; check/migraÃ§Ãµes passaram. Banco local: 0 jornadas, 0 habilitaÃ§Ãµes Jornadas, 6 habilitaÃ§Ãµes Triagem, 0 contratos/planos com Jornadas. O simulador legado foi removido. Ruff focado passou; Ruff global ainda aponta 9 problemas preexistentes fora desta troca. Sem homologaÃ§Ã£o de caixa real. |
| 15/09 | TarifaÃ§Ã£o oficial Integra Contador | Playwright no [produto da Loja Serpro](https://loja.serpro.gov.br/integra-contador/product/integracontador), aba â€œPreÃ§oâ€, e leitura do [catÃ¡logo oficial de serviÃ§os](https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/catalogo_de_servicos/) | A faixa 1 vigente exibiu R$ 0,24/consulta, R$ 0,32/emissÃ£o e R$ 0,40/declaraÃ§Ã£o; faixas 2â€“8 diminuem. O catÃ¡logo classifica lista/detalhe da Caixa, recibo/declaraÃ§Ã£o completa DCTFWeb e consultas de Parcelamentos como **Consultar**, e as guias DCTFWeb/Parcelamentos como **Emitir**. A fatura Mewstack ainda precisa confirmar que o **Tipo** do catÃ¡logo determina a categoria faturada, sobretudo para o indicador **Monitorar**. O responsÃ¡vel decidiu usar faixa 1 para pesos. Nenhuma contrataÃ§Ã£o ou chamada paga foi feita. |
| 15/09 | OAuth configurado pelo escritÃ³rio | MigraÃ§Ã£o `triage.0004` aplicada localmente; Microsoft/Workspace usam app OAuth por escritÃ³rio com segredo cifrado e vÃ­nculo da caixa; Gmail pessoal usa caminho central Mewstack separado, gated por `TRIAGE_GOOGLE_PERSONAL_VERIFIED` | 14 testes OAuth locais passaram, incluindo escolha central quando hÃ¡ app Workspace, rejeiÃ§Ã£o de endereÃ§o Workspace no caminho pessoal e rejeiÃ§Ã£o de Gmail pessoal no caminho Workspace. Sem app externo registrado, retorno HTTPS de produÃ§Ã£o ou caixa real. O guia foi inspecionado em desktop/mobile e o formulÃ¡rio positivo/erro com QA sintÃ©tico. |
| 15/09 | SuÃ­te apÃ³s OAuth por escritÃ³rio e UI de conexÃ£o | `uv run pytest -q`, Ruff focado, `manage.py check`, verificaÃ§Ãµes de sintaxe JavaScript | **520 aprovados, 1 ignorado, 8 subtestes aprovados** em 41,92 s. Os fornecedores externos foram simulados; [auditoria renderizada](auditoria-triagem-aplicativos-2026-09-15.md) delimita os estados vistos. |
| 15/09 | DemonstraÃ§Ã£o pÃºblica sob controle do usuÃ¡rio | Removido ciclo automÃ¡tico de mÃ³dulos; corrigido bloco numÃ©rico da Triagem; abas acessÃ­veis com seleÃ§Ã£o por seta/Home/End e URL `?demo=...` | Playwright desktop 1366 Ã— 900 e celular 390 Ã— 844: tab/painel permaneceram iguais apÃ³s 6 segundos, foco visÃ­vel, rolagem horizontal ausente e console sem erros na pÃ¡gina normal. A demonstraÃ§Ã£o Ã© ilustrativa e nÃ£o prova operaÃ§Ãµes externas. |
| 15/09 | VerificaÃ§Ã£o final desta rodada | `uv run pytest -q`, Ruff nos arquivos Python alterados, `makemigrations --check --dry-run`, `node --check` dos dois scripts e `git diff --check`; [diretrizes Vercel atuais](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) reaplicadas aos arquivos de interface alterados | **521 aprovados, 1 ignorado e 8 subtestes aprovados** em 40,47 s. Nenhuma nova migraÃ§Ã£o detectada, scripts vÃ¡lidos e sem erros materiais na revisÃ£o estÃ¡tica da interface. Playwright desta rodada inspecionou guia OAuth e demonstraÃ§Ã£o em desktop/mobile; estados externos nÃ£o foram alcanÃ§ados. Abas Playwright fechadas. Conta/aplicativo/ativaÃ§Ã£o de mÃ³dulo QA desta rodada removidos; conta de plataforma QA desativada, senha inutilizada e 2 sessÃµes de suporte abertas fechadas. Fedrizzi permaneceu ativa e intocada. |
| 15/09 | Entrada de anexos e leitor IMAP incremental | `triage.0005` aplicada localmente; teste com IMAP sintÃ©tico, MIME com anexo, data interna antes/depois do marco, SELECT readonly, `BODY.PEEK[]`, UIDVALIDITY/cursor, reenvio e isolamento de dois escritÃ³rios | **525 aprovados, 1 ignorado e 8 subtestes aprovados** em 34,73 s. O mesmo arquivo em mensagens distintas gera duas entregas em quarentena atÃ© a polÃ­tica Q-20; repetir a mesma mensagem+parte nÃ£o duplica. Caminho fÃ­sico `.bin` nÃ£o usa extensÃ£o recebida. Sem caixa real, ativaÃ§Ã£o pelo escritÃ³rio, agenda, scanner antimalware ou leitores Graph/Gmail; nenhum e-mail externo foi acessado. |
| 15/09 | Veredito antimalware em quarentena | `triage.0006` aplicada localmente; adaptador candidato ClamAV [INSTREAM oficial](https://docs.clamav.net/manual/Usage/ClamdProtocol.html) somente por socket Unix local ou TCP loopback; teste com socket sintÃ©tico limpo, resposta incompleta, scanner ausente e detecÃ§Ã£o de ameaÃ§a | **528 aprovados, 1 ignorado e 8 subtestes aprovados** em 36,47 s. AmeaÃ§a confirmada rejeita o anexo; falha fica em quarentena com veredito persistente; resultado limpo tambÃ©m fica em quarentena atÃ© aprovaÃ§Ã£o da polÃ­tica de formatos/assinaturas. Nenhum daemon ClamAV estÃ¡ instalado neste PC, nenhuma varredura real foi homologada e nenhum recurso externo ou custo foi criado. |
| 15/09 | Leitor Microsoft Graph incremental | [Delta e anexos oficiais](https://learn.microsoft.com/en-us/graph/api/message-delta?view=graph-rest-1.0) lidos; `poll_graph_mailbox` exercitado com duas pÃ¡ginas, arquivo inline, link de outro domÃ­nio, reenvio e arquivo acima de 25 MB em transporte sintÃ©tico | **531 aprovados, 1 ignorado e 8 subtestes aprovados** em 37,55 s. O cursor avanÃ§ou apenas apÃ³s a pÃ¡gina completa; link externo e anexo grande nÃ£o avanÃ§aram o checkpoint. IDs imutÃ¡veis sÃ£o pedidos em cada chamada. O leitor lista anexos mesmo quando `hasAttachments=false`, conforme a [semÃ¢ntica oficial da mensagem](https://learn.microsoft.com/en-us/graph/api/resources/message?view=graph-rest-1.0). Sem app registrado/consentimento/caixa real, projeÃ§Ã£o `$select` e limites de um tenant real ainda requerem piloto; nenhuma chamada Graph externa foi feita. |
| 15/09 | Leitor Gmail/Workspace incremental | [SincronizaÃ§Ã£o e expiraÃ§Ã£o oficiais](https://developers.google.com/workspace/gmail/api/guides/sync), [histÃ³rico](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list) e [anexos](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages.attachments/get) pesquisados; `poll_gmail_mailbox` testado com snapshot `historyId`, listagem paginada, eventos `messagesAdded`/`labelsAdded`, 404, replay no meio da pÃ¡gina e anexo grande com transporte sintÃ©tico | **535 aprovados, 1 ignorado e 8 subtestes aprovados** em 36,73 s. Checkpoint apÃ³s todos os anexos da pÃ¡gina; 404 reinicia full sync pelo novo snapshot sem perder entregas jÃ¡ recebidas. Nenhuma chamada Gmail externa foi feita; app central pessoal ainda depende de registro/verificaÃ§Ã£o Google e caixas reais de consentimento/piloto. |
| 15/09 | ExecuÃ§Ã£o periÃ³dica da Triagem | `triage.dispatch_active_mailboxes` incluÃ­da no Celery Beat a cada 5 minutos; fila apenas caixas com escritÃ³rio ativo, caixa ativa/status ativo e data inicial; worker usa lease com token e prazo para impedir sobreposiÃ§Ã£o e permitir recuperaÃ§Ã£o de crash; flag `TRIAGE_EMAIL_POLL_ENABLED=false` Ã© o padrÃ£o | **539 aprovados, 1 ignorado e 8 subtestes aprovados** em 36,55 s. Testes cobrem rotina desligada sem chamada ao provedor, seleÃ§Ã£o de caixas, execuÃ§Ã£o simultÃ¢nea bloqueada e falha saneada com lease liberada. NÃ£o hÃ¡ caixa real ativada nem autorizaÃ§Ã£o de custo para ligar a flag. A cadÃªncia de 5 min Ã© tÃ©cnica e configurÃ¡vel antes do piloto; SLA comercial, monitoramento e polÃ­tica de retentativa ainda nÃ£o foram aprovados. |
| 15/09 | Falhas e retentativas da Triagem | Conforme [Graph](https://learn.microsoft.com/en-us/graph/errors) e [Gmail](https://developers.google.com/workspace/gmail/api/guides/handle-errors), 429/5xx e indisponibilidade de rede recebem estado transitÃ³rio com backoff exponencial (5 min atÃ© 6 h, respeitando `Retry-After` atÃ© 24 h); scheduler pula caixa antes de `poll_retry_after`; credencial/contrato/dados invÃ¡lidos deixam caixa em erro para intervenÃ§Ã£o. IMAP separa socket/timeout de recusa do provedor. Migration `triage.0008` aplicada localmente | **544 aprovados, 1 ignorado e 8 subtestes aprovados** em 36,97 s. Cursor nÃ£o avanÃ§ou em falhas sintÃ©ticas e lease foi liberada. A tela entÃ£o ainda mostrava â€œrecebimento indisponÃ­velâ€ para caixa ativa com falha transitÃ³ria e â€œprecisa reconectarâ€ para qualquer erro permanente, mesmo quando a causa podia ser outra; ver revisÃ£o posterior da lista. Nenhuma consulta externa foi feita. |
| 15/09 | Lista operacional das caixas da Triagem | `present_mailbox` separa configuraÃ§Ã£o, leitura, retentativa, erro e desconexÃ£o; `triage.html` mostra Ãºltima/prÃ³xima consulta, remÃ©dio e estado vazio correto. `ui-ux-pro-max`, `watermelon-ui`, referÃªncias SaaSFrame, fonte atual Vercel e Playwright MCP foram consultados; [auditoria dos estados](auditoria-triagem-estados-caixas-2026-09-15.md) registra evidÃªncia e limites. | `uv run pytest -q`: **545 aprovados, 1 ignorado, 8 subtestes aprovados** em 36,60 s; Ruff e `manage.py check` passaram. Playwright desktop/mobile/escuro inspecionou somente caixas sintÃ©ticas, com console limpo; abas e servidor de QA fechados. AtivaÃ§Ã£o pelo escritÃ³rio, provedores reais e fila de anexos ainda nÃ£o foram validados. |
| 15/09 | Fila operacional da Triagem | Lista de anexos recebidos acima da conexÃ£o dos provedores, com etapa, seguranÃ§a, origem, filtro por GET e paginaÃ§Ã£o de 20; administrador vÃª itens ainda sem empresa e operador apenas suas empresas. Detalhe segue a mesma regra; download nÃ£o verificado continua bloqueado. [Auditoria das caixas e fila](auditoria-triagem-estados-caixas-2026-09-15.md) registra referÃªncias e inspeÃ§Ã£o. | `uv run pytest -q`: **546 aprovados, 1 ignorado, 8 subtestes aprovados** em 39,36 s; `manage.py check`, Ruff e `diff --check` passaram. Playwright desktop/mobile/claro/escuro testou trÃªs anexos sintÃ©ticos, filtro, vazio, foco e console sem erros/avisos; aba/servidor de QA fechados. NÃ£o houve anexo nem scanner real; classificaÃ§Ã£o, revisÃ£o e arquivamento permanecem pendentes. |
| 15/09 | Caixa DTE: separar abertura incerta da fila a abrir | Filtros/contadores excluem `reading`/`unknown` e ciÃªncia jÃ¡ observada de â€œA abrirâ€; a fila pendente mostra estados especÃ­ficos, links de acesso, filtro vazio correto e selects/indicadores legÃ­veis no escuro. â€œSelecionar todasâ€ foi inspecionado sem envio. [Auditoria DTE](auditoria-dte-fila-incerta-2026-09-15.md) registra pesquisa Serpro, referÃªncias SaaS e limites. | `uv run pytest -q`: **547 aprovados, 1 ignorado, 8 subtestes aprovados** em 37,35 s; 11 testes focados DTE/ciÃªncia, Ruff e `manage.py check` passaram. Playwright desktop/mobile/claro/escuro: quatro mensagens sintÃ©ticas, fila, filtro, aviso jurÃ­dico, foco, selecionador local; console final 0 erros/avisos, aba/servidor fechados. Contrato e ciÃªncia Serpro reais nÃ£o foram testados. |

| 15/09 | Caixa DTE: continuar pÃ¡ginas por empresa | Ponteiro Serpro salvo por item; operador prepara uma Ãºnica continuaÃ§Ã£o na prÃ³pria tabela, que entra na fila para cotaÃ§Ã£o/autorizaÃ§Ã£o de consumo individual. Formato de atÃ© 24 dÃ­gitos pesquisado na documentaÃ§Ã£o oficial; [auditoria da paginaÃ§Ã£o](auditoria-dte-paginacao-2026-09-15.md). | `uv run pytest -q`: **550 aprovados, 1 ignorado, 8 subtestes aprovados** em 36,34 s. Playwright desktop/mobile: aÃ§Ã£o/foco/estado apÃ³s POST, sem overflow do documento nem erros/avisos no console; cenÃ¡rio SQLite, aba e servidor encerrados. Nenhuma chamada paga ou resposta Serpro real foi feita. |

| 15/09 | Pesquisa e leitores de Parcelamentos | Cinco serviÃ§os PARCSN ordinÃ¡rio pesquisados nas pÃ¡ginas oficiais e registrados no catÃ¡logo; parsers locais de pedidos, detalhe, pagamentos, parcelas disponÃ­veis e DAS base64 limitam tamanho, conferem acordo e formato. [Pesquisa Parcelamentos](pesquisa-parcelamentos-integra-2026-09-15.md). | `uv run pytest -q tests/test_integra_parcelamento.py tests/test_integra_client.py`: **23 aprovados**; Ruff passou. Apenas payloads sintÃ©ticos: sem fila, autorizaÃ§Ã£o, armazenamento, UI, chamada Serpro ou emissÃ£o real. Modalidades da versÃ£o vendÃ¡vel aguardam escolha do responsÃ¡vel. |

| 15/09 | Carteira tÃ©cnica de tokens por mÃ³dulo | `TokenPriceBook`/rates/pesos/medidores/eventos e `token_billing.py` adicionados; reserva local com preÃ§o comum, franquia prÃ³pria, teto global e idempotÃªncia. `close_competence` cria uma fatura com linhas por mÃ³dulo sÃ³ apÃ³s flag e tabela ativa; recusa medidor legado misturado. GravaÃ§Ãµes normais congelam preÃ§o, franquia e pesos apÃ³s aceite. Flag `TOKEN_BILLING_ENABLED=false` no padrÃ£o. | `uv run pytest -q`: **559 aprovados, 1 ignorado, 8 subtestes aprovados** em 38,57 s; 5 testes focados de tokens, Ruff e migration check passaram apÃ³s a mudanÃ§a final de proteÃ§Ã£o. Valores e escritÃ³rios sintÃ©ticos, sem cobranÃ§a externa. Ainda nÃ£o hÃ¡ preÃ§os aprovados nem mÃ³dulos migrados para essa carteira; testar concorrÃªncia, QuerySet.update, retry/estorno, UX e fatura real antes de habilitar. |

| 15/09 | Fechamento mensal seguro | Beat diÃ¡rio Ã s 00:05 agora fecha sempre o Ãºltimo mÃªs completo; chamada manual ao mÃªs atual/futuro Ã© recusada. Fatura aguarda eventos/saldos reservados, e cotaÃ§Ã£o/reserva novas sÃ£o bloqueadas apÃ³s faturar a competÃªncia. Locks por organizaÃ§Ã£o alinham reserva, liquidaÃ§Ã£o e fechamento. [Auditoria do fechamento](auditoria-fechamento-competencia-2026-09-15.md). | `uv run pytest -q`: **563 aprovados, 1 ignorado, 8 subtestes aprovados** em 39,51 s; 18 testes focados de billing/token/tasks e Ruff passaram. Sem cobranÃ§a externa. Uma reserva pendente ainda interrompe a rodada dos escritÃ³rios seguintes; console individual e prova concorrente PostgreSQL faltam. |
| 15/09 | Fechamento parcial por escritÃ³rio | Rodada diÃ¡ria segue apÃ³s reserva pendente, registra estado Parcial e quantidade adiada. Adiamento persistido e exibido no console com competÃªncia/link do escritÃ³rio; retentativa resolve registro sem duplicar fatura. [Auditoria atualizada](auditoria-fechamento-competencia-2026-09-15.md). | **565 aprovados, 1 ignorado, 8 subtestes aprovados** em 39,10 s; Ruff, checks Django/schema e Playwright desktop/mobile com escritÃ³rio sintÃ©tico passaram. Console final sem erro; servidor/aba fechados. DiagnÃ³stico da reserva, retentativa pelo console e concorrÃªncia PostgreSQL faltam. Sem cobranÃ§a externa. |
| 15/09 | Triagem: saÃ­da da quarentena e biblioteca interna | VerificaÃ§Ã£o de formato apÃ³s antimalware limpo vinculado ao hash; aprovaÃ§Ã£o humana termina em pronto para arquivar; cÃ³pia privada distinta e hash conferido antes de marcar arquivado. ProtÃ³tipo manual e destino Windows sem agente nÃ£o sÃ£o tratados como arquivo entregue. [Auditoria](auditoria-triagem-formato-biblioteca-2026-09-15.md). | **579 aprovados, 1 ignorado, 8 subtestes aprovados** em 45,03 s; Ruff e migraÃ§Ãµes passaram. Testes usam scanner/arquivo/escritÃ³rio sintÃ©ticos. ClassificaÃ§Ã£o, revisÃ£o, download e homologaÃ§Ã£o real ainda faltam. |
| 15/09 | Triagem: detalhe e download conferido | Detalhe exibe origem/vereditos/estado, histÃ³rico com rÃ³tulos legÃ­veis e link somente para biblioteca interna arquivada. Download com empresa permitida, hash da cÃ³pia, resposta privada e auditoria; adulteraÃ§Ã£o Ã© recusada. [Auditoria da tela](auditoria-triagem-detalhe-download-2026-09-15.md). | **580 aprovados, 1 ignorado, 8 subtestes aprovados** em 40,97 s; Playwright desktop/mobile com teclado, foco, arquivo baixado, quarentena e console sem erro; abas/servidor fechados. RevisÃ£o e classificaÃ§Ã£o na tela ainda faltam. |
| 15/09 | Copiloto: uso Sonnet e auditoria de tentativa | Resposta simulada registra tokens de entrada/saÃ­da e cache; auditoria marca respondida/incerta/bloqueada, preservando reserva em timeout. MigraÃ§Ã£o marca permissÃµes antigas sem prova como incertas. [Auditoria](auditoria-copiloto-egress-2026-09-15.md). | **581 aprovados, 1 ignorado, 8 subtestes aprovados** em 39,50 s; Ruff/checks/schema passaram. Nenhuma chamada paga. |
| 15/09 | Copiloto: reserva durÃ¡vel antes da chamada | Mensagem/reserva de uso sÃ£o confirmadas antes do I/O local; cota, auditoria e hash do payload Claude sÃ£o confirmados antes da chamada externa, executada sem transaÃ§Ã£o aberta. Resultado e resposta sÃ£o persistidos depois. Teste transacional inspecionou a reserva dentro do mock do fornecedor. [Auditoria atualizada](auditoria-copiloto-egress-2026-09-15.md). | **582 aprovados, 1 ignorado, 8 subtestes aprovados** em 40,39 s; Ruff, Django e schema passaram. Nenhuma chamada paga. Falta reconciliaÃ§Ã£o de tentativa reservada apÃ³s morte do worker e retry seguro. |
| 15/09 | Copiloto: identificar tentativa perdida | Auditoria vinculada Ã  mensagem e Ã  reserva; tarefa agendada identifica tentativas Claude antigas e marca resultado incerto sem liberar a cota nem repetir chamada. Teste cobre tentativa perdida, reconciliaÃ§Ã£o idempotente e resposta comprovada tardia. [Auditoria atualizada](auditoria-copiloto-egress-2026-09-15.md). | **582 aprovados, 1 ignorado, 8 subtestes aprovados** em 42,08 s; Ruff, Django e schema passaram. Nenhuma chamada paga. Falta estado de interrupÃ§Ã£o na conversa, dedupe de POST, decisÃ£o de suporte e observabilidade da rotina. |
| 15/09 | Copiloto: envio e recuperaÃ§Ã£o pela conversa | Playwright encontrou POST com empresa vazia em conversa existente; corrigido. Nova conversa ganhou busca/seleÃ§Ã£o de empresa; mesma chave de envio nÃ£o duplica resposta/reserva; pergunta sem resposta mostra andamento/incerteza/interrupÃ§Ã£o e protocolo. [Auditoria da conversa](auditoria-copiloto-conversa-recuperacao-2026-09-15.md). | **585 aprovados, 1 ignorado, 8 subtestes aprovados** em 41,34 s; Ruff, Django e schema passaram. Playwright local isolado desktop/mobile/claro/escuro conferiu erro, vazio, busca, foco, envio e resposta; console dos estados finais 0 erros. Sem API paga. Falta decisÃ£o de suporte da reserva e piloto externo. |

| 15/09 | P0: revisÃ£o de caso NFS-e e configuraÃ§Ã£o de Triagem | Painel/empresa/fila abrem o caso exato; detalhe exibe evidÃªncia, XML original auditado e resultado da decisÃ£o. Fila de anexos separada de â€œGerenciar caixasâ€; erro IMAP foi inspecionado em navegador sintÃ©tico. [Prova e limites](execucao-p0-area-de-trabalho-2026-09-15.md). | `uv run pytest -q`: **588 aprovados, 1 ignorado e 8 subtestes aprovados**; Ruff focado e Django check passaram. Playwright desktop/celular/foco/erro/vazio sem overflow nem erro de console nos estados alcanÃ§ados; aba/servidor encerrados. Fedrizzi nÃ£o foi alterada. Sem Serpro, e-mail ou outra chamada paga. Demo isolada e homologaÃ§Ã£o real ainda pendentes. |
| 15/09 | P0: base da demo central e decisÃµes da Triagem | `Organization.is_demo`, MFA dispensado sÃ³ para membro exclusivo da demo; DTE/guia/Copiloto e caixa de exemplo sem fornecedor; mensagem DTE fictÃ­cia aberta com confirmaÃ§Ã£o, protocolo local e sem ciÃªncia oficial; anexos fictÃ­cios percorridos atÃ© aprovaÃ§Ã£o, arquivo Ã­ntegro e download. A revisÃ£o da Triagem agora ocorre no detalhe com motivo e confirmaÃ§Ã£o para rejeiÃ§Ã£o. [Isolamento e riscos restantes](auditoria-demo-isolamento-2026-09-15.md). | **597 aprovados, 1 ignorado e 8 subtestes aprovados**; Django check passou. Navegador sintÃ©tico desktop/celular, foco, abertura DTE e arquivamento Triagem, 0 erros de console nos estados alcanÃ§ados. Ruff foi corrigido apÃ³s a suÃ­te; repetir na prÃ³xima rodada. Ainda faltam isolamento de progresso dos visitantes, travas transversais, Parcelamentos e homologaÃ§Ã£o real; demo nÃ£o estÃ¡ pÃºblica. |
| 16/09 | P0: filas por carteira e painel de prÃ³xima aÃ§Ã£o | Guias, RevisÃµes, Triagem e ConciliaÃ§Ã£o ganharam pesquisa e filtros operacionais; a VisÃ£o Geral separa pendÃªncias por mÃ³dulo e abre cada fila jÃ¡ filtrada. RevisÃµes viram cartÃµes no celular, mantendo aÃ§Ã£o e evidÃªncia do caso exato. ReferÃªncias: `ui-ux-pro-max` (seleÃ§Ã£o em lote e feedback), Watermelon Astrix (pipeline de revisÃ£o), Vercel Web Interface Guidelines e produto existente. | **610 aprovados, 1 ignorado e 8 subtestes aprovados** em 56,17 s; Ruff focado, Django check e migrations passaram. Playwright desktop/mobile confirmou dashboard, filtros, foco, contagem, cartÃµes mÃ³veis, ausÃªncia de overflow e console limpo. Nenhum fornecedor externo foi chamado. SeleÃ§Ã£o em lote de emissÃ£o continua bloqueada atÃ© existir cotaÃ§Ã£o, autorizaÃ§Ã£o e atomicidade reais. |

## PrÃ³xima prova exigida por Ã¡rea

- **IA:** chave e modelo Sonnet 5 jÃ¡ passaram pela contagem gratuita. Faltam limites globais/por escritÃ³rio, consentimento e cenÃ¡rio autorizado de teste cobrado. Verificar resposta, erro recuperÃ¡vel, uso, custo e ausÃªncia de segredo no navegador/log. O PC local exigirÃ¡ teste de preferÃªncia do runtime e virada controlada.
- **Triagem:** escritÃ³rio conecta cada tipo de caixa pelo guia interno; primeiro poll respeita corte/cursor; cada anexo passa por proteÃ§Ã£o, identificaÃ§Ã£o, revisÃ£o e destino escolhido; hash de destino e checklist sÃ£o comprovados. DecisÃµes de taxonomia, formatos, padrÃ£o Windows e retenÃ§Ã£o estÃ£o em [dÃºvidas abertas](duvidas-abertas.md).
- **Serpro, ADN/NFS-e, DomÃ­nio e Siescon:** piloto com contrato, credenciais, certificados e amostras autorizados; verificar repetiÃ§Ã£o, falha, cota, escopo e resultado persistido. NÃ£o chamar um mock de homologaÃ§Ã£o externa.
- **Asaas e contrato manual:** uma fatura, pagamento e eventos idempotentes; contrato manual imune ao webhook; carÃªncia, somente leitura e reativaÃ§Ã£o pela regra confirmada.
- **ProduÃ§Ã£o:** resolver workflow/ambiente de deploy, SMTP/DNS, contatos e termos finais, saÃºde Celery, backup e restauraÃ§Ã£o. Recursos e APIs cobrados requerem confirmaÃ§Ã£o especÃ­fica de custo imediatamente antes da aÃ§Ã£o.
- **Telas:** repetir a auditoria para cada nova tela ou mudanÃ§a material; para os estados jÃ¡ alcanÃ§ados, consultar a [prova registrada](auditoria-ui-2026-09-15.md). ConexÃ£o OAuth, anexos recebidos por e-mail e seus estados de carga/erro aguardam implementaÃ§Ã£o.

Qualquer nova execuÃ§Ã£o acrescenta uma linha com comando/ambiente, resultado e limitaÃ§Ã£o. NÃºmeros de teste nÃ£o devem ficar como promessa permanente no README.
| 16/09 | Guias: carteira real de apuraÃ§Ãµes DomÃ­nio | `FOVGUIAINSS` entrou na allowlist ODBC somente leitura, com recorte de 18 meses, valor positivo e projeÃ§Ã£o mÃ­nima. A tela separa 3.022 apuraÃ§Ãµes locais de 241 empresas das guias oficiais, pesquisa a carteira e mostra empresa, competÃªncia, vencimento e valor reais sem declarar dÃ­vida ou pagamento. [Auditoria Fedrizzi](auditoria-guias-dctfweb-fedrizzi-2026-09-15.md). | 17 testes focados e a suÃ­te completa com **615 aprovados, 1 ignorado e 8 subtestes** passaram; Playwright autenticado na Fedrizzi em desktop/celular validou busca, 30 resultados por pÃ¡gina visual, cartÃµes mÃ³veis, aÃ§Ã£o 309 Ã— 44 px, zero overflow e console limpo. Nenhuma linha DomÃ­nio e nenhum fornecedor externo foram alterados/chamados. Serpro ainda precisa reconciliar declaraÃ§Ã£o, recibo, saldo e guia oficial. |
| 16/09 | DCTFWeb: contrato correto e prova do PDF | `GERARGUIA31` agora recebe categoria/ano/mÃªs conforme o Serpro; HTTP 200 sÃ³ conclui apÃ³s validar o PDF base64. Download oficial reutiliza a evidÃªncia cifrada e nÃ£o cria nova chamada. ApuraÃ§Ãµes importadas entram como `discovered` e nÃ£o podem ser emitidas antes da reconciliaÃ§Ã£o. | 47 testes focados e a su?te completa com **626 aprovados, 1 ignorado e 8 subtestes** passaram, incluindo payload oficial, competÃªncia invÃ¡lida, resposta sem PDF, documento corrompido, liberaÃ§Ã£o de uso e download sem fornecedor. `CONSDECCOMPLETA33` e `CONSRECIBO32` ainda precisam do fluxo pago de consulta e aceite. |
| 16/09 | DCTFWeb: declaraÃ§Ã£o completa e recibo | A apuraÃ§Ã£o abre cotaÃ§Ã£o separada de `CONSDECCOMPLETA33` e `CONSRECIBO32`; cada confirmaÃ§Ã£o reserva consumo, persiste estado/PDF e impede retentativa em resultado incerto. Downloads reutilizam a evidÃªncia cifrada. Demo gera resultado fictÃ­cio sem fornecedor. | **633 aprovados, 1 ignorado e 8 subtestes**; 21 focados. Nenhuma chamada paga foi feita. Falta configurar as tarifas no contrato Fedrizzi, homologar chamada autorizada e reconciliar a declaraÃ§Ã£o com a apuraÃ§Ã£o antes de promover guia para emissÃ£o. Playwright indisponÃ­vel nesta passagem por transporte MCP encerrado. |
| 16/09 | DCTFWeb: consumo migrado para tokens | DeclaraÃ§Ã£o completa, recibo e emissÃ£o de DARF reservam e liquidam `TokenUsageEvent` no mÃ³dulo `integra`. A confirmaÃ§Ã£o mostra peso inteiro, franquia e excedente; tabela/peso ausente bloqueia a operaÃ§Ã£o. O worker ainda concilia eventos legados jÃ¡ enfileirados. | 28 testes focados e suÃ­te completa com **633 aprovados, 1 ignorado e 8 subtestes**. Migration `hub.0030` aplicada. Nenhum peso ou preÃ§o foi inventado para a Fedrizzi e nenhuma chamada paga foi feita. Falta a Ã¡rea de proposta/aceite da tabela de tokens para uso sem administraÃ§Ã£o de banco. |
| 16/09 | Tokens: proposta comercial e aceite do escritÃ³rio | Comercial/Admin da Mewstack monta uma proposta em rascunho com valor Ãºnico do token, mensalidade/franquia da Central Integra, pesos inteiros DCTFWeb e teto mensal. Dono/Admin revisa todos os termos em ConfiguraÃ§Ãµes, confirma explicitamente e escolhe vigÃªncia futura. Termos aceitos congelam; mudanÃ§as exigem nova versÃ£o. O consumo ativo substitui a apresentaÃ§Ã£o legada por chamada. | **634 aprovados, 1 ignorado e 8 subtestes**. ConfiguraÃ§Ã£o local recebeu `TOKEN_BILLING_ENABLED=true`; o padrÃ£o seguro do cÃ³digo continua desligado e o `.env.example` documenta a ativaÃ§Ã£o. Nenhuma cobranÃ§a ou API externa foi acionada. Playwright continuou indisponÃ­vel por transporte MCP encerrado. |
| 16/09 | Parcelamentos: Ã¡rea de trabalho da demonstraÃ§Ã£o | A escolha antes indisponÃ­vel na Central agora abre uma jornada por empresa: consulta fictÃ­cia, acordo PARCSN, consolidaÃ§Ã£o, parcelas paga/disponÃ­vel e emissÃ£o fictÃ­cia de DAS. O estado fica isolado por sessÃ£o e a tela real recusa chamada enquanto tarifa e homologaÃ§Ã£o nÃ£o existem. | **13 testes de demo aprovados**, incluindo isolamento entre dois navegadores e ausÃªncia de mutaÃ§Ã£o compartilhada. Ruff e `manage.py check` passaram. O MCP Playwright permaneceu indisponÃ­vel (`Transport closed`), portanto esta rodada nÃ£o declara inspeÃ§Ã£o visual. Nenhuma chamada Serpro ou cobranÃ§a ocorreu. |
| 16/09 | Demo: ConciliaÃ§Ã£o segura por sessÃ£o | A tela apresenta OFX e candidatos DomÃ­nio sintÃ©ticos, permite resolver uma ambiguidade e mantÃ©m o resultado apenas na sessÃ£o. Upload real fica oculto na demo e o texto afirma que nÃ£o hÃ¡ escrita no DomÃ­nio. | **637 testes aprovados, 1 ignorado e 8 subtestes**; isolamento entre dois visitantes e ausÃªncia de `ReconciliationMatch` compartilhado cobertos. Playwright MCP seguiu indisponÃ­vel (`Transport closed`). |
| 16/09 | Landing: promessa alinhada e acesso Ã  demo | A pÃ¡gina pÃºblica agora oferece a demo fictÃ­cia quando o ambiente estÃ¡ realmente pronto, afirma 14 dias sem cartÃ£o e sem cobranÃ§a automÃ¡tica e explica ativaÃ§Ã£o gradual. Textos de NFS-e, DCTFWeb, Central e recebimento deixaram de prometer integraÃ§Ã£o antes da configuraÃ§Ã£o/homologaÃ§Ã£o. | **639 testes aprovados, 1 ignorado e 8 subtestes**. `ui-ux-pro-max`, Watermelon e as diretrizes Vercel foram consultados; Watermelon nÃ£o retornou referÃªncia prÃ³xima. Playwright MCP permaneceu indisponÃ­vel (`Transport closed`). |
| 16/09 | Caixa DTE migrada para tokens | Consulta da caixa por empresa e abertura de teor/poss?vel ci?ncia receberam pesos pr?prios na proposta da Central Integra. A autoriza??o mostra tokens, franquia e excedente em reais; cada item persiste o evento que permitiu a chamada. Tabela ativa usa `TokenUsageEvent`; trabalhos antigos ainda liquidam `UsageEvent` sem criar uma segunda cobran?a. | Migration `hub.0031` aplicada; **640 testes aprovados, 1 ignorado e 8 subtestes**, Ruff, Django check e schema limpos. Demo respondeu HTTP 200. Nenhuma chamada Serpro ou cobran?a externa foi feita. Watermelon n?o encontrou refer?ncia pr?xima; Playwright MCP permaneceu indispon?vel (`Transport closed`). |
| 16/09 | Guias Fedrizzi: carteira acess?vel e DCTFWeb em lote | O ciclo local da Fedrizzi saiu de `provisioning` para `active` como piloto interno autorizado, sem contrato, pre?o ou cobran?a. A tela autenticada leu 3.145 linhas ODBC e exibiu 3.022 apura??es de 241 empresas ativas; 30 linhas carregadas podem ser selecionadas de uma vez, com pr?via agregada de tokens e autoriza??o at?mica de declara??o ou recibo. A demo grava o lote somente na sess?o. | Valida??o autenticada retornou HTTP 200, 3.022 itens, 30 seletores e nenhum estado vazio antigo. **642 testes aprovados, 1 ignorado e 8 subtestes**; Ruff, Django check, schema e sintaxe JS limpos. Nenhuma consulta Serpro nem cobran?a foi executada. Playwright MCP permaneceu indispon?vel (`Transport closed`) e Watermelon n?o encontrou bloco semelhante. |
| 16/09 | Triagem: configuraÃ§Ã£o operacional de caixa e destino | Dono ou administrador configura na prÃ³pria tela a pasta/etiqueta, data inicial, filtros de remetente e assunto e a ativaÃ§Ã£o da leitura. Os trÃªs coletores aplicam os filtros antes de baixar anexos. O escritÃ³rio tambÃ©m escolhe biblioteca interna ou raiz Windows; o padrÃ£o da pasta mantÃ©m nome da empresa e cÃ³digo DomÃ­nio. Enquanto o agente local nÃ£o validar a raiz Windows, o arquivamento Ã© bloqueado com recuperaÃ§Ã£o explÃ­cita, sem gravar no destino errado. | **646 testes aprovados, 1 ignorado e 8 subtestes**; 47 testes focados de Triagem, Ruff, Django check e schema limpos. Render autenticado da Fedrizzi respondeu HTTP 200. Nenhuma caixa real, scanner, agente Windows ou API externa foi acionada. Watermelon nÃ£o encontrou referÃªncia prÃ³xima; Playwright MCP permaneceu indisponÃ­vel (`Transport closed`). |
| 16/09 | ConfiguraÃ§Ãµes: cobranÃ§a apresentada somente em tokens | A Ã¡rea do escritÃ³rio deixou de exibir franquia e excedente por chamada. Agora mostra somente proposta, valor do token, franquia por mÃ³dulo, pesos, teto, vigÃªncia e consumo. Uma tabela aceita para competÃªncia futura aparece como programada e nÃ£o como vigente; o endpoint legado de polÃ­tica por chamada recusa novas alteraÃ§Ãµes. | **646 testes aprovados, 1 ignorado e 8 subtestes**; 70 testes focados de workspace/contratos, Ruff, Django check e render autenticado da Fedrizzi limpos. Watermelon nÃ£o encontrou referÃªncia prÃ³xima. A auditoria Vercel foi aplicada; Playwright MCP permaneceu indisponÃ­vel (`Transport closed`). |
| 16/09 | Copiloto migrado para a carteira de tokens | O Comercial pode incluir o mÃ³dulo de IA numa proposta com mensalidade, franquia e peso inteiro por resposta. O dono vÃª termos de todos os mÃ³dulos antes do aceite e tambÃ©m apÃ³s a vigÃªncia. Com tabela ativa, `ai.answer` reserva e liquida `TokenUsageEvent`; a auditoria Claude referencia o mesmo evento. Sem termos de IA numa tabela vigente, a operaÃ§Ã£o fica bloqueada pela proteÃ§Ã£o contra mistura de medidores. | Migration `intelligence.0026` aplicada. **648 testes aprovados, 1 ignorado e 8 subtestes**; testes cobrem proposta incompleta, aceite transparente, resposta Sonnet simulada, liquidaÃ§Ã£o e vÃ­nculo de auditoria. Nenhum preÃ§o foi inventado e nenhuma chamada Anthropic foi feita. |
| 16/09 | Triagem: arquivamento Windows comprovado pelo agente | A aprovaÃ§Ã£o cria trabalho isolado por escritÃ³rio. O agente compara a raiz local com a raiz escolhida, recusa escape e reparse points, baixa sÃ³ o anexo validado, grava temporÃ¡rio, confere tamanho/SHA-256 e renomeia atomicamente. A tela separa fila, cÃ³pia, falha recuperÃ¡vel e destino confirmado; `Arquivado` sÃ³ ocorre apÃ³s a prova. | **651 testes aprovados, 1 ignorado e 8 subtestes** em 59,34 s; 100 testes focados de Triagem/workspace, Ruff, Django e os dois projetos .NET passaram. Nenhuma pasta real foi alterada. A homologaÃ§Ã£o no PC e compartilhamento Windows do primeiro escritÃ³rio ainda Ã© obrigatÃ³ria. Watermelon nÃ£o encontrou referÃªncia prÃ³xima; Playwright MCP permaneceu indisponÃ­vel (`Transport closed`). |

| 16/09 | Parcelamentos PARCSN: operaÃ§Ã£o real preparada | A Ã¡rea de trabalho pesquisa empresa/CNPJ/cÃ³digo DomÃ­nio, permite selecionar todas as linhas exibidas ou um lote de atÃ© 30, calcula tokens/excedente antes da autorizaÃ§Ã£o, persiste cada tentativa e protocolo, consulta pedidos/detalhe/parcelas e emite DAS. O PDF validado Ã© baixado do resultado salvo sem nova chamada. Falha de transporte fica em resultado incerto e nÃ£o Ã© repetida automaticamente. | **656 testes aprovados, 1 ignorado e 8 subtestes**; 14 testes focados de parser/operaÃ§Ã£o passaram. Django, migrations e Ruff passaram. A migration 0032 foi aplicada no banco local. Nenhuma chamada Serpro ocorreu. O piloto real continua obrigatÃ³rio e depende de tabela de tokens aceita; Playwright permaneceu indisponÃ­vel (Transport closed) e os navegadores CUA nÃ£o estavam disponÃ­veis. |

| 16/09 | Guias/DCTFWeb: agrupamento operacional validado na Fedrizzi | O DSN real retornou 3.145 componentes no recorte; 3.022 pertencem Ã s 562 empresas ativas. A fila agora agrupa duplicidades por empresa/competÃªncia em **2.943 competÃªncias para 241 empresas**, mostra quantidade de componentes, soma local e intervalo de vencimentos e gera uma Ãºnica seleÃ§Ã£o DCTFWeb por competÃªncia. | GET autenticado real retornou 200, 30 competÃªncias visÃ­veis e nenhum texto antigo de fonte ausente. 15 testes focados passaram. Nenhuma linha ODBC foi alterada e nenhuma chamada Serpro ocorreu. Watermelon nÃ£o encontrou referÃªncia prÃ³xima; Playwright permaneceu indisponÃ­vel (Transport closed). |

| 16/09 | DCTFWeb: reconciliaÃ§Ã£o entre documentos, DomÃ­nio e emissÃ£o | Depois que declaraÃ§Ã£o completa e recibo ficam disponÃ­veis, a confirmaÃ§Ã£o relÃª a empresa/competÃªncia no ODBC, agrega componentes e cria ou atualiza a guia `ready` com referÃªncia tÃ©cnica hash. Valores do navegador sÃ£o ignorados; ausÃªncia de qualquer PDF ou desaparecimento da apuraÃ§Ã£o bloqueia a promoÃ§Ã£o. A tela mantÃ©m a soma como cÃ¡lculo DomÃ­nio e manda conferir o valor oficial no DARF. | **658 testes aprovados, 1 ignorado e 8 subtestes**. Ruff, Django e migrations passaram. Nenhuma chamada Serpro ocorreu. Playwright continuou indisponÃ­vel (Transport closed). |
| 16/09 | NFS-e ADN: cliente, checkpoint e Ã¡rea de trabalho | Implementado `GET /contribuintes/DFe/{NSU}` com mTLS A1, CNPJ raiz, limite de 50 documentos, base64/gzip, XML seguro, lote transacional, dedupe por empresa, lease, backoff e espera de uma hora ao alcanÃ§ar o maior NSU. A tela mostra cobertura, status, erros, frescor e permite ativar/pausar/repetir atÃ© 100 empresas exibidas. `NFSE_ADN_SYNC_ENABLED` fica falso atÃ© o piloto restrito autorizado. | **670 testes aprovados, 1 ignorado e 8 subtestes** em 61,78 s. Ruff, Django, migrations e `git diff --check` passaram. A Fedrizzi renderizou 100 empresas na carteira. A demo provou progresso isolado por sessÃ£o sem alterar o escritÃ³rio central. Nenhuma chamada ADN ocorreu; Playwright permaneceu indisponÃ­vel (`Transport closed`). |

## 16/09/2026 ? console de escrit?rios e Concilia??o

- A lista de escrit?rios do console deixou de usar uma coluna estreita de bot?es ?Abrir?: a linha inteira agora ? um link sem?ntico, com foco vis?vel e composi??o m?vel em cart?o.
- A Concilia??o passou a exibir evid?ncia de `AccountingEntry`, comparar candidatos das duas fontes e preservar decis?es manuais na reconstru??o.
- Valida??o local: 671 testes aprovados, 1 ignorado e 8 subtestes; Ruff, `manage.py check` e migrations sem pend?ncias.
- A inspe??o Playwright permaneceu indispon?vel porque o MCP retornou `Transport closed`; a valida??o visual em navegador real ainda precisa ser repetida.

## 16/09/2026 ? cust?dia central do certificado Integra Contador

- O Console Mewstack agora recebe `.pfx`/`.p12` de at? 2 MB, valida senha, chave privada e certificado antes de salvar.
- PKCS#12 e senha ficam cifrados com AES-256-GCM no banco; a tela mostra somente nome, sujeito, validade e os 12 ?ltimos caracteres do SHA-256. N?o existe rota de download.
- O cliente Integra usa primeiro o certificado armazenado; `INTEGRA_CERTIFICATE_PATH` permanece apenas como fallback legado.
- Migration `platform.0032` aplicada localmente; 44 testes focados aprovados.
## 18/09/2026 â€” Etapa 02 concluÃ­da localmente (V-009)

- Fechada a etapa de cadastro, acesso e administraÃ§Ã£o no nÃ­vel de implementaÃ§Ã£o/teste local. As regras comerciais D-79 estÃ£o documentadas; a integraÃ§Ã£o de cobranÃ§a pertence Ã  etapa 10.
- APIs, isolamento e demonstraÃ§Ã£o foram executados em banco de testes; 22 testes de autorizaÃ§Ã£o/API e 4 testes de isolamento da demo passaram. O browser confirmou MFA, painel autenticado, equipe, empresas, configuraÃ§Ãµes, foco, responsividade e console limpo.
- A massa demo nÃ£o foi regravada: o comando recusou corretamente usar um slug operacional existente. SMTP/DNS/Brevo ficam para homologaÃ§Ã£o integrada na etapa 12 por D-77/D-78.
## 18/09/2026 â€” Etapa 03 iniciada: contrato DomÃ­nio Fedrizzi (V-010)

- A leitura autorizada do conector existente passou: 4 consultas fixas, 5 objetos, 13.875 linhas e nenhuma coluna obrigatÃ³ria ausente. A descoberta de 500 objetos/4.733 colunas sÃ³ confirmou metadados jÃ¡ registrados; nÃ£o imprimiu ou gravou dados DomÃ­nio.
- D-80 fixa o serviÃ§o nativo CICA como pacote Ãºnico. O Python fica somente para diagnÃ³stico/migraÃ§Ã£o atÃ© a sincronizaÃ§Ã£o nativa v2 estar homologada.
- Implementada a primeira projeÃ§Ã£o nativa: empresas DomÃ­nio em pÃ¡ginas de 500 via API v2 autenticada. O teste do agente passou e o serviÃ§o .NET compilou em Release sem aviso; uma pÃ¡gina interrompida nÃ£o desativa empresas ausentes.
- A estaÃ§Ã£o Fedrizzi tem DSN `contabil` SQL Anywhere 17 e permissÃµes/ferramentas para instalaÃ§Ã£o. O MSI foi gerado, mas nÃ£o instalado: nÃ£o existe endpoint HTTPS CICA nem CA de agente configurada, portanto instalar agora criaria serviÃ§o falho. V-011 registra o procedimento e a dependÃªncia sem expor DSN ou dados.

## 18/09/2026 â€” DependÃªncias de produÃ§Ã£o centralizadas na etapa 12 (D-87)

- O responsÃ¡vel definiu que toda atividade dependente do site em produÃ§Ã£o serÃ¡ feita somente na etapa 12.
- As etapas 01â€“11 permanecem responsÃ¡veis por implementaÃ§Ã£o, configuraÃ§Ã£o sem segredos, testes locais/isolados e documentaÃ§Ã£o. Nenhum deploy, credencial externa de produÃ§Ã£o, chamada real, piloto ou custo foi acionado por este registro.

## 18/09/2026 â€” Etapa 04 iniciada: descoberta Siescon (V-029)

- A inspeÃ§Ã£o local de metadados encontrou drivers SQL Anywhere 16/17, mas nenhum DSN, driver ou instalaÃ§Ã£o identificada como Siescon. NÃ£o foram lidos dados nem expostos segredos.
- O prÃ³ximo passo exige o contrato tÃ©cnico de Q-33 por canal seguro: versÃ£o do Siescon, mecanismo de leitura autorizado, acesso de homologaÃ§Ã£o e layout de exportaÃ§Ã£o/importaÃ§Ã£o. Sem isso, um adaptador seria especulativo e nÃ£o serÃ¡ implementado.

## 18/09/2026 â€” Etapa 04: base de exportaÃ§Ã£o neutra (V-030)

- `AccountingExport` agora registra destino e versÃ£o do adaptador. O layout DomÃ­nio continua preservado; Siescon Ã© recusado explicitamente atÃ© a revisÃ£o de contrato/layout, sem gerar arquivo ou escrever no sistema de origem.
- A fonte Siescon foi modelada e a matriz de capacidades foi registrada. A suÃ­te focada aprovou 36 testes; migraÃ§Ãµes e Ruff passaram. NÃ£o houve conexÃ£o ou exportaÃ§Ã£o Siescon.

## 22/09/2026 â€” Etapa 11, ondas 0 a 2 da revisÃ£o total de telas (V-100)

- Matriz das 89 rotas de interface (49 telas, 40 aÃ§Ãµes/downloads) registrada em `docs/planejamento/matriz-telas-2026-09-22.md`; varredura GET autenticada e passagem por 20 telas em 375 px sem overflow horizontal ou erro de console.
- DemonstraÃ§Ã£o voltou Ã  home: o `.env` local apontava `cica-demo` e a organizaÃ§Ã£o fictÃ­cia Ã© `escritorio-demo`. A faixa de demonstraÃ§Ã£o ganhou "Sair da demonstraÃ§Ã£o", que encerra a sessÃ£o e descarta o progresso do visitante.
- `GET /sair/` respondia 405 sem corpo (Django 5.0 removeu logout por GET; o projeto usa 6.0.8). Passou a responder com pÃ¡gina de confirmaÃ§Ã£o; o logout continua em POST, com teste de regressÃ£o.
- `refuse()` ganhou `kind="unavailable"`: 24 recusas de estado deixaram de ser rotuladas como falta de permissÃ£o. Estado vazio ganhou parcial Ãºnico e os dois casos fora do contrato foram convertidos.
- SuÃ­te completa no `.venv`: 781 aprovados, 2 ignorados. Ondas 3 a 8 continuam abertas; nada foi homologado.

## 22/09/2026 â€” Etapa 11, ondas 1 a 4 da revisÃ£o total de telas (V-101)

- FundaÃ§Ã£o: `.inline-alert` ganhou estilo real (era texto sem forma) com contraste AA calculado nos dois temas; aÃ§Ãµes em lote sÃ³ aparecem apÃ³s seleÃ§Ã£o em quatro filas; separador de milhar pt-BR ligado; avisos de demonstraÃ§Ã£o deixaram de repetir a faixa global.
- NÃºcleo diÃ¡rio: revisÃµes de NFS-e ganharam situaÃ§Ã£o e origem do acumulador; Empresas ganhou filtro e coluna de certificado e de revisÃ£o aberta; Caixa DTE e VisÃ£o geral passaram a mostrar a idade da pendÃªncia.
- Processamento: o detalhe do movimento da ConciliaÃ§Ã£o parou de perder filtro e pÃ¡gina; os indicadores mostram valor dos dois lados; o destino Windows da Triagem mostra saÃºde do agente e prova da Ãºltima gravaÃ§Ã£o.
- SuÃ­te completa no `.venv`: 788 aprovados, 2 ignorados. Ruff aprovado. Ondas 5 a 8 continuam abertas; nada foi homologado.

## 22/09/2026 â€” Etapa 11, landing e ondas 5 a 8 da revisÃ£o total (V-102)

- Landing: seÃ§Ã£o de marca virou seÃ§Ã£o de problema, contagem errada de etapas corrigida, "Entrar" voltou ao cabeÃ§alho no celular e cinco links passaram ao alvo mÃ­nimo de 24 px. O consentimento do cadastro ganhou nome acessÃ­vel completo.
- Onda 5: Radar com filtro de perÃ­odo, resumo e marca de "publicaÃ§Ã£o coletada"; Copiloto com limite explÃ­cito de rascunho e aviso de resposta sem fonte; aprendizado com vazio Ãºtil e ficha de escopo, diferenÃ§a e responsÃ¡vel.
- Onda 6: console Mewstack inspecionado visualmente pela primeira vez (base fictÃ­cia, sem senha digitada e sem contornar MFA), painel reorganizado por exceÃ§Ã£o, tÃ­tulo do detalhe corrigido e Equipe deixou de expor as contas de outros visitantes da demonstraÃ§Ã£o.
- Onda 7: tutorial guiado implementado â€” catÃ¡logo declarativo, preferÃªncia versionada por pessoa, diÃ¡logo nativo com Pular/Voltar/Fechar, botÃ£o "Como usar" e progresso sÃ³ em sessÃ£o na demonstraÃ§Ã£o.
- Onda 8: auditoria contra as Vercel Web Interface Guidelines nas superfÃ­cies alteradas, varredura em 375 px sem overflow e console limpo. SuÃ­te no `.venv`: 796 aprovados, 2 ignorados; Ruff e `makemigrations --check` limpos.
- Continuam abertos: regressÃ£o por perfil, leitor de tela, temas lado a lado, viewports 1024/768 e a configuraÃ§Ã£o do console sob MFA. Nada foi homologado.

## 22/09/2026 â€” Entrada da demonstraÃ§Ã£o resolvida pela organizaÃ§Ã£o, nÃ£o pelo slug (V-103)

- O `.env` corrigido nÃ£o bastava: `load_dotenv` nÃ£o sobrescreve variÃ¡vel jÃ¡ no ambiente, entÃ£o o servidor em execuÃ§Ã£o manteve `cica-demo` mesmo depois do autoreload trazer o cÃ³digo novo.
- `demo_office()` passou a usar o slug configurado quando ele existe e, caso contrÃ¡rio, a Ãºnica organizaÃ§Ã£o ativa com `is_demo=True`; duas marcadas mantÃªm a entrada fechada.
- Verificado no servidor do responsÃ¡vel sem reiniciar o processo; dois testes de regressÃ£o adicionados. SuÃ­te: 798 aprovados, 2 ignorados.

## 22/09/2026 â€” Chave de criptografia do banco de desenvolvimento (V-104)

- A massa fictÃ­cia de `db.sqlite3` estava cifrada com `test-v1` (settings de teste) e o desenvolvimento usa `local-v1`: a VisÃ£o geral quebrava ao ler NFS-e. `test-v1` entrou no mapa de chaves do `.env` local, com `local-v1` seguindo como ativa; nada foi apagado.
- `config/settings/local.py` passou a usar `load_dotenv(override=True)`, para que o `.env` venÃ§a o ambiente herdado pelo autoreload â€” a mesma armadilha que escondeu a demonstraÃ§Ã£o em V-103.
- Verificado em processo novo: chaves carregadas, documento decifrado e `/app/` em 200. SuÃ­te: 798 aprovados, 2 ignorados.

## 22/09/2026 â€” NFS-e: classificaÃ§Ã£o e barra de filtros (V-105)

- OrientaÃ§Ã£o guiada nÃ£o foca mais o texto do passo: o anel de foco aparecia em toda tela aberta porque `:focus-visible` casa com foco programÃ¡tico em `tabindex="-1"`. Passo anunciado por regiÃ£o viva, foco inicial em â€œAvanÃ§arâ€.
- A porcentagem de confianÃ§a saiu da NFS-e, da fila de revisÃµes, da VisÃ£o geral, do detalhe da revisÃ£o e do manifesto da demonstraÃ§Ã£o. Nova coluna **ClassificaÃ§Ã£o** (Classificada / NÃ£o classificada) antes do acumulador.
- A barra de filtros da carteira virou uma linha sÃ³ e aplica a cada mudanÃ§a, trocando apenas a regiÃ£o de resultados (atualizaÃ§Ã£o local, WCAG 3.2.2); o botÃ£o de envio permanece para quem estÃ¡ sem JavaScript.
- Verificado no servidor isolado de revisÃ£o em 1440 px e 375 px. SuÃ­te: 799 aprovados, 2 ignorados.

## 22/09/2026 â€” Parcelamentos funcional e revisÃ£o da importaÃ§Ã£o da ConciliaÃ§Ã£o (V-106)

- Parcelamentos: consulta direta na empresa em foco, detalhe do acordo renderizado (antes era buscado e pago, mas nunca exibido), carteira da demonstraÃ§Ã£o marca a consulta, parcela em atraso/mÃªs atual, reemissÃ£o de DAS falho, liberaÃ§Ã£o auditada de "resultado a confirmar" (antes bloqueava para sempre), atualizaÃ§Ã£o automÃ¡tica enquanto hÃ¡ fila e botÃµes com estado de envio.
- ConciliaÃ§Ã£o: importador OFX paralelo removido da tela; o envio Ãºnico alimenta as duas filas; perÃ­odo descartado removido; campo Empresa desalinhado corrigido; validaÃ§Ã£o de formato, tamanho e quantidade antes do envio; progresso ao vivo; etapa com nome legÃ­vel; demonstraÃ§Ã£o sem upload compartilhado; contadores da demonstraÃ§Ã£o sem depender do filtro.
- Verificado no servidor isolado em 1366 px e 375 px. Detalhes e limites em V-106.

## V-141 ? Assistente de configuracao retomavel

Implementado em 23/09/2026 sob D-122. Cada etapa pendente mantem seu estado e encaminha o administrador para a acao correspondente, sem ativar modulos, integracoes ou consumo. Validacao focalizada: 72 testes aprovados; regressao completa: 864 aprovados, 2 ignorados e 11 subtestes.


## V-142 â€” Roteiro do responsÃ¡vel para liberaÃ§Ã£o

23/09/2026. Criado `roteiro-do-responsavel-para-liberacao.md`, com as cinco aÃ§Ãµes iniciais e instruÃ§Ãµes objetivas por frente: o que o responsÃ¡vel providencia/decide, o que fornecedor e desenvolvimento fazem, como validar e que evidÃªncia encerra cada etapa. O documento aponta Q-33 e Q-39 como contratos tÃ©cnicos indispensÃ¡veis, preserva a leitura Ãºnica do backup DomÃ­nio Web, exige polÃ­tica/valores aprovados antes de IA ou cobranÃ§a e nÃ£o transforma documentaÃ§Ã£o em homologaÃ§Ã£o. Nenhum ambiente, segredo, chamada, dado real, contrataÃ§Ã£o ou custo foi acionado.

## V-143 â€” Primeiras correÃ§Ãµes da central operacional

24/09/2026. Carteira de colaborador agora exige atribuiÃ§Ã£o ativa e revogar a Ãºltima nÃ£o amplia acesso. Administrador local mantÃ©m visÃ£o total. PrÃ©via/fila ordenam pelo prazo efetivo, deixando sem prazo ao final. D-123/D-124 registrados antes das mudanÃ§as; testes de DTE/Parcelamentos atualizados para atribuiÃ§Ã£o explÃ­cita. RegressÃ£o integral: 869 aprovados, 2 ignorados e 15 subtestes em 77,61 s; Ruff, MyPy, Django e migraÃ§Ãµes sem pendÃªncias. Playwright MCP indisponÃ­vel (Transport closed). PrÃ³xima execuÃ§Ã£o: transformar a VisÃ£o geral na agenda pessoal e agregar fechamentos, mantendo separados escopo de leitura, responsabilidade pela tarefa e gestÃ£o administrativa. O checklist aberto estÃ¡ na etapa 11; estas correÃ§Ãµes nÃ£o encerram a meta.

## V-144 â€” Agenda pessoal como entrada da VisÃ£o geral

24/09/2026. D-125 separa Meu trabalho, Carteira e GestÃ£o. PaginaÃ§Ã£o de 30, agrupamento por prazo, filtro no recorte e responsÃ¡vel visÃ­vel substituem a prÃ©via de seis atividades. Testes de fronteira, perfil, filtro e segunda pÃ¡gina; 89 focados e regressÃ£o integral de 871 aprovados/2 ignorados/15 subtestes. Ruff, MyPy, Django e migraÃ§Ãµes passaram. UI/UX Pro Max, Watermelon e guidelines consultados; fontes e limites na etapa 11. Playwright indisponÃ­vel por Transport closed; nenhuma aba aberta. PrÃ³ximo passo: agregar fechamentos por empresa/competÃªncia/Ã¡rea, evidÃªncias e impedimentos sem presumir que uma lista vazia significa fechamento.

## V-145 â€” RecorrÃªncia mensal recuperÃ¡vel

24/09/2026. D-126, cursor por atribuiÃ§Ã£o (migration 0054), rotina transacional e tarefa Beat horÃ¡ria implementados; responsÃ¡veis invÃ¡lidos ficam sem atribuiÃ§Ã£o, com histÃ³rico. Primeira geraÃ§Ã£o e retomada/pause respeitam mÃªs corrente e limite por lote sem perder cursor. DocumentaÃ§Ã£o de falha/retomada no manual de homologaÃ§Ã£o. 878 testes aprovados, 2 ignorados, 19 subtestes; Ruff, MyPy, Django e migraÃ§Ãµes passaram. NÃ£o aplicado ao banco operacional nem ativado em produÃ§Ã£o. PrÃ³ximo passo: fechamentos agregados na agenda e integraÃ§Ã£o das pendÃªncias/retornos dos mÃ³dulos; concorrÃªncia PostgreSQL e operaÃ§Ã£o publicada permanecem sem prova.

## V-146 â€” Regra compartilhada de conclusÃ£o comprovada

24/09/2026. Identificada e corrigida conclusÃ£o falsa em assess_closing, que antes contava somente work_status. D-127 exige requisitos atuais e retorna causas; conclusÃ£o manual usa a mesma funÃ§Ã£o, inclusive para repetir uma aÃ§Ã£o jÃ¡ marcada concluÃ­da. Testes preservam pagamento separado e modo humano sem ERP. RegressÃ£o: 881 aprovados, 2 ignorados, 21 subtestes; Ruff, MyPy, Django e migraÃ§Ãµes sem pendÃªncia. Checklist e manual externo atualizados. PrÃ³xima execuÃ§Ã£o: implementar apresentaÃ§Ã£o de fechamentos por empresa/Ã¡rea/competÃªncia considerando todo o conjunto autorizado, com causas e navegaÃ§Ã£o, sem reduzir fechamento Ã s tarefas pessoais. Depois ligar mÃ³dulos/observaÃ§Ãµes e validar jornadas e fontes. NÃ£o houve mudanÃ§a de interface nem publicaÃ§Ã£o nesta entrega.

## V-147 â€” Fechamentos na VisÃ£o geral

24/09/2026. D-128 registrado antes da implementaÃ§Ã£o. ServiÃ§o de apresentaÃ§Ã£o, partial e estilos integram requisitos de fechamento na agenda sem confundir responsabilidade pessoal com conjunto da empresa. CompetÃªncia e paginaÃ§Ã£o preservadas nos links; sem requisitos Ã© ausÃªncia de cobertura. 884 testes aprovados/2 ignorados/21 subtestes; checagens tÃ©cnicas passaram. UI/UX Pro Max, Watermelon e guidelines utilizados; Playwright segue indisponÃ­vel por Transport closed. PrÃ³ximo passo: ligar pendÃªncias e resultados dos mÃ³dulos Ã s atividades/observaÃ§Ãµes de fonte de forma idempotente, com evidÃªncias e recuperaÃ§Ã£o, sem promover estados nÃ£o homologados. Checklist/manual atualizados; objetivo segue ativo.

## V-148 â€” Ponte da revisÃ£o NFS-e para a central

24/09/2026. D-129 e migration 0055; serviÃ§o idempotente ligado Ã  captura e decisÃ£o humana. Resolve_review passou a bloquear o caso em transaÃ§Ã£o e inclui artefato, histÃ³rico e atividade no mesmo commit. EvidÃªncia preserva autor/data, sem afirmar ERP fechado/importado. RecuperaÃ§Ã£o local por escritÃ³rio documentada. 889 testes aprovados/2 ignorados/21 subtestes; Ruff/MyPy/Django/migraÃ§Ãµes passaram. PrÃ³ximas aÃ§Ãµes: ligaÃ§Ã£o visual ao caso de origem e integraÃ§Ã£o dos demais mÃ³dulos com estados/evidÃªncias prÃ³prias; nÃ£o substituir aceitaÃ§Ã£o oficial por conclusÃ£o local. Meta continua ativa; nenhum ambiente publicado foi alterado.

## V-149 â€” Triagem conectada Ã  atividade de arquivamento

24/09/2026. D-130 e migration 0056; transiÃ§Ãµes humanas, seguranÃ§a e agente atualizam vÃ­nculo Ãºnico por arquivo identificado. AprovaÃ§Ã£o fica pendente, falha/rejeiÃ§Ã£o impedem, arquivamento com destino/data/hash conclui somente o trabalho local. Itens sem empresa ficam na fila prÃ³pria. RecuperaÃ§Ã£o explÃ­cita por escritÃ³rio documentada. RegressÃ£o de 891 aprovados, 2 ignorados e 21 subtestes; correÃ§Ã£o posterior de compatibilidade AF_UNIX revalidada separadamente conforme VALIDACOES. Nenhuma chamada externa ou cÃ³pia operacional realizada. PrÃ³ximas aÃ§Ãµes: navegaÃ§Ã£o atividade/origem; conectar ConciliaÃ§Ã£o/Serpro/folha/Radar; finalizar identificaÃ§Ã£o de documentos e validar jornadas reais. Meta permanece ativa.

## V-150 â€” AÃ§Ã£o contextual e proteÃ§Ã£o de escrita

24/09/2026. D-131 registrado e implementado: origem da atividade acessÃ­vel por link, permissÃµes separadas de consulta/escrita e bloqueio efetivo ao auditor/financeiro nos serviÃ§os. Detalhe preserva tokens e layout; fontes e auditoria de UI na etapa 11. RegressÃ£o de 893 aprovados/2 ignorados/23 subtestes; checagens tÃ©cnicas passaram. Playwright segue sem transporte, sem aba aberta. PrÃ³ximo passo: atribuiÃ§Ã£o explÃ­cita de tarefas de mÃ³dulo/avulsas e histÃ³rico de redistribuiÃ§Ã£o, seguida das demais pontes e fonte-observaÃ§Ã£o; testes atuais nÃ£o comprovam jornada externa nem produto completo.

## V-151 â€” ResponsÃ¡vel explÃ­cito alimenta a agenda pessoal

24/09/2026. D-132 e assign_activity: formulÃ¡rio no detalhe, destinatÃ¡rios autorizados, motivo/histÃ³rico, detecÃ§Ã£o de alteraÃ§Ã£o concorrente e recusa em tarefa encerrada. Corrigida renderizaÃ§Ã£o de atividade sem responsÃ¡vel. 895 testes aprovados/2 ignorados/23 subtestes; checagens tÃ©cnicas passaram. Guia de atribuiÃ§Ã£o/recuperaÃ§Ã£o e checklist atualizados; UI sem validaÃ§Ã£o renderizada pelo transporte Playwright indisponÃ­vel. PrÃ³ximas aÃ§Ãµes: conectar ConciliaÃ§Ã£o/Serpro/folha/Radar e tratar observaÃ§Ãµes de fontes, mantendo distinÃ§Ãµes de aceitaÃ§Ã£o/importaÃ§Ã£o real; concluir testes integrados e homologaÃ§Ã£o. Objetivo segue ativo.

## V-152 â€” ObservaÃ§Ãµes ordenadas e repetÃ­veis

24/09/2026. D-133: aplicada ordem por dimensÃ£o, repetiÃ§Ã£o exata, preservaÃ§Ã£o de fotografia/estados, tratamento de conflitos e evidÃªncia da observaÃ§Ã£o aplicada. Falha da primeira execuÃ§Ã£o era fixture que sobrescrevia o estado com instÃ¢ncia antiga; corrigida e regressÃ£o repetida atÃ© 897 aprovados/2 ignorados/23 subtestes. Checagens tÃ©cnicas passaram; checklist e manual atualizados. PrÃ³ximas aÃ§Ãµes: conectar resultados persistidos de ConciliaÃ§Ã£o/Serpro/folha/Radar e adaptadores comprovados, com semÃ¢ntica explÃ­cita; nÃ£o representar guia/PDF disponÃ­vel como obrigaÃ§Ã£o aceita. Meta permanece ativa.

## V-153 â€” ConciliaÃ§Ã£o ligada Ã  atividade local

24/09/2026. D-134 e migration 0057: projeÃ§Ã£o Ãºnica por arquivo, comprovaÃ§Ã£o por movimento, reabertura e recuperaÃ§Ã£o explÃ­cita. ValidaÃ§Ã£o final com 898 aprovados/2 ignorados/23 subtestes; checagens tÃ©cnicas passaram. Sem integraÃ§Ã£o externa ou mudanÃ§a de template. Checklist e manual registram limites e comando de recomposiÃ§Ã£o. PrÃ³xima execuÃ§Ã£o: corrigir reconfirmaÃ§Ã£o apÃ³s desfazimento preservando histÃ³rico, completar navegaÃ§Ã£o Ã  origem seguindo workflow UI obrigatÃ³rio, ligar demais mÃ³dulos/fontes e validar jornada integrada. NÃ£o considerar essa ponte como prova de importaÃ§Ã£o ERP nem conclusÃ£o do objetivo.

## V-154 â€” Ciclo de desfazimento e reconfirmaÃ§Ã£o

24/09/2026. D-135 e migration 0058: decisÃµes preservadas, legado identificado, reconfirmaÃ§Ã£o revalida capacidade e atualiza atividade na mesma transaÃ§Ã£o. 899 aprovados/2 ignorados/23 subtestes; 8 testes de pontes repetidos apÃ³s ajuste de tipagem; checagens tÃ©cnicas passaram. Nenhuma integraÃ§Ã£o real ou alteraÃ§Ã£o de template. PrÃ³ximo passo: navegaÃ§Ã£o da atividade ao arquivo e apresentaÃ§Ã£o das decisÃµes com workflow UI obrigatÃ³rio, seguida das pontes Serpro/folha/Radar e adaptadores comprovados. Validar PostgreSQL/volume e jornada externa; objetivo permanece ativo.

## V-155 â€” Contexto do arquivo acessÃ­vel pela atividade

24/09/2026. D-136: link protegido, filtro explÃ­cito no destino, busca/paginaÃ§Ã£o sem perder arquivo e retorno Ã  atividade. CenÃ¡rio inicialmente sem mÃ³dulo habilitado corrigido; 57 testes passaram e 9 foram repetidos apÃ³s reforÃ§ar recorte de movimentos. Auditoria UI registrada, Playwright sem transporte; nenhuma sessÃ£o aberta. PrÃ³ximo passo: apresentar histÃ³rico de decisÃµes no movimento, seguir integraÃ§Ãµes Serpro/folha/Radar e fontes comprovadas; validar jornada renderizada e ambiente externo. Meta ativa.

## V-156 â€” DecisÃµes consultÃ¡veis no fluxo da ConciliaÃ§Ã£o

24/09/2026. D-137 implementado; corrigida apresentaÃ§Ã£o de aÃ§Ãµes para perfil consultivo. 57 testes focados passaram apÃ³s verificaÃ§Ãµes de histÃ³rico/escape/paginaÃ§Ã£o/auditor; checagens tÃ©cnicas passaram. Manual e checklists atualizados; navegador indisponÃ­vel, sem prova visual. PrÃ³xima execuÃ§Ã£o: conectar resultados persistidos dos mÃ³dulos restantes (Serpro, folha, Radar) Ã s atividades e observaÃ§Ãµes, seguindo capacidades reais e sem transformar guia/documento em aceite oficial. Continuar revisÃ£o integrada, PostgreSQL/volume e homologaÃ§Ã£o externa. Meta ativa.

## V-157 â€” Fotografias de folha acessÃ­veis pela importaÃ§Ã£o

24/09/2026. D-138 e migration 0059 ligam rotina antes sem chamador Ã  entrada existente. GravaÃ§Ã£o atÃ´mica de lote, conflito de referÃªncia recusado e documento informado disponÃ­vel na ficha. Teste web completo e regressÃ£o 902/2/23 conforme VALIDACOES; checagens tÃ©cnicas passaram. Manual/modelo CSV entregues. PrÃ³ximo passo: prÃ©via detalhada e atividade de conferÃªncia por empresa/competÃªncia, com reabertura diante de dados novos e comprovaÃ§Ã£o humana vigente; seguir Serpro/Radar e fontes comprovadas. NÃ£o considerar importaÃ§Ã£o local como homologaÃ§Ã£o ERP ou conclusÃ£o da meta.

## V-158 â€” ConferÃªncia da folha acompanha novos recebimentos

24/09/2026. D-139 e migration 0060 implementados: atividade Ãºnica, reabertura, evidÃªncia humana posterior e recuperaÃ§Ã£o explÃ­cita. RegressÃ£o 903/2/23 e checagens tÃ©cnicas passaram. Sem novo template ou alegaÃ§Ã£o visual/externa. PrÃ³xima execuÃ§Ã£o: atalho contextual atividade â†’ comparaÃ§Ã£o e prÃ©via de folha antes de confirmar; continuar Serpro/Radar e observaÃ§Ãµes de fontes homologadas, testes de concorrÃªncia/volume e validaÃ§Ã£o de jornada. Meta permanece ativa.

## V-159 â€” Atividade da folha mantÃ©m contexto da competÃªncia

24/09/2026. D-140 implementado com links de ida/retorno, filtro persistente e escopo revalidado. 106 testes focados/8 subtestes e checagens tÃ©cnicas passaram. Auditoria UI documentada; Playwright indisponÃ­vel sem prova visual. PrÃ³xima execuÃ§Ã£o: prÃ©via detalhada antes da importaÃ§Ã£o, seguida das pontes Serpro/Radar e fontes comprovadas; continuar validaÃ§Ã£o integrada e homologaÃ§Ãµes. Meta ativa.

## V-160 â€” Conferir linhas antes de importar folha

24/09/2026. D-141 implementado com prÃ©via paginada, empresa/valores explÃ­citos, isolamento consultivo e nenhuma gravaÃ§Ã£o em GET. 80 testes focados e checagens tÃ©cnicas passaram. Playwright sem transporte e CUA sem navegador habilitado; nenhum resultado visual presumido. PrÃ³xima execuÃ§Ã£o: integrar resultados persistidos de Serpro/Radar Ã  central, respeitando efeitos/estados comprovados; avanÃ§ar observaÃ§Ãµes de fontes e homologaÃ§Ã£o, concorrÃªncia/volume e validaÃ§Ã£o visual quando disponÃ­vel. Meta ativa.

## V-161 â€” ComunicaÃ§Ã£o DTE alimenta anÃ¡lise humana

24/09/2026. D-142 e migration 0061: mensagem persistida gera atividade Ãºnica, abertura comprovada fornece evidÃªncia de consulta e resultado incerto impede conclusÃ£o. PermissÃ£o de ciÃªncia agora exige carteira vigente no serviÃ§o antes de consumo/provedor. AtualizaÃ§Ã£o da central ocorre apÃ³s commit do recibo, com recuperaÃ§Ã£o local por sync_dte_activities. Teste de falha encontrou incompatibilidade do callback parcial com o tratamento de erros do Django; substituÃ­do por funÃ§Ã£o nomeada, mantendo o recibo recuperÃ¡vel. Resultados finais em VALIDACOES.md.

PrÃ³xima execuÃ§Ã£o: navegaÃ§Ã£o contextual ao resumo seguro DTE, demais resultados Serpro/Radar e integraÃ§Ã£o das observaÃ§Ãµes Ã s fontes comprovadas. Continuar validaÃ§Ã£o visual, concorrÃªncia PostgreSQL, volume e homologaÃ§Ã£o externa. Nenhuma chamada real, custo ou publicaÃ§Ã£o nesta entrega; meta ativa.

## V-162 â€” AnÃ¡lise DTE precisa corresponder ao teor disponÃ­vel

24/09/2026. RevisÃ£o encontrou confirmaÃ§Ã£o anterior satisfazendo conclusÃ£o apÃ³s abertura. D-143 implementado com verificaÃ§Ã£o direta do recibo, reabertura auditada e preservaÃ§Ã£o da confirmaÃ§Ã£o posterior na recuperaÃ§Ã£o. 48 testes/8 subtestes e checagens tÃ©cnicas passaram; detalhes em VALIDACOES.md. Manual/checklist atualizados. Sem mudanÃ§a visual ou validaÃ§Ã£o externa. PrÃ³ximo passo continua sendo navegaÃ§Ã£o contextual segura, demais pontes Serpro/Radar e fontes comprovadas, seguido de validaÃ§Ã£o integrada/visual/PostgreSQL. Meta ativa.

## V-163 â€” Resumo DTE acessÃ­vel no contexto da atividade

24/09/2026. D-144 implementado com navegaÃ§Ã£o local de ida/volta, restriÃ§Ã£o de mÃ³dulo e conservaÃ§Ã£o do formulÃ¡rio humano. Teste do percurso confirma ausÃªncia de abertura/consumo/conclusÃ£o e recusa apÃ³s revogaÃ§Ã£o. Resultados e limitaÃ§Ã£o visual em VALIDACOES.md; manual/checklists atualizados. PrÃ³xima execuÃ§Ã£o: demais resultados Serpro/Radar alimentando a central e observaÃ§Ãµes ligadas Ã s fontes comprovadas, mantendo revisÃ£o de permissÃµes/recuperaÃ§Ã£o. Validar navegador e PostgreSQL quando disponÃ­veis; nÃ£o confundir testes locais com homologaÃ§Ã£o real. Meta ativa.

## V-164 â€” AnÃ¡lises do Radar entram na carteira

24/09/2026. D-145 implementado com seleÃ§Ã£o humana, serviÃ§o protegido, versionamento, prova, reabertura e recuperaÃ§Ã£o local. Coletor respeita apenas vÃ­nculos existentes; pÃ¡gina devolve anÃ¡lise Ã  central. Corrigida falha atual escondida por sucesso antigo na saÃºde da fonte. RegressÃ£o 915/2/23 e verificaÃ§Ã£o focada final conforme VALIDACOES.md. Manual/checklists/auditoria atualizados; nenhuma homologaÃ§Ã£o externa ou visual presumida.

PrÃ³xima execuÃ§Ã£o: revisar demais resultados Serpro (obrigaÃ§Ãµes/guias/parcelamentos) e ligaÃ§Ã£o das observaÃ§Ãµes Ã s fontes comprovadas, incluindo reavaliaÃ§Ã£o de fechamento. Continuar revisÃ£o integrada, volume/concorrÃªncia PostgreSQL, navegador e homologaÃ§Ã£o real autorizada. Meta permanece ativa.

## V-165 â€” AutorizaÃ§Ã£o DCTFWeb sobrevive Ã  fila

24/09/2026. RevisÃ£o encontrou ausÃªncia de revalidaÃ§Ã£o do solicitante no worker. D-146 implementado no serviÃ§o e na execuÃ§Ã£o, com falha recuperÃ¡vel e liberaÃ§Ã£o de reserva nÃ£o enviada. 29 testes finais e checagens tÃ©cnicas passaram; fixture comum/tela corrigido apÃ³s duplicaÃ§Ã£o detectada. Manual/checklist atualizados. Sem UI, migration, provedor real ou homologaÃ§Ã£o externa.

PrÃ³ximo passo: estender verificaÃ§Ã£o a emissÃ£o de guias e parcelamentos, entÃ£o integrar documentos/resultados Ã  central preservando distinÃ§Ã£o entre consulta, aceite, guia e pagamento. Continuar observaÃ§Ãµes de fontes comprovadas, concorrÃªncia/volume e validaÃ§Ã£o visual. Meta ativa.

## V-166 â€” RevogaÃ§Ã£o respeitada por guias e PARCSN

24/09/2026. D-147 implementado nos dois serviÃ§os/workers. RegressÃ£o 929/2/23 e checagens tÃ©cnicas passaram; fixtures passaram a declarar autorizaÃ§Ãµes reais do cenÃ¡rio. Manual/checklist atualizados. Sem migration/UI ou chamada externa.

PrÃ³xima execuÃ§Ã£o: corrigir emissÃ£o de guias apÃ³s transporte incerto/retorno sem PDF, preservando reserva e evitando reemissÃ£o cega; revisar estados e recuperaÃ§Ã£o na interface, seguindo workflow UI obrigatÃ³rio. O checklist genÃ©rico anterior foi corrigido, pois nÃ£o comprovava esse caso. Depois, ligar resultados Ã s atividades/fechamentos e continuar fontes, concorrÃªncia/volume, navegador e homologaÃ§Ã£o. Objetivo ativo.

## V-167 â€” Regra de reemissÃ£o corrigida pelo proprietÃ¡rio

24/09/2026. ImplementaÃ§Ã£o provisÃ³ria de incerteza testada (932/2/23 e 23 focados finais), mas bloqueio de reemissÃ£o foi rejeitado pelo proprietÃ¡rio. D-149 substitui essa inferÃªncia: permitir reemissÃ£o cobrada por guia; modalidade do adicional perguntada, ainda pendente. Preservar incerteza/evidÃªncias e revisar serviÃ§o, UI e testes para a regra efetiva. NÃ£o liberar o estÃ¡gio provisÃ³rio nem considerar testes como aprovaÃ§Ã£o de produto. Nenhuma migration aplicada fora de testes. Objetivo ativo; continuar trabalhos independentes enquanto aguarda definiÃ§Ã£o comercial.

## V-168 â€” PreservaÃ§Ã£o de tentativas enquanto aguarda definiÃ§Ã£o comercial

24/09/2026. D-150 implementado em FiscalGuideAttemptEvent/guide_history, serviÃ§o e worker. Migration 0064 aditiva, somente em testes. HistÃ³rico preserva estado legado conhecido e identifica sua limitaÃ§Ã£o, solicitaÃ§Ã£o, protocolos, retorno criptografado e referÃªncia de consumo. Nova tentativa limpa resultado anterior somente apÃ³s preservÃ¡-lo. Testes focados 26 aprovados; regressÃ£o final 935/2/23 em 92,03 s; Ruff/MyPy/check/migrations aprovados. Nenhuma mudanÃ§a de UI nem chamada externa.

PrÃ³xima execuÃ§Ã£o: disponibilizar histÃ³rico com escopo autorizado e workflow de interface obrigatÃ³rio; implementar reemissÃ£o com confirmaÃ§Ã£o de custo apÃ³s resposta de D-149, sem inventar tarifa. Integrar resultados Ã s atividades/fechamentos respeitando consulta, emissÃ£o, aceite e pagamento distintos; continuar recuperaÃ§Ã£o, fontes comprovadas e validaÃ§Ãµes visual/PostgreSQL/externa. Manual e checklist atualizados. Objetivo permanece ativo; esta entrega nÃ£o conclui reemissÃ£o nem a central.

## V-169 â€” Consulta de tentativas preservadas

24/09/2026. D-151 implementado em guide_detail, partial/CSS especÃ­ficos, rota de PDF por evento e testes de tela/acesso. PaginaÃ§Ã£o de 20 eventos; dados brutos nÃ£o exibidos; PDF anterior mantÃ©m referÃªncia Ã  tentativa e revalida acesso. Rodada conjunta 100 aprovados/1 falha de fixture; corrigido perfil inexistente, rodada final 28 aprovados em 58,62 s. Ruff/MyPy/check/migrations passaram. Sem migration nova, provedor real ou consumo.

PrÃ³xima execuÃ§Ã£o: validar visualmente quando transporte Playwright estiver disponÃ­vel; implementar reemissÃ£o apÃ³s modalidade de adicional respondida em D-149. Prosseguir nas pontes de resultados com atividades/fechamentos, sem transformar consulta/guia em aceite/pagamento. Pendentes recuperaÃ§Ã£o estruturada, fontes homologadas, PostgreSQL e piloto. Meta permanece ativa.

## V-170 â€” Escopo de leitura por mÃ³dulo e empresa

24/09/2026. D-152 implementado na consulta de carteira dos mÃ³dulos Guias/Integra, preservando regras de administraÃ§Ã£o e suporte existentes. Corrigido contador DTE que abrangia todo o escritÃ³rio. Testes finais 939 aprovados, 2 ignorados, 25 subtestes; Ruff/MyPy/check/migrations passaram. Sem migration nova, mudanÃ§a visual ou chamada externa. Manual/checklist atualizados.

PrÃ³xima execuÃ§Ã£o: auditar a cobertura efetiva da central contra o objetivo e consolidar pendÃªncias atuais, pois checklists de entregas histÃ³ricas ainda contÃªm itens depois tratados. Inspecionar os pontos de chamada das pontes e as observaÃ§Ãµes: record_source_observation hoje sÃ³ Ã© chamado nos testes. Implementar ligaÃ§Ãµes sustentadas por dados persistidos/contratos comprovados; nÃ£o inventar aceite oficial, fechamento de ERP, aplicaÃ§Ã£o por empresa ou cobranÃ§a. D-149 segue aguardando resposta; navegador, PostgreSQL, recuperaÃ§Ã£o e fontes reais permanecem pendentes. Objetivo ativo.

## V-171 â€” Cobertura consolidada e correÃ§Ã£o de resoluÃ§Ã£o NFS-e

24/09/2026. Matriz na etapa 11 confronta cada requisito com os pontos de chamada presentes. Pontes existentes confirmadas; ausÃªncia de ligaÃ§Ã£o dos demais resultados Serpro e de adaptadores Ã  rotina de observaÃ§Ãµes registrada expressamente. Corrigido reaproveitamento de prova NFS-e e conflito da segunda resoluÃ§Ã£o no histÃ³rico de acumuladores, encontrado no teste de percurso. 85 testes finais passaram; Ruff/MyPy/check/migrations passaram. Sem migration/UI nova nem chamadas reais.

PrÃ³xima execuÃ§Ã£o: priorizar integraÃ§Ã£o dos resultados Serpro persistidos ainda ausentes da central. Definir qualquer fluxo de negÃ³cio nÃ£o coberto com o proprietÃ¡rio, preservando distinÃ§Ã£o entre emissÃ£o, consulta, aceite e pagamento; nÃ£o inferir fechamento oficial. Para fontes ERP, descobrir contrato/dado comprovado antes de alimentar record_source_observation. D-149 segue pendente. Continuar homologaÃ§Ã£o e validaÃ§Ã£o visual/concorrÃªncia quando os ambientes estiverem disponÃ­veis; nÃ£o marcar completo.

## V-172 â€” PostgreSQL local e concorrÃªncia real entre conexÃµes

24/09/2026. Encontrada imagem PostgreSQL 17 existente no Docker local; executada validaÃ§Ã£o isolada com tmpfs/loopback, sem usar o banco existente. ConfiguraÃ§Ã£o test_postgresql adicionada e procedimento no manual. Primeira suÃ­te identificou falhas reais de locks em relaÃ§Ãµes opcionais; corrigidas conforme D-154. Testes streaming corrigidos para usar fechamento do cliente Django. Resultado final: 942 aprovados, 1 ignorado, 25 subtestes em 177,22 s; checagens estÃ¡ticas/migrations aprovadas. ContÃªiner encerrado e remoÃ§Ã£o confirmada; nenhuma publicaÃ§Ã£o/custo ou chamada Serpro.

Q-40 enviada ao proprietÃ¡rio: separar emissÃ£o, conferÃªncia e pagamento ou exigir conferÃªncia dentro da atividade de emissÃ£o. NÃ£o implementar a conclusÃ£o dependente sem resposta. D-149 permanece pendente. PrÃ³xima execuÃ§Ã£o: ligaÃ§Ãµes Serpro/central apÃ³s decisÃµes aplicÃ¡veis, contrato de observaÃ§Ãµes das fontes e validaÃ§Ã£o visual. Playwright MCP vinha sem transporte; Puppeteer estÃ¡ instalado no reporting, mas seu Chrome esperado nÃ£o estÃ¡ no cache. Isso nÃ£o comprova ausÃªncia de outros navegadores locais; verificar alternativas sem perfil pessoal se necessÃ¡rio. Manter limites de D-73, sem confundir teste PostgreSQL com homologaÃ§Ã£o completa.


**AtualizaÃ§Ã£o V-173 (24/09/2026):** Playwright local com Edge disponÃ­vel, apesar do MCP sem transporte. Central validada em 52 combinaÃ§Ãµes de pÃ¡gina/perfil/tema/viewport, 17 verificaÃ§Ãµes, sem overflow ou erro de console. Capturas desktop/mobile inspecionadas; carteira e leitura do auditor verificadas. NÃ£o foram validados todos os fluxos de alteraÃ§Ã£o, carregamento ou fontes reais. Scripts repetÃ­veis: qa_ui_server.py (QA_REVIEW_SUITE=central), qa_central_fixture.py e qa_central_browser.cjs. Contextos/navegador e servidor encerrados. D-149/Q-40 seguem pendentes; meta ativa.

**AtualizaÃ§Ã£o V-174 (24/09/2026):** D-155 projeta resultados Serpro persistidos em atividades Ãºnicas, com evidÃªncia, impedimento e retorno Ã  origem. Guia/DAS disponÃ­vel nÃ£o conclui pagamento, aceite ou fechamento; DCTFWeb conclui sÃ³ obtenÃ§Ã£o; PARCSN conclui sÃ³ consulta. Migration 0065 e sync_serpro_activities recompÃµem estado sem fornecedor. Corrigida atribuiÃ§Ã£o tardia ao solicitante sem substituir responsÃ¡vel manual. RegressÃ£o: 944 aprovados, 3 ignorados, 25 subtestes; navegador local: 64 combinaÃ§Ãµes/21 verificaÃ§Ãµes sem erro/overflow. D-149/Q-40, recuperaÃ§Ã£o externa e fontes reais continuam pendentes.

**V-177 (24/09/2026):** corrected the invalid visible action after completion: evidence remains permitted and auditable, but block and second-completion controls no longer appear. The synthetic journey covered evidence, completion, trail, agenda return, and mobile: 64 screens/23 checks without console errors or overflow. Focused tests 45/8, Ruff, Django, migrations, and script syntax passed. No real source, cost, transmission, reissue, or commercial change; D-149 remains pending.

**V-178 (24/09/2026):** full local regression passed with 948 tests, 3 known skips, and 25 subtests in 81.08 s. It validates local module integration after the central review, without claiming external sources, costed reissue, transmission, recovery timing, volume, or pilot acceptance.

**V-179 (24/09/2026):** D-157 requires an exact declared capability under source lock before an observation can alter processing or obligation state. Missing-capability, stale-source, and disabled-source tests preserve activity state and create no observation. Focused tests 32/8 plus Ruff, MyPy, Django and migrations passed; no external call, cost, migration, or source homologation. Full local regression after the change: 949 passed, 3 skipped, 25 subtests in 80.61 s.

**V-180 (24/09/2026):** expanded unified recovery validation to persisted NFS-e, guide, DCTFWeb, and PARCSN records in one command, with idempotent replay. Focused recovery tests: 17 passed; Ruff, MyPy command, Django, and migrations passed. No external provider, issuance, transmission, consumption, or cost.

**V-181 (24/09/2026):** registrada D-158: nao inferir qualquer custo, tarifa ou repasse; D-149 autoriza reemissao com custo adicional, mas seus parametros continuam dependentes do proprietario. Ampliado o teste de `recover_operational_center`: NFS-e, Triagem, Conciliacao, folha, DTE, guia, DCTFWeb e PARCSN persistidos recompõem uma atividade cada e o segundo replay nao duplica. 17 testes focados, Ruff, check e migrations passaram. Sem chamada externa, custo ou migration. Proxima lacuna local: Radar e falhas por dominio; permanecem fontes reais, D-73, volume, piloto e D-149.

**V-182 (24/09/2026):** teste de recuperacao do Radar acrescentado: uma publicacao previamente vinculada por pessoa e reprojetada com `radar=1`; nao ha coleta, vinculacao inferida, atividade ou evento duplicado. Suite focada das pontes: 18 aprovados; Ruff, check, migrations e diff-check passaram. Proxima lacuna: observacoes ERP sem adaptador homologado e validacoes externas D-73/piloto; D-149 continua pendente de parametros comerciais.

**V-183 (24/09/2026):** D-159 impede que um retorno tardio de fonte desativada a reative ou altere a atividade; o registro fica em historico e falhas podem indicar indisponibilidade preservando `disabled`. 51 testes das pontes/central e 8 subtestes passaram, com Ruff, MyPy da operacao, check, migrations e diff-check. Proxima lacuna implementavel: percurso administrativo de reativacao com permissao e UI; adaptadores ERP e homologacao externa continuam pendentes. Nenhuma chamada externa ou custo.

**V-184 (24/09/2026):** D-160 implementada na configuracao: reativacao de fonte exige owner/admin, sem suporte, checkbox explicito, preserva capacidades/fotografia e retorna a `not_configured`; auditoria registra transicao e nao ha chamada externa. Testes owner/auditor passaram isoladamente. UI revisada com UI/UX Pro Max, Watermelon Agndex, Refero Basedash, SaaSFrame Prelude e Karbon; WIG revisada. Playwright Edge local: 66 telas/24 verificacoes, desktop/mobile, foco, sem overflow/console; servidor e navegador encerrados. Proxima lacuna: contratos e adaptadores ERP homologados; D-149 ainda aguarda parametros de cobranca.

**V-185 (24/09/2026):** D-161 implementada: geracao recorrente exige relacoes do mesmo escritorio e responsavel operacional com carteira atual; atribuicao invalida vira atividade sem responsavel com evento, e formulario recusa novo vinculo invalido. Central: 36/8; recorrencia: 7 aprovados, 1 skip PostgreSQL, 4 subtestes. Checagens tecnicas passaram. Playwright Edge local: 70 telas/28 verificacoes, modelos desktop/mobile, sem overflow/console; QA encerrado. Proxima lacuna: homologar contrato ERP/control plane e validar em PostgreSQL/carga; D-149 segue pendente de parametros comerciais.

## V-186 — Ficha da empresa segue o prazo efetivo da central

24/09/2026. Corrigida a ordenacao local da lista de atividades na ficha de empresa. Ela agora replica D-124, ja aplicado em agenda e fila: usa prazo interno quando houver; senao usa legal; itens sem data ficam por ultimo, com desempate estavel. O teste de view cobre um prazo legal vencido, um prazo interno futuro com legal anterior e uma atividade sem prazo.

Validacao: teste focado 1 aprovado/75 desmarcados; Ruff, MyPy, Django check, migrations e diff-check sem erro. A revisao Playwright/Edge sintetica passou com 82 telas e 40 verificacoes, incluindo ficha em 1440/390 px para owner, operator e auditor, sem overflow ou console error. Captura desktop revisada. Nenhuma fonte, custo, reemissao, transmissao ou homologacao externa foi acionada. Proximo trabalho permanece contrato ERP/adaptador, validacao com fontes reais, recuperacao D-73, carga e piloto; D-149 continua pendente de parametros comerciais.

## V-187 — Escrita da central revalida vínculo atual

24/09/2026. D-162 elimina confiança em objeto de membro antigo nas operações de atividade. Antes de registrar evidência, impedir, concluir ou redistribuir, o serviço busca o vínculo atual no escritório e exige usuário ativo, perfil operacional, carteira da empresa e, para redistribuir, papel atual de owner/admin. Um autor diferente do membro também é recusado. O teste cobre rebaixamento após carregar o membro, ator externo e administrador rebaixado que ainda teria concessão de empresa; estado, eventos e evidências permanecem intactos.

Validação: `tests/test_operational_center.py` 38 aprovados/12 subtestes em 30,68 s; Ruff, MyPy, Django check, migrations e diff-check passaram. Sem alteração visual, fonte, custo, emissão, transmissão ou publicação. Controle externo, concorrência PostgreSQL, fontes reais, recuperação D-73, volume, piloto e parâmetros D-149 continuam pendentes.

**Complemento V-187 (24/09/2026):** regressão HTTP da área do escritório: `tests/test_hub_workspace_views_django.py` aprovou 76 testes em 59,27 s, cobrindo carteira, detalhes e POSTs das atividades após a revalidação de vínculo.

**Regressao integral V-187 (24/09/2026):** `pytest -q` passou com 962 aprovados, 3 skips conhecidos e 29 subtestes em 91,62 s. Os skips permanecem Playwright Python opcional e cenarios de locks PostgreSQL cobertos no ambiente proprio; o resultado nao homologa fontes externas, recuperacao cronometrada, volume, piloto ou D-149.

## 24/09/2026 â€” RevisÃ£o integral da landing (D-163 / V-188)

Pedido: simplificar a landing, pesquisar referÃªncias online e reforÃ§ar clareza e identidade. Entregues nova narrativa, pauta ilustrativa estÃ¡tica, recursos por tarefa, FAQ/CTAs e CSS exclusivo com tokens da marca. Mantidos gates de demo/Copiloto e limites comerciais. Aplicados ui-ux-pro-max, Watermelon e auditoria atual das Web Interface Guidelines. Pesquisa e diagnÃ³stico em [relatÃ³rio](../cica-landing-review-2026-09-24.md).

27 testes focados passaram; Django check, Ruff e diff-check limpos. Playwright MCP: 12 combinaÃ§Ãµes 320â€“1440 px/claro-escuro, teclado/foco, links, FAQ, tema e contexto sem JS. Zero overflow/console; contraste renderizado mÃ­nimo 5,45:1. Capturas inspecionadas e contextos, aba e servidor encerrados. Sem acesso a dados reais, chamadas pagas, mensagens, rastreamento ou publicaÃ§Ã£o. V-188 registra os estados e limites exatos; nenhuma promessa quantitativa de venda. PrÃ³ximo trabalho comercial depende de mediÃ§Ã£o e homologaÃ§Ã£o jÃ¡ previstas, sem iniciar outra etapa por inferÃªncia.

## 24/09/2026 â€” V-189: sequÃªncia efetiva do agente DomÃ­nio Local

Corrigido um retorno prematuro no processador .NET: a sincronizaÃ§Ã£o de empresas encerrava `RunOnce` antes de a fase jÃ¡ allowlisted de extratos bancÃ¡rios comeÃ§ar. Agora a paginaÃ§Ã£o de empresas apenas encerra sua prÃ³pria fase, e a de extratos Ã© executada se o serviÃ§o nÃ£o tiver sido cancelado. TambÃ©m foi corrigido o argumento da URL autenticada em `AgentClient.DownloadAsync`, eliminando a falha de build do projeto. Build Release concluÃ­da; 43 testes Python relacionados ao agente/central passaram, junto de Ruff, MyPy, Django check e migraÃ§Ãµes. NÃ£o houve ODBC real, envio, custo, MSI ou homologaÃ§Ã£o externa. A prova de paginaÃ§Ã£o, cancelamento, retomada e idempotÃªncia continua no piloto da etapa 12.


## 24/09/2026 — V-190: checklist da central reconciliado

A matriz da etapa 11 foi comparada às entregas V-125 a V-189. Itens locais concluídos deixaram de aparecer como pendentes; continuaram abertos apenas contratos e provas externas que ainda não existem. Não houve mudança de código, fonte, custo, publicação ou alegação de homologação.

## 24/09/2026 — V-191: recuperação local e recorrência revisadas

Auditados o replay unificado e a recorrência da central. O Radar mantém a seleção humana como condição de projeção; portanto, a recuperação não cria análise para empresa que nunca a pediu. As demais pontes recuperam fatos locais persistidos e o segundo replay não duplica atividades. Suite central: 63 aprovados, 1 skip PostgreSQL, 16 subtestes; Ruff, check e migrations passaram. Nenhuma chamada externa, custo, transmissão ou homologação. Permanecem pendentes contrato de estados ERP, recuperação medida, volume, piloto e D-149.

## 24/09/2026 — V-192: UI da central revisada em jornada sintética

Revisadas agenda, fechamentos e estilos relacionados sob ui-ux-pro-max e Web Interface Guidelines atualizadas. Playwright/Edge local percorreu 82 telas/40 verificações, três perfis, temas claro/escuro e 1440/390 px; cenário adicional em 844×390 com movimento reduzido confirmou foco visível, ausência de overflow e console limpo. Inspeção visual de agenda móvel e gestão desktop aprovada. Watermelon não estava exposto nesta sessão. Servidor, contextos e navegador foram encerrados. Nenhuma fonte, custo, envio ou homologação foi acionado; fontes reais, carga, leitor de tela, recuperação medida e piloto seguem pendentes.

## 24/09/2026 — V-193: contrato de observações das fontes pesquisado

Pesquisa oficial reforçou que Domínio tem estados internos e eSocial distintos, enquanto o Siescon público descreve seu Gerenciador de tarefas sem expor contrato de API/layout. Atualizado manual de homologação com requisitos objetivos para o fornecedor antes de adaptar ou declarar capacidades. Sem leitura de fonte, credencial, custo ou mudança de código de integração.

## 24/09/2026 — V-194: regressão integrada após auditoria de integridade

Revisados modelo e serviço de observações quanto a replay, conflito temporal, indisponibilidade, reabertura e retorno tardio. A regressão integral passou: 962 aprovados, 3 skips conhecidos e 29 subtestes em 101,79 s. Não houve chamada externa, custo, envio, publicação ou homologação; pendências externas preservadas.

## 24/09/2026 — V-195: correção visual no endereço efetivo

As capturas do proprietário revelaram HTML antigo com CSS novo na porta 8000, fora da instância isolada usada em V-188. Dois listeners foram identificados por netstat; o processo antigo foi encerrado após confirmação e a instância atual preservada. Cache de templates locais removido sem mudar produção. Após os pedidos de design e ai-design-skills, instalada/aplicada landing-page-design: Manrope local com OFL, escala e espaçamento, botões sem flechas, FAQ com seis perguntas fixas. A regra global foi atualizada para exigir essa skill em toda landing. Auditoria completa atualizada dos arquivos e Playwright MCP em 12 combinações; 4 testes aprovados, check/Ruff/diff-check sem falhas. Abas/contextos fechados, servidor do usuário ativo. Sem publicação, custo ou medição de venda; detalhes e limites em V-195.

## 24/09/2026 — V-196: landing reconstruída do zero

O retorno do proprietário substituiu a restauração da tela anterior por uma reconstrução integral. Foram refeitos HTML, copy, hierarquia, prova visual e CSS. A paleta agora é neutra, com papel quente, grafite e terracota; verde aparece somente como estado positivo. A nova central de fechamento mostra fila, responsáveis, progresso e próxima decisão com dados declaradamente fictícios. O teste de 14 dias permanece como ação principal, enquanto demo, Copiloto e integrações respeitam seus gates e limites reais.

Aplicadas as skills relevantes de landing, conversão, marca, design system, UI e UX; consultados Watermelon, Front, Karbon e Pennylane. A auditoria das guidelines corrigiu contrastes e `theme-color`. Playwright MCP verificou 320–1440 px, claro/escuro, teclado, foco, FAQ, links, sem JavaScript, console e rede, sem overflow ou falha de contraste após a correção. 27 testes focados, Django check, Ruff e diff-check passaram. Capturas foram inspecionadas, abas encerradas e servidor 8000 preservado. Sem publicação, custo, rastreamento ou alegação de aumento de vendas; detalhes em V-196 e no relatório da landing.

## 24/09/2026 — V-197: rotina e integrações sem aparência de template

Atendido o ajuste pontual do proprietário: a sequência de três benefícios foi substituída por uma atividade operacional completa, e os três cards de status das integrações viraram uma faixa única com Domínio, Integra Contador, e-mail e Siescon. Removidas da landing as ressalvas de configuração, validação e preparação; recursos e FAQ foram alinhados à apresentação de produto pronto definida em D-169.

UI/UX Pro Max e guidelines atuais foram reconsultados; Watermelon não retornou composição correspondente, e cards/bento foram deliberadamente evitados. Após corrigir contraste residual, Playwright MCP aprovou 12 combinações de largura/tema, os recortes desktop/mobile, FAQ por teclado, contexto sem JavaScript e console limpo. 4 testes, Django check, Ruff e diff-check passaram. Abas fechadas e servidor 8000 mantido.

## 25/09/2026 — V-198: Fedrizzi sincronizada e gate de ativação confirmado

Executadas leituras allowlisted no DSN Fedrizzi `contabil`: 576 empresas foram identificadas; a sincronização local espelhou 576 empresas e 10.000 registros normalizados sem escrever no Domínio. A consulta de guias retornou 3.335 registros, mas o contrato atual não disponibiliza vencimento. O console de desenvolvimento recebeu vínculo local e auditado de owner, sem convite/e-mail, e habilitou os sete módulos pelo próprio formulário. Nenhuma chamada cobrada, emissão, transmissão ou integração externa foi feita.

A inspeção do console em Edge confirmou seleção dos módulos sem erro de console. A área da Fedrizzi, em desktop e celular, recusou corretamente a operação com “Ativação pendente”: não há contrato vigente. O fluxo não foi burlado. Para prosseguir com agenda, modelos e testes operacionais reais, o responsável precisa definir no Console o contrato de homologação sem cobrança ou o contrato real, incluindo prazo/status; não foi presumido preço, prazo ou cobrança.

## 25/09/2026 — V-199: Fedrizzi como parceiro interno de homologação

Registrada D-170 e implementada uma condição explícita de parceiro interno, distinta de demo e de contrato. O Console permite a Developer/Admin ativar a operação sem contrato comercial e sem cobranças; o encerramento requer confirmação e devolve acesso pendente. Aplicada na Fedrizzi pelo formulário do Console: `active`, 0 contrato comercial, 7 módulos e 576 empresas. Nenhuma chamada externa, emissão, transmissão, ciência ou consumo foi executado.

Corrigido também o texto de Integrações, que ainda dizia “teste de 14 dias”; ele agora descreve corretamente a homologação interna sem cobrança. Playwright/Edge aprovou Console, Integrações e área de trabalho no ambiente Fedrizzi em desktop, celular e paisagem reduzida, sem overflow ou console error. Regressão Console/área: 103 aprovados em 60,13 s; Ruff, MyPy, check e migrations passaram. Ainda faltam modelos/prioridades aprovados para materializar a pauta real, pois os dados atuais não fornecem vencimentos de guia e eles não serão inferidos.

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

## 28/09/2026 — V-202: NFS-e isolado, backup 07129 e Fly.io preparado

Corrigido o menu da assinatura exclusivamente NFS-e para refletir o bloqueio que as views já aplicavam. Em cenário sintético, Playwright confirmou redirecionamento ao Fiscal, ausência de Visão geral/Atividades e 403 nas rotas não contratadas em desktop e celular. Foram aplicados UI/UX Pro Max, consulta ao Watermelon sem resultado correspondente, referências de permissões SaaS e auditoria atual das Web Interface Guidelines. Treze testes focados, Ruff, MyPy, Django check e diff-check passaram.

O backup autorizado 07129 foi validado, extraído em área temporária e iniciado no SQL Anywhere, sem alterar o original. A autenticação interna recusou as credenciais disponíveis; é necessária a credencial de “Usuário Externo” criada nesse escritório para ler os registros. O agente recebeu o contrato allowlisted de `EFACUMULADOR`, em lotes de 500, e o build Release e os dois testes do endpoint passaram. O servidor e a extração temporários foram eliminados; nenhum dado identificável foi registrado.

No Fly.io foram criados a organização `cica` e o app vazio `cica-contabil`; configuração validada, sem deploy ou infraestrutura faturável. O próximo passo é a aprovação específica do custo recorrente para Postgres, Redis, storage e máquinas, seguida pelos segredos, migrações e homologação operacional. Detalhes e limites estão em D-175/V-202.

## 28/09/2026 — V-203: produção Fly.io e credencial do backup 07129

Após a aprovação explícita da arquitetura de aproximadamente US$ 11,28/mês, foram publicados web, worker/beat, Postgres não gerenciado, Valkey autogerenciado e Tigris privado em `gru`. Migrações principal/knowledge, check de produção, health de banco/cache, página pública, estáticos versionados, ping Celery e ciclo criar/ler/apagar no storage passaram. DNS Fly: `cica-contabil.fly.dev`, `66.241.125.197` e `2a09:8280:1::19f:191b:0`. O hostname próprio ainda precisa ser informado para certificado e configuração Django. Limitações de HA, WAL, Sentry e mTLS estão registradas em D-177/V-203.

A cópia temporária do backup 07129 foi reaberta. O contêiner usa a chave separada do Domínio Web; o login/senha informado para gerar o backup foi recusado pelo SQL Anywhere, com e sem a barra escrita antes de `@`. Nenhuma empresa ou acumulador real foi extraído/importado. Falta a credencial interna de “Usuário Externo” do banco Domínio.

## 28/09/2026 — V-204: Bianchi & Rizzotto preparado para carga NFS-e

O proprietário confirmou que o backup 07129 pertence à Bianchi & Rizzotto. O tenant `bianchi-rizzotto` foi criado em produção com somente NFS-e habilitado e fonte de backup preparada; demais módulos ficaram explicitamente desabilitados. Não foi criado contrato, preço, usuário nem dado fiscal fictício. A produção confirma zero empresas e zero acumuladores até a leitura real.

A tentativa adicional com o usuário padrão `Externo` também foi recusada. A cópia extraída foi preservada sob ACL restrita e o servidor local encerrado. O único bloqueio para executar a carga é a senha do Usuário Externo existente no snapshot do Domínio.

## 28/09/2026 — V-204: conexão pública revalidada

Após a captura de `ERR_CONNECTION_RESET`, a produção foi diagnosticada sem alteração. Web e worker estavam iniciados, o check Fly passava, banco e cache estavam `ok`, DNS A/AAAA e TCP/443 funcionavam, o TLS era válido e HTTP redirecionava para HTTPS. A página inicial respondeu 200 em vinte tentativas consecutivas, entre 62 e 196 ms, sem erro, reinício ou OOM nos logs disponíveis.

A falha transitória não foi reproduzida; por isso não houve restart nem redeploy. O histórico mostra uma primeira release falha durante a publicação e as cinco seguintes concluídas, mas não há telemetria retida suficiente para afirmar que essa foi a causa da captura. A validação visual não foi repetida porque o MCP não ofereceu browser nesta sessão. Detalhes e limites estão em V-204.

## 28/09/2026 — V-205: domínio próprio preparado, correção DNS pendente

Registrada D-179 para `cicacontabil.com.br` e `www`. Os certificados foram criados no Fly e os dois hostnames foram incluídos explicitamente em `ALLOWED_HOSTS` e nas origens CSRF. Web e worker reiniciaram normalmente e o health de banco/cache voltou a passar.

A zona HostGator ainda publica dois registros A: o Fly `66.241.125.197` e o legado `162.240.81.81`. O segundo distribui conexões para fora da aplicação e impede a verificação dos certificados. Falta removê-lo no painel DNS; A/AAAA do Fly e CNAME de `www` devem permanecer. Sem acesso ao painel ou browser nesta sessão, essa alteração externa não foi simulada nem marcada como concluída.

O proprietário removeu posteriormente o A legado. Nameservers autoritativos, Cloudflare e Google passaram a retornar somente o Fly, e os certificados Let's Encrypt de apex e `www` ficaram ativos. A falha restante era o cache DNS local do Windows ainda contendo `162.240.81.81`. Após limpar esse cache, cinco requisições ao domínio raiz e três ao `www` retornaram 200 pelo IP correto, com TLS válido. O domínio próprio ficou operacional nos testes executados.

O Edge já aberto ainda conservou o estado anterior e mostrou timeout. Uma instância isolada do próprio Edge, com perfil temporário novo, abriu o HTML completo do domínio; proxy, IPv4, TLS e health continuavam normais. A pendência ficou limitada ao cache/socket da sessão antiga do navegador. As abas do usuário foram preservadas, sem encerramento forçado.

## 28/09/2026 — V-209: carga real do backup 07129 concluída

O Domínio local foi alinhado ao ajuste oficial 10.6A-08.10, com checksum e assinatura do instalador validados. `GERENTE`/`lua` abriu a cópia restaurada e o fluxo suportado do produto criou um usuário externo somente leitura. A origem confirmou 208 empresas e 15.701 acumuladores, sem órfãos, duplicidades de chave ou nomes vazios.

O lote `d4578c99-7258-490e-aa99-c992cf5d9703` foi importado exclusivamente no tenant `bianchi-rizzotto` e terminou com 15.909 registros criados, zero atualizados, zero ignorados e zero erros. O destino contém 208 empresas, 15.701 acumuladores e 15.701 históricos; a fonte está pronta e somente NFS-e permanece habilitado. Uma saturação transitória do Postgres legado foi contornada por retomada idempotente em páginas menores, sem ampliar o custo; health final de banco/cache e todos os checks do Postgres passaram.

## 28/09/2026 — V-210: histórico compacto por contraparte e serviço

A cópia temporária revelou as tabelas fiscais `efservicos` e `efentradas`, relacionadas a clientes/fornecedores e ao acumulador da própria empresa. A extração agregou os registros antes da saída e pseudonimizou CNPJ/CPF com o mesmo SHA-256 truncado usado pela coleta NFS-e. Não foram enviados nomes, notas, valores, descrições ou XMLs históricos.

Produção recebeu 49.199 observações únicas de 188 empresas no lote `b4551285-7f15-4c20-9a13-7bbba68ba3ff`, sem atualização, descarte, órfão ou critério vazio. A fonte ganhou a capacidade `accumulator_observations`; 9.379 chaves historicamente ambíguas foram identificadas para revisão, nunca para escolha arbitrária. O agente e a ponte de backup foram preparados para repetir a agregação. Build Release: zero avisos/erros. Testes focados: 9 aprovados. Ruff: aprovado. A coleta ADN segue desabilitada e a proteção local de ambiguidade precisa ser publicada antes de ativá-la.

## 29/09/2026 — V-211: exceção temporária de MFA do administrador

Por instrução explícita do proprietário, somente `suporte@mewstack.com.br` deixou de exigir MFA temporariamente. O vínculo TOTP inválido foi removido, não havia códigos de recuperação e o evento `accounts.mfa.temporarily_disabled` registrou a alteração. Senha, papel `admin`, demais contas e política global permaneceram inalterados.

O Playwright autenticou pelo formulário público e chegou diretamente ao Console em `/platform/`, sem tela de segundo fator. A aba de validação foi fechada. A reativação futura depende de novo pareamento e nova instrução do proprietário.

## 29/09/2026 — V-212: Console do escritório e convites

D-188 simplificou o detalhe do escritório em duas decisões principais e um bloco avançado recolhido. O convite deixou de pressupor proprietário e passou a oferecer proprietário, administrador, gestor, operador, financeiro e auditor. O resumo de erro agora preserva a falha operacional e aponta campos inválidos; a transação continua impedindo convite sem entrega.

Produção foi consultada sem mutação: SMTP e remetente não estão configurados e não existe convite para o endereço observado. Localmente, 29 testes, Ruff, Django check e diff check passaram. Playwright local cobriu desktop, tablet e celular em claro, escuro e sistema, incluindo movimento reduzido, foco, Escape, erro de campo, overflow, nomes acessíveis e console; todas as instâncias foram encerradas. O conector MCP de navegador não disponibilizou browser. Não houve deploy nem envio externo.

## 29/09/2026 — V-213: correção do fluxo de login/MFA do administrador

A dispensa temporária de D-187 passou a valer em todo o Console. O gate duplicado de Configurações foi removido e as rotas diretas de cadastro, verificação e QR agora retornam ao Console ou 404 sem criar TOTP para a conta dispensada. O dispositivo não confirmado associado ao segredo exposto foi eliminado; a conta terminou com zero dispositivos e zero códigos de recuperação.

Foram aprovados 973 testes, 29 subtestes, Ruff, MyPy, Django check e migrations check. Snapshots de PostgreSQL e Valkey precederam a publicação. O backup contínuo da Fly foi revertido após pressão de I/O e a topologia voltou ao custo/tamanho anterior. A release 12 deixou web e worker saudáveis na mesma imagem; health de banco/cache e checks do PostgreSQL passaram. O código publicado confirmou Console e Configurações 200, cadastro MFA redirecionando para `/platform/` e QR 404. O browser Playwright não estava disponível, portanto não há alegação de inspeção visual nova em produção.

## 29/09/2026 — V-214: corretor removido do nome no convite

O campo de nome do modal de convite recebeu `spellcheck=false`, eliminando a marcação vermelha e o indicador do corretor sem alterar foco ou validação. Vinte e nove testes e Ruff passaram; o rolling deploy terminou com web e worker saudáveis. Playwright não estava disponível na sessão.

## 29/09/2026 — V-215: importação simples e em lote de certificados

D-192 substituiu o cadastro manual por uma única superfície de arraste/seleção para `.pfx` e `.p12`. O CNPJ é lido da extensão oficial ICP-Brasil e correlacionado exatamente a uma empresa acessível; o nome comum do certificado fornece o rótulo. O lote aceita senha comum ou convenções explícitas no nome do arquivo por regras locais e limitadas. Não há IA nem transmissão externa. Falha de abertura, duplicidade, ambiguidade, tamanho excessivo ou empresa ausente produz resultado não reconhecido sem persistir o arquivo ou expor nome e senha.

Cinco testes novos e 76 regressões do workspace passaram com Ruff, MyPy, Django check, migrations check e diff check. A execução integral teve 977 aprovados, 2 ignorados e 2 falhas alheias que passaram isoladamente. Playwright cobriu desktop e celular, claro/escuro, movimento reduzido, foco, Escape, lote misto, responsividade e console; abas e servidor local foram encerrados. A pesquisa externa supriu a ausência de resultado pertinente no Watermelon. Não houve deploy, certificado real ou ativação da coleta.

## 29/09/2026 — V-216: fila de certificados e senha por arquivo

D-193 removeu o teto funcional de 50 itens por meio de uma fila sequencial no navegador. Nomes no padrão usado pelo escritório (`Empresa - SENHA.pfx`) e o sufixo numérico separado por espaço são interpretados localmente. Quando a senha não abre o A1, somente o item corrente pausa e a tela oferece digitação, nova tentativa ou pular, preservando o restante do lote. O servidor continua sem devolver ou registrar nome bruto e senha.

A validação visual local percorreu o fluxo completo em celular com dois arquivos, duas pausas e resumo final, sem erro de console. A versão de assets foi incrementada para impedir cache do fluxo antigo. A homologação com A1 real continua condicionada ao certificado autorizado e não foi simulada como concluída.

Snapshots de PostgreSQL e Valkey foram agendados antes do deploy. A release 15 terminou com migration job, canário, web e worker aprovados. O health externo retornou 200 com banco/cache `ok`; o Celery reconectou ao Valkey e ficou `ready`. A regressão focada final somou 114 aprovados e 1 ignorado opcional, com Ruff, MyPy, Django check, migrations check, sintaxe Node e diff check aprovados.

## 29/09/2026 — V-217: central de certificados recuperável

D-195 reorganizou a central para mostrar primeiro as empresas sem A1 e depois todos os certificados cadastrados, com contagens separadas de cobertura, vencimento e pendências. O filtro inicial deixou de esconder certificados válidos. O modal nasce fechado e só abre por ação explícita; fechar, Escape ou “Cancelar fila” interrompem a requisição corrente. Nome e senha continuam somente no navegador. Respostas HTML/500 agora viram uma etapa curta de tentar novamente ou pular, sem erro técnico bruto e sem interromper os próximos arquivos.

O upload de A1 vigente prepara a sincronização da empresa e, quando o gate ADN estiver habilitado, agenda a primeira tarefa após o commit. Certificado vencido não habilita coleta; o dispatcher também exclui vencidos e revogados, mantendo cada empresa isolada. A mensagem de ativação informa que empresas inválidas foram ignoradas e que as válidas continuam normalmente. O gate real de D-189 permanece fechado até o piloto autorizado.
## 29/09/2026 — V-218: fila oficial sequencial e notas classificadas na lista

D-201 a D-203 foram publicados na release 21. A coleta processa uma empresa por vez, persiste último e maior NSU por página, continua a mesma empresa enquanto houver páginas e só então libera a próxima. A Bianchi passou de 1.327 para 1.746 documentos observados; uma retomada pós-deploy concluiu 50 documentos com NSU 50/50, sem erro ou retry. Health de banco/cache e máquinas web/worker passaram.

A lista principal agora agrupa por empresa, usa apenas Todas/Classificadas/Não classificadas, abre por padrão a competência anterior e permite classificar e baixar o ZIP sem mudar de tela. A antiga área Revisões foi removida da navegação. Noventa e cinco testes focados e as verificações estáticas passaram; Playwright local cobriu desktop e celular e foi encerrado. A inspeção visual adicional em produção ficou indisponível por ausência de browser no MCP. O pacote permanece de conferência, não importação automática no Domínio, até resolver Q-39.

## 29/09/2026 — V-219: acumulador sem botão salvar e lote por filtro

D-204 foi implementada na central de NFS-e. O operador vê o número fiscal da nota, corrige o acumulador por um campo com catálogo e recebe feedback `Salvando…`/`Salvo` sem recarregar. Cada correção acrescenta artefato, histórico e auditoria, e a exportação resolve a ponta da cadeia imutável. A seleção aceita nota, empresa, página ou todos os classificados do filtro e informa a abrangência antes do download.

Ruff, sintaxe Node, Django check e migrations check passaram; a regressão focal fechou em 19 aprovados. Playwright MCP verificou desktop e celular, salvamento real `23` → `24`, seleção global, teclado, foco, movimento reduzido, ausência de overflow e console limpo; a aba e o servidor foram encerrados. A suíte integral teve 991 aprovados e duas falhas em asserções legadas que ainda exigem a tela de revisões retirada por D-202. Não houve deploy nem homologação do importador Domínio; Q-39 continua aberta.

## 30/09/2026 — V-220: Neon em produção, exportação ACU e detalhe de empresa

Os bancos principal e knowledge foram migrados ao Neon somente depois de contagem e hash de conteúdo idênticos. O Fly permaneceu com web, worker e Valkey; a release 27 concluiu e o Postgres Fly antigo foi mantido intacto para rollback. O pacote percorre o XML inteiro por nome local `ACU`, e a prova com XML real confirmou uma tag com o código vigente sem alterar o original. O smoke autenticado da Bianchi confirmou HTTP 200 nas telas centrais e corrigiu o 404 de empresas pausadas. A coleta chegou a 14.452 documentos, com sucesso registrado nas 56 sincronizações e retentativa do 404 legado. Q-39 continua sendo o limite para declarar importação Domínio homologada.

## 30/09/2026 — V-221: PostgreSQL Fly parado

Por D-208, a máquina do banco legado `cica-contabil-db` foi parada depois de reconfirmar os quatro URLs de banco no Neon. O site, o health, web, worker e consultas reais pelos dois aliases permaneceram saudáveis; o acervo continuou crescendo no Neon e chegou a 14.552 NFS-e. A máquina e seu volume foram preservados para rollback e não foram destruídos.

## 30/09/2026 — V-223: reauditoria de facilidade de uso

V-227: links Empresas → NFS-e agora usam ID autorizado, com contexto explícito, persistência entre filtros/atalhos e download limitado à empresa. Três testes e sete subtestes passaram; Playwright desktop/celular percorreu teclado, seleção e saída para carteira. Ruff/MyPy/JS aprovados. Browser e servidor encerrados; sem publicação.

V-226: Empresas passou pela nova revisão com pesquisa prévia. Corrigidos busca de CNPJ sem pontuação, contador filtrado, identificação de pausada e nomes dos filtros de certificados. A validação de cadastro já recusava CNPJ inválido; agora o modal mantém erro visível e foco correto. Vinte e dois testes e dois subtestes passaram, além de Ruff/MyPy/diff check e Playwright desktop/celular. Browser e servidor encerrados; sem publicação.

V-225 acrescentou histórico de downloads com nomes claros, identificação técnica recolhida e caminho direto para novo pacote. A falha de abertura do arquivo passa a ser tratada antes de marcar download. Browser desktop/celular validado e encerrado; checks estáticos passaram. Regressão integral iniciada para a barreira de publicação; produção segue na versão 31.

Resultado final V-225: 1.002 testes e 36 subtestes aprovados, três skips conhecidos; corrigidos o título legado no teste e a emissão fictícia do proprietário demo por sessão. MyPy passou em 221 arquivos após explicitar duas variáveis de texto no validador do runner, cujos seis testes também passaram. Ruff src/runtime/tests aprovado. Publicação continua pendente.

Continuação V-224: validado o lote de 165 notas em duas páginas no tenant sintético comum; corrigidos estado parcial da seleção, rótulo da ação por página e recusa de filtros/seleções inválidos. Regressão final: 23 testes e sete subtestes aprovados, além de Ruff, MyPy e sintaxe JS. Navegador e servidores QA encerrados. Sem deploy.

D-211 e o goal ativo exigem reauditoria inclusive de telas anteriores, com pesquisa prévia por tela. NFS-e recebeu acesso explícito ao lote, instrução contextual, nomenclatura clara, aba ativa única e seleção coerente. Corrigida a pasta mensal do ZIP na virada UTC/local. V-223 registra referências, 29 testes aprovados, verificações estáticas e Playwright desktop/celular com downloads fictícios. Implementação local; publicação e revisão das demais jornadas continuam abertas.

## 30/09/2026 — V-222: Neon suspende sem interromper trabalho

Continuação 01/10/2026, V-231: preparado serviço PostgreSQL com digest validado e suíte integral antes dos builds no CI existente. Sete testes de segurança da configuração passaram; YAML/ordem/porta/ausência de continue-on-error verificados localmente. Nenhuma execução GitHub ou publicação foi acionada; enforcement remoto permanece pendente.

Continuação 01/10/2026, V-230: regressão PostgreSQL local expôs locks inválidos nas projeções de Guias, DCTFWeb e Parcelamentos e falhas do harness (fechamento direto de streaming/data variável). Correções realizadas conforme D-154; repetição integral aprovou 1.012 testes/39 subtestes, com somente um skip opcional de browser. Migração 0067 validada com 1.001 notas históricas e reversão. Sem produção ou fornecedor acionado.

V-230 encerrada: três testes adicionais de projeção com quatro conexões simultâneas passaram. Contêiner exclusivo encerrado/removido automaticamente e ausência confirmada; somente dados sintéticos descartados. Pendências externas e publicação continuam abertas.

Continuação local V-229/D-212: corrigida exposição de metadados de pacotes fora da carteira na lista de downloads. Novo vínculo pacote/notas permite autorização integral no SQL antes de paginar. Migração/backfill local e testes de autorização passaram; Playwright confirmou lista restrita, download e vazio após mudança de carteira em desktop/celular. Publicação e validação PostgreSQL continuam pendentes, com gate de troca dos escritores documentado em VALIDACOES.md.

Regressão V-229 encerrada: 1.009 testes/39 subtestes aprovados, três skips explícitos; Ruff global e MyPy em 221 arquivos passaram. Nenhuma publicação foi realizada.

Continuação local V-228: histórico NFS-e de empresa pausada passou a respeitar o mesmo acesso do cadastro, sem entrar na carteira ativa nem reativar coleta. Mensagem de pausa, retorno ao cadastro, edição oculta e limpeza de filtros com empresa preservada. 61 testes/nove subtestes passaram e o teste específico passou novamente após o ajuste final; Playwright desktop/mobile baixou 83 documentos e recuperou o ZIP pelo histórico. Limites e referências em VALIDACOES.md. QA encerrado; sem publicação.

D-210 separou liveness de readiness no Fly, alinhou em 15 minutos somente as varreduras de recuperação e retirou da agenda integrações desativadas. Enfileiramento normal, coleta NFS-e, leases, checkpoints e retentativas permanecem imediatos. O endpoint Neon mantém 0,25–1 CU e agora suspende após cinco minutos ociosos.

As releases 30 e 31 publicaram a mudança diretamente pelo Fly. Um erro de autenticação do builder e um panic posterior do `flyctl` foram observados na segunda publicação; a imagem já havia sido aplicada, e o worker principal foi iniciado e validado explicitamente. Estado final verificado: web e worker versão 31, liveness e readiness 200, banco/cache `ok`, Celery `pong`, dois aliases PostgreSQL acessíveis e 59 sincronizações NFS-e preservadas. A primeira hora tranquila medida consumiu 387 CU-segundos contra aproximadamente 900 antes da otimização.

## 01/10/2026 — V-232: reauditoria das simulações Integra

Parcelamentos/lote DCTFWeb isolados por sessão também para membro demo autorizado. Corrigido separador de milhar no identificador do formulário, encontrado pelo clique real; teste extrai valor renderizado. 64 testes focados e quatro repetidos após ajuste passaram; Ruff/MyPy aprovados. Desktop/mobile e teclado nos limites de V-232. Navegador encerrado; sem publicação. Consulta individual e descoberta do lote permanecem pendentes.

## 01/10/2026 — V-233: consulta individual encontrável e isolada

Consulta DCTFWeb demo não aciona mais serviço persistente; conclusão fica por sessão e o texto distingue simulação de documento oficial. Atalho por guia torna a consulta acessível na carteira. Cinquenta testes passaram; Ruff/MyPy aprovados. Playwright percorreu o caminho da carteira ao resultado em desktop/mobile e teclado, e a recuperação de competência inválida. Auditoria de guidelines concluída nos templates; referências/limites em V-233. Browser e QA encerrados, sem publicação. Lote e estados reais continuam pendentes.

## 01/10/2026 — V-234: lote descoberto antes da seleção

Ação de revisão de lote visível, instrução página/limite, seleção ausente para consulta somente; centavos sem localização, UUID canonicalizado e competência inválida recusada. Playwright percorreu carteira QA extensa, seleção e prévia bloqueada sem contrato em desktop/mobile. Sobreposição mobile encontrada e corrigida. 110 testes/11 subtestes, Ruff/MyPy/JS aprovados. Browser/QA encerrados; sem publicação nem Serpro. Evidências e limites em V-234.

## 01/10/2026 — V-235: acompanhamento e estados DCTFWeb

Fixture local dos cinco estados criada; atualização de resultado via GET e identificação de registro incerto adicionadas, sem repetição de consulta. Dez combinações estado/largura percorridas, PDF sintético baixado e fila escura conferida. Regressão completa: 1.025 aprovados/43 subtestes, seis skips explícitos; depois 23 DCTFWeb/quatro subtestes passaram com o ajuste final. Ruff/MyPy aprovados; QA/browser encerrados. Limites em V-235; sem publicação nem fornecedor.

## 01/10/2026 — V-245: recuperação do seletor de aparência

Logs de produção confirmaram token CSRF incorreto, não domínio/origem. O seletor passa a
renovar o token antes do POST sem relaxar a proteção, e rejeições HTML recebem página CICA
com retorno seguro; APIs continuam JSON. Playwright reproduziu um campo deliberadamente velho,
confirmou refresh 200 → POST 302 → tema aplicado e inspecionou o fallback 403 responsivo.
Dezoito testes passaram; JS, Ruff, MyPy e diff check foram aprovados. Release Fly 34 publicada;
o mesmo cenário passou em `cicacontabil.com.br`, web/worker/check saudáveis e liveness/readiness
200 com banco/cache `ok`. Pesquisa, auditoria e limites estão em V-245.

## 01/10/2026 — V-244: filtro mensal dos fechamentos

O filtro criticado na Visão geral foi recomposto como campo vertical com contorno completo e
ação curta: compacto no desktop, largura integral no celular, erro junto ao mês e feedback após
submit. Playwright validou claro/escuro, 1440 e 375 px, teclado, foco, competência inválida,
URL/resultado e console sem erros. 38 testes/12 subtestes passaram; o teste específico passou
novamente após a asserção final. Auditoria e limites em V-244; sem publicação.

## 01/10/2026 — V-243: descoberta e busca na Conciliação

A central passou a apresentar importar → processar → revisar → exportar e mantém a importação
visível. Quatro seletores de empresa ganharam combobox pesquisável por nome/código, confirmação
explícita, contagem/limite, teclado e fallback nativo. A auditoria atual manteve o submit
acionável e focou o arquivo ausente. Playwright percorreu desktop/mobile, claro/escuro,
movimento reduzido, URL, erros e modo sem JavaScript com 240 empresas; correções de `Esc`,
seleção implícita e validação foram rechecadas. 51 testes/24 subtestes, JS, Ruff, MyPy e diff
check aprovados. Browser/QA encerrados; sem upload real, Q-39, carga, publicação ou homologação.
Fontes e limites em V-243.

## 01/10/2026 — V-242: seleção segura na configuração da Conciliação

Empresa explícita inválida, fora da carteira ou ambígua não cai mais na primeira empresa;
POST exige empresa no corpo e ações/UUIDs inválidos são recusados antes de qualquer mutação.
Erros ganharam resumo navegável, associação ao campo, conteúdo preservado e recuperação pelo
próprio seletor. Playwright validou desktop/mobile, tema escuro, movimento reduzido, teclado,
foco, erro e fallback sem JavaScript com carteira sintética de 240 empresas; o overflow mobile
encontrado foi corrigido. 96 testes/96 subtestes e repetição final de quatro testes/24 subtestes
passaram; Ruff, MyPy e diff check aprovados. Fontes, auditoria e limites em V-242; sem publicação
ou homologação externa. Regressão SQLite completa: 1.039 testes/139 subtestes aprovados,
seis skips explícitos, em 108,81 s; provas PostgreSQL não foram repetidas.

## 01/10/2026 — V-241: limite das rotas avançadas da demo

D-211 registrado antes do guard. Doze rotas avançadas de Conciliação demo recusadas antes do acesso operacional; central fictícia preservada, recusa com retorno contextual. 94 testes e 72 subtestes aprovados; Ruff/MyPy/diff check aprovados. Playwright desktop/mobile/landscape validou recusa, teclado, foco, temas e retorno; configuração não-demo continua 200. Console somente com os HTTP 403 esperados. QA/browser encerrados. Regressão integral e limites detalhados em V-241; sem publicação/homologação.

Regressão completa SQLite final: 1.037 testes e 115 subtestes aprovados, seis skips explícitos, 115,01 s. Não substitui prova de concorrência PostgreSQL.

## 01/10/2026 — V-240: comparação demo de Conciliação

Membro demo usa a mesma simulação privada que visitante; auditor bloqueado, upload recusado. Demo mostra diretamente a comparação, sem painéis compartilhados, e busca vazia orienta filtros. 91 testes focados e cinco repetidos após ajuste final aprovados; Ruff/MyPy/diff check aprovados. Navegador desktop/mobile verificou confirmação, cancelamento/foco, evidência, isolamento e preservação da navegação não-demo. QA/browser encerrados. V-240 detalha limites; endpoints avançados permanecem em revisão, sem publicação/homologação.

## 01/10/2026 — V-239: contador DTE por carteira e sessão

Resultado final da repetição SQLite: 1.031 testes e 43 subtestes aprovados, seis skips, 108,98 s; sem falha. PostgreSQL não repetido nesta rodada.

Central Integra alinhada à fila: escopo integral para lote real e progresso privado para qualquer entrada demo. Dados de sessão inválidos não produzem lote parcial. Cobertura de carteira, revogação e sessões ampliada; Playwright verificou contador 0→1→0 e isolamento 1/0 em dois contextos. Primeira regressão completa revelou fixture com total divergente; corrigida sem relaxar bloqueio, repetição registrada em V-239. Ruff/MyPy passaram; QA/browser encerrados. Sem publicação/fornecedor.

## 01/10/2026 — V-238: acesso direto ao preparo e revisão DTE

Preparação deixa de ficar recolhida, ganha atalho principal no topo e revisão tem atalho secundário. Links preservam filtros/seleção e funcionam sem JS; texto demo corrigido, seleção por teclado verificada, busca dependente de JS escondida no fallback. Fluxo local desktop/mobile, erro vazio, foco e modo escuro conferidos. 13 testes DTE aprovados após corrigir asserção ampla; limites do teste de busy state em V-238. Sem publicação/Serpro; browser/QA encerrados.

## 01/10/2026 — V-237: escopo integral da fila DTE

Lista, contador e POST de decisão agora exigem acesso atual a todos os itens da consulta pendente. Complemento registrado em D-212 antes da implementação. 12 testes DTE aprovados, Ruff e MyPy da view aprovados. Playwright desktop/mobile validou filtros, foco e estados vazios/bloqueados; carteira restrita coberta por integração, não por navegador. Sem layout novo, fornecedor ou publicação. Sessão e servidor QA encerrados; próximos itens e limites em V-237/etapa 08.

## 01/10/2026 — V-236: isolamento DTE e confirmação explícita

Membro demo usa sessão como visitante; removida abertura persistente compartilhada, preservados confirmação/permissões e bloqueio de paginação externa. Histórico vazio corrigido e centavos preservados nos formulários. 65 testes focados passaram; Playwright confirmou fluxo local e isolamento entre dois contextos da mesma conta. Ruff/MyPy aprovados. Navegador/QA encerrados; limites em V-236, sem publicação ou consulta fiscal real.

## 01/10/2026 — D-213 / V-246: popular a demo em produção

Confirmada a ausência de atividades no tenant demo publicado. Implementado populador transacional e repetível, com guarda is_demo, seis modelos, duas competências e três personas sem senha utilizável. Corrigida a agenda pessoal de visitantes/administradores demo; detalhes de consulta e recusa de POST preservam registros compartilhados. Full suite final: 1.046 aprovados, cinco skips PostgreSQL e 139 subtestes. Publicada imagem derivada da release 32 com somente seis arquivos; release 33 executou o seed sem falha. Inventário final: 84 atividades, 42 atribuições, 60 evidências, 168 eventos; replay criou zero. Playwright verificou telas reais desktop/mobile, teclado, foco, filtros, detalhe, evidência, vazio/erro e console; capturas inspecionadas. Web/worker/health saudáveis; browser e QA exclusivo encerrados. Nenhuma fonte externa, cobrança, mensagem, senha redefinida ou escrita em tenant operacional. Não conclui homologações pendentes; rotina de atualização mensal é manual pelo comando documentado.
## 01/10/2026 — D-215 / V-247: página inicial orientada à próxima ação

Visão geral recomposta após pesquisa: resumo contextual, próxima ação, escopos autoexplicativos,
quatro filtros acionáveis e agenda de dez cartões com prazo relativo/exato e exceções úteis.
Responsável não se repete na visão pessoal; fechamento fica recolhido com estado preservado na
URL. Playwright percorreu desktop/mobile, claro/escuro, teclado, foco, filtros, paginação, vazio
e erro; sem overflow ou console errors. Full suite final: 1.047 testes/139 subtestes, seis skips;
repetição focada pós-isolamento do CSS: 137/19. Ruff, MyPy, Django e migrações aprovados. Fontes,
auditoria e limites em V-247; sem mutação de tenant real ou homologação externa.

Publicada release Fly 37 por imagem mínima derivada da release 34, com somente quatro arquivos da
dashboard. Release command, web, worker e health passaram; readiness informou banco/cache `ok`.
Entrada demo real confirmou POST 302, `/app/` 200, CSS 200 e a nova hierarquia no HTML. Browser
indisponível na retomada impediu repetir a inspeção visual no domínio; a inspeção local anterior
permanece a evidência visual desta entrega.

## 01/10/2026 — D-216 / V-248: NFS-e em lote legível e pacote por empresa

Reauditoria funcional iniciada na produção: a ação em lote já estava encontrável e operacional,
mas o ZIP omitia o nome da empresa nos diretórios. O gerador demo e o pacote não-demo passaram a
usar caminho seguro `código - empresa`, também no manifesto/fotografia. A central NFS-e ganhou
tipografia mobile legível, inputs de 16 px e ações principais de 44 px, sem alterar regra fiscal.

Pesquisa prévia: UI/UX Pro Max; Watermelon sem resultado em duas buscas; padrões públicos de
Linear, Google Drive, Carbon e MUI; Web Interface Guidelines atuais lidas e arquivos finais
auditados. Playwright local e publicado cobriu desktop/mobile/paisagem, claro/escuro, teclado,
foco, filtros, vazio, loading, falha de rede, seleção e downloads emitidas/tomadas. Os ZIPs da
produção confirmaram pasta e manifesto com nome da empresa; console limpo e sem overflow.

147 testes/82 subtestes focados e regressão integral com 1.048 testes/139 subtestes passaram;
seis skips explícitos. Ruff, MyPy, Django e migrações passaram. Release Fly 38 publicada por
overlay de quatro arquivos sobre a release 37; web/worker/health, liveness e readiness saudáveis.
Q-39 e a homologação Domínio continuam abertos; nenhuma fonte fiscal ou tenant operacional foi
alterado. Browser Playwright e QA local encerrados.

## 01/10/2026 — D-217 / V-249: coleta NFS-e orientada à ação

Reauditoria da coleta com UI/UX Pro Max, Watermelon (sem correspondência em duas buscas), padrões
de GitHub Actions, Power Platform e AWS Step Functions e Web Interface Guidelines atuais. A tela
agora explicita simulação, situação, próximo passo e exceções; configuração fica recolhida. Ações
demo são privadas à sessão, repetição não despacha task real e empresa sem A1 válido não ativa.

Onze testes focados, Ruff, MyPy, Node, Django e migrações passaram. Playwright local validou
desktop/mobile, temas, movimento reduzido, teclado, foco, erro/recuperação e overflow. Release 43
publicada com build completa após rollback imediato da tentativa de manifesto incompleto; health,
readiness, dashboard, NFS-e, assets e endpoint da fila responderam 200. O browser automatizado não
estava disponível para repetir a inspeção visual publicada; a produção foi conferida por sessão
demo HTTP e conteúdo. Q-39, carteira real, carga e piloto continuam pendentes.

## 01/10/2026 — D-219 a D-222 / V-251 e V-252: senha e conferência NFS-e

O mínimo de senha foi alinhado a oito caracteres em cadastro, ativação e redefinição, com prova
de sete inválida e oito válida. Na NFS-e, a comparação autorizada com o HubCobalchini levou para
a lista os papéis prestador/tomador, entrada/saída, contraparte, competência, valores e retenções
explícitas. O download da demo virou uma ação única que separa Emitidas/Tomadas e usa apenas
`CÓDIGO-` por empresa.

Depois da correção direta do proprietário, o contrato errado `ACU` foi removido do adaptador: a
cópia derivada agora lê/escreve `infNFSe/valores/acum`, preserva namespace e bloqueia XML sem
`infNFSe`; o original não muda. A coleta normaliza `acum`, prioriza `dhProc` e só classifica o
movimento por coincidência inequívoca do CNPJ. O pacote continua privado e não homologado (Q-39).

Playwright local verificou NFS-e em desktop/mobile, escuro, redução de movimento, teclado, foco,
filtros, retenções, seleção e vazio, sem overflow/console. Regressão integral final: 1.066 testes,
139 subtestes, seis skips; Ruff, MyPy, Django, migrações e diff passaram. Browser e QA encerrados;
nenhum deploy, tenant real ou provedor foi alterado.

## 01/10/2026 — D-223 e D-224 / V-253 e V-254: histórico e retenções NFS-e

Acumuladores e Exportações foram reauditorados para descoberta e recuperação: busca no banco,
filtros, paginação, contexto de origem, escopo, período, responsável, estado e código do pacote.
Depois, a Central NFS-e recebeu relatórios PDF e XLSX do recorte atual com entrada/saída, detalhes
da nota e ISS, PIS, COFINS, CSLL, IRRF e INSS separados. O total ignora agregados inconsistentes
e soma apenas valores retidos explícitos; texto fiscal não pode virar fórmula no Excel.

UI/UX Pro Max, Watermelon (sem correspondência em duas buscas), documentação oficial da NFS-e,
HubCobalchini autorizado e Web Interface Guidelines atuais foram aplicados. Playwright validou
desktop/mobile, tema, movimento reduzido, foco, alvos e overflow. PDF foi renderizado página a
página; XLSX foi reaberto e conferido estruturalmente, pois artifact-tool/LibreOffice não estavam
disponíveis. Validação focada: 41 testes e sete subtestes; a regressão integral concluiu com 1.068
testes, 139 subtestes e seis skips, além de Ruff, MyPy, Django e migrações. Nenhuma fonte, tenant
real, publicação ou cobrança foi acionada; Q-39 e amostra real permanecem.

## 02/10/2026 — D-225 / V-255: histórico NFS-e de empresa pausada

A reauditoria confirmou o acesso histórico explícito para proprietário sem carteira restrita e a
recusa para operador com carteira definida. A tela ganhou contexto de consulta, manteve downloads e
relatórios e deixou de oferecer semanticamente classificação bloqueada. Também foi corrigida a
contagem contraditória de revisão aberta quando a nota já possuía acumulador. UI/UX Pro Max,
Watermelon, GitHub, Slack, Jira, QuickBooks e as Web Interface Guidelines atuais orientaram a
decisão. Playwright cobriu desktop/mobile, escuro, movimento reduzido, teclado, vazio, seleção,
download, overflow e console; browser/QA encerrados. Foram aprovados 27 testes e sete subtestes
focados e a regressão integral com 1.068 testes, 139 subtestes e seis skips; Ruff, MyPy, Django e
migrações também passaram. Sem fonte fiscal, tenant real ou deploy.

## 02/10/2026 — D-226 / V-256: recuperação global de erros

Foram registrados handlers CICA para 400, 403, 404 e 500 com status real, resposta neutra para não
enumerar recursos protegidos, ação de recuperação e JSON preservado em `/api/`. As respostas não
ficam em cache e bloqueiam sniffing. O 500 não consulta banco para escolher destino e possui um
fallback final sem template, reversão de URL ou reflexão da exceção.

UI/UX Pro Max, Watermelon (sete blocos encontrados no retry), GitHub Docs, MDN, Slack, Atlassian e
as Web Interface Guidelines atuais orientaram a composição. Playwright MCP validou desktop/mobile,
claro/escuro, movimento reduzido, teclado, foco de 3 px, alvos de 49 px, ausência de overflow,
assets 200 e retorno ao início 200. Somente o status esperado do documento de erro apareceu no
console; sem falha de JavaScript/asset. Browser, servidor e scripts temporários foram encerrados.

Sete testes focados passaram em 32,01 s. A regressão integral aprovou 1.075 testes e 139 subtestes,
com seis skips explícitos, em 149,97 s. Ruff, MyPy, Django check e migrações passaram. Nenhum dado
real, tenant, publicação, serviço externo ou cobrança foi acionado.

## 02/10/2026 — D-227 / V-257: Conciliação por exceção recuperável

A reauditoria não-demo encontrou duas promessas incorretas: falhas de importação podiam ficar atrás
das métricas sem próximo passo e um layout salvo para arquivo já concluído afirmava processamento
iniciado. A próxima ação agora prioriza mapeamento, conta, OCR ou falha; cada linha mostra orientação
segura e ação específica, sem renderizar a exceção bruta. Reaplicação de regras só aparece quando
existem movimentos e o resultado do salvamento do layout informa se algo realmente entrou na fila.

UI/UX Pro Max, Xero, QuickBooks, BlackLine e SaaSFrame orientaram a sequência e a recuperação;
Watermelon não encontrou bloco em duas buscas. A inspeção Playwright revelou campos de 40 px, links
de erro de 32 px e a tabela ilegível em 390 px. O estado final usa alvos de 44 px, cartões rotulados,
foco de 3 px, largura 356 px, zero overflow, erro focado com escolhas preservadas e nenhum segredo ou
erro de console. Browser e servidor QA foram encerrados. As Web Interface Guidelines atuais foram
reaplicadas sem achado material final.

64 testes e 24 subtestes focados passaram em 37,05 s; a regressão integral aprovou 1.077 testes e
139 subtestes, com seis skips explícitos, em 146,27 s. Ruff, MyPy, Django check, Node, migrações e
diff-check passaram. Nenhum arquivo bancário, tenant, integração, publicação ou cobrança real foi
acionado; revisão/exportação completa e destino Domínio real continuam dependentes de Q-39.

## 02/10/2026 — D-228 / V-258: revisão individual e entrega verificável

A revisão individual da Conciliação passou a mostrar um próximo passo derivado do estado, preservar a
data no campo nativo, focar erros e impedir geração de lançamento antes de os dados estarem completos.
Ações secundárias foram recolhidas. No histórico de exportações, downloads e confirmações revalidam o
SHA-256; confirmação exige aceite explícito, hash, permissão e gate Q-39, registra ator/instante, é
idempotente e não impede baixar o arquivo depois. Conteúdo adulterado não avança o estado.

UI/UX Pro Max, QuickBooks, Xero e Ramp orientaram a separação entre revisão, decisão e sincronização;
Watermelon não encontrou resultado em duas buscas. A auditoria atual das Web Interface Guidelines
levou ao bloqueio de envio duplicado. Playwright MCP percorreu desktop e 390 px, tema escuro, movimento
reduzido, teclado, foco, erro e confirmação sintética; corrigiu data vazia, ação precoce, hash quebrado,
painel esticado e alvo de 39 px. Estado final sem overflow ou aviso/erro no console. Browser e QA foram
encerrados ao fim da rodada.

60 testes e 24 subtestes focados passaram em 33,36 s; a regressão integral aprovou 1.080 testes e 145
subtestes, com seis skips explícitos, em 132,86 s. Ruff, MyPy, Django check, Node, migrações e auditoria
de interface passaram. Nenhum dado real, integração, publicação ou cobrança foi acionado; Q-39 segue
bloqueando o destino Domínio real.

## 03/10/2026 — D-229 / V-259: configuração contábil sem falso requisito

A configuração da Conciliação dizia “pronto” com zero contas e apresentava período/automação como
pré-requisitos. O serviço, porém, exige conta contábil para partidas, usa conta financeira quando um
extrato precisa identificar a origem e somente bloqueia datas cobertas por período explicitamente
fechado. A interface agora declara essas diferenças, oferece uma próxima ação e mantém opcionais como
opcionais.

Os cinco formulários simultâneos viraram painéis sob demanda; só o essencial faltante abre no início.
Deep-link, aviso de edição não salva, resumo de erro focado, valores preservados, loading e retorno à
seção foram verificados. As seis listas têm paginação de 25 registros e cartões em 390 px. Período
exige motivo dentro de confirmação progressiva. Auditor autorizado consulta sem controles e não
consegue executar POST.

UI/UX Pro Max, QuickBooks, Xero e SAP orientaram preparação, plano de contas e proteção de períodos;
Watermelon não encontrou resultado em duas buscas. A fonte atual das Web Interface Guidelines foi
aplicada. Playwright MCP validou desktop/mobile, escuro, movimento reduzido, teclado, foco de 3 px,
alvos de 44 px, deep-link, erro, prevenção de saída, ausência de overflow e console limpo. Browser e
servidor QA foram encerrados ao final.

62 testes e 24 subtestes focados passaram em 36,75 s; a regressão integral aprovou 1.082 testes e 145
subtestes, com seis skips explícitos, em 136,66 s. Ruff, MyPy, Django check, Node e migrações passaram.
Nenhum dado real, integração, publicação ou cobrança foi acionado; Q-39 permanece aberta.

## 03/10/2026 — D-230 / V-260: auditoria legível e segura da Conciliação

A trilha deixou de usar código técnico e UUID como hierarquia principal. Cada evento agora explica a
atividade, categoria, responsável, instante, registro afetado e resultado; apenas metadados de uma
lista segura ganham rótulo de negócio. Código e referências permanecem disponíveis sob detalhe
técnico, sem JSON bruto, hash de IP, request id, hash de arquivo ou payload financeiro.

Busca, atividade, sucesso/falha e intervalo são combináveis e ficam na URL. Filtro inválido retorna
zero com próximo passo, datas usam limites indexáveis e a página contém 50 eventos. O resumo distingue
histórico, resultado atual e falhas. Permissões e escopo de escritório não mudaram.

UI/UX Pro Max e as referências GitHub, Microsoft Purview, Cloudflare, Atlassian e GitLab orientaram
hierarquia e filtros; Watermelon não encontrou resultado em duas buscas. A fonte atual das Web
Interface Guidelines foi reaplicada. Playwright MCP validou desktop e 390 px, escuro, movimento
reduzido, teclado, foco, erro, detalhe, filtros, 44 px, overflow e console; a sobreposição do alerta
mobile encontrada na primeira rodada foi corrigida. Browser e servidor QA foram encerrados ao final.

63 testes e 24 subtestes focados passaram em 35,11 s; a regressão integral aprovou 1.083 testes e 145
subtestes, com seis skips explícitos, em 137,47 s. Ruff, MyPy, Django check, migrações e diff-check
passaram. Nenhum dado real, integração, publicação ou cobrança foi acionado; Q-39 permanece aberta.

## 03/10/2026 — V-261: importação e prévia operacional da folha

Aplicada D-231 no setup: fluxo em três passos, ajuda contextual, pré-validação sem escrita, diagnóstico por linha, confirmação bloqueada com pendências, duplicata concluída direcionada ao histórico e isolamento dos formulários por ação. O histórico foi adaptado para cartão no celular.

Dez testes focados passaram em 24,41 s. A regressão integral aprovou 568 testes em 8,77 s, com um skip explícito, em quatro processos e bancos SQLite isolados. Ruff, MyPy (221 arquivos), Django check, migrações e diff-check passaram. Playwright validou desktop e mobile escuro, movimento reduzido, teclado/foco, erro/vazio, 44 px, overflow e console. Nenhum sistema externo foi acionado; homologação CSV/XLSX real continua aberta.

## 03/10/2026 — D-232 / V-262: conferência da folha por competência

A ficha da empresa passou a exibir pessoas, bruto, descontos, encargos e líquido de cada fonte e a abrir a conferência pelo mês. Os seletores ficam limitados à competência, duas fontes são pré-selecionadas sem execução automática e existe uma única ação por mês comparável. O resultado explica quanto a fonte conferida ficou a mais ou a menos, separa totais ausentes e aponta a atividade como próximo passo sem mudar seu estado.

UI/UX Pro Max orientou período, reflow e recuperação contextual; Watermelon não encontrou composição em duas buscas. Materiais públicos de QuickBooks, Rippling, Gusto e ADP foram usados como referência de relatórios agregados, e as Web Interface Guidelines atuais foram reaplicadas. Playwright validou 1440 × 900 e 390 × 844, claro/escuro, movimento reduzido, descoberta, comparação, erro focado, ajuda associada, 44 px, overflow e console. Foram corrigidos corte horizontal mobile, coluna redundante, ação duplicada e foco tardio. Browser e servidor QA foram encerrados ao final.

Dezesseis testes focados passaram em 54,09 s. A regressão integral aprovou 568 testes em 8,338 s, com um skip explícito, em quatro processos e bancos SQLite isolados. Ruff, MyPy dos módulos alterados, Django check, migrações, sintaxe JavaScript e diff-check passaram. Nenhum dado real, integração, publicação ou cobrança foi acionado; a homologação com duas fontes reais autorizadas permanece aberta.

## 03/10/2026 — D-233 / V-263: Caixa Postal DTE orientada à leitura segura

A Caixa Postal passou a funcionar como uma caixa de trabalho: assunto, empresa, origem, datas e situação formam o contexto; cada mensagem tem uma única ação “Abrir resumo”. O histórico vira cartões no celular. O resumo local continua separado da abertura do teor, que exige confirmação própria por poder registrar ciência no ambiente real. Na demo, abertura e protocolo ficam isolados na sessão e não chamam o Serpro.

UI/UX Pro Max e as referências públicas da Receita Federal, DET, Microsoft 365 Message Center e Outlook orientaram ordem recente, lido/não lido, filtros e separação da ação sensível; Watermelon não encontrou composição em duas buscas. A fonte atual das Web Interface Guidelines foi reaplicada. Playwright MCP validou central e detalhe em 1440 × 900 e 390 × 844, claro/escuro, movimento reduzido, teclado, foco de 3 px, vazio, erro focado, preparo, simulação local, abertura fictícia, alvos de 44 px, ausência de overflow e console limpo.

Treze testes focados passaram em 54,79 s; a regressão integral aprovou 568 testes em 8,394 s, com um skip explícito, em quatro processos e bancos SQLite isolados. Ruff, Django check, sintaxe JavaScript, migrações e diff-check passaram. Nenhum dado real, consulta Serpro, publicação ou cobrança foi acionado; credenciais, contrato e piloto DTE autorizado continuam dependências externas.

## 03/10/2026 — D-234 / V-264: Radar como fila de triagem fiscal

A tabela do Radar escondia as ações em 390 px dentro de 650 px roláveis. Ela foi substituída por uma fila recente em cartões: fonte, tema, data, resumo e limite fiscal ficam juntos; “Analisar impacto” e “Abrir fonte oficial” permanecem visíveis. A saúde das fontes foi compactada e abre na falha. Vazio, filtros e paginação oferecem recuperação e URL canônica.

O detalhe separa leitura de decisão. O filtro local encontrou 1 e 0 resultados dentro de 240 empresas sem remover o `select` nativo. Erro de servidor focou o resumo, loading desabilitou o botão com texto de andamento, retorno preservou filtros e o filtro local não disparou alerta falso de edição. Owner criou/retomou uma atividade; Auditor recebeu “Ver análises”, não formulário, e continuou sem POST.

UI/UX Pro Max, Feedly, PolicyNote, Thomson Reuters Checkpoint Edge, Lexis+ e Google Alerts orientaram fila, filtros e triagem; Watermelon não encontrou composição em duas buscas. As Web Interface Guidelines atuais foram reaplicadas. Playwright MCP validou desktop/mobile, temas, movimento reduzido, teclado/foco, vazio, falha, loading, permissão, 44 px, ausência de overflow e console limpo.

Doze testes focados passaram em 53,55 s. A regressão integral aprovou 568 testes em 8,714 s, com um skip explícito, em quatro processos e bancos SQLite isolados. Ruff, Django check, JavaScript, migrações e diff-check passaram. Nenhuma fonte externa, publicação ou cobrança foi acionada; completude da coleta e aplicabilidade fiscal real permanecem dependências externas.

## 03/10/2026 — D-235 / V-265: fechamento dos relatórios de retenções NFS-e

O relatório foi revalidado contra o HubCobalchini e a documentação atual da NFS-e Nacional. A lista
expõe total e tributos retidos por nota; PDF e Excel `.xlsx` preservam filtros, movimento e seis
tributos separados. O detalhamento ganhou alvo de 44 px e texto maior, e o botão identifica `.xlsx`.

Playwright baixou os dois formatos, percorreu desktop/mobile, escuro, movimento reduzido, teclado,
foco, vazio, overflow e console. As três páginas do PDF foram renderizadas e inspecionadas; a
estrutura, fórmulas e tipos da planilha foram reabertos. Quarenta e um testes e sete subtestes focados
passaram em 55,92 s; a regressão integral aprovou 568 testes em 8,762 s, com um skip explícito. Ruff,
Django check, migrações e diff-check passaram. Browser e servidor QA foram encerrados. Sem publicação
ou dado real; amostra fiscal autorizada e retorno Domínio Q-39 permanecem dependências externas.

## 03/10/2026 — D-236 / V-266: Guias e DCTFWeb orientadas ao próximo passo

A carteira agora distingue apuração local, documentos DCTFWeb e guia oficial; o próximo passo vem
antes da carteira extensa e cada estado tem uma ação principal. Consulta individual e lote mostram
escopo, progresso e custo/bloqueio antes de qualquer autorização. Erros brutos e chaves de serviço
foram retirados da superfície, mantendo referência recolhida para suporte. Incerto não oferece retry.

UI/UX Pro Max, Manual DCTFWeb 2025, QuickBooks Tax Center e Stripe orientaram hierarquia, período,
lote e recuperação; Watermelon não encontrou composição em duas buscas. As Web Interface
Guidelines atuais foram reaplicadas. Playwright validou desktop/mobile/landscape, temas, movimento
reduzido, lote, filtros/vazio, modal/teclado/foco, falha/incerto, PDF demo, 44 px, overflow e console.

Vinte e seis testes focados passaram; a regressão integral aprovou **569 testes em 8,589 s, com um
skip explícito**. Ruff,
MyPy, Django check, migrações e diff-check passaram. Browser/QA encerrados. Sem Serpro, custo,
publicação ou dado real; contrato/credenciais, D-149/Q-40 e transições reais continuam abertas.
## 03/10/2026 — V-268: fechamento técnico das retenções NFS-e

Confirmada a entrega de retenções explícitas (ISS, PIS, COFINS, CSLL, IRRF e INSS), movimento de
entrada/saída e relatórios PDF/XLSX sob os filtros da Central NFS-e. A suíte focada aprovou 111
testes/7 subtestes e a regressão integral 1.087 testes/145 subtestes, com 6 skips documentados.
Ruff, MyPy, Django check, migrations e diff check passaram. O MCP visual estava indisponível;
nenhuma nova validação de navegador foi alegada e as evidências renderizadas de V-265 permanecem.
Sem deploy, amostra fiscal real ou chamada externa.
## 03/10/2026 — V-267: Parcelamentos úteis para o contador

A tela passou a seguir empresa → acordo → parcela → DAS, mantendo a carteira como escolha secundária. Consultas, emissões e lotes ganharam revisão de escopo/consumo; falhas e incertezas mostram orientação segura sem mensagem bruta; nova tentativa após estado incerto exige conferência humana no e-CAC. A demo emite PDF privado à sessão, marcado como fictício e sem validade fiscal. Playwright validou desktop, mobile escuro/reduced-motion, landscape, lote, busca vazia, modal, Tab/Escape, retorno de foco, download, overflow e console. Dezenove testes focados e verificações estáticas passaram; a regressão integral final aprovou 1.088 testes e 145 subtestes, com 5 skips PostgreSQL explícitos. Também foram eliminadas duas fontes de instabilidade da suíte: renderização do seletor de tema sem `request` e testes que presumiam resolução/ordenação temporal do Windows. Watermelon não encontrou composição pertinente; Receita, Stripe, QuickBooks e Xero orientaram a hierarquia e os estados. Sem Serpro, custo, dado real ou publicação.

## 03/10/2026 — D-268 / V-269: ficha de atividade orientada à decisão

A ficha agora responde primeiro onde, quando, com quem e qual é o próximo passo. Condições de
conclusão, responsável e evidências precedem estados técnicos; códigos ficam recolhidos e eventos
ganham rótulos humanos. Evidência, impedimento e conclusão são intenções separadas. Formulários
inválidos preservam dados e foco. A revisão de conclusão torna explícita a resolução de impedimento
quando as demais condições já foram atendidas. Auditor permaneceu estritamente consultivo.

UI/UX Pro Max e referências de Asana, Linear e ClickUp orientaram a hierarquia; Watermelon não
encontrou analogia em duas buscas. A fonte atual das Web Interface Guidelines foi reaplicada.
Playwright MCP percorreu desktop, mobile escuro e landscape, movimento reduzido, estados pendente,
vazio, pronto, impedido e inválido, permissões Owner/Auditor, teclado/modal/foco, histórico, overflow
e console. Setenta e sete testes e 12 subtestes focados passaram; Ruff, MyPy, Django, migrações,
JavaScript e diff-check passaram. Sem integração, dado real, custo ou publicação.
Regressão integral final: 1.090 testes e 145 subtestes aprovados; seis skips explícitos dependem do
Playwright Python opcional ou de locks reais no PostgreSQL.

## 03/10/2026 — D-271 / V-272: fechamentos por competência como fila contábil

O painel embutido na visão geral passou a informar atenção, comprovação, lacunas e empresas da página
antes dos detalhes. Exceções aparecem primeiro; cada empresa/área mostra progresso, próximo passo e
ação para a atividade. Concluídos ficam separados e ausência de requisitos permanece lacuna explícita.
Competência inválida não volta ao mês corrente: o recorte fica vazio e o erro recebe foco.

UI/UX Pro Max orientou feedback e cartões responsivos; Watermelon não encontrou analogia em duas
buscas. FloQast, Financial Cents e QuickBooks Books Review orientaram progresso, exceções e revisão por
período. A fonte atual das Web Interface Guidelines foi reaplicada. Playwright MCP validou desktop e
mobile escuro/reduced-motion, teclado, foco, detalhe, navegação, erro, overflow e console limpo; as
capturas finais estão em `artifacts/closing-v272-desktop-final.png` e
`artifacts/closing-v272-mobile-dark-final.png`. A regressão aprovou 1.095 testes e 145 subtestes, com
seis skips explícitos; Ruff, MyPy, Django, migrações e diff-check passaram. Browser e servidor foram
encerrados. Sem integração externa, dado real, custo ou publicação.

## 03/10/2026 — D-269 / V-270: central de atividades como fila de decisão

A central deixou de misturar trabalho atual e encerrado no recorte inicial. Prioridades aparecem
antes do refinamento; área, situação, fonte, empresa, competência e responsabilidade usam um único
formulário; filtros ativos são removíveis e a URL não conserva campos vazios. Parâmetro inválido,
escopo alheio ou prazo conflitante retorna zero registros, mensagem recuperável e foco.

Cada item mostra próximo passo, prazo relativo/exato, responsável e situação. No celular, a tabela
vira cartão sem esconder coluna; o conflito inicial com a largura mínima compartilhada foi detectado
visualmente e corrigido. UI/UX Pro Max confirmou reflow; Watermelon não encontrou analogia em duas
buscas. Linear, ClickUp, Asana e Microsoft Planner orientaram filtros, URL e dimensões de leitura.
As Web Interface Guidelines atuais foram reaplicadas sem achado material restante.

Playwright validou desktop, mobile escuro e landscape, movimento reduzido, filtros, chips, vazio,
erro focado, teclado, Owner/Auditor, URL limpa, retorno do navegador, 44 px, overflow e console.
Foram aprovados 135 testes/19 subtestes focados e 1.093 testes/145 subtestes integrais; seis skips
explícitos dependem do Playwright Python opcional ou de locks PostgreSQL. Ruff, MyPy, JavaScript,
Django, migrações e diff-check passaram. Sem dado real, fonte externa, custo ou publicação.

## 03/10/2026 — D-272 / V-273: cadastro de empresas como carteira de ação

A lista deixou de exigir leitura de cinco colunas técnicas para descobrir trabalho. Prioridades da
carteira aparecem antes da busca; filtros secundários ficam em refinamento e cada empresa mostra o
próximo passo com destino direto. Empresas pausadas não geram falso alerta. O filtro “sem código”
foi incluído e parâmetros inválidos agora retornam recorte vazio e erro focado, nunca a carteira
inteira. Cadastro duplicado preserva os campos e recebe resumo de erro no modal.

UI/UX Pro Max reforçou feedback, reflow e legibilidade. Watermelon não encontrou analogia em duas
buscas. Foram adaptados padrões de QuickBooks Accountant, TaxDome, Karbon e Financial Cents. As Web
Interface Guidelines atuais foram reaplicadas e corrigiram foco, alvos, tipografia e links de A1.
Playwright MCP percorreu desktop, mobile escuro/reduced-motion e landscape, prioridades, busca,
refinamento, vazio, erro, modal, Escape, 44 px, overflow e console final limpo. Capturas finais:
`artifacts/companies-v273-desktop-final.png` e
`artifacts/companies-v273-mobile-dark-final.png`.

Foram aprovados 24 testes e 2 subtestes focados e 1.097 testes/145 subtestes integrais; seis skips
explícitos dependem do Playwright Python opcional ou de locks PostgreSQL. Ruff, MyPy, Django,
migrações e diff-check passaram. Browser e servidor foram encerrados. Sem dado real, chamada
externa, custo ou publicação.

## 05/10/2026 — D-274 / V-274: reclassificação NFS-e pelo backup em produção

Os leiautes Krek confirmaram `infNFSe/valores/acum`. Foi criada rotina de prévia/aplicação com
fotografia pai/filho, streaming, evidência append-only, origem de resolução `backup`, proteção de
decisões humanas e auditoria. A ramificação Neon prévia permite restauração até 12/10.

A release Fly 45 aplicou a migração e permaneceu saudável. A prévia percorreu 29.042 notas; a
aplicação criou 16 artefatos, 39 revisões, atualizou 666 sugestões e resolveu 16 casos. 24.386 notas
ficaram em revisão por não possuírem correspondência única segura. Reexecução: zero mudanças. Os 16
XMLs derivados foram analisados com um único `acum` diretamente em `valores` e nenhum `ACU`. A
memória web foi elevada temporariamente para a operação e devolvida a 512 MB.

Regressão: 1.106 testes, 145 subtestes, seis skips explícitos; Ruff, MyPy, Django, migrações e
diff-check aprovados. Playwright desktop/mobile e a auditoria atual das Web Interface Guidelines
aprovaram a ficha tocada; browser e QA foram encerrados. Q-39 permanece aberta.
## 05/10/2026 — D-275 / V-275: auditoria integral e plano de conclusão

Solicitação: avaliar todo o CICA como produto, pesquisar sistemas similares online e criar plano.
Entregues diagnóstico funcional, matriz de telas/tarefas, pontos fortes, 14 achados principais,
referências de mercado, oportunidades fora do escopo atual, linguagem e roteiro de teste com usuários.
O plano mestre recebeu estado reconciliado das etapas 00–13, 31 pacotes, seis ondas, dependências,
responsáveis, aceites e próximo prompt. Sem implementação dos pacotes ou publicação.

Pesquisa pública e inspeção de código distinguiram trabalho faltante de homologação e de hipótese.
Playwright MCP percorreu 54 combinações em ambiente isolado atual, mais cenários sintéticos por
perfil. Detalhes, capturas, recusas esperadas e limites em V-275. Navegador e servidores abertos
nesta tarefa encerrados; alterações preexistentes preservadas. Documentação segue como memória
única, sem novo plano concorrente. Próximo passo recomendado: PC-01/02 e material de Q-39.
## 05/10/2026 — D-276 / V-276: revisão integral da classificação NFS-e (Bianchi & Rizzotto)

Solicitação: entender por que poucas notas eram classificadas e por que uma recebeu acumulador
indevido. Auditoria em produção mostrou 29.069 notas, 4.716 classificadas e 24.392 em revisão;
99,9% das notas foram normalizadas antes da chave de direção e guardavam como contraparte o
primeiro CNPJ do XML (a própria empresa em serviço prestado). As 49.199 observações do backup
são só por cliente/fornecedor, sem código de serviço e sem direção. Casos concretos: notas de
serviço prestado da empresa 57 classificadas como "COMPRA DE MERCADORIA A PRAZO".

Correções: direção e contraparte derivadas do XML imutável (`nfse_match_data`, com raiz do CNPJ
para filial); histórico do lado oposto não concorre; acumulador fora do catálogo ativo (ou do
cadastro manual) não é escolhido nem exportado; histórico unânime do fornecedor classifica e
conflito vai para revisão; código de serviço `cTribNac` comparado ao item LC 116; decisão humana
grava a chave completa (corrige `MultipleObjectsReturned`); XML exportado preserva bytes,
prefixos e declaração, inserindo só `infNFSe/valores/acum`; reclassificação pagina por pk
(PgBouncer sem cursor de servidor) e carrega uma empresa por vez, cabendo em 512 MB sem custo
adicional; agente e extrator passam a enviar a direção das observações (migração 0069).

Fontes: documentação Domínio "Como configurar importação NFS-e Padrão Nacional" (acumuladores
separados em Serviços e Entradas, por item de serviço e cliente/fornecedor) —
https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=10162 ; formato
`cTribNac` de seis dígitos (item, subitem, desdobro) — https://buscadorncm.com.br/nfse/ctribnac .

Publicado como releases Fly 47 e 48. Prévia em produção: 29.076 notas, 24.566 classificáveis,
19.909 artefatos novos, 20 trocas (empresa 57), nenhuma decisão humana alterada. Pendência: as
observações do backup continuam sem direção até nova extração do `.dom` (chave e usuário externo).
As três notas nº 453 do CICA estavam sem acumulador e trazem município IBGE 4305108; o "4012"
exibido pelo Domínio não vem do XML do CICA.

Aplicação em produção (run `c0390284`): 29.076 notas lidas, 19.909 artefatos novos, 19.910
revisões resolvidas pelo backup, 1.556 sugestões atualizadas, 23 revisões novas, nenhuma decisão
humana alterada. Estado final: 24.610 de 29.079 notas com acumulador e 4.510 revisões abertas
(antes: 4.716 e 24.392). Validação só leitura em 400 notas sorteadas: zero acumulador fora do
catálogo ativo, zero incoerência nome × direção, XML derivado com um único `acum` em
`infNFSe/valores` e idêntico ao original fora dele. Empresa 57 conferida (notas 864, 866, 870,
874 em "PRESTAÇÃO DE SERVIÇO A PRAZO OFICINA"). Health 200, sem erro nos logs, VMs inalteradas.
Regressão local: 1.131 testes; duas falhas preexistentes no trabalho não versionado (texto
"Código de serviço" no detalhe da revisão e download por auditor).

Releases 49–50: `acum` inserido logo após `infNFSe/valores/vLiq`; pacote separado em
`NFS-e/Emitidas|Tomadas|Tipo-a-confirmar/<código>-/<competência>/` e manifesto com movimento e
importador Domínio (Serviços/Entradas). Teste externo de importação da nota 453 (ADRIANO →
GGBPLAST) confirmou leitura sem erro; a nota é saída da empresa 109 (ADRIANO) e o CICA aplica o
acumulador 1, usado 60 vezes para esse cliente no histórico — o teste a importara como entrada.
Pacote real gerado em produção dentro de transação desfeita: pasta `Emitidas/109-`, manifesto
"Serviços", XML idêntico ao original fora do `acum`.

Release 51: filtros e contadores Entradas/Saídas não funcionavam porque liam
`normalized_data.direction`, ausente em 99,9% das notas (normalização antiga e imutável). Criado
`NfseDocumentSide` (migração 0070) com lado, contraparte e nome derivados do XML; a captura grava
o lado e `backfill_nfse_sides` preencheu as 29.088 notas da Bianchi & Rizzotto em produção.
Filtros, contadores, relatório de retenções e nome da contraparte leem o lado gravado. Resultado
em produção: 21.139 saídas, 7.450 entradas, 499 a confirmar; nota 453 como saída com tomador
GGBPLAST. Regressão local: 1.134 testes, mesmas duas falhas preexistentes.


## 22/09/2026 — Etapa 14 aberta e fase 1 do módulo Rentabilidade (V-281)

- O Lucrums (`Mewstacks/ProjetoARD`) deixa de ser sistema vizinho e entra como oitavo módulo, código `profitability`. Os dois repositórios foram sincronizados localmente e o corte de origem é `d9d4ebb`; o branch de instalador do lado do Lucrums já estava mergeado em `main`.
- A verificação que sustenta o resto: os dois backends são forks do mesmo boilerplate, com Django, Python, Celery e cryptography nas mesmas versões e com `OrganizationScopedModel`, `EncryptedTextField` e `blind_index` equivalentes. Logo a base do Lucrums é descartada e move-se só o produto. D-281 a D-285 registram isso e as quatro decisões de arquitetura; Q-41 a Q-45 ficam abertas.
- Fase 1 entregue: `contracts/` na raiz com os treze SHA-256 do manifesto conferidos, motor de cálculo e normalização portados sem alterar uma conta, onze modelos de domínio e métrica, casador de pessoas e `recompute_competencia` com custo, agrupamento por raiz de CNPJ e deduplicação entre ERPs.
- Por D-282 a carteira continua sendo `hub.ClientCompany` e a `Empresa` do Lucrums não veio: uma segunda entidade faria as telas de rentabilidade contornarem o filtro de `CompanyAccessGrant`, que é regressão de controle de acesso e não duplicação.
- 65 testes do módulo, 89% de cobertura no app, 863 na suíte inteira sem regressão. Ruff, mypy, `manage.py check` e `makemigrations --check` limpos.
- Nada de tela, ingestão ou conector ainda. A margem depende de Q-41, que segue aberta: o levantamento de origem não achou fonte de honorários em nenhum dos dois ERPs, então com dado real o módulo apura custo e horas, não rentabilidade.

## 22/09/2026 — Etapa 14, fase 3: ingestão do ERP para Rentabilidade (V-282)

- O catálogo de consultas fixado por SHA-256 veio do Lucrums e é o que o conector da CICA não tinha: contrato divergente não é despachado nem aplicado, e o hash da consulta fica gravado na execução para uma auditoria poder dizer qual SQL gerou um número.
- Por D-287 a cifra de envelope da origem não veio. O agente já se autentica por mTLS com assinatura do corpo e a CICA já cifra em repouso; um segundo sistema de chaves cobriria trecho já coberto. A página fica cifrada em repouso pelo campo da CICA, com soma conferida antes de aplicar.
- A ponte de D-282 virou comportamento: a linha do ERP acha a empresa que a carteira já tem antes de cadastrar outra, inclusive a gêmea do outro ERP pelo documento. Só o Domínio escreve `dominio_code`, e escritório que exige esse código recusa empresa só do Siescon em vez de furar a própria regra.
- Dois defeitos próprios corrigidos com teste: o perfil de ERP era um-para-um, então duas gêmeas não cabiam na mesma empresa; e o `distinct` das métricas não valia por causa da ordenação padrão do modelo.
- A autenticação do agente não foi reimplementada — as três funções do `agent_v2` ganharam nome público e são importadas, com teste provando que agente revogado também é recusado aqui.
- `PROFITABILITY_SYNC_ENABLED` nasce desligada: catálogo vazio e nenhuma execução aberta. Suíte: 916 aprovados, 3 ignorados; 86% de cobertura no app.
- Nada de tela ainda. Nenhum agente real, ODBC, ERP ou rede foi tocado.

## 22/09/2026 — Etapa 14: módulo Rentabilidade declarado e visível (V-283)

- Os quatro pontos de declaração estão feitos — código, migração, catálogo e o grupo "Gestão" na navegação —, mais o azulejo do painel com os clientes de margem negativa ou em atenção. A visão geral mostra totais da competência e a carteira da menor margem para a maior.
- A tela lê a carteira filtrada por `CompanyAccessGrant`, não a do escritório: é o fecho de D-282 do lado da interface, com teste provando que a margem por cliente não escapa do filtro nem atravessa inquilinos.
- Falta de dado não vira margem: cliente sem hora aparece como "Sem horas no mês" e as situações de ausência usam borda tracejada em vez da cor das faixas. Q-42 continua necessária para o limiar de cobertura da carteira inteira.
- Por D-288 o módulo fica fora dos módulos padrão do cadastro enquanto Q-41 e Q-43 estiverem abertas: ligá-lo no teste gratuito daria a todo escritório novo uma tela sem como responder o que promete.
- Nenhuma dependência de front foi introduzida — sem build, Tailwind, HTMX, CDN ou script inline. Suíte: 928 aprovados, 3 ignorados.

## 22/09/2026 — Etapa 14, fase 2: telas do módulo Rentabilidade (V-284)

- Colaboradores com os vínculos do ERP, ficha da pessoa com a composição do custo anual, horas, análises por recorte, configuração do cálculo e a seção de rentabilidade dentro da ficha de empresa que o hub já tinha. A lista de clientes e a tela de conectores não foram portadas: a CICA já as tem.
- A ficha do colaborador exibe os mesmos valores do vetor do contrato — R$ 64.690,00 de custo anual, R$ 37,09 por hora —, agora conferidos pela interface e não só pelo serviço.
- Por D-286 o gráfico é SVG desenhado por script próprio servido de `static/`, sem biblioteca externa, build, CDN ou script inline. A mesma série sai como tabela ao lado, que é o que leitor de tela percorre, e por isso o SVG é `aria-hidden`.
- Falta de dado não vira número em nenhuma tela: sem horas, custo, resultado, margem e honorário sugerido saem como travessão com a explicação ao lado; sem salário vigente o custo do colaborador também é travessão, e não zero.
- Gravar um parâmetro de custo reprojeta todas as competências na hora, senão esta tela e a ficha do cliente passariam a se contradizer até a importação seguinte.
- D-288 foi ampliada: o módulo ficou fora também da demonstração, não só do cadastro, porque uma demonstração que o abre já o está anunciando. A lista passou a viver em um lugar só.
- Suíte: 955 aprovados, 3 ignorados. Inspeção visual em navegador, responsividade e leitor de tela seguem pendentes e pertencem à etapa 11.

## 22/09/2026 — Etapa 14, fase 4: conector Windows unificado (V-285)

- Antes de qualquer porte, um achado: o agente Windows **não compilava**. `AgentClient` passava um `Uri` para um parâmetro `string` desde `0ac1038`, e nenhum fluxo de integração contínua construía esse projeto. Corrigido, e os quatro projetos do agente entraram no CI — que é o que teria apanhado isso.
- O catálogo de consultas fixado por SHA-256 veio do conector do Lucrums e é o que a CICA não tinha: o SQL vivia solto no código-fonte. Agora a nuvem manda o código e o hash, o SQL sai do catálogo incorporado, e divergência derruba o serviço na subida em vez de falhar calado de madrugada.
- Por D-289 tudo permanece em .NET 8; por D-80 o pacote continua único, com o ERP vindo da configuração em vez de compilado no binário.
- A ponte ODBC de 32 bits entrou, autorizada por D-290: o Pervasive do Siescon não tem driver de 64 bits. Fala por stdin/stdout, sem rede, e a credencial nunca vai pela linha de comando. A conversão de valores subiu para a biblioteca de contratos, porque na origem havia uma cópia de cada lado da ponte.
- Q-33, Q-44 e Q-45 foram resolvidas por D-289 e D-290, e a etapa 04 deixou de estar bloqueada por falta de contrato técnico.
- 17 testes do agente, 955 na suíte Python. Nada foi executado contra Windows, ODBC ou ERP real.

## 22/09/2026 — Etapa 14, fase 5: documentação e material Siescon

- O material Siescon do Lucrums entrou em `docs/siescon/`, porque D-290 o tornou a base técnica do adaptador. O limite viaja junto e está no índice da pasta: o layout foi inferido, não documentado pelo fornecedor.
- O README dos contratos contradizia o próprio manifesto — dizia que três contratos Siescon nasciam não validados, quando três dos quatro estão validados — e descrevia o ERP compilado no binário, que é do projeto de origem e não vale aqui por D-80. Os dois trechos foram corrigidos.
- O README do agente ganhou as seções de contratos, ponte de 32 bits e atualização.
- D-291 registra que o atualizador automático do conector de origem não é absorvido: V-022 diz que o agente da CICA não baixa nem instala MSI sozinho, e reverter isso num porte seria decidir pelo responsável.
- Não foram copiados do projeto de origem: a SPA React, os apps de base do backend (conta, organização, auditoria, privacidade, comuns), o segredo local, o banco de desenvolvimento, o ambiente virtual de PDF e a pasta `tmp/pdfs`.

## 22/09/2026 — Etapa 14, continuidade da fase 2: ficha analítica do cliente (V-286)

- A carteira e a ficha transversal da empresa agora levam a uma análise própria do módulo, sem criar outra entidade de empresa: evolução, conciliação diária de horas automáticas × F9, atividades, equipe, unidades do grupo, referências e histórico ficam na mesma rota por competência.
- A ficha preserva a semântica dos dados ausentes: sem horas não há custo, margem nem honorário sugerido; custo parcial continua identificado. O gráfico próprio de D-286 foi reutilizado e a série também sai como tabela auditável.
- `CompanyAccessGrant` passou a recortar não só a empresa aberta, mas também horas, atividades, unidades e médias de comparação. O custo individual por pessoa continua reservado a dono e administrador.
- O plano da etapa foi consolidado em sete fases, do congelamento da origem à liberação, marcando o que já está concluído, o que depende das etapas 11 e 12 e o que Q-41 a Q-43 ainda bloqueiam. A documentação deixou de chamar o autoatualizador de pendência, em conformidade com D-291.
- Provas locais: 37 testes de tela do módulo; suíte integral com 967 aprovados, 3 ignorados e 11 subtestes aprovados; `ruff`, `mypy`, checks do Django, ausência de migração pendente e `git diff --check` limpos. Não houve navegador, Windows, ODBC, ERP, rede externa, cobrança ou dado real.

## 22/09/2026 — Etapa 14, continuidade da fase 4: configurador e MSI único (V-287)

- A revisão encontrou uma integração pela metade: a ponte Pervasive x86 já entrava no diretório do serviço, mas o configurador só conseguia gravar Domínio. Ele agora seleciona Domínio Web, Domínio Local ou Siescon, filtra a arquitetura correta do registro e testa Siescon pela ponte sem credencial em argumento de processo.
- Domínio e Siescon passaram a compartilhar um contrato de perfil usado pelo configurador e pelo serviço. A configuração protegida grava `SourceSystem`; instalações antigas sem o campo continuam Domínio.
- O WiX continua sendo um único produto e ganhou descrição neutra, reparo de mesma versão, atalho no menu Iniciar e supressão da abertura do configurador em instalação silenciosa. O diagnóstico recusa pacote sem a ponte x86.
- `build.ps1` agora limpa somente suas saídas próprias, verifica todos os executáveis e falha diante de retorno não zero. O CI recebeu um job Windows que gera o MSI e reconcilia seu SHA-256 com `release.json`; D-291 foi preservada e nenhum autoatualizador entrou.
- Serviço, configurador e ponte compilaram sem avisos; 20 testes .NET passaram; WiX/XML e workflow YAML passaram em validação estática. A suíte Python manteve 967 aprovados, 3 ignorados e 11 subtestes. O MSI não foi gerado localmente porque WiX não suporta macOS; a primeira execução do job Windows, instalação, assinatura e ERP real seguem pendentes.

## 28/09/2026 — Etapa 14 revalidada após pull; herança visual corrigida (V-288)

- `git pull --ff-only` confirmou CICA `main` em `d501fbe` e ProjetoARD `main` em `d9d4ebb`, sem novos commits remotos. O trabalho da etapa 14 permanece na worktree local separada, 20 commits além da `main`, com alterações não commitadas preservadas.
- Contrato de cálculo idêntico ao ProjetoARD. Lint, MyPy, Django, migrações, compilação dos três projetos .NET e 20 testes .NET passaram. A suíte Python aprovou 967 testes, 3 ignorados e 11 subtestes, mas a cobertura global ficou em 80,11%, abaixo do piso documental de 85%; o módulo Rentabilidade isolado ficou em 87%.
- A inspeção em navegador com SQLite e dados fictícios revelou que oito templates descartavam os estilos herdados do workspace. Corrigida a herança; visão geral e ficha analítica foram vistas em desktop e celular, sem overflow ou erro de console. Quatro telas adicionais abriram em ambos os tamanhos, também sem overflow. Os 169 testes específicos passaram após a correção. A formatação .NET dos dois arquivos apontados pelo verificador foi normalizada; o verificador voltou a passar.
- Não se marcou a etapa como concluída: o MSI exige execução do job Windows, o adaptador Siescon e as consultas não validadas precisam de base autorizada, Q-41 a Q-43 seguem abertas e a homologação real permanece na etapa 12. Nenhum código foi integrado à `main` ou enviado ao GitHub nesta entrega.

## 09/10/2026 — guia funcional para QA (V-293)

- `CICA-QA.md` criado na raiz com mapa do produto, perfis, funções, roteiros de teste e modelo de evidência.
- Fonte: plano vigente, decisões, validações, etapas e rotas; nenhuma regra ou homologação foi criada.
- README e checklist da etapa 00 atualizados. Links locais e diff conferidos em V-293.
- Próximo uso: QA escolhe release/ambiente e executa os casos pertinentes; estados externos continuam abertos.
