# Iga: Rwanda's S1–S6 curriculum in one app

**Iga** (Kinyarwanda for *"learn!"*) is a learning platform for Rwandan secondary school students (Senior 1–6) and their teachers. It brings together:

- **Lessons** that follow the competence-based curriculum, with maths rendering, worked examples and live code editors (HTML/JS and Python)
- **Virtual labs**: our own offline simulations plus PhET and GeoGebra
- **Practice quizzes** with instant feedback, and **past papers** in timed exam mode
- **An AI study tutor** (Claude) that explains lessons and gives hints without handing out answers
- **Classes** where teachers set work, mark written answers, analyse results and track progress
- **Parent access** so a guardian can follow a child's progress
- **Study groups** with moderated chat and shared notes
- **XP, streaks, badges and leaderboards** to keep students motivated

It is mobile-first, installable as an app (PWA), works in **English and French**, and whole units can be saved for offline study.

**Schools pay, students learn.** Students and teachers choose their school; the school administrator pays one monthly subscription (USD 200 by default) and every approved member of that school gets the full library. Members of schools that haven't subscribed get the free starter lessons. See [School subscriptions](docs/SUBSCRIPTIONS.md).

> This repository also contains some older, unrelated files (`robot.py.4`, `crypto.py.3`, …). They are untouched.

---

## What's in Phase 1

| Area | What works today |
|---|---|
| **Curriculum** | 15 subjects (all core O- and A-level subjects), a 352-unit S1–S6 outline, 39 complete lessons (each with a practice quiz) across maths, sciences, ICT, languages and humanities, all 39 also in French, French unit titles, and resources (with a link to the REB e-learning portal) |
| **Labs** | 4 built-in offline labs (projectile motion, function grapher, Ohm's law circuit, market equilibrium), 32 PhET simulations, 3 GeoGebra apps. Heavy sims only load when a student taps *Launch*, which saves mobile data |
| **Coding** | HTML/CSS/JS playground, and real Python in the browser (Pyodide, self-hosted, works offline) inside lessons and in the playground |
| **AI tutor** | Lesson and question help from Claude, with context the server controls: switched off during exams and timed tests, never shown answers before the student may see them, rate-limited, and off unless an Anthropic API key is configured |
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
| `kevin` | Student, S4 | |
| `teacher` | Teacher | Owns "S2 Mathematics — Stream A" |
| `parent` | Parent | Linked to Aline |
| `lkadmin` | School administrator | Lycée de Kigali (subscribed) — all students above belong to it |
| `apadeadmin`, `samuel` | School administrator, student | APADE (not subscribed): `samuel` sees locked lessons |
| `gsadmin` | School administrator | GS Remera Catholique, waiting for the Iga team to verify it |
| `admin` | Admin | Also has the Django admin at `/django-admin/` |

To load only the curriculum (no demo users), for example on a pilot server, run `python manage.py load_curriculum`.

## Running the tests

```bash
cd backend && pytest                 # 285 API tests (SQLite by default; set DATABASE_URL to test on PostgreSQL)
cd backend && ruff check .           # lint
cd frontend && npm test              # unit tests for the lab maths
cd frontend && npm run lint
cd frontend && npx playwright test   # 18 end-to-end journeys × (mobile + desktop) against the real API
```

The Playwright run starts its own Django server (fresh database with demo data) and Vite dev server. CI (`.github/workflows/ci.yml`) runs everything, including the backend suite against PostgreSQL 16.

## Production-like run with Docker

```bash
cp .env.docker.example .env
echo "DJANGO_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')" >> .env
docker compose up --build
docker compose exec backend python manage.py load_curriculum
docker compose exec backend python manage.py seed_demo --force   # optional demo accounts
# open http://localhost:8080
```

This runs PostgreSQL 16, Redis (shared rate limits), Django on gunicorn, and nginx serving the built app. The example `.env` sets `HTTPS=false` so the trial works on plain `http://localhost`. For a real deployment, put it behind HTTPS and delete that line: secure cookies, HSTS and the HTTPS redirect then switch on. The stack refuses to start without a `DJANGO_SECRET_KEY`. See [`.env.docker.example`](.env.docker.example) and [`backend/.env.example`](backend/.env.example) for every setting.

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
  apps/tutor             AI study tutor (Claude API)
  apps/schools           schools, memberships, subscriptions, payments, access rule
  apps/core              shared constants, permissions, audit log, dashboard, admin API, content loader
  content/               curriculum content as files (JSON + Markdown), loaded by `load_curriculum`
  tests/                 pytest suite
frontend/                React 19 + Vite single-page app (PWA)
  src/pages              one file per screen
  src/sims               built-in offline labs and their maths
  src/i18n               en / fr interface strings
  tests/e2e              Playwright journeys
docs/                    architecture, content guide, roadmap
docker-compose.yml       PostgreSQL + Redis + backend + nginx
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md): components, data model, API, security and scaling
- [Content guide](docs/CONTENT_GUIDE.md): how teachers and editors add lessons, translations, quizzes and exam papers
- [School subscriptions](docs/SUBSCRIPTIONS.md): how schools join and pay, what's free, setting up Flutterwave, reminders
- [Roadmap](docs/ROADMAP.md): what's done, what's next, and the decisions still to make

## Important notes on content

- **Curriculum alignment.** Unit titles follow the usual progression of the Rwandan competence-based curriculum, but they **have not yet been checked line by line against the official REB syllabi**. Every unit is flagged `alignment_verified = false` and the app shows a "draft outline" notice until a teacher verifies it.
- **Past papers.** The two bundled papers are **unofficial practice papers** written for this project and are labelled as such everywhere. Official national exam papers belong to NESA; import them with `import_exam_paper` once you have permission to publish them.
- **Textbooks.** REB textbooks are linked from the REB e-learning portal rather than copied. Confirm redistribution rights before uploading PDFs.
- **Translations.** The French interface strings, server messages and emails, unit titles, lab descriptions and lesson translations were machine-translated and checked, but not yet by a fluent teacher. Have them reviewed before a pilot (lessons carry `reviewed: false` until then). Quizzes are in English only for now. Server messages live in `backend/locale/fr/LC_MESSAGES/django.po`: after marking a new message with `_()`, run `python scripts/messages.py extract`, translate it, then `python scripts/messages.py compile` (a test fails until every message has a French translation).
- **Simulations.** PhET simulations are © University of Colorado Boulder, licensed CC-BY 4.0. GeoGebra apps are loaded from geogebra.org under GeoGebra's terms.
