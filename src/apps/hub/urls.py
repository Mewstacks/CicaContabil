from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy

from apps.hub import views
from apps.platform.legal import legal_document

app_name = "hub"

urlpatterns = [
    path("legal/<slug:document>/", legal_document, name="legal"),
    path("", views.home, name="home"),
    path("demo/", views.demo_entry, name="demo-entry"),
    path("proposta/", views.legacy_proposal, name="proposal"),
    path("proposta/cnpj/", views.proposal_cnpj, name="proposal-cnpj"),
    path("comecar/", views.signup, name="signup"),
    path("comecar/verificar/<str:token>/", views.verify_signup, name="signup-verify"),
    path("ativar/<str:token>/", views.activate_invitation, name="activate"),
    path("entrar/", views.login_view, name="login"),
    path("sair/", LogoutView.as_view(), name="logout"),
    path(
        "recuperar-senha/",
        auth_views.PasswordResetView.as_view(
            template_name="hub/password_reset_form.html",
            email_template_name="hub/emails/password_reset_email.txt",
            subject_template_name="hub/emails/password_reset_subject.txt",
            success_url=reverse_lazy("hub:password-reset-done"),
        ),
        name="password-reset",
    ),
    path(
        "recuperar-senha/enviado/",
        auth_views.PasswordResetDoneView.as_view(template_name="hub/password_reset_done.html"),
        name="password-reset-done",
    ),
    path(
        "recuperar-senha/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(
            template_name="hub/password_reset_confirm.html",
            success_url=reverse_lazy("hub:password-reset-complete"),
        ),
        name="password-reset-confirm",
    ),
    path(
        "recuperar-senha/concluida/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="hub/password_reset_complete.html"
        ),
        name="password-reset-complete",
    ),
    path("app/", views.dashboard, name="dashboard"),
    path("app/equipe/", views.team, name="team"),
    path(
        "app/equipe/convites/<uuid:invitation_id>/reenviar/",
        views.resend_collaborator_invitation,
        name="collaborator-invitation-resend",
    ),
    path(
        "app/equipe/convites/<uuid:invitation_id>/revogar/",
        views.revoke_collaborator_invitation,
        name="collaborator-invitation-revoke",
    ),
    path(
        "app/equipe/<uuid:membership_id>/acessos/",
        views.update_collaborator_access,
        name="collaborator-access",
    ),
    path(
        "app/equipe/<uuid:membership_id>/remover/",
        views.deactivate_collaborator,
        name="collaborator-deactivate",
    ),
    path("app/nfse/", views.nfse_center, name="nfse-center"),
    path("app/guias/", views.guides, name="guides"),
    path("app/guias/dctfweb/consultar/", views.dctfweb_consult, name="dctfweb-consult"),
    path(
        "app/guias/dctfweb/consultar-em-lote/",
        views.dctfweb_bulk_consult,
        name="dctfweb-bulk-consult",
    ),
    path(
        "app/guias/dctfweb/documentos/<uuid:document_id>.pdf",
        views.dctfweb_document_pdf,
        name="dctfweb-document-pdf",
    ),
    path("app/guias/<uuid:guide_id>/", views.guide_detail, name="guide-detail"),
    path("app/guias/<uuid:guide_id>/documento.pdf", views.guide_pdf, name="guide-pdf"),
    path("app/guias/<uuid:guide_id>/exemplo.pdf", views.demo_guide_pdf, name="demo-guide-pdf"),
    path("app/guias/<uuid:guide_id>/emitir/", views.issue_guide, name="issue-guide"),
    path("app/integra-contador/", views.integra, name="integra"),
    path(
        "app/integra-contador/parcelamentos/",
        views.parcelamentos,
        name="parcelamentos",
    ),
    path(
        "app/integra-contador/parcelamentos/das/<uuid:operation_id>.pdf",
        views.parcelamento_das_pdf,
        name="parcelamento-das-pdf",
    ),
    path("app/integra-contador/dte/", views.dte_center, name="dte-center"),
    path(
        "app/integra-contador/dte/consultas/<uuid:item_id>/proxima-pagina/",
        views.prepare_dte_continuation,
        name="dte-next-page",
    ),
    path(
        "app/integra-contador/dte/mensagens/<uuid:message_id>/",
        views.dte_message_detail,
        name="dte-message-detail",
    ),
    path(
        "app/integra-contador/dte/<uuid:run_id>/decidir/",
        views.decide_dte_run,
        name="decide-dte-run",
    ),
    path("app/conciliacao/", views.reconciliation, name="reconciliation"),
    path(
        "app/conciliacao/configuracao/",
        views.reconciliation_configuration,
        name="reconciliation-configuration",
    ),
    path("app/conciliacao/auditoria/", views.reconciliation_audit, name="reconciliation-audit"),
    path("app/conciliacao/importar/", views.reconciliation_upload, name="reconciliation-upload"),
    path(
        "app/conciliacao/processamentos/<uuid:run_id>/",
        views.reconciliation_run_status,
        name="reconciliation-run-status",
    ),
    path(
        "app/conciliacao/processamentos/<uuid:run_id>/acao/",
        views.reconciliation_run_action,
        name="reconciliation-run-action",
    ),
    path(
        "app/conciliacao/arquivos/<uuid:source_id>/mapear/",
        views.reconciliation_mapping,
        name="reconciliation-mapping",
    ),
    path(
        "app/conciliacao/arquivos/<uuid:source_id>/download/",
        views.reconciliation_source_download,
        name="reconciliation-source-download",
    ),
    path(
        "app/conciliacao/arquivos/<uuid:source_id>/visualizar/",
        views.reconciliation_source_preview,
        name="reconciliation-source-preview",
    ),
    path(
        "app/conciliacao/movimentos/<uuid:movement_id>/",
        views.reconciliation_movement_detail,
        name="reconciliation-movement",
    ),
    path(
        "app/conciliacao/movimentos/acoes-em-lote/",
        views.reconciliation_movement_bulk_action,
        name="reconciliation-movement-bulk-action",
    ),
    path(
        "app/conciliacao/exportar/",
        views.reconciliation_export_create,
        name="reconciliation-export-create",
    ),
    path(
        "app/conciliacao/exportacoes/<uuid:export_id>/download/",
        views.reconciliation_export_download,
        name="reconciliation-export-download",
    ),
    path(
        "app/conciliacao/<uuid:match_id>/confirmar/",
        views.confirm_reconciliation,
        name="confirm-reconciliation",
    ),
    path("app/radar-reforma/", views.reform, name="reform"),
    path("app/triagem/", views.triage, name="triage"),
    path("app/triagem/caixas/", views.triage_connections, name="triage-connections"),
    path("app/triagem/conectar-imap/", views.triage_imap_connect, name="triage-imap-connect"),
    path(
        "app/triagem/destino/",
        views.triage_destination_configure,
        name="triage-destination-configure",
    ),
    path(
        "app/triagem/aplicativo/<str:provider>/",
        views.triage_oauth_app_save,
        name="triage-oauth-app-save",
    ),
    path(
        "app/triagem/conectar/<slug:provider>/",
        views.triage_oauth_start,
        name="triage-oauth-start",
    ),
    path(
        "app/triagem/oauth/<slug:provider>/retorno/",
        views.triage_oauth_callback,
        name="triage-oauth-callback",
    ),
    path(
        "app/triagem/caixas/<uuid:mailbox_id>/configurar/",
        views.triage_mailbox_configure,
        name="triage-mailbox-configure",
    ),
    path(
        "app/triagem/caixas/<uuid:mailbox_id>/desconectar/",
        views.triage_mailbox_disconnect,
        name="triage-mailbox-disconnect",
    ),
    path("app/triagem/<uuid:item_id>/", views.triage_item_detail, name="triage-item"),
    path("app/triagem/<uuid:item_id>/arquivo/", views.triage_download, name="triage-download"),
    path("app/trocar-escritorio/", views.switch_office, name="switch-office"),
    path("app/aparencia/", views.set_theme, name="set-theme"),
    path("app/empresas/", views.companies, name="companies"),
    path("app/empresas/<uuid:company_id>/", views.company_detail, name="company-detail"),
    path("app/certificados/", views.certificates, name="certificates"),
    path("app/revisoes/", views.reviews, name="reviews"),
    path("app/revisoes/<uuid:case_id>/", views.review_detail, name="review-detail"),
    path(
        "app/revisoes/<uuid:case_id>/original.xml",
        views.review_original_xml,
        name="review-original-xml",
    ),
    path("app/revisoes/<uuid:case_id>/resolver/", views.resolve_review, name="resolve-review"),
    path("app/configuracoes/", views.settings_view, name="settings"),
    path("app/configuracao/", views.setup_center, name="setup"),
    path(
        "app/configuracoes/dominio/parear/",
        views.issue_dominio_agent_enrollment,
        name="dominio-agent-enrollment",
    ),
]
