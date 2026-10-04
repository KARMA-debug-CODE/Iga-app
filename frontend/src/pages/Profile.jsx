import { useEffect, useState } from "react";

import { api } from "../api";
import { useAuth } from "../auth";
import SchoolPicker from "../components/SchoolPicker";
import { ErrorMessage, GRADES, Loader, useToast } from "../components/ui";
import { useApi } from "../hooks";
import { LANGUAGES, useI18n } from "../i18n";
import { getTheme, setTheme } from "../theme";

function MySchool() {
  const { user, reloadUser } = useAuth();
  const { t } = useI18n();
  const [choosing, setChoosing] = useState(false);
  const [school, setSchool] = useState(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const locked = user.role === "school_admin" && user.school_status === "approved";

  async function send(method, body) {
    setBusy(true);
    setError(null);
    try {
      await api("/my-school/", { method, body });
      await reloadUser();
      setChoosing(false);
      setSchool(null);
      setCode("");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const status = user.school_status;
  return (
    <div className="card" id="school">
      <h2>🏫 {t("school.mySchool")}</h2>
      {user.school ? (
        <div className="stack" style={{ gap: 8 }}>
          <div>
            <strong>{user.school.name}</strong> <span className="small muted">· {user.school.district}</span>
          </div>
          <span className={`pill ${status === "approved" ? "pill-success" : status === "pending" ? "pill-warn" : "pill-danger"}`}>
            {t(`school.status.${status || "none"}`)}
          </span>
          {status === "approved" && user.school.subscription && (
            <span className="small muted">
              {user.access?.premium ? t("school.fullAccess") : t(`access.reason.${user.access?.reason}`, { school: user.school.name })}
            </span>
          )}
          {status === "pending" && <span className="small muted">{t("school.pendingHelp")}</span>}
        </div>
      ) : (
        <p className="small muted">{t("school.noneHelp")}</p>
      )}
      {!locked && !choosing && (
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn btn-sm btn-secondary" onClick={() => setChoosing(true)}>
            {user.school ? t("school.changeSchool") : t("access.chooseSchool")}
          </button>
          {user.school && (
            <button className="btn btn-sm btn-ghost" disabled={busy} onClick={() => window.confirm(t("school.leaveConfirm")) && send("DELETE")}>
              {t("school.leave")}
            </button>
          )}
        </div>
      )}
      {choosing && (
        <form
          className="form"
          style={{ marginTop: 12 }}
          onSubmit={(e) => {
            e.preventDefault();
            if (school) send("POST", { school: school.id, school_code: code.trim() });
          }}
        >
          <SchoolPicker value={school} onChange={setSchool} />
          {school && user.role !== "school_admin" && (
            <label>
              {t("school.code")}
              <input
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                maxLength={12}
                style={{ fontFamily: "var(--mono)", letterSpacing: "0.12em" }}
              />
              <span className="small muted" style={{ fontWeight: 400 }}>
                {t("school.codeHint")}
              </span>
            </label>
          )}
          <ErrorMessage error={error} />
          <div className="row">
            <button className="btn btn-sm" disabled={!school || busy}>
              {t("common.save")}
            </button>
            <button type="button" className="btn btn-sm btn-ghost" onClick={() => setChoosing(false)}>
              {t("common.cancel")}
            </button>
          </div>
        </form>
      )}
      {!choosing && <ErrorMessage error={error} />}
    </div>
  );
}

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

function ParentAccess() {
  const { t, lang } = useI18n();
  const parents = useApi("/auth/parents/");
  const [invite, setInvite] = useState(null);
  const [error, setError] = useState(null);
  async function makeCode() {
    setError(null);
    try {
      setInvite(await api("/auth/parent-code/", { method: "POST" }));
    } catch (e) {
      setError(e);
    }
  }
  async function remove(id) {
    await api(`/auth/parents/${id}/`, { method: "DELETE" });
    parents.reload();
  }
  return (
    <div className="card">
      <h2>👨‍👩‍👧 {t("parent.access")}</h2>
      <p className="muted small">{t("parent.accessHelp")}</p>
      {invite ? (
        <div className="stack">
          <span className="code-display">{invite.code}</span>
          <span className="small muted">{t("parent.expires", { date: new Date(invite.expires_at).toLocaleDateString(lang) })}</span>
        </div>
      ) : (
        <button className="btn btn-secondary" onClick={makeCode}>
          {t("parent.makeCode")}
        </button>
      )}
      <ErrorMessage error={error} />
      {(parents.data || []).length > 0 && (
        <ul className="list" style={{ marginTop: 12 }}>
          {parents.data.map((p) => (
            <li key={p.id} className="spread">
              <span>{p.name}</span>
              <button className="btn btn-sm btn-danger" onClick={() => remove(p.id)}>
                {t("classes.remove")}
              </button>
            </li>
          ))}
        </ul>
      )}
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
          {user.role !== "parent" && user.role !== "admin" && <MySchool />}
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
        {user.role === "student" && <ParentAccess />}
      </div>
    </>
  );
}
