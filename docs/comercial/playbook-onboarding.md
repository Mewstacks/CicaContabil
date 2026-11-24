# Playbook de onboarding: do primeiro dia ao primeiro resultado

> Uso interno da Mewstack. Vale para escritório criado depois de D-304 (modo procuração). O escritório que usa o A1 de cada empresa segue o roteiro antigo.

| Campo | Valor |
|---|---|
| Data | 20/11/2026 |
| Resultado buscado | "Receber a primeira NFS-e": o passo 5 do assistente só fica feito quando existe uma NFS-e do escritório no banco (`hub/procuracao_onboarding.py:51,84-98`) |
| Fonte principal | `docs/nfse-procuracao.md` (D-304, D-305), Manual dos Contribuintes do ADN v1.1 de 03/11/2026 |
| Estado | **A coleta por procuração nunca rodou contra o ADN real** e a fila está desligada em produção (`docs/nfse-procuracao.md`, seções "Ligar em produção" e "O que não está provado"). Este playbook é o roteiro do piloto e dos escritórios seguintes |
| Caminhos | relativos a `src/apps/`; `config/` = `src/config/` |

## 1. Gates da Mewstack (sem eles, não onboardar escritório pagante)

| Gate | Estado em 20/11/2026 | Fonte |
|---|---|---|
| Piloto com e-CNPJ real e ao menos um cliente com procuração outorgada | Pendente (a produção restrita do ADN não tem cadastro de procuração) | `docs/specs/produto-vendavel.md`, seção Fatos de base; `docs/nfse-procuracao.md` |
| Fila ligada: `NFSE_PROCURACAO_SYNC_ENABLED=true` e `NFSE_ADN_ENVIRONMENT=production`; a tela Procurações mostra "Coleta ligada" | Desligada por padrão | `config/settings/base.py:455`; `hub/views_procuracao.py:85-94` |
| Capacidade: decidir o segundo worker (+R$ 36,32 por mês) | Não aplicado; sem ele a fila nova atrasaria a coleta do escritório atual | D-315 (`DECISOES.md:1954`); `docs/capacidade-procuracao.md:24-33` |
| SMTP da Brevo e domínio de envio configurados | Não configurado segundo `docs/comercial/proposta-precos.md:68` | `platform/readiness.py:95-101`; Q-29 |
| Contatos de suporte e privacidade preenchidos; termos sem a palavra "draft" | Pendente | `platform/readiness.py:103-118` |
| Suporte da plataforma em somente leitura (`PLATFORM_DEVELOPER_FULL_ACCESS=false`) | Verdadeiro por padrão em produção | `config/settings/production.py:11-13`; `platform/readiness.py:50-59` |
| Contratar e pagar em carência pela tela | Corrigido na árvore de trabalho, sem commit nem deploy | `hub/views.py:1114-1126`; `docs/legal/lista-de-inconsistencias.md`, I-04 (T-2, T-3) |
| Fotografia do banco antes e depois do deploy (`legacy_snapshot`, comparação idêntica) | Procedimento descrito | `docs/nfse-procuracao.md`, seção "Ligar em produção" |

## 2. Antes do dia 1: o que o escritório prepara

| Item | Detalhe | Fonte |
|---|---|---|
| e-CNPJ A1 | Arquivo `.pfx` ou `.p12` com senha, válido hoje, com a **mesma raiz de CNPJ** do escritório, até 512 KB. Certificado em cartão ou token (A3) não serve: não há arquivo | `hub/office_certificate.py:62-80`; `hub/views_procuracao.py:54,257-260` |
| Duas pessoas com papel de proprietário ou administrador | Só elas enviam, trocam e revogam o e-CNPJ | `hub/views_procuracao.py:69` |
| Planilha da carteira | Colunas `nome;cnpj;email;codigo`, `.csv` ou `.xlsx`, até 10 MB e 10 mil linhas. O e-mail de cada cliente é o destino do pedido de procuração. O código Domínio é opcional | `hub/company_roster.py:41`; `hub/imports.py:41,43` |
| Aviso aos clientes | O pedido chega em nome do escritório, mas enviado pela plataforma da Mewstack: "Procuração para {escritório} acessar as NFS-e". Quem cadastra é o responsável legal da empresa, no Portal de Serviços da Receita | `hub/procuracao_requests.py:50-65` |
| Quem do cliente cadastra e como se autentica no Portal | Confirmar com cada cliente. O caminho exato do menu não foi verificado | `docs/nfse-procuracao.md`, última seção |
| Quem recebe os avisos do produto | Proprietário e administradores recebem alerta de e-CNPJ a vencer e de procuração perdida | `hub/procuracao_alerts.py:23-60` |

