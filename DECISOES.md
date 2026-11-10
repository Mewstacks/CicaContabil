# CICA â€” decisÃµes e limites de confirmaÃ§Ã£o

> Registro canÃ´nico na raiz desde 17/09/2026, por D-59. Ler com [plano mestre](PLANO-MESTRE.md) e [validaÃ§Ãµes tÃ©cnicas](VALIDACOES.md). DecisÃ£o aprovada nÃ£o Ã© funÃ§Ã£o implementada. As classificaÃ§Ãµes histÃ³ricas abaixo foram preservadas: â€œRegistradaâ€ nÃ£o foi promovida a â€œConfirmadaâ€. NÃ£o repetir perguntas jÃ¡ resolvidas.

O bloco D-01â€“D-45 e a lista â€œDecisÃµes que nÃ£o foram tomadasâ€ sÃ£o o registro histÃ³rico de 15/09. AtualizaÃ§Ãµes D-46â€“D-60 ao final prevalecem somente no escopo explÃ­cito; por exemplo, Q-10 foi resolvida.

Atualizado em 15/09/2026. **Confirmada** significa resposta direta do responsÃ¡vel, registrada na sessÃ£o indicada em [fontes e histÃ³rico](docs/planejamento/fontes-e-historico.md) ou nesta conversa. **Registrada** significa que um plano/documento a apresenta como decisÃ£o anterior, mas o detalhe ainda nÃ£o foi reconfirmado nesta rodada. **Proposta** nÃ£o autoriza implementaÃ§Ã£o comercial, publicaÃ§Ã£o ou gasto. Os estados tÃ©cnicos estÃ£o em [estado operacional](docs/planejamento/estado-operacional.md).

## Produto, marca e venda

| ID | Estado | DecisÃ£o / limite exato | Fonte | ConsequÃªncia |
| --- | --- | --- | --- | --- |
| D-01 | Confirmada | Nome oficial **CICA**, Central de InteligÃªncia ContÃ¡bil AvanÃ§ada. â€œHubContadorâ€ e â€œCICAâ€ sÃ£o nomes histÃ³ricos/tÃ©cnicos. | CX-07; `docs/cica-implementation.md` | Texto pÃºblico e documentaÃ§Ã£o de produto usam CICA; renomear identificadores tÃ©cnicos Ã© assunto separado. |
| D-02 | Confirmada | Produto centralizado SaaS para escritÃ³rios, com liberaÃ§Ã£o de ferramentas e funÃ§Ãµes conforme contrataÃ§Ã£o. | CX-01; CX-07 | Contrato, mÃ³dulos, isolamento por escritÃ³rio e permissÃµes precisam ser fontes consistentes de acesso. |
| D-03 | Confirmada | Todos os mÃ³dulos e a IA devem funcionar de ponta a ponta pela visÃ£o operacional antes de serem vendidos; dÃºvidas de produto devem ser trazidas ao responsÃ¡vel. | CX-07; CX-09; CX-10 | â€œHÃ¡ modelo/tela/testeâ€ nÃ£o basta para declarar funÃ§Ã£o pronta. |
| D-04 | Registrada | Teste de 14 dias com suÃ­te completa, sem cartÃ£o; MFA obrigatÃ³rio apÃ³s teste/contrataÃ§Ã£o e dispensado no teste. | `docs/cica-implementation.md`; `docs/cica-mfa-contract-review.md` | A regra atual precisa de validaÃ§Ã£o de ponta a ponta com o fluxo Asaas decidido agora; condiÃ§Ãµes comerciais finais ainda nÃ£o foram reconfirmadas. |
| D-05 | Registrada | Marca visual marfim e verde escuro, domÃ­nio escolhido `cicacontabil.com.br`, fornecedora Mewstack. | `docs/cica-implementation.md`; `docs/cica-landing-direction.md` | Landing e documentos legais seguem esse contexto; marca, prova social e publicaÃ§Ã£o ainda exigem fechamento. |
| D-06 | Confirmada | ConfiguraÃ§Ã£o deve ser simples para o prÃ³prio escritÃ³rio; conexÃ£o DomÃ­nio local por ODBC/agente e DomÃ­nio Web por backup importado com atualizaÃ§Ã£o manual. | CX-02; CX-06 | Assistentes e instruÃ§Ãµes precisam cobrir ambos sem alegar sincronizaÃ§Ã£o automÃ¡tica do DomÃ­nio Web. |
| D-07 | Confirmada | As telas devem ser revisadas pela tarefa real do usuÃ¡rio e por padrÃµes de produtos, com funcionamento em desktop e mobile. | CX-07; CX-09; CL-02 | CritÃ©rios de aceite incluem prÃ³ximo passo, estado, erro, permissÃ£o e navegaÃ§Ã£o, alÃ©m da aparÃªncia. |

## Integra Contador, franquia e cobranÃ§a

| ID | Estado | DecisÃ£o / limite exato | Fonte | ConsequÃªncia |
| --- | --- | --- | --- | --- |
| D-08 | Confirmada | As credenciais/contrato Serpro pertencem Ã  **Mewstack**, centralmente; o escritÃ³rio usa cotas e nÃ£o cadastra sua prÃ³pria chave Serpro. | CX-05; resposta em CX-09 | Segredos e certificados da central nÃ£o entram no workspace do escritÃ³rio; consumo Ã© medido por organizaÃ§Ã£o e serviÃ§o. |
| D-09 | Confirmada | Existe franquia contratada por escritÃ³rio e excedente; o plano Codex enviado pelo responsÃ¡vel especificou uma fatura mensal Ãºnica, com mensalidade e excedentes, sem cobranÃ§a avulsa por aÃ§Ã£o. | CX-05 | Reserva, liquidaÃ§Ã£o, ajuste e faturamento precisam ser idempotentes e auditÃ¡veis. |
| D-10 | Registrada | O plano CX-05 indicou fechamento da competÃªncia em `America/Sao_Paulo` no dia 1, vencimento dia 10, preÃ§os congelados em lanÃ§amentos e polÃ­tica `bloquear`/`exigir aprovaÃ§Ã£o`/`autorizar excedente` dentro do teto contratado. | CX-05 | Validar calendÃ¡rio, polÃ­tica e condiÃ§Ãµes na revisÃ£o comercial antes de publicar ou migrar contratos. |
| D-11 | Confirmada em 15/09 | **Asaas Ã© o padrÃ£o** de cobranÃ§a e atende Pix, boleto e cartÃ£o. Banco Inter para Pix/boleto Ã© desenho anterior, substituÃ­do neste escopo. | respostas do responsÃ¡vel nesta conversa; CL-03 e CX-05 como histÃ³rico | Uma fatura deve evitar tentativas simultÃ¢neas/duplicadas ao trocar o meio de pagamento. IntegraÃ§Ã£o Asaas ainda nÃ£o estÃ¡ homologada. |
| D-12 | Confirmada em 15/09 | Ã‰ possÃ­vel cadastrar escritÃ³rio/empresa manualmente, cobrar manualmente e definir preÃ§o individual diferente do catÃ¡logo. | resposta do responsÃ¡vel nesta conversa | O contrato deve distinguir cobranÃ§a Asaas de cobranÃ§a manual, registrar valores especÃ­ficos e preservar o histÃ³rico. |
| D-13 | Confirmada em 15/09 | Contratos de cobranÃ§a manual ficam fora dos webhooks e da suspensÃ£o dirigida pelo Asaas, inclusive instalaÃ§Ã£o Windows dedicada. | resposta do responsÃ¡vel nesta conversa | Um evento Asaas jamais altera contrato manual; mÃ©todo e estado de acesso manual dependem da regra comercial ainda aberta. |
| D-14 | Registrada | Nenhuma aÃ§Ã£o do usuÃ¡rio deve gerar cobranÃ§a avulsa do Serpro; cotas, aprovaÃ§Ã£o ou bloqueio precedem a chamada e apenas chamadas efetivamente faturÃ¡veis sÃ£o liquidadas. | CX-05; `docs/cica-operation-access-review.md` | HomologaÃ§Ã£o deve conferir projeÃ§Ã£o, reserva, resposta, retry, excedente e reconciliaÃ§Ã£o. |
| D-15 | Confirmada em 15/09 | **Asaas suspende automaticamente por inadimplÃªncia apÃ³s um prazo de carÃªncia ainda a definir, em modo somente leitura, sem apagar dados; contratos manuais tÃªm suspensÃ£o decidida por operador.** A documentaÃ§Ã£o CICA anterior separava registro financeiro e decisÃ£o de acesso para todos. | respostas do responsÃ¡vel nesta conversa; `docs/cica-mfa-contract-review.md`; CL-03 | Confirmar duraÃ§Ã£o e marco inicial da carÃªncia, quais GETs/downloads permanecem disponÃ­veis, recuperaÃ§Ã£o apÃ³s pagamento e tratamento de estornos. |

## IA, conhecimento e dados

| ID | Estado | DecisÃ£o / limite exato | Fonte | ConsequÃªncia |
| --- | --- | --- | --- | --- |
| D-16 | Confirmada | **Claude Sonnet por API KEY no `.env` agora**, deixando o produto preparado para o PC/modelo local futuro. A decisÃ£o cobre Copiloto e, por confirmaÃ§Ã£o nesta conversa, tambÃ©m anÃ¡lise de anexos da Triagem. | CX-09; resposta nesta conversa | O plano CL-04 â€œsomente modelo localâ€ foi substituÃ­do para a etapa provisÃ³ria. Arquitetura de migraÃ§Ã£o e limites devem ser explÃ­citos. |
| D-17 | Confirmada | Serpro e IA terÃ£o cotas por escritÃ³rio. O responsÃ¡vel pediu pesquisa de limites ideais e preÃ§os, mas **nÃ£o definiu** teto Claude por requisiÃ§Ã£o/dia/mÃªs nem franquia final. | CX-09; `docs/cica-operation-access-review.md` | NÃ£o escrever nÃºmero comercial como aprovado nem realizar chamada paga sem confirmaÃ§Ã£o especÃ­fica de custo. |
| D-18 | Registrada | Consulta ao DomÃ­nio Ã© somente leitura, por ODBC local ou agente no escritÃ³rio; respostas de IA precisam de evidÃªncia e curadoria, com aÃ§Ã£o humana para alteraÃ§Ã£o. | CX-02; [MCP interno](docs/intelligence-mcp.md) | Escopo por organizaÃ§Ã£o/empresa e recusa de SQL, DSN e credenciais no argumento da ferramenta. |
| D-19 | Registrada | O Copiloto ficou oculto e indisponÃ­vel para escritÃ³rios atÃ© infraestrutura local na configuraÃ§Ã£o antiga. | `docs/cica-implementation.md`; `platform.PlatformConfiguration` | A decisÃ£o D-16 pede novo caminho temporÃ¡rio; ativaÃ§Ã£o, polÃ­tica de custo e publicaÃ§Ã£o comercial ainda nÃ£o estÃ£o concluÃ­das. |
| D-20 | Registrada | Dados de documento/cliente nÃ£o viram instruÃ§Ãµes da IA; revisÃµes, fontes e correÃ§Ãµes precisam de trilha. | `docs/intelligence-mcp.md`; `docs/plano-triagem-documental.md` | Integridade e privacidade precisam ser testadas com anexos nÃ£o confiÃ¡veis e casos ambÃ­guos. |

## Triagem de Arquivos

| ID | Estado | DecisÃ£o / limite exato | Fonte | ConsequÃªncia |
| --- | --- | --- | --- | --- |
| D-21 | Confirmada | Primeira versÃ£o vendÃ¡vel recebe documentos **somente de caixa de e-mail**, sem upload de tela nem pasta monitorada como entrada. | CX-09; CL-04 | Ã‰ preciso conectar caixa, ler anexos com cursor/idempotÃªncia e oferecer estado de conexÃ£o/erro. |
| D-22 | Confirmada | Suportar **Microsoft 365, Google/Gmail e IMAP genÃ©rico**, os trÃªs. | CX-09 | O plano CL-04 listava Graph e Gmail via IMAP como alternativa; a forma tÃ©cnica e OAuth ainda exigem pesquisa/homologaÃ§Ã£o. |
| D-23 | Confirmada; esclarecida em 15/09 | Cada escritÃ³rio conecta **a prÃ³pria caixa** em um fluxo guiado. Para Microsoft 365 e Google Workspace, configura **seu aplicativo OAuth** no sistema, com manual passo a passo; IMAP genÃ©rico usa assistente TLS. Para **Gmail pessoal**, a Mewstack manterÃ¡ um aplicativo Google verificado e cada escritÃ³rio autorizarÃ¡ apenas sua conta. | CX-09; resposta direta â€œcada escritÃ³rio deve configurar o seuâ€; escolha especÃ­fica do responsÃ¡vel para Gmail pessoal; [pesquisa oficial](docs/planejamento/conexao-caixas-email.md) | Homologar apps e consentimento reais. A Mewstack precisa fornecer redirect HTTPS e registrar/verificar seu app Gmail pessoal antes da venda dessa opÃ§Ã£o. |
| D-24 | Confirmada | Cada escritÃ³rio escolhe **biblioteca interna** ou **Ã¡rvore de pastas Windows da empresa** como destino. | CX-09; CL-04 | Ambas as opÃ§Ãµes fazem parte do objetivo; forma da troca e coexistÃªncia de arquivos antigos precisam ser definidas. |
| D-25 | Confirmada | Para Windows, o prÃ³prio escritÃ³rio configura a raiz; o padrÃ£o de pastas serÃ¡ definido pela CICA e a pasta de empresa deverÃ¡ conter nome e **cÃ³digo DomÃ­nio obrigatÃ³rio**. | CX-09 | Caminho real, nomenclatura completa, validaÃ§Ã£o de escape e permissÃµes do agente seguem pendentes. |
| D-26 | Registrada em CL-04 | `0000` no nome do arquivo Ã© `ClientCompany.dominio_code`; nome mensal `MMYYYY`, anual `YYYY`; colisÃ£o com mesmo hash Ã© duplicata, conteÃºdo diferente recebe `_02`, `_03`. | CL-04 | O padrÃ£o completo das 19 nomenclaturas e Ã¡rvore final ainda precisa de confirmaÃ§Ã£o do responsÃ¡vel. |
| D-27 | Registrada em CL-04 | AutomÃ¡tico sÃ³ com CNPJ Ãºnico no documento, regra determinÃ­stica vÃ¡lida e confianÃ§a â‰¥98% em cada campo obrigatÃ³rio; PDF com mÃºltiplos documentos vai sempre para revisÃ£o. | CL-04 | Meta e amostra de aceite precisam ser aprovadas; confianÃ§a numÃ©rica da IA nÃ£o equivale a precisÃ£o medida. |
| D-28 | Registrada em CL-04 | Limite proposto de 50 MB por anexo, PDF atÃ© 100 pÃ¡ginas; PDF/JPG/PNG/WebP/XLSX/CSV/TXT; protegido por senha rejeitado. | CL-04 | Confirmar limites/formato por operaÃ§Ã£o e dimensionar extraÃ§Ã£o/antimalware antes de publicar. |
| D-29 | Registrada | Checklist de recebidos sÃ³ muda apÃ³s arquivamento confirmado; WhatsApp de pendÃªncias Ã© frente posterior, sem provedor, consentimento, modelo ou custo definidos. | CL-04; [plano inicial](docs/plano-triagem-documental.md) | Mensageria nÃ£o integra o primeiro recorte vendÃ¡vel sem decisÃ£o separada. |
| D-30 | Confirmada como mÃ©todo | A reuniÃ£o de 11/09 Ã© material de conversa, nÃ£o especificaÃ§Ã£o; itens â€œConfirme antes de mudarâ€ devem ser respondidos pelo responsÃ¡vel, sem inventar arquivo, versÃ£o, prazo ou card. | CX-08 | Taxonomia, Ã¡rvore, canais auxiliares e polÃ­ticas permanecem perguntas quando a fonte nÃ£o basta. |

## IntegraÃ§Ãµes e operaÃ§Ãµes adjacentes

| ID | Estado | DecisÃ£o / limite exato | Fonte | ConsequÃªncia |
| --- | --- | --- | --- | --- |
| D-31 | Registrada | NFS-e Nacional (ADN) deve ser fonte de coleta para NFS-e, alÃ©m de telas de custÃ³dia/classificaÃ§Ã£o. | CL-03; `docs/cica-module-truth.md` | NÃ£o anunciar captura externa como pronta atÃ© existir cliente e homologaÃ§Ã£o com certificado autorizado. |
| D-32 | Registrada | DTE e guias/DCTFWeb devem fazer chamadas reais Ã  central Integra, com autorizaÃ§Ã£o de consumo, estados e resultado persistido, sem depender de planilha. | CX-03; CX-05 | Testes de cliente com transporte simulado nÃ£o substituem piloto Serpro. |
| D-33 | Registrada | Siescon nÃ£o tem adaptador homologado nem mecanismo pÃºblico de leitura confirmado; nÃ£o pedir segredo nem anunciar conexÃ£o ativa. | [descoberta Siescon](docs/cica-siescon-discovery.md) | Obter documentaÃ§Ã£o e homologaÃ§Ã£o pelo fornecedor antes de liberar. |
| D-34 | SubstituÃ­da por D-43 em 15/09 | A avaliaÃ§Ã£o anterior cogitava tirar Jornadas da oferta paga e ainda discutia se manteria o quadro. | conversa anterior; [avaliaÃ§Ã£o](docs/planejamento/avaliacao-jornadas.md) | A ordem posterior Ã© mais especÃ­fica: Triagem substitui Jornadas no produto. |
| D-35 | Registrada | ConciliaÃ§Ã£o OFX Ã— DomÃ­nio cruza empresa/data/valor e pede confirmaÃ§Ã£o humana da ambiguidade; Radar reÃºne publicaÃ§Ãµes oficiais, sem cÃ¡lculo de impacto por cliente. | [verdade dos mÃ³dulos](docs/cica-module-truth.md) | Aceite operacional precisa verificar fontes, falhas e carteira real. |
| D-36 | Confirmada em 15/09 | O responsÃ¡vel pediu arquivos `.md` atualizados com todas as decisÃµes tomadas nesta conversa e revisÃ£o completa do README principal. | Pedido direto nesta conversa | A memÃ³ria em `docs/planejamento/`, o README e o registro de execuÃ§Ã£o devem evoluir junto com a implementaÃ§Ã£o, separando confirmaÃ§Ã£o, proposta e evidÃªncia. |
| D-37 | PadrÃ£o tÃ©cnico local; origem do nome pendente | A CICA definiu o componente de empresa `Nome [DomÃ­nio cÃ³digo]` para cumprir a delegaÃ§Ã£o D-25; o cÃ³digo Ã© obrigatÃ³rio e preservado. A funÃ§Ã£o ainda nÃ£o grava no Windows. | D-25; [padrÃ£o e fonte Microsoft](docs/planejamento/padrao-pastas-windows.md) | Confirmar se o nome vem da CICA ou do DomÃ­nio e o comportamento ao renomear; validar raiz e agente antes de ativar. |
| D-38 | Confirmada em 15/09 | A Central Integra Contador deve ser uma Ã¡rea de trabalho real, comeÃ§ando pela Caixa Postal DTE: localizar por empresa/estado, acompanhar consultas, abrir o teor e registrar a consequÃªncia jurÃ­dica com evidÃªncia na prÃ³pria tela. A mesma revisÃ£o crÃ­tica deve seguir nas demais ferramentas. | pedidos diretos do responsÃ¡vel nesta conversa | Caixa de trabalho, resumo sem efeito jurÃ­dico, confirmaÃ§Ã£o explÃ­cita da abertura, histÃ³rico, falha e prÃ³ximo passo; nÃ£o declarar os outros serviÃ§os da Central como prontos por terem apenas cÃ³digo de integraÃ§Ã£o. |
| D-39 | Confirmada em 15/09 | A ciÃªncia oficial por abertura do DTE Ã© permitida a dono/administrador e a colaborador no perfil **Operador** com permissÃ£o especÃ­fica. | resposta direta do responsÃ¡vel nesta conversa | Gestor, auditor, financeiro e suporte nÃ£o recebem ciÃªncia por permissÃ£o genÃ©rica; a equipe precisa exibir e auditar o privilÃ©gio especÃ­fico. |
| D-40 | Confirmada em 15/09 | A entrada da **Central Integra Contador** deve oferecer exatamente trÃªs ferramentas iniciais para escolha do operador: **Caixa DTE, Parcelamentos e DCTFWeb**. O responsÃ¡vel escolheu DCTFWeb como terceira, substituindo a proposta SITFIS. | respostas diretas do responsÃ¡vel nesta conversa | NavegaÃ§Ã£o pela Central; nenhuma ferramenta pode aparentar consulta Serpro homologada por ter apenas tela ou dados locais. |
| D-41 | Confirmada em 15/09 | Na preparaÃ§Ã£o de consultas DTE, o operador precisa poder selecionar todas as empresas **aptas** do escopo, selecionar os resultados da busca e limpar a seleÃ§Ã£o, vendo a quantidade exata de chamadas Serpro antes de autorizar o envio. | pedido direto do responsÃ¡vel e revisÃ£o da tela com 562 empresas | SeleÃ§Ã£o deve incluir aptas alÃ©m das 20 linhas inicialmente exibidas; empresas sem CNPJ vÃ¡lido nÃ£o podem ser cobradas nem enviadas. Na carteira Fedrizzi sÃ£o 554 aptas e 8 sem CNPJ. O preparo Ã© local e a cobranÃ§a sÃ³ pode seguir a autorizaÃ§Ã£o explÃ­cita. |
| D-42 | Confirmada em 15/09 | A terceira ferramenta inicial, **DCTFWeb**, deve permitir consultar a declaraÃ§Ã£o, obter o recibo e emitir guia. | resposta direta do responsÃ¡vel nesta conversa | TransmissÃ£o nÃ£o faz parte do escopo inicial; `CONSDECCOMPLETA33`, `CONSRECIBO32` e `GERARGUIA31` exigem fluxo operacional e homologaÃ§Ã£o Serpro. |
| D-43 | Confirmada em 15/09 | **Triagem de Arquivos substitui Jornadas em todo o produto.** NÃ£o existem contratos comerciais antigos de Jornadas. | ordem e esclarecimento direto do responsÃ¡vel nesta conversa | Tirar Jornadas de oferta, navegaÃ§Ã£o, catÃ¡logo e rotas do escritÃ³rio; preservar o schema legado sem anunciar ou abrir o quadro. Mensalidade da Triagem precisa de pesquisa e aprovaÃ§Ã£o. |
| D-44 | Confirmada em 15/09 | A cobranÃ§a desejada Ã© **mensalidade mÃ­nima por mÃ³dulo + franquia de tokens prÃ³pria + excedente automÃ¡tico atÃ© teto mensal aceito**. Um token CICA terÃ¡ o **mesmo preÃ§o em todos os mÃ³dulos**, com **consumo apenas em nÃºmeros inteiros**; cada operaÃ§Ã£o queimarÃ¡ um peso diferente conforme custo/trabalho. O responsÃ¡vel rejeitou R$ 0,01 e indicou **R$ 0,05 como referÃªncia a pesquisar**, sem fechar tarifa. | respostas diretas do responsÃ¡vel nesta conversa; [pesquisa](docs/planejamento/precificacao-tokens-modulos.md) | Separar token comercial de token do Claude/Gmail; congelar preÃ§o/pesos/franquia/teto no contrato, reservar e liquidar por resultado, mostrar saldo e fatura por mÃ³dulo. Valor final em R$ e pesos ainda nÃ£o aprovados. |
| D-45 | Confirmada em 15/09 | Os pesos das operaÃ§Ãµes **Integra Contador** devem sempre partir da **faixa mais cara vigente do Serpro** para cada serviÃ§o. Faixas mais baratas alcanÃ§adas depois pela Mewstack ampliam sua margem, sem reduÃ§Ã£o automÃ¡tica do peso vendido ao escritÃ³rio. | resposta direta do responsÃ¡vel nesta conversa; [tabela oficial](https://loja.serpro.gov.br/integra-contador/product/integracontador), aba â€œPreÃ§oâ€ | A tabela oficial lida em 15/09 mostra **faixa 1: consulta R$ 0,24, emissÃ£o R$ 0,32 e declaraÃ§Ã£o R$ 0,40**. Confirmar a categoria de cada cÃ³digo DTE/Parcelamentos/DCTFWeb antes de fixar peso por aÃ§Ã£o. |

## DecisÃµes que nÃ£o foram tomadas

Este registro nÃ£o aprova **valor monetÃ¡rio do token, preÃ§os mÃ­nimos, pesos, franquias e teto padrÃ£o por mÃ³dulo**, gasto de API, provedor SMTP, DNS de envio, retenÃ§Ã£o/exportaÃ§Ã£o pÃ³s-contrato, termos finais, **custos e contrataÃ§Ã£o da verificaÃ§Ã£o Gmail pessoal**, catÃ¡logo documental de 19 tipos, caminhos Windows concretos, antimalware/OCR, provedor WhatsApp, integraÃ§Ã£o automÃ¡tica BCB/RFB ou mÃ³dulo â€œOpen Filesâ€ do DomÃ­nio. Ver [dÃºvidas abertas](docs/planejamento/duvidas-abertas.md).


## DecisÃµes confirmadas em 17/09/2026

ResponsÃ¡vel: proprietÃ¡rio do projeto nesta conversa. Fonte: respostas e instruÃ§Ãµes diretas, seguidas da aprovaÃ§Ã£o do plano e da restriÃ§Ã£o Ã  etapa 00.

| ID | Assunto | DecisÃ£o | Fonte | Alcance / efeito |
|---|---|---|---|---|
| D-46 | Arquitetura | SaaS e IA centralizados na Mewstack; agente instalado no escritÃ³rio. | Resposta â€œSaaS + IA centralâ€. | InstalaÃ§Ã£o completa no cliente nÃ£o integra este plano; documentos Cobalchini nÃ£o escolhem produÃ§Ã£o. |
| D-47 | IA inicial | Uso por API KEY agora; preservar Claude conforme D-16. | Pedido inicial e plano aprovado. | AprovaÃ§Ã£o de arquitetura nÃ£o autoriza gasto nem fixa modelo comercial disponÃ­vel. |
| D-48 | IA local | Consulta aos dados + ajuste do modelo com exemplos revisados. | Resposta â€œConsulta + ajuste do modeloâ€. | NÃ£o Ã© treinamento de modelo do zero; preparar corpus, avaliaÃ§Ã£o e publicaÃ§Ã£o. |
| D-49 | Isolamento do aprendizado | Conhecimento, exemplos, correÃ§Ãµes e ajustes derivados dos clientes ficam restritos ao respectivo escritÃ³rio; conhecimento geral pode ser compartilhado. | Resposta â€œRestrito por escritÃ³rioâ€. | NÃ£o alimentar modelo comum com exemplos privados sem nova decisÃ£o explÃ­cita. |
| D-50 | API apÃ³s migraÃ§Ã£o | IA local como padrÃ£o apÃ³s homologaÃ§Ã£o; API como reserva autorizada, sujeita Ã  polÃ­tica de dados e orÃ§amento. | Resposta â€œReserva autorizadaâ€. | Resolve a escolha de rota da Q-10; critÃ©rios de virada ficam em Q-30. |
| D-51 | Aceite local para venda inicial | Pipeline local preparado e testado; treinamento e desempenho na mÃ¡quina definitiva ficam para etapa posterior explÃ­cita. | Resposta â€œPipeline pronto e testadoâ€. | Etapa 13 nÃ£o bloqueia venda por API; etapa 05 continua obrigatÃ³ria e nÃ£o equivale a treino real. |
| D-52 | Ãreas do DomÃ­nio | ContÃ¡bil, fiscal e folha na preparaÃ§Ã£o da IA. | Resposta â€œContÃ¡bil + fiscal + folhaâ€. | NÃ£o reduzir cobertura aos quatro grupos hoje consultados; nÃ£o autoriza escrita no ERP. |
| D-53 | Disponibilidade Siescon | ResponsÃ¡vel confirmou servidor/banco disponÃ­vel para viabilizar descoberta autorizada. | Resposta â€œServidor/banco disponÃ­velâ€. | NÃ£o prova acesso jÃ¡ concedido, schema, versÃ£o, credenciais recebidas ou homologaÃ§Ã£o. |
| D-54 | OperaÃ§Ãµes Siescon | Leitura + exportaÃ§Ã£o revisada; gravaÃ§Ã£o direta nÃ£o aprovada. | Resposta â€œLeitura + exportaÃ§Ã£o revisadaâ€. | Homologar leitura e importaÃ§Ã£o do arquivo no Siescon; nÃ£o inventar layout/API. |
| D-55 | Autonomia | AutomaÃ§Ã£o por regras aprovadas e qualidade medida; exceÃ§Ãµes seguem para revisÃ£o. | Resposta â€œAutomaÃ§Ã£o por regras aprovadasâ€. | NÃ£o aprova limiares especÃ­ficos, autoaprovaÃ§Ã£o irrestrita ou ciÃªncia DTE automÃ¡tica. |
| D-56 | Sem presunÃ§Ãµes | â€œnunca assume nada, o que for preciso tu me pergunta aquiâ€. | Mensagem direta do responsÃ¡vel. | Consultar evidÃªncia existente; perguntar apenas decisÃ£o ausente/conflito concreto. |
| D-57 | MemÃ³ria e execuÃ§Ã£o | Documentar tudo que for decidido; criar etapas para terminar o projeto e um prompt por etapa. | Mensagem direta e aprovaÃ§Ã£o integral do plano. | Registro Ãºnico; atualizar documentaÃ§Ã£o junto da implementaÃ§Ã£o; nÃ£o reabrir decisÃµes sem motivo. |
| D-58 | Plano aprovado | Plano de conclusÃ£o composto pelas etapas 00â€“13, com dependÃªncias e aceites registrados em PLANO-MESTRE.md. | Mensagem â€œPLEASE IMPLEMENT THIS PLANâ€ com plano integral. | Preservar todas as etapas, sem declarar o conjunto implementado. |
| D-59 | LocalizaÃ§Ã£o da memÃ³ria | Plano mestre e tudo que for validado devem ficar na raiz do repositÃ³rio. | Mensagem â€œcola na raiz do repoâ€. | PLANO-MESTRE.md, DECISOES.md e VALIDACOES.md sÃ£o os pontos de entrada; caminhos antigos apontam para eles. |
| D-60 | Escopo desta execuÃ§Ã£o | â€œquero que tu faÃ§a apenas a primeira etapa agoraâ€. | Ãšltima instruÃ§Ã£o do responsÃ¡vel em 17/09/2026. | Executar somente 00, primeira etapa do plano; nÃ£o corrigir Ruff nem iniciar 01â€“13 nesta entrega. |
| D-61 | Fechamento de etapas | â€œnunca finaliza uma etapa se tiver algo pendente, me pede que eu faÃ§oâ€. | Mensagem direta do responsÃ¡vel em 17/09/2026. | Etapa com qualquer checklist, validaÃ§Ã£o ou dependÃªncia pendente fica aberta e bloqueada; comunicar a aÃ§Ã£o concreta exigida do responsÃ¡vel antes de encerrÃ¡-la. |
| D-62 | DemonstraÃ§Ã£o de download NFS-e | A Ã¡rea NFS-e deve oferecer download em lote para demonstraÃ§Ã£o, separado por empresa no padrÃ£o de pastas DomÃ­nio: `Tomadas/CÃ“DIGO -/` e `Emitidas/CÃ“DIGO -/`. | Pedido direto do responsÃ¡vel em 18/09/2026, com correÃ§Ã£o posterior de â€œrecebidasâ€ para â€œemitidasâ€. | Implementar primeiro somente demonstraÃ§Ã£o com dados fictÃ­cios e ZIP gerado sob demanda; nÃ£o alegar escrita real nas pastas Windows, coleta ADN nem homologaÃ§Ã£o do layout final. |
| D-63 | ClassificaÃ§Ã£o antes do download NFS-e | A demonstraÃ§Ã£o deve permitir baixar todas as notas, editar ou definir acumulador antes do ZIP e tratar transitÃ³ria com confianÃ§a zero. Toda nota classificada exige confianÃ§a superior a 95%. | Pedido direto do responsÃ¡vel em 18/09/2026. | Aplicar as regras no servidor para o ZIP de demonstraÃ§Ã£o; usar manifesto no arquivo baixado e nÃ£o gravar decisÃ£o fictÃ­cia no banco nem alegar classificaÃ§Ã£o fiscal homologada. |

## Como registrar a prÃ³xima decisÃ£o

18/09/2026 â€” D-70: responsÃ¡vel solicitou â€œfaz o prÃ³ximo passo do planoâ€ apÃ³s os ajustes da demo. Retomar o primeiro item pendente do plano (etapa 01), preservando D-61: nÃ£o encerrar com pendÃªncias. A restriÃ§Ã£o temporÃ¡ria de D-67 deixa de impedir essa retomada. O questionamento anterior sobre LlamaFactory nÃ£o autoriza sua substituiÃ§Ã£o nem confirma sua adoÃ§Ã£o; esclarecer Q-37 antes do build dependente.

18/09/2026 â€” D-71: diante de â€œfaz o que for melhor pra tiâ€, manter LlamaFactory como ferramenta interna do runtime de ajuste local. A seleÃ§Ã£o tÃ©cnica Ã© `hiyouga/llamafactory@sha256:46b6969e444681829294ed1fce2c4e8848613e654b682dc0359ba94357a0267b`, imagem oficial fixada por digest. O runtime Ã© somente de treinamento, sem porta exposta, credenciais, modelo baixado ou treino executado. Isso resolve Q-37 e nÃ£o altera a IA inicial por API nem autoriza GPU, API paga ou egressÃ£o de dados.

18/09/2026 â€” D-72: Fedrizzi Contabilidade Ã© o ambiente disponÃ­vel para homologaÃ§Ã£o; tudo nele estÃ¡ disponÃ­vel para esse fim. O proprietÃ¡rio do projeto aprova cada mÃ³dulo. Os acessos e amostras concretos serÃ£o solicitados e usados somente na etapa correspondente, por meio seguro, sem credenciais no chat. Isto resolve a disponibilidade de ambiente em Q-28 e o responsÃ¡vel pelo aceite em Q-30; nÃ£o define mÃ©tricas, tamanho de amostra, janelas de operaÃ§Ã£o nem autoriza chamadas cobradas.

18/09/2026 â€” D-73: aprovados os critÃ©rios recomendados de liberaÃ§Ã£o por mÃ³dulo. Cada fluxo automatizado terÃ¡ amostra de 200 itens revisados pelo proprietÃ¡rio; classificaÃ§Ã£o automÃ¡tica exige precisÃ£o medida mÃ­nima de 95%; sincronizaÃ§Ã£o e dados exigem zero duplicidade, associaÃ§Ã£o Ã  empresa errada ou vazamento entre escritÃ³rios; apÃ³s queda de rede, worker ou agente, retomada sem perda em atÃ© 15 minutos; restauraÃ§Ã£o de banco e documentos conferida em atÃ© 4 horas; consultas/processamentos por empresa em atÃ© 5 minutos, salvo dependÃªncia externa registrada; exportaÃ§Ã£o sÃ³ Ã© aprovada apÃ³s importaÃ§Ã£o e conferÃªncia no sistema de destino. A disponibilidade Fedrizzi permanece em D-72; cada chamada cobrada requer autorizaÃ§Ã£o especÃ­fica imediatamente antes.

18/09/2026 â€” D-74: confirmado no ambiente local que Fedrizzi jÃ¡ possui conector DomÃ­nio `direct_odbc` e fonte DomÃ­nio local em estado `ready`; a sincronizaÃ§Ã£o jÃ¡ estÃ¡ configurada. NÃ£o solicitar novamente DSN, driver, servidor ou acesso para esse conector. A etapa 03 deve usar essa conexÃ£o existente para sua homologaÃ§Ã£o, sem expor o DSN ou seus dados. A disponibilidade de outros conectores em Q-28 serÃ¡ tratada somente nas respectivas etapas.

18/09/2026 â€” D-75: diante de qualquer pendÃªncia, o executor deve apresentar proativamente o que precisa ser decidido ou disponibilizado, o impacto, uma recomendaÃ§Ã£o objetiva e como o responsÃ¡vel pode executar ou fornecer o necessÃ¡rio. NÃ£o encerrar a comunicaÃ§Ã£o apenas informando o bloqueio. Registrar a resposta recebida antes de implementar o comportamento dependente.

18/09/2026 â€” D-76: todas as regras, recomendaÃ§Ãµes e propostas jÃ¡ documentadas no repositÃ³rio passam a ser aprovadas para implementaÃ§Ã£o; nÃ£o reabrir itens apenas por estarem identificados como pendentes ou propostos. Quando um documento contiver somente uma pergunta sem valor, regra ou alternativa definida, levantar o fato tÃ©cnico e trazer recomendaÃ§Ã£o conforme D-75. Esta decisÃ£o nÃ£o autoriza gasto, contrataÃ§Ã£o, chamada cobrada ou publicaÃ§Ã£o externa, que continuam exigindo confirmaÃ§Ã£o especÃ­fica. O e-mail de suporte oficial Ã© `suporte@mewstack.com.br`.

18/09/2026 â€” D-77: configuraÃ§Ã£o de SMTP, domÃ­nio/DNS de envio e homologaÃ§Ã£o de entrega transacional ficam para a etapa 12, depois de existir ambiente de produÃ§Ã£o. Nesta fase, concluir somente templates, transporte configurÃ¡vel, testes locais e estados de falha; nÃ£o pedir configuraÃ§Ã£o SMTP nem antecipar envio externo.

18/09/2026 â€” D-78: Brevo serÃ¡ o provedor de e-mail transacional da CICA via SMTP. Configurar host, porta, credencial SMTP, remetente e autenticaÃ§Ãµes do domÃ­nio somente na etapa 12, conforme D-77. NÃ£o criar conta, plano, crÃ©dito, campanha ou envio por esta decisÃ£o.

18/09/2026 â€” D-79: regras comerciais de acesso aprovadas conforme recomendaÃ§Ãµes apresentadas e D-76. ApÃ³s atraso confirmado, hÃ¡ 7 dias de carÃªncia; depois, somente leitura. Pagamento confirmado reativa acesso automaticamente; estorno ou disputa retorna a somente leitura. Somente leitura mantÃ©m consulta, documentos jÃ¡ arquivados, auditoria e exportaÃ§Ã£o de dados prÃ³prios, bloqueando novas sincronizaÃ§Ãµes, IA, downloads em lote novos, Serpro e consumo de tokens. Contrato manual Ã© operado por Comercial ou Administrador Mewstack, com motivo e comprovante auditÃ¡veis. CompetÃªncia fecha no dia 1, vencimento no dia 10; primeiro mÃªs Ã© proporcional e mudanÃ§a de plano vale no prÃ³ximo ciclo. Teste Ã© de 14 dias, sem cartÃ£o e sem reinÃ­cio por convite; contrato manual tambÃ©m pode usar o mesmo teste. PreÃ§os, franquias, pesos e tetos usam a tabela documental aprovada por D-76 e serÃ£o operacionalizados na etapa 10.

18/09/2026 â€” D-80: arquitetura definitiva recomendada e aprovada para o pacote Windows, conforme D-76. O serviÃ§o nativo .NET passa a ser o Ãºnico serviÃ§o instalado e suportado: ele executarÃ¡ sincronizaÃ§Ã£o DomÃ­nio Local somente leitura, processamento de backup DomÃ­nio Web e arquivamento Windows. O agente Python permanece apenas como ferramenta de diagnÃ³stico/migraÃ§Ã£o temporÃ¡ria, sem nova instalaÃ§Ã£o de produÃ§Ã£o. O pacote e as telas deixam a marca CICA e passam a CICA. A sincronizaÃ§Ã£o local deve usar consultas allowlisted, paginaÃ§Ã£o/chave incremental e a API v2 autenticada por mTLS/HMAC; nunca SQL recebido remotamente ou escrita no banco DomÃ­nio. A decisÃ£o substitui a indecisÃ£o Q-32; a execuÃ§Ã£o e homologaÃ§Ã£o continuam na etapa 03.

18/09/2026 â€” D-69: responsÃ¡vel pediu pesquisar e simplificar a seleÃ§Ã£o de datas na demo. SoluÃ§Ã£o de interface: digitaÃ§Ã£o brasileira DD/MM/AAAA e atalhos de mÃªs, preservando D-66 (competÃªncia ou emissÃ£o). Trata-se de escolha de implementaÃ§Ã£o, nÃ£o de nova regra fiscal.

| D-64 | Filtros da carteira NFS-e | A carteira deve filtrar por competÃªncia de emissÃ£o ou por intervalo de data de emissÃ£o; data de captura nÃ£o Ã© o filtro de trabalho nem a data principal da lista. O aviso tÃ©cnico sobre XML fictÃ­cio e pasta Windows deve sair da tela. | Pedido direto do responsÃ¡vel em 18/09/2026. | A competÃªncia Ã© derivada da data de emissÃ£o enquanto nÃ£o existir campo fiscal prÃ³prio homologado; nÃ£o usar data de captura para filtrar. |
| D-65 | Download sem bloqueio na demonstraÃ§Ã£o | O download de demonstraÃ§Ã£o nÃ£o deve bloquear o usuÃ¡rio. Nota sem acumulador entra como TransitÃ³ria com confianÃ§a 0%; acumulador definido pelo contador entra no manifesto como decisÃ£o manual. Somente sugestÃ£o da IA com confianÃ§a acima de 95% aparece como classificaÃ§Ã£o da IA. | Esclarecimento direto do responsÃ¡vel em 18/09/2026. | O manifesto distingue origem e confianÃ§a sem gravar a decisÃ£o fictÃ­cia no banco. |
| D-66 | Escolha do filtro NFS-e | Na demonstraÃ§Ã£o, o usuÃ¡rio escolhe um Ãºnico critÃ©rio de perÃ­odo: competÃªncia de emissÃ£o ou intervalo de data de emissÃ£o. | Pedido direto do responsÃ¡vel em 18/09/2026. | A interface nÃ£o combina os dois filtros; o critÃ©rio inativo nÃ£o restringe a carteira. |
| D-67 | Prioridade atual | A entrega atual fica limitada Ã  demonstraÃ§Ã£o NFS-e; os demais trabalhos serÃ£o retomados depois. | Pedido direto do responsÃ¡vel em 18/09/2026. | NÃ£o avanÃ§ar etapas ou integraÃ§Ãµes fora da demonstraÃ§Ã£o enquanto esta estiver sendo ajustada. |
| D-68 | EdiÃ§Ã£o de acumulador na demonstraÃ§Ã£o | Preencher o acumulador deve mudar imediatamente a linha para Classificada e identificar a decisÃ£o manual com confianÃ§a de 100%; limpar o campo restaura o estado exibido antes da ediÃ§Ã£o. | Pedido direto do responsÃ¡vel em 18/09/2026. | O efeito Ã© visual e entra no manifesto do ZIP; nÃ£o persiste classificaÃ§Ã£o fiscal fictÃ­cia. |

Acrescentar ID Ãºnico, data, texto da escolha, responsÃ¡vel, fonte, etapa afetada, decisÃµes substituÃ­das e pendÃªncias restantes. Registrar antes de executar o comportamento dependente. Nunca copiar credenciais, certificados, dados de clientes ou conteÃºdo integral de conversas. Uma mudanÃ§a de escopo posterior nÃ£o reescreve silenciosamente o histÃ³rico. Custos exigem autorizaÃ§Ã£o especÃ­fica imediatamente antes da aÃ§Ã£o.
18/09/2026 â€” D-81: toda dependÃªncia de site hospedado fica para a etapa 12: domÃ­nio pÃºblico, HTTPS, certificado/CA do agente, DNS, SMTP real, pareamento externo e homologaÃ§Ã£o contra produÃ§Ã£o. Antes disso, executar somente implementaÃ§Ã£o, builds e validaÃ§Ãµes locais, sem solicitar hospedagem antecipada.
18/09/2026 â€” D-82: a API oficial DomÃ­nio/Onvio passa a ser o caminho preferencial de integraÃ§Ã£o. O backup DomÃ­nio Web permanece como contingÃªncia e sua homologaÃ§Ã£o fica na etapa 12, junto do ambiente hospedado. A CICA implementarÃ¡ somente endpoints e escopos documentados e concedidos pela Thomson Reuters; nÃ£o simularÃ¡ leitura de contabilidade, fiscal ou folha como se fosse disponÃ­vel na API pÃºblica. Enquanto a API oficial nÃ£o conceder esses recursos, a leitura local autorizada do agente ODBC permanece necessÃ¡ria para essas Ã¡reas.

18/09/2026 â€” D-83: as limitaÃ§Ãµes e capacidades da integraÃ§Ã£o DomÃ­nio Web devem permanecer consolidadas em `docs/dominio-web-limitacoes-comerciais.md`, como fonte para a oferta e o site. A comunicaÃ§Ã£o comercial deve distinguir API oficial, agente local e backup de contingÃªncia, sem prometer leitura completa ou sincronizaÃ§Ã£o automÃ¡tica do DomÃ­nio Web onde a documentaÃ§Ã£o e a homologaÃ§Ã£o nÃ£o comprovarem isso. Esta decisÃ£o nÃ£o altera D-82 nem libera publicaÃ§Ã£o externa antes da etapa 12.
## D-84 â€” Destino Windows configurÃ¡vel por escritÃ³rio

Data: 18/09/2026. Origem: responsÃ¡vel pelo projeto. Cada escritÃ³rio define dentro da CICA a raiz Windows e seu formato de pastas para documentos aprovados. O formato usa somente variÃ¡veis controladas e pode conter subpastas. O serviÃ§o nÃ£o usa unidades mapeadas; nesta fase a raiz deve ser um caminho local absoluto. UNC depende de conta de serviÃ§o e homologaÃ§Ã£o especÃ­fica antes de ser liberado. Cada trabalho guarda o destino relativo jÃ¡ resolvido, preservando a fila quando a configuraÃ§Ã£o futura mudar.
## D-85 â€” Site como fonte de verdade do destino Windows

Data: 18/09/2026. Origem: responsÃ¡vel pelo projeto, ao exigir configuraÃ§Ã£o por escritÃ³rio dentro do site. A raiz e o formato de pastas sÃ£o definidos pelo administrador no perfil do escritÃ³rio. O agente pareado consulta somente essa configuraÃ§Ã£o do seu escritÃ³rio e atualiza a cÃ³pia DPAPI local. Nesta fase, aceitar somente caminhos locais absolutos; suporte a UNC fica para homologaÃ§Ã£o posterior com conta de serviÃ§o e permissÃµes explÃ­citas.

## D-86 â€” HomologaÃ§Ã£o operacional do agente no final

Data: 18/09/2026. Origem: responsÃ¡vel pelo projeto. A etapa 03 encerra a implementaÃ§Ã£o e as validaÃ§Ãµes locais do agente Windows e da integraÃ§Ã£o DomÃ­nio. A execuÃ§Ã£o no destino definitivo â€” instalaÃ§Ã£o limpa com DSN/driver x64, pareamento HTTPS/mTLS, revogaÃ§Ã£o, atualizaÃ§Ã£o distribuÃ­da, queda e retomada de rede, backup `.dom` autorizado e escrita documental na raiz Windows real â€” fica reunida na etapa 12, depois do deploy do site. Q-22 e Q-31 serÃ£o respondidas no contexto desse piloto; nÃ£o antecipar caminho, conta de serviÃ§o, polÃ­tica de nome ou renomeaÃ§Ã£o de pastas. Esta decisÃ£o complementa D-81/D-82 e nÃ£o libera publicaÃ§Ã£o, infraestrutura paga ou homologaÃ§Ã£o comercial.

## D-87 â€” DependÃªncias de produÃ§Ã£o concentradas na etapa final

Data: 18/09/2026. Origem: responsÃ¡vel pelo projeto. Toda atividade que dependa do site em produÃ§Ã£o fica para a etapa 12: deploy, domÃ­nio pÃºblico, HTTPS/DNS, credenciais e consentimentos externos de produÃ§Ã£o, serviÃ§os hospedados, filas e storage implantados, pareamento de agentes, chamadas reais a provedores, pilotos com dados reais e homologaÃ§Ã£o comercial. As etapas 01â€“11 devem concluir cÃ³digo, configuraÃ§Ã£o sem segredos, testes locais/isolados, documentaÃ§Ã£o e preparaÃ§Ã£o dos fluxos. A transferÃªncia nÃ£o autoriza criar infraestrutura, fazer chamadas cobradas, usar dados reais ou publicar o site; cada custo continua a exigir confirmaÃ§Ã£o especÃ­fica imediatamente antes.

## D-88 â€” Contrato comum de exportaÃ§Ã£o contÃ¡bil

Data: 18/09/2026. Origem: executor, autorizado como decisÃ£o de implementaÃ§Ã£o por D-76. As exportaÃ§Ãµes contÃ¡beis da CICA passam a escolher um destino registrado e versionado, em vez de presumir DomÃ­nio em toda a cadeia. O adaptador DomÃ­nio jÃ¡ existente Ã© preservado. Siescon sÃ³ poderÃ¡ receber exportaÃ§Ã£o apÃ³s registrar seu layout revisado, adaptador e versÃ£o; atÃ© lÃ¡ a solicitaÃ§Ã£o Ã© recusada de forma explÃ­cita, sem gerar arquivo, escrever no Siescon ou alegar compatibilidade. Isto implementa a generalizaÃ§Ã£o estrutural da etapa 04 sem inventar o contrato tÃ©cnico de Q-33.

## D-89 â€” Metadados de escopo para conhecimento e treinamento

Data: 19/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o autorizada por D-52 e D-76. Fontes de conhecimento e exemplos de treinamento passam a registrar, quando aplicÃ¡vel, empresa, perÃ­odo de referÃªncia e uma das Ã¡reas `contÃ¡bil`, `fiscal`, `folha` ou `geral`. Registros existentes recebem o escopo geral e nÃ£o sÃ£o reenviados, reclassificados ou expostos. Uma fonte ligada a empresa sÃ³ pode pertencer ao mesmo escritÃ³rio; na recuperaÃ§Ã£o de uma conversa por empresa, evidÃªncia daquela empresa tem precedÃªncia e nunca Ã© recuperada para outra. Esta decisÃ£o estrutura o pipeline local da etapa 05 sem aprovar egressÃ£o, curadoria, teto, treinamento real ou publicaÃ§Ã£o de modelo; Q-08, Q-09, Q-11 e Q-34 continuam abertos.

## D-90 â€” ProveniÃªncia de avaliaÃ§Ã£o e adaptador local

Data: 19/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o autorizada por D-48, D-51 e D-76. Quando uma versÃ£o local declarar um adaptador, ela deve registrar modelo base, versÃ£o do adaptador, hash SHA-256 do artefato e hash SHA-256 do manifesto/corpus. A avaliaÃ§Ã£o correspondente deve registrar os mesmos valores, e a publicaÃ§Ã£o recusa divergÃªncia. Registros histÃ³ricos sem artefato continuam legÃ­veis, mas nÃ£o passam a alegar vÃ­nculo que nÃ£o possuÃ­am. A decisÃ£o cria somente o gate e a rastreabilidade local; nÃ£o seleciona modelo, nÃ£o inicia treino, nÃ£o publica artefato nem substitui a aprovaÃ§Ã£o humana de Q-34.

## D-91 â€” SeparaÃ§Ã£o imutÃ¡vel entre treino e avaliaÃ§Ã£o

Data: 19/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o autorizada por D-48, D-51 e D-76. Cada exemplo validado passa a ser classificado como `treino` ou `avaliaÃ§Ã£o`; um exemplo nÃ£o integra ambos os manifestos. Os registros anteriores permanecem no conjunto de treino para preservar o comportamento jÃ¡ existente. O job QLoRA exporta apenas o manifesto de treino; a avaliaÃ§Ã£o deve registrar o hash do manifesto de avaliaÃ§Ã£o quando houver artefato local declarado. A escolha, revisÃ£o humana e quantidade de exemplos de cada conjunto continuam dependentes de Q-34 e das mÃ©tricas de D-73. Nenhum exemplo Ã© reenviado, usado em treino ou avaliado por esta decisÃ£o.

## D-92 â€” Retorno controlado de adaptador local

Data: 19/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o autorizada por D-50, D-51 e D-76. O retorno de versÃ£o ativa deve escolher uma versÃ£o anterior do mesmo escritÃ³rio que tenha avaliaÃ§Ã£o aprovada, corpus compatÃ­vel e, quando declarar artefato, proveniÃªncia completa e idÃªntica. O retorno Ã© auditado e nÃ£o reexecuta treinamento, egressÃ£o ou download; a comparaÃ§Ã£o de melhoria usada para publicaÃ§Ã£o de uma versÃ£o nova nÃ£o impede retornar a uma versÃ£o jÃ¡ aprovada. Esta decisÃ£o prepara o mecanismo local e nÃ£o aprova a mudanÃ§a de rota para IA local, que continua dependente da etapa 13, Q-30 e Q-34.

## D-93 â€” Cliente Asaas local, sem configuraÃ§Ã£o nem despacho

Data: 19/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o autorizada por
D-11, D-76 e D-87. O cliente tÃ©cnico da Asaas usa explicitamente os ambientes
`sandbox` e `production`, o cabeÃ§alho `access_token`, `externalReference` para
localizar clientes antes de criÃ¡-los e cobranÃ§a avulsa sem dados de cartÃ£o. A
chave Ã© sempre recebida por injeÃ§Ã£o explÃ­cita; nÃ£o serÃ¡ lida de configuraÃ§Ã£o
local, impressa, criada ou usada nesta etapa. O transporte deve ser substituÃ­vel
nos testes e nÃ£o repetir automaticamente `POST` de cliente ou cobranÃ§a apÃ³s
falha/resultado incerto. A ligaÃ§Ã£o entre dados comerciais do escritÃ³rio,
cliente Asaas, `PaymentAttempt` e ambiente autorizado continua para a etapa 12,
Q-08 e Q-28. Fontes: [autenticaÃ§Ã£o Asaas](https://docs.asaas.com/docs/authentication),
[criar cliente](https://docs.asaas.com/reference/create-new-customer) e
[criar cobranÃ§a](https://docs.asaas.com/reference/create-new-payment), consultadas
em 19/09/2026. Esta decisÃ£o nÃ£o autoriza chamada, custo, sandbox, produÃ§Ã£o ou
homologaÃ§Ã£o.

## D-94 â€” Gate antecipado de identificadores pessoais no corpus local

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o autorizada por
D-20, D-48, D-49, D-51 e D-76. Um exemplo de treino ou avaliaÃ§Ã£o validado nÃ£o
pode entrar no manifesto local quando pergunta, resposta ou referÃªncias
contiverem CPF, CNPJ ou e-mail reconhecÃ­veis pelos mesmos padrÃµes jÃ¡ recusados
pelo runner QLoRA. A exportaÃ§Ã£o deve falhar antes de criar o artefato; nÃ£o deve
alterar, mascarar ou reenviar o registro automaticamente, pois isso poderia
corromper evidÃªncia contÃ¡bil. A anonimizaÃ§Ã£o permanece uma revisÃ£o humana
rastreÃ¡vel no registro de origem. A decisÃ£o antecipa um controle local de
privacidade e nÃ£o autoriza curadoria Claude, egressÃ£o, treinamento, download de
modelo, publicaÃ§Ã£o, dado de cliente ou custo. Q-08, Q-09, Q-11 e Q-34
continuam abertos.

## D-95 â€” ExportaÃ§Ã£o de manifesto local sem sobrescrita

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o autorizada por
D-48, D-51 e D-76. A exportaÃ§Ã£o JSONL de treino ou avaliaÃ§Ã£o deve recusar um
caminho de saÃ­da jÃ¡ existente e criar o novo arquivo exclusivamente, evitando
substituir silenciosamente um artefato que possa estar vinculado a uma avaliaÃ§Ã£o
ou revisÃ£o. A regra vale apenas para o artefato local; nÃ£o executa treino,
publicaÃ§Ã£o, transferÃªncia de dados ou operaÃ§Ã£o externa. Uma nova exportaÃ§Ã£o usa
outro caminho depois de revisÃ£o humana do corpus.

## D-96 â€” Cobertura de certificados sem ocultaÃ§Ã£o da carteira

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelas mÃ©tricas de recuperaÃ§Ã£o de D-73. Quando a tela de
certificados informar empresas ativas sem A1 vÃ¡lido, ela deve permitir percorrer
toda a carteira em pÃ¡ginas de 20 registros, em vez de mostrar apenas as 20
primeiras. A paginaÃ§Ã£o da cobertura Ã© independente da lista de certificados e
preserva os parÃ¢metros jÃ¡ presentes na consulta; o seletor de demonstraÃ§Ã£o usa
somente os itens visÃ­veis nessa pÃ¡gina. Esta decisÃ£o evita ocultaÃ§Ã£o silenciosa
e nÃ£o aprova certificado, coleta ADN, uso de A1 real, conexÃ£o externa, custo ou
homologaÃ§Ã£o fiscal.

## D-97 â€” Ficha da empresa com histÃ³ricos paginados por seÃ§Ã£o

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelas mÃ©tricas de recuperaÃ§Ã£o de D-73. A ficha de uma empresa deve
permitir percorrer todos os documentos NFS-e, revisÃµes abertas e mensagens DTE
visÃ­veis ao escritÃ³rio. Cada seÃ§Ã£o usa sua prÃ³pria pÃ¡gina de 20 registros, sem
alterar as demais seÃ§Ãµes ou o parÃ¢metro de retorno Ã  carteira. Esta decisÃ£o
remove limites silenciosos de apresentaÃ§Ã£o; nÃ£o amplia permissÃµes, nÃ£o autoriza
consulta DTE, coleta ADN, certificado real, conexÃ£o externa, custo ou
homologaÃ§Ã£o.

## D-98 â€” Auditoria de conciliaÃ§Ã£o sem limite silencioso

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelas mÃ©tricas de rastreabilidade de D-73. A auditoria de
conciliaÃ§Ã£o deve permitir percorrer todos os eventos visÃ­veis ao perfil jÃ¡
autorizado em pÃ¡ginas de 100 registros, preservando o filtro de aÃ§Ã£o. A medida
Ã© somente de apresentaÃ§Ã£o e consulta: nÃ£o altera o conteÃºdo imutÃ¡vel do evento,
permissÃµes, arquivos financeiros, integraÃ§Ãµes, exportaÃ§Ãµes, custo ou
homologaÃ§Ã£o.

## D-99 â€” Radar da Reforma sem corte silencioso de alertas

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelas mÃ©tricas de recuperaÃ§Ã£o de D-73. A consulta do Radar deve
permitir percorrer todos os alertas de reforma e fiscal jÃ¡ visÃ­veis ao
escritÃ³rio, em pÃ¡ginas de 50 registros, preservando busca, fonte e tema. A
medida somente altera a apresentaÃ§Ã£o da coleÃ§Ã£o local: nÃ£o coleta fontes,
nÃ£o valida publicaÃ§Ã£o, nÃ£o muda sua relevÃ¢ncia, nÃ£o abre URLs, nÃ£o autoriza
integraÃ§Ã£o, custo ou homologaÃ§Ã£o.

## D-100 â€” HistÃ³rico de cobranÃ§a manual recuperÃ¡vel no console

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelas mÃ©tricas de rastreabilidade de D-73. O console da plataforma
deve permitir percorrer todas as faturas jÃ¡ pertencentes ao escritÃ³rio, em
pÃ¡ginas de 12 registros, em vez de limitar a exibiÃ§Ã£o Ã s 12 mais recentes. A
medida mantÃ©m o escopo de cada escritÃ³rio e somente apresenta o histÃ³rico jÃ¡
registrado: nÃ£o cria cobranÃ§a, nÃ£o altera valores, contratos, status,
integraÃ§Ãµes, credenciais, custo ou homologaÃ§Ã£o Asaas.

## D-101 â€” HistÃ³rico DTE recuperÃ¡vel por pÃ¡gina prÃ³pria

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelas mÃ©tricas de rastreabilidade de D-73. O histÃ³rico de resultados
das consultas DTE deve permitir percorrer todos os itens visÃ­veis ao escritÃ³rio
em pÃ¡ginas de 30 registros, sem interferir na paginaÃ§Ã£o das mensagens DTE e
preservando os parÃ¢metros correntes da tela. A medida somente apresenta o
histÃ³rico local jÃ¡ registrado: nÃ£o prepara consulta, nÃ£o autoriza consumo, nÃ£o
chama Serpro, nÃ£o altera resultado, permissÃ£o, cobranÃ§a, custo ou homologaÃ§Ã£o.

## D-102 â€” HistÃ³rico de importaÃ§Ãµes recuperÃ¡vel no onboarding

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelas mÃ©tricas de rastreabilidade de D-73. O onboarding deve permitir
percorrer todos os lotes de importaÃ§Ã£o jÃ¡ pertencentes ao escritÃ³rio, em pÃ¡ginas
de 20 registros, em vez de exibir somente os oito mais recentes. A medida
preserva fonte e prÃ©via selecionadas na navegaÃ§Ã£o e somente apresenta histÃ³rico
local jÃ¡ registrado: nÃ£o envia arquivo, nÃ£o confirma lote, nÃ£o altera dados,
permissÃ£o, integraÃ§Ã£o, custo ou homologaÃ§Ã£o DomÃ­nio.

## D-103 â€” Trilhas de processamento e exportaÃ§Ã£o recuperÃ¡veis na ConciliaÃ§Ã£o

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelas mÃ©tricas de rastreabilidade de D-73. A ConciliaÃ§Ã£o deve permitir
percorrer todos os processamentos e exportaÃ§Ãµes jÃ¡ visÃ­veis ao escritÃ³rio, em
pÃ¡ginas independentes de 20 registros, em vez de limitar cada trilha aos 12 e 8
mais recentes. Cada navegaÃ§Ã£o preserva os parÃ¢metros correntes da tela e nÃ£o
altera a outra trilha. A medida somente apresenta o histÃ³rico local existente:
nÃ£o importa, reprocessa, exporta, baixa arquivo, chama ERP, altera permissÃµes,
custo ou homologaÃ§Ã£o.

## D-104 â€” HistÃ³rico completo recuperÃ¡vel no Copiloto

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelas mÃ©tricas de rastreabilidade de D-73. O histÃ³rico de conversas
abertas do Copiloto deve permitir percorrer todos os itens jÃ¡ visÃ­veis ao
escritÃ³rio em pÃ¡ginas de 12 registros, em vez de limitar a interface Ã s 12
conversas mais recentes. A seleÃ§Ã£o da conversa e a pÃ¡gina do histÃ³rico devem
ser preservadas entre as navegaÃ§Ãµes. A medida somente apresenta histÃ³rico local
jÃ¡ registrado: nÃ£o cria cobranÃ§a, nÃ£o altera valores, contratos, permissÃµes,
integraÃ§Ãµes, credenciais, custo ou homologaÃ§Ã£o.

## D-105 â€” Fechamentos adiados recuperÃ¡veis no console da plataforma

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelas mÃ©tricas de rastreabilidade de D-73. O console da plataforma
deve permitir percorrer todos os fechamentos ainda adiados, em pÃ¡ginas de 30
registros, em vez de limitar a consulta Ã s 30 ocorrÃªncias mais antigas. A
navegaÃ§Ã£o deve preservar os parÃ¢metros correntes da configuraÃ§Ã£o. A medida
somente apresenta evidÃªncias locais jÃ¡ registradas: nÃ£o executa fechamento, nÃ£o
altera fatura, contrato, reserva, preÃ§o, permissÃ£o, integraÃ§Ã£o, custo ou
homologaÃ§Ã£o.

## D-106 â€” AtenÃ§Ã£o de egressÃ£o recuperÃ¡vel no detalhe do escritÃ³rio

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelas mÃ©tricas de rastreabilidade de D-73. O detalhe do escritÃ³rio
no console da plataforma deve permitir percorrer todas as tentativas Claude que
ainda exigem verificaÃ§Ã£o, em pÃ¡ginas de 20 registros, em vez de limitar a
consulta Ã s 20 mais recentes. A navegaÃ§Ã£o deve preservar os parÃ¢metros correntes
do detalhe. A medida somente apresenta auditorias locais jÃ¡ registradas: nÃ£o
repete chamada, libera ou liquida consumo, altera reserva, polÃ­tica, dado,
permissÃ£o, integraÃ§Ã£o, custo ou homologaÃ§Ã£o.

## D-107 â€” DecisÃ£o NFS-e restrita ao catÃ¡logo do escritÃ³rio

Data: 21/09/2026. Origem: executor, decisÃ£o de implementaÃ§Ã£o local autorizada
por D-55 e pelos critÃ©rios de rastreabilidade da etapa 07. Ao resolver uma
revisÃ£o NFS-e, o acumulador deve existir no catÃ¡logo da mesma empresa: regra
ativa e vigente para a data do documento ou cÃ³digo jÃ¡ observado no histÃ³rico
local da empresa. A tela deve sugerir esses cÃ³digos e recusar cÃ³digo inexistente
ou de outra empresa. A medida nÃ£o infere tratamento fiscal, nÃ£o cria regra,
lanÃ§amento, integraÃ§Ã£o, custo ou homologaÃ§Ã£o.

## D-108 â€” Parcelamentos operÃ¡vel de ponta a ponta e entrada Ãºnica na ConciliaÃ§Ã£o

Data: 22/09/2026. Origem: responsÃ¡vel ("tela de parcelamentos nÃ£o estÃ¡ funcional";
"importaÃ§Ã£o para conciliaÃ§Ã£o precisa ser revisada"). Parcelamentos: a empresa em foco
oferece a consulta de pedidos com o custo cotado; o detalhe jÃ¡ pago Ã© exibido
(consolidaÃ§Ã£o, parcelas pagas, parcela bÃ¡sica); parcelas mostram atraso e mÃªs atual; DAS
nÃ£o concluÃ­do pode ser emitido de novo com nova cotaÃ§Ã£o; "resultado a confirmar" sÃ³ Ã©
liberado por perfil que autoriza consumo, com trilha de auditoria, sem liquidar nem
estornar a reserva de tokens. ConciliaÃ§Ã£o: um Ãºnico envio (`reconciliation-upload`)
recebe todos os formatos; extrato OFX enviado tambÃ©m alimenta a fila OFX Ã— DomÃ­nio
(importaÃ§Ã£o idempotente por hash); o campo de perÃ­odo, coletado e nunca gravado, saiu do
envio; a demonstraÃ§Ã£o nÃ£o recebe arquivos. NÃ£o altera custo, preÃ§o, integraÃ§Ã£o externa
nem homologaÃ§Ã£o.

## D-109 â€” EvoluÃ§Ã£o do CICA como central operacional

Data: 23/09/2026. Origem: responsÃ¡vel, por pedido explÃ­cito de implementaÃ§Ã£o do
plano completo de evoluÃ§Ã£o. O CICA passa a ter uma central de atividades e
fechamentos prÃ³pria, independente de ERP: DomÃ­nio e Siescon podem alimentar dados
por adaptadores autorizados, mas um escritÃ³rio tambÃ©m pode trabalhar com cadastro,
documentos, confirmaÃ§Ãµes humanas e importaÃ§Ãµes no CICA. Nenhum novo conector de
banco, adquirente, agregador financeiro ou ERP de terceiro serÃ¡ incluÃ­do nesta
evoluÃ§Ã£o; a arquitetura preserva adaptadores futuros sem depender deles.

Cada colaborador tem acesso operacional completo Ã s empresas que lhe forem
atribuÃ­das, inclusive confirmaÃ§Ã£o humana de transmissÃ£o e ciÃªncia oficial, desde
que a operaÃ§Ã£o pertenÃ§a Ã  sua empresa e fique registrada. AdministraÃ§Ã£o de equipe,
contrato, limites e configuraÃ§Ã£o global permanece com proprietÃ¡rio/administrador.
Esta decisÃ£o substitui a restriÃ§Ã£o de D-39 para empresas explicitamente atribuÃ­das.

Fechamento concluÃ­do exige processamento comprovado na fonte, quando ela existir,
ou documento mais confirmaÃ§Ã£o humana no modo independente; exige tambÃ©m as
obrigaÃ§Ãµes aplicÃ¡veis aceitas. Pagamento de guia Ã© atividade separada. Prazos
legais e internos sÃ£o distintos, e modelos de atividade tÃªm exceÃ§Ãµes aprovadas por
empresa e Ã¡rea. A auditoria preserva aÃ§Ãµes, resultados, impedimentos, atribuiÃ§Ãµes,
alteraÃ§Ãµes de prazo e atividades esperadas que venceram sem conclusÃ£o.

Os pacotes usam capacidade de usuÃ¡rios internos ativos e raÃ­zes de CNPJ ativas.
Matriz e filiais continuam entidades operacionais independentes. A franquia de IA
Ã© apresentada em reais de uso CICA, com teto mensal definido pelo administrador;
dados enviados Ã  IA externa sÃ£o minimizados e mascarados por padrÃ£o. O Integra
Contador repassa o custo efetivo auditÃ¡vel, incluindo distribuiÃ§Ã£o determinÃ­stica
de descontos e ajustes, sem margem. Esta decisÃ£o substitui a estrutura comercial
por mÃ³dulos/tokens incompatÃ­vel com essas regras, sem aprovar preÃ§os ou limites
numÃ©ricos.

RelatÃ³rios e grÃ¡ficos novos serÃ£o gerados por bibliotecas JavaScript, usando um
serviÃ§o Node/TypeScript interno para PDF, XLSX e grÃ¡ficos. Modelos de relatÃ³rio
sÃ£o configurÃ¡veis; usuÃ¡rios autorizados podem exportar a qualquer momento, com a
data da fotografia dos dados e pendÃªncias visÃ­veis. A conexÃ£o de e-mail evolui
para aplicaÃ§Ã£o central Mewstack com consentimento do escritÃ³rio, preservando o
aplicativo prÃ³prio como alternativa; ativaÃ§Ã£o real continua dependente de
homologaÃ§Ã£o e custos aprovados.

## D-110 â€” Meta de completude e validaÃ§Ã£o verificÃ¡vel

Data: 23/09/2026. Origem: responsÃ¡vel. A evoluÃ§Ã£o autorizada deve ser conduzida atÃ© a completude verificÃ¡vel do escopo aprovado: cada fluxo precisa ter comportamento, testes pertinentes, inspeÃ§Ã£o de interface quando houver tela, recuperaÃ§Ã£o de falha, documentaÃ§Ã£o operacional e limite externo explicitamente registrados. Lacunas devem ser pesquisadas em fontes oficiais ou apresentadas ao responsÃ¡vel como pergunta objetiva; nenhuma resposta, integraÃ§Ã£o, preÃ§o, polÃ­tica de dados ou homologaÃ§Ã£o pode ser presumida.

â€œPerfeitoâ€ nÃ£o autoriza declarar venda, produÃ§Ã£o ou integraÃ§Ã£o externa prontos sem a evidÃªncia exigida por D-73 e etapa 12. O objetivo inclui corrigir falhas locais encontradas na revisÃ£o, mantendo dados existentes e sem criar custo, publicar, contratar ou realizar chamadas externas reais sem autorizaÃ§Ã£o especÃ­fica.

## D-111 â€” NFS-e independente com fotografia Ãºnica do DomÃ­nio Web

Data: 23/09/2026. Origem: responsÃ¡vel. Um escritÃ³rio poderÃ¡ contratar e usar somente o mÃ³dulo NFS-e, com acesso e navegaÃ§Ã£o limitados Ã s superfÃ­cies desse mÃ³dulo. Isso nÃ£o libera os demais mÃ³dulos nem cria preÃ§o, cobranÃ§a ou contrato automaticamente.

Quando a fonte for DomÃ­nio Web, o escritÃ³rio envia um backup completo uma Ãºnica vez para formar a fotografia inicial dos acumuladores. A extraÃ§Ã£o ocorre no agente controlado, com leituras permitidas e versionadas; o CICA recebe apenas os registros normalizados necessÃ¡rios, nunca acesso livre ao banco nem o backup para processamento humano pelo desenvolvedor. O arquivo e a chave sÃ£o descartados apÃ³s a extraÃ§Ã£o concluÃ­da ou a falha terminal, preservando lote, hash, versÃ£o do extrator, hora da fotografia, empresas vinculadas, contagens e erros auditÃ¡veis.

Cada acumulador descoberto serÃ¡ vinculado Ã  empresa de origem e persistido como observaÃ§Ã£o de catÃ¡logo. Novas regras, acumuladores e decisÃµes adicionados nas telas serÃ£o registrados como novos eventos e passarÃ£o a compor o histÃ³rico, sem apagar a fotografia inicial. A exportaÃ§Ã£o para as rotinas automÃ¡ticas do DomÃ­nio serÃ¡ gerada no formato homologado, por empresa e competÃªncia, com prÃ©via, hash, evidÃªncia e estado separado de â€œarquivo geradoâ€, â€œdisponibilizadoâ€ e â€œimportado confirmadoâ€. O CICA nÃ£o alegarÃ¡ baixa ou importaÃ§Ã£o concluÃ­da sem retorno verificÃ¡vel da rotina.

A primeira leitura nÃ£o prova um layout de backup nem autoriza extraÃ§Ã£o real: o contrato tÃ©cnico do backup DomÃ­nio Web, um arquivo de teste autorizado e a homologaÃ§Ã£o do extrator continuam requisitos da etapa 12. A pesquisa oficial confirma que rotinas automÃ¡ticas usam os acumuladores configurados e podem ler arquivos de pasta por empresa/competÃªncia; o produto deve separar configuraÃ§Ã£o, geraÃ§Ã£o do arquivo e confirmaÃ§Ã£o da rotina. [DomÃ­nio: rotinas automÃ¡ticas](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=12051), [DomÃ­nio: acumuladores em NFS-e](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=10162).

## D-112 ? Pacote NFS-e permanece de conferencia ate homologacao

Data: 23/09/2026. Origem: pesquisa oficial e D-111. A documentacao publica do DomÃ­nio confirma que rotinas automaticas exigem configuracao por empresa, competencia e importador, mas nao publica o schema do backup `.dom` nem um contrato que vincule XML NFS-e, acumulador e rotina de importacao. Assim, o ZIP atual e um pacote privado de conferencia e evidencia: nao pode ser chamado de arquivo importavel nem habilitar confirmacao de importacao.

A liberacao dependera do layout tecnico autorizado, de uma amostra descartavel, da configuracao da rotina no ambiente autorizado e de retorno verificavel. Q-39 consolida esses requisitos. Referencias: [rotina de importacao via API](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=7247), [rotinas automaticas da Escrita](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=4364).

## D-113 ? Cadastro manual de acumulador exige crit?rio expl?cito

Data: 23/09/2026. Origem: solicita??o do respons?vel para manter hist?rico perfeito de acumuladores adicionados pela tela. Um acumulador criado manualmente ? um registro de cat?logo e hist?rico para a empresa; sem campos de correspond?ncia aprovados, ele n?o classifica NFS-e automaticamente. A classifica??o autom?tica exige uma regra n?o vazia, expl?cita e audit?vel. Caso contr?rio, a NFS-e segue para revis?o humana.

## D-114 ? Superf?cie exclusiva do produto NFS-e

Data: 23/09/2026. Origem: D-111 e solicita??o do respons?vel. Quando um escrit?rio tiver NFS-e como ?nico m?dulo habilitado de forma expl?cita, a entrada da ?rea autenticada deve levar ? central NFS-e e a navega??o n?o mostrar? a central de atividades nem os modelos operacionais. Cadastro de empresas, certificados, equipe e configura??o inicial permanecem como superf?cies auxiliares necess?rias ao pr?prio NFS-e. As rotas de atividades devem recusar esse recorte, inclusive por URL direta.

## D-115 - Exportacao financeira duravel

Data: 23/09/2026. Origem: D-109 e D-110. A exportacao PDF/XLSX de DRE ou caixa
cria uma solicitacao persistida com fotografia criptografada, hash, empresa, solicitante
e formato antes de ser entregue ao Celery. O worker deve revalidar a associacao ativa
do solicitante e seu acesso atual a empresa antes de renderizar. O arquivo gerado e
privado; o download tambem revalida o escopo atual. Reentrega, queda de worker e
artefato ausente devem permanecer visiveis como estados recuperaveis, sem gerar
resultado duplicado ou expor arquivo de outro escritorio.

A exportacao continua livre para usuario autorizado: nao ha aprovacao adicional. A
retencao definitiva dos artefatos e a operacao em producao continuam dependentes das
politicas e da homologacao da etapa 12.

## D-116 - Edicao versionada do mapa DRE

Data: 23/09/2026. Origem: D-109 e D-110. O escritorio administra o mapa DRE
pela interface, com conta, grupo e sinal. Salvar nunca altera um mapa ja usado: o CICA
valida o conjunto inteiro, cria uma nova versao completa, torna somente ela ativa e
preserva todas as versoes e linhas anteriores. Contas duplicadas, grupo ausente ou sinal
fora de -1/1 impedem o salvamento. A acao fica restrita a administrador/proprietario e
registra a versao, quantidade de contas e autor na auditoria.

## D-117 - Relatorios do Copiloto usam somente o renderizador JavaScript

Data: 23/09/2026. Origem: D-109 e D-110. PDF e XLSX exportados pelo Copiloto
usam a mesma fotografia restrita e o servico Node/TypeScript de relatorios usado
pelas entregas financeiras. ReportLab e OpenPyXL deixam de gerar esses artefatos;
as bibliotecas Python de leitura/importacao permanecem fora desta decisao. Sem URL
interna e segredo configurados, a exportacao responde indisponivel de forma explicita
e nao produz versao alternativa. A fotografia, a verificacao de permissao, o hash e a
auditoria continuam obrigatorios antes da resposta ao usuario.

## D-118 - Conferencia de folha por fotografias agregadas

Data: 23/09/2026. Origem: D-109 e D-110. A ficha da empresa permite comparar duas
fotografias de folha da mesma competencia, mostrando a fonte, os totais agregados, as
metricas ausentes e cada diferenca acima da tolerancia configurada no pedido. A tela nao
calcula folha, nao mostra dado individual de trabalhador e nao chama fonte externa. Apenas
fotografias da empresa que o usuario ja pode acessar podem ser escolhidas; fontes manuais
ou documentais continuam identificadas como tais. A conferencia e leitura explicavel, e o
tratamento de uma diferenca permanece vinculado a atividade operacional responsavel.

## D-119 - Tratamento da divergencia de folha abre a fila no mesmo contexto

Data: 23/09/2026. Origem: D-118 e D-110. A conferencia de fotografias da folha deve
levar diretamente para as atividades de folha da mesma empresa e competencia, sem marcar
qualquer atividade como concluida ou presumir causa da divergencia. A central de atividades
aceita competencia mensal como filtro explicito na URL, combinado com empresa e area.
Competencia malformada nao altera a fila nem e convertida silenciosamente para outro mes.

## D-120 - Prioridade operacional deterministica e estados de fonte visiveis

Data: 23/09/2026. Origem: plano aprovado, secoes 3.1 e 4.2. A area de trabalho resume
todas as atividades abertas do escopo autorizado por atraso, vencimento no dia, proximos
sete dias, impedimento e fonte indisponivel. Cada numero abre a central com o filtro
correspondente na URL. Esses grupos se sobrepoem porque representam dimensoes independentes;
nenhum total deve ser apresentado como soma dos outros. A fila aceita a situacao de
atualizacao como filtro separado do estado de trabalho. A ordenacao permanece deterministica
por prazo, sem IA ocultar, reordenar ou dispensar atividade.

## D-121 - Gestao de carteira mostra distribuicao, nao produtividade presumida

Data: 23/09/2026. Origem: plano aprovado, secao 3.2. Apenas proprietario e administrador
veem na area de trabalho a distribuicao de atividades abertas por membro ativo do escritorio,
com atrasadas e impedidas separadas. Cada linha abre a fila daquele responsavel; tambem existe
o recorte de atividades sem responsavel. Os numeros descrevem atribuicao e estado atual do
trabalho no escopo autorizado, nao avaliam produtividade, disponibilidade individual ou
qualidade do profissional. Membros sem atividade seguem visiveis para distinguir capacidade
sem trabalho atribuido de ausencia da equipe.

## D-122 - Configuracao inicial retomavel conduz para a proxima acao concreta

Data: 23/09/2026. Origem: plano aprovado, secao 3.4, e revisao da superficie existente. O assistente de configuracao deve usar exclusivamente o estado persistido do escritorio para indicar cada etapa concluida ou pendente e levar o owner/administrador para a tela exata que resolve a pendencia: identificacao do escritorio, fonte de dados, empresas, modelos de atividades, modulos e contrato, equipe, limites e MFA. Ele pode ser interrompido e retomado sem perder estado; nao cria empresas, modelos, modulos, franquias, integracoes ou operacoes tarifadas automaticamente. Configuracao pendente de uma fonte ou servico continua sem bloquear recursos independentes.


## D-123 â€” Carteira explÃ­cita e revogaÃ§Ã£o sem acesso legado

Data: 24/09/2026. Origem: meta aprovada de conclusÃ£o da central operacional e D-109. Colaboradores precisam de atribuiÃ§Ã£o ativa para consultar uma empresa, inclusive em escritÃ³rios sem CRMew. A ausÃªncia ou revogaÃ§Ã£o da Ãºltima atribuiÃ§Ã£o nunca concede acesso ao escritÃ³rio inteiro. ProprietÃ¡rio/administrador mantÃ©m visÃ£o total local; quando existe controle externo, sua validade e seus limites continuam obrigatÃ³rios. Membro ou escritÃ³rio inativo nÃ£o recebe carteira nem capacidades. A mesma fronteira deve valer para consulta, capacidade por empresa e capacidade agregada. NÃ£o criar atribuiÃ§Ãµes para preservar silenciosamente o acesso legado.

## D-124 â€” OrdenaÃ§Ã£o pelo prazo efetivo da atividade

Data: 24/09/2026. Origem: correÃ§Ã£o aprovada na meta da central operacional. A prÃ©via e a fila ordenam pelo mesmo prazo usado nos indicadores: prazo interno quando preenchido; caso contrÃ¡rio, prazo legal. Atividades sem qualquer prazo ficam apÃ³s as datadas, com desempate estÃ¡vel. Uma atividade futura com prazo interno nÃ£o precede uma atividade atrasada apenas porque esta tem somente prazo legal.

## D-125 â€” VisÃ£o geral comeÃ§a no trabalho pessoal

Data: 24/09/2026. Origem: meta aprovada e diagnÃ³stico da VisÃ£o geral. A entrada padrÃ£o Ã© Meu trabalho, filtrada pelo responsÃ¡vel atual inclusive para administradores. Carteira mostra atividades das empresas autorizadas, sem atribuir tarefas sem responsÃ¡vel Ã  pessoa. GestÃ£o Ã© exclusiva de proprietÃ¡rio/administrador. Os recortes, filtros e pÃ¡ginas sÃ£o explÃ­citos na URL; links de indicadores mantÃªm o mesmo recorte e mostram somente trabalho aberto. A agenda exibe atraso, hoje, prÃ³ximos sete dias, posteriores e sem prazo, sem limite silencioso de seis itens. MÃ©tricas genÃ©ricas, filas de mÃ³dulos e gestÃ£o de equipe ficam fora da agenda pessoal. A visualizaÃ§Ã£o da carteira nÃ£o amplia permissÃ£o de empresa. Suporte permanece limitado ao escopo autorizado; NFS-e exclusivo preserva sua entrada prÃ³pria.

## D-126 â€” RecorrÃªncia mensal recuperÃ¡vel por atribuiÃ§Ã£o

Data: 24/09/2026. Origem: meta de geraÃ§Ã£o recorrente aprovada. Modelos mensais ativos atribuÃ­dos pelo administrador passam a ter cursor de prÃ³xima competÃªncia. A primeira execuÃ§Ã£o automÃ¡tica comeÃ§a no mÃªs corrente, sem inventar obrigaÃ§Ãµes retroativas; depois retoma competÃªncias nÃ£o executadas. Cada atribuiÃ§Ã£o Ã© bloqueada em transaÃ§Ã£o e o cursor avanÃ§a junto das atividades e auditoria. A execuÃ§Ã£o processa atÃ© 12 competÃªncias por atribuiÃ§Ã£o e retoma o restante no ciclo seguinte. Pausar/reativar pela aÃ§Ã£o administrativa reinicia a referÃªncia automÃ¡tica no mÃªs corrente, sem apagar atividades antigas nem gerar meses da pausa. HistÃ³rico manual continua explÃ­cito.

EscritÃ³rios inativos, demonstraÃ§Ãµes, empresas inativas, modelos pausados e contratos NFS-e exclusivos nÃ£o geram atividades automÃ¡ticas. Limites externos vencidos e ciclo suspenso/arquivado/provisionando impedem geraÃ§Ã£o. ResponsÃ¡vel sem vÃ­nculo e carteira ativos nÃ£o recebe nova tarefa: a atividade fica sem responsÃ¡vel com evento explicativo, sem ampliar acesso. Erro em uma atribuiÃ§Ã£o mantÃ©m o cursor e registra falha auditÃ¡vel sem dados sensÃ­veis; nÃ£o bloqueia as demais. A execuÃ§Ã£o automÃ¡tica tem autor de sistema, sem simular aprovaÃ§Ã£o humana ou concluir trabalho. O agendador roda a cada hora; sua operaÃ§Ã£o publicada e concorrÃªncia real PostgreSQL exigem homologaÃ§Ã£o.

## D-127 â€” Fechamento exige requisitos atuais, alÃ©m do estado da tarefa

Data: 24/09/2026. Origem: implementaÃ§Ã£o da regra aprovada em D-109. A avaliaÃ§Ã£o de fechamento deve revalidar evidÃªncia, processamento obrigatÃ³rio fechado e obrigaÃ§Ã£o obrigatÃ³ria aceita; marcar a tarefa como concluÃ­da nÃ£o substitui esses requisitos. A conclusÃ£o manual e a avaliaÃ§Ã£o agregada compartilham a mesma regra. Fonte indisponÃ­vel ou desatualizada impede comprovar conclusÃ£o; exigÃªncia de fonte integrada tambÃ©m nÃ£o Ã© satisfeita por integraÃ§Ã£o nÃ£o configurada. No modo documental/humano, integraÃ§Ã£o nÃ£o configurada nÃ£o bloqueia por si sÃ³. A exigÃªncia source_or_human pede uma dessas duas comprovaÃ§Ãµes: um documento isolado nÃ£o simula confirmaÃ§Ã£o humana. Dispensa exige motivo, responsÃ¡vel, data e evidÃªncia, preservando o histÃ³rico; nÃ£o exige processamento ou transmissÃ£o do item dispensado. Pagamento permanece independente. A avaliaÃ§Ã£o nÃ£o altera nem apaga conclusÃµes anteriores; informa requisitos ausentes. Esta correÃ§Ã£o de domÃ­nio antecede sua exposiÃ§Ã£o no painel e nÃ£o homologa fontes externas.

## D-128 â€” Fechamentos da carteira com cobertura explÃ­cita

24/09/2026. A VisÃ£o geral apresenta os requisitos cadastrados de fechamento por empresa autorizada, competÃªncia selecionada e Ã¡rea contÃ¡bil/fiscal/folha. A competÃªncia inicial Ã© o mÃªs corrente explicitamente exibido, ajustÃ¡vel na URL. O resumo sempre considera todos os responsÃ¡veis daquela empresa, mesmo na agenda pessoal. Requisitos sÃ£o as atividades que exigem processamento fechado ou obrigaÃ§Ã£o aceita; uma tarefa de pagamento isolada nÃ£o integra esse conjunto. AusÃªncia de requisitos significa cobertura nÃ£o configurada, nunca empresa fechada. O rÃ³tulo positivo serÃ¡ Requisitos comprovados, acompanhado do aviso de que a cobertura depende dos modelos cadastrados. Cada requisito mostra prazo, responsÃ¡vel, atualizaÃ§Ã£o, causa e acesso ao histÃ³rico/evidÃªncias. PaginaÃ§Ã£o Ã© por empresas, sem cortar silenciosamente a carteira. Isso nÃ£o presume completude de obrigaÃ§Ãµes legais nem capacidades ainda nÃ£o homologadas.

## D-129 â€” RevisÃ£o NFS-e alimenta a central pelo resultado local

24/09/2026. Casos de revisÃ£o NFS-e terÃ£o vÃ­nculo Ãºnico com atividade fiscal. Captura cria atividade sem prazo ou responsÃ¡vel inventados, usando a competÃªncia de emissÃ£o quando disponÃ­vel. A decisÃ£o humana no mÃ³dulo conclui a atividade e registra evidÃªncia com autor e data, na mesma transaÃ§Ã£o do caso, histÃ³rico de acumuladores e artefato. A atividade nÃ£o pode ser concluÃ­da separadamente enquanto a revisÃ£o estiver aberta. Processamento local revisado nÃ£o Ã© fechamento/importaÃ§Ã£o no DomÃ­nio, pagamento ou aceitaÃ§Ã£o oficial. Repetir sincronizaÃ§Ã£o nÃ£o duplica atividade/evidÃªncia/eventos; o vÃ­nculo permite recompor registros anteriores explicitamente. DemonstraÃ§Ãµes nÃ£o geram atividade persistida por essa ponte; a entrada NFS-e exclusiva permanece a mesma.

## D-130 â€” Atividade de Triagem acompanha arquivamento comprovado

24/09/2026. Itens com empresa identificada geram atividade geral vinculada, sem prazo ou responsÃ¡vel inventados. Itens sem empresa continuam na fila prÃ³pria da Triagem. AprovaÃ§Ã£o para arquivar nÃ£o conclui trabalho; falha/rejeiÃ§Ã£o gera impedimento. Somente estado arquivado com data, destino e hash coincidente com o conteÃºdo cria evidÃªncia de conclusÃ£o local, sem fechamento de ERP ou obrigaÃ§Ã£o oficial. TransiÃ§Ãµes humanas e retornos do agente atualizam a atividade na transaÃ§Ã£o existente. RepetiÃ§Ã£o preserva evidÃªncias e nÃ£o duplica tarefas. VÃ­nculo com empresa diferente Ã© recusado, sem transferir histÃ³rico silenciosamente. RejeiÃ§Ã£o permanece impedimento documental, nÃ£o dispensa automÃ¡tica. DemonstraÃ§Ãµes nÃ£o geram projeÃ§Ãµes persistidas.

## D-131 â€” AÃ§Ã£o na origem e permissÃ£o consistente da atividade

24/09/2026. Atividades vinculadas Ã  NFS-e/Triagem orientam a prÃ³xima aÃ§Ã£o para o registro de origem, com estado local visÃ­vel. FormulÃ¡rios genÃ©ricos nÃ£o substituem essa decisÃ£o. O acesso ao mÃ³dulo permanece condicionado Ã s permissÃµes existentes; vÃ­nculo divergente de escritÃ³rio/empresa nÃ£o produz link. Consulta da atividade e alteraÃ§Ã£o sÃ£o permissÃµes distintas: auditor/financeiro consultam a carteira autorizada, mas nÃ£o registram evidÃªncia, impedimento ou conclusÃ£o. ServiÃ§os revalidam carteira vigente e perfil; telas tambÃ©m respeitam suporte somente leitura. Nenhum link executa decisÃ£o ou ciÃªncia automaticamente.

## D-132 â€” AtribuiÃ§Ã£o explÃ­cita e histÃ³rico de redistribuiÃ§Ã£o

24/09/2026. ProprietÃ¡rio/administrador atribui ou remove responsÃ¡vel de atividade aberta no detalhe, com motivo obrigatÃ³rio. DestinatÃ¡rio deve ser usuÃ¡rio e membro ativos, com perfil operacional e carteira vigente da empresa; a aÃ§Ã£o nunca concede acesso. Atividade encerrada preserva sua atribuiÃ§Ã£o histÃ³rica. AlteraÃ§Ãµes concorrentes detectam o responsÃ¡vel anterior esperado e recusam sobrescrita silenciosa. Evento e auditoria guardam responsÃ¡veis anterior/novo, autor e motivo. Remover responsÃ¡vel recoloca trabalho na carteira compartilhada. Aplica-se Ã s atividades avulsas, recorrentes e de mÃ³dulos, sem modificar o responsÃ¡vel padrÃ£o dos modelos ou inventar prazo.

## D-133 â€” Ordem temporal e repetiÃ§Ã£o das observaÃ§Ãµes

24/09/2026. ObservaÃ§Ãµes de fontes usam instante explÃ­cito com fuso quando informado. RepetiÃ§Ã£o exata de conteÃºdo, fonte, atividade e instante retorna o registro existente. Retorno antigo permanece no histÃ³rico sem sobrescrever valor mais recente; processamento e obrigaÃ§Ã£o sÃ£o avaliados separadamente. Empate conflitante numa dimensÃ£o nÃ£o escolhe vencedor pela ordem de chegada: conserva valor e marca desatualizaÃ§Ã£o para conferÃªncia. Falha de consulta nÃ£o altera processamento/obrigaÃ§Ã£o. AtualizaÃ§Ã£o da fonte nÃ£o recua sua Ãºltima fotografia. Somente estados efetivamente aplicados podem reabrir uma atividade concluÃ­da. Adaptadores devem reutilizar o instante original para reconhecer repetiÃ§Ã£o; chamadas sem instante representam novas observaÃ§Ãµes. Isso prepara a integraÃ§Ã£o e nÃ£o constitui homologaÃ§Ã£o de uma fonte.

Complemento D-133: observaÃ§Ã£o bem-sucedida que efetivamente aplica processamento ou obrigaÃ§Ã£o registra evidÃªncia vinculada ao ID da observaÃ§Ã£o e Ã  data original. NÃ£o conclui automaticamente o trabalho. Retorno histÃ³rico sem aplicaÃ§Ã£o, falha e conflito sem dado aplicado nÃ£o criam comprovaÃ§Ã£o nova.

## D-134 â€” Tratamento de arquivo da ConciliaÃ§Ã£o na central

24/09/2026. Uma atividade por arquivo acompanha leitura, revisÃ£o e tratamento local dos movimentos. Leitura ou sugestÃµes nÃ£o concluem a atividade. Cada movimento deve estar integralmente conciliado com evidÃªncia, ter lanÃ§amento aprovado/exportado da revisÃ£o vigente, ou estar explicitamente ignorado por decisÃ£o/regra registrada. Arquivo sem movimentos ou com erros nÃ£o comprova conclusÃ£o. Nova revisÃ£o ou desfazimento reavalia a atividade e preserva as evidÃªncias anteriores. ConclusÃ£o local nÃ£o confirma exportaÃ§Ã£o/importaÃ§Ã£o no ERP. RepetiÃ§Ãµes e reprocessamentos do mesmo arquivo usam a mesma atividade; responsÃ¡vel/prazo nÃ£o sÃ£o presumidos. Acesso permanece limitado Ã  empresa.

## D-135 â€” Reconfirmar conciliaÃ§Ã£o preservando decisÃµes

24/09/2026. RelaÃ§Ã£o desfeita pode ser confirmada novamente, apÃ³s revalidar empresa, evidÃªncia, equilÃ­brio e saldo disponÃ­vel dos dois lados. Preservar cada confirmaÃ§Ã£o e desfazimento em histÃ³rico prÃ³prio com valor, evidÃªncia, estado, autor e data; conteÃºdo documental nÃ£o vai para logs genÃ©ricos. RelaÃ§Ã£o jÃ¡ confirmada continua recusando nova alocaÃ§Ã£o. Desfazimento repetido nÃ£o cria outra decisÃ£o. Registros anteriores sem histÃ³rico recebem fotografia identificada como legado antes da alteraÃ§Ã£o; nÃ£o inventar autor/data de confirmaÃ§Ã£o perdidos. ProjeÃ§Ã£o da atividade e histÃ³rico integram a mesma transaÃ§Ã£o.

## D-136 â€” Abrir o arquivo da atividade na ConciliaÃ§Ã£o

24/09/2026. A atividade de ConciliaÃ§Ã£o abre a tela existente com processamentos e movimentos restritos ao arquivo autorizado. Filtro fica na URL, persiste na paginaÃ§Ã£o e busca; arquivo invÃ¡lido ou fora da carteira retorna 404, sem abrir uma fila ampla por engano. Identificar arquivo/empresa, permitir voltar Ã  atividade e remover o filtro explicitamente. Indicadores gerais e exportaÃ§Ãµes continuam identificados como visÃ£o da carteira. NavegaÃ§Ã£o nÃ£o executa processamento nem confirmaÃ§Ã£o. PermissÃµes do mÃ³dulo e empresa sÃ£o revalidadas no destino; a atividade nÃ£o oferece conclusÃ£o genÃ©rica para substituir o fluxo de origem.

## D-137 â€” HistÃ³rico consultÃ¡vel da conciliaÃ§Ã£o no movimento

24/09/2026. Detalhe do movimento apresenta decisÃµes preservadas, mais recentes primeiro, com paginaÃ§Ã£o independente, estado, valor, lanÃ§amento, autor e data disponÃ­veis. Fotografia legada Ã© identificada, nÃ£o datada artificialmente; ausÃªncia de autor nÃ£o implica decisÃ£o humana nem automÃ¡tica. EvidÃªncia Ã© texto escapado, nunca HTML executÃ¡vel. Consulta exige a mesma empresa e mÃ³dulo do movimento e nÃ£o cria decisÃµes ou altera conciliaÃ§Ãµes.

## D-138 â€” Entrada de totais de folha por arquivo

24/09/2026. Fluxo existente de prÃ©via/confirmaÃ§Ã£o aceita CSV/XLSX de totais agregados da folha, uma empresa/competÃªncia/referÃªncia por linha, sem dados pessoais de trabalhadores. CompetÃªncia usa primeiro dia do mÃªs; valores vazios permanecem ausentes, nÃ£o zero. Entrada Ã© documento informado, jamais retorno oficial. Empresa deve corresponder Ã  fonte autorizada. Lote invÃ¡lido nÃ£o grava fotografias parciais. RepetiÃ§Ã£o da referÃªncia com os mesmos dados nÃ£o duplica; conteÃºdo diferente exige referÃªncia nova, preservando o anterior. A comparaÃ§Ã£o existente passa a ter entrada operacional; sua ligaÃ§Ã£o com atividades e homologaÃ§Ã£o ERP permanecem entregas distintas.

## D-139 â€” ConferÃªncia da folha na central

24/09/2026. Receber fotografias da folha gera uma atividade de conferÃªncia por empresa/competÃªncia, sem atribuir pessoa ou prazo presumidos. Nova fotografia recebida reabre conferÃªncia concluÃ­da/dispensada, preserva responsÃ¡vel e evidÃªncias, e exige confirmaÃ§Ã£o humana posterior ao novo recebimento. Igualdade de totais ou simples importaÃ§Ã£o nÃ£o conclui trabalho. Reenvio idÃªntico nÃ£o reabre. A referÃªncia da fotografia mais recentemente cadastrada identifica a revisÃ£o, mesmo se sua observaÃ§Ã£o de origem for antiga. Esta atividade nÃ£o representa fechamento de ERP ou obrigaÃ§Ã£o governamental; comparaÃ§Ãµes continuam na ficha da empresa. RecomposiÃ§Ã£o de registros legados Ã© explÃ­cita por escritÃ³rio.

## D-140 â€” Contexto da conferÃªncia por competÃªncia

24/09/2026. Atividade da folha abre a ficha da empresa com fotografias e seletores de comparaÃ§Ã£o limitados Ã  sua competÃªncia. Filtro explÃ­cito na URL persiste na paginaÃ§Ã£o e envio da comparaÃ§Ã£o; data invÃ¡lida Ã© recusada. Retorno Ã  atividade serve para registrar evidÃªncia/conclusÃ£o humana. Consultar ou comparar nÃ£o conclui atividade. PermissÃµes da empresa sÃ£o revalidadas e nenhum prazo/obrigaÃ§Ã£o Ã© inferido pelo filtro.

## D-141 â€” PrÃ©via dos totais antes da importaÃ§Ã£o

24/09/2026. ProprietÃ¡rio/administrador vÃª linhas paginadas do arquivo da folha antes de confirmar: empresa identificada na fonte, competÃªncia, referÃªncia, pessoas e valores originais. Campos vazios sÃ£o identificados; empresa nÃ£o localizada nÃ£o Ã© associada por aproximaÃ§Ã£o. PrÃ©via nÃ£o grava fotografias, nÃ£o valida conclusÃ£o nem dispensa a validaÃ§Ã£o integral na confirmaÃ§Ã£o. Apenas usuÃ¡rios autorizados a administrar a importaÃ§Ã£o acessam o conteÃºdo do lote.

## D-142 â€” AnÃ¡lise de comunicaÃ§Ã£o DTE na central

24/09/2026. Mensagem persistida da Caixa Postal gera atividade de anÃ¡lise por mensagem, sem prazo/competÃªncia legal presumidos. Monitoramento nÃ£o provoca ciÃªncia. Abertura comprovada registra evidÃªncia de consulta, mas somente anÃ¡lise humana conclui o trabalho local; isso nÃ£o comprova cumprimento da demanda. Abertura com resultado incerto impede conclusÃ£o atÃ© esclarecimento pela rotina existente, sem repetir chamada automaticamente. RepetiÃ§Ã£o de observaÃ§Ãµes nÃ£o duplica atividade/prova. ServiÃ§o de abertura revalida carteira vigente, alÃ©m de permissÃ£o de ciÃªncia, antes de reservar consumo ou chamar o provedor.

## D-143 â€” ConfirmaÃ§Ã£o DTE posterior ao teor disponÃ­vel

24/09/2026. Quando existe abertura comprovada, a anÃ¡lise exige confirmaÃ§Ã£o humana identificada, registrada e observada apÃ³s a abertura. O requisito consulta o recibo mesmo se a projeÃ§Ã£o da central falhar. Novo comprovante reabre conclusÃ£o ou dispensa anterior quando nÃ£o hÃ¡ confirmaÃ§Ã£o humana posterior vÃ¡lida; recomposiÃ§Ã£o nÃ£o reabre anÃ¡lise jÃ¡ comprovada apÃ³s aquele recibo. Resultado aberto sem data ou conteÃºdo Ã© insuficiente. EvidÃªncias e eventos anteriores permanecem no histÃ³rico.

## D-144 â€” Contexto entre anÃ¡lise e mensagem DTE

24/09/2026. A atividade oferece link ao resumo local da mensagem correspondente quando empresa, escritÃ³rio e acesso ao Integra forem vÃ¡lidos. O resumo oferece retorno Ã  atividade vinculada, com escopo novamente conferido. GET nÃ£o abre teor no provedor nem conclui anÃ¡lise; a confirmaÃ§Ã£o legal permanece no fluxo explÃ­cito existente. Sem acesso ao mÃ³dulo, a atividade informa a restriÃ§Ã£o e preserva o registro de evidÃªncia humana autorizado.

## D-145 â€” AnÃ¡lise do Radar vinculada por escolha humana

24/09/2026. PublicaÃ§Ã£o pÃºblica nÃ£o gera tarefas para todas as empresas. UsuÃ¡rio operacional vincula uma publicaÃ§Ã£o Ã  empresa autorizada com justificativa de anÃ¡lise; atividade Ãºnica por publicaÃ§Ã£o/empresa, inicialmente atribuÃ­da ao prÃ³prio usuÃ¡rio. NÃ£o presume competÃªncia, prazo legal, aplicabilidade tributÃ¡ria nem aceite oficial. VersÃ£o observada preserva tÃ­tulo, URL e classificaÃ§Ã£o; mudanÃ§a nesses dados reabre conclusÃ£o/dispensa e exige confirmaÃ§Ã£o humana posterior. Recoleta idÃªntica nÃ£o duplica nem reabre; reclassificaÃ§Ã£o como geral preserva o vÃ­nculo para revisÃ£o humana, sem cancelar silenciosamente o trabalho. Coleta apenas atualiza vÃ­nculos jÃ¡ escolhidos e nÃ£o faz novas atribuiÃ§Ãµes.

## D-146 â€” Acesso DCTFWeb revalidado antes do consumo e da execuÃ§Ã£o

24/09/2026. Consulta de documento DCTFWeb exige solicitante identificado, usuÃ¡rio e vÃ­nculo ativos, perfil operacional, empresa autorizada e mÃ³dulo Guias vigente. ServiÃ§o verifica antes de reservar consumo; worker verifica novamente antes da chamada. SolicitaÃ§Ã£o sem responsÃ¡vel ou com acesso revogado falha sem chamar provedor e libera a reserva ainda nÃ£o consumida. Resultado incerto de chamada jÃ¡ iniciada mantÃ©m o tratamento anterior, sem liberar nem repetir por inferÃªncia. A verificaÃ§Ã£o nÃ£o constitui homologaÃ§Ã£o da declaraÃ§Ã£o ou aceite oficial.

## D-147 â€” Guias e PARCSN exigem autorizaÃ§Ã£o vigente na execuÃ§Ã£o

24/09/2026. Aplicar a verificaÃ§Ã£o de D-146 tambÃ©m Ã  emissÃ£o de guias (mÃ³dulo Guias) e operaÃ§Ãµes PARCSN (mÃ³dulo Integra). Exigir solicitante identificado antes da reserva e revalidar usuÃ¡rio, vÃ­nculo, perfil, empresa, mÃ³dulo e carteira antes da chamada. Recusa anterior Ã  chamada libera apenas reserva nÃ£o executada e registra falha. Nenhuma autorizaÃ§Ã£o antiga ou ausÃªncia de ator concede acesso por compatibilidade. Resultados de chamadas jÃ¡ iniciadas exigem tratamento separado da revogaÃ§Ã£o prÃ©via.

## D-148 â€” EmissÃ£o de guia com resultado incerto

24/09/2026. Erro de transporte apÃ³s iniciar a chamada ou retorno sem PDF vÃ¡lido deixa a guia em Resultado a confirmar; preserva reserva, protocolo e retorno disponÃ­vel, sem declarar emissÃ£o, pagamento ou gratuidade. Estado impede reemissÃ£o, reprocessamento do worker e promoÃ§Ã£o por nova apuraÃ§Ã£o/documentos. Falhas anteriores com cÃ³digo integration serÃ£o reclassificadas para conferÃªncia, sem alterar retroativamente consumo. Carteira oferece filtro prÃ³prio e inclui esses casos nas pendÃªncias; detalhe orienta conferir fornecedor/consumo antes de qualquer nova aÃ§Ã£o. RecuperaÃ§Ã£o financeira exige evidÃªncia, sem liberaÃ§Ã£o automÃ¡tica por timeout.

## D-149 â€” CorreÃ§Ã£o do proprietÃ¡rio: reemissÃ£o permitida com custo adicional

24/09/2026. O proprietÃ¡rio corrigiu explicitamente D-148: pode haver reemissÃ£o, com custo adicional por guia. A proibiÃ§Ã£o de reemitir foi uma inferÃªncia do implementador e nÃ£o representa o comportamento aprovado. Consultar o proprietÃ¡rio antes de definir novas regras de fluxo ou cobranÃ§a; nÃ£o presumir valores. EstÃ¡ pendente a resposta sobre adicional como repasse do custo efetivo Serpro sem margem ou tarifa prÃ³pria CICA. Preservar evidÃªncias, resultados incertos e consumo de tentativas anteriores; a possibilidade de nova emissÃ£o nÃ£o comprova que a anterior falhou ou foi gratuita. CÃ³digo provisÃ³rio de bloqueio nÃ£o estÃ¡ entregue como soluÃ§Ã£o final e precisa ser substituÃ­do pelo fluxo autorizado de reemissÃ£o cobrada.

## D-150 â€” PreservaÃ§Ã£o tÃ©cnica das tentativas de guia

24/09/2026. Detalhamento tÃ©cnico da preservaÃ§Ã£o jÃ¡ exigida por D-149 e pela auditoria do plano: cada tentativa mantÃ©m fotografias imutÃ¡veis da solicitaÃ§Ã£o e dos estados observados, com referÃªncia ao consumo, solicitante, dados da guia, protocolo e retorno criptografado. Antes de iniciar outra tentativa, preservar o resultado existente e limpar os campos de retorno da nova tentativa, impedindo associaÃ§Ã£o de protocolo antigo a resposta nova. HistÃ³rico legado preserva apenas o estado disponÃ­vel, sem fabricar eventos anteriores. Este trabalho nÃ£o define tarifa, liberaÃ§Ã£o de reemissÃ£o ou nova regra comercial; essas mudanÃ§as continuam dependentes da resposta de D-149.

## D-151 â€” Consulta do histÃ³rico de guias

24/09/2026. ExposiÃ§Ã£o da auditoria jÃ¡ prevista: ficha da guia apresenta estados preservados por tentativa, dos mais recentes aos mais antigos, com data, responsÃ¡vel disponÃ­vel no escritÃ³rio, protocolo e distinÃ§Ã£o de registro legado/fictÃ­cio. PaginaÃ§Ã£o de 20 eventos segue os histÃ³ricos existentes. Download de PDF salvo de tentativa emitida revalida escritÃ³rio, carteira e mÃ³dulo, sem chamada ao fornecedor. NÃ£o exibir retorno bruto na pÃ¡gina nem inferir custo ou pagamento a partir do estado. Sem alteraÃ§Ã£o da decisÃ£o comercial pendente de D-149.

## D-152 â€” CorreÃ§Ã£o do escopo de consulta das integraÃ§Ãµes

24/09/2026. CorreÃ§Ã£o tÃ©cnica do isolamento jÃ¡ exigido pelo plano e pelas concessÃµes por empresa: consulta de Guias/Integra deve intersectar carteira e mÃ³dulo na mesma concessÃ£o. Uma concessÃ£o de Guias na empresa A nÃ£o autoriza Guias na empresa B cuja concessÃ£o contÃ©m somente outro mÃ³dulo. Aplicar Ã s pÃ¡ginas e downloads que usam o contexto desses mÃ³dulos, preservando administradores dentro da carteira autorizada e suporte dentro da sessÃ£o prÃ³pria. Perfil consultivo continua consultivo; nenhuma nova autorizaÃ§Ã£o de execuÃ§Ã£o ou regra comercial Ã© concedida.

## D-153 â€” EvidÃªncia de cada resoluÃ§Ã£o NFS-e

24/09/2026. CorreÃ§Ã£o da preservaÃ§Ã£o de histÃ³rico jÃ¡ exigida: a evidÃªncia operacional e a entrada no histÃ³rico de acumuladores identificam revisÃ£o, instante, responsÃ¡vel e acumulador escolhido. Reabertura seguida de nova resoluÃ§Ã£o mantÃ©m a prova anterior e acrescenta outra, sem reutilizar a referÃªncia apenas pelo ID da revisÃ£o. Reprocessar a mesma resoluÃ§Ã£o Ã© idempotente. NÃ£o cria um novo fluxo de reabertura nem comprova importaÃ§Ã£o no DomÃ­nio; corrige somente a projeÃ§Ã£o dos estados existentes.

## D-154 â€” ValidaÃ§Ã£o PostgreSQL e locks de registros opcionais

24/09/2026. CorreÃ§Ã£o tÃ©cnica de compatibilidade encontrada em testes com PostgreSQL 17 local descartÃ¡vel. Workers DCTFWeb/PARCSN e rotinas de Triagem devem bloquear explicitamente a linha principal que controla a transiÃ§Ã£o, sem solicitar FOR UPDATE de relaÃ§Ãµes opcionais carregadas por outer join. Preservar transaÃ§Ãµes e verificaÃ§Ãµes; nÃ£o remover locks para fazer testes passarem. Reserva/liquidaÃ§Ã£o mantÃªm seus prÃ³prios controles. NÃ£o altera fluxo comercial, ciÃªncia, transmissÃ£o ou autorizaÃ§Ã£o. ReferÃªncia tÃ©cnica: documentaÃ§Ã£o Django 6.0 de select_for_update(of=("self",)).

Complemento de D-154 (01/10/2026): a regressão PostgreSQL atual encontrou a mesma incompatibilidade nas projeções de Guias, DCTFWeb e Parcelamentos para atividades. Aplicar `select_for_update(of=("self",))` à linha fiscal que controla cada projeção, preservando o lock separado da atividade e a transação. Não alterar resultado fiscal, permissão ou acionamento de fornecedor.

## D-155 â€” ProjeÃ§Ã£o conservadora dos resultados Serpro na central

24/09/2026. Cada guia, consulta DCTFWeb e operaÃ§Ã£o PARCSN persistida pode originar uma atividade exclusiva da mesma empresa, para apresentar pedido, resultado, evidÃªncia e impedimento na central. A projeÃ§Ã£o nÃ£o presume aceite de obrigaÃ§Ã£o, fechamento de ERP, pagamento, ciÃªncia oficial ou gratuidade. PDF de guia disponÃ­vel atualiza somente o estado de pagamento para â€œGuia disponÃ­velâ€ e deixa o trabalho aberto para a conferÃªncia definida em Q-40. Consulta DCTFWeb disponÃ­vel pode encerrar somente a atividade de obtenÃ§Ã£o do documento, com prova da fonte, sem declarar transmissÃ£o ou aceite. Consultas PARCSN concluÃ­das podem encerrar a atividade de consulta; DAS disponÃ­vel permanece aberto e separado de pagamento. Falhas e resultados incertos geram impedimento explicÃ¡vel; dispensa informada pela fonte requer confirmaÃ§Ã£o humana, nÃ£o Ã© dispensada automaticamente. Esta decisÃ£o implementa o escopo jÃ¡ aprovado de centralizar pendÃªncias e resultados, sem definir a regra comercial de reemissÃ£o D-149 nem substituir Q-40.

## D-156 â€” RecuperaÃ§Ã£o unificada das projeÃ§Ãµes locais da central

24/09/2026. Uma falha entre a persistÃªncia de um mÃ³dulo e sua projeÃ§Ã£o na central poderÃ¡ ser reparada por comando administrativo com escritÃ³rio explÃ­cito, que percorre somente dados jÃ¡ persistidos de NFS-e, Triagem, ConciliaÃ§Ã£o, folha, DTE, Radar e resultados Serpro. A execuÃ§Ã£o nÃ£o consulta fontes, nÃ£o emite/reemite/transmite, nÃ£o abre ciÃªncia oficial, nÃ£o reserva consumo e nÃ£o cria vÃ­nculos de Radar que nÃ£o tenham sido escolhidos por pessoa. Cada ponte conserva suas prÃ³prias condiÃ§Ãµes de idempotÃªncia, estados, provas e responsÃ¡veis; o comando apenas as invoca em sequÃªncia e informa quantidades por domÃ­nio. A execuÃ§Ã£o registra auditoria do resultado consolidado, sem atribuir autor humano inexistente. EscritÃ³rio de demonstraÃ§Ã£o ou inexistente Ã© recusado. Esta recuperaÃ§Ã£o nÃ£o alimenta estados de ERP ainda sem contrato comprovado e nÃ£o resolve D-149 ou Q-40.

## D-157 - Estado operacional exige capacidade declarada da fonte

24/09/2026. Uma observacao so pode alterar processamento quando a fonte bloqueada declarar `activity_processing_status`, ou obrigacao quando declarar `activity_obligation_status`. A declaracao e verificada dentro da transacao, depois de obter lock da fonte; uma capacidade removida nao pode ser usada por objeto em memoria desatualizado. Fonte em estado `disabled` nao pode alterar processamento ou obrigacao, mesmo que preserve capacidade declarada; falhas de leitura sem estado continuam registraveis para preservar indisponibilidade, mas nao autorizam inferencia de processamento ou obrigacao. A capacidade e somente um contrato tecnico: ela nao mapeia codigo do fornecedor, nao homologa Dominio/Siescon e nao transforma guia, envio ou consulta em aceite/pagamento.

## D-158 - Regra de custo exige definicao expressa do proprietario

24/09/2026. Sempre que um fluxo puder criar cobranca, alterar valor, escolher entre tarifa propria e repasse de fornecedor, ou atribuir custo a escritorio/empresa, o CICA deve solicitar definicao expressa do proprietario antes de implementar o comportamento. A autorizacao de reemissao com custo adicional por guia em D-149 nao autoriza inferir valor, base de calculo, moeda, impostos, momento de cobranca, reembolso ou modelo de repasse. Enquanto esses parametros nao existirem, preservar as tentativas e o estado incerto, sem habilitar emissao cobrada nem criar lancamento financeiro.

## D-159 - Desativacao explicita nao e revertida por retorno tardio

24/09/2026. Desativar uma fonte e uma decisao administrativa persistente. Uma observacao que chegar depois da desativacao pode ser mantida apenas como historico/auditoria, mas nao pode reativar a fonte, atualizar sua fotografia, tornar a atividade atual nem alterar processamento ou obrigacao. Uma falha tardia pode registrar indisponibilidade da atividade, sem substituir o estado `disabled` da fonte. A reativacao exige acao administrativa explicita; este comportamento nao cria contrato para Domínio ou Siescon.

## D-160 - Reativacao administrativa conservadora de fonte

24/09/2026. Owner ou administrador do escritorio, fora de sessao de suporte, pode reativar uma fonte explicitamente desativada na configuracao inicial mediante confirmacao visivel. Reativar muda somente o ciclo da fonte para `not_configured`, conserva capacidades, ultima fotografia e historico para auditoria e nao torna dados atuais, nao processa arquivo, nao agenda consulta, nao aciona agente nem concede novo acesso. O proximo retorno autorizado e capaz de atualizar o estado segundo seu contrato tecnico. Registrar ator, fonte e estados anterior/posterior em auditoria. A acao nao tem custo nem chama fornecedor.

## D-161 - Atribuicao recorrente exige carteira no momento da materializacao

24/09/2026. A atividade recorrente nunca pode receber responsavel apenas por ele ser membro do escritorio. Ao criar manualmente ou pelo worker, validar que modelo, atribuicao e empresa pertencem ao mesmo escritorio e que o responsavel ativo possui perfil operacional e carteira vigente para a empresa. Se uma atribuicao existente ficar invalida, gerar a atividade sem responsavel e registrar impedimento/auditoria explicavel; nao alterar o historico da atribuicao por uma geracao manual. Formularios administrativos devem recusar nova atribuicao incompatível. Isto fecha isolamento local e nao altera a regra de templates versionados.

## D-162 — Autor, vínculo atual e carteira na escrita de atividade

24/09/2026. Toda alteração de atividade (evidência humana, impedimento, conclusão e atribuição) deve confirmar no serviço que o autor autenticado corresponde ao membro atual do escritório, que ambos estão ativos, que o perfil atual é operacional e que a empresa continua na carteira vigente. Um objeto de membro carregado antes de revogação ou troca de perfil não autoriza a escrita. Esta revalidação complementa D-131 e não concede acesso, não altera atribuições nem reabre atividades.

## D-163 â€” RevisÃ£o integral da landing com foco na rotina do escritÃ³rio

24/09/2026. Origem: pedido explÃ­cito do proprietÃ¡rio para revisar e implementar uma landing simples, convincente, com pesquisa online e identidade prÃ³pria. Escopo: pÃ¡gina pÃºblica inicial, apresentaÃ§Ã£o e navegaÃ§Ã£o; nÃ£o inclui publicaÃ§Ã£o, mudanÃ§a comercial ou novas integraÃ§Ãµes. A direÃ§Ã£o preserva marfim/verde e tipografia editorial, apresenta primeiro pendÃªncias, responsÃ¡veis e prÃ³ximos passos, usa pauta ilustrativa identificada como exemplo e organiza recursos por tarefa. O teste de 14 dias sem cartÃ£o e sem cobranÃ§a automÃ¡tica continua conforme D-79; demo e Copiloto permanecem condicionados Ã  disponibilidade. NÃ£o publicar preÃ§os/limites numÃ©ricos substituÃ­dos por D-109, inventar prova social, retorno financeiro ou homologaÃ§Ã£o. DependÃªncias de integraÃ§Ãµes ficam em contexto prÃ³prio. Substituir cena animada e catÃ¡logo extenso inicial por conteÃºdo legÃ­vel sem JavaScript, controles nativos e CTA consistente. ReferÃªncias, auditoria e estados realmente inspecionados serÃ£o registrados na etapa 11 e em VALIDACOES.md.

## D-164 â€” Corrigir a landing servida e remover flechas

24/09/2026. Origem: correÃ§Ã£o explÃ­cita do proprietÃ¡rio apÃ³s capturas da pÃ¡gina desorganizada. O servidor local ativo continuou servindo HTML antigo em memÃ³ria com o CSS jÃ¡ atualizado; a revisÃ£o anterior validou uma instÃ¢ncia de QA e nÃ£o detectou essa divergÃªncia. Corrigir a instÃ¢ncia local efetivamente usada, desativar cache de templates apenas na configuraÃ§Ã£o de desenvolvimento para que ediÃ§Ãµes sejam visÃ­veis mesmo com --noreload, retirar flechas decorativas e organizar as aÃ§Ãµes de teste/demonstraÃ§Ã£o. Manter marca, condiÃ§Ãµes e limites de D-163; sem publicaÃ§Ã£o, mudanÃ§a de preÃ§o ou acesso externo. Validar o resultado no endereÃ§o 127.0.0.1:8000 e preservar os demais processos/dados do usuÃ¡rio.

## D-165 â€” SincronizaÃ§Ã£o local conclui todas as leituras allowlisted

24/09/2026. Ao terminar a paginaÃ§Ã£o de empresas DomÃ­nio Local, o agente deve continuar para a leitura de extratos bancÃ¡rios jÃ¡ allowlisted, salvo cancelamento explÃ­cito. Uma pÃ¡gina vazia ou final encerra somente a fase de empresas; nÃ£o encerra a execuÃ§Ã£o inteira. O download autenticado do agente deve usar o caminho e a consulta da URL previamente verificada contra o servidor configurado, mantendo a mesma origem protegida. Esta correÃ§Ã£o nÃ£o acrescenta SQL, capacidades, estados de fechamento, obrigaÃ§Ã£o, pagamento, integraÃ§Ã£o externa ou custo. A execuÃ§Ã£o real continua dependente do piloto autorizado da etapa 12.

## D-166 — Aplicar ai-design-skills à revisão da landing

24/09/2026. Origem: pedido explícito de instalar e usar ai-design-skills do GitHub. Instalada landing-page-design de elayadesign/ai-design-skills pelo instalador local. Aplicar fonte única Manrope com arquivo e licença locais, sem itálicos, escala tipográfica e espaçamento consistentes, botões com hierarquia e feedback e FAQ objetiva. Manter marfim/verde e tokens compartilhados de D-163, sem reproduzir navbar de vidro, gradientes e revelações que ocultem conteúdo: a simplicidade solicitada e a continuidade do produto prevalecem sobre esses padrões genéricos da skill. Não inventar depoimentos, métricas, preços ou disponibilidade. O fluxo principal permanece teste de 14 dias; demonstração secundária condicionada. Sem custo, implantação ou alteração de conta.

## D-167 — A demonstração visual é a prova principal da landing

24/09/2026. Origem: retorno explícito do proprietário de que a revisão retirou a tela que tornava o produto concreto e alterou pouco a composição percebida. Restaurar `cica_motion.html` como a principal demonstração do produto, imediatamente após a promessa e ocupando a largura útil da página. Reorganizar o hero para uma composição editorial própria, com uma única ação comercial dominante; a entrada na demo real continua secundária e condicionada. Manter os dados da tela identificados como ilustrativos, os seis módulos navegáveis, teclado, URL, movimento reduzido e conteúdo útil sem JavaScript. A pauta genérica deixa de ser o visual principal. Não criar métricas, depoimentos, preços, integrações homologadas ou promessa de conversão.

## D-168 — Refazer a landing do zero com linguagem visual neutra

24/09/2026. Origem: correção explícita posterior do proprietário, que rejeitou a restauração da composição anterior e o uso excessivo de verde. Esta decisão substitui a direção visual de D-163, D-166 e D-167, preservando apenas os limites comerciais e de disponibilidade já registrados. Refazer a página pública inicial sem reaproveitar `cica_motion.html`, com estrutura, composição e demonstração visual novas. Usar papel quente, grafite e terracota como base; reservar verde somente para estados positivos reais. A prova principal continua sendo uma representação do produto, criada do zero e identificada como ilustrativa, com dados fictícios. Manter um único CTA comercial dominante para o teste de 14 dias, demonstração secundária apenas quando disponível, integrações descritas com seus limites reais e ausência de preços, métricas, depoimentos, homologações ou ganhos inventados. A mudança não publica a página, não cria custo e não autoriza acesso externo.

## D-169 — Apresentar a landing como produto completo

24/09/2026. Origem: orientação explícita do proprietário após revisar a reconstrução D-168. Substituir a seção de três benefícios numerados, percebida como padrão de conteúdo gerado, por uma demonstração contínua e concreta da rotina. Substituir os três cards de disponibilidade das integrações por uma apresentação unificada de Domínio, Integra Contador, e-mail e Siescon como parte do produto pronto, removendo linguagem de roadmap, preparação, configuração e validação da landing. Ajustar as FAQs e os textos adjacentes para manter essa apresentação consistente. Permanecem a paleta neutra, o CTA de teste, a identificação de dados fictícios e a proibição de inventar preços, clientes, métricas ou depoimentos. Esta decisão altera a comunicação pública solicitada; não executa integração, acesso externo, custo ou publicação.

**Complemento D-166 (24/09/2026):** por pedido explícito posterior, tornar landing-page-design obrigatória globalmente para toda landing page. Regra adicionada em C:/Users/gege/.codex/AGENTS.md sem substituir as obrigações anteriores. A instalação é local e não implica custo ou publicação.

## D-170 — Fedrizzi é parceiro interno de homologação sem cobrança

25/09/2026. Origem: confirmação explícita do proprietário. A Fedrizzi Contabilidade é escritório parceiro interno de testes. Sua ativação operacional não cria contrato comercial, fatura, assinatura Asaas, consumo cobrado, preço, franquia paga ou obrigação de cobrança. O Console de desenvolvimento deve permitir marcar e desmarcar essa condição de modo explícito e auditado; ao marcar, pode liberar o ciclo operacional sem contrato comercial, mas não habilita automaticamente serviços externos, IA, emissão, transmissão ou ciência oficial. Ao desmarcar, sem contrato comercial vigente, o acesso operacional deve voltar ao estado pendente. O escritório continua sujeito a isolamento, permissões, auditoria e confirmações humanas. Esta decisão é exclusiva da Fedrizzi enquanto a condição estiver marcada; não altera a oferta comercial dos demais escritórios.

## D-171 — Prévia navegável da landing

25/09/2026. Origem: pedido explícito do proprietário para que a prévia visual da landing permita clicar nas áreas apresentadas. A janela ilustrativa pública passa a oferecer uma tela por área — Central, Meu trabalho, Empresas, Documentos, Fiscal e Conciliação — usando somente conteúdo fictício, sem autenticação, leitura de dados, escrita, integração, consumo ou efeito operacional. O estado selecionado deve ser perceptível, acessível por teclado e refletido na âncora da URL para permitir abrir a tela demonstrada; “Meu trabalho” é a visão inicial. A prévia não substitui as telas autenticadas, suas permissões nem suas situações reais.

## D-172 — Interface autenticada segue a linguagem da landing

25/09/2026. Origem: pedido explícito do proprietário para refazer as telas antigas de cadastro e operação seguindo a landing atual. A experiência autenticada deve usar o mesmo papel quente, grafite, terracota, Manrope, contraste e hierarquia da landing, preservando formulários, rotas, permissões, estados, mensagens, dados e fluxos existentes. A entrada, o cadastro, a configuração inicial e a navegação operacional receberão primeiro a camada compartilhada; telas especializadas passam a herdá-la e serão refinadas progressivamente sem substituir comportamentos por maquetes. Verde continua reservado a estados positivos. Não há alteração comercial, de integração ou de dados.

## D-173 — Copy da faixa de problema da landing

25/09/2026. O proprietário escolheu substituir a frase da faixa ?O problema real? por ?Atraso não é falta de esforço. É falta de contexto.?. A alteração é somente editorial e preserva a estrutura, os limites comerciais e a identificação da landing.

## D-174 — Faixa de problema sem rótulo

25/09/2026. O proprietário pediu remover o rótulo ?O problema real? da faixa da landing. A seção passa a exibir somente a frase escolhida em D-173.

## D-175 — Venda isolada de NFS-e, backup 07129 e publicação no Fly.io

28/09/2026. Origem: pedido explícito do proprietário. A oferta deve permitir contratar um escritório com somente o módulo NFS-e, mantendo empresas, certificados, equipe e integrações estritamente necessárias ao módulo e recusando os demais módulos e a Central de Atividades inclusive por URL direta. O preço, a vigência, a cobrança e o responsável do escritório não foram informados e não podem ser inventados; a liberação comercial concreta depende desses dados, mas o isolamento técnico pode ser validado agora.

O arquivo autorizado `07129_20260923_2000C.dom`, já baixado na máquina do proprietário, pode ser aberto localmente em cópia temporária somente leitura para descobrir empresas, acumuladores e o contrato real do extrator. O original deve permanecer inalterado; dados identificáveis não devem ser impressos em logs ou incorporados ao repositório. Resultados normalizados somente entram no CICA depois de vinculados ao escritório correto e conferidos contra a fonte.

Foi solicitada a publicação no Fly.io e autorizada a criação da organização/aplicação. Recursos faturáveis continuam sujeitos ao limite global de custo: antes de provisionar máquinas, banco, Redis ou storage cujo total estimado seja de US$ 1,00 ou mais, apresentar a arquitetura, o custo incremental e obter confirmação específica. A publicação não transforma coleta ADN, importação Domínio ou qualquer integração pendente em homologada.

## D-176 — Fly Postgres não gerenciado e infraestrutura enxuta

28/09/2026. Origem: correção explícita do proprietário. Não usar Fly Managed Postgres. A publicação deve partir do Fly Postgres não gerenciado (legacy/unmanaged), dimensionado no menor piso operacional razoável e com caminho documentado para ampliar memória, adicionar réplica e separar processos sem trocar a aplicação. Banco transacional e base de conhecimento podem ocupar bancos lógicos distintos no mesmo cluster para evitar duplicar infraestrutura. Redis/Valkey também deve começar autogerenciado e isolado, evitando o custo fixo do Upstash; a operação, os backups e a recuperação passam a ser responsabilidade do projeto. A escolha reduz custo, mas não pode ser descrita como alta disponibilidade enquanto existir uma única instância. Qualquer provisionamento faturável continua dependendo da aprovação específica do novo total estimado.

## D-177 — Publicação Fly.io aprovada na arquitetura de US$ 11,28/mês

28/09/2026. Origem: autorização explícita do proprietário para provisionar a arquitetura previamente estimada em aproximadamente US$ 11,28/mês. A produção usa uma máquina web de 512 MB, uma máquina worker/agendador de 512 MB, Fly Postgres não gerenciado de 256 MB com volume criptografado de 3 GB, Valkey autogerenciado de 256 MB com volume criptografado de 1 GB e bucket Tigris privado. Banco principal e base de conhecimento são bancos lógicos distintos no mesmo Postgres. Esta topologia possui caminho de escala, mas, com uma instância de cada serviço de dados, não é alta disponibilidade. Snapshots de volume não equivalem a restauração homologada nem a backup contínuo de WAL. Domínio próprio e certificado dependem do hostname exato fornecido pelo proprietário.

## D-178 — Backup 07129 pertence à Bianchi & Rizzotto e o tenant é somente NFS-e

28/09/2026. Origem: confirmação explícita do proprietário. O backup `07129_20260923_2000C.dom` pertence ao escritório Bianchi & Rizzotto. Seus dados normalizados devem ser vinculados exclusivamente ao tenant `bianchi-rizzotto`, cuja oferta contém somente NFS-e; os outros módulos devem possuir registros explícitos desabilitados. Empresas e acumuladores não podem ser inventados ou copiados de outro escritório. A credencial do portal/geração do backup não substitui a credencial interna de Usuário Externo do SQL Anywhere.

## D-179 — Domínio público definitivo da CICA

28/09/2026. Origem: confirmação explícita do proprietário. O domínio público da aplicação é `cicacontabil.com.br`, com `www.cicacontabil.com.br` como hostname adicional. Ambos devem apontar para `cica-contabil` no Fly.io, possuir certificado válido e constar explicitamente em `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`. O registro A legado `162.240.81.81` da HostGator deve ser removido; manter dois destinos concorrentes não constitui redundância e distribui conexões para um servidor que não hospeda a aplicação.

## D-180 — Acesso local ao backup 07129 com Gerente/gerente

28/09/2026. Origem: orientação explícita do proprietário. `Gerente/gerente` deve ser usado somente na tela de login do aplicativo Domínio Contábil; não é credencial ODBC e não deve ser repetido como usuário do SQL Anywhere. A cópia temporária do backup permanece isolada do banco original. Para evitar alterar a conexão instalada do escritório, usar o DSN de usuário `CICA07129`, apontado ao servidor local em `127.0.0.1:2638`, e manter o perfil do Domínio do usuário selecionando esse DSN durante a leitura. O DSN e o perfil temporário devem ser removidos ou revertidos ao concluir a extração. Nenhuma linha será enviada à produção antes da leitura completa, normalização, contagem e vínculo exclusivo ao tenant `bianchi-rizzotto`.

## D-181 — Senha Gerente do backup restaurado não será presumida

28/09/2026. Origem: falha observada pelo proprietário ao tentar `Gerente/gerente` na cópia restaurada e verificação da documentação oficial. A credencial `Gerente/gerente` documentada aplica-se à base criada por uma instalação demonstrativa nova; ela não redefine a senha contida em um backup existente. No backup 07129, usar somente a senha de Gerente vigente no escritório na data da cópia ou o procedimento oficial de recuperação. Não testar listas de senhas, não alterar hashes e não contornar a autenticação. A alternativa suportada é a pergunta/resposta pelo botão `?`; se não estiver configurada ou não funcionar para GERENTE, a Thomson Reuters orienta contatar o suporte para recuperação ou troca da senha do banco.

## D-182 — Bootstrap do primeiro administrador da produção

28/09/2026. Origem: relato explícito do proprietário de que o login administrativo `suporte@mewstack.com.br` era recusado. A inspeção do banco principal de produção confirmou que não existia nenhum usuário, superusuário ou acesso de plataforma. Criar esse endereço como primeiro usuário ativo, com papel `admin` da plataforma, MFA obrigatório e senha inicial aleatória; limpar somente as tentativas de autenticação desse identificador. Não vincular o administrador a tenant, não criar contrato e não reutilizar credencial do Domínio. O bootstrap deve gerar evento de auditoria e a senha inicial deve ser entregue uma única vez ao proprietário.

## D-183 — Remover códigos de recuperação e o verde dominante

28/09/2026. Origem: correção visual e de fluxo explicitamente solicitada pelo proprietário após o primeiro acesso em produção. O cadastro e a verificação do segundo fator continuam usando TOTP, mas o produto deixa de gerar, aceitar, regenerar ou exibir códigos de recuperação. Depois de confirmar o autenticador, encaminhar diretamente ao destino autorizado. Códigos existentes devem ser invalidados; se o autenticador for perdido, a recuperação passa pelo administrador. A remoção reduz a alternativa de contingência e é uma escolha explícita do produto.

A linguagem visual compartilhada de autenticação, console e área do escritório deve abandonar o verde como superfície, navegação e ação dominante. Usar papel quente/grafite no tema claro, carvão/neutros quentes no escuro e terracota somente como acento e foco; verde fica reservado a estados positivos reais. Corrigir tokens na origem e referências legadas que sobrescrevem os tokens de autenticação, em vez de aplicar exceção apenas à tela observada.

## D-184 — Kit oficial e correção integral de UX/UI

28/09/2026. Origem: plano de implementação explicitamente aprovado pelo proprietário. Esta decisão substitui somente a direção cromática do segundo parágrafo da D-183; a remoção dos códigos de recuperação, o fluxo TOTP e os limites funcionais daquela decisão permanecem válidos. Os oito SVGs de `CICA.zip` passam a ser os ativos oficiais, sem alteração de geometria ou proporção: lockup CICA verde ou preto em superfícies claras, creme ou branco em superfícies escuras, e símbolo CA equivalente em espaços compactos. O monograma “C” improvisado deixa de representar a marca.

A base visual compartilhada usa `#114d44` como cor de marca, ação primária e seleção controlada, `#e3ddca` como base institucional e preto/branco para contraste; informação, atenção, erro e sucesso mantêm cores semânticas distintas e acessíveis. Terracota deixa de ser assinatura principal, e verde não deve ocupar grandes superfícies de navegação ou painéis: a estrutura permanece neutra, densa e adequada à rotina contábil. Manrope local, temas claro/escuro/sistema e movimento discreto permanecem. A revisão abrange site público, demonstração, cadastro, autenticação/MFA, área dos escritórios, módulos operacionais, Copiloto, aprendizado e Console Mewstack; Django Admin e e-mails transacionais ficam fora. Preservar URLs, APIs, permissões, regras fiscais, integrações e contratos existentes, sem migração de banco, deploy, chamadas reais, mensagens ou custos externos.

## D-185 — Leitura suportada e carga integral do backup 07129

28/09/2026. Origem: credencial `GERENTE`/`lua` confirmada pelo proprietário e pedido explícito de concluir a carga. A cópia isolada foi atualizada com o pacote oficial Thomson Reuters `C106A0810.exe`, validado pelo checksum publicado e por assinatura digital válida. Pelo próprio cadastro de usuários do Domínio foi criado um acesso externo somente leitura exclusivo para a extração; essa credencial não será registrada no repositório nem reutilizada como acesso de aplicação.

A importação usa exclusivamente `bethadba.geempre` e `bethadba.EFACUMULADOR`, vinculada ao tenant `bianchi-rizzotto` e à fotografia de 23/09/2026 20:00 America/Sao_Paulo. A carga deve ser idempotente pelo hash já validado do `.dom`, conservar o lote e o histórico de acumuladores para auditoria e somente concluir se as contagens de origem e destino coincidirem sem erros. O usuário externo, o DSN, a extração e os arquivos intermediários devem ser eliminados após a validação; o `.dom` original permanece intacto.

## D-186 — Histórico compacto para sugerir acumulador por contraparte e serviço

28/09/2026. Origem: pedido explícito do proprietário para que cada empresa preserve os dados necessários para reencontrar o acumulador quando chegar a nota do mês seguinte. Além do catálogo de D-185, a cópia autorizada pode ler o histórico de NFS-e prestadas e tomadas somente para produzir observações agregadas por empresa, acumulador, código de serviço e contraparte pseudonimizada. Cada combinação conserva apenas frequência e último uso; número da nota, valor, descrição, nome e XML históricos não entram nessa carga.

A contraparte deve usar a mesma normalização da coleta NFS-e atual: CNPJ/CPF somente em memória, reduzido a SHA-256 truncado antes da transmissão ou persistência. A carga rejeita observação sem serviço e sem contraparte, acumulador fora do catálogo da própria empresa, frequência inválida e data ausente. Regras explícitas continuam prioritárias; histórico serve para sugestão explicável e nunca autoriza tratamento fiscal. Ambiguidade, dado novo ou evidência insuficiente permanece em revisão humana. A extração deve agregar na origem, paginar a resposta, ser idempotente pela chave agregada e não registrar conteúdo identificável em logs ou no repositório.

## D-187 — Exceção temporária de MFA do administrador da plataforma

29/09/2026. Origem: instrução explícita do proprietário após o autenticador vinculado recusar o código apresentado. Desabilitar temporariamente a exigência de MFA somente para `suporte@mewstack.com.br` e remover o dispositivo TOTP inválido dessa conta, sem alterar senha, papel `admin`, outras contas ou a política geral de segundo fator. A mudança deve ser auditada e o login real precisa ser validado até o Console. A reativação futura exigirá novo pareamento do autenticador e nova instrução do proprietário.

## D-188 — Console de escritório orientado a decisões e convites com papéis reais

29/09/2026. Origem: rejeição explícita da tela extensa e do convite restrito a proprietário. O detalhe do escritório no Console passa a priorizar sistemas e administração, condensar equipe, comercial e operação no mesmo contexto e recolher homologção e configurações avançadas. Seções vazias de cobrança e tentativas Claude não ocupam a tela; aparecem somente quando houver registro. O convite deve oferecer os papéis vigentes de proprietário, administrador, gestor, operador, financeiro e auditor, preservando as permissões existentes e sem ressuscitar o papel legado genérico.

Falhas de entrega deixam de ser ocultadas por um resumo genérico: erro de campo aponta ao controle e erro operacional informa a próxima correção segura. A produção foi encontrada sem servidor SMTP e remetente configurados; nenhuma credencial será inventada e nenhum convite deve persistir quando o envio falhar. Esta decisão implementa a tela localmente dentro de D-184 e não altera contrato, ciclo operacional, cobrança, API externa nem autoriza deploy.

## D-189 — Bianchi & Rizzotto é o piloto real da primeira liberação NFS-e

29/09/2026. Origem: plano de conclusão aprovado explicitamente pelo proprietário. A primeira liberação comercial completa será o produto exclusivo NFS-e do tenant `bianchi-rizzotto`; os demais módulos permanecem desabilitados e não podem ser apresentados como homologados. A liberação exige piloto real com certificado A1 e autorização fornecidos por canal seguro, coleta em ambiente de prova e oficial, amostra de 200 documentos conforme D-73, zero duplicidade, associação incorreta ou vazamento, precisão mínima de 95% nas sugestões automáticas e revisão humana dos casos ambíguos. O pacote somente será tratado como importável depois de homologar o contrato Q-39 e conferir a importação no Domínio.

Até backup e restauração serem comprovados e o certificado autorizado ser validado, `NFSE_ADN_SYNC_ENABLED` permanece desabilitado. Mudanças de produção podem usar janela controlada de até 30 minutos, sempre com backup e retorno preparados; restauração completa conserva o RTO de quatro horas de D-73. Credenciais SMTP, certificado, senha e artefatos fiscais nunca entram no repositório, documentação ou chat. Se uma dependência externa não estiver disponível, os trabalhos independentes continuam, mas o módulo permanece bloqueado e não recebe declaração de homologação.

## D-190 — A dispensa temporária de MFA do administrador cobre todo o Console

29/09/2026. Origem: correção explícita do proprietário após a conta dispensada alcançar novamente a tela de cadastro TOTP. A exceção de D-187 vale para todo o fluxo da conta `suporte@mewstack.com.br`, inclusive Configurações do Console; uma view não pode impor um segundo gate divergente do `mfa_required=False` vigente. Enquanto a exceção estiver ativa, acesso direto às rotas de cadastro, verificação e QR de MFA deve retornar ao Console sem criar dispositivo. O segredo TOTP exibido na captura é considerado comprometido; o dispositivo não confirmado correspondente deve ser eliminado e o fato registrado em auditoria, sem persistir a chave. Nenhuma outra conta ou política de MFA é dispensada por esta decisão.

## D-191 — Nomes de convidados não usam corretor ortográfico

29/09/2026. Origem: solicitação explícita do proprietário após o navegador sublinhar um nome curto e exibir o indicador do corretor no modal de convite. O campo de nome próprio mantém autocomplete e foco acessível, mas usa `spellcheck=false`; e-mail já seguia a mesma proteção. A mudança não altera validação, dados ou permissões.

## D-192 — MFA opcional e altamente recomendado para clientes

29/09/2026. Origem: instrução explícita do proprietário. Contas que acessam somente um ou mais escritórios clientes não são bloqueadas por ausência de MFA, independentemente de contrato, fim do teste ou preferência histórica do escritório. A configuração permanece disponível e deve ser apresentada como proteção altamente recomendada, com estado e ação claros no primeiro acesso. Depois que o cliente ativa TOTP voluntariamente, o segundo fator passa a proteger os logins seguintes; “opcional” significa escolher ativar, não cadastrar um fator que seria ignorado. Contas internas com acesso ao Console da plataforma continuam obrigadas quando `PlatformAccess.mfa_required=True`; a exceção temporária de D-187/D-190 continua restrita ao administrador indicado.

## D-192 — Certificados por metadados e lote sem seleção manual de empresa

29/09/2026. Origem: pedido explícito do proprietário. O cadastro de A1 passa a aceitar um ou vários arquivos `.pfx`/`.p12` na mesma ação. O servidor abre cada arquivo localmente, extrai o CNPJ do campo ICP-Brasil `Subject Alternative Name` OID `2.16.76.1.3.3`, com compatibilidade restrita ao assunto legado, e vincula somente por CNPJ completo e válido a uma empresa acessível do mesmo escritório. Empresa e identificação deixam de ser exigidas do usuário; a identificação deriva do nome comum do certificado, sem copiar o nome do arquivo.

A senha pode ser comum ao lote ou inferida localmente por convenções explícitas no nome (`senha=VALOR`, sufixo `__VALOR` ou `[VALOR]`). Não usar IA nem enviar nome, senha ou certificado a serviço externo. O nome bruto do arquivo, que pode conter a senha, não entra em banco, auditoria, mensagens ou documentação. Arquivo ilegível, senha não encontrada, CNPJ ausente/inválido, empresa sem correspondência, duplicidade ou limite excedido fica como “não reconhecido” no resultado da própria importação; nesse caso o arquivo e a senha não são guardados. A importação não ativa coleta ADN nem constitui homologação do certificado em ambiente externo.

## D-193 — Fila de certificados com senha por arquivo

29/09/2026. Origem: correção explícita do proprietário sobre o fluxo real do lote. Além das convenções anteriores, a senha pode ser inferida localmente de `Empresa - SENHA.pfx` e do último termo numérico em `Empresa SENHA.pfx`. Não existe limite funcional artificial de 50 certificados: o navegador envia um arquivo por vez, em sequência. Se a abertura falhar, a fila pausa no arquivo atual, solicita a senha em campo normal e permite tentar novamente ou pular; depois continua sem perder os resultados anteriores. Arquivos rejeitados e suas senhas não são guardados. Nome bruto, senha e conteúdo continuam proibidos em sessão, mensagens, auditoria e logs.

## D-194 — Nome do arquivo visível somente na fila local

29/09/2026. Origem: correção explícita do proprietário. Durante a importação, a fila e o pedido de senha exibem o nome real do arquivo para o operador identificar qual A1 precisa de atenção. Essa exibição usa exclusivamente o objeto `File` já presente no navegador; o servidor continua sem devolver, persistir ou registrar o nome, que pode conter senha. O painel de tentativa fica compacto: posição, nome, campo de senha, tentar e pular.

## D-195 — Certificado prepara a coleta sem bloquear outras empresas

29/09/2026. Origem: instrução explícita do proprietário. Esta decisão substitui a última frase de D-192 que impedia o upload de preparar a coleta. Um A1 vigente e correlacionado passa a criar ou atualizar automaticamente a sincronização NFS-e da própria empresa; quando o runtime ADN estiver habilitado, a primeira coleta entra na fila após o commit. Enquanto o gate de D-189 estiver fechado, a sincronização fica pronta e auditada, sem chamada externa.

Certificado vencido, revogado, incompatível ou ausente nunca bloqueia a carteira: a empresa correspondente é ignorada e sinalizada, enquanto cada empresa com A1 vigente segue em tarefa isolada. Um A1 já vencido pode permanecer cadastrado como evidência, mas não habilita nem agenda coleta. A página de certificados abre com todos os registros visíveis, distingue empresas com e sem A1 válido e o modal de importação só abre por ação explícita. A fila pode ser cancelada ou fechada, preserva resultados já confirmados e converte resposta HTML/erro transitório em recuperação por arquivo, sem exibir erro técnico bruto.
## D-196 — Coleta NFS-e liberada globalmente após cadastro de A1 válido (29/09/2026)

O proprietário autorizou explicitamente a coleta NFS-e para todos os clientes. A flag de produção `NFSE_ADN_SYNC_ENABLED` deve permanecer ativa. O cadastro de um A1 válido habilita e enfileira a coleta da empresa correspondente; certificado vencido, revogado, incompatível ou ausente pausa somente aquela empresa e nunca bloqueia as demais. A interface não deve exibir aviso de liberação pendente da Mewstack. Esta decisão substitui o gate operacional de D-189 e D-195 para a ativação global, sem dispensar isolamento por tenant, auditoria ou tratamento conservador de falhas.
## D-197 — Fila NFS-e visível e atualizada automaticamente (29/09/2026)

A tela de coleta exibirá um painel operacional por empresa, atualizado em intervalos curtos sem recarregar a página, com os estados na fila, coletando, concluída, nova tentativa, ignorada e falhou. O painel deve mostrar totais, empresa, explicação curta e horário da atualização; empresas sem A1 válido aparecem como ignoradas e não contaminam o estado das demais. A tabela detalhada e as ações administrativas permanecem como fonte complementar.
## D-198 — Bianchi usa o ADN oficial para documentos reais (29/09/2026)

O proprietário solicitou e autorizou a baixa real de todas as empresas elegíveis da Bianchi & Rizzotto. O ambiente `trial` respondeu HTTP 404 para a carteira real e não serve como origem dos documentos oficiais; produção passa a usar `NFSE_ADN_ENVIRONMENT=production`. A troca não permite repetir indiscriminadamente resultados incertos: apenas sincronizações sem sucesso ou com erro são reenfileiradas, mantendo checkpoint, deduplicação, isolamento por empresa e auditoria.
## D-199 — Retentativa NFS-e sem recarregar ou perder posição (29/09/2026)

Falhas individuais da coleta terão retentativa explícita por empresa e retentativa conjunta apenas das falhas, executadas por requisição assíncrona com CSRF, escopo da carteira e permissão administrativa. A ação não reinicia empresas concluídas ou em processamento e não recarrega a tela. Retentativas automáticas continuam usando backoff para falhas transitórias; falhas definitivas exigem ação humana depois da correção da causa.
## D-200 — Coleta NFS-e cadenciada para proteger produção (29/09/2026)

A coleta real será processada em ritmo limitado por worker, preservando isolamento e evitando que uma importação grande degrade PostgreSQL e a navegação. O dispatcher recupera automaticamente leases vencidos como nova tentativa. A fila pode conter muitas empresas, mas a execução é cadenciada; velocidade não tem prioridade sobre disponibilidade e integridade.

## D-201 — Uma empresa conclui todos os NSUs antes da próxima (29/09/2026)

A unidade visível da fila é a empresa, não o lote técnico do ADN. O worker consulta internamente lotes oficiais de até 50 documentos e continua a mesma empresa até `ultNSU` alcançar `maxNSU`; somente então libera a próxima empresa. `checkpoint_nsu`, `max_nsu` e o NSU de cada documento ficam persistidos para retomada e deduplicação. Uma tarefa pode ceder após dez páginas para proteger banco e worker, mas deve reenfileirar a mesma empresa antes de acionar o dispatcher global. Certificados inválidos são ignorados por empresa e não bloqueiam a fila.

## D-202 — Classificação fiscal na própria lista de notas (29/09/2026)

A tela separada de revisões deixa de integrar a navegação e sua URL antiga redireciona para `Notas` filtrada pelas pendências. Cada nota pendente oferece acumulador e ação `Classificar` na própria linha; evidência e XML ficam em detalhe recolhido, sem navegação obrigatória. A primeira abertura de `Notas` usa a competência imediatamente anterior ao mês atual, inclusive dezembro do ano anterior quando o mês atual for janeiro; filtros escolhidos explicitamente pelo usuário prevalecem.

## D-203 — Notas agrupadas por empresa e estado binário (29/09/2026)

A tela principal agrupa as notas por empresa em seções expansíveis e usa somente os estados operacionais `Classificada` e `Não classificada`; o filtro oferece `Todas`, `Classificadas` e `Não classificadas`. Cada nota classificada e cada grupo de empresa podem gerar e baixar diretamente o ZIP auditável vigente, sem abrir a aba de exportações. O pacote continua identificado tecnicamente como conferência enquanto Q-39 não fornecer e homologar o layout da rotina automática do Domínio; a interface não pode prometer importação automática antes desse aceite.

## D-204 — Operação NFS-e por número da nota, correção e seleção em lote (29/09/2026)

Origem: correção explícita do proprietário sobre o fluxo diário. A lista de NFS-e passa a mostrar o número/código fiscal normalizado da nota, sem expor hash ou NSU como identificação operacional. Hash e NSU permanecem apenas na rastreabilidade interna e nos artefatos auditáveis. Quando a fonte não fornecer o número, a tela declara a ausência em vez de substituir silenciosamente pelo NSU.

Proprietário, administrador, gestor e operador podem corrigir o acumulador de uma nota classificada diretamente na lista, escolhendo somente um código vigente ou observado da mesma empresa. A correção não altera nem apaga a classificação anterior: cria novo artefato e nova entrada no histórico, identifica responsável e instante e faz os próximos downloads usarem a decisão mais recente. A tela oferece seleção por nota, por empresa exibida, por página e por todos os resultados classificados do filtro atual, inclusive entre páginas e empresas; a ação informa a quantidade antes do download. Enquanto Q-39 continuar aberto, o resultado permanece denominado pacote de conferência com XMLs e manifesto, sem promessa de layout importável ou importação concluída no Domínio.

## D-205 — PostgreSQL no Neon e processamento no Fly (29/09/2026)

Origem: instrução explícita do proprietário para separar definitivamente banco e processamento. O Fly permanece responsável por web, worker, fila e balanceamento; os bancos lógicos `cica_main` e `cica_knowledge` migram para o projeto Neon `raspy-river-46466568`, branch `production`, região São Paulo. A aplicação usa endpoint pooled e releases/migrations usam endpoints diretos. O Postgres legado do Fly permanece intacto durante a janela de rollback e só pode ser removido em decisão posterior.

O corte de produção exige dump consistente dos dois bancos com checksum, restauração sem erro, schema normalizado idêntico, contagem e hash de conteúdo idênticos para todas as tabelas, migrations limpas e leitura real pelos dois aliases Django. Enquanto essa barreira não estiver verde, a produção continua no Fly Postgres. A credencial Neon exposta por diagnóstico foi rotacionada antes de qualquer uso em produção.

## D-206 — Acumulador Domínio identificado pela tag ACU em qualquer profundidade (29/09/2026)

Origem: esclarecimento explícito do proprietário sobre o conjunto de dados do Domínio. A integração identifica acumulador pelo nome local da tag XML `ACU`, percorrendo o documento inteiro e ignorando qual seja seu pai ou namespace. O XML derivado para conferência deve conter `ACU` com o código da decisão mais recente; quando existir `prod`, a tag pode ficar dentro dele, e XMLs NFS-e sem `prod` recebem a tag na raiz. Uma `ACU` já existente é atualizada, não tratada como caminho fixo. O XML fiscal original persistido permanece imutável.

## D-207 — Empresa pausada continua acessível pelo cadastro (30/09/2026)

Origem: falha encontrada no smoke test real da Bianchi após a migração. Uma empresa pausada aparecia corretamente no cadastro, mas o detalhe usava o escopo operacional restrito a empresas ativas e devolvia 404 para o link gerado pela própria lista. O detalhe passa a aceitar empresas ativas ou pausadas do mesmo escritório, preservando integralmente os limites de carteira, tenant e sessão de suporte. Pausar uma empresa impede operações automáticas aplicáveis; não apaga nem torna inacessível seu histórico cadastral.

## D-208 — PostgreSQL legado do Fly desligado após corte para o Neon (30/09/2026)

Origem: instrução explícita do proprietário. Depois de confirmar que os aliases de produção usam exclusivamente o Neon e que a release, o worker e o health estão saudáveis, a máquina do PostgreSQL legado `cica-contabil-db` deve ser parada. A máquina e seu volume não serão destruídos nesta ação, preservando um rollback recuperável; qualquer remoção definitiva continua exigindo instrução específica.

## D-209 — Fechar tudo que for tecnicamente executável e auditar as promessas das telas (30/09/2026)

Origem: instrução explícita do proprietário. O trabalho atual pode avançar em todas as etapas e módulos para corrigir defeitos, fechar pendências locais, endurecer a operação, executar testes e revisar em navegador se cada tela e interação cumpre o comportamento prometido. A revisão deve confrontar interface, permissão, estado persistido, efeitos colaterais, falhas, estados vazios e responsividade; texto ou botão existente não constitui prova funcional.

Continuam fora da autorização implícita decisões comerciais, fiscais, jurídicas ou de retenção ainda abertas; uso de credenciais, certificados ou dados que não estejam disponíveis por canal seguro; chamadas pagas, novas despesas, mensagens externas e homologações que dependam de fornecedor ou aceite humano. O executor deve resolver primeiro tudo que independe dessas entradas e, ao final, entregar uma lista objetiva do que somente o proprietário ou terceiros podem fornecer, decidir ou homologar. Nenhuma pendência externa pode ser marcada como concluída por simulação.

## D-211 — Reauditoria por facilidade de uso e descoberta das ações (30/09/2026)

Complemento seleção na configuração de Conciliação (01/10/2026): empresa explicitamente inválida, inacessível ou ambígua não pode ser substituída pela primeira da carteira. POST exige uma empresa explícita no corpo, sem herdar query string. Mostrar recuperação no próprio seletor, sem cadastros de outra empresa e sem executar alterações. Somente o GET inicial sem filtro mantém a seleção inicial existente. IDs de ações e ações desconhecidas devem ser recusados antes de consultar ou alterar registros; preservadas permissões, carteira e dados já persistidos.

Complemento descoberta e carteiras extensas na Conciliação (01/10/2026): os seletores de empresa da configuração, importação, filtro de movimentos e futura exportação devem aceitar busca progressiva por nome ou código sem trocar silenciosamente o contexto. Digitar não escolhe a primeira correspondência; a empresa só muda após seleção explícita. O controle nativo continua disponível sem JavaScript e a busca informa quantidade e ausência de resultados. A central deve apresentar a sequência real como 1. importar, 2. processar, 3. revisar e 4. exportar, mantendo a importação encontrável mesmo quando já existem dados. Perfis somente de consulta não recebem ação de escrita e o bloqueio de exportação Domínio continua explícito até Q-39 ser homologada.

Complemento Conciliação avançada (01/10/2026): no escritório demo, recusar leitura e escrita dos endpoints `reconciliation_*` de configuração, auditoria, arquivos, execução, movimentos e exportação antes de consultar esses dados. Preservar somente a central e a confirmação fictícia já isoladas por sessão. Aplicar a visitante, membro e suporte, sem alterar escritórios não-demo. Explicar o limite e oferecer retorno direto à comparação fictícia, sem sugerir problema de permissão ou tentativa posterior. Não representa homologação dos fluxos reais.

Complemento Conciliação (01/10/2026): listagem e confirmação do cenário fictício dependem do escritório demo, não do método de entrada. Membro autorizado e visitante usam progresso de sessão; auditor continua sem confirmação. Upload de arquivos não é permitido nesse escritório, inclusive via POST direto. Não ampliar funcionalidades contábeis nem considerar essa simulação homologação de importação/exportação.

Na demo, apresentar diretamente a comparação fictícia disponível, sem carregar painéis compartilhados de processamentos/movimentos/exportações. Informar esse limite; a navegação completa permanece no escritório não-demo. A revisão dos endpoints de configuração e ações avançadas continua separada, sem declarar isolamento integral antes dos respectivos testes.

Complemento DTE (01/10/2026): preparação deixa de ficar recolhida; atalho explícito no topo leva à seleção de empresas por âncora nativa, sem requisição, perda de filtros/seleção ou dependência de JavaScript. Consultas preparadas têm atalho secundário quando existem. Preservar preparo local, revisão e autorização separados, permissões e indicação de simulação; seleção demo não deve anunciar consumo Serpro. Referências: GOV.UK Details, GitHub execução manual e Shopify Polaris Page, adaptadas ao layout existente.

Complemento DTE demo (01/10/2026): preparação, autorização, cancelamento e abertura do teor ficam na sessão de qualquer usuário autorizado do escritório is_demo, não só do visitante público. Registros de referência permanecem imutáveis e a demo não prepara paginação externa. Permissão específica e confirmação da abertura continuam obrigatórias; não registrar ciência oficial nem liberar perfis de leitura.

Complemento de acompanhamento (01/10/2026): explicitar atualização de resultado como navegação GET sem nova consulta Serpro, reserva ou repetição automática. Preservar bloqueio de retorno incerto; exibir identificador local para conciliação, sem inventar resolução ou autorizar nova tentativa.

Complemento de lote (01/10/2026): manter a revisão de seleção/custo visível junto à tabela, explicar limite de 30 e seleção somente da página, sem executar antes da confirmação. Perfis somente de consulta não recebem seleção ou envio. Normalizar identificadores UUID antes de deduplicar e transmitir centavos sem localização; o backend continua revalidando escopo/custo.

Complemento DCTFWeb individual (01/10/2026): aplicar o mesmo progresso isolado por sessão do lote à consulta individual demo, sem serviços persistentes, cobrança ou documento oficial. Identificar explicitamente o resultado como simulação e não prometer PDF inexistente. Validar competência antes de qualquer efeito e preservar autorização/carteira. Não altera a consulta real nem substitui sua homologação.

Complemento de isolamento (01/10/2026): nos fluxos já simulados de Parcelamentos e lote DCTFWeb, a natureza fictícia depende do escritório `is_demo`, não do método de entrada. Visitante e membro autorizado do escritório de demonstração usam estado exclusivo da sessão, sem consultas, reservas ou registros fiscais compartilhados. Perfis de consulta e suporte não ganham autorização de execução. Não amplia serviços Serpro ou escopo fiscal homologado.

Origem: instrução explícita do proprietário. Reabrir a revisão de todas as telas, inclusive as já verificadas, priorizando encontrar, entender e concluir tarefas sem orientação externa. Pesquisar padrões e ideias de layout online antes das decisões de cada tela, além de UI/UX Pro Max e Watermelon. Iniciar pela descoberta do download em lote de NFS-e; usar nomes de tarefas claros, seleção com abrangência explícita e orientação quando faltarem dados ou classificação. Preservar permissões e o limite de homologação Q-39. O objetivo ativo inclui esta reauditoria; validação técnica anterior não constitui aceite de usabilidade.

Complemento de execução: aplicar o mesmo limite de acesso do cadastro ao atalho explícito de NFS-e de empresa pausada e à recuperação dos pacotes existentes. Identificar a pausa na tela; não incluir pausadas automaticamente na carteira operacional, reativar coletas ou ampliar acesso de colaboradores/CRMew/suporte restrito. Isso estende a consistência de D-207 ao histórico fiscal já disponível no cadastro.

## D-212 — Histórico de pacotes restrito à carteira atual (30/09/2026)

Complemento Central Integra (01/10/2026): o indicador de consultas DTE pendentes usa o mesmo escopo integral da fila, inclusive progresso da sessão para membros demo. Preparações demo com empresas removidas do escopo não são apresentadas como lotes parciais que o usuário não pode confirmar; histórico concluído continua restrito às empresas visíveis. Não alterar execução externa ou permissões.

Complemento D-209/D-211 (01/10/2026): aplicar também à fila DTE o escopo integral atual da carteira. Consultas preparadas mistas, vazias ou inconsistentes não aparecem nem podem ser autorizadas/retiradas por quem não tem acesso a todos os itens. Lista, contador e POST usam a mesma restrição; revogação vale na próxima requisição. Sem mudar layout, contrato ou executar chamadas externas.

Complemento de execução D-209/D-154 (01/10/2026): preparar no workflow existente a regressão PostgreSQL completa, após SQLite e antes de gerar imagens, usando serviço descartável sem credenciais de produção. Não usar `continue-on-error` nem seleção que deixe os testes concorrentes de fora. A edição local não dispara pipeline; aprovação remota do CI e eventual custo de execução permanecem sujeitos à validação antes de publicação.

Origem: revisão de segurança autorizada em D-209/D-211. A lista de downloads NFS-e só pode revelar pacotes cujas notas estejam integralmente no escopo atual do usuário, assim como o download. Pacote misto não é parcialmente exposto. Registrar vínculo relacional pacote/notas para aplicar a restrição no banco antes da paginação; reconstruir vínculos legados somente a partir de IDs válidos do manifesto e do mesmo tenant, sem alterar XML, ZIP ou snapshot. Registros incompletos ficam indisponíveis, sem inferir autorização. Revogação de acesso deve ter efeito na próxima consulta. Mudança local, sem autorização adicional de publicação/homologação.

## D-210 — Neon suspende somente em ociosidade real (30/09/2026)

Origem: instrução explícita do proprietário para reduzir o custo do Neon sem degradar funções, filas ou crescimento. O Fly Proxy verifica somente `/api/v1/health/live/`; `/api/v1/health/ready/` continua verificando banco e cache para releases e operação, mas deixa de consultar o Postgres a cada 15 segundos. O compute Neon mantém autoscaling de 0,25 a 1 CU e passa a suspender após 300 segundos sem atividade.

Trabalho normal continua imediato por Celery. Varreduras que existem apenas para recuperar uma entrega excepcional são alinhadas em janelas de 15 minutos, e integrações desabilitadas por configuração não entram na agenda até o próximo restart que as habilitar. A coleta NFS-e ativa, suas continuações de 30 segundos, checkpoints, leases e retentativas não são atrasados. O banco deve permanecer acordado sempre que existir coleta ou tráfego real; economia nunca tem prioridade sobre concluir trabalho autorizado.

Complemento D-211 — mapeamento de arquivos da Conciliação (01/10/2026): a etapa deve
mostrar arquivo, empresa, formato e posição na jornada antes dos controles; distinguir os
campos obrigatórios, a escolha alternativa entre valor com sinal e débito/crédito e os campos
opcionais. Sugestões automáticas permanecem revisáveis e nunca justificam processamento
silencioso. Erro preserva nome e escolhas, aparece em resumo focável e junto ao campo. Perfis
de consulta recebem apenas contexto e prévia. Salvar uma nova versão informa se realmente
iniciou processamento ou se servirá somente a arquivos futuros; nenhum processamento será
prometido quando não houver execução elegível. A prévia continua limitada e identificada como
amostra, sem modificar o arquivo original ou constituir homologação de formato bancário.

Complemento D-211 — filtro de competência dos fechamentos (01/10/2026): agrupar rótulo,
controle mensal e erro como um único campo, com o rótulo acima do input. A ação fica alinhada
à base do controle, usa texto curto e específico e não ocupa largura desnecessária no desktop;
no celular, campo e ação usam a largura disponível em uma coluna. Preservar o `input type=month`,
o valor na URL, o foco visível e a altura mínima de 44 px.

## D-213 — Demonstração operacional povoada em produção (01/10/2026)

Pedido explícito: popular melhor a demo em produção, incluindo atividades e uma rotina representativa. Autoriza atualizar exclusivamente o escritório marcado `is_demo` e publicar o código necessário para apresentar o cenário. Usar empresas e pessoas fictícias, atividades das quatro áreas, prazos relativos à data da preparação, modelos, responsáveis, impedimentos, evidências e histórico identificados como simulados. A entrada pessoal do visitante representa uma persona sintética estável, sem atribuir registros compartilhados à conta temporária. Preservar isolamento por sessão e bloqueios de escrita da demonstração; não consultar provedores, enviar mensagens, cobrar ou alterar escritórios reais. Seed transacional, repetível, com recusa explícita de tenant operacional; nenhum reset de senha. Aplicar em infraestrutura existente, com incremento estimado abaixo de US$ 1,00 e sem recurso recorrente novo. Validar o cenário publicado em desktop e celular e registrar contagens e limites reais.

## D-214 — Recuperação segura para token de formulário renovado (01/10/2026)

Origem: falha real apresentada pelo proprietário em `cicacontabil.com.br/app/aparencia/` e confirmada nos logs como `CSRF token from POST incorrect`. O Django renova o token após login; abas anteriores podem conservar um campo escondido inválido. Antes de enviar a preferência de aparência, o cliente deve obter um token atual do endpoint já existente, mantendo cookie `HttpOnly`, verificação CSRF e POST. Qualquer rejeição residual em tela HTML deve conservar status 403, não expor a página técnica padrão nem detalhes internos, informar que nada foi aplicado e oferecer retorno seguro à origem do mesmo host. APIs mantêm resposta JSON. Referências externas nunca podem virar destino de recuperação.

## D-215 — Página inicial orientada à próxima ação (01/10/2026)

Origem: avaliação explícita do proprietário e reauditoria de D-211. A página inicial não deve
apresentar estados técnicos repetidos como se fossem orientação de trabalho. Ela passa a abrir
com um resumo contextual do recorte atual, filtros de prioridade inteiramente acionáveis e uma
fila legível que responda: qual atividade, de qual empresa, quando vence e por que exige atenção.
Na visão pessoal, o responsável repetido é omitido; na Carteira e na Gestão, permanece visível.
Estado de processamento, obrigação e atualização continua preservado no detalhe, mas só aparece
na fila inicial quando representa exceção útil, como impedimento ou fonte indisponível. Prazo
relativo complementa a data exata sem substituir o prazo interno/legal. Nenhuma atividade é
reordenada ou encerrada automaticamente.

Referências adotadas: Linear My Issues (agrupamento por foco e propriedades exibidas sob demanda),
Asana My Tasks (Hoje, Próximas e Mais tarde), Karbon My Week (cartão resumido e detalhe sob demanda)
e Pageflows/Process Street (fila, filtro e detalhe como etapas separadas). Refero confirmou o uso
de telas reais de dashboard e SaaSFrame foi consultado para composição B2B, mas não expôs um fluxo
de tarefas verificável sem acesso pago. Watermelon não retornou correspondência após a busca focada
e a tentativa estreita. As referências foram adaptadas ao design e às permissões já existentes.

## D-216 — Pastas do pacote NFS-e identificam a empresa com segurança (01/10/2026)

Origem: reauditoria funcional de D-211 na produção. O download em lote estava operacional, mas
gerava diretórios como `Emitidas/0106 -/`: o código Domínio permanecia, enquanto o nome da empresa
prometido pela separação visual desaparecia. O pacote de demonstração e o pacote de conferência
não-demo passam a usar `código - nome da empresa`, com remoção de separadores de caminho,
caracteres de controle e nomes vazios. O manifesto e a fotografia auditável devem registrar o
mesmo caminho efetivamente gravado. O XML original, acumulador, escopo, permissões e o bloqueio de
homologação Q-39 permanecem inalterados.

## D-217 — Coleta NFS-e mostra uma verdade operacional e separa simulação (01/10/2026)

Origem: reauditoria funcional da tela “Coleta automática” após V-248. A demonstração não pode
apresentar “Produção” ou “acompanhamento ao vivo” quando nenhum provedor é consultado. Seu resumo,
fila e configuração devem usar o mesmo estado privado da sessão e afirmar explicitamente que a
execução é simulada. No escritório operacional, a tela continua refletindo somente dados
persistidos e autorizados.

A hierarquia passa a responder, nessa ordem: se existe algo que requer ação, o que está sendo
processado ou aguardando, e onde alterar a configuração por empresa. Certificado ausente,
falha/retry e pausa são estados distintos; “ignorada” não serve como rótulo genérico. A lista de
acompanhamento é a leitura principal e a tabela técnica/configuração fica secundária e expansível,
sem esconder a recuperação de falhas. Ações em lote preservam permissões, seleção explícita,
CSRF, escopo de carteira e confirmação de resultado. Nenhuma ativação simulada pode aparentar
sucesso para empresa sem A1 válido. Esta decisão não muda ADN, ordem global, checkpoint, regra
fiscal, custo, certificado real nem a homologação pendente Q-39.

## D-218 — Conciliação conduz pela exceção e preserva o trabalho inválido (01/10/2026)

Origem: continuação da reauditoria D-211 sobre a jornada não-demo. A entrada da Conciliação deve
mostrar uma próxima ação operacional, priorizando conflito e pendência antes de volume total. A
sequência Importar → Processar → Revisar → Exportar permanece, mas cada etapa informa seu estado e
leva diretamente ao trabalho correspondente; métricas descritivas não competem com a ação.

O mapeamento de CSV/XLSX deve explicar origem e destino, marcar os campos essenciais, preservar
nome e escolhas quando houver erro e devolver um resumo focável com links para os campos. Data e
Histórico são obrigatórios; o valor exige exatamente uma estratégia válida: Valor com sinal ou o
par Débito/Crédito. Coluna ausente ou reutilizada continua recusada pelo serviço. Filtros explícitos
inválidos não podem ampliar silenciosamente a carteira: devem resultar em erro recuperável e zero
movimentos exibidos.

Referências adotadas: Xero para revisão humana apenas quando a automação não tem confiança,
QuickBooks para conferir diferenças antes de concluir e BlackLine para filas orientadas a exceção,
evidência e workflow por papel. Watermelon não retornou correspondência após busca focada e retry;
UI/UX Pro Max reforçou resumo de erros focável, erro em linha, recuperação concreta e alvos web.
Permissões, trilha imutável, regras contábeis, exportação bloqueada e homologação Q-39 permanecem
inalteradas.

## D-219 — Senhas passam a aceitar o mínimo de 8 caracteres (01/10/2026)

Origem: pedido explícito do proprietário. Cadastro, ativação por convite e redefinição de senha
devem aceitar senhas a partir de 8 caracteres e rejeitar as de 7 ou menos, com a mesma regra na
validação do servidor, nos atributos do navegador, nas mensagens de ajuda e na documentação.
Continuam ativos Argon2, bloqueio e limitação de tentativas, erros de autenticação neutros e, nos
fluxos que já usam a validação global do Django, os bloqueios de senha comum, exclusivamente
numérica e semelhante aos dados da conta. A mudança não reduz senhas existentes, não exige troca
periódica e não cria regra de composição. Senhas mais longas e gerenciadores continuam
recomendados. O mínimo de 8 é uma decisão explícita de produto; a referência NIST SP 800-63B-4
exige 15 quando a senha é o único fator e admite 8 quando ela integra autenticação multifator,
portanto MFA permanece necessária para contas importantes e privilegiadas.

## D-220 — Pasta NFS-e usa somente `código-` no padrão Domínio (01/10/2026)

Origem: correção explícita do proprietário, que substitui a parte de D-62/D-216 sobre o nome da
pasta. Dentro de `Emitidas/`, `Tomadas/` ou `NFS-e/`, cada empresa deve ser identificada por
`CÓDIGO-`, sem espaço e sem nome depois do hífen. O manual oficial de Rotinas Automáticas da
Domínio confirma que a pasta precisa iniciar com o código da empresa seguido de hífen e que o
texto posterior ao hífen é indiferente; logo, deixar esse trecho vazio é compatível e evita
divergência por razão social. Código vazio continua usando `SEM-CODIGO-`, e separadores, segmentos
de caminho e caracteres de controle continuam neutralizados. ZIP, manifesto e fotografia
auditável devem registrar exatamente o mesmo caminho. XML, competência, acumulador, seleção,
permissões e o bloqueio de homologação Q-39 permanecem inalterados.

## D-221 — Central NFS-e explicita entrada/saída e contexto fiscal (01/10/2026)

Origem: crítica explícita do proprietário durante a reauditoria D-211. A lista de notas deve
responder sem abrir detalhes: se é **Saída · serviço prestado** ou **Entrada · serviço tomado**,
qual a contraparte quando disponível, número, emissão, competência, valor, situação da revisão e
acumulador. Tipo desconhecido nunca é adivinhado: aparece como **Tipo a confirmar**, separado nos
resumos e filtrável. O filtro de movimento usa `Todos`, `Saídas / prestados`, `Entradas / tomados`
e `A confirmar`, preserva os demais filtros na URL e não pode ampliar resultados inválidos.

Para novas coletas ADN, o tipo é derivado somente quando o CNPJ da empresa coincide de forma
inequívoca com o grupo `prest`/Prestador ou `toma`/Tomador do XML; documentos antigos ou leiautes
sem papéis verificáveis permanecem desconhecidos. A demonstração recebe os dois tipos e
contrapartes fictícias. O resumo deixa de chamar todas as notas genericamente de “Recebidas” e
passa a mostrar total, saídas, entradas e pendências de classificação. Downloads, seleção,
permissões, XML original, acumulador e Q-39 não mudam nesta decisão.

Referências adotadas: Domínio separa NFS-e de Serviços Prestados e Serviços Tomados; o leiaute
oficial da NFS-e Nacional identifica `prest` e `toma`; Xero separa invoices de vendas e bills de
compras e mantém estado e valor visíveis na lista. UI/UX Pro Max reforçou moeda consistente,
trilha auditável e um único status contextual; Watermelon não retornou composição pertinente na
busca focada nem no retry estreito. As referências foram adaptadas à linguagem fiscal brasileira
e ao design existente, sem copiar marcas ou telas.

Referência interna adicional: a implementação existente em `HubCobalchini` confirmou que a
extração precisa procurar CNPJ/CPF e nome dentro das seções próprias de prestador e tomador, que
`dhProc` representa melhor a emissão efetiva da NFS-e do que a emissão da DPS (`dhEmi`) e que,
para a conferência de serviços tomados, retenções de ISS, PIS, COFINS, CSLL, IRRF e INSS são
informação operacional de primeira linha. O CICA adota esses campos quando vierem explicitamente
no XML, sem calcular tributo ausente e sem copiar o fallback daquele projeto que infere o tipo
mesmo quando o CNPJ da empresa não coincide com nenhuma das partes.

## D-222 — Acumulador NFS-e usa `infNFSe/valores/acum`, não `ACU` (01/10/2026)

Origem: correção explícita do proprietário, substituindo integralmente D-206 e a parte de V-220
que tratava `ACU` como contrato. No XML derivado do pacote de conferência, o código do acumulador
deve ser lido ou escrito na tag local minúscula `acum`, como filha de `valores` dentro de
`infNFSe`, preservando o namespace do documento. A integração não procura `ACU` em qualquer
profundidade, não a cria em `prod` nem na raiz e não mantém uma tag `ACU` legada no XML derivado.
Ausência de `valores` pode ser suprida dentro de `infNFSe`; ausência de `infNFSe` torna o XML
incompatível com este adaptador e bloqueia o pacote, em vez de inventar uma posição. O XML fiscal
original persistido continua imutável e Q-39 continua impedindo chamar o pacote de importação
homologada no Domínio.

## D-223 — Acumuladores pesquisáveis e pacotes NFS-e recuperáveis (01/10/2026)

Origem: reauditoria funcional e de usabilidade solicitada pelo proprietário. A aba Acumuladores
deve permitir ao contador localizar empresa, código, descrição e origem sem carregar o catálogo
inteiro na memória. O cadastro manual continua sendo apenas disponibilização do acumulador para
classificações futuras, conforme D-113; não cria regra automática. A demonstração não exibirá
um formulário cujo envio é recusado, e explicará que o catálogo ali é somente para consulta.

A aba Exportações deve responder, no próprio histórico, quantas notas e empresas compõem cada
pacote, qual período ele cobre, quem o gerou, se e quando foi baixado e qual é seu código de
conferência. Busca e filtro de situação devem operar no banco e a paginação deve continuar
preservando pacotes antigos. Rebaixar um pacote continua autorizado dentro do escopo atual; arquivo
ausente orienta a gerar outro. `Importação confirmada` permanece bloqueada por D-112/Q-39.

Padrões adotados: trilha filtrável por data, usuário e evento do Xero e QuickBooks; artefato
rebaixável com retenção/indisponibilidade explícita do GitHub Actions; tabela responsiva que vira
cartão no mobile e mensagens de erro com próximo passo conforme a pesquisa UI/UX local. Watermelon
não retornou composição pertinente na busca focada nem no retry estreito, por isso as referências
oficiais acima complementam o design system existente.

## D-224 — Relatórios de retenções NFS-e seguem o recorte visível (01/10/2026)

Origem: pedido explícito do proprietário para expor os impostos retidos e reproduzir no CICA as
funções úteis de relatório PDF e XLSX do HubCobalchini. A Central NFS-e deve oferecer os dois
formatos diretamente na área de notas e aplicar exatamente a empresa, pesquisa, movimento e
período escolhidos pelo contador. O relatório inclui empresa, número, entrada/saída, emissão,
competência, contraparte, serviço, valor da nota, ISS, PIS, COFINS, CSLL, IRRF, INSS e total
retido. PDF prioriza resumo e conferência; XLSX inclui resumo e detalhe filtrável, com datas e
valores tipados. Fórmulas vindas de texto fiscal são neutralizadas na planilha.

Somente valores de retenção explicitamente normalizados do XML podem entrar nos totais. Não se
repete o comportamento legado do HubCobalchini que tratava `vRetCSLL` como todo o CRF: PIS,
COFINS e CSLL permanecem separados, e o total é a soma dos seis campos disponíveis. Direção não
identificada aparece como `A confirmar`; cancelamento ou ausência de dado não autoriza cálculo
fiscal implícito. A consulta é limitada à organização, à carteira autorizada e a 5.000 notas por
arquivo; acima disso, o usuário deve refinar empresa ou período. Geração é local, síncrona,
auditada, sem persistir outro arquivo e sem chamar provedor. A demonstração usa somente dados
fictícios e marca o relatório como demonstração.

Referências adotadas: a documentação de produção da NFS-e Nacional para os campos e esquemas
vigentes; a NT SE/CGNFS-e 007 para distinguir valores devidos de valores retidos e não decompor
indevidamente a retenção agregada; o Guia do Emissor Público para ISS, IRRF, CSLL e contribuição
previdenciária; e o HubCobalchini apenas como referência funcional de seleção, resumo, detalhe e
proteção contra fórmulas. Watermelon não encontrou bloco ou dashboard pertinente após busca
focada e tentativa contábil refinada. A interface segue o design system do CICA, com escopo
visível antes das ações e rótulos explícitos `Baixar PDF` e `Baixar Excel`.

## D-225 — Empresa pausada preserva histórico NFS-e em modo de consulta (02/10/2026)

Origem: reauditoria D-211 e pendência explícita da etapa 11. Pausar uma empresa deve removê-la da
carteira operacional comum e impedir nova coleta ou classificação, mas não apagar nem esconder o
histórico fiscal de proprietários/administradores sem carteira restrita. Ao abrir a NFS-e pelo
cadastro da empresa, a página deve declarar no topo que o recorte é histórico e somente leitura,
explicar o que continua disponível e apontar para o cadastro onde um perfil autorizado pode
reativar a empresa. Downloads de XML/ZIP e relatórios do acervo continuam disponíveis dentro das
permissões atuais; ações que alterariam a classificação ou iniciariam coleta permanecem ausentes.
Perfis com carteira explícita não ganham acesso a empresa pausada por esta exceção histórica.

A interface não deve chamar pendências de “Classificar” quando a classificação estiver bloqueada;
nesse contexto, o indicador abre somente a consulta. GitHub, Slack e Jira orientaram o padrão de
conteúdo arquivado legível, pesquisável e sem novas alterações; a documentação do QuickBooks
confirmou que registros inativos continuam aparecendo em relatórios. UI/UX Pro Max reforçou estado
textual além de cor, semântica e texto curto. Watermelon não encontrou dashboard ou bloco pertinente
após busca focada e retry, portanto esses padrões públicos foram adaptados ao design existente.

## D-226 — Erros web recuperáveis sem revelar existência de recursos (02/10/2026)

Origem: reauditoria de estados de erro do goal ativo. O CICA deve responder 400, 403, 404 e 500
com páginas próprias, status HTTP correto e próximo passo explícito. A resposta 404 continua sendo
usada também quando um registro existe fora da organização ou carteira do usuário: o texto não pode
confirmar existência, dono, permissão faltante nem causa interna. A página deve explicar apenas que
o endereço, conteúdo ou acesso pode ter mudado e oferecer retorno seguro ao CICA. O erro 500 não
mostra exceção, stack trace, configuração, identificador de banco ou dado do pedido; oferece nova
tentativa por GET e retorno ao início. Respostas de caminhos `/api/` continuam JSON, sem HTML.

Todas as respostas recebem `Cache-Control: private, no-store` e `X-Content-Type-Options: nosniff`.
O handler 500 não depende de consulta ao banco para escolher destino. UI/UX Pro Max orientou erro
com recuperação e foco visível; Watermelon ofereceu sua família de blocos de erro após o retry.
Foram adaptados o padrão de não enumeração do GitHub (404 no lugar de confirmar recurso privado),
a orientação do MDN de manter o status 404 real e não confundir o usuário, a mensagem curta de
falha temporária do Slack e a ação direta usada pela Atlassian quando o endereço está incorreto.

## D-227 — Conciliação expõe falha e não promete processamento inexistente (02/10/2026)

Origem: continuação da reauditoria D-211/D-218 na jornada não-demo. Uma importação parada em
mapeamento, conta financeira, OCR ou falha deve aparecer antes das métricas de volume como próxima
ação operacional. Cada linha de processamento apresenta orientação segura derivada do estado e da
etapa, nunca a exceção técnica bruta. O destino deve ser específico quando existe: mapear colunas,
configurar a conta da empresa, abrir os movimentos do arquivo ou reprocessar.

Salvar uma nova versão de layout só pode afirmar “processamento iniciado” quando existe execução
elegível efetivamente recolocada na fila. Se o arquivo já não possui execução pendente, o sistema
informa que o layout foi salvo para arquivos futuros e que nada foi iniciado. A mudança não altera
o arquivo original, decisões contábeis, permissões, idempotência, fila, exportação nem o bloqueio de
homologação Q-39.

## D-228 — Revisão e entrega contábil têm próximo passo e confirmação explícitos (02/10/2026)

Origem: continuação da reauditoria não-demo da Conciliação. O detalhe do movimento deve apresentar
uma única próxima ação derivada do estado: completar dados, gerar rascunho, aprovar, aguardar
exportação, restaurar item ignorado ou reconhecer item já exportado. Ações secundárias, como criar
regra e ignorar, permanecem disponíveis, mas não competem visualmente com o passo principal.

Uma exportação contábil pronta pode continuar sendo baixada depois da confirmação. Cada download é
auditado. A confirmação de importação é um POST separado, exige permissão, layout Domínio
homologado, confirmação humana do hash exibido e revalidação do arquivo armazenado contra o hash
persistido. Ela registra ator e instante e nunca ocorre automaticamente pelo download. Arquivo
ausente ou divergente não avança o estado. Q-39 continua bloqueando geração e confirmação reais;
testes com a configuração explicitamente habilitada provam apenas o contrato local.

UI/UX Pro Max orientou estado e feedback de carregamento; o catálogo Watermelon não encontrou bloco
em uma busca focada nem na tentativa mais estreita. Foram adotados os padrões observados em
QuickBooks (revisão antes de contabilizar), Xero (revisão individual e lote separados) e Ramp
(estado de sincronização distinto da conclusão financeira, com recuperação explícita).

UI/UX Pro Max orientou resumo de erro focável, estado estável e próximo passo; Watermelon não
encontrou bloco pertinente após busca focada e retry. Xero e QuickBooks fundamentaram as etapas
explícitas de mapeamento, revisão de resultado e correção; BlackLine, o tratamento por exceção; e
SaaSFrame, o uso de progresso e resumo final em importações. Os padrões foram adaptados ao fluxo e
ao design system já existentes.

## D-229 — Configuração da Conciliação distingue requisito, recomendação e controle opcional (03/10/2026)

Origem: reauditoria de facilidade de uso da Conciliação prevista em D-211. A configuração por empresa
não pode afirmar “pronto” quando faltam contas, nem apresentar período aberto e automação como se
fossem pré-requisitos universais. Conta contábil ativa que aceite lançamentos é requisito para gerar e
validar partidas; conta financeira é recomendada e passa a ser exigida na importação de extrato
bancário somente quando a empresa já possui esse cadastro; período serve para bloquear intervalos e a
ausência dele não bloqueia; centro de custo e regras/layouts são controles opcionais conforme a
operação. A tela deve nomear essas diferenças, indicar uma única próxima ação e recolher formulários
de criação até pedido explícito, mantendo erro aberto e focado. Listas devem paginar sem corte
silencioso e ações devem retornar à seção afetada. Nenhum cadastro é criado, ativado ou inferido
automaticamente, e permissões, auditoria, Q-39 e as validações contábeis existentes permanecem.

## D-230 — Auditoria da Conciliação prioriza investigação humana, sem expor payload bruto (03/10/2026)

Origem: reauditoria de facilidade de uso da trilha prevista em D-211. A listagem deve responder, na
primeira leitura, o que aconteceu, quando, por quem, sobre qual tipo de registro e se a operação teve
êxito. Códigos de ação, UUIDs e demais referências internas ficam recolhidos em “Detalhes técnicos”;
metadados só aparecem quando a chave está em uma lista segura e com rótulo de negócio. A interface
não renderiza JSON bruto, hash de IP, request id, arquivo, documento financeiro ou segredo.

A busca pode combinar atividade, pessoa/referência, resultado e intervalo de datas. Parâmetro
inválido ou intervalo invertido deve produzir orientação visível e nenhum resultado, nunca ampliar
silenciosamente a consulta. Filtros e página permanecem na URL, a paginação usa 50 eventos e a tela
explica tanto a ausência total de histórico quanto uma busca sem correspondência. O escopo continua
restrito ao escritório atual e aos perfis Owner, Admin e Manager; esta revisão não amplia permissões,
retenção, exportação, mutação nem acesso aos objetos apontados pela trilha.

## D-231 — Importação manual usa escolha, análise e confirmação separadas (03/10/2026)

Origem: reauditoria da entrada operacional e da prévia da folha previstas em D-138 e D-141. O
operador deve primeiro escolher o conteúdo, depois enviar um arquivo e só então revisar uma prévia
antes de qualquer gravação. A orientação de formato aparece junto ao tipo escolhido; para folha, o
modelo, código/CNPJ, competência `AAAA-MM-01`, referência e regra de campos ausentes ficam explícitos.

O arquivo inteiro da folha é pré-validado sem criar fotografias ou atividades. A prévia sinaliza por
linha empresa não localizada, competência, referência e totais/pessoas inválidos e não oferece a ação
de confirmação enquanto houver pendências. A confirmação continua revalidando tudo dentro da
transação e mantém rollback integral. Arquivo idêntico já processado retorna ao histórico, em vez de
abrir uma prévia vazia. Nenhum valor ausente é inferido e nenhuma permissão foi ampliada.

UI/UX Pro Max orientou resumo de erros focável, ajuda contextual e reflow; Watermelon não encontrou
resultado para upload/importação após a busca focada e o retry. Foram adaptados os padrões de
HubSpot (preparação, prévia e erro por linha), Salesforce (escolher, enviar/mapear, revisar),
QuickBooks (instruções e formatos antes do envio) e Google Workspace (modelo e diagnóstico
acionável), preservando o design system e a linguagem contábil do CICA.
## D-232 — Conferência de folha começa pela competência e mostra todos os totais (03/10/2026)

Origem: continuidade da reauditoria de telas solicitada pelo proprietário. A ficha da empresa não
deve carregar um seletor irrestrito com todo o histórico nem pedir que o contador descubra por erro
quais registros pertencem ao mesmo mês. A lista de folha passa a mostrar pessoas, bruto, descontos,
encargos do empregador e líquido, preservando ausências explícitas. Quando uma competência tiver ao
menos duas fontes, a ação local abre somente aquele mês; com exatamente duas fontes, ambas ficam
pré-selecionadas sem executar ou concluir a conferência automaticamente. O resultado identifica a
diferença como valor a mais ou a menos da fonte conferida em relação à fonte de referência. A
tolerância monetária continua opcional e não se aplica ao quadro de pessoas.

A comparação permanece agregada, somente leitura e sem dados de trabalhador, cálculo de folha,
aceite oficial ou mudança de estado da atividade. Pesquisa prévia consultou UI/UX Pro Max; Watermelon
não encontrou composição após busca e refinamento. QuickBooks, Rippling, Gusto e ADP foram
inspecionados como referências de relatórios de folha e reforçaram período explícito, origem,
resumo de bruto/descontos/encargos/líquido e exceção antes do detalhe; o desenho final permanece
adaptado ao fluxo contábil e ao design system da CICA.

## D-233 — Caixa DTE prioriza leitura e separa resumo de ciência (03/10/2026)

Origem: reauditoria da jornada DTE solicitada pelo proprietário. A Caixa Postal continua começando
pelas mensagens já recebidas, com empresa, assunto, origem, data e situação. Cada mensagem terá uma
única ação textual “Abrir resumo”; o assunto deixa de repetir o mesmo link, reduzindo paradas de foco
e tornando a próxima ação inequívoca. Filtros, navegação do serviço, métricas acionáveis e botões da
jornada terão alvo mínimo de 44 px, e metadados/ações deixam de usar texto de 11 px como conteúdo
operacional principal.

Abrir o resumo continua sendo somente leitura e não registra ciência. O teor permanece separado e
exige confirmação explícita do risco jurídico e, quando aplicável, do consumo/excedente. Estados de
retorno incerto não oferecem repetição automática. A demonstração permanece isolada na sessão, sem
Serpro, cobrança ou ciência oficial. No celular, o histórico de consultas usa cartões rotulados em
vez de exigir rolagem horizontal de uma tabela larga.

Pesquisa prévia: UI/UX Pro Max reforçou feedback contextual e anúncio significativo de contagens;
o catálogo Watermelon não encontrou dashboard nem bloco para caixa de entrada após busca e retry.
Foram adaptados padrões da Caixa Postal da Receita Federal, Caixa de Mensagens do DET, Microsoft 365
Message Center e Outlook: mensagens recentes primeiro, situação lida/não lida, filtros explícitos,
origem/data e detalhe separado. Nenhuma interface, marca ou texto foi copiado.

## D-234 — Radar é uma fila de triagem, não uma tabela técnica (03/10/2026)

Origem: reauditoria da jornada do Radar dentro da meta de tornar todas as telas descobríveis e úteis
ao escritório contábil. A página principal apresenta publicações oficiais como uma fila de leitura
em ordem recente, com título, resumo, fonte, data, estado da coleta e ações visíveis sem rolagem
horizontal. “Abrir fonte oficial” apenas consulta a origem; “Analisar impacto” abre a decisão humana
por empresa. Nenhuma publicação cria atividade, aplicabilidade, prazo ou obrigação por si só.

A tela de análise prioriza primeiro a publicação e depois a ação: empresa autorizada, motivo concreto
e botão que explica que criará ou retomará uma atividade. Carteiras longas recebem filtro local
progressivo sem substituir o `select` nativo nem tornar JavaScript obrigatório. Análises existentes
aparecem depois do formulário e levam à atividade já criada. Filtros e retorno à fila preservam a
URL, estados vazios orientam recuperação e controles mantêm alvo mínimo de 44 px. A demonstração
continua sem criar análise e links fictícios não são tratados como prova da publicação.

## D-235 — Retenções NFS-e ficam legíveis e os formatos de relatório são explícitos (03/10/2026)

Origem: revalidação final do pedido D-224 contra o HubCobalchini e uso renderizado em celular. A
lista continua mostrando somente tributos retidos explicitamente presentes no XML e mantém ISS,
PIS, COFINS, CSLL, IRRF e INSS separados. O controle que abre o detalhamento passa a ter alvo mínimo
de 44 px e texto operacional legível; a ação de planilha identifica também a extensão `.xlsx`, sem
alterar filtros, cálculos, permissões ou o limite de 5.000 notas. PDF prioriza conferência e XLSX
preserva dados tipados, resumo e detalhe filtrável. A homologação dos valores com amostra fiscal real
e o retorno Domínio de Q-39 continuam externos e não podem ser concluídos por dados fictícios.

## D-236 — Guias e DCTFWeb priorizam a próxima ação sem expor falha técnica (03/10/2026)

Origem: continuação da reauditoria integral de telas do objetivo ativo. A carteira deve apresentar
primeiro as guias oficiais quando elas existirem e manter a apuração do Domínio como fila de
descoberta separada. Cada guia terá uma ação principal coerente com o estado: emitir ou repetir uma
falha confirmada, acompanhar processamento, baixar o DARF já obtido ou aguardar conciliação quando o
resultado for incerto. “Ver resultado” não será usado antes de existir resultado; detalhes e
documentos permanecem ações secundárias.

Chaves de serviço, exceções do conector/fornecedor e mensagens brutas persistidas deixam de aparecer
como conteúdo operacional. A interface usa orientação segura derivada do estado e do código de erro;
referências necessárias ao suporte ficam recolhidas como detalhe técnico, sem renderizar payload. Na
consulta DCTFWeb, os dois documentos são apresentados por nome e progresso, não pela chave interna.
Resultado incerto continua sem repetição: D-149 e Q-40 permanecem bloqueados até existir regra de
conciliação e custo adicional aprovada pelo proprietário. A revisão não muda preço, consumo,
permissões, integração Serpro, valores fiscais ou homologação externa.

UI/UX Pro Max reforçou feedback após envio e atualização contextual sem deslocar foco. Watermelon não
encontrou dashboard tributário nem bloco de histórico de pagamentos após busca focada e refinamento.
Foram adaptados os padrões da Receita Federal/DCTFWeb (período, situação, saldo e ação de emitir), do
QuickBooks Tax Center (obrigação atual e pagamentos recentes) e do Stripe (estado operacional e
recuperação de falha), preservando a identidade e as regras fiscais do CICA.
## D-267 — Parcelamentos orientados por empresa, acordo, parcela e DAS (03/10/2026)

- Ao abrir uma empresa, seu contexto e próximo passo aparecem antes da carteira; a carteira fica
  abaixo como troca de contexto, busca e seleção em lote.
- A hierarquia usa a terminologia oficial da Receita: consultar pedidos, conferir situação e
  consolidação, consultar parcelas disponíveis e emitir/baixar o DAS. Situação, valor consolidado,
  parcela básica, quantidade, pagamentos e parcelas em atraso/mês atual ficam no contexto.
- Ações que podem consumir tokens exigem uma revisão de escopo e custo antes do POST. Na demo a
  revisão declara ausência de consumo e o DAS fictício baixável é inequivocamente sem validade.
- Cada estado apresenta uma orientação segura e uma ação principal. Resultado incerto bloqueia
  repetição; liberar nova tentativa exige confirmação explícita de conferência no e-CAC.
- Mensagem bruta do provedor não aparece na leitura principal. Registro CICA, protocolo e código de
  falha ficam recolhidos em detalhes para suporte, sem apagar a evidência persistida.
- A decisão adapta Receita Federal/Portal do Simples (consulta → detalhe → emissão), Stripe
  (estado define ações permitidas), QuickBooks Tax Center (obrigação atual antes do histórico) e
  Xero Tax Manager (cliente, referência, prazo e situação). UI/UX Pro Max reforçou feedback de
  envio e atualização contextual. Watermelon não encontrou analogia em duas buscas focadas.
- Nada aqui define regra fiscal, tarifa, pagamento, quitação, reemissão ou homologação PARCSN;
  contrato, credenciais, representação e retorno real continuam dependências externas.
## D-268 — Ficha de atividade orientada ao próximo passo (03/10/2026)

- A leitura principal segue: contexto da empresa e prazo → próximo passo → condições para concluir → responsável → evidências e histórico.
- Estados técnicos permanecem disponíveis, mas são traduzidos como condições de conclusão; código interno e referências ficam recolhidos para suporte.
- Registrar evidência, registrar impedimento e concluir são intenções separadas. Só uma ação principal fica aberta por vez; conclusão exige revisão explícita e não é apresentada quando há requisito pendente conhecido.
- Formulários inválidos preservam dados, exibem erros junto aos campos e retornam foco à seção afetada.
- Evidência e histórico permanecem imutáveis; esta decisão não cria reabertura manual, dispensa, exclusão nem nova regra de conclusão.
- Quando a atividade está impedida e as evidências já atendem às condições, a revisão explicita que concluir também resolve o impedimento atual; isso torna visível a regra preexistente que limpa o motivo e preserva o evento na trilha.
- A interface preserva carteira, papéis e permissões vigentes. Perfis somente leitura recebem o mesmo contexto sem controles de escrita.
- Pesquisa: Asana orientou campos essenciais e conclusão no detalhe; Linear orientou propriedades e responsabilidade; ClickUp orientou atividade cronológica junto da tarefa. UI/UX Pro Max reforçou feedback de sucesso e confirmação; Watermelon não retornou composição pertinente após duas buscas.

## D-269 — Central de atividades como fila de decisão (03/10/2026)

- O recorte padrão mostra trabalho em aberto; atividades concluídas e dispensadas continuam acessíveis por filtro explícito, sem disputar atenção com o trabalho atual.
- Prioridades recorrentes ficam visíveis antes dos filtros detalhados: em aberto, atraso, hoje, próximos sete dias, impedidas e fonte indisponível. Trocar prioridade preserva área, empresa, competência e responsável quando aplicável.
- Área, situação, atualização, empresa, competência e responsabilidade formam um único formulário avançado. Filtros ativos aparecem como elementos removíveis, a URL continua compartilhável e existe uma ação inequívoca para limpar o recorte.
- Valor de filtro inválido ou combinação incompatível nunca amplia silenciosamente a consulta: a tela mostra o erro e nenhum registro até a correção ou limpeza.
- Cada item expõe atividade/empresa, próximo passo, prazo relativo e exato, responsável, situação e uma única ação “Conferir”. No celular, a mesma informação vira cartão rotulado; nenhuma coluna essencial é simplesmente escondida.
- A decisão não cria busca irrestrita, edição em lote, mudança automática de responsável ou nova regra de estado. Carteira e permissões permanecem as vigentes.
- Referências: Linear orientou filtros refletidos na URL e foco no recorte; ClickUp orientou situação, prazo e responsável; Asana orientou lista ordenável por prazo/responsável; Microsoft Planner orientou separar filtro temporário de mudança nos dados e usar grade para escaneamento. UI/UX Pro Max confirmou reflow dos filtros; não encontrou regra de stack após retry. Watermelon não retornou dashboard nem bloco pertinente após duas buscas.
## D-270 — Modelos de atividades como biblioteca e fluxo progressivo (03/10/2026)

- A tela administrativa deve começar pelo estado operacional: quantidade de modelos ativos, atribuições ativas, empresas cobertas e atribuições aptas à geração.
- Definir modelo, aplicar a uma empresa e gerar uma competência são etapas distintas e progressivas; os três formulários não devem disputar atenção ao mesmo tempo.
- A biblioteca de modelos e a revisão de atribuições devem ser paginadas e mostrar cobertura agregada, sem renderizar toda a carteira em uma única resposta.
- Repetir a atribuição do mesmo modelo à mesma empresa deve retornar erro recuperável no próprio formulário, nunca erro interno nem ampliação silenciosa.
- Pausar um modelo interrompe novas atribuições e novas gerações daquela versão, preservando atividades e histórico já criados. Pausar uma atribuição afeta somente a empresa correspondente.
- A geração manual deve declarar previamente quantas atribuições ativas serão consideradas, preservar idempotência e nunca inventar prazo ausente.

## D-271 — Fechamentos por competência como fila de conferência (03/10/2026)

- O painel deve responder primeiro quantos fechamentos da página exigem atenção, quantos estão
  comprovados e quantas combinações de empresa/área ainda não têm requisitos; os totais não podem
  aparentar representar empresas fora da página paginada.
- Estados com ação vêm antes dos concluídos. Cada combinação configurada mostra empresa, área,
  progresso, situação, próximo passo e uma ação direta; atividades, evidências e requisitos ficam
  disponíveis em detalhe sem dominar a leitura inicial.
- Fechamentos comprovados formam um grupo secundário recolhível. Ausência de requisitos é tratada
  como lacuna de cobertura, nunca como conclusão ou dispensa; administradores recebem atalho para
  modelos e demais perfis recebem orientação para acionar o administrador.
- Competência inválida não substitui silenciosamente o recorte pelo mês atual: nenhum fechamento é
  apresentado até o usuário corrigir ou limpar o filtro. Carteira, paginação, requisitos e regras de
  comprovação existentes permanecem inalterados.
- Foram adaptados os padrões de visibilidade de progresso e exceções do
  [FloQast Close](https://get.floqast.com/hubfs/Assets/FloQast_Guide_Buyers%20Guide%20to%20Selecting%20a%20Financial%20Close%20Management%20Solution_January%202023.pdf),
  de situação, responsável e próxima tarefa do
  [Financial Cents](https://help.financial-cents.com/en/articles/5390143-tracking-work-deadlines-in-your-workflow-dashboard),
  e de revisão por etapas e pendências do
  [QuickBooks Books Review](https://quickbooks.intuit.com/learn-support/en-us/help-article/manage-client/month-end-reviews-finish-clients-open-tasks/L4GubaqKy_US_en_US).
  UI/UX Pro Max reforçou feedback contextual e cartões responsivos; Watermelon não retornou
  composição pertinente após busca ampla e refinada.

## D-272 — Cadastro de empresas como carteira de ação (03/10/2026)

- A lista de empresas deve responder antes da busca quais cadastros ativos exigem atenção por
  revisão NFS-e, certificado A1 ou ausência de código no Domínio. As contagens respeitam a carteira
  autorizada e cada prioridade é um filtro explícito; empresas pausadas permanecem consultáveis,
  mas não entram como pendência operacional.
- Busca e prioridades ficam sempre visíveis. Situação, vínculo, certificado e revisão aberta são
  refinamentos progressivos, para não fazer cinco controles disputarem atenção na entrada da tela.
- Cada empresa expõe identidade, contexto de integração e um único próximo passo. Revisão NFS-e
  leva diretamente à fila da empresa; certificado leva à central de A1; ausência de código leva à
  ficha para conferência. Cadastro pronto ou pausado não recebe alerta falso.
- Filtro inválido nunca amplia silenciosamente a carteira: o resultado fica vazio, o erro é
  anunciado e focado e a pessoa pode limpar o recorte. O filtro de vínculo passa a aceitar também
  empresas sem código, necessidade que antes não podia ser isolada.
- Foram adaptados os padrões de visão de cliente e tarefas abertas do
  [QuickBooks Accountant](https://quickbooks.intuit.com/learn-support/en-ie/help-article/manage-client/learn-clients-overview-bookkeeping-tabs-quickbooks/L5p3u06h5_IE_en_IE),
  de filtros e recortes da
  [TaxDome](https://sv.help.taxdome.com/article/123-accounts-list-overview-filters-export),
  de contexto e acompanhamento do
  [Karbon](https://karbonhq.com/en-GB/solution/client-management/) e de grupos operacionais do
  [Financial Cents](https://help.financial-cents.com/en/articles/5386247-organize-your-clients-into-groups).
  UI/UX Pro Max orientou reflow e feedback. Watermelon não retornou composição pertinente após
  busca ampla e refinada.

## D-273 — Ficha da empresa como espaço de trabalho do cliente (05/10/2026)

- A ficha deve responder primeiro quem é a empresa, qual é a próxima ação e quais áreas possuem
  conteúdo ou atenção. Identificação, trabalho, fiscal, folha, financeiro, documentos e DTE ficam
  acessíveis por navegação local com contagens; o conteúdo detalhado permanece disponível em
  seções progressivas, sem exigir uma rolagem integral para descobrir o que existe.
- Trabalho impedido ou vencido precede revisão NFS-e, certificado ausente/vencendo e demais
  atividades abertas na escolha da próxima ação. Empresa pausada permanece somente histórica e
  não recebe chamada operacional enganosa.
- O cadastro só pode ser alterado nesta ficha quando for local, a sessão puder administrar toda a
  carteira e o escritório não estiver sob Domínio, fonte importada ou controle central. Dados com
  origem externa são somente leitura e indicam que a correção deve ocorrer na fonte; a interface
  não oferece pausa manual que a próxima sincronização reverteria.
- Edição inválida preserva os dados, retorna HTTP 400, reabre o diálogo e move o foco ao resumo de
  erros. Toda alteração válida mantém a empresa e seu histórico, registra auditoria e não muda
  atividade, certificado, documento ou autorização.
- Foram adaptados o resumo por cliente, abas com contagens e limite de itens ativos do
  [TaxDome](https://help.taxdome.com/article/client-account-overview-page), o registro único com
  próximos trabalhos, documentos e histórico do
  [Financial Cents](https://help.financial-cents.com/en/articles/4213253-client-profile), a visão
  conjunta de trabalho, comunicação e prazos do
  [Karbon](https://karbonhq.com/en-GB/solution/client-management/) e a priorização de tarefas do
  [QuickBooks Accountant](https://quickbooks.intuit.com/learn-support/en-ca/help-article/manage-client/learn-clients-overview-bookkeeping-tabs-quickbooks/L5p3u06h5_CA_en_CA).
  UI/UX Pro Max orientou estado ativo, hierarquia de títulos e navegação por seção; não encontrou
  correspondência específica para “próxima ação” após retry. Watermelon não retornou composição
  pertinente após busca ampla e refinada.

## D-275 — Auditoria integral e plano de conclusão do produto (05/10/2026)

Origem: pedido do proprietário para analisar todo o CICA, suas funcionalidades, sentido das telas,
usabilidade e gaps, pesquisar sistemas similares online e criar um plano. Esta entrega autoriza
pesquisa pública, inspeção do repositório, navegação local com dados fictícios e atualização da
documentação. O resultado complementa o plano mestre e as etapas 00–13; não cria plano concorrente.
As recomendações novas serão identificadas como propostas, com prioridade, dependência e aceite.
Não há nesta solicitação implementação das propostas, publicação, envio de mensagens, consumo de
APIs comerciais ou nova autorização sobre dados reais. Evidência histórica, inspeção atual,
hipótese de usabilidade e homologação serão diferenciadas. Preservar alterações locais existentes.

## D-274 — Reclassificação NFS-e pelo backup e contrato `infNFSe/valores/acum` (05/10/2026)

- Os arquivos Krek fornecidos são conjuntos do importador Domínio, não notas fiscais. Eles
  confirmam o contrato de saída para NFS-e tomadas: uma única tag minúscula `<acum>` como filha
  direta de `infNFSe/valores`; `<ACU>` pertence ao leiaute de NF-e e é legado inválido em NFS-e.
- O XML fiscal original permanece imutável. A tag é escrita e validada somente na cópia derivada
  do pacote de exportação, removendo qualquer `<ACU>` legado; isso preserva hash/evidência e evita
  representar que o documento oficial recebido já continha uma extensão privada do Domínio.
- Uma rotina administrativa idempotente reaplica regras e observações do backup a todas as NFS-e
  do escritório escolhido. Ela exige fotografia concluída com catálogo e observações, aceitando
  tanto um lote único quanto o par catálogo/lote-filho de observações da mesma fotografia, oferece
  prévia por padrão e só grava com `--apply`.
- Classificação automática confiante cria nova evidência append-only apenas quando o acumulador
  efetivo mudou ou ainda não existia. Revisão aberta sem correspondência segura recebe sugestão e
  confiança atualizadas; quando a evidência é segura, ela é encerrada com origem explícita
  `backup`, nunca como decisão humana. Decisões humanas existentes nunca são substituídas.
- Cada nova evidência aponta para a anterior, registra a fotografia de backup usada e pode ser
  revertida logicamente pelo encadeamento, sem apagar história. A execução registra totais e evento
  de auditoria, sem incluir conteúdo fiscal no log.

## D-276 — Correção emergencial da tela e downloads NFS-e (05/10/2026)

Pedido explícito: revisar criticamente a tela publicada, corrigir e fazer deploy rápido, verificando produção. Escopo: NFS-e, seus filtros, botões, seleção e downloads; preservar modificações locais alheias.
- Atualização dos filtros deve sincronizar lista, indicadores, relatório e campos enviados ao servidor. Filtro vazio deve oferecer recuperação, não instrução falsa de configurar coleta.
- Disponibilizar download dos XMLs originais do filtro para os mesmos perfis já autorizados a baixar NFS-e, inclusive antes da classificação. Não inserir acumulador, não modificar classificação e não representar esse arquivo como pacote Domínio. Pacote classificado existente conserva suas regras.
- Separar claramente XML original, ZIP classificado e relatórios; priorizar notas e controles operacionais, com relatórios em seção recolhível. Preservar identidade, teclado, foco e mobile.
- Publicar patch isolado sobre a imagem atual, sem migração, sem novo recurso ou mudança de capacidade. Build local e substituição nas máquinas existentes: incremento estimado inferior a US$ 0,10, sem aumento mensal; rollback pela imagem anterior.
- UI/UX Pro Max consultado (SaaS, estados desabilitados; stack HTML sem correspondência após retry). Watermelon sem resultado em `bulk selection` e `table`. Refero/SaaSFrame consultados; TaxDome (https://help.taxdome.com/article/233-how-to-edit-download-print-filter-documents) orienta separar download original de ações de classificação, e Helios (https://helios.hashicorp.design/patterns/table-multi-select) orienta escopo explícito da seleção. Correção localizada, sem redesenho genérico.
- Evidência adicional da captura: sessão de suporte vigente é `read_only`. Download original/relatórios são leitura do mesmo acervo já autorizado, não alteração fiscal. Desacoplar essas leituras de `support_can_mutate`, preservando o escopo de empresas e a recusa de classificação/exportação derivada nessa sessão. Suporte `full` deve respeitar a autorização já existente, sem exigir vínculo de colaborador ausente por definição.
- A primeira coluna sem checkbox estava recebendo largura de 48 px, comprimindo identificação e selos. Usar classe semântica exclusiva na célula de seleção; abrir a conferência na ficha existente em vez de expandir centenas de pixels dentro da tabela.
- Solicitação subsequente: após publicação da correção de tela, auditar classificação, acumuladores por empresa e erros de importação apresentados no Domínio. Inspecionar os dados existentes primeiro, sem presumir regras fiscais novas ou sobrescrever decisões humanas.

## D-277 — Rotina diária do contador: prazos, lote, busca, avisos e linguagem (06/10/2026)

Origem: pedido do proprietário para revisar o produto publicado com olhos do contador, pesquisar
UX e executar o plano aprovado em 06/10/2026. Revisão feita na demonstração publicada
(`/demo/`, ~18 telas em 1280 e 375 px) e no código; complementa D-275/V-275 sem plano concorrente.
Ordem aprovada: rotina diária → NFS-e (PC-02) → Triagem (PC-15/16). Portal e envio de guia ao
cliente continuam fora. Validação em produção usa conta de teste aberta pelo próprio proprietário.

1. **Competência × vencimento (PC-13; esclarece D-270).** Trabalho da competência M vence em
   M+k, com k configurável por modelo; modelos existentes mantêm o comportamento atual até nova
   versão explícita. Prazo legal só vem de regra aprovada com base legal, URL e vigência; sem
   regra aprovada ou calendário do ano, o prazo legal fica ausente e isso é registrado. Prazo
   interno nunca fica depois do legal. Mudança de prazo de atividade gerada exige motivo e
   deixa evento. Regras de vencimento são aprovadas por papel da plataforma; o escritório ajusta
   somente a antecedência interna (padrão: 2 dias úteis).
2. **Ação em lote na central de atividades (revoga a exclusão de edição em lote de D-269).**
   Atribuir, mudar prazo interno e concluir quando as condições da atividade forem atendidas;
   até 50 itens; motivo obrigatório; carteira e permissão reconferidas item a item; itens
   pulados voltam com o motivo. Mudar prazo: proprietário, administrador e gestor. Operador pode
   assumir atividade sem responsável dentro da sua carteira. Na demonstração, ações valem só na
   sessão.
3. **Busca e avisos.** Busca global limitada à carteira e aos módulos da pessoa (não é a busca
   irrestrita vetada em D-269). Avisos somente dentro do produto, com deduplicação e link de ação;
   nenhum e-mail/WhatsApp.
4. **Cadastro da empresa.** Regime tributário, IE, IM, contato e responsável por área são
   editáveis localmente mesmo quando a identidade vem do Domínio ou de outra fonte. Responsável
   por área é o padrão quando a atribuição do modelo não tem responsável. Contato é dado pessoal:
   auditoria registra apenas os campos alterados.
5. **Linguagem.** Tela não explica a si mesma: sem parágrafo explicativo sob títulos; rótulo
   curto; identificador técnico (e-mail interno, UUID, hash, papel em inglês) não aparece onde há
   nome humano. Exceções obrigatórias: resumo × ciência da DTE (D-233), confirmação de custo
   (D-149/D-236), aviso de dados fictícios da demonstração e confirmação de ação irreversível.

Referências: Acessórias (prazo e acompanhamento de processos), padrão prazo interno antes do legal
em escritórios contábeis, boas práticas de ação em lote/filtro em tabela (UX DWorld, UX Collective),
heurísticas de Nielsen aplicadas a SaaS B2B. Regras de vencimento iniciais em rascunho, com fontes:
DCTFWeb no último dia útil do mês seguinte desde 01/2025; contribuições previdenciárias no dia 20,
antecipando quando não houver expediente bancário (Lei 8.212/1991, art. 30, §2º); DAS no dia 20,
prorrogando ao dia útil seguinte (confirmar no texto vigente da Resolução CGSN 140/2018 ao aprovar).

## D-280 — Visão geral e download NFS-e mais diretos na operação (07/10/2026)

Registrada em paralelo como D-277 (commit e028851, viniciusamotta) e renumerada na integração
de 09/10/2026, porque D-277 já era a rotina diária. Na mesma integração, a parte NFS-e (barra do
pacote e XML original no cabeçalho) foi substituída pela tela reconstruída de D-277/V-278, que já
estava em produção; a parte da Visão geral segue valendo.

Origem: pedido do proprietário, navegando a demonstração, para tornar telas mais intuitivas. Escopo
autorizado nesta entrega: os três pontos apontados na Visão geral e a reformulação da escolha e do
download de notas na NFS-e. Execução em localhost com aprovação antes de ir para `main`. Pertence à
etapa 11 e ao [PLANO_TELAS.md](PLANO_TELAS.md); não cria plano concorrente nem altera regra fiscal,
contrato externo, cobrança ou autorização de dados.

- A Visão geral tem uma única ação principal: o resumo do dia. Os cartões de prioridade são filtros
  da fila e não repetem o verbo do resumo; passam a declarar apenas o estado de filtragem. Antes,
  "Em atraso" oferecia "Revisar atrasadas" a poucos pixels do botão idêntico do resumo.
- Pendência de prazo e exceção operacional não têm o mesmo peso visual. "Em atraso", "Para hoje" e
  "Próximos 7 dias" ficam sob "Prazo"; "Impedidas" e "Fonte indisponível" sob "Exceções", com número
  menor. "Em atraso" com contagem recebe o maior destaque da linha.
- Contagem zero deixa de ser pintada como pendência. O tom de atenção passa a depender da contagem,
  não de uma marcação fixa no código: um cartão zerado anunciava atenção em âmbar.
- "Como usar" passa ao cabeçalho da página, junto ao título que explica. A linha flutuante à direita
  deixava o acionador sem vínculo com o conteúdo.
- Na NFS-e, os dois downloads aparecem lado a lado como documentos distintos, cada um com escopo e
  botão próprios: XML original (o filtro inteiro, sem acumulador) e pacote com acumuladores (a
  seleção). A separação exigida pela D-276 é mantida; o que muda é a apresentação, antes empilhada
  em dois títulos de mesmo peso com texto corrido.
- Os controles de seleção passam a ficar no cartão que explica o pacote. O título prometia a ação e
  os controles viviam em um bloco separado abaixo dele.
- A ação em lote só existe depois que há seleção, conforme o PLANO_TELAS; antes ocupava a tela como
  botão desabilitado permanente.
- Selecionar a página abre as empresas recolhidas. Marcar notas invisíveis dentro de grupos fechados
  declarava um escopo que o operador não podia conferir.
- O atalho do cabeçalho passa a se chamar "Baixar notas", igual ao bloco que ele abre, e só aparece
  quando há nota no filtro; antes apontava para uma âncora inexistente no resultado vazio.
- Filtro sem resultado continua oferecendo recuperação pelo estado vazio existente, sem cartões de
  download inoperantes.

Limites desta decisão: UI/UX Pro Max, Watermelon e Playwright não estavam disponíveis nesta sessão e
não foram consultados; a revisão apoiou-se no PLANO_TELAS, na D-276 e em inspeção local. Não houve
deploy, consumo externo, custo, migração ou mudança de capacidade. A validação é local e fictícia,
não substitui homologação. A entrega cobre os pontos pedidos, não a auditoria integral da etapa 11.

### D-280.1 — Segunda rodada, sobre a entrega acima (07/10/2026)

Retorno do proprietário na demonstração: "Como usar" precisa ficar destacado, e a NFS-e exige
rolagem longa demais até ver e baixar as notas. Os filtros e a pesquisa foram aprovados como estão.

- "Como usar" adota o tom principal, igual ao da ação do dia. O acionador da orientação deixa de ser
  discreto por decisão explícita do proprietário, mesmo convivendo com a ação principal na mesma tela.
- Cada download passa a ficar onde o seu escopo vive. O XML original depende do filtro e sobe para o
  cabeçalho do painel, com o escopo declarado ao lado. O pacote depende da seleção e vira uma barra
  fina imediatamente acima das notas, fixa na rolagem para acompanhar carteiras longas. A separação
  entre os dois arquivos exigida pela D-276 permanece explícita em rótulo, escopo e botão; o que se
  desfaz é o bloco de cartões que os reunia entre o filtro e a lista.
- Os relatórios de retenções passam para depois da lista, ainda recolhidos. A D-276 manda priorizar
  notas e controles operacionais; ocupar altura antes das notas contrariava essa ordem.
- O cabeçalho do painel perde o selo "CONFERÊNCIA FISCAL", que repetia o título da página e a aba
  ativa, e a descrição encurta para uma linha.
- Os indicadores do recorte passam a uma linha compacta, continuando filtros clicáveis. A compactação
  é escopada em `#nfse-metrics` e `.nfse-workspace`: `metric-strip` e `workspace-panel-head` são
  compartilhados por outras sete telas e não devem mudar sem pedido.

Medição em 1920×950, com a faixa da demonstração presente: o topo da lista saiu de cerca de 995 px
para 686 px e a primeira nota de cerca de 1.120 px para 811 px, com duas empresas visíveis sem
rolagem. Em produção, sem a faixa da demonstração, a lista sobe outros 78 px. Não houve mudança de
regra fiscal, permissão, contrato ou capacidade.

### D-280.2 — Ancoragem do download no cabeçalho da NFS-e (07/10/2026)

Retorno do proprietário: o botão do XML original ficou "no meio do nada"; o restante foi aprovado.

- O cabeçalho do painel tinha três filhos sob `space-between`, o que jogava a ação para o vão entre
  o título e o contador. O contador de resultados passa a acompanhar o título, que é o que ele
  descreve, e a ação fica sozinha encostada à direita.
- Em telas estreitas a ação ocupa a largura inteira. A regra anterior declarava `justify-items`
  sem base de largura e não produzia efeito sobre um item flexível dimensionado pelo conteúdo.

Sem mudança de escopo, permissão, rótulo ou comportamento dos downloads.

## D-281 — Lucrums incorporado como módulo Rentabilidade por Cliente

Registrada na branch `codex/lucrums`/`codex/siescon-adapter` com outra numeração e renumerada na
integração ao `main` de 09/10/2026, porque os números já existiam lá: D-108…D-121 → D-281…D-294,
V-105…V-116 → V-281…V-292 e Q-39…Q-43 → Q-41…Q-45. Mensagens de commit antigas mantêm os números
originais.

Data: 22/09/2026. Origem: responsável pelo projeto, nesta conversa. O projeto
Lucrums (`github.com/Mewstacks/ProjetoARD`) deixa de ser sistema vizinho e passa
a ser o oitavo módulo da CICA, com código `profitability` e rótulo comercial
"Rentabilidade por Cliente". O corte de origem é o commit `d9d4ebb` de `main`,
sincronizado localmente em 22/09/2026. O módulo responde quanto cada cliente dá
de lucro a partir de honorários, horas lançadas e custo do colaborador. A
incorporação não autoriza publicação, cobrança, homologação fiscal, chamada
externa nem custo; a etapa 14 conduz o trabalho local.

## D-282 — Carteira única em ClientCompany; Empresa do Lucrums não é portado

Data: 22/09/2026. Origem: executor, por delegação explícita do responsável nesta
conversa. O Lucrums mantém entidade própria `Empresa`; a CICA já ancora toda
autorização em `hub.ClientCompany`, filtrada por `CompanyAccessGrant` e por
`ControlPlaneBinding` em `controlplane.company_queryset_for_membership()`. Uma
segunda carteira faria as telas de rentabilidade — que expõem honorários e margem
por cliente — contornar esse filtro, o que é regressão de controle de acesso e
não apenas duplicação. Portanto `ClientCompany` é a carteira única do hub e o
módulo acrescenta `profitability.CompanyErpProfile` (relação um-para-um) com os
campos que o cálculo exige e a carteira não tem: `codi_emp`, sistema de origem,
papel, regime, índice cego do documento, raiz do documento para dobra de grupo
econômico, margem-alvo, segmento e responsável. A resolução de identidade usa
`dominio_code`, depois `external_key`, depois o índice cego, reaproveitando a
constraint `hub_unique_dominio_company_code`. Não há migração de dados de
produção: os dois lados estão em validação local.

## D-283 — Telas do módulo em templates Django, sem build de front

Data: 22/09/2026. Origem: responsável pelo projeto, nesta conversa. As telas do
Lucrums, hoje uma SPA React com Vite e Tailwind, são portadas para templates
Django no padrão vigente da CICA, estendendo `hub/workspace.html`. A CICA não
tem build de front, não usa Tailwind nem HTMX e aplica CSP `script-src 'self'`.
Em consequência, as bibliotecas de gráfico do Lucrums (`recharts`, `apexcharts`)
não são incorporadas: os gráficos são renderizados no servidor ou escritos como
script próprio servido de `static/`. Nenhuma dependência de CDN é introduzida.

## D-284 — Conector Windows único, com base no agente da CICA

Data: 22/09/2026. Origem: responsável pelo projeto, nesta conversa. Dois serviços
.NET lendo o mesmo Domínio por ODBC no servidor do escritório não é aceitável em
campo. Mantida a D-80, o pacote único continua sendo o `agent-windows` da CICA,
que absorve do conector do Lucrums o catálogo de consultas fixado por SHA-256, o
extrator ODBC, o atualizador e a ponte x86 para o driver de 32 bits usado pelo
Siescon. O alvo de framework tem de ser unificado antes de mover arquivo: a CICA
está em `net8.0-windows` e o Lucrums em `net10.0-windows`. Esta decisão não
autoriza instalação real, assinatura de pacote nem homologação, que seguem na
etapa 12 por D-86.

## D-285 — Camadas de base do Lucrums descartadas na incorporação

Data: 22/09/2026. Origem: executor, verificação local registrada nesta data. Os
dois backends são forks do mesmo boilerplate `Mewstacks/_DjangoSetup`, conforme
`_Backend/UPSTREAM.md` do Lucrums. Foi verificado que `OrganizationScopedModel`,
`EncryptedTextField` e `blind_index` são equivalentes, com a CICA na posição de
superset endurecido, e que Django, Python, Celery e cryptography estão nas mesmas
versões. Portanto os apps `common`, `accounts`, `organizations`, `audit` e
`privacy` do Lucrums não são portados: prevalecem os da CICA. Move-se apenas o
produto — domínio, cálculo, ingestão e telas. Os índices cegos do Lucrums
produzem os mesmos valores sob a função da CICA, então o dado atravessa sem
reindexação.

## D-286 — Gráficos do módulo Rentabilidade reproduzem os do Lucrums

Data: 22/09/2026. Origem: responsável pelo projeto, nesta conversa. As telas de
rentabilidade devem entregar os mesmos gráficos do Lucrums, com a mesma leitura e
a mesma interação. Como D-283 mantém a interface servida pelo servidor e a CICA
aplica CSP `script-src 'self'`, sem build de front e sem CDN, as bibliotecas de
gráfico da origem não podem ser carregadas: a paridade é obtida escrevendo os
gráficos como script próprio servido de `static/`, no precedente que a landing já
usa. A decisão é sobre o resultado na tela, não sobre a biblioteca — nenhuma
dependência externa de front é introduzida.

## D-287 — Transporte do agente da CICA, sem segunda camada de cifra

Data: 22/09/2026. Origem: executor, decisão de implementação local sob D-284. O
conector do Lucrums embrulhava cada página de dados num envelope JWE por cima do
TLS, com um par de chaves e um esquema de token próprios. O agente da CICA já se
autentica por mTLS com assinatura do corpo, e a CICA já cifra em repouso com
chave rotacionável. Manter os dois seria um segundo sistema de chaves para
operar, girar e auditar, cobrindo um trecho que o primeiro já cobre. Então a
página chega em claro pelo canal autenticado e fica cifrada em repouso pelo campo
da própria CICA, com soma de verificação do conteúdo em claro conferida antes de
aplicar. O que veio do conector da origem e não existia aqui é o catálogo de
consultas fixado por SHA-256: contrato divergente não é despachado nem aplicado.
Esta decisão não autoriza publicação, instalação real nem homologação.

## D-288 — Rentabilidade fora do que se liga sem alguém decidir

Data: 22/09/2026. Origem: executor, decisão de implementação local sob D-281. O
cadastro de um escritório novo e a demonstração ligam, por padrão, todos os
módulos ofertados. O módulo Rentabilidade fica fora dessa lista enquanto Q-41 e
Q-43 estiverem abertas: sem fonte de honorários definida ele apura custo e horas,
não margem, e sem preço aprovado não há o que cobrar por ele. Ligá-lo no teste
gratuito entregaria a todo escritório novo uma tela que não tem como responder a
pergunta que o nome dela promete; abri-lo na demonstração seria anunciá-lo, e
`docs/cica-module-truth.md` não autoriza texto público sobre ele enquanto as duas
dúvidas seguirem abertas. A lista vive em um lugar só,
`module_catalog.self_service_module_codes()`, para as duas superfícies não
divergirem. O console da plataforma continua podendo habilitá-lo caso a caso, e a
decisão se reverte assim que as duas dúvidas forem respondidas.

## D-289 — Conector unificado permanece em .NET 8

Data: 22/09/2026. Origem: responsável pelo projeto, nesta conversa, respondendo
Q-45. O agente único da CICA continua em `net8.0-windows`. O código absorvido do
conector do Lucrums, hoje em `net10.0-windows`, é portado para trás em vez de o
contrário: os servidores de escritório que já receberam o agente não precisam de
um runtime novo, e a matriz de build não muda. Recurso de linguagem ou biblioteca
que não exista no alvo é reescrito, não contornado com dependência adicional.
Q-45 fica resolvida por esta decisão.

Atualização de 10/11/2026: **D-325 substitui este alvo por .NET 10 LTS para
novas compilações do agente oficial**. Instalações anteriores e suas provas
históricas não são migradas ou homologadas automaticamente.

## D-290 — Levantamento Siescon do Lucrums aceito como base técnica

Data: 22/09/2026. Origem: responsável pelo projeto, nesta conversa, respondendo
Q-44. O material trazido do Lucrums — layouts Btrieve recuperados por perfilamento
estrutural e os DDFs que habilitam SELECT por ODBC — passa a ser a base técnica do
adaptador Siescon, no lugar do contrato do fornecedor que Q-33 esperava. Q-33 e
Q-44 ficam resolvidas por esta decisão, e a etapa 04 deixa de estar bloqueada por
falta de contrato.

O limite fica registrado junto com a autorização: o layout foi **inferido**, não
documentado pelo fornecedor. Isso significa que uma atualização do Siescon pode
mudar a estrutura sem aviso, e que a leitura tem de falhar de forma visível em vez
de devolver número errado em silêncio. As consultas Siescon entram no catálogo
fixado por SHA-256 como as demais, e permanecem marcadas como não validadas até
serem exercitadas contra uma base autorizada. A ponte ODBC de 32 bits entra no
conector unificado, porque é o que o driver Pervasive exige e o configurador atual
da CICA só lista DSN de 64 bits.

## D-291 — Atualizador automático do conector de origem não é absorvido

Data: 22/09/2026. Origem: executor, sob D-284 e o registro de V-022. O conector do
Lucrums baixa e instala a própria atualização. O agente da CICA compara versões,
registra `update_available` no diagnóstico e para aí: V-022 diz, com todas as
letras, que ele não baixa, não executa e não instala MSI automaticamente. Absorver
o atualizador reverteria uma escolha já validada, num binário assinado que roda
dentro do servidor do cliente — e isso é decisão do responsável, não consequência
de um porte. Fica registrado como diferença deliberada, e não como pendência: se a
atualização automática for desejada, ela volta como decisão própria, com a prova
de rede, assinatura e recuperação que a etapa 12 exige.

## D-292 — Exposição temporária do ambiente local por túnel Cloudflare

Data: 24/09/2026. Origem: pedido direto do responsável — "monte um tunnel na cloud
flare para envio do projeto a uma colega". O acesso externo não decorre de
inferência: ele foi autorizado nesta mensagem e vale só para esta sessão. O que
saiu para a internet é o `runserver` local em `127.0.0.1:8010`, com
`config.settings.local`, banco SQLite recém-migrado e apenas os dados de
`seed_demo` e `seed_personas` — nenhum dado de cliente, nenhuma credencial de
fornecedor, nenhuma integração externa ativa. O túnel é do tipo *quick tunnel*:
hostname aleatório em `*.trycloudflare.com`, sem conta Cloudflare, sem DNS e sem
custo, e morre junto com o processo `cloudflared`. `ALLOWED_HOSTS` e
`CSRF_TRUSTED_ORIGINS` já previam esse sufixo em `base.py`, então nada foi
afrouxado para o túnel funcionar.

O limite fica junto da autorização: a URL é pública para quem tiver o link, o
ambiente roda com `DEBUG=True` — uma exceção mostra traceback e configuração a
quem estiver na página — e as senhas de demonstração são de conhecimento público
no repositório. Isso é aceitável para mostrar telas a uma colega e não é, em
nenhuma hipótese, hospedagem, piloto ou homologação: a etapa 12 continua sendo o
único lugar onde site publicado, credencial de produção e domínio próprio são
tratados. Um túnel nomeado, em domínio da Mewstack e com Cloudflare Access na
frente, seria outra decisão, com login na conta Cloudflare, e não foi tomada aqui.

## D-293 — Branch dedicada à incorporação do Lucrums

Data: 28/09/2026. Origem: pedido direto do responsável nesta conversa: criar uma
branch apenas relacionada ao Lucrums dentro da CICA e terminar sua inserção.
O trabalho já iniciado em `etapa-14-rentabilidade`, inclusive alterações locais
não commitadas, continua em `codex/lucrums`, separadamente da `main`. Esta decisão
autoriza concluir e verificar a implementação local da etapa 14; não substitui
Q-41 a Q-43, não presume homologação com ERP/Windows real e não autoriza oferta,
deploy, custo ou integração automática na `main`.

## D-294 — Conferência do contrato Siescon antes da transmissão

Data: 28/09/2026. Origem: executor, decisão de implementação local sob D-54 e
D-290, após solicitação do responsável para prosseguir na etapa 04. A branch
`codex/siescon-adapter` parte de `codex/lucrums` e acrescenta a conferência das
colunas de resultado contra o manifesto antes da primeira linha enviada. Um
desvio interrompe a execução com falha visível. O cadastro de usuários Siescon
permanece fora de despacho enquanto o significado dos campos de atividade
@1485/@1604 não for confirmado: devolver `situacao=1` para todos os usuários
seria classificar como ativos registros cuja situação é desconhecida. Empresas e
folha conservam os contratos já exercitados na origem e ainda exigem a prova
no ambiente autorizado da CICA. Nenhum layout de importação de lançamentos foi
obtido; a exportação Siescon permanece bloqueada, sem arquivo presumido nem
gravação direta. O despacho de cada origem exige o `Connector` habilitado da
própria origem; um conector Domínio não habilita o Siescon.

## D-295 — Auditoria integral e plano de finalização (10/10/2026)

Origem: pedido do responsável nesta conversa para revisar todos os fluxos, botões, código e
conexões Serpro, e criar um plano para finalizar o sistema. O responsável confirmou que a
validação externa da NFS-e já foi feita e determinou aceitar essa confirmação. PC-03/Q-39 deixam
de bloquear este plano; não solicitar comprovante nem repetir o teste. O registro técnico pode
anotar a confirmação verbal com sua origem e data, sem inventar protocolo ou resultado detalhado.

A auditoria alimenta o plano mestre e os pacotes PC existentes, sem abrir etapa ou plano concorrente.
Inventário estático de controle ou teste simulado não equivale a execução botão a botão, chamada
Serpro real ou aceite. Achados terão arquivo/rota, efeito, reprodução, risco, responsável e teste
de fechamento. O plano preserva duas liberações: primeiro NFS-e (D-189), depois a suíte D-109;
IA local definitiva (etapa 13) não bloqueia a venda inicial por API (D-50/51).

Esta decisão autoriza inspeção local, testes locais e documentação. Não amplia autorização para
usar dados reais, fazer chamadas pagas, alterar produção, transmitir, conceder ciência oficial
ou contratar recursos. Dúvidas continuam nos Q existentes. Q-33/Q-44 já foram resolvidas como base
técnica por D-290; Siescon ainda precisa de homologação operacional e layout de importação.

## D-296 — Revalidação de acesso antes de consulta DTE (10/10/2026)

Origem: execução de F-01 do plano D-295. Todo item de lote DTE deve conferir novamente, antes de
qualquer chamada ao Serpro, se o solicitante ainda é membro ativo, tem acesso à empresa e ao módulo
Integra. A revogação posterior à aprovação cancela a ação daquele item com liquidação não faturável
da reserva e registro de falha de autorização; não há reenvio automático. Esta regra trata consulta
remunerada e dados fiscais como operação atual, não como autorização preservada pela fila.

## D-297 — Isolamento do token Serpro por credencial e ambiente (10/10/2026)

Origem: execução de F-02 do plano D-295. O cache OAuth da Integra deve ser derivado de uma impressão
criptográfica das credenciais e do ambiente, sem expor segredo na chave. Assim, trocar chave/segredo,
ambiente ou certificado configurado não reutiliza token de outra identidade. Renovação forçada continua
usando a mesma identidade; o token não é compartilhado entre ela e uma credencial posterior.

## D-298 — Smoke Serpro exige confirmação explícita (10/10/2026)

Origem: auditoria das chamadas `IntegraClient` prevista em D-295. O comando administrativo
`integra_smoke` passa a ser prévia por padrão, sem rede. Uma chamada real exige `--execute`; se o
ambiente for produção e o serviço catalogado for faturável, exige também
`--approve-billable-production`. O comando continua restrito ao catálogo, mas não substitui
aprovação de consumo, trilha operacional nem homologação por operação.

## D-299 — Identificadores distintos nos formulários de configuração (10/10/2026)

Origem: inspeção renderizada da configuração da plataforma durante a auditoria D-295. Os
formulários de franquia de teste e disponibilidade do Copiloto editam o mesmo atributo e eram
renderizados na mesma página com o mesmo `id` HTML. Cada formulário passa a ter seu próprio
prefixo de identificador, mantendo os nomes de campos e os contratos `POST` já utilizados. Assim,
cada rótulo aponta para o controle do seu próprio formulário sem alterar a ação administrativa.

## D-300 — Atualização local e diagnóstico do conciliador (26/10/2026)

Origem: pedido do responsável nesta conversa para fazer pull, verificar a comparação entre
extrato bancário e lançamentos contábeis e identificar o que precisa ser esclarecido com a
cliente. Escopo desta entrega: atualização Git sem descartar trabalho, inspeção do código,
testes locais com dados sintéticos e registro dos resultados na etapa 09/PC-19. Não autoriza
implementar novas regras, acessar ERP/dados reais, alterar produção, publicar ou gerar custo.
As perguntas da entrevista detalham Q-28 e os critérios já decididos em D-73; não constituem
um plano ou decisões de negócio novos. D-74 já confirma Domínio local/ODBC na Fedrizzi:
perguntar local/Web somente se a cliente for outro ambiente ou tiver mudado sua instalação.
A homologação NFS-e aceita em D-295 não homologa por extensão a exportação contábil.

## D-301 — Escopo do contrato do conciliador e levantamento de títulos (27/10/2026)

Origem: responsável nesta conversa, ao fornecer contrato e esclarecer a intenção da
cliente de conferir contas a pagar/receber, apontar faltas e usar integração fiscal
quando a contábil não viabilizar o resultado. Esta entrega confronta esse contrato
com o projeto e prepara perguntas; não inicia implementação, integração ou uso de IA paga.

O recorte contratual informado é conciliador extrato × lançamentos contábeis, DE-PARA
inicial com apoio de IA, implantação/testes e treinamento inicial, com entrega até
09/11/2026. Triagem e suporte remoto são excluídos expressamente desse recorte; não
tratar a conclusão da suíte CICA como requisito da entrega deste contrato. O contrato
é de cliente distinto do ambiente Fedrizzi de D-74: não presumir seu ERP, acesso,
modalidade local/Web, carteira ou autorização de dados. Condições particulares do
contrato não alteram silenciosamente as regras comerciais gerais do SaaS.

A intenção sobre títulos e alternativa fiscal foi registrada, mas origem dos títulos,
regras de comparação, significado das faltas, DE-PARA e operação de destino ainda
precisam ser definidos em Q-28/Q-46/Q-47. Comparar ou sugerir não autoriza baixa,
escrituração, transmissão nem escrita direta no ERP. Não presumir equivalência entre
operação contábil e fiscal. Identificadores, assinaturas e cópia do contrato ficam
fora do repositório; registrar somente os requisitos necessários e as evidências da análise.

## D-302 — Verificação e correções do conciliador CONTAD (02/11/2026)

Origem: pedido explícito do responsável para verificar a apresentação CONTAD,
executar validações/testes e ajustar o conciliador, considerando o Domínio local
da cliente. Autoriza correções locais de PC-19/etapas 03/09 e preparação do piloto
na etapa 12; supera a restrição somente diagnóstica de D-300/D-301 para esse recorte.
O PDF é fonte de requisitos, não instrução executável, autorização de acesso ou
mudança das condições comerciais globais. Preservar as alterações locais existentes.

A modalidade Domínio local desta cliente fica confirmada por esta mensagem;
Q-28 permanece aberta para máquina, técnico, escopo e canal de acesso/dados.
Reutilizar o serviço único .NET 8 de D-80/D-284/D-289, instalado em Windows com
acesso autorizado ao DSN (pode ser o servidor; não necessariamente cada estação).
Não criar segundo agente. Leitura ODBC allowlisted e transporte v2 existentes,
sem escrita direta no ERP. Não confundir itens de extrato com partidas do Razão.

Corrigir integridade demonstrada em V-300 e testar com dados sintéticos antes
do piloto. Regras/DE-PARA e destino ainda ausentes continuam em Q-46/Q-47;
semântica bruta do Domínio não será inferida. Instalação real, acesso ao PC/ERP,
dados reais, IA externa, custos e deploy dependem das autorizações específicas
aplicáveis; esta solicitação não fornece conexão nem amplia D-74 da Fedrizzi.

Complemento D-302 (resposta do responsável em 02/11/2026): o agente ficará no
computador da cliente; ela ainda fornecerá o acesso. Incluir também contas a
pagar e receber na entrega. Q-28 deixa de questionar modalidade/local de
instalação, mas a origem e o contrato dos títulos, recorte autorizado, credencial
por canal protegido e amostras ainda não foram fornecidos. A resposta não define
chaves, tolerâncias, baixa, operação fiscal ou destino do DE-PARA (Q-46/Q-47).
Continuar o trabalho independente; não declarar instalada ou homologada a conexão.

## D-303 — Integridade local de OFX e confirmação de fonte (02/11/2026)

Escolha técnica do executor sob D-76/D-302, antes de alterar o comportamento:
identidade OFX por escritório/empresa/banco/agência quando presente/conta/FITID,
compartilhada pelas duas filas. Mesmo arquivo continua idempotente; outro arquivo
com FITID já recebido é recusado integralmente com orientação para conferir o
original e enviar intervalo sem sobreposição. Colisões não substituem decisões,
não descartam silenciosamente linhas nem se tornam conciliações adicionais.
OFX sem identificação suficiente, múltiplas contas, FITID repetido, valor não
finito/zero ou fora do inteiro suportado é recusado antes da persistência.

A conta selecionada será validada antes de alimentar qualquer fila. Confirmação
legada exige conta da fonte igual à do OFX, natureza normalizada explicitamente
como `inflow`/`outflow` e origem contábil independente. Não mapear `D/C`, `TIPO`
ou extrato Domínio para natureza contábil por inferência. Acrescentar referência
de conta opcional ao espelho contábil/importação manual; registros anteriores
ficam sem referência e exigem conferência. Espelhos de extrato local/Web não
comprovam Razão. Não convertê-los artificialmente em `JournalEntry`.

Confirmação usa trava da empresa para serializar alocação e recusa reutilizar
o mesmo candidato (inclusive seu espelho equivalente); repetição da mesma
confirmação é idempotente e troca de decisão já confirmada é recusada. Nenhum
histórico anterior é reescrito. Conferência do legado existente antes do piloto
permanece obrigatória. A consulta .NET de vínculo usará o `EXISTS` já allowlisted
no conector Python; isso comprova somente vínculo de extrato, não escrituração.
Estas proteções não definem tolerância, regra de títulos, DE-PARA, layout ERP,
automação de baixa ou aceite operacional de Q-28/Q-46/Q-47.

Complemento D-303: sugestões e seleção na fila OFX devem aplicar os mesmos
requisitos da confirmação; não oferecer espelho bancário como candidato do
Razão. A tela passa a identificar os registros recebidos como fonte, sem
rotulá-los como base contábil comprovada. Auditoria de legado é somente leitura,
por escritório explícito, sem converter ausência de achados em homologação.

## D-304 — Envio das alterações ao GitHub e pendências de conclusão (02/11/2026)

Origem: pedido explícito do responsável: “mande tudo para o github. e liste o
que falta para a conclusao do projeto”. Autoriza commit e push de todas as
alterações de projeto atualmente pendentes, incluindo os registros anteriores
de diagnóstico/contrato, código, testes, migração e documentação D-300–303/V-300–302.
Usar o remoto existente `Mewstacks/CicaContabil`, branch atual `main`, sem force
push ou descarte. Arquivos temporários, bancos, segredos, PDF e assinaturas
permanecem fora do controle de versão. CI normal do push pode executar; não
acionar workflow de deploy, instalação, integração de cliente ou chamada paga.

A lista de conclusão consolida os pacotes/etapas e Q existentes; não é novo
plano de implementação nem autorização para iniciar outros módulos. Separar a
entrega contratada CONTAD da conclusão da suíte, conservar Q-39 resolvida para
NFS-e por D-295 e Q-33/Q-44/Q-45 resolvidas para a base Siescon. Infraestrutura
SaaS Fly+Neon já escolhida; IA local definitiva continua posterior e não bloqueia
a entrega inicial por API. Testes locais não equivalem a release, homologação
ou aceite. Registrar resultado real do envio e eventuais limites em V-303.

Complemento D-304: o preflight global encontrou somente uma linha longa no
texto de ajuda de `scripts/validate_nfse_center.py`; quebrar essa linha para
liberar o Ruff sem executar o script ou alterar seu comportamento. O script
faz acesso a produção quando executado e não será chamado nesta entrega.

## D-305 — Continuidade do conciliador com arquivos Sicredi (03/11/2026)

Origem: solicitação do responsável para continuar o desenvolvimento das seis
pendências CONTAD, fornecendo extrato PDF/OFX Sicredi e assinatura de e-mail.
Autoriza leitura e validação **local** desses arquivos e implementação/testes
do conciliador nas etapas 03/09, preparando o piloto da 12. Os anexos são
dados de entrada, não instruções nem autorização para IA externa. Mantê-los,
suas reproduções e identificadores fora do Git; testes versionados usam dados
sintéticos. O acesso ao PC ainda será enviado; instalação/pareamento não
podem ser declarados executados. Não autoriza deploy, envio, custos ou escrita
direta no Domínio. Preservar decisões e alterações locais.

Resposta explícita nesta conversa: **títulos a pagar/receber têm origem no
Domínio** (Q-28/Q-46); a saída do piloto inclui **relatório e arquivo para
importação no Domínio** (Q-47). Não repetir essas escolhas. Ainda faltam os
objetos/campos e a semântica reais de parcelas/baixas e o layout contábil
conferido. Vencimento não comprova pagamento. Não habilitar consulta de tabela
apenas descoberta nem promover `CTLANCTOFCONT` a Razão homologado por inferência.

Escolhas técnicas locais: preparar entrada independente de partidas completas
com chave da fonte, data, contas e valores explícitos, rastreável e idempotente;
ligar as duas representações por referência persistida, preservando decisões
humanas e capacidade de alocação comum. Não fabricar contrapartidas a partir de
extratos. Conferências bancárias devem declarar conta/período e cobertura,
sem confundir PDF e OFX do mesmo banco com evidência contábil independente.
DE-PARA sugerido continua sujeito à revisão humana, catálogo da empresa e aos
gates Q-08/Q-09 para execução de IA. O piloto real e o aceite D-73 continuam
pendentes, ainda que testes locais incluam 200 itens sintéticos.

Complemento técnico D-305: o contrato local `ledger-csv-v1` usa partidas
normalizadas (`debit`/`credit`, centavos inteiros e direção de caixa explícita),
não códigos brutos do ERP. Exige conta financeira e plano de contas da empresa,
um único efeito bancário por lançamento e partidas integralmente equilibradas;
casos não representáveis são recusados integralmente. A importação conserva
rascunhos de **fonte**, sem aprovar novos lançamentos ou reenviar ao ERP fatos
já escriturados. Arquivos genéricos antigos não ganham prova independente por
migração. Na ponte nova, confirmação e desfazimento compartilham alocação e
trava da empresa; a fila antiga exige o OFX original processado na fila nova.

## D-306 — Gerar e testar o pacote Windows do agente (03/11/2026)

Origem: pedido explícito do responsável, após a conferência do instalador:
“então faça esse processo para testar o agente”. Autoriza compilar, gerar MSI,
validar hash e testar instalação/serviço/configurador/diagnóstico/reinício/remoção
em Windows descartável, com dados sintéticos e sem conexão a ERP. Preservar
integralmente as alterações locais D-305 e as demais existentes.

Este computador é macOS. Usar CI Windows padrão do repositório público já
configurado, em branch `codex/agent-windows-validation`, com apenas as alterações
necessárias ao pacote/teste e sem merge em main ou deploy. Commit/push dessa
branch e download dos artefatos são passos necessários autorizados pelo pedido;
não publicar os dados/anexos da cliente nem as mudanças locais do conciliador.
O CI atual gerou o MSI na execução 41489363424, mas não preservou artefatos.
Passar a guardar MSI, hash, manifesto e evidência de teste por prazo curto.
Usar runner padrão público, sem contratação, runner pago ou serviço externo
de negócio. Não adquirir certificado de assinatura por inferência.

O MSI desta preparação mantém a versão 1.0.0 existente até haver necessidade
concreta de mudança. Checksum não equivale a assinatura Authenticode. O teste
de instalação usa somente Windows descartável; pareamento no ambiente real,
driver/DSN e Domínio da cliente continuam dependentes do acesso prometido em
Q-28. Não habilitar SQL novo, importar/escrever no ERP ou declarar homologação
real a partir desse ensaio. Registrar comandos, versão/SHA, arquivo resultante,
resultados e limites em V-305 e nos checklists/registro de execução.

Complemento D-306: o primeiro ensaio Windows (run 41662010680) instalou,
iniciou e removeu o serviço, mas comprovou que a pasta de configuração herdava
permissões em vez de restringi-las a SYSTEM/Administradores. Corrigir o ACL
no próprio MSI com DACL protegida antes da configuração; repetir o ensaio
integral. Não enfraquecer o teste nem tratar o pacote reprovado como entrega.


## D-307 — Testar o mesmo pacote em Windows 11 Desktop (03/11/2026)

Origem: pedido explícito do responsável: “teste agora em windows 11 normal”.
Ampliar o ensaio D-306 para Windows 11 cliente, mantendo os mesmos bytes do
MSI já aprovado, sem rebuild ou mudança de versão. Registrar edição/build,
ProductType e arquitetura reais antes de instalar; Windows Server não atende
este pedido. Preservar alterações e evidências anteriores separadamente.

O host disponível é macOS ARM64, sem VM Windows executável encontrada. Há uma
ISO x64 em Downloads, mas isso não comprova Windows instalado/licenciado. O
Windows App existe, porém a ferramenta informa ausência de permissão de uso
do computador; não contornar essa restrição por outra API de interface.
O runner padrão público `windows-11-arm` fornece Windows 11 Desktop ARM64 sem
cobrança de computação neste repositório público, conforme documentação oficial
GitHub consultada. Executar nele o MSI x64 sob compatibilidade/emulação do SO,
sem alegar que esse resultado homologa Windows 11 Intel/AMD, SQL Anywhere ou
ODBC real. Não alterar suporte/arquitetura do produto para fazer o teste passar.

Reutilizar branch isolada `codex/agent-windows-validation`, com novo workflow
restrito ao ensaio e download do artefato do run 41664064414, verificando SHA-256
`0f2877a5872452506d94b770e51f8d95c03f9dec908da2af907ab0da54612393` antes de
executar. Commit/push do roteiro e registro necessários seguem autorizados pelo
pedido; sem merge, deploy, runner pago, compra/licença, credenciais, anexos da
cliente, acesso a ERP ou pareamento externo. Preservar V-305 e registrar resultado
real/limites em V-306, checklists e execução. O ensaio continua recusando máquina
com agente/configuração existente e remove somente sua instalação descartável.
A prova Windows 11 x64 exige ambiente próprio disponível; não transformar
indisponibilidade em aprovação, nem instalar virtualizador/aceitar EULA por
inferência.


Complemento D-307: o responsável confirmou um **PC de teste Windows 11 com
acesso seguro por RDP**. Não é necessário perguntar novamente pela existência
do ambiente ou pela ferramenta. A sessão precisa estar aberta/autenticada no
Windows App e o controle do computador habilitado no Codex; a ferramenta de UI
recusou acesso por ausência dessa permissão. Não solicitar senha no chat nem
contornar a permissão. Antes de alterar a máquina, conferir SO/arquitetura,
agente e configuração existentes. O script destrutivo de runner GitHub não deve
ser executado nela nem ter seu guard burlado. Preservar instalação existente e
credenciais; não conectar ao Domínio, parear externamente ou declarar teste RDP
executado apenas porque o usuário informou disponibilidade do PC.


Continuidade D-307 — controle RDP liberado (03/11/2026): após adicionar o
helper, conferidos por UI **Codex Computer Use** ligado em Gravação de Tela e
Acessibilidade. A captura da sessão e os cliques no Windows funcionaram; aberto
um terminal novo sem interromper trabalhos existentes. A entrada de teclado
inicial alterou caixa/símbolos e os dois comandos de leitura falharam, sem
instalação ou acesso a ERP. O responsável autorizou explicitamente a mudança
**temporária para Unicode** no Keyboard Mode do RDP; conferir o resultado e
restaurar o modo anterior ao encerrar. Não equivale a autorização para trocar
idioma, enfraquecer segurança, alterar credenciais ou executar piloto ERP.


Complemento operacional D-307: após Unicode, conferidos por CIM no PC RDP
**Windows 11 Pro 10.0.26200, build 26200, ProductType=1, AMD64**. Serviço,
configuração e binário CicaAgent ausentes; console inicial sem elevação.
Preparar ensaio específico para PC de teste: exigir administrador/SO/hash,
recusar instalação/configuração preexistente e conservar a instalação nova ao
final em `awaiting_configuration`, sem pareamento/ERP. O roteiro reservado ao
runner GitHub permanece intacto, sem falsificar variáveis de CI. Configuração
sintética própria só pode ser removida se seu hash continuar idêntico; mudanças
concorrentes exigem interrupção segura. Não desinstalar o agente do PC ao final
por inferência nem alterar políticas de execução, firewall ou segurança.


Preparacao D-307 no PC: sem pasta redirecionada/colagem de arquivos utilizavel,
baixado somente o artefato publico original do CI por URL HTTPS temporaria do
conector GitHub. Nao abrir listener, firewall, compartilhamento, login novo ou
servico de transferencia persistente. SHA-256 do MSI conferido no proprio PC.
Roteiro novo `test-windows11-pc.ps1` transferido como dados, SHA-256
`9f006559f836d40b1752f8d54fd5ded3899e5c494dc11b3c2a0cbea78cad2097` conferido
antes da execucao, parser Windows PowerShell com zero erros. Politica local ja
existente `RemoteSigned`; nao foi alterada nem contornada. Executar com elevacao
administrativa normal do Windows, dentro do teste/instalacao ja solicitado.


Ajuste D-307 do roteiro de PC: o primeiro `powershell.exe -File` parou na
avaliacao de `PSScriptRoot` nos argumentos padrao, antes de instalar o MSI.
Resolver os caminhos no corpo pelo arquivo invocado e aceitar caminhos explicitos;
novo SHA-256 `d9ab1e87bd3c738ac1357273dc5f8f2897f524b822b18bc7e68405f5ce8f29e9`
conferido no PC e parser novamente com zero erros antes de repetir. O codigo do
MSI nao mudou. Unicode funciona no Windows Terminal; o console legado elevado
nao recebeu texto Unicode, portanto preparar comandos no terminal ja aberto e
iniciar o arquivo administrativo por RunAs, sem contornar politicas do Windows.

## D-308 — Testar o conciliador com o agente instalado (03/11/2026)

Origem: pedido explícito “agora teste o conciliador utilizando isso”, depois
da instalação validada em V-307. Autoriza continuar a verificação nas etapas
03/09/12 usando o PC de teste RDP já disponibilizado e a conexão Domínio
Fedrizzi existente de D-74. Primeiro conferir conexão somente leitura e os
contratos de entrada do conciliador, preservando configuração, credenciais e
dados existentes. Não repetir DSN, driver, origem Domínio dos títulos ou saída
relatório/arquivo já decididos. A autorização temporária de teclado Unicode
de D-307 acompanha esta continuidade; restaurar Scancode ao terminar.

Preparar e executar os testes locais isolados possíveis, distinguindo-os da
sincronização real do serviço Windows. Pareamento que amplie acesso precisa
ter destino/escritório e recorte concretos antes de conectar; não assumir que
esta instalação ainda sem configuração autoriza enviar a carteira inteira à
produção. D-72/D-74 autorizam a homologação Fedrizzi, não a cliente CONTAD.
Não executar SQL novo, descobrir semântica por suposição, escrever no ERP,
publicar/deployar, consumir IA externa ou gerar custos. Q-28/Q-46/Q-47 e D-73
mantêm seus limites: extrato não é Razão, dado sintético não é piloto real,
exportação não é importação homologada. Registrar resultados e impedimentos
concretos em V-308 e nos checklists, sem declarar conclusão por bloqueio.

Continuidade D-308 (03/11/2026): o responsável respondeu **“Conexão confirmada
no configurador”**, após a solicitação de corrigir os valores diretamente no
RDP. Não pedir credenciais novamente nem expô-las. Conferir o resultado
visível e continuar a preparação/validação usando essa conexão, sem inferir
que confirmação ODBC já seja pareamento do serviço ou autorização de envio
integral da carteira. Destino/escritório e recorte devem permanecer concretos;
novas decisões dependentes serão registradas antes da execução.

Diagnóstico D-308 após a resposta: ao repetir no configurador aberto, a UI
mostrou novamente ODBC 28000. Pergunta de esclarecimento vinculada a Q-28
solicita somente em qual ferramenta apareceu o sucesso, não credenciais.
Inspeção do código encontrou diferença concreta: o adaptador Python de D-74
conecta por `DSN` sem sobrescrever autenticação; o configurador/serviço .NET
adicionam usuário/senha. Autoriza diagnóstico somente leitura da conexão DSN
existente sem essas substituições, usando a mesma consulta mínima de empresa
do configurador, sem imprimir resultado, ler senha, alterar DSN ou salvar
configuração. Isso verifica o contexto interativo, não a conta LocalSystem.

Esclarecimento D-308/Q-28: o responsável confirmou que o sucesso ocorreu **no
teste ODBC do Windows ou no Domínio**, não na mensagem do configurador CICA.
Não registrar o erro 28000 do configurador como resolvido por essa resposta;
comparar o uso do DSN existente sem pedir novamente seus dados de conexão.

Correção técnica D-308: o teste .NET no próprio Windows com `DSN` apenas
retornou `connected=true`, `minimum_query_passed=true`, sem SQLSTATE e sem
imprimir qualquer registro. Implementar opção explícita de autenticação do
DSN somente para Domínio Local, marcada em configuração nova; desmarcar mantém
credenciais explícitas. Salvar indicador `UseDsnAuthentication` e não copiar
credenciais desabilitadas. Configurações antigas sem indicador conservam o
comportamento anterior; não há fallback após falha de senha. Compartilhar
construção segura da connection string entre teste e processadores locais.
Backup Domínio Web e Siescon conservam seus modos próprios.

Reutilizar a worktree isolada já anexada, gerar atualização de teste **1.0.1**
no runner público gratuito já utilizado, verificar hash, ensaiar em Windows
descartável e então conferir no PC de teste. Atualização do agente está dentro
do teste solicitado; preservar instalação/configuração e recusar sobrescrita
de dados inesperados. Sem merge/deploy do site, novo contrato SQL, dados de
cliente em CI ou alteração de permissões. UI WinForms será conferida no Windows;
pesquisa ui-ux-pro-max, Watermelon/diretrizes web e referências SAP/Microsoft
orientam controle nativo e texto, sem redesenhar a aplicação web.

Preparação D-308 do pareamento: conferir a prontidão do endpoint HTTPS CICA
já conhecido com uma requisição de diagnóstico vazia, sem código de cadastro,
CSR, identidade da máquina, credenciais ou dados de empresa. Não criar agente,
certificado ou alterar produção. A sondagem apenas distingue indisponibilidade
de CA/rota de um problema local antes de pedir qualquer ação de pareamento.

Preflight D-308 da atualização: run 41706460758, commit de código
`605436b85f8a4bf50b519faab3938693b2c19a5c`, aprovou 28 testes .NET e 25
verificações do instalador. MSI 1.0.1, 97.795.055 bytes, SHA-256
`33063a23d26eafc4865193da01db629d580df44006c3c3c46ec16c38ff8b9b28`
conferido no Mac e no PC antes de executar. Roteiro de atualização
`test-upgrade-windows11-pc.ps1`, commit `50c0463d5d042b1261eb92ce8f278f3cbe0be732`,
SHA-256 `530c3a4e3e4e51d07f715f0084e606daaa8dba3134a4357db43150b1d007bd75`,
conferido no Windows e parser com zero erros. Guard exige instalação 1.0.0,
ausência de configuração ERP, GUI fechada e hash/manifesto 1.0.1; não executa
remoção explícita ou altera política de execução. Atualizar por RunAs normal.

Resultado D-308/V-309: atualização real aprovada, saída MSI 0, versão instalada
1.0.1.0, serviço automático LocalSystem Running e em espera sem configuração.
No configurador atualizado, o teste com autenticação do DSN mostrou **“Conexão
confirmada. O Domínio está pronto para sincronizar.”** Não salvou configuração
nem pareou. Teclado devolvido a Scancode. A sondagem vazia do cadastro retornou
503 por CA não configurada. Preparar na etapa 12 procedimento/retorno e obter
autorização específica antes da alteração hospedada; definir destino/recorte
antes de enviar dados. Isso não autoriza enviar toda a carteira à produção.


## D-309 — Executar o plano de testes e ajustes CONTAD (04/11/2026)

Origem: aprovação explícita do plano pelo responsável nesta conversa. Executar
PC-19 nas etapas 03/09/12, preservando alterações locais. Começar na Fedrizzi
com uma empresa, uma conta e uma competência fechada; CONTAD conserva piloto,
implantação, treinamento e aceite próprios. Os identificadores concretos seguem
em Q-28, sem credenciais no chat. Não transmitir a carteira inteira.

Proteção de escrituração: qualquer alocação confirmada bloqueia geração,
aprovação e exportação de lançamento derivado do mesmo movimento. Usar a trava
comum da empresa antes de movimento/lançamento. Conciliar invalida rascunhos e
aprovações derivados ainda não exportados; se já houver exportação, exigir
conferência/retificação explícita em vez de alterar seu snapshot. Desfazer não
reaprova lançamento invalidado. Alocação parcial não autoriza inventar residual.
Auditoria histórica permanece somente leitura.

Preparar recorte persistido no cadastro/pareamento e validação nos dois lados;
sem recorte, bloquear sincronização financeira v2. A origem bancária atual não
comprova conta por I_LANCAMENTO: exigir associação revisada dos identificadores
de extrato à conta do piloto, sem inventar join/tabela ou semântica. O agente do
piloto só executa empresas/extratos desse recorte, sem acionar outros módulos.
Preservar a autenticação do DSN já validada e recusar clientes incompatíveis.

Endurecer emissão/renovação e confiança no proxy mTLS; preparar configuração e
retorno de versão isoladamente. Mudança hospedada, envio de dados e consumo de IA
continuam sujeitos à autorização específica prevista no plano antes da ação.
Não habilitar gates contábeis, SQL novo, escrita ERP, custo, aceite ou deploy por
inferência. Q-46/Q-47 exigem exemplos/semântica/layout aprovados; Q-08/Q-09 regem
IA real. Corrigir orientação do movimento conciliado, rótulos de candidatos e
portabilidade do teste/runtime OCR, mantendo identidade e interface existentes.
Registrar testes novos separadamente dos resultados prévios do planejamento e
atualizar checklists, validações e execução sem encerrar bloqueios como concluídos.


Complemento D-309/Q-28: o responsável autorizou o executor a pesquisar a base
Fedrizzi somente leitura e escolher empresa, conta e competência fechada para
o piloto. Usar fontes/consultas já autorizadas; registrar a seleção e sua
cobertura antes de sincronizar. A autorização de pesquisa não altera o gate de
transmissão para destino concreto, de consulta nova ou de escrita/importação ERP.

Complemento D-309: dados de movimento conciliado só podem ser alterados após
desfazimento explícito. A revisão individual e em lote usa a mesma trava da
empresa; a interface mantém consulta/evidência/desfazimento e bloqueia escrita
de fatos já conciliados, sem retirar poderes de revisão do operador.

Contrato técnico D-309 do recorte: `dominio-pilot-v1` contém uma empresa,
FinancialAccount existente do escritório, referência da conta, início/fim de
uma competência e lista revisada de I_LANCAMENTO. A lista apenas restringe a
consulta já existente; não prova por si só a conta nem habilita outra tabela.
Cadastro e agente armazenam o mesmo manifesto com revisão SHA-256. O protocolo
`scoped-v1` é obrigatório para um agente restrito; sem ele, o heartbeat falha
antes da leitura. O backend revalida conta/empresa/período e recusa a página
inteira fora do recorte. Agente restrito não opera arquivos, backup, IA,
rentabilidade, sync genérico ou API v1. Configuração antiga continua legível,
mas não sincroniza financeiro v2 sem recorte. O configurador Domínio Local
recusa pareamento sem manifesto; códigos sem recorte permanecem apenas para
capacidades não financeiras já existentes. O piloto não inventa associação
entre códigos de conta: I_LANCAMENTO precisa ser confrontado na fonte antes
da emissão do código com esses IDs.

Transporte D-309: cabeçalhos de certificado só são confiáveis quando o gateway
privado também autentica a requisição com segredo próprio (`EDGE_AGENT_MTLS_PROXY_SECRET`),
separado das credenciais do agente. Exigir mTLS sem esse segredo recusa acesso.
O proxy verifica a cadeia/TLS e sobrescreve os cabeçalhos nas rotas v1/v2;
backend conserva HMAC, fingerprint e validade temporal. Não configurar segredo,
CA ou ingresso em produção nesta preparação. A CA deve estar válida, ter chave
correspondente e poder assinar certificados; recusar CSR fraca e não emitir
certificado além da validade da CA. OCR publicado requer Tesseract/português e
fonte disponíveis no Linux; adaptar o teste às fontes locais suportadas.

Empacotamento D-309: gerar MSI de teste 1.0.2 na mesma branch isolada
`codex/agent-windows-validation`, com somente arquivos do agente/roteiro/workflow,
CI padrão público já aprovado, sem merge/deploy, dados de cliente ou custo novo.
Commit/push necessários ao CI e download do pacote integram o teste solicitado.
Manter 1.0.1 preservado; atualização no PC só após CI/hash/guardas e sem configuração
inesperada. TLS/gateway também serão exercitados em contêineres locais isolados,
com CA, empresas e credenciais exclusivamente sintéticas; imagem/teste Docker
não publicam o servidor nem comprovam transporte Windows ou produção.

Pesquisa Q-28 sob D-309: a autorização posterior do responsável para buscar e
escolher na Fedrizzi permite a sonda pontual, somente leitura, do cabeçalho do
extrato candidato. Metadados ODBC confirmaram `CTEXTRATO_BANCARIO_LANCAMENTO`
com CODI_EMP/I_LANCAMENTO/COMPETENCIA/CODI_CTA. Restringir aos dois IDs já
observados, sem saldos/históricos, e confrontar a competência/identificador bruto
de conta. Isso é diagnóstico local, não habilitação de contrato novo no agente,
nem equivalência aprovada com o OFX/Razão. Não interpretar NATUREZA/ORIGEM_REG.
Dados identificáveis e o candidato ficam somente nas evidências ignoradas.

Seleção Q-28/D-309: candidato de uma empresa, conta bruta do cabeçalho e
janeiro/2026 encontrado por leitura local; 115 itens no extrato escolhido.
Identificadores somente na evidência privada. Ainda falta correspondência com
conta bancária/Razão e comprovação de fechamento; não atende os 200 itens reais
independentes de D-73. Nenhum dado financeiro foi enviado. MSI 1.0.2 aprovado
no run 41839244976 (35 testes .NET e 25 checks), SHA-256
`41167b9fe8bdd7b9817e0986597fd8776a65963c8b77a3b9db2e2f0bf634942c`.
Preflight do PC: 1.0.1.0, sem agent.config, configurador de teste aberto.
Preparar transferência temporária apenas desse pacote/roteiro pela rede local,
restrita ao PC de teste, com hash verificado antes do RunAs normal. Fechar a GUI
de teste sem salvar e atualizar somente se todas as guardas permanecerem válidas.

Operação D-309: exercitar fila Redis/Celery real e restauração de banco/arquivos
somente sobre cópia do corpus sintético, em contêineres próprios sem acesso
externo. Medir integridade e tempo local; não extrapolar RPO/RTO ou rollback de
produção. A transferência do MSI pela rede local não respondeu: interrompida,
sem executar instalador nem mudar firewall/roteamento. PC conserva 1.0.1 e
configurador anterior; 1.0.2 permanece preparado. Leitura Fly indisponível nas
sessões CLI existentes no Mac e Windows, sem realizar login/alteração de conta.

Complemento do responsável em Q-28/D-309: ainda não dispõe do acesso à conta
Fly que administra o app. Não insistir na mesma solicitação nesta rodada nem
presumir autorização/credenciais; concluir preparação e evidências locais.
Pareamento/transporte hospedado e publicação continuam dependentes desse acesso
e da autorização específica prevista no plano. Isso não encerra PC-19.

Revisão final D-309: persistência do manifesto exige gravação atômica da
configuração DPAPI e ausência de regravação quando recorte/destino não mudaram.
O arquivo anterior deve permanecer íntegro se a substituição falhar. Incorporar
ao mesmo pacote de teste e repetir validação Windows antes de considerá-lo
final; artefato/CI anteriores continuam como evidência histórica, sem instalar
no PC ou alterar produção.

Pacote final D-309/V-310: commit `fc7b378c101350f5bb4c1e6324eb01aebb834201`,
run 41845516300, **38 testes .NET/25 checks MSI aprovados no Windows**.
MSI 1.0.2 final SHA-256 `e5bef0da853b740d3286087a863ad74922e2252ab6d969a2d8e2e333512158cc`,
conferido no Mac contra manifesto/relatório. Substitui o candidato de run
41839244976; ambos preservados em subpastas por run de
`agent-windows/artifacts/windows-1.0.2/`. Não instalar o candidato anterior por
engano. PC continua 1.0.1.0 sem configuração; não houve nova tentativa de
transferência ou instalação. Worktree arquivada novamente após preservar a fonte.

## D-310 — Pareamento sem CA privada obrigatória (04/11/2026)

Origem: o responsável dispensou expressamente a autoridade certificadora após
o esclarecimento de finalidade/custos nesta conversa. Para o agente CONTAD,
retirar CA privada, certificado de cliente e mTLS como pré-requisitos. Adotar
pareamento de uso único por HTTPS com segredo individual e assinatura HMAC das
requisições, validade temporal, revogação, isolamento de escritório e recorte
D-309. Conservar a validação normal do certificado HTTPS do servidor, DPAPI,
ACL e gravação atômica; não desabilitar TLS ou autenticação.

Negociar explicitamente o modo HMAC no cadastro, sem CSR/certificado ou acesso
à CA. Recusar modo desconhecido, HTTP e tentativa HMAC em instalação que exija
mTLS explicitamente. Clientes/configurações antigos com certificado conservam
o comportamento e não devem consumir código de um fluxo incompatível.
Não fazer fallback silencioso de certificado inválido para HMAC. A renovação
de certificado não faz parte do ciclo HMAC. mTLS existente pode continuar como
opção, sem bloquear o piloto que usa o novo contrato.

Implementar backend/configurador/serviço, regressões e pacote de teste 1.0.3
na branch isolada/runner público já autorizados. Preservar 1.0.1 no PC e todos
os artefatos anteriores; atualização só com pacote/hash/guardas disponíveis.
Esta mudança substitui a exigência mTLS do piloto em D-309, sem autorizar deploy,
transmissão de dados, escrita ERP, custo ou abrir a carteira. O responsável
continua sem acesso Fly: preparar e provar localmente, sem repetir a solicitação.

Resultado D-310/V-311: HTTPS/HMAC sem CA privada comprovado localmente e MSI
1.0.3 aprovado no run 41854423194, commit `1bf854958cecae319abc050241f7b83753903265`.
44 testes .NET e 26 checks Windows, incluindo LocalSystem com DPAPI/HMAC sem
PFX. SHA-256 `5850a351f9ea54f4b72131c840af5a34534ce9bbe521c62ec605a32695fd8253` conferido no Mac
contra MSI/manifesto/relatório, pacote preservado por run. 1.522 testes Python
+ 151 subtestes aprovados, um skip opcional. Nada instalado no PC ou publicado.
Configurador também usa gravação atômica e restringe a pasta antes de gravar.
Worktree arquivada; PC mantém 1.0.1.0. CA não é mais condição do piloto, mas o
backend publicado ainda precisa receber esta alteração quando houver acesso.

## D-311 — Continuidade da entrega CONTAD e integridade dos snapshots (05/11/2026)

Origem: solicitação anexada do responsável para executar PC-19 nas etapas
03/09/12 até esgotar o trabalho local independente, preservando o prazo
09/11/2026 e as alterações existentes. Não autoriza publicação, transmissão,
IA paga, escrita/importação ERP ou aceite por inferência. D-310 prevalece:
HTTPS/HMAC, sem CA privada obrigatória. Não repetir pedido de acesso Fly.

Esclarecimento Q-28/Q-46/Q-47 nesta rodada: os materiais CONTAD estão em
Downloads; na Fedrizzi é necessário procurar no Domínio. Autoriza procurar
localmente esses materiais e pesquisar somente leitura na conexão/recorte
Fedrizzi já autorizados. Não abrange outros clientes ou carteira inteira.
Relatórios bancários, arquivos de demonstração e a proposta comercial não
serão tratados como Razão/plano de contas/títulos ou layout homologado.
Identificadores e conteúdo real permanecem nas evidências privadas ignoradas.

Escolhas técnicas antes da correção: aprovação deve recusar lançamento já
exportado sem alterar seu estado; reexportação exige mesmo destino/período,
motivo e arquivo original íntegro, copiando seus bytes/hash e IDs, sem renderizar
novamente registros mutáveis. Nova exportação também consulta o histórico de
IDs para impedir duplicação de um lançamento cujo estado tenha regredido.
Reaplicação de regras usa trava empresa→movimento e revalida proteção humana,
conciliação e lançamentos após a espera, antes de apagar classificação anterior.

Preparar contrato normalizado local de títulos/parcelas/baixas, sem SQL novo
ou ativação no agente; principal, acréscimos, descontos, datas, conta e estorno
devem ser explícitos. Preparar DE-PARA determinístico a partir de exemplos
humanos e plano da empresa, com revisão obrigatória, conflito/insuficiência
explícitos e correção manual preservada. Isso prepara a integração; não prova
IA contratual, semântica Domínio ou regras Q-46. Q-08/Q-09 continuam abertas.
Preparar manifesto revisável da versão e roteiro de publicação/retorno mantendo
hub.0076/0077 e intelligence.0031 aditivas. Não habilitar gate contábil.

Esclarecimento adicional Q-28/Q-46/Q-47: o responsável confirmou que os
relatórios de Razão/títulos/parcelas/baixas solicitados **ainda não existem**;
não continuar pedindo seus caminhos em Downloads. Também confirmou RDP logado.
A primeira leitura da ferramenta mostrava sessão desconectada; após cancelar
menu nativo e elevar a janela, a área de trabalho Windows ficou acessível.
Essa observação supera o impedimento transitório, sem alegar nova autenticação.
Pesquisar os relatórios disponíveis no Domínio em modo somente leitura, no
recorte Fedrizzi já autorizado, sem modificar DSN, encerrar processos de outros
trabalhos, escrever ERP ou transmitir dados. Semântica e exemplos continuam
dependentes da revisão contábil; documento encontrado não equivale a aprovação.

Continuidade Q-28: o responsável concluiu o login diretamente e informou
"só precisa atualizar a domínio". Autoriza usar o atualizador oficial da
instalação existente para prosseguir à consulta, sem baixar de fonte paralela,
alterar DSN ou adquirir serviço/licença. Conferir as telas do atualizador;
preservar backup/retorno antes de conversão de base e não aceitar termos novos,
encerrar processos de terceiros ou ignorar bloqueios por inferência.

Conferência do atualizador: o compartilhamento responde; contém setups
C106A1001/C106A1002, mas não `atualiza.exe` esperado pelo início automático.
Propriedades do C106A1002 identificam Domínio Contábil Setup; Windows confirmou
assinatura digital válida de Thomson Reuters Corporation, carimbo 04/11/2026.
Abrir o assistente desse pacote dentro da atualização já solicitada, para
conferir versão/pré-requisitos e compatibilidade. Não renomear pacote para
contornar o iniciador, mudar caminhos do ERP, forçar conversão ou fechar
processos de outros usuários. Guardas/backup permanecem aplicáveis.

Pré-requisito confirmado pelo assistente: estação em **10.6A-09**, ajuste
C106A1002 exige **10.6A-10** completa. Não forçar o ajuste. Repositório oficial
HTTPS do fornecedor possui `106a10/Atualiza.exe`; preparar essa versão completa
e conferir assinatura antes da aplicação autorizada. O responsável confirmou
expressamente **backup atual concluído e recuperável** ao ser consultado nesta
rodada. Não solicitar novamente essa confirmação. Reusar os caminhos existentes
e observar guardas/termos/processos, sem ampliar a autorização para lançamentos,
baixas ou transmissão ERP.

Pacote completo recebido diretamente do repositório oficial no Windows:
`Atualiza (1).exe`, 1.324.901.936 bytes. Nas propriedades, o Windows confirmou
assinatura digital válida de Thomson Reuters Corporation, carimbo 21/10/2026.
Prosseguir pelo assistente normal dentro da atualização já autorizada e com
backup confirmado; não contornar guardas nem aceitar novos termos por inferência.

O assistente completo oferece componentes adicionais por padrão. Manter o
caminho existente `C:\Contabil` e selecionar apenas Domínio Contábil nesta
atualização; desmarcar drivers/utilitários/Busca NF-e/Backup em Nuvem/LogMeIn
oferecidos pelo pacote. Isso não remove componentes existentes e evita adicionar
acesso remoto ou serviços externos fora da solicitação.

Instalação completa 10.6A-10 e ajuste C106A1002 (Atualização 2, 05/11/2026)
concluídos pelos respectivos assistentes. Na reabertura, Domínio pediu nova
autenticação com senha vazia; solicitar somente login diretamente na janela
preparada, sem credenciais no chat. Não reaproveitar senha desconhecida, testar
senhas ou recriar DSN. Teclado RDP restaurado de Unicode para Scancode antes
da intervenção humana. Relatórios continuam pendentes do acesso à aplicação.

Responsável confirmou novo login concluído. Conferência visual mostra a
aplicação aberta em **10.6A-10 - 02**. Retomar somente leitura de Razão e
títulos no candidato privado já autorizado, confrontando empresa/conta/período
antes de emitir relatório. Não converter o código bruto de conta bancária em
conta do Razão por inferência, nem consolidar outras empresas para a pesquisa.

Conferência visual em Movimentos → Lançamentos de Extrato Bancário identifica
o código bruto do candidato no campo explícito “Conta contábil do banco” e
carrega movimentos ao selecionar janeiro/2026 na mesma empresa. Usar essa
conta para filtrar o Razão do mesmo mês, sem tratar conciliação já marcada no
ERP como aceite CICA nem presumir período fechado. Nenhuma inclusão, exclusão,
alteração de saldo ou gravação deve ser executada nessa tela.

## D-312 — Prévia local de alocação de baixas (05/11/2026)

Origem: continuidade da implementação PC-19 solicitada após o novo login.
Razão emitido na aplicação 10.6A-10 -02 para a empresa/conta/janeiro do
candidato privado; PDF observado em Downloads do Windows. Transferência
para o Mac ainda não confirmada; não declarar extração ou corpus homologado.
Nenhuma nova escrita, baixa ou importação ERP está autorizada.

Preparar um núcleo offline de prévia de alocações explícitas entre movimentos
bancários normalizados e baixas do contrato de títulos D-311. Validar empresa,
conta, período, direção, chaves compostas e capacidade de caixa de ambos os
lados, incluindo agrupamentos, parciais e estornos. Usar o caixa efetivo da
baixa, conservando seus componentes; não usar principal ou vencimento como
pagamento. Sinalizar datas diferentes para revisão. Não escolher associações,
aplicar tolerância, persistir decisões, gerar partidas ou habilitar agente/UI
por essa prévia. Cobertura incompleta permanece explícita. Q-46 continua
exigindo exemplos e aprovação contábil antes da integração real.

Complemento D-312: oferecer execução local por CLI sobre três arquivos JSON
normalizados (títulos, banco e seleções explícitas), com relatório de capacidades,
componentes, diferenças de data e hashes das fontes. Validar tudo antes de
produzir o arquivo, recusar JSON ambíguo e sobrescrita, gravar resultado privado
atômico. Não enviar dados nem usar banco de dados.

Pesquisa somente leitura: “Fechamento atual” contábil mostra 11/2023. Na Escrita
Fiscal da mesma empresa, vigência exibida 09/2021, “Controlar contas a pagar e
receber” desmarcado e período inicial/atual 10/2026. O menu de relatórios não
ofereceu Contas a Pagar e Receber. Parâmetros fechados sem gravação. Isso não
prova ausência histórica absoluta de títulos; impede obtê-los por esse percurso
no recorte atual. Solicitada orientação do responsável em Q-28/Q-46 para outro
recorte somente leitura, sem habilitar controle, criar vigência ou gerar parcelas.

Esclarecimento Q-28/Q-46 nesta continuidade: o responsável autorizou
expressamente “pesquisa de outro recorte somente leitura” na Fedrizzi após
receber os impedimentos do candidato anterior. Permite procurar empresa e
competência alternativas e conferir controle de títulos, fechamento e conta
antes de emissão limitada dos relatórios. Não autoriza habilitar parâmetros,
gerar parcelas/baixas, ampliar transmissão ou importar/escrever ERP. Registrar
identificadores e evidências apenas nos arquivos privados ignorados.

Pesquisa alternativa autorizada: encontrado candidato com menu fiscal de
títulos disponível e fechamento fiscal 09/2026; fechamento contábil exibido
11/2014. Não eleger esse candidato como período contábil fechado/homologado.
Consultar relatórios fiscais limitados a setembro/2026 para conhecer campos
e evidências de títulos/parcelas/baixas, preservando a diferença entre emissão,
vencimento, pagamento e posição. Sem consolidação ou transmissão. A revisão
da contadora e um recorte contábil fechado continuam pendentes para o piloto.

Resultado da pesquisa alternativa: relatório A Pagar por emissão e posição
de setembro emitido e PDF conferido no Windows. A visão tem documento,
vencimento, valores/componentes e situação, mas não apresenta conta bancária,
chave de baixa ou data de pagamento. Não promover documento a chave única,
Valor Pago a caixa efetivo, Outras a tarifa ou Devolução a estorno vinculado
sem exemplos e revisão Q-46. Consultas de recebimentos, pagamentos e situação
parcial delimitadas a setembro retornaram sem dados nos filtros registrados;
isso não prova ausência geral na empresa. Encerrar essas consultas sem alterar
parâmetros/lançamentos, preservar os PDFs no Windows e manter fontes reais,
recorte fechado e integração persistente em aberto. Não repetir pedido de
login, documentos inexistentes, DSN ou backup já confirmado.

## D-313 — Publicação do código preparado na main (05/11/2026)

Origem: autorização expressa do responsável, “pode publicar na main”, após a
entrega local D-312/V-313. Autoriza registrar e enviar ao GitHub o código,
testes, configuração de exemplo e documentação preparados para PC-19, incluindo
as dependências locais D-305–D-312 ainda não presentes na main remota.
O destino conferido é `Mewstacks/CicaContabil`, branch `main`; remoto público
na mesma base b499cd1, sem divergência observada no início desta rodada.

Revisar inventário e bytes antes do commit; adicionar somente arquivos de
fonte/documentação identificados, preservando dados, relatórios, configurações
reais, segredos e artefatos privados fora do Git. Fazer push normal, sem force,
reset, limpeza ou sobrescrita de trabalho concorrente. Não incluir outras
worktrees/branches. O push aciona o CI existente; acompanhar seu resultado e
registrar o SHA exato e os limites, sem transformar evidência histórica em
teste novo. Os workflows conferidos não fazem deploy automático no push main.

Esta autorização supera a restrição anterior de commit/push para esse código.
Publicação no GitHub não autoriza deploy Fly/Cobalchini, instalação no PC,
transmissão financeira, IA paga, escrita/importação ERP ou liberação comercial.
Q-28/Q-46/Q-47, D-73, treinamento e aceite continuam abertos; distinguir código
publicado de aplicação publicada, homologada e liberada.

Execução D-313: commit `4fede1e7f5b1bcfaec8b430a3b0f0d8c4d579b1d`, 84 arquivos,
enviado por push normal para origin/main e confirmado por `ls-remote` com o
mesmo SHA. CI iniciado no run 42067809017 para esse commit. Resultado é
publicação de código no GitHub; nenhum deploy de aplicação ou operação ERP.

CI 42067809017 concluído com sucesso para 4fede1e: agente, pacote Windows e
verificação Python/PostgreSQL/Docker aprovados. Registrar o resultado completo
em V-314 e enviar os registros documentais em commit separado, sem alterar
fontes executáveis ou alegar homologação/implantação por esse sucesso.

## D-314 — Percurso bancário local com anexos CONTAD (05/11/2026)

Origem: após V-315 e a proposta de testar os arquivos já fornecidos, o
responsável autorizou expressamente “pode ser entao, prossiga”. Executar
importação, reenvio, revisão técnica e relatório em banco e mídia novos,
isolados localmente em `.tmp`, preservando originais, desenvolvimento e produção.
Usar settings de teste, bloquear conexões externas e não chamar ERP, IA ou
serviços hospedados. Identificadores, dados, sessões, capturas e relatórios
reais ficam em diretório privado ignorado; Git recebe apenas registros anônimos
ou correção de código/testes sintéticos que se mostre necessária.

OFX será o cenário principal; leitura persistida do PDF será verificada em
cenário separado. São representações dos mesmos 163 movimentos, não 326 itens
independentes. Não importar ambos como se fossem fatos bancários distintos na
mesma conta, nem presumir deduplicação entre formatos sem identidade comum.
Conferir reenvio idêntico/renomeado, sobreposição OFX, escopo de conta/empresa,
retomada, revisão manual preservada, relatório e permissões. A prova sequencial
local não substitui as provas de concorrência PostgreSQL existentes.

Revisão técnica pode salvar os fatos originais, exercitar revisão obsoleta e
ignorar/restaurar somente na cópia isolada, com motivo explícito e trilha.
Não inventar plano de contas, classificação aprovada, Razão, título ou baixa.
Manter gate de exportação contábil desligado e evidenciar pendências reais no
relatório. Sem deploy, transmissão financeira, importação ERP ou aceite CONTAD.

Falha reproduzida no percurso D-314: ignorar manualmente por HTTP deixa
`edited_by` preenchido, mas pode manter `classification_source=none/rule`.
A reaplicação considerava esse movimento elegível e removia o ignorar. Tratar
qualquer movimento com editor humano registrado como protegido na aplicação
e reaplicação, inclusive na revalidação depois da trava. Preservar também o
retorno humano à revisão; não reescrever retrospectivamente a classificação
dos dados. Cobrir estados históricos sem marcador manual e a corrida PostgreSQL
com decisão surgida após a seleção inicial. Não alterar telas ou regras contábeis.

Outro resultado D-314: o aviso de movimentos protegidos na reaplicação é
registrado em `errors`, embora a execução preserve corretamente as escolhas.
O relatório tratava esse aviso como erro de extração e bloqueava o download.
Permitir conferência somente quando a única ocorrência for o aviso conhecido
`protected_movements` da etapa `rules_reapplied`, com contagem consistente;
conservar aviso no relatório. Erro real, mistura, contagem inconsistente,
estado falho/cancelado, arquivo alterado e processamento incompleto continuam
recusados. Cobrir as fronteiras em dados sintéticos antes de repetir o piloto.

Publicação corretiva D-314 segue a autorização de Git D-313 para o código
PC-19 e seus registros: enviar apenas os dois módulos corrigidos, regressões
sintéticas e documentação anônima após a validação local. Preservar o material
real e a evidência em `.tmp`; nenhum deploy ou dado financeiro acompanha o push.

Execução Git D-314: correções/testes/registros publicados por push normal no
commit `700b496fc6b3ae0e521a11ca21ed6b65efbe7246`, 15 arquivos, SHA remoto
conferido. CI 42079806454 iniciado; validação local V-316 concluída, resultado
remoto separado. Nenhum arquivo privado ou imagem de cliente incluído.


## D-315 — Continuidade independente e retorno da revisão (05/11/2026)

Origem: após perguntar sobre AnyDesk, o responsável solicitou prosseguir nos
pontos que não exigem sua interferência. Manter PC-19/etapas 03/09/12 e avançar
em código, verificação local, CI e candidata revisável. A sessão CONTAD ainda
não foi disponibilizada; não iniciar conexão, alterar ERP, instalar/parear,
publicar aplicação, enviar dados ou usar IA paga por essa solicitação.

Corrigir o limite de navegação observado em V-316: todas as respostas de ação
no detalhe do movimento preservam `return_to` usando `detail_redirect`, já
existente. O retorno continua validado pela tag `back_url` contra a rota da
Conciliação, com rejeição de host/caminho arbitrários. Manter empresa, arquivo,
busca, filtros e página da fila na URL ao salvar, ignorar/restaurar ou receber
recusa operacional. Não alterar regras, permissões, fatos contábeis, histórico,
apresentação ou schema. A ausência de origem conserva o retorno padrão.

Aplicar UI/UX Pro Max (navegação previsível/deep link), Web Design Guidelines e
referência de filtros de produto; Watermelon não está exposto nesta sessão.
Conferir a jornada em navegador/Playwright com dados exclusivamente sintéticos,
sem modificar a evidência real V-316. Acompanhar o CI da implementação 700b496
separadamente dos novos testes e preparar nova candidata quando a correção
estiver validada. Publicação de fonte/testes/registros anônimos na main segue
D-313; sem deploy, homologação ou aceite presumidos.

Execução Git D-315: correção/testes/registros enviados por push normal à main
no commit `ed01dd51293be441ef7011763799ae557608cd5f`, 12 arquivos revisados. SHA remoto
idêntico; 809 hashes de fonte do commit iguais ao ZIP da candidata. CI
42082634894 iniciado e ainda em execução na conferência final; não declarar
aprovado por sucesso do push. Registros de confirmação seguem separados.

A sessão RDP já existente foi consultada somente para conferir disponibilidade:
aviso 0x5 informa desconexão porque outra conexão assumiu o PC. Não reconectar
ou interromper essa conexão por inferência; nenhuma janela ERP ou novo relatório
foi acessado nesta observação. AnyDesk da CONTAD não foi disponibilizado.

## D-318 — A espécie da NFS-e importada pertence ao conjunto de dados do Domínio (15/10/2026)

Origem: investigação pedida pelo proprietário a partir de telas do cliente, para entender de onde vem
a espécie das notas de serviço importadas e por que ela não podia ser mudada pela CICA.

- A rota real de importação em uso é o **Importador por conjunto de dados**
  (`Utilitários > Importação > Importador > Importar`), com o conjunto
  `PORTAL NACIONAL TOMADOS - SEM ITENS - SEM ARGUMENTOS V4 (NFS-e Receita Tomados - SI)`, tipo XML.
  Não é a tela `Configuração de Importação > NFS-e Arquivo XML - Padrão Nacional`. O campo Espécie do
  quadro "Dados NFS-e" daquela tela não governa esta rota e não deve ser usado como explicação.
- A espécie é gravada pelo próprio conjunto, na coluna `codi_esp` da tabela `efentradas`
  (identificação "Grava Nota"), com `origem_coluna = F` e `valor_fixo = 1`. Valor fixo: não vem do
  XML, não vem de argumento e não vem de tela.
- O padrão nacional da NFS-e não possui campo de espécie. A CICA continua escrevendo **apenas**
  `infNFSe/valores/acum` no XML derivado (D-274) e **não** passa a escrever espécie, modelo ou série.
  Nenhum campo novo entra no contrato de exportação por causa desta investigação.
- O valor correto informado pelo responsável para a base atual é **39**. Esse número é **por cliente
  e por base**: não pode ser embutido como padrão em código, leiaute, documentação ou conjunto gerado
  pela CICA, nem presumido para outro escritório.
- Alterar a espécie é mudança no conjunto de dados, que é artefato do Domínio. O caminho suportado é
  chamado ao suporte, que cria e versiona esses conjuntos; a edição local do arquivo exportado é
  decisão do escritório, assumida por ele, e não vira procedimento da CICA. A CICA não gera, não
  versiona e não distribui conjunto de dados.
- Qualquer conjunto novo precisa continuar lendo `infNFSe/valores/acum`. Perder essa leitura quebra a
  chegada do acumulador classificado ao Domínio.

## D-319 — Carteira de origem backup: ativação manual e corte pelo backup novo (05/11/2026)

Origem: pedido explícito do proprietário nesta conversa, com a escolha de conflito respondida por
ele ("backup prevalece"). Escritórios cuja carteira vem de backup do Domínio (`DataSource` de tipo
`dominio_web_backup` com capacidade `companies`) não têm agente sincronizando sozinho, então o
cadastro fica parado entre uma importação e outra. Até aqui não existia nenhuma ação de ativar ou
desativar empresa na interface: `ClientCompany.active` só era escrito pela importação e pelo
`full_snapshot` do agente, que nunca roda com `True` nos produtores atuais.

Fica autorizado:

- Uma página própria de Configurações, listando código do Domínio, nome, CNPJ e situação de cada
  empresa da carteira, com ativar e desativar por empresa. Ela aparece somente para escritório de
  origem backup, sem conector Domínio ativo e sem vínculo de controle central — nos demais a origem
  continua mandando e a página não é oferecida.
- Mutação pela mesma fronteira das demais alterações de cadastro (`_can_manage_companies`): dono
  ou administrador do escritório, ou sessão de suporte autorizada a alterar e com a carteira
  inteira; nunca na demonstração, que é compartilhada. Cada empresa alterada gera evento de
  auditoria. Quem enxerga só parte da carteira não vê nem altera empresa fora dela.
- No encerramento de um backup novo sem erro de linha, as empresas daquela fonte que não vieram na
  fotografia passam a inativas. É desativação, não exclusão: histórico de NFS-e, DTE, guias e
  acumuladores continua acessível pela ficha, conforme D-207 e D-209.

Limites: o backup prevalece. A desativação manual vale até a próxima importação, que reescreve
`active` a partir de `stat_emp` — é a escolha do proprietário e precisa estar dita na tela, porque
uma empresa ainda marcada `A` no Domínio volta a ativa sozinha. O corte por ausência não roda em
lote com erro de linha nem em lote interrompido, para que uma importação parcial não esvazie a
carteira. Esta decisão não cria exclusão de empresa, não altera o caminho do agente
(`WHERE stat_emp = 'A'`, sem desativar ausências), não mexe no contrato `companies.v1` da
Rentabilidade, não autoriza custo, deploy, envio de mensagem ou acesso externo, e não declara
homologação de nada.

## D-320 — Executar implantação do conciliador CONTAD e prévia privada (06/11/2026)

Origem: plano discutido e aprovado pelo responsável nesta conversa, seguido de
“Sim, implemente o plano” e “Inicie o desenvolvimento”. Executar PC-19 nas
etapas 03/09/12, preservando alterações locais e os gates ainda abertos.
Sessão AnyDesk acompanhada: avisar o responsável antes de entrar; ele abrirá
a sessão. Recorte e autorização de leitura/envio CONTAD serão registrados em
Q-28 antes do pareamento; a autorização Fedrizzi não os substitui.

Escolhas explícitas: partir da candidata validada, manter o app existente no
Fly da Mewstack e preparar **somente o arquivo**, sem importação efetiva no
Domínio nesta entrega. A saída será uma prévia privada dentro do CICA,
identificada como não homologada. Manter Q-47 e
RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED=false; não registrar exportação,
importação ou escrituração por gerar uma prévia. Publicação da candidata
revisada faz parte do plano aprovado, com backup/retorno e verificações antes;
custos e IA real continuam sujeitos às regras específicas Q-08/Q-09.

Implementação da prévia: registro próprio imutável, separado de
AccountingExport, com fotografia de lançamentos/partidas, recorte, versão,
autor, arquivo e SHA-256. Habilitação por lista explícita de UUIDs de
escritórios, vazia por padrão; não adivinhar o tenant CONTAD nem habilitar
globalmente. Criação por POST/CSRF e papel operacional existente; consulta e
download limitados à carteira autorizada e arquivo íntegro. Não exportar
fonte de Razão, fato já conciliado/exportado, lançamento inválido ou obsoleto;
geração não muda estados/aprovações. Preservar fotografias e sinalizar
desatualização quando fatos/decisões mudarem; exigir nova geração para o
resultado atual. Os adaptadores do Domínio dependem de campos/chaves e
exemplos revisados Q-28/Q-46, sem SQL novo por inferência.

Acesso Fly reconferido: conta pedro@mewstack.com.br, app cica-contabil na
organização mewstack-629; web/worker ativos. Supera o impedimento de acesso
descrito no planejamento anterior, sem alegar deploy novo. Colisão de IDs
D-316/D-317 e V-318/V-319 entre documentos locais e main remota apresentada
ao responsável; preservar ambos os históricos enquanto aguarda escolha de
renumeração. D-320 fica reservado a esta autorização e não reutiliza os IDs.

Continuidade D-320 (06/11/2026): responsável confirmou que entrou no AnyDesk
da cliente e que o Domínio está aberto, autorizando prosseguir na sessão
acompanhada. Iniciar levantamento somente leitura da instalação e das fontes;
registrar recorte/autorização de envio antes de parear, sem importação ERP.
Para a colisão documental, escolheu **manter IDs locais e renumerar os
registros remotos**, preservando integralmente ambos os históricos. Reservar
D-318/D-319 e V-320/V-321 aos dois assuntos remotos; D-320 permanece nesta
implantação, cuja evidência própria será V-322. Atualizar referências remotas
por origem do trecho, sem substituir números globalmente nos registros locais.

Continuidade operacional D-320: a leitura nativa da janela AnyDesk expirou
repetidamente, inclusive após novo primeiro plano, nova instância solicitada
pelo responsável e reinício do controle. A imagem fornecida confirma Domínio
Escrita Fiscal aberto, não uma consulta executada pelo agente. O responsável
priorizou testar no PC da cliente nesta manhã e escolheu **executar os testes
com instruções**, em vez de AppleScript/System Events. Não executar esse
controle alternativo. Primeiro diagnóstico guiado somente leitura: arquitetura,
presença/estado do serviço, driver SQL Anywhere x64 e contagem de DSNs de
sistema x64; sem nomes, credenciais ou conteúdo financeiro no resultado.
Resultados humanos serão identificados como informados, sem alegar verificação
automatizada ou homologação por essa informação.

Diagnóstico guiado informado pelo responsável no PC CONTAD: Windows x64 e
PowerShell x64; CicaAgent ausente; drivers SQL Anywhere 16 e 17 x64 presentes;
zero DSNs de sistema x64, três DSNs de usuário x64 e um DSN de sistema x86.
Conferir o driver/configuração da conexão existente antes de criar o DSN de
sistema x64. Não copiar segredos do registro, testar senhas ou alterar o DSN
original. Credencial de integração somente leitura será preenchida diretamente
pelo responsável no PC; disponibilidade ainda não confirmada. Esses resultados
são relatos do operador, não teste ODBC ou instalação concluídos.

Complemento informado no PC CONTAD: o DSN de sistema x86 existente usa
**SQL Anywhere 17**. Usar a versão 17 x64 já instalada para preparar a conexão
do serviço, preservando o DSN original. A resposta não confirmou ainda a
disponibilidade da credencial somente leitura; não presumir esse acesso.

O responsável confirmou em seguida que **não possui a credencial de
integração somente leitura**. Teste ODBC e configuração dessa conexão aguardam
o técnico/administrador Domínio. Prosseguir com instalação e diagnóstico local
do MSI 1.0.3 conferido, mantendo o serviço sem configuração/pareamento/envio;
não tentar senha, extrair segredo de DSN existente ou usar usuário da aplicação
como substituto por inferência.

Transferência assistida: cópia do MSI criada em Downloads/CICA-Agent-1.0.3
no Mac após reconferir SHA-256. O operador transferiu a pasta inteira para
Downloads no Windows e informou Get-FileHash com o SHA-256 **idêntico** ao
pacote 1.0.3 de V-311. A conferência do operador comprova os bytes recebidos;
instalação e estado do serviço ainda aguardam resultado próprio.

Instalação guiada no PC CONTAD: após conferir o hash, o responsável executou
o MSI e informou `Get-Service CicaAgent` com **Running / Automatic**. Registrar
como execução informada pelo operador; conferir versão/estado seguro a seguir.
Não houve configuração ODBC, código de pareamento, salvamento, leitura ou envio
comprovados. Ausência da credencial somente leitura permanece no próximo passo.

Conferência guiada final da instalação: ProductVersion informado
`1.0.3+1bf854958cecae319abc050241f7b83753903265`, correspondente à candidata
Windows validada. A pasta protegida negou leitura no PowerShell sem elevação;
não alterar ACL. No PowerShell administrativo, o operador informou
`state=awaiting_configuration`. Serviço instalado e em espera; não é conexão
ODBC, pareamento, sincronização ou homologação do conciliador.

Preflight hospedado somente leitura: ambos os aliases de produção respondem
no Neon, com hub.0075/intelligence.0030 aplicadas; exportação Domínio false,
mTLS false e prévia ainda sem lista habilitada. Busca de nome CONTAD não
encontrou escritório; não criar ou atribuir outro escritório por inferência.
A API de storage não informou versionamento habilitado e o ambiente não tem
credencial da API Neon. Isso não prova ausência de backup externo, mas não
confirma recuperação de banco/objetos para o deploy. Preparar candidata com
hub.0076/0077/0078 e intelligence.0031 preservadas; não publicar sem cumprir
o gate de backup/retorno definido acima.

O responsável não sabe se há recuperação configurada nem qual o cadastro
CONTAD existente; considera que talvez seja necessário criar. Consultar
metadados dos escritórios antes de propor novo cadastro. A resposta não
define identidade, acesso de usuário ou condição comercial/teste parceiro,
nem dispensa backup/retorno. Nenhum desses valores será inventado.

Inventário somente leitura encontrou Bianchi & Rizzotto e Cobalchini
Contabilidade como escritórios ativos não demo. O responsável confirmou
que CONTAD é **outro escritório e precisa de cadastro próprio**; não associar
seus dados a nenhum dos dois existentes. Identidade do acesso e ativação
continuam a exigir os dados reais; não atribuir condição de parceiro interno
ou valor comercial por inferência. Bancos de produção medidos em PostgreSQL
18.6, 589.570.048 e 8.175.616 bytes; storage Tigris. A regressão local PostgreSQL
17 não constitui prova de restauração do PostgreSQL 18/Neon/Tigris.

Identidade do novo escritório confirmada pelo responsável: CONTAD, com e-mail
de login fornecido nesta conversa e guardado em evidência privada, fora do Git.
Provisionar o cadastro próprio pelo estado **activation_pending**, com auditoria,
sem ativação comercial, contrato novo, módulo habilitado, associação a outro
escritório, convite enviado ou senha criada. Preparar o vínculo de acesso, sem
alegar que já pode entrar. A lista da prévia permanece vazia até a liberação
concreta; pareamento continua condicionado a recorte/autorização e backend.

Execução do cadastro próprio: CONTAD provisionado com auditoria no UUID
ae13d06f-6461-43a8-a9cc-3e0e0eafde50, slug contad, activation_pending,
zero membros; sem demo/parceiro interno, contrato, convite ou senha criados.
E-mail indicado não entrou nos arquivos versionados. Painel Neon aberto para
verificar recuperação, mas solicitou login; autenticação direta solicitada ao
responsável, sem credencial no chat. Não há acesso autenticado Neon confirmado
ainda. Regressão final local 1.715 testes/163 subtestes aprovada após correção
de auditoria; um skip opcional. V-322 conserva contexto e limites.

Publicação da fonte D-320: incluir a implementação/testes, sua continuidade
canônica e a renumeração dos registros remotos. As entregas documentais locais
anteriores D-316/V-318 (comparação) e D-317/V-319 (parada do legado), seus
apêndices e arquivo próprio permanecem preservados no workspace; não incluí-las
na publicação funcional por inferência. Manter o índice separado desse conteúdo
preexistente, sem reescrever ou descartar o arquivo de trabalho. Como produção
foi identificada em PostgreSQL 18.6, conferir adicionalmente migrações e testes
focados em PostgreSQL 18 descartável antes do eventual deploy, sem dados reais.

Conferência final da candidata: 42 testes focados/migrações aprovados também
em PostgreSQL 18.6 sintético, mesma versão observada no Neon; 21,62 s. Não
executou restore de produção. Código da candidata final com 816 hashes iguais
ao ZIP/workspace, SHA-256 ced90f343ddbb08c82c7950cc7125a68d712e086708d9f317f06c203834a3eaa.

Fonte D-320 publicada por push normal à main em
f86ae4d7630bc707be2f407a1a9c12c5582110b9, SHA remoto idêntico e 816 hashes
da candidata iguais aos blobs do commit. CI 42231907397 em execução; agente
e build/manifesto Windows aprovados na observação, verify ainda pendente.
As entregas documentais locais anteriores continuam fora do commit, preservadas.

Acesso Neon resolvido durante a continuidade: o responsável autenticou pelo
painel. A organização pessoal estava vazia; seletor já disponibilizava
germano@mewstack.com.br e projeto CICA raspy-river-46466568, branch production
br-odd-tree-b6vhgfnv. Ambos os aliases hospedados conferidos no mesmo endpoint
do painel, LSN 0/BE42A1F8 em 06/11/2026 14:16:49 UTC. Backup & Restore informa
**janela de seis horas**, sem snapshots ou agenda. Essa janela existente não
define RPO/retencão de negócio nem prova restore. Não criou snapshot, branch,
chave API, agenda ou alteração de retenção; storage ainda requer recuperação
confirmada. Qualquer nova retenção/backup com custo exige aprovação específica.

Preparação de recuperação D-320: Tigris cica-contabil-media é privado, tem
53 objetos/2.901.052 bytes e snapshots desativados. Inventário/rotina de cópia
privada e pareamento com snapshot Neon preparados, quatro verificações
sintéticas, sem executar backup real. Proposta pontual de sete dias, snapshot
Neon/cópia Tigris e ensaio de restauração isolado, estimativa abaixo de
US$ 0,10 e teto US$ 1,00, detalhada no roteiro de release. **Custo ainda não
aprovado**; não criar snapshot/cópias/branch/expiração antes da resposta.

**Aprovação específica recebida em 06/11/2026:** responsável respondeu
“Sim, autorizo até US$ 1,00” para snapshot Neon, cópia privada Tigris, retenção
de sete dias e ensaio de restauração antes do deploy D-320. Executar somente
esse escopo pontual e respeitar o teto; não criar agenda recorrente ou alterar
retenção global por inferência. Preservar produção no ensaio, registrar IDs,
expiração, contagens/hashes e resultado antes de publicar a aplicação.

Snapshot manual criado no painel às 14:29:44 UTC, ainda com expiração never;
console não oferece edição desse campo. Ensaio Multi-step restore criou
br-soft-pond-b6b07dau, endpoint ep-broad-recipe-b6bd0c92 (0,25–1 CU), mantendo
production/br-odd-tree-b6vhgfnv e conexões originais. Tigris: 53 cópias verificadas,
2.901.052 bytes, prefixo privado 59523a7687024acabb6638ca8cc7f0b7 e expiração
de sete dias confirmada; manifesto preparado a1f5ec6feecd17559b637c72be1885b14b0a487ccfaeecdbe1cacf17901fb213.
Retenção do snapshot ainda precisa ajuste antes de alegar backup finalizado.

Responsável autorizou explicitamente credencial temporária **somente para o
projeto CICA**, para fixar expiração e concluir o ensaio, com revogação ao
terminar. Usar CLI oficial Neon com profile novo e chave project-scoped;
não criar chave de organização/conta nem imprimir segredo. Autorização direta
no navegador; configuração privada fora do Git, sem instalar MCP/skills ou
trocar configuração existente. Teto de US$ 1,00 permanece.

A implementação do CLI 8.23.3 foi inspecionada antes do login: --mint inicia
OAuth com escopos de conta antes de restringir a chave. Para respeitar a
autorização somente CICA, criar a chave project-scoped diretamente no painel
autenticado e importar no profile privado por stdin, sem iniciar OAuth amplo.
Não imprimir token nem mudar permissões/credenciais de outros projetos.

Gate pontual de backup/retorno cumprido antes do deploy: snapshot
snap-hidden-tree-b6xt5ssj, 648.298.496 bytes, expira em 13/11/2026 14:29:44 UTC.
Branch isolada br-soft-pond-b6b07dau restaurada e conferida a partir do Fly,
sem dump/dados financeiros no Mac nem troca de conexão da aplicação. Ambos os
aliases PostgreSQL 18.6: esquemas/migrações e contagens de todas as tabelas iguais
à produção na observação; hashes de sete tabelas críticas do default e quatro
do knowledge iguais. Cinquenta e três referências de arquivo cobertas; 53
objetos/2.901.052 bytes recuperados em temporário no Fly e hashes iguais;
temporário limpo. Manifesto Tigris final pareado com o snapshot, SHA-256
9cb388132280969bf4e43ef03cd8c60a82684f3a8782b1df613c5577d9453443;
inventário original permaneceu igual. Compute do ensaio suspenso/idle às
14:43 UTC, em menos de 30 minutos; branch também expira em 13/11 14:29:44 UTC.
Chave project-scoped criada diretamente no painel, usada por profile privado,
revogada ao terminar; HTTP 401 verificado e cópias locais do token removidas.
Retenção global de seis horas/agenda e produção preservadas. Isso cumpre o
backup pontual D-320, sem concluir recuperação recorrente/RPO ou D-73.

Publicar agora a candidata exata de f86ae4d/CI 42231907397 aprovado, usando
contexto extraído do ZIP com 816 hashes conferidos e build Docker local,
sem novo builder/recurso recorrente. Configuração vigente e candidata têm
as mesmas variáveis; acrescentar somente a prévia privada no UUID CONTAD
ae13d06f-6461-43a8-a9cc-3e0e0eafde50 e explicitar exportação Domínio false.
Esta lista não ativa contrato/módulo/usuário do escritório, ainda pendentes.
Preservar reserva parada 287e35db920e48, tamanho das máquinas e endpoints
Neon originais; aplicar migrações aditivas de ambos os aliases. Em falha,
retornar imagem da release 71 preservando migrações/arquivos/evidências;
não restaurar snapshot sobre produção por inferência.

Deploy D-320 concluído em 06/11/2026, release Fly **72**, criada às 14:49:20 UTC;
imagem registry.fly.io/cica-contabil:contad-f86ae4d-20261106, digest
sha256:3f5f91ec176db121531a1e26176a1054f8001088fb273eea88e99b11ede832eb.
Release command e canário passaram; web/worker originais ativos com a mesma
imagem/512 MB e reserva parada com a imagem anterior preservada. Os 645 arquivos
de fonte presentes no runtime foram conferidos em ambas as máquinas contra o
ZIP aprovado, hash agregado f00613a9dca60643a99f49efb16e8c784ecb78a18115c028141190ae88974f8d.
Ambos os aliases no endpoint Neon original com hub.0078/intelligence.0031;
health nos dois domínios 200, banco/cache ok, worker ready e check Fly passing.
Requisição de agente com identidade/assinatura inválidas recusada 401;
prévia e download anônimos redirecionaram ao login, sem arquivo exposto.
Lista da prévia contém só CONTAD, exportação permanece false, mTLS false.
CONTAD continua activation_pending/zero membros/zero prévias; não afirmar login,
pareamento, envio, leitura do Razão/títulos ou importação/homologação por esse deploy.

Publicar a continuidade operacional D-320 em commit só documental, preservando
fora do índice os registros locais preexistentes D-316/D-317 e V-318/V-319.
Código implantado continua f86ae4d/CI aprovado; não repetir toda a regressão por
atualização documental. Conferir diff/escopo/hashes e marcar o commit documental
com skip ci, sem alterar workflows ou dispensar checks de uma mudança funcional.

Continuidade D-320 (06/11/2026): responsável informou agora que possui a
credencial EXTERNO do Domínio da cliente. Supera a indisponibilidade antes
relatada; não pedir novamente criação de usuário nem solicitar senha no chat.
Retomar configuração guiada do novo DSN de Sistema x64/SQL Anywhere 17,
preservando o DSN x86 e demais conexões. Disponibilidade informada não prova
credencial válida, tipo Externo/permissões, conexão ou acesso LocalSystem.
Senha digitada somente no PC; nenhum salvamento/pareamento/envio antes do
recorte/autorização Q-28 e acesso/ativação. Primeiro passo: abrir administrador
ODBC x64 e a configuração do driver 17; não adivinhar servidor/banco/porta.

Continuidade guiada D-320: operador informou que abriu a tela de configuração
do SQL Anywhere 17. Preparar o novo DSN como CICA_CONTAD, sem sobrescrever
conexão preexistente. Antes de preencher servidor/banco/host ou testar, conferir
os parâmetros reais na conexão x86 já usada pelo Domínio, apenas pela interface
ODBC e fechando com Cancelar. Ler somente nomes técnicos necessários, sem
copiar/extrair credenciais ou enviar conexão completa. Abertura da tela não
comprova DSN salvo ou conexão válida; salvar configuração do agente e parear
ainda dependem do recorte/autorização e acesso/ativação registrados em Q-28.

Continuidade guiada D-320: operador confirmou Server name **srvContabil**
na conexão existente da cliente. Usar esse valor real no novo DSN CICA_CONTAD;
selecionar autenticação Database e conexão a banco já em execução, com usuário
EXTERNO e senha digitada localmente. Executar apenas Testar conexão e aguardar
resultado antes de gravar o DSN; não inventar host, porta ou nome do banco nem
alterar a conexão original. Este teste não pareia o agente nem envia dados ao CICA.

Continuidade D-320: operador informou **successful** no Test Connection do
novo DSN x64 CICA_CONTAD/SQL Anywhere 17, servidor srvContabil e credencial
EXTERNO preenchida localmente. Registrar sucesso informado do ODBC interativo;
não equivale a prova de permissões somente leitura, configurador, serviço
LocalSystem, pareamento ou sincronização. Prosseguir salvando somente o novo
DSN, retirando a senha antes de OK; no configurador usar credenciais explícitas,
desmarcando Usar autenticação já configurada no DSN. Não alterar o DSN original.
Teste do configurador fica restrito à consulta fixa local de diagnóstico, sem
salvar configuração do agente ou Conectar à CICA antes de recorte/ativação Q-28.

Continuidade D-320: imagem fornecida pelo operador mostra Domínio Local,
CICA_CONTAD no seletor de DSNs e SQL Anywhere 17; o seletor enumera apenas
DSNs de sistema x64. A imagem ainda mostrava autenticação pelo DSN marcada,
orientada troca para EXTERNO explícito. Operador agora informou clicar em
Testar sem perceber resultado. Não classificar como sucesso ou falha ODBC.
Código do configurador da versão instalada conferido (sem diff desse arquivo
entre 1bf8549 e HEAD): resultado/erro aparece no label abaixo dos botões, sem
modal, com Aguarde durante execução. Orientar rolagem ao fim/maximização e
leitura dessa mensagem antes de repetir teste, trocar parâmetros ou parear.

Continuidade D-320: operador informou **conexão confirmada** no configurador
instalado, depois da orientação de EXTERNO explícito. Registrar como sucesso
informado de conexão/consulta mínima local; não equivale ao serviço LocalSystem,
pareamento, transmissão ou homologação. Não repetir teste já aprovado sem motivo.
Próximo passo é preparar pareamento restrito: confirmar situação do CONTAD no
backend por consulta somente leitura e obter o recorte já exigido por Q-28
(empresa/código Domínio, conta e competência anterior completa; extratos/IDs
revisados antes de emitir manifesto). Endereço HTTPS do app já conhecido:
https://cicacontabil.com.br/. Não emitir código genérico sem recorte nem ativar
contrato/módulo/usuário por inferência; acesso/ativação e provas reais seguem abertos.

Recorte Q-28/D-320 informado pelo responsável: **URIA COMPONENTES E ACESSORIOS
PARA MODA LTDA**, competência **09/2026**; arquivos correspondentes já estão em
Downloads. Localizar e analisar somente esses arquivos para conferir conta e
código Domínio, preservando originais; nenhuma senha ou dado financeiro em logs
versionados. Identidade bancária/código/IDs ainda dependem das fontes e revisão;
não adivinhar ou emitir manifesto de carteira inteira. Essa consulta local não
equivale a sincronização/ativação ou importação no ERP. Usar evidências locais
anteriores se os hashes dos originais ainda coincidirem, evitando retrabalho.

Continuidade Q-28/D-320: diferença URIA/SURIA apresentada ao responsável, que
confirmou tratar-se de **SURIA COMPONENTES E ACESSORIOS PARA MODA LTDA**, como
consta no extrato. Competência 09/2026 mantida. Responsável não sabe o código
Domínio: orientar consulta somente leitura em Controle > Empresas, localizar
SURIA e informar Código, sem editar/gravar cadastro. Não reabrir identidade,
período ou pedir novamente arquivos bancários já disponíveis.
PDF/OFX Sicredi de Downloads têm os mesmos hashes do piloto V-316 e período
09/2026; a conta no OFX é um identificador longo terminado nos dígitos da conta
do PDF, mas essa relação ainda exige conferência. Aproveitar os 42 checks/163
eventos históricos sem
alegar nova execução. Conta completa e manifesto de preparação ficam privados
fora do Git; não usar FITIDs bancários como IDs internos do Domínio. O plano de
contas inspecionado pertence a outra empresa e foi excluído deste recorte,
sem presumir contas/DE-PARA compartilhados. Código Domínio, referência real da
conta e IDs revisados ainda faltam ao manifesto; nenhum código genérico emitido.
Preflight Fly somente leitura confirmou CONTAD activation_pending, zero membros,
empresas, contas financeiras, contratos, enrollments e agentes. Não houve
ativação, upload financeiro, cadastro de empresa/conta ou alteração de produção.

Continuidade Q-28/D-320: responsável informou **212** como código Domínio da
SURIA COMPONENTES E ACESSORIOS PARA MODA LTDA; competência 09/2026 mantida.
Registrar como identificação informada pelo operador, sem alegar consulta SQL
ou vínculo remoto já executado. Não pedir novamente esse código. Próxima
consulta guiada: na empresa 212, abrir Movimentos > Lançamentos de Extrato
Bancário e consultar Conta contábil do Banco para 09/2026, apenas identificando
a conta Sicredi existente. Não incluir/gravar/importar lançamentos. Referência
real da conta, relação com o extrato bancário e IDs internos revisados continuam
pendentes; não emitir código de pareamento genérico nem deduzir esses campos
do código da empresa ou dos FITIDs do OFX.

Continuidade guiada Q-28/D-320: primeira captura mostrava Escrita Fiscal;
operador em seguida abriu Lançamentos de Extrato Bancário, conforme nova
captura. Campo da conta vazio e competência 11/2026: grade vazia nesse estado
não comprova ausência de extrato em 09/2026. Prosseguir somente com consulta,
mantendo SURIA/212, mudando filtro para 09/2026 e usando F2 no campo da conta
para localizar as contas Sicredi existentes. Se houver mais de uma, revisar a
lista antes de escolher; não presumir vínculo nem cadastrar conta/lançamento.
Atalho de consulta conferido na documentação oficial Domínio, solução 6705.

Continuidade Q-28/D-320: nova captura do operador mostra BANCO SICREDI e
competência 09/2026 em Lançamentos de Extrato Bancário, com movimentos de origem
Importação e linhas visíveis marcadas como conciliadas. Registrar somente esse
trecho observado; não declarar toda a competência conciliada nem ausência de
pendências. Código da conta destacado na imagem não foi lido com segurança:
pedir transcrição apenas desse número antes de fixar a referência. Nome da
conta não prova relação com o identificador bancário dos arquivos nem fornece
IDs internos de extrato. Não gravar/reimportar/desconciliar para testar o agente;
nenhum pareamento genérico ou transmissão liberados por essa captura.

Continuidade Q-28/D-320: operador transcreveu **8** como código da conta
contábil BANCO SICREDI da consulta de SURIA/212, competência 09/2026. Registrar
como ledger_code do recorte; não pedir novamente nem usar esse código como
agência/conta bancária ou I_LANCAMENTO. A referência financeira/relação com os
arquivos e os IDs internos revisados seguem pendentes, assim como acesso/ativação.
Próxima consulta guiada do levantamento já autorizado: emitir localmente o
Razão somente da conta 8, de 01/09/2026 a 30/09/2026, sem consolidar outras
empresas, para obter a fonte contábil independente. Caminho e filtro conferidos
na documentação oficial Domínio (1817/3132). Emitir relatório não altera
lançamentos; não importar, regravar, desconciliar ou habilitar SQL novo. Não
declarar o Razão obtido antes do arquivo/resultado real nem parear sem manifesto.

Continuidade Q-28/D-320: responsável informou ter transferido o Razão solicitado
para Downloads do Mac. Localizar o PDF e conferir titular, conta 8 e período
01–30/09/2026 antes de utilizá-lo. Se corresponder ao recorte, preservar original,
registrar hash e conferir páginas, integridade dos saldos e cobertura local
contra as fontes bancárias já autorizadas. Evidência financeira e derivados
ficam privados/ignorados; não inferir partidas ausentes, conciliação, vínculo
de extrato, IDs internos ou ativação. Nenhuma autorização adicional de SQL,
escrita ERP, envio remoto, IA paga ou homologação decorre dessa transferência.

Resultado Q-28/D-320: Razão.pdf recebido em Downloads, quatro páginas da SURIA,
conta 8 — BANCO SICREDI, 01–30/09/2026, SHA-256
af1ca6b11f558765531bb8009538ce585bbe781629732b281d355427273889d9.
Inspeção visual das quatro páginas e extração numérica local conferiram 163
linhas, números de lançamento distintos, todos os saldos sucessivos e os totais
impressos. As 163 datas/valores assinados formam o mesmo multiconjunto das fontes
bancárias V-316, cujos hashes foram reconferidos. Duas chaves data/valor têm
repetição (quatro linhas); não transformar igualdade em alocação automática.
Relatório de uma conta não fornece todas as partidas; seis linhas não mostram
contrapartida nesse campo. Não preencher contas faltantes nem usar numeração
do Razão como ID de extrato. Não soma 326 eventos nem cumpre os 200 de D-73.

Conflito real Q-28 no mesmo recorte: saldos inicial/final do PDF bancário e
do Razão coincidem, mas divergem dos saldos visíveis na captura da janela de
extrato do Domínio. Valores e diagnóstico ficam privados, fora do Git. Confirmar
a empresa ativa dessa janela e origem da diferença antes de fechar recorte ou
parear; não corrigir saldos nem invalidar a escrituração por inferência.
Associação da conta bancária segue para confirmação humana, IDs revisados e
acesso/ativação continuam pendentes. Nenhum arquivo financeiro enviado, SQL
novo, configuração de serviço ou alteração ERP nesta conferência local.

Continuidade Q-28/D-320: responsável confirmou que a janela de Lançamentos de
Extrato Bancário também estava na **SURIA — 212**. Não repetir a pergunta de
empresa ativa. Informou **não saber confirmar** o vínculo da conta contábil 8
com a conta bancária dos arquivos; manter vínculo pendente, sem concluir que
seja outra conta. A diferença de saldos na mesma empresa permanece real e sem
causa comprovada. Prosseguir com pesquisa documental e consulta guiada somente
leitura dos parâmetros existentes, sem corrigir saldo, reimportar ou parear.
Não transformar essa resposta em autorização de SQL novo, envio ou ativação.

Preparação Q-28/D-320 após as respostas: documentação oficial (1878/238) descreve
saldo informado na rotina e escolha explícita da conta contábil na importação;
não explica a causa da diferença observada nem comprova a associação bancária.
Preparar, sem executar, diagnóstico pontual revisável no PowerShell x64:
metadados de somente duas tabelas já observadas na Fedrizzi e SELECT fixo do
cabeçalho por empresa 212/conta contábil 8/09-2026; no máximo 20 candidatos,
com contagem de itens por cada ID retornado, sempre no mesmo mês/empresa.
Não ler históricos, valores, outras empresas ou toda a carteira; senha EXTERNO
digitada apenas no PC, sem arquivo/registro/rede adicional. A consulta é proposta
para esta instalação CONTAD, ainda não validada nela; não presumir o schema.
Nenhum ID retornado será automaticamente homologado ou usado em pareamento.
D-309 veda SQL novo por inferência: obter autorização específica antes da
execução dessa sonda, preservando o bloqueio de escrita/pareamento e divergência.

**Autorização específica recebida em Q-28/D-320:** responsável respondeu
“Sim, autorizo essa consulta” para a sonda preparada de metadados, identificadores
de extrato e contagens, somente leitura no PC da cliente, limitada à empresa
212/conta contábil 8/setembro-2026, sem históricos/valores, alterações ERP ou
envio ao CICA. Prosseguir com a execução manual guiada desse roteiro; não
repetir autorização. Conferir nomes exatos dos objetos nos metadados antes
dos dois SELECTs fixos e parâmetros; saída contém apenas candidatos para revisão.
A aprovação não resolve vínculo bancário/diferença de saldos nem autoriza
consulta do Razão por SQL, ampliação de recorte, pareamento ou transmissão.

Continuidade operacional Q-28/D-320: operador recebeu arquivo não encontrado
no Get-FileHash de Downloads do Windows; a execução do roteiro não começou.
Isso não comprova ausência em outras pastas nem falha ODBC/schema. Original do
Mac reconferido com o mesmo SHA-256 aprovado. Orientar localização somente do
roteiro nas subpastas de Downloads do Windows, verificando o hash antes de
executá-lo; se não localizado, transferir o arquivo do Mac. Preservar autorização
e escopo existentes, sem pedir nova senha/autorização ou mudar o script.

Resultado informado Q-28/D-320: operador executou o roteiro autorizado e
retornou JSON com um cabeçalho candidato, empresa 212/conta contábil 8,
competência 01/09/2026 e 163 itens no período. Identificador do cabeçalho e
retorno integral guardados somente na preparação privada. Dados conferem com
o recorte proposto e contagem dos PDFs; não pedir novamente esse identificador
nem repetir a sonda sem motivo. O sucesso é informado pelo operador, não
observação automatizada ou prova de LocalSystem. Não houve senha recebida.
Revisão técnica do candidato é consistente, mas scope_reviewed permanece false:
contadora ainda precisa confirmar a correspondência bancária e esclarecer a
divergência de saldos. Não promover candidato a manifesto aprovado, configurar
serviço, parear, enviar dados ou ativar acesso/contrato por esse retorno.

Continuidade Q-28/D-320: responsável perguntou se pode verificar vínculo e
diferença no próprio Domínio. Pode levantar evidências por consulta da conta 8
existente em Arquivos > Contas Contábeis (solução oficial 43), sem editar/gravar.
Não prometer agência/conta nesse cadastro: a documentação confirma identificação
contábil, não vínculo bancário obrigatório. Se houver identificação bancária
explícita, confrontá-la; somente descrição BANCO SICREDI não fecha o vínculo.
A solução 1878 trata o saldo inicial como valor informado na rotina de extrato,
sem demonstrar nesta instalação sua origem ou espelhamento automático do Razão.
Não inventar tela de log/auditoria nem concluir causa pelo campo. Se o histórico
do preenchimento/importação não estiver disponível, origem ainda exige quem
operou ou responsável contábil. Prosseguir com consulta guiada do cadastro,
preservando revisão final, recorte/pareamento e proibição de ajuste/importação.

Continuidade Q-28/D-320: captura recebida do cadastro mostra código 8,
BANCO SICREDI, tipo Analítica e situação Ativa, com classificação contábil
compatível com o Razão. Não aparecem agência ou número da conta bancária na
tela enviada. Registrar limite dessa evidência, sem concluir que inexista
identificação em todo o sistema ou que a descrição genérica prove o vínculo.
Não pedir repetição dessa captura nem abrir abas fiscais sem finalidade para
esses pontos. Orientar saída sem gravar e conferência do arquivo original
usado na importação/quem a realizou para vínculo e origem do saldo; não
presumir a existência de um histórico de importação acessível nessa instalação.

Continuidade documental D-320: responsável pediu resumo simples do trabalho
CONTAD e prompt para outra sessão do Codex continuar. Entregar resumo local em
docs/contad-continuidade-2026-11-06.md e prompt privado em Downloads, com caminhos
das evidências e próximo passo real. Não abrir/criar outra sessão, executar
novas consultas ou publicar alteração por esse pedido. Separar o que foi
implantado, o que foi informado pelo operador e o que segue pendente. Identificador
de extrato, conta bancária, valores e login continuam fora do Git; incluir somente
no prompt/evidências privados o necessário à continuidade, sem senhas/tokens.
Preservar alterações locais anteriores, IDs canônicos e autorizações já dadas;
resumo não cria plano concorrente, aprovação de recorte ou conclusão de etapa.

Retomada D-320 (06/11/2026): responsável solicitou nesta conversa “sim,
continue o trabalho com base nesses dois arquivos”, referindo-se ao resumo e
ao prompt de continuidade. Prosseguir em PC-19/etapas 03/09/12 a partir das
evidências locais existentes, sem reinstalar ou repetir a sonda concluída.
Conferir integridade das fontes e o percurso de acesso já implementado enquanto
aguarda a informação de quem importou o extrato sobre arquivo e saldo inicial,
no mesmo Q-28. A retomada não aprova vínculo/recorte, condição de ativação,
convite, pareamento, envio de dados, SQL adicional, custo ou novo deploy.

Esclarecimento humano na retomada D-320/Q-28 (06/11/2026): responsável afirmou
“a empresa esta fechada e ela passou arquivos para teste. ponto final. utilize
isso como evidencia”. Tratar a declaração de empresa fechada e o fornecimento
dos PDF/OFX/Razão como evidência autorizada do corpus de teste local. Não exigir
origem do saldo da janela Domínio ou identificação de quem importou para
prosseguir nesses testes, nem repetir essa pergunta. A divergência observada
fica como limite da evidência anterior, sem causa presumida e sem bloquear
testes locais. Aproveitar resultados já verificados e avançar no confronto
independente com o Razão fornecido; não contar replay como novos eventos ou
inventar contrapartidas. Não interpretar “fechada” como baixa cadastral/legal,
aprovação de partidas ausentes, autorização de escrita/importação ERP,
pareamento/transmissão, ativação comercial, IA paga ou homologação integral.

Implementação local da retomada D-320: tornar repetível o confronto já feito
com os arquivos, por leitor do layout textual de Razão Domínio observado e
CLI privada de conferência OFX/PDF bancário/Razão. Ler identidade/período/conta,
colunas explícitas de débito/crédito/saldo, páginas e totais; rejeitar documento
incompleto/inconsistente. Preservar hash e localização das linhas e multiplicidade
de datas/valores; coincidência é candidato, com ambiguidades expostas e nenhuma
conciliação automática. É evidência do efeito da conta no Razão, sem fabricar
partidas completas ou cadastrar contas. Saída local restrita, sem banco de
aplicação, alteração de interface, rede, provedor, ERP ou habilitação de gates.

Resultado local da retomada D-320/V-323: leitor/CLI implementados e exercitados
com os arquivos fornecidos; 163 coincidências por data/valor, 159 candidatos
únicos, dois grupos ambíguos e saldos dos PDFs iguais. 139 testes aprovados,
cinco skips antigos de concorrência PostgreSQL; Ruff global/MyPy dos dois
módulos/Django aprovados. Execução real final sem conexões de rede/banco,
fontes preservadas e relatório 0600; nenhuma confirmação automática ou escrita
ERP. Não reabrir a origem do saldo da captura como condição do corpus local.

## D-321 — Publicar a retomada e concluir pendências CONTAD (06/11/2026)

Origem: responsável solicitou “faça o deploy e termine as pendencias” após a
entrega D-320/V-323. Publicar a versão revisada no app Fly existente e avançar
nas pendências PC-19/etapas 03/09/12, preservando arquivos/dados e alterações
locais anteriores. A autorização de publicação não precisa ser repetida.
Usar o corpus fornecido já aceito como evidência, sem reabrir a origem do saldo.
Conferir versão/CI/artefato, recuperação existente e pós-deploy; não ampliar
recursos/recorrência ou consumir IA paga por inferência. Manter saída privada
não homologada e exportação Domínio false. Não inventar títulos/contrapartidas,
condição comercial/papel ou aceite humano para marcar pendência concluída.
Levantar primeiro o estado atual e preparar ações concretas; solicitar somente
informação/autorização específica que realmente faltar, enquanto avança nas
frentes independentes. Não enviar convite/mensagem sem instrução explícita,
nem modificar o Domínio ou executar consulta SQL adicional não autorizada.

Escolha específica D-321 (06/11/2026): diante da proposta de somente
Conciliação, responsável já indicada como Proprietária e contrato existente de
R$ 200/mês sem iniciar cobrança automática, o responsável escolheu **“Ativar,
sem enviar convite”**. Ativar esse escopo no escritório próprio CONTAD; não
enviar convite/recuperação/mensagem, gerar cobrança ou definir senha por essa
ação. Reutilizar usuário existente quando a identidade confirmada já tiver
conta; verificar o fluxo seguro antes de criar conta sem acesso utilizável.
O responsável confirmou também que o PC CONTAD está disponível para passos
guiados do agente. Não retomar controle alternativo AnyDesk nem reinstalar.

Preparação do deploy D-321: expor a mesma conferência local por comando Django
administrativo incluído na imagem, sem novo endpoint/tela, importação ou envio
de arquivos da cliente por inferência. Reutilizar gravação privada/atômica no
módulo da aplicação para que a CLI não dependa de `scripts` ausente no runtime;
incluir a CLI no manifesto de fonte. Validar comando, CLI e a versão exata
antes de publicar. A saída permanece conferência, não partidas contábeis.

Conferência de acesso D-321: o login indicado ainda não possui conta no CICA.
Ativar escritório/contrato individual/módulo sem criar usuário com senha
improvisada ou conta inutilizável, e sem emitir convite; o vínculo Proprietária
fica aprovado para o fluxo seguro posterior. Contrato sem plano de catálogo,
mensalidade travada em R$ 200 e somente Conciliação, preserva a exclusão do
fechamento automático de faturas já implementada. Dois testes isolados aprovaram
acesso ao módulo, recusa de IA, nenhuma fatura/convite/credencial, reutilização
de usuário quando existente e repetição da ativação sem duplicar contrato.

Execução de ativação D-321: escritório CONTAD em **active**, somente
Conciliação habilitada e contrato individual ativo R$ 200/mês, preço travado,
sem plano de catálogo, Asaas, fatura, convite ou senha criados. Auditoria
persistida com referência D-321; responsável ainda sem conta/membro, conforme
escolha de não enviar convite. Não declarar login disponível por essa ativação.
Fonte 651368c publicada na main, candidata de 820 hashes iguais ao commit,
CI 42282953292 em execução. Imagem local linux/amd64 aprovada em teste sem
rede/banco, 647 arquivos de runtime iguais à candidata; deploy ainda pendente.

**Autorização específica recebida Q-28/D-321 (06/11/2026):** responsável escolheu
“Autorizar somente esse recorte” para o agente ler/enviar ao CONTAD os dados da
SURIA, Domínio 212, conta contábil 8 — Sicredi dos arquivos fornecidos,
setembro/2026, somente extrato 55 já identificado pela sonda. Essa aprovação
fecha o recorte operacional do piloto a partir das evidências existentes;
não exigir origem do saldo da captura. Registrar empresa/conta financeira com
identidade extraída dos arquivos aceitos e emitir manifesto `dominio-pilot-v1`
limitado a esses campos/ID; não habilitar carteira inteira ou SQL adicional.
Preparar código temporário de uso único para o operador no PC, sem convite,
senha no chat ou conteúdo financeiro versionado. Preservar fonte bancária e
Razão como fatos distintos; autorização de sincronizar extrato não é escrita
ERP, importação/geração de partidas ausentes, IA paga ou homologação integral.

Execução do recorte Q-28/D-321: empresa e conta financeira registradas no
CONTAD a partir dos arquivos aceitos, manifesto validado para 212/8/09-2026/
extrato 55 e código de uso único emitido por 60 minutos. Código guardado só
em arquivo privado para o operador; não incluído nos registros ou Git.
Três testes isolados de ativação/recorte aprovados; não emitido código genérico.
No primeiro snapshot remoto posterior, código ainda não utilizado e zero
agentes/linhas financeiras: a orientação ao PC não comprova pareamento.

Gate de deploy D-321 cumprido: CI 42282953292 concluído com sucesso para
651368c101bec5b8b0bb9a75b4fb1268029dd220, agente/pacote Windows, testes SQLite/
PostgreSQL e três imagens aprovados. Publicar a imagem já conferida
sha256:20f01b3888c8fa02395a876e6b4597fbf49db7a29a0919e288d3a9b78979717a,
usando configuração hospedada preservada, --ha=false e excluindo a reserva
287e35db920e48. Não ampliar recursos ou alterar banco/retencão/portas/gates;
em falha retornar à imagem release 72, preservando dados/migrações e a
ativação explicitamente autorizada. Conferir runtime, migrações, health e
proteção de acesso após a atualização, antes de afirmar deploy concluído.

Resultado de deploy D-321: release Fly **73** concluída, fonte 651368c,
web/worker com os 647 arquivos/hashes esperados, migrações/endpoint Neon
preservados e health 200/banco/cache ok. Duas máquinas originais/512 MB,
ambiente/serviços e reserva parada conferidos; nenhuma alteração recorrente.
Prévia/download anônimos 302, agente inválido 401, exportação false.

Correção operacional do pareamento D-321: captura do operador mostrou erro
“Não foi possível restringir a pasta de configuração”. Código foi consumido e
agente criado, mas sem heartbeat, conector ou linha financeira; fonte do
configurador confirma falha de icacls antes da gravação DPAPI. Orientar abertura
elevada do configurador, preservando MSI/DSN. Revogar somente essa credencial
órfã sem uso e emitir novo código temporário para o mesmo manifesto aprovado,
sem apagar histórico ou ampliar o recorte; guardar substituto no arquivo
privado já indicado, sem conteúdo de segredo nos registros. Não declarar
serviço configurado ou leitura real até a prova posterior no PC/backend.


Recuperação do pareamento D-321 executada: credencial órfã revogada, código
substituto emitido com manifesto idêntico e arquivo privado substituído 0600.
Operador informou “Recorte configurado” após abertura elevada; novo agente
com heartbeat e **163 movimentos** recebidos no backend. Primeiro estado
informado por PowerShell: Running/LocalSystem/ready, observado 20:13:55 UTC.
Orientado reinício somente do serviço para provar reabertura da configuração e
repetição sem duplicação; sem reiniciar PC/ERP ou alterar rede/credenciais.
Registrar o resultado efetivo antes de marcar essa prova concluída. Credencial
revogada fica no histórico, não reutilizada; código temporário consumido não
representa login pessoal ou convite.

Higiene do DSN dedicado D-321: operador retornou true para presença de campo
PWD/Password/Senha no CICA_CONTAD x64. Isso prova nome de campo, não valor
preenchido. Como a captura/serviço comprovaram credencial EXTERNO explícita na
configuração protegida e autenticação herdada do DSN desmarcada, orientar
remoção somente desses campos do novo CICA_CONTAD x64, sem ler/exportar valores,
alterar usuário/servidor/driver ou tocar o DSN original x86. Reiniciar somente
CicaAgent e conferir ausência dos campos, estado e nova sincronização; não
marcar ausência comprovada antes do resultado. Essa correção segue o requisito
já aberto da etapa 03, sem extração, troca ou revogação da senha do ERP.


Conclusão da prova guiada D-321: após reinício, operador informou
Running/Auto/LocalSystem/ready (20:15:14 UTC). Após remoção só dos campos de
senha no CICA_CONTAD x64 e outro reinício, informou CampoDeSenhaNoDsn=false,
Running/ready (20:17:39 UTC). Configuração protegida reabriu e ciclo concluiu;
nenhuma leitura de segredo do registro ou alteração do DSN original.
Conferência backend anterior: 163 itens/espelho, zero duplicações/fora de recorte,
conector healthy. Multiconjunto data/módulo do valor igual ao corpus aceito;
no recorte observado, C corresponde às 108 saídas e D às 55 entradas,
reproduzindo também as datas/valores assinados dos arquivos. Preservar sinais
originais e direção do Domínio, sem aplicar essa observação como regra geral
para partidas contábeis. 151 vínculos de extrato preexistentes não são prova
de Razão independente ou aceite do conciliador.

Finalização documental D-321: atualizar plano/checklists, V-324, execução e
continuidade com resultados efetivos; publicar somente esses registros de
operação na main com [skip ci], mantendo o código implantado 651368c e as
alterações locais anteriores fora do índice. Não fazer novo deploy por textos,
criar usuário/convite/fatura ou encerrar gates de fontes/títulos/DE-PARA/ERP,
D-73, recuperação recorrente, treinamento e aceite por essa documentação.

**Autorização posterior de acesso pessoal D-321 (06/11/2026):** após perguntar
pela conta da Grazi, o responsável solicitou configurá-la com o e-mail já
fornecido e uma senha simples. Essa instrução autoriza agora criar usuário
ativo e senha inicial, validada pela política vigente, e vinculá-lo como
Proprietária somente à CONTAD, conforme papel já aprovado. Usar nome Grazi e
identidade do arquivo privado existente, sem repetir pergunta de e-mail.
Não atribuir staff/superusuário/acesso de plataforma, criar outro escritório,
enviar convite/e-mail ou mudar contrato/módulos/cobrança/agente. Gerar senha
inicial com caracteres fáceis de digitar e aleatoriedade, sem enfraquecer os
validadores; entregar e-mail/senha em arquivo local 0600, sem Git/logs ou senha
literal em argumentos de processo. Se surgir conta existente inesperada,
preservar credencial/vínculos e revisar antes de sobrescrever. Testar o roteiro
isolado e conferir login HTTPS real, escritório/empresa e permissão de importar,
sem anexar dados ou aprovar conciliações na sessão de verificação. Essa entrega
não exige mudança de código/interface, deploy ou envio de mensagem à Grazi.

Execução de acesso D-321: primeiro roteiro passou em quatro testes isolados,
mas o processo administrativo no web foi encerrado por falta de memória ao
tratar Argon2. Leitura posterior confirmou zero conta/vínculo/auditoria parcial;
site/health/agente continuaram respondendo. Preparar/validar a senha e o hash
Argon2 no Mac, sem carregar essa operação extra no web; transmitir somente hash
à transação na máquina worker existente, preservando algoritmo/parâmetros,
recursos e política. Revalidar roteiro com Argon2 real antes da nova execução;
conferir a senha pelo login HTTPS normal, sem hash ou segredo no registro Git.

Resultado do acesso D-321: roteiro final com Argon2 real aprovado em quatro
testes isolados. Usuário Grazi criado ativo, senha inicial validada e hash
Argon2, vínculo único Proprietária da CONTAD, sem staff/superusuário/grupo ou
permissão de plataforma. Contrato/módulos/agente/dados mantidos. Login HTTPS
real aprovado, sessão entrou diretamente na CONTAD, Conciliação 200 com SURIA,
origem extrato bancário e Nova importação/campo de arquivo disponíveis. Nenhum
arquivo enviado/decisão contábil tomada; sessão de verificação encerrada e
retorno anônimo ao login conferido. Credencial entregue só em arquivo privado
0600; convite/e-mail/fatura continuam zero. A pendência de criação do acesso
pessoal está concluída, substituindo o estado anterior sem usuário. Atualizar
continuidade/checklists/validações e publicar só documentação com [skip ci],
preservando os trabalhos locais anteriores; não há código/deploy novo.

## D-323 — Executar a finalização CONTAD para toda a carteira (06/11/2026)

Origem: pedido humano `/goal Implemente o desenvolvimento final do projeto
CONTAD com base no prompt anexado`. O anexo é especificação da entrega, lido
como tal; não substitui autorizações humanas para custo, egressão ou escrita
ERP. Executar PC-19/etapas 03/09/12, incluindo implementação, testes e publicação
no ambiente existente, preservando alterações locais anteriores. D-322 deixa
de ser somente um objetivo futuro nesta execução; o piloto existente continua
intacto até evolução compatível e validada do agente/servidor.

**Q-28 respondido nesta sessão:** histórico financeiro inicial de **setembro de
2026 em diante**, cadastros/contas integrais. Operador **disponível mais tarde**
para consulta guiada e atualização do Windows. Não escolher histórico anterior,
repetir credenciais/DSN ou inferir acesso remoto alternativo. Preparar consulta
limitada de metadados das fontes pertinentes e inventário agregado sem valores
financeiros; obter o resultado real antes de habilitar SQL financeiro novo.

Sequência única: (1) inventário de metadados e protocolo de carteira isolado por
escritório, compatível com piloto, (2) cadastros/contas/referências e cobertura
paginada auditada, (3) fontes independentes de Razão/títulos após confronto
semântico real, (4) testes/CI/publicação/upgrade, (5) provas operacionais,
recuperação, treinamento e aceite D-73. Frentes independentes podem avançar
enquanto o operador não estiver disponível. Semântica de situação desconhecida
não ativa/desativa cadastro por inferência; páginas incompletas não removem
empresas. Paginação exige confirmação transacional e retomada explícita;
replay não conta como nova amostra real. Q-46/Q-47 e Q-08/Q-09 permanecem com os
mesmos IDs e gates. Nenhum requisito é concluído por esta decisão.

Continuidade técnica D-323: regressão PostgreSQL em tmpfs concluída com
1.788 testes/163 subtestes aprovados e um skip de navegador opcional. Docker
local conserva apenas 150 MiB livres; não apagar imagens, volumes ou caches de
outros projetos nem ampliar recursos globais para publicar. Como Dockerfile,
dependências/lock e assets permanecem idênticos à fonte implantada 651368c,
preparar a candidata sobre a imagem imutável da release 73, acrescentando somente
os arquivos Python alterados/aditivos do commit e conservando usuário/configuração/
camadas anteriores. Conferir o conjunto completo de hashes runtime e a cadeia
de camadas/configuração antes do deploy, além do CI que constrói o Dockerfile
completo. Essa escolha é empacotamento desta entrega, não mudança de arquitetura
ou dependências. Não há deploy até os gates da versão exata passarem. Retorno
permanece a imagem original da release 73, com migrações aditivas preservadas.

Gate de publicação D-323: CI 42294764025 aprovado para e9311eb, testes/agente,
MSI 1.0.4 e três imagens Docker aprovados. Candidata: 825 blobs iguais ao commit,
ZIP edb6538c07e21dd3dee332ae0305b448b966dd9295950b8cbc50b48a0fc7afef.
Imagem candidata imutável sha256:080f24c0b055a0f4d8e8271a6cdd7112b035309bc5824feeddc4b4157920951e,
651 hashes runtime conferidos offline com rede/banco bloqueados, configuração
runtime e camadas da release 73 preservadas. Config Fly atual igual à da 73;
backup original/53 objetos/retencão de sete dias conferidos por metadados.
Publicar no app existente com --ha=false, --update-only e reserva 287e35db920e48
excluída, sem ampliar memória ou alterar bancos/retencão/manifesto do agente.
Aplicar migrações aditivas; retorno na imagem original 73, sem apagar esquema
ou dados. Conferir runtime dos dois processos, migrações, saúde, acesso e
fingerprints do recorte antes de declarar publicação concluída. Publicar backend
não habilita carteira nova, contas, Razão/títulos, IA ou exportação ERP.

Resultado D-323/V-327: backend release 74/fonte e9311eb/CI 42294764025 aprovado,
651 hashes e migrações conferidos nos dois processos/aliases, recursos originais
e reserva preservados, doze fingerprints CONTAD iguais antes/depois, login
Grazi conferido sem upload/decisão. Windows descartável aprovou MSI 1.0.4/52
testes/26 checks; pacote preparado, sem upgrade no PC. Operador respondeu que
continua indisponível. Inventário, novas fontes financeiras e coleta da carteira
não executados. Último heartbeat real anterior ao deploy; não inferir causa ou
prova de sincronização nova. Guia de treinamento preparado, sem execução/aceite.
Manter PC-19 e gates abertos; próximo insumo Q-28 é o resultado real do inventário.

Continuidade independente D-323 (07/11/2026): revisão da carga encontrou uma
lacuna de retomada na recepção já publicada: diferença de cobertura no fim da
leitura devolve 409, mas conserva o scan aberto; se a contagem voltar ao valor
original, a próxima tentativa pode insistir no mesmo cursor inválido. Corrigir
o servidor para abandonar atomicamente somente a leitura aberta inconsistente,
preservar páginas/cadastros anteriores e iniciar outra leitura na próxima
abertura, mesmo com contagem igual. Conservar recibos de cargas concluídas e
não abandonar por requisição atrasada ou cursor alheio. Persistir código/horário
de erro sem nomes, documentos ou texto de origem e disponibilizar diagnóstico
administrativo somente leitura por escritório/agente. Compatível com MSI 1.0.4;
sem alteração de UI, SQL ERP ou manifesto real. Exercitar falha/repetição e
concorrência PostgreSQL, atualizar registros e publicar a correção depois do
CI da versão exata. Inventário e demais gates reais continuam pendentes.

Empacotamento da correção D-323/V-328 (07/11): candidata sobre a imagem
imutável da release 74, acrescentando somente os arquivos Python alterados/
aditivos de c8b0c50. Dockerfile, dependências/lock, assets, agente e manifesto
real continuam iguais; conferir camadas/configuração e todos os hashes runtime
antes do deploy. Backup original/53 objetos/retencão reconferidos após timeout;
processo anterior já ausente, sem leitura duplicada presumida como prova.
Retorno de aplicação na imagem original 74, mantendo intelligence.0034 aditiva.
Sem novo recurso, retenção, chave, cópia ou restore. Gates da versão exata e
verificação pós-deploy continuam obrigatórios; nada disso habilita fonte ERP.

Gate de publicação da correção D-323/V-328: CI 42355490505 aprovado para
c8b0c50; PostgreSQL local 1.801/163 com um skip e CI 1.800/163 com dois skips.
828 blobs da candidata iguais ao commit; imagem imutável
sha256:61e035af2a18ff57b122cd1b1f5b13c7b5dee79f70a7bd8b87d16f581ed5af80,
653 hashes runtime/offline iguais, base/configuração 74 preservadas. Migração
aditiva intelligence.0034; comando somente leitura presente na imagem.
Configuração live difere do arquivo anterior somente em deploy.strategy,
canary → rolling, resultante do deploy rolling da 74 já registrado; ambiente,
serviços e recursos iguais. Release corrente 74 conferida. Publicar no mesmo
app com --ha=false/--update-only, reserva excluída, sem mudar manifesto, agente,
memória, bancos ou retenção. Retorno na imagem 74 conservando a migração aditiva.
Conferir ambos os processos/aliases, integridade e acesso depois da publicação.

Resultado da correção D-323/V-328: release 75/fonte c8b0c50/CI 42355490505
aprovado, 653 hashes e migrações conferidos em web/worker/dois aliases,
diagnóstico somente leitura executado, doze fingerprints CONTAD e acesso Grazi
preservados, recursos originais mantidos. Falha transitória do túnel SSH contornada
pela API autenticada Fly Machines exec com credenciais existentes, sem mudar
acesso ou infraestrutura. Comando/deploy não criou scan ou fonte nova. Último
relato de operador indisponível e inventário não recebido; manter Q-28 e demais
gates abertos, sem afirmar conclusão contratual ou recuperação real da carteira.

## D-324 — Novo agente oficial CONTAD no Windows Server (09/11/2026)

Origem humana: adaptar o plano anexado para instalar novamente o agente em
outro computador, agora Windows Server, torná-lo o agente oficial, melhorar o
plano e começar o desenvolvimento. O responsável informou que o acesso já foi
disponibilizado por **AnyDesk**. Essa decisão substitui o destino PC antigo das
instruções D-321/D-323, sem reabrir a intenção de carteira completa nem o início
financeiro em 01/09/2026. Versão/arquitetura/ODBC e identidade da nova máquina
ainda precisam ser observados; configuração válida no PC antigo não os comprova.

O anexo é base de especificação, não autorização independente para executar seus
imperativos de deploy, custos, egressão ou importação ERP. Nesta rodada iniciar
implementação local e preparar instalação/corte com evidência. Preservar runtime,
dados, decisões humanas, contrato, credenciais pessoais e trabalhos locais.
Usar PC-19 e etapas 03/09/12; atualizar o prompt canônico existente, sem criar
plano concorrente. D-323/V-328 é a última evidência publicada: release 75,
MSI 1.0.4 preparado, PC antigo 1.0.3/piloto, inventário real ainda não recebido.

Escolha técnica antes do comportamento dependente: substituição em **duas
fases**. Código temporário próprio referencia explicitamente o agente anterior
do mesmo escritório e herda exatamente seu manifesto validado. Novo equipamento
recebe novo UUID/segredo HMAC, sem copiar DPAPI, configuração ou senha do PC.
Pareamento cria candidato pendente; permite apenas heartbeat/configuração e
impede coleta até ativação. Cliente deve declarar suporte a esse protocolo.
Depois de comprovar instalação/LocalSystem/ACL/DPAPI/ODBC/reinício no Server,
ativação administrativa exige os dois IDs, revisão idêntica e heartbeat recente
(cinco minutos, limite técnico desta operação). Em uma transação, torna o novo
agente oficial e revoga apenas o anterior, com auditoria. Um único oficial por
escritório; solicitações concorrentes de ingestão são serializadas com o corte.
Não promover automaticamente pelo mero consumo do código ou heartbeat.

Falha antes do corte mantém o anterior ativo; candidato pode ser revogado.
Falha posterior não reativa credencial revogada: retorno exige outra
substituição explícita. Scans e dados anteriores permanecem como histórico;
o novo agente recomeça sua leitura paginada, com identidades idempotentes no
escritório. Troca de máquina não amplia fontes/manifesto: carteira completa
segue após inventário real/situações e contratos Q-28/Q-46, em passo separado.
Q-47, IA Q-08/Q-09, custos, D-73, recuperação, treinamento e aceite permanecem.

Inspeção desta sessão: AnyDesk consta aberto no Mac, mas a ferramenta nativa
retornou timeout (-10005) ao obter a janela por nome e bundle ID; não foi
possível observar/controlar o Server. Isso é limite da ferramenta, não prova de
indisponibilidade do acesso humano. Nenhuma ação remota foi executada.

Revisão de compatibilidade D-324: a [política oficial Microsoft](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core),
consultada em 09/11/2026, informa fim do suporte .NET 8 em **10/11/2026** e
.NET 10 LTS em 14/11/2028. D-289 fixa .NET 8, portanto não trocar o alvo por
inferência nesta implementação. Recomendada revisão explícita de D-289 para
preparar .NET 10 antes da operação oficial duradoura, sujeita à versão do Server
real e às provas de pacote/ODBC/DPAPI. Consulta encaminhada ao responsável;
desenvolvimento independente do corte segue na base atual até a resposta.

Resposta humana sobre a revisão D-289/D-324: **“Verifique se o windows server
(provavelmente antigo) suporta isso”**. Verificar o sistema real antes de
alterar o alvo; isso não é aprovação incondicional de .NET 10. Nova tentativa
de observar AnyDesk por caminho completo também retornou timeout -10005.
Solicitado somente o texto do `winver`, sem senha ou mudança no servidor.
A [matriz oficial .NET 10](https://github.com/dotnet/core/blob/main/release-notes/10.0/supported-os.md)
consultada lista Windows Server 2016/2019/2022/2025 x64 e 2012/2012 R2 sob ESU.
Essas condições documentais não comprovam edição, patches, ESU, driver ou
instalação reais da CONTAD; mantida a base .NET 8 enquanto a versão é desconhecida.

Resultado local D-324/V-329: plano/prompt adaptados, candidato/coleta bloqueada e
corte oficial atômico implementados; PostgreSQL 1.837 testes/163 subtestes,
um skip, SQLite focado 30/seis skips concorrentes e .NET 59/um skip Windows.
Três builds Release sem erros/avisos; Ruff/MyPy/Django/migrações aprovados.
Dez arquivos com alterações anteriores conferidos como preservados. Nenhuma
mudança do alvo .NET 8, CI remoto, MSI 1.0.5, publicação ou instalação/corte reais.
Texto do winver ainda aguardado para verificar suporte do Server. Próxima ação
externa: observar a edição/versão antes da decisão de runtime e preparar a
publicação/pacote exatos; demais gates do projeto permanecem abertos.

Continuidade D-324 — roteiro ao operador (10/11/2026): responsável pediu passo
a passo para instalação e testes dentro do Windows Server. Entrega documental
do procedimento existente, com preparação executável agora e instalação/
pareamento condicionados à versão real compatível, MSI 1.0.5 validado e backend
de substituição publicado. Não tratar o MSI 1.0.4 disponível como portador de
staged-v1 nem supor publicação desde V-329. Não há novo deploy, acesso remoto
ou decisão de runtime nesta orientação. Testar conexão no configurador comprova
ODBC sob o operador; awaiting_activation comprova comunicação/configuração
do serviço, mas o candidato não executa leitura ERP. Não declarar ODBC sob
LocalSystem, ingestão ou carteira completa por esses dois resultados isolados.
O aceite da troca continua exigindo as verificações operacionais e do backend.

Evidência humana Q-28/D-324 (10/11/2026): captura de winver fornecida pelo
responsável identifica **Windows Server 2022 Standard, versão 21H2, compilação
20348.5761**. A identificação não está mais pendente; não repetir pedido de
ano/edição/build. A matriz oficial Microsoft .NET 10 consultada inclui Server
2022 x64: a versão do sistema é compatível em nível de plataforma. A imagem
não comprova arquitetura do processo PowerShell, privilégios, DSN/driver,
conexão LocalSystem, pacote ou funcionamento do agente. Não equivale a execução
remota ou aprovação de mudança do alvo fixado em D-289; próxima verificação
guiada é PowerShell x64 e presença de instalação/configuração CICA no Server.

Continuidade visual Q-28/D-324 (10/11/2026): segunda captura mostra janela
PowerShell identificada como Administrador, Is64BitProcess=True, consulta de
serviço sem listagem e Test-Path da configuração retornando False. ODBC 64 bits,
aba DSN de Sistema, lista Contabil/32 bits/SQL Anywhere 17 (selecionado),
Contabil/64 bits/SQL Anywhere 16, e-Robo/64 bits/SQL Anywhere 16 e
e-Robo 17/64 bits/SQL Anywhere 17. Não inferir que os DSNs apontam ao mesmo
banco ou escolher driver 17 apenas pela versão. Próximo passo guiado: selecionar
Contabil de 64 bits e inspecionar somente identificação do servidor/banco,
sem salvar/alterar o DSN original e sem exibir/extrair senha. CICA_CONTAD não
aparece na lista observada. Isso não é teste ODBC ou instalação concluída.

Continuidade Q-28/D-324 (10/11/2026): captura da configuração inspecionada mostra
Authentication=Database, User ID/Password vazios, Action=Connect to a running
database on another computer, Host/Port vazios, Server name=SrvContabil e
Database name=Contabil. Os nomes/valores estão recebidos; não repetir a pergunta
ou inferir IP/porta/localhost. Orientação seguinte prepara novo DSN de sistema
CICA_CONTAD em x64/SQL Anywhere 16 com esses parâmetros observados, sem alterar
Contabil original e sem salvar usuário/senha no DSN. Isso é configuração inicial,
não clone de Network/Advanced (ainda não inspecionados) nem conexão aprovada;
teste autenticado explícito somente no Windows continua pendente. Não selecionar
SQL Anywhere 17 por existência de outra conexão e não instalar o agente por
essa evidência. Dados do recorte e gates anteriores preservados.

Falha guiada Q-28/D-324 (10/11/2026): captura do teste mostra “Login mode
'Integrated' not permitted by login_mode setting”. É recusa de modo de login,
não prova de senha errada ou incompatibilidade de driver. Não mudar login_mode
do banco nem trocar 16/17 por essa mensagem. Próximo ajuste somente no DSN
dedicado: conferir Authentication=Database e fornecer EXTERNO/senha localmente
apenas para Test Connection. SAP documenta que esse botão exige usuário/senha
na aba Login. Os campos vazios eram para a configuração salva; depois do teste,
limpar User ID/Password antes de salvar, sem captura/chat de credenciais.
Estado atual da aba Login/DSN usado no teste não está visível na captura do
erro: não inferir parâmetro salvo, criação concluída ou resultado do reteste.

Resultado informado Q-28/D-324 (10/11/2026): após orientação de conferir
Authentication=Database e EXTERNO/senha apenas no teste local, responsável
respondeu **“sucesso”**. Registrar teste ODBC interativo bem-sucedido informado
pelo operador; a falha de login integrado não é mais o resultado atual.
Não repetir o teste sem motivo nem inferir parâmetros persistidos, ausência
de senha no DSN, execução LocalSystem ou instalação do agente. Próximo passo
local é limpar User ID/Password e salvar somente CICA_CONTAD, mantendo
Authentication=Database e dados de conexão. Não alterar o DSN original.
Pacote 1.0.5/backend de substituição e demais gates permanecem pendentes.

Confirmação humana Q-28/D-324 (10/11/2026): após instrução de limpar User ID/
Password e salvar CICA_CONTAD mantendo Database, responsável respondeu “foi”.
Registrar limpeza/salvamento informados; não repetir essa tarefa ou exigir
nova senha. Resultado não é leitura do registro, prova LocalSystem ou instalação.
Próxima dependência é o pacote/backend oficial, ainda não entregues.

Preparação independente D-324 antes da revisão D-289: verificar compilação e
testes do alvo .NET 10 em cópia temporária isolada de fontes/contratos, sem
mudar o alvo do projeto corrente, instalar no cliente ou publicar. Essa prova
completa a avaliação solicitada pelo responsável após confirmar Server 2022;
não aprova por si a migração ou homologa runtime/ODBC Windows. Solicitar revisão
expressa de D-289 para incorporar .NET 10 ao pacote oficial; custos, CI/publicação
e demais gates não são inferidos da confirmação de salvamento do DSN.

## D-325 — Agente oficial em .NET 10 LTS (10/11/2026)

Responsável aprovou expressamente a opção “Atualizar para .NET 10 LTS
(recomendado)” após confirmação do Windows Server 2022 Standard. Esta decisão
substitui o alvo .NET 8 de D-289 para as novas compilações do agente oficial
preparado em D-324. Migrar serviço, configurador, ponte ODBC, contratos e testes
para .NET 10, ajustar dependências Microsoft e CI, preservando versão candidata
1.0.5, distribuição autocontida, serviço/configurador x64 e ponte x86. Usar
patches estáveis disponíveis e verificar testes, compilação e publicação local.

A compatibilidade de plataforma Server 2022 x64 está confirmada na matriz
Microsoft; não equivale a homologação de ODBC sob LocalSystem ou do MSI. A
aprovação do runtime não autoriza deploy, publicação de release, custos ou
ativação/revogação de agentes. Permanecem os gates de D-324/Q-28, com DSN
CICA_CONTAD salvo e teste ODBC interativo informados pelo operador.

## D-326 — Branch técnica e CI Windows do agente oficial (10/11/2026)

Responsável respondeu **“Autorizar branch e CI Windows”** à proposta concreta
de enviar somente as alterações do agente oficial/substituição e gerar/testar
MSI 1.0.5 em Windows descartável. Autorizados branch técnica no GitHub e CI
Windows dessa fonte, incluindo migração .NET 10 LTS de D-325. Não inclui deploy
em produção, publicação de release, instalação na cliente, corte de agentes,
mensagens a terceiros ou contratação de recursos. Preservar e excluir do commit
os trabalhos locais anteriores D-316/D-317/etapa 00/comparação Pandolfo. Conferir
privacidade/capacidade do runner antes de disparar; não recorrer a runner pago
especial ou self-hosted/cliente para contornar indisponibilidade. Artefatos,
fonte, hashes e resultado devem ser registrados com seus limites.
