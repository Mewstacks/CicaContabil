# API oficial Domínio / Onvio

Atualizado em 18/09/2026. Este é o contrato externo vigente para a CICA; ele não autoriza chamadas reais nem substitui a homologação da etapa 12.

Para a redação da oferta e do site, usar [Limitações comerciais Domínio Web](dominio-web-limitacoes-comerciais.md). Este documento permanece técnico.

## O que a documentação oficial confirma

O portal da Thomson Reuters disponibiliza duas famílias relevantes:

| Família | Autenticação | Recursos documentados | Uso na CICA |
| --- | --- | --- | --- |
| Integração ERP Domínio v3 | OAuth `client_credentials`, chave do escritório e `integrationKey` por empresa | ativação, envio de XML em lote e consulta do lote | Entrada fiscal XML e confirmação de processamento |
| Onvio BR Accounting API v2 | OAuth `authorization_code` com refresh token e consentimento do usuário | clientes integráveis paginados, estado da integração, envio e consulta de lote XML | Descoberta de empresas autorizadas, diagnóstico e entrada fiscal XML |

Fontes oficiais: [guia de integração ERP](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=8476), [OAuth da Onvio BR Accounting API](https://developerportal.thomsonreuters.com/onvio-br-accounting-api/documents/authenticating-with-oauth-20), [especificação de clientes v2](https://developerportal.thomsonreuters.com/secure-download/40412), [especificação de estado v2](https://developerportal.thomsonreuters.com/secure-download/40408) e [especificação de lotes v2](https://developerportal.thomsonreuters.com/secure-download/40395).

## Limite confirmado

As especificações públicas consultadas não documentam endpoints de leitura de lançamentos contábeis, notas já escrituradas, acumuladores, guias de folha, empregados ou dados fiscais gerais do Domínio Web. A API pode listar empresas integráveis e receber/consultar lotes; isso não é uma leitura completa da base Domínio.

Para obter eventual escopo adicional, a Thomson Reuters exige o cadastro da empresa parceira, contato técnico e callback HTTPS em `api.dominio@thomsonreuters.com`. A solicitação deve pedir explicitamente o Swagger e os escopos de leitura para empresas, contábil, escrita fiscal e folha. Não presumir que tais escopos existem ou serão concedidos.

## Implementação CICA

- `apps.hub.dominio_api` cobre o fluxo ERP v3 documentado: token, confirmação de ativação, geração da `integrationKey`, envio multipart e consulta de lote.
- O adaptador Onvio v2 deve usar autorização por redirecionamento, validar `state`, guardar refresh token cifrado por escritório e paginar a lista de clientes.
- Client ID, Client Secret, callback HTTPS, chaves do escritório e tokens só entram na configuração de produção da etapa 12; nunca no repositório, logs ou chat.
- O agente CICA continua como leitor local somente leitura para os contratos de contabilidade, fiscal e folha que a API pública não cobre.

## Próxima homologação externa

1. Cadastrar a CICA como parceira e receber as credenciais OAuth.
2. Registrar o callback HTTPS hospedado.
3. Fazer login com usuário autorizado do escritório e validar a lista paginada de clientes.
4. Validar ativação de uma empresa e o processamento de um XML não produtivo autorizado.
5. Solicitar e avaliar qualquer Swagger/escopo adicional de leitura antes de implementar esse acesso.
