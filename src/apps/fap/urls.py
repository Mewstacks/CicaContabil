from django.urls import path

from apps.fap import views

app_name = "fap"

urlpatterns = [
    path("", views.index, name="index"),
    path("lotes/novo/", views.batch_new, name="batch-new"),
    path("lotes/<uuid:batch_id>/", views.batch, name="batch"),
    path("lotes/<uuid:batch_id>/acao/", views.batch_action, name="batch-action"),
    path("itens/<uuid:item_id>/arquivo/", views.item_file, name="item-file"),
    path("itens/<uuid:item_id>/reprocessar/", views.item_reprocess, name="item-reprocess"),
    path("configuracao/", views.config, name="config"),
]
