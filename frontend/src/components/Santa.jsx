// Santa, Iga's learning assistant: what the Santa page and the panels in lessons and quizzes share.
// Answers are streamed from /api/tutor/stream/ (Server-Sent Events over a POST, read with fetch), so the
// text appears while the school's server writes it, and Stop really stops it.
import "./Santa.css";

import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { api, ApiError, apiStream, NetworkError, readEvents } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { sitePath } from "../safeUrl";
import { Icon } from "./Icon";
import Markdown from "./Markdown";

// The server reads only the last 10 messages, so only those are sent (less mobile data).
const HISTORY_SENT = 10;
// While Santa writes, the text on screen is refreshed this often (Markdown and maths are re-drawn each time).
const REDRAW_MS = 80;

/** Santa's mark: a speech bubble with a spark, in Iga's sky blue and sun yellow. Decorative. */
export function SantaMark({ size = 24 }) {
  return (
    <svg className="santa-mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <path
        className="santa-mark-bubble"
        d="M16 2.5C8.5 2.5 2.5 7.9 2.5 14.6c0 3.7 1.9 7 4.8 9.2l-1.2 5.7 6.3-3.3c1.1.3 2.4.4 3.6.4 7.5 0 13.5-5.4 13.5-12S23.5 2.5 16 2.5z"
      />
      <path className="santa-mark-spark" d="M15 7.6l1.9 5.1 5.1 1.9-5.1 1.9L15 21.6l-1.9-5.1-5.1-1.9 5.1-1.9z" />
      <circle className="santa-mark-sun" cx="23.6" cy="8.6" r="2.4" />
    </svg>
  );
}

// --- Status -----------------------------------------------------------------------------------

const OFF = { enabled: false, reason: "", state: "", exam: null, allowance: null };
// How long a status answer is reused. "ready" rarely changes; a model waking up does, and an exam ends when
// the student submits it, so those are asked again soon (an exam on the next page that needs it).
const STATUS_MS = { ready: 120_000, exam: 0 };
const OTHER_STATUS_MS = 15_000;
const statuses = new Map(); // user and access -> { promise, value, at }

function normalStatus(s) {
  const enabled = Boolean(s?.enabled);
  return {
    enabled,
    reason: s?.reason || "",
    state: s?.state || (enabled ? "ready" : ""),
    exam: s?.exam || null,
    allowance: s?.allowance || null,
  };
}

/** After an answer, the remembered status of this user shows what is left of their allowance. */
function noteAllowance(userId, allowance) {
  for (const [key, entry] of statuses) {
    if (key.startsWith(`${userId}:`) && entry.value) entry.value = { ...entry.value, allowance };
  }
}

function freshStatus(key) {
  const entry = statuses.get(key);
  if (!entry) return null;
  if (!entry.value) return entry; // still being asked
  return Date.now() - entry.at < (STATUS_MS[entry.value.state] ?? OTHER_STATUS_MS) ? entry : null;
}

function askStatus(key) {
  const entry = { value: null, at: 0 };
  entry.promise = api("/tutor/status/")
    .then((s) => {
      entry.value = normalStatus(s);
      entry.at = Date.now();
      return entry.value;
    })
    .catch(() => {
      // Not kept: the next page or retry() asks again.
      if (statuses.get(key) === entry) statuses.delete(key);
      return { ...OFF, reason: "unreachable" };
    });
  statuses.set(key, entry);
  return entry;
}

/**
 * Santa's status for this user: `{ enabled, reason, state, exam, allowance, loading, retry }`.
 * enabled is false when the school hasn't subscribed (reason "subscription_required") or the server couldn't
 * be asked (reason "unreachable"). state: "ready", "loading" (the model is waking up), "unavailable" (its
 * server isn't answering), "not_installed" (answers come from the lessons) or "exam" (`exam` says which).
 * allowance: what is left of the student's questions for Santa's model (see SantaAllowance).
 */
