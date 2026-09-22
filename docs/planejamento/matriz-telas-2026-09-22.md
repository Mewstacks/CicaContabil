# Matriz de rotas, telas e ações — onda 0 (22/09/2026)

Gerada a partir do URLconf com `scripts`/varredura local em `config.settings.test` sobre a base
fictícia de revisão (`.tmp/ui-review`). [Plano da revisão](plano-revisao-total-ui-demo-onboarding-2026-09-22.md)
· [Etapa 11](etapas/11-jornadas-interfaces.md)

Total de rotas de interface: **89** — 49 telas/estados e 40 ações ou downloads.
Rotas de API REST, webhooks e endpoints do agente ficam fora desta matriz.

## Telas e estados

| Rota | Caminho | Métodos | Varredura GET |
|---|---|---|---|
| `hub:legal` | `/legal/<slug:document>/` | GET | 200 (privacidade, termos) · 404 (slug fora do catálogo) |
| `hub:home` | `/` | GET | 200 |
| `hub:demo-entry` | `/demo/` | GET, POST | 200 |
| `hub:proposal` | `/proposta/` | GET, POST | 302 → /comecar/ |
| `hub:signup` | `/comecar/` | GET, POST | 302 → /app/ (sessão ativa) |
| `hub:signup-verify` | `/comecar/verificar/<str:token>/` | GET, POST | não varrida (POST ou id necessário) |
| `hub:activate` | `/ativar/<str:token>/` | GET, POST | não varrida (POST ou id necessário) |
| `hub:login` | `/entrar/` | GET, POST | 302 → /app/ (sessão ativa) |
| `hub:dashboard` | `/app/` | GET | 200 |
| `hub:team` | `/app/equipe/` | GET, POST | 200 |
| `hub:nfse-center` | `/app/nfse/` | GET, POST | 200 |
| `hub:guides` | `/app/guias/` | GET | 200 |
| `hub:dctfweb-consult` | `/app/guias/dctfweb/consultar/` | GET, POST | 302 → /app/guias/ |
| `hub:dctfweb-bulk-consult` | `/app/guias/dctfweb/consultar-em-lote/` | POST | não varrida (POST ou id necessário) |
| `hub:guide-detail` | `/app/guias/<uuid:guide_id>/` | GET | 200 |
| `hub:integra` | `/app/integra-contador/` | GET | 200 |
| `hub:parcelamentos` | `/app/integra-contador/parcelamentos/` | GET, POST | 200 |
| `hub:dte-center` | `/app/integra-contador/dte/` | GET, POST | 200 |
| `hub:dte-message-detail` | `/app/integra-contador/dte/mensagens/<uuid:message_id>/` | GET, POST | 200 |
| `hub:reconciliation` | `/app/conciliacao/` | GET, POST | 200 |
| `hub:reconciliation-configuration` | `/app/conciliacao/configuracao/` | GET, POST | 200 |
| `hub:reconciliation-audit` | `/app/conciliacao/auditoria/` | GET | 200 |
| `hub:reconciliation-upload` | `/app/conciliacao/importar/` | POST | não varrida (POST ou id necessário) |
| `hub:reconciliation-mapping` | `/app/conciliacao/arquivos/<uuid:source_id>/mapear/` | GET, POST | 403 "Este formato não usa mapeamento de colunas" (origem OFX) |
| `hub:reconciliation-movement` | `/app/conciliacao/movimentos/<uuid:movement_id>/` | GET, POST | 200 |
| `hub:reform` | `/app/radar-reforma/` | GET | 200 |
| `hub:triage` | `/app/triagem/` | GET | 200 |
| `hub:triage-connections` | `/app/triagem/caixas/` | GET | 200 |
| `hub:triage-imap-connect` | `/app/triagem/conectar-imap/` | POST | não varrida (POST ou id necessário) |
| `hub:triage-destination-configure` | `/app/triagem/destino/` | POST | não varrida (POST ou id necessário) |
| `hub:triage-oauth-app-save` | `/app/triagem/aplicativo/<str:provider>/` | POST | não varrida (POST ou id necessário) |
| `hub:triage-mailbox-configure` | `/app/triagem/caixas/<uuid:mailbox_id>/configurar/` | POST | não varrida (POST ou id necessário) |
| `hub:triage-item` | `/app/triagem/<uuid:item_id>/` | GET, POST | 200 |
| `hub:companies` | `/app/empresas/` | GET, POST | 200 |
| `hub:company-detail` | `/app/empresas/<uuid:company_id>/` | GET | 200 |
| `hub:certificates` | `/app/certificados/` | GET, POST | 200 |
| `hub:reviews` | `/app/revisoes/` | GET | 200 |
| `hub:review-detail` | `/app/revisoes/<uuid:case_id>/` | GET | 200 |
| `hub:settings` | `/app/configuracoes/` | GET, POST | 200 |
| `hub:setup` | `/app/configuracao/` | GET, POST | 200 |
| `intelligence:assistant` | `/app/ia/` | GET, POST | 200 |
| `intelligence:learning` | `/app/ia/aprendizado/` | GET | 200 |
| `accounts:mfa-setup` | `/mfa/configurar/` | GET, POST | 200 |
| `accounts:mfa-verify` | `/mfa/entrar/` | GET, POST | 302 → /mfa/configurar/ |
| `accounts:mfa-recovery-codes` | `/mfa/codigos/` | POST | não varrida (POST ou id necessário) |
| `platform:configuration` | `/platform/configuracoes/` | GET, POST | 403 (perfil do escritório) |
| `platform:dashboard` | `/platform/` | GET | 403 (perfil do escritório) |
| `platform:tenants` | `/platform/tenants/` | GET, POST | 403 (perfil do escritório) |
| `platform:tenant-detail` | `/platform/tenants/<uuid:organization_id>/` | GET, POST | não varrida (POST ou id necessário) |

