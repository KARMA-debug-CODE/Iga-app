import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import { A_LEVEL, COMBINATIONS } from "../combinations";
import { DeleteAccount, DownloadData, PrivacySummary } from "../components/AccountPrivacy";
import Avatar from "../components/Avatar";
import AvatarBuilder from "../components/AvatarBuilder";
import { BadgeIcon, Icon } from "../components/Icon";
import SchoolPicker from "../components/SchoolPicker";
import { ErrorMessage, GRADES, Loader, Tabs, useToast } from "../components/ui";
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
    <div className="card profile-card" id="school">
      <h2>
        <Icon name="school" /> {t("school.mySchool")}
      </h2>
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
              {user.access?.premium
                ? t("school.fullAccess")
                : t(`access.reason.${user.access?.reason}`, {
                    school: user.school.name,
                  })}
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
            <button
              className="btn btn-sm btn-ghost"
              disabled={busy}
              onClick={() => window.confirm(t("school.leaveConfirm")) && send("DELETE")}
            >
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
      <h2>
        <Icon name="shield" /> {t("profile.twoFactor")}
      </h2>
      <p className="muted">{user.totp_enabled ? t("profile.twoFactorOn") : t("profile.twoFactorOff")}</p>
      {setup && (
        <div className="stack">
          <p>{t("profile.enter2fa")}</p>
          <code className="code-display" style={{ fontSize: "1rem", wordBreak: "break-all" }}>
            {setup.secret}
          </code>
          <a href={setup.otpauth_uri} className="small">
            {t("profile.otpauthLink")}
          </a>
        </div>
      )}
      {(setup || user.totp_enabled) && (
        <div className="row" style={{ marginTop: 12 }}>
          <input
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            inputMode="numeric"
            maxLength={8}
            placeholder="123456"
            style={{ maxWidth: 160 }}
            aria-label={t("auth.otp")}
          />
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
      <h2>
        <Icon name="users" /> {t("parent.access")}
      </h2>
      <p className="muted small">{t("parent.accessHelp")}</p>
      {invite ? (
        <div className="stack">
          <span className="code-display">{invite.code}</span>
          <span className="small muted">
            {t("parent.expires", {
              date: new Date(invite.expires_at).toLocaleDateString(lang),
            })}
          </span>
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
      <h2>
        <Icon name="key" /> {t("profile.changePassword")}
      </h2>
      <label>
        {t("profile.currentPassword")}
        <input
          type="password"
          autoComplete="current-password"
          value={form.current_password}
          onChange={(e) => setForm({ ...form, current_password: e.target.value })}
          required
        />
      </label>
      <label>
        {t("profile.newPassword")}
        <input
          type="password"
          autoComplete="new-password"
          minLength={8}
          value={form.new_password}
          onChange={(e) => setForm({ ...form, new_password: e.target.value })}
          required
        />
      </label>
      <ErrorMessage error={error} />
      {done && <div className="alert alert-success">{t("common.saved")}</div>}
      <button className="btn btn-secondary">{t("common.save")}</button>
    </form>
  );
}

// The address password reset links go to. Changing it asks for the password.
function EmailAddress() {
  const { user, setUser } = useAuth();
  const { t } = useI18n();
  const [form, setForm] = useState({ email: user.email || "", current_password: "" });
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  const changed = form.email.trim().toLowerCase() !== (user.email || "").toLowerCase();

  async function submit(e) {
    e.preventDefault();
    setError(null);
    setDone(false);
    try {
      const updated = await api("/auth/me/", {
        method: "PATCH",
        body: { email: form.email.trim(), current_password: form.current_password },
      });
      setUser(updated);
      setForm({ email: updated.email || "", current_password: "" });
      setDone(true);
    } catch (err) {
      setError(err);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h2>
        <Icon name="mail" /> {t("profile.email")}
      </h2>
      <p className="muted small">{user.email ? t("profile.emailHelp") : t("profile.emailMissing")}</p>
      <label>
        {t("profile.emailLabel")}
        <input
          type="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          autoComplete="email"
          maxLength={254}
          required={user.role === "school_admin"}
        />
      </label>
      {changed && (
        <label>
          {t("profile.currentPassword")}
          <input
            type="password"
            autoComplete="current-password"
            value={form.current_password}
            onChange={(e) => setForm({ ...form, current_password: e.target.value })}
            required
          />
        </label>
      )}
      <ErrorMessage error={error} />
      {done && <div className="alert alert-success">{t("common.saved")}</div>}
      <button className="btn btn-secondary" disabled={!changed}>
        {t("common.save")}
      </button>
    </form>
  );
}

function Sessions() {
  const { logoutEverywhere } = useAuth();
  const { t } = useI18n();
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    if (!window.confirm(t("profile.logoutEverywhereConfirm"))) return;
    setBusy(true);
    setError(null);
    try {
      await logoutEverywhere();
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>
        <Icon name="logout" /> {t("profile.sessions")}
      </h2>
      <p className="muted small">{t("profile.sessionsHelp")}</p>
      <ErrorMessage error={error} />
      <button className="btn btn-secondary" onClick={run} disabled={busy}>
        {t("profile.logoutEverywhere")}
      </button>
    </div>
  );
}

const TABS = ["details", "avatar", "badges", "school", "security", "privacy", "appearance"];

function ProfileHeader({ onEditAvatar }) {
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const role = t(`auth.${user.role === "admin" ? "teacher" : user.role}`);
  return (
    <section className="card profile-hero">
      <button type="button" className="profile-hero-avatar" onClick={onEditAvatar} aria-label={t("avatar.edit")}>
        <Avatar user={user} size={104} />
        <span className="profile-hero-edit" aria-hidden>
          <Icon name="edit" size={14} />
        </span>
      </button>
      <div className="profile-hero-text">
        <h1>{user.display_name}</h1>
        <p className="muted">@{user.username}</p>
        <div className="profile-hero-tags">
          <span className="pill pill-blue">{role}</span>
          {user.role === "student" && user.grade && <span className="pill">{user.grade}</span>}
          {user.combination_subjects?.length > 0 && <span className="pill">{user.combination}</span>}
          {user.school && <span className="pill">{user.school.name}</span>}
        </div>
      </div>
      <div className="profile-hero-side">
        {user.role === "student" && (
          <dl className="profile-hero-stats">
            <div>
              <dt>{t("profile.xp")}</dt>
              <dd>{user.xp}</dd>
            </div>
            <div>
              <dt>{t("profile.streak")}</dt>
              <dd>
                <Icon name="flame" size={16} /> {user.streak_days}
              </dd>
            </div>
            <div>
              <dt>{t("profile.badges")}</dt>
              <dd>{user.badges?.length ?? 0}</dd>
            </div>
          </dl>
        )}
        <button className="btn btn-secondary btn-sm profile-hero-logout" onClick={logout}>
          <Icon name="logout" /> {t("nav.logout")}
        </button>
      </div>
    </section>
  );
}

function Details() {
  const { user, setUser } = useAuth();
  const { t, lang, setLang } = useI18n();
  const [form, setForm] = useState(() => ({
    first_name: user.first_name,
    last_name: user.last_name,
    grade: user.grade,
    combination: user.combination || "",
    preferred_language: user.preferred_language,
  }));
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const gradeChanges = user.role === "student" && form.grade !== user.grade;
  const aLevel = user.role === "student" && A_LEVEL.includes(form.grade);

  useEffect(() => setForm((f) => ({ ...f, preferred_language: lang })), [lang]);

  async function save(e) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    try {
      const updated = await api("/auth/me/", { method: "PATCH", body: form });
      setUser(updated);
      setForm((f) => ({ ...f, combination: updated.combination }));
      setLang(updated.preferred_language);
      if (updated.left_classes !== undefined) {
        setNotice(
          [
            t("profile.gradeMoved", { grade: updated.grade }),
            updated.left_classes.length
              ? t("profile.gradeLeftClasses", {
                  classes: updated.left_classes.join(", "),
                })
              : "",
          ]
            .filter(Boolean)
            .join(" "),
        );
      } else {
        setNotice(t("common.saved"));
      }
    } catch (err) {
      setError(err);
    }
  }

  return (
    <form className="card form profile-card" onSubmit={save}>
      <h2>
        <Icon name="user" /> {t("profile.title")}
      </h2>
      <div className="form-row">
        <label>
          {t("auth.firstName")}
          <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} autoComplete="given-name" />
        </label>
        <label>
          {t("auth.lastName")}
          <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} autoComplete="family-name" />
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
          {t("profile.language")}
          <select value={form.preferred_language} onChange={(e) => setForm({ ...form, preferred_language: e.target.value })}>
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {aLevel && (
        <label>
          <span id="combination-label">{t("profile.combination")}</span>
          <select
            value={form.combination}
            onChange={(e) => setForm({ ...form, combination: e.target.value })}
            aria-labelledby="combination-label"
            aria-describedby="combination-help"
          >
            <option value="">{t("profile.combinationNone")}</option>
            {COMBINATIONS.map((code) => (
              <option key={code} value={code}>
                {t(`combination.${code}`)}
              </option>
            ))}
          </select>
          <span id="combination-help" className="small muted" style={{ fontWeight: 400 }}>
            {t("profile.combinationHelp")}
          </span>
        </label>
      )}
      {gradeChanges && (
        <p className="alert alert-info small" role="note">
          <Icon name="info" /> {t("profile.gradeChangeHelp", { grade: form.grade })}
        </p>
      )}
      <ErrorMessage error={error} />
      {notice && (
        <div className="alert alert-success" role="status">
          {notice}
        </div>
      )}
      <div>
        <button className="btn">
          <Icon name="save" /> {t("common.save")}
        </button>
      </div>
    </form>
  );
}

