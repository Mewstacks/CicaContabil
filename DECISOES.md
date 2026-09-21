# CICA — decisões e limites de confirmação

> Registro canônico na raiz desde 17/09/2026, por D-59. Ler com [plano mestre](PLANO-MESTRE.md) e [validações técnicas](VALIDACOES.md). Decisão aprovada não é função implementada. As classificações históricas abaixo foram preservadas: “Registrada” não foi promovida a “Confirmada”. Não repetir perguntas já resolvidas.

O bloco D-01–D-45 e a lista “Decisões que não foram tomadas” são o registro histórico de 15/09. Atualizações D-46–D-60 ao final prevalecem somente no escopo explícito; por exemplo, Q-10 foi resolvida.

Atualizado em 15/09/2026. **Confirmada** significa resposta direta do responsável, registrada na sessão indicada em [fontes e histórico](docs/planejamento/fontes-e-historico.md) ou nesta conversa. **Registrada** significa que um plano/documento a apresenta como decisão anterior, mas o detalhe ainda não foi reconfirmado nesta rodada. **Proposta** não autoriza implementação comercial, publicação ou gasto. Os estados técnicos estão em [estado operacional](docs/planejamento/estado-operacional.md).

## Produto, marca e venda

| ID | Estado | Decisão / limite exato | Fonte | Consequência |
| --- | --- | --- | --- | --- |
| D-01 | Confirmada | Nome oficial **CICA**, Central de Inteligência Contábil Avançada. “HubContador” e “CICA” são nomes históricos/técnicos. | CX-07; `docs/cica-implementation.md` | Texto público e documentação de produto usam CICA; renomear identificadores técnicos é assunto separado. |
| D-02 | Confirmada | Produto centralizado SaaS para escritórios, com liberação de ferramentas e funções conforme contratação. | CX-01; CX-07 | Contrato, módulos, isolamento por escritório e permissões precisam ser fontes consistentes de acesso. |
| D-03 | Confirmada | Todos os módulos e a IA devem funcionar de ponta a ponta pela visão operacional antes de serem vendidos; dúvidas de produto devem ser trazidas ao responsável. | CX-07; CX-09; CX-10 | “Há modelo/tela/teste” não basta para declarar função pronta. |
| D-04 | Registrada | Teste de 14 dias com suíte completa, sem cartão; MFA obrigatório após teste/contratação e dispensado no teste. | `docs/cica-implementation.md`; `docs/cica-mfa-contract-review.md` | A regra atual precisa de validação de ponta a ponta com o fluxo Asaas decidido agora; condições comerciais finais ainda não foram reconfirmadas. |
| D-05 | Registrada | Marca visual marfim e verde escuro, domínio escolhido `cicacontabil.com.br`, fornecedora Mewstack. | `docs/cica-implementation.md`; `docs/cica-landing-direction.md` | Landing e documentos legais seguem esse contexto; marca, prova social e publicação ainda exigem fechamento. |
| D-06 | Confirmada | Configuração deve ser simples para o próprio escritório; conexão Domínio local por ODBC/agente e Domínio Web por backup importado com atualização manual. | CX-02; CX-06 | Assistentes e instruções precisam cobrir ambos sem alegar sincronização automática do Domínio Web. |
| D-07 | Confirmada | As telas devem ser revisadas pela tarefa real do usuário e por padrões de produtos, com funcionamento em desktop e mobile. | CX-07; CX-09; CL-02 | Critérios de aceite incluem próximo passo, estado, erro, permissão e navegação, além da aparência. |

## Integra Contador, franquia e cobrança

| ID | Estado | Decisão / limite exato | Fonte | Consequência |
| --- | --- | --- | --- | --- |
| D-08 | Confirmada | As credenciais/contrato Serpro pertencem à **Mewstack**, centralmente; o escritório usa cotas e não cadastra sua própria chave Serpro. | CX-05; resposta em CX-09 | Segredos e certificados da central não entram no workspace do escritório; consumo é medido por organização e serviço. |
| D-09 | Confirmada | Existe franquia contratada por escritório e excedente; o plano Codex enviado pelo responsável especificou uma fatura mensal única, com mensalidade e excedentes, sem cobrança avulsa por ação. | CX-05 | Reserva, liquidação, ajuste e faturamento precisam ser idempotentes e auditáveis. |
| D-10 | Registrada | O plano CX-05 indicou fechamento da competência em `America/Sao_Paulo` no dia 1, vencimento dia 10, preços congelados em lançamentos e política `bloquear`/`exigir aprovação`/`autorizar excedente` dentro do teto contratado. | CX-05 | Validar calendário, política e condições na revisão comercial antes de publicar ou migrar contratos. |
| D-11 | Confirmada em 15/09 | **Asaas é o padrão** de cobrança e atende Pix, boleto e cartão. Banco Inter para Pix/boleto é desenho anterior, substituído neste escopo. | respostas do responsável nesta conversa; CL-03 e CX-05 como histórico | Uma fatura deve evitar tentativas simultâneas/duplicadas ao trocar o meio de pagamento. Integração Asaas ainda não está homologada. |
| D-12 | Confirmada em 15/09 | É possível cadastrar escritório/empresa manualmente, cobrar manualmente e definir preço individual diferente do catálogo. | resposta do responsável nesta conversa | O contrato deve distinguir cobrança Asaas de cobrança manual, registrar valores específicos e preservar o histórico. |
| D-13 | Confirmada em 15/09 | Contratos de cobrança manual ficam fora dos webhooks e da suspensão dirigida pelo Asaas, inclusive instalação Windows dedicada. | resposta do responsável nesta conversa | Um evento Asaas jamais altera contrato manual; método e estado de acesso manual dependem da regra comercial ainda aberta. |
| D-14 | Registrada | Nenhuma ação do usuário deve gerar cobrança avulsa do Serpro; cotas, aprovação ou bloqueio precedem a chamada e apenas chamadas efetivamente faturáveis são liquidadas. | CX-05; `docs/cica-operation-access-review.md` | Homologação deve conferir projeção, reserva, resposta, retry, excedente e reconciliação. |
| D-15 | Confirmada em 15/09 | **Asaas suspende automaticamente por inadimplência após um prazo de carência ainda a definir, em modo somente leitura, sem apagar dados; contratos manuais têm suspensão decidida por operador.** A documentação CICA anterior separava registro financeiro e decisão de acesso para todos. | respostas do responsável nesta conversa; `docs/cica-mfa-contract-review.md`; CL-03 | Confirmar duração e marco inicial da carência, quais GETs/downloads permanecem disponíveis, recuperação após pagamento e tratamento de estornos. |

