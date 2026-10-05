# CICA — auditoria de produto, funcionalidades e usabilidade

Data: 05/10/2026. Escopo autorizado: D-275. Evidência desta entrega: V-275.

Este documento fundamenta a atualização do [plano mestre](../../PLANO-MESTRE.md).
Não cria outro plano de execução, não aprova expansões e não declara o sistema homologado.
As etapas 00–13 continuam sendo a estrutura canônica. As propostas abaixo precisam do aceite
correspondente antes de alterar regras de produto, canais, dados ou cobrança.

## 1. Diagnóstico

O CICA já tem uma base funcional relevante e uma proposta coerente: centralizar o trabalho do
escritório por empresa, competência, responsável e evidência. NFS-e, atividades, fechamentos,
permissões e várias filas estão muito além de um protótipo. O melhor caminho é terminar os
percursos operacionais e comprovar seus resultados, preservando as melhorias recentes.

O sistema ainda não pode ser considerado integralmente concluído. Há três tipos diferentes de
pendência: funcionalidades presentes que precisam de homologação; encadeamentos de negócio que
ainda faltam no código; e dificuldades de uso que exigem observação com pessoas. Agrupar tudo em
“só falta testar” esconderia trabalho real, especialmente em Triagem, cobrança e Siescon.

As prioridades são: entregar o ciclo NFS-e até a conferência no Domínio; conectar as etapas da
Triagem; alinhar contratação e faturamento a D-109; tornar a configuração inicial um diagnóstico
verdadeiro; completar a curadoria da IA; homologar integrações e recuperação; medir o uso diário.

Não atribuí um percentual geral de conclusão. Número de telas, linhas de código e testes não
medem quanto do trabalho de um contador pode ser concluído. A conclusão será acompanhada por
capacidade e jornada, conforme os critérios do plano mestre.

## 2. Como a análise foi feita e o que ela não prova

| Evidência | Trabalho realizado | Limite |
|---|---|---|
| Documental | Leitura do plano, decisões, validações, etapas, dúvidas, inventários e runbooks; prevalência de decisões posteriores | Registros históricos são evidência datada; não substituem nova execução |
| Código | Rotas, modelos, serviços, tarefas, templates, estilos, JavaScript, testes, agente e configuração operacional | Ausência foi pesquisada em pontos produtivos e referências; análise estática não prova comportamento de produção |
| Navegador atual | Playwright MCP em servidor isolado na porta 8055, com SQLite e dados fictícios; egressão bloqueada | Não houve uso de certificado, e-mail, Serpro, IA paga, banco de cliente ou operação real |
| Cobertura renderizada | 27 URLs/recortes em 1440×960 e 390×844: 54 combinações; 25 telas responderam 200 e duas recusaram a demo com 403 em cada largura | Varredura de renderização e overflow; não são 54 jornadas completas |
| Percursos adicionais | Detalhe Triagem, atividade e empresa; filtro inválido, busca vazia; abertura de evidência/Tab/foco; Owner/Auditor/Operator sintéticos; menu móvel/Escape e paisagem | Não cobre todas as permissões, mutações, erros, loading, uploads ou recuperação |
| Pesquisa externa | Produtos contábeis brasileiros, ferramentas de gestão de escritórios, fontes oficiais e exemplos de fluxos | Documentação pública e páginas de produto; nenhuma sessão autenticada de concorrente |
| Usabilidade | Avaliação heurística pela tarefa do usuário e inspeção de telas | Ainda não houve entrevistas ou teste moderado com contadores nesta entrega |

Classificações usadas: **comprovado no código**, **observado no navegador**, **histórico documentado**,
**hipótese a testar** e **proposta nova**. Uma recomendação não equivale a uma decisão aprovada.

Na porta 8055, não houve overflow horizontal nem exceções JavaScript na varredura. O console
registrou os 403 esperados ao abrir configuração/auditoria da Conciliação pela demo. Essas páginas
não foram validadas por dentro. A inspeção preliminar da porta 8012 não integra a contagem: havia
um servidor QA anterior, e a análise foi repetida em porta exclusiva. Um 404 causado por URL
exploratória incorreta foi descartado como achado de produto. Não se presume defeito da demo
publicada a partir dos dados vazios vistos nessa instância anterior.

O cenário atual mostrou nove atividades em Meu trabalho. O auditor sintético abriu uma atividade
sem formulários de alteração. Um campo de evidência recebeu foco visível de 3 px por Tab. Filtro
de competência inválida retornou lista vazia com orientação; busca sem resultado ofereceu retorno.
Operator abriu/fechou o menu móvel com Escape; a lista em 844×390 não apresentou overflow.
A segurança funcional completa e a acessibilidade integral continuam sujeitas à matriz de aceite.
Todas as abas Playwright e os processos de QA abertos nesta tarefa foram encerrados.

Evidências locais:

- [Varredura renderizada em JSON](../../artifacts/product-audit-20261005-rendered.json).
- [Meu trabalho desktop](../../artifacts/product-audit-20261005-current-dashboard-1440.png).
- [NFS-e no celular](../../artifacts/product-audit-20261005-current-nfse-390.png).
- [Primeiros passos no celular](../../artifacts/product-audit-20261005-current-setup-390.png).
- [Triagem desktop](../../artifacts/product-audit-20261005-current-triagem-1440.png).
- [Detalhe de Triagem no celular](../../artifacts/product-audit-20261005-current-triagem-detail-390.png).
- [Ficha da empresa desktop](../../artifacts/product-audit-20261005-current-company-1440.png).

