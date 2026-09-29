# Matriz de rotas, telas, estados, ações e downloads — 28/09/2026

Gerada diretamente do URLconf atual por `python scripts/generate_ui_inventory.py`.
Django Admin, APIs, webhooks e endpoints do agente não integram a auditoria visual.

Total: **145 rotas** — 96 telas, 4 estados, 29 ações e 16 downloads.

| Rota | Caminho | Tipo | Módulo | Perfis | Fixture/estado de QA |
|---|---|---|---|---|---|
| `hub:activities` | `/app/atividades/` | `tela` | Atividades | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:activity-detail` | `/app/atividades/<uuid:activity_id>/` | `tela` | Atividades | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:activity-complete` | `/app/atividades/<uuid:activity_id>/concluir/` | `ação` | Atividades | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:activity-add-evidence` | `/app/atividades/<uuid:activity_id>/evidencias/` | `ação` | Atividades | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:activity-block` | `/app/atividades/<uuid:activity_id>/impedir/` | `ação` | Atividades | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:activity-models` | `/app/atividades/modelos/` | `tela` | Atividades | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `accounts:mfa-setup` | `/mfa/configurar/` | `tela` | Autenticação e MFA | usuário autenticado | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `accounts:mfa-verify` | `/mfa/entrar/` | `tela` | Autenticação e MFA | usuário autenticado | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `accounts:mfa-qr` | `/mfa/qr.svg` | `download` | Autenticação e MFA | usuário autenticado | artefato sintético autorizado |
| `hub:dashboard` | `/app/` | `tela` | Central operacional | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:set-theme` | `/app/aparencia/` | `ação` | Central operacional | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:onboarding-complete` | `/app/orientacao/<slug:tour_id>/concluir/` | `ação` | Central operacional | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:financial-report-export-download` | `/app/relatorios-financeiros/<uuid:export_id>/baixar/` | `download` | Central operacional | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:reviews` | `/app/revisoes/` | `tela` | Central operacional | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:review-detail` | `/app/revisoes/<uuid:case_id>/` | `tela` | Central operacional | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:review-original-xml` | `/app/revisoes/<uuid:case_id>/original.xml` | `download` | Central operacional | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:resolve-review` | `/app/revisoes/<uuid:case_id>/resolver/` | `ação` | Central operacional | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:switch-office` | `/app/trocar-escritorio/` | `ação` | Central operacional | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:certificates` | `/app/certificados/` | `tela` | Certificados | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:reconciliation` | `/app/conciliacao/` | `tela` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:confirm-reconciliation` | `/app/conciliacao/<uuid:match_id>/confirmar/` | `ação` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:reconciliation-source-download` | `/app/conciliacao/arquivos/<uuid:source_id>/download/` | `download` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:reconciliation-mapping` | `/app/conciliacao/arquivos/<uuid:source_id>/mapear/` | `tela` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:reconciliation-source-preview` | `/app/conciliacao/arquivos/<uuid:source_id>/visualizar/` | `tela` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:reconciliation-audit` | `/app/conciliacao/auditoria/` | `tela` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:reconciliation-configuration` | `/app/conciliacao/configuracao/` | `tela` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:reconciliation-export-download` | `/app/conciliacao/exportacoes/<uuid:export_id>/download/` | `download` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:reconciliation-export-create` | `/app/conciliacao/exportar/` | `ação` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:reconciliation-upload` | `/app/conciliacao/importar/` | `ação` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:reconciliation-movement` | `/app/conciliacao/movimentos/<uuid:movement_id>/` | `tela` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:reconciliation-movement-bulk-action` | `/app/conciliacao/movimentos/acoes-em-lote/` | `ação` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:reconciliation-run-status` | `/app/conciliacao/processamentos/<uuid:run_id>/` | `estado` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | execução sintética pendente/concluída/incerta |
| `hub:reconciliation-run-action` | `/app/conciliacao/processamentos/<uuid:run_id>/acao/` | `ação` | Conciliação | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `agent-v2-configuration-next` | `/api/agent/v2/configuration/next` | `tela` | Configurações | visitante / convidado | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:setup` | `/app/configuracao/` | `tela` | Configurações | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:dre-mapping-editor` | `/app/configuracao/mapa-dre/` | `tela` | Configurações | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:settings` | `/app/configuracoes/` | `tela` | Configurações | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:dominio-agent-enrollment` | `/app/configuracoes/dominio/parear/` | `tela` | Configurações | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `platform:dashboard` | `/platform/` | `tela` | Console Mewstack | admin da plataforma / suporte delegado | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `platform:configuration` | `/platform/configuracoes/` | `tela` | Console Mewstack | admin da plataforma / suporte delegado | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `platform:end-support` | `/platform/support/encerrar/` | `ação` | Console Mewstack | admin da plataforma / suporte delegado | registro sintético + confirmação/CSRF |
| `platform:tenants` | `/platform/tenants/` | `tela` | Console Mewstack | admin da plataforma / suporte delegado | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `platform:tenant-detail` | `/platform/tenants/<uuid:organization_id>/` | `tela` | Console Mewstack | admin da plataforma / suporte delegado | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `platform:start-support` | `/platform/tenants/<uuid:organization_id>/support/` | `ação` | Console Mewstack | admin da plataforma / suporte delegado | registro sintético + confirmação/CSRF |
| `intelligence:assistant` | `/app/ia/` | `tela` | Copiloto e aprendizado | proprietário / administrador / operador autorizado | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `intelligence:learning` | `/app/ia/aprendizado/` | `tela` | Copiloto e aprendizado | proprietário / administrador / operador autorizado | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `intelligence:review` | `/app/ia/aprendizado/<uuid:candidate_id>/<str:decision>/` | `tela` | Copiloto e aprendizado | proprietário / administrador / operador autorizado | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `intelligence:feedback` | `/app/ia/feedback/<uuid:message_id>/` | `tela` | Copiloto e aprendizado | proprietário / administrador / operador autorizado | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `intelligence:export` | `/app/ia/relatorios/<uuid:message_id>/<str:export_format>/` | `download` | Copiloto e aprendizado | proprietário / administrador / operador autorizado | artefato sintético autorizado |
| `hub:companies` | `/app/empresas/` | `tela` | Empresas | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:company-detail` | `/app/empresas/<uuid:company_id>/` | `tela` | Empresas | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:company-financial-report` | `/app/empresas/<uuid:company_id>/relatorios/<slug:resource>/<uuid:resource_id>/<slug:export_format>/` | `download` | Empresas | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:team` | `/app/equipe/` | `tela` | Equipe | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:collaborator-access` | `/app/equipe/<uuid:membership_id>/acessos/` | `tela` | Equipe | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:collaborator-deactivate` | `/app/equipe/<uuid:membership_id>/remover/` | `tela` | Equipe | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:collaborator-invitation-resend` | `/app/equipe/convites/<uuid:invitation_id>/reenviar/` | `ação` | Equipe | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:collaborator-invitation-revoke` | `/app/equipe/convites/<uuid:invitation_id>/revogar/` | `ação` | Equipe | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:guides` | `/app/guias/` | `tela` | Guias e DCTFWeb | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:guide-detail` | `/app/guias/<uuid:guide_id>/` | `tela` | Guias e DCTFWeb | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:guide-pdf` | `/app/guias/<uuid:guide_id>/documento.pdf` | `download` | Guias e DCTFWeb | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:issue-guide` | `/app/guias/<uuid:guide_id>/emitir/` | `ação` | Guias e DCTFWeb | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:demo-guide-pdf` | `/app/guias/<uuid:guide_id>/exemplo.pdf` | `download` | Guias e DCTFWeb | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:guide-attempt-pdf` | `/app/guias/<uuid:guide_id>/historico/<uuid:event_id>/documento.pdf` | `download` | Guias e DCTFWeb | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:dctfweb-bulk-consult` | `/app/guias/dctfweb/consultar-em-lote/` | `ação` | Guias e DCTFWeb | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:dctfweb-consult` | `/app/guias/dctfweb/consultar/` | `tela` | Guias e DCTFWeb | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:dctfweb-document-pdf` | `/app/guias/dctfweb/documentos/<uuid:document_id>.pdf` | `download` | Guias e DCTFWeb | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:integra` | `/app/integra-contador/` | `tela` | Integra Contador | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:dte-center` | `/app/integra-contador/dte/` | `tela` | Integra Contador | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:decide-dte-run` | `/app/integra-contador/dte/<uuid:run_id>/decidir/` | `ação` | Integra Contador | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:dte-next-page` | `/app/integra-contador/dte/consultas/<uuid:item_id>/proxima-pagina/` | `ação` | Integra Contador | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:dte-message-detail` | `/app/integra-contador/dte/mensagens/<uuid:message_id>/` | `tela` | Integra Contador | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:parcelamentos` | `/app/integra-contador/parcelamentos/` | `tela` | Integra Contador | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:parcelamento-das-pdf` | `/app/integra-contador/parcelamentos/das/<uuid:operation_id>.pdf` | `download` | Integra Contador | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:nfse-center` | `/app/nfse/` | `tela` | NFS-e | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:nfse-export-download` | `/app/nfse/exportacoes/<uuid:export_id>/baixar/` | `download` | NFS-e | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:nfse-export-confirm-import` | `/app/nfse/exportacoes/<uuid:export_id>/confirmar-importacao/` | `ação` | NFS-e | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:home` | `/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `agent-v2-backup-download` | `/api/agent/v2/backups/<uuid:batch_id>/download` | `download` | Público e acesso | visitante / convidado | artefato sintético autorizado |
| `agent-v2-backup-next` | `/api/agent/v2/backups/next` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `agent-v2-renew` | `/api/agent/v2/certificate/renew` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `agent-v2-dominio-bank-entries` | `/api/agent/v2/dominio/bank-entries` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `agent-v2-dominio-companies` | `/api/agent/v2/dominio/companies` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `agent-v2-enroll` | `/api/agent/v2/enroll` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `agent-v2-file-complete` | `/api/agent/v2/files/<uuid:job_id>/complete` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `agent-v2-file-download` | `/api/agent/v2/files/<uuid:job_id>/download` | `download` | Público e acesso | visitante / convidado | artefato sintético autorizado |
| `agent-v2-file-next` | `/api/agent/v2/files/next` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `agent-v2-heartbeat` | `/api/agent/v2/heartbeat` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `agent-v2-sync` | `/api/agent/v2/sync/<str:capability>` | `ação` | Público e acesso | visitante / convidado | registro sintético + confirmação/CSRF |
| `api-root` | `/api/v1/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `api-root` | `/api/v1/<drf_format_suffix:format>` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `auth-csrf` | `/api/v1/auth/csrf/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `auth-login` | `/api/v1/auth/login/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `auth-logout` | `/api/v1/auth/logout/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `auth-me` | `/api/v1/auth/me/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `company-list` | `/api/v1/companies/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `company-detail` | `/api/v1/companies/<uuid:pk>/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `company-detail` | `/api/v1/companies/<uuid:pk><drf_format_suffix:format>` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `company-list` | `/api/v1/companies<drf_format_suffix:format>` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `health-live` | `/api/v1/health/live/` | `estado` | Público e acesso | visitante / convidado | execução sintética pendente/concluída/incerta |
| `health-ready` | `/api/v1/health/ready/` | `estado` | Público e acesso | visitante / convidado | execução sintética pendente/concluída/incerta |
| `intelligence-agent-enroll` | `/api/v1/intelligence/agent/enroll/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `intelligence-agent-sync` | `/api/v1/intelligence/agent/sync/` | `ação` | Público e acesso | visitante / convidado | registro sintético + confirmação/CSRF |
| `intelligence-mcp` | `/api/v1/intelligence/mcp/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `organization-list` | `/api/v1/organizations/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `organization-detail` | `/api/v1/organizations/<uuid:pk>/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `organization-detail` | `/api/v1/organizations/<uuid:pk><drf_format_suffix:format>` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `organization-list` | `/api/v1/organizations<drf_format_suffix:format>` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-consent-list` | `/api/v1/privacy/consents/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-consent-detail` | `/api/v1/privacy/consents/<uuid:pk>/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-consent-detail` | `/api/v1/privacy/consents/<uuid:pk><drf_format_suffix:format>` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-consent-list` | `/api/v1/privacy/consents<drf_format_suffix:format>` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-purpose-list` | `/api/v1/privacy/purposes/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-purpose-detail` | `/api/v1/privacy/purposes/<uuid:pk>/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-purpose-detail` | `/api/v1/privacy/purposes/<uuid:pk><drf_format_suffix:format>` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-purpose-list` | `/api/v1/privacy/purposes<drf_format_suffix:format>` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-request-list` | `/api/v1/privacy/requests/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-request-detail` | `/api/v1/privacy/requests/<uuid:pk>/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-request-detail` | `/api/v1/privacy/requests/<uuid:pk><drf_format_suffix:format>` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `privacy-request-list` | `/api/v1/privacy/requests<drf_format_suffix:format>` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:activate` | `/ativar/<str:token>/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:signup` | `/comecar/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:signup-verify` | `/comecar/verificar/<str:token>/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:demo-entry` | `/demo/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:login` | `/entrar/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:legal` | `/legal/<slug:document>/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:proposal` | `/proposta/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:proposal-cnpj` | `/proposta/cnpj/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:password-reset` | `/recuperar-senha/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:password-reset-confirm` | `/recuperar-senha/<uidb64>/<token>/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:password-reset-complete` | `/recuperar-senha/concluida/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:password-reset-done` | `/recuperar-senha/enviado/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:logout` | `/sair/` | `tela` | Público e acesso | visitante / convidado | sessão anônima, convite válido/expirado e formulário inválido |
| `hub:reform` | `/app/radar-reforma/` | `tela` | Radar | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:reform-analysis` | `/app/radar/<uuid:alert_id>/analisar/` | `tela` | Radar | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:triage` | `/app/triagem/` | `tela` | Triagem | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:triage-item` | `/app/triagem/<uuid:item_id>/` | `tela` | Triagem | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:triage-download` | `/app/triagem/<uuid:item_id>/arquivo/` | `download` | Triagem | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | artefato sintético autorizado |
| `hub:triage-oauth-app-save` | `/app/triagem/aplicativo/<str:provider>/` | `ação` | Triagem | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:triage-connections` | `/app/triagem/caixas/` | `tela` | Triagem | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão |
| `hub:triage-mailbox-configure` | `/app/triagem/caixas/<uuid:mailbox_id>/configurar/` | `ação` | Triagem | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:triage-mailbox-disconnect` | `/app/triagem/caixas/<uuid:mailbox_id>/desconectar/` | `ação` | Triagem | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:triage-imap-connect` | `/app/triagem/conectar-imap/` | `ação` | Triagem | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:triage-oauth-start` | `/app/triagem/conectar/<slug:provider>/` | `ação` | Triagem | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:triage-destination-configure` | `/app/triagem/destino/` | `ação` | Triagem | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | registro sintético + confirmação/CSRF |
| `hub:triage-oauth-callback` | `/app/triagem/oauth/<slug:provider>/retorno/` | `estado` | Triagem | proprietário / administrador / operador / financeiro / auditor (conforme permissão) | execução sintética pendente/concluída/incerta |

A classificação é um inventário de cobertura, não autorização para executar integrações reais. Os estados sintéticos devem cobrir vazio, carregado, filtrado, erro recuperável, bloqueio, permissão negada, resultado incerto, texto longo e paginação quando aplicável.
