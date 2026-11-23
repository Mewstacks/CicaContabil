from django.apps import AppConfig


class HubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.hub"
    verbose_name = "CICA"

    def ready(self) -> None:
        from apps.hub import signals  # noqa: F401  (D-397 receivers)
