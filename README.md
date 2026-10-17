# Iga: Rwanda's S1–S6 curriculum in one app

**Iga** (Kinyarwanda for *"learn!"*) is a learning platform for Rwandan secondary school students (Senior 1–6) and their teachers. It brings together:

- **Lessons** that follow the competence-based curriculum, with maths rendering, worked examples and live code editors (HTML/JS and Python)
- **Virtual labs**: our own offline simulations plus PhET and GeoGebra
- **A calculator like the Windows 11 one**: Standard, Scientific, Programmer, Graphing, Date calculation and 12 unit converters, all working offline
- **Practice quizzes** with instant feedback, and **past papers** in timed exam mode
- **Santa, Iga's own AI tutor**, which runs on the school's own server (no outside AI service): it explains ideas from Iga's lessons and links them, gives hints without handing out answers, checks arithmetic with a calculator, and has its own page for questions on any subject
- **Books on every lesson and unit**: the official REB student's book for that subject and grade, plus free open textbooks
- **Classes** where teachers set work, mark written answers, analyse results and track progress
- **Parent access** so a guardian can follow a child's progress
- **Study groups** with moderated chat and shared notes
- **XP, streaks, badges and leaderboards** to keep students motivated

It is mobile-first, installable as an app (PWA), works in **English and French**, and whole units can be saved for offline study.

**Schools pay, students learn.** Students and teachers choose their school; the school administrator pays one monthly subscription (USD 200 by default) and every approved member of that school gets the full library. Members of schools that haven't subscribed get the free starter lessons. See [School subscriptions](docs/SUBSCRIPTIONS.md).

---

## What's in Phase 1

