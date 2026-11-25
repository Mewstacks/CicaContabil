# Plano — Conciliação multifontes CONTAD (SURIA, competência 10/2026) — PC-33

> **Situação (24/11/2026):** proposta aprovada como plano de trabalho; registrada como PC-33
> (`PLANO-MESTRE.md`), perguntas Q-50 a Q-66 (`duvidas-abertas.md`) e análise V-465 (`VALIDACOES.md`).
> **Nenhuma decisão D nova foi registrada:** a decisão de escopo (próximo ID livre D-409) depende do
> "de acordo" do responsável e da estimativa enviada à CONTAD. Nenhum código-fonte foi alterado.
> Arquivos da cliente (vídeo, scans, planilhas) ficaram fora do repositório.
> Material analisado: vídeo da reunião de 24/11/2026 (46 min, gravação iniciada às 14:02; transcrição automática local + 93 quadros), 2 scans (Skybox), 4 relatórios .xls, extrato CEF (.docx) e `Caixa OUTUBRO 2026.zip` (planilha de caixa + 5 PDFs).
> Os tempos `[mm:ss]` contam a partir do início da gravação. A transcrição automática tem trechos ruidosos. Os valores citados foram conferidos nos documentos.

---

## 0. Contexto

**Como o sistema funciona hoje (produção ~v127, uso direto pela D-393).** Fluxo: extrato OFX/PDF × Razão do Domínio, depois DE-PARA, lançamento direto e exportação no `.txt` lote 19.

**O que a CONTAD mostrou na reunião.** O trabalho real de fechamento da SURIA exige cruzar o extrato com várias fontes paralelas:
- a **francesinha** (relatório de cobrança);
- a **posição de contas a receber e a pagar**;
- a **planilha de caixa do cliente**, que diz qual NF ou CT-e foi paga;
- o **extrato de aplicação**;
- os **documentos escaneados**.

O extrato sozinho não basta. Frases da reunião:
- [40:40] "todos os relatórios de que estamos falando são necessários; não tem como fazer sem eles";
- [36:45–37:35] Pedro confirmou que é viável: "ele tem que trabalhar com a leitura de vários documentos, de várias fontes de dados".

**Combinado na reunião.**
- Pedro organiza a proposta e manda uma estimativa [37:39–37:53].
- Outubro serve de base de teste e será comparado com o Razão feito à mão [33:33–34:03].
- Novembro roda no sistema no início de dezembro [38:41–38:57].
- Aviso de "pronto" antes de quinta (26/11). Se não der, revisão conjunta na segunda (30/11) [43:58–46:03].

**Resultado esperado deste plano.** Uma referência executável para desenvolvimento, implantação e homologação. Os requisitos têm origem rastreável. Separa o que a cliente pediu do que é sugestão e lista as perguntas que precisam de resposta antes das regras dependentes.

---

## 1. Inventário das fontes analisadas

| # | Fonte | Formato | Conteúdo relevante | Suporte hoje no CICA |
|---|---|---|---|---|
| F1 | Extrato Sicredi 10/2026 (c/c 43407-3) | PDF texto | 167 linhas datadas. Inclui `LIQ.COBRANCA SIMPLES` agregado por dia, `LIQUIDACAO BOLETO <CNPJ> <nome>`, PIX com CPF/CNPJ, `DEB. FOLHA PAGTO`, aplicação e resgate em 1 ou 2 linhas, tarifas e protesto | ✅ `read_sicredi_pdf` (`src/apps/hub/bank_evidence.py:48`); OFX também aceito |
| F2 | Francesinha Sicredi 10/2026 | PDF texto | 87 títulos, R$ 131.360,65, juros R$ 89,06 (6 títulos). Campos: Seu Nº, Nosso Nº, Pagador, Data Mvto, **Data Lçto C/C**, valor nominal, juros, valor do movimento, "Liquidação COMPE/CARTORIAL" | ❌ sem leitor |
| F3 | Extrato de aplicação Sicredinvest 10/2026 | PDF texto | Saldo de 228.016,06 para 187.469,40. Aplicações; resgates com linhas separadas de "Rendimentos" e "Encargos de IRRF" | ❌ |
| F4 | Empréstimo Sicredi C630225768 | PDF texto | 25 parcelas; a 003, de 8.654,61, foi paga em 13/10. **Não separa juros de principal** | ❌ |
| F5 | Fatura do cartão Visa Empresas (final 0126) | PDF texto | Total de 210,42, debitado em conta em 23/10; transações do cartão do sócio | ❌ |
| F6 | Extrato CEF 10/2026 | **.docx** (texto copiado) | 3 movimentos: TED de 5.000 recebido, cesta de 75 e "PREST EMP" de 4.105,51 | ❌ (.docx não aceito) |
| F7 | `Caixa OUTUBRO 2026.xlsx` (**feita pelo cliente** [07:45]) | XLSX com fórmulas | Aba **SICREDI** com 239 linhas, histórico com NF, parcela e CT-e ("FRANC NF 29740/03", "PAGTO transportadora C (CTE 323599, 323808)"). Aba **CAIXA** (dinheiro) com saldo anterior de 12.328,43, aluguel, água/luz e recebimentos cliente F. Aba **CEF**. Os cabeçalhos de mês estão errados ("2026-05-01", "AGOSTO") | ⚠️ só via mapeamento genérico de colunas (`ReconciliationLayout`); sem semântica |
| F8 | Contas a Receber 09/2026 e 10/2026 (Domínio, emitidos pela CONTAD) | **.xls BIFF** | "Por cliente": código/nome, Documento (= nº da NF, **sem sufixo de parcela**), emissão, saída, vencimento, valor da parcela, valor recebido, juros, multa, outras, desconto, devolução, saldo e situação. 09: 231 parcelas, 151 clientes, saldo de 244.631,35. 10: 230 parcelas, 136 clientes, saldo de 282.869,56 | ❌ (.xls não aceito; não há `xlrd`) |
| F9 | Contas a Pagar 09/2026 e 10/2026 (Domínio) | .xls BIFF | "Por fornecedor", mesmos campos. 09: 82 parcelas, 19 fornecedores, saldo de 70.103,88. 10: 89 parcelas, 20 fornecedores, saldo de 68.055,28. Inclui títulos de 2025 ainda abertos | ❌ |
| F10 | `scan_20261124172847.pdf` | PDF escaneado, 7 páginas | Boletos e CT-e pagos em 29 e 30/10: fornecedor I NF 51845/01 de 183,00; transportadora C CT-e 327302 de 40,00; fornecedor G 11982 de 389,16; gráfica 37126 de 3.372,00; fornecedor G 12000 de 905,76; fatura transportadora de 863,95 | ⚠️ OCR Tesseract só para extrato (`reconciliation_service.py:749`) |
| F11 | `scan_20261124172544.pdf` | PDF escaneado, 50 páginas | Recibos de aluguel (10/2026, R$ 650), DANFE e CT-e transportadora, boletos fornecedor G, transportadora H de 409,68 (pagador com **razão social antiga** razão social antiga, mesmo CNPJ) | ⚠️ idem |

