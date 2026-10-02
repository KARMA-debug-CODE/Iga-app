import { useState } from "react";

import { api } from "../api";
import Markdown from "../components/Markdown";
import { Empty, ErrorMessage, Loader } from "../components/ui";
import { formatDate, useApi } from "../hooks";
import { useI18n } from "../i18n";

function MarkCard({ item, onMarked }) {
  const { t, lang } = useI18n();
  const [marks, setMarks] = useState("");
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(`/marking/${item.id}/mark/`, { method: "POST", body: { marks, feedback } });
      onMarked(item.id);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <div className="spread small muted">
        <span>
          <strong style={{ color: "var(--text)" }}>{item.student}</strong> · {item.subject} · {item.quiz}
        </span>
        <span>{formatDate(item.submitted_at, lang)}</span>
      </div>
      <Markdown interactive={false}>{item.question}</Markdown>
      <div>
        <strong className="small">{t("marking.answer")}</strong>
        <div className="alert" style={{ whiteSpace: "pre-wrap" }}>
          {item.answer_text || <em className="muted">{t("quiz.noAnswer")}</em>}
        </div>
      </div>
      {item.marking_guide && (
        <details>
          <summary className="small">{t("quiz.markingGuide")}</summary>
          <Markdown interactive={false}>{item.marking_guide}</Markdown>
        </details>
      )}
      <div className="form-row">
        <label>
          {t("marking.give", { n: Number(item.max_marks) })}
          <input type="number" min="0" max={item.max_marks} step="0.5" value={marks} onChange={(e) => setMarks(e.target.value)} required />
        </label>
        <label>
          {t("marking.feedback")}
          <input value={feedback} onChange={(e) => setFeedback(e.target.value)} />
        </label>
      </div>
      <ErrorMessage error={error} />
      <button className="btn" disabled={busy}>
        {t("marking.save")}
      </button>
    </form>
  );
}

export default function Marking() {
  const { t } = useI18n();
  const state = useApi("/marking/");
  return (
    <div style={{ maxWidth: 820 }}>
      <div className="page-header">
        <h1>✅ {t("marking.title")}</h1>
      </div>
      <Loader state={state}>
        {(items) =>
          items.length === 0 ? (
            <Empty icon="🎉">{t("marking.empty")}</Empty>
          ) : (
            <div className="stack">
              {items.map((item) => (
                <MarkCard key={item.id} item={item} onMarked={(id) => state.setData((list) => list.filter((x) => x.id !== id))} />
              ))}
            </div>
          )
        }
      </Loader>
    </div>
  );
}