As quatro capturas de Meu trabalho, NFS-e, configuração e Triagem foram também abertas e
inspecionadas visualmente. A emissão de capturas adicionais não é tratada como teste completo.

## 3. O que está bom e deve ser preservado

1. **Estado de trabalho separado de estado fiscal.** Concluir uma tarefa não precisa significar
   transmitir obrigação, pagar guia ou fechar ERP. A central já tem estrutura para essas diferenças.
2. **Evidência antes de conclusão.** Fechamentos revalidam requisitos e podem reconhecer reabertura
   e fonte indisponível. Não é preciso reconstruir esse núcleo.
3. **Original preservado.** XML oficial e cópia derivada são separados; reclassificação conserva
   decisões humanas e histórico imutável. Isso é um diferencial operacional de confiança.
4. **Controle de carteira.** Permissões existem em telas, serviços, tarefas e downloads. Manter
   essa aplicação transversal ao criar busca, relatórios, notificações ou portal.
5. **Recuperação e idempotência.** Checkpoints NFS-e, prévias de importação, hashes, reservas e
   retornos incertos evitam repetir cegamente operações sensíveis.
6. **Filas que já orientam.** Meu trabalho, Atividades, Empresas, Guias, DTE e Parcelamentos
   apresentam contexto e próximas ações. Medir e aperfeiçoar é melhor que redesenhar tudo.
7. **Operação independente do ERP.** O escritório pode trabalhar com confirmação humana e
   documentos no modo independente, quando não há exigência de fonte integrada. Falha de uma
   fonte exigida não pode ser substituída por confirmação humana nem inventar estado oficial.
8. **Demo explicitamente fictícia.** Útil para aprender sem custo ou efeito fiscal. Sua cobertura
   deve continuar distinguida da operação real.

## 4. Situação funcional reconciliada

| Área | O que existe | Gap determinante | Evidência / vínculo |
|---|---|---|---|
| Acesso e administração | Cadastro, convites, recuperação, TOTP, papéis, carteira, suporte e parceiro interno | Entrega de e-mails e recuperação reais; explicação de papéis; confirmar versão publicada | Etapa 02; D-170, D-183, D-192; `accounts/mfa.py`, `hub/controlplane.py` |
| Empresas e contexto | Carteira com prioridade, busca, cadastro/edição, histórico e ficha consolidada | Reduzir detalhes técnicos secundários; provar sincronização e manutenção do cadastro real | D-272/273; V-273; `company_detail.html` |
| Central operacional | Agenda pessoal, carteira, gestão, modelos, recorrência, atribuição e evidências | Modelos reais, cobertura, calendário mais abrangente, handoffs e observações de ERP | D-109, D-125–162, D-268–271; `operations.py`, `recurrence.py` |
| Fechamentos | Requisitos por empresa/competência/área; pendência, reabertura e fonte não verificável | Semântica homologada das fontes e biblioteca operacional aprovada | V-271/272; `closing_dashboard.py`; Q-40 quando aplicável |
| NFS-e | ADN real, A1, NSU/checkpoints, lote, catálogo, classificação, derivados e relatórios | Importação/retorno Domínio Q-39; qualidade e esforço dos casos ambíguos; cobertura da fonte | D-189/274; V-274; etapas 07/12 |
| Certificados | Importação por metadados, lote e fila por empresa | Homologar renovação/revogação, erros e continuidade da coleta com dados autorizados | D-192–201; `certificates.html`, `nfse_sync.py` |
| Triagem | Caixas, ingestão, quarentena, estados, revisão, biblioteca, protocolo Windows | Encadear scan/extração/classificação/checklist; prévia e correção humana | Etapa 06; achados A-01/A-02 abaixo |
| DTE | Caixa, resumo, teor e autorização separada; resultado incerto e atividades | Homologação por operação Serpro, representação, ciência e recuperação | V-263; Q-28, D-143, D-155 |
| Guias/DCTFWeb | Consulta, documentos, emissão e histórico; consumo protegido | Contrato real, reemissão/atividade e inventário das transmissões já assumidas no checklist 08 | V-266; D-149, Q-40; implementar/homologar cada operação autorizada, sem inferir novas modalidades |
| Parcelamentos | PARCSN, empresa/acordo/parcela/DAS, lote e histórico | Serviço real, custo/resultado, retorno incerto e modalidades autorizadas | V-267; Q-36 antes de ampliar |
| Conciliação | OFX/CSV/XLSX/PDF, layouts, revisão, partidas, reversão, auditoria | OCR/layouts/amostras reais; exportação e importação no destino | V-257–260; Q-39/Q-33 |
| Folha | Fotografias agregadas, importação/prévia e comparação por competência | Fontes e critérios reais; jornada de divergência até tratamento | V-261/262; não é cálculo de folha nem cadastro individual |
| DRE e caixa | Mapas versionados, fotografias, cenários, fila de exportação | Descoberta/importação guiada; dados reais; renderer Node publicado e recuperação | V-120–136; `financial.py`, `reporting_exports.py` |
| Radar | Publicações, filtros, estado das fontes e vínculo humano à empresa | Cobertura declarada, atualização confiável e detecção de perda/alteração de fonte | V-264; `reform.py` |
| Copiloto | Contexto de empresa, fontes, respostas e histórico, feedback, exportação | Política de dados/custos, avaliação e serviço real; contexto temporal e recusa útil | Etapa 05; Q-08/09/11/34 |
| Aprendizado | Candidato, corpus, avaliação, publicação/rollback e runtime | Curadoria humana incompleta na UI; correção e evidência antes de aprovação | A-03; etapa 05; etapa 13 separada |
| Contratação e consumo | Contratos, capacidade, livros, faturas, webhook e operação manual | Implementar modelo D-109 e orquestrar pagamento/acesso | A-04; etapa 10 |
| Agente e Domínio | Serviço .NET de leitura local, backup e arquivo; leituras reais registradas | Instalação limpa, update, revogação, retomada e pastas reais | Etapa 03; D-80, V-198, D-185 |
| Siescon/Onvio | Tipos de fonte e bloqueio explícito onde não há capacidade | Siescon sem adaptador; Onvio só conforme endpoints/escopos concedidos | Q-33; D-82/83; não prometer paridade automática |
| Infraestrutura e suporte | Produção Fly+Neon, workers/cache, domínio/TLS, logs e runbooks | Restore atual medido, alarmes, carga, suporte e privacidade operacional | V-274; D-73; etapas 01/12 |

