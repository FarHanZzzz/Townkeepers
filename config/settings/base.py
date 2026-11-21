"""Shared settings. Environment-specific modules import from here."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
IS_PRODUCTION = False

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "apps.platform_core",
    "apps.accounts",
    "apps.clubs",
    "apps.events",
    "apps.finance",
    "apps.memos",
    "apps.publishing",
    "apps.analytics",
]

MIDDLEWARE = [
    "apps.platform_core.middleware.CorrelationIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.platform_core.middleware.LoginRequiredMiddleware",
    "apps.platform_core.middleware.DomainErrorMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.platform_core.context_processors.navigation",
            ],
        },
    },
]

DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://townhall:townhall_local@localhost:5432/townhall"
    )
}
DATABASES["default"]["TEST"] = {"NAME": env("TEST_DATABASE_NAME", default="test_townhall")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.Profile"
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.ActiveProfileBackend"]
LOGIN_URL = "accounts:sign_in"
LOGIN_REDIRECT_URL = "dashboard"
AUTH_PASSWORD_VALIDATORS: list[dict] = []

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=8 * 60 * 60)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = False
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "var" / "staticfiles"

# Private evidence storage. Never served by the static or media handlers.
PRIVATE_MEDIA_ROOT = Path(env("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "var" / "private")))
MAX_UPLOAD_BYTES = env.int("MAX_UPLOAD_BYTES", default=10 * 1024 * 1024)
MAX_SIGNATURE_BYTES = 300 * 1024
STAGED_UPLOAD_RETENTION_HOURS = env.int("STAGED_UPLOAD_RETENTION_HOURS", default=24)
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_BYTES + 1024 * 1024

DEFAULT_CURRENCY = "BDT"

# Identity. IUB supplies the eligible hosted domains (PRD Appendix C.2); empty denies live sign-in.
IUB_ALLOWED_DOMAINS = [d.lower() for d in env.list("IUB_ALLOWED_DOMAINS", default=[])]
# Individually provisioned test addresses (e.g. the PRD's example account). Never a whole domain.
EXPLICIT_TEST_ACCOUNTS = [a.lower() for a in env.list("EXPLICIT_TEST_ACCOUNTS", default=[])]
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")
GOOGLE_OIDC_METADATA_URL = "https://accounts.google.com/.well-known/openid-configuration"
DEMO_AUTH = env.bool("DEMO_AUTH", default=False)
DEMO_EMAIL_DOMAIN = "townhall.test"

MAILERS = {
    "default": {
        "BACKEND": env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
    }
}
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="townhall-noreply@townhall.test")
SITE_BASE_URL = env("SITE_BASE_URL", default="http://127.0.0.1:8000")
# Empty until a club website is configured. An unset destination records a failed external send.
EXTERNAL_PUBLISH_URL = env("EXTERNAL_PUBLISH_URL", default="")

ASSISTANCE_URL = env("ASSISTANCE_URL", default="http://127.0.0.1:8001")
ASSISTANCE_SERVICE_TOKEN = env("ASSISTANCE_SERVICE_TOKEN", default="")
ASSISTANCE_TIMEOUT_SECONDS = env.float("ASSISTANCE_TIMEOUT_SECONDS", default=5.0)

WORKER_LEASE_SECONDS = env.int("WORKER_LEASE_SECONDS", default=120)
WORKER_MAX_ATTEMPTS = env.int("WORKER_MAX_ATTEMPTS", default=5)
WORKER_HEARTBEAT_STALE_SECONDS = 300

# Single-holder EB designations per club term (FR-IAM-02, FR-CLB-03). Others may have several holders.
SINGLE_HOLDER_DESIGNATIONS = ["president", "secretary", "treasurer"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"correlation": {"()": "apps.platform_core.logging.CorrelationIdFilter"}},
    "formatters": {
        "plain": {
            "format": "%(asctime)s %(levelname)s %(name)s [%(correlation_id)s] %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["correlation"],
            "formatter": "plain",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}