**Observações quantitativas que servem de teste.** Todas foram conferidas nos arquivos.
- Francesinha × extrato, dia 01/10: `LIQ.COBRANCA` 5.917,99 = 1.411,20 + 4.456,67 + 50,12 [16:02].
- `DEB. FOLHA PAGTO` de 15.096,34 = 6 salários + pró-labore, discriminados na planilha F7.
- Resgate de 05/10: 602,26 + 3.751,09 = 4.353,35, com rendimento de 17,28 e IRRF de 3,87 no extrato F3.
- Nos relatórios F8 e F9, o **Total Geral** de "V. Parcela/Valor Pago" não fecha com a soma das linhas (CP 09: −793,40; CR 10: −9.110,46). O **Saldo** fecha. A causa é desconhecida; ver Q-59.

---

## 2. Levantamento de requisitos

### 2.1 Pedidos explícitos da cliente (R)

| ID | Requisito | Origem |
|---|---|---|
| R-01 | Gerar lançamentos usando **várias fontes** além do extrato: francesinha, posição de clientes e fornecedores, caixa do cliente, aplicação e documentos | [33:09–33:19], [37:23–37:35], [40:40–40:46] |
| R-02 | Importar a **francesinha** e **decompor** o crédito agregado de cobrança do extrato nos recebimentos individuais, pela **data de lançamento em c/c** | [14:04–16:52] |
| R-03 | **Baixar o título a receber** (NF ou parcela) de cada cliente identificado na francesinha, usando a posição de contas a receber | [16:52–17:37], [19:07–19:57], [23:22–23:43] |
| R-04 | Separar **juros e multa recebidos**: baixar o valor nominal no cliente e lançar a diferença como receita de juros. Exemplo: cliente A, 1.400,00 + 11,20 = 1.411,20 | [19:39–20:29] |
| R-05 | Escolha entre títulos candidatos: **valor exato → baixar o mais antigo**; **diferença de valor → sinalizar** para o usuário identificar. A regra pode variar por cliente e deve ser aprendida | [21:13–22:06] |
| R-06 | Conciliar o mês N com a **posição em aberto do fim de N−1**. A de N já vem com as baixas feitas | [17:52–18:09] |
| R-07 | Com o conciliador, as baixas deixam de ser feitas no Domínio. Por isso o sistema precisa **manter os títulos em aberto** e emitir, no fim do mês, um **relatório de posição por NF** (aberto, pago, saldo), para que o Razão de cada cliente mostre as notas que sobraram | [22:21–24:34] |
| R-08 | **Pagamentos a fornecedores:** baixar por CT-e ou NF informados no caixa do cliente, com **um lançamento por documento**. Exemplo: transportadora C 133,25 = CT-e 323599 + 323808 | [24:44–25:55] |
| R-09 | Sem número de documento, usar o **título aberto do fornecedor com valor exato**. Exemplo: fornecedor de software 600,00 | [28:51–29:17] |
| R-10 | Na falta da planilha, o **documento escaneado** (boleto, comprovante) deve bastar para gerar o lançamento: valor, quem pagou, fornecedor e CT-e/NF | [26:04–28:17] |
| R-11 | **Cruzar documento × banco.** Um documento sem pagamento no banco (exemplo: recibo de aluguel) deve ser **sinalizado**: pode ter sido pago em dinheiro (caixa) ou ser ressarcimento | [10:57–11:16], [27:12–27:30] |
| R-12 | **PIX para marketplace (instituição de pagamento)** vai direto para despesa de propaganda. A descrição no caixa do cliente confirma a natureza; se vier **descrição diferente**, sinalizar | [29:31–30:56] |
| R-13 | **Não lançar às cegas.** O sistema deve "gritar" (sinalizar) o que não identificou ou o que parece estranho. Senão surgem lançamentos errados que o usuário não vê | [30:50–31:30] |
| R-14 | **Tarifas** vão pelo DE-PARA básico | [31:32] |
| R-15 | **Aplicação financeira:** importar o extrato da aplicação. Aplicação é transferência; no resgate, separar principal, rendimento e imposto | [31:33–33:07] |
| R-16 | Ao terminar, gerar **relatórios de processamento**: o que foi importado e lançado, e que problemas foram encontrados | [33:19–33:31] |
| R-17 | Validar comparando com o **Razão de outubro já lançado à mão**. Onde divergir, ajustar a regra daquele tipo de histórico | [33:33–34:03] |
| R-18 | **Recebimentos marketplace:** um crédito cobre várias NFs (listadas no caixa). Chega valor menor por causa da comissão. Lançar a comissão no passivo (fornecedor) se a nota de comissão chegar no mês, ou como adiantamento se chegar depois. Pedro: "a gente vai vendo conforme chega nela" | [34:05–36:43] |
| R-19 | Meta inicial: cerca de **70% lançado automaticamente**; os 30% restantes ficam sinalizados e são "ensinados" para o sistema aprender | [38:21–38:41] |
| R-20 | Outubro como base de teste. **Novembro rodado no sistema no início de dezembro**, em paralelo com a operadora ou só no sistema (a decidir) | [38:41–38:57] |
| R-21 | Cada cliente tem relatórios e formas de envio próprios; prever **ajustes por cliente** | [38:59–39:13] |
| R-22 | **Digitalização:** os comprovantes em papel passarão a ser escaneados (o movimento inteiro) para leitura pelo conciliador | [09:44–10:33] |
| R-23 | **Explicar o que foi instalado no servidor.** O agente é só leitura, com o usuário externo do Domínio. A cliente precisa saber responder se for questionada. Pode ser necessário atualizar o agente | [41:32–43:09] |
| R-24 | **Prazo combinado:** aviso antes de quinta, 26/11, ou revisão conjunta na segunda, 30/11 | [43:58–46:03] |
| R-25 | **Comercial:** a cliente quer **saber o custo real** e espera seguir o orçamento combinado no início. Teme que "o que eu quis dizer" seja diferente do que foi entendido | [44:25–45:37] |

**Itens descartados como requisito.**
- O aviso "Texto pode ficar invisível" [43:40–43:56] é do webmail da CONTAD ao anexar a assinatura. Não é do CICA (quadro das 14:45).
- Falhas de câmera e áudio no começo da reunião.

### 2.2 Fatos observados nos documentos (O), não verbalizados

São insumos de projeto, não pedidos.
- **O-01. Seu Nº da francesinha tem formatos diferentes.** Às vezes codifica NF e parcela (`*102974003` → NF 29740/03); às vezes não (`XX00002255` → a F7 diz NF 29968/01). A NF não sai do campo de forma confiável; precisa cruzar pagador + valor + posição (Q-52).
- **O-02. Parcelas sem sufixo no Domínio.** Em F8 e F9, a parcela não tem sufixo: cliente B NF 29968 tem 3 parcelas, 4.456,67 / 4.456,67 / 4.456,66. A ordem vem do vencimento. É o caso "qual delas?" de [21:09].
- **O-03. Linha bancária × planilha do cliente nem sempre é 1:1.**
  - Uma linha do banco pode virar N linhas na F7 (folha → 7 pessoas).
  - O histórico da F7 continua em linhas sem valor ("RECEB MARKETPLACE NF …").
  - Resgates aparecem em 2 linhas no banco.