function Appearance() {
  const { t } = useI18n();
  const [theme, setThemeState] = useState(getTheme);
  const options = [
    ["system", "monitor", t("profile.system")],
    ["light", "sun", t("profile.light")],
    ["dark", "moon", t("profile.dark")],
  ];
  return (
    <div className="card profile-card">
      <h2>
        <Icon name="palette" /> {t("profile.theme")}
      </h2>
      <div className="theme-choices" role="radiogroup" aria-label={t("profile.theme")}>
        {options.map(([value, icon, label]) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={theme === value}
            className={`theme-choice ${theme === value ? "selected" : ""}`}
            onClick={() => {
              setTheme(value);
              setThemeState(value);
            }}
          >
            <Icon name={icon} size={22} />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

function Badges() {
  const { t } = useI18n();
  const badges = useApi("/badges/");
  return (
    <div className="card profile-card">
      <h2>
        <Icon name="award" /> {t("profile.badges")}
      </h2>
      <Loader state={badges}>
        {(list) => (
          <div className="badge-grid">
            {list.map((b) => (
              <div key={b.code} className={`badge-tile ${b.earned ? "earned" : "locked"}`} title={t(`badge.${b.code}.desc`)}>
                <div className="badge-icon">
                  <BadgeIcon name={b.icon} />
                </div>
                <strong className="small">{t(`badge.${b.code}.name`)}</strong>
                <div className="small muted">{t(`badge.${b.code}.desc`)}</div>
              </div>
            ))}
          </div>
        )}
      </Loader>
    </div>
  );
}

export default function Profile() {
  const { user } = useAuth();
  const { t } = useI18n();
  const location = useLocation();
  const navigate = useNavigate();
  const [toast, showToast] = useToast();
  const hasSchool = user.role !== "parent" && user.role !== "admin";
  const tabs = TABS.filter((tab) => (tab === "school" ? hasSchool : tab === "badges" ? user.role === "student" : true));
  const fromHash = location.hash.slice(1);
  const [tab, setTab] = useState(tabs.includes(fromHash) ? fromHash : "details");

  // Links such as /profile#school open that tab.
  useEffect(() => {
    if (tabs.includes(fromHash)) setTab(fromHash);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fromHash]);

  function choose(next) {
    setTab(next);
    navigate({ hash: next === "details" ? "" : next }, { replace: true });
  }

  return (
    <div className="profile-page">
      {toast}
      <ProfileHeader onEditAvatar={() => choose("avatar")} />
      <Tabs
        value={tab}
        onChange={choose}
        tabs={tabs.map((value) => ({
          value,
          label: t(`profile.tab.${value}`),
        }))}
      />
      <div className="profile-panel">
        {tab === "details" && <Details />}
        {tab === "avatar" && (
          <div className="card profile-card">
            <h2>
              <Icon name="palette" /> {t("avatar.title")}
            </h2>
            <p className="muted small">{t("avatar.help")}</p>
            <AvatarBuilder onSaved={() => showToast(t("common.saved"))} />
          </div>
        )}
        {tab === "badges" && <Badges />}
        {tab === "school" && <MySchool />}
        {tab === "security" && (
          <div className="grid-2">
            <ChangePassword />
            <EmailAddress />
            <TwoFactor />
            <Sessions />
            {user.role === "student" && <ParentAccess />}
          </div>
        )}
        {tab === "privacy" && (
          <div className="grid-2">
            <PrivacySummary />
            <DownloadData />
            <DeleteAccount />
          </div>
        )}
        {tab === "appearance" && <Appearance />}
      </div>
    </div>
  );
}
