import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import SchoolPicker, { DistrictSelect } from "../components/SchoolPicker";
import { GRADES } from "../components/ui";
import { useI18n } from "../i18n";
import AuthShell from "./AuthShell";

const ROLES = { student: "🎒 ", teacher: "🧑🏽‍🏫 ", parent: "👨‍👩‍👧 ", school_admin: "🏫 " };

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
  const [school, setSchool] = useState(null);
  const [schoolCode, setSchoolCode] = useState("");
  const [newSchool, setNewSchool] = useState(null); // school administrators registering a school
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const updateSchool = (key) => (e) => setNewSchool((s) => ({ ...s, [key]: e.target.value }));
  const joinsSchool = form.role !== "parent";
  const isSchoolAdmin = form.role === "school_admin";

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = { ...form, preferred_language: lang };
      if (payload.role !== "student") payload.grade = "";
      if (!payload.email) delete payload.email;
      if (isSchoolAdmin && newSchool) {
        payload.new_school = { ...newSchool };
        if (!payload.new_school.email) delete payload.new_school.email;
      } else if (joinsSchool && school) {
        payload.school = school.id;
        if (schoolCode.trim() && !isSchoolAdmin) payload.school_code = schoolCode.trim();
      }
      await register(payload);
      navigate(isSchoolAdmin ? "/school" : "/", { replace: true });
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
            {Object.keys(ROLES).map((role) => (
              <button
                type="button"
                key={role}
                className={`chip ${form.role === role ? "active" : ""}`}
                aria-pressed={form.role === role}
                onClick={() => setForm((f) => ({ ...f, role }))}
              >
                {ROLES[role]}
                {t(`auth.${role === "school_admin" ? "schoolAdmin" : role}`)}
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
          <input value={form.username} onChange={update("username")} autoComplete="username" required pattern="[\w.+-]+" />
        </label>
        <label>
          {isSchoolAdmin ? t("auth.emailRequired") : t("auth.email")}
          <input type="email" value={form.email} onChange={update("email")} autoComplete="email" required={isSchoolAdmin} />
        </label>
        <label>
          {t("auth.password")}
          <input type="password" value={form.password} onChange={update("password")} autoComplete="new-password" minLength={8} required />
          <span className="small muted" style={{ fontWeight: 400 }}>
            {t("auth.passwordHint")}
          </span>
        </label>
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

        {joinsSchool && (
          <fieldset className="fieldset">
            <legend>{t("auth.school")}</legend>
            {isSchoolAdmin && (
              <div className="chips" style={{ marginBottom: 10 }}>
                <button type="button" className={`chip ${!newSchool ? "active" : ""}`} aria-pressed={!newSchool} onClick={() => setNewSchool(null)}>
                  {t("school.existing")}
                </button>
                <button
                  type="button"
                  className={`chip ${newSchool ? "active" : ""}`}
                  aria-pressed={Boolean(newSchool)}
                  onClick={() => setNewSchool({ name: "", district: "", sector: "", phone: "", email: "" })}
                >
                  {t("school.registerNew")}
                </button>
              </div>
            )}
            {isSchoolAdmin && newSchool ? (
              <div className="stack" style={{ gap: 10 }}>
                <label>
                  {t("school.name")}
                  <input value={newSchool.name} onChange={updateSchool("name")} required />
                </label>
                <div className="form-row">
                  <label>
                    {t("school.district")}
                    <DistrictSelect value={newSchool.district} onChange={(district) => setNewSchool((s) => ({ ...s, district }))} required />
                  </label>
                  <label>
                    {t("school.sector")}
                    <input value={newSchool.sector} onChange={updateSchool("sector")} />
                  </label>
                </div>
                <div className="form-row">
                  <label>
                    {t("school.phone")}
                    <input type="tel" value={newSchool.phone} onChange={updateSchool("phone")} required />
                  </label>
                  <label>
                    {t("school.email")}
                    <input type="email" value={newSchool.email} onChange={updateSchool("email")} />
                  </label>
                </div>
                <p className="small muted" style={{ margin: 0 }}>
                  {t("school.verifyNote")}
                </p>
              </div>
            ) : (
              <>
                <SchoolPicker value={school} onChange={setSchool} />
                {school && !isSchoolAdmin && (
                  <label style={{ marginTop: 10 }}>
                    {t("school.code")}
                    <input
                      value={schoolCode}
                      onChange={(e) => setSchoolCode(e.target.value.toUpperCase())}
                      maxLength={12}
                      placeholder="ABCD2345"
                      style={{ fontFamily: "var(--mono)", letterSpacing: "0.12em" }}
                    />
                    <span className="small muted" style={{ fontWeight: 400 }}>
                      {t("school.codeHint")}
                    </span>
                  </label>
                )}
                {school && isSchoolAdmin && <p className="small muted">{t("school.adminApprovalNote")}</p>}
                {!school && <p className="small muted" style={{ margin: "8px 0 0" }}>{t(isSchoolAdmin ? "school.adminPickHint" : "school.skipHint")}</p>}
              </>
            )}
          </fieldset>
        )}

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}
        <button className="btn btn-block" disabled={busy || (isSchoolAdmin && !newSchool && !school)}>
          {t("auth.register")}
        </button>
        <p className="muted small" style={{ margin: 0, textAlign: "center" }}>
          {t("auth.haveAccount")} <Link to="/login">{t("auth.login")}</Link>
        </p>
      </form>
    </AuthShell>
  );
}
