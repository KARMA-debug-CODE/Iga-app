import { useEffect, useState } from "react";

import { api } from "../api";
import { useAuth } from "../auth";
import { ErrorMessage, GRADES, Loader, useToast } from "../components/ui";
import { useApi } from "../hooks";
import { LANGUAGES, useI18n } from "../i18n";
import { getTheme, setTheme } from "../theme";

function TwoFactor() {
  const { user, setUser } = useAuth();
  const { t } = useI18n();
  const [setup, setSetup] = useState(null);
  const [otp, setOtp] = useState("");
  const [error, setError] = useState(null);

  async function begin() {
    setError(null);
    try {
      setSetup(await api("/auth/2fa/setup/", { method: "POST" }));
    } catch (e) {
      setError(e);
    }
  }

  async function confirm(path) {
    setError(null);
    try {
      setUser(await api(path, { method: "POST", body: { otp } }));
      setSetup(null);
      setOtp("");
    } catch (e) {
      setError(e);
    }
  }

  return (
    <div className="card">
      <h2>🔐 {t("profile.twoFactor")}</h2>
      <p className="muted">{user.totp_enabled ? t("profile.twoFactorOn") : t("profile.twoFactorOff")}</p>
      {setup && (
        <div className="stack">
          <p>{t("profile.enter2fa")}</p>
          <code className="code-display" style={{ fontSize: "1rem", wordBreak: "break-all" }}>
            {setup.secret}
          </code>
          <a href={setup.otpauth_uri} className="small">
            otpauth:// link
          </a>
        </div>
      )}
      {(setup || user.totp_enabled) && (
        <div className="row" style={{ marginTop: 12 }}>
          <input value={otp} onChange={(e) => setOtp(e.target.value)} inputMode="numeric" maxLength={8} placeholder="123456" style={{ maxWidth: 160 }} aria-label={t("auth.otp")} />
          {user.totp_enabled ? (
            <button className="btn btn-danger" onClick={() => confirm("/auth/2fa/disable/")}>
              {t("profile.disable")}
            </button>
          ) : (
            <button className="btn" onClick={() => confirm("/auth/2fa/enable/")}>
              {t("profile.enable")}
            </button>
          )}
        </div>
      )}
      {!setup && !user.totp_enabled && (
        <button className="btn btn-secondary" onClick={begin}>
          {t("profile.setup2fa")}
        </button>
      )}
      <ErrorMessage error={error} />
    </div>
  );
}

function ChangePassword() {
  const { t } = useI18n();
  const [form, setForm] = useState({ current_password: "", new_password: "" });
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setError(null);
    setDone(false);
    try {
      await api("/auth/password/", { method: "POST", body: form });
      setDone(true);
      setForm({ current_password: "", new_password: "" });
    } catch (err) {
      setError(err);
    }
  }
  return (
    <form className="card form" onSubmit={submit}>
      <h2>{t("profile.changePassword")}</h2>
      <label>
        {t("profile.currentPassword")}
        <input type="password" autoComplete="current-password" value={form.current_password} onChange={(e) => setForm({ ...form, current_password: e.target.value })} required />
      </label>
      <label>
        {t("profile.newPassword")}
        <input type="password" autoComplete="new-password" minLength={8} value={form.new_password} onChange={(e) => setForm({ ...form, new_password: e.target.value })} required />
      </label>
      <ErrorMessage error={error} />
      {done && <div className="alert alert-success">{t("common.saved")}</div>}
      <button className="btn btn-secondary">{t("common.save")}</button>
    </form>
  );
}

export default function Profile() {
  const { user, setUser, logout } = useAuth();
  const { t, lang, setLang } = useI18n();
  const [form, setForm] = useState(() => ({
    first_name: user.first_name,
    last_name: user.last_name,
    grade: user.grade,
    school: user.school,
    preferred_language: user.preferred_language,
  }));
  const [theme, setThemeState] = useState(getTheme);
  const [error, setError] = useState(null);
  const [toast, showToast] = useToast();
  const badges = useApi("/badges/");

  useEffect(() => setForm((f) => ({ ...f, preferred_language: lang })), [lang]);

  async function save(e) {
    e.preventDefault();
    setError(null);
    try {
      const updated = await api("/auth/me/", { method: "PATCH", body: form });
      setUser(updated);
      setLang(updated.preferred_language);
      showToast(t("common.saved"));
    } catch (err) {
      setError(err);
    }
  }

  return (
    <>
      {toast}
      <div className="page-header spread">
        <div>
          <h1 style={{ margin: 0 }}>{user.display_name}</h1>
          <p>
            @{user.username} · {t(`auth.${user.role === "admin" ? "teacher" : user.role}`)} {user.grade && `· ${user.grade}`} · {user.xp} XP
          </p>
        </div>
        <button className="btn btn-secondary" onClick={logout}>
          {t("nav.logout")}
        </button>
      </div>
      <div className="grid-2">
        <form className="card form" onSubmit={save}>
          <h2>{t("profile.title")}</h2>
          <div className="form-row">
            <label>
              {t("auth.firstName")}
              <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
            </label>
            <label>
              {t("auth.lastName")}
              <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            </label>
          </div>
          <div className="form-row">
            {user.role === "student" && (
              <label>
                {t("auth.grade")}
                <select value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value })}>
                  {GRADES.map((g) => (
                    <option key={g}>{g}</option>
                  ))}
                </select>
              </label>
            )}
            <label>
              {t("auth.school")}
              <input value={form.school} onChange={(e) => setForm({ ...form, school: e.target.value })} />
            </label>
          </div>
          <label>
            {t("profile.language")}
            <select value={form.preferred_language} onChange={(e) => setForm({ ...form, preferred_language: e.target.value })}>
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </label>
          <ErrorMessage error={error} />
          <button className="btn">{t("common.save")}</button>
        </form>

        <div className="stack">
          <div className="card">
            <h2>{t("profile.theme")}</h2>
            <div className="chips">
              {[
                ["system", `🌓 ${t("profile.system")}`],
                ["light", `☀️ ${t("profile.light")}`],
                ["dark", `🌙 ${t("profile.dark")}`],
              ].map(([value, label]) => (
                <button
                  key={value}
                  className={`chip ${theme === value ? "active" : ""}`}
                  aria-pressed={theme === value}
                  onClick={() => {
                    setTheme(value);
                    setThemeState(value);
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="card">
            <h2>🏅 {t("profile.badges")}</h2>
            <Loader state={badges}>
              {(list) => (
                <div className="badge-grid">
                  {list.map((b) => (
                    <div key={b.code} className={`badge-tile ${b.earned ? "" : "locked"}`} title={b.description}>
                      <div className="big" aria-hidden>
                        {b.icon}
                      </div>
                      <strong className="small">{b.name}</strong>
                      <div className="small muted">{b.description}</div>
                    </div>
                  ))}
                </div>
              )}
            </Loader>
          </div>
        </div>
      </div>
      <h2 className="section">{t("profile.security")}</h2>
      <div className="grid-2">
        <ChangePassword />
        <TwoFactor />
      </div>
    </>
  );
}
