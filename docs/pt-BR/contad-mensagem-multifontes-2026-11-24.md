# Rascunho — mensagem à CONTAD após a reunião de 24/11/2026

> **RASCUNHO, NÃO ENVIADO** (revisto em 25/11/2026 com as evidências da D-420/V-477). Revisar e autorizar antes de enviar (AGENTS.md: nenhuma mensagem por inferência).
> A estimativa de esforço e custo (pedido da reunião) é do responsável e deve acompanhar ou anteceder esta mensagem;
> nenhum valor ou prazo foi escrito aqui. Os IDs entre parênteses são internos e podem ser removidos no envio.

---

**Assunto:** Conciliação da SURIA com várias fontes — resumo da reunião e perguntas

Olá, equipe CONTAD,

Obrigado pela reunião de hoje e pelo envio dos documentos de outubro da SURIA. Resumo do que entendemos:

- Para lançar o mês, o conciliador vai cruzar o extrato com a francesinha, a posição de contas a receber e a
  pagar do mês anterior, a planilha de caixa da cliente, o extrato da aplicação e os documentos escaneados.
- Como as baixas deixarão de ser feitas no Domínio, a CICA vai manter os títulos em aberto e emitir, no fim do
  mês, a posição por nota fiscal.
- O que o sistema não conseguir identificar com segurança não será lançado: aparecerá numa lista de pendências,
  com o motivo, para vocês decidirem. Cada decisão pode virar regra daquela empresa.
- Outubro será processado primeiro em modo de teste, sem gerar arquivo para o Domínio, e comparado com o Razão
  que vocês já lançaram. Novembro roda no sistema no início de dezembro.

Antes de perguntar, olhamos os arquivos que vocês nos enviaram: o Razão de setembro da conta Banco Sicredi,
o plano de contas da SURIA, as posições de contas a receber e a pagar de setembro e outubro, a francesinha e o
caixa de outubro. Para a maior parte das dúvidas, o próprio material mostra como vocês fazem hoje. Por isso,
pedimos que **confirmem ou corrijam** o que encontramos. Até a confirmação, o sistema só mostra essas contas
como sugestão; nada é lançado.

**O que encontramos nos arquivos — confirmam?**

1. **Clientes e fornecedores (Q-50).** O plano tem uma conta para cada cliente (3.067) e para cada fornecedor
   (739). No Razão do banco, vocês usam contas de passagem: recebimentos (cobrança e PIX) contra **9 —
   COBRANÇA** e pagamentos (boleto e PIX) contra **4 — PAGAMENTO DE FORNECEDORES**. Entendemos que a baixa de
   cada nota é que leva o valor da conta de passagem para a conta do cliente ou do fornecedor. Como a baixa
   passa a ser feita pela CICA, a proposta é gerar esse segundo lançamento: COBRANÇA × conta do cliente e
   conta do fornecedor × PAGAMENTO DE FORNECEDORES, uma linha por nota. O código do cliente e do fornecedor
   no relatório de contas a receber e a pagar é o próprio código da conta no plano (147 de 151 clientes e
   17 de 19 fornecedores de setembro), e é por ele que a CICA localiza a conta. O lançamento do banco
   continua como hoje. É assim?
2. **Juros recebidos (Q-53).** Em setembro, a cobrança foi lançada pelo total, com os juros juntos, contra
   COBRANÇA. A proposta é separar, na baixa, o valor da nota (conta do cliente) e os juros e a multa em
   **132 — JUROS ATIVOS**. Desconto concedido iria para **230 — DESCONTOS CONCEDIDOS**. Usam outra conta
   para a multa?
3. **"Seu Nº" da francesinha (Q-52).** O formato `*1NNNNNNPP` traz o número da nota (6 dígitos) e a parcela
   (2 dígitos): as 51 notas de outubro nesse formato existem no caixa da cliente. O formato `XX0000nnnn`
   parece uma numeração sequencial do boleto, sem relação com a nota. Esse número aparece em algum
   relatório que ligue o boleto à nota?
4. **Tolerância de valor (Q-58).** Propomos tolerância zero: em outubro nenhuma pendência foi causada por
   centavos. Concordam?
