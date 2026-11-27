from django.urls import path

from apps.admissions import views

app_name = "admissions"

urlpatterns = [
    path("", views.index, name="index"),
    path("nova/", views.new, name="new"),
    path("<uuid:admission_id>/", views.detail, name="detail"),
    path("<uuid:admission_id>/acao/", views.action, name="action"),
    path("configuracao/", views.config, name="config"),
]