O último registro V-274 descreve release 45 e 1.106 testes/145 subtestes aprovados, com seis skips.
Esses números são históricos, não uma suíte reexecutada nesta auditoria. Há testes PostgreSQL
anteriores, inclusive concorrência; os skips recentes não significam que isso nunca foi testado.
Por outro lado, provas antigas não validam automaticamente a release atual.

Na fotografia V-274, 4.656 das 29.042 notas tinham correspondência segura e 24.386 permaneceram
em revisão. Isso mede **cobertura de correspondência nessa fotografia**, não precisão fiscal.
Os 95% de D-73 precisam ser medidos em amostra revisada; não se obtêm dividindo esses totais.

## 5. Achados que precisam gerar trabalho

Prioridade é relativa à liberação afetada. **Crítico do módulo** bloqueia vender aquele percurso,
mas não bloqueia automaticamente o produto NFS-e isolado de D-189.

### A-01 — Triagem não oferece a revisão que solicita

**Comprovado no código e observado no navegador.**
`src/apps/hub/templates/hub/triage_item.html:29` pede conferir empresa, tipo, período e nome, mas
o percurso oferece aprovar/rejeitar, sem editor ou visualização do conteúdo antes do arquivo.
`src/apps/hub/views.py:11440` recusa decisões sem empresa; não há fluxo ali para resolver o vínculo.
O download usa cópia interna já arquivada (`src/apps/triage/services.py:413`).

Consequência: a pessoa pode ter que aprovar o que não conseguiu conferir, ou depender de suporte
para uma correção comum. Entrega: prévia privada de arquivo seguro; empresa/tipo/período/nome
corrigíveis; motivo e histórico; destino previsto; botão específico para aprovar o resultado.
Arquivo em quarentena continua indisponível. **Crítico da Triagem.**

### A-02 — A cadeia automática da Triagem ainda tem peças desconectadas

**Comprovado por referências produtivas no código.** `src/apps/triage/tasks.py:34`/`:54` despacham
e leem caixas. `scan_quarantined_item` aparece apenas na definição em `security.py:108`; o scanner
termina em `AWAITING_EXTRACTION` (`:173`). Estados de extração aparecem na máquina de estados,
entrada manual e seed; não foi localizado despacho produtivo completo de extração/classificação.
`ChecklistExpectation`/`ChecklistEntry` aparecem nos modelos (`models.py:343`/`:373`), sem ponte
produtiva após arquivamento. `archive_internal` confirma cópia/hash/atividade, não esse checklist.

Entrega: jobs encadeados com idempotência, timeout, retry seguro, revisão de ambiguidade,
comprovação do destino e atualização do documento esperado. Não confundir funções unitárias
existentes com automação de ponta a ponta. **Crítico da Triagem.**

### A-03 — Aprendizado não fecha o ciclo de correção

**Comprovado no código; vazio observado.** `intelligence/templates/intelligence/learning.html:5`
diz que resposta útil cria candidato; `intelligence/services.py:825` cria após `NOT_HELPFUL`.
O conteúdo inicial é “Pendente de curadoria com evidência verificável” (`:835`), mas não existe
editor/fonte nessa tela antes de Aprovar; a view altera o estado (`views.py:520`). Não foi encontrada
entrada no menu/Copiloto e a listagem não pagina (`views.py:501`).

Entrega: explicar origem; permitir correção fundamentada, escopo e fonte; validação de completude;
pendentes/histórico paginados; acesso pelo papel correto. Aprovar exemplo, treinar, avaliar e
publicar devem ser atos diferentes. **Crítico para oferecer aprendizado assistido.**

### A-04 — Cobrança e acesso precisam corresponder a D-109

**Comprovado no código, com riscos específicos ainda a reproduzir.** D-109 substitui a estrutura
incompatível por capacidade de usuários/raízes CNPJ, IA em reais e Integra pelo custo efetivo sem
margem. `commercial_capacity.py:19`/`:33` conta capacidade, mas `platform/billing.py:307` ainda
fecha planos/tokens. Não foi localizado rateio completo do custo efetivo. Chamadas do AsaasClient
aparecem apenas no próprio cliente `platform/asaas.py`; `payments.py:62` atualiza o livro da
fatura/tentativa sem tocar acesso, e `tasks.py:36` encerra trial.

A mensalidade em `billing.py:389` não demonstra o primeiro mês proporcional; tratamento de
`PAYMENT_RECEIVED` em `payments.py:109` merece teste de evento antigo após disputa. São casos
de teste planejados, não incidentes de produção afirmados nesta auditoria.

Entrega: reconciliar decisões/snapshot contratual/medidor/fatura/tela; criar ponte de emissão e
pagamento; preservar manual; testar ordem, replay, estorno, carência e reativação. Q-01–06 não
devem ser perguntadas novamente como se D-79 não existisse; o modelo posterior D-109 prevalece
no que substituiu. Valores ausentes continuam dependências. **Crítico da escala comercial.**