## 3. Linha do tempo

Os dias são ilustrativos. As únicas fontes de prazo são o "até 24 h" da procuração e a cadência da fila (`docs/nfse-procuracao.md`, seções Fluxo e Ritmo). Nenhuma meta foi aprovada (seção 7).

| Quando | Quem | Onde | O que fazer | Pronto quando |
|---|---|---|---|---|
| Dia 0 | Responsável pelo CICA | Gates da seção 1 | Conferir os gates e `python manage.py product_readiness` | Sem bloqueio |
| Dia 1 | Proprietário | `/comecar/` | Preencher nome, e-mail, CNPJ, aceite; abrir o link do e-mail (vale 24 h); definir a senha. O teste de 14 dias começa aqui | Cai em **Primeiros passos**; mensagem "Seus 14 dias grátis começaram agora" (`hub/views.py:571`; `platform/signup.py:193-195`) |
| Dia 1 | Proprietário ou administrador | **Primeiros passos › Confirme a identificação** | Conferir razão social e CNPJ e corrigir o que estiver errado: o CNPJ pode ser editado aqui | Passo 1, que já nasce feito porque o CNPJ vem do cadastro, confere com a realidade (`hub/forms.py:219-246`; `hub/procuracao_onboarding.py:59-63`) |
| Dia 1 | Proprietário ou administrador | **Cadastros › Procurações › Enviar e-CNPJ** | Enviar o arquivo e a senha | Faixa "e-CNPJ válido", com CNPJ e dias restantes; passo 2 feito |
| Dia 1 | Quem mexe na carteira | **Importar carteira** (`/app/nfse/carteira/`) | **Baixar modelo**, preencher, **Analisar**, corrigir o que a prévia marcar, **Importar N**. A confirmação cria uma linha de coleta por empresa | Passo 3 feito; empresas em "A verificar" (`hub/views_roster.py:190-191`) |
| Dia 1 | Proprietário, administrador, gestor ou operador | **Procurações › Pedir a todos sem procuração** | Cada clique manda até 80 e-mails, pula quem recebeu há menos de 3 dias e quem está sem e-mail. Repetir o clique para o resto | Passo 4 feito com o primeiro pedido enviado |
| Dia 1 a 3 | Cliente do escritório | Portal de Serviços da Receita | Cadastrar a procuração: outorgado é o CNPJ do escritório, serviço NFS-e, validade a critério da empresa. Pode levar até 24 h para valer | Empresa vira "Em dia" na próxima verificação (a cada 6 h) ou ao clicar **Verificar** |
| Dia 2 a 5 | Escritório | **NFS-e › Notas** | Ver as notas. Cada empresa em dia é consultada a cada 1 h, até 2 páginas (100 notas) por vez; empresa sem notas há 7 dias, a cada 24 h | Passo 5 feito: existe a primeira NFS-e |
| Dia 3 a 7 | Contador | **NFS-e › Notas** | Conferir a sugestão do campo Acumulador e **Classificar**; baixar o **Pacote Domínio** das notas classificadas | Notas classificadas; pacote baixado |
| Dia 7 | Proprietário | **Procurações › Baixar pendentes** | Cobrar por outro canal quem não outorgou. Convidar a equipe e ativar o segundo fator (passos recomendados) | Lista de pendentes tratada |
| Dia 13 | Responsável pelo CICA | Contato com o escritório | Avisar que o teste termina no 14º dia: o escritório fica em somente leitura até contratar | Escritório ciente; tratamento comercial combinado |

## 4. Checklist do responsável pelo CICA

| Quando | Conferir | Como |
|---|---|---|
| Dia 0 | Gates, `product_readiness`, versão dos termos | Seção 1 |
| Dia 1 | e-CNPJ aceito e coleta ligada | Faixas da tela Procurações; evento `hub.office_certificate.uploaded` na auditoria (`hub/office_certificate.py:107-114`) |
| Dia 1 | Carteira: empresas sem e-mail e sem código Domínio | Notas "Sem e-mail" da prévia; coluna Integrações em **Cadastros › Empresas** |
| Dia 2 | Quantas empresas saíram de "A verificar"; nenhuma em "Com erro" | Abas da tela Procurações (`hub/views_procuracao.py:56-62`) |
| Dia 3 a 5 | Empresas "Em dia" com notas maiores que zero | Coluna "Notas" da tabela |
| Semana 1 | Fila atrasada por mais de 6 h | Aviso `procuracao.lane_stalled` no log (`hub/procuracao_alerts.py:25`) |
| Semana 1 | Procuração perdida | Aviso no sino, só ao proprietário e administradores |
| Dia 13 | Aviso de fim do teste | Seção 3 |