## IA, conhecimento e dados

| ID | Estado | Decisão / limite exato | Fonte | Consequência |
| --- | --- | --- | --- | --- |
| D-16 | Confirmada | **Claude Sonnet por API KEY no `.env` agora**, deixando o produto preparado para o PC/modelo local futuro. A decisão cobre Copiloto e, por confirmação nesta conversa, também análise de anexos da Triagem. | CX-09; resposta nesta conversa | O plano CL-04 “somente modelo local” foi substituído para a etapa provisória. Arquitetura de migração e limites devem ser explícitos. |
| D-17 | Confirmada | Serpro e IA terão cotas por escritório. O responsável pediu pesquisa de limites ideais e preços, mas **não definiu** teto Claude por requisição/dia/mês nem franquia final. | CX-09; `docs/cica-operation-access-review.md` | Não escrever número comercial como aprovado nem realizar chamada paga sem confirmação específica de custo. |
| D-18 | Registrada | Consulta ao Domínio é somente leitura, por ODBC local ou agente no escritório; respostas de IA precisam de evidência e curadoria, com ação humana para alteração. | CX-02; [MCP interno](docs/intelligence-mcp.md) | Escopo por organização/empresa e recusa de SQL, DSN e credenciais no argumento da ferramenta. |
| D-19 | Registrada | O Copiloto ficou oculto e indisponível para escritórios até infraestrutura local na configuração antiga. | `docs/cica-implementation.md`; `platform.PlatformConfiguration` | A decisão D-16 pede novo caminho temporário; ativação, política de custo e publicação comercial ainda não estão concluídas. |
| D-20 | Registrada | Dados de documento/cliente não viram instruções da IA; revisões, fontes e correções precisam de trilha. | `docs/intelligence-mcp.md`; `docs/plano-triagem-documental.md` | Integridade e privacidade precisam ser testadas com anexos não confiáveis e casos ambíguos. |

## Triagem de Arquivos

| ID | Estado | Decisão / limite exato | Fonte | Consequência |
| --- | --- | --- | --- | --- |
| D-21 | Confirmada | Primeira versão vendável recebe documentos **somente de caixa de e-mail**, sem upload de tela nem pasta monitorada como entrada. | CX-09; CL-04 | É preciso conectar caixa, ler anexos com cursor/idempotência e oferecer estado de conexão/erro. |
| D-22 | Confirmada | Suportar **Microsoft 365, Google/Gmail e IMAP genérico**, os três. | CX-09 | O plano CL-04 listava Graph e Gmail via IMAP como alternativa; a forma técnica e OAuth ainda exigem pesquisa/homologação. |
| D-23 | Confirmada; esclarecida em 15/09 | Cada escritório conecta **a própria caixa** em um fluxo guiado. Para Microsoft 365 e Google Workspace, configura **seu aplicativo OAuth** no sistema, com manual passo a passo; IMAP genérico usa assistente TLS. Para **Gmail pessoal**, a Mewstack manterá um aplicativo Google verificado e cada escritório autorizará apenas sua conta. | CX-09; resposta direta “cada escritório deve configurar o seu”; escolha específica do responsável para Gmail pessoal; [pesquisa oficial](docs/planejamento/conexao-caixas-email.md) | Homologar apps e consentimento reais. A Mewstack precisa fornecer redirect HTTPS e registrar/verificar seu app Gmail pessoal antes da venda dessa opção. |
| D-24 | Confirmada | Cada escritório escolhe **biblioteca interna** ou **árvore de pastas Windows da empresa** como destino. | CX-09; CL-04 | Ambas as opções fazem parte do objetivo; forma da troca e coexistência de arquivos antigos precisam ser definidas. |
| D-25 | Confirmada | Para Windows, o próprio escritório configura a raiz; o padrão de pastas será definido pela CICA e a pasta de empresa deverá conter nome e **código Domínio obrigatório**. | CX-09 | Caminho real, nomenclatura completa, validação de escape e permissões do agente seguem pendentes. |
| D-26 | Registrada em CL-04 | `0000` no nome do arquivo é `ClientCompany.dominio_code`; nome mensal `MMYYYY`, anual `YYYY`; colisão com mesmo hash é duplicata, conteúdo diferente recebe `_02`, `_03`. | CL-04 | O padrão completo das 19 nomenclaturas e árvore final ainda precisa de confirmação do responsável. |
| D-27 | Registrada em CL-04 | Automático só com CNPJ único no documento, regra determinística válida e confiança ≥98% em cada campo obrigatório; PDF com múltiplos documentos vai sempre para revisão. | CL-04 | Meta e amostra de aceite precisam ser aprovadas; confiança numérica da IA não equivale a precisão medida. |
| D-28 | Registrada em CL-04 | Limite proposto de 50 MB por anexo, PDF até 100 páginas; PDF/JPG/PNG/WebP/XLSX/CSV/TXT; protegido por senha rejeitado. | CL-04 | Confirmar limites/formato por operação e dimensionar extração/antimalware antes de publicar. |
| D-29 | Registrada | Checklist de recebidos só muda após arquivamento confirmado; WhatsApp de pendências é frente posterior, sem provedor, consentimento, modelo ou custo definidos. | CL-04; [plano inicial](docs/plano-triagem-documental.md) | Mensageria não integra o primeiro recorte vendável sem decisão separada. |
| D-30 | Confirmada como método | A reunião de 11/09 é material de conversa, não especificação; itens “Confirme antes de mudar” devem ser respondidos pelo responsável, sem inventar arquivo, versão, prazo ou card. | CX-08 | Taxonomia, árvore, canais auxiliares e políticas permanecem perguntas quando a fonte não basta. |

## Integrações e operações adjacentes

