# CICA × CONTAD — uso direto (D-393)

A CONTAD usa a CICA sem etapas de conferência. O que a CICA calcula aparece e vale como está;
nada fica esperando revisão de ninguém. Este guia substitui o treinamento.

## O dia a dia em 4 passos

1. **Conciliação bancária → Importar extrato.** Escolha a empresa, a conta e anexe o **OFX** do mês.
   (No início, “Abrir conciliação” leva direto para lá; na *Conciliação por empresa*, cada empresa sem
   extrato tem o botão “Importar extrato”.)
   - Se a conta ainda não existe, escolha a conta do Domínio marcada “vincula pelo OFX”.
   - Se a empresa não tem conta de banco no plano do Domínio (ou não tem plano), escolha
     **“Conta do extrato, lida do OFX (sem Razão)”**. O extrato entra e pode ser consultado,
     mas não há Razão para comparar nem lançamento para enviar.
2. **Espere o Razão chegar.** A CICA pede o Razão do mês sozinha e, quando ele chega:
   - confirma tudo o que bate exatamente (data, valor, direção e conta), inclusive valores repetidos
     no mesmo dia quando o extrato e o Razão têm a mesma quantidade deles;
   - aprende com o Razão as regras DE-PARA e já as deixa **ativas**;
   - para os movimentos que **não estão no Razão** e que uma regra reconhece, gera e aprova o
     lançamento sozinha.
3. **Ver resultado** do extrato: cada quadro mostra quantos movimentos tiveram cada destino (clique
   para filtrar a lista) e cada movimento diz o que aconteceu — *Conferido com o Razão*,
   *Lançado pela CICA*, *Enviado ao Domínio*, *No Razão · valor repetido*, *Parecido com o Razão · não
   lançado* (há registro do mesmo valor até 5 dias de diferença) ou *Sem regra · não lançado*.
   O relatório mostra saldos e diferenças do mês.
4. **Conciliação bancária → Exportações → Validar e gerar arquivo.** O painel mostra quantos lançamentos estão
   prontos e quais aguardam o **Razão atualizado** daquele mês: antes de ir no arquivo, cada lançamento
   da CICA espera um Razão lido depois dele, para não duplicar o que o escritório já lançou à mão
   (clique em *Atualizar Razão*). Baixe o .txt e importe no Domínio: *Utilitários → Importação →
   Importador*, Tipo TXT, “Lançamentos Contábeis em Lote (Leiaute Domínio Sistemas)”. O histórico de
   cada lançamento traz o texto do extrato (por exemplo, o número do boleto).

## O que a CICA nunca faz sozinha

- Não escreve direto no Domínio: só gera o arquivo; quem importa é a CONTAD.
- Não lança o que já está no Razão, nem movimento parecido com um registro do Razão (mesmo valor e
  direção, até 5 dias de diferença) — esses ficam de fora para não duplicar. Se o Razão novo mostrar
  que o escritório já lançou, o lançamento da CICA ainda não enviado é retirado sozinho.
- Não aceita OFX de uma conta que já pertence a outra empresa do escritório.
- Não exporta o mesmo lançamento duas vezes.
- Não inventa conta no plano do Domínio.

## Ainda manual (opcional)

- Movimento sem regra (por exemplo, um tipo de pagamento que nunca apareceu no Razão) fica sem
  lançamento até existir histórico suficiente; nada impede consultar ou classificar à mão.
- “Registrar revisão (opcional)” na conferência continua disponível, sem obrigação.
- Títulos e baixas: cada busca no Domínio é interpretada sozinha (juros, multa, desconto e retenções
  pelos tipos oficiais) e aparece em *Títulos e baixas* com o número da nota. Só aparece quando a
  empresa tem conta bancária (importe o OFX dela); a lista de buscas avisa quando falta a conta.
  Serviços e casos fora do padrão (estorno, valor negativo, tipo desconhecido) ficam só como fonte
  recebida.
- IA (Claude Haiku 5.5): para movimentos que nunca apareceram no Razão, sugere a conta entre as que a
  empresa já usa; só vira regra ativa se acertar 90% ou mais num teste às cegas contra o Razão.
  Se uma medição nova ficar abaixo de 90%, as regras da IA voltam a rascunho e os lançamentos delas
  ainda não enviados são retirados. Teto de US$ 1/dia e US$ 5/mês.
