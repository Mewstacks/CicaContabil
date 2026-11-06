# Etapa 12 — Homologação integrada e liberação comercial

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
