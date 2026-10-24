// The Terms of Use and the Privacy Policy. Their text lives in src/legal/ (one file per language, loaded only
// here); what depends on the server (who runs Iga, the privacy contact, how long records are kept, the version)
// comes from /api/site/, so the pages always state the real settings.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Icon } from "../components/Icon";
import PublicShell from "../components/PublicShell";
import { Spinner } from "../components/ui";
import { formatDay } from "../hooks";
import { useI18n } from "../i18n";
import { keepPunctuationAttached } from "../noBreakSpaces";
import { usePageMeta } from "../pageMeta";
import { sitePath } from "../safeUrl";
import { useSiteInfo } from "../site";

const DOCUMENTS = {
  terms: { en: () => import("../legal/terms.en.js"), fr: () => import("../legal/terms.fr.js") },
  privacy: { en: () => import("../legal/privacy.en.js"), fr: () => import("../legal/privacy.fr.js") },
};

// Only if the server can't be reached (offline): its own defaults (backend/config/settings.py).
const FALLBACK = {
  legal: { version: "", draft: true, entity: "Iga", address: "Kigali, Rwanda", privacy_email: "privacy@iga.rw", hosting: "Rwanda" },
  retention: {},
  pricing: {},
};

const LINK = /\[([^\]]+)\]\(([^)\s]+)\)/g;

/** `text` with its {placeholders} filled in and its [label](/path) links made into links to the app's pages. */
export function renderText(text, values, lang) {
  let filled = text.replace(/\{(\w+)\}/g, (match, name) => (values[name] ?? match));
  if (lang === "fr") filled = keepPunctuationAttached(filled);
  const parts = [];
  let last = 0;
  for (const match of filled.matchAll(LINK)) {
    const path = sitePath(match[2]);
    parts.push(filled.slice(last, match.index));
    parts.push(path ? <Link key={match.index} to={path}>{match[1]}</Link> : match[1]);
    last = match.index + match[0].length;
  }
  parts.push(filled.slice(last));
  return parts;
}

function useDocument(name, lang) {
  const [state, setState] = useState({ key: null, doc: null });
  const key = `${name}.${lang}`;
  useEffect(() => {
    let alive = true;
    (DOCUMENTS[name][lang] || DOCUMENTS[name].en)().then((module) => alive && setState({ key, doc: module.default }));
    return () => {
      alive = false;
    };
  }, [name, lang, key]);
  return state.key === key ? state.doc : null;
}

function LegalPage({ name }) {
  const { t, lang } = useI18n();
  usePageMeta(name);
  const site = useSiteInfo();
  const doc = useDocument(name, lang);
  const info = site.data || (site.error ? FALLBACK : null);

  if (!doc || !info) {
    return (
      <PublicShell>
        <Spinner />
      </PublicShell>
    );
  }

  const legal = info.legal;
  const retention = info.retention || {};
  const days = (n) => (n === undefined || n === null ? "…" : n === 0 ? t("legal.untilDeleted") : t("legal.days", { n }));
  const values = {
    entity: legal.entity,
    address: legal.address,
    email: legal.privacy_email,
    hosting: legal.hosting,
    version: legal.version,
    graceDays: days(retention.deletion_grace_days),
    santaDays: days(retention.santa_days),
    auditDays: days(retention.audit_days),
    usageDays: days(retention.usage_days),
    contactDays: days(retention.contact_days),
    backupDays: days(retention.backup_days),
    tempDays: days(retention.temporary_password_days),
    sessionDays: days(retention.session_days),
    subscriptionGraceDays: days(info.pricing?.grace_days),
  };
  const text = (value) => renderText(value, values, lang);
  const version = /^\d{4}-\d{2}-\d{2}$/.test(legal.version) ? formatDay(legal.version, lang) : legal.version;
  const other = name === "terms" ? ["/privacy", "legal.seeAlsoPrivacy"] : ["/terms", "legal.seeAlsoTerms"];

  return (
    <PublicShell>
      <article className="legal">
        {legal.draft && (
          <div className="alert alert-warn legal-draft" role="note">
            <Icon name="warning" />
            <div>
              <strong>{t("legal.draft")}</strong>
              <div className="small">{t("legal.draftOwner")}</div>
            </div>
          </div>
        )}
        <header>
          <h1>{doc.title}</h1>
          {version && <p className="muted small">{t("legal.version", { date: version })}</p>}
        </header>
        {doc.intro.map((paragraph, i) => (
          <p key={i} className="legal-intro">
            {text(paragraph)}
          </p>
        ))}
        <nav className="card legal-contents" aria-labelledby="legal-contents">
          <h2 id="legal-contents">{t("legal.contents")}</h2>
          <ol>
            {doc.sections.map((section) => (
              <li key={section.id}>
                <a href={`#${section.id}`}>{section.title}</a>
              </li>
            ))}
          </ol>
        </nav>
        {doc.sections.map((section, number) => (
          <section key={section.id} id={section.id} className="legal-section" aria-labelledby={`${section.id}-title`}>
            <h2 id={`${section.id}-title`}>
              {number + 1}. {section.title}
            </h2>
            {section.body.map((block, i) =>
              typeof block === "string" ? (
                <p key={i}>{text(block)}</p>
              ) : (
                <ul key={i}>
                  {block.list.map((item, j) => (
                    <li key={j}>{text(item)}</li>
                  ))}
                </ul>
              ),
            )}
          </section>
        ))}
        <div className="legal-more row">
          <Link className="btn btn-secondary btn-sm" to={other[0]}>
            <Icon name="file" size={16} /> {t(other[1])}
          </Link>
          <Link className="btn btn-ghost btn-sm" to="/contact">
            <Icon name="mail" size={16} /> {t("site.contact")}
          </Link>
        </div>
      </article>
    </PublicShell>
  );
}

export function Terms() {
  return <LegalPage name="terms" />;
}

export function Privacy() {
  return <LegalPage name="privacy" />;
}
