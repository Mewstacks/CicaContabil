from django.urls import path

from apps.intelligence import views

app_name = "intelligence"

urlpatterns = [
    path("", views.assistant, name="assistant"),
    path("relatorios/<uuid:message_id>/<str:export_format>/", views.export_answer, name="export"),
    path("feedback/<uuid:message_id>/", views.submit_feedback, name="feedback"),
    path("aprendizado/", views.learning_center, name="learning"),
    path("aprendizado/<uuid:candidate_id>/<str:decision>/", views.review_candidate, name="review"),
]
