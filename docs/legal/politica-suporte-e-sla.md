# Política de suporte e de disponibilidade

> **MINUTA PARA REVISÃO JURÍDICA — não é parecer nem texto vigente**

| Campo | Valor |
|---|---|
| Data | 20/11/2026 |
| Base | árvore de trabalho da branch `feat/produto-vendavel` (parte sem commit). Linhas conferidas em 20/11/2026; podem deslocar |
| Regra desta minuta | só afirma o que o código ou uma decisão sustenta. Tempo, horário, percentual e crédito sem fonte aparecem como **A DEFINIR PELO RESPONSÁVEL**. Nada aqui é oferta enquanto você não aprovar |
| Caminhos | relativos a `src/apps/`; `config/` = `src/config/` |

## 1. Canais e horário

| Canal | Estado hoje | Fonte |
|---|---|---|
| E-mail `suporte@mewstack.com.br` | Definido e exibido no site | `hub/templates/hub/home.html:115`; `DECISOES.md:123`; `docs/planejamento/duvidas-abertas.md:76` |
| Telefone | Campo `support_phone` do console: **A DEFINIR PELO RESPONSÁVEL** | `platform/models.py:31` |
| Horário | Campo `support_hours` do console: **A DEFINIR PELO RESPONSÁVEL**. As páginas legais só o mostram se estiver preenchido | `platform/models.py:33`; `hub/templates/hub/legal.html:11` |
| Privacidade e titulares | Campo `privacy_email`: **A DEFINIR PELO RESPONSÁVEL**. O produto marca a falta como bloqueio de venda | `platform/models.py:32`; `hub/templates/hub/legal.html:12`; `platform/readiness.py:103-109` |
| Dentro do produto | Link "Contatar suporte Mewstack" no Copiloto (desligado em produção) | `intelligence/templates/intelligence/assistant.html:69` |
| Chamado | Não há ferramenta. O único ticket é interno e automático, aberto depois de falha de sincronização do Domínio | `platform/models.py:178-205` |
| Falha de segurança (reporte) | Sem canal publicado; `SECURITY.md` manda criar. Sem `security.txt` | `SECURITY.md:6` |
| Página de status | Não existe | busca em `src/` |
| WhatsApp e portal do cliente final | Fora do escopo (D-309, Q-27) | `DECISOES.md:1928` |

## 2. Severidades e tempos

Os tempos são o que mais falta. Nenhum número abaixo tem fonte.

| Nível | Quando | Exemplos | 1ª resposta | Atualização | Meta de solução |
|---|---|---|---|---|---|
| S1 Crítica | Site fora; dado de um escritório visível a outro; perda de dado; e-CNPJ comprometido | Falha de isolamento; banco indisponível | **A DEFINIR PELO RESPONSÁVEL** | **A DEFINIR PELO RESPONSÁVEL** | **A DEFINIR PELO RESPONSÁVEL** |
| S2 Alta | Módulo crítico parado para um escritório | Coleta de NFS-e parada; e-CNPJ bloqueado; cobrança errada; acesso bloqueado indevidamente | **A DEFINIR PELO RESPONSÁVEL** | **A DEFINIR PELO RESPONSÁVEL** | **A DEFINIR PELO RESPONSÁVEL** |
| S3 Média | Defeito com contorno | Relatório que não baixa; sugestão de acumulador errada | **A DEFINIR PELO RESPONSÁVEL** | **A DEFINIR PELO RESPONSÁVEL** | **A DEFINIR PELO RESPONSÁVEL** |
| S4 Baixa | Dúvida ou pedido | Como usar uma tela; exportação sob pedido; ajuste de cadastro | **A DEFINIR PELO RESPONSÁVEL** | **A DEFINIR PELO RESPONSÁVEL** | **A DEFINIR PELO RESPONSÁVEL** |

Atraso de ADN, Serpro, Receita, Asaas ou Brevo não é defeito da plataforma e não conta no tempo de solução: o suporte mostra o código que a fonte devolveu e espera (`docs/nfse-procuracao.md`, seção Estados).

