import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import Markdown from "../components/Markdown";
import { ErrorMessage, Loader } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";
import { useStartQuiz } from "./Practice";

const CHOICE_TYPES = ["mcq", "multi", "true_false"];

function isAnswered(question, answer) {
  if (!answer) return false;
  if (CHOICE_TYPES.includes(question.type)) return (answer.choice_ids || []).length > 0;
  if (question.type === "numeric") return answer.numeric !== null && answer.numeric !== undefined && answer.numeric !== "";
  return Boolean(answer.text && answer.text.trim());
}

function verdict(question) {
  const s = question.solution;
  if (!s) return null;
  if (s.is_correct === null || s.marks_awarded === null) return "pending";
  if (s.is_correct) return "right";
  return Number(s.marks_awarded) > 0 ? "partial" : "wrong";
}

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
  const [now, setNow] = useState(() => Date.now());
  const fired = useRef(false);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const left = new Date(deadline).getTime() - (now + offset);
  useEffect(() => {
    if (left <= 0 && !fired.current) {
      fired.current = true;
      onExpire();
    }
  }, [left, onExpire]);
  return (
    <span className={`timer ${left < 60000 ? "low" : ""}`} role="timer" aria-label={t("quiz.timeLeft")}>
      ⏱ {formatClock(left)}
    </span>
  );
}

function QuestionBody({ question, answer, onChange, locked }) {
  const { t } = useI18n();
  const solution = question.solution;
  const correct = new Set(solution?.correct_choice_ids || []);
  const selected = new Set(answer?.choice_ids || []);

  if (CHOICE_TYPES.includes(question.type)) {
    const multi = question.type === "multi";
    return (
      <div className="stack" role={multi ? "group" : "radiogroup"}>
        {multi && <span className="small muted">{t("quiz.chooseMany")}</span>}
        {question.choices.map((choice) => {
          const isSelected = selected.has(choice.id);
          let cls = isSelected ? "selected" : "";
          if (solution) {
            if (correct.has(choice.id)) cls = "correct";
            else if (isSelected) cls = "wrong";
          }
          return (
            <label key={choice.id} className={`option ${cls}`}>
              <input
                type={multi ? "checkbox" : "radio"}
                name={`q-${question.id}`}
                checked={isSelected}
                disabled={locked}
                onChange={() => {
                  const next = multi
                    ? isSelected
                      ? [...selected].filter((id) => id !== choice.id)
                      : [...selected, choice.id]
                    : [choice.id];
                  onChange({ choice_ids: next });
                }}
              />
              <Markdown interactive={false}>{choice.text}</Markdown>
            </label>
          );
        })}
      </div>
    );
  }

  if (question.type === "numeric") {
    return (
      <input
        type="number"
        step="any"
        inputMode="decimal"
        placeholder={t("quiz.numberPlaceholder")}
        value={answer?.numeric ?? ""}
        disabled={locked}
        onChange={(e) => onChange({ numeric: e.target.value === "" ? null : e.target.value })}
        aria-label={t("quiz.yourAnswer")}
        style={{ maxWidth: 260 }}
      />
    );
  }

  if (question.type === "short") {
    return (
      <input
        placeholder={t("quiz.textPlaceholder")}
        value={answer?.text ?? ""}
        disabled={locked}
        onChange={(e) => onChange({ text: e.target.value })}
        aria-label={t("quiz.yourAnswer")}
      />
    );
  }

  return (
    <textarea
      placeholder={t("quiz.essayPlaceholder")}
      value={answer?.text ?? ""}
      disabled={locked}
      onChange={(e) => onChange({ text: e.target.value })}
      rows={8}
      aria-label={t("quiz.yourAnswer")}
    />
  );
}

function SolutionPanel({ question, answer }) {
  const { t } = useI18n();
  const s = question.solution;
  if (!s) return null;
  const v = verdict(question);
  const cls = v === "right" ? "good" : v === "wrong" ? "bad" : "neutral";
  const heading = {
    right: `✅ ${t("quiz.correct")}`,
    wrong: `❌ ${t("quiz.incorrect")}`,
    partial: `🟡 ${t("quiz.partly")}`,
    pending: `🧑🏽‍🏫 ${t("quiz.teacherMarked")}`,
  }[v];
  const showTyped = ["numeric", "short"].includes(question.type);
  const expected = question.type === "numeric" ? s.numeric_answer : s.accepted_answers?.[0];

  return (
    <div className={`feedback ${cls}`} aria-live="polite">
      <div className="spread">
        <strong>{heading}</strong>
        {s.marks_awarded !== null && (
          <span className="pill">
            {Number(s.marks_awarded)} / {Number(question.marks)}
          </span>
        )}
      </div>
      {showTyped && (
        <p style={{ margin: "8px 0 0" }}>
          {t("quiz.yourAnswer")}: <strong>{(question.type === "numeric" ? answer?.numeric : answer?.text) ?? t("quiz.noAnswer")}</strong>
          {v !== "right" && expected !== undefined && expected !== null && (
            <>
              {" · "}
              {t("quiz.correctAnswer")}: <strong>{String(expected)}</strong>
            </>
          )}
        </p>
      )}
      {s.teacher_feedback && (
        <div style={{ marginTop: 10 }}>
          <strong>{t("quiz.teacherFeedback")}:</strong> {s.teacher_feedback}
        </div>
      )}
      {s.explanation && (
        <div style={{ marginTop: 10 }}>
          <strong>{t("quiz.explanation")}</strong>
          <Markdown interactive={false}>{s.explanation}</Markdown>
        </div>
      )}
      {s.marking_guide && (
        <details style={{ marginTop: 8 }}>
          <summary>{t("quiz.markingGuide")}</summary>
          <Markdown interactive={false}>{s.marking_guide}</Markdown>
        </details>
      )}
    </div>
  );
}

