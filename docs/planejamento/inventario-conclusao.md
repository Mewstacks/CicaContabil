# Inventário de conclusão — 17/09/2026

[Plano mestre](../../PLANO-MESTRE.md) · [Decisões](../../DECISOES.md) · [Validações](../../VALIDACOES.md)

Inventário obtido por leitura estática do checkout, incluindo alterações locais ainda não commitadas. Não executa integrações nem prova cobertura funcional. Rotas e tarefas são referências de implementação; a homologação continua separada.

## Áreas e etapas responsáveis

| Área | Código principal | Etapas |
|---|---|---|
| Cadastro, autenticação, MFA | `accounts`, `organizations`, `hub` | 02 |
| Escritórios, empresas, certificados, equipe | `organizations`, `hub`, `platform` | 02 |
| Copiloto, aprendizado, consulta e treino | `intelligence`, `knowledge`, `runtime/trainer` | 05, 13 |
| Domínio e agentes | `intelligence/connectors.py`, `agent`, `agent-windows` | 03 |
| Siescon | Enum/interface informativa; adaptador não encontrado | 04 |
| Triagem, caixas, quarentena e arquivo | `triage`, `hub`, `agent-windows` | 06 |
| NFS-e, coleta e revisão | `hub/nfse_adn.py`, `hub/nfse_sync.py`, `hub/services.py` | 07 |
| DTE, Parcelamentos, DCTFWeb | `integra`, `hub` | 08 |
| Conciliação e exportações | `hub/reconciliation_service.py` | 09 |
| Radar | `hub/reform.py`, tarefas do hub | 09 |
| Contratos, tokens e cobrança | `platform`, `platform/payments.py` | 10 |
| Privacidade, auditoria, suporte, operação | `privacy`, `audit`, `common`, `platform` | 01, 02, 12 |
| Site, demo, workspace e console | templates/static de `hub`, `intelligence`, `platform` | 11 |
| Produção, deploy, backup e observabilidade | `deploy`, `scripts`, `.github`, configurações | 01, 12 |

## Aplicações e modelos

### accounts

17 arquivos Python (inclui migrações).

Classes de domínio: `User`, `TotpDevice`, `RecoveryCode`.

### audit

8 arquivos Python (inclui migrações).

Classes de domínio: `AuditEvent`.

### common

19 arquivos Python (inclui migrações).

Classes de domínio: `AppendOnlyQuerySet`, `UUIDTimeStampedModel`.

### hub

73 arquivos Python (inclui migrações).

Classes de domínio: `OfficeProfile`, `ProductModule`, `UsageAllowance`, `ClientCompany`, `ClientJourney`, `JourneyStep`, `PortalRequest`, `CompanyAccessGrant`, `ControlPlaneBinding`, `RemoteSupportGrant`, `Certificate`, `NfseSync`, `ImmutableOrganizationModel`, `NfseDocument`, `AccumulatorRule`, `AccumulatorObservation`, `ReviewCase`, `IntegrationArtifact`, `DataSource`, `ImportBatch`, `AccountingEntry`, `Connector`, `ConsumptionConfirmation`, `DteRun`, `DteRunItem`, `DteMessage`, `DteMessageObservation`, `DteMessageState`, `DteMessageAccess`, `FiscalGuide`, `DctfWebDocument`, `ParcelamentoOperation`, `ReformAlert`, `ReformSourceStatus`, `BankStatementImport`, `BankTransaction`, `DominioBankEntry`, `ReconciliationMatch`, `ReconciliationSourceFile`, `ReconciliationRun`, `ReconciliationLayout`, `FinancialAccount`, `LedgerAccount`, `CostCenter`, `AccountingPeriod`, `ReconciliationRule`, `NormalizedMovement`, `JournalEntry`, `JournalLine`, `MovementReconciliation`, `AccountingExport`, `OperationalTask`.

### integra

11 arquivos Python (inclui migrações).

Sem models.py próprio.

### intelligence

69 arquivos Python (inclui migrações).

