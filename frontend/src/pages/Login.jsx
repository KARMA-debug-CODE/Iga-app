import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import { formatDay } from "../hooks";
import { useI18n } from "../i18n";
import { usePageMeta } from "../pageMeta";
import { useSiteInfo } from "../site";
import AuthShell from "./AuthShell";

/** Log in. `team`: the Iga team's way in while Iga is being updated (/team, see Maintenance.jsx). */
export default function Login({ team = false }) {
  const { login, notice } = useAuth();
  const { t, lang } = useI18n();
  usePageMeta("login");
  const navigate = useNavigate();
  const location = useLocation();
  const site = useSiteInfo();
  // After "Delete my account": when it will happen, and how to keep the account.
  const deletionDue = notice?.key === "deletionScheduled" ? notice.date : null;
  const [form, setForm] = useState({ identifier: "", password: "", otp: "" });
  const [needOtp, setNeedOtp] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(form.identifier, form.password, form.otp || undefined);
      navigate(location.state?.from || "/", { replace: true });
    } catch (err) {
      if (err.data?.otp_required) setNeedOtp(true);
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title={team ? t("auth.teamTitle") : t("auth.welcomeBack")}>
      {team && site.data?.maintenance && (
        <p className="alert alert-info small" role="note">
          {t("auth.teamNote")}
        </p>
      )}
      {deletionDue && (
        <p className="alert alert-warn small" role="status">
          {t("privacy.delete.done", { date: formatDay(deletionDue, lang) })}
        </p>
      )}
      <form className="form" onSubmit={submit}>
        <label>
          {t("auth.identifier")}
          <input value={form.identifier} onChange={update("identifier")} autoComplete="username" required autoFocus />
        </label>
        <label>
          {t("auth.password")}
          <input type="password" value={form.password} onChange={update("password")} autoComplete="current-password" required />
        </label>
        {needOtp && (
          <label>
            {t("auth.otp")}
            <input value={form.otp} onChange={update("otp")} inputMode="numeric" autoComplete="one-time-code" maxLength={8} required />
          </label>
        )}
        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}
        <button className="btn btn-block" disabled={busy}>
          {t("auth.login")}
        </button>
        <p className="muted small" style={{ margin: 0, textAlign: "center" }}>
          <Link to="/forgot-password">{t("reset.forgotLink")}</Link>
        </p>
        <p className="muted small" style={{ margin: 0, textAlign: "center" }}>
          {t("auth.noAccount")} <Link to="/register">{t("auth.register")}</Link>
        </p>
      </form>
    </AuthShell>
  );
}
