# CICA — matriz de capacidades Domínio e Siescon

Atualizada em 28/09/2026, na etapa 04. Esta matriz descreve código e contratos disponíveis; não transforma preparação local em homologação de fornecedor ou promessa comercial.

| Capacidade | Domínio | Siescon | Limite vigente |
| --- | --- | --- | --- |
| Cadastro de fonte | Fonte local/Web e API oficial modeladas | Fonte `siescon` e conector próprio modelados | A sincronização global nasce desligada; só o conector Siescon habilitado permite despachar essa origem. |
| Leitura de empresas | Agente local somente leitura e páginas v2 preparados | Consulta inferida fixada por hash e ponte ODBC x86; colunas conferidas antes do envio | Falta ensaio no ERP autorizado da CICA e conferência dos cadastros. |
| Leitura contábil, fiscal e folha | Consultas Domínio allowlisted conforme pacote semântico aprovado | Folha inferida preparada; usuários e tributação fora de despacho; contas e lançamentos sem contrato | Situação dos usuários, regime e dados contábeis precisam de confirmação ou layout. |
| Espelho CICA | Espelho idempotente por pacote semântico | Ingestão de Rentabilidade separada por origem e conector | O agente não aceita SQL recebido remotamente; DDF inferido pode variar após atualização. |
| Exportação de lançamentos | Destino e adaptador Domínio versionados; operação continua condicionada à homologação | Destino modelado, recusado sem adaptador/layout revisados | Nenhum arquivo Siescon é gerado nesta fase. |
| Escrita no sistema de origem | Não permitida | Não permitida | D-54 permite somente leitura e exportação revisada. |

## Próximo contrato necessário

D-290 aceitou o levantamento inferido do Lucrums para implementar a leitura local. Para concluir, é preciso acesso autorizado ao ERP para ensaio dos DDFs em cópia, conferência dos campos e empresas, além do layout efetivamente aceito para importar lançamentos. O piloto e a importação conferida pertencem à etapa 12 por D-87.
