import { Link } from "react-router-dom";

import { Icon } from "../components/Icon";
import { useI18n } from "../i18n";

/** What a teaching pack would have found, for a school without a subscription. */
export default function PackTeaser({ teaser, isSchoolAdmin = false }) {
  const { t } = useI18n();
  return (
    <div className="pack-teaser" role="status">
      <Icon name="lock" />
      <div>
        {teaser && teaser.misconceptions_found > 0 && (
          <p className="pack-teaser-found">
            {t("packs.teaserFound", { unit: teaser.unit, count: teaser.misconceptions_found })}
          </p>
        )}
        <p>{t("packs.teaser")}</p>
        {isSchoolAdmin ? (
          <Link to="/school/billing" className="btn btn-sm">
            {t("packs.subscribe")}
          </Link>
        ) : (
          <p className="muted">{t("packs.teaserAsk")}</p>
        )}
      </div>
    </div>
  );
}
