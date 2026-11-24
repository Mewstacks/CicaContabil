# Serpro Integra Contador + ERP (Domínio, leitura) num servidor MCP: relatório de pesquisa

> Evidência de pesquisa externa de 20/11/2026 para a [spec do MCP do Domínio](../specs/dominio-mcp.md). Escrita por agente de pesquisa, com nível de confiança por afirmação; antes de virar regra, conferir no banco ou na fonte. Caminhos de scratchpad citados no método não existem mais.

Data da pesquisa: 20/11/2026. Escopo: só pesquisa. Nenhum repositório alterado, nenhum código de produto escrito.

Legenda: **[C]** confirmado em fonte (URL ao lado) · **[I]** inferência minha · **[N]** não achei (a busca feita vem junto).

Método e limites:
- Documentação técnica lida no HTML bruto (curl para diretório novo em `scratchpad/dl/<slug>/`, texto extraído por script). O resumidor do WebFetch errou a contagem do catálogo (disse 87 em produção; o HTML bruto dá 99), por isso os números do catálogo são da minha contagem no HTML.
- `loja.serpro.gov.br` bloqueia WebFetch (HTTP 403) e curl (timeout). Preços e textos da Loja foram lidos no navegador embutido, no DOM da página. Nenhuma página de preço da Loja mostra data.
- Nenhuma instrução encontrada dentro de páginas foi seguida. Nada baixado foi executado. Único PDF baixado: contrato-padrão Serpro (copiado para `scratchpad/dl/contrato_padrao_serpro/`), só lido como texto.
- Nenhuma busca continha dados pessoais ou nome de cliente/empresa.

---

## 0. Resumo executivo: o que muda o desenho

1. **Host da documentação.** `apicenter.serpro.gov.br` não resolve (NXDOMAIN em 20/11/2026). O host real é `apicenter.estaleiro.serpro.gov.br`, o mesmo que a Loja Serpro linka em "Acessar documentação". [C] https://loja.serpro.gov.br/product/integracontador
2. **Catálogo de 15/10/2026: 119 serviços em 28 sistemas; 99 em produção** = 61 Consultar, 23 Emitir, 6 Declarar, 5 Monitorar, 4 Apoiar; 6 em construção, 13 em prospecção, 1 cancelado. [C + contagem minha] https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/catalogo_de_servicos/
3. **"Consultar" não é sinônimo de "sem efeito".** `CAIXAPOSTAL/MSGDETALHAMENTO62` é do tipo Consultar, mas a doc diz que a execução "caracteriza ciência da intimação" (Decreto 70.235/1972). Inversamente, `PGMEI/ATUBENEFICIO23` é do tipo Emitir, mas grava benefício. [C] Um MCP "somente leitura" precisa de allowlist por `idServico`, não por tipo.
4. **Preço**: 3 tabelas (Consulta R$0,24→0,06; Emissão R$0,32→0,08; Declaração R$0,40→0,12), 8 faixas cada, pós-pago, sem mensalidade. Cobram 200, 202 e 403; não cobram 204/304/400/401/404/429/500/503/504 nem nada em `/Apoiar` e `/Monitorar`. [C] "Calculado direto na faixa" implica preço da faixa aplicado ao volume todo do mês (efeito degrau). [I]
5. **Dado estruturado × PDF.** Declaração PGDAS-D, extrato do DAS, DEFIS, SITFIS e declaração completa DCTFWeb voltam como **PDF base64**. JSON só no índice de declarações (com `dasPago` e `malha`), pagamentos, MIT, parcelamentos e procurações; XML na DCTFWeb. Logo "faturamento do ERP × PGDAS-D" exige extração de texto de PDF. [C + I]
6. **Procuração é por cliente e não automatizável.** Autorização de Acesso (gov.br prata/ouro), até 5 anos, validação do outorgado em 30 dias. A IN RFB 2.320/2026, art. 13, proíbe robôs, scripts, automação de navegador e interfaces não oficializadas para outorgar/alterar/revogar autorização; art. 15 deixa a Cogea limitar o nº de autorizações por representante. [C]
7. **Modelo "software house".** Contratante (CNPJ do contrato + e-CNPJ no mTLS) ≠ autor (escritório). O escritório assina um **Termo de Autorização** XMLDSig (e-CPF/e-CNPJ A1 ou A3); o token vale até meia-noite do dia seguinte. Quem opera o MCP precisa ter o certificado do escritório disponível todo dia ou reaproveitar termo com `vigencia` longa. [C + I]
8. **Termos.** O contrato do Integra Contador não é público (fica atrás de login na Área do Cliente). O contrato-padrão de adesão do Serpro (outro produto, 2024) proíbe armazenar/reproduzir os dados obtidos (salvo justificado e informado ao Serpro), usar fora da finalidade e repassar a terceiros. Nada sobre IA/LLM ou cache achado. [C + N] Persistir respostas e mandar a LLM de terceiros são riscos contratuais **em aberto**.
9. **Custo controlável por eventos.** `EVENTOSATUALIZACAO` (Monitorar, gratuito) avisa mudanças de DCTFWeb (E0301), Caixa Postal (E0601) e Pagamentos (E0701): lote de até 1.000 CNPJs, 1.000 req/dia para PF e 1.000 para PJ. Dá para pagar Consulta só quando algo mudou. [C]
10. **MCP/IA pronta para Serpro/Receita: não achei.** Só SDKs do Integra Contador (Dart MIT, Python Apache-2.0) e MCPs genéricos brasileiros (BrasilAPI, fiscal). Serpro diz (fonte secundária, out/2025) que constrói uma camada MCP para suas APIs de IA, sem ligação com Integra Contador. [N + C]

---

## 1. Integra Contador (catálogo, autenticação, limites, preço)

### 1.1 Endpoints e formato [C]
- Fonte: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/integra_contador/ (10/04/2026)
- Base de produção: `https://gateway.apiserpro.serpro.gov.br/integra-contador/v1/{Apoiar|Consultar|Declarar|Emitir|Monitorar}`. POST, JSON, UTF-8, camelCase; o campo `dados` é string JSON escapada.
- Demonstração (trial): `https://gateway.apiserpro.serpro.gov.br/integra-contador-trial/v1/Consultar` (exemplo na doc do e-Processo, 09/11/2026: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-e-processo/eprocesso/). No trial os headers `jwt_token` e `autenticar_procurador_token` ficam vazios. Dados são mock: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/como_usar_a_demonstracao_da_api/
- Corpo obrigatório: `contratante{numero,tipo=2}`, `autorPedidoDados{numero,tipo 1|2}`, `contribuinte{numero,tipo 1|2; 3|4 = lista PF|PJ}`, `pedidoDados{idSistema,idServico,versaoSistema,dados}`.
- CNPJ alfanumérico (novas inscrições a partir de jul/2026) é aceito; `numero` deve ser string `[A-Z0-9]`: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/faq/ (25/05/2026)
- Definição oficial dos caminhos:
  - Apoiar: "serviços auxiliares ou de suporte".
  - Consultar: "serviços do tipo consulta".
  - Declarar: "serviços de entrega ou transmissão de declaração".
  - Emitir: serviços de "comprovantes, relatórios, guia de recolhimento ou documento de arrecadação".
  - Monitorar: "serviços de monitoração".
- Timeout síncrono máximo 30 s (limite do gateway). Timeout por complexidade: baixa 3-8 s, média 10-20 s, alta 20-28 s. 504 não é cobrado, mas "Pode haver persistência tardia de dados na RFB": não reenviar Declarar/Emitir sem consultar o estado. Excesso de timeout pode suspender o endpoint (`SUSPENDED`, circuit breaker): https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/timeout/ (08/09/2026)
- Cabeçalho opcional `X-Request-Tag` (até 32 caracteres) aparece no relatório de consumo CSV (colunas DATA, CNPJ/CPF, URL, RESPONSE_CODE, IP, OBSERVAÇÃO, TAG, QUANTIDADE): https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/identificador_requisicoes/ (10/04/2026). O relatório sai pela Área do Cliente > Consumo e chega por e-mail ao Representante Legal/Financeiro, link válido 3 dias: https://centraldeajuda.serpro.gov.br/duvidas/pt/area-do-cliente/consumo/ (17/03/2026)

### 1.2 Catálogo atual (2026) por sistema [C]
Fonte única: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/catalogo_de_servicos/ (rodapé 15/10/2026). A coluna "Tipo" é a oficial; "Retorno" vem das páginas de cada serviço; "Procuração" vem de https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/servicos_vs_procuracoes/ (01/06/2026).

