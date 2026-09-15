# Bloqueio de novas operações do Copiloto

## Implementado

O serviço `answer_question` chama `require_operation_access` antes de criar conversas ou chamar modelos. A regra exige contrato atual em teste válido ou ativo, vigência válida, módulo contratado e ativado. Estados de carência, suspensão e arquivamento não autorizam novas operações. Ausência de contrato falha fechada.

O teste é verificado por data contratual e pelo instante de início no perfil mais 14 dias. O bloqueio não espera a execução de Celery. Um contrato antigo ativo não é usado para contornar um contrato mais recente bloqueado.

Não existe dispensa implícita para instalações sem contrato neste serviço. Os testes de MCP foram ajustados para criar um teste comercial válido explicitamente, sem simular aprovação da regra.

## Evidência inicial

30 testes passaram: autorização operacional, isolamento do serviço e MCP. Testes negativos verificam que não há chamada local/nuvem nem criação de conversas. Ruff passou nos arquivos alterados.

Regressão ampliada: 88 testes selecionados por `intelligence` passaram, com 288 deselecionados. A primeira execução encontrou três testes de geração que não criavam contrato; seus cenários agora incluem teste válido e módulo ativado explicitamente. As asserções de resposta, evidência e revisão foram mantidas. A regra de produção não foi afrouxada para acomodar esses cenários antigos.

## Franquia da IA

Cada pergunta reserva atomicamente uma unidade de `ai.answer` antes de criar a conversa ou chamar o modelo. A unidade é liquidada após a resposta ser persistida. A franquia vem da tarifa do plano copiada para o contrato; sem tarifa contratual, a operação falha fechada. O padrão bloqueia no limite e não gera cobrança automática.

Um teste com franquia de uma unidade provou que a primeira pergunta é concluída e a segunda é bloqueada sem chamada ao modelo nem nova mensagem. O medidor termina com uma unidade consumida e nenhuma reserva presa. Contratos em carência também não podem reservar novo consumo por chamada direta; pedidos iniciados antes da mudança ainda podem ser liquidados.

Evidências adicionais: 41 testes focados de IA e cobrança passaram; a regressão ampla permaneceu em 88 testes de inteligência aprovados.

A franquia aplicada aos novos testes de 14 dias é configurada no console da plataforma pela Mewstack. O valor escolhido fica congelado no `SignupIntent` e na tarifa do contrato no provisionamento: alterar a configuração global depois disso não muda a franquia de um teste já iniciado. O valor padrão é zero, portanto novos cadastros falham fechados até que a desenvolvedora escolha uma franquia positiva no console. Não há cobrança automática quando a franquia se esgota.

## Ainda pendente

- **Siescon não está integrado.** A tela atual permite salvar uma configuração cifrada para Siescon, mas não existe adaptador, teste de conexão, fila de sincronização ou importação Siescon no código. Isso não pode ser apresentado como uma integração pronta nem receber credenciais reais antes da implementação e homologação autorizada. A conexão real hoje é a do Domínio, por ODBC controlado ou agente local.
- Integrar a regra às demais ferramentas e tarefas que consomem recursos.
- Consolidar snapshots de módulos em todos os contratos. Contratos antigos sem seleção usam os módulos do plano associado.
- Testar concorrência real em PostgreSQL e fechar o valor comercial da franquia.
- Validar mensagens e recuperação do fluxo pelo navegador. Nenhum template foi modificado nesta rodada.
- Separar consulta/exportação e contratação das operações de geração. Esta função autoriza trabalho novo, não decide retenção ou acesso a dados históricos.

## Retenção e exportação: lacuna confirmada em 14/09/2026

O Copiloto expõe exportação autenticada de cada resposta autorizada em PDF ou XLSX. A rota verifica escritório, módulo e empresa do colaborador antes de gerar o arquivo; inclui fontes registradas, resposta e auditoria do download. Não há exportação geral do escritório, nem exportação disponível durante acesso de cliente externo — recurso inexistente nesta etapa. A política de consulta, exportação e retenção após encerramento ainda precisa de fechamento comercial e jurídico.

Antes do lançamento, é necessário definir escopo, prazo de retenção, autorizados, formato, trilha de auditoria e entrega segura da exportação. A implementação deve preservar o isolamento por escritório e nunca expor credenciais, dados de outro tenant ou arquivos sem autorização.
