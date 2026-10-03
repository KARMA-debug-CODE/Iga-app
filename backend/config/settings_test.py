"""Settings for the pytest suite: production-like (DEBUG off) but over plain HTTP."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-that-is-long-enough-1234567890")
os.environ.setdefault("HTTPS", "false")
os.environ.setdefault("DJANGO_DEBUG", "false")

from .settings import *  # noqa: E402,F403
