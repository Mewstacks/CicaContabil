# Inventário da auditoria CICA

> **Fotografia histórica de 14/09/2026, não estado vigente.** Consulte o [plano mestre](../PLANO-MESTRE.md), as [decisões](../DECISOES.md), as [validações](../VALIDACOES.md) e o [inventário de 17/09](planejamento/inventario-conclusao.md). As afirmações abaixo sobre ausência de coleta NFS-e e titularidade Serpro foram superadas: há cliente ADN no código e D-08 confirma credenciais centrais Mewstack. Isso não prova homologação externa. O conteúdo foi preservado para rastreabilidade.

Atualizado em 14/09/2026. Este registro separa o que foi inspecionado do que ainda precisa de validação; não é certificação de segurança nem autorização de lançamento.

## Escopo próprio encontrado

- 226 arquivos de código próprios em `src/` e `agent/`, excluindo migrações, estáticos gerados e caches.
- 66 documentos em `docs/`.
- Áreas: autenticação/MFA, organizações e permissões, hub operacional, plataforma/comercial, conectores e inteligência, privacidade, configuração Django e agente Windows Domínio.

## Evidência já revisada

| Área | Evidência atual | Resultado |
|---|---|---|
| Cadastro, confirmação e MFA | `tests/test_cica_signup_flow.py`, `tests/test_cica_signup_security.py`, `tests/test_cica_auth_flow.py` | Cadastro requer nome, e-mail, CNPJ e aceite; teste dura 14 dias; MFA é exigido fora do teste. Navegador MCP indisponível nesta sessão. |
| Isolamento e colaboradores | `tests/test_hub_workspace_views_django.py`, `tests/test_platform_isolation.py` | Convites, escopo de empresas/módulos e rotas de jornadas são internos ao escritório. |
| Configuração Mewstack | `tests/test_cica_configuration.py` | Runtime local, SMTP, contatos e catálogo são configuráveis pelo console; segredos não são exibidos. |
| Cobrança manual | `tests/test_platform_tenant_django.py`, `tests/test_platform_services.py` | A CICA registra contrato/cobrança; não coleta cartão nem chama gateway. |
| E-mail transacional | `tests/test_cica_configuration.py`, `tests/test_cica_signup_flow.py` | SMTP é cifrado no console; falha de confirmação/convite não persiste estado parcial. |
| Documentos legais | `src/apps/platform/legal.py`, `src/apps/platform/legal_versions.py` | Há minutas versionadas e aceite registrado no cadastro. Elas permanecem como rascunho: e-mails de suporte/privacidade e os prazos de exportação, retenção e descarte ainda não foram definidos. |
| Integrações | `docs/cica-siescon-discovery.md`, testes Domínio/agent | Domínio tem caminho local somente leitura. Siescon não tem adaptador homologado. Integra Contador ainda depende da decisão de escopo de credenciais Serpro. |
| NFS-e Inteligente | `src/apps/hub/models.py`, `src/apps/hub/services.py`, `src/apps/hub/views.py` | A custódia A1/PFX, evidência imutável e classificação determinística existem. A coleta externa não: `NfseSync` não é criado/executado por serviço ou tarefa. Não anunciar captura como ativa até a homologação. |
| Copiloto | `tests/test_intelligence*.py`, `docs/cica-ai-scope-review.md`, `docs/planejamento/ia-operacao.md` | Continua indisponível enquanto a configuração global estiver desligada. O caminho temporário Claude via chave central, cotas, consentimento e auditoria existe, mas a chave, os limites aprovados e o piloto real ainda faltam. |
| Rotinas operacionais | `src/config/settings/base.py`, `src/apps/*/tasks.py`, `src/apps/platform/operations.py` | Ciclos de cobrança, teste, Radar, retenção e conhecimento existem como tarefas Celery agendadas e gravam a última execução, resultado ou falha compacta no console de desenvolvedor. Beat, worker, alertas e restauração ainda exigem homologação no ambiente de implantação. |

## Pendências que não podem ser declaradas concluídas

1. Navegação, teclado, responsividade e console em navegador real via Playwright MCP: indisponível neste ambiente.
2. Homologação Domínio/Siescon e dados autorizados de terceiros.
3. Decisão e migração da credencial Serpro; contrato central Mewstack ou credencial por escritório.
4. Migração da chave/orçamento de fallback externo para configuração global da Mewstack; o modelo legado por escritório não é publicável.
5. Seleção/homologação de provedor SMTP, domínio de envio e DNS.
6. Fechamento comercial, revisão jurídica e prazos finais de retenção/exportação.
7. Restauração de backup e operação de produção.
8. Implementação e homologação da coleta NFS-e: vincular o certificado à empresa, executar consulta autorizada, registrar falha/reconexão e não exibir “conectada” antes da primeira sincronização verificável.
9. Fechar a minuta legal: informar e-mails reais de suporte e privacidade, prazo para exportação após encerramento, período de retenção e tratamento de backups; submeter a versão final à revisão jurídica antes de tratá-la como contrato comercial.
10. Expor no console Mewstack a saúde das rotinas Celery, próxima execução, último resultado e reexecução segura. Não depender de comandos de terminal para a operação rotineira.
