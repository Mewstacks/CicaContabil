# Etapa 03 â€” Concluir agente Windows e integraÃ§Ã£o DomÃ­nio

[Plano mestre](../../../PLANO-MESTRE.md) Â· [DecisÃµes](../../../DECISOES.md) Â· [ValidaÃ§Ãµes](../../../VALIDACOES.md)

**Estado:** ConcluÃ­da no nÃ­vel de implementaÃ§Ã£o e validaÃ§Ã£o local em 18/09/2026. O contrato ODBC Fedrizzi foi validado em ambiente real autorizado (V-010), D-80 definiu o serviÃ§o nativo CICA como pacote Ãºnico e D-82 definiu API oficial DomÃ­nio/Onvio como rota preferencial. Por D-86, a homologaÃ§Ã£o operacional contra o site publicado e o piloto real fica na etapa 12.

**DependÃªncias:** 01â€“02.

**DecisÃµes relacionadas:** D-06, D-18, D-46, D-52, D-74, D-80, D-81, D-82, D-83.

## Escopo e checklist

- [x] Arquitetura definida em D-80; sincronizaÃ§Ã£o de empresas DomÃ­nio Local iniciada no serviÃ§o nativo v2, com pÃ¡ginas de 500 e sem desativaÃ§Ã£o por pÃ¡gina parcial.
- [x] Entregar e instalar localmente o MSI CicaAgent, com configurador, serviÃ§o automÃ¡tico, configuraÃ§Ã£o DPAPI e procedimento de diagnÃ³stico em `agent-windows/INSTALACAO.md`.
- [-] Homologar DSNs e drivers nas arquiteturas suportadas. O pacote define suporte x64 e o configurador filtra componentes incompatÃ­veis em V-024; a execuÃ§Ã£o real e a instalaÃ§Ã£o limpa foram transferidas para a etapa 12 por D-86.
- [x] Preparar os adaptadores oficiais DomÃ­nio ERP v3 e Onvio v2 conforme contratos publicados; configuraÃ§Ã£o OAuth e homologaÃ§Ã£o externa ficam para a etapa 12 por D-81/D-82.
- [-] Homologar atualizaÃ§Ã£o, revogaÃ§Ã£o, diagnÃ³stico e recuperaÃ§Ã£o de rede do agente; o reinÃ­cio local administrativo foi validado em V-017. DiagnÃ³stico, retentativa, renovaÃ§Ã£o, aviso de atualizaÃ§Ã£o e suporte local foram preparados em V-020â€“V-023; a prova de rede, mTLS e atualizaÃ§Ã£o distribuÃ­da pertence Ã  etapa 12 por D-86.
- [x] Validar DomÃ­nio Local; a importaÃ§Ã£o de backup DomÃ­nio Web foi transferida para a etapa 12 como contingÃªncia por D-82.
- [x] Preparar o processador nativo de backup: hash antes da leitura, download atÃ´mico restrito ao servidor CICA, extraÃ§Ã£o protegida contra caminhos fora da fila temporÃ¡ria e envio em pÃ¡ginas de 500, sem limites silenciosos. A prova com backup autorizado, retomada e nÃ£o duplicaÃ§Ã£o foi adiada para a etapa 12 por D-82/D-83.
- [x] Mapear estruturas DomÃ­nio observadas para contÃ¡bil, fiscal e folha em `agent-windows/CONTRATOS-DOMINIO.md`; consultas novas exigem pacote semÃ¢ntico, teste e aprovaÃ§Ã£o antes de habilitaÃ§Ã£o.
- [x] Preparar sincronizaÃ§Ã£o nativa paginada de empresas e extratos bancÃ¡rios pelo protocolo v2; validaÃ§Ã£o real fica registrada em V-027.
- [-] Homologar escrita documental nas pastas Windows permitidas. D-84/D-85 tornam raiz e formato configurÃ¡veis por escritÃ³rio dentro da CICA e entregues ao agente pareado; V-025/V-026 registram a preparaÃ§Ã£o. A validaÃ§Ã£o pelo agente e a prova de escrita real ficam na etapa 12 por D-86, quando Q-22/Q-31 serÃ£o definidos para o piloto.

