import { lazy, Suspense } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth";
import { Icon, SubjectIcon } from "../components/Icon";
import { AccessBanner } from "../components/Locked";
import { Empty, Loader, Progress, scoreClass } from "../components/ui";
import { formatDate, useApi } from "../hooks";
import { useI18n } from "../i18n";

// Parents get their own (lazily loaded) dashboard, in the same chunk as the /children pages.
const ParentDashboard = lazy(() => import("./Children").then((m) => ({ default: m.ParentDashboard })));
const SchoolHome = lazy(() => import("./School").then((m) => ({ default: m.SchoolHome })));

export function SubjectCard({ subject, grade }) {
  const { t } = useI18n();
  return (
    <Link to={`/learn/${subject.code}?grade=${grade || ""}`} className="card card-link subject-card" style={{ "--subject": subject.color }}>
      <div className="row" style={{ flexWrap: "nowrap" }}>
        <div className="icon-tile">
          <SubjectIcon name={subject.icon} />
        </div>
        <div style={{ minWidth: 0 }}>
          <strong className="truncate" style={{ display: "block" }}>
            {subject.display_name || subject.name}
          </strong>
          {subject.lesson_count != null && (
            <span className="small muted">
              {subject.completed_count}/{subject.lesson_count} {t("dash.lessonsDone")}
            </span>
          )}
        </div>
      </div>
      {subject.lesson_count > 0 && (
        <div style={{ marginTop: 12 }}>
          <Progress value={subject.completed_count} max={subject.lesson_count} label={subject.name} />
        </div>
      )}
    </Link>
  );
}

function AssignmentItem({ assignment }) {
  const { t, lang } = useI18n();
  const href = assignment.quiz
    ? `/practice?start=${assignment.quiz}&assignment=${assignment.id}`
    : assignment.lesson_slug
      ? `/lessons/${assignment.lesson_slug}`
      : `/labs/${assignment.simulation_slug}`;
  const icon = { quiz: "practice", lesson: "learn", simulation: "labs" }[assignment.kind] || "bookmark";
  return (
    <li>
      <Link className="list-link" to={href}>
        <div className="icon-tile">
          <Icon name={icon} size={22} />
        </div>
        <div className="grow">
          <strong className="truncate" style={{ display: "block" }}>
            {assignment.title}
          </strong>
          <span className="small muted">
            {assignment.classroom_name} · {assignment.due_at ? t("classes.due", { date: formatDate(assignment.due_at, lang) }) : t("classes.noDue")}
          </span>
        </div>
        {assignment.my_status?.late ? (
          <span className="pill pill-danger">{t("classes.late")}</span>
        ) : (
          <span className="pill">{t(`classes.state.${assignment.my_status?.state || "todo"}`)}</span>
        )}
      </Link>
    </li>
  );
}

