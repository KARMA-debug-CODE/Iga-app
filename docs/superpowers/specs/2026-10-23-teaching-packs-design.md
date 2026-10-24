# Teaching Packs — design

Date: 2026-10-23
Status: proposed (awaiting owner review)

## 1. Goal

Make a school's Iga subscription (USD 200/month per school, paid by the school administrator) clearly worth
paying for. Lessons and practice questions exist for free elsewhere; what does not exist elsewhere is material
built from **one school's own students**. Teaching Packs turn a class's real results into ready-to-teach
material in one click, and save teachers hours every week.

Success: from a weak unit on a class report, a teacher gets, in seconds, a pack with (1) what this class gets
wrong and why, (2) a lesson plan in the official CBC layout, pre-filled, (3) a worksheet at three levels with
a separate answer key, and (4) a targeted quiz — each printable, and the worksheet levels and quiz assignable
in Iga in one click.

## 2. Decisions taken while brainstorming

| Question | Decision |
|---|---|
| First premium lever | Teacher superpowers (exam early-warning and parent reports are later options) |
| How work reaches students | A real mix: printable and in-app are both first-class |
| Lesson plan format | Default to the official REB competence-based curriculum (CBC) layout; every field editable, so a school with its own template can copy from it |
| Generation approach | Checked content for the substance, AI only for optional polish (approach C). No AI-invented questions or facts |
| Surprise value | Misconception detection: the wrong option most of the class picks, from answers Iga already stores |
| Unpaid schools | See the weak-unit list (already free) plus a teaser count of misconceptions found; packs are locked |
| Lapsed subscription | Existing packs stay readable, editable, printable and deletable; new packs, refresh and assign are blocked |

Out of scope for this spec (later phases): schemes of work (term planning), AI-generated questions, server-side
PDF or Word export, sharing packs between teachers, head-teacher and parent dashboards, exam-result prediction.

## 3. What the teacher sees

### Entry points
- The class report (gradebook) lists the class's weakest units. Each gets **Make a teaching pack**.
- **Choose a unit** opens a picker of all the class's units for its subject and grade, weakest first.
- **My teaching packs** (teacher navigation) lists saved packs, filterable by class.

### The pack (four tabs)

**Insight — "What your class gets wrong"**
- The class's average in the unit and its averages in its other units, for comparison.
- Up to 3 misconceptions: the question, the wrong option the class picked most and the share who picked it,
  the correct answer and the explanation.
- Up to 5 hardest questions for this class.
- The students who need most help in this unit (teacher-only; computed when the tab opens, never stored).
- When there is not enough data: "Not enough answers yet" — no patterns are shown.

**Lesson plan — official CBC layout, pre-filled, every field editable**
School, teacher, term, date, subject, class, unit number, lesson number, duration, class size, learners with
special educational needs (left blank for the teacher), unit title, key unit competence, lesson title,
instructional objective, plan for the class (location), learning materials, references, and a timed table of
steps — Introduction, Development, Conclusion — each with teacher activities, learner activities, and
competences and cross-cutting issues; then evaluation and teacher self-evaluation (blank).

**Worksheet — three levels**
Support (difficulty 1), Core (difficulty 2), Stretch (difficulty 3), with a separate answer key including
marking guides. Print the student copy, print the key, or assign any level in Iga.

**Quiz — targeted**
About 10 questions aimed at what this class gets wrong, skipping what it has mastered. Assign it with a due
date, or print it with its key. With no class data, it is a **diagnostic quiz** covering the unit, labelled
"Assign this to find out what your class gets wrong".

Each pack is saved. **Refresh** builds a new pack from the latest results; the old one stays.

## 4. Architecture

### 4.1 Backend: new app `apps/teaching`

Each module has one job and is testable alone.

**`apps/classroom/analytics.py` (new, classroom-owned)** — the gradebook's weak-unit calculation moves here so
the gradebook and Teaching Packs share one implementation:

```python
def class_unit_scores(classroom) -> list[UnitScore]
    # UnitScore(unit, got: float, possible: float, average: float), every unit with marked answers by the
    # class's current students (filtered to the class subject when set), weakest first.
```

