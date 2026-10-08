import { useState } from "react";
import { Link } from "react-router-dom";

import { api, results } from "../api";
import { useAuth } from "../auth";
import { Icon } from "../components/Icon";
import { Empty, ErrorMessage, GRADES, Loader } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";
import { SubjectSelect } from "./Labs";

function JoinClass({ onJoined }) {
  const { t } = useI18n();
  const [code, setCode] = useState("");
  const [error, setError] = useState(null);
  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      await api("/classes/join/", { method: "POST", body: { code } });
      setCode("");
      onJoined();
    } catch (err) {
      setError(err);
    }
  }
  return (
    <form className="card form" onSubmit={submit}>
      <h2>{t("classes.join")}</h2>
      <label>
        {t("classes.joinCode")}
        <input
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          maxLength={8}
          required
          style={{ fontFamily: "var(--mono)", letterSpacing: "0.2em", fontSize: "1.3rem" }}
          placeholder="ABC234"
        />
      </label>
      <ErrorMessage error={error} />
      <button className="btn">{t("groups.join")}</button>
    </form>
  );
}

function CreateClass({ onCreated }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ name: "", grade: "S1", subject: "" });
  const [error, setError] = useState(null);
  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      const subjects = await api("/subjects/");
      const subject = subjects.find((s) => s.code === form.subject);
      await api("/classes/", { method: "POST", body: { name: form.name, grade: form.grade, subject: subject?.id ?? null } });
      setForm({ name: "", grade: form.grade, subject: form.subject });
      onCreated();
    } catch (err) {
      setError(err);
    }
  }
  return (
    <form className="card form" onSubmit={submit}>
      <h2>{t("classes.create")}</h2>
      <label>
        {t("classes.name")}
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
      </label>
      <div className="form-row">
        <label>
          {t("auth.grade")}
          <select value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value })}>
            {GRADES.map((g) => (
              <option key={g}>{g}</option>
            ))}
          </select>
        </label>
        <SubjectSelect value={form.subject} onChange={(subject) => setForm({ ...form, subject })} />
      </div>
      <ErrorMessage error={error} />
      <button className="btn">{t("common.create")}</button>
    </form>
  );
}

function ClassCard({ c }) {
  const { t } = useI18n();
  return (
    <Link to={`/classes/${c.id}`} className="card card-link">
      <div className="row" style={{ flexWrap: "nowrap" }}>
        <div className="icon-tile">
          <Icon name={c.subject_icon || "classes"} size={22} />
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <strong>{c.name}</strong>
          <div className="small muted">
            {c.grade} · {c.subject_name || ""} · {t("classes.teacher", { name: c.teacher_name })}
          </div>
        </div>
        {c.join_code && <span className="pill pill-blue">{c.join_code}</span>}
      </div>
    </Link>
  );
}

/** Classes a student was in before they changed level; they stay readable but no longer count. */
function PreviousClasses() {
  const { t } = useI18n();
  const state = useApi("/classes/", { params: { previous: 1 } });
  const list = results(state.data);
  if (!list.length) return null;
  return (
    <details className="card previous-classes">
      <summary>
        <strong>{t("classes.previous", { n: list.length })}</strong>
        <div className="small muted">{t("classes.previousHelp")}</div>
      </summary>
      <div className="stack" style={{ marginTop: 12 }}>
        {list.map((c) => (
          <ClassCard key={c.id} c={c} />
        ))}
      </div>
    </details>
  );
}

export default function Classes() {
  const { user, isTeacher } = useAuth();
  const { t } = useI18n();
  const state = useApi("/classes/");
  return (
    <>
      <div className="page-header">
        <h1 className="title-with-icon">
          <Icon name="classes" size={28} /> {t("classes.title")}
        </h1>
        {!isTeacher && user?.grade && <p className="muted">{t("classes.forGrade", { grade: user.grade })}</p>}
      </div>
      <div className="grid-2">
        <div className="stack" style={{ alignContent: "start" }}>
          <Loader state={state}>
            {(data) => {
              const list = results(data);
              if (!list.length) return <Empty icon="classes">{t("classes.empty")}</Empty>;
              return (
                <div className="stack">
                  {list.map((c) => (
                    <ClassCard key={c.id} c={c} />
                  ))}
                </div>
              );
            }}
          </Loader>
          {!isTeacher && <PreviousClasses />}
        </div>
        <div>{isTeacher ? <CreateClass onCreated={state.reload} /> : <JoinClass onJoined={state.reload} />}</div>
      </div>
    </>
  );
}