| Sistema | Em produção (idServico) | Retorno confirmado | Procuração e-CAC (cód.) |
|---|---|---|---|
| PGDASD | Consultar: CONSDECLARACAO13, CONSULTIMADECREC14, CONSDECREC15, CONSEXTRATO16. Emitir: GERARDAS12, GERARDASCOBRANCA17, GERARDASPROCESSO18, GERARDASAVULSO19. Declarar: TRANSDECLARACAO11 | 13 = JSON (índice: operações, nº declaração, data/hora, malha, nº DAS, data emissão do DAS, `dasPago`). 14/15 = JSON com PDFs base64 (recibo, declaração, MAED). 16 = PDF. GERARDAS = PDF + JSON de detalhamento | 00146 |
| REGIMEAPURACAO | Consultar: 102, 103, 104. Declarar: EFETUAROPCAOREGIME101 | n/c | 00060 |
| DEFIS | Consultar: CONSDECLARACAO142, CONSULTIMADECREC143, CONSDECREC144. Declarar: TRANSDECLARACAO141 | PDF (recibo/declaração) | 00146 |
| PGMEI | Consultar: DIVIDAATIVA24. Emitir: GERARDASPDF21, GERARDASCODBARRA22, **ATUBENEFICIO23 (grava)** | n/c | n/a |
| CCMEI | Consultar: DADOSCCMEI122, CCMEISITCADASTRAL123. Emitir: EMITIRCCMEI121 | 121 = PDF | n/a |
| DCTFWEB | Consultar: CONSRECIBO32, CONSDECCOMPLETA33, CONSXMLDECLARACAO38. Emitir: GERARGUIA31, GERARGUIAANDAMENTO313. Declarar: TRANSDECLARACAO310 | 33 = PDF base64. 38 = XML base64 (se a declaração está EM ANDAMENTO, gera a minuta para assinar) | 00103 |
| MIT | Consultar: CONSAPURACAO316, LISTAAPURACOES317. Apoiar: SITUACAOENC315. Declarar: ENCAPURACAO314 | 316 = JSON | não consta na tabela [N] |
| PROCURACOES | Consultar: OBTERPROCURACAO41 | JSON (`dtexpiracao`, `nrsistemas`, `sistemas`) | n/a |
| SICALC | Consultar: CONSOLIDAR54. Apoiar: CONSULTAAPOIORECEITAS52. Emitir: CONSOLIDARGERARDARF51, GERARDARFCODBARRA53 | n/c | n/a |
| CAIXAPOSTAL | Consultar: MSGCONTRIBUINTE61, **MSGDETALHAMENTO62 (ciência)**. Monitorar: INNOVAMSG63 | 61 = JSON só de metadados, 50/página, sem corpo | 00006 |
| DTE | Consultar: CONSULTASITUACAODTE111 | n/c | 00050 |
| PAGTOWEB | Consultar: PAGAMENTOS71, CONTACONSDOCARRPG73. Emitir: COMPARRECADACAO72 | 71 = JSON (documento, tipo DARF/DAS/DAE/DJE, PA, arrecadação, receita, valores, saldos, desmembramentos; página ≤100) | 00004 |
| AUTENTICAPROCURADOR | Apoiar: ENVIOXMLASSINADO81 (EXPIRARAUTORIZACAO82 cancelado em 01/04/2024) | token | n/a |
| EVENTOSATUALIZACAO | Monitorar: SOLICEVENTOSPF131, SOLICEVENTOSPJ132, OBTEREVENTOSPF133, OBTEREVENTOSPJ134 | datas de último evento | procuração do sistema monitorado |
| SITFIS | Apoiar: SOLICITARPROTOCOLO91. Emitir: RELATORIOSITFIS92 | 92 = PDF base64 | 00002 |
| PARCSN, PARCSN-ESP, PERTSN, RELPSN, PARCMEI, PARCMEI-ESP, PERTMEI, RELPMEI | cada um: 4 Consultar (PARCELASPARAGERAR, PEDIDOSPARC, OBTERPARC, DETPAGTOPARC) + 1 Emitir (GERARDAS) | n/c | 00076/00188; 00125; 00149/10011; 00210/10036; 00134; 00133; 00152/10012; 00209/10035 |
| PNRCONTADOR | Consultar: CONSVINCULOS261, CONSRENUNCIA263, SITSOLICRENUNCIA265. Emitir: COMPRENUNCIA264. Declarar: SOLICRENUNCIA262 | n/c | n/a |
| EPROCESSO | Consultar: CONSPROCPORINTER271 | JSON paginado | 00051 |

