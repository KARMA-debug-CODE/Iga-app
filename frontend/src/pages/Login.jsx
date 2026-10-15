import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import AuthShell from "./AuthShell";

export default function Login() {
  const { login } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
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
    <AuthShell title={t("auth.welcomeBack")}>
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