## 3. O que o suporte faz e o que não faz

| O suporte faz | O suporte NÃO faz |
|---|---|
| Orienta o uso e lê o estado de uma empresa, de uma coleta ou de uma fatura | Emitir NFS-e, guia ou declaração em nome do escritório. Emissão ainda não existe (E7) e, em produção, só com OK explícito por escritório (D-306, `DECISOES.md:1916`). Transmissão e ciência exigem aprovação humana do escritório (`platform/legal.py:57-63`) |
| Abre sessão de suporte com justificativa, quando o problema exige ver o dado (seção 4) | Alterar dado de cliente do escritório (empresa, contato, classificação, carteira, procuração) sem pedido escrito do escritório. Hoje a tecnologia permite (seção 4); esta política não |
| Pede nova verificação de uma coleta e confere o motivo do erro | Pedir ou receber por e-mail ou chat senha, código MFA, token, link de convite, arquivo `.pfx` ou e-CNPJ, XML completo (D-189, `DECISOES.md:799`) |
| Gera a exportação do escritório sob pedido (`office_export`, `hub/offboarding.py:159-202`) | Cadastrar a procuração pelo cliente: é ato do cliente no Portal da Receita (`docs/nfse-procuracao.md`, seção Fluxo) |
| Trata cobrança de contrato manual, com motivo e comprovante auditáveis (Comercial ou Administrador, D-79, `DECISOES.md:129`) | Consertar ou prometer prazo da fonte oficial (ADN, Serpro, Receita) |
| Abre e conduz incidente de segurança (seção 6) | Dar parecer fiscal ou contábil: o produto e a IA não substituem o profissional (`platform/legal.py:53-55`) |
| | Escrever ao cliente do escritório. O pedido de procuração só sai por clique do escritório (`hub/procuracao_requests.py:1-5`) |
| | Reativar o acesso em somente leitura sem pagamento confirmado ou decisão comercial (D-79) |

## 4. Acesso do suporte aos dados do escritório

| Item | Fato | Fonte |
|---|---|---|
| Quem abre | Papéis Suporte ou Desenvolvedor (Administrador passa em qualquer papel) | `platform/views.py:805-807`; `platform/services.py:27-29` |
| Condições | Justificativa de no mínimo 12 caracteres; quem é membro do escritório não abre sessão de suporte nele; escritório com controle central exige concessão ativa do CRMew | `platform/views.py:810-837` |
| Duração | 30 minutos, ou o prazo da concessão; uma sessão aberta por pessoa | `platform/views.py:838-846` |
| Registro | `SupportSession` (justificativa, empresas, modo, validade) e evento de auditoria na abertura e no fim, com modo e duração | `platform/models.py:775-802`; `platform/views.py:847-868,880-889` |
| Alcance | O escritório inteiro ou as empresas da concessão | `hub/views.py:780-789` |
| Modo somente leitura | As ações que gravam consultam `support_can_mutate` e recusam (dezenas de pontos em `hub/views.py`). Que toda rota respeita isso nesse modo não foi conferido aqui | `hub/views.py:802-806`; `platform/models.py:797-802` |
| Modo completo ("Teste completo") | Grava como um membro. É o modo de **qualquer** papel da plataforma enquanto `PLATFORM_DEVELOPER_FULL_ACCESS` for verdadeiro | `platform/services.py:32-36` |
| Situação em produção | O padrão é **verdadeiro**, marcado "TEMPORARY (testing phase)"; o `fly.toml` não o desliga. O comentário de `base.py` diz o contrário ("Production pins this off") | `config/settings/production.py:11-13`; `config/settings/base.py:320-322` |
| Bloqueio de venda | A checagem de prontidão já marca o modo completo como bloqueio. Desligar afeta o suporte atual e depende do seu OK | `platform/readiness.py:50-59`; `docs/specs/produto-vendavel-plano.md:84` |
| Limites mesmo no modo completo | A sessão de suporte não envia nem revoga e-CNPJ, não pede procuração e não abre a Assinatura | `hub/views_procuracao.py:236-242`; `hub/views_subscription.py:81-85` |
| Autorização do escritório | Não há aceite do escritório antes da sessão, salvo escritório com controle central. A "autorização" do anexo (`platform/legal.py:156-161`) hoje é a justificativa interna | `platform/views.py:816-837` |

