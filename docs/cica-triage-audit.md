# CICA — auditoria da Triagem de Arquivos

Revisão em 15/09/2026. Este documento descreve evidência no repositório e no banco local;
não é homologação de e-mail, extração, IA, armazenamento nem agente Windows.

## Situação real

**Não está pronta para ativação ou venda.** A rota `/app/triagem/` apenas renderiza o estado
vazio. Não existem serviço, tarefa, endpoint, formulário ou worker de triagem. A busca no
repositório não encontrou integração de Graph/IMAP, leitura de anexos, antivírus, quarentena
operacional, extração, classificação, revisão, download autenticado, biblioteca interna,
despacho de agente ou escrita em pastas Windows.

O banco local também mostra `triage.0001_initial` como **não aplicada**. A tela vazia pode
aparecer porque não consulta as tabelas, mas o domínio novo não existe nesse banco até a
migração ser executada no ambiente adequado.

## O que foi bem encaminhado

- O domínio está isolado por organização na base (`Mailbox`, `DocumentType`, `TriageItem`,
  `TriageBlob`, checklist e trabalho do agente).
- A chave de caixa postal usa campo cifrado.
- O hash de conteúdo e a tupla caixa/mensagem/parte têm restrições de duplicidade.
- Há uma máquina de estados explícita e testes para caminho normal, revisão, falha e estados
  terminais.
- O binário foi concebido para caminho privado, fora de mídia pública.

## Bloqueadores de lançamento

1. **Produto anunciado antes de existir.** `module_catalog.py` promete receber e-mail,
   identificar e arquivar; `pricing.py` inclui R$ 149/mês. Nada disso é executado. O módulo
   não deve ser habilitado, aparecer em oferta ou receber descrição funcional até haver um
   primeiro fluxo real.
2. **Não há isolamento relacional suficiente.** `OrganizationScopedModel` só adiciona a FK
   `organization`; ele não valida que `TriageItem.mailbox`, `.company`, `.document_type` ou
   `.reviewed_by` pertencem ao mesmo escritório. O mesmo vale para `TriageBlob.triage_item`,
   `ChecklistExpectation`, `ChecklistEntry` e `AgentFileJob`. Uma gravação de backend
   incorreta pode construir relações cruzadas entre escritórios.
3. **A máquina de estados não é uma barreira de persistência.** `transition_to()` é opcional;
   um `update()` ou atribuição direta de `status` contorna o grafo. Não há serviço transacional,
   evento de auditoria, versão otimista ou regra que exija revisão humana antes de arquivar.
4. **Destino Windows é apenas texto.** Não há allowlist canônica, resolução de caminho,
   validação contra escape de raiz, mTLS/claim do agente ou confirmação de hash de escrita.
   `AgentFileJob` é schema, não protocolo.
5. **Segurança de entrada ausente.** Não há limite de tamanho/tipo próprio, validação de
   conteúdo, quarentena efetiva, varredura, deduplicação de ingestão com tratamento idempotente
   ou proteção contra arquivos maliciosos.
6. **Não há configuração utilizável no SaaS.** Não há telas para caixas, catálogo, aliases,
   destino, checklist, fila, revisão ou erros. A mensagem da rota aponta para Configurações,
   mas esse fluxo não existe.
7. **Sem rastreabilidade de decisão.** `ai_fields` aceita JSON livre e não possui contrato,
   fontes, revisão da regra, versão de modelo, trilha de aprovação ou retenção definida.

## Evidências executadas

- `uv run pytest tests/test_triage_domain.py tests/test_hub_workspace_views_django.py -q`
  → `58 passed`.
- `uv run python manage.py makemigrations --check` → sem alterações pendentes.
- `uv run python manage.py check` → sem erros.
- `uv run python manage.py showmigrations triage` → `0001_initial` não aplicada no banco local.

Os testes atuais validam principalmente schema e o grafo puro. Eles não cobrem nenhuma das
integrações, permissões, armazenamento ou fluxo que uma triagem comercial exigiria.

## Ordem segura para implementação

1. Remover a promessa comercial e manter o módulo indisponível até a primeira frente útil.
2. Criar um serviço transacional que valide toda relação pelo mesmo escritório e seja a única
   forma de criar/alterar itens; bloquear alterações diretas de estado nas rotas.
3. Definir contrato da entrada e quarentena: canais autorizados, MIME/assinatura, tamanho,
   hash, retenção, antivírus e política de duplicidade.
4. Implementar somente um destino inicial (biblioteca interna **ou** agente Windows), com
   download autenticado, auditoria e confirmação de escrita antes do segundo.
5. Criar as telas internas de configuração, fila e revisão, com permissões por módulo e empresa.
6. Só então integrar caixa de e-mail, extração/classificação local e automatização controlada.
7. Homologar com amostra autorizada e testes de isolamento, caminho Windows, reprocessamento e
   arquivamento incorreto antes de liberar ou precificar.
