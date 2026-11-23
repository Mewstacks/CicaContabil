# Suboperadores e fornecedores que recebem dado

> **MINUTA PARA REVISÃO JURÍDICA — não é parecer nem texto vigente**

| Campo | Valor |
|---|---|
| Data | 20/11/2026 |
| Base | árvore de trabalho da branch `feat/produto-vendavel` (parte sem commit). Linhas conferidas em 20/11/2026; podem deslocar |
| Escopo | só o que o código chama ou configura. O que é opcional ou desligado está dito. Nada foi verificado em produção, salvo onde a fonte diz |
| Destino | alimentar o anexo (`platform/legal.py:163-169`) e a política de privacidade (`platform/legal.py:112-119`), que hoje deixam a lista em aberto |
| Caminhos | relativos a `src/apps/`; `config/` = `src/config/`; `fly.toml`, `infra/`, `docs/` e arquivos da raiz como estão |
| Legenda | **ATIVO** = chamado em produção pelo fluxo normal. **OPCIONAL** = só se um módulo ou chave for ligado. **DESLIGADO** = desligado por padrão. **A CONFIRMAR** = o repo não prova; conferir na conta ou no contrato |

## 1. Papéis

Os textos atuais dizem que a Mewstack trata como **controladora** o que é do cadastro, da relação comercial, da segurança e da cobrança, e como **operadora** o dado de cliente do escritório tratado sob instrução dele; o escritório é o controlador desse último (`platform/legal.py:86-93`). A LGPD define os dois papéis no art. 5º, VI e VII, e manda o operador seguir as instruções do controlador (art. 39; planalto.gov.br, 20/11/2026). Cada fornecedor da tabela 2 é, para o dado do cliente do escritório, um suboperador da Mewstack; para o dado de cadastro e cobrança, um operador dela. A exceção é S11: a caixa de e-mail é do escritório e a Mewstack só a lê com o consentimento dele.

## 2. Quem recebe dado

