<!-- PC33-V465-2026-11-24 -->
## PC-33/V-465 — Conciliação multifontes CONTAD: plano e perguntas, 24/11/2026

Reunião com a CONTAD: para lançar outubro da SURIA, o extrato precisa ser cruzado com francesinha,
posição CP/CR do mês anterior, caixa do cliente, extrato de aplicação e documentos escaneados, e a CICA
passa a manter os títulos em aberto. Plano em [contad-multifontes-2026-11-24.md](../contad-multifontes-2026-11-24.md).

- [x] Análise do vídeo e dos arquivos; plano com requisitos rastreáveis, critérios de aceite e riscos (V-465).
- [x] PC-33 e perguntas Q-50 a Q-66 registrados; rascunhos da mensagem à CONTAD e da explicação do agente.
- [ ] Estimativa ao cliente e autorização do envio das perguntas (responsável).
- [ ] Decisão de escopo D-409, inclusive o ajuste da D-393 para sinalizações bloqueantes.
- [ ] Respostas bloqueantes Q-50, Q-52, Q-53, Q-58 e Q-59.
- [x] D-409: Fase 1 em modo simulação autorizada e registrada.
- [x] Fase 1 (linha de comando): leitores CP/CR .xls, francesinha e caixa do cliente; posição de títulos; motor e sinalizações; outubro simulado com os arquivos reais (V-466).
- [x] D-410: agente sem mudança (já aceita outubro); comparação simulação × Razão no comando, em PDF ou ledger-csv-v1 (V-467).
- [ ] Obter o Razão de outubro da SURIA (tela ou exportação da CONTAD) e rodar a comparação.
- [x] D-411: aplicação/resgate pelo extrato da aplicação e natureza divergente (R-12) na simulação (V-468).
- [x] D-412: documentos escaneados por OCR local, cruzados com banco e caixa (R-10/R-11) (V-469).
- [x] D-413: tela “Fechamento do mês (simulação)”, sem gravar nada (V-470).
- [x] D-414: guias de 48 dígitos, linha digitável tolerante, valor por extenso e soma conferida nos documentos (V-471).
- [x] D-415: transferências entre contas da própria empresa pareadas na simulação; contas a definir (Q-57) (V-472).
- [x] Correções C-02 a C-08 do plano mapeadas: já no `main` (D-396 a D-399), exceto C-05.
- [x] D-416 (C-05): extrato da mesma conta em dois arquivos não gera movimento em dobro (V-473).
- [x] D-417: posição de títulos por NF em `.xlsx` (R-07) e detalhe de cada movimento na tela de fechamento (V-474).
- [x] D-418: empréstimo e fatura do cartão identificam o débito na simulação; juros/principal e despesas seguem Q-55/Q-56 (V-475).
- [x] D-419: resultado do extrato sem estourar “Não comparável” no celular e ignorados fora dos “não conferidos” (V-476).
- [ ] Documentos escaneados na tela (exige fila) e lançamento real (decisão própria, conflito com a D-393).

<!-- D373-V412-IN-PROGRESS-2026-11-17 -->
**17/11/2026 — D-373/V-412 em execução: descoberta completa de planos e contas.**
Ampliação autorizada para as146 empresas, consultando catálogo completo e relações
empresa/plano/filial com proveniência, além da configuração de conciliação.
Preparação em lote e confirmação apenas dos campos não comprovados pela fonte;
release100 continua publicada até validação/publicação da nova candidata.
Terceira consulta real completou as duas leituras e recusou SOURCE_CHANGED;
a seção divergente ainda não é conhecida. Manifesto v3 distingue cadastro de
contagens variáveis, com diagnóstico por seção. Testes e fonte real pendentes; ver V-412.

<!-- D372-V411-PUBLISHED-2026-11-17 -->
## D-372/V-411 — preparação publicada e piloto real validado, 17/11/2026

- [x] Receber e validar cadastro real: 146 empresas, 43 candidatas, 120 caixas e zero referências bancárias/Iceberg.
- [x] Publicar release 100, migração 0087 e 43 complementos imutáveis; replay zero, autoria técnica e revisões preservadas.
- [x] Validar coleta real SURIA/8/setembro: 163/163 movimentos compatíveis, diferença líquida zero.
- [x] Aprovar CI integral, 15 verificações de UI sintética, ficha real, saúde/worker/assets e 15 grupos protegidos.
- [ ] Conferir extrato/plano e concluir vínculos bancários das demais empresas; 145 ainda sem conta operacional.
- [ ] Concluir revisão individual do piloto (162 movimentos, dois grupos ambíguos) e demais critérios Q-28/Q-46/D-73.

Cliente pode testar o piloto e revisar as 43 fichas de 11 empresas. Não há prova de
operação para toda a carteira nem homologação contábil. Agente permanece 1.0.13;
nenhum novo comando Windows é necessário. [Evidências V-411](../../../VALIDACOES.md).
Os checkpoints abaixo registram estados anteriores à release 100.

<!-- D371-V410-PUBLISHED-2026-11-17 -->
## Fechamento D-371/V-410 — publicação técnica para testes, 17/11/2026

- [x] Correções revisadas, regressão local/CI exato e QA sintético aprovados.
- [x] Publicar release99/agente1.0.13 e conferir runtime797/assets/saúde/worker.
- [x] Conferir15 grupos protegidos, configuração/capacidade e legado parado.
- [x] Validar instalação limpa e upgrades1.0.10/11/12 em Windows descartável.
- [x] Comprovar instalação1.0.13/conexão/capacidades no SVAPL02; recibo e backend autenticado.
- [ ] Comprovar primeira nova coleta financeira pela tela no recorte autorizado.
- [ ] Concluir revisões humanas e critérios Q-28/Q-46/D-73 próprios.

**SVAPL02 atualizado em17/11/2026:** recibo do atualizador fornecido pelo responsável confirma1.0.10→1.0.13 às10:17BRT, MSIexit0, configuração protegida preservada, serviço Running/Auto/LocalSystem e ciclo recente, sem reinício pendente. Conferência independente no backend autenticado às10:17/10:19BRT confirma o mesmo agente oficial, Razão/títulos online, automatic_counts=true em ambos, portfolio_scope=true no Razão e company_scope=true nos títulos. Instalação/conexão/capacidades estão comprovadas; a primeira nova coleta financeira pela tela continua sem prova. source_review_required corresponde ao título legado já capturado aguardando revisão; fonte e decisões anteriores permanecem preservadas.

Publicação técnica para testes; não é homologação contábil, aceite contratual ou conclusão da suíte. Fontes/vínculos/semântica/plano/regras e Q-28/Q-46/D-73 mantêm provas próprias. Q-47/C01/C02 continuam adiados; backup fora da prioridade do início dos testes. Não reabrir pareamento, carga inicial, fontes recebidas ou primeiro treinamento. Nenhuma nova consulta financeira ERP, revisão contábil em nome da cliente, chamada IA, mensagem ou alteração comercial foi executada nesta publicação.

[Evidências V-410](../../../VALIDACOES.md).

## D-366/V-405 — Correções do uso diário, 16/11/2026

- [x] Corrigir conta manual com motivo, histórico privado e controle de revisão concorrente; proteger identidade já usada.
- [x] Corrigir vínculo sem uso e reconsiderar descarte, preservando fonte e revisão anterior; exigir nova evidência explícita.
- [x] Validar completude do cadastro e manter empresa/conta na importação.
- [x] Separar envio do Razão independente, disponibilizar modelo e rejeitar lote inválido antes da gravação.
- [x] Implementar recuperação por lease360s/watchdog/token e startup, mantendo agenda ociosa15min.
- [x] CI43912687677, ensaio0084, publicação release95 e15 grupos preservados conferidos.
- [ ] Fonte/revisão humana para os43 vínculos e identificação das contas nas134 demais empresas; fontes e cobertura Q-28 próprias.

A implementação não equivale a aceite, backup operacional ou operação completa.
Q-46/D-73 e os adiados Q-47/C01/C02 conservam seus critérios.

## D-365/V-404 — Contas das demais empresas, 16/11/2026

- [x] Conferir fontes retidas, matriz146 e ordem C01–C43 sem completar dados ausentes.
- [x] Implementar pré-cadastro separado, importação idempotente e revisão privada com permissões.
- [x] Indicar vínculos pendentes na carteira/configuração, sem esconder fontes faltantes.
- [x] CI43895994663, migração0083, release94 e43 pré-cadastros reais conferidos; replay0 e14 grupos anteriores intactos.
- [ ] Cliente validar banco/referência, nome/plano/direção e evidência de cada vínculo aplicável.
- [ ] Identificar contas nas134 demais empresas sem candidata e obter fontes/competências reais.

Pré-cadastros disponíveis em Vínculos de contas; nenhum banco validado por inferência.
Esta entrega não encerra PC-19/Q-28, Q-46/D-73 ou os adiados Q-47/C01/C02.

# Etapa 09 — Concluir Conciliação e Radar

## D-364/V-403 — Operação por empresa e competência, 16/11/2026

- [x] Implementar carteira paginada por empresa/conta/mês, incluindo empresas sem conta e ausência de extrato/Razão, com dados já persistidos.
- [x] Aplicar empresa E módulo na consulta/conferência/relatório; preservar suporte restrito e recusar acesso revogado.
- [x] Preservar período entre carteira, conferência, detalhe e relatório; filtros inválidos retornam erro sem ampliar o recorte.
- [x] Oferecer relatório legível/imprimível em reais e CSV técnico compatível; saldos ausentes continuam desconhecidos e leitura não confirma movimentos.
- [x] Preparar importação com empresa/conta/origem válidas, sem upload ou escrita no GET; validar regressão HTTP local e atualizar o guia.
- [x] Concluir QA visual sintético e regressão PostgreSQL focada de160 testes, incluindo concorrência.
- [x] CI integral da árvore exata aprovado; PR22/main7a8af3b e release93 publicados, carteira/relatório autenticados conferidos e 14 grupos de dados preservados.
- [ ] Q-28: revisar vínculos/contagens/filiais e comprovar a operação das empresas; interface não acrescenta cobertura financeira real.

Q-46/D-73, recuperação, treinamento e aceite continuam próprios; Q-47/C01/C02
permanecem adiados. [Evidência local e limites](../../../VALIDACOES.md).

## D-363/V-402 — Mecanismos de expansão publicados, 16/11/2026

