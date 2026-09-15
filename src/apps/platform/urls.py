from django.urls import path

from apps.platform import views
from apps.platform.configuration import configuration

app_name = "platform"

urlpatterns = [
    path("configuracoes/", configuration, name="configuration"),
    path("", views.dashboard, name="dashboard"),
    path("tenants/", views.tenants, name="tenants"),
    path("tenants/<uuid:organization_id>/", views.tenant_detail, name="tenant-detail"),
    path("tenants/<uuid:organization_id>/support/", views.start_support, name="start-support"),
    path("support/encerrar/", views.end_support, name="end-support"),
]
