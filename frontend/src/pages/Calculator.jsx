import Calculator from "../calculator/Calculator";
import { Icon } from "../components/Icon";
import { useI18n } from "../i18n";

export default function CalculatorPage() {
  const { t, lang } = useI18n();
  return (
    <div className="calc-page">
      <div className="page-header">
        <h1 className="title-with-icon">
          <Icon name="calculator" size={28} /> {t("nav.calculator")}
        </h1>
        <p>{t("calc.pageIntro")}</p>
      </div>
      <Calculator lang={lang} />
    </div>
  );
}
