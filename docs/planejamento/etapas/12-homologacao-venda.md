<!-- D373-V412-IN-PROGRESS-2026-11-17 -->
**17/11/2026 — D-373/V-412 em execução: descoberta completa de planos e contas.**
Ampliação autorizada para as146 empresas, consultando catálogo completo e relações
empresa/plano/filial com proveniência, além da configuração de conciliação.
Preparação em lote e confirmação apenas dos campos não comprovados pela fonte;
release100 continua publicada até validação/publicação da nova candidata.
Primeira consulta ampliada interrompida em TEXT_CONTRACT; correção em validação.
Fonte completa e ativação adicional ainda não comprovadas; ver checkpoint V-412.

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

## D-364/V-403 — Facilitar o uso da cliente, 16/11/2026

- [x] Implementar carteira por empresa/conta/mês e relatório legível/imprimível, mantendo o CSV técnico.
- [x] Validar localmente escopo empresa E módulo, período, erros explícitos, leitura sem decisão e importação preenchida sem envio automático.
- [x] Atualizar guia e preparar cenário privado de treinamento técnico com dados fictícios; resultados humanos permanecem sem aprovação presumida.
- [x] Concluir QA visual sintético e regressão PostgreSQL focada, incluindo concorrência.
- [x] CI integral, release93 compatível e conferência posterior concluídos; dados/decisões preservados e serviços saudáveis, sem atribuir aceite humano.
- [ ] Q-28/Q-46/D-73: cobertura real, semântica, amostra, recuperação/backup, treinamento e aceite efetivos.

O avanço é de operação da interface. Não houve coleta financeira nova,
aprovação de conta ou ampliação comprovada da carteira. Q-47/C01/C02
permanecem adiados. [V-403 e limites](../../../VALIDACOES.md).

## D-363/V-402 — Publicação técnica da expansão, 16/11/2026

- [x] Implementar lote mensal revisado, prévia sem escrita, idempotência e isolamento de falhas da fila no checkout isolado.
- [x] Aprovar189 testes PostgreSQL, incluindo concorrência; Ruff/check e migrações sem alterações aprovados.
- [x] Gerar matriz privada146/43 dos perfis de13/11, sem aprovação de vínculos ou nova coleta financeira.
- [x] Preparar roteiro TXT privado com146 nomes cadastrais atuais/códigos conferidos e43 referências à ficha existente; leitura CICA, sem capturaERP.
- [x] Concluir CI43873060568 integral, integrar PR21/mainc053cc0 com árvore idêntica à fonte1a16f3c e publicar release92.
- [x] Conferir732 hashes em web/worker, liveness/readiness200 e workerpong; somente duas máquinas ativas atualizadas, legado igual/parado e capacidade/configuração preservadas.
- [x] Conferir14 grupos protegidos e prévia real READ ONLY do piloto, sem novos jobs ou mudança de autoria/evidência/histórico.
- [ ] Q-28: revisar contas/banco/plano/direção e contagens mensais próprias antes de ativar coleta ampliada.
- [ ] Q-46/D-73: semântica, revisão, recuperação, treinamento e aceite efetivos; Q-47/C01/C02 continuam adiados.

Etapa permanece em andamento. Publicação técnica não amplia por si a carteira
operacional nem comprova recorrência/filiais ou encerra o contrato. Piloto e
alterações locais preservados; sem MSI, nova capturaERP, conta ou inferênciaIA.
[Provas e limites em V-402](../../../VALIDACOES.md). Os blocos abaixo são históricos.

> **Reconciliação V-383 — 13/11/2026:** oficial1.0.9/backend86, captura fiscal, persistência e comparação técnica concluídos conformeV-367–382. C01/C02 adiados; carteira financeira, tradução financeira/banco/regras, IA, Q-47, D-73, recuperação, treinamento e aceite continuam pendentes. Checklist abaixo mantém os critérios; versões e PRs antigos são históricos. [Lista vigente](../pendencias-conclusao-2026-11-02.md).

# Etapa 12 — Homologação integrada e liberação comercial

## Checklist vigente de conclusão — D-343/V-366 (12/11/2026)

A etapa permanece **em andamento**. Os blocos datados abaixo são históricos;
instalação/corte, carga cadastral e coleta inicial não voltam a ser bloqueios.

- [x] V-325/V-347/V-352/V-361: acesso CONTAD, oficial1.0.8, carga A146 e coleta real inicial comprovados.
- [x] V-365: CI PostgreSQL/Windows aprovado e restauração/replay local sintético conferidos; PR11 registrado em rascunho, sem presumir merge/deploy.
- [ ] CONTAD: fontes/contas da carteira completa, títulos/baixas, DE-PARA assistido por IA, saldos/regras e importação contábil Q-28/Q-46/Q-47.
- [ ] D-73: 200 fatos distintos revisados por fluxo, precisão mínima95% aplicável, integridade, até5min por empresa, retomada até15min e restore até4h; RPO e rotina de backup registrados.
- [ ] CONTAD: treinamento inicial executado e aceite formal vinculado à release.
- [ ] NFS-e: testar/concluir a correção específica de espécie D-318/V-320, ainda pendente segundo o responsável em D-343; preservar a importação anterior aceita em D-295.
- [ ] Suíte: fechar homologações por operação/módulo, e-mail/cobrança, fontes/relatórios, privacidade, carga/alertas, suporte e oferta coerente conforme pacotes existentes.

V-322 comprova restore pontual isolado, V-365 usa corpus sintético local;
nenhum deles encerra sozinho a recuperação operacional recorrente. O snapshot
pontual citado no handoff vence em13/11/2026 às11:29:44 de Brasília, segundo
o registro existente; validade/rotina precisam ser conferidas em PC-09.
[Pendências, responsáveis e provas](../pendencias-conclusao-2026-11-02.md).
Sem produção/ERP/CI consultados novamente nesta revisão documental.


