# Architecture

## Overview

```
             Phones, tablets, school computers (browser or installed PWA)
                                   │  HTTPS
                                   ▼
        ┌─────────────────────────────────────────────────────┐
        │ nginx: serves the built React app (hashed assets,   │
        │ cached forever), proxies /api /django-admin /static │
        │ to Django, serves uploaded /media from a volume     │
        └───────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────▼────────────────┐       ┌──────────────┐
        │ Django + DRF on gunicorn       │──────▶│ Redis        │ shared rate limits
        │ (stateless; scale horizontally)│       └──────────────┘ (cache)
        └───────┬───────────────┬────────┘
                │               │
        ┌───────▼──────┐  ┌─────▼──────────────────────┐
        │ PostgreSQL   │  │ Media storage               │ textbooks, papers,
        │ (all data)   │  │ (volume today; S3/GCS later)│ uploaded resources
        └──────────────┘  └─────────────────────────────┘

   Third-party, loaded only when a student taps "Launch":
   phet.colorado.edu (iframes)   geogebra.org (deployggb.js)
```

- **Frontend:** React 19 + React Router, built with Vite. Pages are code-split, so the first load is about 95 KB gzipped. KaTeX and the Markdown pipeline load only with lesson pages.
- **Backend:** Django 5.2 LTS + Django REST Framework. It's a modular monolith: one Django app per domain, each with its own models, services and API. The vision's "auto-marking service" is the `assessments/services.py` module. It can be split into its own service later without changing the API.
- **Database:** PostgreSQL in production; SQLite for local development and quick tests. The test suite passes on both.
- **Content as files:** lessons, quizzes and papers live in `backend/content/` and are imported idempotently. Teachers can also author in the app; that content goes through admin review.

## Backend apps

| App | Responsibility | Key models |
|---|---|---|
| `accounts` | Users and roles (student, teacher, admin), registration, JWT login, refresh cookie, TOTP 2FA, per-account login throttle | `User` |
| `curriculum` | Subjects (names in en/rw/sw), units per grade, lessons (Markdown) with translations, resources, completion tracking | `Subject`, `Unit`, `Lesson`, `LessonTranslation`, `Resource`, `LessonProgress` |
| `simulations` | Lab catalogue; builds PhET/GeoGebra embed URLs with the right locale | `Simulation`, `SimulationView` |
| `assessments` | Question bank, quizzes, exam papers, attempts, scoring, teacher marking | `Question`, `Choice`, `Quiz`, `QuizQuestion`, `ExamPaper`, `Attempt`, `Answer` |
| `classroom` | Classes with join codes, enrolment, assignments, gradebook | `Classroom`, `Enrollment`, `Assignment` |
| `community` | Study groups, chat, shared notes, reports | `StudyGroup`, `GroupMembership`, `Message`, `SharedNote`, `MessageReport` |
| `gamification` | XP ledger, streaks, badges, leaderboards | `XPEvent`, `Badge`, `UserBadge` |
| `core` | Constants, permissions, audit log, dashboard, search, admin API, content loader and management commands | `AuditLog` |

### Data model (simplified)

```
Subject ─< Unit (grade S1–S6, number) ─< Lesson ─< LessonTranslation (rw, sw)
   │          │                           │ >─< Simulation
   │          │                           └─< LessonProgress >─ User
   │          └─< Question ─< Choice
   └─< Quiz >─< Question (ordered, via QuizQuestion)
         ├── ExamPaper (level, year, official?, PDF, marking guide)  [optional 1:1]
         └─< Attempt (user, question_order, choice_order, deadline, score) ─< Answer

User (role) ─< Classroom (teacher) ─< Enrollment >─ User (student)
                   └─< Assignment → Quiz | Lesson | Simulation
User ─< GroupMembership >─ StudyGroup ─< Message ─< MessageReport
User ─< XPEvent    User ─< UserBadge >─ Badge    User ─< AuditLog (actor)
```

## The assessment engine

The integrity rules live in `apps/assessments/services.py`:

1. **No answer leaks.** The attempt payload never contains `is_correct`, numeric answers or accepted answers until the attempt is submitted. In practice mode, solutions appear only for questions the student has already checked.
2. **Shuffling.** Question order and option order are randomised per attempt with `SystemRandom`. Both are stored on the attempt, so a refresh shows the same order.
3. **Server-side timing.** `deadline = started_at + time_limit`. Any answer after `deadline + EXAM_SUBMIT_GRACE_SECONDS` triggers an automatic submit. Opening an expired attempt also closes it. The browser countdown corrects for a wrong phone clock using the server's time.
4. **Locked checks.** In practice mode, once a student checks an answer it can't be changed, so practice scores stay meaningful.
5. **Scoring.** MCQ and true/false are all-or-nothing. Multi-select gives partial credit, `(right − wrong) / total right`, never below zero. Numeric answers allow an absolute tolerance. Short answers ignore case, extra spaces and a trailing full stop. Essays, and short answers with no accepted list, go to the teacher.
6. **Teacher marking.** A teacher can mark only students enrolled in one of their classes. The attempt becomes `marked` once every answer has marks, and XP is awarded then.
7. **Exactly-once rewards.** XP events carry a unique `reference` (e.g. `attempt:42`), so re-submitting or racing requests can't award XP twice.

