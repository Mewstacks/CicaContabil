from django.apps import AppConfig


class AdmissionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admissions"
    verbose_name = "Admissões"

    def ready(self) -> None:
        from . import kinds  # noqa: F401  (registra os tipos RPA)
