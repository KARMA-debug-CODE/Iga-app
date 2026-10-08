import { useEffect, useRef, useState } from "react";

import { api } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import Markdown from "./Markdown";
import { ErrorMessage } from "./ui";

const statusRequests = new Map();

const OFF = { enabled: false, reason: "" };

/**
 * The tutor's status for this user, asked once per user and access state:
 * `{ enabled, reason, loading, retry }`. reason is "subscription_required" when the tutor is on but
 * this student's school hasn't subscribed, and "unreachable" when the server couldn't be asked
 * (that answer isn't kept, so the next page or `retry()` asks again).
 */
export function useTutorStatus() {
  const { user } = useAuth();
  const key = user ? `${user.id}:${user.access?.premium ? 1 : 0}` : "";
  const [status, setStatus] = useState({ key: "", ...OFF });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!key) return undefined;
    if (!statusRequests.has(key)) {
      statusRequests.set(
        key,
        api("/tutor/status/")
          .then((s) => ({ enabled: Boolean(s?.enabled), reason: s?.reason || "" }))
          .catch(() => {
            statusRequests.delete(key);
            return { enabled: false, reason: "unreachable" };
          }),
      );
    }
    let alive = true;
    statusRequests.get(key).then((value) => alive && setStatus({ key, ...value }));
    return () => {
      alive = false;
    };
  }, [key, attempt]);
  const retry = () => {
    setStatus({ key: "", ...OFF });
    setAttempt((n) => n + 1);
  };
  if (!key) return { ...OFF, loading: false, retry };
  return status.key === key
    ? { enabled: status.enabled, reason: status.reason, loading: false, retry }
    : { ...OFF, loading: true, retry };
}

/** Whether the tutor is on and this user may use it. */
export function useTutorEnabled() {
  return useTutorStatus().enabled;
}

/**
 * A small chat with the AI tutor about what the student is looking at.
 * Pass `lesson` (slug) and/or `attempt` + `question` (ids); the server decides what
 * the tutor may see, so answers stay hidden until the student is allowed to see them.
 */
export default function TutorPanel({ lesson, attempt, question, starters = [], label, defaultOpen = false, lang: readingLang }) {
  const { t, lang: uiLang } = useI18n();
  const lang = readingLang || uiLang; // the tutor answers in the language the student is reading
  const enabled = useTutorEnabled();
  const [open, setOpen] = useState(defaultOpen);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const log = useRef(null);

  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [messages.length, busy]);

  if (!enabled) return null;

  async function send(text) {
    const message = text.trim();
    if (!message || busy) return;
    const history = messages;
    setMessages([...history, { role: "user", content: message }]);
    setInput("");
    setBusy(true);
    setError(null);
    try {
      const res = await api("/tutor/ask/", {
        method: "POST",
        body: { message, history, lesson, attempt, question, lang },
      });
      setMessages((current) => [...current, { role: "assistant", content: res.reply }]);
    } catch (err) {
      setError(err);
      setMessages(history);
      setInput(message);
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button className="btn btn-secondary btn-sm" onClick={() => setOpen(true)}>
        {label || t("tutor.open")}
      </button>
    );
  }

  return (
    <section className="card tutor" aria-label={t("tutor.title")}>
      <div className="spread">
        <strong>{t("tutor.title")}</strong>
        <button className="btn btn-ghost btn-sm" onClick={() => setOpen(false)} aria-label={t("common.close")}>
          ✕
        </button>
      </div>
      <p className="small muted" style={{ margin: "4px 0 10px" }}>
        {t("tutor.disclaimer")}
      </p>
      <div className="chat-log tutor-log" ref={log} aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role === "user" ? "mine" : ""}`}>
            {m.role === "assistant" ? <Markdown interactive={false}>{m.content}</Markdown> : m.content}
          </div>
        ))}
        {busy && <div className="bubble muted">{t("tutor.thinking")}</div>}
      </div>
      {messages.length === 0 && starters.length > 0 && (
        <div className="chips" style={{ flexWrap: "wrap", margin: "8px 0" }}>
          {starters.map((s) => (
            <button key={s} className="chip" onClick={() => send(s)} disabled={busy}>
              {s}
            </button>
          ))}
        </div>
      )}
      <ErrorMessage error={error} />
      <form
        className="chat-form"
        style={{ marginTop: 8 }}
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <label className="sr-only" htmlFor={`tutor-${lesson || ""}-${question || ""}`}>
          {t("tutor.placeholder")}
        </label>
        <input
          id={`tutor-${lesson || ""}-${question || ""}`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t("tutor.placeholder")}
          maxLength={2000}
          autoComplete="off"
        />
        <button className="btn" disabled={busy || !input.trim()}>
          {t("groups.send")}
        </button>
      </form>
    </section>
  );
}