- **O-04. Natureza que só aparece na F7.**
  - PIX de 10.000 para o sócio = "DISTRIBUIÇÃO DE LUCROS".
  - terceiro pagador 22.731 = "ADIANTAMENTO CLIENTE CLIENTE D (NF 30128)": quem paga é diferente do cliente.
  - "TRANSFERENCIA PARA CAIXA 30.000" ↔ aba CAIXA "RECEBIDO DE SICREDI".
  - "TRANS CAIXA ECONOMICA 5.000" ↔ CEF "CRED TED".
  - Guias de FGTS, consignado, Simples e Receita.
- **O-05. CNPJ no extrato.** O extrato traz CNPJ/CPF em `LIQUIDACAO BOLETO` e PIX. O boleto da transportadora H tem razão social antiga e mesmo CNPJ. **O CNPJ é chave mais forte que o nome.**
- **O-06. Boleto não prova pagamento.** Os scans são boletos, CT-e, DANFE e recibos, não comprovantes bancários. A prova de pagamento vem do casamento com a linha do banco.
- **O-07. Oráculo de teste.** A posição CR/CP 10/2026 (emitida em 23/11) reflete as baixas de outubro feitas pela CONTAD [18:04]. Serve para conferir a posição que o CICA calcular (ver S-02).

### 2.3 Sugestões da análise (S), não pedidas

| ID | Sugestão | Motivo |
|---|---|---|
| S-01 | **Checklist de fontes do mês por empresa** ("perfil de fontes" da SURIA: extrato, francesinha, aplicação, CP/CR, caixa, scans) com situação recebido/faltando | Atende R-21 sem configuração livre; evita processar o mês incompleto |
| S-02 | Usar a posição CR/CP de N como **oráculo automático** da posição calculada pelo CICA | Critério objetivo para R-07/R-17 |
| S-03 | Casamento por **CNPJ/CPF primeiro**, nome normalizado depois | O-05 |
| S-04 | Toda sinalização com **motivo legível e ação sugerida** ("2 parcelas abertas de 4.456,67 — escolher") | R-13/R-19 |
| S-05 | **Modelo padrão de "Caixa do cliente"** (colunas data, histórico, documento, natureza) para os próximos clientes | R-12 pede a descrição da despesa; reduz o custo de R-21 |
| S-06 | Na fase 2, obter a posição de títulos pelo **agente** (títulos nativos C01/C02 já existentes, D-394) em vez de .xls | Menos trabalho manual; depende de Q-61 |
| S-07 | **Simulação antes do lançamento** (rodada "ensaio" que não gera .txt) para outubro | R-17 sem risco de exportar em dobro |
| S-08 | Documento curto **"O que está instalado no servidor da CONTAD"** | Atende R-23; reaproveita `docs/contad-agente-oficial-windows-server.md` |

---

## 3. O sistema atual e o que muda

Base: **`origin/main` 565773d** (D-403/V-462). O checkout local está em `b65dfe7`, com alterações não commitadas, e não deve ser a base.

| Área | Existe hoje | Lacuna para os R |
|---|---|---|
| Ingestão (`reconciliation_service.py:59,82,563,653,749`; `forms.py:880,889`) | OFX, CSV/XLSX com mapeamento, PDF Sicredi, PDF genérico, OCR | Faltam .xls, .docx, francesinha, aplicação, empréstimo, fatura, caixa com semântica, scans de documentos |
| Movimentos (`NormalizedMovement`, `models.py:1688`) | 1 linha = 1 movimento | Decompor 1→N (francesinha, folha, resgate) com rastreio da origem |
| Títulos (`title_contract.py:98`, `title_allocation.py:79`, `title_persistence.py:152-600`) | Contrato título → parcela → baixa com juros, multa e desconto; alocação **manual** n:m | Faltam casamento automático (R-03/05/08/09), carteira própria contínua mês a mês (R-07), leitor de CP/CR .xls, tela |
| Títulos nativos (agente; `contracts/titles/*.sql`; D-394) | Captura de `efentradas*`/`efsaidas*`; interpretação C01/C02 | Período fixo em **09/2026** (`NativeTitlePlan.cs:18-19`, `NativeLedgerPlan.cs:16-17`); serviços excluídos |
| Conciliação e lançamento (`reconciliation_service.py:1007,1128,1721,1781`; `direct_use.py`) | Auto-confirmação exata; partida simples D/C; uso direto por regra | Faltam lançamento **com várias partidas** (banco × cliente + juros), lançamentos de aplicação, transferência entre contas e comissão, sinalização com motivo |
| DE-PARA (`depara.py`, `depara_ledger.py`, `depara_ai_auto.py`) | Regras pelo Razão; IA com teto (D-395) | Falta regra condicionada a fonte secundária (R-12: "marketplace + descrição = propaganda") |
| Exportação (`accounting_import.py`, lote 19, D-380) | TXT lote 19 com partidas; **nunca importado de fato** no Domínio (V-428) | Validar várias partidas e histórico com nº do documento (a revisão de 23/11 aponta que ele se perde) |
| Relatórios (`reconciliation_report.py:96,199,470`) | Conferência banco × Razão; CSV | Faltam relatório de processamento (R-16), posição de títulos (R-07), comparação com o Razão manual (R-17) |
| Livro caixa / contas | `cash_projection.py` só faz projeção | Faltam caixa físico e transferências Sicredi ↔ Caixa ↔ CEF |
| Agente (`agent-windows/...`) | Só leitura via usuário externo | Liberar outubro em diante (período fixo); documentação para a cliente (R-23) |

---

## 4. Correções necessárias (defeitos e inconsistências que bloqueiam o novo fluxo)

| C | Problema | Onde | Por que bloqueia |
|---|---|---|---|
| C-01 | ~~Consultas nativas presas a 09/2026~~ **Não procede (D-410):** o modo automático do agente já aceita qualquer mês desde 09/2026; só o piloto antigo é fixo | `agent-windows/src/Cica.Agent.Contracts/NativeLedgerPlan.cs:16-17`, `NativeTitlePlan.cs:18-19` | Outubro e novembro sem Razão nem títulos pelo agente (R-17, R-20). Exige nova versão do agente [43:01] |
| C-02 | Razão não é pedido no 2º mês ou em OFX que cruza meses | `account_auto_link.py:164`, `ledger_requests.py:430` (revisão 23/11 §4.1) | Outubro é o 2º mês da SURIA. Confirmar se a D-396/D-397 já está em `origin/main` e em produção |
| C-03 | Títulos exibidos por código ("Título ea9d8ba1") | `title_labels.py:18-21`, `title_auto.py:331-340` | R-07 exige mostrar a NF |
| C-04 | OFX em Windows-1252 perde acentos | `reconciliation.py:80` | Prejudica nomes e regras por histórico (R-12) |
| C-05 | PDF e OFX do mesmo mês podem duplicar (só o OFX tem FITID) | revisão 23/11, item 1a | A SURIA tem PDF e pode ter OFX |
| C-06 | Lançamentos de regra retirada continuam exportáveis | `reconciliation_service.py:1597-1611` (revisão §4.4) | Agrava R-13 |
| C-07 | Histórico exportado perde o nº do documento | revisão §3, item 5b | R-08 pede o lançamento por CT-e/NF identificável |
| C-08 | Telas ainda falam em "revisão" e "fotografia" | revisão §5 | Contradiz a D-393; confunde a nova fila de sinalizações |

