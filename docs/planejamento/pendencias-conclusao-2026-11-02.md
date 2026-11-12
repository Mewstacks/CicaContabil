# Pendências para concluir o projeto CICA

**Avanço de desenvolvimento — D-344–346/V-367, 12/11/2026:** Persistência/alocação normalizadas de títulos e CLI implementadas;181 testes focados PostgreSQL aprovados. Ainda falta o adaptador ERP real Q-46. Complemento fiscal restrito a metadados preparado, com Windows/CI pendentes na branch autorizada. Este avanço não encerra carteira financeira, DE-PARA com IA, Q-47, recuperação, treinamento ou aceite.


## Verificação vigente — 12/11/2026, D-343/V-366

**O projeto ainda não está concluído.** A integração inicial do conciliador
CONTAD está comprovada, mas faltam cobertura financeira da carteira,
títulos/baixas, DE-PARA com IA, retorno contábil homologado e aceite operacional.
A suíte inteira conserva outras frentes próprias. Este levantamento atualiza
os pacotes existentes; não abre outro plano nem executa essas implementações.

Base: plano, decisões, validações até V-365, etapas 00–14, Q existentes,
guia CONTAD e inspeção estática dos caminhos críticos. Produção, ERP e GitHub
não foram consultados novamente; os estados externos abaixo são as últimas
evidências registradas, não uma observação ao vivo.

### Avanços comprovados que não devem voltar como bloqueios

| Entrega | Evidência existente e limite |
|---|---|
| Acesso da Grazi | V-325: Proprietária CONTAD, login real aprovado. Não recriar conta ou convite. |
| Oficial Windows | V-347/V-361: SVAPL02, versão 1.0.8/.NET 10, Running/Auto/LocalSystem/ready; anterior revogado. Não repetir instalação, corte ou DSN. |
| Cadastros das empresas | V-352: carga A146/146 concluída, releituras sem duplicação. M10 não classificado; isso não comprova fontes financeiras de toda a carteira. |
| Razão independente do piloto | V-361: 177 registros, 163 lançamentos, 334 partidas equilibradas e 163 efeitos compatíveis com OFX; replay criou zero. Tudo em rascunho, sem aprovação/exportação ou aceite humano. |
| Regressão atual registrada | V-365: CI 43233720276 aprovado, PostgreSQL 2.026 testes e 163 subtestes; Windows 88 testes. PR #11 registrado em rascunho; aprovação do CI não equivale a merge, deploy ou homologação. |
| Recuperação parcial | V-322: backup/restore pontual isolado; V-365: restauração SQLite/fonte sintética e replay sem duplicação. Rotina operacional e métricas D-73 continuam abertas. |

### O que falta para entregar o contrato CONTAD

| Pendência | O que deve ser feito / quem depende | Prova para encerrar |
|---|---|---|
| Carteira financeira completa — Q-28, PC-17/19 | Desenvolvimento evolui a coleta para empresas/planos/contas e competências desde 09/2026; técnico/contadora comprovam planos compartilhados e situação M. | Contas completas e cobertura por empresa/conta/período, coleta recorrente e retomável sem perda/duplicação. Hoje o código nativo aceita somente empresa/plano/filial 212, conta 8, setembro/2026; só 18 contas brutas referenciadas vieram no snapshot. |
| Títulos a pagar/receber — Q-28/Q-46, PC-19 | Obter/conferir chaves próprias e vínculos título → parcela → baixa; implementar coleta e integração persistida. Contadora valida exemplos em aberto, baixa total/parcial e estorno. | Eventos e saldos rastreáveis na origem e no banco. O recorte de sete objetos/52 relações de V-364 não comprova esses vínculos; contratos/prévia offline não concluem o adaptador. |
| DE-PARA assistido por IA — Q-46/Q-08/Q-09, PC-19/22 | Desenvolvimento liga o apoio de IA ao plano de contas e exemplos revisados; responsável define apenas dados/limites ainda ausentes, contadora aprova sugestões. | DE-PARA inicial demonstrado e revisado com custo/egressão permitidos. O preparador atual cria rascunhos determinísticos a partir de exemplos humanos, sem chamada ao provedor. |
| Saldos, diferenças e regras reais — Q-46, PC-19 | Conferir saldo inicial/final, ambiguidades, agrupamentos, tarifas, transferências, baixas parciais e estornos aplicáveis. | Relatório explicado nos dois sentidos e decisões humanas preservadas. A igualdade técnica dos 163 movimentos não prova fechamento de saldos ou correspondências humanas. |
| Arquivo de retorno contábil — Q-47, PC-19 | Técnico do Domínio/contadora fixam o leiaute aceito, campos/ordem/codificação e partidas simples/compostas; desenvolvimento ajusta o adaptador e prepara caso ainda não escriturado. | Importação de teste autorizada e partidas conferidas no destino. Exportação/confirmar importação seguem bloqueados por gate; aceite NFS-e não homologa essa saída. |
| Qualidade, desempenho e recuperação — D-73, PC-09/10/19 | Proprietário revisa amostra independente; técnico mede processamento, interrupção e recuperação no ambiente representativo, bancos e documentos. | 200 fatos distintos revisados por fluxo, precisão mínima de 95% na classificação automática, zero duplicação/empresa errada/vazamento; até 5 min por empresa, retomada sem perda até 15 min e restore até 4 h; RPO/rotina registrados. Se os 163 eventos atuais forem aceitos na revisão humana, ainda faltam ao menos 37 distintos. |
| Entrega e aceite — etapa 12, PC-30 | Desenvolvimento/operação publicam e conferem apenas as alterações necessárias após validação; responsável conduz treinamento inicial com CONTAD e registra aceite por release. | Usuária conclui o percurso real, manuais/limites correspondem ao liberado e proprietário formaliza o aceite. Guia/roteiro pronto não comprova treinamento realizado. |

Sequência dependente já existente: cobertura/contas e fontes → títulos/regras/
DE-PARA → retorno contábil → percurso real, métricas, recuperação, treinamento
e aceite. Preparação de recuperação e treinamento pode avançar durante as
dependências de fonte. Não reenviar ao ERP o Razão que já estava escriturado.

Conferência estática desta verificação:
[comando de coleta](../../src/apps/intelligence/management/commands/queue_contad_native_ledger.py),
[contrato do backend](../../src/apps/intelligence/native_ledger_contract.py) e
[plano do agente](../../agent-windows/src/Cica.Agent.Contracts/NativeLedgerPlan.cs)
fixam o piloto. [DE-PARA](../../src/apps/hub/depara.py) prepara rascunhos
humanos sem provedor; [alocação de títulos](../../src/apps/hub/title_allocation.py)
é prévia offline sem persistência.
[Serviço de exportação](../../src/apps/hub/reconciliation_service.py) bloqueia
Domínio sem homologação, exclui lançamentos `source_ledger` da saída e recusa
Siescon sem adaptador registrado. Esses seis arquivos coincidem por hash com
a referência `origin/main` disponível localmente; não houve fetch nesta revisão.

O prazo contratual registrado em D-301 é **09/11/2026**, já transcorrido na
data desta verificação. Não foi localizado aceite final nos registros lidos;
este levantamento não altera prazo nem condições do contrato.

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
