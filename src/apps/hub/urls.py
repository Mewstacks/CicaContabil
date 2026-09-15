from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy

from apps.hub import views
from apps.platform.legal import legal_document

app_name = "hub"

urlpatterns = [
    path("legal/<slug:document>/", legal_document, name="legal"),
    path("", views.home, name="home"),
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
    path("app/guias/<uuid:guide_id>/emitir/", views.issue_guide, name="issue-guide"),
    path("app/integra-contador/", views.integra, name="integra"),
    path("app/integra-contador/dte/", views.dte_center, name="dte-center"),
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
        "app/conciliacao/<uuid:match_id>/confirmar/",
        views.confirm_reconciliation,
        name="confirm-reconciliation",
    ),
    path("app/radar-reforma/", views.reform, name="reform"),
    path("app/triagem/", views.triage, name="triage"),
    path("app/triagem/conectar-imap/", views.triage_imap_connect, name="triage-imap-connect"),
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
    path("app/revisoes/<uuid:case_id>/resolver/", views.resolve_review, name="resolve-review"),
    path("app/configuracoes/", views.settings_view, name="settings"),
    path("app/configuracao/", views.setup_center, name="setup"),
    path(
        "app/configuracoes/dominio/parear/",
        views.issue_dominio_agent_enrollment,
        name="dominio-agent-enrollment",
    ),
]
