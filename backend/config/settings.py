"""
Django settings for the Iga learning platform.

All deployment-specific values come from environment variables so the same
code runs on a laptop (SQLite) and in production (PostgreSQL behind HTTPS).
See backend/.env.example for the full list.
"""

import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# Fail safe: production (gunicorn via wsgi.py) runs with DEBUG off unless told
# otherwise. manage.py turns it on by default for local development.
DEBUG = env_bool("DJANGO_DEBUG", False)

PLACEHOLDER_SECRETS = {
    "",
    "change-me-to-a-long-random-string",
    "dev-only-insecure-key-do-not-use-in-production",
}
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if SECRET_KEY in PLACEHOLDER_SECRETS or len(SECRET_KEY) < 32:
    if not DEBUG:
        raise RuntimeError("Set DJANGO_SECRET_KEY to a long random value (at least 32 characters) when DJANGO_DEBUG is off.")
    SECRET_KEY = SECRET_KEY if len(SECRET_KEY) >= 32 else "dev-only-insecure-key-do-not-use-in-production"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")

APP_NAME = os.environ.get("APP_NAME", "Iga")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "apps.core",
    "apps.accounts",
    "apps.curriculum",
    "apps.simulations",
    "apps.assessments",
    "apps.classroom",
    "apps.community",
    "apps.gamification",
    "apps.tutor",
    "apps.schools",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite for local development; set DATABASE_URL=postgres://... in production.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=int(os.environ.get("DB_CONN_MAX_AGE", "60")),
    )
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("fr", "Français")]
TIME_ZONE = "Africa/Kigali"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Rate limits and other caches must be shared between server processes in
# production, so point REDIS_URL at a Redis instance there.
if os.environ.get("REDIS_URL"):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": os.environ["REDIS_URL"]}}

# --- REST API -------------------------------------------------------------

