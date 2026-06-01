from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Общее"

    def ready(self):
        import core.admin_site  # noqa: F401
