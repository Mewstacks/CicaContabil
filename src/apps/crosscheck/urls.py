from django.urls import path

from apps.crosscheck import views

app_name = "crosscheck"

urlpatterns = [
    path("", views.index, name="index"),
    path("nova/", views.new_run, name="new-run"),
    path("modelo-dominio/", views.dominio_template, name="dominio-template"),
    path("<uuid:run_id>/", views.run_detail, name="run-detail"),
    path("<uuid:run_id>/estado/", views.run_status, name="run-status"),
    path("<uuid:run_id>/arquivos/", views.run_attach, name="run-attach"),
    path("<uuid:run_id>/arquivos/<uuid:input_id>/remover/", views.run_remove, name="run-remove"),
    path("<uuid:run_id>/agente/consultar/", views.run_agent_request, name="run-agent-request"),
    path("<uuid:run_id>/agente/arquivo/", views.run_agent_file, name="run-agent-file"),
    path("<uuid:run_id>/conferir/", views.run_start, name="run-start"),
    path("<uuid:run_id>/cancelar/", views.run_cancel, name="run-cancel"),
    path("<uuid:run_id>/repetir/", views.run_repeat, name="run-repeat"),
    path("<uuid:run_id>/baixar/<str:fmt>/", views.run_download, name="run-download"),
]
