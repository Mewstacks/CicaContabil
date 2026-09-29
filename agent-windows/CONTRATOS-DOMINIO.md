# Contratos DomÃ­nio observados â€” Fedrizzi

Data da descoberta: 18/09/2026. Fonte: metadados ODBC do DSN DomÃ­nio jÃ¡ configurado no escritÃ³rio. Nenhum dado de origem Ã© copiado neste documento.

## Regras comuns

- O agente usa somente consultas allowlisted no cÃ³digo-fonte; nÃ£o recebe SQL remoto.
- Leitura Ã© somente leitura, por empresa e perÃ­odo quando o contrato possuir esse campo.
- Envio Ã© paginado em atÃ© 500 registros e idempotente pela chave externa do contrato.
- Uma tabela descoberta nÃ£o entra automaticamente em IA, automaÃ§Ã£o ou exportaÃ§Ã£o: cada contrato precisa de implementaÃ§Ã£o, teste e aprovaÃ§Ã£o de pacote semÃ¢ntico.

## ContÃ¡bil

| Fonte observada | Chave proposta | Campos observados necessÃ¡rios | Finalidade | Estado |
| --- | --- | --- | --- | --- |
| `CTLANCTOFCONT` | `CODI_EMP + CODI_LOTE + SEQUENCIAL` | `CODI_EMP`, `CODI_LOTE`, `SEQUENCIAL`, `DATA_FCONT`, `DEBITO`, `CREDITO`, `I_HISTORICO`, `HISTORICO`, `VALOR` | LanÃ§amentos contÃ¡beis para conferÃªncia e conciliaÃ§Ã£o | Estrutura confirmada; consulta e espelho pendentes |
| `CTEXTRATO_BANCARIO_LANCAMENTO_ITEM` | `CODI_EMP + I_LANCAMENTO + I_ITEM` | `CODI_EMP`, `I_LANCAMENTO`, `I_ITEM`, `DATA_ITEM`, `HISTORICO`, `DOCUMENTO`, `VALOR`, `TIPO` | MovimentaÃ§Ã£o bancÃ¡ria para conciliaÃ§Ã£o | Consulta allowlisted jÃ¡ validada |

## Fiscal

**Contrato de catálogo para backup:** `bethadba.EFACUMULADOR`, chave
`CODI_EMP + CODI_ACU`, com somente empresa, código, nome e data de inativação.
A consulta allowlisted está implementada no agente e envia páginas de até 500 registros
como `accumulator_catalog`. Ela não lê parâmetros de cálculo nem interpreta tributação.

Para reconhecer o acumulador em uma NFS-e posterior, o agente também envia
`accumulator_observations`. A consulta agrega na origem os serviços emitidos e as entradas de
serviço por empresa, acumulador, código de serviço disponível e cliente/fornecedor. O documento
da contraparte é convertido localmente em SHA-256 truncado antes de sair da máquina; nomes,
número da nota, valores, descrição e XML histórico não são transmitidos. Cada linha contém apenas
`company_key`, `accumulator_code`, `service_code`, `counterparty_ref`, `frequency` e
`last_used_at`. O servidor recusa critério vazio e acumulador fora do catálogo da própria empresa.
Correspondências ambíguas permanecem em revisão humana.
A execução no backup 07129 aguarda a credencial de usuário Externo cadastrada nesse
escritório; `DBA/sql` e login integrado foram recusados pelo próprio banco.

| Fonte observada | Chave proposta | Campos observados necessÃ¡rios | Finalidade | Estado |
| --- | --- | --- | --- | --- |
| `FONOTA_FISCAL_SERVICOS_PRESTADOS` | `CODI_EMP + I_SERVICOS + I_SERVICO_PRESTADO` | empresa, serviÃ§o, cliente, data, sÃ©rie, nÃºmero, valor bruto, valor dos serviÃ§os, deduÃ§Ãµes e retenÃ§Ãµes | ConferÃªncia de NFS-e emitidas | Estrutura confirmada; nÃ£o habilitada |
| `FONOTA_FISCAL_SERVICOS_TOMADOS` | `CODI_EMP + I_SERVICOS + I_SERVICO_TOMADO` | empresa, fornecedor, data, sÃ©rie, nÃºmero, valor bruto e retenÃ§Ãµes | ConferÃªncia de NFS-e tomadas | Estrutura confirmada; nÃ£o habilitada |
| `EFACUMULADOR_VIGENCIA_IMPOSTOS` | `CODI_EMP + CODI_ACU + VIGENCIA_ACU + CODI_IMP` | empresa, acumulador, vigÃªncia, imposto e parÃ¢metros de cÃ¡lculo | CatÃ¡logo fiscal por empresa | Estrutura confirmada; nÃ£o habilitada |

