// Shown instead of the app while the account hasn't accepted the current Terms of Use and Privacy Policy: a
// roster account at its first sign-in, or anyone after the texts changed (backend/apps/accounts/legal.py).
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import { DeleteAccount } from "../components/AccountPrivacy";
import ConsentCheckbox from "../components/ConsentCheckbox";
import { ErrorMessage } from "../components/ui";
import { useI18n } from "../i18n";
import { loadSiteInfo } from "../site";
import AuthShell from "./AuthShell";

export default function ConsentGate() {
  const { user, setUser, logout } = useAuth();
  const { t } = useI18n();
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const first = !user.terms_version;

  async function accept(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const site = await loadSiteInfo();
      setUser(await api("/auth/accept-terms/", { method: "POST", body: { version: site.legal.version } }));
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <AuthShell title={t(first ? "consent.firstTitle" : "consent.updatedTitle")}>
      <p className="muted">{t(first ? "consent.firstIntro" : "consent.updatedIntro")}</p>
      <form className="form" onSubmit={accept}>
        <ConsentCheckbox checked={checked} onChange={setChecked} student={user.role === "student"} />
        <ErrorMessage error={error} />
        <button className="btn btn-block" disabled={!checked || busy}>
          {t("consent.continue")}
        </button>
        <button type="button" className="btn btn-ghost" onClick={logout}>
          {t("nav.logout")}
        </button>
      </form>
      <details className="consent-disagree">
        <summary>{t("consent.disagree")}</summary>
        <p className="small muted">
          {t("consent.disagreeHelp")} <Link to="/contact">{t("site.contact")}</Link>
        </p>
        <DeleteAccount />
      </details>
    </AuthShell>
  );
}
