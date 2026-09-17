# Revisão funcional pelo ponto de vista do contador — 16/09/2026

## Parecer

**As ferramentas atendem a necessidades reconhecíveis de um escritório contábil, mas o conjunto ainda não está pronto para ser considerado autoexplicativo de ponta a ponta.** Um contador experiente provavelmente consegue navegar, pesquisar e executar parte das ações depois que alguém configura o ambiente. A implantação sem ajuda e o tratamento de exceções ainda apresentam bloqueios importantes.

O problema principal é a distância entre **entender o nome da ferramenta** e **conseguir terminar o trabalho com segurança**. Há telas que pedem conferência sem mostrar os dados necessários, pendências sem saída operacional e estados técnicos que o usuário precisa interpretar sozinho.

Esta é uma avaliação heurística com navegação real e leitura de código. Não foram entrevistados contadores nem medidas taxas de sucesso com usuários. “Autonomia” abaixo é um julgamento fundamentado nos fluxos observados, não uma certificação de usabilidade ou de conformidade fiscal.

## Escopo e evidência

- Percorridas 18 telas-base do escritório em 1440 × 960 e 390 × 960, com 36 capturas, além de detalhes, diálogos e estados de resultado. Inspeção visual focada em NFS-e, configuração, Triagem, Conciliação, Parcelamentos, Copiloto e bloqueio DCTFWeb; não equivale a inspeção pixel a pixel das 36 capturas.
- Perfis: visitante da demonstração e proprietário de escritório sintético. Carteira adicional de 240 empresas e 2.945 apurações sintéticas. Habilitados módulos apenas nesse banco de QA para alcançar telas sem a simplificação da demo.
- Servidor `scripts/qa_ui_server.py`: bancos e arquivos isolados em `.tmp/ui-review`, conexões externas bloqueadas. Nenhuma chamada paga ou operação fiscal real.
- Avaliados: objetivo, entrada, vocabulário, decisão, resultado, próximo passo, recuperação e continuidade entre ferramentas.
- O painel interno da Mewstack, o site comercial e a homologação externa não integram este parecer de ferramentas do contador. Jornadas aparece no catálogo interno, mas está excluída da oferta e não tem rota em `hub/urls.py`; não foi tratada como ferramenta disponível ao usuário.
- A sessão demo já continha progresso de QA anterior. Contradições próprias da demo estão separadas dos problemas encontrados no fluxo operacional.

Evidência: [inventário renderizado](../../.playwright-mcp/functional-review/screens.json), [ações e estados observados](../../.playwright-mcp/functional-review/flows.json). As capturas usam somente dados sintéticos.

## Avaliação de todas as áreas acessíveis

“Boa para a tarefa simples” não significa homologação completa. “Parcial” significa que a entrada é compreensível, mas existem lacunas para terminar o trabalho. “Depende de ajuda” indica uma barreira concreta à autonomia.

