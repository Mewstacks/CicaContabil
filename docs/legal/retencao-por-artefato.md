# Retenção por artefato de dado

> **MINUTA PARA REVISÃO JURÍDICA — não é parecer nem texto vigente**

| Campo | Valor |
|---|---|
| Data | 20/11/2026 |
| Base | árvore de trabalho da branch `feat/produto-vendavel` (parte sem commit). Linhas conferidas em 20/11/2026; podem deslocar |
| Fecha | PC-28 em parte (`PLANO-MESTRE.md:124`): retenção por artefato. Exportação e exclusão: Q-49 (`docs/planejamento/duvidas-abertas.md:110`) |
| Caminhos | relativos a `src/apps/`; `config/` = `src/config/` |
| Legenda | **PROPOSTA** = valor sugerido aqui, com fonte, para você aprovar. **DECIDIDO** = já há decisão registrada. **A DEFINIR PELO RESPONSÁVEL** = não há fonte para o número. Nenhum prazo desta minuta vale antes da sua aprovação e da revisão jurídica |

## 1. Quem decide o prazo

| Dado | Papel da Mewstack | Quem decide | Regra |
|---|---|---|---|
| Empresa, nota, documento, conversa sobre cliente do escritório | Operadora | O escritório (controlador), dentro do contrato | A operadora segue a instrução (LGPD art. 39) e elimina quando o tratamento termina, salvo guarda legal (arts. 15 e 16; planalto.gov.br, 20/11/2026) |
| Cadastro do escritório e dos usuários, fatura, trilha de acesso e de segurança | Controladora (`platform/legal.py:86-90`) | A Mewstack, por finalidade e por obrigação legal | O que a lei manda guardar fica; o resto sai com o fim da finalidade |

## 2. A tensão: escritório controlador, Mewstack operadora, evidência imutável

| Pergunta | O que a regra diz | O que o código faz hoje |
|---|---|---|
| Quem manda no prazo do dado do cliente? | O escritório. A operadora elimina ao fim do tratamento (LGPD arts. 15, 16 e 39) | Nenhum comando elimina. Encerrar é arquivar: o acesso é recusado e o dado fica (`platform/services.py:86-111`; `hub/views.py:1100-1104`) |
| E a guarda fiscal? | É obrigação de quem escritura: livros e comprovantes ficam até prescrever o crédito tributário, de prazo-base de 5 anos (CTN arts. 173, 174 e 195, parágrafo único; planalto.gov.br, 20/11/2026); o termo inicial é ponto para o jurídico. O escritório decide se a Mewstack guarda por ele | A evidência fiscal é **imutável por desenho**: o objeto não se altera nem se apaga, nem em lote; a empresa e o escritório têm `PROTECT` (`hub/models.py:509-541`; `common/models.py:13-20`; `platform/models.py:606-609`). Apagar exige caminho fora do aplicativo |
| O que a Mewstack guarda por obrigação própria? | Fatura, contrato, trilha de acesso e de segurança (Q-49 as trata como registro contábil da Mewstack) | Retidos, sem prazo escrito |
| Cópia e backup | O texto promete informar o ciclo de eliminação em backup (`platform/legal.py:77-79,125-127`) | Neon guarda 6 h de histórico (`docs/comercial/proposta-precos.md:290`); Postgres antigo da Fly parado com volume (`DECISOES.md:880`); sem rotina |

**Opções para decidir o encerramento (Q-49).** Nada está decidido; o anexo já promete A e D sem comando (`platform/legal.py:178-184`).

| Opção | O que faz | Custo ou risco |
|---|---|---|
| A | Exportar, esperar o prazo contratual e só então apagar tudo que não seja registro da Mewstack, com comando próprio, confirmação digitada e revisão jurídica (recomendação de `docs/planejamento/duvidas-abertas.md:110`) | Escrever e testar o comando; ele precisa de caminho que atravessa o "imutável" |
| B | Anonimizar: manter contagens e hashes, apagar `original_xml` e as colunas de pessoa | Exige exceção ao "imutável" e prova de que a evidência ainda serve |
| C | Reter fechado: manter N anos depois do contrato, sem acesso | Precisa de base legal e de cláusula; custa armazenamento e risco |
| D | Devolver a custódia (ZIP e bucket) e apagar em X dias | Precisa de prazo de entrega e de confirmação de recebimento |

## 3. Por artefato

