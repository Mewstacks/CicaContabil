# Etapa 09 — Concluir Conciliação e Radar

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
- [ ] Gerar/testar MSI 1.0.5 e aprovar CI da fonte exata; publicar backend compatível.
- [ ] Observar edição/build/arquitetura do Server e compatibilidade do runtime
  (D-289); responsável pediu conferir o sistema provavelmente antigo antes de mudar.
- [ ] Instalar/configurar no Server; comprovar ODBC/LocalSystem/ACL/DPAPI/reinício.
- [ ] Efetuar corte real, novo oficial/ready, anterior recusado e dados preservados.
- [ ] Inventário/fontes/carteira completa, Q-46/Q-47, D-73, recuperação,
  treinamento e aceite conforme os mesmos gates existentes.

AnyDesk disponibilizado pelo responsável; a ferramenta nativa retornou timeout
-10005 ao obter a janela, sem observar/controlar o Server. Solicitado somente
texto do winver. Isso não é indisponibilidade humana nem prova de instalação.
[Procedimento técnico](../../contad-agente-oficial-windows-server.md).
