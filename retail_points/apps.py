from django.apps import AppConfig


class RetailPointsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "retail_points"
    verbose_name = "Торговые точки"

    def ready(self):
        import retail_points.signals  # noqa: F401
