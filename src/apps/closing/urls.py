from django.urls import path

from apps.closing import views

app_name = "closing"

urlpatterns = [
    path("", views.index, name="index"),
    path("enviar/", views.upload, name="upload"),
    path("documentos/<uuid:document_id>/", views.document, name="document"),
    path("documentos/<uuid:document_id>/arquivo/", views.document_file, name="document-file"),
    path("documentos/<uuid:document_id>/reler/", views.document_reread, name="document-reread"),
    path(
        "documentos/<uuid:document_id>/descartar/", views.document_discard, name="document-discard"
    ),
    path("documentos/<uuid:document_id>/layout/", views.document_to_layout, name="document-layout"),
    path(
        "documentos/<uuid:document_id>/conferencias/<uuid:conference_id>/decidir/",
        views.conference_decide,
        name="conference-decide",
    ),
    path("layouts/", views.layouts, name="layouts"),
    path("layouts/novo/", views.layout_new, name="layout-new"),
    path("layouts/<uuid:layout_id>/", views.layout, name="layout"),
    path("layouts/<uuid:layout_id>/campos/", views.layout_field_add, name="layout-field-add"),
    path(
        "layouts/<uuid:layout_id>/campos/<uuid:field_id>/remover/",
        views.layout_field_remove,
        name="layout-field-remove",
    ),
    path("layouts/<uuid:layout_id>/amostra/", views.layout_sample, name="layout-sample"),
    path("layouts/<uuid:layout_id>/ativar/", views.layout_activate, name="layout-activate"),
]
