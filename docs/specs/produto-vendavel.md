# Spec — CICA como produto vendável (20/11/2026)

Plano de execução: [produto-vendavel-plano.md](produto-vendavel-plano.md). Decisões: D-303 a D-309 em [DECISOES.md](../../DECISOES.md).

## Problema

O CICA opera para três clientes (Bianchi & Rizzotto no Fly, Fedrizzi como parceiro de teste, Cobalchini em Compose local) e não está pronto para ser vendido a escritórios novos. Lacunas provadas no código:

- **NFS-e exige o A1 de cada empresa-cliente.** O ADN passou a aceitar consulta de outro contribuinte mediante procuração (Manual ADN v1.1, 03/11/2026). O HubFedrizzi já opera assim com o e-CNPJ do escritório; o CICA não tem e-CNPJ de escritório nem modelo de procuração (`Certificate.company` é obrigatório; `nfse_sync.py:78-94` exige raiz igual à da empresa).
- **Cobrança não está ligada.** O cliente Asaas nunca é instanciado; nada cria `PaymentAttempt`; `grace_ends_on` só é escrito; não há checkout nem conversão trial→pago.
- **Plano e limite não são aplicados.** `Plan.limits`, `Entitlement`, `FeatureFlag` e `OfficeProfile.require_mfa` não têm leitor em produção.
- **Fila ADN global e serial** (uma empresa por vez, ~30 s): um tenant novo competiria com a Bianchi.
- **Confiança:** termos em rascunho, `PLATFORM_DEVELOPER_FULL_ACCESS` verdadeiro em produção, sem CAPTCHA no cadastro, restauração não provada, Sentry desligado.

## Objetivo

Escritório novo (Domínio) cadastra-se, sobe o e-CNPJ, pede procuração aos clientes e vê NFS-e chegando, com cobrança, limites, segurança e suporte de produto. Clientes atuais não percebem nenhuma diferença.

## Regras invioláveis do legado (L1–L5)

| ID | Regra | Prova |
|---|---|---|
| L1 | Migração só adiciona: `CreateModel`, `AddField` nulo ou com default que preserva o comportamento, índice, constraint nova. Nada de `RemoveField`, `DeleteModel`, `RenameField` nem `AlterField` que mude tipo, nulidade ou default de coluna existente | `tests/test_migration_safety.py` |
| L2 | Todo comportamento novo fica atrás de modo por organização cujo valor para linhas existentes é o comportamento atual, e de flag de runtime desligada por padrão | testes de default + flag |
| L3 | Código legado não é editado: `nfse_adn.AdnClient`, `nfse_sync.certificate_ssl_context`, `tasks.poll_nfse_sync`, `_eligible_nfse_syncs`. Novo código mora em módulos novos; ligações só por adição | revisão de diff + testes de caracterização |
| L4 | Suíte de contrato do legado passa antes e depois; `legacy_snapshot` de produção, lido antes e depois do deploy, é idêntico para toda organização existente | `tests/test_legacy_contract.py`, `manage.py legacy_snapshot --compare` |
| L5 | Capacidade nova não consome o worker nem a fila dos tenants atuais sem confirmação de custo com número exato | gate de custo no plano |

## Escopo (D-303: tudo junto, um plano, entrega por épicos)

E0 guarda do legado · E1 NFS-e por procuração (coleta) · E2 cadastro e onboarding até o primeiro resultado · E3 cobrança, planos e limites · E4 segurança, privacidade e confiança · E5 capacidade e operação · E6 experiência e conteúdo · E7 módulos novos (emissão NFS-e por procuração, RBT12/Fator R/teto Simples e MEI, Reforma IBS/CBS, situação fiscal) · E8 qualidade · E9 kit comercial.

## Fora de escopo

Portal do cliente final e WhatsApp (D-309); ERP além do Domínio (D-308); retificação de EFD e recuperação de tributos (D-306); publicar preço, cobrar, emitir nota em produção, aumentar VM ou contratar serviço sem OK explícito com valor exato; migrar clientes atuais para procuração; mexer em Contraprova e Rentabilidade (seguem desligados até Q-46/47/41/42/43).

## Fatos de base (fontes)