**Conexão vigente — D-308/V-309 (03/11/2026):** versão 1.0.1 atualizada no PC
Windows 11 Pro AMD64, serviço Running e conexão Domínio confirmada no
configurador. Pareamento bloqueado por 503, CA não configurada no servidor.
Procedimento proposto ao final; nenhuma mudança de produção executada.

**Preparação Windows em 03/11/2026 — D-306/V-305:** MSI 1.0.0 e ciclo de
instalação/serviço/configurador/DPAPI/reparo/reinício/remoção aprovados em runner
Windows Server 2022 descartável, com 25 verificações. Instalador de teste sem
assinatura digital e com hash conferido. O acesso ao PC da cliente continua
pendente; esta evidência não homologa DSN/ODBC/pareamento/rede/ERP reais.

**CONTAD em 03/11/2026 — D-305/V-304:** contrato local de Razão, ponte das
filas, conferência Sicredi/CSV e ensaio de 200 lançamentos sintéticos validados.
Não equivalem ao piloto real D-73. Acesso ao PC, pareamento, fonte Domínio real,
títulos/parcelas/baixas, DE-PARA revisado, arquivo importado, recuperação,
treinamento e aceite continuam pendentes. Nenhum gate contábil foi habilitado.

**Acompanhamento 10/10/2026 — D-295/V-294:** consultar a [auditoria de fluxos e plano de finalização](../auditoria-fluxos-serpro-finalizacao-2026-10-10.md). A etapa já tem publicações e validações parciais registradas abaixo; seu estado vigente é **em andamento, não concluída**. O responsável confirmou a validação externa NFS-e como concluída. Permanecem os gates de Serpro por operação, outras integrações, recuperação, operação e aceite por módulo.


