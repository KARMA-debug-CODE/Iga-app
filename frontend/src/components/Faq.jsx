// Questions and answers on the home page.
import { Link } from "react-router-dom";

import { useI18n } from "../i18n";
import { Icon } from "./Icon";

const QUESTIONS = ["who", "free", "subscribe", "offline", "santa", "privacy", "parents", "data", "password"];
// Answers followed by a link to the page that says more.
const MORE = { privacy: ["/privacy", "site.privacy"], subscribe: ["/pricing", "site.pricing"] };

export default function Faq() {
  const { t } = useI18n();
  return (
    <section className="section" id="faq" aria-labelledby="faq-title">
      <h2 id="faq-title" className="title-with-icon">
        <Icon name="help" size={24} /> {t("faq.title")}
      </h2>
      <div className="faq">
        {QUESTIONS.map((key) => (
          <details key={key} className="faq-item">
            <summary>
              {t(`faq.${key}.q`)}
              <Icon name="chevronDown" size={18} className="faq-chevron" />
            </summary>
            <p>
              {t(`faq.${key}.a`)}
              {MORE[key] && (
                <>
                  {" "}
                  <Link to={MORE[key][0]}>{t(MORE[key][1])}</Link>
                </>
              )}
            </p>
          </details>
        ))}
      </div>
      <p className="small">
        <Link to="/contact">{t("faq.more")}</Link>
      </p>
    </section>
  );
}
