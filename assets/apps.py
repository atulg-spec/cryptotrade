from django.apps import AppConfig


class AssetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assets"

    def ready(self):
        # Import signal handlers
        from . import signals  # noqa
