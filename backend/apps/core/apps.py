from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from django.urls import register_converter

        from . import checks  # noqa: F401  (registers Iga's system checks)
        from .converters import IdConverter

        register_converter(IdConverter, "id")