- **ADN, consulta de outro contribuinte.** Manual dos Contribuintes, Guia das APIs do ADN, v1.1 de 03/11/2026, §1.1.1(a): sem `cnpjConsulta` retorna o titular do certificado; `cnpjConsulta` com mesma raiz autoriza sem procuração; raiz diferente (ou `cpfConsulta` diferente) exige procuração válida cadastrada pelo outorgante no Portal de Serviços da Receita (`https://servicos.receitafederal.gov.br/`), senão erro **E2245**; os dois parâmetros juntos dão E2244; a resposta traz `TipoConsulta` (`InscricaoCertificado`, `CnpjBase`, `Procuracao`). Erros E2210–E2214 (certificado), E2220/E2230/E2240/E2241 (404), E2243, E2246, E2247, E999. PDF: `gov.br/nfse/.../manual-municipios-apis-adn-sistema-nacional-nfs-e-v1-1-20261103.pdf` (a URL `manual-contribuintes-...` ainda serve a v1.0 de 12/02/2026, que só prevê mesma raiz).
- **Prática comprovada.** HubFedrizzi (`docs/portal-nacional-nfse.md`, `apps/nfse/portal_nacional.py`): mTLS com o e-CNPJ A1 do escritório, `cnpjConsulta` do cliente, sonda para saber se há procuração (200 ou 404 E2220 = ok; 400 E2245 = pendente, repetir em 6 h), 495 coloca o certificado 15 min em quarentena, 429 pausa global, piso de 1 req/s, cadência de 1/6/24 h. EmissaoNFSe provou emissão por procuração (HTTP 201 em 04/11/2026) e leitura ADN de 403 clientes e 58.697 documentos em 10/11/2026.
- **Procuração só vale em produção.** No ambiente restrito não há cadastro de procuração (EmissaoNFSe `src/tenant/credencial.ts:82-83`).
- **Portal de Serviços:** o outorgante indica CPF/CNPJ do procurador, validade e o serviço NFS-e (Contábeis, Brasil 61, 06/11/2026). O caminho exato de menu varia e não foi verificado.

## Critérios de aceitação — E0 (guarda do legado)

**Estado 20/11/2026:** AC-0.1 a AC-0.4 atendidos localmente (V-301).

- **AC-0.1** `tests/test_legacy_contract.py` fixa o comportamento atual: URL e cabeçalhos de `AdnClient.fetch_page`; `poll_nfse_sync` usa o certificado da empresa; `_eligible_nfse_syncs` exige `certificate` não nulo; todo `NfseSync` e `OfficeProfile` existente tem modo legado. Passa antes e depois da mudança.
- **AC-0.2** `tests/test_migration_safety.py` reprova qualquer operação proibida por L1 em migração criada depois da linha de base e aprova as migrações novas desta entrega.
- **AC-0.3** `manage.py legacy_snapshot` imprime JSON determinístico por organização (contagens por modelo, módulos, contrato, estado das sincronizações, hash do esquema das tabelas legadas) e `--compare A B` sai com 0 só se forem idênticos, ignorando campos de tempo documentados.
- **AC-0.4** Flags novas desligadas: com `NFSE_PROCURACAO_SYNC_ENABLED=False` as tarefas novas retornam sem tocar em banco nem rede; as entradas legadas de `CELERY_BEAT_SCHEDULE` não mudam.

## Critérios de aceitação — E1 (NFS-e por procuração)

**Estado 20/11/2026:** AC-1.1 a AC-1.10 atendidos localmente com transporte falso (V-301). Pendente: piloto real (e-CNPJ e cliente reais, só em produção), ligar a flag e decidir a capacidade do worker. A planilha do AC-1.7 é só de pendentes; a cadência de 24 h do AC-1.6 vale para empresa sem notas há 7 dias.

