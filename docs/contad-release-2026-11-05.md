# Release candidata CONTAD: revisão e operação

## Release vigente — D-321/V-324, 06/11/2026

**Release Fly 73**, fonte 651368c101bec5b8b0bb9a75b4fb1268029dd220,
[CI 42282953292 aprovado](https://github.com/Mewstacks/CicaContabil/actions/runs/42282953292).
Imagem registry.fly.io/cica-contabil@sha256:20f01b3888c8fa02395a876e6b4597fbf49db7a29a0919e288d3a9b78979717a.
Candidata 820 arquivos, ZIP 600af5819f7cd90f61bafbafc586f4f168bbe1e56acff2d1f7ecfb7cbb58c2b6.
647 fontes runtime/hash agregado be6a65a2754a42c4e63f77c4ea1b8e9b26e149243eb20b63763c2aeb43a08772
conferidos em web/worker. Migrações/Neon original preservados, health 200,
banco/cache ok, worker ready, recursos 512 MB e reserva parada preservados.
Exportação Domínio false; prévia limitada à CONTAD e não homologada.

Contrato individual/Conciliação/escritório ativos conforme autorização, sem
convite/cobrança automática. Conta pessoal Grazi criada depois em D-321/V-325,
Proprietária somente CONTAD, login HTTPS/Conciliação 200 e importação disponível;
sem novo deploy ou arquivo importado na verificação. Agente 1.0.3 pareado no recorte
explicitamente aprovado; operador comprovou Running/Auto/LocalSystem/ready após
reinício e ausência dos campos de senha do novo CICA_CONTAD x64. Backend:
163 itens, conector healthy, sem duplicações/fora do recorte e datas/valores
conferidos. Falha inicial icacls corrigida com execução elevada; credencial
órfã revogada e código substituto consumido. Não emitir novo código se ready.

Retorno de aplicação: imagem release 72 abaixo, preservando esquema aditivo,
dados/ativação/credencial válida. Backup D-320 não foi refeito: só manifesto e
metadados/53 objetos foram reconferidos; mesma validade até 13/11/2026.
Resultados/limites em V-324 e [continuidade](contad-continuidade-2026-11-06.md).
As próximas seções documentam a implantação anterior e a preparação histórica.

## Implantação anterior — D-320/V-322, 06/11/2026

Para o estado mais recente dos testes guiados, documentos da cliente e
pendências de vínculo/saldos/pareamento, leia o
[resumo de continuidade](contad-continuidade-2026-11-06.md).

Publicação concluída na **release Fly 72**, em 06/11/2026, fonte f86ae4d e
[CI 42231907397 aprovado](https://github.com/Mewstacks/CicaContabil/actions/runs/42231907397).
Imagem registry.fly.io/cica-contabil:contad-f86ae4d-20261106, digest
sha256:3f5f91ec176db121531a1e26176a1054f8001088fb273eea88e99b11ede832eb.
App existente cica-contabil/mewstack-629, web/worker originais/512 MB ativos e
reserva parada preservada. Prévia privada não homologada, distinta de
AccountingExport, limitada ao UUID CONTAD. Exportação Domínio false; importação
efetiva no ERP não faz parte desta entrega. Migrações dos dois aliases Neon
agora hub.0078/intelligence.0031, endpoint original preservado. Os 645 arquivos
de fonte do runtime foram confrontados com a candidata em web/worker; health
nos dois domínios 200, banco/cache ok, worker ready e check Fly passing.
Requisição de agente inválida 401; prévia/download anônimos 302 para login.

Candidata: `.tmp/contad-development-2026-11-06/release-candidate-final/`,
816 arquivos; SHA-256 `ced90f343ddbb08c82c7950cc7125a68d712e086708d9f317f06c203834a3eaa`.
Preservar **hub.0076/0077/0078 e intelligence.0031** no retorno da aplicação;
release command aplica migrações pelos endpoints diretos em ambos os aliases.
O esquema é aditivo; não fazer rollback apagando tabelas/evidências.
V-322 discrimina regressões e verificação final, navegador e limites.
Migrações e 42 testes focados aprovados também em PostgreSQL **18.6** descartável
(21,62 s), mesma versão do servidor observado; não comprova recuperação Neon.

O operador instalou MSI 1.0.3 íntegro no PC **CONTAD**: informou Running/Automatic,
ProductVersion correspondente e awaiting_configuration. Isso supera ausência
inicial do agente; o PC Fedrizzi anterior é outro ambiente. Responsável informou possuir EXTERNO e Test Connection successful no novo
DSN x64 CICA_CONTAD e conexão confirmada no configurador instalado. Faltam
confirmar modo de autenticação, LocalSystem, recorte/acesso, pareamento e envio.
Usar SQL Anywhere 17 x64 para conexão própria do serviço, preservando DSN x86.
Nenhuma senha deve ser copiada do registro ou informada no chat.

CONTAD é escritório próprio, UUID **ae13d06f-6461-43a8-a9cc-3e0e0eafde50**,
provisionado em activation_pending com auditoria e zero membros, sem contrato
inventado, demo ou parceiro interno. Login responsável indicado em evidência
privada; nenhum convite enviado ou senha criada. Cadastro não equivale a acesso
ativo. Não reutilizar Bianchi/Cobalchini; fechar ativação e recorte antes de parear.

**Gate pontual de backup/retorno cumprido em 06/11/2026:** snapshot
Neon snap-hidden-tree-b6xt5ssj de 14:29:44 UTC/648.298.496 bytes, expira em
13/11/2026 14:29:44 UTC. Restore isolado br-soft-pond-b6b07dau conferido desde
Fly, sem trocar produção: default 180 tabelas/356.077 linhas e knowledge quatro
tabelas/193 linhas, esquemas/migrações/contagens iguais; hashes de sete tabelas
críticas do default e todas as quatro do knowledge iguais. Arquivos: 53
referências cobertas, 53 objetos/2.901.052 bytes recuperados em temporário no
Fly com hashes iguais e limpos ao terminar. Manifesto privado final pareado
com o snapshot, SHA-256 9cb388132280969bf4e43ef03cd8c60a82684f3a8782b1df613c5577d9453443.
Originais preservados e expiração restrita ao novo prefixo Tigris, sete dias.
Compute do ensaio suspenso/idle em menos de 30 minutos; branch expira junto do
snapshot. Chave project-scoped temporária revogada, HTTP 401 verificado e
cópias locais removidas. Nenhum dump no Mac. Teto US$ 1,00 aprovado; cobrança
final não medida. RPO/agenda recorrente/D-73 permanecem pendentes.

Gate cumprido e candidata publicada/verificada; Q-47 continua false. Isolamento
por carteira e integridade foram verificados com cenários sintéticos, sem alegar
percurso autenticado de cliente em produção. Depois de acesso/ativação e
recorte/autorização Q-28, parear 1.0.3 e provar leitura
LocalSystem, paginação/repetição/retomada. Q-46/Q-47, IA Q-08/Q-09, D-73,
treinamento e aceite ainda se aplicam. As seções seguintes são histórico das
candidatas anteriores e não substituem esta continuidade.

Continuidade D-315/V-317: retorno da revisão preserva filtro/página após ações,
93 testes/24 subtestes locais e navegador desktop/celular/claro/escuro aprovados.
Candidata atual em `.tmp/contad-navigation-2026-11-05/release-candidate/`:
809 arquivos, 2.023.623 bytes, SHA-256
`bc293cc85bbf3191d6f0d5e0c8f27171c72508c4b47d76ab2572c34b9f8d4542`.
809 hashes de ZIP/workspace conferidos. Sem migração/alteração de agente/gates.
CI 42079806454 aprovado para a implementação anterior 700b496, com limites em
V-317; a candidata nova ainda depende de seu próprio resultado remoto.

D-311/V-312, D-312/V-313 e D-313/V-314, PC-19, etapas 03/09/12. Este roteiro complementa os gates e
checklists existentes. **Código publicado no GitHub; aplicação ainda não
implantada, homologada ou liberada.**
Prazo contratual 09/11/2026 preservado. A suíte inteira não integra este recorte.

Continuidade D-314/V-316: percurso bancário real local passou em 42 verificações;
corrigidos proteção do editor humano e relatório com aviso de proteção.
134 testes/24 subtestes PostgreSQL aprovados, zero skips. Nova candidata em
`.tmp/contad-bank-pilot-2026-11-05/release-candidate/`, 809 arquivos, 2.023.175
bytes, SHA-256 `a3cd63af4679d0e3067657ffaa6a1f6361a57e4dedea2e50b2a0ce5d2ec6e88c`.
Sem migração/agente/UI novos. O pacote V-313 abaixo é histórico preservado.

Autorização expressa de publicação na main executada no commit
[4fede1e](https://github.com/Mewstacks/CicaContabil/commit/4fede1e7f5b1bcfaec8b430a3b0f0d8c4d579b1d),
SHA remoto conferido. CI 42067809017 aprovado para esse SHA: PostgreSQL 1.633
testes/151 subtestes, dois skips; agente, build Windows e três builds Docker
aprovados, com ambientes/limites em V-314. Os hashes de código
da candidata local abaixo permanecem iguais; registros Markdown não integram
o ZIP de fonte. Nenhuma imagem hospedada, migração remota ou configuração do PC
foi alterada pelo envio ao GitHub.

## Artefatos

`scripts/prepare_contad_release.py --output <pasta-nova>` prepara ZIP do código
do workspace e manifesto SHA-256 por arquivo. Não usa o índice para substituir
arquivos modificados, não inclui Downloads, `.tmp`, `.env`, artefatos MSI ou
configuração real do agente; não altera Git ou serviço externo. Recusa destino
com pacote existente, links simbólicos e arquivos protegidos no inventário.
O ZIP é reaberto e cada arquivo é confrontado com o hash antes do manifesto.

A base Git é `b499cd1`; a candidata contém mudanças locais anteriores D-305–310
e D-311/D-312. O commit isolado do MSI não é o commit do backend. Pacote e manifesto
desta rodada ficam em `.tmp/contad-delivery-2026-11-05/release/`; os hashes
efetivos e os resultados estão em `test-results.json` no diretório pai.
Mudança de código posterior exige novo pacote/revalidação correspondente.

A candidata atual, após a prévia offline D-312, está em `release-title-preview/`
no mesmo diretório privado: 809 arquivos, 2.022.148 bytes, SHA-256
`db4085a89ff9215893478c51cae78c556284a303a2a013ed0b5e30040991b2e8`.
Inclui núcleo/CLI/testes; 809 hashes reconferidos contra ZIP/workspace.
V-313 registra 85 testes focados e CLI sintética; V-312 conserva a regressão
completa anterior. Não são uma única bateria nem homologação. A CLI offline
não exige alteração de migração, worker, agente, parâmetros ERP ou gate contábil.

Agente preparado: MSI **1.0.3**, commit
`1bf854958cecae319abc050241f7b83753903265`, CI histórico 41854423194,
SHA-256 `5850a351f9ea54f4b72131c840af5a34534ce9bbe521c62ec605a32695fd8253`.
Bytes reconferidos nesta rodada; não instalado. Pacote de teste sem Authenticode.
O PC conserva 1.0.1.0 segundo V-311; RDP acessível nesta rodada, sem novo MSI
instalado ou preflight completo de atualização.

## Antes da publicação autorizada

1. Acesso Fly e autorização específica ainda necessários. Não pedir novamente
   o acesso indisponível, efetuar login por inferência ou acionar deploy/CI.
   Operador autorizado confronta app, release/imagem efetivos, processos e
   configuração; não assume que o estado hospedado corresponde ao workspace.
2. Preservar release anterior, configuração não secreta e recuperação protegida
   dos segredos. Backup de banco e objetos deve pertencer ao mesmo ponto
   consistente, com contagens/hashes. Não imprimir credenciais ou dados reais.
3. Conferir `hub.0076_accountingentry_account_reference_and_more` →
   `hub.0077_independent_ledger_record` e `intelligence.0031_agent_sync_scope`.
   São aditivas. A rodada ensaiou aplicação em PostgreSQL descartável, sem
   migração no banco de desenvolvimento, produção ou ERP. Não regredir essas
   migrações para retornar a aplicação: há identidades/evidências a preservar.
4. Conferir configuração HTTPS/HMAC de D-310, `EDGE_AGENT_MTLS_REQUIRED=false`
   para esse percurso e validação normal do certificado do servidor.
   Não criar CA/gateway/novo ingresso. Instalações antigas com `true` explícito
   conservam sua exigência; não alterar outros ambientes por inferência.
5. Manter o gate contábil `RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED` desligado
   enquanto Q-47 não tiver homologação real. Testes usam override apenas em
   banco sintético. IA real continua sujeita a Q-08/Q-09; nenhum limite foi criado.
6. Revisar imagem Linux/Tesseract português/fontes, web/worker/Beat/storage,
   health e compatibilidade com agente 1.0.3. Publicar apenas a candidata revisada
   quando autorizado; sondagem sem código deve recusar cadastro HMAC inválido
   sem erro de CA. Isso não cria agente nem autoriza envio financeiro.

## Atualização e percurso do piloto

Após preflight real, conferir bytes/manifesto/guardas do MSI e do roteiro
`agent-windows/test-upgrade-windows11-pc.ps1`. Exige origem suportada, GUI
fechada e ausência de configuração inesperada. **Não executar
`test-installer.ps1` no PC**; ele remove o agente no runner descartável.
Preservar autenticação do DSN e políticas/firewall existentes.

Antes de emitir código/parear, confirmar escritório/destino, equivalência da
conta bancária/contábil e competência fechada, com IDs revisados em manifesto.
O candidato de 115 itens da Fedrizzi fica privado e não atende D-73 por si só.
Leitura autorizada não é autorização de transmissão. ODBC sob LocalSystem,
HTTPS/HMAC Windows, recorte, replay, queda entre páginas e retomada precisam
ser demonstrados no serviço real. A prova interativa antiga não os substitui.

Q-28/Q-46/Q-47 ainda exigem Razão, títulos/parcelas/baixas, exemplos de exceções,
DE-PARA revisado e layout real. Nenhum SQL foi habilitado nesta rodada. Importação
efetiva no Domínio requer autorização própria e conferência no destino.
Reexportação agora copia o snapshot original íntegro, com mesmo período/destino
e motivo, sem reconstruir fatos mutáveis. Não equivale a nova escrituração.

## Retorno e recuperação

Interromper novo pareamento/envio, preservar logs/evidências e revogar o agente
HMAC antes de retornar a backend/agente incompatíveis. Não converter configuração
HMAC em certificado nem apagar `agent.config`. Recuperar imagem/configuração
anterior verificadas, conservando o esquema aditivo e dados. Conferir health,
filas, contagens/hashes e isolamento antes de retomar. Migração regressiva com
remoção de tabelas não é retorno ordinário.

Restauração local desta rodada usou PostgreSQL e arquivos **sintéticos**:
200 movimentos, 200 registros de Razão e dez alocações confirmadas. Dump/restore
em outro banco descartável confrontou contagens e hash de todas as linhas de
182 tabelas, estado de 15 sequências e hash de dois arquivos. Resultado e tempo
em `postgres-restore-results.json`. Isso não demonstra Neon/objetos/knowledge,
retorno à versão anterior, RPO ou recuperação CONTAD em produção.

Proprietário/operador define RPO e janela de medição; não há número presumido.
Concluir recuperação operacional D-73, 200 itens reais independentes por fluxo,
precisão aplicável, treinamento e aceite antes de liberar PC-19.

## Backup pontual aprovado e executado — D-320

06/11/2026, continuidade de V-322. Acesso ao projeto CICA no Neon resolvido
pelo seletor da organização germano@mewstack.com.br. Projeto
raspy-river-46466568, production/br-odd-tree-b6vhgfnv; os dois aliases hospedados
conferidos no mesmo endpoint. No preflight havia janela de seis horas, sem
snapshots/agenda; o snapshot pontual abaixo foi criado depois.
Não alterar retenção corrente nem restaurar sobre produção por inferência.

Inventário Tigris: cica-contabil-media na organização Fly cica, privado,
53 objetos/2.901.052 bytes, snapshot desativado. Hash do inventário de metadados
48e6075f99a372e268d79a7eb6da2aa0de90f24eab0c2f8bed47f80d496d30b8.
Isso é hash de nomes/tamanhos/ETags/datas, não verificação dos bytes ou backup.
Objetos originais e política de acesso preservados; adicionada apenas a regra
de expiração de sete dias restrita ao prefixo novo.

Operação aprovada até US$ 1,00 e executada em 06/11/2026: um snapshot manual do projeto CICA,
cópia dos objetos para prefixo novo privado dentro do mesmo bucket e conferência
de restauração em branch isolada, até 30 minutos/1 CU, sem trocar produção.
Retenção de sete dias para estas cópias/snapshot, usando expiração explícita;
nenhuma agenda recorrente. Preservar regras existentes do bucket e restringir
a expiração ao prefixo novo. Se a expiração não puder ser confirmada, não
prosseguir com cópias sem nova revisão. Snapshot manual deve ter expiração
própria: as regras de uma agenda não o expiram.

Preparação revisável em `.tmp/contad-development-2026-11-06/backup_objects_review.py`:
modo padrão somente leitura; cópia exige inventário igual, prefixo UUID novo,
limites de volume, ACL private, hash original/cópia, preservação de lifecycle
e manifesto; finalização exige snapshot ID e inventário original ainda igual.
Sem exportar credenciais ou dumps ao Mac, apagar arquivo ou mudar políticas de
acesso. Compilação e quatro verificações sintéticas passaram antes da execução real.
As cópias, pareamento e restauração descritos na continuidade vigente passaram. Mudança de fonte/inventário exige rever o plano, sem ocultar
novos objetos ou aceitar fotografia parcial.

Custo estimado adicional abaixo de US$ 0,10 para este volume e ensaio breve;
**teto US$ 1,00 aprovado explicitamente** antes da execução pontual.
[Neon](https://neon.com/docs/introduction/plans) informa US$ 0,09/GB-mês de
snapshot e US$ 0,106/CU-hora no Launch; cerca de 0,65 GB por sete dias custa
aproximadamente US$ 0,014 em armazenamento. [Tigris](https://www.tigrisdata.com/pricing/)
informa Standard a US$ 0,02/GB-mês e COPY a US$ 0,005/mil, antes de franquias;
53 cópias e 2,9 MB representam fração de centavo. Não tratar franquia como
confirmada nesta conta. Parar se volume, preço ou recurso excederem a proposta.
A retenção pontual não resolve RPO, agenda permanente ou D-73.

### Retorno da aplicação preparado

A imagem anterior da release 71 continua disponível. Se houver falha desta
release, o retorno da aplicação usa a imagem anterior sem desfazer migrações
aditivas nem substituir banco/arquivos por fotografia antiga. Executar a partir
da raiz do projeto, somente quando o retorno for necessário:

```sh
flyctl deploy --app cica-contabil --config fly.toml \
  --image registry.fly.io/cica-contabil:deployment-01M4GGRN0RPCT44F7JRZH4SYH0 \
  --skip-release-command --ha=false --exclude-machines 287e35db920e48 \
  --env RECONCILIATION_DOMINIO_PREVIEW_ORGANIZATION_IDS= \
  --env RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED=false --yes
```

Conferir depois health nos dois domínios, worker e imagem das duas máquinas.
O retorno não foi necessário nem executado; não alegar ensaio da imagem anterior
em produção. O ensaio de dados usou Multi-step restore em branch separada, sem
Migrate connections and settings/finalize. Para recuperar dados no prazo da
retenção, preservar produção, criar cópia pelo snapshot ID, conferir aliases e
restaurar os objetos do manifesto privado para destino isolado antes de propor
qualquer troca. Manifesto final:
`private/operations/backups/contad/59523a7687024acabb6638ca8cc7f0b7/final.json`.
O manifesto contém caminhos e hashes e deve permanecer privado no Tigris.

### Próxima execução no PC CONTAD

O responsável informou possuir a credencial EXTERNO. Falta validar essa
credencial e configurar um **novo DSN de Sistema de 64 bits**
com SQL Anywhere 17, usando os dados reais da conexão. Preservar o DSN x86
existente e os DSNs de usuário; não aproveitar senha salva ou usuário comum da
aplicação por inferência. Digitar a senha diretamente no PC, sem enviá-la ao chat.
O agente 1.0.3 está instalado/Running/Automatic e awaiting_configuration;
não reinstalar só para obter esse diagnóstico.

Antes de salvar/parear, concluir acesso/ativação do escritório e registrar uma
empresa/conta/período e operações autorizadas em Q-28. Em seguida testar a
conexão do serviço LocalSystem, escopo da coleta, reenvio/paginação/retomada e
vínculo exclusivo ao CONTAD. Campos/chaves reais do Razão e títulos continuam
em Q-28/Q-46; não escrever SQL por hipótese ou tratar lançamento fiscal como
partida contábil. Prévia continua não homologada e não autoriza importar no ERP.