| # | Fornecedor | Para quê | Dado que recebe | Onde fica | Quando é acionado | Estado | Evidência |
|---|---|---|---|---|---|---|---|
| S1 | **Fly.io** (app `cica-contabil`) | Executa o site (gunicorn) e o worker com agenda (Celery); termina o TLS | Tudo o que passa nas requisições (login, e-CNPJ enviado, XML) e o log em stdout: e-mail redigido; o log de acesso do gunicorn grava o caminho, inclusive links de uso único | Região `gru` (São Paulo) | Sempre | ATIVO | `fly.toml:2-3,37-38,64-72`; `common/logging.py:11-30` |
| S2 | **Fly.io** (app `cica-contabil-valkey`) | Fila e resultados do Celery, cache, limite de taxa, bloqueio de login, sessão em cache | Identificadores de tarefa, chaves de cache, sessão, resposta da consulta de CNPJ por 1 h; grava em disco (AOF, volume) | Região `gru` | Sempre | ATIVO | `infra/valkey/fly.toml:1-10`; `config/settings/base.py:329,514-515`; `common/cnpj.py:30-35,70` |
| S3 | **Neon** (PostgreSQL: bancos `cica_main` e `cica_knowledge`) | Guarda todos os dados do produto | Dados de negócio e pessoais. Segredo e campo sensível são cifrados no aplicativo (AES-GCM, chave fora do banco). Sem cifra: nome, CNPJ e contato da empresa, contraparte da nota, e-mail do usuário | `aws-sa-east-1` (São Paulo); a região não muda depois de criada | Sempre | ATIVO | `DECISOES.md:866-868`; `docs/comercial/proposta-precos.md:45`; `hub/models.py:155-177,564-592`; `common/encryption.py:63-92`; `config/settings/production.py:62-66` |
| S4 | **Tigris** (bucket privado, via Fly) | Guarda arquivos | Pacotes de NFS-e (`private/nfse-exports/`), relatórios, importações, documentos da Triagem, arquivos do Contraprova, fontes da conciliação | O padrão da Tigris é global; o tipo deste bucket é A CONFIRMAR | Quando um módulo grava arquivo | ATIVO | `fly.toml:29`; `config/settings/production.py:102-130`; `hub/models.py:42-52`; `triage/storage.py:18-31`; `VALIDACOES.md:3096` |
| S5 | **Brevo** (SMTP) | E-mail transacional | Endereço do destinatário, nomes (escritório, empresa), links de uso único; pedido de procuração enviado ao cliente do escritório | UE, segundo a Brevo (A CONFIRMAR) | Cadastro (link de 24 h), convite (7 dias), redefinição de senha, pedido de procuração (por clique) | Decidido (D-78); SMTP em produção A CONFIRMAR | `DECISOES.md:125-127`; `config/settings/production.py:132-134`; `common/database_email.py:44-68`; `platform/signup.py:153-164`; `hub/procuracao_requests.py:50-65`; `docs/comercial/proposta-precos.md:68` |
| S6 | **Cloudflare** (Turnstile) | Barra robô no cadastro | O navegador do visitante carrega o script e fala direto com a Cloudflare (IP e sinais do navegador). O servidor envia só a chave secreta e o token, sem IP | Rede global da Cloudflare | Só em `/comecar/`, com as duas chaves | DESLIGADO | `common/turnstile.py:12-15,74-102`; `config/settings/base.py:361-365`; `hub/templates/hub/signup.html:29,37`; `DECISOES.md:1936` |
| S7 | **Anthropic** (Claude API) | Reserva do Copiloto | Pergunta e evidências com CPF, CNPJ, e-mail e segredo mascarados; no banco fica só metadado (hash, tokens, custo) | `api.anthropic.com`; local de processamento A CONFIRMAR | Só com `cloud_fallback_enabled`, aprovação do escritório, chave e teto maior que zero | DESLIGADO; Copiloto desligado em produção em 20/11/2026 | `intelligence/gateway.py:44,56-70`; `platform/models.py:40,45-52`; `intelligence/models.py:31,598-633`; `docs/comercial/proposta-precos.md:32` |
| S8 | **Asaas** | Cobrança por Pix, boleto e cartão | Razão social, CNPJ, e-mail do dono do escritório, valor, vencimento e descrição "Mensalidade CICA, competência MM/AAAA". O cartão é digitado na página do Asaas | Brasil; hospedagem A CONFIRMAR | Clique em Pix, Boleto ou Cartão numa fatura de contrato automático; tarefas diárias de política e conciliação | DESLIGADO (sandbox por padrão) | `platform/collection.py:72-86,126-210`; `hub/views_subscription.py:54-61,108-132`; `config/settings/base.py:49-55`; `platform/webhooks.py:16-46` |
| S9 | **BrasilAPI** | Preenche o cadastro pelo CNPJ | CNPJ do escritório, na URL. Volta dado cadastral público, sem sócios | Projeto comunitário, sem contrato; hospedagem A CONFIRMAR | A cada cadastro e a cada consulta do formulário | ATIVO | `common/cnpj.py:28-71`; `platform/signup.py:84`; `hub/templates/hub/signup.html:10` |
| S10 | **Serpro** (Integra Contador) | Consultas e emissões fiscais da Central Integra | CNPJ ou CPF do contribuinte e do escritório, identificadores de guia e pedido. Autentica com o A1 central da Mewstack e a chave do contrato | Órgão público brasileiro | Módulo ligado por escritório; custo mostrado antes de cada chamada (D-109 e D-306) | OPCIONAL (ambiente `trial` por padrão) | `integra/client.py:38-41`; `config/settings/base.py:416-425`; `platform/models.py:61-75` |
| S11 | **Google** (Gmail) e **Microsoft** (Graph) | Ler a caixa de e-mail que o escritório conectar (Triagem) | Mensagens e anexos da caixa, só leitura, com dado de terceiros; a Mewstack guarda cópia dos anexos | Nuvens do Google e da Microsoft; a caixa é do escritório | Só com OAuth ligado e consentimento do escritório | DESLIGADO | `config/settings/base.py:428-443`; `triage/oauth.py`; `triage/models.py:284-296` |
| S12 | **Sentry** | Monitoramento de erros | Se ligado: erro sem corpo de requisição, cookie, e-mail ou usuário | Região do DSN a escolher | Só com `SENTRY_ENABLED=true` e DSN | DESLIGADO | `fly.toml:32`; `config/settings/production.py:136-160`; `common/sentry.py:48-` |
| S13 | **Thomson Reuters** (Onvio e Domínio, API oficial) | Empresas e lotes de XML | OAuth do escritório, lista de empresas, lotes | A CONFIRMAR | Quando houver credencial de parceiro | NÃO ATIVO (adaptador pronto, OAuth pendente) | `hub/dominio_api.py`; `docs/dominio-web-limitacoes-comerciais.md:73-80` |