| # | Artefato | Hoje no código | Prazo | Por quê (linguagem simples) | Falta |
|---|---|---|---|---|---|
| R-01 | **Empresa-cliente** (nome, CNPJ, código Domínio, contato) | Colunas sem cifra (`hub/models.py:155-177`). Só se desativa (`active`); empresa com nota não se apaga (`PROTECT`, `hub/models.py:540`). Pedido de procuração guarda e-mail mascarado (`hub/models.py:484-506`). Sem expurgo | Enquanto o escritório mantiver a empresa. Depois do contrato: **A DEFINIR PELO RESPONSÁVEL** | É dado do cliente do escritório: a Mewstack guarda enquanto ele mandar e apaga quando ele mandar, salvo guarda legal. O contato é dado pessoal | Eliminar ou anonimizar o contato; decidir se o contato passa a ser cifrado; depende da Q-49 |
| R-02 | **XML da NFS-e** e derivados | `original_xml` cifrado, imutável (`hub/models.py:538-561`); derivados: contraparte e valores sem cifra (`hub/models.py:564-592`), `IntegrationArtifact`, pacote `NfseExport` no bucket (`hub/models.py:742-785`). Nada expira | **PROPOSTA**: 60 meses online (`docs/comercial/proposta-precos.md:195`, que a marca como hipótese). Depois do contrato: **A DEFINIR PELO RESPONSÁVEL** | A nota é prova; quem tem de guardar é o contribuinte, até prescrever o crédito tributário (prazo-base de 5 anos; CTN arts. 173, 174 e 195, parágrafo único; o termo inicial fica para o jurídico). A Mewstack guarda a pedido do escritório, não por obrigação própria | Comando de eliminação com conferência de guarda legal (Q-49); contraparte sem cifra; prazo do pacote baixado |
| R-03 | **Lote de importação e carteira por planilha** | Carteira: prévia não confirmada some em 7 dias; lote concluído tem o conteúdo cifrado esvaziado em 30 dias (`hub/company_roster.py:45-46,593-611`); fica o registro (nome do arquivo, hash, contagens, `errors`). Importação antiga: conteúdo zerado ao confirmar (`hub/imports.py:931`); prévia nunca confirmada fica sem prazo. Backup `.dom` e chave saem ao concluir (`hub/backup_bridge.py:271-287`) | **PROPOSTA já no código**: 7 e 30 dias. Lotes antigos: **A DEFINIR PELO RESPONSÁVEL** | A planilha traz nome, CNPJ e e-mail dos clientes; depois de importada ou descartada não serve (LGPD art. 6º, III, necessidade) | Expurgo da prévia antiga e do nome do arquivo; D-310 deixou o prazo "a definir em E4": os 7 e 30 dias nunca foram aprovados |
| R-04 | **Relatório de ocorrências** da carteira | Depois de confirmar, o lote guarda só as linhas com problema ou aviso (nome, CNPJ, e-mail, motivo), cifradas (`hub/company_roster.py:511-525`); some em 30 dias (`:610`). O CSV baixado sai do controle da plataforma (`hub/views_roster.py:261-284`) | **PROPOSTA já no código**: 30 dias | Dá tempo de corrigir a planilha; depois só acumula dado de cliente | Aprovar o prazo; avisar que o CSV baixado é do escritório |
| R-05 | **Trilha de auditoria** | `AuditEvent` só cresce: a aplicação não edita nem apaga (`audit/models.py:55-115`). Autor e escritório viram nulos se forem apagados. Metadado não pode ter e-mail, CNPJ nem nome (`audit/models.py:13-53`); o IP entra só como HMAC (`audit/services.py:15-23`). Sem expurgo | **A DEFINIR PELO RESPONSÁVEL**. Ponto de partida **PROPOSTA**: no mínimo o prazo do artefato que ela prova (R-02, R-07) | Prova quem fez o quê; se sumir antes do documento, a prova se perde | Política escrita; destino da trilha de escritório encerrado |
| R-06 | **Certificado A1 e e-CNPJ** (cifrados) | Arquivo `.pfx` e senha cifrados (AES-GCM) em `Certificate` e `OfficeCertificate` (`hub/models.py:356-410`). Revogar só marca `revoked_at` (`hub/office_certificate.py:126-142`); nenhum código apaga o arquivo nem a senha (busca em `src/`); vencido continua guardado. Aviso de vencimento do e-CNPJ aos 30, 15, 7, 3 e 1 dia (`hub/procuracao_alerts.py:23`) | **PROPOSTA**: apagar arquivo e senha ao revogar, ao vencer e no fim do contrato; manter assunto, validade e impressão digital | Certificado vencido ou revogado não serve a ninguém e segue sendo segredo de alto valor (LGPD art. 6º, III; `docs/specs/produto-vendavel-plano.md`, seção Riscos) | A rotina; rotação de chave (um só chaveiro no ambiente, `config/settings/base.py:477-478`) |
| R-07 | **Fatura e cobrança** | `Invoice` e linhas não se apagam (`PROTECT`, `platform/models.py:596-640`); tentativas e eventos do Asaas ficam (`platform/models.py:642-709`). `TenantLifecycle.retention_until` existe e ninguém lê nem grava (`platform/models.py:171`). No Asaas vale a retenção do Asaas | **PROPOSTA**: 5 anos (prazo-base do CTN); termo inicial **A DEFINIR PELO RESPONSÁVEL** | Registro contábil e fiscal da própria Mewstack; guarda até prescrever (CTN art. 195, parágrafo único). É obrigação dela, não instrução do escritório | Política escrita; usar ou remover `retention_until`; e-mail do dono no Asaas (`platform/collection.py:168-176`) |
| R-08 | **Conversa e anexo da IA** | Padrão de 90 dias por escritório, ajustável de 1 a 3.650 no console (`intelligence/models.py:39`; `platform/forms.py:621-655`). Tarefa diária às 02:40 apaga conversa, mensagens e anexos (`config/settings/base.py:587`; `intelligence/retention.py:18-32`; `intelligence/tasks.py:52-61`). Não apaga conversa com rascunho de classificação nem com feedback que virou candidato de aprendizado (`intelligence/retention.py:24-25`). `EgressAudit` sem prazo. **Falha**: ver F-1, seção 5 | **PROPOSTA**: 90 dias, o padrão; o escritório pode mudar | A conversa mistura dado de cliente; quanto menos tempo, menos risco (LGPD art. 6º, III); 90 dias cobre a conferência do mês | Corrigir o expurgo; prazo de `EgressAudit`, `ReportExportRecord` e candidatos de aprendizado |
| R-09 | **Resultado de conferência** (Contraprova) | Entradas (SPED, XML, ZIP, linhas do agente): 24 h depois de terminar. Rascunho parado: 72 h. Achados e XLSX: 90 dias. Cabeçalho e recibos (papel, tamanho, hash) ficam (`crosscheck/limits.py:38-42`; `crosscheck/retention.py:62-153`). Tarefa diária às 03:40 (`config/settings/base.py:633`). Módulo desligado em produção (Q-46, Q-47) | **DECIDIDO** (D-302, `DECISOES.md:1900`): 24 h, 72 h e 90 dias | Só repetir a conferência com outra regra exige o arquivo; o resto é resultado | Prazo do cabeçalho e dos hashes (D-302 diz que não é a política geral) |
| R-10 | **Pacote de exportação** | (a) `office_export` gera um ZIP com um JSON por linha por modelo do `hub`, a equipe e `manifest.json`; XML fiscal em claro; só leitura (`hub/offboarding.py:159-202`; `hub/management/commands/office_export.py:1-9`). Fica onde o operador gravar; nada o apaga. Fora do ZIP: `profitability`, `crosscheck`, `triage`, `intelligence` (sob pedido), `platform`, `audit` e os binários do bucket (`hub/offboarding.py:46-60,183-187`). (b) O pacote NFS-e/Domínio (`NfseExport`) fica no bucket sem expurgo | **A DEFINIR PELO RESPONSÁVEL**: dias para apagar a cópia da Mewstack depois da entrega | O ZIP é uma segunda cópia completa dos dados do escritório; cada dia guardado é risco sem finalidade (LGPD art. 16) | Prazo e rotina; registro da entrega; exportar os módulos "sob pedido" e o bucket; hoje só por comando interno |
| R-11 | **Log** | JSON em stdout, com e-mail e token redigidos (`common/logging.py:11-30`). O log de acesso do gunicorn também sai em stdout e grava o caminho, inclusive `/comecar/verificar/<token>/` e `/ativar/<token>/` (`fly.toml:37`; `hub/urls.py:17-18`). Quem guarda e por quanto tempo: a Fly (A CONFIRMAR). Sentry desligado (`fly.toml:32`). `X-Request-ID` só no cabeçalho (`common/middleware.py:25`) | **A DEFINIR PELO RESPONSÁVEL**. Se a Mewstack for provedor de aplicações de internet (pessoa jurídica, atividade organizada e com fim econômico), o Marco Civil (art. 15; planalto.gov.br, 20/11/2026) manda guardar registros de acesso, sob sigilo, por 6 meses: aplicabilidade A AVALIAR pelo jurídico | Log serve para achar defeito e provar acesso; sem prazo vira cópia eterna de dado pessoal | Definir onde fica o IP (a trilha guarda só HMAC); tirar o token do log de acesso; prazo do log da Fly |

