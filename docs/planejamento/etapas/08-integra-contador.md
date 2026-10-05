# Etapa 08 — Concluir Central Integra Contador

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Em andamento em 21/09/2026. V-034 validou localmente DTE, DCTFWeb, PARCSN, consumo e retorno incerto; V-051 retestou o parser PARCSN, V-062 tipou a reserva DTE entre os livros de consumo, V-064 tipou serviços/tarefas locais, V-068 concluiu a verificação estática global e V-074/V-075/V-077/V-083 eliminaram cortes silenciosos nas carteiras, no histórico de Parcelamentos e no histórico DTE. V-094 preservou as páginas independentes das mensagens e do histórico DTE. Não houve chamada Serpro, credencial ou documento real.

**Dependências:** 02 e controles de consumo da 10.

**Decisões relacionadas:** D-08, D-14, D-38 a D-42, D-45.

## Escopo e checklist

- [x] DTE: consulta, paginação, teor, autorização específica de ciência e recuperação de retorno incerto. Implementado e validado com transporte simulado; falta a prova Serpro.
- [x] DCTFWeb: consulta de declaração, recibo e guia implementada/testada localmente; falta homologação real. O registro histórico sem transmissão foi superado pela ampliação aprovada em D-109.
- [ ] Transmissões com aprovação humana vinculada ao conteúdo, conforme ampliação aprovada; implementar/homologar contratos de cada operação, sem presumir disponibilidade por existir consulta.
- [x] Parcelamentos: concluir PARCSN e consultar o responsável antes de ampliar modalidades. O recorte é PARCSN; Q-36 continua obrigatório antes de ampliar.
- [ ] Homologar credenciais centrais, certificados, representação e serviços.
- [x] Validar estimativa, autorização, reserva, liquidação e persistência de documentos. Cobertura local de cotação, token, PDF e estado persistido.
- [ ] D-149 corrige D-148: permitir reemissão com custo adicional por guia. Definição do adicional perguntada ao proprietário; substituir bloqueio provisório, preservando evidências e consumo de cada tentativa. Não confundir nova emissão autorizada com repetição automática do worker.
- [ ] Completar conciliação documentada de resultado/custo para recuperar guias incertas sem alteração manual opaca nem nova chamada automática.

## Bloqueios e responsabilidade

Q-28 e Q-36; Q-05 e Q-30 foram resolvidas por D-76/D-79 e D-72/D-73. Chamadas cobradas exigem autorização específica.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Permissão de ciência, paginação, autorização/custo, indisponibilidade, resultado incerto, idempotência, PDF persistido e consumo conciliado.

**Critério de aceite:** Cada operação prometida completa a jornada real, com documentos, protocolo, consumo e falhas rastreáveis.

## Evidências e próximo passo

### Ponte DTE → central (D-142)

- [x] Mensagem persistida cria análise local única; listagens repetidas não duplicam nem provocam ciência.
- [x] Consulta comprovada cria evidência sem concluir análise; resultado incerto impede conclusão.
- [x] Carteira vigente revalidada no serviço antes de reservar consumo/chamar provedor.
- [x] Projeção após commit com recuperação explícita; falha da central não apaga recibo de abertura.
- [x] D-143: confirmação anterior ao teor não conclui análise; novo recibo reabre conclusão/dispensa sem confirmação posterior, preservando histórico. Recuperação conserva análise posterior válida.
- [x] D-144: navegação contextual da atividade ao resumo local e retorno, com acesso revalidado e sem abertura em GET.
- [ ] Demais resultados Serpro e transmissões aprovadas.
- [x] D-146: serviço de documentos DCTFWeb exige solicitante autorizado antes de reservar; worker revalida antes do provedor e libera reserva não executada em caso de revogação.
- [x] D-147: emissão de guias e PARCSN revalidam solicitante/carteira/módulo antes da reserva e da execução; revogação anterior ao envio libera reserva não executada.
- [ ] Estado de incerteza/filtro implementados provisoriamente em D-148; revisar detalhe e ações conforme reemissão autorizada em D-149. Migration 0063 somente em testes, ainda não liberada.
- [ ] Homologar recuperação e custo das guias incertas com comprovantes autorizados.
- [x] D-150: preservar tentativas e estados de emissão em histórico imutável, com retorno criptografado e referência de consumo; nova tentativa não reutiliza protocolo anterior.
- [x] D-151: histórico paginado na ficha e download do PDF preservado por tentativa, revalidando empresa/escritório/módulo e sem consulta ao provedor.
- [x] D-152: consulta de Guias/Integra intersecta módulo e empresa na mesma concessão; contagem de consultas pendentes também respeita esse escopo.
- [x] V-266: histórico de tentativas, PDF fictício e estados pronto/emitido/falha/incerto validados no navegador em desktop e celular; erro bruto e chave de serviço não são apresentados.
- [ ] Implementar e homologar reemissão somente depois da definição comercial pendente de D-149; resultado incerto continua sem repetição.
- [x] D-155: guias, documentos DCTFWeb e operações PARCSN persistidos projetam atividade única, evidência e impedimento na central. Guia/DAS disponível não conclui pagamento, aceite ou fechamento; Q-40 e D-149 permanecem pendentes. O comando local `sync_serpro_activities` recompõe projeções sem chamada externa (V-174).
- [ ] Homologação real e concorrência PostgreSQL. Chamadas dos testes são simuladas.
- [x] V-172: suíte executada em PostgreSQL 17 local descartável; corrigidos locks de DCTFWeb/PARCSN, reserva concorrente validada. Provedores, cliques concorrentes específicos e recuperação real continuam pendentes.
- [ ] Q-40: confirmar conclusão da atividade de emissão antes de ligar esse resultado à central; pergunta enviada ao proprietário.