- [x] Implementar prévia sem escrita e lote atômico de escopos revisados por empresa/conta/mês, preservando contratos, autoria e reenvios.
- [x] Isolar conta/escopo inválido e falha transitória na fila, sem impedir outros jobs válidos.
- [x] Aprovar189 testes PostgreSQL, incluindo concorrência; Ruff/check e migrações sem alterações aprovados.
- [x] Gerar matriz privada dos perfis de13/11:146 empresas,43 candidatas/11 empresas,135 sem candidata,32 sem linhas e14 sem parâmetros; campos humanos vazios.
- [x] Preparar roteiro TXT privado com nomes atuais do cadastro CICA,146 códigos iguais à matriz e43 referências à ficha existente, sem nova capturaERP.
- [x] Concluir CI43873060568 integral, integrar PR21/mainc053cc0 com árvore idêntica à fonte1a16f3c e publicar release92.
- [x] Conferir732 hashes em web/worker, saúde200 e workerpong; mesmos recursos/configuração e legado integralmente igual/parado.
- [x] Conferir14 grupos protegidos, autoria/evidência/histórico e prévia real READ ONLY do piloto com zero novos jobs.
- [ ] Q-28: comprovar banco/conta/plano/direção, contagens por conta/mês e lotes completos antes da coleta ampliada.

A matriz não é manifesto de captura; seis empresas têm múltiplas filiais e
exigem conferir lotes completos. Não há aprovação por flags A/A, dispensa das
135 ausências, nova coleta ou agenda recorrente. Mecanismo técnico publicado
não conclui carteira, múltiplas filiais, recuperação ou treinamento/aceite.
Q-46/D-73 e Q-47/C01/C02 adiados mantêm seus critérios.
[V-402 e limites](../../../VALIDACOES.md).
Os blocos datados abaixo preservam o histórico.

## Checklist vigente CONTAD — D-343/V-366 (12/11/2026)

Os blocos datados abaixo preservam histórico. Esta lista consolida V-325,
V-347/V-352 e V-361–365, sem transformar prova técnica em aceite.

- [x] Acesso pessoal, instalação/corte do oficial, ODBC LocalSystem e versão 1.0.8.
- [x] Carga cadastral A146/146 e releituras sem duplicação.
- [x] Coleta nativa inicial real: 163 lançamentos/334 partidas independentes e equilibradas, replay idempotente e compatibilidade técnica com OFX.
- [x] Regressão V-365, incluindo concorrência PostgreSQL e Windows, registrada como aprovada.
- [ ] Q-28: carteira financeira recorrente desde 09/2026, planos/contas completos e situação M comprovada. O contrato nativo ainda é fixo no piloto212/8/setembro.
- [ ] Q-46: chaves/vínculos e coleta persistida de títulos, parcelas, baixas totais/parciais e estornos com exemplos revisados.
- [ ] Q-46/Q-08/Q-09: DE-PARA inicial com apoio de IA, dados/custos permitidos e revisão humana; rascunho determinístico não comprova IA.
- [ ] Q-46: saldos inicial/final e regras/exceções reais conferidos, além de pares técnicos por data/direção/valor.
- [ ] Q-47: leiaute contábil aceito e importação de teste autorizada conferida no destino, com caso ainda não escriturado.
- [ ] D-73/etapa12: amostra/qualidade, desempenho, retomada/restore, treinamento e aceite por release.

A suíte preserva ainda seus próprios layouts/OCR/destinos, folha/DRE/caixa,
relatórios e fontes do Radar. [Detalhamento vigente](../pendencias-conclusao-2026-11-02.md).
Nenhuma implementação ou homologação nova foi executada nesta revisão.


**Continuidade 03/11/2026 — D-308/V-309:** corrigida autenticação do DSN no
agente; versão 1.0.1 atualizada e conexão Domínio confirmada no configurador
instalado do PC Windows 11 x64. Pareamento segue pendente porque o endpoint
CICA respondeu 503 por ausência da CA do agente. A prova local V-308 e os gates
de Razão/títulos/piloto permanecem distintos dessa conexão mínima.

**Teste 03/11/2026 — D-308/V-308:** 157 testes/24 subtestes PostgreSQL
aprovados (um skip de OCR), incluindo nova travessia HTTP do contrato do agente
até a conferência com Razão independente. Isso é replay sintético local, sem
transporte pelo serviço Windows. No PC real, o teste ODBC do configurador
retornou 28000 (credenciais recusadas); aguarda correção segura no RDP antes do
pareamento/sincronização. Etapa e piloto continuam abertos.

**Revisão 03/11/2026 — D-305/V-304:** [contrato e operação do Razão normalizado](../../conciliacao-razao-normalizado.md).
Entrada local de partidas completas, ponte das duas filas e relatório privado
implementados. Sicredi textual recebeu documento/página/saldo e validação da
sequência. Títulos confirmados como origem Domínio; saída deve incluir relatório
e arquivo de importação. Isso não valida o adaptador direto, regras de títulos,
IA, instalação ou importação real no ERP. Etapa permanece aberta.

**Revisão 02/11/2026 — D-302/D-303/V-302:** [verificação CONTAD](../verificacao-conciliador-contad-2026-11-02.md).
As lacunas OFX de V-300 receberam correções e testes locais. A etapa permanece aberta para
Razão independente, títulos a pagar/receber incluídos pelo responsável, DE-PARA com IA e piloto.
O agente ficará no computador da cliente; o acesso ainda será fornecido.

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Revisão em 26/10/2026 — D-300/V-300:** [diagnóstico do conciliador](../diagnostico-conciliador-2026-10-26.md)
verificou `aad2f5a` e reproduziu quatro lacunas na fila OFX. Os controles de
alocação do fluxo novo não cobrem automaticamente essa fila. O conector lê
itens de extrato Domínio; ainda falta comprovar a fonte de Razão e sua ligação
ao fluxo avançado. Não há homologação contábil nova. O aceite NFS-e D-295 não
se estende ao arquivo de exportação contábil.

**Estado:** Em andamento: funções e controles locais revalidados em V-037.
V-047/V-049/V-050/V-062/V-064 tiparam formulários, serviço, limites de entrada,
multipart, navegação e tarefas, preservando a integração local. V-068 completou
a tipagem da view de conciliação e sua regressão focada; V-076 eliminou o corte
silencioso da fila OFX × Domínio e V-080 fez o mesmo na trilha de auditoria.
V-081 eliminou o corte da lista de alertas do Radar. V-085 eliminou os cortes
das trilhas de processamentos e exportações da Conciliação. V-090 eliminou o
corte da lista de candidatos no detalhe de um movimento. V-092 preservou as
páginas das três trilhas da Conciliação quando se navega pela carteira de
movimentos. V-093 estendeu essa preservação de contexto à fila OFX × Domínio.
Não há homologação de
arquivo, ERP, fonte oficial ou volume.

**Dependências:** 03–05; exportação Siescon depende de 04.

**Decisões relacionadas:** D-35, D-54, D-55.

## Escopo e checklist

- [x] Exercitar localmente o endpoint bancário v2 com páginas 500+1, retry, isolamento, assinatura/revogação/mTLS obrigatório e confirmação posterior com fonte independente (D-308/V-308).
- [x] V-309: corrigir autenticação do DSN e confirmar a conexão ODBC pelo configurador 1.0.1 instalado no PC de teste.
- [ ] Completar pareamento e sincronização do agente: servidor respondeu 503, CA ausente; envio e leitura sob LocalSystem ainda não executados.

- [x] Implementar entrada local de Razão com partidas completas, referência de conta, origem, fingerprint e recusa integral de inconsistências (D-305/V-304).
- [x] Integrar as duas filas para essa fonte normalizada, com alocação compartilhada, desfazimento, retry, auditoria e sem reexportar fatos já escriturados.
- [x] Implementar relatório privado por extrato/conta/período, sobras dos dois lados e saldos desconhecidos explícitos; leitura Sicredi com saldo/documento/região.
- [ ] Homologar adaptador direto de Razão e títulos Domínio, conferência dos saldos da fonte e equivalência de conta PDF/OFX com a contadora.

- [x] Confrontar o contrato fornecido em 27/10/2026 e a intenção de contas a pagar/receber e alternativa fiscal, sem ampliar o aceite para a suíte inteira (D-301/V-301).
- [ ] Resolver Q-46/Q-47: fonte de títulos em Q-28, significado de faltas, regras, DE-PARA inicial assistido por IA e operação contábil/fiscal de destino; comprovar execução no recorte da cliente.
- [x] Diagnosticar em 26/10/2026 a comparação extrato × registros disponíveis e detalhar Q-28 para entrevista, com provas sintéticas em V-300.
- [x] Corrigir localmente reutilização do candidato, conta/natureza não comprovadas e sobreposição OFX; compartilhar a identidade e validar a conta antes das duas filas (D-303/V-302).
- [x] Validar concorrência PostgreSQL de confirmação, upload e reconstrução sem apagar decisão humana; preparar auditoria de legado somente leitura.
- [ ] Homologar semântica/contas reais, revisar o legado existente e integrar o resultado das duas cadeias sobre fonte independente.
- [ ] Implementar e homologar títulos a pagar/receber da fonte autorizada, com parcelas/baixas e regras Q-46; inclusão já confirmada em D-302.
- [ ] Demonstrar o DE-PARA inicial assistido por IA do contrato, com revisão humana e controles Q-08/Q-09.
- [ ] Validar fonte independente de lançamentos do Razão, vínculo real do ERP e integração entre `AccountingEntry` e o fluxo de `JournalEntry`, sem assumir que item de extrato seja partida contábil.
- [ ] Concluir OFX, CSV, XLSX e PDF/OCR com layouts e evidências.
- [x] Permitir localmente corrigir mapeamento, classificar, revisar, conciliar e tratar ausência de correspondência.
- [x] Validar localmente cadastros, direção da normalização, competência, capacidade de alocação e partidas equilibradas no fluxo novo; isso não valida natureza/conta na fila OFX nem saldo inicial/final contra o Razão (V-300).
- [ ] Homologar exportações Domínio e Siescon sem apresentar exportação como importação concluída.
- [ ] Validar volume com PostgreSQL e corpus representativo.
- [ ] No Radar, comprovar coleta, atualização, origem e falhas, preservando a proposta de acompanhamento de publicações.

## Bloqueios e responsabilidade

Q-28; layouts reais e amostra independente. As métricas aplicáveis estão decididas
em D-73 e ainda precisam de prova.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Reimportação, layout alterado, OCR insuficiente, lançamento desequilibrado,
ambiguidade, saldo insuficiente, partidas compostas, reexportação e fonte do
Radar indisponível. V-037 reexecutou essas proteções localmente, exceto o OCR
em português, que ficou explicitamente ignorado por ausência da dependência local.

