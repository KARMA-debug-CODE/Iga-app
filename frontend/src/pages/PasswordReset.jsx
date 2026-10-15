// "Forgot your password?": ask for an emailed link, then choose a new password with it.
// The link's secret travels in the URL fragment (#...), which browsers never send to a server.
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { api } from "../api";
import { ErrorMessage } from "../components/ui";
import { useI18n } from "../i18n";
import AuthShell from "./AuthShell";

export function ForgotPassword() {
  const { t } = useI18n();
  const [identifier, setIdentifier] = useState("");
  const [sent, setSent] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await api("/auth/password-reset/", { method: "POST", body: { identifier } });
      setSent(data.detail);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title={t("reset.forgotTitle")}>
      {sent ? (
        <div className="stack">
          <div className="alert alert-success" role="status">
            {sent}
          </div>
          <p className="small muted">{t("reset.checkSpam")}</p>
          <p className="small muted">{t("reset.noEmail")}</p>
          <Link to="/login" className="btn btn-secondary btn-block">
            {t("reset.backToLogin")}
          </Link>
        </div>
      ) : (
        <form className="form" onSubmit={submit}>
          <p className="muted">{t("reset.forgotIntro")}</p>
          <label>
            {t("auth.identifier")}
            <input
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              autoComplete="username"
              maxLength={254}
              required
              autoFocus
            />
          </label>
          <ErrorMessage error={error} />
          <button className="btn btn-block" disabled={busy}>
            {t("reset.send")}
          </button>
          <p className="small muted" style={{ margin: 0 }}>
            {t("reset.noEmail")}
          </p>
          <p className="muted small" style={{ margin: 0, textAlign: "center" }}>
            <Link to="/login">{t("reset.backToLogin")}</Link>
          </p>
        </form>
      )}
    </AuthShell>
  );
}

function tokenFromHash(hash) {
  const raw = (hash || "").replace(/^#/, "");
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

export function ResetPassword() {
  const { t } = useI18n();
  const location = useLocation();
  const navigate = useNavigate();
  // Read the secret once, then take it out of the address bar (and the browser history).
  const [token] = useState(() => tokenFromHash(location.hash));
  const [form, setForm] = useState({ new_password: "", repeat: "" });
  const [done, setDone] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (location.hash) navigate(location.pathname, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError(null);
    if (form.new_password !== form.repeat) {
      setError(new Error(t("firstLogin.mismatch")));
      return;
    }
    setBusy(true);
    try {
      const data = await api("/auth/password-reset/confirm/", {
        method: "POST",
        body: { token, new_password: form.new_password },
      });
      setDone(data.detail);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <AuthShell title={t("reset.title")}>
        <div className="stack">
          <div className="alert alert-success" role="status">
            {done}
          </div>
          <Link to="/login" className="btn btn-block">
            {t("auth.login")}
          </Link>
        </div>
      </AuthShell>
    );
  }

  if (!token) {
    return (
      <AuthShell title={t("reset.title")}>
        <div className="stack">
          <div className="alert alert-error" role="alert">
            {t("reset.incompleteLink")}
          </div>
          <Link to="/forgot-password" className="btn btn-secondary btn-block">
            {t("reset.askAgain")}
          </Link>
        </div>
      </AuthShell>
    );
  }

  const field = (name) => ({
    value: form[name],
    onChange: (e) => setForm({ ...form, [name]: e.target.value }),
    required: true,
    minLength: 8,
    type: "password",
    autoComplete: "new-password",
  });

  return (
    <AuthShell title={t("reset.title")}>
      <form className="form" onSubmit={submit}>
        <p className="muted">{t("reset.intro")}</p>
        <label>
          {t("profile.newPassword")}
          <input {...field("new_password")} autoFocus />
        </label>
        <label>
          {t("firstLogin.repeat")}
          <input {...field("repeat")} />
        </label>
        <p className="small muted">{t("firstLogin.tips")}</p>
        <ErrorMessage error={error} />
        {error?.data?.code === "invalid_link" && (
          <Link to="/forgot-password" className="small">
            {t("reset.askAgain")}
          </Link>
        )}
        <button className="btn btn-block" disabled={busy}>
          {t("reset.save")}
        </button>
      </form>
    </AuthShell>
  );
}
