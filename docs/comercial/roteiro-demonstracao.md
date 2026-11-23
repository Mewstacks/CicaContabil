# Roteiro de demonstração (20 minutos)

> Uso interno. Não distribuir ao cliente. Não mostrar valor de plano: a grade é proposta e não foi aprovada (`proposta-precos.md`, D-307).

| Campo | Valor |
|---|---|
| Data | 20/11/2026 |
| Público | escritório de contabilidade novo, que usa Domínio (D-308) |
| Base | telas e rotas da árvore de trabalho da branch `feat/produto-vendavel`. Caminhos relativos a `src/apps/` |
| Estado do que se mostra | Coleta por procuração: pronta e testada com transporte falso, **sem nenhuma chamada ao ADN real** e com a fila desligada em produção (`docs/nfse-procuracao.md`, seções "Ligar em produção" e "O que não está provado"). Cobrança: pronta e desligada. IA: desligada em produção |

## 1. Antes de começar (10 minutos antes)

| Passo | Por quê |
|---|---|
| Rodar `python manage.py product_readiness` e ler os bloqueios (e-mail, contatos, termos, planos, Asaas, fila de procuração) | O cadastro e o pedido de procuração dependem do SMTP (`platform/readiness.py:95-109`). Sem ele, o cadastro ao vivo falha |
| Ter **duas** sessões abertas: (a) conta de teste em modo procuração, criada antes, com dados fictícios; (b) `/demo/` ("Iniciar demonstração fictícia") | O modo procuração não existe no escritório de demonstração, que também "não recebe empresas" (`hub/views_roster.py:57`). As notas e a classificação só aparecem na demonstração |
| Na conta (a): **não enviar e-CNPJ real** e só importar planilha com a coleta desligada | Com e-CNPJ e a fila ligados, CNPJs fictícios gerariam consultas reais ao ADN |
| Usar o e-mail do próprio apresentador como contato da empresa de teste | O pedido de procuração **sai de verdade** (Brevo) |
| Conferir a faixa da tela Procurações: "Coleta desligada", "Coleta só em produção", "Coleta em pausa" ou "Coleta ligada" | É o que o cliente verá; diga o estado real (`hub/views_procuracao.py:85-94`) |

## 2. Roteiro