## Ações e downloads

| Rota | Caminho | Métodos | Tipo |
|---|---|---|---|
| `hub:proposal-cnpj` | `/proposta/cnpj/` | POST | ação/API |
| `hub:logout` | `/sair/` | GET | ação/API |
| `hub:password-reset` | `/recuperar-senha/` | GET | ação/API |
| `hub:password-reset-done` | `/recuperar-senha/enviado/` | GET | ação/API |
| `hub:password-reset-confirm` | `/recuperar-senha/<uidb64>/<token>/` | GET | ação/API |
| `hub:password-reset-complete` | `/recuperar-senha/concluida/` | GET | ação/API |
| `hub:collaborator-invitation-resend` | `/app/equipe/convites/<uuid:invitation_id>/reenviar/` | POST | ação/API |
| `hub:collaborator-invitation-revoke` | `/app/equipe/convites/<uuid:invitation_id>/revogar/` | POST | ação/API |
| `hub:collaborator-access` | `/app/equipe/<uuid:membership_id>/acessos/` | POST | ação/API |
| `hub:collaborator-deactivate` | `/app/equipe/<uuid:membership_id>/remover/` | POST | ação/API |
| `hub:dctfweb-document-pdf` | `/app/guias/dctfweb/documentos/<uuid:document_id>.pdf` | GET | download |
| `hub:guide-pdf` | `/app/guias/<uuid:guide_id>/documento.pdf` | GET | download |
| `hub:demo-guide-pdf` | `/app/guias/<uuid:guide_id>/exemplo.pdf` | GET | download |
| `hub:issue-guide` | `/app/guias/<uuid:guide_id>/emitir/` | POST | ação/API |
| `hub:parcelamento-das-pdf` | `/app/integra-contador/parcelamentos/das/<uuid:operation_id>.pdf` | GET | download |
| `hub:dte-next-page` | `/app/integra-contador/dte/consultas/<uuid:item_id>/proxima-pagina/` | POST | ação/API |
| `hub:decide-dte-run` | `/app/integra-contador/dte/<uuid:run_id>/decidir/` | POST | ação/API |
| `hub:reconciliation-run-status` | `/app/conciliacao/processamentos/<uuid:run_id>/` | GET | ação/API |
| `hub:reconciliation-run-action` | `/app/conciliacao/processamentos/<uuid:run_id>/acao/` | POST | ação/API |
| `hub:reconciliation-source-download` | `/app/conciliacao/arquivos/<uuid:source_id>/download/` | GET | download |
| `hub:reconciliation-source-preview` | `/app/conciliacao/arquivos/<uuid:source_id>/visualizar/` | GET | download |
| `hub:reconciliation-movement-bulk-action` | `/app/conciliacao/movimentos/acoes-em-lote/` | POST | ação/API |
| `hub:reconciliation-export-create` | `/app/conciliacao/exportar/` | POST | ação/API |
| `hub:reconciliation-export-download` | `/app/conciliacao/exportacoes/<uuid:export_id>/download/` | GET | download |
| `hub:confirm-reconciliation` | `/app/conciliacao/<uuid:match_id>/confirmar/` | POST | ação/API |
| `hub:triage-oauth-start` | `/app/triagem/conectar/<slug:provider>/` | POST | ação/API |
| `hub:triage-oauth-callback` | `/app/triagem/oauth/<slug:provider>/retorno/` | GET | ação/API |
| `hub:triage-mailbox-disconnect` | `/app/triagem/caixas/<uuid:mailbox_id>/desconectar/` | POST | ação/API |
| `hub:triage-download` | `/app/triagem/<uuid:item_id>/arquivo/` | GET | download |
| `hub:switch-office` | `/app/trocar-escritorio/` | POST | ação/API |
| `hub:set-theme` | `/app/aparencia/` | POST | ação/API |
| `hub:review-original-xml` | `/app/revisoes/<uuid:case_id>/original.xml` | GET | download |
| `hub:resolve-review` | `/app/revisoes/<uuid:case_id>/resolver/` | POST | ação/API |
| `hub:dominio-agent-enrollment` | `/app/configuracoes/dominio/parear/` | POST | ação/API |
| `intelligence:export` | `/app/ia/relatorios/<uuid:message_id>/<str:export_format>/` | GET | download |
| `intelligence:feedback` | `/app/ia/feedback/<uuid:message_id>/` | POST | ação/API |
| `intelligence:review` | `/app/ia/aprendizado/<uuid:candidate_id>/<str:decision>/` | POST | ação/API |
| `accounts:mfa-qr` | `/mfa/qr.svg` | GET | ação/API |
| `platform:start-support` | `/platform/tenants/<uuid:organization_id>/support/` | POST | ação/API |
| `platform:end-support` | `/platform/support/encerrar/` | POST | ação/API |
