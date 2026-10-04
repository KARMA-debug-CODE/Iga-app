import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import { GRADES } from "../components/ui";
import { useI18n } from "../i18n";
import AuthShell from "./AuthShell";

export default function Register() {
  const { register } = useAuth();
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    role: "student",
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    password: "",
    grade: "S1",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = { ...form, preferred_language: lang };
      if (payload.role !== "student") payload.grade = "";
      if (!payload.email) delete payload.email;
      await register(payload);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title={t("auth.register")}>
      <form className="form" onSubmit={submit}>
        <div>
          <div style={{ fontWeight: 600, fontSize: "0.92rem", marginBottom: 6 }}>{t("auth.iAm")}</div>
          <div className="chips">
            {["student", "teacher", "parent"].map((role) => (
              <button
                type="button"
                key={role}
                className={`chip ${form.role === role ? "active" : ""}`}
                aria-pressed={form.role === role}
                onClick={() => setForm((f) => ({ ...f, role }))}
              >
                {{ student: "🎒 ", teacher: "🧑🏽‍🏫 ", parent: "👨‍👩‍👧 " }[role]}
                {t(`auth.${role}`)}
              </button>
            ))}
          </div>
        </div>
        <div className="form-row">
          <label>
            {t("auth.firstName")}
            <input value={form.first_name} onChange={update("first_name")} autoComplete="given-name" required />
          </label>
          <label>
            {t("auth.lastName")}
            <input value={form.last_name} onChange={update("last_name")} autoComplete="family-name" />
          </label>
        </div>
        <label>
          {t("auth.username")}
          <input value={form.username} onChange={update("username")} autoComplete="username" required pattern="[\w.@+-]+" />
        </label>
        <label>
          {t("auth.email")}
          <input type="email" value={form.email} onChange={update("email")} autoComplete="email" />
        </label>
        <label>
          {t("auth.password")}
          <input type="password" value={form.password} onChange={update("password")} autoComplete="new-password" minLength={8} required />
          <span className="small muted" style={{ fontWeight: 400 }}>
            {t("auth.passwordHint")}
          </span>
        </label>
        <div className="form-row">
          {form.role === "student" && (
            <label>
              {t("auth.grade")}
              <select value={form.grade} onChange={update("grade")}>
                {GRADES.map((g) => (
                  <option key={g}>{g}</option>
                ))}
              </select>
            </label>
          )}
        </div>
        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}
        <button className="btn btn-block" disabled={busy}>
          {t("auth.register")}
        </button>
        <p className="muted small" style={{ margin: 0, textAlign: "center" }}>
          {t("auth.haveAccount")} <Link to="/login">{t("auth.login")}</Link>
        </p>
      </form>
    </AuthShell>
  );
}
