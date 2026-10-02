import { Link, useParams, useSearchParams } from "react-router-dom";

import { useAuth } from "../auth";
import { GradeChips, Loader, Progress } from "../components/ui";
import { results } from "../api";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

function ResourceList({ code, grade }) {
  const { t } = useI18n();
  const state = useApi("/resources/", { params: { subject: code, grade } });
  const list = results(state.data);
  if (!list.length) return null;
  return (
    <section className="section">
      <h2>{t("learn.resources")}</h2>
      <div className="card">
        <ul className="list">
          {list.map((r) => (
            <li key={r.id}>
              <a className="list-link" href={r.file_url || r.url} target="_blank" rel="noopener noreferrer">
                <div className="icon-tile" aria-hidden>
                  {r.kind === "video" ? "🎬" : r.kind === "link" ? "🔗" : "📄"}
                </div>
                <div className="grow">
                  <strong>{r.title}</strong>
                  {r.description && <div className="small muted">{r.description}</div>}
                </div>
                {r.is_official && <span className="pill pill-success">{t("learn.official")}</span>}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function QuizList({ code, grade }) {
  const { t } = useI18n();
  const state = useApi("/quizzes/", { params: { subject: code, grade } });
  const list = results(state.data);
  if (!list.length) return null;
  return (
    <section className="section">
      <h2>{t("practice.quizzes")}</h2>
      <div className="grid">
        {list.map((q) => (
          <Link key={q.id} to={`/practice?start=${q.id}`} className="card card-link">
            <strong>{q.title}</strong>
            <div className="small muted">{t("practice.questions", { n: q.question_count })}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}

export default function Subject() {
  const { code } = useParams();
  const { user } = useAuth();
  const { t, lang } = useI18n();
  const [params, setParams] = useSearchParams();
  const grade = params.get("grade") || user.grade || "S1";
  const state = useApi(`/subjects/${code}/`, { params: { grade, lang } });

  return (
    <Loader state={state}>
      {(subject) => (
        <>
          <div className="breadcrumb">
            <Link to={`/learn?grade=${grade}`}>{t("learn.subjects")}</Link> <span>›</span> <span>{subject.display_name}</span>
          </div>
          <div className="page-header row" style={{ flexWrap: "nowrap" }}>
            <div className="icon-tile" style={{ background: `${subject.color}22`, width: 56, height: 56, fontSize: "1.8rem" }} aria-hidden>
              {subject.icon}
            </div>
            <div>
              <h1 style={{ margin: 0 }}>{subject.display_name}</h1>
              <p>{subject.description}</p>
            </div>
          </div>
          <GradeChips value={grade} onChange={(g) => setParams({ grade: g })} grades={subject.grades.length ? subject.grades : undefined} />

          {subject.lesson_count > 0 && (
            <div className="card" style={{ marginTop: 16 }}>
              <div className="spread small">
                <span>
                  {subject.completed_count}/{subject.lesson_count} {t("dash.lessonsDone")}
                </span>
              </div>
              <div style={{ marginTop: 8 }}>
                <Progress value={subject.completed_count} max={subject.lesson_count} />
              </div>
            </div>
          )}

          <div className="stack" style={{ marginTop: 16 }}>
            {subject.units.map((unit) => (
              <details className="unit" key={unit.id} open={unit.lessons.length > 0}>
                <summary>
                  <span className="pill pill-blue">{t("learn.unit", { n: unit.number })}</span>
                  <span>{unit.title}</span>
                </summary>
                <div className="unit-body">
                  {!unit.alignment_verified && <p className="small muted">ⓘ {t("learn.notVerified")}</p>}
                  {unit.lessons.length ? (
                    <ul className="list">
                      {unit.lessons.map((lesson) => (
                        <li key={lesson.id}>
                          <Link className="list-link" to={`/lessons/${lesson.slug}`}>
                            <span className={`done-dot ${lesson.completed ? "done" : ""}`} aria-label={lesson.completed ? t("learn.completed") : ""}>
                              {lesson.completed ? "✓" : ""}
                            </span>
                            <div className="grow">
                              <div>{lesson.title}</div>
                              <div className="small muted">{t("learn.minutes", { n: lesson.estimated_minutes })}</div>
                            </div>
                            <span aria-hidden>›</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted small" style={{ margin: 0 }}>
                      {t("learn.noLessons")}
                    </p>
                  )}
                </div>
              </details>
            ))}
          </div>

          <QuizList code={code} grade={grade} />
          <ResourceList code={code} grade={grade} />
        </>
      )}
    </Loader>
  );
}
