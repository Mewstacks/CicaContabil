from django.contrib.auth.views import LogoutView
from django.urls import path

from apps.hub import views

app_name = "hub"

urlpatterns = [
    path("", views.home, name="home"),
    path("proposta/", views.proposal, name="proposal"),
    path("ativar/<str:token>/", views.activate_invitation, name="activate"),
    path("entrar/", views.login_view, name="login"),
    path("sair/", LogoutView.as_view(), name="logout"),
    path("app/", views.dashboard, name="dashboard"),
    path("app/nfse/", views.nfse_center, name="nfse-center"),
    path("app/guias/", views.guides, name="guides"),
    path("app/integra-contador/", views.integra, name="integra"),
    path("app/integra-contador/dte/", views.dte_center, name="dte-center"),
    path(
        "app/integra-contador/dte/<uuid:run_id>/decidir/",
        views.decide_dte_run,
        name="decide-dte-run",
    ),
    path("app/conciliacao/", views.reconciliation, name="reconciliation"),
    path("app/radar-reforma/", views.reform, name="reform"),
    path("app/trocar-escritorio/", views.switch_office, name="switch-office"),
    path("app/empresas/", views.companies, name="companies"),
    path("app/empresas/<uuid:company_id>/", views.company_detail, name="company-detail"),
    path("app/certificados/", views.certificates, name="certificates"),
    path("app/revisoes/", views.reviews, name="reviews"),
    path("app/revisoes/<uuid:case_id>/resolver/", views.resolve_review, name="resolve-review"),
    path("app/configuracoes/", views.settings_view, name="settings"),
    path(
        "app/configuracoes/dominio/parear/",
        views.issue_dominio_agent_enrollment,
        name="dominio-agent-enrollment",
    ),
]