`ClassroomViewSet.report` keeps its response unchanged (`weak_units` = the 5 weakest, same label and rounding).
Dependency direction: `teaching` imports `classroom`; `classroom` never imports `teaching`.

**`apps/teaching/insight.py`** — reads the class's data for one unit; no writes:

```python
def unit_insight(classroom, unit, lang) -> dict        # averages, misconceptions, hardest questions, data_enough
def students_needing_help(classroom, unit) -> list     # computed live; not stored
def question_stats(classroom, unit) -> dict[int, QStat]
    # per question: answered (distinct students), correct_share, choice_counts, most_picked_wrong
```

Only current (active) enrollments count. Only marked attempts count, within `TEACHING_LOOKBACK_DAYS`.

**`apps/teaching/builder.py`** — pure assembly from checked content; no AI, no network:

```python
def build_pack(classroom, unit, lesson, teacher, lang) -> dict   # the pack document (section 5)
def select_worksheet(unit, stats) -> dict[str, list[Question]]   # support / core / stretch
def select_quiz(unit, stats) -> tuple[list[Question], bool]      # (questions, is_diagnostic)
def lesson_plan(classroom, unit, lesson, teacher, insight, lang) -> dict
```

**`apps/teaching/polish.py`** — the optional AI layer:

```python
def polish(document, teacher, lang) -> dict   # returns {"hook": str, "simpler": str, "ai": bool}
```

Never raises and never blocks past `TEACHING_AI_SECONDS`.

**`apps/teaching/models.py`**

```python
class TeachingPack(models.Model):
    classroom   FK Classroom, CASCADE, related_name="teaching_packs"
    unit        FK curriculum.Unit, SET_NULL, null (the document keeps the unit's label)
    lesson      FK curriculum.Lesson, SET_NULL, null
    created_by  FK User, CASCADE, related_name="teaching_packs"
    created_at  auto_now_add
    language    "en" | "fr"
    document    JSONField   # the snapshot (section 5)
    plan_edits  JSONField(default=dict)  # {field: text}, allow-listed keys only
    ai_used     bool

class PackAssignment(models.Model):
    pack        FK TeachingPack, CASCADE, related_name="assignments"
    what        "quiz" | "worksheet_support" | "worksheet_core" | "worksheet_stretch"
    quiz        FK assessments.Quiz, SET_NULL, null
    assignment  FK classroom.Assignment, SET_NULL, null
    created_at  auto_now_add
    unique (pack, what)   # assigning twice returns the existing assignment
```

**`apps/teaching/userdata.py`** — `export_for(user)` returns the user's packs (unit label, date, plan edits,
document summary); `erase_for(user)` deletes them. Quizzes and assignments they created follow the existing
rules of the assessments and classroom apps.

### 4.2 API

All under `/api/teaching/`, authenticated, throttled by the default throttles; creation also uses the scope
`teaching_pack` (`THROTTLE_TEACHING_PACK`, default `30/hour`).

| Method and path | Body | Result |
|---|---|---|
| `GET classes/{id}/units/` | – | the class's units, weakest first: unit, average, answered, misconceptions_found (count only). A class with a subject lists that subject's units for its grade; a class without a subject (the field is optional) lists every subject's units for its grade, grouped by subject |
| `POST packs/` | `{classroom, unit, lesson?}` | 201, the full pack. `lesson` must belong to `unit`; default: the unit's first published lesson |
| `GET packs/?classroom=` | – | the teacher's packs (summary fields) |
| `GET packs/{id}/` | – | the full pack: document with plan edits applied, plus `students_needing_help` computed live |
| `PATCH packs/{id}/` | `{plan: {field: text}}` | only the allow-listed plan fields (section 5.3); each cleaned with `apps/core/text.py`, at most 2,000 characters |
| `DELETE packs/{id}/` | – | 204 |
| `POST packs/{id}/assign/` | `{what, due_at?}` | 201 with the assignment, or 200 with the existing one |

There is no separate refresh endpoint: **Refresh** in the UI calls `POST packs/` again with the same unit and
lesson, which saves a new pack and leaves the old one untouched.

