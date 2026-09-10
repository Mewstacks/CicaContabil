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
    path("app/trocar-escritorio/", views.switch_office, name="switch-office"),
    path("app/trocar-empresa/", views.switch_company, name="switch-company"),
    path("app/empresas/", views.companies, name="companies"),
    path("app/certificados/", views.certificates, name="certificates"),
    path("app/revisoes/", views.reviews, name="reviews"),
    path("app/revisoes/<uuid:case_id>/resolver/", views.resolve_review, name="resolve-review"),
    path("app/configuracoes/", views.settings_view, name="settings"),
]