function Results({ attempt }) {
  const { t } = useI18n();
  const { start, busy } = useStartQuiz();
  const pct = attempt.percentage;
  return (
    <div className="quiz-shell">
      <div className="card" style={{ textAlign: "center" }}>
        <span className="small muted">
          {attempt.quiz.subject.icon} {attempt.quiz.subject.name} · {attempt.quiz.grade}
        </span>
        <h1 style={{ margin: "6px 0 16px" }}>{attempt.quiz.title}</h1>
        <div className="score-ring" style={{ "--pct": pct ?? 0 }}>
          <div>{pct != null ? `${Math.round(pct)}%` : "…"}</div>
        </div>
        <p style={{ marginTop: 12 }}>
          {t("quiz.yourScore")}: <strong>{Number(attempt.score ?? 0)}</strong> / {Number(attempt.max_score)}
        </p>
        {attempt.status === "needs_marking" && <div className="alert alert-warn">{t("quiz.awaitingMarking")}</div>}
        <div className="row" style={{ justifyContent: "center", marginTop: 12 }}>
          <Link className="btn btn-secondary" to="/practice">
            ← {t("quiz.back")}
          </Link>
          <button className="btn" disabled={busy} onClick={() => start(attempt.quiz.id)}>
            ↻ {t("quiz.tryAgain")}
          </button>
          {attempt.quiz.marking_guide_link && (
            <a className="btn btn-secondary" href={attempt.quiz.marking_guide_link} target="_blank" rel="noopener noreferrer">
              {t("practice.markingGuide")}
            </a>
          )}
        </div>
      </div>

      <h2 className="section">{t("quiz.review")}</h2>
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
  const pending = useRef({});
  // Server clock minus browser clock, so the countdown is right even if the phone's time is off.
  const offset = useMemo(() => new Date(initial.server_now).getTime() - Date.now(), [initial.server_now]);

  const question = attempt.questions[index];
  const immediate = attempt.quiz.feedback_mode === "immediate";
  const total = attempt.questions.length;

  const save = useCallback(
    async (questionId) => {
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
        setSaving("saved");
      } catch (e) {
        setError(e);
        setSaving("idle");
        if (e.status === 400 && /time is up/i.test(e.message)) onFinished();
      }
    },
    [attempt.id, onFinished],
  );

  const flush = useCallback(async () => {
    Object.values(timers.current).forEach(clearTimeout);
    timers.current = {};
    await Promise.all(Object.keys(pending.current).map((id) => save(Number(id))));
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
    await flush();
    try {
      const updated = await api(`/attempts/${attempt.id}/check/`, { method: "POST", body: { question: question.id } });
      setAttempt((a) => ({ ...a, questions: a.questions.map((q) => (q.id === updated.id ? updated : q)) }));
    } catch (e) {
      setError(e);
    }
  }

  const submit = useCallback(
    async (force = false) => {
      const unanswered = attempt.questions.filter((q) => !isAnswered(q, answers[q.id])).length;
      const message = `${t("quiz.confirmSubmit")}${unanswered ? `\n\n${t("quiz.unanswered", { n: unanswered })}` : ""}`;
      if (!force && !window.confirm(message)) return;
      setSubmitting(true);
      try {
        await flush();
        await api(`/attempts/${attempt.id}/submit/`, { method: "POST" });
        onFinished(force ? t("quiz.timeUp") : null);
      } catch (e) {
        setError(e);
        setSubmitting(false);
      }
    },
    [attempt, answers, flush, onFinished, t],
  );

  const onExpire = useCallback(() => submit(true), [submit]);

  useEffect(() => {
    const warn = (e) => {
      if (Object.keys(pending.current).length) {
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
            <span className="small muted" aria-live="polite">
              {saving === "saving" ? t("quiz.saving") : saving === "saved" ? `✓ ${t("quiz.saved")}` : ""}
            </span>
            {attempt.deadline && <Timer deadline={attempt.deadline} offset={offset} onExpire={onExpire} />}
          </div>
        </div>
        <nav className="qnav" style={{ marginTop: 10 }} aria-label="Questions">
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
              {t("quiz.submit")} ✓
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
  const finished = useCallback(
    (message) => {
      if (message) setNotice(message);
      state.reload();
    },
    [state],
  );
  return (
    <Loader state={state}>
      {(attempt) =>
        attempt.status === "in_progress" ? (
          <Player key={attempt.id} initial={attempt} onFinished={finished} />
        ) : (
          <>
            {notice && <div className="alert alert-warn quiz-shell" style={{ marginBottom: 12 }}>{notice}</div>}
            <Results attempt={attempt} />
          </>
        )
      }
    </Loader>
  );
}
