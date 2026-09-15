# Validação de escopo no serviço do Copiloto

Revisão de backend em 13/09/2026.

## Correção

`answer_question` agora verifica vínculo ativo, usuário ativo e organização ativa antes de criar conversas, anexos ou mensagens e antes de qualquer chamada ao modelo. Uma empresa informada precisa passar pela mesma verificação de escopo e capacidade de leitura utilizada pelo produto. Conversas encerradas são recusadas.

Antes, o serviço consultava um vínculo sem verificar se estava ativo e dependia das verificações feitas pela tela. Uma chamada interna podia alcançar esse serviço sem a mesma proteção.

## Evidência

21 testes passaram: cinco regressões novas e a suíte existente de MCP/inteligência. As regressões confirmam que vínculo ausente/inativo, usuário inativo, escritório inativo e empresa de outro escritório não criam mensagens nem chamam o modelo local ou o fallback.

## Escopo remanescente nesta leitura

- A validação de conversa encerrada foi implementada, mas ainda não tem regressão específica nesta rodada.
- A revisão de retenção, restauração e limpeza de anexos ainda precisa ser concluída antes do lançamento.

Este registro não declara concluída a auditoria da IA, de todos os endpoints ou das tarefas em segundo plano.

## Fechamento complementar em 14/09/2026

- A tela do assistente, feedback, exportações e a central de aprendizado agora aplicam o mesmo bloqueio por organização, permissão de colaborador e módulo habilitado. Uma URL salva não revela metadados nem gera relatórios quando o Copiloto não estiver contratado.
- A navegação desktop, mobile e o card do painel também deixam de exibir o Copiloto quando esse módulo estiver indisponível.
- A operação que consome IA continua protegida no serviço por `require_operation_access`, antes da reserva de capacidade e da chamada local ou de fallback.
