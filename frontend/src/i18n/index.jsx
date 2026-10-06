import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import en from "./en";
import fr from "./fr";

export const LANGUAGES = [
  { code: "en", name: "English" },
  { code: "fr", name: "Français" },
];
const DICTIONARIES = { en, fr };
const STORAGE_KEY = "iga.lang";

export function translate(lang, key, vars) {
  // "<key>.one" is the singular form, used when vars.n is 1 ("1 month" rather than "1 months").
  const singular = vars?.n === 1 ? (DICTIONARIES[lang]?.[`${key}.one`] ?? en[`${key}.one`]) : undefined;
  const text = singular ?? DICTIONARIES[lang]?.[key] ?? en[key] ?? key;
  if (!vars) return text;
  return text.replace(/\{(\w+)\}/g, (_, name) => (vars[name] ?? `{${name}}`));
}

/** The language the page is shown in right now (for code outside React, e.g. api.js). */
export function currentLanguage() {
  const lang = typeof document !== "undefined" ? document.documentElement.lang : "";
  return DICTIONARIES[lang] ? lang : "en";
}

/** Translate outside React (e.g. in api.js), in the language the page is shown in right now. */
export function translateNow(key, vars) {
  return translate(currentLanguage(), key, vars);
}

/** True when the dictionaries have a text for this key (English counts). */
export function hasTranslation(key) {
  return key in en;
}

function storedLanguage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && DICTIONARIES[saved]) return saved;
  } catch {
    /* storage blocked */
  }
  const browser = (navigator.language || "en").slice(0, 2);
  return DICTIONARIES[browser] ? browser : "en";
}

const I18nContext = createContext({ lang: "en", setLang: () => {}, t: (k) => k });

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(storedLanguage);

  const setLang = useCallback((next) => {
    if (!DICTIONARIES[next]) return;
    setLangState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const t = useCallback((key, vars) => translate(lang, key, vars), [lang]);
  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