| Area | What works today |
|---|---|
| **Curriculum** | 16 subjects (all core O- and A-level subjects, with ICT for everyone and Computer Science for the MCE and MPC combinations), a 398-unit S1–S6 outline, 42 complete lessons (each with a practice quiz) across maths, sciences, ICT, computer science, languages and humanities, all 42 also in French, French unit titles, and resources (with a link to the REB e-learning portal) |
| **Labs** | 4 built-in offline labs (projectile motion, function grapher, Ohm's law circuit, market equilibrium), 32 PhET simulations, 3 GeoGebra apps. Heavy sims only load when a student taps *Launch*, which saves mobile data |
| **Coding** | Code playground with HTML/CSS/JS, real Python (Pyodide) and SQL (SQLite via sql.js), all in the browser, self-hosted and working offline; plus **C++ and Java**, compiled and run on Iga's own sandboxed code runner. A real code editor (automatic indentation, colours, line numbers) and a terminal-style console: when a program asks for input (`input()`, `cin`, `Scanner`), the question appears and it waits for the student's answer. Python and web code also run inside lessons |
| **Calculator** | A calculator page in the style of the Windows 11 Calculator, chosen from its menu: Standard (immediate execution), Scientific (precedence, brackets, trigonometry in degrees, radians or gradians, exact decimals), Programmer (HEX/DEC/OCT/BIN, word sizes, bit operations), Graphing (several functions, pan, zoom and trace, gaps at asymptotes, its own safe parser), Date calculation, and converters for volume, length, weight, temperature, energy, area, speed, time, power, data (kB and KiB), pressure and angle with exact factors. History and memory as in Windows, keyboard shortcuts, English and French, and it works offline |
| **Santa (AI tutor)** | Iga's own learning assistant: an open model (Gemma 4 E4B by default) running with llama.cpp on the school's server, so questions never leave it. In lessons, quizzes and on the **Santa** page (pick a subject, or ask about anything you study). Answers appear as they are written, are grounded in passages from Iga's own lessons (linked under each answer), use a calculator for arithmetic, and come in English or French. The server controls the context: Santa is switched off everywhere while a student has an exam or timed test running, never sees answers before the student may, and is rate-limited. Without its model (not installed, or still starting) Santa answers with the best matching lesson passages. See [Santa](#santa-igas-own-ai-tutor) |
| **Books** | Every lesson lists the official REB student's book for its subject and grade (with the unit to look for) and free open textbooks (OpenStax, Standard Ebooks, CS Field Guide, Think Java…); units without an Iga lesson point to the textbook. Books are links, kept in `content/books.json`; `check_book_links` finds links that have moved |
| **Offline** | Save a unit for offline use (lessons, maths fonts, built-in labs); the app opens without a connection for a student who logged in before, and logging out clears the saved pages on shared computers |
| **Assessment** | 6 question types (MCQ, multi-select, true/false, numeric with tolerance, short answer, essay); practice and exam modes; server-enforced time limits; per-attempt shuffling; answers never sent before submit; partial credit; teacher marking queue; explanations and marking guides |
| **Past papers** | Library filtered by level, year and subject; PDF and marking-guide links; interactive versions. Ships with **2 clearly-labelled unofficial sample papers**. Real NESA papers go in through the importer |
| **Teachers** | Classes with readable join codes, student accounts created from a CSV list (temporary passwords, changed at first login) and password resets, assignments (quiz, lesson or lab) with due dates, gradebook, "hardest topics" report, per-quiz results analysis (score distribution, question difficulty and discrimination, option choices), question-bank and quiz builder, lesson editor with live preview, resource sharing |
| **Schools & billing** | Verified school directory; membership by school code or administrator approval; school administrators manage members, the school code and the subscription (1, 3, 6 or 12 months by card or mobile money through Flutterwave, or bank transfer recorded by the Iga team); receipts and email reminders; premium content locked for everyone else, including past-paper files served only through access-checked links |
| **Parents** | A student creates a one-time code; the linked parent sees a read-only progress report (subjects, recent scores, assignments) and can unlink at any time |
| **Community** | Public and private study groups, polling chat, shared Markdown notes, message reporting, moderator hiding, an admin moderation queue |
| **Motivation** | XP ledger (never double-awarded), levels, daily streaks, 8 badges, weekly leaderboards by grade, school or class (surnames shortened for privacy) |
| **Admin** | Stats dashboard, teacher approval, content review (teacher content needs approval before it goes public), audit log, full Django admin |
| **Security** | Short-lived JWT access token kept in memory; refresh tokens in an httpOnly cookie that rotate, are revoked on logout, password or 2FA change, and end every session if a used one is replayed; optional TOTP 2FA (single-use codes), required for the Django admin; per-account login and per-user code-guessing throttles; uploads type-checked and served so they can't run scripts; role-based access everywhere; audit trail |

## Quick start (development)

You need **Python 3.11+** and **Node 22+**.

```bash
# 1. Backend: Django API on http://127.0.0.1:8000
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py seed_demo          # loads all content + demo accounts
python manage.py runserver

# 2. Frontend: React app on http://localhost:5173 (proxies /api to Django)
cd frontend
npm install
npm run dev
```

**Demo accounts** (password `Iga-demo-2026`; development only):

| Username | Role | Notes |
|---|---|---|
| `aline`, `eric`, `divine` | Student, S2 | In the demo class, with assignments and a study group |
| `grace` | Student, S1 | |
| `kevin` | Student, S4 | MPC combination: Mathematics, Physics and Computer Science come first |
| `teacher` | Teacher | Owns "S2 Mathematics — Stream A" |
| `parent` | Parent | Linked to Aline |
| `lkadmin` | School administrator | Lycée de Kigali (subscribed) — all students above belong to it |
| `apadeadmin`, `samuel` | School administrator, student | APADE (not subscribed): `samuel` sees locked lessons |
| `gsadmin` | School administrator | GS Remera Catholique, waiting for the Iga team to verify it |
| `admin` | Admin | Also has the Django admin at `/django-admin/` |

To load only the curriculum (no demo users), for example on a pilot server, run `python manage.py load_curriculum`.

## Running the tests

```bash
cd backend && pytest                 # 429 API tests (SQLite by default; set DATABASE_URL to test on PostgreSQL)
cd backend && ruff check .           # lint
cd frontend && npm test              # 158 unit tests: calculator, lab maths, Santa's stream reader, the no-emoji guard
cd frontend && npm run lint
cd frontend && npx playwright test   # end-to-end journeys × (mobile + desktop) against the real API
python3 frontend/tests/nginx/test_nginx.py   # the nginx layer: rate limits, client addresses, sizes, HTTPS, headers (Docker)
cd frontend && npx playwright test -c playwright.docker.config.js   # the Docker stack in a browser, CSP on (below)
```

The Playwright run starts its own Django server (fresh database with demo data) and Vite dev server. The `playwright.docker.config.js` run instead uses the production build behind the real nginx on http://localhost:8080 (start the Docker stack first, with the curriculum and demo accounts loaded): it signs in, opens a lesson with maths, the labs, the Python, SQL and HTML playgrounds, Santa and the calculator, and fails on any Content-Security-Policy violation. CI (`.github/workflows/ci.yml`) runs everything, including the backend suite against PostgreSQL 16.

## Production-like run with Docker

```bash
cp .env.docker.example .env
echo "DJANGO_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')" >> .env
echo "FIELD_ENCRYPTION_KEYS=$(python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')" >> .env
docker compose up --build
docker compose exec backend python manage.py load_curriculum
docker compose exec -e DJANGO_DEBUG=true backend python manage.py seed_demo   # optional demo accounts (local trial only)
# open http://localhost:8080
```

This runs PostgreSQL 16, Redis (shared rate limits), Django on gunicorn, nginx serving the built app, Iga's code runner for C++ and Java (built from the official GCC and OpenJDK images, so the first build downloads about 700 MB once; it needs no special Docker permissions), and, when you ask for it, Santa's model server. Santa's model is optional: plain `docker compose up` starts the app without it (the app says Santa's model is not installed, and Santa answers from the lessons), so the app always starts even where the model server's image or model can't be downloaded. To run it too, start with `docker compose --profile santa up --build -d`, or put `COMPOSE_PROFILES=santa` in `.env` so every `docker compose` command includes it (its first start downloads the model once, about 4.5 GB: see [Santa](#santa-igas-own-ai-tutor)). To run without C++ and Java, add `CODE_RUNNER_URL=` to `.env` (the playground then says they are off) and start only the other services: `docker compose up --build db migrate redis backend scheduler web`. For a real deployment, set a random `CODE_RUNNER_TOKEN` and `SANTA_API_KEY` in `.env`. The example `.env` sets `HTTPS=false` so the trial works on plain `http://localhost`. For a real deployment, put it behind HTTPS and delete that line: secure cookies, HSTS and the HTTPS redirect then switch on. The stack refuses to start without a `DJANGO_SECRET_KEY` and a `FIELD_ENCRYPTION_KEYS` key (it encrypts 2FA secrets, phone numbers and payment details in the database: keep a copy apart from database backups). Before the backend starts, the one-off `migrate` service sets up the database roles with the PostgreSQL superuser and applies the migrations as `iga_owner`, the role that owns the tables; the backend and the scheduler connect as `iga_app`, which may only read and write rows (see "Database roles" in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#database-roles)). An existing database from an older version is converted on the first start. For a real deployment, set random `POSTGRES_PASSWORD`, `POSTGRES_OWNER_PASSWORD` and `POSTGRES_APP_PASSWORD` too: the local values are refused when HTTPS is on. Password reset emails need real email settings (`EMAIL_BACKEND` and friends). See [`.env.docker.example`](.env.docker.example) and [`backend/.env.example`](backend/.env.example) for every setting.

nginx limits requests per client address (strictly for sign-in and account changes, tightly for Santa, C++/Java runs and payments, generously for the rest; `NGINX_RATE_*`) and answers a flood with a JSON 429; Django adds its own limits per account and per user. Behind a load balancer or Cloudflare, tell nginx which proxies may name the client (`NGINX_TRUSTED_PROXIES`), or every student would share the proxy's address: see [docs/CLOUDFLARE.md](docs/CLOUDFLARE.md), which also covers the DDoS protection only such a network can give. `python3 frontend/tests/nginx/test_nginx.py` tests the nginx layer (needs Docker).

### Secrets

Every key and password lives in `.env` on the server (git and every image build ignore `.env` files and key files). The defaults in `docker-compose.yml` (`iga-local-...`) are public, like the examples in the docs: as soon as `DJANGO_ALLOWED_HOSTS` names a real server or HTTPS is on, Iga refuses to start with any of them, or with a short or placeholder secret, for the secret key, the database passwords, `CODE_RUNNER_TOKEN`, `SANTA_API_KEY`, the Flutterwave keys and `LEDGER_HMAC_KEY` (check `iga.E002`; `docker compose logs migrate` says which). Generate each with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. CI scans dependencies, images and every commit for known vulnerabilities and secrets (`.github/workflows/security.yml`), and Dependabot proposes upgrades.

### HTTPS

A real deployment runs over HTTPS only: leave `HTTPS=false` out of `.env` and nginx redirects plain HTTP to HTTPS and sends HSTS (a year, with subdomains), Django redirects too, marks every cookie `Secure` and sends HSTS on the API, and `manage.py check --deploy` is clean (`docker compose exec backend python manage.py check --deploy`). HSTS `preload` is a commitment for the whole domain, so it is off until you set `HSTS_PRELOAD=true`. Two ways to get the certificate:

- **Behind Cloudflare or a load balancer that terminates HTTPS:** tell nginx which proxies to trust (`NGINX_TRUSTED_PROXIES=cloudflare`, or your load balancer's addresses). nginx then believes their `X-Forwarded-Proto`, so Django knows the visitor used HTTPS; from anyone else the header is ignored. See [docs/CLOUDFLARE.md](docs/CLOUDFLARE.md).
- **nginx with your own certificate** (Let's Encrypt or Cloudflare's Origin CA): copy [`frontend/nginx/tls.conf.example`](frontend/nginx/tls.conf.example) to `tls/tls.conf`, put `fullchain.pem` and `privkey.pem` in `certs/`, and mount both with the `docker-compose.override.yml` shown in that file (it also publishes ports 80 and 443). nginx answers on 443 with TLS 1.2 and 1.3 only, and on 80 redirects everything except Let's Encrypt's checks.

## Santa, Iga's own AI tutor

Santa is Iga's learning assistant. Its "brain" is an open language model that runs on the school's (or Iga's) own server with [llama.cpp](https://github.com/ggml-org/llama.cpp): no outside AI service is called and no question leaves the server. In `docker-compose.yml` it is the `santa` service (`ghcr.io/ggml-org/llama.cpp:server-b11151`, the CPU build for amd64 and arm64), reachable only by Django on an internal network and protected by `SANTA_API_KEY`.

**How it answers.** For each question Django:

1. checks that the student may use Santa (school subscription, no exam or timed test open, rate limit) and gathers what Santa may see: the open lesson, or the quiz question (and its answer only once the student may see it), or the subject chosen on the Santa page;
2. finds the best matching passages in Iga's own lessons, in English and French (BM25 ranking over lesson sections, preferring the open lesson, the student's grade and subject, and only lessons the student may read), and links them under the answer;
3. sends a short, fixed set of instructions (so llama.cpp can reuse its prompt cache) and the question with its context to the model, which may call a `calculate` tool (a safe calculator, never `eval`) up to 3 times, and streams the answer to the student as it is written.

If the model is not installed, still starting or not answering, Santa still helps: it answers with the best matching lesson passages and says so. Every question and answer is logged (`TutorExchange`, in the Django admin) for safeguarding review.

**Hardware.** The default model, Google's Gemma 4 E4B (`google/gemma-4-E4B-it-qat-q4_0-gguf:Q4_0`, Apache-2.0), is about 4.5 GB and uses about 5-6 GB of RAM: a server with **16 GB of RAM** and 4-8 CPU cores is recommended. On such a CPU it should write roughly 8-12 tokens (pieces of words) a second, so a full answer takes 20-60 seconds (an estimate; measure yours, below). It answers 4 students at once (`-np 4`); others get a lesson-passage answer and are asked to try again in a minute. For an **8 GB server**, use the smaller Gemma 4 E2B (about 2.9 GB):

```bash
# in .env
SANTA_MODEL=google/gemma-4-E2B-it-qat-q4_0-gguf:Q4_0
SANTA_MEMORY_LIMIT=5g
SANTA_THREADS=4          # the number of physical CPU cores
```

**Switching it on.** The `santa` service belongs to the Compose profile `santa`, so it runs only when asked for: `docker compose --profile santa up -d`, or `COMPOSE_PROFILES=santa` in `.env` (then plain `docker compose up -d` includes it). Without it, Django can't find the host `santa` and the app says Santa's model is not installed; nothing else changes, and Santa answers from the lessons. Stop it again with `docker compose --profile santa stop santa`.

**First start.** `docker compose --profile santa up -d` starts the `santa` service, which downloads the model from Hugging Face once into the `santa-models` volume (about 4.5 GB; follow it with `docker compose logs -f santa`). Until it is ready, the app says "Santa is waking up" and answers from the lessons. To download from an internal mirror instead, set `MODEL_ENDPOINT` on the service; `HF_TOKEN` is only needed for gated or private models.

**Fully offline.** Once the model is downloaded, set `SANTA_OFFLINE=true` in `.env` (llama.cpp's `--offline`: it uses only the cached model and never goes online), and if you like remove the `santa-download` network from the service so it has no route to the internet at all. Alternatively, point it at the file itself: replace `-hf <model>` in the command with `-m /models/<path to the .gguf file>` (find it with `docker compose exec santa find /models -name "*.gguf"`). To install a school with no internet, download on another machine and copy the `santa-models` volume.

**Switching models.** Set `SANTA_MODEL` to another GGUF model as `<Hugging Face repo>:<quant>` and restart the service; Django needs no change (the model is always called `santa`). Options from our research, all Apache-2.0: Gemma 4 E2B (smaller, same format), IBM Granite 4.2 3B (`ibm-granite/granite-4.2-3b-GGUF:Q4_K_M`, about 2.3 GB, strong at maths) and, with a GPU or 32 GB of RAM, Gemma 4 26B-A4B (`google/gemma-4-26B-A4B-it-qat-q4_0-gguf:Q4_0`, about 14 GB). Test French answers with your teachers before switching. Check a model's licence before using it.

**GPU.** With an NVIDIA GPU, add a `docker-compose.override.yml`:

```yaml
services:
  santa:
    image: ghcr.io/ggml-org/llama.cpp:server-cuda-b11151
    environment:
      LLAMA_ARG_N_GPU_LAYERS: all
    deploy:
      resources:
        reservations:
          devices: [{ driver: nvidia, count: all, capabilities: [gpu] }]
```

(`server-vulkan-b11151` works with other GPUs.) Answers then come many times faster, and bigger models become practical.

**Measuring speed.** `docker run --rm -v <project>_santa-models:/models ghcr.io/ggml-org/llama.cpp:full-b11151 --bench -m /models/<path to the .gguf file> -p 512 -n 128 -t 4` (`docker volume ls` shows the volume's full name).

**Settings** (backend environment; defaults in brackets): `SANTA_URL` (`http://santa:8080` in Compose; empty = no model, answers from the lessons only), `SANTA_API_KEY` (shared with the model server's `LLAMA_API_KEY`), `SANTA_MODEL_NAME` (`santa`), `SANTA_MAX_TOKENS` (600), `SANTA_TEMPERATURE` (0.6), `SANTA_TIMEOUT_SECONDS` (150, calculator rounds included), `SANTA_PARALLEL` (4, match `-np`), `THROTTLE_TUTOR` (30/hour per student), `SANTA_MAX_INPUT_TOKENS` (2800, what one question may send besides the system prompt), and the allowances (0 = no limit): `SANTA_USER_DAILY_QUESTIONS` (60), `SANTA_USER_MONTHLY_QUESTIONS` (800), `SANTA_USER_DAILY_TOKENS` (250000), `SANTA_USER_MONTHLY_TOKENS` (3000000) per student, and `SANTA_SCHOOL_DAILY_TOKENS` (20000000) per school. When one is used up, Santa answers from the lessons and says so; students see what is left, platform admins the use (Admin -> Overview). In development, leave `SANTA_URL` empty, or run a model server as shown in [`backend/.env.example`](backend/.env.example).

**Honest limits.** A 2-4 billion parameter model on a school server is far less capable than the large AI models in the cloud. Santa can be wrong, sound sure when it is not, misread a question, or slip in long multi-step maths (the calculator checks arithmetic, not reasoning). Grounding in Iga's lessons helps, but only for topics the lessons cover. The app tells students that Santa can make mistakes and to check important answers in their lessons or with their teacher. Before a pilot, have teachers try about 50 typical S1-S6 questions in English and French, and review the logged exchanges now and then.

## Repository layout

```
backend/                 Django + Django REST Framework API
  apps/accounts          users, roles, JWT auth, 2FA, sessions, parent links
  apps/curriculum        subjects, units, lessons (+ translations), resources, progress
  apps/simulations       lab catalogue and embed URLs
  apps/assessments       question bank, quizzes, exam papers, attempts, marking
  apps/classroom         classes, enrolment, CSV roster import, assignments, reports
  apps/community         study groups, chat, notes, reports
  apps/gamification      XP ledger, streaks, badges, leaderboards
  apps/tutor             Santa, the AI tutor: what it may see, lesson search, calculator, model server client
  apps/coderun           C++ and Java runs for the code playground (sent to the code runner)
  apps/schools           schools, memberships, subscriptions, payments, access rule
  apps/core              shared constants, permissions, audit log, dashboard, admin API, content loader
  content/               curriculum content as files (JSON + Markdown), loaded by `load_curriculum`
  tests/                 pytest suite
coderunner/              the code runner: compiles and runs students' C++ and Java in sandboxed sessions
frontend/                React 19 + Vite single-page app (PWA)
  src/pages              one file per screen
  src/sims               built-in offline labs and their maths
  src/calculator         the Windows 11-style calculator: engine/ (plain JS maths, with tests) and its modes
  src/i18n               en / fr interface strings
  tests/e2e              Playwright journeys
docs/                    architecture, content guide, roadmap
docker-compose.yml       PostgreSQL + Redis + backend + nginx + code runner + Santa's model server
```

## Documentation

- [Deployment](docs/DEPLOYMENT.md): a step-by-step checklist to put Iga on a real server (domain, HTTPS, secrets, first admin, email, backups, monitoring)
- [Architecture](docs/ARCHITECTURE.md): components, data model, API, security and scaling
- [Content guide](docs/CONTENT_GUIDE.md): how teachers and editors add lessons, translations, quizzes and exam papers
- [School subscriptions](docs/SUBSCRIPTIONS.md): how schools join and pay, what's free, setting up Flutterwave, reminders
- [Roadmap](docs/ROADMAP.md): what's done, what's next, and the decisions still to make

## Important notes on content

- **Curriculum alignment.** Unit titles follow the usual progression of the Rwandan competence-based curriculum, but they **have not yet been checked line by line against the official REB syllabi**. Every unit is flagged `alignment_verified = false` and the app shows a "draft outline" notice until a teacher verifies it.
- **Past papers.** The two bundled papers are **unofficial practice papers** written for this project and are labelled as such everywhere. Official national exam papers belong to NESA; import them with `import_exam_paper` once you have permission to publish them.
- **Textbooks.** Every lesson and unit links the official REB student's book for its subject and grade, plus free open textbooks (`content/books.json`). Books are linked, never copied: confirm redistribution rights before uploading any PDF. REB links change when REB re-uploads a file, so run `python manage.py check_book_links` each term (see the [content guide](docs/CONTENT_GUIDE.md#books-contentbooksjson)).
- **Translations.** The French interface strings, server messages and emails, unit titles, lab descriptions and lesson translations were machine-translated and checked, but not yet by a fluent teacher. Have them reviewed before a pilot (lessons carry `reviewed: false` until then). Quizzes are in English only for now. Server messages live in `backend/locale/fr/LC_MESSAGES/django.po`: after marking a new message with `_()`, run `python scripts/messages.py extract`, translate it, then `python scripts/messages.py compile` (a test fails until every message has a French translation).
- **Simulations.** PhET simulations are © University of Colorado Boulder, licensed CC-BY 4.0. GeoGebra apps are loaded from geogebra.org under GeoGebra's terms.
