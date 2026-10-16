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
        │ Django + DRF on gunicorn       │──────►│ Redis        │ shared rate limits
        │ (stateless; scale horizontally)│       └──────────────┘ (cache)
        └───────┬───────────────┬────────┘
                │               │
        ┌───────▼──────┐  ┌─────▼──────────────────────┐
        │ PostgreSQL   │  │ Media storage               │ textbooks, papers,
        │ (all data)   │  │ (volume today; S3/GCS later)│ uploaded resources
        └──────────────┘  └─────────────────────────────┘

   Third-party, loaded only when a student taps "Launch":
   phet.colorado.edu (iframes)   geogebra.org (deployggb.js)

   Called by the server only, when SANTA_URL is set:
   Santa's model server (llama.cpp with an open model: the AI tutor; internal network, no outside AI service)

   Called by the server only, when CODE_RUNNER_URL is set:
   Iga code runner (coderunner/: compiles and runs C++ and Java; internal network, no internet)
```

- **Frontend:** React 19 + React Router, built with Vite. Pages are code-split, so the first load is about 95 KB gzipped. KaTeX and the Markdown pipeline load only with lesson pages.
- **Backend:** Django 5.2 LTS + Django REST Framework. It's a modular monolith: one Django app per domain, each with its own models, services and API. The vision's "auto-marking service" is the `assessments/services.py` module. It can be split into its own service later without changing the API.
- **Database:** PostgreSQL in production; SQLite for local development and quick tests. The test suite passes on both.
- **Content as files:** lessons, quizzes and papers live in `backend/content/` and are imported idempotently. Teachers can also author in the app; that content goes through admin review.

## Backend apps

| App | Responsibility | Key models |
|---|---|---|
| `accounts` | Users and roles (student, teacher, parent, admin), registration, JWT login, refresh cookie with rotation and revocation, session versions, TOTP 2FA, sign-in lockout, password reset by email, parent links | `User`, `PasswordResetToken`, `ParentInvite`, `ParentLink` |
| `curriculum` | Subjects and units (English and French names), lessons (Markdown) with French translations and a free/premium flag, resources, completion tracking | `Subject`, `Unit`, `Lesson`, `LessonTranslation`, `Resource`, `LessonProgress` |
| `simulations` | Lab catalogue; builds PhET/GeoGebra embed URLs with the right locale | `Simulation`, `SimulationView` |
| `assessments` | Question bank, quizzes, exam papers, attempts, scoring, teacher marking | `Question`, `Choice`, `Quiz`, `QuizQuestion`, `ExamPaper`, `Attempt`, `Answer` |
| `classroom` | Classes with join codes, enrolment, CSV roster import and password resets, assignments, gradebook | `Classroom`, `Enrollment`, `Assignment` |
| `community` | Study groups, chat, shared notes, reports | `StudyGroup`, `GroupMembership`, `Message`, `SharedNote`, `MessageReport` |
| `gamification` | XP ledger, streaks, badges, leaderboards | `XPEvent`, `Badge`, `UserBadge` |
| `schools` | Schools (verification, join code, paid-through date), memberships, payments (Flutterwave, manual, test), reminders, and the single access rule every content endpoint uses | `School`, `Payment`, `BillingReminder` |
| `tutor` | Santa, the AI tutor, in lessons, quizzes and on the Santa page: builds the context the model may see (lesson, chosen subject, or a question once its solution is visible), switches itself off while the student sits a timed test, finds matching lesson passages, runs the calculator tool, talks to Santa's model server, answers from the lessons when the model can't, logs exchanges | `TutorExchange` |
| `coderun` | C++ and Java for the code playground: checks the request, starts the program on the code runner, and passes the student's answers to a program waiting for input. Each session belongs to the student who started it. Stores nothing | – |
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
| Santa (AI tutor), search, dashboard | Santa refused; Santa never quotes locked lessons; locked lesson text not searchable; "continue learning" suggests lessons the student can open |

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

## Santa, the AI tutor

Santa's model runs on our own infrastructure: llama.cpp's `llama-server` (the `santa` Compose service, optional: it starts only with the `santa` profile, and without it the app reports the model as not installed) with an open model, Gemma 4 E4B by default. Django is its only client, on an internal Docker network, with a shared API key (`SANTA_API_KEY`); no port is published and no question goes to an outside AI service. The code is in `apps/tutor/`:

| Module | Job |
|---|---|
| `services.py` | Checks access and builds the context (the rules below), writes the fixed system prompt and the student's turn, runs up to 3 calculator rounds, falls back to lesson passages, adds the child-helpline line when a message sounds unsafe, logs the exchange |
| `retrieval.py` | BM25 over every published lesson, cut into passages at its headings, in English and French. Built in each process's memory on first use and rebuilt when a lesson, translation, unit or subject changes (a version in the shared cache) or every 15 minutes. The open lesson comes first; the student's grade and subject rank higher, lessons two or more years ahead lower; only lessons the student may read are quoted |
| `calculator.py` | The `calculate` tool: an `ast` whitelist of numbers, `+ - * / ** %`, brackets and a few maths functions, worked out with exact fractions where possible, with limits on length, size and exponents. Nothing reaches `eval` or `exec` |
| `llm.py` | The OpenAI-compatible client (`POST /v1/chat/completions`, standard library only): plain and streamed answers (`data:` chunks, `:` pings ignored, `[DONE]`), tool calls, `GET /health`, and one error per problem: not installed (no `SANTA_URL`, or its host doesn't resolve), loading (503 "Loading model"), unreachable, timeout, bad reply, tools rejected (Santa then asks again without the calculator), too long for a slot (Santa then asks again with no history and one passage) |

The rules:

1. **What Santa may see** is decided by the server, never the model: the open lesson, the chosen subject, or a quiz question with the student's answer, plus the correct answer only once the student may see it (after submitting, or after checking a practice answer). Nothing while a timed or exam-mode attempt is open anywhere.
2. **Prompt cache.** The system prompt is short and the same for every request, so llama.cpp reuses its cached prefix; everything about this question (context, lesson passages, the question) goes in the student's turn, sized to fit a 4,000-token slot with the trimmed history and the answer: a long question, quiz or history leaves less room for lesson passages, and the oldest turns go first.
3. **Limits.** One answer at a time per student, `SANTA_PARALLEL` answers at a time in all (matching `-np`), `SANTA_TIMEOUT_SECONDS` per answer including calculator rounds, `THROTTLE_TUTOR` per student.
4. **Never a dead end.** When the model is not installed, still loading, busy or not answering, Santa answers with the best matching lesson passages and a short note; the status endpoint lets the app say so up front.
5. **Streaming.** `tutor/stream/` is a `StreamingHttpResponse` (`text/event-stream`, `X-Accel-Buffering: no`); nginx does not buffer `/api/tutor/` and allows 200 s. gunicorn runs threaded workers, and each stream is bounded by the timeout. When the student presses Stop, the browser aborts the request, Django closes the connection to the model (which stops writing) and logs what was said.

## API

All endpoints are under `/api/`. Lists are paginated where large (`?page=`). Everything except `auth/register`, `auth/login`, `auth/refresh`, `auth/logout`, `auth/password-reset` (and `/confirm`), `health` and `meta` requires a `Bearer` access token.

| Endpoint | Who | Purpose |
|---|---|---|
| `POST auth/register/`, `auth/login/`, `auth/refresh/`, `auth/logout/` | anyone | Session lifecycle (refresh token in httpOnly cookie) |
| `POST auth/password-reset/` · `POST auth/password-reset/confirm/` | anyone | Email a single-use link (same answer for every name); choose a new password with it |
| `GET/PATCH auth/me/`, `POST auth/password/`, `auth/2fa/{setup,enable,disable}/`, `auth/logout-all/`, `auth/step-up/` | user | Profile (changing the email needs the password) and security; log out on every device; confirm the password (and 2FA code) before a privileged operation |
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
| `GET code/status/` · `POST code/run/` · `POST code/input/` · `POST code/stop/` | user | C++ and Java for the playground on the code runner: start a program, answer it when it waits for input, stop it (one program per student; `THROTTLE_CODE_RUN`, `THROTTLE_CODE_INPUT`); 503 when it is off, busy or not answering, 410 when the program has already finished |
| `GET tutor/status/` · `POST tutor/ask/` · `POST tutor/stream/` | user | Santa: from a lesson or question, or the Santa page with an optional `subject`. `status` says ready, loading, not installed, unavailable or exam; `ask` returns the whole answer as JSON (reply, sources, fallback, tools); `stream` sends it as Server-Sent Events while it is written. Off everywhere while the student has a timed test or exam running; needs the school subscription; `THROTTLE_TUTOR` |
| `GET schools/?q=&district=` · `GET schools/districts/` | anyone | Verified school directory for the sign-up picker |
| `GET/POST/DELETE my-school/` | user | See, choose (optionally with the school code) or leave a school |
| `GET/PATCH school/` · `GET school/members/` · `POST school/members/decide/` · `POST school/members/{id}/remove/` · `POST school/new-code/` · `GET school/payments/` | school admin | Manage the school |
| `POST billing/checkout/` · `GET billing/payments/{ref}/` · `POST billing/payments/{ref}/confirm/` | school admin | Pay and confirm |
| `POST billing/webhooks/flutterwave/` | Flutterwave | Payment notifications (secret hash checked, then verified with the API) |
| `GET admin/schools/` · `GET/PATCH admin/schools/{id}/` · `POST admin/schools/{id}/{verify,suspend,reinstate}/` · `POST admin/schools/{id}/payments/` · `GET/POST admin/schools/{id}/members/` | admin | Run schools and record payments |
| `GET admin/stats/` · `admin/users/` · `admin/review/` · `admin/moderation/` · `admin/audit/?security=1` | admin | Administration; the audit log can show only security events |

## Security and privacy

| Concern | Measure |
|---|---|
| Passwords | Argon2id (`argon2-cffi`, costs in `ARGON2_*`); older PBKDF2 hashes still work and are re-hashed at the next login. Django's validators: minimum length, common passwords, all-numeric, similarity to the username |
| Sessions | 15-minute access token held in memory (never in `localStorage`); 14-day refresh token in an `httpOnly`, `SameSite=Strict`, `Secure` (under HTTPS), path-scoped (`/api/auth/`) cookie. Each refresh token works once; logout revokes it. Every token carries the user's session version: a password change or reset (any path, the Django admin included), a 2FA change, a teacher's reset, deactivation, "Log out everywhere" or a stolen refresh token (a used one presented again after the 30-second two-tab window, signature checked) raises it, so every other session's access token stops working at once; the device that made the change gets new tokens |
| Cross-site requests | The refresh and logout endpoints (the only ones a cookie authenticates) refuse an `Origin`/`Referer` from another site on top of `SameSite`. Django's session and CSRF cookies serve only the Django admin: path `/django-admin/`, `HttpOnly`, `Secure` under HTTPS, admin sessions 8 hours |
| Second factor | Optional TOTP (any authenticator app); each code works once. Always required for staff in the Django admin, which is off unless `DJANGO_ADMIN_ENABLED` and, in production, lives only at `/django-admin/<DJANGO_ADMIN_PATH>/` (a long random secret); its sign-ins are limited per account and per address, share the app's progressive lockout, and every attempt is a security event. No demo accounts or well-known secrets in production: `seed_demo` refuses to run with `DEBUG` off, and checks `iga.E002`/`iga.E003` stop a real deployment's start while any remain |
| Brute force | Per account (the name typed) 10 sign-in attempts/min, plus a progressive lockout: 5 failures in a row (wrong password or 2FA code) for one account from one IP, 20 from anywhere, or 100 from one IP lock sign-in for 1 minute, doubling each time that day up to an hour (`LOGIN_LOCKOUT_*`). Locks are keyed on the typed text, so made-up names behave like real ones. Per-IP limits on sign-up, refresh, password reset, 2FA and password changes (generous, because whole schools share one public IP); per-account limits on refresh and reset emails; wrong current passwords and 2FA codes on profile changes and at step-up lock too; per-user limits on guessing class, group and parent codes. Shared through Redis across processes. Client IPs only trust `X-Forwarded-For` entries from our own proxies (`TRUSTED_PROXY_COUNT`) |
| Floods and client addresses | Two layers of rate limits. nginx, per client address: a strict zone for sign-in, sign-up, password reset, 2FA, step-up, password changes and the Django admin, a tight one for Santa's answers, C++/Java runs and payments, a general one for the rest of the API, and a cap on requests in progress at once (Santa's streams have their own); refusals are a JSON 429 in English or French (`NGINX_RATE_*`, `frontend/nginx/defaults.envsh`). Django, behind it: every view, signed in or not, counts against its own scope plus a per-IP (`THROTTLE_ANON`) or per-user (`THROTTLE_USER`) limit, and a test fails if a view has none. nginx alone decides who the client is: only proxies listed in `NGINX_TRUSTED_PROXIES` (for example `cloudflare`) may name it, through `CF-Connecting-IP` or `X-Forwarded-For`, and it passes exactly one address to Django, which trusts that one hop; made-up headers change nothing (`frontend/tests/nginx/test_nginx.py`). Large distributed attacks need a network in front: [CLOUDFLARE.md](CLOUDFLARE.md) |
| Slow clients and big requests | nginx drops a client that takes more than 10 s to send its headers, stalls a body or an answer for 15 s or 30 s, or leaves a keep-alive connection idle for 20 s (`NGINX_*_TIMEOUT`), and reads every request whole before Django sees it, so slow clients only ever hold nginx's cheap connections. Bodies are capped per route: 16 KB for the app itself, 64 KB for sign-in and account routes, 2 MB for the API, 25 MB only where files are uploaded (resources, the Django admin), refused with a JSON 413 (`NGINX_MAX_BODY_*`); Django refuses more than `DATA_UPLOAD_MAX_MEMORY_SIZE` (2 MB), 1,000 fields or 10 files on its own. gunicorn runs threaded workers with timeouts, worker recycling and nginx's header caps (`backend/gunicorn.conf.py`). No version number in answers. Static files are cached (a year for hashed assets, 30 days for the language runtimes) |
| Account discovery | Sign-in answers and work are the same for real and made-up names (unknown names are checked against a dummy Argon2id hash). Password reset always gives the same answer and does the lookup and email after answering. "This email is already used" answers (sign-up, profile, class roster) spend a small hourly budget per IP or account (`EMAIL_IN_USE_LIMIT`). Usernames are public (groups, leaderboards), so "username taken" is shown |
| One-time secrets | Password reset links: random 256-bit secret in the URL fragment, only its hash stored, one use, 1 hour (`PASSWORD_RESET_TIMEOUT_SECONDS`), void after a password or email change or a newer link. Parent codes: 7 days, one use, replaced by a new code, stored as keyed hashes. Refresh tokens are recorded without their signature, so the database holds no working session. Teachers' temporary passwords expire after `TEMPORARY_PASSWORD_DAYS` and allow nothing but choosing a new password |
| Encryption at rest | 2FA secrets, schools' phone numbers and payment providers' answers (they name the payer: phone, email, card digits) are encrypted in the database with Fernet under `FIELD_ENCRYPTION_KEYS` (`apps/core/encryption.py`; MultiFernet, so keys rotate with `manage.py rotate_field_encryption`); migrations encrypted the existing rows. Production refuses to start without a key, or with one that is not random. Keep the key apart from database backups: without it those values are lost |
| Authorisation | Role checks in one place (`apps/core/permissions.py`) on every endpoint; teachers see only students enrolled in their current classes, and only their work in the class subject or on their own assignments; students never reach the question bank; teacher self-registration needs admin approval; accounts with a teacher-issued temporary password can do nothing but change it. Every query is scoped to the requesting user in Django (see [Row-level access](#row-level-access)) |
| Privileged operations | Everything under `/api/admin/`, school membership and teacher decisions, new school codes, starting a payment and resetting a student's password need the right role **and** a password confirmed in the last 15 minutes (`STEP_UP_MAX_AGE_SECONDS`): at sign-in, or again at `POST /api/auth/step-up/` (with the 2FA code when it is on; wrong answers lock it for a while, as on profile changes). They are audit-logged |
| Input | Every view validates its input with serializers or explicit validators (types, lengths, ranges, ids), and a NUL character anywhere in a URL, query string or body is refused (PostgreSQL can't store one); writable serializers list the fields a client may set, so role, school, approval, XP, scores, prices, owners and dates stay server-decided. All queries go through the ORM; the few raw statements are constants with parameters (a test scans the code) |
| Database | Django connects as a role that may only read and write rows; see [Database roles](#database-roles) |
| Payments and money | Prices, plans and durations come only from the server's settings. A payment is applied only after the provider's own API confirms it (reference, status, currency, at least the amount, the school), never from a redirect or a webhook body; webhooks must be signed (secret hash or HMAC-SHA256, compared in constant time), replays are recognised, and refusals are logged and audited. Applying a payment, recording a bank transfer, a refund or a correction runs in one transaction that locks the payment and school rows, and unique constraints plus `Idempotency-Key` headers stop the same transaction, bank reference or request from counting twice. Every money event is an entry in an append-only, hash-chained ledger (a PostgreSQL trigger refuses `UPDATE`/`DELETE`; `manage.py verify_ledger` detects tampering) with gross, the provider's fee and net. A real deployment refuses to start with the test checkout or a test provider key. See [SUBSCRIPTIONS.md](SUBSCRIPTIONS.md#money-what-is-computed-and-recorded) |
| Offline copies | The PWA keeps lessons and the student's profile on the device, and its saves can be replayed, held back or edited. The server believes only the choice itself: scores, XP, marks, times and deadlines are recomputed from its own data and clock; answers to questions outside the attempt, to options of another question, or after the deadline or the submit are refused; numbers must be finite; lesson completions and quiz XP count once, and a burst of identical lab visits records one (`tests/test_offline_tampering.py`) |
| Content injection | Markdown is rendered without raw HTML; code-playground previews run in a sandboxed iframe; Python and SQL run in Web Workers, entirely in the browser. Uploads get random names, must be an allowed type whose bytes match the extension, and nginx serves them with `nosniff`, a sandboxing CSP, and as downloads unless they are PDFs, images or media |
| Student code | HTML/CSS/JS runs in a sandboxed iframe, Python (Pyodide) and SQL (sql.js) in Web Workers in the student's browser. C++ and Java never run on the Django server: Django sends them to Iga's **code runner** (`coderunner/`), a separate container on an internal network with no internet access and no published port, which only accepts requests carrying `CODE_RUNNER_TOKEN`. It has no privileges except those needed to start each program as its slot's own unprivileged user (one user per slot, so programs running at once can't see or signal each other), in a fresh folder that is deleted afterwards, with limits: 10 s of CPU and 10 s to finish or ask for input after each answer, 512 MB (C++) or a 256 MB Java heap, 32/128 processes, 8 MB files, 64 KB of output, 120 s to answer, 10 minutes per session, and 4 sessions at a time (`CODE_RUNNER_SLOTS`; the container itself is capped at 2 GB and 2 CPUs). A program waiting for input is detected from `/proc` (every thread blocked reading stdin) and paused until the student answers. Each student's requests go one at a time, and starting a new program ends the previous one |
| Minors' safety | No direct messages, only group chat; reporting and hiding; teacher badge only for approved teachers; group members, chat and leaderboards show first name + initial; parents see only their linked child, read-only; Santa never sees other students' data, and every question and answer is logged for review |
| Accountability | `AuditLog` records content changes, approvals, marks, role changes and moderation, with actor and IP. Security events (sign-ins and failures, lockouts, password and 2FA changes, step-ups, resets, refresh-token reuse, refused and throttled requests, cross-site refusals, Django admin logins) are also written to the `iga.security` logger as JSON lines, never with passwords, codes or the text typed as an unknown username; floods are deduplicated in the audit log. Admin -> Audit can show only security events |
| Transport | HTTPS enforced when `HTTPS` is on, the default in production: nginx redirects plain HTTP (Let's Encrypt's checks excepted) and sends HSTS on its answers, Django redirects, sends HSTS on the API's and marks every cookie `Secure`; one year with subdomains, `preload` only with `HSTS_PRELOAD=true`. nginx terminates TLS itself (TLS 1.2/1.3, `frontend/nginx/tls.conf.example`) or sits behind a proxy that does, whose `X-Forwarded-Proto` it believes only from `NGINX_TRUSTED_PROXIES`; Django believes nginx's only when `TRUSTED_PROXY_COUNT` > 0. `manage.py check --deploy` is clean with the production settings (`tests/test_https.py`) |
| Cross-origin access | nginx serves the app and the API from one origin, so production grants no CORS access to any other site unless `CORS_ALLOWED_ORIGINS` names it, and only on `/api/`. Origins come only from the environment and must be `scheme://host[:port]`: a wildcard, path or `null` stops the start; a real deployment refuses plain-HTTP origins (check `iga.E012`). `CSRF_TRUSTED_ORIGINS` follows the same rules (plus Django's `https://*.example.rw` form) (`tests/test_cors.py`) |

