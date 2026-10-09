import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { results } from "../api";
import { useAuth } from "../auth";
import { LockedNotice } from "../components/Locked";
import {
  finishedMessages,
  SantaForm,
  SantaLog,
  SantaMark,
  SantaNote,
  SantaState,
  useSantaChat,
  useScrollToEnd,
  useTutorStatus,
} from "../components/Santa";
import { ErrorMessage, Spinner } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

const STARTERS = ["ask.s.explain", "ask.s.steps", "ask.s.quiz", "ask.s.plan", "ask.s.summary", "ask.s.remember"];

// The conversation lasts for this browser tab, per student; logging out clears it (offline.js).
const storageKey = (user) => `iga.ask.${user.id}`;

function loadSaved(user) {
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey(user)) || "null");
    if (saved && Array.isArray(saved.messages)) return { subject: saved.subject || "", messages: finishedMessages(saved.messages) };
  } catch {
    /* storage blocked or damaged: start a fresh chat */
  }
  return { subject: "", messages: [] };
}

/** The Santa page: a full-page study helper. It is the same Santa as in lessons and quizzes. */
export default function Ask() {
  const { user } = useAuth();
  const { t, lang } = useI18n();
  const status = useTutorStatus();
  const subjects = useApi("/subjects/", { params: { grade: user.grade || undefined, lang } });
  const [saved] = useState(() => loadSaved(user));
  const [subject, setSubject] = useState(saved.subject);
  const [input, setInput] = useState("");
  const chat = useSantaChat({ scope: { subject: subject || undefined }, lang, initial: saved.messages });
  const log = useRef(null);
  const box = useRef(null);
  useScrollToEnd(log, chat.messages, chat.phase);

  useEffect(() => {
    try {
      sessionStorage.setItem(storageKey(user), JSON.stringify({ subject, messages: finishedMessages(chat.messages) }));
    } catch {
      /* private window or full storage: the chat still works, it just isn't kept */
    }
  }, [user, subject, chat.messages]);

  if (status.loading) return <Spinner />;

  const header = (
    <div className="page-header santa-header">
      <h1>
        <SantaMark size={36} />
        {t("ask.title")}
      </h1>
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
          <ErrorMessage error={new Error(t("errors.network"))} onRetry={status.retry} />
        )}
      </>
    );
  }

  if (status.state === "exam") {
    return (
      <>
        {header}
        <SantaState status={status} />
      </>
    );
  }

  async function start(text) {
    if (!(await chat.send(text))) setInput(text);
    box.current?.focus();
  }

  const subjectList = results(subjects.data);
  const chosen = subjectList.find((s) => s.code === subject);

  return (
    <>
      {header}
      <SantaState status={status} />
      <section className="card ask" aria-label={t("ask.title")}>
        <div className="spread ask-bar">
          <div className="ask-subject">
            <label className="small muted" htmlFor="ask-subject">
              {t("ask.subject")}
            </label>
            <select id="ask-subject" value={subject} onChange={(e) => setSubject(e.target.value)} disabled={chat.busy}>
              <option value="">{t("ask.anySubject")}</option>
              {subjectList.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.display_name || s.name}
                </option>
              ))}
            </select>
          </div>
          {chat.messages.length > 0 && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                chat.reset();
                setInput("");
                box.current?.focus();
              }}
              disabled={chat.busy}
            >
              {t("ask.newChat")}
            </button>
          )}
        </div>
        <div style={{ marginTop: 8 }}>
          <SantaNote privacy />
        </div>
        <SantaLog chat={chat} logRef={log} className="ask-log">
          {chat.messages.length === 0 && (
            <div className="ask-empty">
              <p>{chosen ? t("ask.helloSubject", { subject: chosen.display_name || chosen.name }) : t("ask.hello")}</p>
              <div className="chips wrap">
                {STARTERS.map((key) => (
                  <button key={key} className="chip" onClick={() => start(t(key))} disabled={chat.busy}>
                    {t(key)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </SantaLog>
        <ErrorMessage error={chat.error} />
        {chat.error?.data?.attempt && (
          <Link className="btn btn-sm" to={`/attempts/${chat.error.data.attempt}`} style={{ marginBottom: 8 }}>
            {t("ask.openExam")}
          </Link>
        )}
        <div style={{ marginTop: 8 }}>
          <SantaForm
            id="ask-input"
            chat={chat}
            value={input}
            onChange={setInput}
            multiline
            inputRef={box}
            placeholder={t("ask.placeholder")}
          />
        </div>
      </section>
    </>
  );
}
