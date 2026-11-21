"""Test settings: PostgreSQL, in-memory email, synthetic identity domain."""

from .base import *  # noqa: F403
from .base import BASE_DIR, env

DEBUG = False
SECRET_KEY = "test-only-insecure-key"  # noqa: S105
ALLOWED_HOSTS = ["testserver", "127.0.0.1", "localhost"]
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
DEMO_AUTH = True
IUB_ALLOWED_DOMAINS = ["iub-synthetic.test"]
GOOGLE_CLIENT_ID = "synthetic-client-id"
GOOGLE_CLIENT_SECRET = "synthetic-client-secret"  # noqa: S105
PRIVATE_MEDIA_ROOT = BASE_DIR / "var" / "test-private"
ASSISTANCE_SERVICE_TOKEN = "synthetic-service-token"  # noqa: S105
ASSISTANCE_TIMEOUT_SECONDS = env.float("ASSISTANCE_TIMEOUT_SECONDS", default=1.0)
LOGGING["root"]["level"] = "WARNING"  # noqa: F405
