# Spec — CICA pronto para venda, v2 (23/11/2026)

Continua [produto-vendavel.md](produto-vendavel.md) (E0–E9, aprovado em 20/11/2026) e [dominio-mcp-fase2.md](dominio-mcp-fase2.md). Reúne a pesquisa pedida pelo dono em 23/11/2026 e propõe os épicos E1b, E10–E16 e E13a. **Proposta: nada aqui está aprovado** (gate 1 do dev-flow). Nenhum arquivo de código foi alterado para escrevê-la.

Legenda: **[C]** confirmado em código ou fonte · **[I]** inferência · **[N]** não achei ou não verifiquei.

## 0. Estado de execução (23/11/2026, fim do dia)

**Achado que explica "o CICA está desatualizado".** A produção (`cica-contabil` no Fly) está na **release v121**, publicada 34 minutos antes da medição por `pedro@mewstack.com.br`, saindo de `origin/main` (`2cc9c5c8`, PR #62). Essa linha tem 207 commits e 100 mil linhas novas desde `aad2f5a6` (10/10/2026): conciliação CONTAD (OFX × Razão, DE-PARA com IA, exportação para o Domínio, uma filial por conta), agente Windows até a 1.0.9, releases v105–v121, decisões até D-396 e validações até V-447. A linha local do dono (`feat/produto-vendavel`) tem 13+ commits sobre a mesma base e **nunca foi integrada**: procuração, cobrança, Contraprova e MCP não estão no ar. As duas linhas só tocam 21 arquivos em comum. [C: `git rev-list`, `flyctl releases`]

| Item | Estado |
|---|---|
| Gate 1 (plano) | aprovado pelo dono em 23/11 ("plano completo"): inclui commit local; push, merge e deploy seguem com OK próprio |
| E0b | feito: `442c32af` docs, `115ec032` portão de qualidade, `83a67cf9` código (E0–E5), só arquivos desta frente. Em worktree limpo: `ruff`, `manage.py check`, `makemigrations --check` limpos e **2.557 testes passaram** (6 ignorados), 10 min. A verificação achou e corrigiu um defeito meu antes de qualquer push: patch de contexto zero tinha encaixado blocos de `settings/base.py` no lugar errado. |
| E13a | feito e testado (`tests/test_cnpj_alfanumerico.py`, 419 testes de regressão verdes); commit `46d44f0d`. `AdnClient.fetch_page` (L3) não foi tocado. |
| **E0c** (novo) | integração com `origin/main` em branch **separada** `integ/origin-main-sync` (a `feat/produto-vendavel` não foi alterada): merge com 10 conflitos textuais resolvidos (imports de `hub/urls.py` e `urls_agent_v2.py`, `navigation.py`, CSS, `Worker.cs` do agente com a fila isolada do Contraprova, três docs); migração de junção `hub/0090` (as duas linhas ramificaram em `0075`; `makemigrations --check` sem desvio). **D-300 a D-333 e V-300 a V-314 foram usados pelas duas linhas com significados diferentes** (e Q-46 e Q-47): `DECISOES.md` e `VALIDACOES.md` ficaram com o texto da produção; o nosso foi para `DECISOES-produto-vendavel.md` e `VALIDACOES-produto-vendavel.md`, sem renumerar (312 referências em código, testes, specs e dados do `dominio-mcp`). Verificação completa da branch em andamento. |
| E10, E11 | sessões `e10-serpro` e `e11-triagem` abertas em worktrees cortados de `origin/main` (base correta: `integra/` e `triage/` não mudaram nessa linha); decisões vão em `docs/specs/e10-notas.md` e `e11-notas.md`, sem D-/V-. |
| E12 | proposta de divisão enviada à sessão do MCP; sem resposta. |
| E1b | lacunas listadas na seção 9; correção não iniciada. |

**Antes de qualquer PR ou deploy:** (1) o dono decide se abre PR de `integ/origin-main-sync` para `main` (push de branch e PR são ações externas; o Pedro publica várias releases por dia e a base vai se mover: reintegrar logo antes); (2) cadastro novo nasce em modo procuração (`platform/signup.py:203`) e, com `NFSE_PROCURACAO_SYNC_ENABLED` desligada, esse escritório vê a tela de procurações e nada coleta: ligar a flag junto do piloto, bloquear o cadastro público até lá ou aceitar; (3) conferir com o Pedro o que ele já tem em produção que se sobrepõe (nenhuma mudança dele em `integra/`, `triage/` ou procuração foi vista).

## 1. Pedido do dono (23/11/2026)

1. O CICA está desatualizado; a baixa de NFS-e precisa ser por procuração.
2. Faltam as ferramentas do Serpro.
3. A triagem de arquivos deve ter o formato da do HubFedrizzi, melhor: aprendizado constante, mais intuitiva, checklist melhor.
4. Conversar com a sessão que melhora o copiloto e o MCP do Domínio.
5. O sistema precisa estar perfeito para venda.
6. Como o MCP e o copiloto funcionam com vários escritórios; o que mais acrescentar para facilitar a vida do contador; pesquisa a fundo para ser único e disruptivo; pesquisar as outras ferramentas que o dono já fez e ranquear as melhores para validar no CICA.

## 2. Resumo

1. **A linha local do dono nunca chegou à produção.** A produção está na release v121, saindo de `origin/main`, que tem 207 commits e 100 mil linhas que a nossa branch não tem (e vice-versa: 13+ commits dela, 366 arquivos). Procuração, cobrança, Contraprova e MCP não estão no ar. Integração feita em branch separada (seção 0). [C]
2. **NFS-e por procuração já existe, falta prova.** A faixa E1 passa nos testes com transporte falso (161 testes de procuração, contrato do legado, migração segura e isolamento passaram em 23/11, de 2.656 coletados), com a flag desligada e sem piloto real. [C]
3. **Serpro: 19 de 99.** O catálogo oficial tem 99 serviços em produção; o registro do CICA tem 19. Faltam 80: 56 de leitura, 16 de emissão de documento ou guia, 7 que declaram ou gravam e 1 de autenticação. [C]
4. **Há um pré-requisito do Serpro que o código não tem.** O CICA manda o CNPJ do escritório como autor do pedido e o da Mewstack como contratante, mas não implementa o Termo de Autorização (`autenticar_procurador_token`) que a doc exige quando autor ≠ contratante. [C no código, I sobre o efeito: provável 403]
5. **O copiloto não usa ferramentas.** É busca mais uma chamada Claude sem `tools`, com modelo fixo `claude-sonnet-5`; o MCP interno tem 8 ferramentas e o gateway externo (outra sessão, em construção) expõe 6 de leitura. Nenhuma de Serpro, NFS-e ou triagem. [C]
6. **Triagem: o CICA sempre manda para revisão e não aprende.** A do HubFedrizzi é um motor de identificação por placar com 6 laços de aprendizado, regras ensinadas, checklist e auto-aprovação com prova. No CICA, nenhum escritório real consegue cadastrar tipo de documento (só o seed da demo). [C]
7. **CNPJ alfanumérico (emitido desde jul/2026).** O validador central aceita; cerca de 15 pontos que removem "não dígito" quebram importação, XML de NFS-e, certificado e triagem. [C]
8. **Mercado.** O concorrente direto (Jettax) vende captura com A1 por cliente, auditoria, DAS diário, monitoramento de e-CAC e integração nativa com Domínio. O CICA ganha em procuração sem custódia de certificado, MCP aberto e leitura do Domínio sem RPA; perde em captura de NF-e/CT-e e cobertura de prefeituras. [C/I]
9. **O que pesa na venda.** 60% dos contadores dizem não estar preparados para a Reforma e 40% das empresas cogitam trocar de contador (Omie/SESCON-SP); 50% citam pressão por preço; 55% já fazem consultoria (Cora). [C]
10. **Ferramentas do dono.** Coleta de NFS-e foi reimplementada 7 vezes (a procuração venceu a raspagem) e RBT12/Fator R aparece em 6 projetos: são os sinais de dor mais fortes. Ranking: Radar Simples/MEI primeiro (já existe conjunto de ouro: 266 pares iguais e 24 divergentes entre PGDAS-D e Domínio), depois triagem v2, Serpro completo, conferência declarado × pago e fechamento por API; emissão de NFS-e, WhatsApp, Reforma e crédito extemporâneo ficam para depois, com gates. [C]

## 3. Estado medido (23/11/2026)

| Área | Fato | Fonte |
|---|---|---|
| Produção | Fly `cica-contabil` na **v121** (23/11), de `origin/main` `2cc9c5c8`; o `main` local parou em `aad2f5a6` (10/10). Fly: `SENTRY_ENABLED=false`, `EDGE_AGENT_MTLS_REQUIRED=false`, worker `--concurrency=1`, `DEMO_ENTRY_ENABLED=true` | `flyctl releases`, `git rev-list`, `fly.toml` |
| Testes | 2.656 coletados; `pytest -k procuracao` → 161 passaram em 81 s (inclui `test_legacy_contract`, `test_migration_safety`, `test_tenant_isolation_matrix`) | execução de 23/11 |
| Módulos oferecidos | 9: NFS-e, Guias/DCTFWeb, Integra, Conciliação, Radar da Reforma, Copiloto, Rentabilidade, Triagem, Contraprova | `hub/module_catalog.py:19-114` |
| Serpro, registro | 19 serviços; PARCSN só na modalidade ordinária | `integra/catalog.py:53-149`, `README.md:49` |
| Serpro, identidade | autor = CNPJ do escritório (`author_cnpj_for`) em 5 chamadas; contratante = Mewstack; sem Termo nem `autenticar_procurador_token` | `integra/parties.py:12`, `integra/client.py:300-306`, `hub/tasks.py:572,842,991,1158`, `hub/dte_access.py:175` |
| Serpro, prova real | homologação em chamadas reais com o contrato Mewstack ainda pendente; `INTEGRA_ENVIRONMENT` padrão `trial` | `README.md:49`, `settings/base.py:494` |
| Copiloto | `claude_fallback_payload` não envia `tools`; modelo `claude-sonnet-5` fixo (a família atual é 5.5); oculto por padrão até haver limites e consentimento | `intelligence/gateway.py:78-121`, `README.md:52` |
| MCP interno | 8 ferramentas, protocolo `2025-06-18`; escritório e papel vêm da sessão | `intelligence/mcp.py:28-125` |
| MCP externo | `mcpgateway` novo (D-333), não commitado: 6 leituras, protocolos até `2025-11-25`; a spec vigente é `2026-07-28` | `mcpgateway/endpoint.py:34-46` |
| NFS-e procuração | `NFSE_PROCURACAO_SYNC_ENABLED=False`; sem piloto; legado intocado (L1–L5) | `settings/base.py:530`, `produto-vendavel.md` E1 |
| Triagem | ver seção 7 | relatório de leitura de 23/11 |
| CNPJ alfanumérico | `normalize_cnpj` aceita `[A-Z0-9]{12}[0-9]{2}`; pontos com `\D` quebram (seção 11) | `common/cnpj.py:13-25` |
| Cobrança | `TOKEN_BILLING_ENABLED=False`; Asaas sem chave sandbox | `settings/base.py:49-55` |

## 4. Como o MCP e o copiloto funcionam com vários escritórios

**O que existe**

1. Tenant é `Organization`; pessoa é `Membership` (papel, capacidades, empresas e módulos permitidos). Todo modelo do copiloto é `OrganizationScopedModel`.
2. MCP interno: escritório e papel vêm da sessão do Hub, nunca dos argumentos; cada chamada confere permissão central fresca (`authorization_is_fresh`), capacidade por empresa e audita só o hash do resultado. [C `intelligence/mcp.py:161-321`]
3. MCP externo (outra sessão): OAuth por django-oauth-toolkit. O token prova pessoa e cliente; o escritório é escolhido no consentimento (`McpConsent`) e trocar revoga. A audiência exata `/mcp` (RFC 8707) e o emissor vêm de configuração, não do `Host`. Teto por pessoa e por escritório; só leitura; lista de ferramentas filtrada por capacidade. [C `mcpgateway/*`, em construção]
4. Domínio: cada escritório tem agente Windows próprio, só de saída (enrollment, assinatura, mTLS opcional). A consulta vira job na fila daquele agente; o Hub nunca abre porta no escritório. O MCP local `dominio-mcp` roda na máquina do escritório e é de um escritório só por construção. [C `intelligence/agent_v2.py`, `dominio-mcp-fase2.md`]
5. Serpro: contratante único (a plataforma), autor é o escritório, procuração por cliente no e-CAC.

**O que falta para valer com N escritórios**

1. **Registro único de ferramentas** usado pelo copiloto do Hub e pelo MCP externo. Cada ferramenta declara: módulo exigido, capacidade, classe de efeito (lê / ciência jurídica / emite / declara), custo em R$ e tokens, formato de retorno (JSON, XML, PDF) e se pode sair para cliente externo.
2. **Filtro por contrato**: a ferramenta só aparece se o escritório contratou o módulo e o plano permite, além do papel (`module_codes_for_membership` já existe).
3. **Orçamento Serpro por escritório e por conversa.** 200, 202 e 403 são cobrados (R$ 0,24–0,06 por consulta, 0,32–0,08 por emissão, 0,40–0,12 por declaração, faixa mensal); `/Apoiar` e `/Monitorar` não. Pré-checar a procuração (`OBTERPROCURACAO41`, cache curto) antes de gastar; usar `EVENTOSATUALIZACAO` (grátis) para decidir se vale consultar; marcar cada chamada com `X-Request-Tag` = escritório.
4. **Interruptor por escritório** "permitir clientes MCP externos" (padrão desligado) e lista de ferramentas por escritório; mascaramento e `EgressAudit` já existem para a chamada Claude do Hub.
5. **Teste de contrato "toda ferramenta × 2 escritórios"**, extensão da matriz de isolamento (V-307), incluindo o endpoint externo.
6. **Protocolo:** gateway aceita até `2025-11-25`; a spec vigente (`2026-07-28`) é sem estado e põe `Mcp-Method` e `_meta` por requisição. Avaliar compatibilidade antes do primeiro cliente real.
7. **Contrato com o Serpro:** o contrato do Integra Contador não é público; o contrato-padrão de adesão do Serpro (de outro produto) proíbe armazenar, reproduzir e repassar dados a terceiros, e o relatório da outra frente manda tratar LLM de terceiros como destinatário não autorizado até haver resposta por escrito (seção 4 dele). Até lá: nenhuma resposta do Serpro vai para LLM externo nem persiste além da sessão, salvo achados derivados. As perguntas estão prontas em [perguntas-serpro.md](../legal/perguntas-serpro.md).

## 5. Mercado

| Quem | O que vende (fonte) | Certificado do cliente | Onde o CICA ganha | Onde perde |
|---|---|---|---|---|
| Jettax | captura NF-e/NFC-e/CT-e na SEFAZ e NFS-e em +2.000 prefeituras, auditoria, DAS diário com Fator R/ST/monofásico, monitor de e-CAC e DEC-SP, ICMS com 24 etapas, SPED em lote, integra Domínio, Contmatic, SCI, Omie, Nibo, API aberta (jettax.com.br) | A1 por cliente | procuração e Serpro oficial, sem custódia de A1; MCP; Domínio por leitura direta | captura de NF-e/CT-e, prefeituras, ICMS, SPED em lote |
| SIEG Hub | XML de NF-e/NFC-e/NFS-e (+1.200 prefeituras), integra Domínio por importação de XML, sem retroativo (Domínio Atendimento); reclamações de falha de captura em 2026 (Reclame Aqui) | A1 | confiabilidade, leitura retroativa do Domínio | captura de XML |
| Qive, Acessórias, Gestta | captura de NFS-e com A1 a cada 2 h; gestão de obrigações; preço sob consulta (levantamento de 20/11) | A1 | preço transparente, procuração | gestão de obrigações madura |
| Domínio (Thomson Reuters) | TRIA (2019, assistente de eSocial/EFD-Reinf); agentes de IA da TR foram lançados nos EUA em jun/2025 (CoCounsel). Não achei anúncio de IA da Domínio para escritórios brasileiros [N] | n/a | copiloto sobre Domínio **e** Serpro **e** NFS-e, aberto por MCP | é o ERP: pode embutir |
| Basis, TaxDome, Karbon | Basis levantou US$ 100 mi (fev/2026) para agentes; TaxDome tem a organização de documentos como recurso de IA de destaque (renomeou 2 milhões de documentos na safra de 2025, dado do fornecedor); Karbon: 98% das firmas usam IA, só 21% têm política documentada (2026) | n/a | governança por escritório, aprovação, custo visível | maturidade e escala |

Sinais de demanda: 60% dos contadores não se sentem preparados para a Reforma e 40% das empresas cogitam trocar de contador (Omie); 50% citam pressão por preço e 27% pretendem revisar honorários recorrentes (Omie/SESCON-SP 1S2026); 55% participam das decisões dos clientes, 15% só operacional (Cora, 641 profissionais, jul–ago/2026); regulação: a IN RFB 2.320/2026 (art. 13) veda robôs e automação de navegador para outorgar, alterar ou revogar autorização, e a Receita pode bloquear o representante (alcance sobre leitura de dados: [I]).

**Tese:** do documento ao fechamento, sem guardar certificado de cliente, com IA que mostra a fonte, pede aprovação e mostra o custo antes.

## 6. Ferramentas do dono: inventário e ranking

Leitura de 23/11 por agente de inventário (nada executado, nenhum teste rodado; contagens de commits e testes são das pastas). Escritórios anonimizados.

| Projeto | O que faz | CICA hoje | Veredito |
|---|---|---|---|
| EmissaoNFSe (Node/TS, 77 commits, 70 testes) | bot de WhatsApp que emite e cancela NFS-e Nacional por procuração ou A1; provado em produção em 04/11 (HTTP 201); `src/simples` calcula RBT12 e alíquota efetiva em centavos | só coleta | emissão: DEPOIS (gate da norma da DPS e OK fiscal); `src/simples`: AGORA |
| RBT12 (Python, 9 arquivos) | lê PGDAS-D (CONSDECLARACAO13, CONSDECREC15, CONSEXTRATO16), extrai o PDF e gera XLSX de RBT12 e FS12 | falta | AGORA: parser e testes |
| dominio-automacao | PyAutoGUI preenche RBT12/Fator R na tela do Domínio; `output/` traz conferência PGDAS-D × Domínio de jan–ago/2026: 266 iguais, 24 divergentes | falta | RPA: descartar; a conferência vira conjunto de ouro |
| Conta200 (Django 6/Celery/HTMX, 90 commits, 1.398 testes; mesma base do CICA) | emissão de DPS (XMLDSig, mTLS, DANFSe), WhatsApp Cloud API oficial + Claude, Fator R com evidência, teto MEI, signer isolado de A1, Integra (PGDASD, PGMEI, CCMEI, DEFIS, DASN, SITFIS), eSocial/Reinf, livro-caixa e DRE; não lançado | parcial | evidência do Fator R e teto MEI: AGORA; emissão, WhatsApp, CCMEI/DEFIS/DASN: DEPOIS |
| HubFedrizzi `fechamento`, `core`, `workflow` (437 commits, ~1.560 testes) | robô de fechamento fiscal: recibo × guia, baixa no checklist por empresa, obrigação e competência; catálogo de obrigações (regime, esfera, periodicidade, feriado, IE por UF) | parcial (`fiscal_calendar`, `ActivityTemplate`, `closing_dashboard`) | DEPOIS, junto da triagem; pelo Serpro o recibo vem por API |
| HubFedrizzi `fgts`, `fap`, `det`, `admissoes`, `relatorios_folha` | portais e telas do Domínio Folha por automação, em VM interativa | falta | descartar como RPA (a spec do CICA proíbe; a IN 2.320 eleva o risco); revisitar se houver API oficial [I] |
| RetificacaoPandolfo (Django + Next, 64 testes) | ingestão de EFD e XML, crédito extemporâneo de PIS/COFINS para EFD retificadora com dupla aprovação, diagnóstico RTC, monitor normativo; 22 ideias em `documentos/OPORTUNIDADES-PRODUTO.md` | parcial (Contraprova lê EFD) | DEPOIS (D-306 deixa a retificação fora do escopo) |
| GarantiaBPO | BPO financeiro sobre Conta Azul; AutoWhats (grupos de WhatsApp viram cards por Claude, com biblioteca não oficial) | parcial | DEPOIS: só a ideia, pela Cloud API oficial |
| MewLock | cofre de A1 do cliente, agente Windows, upload cego | parcial (e-CNPJ do escritório) | DEPOIS: a procuração reduz a necessidade |
| Site_Integracao (Django 4.2, 1.129 commits) | intranet: Tax_Envel (virou Contraprova), caixa postal em lote (o CICA tem), conversores por cliente para o TXT de importação do Domínio, faturamento mensal pelas tabelas fiscais do Domínio, NCM → CST/cClassTrib, bot OpenAI × checklist de folha | parcial | descartar o código; extrair as ideias |
| RA1_XML, ROBO1_NFSE, HubCobalchini | coleta de NFS-e (3 das 7 reimplementações) | existe | descartar; ROBO1_NFSE guarda credencial de portal e resolve captcha por API paga: risco legal |
| ProgramaARD (Lucrums) | = Rentabilidade | existe | descartar |
| API_RECEITA | planilha de cerca de 1.000 escritórios do RS a partir da base de CNPJ | n/a | prospecção, fora do produto (LGPD, anti-spam) |
| qa-agent | plugin `/qa` | n/a | usar para validar o CICA |

Sem relação contábil ou vazios: ProceSync, DiBracco, FloresTintas, ProjetoRoselar, LeoDeCesaro, Spreading*, EmissaoNFSe-diag, cavalo, flet, InovaFiscal (só venv), AcompanhamentoDiario.

**Dores que se repetem** (sinal de demanda real): WhatsApp como canal (5 projetos; o CICA tem zero); RBT12/Fator R/sublimite (6); coleta de NFS-e (7 reimplementações); custódia de A1 (5); caixa postal, DTE e DET (4); cClassTrib e NCM da Reforma (4); planilha do cliente para lançamento no Domínio (3).

**Ranking para adicionar e validar no CICA** (valor para o contador × evidência × risco; esforço P/M/G):

1. **Radar Simples/MEI** (M): RBT12, alíquota efetiva, Fator R, teto MEI e sublimites com alerta em 80/90/100%. Fontes: EmissaoNFSe `src/simples`, RBT12, Conta200 (modelo de evidência), Site_Integracao `faturamento`. Fatia 1 só com a NFS-e já coletada (custo Serpro zero). Validação: os 266 pares iguais e 24 divergentes de `dominio-automacao/output` como conjunto de ouro; só aceita se o RBT12 bater ao centavo.
2. **Triagem v2 com checklist** (G): seção 7.
3. **Serpro completo e radar fiscal** (G): seção 8; é o que a Jettax chama de "Prevenção", sem A1 de cliente.
4. **Conferência declarado × apurado × pago** (M): índice do PGDAS-D (`dasPago`, `malha`) × NFS-e e Domínio × pagamentos; reaproveita o conjunto de ouro do item 1.
5. **Fechamento por API** (G): checklist de obrigações por competência com baixa por recibo vindo do Serpro (PGDAS-D 14/15, DCTFWeb 32) em vez de arquivo; é o conceito do HubFedrizzi sem a pasta do robô. Depende de 2 e 3.
6. **Copiloto com ações aprovadas e custo à vista** (G, E12): "gere o DAS dos MEI em atraso" vira cartões para aprovar.
7. **Emissão de NFS-e por procuração** (G): EmissaoNFSe e Conta200; gate da norma da assinatura da DPS e OK fiscal por escritório (hoje a prova é empírica: o 201 de 04/11).
8. **Reforma: validador de cClassTrib e NCM e diagnóstico cadastral** (M a G): RetificacaoPandolfo, Site_Integracao, Conta200, com as calculadoras oficiais da Receita; atende a dor dos 60% não preparados.
9. **Consultivo** (M): seção 10, item 3.
10. **WhatsApp do cliente** (M): decisão do dono sobre D-309; custo por conversa da Meta é gate de custo.

**Alertas de segurança (achados no caminho, nada foi aberto ou copiado):**

- `Site_Integracao/Django/apps/nfse/rotinas_automaticas.py` tem usuário e senha de banco em texto no código: rotacionar; nunca portar.
- Há `.pfx` com a senha escrita no nome do arquivo (raiz de Documentos, `HubFedrizzi`, `RBT12`): renomear, mover para cofre e rotacionar se o nome circulou.
- `MewLock-Piloto-Chaves` contém chaves privadas.

## 7. Triagem v2 (formato HubFedrizzi, melhor)

Fonte da comparação: leitura de 23/11 do HubFedrizzi canônico (`main`, `ecc19c3`, 19/11; a cópia `HubFedrizzi-triagem-ui` é branch de 13/11, 18 commits atrás, ignorada) e do `src/apps/triage` do CICA. Prefixos: F = `HubFedrizzi\apps\triagem`; C = `src\apps\triage`; H = `src\apps\hub`.

**Como a do HubFedrizzi funciona.** Entrada por IMAP (só leitura) e Graph; ZIP/RAR; guarda SHA-256, corpo do e-mail e remetente original de encaminhado; ignora logo; formato ruim vira Rejeitado e a caixa segue; ClamAV fail-closed (F\security.py:75). Leitura com pypdf, OCR se o texto tem menos de 80 caracteres, planilhas, html, csv, ofx (F\services.py:69). Pipeline (F\services.py:695): (1) empresa por placar de famílias de sinal, aceita com 100 pontos e margem de 50, duas provas duras divergentes vão a humano (F\identificacao.py:803-976); (2) tipo por palavras-chave, regra de remetente, assinaturas, histórico, senão "Diversos"; (3) período por 5 fontes; (4) IA só se o motor não fecha, com citação literal conferida pelo código, confiança ≥ 0,9, amostra 1/20 e teto em dólar; (5) auto só com motor aceito ou IA validada. "Motor 13" é `ENGINE_VERSION`: subir a versão reclassifica pendentes. Princípio do código: empresa errada é inaceitável.

**Aprendizado (6 laços).** 3 e-mails e 3 arquivos com o mesmo CNPJ aprendem o vínculo do remetente e reprocessam pendentes; conta bancária com 2 provas; confirmação do operador soma uma ocorrência à regra do remetente, que ativa com 3; regra de campo (o operador seleciona o nome da empresa no PDF, o sistema deriva âncora e sufixo e grava o apelido); correção de documento arquivado desfaz vínculo errado; IA por tipo liga após 10 revisões sem erro. Regras em 6 modos (`dois_pontos`, `linha_seguinte`, `colunas`, `ofx_conta`, `contem`, `entre`); "contém" trava se o trecho aparece em arquivado de outra empresa.

**Checklist.** Matriz empresa × tipo × competência, preenchida ao arquivar; esperado = tipo obrigatório por padrão (só "Extrato") ou exceção por empresa. Pendência mostra motivo curto e próximo passo, falhas em português. Telas: Pendências (por remetente, painel com PDF.js, irmãos, atalhos), Fluxo, Histórico, Regras, Checklist, Catálogo, Configuração.

**Como a do CICA está.** Entrada por Graph, Gmail e IMAP por escritório; upload (`intake_manual`) existe mas nenhuma view o chama. Só pdf/csv/xml/ofx/xlsx; sem zip, sem corpo do e-mail; logo e formato fora da lista ficam em quarentena para sempre; anexo > 25 MB põe a caixa em ERRO. Extração sem OCR nem IA: empresa por CNPJ único no texto ou código Domínio no nome; tipo por palavra do código ou rótulo; período por regex; **sempre** `aguardando_revisao`, sem confiança, sem auto e **sem aprendizado** (C\services.py:315 só grava evento). `DocumentType` não tem palavras-chave nem "esperado" e nenhuma tela ou comando o cria (só `seed_demo`): escritório real não aprova nada. Checklist é gravado ao arquivar e ninguém o lê. UI: lista de 20 por página, detalhe com 5 campos, aprovar → arquivar em 2 cliques; sem atalho, lote nem agrupamento.

| Recurso | HubFedrizzi | CICA | Lacuna |
|---|---|---|---|
| Entrada | IMAP/Graph, zip/rar | Graph/Gmail/IMAP por escritório | upload, zip, ingestão robusta |
| Leitura, tipo, período | PDF+OCR, palavras-chave, assinaturas | PDF 3 páginas, rótulo, regex | OCR, catálogo, heurísticas |
| Empresa | placar de ~12 sinais | CNPJ + código | motor inteiro |
| Regras e aprendizado | 6 modos, 6 laços | nenhum | tudo |
| IA e auto-aprovação | sim, com prova | nunca | opt-in com limiar |
| Checklist | tela, só Extrato padrão | dados sem tela | tela, perfil, prazo |
| Operador | lado a lado, atalhos | lista e detalhe | UX |
| Dedupe, multi-tenant, destino | fraco; não; pasta direta | forte; sim; biblioteca ou agente com hash | **o CICA ganha** |

**Ordem de portabilidade (valor ÷ esforço).**

1. Catálogo de tipos por escritório com palavras-chave e "esperado": F\catalogo.py:34 → C\models.py:108 + migração + tela. Sem isso nada fecha.
2. Ingestão: corpo, remetente original, ignorar logo, rejeitar anexo estranho sem travar a caixa, upload manual por view, zip seguro: F\microsoft.py:165, F\imap.py:86 → C\ingest.py, C\imap_poll.py:112, C\graph_poll.py:224, C\gmail_poll.py.
3. Leitura, OCR (fila Celery própria), tipo, período, banco, assinaturas: F\services.py:69-454, F\assinaturas.py → C\extraction.py:74,134.
4. Motor de empresa por placar: F\identificacao.py → `C\identification.py` novo; `Empresa` → `ClientCompany` (`cnpj_masked`, `dominio_code`, `contact_email`); **CNPJ alfanumérico**.
5. Aprendizado por escritório: SenderCompany, SenderRule, ExtractionRule, `account_key`, `engine_version` (F\services.py:797-989, F\regras.py) → `C\learning.py`; com `clean()`, nunca vínculo entre escritórios.
6. Auto-aprovação opt-in por escritório (padrão "revisar tudo"): `auto_approve` em C\services.py:433 (EXTRACTING → READY já é permitido).
7. UI: Pendências por remetente, painel lateral com leitor de PDF, atalhos, lote, explicação "por quê", em views novas (H\views.py tem 12 mil linhas: módulo novo) e `hub/templates/hub/triage_*.html`.
8. Depois: regras ensinadas (regra de campo), tela de checklist, IA opt-in, backtest (`triagem_backtest`).

**Só da Fedrizzi — generalizar ou cortar:** `TRIAGE_WINDOWS_ROOT`, homologação, `ClientFolderIndex`, `{pasta_cliente}`, árvore CONTABIL/EXTRATOS, `automacao.arquivo_clientes`, `ControleAcervo` (→ `DestinationProfile` + `AgentFileJob`), `CODIGO_MODELO_MINIMO=9000`, sócios `bethadba`, host fixo de NFS-e (`F\nfse_link.py:18`, risco de SSRF), `TriageConfig` singleton, IMAP CIPNET, variáveis `TRIAGE_*`/`ANTHROPIC` globais.

**Além da Fedrizzi (hipóteses [I]).**

- Checklist por regime tributário (`ClientCompany.tax_regime`), vencimento, % de completude, "falta há N dias" e rascunho de pedido ao cliente por e-mail.
- Confiança persistida: hoje F\services.py:688 descarta os pontos do placar; guardar, e calibrar limiar por tipo × fonte com backtest; 100% de revisão nos primeiros N documentos de um escritório.
- Aprendizado ativo: fila ordenada por menor margem; sugerir regra na segunda confirmação igual; `ExtractionRule.errors` nunca incrementa hoje (F\models.py:301): desligar regra que erra.
- Dedupe semântico: alerta de empresa + tipo + competência + conta já arquivados (OFX × PDF).
- Referência de padrão (só estrutura): Paperless-ngx (GPL-3.0) treina o classificador só com documentos revisados, fora da caixa de entrada, e reaprende quando algo muda; descarta previsão abaixo do limiar. Docspell (AGPL) reaprende etiquetas em agenda. TaxDome destaca a organização automática de documentos como seu recurso de IA central.
- Custo de OCR e de IA é decisão do dono; o plano da triagem veda IA externa sem decisão (`docs/plano-triagem-documental.md:246`).

## 8. Serpro completo

**Catálogo oficial de 15/10/2026 (baixado em 23/11):** 119 serviços, 99 em produção, 6 em construção, 13 em prospecção, 1 cancelado. Os 99 de produção são 61 Consultar, 23 Emitir, 6 Declarar, 5 Monitorar e 4 Apoiar. O CICA registra 19.

| Bloco | Serviços que faltam | Qtd | Classe | Onde entra |
|---|---|---|---|---|
| Leitura | PGDASD 13, 14, 15, 16 (índice com `dasPago` e `malha`; PDFs); EVENTOS 131–134; PAGTOWEB 71, 73; MIT 315, 316, 317; DEFIS 142–144; REGIMEAPURACAO 102–104; CCMEI 122, 123; SICALC 52, 54; 7 modalidades de parcelamento × 4 consultas (PARCSN-ESP, PERTSN, RELPSN, PARCMEI, PARCMEI-ESP, PERTMEI, RELPMEI); PNRCONTADOR 261, 263, 265; EPROCESSO 271 | 56 | A | copiloto, MCP externo, Hub |
| Emissão de documento ou guia | PGDASD 17, 18, 19; PGMEI 22; DCTFWEB 313; SICALC 51, 53; GERARDAS das 7 modalidades; CCMEI 121; PAGTOWEB 72; PNR 264 | 16 | C/D | só Hub, com aprovação humana e custo visível |
| Declara ou grava | PGDASD 11; DEFIS 141; DCTFWEB 310; MIT 314; REGIMEAPURACAO 101; PNR 262; PGMEI 23 | 7 | E/F | fora da v2 (efeito legal); só com pedido explícito do dono |
| Autenticação | AUTENTICAPROCURADOR 81 | 1 | G | infraestrutura (Termo) |

Também fora do Integra: Consulta CNPJ, CND, Dívida Ativa e NF-e por chave são APIs separadas, cobradas por faixa (relatório do Serpro, seção 2).

**Regras já pesquisadas e adotadas** ([relatório do Serpro](../pesquisa/serpro-integra-contador-mcp.md)): allowlist por `idServico`, não por tipo (`MSGDETALHAMENTO62` é "Consultar" mas registra ciência da intimação; `PGMEI/ATUBENEFICIO23` é "Emitir" e grava); PDF em PGDAS-D, extrato, DEFIS, SITFIS e DCTFWeb completa, JSON só no índice, pagamentos, MIT, parcelamentos e procurações; `EVENTOSATUALIZACAO` (E0301 DCTFWeb, E0601 Caixa Postal, E0701 Pagamentos; lote de 1.000 CNPJs, 1.000 requisições por dia por PF e por PJ) avisa mudança sem custo.

**Tarefas (E10).**

- **T10.1** Registro dirigido por tabela: os 99 serviços com `effect_class`, `response_format`, `billable`, `copilot_allowed`, `needs_confirmation`, `versao`; teste que reprova serviço fora do catálogo e que soma 99; script que compara o registro com a página oficial e acusa serviço novo (por exemplo `QTQMSG64`, `ANEXOSMSG65`, `URLANEXOMSG66`, previstos para 31/10/2026 e ausentes em 23/11).
- **T10.2** Construtores de requisição e leitores de resposta tipados para os 56 de leitura, com fixtures gravadas do trial; as 7 modalidades de parcelamento geradas da mesma tabela do PARCSN.
- **T10.3** Identidade Serpro por escritório: (a) cada escritório contrata com o próprio e-CNPJ, ou (b) a plataforma contrata e o escritório assina o Termo (XMLDSig com o `OfficeCertificate` de E1, `AUTENTICAPROCURADOR/ENVIOXMLASSINADO81`, token válido até a meia-noite seguinte, cabeçalho `autenticar_procurador_token`). Padrão recomendado: (a) no piloto, como na pesquisa da outra frente; (b) depois das respostas do Serpro.
- **T10.4** Governador de custo: `UsageEvent` com custo efetivo e `X-Request-Tag`, teto mensal por escritório, orçamento por conversa, pré-checagem de procuração com cache, evento gratuito antes de consulta paga, nunca em laço de modelo.
- **T10.5** Radar fiscal da carteira: `EVENTOSATUALIZACAO` em lote (1.000 CNPJs por requisição) complementa ou substitui o `INNOVAMSG63` por empresa, conforme o volume; agregador de situação (SITFIS, DTE, parcelamentos, pagamentos, "declarou? DAS pago? em malha?" pelo índice do PGDAS-D) com tela única "o que fazer hoje".
- **T10.6** Telas do Hub para o que já tem fluxo humano: demais modalidades de parcelamento, MIT, PGDAS-D (extrato e declarações), DEFIS, CCMEI, SICALC, comprovante de pagamento; emissão sempre com cotação, confirmação e PDF persistido (padrão do PARCSN atual).

Critérios: nenhuma chamada paga sem confirmação com valor (regra de custo); transporte falso conta chamadas cobráveis e reprova 403 evitável; matriz de isolamento cobre as ferramentas novas; `legacy_snapshot --compare` idêntico (L4).

## 9. NFS-e por procuração: fechar o ciclo (E1b)

Leitura de 23/11 por agente (nenhuma chamada ao ADN real; nada executado). Siglas: PN = `HubFedrizzi/apps/nfse/portal_nacional.py`; DOC = `HubFedrizzi/docs/portal-nacional-nfse.md`; arquivos sem prefixo ficam em `src/apps/hub/`.

**Prática provada.** A sonda é a própria consulta com `cnpjConsulta` (PN:865); 200 e 404 com E2220 ou `NENHUM_DOCUMENTO_LOCALIZADO` são ok; 400 E2245 (e o E2243 antigo) grava "ausente" e repergunta em 6 h com o texto bruto do ADN; mesma raiz é isenta. 429 lê `Retry-After` (até 120 s), pausa a fila toda, soma 1 s por 429 (teto 6 s) e normaliza em 300 s; 5xx e rede com recuo; 495 põe o e-CNPJ 15 min em quarentena; piso global de 1 req/s. Cadência por empresa 1 h, 6 h, 24 h; empresa reivindicada por UPDATE condicional. Laço por NSU com checkpoint por lote, até 200 lotes por rodada; o NSU é do CNPJ, não do certificado (DOC:43). Upsert por `{cnpj, chave}`; evento guardado e reaplicado se chegar antes da nota; 101101, 105104 e 305101 cancelam, 105102 substitui, 101103 não cancela. EmissaoNFSe leu 403 clientes e 58.697 documentos por procuração.

**Faixa do CICA.** `ProcuracaoAdnClient` (`nfse_procuracao.py:147`) trata 200, 404 E2220/E2230, E2245 (6 h), 495 (15 min), E2210–E2213 (60 min), 429 (pausa de 60 s), 5xx com recuo dobrado até 6 h; lease por e-CNPJ, 2 páginas por fatia, beat de 2 min; ingestão por `process_sync_pages` (checkpoint transacional, índices únicos de NSU e hash, XML cifrado e imutável).

**Lacunas, por risco** (leitura; reproduzir cada uma por teste vermelho antes de corrigir).

| # | Risco | Lacuna | Onde |
|---|---|---|---|
| 1 | perder nota | cancelamento por 101103; 105104 e 305101 ignorados. Corrigir muda dado derivado dos legados: decisão do dono | `nfse_facts.py:39,146` |
| 2 | perder nota | e-CNPJ vencido: a fila para calada, as linhas seguem "Em dia" e o aviso acaba 1 dia antes | `nfse_procuracao.py:305`, `procuracao_alerts.py:117` |
| 3 | perder nota | `ERROR` não volta sozinho (401/403, 400 sem código, E2243, NSU/hash divergente); trocar o e-CNPJ não reativa | `nfse_procuracao.py:431,481`, `office_certificate.py:115` |
| 4 | perder nota | 404 só vale com E2220/E2230; E2240/E2241 viram repetição eterna e o alarme é só log, com Sentry desligado | `nfse_procuracao.py:203`, `procuracao_alerts.py:133` |
| 5 | bloquear certificado | 401/403 não põem em quarentena: a cadeia testa a carteira inteira a 1/s com certificado recusado | `nfse_procuracao.py:207,583` |
| 6 | bloquear certificado | 429 ignora `Retry-After`; o piso de 1 s vale por instância e `last_call_at` nunca é lido; sem disjuntor para 5xx | `nfse_procuracao.py:213,602` |
| 7 | bloquear certificado | HubFedrizzi e CICA no mesmo e-CNPJ somam 2 req/s; o limite é por certificado | DOC:225 |
| 8 | duplicar | `NfseSync` é único por (org, empresa); virar o modo de uma linha legada mantém `certificate` e o legado a seleciona: duas faixas na mesma linha e corrida de checkpoint | `models.py:477`, `tasks.py:108` |
| 9 | duplicar [I] | `_enqueue` usa `.update()` e `updated_at` é `auto_now`; `recover` trata QUEUED com mais de 5 min como abandonado e reenfileira a cada 2 min com o worker ocupado | `tasks_procuracao.py:43,396` |
| 10 | custo | fila única e worker de 512 MB: a cadeia espera atrás da fila A1; segundo worker +R$ 36,32/mês só com OK | `settings/base.py:591` |
| 11 | onboarding | "Pedir a todos" inclui "A verificar" e mandaria e-mail a quem já tem procuração; o e-mail usa o CNPJ do perfil, não o do e-CNPJ (pode ser filial) | `views_procuracao.py:146`, `procuracao_requests.py:78` |

Vazamento entre escritórios: nada achado nas rotas lidas (`views_procuracao.py:130,350`, `procuracao_requests.py:91`); roster e matriz de isolamento não verificados por este agente (a matriz passou nos testes de 23/11).

**Armadilhas que a spec ignorava.** 101103 e 203202 não cancelam; cerca de 32% dos documentos lidos pela EmissaoNFSe não são nota própria. E2243: o HubFedrizzi trata como falta de procuração, o CICA como erro fatal; gravar código e texto brutos. CNPJ alfanumérico: `nfse_sync.py:119` tira as letras [I]. Cancelar por procuração com e-CNPJ dá E0812/E0813 e exige e-CPF (memória EmissaoNFSe de 04/11), vale para a emissão (E16).

**Roteiro do piloto (escritório do HubFedrizzi, 25 a 40 empresas).**

- *Pré-condições:* árvore commitada (E0b), suíte e `makemigrations --check` verdes, `product_readiness --strict` e `legacy_snapshot` "antes"; capacidade decidida com OK do dono; valor de `NFSE_ADN_ENVIRONMENT` em produção conferido (o legado o compartilha: se hoje for `trial`, ligar a flag muda o legado); organização nova em modo `procuracao` com `OfficeProfile.cnpj` igual ao CNPJ exato do e-CNPJ; o dono sobe o e-CNPJ pela tela, nenhum agente vê arquivo ou senha; janela combinada com o HubFedrizzi, que usa o mesmo certificado; amostra de 10 empresas com procuração, 3 sem, 1 de mesma raiz e 2 com cancelamento.
- *Passos:* (1) deploy com a flag desligada e `legacy_snapshot --compare` igual a 0; (2) importar a carteira e clicar "Verificar", nunca "Pedir a todos" antes da sonda; (3) ligar a flag fora do ciclo da fila A1; (4) ler estado, `query_type` e códigos por 3 ciclos; (5) pedir procuração a 2 ou 3 clientes reais; (6) conferir paridade com o HubFedrizzi por empresa, com contagem e hash do conjunto de chaves, sem imprimir CNPJ; (7) operar 72 h e depois 7 dias.
- *Sucesso:* procuração conhecida chega a "Em dia" com `Procuracao` em até 2 sondas; 0 chave faltando contra o HubFedrizzi e 0 divergência de situação; 0 violação de índice ou NSU; 429 no máximo 1 por dia, 495 igual a 0, nenhuma chamada com menos de 1 s de intervalo; `oldest_minutes` abaixo de 120; ciclo do legado sem piora acima de 10%; `legacy_snapshot --compare` igual a 0; todo erro com código registrado.
- *Registrar:* por empresa (índice, sem CNPJ): estado, códigos, `TipoConsulta`, NSU e páginas; HTTP por código e hora, duração por chamada, RSS e CPU do worker, conexões no Neon, atraso da fila; tempo do pedido ao "Em dia" e ações manuais.
- *Rollback:* `NFSE_PROCURACAO_SYNC_ENABLED=false` torna as tarefas no-op; revogar o e-CNPJ na tela; dados são imutáveis e ficam; a migração 0078 é aditiva. Desligar na hora se aparecer 429, 495 ou 401 em sequência.

**Clientes legados (Fly e on-prem).** Não mudar linha existente (lacuna 8). Criar uma organização irmã em modo `procuracao` por legado (`store_office_certificate` já recusa organização legada, `office_certificate.py:57`), carregar a mesma carteira por planilha e pedir procuração em lotes de 80; nada é escrito no legado; o armazenamento no Neon dobra: medir e pedir OK. Provar antes de cortar: por empresa, mesmo NSU com o mesmo `document_hash`, mesmo conjunto de chaves e 14 dias de incremento sem diferença (que o NSU é do CNPJ só consta em DOC:43 e não está provado no CICA). Cortar por empresa, com OK e perto do vencimento do A1, com migração aditiva que guarda `certificate` em coluna nova, copia `checkpoint_nsu` e desliga a faixa legada no mesmo ato, de forma reversível. Antes, corrigir as lacunas 1 e 3. Arquitetura do on-prem: não verificado.

**Tarefas (E1b).** T1b.1 corrigir as lacunas 2 a 7, 9 e 11, cada uma por teste vermelho antes (lacunas 1 e 8 só com decisão do dono); T1b.2 conferir `NFSE_ADN_ENVIRONMENT` e capacidade; T1b.3 executar o roteiro com o dono. O código da faixa é do épico E1 (L3 não se aplica: é módulo novo).

## 10. Ideias novas com evidência (fora das ferramentas do dono)

1. **Ferramentas públicas no copiloto, sem custo:** situação e cadastro de CNPJ (BrasilAPI), opção Simples/MEI, CNAE, municípios do IBGE, indicadores do Banco Central (SELIC e IPCA para reajuste), validação offline de chave de NF-e, CPF e CNPJ. Padrão: `mcp-fiscal-brasil` (MIT, cerca de 44 ferramentas). Esforço P; não passa por Serpro nem por procuração.
2. **Comunicação com o cliente:** o uso de IA mais comum entre contadores é comunicação (Karbon). Rascunho de e-mail que explica guia, vencimento, mudança da Reforma e impacto, sempre aprovado por humano e enviado pelo e-mail que já existe. Atende o dado da Omie de que mandar só a guia, sem explicar o impacto, leva o cliente a procurar outro profissional. Esforço P a M; não exige portal nem WhatsApp (D-309).
3. **Painel consultivo:** Rentabilidade + sugestão de reajuste de honorários (34% veem a Reforma como chance de reajustar consultoria; 27% vão revisar os recorrentes, Omie/SESCON-SP) + impacto da Reforma por cliente. Depende de Q-41/42/43 (fonte de honorário).
4. **Captura de NF-e e CT-e:** é o núcleo de Jettax e SIEG. Caminho sem custódia de A1: o emissor coloca o CNPJ do escritório no `autXML` e o escritório consulta a distribuição DF-e com o próprio e-CNPJ, depois da ciência da emissão (relatório do Serpro, seção 2; fórum fiscal.io, [I]). Sem `autXML` só com certificado do cliente. Alternativa: ingerir o XML que SIEG, Qive ou Jettax já capturaram, pela triagem. Decisão do dono.
5. **Governança de IA como produto:** só 21% das firmas têm política de IA documentada (Karbon). Entregar por escritório uma política pronta (o que a IA vê, quem aprova, registro de saída, retenção) como argumento de venda; a base existe (`EgressAudit`, consentimento, cotas).
6. **Confiabilidade visível:** página de status e relatório mensal de coleta ("N notas, M empresas, 0 falhas"), porque a queixa recorrente do SIEG é falha de captura (Reclame Aqui). Padrão: uptime-kuma.

## 11. Dureza para venda (E13)

**CNPJ alfanumérico.** A Receita começou a emitir em jul/2026 (IN RFB 2.229/2024; raiz e ordem aceitam letras, os dois dígitos verificadores seguem numéricos; módulo 11 com valor ASCII − 48; o Serpro publicou rotinas em Java, Python e TypeScript). `common/cnpj.py:13-25` e `integra/envelope.py:34` já aceitam; os pontos abaixo removem tudo que não é dígito ou exigem 14 dígitos:

- importação de empresas: `hub/imports.py:293,300,379,796,806`;
- XML de NFS-e e certificado: `hub/nfse_facts.py:89,191`, `hub/nfse_sync.py:83-87,119,333`, `hub/services.py:438-449`, `hub/nfse_adn.py:102-104` (`AdnClient.fetch_page`, **legado congelado, L3**: cliente com CNPJ alfanumérico recebe "CNPJ válido" recusado; a faixa de procuração já sobrescreve com `normalize_cnpj` em `nfse_procuracao.py:177-180`, então só o legado fica de fora e precisa de decisão do dono);
- busca e listas: `hub/search.py:36`, `hub/nfse_list.py:226`, `hub/views.py:5694`;
- triagem: `triage/extraction.py:114-116`;
- copiloto e plataforma: `intelligence/connectors.py:140`, `platform/models.py:84`;
- Rentabilidade: `profitability/normalize.py:80-82` recusa letras de propósito; ajustar só com o contrato de vetores.

Critério: um fixture com CNPJ alfanumérico passa por cadastro, importação por planilha, XML de NFS-e, extração da triagem, busca e tela, sem tocar no legado sem o OK do dono.

**Outros itens de venda já mapeados** (E4–E6, E9 em `produto-vendavel-plano.md`): `PLATFORM_DEVELOPER_FULL_ACCESS` fora do produto, Sentry ligado (`SENTRY_ENABLED=false` no Fly), prova de restauração, MFA em degrau, exclusão de escritório (Q-49), SMTP, Turnstile, Asaas sandbox, grade de preços, revisão jurídica de termos e DPA, `EDGE_AGENT_MTLS_REQUIRED=false` no Fly.

## 12. Plano por épicos (proposta)

| Épico | Conteúdo | Depende de | Paralelo com |
|---|---|---|---|
| **E0c** | **integrar com `origin/main`** (produção v121): branch `integ/origin-main-sync`, conflitos resolvidos, migração de junção, verificação completa; reintegrar logo antes do PR porque a base se move | OK do dono para push da branch e PR; combinar com o Pedro | nada: pré-requisito do PR |
| **E0b** | **entregar o que já está pronto** (E0–E8): separar a árvore em commits por épico só com arquivos desta frente, suíte inteira e PostgreSQL, PR para `main`, `legacy_snapshot` antes e depois, deploy canário | OK do dono para commitar e para fazer deploy (dois gates) | nada: é pré-requisito dos worktrees |
| **E1b** | piloto real da NFS-e por procuração e ligar a flag | E0b; e-CNPJ e cliente reais (gate) | tudo |
| **E13a** | varredura do CNPJ alfanumérico | decisão sobre `nfse_adn.py:102` | curta, antes dos demais |
| **E10** | Serpro completo (T10.1–T10.6) | T10.3 depende da resposta do Serpro | E11 |
| **E11** | Triagem v2 e checklist (itens 1–8 da seção 7) | decisão de OCR e IA | E10 |
| **E12** | ferramentas no copiloto e no MCP, com a outra sessão | registro único de ferramentas | E10, E11 |
| **E14** | Radar Simples/MEI e conferência declarado × apurado × pago (E7.1 do plano de 20/11; ranking 1 e 4) | NFS-e já coletada; conjunto de ouro do `dominio-automacao`; índice do PGDAS-D vem de E10 | E10, E11 |
| **E15** | fechamento por API: checklist de obrigações com baixa por recibo do Serpro (ranking 5) | E10 e E11 | depois |
| **E16** | só com gate: emissão de NFS-e, Reforma (cClassTrib/NCM), WhatsApp, crédito extemporâneo, cofre de A1 (ranking 6 a 10) | decisões do dono | depois |

**Por que E0b vem primeiro.** Em 23/11 a árvore tem 28 arquivos modificados e 67 novos, misturando duas frentes: esta (E0–E8: `hub/0078_nfse_procuracao.py`, `platform/0034` e `0035`, 27 arquivos de teste, módulos de procuração, cobrança, exportação, `scripts/quality_gate.py`) e a do MCP (`src/apps/mcpgateway/`, `tests/test_mcp_gateway_oauth.py`, `pyproject.toml`, `requirements.txt`, `uv.lock`, `src/config/urls.py`, `docs/specs/dominio-mcp-fase2.md`). `src/config/settings/base.py`, `DECISOES.md`, `VALIDACOES.md`, `docs/README.md` e `registro-de-execucao.md` têm texto das duas. Um worktree novo nasce do commit de `HEAD`: sem E0b ele não teria a faixa de procuração nem a migração `0078`, e as migrações de dois worktrees colidiriam. Também é o que resolve "o CICA está desatualizado": nada de E0–E8 está no ar. Os commits levam só os blocos desta frente (índice montado por patch filtrado, como a outra frente já fez); o que é da outra sessão fica com ela.

**Fases.** A (agora): E0b, depois E13a, preparo do piloto E1b, E10 (T10.1–T10.2) e E11 (itens 1–3) em dois worktrees, E14 fatia 1. B: E10 (T10.3–T10.6), E11 (itens 4–8), E12. C: E15 e E16. No máximo 2 frentes de implementação ao mesmo tempo (regra de cota).

**Estado E14 (23/11/2026).** Fatia 1 pronta na `integ/origin-main-sync`, tudo atrás de `SIMPLES_RADAR_ENABLED` (desligada): `hub/simples_radar.py` (receita de serviço por NFS-e ativa contra o teto, 80/90/100% sobre a razão exata, teto proporcional do MEI na abertura, Fator R só com 12 meses de folha), tela `app/nfse/teto/` com aba, planilha e filtro, e aviso diário para dono e administrador (`hub.notify_simples_radar`, 07:40). Limites em tabela com fonte e `confirmed=False`: conferir no portal oficial antes de ligar. O aviso usa a chave `simples_ceiling` fora do enum `Notification.Kind` porque o enum novo exige migração `AlterField`, barrada pela guarda L1; rótulo bonito depende de OK do dono. Falta: RBT12 oficial (PGDAS-D, E10) e declarado × apurado × pago.

Divisão com a outra sessão: ela fica com `dominio-mcp/`, OAuth, `mcpgateway/`, relay, `intelligence/mcp.py` e `gateway.py`; esta frente fica com `integra/`, `triage/`, NFS-e por procuração e módulos novos, entregando as ferramentas como funções que o registro dela consome. **[N] A outra sessão ainda não respondeu à proposta.** Para não colidir no mesmo checkout, cada épico implementado vai para worktree próprio e views novas vão para módulos novos (`hub/views.py` tem mais de 12 mil linhas).

### Critérios de aceitação (nível de título; detalhar ao iniciar cada épico)

Valem para todos: migração só adiciona (L1), comportamento novo atrás de flag desligada por padrão e de modo por escritório (L2), código legado intocado (L3), `legacy_snapshot --compare` idêntico antes e depois (L4), nada que consuma o worker dos escritórios atuais sem custo confirmado (L5), suíte inteira verde, `ruff` e `mypy` nos arquivos novos, texto de tela sem frase explicativa, 375 px sem rolagem horizontal, contraste AA.

- **AC-0b** Um commit por épico, nenhum arquivo da outra frente incluído, `git diff main` revisável por épico; suíte inteira verde (e `--ds=config.settings.test_postgresql` quando houver PostgreSQL local), `makemigrations --check` limpo, numeração de migrações sem colisão com a outra frente, `legacy_snapshot --compare` idêntico antes e depois do deploy; deploy canário só depois do diff aprovado.
- **AC-1b** Piloto com um e-CNPJ real e pelo menos 3 clientes reais com procuração: um ciclo de coleta sem erro, contagem de notas por empresa e competência confere por amostra com o portal, alarmes de procuração e de e-CNPJ a vencer disparam em teste, desligar a flag devolve o estado anterior.
- **AC-13a** Fixture com CNPJ alfanumérico passa por cadastro, importação por planilha, XML de NFS-e, extração da triagem, busca e telas; o CNPJ numérico segue idêntico em todos os testes de caracterização.
- **AC-10** Seção 8: registro com 99 serviços e teste de soma; fixtures do trial para os 56 de leitura; Termo de Autorização com teste de assinatura e de reaproveitamento até a meia-noite; transporte falso conta chamadas cobráveis e reprova 403 evitável; teto por escritório e por conversa.
- **AC-11.1** Escritório novo cria, edita e desativa tipos de documento (nome, código, palavras-chave, pasta de destino, esperado por regime) pela tela; seed contábil padrão é opt-in.
- **AC-11.2** E-mail com logo ou assinatura não trava a caixa; anexo fora do limite vira Rejeitado com motivo e a caixa segue; corpo e remetente original de encaminhado ficam gravados; upload manual chega ao mesmo pipeline e arquiva; ZIP com limites de arquivos, tamanho e profundidade; ZIP bomba recusado.
- **AC-11.3** PDF com menos de 80 caracteres de texto passa por OCR em fila própria, atrás de flag e orçamento; planilha, html, csv, ofx e txt lidos sem executar conteúdo.
- **AC-11.4** Empresa por placar com limiar e margem; duas provas duras divergentes vão para revisão; CNPJ alfanumérico reconhecido; **teste de isolamento do aprendizado**: nada aprendido num escritório muda a decisão em outro.
- **AC-11.5** Confirmação soma à regra do remetente e ativa com 3; correção de arquivado desfaz vínculo errado; `engine_version` por escritório reclassifica pendentes ao subir; backtest sobre conjunto rotulado imprime acurácia e cobertura.
- **AC-11.6** Auto-aprovação opt-in por escritório (padrão revisar tudo), só com motor aceito, com amostra de auditoria e registro do porquê; IA externa só com decisão do dono.
- **AC-11.7** Tela de checklist empresa × tipo × competência com esperado por regime ou empresa, prazo, % de completude, "falta há N dias" e rascunho de pedido ao cliente (o humano envia).
- **AC-11.8** Pendências agrupadas por remetente, painel com leitor de PDF, atalhos de teclado (aprovar, rejeitar, próximo), ação em lote, "por quê" com a evidência; todo estado desenhado (vazio, carregando, erro, sem resultado com saída).
- **AC-11.9** Escopo escritório + empresa em toda view nova; a matriz de isolamento cobre as telas novas.
- **AC-12** Toda ferramenta nova passa pelo teste "× 2 escritórios"; ferramenta com efeito exige confirmação humana; custo aparece antes da chamada; interruptor por escritório para cliente MCP externo, desligado por padrão.
- **AC-14** RBT12 por empresa bate ao centavo com o conjunto de ouro (266 pares iguais; os 24 divergentes explicados); alerta em 80/90/100% do teto; Fator R com evidência (folha de 12 meses ÷ RBT12).

## 13. Gates do dono e perguntas ao Serpro

0. OK para commitar E0–E8 por épico (só arquivos desta frente) e, depois do diff aprovado, para fazer deploy canário no Fly. Sem isso nada do que foi feito chega à produção.
1. Enviar ao Serpro as 8 perguntas de [perguntas-serpro.md](../legal/perguntas-serpro.md) (armazenar, TTL de cache, repassar a LLM, software house com vários escritórios, Termo, limites, cobrança de Apoiar/Monitorar, faixa e entidade representativa). Bloqueia T10.3 e qualquer envio de dado do Serpro a LLM.
2. e-CNPJ e cliente reais para o piloto de procuração; OK por escritório para ligar a flag.
3. Custos com valor: OCR e worker de triagem; segundo worker (+R$ 36,32/mês, `capacidade-procuracao.md`); chamadas reais de homologação do Serpro (R$ 0,24 a R$ 0,40 cada, faixa 1).
4. Migrar os clientes legados para procuração? (spec de 20/11 diz que não até haver prova)
5. IA na triagem: permitir, com que teto?
6. Quem contrata o Serpro: (a) cada escritório ou (b) a plataforma com Termo.
7. Declarar e gravar no Serpro (7 serviços): fora da v2?
8. Reabrir D-309 (portal do cliente e WhatsApp fora) e D-308 (só Domínio)? A pesquisa mostra comunicação como principal uso de IA entre contadores (Karbon); nenhuma decisão é tomada aqui.
9. `hub/nfse_adn.py:102` (L3) entra na varredura do CNPJ alfanumérico?

## 14. Fontes (acessadas em 23/11/2026)

- Serpro, catálogo: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/catalogo_de_servicos/ ; eventos: .../solucoes/integra-contador-gerenciador/eventosatualizacao/ e `/mapa_dos_eventos/`; relatório interno `docs/pesquisa/serpro-integra-contador-mcp.md` (20/11).
- MCP, autorização (2026-07-28): https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization
- Paperless-ngx (classificador, caixa de entrada): https://github.com/paperless-ngx/paperless-ngx (via DeepWiki).
- mcp-fiscal-brasil (MIT, ~44 ferramentas públicas: CNPJ, Simples/MEI, CNAE, IBGE, BCB): https://github.com/DeHor-Labs/mcp-fiscal-brasil
- Jettax: https://www.jettax.com.br/ · SIEG: https://www.contabeis.com.br/noticias/53959/sieg-hub-a-ferramenta-mais-poderosa-para-gestao-de-documentos-fiscais/ · Domínio e SIEG: https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=7539
- Thomson Reuters, IA agêntica (2/6/2025): https://www.thomsonreuters.com.br/pt/sala-de-imprensa/tr-lancamento-inteligencia-agentica.html
- Omie/SESCON-SP: https://www.omie.com.br/blog/pesquisa-contadores-nao-preparados-reforma-tributaria/ e https://www.omie.com.br/blog/sondagem-reforma-tributaria-custos-contabilidade/ · Cora, Radar Contábil: https://www.cora.com.br/blog/radar-contabil/ · Karbon 2026: https://karbonhq.com/resources/state-of-ai-accounting-2026/ · TaxDome: https://taxdome.com/blog/top-ai-tools-for-accountants
- CNPJ alfanumérico: https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf · https://serpro.gov.br/menu/noticias/noticias-2024/cnpj-alfanumerico
- Basis.ai (rodada de US$ 100 mi, fev/2026, segundo CPA Trendlines): https://cpatrendlines.com/?p=154482
- Autorização de XML de NF-e por contador (autXML), com ressalvas de fóruns: https://conteudo.fiscal.io/blog/como-baixar-nfe-e-cte-certificado-contabilidade-procuracao-eletronica

## 15. Auditoria do produto completo (23/11/2026)

Inventário da linha integrada (`integ/origin-main-sync`): 160 templates, 148 rotas do `hub`, 25 automações agendadas (Celery beat), 14 módulos de app. Leitura de código e testes; nenhuma tela foi aberta no navegador e nenhuma chamada real foi feita nesta rodada. [C]

**Jornadas do contador e onde estão**

| Jornada | Hoje | Lacuna para ser disruptivo | Épico |
|---|---|---|---|
| Entrada de documento | Triagem (3 caixas, quarentena, revisão) | motor com aprendizado, checklist, lote, atalhos | E11 (feito 1–3; 4–8 em andamento) |
| Coleta de NFS-e | A1 por empresa (produção) e procuração (opcional, flag) | piloto real, 3 lacunas corrigidas, falta ritmo 429 e pedido a quem já tem | E1b |
| Obrigações e guias | Guias, DCTFWeb, PARCSN, DTE | 80 serviços do Serpro, radar por evento, "o que fazer hoje" | E10 |
| Conferência | Conciliação OFX × Domínio, DE-PARA com IA (produção), Contraprova | declarado × apurado × pago, Radar Simples/MEI | E14 |
| Fechamento | calendário e dashboard | checklist com baixa por recibo do Serpro | E15 |
| Copiloto | busca + 1 chamada Claude, MCP interno e externo (6 leituras) | registro único (feito), laço com ferramentas, aprovação e custo à vista | E12 |
| Reforma | Radar de notícias | validador cClassTrib/NCM, impacto por cliente | E16 |
| Comunicação | e-mails de procuração | rascunho de e-mail ao cliente com o impacto, enviado por humano | E16 |
| Negócio do escritório | Rentabilidade (desligada), assinatura e limites (flags) | reajuste de honorários, painel consultivo | E16 |
| Confiança | isolamento por escritório (matriz), auditoria, retenção | página de status, relatório de coleta, política de IA pronta | E13 |

**Automações que rodam sem humano (revisar antes de ligar para novos escritórios):** coleta de NFS-e A1 e procuração, DTE, conciliação, triagem de caixas, DE-PARA com IA (produção), cobrança Asaas, lifecycle de tenant, retenção, alarmes de e-CNPJ e procuração. Regra: tudo novo nasce desligado e por escritório; nenhum cliente atual muda.

**O que tornaria o CICA único** (todas as pontas existem ou estão em andamento): procuração em vez de guardar certificado de cliente; Serpro oficial por evento (barato) com custo à vista; copiloto sobre Domínio, Serpro, NFS-e e documentos, aberto por MCP, com aprovação e evidência; triagem que aprende por escritório; checklist de fechamento; governança de IA por escritório. O que falta para fechar a tese: laço do copiloto com ferramentas (E12), Radar Simples/MEI (E14), fechamento por API (E15), captura de NF-e/CT-e por `autXML` ou integração com SIEG/Qive (decisão do dono).

**Pendências que dependem do dono** (nada disso se resolve só com código): perguntas ao Serpro, e-CNPJ real do piloto, custos (OCR, segundo worker), PR para `main` combinado com o Pedro, revisão jurídica de termos e DPA, grade de preços.
