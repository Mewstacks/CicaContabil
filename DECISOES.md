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
