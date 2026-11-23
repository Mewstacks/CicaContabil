# Plano — CICA como produto vendável (20/11/2026)

Spec e critérios: [produto-vendavel.md](produto-vendavel.md). Branch `feat/produto-vendavel` (a partir de `codex/contraprova`). Um plano, um gate de aprovação (D-303); cada épico vira PR próprio, deixa `main` liberável e passa pela guarda do legado (L1–L5). Sem estimativa de calendário (AGENTS.md): tamanhos P/M/G são relativos.

## Estado em 20/11/2026

| Épico | Estado | Evidência |
|---|---|---|
| E0 guarda do legado | feito localmente | V-301: `test_legacy_contract`, `test_migration_safety`, `legacy_snapshot` |
| E1 NFS-e por procuração | feito localmente, sem prova real | V-301; falta piloto com e-CNPJ e cliente reais, flag desligada, capacidade (custo) |
| E2 cadastro e onboarding | feito localmente (D-310, D-311) | V-302: carteira por planilha, passos com predicado verdadeiro, Turnstile desligado até haver chave |
| E3 cobrança, planos e limites | feito localmente (D-312, D-313), sem chamada ao Asaas real | V-303; falta sandbox Asaas (chave e webhook), grade aprovada, Q-48 |
| E4 segurança e privacidade | código feito localmente (D-314); **matriz de isolamento feita, sem vazamento** (V-307); minutas em `docs/legal/`; MFA em degrau, exclusão de escritório (Q-49), Sentry, restauração e `PLATFORM_DEVELOPER_FULL_ACCESS` ficam com o responsável | V-304, V-307 |
| E5 capacidade | feito localmente (D-315), sem custo aplicado | V-304; `docs/capacidade-procuracao.md`: segundo worker = +R$ 36,32/mês, aguarda OK |
| E6 a E9 | plano aprovado em 20/11/2026, em execução | proposta de preços pronta em `docs/comercial/proposta-precos.md` (não aprovada) |

Fora do escopo original de E1 e já feito porque a tela legada mostrava "Sem A1 válido" a escritório novo: lista de empresas, ficha da empresa e próximo passo falam de procuração só no modo `procuracao` (T1.9). Ficam para E4/E5: aviso de vencimento do e-CNPJ do escritório (hoje só o A1 por empresa notifica), alarme de procuração que expira, e capacidade do worker.