| Ferramenta / área | Faz sentido para o contador? | Autonomia observada | Principal melhoria |
|---|---|---|---|
| Visão geral | Sim: organiza pendências da carteira | Parcial | Priorizar por prazo, impacto e responsável; deixar explícito o que precisa de ação hoje |
| Empresas e detalhe | Sim: pesquisar e localizar cliente é familiar | Boa para consulta; parcial para operação | Transformar o detalhe em ponto de acesso às tarefas da empresa; mensagens DTE e documentos listados nem sempre abrem o respectivo trabalho |
| Certificados | Sim: validade e ausência de A1 são claras | Parcial | Oferecer envio/substituição já vinculado à empresa; evitar a volta entre certificado → empresa → certificados |
| NFS-e Inteligente | Sim: coleta, classificação e exceções são úteis | Parcial | Colocar documentos e decisões antes da configuração da coleta; mostrar identificação fiscal legível |
| Revisão de NFS-e | Sim: decidir acumulador é uma tarefa real | Depende de consulta externa à tela | Mostrar nota legível, descrição do serviço e descrição do acumulador; permitir decisão fundamentada |
| Guias | Sim: empresa, competência e vencimento são familiares | Parcial | Distinguir valor calculado, documento oficial, emissão e eventual pagamento; completar alcance da fila |
| Consulta DCTFWeb / lote | Sim: conferir documentos antes de emitir é compreensível | Parcial; bloqueada no cenário sem contrato | Explicar as etapas por tarefa e oferecer saída direta para resolver bloqueio de contrato |
| Central Integra Contador | Sim como agrupador de rotinas | Boa para escolher uma ferramenta | Subordinar o nome do fornecedor às tarefas: mensagens, guias e parcelas |
| Caixa DTE | Sim; resumo separado da abertura é um ponto forte | Boa no caminho simples; parcial nas exceções | Associar acompanhamento, responsável e providência após leitura; oferecer canal acionável para retorno incerto |
| Parcelamentos | Sim para acordos e parcelas do Simples | Parcial | Percorrer toda a carteira, abrir resultado em posição perceptível e manter empresa/filtros |
| Conciliação OFX × Domínio | Sim; comparação é uma necessidade concreta | Depende de melhoria para concluir exceções | Dar saída aos sem correspondência, mostrar dados bancários suficientes e corrigir celular |
| Triagem de Arquivos | Sim: receber, identificar e arquivar documentos | Depende de melhoria na revisão | Permitir conferir o arquivo liberado e corrigir classificação antes de aprovar |
| Caixas de e-mail / destino | Sim como configuração da Triagem | Depende de TI no fluxo atual | Separar a autorização cotidiana das credenciais técnicas de aplicativo e da instalação do agente |
| Radar da Reforma | Sim como pesquisa de publicações | Boa como lista de leitura; parcial como ferramenta de trabalho | Explicitar para quem a publicação importa e permitir acompanhar sua análise |
| Copiloto | Sim; empresa e perguntas iniciais ajudam | Boa para iniciar; resultado real não homologado | Dar contexto de período e transformar referências em acesso à tarefa correspondente |
| Central de aprendizado | A utilidade não fica clara no estado vazio | Parcial | Explicar o que chegará para revisão, de onde vem e o que uma aprovação altera |
| Primeiros passos / importação | Necessária, mas mistura cadastro e preparação técnica | Depende de ajuda | Checklist acionável, caminho para quem trabalha sozinho e modelos de importação disponíveis |
| Integrações / consumo e contrato / equipe | Necessárias para administrar o escritório | Parcial | Separar conexão, habilitação operacional e contratação; explicar poderes de cada perfil e consumo na tarefa |

## Achados prioritários

### 1. Alta — a Triagem pede uma conferência que a própria tela não permite fazer

**Reproduzido:** abrir `DOCUMENTO_FICTICIO_1.xml`, em “Aguardando revisão”. A instrução pede conferir empresa, tipo, período e nome. A tela mostra metadados e nome aprovado, mas não mostra o período em campo próprio, não oferece alteração da classificação e não permite abrir o arquivo antes da aprovação. O download aparece somente depois do arquivamento. O template operacional tem a mesma limitação.

**Efeito para o contador:** quando a empresa ou o tipo estiver errado, as opções são aprovar informação inadequada, rejeitar ou depender de alguém. Não existe um caminho de correção dentro da revisão. Um arquivo já liberado pela segurança ainda não pode ser conferido visualmente nessa etapa.

**Mudança recomendada:** prévia/download protegido somente após a liberação de segurança; campos corrigíveis de empresa, tipo, competência e nome; prévia do destino; “Aprovar e arquivar” quando a operação puder ser concluída em uma etapa. Se preparação e execução precisarem permanecer separadas, explicar quem executa a segunda etapa e mostrar o encaminhamento.

**Aceite:** um contador recebe arquivo com empresa sugerida errada, confere o conteúdo, corrige os metadados, arquiva e encontra o arquivo sem recorrer à administração técnica.

Evidência: `src/apps/hub/templates/hub/triage_item.html:24` e `:28`; estados aprovados e arquivados em `flows.json`.

### 2. Alta — revisão de NFS-e tem pouca evidência para a decisão solicitada

