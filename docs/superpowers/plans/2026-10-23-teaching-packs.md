# Teaching Packs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One click turns a class's weak unit into a saved teaching pack (class insight with misconceptions, a pre-filled CBC lesson plan, a three-level worksheet with answer key, and a targeted quiz), printable or assigned in Iga, as the paid feature of the school subscription.

**Architecture:** A new Django app `apps/teaching` with four single-purpose modules (`insight` reads the class's answers, `builder` assembles the pack from checked content, `polish` adds optional labelled Santa text with a fallback, `models` stores snapshots), a small DRF API under `/api/teaching/`, and React pages for the pack, the pack list and print layouts. The gradebook's weak-unit maths moves to `apps/classroom/analytics.py` so both share it.

**Tech Stack:** Django 5.2 + DRF, PostgreSQL/SQLite, pytest; React 19 + Vite, vitest, Playwright. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-23-teaching-packs-design.md` (read it with this plan; section numbers below refer to it).

## Global Constraints

- Branch `claude/wonderful-cannon-lkbyu8`; commit after every task; every commit message ends with a blank line, then:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_013oGCxbyk2MeA2orj2puVnf`.
- No new Python or npm dependencies.
- Every user-visible string in English and French: frontend keys in `frontend/src/i18n/en.js` and `fr.js` (flat dotted keys, prefix `packs.`; `src/i18n/parity.test.js` checks parity); backend strings via `gettext`, then `cd backend && .venv/bin/python scripts/messages.py extract`, add the French in `backend/locale/fr/LC_MESSAGES/django.po`, then `.venv/bin/python scripts/messages.py compile` (`tests/test_translations.py` fails otherwise). Do this inside the task that adds the string.
- No emojis (`frontend/src/no-emoji.test.js`); icons only from `frontend/src/components/Icon.jsx`.
- Settings read from the environment with these defaults (spec §8): `TEACHING_MIN_STUDENTS=5`, `TEACHING_MISCONCEPTION_SHARE=0.3`, `TEACHING_MASTERED_SHARE=0.85`, `TEACHING_WORKSHEET_PER_LEVEL=5`, `TEACHING_QUIZ_SIZE=10`, `TEACHING_PERIOD_MINUTES=40`, `TEACHING_LOOKBACK_DAYS=365`, `TEACHING_AI_SECONDS=20`, `THROTTLE_TEACHING_PACK=30/hour`.
- Text from people or the model is cleaned with `apps.core.text.clean_text` / `CleanCharField` and rendered as plain text (no HTML, no Markdown rendering of edits).
- Match existing patterns: views like `apps/notes/views.py`, tests like `backend/tests/test_notes.py`, vitest like `frontend/src/pages/MyNotes.test.jsx`, e2e like `frontend/tests/e2e/notes.spec.js`.
- Checks per task: `cd backend && .venv/bin/python -m pytest -q <files>` plus `.venv/bin/ruff check . && .venv/bin/ruff format --check <touched files>`; frontend tasks: `cd frontend && npx eslint src tests && npx vitest run`.
- A question counts in statistics only through marked answers (`Answer.marks_awarded` not null) of marked attempts (`Attempt.status == "marked"`) submitted within `TEACHING_LOOKBACK_DAYS`; an answer is correct only with full marks (`marks_awarded == question.marks`); for each (student, question) only the student's latest such answer counts (latest `attempt.submitted_at`, then highest answer id).

## Review Focus

1. A class with years of attempts: building insight must not issue more queries as attempts grow (Task 3 test `test_insight_query_count_does_not_grow_with_attempts`).
2. Multi-select questions with partial credit: partial marks are not "correct", and wrongly ticked options still count toward misconceptions (Task 3 test `test_partial_marks_on_multi_select_are_not_correct`).
3. A school in its grace period after `paid_until` must still be treated as paid (Task 6 test `test_a_school_in_its_grace_period_can_make_packs`).
4. Lessons with no `## ` headings, or headings holding Markdown or maths, must still give a readable Development step (Task 4 test `test_development_falls_back_when_the_lesson_has_no_headings`).
5. A class handed to another teacher: its packs follow the class, so the previous teacher loses access and the new one gains it (Task 6 test `test_packs_follow_the_class_when_it_changes_teacher`).

---

### Task 1: Shared class unit scores

**Files:**
- Create: `backend/apps/classroom/analytics.py`
- Modify: `backend/apps/classroom/views.py` (`ClassroomViewSet.report`, the "Weak topics" block)
- Test: `backend/tests/test_classroom_analytics.py`

**Interfaces:**
- Produces:
  - `UnitScore` (frozen dataclass): `unit: Unit`, `got: float`, `possible: float`, property `average -> float` = `round(got / possible * 100, 1)`.
  - `class_unit_scores(classroom, students, since=None) -> list[UnitScore]`: marked answers with a unit, by `students`, in marked attempts (filtered to `classroom.subject_id` when set; to `submitted_at >= since` when `since` is given), summed per unit, units with `possible > 0` only, weakest first (ties by unit id).
  - Report rows in `weak_units` gain `"unit_id"`; existing keys and values unchanged.

- [ ] **Step 1: Write the failing tests**

```python
def test_report_weak_units_are_unchanged_and_carry_the_unit_id(client_for, teacher, subject, unit): ...
    # fixed dataset: two units; unit A 1/4 marks, unit B 3/4 marks
    # assert report["weak_units"] == [
    #   {"unit": f"{unit_a.grade} Unit {unit_a.number}: {unit_a.title}", "average": 25.0, "unit_id": unit_a.id},
    #   {"unit": ..., "average": 75.0, "unit_id": unit_b.id}]
def test_class_unit_scores_are_weakest_first(...): ...      # [s.unit for s in scores] == [unit_a, unit_b]
def test_class_unit_scores_respect_since(...): ...          # an attempt submitted before `since` is not counted
def test_class_unit_scores_count_only_the_given_students(...): ...
```

- [ ] **Step 2: Run them; expect failures** — `pytest tests/test_classroom_analytics.py -q` → ImportError / KeyError `unit_id`.
- [ ] **Step 3: Implement `class_unit_scores` and switch `report` to it** (the report passes its current `students` list and no `since`; it keeps the 5 weakest).
- [ ] **Step 4: Run `pytest tests/test_classroom_analytics.py tests/test_classroom.py -q`** → all pass.
- [ ] **Step 5: Commit** — `Classroom: share the class unit scores; weak units carry the unit id`.

---

### Task 2: Teaching app, models, settings and personal data

**Files:**
- Create: `backend/apps/teaching/{__init__,apps,models,admin,userdata}.py`, `backend/apps/teaching/migrations/0001_initial.py` (via `makemigrations teaching`)
- Modify: `backend/config/settings.py` (`INSTALLED_APPS` add `"apps.teaching"`; the nine settings; `DEFAULT_THROTTLE_RATES["teaching_pack"]`), `docker-compose.yml` (backend `environment`, pattern `KEY: ${KEY:-default}`), `.env.docker.example`, `backend/.env.example`
- Test: `backend/tests/test_teaching_models.py`

**Interfaces:**
- Produces (spec §4.1):
  - `TeachingPack` fields `classroom` (CASCADE, `related_name="teaching_packs"`), `unit` (SET_NULL, null), `lesson` (SET_NULL, null), `created_by` (CASCADE, `related_name="teaching_packs"`), `created_at`, `language` (`"en"|"fr"`), `document` (JSON), `plan_edits` (JSON, default dict), `ai_used` (bool, default False); `Meta.ordering = ["-created_at", "-id"]`.
  - `PackAssignment.What` TextChoices `QUIZ="quiz"`, `WORKSHEET_SUPPORT="worksheet_support"`, `WORKSHEET_CORE="worksheet_core"`, `WORKSHEET_STRETCH="worksheet_stretch"`; fields `pack` (CASCADE, `related_name="assignments"`), `what`, `quiz` (SET_NULL, null), `assignment` (SET_NULL, null), `created_at`; `UniqueConstraint(fields=["pack", "what"], name="one_assignment_per_pack_part")`.
  - `PLAN_EDITABLE_FIELDS` (tuple in `models.py`): `school, teacher, term, date, lesson_number, duration, class_size, sen_learners, unit_title, key_unit_competence, lesson_title, objective, location, materials, references, steps, evaluation, self_evaluation`.
  - `userdata.export_for(user) -> {"teaching_packs": [{"unit", "lesson", "created_at", "language", "plan_edits"}]}` (labels from `document`); `userdata.erase_for(user)` deletes the user's packs.

- [ ] **Step 1: Write the failing tests**

```python
def test_one_assignment_per_pack_part(...):        # second PackAssignment(pack, "quiz") -> IntegrityError
def test_deleting_the_class_deletes_its_packs(...):
def test_export_lists_the_teachers_packs(...):     # export_for(teacher)["teaching_packs"][0]["unit"] == document["unit"]["label"]
def test_erasure_deletes_the_teachers_packs(...):  # erase_for(teacher); TeachingPack.objects.count() == 0
def test_teaching_settings_have_their_defaults(settings):
    assert settings.TEACHING_MIN_STUDENTS == 5 and settings.TEACHING_MISCONCEPTION_SHARE == 0.3
    assert settings.TEACHING_MASTERED_SHARE == 0.85 and settings.TEACHING_QUIZ_SIZE == 10
    assert settings.TEACHING_PERIOD_MINUTES == 40 and settings.TEACHING_AI_SECONDS == 20
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["teaching_pack"] == "30/hour"
```

- [ ] **Step 2: Run** `pytest tests/test_teaching_models.py -q` → fails (app missing).
- [ ] **Step 3: Implement** the app, models, migration, admin (read-only list of packs: class, unit label, author, date), userdata, settings, compose and env docs.
- [ ] **Step 4: Run** `pytest tests/test_teaching_models.py tests/test_privacy.py -q` and `python manage.py makemigrations --check --dry-run` → pass / "No changes detected".
- [ ] **Step 5: Commit** — `Teaching: app, pack models, settings and personal data`.

---

### Task 3: Class insight

**Files:**
- Create: `backend/apps/teaching/insight.py`, `backend/tests/teaching_factories.py`
- Test: `backend/tests/test_teaching_insight.py`

**Interfaces:**
- Consumes: `class_unit_scores` (Task 1).
- Produces:
  - `teaching_factories.mark_answer(student, question, marks, choices=(), submitted_at=None, quiz=None) -> Answer` — a marked attempt with one answer (test helper, reused by Tasks 4, 6, 7).
  - `current_students(classroom) -> QuerySet[User]` (active enrollments).
  - `unit_label(unit, lang) -> str` — `f"{grade} Unit {number}: {title}"`, `title_fr` when `lang == "fr"` and set.
  - `QStat` (frozen dataclass): `question`, `answered: int`, `correct: int`, `choice_counts: dict[int, int]`; property `correct_share -> float` (0 when `answered == 0`); `most_picked_wrong() -> tuple[Choice, float] | None` (choice types only; share of `answered`).
  - `question_stats(classroom, unit) -> dict[int, QStat]` — published questions of the unit; rules in Global Constraints.
  - `unit_insight(classroom, unit, lang="en") -> dict` — keys `data_enough`, `average` (from `class_unit_scores` with current students and the lookback; `None` without data), `other_units` (up to 5 `{label, average}`), `misconceptions` (up to 3 `{question_id, prompt, wrong_choice, share, answered, correct, explanation}`, `share` rounded to 2, `correct` = correct choice texts joined with `" / "`), `hardest` (up to 5 `{question_id, prompt, correct_share, answered}`). Thresholds per spec §5.2.
  - `students_needing_help(classroom, unit) -> list[{"id", "display_name", "average", "answered"}]` — spec §5.2.

- [ ] **Step 1: Write the failing tests**

```python
def test_misconception_is_the_most_picked_wrong_option(...):
    # 6 current students: 4 pick "3", 1 picks "5", 1 picks "4" (correct)
    m = unit_insight(c, unit)["misconceptions"][0]
    assert (m["wrong_choice"], m["share"], m["answered"], m["correct"]) == ("3", 0.67, 6, "4")
def test_a_wrong_option_below_the_share_is_not_a_misconception(...):   # 2 of 10 pick "3" -> []
def test_fewer_students_than_the_threshold_make_no_pattern(...):       # 4 students -> data_enough False, []
def test_only_each_students_latest_answer_counts(...):                 # wrong then right -> correct == answered
def test_former_students_and_other_classes_are_ignored(...):
def test_answers_older_than_the_lookback_are_ignored(settings, ...):   # TEACHING_LOOKBACK_DAYS = 30
def test_partial_marks_on_multi_select_are_not_correct(...):           # Review Focus 2
    # multi question, 2 marks; 5 students score 1 with wrong option "X" ticked -> correct 0, misconception "X"
def test_hardest_lists_the_lowest_correct_share_first(...):
def test_students_needing_help(...):   # 3 answers at 33% listed; 2 answers excluded; 80% excluded; lowest first
def test_insight_query_count_does_not_grow_with_attempts(...):         # Review Focus 1
    # CaptureQueriesContext around unit_insight + students_needing_help for 5 attempts and for 50: equal counts
```

- [ ] **Step 2: Run** `pytest tests/test_teaching_insight.py -q` → fails.
- [ ] **Step 3: Implement** `insight.py` (prefetch answers with `selected_choices`, `question__choices`; compute in Python per (student, question)).
- [ ] **Step 4: Run** the same → pass.
- [ ] **Step 5: Commit** — `Teaching: class insight with misconceptions`.

---

### Task 4: Pack builder

**Files:**
- Create: `backend/apps/teaching/builder.py`
- Test: `backend/tests/test_teaching_builder.py`

**Interfaces:**
- Consumes: `question_stats`, `unit_insight`, `unit_label`, `current_students` (Task 3).
- Produces:
  - `LEVELS = (("support", 1), ("core", 2), ("stretch", 3))`.
  - `question_payload(question) -> dict` — spec §5.1 `<question>` shape.
  - `priority_ids(insight) -> list[int]` — misconception question ids in order, then hardest ids not already listed.
  - `select_worksheet(unit, stats, priority) -> {"support": [Question], "core": [...], "stretch": [...], "notes": [str]}` — spec §5.2; note copy `_("Only %(count)s %(level)s questions exist for this unit.")` / `_("No %(level)s questions exist for this unit yet.")` with level names `_("support")`, `_("core")`, `_("stretch")`.
  - `select_quiz(unit, stats, priority, data_enough) -> tuple[list[Question], bool]` — `(questions, is_diagnostic)`, spec §5.2.
  - `default_lesson(unit) -> Lesson | None` — first published lesson by `order`, then id.
  - `lesson_plan(classroom, unit, lesson, teacher, insight, core_questions, lang) -> dict` — the keys of `PLAN_EDITABLE_FIELDS` plus read-only `subject`, `class_name`, `unit_number`; `steps` = three dicts `{name, minutes, teacher, learners, competences}` named `introduction`, `development`, `conclusion`; minutes `round(D*5/40)`, `D - intro - conclusion`, `round(D*10/40)` for `D = TEACHING_PERIOD_MINUTES`; filling per spec §5.3.
  - `template_polish(document) -> {"hook", "simpler", "ai": False}`.
  - `build_pack(classroom, unit, lesson, teacher, lang) -> dict` — the full document, `version` 1, `polish` = `template_polish`, top-level `notes` (e.g. `_("Some content is only available in English.")`), JSON-serialisable.
  - `apply_polish(document, polish) -> dict` — stores `polish`; when `polish["ai"]`, puts the hook in the introduction's `teacher` text and appends `simpler` to the development step's `teacher` text.

- [ ] **Step 1: Write the failing tests**

```python
def test_worksheet_levels_follow_difficulty(...):        # q.difficulty 1/2/3 land in support/core/stretch
def test_misconception_questions_come_first(...):         # priority id is first in its level
def test_drafts_and_mastered_questions_are_left_out(...): # draft and correct_share 0.9 (answered >= 5) excluded
def test_short_levels_say_so_and_are_not_backfilled(...): # 2 stretch -> notes contain "Only 2 stretch"; core not moved
def test_quiz_uses_only_self_marking_questions(...):      # essay and short-without-accepted excluded
def test_diagnostic_quiz_without_data(...):               # data_enough False -> diagnostic True, difficulties cycle 1,2,3
def test_plan_is_prefilled(...):                          # key_unit_competence, lesson_title, class_size, references (official textbooks, max 3)
def test_blank_competence_stays_blank(...):
def test_step_minutes_scale_with_the_period(settings, ...): # 40 -> [5, 25, 10]; 80 -> [10, 50, 20]
def test_development_tackles_the_misconceptions(...):     # wrong_choice and correct text appear in development "teacher"
def test_introduction_recalls_the_previous_unit(...):     # unit number 3 of the subject and grade -> unit 2's title in introduction "teacher"; unit 1 has no recall
def test_development_falls_back_when_the_lesson_has_no_headings(...):  # Review Focus 4
    # no "## " lines -> one activity named after the lesson; "## The **speed** $v$" -> "The speed v" (no * or $)
def test_plan_without_a_lesson_uses_the_unit(...):
def test_french_pack_uses_french_titles_and_notes_the_gaps(...):
def test_pack_document_is_json_and_versioned(...):        # json.dumps(doc); doc["version"] == 1; doc["polish"]["ai"] is False
def test_apply_polish_only_changes_text_when_ai(...):
```

- [ ] **Step 2: Run** `pytest tests/test_teaching_builder.py -q` → fails.
- [ ] **Step 3: Implement** `builder.py` (strip `*`, `_`, `` ` ``, `$` and leading `#` from heading text; plan copy in English via `gettext`, French in the catalogue).
- [ ] **Step 4: Run** the same plus `tests/test_translations.py` → pass.
- [ ] **Step 5: Commit** — `Teaching: assemble packs from checked content`.

---

### Task 5: Optional Santa polish

**Files:**
- Create: `backend/apps/teaching/polish.py`
- Test: `backend/tests/test_teaching_polish.py`

**Interfaces:**
- Consumes: `template_polish` (Task 4); `apps.tutor.llm` (`installed()`, `cached_health()`, `chat(payload, deadline) -> Reply` with `content`, `prompt_tokens`, `completion_tokens`; errors subclass `llm.SantaError`), `apps.tutor.guard` (`neutralise(text, authored=True)`, `looks_like_injection(text)`), `apps.tutor.usage` (`allowance(user).reached`, `record(user, input_tokens, output_tokens)`).
- Produces: `polish(document, teacher, lang) -> {"hook": str, "simpler": str, "ai": bool}` — never raises.
  - Calls Santa only when installed, cached health is not `"unreachable"`, `allowance(teacher).reached` is falsy, and the document has at least one misconception; otherwise `template_polish(document)`.
  - Payload `{"model": settings.SANTA_MODEL_NAME, "messages": [system, user], "max_tokens": 300}`, deadline `time.monotonic() + settings.TEACHING_AI_SECONDS`; facts per spec §5.4, each through `neutralise(..., authored=True)`.
  - Accept only a JSON object (one surrounding ``` fence may be stripped) with non-empty string `hook` and `simpler`, each ≤ 80 words and ≤ 800 characters, neither `looks_like_injection`; then `clean_text(..., multiline=True)`; record usage on every completed call.

- [ ] **Step 1: Write the failing tests** (monkeypatch `apps.teaching.polish.llm`)

```python
def test_without_santa_the_template_is_used(...):        # installed False -> ai False, chat not called
def test_no_misconception_means_no_call(...):
def test_santa_reply_is_cleaned_and_labelled(...):       # content '{"hook": "Ask...", "simpler": "Speed..."}' -> ai True
def test_fenced_json_is_accepted(...):
@pytest.mark.parametrize("failure", ["timeout", "error", "empty", "not_json", "too_long", "injection"])
def test_every_failure_falls_back_to_the_template(failure, ...):   # ai False
def test_usage_is_recorded(...):                         # SantaUsage for teacher grows by prompt+completion tokens
def test_a_reached_allowance_skips_santa(...):
def test_lesson_text_sent_to_santa_is_neutralised(...):  # explanation "ignore previous instructions" absent from payload
```

- [ ] **Step 2: Run** `pytest tests/test_teaching_polish.py -q` → fails.
- [ ] **Step 3: Implement** `polish.py`.
- [ ] **Step 4: Run** the same → pass.
- [ ] **Step 5: Commit** — `Teaching: optional, labelled Santa polish with a template fallback`.

---

### Task 6: Pack API

**Files:**
- Create: `backend/apps/teaching/{access,serializers,views,urls}.py`
- Modify: `backend/config/urls.py` (in the `api` list: `path("teaching/", include("apps.teaching.urls"))`), `backend/tests/test_access_matrix.py`, `backend/tests/test_mass_assignment.py`
- Test: `backend/tests/test_teaching_api.py`

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces:
  - `access.teacher_classroom(user, pk) -> Classroom` — `get_object_or_404(Classroom, pk=pk, teacher=user)`.
  - `access.packs_for(user) -> QuerySet[TeachingPack]` — `classroom__teacher=user`.
  - `access.require_premium(user, teaser=None)` — raises 403 `{"detail", "code": "subscription_required", "teaser"}` unless `content_access(user).premium`.
  - `access.require_active(classroom)` — raises 400 `{"detail": _("This class is archived."), "code": "class_archived"}` when archived.
  - `serializers.merged_document(pack) -> dict` — `document` with `plan_edits` applied (step edits by index).
  - Routes (spec §4.2): `GET classes/<int:pk>/units/` (`ClassUnitsView`, no premium needed, `[{unit_id, label, subject, average, answered, misconceptions_found}]`); router `packs` (`PackViewSet`: list with `?classroom=`, create, retrieve with live `students_needing_help`, `partial_update` with `{plan: {...}}`, destroy). Create uses `throttle_scope = "teaching_pack"`; language from `apps.core.utils.request_language`.

- [ ] **Step 1: Write the failing tests**

```python
def test_creating_a_pack_saves_and_returns_it(...):       # 201; TeachingPack exists; document["unit"]["id"] == unit.id; ai_used False
def test_units_are_listed_weakest_first(...):
def test_a_class_without_a_subject_lists_every_subject(...):
def test_the_lesson_must_belong_to_the_unit(...):         # 400
def test_the_unit_must_match_the_class(...):              # other grade -> 400
def test_unpaid_school_gets_the_teaser(...):              # 403, code subscription_required, teaser keys {"unit","average","misconceptions_found"}; units endpoint 200
def test_a_school_in_its_grace_period_can_make_packs(...):  # Review Focus 3: paid_until = now - 1 day -> 201
def test_lapsed_school_keeps_its_packs(...):              # GET 200, PATCH 200, DELETE 204, POST 403
def test_archived_class_refuses_new_packs(...):           # 400 class_archived; GET 200
def test_plan_edits_are_allow_listed_cleaned_and_merged(...):  # objective saved; unknown key 400; 2001 chars 400; "​" removed
def test_students_needing_help_are_live_not_stored(...):  # in GET; "students_needing_help" not in pack.document
def test_packs_follow_the_class_when_it_changes_teacher(...):  # Review Focus 5: old teacher 404, new teacher 200
def test_list_filters_by_class(...):                      # ?classroom=abc -> 400; ?classroom=<id> filters
def test_creation_uses_the_teaching_pack_throttle(...):   # PackViewSet create throttles include scope "teaching_pack"
```

  Access matrix additions: `world` gets `pack_b` (class B, `teacher_b`, document and `plan_edits["objective"]` holding `"SECRET-PACK-B"`); `markers` add `"SECRET-PACK-B"`; `route_targets` add `api/teaching/classes/{pk}/units/` → `class_b`, `api/teaching/packs/{pk}/` and `.../assign/` → `pack_b`; `snapshot` adds side B's pack ids, `plan_edits` and the count of packs and pack assignments on `class_b`; the owners test asserts `teacher_b` reads `pack_b`.
  Mass assignment: `test_teaching_pack_writes_keep_owner_document_and_class` — POST with `created_by`, `document`, `ai_used` and PATCH with `document`, `classroom`, `created_by`, `ai_used` leave the server's values.

- [ ] **Step 2: Run** `pytest tests/test_teaching_api.py tests/test_access_matrix.py tests/test_mass_assignment.py -q` → fails.
- [ ] **Step 3: Implement** access, serializers, views, urls, and the French for new messages.
- [ ] **Step 4: Run** the same plus `tests/test_translations.py` → pass.
- [ ] **Step 5: Commit** — `Teaching: pack API for the class's teacher, paid schools only`.

---

### Task 7: Assigning a pack in Iga

**Files:**
- Modify: `backend/apps/teaching/{views,serializers}.py`
- Test: `backend/tests/test_teaching_assign.py`

**Interfaces:**
- Consumes: `packs_for`, `require_active`, `require_premium` (Task 6); `PackAssignment` (Task 2).
- Produces: `POST /api/teaching/packs/<pk>/assign/` with `{what, due_at?}` → `{what, assignment_id, quiz_id, dropped, created}`; 201 when created, 200 when it already existed; 400 `{"code": "nothing_to_assign"}` when none of the questions are still published. It creates a published practice `Quiz` (author = teacher, `is_free=False`, unit and subject of the pack, the questions in pack order), an `Assignment` on the class (`created_by` = teacher, `due_at`), and the `PackAssignment`, in one transaction with `select_for_update` on the pack's rows; an `IntegrityError` from a concurrent request returns the existing row.

- [ ] **Step 1: Write the failing tests**

```python
def test_assigning_the_quiz_creates_a_quiz_and_an_assignment(...):  # 201; quiz questions == document quiz ids in order; quiz.is_free False; author teacher
def test_assigning_twice_returns_the_same_assignment(...):          # 200; same assignment_id; Quiz count unchanged
def test_assigning_a_worksheet_level_uses_that_level(...):          # worksheet_core -> core ids
def test_unpublished_questions_are_dropped_and_reported(...):       # dropped == 1
def test_nothing_left_to_assign(...):                               # 400 nothing_to_assign
def test_students_can_take_the_assigned_quiz(...):                  # enrolled student lists it, starts, submits -> attempt "marked"
def test_lapsed_or_archived_cannot_assign(...):                     # 403 / 400
```

- [ ] **Step 2: Run** `pytest tests/test_teaching_assign.py -q` → fails.
- [ ] **Step 3: Implement** the `assign` action.
- [ ] **Step 4: Run** the same plus `tests/test_access_matrix.py tests/test_mass_assignment.py` → pass.
- [ ] **Step 5: Commit** — `Teaching: assign a pack's quiz or worksheet level to the class`.

---

### Task 8: Frontend entry points and the pack list

**Files:**
- Create: `frontend/src/pages/TeachingPacks.jsx`, `frontend/src/teaching/UnitPicker.jsx`, `frontend/src/teaching/PackTeaser.jsx`, `frontend/src/teaching/createPack.js`
- Modify: `frontend/src/pages/ClassDetail.jsx` (weak-units card), `frontend/src/App.jsx` (lazy routes `/teaching-packs`, `/teaching-packs/:id`, guarded like `/teach`), `frontend/src/components/Layout.jsx` (teacher nav entry), `frontend/src/components/Icon.jsx` (`pack` icon), `frontend/src/i18n/en.js`, `fr.js`, `frontend/src/styles.css`
- Test: `frontend/src/pages/TeachingPacks.test.jsx`, `frontend/src/teaching/createPack.test.jsx`

**Interfaces:**
- Consumes: Task 6 routes; `api`, `results`, `ApiError` from `src/api.js`.
- Produces: `createPack({classroom, unit, lesson}) -> Promise<{pack} | {teaser}>` — resolves `{teaser}` on a 403 with code `subscription_required`, rethrows other errors; a "Building your pack" state while waiting (creation can take up to `TEACHING_AI_SECONDS`). `PackTeaser({teaser})` shows the misconception count and the subscription message, plus a link to `/school/billing` when the user's role is `school_admin`.

- [ ] **Step 1: Write the failing tests**

```js
test("each weak unit offers a teaching pack and opens the new pack", ...)  // POST body {classroom, unit: unit_id}; navigates to /teaching-packs/<id>
test("an unpaid school sees the teaser with the misconception count", ...) // "3" and packs.teaser text shown; billing link only for school_admin
test("the unit picker lists the class's units weakest first", ...)
test("my teaching packs lists, filters by class and deletes", ...)
```

- [ ] **Step 2: Run** `npx vitest run src/pages/TeachingPacks.test.jsx src/teaching` → fails.
- [ ] **Step 3: Implement** the entry points, list, routes, nav, icon and strings.
- [ ] **Step 4: Run** `npx eslint src tests && npx vitest run` → pass.
- [ ] **Step 5: Commit** — `Teaching: make a pack from the class report; my teaching packs`.

---

### Task 9: The pack page

**Files:**
- Create: `frontend/src/pages/TeachingPack.jsx`, `frontend/src/teaching/{PackInsight,PackPlan,PackQuestions,AssignDialog}.jsx`, `frontend/src/teaching/fixture.js`
- Modify: `frontend/src/i18n/en.js`, `fr.js`, `frontend/src/styles.css`
- Test: `frontend/src/pages/TeachingPack.test.jsx`

**Interfaces:**
- Consumes: Tasks 6–7 routes; the `Tabs` component in `src/components/ui.jsx`.
- Produces: `fixture.js` exporting `packFixture` (a merged pack response with data, misconceptions, three levels, a quiz, `polish.ai: true`) used by Tasks 9–10; `PackQuestions({questions, showAnswers})`.
- Behaviour: tabs Insight / Lesson plan / Worksheet / Quiz; plan fields edit in place and PATCH `{plan: {field: value}}` 800 ms after the last keystroke with saving/saved/error status; Assign (disabled for a level or quiz with no questions) opens `AssignDialog` (optional due date) and posts `{what, due_at}`, then shows the result and any dropped count; Refresh posts `{classroom, unit, lesson}` again and opens the new pack; "Suggested by Santa" badge only when `polish.ai`; "Not enough answers yet" when `insight.data_enough` is false; diagnostic label on the quiz; notes shown.

- [ ] **Step 1: Write the failing tests**

```js
test("shows the four tabs from the pack", ...)
test("editing the objective saves after a pause", ...)     // fake timers; one PATCH {plan: {objective: "New"}}
test("assigning the quiz posts what and due date", ...)
test("assign is disabled for a part with no questions", ...)
test("labels Santa's text only when it is AI", ...)
test("says when there are not enough answers and marks the diagnostic quiz", ...)
test("lists the students who need help", ...)
```

- [ ] **Step 2: Run** `npx vitest run src/pages/TeachingPack.test.jsx` → fails.
- [ ] **Step 3: Implement** the page and components.
- [ ] **Step 4: Run** `npx eslint src tests && npx vitest run` → pass.
- [ ] **Step 5: Commit** — `Teaching: the pack page with insight, plan, worksheet and quiz`.

---

### Task 10: Print layouts

**Files:**
- Create: `frontend/src/teaching/PackPrint.jsx`
- Modify: `frontend/src/pages/TeachingPack.jsx` (render `PackPrint` alone when `?print=` is `insight|plan|worksheet|key|quiz`, call `window.print()` once after render), `frontend/src/styles.css` (`@media print`, following the existing print blocks), `frontend/src/i18n/en.js`, `fr.js`
- Test: `frontend/src/teaching/PackPrint.test.jsx`

**Interfaces:**
- Consumes: `packFixture`, `PackQuestions` (Task 9).
- Produces: `PackPrint({pack, mode})`. `worksheet` = the three levels for students (name and date lines, no answers); `key` = the worksheet answers (correct choices, numeric answer, accepted answers, marking guide, explanation); `quiz` = the quiz for students, then its key on a new page; `plan` = the CBC plan with edits; `insight` = misconceptions, hardest questions and students needing help, headed "Teacher only".

- [ ] **Step 1: Write the failing tests**

```js
test("the student worksheet has no answers", ...)   // prompts present; no explanation text; no correct marker
test("the answer key has the answers", ...)
test("the quiz print ends with its key on a new page", ...)
test("the plan print shows the teacher's edits", ...)
test("the insight print is headed Teacher only", ...)
test("print view calls window.print once", ...)
```

- [ ] **Step 2: Run** `npx vitest run src/teaching/PackPrint.test.jsx` → fails.
- [ ] **Step 3: Implement** `PackPrint` and the print styles.
- [ ] **Step 4: Run** `npx eslint src tests && npx vitest run && npm run build` → pass (build includes the bundle secret scan).
- [ ] **Step 5: Commit** — `Teaching: print layouts for plan, worksheet, key, quiz and insight`.

---

### Task 11: Browser test, screenshots and docs

**Files:**
- Create: `frontend/tests/e2e/teaching.spec.js`
- Modify: `docs/ARCHITECTURE.md` (apps table row for `teaching`; a short "Teaching packs" section), `docs/SUBSCRIPTIONS.md` (paid column: "Teaching packs"), `README.md` (features table row)

**Interfaces:**
- Consumes: the demo data from `seed_demo` (teacher `teacher` with class "S2 Mathematics — Stream A" in the paid school Lycée de Kigali); helpers `login`, `logout`, `PASSWORD` from `tests/e2e/helpers.js`.

- [ ] **Step 1: Write the spec**

```js
test("a teacher makes, edits, prints and assigns a teaching pack", ...)
  // teacher: class page -> Choose a unit -> first unit -> pack page with four tabs; edit objective (saved);
  // open ?print=worksheet with page.emulateMedia({media: "print"}): topbar hidden, no explanation text;
  // assign the quiz; logout; an enrolled student sees the new assignment
test("an unpaid school sees the teaser", ...)   // page.route POST /api/teaching/packs/ -> 403 subscription_required with teaser
```

- [ ] **Step 2: Run** `fuser -k 8131/tcp 5231/tcp; E2E_API_PORT=8131 E2E_WEB_PORT=5231 npx playwright test teaching.spec.js` → pass on mobile and desktop projects; also run `classroom.spec.js` (ClassDetail changed).
- [ ] **Step 3: Screenshots** — a temporary `tests/e2e/zz-teaching-shots.spec.js` writing PNGs to the session scratchpad `shots/teaching/` (pack tabs, teaser, each print view) at 360px and desktop, light and dark; review and fix; delete the temporary spec.
- [ ] **Step 4: Update the docs** listed above.
- [ ] **Step 5: Commit** — `Teaching: browser test and docs`.

---

### Task 12: Final verification and push

- [ ] **Step 1:** `cd backend && .venv/bin/python -m pytest -q` → all pass (SQLite).
- [ ] **Step 2:** PostgreSQL: `docker run -d --name pg-teaching -e POSTGRES_USER=iga -e POSTGRES_PASSWORD=iga -e POSTGRES_DB=iga -p 127.0.0.1:5480:5432 postgres:16-alpine`, then `DATABASE_URL=postgres://iga:iga@127.0.0.1:5480/iga .venv/bin/python -m pytest -q` → all pass; `docker rm -f pg-teaching`.
- [ ] **Step 3:** `.venv/bin/ruff check . && .venv/bin/ruff format --check .`; `python manage.py makemigrations --check --dry-run`; `cd ../frontend && npx eslint src tests && npx vitest run && npm run build` → clean.
- [ ] **Step 4:** `git push origin claude/wonderful-cannon-lkbyu8` (retry on network errors: 2s, 4s, 8s, 16s).
