# CICA — matriz de capacidades Domínio e Siescon

Atualizada em 18/09/2026, na etapa 04. Esta matriz descreve código e contratos disponíveis; não transforma preparação local em homologação de fornecedor ou promessa comercial.

| Capacidade | Domínio | Siescon | Limite vigente |
| --- | --- | --- | --- |
| Cadastro de fonte | Fonte local/Web e API oficial modeladas | Fonte `siescon` modelada, inicialmente sem configuração | Siescon não recebe credenciais nem ativa sincronização sem Q-33. |
| Leitura de empresas | Agente local somente leitura e páginas v2 preparados | Sem adaptador | Exige versão, mecanismo autorizado e schema Siescon. |
| Leitura contábil, fiscal e folha | Consultas Domínio allowlisted conforme pacote semântico aprovado | Sem adaptador | Não inferir nomes de tabela, campos ou permissões Siescon. |
| Espelho CICA | Espelho idempotente por pacote semântico | Reutilizável após contrato revisado | O espelho não aceita SQL recebido remotamente. |
| Exportação de lançamentos | Destino e adaptador Domínio versionados; operação continua condicionada à homologação | Destino modelado, recusado sem adaptador/layout revisados | Nenhum arquivo Siescon é gerado nesta fase. |
| Escrita no sistema de origem | Não permitida | Não permitida | D-54 permite somente leitura e exportação revisada. |

## Próximo contrato necessário

Para registrar o adaptador Siescon, o responsável técnico deve fornecer por canal seguro a versão instalada, mecanismo de leitura somente leitura, schema/campos autorizados, identificador de empresa, cursor de atualização e layout de exportação/importação. A implementação só começa depois de revisar esse material; o piloto e a importação conferida pertencem à etapa 12 por D-87.