### Row-level access

The browser never talks to the database and holds no database credentials: it only calls `/api/`, and every query is made by Django on its behalf (there is no "public" database key as in Supabase-style apps). So the guarantee that PostgreSQL row-level security would give, "each user reads and writes only their own rows", is enforced where the queries are built: each view filters its queryset by the requesting user (their own attempts, drafts, notes and profile; their class's students for a teacher; their linked child for a parent; their school for a school administrator), detail, update and delete routes look the object up inside that filtered queryset (so another user's id is refused, usually as "not found"), and object-level rules (`apps/core/permissions.py`, `apps/schools/access.py`) decide the rest. `tests/test_access_matrix.py` proves it: it lists every route from Django's URL resolver and, for a student, teacher, parent and school administrator of one school and an anonymous visitor, calls each one with another school's ids in the URL, the query string and the body; nothing of the other school may be read or changed, and a new route fails the test until it is classified. `tests/test_mass_assignment.py` does the same for fields a client must not set.

We deliberately do not add PostgreSQL RLS policies: they would have to repeat the teacher, parent, school and subscription rules in SQL next to the Python ones, and the two copies would drift (one wrong policy silently hides rows or breaks a page), while Django connects as a single app role anyway. What the database does enforce is in the next section: the app's role cannot change the schema, cannot reach other databases and has no powers beyond rows.