**Critério de aceite:** Processamento auditável, nenhuma conciliação sem evidência independente e exportações conferidas nos sistemas de destino.

## Evidências e próximo passo

V-037 registra 46 testes de domínio, um skip de OCR local e quatro testes de
interface/demo, além de lint/Django/diff limpos. V-047/V-049 revalidaram
formulários e serviço com 35 testes (um skip de OCR); V-050 validou os caminhos
locais de importação com 57 testes. Ruff, Django, migrações e diff ficaram
limpos, sem tocar integrações. V-068 incluiu conciliação em 119 testes locais e
concluiu a verificação estática global, sem tocar integrações. V-076 acrescentou
paginação com 101 correspondências de teste, preservando filtros e limitando as
evidências à página visível. V-080 paginou a trilha de auditoria com 201 eventos
fictícios, preservou a ação no retorno e a exercitou em navegador local. V-081
paginou 101 alertas sintéticos do Radar, preservando seus filtros e sem alegar
coleta ou visualização em volume na demonstração. V-085 paginou 21 execuções e
21 exportações sintéticas da Conciliação, preservando as duas trilhas de forma
independente, sem importar, reprocessar ou gerar arquivo. V-090 paginou 51
candidatos sintéticos da conciliação no detalhe do movimento, mantendo a
confirmação humana e evidência obrigatória; a demonstração temporária alcançou
a segunda página em 390 px sem overflow ou erro de console. Nenhuma homologação nova é
atribuída a esta etapa. V-092 confirmou em teste a independência entre 21
processamentos, 21 exportações e 51 movimentos sintéticos, sem executar ação
operacional. V-093 confirmou que a terceira página de 101 correspondências
sintéticas mantém as demais páginas abertas. V-097 passou a recusar XLSX
corrompido antes da persistência e limitou a prévia CSV às 51 linhas exibidas;
V-098 estendeu a recusa prévia a PDF malformado, sem retirar o OCR local de
documentos digitalizados válidos. A prova continua sintética, sem layout ou
arquivo real. V-099 abriu a demonstração isolada em banco temporário e revisou
a Conciliação em desktop e celular, sem overflow horizontal ou erro de console,
sem envio de arquivo ou integração. A existência de código ou testes
anteriores não prova conclusão.
Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no
registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

### Radar ligado à central (D-145)

- [x] Escolha explícita de publicação/empresa, justificativa, atribuição ao solicitante e tarefa idempotente.
- [x] Versão e URL preservadas; coleta atualiza somente vínculos existentes. Mudança/reclassificação reabre análise concluída sem presumir obrigação.
- [x] Recuperação local por escritório, sem coleta; confirmação humana posterior à versão atual.
- [x] Percurso Radar → seleção → atividade → publicação/análises da carteira, com recusa de perfis consultivos.
- [ ] Validar navegador, concorrência PostgreSQL, volume de publicações/vínculos e coleta real autorizada.
- [x] Saúde das fontes prioriza erro da coleta atual, preservando data do último sucesso.

### Extensão operacional D-134 / V-153 (24/09/2026)

- [x] Projetar arquivo na central, distinguindo processamento, tratamento comprovado e importação não confirmada.
- [x] Reavaliar após confirmação, desfazimento, aprovação, revisão e retomada; comando de recuperação por escritório.
- [x] Testar confirmação → conclusão → desfazimento e aprovação → revisão de origem, preservando evidência.
- [x] Reconfirmar relação desfeita com preservação histórica (D-135); revalidar saldo e manter decisões anteriores.
- [x] Navegação contextual por arquivo autorizada com filtros persistidos (D-136).
- [x] Expor histórico detalhado de decisões com paginação e acesso consultivo (D-137).
- [ ] Validar interface no navegador, concorrência e volume.
- [ ] Homologar concorrência, documentos/layouts autorizados e volume. V-153 comprova apenas ambiente local sintético.

> Execute a etapa 09. Complete conciliação, lançamentos revisados e exportações homologadas para os conectores aprovados. Valide documentos reais autorizados e volume. Complete também a operação do Radar, sem ampliar sua promessa para cálculo tributário individual não decidido.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.

## Continuidade D-309/V-310 — integridade e operação (04/11/2026)

- [x] Bloquear nova escrituração de movimento já conciliado, inclusive parcial e histórico.
- [x] Compartilhar trava da empresa em geração, aprovação, exportação e conciliação; testar concorrência PostgreSQL.
- [x] Invalidar rascunho/aprovação ao conciliar; não reaprovar ao desfazer; recusar conciliação se já exportado sem conferência.
- [x] Impedir edição individual/em lote de fatos conciliados até desfazer; orientar à evidência e corrigir rótulo de candidatos.
- [x] Auditar duplicidade histórica somente leitura, sem modificar snapshots ou decisões.
- [x] Exercitar OCR português na imagem Linux e fila Redis/Celery real com replay/reinício e decisão preservada.
- [ ] Confrontar Razão/títulos/parcelas/baixas independentes e exemplos Q-46.
- [ ] Homologar DE-PARA/IA conforme Q-08/Q-09 e arquivo Domínio conforme Q-47.
- [ ] Executar piloto D-73 real e aceite; 115 itens bancários candidatos não são amostra independente de 200.

V-310: 1.502 testes Python/151 subtestes, um skip opcional; navegador e seis
combinações de viewport/tema via CUA/Playwright. O corpus é sintético, salvo
a pesquisa ODBC local limitada e sem envio. Etapa permanece aberta.

Continuidade D-310/V-311 (04/11/2026): autenticação do piloto passa a HTTPS +
HMAC sem CA privada. Travas de duplicidade, decisões humanas, manifesto e
recusa fora do recorte continuam preservados. Regressão integral PostgreSQL:
1.522 testes e 151 subtestes aprovados, um skip opcional. Nenhuma regra Q-46,
contrato contábil, envio, importação ou aceite foi presumido por essa mudança.

## Continuidade D-311/V-312 — 05/11/2026

- [x] Recusar reaprovação de lançamento exportado, preservando estado/snapshot;
  histórico também impede nova exportação se o estado do lançamento regredir.
- [x] Reexportar somente bytes/hash/IDs/versão originais íntegros, com mesmo
  destino/período e motivo; não reconstruir arquivo a partir de fatos mutáveis.
- [x] Revalidar proteção humana e lançamentos sob trava empresa→movimento na
  aplicação/reaplicação de regras, incluindo espera concorrente em PostgreSQL.
- [x] Preparar contrato local de títulos/parcelas/baixas e DE-PARA determinístico
  em rascunho, com contas válidas, conflitos e revisão humana; nenhum provedor
  acionado. [Contrato e limites](../../conciliacao-fontes-titulos.md).
- [x] Extrair privadamente 754 contas candidatas do material local, sem importar
  catálogo ou presumir situação ativa/código contábil aprovado.
- [ ] Obter os relatórios Domínio ainda inexistentes e revisão Q-28/Q-46/Q-47;
  completar adaptador real, alocação de títulos e exceções com exemplos aprovados.
- [x] Preparar consulta com referência oficial de Razão por conta, títulos e
  leiautes; Domínio 10.6A-10/ajuste 2 instalado. Reabertura aguarda login direto
  solicitado ao responsável; isso não comprova dados ou semântica contábil.
- [ ] Executar IA do DE-PARA conforme Q-08/Q-09, homologar layout/importação,
  corpus real, treinamento e aceite. D-73 permanece aberto.

## Continuidade D-312/V-313 — 05/11/2026

- [x] Preparar alocação offline explícita banco↔baixas: chaves compostas,
  escopo/período/direção, capacidades acumuladas, parciais/agrupamentos,
  componentes, estornos brutos e datas diferentes para revisão.
- [x] CLI privada com hashes, validação integral, recusa de JSON ambíguo,
  sobrescrita/symlink e publicação atômica 0600; 85 testes focados aprovados.
- [x] Emitir Razão de uma conta do recorte original no Domínio atualizado;
  confirmar limite de fechamento/títulos e autorização de pesquisa alternativa.
- [x] Confrontar colunas do A Pagar da alternativa, preservando diferenças de
  emissão/vencimento/baixa/posição; PDF Windows não fornece as chaves necessárias.
- [ ] Obter fontes reais revisadas e completar integração persistente de títulos
  e regras Q-46; a prévia não confirma associações nem gera partidas.
- [ ] Q-47, IA Q-08/Q-09, corpus D-73 e aceite permanecem abertos.

[Contratos, CLI e limites](../../conciliacao-fontes-titulos.md). Nova candidata
local inclui a CLI; nenhum gate contábil foi habilitado.

## Publicação do código D-313/V-314 — 05/11/2026

- [x] Publicar na main as fontes/testes/contratos preparados, commit 4fede1e,
  com hashes de código iguais à candidata V-313 e CI aprovado para esse SHA.
- [x] PostgreSQL remoto: 1.633 testes/151 subtestes aprovados, dois skips
  Playwright/OCR; testes de concorrência executados. Não equivale a dado real.
- [ ] Concluir integração real de títulos, fontes/regras/layout revisados,
  importação conferida e homologação. Gate contábil permanece desligado.

## Anexos bancários CONTAD — V-315 (05/11/2026)

- [x] Reconferir PDF/OFX reais com o parser publicado: 163 movimentos em cada,
  zero sobras por data/valor, FITIDs únicos e saldos coerentes, sem SQL/escrita.
- [x] Distinguir início dos testes bancários de homologação contábil: os anexos
  permitem o primeiro, enquanto Razão/títulos/revisão/layout permanecem pendentes.
- [ ] Homologar fontes contábeis independentes, regras Q-46 e importação Q-47;
  não contar os dois formatos como 326 itens da amostra D-73.

## Percurso bancário autorizado — D-314/V-316 (05/11/2026)

- [x] Executar upload/reenvio/retomada/revisão/relatório em cópia isolada dos
  163 eventos reais; cenários OFX/PDF separados, 42 verificações finais aprovadas.
- [x] Corrigir preservação do editor humano em aplicação/reaplicação, incluindo
  ignorar/restaurar históricos e revalidação após trava.
- [x] Permitir relatório com aviso único de proteção, recusando erro real ou
  aviso inconsistente; 134 testes/24 subtestes PostgreSQL aprovados, zero skips.
- [x] Conferir navegador, salvar fatos originais e baixar CSV de 163 pendências,
  sem Razão/alocações/partidas inventados; contas contábeis continuam em branco.
