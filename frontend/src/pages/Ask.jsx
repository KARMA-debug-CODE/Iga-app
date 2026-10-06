import { useEffect, useRef, useState } from "react";

import { api, results } from "../api";
import { useAuth } from "../auth";
import { LockedNotice } from "../components/Locked";
import Markdown from "../components/Markdown";
import { useTutorStatus } from "../components/TutorPanel";
import { ErrorMessage, Spinner } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

const STARTERS = ["ask.s.explain", "ask.s.steps", "ask.s.quiz", "ask.s.plan", "ask.s.summary", "ask.s.remember"];

// The conversation lasts for this browser tab, per student; logging out clears it (offline.js).
const storageKey = (user) => `iga.ask.${user.id}`;

function loadSaved(user) {
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey(user)) || "null");
    if (saved && Array.isArray(saved.messages)) return { subject: saved.subject || "", messages: saved.messages };
  } catch {
    /* storage blocked or damaged: start a fresh chat */
  }
  return { subject: "", messages: [] };
}

/** "Ask AI": a full-page study helper. It uses the same tutor as lessons and quizzes. */
export default function Ask() {
  const { user } = useAuth();
  const { t, lang } = useI18n();
  const status = useTutorStatus();
  const subjects = useApi("/subjects/", { params: { grade: user.grade || undefined, lang } });
  const [saved] = useState(() => loadSaved(user));
  const [subject, setSubject] = useState(saved.subject);
  const [messages, setMessages] = useState(saved.messages);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const log = useRef(null);
  const box = useRef(null);

  useEffect(() => {
    try {
      sessionStorage.setItem(storageKey(user), JSON.stringify({ subject, messages }));
    } catch {
      /* private window or full storage: the chat still works, it just isn't kept */
    }
  }, [user, subject, messages]);

  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [messages.length, busy]);

  if (status.loading) return <Spinner />;

  const header = (
    <div className="page-header">
      <h1>🤖 {t("ask.title")}</h1>
      <p>{t("ask.intro")}</p>
    </div>
  );

  if (!status.enabled) {
    return (
      <>
        {header}
        {status.reason === "subscription_required" ? (
          <LockedNotice />
        ) : (
          <div className="card" role="note">
            <strong>{t("ask.offTitle")}</strong>
            <p className="small muted" style={{ margin: "4px 0 0" }}>
              {t("ask.off")}
            </p>
          </div>
        )}
      </>
    );
  }

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
        body: { message, history, subject: subject || undefined, lang },
      });
      setMessages((current) => [...current, { role: "assistant", content: res.reply }]);
    } catch (err) {
      setError(err);
      setMessages(history);
      setInput(message);
    } finally {
      setBusy(false);
      box.current?.focus();
    }
  }

  function newChat() {
    setMessages([]);
    setError(null);
    setInput("");
    box.current?.focus();
  }

  const subjectList = results(subjects.data);
  const chosen = subjectList.find((s) => s.code === subject);

  return (
    <>
      {header}
      <section className="card ask" aria-label={t("ask.title")}>
        <div className="spread ask-bar">
          <div className="ask-subject">
            <label className="small muted" htmlFor="ask-subject">
              {t("ask.subject")}
            </label>
            <select id="ask-subject" value={subject} onChange={(e) => setSubject(e.target.value)} disabled={busy}>
              <option value="">{t("ask.anySubject")}</option>
              {subjectList.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.icon ? `${s.icon} ` : ""}
                  {s.display_name || s.name}
                </option>
              ))}
            </select>
          </div>
          {messages.length > 0 && (
            <button className="btn btn-secondary btn-sm" onClick={newChat} disabled={busy}>
              {t("ask.newChat")}
            </button>
          )}
        </div>
        <p className="small muted" style={{ margin: "8px 0" }}>
          {t("tutor.disclaimer")}
        </p>
        <div className="chat-log ask-log" ref={log} aria-live="polite">
          {messages.length === 0 && (
            <div className="ask-empty">
              <p>
                {chosen
                  ? t("ask.helloSubject", { subject: chosen.display_name || chosen.name })
                  : t("ask.hello")}
              </p>
              <div className="chips wrap">
                {STARTERS.map((key) => (
                  <button key={key} className="chip" onClick={() => send(t(key))} disabled={busy}>
                    {t(key)}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`bubble ${m.role === "user" ? "mine" : ""}`}>
              {m.role === "assistant" ? <Markdown interactive={false}>{m.content}</Markdown> : m.content}
            </div>
          ))}
          {busy && <div className="bubble muted">{t("tutor.thinking")}</div>}
        </div>
        <ErrorMessage error={error} />
        <form
          className="chat-form"
          style={{ marginTop: 8 }}
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <label className="sr-only" htmlFor="ask-input">
            {t("ask.placeholder")}
          </label>
          <textarea
            id="ask-input"
            ref={box}
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                send(input);
              }
            }}
            placeholder={t("ask.placeholder")}
            maxLength={2000}
          />
          <button className="btn" disabled={busy || !input.trim()}>
            {t("groups.send")}
          </button>
        </form>
      </section>
    </>
  );
}
