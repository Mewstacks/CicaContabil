# CICA × CONTAD — uso direto (D-393)

A CONTAD usa a CICA sem etapas de conferência. O que a CICA calcula aparece e vale como está;
nada fica esperando revisão de ninguém. Este guia substitui o treinamento.

## O dia a dia em 4 passos

1. **Conciliação → Nova importação.** Escolha a empresa, a conta e anexe o **OFX** do mês.
   - Se a conta ainda não existe, escolha a conta do Domínio marcada “vincula pelo OFX”.
   - Se a empresa não tem conta de banco no plano do Domínio (ou não tem plano), escolha
     **“Conta do extrato, lida do OFX (sem Razão)”**. O extrato entra e pode ser consultado,
     mas não há Razão para comparar nem lançamento para enviar.
2. **Espere o Razão chegar.** A CICA pede o Razão do mês sozinha e, quando ele chega:
   - confirma tudo o que bate exatamente (data, valor, direção e conta);
   - aprende com o Razão as regras DE-PARA e já as deixa **ativas**;
   - para os movimentos que **não estão no Razão** e que uma regra reconhece, gera e aprova o
     lançamento sozinha.
3. **Ver relatório** na conferência do extrato: saldos, movimentos e diferenças do mês.
4. **Conciliação → Exportações → Validar e gerar arquivo.** Baixe o .txt e importe no Domínio:
   *Utilitários → Importação → Importador*, Tipo TXT, “Lançamentos Contábeis em Lote (Leiaute
   Domínio Sistemas)”.

## O que a CICA nunca faz sozinha

- Não escreve direto no Domínio: só gera o arquivo; quem importa é a CONTAD.
- Não lança o que já está no Razão, nem movimento parecido com um registro do Razão (mesma data,
  valor e direção) — esses ficam de fora para não duplicar.
- Não exporta o mesmo lançamento duas vezes.
- Não inventa conta no plano do Domínio.

## Ainda manual (opcional)

- Movimento sem regra (por exemplo, um tipo de pagamento que nunca apareceu no Razão) fica sem
  lançamento até existir histórico suficiente; nada impede consultar ou classificar à mão.
- “Registrar revisão (opcional)” na conferência continua disponível, sem obrigação.
- Títulos e baixas: a fonte recebida do Domínio aparece como veio, sem aviso de conferência.
- IA como segunda opinião continua desligada (depende de chave e limite de custo).