[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Em andamento nesta execução. As validações e publicações parciais registradas nesta
etapa não constituem homologação integrada nem aceite de liberação; os itens pendentes abaixo
continuam como gates de conclusão.

**Dependências:** 01–11.

**Decisões relacionadas:** D-03, D-46, D-51, D-56, D-77, D-81, D-86, D-87.

## Escopo e checklist

- [ ] Configurar Brevo SMTP, remetente e autenticação de domínio/DNS da CICA; testar confirmação, convite e recuperação, incluindo falha de entrega (D-77/D-78).

- [ ] Identificar ambiente de produção e capacidade necessária, sem presumir provedor ou contratar recursos.
- [ ] Reunir toda dependência de site em produção preparada nas etapas 01–11: domínio/HTTPS/DNS, credenciais e consentimentos externos, serviços hospedados, chamadas reais a provedores, pilotos e homologação comercial (D-87).
- [ ] Validar deploy, migrações, workers, agendador, storage e conectividade dos agentes.
- [ ] Executar o piloto operacional do agente CICA: instalação limpa x64, DSN/driver, pareamento HTTPS/mTLS, revogação, atualização distribuída, queda/retomada de rede, backup `.dom` autorizado e escrita documental na raiz Windows real. Definir Q-22/Q-31 no contexto do piloto (D-86).
- [ ] Executar restauração de banco e documentos, recuperação de falhas e retorno de versão.
- [ ] Homologar retenção, exportação, exclusão, termos e contatos de suporte.
- [ ] Executar piloto por módulo, com critérios e amostra aprovados.
- [ ] Entregar manuais de instalação, operação e suporte, matriz de compatibilidade e limitações.
- [ ] Produzir relatório final de liberação por módulo.

## Bloqueios e responsabilidade

Q-24, Q-28 a Q-30 e Q-35. Recursos pagos exigem aprovação específica.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

- [x] V-230: repetir regressão local em PostgreSQL 17 isolado; corrigir locks incompatíveis nas projeções fiscais; 1.012 testes/39 subtestes aprovados, incluindo recorrência e tokens concorrentes.
- [x] V-231: preparar regressão PostgreSQL integral no workflow local, antes dos builds e sem tolerância a falhas; testar isolamento da configuração.
- [ ] Publicar o workflow e confirmar sua primeira execução no GitHub Actions; proteger a publicação contra bypass do CI. A configuração local não prova enforcement remoto.

Instalação integrada, carga aprovada, queda de serviços, restauração verificável, rollback compatível com migrations, retenção e piloto por módulo.

**Critério de aceite:** Todos os módulos da oferta possuem evidência de funcionamento e operação sustentável; nenhuma pendência crítica é escondida como concluída.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

### V-202 — Preparação da publicação no Fly.io

- [x] Criar a organização `cica` e reservar o app `cica-contabil`, ainda sem deploy ou recurso faturável provisionado.
- [x] Validar a configuração local do Fly e o check do Django.
- [x] Aprovar especificamente a arquitetura e o custo recorrente antes de criar Postgres, Redis, storage e máquinas (D-177).
- [x] Configurar segredos, executar migrações, publicar web/worker/agendador e validar filas, storage e HTTPS.
- [ ] Validar restauração e rollback em produção.

### V-203/V-204 — Publicação e revalidação operacional

- [x] Aprovar e provisionar a arquitetura de D-177.
- [x] Configurar segredos, executar migrações e publicar web e worker/agendador.
- [x] Validar página pública, HTTPS, health de banco/cache, fila e ciclo temporário no storage privado.
- [x] Revalidar DNS, TCP/443, TLS, redirecionamento e estabilidade de vinte requisições após `ERR_CONNECTION_RESET` não reproduzido.
- [ ] Homologar restauração, rollback e recuperação cronometrada; a disponibilidade atual não substitui essas provas.

### V-205 — Domínio próprio

- [x] Registrar `cicacontabil.com.br` e `www.cicacontabil.com.br` no Fly.
- [x] Configurar os hostnames em `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` e revalidar o health após o restart.
- [x] Remover da zona HostGator o A legado `162.240.81.81`, preservando os destinos Fly.
- [x] Verificar a emissão TLS e validar apex e `www` após a correção autoritativa e a limpeza do cache DNS local.
- [x] Tratar token CSRF renovado no seletor de aparência e substituir a página técnica 403 por recuperação segura, preservando JSON nas APIs (V-245).

## Prompt de execução

> Execute a etapa 12. Faça a homologação integrada da CICA e reúna evidências por módulo, incluindo restauração, filas, integrações, instalação e suporte. Confirme com o responsável ambiente, metas e critérios ainda pendentes. Não libere venda nem contrate infraestrutura por inferência.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.

### V-246 — População autorizada da demo publicada

- [x] Publicar somente os seis arquivos necessários sobre a release existente, sem migração ou infraestrutura nova.
- [x] Popular exclusivamente o tenant demo com 84 atividades e conferir replay sem duplicação.
- [x] Verificar health/web/worker e as telas publicadas em desktop/celular por Playwright MCP.
- [x] Encerrar os contextos do navegador e o QA local desta tarefa.

Release 33, 01/10/2026. V-246 registra as contagens e os limites; dados, prazos, pessoas e evidências são fictícios. Isso não encerra a etapa 12 nem comprova fontes fiscais, cobrança, recuperação ou piloto reais.

### Piloto contratual CONTAD — D-302/D-303/V-302 (02/11/2026)

Recorte PC-19, com [matriz e roteiro](../verificacao-conciliador-contad-2026-11-02.md).
Não exige concluir os demais módulos da suíte. Acesso ao PC da cliente ainda
será fornecido; Domínio local e inclusão de pagar/receber já confirmados.

- [x] Preparar correções e testes locais da integridade OFX, builds do agente
  e roteiro seguro. Isso não prova instalação ou homologação CONTAD.
- [ ] Autorizar/receber recorte de dados e canal seguro; instalar/parear pacote
  atual no PC e conferir DSN/driver/conta de serviço sem escrita no ERP.
- [ ] Conferir Razão, títulos/parcelas/baixas e DE-PARA inicial assistido por IA;
  completar o encadeamento e a comparação conforme Q-28/Q-46/Q-47.
- [ ] Auditar legado, validar 200 itens independentes e demais critérios D-73,
  recuperação, destino/importação quando aplicável, treinamento e aceite.

Sem deploy ou liberação desta correção nesta entrega. O aceite NFS-e anterior
não habilita o gate contábil. Retenção/comercial gerais continuam com seus próprios
responsáveis e não alteram silenciosamente as condições deste contrato.


### Windows 11 cliente — D-307/V-306 (03/11/2026)

- [x] Executar 25 verificações do mesmo pacote x64 em Windows 11 Enterprise
  ARM64 build 26200, ProductType=1, com relatório/ambiente/logs preservados.
- [x] V-307: repetir no PC de teste Windows 11 Pro AMD64 por RDP, 24 checks
  aprovados. Agente conservado instalado, sem configuração de ERP.
- [ ] Homologar driver/DSN/pareamento/rede/ERP no PC autorizado da cliente.

O resultado ARM64 é adicional ao Server 2022 V-305; não resolve o acesso RDP
nem os critérios do piloto contábil. MSI sem Authenticode; nenhum deploy.


### Prova Windows 11 Pro Intel/AMD — V-307

Instalação, serviço, GUI, ACL/DPAPI, diagnóstico, reparo e reinício passaram no
PC disponibilizado. O bloqueio de controle descrito em V-306 foi resolvido.
Essa prova do pacote não constitui o piloto CONTAD ou teste de ODBC/pareamento.

### Domínio Local no PC Windows — D-308/V-309 (03/11/2026)

- [x] Corrigir uso da autenticação do DSN existente e validar 28 testes .NET.
- [x] Gerar 1.0.1, 25 verificações CI aprovadas e hash idêntico no Mac/PC.
- [x] Atualizar a instalação 1.0.0 no PC real, serviço automático Running e
  confirmar conexão no configurador CICA, sem escrita no ERP.
- [x] Sondar prontidão do pareamento sem código/CSR/dados: HTTP 503, CA ausente.
- [ ] Configurar CA/caminhos protegidos no ambiente hospedado com autorização
  da alteração de produção e verificar a rota de emissão; não enfraquecer TLS.
- [ ] Parear no escritório/recorte definido e testar leitura pelo serviço,
  paginação/repetição/queda/retomada, comparações independentes e critérios D-73.

A conexão mínima do configurador usa o contexto interativo; não comprova ODBC
sob LocalSystem nem envio do serviço. Não houve deploy ou alteração de produção.

Procedimento preparado para a próxima ação D-308, ainda não executado:

1. Obter autorização específica para configurar a CA no servidor CICA existente
   e aplicar configuração/reinício necessário. Sem recurso recorrente ou custo
   novo; não publicar as mudanças contábeis locais junto desta ação.
2. Conferir configuração hospedada efetiva e preservar referência recuperável
   da release/configuração vigente. Não substituir CA existente sem verificar
   dependentes. Preparar certificado/chave protegidos, fora do Git/chat, e os
   caminhos `EDGE_AGENT_CA_CERT_PATH`/`EDGE_AGENT_CA_KEY_PATH`, com acesso
   somente do processo autorizado.
3. Aplicar somente a alteração revisada, conferir health e repetir diagnóstico
   vazio: esperado erro de CSR inválida em vez de 503. Isso comprova prontidão
   da rota, não emissão/pareamento/mTLS. Em falha, restaurar configuração/release
   se alterada e conferir health; conservar logs sem segredos.
4. Antes de criar agente, definir escritório/destino e recorte de empresas e
   período. A autorização do PC não permite enviar toda a carteira. Depois
   executar pareamento/leitura pelo serviço/retomada com esse limite; validar
   mTLS separadamente, sem desabilitar validação de certificados.

O POST de diagnóstico não consome código de cadastro nem cria agente. Não há
pareamento ou transmissão financeira aprovados por este procedimento escrito.

## Continuidade D-309/V-310 — preparação de liberação (04/11/2026)

- [x] Entregar e testar localmente bloqueios de duplicidade/recorte/transporte/interface/OCR.
- [x] Preparar MSI 1.0.2 com hash e CI, preservando 1.0.1 instalado e pacote anterior.
- [x] Testar transporte Nginx/Django real local, replay Redis/Celery e restauração de cópia sintética com hashes.
- [x] Selecionar candidato Fedrizzi por leitura autorizada; 115 itens, sem transmissão ou escrita ERP.
- [ ] Conferir sessão/configuração efetiva Fly: CLI existente não acessa `cica-contabil` no Mac ou Windows.
- [ ] Autorizar/aplicar alteração hospedada revisada, depois de preservar release/configuração recuperáveis.
- [ ] Validar ingresso mTLS e agente Windows, recorte, fonte independente e fila/recuperação publicados.
- [ ] Concluir Q-46/Q-47, importação Domínio conferida, D-73, treinamento e aceite CONTAD.

### Configuração e retorno preparados para revisão, ainda não aplicados

O `fly.toml` local usa `[http_service]` na porta 8000 e mTLS false. Esse caminho
termina TLS no Fly Proxy; instalar apenas CA ou confiar em cabeçalho público não
prova certificado do cliente no Django. Conferir o ingresso efetivo antes de
propor uma mudança exata. A [documentação Fly de serviços](https://docs.fly.io/networking/services)
distingue terminação TLS e TCP pass through; este último exige avaliar IP,
certificado do servidor e custos. Nenhum novo ingresso, IP, recurso ou provedor
foi criado/contratado. A configuração abaixo é requisito de integração, não um
deploy Fly pronto que possa ser aplicado sem esse confronto.

| Configuração | Valor/guarda para a alteração revisada |
|---|---|
| CA | `EDGE_AGENT_CA_CERT_PATH` e `EDGE_AGENT_CA_KEY_PATH` em armazenamento protegido persistente; cert/chave correspondentes, CA válida, permissão de assinatura. Não substituir CA existente sem inventário. |
| Gateway | Nginx recebe o TLS do cliente e sobrescreve cabeçalhos. Incluir `deploy/nginx/edge-agent-mtls.conf` no servidor TLS; renderizar **somente** `${EDGE_AGENT_MTLS_PROXY_SECRET}` e validar `nginx -t`. |
| Segredo privado | `EDGE_AGENT_MTLS_PROXY_SECRET` aleatório de pelo menos 32 caracteres no proxy e Django, fora de Git/chat/logs e inacessível ao agente. |
| Exigência | `EDGE_AGENT_MTLS_REQUIRED=true` apenas no percurso completo validado; não emitir código financeiro enquanto faltar mTLS/recorte. Testar ausência/certificado inválido/expirado/revogado e cabeçalhos forjados. |
| Migrações | `hub.0076` → `hub.0077` e `intelligence.0031` aditivas. Conferir plano e backup consistente de banco/objetos antes da release autorizada. Não apagar evidências em rollback. |
| Cadastro | `issue_agent_enrollment --financial-account <UUID existente> --period-start <início> --period-end <fim> --statement-id <ID revisado>`; repetir somente IDs da mesma conta. Escritório e destino concretos precisam estar aprovados. |
| PC | Pacote 1.0.2/hash V-310, `test-upgrade-windows11-pc.ps1`, origem 1.0.1.0, GUI fechada e sem configuração inesperada. Executar por RunAs normal. Não alterar política de execução, firewall ou autenticação DSN. |

Antes de alterar, preservar referência de imagem/release atual, configuração
não secreta e recuperação dos segredos por mecanismo seguro; exportação/hash,
evidências, alocações e arquivos precisam pertencer ao mesmo ponto consistente.
No recuo, bloquear novos cadastros e revogar o agente do piloto antes de retornar à imagem/configuração
anterior verificada e manter as migrações aditivas. Não tornar mTLS falso como
forma de aceitar tráfego do piloto. Revogar agente em caso de exposição e refazer
pareamento, preservando auditoria. Conferir health, fila e contagens/hashes depois.

O MSI anterior foi preservado. Reparo preservando configuração passou em CI;
upgrade/downgrade 1.0.1↔1.0.2 com configuração real e retorno hospedado ainda não
foram demonstrados. Não usar remoção de tabelas/configuração como procedimento
ordinário de retorno. Restauração SQLite/media local em 0,02 s não equivale a
restore Neon/objetos em quatro horas; RPO/janela de medição continuam pendentes.

Referências do gateway: [verificação SSL Nginx](https://nginx.org/en/docs/http/ngx_http_ssl_module.html#ssl_verify_client)
e [sobrescrita de cabeçalhos](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header).

Persistência final D-309/V-310: configuração DPAPI é gravada em arquivo
criptografado temporário na pasta protegida, com flush e substituição atômica;
falha conserva o arquivo anterior e limpa o temporário. Ciclos sem mudança de
recorte/destino não regravam configuração. O pacote final foi revalidado no
Windows com 38 testes .NET, incluindo falha por bloqueio de arquivo, e 25 checks
MSI (run 41845516300). Sem atualização no PC ou alteração do DSN.

## Percurso vigente sem CA privada — D-310/V-311 (04/11/2026)

Este procedimento substitui CA/gateway/ingresso mTLS como requisito do piloto.
Usar o HTTPS normal já previsto para o site, com validação de certificado do
servidor e HMAC individual. Nenhuma nova infraestrutura ou contratação foi feita.

- [x] Preparar backend e agente 1.0.3 para `authentication_mode=hmac`, sem CSR/certificado de cliente ou acesso à CA.
- [x] Exigir HTTPS, código válido de uso único, assinatura/timestamp, agente ativo e recorte válido.
- [x] Testar HTTPS real local sem CA de cliente, replay, rejeições e reinício; testar configuração HMAC sem PFX sob LocalSystem em CI.
- [ ] Publicar backend e instalar versão compatível no PC, com autorização específica e acesso disponíveis.
- [ ] Concluir sincronização, ERP/recuperação publicados, Q-46/Q-47 e aceite D-73.

1. Quando houver acesso, preservar release/configuração recuperáveis e conferir
   a publicação revisada. `EDGE_AGENT_MTLS_REQUIRED=false` é o percurso HMAC;
   instalação com `true` explícito continua exigindo certificado. Não modificar
   outras instalações por inferência. Acesso Fly segue indisponível ao responsável.
2. Publicar backend compatível e manter as migrações aditivas 0076/0077/0031
   previstas na release. D-310 não adiciona migração. CA/chave/gateway mTLS não
   são necessários para HMAC. O POST HTTPS com `authentication_mode=hmac` e sem
   código deve recusar o código (403), sem erro de CA; não cria agente.
3. Usar o MSI 1.0.3 de V-311 e conferir seu hash/manifesto antes do RunAs normal.
   Roteiro de atualização conserva guardas de versão, GUI fechada e ausência de
   configuração inesperada. PC permanece 1.0.1, sem instalação nesta rodada.
4. Só depois de conferir empresa/conta/competência e autorizar destino/envio,
   emitir código com manifesto e parear. O configurador salva modo HMAC e segredo
   via DPAPI/ACL/gravação atômica; nenhuma chave de certificado de cliente existe.
5. Conferir HTTPS, assinatura inválida, expiração/reuso de código, revogação,
   recorte, repetição/retomada e processamento pelo serviço. Preservar limites
   do piloto; autenticação nova não autoriza transmitir a carteira.
6. Em retorno ao backend/agente anterior incompatível, revogar primeiro o
   agente HMAC e conservar configuração, evidências e migrações aditivas.
   Configuração HMAC não vira certificado automaticamente. Não apagar histórico.

Relatórios sintéticos não substituem publicação, ODBC real do serviço, restore
Neon/objetos, importação Domínio, treinamento ou aceite. Não solicitar novamente
CA ou acesso Fly nesta rodada; o responsável já informou a indisponibilidade.

## Continuidade D-311/V-312 — 05/11/2026

- [x] Preparar ZIP de fonte local, manifesto por arquivo e roteiro revisável
  de configuração/publicação/retorno: [release candidata](../../contad-release-2026-11-05.md).
- [x] Ensaiar migrações aditivas em PostgreSQL descartável, sem alteração de
  desenvolvimento/produção/ERP; manter 0076/0077/0031 no retorno de aplicação.
- [x] Restaurar PostgreSQL/arquivos sintéticos em outro banco: 182 tabelas e
  15 sequências iguais, dois arquivos íntegros, 200 movimentos/200 registros
  independentes/dez decisões preservadas, 5,726 s. Não comprova Neon/objetos,
  banco knowledge, RPO ou retorno à versão anterior em produção.
- [ ] Acesso/autorização de publicação, PC/serviço real, destino/transmissão,
  fonte Domínio, Q-46/Q-47 e IA Q-08/Q-09 continuam nos gates existentes.
- [ ] Provar D-73 em dados reais, recuperação operacional, treinamento e aceite
  CONTAD. Nenhum bloqueio foi convertido em conclusão.

Instalação Domínio no PC de teste atualizada para 10.6A-10/ajuste 2 após backup
confirmado pelo responsável e assinaturas oficiais válidas. Não equivale à
atualização do agente, publicação CICA, conversão de base verificada ou piloto
CONTAD. Aplicação reaberta até login, sem relatórios obtidos; intervenção direta
do responsável solicitada para autenticar, sem credenciais no chat.

## Continuidade D-312/V-313 — 05/11/2026

- [x] Reempacotar candidata após núcleo/CLI de prévia: 809 arquivos, hashes de
  ZIP/workspace iguais; pacote anterior preservado, sem publicação.
- [x] Validar 85 testes focados e CLI sintética, Ruff global/MyPy; resultados
  não substituem regressão V-312, testes Windows ou homologação contábil.
- [x] Registrar Razão emitido e impedimentos do primeiro candidato; autorização
  de pesquisa alternativa somente leitura recebida. Alternativa com fechamento
  fiscal 09/2026, contábil 11/2014; não é período contábil homologado.
- [x] Preservar PDF A Pagar no Windows e resultados dos filtros em evidência
  privada; baixas, vínculo bancário e semântica não homologados por essa pesquisa.
- [ ] Fechar recorte real, fontes/regras/importação, publicação e serviço real,
  D-73/recuperação operacional, treinamento e aceite do proprietário CONTAD.

## Publicação do código D-313/V-314 — 05/11/2026

- [x] Registrar autorização expressa e publicar 84 arquivos revisados na main,
  commit 4fede1e; SHA remoto conferido, arquivos privados preservados fora do Git.
- [x] Conferir sucesso do CI 42067809017 para o commit exato: Python/PostgreSQL,
  agente, pacote Windows e três builds Docker; logs/skips/limites em V-314.
- [ ] Publicar aplicação hospedada e comprovar percurso real, recuperação,
  Q-28/Q-46/Q-47, D-73, treinamento e aceite. GitHub não equivale à implantação.

## Teste bancário local — D-314/V-316 (05/11/2026)

- [x] Executar percurso persistido com anexos reais em SQLite/mídia novos,
  42 verificações finais aprovadas; dados privados preservados fora do Git.
- [x] Corrigir duas falhas e validar 134 testes/24 subtestes em PostgreSQL,
  incluindo corridas de revisão humana, sem skips; sem nova prova Windows.
- [x] Preparar candidata de 809 arquivos/hashes conferidos, relatórios privados
  e evidência do navegador; servidor/aba/contêiner próprios encerrados.
- [ ] Concluir publicação hospedada, fontes/retorno ERP, D-73 operacional,
  treinamento e aceite. O teste local não é homologação completa da CONTAD.


## Continuidade independente — D-315/V-317 (05/11/2026)

- [x] Conferir CI 42079806454 aprovado para 700b496, sem presumir deploy.
- [x] Preparar nova candidata após correção de retorno: 809 hashes de ZIP e
  workspace iguais, SHA-256 em V-317; pacotes anteriores preservados.
- [x] Encerrar QA somente sintético e registrar testes/limites: 93 testes e
  24 subtestes locais, navegador desktop/celular/claro/escuro/teclado.
- [ ] Publicação hospedada, serviço real, fontes/layout/importação, D-73,
  recuperação operacional, treinamento e aceite continuam pendentes.

## Operação pontual D-317/V-319 — 06/11/2026

- [x] Conferir nas máquinas web/worker que bancos principal e knowledge usam
  Neon; no legado, sessões/TCP sem clientes externos na observação.
- [x] Executar a alternativa autorizada de manter `cica-contabil-db` parado,
  confirmando `stopped` e preservando máquina/volume de 3 GB para rollback.
- [x] Conferir site/readiness 200 após parada nos domínios público e Fly,
  banco/cache `ok` e web/worker iniciados; registrar evidências em V-319.
- [x] Registrar que o legado permanece em CICA, sem transferência ou exclusão;
  armazenamento preservado ainda pode gerar cobrança, conforme preços Fly.
- [ ] Concluir os gates de recuperação operacional e homologação já existentes;
  essa parada não comprova restore, piloto integrado ou liberação comercial.

## Implantação CONTAD — D-320/V-322 (06/11/2026)

- [x] Confirmar acesso Fly/app/organização e preservar release 71/imagem/configuração
  anteriores; consultas de aliases/migrações/gates sem segredos ou dados contábeis.
- [x] Reconciliar IDs por escolha humana, preservando os locais e renumerando
  os remotos; integrar source/main sem perda das alterações anteriores.
- [x] Preparar candidata de 816 arquivos/hashes e manifesto incluindo hub.0078;
  manter migrações aditivas de ambos os aliases no retorno da aplicação.
- [x] Aplicar migrações e aprovar 42 testes focados em PostgreSQL 18.6 sintético,
  além da regressão integral PostgreSQL 17; não é restore de produção.
- [x] Instalação guiada no PC: MSI/hash/versão 1.0.3, serviço Running/Automatic
  e awaiting_configuration informados; nenhum pareamento/envio configurado.
- [x] Criar escritório próprio CONTAD em activation_pending e auditoria, após
  confirmação humana, com zero membros/módulos liberados e sem convite.
- [x] Conferir backup pontual Neon **18.6**/Tigris e restore isolado dos dois bancos,
  contagens/esquemas/hashes e 53 referências/arquivos, expiração sete dias.
  Compute suspenso, chave temporária revogada; nenhum dump no Mac. Não conclui D-73.
- [x] Publicar fonte f86ae4d e conferir CI 42231907397 aprovado; 816 hashes iguais.
- [x] Publicar candidata no Fly/release 72; conferir fonte em web/worker,
  migrações nos dois aliases, health e worker ready; agente inválido 401,
  prévia/download anônimos bloqueados. Lista só CONTAD, exportação false.
  Não equivale a pareamento ou teste autenticado da cliente em produção.
- [ ] Concluir acesso/ativação do escritório e recorte/ODBC/serviço/retomada reais,
  Q-28/Q-46/Q-47, D-73, recuperação operacional, treinamento e aceite.

Autorização de deploy existe no plano aprovado; o gate pontual de
backup/retorno e o deploy foram cumpridos. Operador informou sucesso ODBC e
conexão no configurador x64; SURIA/código Domínio 212/09-2026 informados e fontes
bancárias identificadas; conta contábil 8 — BANCO SICREDI transcrita pelo operador.
Razão real de quatro páginas recebido e conferido localmente, com 163 datas/
valores iguais ao banco; há divergência de saldos na captura de extrato Domínio
a esclarecer em Q-28. Permanecem vínculo/referência bancária/IDs, partidas
completas/revisão semântica, acesso/ativação,
recorte completo e provas reais do serviço/fluxos; não repetir a aprovação de deploy. Agente instalado em
espera e cadastro provisionado não equivalem à implantação completa.

## Retomada do corpus local — D-320/V-323 (06/11/2026)

- [x] Registrar esclarecimento humano: empresa fechada, arquivos fornecidos
  para teste e aceitos como evidência; origem do saldo da captura não é gate local.
- [x] Executar nova CLI privada banco/Razão com os arquivos reais, 163 linhas
  conferidas, ambiguidades mantidas, fontes preservadas e rede/banco bloqueados.
- [x] Registrar 139 testes aprovados/cinco skips PostgreSQL, verificações
  estáticas aprovadas e relatório privado 0600, sem nova migração ou deploy.
- [ ] Completar acesso/agente real, fontes/regras ainda ausentes, DE-PARA,
  treinamento e aceite; não converter a evidência dos arquivos em homologação.


## Estado atual CONTAD — D-321/V-324 (06/11/2026)

- [x] Conferir fonte 651368c e CI 42282953292 aprovado; candidata 820 hashes,
  imagem amd64/runtime conferidos. Trabalhos locais anteriores preservados.
- [x] Reconferir manifesto/metadados dos 53 objetos do backup D-320, mesma
  retenção; sem nova cópia, custo autorizado adicional ou novo ensaio de restore.
- [x] Publicar release Fly 73 e conferir web/worker, 647 fontes/hashes,
  migrações/Neon, health, acesso protegido, 512 MB e reserva parada.
- [x] Ativar CONTAD/Conciliação/contrato individual R$ 200 existente, sem convite,
  conta pessoal/senha, cobrança automática ou fatura, conforme escolha humana.
- [x] Registrar autorização específica de dados e parear recorte restrito;
  operador comprovou LocalSystem/Auto/ready e reinícios, sem campos de senha
  no novo DSN. Backend: 163 itens, conector saudável, sem duplicação/fora do recorte.
- [x] Conferir datas/valores com os arquivos aceitos, preservando fatos de
  extrato versus Razão e sem contar formatos/repetições como novos eventos.
- [x] Concluir acesso pessoal D-321/V-325 com senha inicial validada,
  Proprietária somente CONTAD, login HTTPS e importação disponível; sem convite
  ou upload. Não equivale a aceite do fluxo contábil completo.
- [ ] Concluir fontes completas/regras Q-28/Q-46, DE-PARA, Q-47/importação
  homologada, D-73, recuperação operacional, treinamento e aceite.

Deploy, ativação do escritório e integração real do extrato estão concluídos.
O escopo é piloto bancário autorizado; a homologação integral continua aberta.
O corpus de 163 não preenche os 200 eventos independentes de D-73. O ensaio
pontual de backup/restore anterior não equivale a recuperação recorrente/RPO.


## Objetivo da próxima execução — D-322/V-326 (06/11/2026)

- [x] Entregar prompt para finalizar as entregas contratuais CONTAD com todas
  as empresas do escritório, estados comprovados e critérios de conclusão.
- [ ] Cumprir implementação/regressão/Windows/jornada real, CI/publicação,
  recuperação e métricas D-73 sobre a integração completa, sem somar replays.
- [ ] Executar treinamento inicial e obter aceite real do responsável,
  fechando requisitos de saída ERP sob autorização e validação Q-47.

[Prompt de finalização](../../contad-prompt-finalizacao-2026-11-06.txt).
Somente preparação documental nesta entrega, sem outra sessão, custo ou deploy.

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

- [x] V-330 (10/11): entregar passo a passo ao operador, com comandos/campos
  conferidos na fonte e gates de runtime/MSI/backend explícitos; execução pendente.
- [x] Adaptar prompt canônico, preservar original/cópias privadas e atualizar
  sequência de execução: instalar novo Server → validar candidato → corte → carteira.
- [x] Implementar candidato pendente, novo UUID/segredo, manifesto herdado,
  bloqueio de coleta e comando de ativação/revogação atômica com auditoria.
- [x] Preparar fonte 1.0.5, atualizar configuração recebida/worker e workflows;
  compilar serviço/configurador/ponte e validar 59 testes .NET, um skip Windows.
- [x] V-329: regressão final PostgreSQL 1.837/163 aprovada, um skip; foco
  SQLite 30 aprovados/seis skips concorrentes cobertos no PostgreSQL.
- [x] D-326/V-338: MSI 1.0.5/.NET 10.0.15 gerado/testado, CI Windows da fonte
  53b834b aprovado: 62 testes e 26 checks, hashes/manifestos conferidos.
- [x] D-327/V-339: backend release 77/fonte 03ed5b0/CI completo aprovado;
  migrations, hashes, saúde e dados conferidos; código privado de uso único emitido.
- [x] V-343: parear candidato no Windows e receber estados de serviço/awaiting_activation.
- [x] V-331: captura confirma Server 2022 Standard, 21H2/build 20348.5761;
  plataforma incluída na matriz .NET 10.
- [x] V-332: captura mostra PowerShell x64/Administrador, serviço sem listagem
  e configuração ausente; catálogo de DSNs x64 observado.
- [x] V-333: receber servidor SrvContabil/banco Contabil, Host/Port vazios
  na configuração inspecionada de Contabil 64/SQL Anywhere 16.
- [x] V-335: operador informou sucesso no reteste ODBC após orientação
  Database/EXTERNO; falha Integrated de V-334 superada no teste interativo.
- [x] V-336: operador confirmou limpeza das credenciais temporárias e salvamento
  de CICA_CONTAD; sem inspeção de segredos no registro.
- [x] D-325/V-337: atualizar projetos/CI para .NET 10 LTS; três componentes
  autocontidos 10.0.15 publicados localmente, 59 testes aprovados/três Windows pendentes.
- [x] V-338: homologar MSI .NET 10 em Windows Server 2022 descartável.
- [x] V-345: conferir conexão real sob LocalSystem na cliente.
  Network/Advanced não inspecionados; teste interativo já informado em V-335.
- [x] V-345/V-346: instalação/ODBC/LocalSystem/ACL/DPAPI e reinício pré-corte comprovados.
- [x] V-346: corte real, novo oficial/primeiro ready, anterior recusado e dados preservados.
- [ ] Inventário/fontes/carteira completa, Q-46/Q-47, D-73, recuperação,
  treinamento e aceite conforme os mesmos gates existentes.

AnyDesk disponibilizado pelo responsável; a ferramenta nativa retornou timeout
-10005 ao obter a janela, sem observar/controlar o Server. Solicitado somente
texto do winver, agora recebido em V-331. Isso não é prova de instalação.
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

- [x] V-363: retomada e rollback do Razão validados com dados sintéticos e recibos existentes de V-361 reconferidos.
- [ ] Medir retomada operacional em até 15 minutos, conferir restauração em até 4 horas e obter aceite D-73.
- [x] V-364: validar localmente o diagnóstico estrutural Q-46 sem usar valores de negócio ou dados reais em testes.
- [x] V-365: restaurar os aliases SQLite e a fonte privada sintética em ambiente separado, conferir o hash e repetir o recibo sem duplicar.
- [x] V-365: registrar no guia CONTAD as evidências operacionais que faltam e quem as confere.


## Preparação operacional de títulos — D-344/V-367 (12/11/2026)

- [x] Confirmar disponibilidade do responsável para acompanhar testes no Domínio hoje.
- [x] Validar títulos/alocações em PostgreSQL descartável, incluindo confirmação concorrente, replay e rollback.
- [x] Preparar guia de operação e complemento fiscal sem valores financeiros ou alteração de agente.
- [x] Obter autorização específica da branch pública/PR em rascunho/CI padrão em D-346.
- [ ] Confirmar CI Windows/integral e entregar comando HTTPS fixado por hash.
- [ ] Executar prova de fonte real Q-46, retorno contábil Q-47 e métricas/recuperação D-73.
- [ ] Publicar alterações aplicáveis após seus gates e registrar treinamento/aceite reais.

Esta preparação não instala MSI, altera coleta real ou habilita exportação.


### Candidata fiscal original pronta — D-352/V-376 (12/11/2026)

- [x] CI integral43285420180 e pacote/upgrade Windows1.0.9 aprovados.
- [x] Conferir artefato/SHA/árvore, imagem714 hashes e base/configuração da release84.
- [x] Reconferir backup53 objetos e executar restauração sintética dos dois aliases/fonte com replay idempotente.
- [ ] Publicar candidata, acompanhar upgrade e receber fonte original sob solicitação confirmada.
- [ ] Conferência semântica Q-46, importação Q-47, carteira completa, IA e recuperação/amostra/treinamento/aceite D-73.


### Publicação da captura preparada — D-353/V-377

- [x] D-353/V-377: publicar/verificar backend85 e pacote1.0.9; preservação dos dados e gate de exportação conferidos.
- [x] V-378:1.0.9 saudável e captura privada original conferidos.
- [ ] Conferência semântica Q-46; demais gates permanecem abertos.


### Fonte fiscal recebida — D-353/D-354/V-378/V-379

- [x] Oficial1.0.9/mesma identidade/DPAPI e fonte original/hash/contagens conferidos.
- [x] Sete exemplos técnicos privados, idempotência e preservação dos dados anteriores conferidos.
- [ ] D-355/V-380: C01/retenções e C02/juros adiados por indisponibilidade do Domínio; não solicitar agora. Semântica/gates continuam pendentes.


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


### D-368/V-407 — Limite da entrega autônoma

- [x] Backend97 e pacote1.0.11 publicados após CI exato; runtime/saúde/dados preservados conferidos.
- [ ] Atualização/capability e coleta real no agente oficial; acesso ao servidor indisponível hoje.
- [ ] Cobertura das contas/competências da carteira, fontes e semântica reais.
- [ ] Generalização técnica da captura de títulos, atualmente fixa no piloto.
- [ ] Retorno DomínioQ-47, amostra/métricas e aceite completoD-73 seguem próprios; não repetir treinamento já relatado.


### Fechamento D-369/V-408 — entrega publicada

- [x] Implementação, testes, CI, migração, pacote1.0.12 e backend98 publicados/verificados.
- [ ] Atualização1.0.12 no SVAPL02 e recepção real; dependência técnica de acesso.
- [ ] Fontes, dados e conferência humana das contas/relações/regras aplicáveis.

**Fechamento D-369/V-408 —16/11/2026:** release98/PR27 e agente1.0.12 publicados após CI43949218680; fonte integrada/testada com árvore idêntica. Migração0041,796 hashes/14 assets, saúde/worker e15 grupos protegidos verificados. Prévia somente leitura146×12 aprovada, incluindo empresas sem conta; fonte v1 intacta e zero novas coletas/normalizações/decisões de produção. A captura fora do piloto está implementada pela tela. Resta tecnicamente aplicar1.0.12 no SVAPL02 e comprovar recepção real, quando houver acesso. Dados, vínculos, semântica e regras reais permanecem humanos; Q-47/C01/C02 adiados e backup fora da prioridade. Pacote único substitui1.0.11 pendente; não refazer pareamento/DSN nem pedir acesso novamente hoje.


### Análise de prontidão — D-370/V-409, 17/11/2026

- [x] Distinguir início de testes do piloto, autonomia das novas coletas, contrato CONTAD e suíte completa.
- [x] Reconferir site/login/saúde, CI e fonte publicada sem mutação de negócio; capacidades do agente ainda desatualizadas.
- [x] Consolidar parecer e roteiro do dia no documento canônico de pendências.
- [ ] Instalar atualização 1.0.12 e comprovar coleta real antes de afirmar autonomia.
- [ ] Corrigir P2 do histórico para uso ampliado; medir vazão real antes de lote da carteira.
- [ ] Revisões humanas, amostra/precisão/desempenho/recuperação/aceite D-73 e retorno Q-47 próprios.

Testes controlados do piloto podem começar. O primeiro treinamento/conferência
não voltou como pendência; falta complementar autonomia/evidência já registrada
em V-401. Backup continua fora da prioridade do início dos testes, sem encerrar
recuperação. Nenhuma liberação integral ou aceite foi registrado por esta análise.


## Correções para testes — D-371/V-410 EM ANDAMENTO (17/11/2026)

- [x] Registrar autorização de corrigir/validar/publicar preservando dados/decisões anteriores.
- [x] Implementar candidata e concluir revisão independente sem novo bloqueador concreto.
- [x] Aprovar SQLite3072/53 skips/181 subtestes; última regressãoPOST coberta pela rodada focada27.
- [x] Registrar .NET176/três Windows reservados e QA17+POST sintéticos, com seus limites.

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