**Reproduzido:** detalhe oferece código de serviço, referência da contraparte, acumulador numérico, confiança e download XML. Não apresenta a nota em formato legível com descrição, valores, prestador/tomador e competência. O acumulador é um campo de texto preenchido com a sugestão; não há busca por código + descrição na empresa.

O código confirma que a evidência exibida se limita a `service_code` e `counterparty_ref`. A gravação exige apenas acumulador não vazio; não valida nesse ponto a existência do código em um catálogo da empresa.

**Efeito:** o contador precisa conhecer o código de memória e abrir XML em outra ferramenta para fundamentar a decisão. “26% de confiança” não explica qual informação está faltando. O caminho convida a confirmar uma sugestão sem facilitar a conferência.

**Mudança:** apresentar dados fiscais legíveis, motivo específico da dúvida e catálogo de acumuladores da empresa, quando disponível. Diferenciar “Aceitar sugestão” de “Escolher outro acumulador”; registrar justificativa quando necessária. Manter o aviso existente de que a decisão não altera o Domínio e oferecer o próximo passo operacional.

**Aceite:** o contador explica por que escolheu um acumulador usando a evidência da tela e sabe o que ainda precisa fazer no sistema contábil.

Evidência: `src/apps/hub/views.py:5717`, `:5787`; `src/apps/hub/templates/hub/review_detail.html:16` e `:30`.

### 3. Alta — Conciliação não fecha o fluxo de quem ficou sem correspondência

**Reproduzido:** a fila contém “Sem correspondência” e a coluna de ação termina em “Sem candidato compatível”. Para um caso ambíguo, existe “Comparar candidatos”, mas a comparação é um seletor de texto, sem comparação detalhada lado a lado.

A lista mostra valor absoluto do movimento; não apresenta coluna própria de entrada/saída nem conta bancária. O arquivo de origem ajuda, mas não substitui essa identificação. O texto solicita conferir data, valor e histórico, enquanto a opção de candidato não apresenta a data e a referência do lançamento.

**Efeito:** o usuário identifica a pendência e não consegue encaminhá-la ou registrar como foi tratada. Quem opera várias contas precisa de contexto adicional para evitar associação errada.

**Mudança:** exibir banco/conta, direção e período, comparar movimento e lançamento de modo legível; criar tratamento explícito para ausência de correspondência, com reprocessamento após atualização dos dados e registro de providência. Isso não exige escrever automaticamente no Domínio.

**Aceite:** um movimento sem candidato consegue sair da fila por um caminho documentado e auditável, sem ser indevidamente marcado como conciliado.

Evidência: `src/apps/hub/templates/hub/reconciliation.html:23` e `:31`; `src/apps/hub/views.py:4146`.

### 4. Alta — no celular, parte da Conciliação fica fora da área visível

**Reproduzido em 390 px:** tabela com largura de 650 px dentro de um contêiner de 341 px; status e parte do botão ficam cortados. A regra genérica `.data-table-wrap table` mantém largura mínima e vence a regra específica da Conciliação. O corpo esconde a sobra; por isso uma sonda que verifica somente a largura total da página informa falsamente ausência de problema.

**Mudança:** corrigir a especificidade e o dimensionamento dos cartões móveis; validar limites de cada controle, não apenas a rolagem do documento.

**Aceite:** nome, valor, situação e ação completos em 375/390 px, com teclado e foco visível.

Evidência: [captura](../../.playwright-mcp/functional-review/demo-7-390.png); `src/apps/hub/static/hub/operations.css:677`; regra móvel em `src/apps/hub/static/hub/hub.css:1`.

### 5. Alta — existem filas limitadas sem navegação para os demais registros

**Reproduzido:** Parcelamentos exibe 100 de 240 empresas e não apresenta próxima página. A pesquisa pode localizar uma empresa específica, mas não permite percorrer sistematicamente a carteira inteira.

**Confirmado também por código:** documentos NFS-e, guias oficiais e conciliações cortam a consulta em 100 registros, sem paginação correspondente nos templates. A lista de empresas sem certificado limita-se a 20. Não confundir com apurações do Domínio, revisões, certificados cadastrados, DTE e Triagem, que já têm paginação.

