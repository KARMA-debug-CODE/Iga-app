// "I have read and accept the Terms of Use and the Privacy Policy" (registration, a roster account's first
// sign-in, and a new version of the texts). The links open in a new tab so nothing typed is lost.
import { Fragment } from "react";

import { useI18n } from "../i18n";

function DocLink({ to, label }) {
  const { t } = useI18n();
  return (
    <a href={to} target="_blank" rel="noopener noreferrer">
      {label}
      <span className="sr-only"> {t("consent.newTab")}</span>
    </a>
  );
}

export default function ConsentCheckbox({ checked, onChange, student = false, id = "accept-terms" }) {
  const { t } = useI18n();
  const parts = t("consent.accept").split(/(\{terms\}|\{privacy\})/);
  const links = {
    "{terms}": <DocLink to="/terms" label={t("consent.termsLink")} />,
    "{privacy}": <DocLink to="/privacy" label={t("consent.privacyLink")} />,
  };
  return (
    <div className="consent">
      <input id={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} required />
      <label htmlFor={id}>
        {parts.map((part, i) => (
          <Fragment key={i}>{links[part] || part}</Fragment>
        ))}
        {student && <span className="consent-note">{t("consent.under16")}</span>}
      </label>
    </div>
  );
}
