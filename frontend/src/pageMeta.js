// The title, description and Open Graph tags of the public pages. The app sets them as each page opens
// (usePageMeta), and the build writes a copy of index.html per public page with them already in place
// (scripts/public-pages.mjs), for search engines and link previews that don't run JavaScript.
import { useEffect } from "react";

import { useI18n } from "./i18n";

export { PUBLIC_PAGES } from "./publicPages";

const DEFAULT_TITLE = typeof document !== "undefined" ? document.title : "Iga";

export function fullTitle(title, home = false) {
  return home ? title : `${title} · Iga`;
}

function setMeta(selector, attribute, value) {
  const element = document.head.querySelector(selector);
  if (!element) return null;
  const before = element.getAttribute(attribute);
  element.setAttribute(attribute, value);
  return () => element.setAttribute(attribute, before ?? "");
}

/** Set the page's title, description and Open Graph tags while it is shown (key: see PUBLIC_PAGES). */
export function usePageMeta(key) {
  const { t, lang } = useI18n();
  useEffect(() => {
    const title = fullTitle(t(`meta.${key}.title`), key === "home");
    const description = t(`meta.${key}.description`);
    const before = document.title;
    document.title = title;
    const undo = [
      setMeta('meta[name="description"]', "content", description),
      setMeta('meta[property="og:title"]', "content", title),
      setMeta('meta[property="og:description"]', "content", description),
      setMeta('meta[property="og:locale"]', "content", lang === "fr" ? "fr_FR" : "en_GB"),
    ];
    return () => {
      document.title = before || DEFAULT_TITLE;
      undo.forEach((fn) => fn?.());
    };
  }, [key, t, lang]);
}