Classes de domínio: `AssistantSettings`, `ClaudeFallbackApproval`, `DataCatalogEntry`, `DominioSchemaObject`, `SemanticPackage`, `MirrorRecord`, `KnowledgeSource`, `KnowledgeChunk`, `TrainingExample`, `EvaluationRun`, `IntelligenceConnector`, `DominioCommunication`, `AgentEnrollment`, `EdgeAgent`, `Conversation`, `Message`, `ChatAttachment`, `ClassificationDraft`, `AnswerFeedback`, `LearningCandidate`, `ModelVersion`, `EgressAudit`.

### knowledge

6 arquivos Python (inclui migrações).

Classes de domínio: `SharedKnowledgeSource`, `SharedKnowledgeChunk`, `GlobalLearningPromotion`.

### organizations

14 arquivos Python (inclui migrações).

Classes de domínio: `Organization`, `Membership`, `OrganizationScopedModel`.

### platform

56 arquivos Python (inclui migrações).

Classes de domínio: `PlatformConfiguration`, `OperationalRun`, `BillingCloseDeferral`, `PlatformAccess`, `TenantLifecycle`, `DominioSupportTicket`, `Plan`, `PlanServiceRate`, `TenantContract`, `TokenPriceBook`, `TokenModuleRate`, `TokenActionWeight`, `TokenMeter`, `TokenUsageEvent`, `TenantServiceRate`, `TenantUsagePolicy`, `UsageMeter`, `UsageEvent`, `Invoice`, `InvoiceLine`, `PaymentAttempt`, `PaymentWebhookDelivery`, `Entitlement`, `FeatureFlag`, `Invitation`, `SupportSession`, `Lead`, `SignupIntent`.

### privacy

7 arquivos Python (inclui migrações).

Classes de domínio: `ProcessingPurpose`, `PrivacyNotice`, `ConsentRecord`, `DataSubjectRequest`, `PersonalDataIncident`.

### triage

30 arquivos Python (inclui migrações).

Classes de domínio: `MailboxOAuthApp`, `Mailbox`, `DocumentType`, `CounterpartyAlias`, `DestinationProfile`, `TriageItem`, `TriageBlob`, `TriageSafetyScan`, `TriageEvent`, `ChecklistExpectation`, `ChecklistEntry`, `AgentFileJob`.

## Rotas e registros de API

Inclui prefixos de configuração e declarações nas aplicações; combinações `include` devem ser lidas com seus prefixos.

### `src/apps/accounts/urls.py`

- `path('configurar/', views.setup, name='mfa-setup')`
- `path('entrar/', views.verify, name='mfa-verify')`
- `path('qr.svg', views.enrollment_qr, name='mfa-qr')`
- `path('codigos/', views.regenerate_recovery_codes, name='mfa-recovery-codes')`

### `src/apps/hub/urls.py`

