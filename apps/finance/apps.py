from django.apps import AppConfig


class FinanceConfig(AppConfig):
    name = "apps.finance"
    label = "finance"
    verbose_name = "Financial and fund management"

    def ready(self):
        from . import access  # noqa: F401