### A-05 — Configuração inicial confunde existência com prontidão

**Comprovado no código.** `hub/views.py:13086` marca aplicação de modelos por qualquer modelo
ativo, sem exigir atribuição. O indicador de limites usa `UsageAllowance`, enquanto consumo
segue livros distintos. Hipótese adicional: checklist único pode oferecer modelos a cliente
exclusivo NFS-e, cuja rota não está disponível; reproduzir antes de corrigir.

Entrega: diagnóstico por capacidade contratada e papel; estados “não configurado”, “configurado”,
“testado” e “requer ação”; levar até primeira tarefa efetiva, não apenas completar oito marcações.
Validar escritório vazio, independente, Domínio local/Web e NFS-e isolado. **Alta.**

### A-06 — O calendário não cobre toda a rotina de um escritório

**Limite comprovado; expansão proposta.** `ActivityTemplate.Frequency` (`hub/models.py:2135`)
admite mensal/sob demanda; dias recorrentes vão de 1 a 28. Já existe sobrescrita por empresa
(`ActivityTemplateAssignment`, `:2191`), também limitada a 1–28. `operations.py:328` monta o
vencimento no mesmo mês da competência; `recurrence.py:35` materializa mensal. Atividades guardam
datas completas e uma guia pode trazer outro vencimento pela fonte; a limitação é da configuração
recorrente. Não foi encontrado editor auditável de prazo de atividade já gerada.

Proposta: separar competência de vencimento, permitir mês seguinte e alteração auditada de prazo;
priorizar periodicidades anuais/trimestrais, último dia e calendários de dias úteis, dependências
e substituição de responsável a partir das rotinas efetivas do piloto. A regra legal
de cada vencimento precisa de origem/versão/aprovação; não gerar um calendário tributário por
suposição. **Alta para a central integral; não nova condição para NFS-e isolado.**

### A-07 — Equipe perde praticidade em carteira grande

**Estrutura comprovada; impacto a medir.** `team.html:36`/`:45` renderiza empresas no convite e
novamente por pessoa editável. Para centenas de empresas, localizar e conferir seleção vira
trabalho repetitivo. `forms.py:175` apresenta perfis sem explicar os poderes no contexto.

Entrega: busca de carteira, seleção por recorte explícito, resumo das permissões e um editor de
pessoa por vez. Mostrar consequências de consulta, alteração, emissão/consumo e ciência. Testar
revogação durante trabalho em andamento. Não medir produtividade por contagem de tarefas. **Alta.**

### A-08 — Ajuda e terminologia precisam acompanhar o comportamento real

**Desalinhamentos estáticos e hipóteses.** `hub/onboarding.py:85` ensina Classificar sem explicar
as diferenças entre primeira classificação e correção com salvamento automático. A orientação
da Triagem exige conferência sem editor; `:59` promete ajuda em qualquer área, mas o catálogo é
limitado. Não remover um botão só porque outra variante usa autosave.

Entrega: ajuda por tarefa/papel e estado; tour curto demonstrando efeito real; glossário contextual;
diagnóstico que diga problema, impacto, próxima ação e quem pode fazê-la. Atualizar ajuda e teste
na mesma entrega da mudança funcional. **Alta.**

### A-09 — Integrações e console ainda têm recuperação incompleta

**Comprovado no código; percurso de erro do console ainda a reproduzir.** Erro Domínio persiste
`str(error)` e o apresenta em `settings.html:48`/`:73`, `views.py:13325`. Não foi demonstrado
vazamento de segredo; a lacuna comprovada é exposição de mensagem técnica sem tratamento uniforme.
`platform/views.py:182` devolve erro de cadastro, mas `tenants.html:7`/`:10` mantém modal oculto e
não repõe entrada. Lista de escritórios não tem busca/paginação (`views.py:210`).

Entrega: erro acionável com referência segura para suporte; estado e impacto de integração;
modal preservado/focado; pesquisa/paginação; suporte com limites e trilha. **Alta para operação.**

### A-10 — Relatórios existem, mas a chegada ao resultado precisa ser guiada

**Código existente; gaps de descoberta.** `company_detail.html:127`/`:139`/`:149` expõe relatórios,
fila e vazios; importação exige formatos e mapa, sem condução suficiente ao passo específico.
`dre_mapping_editor.html:18` e `views.py:12765` limitam histórico visual a 12 versões, sem paginação.
A ficha secundária NFS-e volta a NSU/hash (`company_detail.html:199`) onde a central usa número fiscal.

Entrega: exemplo de arquivo, prévia, vínculo ao mapa e empresa/período; acompanhamento de
exportação e recuperação; histórico completo; identificadores humanos antes das referências técnicas.
Homologar o renderer Node no ambiente publicado. **Alta para relatórios vendáveis; média na ergonomia.**

### A-11 — Radar precisa declarar e provar sua cobertura

**Limite comprovado.** `hub/reform.py:18` lê até 40 links por origem; fontes gerais e títulos
orientam seleção/relevância/hash. Isso não demonstra teor integral, histórico normativo ou cobertura
de todas as alterações aplicáveis a todos os clientes.

Entrega: catálogo de fontes/cobertura, data publicada versus coletada, detecção de origem vazia,
alterada e atrasada, teste de publicações esperadas e análise humana. Preservar a proposta de
acompanhamento, sem prometer cálculo ou aconselhamento fiscal automático. **Alta para confiança.**

### A-12 — Operação e memória precisam refletir a arquitetura atual