## API

All endpoints are under `/api/`. Lists are paginated where large (`?page=`). Everything except `auth/register`, `auth/login`, `auth/refresh`, `health` and `meta` requires a `Bearer` access token.

| Endpoint | Who | Purpose |
|---|---|---|
| `POST auth/register/`, `auth/login/`, `auth/refresh/`, `auth/logout/` | anyone | Session lifecycle (refresh token in httpOnly cookie) |
| `GET/PATCH auth/me/`, `POST auth/password/`, `auth/2fa/{setup,enable,disable}/` | user | Profile and security |
| `GET subjects/?grade=` · `GET subjects/{code}/?grade=&lang=` | user | Subjects with progress; units and lessons |
| `GET units/?subject=&grade=` | user | Unit picker for authoring |
| `GET lessons/{slug}/?lang=` · `POST lessons/{slug}/complete/` | user | Lesson with sims, resources, quizzes, prev/next |
| `POST/PATCH lessons/` | teacher | Author lessons (non-admins → review) |
| `GET/POST resources/` | user / teacher | Textbooks, guides, notes, links |
| `GET simulations/?subject=&grade=&q=` · `POST simulations/{slug}/view/` | user | Lab library |
| `GET/POST questions/` | teacher | Question bank (contains answers, so never for students) |
| `GET quizzes/` · `POST quizzes/{id}/start/` | user | Quiz library; start or resume an attempt |
| `POST/PATCH quizzes/` | teacher | Quiz builder |
| `GET exam-papers/?level=&year=&subject=` · `GET exam-papers/years/` | user | Past-paper library |
| `GET attempts/{id}/` · `POST attempts/{id}/{answer,check,submit}/` | owner | Taking a quiz |
| `GET marking/` · `POST marking/{answer_id}/mark/` | teacher | Marking queue |
| `GET/POST classes/` · `POST classes/join/` · `GET classes/{id}/report/` | user / teacher | Classes and gradebook |
| `GET/POST assignments/` | user / teacher | Assignments with each student's status |
| `GET/POST groups/` · `POST groups/{id}/join/` · `GET/POST groups/{id}/messages/?after=` · `GET/POST groups/{id}/notes/` | user | Study groups |
| `POST messages/{id}/report/` · `POST messages/{id}/hide/` | member / moderator | Moderation |
| `GET dashboard/` · `GET search/?q=` · `GET leaderboard/` · `GET badges/` | user | Home screen, search, motivation |
| `GET admin/stats/` · `admin/users/` · `admin/review/` · `admin/moderation/` · `admin/audit/` | admin | Administration |

## Security and privacy

| Concern | Measure |
|---|---|
| Passwords | Django's PBKDF2 hashing, password-strength validators |
| Sessions | 15-minute access token held in memory (never in `localStorage`); 14-day rotating refresh token in an `httpOnly`, `SameSite=Lax`, path-scoped cookie |
| Second factor | Optional TOTP (any authenticator app); recommended for teachers and admins |
| Brute force | 10 login attempts/min **per account**; per-IP limits are generous because whole schools share one public IP; shared through Redis across processes |
| Authorisation | Role checks on every endpoint; teachers see only students enrolled in their classes; students never reach the question bank; teacher self-registration needs admin approval |
| Content injection | Markdown is rendered without raw HTML; code-playground previews run in a sandboxed iframe |
| Minors' safety | No direct messages, only group chat; reporting and hiding; teacher badge on teacher messages; leaderboards show first name + initial |
| Accountability | `AuditLog` records content changes, approvals, marks, role changes and moderation, with actor and IP |
| Transport | HTTPS enforced (redirect, HSTS, secure cookies) when `HTTPS` is on, which is the default in production |

Still to do: a Content-Security-Policy that fits the GeoGebra loader, a formal data-protection review against Rwanda's Law N° 058/2021 on personal data, retention rules, and parental-consent flows for younger students. See the [roadmap](ROADMAP.md).

## Performance and scaling

- **Stateless API.** Add gunicorn workers or containers behind the load balancer as load grows. Sessions live in tokens, not server memory.
- **Database.** Indexed lookups on grade, status and timestamps. Hot reads (subjects, lessons, sims) are cache-friendly and can move to read replicas. `CONN_MAX_AGE` keeps connections alive.
- **Static content.** Hashed assets are cached forever by nginx/CDN. The service worker caches lessons a student has opened, so revision works offline.
- **Heavy media.** PhET and GeoGebra load only on demand. Videos are links, not autoplay.
- **Exam weeks.** Before a national-exam revision peak, load-test the attempt endpoints (`start`, `answer`, `submit`), which do the most writes, with Locust or k6, and size the database and workers from the results.
- **Real-time.** Chat polls every 4 s, and only while the tab is visible. Move to WebSockets (Django Channels) if groups become busy.
