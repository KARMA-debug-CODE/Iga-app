import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api, results } from "../api";
import Markdown from "../components/Markdown";
import { Empty, ErrorMessage, GRADES, Loader, Tabs, useToast } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

const TYPES = [
  ["mcq", "Multiple choice (one answer)"],
  ["multi", "Multiple choice (several answers)"],
  ["true_false", "True / False"],
  ["numeric", "Numeric"],
  ["short", "Short answer"],
  ["essay", "Written (teacher-marked)"],
];

/** Subject + grade + unit pickers shared by the authoring forms. */
function useScope() {
  const subjects = useApi("/subjects/");
  const [scope, setScope] = useState({ subject: "", grade: "S1", unit: "" });
  const subjectList = useMemo(() => subjects.data || [], [subjects.data]);
  const subject = subjectList.find((s) => String(s.id) === String(scope.subject));
  const units = useApi("/units/", { params: { subject: subject?.code, grade: scope.grade }, skip: !subject });

  useEffect(() => {
    if (!scope.subject && subjectList.length) setScope((s) => ({ ...s, subject: String(subjectList[0].id) }));
  }, [subjectList, scope.subject]);

  const picker = (
    <div className="form-row">
      <label>
        Subject
        <select value={scope.subject} onChange={(e) => setScope({ ...scope, subject: e.target.value, unit: "" })}>
          {subjectList.map((s) => (
            <option key={s.id} value={s.id}>
              {s.icon} {s.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Grade
        <select value={scope.grade} onChange={(e) => setScope({ ...scope, grade: e.target.value, unit: "" })}>
          {GRADES.map((g) => (
            <option key={g}>{g}</option>
          ))}
        </select>
      </label>
      <label>
        Unit
        <select value={scope.unit} onChange={(e) => setScope({ ...scope, unit: e.target.value })}>
          <option value="">—</option>
          {(units.data || []).map((u) => (
            <option key={u.id} value={u.id}>
              {u.number}. {u.title}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
  return { scope, subject, picker, units: units.data || [] };
}

function QuestionForm({ onSaved }) {
  const { t } = useI18n();
  const { scope, picker } = useScope();
  const blank = { type: "mcq", prompt: "", explanation: "", marks: 1, numeric_answer: "", numeric_tolerance: 0, accepted: "", marking_guide: "" };
  const [form, setForm] = useState(blank);
  const [choices, setChoices] = useState([
    { text: "", is_correct: true },
    { text: "", is_correct: false },
  ]);
  const [error, setError] = useState(null);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  function setCorrect(index) {
    setChoices((list) => list.map((c, i) => ({ ...c, is_correct: form.type === "multi" ? (i === index ? !c.is_correct : c.is_correct) : i === index })));
  }

  async function submit(e) {
    e.preventDefault();
    setError(null);
    const body = {
      subject: Number(scope.subject),
      grade: scope.grade,
      unit: scope.unit ? Number(scope.unit) : null,
      type: form.type,
      prompt: form.prompt,
      explanation: form.explanation,
      marks: form.marks,
      marking_guide: form.marking_guide,
    };
    if (form.type === "true_false") body.choices = [{ text: "True", is_correct: form.tf !== "false" }, { text: "False", is_correct: form.tf === "false" }];
    else if (["mcq", "multi"].includes(form.type)) body.choices = choices.filter((c) => c.text.trim());
    if (form.type === "numeric") {
      body.numeric_answer = Number(form.numeric_answer);
      body.numeric_tolerance = Number(form.numeric_tolerance) || 0;
    }
    if (form.type === "short") body.accepted_answers = form.accepted.split("\n").map((s) => s.trim()).filter(Boolean);
    try {
      await api("/questions/", { method: "POST", body });
      setForm({ ...blank, type: form.type });
      setChoices([
        { text: "", is_correct: true },
        { text: "", is_correct: false },
      ]);
      onSaved();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h2>{t("teach.newQuestion")}</h2>
      {picker}
      <div className="form-row">
        <label>
          {t("teach.type")}
          <select value={form.type} onChange={set("type")}>
            {TYPES.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("teach.marks")}
          <input type="number" min="0.5" step="0.5" value={form.marks} onChange={set("marks")} />
        </label>
      </div>
      <label>
        {t("teach.prompt")}
        <textarea rows={3} value={form.prompt} onChange={set("prompt")} required />
      </label>
      {form.prompt && (
        <div className="alert">
          <Markdown interactive={false}>{form.prompt}</Markdown>
        </div>
      )}

      {["mcq", "multi"].includes(form.type) && (
        <fieldset className="stack" style={{ border: 0, padding: 0, margin: 0 }}>
          <legend style={{ fontWeight: 600, fontSize: "0.92rem", marginBottom: 6 }}>{t("teach.choices")}</legend>
          {choices.map((c, i) => (
            <div className="row" key={i} style={{ flexWrap: "nowrap" }}>
              <input
                type={form.type === "multi" ? "checkbox" : "radio"}
                name="correct"
                checked={c.is_correct}
                onChange={() => setCorrect(i)}
                aria-label={`Option ${i + 1} is correct`}
              />
              <input value={c.text} onChange={(e) => setChoices((list) => list.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)))} placeholder={`Option ${i + 1}`} />
              {choices.length > 2 && (
                <button type="button" className="btn btn-sm btn-ghost" onClick={() => setChoices((list) => list.filter((_, j) => j !== i))} aria-label="Remove option">
                  ✕
                </button>
              )}
            </div>
          ))}
          <button type="button" className="btn btn-sm btn-secondary" onClick={() => setChoices((l) => [...l, { text: "", is_correct: false }])}>
            + {t("teach.addChoice")}
          </button>
        </fieldset>
      )}
      {form.type === "true_false" && (
        <label>
          {t("teach.answer")}
          <select value={form.tf || "true"} onChange={set("tf")}>
            <option value="true">True</option>
            <option value="false">False</option>
          </select>
        </label>
      )}
      {form.type === "numeric" && (
        <div className="form-row">
          <label>
            {t("teach.answer")}
            <input type="number" step="any" value={form.numeric_answer} onChange={set("numeric_answer")} required />
          </label>
          <label>
            {t("teach.tolerance")}
            <input type="number" step="any" min="0" value={form.numeric_tolerance} onChange={set("numeric_tolerance")} />
          </label>
        </div>
      )}
      {form.type === "short" && (
        <label>
          {t("teach.accepted")}
          <textarea rows={3} value={form.accepted} onChange={set("accepted")} />
        </label>
      )}
      {["essay", "short"].includes(form.type) && (
        <label>
          {t("teach.markingGuide")}
          <textarea rows={3} value={form.marking_guide} onChange={set("marking_guide")} />
        </label>
      )}
      <label>
        {t("teach.explanation")}
        <textarea rows={2} value={form.explanation} onChange={set("explanation")} />
      </label>
      <ErrorMessage error={error} />
      <button className="btn">{t("common.save")}</button>
    </form>
  );
}

function QuestionBank() {
  const [refresh, setRefresh] = useState(0);
  const state = useApi("/questions/", { params: { mine: 1 } }, [refresh]);
  return (
    <div className="grid-2">
      <QuestionForm onSaved={() => setRefresh((n) => n + 1)} />
      <Loader state={state}>
        {(data) => {
          const list = results(data);
          if (!list.length) return <Empty icon="❓">—</Empty>;
          return (
            <div className="stack">
              {list.map((q) => (
                <div className="card" key={q.id}>
                  <div className="row small muted">
                    <span className="pill">{q.type}</span>
                    <span>
                      {q.subject_code} · {q.grade} · {Number(q.marks)} mark(s)
                    </span>
                  </div>
                  <Markdown interactive={false}>{q.prompt}</Markdown>
                </div>
              ))}
            </div>
          );
        }}
      </Loader>
    </div>
  );
}

function QuizBuilder() {
  const { t } = useI18n();
  const { scope, subject, picker } = useScope();
  const [form, setForm] = useState({
    title: "",
    description: "",
    time_limit_minutes: "",
    max_attempts: "",
    feedback_mode: "immediate",
    kind: "practice",
  });
  // Picked questions belong to the subject and grade they were picked from; changing either starts afresh.
  const scopeKey = `${scope.subject}|${scope.grade}`;
  const [selection, setSelection] = useState({ key: scopeKey, ids: [] });
  const selected = selection.key === scopeKey ? selection.ids : [];
  const setSelected = (update) =>
    setSelection((current) => {
      const ids = current.key === scopeKey ? current.ids : [];
      return { key: scopeKey, ids: typeof update === "function" ? update(ids) : update };
    });
  const [error, setError] = useState(null);
  const [toast, showToast] = useToast();
  const bank = useApi("/questions/", { params: { subject: subject?.code, grade: scope.grade }, skip: !subject });
  const mine = useApi("/quizzes/", { params: { mine: 1 } });

  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      await api("/quizzes/", {
        method: "POST",
        body: {
          ...form,
          subject: Number(scope.subject),
          grade: scope.grade,
          unit: scope.unit ? Number(scope.unit) : null,
          time_limit_minutes: form.time_limit_minutes ? Number(form.time_limit_minutes) : null,
          max_attempts: form.max_attempts ? Number(form.max_attempts) : null,
          status: "published",
          question_ids: selected,
        },
      });
      setSelected([]);
      setForm({ ...form, title: "", description: "" });
      mine.reload();
      showToast(t("common.saved"));
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="grid-2">
      {toast}
      <form className="card form" onSubmit={submit}>
        <h2>{t("teach.newQuiz")}</h2>
        <p className="small muted">{t("teach.reviewNote")}</p>
        {picker}
        <label>
          {t("classes.title.field")}
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        </label>
        <div className="form-row">
          <label>
            {t("classes.type")}
            <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
              <option value="practice">Practice</option>
              <option value="test">Class test</option>
              <option value="mock">Mock exam</option>
            </select>
          </label>
          <label>
            Mode
            <select value={form.feedback_mode} onChange={(e) => setForm({ ...form, feedback_mode: e.target.value })}>
              <option value="immediate">{t("practice.practiceMode")}</option>
              <option value="after_submit">{t("practice.examMode")}</option>
            </select>
          </label>
          <label>
            ⏱ min
            <input type="number" min="1" value={form.time_limit_minutes} onChange={(e) => setForm({ ...form, time_limit_minutes: e.target.value })} placeholder="—" />
          </label>
          <label>
            {t("teach.maxAttempts")}
            <input type="number" min="1" value={form.max_attempts} onChange={(e) => setForm({ ...form, max_attempts: e.target.value })} placeholder="∞" />
          </label>
        </div>
        <div>
          <strong className="small">
            {t("teach.selectQuestions")} ({selected.length})
          </strong>
          <div className="stack" style={{ maxHeight: 360, overflowY: "auto", marginTop: 8 }}>
            {results(bank.data).map((q) => (
              <label key={q.id} className={`option ${selected.includes(q.id) ? "selected" : ""}`}>
                <input
                  type="checkbox"
                  checked={selected.includes(q.id)}
                  onChange={() => setSelected((s) => (s.includes(q.id) ? s.filter((x) => x !== q.id) : [...s, q.id]))}
                />
                <span style={{ minWidth: 0 }}>
                  <span className="pill">{q.type}</span> <Markdown interactive={false}>{q.prompt}</Markdown>
                </span>
              </label>
            ))}
            {!results(bank.data).length && <p className="muted small">—</p>}
          </div>
        </div>
        <ErrorMessage error={error} />
        <button className="btn" disabled={!selected.length}>
          {t("common.create")}
        </button>
      </form>
      <Loader state={mine}>
        {(data) => (
          <div className="stack">
            {results(data).map((q) => (
              <div key={q.id} className="card spread">
                <div>
                  <strong>{q.title}</strong>
                  <div className="small muted">
                    {q.subject.name} · {q.grade} · {q.question_count} Q
                  </div>
                </div>
                <span className={`pill ${q.status === "published" ? "pill-success" : "pill-warn"}`}>{q.status}</span>
              </div>
            ))}
          </div>
        )}
      </Loader>
    </div>
  );
}

function LessonEditor() {
  const { t } = useI18n();
  const { scope, picker } = useScope();
  const [form, setForm] = useState({ title: "", slug: "", summary: "", body: "## Introduction\n\nWrite your lesson here. Use $E = mc^2$ for maths.\n", estimated_minutes: 20 });
  const [slugTouched, setSlugTouched] = useState(false);
  const [preview, setPreview] = useState(false);
  const [error, setError] = useState(null);
  const [toast, showToast] = useToast();
  const mine = useApi("/lessons/", { params: { mine: 1 } });

  async function submit(e) {
    e.preventDefault();
    setError(null);
    if (!scope.unit) {
      setError(new Error("Choose a unit for this lesson."));
      return;
    }
    try {
      await api("/lessons/", { method: "POST", body: { ...form, unit: Number(scope.unit), status: "published" } });
      mine.reload();
      showToast(t("common.saved"));
    } catch (err) {
      setError(err);
    }
  }

  const slugify = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "").slice(0, 80);

  return (
    <div className="stack">
      {toast}
      <form className="card form" onSubmit={submit}>
        <h2>{t("teach.newLesson")}</h2>
        <p className="small muted">{t("teach.reviewNote")}</p>
        {picker}
        <div className="form-row">
          <label>
            {t("classes.title.field")}
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value, slug: slugTouched ? form.slug : slugify(e.target.value) })}
              required
            />
          </label>
          <label>
            {t("teach.slug")}
            <input
              value={form.slug}
              onChange={(e) => {
                setSlugTouched(e.target.value !== "");
                setForm({ ...form, slug: slugify(e.target.value) });
              }}
              required
            />
          </label>
        </div>
        <label>
          {t("teach.summary")}
          <input value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} />
        </label>
        <div className="tabs" style={{ marginBottom: 0 }}>
          <button type="button" className={`tab ${!preview ? "active" : ""}`} onClick={() => setPreview(false)}>
            ✏️ {t("teach.body")}
          </button>
          <button type="button" className={`tab ${preview ? "active" : ""}`} onClick={() => setPreview(true)}>
            👁 {t("teach.preview")}
          </button>
        </div>
        {preview ? (
          <div className="card">
            <Markdown>{form.body}</Markdown>
          </div>
        ) : (
          <textarea rows={16} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} style={{ fontFamily: "var(--mono)", fontSize: "0.9rem" }} />
        )}
        <p className="small muted" style={{ margin: 0 }}>
          Tip: embed a lab with a code block whose language is <code>sim</code> containing the lab name (e.g. <code>projectile-lab</code>), or a live editor with
          <code> playground</code>.
        </p>
        <ErrorMessage error={error} />
        <button className="btn">{t("common.save")}</button>
      </form>
      <Loader state={mine}>
        {(data) => (
          <div className="stack">
            {results(data).map((l) => (
              <div key={l.id} className="card spread">
                <Link to={`/lessons/${l.slug}`}>{l.title}</Link>
                <span className={`pill ${l.status === "published" ? "pill-success" : "pill-warn"}`}>{l.status}</span>
              </div>
            ))}
          </div>
        )}
      </Loader>
    </div>
  );
}