**Histórico e código.** `docs/pt-BR/runbooks/backup-restauracao.md:5` ainda cita Fly Managed
Postgres, enquanto produção usa Neon. O índice das etapas diz que a 12 não iniciou e a 07 ainda é
sintética, apesar de V-274. Fly tem web/worker, concorrência limitada e liveness; não há prova nova
de restore de banco, objetos e chaves dentro do tempo aprovado.

Entrega: estado atual por capacidade/release; manifesto de publicação; runbook Neon/Tigris/chaves;
RPO definido, restore e retomada cronometrados; alarmes de readiness/fila/certificado/fonte; carga
representativa e escalonamento estimado antes de custo. **Crítico para liberação sustentável.**

### A-13 — Oferta comercial versus capacidade comprovada

**Conflito documental a resolver antes da liberação afetada.** D-169/V-197 pediram apresentação
de Siescon como parte pronta; `home.html:108` segue essa direção. Q-33 e a interface autenticada
indicam conector em preparação. Não alterar unilateralmente decisão explícita de oferta.

Recomendação ao responsável: homologar a capacidade ou delimitar sua disponibilidade de forma
específica na contratação/oferta, conciliando D-169, D-03 e Q-33. A comunicação geral do produto
pode permanecer coesa; o cliente deve compreender exatamente o que recebe agora. **Crítico da oferta.**

### A-14 — Indicadores NFS-e não seguem o período da lista

**Observado na demo atual e confirmado no código dos modos demo/real.** Em 05/10, a lista filtrada
para setembro mostrou 12 resultados e o indicador “Total no período” mostrou 24. `views.py:3791`
define o acervo `document_query`; a lista aplica filtros e calcula `document_total` (`:3887`/`:3935`),
mas os indicadores voltam à consulta base (`:4309`, `:4318`, `:4367`). Os links dos cards em
`nfse_center.html:65`–`:68` descartam período/pesquisa. Classificação da sessão demo também pode
atualizar a lista sem atualizar os indicadores que usam somente artefatos persistidos.

Consequência: a pessoa não consegue conciliar o resumo com o que está conferindo; clicar pode
trocar o contexto silenciosamente. Entrega: compartilhar recorte de empresa/pesquisa/período,
definir a semântica de facetas situação/movimento, preservar contexto nos links e usar decisão
efetiva da sessão demo. Separar contagem do acervo usada no primeiro uso. Aceite com dois meses,
duas empresas, filtros, classificação, paginação e relatório concordantes. **Alta; primeira correção
recomendada no produto NFS-e.** Não foi executado teste com dados reais nesta auditoria.

## 6. Sentido das telas e tarefas do usuário

| Tela / família | Pergunta que deveria responder | Avaliação e direção |
|---|---|---|
| Landing/demo/cadastro | O CICA resolve minha rotina? O que posso experimentar/contratar? | Demo é boa prova; alinhar promessa, disponibilidade e próximo passo sem inventar resultado comercial |
| Login/recuperação/MFA | Como entro ou recupero meu acesso? | Preservar MFA opcional do cliente e remoção de recovery codes D-183/192; tornar recuperação administrativa encontrável |
| Meu trabalho | O que faço primeiro hoje? | Já responde bem com nove tarefas no cenário atual; reduzir repetição somente se teste mostrar dificuldade |
| Carteira | O que está pendente nas empresas ao meu alcance? | Preservar recorte e drill-down; mostrar diferença entre falta de trabalho configurado e ausência real de pendência |
| Gestão | Quem assume o que está atrasado/sem dono/impedido? | Distribuição existe; propor passagem/substituição e carga observável, sem avaliação automática da pessoa |
| Atividades/detalhe | O que fazer, até quando, para quem e o que comprova? | Bom próximo passo e evidência; ligar documento faltante, origem e revisão ao mesmo contexto |
| Modelos | Quais rotinas esta empresa precisa repetir? | Biblioteca e versionamento bons; usar modelos aprovados, cobertura e calendário real |
| Fechamentos | Por que a competência ainda não pode ser encerrada? | Preservar requisitos e reabertura; não usar zero de fonte não configurada como resultado positivo |
| Empresas/ficha | Qual é a situação deste cliente e onde continuo? | Boa centralização; reduzir repetição de tabelas técnicas e aprofundar somente a seção escolhida |
| NFS-e/notas | Que notas preciso conferir e como preparo a entrega? | Lote e classificação acessíveis; medir triagem massiva de ambiguidades, significado de acumulador e retorno Domínio |
| Acumuladores | Qual código é válido nesta empresa e por quê? | Exibir origem/atualização/critério; não reutilizar código de outra empresa por semelhança |
| Coleta/certificados | Está coletando? O que falta e o que preciso fazer? | Próxima ação e cobertura boas; conferir renovação, pausa, ausência e coleta parcial reais |
| Exportações | O que gerei, o que entreguei e o que o ERP aceitou? | Manter pacote, download e importação confirmada distintos; concluir Q-39 |
| Triagem/caixas/detalhe | Recebi o documento certo, seguro, da empresa/período certos? | Gaps A-01/A-02 bloqueiam o resultado; lista de estados técnicos sozinha não resolve revisão |
| Guias/DCTFWeb | Posso obter este documento e quanto isso consome? | Revisão de escopo boa; emissão, conferência, transmissão e pagamento continuam distintos |
| DTE/resumo/teor | Posso ler sem produzir ciência? Quem trata a mensagem? | Distinção explícita é essencial; homologar ciência/retorno incerto antes de afirmar uso real |
| Parcelamentos | Qual acordo/parcela exige ação? | Fluxo empresa→acordo→parcela já coerente; provar serviço real e resultado incerto |
| Conciliação/configuração/auditoria | Que divergência existe e qual evidência sustenta a decisão? | Boa cadeia de importação/revisão; demo não cobre upload/exportação; homologar não-demo e destino |
| Folha/DRE/caixa | Os números concordam com a fonte? Que período e versão estou vendo? | Mostrar origem/tempo/pendências, explicar “fotografia”, guiar entrada e mapa; não confundir cenário com realizado |
| Radar/análise | Essa publicação merece análise para qual empresa? | Triagem humana é correta; deixar alcance e frescor claros |
| Copiloto | O que os dados autorizados permitem responder? | Contexto e fontes são bons; explicitar período, lacunas e correção, com próxima ação revisável |
| Aprendizado | Qual correção estou aprovando e com qual prova? | Corrigir A-03 antes de apresentar fila como aprendizado completo |
| Primeiros passos | Qual é o menor caminho até meu primeiro resultado? | Personalizar por contratação/papel e validar prontidão efetiva, A-05 |
| Integrações/consumo/contrato | O que está conectado, contratado e consumido? | Separar intenções mantendo navegação; alinhar D-109 e detalhes por operação |
| Equipe | O que esta pessoa poderá fazer em quais empresas? | Permissões explícitas são boas; falta clareza de papéis e operação de carteira extensa |
| Console/tenants/suporte | Qual escritório precisa de ação e como atendê-lo com limite? | Melhorar localizar, diagnosticar e recuperar erros sem expor detalhes internos ao cliente |

