import { Link } from "react-router-dom";

import { Empty } from "../components/ui";
import { useI18n } from "../i18n";

export default function NotFound() {
  const { t } = useI18n();
  return (
    <Empty icon="🧭">
      {t("common.notFound")} · <Link to="/">{t("common.goHome")}</Link>
    </Empty>
  );
}
