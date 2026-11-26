from django.urls import path

from apps.delivery import views

app_name = "delivery"

urlpatterns = [
    path("", views.index, name="index"),
    path("novo/", views.compose, name="compose"),
    path("conta/", views.account, name="account"),
    path("liberacao/", views.release_days, name="release-days"),
    path("<uuid:delivery_id>/", views.detail, name="detail"),
    path("<uuid:delivery_id>/reenviar/", views.resend, name="resend"),
    path("<uuid:delivery_id>/cancelar/", views.cancel, name="cancel"),
]
