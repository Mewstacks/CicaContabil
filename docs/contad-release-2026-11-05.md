# Release candidata CONTAD: revisão e operação

D-311/V-312 e D-312/V-313, PC-19, etapas 03/09/12. Este roteiro complementa os gates e
checklists existentes. **Preparação local; não publicado, homologado ou liberado.**
Prazo contratual 09/11/2026 preservado. A suíte inteira não integra este recorte.

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
