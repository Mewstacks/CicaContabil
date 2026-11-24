# Proposta de preços do CICA

> **PROPOSTA — não aprovada, nada publicado nem cobrado.**

| Campo | Valor |
|---|---|
| Data | 20/11/2026. Preços de terceiros lidos nesta data; câmbio PTAX de 19/11/2026 |
| Origem | D-307: Claude pesquisa e propõe, o responsável aprova. Entrega do épico E9 (`docs/specs/produto-vendavel-plano.md`) |
| Efeito | Nenhum. Não cria `Plan`, não muda contrato, página de preços, cobrança nem o legado (D-303, regras L1 a L5) |
| Método | Páginas públicas; `flyctl` e Neon só em leitura. Nenhuma conta criada, API paga chamada, e-mail enviado ou página publicada |
| Legenda | **[F#]** fonte da seção 7 · **HIP** = HIPÓTESE, sempre com a conta mostrada · "sob consulta" = preço não publicado pelo fornecedor |

## 1. Status e premissas

| Plano (nome provisório) | Mensal | Anual (10 mensalidades) | Empresas | Usuários | IA incluída/mês | Margem de contribuição no arquétipo |
|---|---:|---:|---:|---:|---:|---|
| A | R$ 199 | R$ 1.990 | 30 | 3 | R$ 20 | 84,9% (20 empresas) |
| B | R$ 499 | R$ 4.990 | 120 | 8 | R$ 55 | 80,0% (100 empresas) |
| C | R$ 1.199 | R$ 11.990 | 350 | 20 | R$ 160 | 80,7% (500 empresas, com adicionais) |

Custo fixo da plataforma: **R$ 196,25/mês hoje** (medido) e **R$ 591,20/mês na operação comercial** (HIP). Quatro tenants A, ou dois B, pagam essa infraestrutura. Serpro é repasse sem margem (D-109) e fica fora da conta.

**Premissas que dependem do dono** (nada abaixo foi confirmado por ele):

1. Aprovar os valores da seção 4. Antes disso nada vale e a página de preços não exibe número (E6).
2. Regime e enquadramento tributário da Mewstack. Usei 6,00% (Simples, Anexo III, 1ª faixa) como HIP [F18].
3. Tarifas Asaas da conta real (Menu do usuário > Taxas). Usei a página pública [F10].
4. Faixa e contrato Serpro da conta central. Usei a faixa 1 como teto de repasse [F12].
5. Câmbio R$ 5,8889 (PTAX 19/11) + IOF de 3,5% no cartão internacional (HIP, só fonte secundária) = R$ 6,0950 por US$ [F15, F16].
6. Custos fixos novos (worker extra, Sentry, Brevo) só com OK e valor exato (seção 2.2).
7. Uso dos arquétipos (empresas, documentos, perguntas de IA, e-mails) é HIP, calibrado com uma medição da produção atual (seção 2.4).
8. O Copiloto está **desligado em produção** (`copilot_available_for_offices = false`, limites Claude = 0, `trial_ai_included_requests = 0`, 20/11/2026). A franquia de IA só vale quando o dono o ligar.
9. Custo humano (suporte, jurídico, comercial) não está no modelo.

Compatibilidade com o já decidido: D-109 trocou a estrutura por módulos e tokens por **pacotes de capacidade** (usuários ativos e raízes de CNPJ ativas, filial não conta), **franquia de IA em reais** com teto mensal e **Serpro sem margem**. Por isso esta proposta não usa token CICA (R$ 0,05) nem preço por módulo, e não reaproveita os valores antigos (R$ 249, R$ 169 etc.). Esses valores ainda existem no template órfão `src/apps/hub/templates/hub/plan_simulator.html`, sem view que o use. D-79 vale integralmente (seção 4.5). Em produção existe **um** contrato ativo, de R$ 200,00/mês com valor travado, e nenhum `Plan` cadastrado.

## 2. Custo por escritório (tenant)

### 2.1 Tarifas usadas

| Serviço | Tarifa lida em 20/11/2026 | Fonte |
|---|---|---|
| Fly.io | shared-cpu-1x 256 MB US$ 2,19/mês (Ashburn); RAM extra US$ 6,00/GB; **gru = 1,615×**; volume US$ 0,15/GB; snapshot US$ 0,08/GB (10 GB grátis); saída América do Sul US$ 0,04/GB; IPv4 compartilhado grátis | F1, F2, F3 |
| VM em gru (cálculo) | 512 MB: (2,19 + 0,25 × 6,00) × 1,615 = **US$ 5,96 = R$ 36,32**; 256 MB: US$ 3,54 = R$ 21,56; 1 GB: US$ 10,80 = R$ 65,85 | F1 |
| Neon (Launch, aws-sa-east-1) | US$ 0,106/CU-h; US$ 0,35/GB-mês; histórico de restauração US$ 0,20/GB-mês; 500 GB de saída inclusos; sem mínimo mensal | F4, F5 |
| Tigris (o repo usa: `production.py` lê `BUCKET_NAME` e `AWS_ENDPOINT_URL_S3`; `deploy-fly.md` manda criar bucket Tigris; os segredos existem no Fly, o endpoint não foi conferido) | US$ 0,02/GB-mês; Classe A US$ 0,005/mil; Classe B US$ 0,0005/mil; saída grátis; 5 GB grátis | F8 |
| Brevo | transacional (SMTP/API) em todos os planos; Free 300 e-mails/dia; Starter R$ 40/mês com 5.000 e-mails, +R$ 36 a cada faixa de 5.000 (lista em BRL, não conversão de US$ 9) | F9 |
| Asaas | Pix R$ 1,59; boleto R$ 1,59; cartão à vista R$ 0,49 + 2,99% (2 a 6x: 3,49%); emissão de NFS-e pelo Asaas R$ 0,49/nota. Promoção de 3 meses para conta nova: Pix e boleto R$ 0,79, cartão 1,99% | F10 |
| Serpro Integra Contador | 8 faixas por consumo mensal. Consulta: R$ 0,24 / 0,21 / 0,18 / 0,16 / 0,14 / 0,11 / 0,09 / 0,06 (limites 300, 1.000, 3.000, 7.000, 15.000, 23.000, 30.000, acima). Emissão: 0,32 / 0,29 / 0,26 / 0,22 / 0,19 / 0,16 / 0,12 / 0,08 (500, 5.000, 10.000, 15.000, 25.000, 35.000, 50.000, acima). Declaração: 0,40 / 0,36 / 0,32 / 0,28 / 0,24 / 0,20 / 0,16 / 0,12 (100, 500, 1.000, 3.000, 5.000, 8.000, 10.000, acima). Sem mensalidade na página | F12, F13 |
| Claude `claude-sonnet-5` (o modelo do repo: `gateway.py`, `verify_claude_*`) | US$ 2/MTok entrada, US$ 10/MTok saída, cache hit US$ 0,20, Batch −50%. O preço de introdução virou padrão; o aumento para US$ 3/15 não ocorrerá. Haiku 5.5: US$ 0,10 / 0,50 | F14 |
| Sentry | Team US$ 29/mês (US$ 26 no anual) | F17 |

**Divergências.** Asaas: a página de preços de 20/11/2026 mostra Pix e boleto a R$ 1,59 (riscado, valor padrão) e R$ 0,79 (destaque, 3 meses); o blog do Asaas, atualizado em 23/04/2026, diz R$ 0,99 nos 3 primeiros meses e R$ 1,99 depois, e buscadores ainda indexam R$ 1,99 e páginas de parceiros com R$ 1,79 ou Pix grátis [F10, F11]. **Vale a página de 20/11/2026** (mais recente, do próprio Asaas). Confirmar na conta do dono. Fly: `docs.fly.io` não carrega a tabela regional; cruzei com `fly.io/pricing.md`, que traz a linha de São Paulo [F1, F2]. `HOSPEDAGEM.md` (Oracle, R$ 227/mês) descreve uma alternativa não adotada; a produção roda em Fly + Neon e usei os custos desses dois.

### 2.2 Custo fixo da plataforma

| Item | Hoje (medido) | Operação comercial (HIP) | Nota |
|---|---:|---:|---|
| Fly web 512 MB | R$ 36,32 | R$ 36,32 | `fly.toml`, 1 máquina `web` ativa [F7] |
| Fly worker 512 MB | R$ 36,32 | R$ 36,32 | Celery + beat, `--concurrency=1` |
| Fly worker 2 (fila de procuração) | — | R$ 36,32 | gate de custo do E5 |
| Fly Valkey 256 MB + volume 1 GB | R$ 22,47 | R$ 22,47 | `infra/valkey/fly.toml` |
| Fly máquina parada, snapshots, saída | R$ 4,27 | R$ 4,27 | HIP: rootfs 2 GB, 10 GB de saída |
| Neon compute | R$ 95,65 (148,1 CU-h em nov, extrapolado de 97,8 CU-h em 1 a 20/11; out: 116,4 CU-h) | R$ 235,82 | operação: 0,5 CU médio = 365 CU-h (HIP). 1 CU = R$ 471,63; 2 CU = R$ 943,26 |
| Neon armazenamento e histórico | R$ 1,22 | R$ 2,93 | 0,56 GB hoje; 1 GB na operação; histórico de 6 h para 7 dias custa ~US$ 0,13 |
| Tigris | ≈ R$ 0 | ≈ R$ 0 | HIP: não medi o bucket; os 5 GB iniciais são grátis |
| Sentry Team | desligado | R$ 176,76 | E4 liga o Sentry |
| Brevo Starter | não configurado (D-77, D-78; sem segredo SMTP no Fly) | R$ 40,00 | o Free (300/dia) pode travar lotes de "Pedir procuração" (80 por clique) |
| **Total** | **R$ 196,25** (Fly 99,38 + Neon 96,87) | **R$ 591,20** | diferença **+R$ 394,95/mês** |

Medições: produção no Neon tem plano `launch_v3`, 770,9 MB de banco, 4 organizações, 218 empresas ativas e 10 usuários ativos [F5, F6]. Em 09/10/2026 a VM web tinha ~27 MB livres (nota operacional): o degrau de capacidade da seção 2.3 é a variável mais incerta.

**Decisões de custo com valor exato** (regra de custo do projeto; nada foi aplicado):

| Mudança | Valor/mês | Quando |
|---|---:|---|
| Worker 2 em gru (512 MB) | +R$ 36,32 (US$ 5,96) | só após a medição de E5 |
| Sidecar IBS/CBS (1 GB, gru) | +R$ 65,85 (US$ 10,80), HIP | gate do E7 |
| Sentry Team | +R$ 176,76 (US$ 29) | entrada do 1º tenant pago |
| Brevo Starter | +R$ 40,00 | entrada do 1º tenant pago |
| Neon de 148 CU-h (hoje) para 365 CU-h (0,5 CU médio) | +R$ 140,17 | conforme carga medida |

### 2.3 Custo variável (fórmula)

```
custo direto do tenant (R$/mês), E = empresas ativas (raízes), VM512 = R$ 36,32
  = E ÷ 150 × VM512                                         capacidade Fly      = R$ 0,242 por empresa (HIP: 1 VM por 150)
  + E × 0,3 CU-h × US$ 0,106 × 6,0950                       Neon compute        = R$ 0,194 por empresa (HIP)
  + docs acumulados × 10,95 KB × US$ 0,35/GB × 6,0950       Neon armazenamento  (medido: 412.041.216 B ÷ 37.620 docs)
  + E × 2 MB × 12 meses × US$ 0,02/GB × 6,0950              Tigris (HIP)
  + e-mails × R$ 0,0072                                     Brevo (R$ 36 ÷ 5.000)
  + perguntas × (3.000 × US$ 2 + 900 × US$ 10) ÷ 10^6 × 6,0950 = perguntas × R$ 0,0914   Claude
  + 0,60 × R$ 1,59 + 0,25 × R$ 1,59 + 0,15 × (R$ 0,49 + 2,99% × preço)                     Asaas (mix HIP)
Serpro: repasse, fora do custo.   NFS-e do ADN: sem tarifa no manual v1.1 (HIP), só compute e armazenamento.
```

Notas: uma pergunta de IA = 3.000 tokens de entrada e 900 de saída (`max_tokens` 900 em `gateway.py`; mesma conta de `precificacao-e-cotas-ia.md`, que deu R$ 0,078 com PTAX 5,1696 e sem IOF). Com Haiku 5.5 a pergunta custaria US$ 0,00075 = R$ 0,0046 (20× menos), qualidade não avaliada (HIP). O dólar subiu 6,8% de 09/11 a 19/11 (5,5146 para 5,8889) [F15]; cada +10% de câmbio tira 1,4 a 1,9 ponto de margem.

### 2.4 Arquétipos (HIP) e custo por tenant

| | P (pequeno) | M (médio) | G (grande) |
|---|---:|---:|---:|
| Empresas ativas (raízes) | 20 | 100 | 500 |
| Usuários ativos | 3 | 8 | 25 |
| NFS-e/mês (20 por empresa) | 400 | 2.000 | 10.000 |
| Perguntas de IA/mês (66 por usuário = 3 por dia útil) | 198 | 528 | 1.650 |
| E-mails/mês (5 por empresa) | 100 | 500 | 2.500 |
| Serpro/mês (4 consultas + 1 emissão por empresa) | 80 + 20 | 400 + 100 | 2.000 + 500 |

Âncora dos 20 documentos por empresa: medi 2.152 a 2.617 NFS-e/mês (jun a out) em 58 a 66 empresas com coleta, **41 por empresa** [F6]. Usei metade porque carteira nova inclui empresas sem movimento. O XML médio subiu de ~9,1 mil para ~12,2 mil caracteres em novembro (HIP: campos IBS/CBS), sem efeito relevante no custo.

| Custo mensal (R$) | P → plano A | M → plano B | G → plano C + adicionais |
|---|---:|---:|---:|
| Fly capacidade | 4,84 | 24,21 | 121,07 |
| Neon compute | 3,88 | 19,38 | 96,91 |
| Neon armazenamento (12 meses de acervo) | 0,11 | 0,56 | 2,80 |
| Tigris | 0,06 | 0,29 | 1,46 |
| Brevo | 0,72 | 3,60 | 18,00 |
| **Infra variável** | **9,61** | **48,05** | **240,25** |
| Claude (uso esperado) | 18,10 | 48,27 | 150,85 |
| Asaas (60% Pix, 25% boleto, 15% cartão) | 2,32 | 3,66 | 10,75 |
| **Custo direto variável** | **30,03** | **99,99** | **401,85** |
| Repasse Serpro, faixa 1 (não é custo da Mewstack) | 25,60 | 128,00 | 640,00 |

O repasse real cai com o volume agregado da conta central (faixa 8: consulta R$ 0,06, emissão R$ 0,08). Se a Loja aplicar o preço da faixa a todas as chamadas do mês, G pagaria R$ 520,00 (consultas na faixa 3, emissões na faixa 1); a regra exata (todas as chamadas ou só as da faixa) **não está na página**: confirmar com a Serpro (HIP: todas).

### 2.5 Ponto de equilíbrio da infraestrutura

N* = custo fixo ÷ margem de contribuição do tenant (seção 4.4): A R$ 168,97; B R$ 399,01; mix 60% A, 30% B, 10% C R$ 388,80 (HIP).

| Cenário | Fixo/mês | Só plano A | Só plano B | Mix 60/30/10 |
|---|---:|---:|---:|---:|
| Hoje | R$ 196,25 | 1,2 → 2 tenants | 0,5 → 1 | 0,5 → 1 |
| Operação comercial | R$ 591,20 | 3,5 → 4 | 1,5 → 2 | 1,5 → 2 |

A infraestrutura não limita o negócio. Com R$ 5.000/mês de custo humano (HIP ilustrativa), o equilíbrio do mix sobe para (591,20 + 5.000) ÷ 388,80 = 14,4, ou seja, 15 tenants.

## 3. Referências de mercado

| Fornecedor | Produto | Cobra por | Preço público em 20/11/2026 | Fonte |
|---|---|---|---|---|
| Qive (antiga Arquivei) | captura e gestão de documentos fiscais | sob consulta; "escritórios contábeis: planos conforme a carteira" | **sob consulta** (todos os planos pedem contato) | F19 |
| SIEG | gestão fiscal para escritórios (Control, Flow, Essential; cofre de 15 anos) | sob consulta; o formulário pergunta a quantidade de CNPJs (1 a 10 até mais de 300) e os planos limitam usuários (3, ilimitados, ilimitados) | **sob consulta**. Certificado A1 para clientes: R$ 69 / 59 / 49 por unidade | F20 |
| Acessórias | prazos e entregas do escritório | sob consulta | **sob consulta** (sem página de preços; só demonstração) | F21 |
| Gestta | gestão de escritório | **HIP** sob consulta | o site não abriu (HTTP 522); o plano E9 do repo registrava "sob consulta" | F22 |
| Domínio (Thomson Reuters) | Domínio Contábil e Domínio Cobranças | licença: sob consulta. Cobranças: por cobrança e por NFS-e emitida | tabela só dentro da conta (aba Valores); a página não cita mensalidade | F24 |
| Questor, Alterdata | sistemas contábeis | **HIP** sob consulta | a busca de 20/11 não achou tabela pública; nenhuma página de preço aberta | F32 |
| Omie.G-Click | gestão de processos do escritório | por usuário | a partir de **R$ 119/mês** (1 usuário). O repo registrou R$ 100 em 15/09/2026 | F23 |
| Focus NFe | API fiscal com recebimento de NFS-e Nacional | por CNPJ e por documento | Solo R$ 94,90 (1 CNPJ, 100 docs); Start R$ 119,90 (3 CNPJs, +R$ 39,90 por CNPJ); Growth R$ 572 (CNPJs ilimitados, 4.000 docs); doc extra R$ 0,11 a 0,125 | F25 |
| NFE.io | captura de NFS-e recebida (Ambiente Nacional, certificado da empresa) | sob consulta | página sem preço | F26 |
| NFSeek | captura de NFS-e, A1 de cada empresa | faixa de CNPJs; avulso por CNPJ | R$ 49,90 (50 CNPJs); R$ 89,90 (150); R$ 149,90 (300); avulso R$ 1,50/CNPJ (mín. 10) | F27 |
| Motor Fiscal | NF-e, CT-e e NFS-e Nacional, A1 da empresa | faixa de CNPJs e de notas | R$ 79 (10 CNPJs, 600 notas); R$ 187 (50, 1.500); R$ 397 (200, 4.000); Enterprise sob consulta | F28 |
| FiscalBase | NFS-e por A1 da empresa **ou do escritório, por procuração**; app Windows, XML no disco do usuário | faixa de empresas | R$ 59,90 (10); R$ 99,90 (20); R$ 149,90 (50); acima sob consulta | F29 |
| iFiscal.ai | nota, apuração e guia | base + por CNPJ (conta após a 1ª nota importada) | R$ 159/mês com 20 CNPJs + R$ 7 por CNPJ; anual R$ 1.590 (R$ 960 no 1º ano para os 100 primeiros) | F30 |
| "Notas Fiscais Brasil" | produto com esse nome não localizado | — | — | — |

Contabilizei é escritório, não referência de software.

### 3.1 Captura de NFS-e: A1 por CNPJ × procuração

| Modelo | Credencial | Quem vende | Preço por empresa·mês |
|---|---|---|---|
| A1 por CNPJ | certificado de cada cliente. O A1 e-CNPJ custa ~R$ 219,90 a R$ 235/ano [F31]; SIEG o revende por R$ 49 a 69 a seus clientes [F20] | NFSeek, Motor Fiscal, iFiscal, Focus NFe, NFE.io, Qive, SIEG | R$ 0,50 a 1,00 (NFSeek) até R$ 7 a 8 (iFiscal) |
| Procuração + e-CNPJ do escritório | 1 certificado do escritório + procuração do cliente no Portal da Receita (Manual ADN v1.1, 03/11/2026; só vale em produção) | FiscalBase (R$ 3,00 a 6,00); **CICA** | CICA proposto: R$ 3,43 a 6,63 no limite do plano |

Valor percebido, não receita: 100 empresas com A1 próprio custam R$ 1.833 a R$ 1.958/mês em certificados ao preço de tabela (100 × R$ 219,90 a 235 ÷ 12), ou R$ 408 a R$ 575 ao preço SIEG. A procuração dispensa essa renovação anual.

### 3.2 Leitura

- Captura pura é commodity: R$ 0,50 a R$ 8 por empresa·mês, e a procuração já existe no mercado (FiscalBase), sem nuvem nem suíte. O CICA só sustenta preço acima disso vendendo a suíte (guias, Integra, conciliação, Copiloto, Pacote fiscal) e a ausência de PC e de A1 por cliente.
- As suítes de gestão (Qive, SIEG, Acessórias, Gestta, Domínio) não publicam preço. As âncoras públicas mais próximas são Omie.G-Click (R$ 119 por usuário) e iFiscal.

| Mesma carteira em… | 30 empresas | 120 empresas | 350 empresas |
|---|---:|---:|---:|
| iFiscal (159 + 7 por CNPJ acima de 20) | R$ 229 | R$ 859 | R$ 2.469 |
| Motor Fiscal | R$ 187 | R$ 397 | sob consulta |
| FiscalBase (procuração) | R$ 149,90 | sob consulta | sob consulta |
| NFSeek | R$ 49,90 | R$ 89,90 | sob consulta (acima de 300) |
| **CICA proposto** | **R$ 199** | **R$ 499** | **R$ 1.199** |

## 4. Grade proposta

### 4.1 Planos e limites

| | **A** | **B** | **C** | **Teste** |
|---|---:|---:|---:|---|
| Mensal | R$ 199 | R$ 499 | R$ 1.199 | R$ 0, sem cartão |
| Anual (10 mensalidades, −16,7%) | R$ 1.990 | R$ 4.990 | R$ 11.990 | — |
| Empresas ativas (raiz de CNPJ; filial não conta) | 30 | 120 | 350 | 10 |
| Usuários ativos (inclui administradores) | 3 | 8 | 20 | 2 |
| e-CNPJ do escritório (um vigente + um de renovação) | 2 | 2 | 3 (HIP: fila paralela) | 1 |
| A1 por empresa (modo `certificate`) | 0 | 0 | 0 | 0 |
| Franquia de IA (R$ de uso CICA/mês) | R$ 20 (≈ 219 perguntas) | R$ 55 (≈ 600) | R$ 160 (≈ 1.750) | 20 perguntas (≈ R$ 1,83) |
| Teto técnico de documentos/mês (uso justo, não cobrado) | 1.800 | 7.200 | 21.000 | 600 |
| Retenção de documentos online | 60 meses | 60 | 60 | até exportar |
| Empresa adicional (só com aceite) | R$ 9,90 | R$ 5,90 | R$ 4,90 | — |
| Usuário adicional (só com aceite) | R$ 29 | R$ 29 | R$ 29 | — |
| Preço por empresa no limite | R$ 6,63 | R$ 4,16 | R$ 3,43 | — |

Todos os planos têm a mesma suíte; muda a capacidade e a franquia de IA (`PLANO-MAIS-QUE-MESTRE.md` §11). MFA é opcional e recomendado em todos (D-192), não é diferencial. Suporte por `suporte@mewstack.com.br` (D-76); canal prioritário no C é decisão do dono, e seu custo não está no modelo.

**Repasse sem margem (D-109, D-306):** Serpro Integra Contador, pelo custo efetivo e auditável de cada chamada (consulta R$ 0,24 a 0,06; emissão R$ 0,32 a 0,08; declaração R$ 0,40 a 0,12), mostrado antes da chamada, fora da mensalidade e da franquia, com descontos e arredondamento distribuídos de forma determinística. Teto de referência: faixa 1. Estimativa por arquétipo: R$ 25,60 / 128,00 / 640,00 por mês (seção 2.4). Nada mais é repassado: Fly, Neon, Brevo, Asaas e Claude estão dentro do preço.

### 4.2 O que inclui (Pacote fiscal, D-306)

| Módulo | Estado em 20/11/2026 |
|---|---|
| Coleta de NFS-e por procuração (ADN) | pronta localmente (E1), sem piloto real, flag desligada |
| Emissão de NFS-e por procuração | E7, não iniciada; produção só com OK explícito por tenant |
| RBT12, Fator R, teto Simples e MEI | E7 |
| Reforma IBS/CBS | E7 |
| Situação fiscal e pendências (SITFIS) | E7; custo Serpro mostrado antes da chamada |
| Já existentes: NFS-e Inteligente, Guias e DCTFWeb, Central Integra, Conciliação OFX × Domínio, Radar da Reforma, Triagem de Arquivos, Copiloto | existem; Copiloto desligado em produção |
| Fora: Contraprova, Rentabilidade, retificação de EFD, recuperação de tributos | desligados ou fora (D-306) |

O preço só passa a valer quando os módulos acima existirem.

### 4.3 Por que esses números

| Plano | Piso (custo no limite ÷ 0,30, HIP de 70% de margem) | Mercado para o mesmo porte | Escolha |
|---|---|---|---|
| A R$ 199 | R$ 116 (custo direto R$ 34,83) | iFiscal R$ 229; FiscalBase R$ 149,90; o contrato legado atual custa R$ 200,00 | abaixo do iFiscal e perto do legado |
| B R$ 499 | R$ 365 (R$ 109,60) | Motor Fiscal R$ 397 (só captura); Focus Growth R$ 572; iFiscal R$ 859 | entre captura pura e iFiscal |
| C R$ 1.199 | R$ 984 (R$ 295,21) | iFiscal R$ 2.469; Motor Fiscal sob consulta | 49% do iFiscal; **pouca folga para desconto** |

- Limites (30/120/350 empresas; 3/8/20 usuários; 2/2/3 e-CNPJ) são desenho, não derivação de custo (HIP): foram calibrados para 20, 100 e 500 empresas caírem em A, B e C + adicionais, com 1 usuário para cada 10 a 18 empresas. O custo de um usuário é só a IA (~R$ 6/mês). O mercado fatia carteiras em 10, 20, 50, 150, 200 e 300 CNPJs (seção 3).
- Degraus: preço por empresa cai de R$ 6,63 para R$ 4,16 e R$ 3,43, dentro da faixa R$ 3 a 8 do mercado de captura (seção 3).
- Anual = 10 mensalidades, o mesmo desenho do iFiscal (R$ 1.590 contra R$ 159).
- Adicional por empresa sempre acima da média do plano (9,90 > 6,63; 5,90 > 4,16; 4,90 > 3,43), para o upgrade ser racional. Usuário adicional R$ 29: custa ~R$ 6,03 de IA (66 × R$ 0,0914), margem de 79%.
- Franquia de IA = 10% a 13% do preço (R$ 20 de R$ 199; R$ 55 de R$ 499; R$ 160 de R$ 1.199) e cobre o uso esperado (A 90%, B 88%, C 75%). **Adicional de IA: custo × 2 (HIP), R$ 0,18 por pergunta de referência**, só com aceite do administrador e teto mensal; o padrão é bloquear (D-109).
- Retenção de 60 meses = 5 anos, o prazo de decadência tributária (CTN art. 173; HIP, validar com o jurídico). Custa quase nada: 1.000 NFS-e = US$ 0,0038/mês no Neon (10,95 KB por documento × US$ 0,35/GB). Valor provisório: PC-28 segue aberto.

### 4.4 Margem por arquétipo

| | P → A | M → B | G → C + adicionais |
|---|---:|---:|---:|
| Receita/mês | 199,00 | 499,00 | 2.079,00 (1.199 + 150 × 4,90 + 5 × 29) |
| Custo direto variável | 30,03 | 99,99 | 401,85 |
| **Margem de contribuição** | **168,97 (84,9%)** | **399,01 (80,0%)** | **1.677,15 (80,7%)** |
| Fixo comercial rateado a 5 tenants (R$ 118,24) | 50,73 (25,5%) | 280,77 (56,3%) | 1.558,91 (75,0%) |
| **Margem bruta**, fixo rateado a 20 tenants (R$ 29,56) | **139,41 (70,1%)** | **369,45 (74,0%)** | **1.647,59 (79,2%)** |
| Após 6,00% de imposto (HIP, Anexo III) | 127,47 (64,1%) | 339,51 (68,0%) | 1.522,85 (73,2%) |
| Após 15,50% (HIP, Anexo V) | 108,56 (54,6%) | 292,10 (58,5%) | 1.325,34 (63,8%) |
| IA gasta 100% da franquia (contribuição) | 167,07 (84,0%) | 392,29 (78,6%) | 1.668,00 (80,2%) |

Serpro não está nas linhas acima: é repasse, sem margem (D-109). A taxa do Asaas e o imposto sobre o repasse ficam com a Mewstack (cartão: 2,99% do valor repassado).

### 4.5 Teste, cobrança e legado

| Item | Proposta | Âncora |
|---|---|---|
| Duração | 14 dias, sem cartão, sem reinício por convite | D-79; `TRIAL_DAYS = 14` (`signup.py`) |
| Registro | `Plan cica-trial-v1` (inativo), `TenantContract` em `trial` com `trial_ends_on` = hoje + 14, `quoted_monthly_cents = 0`, `Entitlement` por módulo até o fim do teste | `signup.py:206-256` |
| Serpro e emissão fiscal | bloqueados: repasse exige fatura e o teste não tem cartão. Hoje `signup.py` só cria taxa de `ai.answer` | `signup.py:213-241` |
| IA | 20 perguntas (≈ R$ 1,83). Se o Copiloto for ligado com `trial_ai_included_requests < 1`, o cadastro falha com "indisponível" | `signup.py:50-59`; `precificacao-e-cotas-ia.md` |
| Custo por teste | R$ 4,22 (IA 1,83 + infra 2,03 + e-mail 0,36) | cálculo da seção 2 |
| Fim sem contratação | somente leitura e exportação (HIP: D-79 trata atraso de fatura, não o fim do teste); carência de 7 dias só para atraso | D-79 |
| Ciclo | competência fecha no dia 1, vencimento no dia 10, 1º mês proporcional, troca de plano no ciclo seguinte | D-79 |
| Legado | contrato atual (R$ 200,00, travado) não muda; migração só com aceite explícito. Medi **218 empresas ativas e só 72 raízes distintas** (145 sem raiz preenchida): migrar por raiz muda a conta, simular antes | D-303; `manual-homologacao-externa.md` |
| Vigência | a partir da aprovação; valor congelado por contrato (`monthly_price_cents`, `monthly_price_locked`) | `platform/models.py` |

## 5. Mapeamento para o código (E3)

`Plan.limits` é JSON sem leitor em produção (spec) e o `Plan` da tabela está vazio. Nomes **existentes** vêm de `hub/seeding.py:155` e de `UsageAllowance.Metric`; os demais são **novos**.

| Conceito | Chave ou campo | Valores A / B / C (teste) | Leitor |
|---|---|---|---|
| Preço mensal | `Plan.monthly_price_cents` (existe) | 19900 / 49900 / 119900 | copiado para `TenantContract.monthly_price_cents` |
| Preço anual | `Plan.limits["annual_price_cents"]` (**novo**) | 199000 / 499000 / 1199000 | checkout Asaas, só Pix ou boleto |
| Empresas ativas | `Plan.limits["companies"]` (existe) | 30 / 120 / 350 (10) | `calculate_commercial_capacity().active_company_roots` |
| Usuários ativos | `Plan.limits["users"]` (existe) | 3 / 8 / 20 (2) | `active_users` |
| Documentos/mês | `Plan.limits["documents"]` (existe) | 1800 / 7200 / 21000 (600) | `UsageAllowance.Metric.DOCUMENTS`; aviso, sem cobrança |
| e-CNPJ do escritório | `Plan.limits["office_certificates"]` (**novo**) | 2 / 2 / 3 (1) | upload em `office_certificate.py` |
| A1 por empresa | `Plan.limits["company_certificates"]` (**novo**) | 0 / 0 / 0 (0); ausente = sem limite (legado) | upload de certificado |
| Franquia de IA | `Plan.limits["ai_allowance_cents"]` (**novo**) | 2000 / 5500 / 16000 (≈ 183) | E3 decide: medir em centavos ou em respostas de referência |
| IA em respostas | `PlanServiceRate(ai.answer).included_units` (existe) | 219 / 600 / 1750 (20 = `trial_ai_included_requests`) | `intelligence/services.py` |
| Preço do adicional de IA | `PlanServiceRate.overage_unit_price_cents` (existe) | 18 / 18 / 18 | meter `ai.answer` |
| Teto de excedente de IA | `Plan.limits["ai_overage_cap_max_cents"]` (**novo**) | 5000 / 15000 / 50000; padrão 0 | `TenantUsagePolicy.monthly_overage_cap_cents`; `overage_mode = block` (existe) |
| Empresa adicional | `Plan.limits["extra_company_cents"]` (**novo**) | 990 / 590 / 490 | aceite explícito do administrador |
| Usuário adicional | `Plan.limits["extra_user_cents"]` (**novo**) | 2900 / 2900 / 2900 | idem |
| Retenção | `Plan.limits["retention_months"]` (**novo**) | 60 / 60 / 60 | job de retenção (PC-28) |
| Serpro | sem preço fixo. `UsageEvent` com custo efetivo; `InvoiceLine` `overage` + `adjustment` para o ajuste de faixa (D-109); referência de teto = faixa 1 | — | `integra/catalog.py` (`RELATORIOSITFIS92` está como "Emitir", R$ 0,32) |
| Carência | 7 dias após atraso: `TenantContract.grace_ends_on` (existe, só escrito) | constante D-79 | automação do E3 |
| Preços e limites no teste | `Plan cica-trial-v1.limits` | `{companies: 10, users: 2, documents: 600, office_certificates: 1, company_certificates: 0}` | `signup.py` |

Preços dentro de `limits` evitam migração (L1 permite só adicionar); E3 pode movê-los para campo próprio. Antes de cobrar por raiz: garantir `commercial_root_cnpj` na importação do E2 e fazer o backfill, pois 145 de 218 empresas ativas hoje estão sem raiz.

## 6. Riscos e perguntas ao dono

**Riscos:** (1) captura é commodity de R$ 0,50 a R$ 8 por empresa e o plano A é o mais exposto; (2) câmbio e IOF: ~90% do custo direto variável é em US$ (14% a 19% da receita); (3) a capacidade de 1 VM por 150 empresas é HIP e a web já operou com ~27 MB livres, então o custo fixo pode subir antes do teste de carga do E5; (4) a procuração depende de o cliente final outorgar e só funciona em produção, e 14 dias podem não bastar para converter; (5) Serpro: categoria cobrada do SITFIS e regra da faixa a confirmar na primeira fatura; (6) o histórico do Neon é de 6 h; restaurar um erro descoberto no dia seguinte (D-73, RTO de 4 h) exige ampliar: 7 dias custam ~US$ 0,13; (7) o template órfão `plan_simulator.html` ainda tem preços antigos: remover no E6; (8) o Neon Launch não tem SLA de disponibilidade (só o Scale, US$ 0,222/CU-h): prometer SLA em contrato custaria +R$ 258/mês a 0,5 CU ((0,222 − 0,106) × 365 × 6,0950) [F4].

**Perguntas** (cada uma com recomendação):

1. **Aprovar A/B/C (R$ 199 / 499 / 1.199)?** Recomendo sim, como preço de lançamento para os 10 primeiros escritórios, revisto em 90 dias com uso medido.
2. **Faixa com adicional por empresa, ou só por empresa ativa?** Recomendo faixa + adicional: D-109 fala em pacotes, o mercado usa faixa (iFiscal, NFSeek) e a fatura fica previsível.
3. **Desconto de fundador?** Recomendo −30% por 12 meses até 10 escritórios, só enquanto o E7 estiver incompleto e em troca do piloto. Precedente: iFiscal dá −50% no 1º ano aos 100 primeiros.
4. **Preço com imposto embutido? Qual regime e anexo (6,00% ou 15,50%)? O repasse Serpro entra na base?** Recomendo preço de tabela final e fechar com o contador antes de publicar; a margem após imposto varia de 54,6% a 73,2%.
5. **Nota fiscal do CICA pelo Asaas (R$ 0,49/nota) ou emissor próprio?** Recomendo Asaas depois da confirmação do contador: custa 0,25% do plano A e fecha cobrança e nota.
6. **Teste: manter 14 dias sem cartão (D-79) contando do cadastro?** Recomendo manter e medir quantos chegam à 1ª NFS-e; se menos da metade, propor contar a partir do envio do e-CNPJ (isso alteraria D-79).
7. **Excedente de empresa, usuário e IA: só com aceite prévio e teto, ou bloqueio rígido?** Recomendo aceite prévio com teto; sem aceite, bloquear (`overage_mode = block`).
8. **Autoriza os custos fixos novos?** Brevo Starter R$ 40,00 + Sentry Team R$ 176,76 = **+R$ 216,76/mês** na entrada do 1º tenant pago; worker 2 **+R$ 36,32** só após o E5; sidecar IBS/CBS **+R$ 65,85** no gate do E7. Recomendo aprovar os dois primeiros agora e deixar os outros nos gates.
9. **Reajuste?** Recomendo IPCA anual com aviso de 30 dias na mensalidade, Serpro sempre pelo custo efetivo e adicional de IA revisado por câmbio a cada trimestre.
10. **Plano anual aceita cartão?** A taxa em R$ 4.990 seria R$ 149,69 (R$ 359 em R$ 11.990). Recomendo anual só por Pix ou boleto (R$ 1,59); mensal aceita cartão.

## 7. Fontes

Acessos em 20/11/2026, salvo indicação. F5 e F6 são leituras somente leitura da conta Neon do próprio dono; F7 idem no Fly.

1. F1: Fly.io, preços (Machines por região, volumes, saída). https://fly.io/pricing.md
2. F2: Fly.io Docs, preços (512 MB = US$ 3,69 em iad/ewr; a tabela regional não carregou). https://docs.fly.io/about/pricing
3. F3: Fly.io, atualização de preços vigente desde 01/10/2026. https://fly.io/pricing-update/
4. F4: Neon, preços (atualizado em 04/11/2026). https://neon.com/pricing e https://neon.com/pricing.md
5. F5: Neon MCP (`describe_project`, `get_project_consumption`) no projeto da CICA: plano `launch_v3`, aws-sa-east-1, 116,4 CU-h em out e 97,8 CU-h em 1 a 20/11, histórico de 6 h.
6. F6: Neon SQL somente leitura, só agregados (tamanho de tabelas, contagem de documentos por mês, empresas e raízes, `PlatformConfiguration`, `Plan`, `TenantContract`).
7. F7: `flyctl machine list`, `volumes list`, `ips list` dos apps `cica-contabil` e `cica-contabil-valkey` (somente leitura).
8. F8: Tigris, preços. https://www.tigrisdata.com/pricing/ (a página de docs de preços deu 404)
9. F9: Brevo, planos e catálogo em BRL (gerado em 29/09/2026). https://www.brevo.com/pt/pricing/ e https://www.brevo.com/pricing.md
10. F10: Asaas, preços e taxas (valor riscado = padrão; destaque = promoção de 3 meses). https://www.asaas.com/precos-e-taxas
11. F11: Asaas, blog de taxas (atualizado em 23/04/2026; **diverge de F10**). https://blog.asaas.com/taxas-asaas/
12. F12: Serpro, Loja, Integra Contador, aba Preço (renderizada no navegador; `WebFetch` deu 403). https://loja.serpro.gov.br/integra-contador/product/integracontador
13. F13: Domínio Atendimento, custos da API Integra Contador (exemplo R$ 0,96 na faixa 1, confere com F12). https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=10776
14. F14: Anthropic, preços da API. https://platform.claude.com/docs/en/about-claude/pricing
15. F15: Banco Central, PTAX (API Olinda, `CotacaoDolarPeriodo`): venda de 19/11/2026 = R$ 5,8889. https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/
16. F16: IOF de 3,5% no cartão internacional. **HIPÓTESE**: só fontes secundárias, sem página oficial da Receita. https://www.arqfinance.com/pt-BR/articles/aliquota-iof-compras-exterior-cartao
17. F17: Sentry, preços. https://sentry.io/pricing/index.md
18. F18: Lei Complementar 123/2006, Anexos III (6,00%) e V (15,50%), 1ª faixa. https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm
19. F19: Qive, planos (sob consulta). https://qive.com.br/planos
20. F20: SIEG, planos (sob demonstração; certificado A1 R$ 49 a 69). https://www.sieg.com/precos/
21. F21: Acessórias, site (sem preços). https://acessorias.com/site/
22. F22: Gestta. https://www.gestta.com.br/ **não abriu (HTTP 522)**; linha **HIPÓTESE**.
23. F23: Omie.G-Click (a partir de R$ 119). https://www.omie.com.br/gclick/
24. F24: Domínio Cobranças, suporte (valores na aba Valores da conta). https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=12002
25. F25: Focus NFe, preços. https://focusnfe.com.br/preco
26. F26: NFE.io, NFS-e recebida (sem preço na página). https://nfe.io/nfse-recebida/
27. F27: NFSeek. https://nfseek.com.br/
28. F28: Motor Fiscal. https://motorfiscal.com.br/
29. F29: FiscalBase. https://fiscalbase.com.br/
30. F30: iFiscal.ai. https://ifiscal.ai/
31. F31: Omie, blog do certificado A1 em 2026 (e-CNPJ A1 ~R$ 219,90 a 235). https://www.omie.com.br/blog/qual-e-o-valor-do-certificado-digital-a1-e-a3-em-2026/
32. F32: buscas por preço de Questor Zen e Alterdata Contábil: nenhuma tabela pública; **HIPÓTESE: sob consulta**; nenhuma página de preço aberta.

Arquivos do repositório lidos: `DECISOES.md` (D-73, D-76 a D-79, D-109, D-192, D-303 a D-309), `fly.toml`, `infra/valkey/fly.toml`, `docs/specs/produto-vendavel*.md`, `docs/planejamento/precificacao-*.md`, `docs/planejamento/manual-homologacao-externa.md`, `PLANO-MAIS-QUE-MESTRE.md`, `src/apps/platform/models.py`, `src/apps/platform/signup.py`, `src/apps/hub/seeding.py`, `src/apps/hub/commercial_capacity.py`, `src/apps/integra/catalog.py`, `src/apps/intelligence/gateway.py`.
