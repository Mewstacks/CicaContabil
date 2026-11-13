# Carteira CONTAD — contrato de integração em implementação

**Continuidade D-333/D-334/V-352 — 11/11/2026:** **SVAPL02/1.0.7** atualizado
por download direto no servidor, Running/Auto/LocalSystem/ready, configuração
protegida preservada e sem reboot às18:31:19 UTC. Backend **release83**, PR7/main
1a0f30b, fonte ffe2be3/CI43071093213, migração aditiva0080 e665 hashes conferidos.
**Primeira carga A concluída:146/146**,145 criações/uma atualização/zero ignorados,
mesmo scan fc7eed16/revisão ebd69a73. Releituras reais sem duplicatas ou mudança
nos valores/identidades; última conferida às18:34:23 UTC. Onze fingerprints
protegidos e campos anteriores da SURIA/CNPJ/conta/163 movimentos preservados.
Inscrição e tipo de origem ficam literais em campos próprios, sem inferir CPF/CNPJ,
completar zeros ou derivar raiz comercial. Perfil0/11/14 coincide com a origem.
**Não repetir upgrade, manifesto, corte, pareamento ou sondas já concluídas.**
M=10 permanece não classificado/fora do primeiro recorte, sem ser marcado inativo.
Download oficial por versão disponível, sem transferência manual de arquivos;
a1.0.7 não implementa instalação automática de versões futuras. AnyDesk aceito,
mas entrada falhou na ferramenta; instalação real foi feita pelo comando direto.
Próximas dependências: M quando comprovado, relações/contas/Razão/títulos,
Q-46/Q-47, IA/D-73, recuperação, treinamento e aceite. Projeto não concluído.
Os estados anteriores abaixo registram a sequência histórica das entregas.





**Revisão de destino D-324 (09/11/2026):** nova instalação será no Windows Server
como agente oficial, com candidato sem coleta e corte explícito/revogação do
anterior. Implementação local em desenvolvimento; nenhuma troca real realizada.
[Procedimento técnico e limites](contad-agente-oficial-windows-server.md).
As provas da release 75 abaixo continuam históricas e não cobrem essa mudança.

