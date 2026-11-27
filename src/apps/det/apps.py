from django.apps import AppConfig


class DetConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.det"
    verbose_name = "DET"

    def ready(self) -> None:
        from . import kinds  # noqa: F401  (registra os tipos RPA)
