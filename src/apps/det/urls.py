from django.urls import path

from apps.det import views

app_name = "det"

urlpatterns = [
    path("", views.index, name="index"),
    path("consultas/nova/", views.query_new, name="query-new"),
    path("consultas/<uuid:query_id>/", views.query, name="query"),
    path("consultas/<uuid:query_id>/planilha/", views.sheet, name="sheet"),
]
