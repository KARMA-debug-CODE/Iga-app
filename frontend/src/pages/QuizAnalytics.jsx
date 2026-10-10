// Item analysis for a quiz: how a class did overall and question by question.
// Charts are plain HTML (bars are divs) with a table view of the same numbers,
// so they work with screen readers, print well, and need no chart library.
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Icon } from "../components/Icon";
import Markdown from "../components/Markdown";
import { Empty, Loader } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

function pct(value) {
  return value == null ? "—" : `${Math.round(value)}%`;
}

// Discrimination index: how much better the top 27% did on a question than the bottom 27%.
function discriminationLabel(d) {
  if (d == null) return null;
  if (d < 0) return { key: "analytics.d.negative", tone: "pill-danger" };
  if (d < 0.2) return { key: "analytics.d.weak", tone: "pill-warn" };
  if (d < 0.3) return { key: "analytics.d.fair", tone: "" };
  return { key: "analytics.d.good", tone: "pill-success" };
}

function ViewToggle({ table, onChange }) {
  const { t } = useI18n();
  return (
    <button type="button" className="btn btn-ghost btn-sm" aria-pressed={table} onClick={() => onChange(!table)}>
      <Icon name={table ? "chart" : "table"} size={16} /> {table ? t("analytics.showChart") : t("analytics.showTable")}
    </button>
  );
}