function StudentDashboard({ data, user }) {
  const { t, lang } = useI18n();
  const subjects = useApi("/subjects/", { params: { grade: user.grade, lang } });
  return (
    <>
      <div className="grid-2">
        <div className="card">
          <div className="spread">
            <strong>{t("dash.level", { level: data.level.level })}</strong>
            <span className="pill pill-warn">
              <Icon name="flame" size={14} /> {t("dash.streak", { n: data.streak_days })}
            </span>
          </div>
          <div style={{ margin: "12px 0 6px" }}>
            <Progress value={data.level.current} max={data.level.needed} label="XP" />
          </div>
          <span className="small muted">{t("dash.xpToNext", { current: data.level.current, needed: data.level.needed })}</span>
          <div className="stats stats-3" style={{ marginTop: 14 }}>
            <div className="stat">
              <strong>{data.xp}</strong>
              <span className="small muted">XP</span>
            </div>
            <div className="stat">
              <strong>{data.lessons_completed}</strong>
              <span className="small muted">{t("dash.lessonsDone")}</span>
            </div>
            <div className="stat">
              <strong>{data.badges_earned}</strong>
              <span className="small muted">{t("dash.badges")}</span>
            </div>
          </div>
        </div>

        {data.continue_learning ? (
          <Link to={`/lessons/${data.continue_learning.slug}`} className="card card-link" style={{ borderLeft: "6px solid var(--yellow)" }}>
            <span className="small muted">{t("dash.continue")}</span>
            <div className="row" style={{ marginTop: 8, flexWrap: "nowrap" }}>
              <div className="icon-tile">
                <SubjectIcon name={data.continue_learning.icon} />
              </div>
              <div style={{ minWidth: 0 }}>
                <strong style={{ display: "block" }}>{data.continue_learning.title}</strong>
                <span className="small muted">
                  {data.continue_learning.subject} · {t("learn.unit", { n: data.continue_learning.unit_number })}: {data.continue_learning.unit_title}
                </span>
              </div>
            </div>
            <span className="btn btn-sm" style={{ marginTop: 14 }}>
              {t("practice.resume")} →
            </span>
          </Link>
        ) : (
          <Link to="/learn" className="card card-link">
            <strong>{t("dash.startHere")} →</strong>
          </Link>
        )}
      </div>

      {/* Phones have no side menu, so the study tools are linked from here too. */}
      <div className="grid-2 section study-tools">
        <Link to="/ask" className="card card-link row" style={{ flexWrap: "nowrap" }}>
          <div className="icon-tile">
            <Icon name="santa" size={22} />
          </div>
          <div style={{ minWidth: 0 }}>
            <strong style={{ display: "block" }}>{t("nav.ask")}</strong>
            <span className="small muted">{t("dash.askHint")}</span>
          </div>
        </Link>
        <Link to="/playground" className="card card-link row" style={{ flexWrap: "nowrap" }}>
          <div className="icon-tile">
            <Icon name="playground" size={22} />
          </div>
          <div style={{ minWidth: 0 }}>
            <strong style={{ display: "block" }}>{t("nav.playground")}</strong>
            <span className="small muted">{t("dash.playgroundHint")}</span>
          </div>
        </Link>
      </div>

      <section className="section grid-2">
        <div className="card">
          <h2>{t("dash.assignments")}</h2>
          {data.assignments.length ? (
            <ul className="list">
              {data.assignments.map((a) => (
                <AssignmentItem key={a.id} assignment={a} />
              ))}
            </ul>
          ) : (
            <>
              <p className="muted">{t("dash.noAssignments")}</p>
              <Link className="btn btn-secondary btn-sm" to="/classes">
                {t("classes.join")}
              </Link>
            </>
          )}
        </div>
        <div className="card">
          <h2>{t("dash.recentScores")}</h2>
          {data.recent_attempts.length ? (
            <ul className="list">
              {data.recent_attempts.map((a) => (
                <li key={a.id}>
                  <Link className="list-link" to={`/attempts/${a.id}`}>
                    <div className="icon-tile">
                      <SubjectIcon name={a.subject_icon} />
                    </div>
                    <div className="grow truncate">{a.quiz_title}</div>
                    <span className={scoreClass(a.percentage)}>{a.percentage != null ? `${a.percentage}%` : "…"}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">{t("dash.noScores")}</p>
          )}
        </div>
      </section>

      <section className="section">
        <div className="section-title">
          <h2>
            {t("dash.subjects")} · {user.grade}
          </h2>
          <Link to="/learn">{t("learn.subjects")} →</Link>
        </div>
        <Loader state={subjects}>
          {(list) => (
            <div className="grid">
              {list.map((s) => (
                <SubjectCard key={s.code} subject={s} grade={user.grade} />
              ))}
            </div>
          )}
        </Loader>
      </section>
    </>
  );
}

function TeacherDashboard({ data }) {
  const { t, lang } = useI18n();
  const teacher = data.teacher;
  return (
    <>
      <div className="stats">
        <Link to="/classes" className="card card-link stat">
          <strong>{teacher.classes.length}</strong>
          <span className="muted small">{t("dash.myClasses")}</span>
        </Link>
        <Link to="/marking" className="card card-link stat">
          <strong>{teacher.pending_marking}</strong>
          <span className="muted small">{t("dash.pendingMarking")}</span>
        </Link>
        <Link to="/teach" className="card card-link stat">
          <strong>{teacher.awaiting_review.lessons + teacher.awaiting_review.quizzes}</strong>
          <span className="muted small">{t("dash.awaitingReview")}</span>
        </Link>
      </div>
      <section className="section grid-2">
        <div className="card">
          <div className="section-title">
            <h2>{t("dash.myClasses")}</h2>
            <Link to="/classes">+ {t("classes.create")}</Link>
          </div>
          {teacher.classes.length ? (
            <ul className="list">
              {teacher.classes.map((c) => (
                <li key={c.id}>
                  <Link className="list-link" to={`/classes/${c.id}`}>
                    <div className="icon-tile">
                      <Icon name="classes" size={22} />
                    </div>
                    <div className="grow">
                      <strong>{c.name}</strong>
                      <div className="small muted">
                        {c.grade} · {c.students} {t("classes.students").toLowerCase()}
                      </div>
                    </div>
                    <span className="pill pill-blue">{c.join_code}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <Empty icon="classes">{t("classes.empty")}</Empty>
          )}
        </div>
        <div className="card">
          <h2>{t("dash.recentSubmissions")}</h2>
          {teacher.recent_submissions.length ? (
            <ul className="list">
              {teacher.recent_submissions.map((a) => (
                <li key={a.id} className="spread">
                  <div style={{ minWidth: 0 }}>
                    <div className="truncate">{a.quiz_title}</div>
                    <div className="small muted">{formatDate(a.submitted_at, lang)}</div>
                  </div>
                  <span className={scoreClass(a.percentage)}>{a.percentage != null ? `${a.percentage}%` : t("classes.state.needs_marking")}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">—</p>
          )}
        </div>
      </section>
    </>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const { t, lang } = useI18n();
  // ?lang= makes the answer follow a language change straight away (it's part of the request key).
  const state = useApi("/dashboard/", { skip: user.role === "parent" || user.role === "school_admin", params: { lang } });
  if (user.role === "school_admin") {
    return (
      <Suspense fallback={<div className="muted">{t("common.loading")}</div>}>
        <SchoolHome />
      </Suspense>
    );
  }
  return (
    <>
      <div className="page-header">
        <h1>{t("dash.hello", { name: user.first_name || user.username })}</h1>
        <p>{t("app.tagline")}</p>
      </div>
      {user.role === "teacher" && !user.teacher_approved && <div className="alert alert-warn" style={{ marginBottom: 16 }}>{t("auth.teacherPending")}</div>}
      <AccessBanner />
      {user.role === "parent" ? (
        <Suspense fallback={<div className="muted">{t("common.loading")}</div>}>
          <ParentDashboard />
        </Suspense>
      ) : (
        <Loader state={state}>
          {(data) => (data.teacher?.classes ? <TeacherDashboard data={data} /> : <StudentDashboard data={data} user={user} />)}
        </Loader>
      )}
    </>
  );
}