- `path('legal/<slug:document>/', legal_document, name='legal')`
- `path('', views.home, name='home')`
- `path('demo/', views.demo_entry, name='demo-entry')`
- `path('proposta/', views.legacy_proposal, name='proposal')`
- `path('proposta/cnpj/', views.proposal_cnpj, name='proposal-cnpj')`
- `path('comecar/', views.signup, name='signup')`
- `path('comecar/verificar/<str:token>/', views.verify_signup, name='signup-verify')`
- `path('ativar/<str:token>/', views.activate_invitation, name='activate')`
- `path('entrar/', views.login_view, name='login')`
- `path('sair/', LogoutView.as_view(), name='logout')`
- `path('recuperar-senha/', auth_views.PasswordResetView.as_view(template_name='hub/password_reset_form.html', email_template_name='hub/emails/password_reset_email.txt', subject_template_name='hub/emails/password_reset_subject.txt', success_url=reverse_lazy('hub:password-reset-done')), name='password-reset')`
- `path('recuperar-senha/enviado/', auth_views.PasswordResetDoneView.as_view(template_name='hub/password_reset_done.html'), name='password-reset-done')`
- `path('recuperar-senha/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(template_name='hub/password_reset_confirm.html', success_url=reverse_lazy('hub:password-reset-complete')), name='password-reset-confirm')`
- `path('recuperar-senha/concluida/', auth_views.PasswordResetCompleteView.as_view(template_name='hub/password_reset_complete.html'), name='password-reset-complete')`
- `path('app/', views.dashboard, name='dashboard')`
- `path('app/equipe/', views.team, name='team')`
- `path('app/equipe/convites/<uuid:invitation_id>/reenviar/', views.resend_collaborator_invitation, name='collaborator-invitation-resend')`
- `path('app/equipe/convites/<uuid:invitation_id>/revogar/', views.revoke_collaborator_invitation, name='collaborator-invitation-revoke')`
- `path('app/equipe/<uuid:membership_id>/acessos/', views.update_collaborator_access, name='collaborator-access')`
- `path('app/equipe/<uuid:membership_id>/remover/', views.deactivate_collaborator, name='collaborator-deactivate')`
- `path('app/nfse/', views.nfse_center, name='nfse-center')`
- `path('app/guias/', views.guides, name='guides')`
- `path('app/guias/dctfweb/consultar/', views.dctfweb_consult, name='dctfweb-consult')`
- `path('app/guias/dctfweb/consultar-em-lote/', views.dctfweb_bulk_consult, name='dctfweb-bulk-consult')`
- `path('app/guias/dctfweb/documentos/<uuid:document_id>.pdf', views.dctfweb_document_pdf, name='dctfweb-document-pdf')`
- `path('app/guias/<uuid:guide_id>/', views.guide_detail, name='guide-detail')`
- `path('app/guias/<uuid:guide_id>/documento.pdf', views.guide_pdf, name='guide-pdf')`
- `path('app/guias/<uuid:guide_id>/exemplo.pdf', views.demo_guide_pdf, name='demo-guide-pdf')`
- `path('app/guias/<uuid:guide_id>/emitir/', views.issue_guide, name='issue-guide')`
- `path('app/integra-contador/', views.integra, name='integra')`
- `path('app/integra-contador/parcelamentos/', views.parcelamentos, name='parcelamentos')`
- `path('app/integra-contador/parcelamentos/das/<uuid:operation_id>.pdf', views.parcelamento_das_pdf, name='parcelamento-das-pdf')`
- `path('app/integra-contador/dte/', views.dte_center, name='dte-center')`
- `path('app/integra-contador/dte/consultas/<uuid:item_id>/proxima-pagina/', views.prepare_dte_continuation, name='dte-next-page')`
- `path('app/integra-contador/dte/mensagens/<uuid:message_id>/', views.dte_message_detail, name='dte-message-detail')`
- `path('app/integra-contador/dte/<uuid:run_id>/decidir/', views.decide_dte_run, name='decide-dte-run')`
- `path('app/conciliacao/', views.reconciliation, name='reconciliation')`
- `path('app/conciliacao/configuracao/', views.reconciliation_configuration, name='reconciliation-configuration')`
- `path('app/conciliacao/auditoria/', views.reconciliation_audit, name='reconciliation-audit')`
- `path('app/conciliacao/importar/', views.reconciliation_upload, name='reconciliation-upload')`
- `path('app/conciliacao/processamentos/<uuid:run_id>/', views.reconciliation_run_status, name='reconciliation-run-status')`
- `path('app/conciliacao/processamentos/<uuid:run_id>/acao/', views.reconciliation_run_action, name='reconciliation-run-action')`
- `path('app/conciliacao/arquivos/<uuid:source_id>/mapear/', views.reconciliation_mapping, name='reconciliation-mapping')`
- `path('app/conciliacao/arquivos/<uuid:source_id>/download/', views.reconciliation_source_download, name='reconciliation-source-download')`
- `path('app/conciliacao/arquivos/<uuid:source_id>/visualizar/', views.reconciliation_source_preview, name='reconciliation-source-preview')`
- `path('app/conciliacao/movimentos/<uuid:movement_id>/', views.reconciliation_movement_detail, name='reconciliation-movement')`
- `path('app/conciliacao/movimentos/acoes-em-lote/', views.reconciliation_movement_bulk_action, name='reconciliation-movement-bulk-action')`
- `path('app/conciliacao/exportar/', views.reconciliation_export_create, name='reconciliation-export-create')`
- `path('app/conciliacao/exportacoes/<uuid:export_id>/download/', views.reconciliation_export_download, name='reconciliation-export-download')`
- `path('app/conciliacao/<uuid:match_id>/confirmar/', views.confirm_reconciliation, name='confirm-reconciliation')`
- `path('app/radar-reforma/', views.reform, name='reform')`
- `path('app/triagem/', views.triage, name='triage')`
- `path('app/triagem/caixas/', views.triage_connections, name='triage-connections')`
- `path('app/triagem/conectar-imap/', views.triage_imap_connect, name='triage-imap-connect')`
- `path('app/triagem/destino/', views.triage_destination_configure, name='triage-destination-configure')`
- `path('app/triagem/aplicativo/<str:provider>/', views.triage_oauth_app_save, name='triage-oauth-app-save')`
- `path('app/triagem/conectar/<slug:provider>/', views.triage_oauth_start, name='triage-oauth-start')`
- `path('app/triagem/oauth/<slug:provider>/retorno/', views.triage_oauth_callback, name='triage-oauth-callback')`
- `path('app/triagem/caixas/<uuid:mailbox_id>/configurar/', views.triage_mailbox_configure, name='triage-mailbox-configure')`
- `path('app/triagem/caixas/<uuid:mailbox_id>/desconectar/', views.triage_mailbox_disconnect, name='triage-mailbox-disconnect')`
- `path('app/triagem/<uuid:item_id>/', views.triage_item_detail, name='triage-item')`
- `path('app/triagem/<uuid:item_id>/arquivo/', views.triage_download, name='triage-download')`
- `path('app/trocar-escritorio/', views.switch_office, name='switch-office')`
- `path('app/aparencia/', views.set_theme, name='set-theme')`
- `path('app/empresas/', views.companies, name='companies')`
- `path('app/empresas/<uuid:company_id>/', views.company_detail, name='company-detail')`
- `path('app/certificados/', views.certificates, name='certificates')`
- `path('app/revisoes/', views.reviews, name='reviews')`
- `path('app/revisoes/<uuid:case_id>/', views.review_detail, name='review-detail')`
- `path('app/revisoes/<uuid:case_id>/original.xml', views.review_original_xml, name='review-original-xml')`
- `path('app/revisoes/<uuid:case_id>/resolver/', views.resolve_review, name='resolve-review')`
- `path('app/configuracoes/', views.settings_view, name='settings')`
- `path('app/configuracao/', views.setup_center, name='setup')`
- `path('app/configuracoes/dominio/parear/', views.issue_dominio_agent_enrollment, name='dominio-agent-enrollment')`