**PROPOSTA de regra de processo, até o modo completo sair de produção:** (1) sessão no modo completo só com pedido escrito do escritório, citado na justificativa; (2) toda alteração em dado de cliente é registrada no chamado com o que mudou e por quê; (3) as sessões abertas do mês são revisadas pelo responsável pela auditoria; (4) o texto do anexo passa a dizer "justificativa registrada" ou o produto ganha um aceite do escritório.

## 5. Disponibilidade, RTO e restauração

| Item | Fato | Fonte |
|---|---|---|
| Disponibilidade (%) | **A DEFINIR PELO RESPONSÁVEL**. Não há medição, página de status nem alerta que chegue a uma pessoa (Sentry desligado) | `fly.toml:32` |
| Topologia | Uma VM `shared-cpu-1x` de 512 MB para o site e outra para o worker; um Valkey; um endpoint do Neon (0,25 a 1 CU, suspende após 300 s ocioso). "Uma instância por serviço de dados não é alta disponibilidade" | `fly.toml:37-46,64-72`; `infra/valkey/fly.toml`; `DECISOES.md:928`; `VALIDACOES.md:3098` |
| Saúde | A Fly consulta `/api/v1/health/live/` a cada 15 s; `/ready/` (banco e cache) serve a deploy e operação | `fly.toml:53-62` |
| Mudança | Deploy canário; comando de release (migrações) até 10 min. Janela de mudança de até 30 minutos, com backup e retorno preparados | `fly.toml:10-14`; `DECISOES.md:799` |
| **RTO de 4 h** | É o critério aprovado de liberação para restaurar banco e documentos (D-73), reafirmado em D-189. **A restauração ainda não foi medida** | `DECISOES.md:117,799`; `PLANO-MESTRE.md:105` (PC-09); `VALIDACOES.md:5000`; `docs/specs/produto-vendavel-plano.md:87` |
| O que já se restaurou | A migração Fly para Neon de 30/09/2026 (despejo e restauração com contagem e hash idênticos). Não foi ensaio de desastre nem foi cronometrada | `VALIDACOES.md:3213` |
| RPO | **A DEFINIR PELO RESPONSÁVEL**: "definir RPO e janela de medição sem presumir novos números". O histórico do Neon é de 6 h; isso é um fato, não uma promessa | `PLANO-MESTRE.md:63`; `docs/comercial/proposta-precos.md:290` |
| Documentos (bucket) | Restauração e versionamento: não verificados | `fly.toml:29` |
| Retomada após queda de worker, rede ou agente | Critério de 15 minutos (D-73). Não medido | `DECISOES.md:117` |
| Processamento por empresa | Critério de 5 minutos, salvo dependência externa (D-73). Não medido | `DECISOES.md:117` |
| Capacidade | O worker é um só e a fila legada o ocupa por horas; a fila de procuração no mesmo worker atrasaria a legada. Segundo worker: custo adicional ainda não aprovado (D-315) | `docs/capacidade-procuracao.md:24-33`; `DECISOES.md:1954` |
| Dependências sem SLA repassável | ADN, Serpro, Receita (procuração), Asaas, Brevo, Neon, Fly, Tigris | `platform/legal.py:60-62` |
| Aviso prévio de manutenção, crédito e penalidade | **A DEFINIR PELO RESPONSÁVEL**. Sem medição, não prometer | n/a |

## 6. Incidente de segurança com dado pessoal