## 5. Erros comuns

| Sintoma ou mensagem | Causa | O que fazer | Escalar quando |
|---|---|---|---|
| Empresa em **Sem procuração** (ADN devolve E2245) | O cliente não cadastrou, ainda não valeu, ou cadastrou com dado errado | Conferir com o cliente: outorgado é o CNPJ do escritório e o serviço é NFS-e. Esperar até 24 h; clicar **Verificar** | Mais de 48 h e o cliente confirma que cadastrou |
| "O CNPJ do certificado não é o do escritório." | Certificado de **outra raiz de CNPJ** (cliente, holding, outro grupo), ou CNPJ errado no cadastro | Enviar o e-CNPJ da mesma raiz. Corrigir o CNPJ em **Primeiros passos › Confirme a identificação** se foi digitado errado | O CNPJ certo continua recusado |
| Pedido de procuração não sai: "N sem e-mail"; na prévia, "Sem e-mail" | **E-mail do cliente ausente** | Preencher o e-mail na planilha (a empresa que já existe recebe o e-mail: "Atualiza e-mail") ou em Empresas; usar **Baixar pendentes** para cobrar por outro canal | Nunca: é do escritório |
| "Não foi possível abrir o arquivo com esta senha." | Senha errada, ou arquivo com cifra que o servidor não lê | Conferir a senha; reexportar o A1 | A senha certa não abre |
| "Este e-CNPJ está vencido." ou "ainda não é válido." | Certificado fora da validade | Renovar e usar **Trocar e-CNPJ** | Nunca |
| "O arquivo é maior que o esperado para um e-CNPJ A1." | Arquivo errado (limite de 512 KB) | Enviar o `.pfx` do A1 | Nunca |
| "Informe o CNPJ do escritório antes de enviar o e-CNPJ." ou "…antes de pedir procurações." | Cadastro sem CNPJ | Passo "Confirmar escritório" | Nunca |
| "Faltam as colunas nome e cnpj na primeira linha.", "O arquivo não possui linhas para importar.", "Envie um arquivo .csv ou .xlsx." | Planilha fora do modelo | Usar **Baixar modelo** | Nunca |
| Linha "Com problema": "Informe o CNPJ", "Dígitos do CNPJ não conferem", "CNPJ repetido na linha N", "Código repetido…", "Nome acima de 180 caracteres" | Dado da planilha | Corrigir e reenviar; **Baixar erros** lista tudo | Nunca |
| "Limite de empresas do plano" | O plano tem limite por raiz de CNPJ; filial não conta | Reduzir a carteira ou tratar o plano com o comercial | Sempre (comercial) |
| Importação bloqueada: "As empresas deste escritório são sincronizadas pelo Domínio." ou "…controladas pelo controle central da Mewstack." ou "Seu perfil não altera a carteira." | Escritório com agente Domínio ou controle central, ou papel sem permissão | Usar a sincronização do Domínio; pedir o papel adequado | Escritório que devia importar e não consegue |
| Faixa "Coleta desligada" ou "Coleta só em produção" | A fila é desligada pela Mewstack ou o ambiente do ADN não é produção | Nada a fazer no escritório | Sempre: é gate da seção 1 |
| Faixa "Coleta em pausa" | O ADN limitou a taxa (429): pausa de 60 s | Esperar | A pausa se repete por mais de uma hora |
| Empresa em **Com erro**, com E2243, E2244, E2246 ou E2247 | Consulta recusada pelo ADN por configuração | Ler a mensagem da linha | Sempre: precisa de análise |
| **Com erro** por E2210 a E2213, ou 401 e 403 | Problema do certificado. Nos códigos E2210 a E2213 o escritório inteiro fica parado por 60 minutos (`hub/nfse_procuracao.py:66,74`) | Conferir validade e cadeia do e-CNPJ; esperar 60 minutos | Repetiu depois do reenvio |
| Faixa "Bloqueado por alguns minutos" | ADN devolveu 495: e-CNPJ em quarentena por 15 minutos | Esperar; não reenviar o arquivo | Mais de 1 hora |
| "Em dia" e nenhuma nota | ADN respondeu 404 E2220 ou E2230: não há notas novas. Sem notas há 7 dias, a consulta passa a diária | Normal | Nunca |
| Empresa que estava "Em dia" volta a "Sem procuração" | Cliente revogou ou a validade escolhida acabou; o proprietário e os administradores recebem aviso | Pedir de novo | Muitas empresas ao mesmo tempo |
| "O e-mail não saiu. Confira a configuração de envio." | SMTP da Brevo fora ou sem configuração | Nada no escritório | Sempre |
| Cliente diz que não recebeu o e-mail | Caixa de spam, endereço errado, remetente desconhecido | Pedir para procurar "Procuração para…"; conferir o endereço | Vários clientes do mesmo domínio |
| "Falha inesperada na coleta por procuração. Solicite suporte." | Erro não previsto na coleta da empresa | Nada | Sempre |
| e-CNPJ "vence em breve" (30 dias) | Aviso preventivo; o vencimento para a coleta de **todas** as empresas | Renovar e **Trocar e-CNPJ** antes da data | Nunca |

