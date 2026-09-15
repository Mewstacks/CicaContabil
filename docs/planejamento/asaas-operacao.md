# Operação Asaas — estado e roteiro de homologação

Atualizado em 15/09/2026. O Asaas é o meio padrão de cobrança CICA para Pix, boleto e cartão. Contratos manuais continuam fora do fluxo do provedor: um evento Asaas não pode mudar sua cobrança, seu contrato ou seu acesso.

## O que o código já recebe

O endpoint `POST /platform/webhooks/asaas/` só existe quando `ASAAS_WEBHOOK_TOKEN` está configurado no ambiente. Ele exige `Content-Type: application/json`, compara em tempo constante o cabeçalho `asaas-access-token`, limita o corpo a 64 kB e não registra a carga completa do pagamento. Cada `id` de evento é único; reentregas retornam sucesso sem repetir a alteração. Uma tentativa conhecida é localizada por `payment.id`, com provedor Asaas e ID externo único.

- `PAYMENT_RECEIVED` marca a tentativa e a fatura como pagas.
- `PAYMENT_OVERDUE` marca fatura aberta como vencida, mas nunca rebaixa uma fatura já paga.
- Falha de cartão ou exclusão encerra tentativa ainda não paga.
- Estorno, chargeback e reversão marcam a fatura como contestada; não suspendem nem reativam o escritório por inferência.
- Evento sem tentativa correspondente fica registrado como ignorado, para reconciliação, sem tocar uma fatura manual.

O desenho segue a documentação oficial: o Asaas usa o token no cabeçalho `asaas-access-token`, pode reenviar eventos e espera retorno HTTP 200. [Receber eventos Asaas](https://docs.asaas.com/docs/receive-asaas-events-at-your-webhook-endpoint) e [eventos de cobranças](https://docs.asaas.com/docs/payment-events) são as fontes operacionais.

## Roteiro que falta homologar

1. Definir `ASAAS_WEBHOOK_TOKEN` forte e exclusivo no ambiente, sem reutilizar a API key; cadastrar endpoint HTTPS público e apenas os eventos de pagamento necessários no Sandbox.
2. Implementar e testar a criação idempotente de cliente, cobrança e `PaymentAttempt` para Pix, boleto e cartão. A CICA ainda não possui dados comerciais finais nem autorização para fazer chamadas externas.
3. Exercitar no Sandbox: criado, confirmado, recebido, atraso, falha, reentrega, evento fora de ordem, estorno e chargeback; guardar IDs, resultado e evidência sem dados sensíveis.
4. Confirmar as regras Q-01 a Q-06 de [dúvidas abertas](duvidas-abertas.md) antes de ligar carência, somente leitura, suspensão ou reativação a qualquer evento.
5. Repetir o roteiro com uma cobrança autorizada em produção somente após custo, ambiente, chave e responsável terem confirmação explícita.

O token do webhook, API key, cliente, cobrança e webhook externo não foram criados nesta máquina.
