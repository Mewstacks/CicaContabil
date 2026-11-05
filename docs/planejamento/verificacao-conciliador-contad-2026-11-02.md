# Verificação do conciliador CONTAD no CICA

## Percurso bancário executado — D-314/V-316 (05/11/2026)

42 verificações finais locais aprovadas com os 163 eventos reais, em cenários
separados por formato: upload, reenvio/retomada, revisão auditada, escopo/perfis
e download do relatório. Corrigidos ignorar humano perdido na reaplicação e
aviso de proteção bloqueando relatório. 134 testes/24 subtestes PostgreSQL
aprovados, sem skips; navegador conferido. Candidata de fonte com 809 arquivos,
hash em V-316; dados/artefatos reais privados. Razão/títulos, arquivo importado,
implantação/serviço real, D-73, treinamento e aceite continuam pendentes.

## Anexos permitem teste bancário — V-315 (05/11/2026)

PDF/OFX fornecidos reconferidos com os parsers publicados: 163 movimentos em
cada, mesma multiplicidade de data/valor, zero sobras, FITIDs únicos e saldos
coerentes. Teste local de leitura/comparação concluído, sem banco/ERP/IA/rede.
Permitem iniciar teste real da entrada bancária; o fluxo contábil completo ainda
exige Razão/títulos independentes e revisão Q-28/Q-46/Q-47. Não são 326 itens
independentes nem amostra D-73 completa. Evidência privada em V-315.

## Código publicado — D-313/V-314 (05/11/2026)

