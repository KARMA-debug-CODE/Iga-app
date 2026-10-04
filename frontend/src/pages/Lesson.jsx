import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import Markdown from "../components/Markdown";
import { LockBadge, LockedNotice } from "../components/Locked";
import SimEmbed from "../components/SimEmbed";
import TutorPanel from "../components/TutorPanel";
import { Loader, useToast } from "../components/ui";
import { useApi } from "../hooks";
import { LANGUAGES, useI18n } from "../i18n";

export default function Lesson() {
  const { slug } = useParams();
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const [readLang, setReadLang] = useState(null);
  const state = useApi(`/lessons/${slug}/`, { params: { lang: readLang || lang } });
  const [toast, showToast] = useToast();
  const [busy, setBusy] = useState(false);

  async function complete() {
    setBusy(true);
    try {
      const res = await api(`/lessons/${slug}/complete/`, { method: "POST" });
      state.setData((d) => ({ ...d, completed: true }));
      if (res.xp_gained) showToast(`🎉 ${t("learn.xpGained", { n: res.xp_gained })}`);
    } finally {
      setBusy(false);
    }
  }

  async function startQuiz(quizId) {
    try {
      const attempt = await api(`/quizzes/${quizId}/start/`, { method: "POST" });
      navigate(`/attempts/${attempt.id}`);
    } catch (err) {
      showToast(err.message);
    }
  }

  return (
    <Loader state={state}>
      {(lesson) => {
        const sims = Object.fromEntries(lesson.simulations.map((s) => [s.slug, s]));
        const inline = new Set([...lesson.body.matchAll(/```sim\s*\n\s*([\w-]+)/g)].map((m) => m[1]));
        const extraSims = lesson.simulations.filter((s) => !inline.has(s.slug));
        return (
          <article style={{ maxWidth: 820 }}>
            {toast}
            <div className="breadcrumb">
              <Link to={`/learn/${lesson.subject.code}?grade=${lesson.unit.grade}`}>
                {lesson.subject.icon} {lesson.subject.name}
              </Link>
              <span>›</span>
              <span>
                {lesson.unit.grade} · {t("learn.unit", { n: lesson.unit.number })}: {lesson.unit.title}
              </span>
            </div>
            <h1>{lesson.title}</h1>
            <div className="row small muted" style={{ marginBottom: 16 }}>
              <span>⏱ {t("learn.minutes", { n: lesson.estimated_minutes })}</span>
              {lesson.completed && <span className="pill pill-success">✓ {t("learn.completed")}</span>}
              {lesson.available_languages.length > 1 && (
                <span className="row">
                  {t("learn.readIn")}:
                  {lesson.available_languages.map((code) => (
                    <button
                      key={code}
                      className={`chip ${lesson.language === code ? "active" : ""}`}
                      style={{ minHeight: 30, padding: "2px 10px" }}
                      onClick={() => setReadLang(code)}
                    >
                      {LANGUAGES.find((l) => l.code === code)?.name || code}
                    </button>
                  ))}
                </span>
              )}
            </div>
            {lesson.summary && <p className="alert">{lesson.summary}</p>}

            {lesson.video_url && (
              <div className="sim-frame">
                <a className="sim-placeholder" href={lesson.video_url} target="_blank" rel="noopener noreferrer">
                  🎬 {t("learn.watchVideo")}
                </a>
              </div>
            )}

            {lesson.locked ? (
              <LockedNotice reason={lesson.access_reason} />
            ) : (
              <>
                <div className="card">
                  <Markdown sims={sims}>{lesson.body}</Markdown>
                </div>

                <div className="section">
                  <TutorPanel lesson={lesson.slug} lang={lesson.language} starters={[t("tutor.s.simpler"), t("tutor.s.example"), t("tutor.s.quizme")]} />
                </div>
              </>
            )}

            {extraSims.length > 0 && (
              <section className="section">
                <h2>🔬 {t("learn.simulations")}</h2>
                {extraSims.map((sim) => (
                  <SimEmbed key={sim.slug} slug={sim.slug} sim={sim} />
                ))}
              </section>
            )}

            {!lesson.locked && (
              <div className="card section" style={{ textAlign: "center" }}>
                {lesson.completed ? (
                  <strong style={{ color: "var(--success)" }}>✓ {t("learn.completed")}</strong>
                ) : (
                  <button className="btn btn-success" onClick={complete} disabled={busy}>
                    ✓ {t("learn.markComplete")}
                  </button>
                )}
              </div>
            )}

            {lesson.quizzes.length > 0 && (
              <section className="section">
                <h2>📝 {t("learn.quizzes")}</h2>
                <div className="grid">
                  {lesson.quizzes.map((q) => (
                    <button
                      key={q.id}
                      className="card card-link"
                      style={{ textAlign: "left", font: "inherit", cursor: q.locked ? "not-allowed" : "pointer" }}
                      onClick={() => !q.locked && startQuiz(q.id)}
                      aria-disabled={q.locked}
                    >
                      <strong>{q.title}</strong>
                      <div className="small muted">{t("practice.questions", { n: q.question_count })}</div>
                      {q.locked && <LockBadge />}
                    </button>
                  ))}
                </div>
              </section>
            )}

            {lesson.resources.length > 0 && (
              <section className="section">
                <h2>{t("learn.resources")}</h2>
                <ul className="list card">
                  {lesson.resources.map((r) => (
                    <li key={r.id}>
                      <a href={r.file_url || r.url} target="_blank" rel="noopener noreferrer">
                        {r.title}
                      </a>{" "}
                      {r.is_official && <span className="pill pill-success">{t("learn.official")}</span>}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <nav className="spread section" aria-label={t("a11y.lessonNav")}>
              {lesson.previous ? (
                <Link className="btn btn-secondary" to={`/lessons/${lesson.previous.slug}`}>
                  ← {t("learn.previous")}
                </Link>
              ) : (
                <span />
              )}
              {lesson.next && (
                <Link className="btn" to={`/lessons/${lesson.next.slug}`}>
                  {t("learn.next")} →
                </Link>
              )}
            </nav>
          </article>
        );
      }}
    </Loader>
  );
}
