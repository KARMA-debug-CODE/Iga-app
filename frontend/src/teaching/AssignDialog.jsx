import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { ErrorMessage } from "../components/ui";
import { useI18n } from "../i18n";

/** Assign one part of a pack (the quiz or a worksheet level) to its class, with an optional due date. */
export default function AssignDialog({ packId, what, classroomId, onClose }) {
  const { t } = useI18n();
  const [due, setDue] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = { what, ...(due ? { due_at: new Date(due).toISOString() } : {}) };
      setResult(await api(`/teaching/packs/${packId}/assign/`, { method: "POST", body }));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <div className="pack-assign pack-assigned" role="status">
        <p>{result.created ? t("packs.assigned") : t("packs.alreadyAssigned")}</p>
        {result.dropped > 0 && <p className="muted">{t("packs.dropped", { n: result.dropped })}</p>}
        <Link to={`/classes/${classroomId}`}>{t("packs.openClass")}</Link>
      </div>
    );
  }
  return (
    <form className="pack-assign" onSubmit={submit}>
      <label>
        {t("packs.dueDate")}
        <input type="datetime-local" value={due} onChange={(e) => setDue(e.target.value)} />
      </label>
      <div className="pack-assign-actions">
        <button type="submit" className="btn btn-sm" disabled={busy}>
          {t("packs.assignConfirm")}
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
          {t("common.cancel")}
        </button>
      </div>
      {error && <ErrorMessage error={error} />}
    </form>
  );
}
