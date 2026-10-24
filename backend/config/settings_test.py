"""Settings for the pytest suite: production-like (DEBUG off) but over plain HTTP."""

import base64
import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-that-is-long-enough-1234567890")
os.environ.setdefault("HTTPS", "false")
os.environ.setdefault("DJANGO_DEBUG", "false")
# A fresh random key for each test run (encrypted fields): no key is ever written in the repository.
os.environ.setdefault("FIELD_ENCRYPTION_KEYS", base64.urlsafe_b64encode(os.urandom(32)).decode())

from .settings import *  # noqa: E402,F403
