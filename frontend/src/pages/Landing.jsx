import { Link } from "react-router-dom";

import { Icon } from "../components/Icon";
import { Logo } from "../components/ui";
import { LANGUAGES, useI18n } from "../i18n";

const FEATURES = [
  ["learn", "landing.f.lessons"],
  ["labs", "landing.f.labs"],
  ["practice", "landing.f.exams"],
  ["groups", "landing.f.groups"],
  ["teach", "landing.f.teachers"],
  ["code", "landing.f.code"],
];

export function LanguagePicker() {
  const { lang, setLang, t } = useI18n();
  return (
    <div className="chips" role="group" aria-label={t("profile.language")}>
      {LANGUAGES.map((l) => (
        <button key={l.code} className={`chip ${lang === l.code ? "active" : ""}`} aria-pressed={lang === l.code} onClick={() => setLang(l.code)}>
          {l.name}
        </button>
      ))}
    </div>
  );
}

export default function Landing() {
  const { t } = useI18n();
  const showDemo = import.meta.env.DEV || import.meta.env.VITE_SHOW_DEMO_ACCOUNTS === "true";
  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "16px var(--gutter) 48px" }}>
      <header className="spread" style={{ marginBottom: 16 }}>
        <div className="brand">
          <Logo />
          <span>Iga</span>
        </div>
        <div className="row">
          <Link className="btn btn-ghost" to="/login">
            {t("auth.login")}
          </Link>
          <Link className="btn" to="/register">
            {t("auth.joinNow")}
          </Link>
        </div>
      </header>

      <section className="hero">
        <div className="sun" aria-hidden />
        <div style={{ position: "relative" }}>
          <h1>{t("landing.title")}</h1>
          <p>{t("landing.subtitle")}</p>
          <div className="row" style={{ marginTop: 18 }}>
            <Link className="btn" style={{ background: "var(--yellow)", color: "#1b1b1b" }} to="/register">
              {t("auth.joinNow")} →
            </Link>
            <Link className="btn btn-secondary" to="/login">
              {t("auth.login")}
            </Link>
          </div>
        </div>
      </section>

      <div style={{ margin: "18px 0" }}>
        <LanguagePicker />
      </div>

      <section className="grid" aria-label={t("a11y.features")}>
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

      {showDemo && (
        <p className="alert line-with-icon" style={{ marginTop: 20 }}>
          <Icon name="key" /> <span>{t("landing.demo")}</span>
        </p>
      )}

      <footer className="muted small" style={{ marginTop: 32, textAlign: "center" }}>
        Iga · {t("app.tagline")} · {t("landing.credits")}
      </footer>
    </div>
  );
}
