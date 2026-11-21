from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Performance and legacy analytics (PRD 3.1.8). Built in Increment 6."""

    name = "apps.analytics"
    label = "analytics"
    verbose_name = "Analytics"
