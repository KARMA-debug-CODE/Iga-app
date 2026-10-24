// The public pages: path -> key of their title and description in the dictionaries (meta.<key>.title and
// meta.<key>.description). No imports, so the build (vite.config.js) can read it too.
export const PUBLIC_PAGES = {
  "/": "home",
  "/pricing": "home",
  "/faq": "home",
  "/register": "register",
  "/login": "login",
  "/contact": "contact",
  "/terms": "terms",
  "/privacy": "privacy",
};
