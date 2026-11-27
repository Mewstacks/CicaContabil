from django.apps import AppConfig


class FolhaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.folha"
    verbose_name = "Folha: relatórios no Domínio"

    def ready(self) -> None:
        from . import kinds  # noqa: F401  (registra os tipos RPA)