Antes de começar, conferir quais desses itens já foram resolvidos nas branches `claude/contad-revisao-restante`, `codex/contad-correcoes-revisao`, `claude/contad-tela-unificada` e `claude/contad-registro-v128`.

---

## 5. Novas funcionalidades e regras de negócio

As regras marcadas **[Q]** dependem de resposta da CONTAD (seção 12) e não serão presumidas.

### N-01 Perfil de fontes por empresa e "Mês de fechamento" (R-01, R-21, S-01)
- Cada empresa define as fontes esperadas no mês. A SURIA tem: extrato Sicredi, francesinha, aplicação, CEF, CP/CR do mês anterior, caixa do cliente e scans.
- O mês só passa para "processar" com as fontes obrigatórias presentes. Fonte faltante vira pendência visível.
- Cada arquivo leva hash, competência, empresa e tipo. Reenvio idêntico não duplica (mesmo padrão de `reconciliation_service.py:151-185`).

### N-02 Leitores novos (R-02, R-03, R-06, R-08, R-15)

| Leitor | Regras de validação |
|---|---|
| CP/CR Domínio `.xls` (F8, F9) | Contrato `titles-position-xls-v1`. Lê cabeçalho (empresa e CNPJ devem bater com a empresa), grupos Cliente/Fornecedor (código e nome) e linhas. A parcela recebe ordinal por documento, ordenado por vencimento. Confere Σ saldo = Total Geral do saldo. Divergência em V. Parcela/Pago vira aviso, não erro (Q-59) |
| Francesinha Sicredi (F2) | Contrato `sicredi-francesinha-v1`. Lê Seu Nº, Nosso Nº, pagador, datas de movimento e de lançamento em c/c, nominal, abatimento, desconto, juros, multa, valor do movimento e tipo. Confere os totais do cabeçalho (87 títulos, 131.360,65, juros 89,06) |
| Extrato de aplicação Sicredi (F3) | Contrato `sicredi-aplicacao-v1`: aplicações, resgates, rendimentos, IRRF, saldo anterior e atual. Confere a cadeia de saldos |
| Caixa do cliente (F7) | Mapeamento por empresa: aba ↔ conta (SICREDI, CAIXA, CEF). Junta as linhas de continuação sem valor ao histórico anterior. Extrai referências por padrão (NF n/p, CTE n, "NF a,b,c", série). Usa a data da linha, nunca o cabeçalho do mês (O-02/F7) |
| CEF (F6) | Pedir OFX ou PDF à CONTAD (Q-63). Leitor `.docx` só se não houver alternativa |
| Empréstimo (F4) e fatura (F5) | Leitura dos campos. Uso contábil depende de **[Q]** Q-55/Q-56 |

### N-03 Carteira de títulos da CICA (R-06, R-07)
- **Abertura:** carrega a posição do fim de N−1 (o .xls agora; depois o agente, S-06).
- **Ao longo do mês:** baixas confirmadas pelo motor (N-04) ou pelo usuário, com principal, juros, multa, desconto e data.
- **Fechamento:** gera a posição de N, que vira a abertura de N+1, sem depender de o Domínio ter baixado.
- **Relatório "Posição de títulos em aberto"** por cliente/fornecedor e NF/parcela: valor, pago no mês, saldo e situação. Exporta em XLSX/PDF.
- **Conferência com o oráculo (S-02):** diferença entre a posição calculada e a posição do Domínio de N, quando houver.
- **Reaproveita** `title_contract`, `title_persistence` e `ReconciliationTitleSnapshot`. Estende para uma cadeia mensal; o detalhe técnico está na seção 7.

### N-04 Motor de casamento multifontes (R-02 a R-05, R-08, R-09, R-13)

A ordem das regras é determinística, e toda decisão grava o **motivo**.

1. **Decomposição de cobrança:** cada `LIQ.COBRANCA` do extrato na data D casa com o conjunto de linhas da francesinha cuja *Data Lçto C/C* = D. A soma tem de ser exata, ou o movimento é sinalizado com a diferença.
2. **Recebimento → título:**
   - candidato = cliente (pelo pagador ou CNPJ) + NF (pelo Seu Nº ou pela F7) + parcela aberta;
   - a baixa é do valor **nominal**, e os juros e a multa da francesinha vão para receita **[Q-53: contas]**;
   - **R-05:** valor exato com vários candidatos → baixa a parcela de vencimento mais antigo; valor diferente → sinalização "valor não confere" com os candidatos.
3. **Pagamento → título de fornecedor:**
   - documentos citados na F7 (CT-e/NF) ou no scan → um lançamento por documento, com Σ = linha do banco (R-08);
   - sem documento: CNPJ do boleto ou PIX → fornecedor → título aberto de **valor exato**; com um único candidato, baixa; com mais de um, sinaliza (R-09);
   - diferença de valor → sinaliza; não há tolerância implícita **[Q-58]**.
4. **Decomposição 1→N pela F7:** folha, "RECEB MARKETPLACE", guias. Σ das linhas da F7 = linha do banco; senão, sinaliza.
5. **Natureza pela F7:** distribuição de lucros, adiantamento de cliente, transferência entre contas e propaganda. As regras dependem do mapeamento de contas **[Q-54/Q-57]**.
6. **Regra condicionada (R-12):** "contraparte instituição de pagamento do marketplace/marketplace **e** descrição da F7 = propaganda" → despesa de propaganda. Qualquer outra descrição → sinalização "natureza diferente do habitual".
7. **Documentos × banco (R-10, R-11):**
   - todo documento escaneado identificado deve casar com uma linha de banco ou de caixa;
   - documento sem pagamento → sinalização "documento sem pagamento identificado — pode ter sido pago em dinheiro (caixa) ou ser ressarcimento";
   - linha de banco sem documento nem planilha → sinalização.
8. **Aprendizado por cliente (R-05, R-19):** a escolha manual numa sinalização pode virar "regra desta empresa", ativada pela pessoa e registrada, no padrão `ReconciliationRule` (`reconciliation_service.py:862-1071`).

**Princípio (R-13):** nada é lançado sem regra ou casamento determinístico. Ambiguidade, diferença de valor ou natureza divergente geram **sinalização**, não lançamento. Esse ponto precisa de decisão nova (ver o conflito com a D-393 na seção 12).

### N-05 Lançamentos especiais (R-04, R-15, R-18)

| Situação | Regra | Situação da regra |
|---|---|---|
| Recebimento com juros | Banco D = cliente C (nominal) + juros recebidos C | Conta de juros **[Q-53]** |
| Aplicação | Banco C / aplicação D (transferência) | Conta **[Q-54]** |
| Resgate | Banco D = aplicação C (principal) + rendimento C − IRRF D, confrontado com F3 | A cliente disse "IOF"; o extrato traz "IRRF" **[Q-54]** |
| Transferências Sicredi ↔ Caixa ↔ CEF | Um par de lançamentos espelhados entre contas da empresa; casamento por valor e data nas duas fontes | **[Q-57]** |
| Recebimento marketplace com comissão | Σ NFs (F7) − crédito = comissão → fornecedor marketplace (nota no mês) ou adiantamento (nota depois) | Rateio por NF e contas **[Q-51]**; a reunião adiou o detalhe [36:33] |
| Empréstimo e cartão | Fora da 1ª entrega; ficam sinalizados | **[Q-55/Q-56]** |

