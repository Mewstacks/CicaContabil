# Perguntas ao Serpro — Integra Contador (rascunho para envio pelo titular do contrato)

Rascunho de 23/11/2026. **Não enviado.** Quem envia é o titular do contrato, pela Área do Cliente ou pela Central de Ajuda do Serpro. As respostas por escrito destravam: persistência de dados do Serpro no CICA, uso de IA sobre esses dados, o modelo de contratação por escritório e o faturamento. Origem das dúvidas: [relatório de pesquisa](../pesquisa/serpro-integra-contador-mcp.md), seções 4 e 6; spec [cica-venda-v2](../specs/cica-venda-v2.md), seção 4.

## Texto sugerido

Assunto: Integra Contador — esclarecimentos sobre armazenamento, uso de IA, múltiplos escritórios e cobrança

[Razão social e CNPJ do contratante] contratou o Integra Contador e opera uma plataforma de software para escritórios de contabilidade. Cada escritório é o autor do pedido de dados e cada cliente do escritório outorga autorização de acesso ao escritório. Pedimos resposta por escrito às perguntas abaixo, com a cláusula ou a página da documentação em que se apoia.

1. **Armazenamento.** O contrato do Integra Contador tem cláusula de não armazenar ou reproduzir os dados obtidos? O que conta como armazenar: guardar o PDF, o XML ou o JSON da resposta? Guardar uma tabela derivada (por exemplo, "declarou", "DAS pago", "em malha")? Existe prazo máximo de retenção ou de cache permitido para conferência mensal?
2. **Inteligência artificial.** É permitido enviar respostas do Integra Contador a um operador de IA (modelo de linguagem) contratado pela software house ou pelo escritório? Em que condições (processamento no Brasil, sem retenção, sem treinamento com os dados)? Se não for permitido, qual tratamento é aceito (por exemplo, enviar só achados derivados, sem o documento)?
3. **Software house com vários escritórios.** A contratante pode atender vários escritórios, cada um assinando o Termo de Autorização, com as mesmas credenciais? Como o consumo de cada escritório aparece na fatura (por `X-Request-Tag`, por autor do pedido)?
4. **Termo de Autorização.** Qual a vigência máxima do campo `vigencia`? O mesmo XML assinado pode ser reenviado enquanto a vigência e o certificado valerem? O Termo é obrigatório quando o autor do pedido difere do contratante, mesmo que o autor tenha autorização de acesso do contribuinte?
5. **Limites.** Qual o limite de requisições por segundo por contrato e qual o SLA de disponibilidade?
6. **Cobrança de Apoiar e Monitorar.** Os caminhos `/Apoiar` e `/Monitorar` (por exemplo SITFIS `SOLICITARPROTOCOLO91`, Caixa Postal `INNOVAMSG63`, `EVENTOSATUALIZACAO`) são cobrados? A Loja os lista em "Consulta dados" e "Emissão de documentos", enquanto a documentação diz que não são bilhetados.
7. **Faixas.** "Calculado direto na faixa do consumo" significa que o preço da faixa vale para todas as chamadas do mês na categoria (Consulta, Emissão, Declaração)? A faixa é por categoria e por mês?
8. **Entidade representativa.** Se o escritório for associado a um sindicato contábil com contrato Serpro, o consumo dele soma na faixa da entidade? A contratante da software house participa dessa soma?

## O que fazer com as respostas

| Resposta | Efeito no CICA |
|---|---|
| 1 permite guardar resposta ou derivado | liberar `UsageEvent`/snapshot de achados e, se couber, PDF e XML com retenção mínima (hoje: nada persiste além da sessão, salvo achados derivados) |
| 2 permite IA com condições | liberar o Serpro no copiloto e no MCP externo conforme as condições; hoje fica bloqueado |
| 3 e 4 confirmam o modelo (b) | implementar o Termo de Autorização (T10.3 b) |
| 3 e 4 não confirmam | cada escritório contrata com o próprio e-CNPJ (T10.3 a) |
| 6 e 7 | ajustar o governador de custo e a tabela de repasse |
