from django.apps import AppConfig


class FgtsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.fgts"
    verbose_name = "FGTS Digital"

    def ready(self) -> None:
        from . import kinds  # noqa: F401  (registra os tipos RPA)