### N-06 Leitura de documentos escaneados (R-10, R-22)
- **Paginação:** separação por página e por documento. Um documento pode ocupar 2 páginas (boleto + CT-e).
- **OCR local** (Tesseract já usado, `reconciliation_service.py:104-146`).
- **Classificação:** boleto, CT-e/fatura, DANFE, recibo, guia.
- **Extração:** beneficiário, CNPJ, valor, vencimento, nº do documento, CT-e/NF.
- **Baixa confiança** (< 90, mesmo critério de `:985`) → sinalização "leitura incerta" com a imagem da página.
- **IA só dentro da D-395** (teto de US$ 1/dia e US$ 5/mês). Ampliar exige autorização expressa (D-158).

### N-07 Relatórios (R-16, R-17)
1. **Relatório de processamento do mês:**
   - fontes lidas;
   - linhas por situação: lançado automaticamente, decomposto, sinalizado com motivo, ignorado;
   - % automático (meta R-19).
2. **Posição de títulos** (N-03).
3. **Comparação com o Razão manual:** lançamentos CICA × Razão de outubro lido pelo agente.
   - Por linha: igual / diferente na conta / diferente no valor / só CICA / só manual.
   - Agrupado por "tipo de histórico" para ajustar regras.
   - Deve rodar em modo **simulação** (S-07), sem gerar `.txt`.

### N-08 Documentação do agente para a cliente (R-23)
Linguagem simples:
- o que é o agente;
- onde está instalado (SVAPL02);
- usuário externo do Domínio, só leitura;
- o que lê e para onde envia;
- como parar ou desinstalar;
- como atualizar.

Fonte: `docs/contad-agente-oficial-windows-server.md`. **O envio à cliente depende da autorização do Pedro.**

---

## 6. Interface e experiência (UI/UX)

Obrigatório em toda mudança de tela, pelo AGENTS.md: ui-ux-pro-max, Watermelon, pesquisa de produtos (referência: "Conciliador Contábil" citado [40:26–40:36], **[Q-64]**), web-design-guidelines e Playwright em 1366/375 px, temas claro e escuro.

1. **Tela "Fechamento do mês"** (empresa + competência) como entrada única. Passos: ① Fontes (checklist N-01, com envio múltiplo e tipo detectado automaticamente) → ② Processar → ③ Sinalizações → ④ Relatórios → ⑤ Exportar.
2. **Fila de sinalizações (R-13).**
   - Agrupada por motivo: valor não confere, vários títulos, documento sem pagamento, natureza diferente, leitura incerta, sem regra.
   - Cada item mostra a linha do banco, as fontes cruzadas e os candidatos, com **ação em 1 clique** (escolher título, definir conta, marcar como caixa) e a opção "aplicar sempre para esta empresa" (N-04.8).
3. **Detalhe do movimento** com a **decomposição visual**: linha do banco → partes (francesinha, F7, documento) → lançamentos gerados. O ícone de origem de cada parte abre o PDF ou a linha da planilha.
4. **Títulos pela NF** ("NF 29968 · parcela 2/3 · cliente B"), nunca por código (C-03).
5. **Indicador de progresso** "% automático" e "faltam N sinalizações" no topo.
6. **Linguagem do uso direto:** remover "revisão", "fotografia" e IDs de decisão da tela (C-08). As mensagens dizem o que fazer.
7. **Visualizador de documento escaneado** ao lado do item, com o campo lido destacado.
8. **Acessibilidade:** sem rolagem horizontal a 375 px; contraste AA; datas em dd/mm/aaaa; valores em pt-BR; foco visível.

---

## 7. Análise técnica

| Camada | Impacto |
|---|---|
| **Banco de dados** (migrações novas) | `SourceProfile`/`MonthClose` (empresa, competência, fontes esperadas e recebidas, situação). `CollectionItem` (linhas da francesinha). `ClientCashLine` (linhas da F7 com referências extraídas). `ScannedDocument` + `ScannedDocumentField`. `TitlePositionSnapshot` (posição de abertura e de fechamento por mês, ligada a `ReconciliationTitleSnapshot`). `MovementSplit` (parte de um `NormalizedMovement` com origem e valor em centavos). `Flag` (sinalização com motivo, candidatos e resolução). `JournalEntry` com **várias partidas** (conferir se o modelo atual suporta N partidas ou se precisa de `JournalLine`) |
| **Backend** | Leitores novos em módulos próprios (padrão de `bank_evidence.py`). Motor N-04 em `src/apps/hub/multisource_matching.py`, idempotente e reexecutável por mês. Extensão de `title_persistence` para a cadeia mensal. Regras condicionadas como extensão de `ReconciliationRule`. Processamento pesado (OCR de 50 páginas) em **tarefa assíncrona** (Celery, `tasks.py`), não na requisição |
| **Dependência nova** | `xlrd` (somente .xls BIFF) **ou** conversão no envio. Exige registro de decisão. `python-docx` só se Q-63 exigir |
| **Exportação** | Lote 19 com várias partidas e histórico com nº do documento (C-07). Antes de usar com a SURIA, executar o roteiro da V-428 (importação real no Domínio), que ainda não foi feita |
| **Agente Windows** | Sem mudança (D-410): o modo automático já aceita qualquer mês desde 09/2026. Atualização só se outra etapa exigir, a combinar com a CONTAD [42:59–43:09]. Sem escrita no Domínio |
| **IA/OCR** | OCR local por padrão. IA só dentro do teto da D-395; a chave vence em 13/12 (Q-11) |
| **Armazenamento e LGPD** | Arquivos de cliente (planilhas e scans) no armazenamento de objetos, com retenção definida (Q-24/Q-49 abertas). Nunca em repositório ou fixture real; os testes usam réplicas sintéticas dos layouts |
| **Arquitetura** | Sem conector novo de banco ou ERP (D-109): só importação de arquivos. Isolamento por escritório (`CICA_DIRECT_USE_ORGANIZATION_IDS`) mantido |

---

## 8. Priorização

Criticidade: P0 bloqueia o teste de outubro, P1 é necessário para novembro, P2 é evolução.