function ResourceForm() {
  const { t } = useI18n();
  const { scope, picker } = useScope();
  const [form, setForm] = useState({ title: "", url: "", kind: "notes", description: "" });
  const [error, setError] = useState(null);
  const [toast, showToast] = useToast();
  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      await api("/resources/", {
        method: "POST",
        body: { ...form, subject: Number(scope.subject), grade: scope.grade, unit: scope.unit ? Number(scope.unit) : null },
      });
      setForm({ title: "", url: "", kind: form.kind, description: "" });
      showToast(t("common.saved"));
    } catch (err) {
      setError(err);
    }
  }
  return (
    <form className="card form" onSubmit={submit} style={{ maxWidth: 640 }}>
      {toast}
      <h2>{t("teach.resources")}</h2>
      <p className="small muted">{t("teach.reviewNote")}</p>
      {picker}
      <div className="form-row">
        <label>
          {t("classes.title.field")}
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        </label>
        <label>
          {t("teach.kind")}
          <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            <option value="notes">Revision notes</option>
            <option value="formula_sheet">Formula sheet</option>
            <option value="video">Video</option>
            <option value="link">Web link</option>
          </select>
        </label>
      </div>
      <label>
        {t("teach.url")}
        <input type="url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} required />
      </label>
      <label>
        {t("teach.summary")}
        <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </label>
      <ErrorMessage error={error} />
      <button className="btn">{t("common.save")}</button>
    </form>
  );
}

export default function Teach() {
  const { t } = useI18n();
  const [tab, setTab] = useState("questions");
  return (
    <>
      <div className="page-header">
        <h1>🧑🏽‍🏫 {t("teach.title")}</h1>
      </div>
      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
          { value: "questions", label: t("teach.questions") },
          { value: "quizzes", label: t("teach.quizzes") },
          { value: "lessons", label: t("teach.lessons") },
          { value: "resources", label: t("teach.resources") },
        ]}
      />
      {tab === "questions" && <QuestionBank />}
      {tab === "quizzes" && <QuizBuilder />}
      {tab === "lessons" && <LessonEditor />}
      {tab === "resources" && <ResourceForm />}
    </>
  );
}