## 7. Pesquisa online de sistemas similares

Fontes consultadas em 05/10/2026. Recursos descritos por fornecedores não são prova de eficácia,
acessibilidade, disponibilidade contratual ou compatibilidade com o CICA. Não foram comparados
preços nem prometida equivalência fiscal. Fontes antigas foram usadas apenas para padrões estáveis.

| Produto e fonte | Capacidade relevante | Decisão recomendada para o CICA |
|---|---|---|
| [Domínio/Gestta](https://www.dominiosistemas.com.br/blog/como-criar-um-checklist-de-tarefas-contabeis/) | Checklists e gestão conectados à rotina contábil | Integrar evidência à tarefa e evitar repetir a mesma conclusão em dois sistemas; fonte histórica, sem inferir API atual |
| [Nibo Docs](https://www.nibo.com.br/contador/funcionalidades/nibo-docs) | Pedido recorrente, recebimento e classificação documental | Ligar documento esperado à competência, falta, responsável e conferência |
| [Nibo Conciliador](https://www.nibo.com.br/conciliador-open-finance) | Distinção financeira/contábil, plano de contas e exportação | Explicar classificar, conciliar, exportar e importar como resultados diferentes; Open Finance não entra por inferência |
| [Acessórias — gestão de processos](https://acessorias.com/site/funcionalidade/gestao-de-processos/) | Processos com responsáveis, prazos e acompanhamento | Comprovar entrega e andamento; não equiparar arquivo gerado a obrigação cumprida |
| [SIEG IriS](https://www.sieg.com/iris/) | Carteira de pendências e serviços fiscais | Priorizar exceções por empresa e origem; ampliar serviços só com escopo/contrato próprios |
| [Qive — acesso por CNPJ](https://ajuda.qive.com.br/pt-BR/articles/1939596-painel-de-acesso-basico-pab-o-que-e-e-como-ativar) | Acesso restrito ao conjunto autorizado | Manter isolamento em arquivos, pesquisas e ações de lote; não é gap a implementar do zero |
| [Qive — colunas de NF-e](https://ajuda.qive.com.br/pt-BR/articles/8225615-listagem-de-nfes-personalizacao-de-colunas) | Configuração de leitura de listagem | Avaliar colunas/visões úteis por papel; não copiar regras de NF-e para NFS-e |
| [Karbon — Triage](https://karbonhq.com/resources/improve-workflow-karbon-triage/) | Mensagem, leitura, associação e responsabilidade em contexto | Preservar fila/posição ao conferir conteúdo e associar ao trabalho |
| [TaxDome — Jobs](https://help.taxdome.com/article/jobs-explained) | Trabalho reúne tarefas, arquivos e bloqueios | Separar etapa de impedimento; reunir o que explica progresso na ficha de trabalho |
| [Financial Cents — dashboard](https://help.financial-cents.com/en/articles/5390143-tracking-work-deadlines-in-your-workflow-dashboard) | Fila por cliente, responsável e prazo, com visões | Preservar agenda pessoal/gestão; avaliar visões salvas e filtros recuperáveis |
| [FloQast — fechamento](https://www.floqast.com/close-management) | Checklist, reconciliação, evidências e revisão | Aproveitar fechamento verificável existente; concluir homologação e revisão onde exigida |
| [Ramp — monitoramento de integrações](https://support.ramp.com/integration-monitoring-dashboard) | Saúde e diagnóstico das integrações | Mostrar última execução, cobertura, impacto e retomada; segredos/configuração em segundo plano |

Cinco fluxos foram examinados na documentação pública: triagem Karbon; ciclo de trabalho
TaxDome; escolha do trabalho no dashboard Financial Cents; [atendimento Nibo web/móvel](https://ajuda.nibo.com.br/pt-BR/articles/9801636-atendimento-com-o-contador-via-portal-do-cliente);
e [solicitações Karbon](https://help.karbonhq.com/en/articles/1524439-overview-of-client-requests).
O último foi legível no resultado indexado; a abertura direta posterior retornou 403. Seus princípios
úteis são pedido vinculado, instrução, prazo, recebimento e validação. Lembrete deve parar quando
resolvido/cancelado; enviar mensagem não integra esta entrega nem a autorização de pesquisa.

### Referências de UI e limites de acesso

- **Watermelon MCP:** busca `dashboards: accounting workflow client management` e retry
  `blocks: data table` não retornaram resultados. Isso levou à pesquisa concreta dos produtos acima.
- **Refero primeiro:** [catálogo web](https://refero.design/apps) consultado; sem MCP disponível e
  sem sequência completa específica acessível. Não foi atribuída inspiração a uma tela não vista.
- **SaaSFrame segundo:** [Mercury](https://www.saasframe.io/saas/mercury) e
  [transações](https://www.saasframe.io/examples/mercury-transactions-dashboard) indicam organização
  por tabela/fluxo; conteúdo completo/mobile depende de Pro. Não houve assinatura nem inspeção paga.
- [Linear — filtros](https://linear.app/docs/filters) reforça URLs compartilháveis; o CICA já usa
  esse padrão em várias telas. Adotar persistência consistente, não reimplementar o que existe.
- [TaxDome — documentos](https://client-help.taxdome.com/article/24-documents-section-overview)
  apoia conferir conteúdo e identidade antes da decisão; adaptar ao acesso e segurança do CICA.
- [Documentação técnica oficial NFS-e](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-atual)
  deve orientar inventário de versões e testes de contrato; nenhuma regra tributária nova foi inferida.

UI/UX Pro Max foi aplicada com buscas de produto, hierarquia, erros e stack. A busca inicial trouxe
dashboard financeiro genérico; retry trouxe produtividade/gestão de trabalho, mais adequado.
O CICA usa templates Django/CSS/JavaScript; orientações HTML foram adaptadas, sem propor migração
para React/Tailwind. A skill landing-page-design foi lida para revisar oferta/primeiro uso,
preservando marca e decisões posteriores do projeto. Não se recomenda uma troca estética global.

A fonte atual das [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
foi lida integralmente. Regras aplicáveis orientaram a revisão estática das famílias de UI:
semântica, rótulos, foco, erros recuperáveis, estado na URL, conteúdo longo, temas e movimento.
Problemas estão localizados nos achados; hipóteses de contraste/tamanho exigem medição renderizada.
Não houve mudança de UI nesta entrega, nem declaração de conformidade integral de todos os arquivos.

## 8. Funções importantes ausentes e limites de expansão

| Capacidade | Necessidade | Recomendação / classificação |
|---|---|---|
| Calendário completo e dependências | Rotinas não são exclusivamente mensais; trabalho passa entre áreas | Proposta prioritária da central, baseada nos casos do piloto; A-06 |
| Pendência documental com responsável | “Aguardando cliente” precisa dizer o que falta e quem acompanha | Completar expectativa/checklist da Triagem; pedido externo/portal é expansão distinta |
| Alertas dentro do produto | Usuário precisa perceber nova atribuição, prazo e falha relevante | Proposta de inbox com preferências, dedupe e link de ação; e-mail/WhatsApp só conforme política/custo |
| Revisão e devolução estruturadas | Quem executa e quem confere podem ser pessoas distintas | Proposta de revisão aplicável por modelo, com motivo e evidência; não impor dupla aprovação universal |
| Passagem de trabalho e ausência | Férias/afastamento não podem deixar tarefa sem dono | Proposta de substituição com abrangência, datas, permissões e trilha |
| Busca transversal/visões salvas | Carteira grande exige recuperar contexto rapidamente | Proposta após garantir busca com carteira, paginação e estado; útil, não condição retroativa de NFS-e |
| Curadoria editável de IA | Feedback precisa se tornar correção verificável | Gap de conclusão do módulo existente; A-03 |
| Centro de saúde das integrações | Operador deve entender consequência da falha | Consolidar componentes existentes, diagnóstico e alertas; não nova ferramenta genérica de monitoramento |
| Portabilidade/retenção executáveis | CRUD de solicitação não conclui atendimento do pedido | Completar procedimento por artefato e backup conforme Q-24/29 e revisão responsável |
| Portal seguro do cliente | Reduz ida e volta de documentos e pedidos | Proposta a validar depois do núcleo; `PortalRequest` legado não é portal funcional e D-43 retirou Jornadas |

Não incluir automaticamente ERP completo, cálculo individual de folha, CRM amplo, societário,
aplicativo móvel próprio, Open Finance, WhatsApp, assinatura eletrônica ou construtor universal
de automações. São oportunidades possíveis, com descoberta e autorização próprias. “100% do
CICA” é concluir o escopo assumido; não reproduzir todas as funções de todos os concorrentes.

## 9. Linguagem proposta e orientação no ponto de uso

| Termo / situação | Explicação curta proposta | Próxima ação |
|---|---|---|
| Competência | Mês a que este trabalho se refere; pode ser diferente da data de recebimento | Mostrar mês/ano junto da empresa e da fonte |
| Acumulador | Código usado pelo seu Domínio para classificar esta operação | Consultar catálogo da empresa e evidência da sugestão |
| Fotografia | Conjunto de dados capturado em uma data; não muda com consultas futuras | Mostrar capturado em, período e origem |
| Fonte indisponível | Não foi possível atualizar os dados; a situação pode ter mudado | Mostrar última atualização e quem pode retomar |
| Sem dados | Ainda não há dados para este recorte | Distinguir primeira configuração, consulta sem resultado e falha |
| Classificada | Há uma decisão de classificação registrada | Mostrar origem humana/regra, data e como corrigir; não afirmar acerto fiscal apenas pelo estado |
| Pacote gerado | O arquivo foi preparado pelo CICA | Baixar e conferir; importação no ERP exige retorno próprio |
| Guia disponível | O documento pode ser conferido e baixado | Conferência/pagamento separados conforme Q-40 |
| Resultado incerto | A operação foi enviada, mas o retorno não confirmou o resultado | Conferir protocolo/origem antes de repetir |
| Abrir resumo DTE | Ver os dados que o CICA já recebeu | Separar explicitamente da ação que pode produzir ciência oficial |
| Aguardando cliente | Falta um item definido para continuar este trabalho | Mostrar item, responsável pelo acompanhamento e prazo |
| Concluído | Todos os requisitos deste trabalho foram atendidos | Permitir ver evidências e razão de eventual reabertura |

Texto de erro deve explicar a ação necessária sem obrigar o contador a interpretar stacktrace,
hash, DSN ou protocolo interno. Esses detalhes podem ficar acessíveis ao suporte quando úteis.
Exemplo proposto: “Não conseguimos atualizar esta empresa. Os dados exibidos são de 04/10 às
16h. Peça ao administrador para verificar o conector.” Data e motivo devem vir de evidência real.

## 10. Como validar a usabilidade real

Proposta: primeira rodada moderada com 5–8 participantes que representem dono/gestor, operador
fiscal, contábil, folha, auditor e financeiro; suporte interno separado. É amostra exploratória,
não estimativa estatística de toda a população. O responsável aprova participantes e dados.

Apresentar objetivos, não instruções de clique. Observar em silêncio; registrar tempo, caminho,
hesitações, erros, pedidos de ajuda e se o resultado foi entendido. Separar pessoa familiarizada
com contabilidade da pessoa já treinada no CICA. Depois de cada tarefa, pedir explicação do que
foi feito e do que ainda falta; comparar com o estado efetivo do sistema.

| Cenário | Resultado esperado | Erro de compreensão a procurar |
|---|---|---|
| Começar o dia | Identificar tarefa prioritária e contexto | Somar indicadores sobrepostos ou confundir carteira com minhas tarefas |
| Configurar primeiro cliente | Chegar à primeira rotina executável | Tratar checklist visual como prova de integração |
| Classificar NFS-e ambígua | Conferir dados, selecionar acumulador da empresa e explicar a decisão | Aceitar sugestão sem conferir origem, dados e evidência |
| Preparar entrega NFS-e | Gerar lote correto e conhecer o próximo passo no Domínio | Confundir download com importação concluída |
| Corrigir anexo recebido | Ver conteúdo seguro, corrigir metadados e comprovar arquivo | Aprovar sem conferir ou não conseguir resolver falta de empresa |
| Conferir fechamento | Descobrir impedimento e responsável; apresentar prova | Marcar concluído para ocultar falta de documento/fonte |
| Obter guia/ler DTE | Entender custo, documento e efeito oficial antes da ação | Confundir emissão com pagamento ou resumo com ciência |
| Conferir extrato/folha | Encontrar divergência e registrar tratamento | Tratar sugestão/valor agregado como cálculo oficial |
| Exportar DRE/caixa | Identificar versão, período e lacunas | Confundir simulação com realizado ou fotografia antiga com dado atual |
| Resolver falha | Encontrar impacto, próxima ação e pessoa responsável | Repetir operação fiscal de resultado incerto |
| Dar acesso à equipe | Antecipar a carteira e os poderes da pessoa convidada | Liberar toda carteira sem perceber abrangência |
| Corrigir Copiloto | Identificar fonte/limite e registrar correção revisável | Interpretar feedback como publicação automática de modelo |

Metas propostas de UX, a calibrar na primeira rodada: pelo menos 90% das tarefas prioritárias
concluídas sem instrução de clique; próxima ação encontrada em até um minuto; nenhuma confusão
observada entre geração/importação, emissão/pagamento ou resumo/ciência; nenhuma perda de entrada
em erro recuperável. Relatar numerador e denominador, sem esconder falhas atrás da média.

As metas técnicas já aprovadas em D-73 permanecem: 200 itens por fluxo automatizado, precisão
mínima de 95% onde aplicável, zero duplicidade/empresa errada/vazamento, retomada até 15 minutos,
restauração até quatro horas e processamento por empresa até cinco minutos salvo dependência
externa registrada. Exportação exige importação e conferência no destino.

## 11. Lacunas de documentação que a execução deve reconciliar

- Q-35: ambiente SaaS já foi decidido e publicado; permanece a parte da máquina definitiva de IA.
- Q-38: backup Bianchi já existe e foi usado; pedir somente material adicional indispensável,
  não repetir a pergunta genérica pelo mesmo backup.
- Q-13/Q-29: domínio do site está definido; homologação OAuth/SMTP/remetente não decorre disso.
- Q-39: contrato `infNFSe/valores/acum` tem evidência posterior; ainda falta aceite da importação
  e retorno no Domínio. Não dizer que nada do layout é conhecido.
- Q-01–06/D-79: não voltar ao início da discussão comercial. Conciliar a mudança D-109 com
  registros, código e valores remanescentes.
- Índice das etapas e runbooks devem apontar para estado vigente antes de qualquer nova execução.
- Mudanças locais recentes precisam de manifesto por capacidade para comprovar publicação;
  release numericamente maior não garante que todo arquivo local esteja nela.
- Há duplicidade histórica do ID D-192. Referenciar também título/data e corrigir por índice de
  equivalência, preservando referências anteriores; não renumerar o histórico silenciosamente.

A sequência, responsáveis, pacotes de trabalho e critérios de liberação estão no
[plano mestre atualizado](../../PLANO-MESTRE.md). Esta auditoria é sua base de evidências.