## 3. Transferência internacional e o que cada parte percebe

A LGPD só permite a transferência internacional nos casos do art. 33 (adequação, cláusulas, selos, consentimento específico e outros). A ANPD aprovou o regulamento e as cláusulas-padrão na Resolução CD/ANPD nº 19/2024: a transferência por cláusulas-padrão só vale com o texto do Anexo II adotado por inteiro, e o prazo de adequação foi de 12 meses da publicação (<https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/resolucao-cd-anpd-no-19-de-23-de-agosto-de-2024>, resumo de busca de 20/11/2026; conferir o texto). Servidor no Brasil de fornecedor estrangeiro e acesso remoto de fora são pontos que o jurídico precisa decidir caso a caso; esta coluna só registra o fato.

| # | Observação, com fonte | O escritório percebe | O cliente do escritório percebe |
|---|---|---|---|
| S1, S2 | Servidores em São Paulo (`fly.toml:3`). Sede do fornecedor, acesso de suporte e subprocessadores: A CONFIRMAR no DPA | Nada na tela | Nada |
| S3 | Banco em São Paulo (Neon: a região é fixa na criação, <https://neon.com/docs/introduction/regions>, 20/11/2026). Histórico de restauração de 6 h (`docs/comercial/proposta-precos.md:290`). Sede e subprocessadores A CONFIRMAR | Nada | Nada |
| S4 | Padrão global: o objeto fica na região mais próxima do upload e nomes e tamanhos de objeto são replicados para todas as regiões; só o tipo single-region fixa a residência (<https://www.tigrisdata.com/docs/buckets/locations/>, 20/11/2026). `docs/pt-BR/lgpd.md:52` já avisa | Download autenticado; sem URL pública | Nada |
| S5 | Hospedagem na UE segundo a Brevo (<https://help.brevo.com/hc/en-us/articles/360001005510-Data-storage-location>: a página deu HTTP 403 ao abrir; resumo de busca de 20/11/2026; conferir). Brasil para UE é transferência do art. 33 | E-mail de confirmação, convite e recuperação | Recebe "Procuração para {escritório} acessar as NFS-e" do remetente da Mewstack, não do escritório (`hub/procuracao_requests.py:50-65`). Domínio de envio e autenticação DNS pendentes (Q-29) |
| S6 | O IP do visitante não passa pelo nosso servidor (`common/turnstile.py:14`), mas o navegador fala com a Cloudflare. A Cloudflare diz que processa só o necessário e remete a um "Turnstile Privacy Addendum"; a página não cita a LGPD (<https://developers.cloudflare.com/turnstile/frequently-asked-questions/>, 20/11/2026) | Widget sem imagem no cadastro | Nada (o cadastro é do escritório) |
| S7 | Documentação da Anthropic (<https://platform.claude.com/docs/en/manage-claude/api-and-data-retention>, 20/11/2026): prompt e resposta não ficam retidos por padrão, salvo modelos "Covered" (30 dias); conteúdo sinalizado pode ficar até 2 anos; retenção zero por contrato. O repo não usa o parâmetro de residência (`inference_geo`) | Copiloto (hoje indisponível) | Nada |
| S8 | Fornecedor brasileiro. Sem transferência a confirmar | Página de pagamento em `asaas.com` (só esse domínio é aceito, `hub/views_subscription.py:54-61`) | Nada |
| S9 | CNPJ de empresário individual pode identificar pessoa natural: A AVALIAR pelo jurídico | "A CICA consulta o CNPJ para preparar o ambiente" (`hub/templates/hub/signup.html:10`) | Nada |
| S10 | Órgão público brasileiro | Custo mostrado antes da chamada | A Receita e o Serpro veem a consulta em nome do escritório |
| S11 | O escritório é controlador da própria caixa; a Mewstack passa a guardar anexos | Tela de consentimento do Google ou da Microsoft | Remetentes de e-mail não percebem |
| S12, S13 | Desligados; sem transferência hoje | Nada | Nada |

## 4. Fontes oficiais e componentes próprios (não são suboperadores)

| Item | O que é | Evidência |
|---|---|---|
| ADN / NFS-e Nacional | Fonte oficial. Recebe o CNPJ consultado e o certificado (mTLS). Legado ATIVO em produção; fila por procuração DESLIGADA | `hub/nfse_adn.py`; `fly.toml:27-28`; `config/settings/base.py:455` |
| Portal de Serviços da Receita | Onde o cliente do escritório cadastra a procuração. O CICA só cita o link no e-mail | `hub/procuracao_requests.py:28,57-58` |
| Mewpulse e Mewguard (CRMew, da Mewstack) | Eventos de monitoramento sem CNPJ, CPF, XML nem certificado. Só com URL e token. Se é pessoa jurídica distinta: A CONFIRMAR | `hub/monitoring.py:9-17,20-78`; `config/settings/base.py:480-482` |
| Modelo local de IA | Endpoint próprio da Mewstack (`local_llm_endpoint`, `local_multimodal_endpoint`). Máquina definitiva indefinida (Q-35) | `platform/models.py:41-44`; `docs/planejamento/duvidas-abertas.md:89` |
| Serviço Node de relatórios | Interno (`CICA_REPORTING_URL`). Não aparece nos processos do `fly.toml`; onde roda em produção: A CONFIRMAR | `config/settings/base.py:43`; `fly.toml:36-38` |
| Agente Windows | Roda na rede do escritório, só leitura | `docs/dominio-web-limitacoes-comerciais.md` |
| Postgres antigo da Fly | Máquina parada em 30/09/2026, volume preservado para rollback: guarda uma cópia dos dados daquela data | `DECISOES.md:880`; `VALIDACOES.md:3219-3221` |
| Implantação Cobalchini (Compose local) | Tem fornecedores próprios; fora desta lista | `docs/operations-cobalchini.md` |

## 5. Lacunas entre este inventário e os textos publicados

- O anexo e a política citam "pagamentos, e-mail, hospedagem e monitoramento" e IA (`platform/legal.py:112-119`). Não citam armazenamento de objetos (S4), anti-robô (S6), consulta de CNPJ (S9), Serpro (S10) nem as caixas de e-mail (S11). D-311 manda listar a Cloudflare.
- Cada linha tem estado. A lista publicada precisa dizer o que está ligado no dia, ou o escritório lê promessa de fornecedor que não é usado. Ver `lista-de-inconsistencias.md`, I-05.

## Pendências do responsável

| # | Pergunta | Por que importa | Recomendação |
|---|---|---|---|
| 1 | Quais DPAs e termos de cada fornecedor (Fly, Neon, Tigris, Brevo, Cloudflare, Anthropic, Asaas) estão aceitos ou assinados? | Sem contrato de operador não há suboperador | Levantar os aceites já feitos e guardar a versão e a data |
| 2 | Qual é o tipo de localização do bucket Tigris (global, multi-região, dual, single)? Aceita mudar para single-region no Brasil, se existir? | O padrão é global | Conferir no painel; decidir antes de publicar a lista |
| 3 | O SMTP da Brevo está configurado em produção, e em que região? Qual domínio de envio? | `docs/comercial/proposta-precos.md:68` diz que não; o cadastro e o pedido de procuração dependem dele | Configurar e registrar (Q-29, D-77) |
| 4 | O Copiloto vai usar a Anthropic? Com qual modelo e contrato? Que parte dos anexos pode sair (Q-09)? | Define S7 e o texto de IA | Manter desligado até Q-09 e Q-35 |
| 5 | O Turnstile entra no cadastro? | Entra na lista e na política | Ligar com a lista publicada |
| 6 | A consulta de CNPJ continua na BrasilAPI (sem contrato) ou migra para fonte oficial? | CNPJ de empresário individual | Avaliar com o jurídico |
| 7 | Quando destruir o volume do Postgres antigo da Fly? | É uma cópia de produção fora do ciclo de retenção | Marcar data; destruir só com sua instrução (D-208) |
| 8 | A lista publicada é única ou por módulo ligado? | Triagem e Serpro só existem para quem liga | Por módulo, com data de vigência |
| 9 | Ligar o Sentry? Em qual região? | Entra na lista; `docs/specs/produto-vendavel-plano.md` (E4) planeja ligar | Decidir junto com o custo |
| 10 | O CRMew é a mesma pessoa jurídica da Mewstack? | Muda a classificação do Mewpulse e do Mewguard (seção 4) | Confirmar |
| 11 | Qual mecanismo do art. 33 vale para cada fornecedor estrangeiro (cláusulas-padrão da ANPD ou outro)? | Exigência legal | Parecer do jurídico por fornecedor |
| 12 | Quem é o encarregado e qual o canal de privacidade que a lista indicará? | `privacy_email` vazio por padrão (`platform/models.py:32`) | Preencher antes de publicar |