## Bloqueios e responsabilidade

Q-22, Q-28 e Q-31. D-80 resolveu a arquitetura definitiva. Por D-86, Q-22/Q-31 e a execuÃ§Ã£o contra ambiente publicado deixam de bloquear o encerramento local desta etapa e passam a compor o piloto da etapa 12. A importaÃ§Ã£o DomÃ­nio Web aguarda backup `.dom` autorizado e chave correspondente para a validaÃ§Ã£o da etapa 12; nesta etapa, o fluxo fica preparado sem alegaÃ§Ã£o de execuÃ§Ã£o real. Os [limites comerciais](../../dominio-web-limitacoes-comerciais.md) permanecem em D-83.

Regras e autorizaÃ§Ã£o externa: responsÃ¡vel pelo projeto. CÃ³digo, inventÃ¡rio e verificaÃ§Ã£o local: executor da etapa. Os IDs Q apontam ao [registro Ãºnico de dÃºvidas](../duvidas-abertas.md); nÃ£o criar a mesma pergunta em outro documento.

## Testes e aceite

Os testes de instalaÃ§Ã£o limpa, x64, revogaÃ§Ã£o, fila offline, repetiÃ§Ã£o, volume, atualizaÃ§Ã£o e escape/reparse points/UNC ficam para a etapa 12 por D-86.

**CritÃ©rio de encerramento local:** serviÃ§o nativo, configurador, instalador, protocolo seguro, consultas allowlisted e sincronizaÃ§Ã£o paginada preparados e com evidÃªncias locais. O aceite operacional original â€” instalar em mÃ¡quina limpa, sincronizar, interromper a rede, reiniciar e retomar sem perder ou duplicar dados â€” Ã© obrigatÃ³rio na etapa 12.

## EvidÃªncias e prÃ³ximo passo

V-010/V-017: o contrato ODBC Fedrizzi foi executado sem imprimir DSN ou dados: 4 consultas allowlisted, 5 objetos obrigatÃ³rios, 13.875 linhas e nenhuma coluna ausente. A descoberta persistiu somente metadados para 500 objetos gerais, 49 de folha e 387 contÃ¡beis. A rota v2 e processador nativo de empresas passaram em 5 testes e build .NET Release sem avisos. O processador de backup nÃ£o possui mais cortes de 10 mil/100 mil linhas e envia pÃ¡ginas de 500. Os adaptadores oficiais DomÃ­nio ERP v3 e Onvio v2 passaram em quatro testes locais. O MSI CicaAgent foi gerado, instalado e reiniciado na prÃ³pria estaÃ§Ã£o Fedrizzi como serviÃ§o automÃ¡tico em execuÃ§Ã£o, sem configuraÃ§Ã£o de rede. V-020 preparou um arquivo local de estado sem segredos e retentativa progressiva para falhas de comunicaÃ§Ã£o; V-021 preparou a renovaÃ§Ã£o de certificado com a chave que permanece na estaÃ§Ã£o; V-022 preparou o versionamento do pacote e o aviso de atualizaÃ§Ã£o sem execuÃ§Ã£o automÃ¡tica. V-084 tornou recuperÃ¡vel o histÃ³rico local de 21 lotes de importaÃ§Ã£o no onboarding, preservando fonte e prÃ©via e sem enviar arquivo. A API pÃºblica nÃ£o documenta leitura completa de contÃ¡bil/fiscal/folha; o agente local segue como rota para esses dados atÃ© a Thomson Reuters conceder escopos especÃ­ficos. OAuth, instalaÃ§Ã£o limpa, atualizaÃ§Ã£o, revogaÃ§Ã£o, rede e homologaÃ§Ã£o externa ficam para a etapa 12 por D-81/D-82.

## Prompt de execuÃ§Ã£o