Permissions:
- Only the class's own teacher may use a class or its packs (the same scoping as `ClassroomViewSet`); anyone
  else gets 404. Packs are also reachable in the Django admin for platform staff.
- `POST packs/` and `POST packs/{id}/assign/` need premium: `content_access(teacher).premium`. Otherwise 403
  `{"code": "subscription_required", "teaser": {"unit", "average", "misconceptions_found"}}`. `GET`, `PATCH`
  and `DELETE` on existing packs stay available after a lapse.
- `classes/{id}/units/` is available to unpaid schools (counts only, no question content): it drives the
  teaser.

### 4.3 Frontend

- Class report: **Make a teaching pack** next to each weak unit; **Choose a unit** picker.
- `pages/TeachingPack.jsx` with four tabs: Insight · Lesson plan · Worksheet · Quiz.
- `pages/TeachingPacks.jsx`: My teaching packs.
- Lesson-plan fields edit in place and save with PATCH (debounced), with a saved/saving state.
- Assign: choose what (a worksheet level or the quiz) and an optional due date.
- Unpaid school: a teaser card with the misconception count and the subscription message (school
  administrators get a link to Subscription).
- Printing: print layouts selected with `?print=plan|worksheet|key|quiz`, then `window.print()`. `@media print`
  hides the app chrome. The student copy never contains answers; the key does. The Insight print is headed
  "Teacher only". No PDF library and no new dependency: the browser's Save as PDF covers PDFs.
- Routes in `App.jsx` (lazy-loaded), teacher navigation entry, strings in `en.js` and `fr.js`, no emojis,
  existing design and motion tokens.

## 5. The pack document

### 5.1 Shape

```json
{
  "version": 1,
  "language": "en",
  "classroom": {"id": 1, "name": "S2 B Physics", "grade": "S2", "size": 42},
  "unit": {"id": 7, "label": "S2 Unit 3: Motion", "number": 3, "title": "Motion", "key_unit_competence": "..."},
  "lesson": {"id": 31, "slug": "speed-and-velocity", "title": "Speed and velocity"},
  "insight": {
    "data_enough": true,
    "average": 41.5,
    "other_units": [{"label": "S2 Unit 2: Forces", "average": 63.0}],
    "misconceptions": [{
      "question_id": 120, "prompt": "...", "wrong_choice": "...", "share": 0.62, "answered": 37,
      "correct": "...", "explanation": "..."
    }],
    "hardest": [{"question_id": 121, "prompt": "...", "correct_share": 0.18, "answered": 35}]
  },
  "plan": { "<field>": "<text>", "steps": [{"name": "introduction", "minutes": 5,
            "teacher": "...", "learners": "...", "competences": "..."}] },
  "polish": {"hook": "...", "simpler": "...", "ai": false},
  "worksheet": {"support": [<question>], "core": [<question>], "stretch": [<question>],
                "notes": ["Only 2 stretch questions exist for this unit."]},
  "quiz": {"diagnostic": false, "questions": [<question>]},
  "generated_at": "2026-10-23T09:00:00+02:00"
}
```

`<question>` is `{id, type, prompt, choices: [{id, text, is_correct}], numeric_answer, accepted_answers,
explanation, marking_guide, marks, difficulty}`. The snapshot holds answers because it is a teacher-only
document; student-facing output (the student print, an assigned quiz) never exposes them.

### 5.2 Selection rules

- **Pattern threshold:** a question's statistics count only when at least `TEACHING_MIN_STUDENTS` (default 5)
  distinct current students answered it. `data_enough` is true when at least one question in the unit meets it.
- **Misconception:** for a choice question, the most-picked wrong option when picked by at least
  `TEACHING_MISCONCEPTION_SHARE` (default 0.3) of the students who answered. Top 3 by share, then by answered.
