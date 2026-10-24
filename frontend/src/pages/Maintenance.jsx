// "Back soon": Iga is being updated (maintenance mode). The server answers 503 to everyone but the Iga team,
// who log in at /team.
import { Link } from "react-router-dom";

import { Icon } from "../components/Icon";
import LanguagePicker from "../components/LanguagePicker";
import { Logo } from "../components/ui";
import { useI18n } from "../i18n";

export default function Maintenance() {
  const { t } = useI18n();
  return (
    <div className="maintenance-page">
      <main id="main" className="card maintenance-card">
        <Logo size={56} />
        <h1>{t("maintenance.title")}</h1>
        <p>{t("maintenance.text")}</p>
        <p className="muted small">{t("maintenance.offline")}</p>
        <button className="btn" onClick={() => window.location.reload()}>
          <Icon name="refresh" size={18} /> {t("maintenance.retry")}
        </button>
        <p className="small" style={{ marginTop: 18 }}>
          <Link to="/team">{t("maintenance.team")}</Link>
        </p>
      </main>
      <LanguagePicker />
    </div>
  );
}
