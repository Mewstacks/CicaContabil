# Spec (rascunho) — MCP do Domínio, Fase 2: gateway no CICA (21/11/2026)

Só entra em execução depois da Fase 1 ([dominio-mcp.md](dominio-mcp.md)) e de OK próprio. Pesquisa: [Serpro](../pesquisa/serpro-integra-contador-mcp.md), [Domínio e IAs](../pesquisa/dominio-mcp-pesquisa-externa.md). Tudo é aditivo (migração só adiciona), atrás de flag desligada e de modo por organização, sem tocar nos módulos congelados (regras L1 a L5 de [produto-vendavel.md](produto-vendavel.md)).

## Objetivo

O dono usa o MCP no **Claude web e celular** e no **ChatGPT web** entrando com o login do CICA; o **Copiloto** passa a usar as mesmas ferramentas; o Domínio chega pelo agente de saída, sem abrir porta; o Serpro entra com allowlist e custo controlado.

## Peças

| # | Peça | Fato de partida | Desenho |
|---|---|---|---|
| 1 | Autenticação OAuth 2.1 (servidor de autorização e recurso protegido) | `mcp_endpoint` em `src/apps/intelligence/api.py:32` (rota `intelligence/mcp/` em `src/config/urls_api.py:25`) usa só sessão Django; não há biblioteca de servidor OAuth em `requirements.txt` | `401` com `WWW-Authenticate` apontando os metadados do recurso (RFC 9728); metadados do servidor (RFC 8414) com PKCE somente S256, `client_id_metadata_document_supported` e `none` no endpoint de token; CIMD e DCR; `resource` (RFC 8707) obrigatório e igual à URL do gateway; token opaco com hash no banco (revogação imediata), refresh rotativo; login e MFA do CICA; tela de consentimento; redirecionamentos fixos (`https://claude.ai/api/mcp/auth_callback`, callbacks do ChatGPT, loopback do Claude Code). Claude só usa o primeiro `authorization_servers` e exige `401` para iniciar o login |
| 2 | Endpoint MCP externo | `call_tool` em `intelligence/mcp.py` já aplica `authorization_is_fresh`, `companies_for_membership` e `company_has_capability` | Streamable HTTP em rota nova; mesmas permissões; `tools/list` filtrada por capacidade; limite por token e por escritório; auditoria por `record_event` sem conteúdo |
| 3 | Repasse ao agente | Agente só sai, só consultas fixas, ciclo de 60 s (`HUB_AGENT_INTERVAL_SECONDS`) | Fila de trabalho assinada (HMAC já existente), `job = {ferramenta, argumentos, versão do contrato, versão do pack}` só L0 a L2, nunca L3 nem SQL (a consulta estruturada amplia o modelo atual de consultas fixas: pede contrato próprio e teste de recusa); o agente compila contra o pack local e devolve o resultado moldado; modo de espera longa para p95 ≤ 5 s; fila própria, sem disputar a dos tenants atuais (L5) |
| 4 | Serpro | `apps/integra/catalog.py` é registro fechado com verbo e `billable` | Ferramentas só de consulta por `idServico` (Apêndice A da pesquisa), acrescentadas ao registro de forma aditiva (PGDAS-D 13 a 16, DEFIS 142 a 144, MIT 316 e 317, PAGTOWEB 71 e 73, EVENTOS 131 a 134, SICALC 54); cada uma declara custo, procuração exigida e se cobra |
| 5 | Governador de custo | 200, 202 e 403 são cobrados; faixa mensal por categoria | Teto por escritório e por conversa; pré-checagem de procuração (`OBTERPROCURACAO41`, cache curto) porque 403 cobra; evento gratuito antes da consulta paga; contador por `X-Request-Tag`; sem laço de modelo |
| 6 | Cruzamentos | 9 cruzamentos viáveis só com leitura (pesquisa, 3.2) | Motor determinístico (Python) que combina L1 e Serpro e devolve achados estruturados (id, severidade, evidência, fonte, data e hora da consulta); a IA explica e prioriza. Ordem: procuração × vigência, mensagens DTE (só metadados), SITFIS, índice do PGDAS-D |
| 7 | Copiloto | `answer_question` e `gateway.py` | Passa a chamar `call_tool` com o mesmo conjunto; sem dado pessoal por padrão |

## Escolhas que dependem de pesquisa de versão (regra do repo)

Biblioteca do servidor de autorização (Authlib, django-oauth-toolkit ou mínimo próprio): requisitos são DCR, CIMD, PKCE S256 único, `resource`, metadados RFC 9728 e 8414. Consultar a documentação da versão antes de decidir; nenhuma está no repo.

## Critérios de aceitação (rascunho)

1. Claude (conector personalizado) e ChatGPT (servidor MCP próprio) conectam em ambiente de teste com OAuth; token com audiência errada, PKCE sem S256, `redirect_uri` fora da lista e `resource` diferente são recusados.
2. Revogação invalida o acesso em ≤ 1 s; refresh rotativo detecta reuso.
3. Matriz de isolamento entre escritórios sem vazamento (como V-307) incluindo o novo endpoint.
4. Transporte falso do Serpro conta chamadas cobráveis: sem pré-checagem de procuração o teste falha; o teto por escritório para a conversa antes de estourar.
5. `legacy_snapshot --compare` idêntico antes e depois (L4); migrações só adicionam (L1).
6. Repasse: p95 ≤ 5 s com agente real; L3 impossível por esse caminho (teste).
7. Revisão adversarial pelo Codex do OAuth e do repasse (área de risco: auth e dado de cliente).

## Fora de escopo

Escrita, guias, declarações e ciência de intimação (`MSGDETALHAMENTO62` só com clique humano, fora do MCP); portal do cliente final (D-309); túnel do Claude (Enterprise por pedido); parser de PDF antes de haver amostra real; persistir PDF ou XML brutos do Serpro.

## Custo e perguntas abertas

Nada aplicado. Qualquer chamada paga ao Serpro, VM, worker ou deploy exige confirmação com valor (regra de custo). Perguntas à Serpro (relatório, seção 4): armazenamento e retenção, repasse a LLM de terceiros, TTL de cache, reuso de credencial por produto, vigência máxima do Termo de Autorização. Quem contrata: no piloto cada escritório com o próprio e-CNPJ; o contrato do Integra Contador não é público e precisa ser lido.