Autorização expressa para main; commit [4fede1e](https://github.com/Mewstacks/CicaContabil/commit/4fede1e7f5b1bcfaec8b430a3b0f0d8c4d579b1d)
enviado e SHA remoto conferido. 84 arquivos de código/testes/documentação,
sem relatórios/dados/segredos/artefatos privados. Ruff/whitespace aprovados;
809 hashes do commit iguais à candidata V-313. CI 42067809017 aprovado:
PostgreSQL 1.633 testes/151 subtestes, dois skips Playwright/OCR; SQLite 1.617
testes/151 subtestes, 18 skips. .NET Linux 43 aprovados/um skip Windows,
build/manifesto MSI e três builds Docker aprovados. Sem novo teste de instalação.
**Código publicado no GitHub; aplicação hospedada, homologação e liberação
CONTAD pendentes.** Nenhum gate contábil, transmissão ou instalação habilitados.

## Continuidade — D-312/V-313 (05/11/2026)

Prévia offline explícita banco↔baixas e CLI privada implementadas/testadas:
85 testes focados, cobertura combinada 97,44%, Ruff global/MyPy aprovados.
Capacidade, parciais/agrupamentos/componentes/estornos e escopo conferidos;
nenhuma decisão persistida, escolha automática ou nova UI. Nova candidata local
809 arquivos e SHA-256 em V-313, sem publicação/homologação/liberação.
Login Domínio concluído e Razão original emitido/salvo no Windows, ainda sem
extração/revisão. Primeiro candidato não comprova fechamento/títulos. Pesquisa
alternativa somente leitura autorizada; fechamento fiscal 09/2026, contábil
11/2014 na alternativa examinada. A Pagar emitido, PDF conferido no Windows;
faltam chave de baixa/conta/data efetiva nessa visão. Cinco consultas de setembro
sem dados não comprovam ausência geral. Q-28/Q-46/Q-47 e demais gates continuam.
Os resultados completos abaixo são o snapshot anterior V-312, preservado.

## Continuidade — D-311/V-312 (05/11/2026)

**PC-19 continua aberto; prazo contratual 09/11/2026.** [Release candidata e
retorno](../contad-release-2026-11-05.md), [títulos/DE-PARA preparados](../conciliacao-fontes-titulos.md).
Base `b499cd1` com alterações locais preservadas, sem commit/push/deploy.

| Capacidade | Implementado nesta rodada | Validado localmente | Publicado | Homologado CONTAD | Liberado |
|---|---|---|---|---|---|
| Integridade da saída | Aprovação não reabre exportado; histórico impede nova escrituração; reexportação copia snapshot íntegro, mesmo período/destino | PostgreSQL, hash, corrupção/ausência e concorrência | Não nesta rodada | Não | Não |
| Decisão humana | Trava empresa→movimento e revalidação após espera em aplicação/reaplicação de regras | Corridas PostgreSQL e objeto desatualizado preservados | Não nesta rodada | Não | Não |
| Títulos/parcelas/baixas | Contrato normalizado offline, sem persistência/SQL/agente | Casos sintéticos de datas, saldo, parcialidade, componentes e estorno | Não | Não | Não |
| DE-PARA inicial | Rascunhos determinísticos de exemplos humanos, conta/plano/autorizações, conflito/insuficiência e retry | Testes sintéticos; nenhum provedor acionado | Não | Não; IA contratual pendente | Não |
| Material da cliente | 754 contas candidatas extraídas privadamente de 14 páginas; não importadas | Estrutura da extração, sem aprovação semântica | Não | Não | Não |
| Release/recuperação | ZIP/manifesto/roteiro; migrações e restore PostgreSQL sintéticos | 806 hashes, 182 tabelas, 15 sequências e dois arquivos íntegros | Não | Não | Não |

Regressão **final**: 1.578 testes Python e 151 subtestes aprovados, um skip
opcional, PostgreSQL, 430,32 s. .NET no Mac: 43 aprovados/um skip Windows.
MSI 1.0.3/hash reconferidos; os 44 testes/26 checks Windows de V-311 não foram
repetidos. Nenhuma tela nova ou alteração de template/JS/CSS; não declarar
Playwright/UI desta rodada como executados. Evidências em V-312 e
`.tmp/contad-delivery-2026-11-05/` (privado/ignorado).

O responsável esclareceu que Razão/títulos/parcelas/baixas solicitados ainda
não existem como arquivos. Não insistir em caminhos. RDP está acessível; ele
realizou o login Domínio e autorizou atualizar. O iniciador não encontrou seu
executável na rede; o ajuste disponível exigia a versão completa 10.6A-10.
Backup concluído/recuperável confirmado pelo responsável. Pacote completo
baixado do fornecedor, assinatura válida e instalação base concluída no
caminho existente, sem extras de nuvem/acesso remoto. Ajuste 2 concluído também.
Ao reabrir, Domínio pediu novo login com senha vazia; janela preparada e login
direto solicitado ao responsável. Teclado Scancode restaurado. Sem SQL novo,
conversão de base observada ou obtenção de Razão/títulos até esta observação.
Desenvolvimento obtém os relatórios do recorte e contadora revisa campos/exemplos.
DSN permanece intacto; não há necessidade de pedir novamente pacote ou backup.

Fonte real/regras Q-46, layout/importação Q-47, IA Q-08/Q-09, publicação
autorizada/acesso Fly, ODBC LocalSystem, transmissão no destino concreto,
recuperação real, 200 itens independentes, treinamento e aceite continuam
pendentes. Restore sintético em 5,726 s não comprova D-73 em produção.

Referência oficial pesquisada para a próxima consulta: o [relatório de contas
a pagar e receber do Domínio](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=224)
fica em Relatórios → Contas a Pagar e Receber na Escrita Fiscal; sua existência
e configuração na instalação ainda serão conferidas. Não alterar parâmetros,
gerar parcelas, registrar baixas ou gravar notas para obter uma amostra.
Conteúdo público indexado consultado; aberturas diretas da Central retornaram
403. Documentação não prova dados, semântica, operação ou homologação local.

## Revisão de autenticação — D-310/V-311 (04/11/2026)

O responsável dispensou a CA privada. O percurso vigente do piloto usa
**HTTPS + segredo individual + HMAC**, sem CSR, certificado de cliente, gateway
mTLS ou renovação de certificado. O backend e o agente 1.0.3 estão ajustados;
clientes antigos com certificado permanecem compatíveis, sem fallback silencioso.
As exigências mTLS de V-310 abaixo são históricas e não bloqueiam esse percurso.

Validação: **1.522 testes Python + 151 subtestes**, um skip opcional; **44 testes
.NET e 26 checks do MSI** no Windows. Dez cenários HTTPS reais sintéticos sem
certificado/CA de cliente aprovados, incluindo certificado HTTPS do servidor
inválido recusado, assinaturas inválidas, recorte, replay e reinício sem duplicação.
O serviço instalado em runner Windows leu configuração DPAPI HMAC sem PFX e
chegou à comunicação HTTPS de loopback, sem acessar ERP. Pacote final/evidência
em V-311 e `agent-windows/artifacts/windows-1.0.3/`.

O site hospedado ainda precisa receber o novo backend e o PC ainda precisa
receber o MSI; nada foi publicado/instalado no PC nesta rodada. O acesso Fly
continua indisponível. Não houve envio de dados, custo contratado ou escrita ERP.
Q-28/Q-46/Q-47, amostra real, recuperação publicada, treinamento e aceite seguem
abertos. Não repetir a solicitação de acesso nem converter isso em conclusão.

## Implementação de 04/11/2026 — D-309/V-310

| Prioridade do plano | Entregue e comprovado nesta rodada | Condição ainda aberta |
|---|---|---|
| Duplicidade | Geração/aprovação/exportação revalidam conciliação sob a trava da empresa. Confirmação invalida rascunho/aprovação; postagem já exportada impede confirmação até conferência explícita. Concorrência em PostgreSQL e auditoria histórica somente leitura testadas. | Conferir histórico real; não houve correção automática nem liberação de exportação. |
| Recorte | Manifesto `dominio-pilot-v1` persistido em cadastro/agente, protocolo `scoped-v1`, filtros antes da consulta/envio e rejeição atômica pelo servidor. Sem recorte não há sync financeiro v2. Piloto restrito não executa outros módulos. | Candidato selecionado por pesquisa local: uma empresa/conta bruta/janeiro de 2026, 115 itens. Conferir fechamento, conta bancária e fonte independente antes de parear/transmitir. |
| Transporte | CA/CSR/validade/renovação/revogação endurecidos; segredo privado do gateway além do certificado/HMAC. Oito cenários HTTPS reais com Nginx/Django aprovados localmente. | Cadastro hospedado permanece 503 por CA ausente. Ingresso TLS e sessão com acesso ao app Fly ainda indisponíveis; não houve mudança hospedada ou teste de transporte Windows. |
| Contratos | Fonte de extrato continua identificada como banco; pesquisa de metadados/cabeçalho não habilitou SQL novo no agente nem inferiu Razão/baixa. Contrato normalizado existente preservado. | Q-28/Q-46: confrontar partidas, títulos, parcelas e baixas com relatórios Domínio e contadora. Q-47: layout/importação conferida. |
| Interface/OCR | Movimento conciliado direciona à evidência e fica somente leitura até desfazer; candidatos deixam de aparecer como inexistentes. Teste OCR portátil e Tesseract/português/fontes na imagem Linux; extração digitalizada aprovada no runtime. | Homologação dos layouts reais e uso no runtime publicado. |

**Testes desta implementação, separados da rodada anterior de planejamento:**
1.502 testes Python e 151 subtestes aprovados em PostgreSQL, um skip do Playwright
Python opcional; navegador exercitado por CUA/Playwright. 38 testes .NET, builds
sem avisos/erros e 25 verificações do MSI em CI Windows Server 2022 descartável.
Django, migrações sem alterações pendentes, Ruff, tipagem dos sete módulos
críticos e whitespace aprovados. Não foram reformatados arquivos preexistentes
fora da mudança; o format-check global encontrou divergências de formatação.

Redis/Celery reais, sem execução eager: três entregas do mesmo run preservaram
200 movimentos sintéticos e uma decisão já confirmada. Primeira execução em
11,84 s; reinício/retry em 7,02 s. Restauração de cópia SQLite e três arquivos:
0,02 s, sete tabelas e hashes íntegros. A recuperação do backend HTTPS levou
5,86 s. São medidas locais; não demonstram RPO, restauração Neon/objetos, queda
no meio de tarefa, capacidade publicada ou tempos Windows/CONTAD de D-73.

O MSI 1.0.2 está preparado em `agent-windows/artifacts/windows-1.0.2/`, CI
[41845516300](https://github.com/Mewstacks/CicaContabil/actions/runs/41845516300),
commit `fc7b378c101350f5bb4c1e6324eb01aebb834201`, SHA-256
`e5bef0da853b740d3286087a863ad74922e2252ab6d969a2d8e2e333512158cc`.
A rede local não entregou o pacote ao PC; tentativa interrompida, nenhum MSI
executado. Windows conserva 1.0.1 e configurador anterior, sem agent.config.
Não houve alteração de firewall, credenciais, DSN, ERP, produção ou consumo de IA.

Evidências ignoradas em `.tmp/contad-implementation-2026-11-04/`:
`full-pytest.xml`, `nginx-mtls-results.json`, `queue-recovery-results.json`,
`ocr-runtime-results.json`, `ui-viewport-results.json` e capturas. Identificadores
reais ficam apenas em `private-pilot-candidate.json`, com acesso local restrito.
O candidato tem **zero itens independentes homologados** até o confronto;
115 itens bancários não atingem a amostra D-73. Não confundir com o ensaio de
200 partidas independentes sintéticas de V-304. RPO/janela continuam a definir.

**Continuidade 03/11/2026 — D-308/V-309:** PC de teste Windows 11 Pro AMD64,
distinto da CONTAD, recebeu atualização 1.0.1. Serviço Running e conexão Domínio
confirmada no configurador após corrigir substituição da autenticação do DSN.
28 testes .NET/25 checks CI aprovados. Pareamento/sincronização não executados:
endpoint CICA retorna 503, CA não configurada. Procedimento da alteração
hospedada e autorização pendente na etapa 12. Acesso CONTAD/piloto reais abertos.

**Pacote do agente em 03/11/2026 — D-306/V-305:** MSI 1.0.0 gerado e aprovado
em [Windows Server 2022 descartável](https://github.com/Mewstacks/CicaContabil/actions/runs/41664064414),
com 25 verificações do ciclo instalado. Cópia local e ZIP em
`agent-windows/artifacts/`, checksum conferido e assinatura de editor ainda
ausente. Corrigida a ACL da pasta de configuração. Acesso ao PC, DSN/driver e
pareamento/ERP reais continuam pendentes; este ensaio não homologa o conciliador.

## Atualização de 03/11/2026 — D-305/V-304

O responsável pediu a continuidade e forneceu PDF/OFX Sicredi e uma imagem de
assinatura de e-mail. Autorizada a leitura/teste local desses arquivos. A imagem
identifica contato; não contém Razão, títulos, plano de contas ou regras de baixa.
Os binários e identificadores permanecem fora do Git. As respostas confirmam
**títulos no Domínio** e saída de **relatório e arquivo para importação**.

- PDF de seis páginas renderizado e inspecionado. Foram lidos **163 movimentos**,
  com as mesmas datas/valores/multiplicidades do OFX, sem sobras nessa comparação
  bancária. A sequência fecha de **R$ 1,00** para **R$ 0,00**. A equivalência de
  formatos da conta exige conferência; os dois arquivos não são Razão independente.
- [Contrato `ledger-csv-v1`](../conciliacao-razao-normalizado.md): entrada
  local de partidas completas, saldos de débitos/créditos, conta/direção explícitas,
  rastreabilidade por hash/linhas, idempotência e recusa integral de inconsistências.
  Não representa layout oficial ou consulta direta Domínio homologada.
- Nova evidência persistida liga `AccountingEntry`, `JournalEntry` e o efeito
  bancário. Confirmação e desfazimento compartilham a alocação das duas filas;
  retry/reconstrução preservam a decisão. Registros antigos não recebem prova
  artificial e fatos já escriturados não são reexportados como novos lançamentos.
- Relatório CSV privado em **Processar → Baixar conferência**, por extrato/conta/
  período, com pendências nos dois sentidos, diferença líquida e saldos desconhecidos
  explícitos. PDF Sicredi conserva documento, página/região e saldo por movimento.
  A sequência inconsistente é recusada; lançamentos futuros não viram pagamentos.
- Migração aditiva `0077` cria apenas o vínculo de fonte independente. Nenhuma
  migração foi aplicada a desenvolvimento ou produção. Em release autorizada,
  aplicar 0077 após 0076 e manter ambas em rollback de aplicação, preservando
  evidências/alocações. Não reverter a tabela com dados como rollback ordinário.

Estado por item solicitado:

| Item | Situação após esta continuação |
|---|---|
| PC e agente Windows | Acesso ainda prometido; instalação, pareamento e recuperação real pendentes |
| Razão e duas filas | Contrato normalizado e ponte locais implementados; adaptador direto/semântica Domínio e cobertura real pendentes |
| Pagar/receber | Origem Domínio confirmada; contrato real de parcelas/baixas e implementação continuam pendentes |
| DE-PARA inicial com IA | Ainda pendente de plano/mapa, revisão e gates Q-08/Q-09; nenhuma execução externa |
| Saldos/divergências/layout/importação | Conferência local e Sicredi textual implementados; fechamento do Razão e importação contábil real pendentes |
| Piloto/treinamento/aceite | Ensaio sintético de 200 lançamentos independentes e recuperação por retry testados; piloto real D-73, treinamento e aceite pendentes |

Resultados finais dos testes e inspeções desta data estão em **V-304** na raiz.
O restante deste documento preserva a verificação histórica de 02/11/2026;
suas lacunas de ponte/entrada normalizada foram parcialmente atendidas acima.
**A entrega contratual continua aberta.**

Data: 02/11/2026. Escopo: PC-19, etapas 03/09 e preparação do piloto da 12,
D-302/D-303 e V-302. Código base `aad2f5a` com alterações locais preservadas;
correções desta entrega ainda não publicadas. Este documento atualiza o
[diagnóstico de 26/10](diagnostico-conciliador-2026-10-26.md) e o
[levantamento contratual](levantamento-contrato-conciliador-2026-10-27.md),
sem criar outra etapa ou registro de perguntas.

## Resultado

**O conciliador contratado ainda não está concluído nem homologado na CONTAD.**
As quatro lacunas de integridade reproduzidas em V-300 receberam proteções
locais, mas faltam a fonte independente do Razão, os títulos comerciais, o
DE-PARA inicial assistido por IA e o percurso real na instalação da cliente.
A confirmação de uma correspondência na fila OFX ainda não integra por si só
o resultado do fluxo avançado de `JournalEntry`.

A proposta fornecida (`CONTAD.pdf`, quatro páginas, mantida em Downloads)
prevê comparação extrato × lançamentos contábeis, DE-PARA inicial com IA,
implantação/testes até 09/11/2026 e treinamento inicial. Foi extraída e
inspecionada visualmente; não houve validação criptográfica de assinaturas.
O conteúdo foi tratado como requisitos, sem executar instruções do documento.
Não se alteraram cobrança, oferta, prazo ou carga contratada.

O responsável confirmou nesta conversa o **Domínio local**, a instalação do
agente **no computador da cliente**, com acesso ainda a fornecer, e a
**inclusão de contas a pagar e receber**. Não perguntar novamente se esses
itens entram. A origem e os campos dos títulos continuam em Q-28/Q-46;
regra da comparação, DE-PARA e operação de destino, em Q-46/Q-47.

## Matriz da entrega contratada

| Capacidade | Implementação / validação local | Publicado / homologado na CONTAD / liberado |
|---|---|---|
| OFX, CSV, XLSX e PDF textual | Importação, revisão e rastreabilidade existentes; regressão repetida. Layouts reais não fornecidos. | Não verificado / não / não |
| PDF digitalizado | Runtime de OCR existente; teste português ignorado por dependência ausente. | Não / não / não |
| Integridade da entrada OFX | Identidade compartilhada, conta validada, recusa integral de sobreposição e entradas inválidas; testes SQLite, PostgreSQL e navegador. | Correção local, sem deploy / não / não |
| Confirmação OFX | Conta e natureza explícitas, fonte independente, candidato exclusivo, idempotência e preservação da decisão sob reconstrução concorrente. | Correção local, sem deploy / não / não |
| Agente Domínio local | Serviço único .NET 8 existente; serviço, configurador e ponte compilados. Vínculo bancário deixa de ser fixado como falso. | Instalação desta versão não verificada / não / não |
| Fonte independente do Razão | Importação manual de registros aceita referência de conta; fluxo local exige natureza explícita. Consulta Domínio de partidas e ligação ao fluxo avançado não concluídas. | Não / não / não |
| Contas a pagar e receber | Inclusão confirmada. Origem, parcelas, baixas e representação ainda não implementadas/homologadas neste recorte. “Títulos ou obrigações” no upload não comprova essa função. | Não / não / não |
| DE-PARA inicial com IA | Regras/correção manual existentes não demonstram geração inicial de mapa por IA. Entradas/saídas e revisão precisam ser especificadas; Q-08/Q-09 regem execução externa. | Não / não / não |
| Diferenças e fechamento | Faltam prova nos dois sentidos, saldos por conta/período e resultado independente conferido pela contadora. | Não / não / não |
| Retorno ao Domínio | Exportação contábil mantém gate próprio desligado por padrão. Resultado esperado ainda em Q-47. Aceite NFS-e D-295 não homologa essa exportação. | Não / não / não |
| Implantação, recuperação e treinamento inicial | Roteiro preparado abaixo; acesso ainda não entregue. | Não / não / não |

## Correções realizadas

1. **Conta divergente:** o OFX é validado antes de persistir a fonte ou alimentar
   a fila antiga; o worker conserva sua validação para arquivos históricos.
   O upload repassa a conta selecionada ao importador antigo.
2. **Sobreposição de transações:** `OfxTransactionIdentity` reserva
   escritório/empresa/banco/agência quando informada/conta/FITID para as duas
   entradas. O mesmo arquivo é idempotente. Outro arquivo com FITID já recebido
   é recusado inteiro, incluindo eventual parte nova; a orientação é conferir
   o original e obter um intervalo sem sobreposição. Não há fusão silenciosa.
   Há verificação de registros anteriores à migração. FITID ausente, repetido
   ou longo, múltiplas contas e valor não finito/zero/fora do inteiro são recusados.
3. **Natureza e origem:** só entram como candidatos registros de fonte
   independente com referência exata de conta e natureza `inflow`/`outflow`
   compatível. Não houve mapeamento presumido de `D/C` ou `TIPO`. Itens do
   extrato Domínio local/Web não viram prova de Razão, nem `JournalEntry` fictício.
   CSV de registros contábeis aceita `conta_bancaria`/`account_reference`.
4. **Reutilização e concorrência:** confirmação serializada por empresa,
   recarregamento do candidato e recusa de candidato consumido, troca de
   confirmação existente ou transação histórica duplicada. Retry idêntico
   não duplica auditoria. Reconstrução usa a mesma trava e preserva a decisão humana.
5. **Agente:** `DominioLocalProcessor` usa o `EXISTS` do contrato somente
   leitura já presente no conector Python para informar `is_linked`. Adicionado
   timeout do comando. Isso indica vínculo do extrato, não prova de escrituração.
6. **Operação e linguagem:** a tela identifica registros como fonte recebida e
   explica a necessidade de Razão independente. `audit_ofx_integrity` inspeciona
   legado sem reescrever dados. O teste de migração NFS-e restaura agora o
   esquema atual completo, evitando falha nos testes transacionais seguintes.

A migração `0076` é aditiva: campo de conta vazio nos registros anteriores e
nova tabela de identidade, sem inventar evidência ou modificar decisões. Aplicar
antes do código em uma eventual release autorizada. Rollback de aplicação deve
preservar esse esquema e seus dados; reverter a migração apagaria a identidade
reservada e as referências novas. Nenhuma migração foi aplicada ao banco de
desenvolvimento, a ERP ou produção nesta entrega.

## Evidência e limites dos testes

V-302 na raiz registra resultados finais, comandos, capturas e limitações.
A suíte integral passou em PostgreSQL com **1.423 testes e 145 subtestes**,
com dois skips explícitos (OCR português e Playwright Python opcional).
Em SQLite foram 1.415 testes/145 subtestes; os testes de concorrência foram
exercitados no PostgreSQL. Os 23 testes .NET e a inspeção Playwright Node passaram.
Os testes são sintéticos: não medem precisão da IA, correção contábil no cliente,
completude do Razão, baixa de títulos ou compatibilidade real de importação ERP.
Build cruzado no macOS não substitui execução/instalação Windows e não gera prova
de um MSI novo assinado. Celery em modo de teste não prova rede/worker/Redis reais.

A inspeção de interface aplicou UI/UX Pro Max, pesquisa na documentação do Xero
sobre confronto de extrato com transação existente e as
[Web Interface Guidelines atuais](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md).
Watermelon e Playwright MCP não estavam expostos; Playwright Node do runtime
foi usado com Chrome local, banco/mídia sintéticos e bloqueio de rede externa.
A referência de produto orienta apenas a separação de fatos, sem copiar a UI.
A página oficial da especificação OFX 2.3 retornou 404; a proteção de identidade
está registrada como decisão técnica D-303 e será confrontada com arquivos reais.

## Piloto no computador da cliente, quando o acesso chegar

1. **Acesso e escopo (Q-28):** o responsável recebe acesso remoto por canal
   protegido; a cliente indica técnico e autoriza empresa, conta e competência.
   Não registrar login, senha, DSN, certificado ou conteúdo de cliente no Git/chat.
   A autorização Fedrizzi não vale automaticamente para a CONTAD.
2. **Fonte e resultado (Q-28/Q-46/Q-47):** localizar no Domínio o Razão da conta
   e os títulos a pagar/receber, incluindo parcela, vencimento, saldo e baixas.
   Se os títulos vierem de outro sistema/planilha, identificar essa fonte.
   Conferir chaves, contas e semântica com uma competência já fechada. A cliente
   demonstra a rotina; o desenvolvimento especifica a extração permitida.
3. **Pacote único Windows:** seguir [INSTALACAO.md](../../agent-windows/INSTALACAO.md),
   confirmar Windows x64, DSN de sistema SQL Anywhere x64 acessível à conta do
   serviço e credencial somente leitura. Gerar/revisar o MSI no Windows/CI e
   conferir checksum. Não instalar o agente Python nem um segundo serviço.
4. **Pareamento:** usar a URL HTTPS autorizada do CICA e código temporário;
   conferir certificado do agente, assinatura do corpo e o isolamento do tenant.
   O agente faz conexões de saída; não abrir o banco Domínio à internet nem
   desativar validação TLS. Verificar serviço `CicaAgent` e diagnóstico seguro.
5. **Contrato contábil:** validar consulta allowlisted e semântica da fonte real
   antes de habilitá-la. A consulta atual de itens de extrato não resolve esse
   passo. Completar a ligação com os candidatos do fluxo avançado preservando
   origem, partidas, conta e documento; sem inventar contrapartida.
6. **Títulos e DE-PARA:** definir o cadastro inicial a partir do plano de contas
   e mapa da cliente, com revisão humana. Implementar a comparação de títulos
   pela fonte e regras confirmadas; não usar vencimento como pagamento. Antes
   de IA externa, resolver o conteúdo permitido e o custo de Q-08/Q-09.
7. **Conferência:** usar extrato, Razão, títulos e resultado esperado do mesmo
   recorte; verificar saldos, sobras nos dois sentidos, parcelas, pagamentos
   parciais/agrupados, tarifas, transferências, estornos e sobreposição. Aplicar
   os 200 itens independentes e os critérios de D-73; 200 itens sintéticos não
   substituem a revisão da cliente nem provam precisão de 95%.
8. **Histórico e recuperação:** executar a auditoria abaixo em escritório
   explicitamente autorizado; revisar achados sem apagar decisões. Ensaiar
   agente/rede indisponíveis, retry, reinício, revogação, reativação e retomada
   em até 15 minutos; restore até quatro horas e demais gates D-73.
9. **Saída e aceite:** se houver arquivo ERP no resultado Q-47, conferir
   importação/retorno e ausência de duplicidade antes de habilitar o gate
   contábil. Registrar release, contagens, erros, responsável e aceite.
   Realizar treinamento inicial e acompanhar os primeiros usos.

Auditoria somente leitura, após preparar o ambiente autorizado:

```text
python manage.py audit_ofx_integrity --organization UUID_DO_ESCRITORIO
```

A saída traz contagens de problemas, `read_only=true` e `homologated=false`.
Zero achados ou nenhum registro não equivale a aceite. Não executar contra
outro escritório nem corrigir histórico automaticamente.

## Próxima dependência concreta

**Responsável:** fornecer o acesso prometido ao PC por canal protegido e definir
com a cliente uma empresa/conta/mês autorizado, extrato, Razão já conferido,
fonte/lista de títulos e plano de contas/DE-PARA existente. **Desenvolvimento:**
completar os adaptadores e a ligação dos fluxos sobre essa evidência, validar
as regras/destino remanescentes e executar o piloto. Não solicitar novamente
modalidade local, computador de instalação ou inclusão de pagar/receber.

Sem esse material, a conclusão contratual e o aceite continuam pendentes.
Não houve deploy, instalação remota, consulta ao ERP, baixa, escrituração,
transmissão, IA externa, mensagem a terceiros ou custo nesta entrega.
