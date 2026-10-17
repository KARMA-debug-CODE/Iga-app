// The pricing section of the home page. Prices, month options and the grace period come from the server's
// price list (/api/site/, the same one the school's billing page uses), never from this file.
import { Link } from "react-router-dom";

import { formatMoney } from "../hooks";
import { useI18n } from "../i18n";
import { useSiteInfo } from "../site";
import { Icon } from "./Icon";

function Benefits({ keys }) {
  const { t } = useI18n();
  return (
    <ul className="pricing-list">
      {keys.map((key) => (
        <li key={key}>
          <Icon name="check" size={18} /> <span>{t(key)}</span>
        </li>
      ))}
    </ul>
  );
}

export function monthList(options, t) {
  if (!options?.length) return "";
  if (options.length === 1) return String(options[0]);
  return t("pricing.monthsOr", { list: options.slice(0, -1).join(", "), last: options[options.length - 1] });
}

export default function Pricing() {
  const { t, lang } = useI18n();
  const site = useSiteInfo();
  const pricing = site.data?.pricing;
  const currencies = Object.keys(pricing?.prices || {});
  const main = currencies.includes("USD") ? "USD" : currencies[0];

  return (
    <section className="section" id="pricing" aria-labelledby="pricing-title">
      <h2 id="pricing-title" className="title-with-icon">
        <Icon name="receipt" size={24} /> {t("pricing.title")}
      </h2>
      <p className="muted">{t("pricing.intro")}</p>
      <div className="grid-2 pricing">
        <div className="card pricing-card">
          <h3>{t("pricing.free")}</h3>
          <p className="pricing-price">{t("pricing.free")}</p>
          <p className="muted small">{t("pricing.freeFor")}</p>
          <Benefits keys={["pricing.free.1", "pricing.free.2", "pricing.free.3"]} />
          <Link className="btn btn-secondary" to="/register">
            {t("auth.joinNow")}
          </Link>
        </div>
        <div className="card pricing-card pricing-featured">
          <h3>{t("pricing.school")}</h3>
          {main ? (
            <>
              <p className="pricing-price">{formatMoney(pricing.prices[main], main, lang)}</p>
              <p className="muted small">
                {t("pricing.perMonth")}
                {currencies
                  .filter((c) => c !== main)
                  .map((c) => ` · ${t("pricing.or", { price: formatMoney(pricing.prices[c], c, lang) })}`)
                  .join("")}
              </p>
            </>
          ) : (
            <p className="muted small">{site.error ? t("pricing.unavailable") : t("common.loading")}</p>
          )}
          <Benefits keys={["pricing.school.1", "pricing.school.2", "pricing.school.3"]} />
          {pricing && (
            <ul className="pricing-notes small muted">
              <li>{t("pricing.months", { months: monthList(pricing.month_options, t) })}</li>
              <li>{t("pricing.payment")}</li>
              <li>{t("pricing.grace", { n: pricing.grace_days })}</li>
            </ul>
          )}
          <div className="row">
            <Link className="btn" to="/register?role=school_admin">
              {t("pricing.register")}
            </Link>
            <Link className="btn btn-ghost" to="/contact">
              {t("pricing.talk")}
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