**Efeito:** filas com total maior podem parecer completas, e empresas ou pendências ficam fora da rotina de conferência.

**Mudança:** paginação e “exibindo X–Y de Z” em todas as filas; filtros e contexto mantidos na navegação; distinguir seleção da página de seleção de toda a carteira.

Evidência: `src/apps/hub/views.py:1727`, `:2077`, `:3226`, `:4108`, `:5602`. Volume reproduzido no navegador somente para Parcelamentos; os outros cortes foram constatados por código.

### 6. Alta — Primeiros passos não conduz uma pessoa sozinha até o uso

**Reproduzido:** os seis itens do checklist são texto sem links. “Confirmar escritório” e “Ativar MFA” não levam às respectivas ações. “Convidar sua equipe” permanece como pendência para um escritório de uma pessoa. “Configurar os módulos” aparece concluído quando existe qualquer módulo habilitado, mesmo sem conexão funcional.

Na importação manual, a instrução manda usar modelos CSV/XLSX, mas não oferece download ou especificação de colunas nessa tela. A prévia, pelo template, apresenta arquivo, tipo e quantidade; não permite conferir linhas ou distinguir o que será criado e atualizado. No caminho Domínio Local, o ambiente inspecionado mostra “Instalador aguardando publicação”. Essa indisponibilidade depende da configuração da instalação e não deve ser generalizada para todos os ambientes.

**Mudança:** cada pendência deve abrir sua ação; tratar equipe como opcional para quem trabalha sozinho; distinguir módulo contratado/habilitado de pronto para operar. Disponibilizar modelos preenchidos, validação por linha e prévia real da importação. Mostrar dependências de instalação antes de prometer que o caminho está pronto.

**Aceite:** contador sem equipe cadastra a primeira empresa e conclui uma primeira tarefa, sem interpretar DSN, procurar modelo fora do produto ou ver etapa falsamente concluída.

Evidência: `src/apps/hub/templates/hub/setup.html:6`, `:19`, `:24`, `:36`; `src/apps/hub/views.py:5962`.

### 7. Alta — conectar e-mail exige conhecimento de administrador de TI

**Reproduzido fora da demo:** “Conectar com Microsoft” exige criar aplicativo no Entra, permissões Graph, Client ID, Client Secret e Tenant ID. Google Workspace segue um caminho de registro OAuth. No ambiente local, falta ainda o endereço de retorno configurado pela Mewstack.

**Efeito:** alguém pode saber usar e-mail e contabilidade e ainda assim não conseguir configurar a ferramenta. O passo a passo técnico é útil para TI, mas não transforma essa configuração em uma tarefa intuitiva para o contador.

**Mudança:** preparar a integração da plataforma para permitir autorização normal do provedor quando viável; oferecer explicitamente o caminho “Preciso do administrador de TI”, com instruções e diagnóstico compartilháveis. Manter os detalhes técnicos numa área apropriada. Mostrar separadamente caixa autorizada, leitura ativada e processamento pronto.

Evidência: `src/apps/hub/templates/hub/triage_connections.html:15` e `:38`; [tela operacional](../../.playwright-mcp/functional-review/owner-caixas.png). Nenhuma configuração externa foi executada.

### 8. Alta — “Guias oficiais / Valor” pode ser interpretado como valor oficial, embora seja cálculo local

**Confirmado por código:** a lista usa o título “Guias oficiais”, descrição de resultados conferidos na fonte oficial e coluna genérica “Valor”. O valor vem de `guide.amount_cents`. No detalhe operacional, esse mesmo valor é identificado como “Soma calculada no Domínio”, e o texto manda conferir o valor oficial no DARF.

**Efeito:** o usuário precisa descobrir só no detalhe que o número da lista não necessariamente representa o valor do documento devolvido pelo fornecedor. A distinção está implementada parcialmente, mas deve existir onde o valor é visto primeiro.

**Mudança:** rotular a origem do valor na lista e no detalhe; apresentar valor oficial somente quando efetivamente extraído/confirmado; mostrar divergência sem inferir igualdade. Diferenciar claramente emissão de pagamento: a tela inspecionada acompanha emissão, não prova quitação.