- [ ] Concluir fontes/regras/importação reais Q-28/Q-46/Q-47 e aceite D-73.
  Limite de retorno ao filtro após salvar registrado em V-316; sem nova UI.


## Continuidade independente — D-315/V-317 (05/11/2026)

- [x] Corrigir perda de origem após ações do detalhe; preservar filtros/página
  com helper existente e validação de retorno, sem nova regra contábil.
- [x] Validar 93 testes/24 subtestes locais, zero skips; CUA/Playwright em
  desktop/celular/claro/escuro, ignorar/restaurar e retorno por teclado.
- [x] Conferir CI da correção anterior 700b496: PostgreSQL 1.652/151, dois skips;
  build/manifesto Windows, agente e três builds Docker aprovados.
- [ ] Completar fonte real/regras/importação, serviço/implantação e D-73/aceite.

O limite de V-316 após salvar foi corrigido. Trocar o tema na fila ainda perde
o painel do hash com a query preservada; registrado em V-317, sem alterar essa
rotina nesta rodada. Nova candidata de fonte com 809 hashes conferidos.

## Prévia privada CONTAD — D-320/V-322 (06/11/2026)

- [x] Separar prévia imutável de AccountingExport, habilitada por UUID explícito,
  com arquivo privado, fotografia, versão, autor e hash; lista vazia por padrão.
- [x] Conferir aprovação/conta/partidas/revisão/período, rejeitar fatos existentes,
  obsoletos ou exportados; não alterar estado dos lançamentos ao gerar prévia.
- [x] Recusar download obsoleto/corrompido, preservar bytes anteriores e registrar
  auditoria; validar concorrência e isolamento entre carteiras/escritórios.
- [x] Conferir formulário/histórico/download em desktop/celular e claro/escuro,
  erro/teclado, campos preservados, alvos e console com dados sintéticos.
- [x] Publicar release 72 após backup/restore pontual e CI aprovado; prévia
  configurada só no UUID CONTAD, exportação false, bloqueio anônimo conferido.
- [ ] Concluir acesso/ativação e recorte autorizado para uso autenticado real;
  cadastro CONTAD ainda em ativação pendente/sem membros.
- [ ] Obter fonte independente real de Razão/títulos e aprovar semântica Q-46.
- [x] Receber identificação do recorte SURIA/212, conta contábil 8 — BANCO
  SICREDI, 09/2026; captura bancária com linhas visíveis já conciliadas.
- [x] Receber/conferir quatro páginas do Razão independente da conta 8 em
  01–30/09/2026: 163 linhas e datas/valores iguais ao banco, sem alocação automática.
- [ ] Resolver Q-28: saldos da captura de extrato Domínio diferem dos PDFs;
  SURIA/212 confirmada pelo operador, origem pendente, sem ajustar saldo por inferência.
- [ ] Obter partidas completas/revisão semântica e vínculo da conta/IDs do
  recorte; relatório de uma conta não completa contrato de importação do Razão.
- [ ] Concluir importação/layout Q-47 em entrega autorizada própria, DE-PARA
  com IA sob Q-08/Q-09, D-73, treinamento e aceite CONTAD.

O responsável escolheu preparar somente arquivo nesta entrega; prévia privada
é explicitamente não homologada. Gate contábil permanece false; preview não
registra exportação, importação, baixa ou escrituração. V-322 distingue as
rodadas de teste e os limites da versão. Não encerrar PC-19 por esta prévia.

## Retomada dos arquivos fornecidos — D-320/V-323 (06/11/2026)

- [x] Registrar informação humana de empresa fechada e aceitar os arquivos
  fornecidos como evidência do teste local, sem exigir origem do saldo da captura.
- [x] Implementar leitura repetível do Razão PDF observado, validando folhas,
  empresa/conta/período, colunas, sequência de saldos e totais, sem fabricar partidas.
- [x] Gerar conferência privada OFX/PDF/Razão com hashes e linhas rastreáveis:
  163 coincidências, 159 candidatos únicos, dois grupos ambíguos e zero sobras.
- [x] Validar 139 testes, cinco skips PostgreSQL explícitos; execução real com
  rede/banco bloqueados, fontes intactas e saída 0600; Ruff/MyPy/Django aprovados.
- [ ] Completar uso autenticado/agente, títulos/baixas/DE-PARA, partidas reais
  quando necessárias e aceite; CLI local não encerra essas entregas.

A pendência histórica de explicar o saldo da captura não bloqueia este corpus,
por esclarecimento humano posterior. Não reabrir a pergunta para os testes.
[Uso da CLI e limites](../../conciliacao-razao-normalizado.md).


## Estado atual CONTAD — D-321/V-324 (06/11/2026)

- [x] Publicar conferência OFX/PDF/Razão também como comando administrativo
  na release 73, sem novo endpoint ou importação; 100 testes focados aprovados.
- [x] Conferir CI da fonte 651368c: PostgreSQL 1.755 testes/163 subtestes,
  dois skips declarados, incluindo os testes concorrentes antes omitidos em SQLite.
- [x] Ativar somente Conciliação no escritório próprio, sem convite/fatura,
  e receber autorização explícita do recorte bancário limitado.
- [x] Receber via agente real os 163 itens de 212/09-2026/extrato aprovado;
  conector healthy, zero duplicações/fora do recorte. Datas/valores conferidos
  com o corpus fornecido; os 163 registros AccountingEntry são espelho bancário.
- [x] Comprovar serviço LocalSystem/ready e persistência da configuração após
  reinício; ausência de campos de senha no novo DSN informada pelo operador.
- [x] Concluir acesso pessoal por solicitação posterior D-321/V-325: Grazi
  Proprietária, login HTTPS/Conciliação 200/Nova importação conferidos, sem
  convite, upload ou acesso de plataforma; credencial em arquivo privado.
- [ ] Completar partidas/fontes de títulos e baixas/regras Q-46/DE-PARA sob
  Q-08/Q-09; não fabricar dados ausentes nem consumir IA paga por inferência.
- [ ] Homologar importação Q-47 em autorização própria, D-73, treinamento e
  aceite. Exportação Domínio permanece false; prévia é não homologada.

A aprovação posterior do corpus e do recorte supera a antiga exigência de
explicar o saldo da captura para o teste. Não reabrir importador/saldo ou pedir
novamente arquivos/empresa/conta/competência/ID. Continuam 163 eventos únicos.


## Objetivo da próxima execução — D-322/V-326 (06/11/2026)

- [x] Preparar prompt de conclusão para carteira completa CONTAD, explicitando
  conta/empresa do piloto versus integração automática ainda pendente.
- [ ] Completar contas/plano por empresa, Razão independente/títulos/baixas,
  comparação/DE-PARA, identidade do extrato e revisão das ambiguidades.
- [ ] Executar jornada real da Grazi e fechar Q-28/Q-46/Q-47/D-73 com evidências,
  preservando custo/egressão e autorização de escrita/importação ERP.

[Prompt de finalização](../../contad-prompt-finalizacao-2026-11-06.txt).
O documento não habilita gates no runtime ou comprova dados ainda não recebidos.

## Execução integral CONTAD — D-323/V-327 (06/11/2026)

- [x] Histórico financeiro humano desde 09/2026; cadastros/contas integrais.
- [x] Protocolo/recepção paginada de empresas, situação explícita, replay/retomada,
  concorrência PostgreSQL e isolamento implementados e testados.
- [x] Fonte e9311eb/CI 42294764025 aprovado; backend release 74 com hashes,
  migrações, saúde, acesso e integridade de dados conferidos.
- [x] MSI 1.0.4/52 testes Windows/26 checks e roteiros preparados/validados.
- [x] Guia de treinamento preparado, sem alegar execução ou aceite.
- [ ] Inventário/situações/fontes reais no Windows: operador ainda indisponível.
- [ ] Completar contas/referências/Razão/títulos e regras Q-28/Q-46 com fatos reais.
- [ ] Upgrade configurado, manifesto ampliado e coleta/retomada reais da carteira.
- [ ] Saída Q-47, IA Q-08/Q-09, métricas D-73, recuperação, treinamento/aceite reais.

[Contrato e limites](../../contad-carteira-protocolo.md). Runtime conserva piloto
SURIA/163 eventos, sem fonte financeira nova. Publicação desta fase não conclui
PC-19 nem a entrega contratual. Próximo insumo externo: inventário real do PC.

### Continuidade D-323/V-328 — recuperação de cobertura (07/11/2026)

- [x] Corrigir abandono/reinício de leitura inconsistente e proteger recibos concluídos.
- [x] Persistir erro/horário e diagnóstico administrativo sem dados/segredos.
- [x] Foco PostgreSQL 62 e regressão local 1.801/163 aprovados, um skip explícito.
- [x] Fonte c8b0c50/CI 42355490505 e release 75, hashes, migrações, integridade,
  recursos, saúde, diagnóstico somente leitura e acesso conferidos.
- [ ] Inventário real Q-28, upgrade/coleta da carteira e fontes contábeis/financeiras.
- [ ] Demais gates Q-46/Q-47/IA, D-73, recuperação recorrente, treinamento e aceite.

Nenhuma varredura real da carteira ocorreu; a recuperação foi testada com dados
sintéticos no PostgreSQL. Manifesto do piloto e dados anteriores preservados.

## Novo agente oficial no Windows Server — D-324 (09/11/2026)

- [x] Adaptar prompt canônico, preservar original/cópias privadas e atualizar
  sequência de execução: instalar novo Server → validar candidato → corte → carteira.
- [x] Implementar candidato pendente, novo UUID/segredo, manifesto herdado,
  bloqueio de coleta e comando de ativação/revogação atômica com auditoria.
- [x] Preparar fonte 1.0.5, atualizar configuração recebida/worker e workflows;
  compilar serviço/configurador/ponte e validar 59 testes .NET, um skip Windows.
- [x] V-329: regressão final PostgreSQL 1.837/163 aprovada, um skip; foco
  SQLite 30 aprovados/seis skips concorrentes cobertos no PostgreSQL.
- [x] V-338/V-342: MSI 1.0.5 testado e backend consolidado publicado com CI aprovado.
- [x] V-331/V-332/D-325: Server 2022 x64 observado; .NET 10 aprovado e MSI validado.
- [x] V-345/V-346: instalação/ODBC/LocalSystem/ACL/DPAPI e reinício pré-corte comprovados.
- [x] V-346: corte real, novo oficial/primeiro ready, anterior recusado e dados preservados.
- [ ] Inventário/fontes/carteira completa, Q-46/Q-47, D-73, recuperação,
  treinamento e aceite conforme os mesmos gates existentes.