## Folha

| Fonte observada | Chave proposta | Campos observados necessÃ¡rios | Finalidade | Estado |
| --- | --- | --- | --- | --- |
| `FOVGUIAINSS` | `CODI_EMP + I_GUIAINSS` | empresa, competÃªncia, tipo de guia/processo, vencimento e valores | Guias calculadas para revisÃ£o; nÃ£o representa documento oficial DCTFWeb | Consulta allowlisted jÃ¡ validada |
| `FOVBASES` | `CODI_EMP + I_EMPREGADOS + COMPETENCIA + TIPO_PROCESS` | empresa, competÃªncia, bases, proventos, descontos e IRRF | ConferÃªncia agregada de folha | Estrutura confirmada; contÃ©m dados pessoais e nÃ£o estÃ¡ habilitada |

## Limites que continuam explÃ­citos

- A confirmaÃ§Ã£o semÃ¢ntica dos cÃ³digos de tipo, situaÃ§Ã£o e direÃ§Ã£o continua necessÃ¡ria antes de qualquer decisÃ£o automÃ¡tica.
- O agente atual envia empresas; o endpoint legado pode receber guias calculadas, mas nenhuma rota efetiva lÃª ou envia fechamento, reabertura ou aceite oficial. O campo `SITUACAO` observado em `FOVGUIAINSS` nÃ£o tem equivalÃªncia aprovada e nÃ£o pode virar "fechado", "aceito" ou "pago".
- A documentaÃ§Ã£o oficial confirma que fechamento da competÃªncia e envio do S-1299 sÃ£o operaÃ§Ãµes distintas; tambÃ©m condiciona a transmissÃ£o DCTFWeb a S-1299 e/ou R-2099 enviados. Isso sustenta a separaÃ§Ã£o da central, mas nÃ£o Ã© um contrato de leitura: [fechamento da folha](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=32) e [DCTFWeb via API](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=10985).
- Antes de criar consulta allowlisted que alimente `record_source_observation`, aprovar objeto/consulta, chave de empresa e competÃªncia, cÃ³digos de estado, exemplos mascarados e a equivalÃªncia de cada valor com o estado CICA. Descoberta de metadados nÃ£o substitui essa aprovaÃ§Ã£o.
- As tabelas de folha com empregado, endereÃ§o, CPF ou dados equivalentes ficam classificadas como pessoais/restritas e nÃ£o podem sair para IA por API sem a polÃ­tica de dados da etapa 05.
- A execuÃ§Ã£o contra backup DomÃ­nio Web, retomada de rede e prova de nÃ£o duplicaÃ§Ã£o ainda precisam de uma amostra de backup autorizada.

## Pesquisa documental atualizada — 24/09/2026

A consulta à Central de Soluções do Domínio confirma que fechar/reabrir a competência no módulo Folha bloqueia ou libera cálculo e não é o envio S-1299; a orientação também separa a validação do S-1299 e a transmissão da DCTFWeb. A configuração de transmissão via API exige S-1299 e/ou R-2099 previamente enviados. Fontes: [fechamento/reabertura de competência](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=32), [envio S-1299](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=4576&intencaoID=2&modulosSelecionados=0&palavraChave=esocial) e [DCTFWeb via API](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=10985).

Essas publicações descrevem operação do produto, não um contrato público de leitura pelo agente, nem os códigos/semântica de uma tabela para atualizar `activity_processing_status` ou `activity_obligation_status`. A pesquisa não habilita query nova nem capacidade de fonte. Antes da ligação, permanece obrigatório aprovar a consulta allowlisted, chave empresa/competência, valores de origem, exemplos mascarados e mapeamento CICA.
