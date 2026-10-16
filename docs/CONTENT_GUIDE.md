# Content guide

There are two ways to add content:

1. **In the app.** Approved teachers use **Teach** to write questions, build quizzes, write lessons (with a live preview) and share resources. Their classes can use the content straight away. It enters the public library after an admin approves it under **Admin → Content review**.
2. **As files** in `backend/content/`, for curriculum teams adding many lessons or importing exam papers. Files are reviewed through pull requests and loaded with:

```bash
python manage.py load_curriculum          # everything in backend/content/
python manage.py import_exam_paper paper.json [--draft]
```

Both commands are **idempotent**: running them again updates existing items, matched by `slug`, by `(subject, grade, number)` for units, and by `(title, subject, grade)` for quizzes. They never duplicate. A quiz's questions are rebuilt only while nobody has attempted it, so students' results stay valid. Re-running them never republishes a lesson or quiz an admin has archived or unpublished, and a PDF-only past paper and its digitised version are merged into one library entry.

---

## Subjects and units

- `content/subjects.json` holds code, names in English and French (`name_fr`), icon (the name of a line icon in `frontend/src/components/Icon.jsx`, such as `atom`; no emojis), colour, and whether the subject is offered at O-level and/or A-level.
- `content/units.json` maps `{subject_code: {grade: [unit titles in order]}}`.

After checking a unit against the official REB syllabus, tick **alignment verified** in the Django admin (and fill in *syllabus reference* and *key unit competence*). The "draft outline" notice then disappears for that unit.

Units are matched by `(subject, grade, number)`, so giving a unit another number renames the unit that had that number. A unit removed from `units.json` is deleted by the next `load_curriculum` when nothing is in it; a unit that still holds lessons, questions, quizzes or teachers' material is kept, and the command lists it so you can move that content first.

ICT and Computer Science are two subjects, as in REB's curriculum: `ict` for every student (S1–S6) and `computer-science` for A-level students in the MCE and MPC combinations (S4–S6). The migration `curriculum/0007_computer_science` moved the units of the old combined subject, with everything in them, to their new places; run `load_curriculum` after it. A-level students can set their combination in their profile, and its three principal subjects then come first in their subject lists: the combinations and their subjects are `COMBINATIONS` in `apps/core/constants.py` (with the names in the frontend dictionaries, `combination.MCE`…).

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

Run real Python in the browser (it works offline once loaded; `input()` is supported). Programs have no network access, so they can't download data or packages:

```python-run
name = input("Your name? ")
print("Muraho", name)
```
```

Labs listed in `simulations:` but not embedded inline appear in a "Try it in the lab" section after the lesson.

Writing tips:
- Short paragraphs; a worked example for every new idea; finish with **Check yourself** questions and answers.
- Use local contexts: FRW prices, moto fares, Lake Kivu, Mount Karisimbi, farming in Musanze.
- Raw HTML is ignored for safety. Use Markdown only.

## Free or premium

Library lessons and quizzes are part of the school subscription unless marked free: add `access: free` to a lesson's front matter, or `"access": "free"` to a quiz file. Keep one starter lesson and quiz per subject free so every student can try Iga. Lessons and quizzes that teachers write in the app are free automatically (unless a quiz reuses library questions). See [School subscriptions](SUBSCRIPTIONS.md).

## Translations: `content/translations/<slug>.fr.md`

Unit titles in French live in `content/units.fr.json`, with exactly the same structure (subject → grade → list of titles) as `units.json`; the loader checks the lists have the same length.

The front matter holds `slug`, `language` (`fr`), `title` and `summary`, and optionally `reviewed: true` once a fluent speaker has checked it. The body is the translated Markdown. Students see a language switch on the lesson, and the lesson falls back to English when there is no translation.

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

## Books: `content/books.json`

Every lesson and every unit shows **Books**: the official REB student's book for that subject and grade first, then a few
free open textbooks. Units that have no Iga lesson yet point students to the official book, with the unit to look for.
Books are **links** to the publishers' own sites (REB's e-learning portal, OpenStax, Standard Ebooks…); the app never copies
them, so a book's licence does not need to allow redistribution. They need internet; they are not saved for offline use.

```json
{
  "id": "reb-mathematics-s2",
  "subject": "mathematics",
  "grades": ["S2"],
  "kind": "textbook",
  "official": true,
  "title": "Mathematics Senior 2 Student's Book",
  "publisher": "Rwanda Basic Education Board (REB)",
  "language": "en",
  "url": "https://elearning.reb.rw/…",
  "format": "pdf",
  "licence": "© REB, free to read",
  "description": "One short sentence for students.",
  "description_fr": "La même phrase en français.",
  "source": "Where the link came from (for editors; not shown in the app)"
}
```

- `id` stays the same when you edit an entry. Official books are `reb-<subject>-<grade>`.
- `grades`: the book is shown on every lesson and unit of those grades. `kind`: `textbook`, `teacher_guide` or `link`.
- `official: true` only for REB books; keep **one** official student's book for every subject and grade (a test checks it).
- `language`: `en`, `fr`, `rw` (Kinyarwanda) or `sw` (Kiswahili). `format`: `pdf` (the link downloads a PDF), `page` (a page
  that links the book, such as a REB folder) or `web` (read online).
- The link must start with `https://`. Removing an entry removes the book from the site on the next `load_curriculum`;
  books that teachers add in the app are never touched.

**Links change.** REB replaces its files from time to time, and the old links stop working. Every term, from a computer with
normal internet access, run:

```bash
python manage.py check_book_links            # or --subject mathematics
```

It lists every broken link; find the new one on [elearning.reb.rw](https://elearning.reb.rw/) (guest access, no account)
and update `books.json`. The links in the file were collected from REB's portal listings and the publishers' own pages;
run the checker before a pilot.

## Simulations: `content/simulations.json`

| provider | `provider_id` | Notes |
|---|---|---|
| `builtin` | `projectile`, `grapher`, `ohms`, `market` | Our own React labs in `frontend/src/sims/`; work offline |
| `phet` | the sim's name in its PhET URL, e.g. `circuit-construction-kit-dc` | Embedded as `https://phet.colorado.edu/sims/html/<name>/latest/<name>_all.html?locale=…`, in French when the student reads in French (PhET falls back to English where a translation is missing) |
| `geogebra` | `graphing`, `geometry`, `3d`, `scientific`, or a GeoGebra material ID | Apps load via GeoGebra's official deploy script |
| `external` | a full `https://` URL of another site | Must allow embedding in an iframe; anything else (`http:`, `javascript:`, a page of Iga itself) is refused and never framed |

Give each entry a French title in `title_fr` (and `description_fr` / `learning_goals_fr` when it has a description or goals); French readers see those, and the English texts otherwise.

To add a new built-in lab, put a component in `frontend/src/sims/`, register it in `sims/registry.js`, keep its maths in a pure function with a unit test (see `physics.js`), and add a catalogue entry with `"provider": "builtin"`.

## Review workflow

| Who | Can publish directly? |
|---|---|
| Content files merged to `main` | Yes, loaded as published (use `--draft` for exam papers if you want a second check) |
| Admin in the app | Yes |
| Approved teacher in the app | Visible to their own classes at once; public after admin approval. Every edit to a published lesson goes back to review |

Every create, edit, approval and rejection is written to the audit log.
