// Accounts a teacher created (or reset) start with a temporary password.
// The student picks their own here before using the rest of the app.
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import { ErrorMessage } from "../components/ui";
import { useI18n } from "../i18n";
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