| Min | Tela e rota | O que clicar | O que dizer | O que NÃO prometer |
|---|---|---|---|---|
| 0:00 a 2:00 | Site `/` | Mostrar "Começar teste de 14 dias" | "O CICA junta NFS-e, documentos, prazos e revisões por empresa. Para escritório novo, as notas dos clientes chegam com o e-CNPJ do escritório e uma procuração de cada cliente: ninguém precisa entregar o certificado de cada empresa" | Que o cliente entrega a procuração em um dia; qualquer preço |
| 2:00 a 4:30 | `/comecar/`, depois o e-mail, depois `/comecar/verificar/<token>/` | "Seu nome", "E-mail profissional", "CNPJ do escritório", aceite, **Enviar confirmação**. No e-mail, abrir o link. "Defina sua senha", **Criar ambiente CICA**. Cai em **Primeiros passos** (`/app/configuracao/`) | "Sem cartão, 14 dias contados da senha. O CNPJ preenche o ambiente por consulta pública. São 7 passos e cada um só aparece como feito quando o fato é verdadeiro no banco" (`hub/procuracao_onboarding.py:29-114`) | Cadastro sem e-mail (o link vale 24 h); segundo fator obrigatório (é recomendado, D-192) |
| 4:30 a 7:00 | **Cadastros › Procurações** (`/app/nfse/procuracoes/`) | **Enviar e-CNPJ** (abre a janela com "Arquivo .pfx ou .p12" e "Senha"); fechar sem enviar. Mostrar a faixa "e-CNPJ ausente" | "O CICA abre o arquivo na hora, exige chave privada, validade futura e a mesma raiz de CNPJ do escritório. Guarda cifrado e nunca devolve. Só proprietário e administrador enviam ou revogam. Avisa o vencimento aos 30, 15, 7, 3 e 1 dia" (`hub/office_certificate.py:47-122`; `hub/procuracao_alerts.py:23`) | Que serve e-CNPJ em cartão ou token (precisa do arquivo A1); "segurança total" |
| 7:00 a 10:00 | **Importar carteira** (`/app/nfse/carteira/`) | **Baixar modelo** (colunas `nome;cnpj;email;codigo`); escolher a planilha; **Analisar**; ver "Nova", "Atualiza e-mail", "Já existe", "Com problema", "Sem e-mail"; **Baixar erros**; **Importar N** | "A planilha vira prévia linha a linha antes de gravar. Só entra CNPJ válido. Empresa que já existe só recebe o e-mail; nada é apagado. Até 10 mil linhas e 10 MB. O limite do plano conta por raiz de CNPJ" (`hub/company_roster.py:41,306-420`; `hub/imports.py:41,43`) | Importar do Domínio por aqui (escritório sincronizado pelo Domínio vê "As empresas deste escritório são sincronizadas pelo Domínio") |
| 10:00 a 12:30 | Mesma tela, tabela **Empresas** | **Pedir aos selecionados** (uma empresa, com o e-mail do apresentador); abrir o e-mail recebido; mostrar **Verificar**, **Baixar pendentes** e as abas "Sem procuração", "A verificar", "Em dia", "Com erro" | "O e-mail só sai por clique, nunca sozinho. Pula quem recebeu há menos de 3 dias e manda no máximo 80 por clique. O cliente cadastra a procuração no Portal de Serviços da Receita: outorgado é o CNPJ do escritório, serviço NFS-e. Pode levar até 24 h. O CICA reverifica sozinho a cada 6 h e a empresa vira 'Em dia'" (`hub/procuracao_requests.py:23-24,50-65`; `hub/nfse_procuracao.py:67`) | O menu exato do Portal (não foi verificado, `docs/nfse-procuracao.md`, última seção); o prazo do cliente; o ADN real |
| 12:30 a 16:00 | **`/demo/`**: **NFS-e › Notas** (`/app/nfse/`) | Abrir uma empresa do grupo; mostrar "N para classificar", totais de ISS, CRF, IRRF, INSS e o campo **Acumulador**, já preenchido com a sugestão; **Classificar** | "Aqui os dados são fictícios. A coleta por procuração ainda não tem prova com e-CNPJ real. O modo antigo, com o A1 de cada empresa, já coleta em produção (`VALIDACOES.md:3213`). A sugestão é conferida por uma pessoa" (`hub/templates/hub/nfse_group_rows.html`) | Notas reais chegando ao escritório novo hoje; classificação sem revisão; qualquer percentual de acerto (a meta de 95% se mede no piloto, D-73) |
| 16:00 a 18:00 | `/demo/`: **Baixar** (na barra das notas) e a aba **Exportações** | **Baixar › Pacote com acumuladores › Baixar ZIP** (na demonstração, "arquivos fictícios"); mostrar **XML originais** e **Retenções** (PDF, Excel) | "O pacote leva os XMLs e o manifesto de classificação. A tela ainda diz 'layout de importação em homologação'. O CICA não escreve no Domínio: quem importa é o escritório, pela rotina do Domínio" (`hub/templates/hub/nfse_center.html:54,117-119`) | Importação automática; API oficial do Domínio (não homologada, `docs/dominio-web-limitacoes-comerciais.md`) |
| 18:00 a 20:00 | Conta (a): **Configurações › Assinatura** (`/app/assinatura/`) e **Consumo e contrato** | Mostrar "Plano: Teste CICA", "Cobrança: Mewstack", "Teste até". Fechar com o próximo passo | "Os limites por plano (empresas por raiz de CNPJ, usuários, e-CNPJ) e o aviso a 80% e 100% estão prontos; os valores dependem de aprovação. Ao fim dos 14 dias o escritório fica em somente leitura até contratar" (`platform/limits.py`; `hub/views_subscription.py:136-189`) | Valor; contratar pela tela depois do teste (a correção que libera o clique ainda está sem commit nem deploy, `docs/legal/lista-de-inconsistencias.md` I-04); cobrança automática ligada |

Na conta de teste, a tela Assinatura hoje mostra só o plano do teste e "Nenhuma fatura": o painel "Limites" só aparece com plano que tenha limite e o painel "Planos" só com plano ativo e com preço, e nenhum existe (`hub/views_subscription.py:176-184`; `platform/signup.py:206-214`).

## 3. Objeções comuns