Fora de produção: DASNSIMEI 151-153 (em construção, sem data); EPROCESSO 272, 273, 274 (catálogo de 15/10/2026: em construção; o changelog 1.1.0 de 09/11/2026 os lista como "Adicionado" e as páginas 273/274 trazem "A FUNCIONALIDADE AINDA NÃO ESTÁ DISPONÍVEL PARA CONTRATAÇÃO"; 274 = comunicados e intimações): https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-e-processo/eprocesso/changelog/ ; DCTFWEB 34, 35, 36, 37, 39, 311, 312 (prospecção); PARC-PAEX e PARC-SIPADE (prospecção). Não há "REGULARIZE" no catálogo [N: li as 119 linhas]; Regularize é portal da PGFN, não API do Integra Contador (https://www.serpro.gov.br/menu/noticias/noticias-2026/novo-acesso-portal-regularize, não aberta, só título no buscador).

### 1.3 Classificação pedida: consulta × emissão × declaração

| Classe | Serviços (em produção) | Altera algo na RFB? |
|---|---|---|
| **A. Leitura pura** | 60 Consultar (todos os 61, menos MSGDETALHAMENTO62) + 5 Monitorar + 3 Apoiar de leitura (SITFIS 91, MIT 315, SICALC 52) | Não. Observações abaixo |
| **B. Leitura com efeito jurídico** | CAIXAPOSTAL MSGDETALHAMENTO62 (futuros: EPROCESSO 274, a confirmar) | **Sim: registra ciência da intimação** (e-Processo 273/274, ainda indisponíveis: a doc fala em "ciências" e em "ciência que impede o download"; reavaliar quando liberar) |
| **C. Emissão de documento sem mudar situação** | SITFIS RELATORIOSITFIS92, PAGTOWEB COMPARRECADACAO72, CCMEI EMITIRCCMEI121, PNR COMPRENUNCIA264 | Na prática não [I]; cobradas como Emissão |
| **D. Emissão de guia** (18) | PGDASD 12, 17, 18, 19; PGMEI 21, 22; DCTFWEB 31, 313; SICALC 51, 53; GERARDAS dos 8 parcelamentos | Não muda débito nem declaração. PGDAS-D registra "Geração de DAS" no histórico do PA (aparece no índice CONSDECLARACAO13) [C]; nos demais, registro de emissão não documentado [N] |
| **E. Emitir que grava** | PGMEI ATUBENEFICIO23 ("registrar benefício"); prospecção: DCTFWEB 39 (aplicar vinculação), 312 (editar valor suspenso) | **Sim** |
| **F. Declarar/transmitir** (6) | PGDASD 11, DEFIS 141, DCTFWEB 310, MIT ENCAPURACAO314, REGIMEAPURACAO EFETUAROPCAOREGIME101, PNR SOLICRENUNCIA262 | **Sim: altera situação fiscal**, em geral difícil de desfazer |
| **G. Apoio/auth** | AUTENTICAPROCURADOR ENVIOXMLASSINADO81 | Só cria token de sessão |

Observações da classe A:
- CAIXAPOSTAL INNOVAMSG63 virou Monitorar em 16/01/2023 (changelog) e a lista MSGCONTRIBUINTE61 só devolve metadados (assunto, datas, `indicadorLeitura`, `dataCiencia`, relevância, `isn`). Não há texto dizendo que listar registra leitura [C; deduzo que não registra: I].
- DCTFWEB CONSXMLDECLARACAO38 gera "minuta" (rascunho) de declaração EM ANDAMENTO; não transmite. [C]
- Idempotência de leitura não é garantida em 202/504 (SITFIS usa 202/204 com `tempoEspera`).

Fontes: ciência: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-caixapostal/caixapostal/servicos/obter_detalhes_de_uma_mensagem_especifica/ (31/08/2026) · lista: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-caixapostal/caixapostal/servicos/obter_lista_de_mensagens_por_contribuintes/ (19/09/2026) · benefício: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-mei/pgmei/servicos/atualizar_beneficio/ (25/06/2026) · índice PGDAS-D: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-sn/pgdasd/servicos/consultar_declaracao_por_ano_pa/ (10/04/2026) · changelog Caixa Postal: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-caixapostal/caixapostal/changelog/ (19/10/2026).

Divergência a verificar na primeira fatura: a Loja lista "Caixa Postal - Obter Indicador de novas mensagens" em "Consulta dados" e "SITFIS - Solicitar relatório" em "Emissão de documentos", mas a doc diz que `/Apoiar` e `/Monitorar` não são bilhetados. Conferir no CSV de consumo (coluna URL).

### 1.4 Autenticação [C]
Fonte: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/quick_start/ (10/04/2026) e FAQ (25/05/2026).
1. **Credencial**: Consumer Key + Consumer Secret da Área do Cliente (https://cliente.serpro.gov.br), que identificam o contrato.
2. **Token**: POST `https://autenticacao.sapi.serpro.gov.br/authenticate` com `Authorization: Basic base64(key:secret)`, `Role-Type: TERCEIROS`, `grant_type=client_credentials`, **mTLS com o e-CNPJ ICP-Brasil (.p12/.pfx) do contratante, o mesmo da contratação**. Retorna `access_token` + `jwt_token` + `expires_in` (exemplo da doc: 2008 s). 401 = renovar.
3. **Chamada**: `Authorization: Bearer` + header `jwt_token` + (quando autor ≠ contratante) `autenticar_procurador_token`.
4. Contratante só aceita CNPJ; divergência entre o NI da requisição e o do certificado dá 403 `[AcessoNegado-ICGERENCIADOR-016]`.
5. **Termo de Autorização** (AUTENTICAPROCURADOR/ENVIOXMLASSINADO81): XML `termoDeAutorizacao` com `dataAssinatura`, `vigencia` (AAAAMMDD, sem teto máximo documentado [N]), `destinatario` (contratante), `assinadoPor` (autor). XMLDSig; certificado e-CPF/e-CNPJ série A (A1 ou A3; série S rejeitada), cadeia ICP-Brasil e LCR validadas, não expirado "na data da verificação". Resposta: `autenticar_procurador_token` (36 bytes), "válido até a meia-noite do dia seguinte" (Brasília); reenviar o mesmo termo válido devolve 304 (cache). Fontes: .../autenticaprocurador/ , .../cache/ , .../padroes_tecnicos_assinatura_xml/ (25/02 e 10/04/2026).
6. **Procuração/autorização no e-CAC** (cliente → escritório) é outra camada: o gerenciador consulta o sistema de procurações a cada requisição e devolve 403 `[AcessoNegado-ICGERENCIADOR-022]` se o autor não a tem (https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/mensagens/, 08/09/2026). Quando `autorPedidoDados` = `contribuinte`, o barramento trata como titular (doc do e-Processo).
7. Modelo "software house" descrito pela própria Serpro: quem contratou e não tem procuração do contribuinte envia o Termo assinado pelo procurador (https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/, 25/02/2026). A Loja diz o mesmo ("Termo de Autorização" assinado pelo certificado do procurador).
8. **Regras da procuração (Autorização de Acesso)** — IN RFB 2.320/2026 (texto oficial: https://normasinternet2.receita.fazenda.gov.br/#/consulta/externa/150461; DOU 09/04/2026, seção 1, p. 56):
   - art. 6º parágrafo único: tem "os mesmos efeitos de uma procuração" para serviços digitais;
   - art. 7º §1º: serviços fixados "com exatidão"; permite "atos de ciência", confissões, recursos; prazo "no máximo cinco anos"; concedida pelo titular na internet e **validada pelo outorgado em 30 dias** (§2º), senão cancela;
   - art. 12: emitida e cancelada "exclusivamente pela internet";
   - art. 13: veda sistema que "possibilite outorga, alteração ou revogação" por automação; §1º: robôs de software, scripts, automação de navegador e "interfaces de programação não oficializadas pela" RFB; §2º: RFB pode interromper sessão, bloquear o representante e cancelar autorizações;
   - art. 15: a Cogea pode fixar nº máximo de autorizações ativas por representante (valor não achado [N]: busca "Cogea limite autorizações representante digital 2026");
   - art. 11/14: bloqueio por situação cadastral irregular do CNPJ/CPF.
   - Guia do usuário (v1.0, Cogea): "antiga Procuração Digital"; só vale após confirmação da pessoa autorizada; gov.br nível prata/ouro para validar; "Todos" inclui serviços futuros; cancelável por qualquer parte: https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/passo-a-passo/autorizacoes-de-acesso-guia-do-usuario
   - Não achei como um **outorgado pessoa jurídica** (escritório com e-CNPJ) valida no sistema novo [N]: o guia mostra só o caminho por conta gov.br.

### 1.5 Limites de taxa e de uso [C]
- **Limite global de requisições/s do Integra Contador: não achei** [N: varri as páginas baixadas por "rate limit", "429", "limite de requisição", "TPS"]. O código 429 existe: "Alguns serviços podem ter esse controle" (https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/codigos_retorno/, 08/09/2026).
- EVENTOSATUALIZACAO: 1.000 req/dia para PF e 1.000 para PJ; até 1.000 contribuintes por requisição; resultado com TTL padrão de 20 min e entrega única ("pega e apaga"); evento fica no máximo 60 dias; sincronização média de 15 min; exige procuração para cada contribuinte vigente até D-1; 429 `[Aviso-EVENTOSATUALIZACAO-004]`: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-contador-gerenciador/eventosatualizacao/limites/ (25/02/2026)
- PNRCONTADOR: página de até 50 registros, até 200 requisições simultâneas.
- CAIXAPOSTAL: 50 mensagens por página; PAGTOWEB: página ≤100.
- SITFIS: protocolo válido só na data da solicitação; respeitar `tempoEspera`; 204 = ainda processando (não cobrado); 202 = pediu cedo demais (cobrado, ver 1.6): https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-sitfis/sitfis/tempo_espera/
- e-Processo exige `contratante.enderecoIp` (IP de origem). Implica IP de saída controlado [C: só nesta doc].

### 1.6 Preço e contratação

**Tabela oficial** (Loja Serpro, aba Preço, lida em 20/11/2026; a página não mostra data de vigência). Texto da página: "Você paga apenas pelo que consumir, o pagamento é calculado direto na faixa do consumo." Fonte: https://loja.serpro.gov.br/product/integracontador

| Faixa | Consulta (chamadas) | R$ | Emissão (chamadas) | R$ | Declaração (chamadas) | R$ |
|---|---|---|---|---|---|---|
| 1 | 1 a 300 | 0,24 | 1 a 500 | 0,32 | 1 a 100 | 0,40 |
| 2 | 301 a 1.000 | 0,21 | 501 a 5.000 | 0,29 | 101 a 500 | 0,36 |
| 3 | 1.001 a 3.000 | 0,18 | 5.001 a 10.000 | 0,26 | 501 a 1.000 | 0,32 |
| 4 | 3.001 a 7.000 | 0,16 | 10.001 a 15.000 | 0,22 | 1.001 a 3.000 | 0,28 |
| 5 | 7.001 a 15.000 | 0,14 | 15.001 a 25.000 | 0,19 | 3.001 a 5.000 | 0,24 |
| 6 | 15.001 a 23.000 | 0,11 | 25.001 a 35.000 | 0,16 | 5.001 a 8.000 | 0,20 |
| 7 | 23.001 a 30.000 | 0,09 | 35.001 a 50.000 | 0,12 | 8.001 a 10.000 | 0,16 |
| 8 | acima de 30.000 | 0,06 | acima de 50.000 | 0,08 | acima de 10.000 | 0,12 |

Consistência de data: os valores batem com os "aproximados da 3ª faixa" que a Omie cita para 04/2026 (DCTFWeb R$1,12 = 3 consultas + 1 declaração + 1 emissão; PGDAS R$0,76; PGMEI R$0,26; SICALC R$0,52: https://ajuda.omie.com.br/pt-BR/articles/9750205) e com o exemplo de faixa 1 da Domínio (R$0,40 + 0,32 + 0,24 = R$0,96, sem data: https://suporte.dominioatendimento.com/central/faces/solucao-onvio.html?codigo=10776). Logo a tabela estava igual em abril/2026 e continua igual em 20/11/2026 [I]. A "Nova política de preços 2024" (IPCA 4,62% em 21/06/2024) **não lista o Integra Contador** entre os serviços reajustados: https://centraldeajuda.serpro.gov.br/duvidas/pt/avisos/avisonovapoliticapreco2024/

**Regras de cobrança** [C]
- Cobradas: respostas 200, 202 e 403. Não cobradas: 204, 304, 400, 401, 404, 429, 500, 503, 504 e tudo em `/Apoiar` e `/Monitorar`. Fontes: FAQ (25/05/2026) https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/faq/ ("Todas as solicitações com o código de retorno 200, 202 e 403 são cobradas") e https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/codigos_retorno/ (08/09/2026: "Os serviços acionados pelo caminho /Apoiar ou /Monitorar não são bilhetados."). Eventos de Última Atualização "gratuita": https://centraldeajuda.serpro.gov.br/duvidas/pt/avisos/integracontadoreventosatualizacao/ (17/04/2024).
- Consequência: **403 por falta de procuração é cobrado**; **202 do SITFIS por pedir antes do `tempoEspera` é cobrado**.
- A Loja agrupa as funcionalidades em "Consulta dados", "Emissão de documentos" e "Geração de declarações" (as três tabelas). Itens que existem no catálogo mas não aparecem na lista da Loja: REGIMEAPURACAO (4), DEFIS (consultas 142-144), MIT ENCAPURACAO314 e SITUACAOENC315, PGDASD 17/18/19, PAGTOWEB PAGAMENTOS71 [I: a lista da Loja parece desatualizada; confirmar a categoria de cobrança dessas no consumo real].
- **Modelo "direto na faixa"** [I, forte]: a página da Consulta NF-e diz "Multiplique então o número de consultas pelo valor unitário da respectiva faixa" (https://loja.serpro.gov.br/consulta-nf-e/product/consultanfe) e a da Consulta CND diz "mensalmente apura-se o volume de consultas para determinar a faixa de preço" (https://loja.serpro.gov.br/consulta-cnd/product/consultacnd). Para o Integra Contador a página só diz "calculado direto na faixa do consumo". Se for igual, o volume mensal de cada categoria define **um** preço unitário para todas as chamadas da categoria. Efeito degrau: 300 consultas = R$72,00; 301 consultas = R$63,21. Confirmar no contrato.
- Pós-pago, sem taxa de instalação, "Cancele a qualquer momento, sem taxas ou multas" (https://loja.serpro.gov.br/product/integracontador, aba Características); cancelamento "por simples manifestação de vontade" pela Central de Ajuda (https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/como_contratar/). Reajuste: não achei regra específica do Integra Contador [N]; o contrato-padrão prevê IPCA (seção 4).
- Contratação: botão "Quero contratar", conta Serpro, **e-CNPJ**, assina o contrato online; "em até 10 minutos" tem chaves na Área do Cliente (https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/como_contratar/, 25/02/2026). Cada contrato é de um CNPJ (as credenciais valem só com o e-CNPJ do contratante: FAQ erro 016; Omie, fonte secundária, diz o mesmo: https://ajuda.omie.com.br/pt-BR/articles/9749470-como-contratar-o-integra-contador).
- **Contratação por entidade de classe** (sindicato contábil etc.): cobrança individual, mas a faixa considera o consumo somado dos associados: "Quanto maior o uso, menor o preço do acesso" (https://loja.serpro.gov.br/entidades-representativas/, que lista vários SESCON/sindicatos de empresas contábeis). Serpro e Sescon-PA fecharam contrato para Integra Contador com "condições diferenciadas" (06/10/2025, https://www.serpro.gov.br/menu/noticias/noticias-2025/sescon-pa-contrata-integra-contador). Em 24/09/2026 a Serpro divulgou o modelo geral (https://www.serpro.gov.br/menu/noticias/noticias-2026/contratacao-entidades-representativas), sem citar Integra Contador. Não achei a tabela de faixas desses contratos [N].

**Ordem de grandeza por cliente/mês** (conta minha, premissas: 3 Consultas + 1 Emissão SITFIS por cliente; preço da faixa aplicado ao volume mensal total da categoria; SITFIS solicitar = Apoiar não cobrado): 100 clientes = 300 Consultas (R$0,24) + 100 Emissões (R$0,32) = R$104/mês (R$1,04 por cliente); 500 = R$430 (R$0,86); 1.000 = R$830 (R$0,83); 2.000 = R$1.540 (R$0,77). Declarar/Emitir guias ficam fora do MCP somente-leitura.

### 1.7 Novidades 2025-2026 [C]
- 28/03/2025: MIT (encerrar, situação, consultar apuração, listar) + DCTFWEB GERARGUIAANDAMENTO313 (https://serpro.gov.br/menu/noticias/noticias-2025/integra-contador-novas-funcionalidades, 09/04/2025).
- 10/11/2025: EPROCESSO CONSPROCPORINTER271. 02/12/2025: PNRCONTADOR (5 serviços). 09/11/2026: changelog do e-Processo documenta 272/273/274 (ainda "não disponível para contratação").
- Changelogs sem mudança de serviço em 2026 para PGDASD, DEFIS, PGMEI, CCMEI, DTE, PAGTOWEB, REGIMEAPURACAO, PARCSN (versão 1.0.0 só; os outros 7 parcelamentos não conferi), SITFIS (último 2.0.0 em 01/04/2024), PROCURACOES (1.0.1, 06/05/2025, tipos de dados), DCTFWEB (1.3.0 em 01/09/2025: filtro opcional por sistema de origem das receitas) e MIT (1.0.0 em 28/03/2025). Em 2026 só: EVENTOSATUALIZACAO 1.0.1 (25/02/2026: TTL do resultado de 5 para 20 min, estimativa EMA/P90, status 202 "em processamento"); PGDASD (changelog de 03/11/2026): o campo `folhasSalario` passa a ser obrigatório na transmissão para PA posterior a 10/2026 (afeta TRANSDECLARACAO11, não leituras). Fontes: `.../pt/solucoes/<sistema>/changelog/` de cada solução.
- 2026: SICALC CONSOLIDAR54 ("consolida o débito com acréscimos legais, mas sem emitir o DARF"): changelog 10/02/2026 e catálogo "produção 15/10/2026"; DTE obrigatório para todas as PJ desde jan/2026 (https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2026/janeiro/atencao-pessoas-juridicas); política de timeout (08/09/2026); `indicadorPagina` do Caixa Postal passa a Number(24) em 05/09/2026.
- **Planejados para 31/10/2026** (changelog do Caixa Postal, 19/10/2026): QTQMSG64 (quantidades de mensagens lidas/não lidas/novas/favoritas/relevantes), ANEXOSMSG65 (lista anexos; só para mensagem com ciência registrada) e URLANEXOMSG66 (URL temporária de 5 min). **Não constam no catálogo de 15/10/2026 e não verifiquei se entraram.** Reabrir o catálogo antes de desenhar tools.
- Segundo a Receita, a página de lançamento foi atualizada em 06/11/2026 e cita 24 APIs em 7 grupos no lançamento (2022): https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2022/setembro/receita-federal-e-serpro-disponibilizam-nova-plataforma-de-prestacao-de-servicos-contabeis-e-fiscais

---

## 2. Outras APIs Serpro úteis a escritório contábil

Preços lidos na Loja em 20/11/2026 (sem data de vigência nas páginas). Contratação por e-CNPJ; as páginas de NF-e, Integra Contador e Dívida Ativa declaram modelo pós-pago e todas descrevem cobrança "faixa do volume mensal × preço unitário". **Autenticação** confirmada para Consulta CNPJ e Consulta NF-e (CPF e CND por analogia [I]): OAuth2 `client_credentials` com Consumer Key/Secret em `https://gateway.apiserpro.serpro.gov.br/token` (Bearer de 1 h na doc do CNPJ), sem mTLS (https://apicenter.estaleiro.serpro.gov.br/documentacao/consulta-cnpj/pt/quick_start/ e .../consulta-nfe/pt/quick_start/). Só o Integra Contador exige mTLS com e-CNPJ.

| API | Entrega | Preço (1ª faixa → última) | Relevância para escritório |
|---|---|---|---|
| **Consulta CNPJ** https://loja.serpro.gov.br/consulta-cnpj/product/consultacnpj | Básica (situação cadastral, data e motivo, CNAE, endereço, porte, natureza), QSA (+ sócios, opção Simples/MEI, data de exclusão do Simples), Empresa (+ CPF/CNPJ dos sócios) | 1-999: R$0,6591 / 0,8683 / 1,1717; 1.000-9.999: 0,5649 / 0,7428 / 1,0148; 10.000-49.999: 0,3557 / 0,5963 / 0,8265; ... ≥30M: 0,025 / 0,067 / 0,108 (16 faixas) | **Alta**: cadastro de fornecedor/cliente. Opção gratuita, com defasagem: dados abertos do CNPJ da RFB (pastas mensais `dados_abertos_cnpj/AAAA-MM`, arquivos Empresas, Estabelecimentos, Socios, Simples, Cnaes) [C: https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/2025-08/ ; a periodicidade difere entre fontes: mensal no dados.gov.br, trimestral numa página antiga da Receita: https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj] |
| **Consulta NF-e** https://loja.serpro.gov.br/consulta-nf-e/product/consultanfe | Por chave de acesso, só NF-e modelo 55 ("A API retorna somente nota fiscal modelo 55"), JSON/XML no leiaute ENCAT, **somente os campos autorizados pela anuência**, eventos (cancelamento, CC-e, manifestação etc.), Push NF-e (monitorar chave 30 dias, mesmo preço da consulta) | 1-999: R$0,6591; 1.000-9.999: 0,5649; 10.000-49.999: 0,3557; ...; >30M: 0,0270 (16 faixas). Não bilhetados: 400, 401, 403, 404, 406, 408, 500, 504 (o único sucesso listado é 200); Push cobra por nota monitorada | **Média-alta**, mas cara em escala (ver 3.3). Doc: https://apicenter.estaleiro.serpro.gov.br/documentacao/consulta-nfe/pt/faq/ |
| **Consulta CND** https://loja.serpro.gov.br/consulta-cnd/product/consultacnd | Certidão conjunta RFB/PGFN (PJ, PF, imóvel rural): PDF, código de controle, tipo (Negativa/Positiva com efeitos), validade | 1-5.000: R$0,8788; 5.001-10.000: 0,8265; ... >10M: 0,2511 (13 faixas); sem franquia. A própria página tem um link "clique aqui" para a consulta gratuita de certidão (destino não aberto) | **Média**: monitorar validade de certidão de clientes |
| **Consulta CPF** https://loja.serpro.gov.br/consulta-cpf/product/consultacpf | CPF + data de nascimento → situação cadastral, nome, inscrição, nome social | 1-999: R$0,6591 ... >30M: 0,017 | Baixa (conferência de sócio/funcionário) |
| **Datavalid** https://loja.serpro.gov.br/product/datavalid | Validação cadastral/biométrica (7 tipos) | Faixa 1 (1-999): R$0,80 (cadastral simples) a R$3,50 (completa); faixa 10 (>4M): R$0,51 a R$2,71; preços para ente privado | Baixa (onboarding/KYC) |
| **Consulta Dívida Ativa (PGFN)** https://loja.serpro.gov.br/product/consulta-divida-ativa | Dívida tributária não previdenciária: nº do processo, data de inscrição, situação, valor inscrito, órgão de origem | R$0,6591 (≤999) ... R$0,0314 (>10M), 12 faixas | Média-baixa (o SITFIS já traz pendências PGFN) |
| **Consulta Faturamento** https://loja.serpro.gov.br/product/consultafaturamento | Faturamento empresarial declarado à RFB, **mediante autorização do titular** (Compartilha Receita/e-CAC, token); resposta criptografada com a chave pública do e-CNPJ do contratante | R$0,00 (1-5); R$3,6617 (6-25.000) ... R$2,7410 (>200.000) | Baixa: o fluxograma é desenhado para instituição financeira e diz "somente com instituições financeiras contratantes" [I: escritório provavelmente inelegível; confirmar] |
| **Consulta Renda / Restituição IRPF** https://loja.serpro.gov.br/product/ConsultaRestituicao | IRPF da pessoa física com autorização do titular (Compartilha Receita) | Restituição: R$0,00 (1-5); R$1,5693 (6-80.000) ... R$1,4228 (>240.000) | Baixa (PF; fluxo de crédito) |
| **Radar** https://loja.serpro.gov.br/product/radar | Sistema de **gestão de multas de trânsito** (Senatran) | n/a | **Irrelevante** (não é o Radar de comércio exterior; para comércio exterior o produto é Integra Comex) |

Outras na Loja sem relevância direta: Integra Comex, Consulta DU-E, CCIR, AntecipaGov, Cartório Data, GovData (lista em https://loja.serpro.gov.br/home).

Alternativa gratuita para chave de NF-e, fora do Serpro [C: manual de orientação do contribuinte hospedado pela SEFAZ-PR, http://moc.sped.fazenda.pr.gov.br/NFe_NFCe/NFeDistribuicaoDFe.html]: `NFeDistribuicaoDFe` serve atores da NF-e (PJ ou PF) com certificado válido; "o CNPJ base consultado seja o mesmo do certificado digital" (senão rejeição 593); consulta por chave só alcança documentos recebidos pelo Ambiente Nacional "nos últimos 90 dias"; repetir busca de registros já entregues gera rejeição 656 "Consumo Indevido" e, sem documentos novos, é preciso esperar pelo menos uma hora. Lotes de até 50 documentos em gzip. **O destinatário só recebe o XML completo depois de manifestar a operação** (ciência, operação não realizada ou confirmação; manifestação é um evento, portanto não é leitura pura); antes disso recebe só o resumo (`resNFe`/`resEvento`). Exige o certificado do CNPJ consultado, ou seja, o do cliente, não o do escritório [I].

---

## 3. Padrão de arquitetura: ERP (Domínio, ODBC somente leitura) + Serpro

### 3.1 Desenho recomendado [I, apoiado nos fatos da seção 1]
1. **Camada ERP (leitura)**: usuário ODBC só com SELECT, views materializadas por competência/CNPJ (faturamento, guias emitidas/pagas, fornecedores, chaves de NF-e, folha apurada). Nada do Serpro volta ao ERP.
2. **Adaptador Serpro com allowlist por `idServico`** (apêndice A) aplicada no código do adaptador, não no prompt. `Emitir`/`Declarar` e MSGDETALHAMENTO62 ficam fora do processo do MCP (ou em processo separado com confirmação humana).
3. **Registro de procurações por cliente**: tabela com `dtexpiracao` vinda de OBTERPROCURACAO41, sistemas autorizados e último 403. Avisar vencimento antes (≤5 anos). Pré-checar antes de gastar chamada (403 é cobrado).
4. **Governador de custo**: contador por categoria e por tenant (usar `X-Request-Tag`), teto mensal, aviso perto das viradas de faixa, nunca deixar a LLM chamar em laço. Preferir `EVENTOSATUALIZACAO` (grátis) para decidir **se** vale consultar.
5. **Snapshots com proveniência**: guardar resposta bruta (JSON/XML/PDF) + `idSistema/idServico/versão/data-hora/X-Request-Tag/status` num armazenamento cifrado e separado, com retenção mínima (ver 3.4/4). Conferir com Serpro antes de reter além da sessão.
6. **Parsers determinísticos** para PDF/XML (SITFIS, PGDAS-D, DCTFWeb) e **motor de cruzamento determinístico** (SQL/Python) que gera "achados" estruturados. A LLM só explica e prioriza achados, citando o id do snapshot; não calcula imposto nem lê PDF cru por padrão.
7. **Segredos**: e-CNPJ A1 (mTLS) do contratante e, se for o caso, certificados dos escritórios para assinar o Termo, em cofre/HSM, nunca no contexto da LLM nem em log.
8. **Reuso de credencial**: se o escritório já contratou o Integra Contador para o Domínio (a Domínio informa que os custos são pagos direto à Serpro, sem valor adicional dela), usar as mesmas credenciais mistura o consumo; separar por `X-Request-Tag` ou contratar outra chave. O contrato precisa permitir [N].

### 3.2 Cruzamentos de alto valor: viabilidade (só leitura × exige emitir/declarar)

| # | Cruzamento | Serviços Serpro (todos de leitura) | Formato | Só leitura? | Custo típico por cliente/mês (faixa 1) | Procuração | Notas e riscos |
|---|---|---|---|---|---|---|---|
| 1 | **Faturamento do ERP × PGDAS-D/DEFIS** | CONSDECLARACAO13 (índice: nº, data/hora, malha, DAS, `dasPago`) + CONSULTIMADECREC14 ou CONSDECREC15 (PDF da declaração) ; DEFIS 142/143/144 | JSON + **PDF** | **Sim** | 2 Consultas ≈ R$0,48 | 00146 | Receita bruta só no PDF: precisa extrair texto do PDF da RFB (layout não documentado como contrato estável [I]). Só PJ (tipo 2). O índice sozinho já entrega: declarou? retificou? DAS emitido? **pago?** em malha? |
| 2 | **Débitos do SITFIS × guias pagas** | SITFIS 91 (Apoiar, não cobrado) + 92 (Emissão) ; PAGAMENTOS71, CONTACONSDOCARRPG73 ; PARC* consultas ; CONSOLIDAR54 (valor atualizado sem emitir DARF) | **PDF** (SITFIS) + JSON (pagamentos, parcelamentos) | **Sim** | 1 Emissão + 2-3 Consultas ≈ R$0,80-1,04 | 00002, 00004, parcelamentos | SITFIS só vem em PDF: usar como "há pendência?" e parsear; a prova do pagamento sai do JSON do PAGTOWEB. Respeitar `tempoEspera` (202 é cobrado). Evento E0701 avisa pagamento novo. |
| 3 | **Mensagens do e-CAC/DTE × obrigações** | INNOVAMSG63 (grátis) ; MSGCONTRIBUINTE61 (metadados) ; CONSULTASITUACAODTE111 ; evento E0601 | JSON | **Sim, só até os metadados.** Ler o corpo (MSGDETALHAMENTO62) **registra ciência** | ≈ R$0,24-0,48 | 00006, 00050 | DTE é obrigatório para toda PJ desde jan/2026 e as comunicações têm "validade jurídica plena"; não acessar no prazo legal gera ciência tácita (https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2026/janeiro/atencao-pessoas-juridicas). Para o MCP, classificar por assunto/relevância/`dataCiencia` e exigir clique humano com aviso legal para abrir o corpo. |
| 4 | **Situação cadastral de fornecedores × notas de entrada** | Consulta CNPJ (Básica/QSA) ; opcional CCMEISITCADASTRAL123 (MEI por CPF) | JSON | **Sim** | R$0,66-0,87 por CNPJ distinto (faixa ≤999) | **Não** (dado público) | Traz "data da situação cadastral" e motivo: dá para marcar nota emitida após baixa/inaptidão. Reduzir custo com a base aberta mensal da RFB e cache por CNPJ (ver 4: cache). |
| 5 | **Chave NF-e das notas escrituradas × NF-e autorizada** | Serpro Consulta NF-e (por chave) **ou** NFeDistribuicaoDFe (SEFAZ, grátis, com certificado do cliente) | JSON/XML | **Sim** com Serpro. Com DFe, o XML completo exige manifestar a operação (evento) | Serpro: R$0,66 por chave (faixa ≤999) | **Não** (Serpro) | Só modelo 55; campos restritos pela anuência. Exemplo meu: 100 clientes × 400 notas = 40.000 chaves/mês ≈ faixa R$0,3557 ≈ R$14,2 mil/mês. Preferir amostragem por exceção; com DFe, antes de manifestar o destinatário recebe só o resumo e o cancelamento (o conteúdo exato do `resNFe` não verifiquei [N]). |
| 6 | DCTFWeb × folha/ERP | CONSXMLDECLARACAO38 (XML), CONSRECIBO32 ; evento E0301 | XML | **Sim** | ≈ R$0,24-0,48 | 00103 | XML é o único formato estruturado "forte" do catálogo. |
| 7 | MIT × apuração do ERP | CONSAPURACAO316, LISTAAPURACOES317 | JSON | **Sim** | ≈ R$0,24-0,48 | não listada [N] | Só PJ. |
| 8 | Parcelamentos × contas a pagar | 8 modalidades × (PEDIDOSPARC, OBTERPARC, DETPAGTOPARC, PARCELASPARAGERAR) | JSON | **Sim** | 1-3 Consultas por modalidade com parcelamento | vários | Disparar só para clientes com parcelamento conhecido. |
| 9 | Procuração × vigência | OBTERPROCURACAO41 | JSON | **Sim** | 1 Consulta por cliente (pode ser trimestral) | n/a | Evita 403 cobrado. |

**Exigem emissão ou transmissão (fora do escopo somente-leitura):** gerar DAS/DARF/guias (classe D), transmitir PGDAS-D/DEFIS/DCTFWeb/MIT, opção de regime, renúncia no PNR, benefício MEI. Nenhum dos 9 cruzamentos acima precisa deles. Dois usam o caminho `/Emitir` só porque o SITFIS e o comprovante se chamam assim (classe C).

### 3.3 Riscos e como o dado se comporta
- **Sigilo fiscal.** A Loja diz que a solução opera "em estrita conformidade com as regras de sigilo fiscal e a LGPD" (https://loja.serpro.gov.br/product/integracontador). O art. 198 do CTN veda divulgação pela Fazenda Pública e seus servidores (https://www.planalto.gov.br/ccivil_03/leis/l5172compilado.htm); ele não se aplica diretamente ao escritório. O escritório responde por LGPD, contrato com o cliente e sigilo profissional [I]. Não consegui confirmar o artigo do sigilo na NBC PG 01 (2019, que substituiu a Res. CFC 803/96): https://cfc.org.br/registro/codigo-de-etica-profissional/ [N].
- **LGPD e LLM.** O próprio Termo de Autorização carrega aviso legal: é dever de quem consome o acesso "observar a adoção de base legal para o tratamento dos dados recebidos" (arts. 7º/11, 6º, 9º, 17, 18). Enviar dados fiscais a um provedor de LLM cria um operador/suboperador; o operador trata "conforme as instruções do controlador" (art. 39), controlador e operador respondem solidariamente em caso de dano (art. 42 §1º), e transferência internacional exige hipótese do art. 33 (modelo hospedado fora do Brasil). https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm [C para os artigos; aplicação ao caso: I]. Dados de PJ tendem a incluir CPF de sócios e dados de empregados (parcelas de folha): minimizar o que vai ao contexto.
- **Procuração por cliente.** Onboarding manual no portal da Receita (cliente: gov.br prata/ouro; validação em 30 dias). A IN 2.320/2026 art. 13 impede automatizar a outorga; art. 15 pode limitar a quantidade por representante; RFB pode bloquear o representante que use acesso intermediado.
- **Custo por chamada.** Preço único por faixa mensal (efeito degrau), 403/202 cobrados, laços de agente podem estourar a faixa. Tools devem ser baratas por padrão (índice antes do PDF) e ter orçamento por conversa.
- **Dados voláteis e estado.** O resultado de leitura pode mudar (malha, DAS pago). Guardar data/hora da consulta e mostrar ao usuário. 504 em Declarar/Emitir é estado indeterminado.
- **Automação x scraping.** A própria doc diz que a API do Caixa Postal "busca substituir abordagens baseadas em Web Scraping" (https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-caixapostal/caixapostal/). Não usar RPA no e-CAC como atalho: a IN 2.320 enquadra automação de navegador como acesso intermediado (art. 13 §1º). O texto do art. 13 trata de outorga, alteração e revogação de autorizações; a notícia oficial da Receita resume de forma mais ampla (veda sistemas automatizados ou intermediários não autorizados): https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2026/abril/receita-federal-atualiza-regras-para-acesso-a-servicos-digitais [C para os dois textos; alcance exato sobre leitura de dados: I].

### 3.4 Cache/TTL: o que existe e o que não achei
- Caches **técnicos** documentados: Termo de Autorização (até 00:00 do dia seguinte, 304 no reenvio); protocolo SITFIS (só no dia); resultado de EVENTOS (20 min, entrega única).
- **Direito de reter/cachear dados de resposta do Integra Contador: não achei** [N: busca por "armazenamento", "retenção", "terceiros", "LGPD", "cache" nas dezenas de páginas de doc baixadas e nas páginas da Central de Ajuda]. O contrato-padrão do Serpro tem cláusula contra armazenar/reproduzir (seção 4). Tratar qualquer persistência além da sessão como pendente de resposta formal da Serpro.

### 3.5 Decisões que ficam em aberto, com recomendação [I]
1. **Quem é o contratante.** (a) Cada escritório contrata com o próprio e-CNPJ e usa as próprias credenciais: sem Termo, sem terceiros, consumo e fatura do próprio escritório. (b) O produto contrata e cada escritório assina Termo de Autorização: exige certificado do escritório disponível todo dia (ou termo de `vigencia` longa, a testar), consumo consolidado no produto e repasse comercial a definir. Recomendação: (a) no piloto; (b) só depois das respostas da Serpro às perguntas 1, 3 e 4 da seção 4.
2. **Escopo v1 do MCP.** Allowlist do apêndice A (inclui SITFIS 92); nenhum guia/declaração; MSGDETALHAMENTO62 apenas com confirmação humana e aviso de ciência.
3. **O que persiste.** Índices, metadados e **resultados dos cruzamentos**; PDF/XML brutos só durante a sessão até a Serpro responder sobre armazenamento.
4. **LLM.** Contexto mínimo (achados estruturados, não documentos), provedor sob controle do escritório, sem retenção/treino, processamento no Brasil se possível.
5. **Custo.** Governador por categoria/tenant, eventos gratuitos antes de consultas pagas, piloto no trial para medir nº de chamadas por conversa. Se o escritório for associado a um SESCON/sindicato contábil com contrato Serpro, perguntar a faixa agregada.
6. **Procuração.** Onboarding guiado e manual (a IN 2.320 impede automatizar a outorga), com OBTERPROCURACAO41 para validar existência/vencimento e um calendário de renovação.
7. **PDF.** Decidir parser de PDF (PGDAS-D, SITFIS) com amostras reais antes de prometer o cruzamento 1; o índice JSON (`dasPago`, `malha`) entrega valor sem parser.

---

## 4. Termos de uso do Integra Contador: repasse a terceiros/LLM, armazenamento, IA

**O que existe de público e o que não** [C/N]
- O contrato do Integra Contador **não é público**. A contratação redireciona para login (https://cliente.serpro.gov.br/#!/e-commerce/integra_contador/inicio abre `login-produtos.serpro.gov.br`). A página do Integra Contador na Central de Ajuda não traz contrato nem termos (só links genéricos de gestão contratual): https://centraldeajuda.serpro.gov.br/duvidas/pt/documentacoes/doc_integracontador/ (atualizada 22/09/2022) e https://centraldeajuda.serpro.gov.br/duvidas/pt/gestao-contratual/informacoesgestaocontratual/ . A cópia do contrato fica na Área do Cliente (opção Contratos).
- Buscas feitas sem achar a cláusula: "Integra Contador contrato de adesão cláusula repassar terceiros", "termos de uso armazenamento retenção software house", "contrato Integra Contador Descrição dos Serviços anexo", "Aviso de Privacidade Integra Contador", "Serpro contrato inteligência artificial treinamento dados". Só apareceram contratos de adesão de outros produtos e avisos de privacidade de CPF/CNPJ/Datavalid.

**Evidência mais próxima 1: o Termo de Autorização** [C] (https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-contador-gerenciador/autenticaprocurador/padroes_tecnicos_assinatura_xml/): o aviso legal obrigatório no XML põe no destinatário/consumidor do acesso o dever de "observar a adoção de base legal para o tratamento dos dados recebidos" (LGPD). A finalidade do termo é "única e exclusiva" apresentar o consentimento do procurador para o contratante fazer requisições em nome dele. Nada diz sobre repasse.

**Evidência mais próxima 2: contrato-padrão de adesão do Serpro (outro produto)** [C, mas de outro produto]. Cópia do contrato de adesão da Consulta Restituição IRPF via entidade representativa (versão 20240228.1404, Parecer Jurídico SERPRO 0408/2023): https://www.fomento.pr.gov.br/sites/default/arquivos_restritos/files/documento/2024-09/Inexigibilidade_02_24_Contrato_15_24_Consulta_Restituicao_IRPF_SERPRO.pdf
- Cl. 3.1.5, obrigação do CLIENTE: "Não armazenar ou reproduzir os dados e informações obtidos por meio dos serviços", exceto situações justificadas necessárias à atividade do cliente ou exigidas por lei, "informando individual e detalhadamente ao SERPRO sobre cada ocorrência excepcional".
- Cl. 3.1.6: "Não utilizar os serviços e os dados obtidos para finalidade ou forma distinta" da concebida; suspeita permite suspensão e rescisão.
- Cl. 5.2.2: confidencialidade implica "não divulgar ou repassar informações e conhecimentos a terceiros não envolvidos nesta relação contratual", salvo autorização escrita; exceção para exigência legal (5.2.4).
- Cl. 5.6: Serpro não responde por "uso indevido por terceiros das ferramentas".
- Anexo LGPD: o CLIENTE é responsável por finalidades legítimas, por informar ao titular o compartilhamento com o Operador (Serpro) e por informar o volume esperado de consultas.
- Cl. 11.1: reajuste de preço pelo IPCA; 12.3: cancelamento da autorização que a origem dos dados deu ao Serpro suspende o serviço.
- [I] O Integra Contador contratado pela Loja deve usar contrato da mesma família, com anexo "Descrição dos Serviços" próprio. **Não confirmei.** O anexo é onde estariam regras de cache/retenção/uso por terceiros.

**Pode repassar a resposta a terceiros/LLM?** [N/I] Não achei autorização nem vedação específica. Pela família de cláusulas acima, repasse a terceiro fora da relação contratual precisa de autorização escrita, e persistir/reproduzir exige justificativa informada ao Serpro. **Tratar LLM de terceiros como destinatário não autorizado até haver resposta por escrito.** Opção de menor risco: LLM com dados sob controle do escritório (processamento no Brasil, sem retenção/treino pelo provedor, contrato de operador) e contexto mínimo.

**Exposição por API a clientes do escritório** [N] Não achei texto sobre isso. O que existe: o Serpro diz em 2026 que "empresas utilizem capacidades tecnológicas do Serpro" para integrar nos produtos que vendem, mas a notícia fala de CPF/CNPJ/Datavalid e não menciona Integra Contador: https://www.serpro.gov.br/menu/noticias/noticias-2026/quando-dados-viram-oportunidade-de-negocio (14/09/2026). No mercado, software houses contratam e escritórios assinam o Termo (modelo oficial); Alterdata/Omie/Domínio apresentam o escritório como pagante direto do Serpro (secundário). Cliente final do escritório vendo dado dele próprio parece tema de LGPD, não de contrato, mas é [I].

**IA/LLM no contrato:** [N] nenhuma cláusula achada. Um resumo de busca cita, no contrato Serpro Multicloud (versão 2025), vedação de o provedor usar informação do cliente para otimizar mecanismos de IA; não abri o PDF e é irrelevante para o Integra Contador. A Serpro lançou produtos de IA para a administração pública (Serpro Agents, Nexo) em ago/2026, sem relação com Integra Contador: https://www.serpro.gov.br/menu/noticias/noticias-2026/serpro-secop-2026

**Perguntas para a Serpro por escrito (Central de Ajuda / Área do Cliente):**
1. O contrato do Integra Contador contém cláusula equivalente à 3.1.5 (não armazenar/reproduzir)? O que conta como "armazenar" (snapshot de PDF/XML/JSON, tabela derivada)?
2. Há prazo máximo de retenção/TTL permitido para cache por finalidade (conferência mensal)?
3. É permitido enviar respostas a operador de IA (LLM) contratado pelo escritório? Em que condições (Brasil, sem treino)?
4. Uma software house contratante pode servir vários escritórios (Termo de Autorização) com a mesma chave, e como isso aparece no consumo/faturamento?
5. Qual o limite de requisições por segundo/contrato e o SLA?
6. A Loja cobra SITFIS SOLICITARPROTOCOLO91 e INNOVAMSG63 (Apoiar/Monitorar) ou não?
7. A faixa é calculada "direto na faixa" por categoria e por mês de apuração?

---

## 5. MCP server / integração de IA já pronta para Serpro/Receita

**Nada pronto para Integra Contador ou APIs Serpro de contabilidade** [N]. Buscas feitas em 20/11/2026:
- `gh search repos` com: "integra contador mcp", "serpro mcp", "receita federal mcp", "model context protocol serpro", "mcp contabilidade", "mcp consulta cnpj", "mcp sped fiscal", "mcp esocial", "mcp nota fiscal eletronica".
- Registry oficial MCP (`registry.modelcontextprotocol.io/v0/servers?search=serpro` e `search=integra`), registry do claude.ai (keywords: serpro, integra contador, receita federal, cnpj, nfe, sped, contabil), grep.app (`integra-contador/v1`, `gateway.apiserpro.serpro.gov.br`), listas awesome-mcp-brasil.

**Achados relacionados (nenhum é Integra Contador):**

| Item | O que é | Licença / status |
|---|---|---|
| `mcp-dir/serpro_radar_veiculo-mcp` (registry oficial) | Consulta de veículo "Serpro Radar", hospedada em plataforma de terceiros, pré-pago | repositório MIT, 0 estrelas, push 30/08/2026; irrelevante para contabilidade https://github.com/mcp-dir/serpro_radar_veiculo-mcp |
| `DeHor-Labs/mcp-fiscal-brasil` | 44 tools fiscais (CNPJ, NF-e, NFS-e, CT-e, SPED, eSocial, Simples, reforma IBS/CBS); SEFAZ por mTLS A1 opt-in; sem Serpro Integra Contador | MIT, 435 estrelas, push 15/11/2026 https://github.com/DeHor-Labs/mcp-fiscal-brasil |
| `SamuelMoraesF/mcp-nfse-nacional` | Consulta NFS-e no portal nacional com e-CNPJ/e-CPF | sem licença, 19 estrelas, push 12/02/2026 https://github.com/SamuelMoraesF/mcp-nfse-nacional |
| `pqgventures/dilligence-mcp` | MCP hospedado de certidões (CND etc.); repositório só traz setup | MIT (repo), 0 estrelas, push 15/11/2026 https://github.com/pqgventures/dilligence-mcp |
| `silasrm/mcp-brasilapi` | BrasilAPI (CNPJ, CEP, IBGE...) | Apache-2.0, push 09/07/2026 https://github.com/silasrm/mcp-brasilapi |
| Dext MCP (registry claude.ai) | MCP de contabilidade "Read-only" de outro fornecedor: bom modelo de escopo | proprietário |
| awesome-mcp-brasil (duas listas) | Índices de MCPs brasileiros | CC0 https://github.com/daniel-filius/awesome-mcp-brasil · https://github.com/ciro-maciel/awesome-mcp-brasil |

**SDKs/clientes do Integra Contador (não são MCP, úteis como referência de contrato HTTP)** [C: gh]: `MarlonSantosDev/serpro_integra_contador_api` (Dart, MIT, 15 estrelas, push 07/07/2026, mTLS + Termo de Autorização + trial), `GabrielHCamargo/SDK-Integra-Contador` (Python/Pydantic, Apache-2.0, 3 estrelas, push 30/11/2025), `danilorc/integra-contador-opensource` (MIT, 0 estrelas), outros sem licença. Pouca tração e mantenedores individuais: usar só como leitura.

**Serpro e MCP:** a matéria da Consecti (16/10/2025, secundária) cita um gerente do Serpro: "Estamos construindo MCPs que também vão poder ser usados por nossos desenvolvedores", ligado às APIs de IA (ConversAI Studio); sem informação sobre disponibilidade externa. A nota oficial de 06/08/2026 sobre Serpro Agents/Nexo não menciona MCP. https://consecti.org.br/serpro-lanca-chatgpt-dos-orgaos-publicos-e-prepara-agentes-de-inteligencia-artificial/

---

## 6. Lacunas e verificações pendentes
1. **Texto do contrato do Integra Contador** (Área do Cliente > Contratos): cláusulas de armazenamento, terceiros, IA, SLA, reajuste. Bloqueia as decisões de cache e LLM.
2. **Catálogo após 31/10/2026**: QTQMSG64, ANEXOSMSG65, URLANEXOMSG66 entraram? Há serviços novos além dos 99?
3. **Cobrança real de Apoiar/Monitorar** (SITFIS 91, INNOVAMSG63): conferir no CSV de consumo (coluna URL) no primeiro mês.
4. **Modelo "direto na faixa" do Integra Contador**: confirmar por categoria e por mês.
5. **Como um escritório PJ valida a Autorização de Acesso** no sistema novo e se existe limite da Cogea por representante (art. 15).
6. **Vigência máxima do Termo de Autorização** e se reenviar o mesmo XML assinado por vários dias é aceito enquanto `vigencia` e o certificado valerem.
7. **Procuração do MIT**: código não consta na tabela "Serviços x Procurações" (que não inclui MIT, PGDASD 17-19, DCTFWEB 313).
8. **Parsing de PDF** (PGDAS-D, SITFIS): avaliar estabilidade de layout com amostras do trial e de um cliente real antes de prometer o cruzamento 1.
9. **Preço de entidade de classe** (Sescon etc.) para o Integra Contador: não achei tabela.
10. **Consulta Faturamento/Renda/Restituição**: elegibilidade de escritório não confirmada.

---

## 7. Fontes (acessadas em 20/11/2026)

Serpro, documentação técnica (HTML bruto via curl; datas = rodapé da página):
- https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/ (25/02/2026) · /pt/catalogo_de_servicos/ (15/10/2026) · /pt/integra_contador/ (10/04/2026) · /pt/quick_start/ (10/04/2026) · /pt/como_contratar/ (25/02/2026) · /pt/faq/ (25/05/2026) · /pt/codigos_retorno/ (08/09/2026) · /pt/timeout/ (08/09/2026) · /pt/mensagens/ (08/09/2026) · /pt/servicos_vs_procuracoes/ (01/06/2026) · /pt/identificador_requisicoes/ (10/04/2026) · /pt/como_usar_a_demonstracao_da_api/ (25/02/2026)
- Gerenciador: /pt/solucoes/integra-contador-gerenciador/autenticaprocurador/ (+ /cache/, /servicos/envio_de_xml_assinado/, /padroes_tecnicos_assinatura_xml/) e /eventosatualizacao/ (+ /limites/, /mapa_dos_eventos/)
- Serviços: /pt/solucoes/integra-sitfis/sitfis/ (+ /cache/, /tempo_espera/, /servicos/apoiar_relatorio/, /servicos/emitir_relatorio/, /changelog/) · integra-caixapostal/caixapostal/ (+ /changelog/, serviços de detalhe, lista, anexos, indicador) · integra-sn/pgdasd/ (intro e serviços) · integra-dctfweb/dctfweb/ e /mit/ · integra-mei/pgmei/servicos/atualizar_beneficio/ · integra-pagamento/pagtoweb/servicos/consulta_pagamento/ · integra-procuracoes/procuracoes/servicos/obter_procuracao/ · integra-sicalc/sicalc/changelog/ · integra-redesim/pnrcontador/ · integra-e-processo/eprocesso/ · integra-caixapostal/dte/
- Outras APIs: https://apicenter.estaleiro.serpro.gov.br/documentacao/consulta-nfe/ (pt/faq, leiautes_formatos, tipos_retornados, codigos_retorno, como_contratar, informacoes_push, quick_start), .../consulta-cnpj/pt/quick_start/, .../consulta-cnd/

Loja Serpro (navegador embutido): https://loja.serpro.gov.br/product/integracontador (abas Características, Forma de Contratação, Preço, Documentação) · /consulta-cnpj/product/consultacnpj · /consulta-cnd/product/consultacnd · /consulta-nf-e/product/consultanfe · /consulta-cpf/product/consultacpf · /product/datavalid · /product/consultafaturamento · /product/ConsultaRestituicao · /product/consulta-divida-ativa · /product/radar · /entidades-representativas/ · /home

Serpro, notícias e ajuda: https://serpro.gov.br/menu/noticias/noticias-2025/integra-contador-novas-funcionalidades (09/04/2025) · https://www.serpro.gov.br/menu/noticias/noticias-2025/sescon-pa-contrata-integra-contador (06/10/2025) · https://www.serpro.gov.br/menu/noticias/noticias-2026/contratacao-entidades-representativas (24/09/2026) · https://www.serpro.gov.br/menu/noticias/noticias-2026/quando-dados-viram-oportunidade-de-negocio (14/09/2026) · https://www.serpro.gov.br/menu/noticias/noticias-2026/serpro-secop-2026 (06/08/2026) · Central de Ajuda: /avisos/integracontadoreventosatualizacao/ (17/04/2024), /area-do-cliente/consumo/ (17/03/2026), /avisos/avisonovapoliticapreco2024/ (19/06/2024), /documentacoes/doc_integracontador/, /gestao-contratual/informacoesgestaocontratual/

Receita Federal / Gov / legislação: IN RFB 2.320/2026 (texto oficial) https://normasinternet2.receita.fazenda.gov.br/#/consulta/externa/150461 · https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2026/abril/receita-federal-atualiza-regras-para-acesso-a-servicos-digitais (09/04/2026, atualizada 28/10/2026) · https://www.gov.br/pt-br/servicos/cadastrar-ou-cancelar-procuracao-para-acesso-ao-e-cac (12/11/2026) · Guia do usuário Autorizações de Acesso v1.0 · https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2026/janeiro/atencao-pessoas-juridicas (DTE) · https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2022/setembro/receita-federal-e-serpro-disponibilizam-nova-plataforma-de-prestacao-de-servicos-contabeis-e-fiscais · https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm (LGPD) · https://www.planalto.gov.br/ccivil_03/leis/l5172compilado.htm (CTN) · https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/2025-08/ · http://moc.sped.fazenda.pr.gov.br/NFe_NFCe/NFeDistribuicaoDFe.html

Contrato-padrão Serpro (outro produto): https://www.fomento.pr.gov.br/sites/default/arquivos_restritos/files/documento/2024-09/Inexigibilidade_02_24_Contrato_15_24_Consulta_Restituicao_IRPF_SERPRO.pdf

Fontes secundárias (marcadas como tal no texto): https://ajuda.omie.com.br/pt-BR/articles/9750205 · https://suporte.dominioatendimento.com/central/faces/solucao-onvio.html?codigo=10776 · https://toexceed.com.br/blog/2026/10/03/integra-contador-preco-quanto-custa-e-como-funciona-a-cobranca/ · https://ajuda.alterdata.com.br/prosoftcontabil/c1725-simples-nacional-serpro-integra-contador-contratacao-e-procuracao-220178525.html · https://consecti.org.br/serpro-lanca-chatgpt-dos-orgaos-publicos-e-prepara-agentes-de-inteligencia-artificial/ · repositórios GitHub citados na seção 5.

---

## Apêndice A. Allowlist e blocklist por `idServico` (99 em produção)

**Allowlist somente-leitura (68):**
- PGDASD: CONSDECLARACAO13, CONSULTIMADECREC14, CONSDECREC15, CONSEXTRATO16
- REGIMEAPURACAO: CONSULTARANOSCALENDARIOS102, CONSULTAROPCAOREGIME103, CONSULTARRESOLUCAO104
- DEFIS: CONSDECLARACAO142, CONSULTIMADECREC143, CONSDECREC144
- PGMEI: DIVIDAATIVA24 · CCMEI: DADOSCCMEI122, CCMEISITCADASTRAL123
- DCTFWEB: CONSRECIBO32, CONSDECCOMPLETA33, CONSXMLDECLARACAO38
- MIT: CONSAPURACAO316, LISTAAPURACOES317, SITUACAOENC315
- PROCURACOES: OBTERPROCURACAO41 · SICALC: CONSOLIDAR54, CONSULTAAPOIORECEITAS52
- CAIXAPOSTAL: MSGCONTRIBUINTE61, INNOVAMSG63 · DTE: CONSULTASITUACAODTE111
- PAGTOWEB: PAGAMENTOS71, CONTACONSDOCARRPG73
- PARCSN 162-165, PARCSN-ESP 172-175, PERTSN 182-185, RELPSN 192-195, PARCMEI 202-205, PARCMEI-ESP 212-215, PERTMEI 222-225, RELPMEI 232-235 (PARCELASPARAGERAR, PEDIDOSPARC, OBTERPARC, DETPAGTOPARC de cada)
- PNRCONTADOR: CONSVINCULOS261, CONSRENUNCIA263, SITSOLICRENUNCIA265 · EPROCESSO: CONSPROCPORINTER271
- EVENTOSATUALIZACAO: SOLICEVENTOSPF131, SOLICEVENTOSPJ132, OBTEREVENTOSPF133, OBTEREVENTOSPJ134
- SITFIS: SOLICITARPROTOCOLO91

**Opcionais (cobradas como Emissão, efeito prático de leitura) (4):** SITFIS RELATORIOSITFIS92, PAGTOWEB COMPARRECADACAO72, CCMEI EMITIRCCMEI121, PNRCONTADOR COMPRENUNCIA264. (SITFIS 92 é necessário para o cruzamento 2: liberar.)

**Blocklist (27):** CAIXAPOSTAL MSGDETALHAMENTO62 (ciência; só com confirmação humana) · AUTENTICAPROCURADOR ENVIOXMLASSINADO81 (uso interno) · PGMEI ATUBENEFICIO23 (grava) · guias (18): PGDASD GERARDAS12/17/18/19, PGMEI GERARDASPDF21/GERARDASCODBARRA22, DCTFWEB GERARGUIA31/GERARGUIAANDAMENTO313, SICALC CONSOLIDARGERARDARF51/GERARDARFCODBARRA53, GERARDAS161/171/181/191/201/211/221/231 · Declarar (6): PGDASD TRANSDECLARACAO11, DEFIS TRANSDECLARACAO141, DCTFWEB TRANSDECLARACAO310, MIT ENCAPURACAO314, REGIMEAPURACAO EFETUAROPCAOREGIME101, PNRCONTADOR SOLICRENUNCIA262.

Conferência: 68 + 4 + 27 = 99.