> Execute a etapa 03. Complete o serviÃ§o instalÃ¡vel e o conector DomÃ­nio local/Web. Apresente a decisÃ£o tÃ©cnica pendente sobre Python e serviÃ§o nativo com evidÃªncias antes de alterar essa arquitetura. Homologue instalaÃ§Ã£o, leitura, recuperaÃ§Ã£o, atualizaÃ§Ã£o e pastas Windows, sem SQL arbitrÃ¡rio nem escrita no banco DomÃ­nio.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. NÃ£o refaÃ§a decisÃµes confirmadas. Pergunte ao responsÃ¡vel somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alteraÃ§Ãµes existentes. NÃ£o incorra em custos sem aprovaÃ§Ã£o especÃ­fica imediatamente anterior. Ao terminar, atualize os .md com mudanÃ§as, testes executados, evidÃªncias, limitaÃ§Ãµes, bloqueios e prÃ³ximo passo. NÃ£o marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitaÃ§Ã£o atual; a existÃªncia do prÃ³ximo prompt nÃ£o autoriza iniciar outra etapa.

## CorreÃ§Ã£o local V-189 â€” sequÃªncia de sincronizaÃ§Ã£o

`DominioLocalProcessor.RunOnce` encerrava a execuÃ§Ã£o ao encontrar a Ãºltima pÃ¡gina de empresas, deixando `SendBankEntries` inalcanÃ§Ã¡vel. A fase agora termina com `break` e inicia a leitura de extratos somente quando o cancelamento nÃ£o foi solicitado. A alteraÃ§Ã£o usa exclusivamente as duas consultas existentes e allowlisted; nÃ£o envia fechamento, reabertura, aceite ou pagamento. A build Release do serviÃ§o passou depois de corrigir a sobrecarga de `DownloadAsync` para usar `PathAndQuery`; também sem avisos.

A prova operacional ainda exige o piloto da etapa 12: parear o agente, usar um DSN autorizado, verificar que empresas e extratos chegam paginados, interromper entre as duas fases e retomar sem duplicar registros. NÃ£o executar esse piloto sem autorizaÃ§Ã£o e ambiente publicado apropriado.

### Evidência Fedrizzi V-198 — leitura direta allowlisted

25/09/2026: o DSN autorizado `contabil` respondeu à consulta de empresas com 576 registros e à consulta de guias com 3.335 registros. A sincronização local espelhou empresas e 10.000 registros normalizados. O contrato de guia não forneceu vencimento, logo nenhum prazo de guia foi inferido. A operação foi de leitura; não houve escrita no Domínio, emissão, transmissão ou chamada cobrada. A prova do agente pareado, interrupção e retomada continua na etapa 12.

## Atualização PC-19/CONTAD — D-302/D-303/V-302 (02/11/2026)

