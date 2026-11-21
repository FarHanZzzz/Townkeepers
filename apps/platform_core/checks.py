"""System checks that keep development shortcuts out of production (TR 4.2, AC-15)."""

from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def demo_auth_disabled_in_production(app_configs, **kwargs):
    errors = []
    if getattr(settings, "IS_PRODUCTION", False) and getattr(settings, "DEMO_AUTH", False):
        errors.append(
            Error(
                "DEMO_AUTH is enabled in production settings.",
                hint="Demonstration identities must stay isolated from live sign-in. Set DEMO_AUTH=false.",
                id="townhall.E001",
            )
        )
    if getattr(settings, "IS_PRODUCTION", False) and not settings.IUB_ALLOWED_DOMAINS:
        errors.append(
            Warning(
                "IUB_ALLOWED_DOMAINS is empty, so every live sign-in will be denied.",
                hint="IUB identity owners supply the eligible hosted domains (PRD Appendix C.2).",
                id="townhall.W001",
            )
        )
    return errors
