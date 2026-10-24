import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { Burst, useCelebrations } from "../components/Celebrate";
import { Icon, SubjectIcon } from "../components/Icon";
import Markdown from "../components/Markdown";
import { CHOICE_TYPES, isAnswered, QuestionBody, SolutionPanel, verdict } from "../components/Question";
import TutorPanel from "../components/TutorPanel";
import { LockedNotice } from "../components/Locked";
import { CountUp, ErrorMessage, Loader } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";
import { safeUrl } from "../safeUrl";
import { useStartQuiz } from "./Practice";

const RETRY_MS = 5000;

function formatClock(ms) {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

function Timer({ deadline, offset, onExpire }) {
  const { t } = useI18n();
  // Count down on the monotonic clock: changing the phone's time can't end the exam early.
  const [end] = useState(() => performance.now() + (new Date(deadline).getTime() - (Date.now() + offset)));
  const [now, setNow] = useState(() => performance.now());
  const fired = useRef(false);
  useEffect(() => {
    const id = setInterval(() => setNow(performance.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const left = end - now;
  useEffect(() => {
    if (left <= 0 && !fired.current) {
      fired.current = true;
      onExpire();
    }
  }, [left, onExpire]);
  return (
    <span className={`timer with-icon ${left < 60000 ? "low" : ""}`} role="timer" aria-label={t("quiz.timeLeft")}>
      <Icon name="timer" size={16} /> {formatClock(left)}
    </span>
  );
}

// From this score up a quiz just finished gets a burst around its ring (the same line as a green score pill).
const GOOD_SCORE = 75;

// The ring fills from empty where the browser can animate its fill (CSS @property), and is simply full elsewhere.
const canFillRing = typeof CSS !== "undefined" && typeof CSS.registerProperty === "function";

function ScoreRing({ pct, celebrate }) {
  return (
    <div className={`score-ring ${canFillRing ? "is-filling" : ""}`} style={{ "--pct": pct ?? 0 }}>
      <div>{pct != null ? <CountUp value={Math.round(pct)} format={(n) => `${n}%`} /> : "…"}</div>
      {celebrate && <Burst size={280} />}
    </div>
  );
}

function Results({ attempt, fresh = false }) {
  const { t } = useI18n();
  const { start, busy, error } = useStartQuiz();
  const pct = attempt.percentage;
  return (
    <div className="quiz-shell">
      <div className="card" style={{ textAlign: "center" }}>
        <span className="small muted with-icon">
          <SubjectIcon name={attempt.quiz.subject.icon} size={16} /> {attempt.quiz.subject.name} · {attempt.quiz.grade}
        </span>
        <h1 style={{ margin: "6px 0 16px" }}>{attempt.quiz.title}</h1>
        <ScoreRing pct={pct} celebrate={fresh && pct != null && pct >= GOOD_SCORE} />
        <p style={{ marginTop: 12 }}>
          {t("quiz.yourScore")}: <strong>{Number(attempt.score ?? 0)}</strong> / {Number(attempt.max_score)}
        </p>
        {attempt.status === "needs_marking" && <div className="alert alert-warn">{t("quiz.awaitingMarking")}</div>}
        <ErrorMessage error={error} />
        <div className="row" style={{ justifyContent: "center", marginTop: 12 }}>
          <Link className="btn btn-secondary" to="/practice">
            ← {t("quiz.back")}
          </Link>
          <button className="btn" disabled={busy} onClick={() => start(attempt.quiz.id)}>
            <Icon name="refresh" size={16} /> {t("quiz.tryAgain")}
          </button>
          {attempt.quiz.marking_guide_link && (
            <a className="btn btn-secondary" href={safeUrl(attempt.quiz.marking_guide_link)} target="_blank" rel="noopener noreferrer">
              {t("practice.markingGuide")}
            </a>
          )}
        </div>
      </div>

      <h2 className="section">{t("quiz.review")}</h2>
      {attempt.quiz.locked && attempt.questions.length === 0 && <LockedNotice compact />}
      <div className="stack">
        {attempt.questions.map((q) => (
          <div className="card" key={q.id}>
            <div className="spread small muted">
              <span>{t("quiz.question", { n: q.number, total: attempt.questions.length })}</span>
              <span>{t("quiz.marks", { n: Number(q.marks) })}</span>
            </div>
            <Markdown interactive={false}>{q.prompt}</Markdown>
            <QuestionBody question={q} answer={q.answer} onChange={() => {}} locked />
            <SolutionPanel question={q} answer={q.answer} />
            <div style={{ marginTop: 12 }}>
              <TutorPanel
                attempt={attempt.id}
                question={q.id}
                label={t("tutor.explain")}
                starters={[t("tutor.s.why"), t("tutor.s.wrong"), t("tutor.s.similar")]}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Player({ initial, onFinished }) {
  const { t } = useI18n();
  const [attempt, setAttempt] = useState(initial);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState(() =>
    Object.fromEntries(initial.questions.map((q) => [q.id, q.answer || {}])),
  );
  const [saving, setSaving] = useState("idle");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const timers = useRef({});
  const pending = useRef({}); // newest answer not yet sent, per question
  const inflight = useRef({}); // the save currently running, per question
  // Server clock minus browser clock, so the countdown is right even if the phone's time is off.
  const offset = useMemo(() => new Date(initial.server_now).getTime() - Date.now(), [initial.server_now]);

  const question = attempt.questions[index];
  const immediate = attempt.quiz.feedback_mode === "immediate";
  const total = attempt.questions.length;

  const closedByServer = useCallback(
    (e) => {
      // The server says the attempt is over (its codes don't depend on the reader's language).
      const code = e?.status === 400 ? e.data?.code : null;
      if (code === "time_up" || code === "attempt_closed") {
        onFinished(code === "time_up" ? t("quiz.timeUp") : null);
        return true;
      }
      return false;
    },
    [onFinished, t],
  );

  const save = useCallback(
    (questionId) => {
      const send = async () => {
        const answer = pending.current[questionId];
        if (!answer) return;
        delete pending.current[questionId];
        setSaving("saving");
        try {
          await api(`/attempts/${attempt.id}/answer/`, {
            method: "POST",
            body: {
              question: questionId,
              choice_ids: answer.choice_ids || [],
              text: answer.text || "",
              numeric: answer.numeric === "" || answer.numeric === undefined ? null : answer.numeric,
            },
          });
          if (!Object.keys(pending.current).length) setSaving("saved");
        } catch (e) {
          if (closedByServer(e)) return;
          if (e.status === 400) {
            setError(e); // the answer itself was refused; resending won't help
            setSaving("idle");
            return;
          }
          // Network or server trouble: keep the answer (unless a newer one is waiting) and retry.
          if (!pending.current[questionId]) pending.current[questionId] = answer;
          setSaving("failed");
          clearTimeout(timers.current[questionId]);
          timers.current[questionId] = setTimeout(() => save(questionId), RETRY_MS);
          throw e;
        }
      };
      // One request per question at a time, in order, so an older answer never lands last.
      const run = (inflight.current[questionId] || Promise.resolve()).catch(() => {}).then(send);
      inflight.current[questionId] = run;
      run
        .finally(() => {
          if (inflight.current[questionId] === run) delete inflight.current[questionId];
        })
        .catch(() => {});
      return run;
    },
    [attempt.id, closedByServer],
  );

  // Send everything waiting and wait for saves already on their way. Rejects if any failed.
  const flush = useCallback(async () => {
    Object.values(timers.current).forEach(clearTimeout);
    timers.current = {};
    Object.keys(pending.current).forEach((id) => save(Number(id)));
    await Promise.all(Object.values(inflight.current));
  }, [save]);

  function change(patch) {
    const qid = question.id;
    const next = { ...answers[qid], ...patch };
    setAnswers((a) => ({ ...a, [qid]: next }));
    pending.current[qid] = next;
    clearTimeout(timers.current[qid]);
    const delay = CHOICE_TYPES.includes(question.type) ? 0 : 700;
    timers.current[qid] = setTimeout(() => save(qid), delay);
  }

  async function check() {
    setError(null);
    try {
      await flush();
      const updated = await api(`/attempts/${attempt.id}/check/`, { method: "POST", body: { question: question.id } });
      setAttempt((a) => ({ ...a, questions: a.questions.map((q) => (q.id === updated.id ? updated : q)) }));
    } catch (e) {
      if (!closedByServer(e)) setError(e);
    }
  }

  const submit = useCallback(
    async (force = false) => {
      const unanswered = attempt.questions.filter((q) => !isAnswered(q, answers[q.id])).length;
      const message = `${t("quiz.confirmSubmit")}${unanswered ? `\n\n${t("quiz.unanswered", { n: unanswered })}` : ""}`;
      if (!force && !window.confirm(message)) return;
      setSubmitting(true);
      setError(null);
      try {
        await flush();
      } catch (e) {
        // Out of time: submit what the server has. Otherwise stop, so no answer is lost.
        if (!force) {
          setError(e);
          setSubmitting(false);
          return;
        }
      }
      try {
        const done = await api(`/attempts/${attempt.id}/submit/`, { method: "POST" });
        onFinished(force ? t("quiz.timeUp") : null, done?.rewards);
      } catch (e) {
        if (closedByServer(e)) return;
        setError(e);
        setSubmitting(false);
      }
    },
    [attempt, answers, flush, onFinished, closedByServer, t],
  );

  const onExpire = useCallback(() => submit(true), [submit]);

  useEffect(() => {
    const warn = (e) => {
      if (Object.keys(pending.current).length || Object.keys(inflight.current).length) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);

  const locked = Boolean(question.answer?.checked || question.solution);

  return (
    <div className="quiz-shell">
      <div className="quiz-top">
        <div className="spread">
          <strong className="truncate" style={{ maxWidth: "60%" }}>
            {attempt.quiz.title}
          </strong>
          <div className="row">
            <span className="small muted with-icon" aria-live="polite">
              {saving === "saving" && t("quiz.saving")}
              {saving === "saved" && (
                <>
                  <Icon name="check" size={14} /> {t("quiz.saved")}
                </>
              )}
              {saving === "failed" && (
                <>
                  <Icon name="warning" size={14} /> {t("quiz.notSaved")}
                </>
              )}
            </span>
            {attempt.deadline && <Timer deadline={attempt.deadline} offset={offset} onExpire={onExpire} />}
          </div>
        </div>
        <nav className="qnav" style={{ marginTop: 10 }} aria-label={t("a11y.questionNav")}>
          {attempt.questions.map((q, i) => {
            const v = verdict(q);
            const cls = [
              i === index ? "current" : "",
              v === "right" ? "right" : v === "wrong" ? "wrong" : isAnswered(q, answers[q.id]) ? "answered" : "",
            ].join(" ");
            return (
              <button key={q.id} className={cls} onClick={() => setIndex(i)} aria-label={t("quiz.question", { n: i + 1, total })} aria-current={i === index}>
                {i + 1}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="card">
        <div className="spread small muted">
          <span>{t("quiz.question", { n: index + 1, total })}</span>
          <span>{t("quiz.marks", { n: Number(question.marks) })}</span>
        </div>
        <Markdown interactive={false}>{question.prompt}</Markdown>
        <QuestionBody question={question} answer={answers[question.id]} onChange={change} locked={locked || submitting} />
        <SolutionPanel question={question} answer={answers[question.id]} />
        {immediate && !attempt.deadline && (
          <div style={{ marginTop: 12 }}>
            <TutorPanel
              key={question.id}
              attempt={attempt.id}
              question={question.id}
              label={t("tutor.hint")}
              starters={[t("tutor.s.hint"), t("tutor.s.idea")]}
            />
          </div>
        )}
        <ErrorMessage error={error} />
        <div className="spread" style={{ marginTop: 16 }}>
          <button className="btn btn-secondary" disabled={index === 0} onClick={() => setIndex((i) => i - 1)}>
            ← {t("quiz.prev")}
          </button>
          {immediate && !locked && !question.teacher_marked && (
            <button className="btn btn-success" disabled={!isAnswered(question, answers[question.id])} onClick={check}>
              {t("quiz.check")}
            </button>
          )}
          {index < total - 1 ? (
            <button className="btn" onClick={() => setIndex((i) => i + 1)}>
              {t("quiz.next")} →
            </button>
          ) : (
            <button className="btn" disabled={submitting} onClick={() => submit(false)}>
              {t("quiz.submit")} <Icon name="check" size={16} />
            </button>
          )}
        </div>
      </div>
      {index < total - 1 && (
        <div style={{ textAlign: "center", marginTop: 16 }}>
          <button className="btn btn-ghost" disabled={submitting} onClick={() => submit(false)}>
            {t("quiz.submit")}
          </button>
        </div>
      )}
    </div>
  );
}

export default function QuizPlayer() {
  const { id } = useParams();
  const state = useApi(`/attempts/${id}/`, {}, [id]);
  const [notice, setNotice] = useState(null);
  const [freshId, setFreshId] = useState(null); // finished here just now, rather than an old attempt opened again
  const [celebration, celebrate] = useCelebrations();
  const finished = useCallback(
    (message, rewards) => {
      if (message) setNotice(message);
      setFreshId(id);
      celebrate(rewards);
      state.reload();
    },
    [state, celebrate, id],
  );
  return (
    <>
      {celebration}
      <Loader state={state}>
        {(attempt) =>
          attempt.status === "in_progress" ? (
            <Player key={attempt.id} initial={attempt} onFinished={finished} />
          ) : (
            <>
              {notice && <div className="alert alert-warn quiz-shell" style={{ marginBottom: 12 }}>{notice}</div>}
              <Results attempt={attempt} fresh={String(attempt.id) === freshId} />
            </>
          )
        }
      </Loader>
    </>
  );
}