AnyDesk disponibilizado pelo responsável; a ferramenta nativa retornou timeout
-10005 ao obter a janela, sem observar/controlar o Server. Solicitado somente
texto do winver. Isso não é indisponibilidade humana nem prova de instalação.
[Procedimento técnico](../../contad-agente-oficial-windows-server.md).

### Consolidação D-329/V-342 — 10/11/2026

- [x] Integrar agente à main/PR 3, consolidar D-324/V-329 e D-328/V-341,
  preservar correções atuais e aprovar CI completo 42882756516.
- [x] Publicar/conferir backend consolidado release 80, hashes/saúde,
  migrações, dados/manifesto e recursos; manter MSI 1.0.5 entregue.
- [x] V-340: receber confirmação visual de ODBC interativo em SVAPL02.
- [x] Conferir código antigo expirado sem uso/zero candidato; emitir novo código
  privado por 60 minutos, fora de Git/ZIP, e atualizar roteiro do operador.
- [x] V-343: candidato pareado; captura Running/Auto/LocalSystem e
  awaiting_activation após reinício. Versão/horário/ACL/ODBC ainda por provar.
- [x] V-345/V-346: ODBC/LocalSystem/ACL/DPAPI e corte explícito comprovados;
  novo oficial/recepção/recusa do anterior sem perda ou duplicação.

Q-28 e demais gates continuam abertos. Não repetir o teste ODBC interativo,
a identificação do Windows, decisão .NET ou instalação sem motivo novo.

### Pareamento e prova SYSTEM — D-330/V-343/V-344 (10/11/2026)

- [x] Candidato SVAPL02 real, identidade nova/manifesto idêntico e heartbeat;
  captura Running/Auto/LocalSystem/awaiting_activation após reinício.
- [x] Entregar ferramenta pontual ODBC SYSTEM, relatório seguro, hash e roteiro;
  validar tarefa/DPAPI/ACL/limpeza no CI Windows 2022 da fonte exata.
- [x] V-345: receber relatório real ODBC sob SYSTEM, versão 1.0.5/status/horário,
  configuração acessível por DPAPI no serviço e ACL Administradores/SYSTEM.
- [x] V-346: corte oficial e primeiro ready/recepção comprovados,
  anterior recusado e dados preservados; demais gates continuam abertos.

### Corte e primeiro ciclo concluídos — V-345/V-346 (10/11/2026)

- [x] ODBC SYSTEM/x64, ACL privada, versão 1.0.5 e limpeza comprovados.
- [x] SVAPL02 único ativo/oficial; anterior revogado/auditado e assinatura 401.
- [x] Primeiro ready e recepção reais, mesmo manifesto e dados/piloto preservados.
- [x] V-347: JSON recebido após reinício posterior ao corte: Running/Auto/
  LocalSystem/ready/1.0.5; recepção real, único oficial e dados preservados.
- [ ] Demais fontes/carteira, Q-46/Q-47, D-73, recuperação, treinamento e aceite.

### Carteira após o agente oficial — D-331/V-348 (10/11/2026)

- [x] Prévia/aplicação com evidência e revisão, CAS, auditoria e travas; 112 testes
  focados e regressão PostgreSQL 1.881/163 aprovados, sem ativação operacional.
- [x] Inventário/diagnóstico executados em CI Windows 2022; sucesso sintético,
  limites, IM002 real, redação e ACL. Tentativa na cliente falhou, sem inventário.
- [x] V-349: causa das restrições ODBC corrigida; operador concluiu inventário
  de 601 objetos/5.674 colunas/502 empresas, com hash informado.
- [ ] Revisar situações/chaves, aplicar manifesto e conferir scan real da carteira.
- [ ] Contas/fontes financeiras, Q-46/Q-47, D-73, recuperação, treinamento e aceite.

### Inventário e publicação da carteira — V-349 (11/11/2026)

- [x] CI exato/PR 5/main e backend release 81 conferidos; 663 hashes, doze
  fingerprints, saúde, recursos, oficial/piloto e novo ciclo real preservados.
- [x] Conclusão do inventário real informada pelo operador, sem pedir repetição.
- [ ] Receber JSON completo e reconferir SHA, situações, tipos/chaves/fontes.
- [ ] Revisão/aplicação do mapa e scan real das 502 empresas com cobertura.
- [ ] Contas/Razão/títulos, Q-46/Q-47, IA/D-73, recuperação, treinamento e aceite.

### Somente ativas e atualização de origem — D-332/V-350 (11/11/2026)

- [x] JSON completo recebido e hash/601 objetos/5.674 colunas/502 empresas conferidos.
- [x] Pedido de todas as ativas registrado; primeiro seletor A=146, M=10 pendente sem inativação.
- [x] Filtro parametrizado na origem/protocolo v3/recepção e compatibilidade testados.
- [x] MSI1.0.6/Windows2022/upgrade DPAPI/retomada aprovados e pacote entregue.
- [x] PR6 integrado; backend release82 e preservação/saúde conferidos.
- [x] V-351/V-352: atualização real/heartbeat recebidos e conferidos.
- [ ] Prévia/aplicação única do seletor A e cobertura real, sem declarar M resolvido.
- [ ] Relações/fontes financeiras, Q-46/Q-47, D-73, recuperação, treinamento e aceite.

Não repetir instalação/corte/DSN/credenciais ou inventário já concluídos. A atualização
funcional1.0.6 preserva identidade e configuração. O piloto permanece até essa prova;
companies ampliado pausa sua leitura financeira, preservando os163 movimentos.

### Retorno real e formatos — D-333/V-351 (11/11/2026)

- [x] Upgrade real1.0.6/serviço/bytes protegidos e heartbeat conferidos.
- [x] Prévia e aplicação única do recorte A, com auditoria sem ator humano.
- [x] Origem contou146 e abriu scan; recusa por contrato14 dígitos localizada.
- [x] Sonda agregada testada no Windows e executada:12 inscrições11/133 inscrições14/uma vazia.
- [x] V-352: espelho literal/backend83/MSI1.0.7 publicados e conferidos.
- [x] V-352: mesmo agente atualizado e scan146 concluído/relido sem duplicação.
- [ ] M/relações/fontes financeiras, Q-46/Q-47/D-73, recuperação, treinamento e aceite.

O scan está incompleto/zero recebido. Não repetir manifesto, corte, credencial ou
inventário. Inscrições não serão omitidas, completadas com zeros ou rebatizadas.

### Carga real e entrega direta — D-333/D-334/V-352 (11/11/2026)

- [x] Inscrição literal/tipo de origem em campos próprios, sem inferência CPF/CNPJ.
- [x] 143 testes PG focados, CI integral/74 Windows e upgrade1.0.6→1.0.7 aprovados.
- [x] PR7/main, backend83/665 hashes e migração aditiva0080 conferidos.
- [x] Download direto/hash verificado; upgrade real ready/1.0.7, sem novo pareamento.
- [x] Scan original retomado e concluído146/146:145 criações/uma atualização/zero ignorados.
- [x] Releituras sem duplicação, IDs/valores/financeiro/CNPJ anteriores preservados.
- [ ] M/relações/contas/Razão/títulos, Q-46/Q-47, D-73, recuperação, treinamento e aceite.

Primeiro recorte A concluído; não declarar M resolvido ou projeto homologado.
Atualização direta elimina cópia manual; agente não faz auto-instalação futura.

### Chaves e relações — D-335/V-353 (11/11/2026)

- [x] Complemento limitado de catálogos, preservando inventário e agente1.0.7.
- [x] Análise local de chaves compostas/pares FK, com conferência de colunas.
- [x] 46 testes locais e12 cenários Windows5.1/JSON entre linguagens aprovados.
- [x] Download direto/commit/hash verificados; comando enviado ao operador.
- [x] V-354: relações reais recebidas/hash conferido/análise contra inventário aprovada.
- [ ] Validar plano próprio/compartilhado, contas, partidas completas e títulos/baixas.
- [ ] Q-46/Q-47/D-73, recuperação, treinamento e aceite.

Sem reinstalação, novo escopo ou ativação de fontes financeiras. Consulta de
catálogos não decide M nem autoriza JOIN por semelhança de nomes.

### Perfil contábil D-336/V-355/V-356

- [x] Perfil curto testado em16 cenários Windows e executado no piloto real.
- [x]1.405 registros/contas correspondentes/zero fanout,163 da conta8 conferidos.
- [x] D-337/V-358/V-359: agrupamento estrutural comprovado e normalizador local preparado.
- [ ] Q-46/Q-47/D-73 e aceite, sem contabilizar contagens como amostra revisada.

- [x] D-338/V-361: integrar e conferir snapshot real completo do piloto como fonte independente em rascunho.

- [x] V-359: normalizador integrado na main094a93d após CI integral aprovado.


### Integração nativa D-338/V-360 — 12/11/2026

- [x] Implementar snapshot completo/double-read/hash e recepção privada do oficial.
- [x] Persistir partidas literais em rascunho com idempotência e revisão de conflitos.
- [x] CI integral, MSI/upgrade Windows Server2022 e backend84 publicados/verificados.
- [x] V-361:1.0.8 confirmado no SVAPL02; Running/Auto/LocalSystem/ready e DPAPI preservado.
- [x] V-361: snapshot real/relatório/repetição idempotente/integridade conferidos; retomada do upgrade confirmada.
- [ ] Q-46/Q-47/D-73 e aceite humano; nenhum gate liberado por testes técnicos.


V-361:163 lotes/334 partidas reais equilibradas, OFX163 compatível por data,
direção e valor, diferença líquida zero; reimportação criou0/ignorou163.
Relatório privado entregue. Isso não substitui revisão humana200 itens, saldo
inicial/fechamento de saldos ou homologação de layout/importação no Domínio.

- [x] V-363: falha simulada antes do recibo reverteu lançamentos, partidas, efeitos e arquivo privado. O reenvio concluiu o mesmo job.
- [x] V-365: reexecutar a concorrência da coleta no PostgreSQL com as novas alterações de teste.
- [x] V-364: separar colunas inventariadas, chaves da seleção original e referências estruturais de candidatos Q-46.
- [ ] Confirmar chaves próprias e vínculos entre títulos, parcelas, baixas e estornos com amostras representativas.


## Desenvolvimento de títulos persistidos — D-344/V-367 (12/11/2026)

