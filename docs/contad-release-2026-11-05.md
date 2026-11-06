# Release candidata CONTAD: revisão e operação

## Continuidade vigente — D-320/V-322, 06/11/2026

Plano de publicação aprovado; a aplicação ainda está na **release Fly 71**,
com hub.0075 e intelligence.0030 nos dois aliases Neon. Acesso ao app existente
cica-contabil/mewstack-629 disponível para pedro@mewstack.com.br; não criar app.
A candidata atual inclui prévia privada não homologada e hub.0078, distinta de
AccountingExport. Manter exportação false e lista de prévia vazia até habilitação
no escritório correto. A importação efetiva no Domínio não faz parte desta entrega.

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
inicial do agente; o PC Fedrizzi anterior é outro ambiente. Sem credencial de
integração somente leitura, DSN de sistema x64, teste ODBC, pareamento ou envio.
Usar SQL Anywhere 17 x64 para conexão própria do serviço, preservando DSN x86.
Nenhuma senha deve ser copiada do registro ou informada no chat.

CONTAD é escritório próprio, UUID **ae13d06f-6461-43a8-a9cc-3e0e0eafde50**,
provisionado em activation_pending com auditoria e zero membros, sem contrato
inventado, demo ou parceiro interno. Login responsável indicado em evidência
privada; nenhum convite enviado ou senha criada. Cadastro não equivale a acesso
ativo. Não reutilizar Bianchi/Cobalchini; fechar ativação e recorte antes de parear.

**Gate antes de deploy:** backup/retorno consistente ainda não confirmado.
Produção PostgreSQL 18.6/Neon (589.570.048/8.175.616 bytes); storage Tigris não
informou versionamento habilitado. Ausência de API Neon no ambiente e falta de
informação do responsável impedem confirmar janela/ponto de recuperação; não
provam ausência de backup externo. Nenhum dump de produção baixado para o Mac.
Verificar recuperação de ambos os bancos e objetos com identificador/data,
retenção, chaves recuperáveis, contagens/hashes e procedimento de retorno antes
de publicar. Restauração sintética PostgreSQL 17 não é essa evidência. Não criar
infraestrutura/custo nem dispensar o gate por inferência.

Após cumprir esse gate, publicar a candidata exata, conferir health/worker e
migrações, recusa HMAC inválida sem CA, isolamento e arquivo privado; manter
Q-47 false. Depois do recorte/autorização Q-28, parear 1.0.3 e provar leitura
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