Evidência: `src/apps/hub/templates/hub/guides_center.html:61`, `src/apps/hub/templates/hub/guide_detail.html:10`, `src/apps/hub/views.py:2079`. Não foi constatada uma divergência fiscal real; o achado é a ambiguidade da interface e de sua fonte de dados.

### 9. Média — bloqueios explicam o problema, mas deixam a recuperação fora do fluxo

**Reproduzido:** DCTFWeb sem contrato apresenta duas consultas indisponíveis e depois pede obter os dois documentos. Não oferece na própria mensagem a ação para regularizar o acesso. Em Parcelamentos, o contador recebe “Configure as credenciais Serpro da Mewstack”. Na quarentena, é informado de que não pode abrir o arquivo, mas não vê quem resolverá a falha de varredura.

**Código:** abertura DTE com retorno incerto pede aguardar conferência da Mewstack, sem ação contextual de acompanhamento ou suporte. Esse estado específico foi revisado em código, não reproduzido com o Serpro.

**Mudança:** mensagem com causa compreensível, responsável e próxima ação: “Pedir ativação ao administrador”, “Ver contrato”, “Acompanhar verificação”, ou suporte com identificação do caso. Não incentivar repetição de chamada com resultado incerto.

Evidência: [DCTFWeb bloqueada](../../.playwright-mcp/functional-review/dctfweb-blocked.png); `src/apps/hub/templates/hub/dctfweb_consult.html:37`, `src/apps/hub/templates/hub/parcelamentos.html:7`, `src/apps/hub/templates/hub/dte_message_detail.html:22`.

### 10. Média — o contexto da tarefa se perde entre listas e detalhes

Parcelamentos abre a empresa depois de toda a tabela, sem âncora no link ou transferência explícita de foco. Em carteira longa, a primeira parte da tela permanece praticamente igual. O detalhe vazio manda voltar à tabela para consultar a empresa. O link de abertura também elimina a pesquisa atual.

O detalhe de empresa lista mensagens DTE sem link para o teor e não reúne as demais rotinas por competência. Certificados ausentes levam à empresa, que por sua vez manda retornar aos certificados para enviar o A1.

**Mudança:** detalhe dedicado ou painel com foco perceptível; preservar filtros e retorno; abrir envio de certificado com a empresa preenchida; oferecer atalhos contextualizados para guias, DTE, documentos e conciliação.

Evidência: `src/apps/hub/templates/hub/parcelamentos.html:15` e `:20`; `src/apps/hub/templates/hub/company_detail.html:61` e `:66`.

### 11. Média — a linguagem ainda obriga o usuário a conhecer a implementação

Exemplos observados: `Checkpoint`, hash em destaque, `DCTFWEB.DECLARACAO_COMPLETA`, “O servidor relê a apuração”, “cópia persistida”, “artefatos”, “Confirmar N tokens”. Esses termos ocupam espaço em decisões que o contador pensa como conferir nota, obter recibo, emitir guia ou arquivar documento.

**Mudança:** ação principal com verbo e objeto; custo e efeito como informação de confirmação. Ex.: “Obter recibo — usa N tokens, sem excedente”; “Último documento recebido” no lugar de checkpoint; detalhes de identificação técnica em uma área expansível.

As siglas que pertencem ao trabalho, como DCTFWeb, DAS, OFX e acumulador do Domínio, podem permanecer, com ajuda contextual quando necessária. A simplificação deve preservar a precisão.

Evidência: `src/apps/hub/templates/hub/nfse_center.html:28`, `src/apps/hub/templates/hub/dctfweb_consult.html:23`, `src/apps/hub/templates/hub/dctfweb_bulk.html:19`.

### 12. Média — Radar e Copiloto ajudam a consultar, mas ainda deixam trabalho de interpretação

O Radar apresenta título, fonte, data e link. É compreensível como lista de publicações; a tela não explica impacto na carteira nem permite registrar leitura/providência. Recomenda-se contexto de aplicação, vigência quando verificada e acompanhamento, sem produzir recomendações fiscais sem evidência.