| Item | Prio | Importância | Complexidade | Depende de |
|---|---|---|---|---|
| Governança: base `origin/main`, branches, registro D/Q (Fase 0) | P0 | Alta | Baixa | — |
| C-02 Razão do 2º mês (C-01 não procede, D-410) | P0 | Alta | Baixa | Fase 0 |
| N-02 leitores CP/CR .xls + francesinha + F7 | P0 | Alta | Média | Q-52, Q-59 |
| N-03 carteira de títulos (abertura → fechamento) | P0 | Alta | Alta | N-02 |
| N-04 regras 1–4, 7 (parcial) e 8 + fila de sinalizações | P0 | Alta | Alta | N-02, N-03, Q-58 |
| N-07 relatórios + comparação com o Razão manual (simulação) | P0 | Alta | Média | N-04 |
| N-05 juros recebidos | P0 | Alta | Baixa | Q-53 |
| C-03, C-07, C-08 | P1 | Média | Baixa | — |
| N-05 aplicação e resgate + leitor F3 | P1 | Alta | Média | Q-54 |
| N-04.5 e .6 natureza pela F7, marketplace propaganda, transferências | P1 | Alta | Média | Q-54, Q-57 |
| N-06 documentos escaneados (OCR + casamento) | P1 | Alta | Alta | N-04, LGPD |
| Lote 19 várias partidas + importação real (V-428) | P1 | Alta | Média | Q-62 |
| N-08 documentação do agente | P1 | Média | Baixa | Autorização do Pedro |
| N-05 recebimento marketplace com comissão | P2 | Média | Média | Q-51 |
| Empréstimo e cartão | P2 | Média | Média | Q-55, Q-56 |
| S-05 modelo padrão de caixa; S-06 posição pelo agente | P2 | Média | Média | Q-61 |
| C-04, C-05, C-06 | P1 | Média | Baixa | — |

---

## 9. Plano de implementação (sequência)

**Fase 0 — Alinhamento e registro (sem código)**
1. Partir de `origin/main` 565773d em worktree nova. Mapear o que as branches não mescladas já resolvem (C-02, C-03, C-06, D-404 a D-408).
2. Registrar:
   - este plano em `docs/planejamento/contad-multifontes-2026-11-24.md`;
   - o pacote **PC-33** em `PLANO-MESTRE.md` (etapa 09, com reflexos nas 11 e 12);
   - as perguntas **Q-50 em diante** em `docs/planejamento/duvidas-abertas.md`;
   - a decisão de escopo **D-409**, somente após o "de acordo" do Pedro;
   - o checklist da etapa 09 e o `registro-de-execucao.md`.
3. Enviar à CONTAD as perguntas da seção 12 e a estimativa (R-25). **Exige autorização do Pedro para enviar mensagem.**

**Fase 1 — Fatia de outubro (alvo: revisão conjunta, ver R-24; prazo depende da estimativa)**
- C-02 (C-01 não procede, D-410).
- Leitores CP/CR .xls, francesinha e F7.
- Carteira N-03 (abertura 09 → fechamento 10).
- Motor N-04, regras 1–4 e 8; juros N-05.
- Fila de sinalizações mínima; relatórios N-07 em **simulação**.
- **Saída:** outubro da SURIA processado, com % automático, sinalizações e posição de 31/10 comparada com o CR/CP 10 e com o Razão manual.

**Fase 2 — Completar outubro**
- Aplicação e resgate (F3), natureza pela F7, marketplace propaganda, transferências Sicredi ↔ Caixa ↔ CEF, leitor CEF.
- C-03, C-04, C-05, C-06, C-07 e C-08.
- Lote 19 com várias partidas e importação real (V-428).

**Fase 3 — Documentos escaneados**
- N-06 com os scans F10 e F11; cruzamento documento × banco/caixa (R-11).

**Fase 4 — Telas definitivas**
- Seção 6 completa, com o protocolo de UI do AGENTS.md.

**Fase 5 — Homologação de novembro (início de dezembro, R-20)**
- Rodar novembro: em paralelo com a operadora ou só o sistema (Q-60).
- Medir o % automático (R-19); converter as sinalizações resolvidas em regras.

**Fase 6 — Evolução**
- marketplace com comissão, empréstimo, cartão, modelo padrão de caixa (S-05), posição pelo agente (S-06) e próximos clientes (R-21).

---

## 10. Critérios de aceitação (objetivos, com os dados de outubro da SURIA)

| Demanda | Concluída quando |
|---|---|
| Leitor francesinha | 87 títulos, Σ 131.360,65, juros 89,06. O total diário por Data Lçto bate com cada `LIQ.COBRANCA SIMPLES` do extrato (ex.: 01/10, 5.917,99 = 1.411,20 + 4.456,67 + 50,12). Arquivo repetido não duplica |
| Leitor CP/CR .xls | CR 09: 231 parcelas, 151 clientes, saldo 244.631,35. CP 09: 82 parcelas, 19 fornecedores, saldo 70.103,88. Divergência do "Total Geral" de parcela/pago vira aviso registrado. Empresa errada (CNPJ ≠) é recusada |
| Leitor caixa F7 | As 3 abas são lidas. Linhas de continuação são unidas. Referências extraídas: "PAGTO transportadora C (CTE 323599, 323808)" → 2 CT-e. O saldo calculado bate com a fórmula da planilha |
| Recebimento com juros | cliente A: baixa de 1.400,00 na NF 29740 + juros de 11,20 na conta definida (Q-53). Σ = 1.411,20 |
| Regra do mais antigo | cliente B NF 29968 com 4.456,67 → baixa a parcela de vencimento mais antigo em aberto. Com valor diferente → sinalização "valor não confere" com os candidatos |
| Pagamento por documento | transportadora C 133,25 → 2 baixas (CT-e 323599, 93,25; CT-e 323808, 40,00), um lançamento por documento |
| Pagamento sem documento | fornecedor de software 600,00 → baixa do único título aberto de 600,00. Com 2 candidatos → sinalização |
| Folha | `DEB. FOLHA PAGTO` 15.096,34 decomposto nas 7 linhas da F7 (Σ exata) |
| Aplicação e resgate | Resgate de 05/10 (602,26 + 3.751,09 = 4.353,35) confrontado com F3 (rendimento 17,28, IRRF 3,87). Saldo final da aplicação = 187.469,40 |
| marketplace propaganda | PIX instituição de pagamento do marketplace com descrição "PAGTO MARKETPLACE" → propaganda. A mesma contraparte com outra descrição → sinalização |
| Documento sem pagamento | Recibo de aluguel 650,00 (F11) sem linha no Sicredi → sinalização. Ao marcar "pago em caixa", casa com a aba CAIXA "PAGTO ALUGUEL" 650 |
| Posição de títulos | Posição de 31/10 calculada × CR/CP 10/2026: toda diferença listada e explicada (baixa de novembro, sinalização pendente ou erro). Meta de aceite **[Q-60]** |
| Comparação com o Razão manual | Relatório por linha e por tipo de histórico, gerado em simulação, sem `.txt` exportado |
| Princípio R-13 | Nenhum lançamento gerado para item ambíguo. 100% das sinalizações com motivo e ação |
| R-19 | % automático calculado e exibido. Os 70% são meta de referência, não critério de aceite, até decisão |
| R-23 | Documento entregue e validado pelo Pedro antes do envio |
| UI | Protocolo do AGENTS.md cumprido; Playwright 1366/375, claro e escuro, sem rolagem horizontal, contraste AA |

---

## 11. Testes e validação

- **Unitários com réplicas sintéticas** de cada layout (francesinha, .xls, F7, aplicação, scans): mesma estrutura, dados fictícios. Arquivo real de cliente nunca entra no repositório.
- **Cenários do motor:**
  - decomposição exata e com diferença;
  - várias parcelas iguais;
  - juros e desconto;
  - CNPJ com razão social antiga;
  - documento sem pagamento;
  - pagamento sem documento;
  - natureza divergente;
  - reprocessamento idempotente;
  - desfazer.
