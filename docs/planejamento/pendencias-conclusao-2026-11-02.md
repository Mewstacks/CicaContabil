<!-- D371-V410-PUBLISHED-2026-11-17 -->
**17/11/2026 — D-371/V-410: correções publicadas para testes, release99.**
[PR28](https://github.com/Mewstacks/CicaContabil/pull/28), main`b237e924` e [CI44086070065](https://github.com/Mewstacks/CicaContabil/actions/runs/44086070065) aprovados; head`1c9935745b45855c8c13e63e38d038a52a3beafa`, árvore exata`36f15b49e60a4c9a3b6208405d484019a1c5be19`. Backend797 arquivos/SHA`55585d53bb9812094edebc098201ae093928d5af0e674798b9cdfaaaf59645d0`, saúde/worker/assets e15 grupos de dados preservados conferidos. Agente1.0.13 [publicado](https://github.com/Mewstacks/CicaContabil/releases/tag/agent-v1.0.13), com instalação limpa e upgrades 1.0.10/11/12 aprovados no Windows sintético.

CI integral: 3072 SQLite/54 skips, 3124 PostgreSQL/2 skips; 181/181 subtestes, respectivamente; 179 testes Windows aprovados.

**SVAPL02 atualizado em17/11/2026:** recibo do atualizador fornecido pelo responsável confirma1.0.10→1.0.13 às10:17BRT, MSIexit0, configuração protegida preservada, serviço Running/Auto/LocalSystem e ciclo recente, sem reinício pendente. Conferência independente no backend autenticado às10:17/10:19BRT confirma o mesmo agente oficial, Razão/títulos online, automatic_counts=true em ambos, portfolio_scope=true no Razão e company_scope=true nos títulos. Instalação/conexão/capacidades estão comprovadas; a primeira nova coleta financeira pela tela continua sem prova. source_review_required corresponde ao título legado já capturado aguardando revisão; fonte e decisões anteriores permanecem preservadas.

Publicação técnica para testes; não é homologação contábil, aceite contratual ou conclusão da suíte. Fontes/vínculos/semântica/plano/regras e Q-28/Q-46/D-73 mantêm provas próprias. Q-47/C01/C02 continuam adiados; backup fora da prioridade do início dos testes. Não reabrir pareamento, carga inicial, fontes recebidas ou primeiro treinamento. Nenhuma nova consulta financeira ERP, revisão contábil em nome da cliente, chamada IA, mensagem ou alteração comercial foi executada nesta publicação.

Histórico do Razão filtra mês antes de paginar; extratos têm páginas próprias, fonte/contexto preservados e páginas inválidas recusadas antes de escrita. Polling informa falha/timeout/pausa e conserva o último estado íntegro. Agente mantém pares sequenciais Razão→títulos, controle autenticado antes de cada par e orçamento de quatro pares/30s verificado entre pares para sincronizar novamente a carteira. Recupera timeout HTTP sem encerrar o serviço, respeita parada real, preserva justiça entre famílias e exige prova recente do último ciclo no diagnóstico. Não é benchmark de vazão nem promessa de concluir um lote real no mesmo dia.

Roteiro do piloto continua válido; registrar a release efetivamente testada. Novas coletas dependem da prova do agente, sem confundir cobertura da carteira com cadastro146/uma conta/43 candidatas históricas. [V-410](../../VALIDACOES.md).

## Correções para testes — D-371/V-410 EM ANDAMENTO, 17/11/2026

Após V-409, o responsável autorizou corrigir, validar e publicar. A candidata
está no worktree contad-test-fixes, branch codex/contad-correcoes-testes,
base main7d075261. **A nova entrega ainda não foi publicada.** A auditoria
V-409 abaixo permanece como prova da release98 anterior à correção.

| Frente | Estado da candidata | Prova restante |
|---|---|---|
| Histórico do Razão/extratos | Mês filtrado antes de paginar20, páginas independentes, contexto/fonte preservados e página inválida recusada antes de escrita | PostgreSQL integral, CI exato e conferência da publicação |
| Acompanhamento | Polling com timeout, aviso acessível, preservação de estado e atualização manual; QA sintético concluído | CI/publicação e conferência dos assets |
| Agente1.0.13 | Pares sequenciais, controle autenticado por par, timeout recuperável e diagnóstico do último ciclo; .NET176 aprovados/três Windows reservados | CI Windows, instalação limpa, upgrades diretos1.0.10/11/12 e publicação |
| Novas coletas reais | Pendência técnica de atualização/prova mantida | Aplicar o pacote efetivamente publicado no SVAPL02 e observar capacidades/recepção, preservando identidade/DSN/DPAPI |
| Fontes e aceite | Dependências humanas mantidas | Dados/vínculos das contas, semântica, evidência bancária, plano/regras e critérios D-73 |

SQLite integral:3072 aprovados,53 skips,181 subtestes. Essa coleta de testes
precedeu a última regressão do POST do vínculo:26 casos novos entraram na suíte
integral;27 casos novos focados, incluindo esse POST, passaram depois. O CI
validará a fonte total exata. Checks Django/migrações/Ruff globais aprovados.
PostgreSQL integral ainda em andamento; não declarar conclusão antes do resultado.
QA Playwright:17 verificações mais POST do formulário real, em dados sintéticos,
com paginação de43 pedidos/23 extratos, contexto, erros, recuperação e teclado.
Capturas375/1440px claro/escuro; sem overflow/erro inesperado. Console400/503
pertence aos cenários induzidos. Browser/servidor próprios encerrados.

O orçamento do agente é verificado ao terminar cada par Razão→títulos:
sincroniza novamente a carteira ao atingir quatro pares ou30s. Não é timeout
de leitura nem promessa de concluir um lote real hoje. O controle autenticado
é renovado antes de cada par; cancelamento é verificado antes de cada job.
Revisão sem trabalho novo mantém pausa de um minuto; falha tratada do Razão
não suprime títulos. A implementação ainda exige validação Windows/publicação.

Produção comprovada permanece release98/canal1.0.12. O candidato1.0.13 reúne
as funções anteriores para atualização única futura; não afirmar disponibilidade,
instalação ou recepção real antes das provas. O piloto recebido continua apto
para testes controlados; autonomia, contrato CONTAD e suíte têm critérios próprios.
Manter roteiro V-409 registrando a release efetivamente testada. Não reabrir
pareamento, carga inicial, primeiro treinamento ou fontes recebidas.
Q-47/C01/C02 adiados; backup fora da prioridade do início dos testes.
[Evidências e limites de V-410](../../VALIDACOES.md).

## Prontidão para testes em 17/11/2026 — D-370/V-409

**Parecer: é possível iniciar hoje testes controlados do conciliador CONTAD
com o piloto já carregado. A entrega autônoma de novas coletas e a conclusão
integral do contrato ainda não estão comprovadas. A suíte completa permanece
com pendências próprias.** Esta análise não registra aceite da cliente.

Esta atualização prevalece sobre os estados datados abaixo, inclusive títulos
antigos chamados “vigente”. Referências a “hoje” nos registros de 16/11 pertencem
àquela data. Não reabrir pareamento, instalação inicial, carga 146, captura do
piloto, primeira chamada IA ou primeiro treinamento/conferência já realizados.

### Evidência atual e alcance

Leitura de produção em **17/11, 08:53:49 de Brasília**, com transação PostgreSQL
`REPEATABLE READ READ ONLY`: runtime web com 796 arquivos e SHA
`54f07e18e44a37dc45db1122b6692eb1cd772a95b9b11185532923a273ea1894`, igual à release 98.
146 empresas autorizadas, uma conta operacional, 145 empresas sem conta,
43 candidatas pendentes em 11 empresas, 134 outras sem candidata identificada.
Há um job legado de Razão, um de títulos, zero jobs novos de títulos por empresa,
zero fotografias de títulos normalizados, zero contas lançáveis e zero regras.
Essas contagens não representam ausência de títulos na fonte bruta.

Heartbeat recente às 08:53:27; capacidades autenticadas observadas às 08:53:29
continuam com `automatic_counts=false` em Razão e títulos e `company_scope=false`
em títulos. Ambas as telas classificam o agente como **precisa de atualização**.
Canal de atualização aponta 1.0.12; última versão instalada comprovada permanece
1.0.10 (V-388). O campo `version` das capabilities identifica o protocolo e não
deve ser apresentado como versão instalada. Não foi acessado o Windows/ERP.

Home, rota correta de login `/entrar/`, liveness e readiness responderam 200
por HTTPS com validação TLS; banco/cache `ok`. PR 27 e CI 43949218680 foram
reconsultados no GitHub: integração e jobs aprovados, incluindo instalação
limpa e upgrades 1.0.10/1.0.11→1.0.12. O Windows do CI é sintético.
Worker também reconferido: os mesmos 796 arquivos/SHA e resposta ao ping operacional.
Novas regressões: **3046 testes SQLite/53 skips e 3098 PostgreSQL/um skip**, com
181 subtestes em cada execução; concorrência PostgreSQL aprovada. .NET local:
149 aprovados/três casos Windows reservados;152 Windows aprovados no CI.
Smoke Playwright:28 verificações de sete telas em desktop/celular/claro/escuro,
mais três de navegação/teclado, sem erros. Não somar execuções das duas bases
como casos independentes. [Evidências e limites em V-409](../../VALIDACOES.md).

### O que a cliente pode testar

| Percurso | Situação para hoje | Condição/limite |
|---|---|---|
| Acesso, carteira e piloto | Disponível | Usar conta existente e piloto SURIA/212, conta 8,09/2026; fontes 163+163 comprovadas em V-401/V-408. Não exigir revisão das 43 candidatas para começar. |
| Conferência, histórico, desfazer e relatório | Disponível | A própria cliente decide com evidência. HTML/impressão/CSV são conferência, não importação contábil. |
| Importação de outro extrato | Disponível com fonte/cadastro corretos | OFX/QFX/CSV/XLSX/PDF até 25 MiB, nos layouts suportados; formato PDF não é universal. Razão independente tem CSV próprio de partidas completas. |
| Revisão/cadastro de contas | Disponível para configuração |43 pré-cadastros não são 43 contas operacionais. Banco, conta, plano, filial/direção e evidência não podem ser inferidos. |
| Nova coleta de Razão e títulos pela tela | Código publicado; integração real pendente | Atualização única 1.0.12 no SVAPL02 e prova de recepção de um recorte real. Não precisa novo pareamento/DSN. |
| Títulos já recebidos | Consulta e revisão disponíveis | Fonte retida em V-408:822 parcelas, 546 registros de baixa e 590 vínculos brutos; semântica, componentes e alocação bancária exigem revisão. Não há títulos normalizados em produção hoje. |
| DE-PARA inicial | Revisão das sugestões retidas disponível | Duas sugestões reais (V-395); cadastrar/revisar contas lançáveis e históricos antes de criar/ativar regras. Política IA desligada, sem terceira chamada autorizada. |
| Exportação/importação Domínio | Fora do teste liberado | Q-47 continua adiada e gate de exportação permanecefalse; relatório não substitui arquivo homologado. |

### Achados e prioridades dentro de PC-19/03/09/12

1. **Bloqueio técnico das novas coletas:** aplicar 1.0.12 no servidor existente,
   conferir serviço/configuração preservados, observar capacidades autenticadas
   e concluir uma coleta de Razão e uma de títulos pela interface. Responsável:
   técnico com acesso ao SVAPL02. A indisponibilidade foi relatada em 16/11;
   disponibilidade humana em 17/11 não foi verificada. Heartbeat não comprova
   acesso administrativo nem atualização.
2. **Defeito P2 reproduzido no histórico do Razão:** `ledger_requests.py:579–584`
   limita às 20 solicitações mais recentes de toda a conta antes de
   `ledger_request_views.py:179–180` filtrar o mês. Um pedido de setembro seguido
   de 20 pedidos de outubro permanece no banco, mas a tela de setembro mostra
   “Nenhuma solicitação nesta competência”. Não há paginação para recuperá-lo.
   Corrigir o filtro antes do limite e disponibilizar histórico acessível antes
   do uso ampliado; não impede o piloto atual com poucos pedidos. Responsável:
   desenvolvimento. Reprodução sintética confirmada em V-409, sem correção nesta
   análise. Caminhos/linhas referem-se à fonte 32bc89d da release 98.
3. **Volume não comprovado para o mesmo dia:** `Worker.cs:75–76,110` executa
   no máximo um job de Razão e um de títulos por ciclo e espera um minuto entre
   ciclos. Só os intervalos de 1.752 pedidos de títulos (146 × 12, lote demonstrado)
   representam aproximadamente 29 h, além das leituras e transmissões. Não é um
   benchmark real nem exigência de coletar 12 meses hoje. Prévia rápida não mede
   conclusão do lote. Começar com uma empresa/competência; medir antes de ampliar.
4. **Cobertura e decisões contábeis:** revisar 43 candidatas, identificar demais
   contas/extratos, interpretar títulos/estornos e aprovar contas/regras.
   Responsável: cliente/contadora, com suporte técnico. Contas ausentes não
   impedem captura fiscal por empresa depois da atualização; impedem revisão
   financeira por conta sem vínculo comprovado. Q-28/Q-46 permanecem próprios.
5. **Aceite integral:**200 fatos distintos por fluxo aplicável, precisão95%
   quando aplicável, desempenho/retomada/recuperação e aceite humano de D-73
   ainda não comprovados.163 fatos do piloto não viram326 por haver duas fontes.
   Faltam ao menos37 fatos adicionais, além da revisão da amostra completa.
   Backup permanece fora da prioridade do início dos testes; seu critério de
   recuperação não foi encerrado. Q-47/C01/C02 continuam adiados.

### Roteiro de teste de hoje

Continuação do roteiro existente dePC-19, sem novo plano concorrente:

1. Registrar release 98, usuária, empresa/conta/competência e contagens iniciais.
2. Abrir piloto, comparar uma relação comprovável e registrar referência
   auditável; confirmação cabe à cliente, não ao executor da análise.
3. Consultar histórico; quando houver motivo real, desfazer/corrigir e conferir
   preservação da trilha. Não criar decisões fictícias em produção.
4. A cliente abre e baixa o relatório, confere valores/pendências e explica
   seu significado. Completar autonomia de download e referência já pendentes
   em V-401; não repetir o primeiro treinamento como se nunca tivesse ocorrido.
5. Consultar fonte de títulos retida e revisar uma conta com documentação real.
   Separar defeito de software, dado ausente e decisão contábil pendente.
6. Se o técnico concluir a atualização, testar uma empresa/competência em cada
   nova coleta: pedido, entrega ao agente, recepção, conteúdo, comparação e
   repetição sem duplicidade. Só então ampliar o lote.
7. Registrar resultado de cada cenário e pendências. Início de testes não é
   aceite integral nem encerramento contratual.

### Demais frentes do projeto

O contrato D-301/D-302 cobre conciliador, pagar/receber, DE-PARA inicial com IA,
implantação/testes e treinamento; exclui Triagem e suporte remoto. Prazo
documentado 09/11/2026, sem novo prazo ou aceite final localizado. A suíte toda
não é pré-requisito para o teste CONTAD. Fora desse recorte, a análise documental
mantém as pendências da matriz já existente neste arquivo:

| Frente | Limite para declarar a suíte concluída |
|---|---|
| Acesso/e-mail | Homologação real de convites/recuperação/MFA e papéis; acesso CONTAD não valida o fluxo geral. |
| Siescon/Rentabilidade | Integração/piloto reais, honorários/cobertura/regrasQ-41–43; não reabrir base técnicaQ-33/44/45. |
| IA/Triagem | Governança/custos/dados/curadoria e qualidade; percurso real e-mail→revisão→arquivo→checklist; relatórios publicados/recuperáveis. |
| NFS-e | Qualidade/cobertura/recuperação e correção específica da espécieD-318/D-343; preservar importação anterior aceitaD-295. |
| Integra Contador | Prova real de cada operação DTE/DCTFWeb/PARCSN e respectivos controles. |
| Folha/DRE/caixa/Radar | Fontes/layouts/totais/destinos e completude/frescor reais. |
| Cobrança | ModeloD-109, Asaas e pagamento→acesso, atraso/reativação/estorno/repetição. |
| Rotinas e operação | Modelos/prazos/responsáveis reais, usabilidade por perfil, carga/alertas, privacidade, recuperação e aceite. |

IA local definitiva permanece posterior, conformeD-50/D-51. A avaliação dessas
frentes foi documental/estática com regressão de software; não houve nova
homologação de integrações externas ou revisão fiscal de toda a suíte.

### Continuidade e preservação

O checkout principal está em `b65dfe7` com alterações locais anteriores. A auditoria
funcional usa o worktree isolado`contad-title-self-service`, commit`32bc89d`, árvore
`1cc5f9c112fb63760e4f0bc65846d9794000faf6`, igual ao código integrado/publicado.
Não executar pull/reset ou publicar a pasta principal como se fosse a release 98.

README, CICA-QA e blocos históricos das etapas conservam referências antigas
(.NET8/mTLS, Q-33/Q-39, coleta restrita e treinamento ausente). Usar esta análise,
D-370/V-409 e os fechamentos V-407/V-408 para a situação atual. A auditoria atualiza
os pontos de entrada canônicos sem apagar o histórico ou refazer todo o material.
Nenhuma mudança de aplicação, coleta ERP, decisão contábil, deploy, mensagem,
chamada IA ou cobrança foi feita nesta rodada.

## Entrega publicada — D-369/V-408, 16/11/2026, release98

A coleta de títulos e baixas por empresa/competência está implementada pela tela,
incluindo empresas sem conta cadastrada. A cliente seleciona empresas e meses,
confere o lote e acompanha as fontes. CI43949218680, migração0041, release98 e agente1.0.12 foram publicados/verificados
emV-408. A prévia real das146empresas passou sem gravar pedidos; o agente observado
ainda precisa da atualização, antes de receber as novas solicitações.

| Dependência real | O que falta | Responsável |
|---|---|---|
| Conexão do Domínio às novas telas | Aplicar a atualização única1.0.12, que reúne Razão e títulos, e comprovar recepção real. | Técnico com acesso ao SVAPL02; acesso indisponível hoje. Não é outra instalação/pareamento nem validação da contadora. |
| Demais contas e extratos | Conferir43 candidatas em11 empresas; identificar contas nas134 outras; fornecer extratos por conta/competência. | Cliente fornece/confere dados reais; cadastro e revisão já existem. A coleta fiscal por empresa não depende disso. |
| Interpretação e vínculo financeiro | Revisar natureza, componentes/estornos e evidência das relações com o banco; conferir plano e regras DE-PARA. | Cliente/contadora. Nenhuma igualdade de valor substitui evidência. |
| Retorno e aceite completo | Critérios de importação/aceite próprios, cobertura e amostra real. | Técnico+contadora/responsável. Q-47/C01/C02 seguem adiados; não impedem a consulta/conciliação disponível. |

O primeiro treinamento e a conferência real já relatados não voltam como
pendência. Backup permanece fora da prioridade. Os registros abaixo são
históricos; prevalece esta atualização e o fechamento deV-408.


## Entrega vigente — D-367/V-406, 16/11/2026, release96

- [x] Títulos/baixas pela interface: fonte, revisão, prévia, vínculo, histórico, desfazer e relatório em reais.
- [x] Revisão das sugestões DE-PARA retidas e ativação humana com revalidação do plano.
- [x] CI43925999340, migração0085, publicação, saúde e preservação de15 grupos de dados comprovados.

Pendência técnica para uso autônomo, identificada na pergunta sobre o envio de extratos:

- [ ] Disponibilizar solicitação e acompanhamento da coleta direta do Razão pela interface. Hoje o upload compara com o Razão já recebido; nova coleta exige comando administrativo. V-406/D-363.

Dependências reais para ampliar a operação:

- Cliente valida dados bancários/contábeis e evidência das43 candidatas em11 empresas.
- Identificar contas e obter fontes/períodos nas134 demais empresas sem candidata.
- Revisar natureza/componentes dos títulos e comprovar suas relações com o banco.
- Aprovar contas lançáveis e históricos das sugestões DE-PARA; realizar uso real e aceite.
- Q-47/C01/C02 seguem adiados; não solicitar novamente nesta rodada.

Backup não é prioridade por instrução expressa. Os registros abaixo são
histórico do projeto; lacunas técnicas superadas não voltam como bloqueios.

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

## Uso da carteira e relatório — D-364/V-403, 16/11/2026

Publicada na release 93: carteira por empresa/conta/competência,
incluindo ausências; relatório legível/imprimível em reais, CSV técnico e
período preservado no percurso. Empresa E módulo limitam a consulta; filtros
inválidos não ampliam o recorte e importação preenchida não envia arquivos.
CI integral aprovado e publicação verificada na sessão existente da cliente.
A carteira mostra 146 empresas, com o piloto disponível e 145 ainda sem conta
financeira cadastrada no CICA; 14 grupos de dados permaneceram iguais.

O guia está atualizado e o ensaio usa dados fictícios. Continuam pendentes
os vínculos/contagens reais Q-28, lotes completos multi-filial, recorrência,
semântica Q-46, amostra/recuperação/backup e treinamento/aceite D-73. A página
não acrescenta fontes financeiras à carteira nem aprova banco ou conciliação.
Q-47/C01/C02 permanecem adiados. [V-403](../../VALIDACOES.md).

## Mecanismos de expansão publicados — D-363/V-402, 16/11/2026

Fonte1a16f3c/PR21 integrada emmainc053cc0, árvore exata, release92 publicada:
prévia e lote mensal revisado, gravação atômica, reenvio sem duplicação e
isolamento de falhas da fila. CI43873060568 integral aprovado, incluindo
2357SQLite/2393PostgreSQL/110Windows e três builds.

Runtime732 hashes conferido emweb/worker; saúde200/workerpong, mesmos recursos
e configuração, legado integralmente igual/parado.14 grupos protegidos e
prévia real READ ONLY do piloto conferidos, zero novos jobs; autoria/evidência
e histórico preservados. Sem MSI, nova capturaERP, conta ou inferênciaIA.

Matriz privada dos perfis originais de13/11 conserva146 empresas e43 candidatas
em11 empresas. Das135 sem candidata,103 têm linhas no recorte;32 não têm
linhas e14 não têm parâmetros. Seis empresas têm múltiplas filiais. Campos
humanos vazios, zero contas prontas para captura; piloto com prova separada.
Roteiro privado `Downloads/CONTAD-prontidao-carteira-2026-11-16.txt` identifica
as146 empresas com nomes atuais do cadastro CICA, códigos146/146 conferidos
em leitura READ ONLY de16/11 e43 referências à ficha existente. Fontes de
cobertura continuam as de13/11; nenhuma capturaERP ou aprovação de conta.

Para ampliar a operação continuam necessários banco/conta/plano/direção e
contagens por conta/mês efetivamente revisados, inclusive lotes completos.
Matriz não é manifesto; ausência não é dispensa nem zero presumido. Não houve
nova coleta, revisão contábil, criação de contas/regras ou agenda recorrente.
Q-28/Q-46/D-73 e Q-47/C01/C02 adiados permanecem abertos. [V-402](../../VALIDACOES.md).

## Entrega assistida — D-362/V-401, 16/11/2026

Acesso atual e piloto163+163 confirmados; roteiro e ficha privados prontos.
Exercício humano desfeito e nova confirmação observados;1 conferido/162
pendentes. Revisão real declarada, nota“documento” genérica; completar referência
auditável, download autônomo e explicação do CSV. Relatório atual163+163 foi
baixado/verificado pelo executor e entregue em pasta privada. Sem aceite
formal, precisãoD-73 ou conclusão do contrato.
Carteira/títulos/regras/backup e Q-47/C01/C02 adiados permanecem conforme abaixo.

## Sete pontos — D-361/V-400, 13/11/2026

Trabalho autônomo publicado na release91; PR20/main1f8d9c5/CI43498802673
integral aprovados.729 hashes/14 grupos e ficha163 READ ONLY conferidos.
Legado restaurado exatamente/parado; registros anteriores abaixo são históricos.

| Ponto | Concluído nesta execução | Evidência ainda necessária |
|---|---|---|
| 1. Carteira | Artefatos146/43 conferidos offline; referências e cobertura preservadas. | Banco/conta/plano/direção e escopos reais revisados antes de nova coleta. |
| 2. Títulos/baixas/saldos | Regressão dos contratos e conferência mecânica163 banco/Razão, saldos iniciais/finais iguais, dois grupos ambíguos explícitos. | Semântica de títulos/baixas/estornos e revisão de correspondências/saldos Q-46. |
| 3. Recuperação | Ensaio PostgreSQL local195 tabelas+1arquivo íntegros, replay sem duplicação, restore/verificação1,283s; runbooks atualizados. | RPO de negócio, rotina recorrente, recuperação real Neon/Tigris/worker/agente e substituto. |
| 4. DE-PARA | Duas sugestões vinculadas aos três casos originais reconferidas; gates testados. | Revisão humana dos históricos/contas e ativação das regras aprovadas; IA desabilitada. |
| 5. Retorno Domínio | Dois testes de bloqueioQ-47 aprovados. | Continua adiado, inclusiveC01/C02; layout e importação real não executados. |
| 6. Aceite/desempenho | Corrigidos vínculos de fonte/ficha;163 fatos distintos e zero revisões conferidos; leitura/relatório local1,17–1,63s. | Ao menos37 fatos adicionais, revisão200/95% e medição representativa de toda a operação. |
| 7. Treinamento | Roteiro e ficha preenchível prontos;11 testes do percurso aprovados. Pode iniciar no piloto sem ficha43. | Participação efetiva, primeira operação acompanhada e manifestação real de aceite. |

Não converter preparação, ensaio sintético ou auditoria de arquivos em homologação.
[Provas e limites](../../VALIDACOES.md).

## Uso disponível — D-360/V-399, backend90

Conferência assistida do piloto publicada e verificada na sessão CONTAD:
163 movimentos/163 registros independentes, comparação e relatório CSV,
confirmação disponível para a usuária e desfazer com trilha. CI integral e
14 grupos protegidos aprovados. A ficha43 não bloqueia esse primeiro uso.
Carteira ampliada, títulos/saldos/banco, DE-PARA revisado,200/95%, medições/
recuperação/treinamento/aceite e Q-47 adiado continuam com pendências próprias.

## Prioridade D-360/V-399 — uso pela cliente hoje

A ficha43 contas não bloqueia conferir a conta piloto já vinculada. Candidata
PR19 prioriza conferência extrato/Razão, confirmação humana, desfazer e CSV
na tela.123 testes/24 subtestes e ensaio sintético aprovados; CI integral e
implantação ainda em execução. Não marcar os cinco pontos ou aceite concluídos.

## Estado operacional — D-356/V-398 (13/11/2026)

Backend89 publicado e conferido, com725 hashes runtime e saúde comprovados
emV-394. Agente1.0.10 instalado noSVAPL02, configuração e comunicação
preservadas. source_review_required mantém a revisão semântica da fonte de
títulos; não reinstalar.14 grupos protegidos conferidos após a segunda IA,
com os recortes de fingerprints documentados emV-395.

| Ponto solicitado | Situação real agora |
|---|---|
| Carteira financeira | Código aceita escopos mensais explícitos; operação continua com uma conta/piloto e146 cadastros. Perfil real146 A conferido:94566 linhas agregadas em242 grupos de09/10-2026,32 empresas sem linhas,14 sem parâmetros e120 cadastros de caixa sem referência bancária. Matriz privada entregue. Complemento real43 contas/11 empresas conferido; ficha guiada entregue para revisão. Valores/contas/banco e recorrência ainda pendentes, sem dispensar as135 empresas sem configuração. |
| Títulos | Ponte revisada publicada e testada; fonte real ainda bruta, com zero títulos normalizados/alocações. Semântica, saldo/história completa e banco Q-46 precisam de prova. |
| DE-PARA IA | Duas chamadas expressamente autorizadas executadas: primeira unknown/zero sugestões; segunda succeeded/duas sugestões para três casos. Ficha privada com históricos originais pronta. Zero LedgerAccount/regras: revisão das contas/sugestões e ativação separada continuam pendentes. Política externa desabilitada; não executar terceira chamada. |
| Retorno contábil | Q-47 adiado pelo responsável, sem layout/importação promovidos; exportação bloqueada. |
| Aceite/desempenho | Ferramentas publicadas; medição limitada real de leitura/normalização do piloto em1,537s, sem fatos novos. Amostra real163 fatos distintos congelada/ficha privada entregue, zero revisados; faltam no mínimo37 fatos adicionais. Ainda sem200 revisados, precisão95%, carga representativa, recuperação e aceite. |

CI das ferramentas2270 SQLite/2305 PostgreSQL,163 subtestes,110 Windows,
30 cenários do diagnóstico e três imagens aprovados; PR18 integrado sem
novo backend/MSI (V-398). Isso não mede aceite. Consumo estimado das duas chamadas
US$0,0004335 em créditos existentes, sem compra. As duas reservas somam
R$0,20 e não são o consumo efetivo. Q-08/Q-09 foram atendidos para estes dois
pedidos específicos; não autorizam outros lotes ou franquia comercial.
Não repetir A146/captura bruta/pareamento nem C01/C02 e Q-47 adiados.
Ficha de revisão: /Users/pedromachado/Downloads/CONTAD-sugestoes-DEPARA-para-revisar-2026-11-13.txt.
Os blocos abaixo preservam a sequência anterior, sem substituir este estado.

## Avanço local — D-356/V-384 (13/11/2026)

Os cinco pontos foram retomados em código isolado `ecdb9a7`:

| Ponto | Avanço local verificado | Ainda necessário para concluir |
|---|---|---|
| Carteira | Coleta do Razão por escopos explícitos de empresa/plano/conta/mês, autorização e replay. | CI Windows/publicação, descoberta/conferência de todas as contas/planos, recorrência e cobertura real da carteira. |
| Títulos | Ponte de decisões revisadas da captura íntegra até títulos e alocação parcial/desfazimento, com trilha por componente. | Semântica Q-46, saldo/história completa e vínculo bancário reais; C01/C02 seguem adiados. |
| DE-PARA IA | Chamada por gateway/cotas, reserva única concorrente, reuso e revisão privada para rascunho. | Dados/teto Q-08/Q-09 concretos, chamada real e revisão CONTAD; “menor custo” foi registrado, sem teto presumido. |
| Retorno | Candidata CSV/gate existentes preservados e limites documentados. | Q-47 foi adiado pelo responsável; layout e importação continuam sem aceite. |
| Aceite | Amostra congelada, revisão do proprietário e medidor de fatos/precisão/duração. |200 fatos reais revisados,95% e desempenho/recuperação reais; testes sintéticos não contam como essa amostra. |

PostgreSQL2207/163 subtestes, bateria final54 e .NET101 aprovados, com
limites emV-384. Sem CI externo, implantação, coleta ERP, IA real ou aceite.
A situação publicada continua a última prova V-382; o texto V-383 abaixo
é a revisão anterior à candidata local e permanece como histórico.

# Pendências para concluir o projeto CICA

## Verificação vigente — 13/11/2026, D-343/D-355/V-383

**Ainda há desenvolvimento, homologação operacional e aceite pendentes.**
A conferência adiada de C01/retenções e C02/juros é uma dependência específica;
não resume tudo o que falta. Esta revisão reconcilia a lista existente com
V-367–382. Documentação e código locais foram lidos; produção, ERP e CI não
foram consultados ou executados novamente nesta verificação.

### Avanços comprovados que não devem voltar como bloqueios

| Entrega | Evidência existente e limite |
|---|---|
| Acesso da Grazi | V-325: conta CONTAD e login real aprovados. Não recriar acesso/convite. |
| Oficial Windows | V-378: SVAPL02/1.0.9 saudável, identidade/DPAPI/DSN preservados. Não repetir instalação, corte ou pareamento. |
| Cadastros das empresas | V-352: carga A146/146 concluída. Isso não comprova contas/fontes financeiras completas; M10 continua sem classificação comprovada. |
| Razão independente do piloto | V-361:163 lançamentos/334 partidas e163 efeitos compatíveis com OFX, replay sem duplicação. Não equivale à amostra humana D-73. |
| Títulos e fonte fiscal | V-367/V-378: persistência/alocação normalizadas implementadas e captura original privada recebida;822 parcelas/546 componentes/590 vínculos. Fonte bruta ainda sem tradução financeira homologada. |
| Exemplos e comparação técnica | V-379/V-382: sete exemplos privados e comparador publicados; autocomparação READ ONLY com1958 linhas inalteradas. Não prova duas capturas reais distintas nem aprova juros/retenções/saldo/banco. |
| Código publicado e regressão | V-382: backend86 saudável, CI integral com2121 SQLite/2155 PostgreSQL/100 Windows, dados anteriores preservados. CI aprovado não encerra os critérios operacionais. |
| Recuperação parcial | V-322/V-365/V-376: backup/restore pontual isolado e ensaios sintéticos. Rotina operacional/RPO e métricas D-73 continuam pendentes. |

### O que falta para entregar o contrato CONTAD

| Pendência | Trabalho restante / responsabilidade | Prova para encerrar |
|---|---|---|
| Carteira financeira completa — Q-28, PC-17/19 | Desenvolvimento amplia coleta de contas, planos e fatos financeiros para as empresas elegíveis e períodos desde09/2026. Conferir planos compartilhados/situação M com a origem. | Cobertura por empresa/conta/período, coleta recorrente/retomável sem perda ou duplicação. Código financeiro nativo continua fixo na empresa212/conta8/setembro2026, apesar da carga cadastral A146 concluída. |
| Integração financeira dos títulos — Q-46, PC-19 | Converter a fonte fiscal bruta para o contrato normalizado e integrá-la à conciliação, após comprovar regras; desenvolvimento prepara o adaptador e contadora revisa os casos. C01/C02 continuam adiados por D-355. | Parcelas, baixas totais/parciais, saldo e estornos rastreáveis; associação bancária própria demonstrada. Catálogo/captura/comparação técnica e persistência prontas não encerram a tradução financeira. |
| Saldos, diferenças e regras reais — Q-46, PC-19 | Conferir saldos inicial/final, ambiguidades, agrupamentos, tarifas e transferências; concluir regras e decisões revisadas no fluxo. | Relatório explicado nos dois sentidos, sem completar vínculos por data/valor ou histórico.163 movimentos coincidentes não provam fechamento completo ou revisão humana. |
| DE-PARA assistido por IA — Q-46/Q-08/Q-09, PC-19/22 | Desenvolvimento liga sugestões de contas aos planos/exemplos revisados, dentro dos dados e limites de custo autorizados. Contadora revisa as sugestões. | Demonstração real de sugestão e revisão, proveniência e limites. Preparador atual cria rascunhos determinísticos de exemplos humanos; não chama provedor de IA. |
| Retorno contábil — Q-47, PC-19 | Fixar o leiaute/partidas aceitos no Domínio, ajustar o adaptador e preparar teste autorizado com fato ainda não escriturado. É outra dependência de Domínio além de C01/C02. | Importação efetiva e partidas conferidas no destino. A exportação permanece bloqueada. Nunca reenviar o Razão já escriturado para produzir essa prova. |
| Qualidade e desempenho — D-73, PC-19/30 | Proprietário revisa amostra independente, técnico mede acurácia, integridade e duração em ambiente representativo. |200 fatos distintos por fluxo; precisão mínima95% na classificação automática; zero duplicação/empresa errada/vazamento; processamento até5min por empresa, salvo dependência externa registrada. Os163 fatos do piloto só contam depois da revisão; nesse caso faltam ao menos37 distintos. |
| Operação e recuperação — D-73, PC-09/10 | Técnico conclui rotina de backup/RPO, monitoramento e ensaios operacionais de interrupção/restore de bancos e documentos. Pode preparar/avançar independentemente da conferência C01/C02, dentro do escopo autorizado. | Retomada sem perda até15min e restauração conferida até4h, com registros reais. Backups pontuais e testes locais não comprovam a rotina. |
| Treinamento e aceite — etapa12, PC-30 | Preparar e executar o percurso acompanhado com a CONTAD; registrar dificuldades, limites e aceite do proprietário por release. | Usuária conclui a jornada real; treinamento realizado e aceite formal registrados. Guia pronto não comprova treinamento ou aprovação. |

Sequência canônica: cobertura/contas e fontes → tradução financeira/regras/
DE-PARA → retorno contábil → percurso real/métricas/recuperação/treinamento/
aceite. Preparação de IA, recuperação e treinamento pode avançar sem repetir
C01/C02 agora; uso real de IA/custos conserva Q-08/Q-09 e suas autorizações.

Conferência estática: contratos nativos de Razão/títulos mantêm212/8/setembro;
`depara.py` declara ausência de chamada ao provedor; exportação exige gate de
homologação e exclui `source_ledger`. Persistência normalizada, captura fiscal
e comparador já existem e não devem voltar à lista como código inexistente.

O prazo contratual D-301 permanece09/11/2026, sem alteração por esta revisão.
Não foi localizado aceite final nos registros lidos. Não atribuir percentual
ou nova data de conclusão a partir da contagem de testes ou cadastros.

### O que falta para concluir a suíte CICA

| Frente / etapas | Pendência remanescente | Referência existente |
|---|---|---|
| Acesso/equipe/e-mail — 02/11/12 | Entrega real Brevo, convite/recuperação/MFA administrativa e validação dos papéis em carteira operacional. Acesso CONTAD já criado não homologa o fluxo geral de e-mail. | PC-06/11/26, Q-29 |
| Domínio/Siescon — 03/04/12 | Completar capacidades de fontes, backup/pastas quando aplicáveis e prova de leitura/importação Siescon. Adaptador local de empresas/folha existe; base inferida já aceita, sem reabrir Q-33/Q-44/Q-45. Alvo novo .NET 10 por D-325. | PC-17/25, Q-28/Q-31 |
| IA/curadoria/relatórios — 05 | Dados permitidos, limites, governança da chave, curador, corpus/qualidade independente e renderer Node publicado com fila/download/recuperação comprovados. | PC-21/22/23, Q-08/Q-09/Q-11/Q-34 |
| Triagem — 06 | Percurso completo e-mail → segurança → extração/classificação/revisão → destino → checklist; homologar provedores, catálogo e Windows reais. | PC-15/16/17, Q-12–25/Q-31 |
| NFS-e — 07/12 | Qualidade/cobertura do piloto, ambiguidades e recuperação; **correção da espécie no conjunto do Domínio ainda pendente**, confirmada pelo responsável nesta verificação. D-295 continua aceitando a importação anterior; não repetir essa homologação genericamente. | PC-02/03/04/05, D-295/D-318/D-343, Q-39 específico |
| Integra Contador — 08 | Prova real por operação de DTE/DCTFWeb/PARCSN, representação, custo/retorno incerto, reemissão e transição da atividade. Consulta não comprova transmissão. | PC-18, D-149/Q-40 |
| Conciliação ampliada, folha/DRE/caixa/Radar — 09 | Além do contrato CONTAD, validar demais layouts/OCR, destinos, totais financeiros, relatórios e completude/frescor das fontes do Radar. | PC-19/20/21/24 |
| Cobrança — 10 | Reconciliar modelo D-109 e completar Asaas/pagamento → acesso, Pix/boleto/cartão, atraso, reativação, estorno e eventos repetidos/fora de ordem. Não presumir valores ausentes. | PC-07/08 |
| Rotina e interfaces — 11 | Modelos/prazos/responsáveis/evidências reais, calendário/handoffs aplicáveis, jornadas por perfil e teste de usabilidade com contadores. Inspeções anteriores não são aceite de usuário. | PC-11–14/26/27/29/30 |
| Operação/liberação — 01/12 | Backup recorrente/RPO, restore/rollback cronometrados, carga/alertas, privacidade/retenção/portabilidade/exclusão, suporte e aceite por módulo/release. Fly+Neon e CI PostgreSQL já existem. | PC-01/09/10/28/30, Q-24/Q-29 |
| Rentabilidade — 14 | Fonte de honorários, cobertura mínima de horas, regras comerciais e piloto real/acessível. O déficit de cobertura de testes de V-291 (80,09% diante de 85%) é histórico e requer aferição da etapa, não uma medição nova desta auditoria. | Q-41/Q-42/Q-43, V-281–292 |

**IA local definitiva (etapa 13/PC-31):** equipamento/modelo, treino, avaliação,
capacidade e virada com rollback permanecem posteriores. Não bloqueiam a
entrega inicial por API, conforme D-50/D-51.

Prioridade operacional já documentada: o snapshot Neon pontual referido no
handoff D-339 tem vencimento registrado em **13/11/2026, 11:29:44 de Brasília**.
Conferir validade e a cobertura da rotina de backup no trabalho de PC-09;
este levantamento não consultou nem renovou recursos.

Não há base para percentual confiável ou data de conclusão: testes/telas e
cadastros não medem aceite, e os insumos de Q-28/Q-46/Q-47 ainda condicionam
o esforço. Manter implementado, validado, publicado, homologado e liberado
como estados distintos.

## Histórico preservado até 05/11/2026

Os estados e próximos passos abaixo são datados. Usar a verificação acima
para a situação atual; não repetir instalação, pareamento, coleta inicial,
credenciais ou aprovação do CI já comprovados posteriormente.

**Continuidade D-315/V-317 — 05/11/2026:** retorno do detalhe preserva filtros e
página após ações; 93 testes/24 subtestes locais aprovados, zero skips,
CUA/Playwright desktop/celular/claro/escuro/teclado conferidos. CI anterior
42079806454 aprovado para 700b496 (PostgreSQL 1.652/151, dois skips).
Nova candidata com manifesto preparada; publicação hospedada, fontes/regras,
serviço real, importação, D-73, treinamento e aceite continuam pendentes.

**Teste bancário D-314/V-316 — 05/11/2026:** percurso local com anexos reais
concluído em 42 verificações finais: importação, reenvio/retomada, revisão e
relatório. Duas falhas corrigidas; 134 testes/24 subtestes PostgreSQL aprovados,
zero skips. Testar a entrada bancária não depende mais de material adicional.
Desenvolvimento/contadora ainda completam Razão/títulos/regras/importação;
operação/CONTAD completam implantação, provas D-73, treinamento e aceite.

**Publicação do código D-313/V-314 — 05/11/2026:** commit 4fede1e enviado à
main por autorização expressa e SHA remoto conferido; CI 42067809017 aprovado.
O código está no GitHub. Operador ainda publica aplicação hospedada quando
houver acesso/autorização; desenvolvimento/contadora fecham fontes/regras e
Q-47; percurso real, recuperação, treinamento e aceite CONTAD continuam abertos.

**Continuidade D-312/V-313 — 05/11/2026:** prévia offline de alocação e CLI
privada prontas, 85 testes focados aprovados, nova candidata local preservada.
Razão emitido/salvo no Windows; transferência/extração/revisão pendentes.
Candidato original sem fechamento contábil do mês/controle de títulos;
pesquisa alternativa somente leitura autorizada e iniciada. Alternativa com
fechamento fiscal 09/2026, contábil 11/2014; não elegível por inferência.
A Pagar emitido e PDF conferido no Windows, sem chave de baixa/conta/data de
pagamento na visão. Consultas de baixas/parciais limitadas retornaram sem dados.
Desenvolvimento pesquisa fontes e adapta; contadora revisa regras/período;
operador habilitado publica quando houver acesso/autorização; CONTAD treina
com o responsável e formaliza aceite. PC-19 continua aberto.

**Continuidade D-311/V-312 — 05/11/2026:** proteção de snapshots/reexportação
e preservação de decisão humana sob corrida corrigidas localmente. Contrato
offline de títulos e preparação de DE-PARA determinístico em rascunho entregues;
adaptador Domínio/IA real continuam pendentes. Regressão final: 1.578 testes
Python/151 subtestes, um skip; .NET Mac 43 aprovados/um skip Windows. Release
com manifesto e restore PostgreSQL sintético preparados, sem publicação.
[Matriz vigente e próxima ação](verificacao-conciliador-contad-2026-11-02.md).

Plano de contas encontrado em Downloads: 754 linhas candidatas privadas, não
importadas. O responsável confirmou que os relatórios Domínio solicitados ainda
não existem; desenvolvimento deve obtê-los, sem insistir em seus caminhos.
RDP acessível e login ERP feito pelo responsável. Executável ausente na rede e
pré-requisito da versão anterior superados: versão completa 10.6A-10 instalada
do repositório oficial, com assinatura válida e backup confirmado. Ajuste 2
também concluído. Reabertura pediu novo login direto pelo responsável;
desenvolvimento obtém relatórios após esse acesso, contadora revisa
fonte/regras/layout. Não é problema de DSN a ser reconfigurado.
Publicação autorizada, Q-46/Q-47, IA Q-08/Q-09, recuperação real, D-73,
treinamento e aceite CONTAD mantêm a entrega aberta.

**Autenticação revista — D-310/V-311 (04/11/2026):** o piloto dispensa CA privada
por decisão do responsável. Backend/configurador/serviço 1.0.3 usam HTTPS + HMAC,
sem certificado de cliente, preservando recorte/revogação/DPAPI. Testes locais e
CI Windows aprovados. Falta publicar backend e atualizar PC quando houver acesso;
configurar CA ou ingresso mTLS não faz parte dessa pendência. As referências
anteriores a CA obrigatória foram superadas por D-310.

**Atualização em 04/11/2026 — D-309/V-310:** correções locais de duplicidade,
recorte do agente/API, mTLS e interface/OCR testadas: 1.502 testes Python + 151
subtestes, 38 .NET e 25 checks MSI. Nginx/Django, fila Redis/Celery e restore de
cópia sintética aprovados. MSI 1.0.2 preparado; PC conserva 1.0.1, sem pareamento.
Pesquisa Q-28 escolheu candidato com 115 itens, sem envio; falta confronto de
conta/fechamento/fonte independente. Responsável ainda não tem acesso ao Fly.
Isso mantém publicação/pareamento, Q-46/Q-47 e aceite abertos. [Detalhes](verificacao-conciliador-contad-2026-11-02.md).

**Conexão de teste em 03/11/2026 — D-308/V-309:** agente 1.0.1 atualizado no
PC Windows 11 Pro AMD64 autorizado, serviço Running e teste ODBC do configurador
CICA confirmado. 28 testes .NET e 25 checks CI aprovados. Pareamento bloqueado
por 503 (CA do agente no servidor); procedimento/autorização na etapa 12.
O PC de teste não substitui acesso à cliente CONTAD nem o piloto contábil.

**Complemento em 03/11/2026 — D-305/V-304:** [Razão normalizado e conferência](../conciliacao-razao-normalizado.md)
implementados localmente, incluindo ponte das duas filas. A origem dos títulos
é **Domínio**, e a saída inclui **relatório e arquivo de importação**, conforme
respostas do responsável. Essas escolhas não devem ser solicitadas novamente.

Atualização documental em 02/11/2026, D-304/V-303. Consolidação das etapas e
pacotes PC existentes; não cria plano concorrente ou novas perguntas.
Base: PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md, checklists das etapas 00–14
e auditoria de 10/10/2026. V-302 comprova a regressão local atual, não todos os
aceites de produto. Estados publicados e operacionais não foram consultados
novamente nesta atualização; referências históricas foram reconciliadas com
decisões posteriores. Nenhuma etapa funcional é concluída por este documento.

## Prioridade imediata: contrato CONTAD

| O que falta | Responsável / dependência existente | Condição de conclusão |
|---|---|---|
| Acesso ao PC da cliente e recorte autorizado | Responsável/cliente; Q-28. Domínio local e PC de instalação já confirmados; acesso ainda prometido. | Canal protegido, empresa/conta/período e técnico identificados, sem credenciais no Git/chat. |
| Instalar e parear o agente Windows atual | Desenvolvimento + técnico; PC-17, etapas 03/12 | MSI 1.0.1/checksum/CI e atualização no PC de teste aprovados; configurador conectou ao Domínio (V-309). Pacote sem assinatura de editor. Servidor retorna 503 por CA não configurada. Faltam pareamento/serviço no recorte correto e PC da cliente; não repetir a conexão já confirmada no PC de teste. |
| Extrair partidas independentes do Razão | Desenvolvimento + contadora; PC-19/Q-28 | Fonte/consulta/semântica permitidas e dados confrontados. Itens de extrato Domínio não são partidas contábeis. |
| Implementar contas a pagar/receber | Desenvolvimento; fonte Q-28 e regras Q-46 | Origem Domínio e inclusão confirmadas. Faltam objetos/campos, parcelas, vencimento, baixas, saldo e regras; provar a comparação com o banco. |
| Homologar a integração das duas cadeias | Desenvolvimento + contadora; PC-19 | Ponte local sobre Razão normalizado implementada em D-305/V-304. Conferir a fonte real, sem equivaler extrato Domínio a partidas. |
| Concluir DE-PARA inicial com apoio de IA | Desenvolvimento + contadora; Q-46 e Q-08/Q-09 | Entradas/saídas e plano de contas definidos; sugestões revisadas; conteúdo permitido e custo antes da execução externa. Regras manuais não comprovam essa entrega. |
| Completar diferenças, saldos e exceções | Desenvolvimento + contadora; PC-19/Q-46 | Sobras nos dois sentidos, saldos por conta/período, parciais, agrupamentos, tarifas, estornos e transferências explicados. |
| Homologar o arquivo que retorna ao ERP | Cliente/contadora + desenvolvimento; Q-47 | Relatório e arquivo de importação confirmados em D-305. Conferência privada local implementada; layout/importação contábil no Domínio continuam pendentes. Aceite NFS-e não habilita exportação contábil. |
| Homologar e entregar | Proprietário + equipe CONTAD; D-73, etapa 12 | Amostra independente de 200 itens, qualidade/integridade, recuperação, treinamento inicial e aceite vinculados à release. |

Prazo contratual registrado: **09/11/2026**. Essas dependências não representam
prorrogação ou aceite. O próximo insumo da cliente é o acesso prometido ao PC,
um recorte já conferido de extrato/Razão/títulos e o plano de contas/DE-PARA.
Não repetir se pagar/receber entra ou se o Domínio é local: já foi respondido.

As correções OFX de D-303 foram concluídas localmente e testadas em V-302.
Não precisam ser reimplementadas. Ainda exigem publicação autorizada, revisão
do legado e conferência no cliente. [Detalhes e roteiro CONTAD](verificacao-conciliador-contad-2026-11-02.md).

## Conclusão da suíte CICA, além do contrato CONTAD

| Frente existente | Pendência principal | Referências |
|---|---|---|
| Release e base técnica | Conferir CI remoto da versão enviada, corrigir falhas aplicáveis, preparar release com migração/rollback e validar carga/recuperação reais. `views.py` tem dez erros de tipagem anteriores comprovados em V-302. | PC-01/09/10/30; etapas 01/12 |
| Acesso, equipe e e-mail | Homologar Brevo, confirmação, convites, recuperação e recuperação administrativa MFA; validar perfis/carteira e operação real. Remetente/privacidade remanescentes em Q-29. | PC-06/11/26; etapas 02/11/12 |
| Agente e Domínio | Homologar instalação/atualização/revogação/rede, sincronização completa, backup e pastas quando contratados; provar fonte de cada capacidade. | PC-17; etapas 03/12; Q-28/Q-31 |
| Siescon | Conferir leitura real, semântica, contas/lançamentos e importar/conferir exportação em layout aceito. A base inferida já foi aprovada; não reabrir Q-33/Q-44/Q-45. | PC-25; etapa 04; D-289/D-290/V-292 |
| IA e curadoria | Fechar limites/egressão/governança e curador; demonstrar correções/fontes/versionamento e qualidade independente; homologar relatórios publicados. | PC-21/22/23; etapa 05; Q-08/Q-09/Q-11/Q-34 |
| Triagem | Completar e homologar e-mail → segurança/extração → classificação/revisão → destino → checklist, com caixas, catálogo, políticas e Windows reais. | PC-15/16/17; etapa 06; Q-12–25/Q-31 |
| NFS-e | Completar prova fiscal independente, qualidade/cobertura, tratamento das ambiguidades e recuperação operacional da coleta. Há coleta real e importação aceita; não apresentar todo o módulo como “não iniciado”. | PC-02/04/05; etapa 07; D-295 |
| Integra Contador | Homologar operações assumidas de DTE/DCTFWeb/PARCSN e transmissões aprovadas, credenciais/representação, custos/retornos e incerteza; concluir reemissão e vínculo com atividades conforme regras remanescentes. | PC-18; etapa 08; D-149/Q-40; Q-36 para ampliação de modalidades |
| Conciliação, relatórios e Radar | Além de CONTAD, validar corpus/layouts/OCR reais, outros destinos ERP, escala; provar DRE/caixa/folha e renderer Node publicados; Radar com completude/frescor e fonte oficial. | PC-19/20/21/24; etapa 09 |
| Cobrança | Reconciliar capacidade, IA e custo efetivo Integra ao modelo D-109; completar Asaas e pagamento → acesso; homologar Pix/boleto/cartão, atraso, reativação, estorno e eventos fora de ordem. | PC-07/08; etapa 10; somente valores realmente ausentes precisam decisão |
| Jornadas do escritório | Homologar modelos, responsáveis, prazos e critérios reais; concluir ligações entre módulos e atividades, interfaces/permissões/estados, usabilidade com contadores e oferta coerente com capacidade. | PC-11–14/26/27/29/30; etapa 11 |
| Operação, privacidade e liberação | Medir restore/rollback, retomada e carga; alarmes de fontes/filas; executar retenção/portabilidade/exclusão e termos; manuais, suporte e aceite por módulo/release. Fly+Neon já escolhidos. | PC-09/10/28/30; etapa 12; Q-24/Q-29 |
| Rentabilidade | Fonte de honorários, cobertura mínima de horas, comercial, critérios reais e homologação operacional/acessível; conciliar a exigência de cobertura de testes com o resultado histórico V-291 (80,09% ante 85%, não reexecutado agora). | Etapa 14; Q-41/Q-42/Q-43 |
| IA local definitiva | Hardware/modelo, treino, avaliação, capacidade, isolamento e virada com rollback aprovados. É etapa posterior e não bloqueia venda inicial por API. | PC-31; etapa 13; D-50/D-51; Q-35 somente máquina de IA |

## O que já está resolvido e não deve voltar como bloqueio

- **Q-39/PC-03 NFS-e:** o proprietário confirmou concluída a importação externa
  em D-295. Não exigir comprovante ou repetição. Exportação contábil tem aceite próprio.
- **Q-33/Q-44/Q-45:** base Siescon inferida aceita e agente unificado .NET 8
  definidos. Falta homologação operacional e layout de importação contábil.
- **Infraestrutura SaaS:** Fly+Neon definidos e já usados; falta prova por
  release/módulo e recuperação, não escolher provedor de novo.
- **Critérios D-73 e aprovador:** já decididos. Aplicar 200 itens independentes,
  precisão mínima de 95% onde aplicável, integridade e tempos aprovados, sem
  confundir corpus sintético com aprovação do contador.
- **Fedrizzi ODBC:** D-74 confirma a conexão existente; o ambiente CONTAD é outro.
- **Contrato CONTAD:** prazo, condições, DE-PARA com IA e treinamento inicial
  já constam do contrato. Este levantamento não altera regras comerciais.

## Evidência disponível e próximos responsáveis

V-302: suíte integral PostgreSQL **1.423 testes/145 subtestes aprovados**, com
OCR português e Playwright Python opcionais ignorados; UI exercitada por Node;
23 testes .NET e builds aprovados. Isso reduz o risco local, sem concluir fontes,
integrações, precisão, operação publicada ou aceite real.

O responsável fornece acesso/material da CONTAD e resolve somente as decisões
Q remanescentes pertinentes. O desenvolvimento executa os adaptadores e
encadeamentos, prepara a release e produz evidência. Contadora/técnico conferem
as fontes e o retorno no ERP; o proprietário aprova os módulos conforme D-73.

**GitHub é entrega de código.** Push/CI não instala o agente, não aplica a
migração em produção nem homologa o produto. Autorização de publicação/ERP/custo
permanece específica, nos termos de D-304 e decisões anteriores.


## Prioridade de uso atual — D-367/V-406 (16/11/2026)

A implementação de títulos/baixas e da revisão DE-PARA está publicada na
release96, conforme V-406. A cliente pode operar pela tela; CLI/JSON
não são mais a etapa de revisão. Dependências reais mantidas:

- Validar banco, referência, conta contábil e uso das43 candidatas; cadastro
  não autoriza ativação automática de plano/vínculo.
- Fornecer/identificar contas e fontes nas134 demais empresas sem candidata;
  preencher cadastro não cria extrato, Razão ou títulos ausentes.
- Conferir a semântica/componentes dos títulos e a evidência de cada relação
  bancária; ausência/valor igual não comprovam saldo, quitação ou vínculo.
- Validar contas lançáveis e histórico das sugestões DE-PARA existentes.
- Confronto Domínio/aceite conforme Q-47/C01/C02 adiados e critérios humanos
  já existentes. Não reabrir perguntas decididas nem inventar homologação.

Backup não é prioridade desta rodada, por instrução expressa do responsável,
e não será apresentado como impedimento para avançar no uso assistido.


### D-368/V-407 — Coleta pela cliente (16/11/2026)

**Backend97 e pacote1.0.11 publicados e verificados. Operação completa da carteira ainda pendente.** A cliente pode continuar no piloto com fontes carregadas. A nova tela de Extrato e Razão está publicada; o agente observado ainda exige atualização. Não existe acesso ao SVAPL02 hoje.

| Prioridade de uso | Falta real | Responsabilidade |
|---|---|---|
| Busca direta do Razão | Aplicar1.0.11 no SVAPL02 e comprovar capability/coleta real pela tela. | Técnico, quando houver acesso. Pacote/interface prontos. |
| Demais contas | Revisar43 candidatas em11 empresas; identificar/cadastrar contas nas134 outras. | Cliente fornece/confere banco, agência/conta, conta contábil, plano, filial e direção; cadastro/revisão já existem. |
| Fontes por competência | Extrato de cada conta/mês e Razão correspondente; tratar arquivo ilegível/colunas. | Cliente fornece fonte; nova coleta do Razão usa agente atualizado e vínculo validado. |
| Títulos fora do piloto | Generalizar captura de títulos por empresa/conta/período e torná-la autônoma. Contrato atual fixa212/8/setembro2026 e expected_counts/comando. | Trabalho técnico ainda aberto (Q-28/Q-46), separado da validação humana. |
| Títulos/baixas e DE-PARA | Revisar natureza/componentes/estornos e vínculos reais; cadastrar contas/contrapartidas aptas no plano e revisar/ativar regras. Catálogo bruto não é LedgerAccount aprovado. | Cliente/contadora valida; telas já entregues. C01/C02 seguem adiados. |
| Retorno ao Domínio | Confirmar leiaute/adaptação e importação de fato não escriturado com conferência no destino. | Técnico+contadora/operador; Q-47 continua adiado, não bloqueia consulta/conciliação disponíveis. |
| Contrato completo | Cobertura contratada, amostra/métricas reais e aceiteD-73. | Técnico+contadora/responsável; primeiro treinamento e conferência real já relatados. |

Formatos atuais: OFX/QFX/CSV/XLSX/PDF até25MiB; imagens/XLS antigo e conteúdo PDF não extraível não são cobertura universal. Novas chamadas de IA não são requisito para usar conciliação ou revisar sugestões retidas. Backup não é bloqueio desta rodada. Não apresentar todos os itens restantes como responsabilidade da cliente.
