from django.urls import path

from apps.fgts import views

app_name = "fgts"

urlpatterns = [
    path("", views.index, name="index"),
    path("fonte/", views.source, name="source"),
    path("lotes/novo/", views.batch_new, name="batch-new"),
    path("itens/<uuid:item_id>/", views.item_action, name="item"),
    path("configuracao/", views.config, name="config"),
]
