// Accounts a teacher created (or reset) start with a temporary password.
// The student picks their own here before using the rest of the app, and, for a new roster account, accepts
// the Terms of Use and Privacy Policy at the same time.
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import ConsentCheckbox from "../components/ConsentCheckbox";
import { ErrorMessage } from "../components/ui";
import { useI18n } from "../i18n";
import { loadSiteInfo } from "../site";
import AuthShell from "./AuthShell";

export default function FirstLogin() {
  const { user, reloadUser, logout } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    repeat: "",
  });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const askConsent = Boolean(user.consent_required);
  const [accepted, setAccepted] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError(null);
    if (form.new_password !== form.repeat) {
      setError(new Error(t("firstLogin.mismatch")));
      return;
    }
    setBusy(true);
    try {
      await api("/auth/password/", {
        method: "POST",
        body: {
          current_password: form.current_password,
          new_password: form.new_password,
        },
      });
      if (askConsent && accepted) {
        // If this fails, the app asks again on the next page (ConsentGate): the new password is already saved.
        const site = await loadSiteInfo().catch(() => null);
        if (site) await api("/auth/accept-terms/", { method: "POST", body: { version: site.legal.version } }).catch(() => {});
      }
      await reloadUser();
      navigate("/", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const field = (name) => ({
    value: form[name],
    onChange: (e) => setForm({ ...form, [name]: e.target.value }),
    required: true,
  });

  return (
    <AuthShell title={t("firstLogin.title", { name: user.first_name || user.username })}>
      <p className="muted">{t("firstLogin.intro")}</p>
      <form className="form" onSubmit={submit}>
        <label>
          {t("firstLogin.temporary")}
          <input type="password" autoComplete="current-password" {...field("current_password")} />
        </label>
        <label>
          {t("profile.newPassword")}
          <input type="password" autoComplete="new-password" minLength={8} {...field("new_password")} />
        </label>
        <label>
          {t("firstLogin.repeat")}
          <input type="password" autoComplete="new-password" minLength={8} {...field("repeat")} />
        </label>
        <p className="small muted">{t("firstLogin.tips")}</p>
        {askConsent && <ConsentCheckbox checked={accepted} onChange={setAccepted} student={user.role === "student"} />}
        <ErrorMessage error={error} />
        <button className="btn" disabled={busy}>
          {t("firstLogin.save")}
        </button>
        <button type="button" className="btn btn-ghost" onClick={logout}>
          {t("nav.logout")}
        </button>
      </form>
    </AuthShell>
  );
}
