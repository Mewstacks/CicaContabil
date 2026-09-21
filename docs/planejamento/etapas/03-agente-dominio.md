# Etapa 03 — Concluir agente Windows e integração Domínio

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Concluída no nível de implementação e validação local em 18/09/2026. O contrato ODBC Fedrizzi foi validado em ambiente real autorizado (V-010), D-80 definiu o serviço nativo CICA como pacote único e D-82 definiu API oficial Domínio/Onvio como rota preferencial. Por D-86, a homologação operacional contra o site publicado e o piloto real fica na etapa 12.

**Dependências:** 01–02.

**Decisões relacionadas:** D-06, D-18, D-46, D-52, D-74, D-80, D-81, D-82, D-83.

## Escopo e checklist

- [x] Arquitetura definida em D-80; sincronização de empresas Domínio Local iniciada no serviço nativo v2, com páginas de 500 e sem desativação por página parcial.
- [x] Entregar e instalar localmente o MSI CicaAgent, com configurador, serviço automático, configuração DPAPI e procedimento de diagnóstico em `agent-windows/INSTALACAO.md`.
- [-] Homologar DSNs e drivers nas arquiteturas suportadas. O pacote define suporte x64 e o configurador filtra componentes incompatíveis em V-024; a execução real e a instalação limpa foram transferidas para a etapa 12 por D-86.
- [x] Preparar os adaptadores oficiais Domínio ERP v3 e Onvio v2 conforme contratos publicados; configuração OAuth e homologação externa ficam para a etapa 12 por D-81/D-82.
- [-] Homologar atualização, revogação, diagnóstico e recuperação de rede do agente; o reinício local administrativo foi validado em V-017. Diagnóstico, retentativa, renovação, aviso de atualização e suporte local foram preparados em V-020–V-023; a prova de rede, mTLS e atualização distribuída pertence à etapa 12 por D-86.
- [x] Validar Domínio Local; a importação de backup Domínio Web foi transferida para a etapa 12 como contingência por D-82.
- [x] Preparar o processador nativo de backup: hash antes da leitura, download atômico restrito ao servidor CICA, extração protegida contra caminhos fora da fila temporária e envio em páginas de 500, sem limites silenciosos. A prova com backup autorizado, retomada e não duplicação foi adiada para a etapa 12 por D-82/D-83.
- [x] Mapear estruturas Domínio observadas para contábil, fiscal e folha em `agent-windows/CONTRATOS-DOMINIO.md`; consultas novas exigem pacote semântico, teste e aprovação antes de habilitação.
- [x] Preparar sincronização nativa paginada de empresas e extratos bancários pelo protocolo v2; validação real fica registrada em V-027.
- [-] Homologar escrita documental nas pastas Windows permitidas. D-84/D-85 tornam raiz e formato configuráveis por escritório dentro da CICA e entregues ao agente pareado; V-025/V-026 registram a preparação. A validação pelo agente e a prova de escrita real ficam na etapa 12 por D-86, quando Q-22/Q-31 serão definidos para o piloto.

## Bloqueios e responsabilidade

Q-22, Q-28 e Q-31. D-80 resolveu a arquitetura definitiva. Por D-86, Q-22/Q-31 e a execução contra ambiente publicado deixam de bloquear o encerramento local desta etapa e passam a compor o piloto da etapa 12. A importação Domínio Web aguarda backup `.dom` autorizado e chave correspondente para a validação da etapa 12; nesta etapa, o fluxo fica preparado sem alegação de execução real. Os [limites comerciais](../../dominio-web-limitacoes-comerciais.md) permanecem em D-83.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Os testes de instalação limpa, x64, revogação, fila offline, repetição, volume, atualização e escape/reparse points/UNC ficam para a etapa 12 por D-86.

**Critério de encerramento local:** serviço nativo, configurador, instalador, protocolo seguro, consultas allowlisted e sincronização paginada preparados e com evidências locais. O aceite operacional original — instalar em máquina limpa, sincronizar, interromper a rede, reiniciar e retomar sem perder ou duplicar dados — é obrigatório na etapa 12.

## Evidências e próximo passo

V-010/V-017: o contrato ODBC Fedrizzi foi executado sem imprimir DSN ou dados: 4 consultas allowlisted, 5 objetos obrigatórios, 13.875 linhas e nenhuma coluna ausente. A descoberta persistiu somente metadados para 500 objetos gerais, 49 de folha e 387 contábeis. A rota v2 e processador nativo de empresas passaram em 5 testes e build .NET Release sem avisos. O processador de backup não possui mais cortes de 10 mil/100 mil linhas e envia páginas de 500. Os adaptadores oficiais Domínio ERP v3 e Onvio v2 passaram em quatro testes locais. O MSI CicaAgent foi gerado, instalado e reiniciado na própria estação Fedrizzi como serviço automático em execução, sem configuração de rede. V-020 preparou um arquivo local de estado sem segredos e retentativa progressiva para falhas de comunicação; V-021 preparou a renovação de certificado com a chave que permanece na estação; V-022 preparou o versionamento do pacote e o aviso de atualização sem execução automática. V-084 tornou recuperável o histórico local de 21 lotes de importação no onboarding, preservando fonte e prévia e sem enviar arquivo. A API pública não documenta leitura completa de contábil/fiscal/folha; o agente local segue como rota para esses dados até a Thomson Reuters conceder escopos específicos. OAuth, instalação limpa, atualização, revogação, rede e homologação externa ficam para a etapa 12 por D-81/D-82.

## Prompt de execução

> Execute a etapa 03. Complete o serviço instalável e o conector Domínio local/Web. Apresente a decisão técnica pendente sobre Python e serviço nativo com evidências antes de alterar essa arquitetura. Homologue instalação, leitura, recuperação, atualização e pastas Windows, sem SQL arbitrário nem escrita no banco Domínio.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