No Copiloto, escolher a empresa e usar uma pergunta sugerida é simples. Porém “Riscos do período” preenche “Resuma os riscos deste período” sem definir o período. “Classificação” não identifica um documento. As referências da resposta são exibidas como texto no template, sem ligação direta à tarefa operacional.

**Mudança:** pedir ou apresentar explicitamente o contexto necessário, indicar limites dos dados e permitir abrir a origem relacionada à resposta. Preservar a distinção entre consulta e alteração no sistema contábil.

Evidência: `src/apps/hub/templates/hub/reform.html:37`; `src/apps/intelligence/templates/intelligence/assistant.html:77`, `:108`. Resposta do Copiloto testada somente na demonstração, sem provedor de IA real.

### 13. Média — a demonstração não mantém todos os resumos coerentes com as decisões

**Reproduzido somente na demo:** após confirmar uma correspondência, o item sai da fila de atenção, mas o contador “Conciliados” permanece zero nessa visualização. O código calcula os resumos sobre a lista já filtrada. Após consultar Parcelamentos, a empresa continua “Nunca consultada / Sem leitura”, embora seu detalhe passe a mostrar acordo. Revisões resolvidas na sessão não se refletem de forma consistente nos números de NFS-e.

**Efeito:** quem experimenta o produto não sabe se o clique funcionou ou se a operação se perdeu. Isso compromete justamente o aprendizado sem ajuda.

**Mudança:** todos os cartões, listas e detalhes devem usar a mesma projeção do estado da sessão. Retestar também certificado simulado → coleta NFS-e.

Evidência: `flows.json`; `src/apps/hub/views.py:4069`. Não atribuir esses comportamentos à operação real sem teste próprio.

## O que já funciona bem

- Nomes das rotinas principais reconhecíveis, pesquisa por empresa/código e identificação do escritório ativo.
- Separação explícita entre resumo DTE e ação de abrir o teor; consequência apresentada antes da confirmação. A avaliação é de comunicação de interface, não de validação jurídica.
- Demonstração identifica dados fictícios e ausência de efeito fiscal/cobrança.
- Guias e Triagem chegam a estados de resultado com feedback; a Triagem mantém histórico das etapas.
- Conciliação e revisão informam que não escrevem no Domínio. Essa transparência deve ser preservada.
- Menu móvel responde a Escape e devolve foco ao acionador; campos de cadastro têm foco visível. Importação de OFX inválido mantém o diálogo aberto, focaliza o resumo e mostra erro junto do arquivo.
- Busca sem resultados em Empresas oferece “Ver todas”. A Conciliação vazia oferece importação do primeiro extrato. São exemplos melhores do que um zero sem explicação.

## Ordem sugerida de trabalho

1. **Completar a decisão:** revisão NFS-e, correção/visualização da Triagem, tratamento de conciliação sem candidato, origem dos valores das guias.
2. **Garantir alcance:** corrigir Conciliação móvel e paginação das filas truncadas; preservar contexto ao abrir detalhes.
3. **Viabilizar o primeiro uso:** checklist acionável, modelos e prévia de importação, caminho de implantação com responsabilidade clara para TI/Mewstack.
4. **Aprimorar produtividade:** prioridades por prazo, tarefas por empresa/competência, linguagem orientada à ação, Radar e Copiloto ligados à operação.
5. **Corrigir coerência da demo:** confirmar uma ação e observar imediatamente o mesmo resultado em todas as telas relacionadas.

Não recomendo iniciar por um redesenho visual amplo. A identidade atual pode ser preservada; o maior ganho vem de completar os caminhos de trabalho.

## Validação e limites

Exercitados no Playwright MCP nesta revisão: navegação das ferramentas; pesquisa sem resultado; abertura de detalhes; confirmação fictícia de revisão; aprovação e arquivamento fictício; confirmação de correspondência; abertura fictícia DTE; consulta fictícia de Parcelamentos; emissão fictícia DCTFWeb até a tela de resultado; pergunta sugerida e resposta fictícia do Copiloto; seleção de fonte manual/local; erro com arquivo OFX inválido; menu móvel, Escape e foco de formulário.