| Objeção | Resposta honesta | Base |
|---|---|---|
| "Preciso do certificado de cada cliente?" | Não, para escritório novo: o do escritório e uma procuração de cada cliente. Sem a procuração a empresa fica "Sem procuração" e nada chega. Escritório que já usa o A1 por empresa segue como está | D-304, D-305 |
| "Quanto custa?" | O preço ainda não foi aprovado. O teste é de 14 dias, sem cartão | D-307; `proposta-precos.md` |
| "É seguro entregar o e-CNPJ do escritório?" | Fica cifrado, não volta para a tela, só proprietário e administrador mexem, e cada envio e revogação é auditado. Os riscos que restam: o suporte da plataforma hoje pode gravar nas sessões de suporte (modo temporário de teste), e a restauração de desastre não foi medida | `hub/models.py:378-410`; `config/settings/production.py:11-13`; `PLANO-MESTRE.md:105` |
| "E se o cliente não outorgar a procuração?" | Fica "Sem procuração", reverificada a cada 6 h. O CICA pede por e-mail, por clique, e baixa a lista de pendentes. Não coleta sem procuração | `docs/nfse-procuracao.md`, seção Estados |
| "Quanto tempo até a primeira nota?" | A procuração pode levar até 24 h para valer, mais o tempo do cliente. Depois, a coleta de cada empresa roda de hora em hora. Medida real: ainda não existe | `docs/capacidade-procuracao.md` |
| "Funciona com o Domínio?" | O Domínio é o ERP de lançamento. O CICA lê só (agente local) e gera o pacote de NFS-e; não escreve no Domínio. A importação do pacote é do escritório | D-308; `docs/dominio-web-limitacoes-comerciais.md` |
| "Vocês emitem nota?" | Ainda não. Hoje é coleta, conferência e classificação. Emissão está planejada e, em produção, só com seu OK por escritório | D-306 |
| "A IA lê meus documentos?" | O Copiloto está desligado em produção. Quando ligar: modelo local como padrão, reserva externa só com aprovação e com CPF, CNPJ e e-mail mascarados | `docs/comercial/proposta-precos.md:32`; `intelligence/gateway.py:56-70` |
| "Onde ficam os dados? E a LGPD?" | Aplicação e banco em São Paulo (Fly e Neon). Os arquivos ficam num bucket cujo tipo de localização ainda precisa ser confirmado. A lista de fornecedores e os prazos de retenção estão em minuta, ainda sem versão publicada | `docs/legal/suboperadores.md`; `docs/legal/retencao-por-artefato.md` |
| "Posso exportar tudo e sair?" | Exportação existe, sob pedido, em ZIP com manifesto. A eliminação dos dados não é executada ainda: depende de decisão e de revisão jurídica | `hub/offboarding.py:15-17`; Q-49 |
| "Posso exigir segundo fator da minha equipe?" | Não. O segundo fator é opcional e recomendado, por usuário. O campo `require_mfa` existe, mas nenhum código o lê | D-192; `hub/models.py:76` |
| "Tem SLA e suporte?" | Suporte por e-mail. Tempo de resposta e disponibilidade ainda não estão definidos. A meta de restaurar em 4 h é critério de liberação e não foi medida | `docs/legal/politica-suporte-e-sla.md` |
| "Meu cliente também usa o sistema?" | Não. Não há portal nem WhatsApp para o cliente do escritório | D-309 |
| "Quantas empresas aguenta?" | O limite real é o ritmo do ADN (uma consulta por segundo por e-CNPJ) e a fila de coleta, que hoje tem um só processador. A capacidade cresce conforme a carga medida no piloto. Não cite o custo interno | `docs/capacidade-procuracao.md`; D-315 |

## 4. Nunca dizer

Preço ou desconto. "Importa direto no Domínio." "Emitimos NFS-e." "A IA analisa seus documentos." "Tudo fica no Brasil." Percentual de disponibilidade, tempo de restauração ou de resposta. "Sem risco." "O cliente do escritório não precisa fazer nada."

## Pendências do responsável

| # | Pergunta | Recomendação |
|---|---|---|
| 1 | Quem cria e mantém a conta de apresentação em produção, e com que dados fictícios? | Conta própria da Mewstack, sem e-CNPJ e sem cliente real |
| 2 | O SMTP da Brevo e o domínio de envio serão configurados antes da primeira demonstração com cadastro ao vivo? | Sim; senão use a conta pré-criada |
| 3 | O piloto da procuração (e-CNPJ e cliente reais) acontece antes ou depois da primeira demonstração? | Antes; sem ele, o item "notas chegando" é só demonstração fictícia |
| 4 | Fazer o commit e o deploy da exceção que libera contratar e pagar em carência (I-04) antes de demonstrar a conversão? | Sim |
| 5 | Qual preço, ou faixa de preço, pode ser dito ao prospect? | Nenhum até aprovar D-307 |
| 6 | O Portal de Serviços tem caminho de menu estável para o cliente? | Conferir com uma procuração real no piloto e anotar aqui |