# Number of reverse proxies in front of Django that append to X-Forwarded-For
# (1 for the bundled nginx). 0 means use the direct connection address only.
TRUSTED_PROXY_COUNT = int(os.environ.get("TRUSTED_PROXY_COUNT", "0"))

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.IgaJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    # Per-IP throttles only trust X-Forwarded-For entries added by our own proxies.
    "NUM_PROXIES": TRUSTED_PROXY_COUNT,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    # Per-IP limits are generous because a whole school often shares one public IP;
    # "login" is per account and is what actually stops password guessing.
    "DEFAULT_THROTTLE_RATES": {
        "auth": os.environ.get("THROTTLE_AUTH", "300/min"),
        "login": os.environ.get("THROTTLE_LOGIN", "10/min"),
        "refresh": os.environ.get("THROTTLE_REFRESH", "600/min"),
        "chat": os.environ.get("THROTTLE_CHAT", "30/min"),
        # Per user: password / 2FA changes, and guessing class, group or parent codes.
        "sensitive": os.environ.get("THROTTLE_SENSITIVE", "5/min"),
        "join": os.environ.get("THROTTLE_JOIN", "10/min"),
        "tutor": os.environ.get("THROTTLE_TUTOR", "30/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", "14"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

# The refresh token lives in an httpOnly cookie scoped to the auth endpoints,
# so page scripts never see it. The short-lived access token stays in memory.
REFRESH_COOKIE_NAME = "iga_refresh"
REFRESH_COOKIE_PATH = "/api/auth/"
REFRESH_COOKIE_SECURE = env_bool("REFRESH_COOKIE_SECURE", env_bool("HTTPS", not DEBUG))
REFRESH_COOKIE_SAMESITE = os.environ.get("REFRESH_COOKIE_SAMESITE", "Lax")
# A used refresh token that comes back later means it was stolen, and every session of
# that user is ended. Within this window it is treated as two tabs refreshing at once.
REFRESH_REUSE_GRACE_SECONDS = int(os.environ.get("REFRESH_REUSE_GRACE_SECONDS", "30"))

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

# --- AI tutor (Claude API) -------------------------------------------------
# Switched on when an Anthropic credential is configured (ANTHROPIC_API_KEY),
# or explicitly with TUTOR_ENABLED=true (e.g. when using an `ant auth` profile).
TUTOR_ENABLED = env_bool("TUTOR_ENABLED", bool(os.environ.get("ANTHROPIC_API_KEY")))
TUTOR_MODEL = os.environ.get("TUTOR_MODEL", "claude-opus-5-5")
TUTOR_EFFORT = os.environ.get("TUTOR_EFFORT", "low")
TUTOR_MAX_TOKENS = int(os.environ.get("TUTOR_MAX_TOKENS", "4000"))
TUTOR_TIMEOUT_SECONDS = float(os.environ.get("TUTOR_TIMEOUT_SECONDS", "60"))

# --- School subscriptions -------------------------------------------------
# Each school pays a flat monthly price for all its members. Prices per currency:
# USD for cards; set SUBSCRIPTION_PRICE_RWF to also accept mobile money in francs.
SUBSCRIPTION_PRICES = {"USD": Decimal(os.environ.get("SUBSCRIPTION_PRICE_USD", "200"))}
if os.environ.get("SUBSCRIPTION_PRICE_RWF"):
    SUBSCRIPTION_PRICES["RWF"] = Decimal(os.environ["SUBSCRIPTION_PRICE_RWF"])
SUBSCRIPTION_MONTH_OPTIONS = [1, 3, 6, 12]
# Days a lapsed subscription keeps working while the school renews.
SUBSCRIPTION_GRACE_DAYS = int(os.environ.get("SUBSCRIPTION_GRACE_DAYS", "3"))
# Online payments: "flutterwave" (cards and mobile money) or "" for manual payments only.
BILLING_PROVIDER = os.environ.get("BILLING_PROVIDER", "")
# A fake checkout for local demos and tests. Never enable it in production.
BILLING_DEV_MODE = env_bool("BILLING_DEV_MODE", DEBUG)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
# Flutterwave (cards and MTN/Airtel mobile money). Test keys start with FLWSECK_TEST-.
FLUTTERWAVE_SECRET_KEY = os.environ.get("FLUTTERWAVE_SECRET_KEY", "")
FLUTTERWAVE_WEBHOOK_HASH = os.environ.get("FLUTTERWAVE_WEBHOOK_HASH", "")
FLUTTERWAVE_BASE_URL = os.environ.get("FLUTTERWAVE_BASE_URL", "https://api.flutterwave.com/v3")
# Used as the payer's email when the school administrator has none (providers require one).
BILLING_FALLBACK_EMAIL = os.environ.get("BILLING_FALLBACK_EMAIL", "billing@iga.rw")
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Iga <no-reply@iga.rw>")

# Behind the bundled nginx, protected files (uploaded past papers) are sent by nginx from an
# internal location after Django has checked access. Without nginx, Django streams them.
PROTECTED_MEDIA_ACCEL = env_bool("PROTECTED_MEDIA_ACCEL", False)

# Largest file a teacher may upload as a resource (nginx allows 25 MB per request).
UPLOAD_MAX_MB = int(os.environ.get("UPLOAD_MAX_MB", "20"))

# Grace period after a timed exam's deadline during which a final submit is
# still accepted (covers slow mobile connections).
EXAM_SUBMIT_GRACE_SECONDS = int(os.environ.get("EXAM_SUBMIT_GRACE_SECONDS", "30"))

# The Django admin (/django-admin/) is for content managers. In production it is
# off unless DJANGO_ADMIN_ENABLED=true, and staff must use two-factor login.
ADMIN_ENABLED = env_bool("DJANGO_ADMIN_ENABLED", DEBUG)
ADMIN_REQUIRE_2FA = env_bool("DJANGO_ADMIN_REQUIRE_2FA", not DEBUG)
ADMIN_LOGIN_ATTEMPTS_PER_MINUTE = int(os.environ.get("ADMIN_LOGIN_ATTEMPTS_PER_MINUTE", "10"))

# --- Production hardening --------------------------------------------------

# HTTPS defaults to on whenever DEBUG is off. Only switch it off for a local
# docker-compose trial over plain http://localhost.
HTTPS = env_bool("HTTPS", not DEBUG)
if HTTPS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
