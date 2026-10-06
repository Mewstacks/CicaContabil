from django.urls import path

from apps.platform import views
from apps.platform.configuration import configuration
from apps.platform.fiscal_calendar_views import fiscal_calendar_review
from apps.platform.webhooks import asaas

app_name = "platform"

urlpatterns = [
    path("configuracoes/", configuration, name="configuration"),
    path("agenda-tributaria/", fiscal_calendar_review, name="fiscal-calendar"),
    path("", views.dashboard, name="dashboard"),
    path("tenants/", views.tenants, name="tenants"),
    path("tenants/<uuid:organization_id>/", views.tenant_detail, name="tenant-detail"),
    path("tenants/<uuid:organization_id>/support/", views.start_support, name="start-support"),
    path("support/encerrar/", views.end_support, name="end-support"),
    path("webhooks/asaas/", asaas, name="asaas-webhook"),
]