## 4. Outros artefatos

| # | Artefato | Hoje no código | Prazo | Falta |
|---|---|---|---|---|
| R-12 | **Cadastro e conta**: `SignupIntent`, `Lead`, `Invitation`, usuário | `SignupIntent` (e-mail, nome, hash de senha, CNPJ cifrado, aceite com versão e IP em HMAC) expira em 24 h, mas a linha nunca sai (`platform/models.py:823-860`; `platform/signup.py:129`). `Lead` cifrado, sem expurgo (`platform/models.py:805-820`). Convite expira em 7 dias e a linha fica. Usuário só se desativa; não há exclusão de conta | Não verificado: **PROPOSTA** apagar logo depois de expirar (dias: **A DEFINIR PELO RESPONSÁVEL**). Verificado: guardar como prova do aceite, prazo **A DEFINIR PELO RESPONSÁVEL** | Rotina de expurgo; fluxo de exclusão de conta |
| R-13 | **Notificação** | Lida: some em 90 dias, às 03:10. Não lida: fica (`hub/notifications.py:152-155`; `config/settings/base.py:561`) | **PROPOSTA**: manter | Prazo para não lida |
| R-14 | **Demonstração** | Visitante `demo-*@example.test` sai depois de 24 h, na próxima entrada, não por agenda (`hub/demo_session.py:20-45`). Dado fictício | Manter | Nenhuma |
| R-15 | **Pedido de titular, incidente, consentimento** | `DataSubjectRequest` sem expurgo; alvo de resposta de 15 dias (`privacy/models.py:18-19`; `config/settings/base.py:483`). Incidente guarda no mínimo 5 anos (`privacy/models.py:211-221`). Consentimento só anexa (`privacy/models.py:72-133`). Nenhum `ProcessingPurpose` é criado por código e o admin está desligado (`fly.toml:17`): ninguém atende pelo produto | Incidente: 5 anos (já no código). Os demais: **A DEFINIR PELO RESPONSÁVEL** | Tela ou runbook para atender; propósitos cadastrados |
| R-16 | **Cópias fora do aplicativo** | Neon guarda 6 h de histórico (`docs/comercial/proposta-precos.md:290`). Postgres antigo da Fly parado com volume preservado desde 30/09/2026 (`DECISOES.md:880`; `VALIDACOES.md:3219-3221`). Valkey grava em disco (`infra/valkey/fly.toml:10`). Versionamento do bucket: não verificado | Eliminação em backup: **A DEFINIR PELO RESPONSÁVEL** (`platform/legal.py:77-79,125-127` prometem informar) | Decidir o fim do volume antigo; medir restauração (D-73) |