function Histogram({ bins, total }) {
  const { t } = useI18n();
  const [table, setTable] = useState(false);
  const max = Math.max(1, ...bins.map((b) => b.count));
  const label = (b) => t("analytics.binLabel", { from: b.from, to: b.to, n: b.count });
  return (
    <section className="card">
      <div className="spread">
        <h2 style={{ margin: 0 }}>{t("analytics.distribution")}</h2>
        <ViewToggle table={table} onChange={setTable} />
      </div>
      {table ? (
        <div className="table-wrap" style={{ marginTop: 12 }}>
          <table>
            <thead>
              <tr>
                <th scope="col">{t("analytics.score")}</th>
                <th scope="col">{t("analytics.students")}</th>
              </tr>
            </thead>
            <tbody>
              {bins.map((b) => (
                <tr key={b.from}>
                  <td>
                    {b.from}–{b.to}%
                  </td>
                  <td>{b.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <figure className="histogram" aria-label={t("analytics.distributionOf", { n: total })}>
          <div className="histogram-plot">
            <span className="histogram-max small muted">{max}</span>
            {bins.map((b) => (
              <div key={b.from} className="histogram-col" tabIndex={0} role="img" aria-label={label(b)} data-tip={label(b)}>
                <div className="chart-bar-v" style={{ height: `${(b.count / max) * 100}%` }} />
              </div>
            ))}
          </div>
          <div className="histogram-axis small muted" aria-hidden>
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
        </figure>
      )}
    </section>
  );
}

function Bar({ value, max = 100, tone = "", label }) {
  const width = max ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div className="chart-row" data-tip={label}>
      <div className="chart-track">
        <div className={`chart-bar-h ${tone}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function OptionBreakdown({ question }) {
  const { t } = useI18n();
  const total = question.choices.reduce((sum, c) => sum + c.count, 0);
  return (
    <div className="stack" style={{ gap: 6, marginTop: 8 }}>
      {question.choices.map((c) => {
        const share = total ? Math.round((c.count / total) * 100) : 0;
        const label = t("analytics.optionLabel", { n: c.count, pct: share });
        return (
          <div key={c.id} className="option-stat">
            <div className="spread small">
              <span className="option-stat-text">
                {c.is_correct && (
                  <span className="pill pill-success">
                    <Icon name="check" size={14} /> {t("analytics.correct")}
                  </span>
                )}{" "}
                <Markdown interactive={false}>{c.text}</Markdown>
              </span>
              <span className="muted">{label}</span>
            </div>
            <Bar value={c.count} max={total} tone={c.is_correct ? "is-correct" : ""} label={label} />
          </div>
        );
      })}
    </div>
  );
}

function QuestionRow({ q, hardest }) {
  const { t } = useI18n();
  const d = discriminationLabel(q.discrimination);
  return (
    <li className="card question-stat">
      <div className="spread small muted">
        <span>
          {t("analytics.question", { n: q.number })} · {t("quiz.marks", { n: Number(q.marks) })}
          {hardest && (
            <span className="pill pill-warn" style={{ marginLeft: 6 }}>
              {t("analytics.hard")}
            </span>
          )}
        </span>
        {q.pending_marking > 0 && <span className="pill">{t("analytics.pending", { n: q.pending_marking })}</span>}
      </div>
      <div className="question-stat-prompt">
        <Markdown interactive={false}>{q.prompt}</Markdown>
      </div>
      <div className="spread small">
        <span>{t("analytics.average")}</span>
        <strong>{pct(q.average_pct)}</strong>
      </div>
      <Bar value={q.average_pct ?? 0} label={`${t("analytics.average")}: ${pct(q.average_pct)}`} />
      <div className="row small" style={{ marginTop: 8, gap: 8 }}>
        <span className="muted">
          {t("analytics.fullMarks")}: <strong>{pct(q.full_marks_pct)}</strong>
        </span>
        {d && (
          <span className={`pill ${d.tone}`} title={t("analytics.dHelp")}>
            {t(d.key)} ({q.discrimination})
          </span>
        )}
      </div>
      {q.choices.length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary className="small">{t("analytics.options")}</summary>
          <OptionBreakdown question={q} />
        </details>
      )}
    </li>
  );
}

function QuestionTable({ questions }) {
  const { t } = useI18n();
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">{t("analytics.average")}</th>
            <th scope="col">{t("analytics.fullMarks")}</th>
            <th scope="col">{t("analytics.discrimination")}</th>
            <th scope="col">{t("analytics.marked")}</th>
          </tr>
        </thead>
        <tbody>
          {questions.map((q) => (
            <tr key={q.id}>
              <th scope="row">{q.number}</th>
              <td>{pct(q.average_pct)}</td>
              <td>{pct(q.full_marks_pct)}</td>
              <td>{q.discrimination ?? "—"}</td>
              <td>
                {q.marked}
                {q.pending_marking ? ` (+${q.pending_marking})` : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function QuizAnalytics() {
  const { id: classroomId, quizId } = useParams();
  const { t } = useI18n();
  const [table, setTable] = useState(false);
  const state = useApi(`/quizzes/${quizId}/analytics/`, { params: { classroom: classroomId } }, [quizId, classroomId]);

  return (
    <Loader state={state}>
      {(data) => {
        const hardest = new Set(data.hardest);
        return (
          <>
            <div className="breadcrumb">
              {data.classroom ? (
                <>
                  <Link to="/classes">{t("classes.title")}</Link> <span>›</span>{" "}
                  <Link to={`/classes/${data.classroom.id}`}>{data.classroom.name}</Link>
                </>
              ) : (
                <Link to="/teach">{t("nav.teach")}</Link>
              )}{" "}
              <span>›</span> <span>{t("analytics.title")}</span>
            </div>
            <div className="page-header">
              <h1 className="title-with-icon">
                <Icon name="chart" size={28} /> {data.quiz.title}
              </h1>
              <p>
                {data.quiz.subject} · {data.quiz.grade}
              </p>
            </div>

            <div className="stats stats-3">
              <div className="card stat">
                <strong>
                  {data.students_attempted}
                  {data.classroom ? ` / ${data.classroom.students}` : ""}
                </strong>
                <span className="small muted">{t("analytics.attempted")}</span>
              </div>
              <div className="card stat">
                <strong>{pct(data.average_pct)}</strong>
                <span className="small muted">{t("analytics.average")}</span>
              </div>
              <div className="card stat">
                <strong>{pct(data.median_pct)}</strong>
                <span className="small muted">{t("analytics.median")}</span>
              </div>
            </div>
            <p className="small muted">{t("analytics.firstAttemptNote")}</p>

            {data.students_attempted === 0 ? (
              <Empty icon="inbox">{t("analytics.none")}</Empty>
            ) : (
              <>
                <Histogram bins={data.histogram} total={data.students_attempted} />
                <section className="section">
                  <div className="section-title">
                    <h2>{t("analytics.byQuestion")}</h2>
                    <ViewToggle table={table} onChange={setTable} />
                  </div>
                  {table ? (
                    <QuestionTable questions={data.questions} />
                  ) : (
                    <ul className="stack question-stats">
                      {data.questions.map((q) => (
                        <QuestionRow key={q.id} q={q} hardest={hardest.has(q.number)} />
                      ))}
                    </ul>
                  )}
                  <details className="small muted" style={{ marginTop: 12 }}>
                    <summary>{t("analytics.dWhat")}</summary>
                    <p>{t("analytics.dHelp")}</p>
                  </details>
                </section>
              </>
            )}
          </>
        );
      }}
    </Loader>
  );
}
