import { lazy, Suspense } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth";
import { groupTitle, subjectGroups } from "../combinations";
import { Icon, SubjectIcon } from "../components/Icon";
import { AccessBanner } from "../components/Locked";
import { CountUp, Empty, Loader, Progress, scoreClass, Skeleton, SkeletonCards } from "../components/ui";
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

/** Subject cards for `grade`. An A-level student's combination comes first, under its own heading. */
export function SubjectGrid({ subjects, grade, headingLevel = 3 }) {
  const { user } = useAuth();
  const { t } = useI18n();
  const grid = (list) => (
    <div className="grid stagger">
      {list.map((s) => (
        <SubjectCard key={s.code} subject={s} grade={grade} />
      ))}
    </div>
  );
  const groups = subjectGroups(subjects, user, grade);
  if (!groups) return grid(subjects);
  const Heading = `h${headingLevel}`;
  return groups.map((group) => (
    <section key={group.key} className="subject-group">
      <Heading>{groupTitle(t, group, user)}</Heading>
      {grid(group.subjects)}
    </section>
  ));
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
              <strong>
                <CountUp value={data.xp} id={`dash.xp.${user.id}`} />
              </strong>
              <span className="small muted">XP</span>
            </div>
            <div className="stat">
              <strong>
                <CountUp value={data.lessons_completed} id={`dash.lessons.${user.id}`} />
              </strong>
              <span className="small muted">{t("dash.lessonsDone")}</span>
            </div>
            <div className="stat">
              <strong>
                <CountUp value={data.badges_earned} id={`dash.badges.${user.id}`} />
              </strong>
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
                  {data.continue_learning.subject} ·{" "}
                  {t("learn.unitTitle", { n: data.continue_learning.unit_number, title: data.continue_learning.unit_title })}
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
            <ul className="list stagger">
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
            <ul className="list stagger">
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
        <Loader state={subjects} skeleton={<SkeletonCards count={6} progress />}>
          {(list) => <SubjectGrid subjects={list} grade={user.grade} />}
        </Loader>
      </section>
    </>
  );
}

function TeacherDashboard({ data, user }) {
  const { t, lang } = useI18n();
  const teacher = data.teacher;
  return (
    <>
      <div className="stats stagger">
        <Link to="/classes" className="card card-link stat">
          <strong>
            <CountUp value={teacher.classes.length} id={`dash.classes.${user.id}`} />
          </strong>
          <span className="muted small">{t("dash.myClasses")}</span>
        </Link>
        <Link to="/marking" className="card card-link stat">
          <strong>
            <CountUp value={teacher.pending_marking} id={`dash.marking.${user.id}`} />
          </strong>
          <span className="muted small">{t("dash.pendingMarking")}</span>
        </Link>
        <Link to="/teach" className="card card-link stat">
          <strong>
            <CountUp value={teacher.awaiting_review.lessons + teacher.awaiting_review.quizzes} id={`dash.review.${user.id}`} />
          </strong>
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
            <ul className="list stagger">
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

/** The home screen while it loads: the level card and the "continue" card, then the subjects. */
function DashboardSkeleton() {
  return (
    <Skeleton>
      <div className="grid-2">
        <div className="card skeleton">
          <div className="spread">
            <span className="sk sk-title" style={{ width: "30%" }} />
            <span className="sk sk-pill" style={{ width: 90 }} />
          </div>
          <span className="sk sk-bar" style={{ margin: "18px 0 10px" }} />
          <span className="sk" style={{ width: "45%" }} />
          <div className="stats stats-3" style={{ marginTop: 18 }}>
            {[0, 1, 2].map((i) => (
              <span className="sk-lines" key={i}>
                <span className="sk sk-title" style={{ width: "35%" }} />
                <span className="sk" style={{ width: "70%" }} />
              </span>
            ))}
          </div>
        </div>
        <div className="card skeleton">
          <span className="sk" style={{ width: "35%" }} />
          <div className="sk-row" style={{ marginTop: 14 }}>
            <span className="sk sk-tile" />
            <span className="sk-lines">
              <span className="sk sk-title" />
              <span className="sk" style={{ width: "75%" }} />
            </span>
          </div>
          <span className="sk sk-pill" style={{ width: 110, height: 34, marginTop: 18 }} />
        </div>
      </div>
      <div className="grid-2 section">
        {[0, 1].map((i) => (
          <div className="card skeleton" key={i}>
            <div className="sk-row">
              <span className="sk sk-tile" />
              <span className="sk-lines">
                <span className="sk sk-title" style={{ width: "40%" }} />
                <span className="sk" style={{ width: "80%" }} />
              </span>
            </div>
          </div>
        ))}
      </div>
    </Skeleton>
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
        <Loader state={state} skeleton={<DashboardSkeleton />}>
          {(data) => (data.teacher?.classes ? <TeacherDashboard data={data} user={user} /> : <StudentDashboard data={data} user={user} />)}
        </Loader>
      )}
    </>
  );
}