### `src/apps/intelligence/urls.py`

- `path('', views.assistant, name='assistant')`
- `path('relatorios/<uuid:message_id>/<str:export_format>/', views.export_answer, name='export')`
- `path('feedback/<uuid:message_id>/', views.submit_feedback, name='feedback')`
- `path('aprendizado/', views.learning_center, name='learning')`
- `path('aprendizado/<uuid:candidate_id>/<str:decision>/', views.review_candidate, name='review')`

### `src/apps/platform/urls.py`

- `path('configuracoes/', configuration, name='configuration')`
- `path('', views.dashboard, name='dashboard')`
- `path('tenants/', views.tenants, name='tenants')`
- `path('tenants/<uuid:organization_id>/', views.tenant_detail, name='tenant-detail')`
- `path('tenants/<uuid:organization_id>/support/', views.start_support, name='start-support')`
- `path('support/encerrar/', views.end_support, name='end-support')`
- `path('webhooks/asaas/', asaas, name='asaas-webhook')`

### `src/config/urls.py`

- `path('', include('apps.hub.urls'))`
- `path('app/ia/', include('apps.intelligence.urls'))`
- `path('mfa/', include('apps.accounts.urls'))`
- `path('platform/', include('apps.platform.urls'))`
- `path('api/v1/', include('config.urls_api'))`
- `path('api/agent/v2/', include('config.urls_agent_v2'))`
- `path('admin/', admin.site.urls)`
- `path('api/schema/', SpectacularAPIView.as_view(), name='api-schema')`
- `path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs')`

