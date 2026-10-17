"""
Django settings for the Iga learning platform.

All deployment-specific values come from environment variables so the same
code runs on a laptop (SQLite) and in production (PostgreSQL behind HTTPS).
See backend/.env.example for the full list.
"""

import os
import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def env_origins(name, default="", subdomain_wildcards=False):
    """Origins (scheme://host[:port]) from the environment. Anything else, a "*" above all, would let other
    sites in, so it stops the start. CSRF_TRUSTED_ORIGINS may use Django's https://*.example.rw form."""
    origins = env_list(name, default)
    for origin in origins:
        scheme, _, host = origin.partition("://")
        if subdomain_wildcards and host.startswith("*."):
            host = host[2:]
        if scheme not in ("http", "https") or not re.fullmatch(
            r"[A-Za-z0-9.-]+(:[0-9]{1,5})?|\[[0-9A-Fa-f:.]+\](:[0-9]{1,5})?", host
        ):
            raise RuntimeError(
                f"{name}: {origin!r} is not an origin such as https://iga.example.rw (no wildcards, paths or trailing slashes)."
            )
    return origins


# Fail safe: production (gunicorn via wsgi.py) runs with DEBUG off unless told
# otherwise. manage.py turns it on by default for local development.
DEBUG = env_bool("DJANGO_DEBUG", False)

PLACEHOLDER_SECRETS = {
    "",
    "change-me-to-a-long-random-string",
    "dev-only-insecure-key-do-not-use-in-production",
    "build-time-placeholder-only-used-for-collectstatic",  # the image build's, before it used a random one
}
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if SECRET_KEY in PLACEHOLDER_SECRETS or len(SECRET_KEY) < 32:
    if not DEBUG:
        raise RuntimeError("Set DJANGO_SECRET_KEY to a long random value (at least 32 characters) when DJANGO_DEBUG is off.")
    SECRET_KEY = SECRET_KEY if len(SECRET_KEY) >= 32 else "dev-only-insecure-key-do-not-use-in-production"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")

# Keys for the secrets and personal data encrypted in the database (apps/core/encryption.py):
# comma-separated Fernet keys, the first encrypts and every one decrypts (for key rotation). Generate
# one with: python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
FIELD_ENCRYPTION_KEYS = env_list("FIELD_ENCRYPTION_KEYS")
if not FIELD_ENCRYPTION_KEYS:
    if not DEBUG:
        raise RuntimeError("Set FIELD_ENCRYPTION_KEYS (see .env.docker.example) when DJANGO_DEBUG is off.")
    # Local development only: a key derived from the (development) secret key.
    import base64
    import hashlib

    FIELD_ENCRYPTION_KEYS = [base64.urlsafe_b64encode(hashlib.sha256(f"iga-fields:{SECRET_KEY}".encode()).digest()).decode()]
else:
    import base64

    from cryptography.fernet import Fernet

    for _key in FIELD_ENCRYPTION_KEYS:
        try:
            Fernet(_key)
        except ValueError:
            raise RuntimeError(
                "FIELD_ENCRYPTION_KEYS must hold Fernet keys: 32 random bytes, URL-safe base64 (44 characters)."
            ) from None
        _raw = base64.urlsafe_b64decode(_key)
        # A phrase or a run of one character, base64-encoded, is a valid key but not a secret one.
        if len(set(_raw)) < 12 or all(32 <= byte < 127 for byte in _raw):
            raise RuntimeError("FIELD_ENCRYPTION_KEYS holds a key that is not random: generate one (see .env.docker.example).")

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
    "apps.coderun",
    "apps.schools",
    "apps.website",
    "apps.review",
    "apps.planner",
    "apps.notes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Content-Security-Policy, Permissions-Policy and Cross-Origin-Resource-Policy on every answer.
    "apps.core.middleware.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Answers (error messages included) in the reader's language: the app sends Accept-Language.
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    # A NUL character in the URL or query string is a 400 (PostgreSQL can't store one).
    "apps.core.middleware.RejectNulMiddleware",
    # Maintenance mode: 503 "back soon" for everyone but platform admins (apps/core/maintenance.py).
    "apps.core.maintenance.MaintenanceModeMiddleware",
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

