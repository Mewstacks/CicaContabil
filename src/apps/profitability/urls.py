from django.urls import path

from apps.profitability import views

app_name = "profitability"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("clientes/<uuid:company_id>/", views.client_detail, name="client-detail"),
    path("colaboradores/", views.collaborators, name="collaborators"),
    path(
        "colaboradores/<uuid:collaborator_id>/",
        views.collaborator_detail,
        name="collaborator-detail",
    ),
    path("horas/", views.hours, name="hours"),
    path("analises/", views.analyses, name="analyses"),
    path("configuracao/", views.settings_view, name="settings"),
]
