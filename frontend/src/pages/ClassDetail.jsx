import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, results } from "../api";
import { useAuth } from "../auth";
import { Empty, ErrorMessage, Loader, scoreClass, Tabs } from "../components/ui";
import { formatDate, useApi } from "../hooks";
import { useI18n } from "../i18n";

function NewAssignment({ classroom, onCreated }) {
  const { t } = useI18n();
  const [kind, setKind] = useState("quiz");
  const [form, setForm] = useState({ title: "", instructions: "", target: "", due_at: "" });
  const [error, setError] = useState(null);
  const subject = classroom.subject_code;
  const quizzes = useApi("/quizzes/", { params: { grade: classroom.grade, subject } });
  const lessons = useApi("/lessons/", { params: { grade: classroom.grade, subject } });
  const sims = useApi("/simulations/", { params: { grade: classroom.grade } });

  const options =
    kind === "quiz"
      ? results(quizzes.data).map((q) => ({ id: q.id, label: q.title }))
      : kind === "lesson"
        ? results(lessons.data).map((l) => ({ id: l.id, label: `${l.subject} · ${l.title}` }))
        : results(sims.data).map((s) => ({ id: s.id, label: s.title }));

  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      await api("/assignments/", {
        method: "POST",
        body: {
          classroom: classroom.id,
          title: form.title || options.find((o) => String(o.id) === String(form.target))?.label || "Assignment",
          instructions: form.instructions,
          [kind]: Number(form.target),
          due_at: form.due_at ? new Date(form.due_at).toISOString() : null,
        },
      });
      setForm({ title: "", instructions: "", target: "", due_at: "" });
      onCreated();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h2>{t("classes.newAssignment")}</h2>
      <div className="chips">
        {["quiz", "lesson", "simulation"].map((k) => (
          <button type="button" key={k} className={`chip ${kind === k ? "active" : ""}`} onClick={() => { setKind(k); setForm((f) => ({ ...f, target: "" })); }}>
            {{ quiz: "📝 Quiz", lesson: "📖 Lesson", simulation: "🔬 Lab" }[k]}
          </button>
        ))}
      </div>
      <label>
        {t("classes.pick")}
        <select value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })} required>
          <option value="">{t("classes.pick")}</option>
          {options.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t("classes.title.field")} <span className="muted small">({t("common.optional")})</span>
        <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
      </label>
      <label>
        {t("classes.instructions")}
        <textarea rows={3} value={form.instructions} onChange={(e) => setForm({ ...form, instructions: e.target.value })} />
      </label>
      <label>
        {t("classes.dueDate")}
        <input type="datetime-local" value={form.due_at} onChange={(e) => setForm({ ...form, due_at: e.target.value })} />
      </label>
      <ErrorMessage error={error} />
      <button className="btn">{t("common.create")}</button>
    </form>
  );
}

