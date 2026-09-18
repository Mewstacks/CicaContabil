# Contratos Domínio observados — Fedrizzi

Data da descoberta: 18/09/2026. Fonte: metadados ODBC do DSN Domínio já configurado no escritório. Nenhum dado de origem é copiado neste documento.

## Regras comuns

- O agente usa somente consultas allowlisted no código-fonte; não recebe SQL remoto.
- Leitura é somente leitura, por empresa e período quando o contrato possuir esse campo.
- Envio é paginado em até 500 registros e idempotente pela chave externa do contrato.
- Uma tabela descoberta não entra automaticamente em IA, automação ou exportação: cada contrato precisa de implementação, teste e aprovação de pacote semântico.

## Contábil

| Fonte observada | Chave proposta | Campos observados necessários | Finalidade | Estado |
| --- | --- | --- | --- | --- |
| `CTLANCTOFCONT` | `CODI_EMP + CODI_LOTE + SEQUENCIAL` | `CODI_EMP`, `CODI_LOTE`, `SEQUENCIAL`, `DATA_FCONT`, `DEBITO`, `CREDITO`, `I_HISTORICO`, `HISTORICO`, `VALOR` | Lançamentos contábeis para conferência e conciliação | Estrutura confirmada; consulta e espelho pendentes |
| `CTEXTRATO_BANCARIO_LANCAMENTO_ITEM` | `CODI_EMP + I_LANCAMENTO + I_ITEM` | `CODI_EMP`, `I_LANCAMENTO`, `I_ITEM`, `DATA_ITEM`, `HISTORICO`, `DOCUMENTO`, `VALOR`, `TIPO` | Movimentação bancária para conciliação | Consulta allowlisted já validada |

## Fiscal

| Fonte observada | Chave proposta | Campos observados necessários | Finalidade | Estado |
| --- | --- | --- | --- | --- |
| `FONOTA_FISCAL_SERVICOS_PRESTADOS` | `CODI_EMP + I_SERVICOS + I_SERVICO_PRESTADO` | empresa, serviço, cliente, data, série, número, valor bruto, valor dos serviços, deduções e retenções | Conferência de NFS-e emitidas | Estrutura confirmada; não habilitada |
| `FONOTA_FISCAL_SERVICOS_TOMADOS` | `CODI_EMP + I_SERVICOS + I_SERVICO_TOMADO` | empresa, fornecedor, data, série, número, valor bruto e retenções | Conferência de NFS-e tomadas | Estrutura confirmada; não habilitada |
| `EFACUMULADOR_VIGENCIA_IMPOSTOS` | `CODI_EMP + CODI_ACU + VIGENCIA_ACU + CODI_IMP` | empresa, acumulador, vigência, imposto e parâmetros de cálculo | Catálogo fiscal por empresa | Estrutura confirmada; não habilitada |

## Folha

| Fonte observada | Chave proposta | Campos observados necessários | Finalidade | Estado |
| --- | --- | --- | --- | --- |
| `FOVGUIAINSS` | `CODI_EMP + I_GUIAINSS` | empresa, competência, tipo de guia/processo, vencimento e valores | Guias calculadas para revisão; não representa documento oficial DCTFWeb | Consulta allowlisted já validada |
| `FOVBASES` | `CODI_EMP + I_EMPREGADOS + COMPETENCIA + TIPO_PROCESS` | empresa, competência, bases, proventos, descontos e IRRF | Conferência agregada de folha | Estrutura confirmada; contém dados pessoais e não está habilitada |

## Limites que continuam explícitos

- A confirmação semântica dos códigos de tipo, situação e direção continua necessária antes de qualquer decisão automática.
- As tabelas de folha com empregado, endereço, CPF ou dados equivalentes ficam classificadas como pessoais/restritas e não podem sair para IA por API sem a política de dados da etapa 05.
- A execução contra backup Domínio Web, retomada de rede e prova de não duplicação ainda precisam de uma amostra de backup autorizada.