5. **"Total Geral" dos relatórios de contas a receber e a pagar (Q-59).** A diferença foi sempre uma nota sem
   saldo que o relatório não detalha. No a pagar de setembro, uma nota de 793,40, já paga, entra no total
   mas não aparece nas linhas. No a receber de outubro, uma nota aparece com valor zero na linha e 9.110,46
   no total. O saldo fecha nos dois casos. É o comportamento esperado do relatório?
6. **Aplicação (Q-54).** Aplicações e resgates foram lançados contra **13 — APLICAÇÃO SICREDINVEST
   AUTOMATICO**. Para o rendimento e o IRRF, propomos **134 — RECEITA DE APLICAÇÕES FINANCEIRAS** e **232 —
   IRRF S/ APLICAÇÃO FINANCEIRA**, por resgate, como aparece no extrato da aplicação. Vimos também contas
   de provisão (14, 15 e 16). Qual das duas formas vocês usam?
7. **Empréstimo Sicredi (Q-55).** A parcela 02/35 foi dividida entre o contrato (117, principal 8.850,94) e
   **231 — JUROS PASSIVOS** (122,39). O cronograma do banco só traz o total da parcela. De onde vem a
   divisão entre principal e juros a cada mês? Existe cronograma do empréstimo da Caixa Econômica?
8. **Fatura do cartão (Q-56).** Em setembro, a fatura foi lançada pelo total contra PAGAMENTO DE
   FORNECEDORES. Seguimos assim, ou cada despesa da fatura deve ser lançada?
9. **Caixa e Caixa Econômica (Q-57).** O saque foi lançado contra **1 — CAIXA** e a transferência contra
   **3 — CAIXA ECONOMICA FEDERAL**. Em outubro, a CICA já liga a saída de um lado com a entrada do outro
   (5.000,00 para a Caixa Econômica e 30.000,00 para o caixa). Usamos essas contas?
10. **Folha, guias e sócios (Q-66).**
    - Folha: o débito foi lançado contra PAGAMENTO DE FORNECEDORES.
    - Guias: FGTS (75), Simples (100), ICMS diferencial (83), consignado (78) e tributos federais, estes
      divididos entre IRRF, INSS e contribuições.
    - Sócios: os PIX foram lançados como empréstimo aos sócios (385 e 386), meio a meio.
    - O caixa de outubro descreve um PIX aos sócios como "distribuição de lucros". Continua como
      empréstimo?
11. **Marketplace (Q-51).** Na reunião, os PIX para a instituição de pagamento do marketplace foram descritos
    como despesa de propaganda. Em setembro, porém, foram lançados como pagamento de fornecedor, e a baixa
    foi em notas do marketplace. Qual vale? Como ratear a comissão por nota?

**Ainda sem resposta nos arquivos**

12. Critério de aceite: % automático mínimo e taxa de erro tolerada? Novembro roda em paralelo com a
    operadora ou só no sistema? Quem valida? (Q-60)
13. Daqui em diante, qual é a posição oficial dos títulos: a da CICA ou a do Domínio? O fiscal seguirá
    emitindo o CP/CR do mês anterior, ou a CICA o substitui? (Q-61)
14. Quem importa o `.txt` no Domínio e quando dá para fazer a importação real de teste? (Q-62)
15. É possível obter o extrato da Caixa Econômica em OFX ou PDF, em vez de texto copiado no Word? (Q-63)
16. O "Conciliador Contábil" citado como referência: qual produto ou tela é? Quais funções eram usadas? (Q-64)
17. Como os arquivos chegarão todo mês (envio pela tela do CICA, por quem, até que dia) e por quanto tempo
    guardar? (Q-65)

Para compararmos o resultado com o que vocês já lançaram em outubro, pedimos também o **Razão da conta
8 — Banco Sicredi da SURIA, de 01/10/2026 a 31/10/2026, em PDF**, exportado do Domínio no mesmo modelo do
Razão de setembro que vocês nos enviaram. Se possível, mandem também o Razão de outubro do caixa em dinheiro
e da Caixa Econômica, no mesmo modelo.

Sobre o servidor: segue em anexo uma explicação curta do que está instalado e do que ele faz.

Assim que a primeira parte estiver pronta para olharmos juntos, avisamos.

Abraço,