### `src/config/urls_agent_v2.py`

- `path('enroll', agent_v2.enroll, name='agent-v2-enroll')`
- `path('heartbeat', agent_v2.heartbeat, name='agent-v2-heartbeat')`
- `path('backups/next', agent_v2.next_backup, name='agent-v2-backup-next')`
- `path('files/next', agent_v2.next_file_job, name='agent-v2-file-next')`
- `path('files/<uuid:job_id>/download', agent_v2.download_file_job, name='agent-v2-file-download')`
- `path('files/<uuid:job_id>/complete', agent_v2.complete_file_job, name='agent-v2-file-complete')`
- `path('backups/<uuid:batch_id>/download', agent_v2.download_backup, name='agent-v2-backup-download')`
- `path('sync/<str:capability>', agent_v2.sync_capability, name='agent-v2-sync')`
- `path('certificate/renew', agent_v2.renew_certificate, name='agent-v2-renew')`

### `src/config/urls_api.py`

- `router.register('companies', ClientCompanyViewSet, basename='company')`
- `router.register('organizations', OrganizationViewSet, basename='organization')`
- `router.register('privacy/purposes', ProcessingPurposeViewSet, basename='privacy-purpose')`
- `router.register('privacy/consents', ConsentViewSet, basename='privacy-consent')`
- `router.register('privacy/requests', DataSubjectRequestViewSet, basename='privacy-request')`
- `path('health/live/', LivenessView.as_view(), name='health-live')`
- `path('health/ready/', ReadinessView.as_view(), name='health-ready')`
- `path('intelligence/mcp/', mcp_endpoint, name='intelligence-mcp')`
- `path('intelligence/agent/enroll/', agent_enroll, name='intelligence-agent-enroll')`
- `path('intelligence/agent/sync/', agent_sync, name='intelligence-agent-sync')`
- `path('auth/me/', MeView.as_view(), name='auth-me')`
- `path('auth/csrf/', CsrfTokenView.as_view(), name='auth-csrf')`
- `path('auth/login/', LoginView.as_view(), name='auth-login')`
- `path('auth/logout/', LogoutView.as_view(), name='auth-logout')`
- `path('', include(router.urls))`

## Tarefas e agendamentos

### `src/apps/hub/tasks.py`

- `dispatch_active_nfse_syncs` — `shared_task(name='hub.dispatch_active_nfse_syncs')`
- `poll_nfse_sync` — `shared_task(name='hub.poll_nfse_sync')`
- `refresh_reform_sources_task` — `shared_task(name='hub.refresh_reform_sources')`; `track_scheduled_operation(OperationalRun.Task.REFRESH_REFORM)`
- `process_reconciliation_run` — `shared_task(name='hub.process_reconciliation_run')`
- `dispatch_waiting_reconciliation_runs` — `shared_task(name='hub.dispatch_waiting_reconciliation_runs')`
- `recover_reconciliation_runs` — `shared_task(name='hub.recover_reconciliation_runs')`
- `dispatch_dte_run` — `shared_task(name='hub.dispatch_dte_run')`
- `dispatch_dctfweb_document` — `shared_task(name='hub.dispatch_dctfweb_document')`
- `dispatch_parcelamento_operation` — `shared_task(name='hub.dispatch_parcelamento_operation')`
- `dispatch_fiscal_guide` — `shared_task(name='hub.dispatch_fiscal_guide')`

### `src/apps/intelligence/tasks.py`

