from django.apps import AppConfig


class PlatformCoreConfig(AppConfig):
    name = "apps.platform_core"
    label = "platform_core"
    verbose_name = "Platform core"

    def ready(self) -> None:
        from . import checks, job_handlers  # noqa: F401  (registers checks and job handlers)