function Report({ id }) {
  const { t } = useI18n();
  const state = useApi(`/classes/${id}/report/`);
  return (
    <Loader state={state}>
      {(report) => (
        <>
          {report.weak_units.length > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <h3>📉 {t("classes.weakUnits")}</h3>
              <ul className="list">
                {report.weak_units.map((u) => (
                  <li key={u.unit} className="spread">
                    <span>{u.unit}</span>
                    <span className={scoreClass(u.average)}>{u.average}%</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {report.rows.length === 0 ? (
            <Empty icon="👩🏽‍🎓">{t("classes.share")}</Empty>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("marking.student")}</th>
                    {report.assignments.map((a) => (
                      <th key={a.id} title={a.title}>
                        {a.title.length > 18 ? `${a.title.slice(0, 16)}…` : a.title}
                      </th>
                    ))}
                    <th>{t("classes.average")}</th>
                    <th>📖</th>
                  </tr>
                </thead>
                <tbody>
                  {report.rows.map((row) => (
                    <tr key={row.student.id}>
                      <td>
                        <strong>{row.student.display_name}</strong>
                        <div className="small muted">{row.student.xp} XP</div>
                      </td>
                      {report.assignments.map((a) => {
                        const cell = row.assignments[a.id];
                        return (
                          <td key={a.id}>
                            {cell.score != null ? (
                              <span className={scoreClass(cell.score)}>{cell.score}%</span>
                            ) : (
                              <span className={`pill ${cell.state === "done" ? "pill-success" : ""}`}>{t(`classes.state.${cell.state}`)}</span>
                            )}
                            {cell.late && <span className="pill pill-danger" style={{ marginLeft: 4 }}>{t("classes.late")}</span>}
                          </td>
                        );
                      })}
                      <td>{row.average_score != null ? <span className={scoreClass(row.average_score)}>{row.average_score}%</span> : "—"}</td>
                      <td>{row.lessons_completed}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </Loader>
  );
}

export default function ClassDetail() {
  const { id } = useParams();
  const { user, isTeacher } = useAuth();
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const [tab, setTab] = useState("assignments");
  const [actionError, setActionError] = useState(null);
  const state = useApi(`/classes/${id}/`);
  const subjects = useApi("/subjects/");

  return (
    <Loader state={state}>
      {(c) => {
        const owner = isTeacher && c.join_code;
        const subjectCode = (subjects.data || []).find((s) => s.id === c.subject)?.code;
        return (
          <>
            <div className="breadcrumb">
              <Link to="/classes">{t("classes.title")}</Link> <span>›</span> <span>{c.name}</span>
            </div>
            <div className="page-header spread">
              <div>
                <h1 style={{ margin: 0 }}>
                  {c.subject_icon} {c.name}
                </h1>
                <p>
                  {c.grade} · {c.subject_name || ""} · {t("classes.teacher", { name: c.teacher_name })}
                </p>
              </div>
              {owner && (
                <div>
                  <div className="small muted">{t("classes.share")}</div>
                  <span className="code-display">{c.join_code}</span>
                </div>
              )}
            </div>

            {owner && (
              <Tabs
                value={tab}
                onChange={setTab}
                tabs={[
                  { value: "assignments", label: t("classes.assignments") },
                  { value: "report", label: t("classes.report") },
                  { value: "students", label: `${t("classes.students")} (${c.students?.length || 0})` },
                ]}
              />
            )}

            {tab === "assignments" && (
              <div className={owner ? "grid-2" : ""}>
                <div className="stack">
                  {c.assignments.length === 0 && <Empty icon="📭">—</Empty>}
                  {c.assignments.map((a) => (
                    <div className="card" key={a.id}>
                      <div className="spread">
                        <strong>
                          {{ quiz: "📝", lesson: "📖", simulation: "🔬" }[a.kind]} {a.title}
                        </strong>
                        {a.my_status &&
                          (a.my_status.score != null ? (
                            <span className={scoreClass(a.my_status.score)}>{a.my_status.score}%</span>
                          ) : (
                            <span className="pill">{t(`classes.state.${a.my_status.state}`)}</span>
                          ))}
                      </div>
                      {a.instructions && <p className="small" style={{ margin: "6px 0" }}>{a.instructions}</p>}
                      <div className="spread small muted" style={{ marginTop: 6 }}>
                        <span>{a.due_at ? t("classes.due", { date: formatDate(a.due_at, lang) }) : t("classes.noDue")}</span>
                        {owner && a.quiz && (
                          <Link className="btn btn-sm btn-secondary" to={`/classes/${id}/quizzes/${a.quiz}/analytics`}>
                            📊 {t("analytics.title")}
                          </Link>
                        )}
                        {user.role === "student" && (
                          <button
                            className="btn btn-sm"
                            onClick={() =>
                              navigate(
                                a.quiz ? `/practice?start=${a.quiz}&assignment=${a.id}` : a.lesson_slug ? `/lessons/${a.lesson_slug}` : `/labs/${a.simulation_slug}`,
                              )
                            }
                          >
                            {t("practice.start")} →
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                {owner && <NewAssignment classroom={{ ...c, subject_code: subjectCode }} onCreated={state.reload} />}
              </div>
            )}

            {tab === "report" && owner && <Report id={id} />}

            {tab === "students" && owner && (
              <div className="card">
                <ErrorMessage error={actionError} />
                <ul className="list">
                  {(c.students || []).map((s) => (
                    <li key={s.id} className="spread">
                      <span>
                        <strong>{s.display_name}</strong> <span className="muted small">@{s.username}</span>
                      </span>
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={async () => {
                          if (!window.confirm(t("classes.removeConfirm", { name: s.display_name }))) return;
                          setActionError(null);
                          try {
                            await api(`/classes/${id}/remove_student/`, { method: "POST", body: { student: s.id } });
                            state.reload();
                          } catch (err) {
                            setActionError(err);
                          }
                        }}
                      >
                        {t("classes.remove")}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        );
      }}
    </Loader>
  );
}