- `refresh_knowledge_chunks_task` — `shared_task(name='intelligence.refresh_knowledge_chunks')`; `track_scheduled_operation(OperationalRun.Task.REFRESH_KNOWLEDGE)`
- `refresh_shared_knowledge_chunks_task` — `shared_task(name='intelligence.refresh_shared_knowledge_chunks')`; `track_scheduled_operation(OperationalRun.Task.REFRESH_SHARED_KNOWLEDGE)`
- `reconcile_claude_attempts_task` — `shared_task(name='intelligence.reconcile_claude_attempts')`
- `purge_expired_conversations_task` — `shared_task(name='intelligence.purge_expired_conversations')`; `track_scheduled_operation(OperationalRun.Task.PURGE_INTELLIGENCE)`
- `analyze_attachment_task` — `shared_task(name='intelligence.analyze_attachment')`
- `retry_pending_attachments_task` — `shared_task(name='intelligence.retry_pending_attachments')`; `track_scheduled_operation(OperationalRun.Task.RETRY_ATTACHMENTS)`

### `src/apps/platform/tasks.py`

- `close_previous_competence` — `shared_task(name='platform.close_previous_competence')`; `track_scheduled_operation(OperationalRun.Task.CLOSE_COMPETENCE)`
- `advance_tenant_lifecycles` — `shared_task(name='platform.advance_tenant_lifecycles')`; `track_scheduled_operation(OperationalRun.Task.ADVANCE_LIFECYCLES)`

### `src/apps/triage/tasks.py`

- `dispatch_active_mailboxes` — `shared_task(name='triage.dispatch_active_mailboxes')`
- `poll_activated_mailbox` — `shared_task(name='triage.poll_activated_mailbox')`

### Agenda declarada em base.py

```python
{'advance-tenant-lifecycles': {'task': 'platform.advance_tenant_lifecycles', 'schedule': crontab(hour=0, minute=1)}, 'close-previous-billing-competence': {'task': 'platform.close_previous_competence', 'schedule': crontab(hour=0, minute=5)}, 'refresh-approved-knowledge-chunks': {'task': 'intelligence.refresh_knowledge_chunks', 'schedule': crontab(hour=2, minute=10)}, 'refresh-shared-knowledge-chunks': {'task': 'intelligence.refresh_shared_knowledge_chunks', 'schedule': crontab(hour=2, minute=25)}, 'purge-expired-intelligence-conversations': {'task': 'intelligence.purge_expired_conversations', 'schedule': crontab(hour=2, minute=40)}, 'retry-pending-intelligence-attachments': {'task': 'intelligence.retry_pending_attachments', 'schedule': timedelta(minutes=5)}, 'reconcile-stale-claude-attempts': {'task': 'intelligence.reconcile_claude_attempts', 'schedule': timedelta(minutes=5)}, 'dispatch-active-triage-mailboxes': {'task': 'triage.dispatch_active_mailboxes', 'schedule': timedelta(minutes=TRIAGE_EMAIL_POLL_INTERVAL_MINUTES)}, 'dispatch-active-nfse-syncs': {'task': 'hub.dispatch_active_nfse_syncs', 'schedule': timedelta(minutes=NFSE_ADN_POLL_INTERVAL_MINUTES)}, 'refresh-reform-radar': {'task': 'hub.refresh_reform_sources', 'schedule': crontab(hour=5, minute=20)}, 'recover-reconciliation-runs': {'task': 'hub.recover_reconciliation_runs', 'schedule': timedelta(minutes=5)}, 'dispatch-waiting-reconciliation-runs': {'task': 'hub.dispatch_waiting_reconciliation_runs', 'schedule': timedelta(minutes=1)}}
```

## Serviços instaláveis, runtime e infraestrutura

| Componente | Evidência no checkout | Limite observado |
|---|---|---|
| Agente Python | `agent/runner.py`, `windows_service.py`, `install-windows-service.ps1`, fila e cliente sync | Leitura Domínio e serviço; exige homologação no host |
| Agente nativo | `Worker.cs`, `AgentClient.cs`, `BackupProcessor.cs`, `FileArchiveProcessor.cs` | Loop contém heartbeat, backup e arquivamento; sincronização local permanece Python |
| Instalador | `agent-windows/installer`, configurador e `build.ps1` | Código de MSI não prova instalação/atualização homologada |
| Treinamento | `runtime/trainer/runner.py`, Dockerfile, comandos de corpus/QLoRA | Preparação e runner existem; execução real/modelo definitivo não homologados |
| Inferência | `intelligence/gateway.py`, `multimodal.py`, Compose opcional | Roteamento/API e runtime local não provam desempenho no equipamento definitivo |
| Integrações | ADN, Integra, Graph, Gmail, IMAP, Asaas webhook, Radar | Testes de transporte não equivalem a homologação do fornecedor |

