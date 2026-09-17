# Auditoria da coleta NFS-e ADN — 16/09/2026

## Contrato oficial adotado

O [Manual de Contribuintes das APIs do ADN](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-atual/manual-contribuintes-apis-adn-sistema-nacional-nfse.pdf) documenta a consulta de documentos em que o contribuinte figura como emitente, tomador ou intermediário por `GET /DFe/{NSU}` e permite certificado do mesmo CNPJ raiz quando o CNPJ consultado é informado. A [lista oficial de ambientes](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/apis-prod-restrita-e-producao) identifica os hosts de produção restrita e produção. O Manual Integrado determina lotes de até 50 DF-e em NSU crescente e espera mínima de uma hora quando o último NSU alcança o maior NSU disponível.

## Implementado

- Cliente somente leitura com origens oficiais fixas, TLS 1.2+, mTLS e resposta limitada a 12 MB.
- PKCS#12 armazenado de forma cifrada, convertido em arquivo PEM temporário removido assim que o contexto TLS é carregado.
- Validade, revogação e CNPJ raiz do A1 conferidos antes da consulta.
- Parâmetros `lote=true` e `cnpjConsulta`; envelope limitado a 50 documentos em NSU estritamente crescente.
- XML UTF-8 em texto, base64 ou gzip/base64, limitado a 4 MB, sem `DOCTYPE` e analisado com `defusedxml`.
- Persistência de toda a página e avanço do checkpoint na mesma transação. XML inválido ou NSU inconsistente desfaz o lote inteiro.
- Deduplicação por escritório, empresa e hash, com unicidade adicional do NSU por empresa.
- Worker com lease, limite de 10 páginas por execução, retentativa exponencial e agendamento de uma hora quando alcança o fim.
- Tela operacional com cobertura de certificado, seleção de todas as empresas exibidas, ativação, pausa, nova tentativa, último sucesso, próxima execução, erro e checkpoint.
- Demo altera apenas o progresso da sessão e nunca abre certificado nem chama o ADN.

## Limite atual e prova pendente

`NFSE_ADN_SYNC_ENABLED=false` é o padrão. Os testes usam envelopes e XMLs sintéticos e provam transação, isolamento e recuperação locais; não provam a cadeia ICP-Brasil, nomes exatos de todos os campos retornados pelo Swagger vivo, cobertura dos atores nem limites aplicados pelo fornecedor. A ativação comercial exige um piloto autorizado em produção restrita, conferência manual dos primeiros XMLs e teste de retomada sem duplicidade. Nenhum acesso externo foi feito nesta auditoria.
