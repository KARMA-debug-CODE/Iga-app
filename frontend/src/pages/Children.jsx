import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { Icon, SubjectIcon } from "../components/Icon";
import { Empty, ErrorMessage, Loader, Progress, scoreClass } from "../components/ui";
import { formatDate, useApi } from "../hooks";
import { useI18n } from "../i18n";

function LinkChild({ onLinked }) {
  const { t } = useI18n();
  const [code, setCode] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/children/", { method: "POST", body: { code } });
      setCode("");
      onLinked();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="card form" onSubmit={submit}>
      <h2>{t("parent.link")}</h2>
      <p className="small muted" style={{ margin: 0 }}>
        {t("parent.linkHelp")}
      </p>
      <label>
        {t("parent.code")}
        <input
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          maxLength={12}
          required
          placeholder="ABCD2345"
          style={{ fontFamily: "var(--mono)", letterSpacing: "0.15em", fontSize: "1.2rem" }}
        />
      </label>
      <ErrorMessage error={error} />
      <button className="btn" disabled={busy}>
        {t("parent.linkButton")}
      </button>
    </form>
  );
}

/** Dashboard for parent/guardian accounts. */
export function ParentDashboard() {
  const { t } = useI18n();
  const state = useApi("/children/");
  return (
    <div className="grid-2">
      <div>
        <h2>{t("parent.children")}</h2>
        <Loader state={state}>
          {(children) =>
            children.length === 0 ? (
              <Empty icon="users">{t("parent.none")}</Empty>
            ) : (
              <div className="stack">
                {children.map((c) => (
                  <Link key={c.id} to={`/children/${c.id}`} className="card card-link">
                    <div className="spread">
                      <strong>
                        {c.name} · {c.grade}
                      </strong>
                      <span className="pill pill-warn">
                        <Icon name="flame" size={14} /> {t("dash.streak", { n: c.streak_days })}
                      </span>
                    </div>
                    <div className="stats stats-3" style={{ marginTop: 12 }}>
                      <div className="stat">
                        <strong>{c.level}</strong>
                        <span className="small muted">{t("parent.level")}</span>
                      </div>
                      <div className="stat">
                        <strong>{c.lessons_this_week}</strong>
                        <span className="small muted">{t("parent.lessonsWeek")}</span>
                      </div>
                      <div className="stat">
                        <strong>{c.latest_result?.percentage != null ? `${Math.round(c.latest_result.percentage)}%` : "—"}</strong>
                        <span className="small muted">{t("parent.latest")}</span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )
          }
        </Loader>
      </div>
      <LinkChild onLinked={state.reload} />
    </div>
  );
}

/** Read-only progress report for one linked child. */
export default function ChildReport() {
  const { id } = useParams();
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const state = useApi(`/children/${id}/`);

  async function unlink() {
    if (!window.confirm(t("parent.unlinkConfirm"))) return;
    await api(`/children/${id}/`, { method: "DELETE" });
    navigate("/");
  }

  return (
    <Loader state={state}>
      {(child) => (
        <>
          <div className="breadcrumb">
            <Link to="/">{t("nav.home")}</Link> <span>›</span> <span>{child.name}</span>
          </div>
          <div className="page-header spread">
            <div>
              <h1 style={{ margin: 0 }}>{child.name}</h1>
              <p>
                {child.grade} {child.school && `· ${child.school}`} · {t("parent.lastActive")}: {child.last_active || "—"}
              </p>
            </div>
            <button className="btn btn-sm btn-danger" onClick={unlink}>
              {t("parent.unlink")}
            </button>
          </div>

          <div className="stats">
            <div className="card stat">
              <strong>{child.level}</strong>
              <span className="small muted">
                {t("parent.level")} · {child.xp} XP
              </span>
            </div>
            <div className="card stat">
              <strong className="with-icon">
                <Icon name="flame" size={22} style={{ color: "var(--warn)" }} /> {child.streak_days}
              </strong>
              <span className="small muted">{t("parent.streak")}</span>
            </div>
            <div className="card stat">
              <strong>{child.lessons_this_week}</strong>
              <span className="small muted">{t("parent.lessonsWeek")}</span>
            </div>
            <div className="card stat">
              <strong>{child.badges.length}</strong>
              <span className="small muted">{t("dash.badges")}</span>
            </div>
          </div>

          <div className="grid-2 section">
            <div className="card">
              <h2>{t("parent.subjects")}</h2>
              {child.subjects.filter((s) => s.lessons > 0).length === 0 ? (
                <p className="muted">—</p>
              ) : (
                <ul className="list">
                  {child.subjects
                    .filter((s) => s.lessons > 0)
                    .map((s) => (
                      <li key={s.code}>
                        <div className="spread small">
                          <span className="with-icon">
                            <SubjectIcon name={s.icon} size={16} /> {s.name}
                          </span>
                          <span className="muted">
                            {s.completed}/{s.lessons}
                          </span>
                        </div>
                        <div style={{ marginTop: 6 }}>
                          <Progress value={s.completed} max={s.lessons} label={s.name} />
                        </div>
                      </li>
                    ))}
                </ul>
              )}
            </div>
            <div className="card">
              <h2>{t("dash.recentScores")}</h2>
              {child.recent_results.length === 0 ? (
                <p className="muted">—</p>
              ) : (
                <ul className="list">
                  {child.recent_results.map((r, i) => (
                    <li key={i} className="spread">
                      <span style={{ minWidth: 0 }}>
                        <span className="with-icon">
                          <SubjectIcon name={r.icon} size={16} /> {r.quiz}
                        </span>
                        <div className="small muted">{formatDate(r.submitted_at, lang)}</div>
                      </span>
                      <span className={scoreClass(r.percentage)}>
                        {r.percentage != null ? `${Math.round(r.percentage)}%` : t("classes.state.needs_marking")}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="card section">
            <h2>{t("classes.assignments")}</h2>
            {child.assignments.length === 0 ? (
              <p className="muted">—</p>
            ) : (
              <ul className="list">
                {child.assignments.map((a, i) => (
                  <li key={i} className="spread">
                    <span style={{ minWidth: 0 }}>
                      <strong>{a.title}</strong>
                      <div className="small muted">
                        {a.classroom} · {a.due_at ? t("classes.due", { date: formatDate(a.due_at, lang) }) : t("classes.noDue")}
                      </div>
                    </span>
                    <span className="row">
                      {a.status.score != null ? (
                        <span className={scoreClass(a.status.score)}>{Math.round(a.status.score)}%</span>
                      ) : (
                        <span className="pill">{t(`classes.state.${a.status.state}`)}</span>
                      )}
                      {a.status.late && <span className="pill pill-danger">{t("classes.late")}</span>}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </Loader>
  );
}