V-034 registra 63 testes locais para DTE, DCTFWeb, PARCSN, cliente, autorização, consumo e recuperação. V-051 acrescenta 20 testes locais de PARCSN/operações agendadas e validações de tipo, sem chamada externa. V-068 repetiu os testes locais correlatos e concluiu a verificação estática global, sem executar serviço externo. V-074 acrescentou paginação da carteira de guias e a percorreu no navegador com 101 itens fictícios, preservando filtros e sem erro de console. V-075 fez o mesmo com a carteira de Parcelamentos e definiu 30 itens por página, coincidindo com o limite já autorizado por lote. V-077 paginou o histórico de operações de uma empresa e confirmou a recuperação de 21 tentativas fictícias. V-079 estendeu a ficha de cada empresa à paginação das mensagens DTE, sem acessar o serviço. V-083 acrescentou a página própria do histórico de resultados DTE: 31 itens sintéticos alcançaram a página 2 sem mudar a fila de mensagens; a demonstração vazia confirmou somente a superfície móvel. O próximo passo depende de contrato, credenciais centrais, representação, ambiente e amostra Serpro autorizados por canal seguro; uma chamada cobrada requer confirmação específica imediatamente anterior. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 08. Homologue DTE, DCTFWeb e Parcelamentos com credenciais centrais Mewstack e escopo já aprovado. Preserve autorização de ciência e controles de consumo. Antes de qualquer chamada cobrada, solicite aprovação específica de custo; não repita chamadas de resultado incerto.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.

## Continuação de usabilidade — V-232

- [x] V-236: DTE demo isolada por sessão também para membro; preparação/decisão/abertura sem registros compartilhados, confirmação preservada e auditor bloqueado. Jornada local no navegador; não é ciência ou homologação real.
- [x] V-237: fila DTE não-demo restrita integralmente à carteira atual; contador e POST usam o mesmo escopo. Testes de lote misto, vazio, inconsistente e revogação; sem serviço externo.
- [x] V-238: atalho de seleção no topo, preparação aberta, revisão acessível por âncora, duas etapas explícitas e texto demo sem promessa de consumo. Jornada demo desktop/mobile, teclado, validação vazia e navegação sem JS verificadas localmente.
- [x] V-239: contador da Central Integra usa a mesma carteira integral da fila DTE; demo de membro usa sessão, com entradas inválidas/mistas ocultadas. Jornada do contador 0→1→0 e isolamento entre sessões verificados localmente.
- [ ] Reauditar estados reais/recuperação. Carteira restrita verificada por teste de integração em V-237/V-239, não por login restrito no navegador; sem homologação Serpro.

- [x] Demo de Parcelamentos e confirmação de lote DCTFWeb: isolamento por sessão, permissões, identificador não localizado e testes locais conforme V-232.
- [x] V-233: consulta individual demo isolada, validação da competência e acesso “Consultar documentos” pela linha da guia. Desktop/mobile e teclado verificados localmente; sem homologação Serpro nem publicação.
- [x] V-234: descoberta do lote, seleção vazia/parcial/página, revisão de escopo e bloqueio sem contrato percorridos em tenant QA não-demo com fonte sintética. Centavos e UUIDs normalizados; limite e seleção explicitados.
- [x] V-235: fila, processamento, falha, disponível e incerto renderizados em fixture local desktop/mobile; download de PDF sintético e atualização GET por teclado. Sem nova consulta/consumo. Falha inspecionada sem contrato, não uma nova tentativa paga.
- [x] V-266: carteira prioriza guias oficiais, oferece consulta individual/lote a partir das apurações, mostra progresso de declaração/recibo e uma ação por estado. Lote, filtros, vazio, falha, incerto, detalhe e PDF demo foram reinspecionados sem chamada externa.
- [ ] Homologar separadamente as transições do serviço real, retorno incerto/conciliação e contrato vigente. V-235 valida apresentação de estados locais, não transporte Serpro.
## V-267 — Parcelamentos

- [x] Reorganizar por empresa, acordo, parcela e DAS; incluir revisão de custo/escopo, lote, orientação segura, confirmação humana para estado incerto e PDF demo fictício privado à sessão.
- [x] Validar localmente desktop, mobile, landscape, tema escuro, movimento reduzido, vazio, lote, teclado, foco, overflow e console.
- [ ] Homologar com contrato e credenciais Serpro reais, incluindo respostas, custo, conciliação de estado incerto e validade do DAS oficial.
