import { useEffect, useRef, useState } from "react";

import { useI18n } from "../i18n";

/**
 * Program output, like a terminal. When the program is waiting for keyboard input, an answer line appears
 * after the last output (the prompt); Enter sends it, and what was typed stays in the output, as in a terminal.
 * entries: [{ stream: "stdout" | "stderr" | "stdin" | "compile" | "info" | "result", text }]
 */
export default function Console({ entries, waiting, onAnswer, status, empty, minHeight = 300, label }) {
  const { t } = useI18n();
  const [answer, setAnswer] = useState("");
  const box = useRef(null);
  const input = useRef(null);

  useEffect(() => {
    if (box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [entries, waiting, status]);

  useEffect(() => {
    if (waiting) input.current?.focus({ preventScroll: true });
  }, [waiting]);

  function onKeyDown(event) {
    if (event.key !== "Enter" || event.nativeEvent.isComposing) return;
    event.preventDefault();
    const text = answer;
    setAnswer("");
    onAnswer(text);
  }

  return (
    // Clicking anywhere in the console while the program waits puts the cursor on the answer line.
    <div className="console" ref={box} style={{ minHeight }} onClick={() => waiting && input.current?.focus()} aria-label={label}>
      <pre className="console-output" aria-live="polite">
        {entries.map((entry, i) => (
          <span key={i} className={`out-${entry.stream}`}>
            {entry.text}
          </span>
        ))}
        {waiting && (
          <input
            ref={input}
            className="console-input"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={onKeyDown}
            aria-label={t("console.answer")}
            title={t("console.answerHint")}
            style={{ width: `${Math.max(answer.length + 2, 14)}ch` }}
            autoComplete="off"
            autoCapitalize="off"
            autoCorrect="off"
            spellCheck={false}
          />
        )}
        {status && <span className="out-info">{status}</span>}
        {!entries.length && !status && !waiting && <span className="out-info">{empty}</span>}
      </pre>
      {waiting && <p className="console-hint">{t("console.answerHint")}</p>}
    </div>
  );
}