- **Regressão:** `uv run pytest -q`, `ruff check`, `manage.py check`, `makemigrations --check`, rodada `--ds=config.settings.test_postgresql` (CI `.github/workflows/ci.yml:141-151`). Para o agente, `dotnet test agent-windows/tests/Cica.Agent.Tests/...` e `agent-windows-validation.yml`. Os 28 arquivos de teste ligados à CONTAD (566 testes na revisão de 23/11) devem continuar verdes.
- **Validação com dados reais (fora do repositório, com autorização):**
  - outubro da SURIA em simulação;
  - confronto com o CR/CP 10 e com o Razão manual de outubro (R-17);
  - resultado registrado em `VALIDACOES.md` (V-465 em diante), dizendo o que foi e o que não foi verificado.
- **Exportação:** importação real do lote 19 com várias partidas no Domínio, pela CONTAD (roteiro V-428).
- **Homologação:** novembro (R-20), com medição do % automático e da taxa de erro nas confirmações automáticas. O critério final depende de Q-60 (D-73 foi dispensada pela D-393 item 8).

---

## 12. Riscos, pontos de atenção e perguntas

### 12.1 Riscos e pontos de atenção
1. **Base de código divergente.** O checkout local está desatualizado e tem alterações não commitadas. Há branches não mescladas com decisões só no código (D-405 a D-408). Planejar e implementar sobre `origin/main`, preservando as alterações locais (AGENTS.md).
2. **Possível conflito com a D-393 (uso direto, sem revisão).** R-13 pede que o sistema sinalize e não lance o que for ambíguo, e R-17 pede validação contra o Razão manual. Não contradiz o "lançar o que tem regra", mas muda o comportamento: regras condicionadas e sinalizações bloqueantes. **Exige decisão nova antes da implementação.**
3. **Fonte de títulos (D-305, D-394).** Hoje é o Domínio via agente. Os novos .xls também vêm do Domínio, mas a planilha do cliente (F7) é uma fonte nova, com outro dono. Registrar.
4. **Baixas fora do Domínio (R-07).** O módulo fiscal do Domínio e a carteira CICA vão divergir com o tempo. É preciso definir qual é a posição oficial (Q-61).
5. **Lote 19 nunca importado de verdade** (V-428). Lançamentos com várias partidas aumentam o risco.
6. **Agente.** Não precisa de nova versão para outubro (D-410); a cliente pediu clareza sobre o que está instalado (R-23).
7. **LGPD e autorização de dados.** Planilhas e scans contêm nomes, CPFs e salários (folha). Q-24 e Q-49 estão abertas. A autorização de IA da D-395 não foi coletada em tela.
8. **Custo de IA.** OCR com IA pode estourar o teto da D-395. A chave vence em 13/12. Qualquer ampliação exige autorização (D-158).
9. **Variação por cliente (R-21).** Cada cliente com layouts próprios encarece a escala (146 empresas). Mitigar com perfis de fonte e o modelo padrão (S-05).
10. **Qualidade dos scans.** Páginas tortas, furos de pasta, carimbos e 2 páginas por documento. Haverá itens com "leitura incerta".
11. **Expectativa e comercial (R-25).** A cliente esperava algo "similar ao Conciliador Contábil" [40:26] e quer manter o orçamento. **Valores e prazo não são presumidos aqui.** A estimativa é do Pedro e deve ser enviada antes de assumir o escopo (Fase 0).
12. **Prazo (R-24).** Quinta (26/11) ou segunda (30/11) é a expectativa da cliente para "ver algo", não um prazo de entrega total. Alinhar o que estará pronto (Fase 1).
13. **Transcrição automática.** Trechos ruidosos (ex.: [34:52] "valor de multa" no contexto de comissão marketplace). Pontos sem confirmação viraram perguntas, não regras.

### 12.2 Perguntas para a CONTAD (registradas como Q-50 a Q-66 em `duvidas-abertas.md`)

| Ref | Pergunta | Bloqueia |
|---|---|---|
| Q-50 | O plano de contas da SURIA tem **conta analítica por cliente e por fornecedor**, ou conta única com histórico por NF? ("cada razão de cliente diga quem são as notas", [24:26]) | N-03, N-05, exportação |
| Q-51 | marketplace: como ratear a comissão por NF? Qual documento traz a comissão? Quais contas usar (fornecedor ou adiantamento)? | N-05 marketplace |
| Q-52 | Na francesinha, o que significa Seu Nº no formato `XX0000xxxx`? Ele aponta para a NF e a parcela em algum relatório? | N-04.2 |
| Q-53 | Contas de juros recebidos, multa recebida e desconto concedido da SURIA | N-05 |
| Q-54 | Contas de aplicação, rendimento e imposto. O imposto é o IRRF que aparece no extrato, ou também IOF? O lançamento é por resgate ou mensal? | N-05 |
| Q-55 | Empréstimo: separar juros e principal? Com que fonte (o cronograma só traz o total)? Há cronograma do empréstimo da CEF? | P2 |
| Q-56 | Fatura do cartão: lançar o total ou cada despesa da fatura? | P2 |
| Q-57 | Escopo das contas: entram o caixa físico (aba CAIXA) e a CEF? Como lançar as transferências entre elas? | N-04.5 |
| Q-58 | Existe alguma **tolerância de valor** (centavos) ou baixa parcial automática, ou toda diferença é sinalizada? | N-04 |
| Q-59 | Por que o "Total Geral" de valor da parcela e valor pago nos .xls não fecha com as linhas (o saldo fecha)? | Leitor .xls |
| Q-60 | Critério de aceite: % automático mínimo e taxa de erro tolerada? Novembro roda em paralelo com a operadora ou só no sistema? Quem valida? | Homologação |
| Q-61 | Daqui em diante, qual é a **posição oficial** dos títulos: a da CICA ou a do Domínio? O fiscal seguirá emitindo o CP/CR do mês anterior, ou a CICA o substitui? | N-03, S-06 |
| Q-62 | Quem importa o `.txt` no Domínio e quando dá para fazer a importação real de teste? | Exportação |
| Q-63 | É possível obter o extrato CEF em OFX ou PDF, em vez de texto copiado no Word? | Leitor CEF |
| Q-64 | O "Conciliador Contábil" citado como referência: qual produto ou tela é? Quais funções eram usadas? | UI/UX, escopo |
| Q-65 | Como os arquivos chegarão todo mês (envio pela tela do CICA, por quem, até que dia) e por quanto tempo guardar? | N-01, LGPD |
| Q-66 | Folha, guias, distribuição de lucros e adiantamentos de cliente (cliente D, pago por terceiro; cliente E): contas e documentos de suporte | N-04.5 |

---

## 13. Arquivos críticos (referência para a implementação)

