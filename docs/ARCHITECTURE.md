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

   Called by the server only, when an API key is configured:
   Claude API (AI tutor and Ask AI)

   Called by the server only, when CODE_RUNNER_URL is set:
   Piston code runner (compiles and runs C++ and Java in a sandbox; reachable only from Django)
```

- **Frontend:** React 19 + React Router, built with Vite. Pages are code-split, so the first load is about 95 KB gzipped. KaTeX and the Markdown pipeline load only with lesson pages.
- **Backend:** Django 5.2 LTS + Django REST Framework. It's a modular monolith: one Django app per domain, each with its own models, services and API. The vision's "auto-marking service" is the `assessments/services.py` module. It can be split into its own service later without changing the API.
- **Database:** PostgreSQL in production; SQLite for local development and quick tests. The test suite passes on both.
- **Content as files:** lessons, quizzes and papers live in `backend/content/` and are imported idempotently. Teachers can also author in the app; that content goes through admin review.

## Backend apps

| App | Responsibility | Key models |
|---|---|---|
| `accounts` | Users and roles (student, teacher, parent, admin), registration, JWT login, refresh cookie with rotation and revocation, TOTP 2FA, per-account login throttle, parent links | `User`, `ParentInvite`, `ParentLink` |
| `curriculum` | Subjects and units (English and French names), lessons (Markdown) with French translations and a free/premium flag, resources, completion tracking | `Subject`, `Unit`, `Lesson`, `LessonTranslation`, `Resource`, `LessonProgress` |
| `simulations` | Lab catalogue; builds PhET/GeoGebra embed URLs with the right locale | `Simulation`, `SimulationView` |
| `assessments` | Question bank, quizzes, exam papers, attempts, scoring, teacher marking | `Question`, `Choice`, `Quiz`, `QuizQuestion`, `ExamPaper`, `Attempt`, `Answer` |
| `classroom` | Classes with join codes, enrolment, CSV roster import and password resets, assignments, gradebook | `Classroom`, `Enrollment`, `Assignment` |
| `community` | Study groups, chat, shared notes, reports | `StudyGroup`, `GroupMembership`, `Message`, `SharedNote`, `MessageReport` |
| `gamification` | XP ledger, streaks, badges, leaderboards | `XPEvent`, `Badge`, `UserBadge` |
| `schools` | Schools (verification, join code, paid-through date), memberships, payments (Flutterwave, manual, test), reminders, and the single access rule every content endpoint uses | `School`, `Payment`, `BillingReminder` |
| `tutor` | AI study tutor and the Ask AI page: builds the context the model may see (lesson, chosen subject, or a question once its solution is visible), switches itself off while the student sits a timed test, calls the Claude API, logs exchanges | `TutorExchange` |
| `coderun` | C++ and Java for the code playground: checks the request, sends the program to the Piston code runner, turns its result into a verdict (compile error, time limit, …). Stores nothing | – |
| `core` | Constants, permissions, audit log, dashboard, search, admin API, content loader and management commands | `AuditLog` |

### Data model (simplified)

```
Subject ─< Unit (grade S1–S6, number) ─< Lesson ─< LessonTranslation (fr)
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
User (parent) ─< ParentLink >─ User (student)    User ─< TutorExchange
School ─< User (school, school_status)    School ─< Payment    School ─< BillingReminder
```

## Schools and the paywall

One function, `apps/schools/access.content_access(user)`, decides whether someone has premium access: platform admins always; students, teachers and school administrators when their membership is approved and their school is verified with an active subscription (`paid_until` plus a grace period). Everything else on the platform stays open. The rule is enforced on the server at every place premium value leaves it:

| Surface | Locked behaviour |
|---|---|
| Lesson lists and detail | Title and summary with `locked: true`; no body or translated body; "complete" refused |
| Quizzes | Listed with `locked: true`; `start` refused (an assignment never grants access); an attempt left open when access ends is closed on the next request |
| Attempt results | Score and answers stay; explanations and marking guides withheld |
| Past papers | Links withheld; uploaded files only through signed 10-minute links that re-check access (nginx `X-Accel-Redirect` from an internal location; `/media/exam_papers/` is not served) |
| Question bank | Library questions hidden from teachers without access, and can't be put in their quizzes |
| AI tutor, search, dashboard | Tutor refused; locked lesson text not searchable; "continue learning" suggests lessons the student can open |

Payments are applied by `billing.apply_payment` inside a transaction that locks the payment and school rows, so a redirect, a webhook retry and an administrator can't extend a subscription twice. See [School subscriptions](SUBSCRIPTIONS.md).

## The assessment engine

The integrity rules live in `apps/assessments/services.py`:

1. **No answer leaks.** The attempt payload never contains `is_correct`, numeric answers or accepted answers until the attempt is submitted. In practice mode, solutions appear only for questions the student has already checked.
2. **Shuffling.** Question order and option order are randomised per attempt with `SystemRandom`. Both are stored on the attempt, so a refresh shows the same order.
3. **Server-side timing.** `deadline = started_at + time_limit`. Any answer after `deadline + EXAM_SUBMIT_GRACE_SECONDS` triggers an automatic submit. Opening an expired attempt (or a teacher's gradebook) also closes it. The browser countdown corrects for a wrong phone clock using the server's time and then runs on the monotonic clock, so changing the phone's time can't end an exam early.
4. **Locked checks.** In practice mode, once a student checks an answer it can't be changed, so practice scores stay meaningful.
5. **No races.** Starting is serialised per student and the database allows one open attempt per quiz; saves, checks and marks lock the attempt row, so nothing lands after the submit that scored it. In the browser, saves for a question go one at a time, failed saves are retried, and submit waits for them.
6. **Stable answer keys.** Once anyone has answered a question, its answer key can't be edited (wording can), and a quiz's questions can't change after attempts start.
7. **Scoring.** MCQ and true/false are all-or-nothing. Multi-select gives partial credit, `(right − wrong) / total right`, never below zero. Numeric answers allow an absolute tolerance (plus a tiny relative allowance for floating-point noise). Short answers ignore case, extra spaces and a trailing full stop. Essays, and short answers with no accepted list, go to the teacher.
8. **Teacher marking.** A teacher marks written answers only for their current classes: work set as one of their assignments, or a student's self-practice in that class's subject. Auto-marked questions can't be re-marked. The attempt becomes `marked` once every answer has marks, and XP is awarded then.
9. **Exactly-once rewards.** XP events carry a unique `reference` (`quiz:42`, `quiz-perfect:42`), so quiz XP is earned once per quiz however often it is retaken, and racing requests can't award it twice. Blank attempts earn nothing.

## API

All endpoints are under `/api/`. Lists are paginated where large (`?page=`). Everything except `auth/register`, `auth/login`, `auth/refresh`, `health` and `meta` requires a `Bearer` access token.

| Endpoint | Who | Purpose |
|---|---|---|
| `POST auth/register/`, `auth/login/`, `auth/refresh/`, `auth/logout/` | anyone | Session lifecycle (refresh token in httpOnly cookie) |
| `GET/PATCH auth/me/`, `POST auth/password/`, `auth/2fa/{setup,enable,disable}/` | user | Profile and security |
| `POST auth/parent-code/` · `GET auth/parents/` · `DELETE auth/parents/{id}/` | student | Share progress with a parent, or unlink |
| `GET/POST children/` · `GET/DELETE children/{id}/` | parent | Link with a code; read-only progress report |
| `GET subjects/?grade=` · `GET subjects/{code}/?grade=&lang=` | user | Subjects with progress; units and lessons |
| `GET units/?subject=&grade=` | user | Unit picker for authoring |
| `GET lessons/{slug}/?lang=` · `POST lessons/{slug}/complete/` | user | Lesson with sims, resources, quizzes, prev/next |
| `POST/PATCH lessons/` | teacher | Author lessons (non-admins → review) |
| `GET/POST resources/` | user / teacher | Textbooks, guides, notes, links |
| `GET simulations/?subject=&grade=&q=` · `POST simulations/{slug}/view/` | user | Lab library |
| `GET/POST questions/` | teacher | Question bank (contains answers, so never for students) |
| `GET quizzes/` · `POST quizzes/{id}/start/` | user | Quiz library; start or resume an attempt |
| `GET quizzes/{id}/analytics/?classroom=` | teacher | Results analysis: histogram, per-question difficulty, discrimination, option counts |
| `POST/PATCH quizzes/` | teacher | Quiz builder |
| `GET exam-papers/?level=&year=&subject=` · `GET exam-papers/years/` | user | Past-paper library |
| `GET attempts/{id}/` · `POST attempts/{id}/{answer,check,submit}/` | owner | Taking a quiz |
| `GET marking/` · `POST marking/{answer_id}/mark/` | teacher | Marking queue |
| `GET/POST classes/` · `POST classes/join/` · `GET classes/{id}/report/` | user / teacher | Classes and gradebook |
| `POST classes/{id}/import_roster/` · `POST classes/{id}/reset_password/` | teacher | Create student accounts from CSV (preview, then confirm); temporary passwords |
| `GET/POST assignments/` | user / teacher | Assignments with each student's status |
| `GET/POST groups/` · `POST groups/{id}/join/` · `GET/POST groups/{id}/messages/?after=` · `GET/POST groups/{id}/notes/` | user | Study groups |
| `POST messages/{id}/report/` · `POST messages/{id}/hide/` | member / moderator | Moderation |
| `GET dashboard/` · `GET search/?q=` · `GET leaderboard/` · `GET badges/` | user | Home screen, search, motivation |
| `GET code/status/` · `POST code/run/` | user | C++ and Java runs for the playground, sent to the Piston code runner (one run per student at a time, `CODE_RUNNER_MAX_RUNNING` site-wide, `THROTTLE_CODE_RUN`); 503 when it is off, busy or not answering |
| `GET tutor/status/` · `POST tutor/ask/` | user | AI tutor: from a lesson or question, or the Ask AI page with an optional `subject`; off everywhere while the student has a timed test or exam running; needs the school subscription |
| `GET schools/?q=&district=` · `GET schools/districts/` | anyone | Verified school directory for the sign-up picker |
| `GET/POST/DELETE my-school/` | user | See, choose (optionally with the school code) or leave a school |
| `GET/PATCH school/` · `GET school/members/` · `POST school/members/decide/` · `POST school/members/{id}/remove/` · `POST school/new-code/` · `GET school/payments/` | school admin | Manage the school |
| `POST billing/checkout/` · `GET billing/payments/{ref}/` · `POST billing/payments/{ref}/confirm/` | school admin | Pay and confirm |
| `POST billing/webhooks/flutterwave/` | Flutterwave | Payment notifications (secret hash checked, then verified with the API) |
| `GET admin/schools/` · `GET/PATCH admin/schools/{id}/` · `POST admin/schools/{id}/{verify,suspend,reinstate}/` · `POST admin/schools/{id}/payments/` · `GET/POST admin/schools/{id}/members/` | admin | Run schools and record payments |
| `GET admin/stats/` · `admin/users/` · `admin/review/` · `admin/moderation/` · `admin/audit/` | admin | Administration |

## Security and privacy

| Concern | Measure |
|---|---|
| Passwords | Django's PBKDF2 hashing, password-strength validators |
| Sessions | 15-minute access token held in memory (never in `localStorage`); 14-day refresh token in an `httpOnly`, `SameSite=Lax`, path-scoped cookie. Each refresh token works once; logout revokes it; a password or 2FA change ends every other session; a used token presented again (after a 30-second window for two tabs refreshing together) ends all of that user's sessions |
| Second factor | Optional TOTP (any authenticator app); each code works once. Required for the Django admin, which is off in production unless `DJANGO_ADMIN_ENABLED` |
| Brute force | 10 login attempts/min **per account**; per-IP limits are generous because whole schools share one public IP; per-user limits on guessing class, group and parent codes and on password/2FA changes; shared through Redis across processes. Client IPs only trust `X-Forwarded-For` entries from our own proxies (`TRUSTED_PROXY_COUNT`) |
| Authorisation | Role checks on every endpoint; teachers see only students enrolled in their current classes; students never reach the question bank; teacher self-registration needs admin approval; accounts with a teacher-issued temporary password can do nothing but change it |
| Content injection | Markdown is rendered without raw HTML; code-playground previews run in a sandboxed iframe; Python and SQL run in Web Workers, entirely in the browser. Uploads get random names, must be an allowed type whose bytes match the extension, and nginx serves them with `nosniff`, a sandboxing CSP, and as downloads unless they are PDFs, images or media |
| Student code | HTML/CSS/JS runs in a sandboxed iframe, Python (Pyodide) and SQL (sql.js) in Web Workers in the student's browser. C++ and Java never run on the Django server: Django sends them to a separate **Piston** code runner, which compiles and runs each program in an `isolate` sandbox with networking off, 6 s / 256 MB per run (Java 512 MB), 10 s to compile C++ (Java compiles in memory within its 6 s run), 16 KB of output and 4 jobs at a time. Piston has no authentication, so it must only be reachable from Django (Docker Compose publishes no port for it). Its container must be privileged, so in production run it on its own small machine with no secrets on it, behind a firewall that only lets the Django host in, and set `CODE_RUNNER_URL`. Each student can have one program running at a time and the whole site at most `CODE_RUNNER_MAX_RUNNING` (4, matching Piston's job limit); extra runs are refused at once ("try again in a few seconds") rather than queued, so they never hold up the web server's threads. Runs are also limited to 20 per minute per user (`THROTTLE_CODE_RUN`) |
| Minors' safety | No direct messages, only group chat; reporting and hiding; teacher badge only for approved teachers; group members, chat and leaderboards show first name + initial; parents see only their linked child, read-only; the AI tutor never sees other students' data |
| Accountability | `AuditLog` records content changes, approvals, marks, role changes and moderation, with actor and IP |
| Transport | HTTPS enforced (redirect, HSTS, secure cookies) when `HTTPS` is on, which is the default in production |

Still to do: a Content-Security-Policy that fits the GeoGebra loader, a formal data-protection review against Rwanda's Law N° 058/2021 on personal data, retention rules, and parental-consent flows for younger students. See the [roadmap](ROADMAP.md).

## Performance and scaling

- **Stateless API.** Add gunicorn workers or containers behind the load balancer as load grows. Sessions live in tokens, not server memory.
- **Database.** Indexed lookups on grade, status and timestamps. Hot reads (subjects, lessons, sims) are cache-friendly and can move to read replicas. `CONN_MAX_AGE` keeps connections alive.
- **Static content.** Hashed assets are cached forever by nginx/CDN. The service worker caches lessons a student has opened (and whole units they save), so revision works offline. Pyodide is self-hosted and cached the same way.
- **Heavy media.** PhET and GeoGebra load only on demand. Videos are links, not autoplay.
- **Exam weeks.** Before a national-exam revision peak, load-test the attempt endpoints (`start`, `answer`, `submit`), which do the most writes, with Locust or k6, and size the database and workers from the results.
- **Real-time.** Chat polls every 4 s, and only while the tab is visible. Move to WebSockets (Django Channels) if groups become busy.