**Verificação do repo** (README.md:69-73, ci.yml:53-93), a cada tarefa e ao fim de cada épico:

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m pytest -q <arquivos da tarefa>
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m mypy <módulos novos>
```

Fim de épico: `pytest -q` inteiro (base: 1.869 testes, V-300) e `pytest --ds=config.settings.test_postgresql` quando houver PostgreSQL local.

## Ordem e dependências

E0 → E1 → (E2, E4 em paralelo) → E3 → E5 → E7 → E6/E8/E9 contínuos. E3 depende do sandbox Asaas e da grade de preços aprovada; E7 depende de E1 (certificado do escritório) e de E4 (isolamento).

## E0 — Guarda do legado (P)

| Tarefa | Arquivos | Verificação |
|---|---|---|
| T0.1 Testes de caracterização do legado | `tests/test_legacy_contract.py` | `pytest -q tests/test_legacy_contract.py tests/test_nfse_adn_sync.py` |
| T0.2 Linter de migração e linha de base | `tests/test_migration_safety.py`, `tests/legacy_baseline/migrations.json` | `pytest -q tests/test_migration_safety.py` |
| T0.3 Fotografia somente leitura | `src/apps/hub/management/commands/legacy_snapshot.py`, `tests/test_legacy_snapshot.py` | `pytest -q tests/test_legacy_snapshot.py` |
| T0.4 Flags desligadas | `src/config/settings/base.py` (`NFSE_PROCURACAO_SYNC_ENABLED`, `NFSE_PROCURACAO_POLL_INTERVAL_MINUTES`) | teste de default em `test_legacy_contract.py` |

Antes de qualquer deploy: `legacy_snapshot` em produção (leitura, autorizado em `deploy-authorized`) → deploy canário → `legacy_snapshot` de novo → `--compare` idêntico.

## E1 — NFS-e por procuração (M)

Mapa do que existe e do que se acrescenta (nada do legado é editado):

| Peça | Legado (intocado) | Novo |
|---|---|---|
| Cliente ADN | `hub/nfse_adn.py` `AdnClient` já envia `lote=true&cnpjConsulta` | `hub/nfse_procuracao.py`: subclasse que lê o corpo de erro (`Erros[].Codigo`) e mapeia E22xx, 495, 429 |
| Certificado | `Certificate` por empresa; `certificate_ssl_context` exige raiz da empresa | `OfficeCertificate` por escritório; `office_ssl_context` exige raiz de `OfficeProfile.cnpj` |
| Ingestão | `process_sync_pages` | reutilizado como está |
| Fila | `dispatch_active_nfse_syncs`/`poll_nfse_sync`; `_eligible_nfse_syncs` já exclui linha sem `certificate` | `hub/tasks_procuracao.py`: despacho e sondagem próprios, elegibilidade própria |
| Estado | `NfseSync` | campos novos: `credential_mode`, `office_certificate`, `procuracao_status`, `procuracao_checked_at`, `procuracao_notice`, `tipo_consulta` |
| Modo | — | `OfficeProfile.nfse_collection_mode` (`certificate` padrão; `procuracao` para cadastros novos) |

| Tarefa | Arquivos | Verificação |
|---|---|---|
| T1.1 Modelos e migração 0078 (só adiciona) | `hub/models.py`, `hub/migrations/0078_*.py` | `makemigrations --check`, `test_migration_safety.py` |
| T1.2 Cliente, sonda, semeadura, processamento | `hub/nfse_procuracao.py`, `tests/test_nfse_procuracao.py` | `pytest -q tests/test_nfse_procuracao.py` |
| T1.3 Tarefas Celery e agenda (flag desligada) | `hub/tasks_procuracao.py`, `config/settings/base.py` (beat), `tests/test_nfse_procuracao_tasks.py` | idem |
| T1.4 Envio e validação do e-CNPJ do escritório | `hub/office_certificate.py`, `tests/test_office_certificate.py` | idem |
| T1.5 Pedido de procuração por e-mail | `hub/procuracao_requests.py`, `tests/test_procuracao_requests.py` | idem |
| T1.6 Telas e rotas | `hub/views_procuracao.py`, `hub/urls.py`, `hub/templates/hub/nfse_procuracao.html`, `hub/static/hub/` | testes de view + Playwright 375/768/1440 |
| T1.7 Cadastro novo nasce em `procuracao` | `platform/signup.py`, `platform/views.py` (criar tenant), testes | `pytest -q tests/test_platform_signup*.py` |
| T1.8 Documento operacional | `docs/nfse-procuracao.md` (passo a passo do outorgante, e-mail, erros e ação) | revisão |
| T1.9 Telas legadas que falam de A1 | `hub/templates/hub/companies.html`, `company_detail.html`, `hub/views.py` (próximo passo, desvio de `certificates` e da aba Coleta), `hub/navigation.py`, `hub/templatetags/procuracao_tags.py` | `pytest -q tests/test_nfse_procuracao_views.py` |

Teste real da procuração só em produção e com e-CNPJ e cliente reais autorizados (a produção restrita não tem cadastro de procuração). Piloto sugerido: Fedrizzi (parceiro de teste, já usa esse modelo no HubFedrizzi). Antes disso, `NFSE_PROCURACAO_SYNC_ENABLED` fica desligada e `NFSE_ADN_ENVIRONMENT=production` é exigido.

## E2 — Cadastro e onboarding até o primeiro resultado (M)

Base: `/comecar/` (hub/views.py:483-539), `platform/signup.py`, assistente `hub:setup` (hub/views.py:13740-14070). Tarefas: passos do assistente com predicados verdadeiros (PC-11): e-CNPJ enviado → empresas importadas (CSV ou sincronização Domínio) → procurações pedidas → primeira NFS-e; importação de carteira por planilha com prévia e relatório de erro (padrão `clientes/importar` do Accurit); convite de equipe; CAPTCHA no cadastro (Cloudflare Turnstile, gratuito); e-mail transacional por Brevo já decidido (D-77/78), configuração do SMTP é ação do responsável; estados vazios com atalho de saída.

## E3 — Cobrança, planos e limites (G)

Base: `platform/billing.py`, `platform/asaas.py`, `platform/payments.py`, `platform/tasks.py`, `Plan`/`TenantContract`/`Entitlement`/`FeatureFlag` (platform/models.py). Tarefas: instanciar o cliente Asaas e criar cliente e cobrança na conversão trial→pago; criar `PaymentAttempt` e gravar `asaas_*_id`; página de checkout; automação de carência e somente leitura de D-79 (`grace_ends_on` hoje só é escrito; reativação hoje é manual, views.py:336-354); ler `Plan.limits` para teto de empresas, usuários e certificados, com aviso em 80% e 100% (padrão do Accurit); taxa de Serpro no trial (`signup.py:213-241` só cria `ai.answer`); medidor com idempotência por `transaction_id` (padrão do Lago); reconciliação de eventos fora de ordem. **Gates do responsável:** chave e token de webhook do sandbox Asaas; grade de preços aprovada; nenhuma cobrança real sem OK.

## E4 — Segurança, privacidade e confiança (G)

- Matriz de isolamento: `tests/test_tenant_isolation_matrix.py` cria dois escritórios e percorre toda rota do `urls.py`, esperando 403/404 nos recursos do vizinho (padrão `idor_matrix.rs` do Accurit). `OrganizationScopedModel` é FK simples sem manager que filtre (organizations/models.py:90-95): primeiro testes, depois correção só dos vazamentos achados.
- Remover `PLATFORM_DEVELOPER_FULL_ACCESS` de produção (production.py:11-13, marcado temporário). **Gate:** afeta o acesso de suporte; precisa do seu OK.
- Alinhar termos a D-192 (MFA opcional para cliente; legal.py:25-27 promete obrigatório) ou impor; MFA em degrau para enviar/trocar e-CNPJ; auditoria de uso do certificado; rotação de chave simulada (chaveiro único no env, base.py:459-460).
- LGPD (PC-28): retenção por artefato, exportação e exclusão executáveis, lista de suboperadores (Fly, Neon, Tigris, Brevo, Anthropic), minutas de DPA e política para revisão jurídica.
- Restauração Neon e documentos medida contra o RTO de 4 h (D-73); Sentry ligado (fly.toml:32 está desligado).

## E5 — Capacidade e operação (M)

A fila ADN legada é global e serial (hub/tasks.py:158-161): ~560 CNPJs levam horas. A fila de procuração nasce com cadência por empresa (1/6/24 h), um e-CNPJ por vez com piso de 1 s, e despacho em lote por escritório. **Gate de custo (CLAUDE.md):** rodar a fila nova sem tirar tempo da Bianchi exige um segundo processo worker (hoje `shared-cpu-1x` 512 MB, `--concurrency=1`, fly.toml:64-72) ou mais concorrência/memória. Antes de aplicar: preço mensal atual e novo, e a diferença, medidos na documentação do Fly; nada é aplicado sem sua confirmação. Também: alarme de fila parada, procuração e certificado a vencer, teste de carga (N escritórios × M empresas), Neon (conexões) e Valkey conferidos.

## E6 — Experiência e conteúdo (M)

Ajuda no ponto de uso (sem parágrafo explicativo, regras de UI), página de preços que só exibe valor aprovado, demonstração coerente com o produto, e-mails transacionais, 375/768/1440 px, contraste AA, `/impeccable audit` por tela alterada. Referências: Linear e Stripe (barra de lista), Qive (lista de documentos fiscais), Acessórias e Gestta (prazos, área do cliente fica fora, D-309).

## E7 — Módulos novos (G, um PR por módulo)

| Módulo | Origem | Dependência | Nota |
|---|---|---|---|
| Emissão de NFS-e por procuração | EmissaoNFSe, Conta200 | E1, E4 | DPS assinada XMLDSig com o e-CNPJ, SEFIN mTLS, DANFSe do ADN, lote CSV/XLSX, cancelamento. Aprovação humana antes de cada emissão; produção fiscal só com OK explícito. Verificar na norma se a assinatura pode ser do outorgado (Resolução CGNFS-e 003/2023, citada em notícia, não lida) |
| RBT12, Fator R e teto Simples/MEI | RBT12, dominio-automacao, Conta200 | Integra (`integra/` tem PGDAS-D), folha agregada do agente | Alerta de sublimite e Fator R; custo Serpro mostrado antes (repasse sem margem, D-109); saída em planilha para o Domínio, sem RPA de tela |
| Reforma IBS/CBS | RetificacaoPandolfo (plano), Radar existente | calculadoras oficiais da Receita (MIT) | Sidecar Java 25 é custo de infra: gate de custo. Alternativa a pesquisar: serviço público oficial |
| Situação fiscal e pendências | Accurit (padrão) | Integra (SITFIS) | Só leitura; agregação por carteira; custo por chamada visível |

## E8 — Qualidade (P)

CI passa a rodar `ruff format --check` e `mypy` somente nos arquivos novos ou alterados (há 177 arquivos e 14 erros de mypy preexistentes, V-300), cobertura (gate 85, pyproject.toml:87), `test_migration_safety`, PostgreSQL (já existe), `pip-audit`, Playwright do fluxo cadastro→procuração. Verificação de licença das dependências novas.

## E9 — Kit comercial (M)

`docs/comercial/proposta-precos.md`: grade proposta com fontes e custo por tenant (Fly, Neon, Brevo, Asaas, Serpro, Claude em reais). Referências já levantadas: Acessórias e Gestta cobram sob consulta; Qive captura NFS-e com A1 por CNPJ a cada 2 h; Domínio Cobranças cobra por uso; tabela de consumo Serpro divulgada de R$ 0,06 a R$ 0,40 (confirmar na Loja Serpro); Asaas Pix R$ 1,59 e boleto R$ 1,59 após a promoção, cartão 2,99% + R$ 0,49 (páginas divergem, confirmar na conta). Também: minutas de termos, DPA e suporte, roteiro de demonstração, playbook de onboarding, lista de prospecção a partir de `API_RECEITA` (escritórios do RS).

## Referências open source (padrão extraído, não código; D-303)

| Projeto | Licença | Usar para |
|---|---|---|
| [nfse-nacional/nfse-php](https://github.com/nfse-nacional/nfse-php) | MIT | cliente ADN com `cnpjConsulta`, OpenAPI oficial em `references/api-specs` |
| [gabrielbuzziv/emissor-nfse-nacional](https://github.com/gabrielbuzziv/emissor-nfse-nacional) | MIT | emissão direta, e-CNPJ como segredo, aviso de renegociação TLS do governo |
| [OpenAC-Net/OpenAC.Net.NFSe.Nacional](https://github.com/OpenAC-Net/OpenAC.Net.NFSe.Nacional) | MIT | leiaute e assinatura da DPS |
| [Siricode-BR/Accurit](https://github.com/Siricode-BR/Accurit) | MIT | SaaS multi-tenant contábil: verificação de procuração (`OBTERPROCURACAO41`), planos e consumo com aviso 80/100%, LGPD, matriz IDOR, ensaio de restore |
| [GabrielHCamargo/SDK-Integra-Contador](https://github.com/GabrielHCamargo/SDK-Integra-Contador), [lucas-bogos/xsign](https://github.com/lucas-bogos/xsign) | Apache-2.0, MIT | envelope Integra e XMLDSig |
| [ReceitaFederal/calculadora-rtc-simples-nacional](https://github.com/ReceitaFederal/calculadora-rtc-simples-nacional), `-regime-regular`, `-gerador-danfse` | MIT | CBS/IBS oficial e DANFSe |
| [django-waffle](https://github.com/django-waffle/django-waffle) | BSD-3 | padrão de flag por organização (o repo já tem `FeatureFlag` sem leitor) |
| [django-scopes](https://github.com/raphaelm/django-scopes) | Apache-2.0 | escopo de tenant que falha alto |
| [getlago/lago](https://github.com/getlago/lago) | AGPL-3.0, só estrutura | evento de uso idempotente por `transaction_id`, métricas, assinatura resolvida no instante do evento |
| [paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) | GPL-3.0, só estrutura | pipeline de consumo, regras de correspondência, duplicata sinalizada (Triagem) |
| [DeHor-Labs/mcp-fiscal-brasil](https://github.com/DeHor-Labs/mcp-fiscal-brasil) | MIT | ferramentas fiscais para o Copiloto |
| [uptime-kuma](https://github.com/louislam/uptime-kuma) | MIT | página de status |

## Gates do responsável (nada abaixo é presumido)

Chave e webhook do sandbox Asaas · SMTP Brevo e domínio de envio · aprovar a grade de preços · custos de infra E5 e E7 com valor exato · remover `PLATFORM_DEVELOPER_FULL_ACCESS` · Q-41/42/43/46/47 para ligar Rentabilidade e Contraprova · revisão jurídica de termos e DPA · e-CNPJ e cliente reais para o piloto de procuração · OK por tenant para emissão fiscal em produção.

## Riscos

| Risco | Tratamento |
|---|---|
| Limite de taxa do ADN desconhecido | piso de 1 s por e-CNPJ, pausa em 429, quarentena em 495, cadência por empresa |
| Cliente demora ou não outorga procuração | estado explícito, pedido por e-mail e planilha de pendentes, nova sonda em 6 h |
| e-CNPJ do escritório é segredo de alto valor | AAD próprio, MFA em degrau, auditoria, rotação, nunca no log |
| Fila nova atrasa a Bianchi | filas separadas por modo; capacidade com gate de custo |
| Migração em banco compartilhado | só adiciona; linter; `legacy_snapshot` antes e depois |
| "Tudo junto" estoura escopo | um PR por épico, `main` liberável a cada passo, módulos desligados por padrão (`NOT_SELF_SERVICE_MODULE_CODES`) |
