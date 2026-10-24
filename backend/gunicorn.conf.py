"""gunicorn's settings for the backend container: gunicorn reads ./gunicorn.conf.py (the Dockerfile's CMD
runs it from /app). Each can be changed in the environment.

nginx sits in front of gunicorn: it reads every request whole before passing it on and buffers ordinary
answers, so slow clients tie up nginx's cheap connections, never these threads (frontend/nginx.conf). The
workers are threaded (gthread) so that slow calls, Santa's answers and C++/Java runs, don't hold up others.
"""

import os


def _int(name, default):
    return int(os.environ.get(name, default))


bind = "0.0.0.0:8000"
worker_class = "gthread"
workers = _int("GUNICORN_WORKERS", 3)
# Threads per worker: requests handled at once = workers x threads. Each Santa answer holds one while it streams.
threads = _int("GUNICORN_THREADS", 4)
# A worker that stops checking in with gunicorn for this long is restarted. (A request may take longer: with
# threaded workers it runs in a thread while the worker keeps checking in, bounded by SANTA_TIMEOUT_SECONDS
# and CODE_RUNNER_TIMEOUT_SECONDS.)
timeout = _int("GUNICORN_TIMEOUT", 60)
# On restart, requests in progress get this long to finish.
graceful_timeout = _int("GUNICORN_GRACEFUL_TIMEOUT", 30)
# Idle keep-alive connections from nginx close after this many seconds.
keepalive = _int("GUNICORN_KEEPALIVE", 5)
# Each worker is replaced after about this many requests, so a slow leak can't grow without end.
max_requests = _int("GUNICORN_MAX_REQUESTS", 2000)
max_requests_jitter = _int("GUNICORN_MAX_REQUESTS_JITTER", 200)
# The request line and headers: the same caps as nginx (8 KB per line, at most 100 headers).
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190
# gunicorn itself trusts X-Forwarded-* only from 127.0.0.1, which nginx (another container) is not;
# Django reads X-Forwarded-Proto and X-Forwarded-For from nginx itself (SECURE_PROXY_SSL_HEADER, TRUSTED_PROXY_COUNT).
forwarded_allow_ips = "127.0.0.1,::1"
accesslog = "-"
