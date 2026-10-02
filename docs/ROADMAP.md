# Roadmap

## Where we are against the vision

| Vision item | Status | Notes |
|---|---|---|
| All subjects, S1–S6, matching the REB curriculum | 🟡 Structure done, content started | 15 subjects and a 352-unit outline; 19 full lessons. Units still need line-by-line checking against REB syllabi |
| Official textbooks & guides | 🟡 | Resource library with an "official" flag and a link to the REB e-learning portal. Uploading PDFs is waiting on redistribution rights |
| Simplified lessons, visuals, rich media | 🟢 | Markdown lessons with maths, tables, embedded labs and video links |
| ICT / coding modules (W3Schools-style) | 🟢 | Live HTML/CSS/JS editor in lessons and a standalone playground. Python runtime not yet built |
| English / Kinyarwanda / Kiswahili | 🟡 | Full UI framework in 3 languages, lesson translations supported. Draft rw/sw strings need native review; only 1 lesson translated |
| Interactive simulations (PhET, GeoGebra) | 🟢 | 28 PhET, 3 GeoGebra, 4 built-in offline labs, mapped to subjects and grades |
| Past national exam papers with marking guides | 🟡 Engine done | Library, timed exam mode, importer and marking guides. Needs NESA papers and permission; ships with 2 unofficial samples |
| Question bank, quizzes, instant feedback | 🟢 | 6 question types, explanations, partial credit |
| Real marks for written answers | 🟢 | Teacher marking queue with marking guide and feedback |
| Student accounts, teacher accounts, admin | 🟢 | Plus teacher approval and an audit log |
| Classes, assignments, progress tracking | 🟢 | Gradebook and "hardest topics" report |
| Study groups / clubs with moderated chat | 🟢 | Polling chat, notes, report/hide, admin queue |
| Gamification | 🟢 | XP, levels, streaks, badges, leaderboards |
| Mobile-first, dark mode, Rwanda colours | 🟢 | Installable PWA |
| Security (2FA, HTTPS, scoped access, anti-cheat) | 🟢 | See the Architecture doc for remaining hardening |
| Scalable cloud deployment | 🟡 | Stateless API, Docker, PostgreSQL, Redis. Load testing and CDN still to do |
| Testing & QA | 🟢 | 91 API tests (SQLite + PostgreSQL), unit tests, 18 E2E runs, CI |
| Parent role | ⚪ Not started | Mentioned in the summary of core features |
| AI tutor, offline sync, teacher analytics dashboards | ⚪ Phase 3 | |

## Before a pilot (next 4–8 weeks)

1. **Curriculum alignment.** Teachers check each unit against the REB syllabus PDFs, tick *alignment verified*, and add the key unit competence.
2. **Content sprint.** Prioritise S3 and S6 (exam years) in Maths, Physics, Chemistry, Biology and English. Target at least 3 lessons and 1 quiz per unit.
3. **Permissions.** Write to NESA for permission to publish past papers and marking guides, and to REB about hosting textbook PDFs. Record the reference in each paper's `source_note`.
4. **Language review.** Native speakers review the Kinyarwanda and Kiswahili UI strings (`frontend/src/i18n/`) and translate the top lessons.
5. **Privacy.** Review against Rwanda's data-protection law (Law N° 058/2021). Decide on consent for students under 16, data retention periods, and whether school email or another identifier is used at sign-up. Register with NCSA if required.
6. **Safeguarding.** Agree moderation rules with the pilot school and appoint teacher moderators per group.
7. **Hosting.** Pick a provider with low latency to Rwanda (a local data centre or the nearest cloud region), set up HTTPS, backups and monitoring (e.g. Sentry and uptime checks).
8. **Load test** the exam-week path (start, answer and submit attempts) with k6 or Locust.

## Phase 2: A-level depth, labs and groups

- Full A-level content for each combination (PCM, PCB, MCB, MEG, HEG, …), and student "combination" on the profile
- More built-in labs (titration, pendulum, genetics crosses, logic gates, sorting algorithms)
- Python in the browser for ICT (Pyodide), SQL playground
- WebSocket chat (Django Channels) and live class quizzes, Kahoot-style
- Parent accounts linked to students (read-only progress)
- Teacher analytics: item difficulty and discrimination, per-question error patterns
- Bulk import of class lists (CSV) for schools
- Accessibility audit (screen readers, colour contrast, keyboard use) and fixes

## Phase 3: Reach and intelligence

- **Offline sync:** download whole units, take quizzes offline and sync answers later
- **Low-bandwidth modes:** text-only lessons; SMS/USSD revision quizzes for feature phones
- **AI tutor** that explains a student's mistakes using the lesson and marking guide, with teacher oversight and clear limits
- **Adaptive practice** that picks questions from weak units (using the unit tags already on every question)
- Native Android app (wrapping the PWA) if app-store distribution matters for schools
- Integration with SDMS (School Data Management System) for rosters, if REB provides an API

## Yearly upkeep

- Import each year's papers after NESA releases them
- Re-check alignment when REB revises a syllabus. The `alignment_verified` flag makes outdated units easy to find
- Refresh the PhET catalogue (new sims, new Kinyarwanda translations)

## Open decisions for the team

1. **Name.** "Iga" is a working name. It's set in `APP_NAME` (backend) and a few strings in `frontend/` (`index.html`, `manifest.webmanifest`, `Layout.jsx`, `Landing.jsx`).
2. **Sign-up identity.** Username/email today. Should schools pre-create accounts for privacy and control instead?
3. **Teacher verification.** Admin approval today. Could it be automated via school email domains or an REB staff list?
4. **Hosting budget** and who operates the service after the school project ends.