- **AC-1.1** Escritório em modo `procuracao` envia o e-CNPJ A1 (`OfficeCertificate`): abre o PKCS#12, exige chave privada, validade futura e raiz do CNPJ igual à de `OfficeProfile.cnpj`; guarda cifrado (`EncryptedTextField`), nunca devolve o arquivo ou a senha, registra auditoria, só papéis owner/admin.
- **AC-1.2** Toda empresa ativa de organização em modo `procuracao` ganha uma `NfseSync` de modo `procuracao` por rotina idempotente; organização legada não ganha nenhuma.
- **AC-1.3** A sonda classifica: 200 e 404 com E2220/E2230 → `ok`; 400 com E2245 → `aguardando procuração` (não é erro; nova sonda em 6 h); 400 com E2243/E2244/E2246/E2247 → erro de configuração com código; E2210–E2214 → problema de certificado, bloqueia só as sincronizações desse escritório; 401/403 → certificado recusado; 429 → pausa da fila; 495 → quarentena do certificado por 15 min; 5xx e rede → nova tentativa com recuo.
- **AC-1.4** A ingestão reutiliza `process_sync_pages` sem alterá-lo: dedupe por NSU e hash, XML imutável, checkpoint atômico por empresa. Documentos de empresa em modo `procuracao` são indistinguíveis dos demais para classificação e pacote.
- **AC-1.5** `TipoConsulta` da resposta fica gravado; empresa de mesma raiz do escritório usa `CnpjBase` e conta como `ok` sem procuração.
- **AC-1.6** No máximo uma chamada em voo por e-CNPJ, piso de 1 s entre chamadas por e-CNPJ, cadência por empresa de 1 h (em dia), 6 h (aguardando) ou 24 h (sem movimento). O despachante novo nunca seleciona linha legada e o legado nunca seleciona linha nova.
- **AC-1.7** Tela para organização em modo `procuracao`: cartão do e-CNPJ (validade, dias restantes, enviar/trocar), tabela de empresas com estado da procuração, última verificação, último NSU e contagem, filtros Sem procuração / Em dia / Com erro, ações "Pedir procuração" (linha e lote), "Verificar" e XLSX dos pendentes. Texto conforme as regras de UI do CLAUDE.md, 375 px sem rolagem horizontal, contraste AA, teclado.
- **AC-1.8** O pedido de procuração é e-mail por clique (nunca automático), a `ClientCompany.contact_email`, identifica escritório e CNPJ do outorgado e o serviço NFS-e; registrado em `NfseProcuracaoRequest`; salta quem recebeu há menos de 3 dias; máximo 80 por clique; sem dado de certificado.
- **AC-1.9** `NFSE_PROCURACAO_SYNC_ENABLED` desligada por padrão; a fila recusa rodar com `NFSE_ADN_ENVIRONMENT=trial` e mostra o motivo.
- **AC-1.10** Testes unitários e de integração com transporte falso para cada código de erro; cobertura ≥ 90% nos módulos novos; `ruff` e `mypy` limpos neles; `makemigrations --check` sem pendência; suíte inteira verde.

## Critérios de aceitação — E2 a E9 (nível de título; detalhados ao iniciar cada épico)

**Estado 20/11/2026 (V-302 a V-305):** E2, E3, E5 e E8 atendidos localmente no que não depende de terceiro; E4 em parte (exportação, retenção, prontidão, alarmes, termos e matriz de isolamento feitos, sem vazamento; exclusão de escritório, degrau de MFA, Sentry e restauração abertos); E6 em parte (telas em 375, 768 e largura de painel, foco e contraste; ajuda no ponto de uso e e-mails não revisitados); E7 só especificação (`docs/specs/modulos-pacote-fiscal.md`); E9 com proposta de preços e minutas não aprovadas. Pendências que são do responsável estão em `docs/specs/produto-vendavel-plano.md` (gates).

- **E2** Cadastro novo chega ao primeiro NFS-e sem ajuda humana; nenhum passo do assistente aparece concluído sem predicado verdadeiro.
- **E3** Trial→pago por Asaas (sandbox primeiro), carência e somente leitura automáticos (D-79), limites de empresas/usuários/certificados aplicados, eventos repetidos e fora de ordem sem regressão.
- **E4** Matriz de isolamento entre dois escritórios cobre toda rota; termos coerentes com D-192; `PLATFORM_DEVELOPER_FULL_ACCESS` fora do produto; restauração medida; exportação e exclusão LGPD executáveis.
- **E5** Tenant novo não atrasa tenant atual; teste de carga com N escritórios × M empresas dentro do orçamento; alarmes de fila, procuração a vencer e certificado a vencer.
- **E6** Ajuda no ponto de uso, página de preços sem número não aprovado, demonstração coerente, 375/768/1440 px, AA.
- **E7** Cada módulo com fonte oficial citada, aprovação humana antes de qualquer efeito legal, custo Serpro visível antes da chamada.
- **E8** CI roda ruff, mypy nos arquivos novos, cobertura, migração segura e PostgreSQL.
- **E9** Grade de preços proposta com fontes e custo por tenant; minutas de termos, DPA e suporte para revisão jurídica.
