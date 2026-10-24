# Deploying Iga to production

A step-by-step checklist for putting Iga on a real server for real schools. It uses the bundled
`docker-compose.yml`: PostgreSQL, Redis, Django on gunicorn, nginx serving the built app, the code runner
for C++ and Java, the daily backup service, and (optional) Santa's model server.

Read it alongside:

- [README.md](../README.md) — the same stack for a local trial, and Santa in detail.
- [ARCHITECTURE.md](ARCHITECTURE.md) — what each part does and the security model.
- [CLOUDFLARE.md](CLOUDFLARE.md) — HTTPS and DDoS protection in front of Iga.
- [SUBSCRIPTIONS.md](SUBSCRIPTIONS.md) — how schools pay, and setting up Flutterwave.
- [`.env.docker.example`](../.env.docker.example) — every setting, with safe defaults.

Work top to bottom the first time. The boxes are things to tick off.

---

## 1. Before you start

- [ ] A server with Docker Engine and the Docker Compose plugin. **4 GB of RAM** runs the app without Santa's
      own model; **16 GB** (and 4–8 CPU cores) is recommended to run Santa too (see [§9](#9-santa-optional)).
      Give it enough disk for the database, uploaded files and the backups you keep.
- [ ] A domain name you control (for example `iga.example.rw`), pointed at the server (or at Cloudflare).
- [ ] A plan for HTTPS: Cloudflare, a load balancer, or nginx with your own certificate ([§4](#4-https)).
- [ ] An email account or service for sending mail (password resets, receipts, contact notifications).
- [ ] If schools will pay online: a Flutterwave account ([SUBSCRIPTIONS.md](SUBSCRIPTIONS.md)).

Get the code onto the server and copy the example environment file:

```bash
git clone <your Iga repository> iga && cd iga
cp .env.docker.example .env
```

Everything below is edits to `.env` and `docker compose` commands run in that folder. `.env` is ignored by git
and by every image build, so secrets never end up in the repository or the images.

---

## 2. Generate the secrets

Iga refuses to start in production with any secret that is short, a placeholder, or a value the repository or
docs have ever used (check `iga.E002`; `docker compose logs migrate` names the culprit). Generate a fresh
random value for each. Two helpers:

```bash
# A URL-safe secret (secret key, tokens, passwords, webhook hash, ledger key):
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
# A Fernet key (field encryption only):
python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Set these in `.env`:

| Variable | What it is | Required |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django's signing key | **Always** |
| `FIELD_ENCRYPTION_KEYS` | encrypts 2FA secrets, phone numbers, payment details (Fernet key) | **Always** |
| `POSTGRES_PASSWORD` | the database superuser (used only by the one-off `migrate` service) | Real deployment |
| `POSTGRES_OWNER_PASSWORD` | the role that owns the tables and runs migrations | Real deployment |
| `POSTGRES_APP_PASSWORD` | the role Django runs as (rows only) | Real deployment |
| `CODE_RUNNER_TOKEN` | shared secret between Django and the code runner | If C++/Java are on |
| `SANTA_API_KEY` | shared secret between Django and Santa's model server | If Santa's model is on |
| `FLUTTERWAVE_SECRET_KEY`, `FLUTTERWAVE_WEBHOOK_HASH` | your Flutterwave keys | If taking online payments |
| `LEDGER_HMAC_KEY` | signs the money ledger's hash chain (optional, but set it before the first payment) | Recommended |

**Keep `FIELD_ENCRYPTION_KEYS` safe and apart from the database backups.** Without it, the encrypted columns
in a restored backup cannot be read. The same goes for `LEDGER_HMAC_KEY`: once set, keep it and never change it
(older ledger entries need it to verify).

---

## 3. Domain, hosts and origins

Set these in `.env` to your real domain (the backend refuses unknown hosts):

```ini
DJANGO_ALLOWED_HOSTS=iga.example.rw
CSRF_TRUSTED_ORIGINS=https://iga.example.rw
FRONTEND_URL=https://iga.example.rw
```

- `FRONTEND_URL` is where payment and email links point, and the address written into `robots.txt` and the
  sitemap. Set it even if you are not taking payments.
- nginx serves the app and the API from one origin, so no other site needs CORS access. Only set
  `CORS_ALLOWED_ORIGINS` if you serve the app from a different origin (https only; wildcards are refused).

---

## 4. HTTPS

A real deployment runs over HTTPS only. Leave `HTTPS=false` **out** of `.env` (delete the line the example
ships with): nginx then redirects plain HTTP and sends HSTS, Django redirects and marks every cookie `Secure`,
and `manage.py check --deploy` is clean. Pick one way to get the certificate:

- **Cloudflare or a load balancer that terminates HTTPS** (simplest, and the only real defence against large
  floods): set `NGINX_TRUSTED_PROXIES` so nginx believes the proxy's `X-Forwarded-Proto` and `X-Forwarded-For`,
  and nothing else's. Full steps, including which Cloudflare settings to turn on, are in
  [CLOUDFLARE.md](CLOUDFLARE.md).
- **nginx with your own certificate** (Let's Encrypt or Cloudflare Origin CA): copy
  [`frontend/nginx/tls.conf.example`](../frontend/nginx/tls.conf.example) to `tls/tls.conf`, put
  `fullchain.pem` and `privkey.pem` in `certs/`, and mount both with the `docker-compose.override.yml` shown at
  the top of that file (it also publishes ports 80 and 443).

`HSTS_PRELOAD=true` is a commitment that your whole domain, every subdomain, will be HTTPS for good. Turn it on
only once that is true.

---

## 5. Email (SMTP)

Password reset links, payment receipts, subscription reminders and contact-form notifications all go by email.
Without real settings Iga only prints them to the logs (the default console backend), so set these in `.env`:

```ini
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=Iga <no-reply@iga.example.rw>
# Where a message from the public contact form is sent (also kept in Admin -> Messages):
CONTACT_EMAIL=hello@iga.example.rw
```

Use an address your provider lets you send from, or a transactional email service. After the stack is up, test
it: use "Forgot your password?" on the sign-in page and the contact form on `/contact`, and check both arrive.

---

## 6. Legal pages and data protection

Iga ships draft Terms of Use and a Privacy Policy, written for a Rwandan school product used by minors and
built around Rwanda's **Law N° 058/2021** on the protection of personal data and privacy. **A lawyer must
review both before launch.** Until then, each page shows a visible "draft" note.

Set the real details in `.env` (they appear in the pages):

```ini
LEGAL_ENTITY_NAME=Iga Ltd                 # the data controller
LEGAL_ENTITY_ADDRESS=KN 0 St, Kigali, Rwanda
PRIVACY_CONTACT_EMAIL=privacy@iga.example.rw
DATA_HOSTING_LOCATION=Rwanda              # where the servers (and the data) are
```

- Hosting personal data **outside Rwanda** needs an authorisation from the supervisory authority (the NCSA).
  Keep the servers and backups in Rwanda unless you have one.
- After the lawyer approves the texts, set `LEGAL_DRAFT_NOTICE=false` to remove the note.
- Whenever you change the Terms or Privacy Policy in a way users must agree to again, raise `LEGAL_VERSION`
  (a date is clearest). Signed-in users are then asked to accept the new version at their next visit.

Retention periods are shown in the Privacy Policy and enforced by `privacy_cleanup` (the scheduler runs it;
[§11](#11-monitoring-and-maintenance)). The defaults are sensible; change them in `.env` only with a reason
(`ACCOUNT_DELETION_GRACE_DAYS`, `SANTA_LOG_RETENTION_DAYS`, `AUDIT_LOG_RETENTION_DAYS`, `USAGE_RETENTION_DAYS`,
`CONTACT_RETENTION_DAYS`).

---

## 7. Start the stack

```bash
# Add the two always-required secrets if you have not already:
echo "DJANGO_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')" >> .env
echo "FIELD_ENCRYPTION_KEYS=$(python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')" >> .env

docker compose up --build -d
docker compose logs -f migrate      # watch it set up the roles and apply migrations, then exit 0
```

The one-off `migrate` service creates the two least-privilege database roles with the superuser and applies the
migrations as the owner role; the backend and scheduler then connect as `iga_app`, which may only read and
write rows (see "Database roles" in [ARCHITECTURE.md](ARCHITECTURE.md#database-roles)). If a secret is weak,
`migrate` stops and says which one.

Load the curriculum once:

```bash
docker compose exec backend python manage.py load_curriculum
```

Do **not** run `seed_demo` on a real server — it refuses to run with `DJANGO_DEBUG` off, because demo accounts
have well-known passwords.

Confirm the deployment checks are clean (should print "no issues"):

```bash
docker compose exec backend python manage.py check --deploy
```

---

## 8. Create the first platform admin

A platform admin runs the whole service: verifying schools, recording payments, moderation, the admin area.
Create the first one interactively:

```bash
docker compose exec backend python manage.py createsuperuser
```

Give it a username, an email and a strong password. This account can sign in at your domain and use the
**Admin** area in the app. From there it can promote other staff. Turn on two-factor authentication for it in
**Profile -> Security** straight away: platform actions need a recently confirmed password (and the 2FA code
when it is on).

The content managers' Django admin stays off unless you turn it on (`DJANGO_ADMIN_ENABLED=true` plus a long
random `DJANGO_ADMIN_PATH`); see [`.env.docker.example`](../.env.docker.example).

---

## 9. Santa (optional)

Santa, the AI tutor, answers from the lessons on its own. To also run its language model on your server, start
the `santa` profile. The model runs locally, so no question ever leaves the server. Hardware, model choices,
going fully offline and GPUs are all covered in [README "Santa"](../README.md#santa-igas-own-ai-tutor). The
short version:

```ini
# in .env
COMPOSE_PROFILES=santa
SANTA_API_KEY=<a random secret>
# On an 8 GB server, use the smaller model:
# SANTA_MODEL=google/gemma-4-E2B-it-qat-q4_0-gguf:Q4_0
# SANTA_MEMORY_LIMIT=5g
# SANTA_THREADS=4
```

```bash
docker compose --profile santa up --build -d   # first start downloads the model once (about 4.5 GB)
```

Before a pilot, have teachers try about 50 typical S1–S6 questions in English and French, and set
`SANTA_OFFLINE=true` once the model is downloaded so it never goes online again.

---

## 10. Backups and restore

The `backup` service takes a backup every day at `BACKUP_TIME` (default `02:30` in `TZ`, default
`Africa/Kigali`): a compressed `pg_dump` of the database and a tar of the uploaded files, into the `backups`
volume, keeping `BACKUP_KEEP_DAYS` days (default 14). Each dump is verified before the old ones are pruned, and
the service's health check turns unhealthy if the newest backup is more than a day old.

```ini
# in .env (optional; these are the defaults)
BACKUP_KEEP_DAYS=14
BACKUP_TIME=02:30
TZ=Africa/Kigali
```

Take one now, and list what is there:

```bash
docker compose exec backup iga-backup
docker compose exec backup ls -lh /backups/db /backups/media
```

**Copy the backups off the server.** A backup in the same volume as the database does not survive the server
dying. Copy the `backups` volume to a second location (another machine, object storage), **encrypted**, on a
schedule. The dumps hold personal data; keep `FIELD_ENCRYPTION_KEYS` somewhere else, or the encrypted columns
cannot be read after a restore. For example, to pull the latest dump to your laptop:

```bash
dir=$(docker compose exec -T backup sh -c 'ls -1t /backups/db/iga-*.dump | head -1')
docker compose cp "backup:$dir" ./       # then encrypt and store it off-site
```

### Restore

Restoring **replaces** the database. Stop the app first, restore, then start again; the `migrate` service
re-applies the roles and any newer migrations on start.

```bash
docker compose stop backend scheduler web
# Database:
docker compose run --rm backup iga-restore /backups/db/iga-YYYYMMDD-HHMMSS.dump
# Uploaded files too, if you are restoring those:
docker compose run --rm backup iga-restore --media /backups/media/media-YYYYMMDD-HHMMSS.tar.gz
docker compose up -d
```

If the backups are off-site, copy the files back into the `backups` volume first
(`docker compose cp ./iga-...dump backup:/backups/db/`). After restoring money data, check the ledger is
intact: `docker compose exec backend python manage.py verify_ledger`.

**Practise a restore** into a throwaway environment before you need one. This exact cycle (dump, then restore
into a fresh PostgreSQL 16) is tested in development, and data, sequences and the append-only ledger all come
back.

---

## 11. Monitoring and maintenance

**Health check.** `GET https://iga.example.rw/api/health/` returns `{"status": "ok"}` and HTTP 200 only when
Django can reach the database. Point your uptime monitor at it. It stays answerable during maintenance mode.

**Logs.** `docker compose logs -f backend` (and `web`, `scheduler`, `backup`). Security events — sign-ins and
failures, lockouts, password and 2FA changes, step-ups, refused requests, cross-site refusals — are JSON lines
on the backend's output (logger `iga.security`) and in **Admin -> Audit** (which can show only security events).
Ship the logs somewhere durable so they survive a container restart.

**Service health.** `docker compose ps` shows each service's health. The `backup` service reads `unhealthy`
when backups stop; the `db`, `coderunner` and `santa` services have their own checks.

**Background jobs.** The `scheduler` service runs every 10 minutes: it reconciles open payments, sends due
subscription reminders, and runs `privacy_cleanup` (which erases accounts whose 14-day deletion grace is over
and deletes records past their retention period). No cron to set up.

**Maintenance mode.** To take the app down gently for an upgrade — a "back soon" page (HTTP 503) for everyone
except the Iga team — without a restart:

```bash
docker compose exec backend python manage.py maintenance on
# ... do the work ...
docker compose exec backend python manage.py maintenance off
```

Django then refuses the API to everyone but platform admins, and nginx shows the "back soon" page for the app,
except at `/team`, where the team signs in. (You can also set `MAINTENANCE_MODE=true` and restart.)

---

## 12. Updating

```bash
git pull
docker compose pull            # newer base images (database, Redis, Santa's server)
docker compose up --build -d   # rebuilds and restarts; migrate re-applies any new migrations first
```

Consider `maintenance on` first for a change that touches the database. Take a backup before a big upgrade
(`docker compose exec backup iga-backup`). Check for upgrades regularly: CI scans dependencies and images for
known vulnerabilities, and Dependabot proposes updates.

---

## Launch checklist

- [ ] Fresh random secrets for every value in [§2](#2-generate-the-secrets); `FIELD_ENCRYPTION_KEYS` and
      `LEDGER_HMAC_KEY` stored safely and apart from the backups.
- [ ] `HTTPS=false` removed; the site loads over HTTPS and `check --deploy` is clean.
- [ ] `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and `FRONTEND_URL` set to the real domain.
- [ ] SMTP works: a password reset and a contact-form message both arrive.
- [ ] Terms and Privacy Policy reviewed by a lawyer; `LEGAL_DRAFT_NOTICE=false`; entity, address and privacy
      contact set; data hosted in Rwanda (or an NCSA authorisation held).
- [ ] Curriculum loaded; the first platform admin created, with 2FA on; no demo accounts.
- [ ] Payments configured and tested, or bank transfers only ([SUBSCRIPTIONS.md](SUBSCRIPTIONS.md)).
- [ ] A backup has run, is being copied off-site encrypted, and a restore has been practised.
- [ ] An uptime monitor watches `/api/health/`; logs are shipped somewhere durable.