**Pacote testado em 03/11/2026 — D-306/V-305:** [CI Windows aprovado](https://github.com/Mewstacks/CicaContabil/actions/runs/41664064414),
MSI 1.0.0 e SHA-256 conferidos na cópia local em `agent-windows/artifacts/`.
25 verificações do ciclo instalado, 23 testes .NET e 23 testes do servidor
aprovados. O primeiro ensaio descobriu ACL herdado na pasta de configuração;
o MSI agora a protege para Administradores/SYSTEM. Pacote ainda sem assinatura
de editor. Instalação no PC da cliente, driver/DSN/pareamento, ERP e retomada
de rede reais continuam pendentes; não foram simulados como aceite.

- [x] Gerar MSI atual, preservar artefatos e conferir hash/manifesto/relatório.
- [x] Instalar, executar, diagnosticar, reparar, reiniciar e remover em Windows Server 2022 descartável.
- [x] Verificar pasta protegida e DPAPI sob LocalSystem sem credenciais reais.
- [ ] Instalar e parear no PC autorizado da cliente, com SQL Anywhere/DSN e credencial somente leitura reais.

Complemento de 03/11/2026 — D-305/V-304: títulos confirmados como origem
Domínio; saída do piloto inclui relatório e arquivo de importação. A entrada
normalizada de Razão e a ponte entre filas foram implementadas no servidor,
conforme [contrato local](../../conciliacao-razao-normalizado.md), sem habilitar
consulta ODBC nova ou alterar o agente. Acesso ao PC, instalação/pareamento e
contratos reais de Razão/parcelas/baixas continuam pendentes nesta instalação.

O responsável confirmou Domínio local e agente no computador da cliente; ela
ainda fornecerá o acesso. Reutilizar o serviço único .NET 8, sem instalar Python.
A conclusão local histórica da base desta etapa não comprova o conciliador CONTAD.

- [x] Compilar serviço, configurador e ponte x86 e executar 23 testes .NET.
- [x] Corrigir `is_linked` do processador local com o contrato `EXISTS` já
  allowlisted, sem escrita no ERP nem inferência de escrituração.
- [x] Preparar [roteiro do piloto CONTAD](../verificacao-conciliador-contad-2026-11-02.md).
- [ ] Receber acesso autorizado e instalar/parear o pacote Windows conferido
  no computador da cliente; testar DSN, credencial do serviço e rede.
- [ ] Validar/implementar fonte de Razão e títulos comerciais. A consulta de
  extrato atual não entrega esses fatos e não os transforma em lançamentos.
- [ ] Homologar instalação, atualização, revogação, queda/retomada e integridade
  no ambiente real. A prova permanece na etapa 12; não declarar instalada.


## Windows 11 Desktop — D-307/V-306 (03/11/2026)

- [x] Testar os mesmos bytes do MSI 1.0.0 em Windows 11 cliente: Enterprise,
  build 26200, ARM64, 25 verificações aprovadas no run 41669715057.
- [x] Preservar hash, arquitetura e logs/relatórios separadamente de V-305.
- [x] V-307: controle RDP liberado, instalado o mesmo MSI no Windows 11 Pro
  AMD64 build 26200, 24 verificações aprovadas. Serviço mantido Running sem
  configuração ERP; não é instalação/pareamento no PC CONTAD.

A compatibilidade do instalador x64/ponte x86 sob emulação ARM64 não homologa
ODBC/SQL Anywhere, pareamento, ERP ou o ambiente CONTAD. Sem mudança no MSI.


### Continuidade Windows 11 x64 — V-307

Roteiro específico `agent-windows/test-windows11-pc.ps1`, hashes conferidos,
instalação/reparo com saída 0 e 24 checks aprovados. Preservar o agente instalado
em espera, sem credenciais. Relatórios/logs no PC e resumo local nos artefatos.
Acesso real à cliente, driver/DSN/pareamento e ERP seguem nos próprios gates.

### Conexão do PC de teste — D-308/V-308 (03/11/2026)

- [x] Abrir o configurador instalado, selecionar Domínio Local e conferir DSN
  de sistema/driver SQL Anywhere 16 encontrados, sem recriar a conexão D-74.
- [x] Executar o botão de teste somente leitura: banco recusou as credenciais
  preenchidas com ODBC 28000. Não é sucesso de leitura de dados.
- [x] V-309: esclarecer que o sucesso informado foi no ODBC/Domínio, identificar
  autenticação do DSN sobrescrita pelo configurador e corrigir no pacote 1.0.1.
- [x] Atualizar o PC de 1.0.0 para 1.0.1, serviço Running e teste no configurador
  mostrando conexão Domínio confirmada, sem ler/copiar senha do DSN.
- [ ] Parear e conferir sincronização real no escritório/recorte definido.

Em V-308, não salvou configuração, expôs senha ou enviou dados. RDP foi mantido
em tela cheia, configurador preservado em Domínio Local para a correção e sem
mudança do modo Scancode naquela execução.

V-309 supera o erro de conexão de V-308: opção explícita de usar autenticação
do DSN, mesma construção no teste e serviço, sem fallback de identidade após
erro. Configurações antigas conservam modo explícito. Teclado Unicode usado
temporariamente no diagnóstico e retornado a Scancode. Configurador atualizado
mantido aberto com sucesso visível, endereço/código vazios e sem salvar.
Pareamento bloqueado pelo servidor HTTPS: 503, CA do agente não configurada.

## Continuidade D-309/V-310 — recorte do piloto (04/11/2026)

- [x] Persistir recorte empresa/conta/competência/extratos e revisão no cadastro/agente.
- [x] Exigir protocolo compatível; filtrar antes do envio e recusar páginas externas no servidor.
- [x] Bloquear financeiro v2 sem recorte e demais módulos no agente restrito.
- [x] Preparar MSI 1.0.2: 38 testes .NET e 25 checks CI aprovados, hash registrado em V-310.
- [x] Escolher candidato por pesquisa local autorizada em Q-28: uma conta bruta, janeiro/2026, 115 itens; nenhum envio.
- [ ] Confrontar conta bancária e fechamento com a fonte, antes de emitir código.
- [ ] Atualizar o PC com 1.0.2 pelo canal disponível; rede local de transferência não respondeu, 1.0.1 preservado.
- [ ] Provar ODBC LocalSystem, mTLS Windows/hospedado e retomada no recorte real.

O Nginx/Django sintético passou em emissão, autenticação, renovação, cabeçalhos
forjados, rejeição fora do recorte e interrupção. Isso não comprova o ingresso
Fly ou o PC. Consulta de cabeçalho é diagnóstico; nenhum contrato de Razão,
título, parcela ou baixa foi presumido/habilitado. [Detalhes](../verificacao-conciliador-contad-2026-11-02.md).

Persistência final D-309/V-310: configuração DPAPI é gravada em arquivo
criptografado temporário na pasta protegida, com flush e substituição atômica;
falha conserva o arquivo anterior e limpa o temporário. Ciclos sem mudança de
recorte/destino não regravam configuração. O pacote final foi revalidado no
Windows com 38 testes .NET, incluindo falha por bloqueio de arquivo, e 25 checks
MSI (run 41845516300). Sem atualização no PC ou alteração do DSN.

## Revisão do pareamento — D-310/V-311 (04/11/2026)

- [x] Dispensar CA privada/mTLS no piloto por decisão do responsável.
- [x] Negociar modo HMAC explicitamente por HTTPS, com código de uso único, segredo individual, revogação e recorte preservados.
- [x] Não gerar CSR/PFX nem renovar certificado no modo HMAC; manter validação normal do HTTPS do servidor.
- [x] Preservar configurações antigas em modo certificado, sem fallback silencioso.
- [x] Compartilhar gravação atômica no configurador/serviço; restringir a pasta antes de gravar.
- [x] Preparar MSI 1.0.3: 44 testes .NET e 26 checks Windows, incluindo LocalSystem com HMAC/DPAPI sem PFX.
- [ ] Publicar backend compatível e atualizar o PC por pacote/hash/guardas conferidos.
- [ ] Parear/sincronizar no recorte real aprovado; provar ODBC LocalSystem e retomada.

A exigência anterior de mTLS no piloto está superada. O acesso Fly ainda não
está disponível; nenhuma configuração hospedada ou instalação do PC foi alterada.

## Continuidade D-311/V-312 — 05/11/2026

- [x] Reconferir bytes do MSI 1.0.3 e fonte contra commit CI; 43 arquivos
  comparados, somente documentação difere. Nenhum agente atualizado nesta rodada.
- [x] Repetir .NET no Mac: 43 aprovados, um skip exclusivamente Windows.
  Os 44 testes/26 checks Windows de V-311 continuam evidência histórica.
- [x] Preparar contrato normalizado local de títulos/parcelas/baixas, com
  identidade, conta, datas, valores, cobertura e estornos explícitos; sem SQL
  novo, persistência ou ativação no agente. [Contrato](../../conciliacao-fontes-titulos.md).
- [x] Acessar novamente a sessão RDP logada após superar leitura transitória
  da ferramenta; não repetir pedido de conexão/DSN ou caminhos de relatórios
  que o responsável confirmou ainda não existirem.
- [ ] Confrontar/adaptar Razão e títulos Domínio no recorte Fedrizzi e depois
  CONTAD, com revisão contábil Q-28/Q-46. Preparação sintética não os homologa.
- [x] Instalar versão completa Domínio 10.6A-10 oficial, assinatura válida e
  backup confirmado; preservar caminho/DSN e desmarcar extras de nuvem/acesso remoto.
- [x] Concluir ajuste 2 de 05/11/2026; reabrir aplicação até login. Senha vazia,
  login direto solicitado ao responsável e teclado Scancode restaurado.
- [ ] Conferir acesso à aplicação/base e obter relatórios após o novo login.
- [ ] Publicação autorizada, instalação/pareamento, ODBC LocalSystem e
  sincronização real continuam abertos. [Release e retorno](../../contad-release-2026-11-05.md).

## Continuidade D-312/V-313 — 05/11/2026

- [x] Conferir novo login e versão efetiva Domínio 10.6A-10 -02.
- [x] Identificar conta contábil pela consulta de extrato e emitir Razão limitado
  ao candidato original; PDF observado no Windows, sem extração/homologação.
- [x] Consultar fechamento/controle de títulos, sem gravar; obter autorização
  para pesquisar alternativa somente leitura, registrada em D-312/Q-28/Q-46.
- [x] Preparar prévia offline de capacidades e CLI privada; 85 testes focados,
  sem SQL novo, persistência, pareamento ou ativação no agente.
- [x] Emitir A Pagar limitado na alternativa e conferir PDF no Windows;
  registrar campos ausentes e cinco consultas sem dados nos filtros de setembro.
- [ ] Obter/revisar fontes e exemplos reais, fechar contrato do adaptador e
  comprovar recorte contábil fechado; alternativa não foi homologada.
- [ ] Publicação, upgrade/pareamento, ODBC LocalSystem e envio real continuam
  dependentes dos gates documentados. MSI/DSN permanecem intactos.

## Publicação do código D-313/V-314 — 05/11/2026

- [x] Publicar fontes/configuração de exemplo/testes do agente na main, commit
  4fede1e, com 40 arquivos não Markdown iguais ao commit Windows validado.
- [x] CI 42067809017 aprovado: builds serviço/configurador/ponte, 43 testes
  .NET Linux/um skip Windows e build/manifesto MSI; sem instalação nova.
- [ ] Publicar backend hospedado e atualizar/parear o PC com acesso/autorização
  próprios; envio ao GitHub não demonstra ODBC LocalSystem ou sincronização real.

V-316 (05/11): percurso bancário dos anexos executado em banco/mídia isolados,
42 verificações finais aprovadas. Não acionou agente/ODBC/Windows nem altera
o estado pendente de implantação e sincronização real desta etapa.


V-317/D-315 (05/11): correção de retorno do detalhe e QA sintético não alteram
agente, DSN ou ERP. CI 42079806454 aprovou builds/testes Linux e manifesto MSI
da implementação 700b496, sem nova instalação/ODBC LocalSystem ou pareamento.

### Origem backup: carteira editável e corte por fotografia (D-319, V-321)

05/11/2026. O escritório que vive de backup manual não tem agente atualizando o cadastro entre uma
importação e outra, e até aqui `ClientCompany.active` só era escrito pela importação. Agora
`app/configuracoes/carteira/` lista código do Domínio, nome, CNPJ e situação e permite ativar ou
desativar empresa por empresa; a página só aparece onde a fonte é `dominio_web_backup` com
capacidade `companies`, sem conector Domínio e sem controle central.

O encerramento de um backup completo e sem erro de linha desativa as empresas daquela fonte que não
vieram na fotografia — desativa, nunca exclui. O backup prevalece: `BackupProcessor` já lê
`stat_emp` como coluna, sem filtro, e `apply_backup_page` reescreve `active` a cada importação, de
modo que a desativação manual vale até a próxima. O caminho do agente ao vivo não mudou: continua
`WHERE stat_emp = 'A'` e continua sem desativar ausências, porque `full_snapshot` é `False` nos
produtores atuais.

Limite: nada foi exercitado contra um `.dom` real nem contra a carteira da Bianchi. A prova
operacional dessa rotina continua dependendo do piloto da etapa 12.

## Implantação CONTAD — D-320/V-322 (06/11/2026)

- [x] Receber sessão acompanhada; após falhas nativas AnyDesk, respeitar escolha
  humana por testes guiados, sem controle alternativo do Mac.
- [x] Registrar diagnóstico informado: Windows/PowerShell x64, SQL Anywhere
  16/17 x64, zero DSNs de sistema x64; sistema x86 existente usa versão 17.
- [x] Operador transferiu/conferiu hash e instalou MSI 1.0.3 no PC CONTAD;
  informou Running/Automatic, versão correspondente e awaiting_configuration.
- [x] Preservar conexão/permissões existentes e serviço em espera, sem salvar
  configuração, senha extraída ou tentativa de identidade alternativa.
- [x] Receber informação de disponibilidade da credencial EXTERNO, sem senha
  no chat; não equivale a conexão ou permissões validadas.
- [x] Receber relato de Test Connection successful no novo CICA_CONTAD x64/
  SQL Anywhere 17, srvContabil e EXTERNO local; não equivale a teste do serviço.
- [x] Conferir imagem com CICA_CONTAD no seletor de DSNs de sistema x64.
- [x] Receber relato de conexão confirmada no configurador após orientação de
  EXTERNO explícito; mensagem final localizada abaixo dos botões.
- [ ] Conferir ausência de senha no novo DSN e modo efetivo da credencial;
  validar LocalSystem após recorte/pareamento, preservando o DSN original.
  Nome do banco/host/porta não foram presumidos.
- [x] Publicar backend compatível/release 72 após backup/restore pontual,
  conferir hub.0078/intelligence.0031 nos dois aliases e web/worker saudáveis.
- [ ] Concluir ativação/acesso CONTAD e autorizar recorte Q-28 antes do
  pareamento/envio e prova de retomada.
- [x] Receber identificação do piloto: SURIA, código Domínio 212, 09/2026;
  código informado pelo operador, sem consulta SQL ou cadastro remoto.
- [ ] Conferir conta/referência e IDs internos de extrato do recorte Q-28;
  não confundir com FITIDs bancários ou emitir pareamento genérico.
- [x] Conferir captura de Lançamentos de Extrato Bancário aberta pelo operador;
  conta vazia/11-2026 não comprovam consulta do recorte SURIA/09-2026.
- [x] Receber captura com BANCO SICREDI/09-2026 e movimentos importados;
  linhas visíveis conciliadas; operador depois transcreveu conta contábil 8.
- [x] Registrar conta contábil 8 — BANCO SICREDI do recorte SURIA/212;
  vínculo bancário e IDs de extrato continuam a exigir revisão própria.
- [ ] Resolver divergência Q-28 entre saldos da captura de extrato Domínio e
  dos PDFs antes de fechar recorte/parear; SURIA/212 confirmada pelo operador.
- [x] Preparar sonda pontual x64/SELECTs parametrizados e receber autorização
  específica de metadados/IDs/contagens, limitada a SURIA/212/conta 8/09-2026.
- [x] Receber resultado da sonda executada pelo operador e revisar retorno:
  um cabeçalho de empresa 212/conta 8/09-2026 e 163 itens, tecnicamente consistente.
  Primeira tentativa de caminho inexistente superada; resultado informado,
  sem prova de LocalSystem ou aprovação final do vínculo/recorte.
- [ ] Concluir revisão contábil do vínculo/saldos antes de promover o candidato
  a manifesto aprovado; manter configuração/pareamento/envio pendentes.
  Operador pode levantar identificação explícita no cadastro da conta 8;
  captura recebida confirma conta analítica/ativa BANCO SICREDI, sem agência/
  conta bancária visíveis; vínculo e origem do saldo permanecem pendentes.
- [ ] Fechar contratos reais Razão/títulos/parcelas/baixas Q-28/Q-46 e homologar.
- [x] Salvar resumo simples e prompt privado de continuidade, a pedido do
  responsável; [retomada](../../contad-continuidade-2026-11-06.md), sem concluir os gates.

Resultados do PC são informados pelo operador, não controle automatizado ou
homologação do ERP. Cadastro CONTAD está em ativação pendente; não usar os
escritórios Bianchi/Cobalchini. Pacote sem Authenticode; checks Windows de V-311
continuam históricos. O acesso Fly anterior indisponível foi superado.

Retomada D-320/V-323 (06/11/2026): arquivos bancários/Razão aceitos como
evidência de teste da empresa informada como fechada. Leitor PDF/CLI local
confronta os 163 movimentos sem exigir a origem do saldo da captura Domínio.
Essa entrega não aciona o serviço ou altera os gates de recorte/envio; não
repetir instalação, sonda ou pergunta do importador para prosseguir no corpus.