export function useTutorStatus() {
  const { user } = useAuth();
  const key = user ? `${user.id}:${user.access?.premium ? 1 : 0}` : "";
  const [status, setStatus] = useState(() => {
    const entry = key && freshStatus(key);
    return entry?.value ? { key, ...entry.value } : { key: "", ...OFF };
  });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!key) return undefined;
    const entry = freshStatus(key) || askStatus(key);
    let alive = true;
    entry.promise.then((value) => alive && setStatus({ key, ...value }));
    return () => {
      alive = false;
    };
  }, [key, attempt]);
  const retry = () => {
    statuses.delete(key);
    setStatus({ key: "", ...OFF });
    setAttempt((n) => n + 1);
  };
  if (!key) return { ...OFF, loading: false, retry };
  return status.key === key ? { ...status, loading: false, retry } : { ...OFF, loading: true, retry };
}

// --- Conversation -------------------------------------------------------------------------------

/** The finished question-and-answer pairs (a question still being answered, or never answered, is left out). */
export function finishedMessages(messages) {
  const out = [];
  for (let i = 0; i + 1 < messages.length; i += 2) {
    const [question, answer] = [messages[i], messages[i + 1]];
    if (question?.role === "user" && answer?.role === "assistant" && !answer.pending && answer.content?.trim()) {
      out.push(question, answer);
    }
  }
  return out;
}

