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
  const text = DICTIONARIES[lang]?.[key] ?? en[key] ?? key;
  if (!vars) return text;
  return text.replace(/\{(\w+)\}/g, (_, name) => (vars[name] ?? `{${name}}`));
}

/** Translate outside React (e.g. in api.js), in the language the page is shown in right now. */
export function translateNow(key, vars) {
  const lang = typeof document !== "undefined" ? document.documentElement.lang : "en";
  return translate(lang, key, vars);
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