- [x] Persistir fonte normalizada privada/imutável e recibo idempotente.
- [x] Preparar/revalidar plano de alocações, compartilhar capacidade entre lotes e fotografias e detectar OFX sobreposto.
- [x] Confirmar/desfazer com trilha imutável, sem criar escrituração ou baixar ERP.
- [x] Conferir fontes/hash, revisão explícita de datas e acesso/carteira/contrato atuais.
- [x] Validar concorrência PostgreSQL, rollback, CLI e casos negativos em181 testes focados.
- [x] Preparar complemento fiscal restrito a metadados e análise offline, sem pedir ao usuário os nomes técnicos.
- [x] Windows e CI integral aprovados em fdbda60/43265387462; perfil em a560b7d/43270180630. Complementos posteriores têm provas próprias.
- [x] V-368: receber/conferir o catálogo fiscal real:15 tabelas,557 colunas e242 relações, incluindo nota → parcela → pagamento → lançamento.
- [ ] Comprovar tipos/componentes/estornos e amostras reais; implementar/homologar o adaptador de títulos Q-46.
- [ ] Concluir carteira financeira, DE-PARA com IA, Q-47, D-73, treinamento e aceite.

Operação técnica documentada no [guia CONTAD](../../pt-BR/contad-conciliacao.md).
A persistência normalizada está implementada; a fonte ERP não foi presumida homologada.


### Perfil fiscal do piloto — D-348/V-369 (12/11/2026)

- [x] Consultas agregadas das famílias comprovadas; nove cenários relacionais
  adversariais e78 testes de consultas/catálogos aprovados localmente.
- [x] CI43265387462/fdbda60 integral aprovado para a persistência de títulos.
- [x] Perfil PowerShell validado no Windows5.1,12 cenários, fontea560b7d/CI43270180630.
- [x] V-371: perfil real recebido/conferido, duas leituras idênticas; nenhum vínculo direto à conta8.
- [x] D-350/V-374: conferir lotes/contas e multiplicidade; nenhum vínculo com a conta8 foi demonstrado.
- [ ] Comprovar semântica de tipos/componentes/estornos e exemplos Q-46.


### Vínculos fiscais por lote — D-350/V-371/V-372 (12/11/2026)

- [x] Receber/conferir perfil real do piloto sem repetir o catálogo.
- [x] Preparar conferência sem montantes;12 cenários relacionais/90 testes aprovados.
- [x] V-372:15 cenários Windows aprovados em54ba2fb/CI43274063310; HTTPS/hash conferidos.
- [x] V-373: revisão com diagnóstico estático/limite1024/transporte compacto passou em17 cenários Windows/0effa47.
- [x] V-374: receber/conferir o recorte completo;193 formas em Saídas excedem limite antigo e nenhum vínculo bancário à conta8 aparece nos lotes.
- [x] D-351/V-375: conferir referências retidas e preservar ausência de associação; semântica/exemplos seguem pendentes.
- [ ] Confrontar semântica e eventos reais antes de habilitar títulos Q-46.


### Captura fiscal original — D-352/V-376 (12/11/2026)

- [x] Preservar campos e decimais literais em fonte privada, sem converter tipo normal em principal/caixa.
- [x] Implementar contrato/consultas incorporados por hash e duas leituras completas.
- [x] Implementar prévia de fila, autorização atual, isolamento, replay e auditoria única.
- [x] Provar 89 testes PostgreSQL, concorrência e recusa de resultado que dispense revisão.
- [x] Preparar candidata 1.0.9 e ensaio Windows de upgrade preservando DPAPI/identidade/DSN.
- [x] CI43285420180/84a3190 integral aprovado, incluindo pacote/upgrade Windows.
- [x] D-353/V-377: backend85 e pacote publicados, solicitante Grazi autorizado.
- [x] V-378: upgrade saudável confirmado e captura original concluída.
- [x] V-378/V-379: fonte original recebida/conferida e exemplos privados preparados.
- [ ] Confrontar semântica com os exemplos no Domínio.
- [ ] Homologar adaptador de títulos, vínculo bancário próprio e demais critérios Q-46/Q-47/D-73.


### Publicação da captura preparada — D-353/V-377

- [x] D-353/V-377: publicação/saúde/migrações e14 grupos anteriores inalterados conferidos; prévia da captura aprovada.
- [x] V-378: receber/conferir prova1.0.9 e fonte fiscal original privada.


### Fonte fiscal recebida — D-353/D-354/V-378/V-379

- [x] Oficial1.0.9/mesma identidade/DPAPI e fonte original/hash/contagens conferidos.
- [x] Sete exemplos técnicos privados, idempotência e preservação dos dados anteriores conferidos.
- [ ] D-355/V-380: C01/retenções e C02/juros adiados por indisponibilidade do Domínio; não solicitar agora. Semântica/gates continuam pendentes.


### Desenvolvimento independente da conferência adiada — D-355/V-381

- [x] Comparador por chaves completas, referência opaca/posição e literalidade das mudanças.
- [x] Leitura privada/isolamento/acesso atual, integridade e recusa de saída existente/symlink.
- [x]88 testes locais e checagens estáticas/Django aprovados; sem migração.
- [x] V-382: CI43335886670 integral aprovado, PR13 integrado e backend86 saudável; prova READ ONLY da fonte retida e preservação dos14 grupos conferidas.
- [ ] C01/C02 adiados; ausência ou comparação sem mudanças não prova estorno/semântica.


### Candidata local dos cinco pontos — D-356/V-384 (13/11/2026)

Código isolado `ecdb9a7`, branch `codex/contad-cinco-pontos`; não publicado.

- [x] Escopos mensais explícitos de coleta e compatibilidade do piloto implementados/testados localmente.
- [x] Ponte revisada captura→títulos→alocação parcial→desfazimento com proveniência e testes sintéticos.
- [x] Sugestões IA com reserva/cotas, revisão privada e regra em rascunho; provedor real apenas simulado nos testes.
- [x] Amostra congelada, revisão do proprietário e aferição por fatos/precisão/duração implementadas e testadas.
- [x] Regressão PostgreSQL2207/163 subtestes, bateria final54 e .NET101 registradas com limites emV-384.
- [ ] CI Windows/MSI/upgrade e publicação desta candidata, dentro da autorização operacional aplicável.
- [ ] Descoberta/contas/planos e coleta recorrente da carteira inteira desde09/2026; escopo explícito não prova cobertura.
- [ ] Semântica Q-46, saldo/história completa e vínculo bancário real; C01/C02 continuam adiados.
- [ ] Q-08/Q-09: teto numérico e conteúdo permitido, execução IA real e revisão de sugestões CONTAD.
- [ ] Q-47: conjunto/leiaute e importação real conferida, quando houver acesso; teste adiado nesta sessão.
- [ ] D-73:200 fatos reais distintos revisados,95% medidos e desempenho/recuperação/aceite operacional.

Não promover estas provas locais a homologação ou conclusão dos cinco pontos.


### Candidata em revisão — V-385 (13/11/2026)

- [x] PR14/código genérico publicado; Windows104/zero skips e MSI1.0.10/upgrade1.0.9→1.0.10 no CI conferidos.
- [x] Fonte/artefatos por hash e imagem candidata local sobre a base86 preparados para revisão, sem dados reais.
- [x] CI43426219942 integral aprovado: três builds Docker e regressões/Windows, com limites emV-385.
- [ ] Publicação/implantação/upgrade reais e fontes/IA/retorno/amostra D-73, sob seus gates.

A instalação oficial e a carteira real não foram alteradas por estas provas.


### Operação publicada — D-357/V-386–387 (13/11/2026)

- [x] PR14/15 integrados, CIs integrais e pacote final1.0.10/110 Windows aprovados.
- [x] Backend87, migrações0038/0039 nos aliases originais,725 hashes e saúde conferidos.
- [x] Mesmas máquinas/capacidade/configuração e dados financeiros anteriores conferidos; limites cadastrais emV-386.
- [x] Release1.0.10/download HTTPS/hash e comando PowerShell preparados e entregues.
- [x] Medição READ ONLY limitada do piloto em1,537s, sem fatos novos ou falso aceite.
- [x] V-388: JSON real1.0.10/exit0/configuração preservada e comunicação posterior do mesmo oficial conferidos; source_review_required mantém gate semântico.
- [ ] Carteira/fontes/contas/planos completos, títulos/saldos/banco Q-46, IA real Q-08/Q-09 e retorno Q-47.
- [ ]200 fatos reais distintos revisados,95% medidos, carga/recuperação representativas e aceite D-73.

Continuam válidos o adiamento do teste Domínio e os limites dos cinco pontos.


### DE-PARA preparado para revisão — V-389 (13/11/2026)

- [x] Ficha privada0600 com18 contas literais da fonte retida, sem nova coleta.
- [x] Conferência segura de metadados: provedor/chave central/política ainda indisponíveis, sem API/gasto.
- [ ] Seleção humana de contas ativas/analíticas e recorte revisado de descrições.
- [ ] Configuração segura do provedor e dados/teto Q-08/Q-09; geração/revisão IA real.


### Credencial e orientação — D-358/V-390 (13/11/2026)

- [x] Chave Claude específica criada no console autenticado pelo titular e armazenada localmente0600/0700, sem expor valor.
- [x] GET /v1/models HTTP200, sem inferência ou dado CONTAD; saldo promocional conferido sem compra.
- [x] Guia privado de consulta e proposta de12 contas pelo uso real retido, sem ativação por inferência.
- [ ] Conferência contábil de Tipo/Situação e recorte de descrições, sem reabrir teste Domínio adiado.
- [ ] Teto/dados Q-08/Q-09 e governança/configuração segura Q-11 para geração/revisão reais.


### Catálogo provisório e lote mínimo — D-359/V-391 (13/11/2026)

- [x] Autorização para avançar recebida; proposta privada3 descrições/12 contas sem dados identificáveis preparada.
- [x] Correção isolada permite sugestões pelo catálogo com hash/escopo, mantendo regras bloqueadas até plano confirmado.
- [x]70 SQLite/41 PostgreSQL, Ruff/MyPy/check e candidata local725 hashes conferidos.
- [x] PR16/código genérico e CI43453526955 iniciados sob D-346.
- [ ] Confirmar teto numérico proposto R$0,10/D-17 antes de consumir créditos.
- [ ] CI integral, publicação/configuração no escopo aprovado e geração IA real.
- [ ] Revisão contábil das contas/sugestões, ativação separada e demais Q-46/Q-47/D-73.


### Tentativa real sem sugestões utilizáveis — D-359/V-392

