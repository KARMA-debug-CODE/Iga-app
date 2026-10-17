// The contact form: a message for the Iga team (kept for platform admins in Admin -> Messages and emailed to
// the team). Anyone may write; the server checks, cleans and rate-limits it.
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import { Icon } from "../components/Icon";
import PublicShell from "../components/PublicShell";
import { ErrorMessage } from "../components/ui";
import { useI18n } from "../i18n";
import { usePageMeta } from "../pageMeta";
import { useSiteInfo } from "../site";

function emptyForm(user) {
  return {
    name: user ? user.display_name : "",
    email: user?.email || "",
    school: user?.school?.name || "",
    message: "",
    website: "", // never shown: only robots fill it in
  };
}

export default function Contact() {
  const { user } = useAuth();
  const { t } = useI18n();
  usePageMeta("contact");
  const site = useSiteInfo();
  const [form, setForm] = useState(() => emptyForm(user));
  const [sent, setSent] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const field = (name) => ({ value: form[name], onChange: (e) => setForm({ ...form, [name]: e.target.value }) });

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await api("/contact/", { method: "POST", body: form });
      setSent(data.detail);
      setForm(emptyForm(user));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const privacyEmail = site.data?.legal?.privacy_email;
  return (
    <PublicShell>
      <div className="contact-page">
        <h1 className="title-with-icon">
          <Icon name="mail" size={28} /> {t("contact.title")}
        </h1>
        <p className="muted">{t("contact.intro")}</p>
        <p className="small">
          {t("contact.faqFirst")} <Link to="/faq">{t("faq.title")}</Link>
        </p>
        {sent ? (
          <div className="card stack">
            <div className="alert alert-success" role="status">
              {sent}
            </div>
            <div>
              <button className="btn btn-secondary" onClick={() => setSent(null)}>
                {t("contact.another")}
              </button>
            </div>
          </div>
        ) : (
          <form className="card form" onSubmit={submit}>
            <div className="form-row">
              <label>
                {t("contact.name")}
                <input {...field("name")} autoComplete="name" maxLength={120} required />
              </label>
              <label>
                {t("contact.email")}
                <input type="email" {...field("email")} autoComplete="email" maxLength={254} required />
              </label>
            </div>
            <label>
              {t("contact.school")}
              <input {...field("school")} autoComplete="organization" maxLength={200} />
            </label>
            <label>
              {t("contact.message")}
              <textarea {...field("message")} rows={6} minLength={10} maxLength={5000} required aria-describedby="contact-message-hint" />
              <span id="contact-message-hint" className="small muted" style={{ fontWeight: 400 }}>
                {t("contact.messageHint")}
              </span>
            </label>
            <label className="trap" aria-hidden="true">
              {t("contact.trap")}
              <input {...field("website")} tabIndex={-1} autoComplete="off" />
            </label>
            <ErrorMessage error={error} />
            <div>
              <button className="btn" disabled={busy}>
                <Icon name="send" size={18} /> {t("contact.send")}
              </button>
            </div>
          </form>
        )}
        {privacyEmail && <p className="small muted" style={{ marginTop: 16 }}>{t("contact.privacy", { email: privacyEmail })}</p>}
      </div>
    </PublicShell>
  );
}
