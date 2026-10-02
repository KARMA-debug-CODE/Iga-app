# Content guide

There are two ways to add content:

1. **In the app.** Approved teachers use **Teach** to write questions, build quizzes, write lessons (with a live preview) and share resources. Their classes can use the content straight away. It enters the public library after an admin approves it under **Admin → Content review**.
2. **As files** in `backend/content/`, for curriculum teams adding many lessons or importing exam papers. Files are reviewed through pull requests and loaded with:

```bash
python manage.py load_curriculum          # everything in backend/content/
python manage.py import_exam_paper paper.json [--draft]
```

Both commands are **idempotent**: running them again updates existing items, matched by `slug`, by `(subject, grade, number)` for units, and by `(title, subject, grade)` for quizzes. They never duplicate. A quiz's questions are rebuilt only while nobody has attempted it, so students' results stay valid.

---

## Subjects and units

- `content/subjects.json` holds code, names in English/Kinyarwanda/Kiswahili, icon, colour, and whether the subject is offered at O-level and/or A-level.
- `content/units.json` maps `{subject_code: {grade: [unit titles in order]}}`.

After checking a unit against the official REB syllabus, tick **alignment verified** in the Django admin (and fill in *syllabus reference* and *key unit competence*). The "draft outline" notice then disappears for that unit.

## Lessons: `content/lessons/<slug>.md`

```markdown
---
slug: s2-physics-ohms-law          # unique, used in the URL
subject: physics                   # subject code
grade: S2
unit: 4                            # unit number within that grade
order: 1                           # position within the unit
title: Current, voltage and Ohm's law
summary: One sentence shown at the top and in lists.
minutes: 25
simulations: ohms-law-lab, phet-ohms-law     # optional, comma-separated slugs
video: https://...                            # optional
---
## Headings, **bold**, tables, lists…

Maths: inline $V = IR$ or display $$I = \frac{V}{R}$$

Embed a lab where it's needed in the text:

```sim
ohms-law-lab
```

Embed a live HTML/CSS/JS editor (for ICT lessons):

```playground html
<h1>Hello</h1>
```
```

Labs listed in `simulations:` but not embedded inline appear in a "Try it in the lab" section after the lesson.

Writing tips:
- Short paragraphs; a worked example for every new idea; finish with **Check yourself** questions and answers.
- Use local contexts: FRW prices, moto fares, Lake Kivu, Mount Karisimbi, farming in Musanze.
- Raw HTML is ignored for safety. Use Markdown only.

## Translations: `content/translations/<slug>.<lang>.md`

The front matter holds `slug`, `language` (`rw` or `sw`), `title` and `summary`, and optionally `reviewed: true` once a fluent speaker has checked it. The body is the translated Markdown. Students see a language switch on the lesson, and the lesson falls back to English when there is no translation.

## Quizzes: `content/quizzes/<name>.json`

```json
{
  "title": "Ohm's law — practice",
  "subject": "physics", "grade": "S2", "unit": 4,
  "kind": "practice",                 // practice | test | mock | past_paper
  "feedback_mode": "immediate",       // immediate | after_submit (exam mode)
  "time_limit_minutes": null,
  "shuffle_questions": true, "shuffle_choices": true,
  "questions": [
    {"type": "mcq", "prompt": "…", "marks": 1, "difficulty": 1,
     "choices": [{"text": "…"}, {"text": "…", "correct": true}],
     "explanation": "Shown after answering."},
    {"type": "multi",      "prompt": "…", "choices": [{"text": "…", "correct": true}, …]},
    {"type": "true_false", "prompt": "…", "answer": false},
    {"type": "numeric",    "prompt": "…", "answer": 9.8, "tolerance": 0.1},
    {"type": "short",      "prompt": "…", "accepted": ["ohm", "ohms", "Ω"]},
    {"type": "essay",      "prompt": "…", "marks": 4, "marking_guide": "1 mark for …"},
    {"type": "numeric",    "prompt": "…", "answer": 3, "unit_ref": {"grade": "S1", "unit": 3}}
  ]
}
```

- Remember to escape backslashes in JSON: write `"$\\frac{1}{2}$"`.
- `unit_ref` tags a question with a unit from another grade (useful in exam papers covering S1–S3). The class report uses these tags to find weak topics.
- The importer rejects bad files with a clear error: an MCQ without exactly one correct option, a numeric question without an answer, an unknown unit, and so on.

## Exam papers: `content/exam_papers/<name>.json`

Same format as a quiz plus a `paper` block:

```json
{
  "paper": {
    "level": "O", "year": 2019, "paper_code": "Paper 1",
    "title": "Mathematics O-Level 2019 Paper 1",
    "is_official": true,
    "source_note": "Published by NESA; used with permission (ref …)",
    "paper_url": "https://…/paper.pdf",
    "marking_guide_url": "https://…/marking-guide.pdf"
  },
  "title": "Mathematics O-Level 2019 Paper 1",
  "subject": "mathematics", "grade": "S3",
  "kind": "past_paper", "feedback_mode": "after_submit", "time_limit_minutes": 150,
  "shuffle_questions": false,
  "questions": [ … ]
}
```

- **Only set `is_official: true` for papers obtained from NESA with permission to publish them.** Unofficial papers are always labelled "Unofficial sample" in the app.
- A paper can be PDF-only: give `paper_url` and an empty `questions` list for the library entry. Digitise the questions later to make it interactive.
- Use `--draft` to import for admin review before students see it.
- Written questions (`essay`) go to teachers' marking queues. The `marking_guide` is shown to teachers, and to students after they submit.

## Simulations: `content/simulations.json`

| provider | `provider_id` | Notes |
|---|---|---|
| `builtin` | `projectile`, `grapher`, `ohms`, `market` | Our own React labs in `frontend/src/sims/`; work offline |
| `phet` | the sim's name in its PhET URL, e.g. `circuit-construction-kit-dc` | Embedded as `https://phet.colorado.edu/sims/html/<name>/latest/<name>_all.html?locale=…`. Set `supports_kinyarwanda` once you've confirmed a Kinyarwanda translation exists |
| `geogebra` | `graphing`, `geometry`, `3d`, `scientific`, or a GeoGebra material ID | Apps load via GeoGebra's official deploy script |
| `external` | a full `https://` URL | Must allow embedding in an iframe |

To add a new built-in lab, put a component in `frontend/src/sims/`, register it in `sims/registry.js`, keep its maths in a pure function with a unit test (see `physics.js`), and add a catalogue entry with `"provider": "builtin"`.

## Review workflow

| Who | Can publish directly? |
|---|---|
| Content files merged to `main` | Yes, loaded as published (use `--draft` for exam papers if you want a second check) |
| Admin in the app | Yes |
| Approved teacher in the app | Visible to their own classes at once; public after admin approval. Every edit to a published lesson goes back to review |

Every create, edit, approval and rejection is written to the audit log.
