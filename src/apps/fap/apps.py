from django.apps import AppConfig


class FapConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.fap"
    verbose_name = "FAP"

    def ready(self) -> None:
        from . import kinds  # noqa: F401  (registra os tipos RPA)