| Item | Fato |
|---|---|
| Roteiro | `docs/pt-BR/runbooks/resposta-incidentes.md`. Registro em `PersonalDataIncident`, com guarda mínima de 5 anos (`privacy/models.py:183-221`) |
| Quem comunica à ANPD | O **controlador** (o escritório) em 3 dias úteis; a operadora fornece as informações para ele comunicar (Resolução CD/ANPD nº 15/2024, arts. 6º e 9º; resumo de busca de 20/11/2026 em <https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis/comunicacao-de-incidentes-de-seguranca>; conferir o texto). LGPD art. 48 |
| Prazo da Mewstack para avisar o escritório | **A DEFINIR PELO RESPONSÁVEL** (sugestão: "sem demora injustificada", com número no contrato) |
| Contato do encarregado | LGPD art. 41, §1º: identidade e contato divulgados publicamente. **A DEFINIR PELO RESPONSÁVEL** |

## 7. O que o cliente deve fazer para o suporte

| O escritório deve | Por quê |
|---|---|
| Escrever para o e-mail de suporte com: escritório e CNPJ, quem escreve, empresa afetada (CNPJ), tela e horário com fuso, o que esperava e o que viu (texto literal da mensagem), quantas empresas | A tela de erro mostra só o código HTTP; o identificador da requisição vai só no cabeçalho `X-Request-ID` (`hub/templates/hub/error_page.html:13`; `common/middleware.py:25`) |
| Não enviar senha, código MFA, link de convite ou de verificação, `.pfx` ou e-CNPJ, nem XML completo de cliente | O suporte indica outro canal se precisar de arquivo (D-189) |
| Manter ao menos dois administradores (proprietário e administrador) e uma pessoa de cobrança | Sem isso o acesso depende de uma pessoa; a recuperação administrativa de MFA ainda não está pronta (PC-06, `PLANO-MESTRE.md:102`) |
| Manter ativo o segundo fator, recomendado e opcional (D-192) | Protege os acessos seguintes |
| Manter o e-mail de contato de cada empresa-cliente preenchido | Sem e-mail o pedido de procuração não sai (`hub/procuracao_requests.py:96-99`) |
| Avisar antes de trocar ou revogar o e-CNPJ do escritório | O vencimento ou a revogação para a coleta de **todas** as empresas; o produto avisa aos 30, 15, 7, 3 e 1 dia (`hub/procuracao_alerts.py:23`) |
| Autorizar por escrito a sessão de suporte e indicar as empresas | A sessão dura 30 minutos e fica registrada |
| Em atraso de pagamento: pagar a fatura | D-79: 7 dias de carência e depois somente leitura; pagamento confirmado reativa sozinho. A consulta e a exportação deveriam seguir ativas, mas hoje os downloads de NFS-e são recusados nesse estado (`lista-de-inconsistencias.md`, I-04) |
| Pedir a saída por e-mail | Hoje a exportação é um comando interno; entrega por canal seguro. Eliminação ainda não existe (Q-49) |

## Pendências do responsável

| # | Pergunta | Recomendação |
|---|---|---|
| 1 | Qual o horário de atendimento e há telefone? | Só e-mail, em dias úteis, até existir equipe de plantão |
| 2 | Quais os tempos de S1 a S4? | Tempo de 1ª resposta apenas, sem meta de solução, no lançamento |
| 3 | Quando desligar `PLATFORM_DEVELOPER_FULL_ACCESS` em produção? | Antes de abrir para o primeiro escritório pago; até lá vale a regra de processo da seção 4 |
| 4 | O escritório aceita a sessão de suporte antes de ela abrir (consentimento na tela)? | Sim, para escritório sem controle central |
| 5 | Haverá percentual de disponibilidade, crédito ou penalidade? | Não prometer até medir 90 dias |
| 6 | Qual o RPO, e quem autoriza o ensaio de restauração (custo do Neon e do bucket)? | Ensaio em ramificação isolada e cronometrado, com custo informado antes |
| 7 | Página de status e canal de reporte de vulnerabilidade: criar? | Sim, `security.txt` primeiro (sem custo) |
| 8 | Quem é o encarregado e qual o prazo para avisar o escritório de um incidente? | Nome e e-mail públicos antes do lançamento |
| 9 | O contrato manual existente (R$ 200,00, travado) recebe a mesma política? | Sim, com a mesma regra de acesso do suporte |