O console consultado durante a navegação demo registrou zero erros. Não significa ausência de erro em todos os contextos. A consulta direta ao Copiloto do escritório não-demo retornou 404 porque a liberação desse serviço estava desativada; o menu desse escritório também o omitia.

O transporte Playwright encerrou durante a tentativa final de downloads (`Transport closed`). **Downloads e emissão final de DAS da demonstração não foram confirmados por esse último teste.** Os links de download foram observados em telas anteriores. O navegador de QA foi encerrado por processo identificado após falha do comando de fechamento, incluindo os contextos usados nesta tarefa.

Não validados nesta revisão: emissão/ciência reais; contratos e tarifas reais; conexão OAuth/IMAP real; agente Windows real; IA paga; arquivo OFX válido até conciliação completa; importação válida até gravação; todos os estados de rede lenta, sessão expirada e retorno parcial; leitor de tela e contraste exaustivo. Nenhum desses pontos foi considerado aprovado por inferência. Não houve alteração de código da aplicação nem execução da suíte completa nesta revisão.

### Diretrizes e referências consultadas

Aplicadas `ui-ux-pro-max` e `web-design-guidelines`, com consulta à [fonte atual das diretrizes Vercel](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md). Revisão dos grupos aplicáveis: semântica, foco, formulários, feedback, navegação/estado, conteúdo, responsividade, movimento e tema. Sem mudança de UI nesta tarefa; os achados ficam como diagnóstico. Exemplos de violações materiais: conteúdo móvel cortado, recuperação sem próxima ação e rótulos de ação excessivamente técnicos.

Buscas locais: produto SaaS contábil, onboarding e recuperação de erro. Não houve correspondência verificada nas duas buscas de stack `html-tailwind`; Django Templates/CSS/JS e as diretrizes web foram a evidência de implementação. Não foi imposta uma stack diferente.

| Referência | Padrão usado para avaliar / recomendar |
|---|---|
| Watermelon UI MCP — catálogo e Astrix Dashboard | Separar configuração, acompanhamento e fila de classificação; consulta ao catálogo, sem copiar componentes |
| [Refero](https://refero.design/) | Tentativa de pesquisa como fonte principal; sem resultados/fluxos utilizáveis nesta sessão, não contado como interface inspecionada |
| [SaaSFrame / Wise](https://www.saasframe.io/saas/wise) | Referência de sequência entre seleção, revisão e resultado; previews públicos, sem acesso aos fluxos completos pagos |
| [TaxDome — pipelines](https://help.taxdome.com/article/1828-automate-your-processes) | Trabalho vinculado ao cliente, etapas e conclusão; apoio à recomendação de continuidade operacional |
| [Karbon — solicitações ao cliente](https://help.karbonhq.com/en/articles/1524439-overview-of-client-requests) | Contexto de trabalho e feedback de conclusão; consultado via resultado público indexado, abertura integral retornou 403 |

Essas referências apoiam as recomendações de fluxo; não comprovam requisitos da contabilidade brasileira. Nenhuma composição visual foi implementada nesta revisão.

## Como confirmar a autonomia com contadores

Rodar uma sessão moderada com contadores que não conhecem o produto, sem ensinar o caminho antes. Incluir alguém que trabalha sozinho. Usar tarefas concretas: cadastrar/importar uma empresa; localizar uma pendência; decidir NFS-e com acumulador diferente; corrigir arquivo classificado na empresa errada; tratar um movimento sem candidato; obter uma guia de determinada competência; explicar o efeito de abrir uma mensagem DTE; retomar uma operação bloqueada.

Registrar conclusão sem ajuda, pedidos de explicação, caminhos errados, erros de decisão e capacidade de explicar o resultado. Como critério proposto de aceite, exigir ausência de erro crítico e sucesso sem instrução na maioria das tarefas essenciais; definir o limiar e a amostra antes do teste. O teste precisa avaliar o que a pessoa entendeu, além de verificar se conseguiu clicar no botão.
