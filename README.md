# Iga: Rwanda's S1–S6 curriculum in one app

**Iga** (Kinyarwanda for *"learn!"*) is a learning platform for Rwandan secondary school students (Senior 1–6) and their teachers. It brings together:

- **Lessons** that follow the competence-based curriculum, with maths rendering, worked examples and live code editors
- **Virtual labs**: our own offline simulations plus PhET and GeoGebra
- **Practice quizzes** with instant feedback, and **past papers** in timed exam mode
- **Classes** where teachers set work, mark written answers and track progress
- **Study groups** with moderated chat and shared notes
- **XP, streaks, badges and leaderboards** to keep students motivated

It is mobile-first, installable as an app (PWA), works in **English, Kinyarwanda and Kiswahili**, and keeps lessons you've opened available offline.

> This repository also contains some older, unrelated files (`robot.py.4`, `crypto.py.3`, …). They are untouched.

---

## What's in Phase 1

| Area | What works today |
|---|---|
| **Curriculum** | 15 subjects (all core O- and A-level subjects), a 352-unit S1–S6 outline, 19 complete sample lessons across maths, sciences, ICT, languages and humanities, a Kiswahili translation, and resources (with a link to the REB e-learning portal) |
| **Labs** | 4 built-in offline labs (projectile motion, function grapher, Ohm's law circuit, market equilibrium), 28 PhET simulations, 3 GeoGebra apps. Heavy sims only load when a student taps *Launch*, which saves mobile data |
| **Assessment** | 6 question types (MCQ, multi-select, true/false, numeric with tolerance, short answer, essay); practice and exam modes; server-enforced time limits; per-attempt shuffling; answers never sent before submit; partial credit; teacher marking queue; explanations and marking guides |
| **Past papers** | Library filtered by level, year and subject; PDF and marking-guide links; interactive versions. Ships with **2 clearly-labelled unofficial sample papers**. Real NESA papers go in through the importer |
| **Teachers** | Classes with readable join codes, assignments (quiz, lesson or lab) with due dates, gradebook, "hardest topics" report, question-bank and quiz builder, lesson editor with live preview, resource sharing |
| **Community** | Public and private study groups, polling chat, shared Markdown notes, message reporting, moderator hiding, an admin moderation queue |
| **Motivation** | XP ledger (never double-awarded), levels, daily streaks, 8 badges, weekly leaderboards by grade, school or class (surnames shortened for privacy) |
| **Admin** | Stats dashboard, teacher approval, content review (teacher content needs approval before it goes public), audit log, full Django admin |
| **Security** | Short-lived JWT access token kept in memory, rotating refresh token in an httpOnly cookie, optional TOTP 2FA, per-account login throttling, role-based access everywhere, audit trail |

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
| `admin` | Admin | Also has the Django admin at `/django-admin/` |

To load only the curriculum (no demo users), for example on a pilot server, run `python manage.py load_curriculum`.

## Running the tests

```bash
cd backend && pytest                 # 91 API tests (SQLite by default; set DATABASE_URL to test on PostgreSQL)
cd backend && ruff check .           # lint
cd frontend && npm test              # unit tests for the lab maths
cd frontend && npm run lint
cd frontend && npx playwright test   # 9 end-to-end journeys × (mobile + desktop) against the real API
```

The Playwright run starts its own Django server (fresh database with demo data) and Vite dev server. CI (`.github/workflows/ci.yml`) runs everything, including the backend suite against PostgreSQL 16.

## Production-like run with Docker

```bash
docker compose up --build
docker compose exec backend python manage.py load_curriculum
docker compose exec backend python manage.py seed_demo --force   # optional demo accounts
# open http://localhost:8080
```

This runs PostgreSQL 16, Redis (shared rate limits), Django on gunicorn, and nginx serving the built app. For a real deployment, put it behind HTTPS, set a long random `DJANGO_SECRET_KEY`, and leave `HTTPS` unset (it defaults to on). See [`backend/.env.example`](backend/.env.example) for every setting.

## Repository layout

```
backend/                 Django + Django REST Framework API
  apps/accounts          users, roles, JWT auth, 2FA, per-account login throttle
  apps/curriculum        subjects, units, lessons (+ translations), resources, progress
  apps/simulations       lab catalogue and embed URLs
  apps/assessments       question bank, quizzes, exam papers, attempts, marking
  apps/classroom         classes, enrolment, assignments, reports
  apps/community         study groups, chat, notes, reports
  apps/gamification      XP ledger, streaks, badges, leaderboards
  apps/core              shared constants, permissions, audit log, dashboard, admin API, content loader
  content/               curriculum content as files (JSON + Markdown), loaded by `load_curriculum`
  tests/                 pytest suite
frontend/                React 19 + Vite single-page app (PWA)
  src/pages              one file per screen
  src/sims               built-in offline labs and their maths
  src/i18n               en / rw / sw interface strings
  tests/e2e              Playwright journeys
docs/                    architecture, content guide, roadmap
docker-compose.yml       PostgreSQL + Redis + backend + nginx
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md): components, data model, API, security and scaling
- [Content guide](docs/CONTENT_GUIDE.md): how teachers and editors add lessons, translations, quizzes and exam papers
- [Roadmap](docs/ROADMAP.md): what's done, what's next, and the decisions still to make

## Important notes on content

- **Curriculum alignment.** Unit titles follow the usual progression of the Rwandan competence-based curriculum, but they **have not yet been checked line by line against the official REB syllabi**. Every unit is flagged `alignment_verified = false` and the app shows a "draft outline" notice until a teacher verifies it.
- **Past papers.** The two bundled papers are **unofficial practice papers** written for this project and are labelled as such everywhere. Official national exam papers belong to NESA; import them with `import_exam_paper` once you have permission to publish them.
- **Textbooks.** REB textbooks are linked from the REB e-learning portal rather than copied. Confirm redistribution rights before uploading PDFs.
- **Translations.** The Kinyarwanda and Kiswahili interface strings, and the Kiswahili lesson, are drafts. Have a fluent speaker review them before a pilot.
- **Simulations.** PhET simulations are © University of Colorado Boulder, licensed CC-BY 4.0. GeoGebra apps are loaded from geogebra.org under GeoGebra's terms.