- [x] TetoR$0,10/um lote e conteúdo técnico aprovados expressamente.
- [x] PR16/CI integral e backend88/725 hashes/saúde/secret store conferidos.
- [x] Uma chamada realHTTP200,973entrada/420saída e custo estimadoUS$0,0003073 registrados; zero sugestões úteis.
- [x] Estado unknown/reserva preservados, configuração restaurada e uso externo desabilitado, sem retry.
- [x]14 grupos protegidos antes/depois da tentativa inalterados, sem contas/regras/ERP.
- [ ] Corrigir/testar configuração curta do Haiku5.5 e metadata de resposta vazia.
- [ ] Obter aprovação específica de outra tentativa antes de gastar; primeira autorização de uma chamada já utilizada.
- [ ] Sugestões válidas, revisão contábil/ativação separada e demais provas Q-46/Q-47/D-73.


### Correção publicada e proposta pronta — D-359/V-394

- [x] PR17/CI integral e backend89/725 hashes/saúde/dados preservados conferidos.
- [x] Classificação curta corrigida e uso de resposta vazia registrado sem pensamento/assinatura.
- [x] Lotev2 prepared por hash634fa811…, sem outra chamada ou ativação; primeiro unknown preservado.
- [ ] Nova autorização específica para mais uma única chamada atéR$0,10 adicionais.
- [ ] Sugestões utilizáveis, revisão contábil/ativação separada e demais critérios reais.


### Sugestões reais prontas para revisão — D-359/V-395 (13/11/2026)

- [x] Segunda chamada até R$0,10 adicionais autorizada expressamente e executada uma única vez, sem compra/retry.
- [x] Lote corrigido succeeded: duas sugestões para três casos,972 entrada/58 saída/zero cache e recibo de uso conhecido.
- [x] Primeira tentativa unknown e ambas reservas preservadas; somente duas inferências, consumo total estimado US$0,0004335.
- [x] Ficha privada dos três casos com históricos originais/proveniência e campos de decisão entregue, sem enviar originais à IA.
- [x] Política central/escritório desabilitados, aprovação revogada e14 grupos protegidos conferidos; zero contas/regras criadas.
- [ ] Revisão humana dos históricos e contas ativas/analíticas, correção do item sem sugestão e rascunhos vinculados às descrições literais.
- [ ] Ativação separada e demais critérios reais Q-46/Q-47/D-73; projeto permanece em andamento.

Projeções técnicas não são condições de regra. Ficha e evidências em
Downloads/CONTAD-sugestoes-DEPARA-para-revisar-2026-11-13.txt e
CONTAD-evidencias-revisao-DEPARA-2026-11-13.json (ambas0600). Limites emV-395.


### Descoberta da carteira e amostra independente — D-356/V-396 (13/11/2026)

- [x] Sonda limitada a códigos/contagens de empresas A e analisador offline implementados; sem criar contas/coletas ou interpretar flags/plano.
- [x]70 testes novos/102 com regressão local, Ruff/MyPy e22 cenários Windows específicos aprovados; PR18/CI integral iniciado.
- [x] Download HTTPS/commit/SHA conferidos e comando com orientações comentadas entregue; AnyDesk retornou timeout.
- [x]163 fatos bancários reais distintos congelados, referência humana vazia/previsões ocultas e ficha privada entregues.
- [x]14 grupos protegidos conferidos; backend89/agente1.0.10 e duas chamadas IA preservados, sem custo adicional.
- [ ] Receber/conferir o perfil real de cobertura e depois provar vínculos/escopos de contas, planos e banco antes de coleta de valores.
- [ ] Revisão humana das sugestões e dos163 fatos, pelo menos37 fatos adicionais,95% medidos e demais critérios D-73.
- [ ] Q-46 e retorno Q-47/C01/C02 adiados; não há aceite operacional nesta preparação.


### Perfil real da carteira — D-356/V-397 (13/11/2026)

- [x] Retorno70728bytes/SHA21136b2a…9e1231 recebido, contrato/hash e duas leituras conferidos.
- [x]146 códigos A idênticos ao cadastro;94566 linhas agregadas em242 grupos de09/10-2026, sem valores financeiros.
- [x]32 empresas sem linhas/14 sem parâmetros/120 cadastros de caixa sem referência bancária explicitados na matriz privada.
- [x] CI inicial43473250820 integral aprovado; não repetir a primeira consulta ou instalação.
- [x] Complemento fixo CTCONCILIACAO_CONTA→CTCONTAS preparado:80 testes/115 com regressão, Ruff/MyPy; CI43475605920 iniciado.
- [ ] Windows do complemento e retorno real dos códigos configurados; conferir natureza/plano/banco antes de valores.
- [ ] Revisão humana das sugestões/163 fatos, ao menos37 fatos adicionais e demais Q-46/Q-47/D-73.

- [x] Continuidade V-397:30 cenários Windows dos dois modos aprovados, comando do complemento entregue.
- [ ] Resultado real das contas configuradas e demais provas financeiras/aceite permanecem pendentes.


### Contas configuradas reais — D-356/V-398 (13/11/2026)

- [x] Segundo retorno21668bytes/SHA99c90475…16d01cfa conferido;43 contas em11 empresas, correspondência composta integral.
- [x] Configurações das146 empresas idênticas entre perfis;135 sem configuração não são marcadas inativas/dispensadas.
- [x] Ficha guiada C01–C43 com nomes retidos/proveniência entregue, campos humanos vazios e piloto preservado à parte.
- [x]30 cenários Windows específicos e CI2270SQLite/2305PG/três builds aprovados; limites emV-398.
- [ ] Revisão efetiva de banco/atividade/lançamentos/direção e escopos antes de coleta financeira ampliada.
- [ ] Títulos Q-46, sugestões/contas, Q-47 adiado e amostra200/95%/desempenho/recuperação/aceite D-73.

- [x] Fechamento V-398: CI43475605920 integral/110Windows e PR18 integrados; árvore final conferida, sem novo backend/MSI.
- [ ] Confirmações contábeis e aceite continuam pendentes; perguntar onde preencher não equivale a revisão.


### D-360/V-399 — Uso operacional no aplicativo, 13/11/2026

- [x] Inspecionar sessão CONTAD autenticada e identificar desvio para classificação sem plano.
- [x] Preparar conferência de extrato/Razão no início, revisão de registros existentes, relatório e retorno, sem ficha externa como porta de entrada.
- [x] Validar confirmação/desfazer/CSV em dados sintéticos e isolamento/papéis na regressão local.
- [ ] Concluir CI integral da candidata exata, implantação compatível e prova autenticada da interface publicada.
- [ ] Manter revisão humana real, carteira ampliada, títulos/saldos/banco, DE-PARA revisado e critérios D-73 como pendências próprias.

Candidata2a5ddfc/PR19, CI43487952368 em execução; release89 ainda vigente.
Sem novo consumo IA, agente ou importação Domínio. D-360 altera prioridade
da entrega, não cria homologação ou decisão em nome da contadora.


### Entrega D-360/V-399 — conferência publicada, 13/11/2026

- [x] CI integral da fonte451e129 aprovado e PR19 integrado com árvore idêntica.
- [x] Backend90 implantado nas mesmas máquinas;729 hashes, readiness/worker e configuração conferidos.
- [x] CONTAD autenticada: abrir conferência163+163, consultar revisão/candidatas e baixar CSV real.
- [x] Confirmação/desfazer com evidência e histórico validados em ensaio sintético, sem decisões contábeis reais do executor.
- [x] Desktop/celular, filtros/páginas/retorno, papéis e isolamento verificados no recorte desta entrega.
- [x]14 grupos protegidos/política IA/agente preservados; guia e imagens privadas preparados, aba entregue aberta.
- [ ] Carteira completa, semântica/vínculos de títulos, DE-PARA revisado e critérios de200 fatos/95%/desempenho/recuperação/treinamento/aceite reais.
- [ ] Q-47/C01/C02 permanecem adiados conforme pedido humano.

O percurso assistido do piloto está disponível para uso; esta prova parcial
não encerra a etapa nem comprova homologação integral. [Limites em V-399](../../../VALIDACOES.md).


### D-361/V-400 — Sete pontos sem intervenção externa, 13/11/2026

- [x] Endurecer aceite contra troca de fonte/ficha/escopo e contexto alterado, sem criar revisão humana;69 testes+2 gatesQ-47 aprovados.
- [x] Executar restore sintético PostgreSQL dos dois aliases/objeto/chaves, hashes íntegros/replay sem duplicação;9 guardas aprovadas.
- [x] Reconferir offline163 fatos banco/Razão e saldos, tempos locais1,17–1,63s, sem inflar amostra/95% ou homologação.
- [x] Preparar treinamento/ficha vinculados à release90;11 testes do percurso aprovados, piloto independe da ficha43.
- [x] Publicar candidata genéricaff3bac3/PR20 e iniciar CI43498802673, sem dados privados ou MSI novo.
- [x] CI43498802673 integral/PR20/main1f8d9c5 e backend91 publicados;729 hashes/14 grupos/readiness/worker/ficha163 READ ONLY conferidos, legado restaurado exatamente e parado.
- [ ] Confirmar vínculos/contas/semânticaQ-28/Q-46, revisar DE-PARA e163 fatos, obter37 fatos adicionais e precisão95% aplicável.
- [ ] Aprovar RPO e comprovar rotina/recuperação operacional, desempenho representativo, treinamento e aceite humanos.
- [ ] Retomar Q-47/C01/C02 somente conforme solicitação explícita; continuam adiados.

Provas e limites em [V-400](../../../VALIDACOES.md); nenhum bloqueio foi convertido em concluído.


### D-362/V-401 — Entrega assistida atual, 16/11/2026

- [x] Registrar autorização do plano e preservar alterações locais anteriores.
- [x] Conferir árvore publicada,11 testes do percurso e saúde atual do site/banco/cache.
- [x] Confirmar acesso existente após autenticação humana e abrir piloto163+163.
- [x] Preparar roteiro, suporte e ficha privada sem aceite preenchido.
- [x] Identificar a confirmação de exercício e distingui-la de conferência real.
- [x] Conferir desfazimento do exercício e nova confirmação humana, preservando o histórico.
- [x] Registrar revisão real declarada e nota genérica, sem inferir correção contábil.
- [x] Baixar/verificar tecnicamente CSV atual163+163/uma alocação de cada lado; entregar cópia privada.
- [x] Registrar resultados observados/declarados e manter aceite humano ausente.
- [ ] Completar referência auditável, download autônomo e explicação do CSV pela cliente.
- [ ] Obter eventual aceite humano limitado ao recorte; não presumir aceite integral.

Q-28/Q-46/D-73 e recuperação continuam próprios; Q-47/C01/C02 adiados.
As marcações acima não encerram a etapa nem a entrega integral do contrato.


