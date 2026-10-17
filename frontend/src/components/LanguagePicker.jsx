import { LANGUAGES, useI18n } from "../i18n";

export default function LanguagePicker() {
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
