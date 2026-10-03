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
  const [form, setForm] = useState({
    title: "",
    instructions: "",
    target: "",
    due_at: "",
  });
  const [error, setError] = useState(null);
  const subject = classroom.subject_code;
  const quizzes = useApi("/quizzes/", {
    params: { grade: classroom.grade, subject },
  });
  const lessons = useApi("/lessons/", {
    params: { grade: classroom.grade, subject },
  });
  const sims = useApi("/simulations/", { params: { grade: classroom.grade } });

  const options =
    kind === "quiz"
      ? results(quizzes.data).map((q) => ({ id: q.id, label: q.title }))
      : kind === "lesson"
        ? results(lessons.data).map((l) => ({
            id: l.id,
            label: `${l.subject} · ${l.title}`,
          }))
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
          <button
            type="button"
            key={k}
            className={`chip ${kind === k ? "active" : ""}`}
            onClick={() => {
              setKind(k);
              setForm((f) => ({ ...f, target: "" }));
            }}
          >
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
                              <span className={`pill ${cell.state === "done" ? "pill-success" : ""}`}>
                                {t(`classes.state.${cell.state}`)}
                              </span>
                            )}
                            {cell.late && (
                              <span className="pill pill-danger" style={{ marginLeft: 4 }}>
                                {t("classes.late")}
                              </span>
                            )}
                          </td>
                        );
                      })}
                      <td>
                        {row.average_score != null ? <span className={scoreClass(row.average_score)}>{row.average_score}%</span> : "—"}
                      </td>
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

function downloadCsv(filename, rows) {
  const escape = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const text = rows.map((r) => r.map(escape).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob(["\ufeff" + text], { type: "text/csv;charset=utf-8" }));
  const a = Object.assign(document.createElement("a"), {
    href: url,
    download: filename,
  });
  a.click();
  URL.revokeObjectURL(url);
}