### D-367/V-406 — Operação de títulos/baixas e DE-PARA pela cliente

- [x] Revisão nativa guiada, cumulativa e restauração auditada sem alterar fonte.
- [x] Seleção banco/baixas, prévia, confirmação, capacidade global, histórico e desfazer.
- [x] Relatório legível/CSV em reais e referências humanas das fontes revisadas.
- [x] Revisão das sugestões DE-PARA retidas e ativação com plano/acesso atuais.
- [x] Testes sintéticos PostgreSQL/SQLite e QA no navegador.
- [x] CI43925999340, 0085 e release96: árvore/runtime/saúde e15 grupos preservados comprovados.
- [ ] Cliente valida as fontes/semântica/vínculos reais; fontes ausentes continuam próprias.

Backup fora da prioridade desta rodada; Q-47/C01/C02 permanecem adiados.


### Esclarecimento V-406 — Autonomia da coleta do Razão

- [ ] Solicitar e acompanhar coleta direta pelo agente na interface, com escopo revisado; upload atual somente processa o arquivo e compara com fontes já recebidas.

A coleta técnica por comandos existe; esse ponto não está entregue à cliente
como ação autônoma. Não autoriza captura ou inferência de novos vínculos.


### D-368/V-407 — Extrato e Razão pela tela

- [x] Jornada empresa/conta/competência, upload retido e pedido idempotente.
- [x] Vínculo auditado, acesso atual, acompanhamento e retomada.
- [x] Contagens automáticas/dupla leitura, compatibilidade e preservação de decisões.
- [x] QA completo, CI43937515442, migrações0086/0040, backend97 e pacote1.0.11 publicados/verificados.
- [ ] Atualizar SVAPL02, observar capability e comprovar coleta real; sem acesso hoje.
- [ ] Revisar43 candidatas/11 empresas, identificar contas nas134 demais e obter fontes.
- [ ] Generalizar captura de títulos para outras empresas/períodos e solicitação autônoma (Q-28/Q-46).
- [ ] Conferir semântica, plano/contrapartidas e regras; retorno DomínioQ-47 continua adiado.


### D-369/V-408 — Títulos e baixas da carteira

- [ ] Contrato/agente com contagens automáticas por empresa/competência, legado preservado.
- [ ] Solicitação em lote, prévia, acompanhamento, retomada e fonte por empresa sem conta obrigatória.
- [ ] Revisão por conta e capacidade global por origem, sem inferência de banco/semântica.
- [ ] QA/CI/migrações e backend/pacote publicados e verificados.
- [ ] Atualização/prova real no servidor quando houver acesso; validações contábeis humanas.


### Fechamento D-369/V-408 — entrega publicada

- [x] Implementação, testes, CI, migração, pacote1.0.12 e backend98 publicados/verificados.
- [ ] Atualização1.0.12 no SVAPL02 e recepção real; dependência técnica de acesso.
- [ ] Fontes, dados e conferência humana das contas/relações/regras aplicáveis.

**Fechamento D-369/V-408 —16/11/2026:** release98/PR27 e agente1.0.12 publicados após CI43949218680; fonte integrada/testada com árvore idêntica. Migração0041,796 hashes/14 assets, saúde/worker e15 grupos protegidos verificados. Prévia somente leitura146×12 aprovada, incluindo empresas sem conta; fonte v1 intacta e zero novas coletas/normalizações/decisões de produção. A captura fora do piloto está implementada pela tela. Resta tecnicamente aplicar1.0.12 no SVAPL02 e comprovar recepção real, quando houver acesso. Dados, vínculos, semântica e regras reais permanecem humanos; Q-47/C01/C02 adiados e backup fora da prioridade. Pacote único substitui1.0.11 pendente; não refazer pareamento/DSN nem pedir acesso novamente hoje.


### Análise de prontidão — D-370/V-409, 17/11/2026

- [x] Auditar release 98 e comprovar runtime 796 hashes em produção; fontes existentes continuam acessíveis ao percurso do piloto.
- [x] Reproduzir defeito de histórico:limite 20 por conta antes de filtrar competência esconde pedidos anteriores, sem apagar dados.
- [x] Inspecionar sete páginas em 375/1440 px e claro/escuro:28 verificações Playwright e3 navegação/teclado aprovadas, exclusivamente sintéticas.
- [ ] Corrigir filtro/histórico paginado antes do uso ampliado; defeito P2 não impede o piloto atual.
- [ ] Atualização1.0.12 e recepção real de Razão/títulos pela tela; revisão de contas/fontes/semântica/regras Q-28/Q-46.
- [ ] AceiteD-73 e retorno Q-47 nos seus critérios; Q-47/C01/C02 continuam adiados.

[Análise e roteiro de testes](../pendencias-conclusao-2026-11-02.md).
Esta entrega não corrige aplicação nem homologa fontes/decisões contábeis.


## Correções para testes — D-371/V-410 EM ANDAMENTO (17/11/2026)

- [x] Filtrar competência antes de paginar20 e oferecer páginas independentes de extratos.
- [x] Preservar contexto/fonte no vínculo e retomada; recusar página inválida antes de escrita.
- [x] Informar falha/timeout/pausa de polling com atualização manual e estado preservado.
- [x] Aprovar27 regressões novas focadas, incluindo POST do vínculo, e QA17+POST sintéticos.

- [ ] Concluir PostgreSQL integral, CI da fonte exata, MSI limpo e upgrades diretos1.0.10/11/12.
- [ ] Publicar e conferir hashes/assets/saúde/worker e preservação dos dados/configuração.
- [ ] Comprovar atualização/capacidades/recepção reais no SVAPL02 antes de declarar autonomia.

Produção comprovada release98/canal1.0.12; candidata ainda não publicada.
Piloto, autonomia, contrato e suíte permanecem distintos. Q-28/Q-46/D-73
mantêm critérios próprios; Q-47/C01/C02 adiados e backup fora da prioridade.
[V-410 e limites](../../../VALIDACOES.md).


**D-372/V-411 — coleta real concluída em17/11 às11:00BRT:** solicitação pela tela autorizada, novo Razão recebido pelo agente1.0.13 e163/163 movimentos compatíveis com o OFX por data/direção/valor, diferença líquida zero. Fontes e decisões anteriores preservadas; dois grupos repetidos e162 movimentos aguardam conferência individual. Preparação das demais empresas permanece em andamento, aguardando complemento cadastral; não declarar carteira integral pronta.

<!-- D372-WINDOWS-CHECKPOINT-2026-11-17 -->
**D-372/V-411 — complemento cadastral preparado:** leitor independente com
37 cenários Windows aprovados no step do CI44101060487; download imutável
e SHA conferidos, comando entregue para execução local no SVAPL02 porque
AnyDesk retorna timeout. Fonte real ainda não recebida; nenhuma conta nova
ativada. A coleta/comparação SURIA está concluída; carteira integral continua
em preparação, sem inferir referências bancárias ou aprovação humana.

<!-- D372-REAL-DETAILS-RECEIVED-2026-11-17 -->
**D-372/V-411 — fonte cadastral real recebida e validada:**146 empresas,
43 candidatas com nomes e catálogo comprovados,120 caixas,zero referências
bancárias/Iceberg. Leitor PR29/CI44101060487 concluído. Preparação imutável das
43 fichas implementada e em validação/publicação; nada ativado automaticamente.
Piloto SURIA segue com coleta real/comparação concluídas. Carteira integral
continua com lacunas bancárias e de vínculo, sem aceite contábil presumido.


## Vínculo pelo OFX — D-377/V-417 (19/11/2026)

- [x] Registrar decisão D-377 antes do comportamento: OFX só pré-preenche banco e referência; nada é gravado nem vinculado sozinho.
- [x] Ler BANKID/BRANCHID/ACCTID com o mesmo analisador da importação; referência `banco:agência:conta` idêntica à exigida por `validate_ofx_account`.
- [x] Recusar arquivo sem banco/conta únicos, fora de OFX/QFX, maior que 25 MB, duplicado, perfil consultivo e ficha já pronta, sem escrita.
- [x] 13 testes novos; prova de que a referência digitada à mão seria recusada pelo primeiro OFX.
- [ ] Publicar (merge/deploy autorizados pelo responsável) e CONTAD vincular as contas reais pela tela.

## Amostra D-73 reprodutível — D-378/V-417 (19/11/2026)

- [x] `reconciliation_acceptance select`: semente registrada, fatos distintos, exclusão dos já congelados, filtro por competência, arquivo 0600 consumível por `prepare`.
- [x] Seleção não congela previsão, não revisa e não conta como amostra D-73.
- [ ] Revisão do proprietário dos 163 fatos SURIA e de pelo menos 37 fatos de outra conta vinculada; precisão automática só com regra ativa.

## Uso direto — D-393/V-440 (23/11/2026)

- [x] Regras DE-PARA pelo Razão ativas sem revisão no escritório habilitado; lançamento aprovado só do que falta no Razão.
- [x] Extrato sem Razão para empresas sem conta de banco no plano ou sem plano.
- [x] Revisão das confirmações automáticas opcional; amostra D-73 deixa de ser condição de uso da CONTAD.
- [x] Publicação v118, habilitação do UUID e `uso_direto --apply` em produção (V-441).

## Títulos automáticos — D-394/V-442 (23/11/2026)

- [x] Captura de títulos interpretada sem revisão humana no uso direto (C01/C02 pelos tipos oficiais).
- [x] Publicação v119 e `titulos_auto --apply` em produção (V-443); gravação depende de conta bancária na empresa.

## Correções da revisão — D-396/D-397, V-446/V-448 (23/11/2026)

- [x] Razão pedido para cada mês coberto pelo OFX em conta vinculada pela importação (D-396).
- [x] Desfazer de confirmação automática não é refeito; uma falha não anula o mês (D-396).
- [x] Regra retirada (Razão ou IA) invalida seus lançamentos não exportados (D-396).
- [x] “Parecido com o Razão” por janela de 5 dias e lançamento da CICA exportado só após Razão relido (D-397).
- [x] OFX Windows-1252, OFX de outra empresa recusado, rotina fora da requisição, IA rebaixada abaixo de 90% (D-397).
- [x] Telas no uso direto com estados reais, contagens de lançados/enviados e pendências de exportação (D-397).
- [x] D-396 publicada na release v121 (V-447, outra sessão).
- [x] D-397 publicada na release v122 (V-449).
- [x] Conferência somente leitura das contas da CONTAD em produção (V-450).

