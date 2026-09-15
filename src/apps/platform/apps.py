from django.apps import AppConfig


class PlatformConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform"
    verbose_name = "CICA — Plataforma"

    def ready(self) -> None:
        from apps.platform import signals  # noqa: F401
