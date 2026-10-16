FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# collectstatic needs settings to load; production settings refuse short keys and a missing field
# encryption key, so the build uses a long placeholder and a throwaway random key. The real keys come
# from the environment when the container runs.
RUN DJANGO_DEBUG=false DJANGO_SECRET_KEY=build-time-placeholder-only-used-for-collectstatic \
    FIELD_ENCRYPTION_KEYS="$(python -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')" \
    python manage.py collectstatic --noinput \
    && useradd --create-home --uid 1000 iga \
    && mkdir -p /app/media \
    && chown -R iga /app/media

USER iga
EXPOSE 8000

# Apply migrations, then serve. Under docker compose the "migrate" service has already applied them as the
# owner role, so here (as the app role, which may not change the schema) this only runs the system checks
# that stop a misconfigured production start. Load content once with:
#   docker compose exec backend python manage.py load_curriculum
# gunicorn's settings (workers, threads, timeouts, request caps) are in gunicorn.conf.py.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application"]
