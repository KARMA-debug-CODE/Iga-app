import { useEffect } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth";
import Faq from "../components/Faq";
import { Icon } from "../components/Icon";
import Pricing from "../components/Pricing";
import PublicShell from "../components/PublicShell";
import { useI18n } from "../i18n";
import { usePageMeta } from "../pageMeta";

const FEATURES = [
  ["learn", "landing.f.lessons"],
  ["labs", "landing.f.labs"],
  ["practice", "landing.f.exams"],
  ["groups", "landing.f.groups"],
  ["teach", "landing.f.teachers"],
  ["code", "landing.f.code"],
];

/** The home page for visitors. /pricing and /faq open it at that section (for signed-in users too). */
export default function Landing({ section }) {
  const { user } = useAuth();
  const { t } = useI18n();
  usePageMeta("home");
  const showDemo = import.meta.env.DEV || import.meta.env.VITE_SHOW_DEMO_ACCOUNTS === "true";

  useEffect(() => {
    if (section) document.getElementById(section)?.scrollIntoView({ block: "start" });
  }, [section]);

  return (
    <PublicShell wide>
      <section className="hero">
        <div className="sun" aria-hidden />
        <div style={{ position: "relative" }}>
          <h1>{t("landing.title")}</h1>
          <p>{t("landing.subtitle")}</p>
          <div className="row" style={{ marginTop: 18 }}>
            {user ? (
              <Link className="btn" style={{ background: "var(--yellow)", color: "#1b1b1b" }} to="/">
                {t("site.openApp")} →
              </Link>
            ) : (
              <>
                <Link className="btn" style={{ background: "var(--yellow)", color: "#1b1b1b" }} to="/register">
                  {t("auth.joinNow")} →
                </Link>
                <Link className="btn btn-secondary" to="/login">
                  {t("auth.login")}
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      <section className="grid section" aria-label={t("a11y.features")}>
        {FEATURES.map(([icon, key]) => (
          <div className="card" key={key}>
            <div className="icon-tile">
              <Icon name={icon} size={22} />
            </div>
            <h3 style={{ marginTop: 12 }}>{t(key)}</h3>
            <p className="muted" style={{ margin: 0 }}>
              {t(`${key}.d`)}
            </p>
          </div>
        ))}
      </section>

      <Pricing />
      <Faq />

      {showDemo && (
        <p className="alert line-with-icon" style={{ marginTop: 20 }}>
          <Icon name="key" /> <span>{t("landing.demo")}</span>
        </p>
      )}
    </PublicShell>
  );
}
