import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api, results } from "../api";
import { useAuth } from "../auth";
import { LockBadge, LockedNotice } from "../components/Locked";
import { Empty, ErrorMessage, GradeChips, Loader, scoreClass, Tabs } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";
import { SubjectSelect } from "./Labs";

export function useStartQuiz() {
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  async function start(quizId, assignmentId, { replace = false } = {}) {
    setBusy(true);
    setError(null);
    try {
      const attempt = await api(`/quizzes/${quizId}/start/`, {
        method: "POST",
        body: assignmentId ? { assignment: assignmentId } : {},
      });
      navigate(`/attempts/${attempt.id}`, { replace });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return { start, error, busy };
}

function QuizGrid({ subject, grade }) {
  const { t } = useI18n();
  const { start, error, busy } = useStartQuiz();
  const state = useApi("/quizzes/", { params: { subject, grade } });
  return (
    <>
      <ErrorMessage error={error} />
      <Loader state={state}>
        {(data) => {
          const list = results(data);
          if (!list.length) return <Empty icon="📝">—</Empty>;
          return (
            <div className="grid">
              {list.map((q) => {
                const pct = q.my_best != null && q.total_marks ? Math.round((q.my_best / q.total_marks) * 100) : null;
                return (
                  <div key={q.id} className="card subject-card" style={{ "--subject": q.subject.color }}>
                    <div className="spread" style={{ alignItems: "flex-start" }}>
                      <span className="pill">
                        {q.subject.icon} {q.subject.name} · {q.grade}
                      </span>
                      {pct != null && <span className={scoreClass(pct)}>{t("practice.best", { score: `${pct}%` })}</span>}
                    </div>
                    <h3 style={{ margin: "10px 0 4px" }}>{q.title}</h3>
                    <div className="row small muted">
                      <span>{t("practice.questions", { n: q.question_count })}</span>
                      <span>·</span>
                      <span>{q.time_limit_minutes ? `⏱ ${t("practice.timeLimit", { n: q.time_limit_minutes })}` : t("practice.untimed")}</span>
                      <span>·</span>
                      <span>{q.feedback_mode === "immediate" ? t("practice.practiceMode") : t("practice.examMode")}</span>
                    </div>
                    {q.locked ? (
                      <div style={{ marginTop: 12 }}>
                        <LockBadge />
                      </div>
                    ) : (
                      <button className="btn btn-sm" style={{ marginTop: 12 }} disabled={busy} onClick={() => start(q.id)}>
                        {q.my_attempts ? t("quiz.tryAgain") : t("practice.start")} →
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          );
        }}
      </Loader>
    </>
  );
}

function PastPapers({ subject }) {
  const { t } = useI18n();
  const [level, setLevel] = useState("");
  const [year, setYear] = useState("");
  const years = useApi("/exam-papers/years/");
  const state = useApi("/exam-papers/", { params: { level, year, subject } });
  const { start, error, busy } = useStartQuiz();

  return (
    <>
      <p className="small muted">{t("practice.papersNote")}</p>
      <div className="form-row" style={{ marginBottom: 14 }}>
        <label>
          {t("practice.level")}
          <select value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="">{t("practice.all")}</option>
            <option value="O">O-Level (S3)</option>
            <option value="A">A-Level (S6)</option>
          </select>
        </label>
        <label>
          {t("practice.year")}
          <select value={year} onChange={(e) => setYear(e.target.value)}>
            <option value="">{t("practice.all")}</option>
            {(years.data || []).map((y) => (
              <option key={y}>{y}</option>
            ))}
          </select>
        </label>
      </div>
      <ErrorMessage error={error} />
      <Loader state={state}>
        {(data) => {
          const list = results(data);
          if (!list.length) return <Empty icon="📄">{t("practice.noPapers")}</Empty>;
          return (
            <div className="stack">
              {list.map((p) => (
                <div key={p.id} className="card">
                  <div className="spread" style={{ alignItems: "flex-start" }}>
                    <div className="row" style={{ flexWrap: "nowrap", minWidth: 0 }}>
                      <div className="icon-tile" aria-hidden>
                        {p.subject_icon}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <strong>{p.title}</strong>
                        <div className="small muted">
                          {p.level}-Level · {p.year} {p.paper_code && `· ${p.paper_code}`}
                        </div>
                      </div>
                    </div>
                    <span className={p.is_official ? "pill pill-success" : "pill pill-warn"}>
                      {p.is_official ? t("practice.official") : t("practice.sample")}
                    </span>
                  </div>
                  {p.source_note && <p className="small muted" style={{ margin: "10px 0 0" }}>{p.source_note}</p>}
                  {p.locked && (
                    <div style={{ marginTop: 12 }}>
                      <LockedNotice compact />
                    </div>
                  )}
                  <div className="row" style={{ marginTop: 12 }}>
                    {p.quiz && !p.locked && (
                      <button className="btn btn-sm" disabled={busy} onClick={() => start(p.quiz)}>
                        ✍️ {t("practice.takeInteractive")}
                      </button>
                    )}
                    {p.paper_link && (
                      <a className="btn btn-sm btn-secondary" href={p.paper_link} target="_blank" rel="noopener noreferrer">
                        📄 {t("practice.openPaper")}
                      </a>
                    )}
                    {p.marking_guide_link && (
                      <a className="btn btn-sm btn-secondary" href={p.marking_guide_link} target="_blank" rel="noopener noreferrer">
                        ✅ {t("practice.markingGuide")}
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          );
        }}
      </Loader>
    </>
  );
}

export default function Practice() {
  const { user } = useAuth();
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "quizzes";
  const [subject, setSubject] = useState("");
  const [grade, setGrade] = useState(user.grade || "");
  const { start, error } = useStartQuiz();
  const started = useRef(false);

  // Deep links from assignments: /practice?start=<quiz>&assignment=<id>
  useEffect(() => {
    const quiz = params.get("start");
    if (quiz && !started.current) {
      started.current = true;
      // Replace the ?start= entry so Back from the quiz doesn't land here and start it again.
      start(quiz, params.get("assignment"), { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <div className="page-header">
        <h1>📝 {t("nav.practice")}</h1>
      </div>
      <ErrorMessage error={error} />
      <Tabs
        value={tab}
        onChange={(value) => setParams({ tab: value })}
        tabs={[
          { value: "quizzes", label: t("practice.quizzes") },
          { value: "papers", label: t("practice.pastPapers") },
        ]}
      />
      <div className="form-row" style={{ marginBottom: 12 }}>
        <SubjectSelect value={subject} onChange={setSubject} />
      </div>
      {tab === "quizzes" ? (
        <>
          <GradeChips value={grade} onChange={setGrade} allowAll />
          <div style={{ marginTop: 16 }}>
            <QuizGrid subject={subject} grade={grade} />
          </div>
        </>
      ) : (
        <PastPapers subject={subject} />
      )}
    </>
  );
}