### Database roles

`manage.py db_roles` (run with the superuser; docker compose's one-off `migrate` service does it before every start) sets up two roles with no `SUPERUSER`, `CREATEDB`, `CREATEROLE`, `REPLICATION` or `BYPASSRLS`:

- `iga_owner` owns every table, view and sequence and may create new ones; `manage.py migrate` runs as it, nothing else does.
- `iga_app`, the only role the backend and the scheduler know, may connect to the Iga database and `SELECT`, `INSERT`, `UPDATE` and `DELETE` rows (and use the id sequences); on the append-only money ledger (`schools_ledgerentry`) only `SELECT` and `INSERT`, under a trigger that refuses `UPDATE` and `DELETE` from anyone. It cannot create, alter, drop or truncate tables, create temporary tables, schemas, roles or databases, read server files or run programs, or pass its rights on. Tables created by later migrations get the same grants automatically.

Other roles on the server may not connect to the database. Passwords come from `.env` (changing them rotates them on the next start) and are sent as SCRAM-SHA-256 verifiers, never in clear text. A database from an older single-role setup is converted on the first start (its tables move to `iga_owner`). On a real deployment, `migrate` stops if Django connects as a superuser (check `iga.E004`) and warns about the other powers (`iga.W002`). `tests/test_db_roles.py` runs all of this against a real PostgreSQL server.

Still to do: a Content-Security-Policy that fits the GeoGebra loader, a formal data-protection review against Rwanda's Law N° 058/2021 on personal data, retention rules, and parental-consent flows for younger students. See the [roadmap](ROADMAP.md).

## Performance and scaling

- **Stateless API.** Add gunicorn workers or containers behind the load balancer as load grows. Sessions live in tokens, not server memory.
- **Database.** Indexed lookups on grade, status and timestamps. Hot reads (subjects, lessons, sims) are cache-friendly and can move to read replicas. `CONN_MAX_AGE` keeps connections alive.
- **Static content.** Hashed assets are cached forever by nginx/CDN. The service worker caches lessons a student has opened (and whole units they save), so revision works offline. Pyodide is self-hosted and cached the same way.
- **Heavy media.** PhET and GeoGebra load only on demand. Videos are links, not autoplay.
- **Exam weeks.** Before a national-exam revision peak, load-test the attempt endpoints (`start`, `answer`, `submit`), which do the most writes, with Locust or k6, and size the database and workers from the results.
- **Real-time.** Chat polls every 4 s, and only while the tab is visible. Move to WebSockets (Django Channels) if groups become busy.