## 5. Falhas achadas enquanto lia (não corrigidas aqui)

| # | Falha | Prova |
|---|---|---|
| F-1 | **Expurgo de conversa trava com relatório exportado.** Conversa com mensagem que tem `ReportExportRecord` levanta `ProtectedError` (`intelligence/models.py:458`), e a tarefa diária não captura o erro (`intelligence/tasks.py:57-60`). Uma conversa assim impede a purga dos escritórios seguintes, todo dia | Teste descartável de 20/11/2026, fora do repo: conversa de 91 dias com mensagem e `ReportExportRecord`; `purge_expired_conversations(apply=True)` levantou `ProtectedError`. O teste existente cobre só conversa sem exportação (`tests/test_intelligence_retention_django.py`) |
| F-2 | Arquivo e senha do certificado nunca são apagados (R-06) | Busca por `pfx_blob` em `src/`: só criação e uso |
| F-3 | `SignupIntent` e `Lead` sem expurgo (R-12) | Busca por esses nomes em `src/`: só o próprio fluxo |

## Pendências do responsável

| # | Pergunta | Recomendação |
|---|---|---|
| 1 | Qual opção (A, B, C ou D) vale no encerramento, e em quantos dias após o contrato? (Q-49) | A, com prazo contratual e comando só depois da revisão jurídica |
| 2 | Os 60 meses de R-02 e os 5 anos de R-07 valem? Quem valida (jurídico ou contador)? | Aprovar como proposta de lançamento e rever em 90 dias |
| 3 | Os 7 e 30 dias da carteira (R-03, R-04) e os 90 dias da IA (R-08) ficam? | Sim |
| 4 | Apagar o arquivo e a senha do certificado ao revogar e ao vencer? | Sim; guardar só os metadados |
| 5 | Qual prazo para a cópia do ZIP de exportação e para o pacote baixado (R-10)? | Valor seu; sugestão: curto, contado da entrega confirmada |
| 6 | Qual prazo para `SignupIntent` não verificado, `Lead` e notificação não lida (R-12, R-13)? | Valor seu |
| 7 | A Mewstack é provedor de aplicações de internet para o art. 15 do Marco Civil? Onde e por quanto tempo ficam os registros de acesso (IP e hora)? | Parecer do jurídico; hoje só há HMAC do IP |
| 8 | O contato da empresa-cliente (nome, e-mail, telefone) passa a ser cifrado? | Sim, é dado pessoal sem cifra |
| 9 | Quando destruir o volume do Postgres antigo da Fly? | Marcar data e instruir (D-208) |
| 10 | Quem corrige o F-1 e em que ordem frente ao restante? | Antes de ligar o Copiloto |