Fontes das mensagens: `hub/office_certificate.py:61-80`; `hub/views_procuracao.py:85-94,254,258-260`; `hub/company_roster.py:201,204,228,276-420`; `hub/views_roster.py:53-68`; `hub/procuracao_requests.py:80,98,123`; `hub/nfse_procuracao.py:63-79,549,590`; `hub/templates/hub/nfse_procuracao.html:19`; `docs/nfse-procuracao.md`, seção Estados.

## 6. Quando escalar

| Gatilho | Para quem | Tempo |
|---|---|---|
| Qualquer linha "Sempre" da seção 5 | Suporte (`suporte@mewstack.com.br`), depois desenvolvimento | **A DEFINIR PELO RESPONSÁVEL** (S2 em `docs/legal/politica-suporte-e-sla.md`) |
| Suspeita de dado de um escritório visto por outro | S1 imediato e runbook de incidente | **A DEFINIR PELO RESPONSÁVEL** |
| e-CNPJ enviado por engano ou comprometido | O escritório clica **Revogar e-CNPJ** (a coleta do escritório para) e troca o certificado na emissora; avisar o suporte | Imediato |
| Cobrança, plano ou limite | Comercial | **A DEFINIR PELO RESPONSÁVEL** |
| Pedido de saída ou de exportação | Suporte, com pedido por escrito | `docs/legal/retencao-por-artefato.md`, R-10 |

## 7. O que registrar em cada onboarding

Data do cadastro, do envio do e-CNPJ e da importação; empresas importadas e sem e-mail; pedidos enviados; empresas "Em dia" no dia 3 e no dia 7; data da primeira NFS-e; notas classificadas; pacote baixado; erros da seção 5 que apareceram. Nenhuma meta de tempo ou de percentual foi aprovada.

## Pendências do responsável

| # | Pergunta | Recomendação |
|---|---|---|
| 1 | Qual a meta de tempo do cadastro à primeira NFS-e e de percentual de empresas "Em dia" no dia 7? | Medir no piloto e só então fixar |
| 2 | Quem é o responsável pelo CICA em cada onboarding e qual o tempo de resposta (S2)? | Uma pessoa nomeada, com substituto |
| 3 | Quem aprova o texto de aviso que o escritório manda aos clientes antes do pedido? | Modelo curto, assinado pelo escritório |
| 4 | A procuração de uma matriz vale para as filiais, ou cada CNPJ outorga o seu? E o MEI? | Verificar no piloto e anotar aqui |
| 5 | Qual o caminho de menu e a autenticação do cliente no Portal de Serviços? | Anotar do piloto, com data |
| 6 | Os 14 dias de teste bastam, já que a procuração depende do cliente? | Rever depois do piloto; `proposta-precos.md` sugere contar do envio do e-CNPJ, o que muda D-79 |
| 7 | Quem e quando faz o piloto (Fedrizzi é o candidato)? | Antes do primeiro escritório novo |
| 8 | O commit e o deploy da exceção de carência (I-04) entram antes do piloto? | Sim, porque o primeiro teste que termina bate nela |
