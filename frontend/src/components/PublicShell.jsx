// The frame of the public pages (home, contact, Terms of Use, Privacy Policy): Iga's name, links to the
// sections of the home page, sign-in, and a footer with the legal pages. Shown to visitors and to signed-in
// users alike (they get a link back to the app instead of "Log in").
import { Link } from "react-router-dom";

import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import LanguagePicker from "./LanguagePicker";
import { Logo } from "./ui";

export function SiteFooter() {
  const { t } = useI18n();
  return (
    <footer className="site-footer">
      <nav aria-label={t("site.footerLinks")} className="site-footer-links">
        <Link to="/pricing">{t("site.pricing")}</Link>
        <Link to="/faq">{t("site.faq")}</Link>
        <Link to="/contact">{t("site.contact")}</Link>
        <Link to="/terms">{t("site.terms")}</Link>
        <Link to="/privacy">{t("site.privacy")}</Link>
      </nav>
      <p className="muted small">
        Iga · {t("app.tagline")} · {t("site.made")}
      </p>
      <p className="muted small">{t("landing.credits")}</p>
    </footer>
  );
}

export default function PublicShell({ children, wide = false }) {
  const { user } = useAuth();
  const { t } = useI18n();
  return (
    <div className={`public-page ${wide ? "public-wide" : ""}`}>
      <header className="public-header">
        <Link to="/" className="brand" aria-label={t("a11y.home")}>
          <Logo />
          <span>Iga</span>
        </Link>
        <div className="row public-actions">
          {user ? (
            <Link className="btn btn-sm" to="/">
              {t("site.openApp")}
            </Link>
          ) : (
            <>
              <Link className="btn btn-ghost btn-sm" to="/login">
                {t("auth.login")}
              </Link>
              <Link className="btn btn-sm" to="/register">
                {t("auth.joinNow")}
              </Link>
            </>
          )}
        </div>
      </header>
      <main id="main" className="public-main">
        {children}
      </main>
      <div className="public-language">
        <LanguagePicker />
      </div>
      <SiteFooter />
    </div>
  );
}