// What a screen reader says when the answer is complete: the text without Markdown and LaTeX symbols.
const plainText = (text) =>
  text
    .replace(/[*_`#>$\\{}]/g, "")
    .replace(/\s+/g, " ")
    .trim();

/**
 * A conversation with Santa. `scope` is what the student is looking at ({lesson}, {attempt, question} or
 * {subject}); `lang` the language Santa answers in. Messages come in pairs: the question, then Santa's answer
 * ({content, sources, tools, fallback, pending, stopped}).
 */
export function useSantaChat({ scope, lang, initial = [] }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const [messages, setMessages] = useState(initial);
  const [allowance, setAllowance] = useState(null); // from the last answer: what is left today
  const [phase, setPhase] = useState(""); // "" | "waiting" (no text yet) | "writing"
  const [error, setError] = useState(null);
  const [announcement, setAnnouncement] = useState("");
  const controller = useRef(null);
  const conversation = useRef(0); // changes on "New chat", so a stopped answer can't land in the new one

  // Leaving the page stops the answer, so the school's server doesn't keep writing it.
  useEffect(() => () => controller.current?.abort(), []);

  /** Ask Santa. Resolves to false when nothing was answered, so the question can go back in the box. */
  async function send(text) {
    const message = text.trim();
    if (!message || controller.current) return true;
    const history = finishedMessages(messages)
      .slice(-HISTORY_SENT)
      .map(({ role, content }) => ({ role, content }));
    const ctrl = new AbortController();
    controller.current = ctrl;
    const mine = conversation.current;
    const answer = { role: "assistant", content: "", pending: true, sources: [], tools: [] };
    const update = (patch) => {
      Object.assign(answer, patch);
      if (conversation.current === mine) setMessages((current) => [...current.slice(0, -1), { ...answer }]);
    };
    setMessages((current) => [...current, { role: "user", content: message }, { ...answer }]);
    setPhase("waiting");
    setError(null);
    setAnnouncement(t("tutor.thinking"));

    let written = "";
    let done = null;
    let failure = null;
    let redraw = null;
    try {
      const response = await apiStream("/tutor/stream/", {
        body: { message, history, ...scope, lang },
        signal: ctrl.signal,
      });
      await readEvents(response, (event) => {
        if (event.type === "delta") {
          written += event.text;
          if (!redraw) {
            redraw = setTimeout(() => {
              redraw = null;
              update({ content: written });
            }, REDRAW_MS);
          }
          setPhase("writing");
        } else if (event.type === "tool") {
          update({ tools: [...answer.tools, { expression: event.expression, result: event.result }] });
        } else if (event.type === "done") {
          done = event;
        } else if (event.type === "error") {
          failure = new Error(event.detail);
        }
      });
    } catch (err) {
      // Stop aborts the request. Anything else not from the server (the connection dropped while Santa
      // wrote, an unreadable piece) is shown as a network problem, in the student's language.
      if (err?.name !== "AbortError") failure = err instanceof ApiError || err instanceof NetworkError ? err : new NetworkError();
    } finally {
      clearTimeout(redraw);
      controller.current = null;
      setPhase("");
    }
    if (conversation.current !== mine) return true;

    if (done) {
      if (done.allowance) {
        setAllowance(done.allowance);
        if (user) noteAllowance(user.id, done.allowance);
      }
      update({
        content: done.reply,
        sources: done.sources || [],
        tools: done.tools || [],
        fallback: done.fallback || null,
        pending: false,
      });
      setAnnouncement(`${t("tutor.answered")} ${plainText(done.reply)}`);
      return true;
    }
    if (written.trim()) {
      // Stopped by the student, or the connection dropped half-way: keep what arrived.
      update({ content: written, pending: false, stopped: true });
      setAnnouncement(t("tutor.stopped"));
      if (failure) setError(failure);
      return true;
    }
    // Nothing arrived: take the question back, so it can be asked again.
    setMessages((current) => current.slice(0, -2));
    setAnnouncement("");
    if (failure) setError(failure);
    else if (!ctrl.signal.aborted) setError(new Error(t("tutor.noAnswer")));
    return false;
  }

  const stop = () => controller.current?.abort();

  function reset() {
    conversation.current += 1;
    stop();
    setMessages([]);
    setError(null);
    setAnnouncement("");
  }

  return { messages, phase, busy: phase !== "", error, announcement, allowance, send, stop, reset };
}

/** Keeps the newest message in view while Santa writes. */
export function useScrollToEnd(ref, messages, phase) {
  const last = messages.at(-1)?.content?.length || 0;
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [ref, messages.length, last, phase]);
}

function Typing() {
  const { t } = useI18n();
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 12_000);
    return () => clearTimeout(timer);
  }, []);
  return (
    <span className="santa-typing">
      <span className="santa-dots" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      <span className="small muted">{slow ? t("tutor.slow") : t("tutor.thinking")}</span>
    </span>
  );
}

function Answer({ message }) {
  const { t } = useI18n();
  const tools = (message.tools || []).filter((tool) => tool.result && !tool.result.startsWith("error"));
  return (
    <div className="santa-answer">
      <SantaMark size={26} />
      <div className="bubble santa-bubble">
        {message.content ? <Markdown interactive={false}>{message.content}</Markdown> : <Typing />}
        {tools.length > 0 && (
          <ul className="santa-tools small muted">
            {tools.map((tool, i) => (
              <li key={i}>
                <Icon name="calculator" size={14} /> {t("tutor.calc", tool)}
              </li>
            ))}
          </ul>
        )}
        {message.stopped && <p className="small muted santa-stopped">{t("tutor.stopped")}</p>}
        {message.sources?.length > 0 && (
          <div className="santa-sources">
            <span className="small muted">{t("tutor.sources")}</span>
            <ul>
              {message.sources.map((source) => (
                <li key={source.slug}>
                  <Link to={sitePath(source.url) || `/lessons/${encodeURIComponent(source.slug)}`}>
                    <Icon name="book" size={14} />
                    {source.title}
                  </Link>
                  {source.section && <span className="small muted"> · {source.section}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * The conversation, newest at the bottom. Screen readers hear "Santa is thinking" and then the whole answer
 * once it is complete (from a separate live region), not every word as it arrives.
 */
export function SantaLog({ chat, logRef, className = "", children }) {
  const { t } = useI18n();
  return (
    <>
      <div
        className={`chat-log santa-log ${className}`}
        ref={logRef}
        role="log"
        aria-live="off"
        aria-label={t("tutor.conversation")}
        aria-busy={chat.busy}
        tabIndex={chat.messages.length ? 0 : undefined}
      >
        {children}
        {chat.messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="bubble mine">
              {m.content}
            </div>
          ) : (
            <Answer key={i} message={m} />
          ),
        )}
      </div>
      <div className="sr-only" role="status" aria-live="polite">
        {chat.announcement}
      </div>
    </>
  );
}

/** The question box with Send, which becomes Stop while Santa writes (the same button, so focus stays). */
export function SantaForm({ id, chat, value, onChange, multiline = false, inputRef, placeholder, label = placeholder }) {
  const { t } = useI18n();
  async function submit() {
    const message = value;
    if (!message.trim() || chat.busy) return;
    onChange("");
    if (!(await chat.send(message))) onChange(message);
  }
  const field = {
    id,
    ref: inputRef,
    value,
    placeholder,
    maxLength: 2000,
    onChange: (e) => onChange(e.target.value),
  };
  return (
    <form
      className="chat-form santa-form"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <label className="sr-only" htmlFor={id}>
        {label}
      </label>
      {multiline ? (
        <textarea
          {...field}
          rows={2}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
        />
      ) : (
        <input {...field} autoComplete="off" />
      )}
      <button
        type={chat.busy ? "button" : "submit"}
        className={`btn ${chat.busy ? "btn-secondary" : ""}`}
        onClick={
          chat.busy
            ? (e) => {
                // Stopping turns this button back into Send before the click ends: don't let it submit.
                e.preventDefault();
                chat.stop();
                inputRef?.current?.focus(); // ready for the next question
              }
            : undefined
        }
        disabled={!chat.busy && !value.trim()}
      >
        <Icon name={chat.busy ? "stop" : "send"} size={16} />
        {chat.busy ? t("tutor.stop") : t("groups.send")}
      </button>
    </form>
  );
}

/**
 * What is left of the student's questions for Santa's AI (`allowance` from the status or the last answer):
 * a quiet line while there is some, and a note when one is used up (Santa then answers from the lessons).
 */
export function SantaAllowance({ allowance }) {
  const { t } = useI18n();
  if (!allowance) return null;
  const { reached, questions_left_today: today, questions_per_day: perDay, questions_left_month: month } = allowance;
  if (reached) {
    return (
      <div className="alert alert-info santa-state santa-allowance" role="note">
        <Icon name="hourglass" />
        <div>
          <strong>{t(`tutor.limit.${reached}`)}</strong>
          <p>{t(`tutor.limit.${reached}.text`)}</p>
        </div>
      </div>
    );
  }
  const parts = [];
  if (today != null) parts.push(t("tutor.left.today", { n: today, total: perDay }));
  if (month != null && (today == null || month < today)) parts.push(t("tutor.left.month", { n: month }));
  const time = allowance.time_left_percent;
  if (time != null && time < 50) parts.push(t("tutor.left.time", { percent: time }));
  if (!parts.length) return null;
  return <p className="small muted santa-allowance">{parts.join(" · ")}</p>;
}

/** The honest note shown with every conversation. */
export function SantaNote({ privacy = false }) {
  const { t } = useI18n();
  return (
    <p className="small muted santa-note">
      {t("tutor.disclaimer")}
      {privacy && ` ${t("tutor.privacy")}`}
    </p>
  );
}

/** Explains a status other than "ready": waking up, not installed, not answering, or off during an exam. */
export function SantaState({ status }) {
  const { t } = useI18n();
  const { state, exam } = status;
  if (state === "exam") {
    return (
      <div className="alert alert-warn santa-state" role="note">
        <Icon name="lock" />
        <div>
          <strong>{t("tutor.state.exam")}</strong>
          <p>{t("tutor.state.exam.text", { quiz: exam?.quiz || "" })}</p>
          {exam?.attempt && (
            <Link className="btn btn-sm" to={`/attempts/${exam.attempt}`}>
              {t("ask.openExam")}
            </Link>
          )}
        </div>
      </div>
    );
  }
  if (!["loading", "not_installed", "unavailable"].includes(state)) return null;
  return (
    <div className="alert alert-info santa-state" role="note">
      <Icon name={state === "loading" ? "hourglass" : "book"} />
      <div>
        <strong>{t(`tutor.state.${state}`)}</strong>
        <p>{t(`tutor.state.${state}.text`)}</p>
      </div>
    </div>
  );
}
