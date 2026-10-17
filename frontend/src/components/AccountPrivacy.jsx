// Profile -> Privacy: what the account accepted, "Download my data" and "Delete my account" (the rights the
// Privacy Policy describes). Both actions ask for the password first (the server's step-up, StepUpDialog).
import { useState } from "react";
import { Link } from "react-router-dom";

import { api, saveFile } from "../api";
import { useAuth } from "../auth";
import { formatDate, formatDay } from "../hooks";
import { useI18n } from "../i18n";
import { useSiteInfo } from "../site";
import { Icon } from "./Icon";
import { ErrorMessage } from "./ui";

export function PrivacySummary() {
  const { user } = useAuth();
  const { t, lang } = useI18n();
  const version = /^\d{4}-\d{2}-\d{2}$/.test(user.terms_version || "") ? formatDay(user.terms_version, lang) : user.terms_version;
  return (
    <div className="card profile-card">
      <h2>
        <Icon name="shield" /> {t("privacy.title")}
      </h2>
      <p className="muted small">{t("privacy.intro")}</p>
      {user.terms_accepted_at && (
        <p className="small">{t("privacy.accepted", { version, date: formatDate(user.terms_accepted_at, lang) })}</p>
      )}
      <div className="row">
        <Link className="btn btn-secondary btn-sm" to="/privacy">
          <Icon name="file" size={16} /> {t("site.privacy")}
        </Link>
        <Link className="btn btn-secondary btn-sm" to="/terms">
          <Icon name="file" size={16} /> {t("site.terms")}
        </Link>
        <Link className="btn btn-ghost btn-sm" to="/contact">
          <Icon name="mail" size={16} /> {t("site.contact")}
        </Link>
      </div>
    </div>
  );
}

export function DownloadData() {
  const { t } = useI18n();
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function download() {
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      const blob = await api("/auth/my-data/", { as: "blob" });
      saveFile(blob, `iga-my-data-${new Date().toISOString().slice(0, 10)}.json`);
      setDone(true);
    } catch (err) {
      if (err?.message !== "cancelled") setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card profile-card">
      <h2>
        <Icon name="download" /> {t("privacy.download.title")}
      </h2>
      <p className="muted small">{t("privacy.download.help")}</p>
      <ErrorMessage error={error} />
      {done && (
        <div className="alert alert-success" role="status">
          {t("privacy.download.done")}
        </div>
      )}
      <div>
        <button className="btn btn-secondary" onClick={download} disabled={busy}>
          <Icon name="download" size={18} /> {t("privacy.download.button")}
        </button>
      </div>
    </div>
  );
}

export function DeleteAccount() {
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const site = useSiteInfo();
  const [understood, setUnderstood] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const days = site.data?.retention?.deletion_grace_days;

  if (user.role === "admin") {
    return (
      <div className="card profile-card">
        <h2>
          <Icon name="trash" /> {t("privacy.delete.title")}
        </h2>
        <p className="muted small">{t("privacy.delete.team")}</p>
      </div>
    );
  }

  async function remove(event) {
    event.preventDefault();
    if (!window.confirm(t("privacy.delete.ask"))) return;
    setBusy(true);
    setError(null);
    try {
      const data = await api("/auth/delete-account/", { method: "POST", body: { confirm: true } });
      // Every session has ended; the log in page that follows says when the account goes, and how to keep it.
      await logout({ notice: { key: "deletionScheduled", date: data.deletion_due_at } });
    } catch (err) {
      if (err?.message !== "cancelled") setError(err);
      setBusy(false);
    }
  }

  return (
    <form className="card profile-card danger-zone" onSubmit={remove}>
      <h2>
        <Icon name="trash" /> {t("privacy.delete.title")}
      </h2>
      <p className="small">{t("privacy.delete.help")}</p>
      {days !== undefined && <p className="small">{t("privacy.delete.grace", { days })}</p>}
      <p className="muted small">{t("privacy.delete.kept")}</p>
      <label className="check">
        <input type="checkbox" checked={understood} onChange={(e) => setUnderstood(e.target.checked)} required />
        {t("privacy.delete.confirm")}
      </label>
      <ErrorMessage error={error} />
      <div>
        <button className="btn btn-danger" disabled={!understood || busy}>
          <Icon name="trash" size={18} /> {t("privacy.delete.button")}
        </button>
      </div>
    </form>
  );
}
