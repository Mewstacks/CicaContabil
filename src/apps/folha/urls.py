from django.urls import path

from apps.folha import views

app_name = "folha"

urlpatterns = [
    path("", views.index, name="index"),
    path("ciclos/novo/", views.cycle_new, name="cycle-new"),
    path("ciclos/<uuid:cycle_id>/", views.cycle, name="cycle"),
    path("ciclos/<uuid:cycle_id>/acao/", views.cycle_action, name="cycle-action"),
    path("ciclos/<uuid:cycle_id>/envio/<uuid:company_id>/", views.send, name="send"),
    path("configuracao/", views.config, name="config"),
]
