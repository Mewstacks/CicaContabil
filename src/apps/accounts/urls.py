from __future__ import annotations

from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("configurar/", views.setup, name="mfa-setup"),
    path("entrar/", views.verify, name="mfa-verify"),
    path("qr.svg", views.enrollment_qr, name="mfa-qr"),
    path("codigos/", views.regenerate_recovery_codes, name="mfa-recovery-codes"),
]