# Argon2id for every new or changed password. The other hashers only read older hashes, which Django
# re-hashes with Argon2id the next time their owner logs in.
PASSWORD_HASHERS = [
    "apps.accounts.hashers.IgaArgon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]
# Argon2id costs (Django's defaults). Each login briefly uses ARGON2_MEMORY_COST_KIB of memory.
ARGON2_TIME_COST = int(os.environ.get("ARGON2_TIME_COST", "2"))
ARGON2_MEMORY_COST_KIB = int(os.environ.get("ARGON2_MEMORY_COST_KIB", "102400"))
ARGON2_PARALLELISM = int(os.environ.get("ARGON2_PARALLELISM", "8"))

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("fr", "Français")]
# The French catalogue of Iga's own messages (see scripts/messages.py).
LOCALE_PATHS = [BASE_DIR / "locale"]
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
    # DRF's parsers, refusing text with a NUL character (a 400 instead of a database error).
    "DEFAULT_PARSER_CLASSES": [
        "apps.core.parsers.JSONParser",
        "apps.core.parsers.FormParser",
        "apps.core.parsers.MultiPartParser",
    ],
    # JSON only in production: DRF's browsable HTML API is a development tool.
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]
    + (["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    # Refused (403) and throttled (429) requests are logged as security events.
    "EXCEPTION_HANDLER": "apps.core.security_log.exception_handler",
    "PAGE_SIZE": 50,
    # Per-IP throttles only trust X-Forwarded-For entries added by our own proxies.
    "NUM_PROXIES": TRUSTED_PROXY_COUNT,
    # Every view is limited (apps/core/throttles.py): its own scope when it has one, plus "anon" (per IP,
    # visitors not signed in) and "user" (per signed-in user). Views with their own throttle_classes replace
    # these with stricter ones. nginx adds per-IP limits in front (frontend/nginx.conf).
    "DEFAULT_THROTTLE_CLASSES": [
        "apps.core.throttles.ScopedRateThrottle",
        "apps.core.throttles.AnonRateThrottle",
        "apps.core.throttles.UserRateThrottle",
    ],
    # Per-IP limits are generous because a whole school often shares one public IP;
    # "login" is per account and is what actually stops password guessing.
    "DEFAULT_THROTTLE_RATES": {
        # Per IP: any request without a signed-in user (the backstop for endpoints with no scope).
        "anon": os.environ.get("THROTTLE_ANON", "600/min"),
        # Per signed-in user: any request (far above what a person does by hand).
        "user": os.environ.get("THROTTLE_USER", "600/min"),
        # Per IP: sign-in, sign-up, password reset and 2FA requests together.
        "auth": os.environ.get("THROTTLE_AUTH", "300/min"),
        # Per account (the username or email typed): sign-in attempts. Repeated failures also lock
        # the account for a while (LOGIN_LOCKOUT_* below).
        "login": os.environ.get("THROTTLE_LOGIN", "10/min"),
        # Per IP: new accounts (a whole class may sign up together from one school address).
        "register": os.environ.get("THROTTLE_REGISTER", "100/hour"),
        # Password reset emails: per account (so nobody floods an inbox) and per IP.
        "password_reset": os.environ.get("THROTTLE_PASSWORD_RESET", "5/hour"),
        "password_reset_ip": os.environ.get("THROTTLE_PASSWORD_RESET_IP", "30/hour"),
        # Session refreshes: per IP, and per account (only validly signed refresh cookies count).
        "refresh": os.environ.get("THROTTLE_REFRESH", "600/min"),
        "refresh_user": os.environ.get("THROTTLE_REFRESH_USER", "60/min"),
        "chat": os.environ.get("THROTTLE_CHAT", "30/min"),
        # Per user: password / 2FA changes, and guessing class, group or parent codes.
        "sensitive": os.environ.get("THROTTLE_SENSITIVE", "5/min"),
        "join": os.environ.get("THROTTLE_JOIN", "10/min"),
        # The billing return page asks every few seconds while mobile money is confirmed.
        "billing_confirm": os.environ.get("THROTTLE_BILLING_CONFIRM", "30/min"),
        "tutor": os.environ.get("THROTTLE_TUTOR", "30/hour"),
        # Per user: C++ and Java runs in the code playground.
        "code_run": os.environ.get("THROTTLE_CODE_RUN", "20/min"),
        # Per user: answers typed into a running program.
        "code_input": os.environ.get("THROTTLE_CODE_INPUT", "120/min"),
        # Per user: "Download my data" (it reads every table that holds the user's data).
        "data_export": os.environ.get("THROTTLE_DATA_EXPORT", "5/hour"),
        # Per IP: messages sent with the contact form.
        "contact": os.environ.get("THROTTLE_CONTACT", "20/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", "14"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

# Progressive lockout after failed sign-ins (apps/accounts/lockout.py): failures in a row for one
# account from one IP, for one account from anywhere, and from one IP for any account. The first
# lock lasts LOGIN_LOCKOUT_BASE_SECONDS and doubles with each lock that day, up to the maximum.
LOGIN_LOCKOUT_THRESHOLD = int(os.environ.get("LOGIN_LOCKOUT_THRESHOLD", "5"))
LOGIN_LOCKOUT_ACCOUNT_THRESHOLD = int(os.environ.get("LOGIN_LOCKOUT_ACCOUNT_THRESHOLD", "20"))
LOGIN_LOCKOUT_IP_THRESHOLD = int(os.environ.get("LOGIN_LOCKOUT_IP_THRESHOLD", "100"))
LOGIN_LOCKOUT_BASE_SECONDS = int(os.environ.get("LOGIN_LOCKOUT_BASE_SECONDS", "60"))
LOGIN_LOCKOUT_MAX_SECONDS = int(os.environ.get("LOGIN_LOCKOUT_MAX_SECONDS", "3600"))
# Failures further apart than this don't add up.
LOGIN_FAILURE_WINDOW_SECONDS = int(os.environ.get("LOGIN_FAILURE_WINDOW_SECONDS", "900"))

# Password reset links work once, for this many seconds, and only until the password changes or a
# newer link is sent (apps/accounts/password_reset.py).
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT_SECONDS", "3600"))
# A temporary password a teacher hands out (class roster, password reset) stops working after this.
TEMPORARY_PASSWORD_DAYS = int(os.environ.get("TEMPORARY_PASSWORD_DAYS", "14"))
# Answers saying "this email address is already used" per hour, per IP (sign-up) or per account
# (profile, class roster) before every request with an email is refused until the hour is over.
EMAIL_IN_USE_LIMIT = int(os.environ.get("EMAIL_IN_USE_LIMIT", "10"))

# Privileged operations (the admin area, school membership and billing decisions, resetting a student's
# password) need a password confirmed this recently: at sign-in or at POST /api/auth/step-up/.
STEP_UP_MAX_AGE_SECONDS = int(os.environ.get("STEP_UP_MAX_AGE_SECONDS", "900"))

# The refresh token lives in an httpOnly cookie scoped to the auth endpoints,
# so page scripts never see it. The short-lived access token stays in memory.
REFRESH_COOKIE_NAME = "iga_refresh"
REFRESH_COOKIE_PATH = "/api/auth/"
REFRESH_COOKIE_SECURE = env_bool("REFRESH_COOKIE_SECURE", env_bool("HTTPS", not DEBUG))
# Strict: the browser never sends it with a request started by another site. The app and its API
# share one site, so nothing else is needed (refresh and logout also check the Origin header).
REFRESH_COOKIE_SAMESITE = os.environ.get("REFRESH_COOKIE_SAMESITE", "Strict")
# A used refresh token that comes back later means it was stolen, and every session of
# that user is ended. Within this window it is treated as two tabs refreshing at once.
REFRESH_REUSE_GRACE_SECONDS = int(os.environ.get("REFRESH_REUSE_GRACE_SECONDS", "30"))

# Cross-origin access. nginx serves the app and the API from one origin, so a deployment needs none: other
# sites get no CORS grant unless CORS_ALLOWED_ORIGINS lists them (only for an app served from another
# origin). Never a wildcard, and only on the API. The Vite dev server's origins are trusted in development.
DEV_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173" if DEBUG else ""
CORS_ALLOWED_ORIGINS = env_origins("CORS_ALLOWED_ORIGINS", DEV_ORIGINS)
CORS_ALLOWED_ORIGIN_REGEXES = []
CORS_ALLOW_ALL_ORIGINS = False
CORS_URLS_REGEX = r"^/api/"
CORS_ALLOW_CREDENTIALS = True
# Origins whose pages may send forms and cookie-authenticated requests (the Django admin, refresh and logout)
# besides the site itself: the public https:// origin when a proxy changes the Host Django sees.
CSRF_TRUSTED_ORIGINS = env_origins("CSRF_TRUSTED_ORIGINS", DEV_ORIGINS, subdomain_wildcards=True)
# Django's own session and CSRF cookies only serve the Django admin: scoped to it, out of reach of
# page scripts, never sent cross-site with a form, Secure under HTTPS (below), and admin sessions
# end after DJANGO_ADMIN_SESSION_HOURS.
SESSION_COOKIE_PATH = "/django-admin/"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = int(float(os.environ.get("DJANGO_ADMIN_SESSION_HOURS", "8")) * 3600)
CSRF_COOKIE_PATH = "/django-admin/"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
# Django admin forms refused for a missing or wrong CSRF token are logged as security events.
CSRF_FAILURE_VIEW = "apps.core.security_log.csrf_failure"

# --- Santa, Iga's own AI tutor ---------------------------------------------
# Santa's model runs on the school's own server: the "santa" service in docker-compose.yml (llama.cpp's
# llama-server with an open model). Django calls its OpenAI-compatible API on the internal network, so
# questions never leave the server. Empty SANTA_URL = the model is not installed; Santa then answers
# from Iga's lessons only. See apps/tutor/llm.py and the Santa section of README.md.
SANTA_URL = os.environ.get("SANTA_URL", "").strip()
# The key the model server expects (its LLAMA_API_KEY). Docker Compose gives both sides the same value.
SANTA_API_KEY = os.environ.get("SANTA_API_KEY", "").strip()
# The model's name on the server (llama-server --alias).
SANTA_MODEL_NAME = os.environ.get("SANTA_MODEL_NAME", "santa")
# Longest answer, in tokens (about 450 words), and how creative answers are (0 = always the same).
SANTA_MAX_TOKENS = int(os.environ.get("SANTA_MAX_TOKENS", "600"))
SANTA_TEMPERATURE = float(os.environ.get("SANTA_TEMPERATURE", "0.6"))
# The most time one answer may take, tool rounds included. A CPU server writes about 8-12 tokens a second.
SANTA_TIMEOUT_SECONDS = float(os.environ.get("SANTA_TIMEOUT_SECONDS", "150"))
# Answers written at the same time (match llama-server -np). Each holds a web-server thread while it
# streams; when all are busy, Santa answers from the lessons and asks the student to try again soon.
SANTA_PARALLEL = int(os.environ.get("SANTA_PARALLEL", "4"))
# The most one question may send the model besides its fixed system prompt, in tokens (counted as 3
# characters each): the history, the context and lesson passages are cut to fit. With the system prompt
# (about 1,000 tokens) and SANTA_MAX_TOKENS it must fit one llama-server slot (-c / -np: 4,096 by default).
# SANTA_MAX_TOKENS is for the whole answer, calculator rounds included.
SANTA_MAX_INPUT_TOKENS = int(os.environ.get("SANTA_MAX_INPUT_TOKENS", "2800"))
# Santa's allowances (0 = no limit), counted per day (Kigali time) and per calendar month. Questions the
# model answers count; answers made of lesson passages don't. When one is used up, Santa answers from the
# lessons and says so, and the student sees what is left (apps/tutor/usage.py).
SANTA_USER_DAILY_QUESTIONS = int(os.environ.get("SANTA_USER_DAILY_QUESTIONS", "60"))
SANTA_USER_MONTHLY_QUESTIONS = int(os.environ.get("SANTA_USER_MONTHLY_QUESTIONS", "800"))
SANTA_USER_DAILY_TOKENS = int(os.environ.get("SANTA_USER_DAILY_TOKENS", "250000"))
SANTA_USER_MONTHLY_TOKENS = int(os.environ.get("SANTA_USER_MONTHLY_TOKENS", "3000000"))
# All the members of one school together, per day: so one school can't use up a shared server.
SANTA_SCHOOL_DAILY_TOKENS = int(os.environ.get("SANTA_SCHOOL_DAILY_TOKENS", "20000000"))

# --- Code runner (C++ and Java in the playground) ---------------------------
# Iga's code runner (the coderunner/ folder), reachable only from Django; empty = C++ and Java are off.
# Docker Compose starts one at http://coderunner:2000. See apps/coderun/services.py.
CODE_RUNNER_URL = os.environ.get("CODE_RUNNER_URL", "").strip()
CODE_RUNNER_TOKEN = os.environ.get("CODE_RUNNER_TOKEN", "").strip()
# Compiling (up to 30 s) plus running until the program ends or asks for input (up to 10 s), plus a margin.
CODE_RUNNER_TIMEOUT_SECONDS = float(os.environ.get("CODE_RUNNER_TIMEOUT_SECONDS", "45"))
# Who may run C++ and Java: "signed_in" (every signed-in user, like the other playgrounds) or "subscribed"
# (members of a subscribed school, and platform admins).
CODE_RUNNER_ACCESS = os.environ.get("CODE_RUNNER_ACCESS", "signed_in").strip().lower()
# Per user and day (Kigali time; 0 = no limit): programs started, and CPU seconds used compiling and running
# them, as measured by the code runner. A run that starts under the limit may finish over it.
CODE_RUNNER_DAILY_RUNS = int(os.environ.get("CODE_RUNNER_DAILY_RUNS", "300"))
CODE_RUNNER_DAILY_CPU_SECONDS = int(os.environ.get("CODE_RUNNER_DAILY_CPU_SECONDS", "900"))

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
# A real deployment (DEBUG off, HTTPS on) refuses to start with the fake checkout or a Flutterwave test key
# (checks iga.E010, iga.E011). Only a staging server that takes test payments on purpose sets this.
BILLING_ALLOW_TEST_PAYMENTS = env_bool("BILLING_ALLOW_TEST_PAYMENTS", False)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
# Flutterwave (cards and MTN/Airtel mobile money). Test keys start with FLWSECK_TEST-.
FLUTTERWAVE_SECRET_KEY = os.environ.get("FLUTTERWAVE_SECRET_KEY", "")
FLUTTERWAVE_WEBHOOK_HASH = os.environ.get("FLUTTERWAVE_WEBHOOK_HASH", "")
FLUTTERWAVE_BASE_URL = os.environ.get("FLUTTERWAVE_BASE_URL", "https://api.flutterwave.com/v3")
FLUTTERWAVE_MAX_RETRIES = int(os.environ.get("FLUTTERWAVE_MAX_RETRIES", "5"))
# How long a hosted checkout stays open (minutes). Payments still open after it are re-checked and
# closed by `manage.py reconcile_payments`; a success reported later is still applied.
CHECKOUT_SESSION_MINUTES = int(os.environ.get("CHECKOUT_SESSION_MINUTES", "60"))
# How far back reconcile_payments re-checks open payments with the provider.
BILLING_RECONCILE_DAYS = int(os.environ.get("BILLING_RECONCILE_DAYS", "3"))
# Used as the payer's email when the school administrator has none (providers require one).
BILLING_FALLBACK_EMAIL = os.environ.get("BILLING_FALLBACK_EMAIL", "billing@iga.rw")
# The money ledger (apps/schools/ledger.py) chains its entries by hash. With a key, the hashes are
# HMAC-SHA256, so someone who can write to the database but doesn't have the key can't rebuild the
# chain after changing an entry. Optional; once set, keep it (entries written with it need it to verify).
LEDGER_HMAC_KEY = os.environ.get("LEDGER_HMAC_KEY", "")
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
# Seconds before giving up on the mail server, so a silent one can't hang a payment or the scheduler.
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Iga <no-reply@iga.rw>")

# Behind the bundled nginx, protected files (uploaded past papers) are sent by nginx from an
# internal location after Django has checked access. Without nginx, Django streams them.
PROTECTED_MEDIA_ACCEL = env_bool("PROTECTED_MEDIA_ACCEL", False)

# Largest file a teacher may upload as a resource (nginx allows 25 MB per request, only on upload routes).
UPLOAD_MAX_MB = int(os.environ.get("UPLOAD_MAX_MB", "20"))
# Images are smaller: at most this many MB, and this many pixels in all (frames of an animation included),
# so a small file that unpacks into a huge picture can't use the server's memory. See apps/core/uploads.py.
UPLOAD_IMAGE_MAX_MB = int(os.environ.get("UPLOAD_IMAGE_MAX_MB", "5"))
UPLOAD_IMAGE_MAX_PIXELS = int(os.environ.get("UPLOAD_IMAGE_MAX_PIXELS", "50000000"))

# The longest text (a lesson, a shared note, a question) a text field without its own limit accepts.
# Shorter fields keep their own limits. See apps/core/text.py.
TEXT_MAX_CHARS = int(os.environ.get("TEXT_MAX_CHARS", "100000"))

# Request size limits. nginx refuses bigger bodies first (frontend/nginx.conf: 2 MB for the API, 25 MB on
# upload routes); these also protect a deployment without it. A refused request is a JSON 413
# (apps/core/errors.py). The body Django reads into memory (JSON, form fields; uploaded files excluded):
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get("DATA_UPLOAD_MAX_MEMORY_SIZE", str(2 * 1024 * 1024)))
# Uploaded files larger than this are written to a temporary file instead of being held in memory.
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get("FILE_UPLOAD_MAX_MEMORY_SIZE", str(2 * 1024 * 1024)))
# Form fields and files in one request (JSON bodies are limited by size only).
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(os.environ.get("DATA_UPLOAD_MAX_NUMBER_FIELDS", "1000"))
DATA_UPLOAD_MAX_NUMBER_FILES = int(os.environ.get("DATA_UPLOAD_MAX_NUMBER_FILES", "10"))

# --- Legal, privacy and the public site --------------------------------------
# The Terms of Use and Privacy Policy (frontend/src/legal/) are accepted together, as one version: the date
# they last changed. Raise it whenever either text changes in a way people must agree to again: everyone is
# asked to accept the new version at their next visit (apps/accounts/legal.py).
LEGAL_VERSION = os.environ.get("LEGAL_VERSION", "2026-10-17").strip()
# The note at the top of both pages saying they are drafts a lawyer must review before launch. Set it to
# false once a lawyer has approved the texts.
LEGAL_DRAFT_NOTICE = env_bool("LEGAL_DRAFT_NOTICE", True)
# Who is responsible for the personal data (the "data controller"), and how to reach them about privacy.
LEGAL_ENTITY_NAME = os.environ.get("LEGAL_ENTITY_NAME", "Iga").strip()
LEGAL_ENTITY_ADDRESS = os.environ.get("LEGAL_ENTITY_ADDRESS", "Kigali, Rwanda").strip()
PRIVACY_CONTACT_EMAIL = os.environ.get("PRIVACY_CONTACT_EMAIL", "privacy@iga.rw").strip()
# Where the servers (and so the personal data) are. Storing personal data outside Rwanda needs an
# authorisation from the supervisory authority (NCSA): see docs/DEPLOYMENT.md.
DATA_HOSTING_LOCATION = os.environ.get("DATA_HOSTING_LOCATION", "Rwanda").strip()
# "Delete my account": days during which signing in again cancels the deletion. Then `manage.py
# privacy_cleanup` (the scheduler runs it) erases or anonymises the account (apps/accounts/privacy.py).
ACCOUNT_DELETION_GRACE_DAYS = int(os.environ.get("ACCOUNT_DELETION_GRACE_DAYS", "14"))
# How long records are kept (days; 0 = keep them). `manage.py privacy_cleanup` deletes older ones.
# Santa's questions and answers (kept for safeguarding review):
SANTA_LOG_RETENTION_DAYS = int(os.environ.get("SANTA_LOG_RETENTION_DAYS", "365"))
# The audit log (sign-ins, security events, content changes, marks, approvals):
AUDIT_LOG_RETENTION_DAYS = int(os.environ.get("AUDIT_LOG_RETENTION_DAYS", "730"))
# Daily usage counters of Santa and the code runner:
USAGE_RETENTION_DAYS = int(os.environ.get("USAGE_RETENTION_DAYS", "400"))
# Messages sent with the contact form:
CONTACT_RETENTION_DAYS = int(os.environ.get("CONTACT_RETENTION_DAYS", "730"))
# Database backups (the backup service in docker-compose.yml keeps this many days; shown in the Privacy Policy).
BACKUP_KEEP_DAYS = int(os.environ.get("BACKUP_KEEP_DAYS", "14"))
# Where messages from the contact form are emailed (they are also kept for platform admins in Admin ->
# Messages). Empty: kept only.
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "").strip()

# Maintenance mode: every API request gets 503 "back soon" except a platform admin's, and nginx shows its
# "back soon" page. On while MAINTENANCE_MODE is true or the file MAINTENANCE_FILE exists (`manage.py
# maintenance on|off`; docker compose shares the file with nginx). See apps/core/maintenance.py.
MAINTENANCE_MODE = env_bool("MAINTENANCE_MODE", False)
MAINTENANCE_FILE = os.environ.get("MAINTENANCE_FILE", str(BASE_DIR / "maintenance" / "on")).strip()

# Grace period after a timed exam's deadline during which a final submit is
# still accepted (covers slow mobile connections).
EXAM_SUBMIT_GRACE_SECONDS = int(os.environ.get("EXAM_SUBMIT_GRACE_SECONDS", "30"))

# The Django admin is for content managers. In production it is off unless DJANGO_ADMIN_ENABLED=true AND
# DJANGO_ADMIN_PATH is a long random secret (at least 16 letters, digits, - or _): it then lives at
# /django-admin/<DJANGO_ADMIN_PATH>/. Staff must use two-factor login (always, when DEBUG is off).
ADMIN_ENABLED = env_bool("DJANGO_ADMIN_ENABLED", DEBUG)
ADMIN_PATH = os.environ.get("DJANGO_ADMIN_PATH", "").strip().strip("/")
ADMIN_REQUIRE_2FA = env_bool("DJANGO_ADMIN_REQUIRE_2FA", False) if DEBUG else True
ADMIN_LOGIN_ATTEMPTS_PER_MINUTE = int(os.environ.get("ADMIN_LOGIN_ATTEMPTS_PER_MINUTE", "10"))
# Per address too, so one machine can't try a password on many staff accounts.
ADMIN_LOGIN_IP_ATTEMPTS_PER_MINUTE = int(os.environ.get("ADMIN_LOGIN_IP_ATTEMPTS_PER_MINUTE", "30"))

# --- Production hardening --------------------------------------------------

# HTTPS defaults to on whenever DEBUG is off. Only switch it off for a local
# docker-compose trial over plain http://localhost.
HTTPS = env_bool("HTTPS", not DEBUG)
if HTTPS:
    # Behind a proxy (TRUSTED_PROXY_COUNT > 0: the bundled nginx, which sets X-Forwarded-Proto itself and
    # takes the client's value only from proxies it trusts), believe its word for the scheme. With no proxy,
    # anyone could send the header, so it is ignored and gunicorn's own scheme counts.
    if TRUSTED_PROXY_COUNT > 0:
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # "preload" asks browsers to ship this site as HTTPS-only (hstspreload.org): a commitment for the whole
    # domain and every subdomain that is slow to undo, so the owner opts in (HSTS_PRELOAD=true in .env).
    SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
    if not SECURE_HSTS_PRELOAD:
        # check --deploy's reminder about preload (security.W021): left off on purpose until the owner opts in.
        SILENCED_SYSTEM_CHECKS = ["security.W021"]
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# Django's defaults, written out: links to other sites carry no path, and no other window keeps a handle on ours.
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    # Security events (apps/core/security_log.py) are one JSON object per line, for a log collector.
    "formatters": {"json_line": {"format": "%(message)s"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "security": {"class": "logging.StreamHandler", "formatter": "json_line"},
    },
    "loggers": {
        "iga.security": {
            "handlers": ["security"],
            "level": os.environ.get("SECURITY_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
