# Domínio Web: capacidades e limites para comunicação comercial

Atualizado em 18/09/2026. Este documento é a referência comercial da CICA para a integração com Domínio Web/Onvio. Ele separa o que foi documentado publicamente pela Thomson Reuters, o que a CICA já preparou e o que ainda depende de homologação. Não use uma capacidade preparada como promessa de produção antes da homologação correspondente.

## Mensagem comercial aprovada

A CICA integra-se ao ecossistema Domínio em duas rotas complementares:

1. **API oficial Domínio/Onvio:** descoberta de empresas autorizadas, diagnóstico da integração e envio/consulta de lotes de XML fiscal, conforme os contratos públicos liberados pela Thomson Reuters.
2. **Agente CICA no escritório:** leitura local, exclusivamente autorizada e sem escrita no Domínio, para os dados contábeis, fiscais e de folha que não estejam expostos na API oficial contratada pelo escritório.

O backup Domínio Web é uma contingência: o operador envia o arquivo e a chave exibida no Onvio; o agente CICA o processa localmente e devolve apenas os dados permitidos. Esta rota não substitui a API e não deve ser oferecida como sincronização automática até a homologação da etapa 12.

## O que pode ser prometido depois da homologação

| Capacidade | Rota | Situação em 18/09/2026 | Condição para venda |
| --- | --- | --- | --- |
| Listar empresas que o usuário autorizou integrar | Onvio BR Accounting API v2 | Adaptador preparado; OAuth real pendente | Credenciais de parceiro, callback HTTPS e homologação com escritório autorizado |
| Verificar estado da integração | Onvio BR Accounting API v2 | Adaptador preparado | Mesmas credenciais e homologação da API |
| Ativar empresa para integração fiscal e enviar XML em lote | ERP Domínio API v3 | Adaptador preparado | Chaves liberadas pela Thomson Reuters e teste de lote autorizado |
| Consultar resultado de lote XML enviado | ERP Domínio API v3 | Adaptador preparado | Homologação do fluxo anterior |
| Ler empresas, contabilidade, fiscal e folha disponíveis no Domínio Local | Agente CICA + ODBC | Contrato de leitura local validado no ambiente Fedrizzi; agente e instalador preparados | Homologação operacional do agente pareado, inclusive interrupção e retomada |
| Importar um backup Domínio Web manual | Agente CICA | Processador preparado; prova com `.dom` real ainda pendente | Backup autorizado, chave correspondente e homologação de integridade/retomada |

## Limites que precisam constar na oferta

### A API pública não equivale à leitura completa do Domínio Web

Nas especificações públicas consultadas, a Thomson Reuters documenta autenticação OAuth, clientes integráveis, estado da integração e lotes de XML. Elas **não documentam** endpoints públicos para ler lançamentos contábeis, notas já escrituradas, acumuladores, guias de folha, empregados ou a totalidade dos dados fiscais do Domínio Web.

Portanto, não usar nas páginas, propostas ou apresentações afirmações como:

- “a CICA lê toda a base do Domínio Web pela API”;
- “a CICA sincroniza automaticamente contábil, fiscal e folha pelo Onvio”;
- “a CICA altera lançamentos, acumuladores ou dados dentro do Domínio”.

Se a Thomson Reuters fornecer Swagger e escopos adicionais à CICA, a equipe deve registrar o contrato, implementar somente os recursos concedidos e homologá-los antes de alterar esta página comercial.

### Acesso depende de autorização e contrato do escritório

OAuth exige consentimento do usuário autorizado. O acesso à API depende de cadastro de parceiro, credenciais, callback HTTPS e escopos concedidos pela Thomson Reuters. Cada escritório vê somente suas próprias empresas e dados; a CICA não usa credenciais de um cliente para acessar outro.

### O agente local é necessário onde a API não cobre a leitura

Para dados que não possuam endpoint público concedido, a CICA precisa do agente instalado na rede do escritório e de um acesso de leitura autorizado ao Domínio Local. O agente usa consultas previamente definidas, paginação e rastreabilidade. Ele não recebe SQL remoto e não escreve no banco Domínio.

### Backup Domínio Web não é instantâneo nem automático

O backup requer que o escritório gere o arquivo no Onvio, forneça a chave do próprio arquivo e o envie pela interface. O processamento acontece no agente local. Durante a importação, o arquivo e a chave são tratados como material sensível; após a conclusão, devem ser removidos conforme o fluxo de retenção.

Antes da homologação real, a comunicação correta é: **“importação de backup Domínio Web em preparação de homologação”**. Não dizer que a CICA já importa qualquer backup, cobre todo o seu conteúdo ou garante retomada sem prova no arquivo autorizado.

## Perguntas de venda e resposta correta

| Pergunta | Resposta correta |
| --- | --- |
| “Vocês conectam ao Domínio Web?” | “Sim, pela API oficial nos recursos liberados pela Thomson Reuters. Para leituras que a API pública não disponibiliza, a CICA opera com agente local autorizado.” |
| “Puxa toda a minha contabilidade pelo Onvio?” | “A documentação pública não confirma essa leitura completa. Validamos o escopo liberado para o seu escritório; se for necessário, usamos o agente local somente leitura.” |
| “A CICA escreve no Domínio?” | “Não. A integração atual não grava no banco Domínio. XMLs podem ser enviados somente pelo fluxo oficial e homologado da Thomson Reuters.” |
| “Posso usar backup?” | “Sim, como contingência mediante backup e chave fornecidos pelo escritório. A disponibilidade comercial depende da homologação do arquivo real.” |
| “O que vocês precisam instalar?” | “Somente o agente CICA quando a leitura local ou o processamento de backup forem necessários. A instalação, permissões e diagnóstico são validados antes da liberação.” |

## Fontes oficiais e controle de atualização

- [Integração ERP Domínio v3 — guia oficial](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=8476)
- [OAuth 2.0 — Onvio BR Accounting API](https://developerportal.thomsonreuters.com/onvio-br-accounting-api/documents/authenticating-with-oauth-20)
- [Especificação de clientes integráveis v2](https://developerportal.thomsonreuters.com/secure-download/40412)
- [Especificação de estado da integração v2](https://developerportal.thomsonreuters.com/secure-download/40408)
- [Especificação de lotes XML v2](https://developerportal.thomsonreuters.com/secure-download/40395)

Antes de publicar ou atualizar uma página comercial, revisar essas fontes, o [contrato técnico da API](dominio-api-oficial.md), a [etapa 03](planejamento/etapas/03-agente-dominio.md) e [VALIDACOES.md](../VALIDACOES.md). Alterações de versão, escopo ou política da Thomson Reuters precisam ser registradas em `DECISOES.md` e validadas antes de mudar a promessa comercial.

## Estado de evidência

| Marco | Estado |
| --- | --- |
| Implementado | Adaptadores de API, agente nativo e processamento de backup estão preparados no repositório. |
| Testado localmente | Contratos de API foram testados sem chamada externa; o contrato ODBC Fedrizzi foi validado. |
| Homologado no ambiente real | Somente a consulta ODBC permitida. OAuth, API oficial, pareamento público e backup `.dom` real ainda não foram homologados. |
| Liberado para venda | Depende das homologações da etapa 12 e da aprovação por módulo do responsável. |