| ID | Estado | Decisão / limite exato | Fonte | Consequência |
| --- | --- | --- | --- | --- |
| D-31 | Registrada | NFS-e Nacional (ADN) deve ser fonte de coleta para NFS-e, além de telas de custódia/classificação. | CL-03; `docs/cica-module-truth.md` | Não anunciar captura externa como pronta até existir cliente e homologação com certificado autorizado. |
| D-32 | Registrada | DTE e guias/DCTFWeb devem fazer chamadas reais à central Integra, com autorização de consumo, estados e resultado persistido, sem depender de planilha. | CX-03; CX-05 | Testes de cliente com transporte simulado não substituem piloto Serpro. |
| D-33 | Registrada | Siescon não tem adaptador homologado nem mecanismo público de leitura confirmado; não pedir segredo nem anunciar conexão ativa. | [descoberta Siescon](docs/cica-siescon-discovery.md) | Obter documentação e homologação pelo fornecedor antes de liberar. |
| D-34 | Substituída por D-43 em 15/09 | A avaliação anterior cogitava tirar Jornadas da oferta paga e ainda discutia se manteria o quadro. | conversa anterior; [avaliação](docs/planejamento/avaliacao-jornadas.md) | A ordem posterior é mais específica: Triagem substitui Jornadas no produto. |
| D-35 | Registrada | Conciliação OFX × Domínio cruza empresa/data/valor e pede confirmação humana da ambiguidade; Radar reúne publicações oficiais, sem cálculo de impacto por cliente. | [verdade dos módulos](docs/cica-module-truth.md) | Aceite operacional precisa verificar fontes, falhas e carteira real. |
| D-36 | Confirmada em 15/09 | O responsável pediu arquivos `.md` atualizados com todas as decisões tomadas nesta conversa e revisão completa do README principal. | Pedido direto nesta conversa | A memória em `docs/planejamento/`, o README e o registro de execução devem evoluir junto com a implementação, separando confirmação, proposta e evidência. |
| D-37 | Padrão técnico local; origem do nome pendente | A CICA definiu o componente de empresa `Nome [Domínio código]` para cumprir a delegação D-25; o código é obrigatório e preservado. A função ainda não grava no Windows. | D-25; [padrão e fonte Microsoft](docs/planejamento/padrao-pastas-windows.md) | Confirmar se o nome vem da CICA ou do Domínio e o comportamento ao renomear; validar raiz e agente antes de ativar. |
| D-38 | Confirmada em 15/09 | A Central Integra Contador deve ser uma área de trabalho real, começando pela Caixa Postal DTE: localizar por empresa/estado, acompanhar consultas, abrir o teor e registrar a consequência jurídica com evidência na própria tela. A mesma revisão crítica deve seguir nas demais ferramentas. | pedidos diretos do responsável nesta conversa | Caixa de trabalho, resumo sem efeito jurídico, confirmação explícita da abertura, histórico, falha e próximo passo; não declarar os outros serviços da Central como prontos por terem apenas código de integração. |
| D-39 | Confirmada em 15/09 | A ciência oficial por abertura do DTE é permitida a dono/administrador e a colaborador no perfil **Operador** com permissão específica. | resposta direta do responsável nesta conversa | Gestor, auditor, financeiro e suporte não recebem ciência por permissão genérica; a equipe precisa exibir e auditar o privilégio específico. |
| D-40 | Confirmada em 15/09 | A entrada da **Central Integra Contador** deve oferecer exatamente três ferramentas iniciais para escolha do operador: **Caixa DTE, Parcelamentos e DCTFWeb**. O responsável escolheu DCTFWeb como terceira, substituindo a proposta SITFIS. | respostas diretas do responsável nesta conversa | Navegação pela Central; nenhuma ferramenta pode aparentar consulta Serpro homologada por ter apenas tela ou dados locais. |
| D-41 | Confirmada em 15/09 | Na preparação de consultas DTE, o operador precisa poder selecionar todas as empresas **aptas** do escopo, selecionar os resultados da busca e limpar a seleção, vendo a quantidade exata de chamadas Serpro antes de autorizar o envio. | pedido direto do responsável e revisão da tela com 562 empresas | Seleção deve incluir aptas além das 20 linhas inicialmente exibidas; empresas sem CNPJ válido não podem ser cobradas nem enviadas. Na carteira Fedrizzi são 554 aptas e 8 sem CNPJ. O preparo é local e a cobrança só pode seguir a autorização explícita. |
| D-42 | Confirmada em 15/09 | A terceira ferramenta inicial, **DCTFWeb**, deve permitir consultar a declaração, obter o recibo e emitir guia. | resposta direta do responsável nesta conversa | Transmissão não faz parte do escopo inicial; `CONSDECCOMPLETA33`, `CONSRECIBO32` e `GERARGUIA31` exigem fluxo operacional e homologação Serpro. |
| D-43 | Confirmada em 15/09 | **Triagem de Arquivos substitui Jornadas em todo o produto.** Não existem contratos comerciais antigos de Jornadas. | ordem e esclarecimento direto do responsável nesta conversa | Tirar Jornadas de oferta, navegação, catálogo e rotas do escritório; preservar o schema legado sem anunciar ou abrir o quadro. Mensalidade da Triagem precisa de pesquisa e aprovação. |
| D-44 | Confirmada em 15/09 | A cobrança desejada é **mensalidade mínima por módulo + franquia de tokens própria + excedente automático até teto mensal aceito**. Um token CICA terá o **mesmo preço em todos os módulos**, com **consumo apenas em números inteiros**; cada operação queimará um peso diferente conforme custo/trabalho. O responsável rejeitou R$ 0,01 e indicou **R$ 0,05 como referência a pesquisar**, sem fechar tarifa. | respostas diretas do responsável nesta conversa; [pesquisa](docs/planejamento/precificacao-tokens-modulos.md) | Separar token comercial de token do Claude/Gmail; congelar preço/pesos/franquia/teto no contrato, reservar e liquidar por resultado, mostrar saldo e fatura por módulo. Valor final em R$ e pesos ainda não aprovados. |
| D-45 | Confirmada em 15/09 | Os pesos das operações **Integra Contador** devem sempre partir da **faixa mais cara vigente do Serpro** para cada serviço. Faixas mais baratas alcançadas depois pela Mewstack ampliam sua margem, sem redução automática do peso vendido ao escritório. | resposta direta do responsável nesta conversa; [tabela oficial](https://loja.serpro.gov.br/integra-contador/product/integracontador), aba “Preço” | A tabela oficial lida em 15/09 mostra **faixa 1: consulta R$ 0,24, emissão R$ 0,32 e declaração R$ 0,40**. Confirmar a categoria de cada código DTE/Parcelamentos/DCTFWeb antes de fixar peso por ação. |

## Decisões que não foram tomadas

Este registro não aprova **valor monetário do token, preços mínimos, pesos, franquias e teto padrão por módulo**, gasto de API, provedor SMTP, DNS de envio, retenção/exportação pós-contrato, termos finais, **custos e contratação da verificação Gmail pessoal**, catálogo documental de 19 tipos, caminhos Windows concretos, antimalware/OCR, provedor WhatsApp, integração automática BCB/RFB ou módulo “Open Files” do Domínio. Ver [dúvidas abertas](docs/planejamento/duvidas-abertas.md).


## Decisões confirmadas em 17/09/2026

Responsável: proprietário do projeto nesta conversa. Fonte: respostas e instruções diretas, seguidas da aprovação do plano e da restrição à etapa 00.

| ID | Assunto | Decisão | Fonte | Alcance / efeito |
|---|---|---|---|---|
| D-46 | Arquitetura | SaaS e IA centralizados na Mewstack; agente instalado no escritório. | Resposta “SaaS + IA central”. | Instalação completa no cliente não integra este plano; documentos Cobalchini não escolhem produção. |
| D-47 | IA inicial | Uso por API KEY agora; preservar Claude conforme D-16. | Pedido inicial e plano aprovado. | Aprovação de arquitetura não autoriza gasto nem fixa modelo comercial disponível. |
| D-48 | IA local | Consulta aos dados + ajuste do modelo com exemplos revisados. | Resposta “Consulta + ajuste do modelo”. | Não é treinamento de modelo do zero; preparar corpus, avaliação e publicação. |
| D-49 | Isolamento do aprendizado | Conhecimento, exemplos, correções e ajustes derivados dos clientes ficam restritos ao respectivo escritório; conhecimento geral pode ser compartilhado. | Resposta “Restrito por escritório”. | Não alimentar modelo comum com exemplos privados sem nova decisão explícita. |
| D-50 | API após migração | IA local como padrão após homologação; API como reserva autorizada, sujeita à política de dados e orçamento. | Resposta “Reserva autorizada”. | Resolve a escolha de rota da Q-10; critérios de virada ficam em Q-30. |
| D-51 | Aceite local para venda inicial | Pipeline local preparado e testado; treinamento e desempenho na máquina definitiva ficam para etapa posterior explícita. | Resposta “Pipeline pronto e testado”. | Etapa 13 não bloqueia venda por API; etapa 05 continua obrigatória e não equivale a treino real. |
| D-52 | Áreas do Domínio | Contábil, fiscal e folha na preparação da IA. | Resposta “Contábil + fiscal + folha”. | Não reduzir cobertura aos quatro grupos hoje consultados; não autoriza escrita no ERP. |
| D-53 | Disponibilidade Siescon | Responsável confirmou servidor/banco disponível para viabilizar descoberta autorizada. | Resposta “Servidor/banco disponível”. | Não prova acesso já concedido, schema, versão, credenciais recebidas ou homologação. |
| D-54 | Operações Siescon | Leitura + exportação revisada; gravação direta não aprovada. | Resposta “Leitura + exportação revisada”. | Homologar leitura e importação do arquivo no Siescon; não inventar layout/API. |
| D-55 | Autonomia | Automação por regras aprovadas e qualidade medida; exceções seguem para revisão. | Resposta “Automação por regras aprovadas”. | Não aprova limiares específicos, autoaprovação irrestrita ou ciência DTE automática. |
| D-56 | Sem presunções | “nunca assume nada, o que for preciso tu me pergunta aqui”. | Mensagem direta do responsável. | Consultar evidência existente; perguntar apenas decisão ausente/conflito concreto. |
| D-57 | Memória e execução | Documentar tudo que for decidido; criar etapas para terminar o projeto e um prompt por etapa. | Mensagem direta e aprovação integral do plano. | Registro único; atualizar documentação junto da implementação; não reabrir decisões sem motivo. |
| D-58 | Plano aprovado | Plano de conclusão composto pelas etapas 00–13, com dependências e aceites registrados em PLANO-MESTRE.md. | Mensagem “PLEASE IMPLEMENT THIS PLAN” com plano integral. | Preservar todas as etapas, sem declarar o conjunto implementado. |
| D-59 | Localização da memória | Plano mestre e tudo que for validado devem ficar na raiz do repositório. | Mensagem “cola na raiz do repo”. | PLANO-MESTRE.md, DECISOES.md e VALIDACOES.md são os pontos de entrada; caminhos antigos apontam para eles. |
| D-60 | Escopo desta execução | “quero que tu faça apenas a primeira etapa agora”. | Última instrução do responsável em 17/09/2026. | Executar somente 00, primeira etapa do plano; não corrigir Ruff nem iniciar 01–13 nesta entrega. |
| D-61 | Fechamento de etapas | “nunca finaliza uma etapa se tiver algo pendente, me pede que eu faço”. | Mensagem direta do responsável em 17/09/2026. | Etapa com qualquer checklist, validação ou dependência pendente fica aberta e bloqueada; comunicar a ação concreta exigida do responsável antes de encerrá-la. |
| D-62 | Demonstração de download NFS-e | A área NFS-e deve oferecer download em lote para demonstração, separado por empresa no padrão de pastas Domínio: `Tomadas/CÓDIGO -/` e `Emitidas/CÓDIGO -/`. | Pedido direto do responsável em 18/09/2026, com correção posterior de “recebidas” para “emitidas”. | Implementar primeiro somente demonstração com dados fictícios e ZIP gerado sob demanda; não alegar escrita real nas pastas Windows, coleta ADN nem homologação do layout final. |
| D-63 | Classificação antes do download NFS-e | A demonstração deve permitir baixar todas as notas, editar ou definir acumulador antes do ZIP e tratar transitória com confiança zero. Toda nota classificada exige confiança superior a 95%. | Pedido direto do responsável em 18/09/2026. | Aplicar as regras no servidor para o ZIP de demonstração; usar manifesto no arquivo baixado e não gravar decisão fictícia no banco nem alegar classificação fiscal homologada. |

## Como registrar a próxima decisão

18/09/2026 — D-70: responsável solicitou “faz o próximo passo do plano” após os ajustes da demo. Retomar o primeiro item pendente do plano (etapa 01), preservando D-61: não encerrar com pendências. A restrição temporária de D-67 deixa de impedir essa retomada. O questionamento anterior sobre LlamaFactory não autoriza sua substituição nem confirma sua adoção; esclarecer Q-37 antes do build dependente.

18/09/2026 — D-71: diante de “faz o que for melhor pra ti”, manter LlamaFactory como ferramenta interna do runtime de ajuste local. A seleção técnica é `hiyouga/llamafactory@sha256:46b6969e444681829294ed1fce2c4e8848613e654b682dc0359ba94357a0267b`, imagem oficial fixada por digest. O runtime é somente de treinamento, sem porta exposta, credenciais, modelo baixado ou treino executado. Isso resolve Q-37 e não altera a IA inicial por API nem autoriza GPU, API paga ou egressão de dados.

18/09/2026 — D-72: Fedrizzi Contabilidade é o ambiente disponível para homologação; tudo nele está disponível para esse fim. O proprietário do projeto aprova cada módulo. Os acessos e amostras concretos serão solicitados e usados somente na etapa correspondente, por meio seguro, sem credenciais no chat. Isto resolve a disponibilidade de ambiente em Q-28 e o responsável pelo aceite em Q-30; não define métricas, tamanho de amostra, janelas de operação nem autoriza chamadas cobradas.

18/09/2026 — D-73: aprovados os critérios recomendados de liberação por módulo. Cada fluxo automatizado terá amostra de 200 itens revisados pelo proprietário; classificação automática exige precisão medida mínima de 95%; sincronização e dados exigem zero duplicidade, associação à empresa errada ou vazamento entre escritórios; após queda de rede, worker ou agente, retomada sem perda em até 15 minutos; restauração de banco e documentos conferida em até 4 horas; consultas/processamentos por empresa em até 5 minutos, salvo dependência externa registrada; exportação só é aprovada após importação e conferência no sistema de destino. A disponibilidade Fedrizzi permanece em D-72; cada chamada cobrada requer autorização específica imediatamente antes.

18/09/2026 — D-74: confirmado no ambiente local que Fedrizzi já possui conector Domínio `direct_odbc` e fonte Domínio local em estado `ready`; a sincronização já está configurada. Não solicitar novamente DSN, driver, servidor ou acesso para esse conector. A etapa 03 deve usar essa conexão existente para sua homologação, sem expor o DSN ou seus dados. A disponibilidade de outros conectores em Q-28 será tratada somente nas respectivas etapas.

18/09/2026 — D-75: diante de qualquer pendência, o executor deve apresentar proativamente o que precisa ser decidido ou disponibilizado, o impacto, uma recomendação objetiva e como o responsável pode executar ou fornecer o necessário. Não encerrar a comunicação apenas informando o bloqueio. Registrar a resposta recebida antes de implementar o comportamento dependente.

18/09/2026 — D-76: todas as regras, recomendações e propostas já documentadas no repositório passam a ser aprovadas para implementação; não reabrir itens apenas por estarem identificados como pendentes ou propostos. Quando um documento contiver somente uma pergunta sem valor, regra ou alternativa definida, levantar o fato técnico e trazer recomendação conforme D-75. Esta decisão não autoriza gasto, contratação, chamada cobrada ou publicação externa, que continuam exigindo confirmação específica. O e-mail de suporte oficial é `suporte@mewstack.com.br`.

18/09/2026 — D-77: configuração de SMTP, domínio/DNS de envio e homologação de entrega transacional ficam para a etapa 12, depois de existir ambiente de produção. Nesta fase, concluir somente templates, transporte configurável, testes locais e estados de falha; não pedir configuração SMTP nem antecipar envio externo.

18/09/2026 — D-78: Brevo será o provedor de e-mail transacional da CICA via SMTP. Configurar host, porta, credencial SMTP, remetente e autenticações do domínio somente na etapa 12, conforme D-77. Não criar conta, plano, crédito, campanha ou envio por esta decisão.

18/09/2026 — D-79: regras comerciais de acesso aprovadas conforme recomendações apresentadas e D-76. Após atraso confirmado, há 7 dias de carência; depois, somente leitura. Pagamento confirmado reativa acesso automaticamente; estorno ou disputa retorna a somente leitura. Somente leitura mantém consulta, documentos já arquivados, auditoria e exportação de dados próprios, bloqueando novas sincronizações, IA, downloads em lote novos, Serpro e consumo de tokens. Contrato manual é operado por Comercial ou Administrador Mewstack, com motivo e comprovante auditáveis. Competência fecha no dia 1, vencimento no dia 10; primeiro mês é proporcional e mudança de plano vale no próximo ciclo. Teste é de 14 dias, sem cartão e sem reinício por convite; contrato manual também pode usar o mesmo teste. Preços, franquias, pesos e tetos usam a tabela documental aprovada por D-76 e serão operacionalizados na etapa 10.

18/09/2026 — D-80: arquitetura definitiva recomendada e aprovada para o pacote Windows, conforme D-76. O serviço nativo .NET passa a ser o único serviço instalado e suportado: ele executará sincronização Domínio Local somente leitura, processamento de backup Domínio Web e arquivamento Windows. O agente Python permanece apenas como ferramenta de diagnóstico/migração temporária, sem nova instalação de produção. O pacote e as telas deixam a marca CICA e passam a CICA. A sincronização local deve usar consultas allowlisted, paginação/chave incremental e a API v2 autenticada por mTLS/HMAC; nunca SQL recebido remotamente ou escrita no banco Domínio. A decisão substitui a indecisão Q-32; a execução e homologação continuam na etapa 03.

18/09/2026 — D-69: responsável pediu pesquisar e simplificar a seleção de datas na demo. Solução de interface: digitação brasileira DD/MM/AAAA e atalhos de mês, preservando D-66 (competência ou emissão). Trata-se de escolha de implementação, não de nova regra fiscal.

| D-64 | Filtros da carteira NFS-e | A carteira deve filtrar por competência de emissão ou por intervalo de data de emissão; data de captura não é o filtro de trabalho nem a data principal da lista. O aviso técnico sobre XML fictício e pasta Windows deve sair da tela. | Pedido direto do responsável em 18/09/2026. | A competência é derivada da data de emissão enquanto não existir campo fiscal próprio homologado; não usar data de captura para filtrar. |
| D-65 | Download sem bloqueio na demonstração | O download de demonstração não deve bloquear o usuário. Nota sem acumulador entra como Transitória com confiança 0%; acumulador definido pelo contador entra no manifesto como decisão manual. Somente sugestão da IA com confiança acima de 95% aparece como classificação da IA. | Esclarecimento direto do responsável em 18/09/2026. | O manifesto distingue origem e confiança sem gravar a decisão fictícia no banco. |
| D-66 | Escolha do filtro NFS-e | Na demonstração, o usuário escolhe um único critério de período: competência de emissão ou intervalo de data de emissão. | Pedido direto do responsável em 18/09/2026. | A interface não combina os dois filtros; o critério inativo não restringe a carteira. |
| D-67 | Prioridade atual | A entrega atual fica limitada à demonstração NFS-e; os demais trabalhos serão retomados depois. | Pedido direto do responsável em 18/09/2026. | Não avançar etapas ou integrações fora da demonstração enquanto esta estiver sendo ajustada. |
| D-68 | Edição de acumulador na demonstração | Preencher o acumulador deve mudar imediatamente a linha para Classificada e identificar a decisão manual com confiança de 100%; limpar o campo restaura o estado exibido antes da edição. | Pedido direto do responsável em 18/09/2026. | O efeito é visual e entra no manifesto do ZIP; não persiste classificação fiscal fictícia. |

Acrescentar ID único, data, texto da escolha, responsável, fonte, etapa afetada, decisões substituídas e pendências restantes. Registrar antes de executar o comportamento dependente. Nunca copiar credenciais, certificados, dados de clientes ou conteúdo integral de conversas. Uma mudança de escopo posterior não reescreve silenciosamente o histórico. Custos exigem autorização específica imediatamente antes da ação.
18/09/2026 — D-81: toda dependência de site hospedado fica para a etapa 12: domínio público, HTTPS, certificado/CA do agente, DNS, SMTP real, pareamento externo e homologação contra produção. Antes disso, executar somente implementação, builds e validações locais, sem solicitar hospedagem antecipada.
18/09/2026 — D-82: a API oficial Domínio/Onvio passa a ser o caminho preferencial de integração. O backup Domínio Web permanece como contingência e sua homologação fica na etapa 12, junto do ambiente hospedado. A CICA implementará somente endpoints e escopos documentados e concedidos pela Thomson Reuters; não simulará leitura de contabilidade, fiscal ou folha como se fosse disponível na API pública. Enquanto a API oficial não conceder esses recursos, a leitura local autorizada do agente ODBC permanece necessária para essas áreas.

18/09/2026 — D-83: as limitações e capacidades da integração Domínio Web devem permanecer consolidadas em `docs/dominio-web-limitacoes-comerciais.md`, como fonte para a oferta e o site. A comunicação comercial deve distinguir API oficial, agente local e backup de contingência, sem prometer leitura completa ou sincronização automática do Domínio Web onde a documentação e a homologação não comprovarem isso. Esta decisão não altera D-82 nem libera publicação externa antes da etapa 12.
## D-84 — Destino Windows configurável por escritório

Data: 18/09/2026. Origem: responsável pelo projeto. Cada escritório define dentro da CICA a raiz Windows e seu formato de pastas para documentos aprovados. O formato usa somente variáveis controladas e pode conter subpastas. O serviço não usa unidades mapeadas; nesta fase a raiz deve ser um caminho local absoluto. UNC depende de conta de serviço e homologação específica antes de ser liberado. Cada trabalho guarda o destino relativo já resolvido, preservando a fila quando a configuração futura mudar.
## D-85 — Site como fonte de verdade do destino Windows

Data: 18/09/2026. Origem: responsável pelo projeto, ao exigir configuração por escritório dentro do site. A raiz e o formato de pastas são definidos pelo administrador no perfil do escritório. O agente pareado consulta somente essa configuração do seu escritório e atualiza a cópia DPAPI local. Nesta fase, aceitar somente caminhos locais absolutos; suporte a UNC fica para homologação posterior com conta de serviço e permissões explícitas.

## D-86 — Homologação operacional do agente no final

Data: 18/09/2026. Origem: responsável pelo projeto. A etapa 03 encerra a implementação e as validações locais do agente Windows e da integração Domínio. A execução no destino definitivo — instalação limpa com DSN/driver x64, pareamento HTTPS/mTLS, revogação, atualização distribuída, queda e retomada de rede, backup `.dom` autorizado e escrita documental na raiz Windows real — fica reunida na etapa 12, depois do deploy do site. Q-22 e Q-31 serão respondidas no contexto desse piloto; não antecipar caminho, conta de serviço, política de nome ou renomeação de pastas. Esta decisão complementa D-81/D-82 e não libera publicação, infraestrutura paga ou homologação comercial.

## D-87 — Dependências de produção concentradas na etapa final

Data: 18/09/2026. Origem: responsável pelo projeto. Toda atividade que dependa do site em produção fica para a etapa 12: deploy, domínio público, HTTPS/DNS, credenciais e consentimentos externos de produção, serviços hospedados, filas e storage implantados, pareamento de agentes, chamadas reais a provedores, pilotos com dados reais e homologação comercial. As etapas 01–11 devem concluir código, configuração sem segredos, testes locais/isolados, documentação e preparação dos fluxos. A transferência não autoriza criar infraestrutura, fazer chamadas cobradas, usar dados reais ou publicar o site; cada custo continua a exigir confirmação específica imediatamente antes.

## D-88 — Contrato comum de exportação contábil

Data: 18/09/2026. Origem: executor, autorizado como decisão de implementação por D-76. As exportações contábeis da CICA passam a escolher um destino registrado e versionado, em vez de presumir Domínio em toda a cadeia. O adaptador Domínio já existente é preservado. Siescon só poderá receber exportação após registrar seu layout revisado, adaptador e versão; até lá a solicitação é recusada de forma explícita, sem gerar arquivo, escrever no Siescon ou alegar compatibilidade. Isto implementa a generalização estrutural da etapa 04 sem inventar o contrato técnico de Q-33.

## D-89 — Metadados de escopo para conhecimento e treinamento

Data: 19/09/2026. Origem: executor, decisão de implementação autorizada por D-52 e D-76. Fontes de conhecimento e exemplos de treinamento passam a registrar, quando aplicável, empresa, período de referência e uma das áreas `contábil`, `fiscal`, `folha` ou `geral`. Registros existentes recebem o escopo geral e não são reenviados, reclassificados ou expostos. Uma fonte ligada a empresa só pode pertencer ao mesmo escritório; na recuperação de uma conversa por empresa, evidência daquela empresa tem precedência e nunca é recuperada para outra. Esta decisão estrutura o pipeline local da etapa 05 sem aprovar egressão, curadoria, teto, treinamento real ou publicação de modelo; Q-08, Q-09, Q-11 e Q-34 continuam abertos.

## D-90 — Proveniência de avaliação e adaptador local

Data: 19/09/2026. Origem: executor, decisão de implementação autorizada por D-48, D-51 e D-76. Quando uma versão local declarar um adaptador, ela deve registrar modelo base, versão do adaptador, hash SHA-256 do artefato e hash SHA-256 do manifesto/corpus. A avaliação correspondente deve registrar os mesmos valores, e a publicação recusa divergência. Registros históricos sem artefato continuam legíveis, mas não passam a alegar vínculo que não possuíam. A decisão cria somente o gate e a rastreabilidade local; não seleciona modelo, não inicia treino, não publica artefato nem substitui a aprovação humana de Q-34.

## D-91 — Separação imutável entre treino e avaliação

Data: 19/09/2026. Origem: executor, decisão de implementação autorizada por D-48, D-51 e D-76. Cada exemplo validado passa a ser classificado como `treino` ou `avaliação`; um exemplo não integra ambos os manifestos. Os registros anteriores permanecem no conjunto de treino para preservar o comportamento já existente. O job QLoRA exporta apenas o manifesto de treino; a avaliação deve registrar o hash do manifesto de avaliação quando houver artefato local declarado. A escolha, revisão humana e quantidade de exemplos de cada conjunto continuam dependentes de Q-34 e das métricas de D-73. Nenhum exemplo é reenviado, usado em treino ou avaliado por esta decisão.

## D-92 — Retorno controlado de adaptador local

Data: 19/09/2026. Origem: executor, decisão de implementação autorizada por D-50, D-51 e D-76. O retorno de versão ativa deve escolher uma versão anterior do mesmo escritório que tenha avaliação aprovada, corpus compatível e, quando declarar artefato, proveniência completa e idêntica. O retorno é auditado e não reexecuta treinamento, egressão ou download; a comparação de melhoria usada para publicação de uma versão nova não impede retornar a uma versão já aprovada. Esta decisão prepara o mecanismo local e não aprova a mudança de rota para IA local, que continua dependente da etapa 13, Q-30 e Q-34.

## D-93 — Cliente Asaas local, sem configuração nem despacho

Data: 19/09/2026. Origem: executor, decisão de implementação autorizada por
D-11, D-76 e D-87. O cliente técnico da Asaas usa explicitamente os ambientes
`sandbox` e `production`, o cabeçalho `access_token`, `externalReference` para
localizar clientes antes de criá-los e cobrança avulsa sem dados de cartão. A
chave é sempre recebida por injeção explícita; não será lida de configuração
local, impressa, criada ou usada nesta etapa. O transporte deve ser substituível
nos testes e não repetir automaticamente `POST` de cliente ou cobrança após
falha/resultado incerto. A ligação entre dados comerciais do escritório,
cliente Asaas, `PaymentAttempt` e ambiente autorizado continua para a etapa 12,
Q-08 e Q-28. Fontes: [autenticação Asaas](https://docs.asaas.com/docs/authentication),
[criar cliente](https://docs.asaas.com/reference/create-new-customer) e
[criar cobrança](https://docs.asaas.com/reference/create-new-payment), consultadas
em 19/09/2026. Esta decisão não autoriza chamada, custo, sandbox, produção ou
homologação.

## D-94 — Gate antecipado de identificadores pessoais no corpus local

Data: 21/09/2026. Origem: executor, decisão de implementação autorizada por
D-20, D-48, D-49, D-51 e D-76. Um exemplo de treino ou avaliação validado não
pode entrar no manifesto local quando pergunta, resposta ou referências
contiverem CPF, CNPJ ou e-mail reconhecíveis pelos mesmos padrões já recusados
pelo runner QLoRA. A exportação deve falhar antes de criar o artefato; não deve
alterar, mascarar ou reenviar o registro automaticamente, pois isso poderia
corromper evidência contábil. A anonimização permanece uma revisão humana
rastreável no registro de origem. A decisão antecipa um controle local de
privacidade e não autoriza curadoria Claude, egressão, treinamento, download de
modelo, publicação, dado de cliente ou custo. Q-08, Q-09, Q-11 e Q-34
continuam abertos.

## D-95 — Exportação de manifesto local sem sobrescrita

Data: 21/09/2026. Origem: executor, decisão de implementação autorizada por
D-48, D-51 e D-76. A exportação JSONL de treino ou avaliação deve recusar um
caminho de saída já existente e criar o novo arquivo exclusivamente, evitando
substituir silenciosamente um artefato que possa estar vinculado a uma avaliação
ou revisão. A regra vale apenas para o artefato local; não executa treino,
publicação, transferência de dados ou operação externa. Uma nova exportação usa
outro caminho depois de revisão humana do corpus.

## D-96 — Cobertura de certificados sem ocultação da carteira

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelas métricas de recuperação de D-73. Quando a tela de
certificados informar empresas ativas sem A1 válido, ela deve permitir percorrer
toda a carteira em páginas de 20 registros, em vez de mostrar apenas as 20
primeiras. A paginação da cobertura é independente da lista de certificados e
preserva os parâmetros já presentes na consulta; o seletor de demonstração usa
somente os itens visíveis nessa página. Esta decisão evita ocultação silenciosa
e não aprova certificado, coleta ADN, uso de A1 real, conexão externa, custo ou
homologação fiscal.

## D-97 — Ficha da empresa com históricos paginados por seção

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelas métricas de recuperação de D-73. A ficha de uma empresa deve
permitir percorrer todos os documentos NFS-e, revisões abertas e mensagens DTE
visíveis ao escritório. Cada seção usa sua própria página de 20 registros, sem
alterar as demais seções ou o parâmetro de retorno à carteira. Esta decisão
remove limites silenciosos de apresentação; não amplia permissões, não autoriza
consulta DTE, coleta ADN, certificado real, conexão externa, custo ou
homologação.

## D-98 — Auditoria de conciliação sem limite silencioso

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelas métricas de rastreabilidade de D-73. A auditoria de
conciliação deve permitir percorrer todos os eventos visíveis ao perfil já
autorizado em páginas de 100 registros, preservando o filtro de ação. A medida
é somente de apresentação e consulta: não altera o conteúdo imutável do evento,
permissões, arquivos financeiros, integrações, exportações, custo ou
homologação.

## D-99 — Radar da Reforma sem corte silencioso de alertas

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelas métricas de recuperação de D-73. A consulta do Radar deve
permitir percorrer todos os alertas de reforma e fiscal já visíveis ao
escritório, em páginas de 50 registros, preservando busca, fonte e tema. A
medida somente altera a apresentação da coleção local: não coleta fontes,
não valida publicação, não muda sua relevância, não abre URLs, não autoriza
integração, custo ou homologação.

## D-100 — Histórico de cobrança manual recuperável no console

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelas métricas de rastreabilidade de D-73. O console da plataforma
deve permitir percorrer todas as faturas já pertencentes ao escritório, em
páginas de 12 registros, em vez de limitar a exibição às 12 mais recentes. A
medida mantém o escopo de cada escritório e somente apresenta o histórico já
registrado: não cria cobrança, não altera valores, contratos, status,
integrações, credenciais, custo ou homologação Asaas.

## D-101 — Histórico DTE recuperável por página própria

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelas métricas de rastreabilidade de D-73. O histórico de resultados
das consultas DTE deve permitir percorrer todos os itens visíveis ao escritório
em páginas de 30 registros, sem interferir na paginação das mensagens DTE e
preservando os parâmetros correntes da tela. A medida somente apresenta o
histórico local já registrado: não prepara consulta, não autoriza consumo, não
chama Serpro, não altera resultado, permissão, cobrança, custo ou homologação.

## D-102 — Histórico de importações recuperável no onboarding

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelas métricas de rastreabilidade de D-73. O onboarding deve permitir
percorrer todos os lotes de importação já pertencentes ao escritório, em páginas
de 20 registros, em vez de exibir somente os oito mais recentes. A medida
preserva fonte e prévia selecionadas na navegação e somente apresenta histórico
local já registrado: não envia arquivo, não confirma lote, não altera dados,
permissão, integração, custo ou homologação Domínio.

## D-103 — Trilhas de processamento e exportação recuperáveis na Conciliação

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelas métricas de rastreabilidade de D-73. A Conciliação deve permitir
percorrer todos os processamentos e exportações já visíveis ao escritório, em
páginas independentes de 20 registros, em vez de limitar cada trilha aos 12 e 8
mais recentes. Cada navegação preserva os parâmetros correntes da tela e não
altera a outra trilha. A medida somente apresenta o histórico local existente:
não importa, reprocessa, exporta, baixa arquivo, chama ERP, altera permissões,
custo ou homologação.

## D-104 — Histórico completo recuperável no Copiloto

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelas métricas de rastreabilidade de D-73. O histórico de conversas
abertas do Copiloto deve permitir percorrer todos os itens já visíveis ao
escritório em páginas de 12 registros, em vez de limitar a interface às 12
conversas mais recentes. A seleção da conversa e a página do histórico devem
ser preservadas entre as navegações. A medida somente apresenta histórico local
já registrado: não cria cobrança, não altera valores, contratos, permissões,
integrações, credenciais, custo ou homologação.

## D-105 — Fechamentos adiados recuperáveis no console da plataforma

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelas métricas de rastreabilidade de D-73. O console da plataforma
deve permitir percorrer todos os fechamentos ainda adiados, em páginas de 30
registros, em vez de limitar a consulta às 30 ocorrências mais antigas. A
navegação deve preservar os parâmetros correntes da configuração. A medida
somente apresenta evidências locais já registradas: não executa fechamento, não
altera fatura, contrato, reserva, preço, permissão, integração, custo ou
homologação.

## D-106 — Atenção de egressão recuperável no detalhe do escritório

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelas métricas de rastreabilidade de D-73. O detalhe do escritório
no console da plataforma deve permitir percorrer todas as tentativas Claude que
ainda exigem verificação, em páginas de 20 registros, em vez de limitar a
consulta às 20 mais recentes. A navegação deve preservar os parâmetros correntes
do detalhe. A medida somente apresenta auditorias locais já registradas: não
repete chamada, libera ou liquida consumo, altera reserva, política, dado,
permissão, integração, custo ou homologação.

## D-107 — Decisão NFS-e restrita ao catálogo do escritório

Data: 21/09/2026. Origem: executor, decisão de implementação local autorizada
por D-55 e pelos critérios de rastreabilidade da etapa 07. Ao resolver uma
revisão NFS-e, o acumulador deve existir no catálogo da mesma empresa: regra
ativa e vigente para a data do documento ou código já observado no histórico
local da empresa. A tela deve sugerir esses códigos e recusar código inexistente
ou de outra empresa. A medida não infere tratamento fiscal, não cria regra,
lançamento, integração, custo ou homologação.
