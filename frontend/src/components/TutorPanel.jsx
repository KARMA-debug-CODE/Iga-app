import { useEffect, useRef, useState } from "react";

import { useI18n } from "../i18n";
import { Icon } from "./Icon";
import { SantaForm, SantaLog, SantaMark, SantaNote, SantaState, useSantaChat, useScrollToEnd, useTutorStatus } from "./Santa";
import { ErrorMessage } from "./ui";

export { useTutorStatus };

/** Whether Santa is on and this user may use it. */
export function useTutorEnabled() {
  return useTutorStatus().enabled;
}

/**
 * A small chat with Santa about what the student is looking at.
 * Pass `lesson` (slug) and/or `attempt` + `question` (ids); the server decides what
 * Santa may see, so answers stay hidden until the student is allowed to see them.
 */
export default function TutorPanel({ lesson, attempt, question, starters = [], label, defaultOpen = false, lang: readingLang }) {
  const { t, lang: uiLang } = useI18n();
  const lang = readingLang || uiLang; // Santa answers in the language the student is reading
  const status = useTutorStatus();
  const [open, setOpen] = useState(defaultOpen);
  const [input, setInput] = useState("");
  const chat = useSantaChat({ scope: { lesson, attempt, question }, lang });
  const log = useRef(null);
  const box = useRef(null);
  const opened = useRef(defaultOpen);
  useScrollToEnd(log, chat.messages, chat.phase);

  useEffect(() => {
    // Opening the panel puts the cursor in the question box (not on page load).
    if (open && !opened.current) box.current?.focus();
    opened.current = open;
  }, [open]);

  if (!status.enabled) return null;

  if (!open) {
    return (
      <button className="btn btn-secondary btn-sm santa-open" onClick={() => setOpen(true)}>
        <SantaMark size={18} />
        {label || t("tutor.open")}
      </button>
    );
  }

  const id = `tutor-${lesson || ""}-${question || ""}`;
  return (
    <section className="card tutor" aria-label={t("tutor.title")}>
      <div className="spread">
        <strong className="santa-title">
          <SantaMark size={22} />
          {t("tutor.title")}
        </strong>
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => {
            chat.stop();
            setOpen(false);
          }}
          aria-label={t("common.close")}
        >
          <Icon name="close" />
        </button>
      </div>
      <SantaNote />
      <SantaState status={status} />
      {status.state !== "exam" && (
        <>
          <SantaLog chat={chat} logRef={log} className="tutor-log" />
          {chat.messages.length === 0 && starters.length > 0 && (
            <div className="chips wrap" style={{ margin: "8px 0" }}>
              {starters.map((s) => (
                <button key={s} className="chip" onClick={() => chat.send(s)} disabled={chat.busy}>
                  {s}
                </button>
              ))}
            </div>
          )}
          <ErrorMessage error={chat.error} />
          <div style={{ marginTop: 8 }}>
            <SantaForm id={id} chat={chat} value={input} onChange={setInput} inputRef={box} placeholder={t("tutor.placeholder")} />
          </div>
        </>
      )}
    </section>
  );
}