- **Hardest:** lowest correct share among questions meeting the threshold; top 5.
- **Mastered:** correct share at least `TEACHING_MASTERED_SHARE` (default 0.85); excluded from worksheet and quiz.
- **Eligible questions:** published, `unit` = the pack's unit.
- **Worksheet:** up to `TEACHING_WORKSHEET_PER_LEVEL` (default 5) per level, by difficulty 1/2/3. Order: questions
  behind misconceptions, then hardest, then not yet answered by the class, then the rest; ties by id. All
  question types are allowed (it may be printed). An empty or short level adds a note; nothing is backfilled
  from another level and nothing is invented.
- **Quiz:** up to `TEACHING_QUIZ_SIZE` (default 10), auto-marked types only (MCQ, multi-select, true/false,
  numeric, short answer with accepted answers), so the assignment marks itself. With data: misconception and
  hardest questions first, then the rest, excluding mastered. Without data (`data_enough` false): diagnostic —
  spread across difficulties 1, 2, 3 in turn, ties by id.
- **Students needing help:** current students with at least 3 marked answers in the unit and a unit average
  below 50%; up to 10, lowest first. Computed on read, never stored.

### 5.3 Lesson plan filling

Allow-listed editable fields: `school`, `teacher`, `term`, `date`, `lesson_number`, `duration`, `class_size`,
`sen_learners`, `unit_title`, `key_unit_competence`, `lesson_title`, `objective`, `location`, `materials`,
`references`, `steps` (each step's `teacher`, `learners`, `competences` text), `evaluation`,
`self_evaluation`.

- Pre-filled: school (the teacher's school name), teacher (display name), date (today), class size (current
  enrollments), unit title and number, key unit competence (`Unit.key_unit_competence`; left empty if blank),
  lesson title, duration (`TEACHING_PERIOD_MINUTES`, default 40), references (up to 3 published official
  textbooks: `Resource.kind == textbook`, `is_official`, matching the unit, else the subject and grade),
  objective (built from the lesson title and the unit's competence; editable).
- Steps, with timings scaled to the duration (default 5 / 25 / 10 minutes):
  - Introduction: the hook (Santa's if available, else a template that opens with the top misconception's
    question as a class vote), plus recall of the previous unit when one exists.
  - Development: up to 3 activities from the lesson's level-2 headings; each paired with a misconception to
    address explicitly (the misconception's wrong idea, the correct answer and the explanation).
  - Conclusion: a short summary and 2–3 evaluation questions from the core level.
- Learners with special educational needs, term and self-evaluation are left blank for the teacher.
- French: unit `title_fr`, the lesson's French translation and French field labels where they exist; otherwise
  English, with a note that French content is not available.

### 5.4 Santa polish

- Runs only when `tutor.llm.installed()`, Santa's cached health is not unreachable, and the teacher is within
  the tutor app's usage caps.
- One `llm.chat()` call with a deadline of `TEACHING_AI_SECONDS` (default 20). The prompt asks, in the pack
  language, for JSON `{"hook": "...", "simpler": "..."}`, each at most 80 words, plain text, using only the facts
  given. Facts sent: unit title, lesson title, the top misconception (question, wrong option, correct answer,
  explanation), each passed through `tutor.guard.neutralise()`.
- The reply is accepted only if it parses, both fields are non-empty strings within the limits, and neither
  `guard.looks_like_injection()`. Accepted text is cleaned with `apps/core/text.py` and marked
  `"ai": true` ("Suggested by Santa").
- Anything else (not installed, timeout, error, empty, rejected) uses the templates. Usage is recorded with
  `tutor.usage.record()`.

## 6. Edge cases

| Situation | Behaviour |
|---|---|
| Not enough answers in the unit | "Not enough answers yet"; no patterns; diagnostic quiz |
| Few questions at a level | Fill what exists; add a note; never invent |
| No questions in the unit at all | Worksheet and quiz say so; the plan still builds; assign is disabled |
| No published lesson in the unit | Plan from the unit's title, summary and competence plus misconceptions; references still listed |
| Key unit competence blank | Field empty and editable |
| Santa off, slow, failing, over cap, or rejected reply | Templates; small note; the pack is never delayed past the deadline |
| Subscription lapses | Existing packs readable, editable, printable, deletable; create, refresh and assign return 403 |
| Questions unpublished after the pack was made | The snapshot reprints unchanged; assign uses only still-published questions and reports how many dropped |
| Assign repeated | Returns the existing assignment (unique pack + what) |
| Student left the class | Excluded from statistics and from students needing help |
| Class deleted | Its packs are deleted |
| Class archived | Its packs stay readable, editable, printable and deletable; create and assign return 400 "This class is archived" |
| Class has no subject | Statistics and the unit picker cover every subject for the class's grade |
| Teacher's account erased | Their packs are deleted (`userdata.erase_for`) |

## 7. Security and privacy

- Student names appear only in the teacher's Insight tab, computed live from current enrollments; they are
  never stored in a pack, so an erased student cannot remain in one. Student prints never show other students'
  names or results.
- Plan edits and AI text: cleaned, length-limited, rendered as plain text (no HTML, no Markdown rendering of
  edits).
- PATCH accepts only the allow-listed plan keys; every other field is read-only (mass-assignment tests).
- Assigned quizzes from library questions remain premium (the existing rule that library material cannot be
  repackaged); their author is the teacher.
- The cross-user access matrix covers every new route; mass-assignment tests cover PATCH and assign.
- Throttles: default throttles on every view, plus `teaching_pack` on creation; Santa calls count toward the
  tutor caps.

## 8. Settings

All read from the environment, with these defaults, documented in `.env.docker.example` and
`backend/.env.example`:

| Setting | Default |
|---|---|
| `TEACHING_MIN_STUDENTS` | 5 |
| `TEACHING_MISCONCEPTION_SHARE` | 0.3 |
| `TEACHING_MASTERED_SHARE` | 0.85 |
| `TEACHING_WORKSHEET_PER_LEVEL` | 5 |
| `TEACHING_QUIZ_SIZE` | 10 |
| `TEACHING_PERIOD_MINUTES` | 40 |
| `TEACHING_LOOKBACK_DAYS` | 365 |
| `TEACHING_AI_SECONDS` | 20 |
| `THROTTLE_TEACHING_PACK` | 30/hour |

## 9. Testing

Backend (pytest, SQLite and PostgreSQL):
- `class_unit_scores`: the gradebook's `weak_units` is identical before and after the move (regression test
  with a fixed dataset).
- Insight: exact averages; the right most-picked wrong option and share; threshold respected (one student never
  makes a pattern); former students excluded; other classes' answers never counted; lookback respected.
- Builder: levels by difficulty; priority order; drafts and mastered excluded; quiz auto-marked types only;
  diagnostic quiz without data; notes for short levels; no lesson; blank competence; references; timings scale
  with duration; French fields used when present.
- Polish: not installed, timeout, error, empty, malformed JSON, over-long, injection-looking — all give
  templates with `ai: false`; success gives cleaned text with `ai: true`; usage recorded; caps respected.
- API: create, list, retrieve, PATCH allow-list, delete, assign; assign idempotent; an assigned quiz appears to
  the class's students and marks itself; unpublished questions dropped and reported; an archived class refuses
  create and assign; a class without a subject gets every subject's units for its grade.
- Access: student, parent, another teacher, another school's administrator and anonymous are refused on every
  route; unpaid school gets the teaser on create; lapsed school can read, edit and delete but not create,
  refresh or assign.
- Privacy: export includes packs; erasure removes them; students needing help is not in the stored document.
- Translations: every new message has French (existing test).

Frontend:
- Vitest: the four tabs render from a fixture document; plan edits save; student print has no answers, key
  print has answers; teaser for unpaid; i18n parity and no-emoji tests.
- Playwright: teacher opens the class report, makes a pack, edits a plan field, opens each print view (app
  chrome hidden), assigns the quiz; the student sees the assignment. Unpaid school sees the teaser.
- Screenshots: phone and desktop, light and dark, plus print previews.

## 10. Assumptions to confirm

- CBC layout as the default lesson-plan format (the owner was unsure; every field is editable either way).
- Default period of 40 minutes and the thresholds in section 8 (all configurable).
- This work lands on the branch `claude/wonderful-cannon-lkbyu8`, so it joins the open pull request
  KARMA-debug-CODE/Iga-app#2 unless the owner prefers a separate pull request.
