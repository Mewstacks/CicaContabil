from django.urls import path

from apps.profitability import views

app_name = "profitability"

urlpatterns = [
    path("", views.overview, name="overview"),
]