function RosterImport({ classroom, onCreated }) {
  const { t } = useI18n();
  const [text, setText] = useState("");
  const [preview, setPreview] = useState(null);
  const [created, setCreated] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function send(confirm) {
    setBusy(true);
    setError(null);
    try {
      const data = await api(`/classes/${classroom.id}/import_roster/`, {
        method: "POST",
        body: { csv: text, confirm },
      });
      if (data.created) {
        setCreated(data.created);
        setPreview(null);
        setText("");
        onCreated();
      } else {
        setPreview(data);
      }
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function readFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setText(await file.text());
    setPreview(null);
  }

  if (created) {
    return (
      <div className="card stack">
        <div className="alert alert-success">{t("roster.done", { n: created.length })}</div>
        <div className="alert alert-warn">{t("roster.once")}</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">{t("marking.student")}</th>
                <th scope="col">{t("roster.temporary")}</th>
              </tr>
            </thead>
            <tbody>
              {created.map((r) => (
                <tr key={r.username}>
                  <td>
                    {r.first_name} {r.last_name}
                    <div className="small muted">@{r.username}</div>
                  </td>
                  <td>
                    <code style={{ fontSize: "1rem" }}>{r.temporary_password}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="row">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() =>
              downloadCsv(`${classroom.name}-accounts.csv`, [
                ["first_name", "last_name", "username", "temporary_password"],
                ...created.map((r) => [r.first_name, r.last_name, r.username, r.temporary_password]),
              ])
            }
          >
            ⬇ {t("roster.download")}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => window.print()}>
            🖨 {t("roster.print")}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setCreated(null)}>
            {t("common.close")}
          </button>
        </div>
      </div>
    );
  }

  const bad = preview && !preview.valid;
  return (
    <details className="card">
      <summary>
        <strong>➕ {t("roster.title")}</strong>
      </summary>
      <div className="form" style={{ marginTop: 12 }}>
        <p className="small muted">{t("roster.help")}</p>
        <label className="btn btn-secondary btn-sm" style={{ alignSelf: "flex-start" }}>
          📄 {t("roster.file")}
          <input type="file" accept=".csv,text/csv,text/plain" onChange={readFile} hidden />
        </label>
        <textarea
          rows={6}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setPreview(null);
          }}
          placeholder={"first_name,last_name\nAline,Uwase\nEric,Niyonzima"}
          aria-label={t("roster.title")}
          style={{ fontFamily: "var(--mono)" }}
        />
        <ErrorMessage error={error} />
        {preview && (
          <>
            {bad && <div className="alert alert-error">{t("roster.problems")}</div>}
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th scope="col">{t("roster.line")}</th>
                    <th scope="col">{t("marking.student")}</th>
                    <th scope="col">{t("auth.username")}</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((r) => (
                    <tr key={r.line} className={r.errors.length ? "row-error" : ""}>
                      <td>{r.line}</td>
                      <td>
                        {r.first_name} {r.last_name}
                        {r.errors.map((err) => (
                          <div key={err} className="small" style={{ color: "var(--danger)" }}>
                            ⚠ {err}
                          </div>
                        ))}
                      </td>
                      <td>{r.username}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        <div className="row">
          <button className="btn btn-secondary" disabled={busy || !text.trim()} onClick={() => send(false)}>
            {t("roster.preview")}
          </button>
          {preview?.valid && (
            <button className="btn" disabled={busy} onClick={() => send(true)}>
              {t("roster.create", { n: preview.rows.length })}
            </button>
          )}
        </div>
      </div>
    </details>
  );
}

export default function ClassDetail() {
  const { id } = useParams();
  const { user, isTeacher } = useAuth();
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const [tab, setTab] = useState("assignments");
  const [actionError, setActionError] = useState(null);
  const [notice, setNotice] = useState(null);
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
                  {
                    value: "students",
                    label: `${t("classes.students")} (${c.students?.length || 0})`,
                  },
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
                      {a.instructions && (
                        <p className="small" style={{ margin: "6px 0" }}>
                          {a.instructions}
                        </p>
                      )}
                      <div className="spread small muted" style={{ marginTop: 6 }}>
                        <span>
                          {a.due_at
                            ? t("classes.due", {
                                date: formatDate(a.due_at, lang),
                              })
                            : t("classes.noDue")}
                        </span>
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
                                a.quiz
                                  ? `/practice?start=${a.quiz}&assignment=${a.id}`
                                  : a.lesson_slug
                                    ? `/lessons/${a.lesson_slug}`
                                    : `/labs/${a.simulation_slug}`,
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
              <div className="stack">
                <RosterImport classroom={c} onCreated={state.reload} />
                <div className="card">
                  <ErrorMessage error={actionError} />
                  {notice && (
                    <div className="alert alert-success" role="status">
                      {notice}
                    </div>
                  )}
                  <ul className="list">
                    {(c.students || []).map((s) => (
                      <li key={s.id} className="spread">
                        <span>
                          <strong>{s.display_name}</strong> <span className="muted small">@{s.username}</span>
                          {s.awaiting_first_login && (
                            <span className="pill" style={{ marginLeft: 6 }}>
                              {t("roster.awaiting")}
                            </span>
                          )}
                        </span>
                        <span className="row" style={{ gap: 6 }}>
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={async () => {
                              if (
                                !window.confirm(
                                  t("roster.resetConfirm", {
                                    name: s.display_name,
                                  }),
                                )
                              )
                                return;
                              setActionError(null);
                              try {
                                const r = await api(`/classes/${id}/reset_password/`, { method: "POST", body: { student: s.id } });
                                setNotice(
                                  t("roster.resetDone", {
                                    username: r.username,
                                    password: r.temporary_password,
                                  }),
                                );
                                state.reload();
                              } catch (err) {
                                setActionError(err);
                              }
                            }}
                          >
                            🔑 {t("roster.reset")}
                          </button>
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={async () => {
                              if (
                                !window.confirm(
                                  t("classes.removeConfirm", {
                                    name: s.display_name,
                                  }),
                                )
                              )
                                return;
                              setActionError(null);
                              try {
                                await api(`/classes/${id}/remove_student/`, {
                                  method: "POST",
                                  body: { student: s.id },
                                });
                                state.reload();
                              } catch (err) {
                                setActionError(err);
                              }
                            }}
                          >
                            {t("classes.remove")}
                          </button>
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </>
        );
      }}
    </Loader>
  );
}