**Estado verificado em V-328:** backend publicado na release 75, fonte c8b0c50,
[CI 42355490505 aprovado](https://github.com/Mewstacks/CicaContabil/actions/runs/42355490505).
MSI 1.0.4 aprovado em Windows descartável; upgrade no PC e inventário real
aguardam o operador, que confirmou indisponibilidade. Manifesto real continua
piloto, com uma empresa/conta e 163 eventos. Esta fase não conclui o projeto.

| Capacidade | Implementada/testada | Publicada | Provada na CONTAD | Homologada/aceita |
|---|---|---|---|---|
| Protocolo/recepção da carteira de empresas | Sim; PostgreSQL, reenvio e concorrência | Backend 75 | Ainda sem scan real | Não |
| Inventário de metadados/contagens | CI Windows/contrato ODBC real e limites aprovados | Script/hash entregues | 601 objetos/5.674 colunas/502 empresas informados; JSON pendente | Semântica não revisada |
| Agente oficial 1.0.5 | 62 testes/26 checks Windows, MSI/hash aprovados | MSI oficial preservado | SVAPL02/ready/LocalSystem após reinício | Instalação/corte validados; fontes completas pendentes |
| Contas/referências/Razão/títulos | Contratos anteriores não equivalem a adaptadores reais | Nenhuma fonte nova ativada | Piloto bancário anterior preservado | Não |
| Treinamento | [Guia preparado](pt-BR/contad-conciliacao.md) | Documento disponível | Não executado | Não |

D-323, PC-19, etapas 03/09/12, Q-28/Q-46/Q-47. Histórico financeiro solicitado:
**01/09/2026 em diante**. Cadastros e contas devem ser inventariados integralmente.
Este documento descreve o contrato técnico; não é um segundo plano de execução.

## Capacidade desta implementação

O manifesto `dominio-portfolio-v1` identifica o UUID do escritório, fontes
permitidas, período financeiro e mapa revisado de situações do cadastro. Sua
revisão SHA-256 cobre todos os campos. A versão inicial aceita **somente
`companies`**: não afirma ler contas, Razão ou títulos. Cada fonte adicional
exige contrato e semântica conferidos no Domínio real antes de ser habilitada.
O início financeiro do manifesto não restringe a leitura dos cadastros.

O agente novo mantém `scoped-v1` enquanto estiver no manifesto piloto, inclusive
para retorno à release 73. No manifesto de carteira usa `scoped-v2`. O servidor
permite buscar configuração/heartbeat com o protocolo anterior para a transição,
mas recusa ingestão de carteira por cliente antigo. Códigos de carteira não
são consumidos por pareamento incompatível. **Atualizar a mesma máquina não
exige novo pareamento.** A troca para outro computador em D-324 exige novo
UUID/segredo, sem copiar DPAPI, candidato pendente e corte explícito. A recepção
preserva dados/scans anteriores; o novo agente inicia seu próprio scan.

`POST /api/agent/v2/dominio/portfolio/companies` oferece abertura/retomada e
confirmação de páginas de até 500 empresas, na ordem numérica de `CODI_EMP`.
A consulta projeta somente código, nome, identificação cadastral e situação de
`GEEMPRE`, incluindo situações não ativas. A ordenação usa parâmetro numérico,
não o cursor textual que ordenaria 100 antes de 20.

`AgentCompanyScan` registra escritório/agente/revisão, contagem de origem,
cursor confirmado, contagem recebida, páginas e último recibo/digest. Página,
cadastros e cursor são uma transação. Reenvio idêntico da última página devolve
o recibo, sem reaplicar; falha antes do commit conserva o cursor. Reinício
retoma do cursor guardado no servidor. Uma página inválida rejeita todo o lote.
Trava do agente serializa requisições concorrentes e revalida revogação/recorte.

A conclusão exige declaração de fim, contagem inicial/final igual e quantidade
recebida igual. Mudança de contagem abandona a varredura anterior, conservando
histórico/dados, e a próxima abertura começa do zero. Após conclusão, o ciclo
seguinte relê os cadastros e aplica correções de origem sem duplicar identidades.
Isto é **varredura por chave**, não snapshot transacional do ERP: mudanças com
contagem igual durante a leitura podem exigir o ciclo seguinte. Não comprova
uma fotografia consistente nem substitui a homologação de atualização real.
O teto de um milhão de cadastros é explícito e recusa a carga; não corta dados.

V-328 corrige a leitura que podia permanecer presa quando uma divergência
de cobertura era seguida pelo retorno da contagem original. A recusa 409 com
`code=source_count_changed` ou `coverage_mismatch` abandona a leitura aberta
atomicamente, guarda erro/horário e conserva as páginas anteriores. A próxima
abertura começa do zero, mesmo com a mesma contagem. Solicitação atrasada não
abandona o progresso atual; recibo de carga concluída continua repetível.
O protocolo e o MSI 1.0.4 anterior permanecem compatíveis.

## Diagnóstico administrativo de cobertura

No ambiente administrativo do servidor, o comando somente leitura
`python manage.py portfolio_sync_status --organization <UUID-ou-slug>` apresenta
estado do agente, último heartbeat/idade, contagens, conclusão/abandono e erros.
`--agent <UUID>` limita ao agente do mesmo escritório; `--limit 1..100` limita
scans por agente e informa quantos foram omitidos. Não imprime segredos, DSN,
nomes de empresas, documentos ou valores financeiros. No PostgreSQL usa
transação própria REPEATABLE READ/READ ONLY; recusa chamada dentro de outra
transação. O diagnóstico não marca sincronização ou aceite como concluídos.

A execução real em V-328 retornou manifesto piloto e zero scans da carteira.
Os testes de reinício/erro/concorrência são PostgreSQL sintéticos, ainda sem
prova dessa carga no Windows. O uso normal pela Grazi continua pela interface;
este comando é para operação técnica e não exige ação da cliente.

Código é único dentro do escritório. O mapa aprovado define `active` e a
situação bruta fica em `ClientCompany.dominio_status`. Situação desconhecida,
identificação fora do contrato, nome excessivo ou chave inválida interrompem
a página com erro; não são ignorados. Ausência em página/varredura não apaga
nem desativa cadastro. Semântica A/I dos testes é **sintética**, não aprovação
do mapa real da CONTAD. O novo caminho não escreve movimentos, partidas ou
decisões de conciliação e não habilita exportação/IA.

## Inventário para o operador

`agent-windows/inspect-contad-schema.ps1` executa no PowerShell x64, usa o DSN
CICA_CONTAD existente e solicita a credencial **somente no próprio Windows**.
Não lê senha do registro/configuração do agente. Lê metadados de GEEMPRE, CT*
e objetos EF pertinentes a títulos/contas; consulta apenas contagens agrupadas
por situação em GEEMPRE, após verificar suas colunas. Não consulta históricos,
nomes de clientes, documentos ou valores financeiros nessa sonda.

Limites explícitos: 1.500 objetos, 50.000 colunas, vinte situações; excesso
interrompe sem apresentar resultado parcial como completo. Resultado JSON em
nova pasta Downloads restrita ao usuário, SYSTEM e Administradores, sem upload.
Metadados não aprovam chaves/relações, interpretação de baixas, cancelamentos,
sinais ou equivalência de situações. Documentação usada para a API de metadados:
[Microsoft OdbcConnection.GetSchema](https://learn.microsoft.com/dotnet/api/system.data.odbc.odbcconnection.getschema).

`agent-windows/upgrade-configured-contad.ps1` é específico para **1.0.3 → 1.0.4**,
com MSI/manifesto/hash conferidos, sem novo código, descriptografia da configuração
ou alteração do DSN. Confere preservação dos bytes criptografados, versão real,
serviço e ciclo novo. Diferentemente do roteiro de PC de teste, aceita a
configuração já existente. Não usar `test-installer.ps1` no PC CONTAD: ele instala
e remove serviços somente em runner descartável. Bytes aprovados estão em
Downloads/CICA-CONTAD-1.0.4-e9311eb; upgrade real aguarda o operador. Retorno funcional:
manifesto piloto e imagem anterior, mantendo dados e esquema aditivo.

## Condições para avançar

Inventário real e confronto de situação/contas/fontes são o próximo insumo
Q-28. A recepção de cadastros não homologa Razão, títulos/parcelas/baixas,
DE-PARA Q-46, saída Q-47, D-73 ou treinamento/aceite. O manifesto instalado
permanece piloto até alteração operacional validada. Cada verificação pertence
à versão e ao ambiente registrados em VALIDACOES.md.

Continuidade D-329/V-342 (10/11): backend do agente integrado na main e publicado
na release 80. ODBC interativo do SVAPL02 comprovado em V-340;
pareamento e provas de serviço/LocalSystem/corte ainda pendentes. Mesma revisão
de manifesto/piloto e MSI 1.0.5; esta liberação não amplia a carteira/fontes.

## Transição administrativa preparada — D-331/V-349

configure_agent_portfolio foi publicado na release 81. Exige --organization,
--agent, --expected-scope-revision, --inventory, --review e --period-end.
Sem --apply apenas verifica e mostra a prévia; --apply muda o manifesto sob
travas organização/agente e auditoria. Não exige novo pareamento ou MSI.
Não executar antes de receber e revisar o JSON real. Evidência recente (24 h),
completa e de até 12 MiB; revisão de até 32 KiB, sem campos repetidos, vinculada
ao hash/UUIDs e dono/administrador ativo. A revisão possui exatamente:
version=contad-company-status-review-v1, organization_id, agent_id, reviewer_id,
inventory_sha256, review_reference, agent_version e company_status_map.
Mapa deve cobrir exatamente os códigos observados, com booleanos revisados;
não preencher A/I por causa dos exemplos sintéticos dos testes.

Somente piloto → companies nesta fase, heartbeat oficial recente e nenhuma
substituição em aberto. Revisão anterior esperada impede mudança concorrente;
repetição idêntica usa auditoria original. UUID/segredo/dados/recibos permanecem.
Ao trocar, o modo companies pausa leitura financeira do piloto e mantém seus
dados. Isso não entrega contas/Razão/títulos ou carga financeira da carteira.
Primeira execução operacional continua pendente; diagnóstico de cobertura deve
confrontar todas as empresas e preservar situações inativas e campos desconhecidos.

## Seleção na origem — D-332/V-350

A solicitação passou a ser buscar somente empresas ativas. `dominio-portfolio-v2`
exige `company_selection=active_only` e `scoped-v3`; sua revisão cobre a seleção.
Agente1.0.6 usa a mesma condição ODBC parametrizada na contagem e em cada página,
com cursor numérico e limite500. Somente situações com valor true são lidas;
cliente e backend recusam qualquer linha fora da seleção. V1 continua permitindo
situações inativas revisadas, conforme contrato histórico acima.

Inventário original recebido/reconferido: A146/I346/M10. Primeiro seletor usa
somente A, já empregado pelo conector existente. M permanece não classificado,
fora dessa primeira seleção e sem gravar active=false. Ausência não apaga nem
desativa cadastros/histórico. Isto não é prova de cobertura de todas as situações.

A exceção administrativa `--active-only --existing-active-selector` aceita apenas
review version `contad-active-selection-review-v1`, reviewer_id=null, mapa A=true
e referência D-332; actor=None/review_origin=existing_active_selector na auditoria.
Mantém hash original/UUIDs/24h/heartbeat/CAS/--apply e exige cliente1.0.6. Não usar
a exceção para M/outros mapas nem atribuir aprovação à Grazi. Revisões normais
mantêm cobertura integral e dono/administrador ativo.

`inspect_agent_inventory` valida metadados sem aprovação ou consultas ao banco.
`configure_agent_portfolio` permanece em prévia por padrão. Pacote novo contém
`upgrade-active-companies.ps1`, específico1.0.5→1.0.6; script de teste CI nunca é
entregue à cliente. Atualização real e aplicação/scan continuam pendentes.

Próximas fontes: CTCONTAS/CTCONTACAIXA/relação bancária, CTLANCTO/CTCLANCTO e
CTCCUSTO observados no inventário. Antes de qualquer join, conferir chaves,
plano próprio/compartilhado (CODI_EMP_PLANO), partidas/sinais/cancelamentos e
confronto do Razão. Nomes de objetos EF tributários não comprovam contas a
pagar/receber, parcelas ou baixas. Nenhuma fonte financeira nova habilitada.

## Inscrição literal e primeira carga real — D-333/D-334/V-352

`scoped-v4` no mesmo manifesto A usa exatamente codigo/nome/status/registration_raw,
com registration_type_code opcional/nulo. Inscrição é texto até14 sem controles,
com apenas padding de espaço removido; tipo é código nulo/0..255. Não interpretar
CPF/CNPJ por comprimento/código, preencher zeros ou gravar raiz comercial. Campos
ClientCompany.dominio_registration_raw/type_code guardam origem; CNPJ existente
permanece. V3 mantém contrato anterior; a representação v4 exige cliente1.0.7.

Migração0080 aditiva com default de banco, release83 e665 hashes conferidos.
MSI1.0.7/upgrade real aprovados; não há novo manifesto ou pareamento. Scan fc7eed16
retomado e concluído146/146,145 criações/uma atualização/zero ignorados; releituras
não duplicaram nem mudaram valores/IDs. Onze fingerprints protegidos e SURIA/
CNPJ/conta/163 movimentos preservados. M10 permanece não classificado e ausente.

Download por versão: https://github.com/Mewstacks/CicaContabil/releases/tag/agent-v1.0.7
ZIP genérico/hash conferidos; comando baixa/verifica/extrai e atualiza, sem copiar
arquivos manualmente. Não é auto-instalação permanente. AnyDesk recebeu aceite,
mas ferramenta não conseguiu enviar entrada; execução real veio do operador pelo
comando direto. Não usar jobs de backup/arquivos como mecanismo de execução.
Próximo avanço técnico são relações/fontes financeiras, não repetir esta instalação.

## Relações das fontes — D-335/V-353

Complemento e contrato em `docs/contad-relacoes-fontes.md`; consulta somente
catálogos, com chave composta e primary_column_id explícitos.46 testes locais/
12 cenários Windows aprovados; comando direto/hash conferidos. Aguarda resultado
real, sem atualizar agente1.0.7 ou habilitar datasets de contas/Razão/títulos.


## Coleta financeira mensal com escopo explícito — D-356 (candidata local)

A candidata de código1.0.10 remove o recorte fixo do caminho de Razão, mantendo
as três consultas SQL e seus hashes. Não é o agente oficial instalado1.0.9,
MSI aprovado ou cobertura real da carteira. O catálogo continua literal: nenhuma
conta é declarada ativa/analítica e nenhum plano compartilhado é inferido.

`queue_portfolio_ledger` recebe organização, oficial, conta existente, solicitante,
referência da conferência e `--scope-file`. O arquivo contém os mesmos onze
campos do piloto, agora validados por tipo/limite: empresa, empresa do plano,
filial, conta bancária, sentinela zero, lado da entrada, início/fim exclusivo
de um mês desde09/2026 e contagens de linhas/lotes/efeitos. O mapeamento e as
contagens precisam de prova da origem; a ferramenta não os inventa dos cadastrosA146.

Sem `--allow-financial-capture`, o comando só faz a prévia e retorna hashes.
Com a confirmação operacional aplicável, cria um job auditado por escopo.
Repetição não cria outro job e não altera recibos existentes. A recepção
revalida acesso atual, conta/empresa e hashes; revogação posterior bloqueia
entrega e importação. O plano contábil explicitamente escolhido deve coincidir
com cada conta do catálogo, mesmo quando difere da empresa fiscal/contábil.

O agente novo declara `portfolio_scope=true`. O backend continua atendendo
1.0.8/1.0.9 sem essa capacidade exclusivamente no piloto original; não manda
a eles jobs ampliados. Publicar backend compatível antes de atualizar agente.
Candidata de upgrade1.0.9→1.0.10 e ensaio Windows estão preparados nos arquivos
`upgrade-portfolio-ledger.ps1` e `test-portfolio-ledger-upgrade.ps1`. Não executar
o ensaio de CI em cliente. Windows/MSI/upgrade reais ainda precisam de prova exata.

Limites preservados:50.000 linhas,5.000 contas,2MB, mês completo e um efeito
bancário por lote. Excesso/multipartida incompatível vai para recusa/revisão,
sem truncar ou forçar vínculo. Escopo zero/zero/zero pode registrar fotografia
vazia, sem criar eventos. Comparar cobertura por empresa/conta/mês após a
coleta real; essa preparação não implementa descoberta automática de todas
as contas, situaçãoM, agendamento recorrente ou retomada operacional homologada.
## Sugestões DE-PARA antes da conferência do catálogo

O preparo administrativo aceita `depara_ai ... prepare --input <privado.json>
--native-collection <uuid>`. A coleção deve estar importada, pertencer à mesma
conta/empresa/escritório e manter fonte, hash e escopo íntegros. O arquivo de
entrada continua contendo apenas `items` (até quatro) e `candidate_codes`
(de dois a doze, incluindo a conta bancária). A procedência integra o fingerprint
do lote e é reconferida antes de cada uso.

Esse caminho não interpreta tipo/situação brutos nem cria `LedgerAccount`.
Permite sugestões preliminares sobre as contas do catálogo retido; nomes fora
do vocabulário técnico são omitidos no payload externo, e a conta bancária
recebe rótulo genérico. Projeções de históricos devem ser identificadas como
reduzidas e conservar a referência privada ao original para revisão.

A geração mantém os mesmos gates de acesso, política, teto e reserva única.
O pacote privado de revisão informa `requires_chart_review=true`. Para criar
uma regra, as contas efetivamente escolhidas precisam existir como ativas e
aptas a lançamentos no plano confirmado; a regra permanece em rascunho e
exige ativação separada. Sugestão IA não comprova a legenda do catálogo,
adequação contábil, saldo ou aprovação humana.