- **Ingestão:** `src/apps/hub/reconciliation_service.py`, `bank_evidence.py`, `forms.py`, `views.py` (`reconciliation_upload` ~10100/10443), `models.py` (1421, 1471, 1580, 1688, 1895-1980).
- **Títulos:** `src/apps/hub/title_contract.py`, `title_allocation.py`, `title_persistence.py`, `title_labels.py`, `title_auto.py`, `src/apps/intelligence/native_title_contract.py`, `contracts/titles/*.sql`.
- **Uso direto e regras:** `direct_use.py`, `depara_ledger.py`, `depara_ai_auto.py`, `auto_confirm.py`.
- **Exportação e relatórios:** `accounting_import.py`, `reconciliation_report.py`.
- **Agente:** `agent-windows/src/Cica.Agent.Contracts/NativeLedgerPlan.cs`, `NativeTitlePlan.cs`, `Cica.Agent.Service/Worker.cs`.
- **Governança:** `PLANO-MESTRE.md`, `DECISOES.md`, `VALIDACOES.md`, `docs/planejamento/duvidas-abertas.md`, `docs/planejamento/etapas/09-conciliacao-radar.md`, `docs/planejamento/registro-de-execucao.md`.

## 14. Fase 0 — situação

- [x] Plano gravado neste arquivo; PC-33, Q-50 a Q-66, V-465, checklist da etapa 09 e registro de execução atualizados.
- [x] Rascunho da mensagem à CONTAD com as perguntas: [`../pt-BR/contad-mensagem-multifontes-2026-11-24.md`](../pt-BR/contad-mensagem-multifontes-2026-11-24.md) (não enviado).
- [x] Explicação do agente para a cliente (R-23): [`../pt-BR/contad-agente-o-que-esta-instalado.md`](../pt-BR/contad-agente-o-que-esta-instalado.md) (não enviada).
- [ ] Estimativa de esforço e custo (R-25) — responsável.
- [ ] Revisão e autorização do envio da mensagem e da explicação do agente — responsável.
- [ ] Decisão de escopo D-409 (inclui o ajuste da D-393 para sinalizações bloqueantes, risco 12.1-2) — responsável.
- [ ] Mapear o que as branches não mescladas já resolvem (C-02, C-03, C-06, D-404 a D-408).

A implementação (Fase 1 em diante) só começa depois da estimativa (R-25), das respostas bloqueantes (Q-50, Q-52, Q-53, Q-58, Q-59) e do registro da D-409.

## 15. Fase 1 — entregue em modo simulação (D-409, V-466)

**O que existe**
- Pacote `src/apps/hub/multisource/`:
  - `title_position.py`: posição CP/CR do Domínio em `.xls`;
  - `francesinha.py`: francesinha Sicredi em PDF;
  - `client_cashbook.py`: caixa do cliente em `.xlsx`;
  - `matching.py`: motor de casamento;
  - `report.py`: relatórios.
- Comando `manage.py simular_multifontes`. Não grava nada no banco; escreve 4 relatórios numa pasta privada.

```bash
uv run python manage.py simular_multifontes --extrato extrato.pdf --francesinha francesinha.pdf \
  --receber CR-mes-anterior.xls --pagar CP-mes-anterior.xls --caixa caixa.xlsx --aba SICREDI \
  --aba-sem-extrato CAIXA --aba-sem-extrato CEF \
  --receber-referencia CR-mes.xls --pagar-referencia CP-mes.xls --cnpj 00000000000000 --saida /pasta/privada
```

**Resultado de outubro da SURIA** (detalhes em V-466)
- 184 movimentos:
  - 26,1% com baixa automática de títulos;
  - 96,2% identificados (título, natureza ou nota do próprio mês);
  - 7 sinalizações.
- As 7 sinalizações:
  - 4 recebimentos marketplace com comissão (Q-51);
  - 1 pagamento parcial;
  - 2 números de nota digitados no caixa diferentes do título aberto de mesmo fornecedor e valor.
- A meta da reunião (~70% automático, R-19) se mede no lançamento. Hoje, notas emitidas e pagas no próprio
  mês ficam "identificadas", sem baixa, porque não estão na posição de abertura. Para baixá-las, é preciso
  ter os títulos do mês pelo agente (S-06) ou a posição do Domínio emitida depois.

**Observações para as perguntas abertas**
- **Q-51 (marketplace):** o Domínio baixou notas da empresa do marketplace com os pagamentos à instituição de pagamento do marketplace. A R-12 diz que esses
  pagamentos vão direto para propaganda. Confirmar qual regra vale.
- **Q-66 (adiantamentos):** o Domínio baixou a NF 30094 da cliente E, ao que parece com os adiantamentos
  recebidos.
- **R-05 na prática:** a NF 29984 tem parcelas de 3.317,47 e 3.317,46. O caixa indica a parcela 3; o
  Domínio baixou a 2. A diferença de 1 centavo decide a parcela; vale confirmar com a contadora.

**Próximos passos da Fase 1**
- ~~Período configurável no agente~~ não é necessário (D-410). Comparação com o Razão pronta no comando (`--razao-pdf`/`--razao-csv`); falta obter o Razão de outubro.
- Tela de fechamento do mês, com o protocolo de UI do AGENTS.md.
- Aplicação e resgate com rendimento/IRRF (Fase 2).

## 16. Fase 2 — aplicação financeira e natureza divergente (D-411, V-468)

- `--aplicacao extrato-aplicacao.pdf` confere a cadeia de saldos do extrato de aplicação.
- Aplicações e resgates do banco (inclusive em várias linhas) são casados com o extrato da aplicação e ficam
  como transferência automática.
- Rendimentos e IRRF ficam listados para lançar na conta da aplicação; as contas dependem da Q-54.
- R-12: o mesmo CPF/CNPJ com natureza habitual no caixa e um movimento de natureza diferente vira
  sinalização. Variações de grafia são toleradas.
- Outubro da SURIA: **45,1% automático** (era 26,1%), 96,2% identificado e as mesmas 7 sinalizações.
- Próximos itens do plano que não dependem de resposta da CONTAD:
  - documentos escaneados (N-06);
  - tela de fechamento do mês;
  - lote 19 com várias partidas.

## 17. Documentos escaneados (D-412, V-469)

- `--documentos scan.pdf` (pode repetir) faz o OCR local de cada página. O boleto vale pela linha
  digitável validada; recibos, faturas, CT-e e DANFE são lidos do texto.
- Cada documento de pagamento é procurado no extrato e no caixa em dinheiro. O que não for encontrado vira
  "sem pagamento identificado" (R-11). Sem o caixa do cliente, o documento identifica o pagamento ou baixa o
  título (R-10).
- Outubro: os 40 documentos de pagamento com valor foram encontrados, incluindo o aluguel pago em dinheiro.
  Ficaram 11 leituras incertas, listadas para conferência.
- Itens restantes do plano:
  - tela de fechamento do mês (protocolo de UI);
  - lote 19 com várias partidas (depende da importação real, V-428);
  - itens que dependem das respostas Q-50 a Q-66.

## 18. Tela de fechamento do mês (D-413, V-470)

- Conciliação bancária → **Fechamento do mês (simulação)**. A pessoa escolhe a empresa, envia as fontes e vê
  o resultado na mesma página. Também pode baixar os relatórios em `.zip`. Nada é gravado.
- Os documentos escaneados continuam pelo comando: o OCR passa do limite de 30 s da requisição.
- Itens restantes do plano:
  - lançamento real e exportação (decisão própria; conflito com a D-393);
  - documentos escaneados na tela, por fila;
  - itens que dependem das respostas Q-50 a Q-66.