### Arquivos operacionais encontrados

- `.github/workflows/ci.yml`
- `.github/workflows/deploy-cobalchini.yml`
- `agent-windows/Directory.Build.props`
- `agent-windows/build.ps1`
- `agent-windows/installer/Package.wxs`
- `agent-windows/installer/Regaro.Agent.Installer.wixproj`
- `agent-windows/src/Regaro.Agent.Configurator/Program.cs`
- `agent-windows/src/Regaro.Agent.Configurator/Regaro.Agent.Configurator.csproj`
- `agent-windows/src/Regaro.Agent.Service/AgentClient.cs`
- `agent-windows/src/Regaro.Agent.Service/AgentConfig.cs`
- `agent-windows/src/Regaro.Agent.Service/BackupProcessor.cs`
- `agent-windows/src/Regaro.Agent.Service/FileArchiveProcessor.cs`
- `agent-windows/src/Regaro.Agent.Service/Program.cs`
- `agent-windows/src/Regaro.Agent.Service/Regaro.Agent.Service.csproj`
- `agent-windows/src/Regaro.Agent.Service/Worker.cs`
- `agent/__init__.py`
- `agent/hub_agent.py`
- `agent/install-windows-service.ps1`
- `agent/local_queue.py`
- `agent/runner.py`
- `agent/sync_client.py`
- `agent/windows_service.py`
- `deploy/nginx/edge-agent-mtls.conf`
- `runtime/__init__.py`
- `runtime/multimodal/Dockerfile`
- `runtime/trainer/Dockerfile`
- `runtime/trainer/__init__.py`
- `runtime/trainer/runner.py`
- `scripts/configure_fly.py`
- `scripts/generate_production_secrets.py`
- `scripts/init_local.py`
- `scripts/probe_fedrizzi_dctfweb_readonly.py`
- `scripts/qa_regaro_landing.py`
- `scripts/qa_ui_server.py`
- `scripts/setup-local-dominio.ps1`

## Contradições documentais reconciliadas

| Registro anterior | Evidência atual / decisão vigente | Tratamento nesta etapa |
|---|---|---|
| Inventário de 14/09 dizia que não havia coleta NFS-e | Cliente ADN, sync, testes e auditoria de 16/09 existem | Documento marcado histórico; não confundir implementação com homologação |
| Inventário antigo dizia faltar titularidade Serpro | D-08 confirma Mewstack central | Não repetir essa pergunta |
| Ações do responsável descreviam todos os aplicativos OAuth centrais | D-23 confirma app do escritório para Microsoft/Workspace, central para Gmail pessoal | Corrigir roteiro para seguir D-23 |
| Q-10 reabria papel de Claude após chegada da máquina | D-50 define reserva autorizada e D-51 separa aceite do pipeline | Encerrar Q-10; métricas ficam em Q-30 |
| Siescon indisponível sem adaptador | D-53 confirma banco disponível e D-54 define leitura/exportação | Atualizar disponibilidade do recurso; não declarar adaptador ou acesso já homologados |
| Conciliação descrita somente como OFX descartado | Novo domínio preserva fontes, layouts, execuções, lançamentos e exports | Referenciar decisões de conciliação; fluxo legado não descreve sozinho o módulo atual |
| D-37 e Q-31 afirmavam que função não escreve Windows | Arquivamento por agente e prova de integridade existem no código | Manter pergunta de nome/renomeação; corrigir estado técnico, sem afirmar homologação real |

Nenhuma divergência de regra de negócio foi resolvida por preferência técnica. Correções acima usam decisões explícitas ou distinguem fato de implementação e evidência externa.
