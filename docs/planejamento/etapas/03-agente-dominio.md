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
