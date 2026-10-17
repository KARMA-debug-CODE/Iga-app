// After the build: a copy of index.html for each public page (dist/terms.html, dist/contact.html, ...) with that
// page's title, description and Open Graph tags already in place, for search engines and link previews that
// don't run JavaScript. nginx serves /terms from terms.html (try_files $uri $uri.html), and the app then sets
// the same tags in the reader's language (src/pageMeta.js). The texts come from src/i18n/en.js.
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import en from "../src/i18n/en.js";
import { PUBLIC_PAGES } from "../src/publicPages.js";

const escape = (text) => text.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function setTag(html, pattern, replacement) {
  if (!pattern.test(html)) throw new Error(`index.html has no ${pattern}: keep the tags public-pages.mjs fills in`);
  return html.replace(pattern, replacement);
}

/** `html` (index.html) with the title, description and Open Graph tags of the page whose texts are `key`. */
export function pageHtml(html, key, dictionary = en) {
  const name = dictionary[`meta.${key}.title`];
  const title = key === "home" ? name : `${name} · Iga`;
  const description = dictionary[`meta.${key}.description`];
  if (!name || !description) throw new Error(`No meta.${key}.title / meta.${key}.description in the dictionary`);
  let out = setTag(html, /<title>[^<]*<\/title>/, `<title>${escape(title)}</title>`);
  out = setTag(out, /<meta name="description" content="[^"]*" \/>/, `<meta name="description" content="${escape(description)}" />`);
  out = setTag(out, /<meta property="og:title" content="[^"]*" \/>/, `<meta property="og:title" content="${escape(title)}" />`);
  out = setTag(out, /<meta property="og:description" content="[^"]*" \/>/, `<meta property="og:description" content="${escape(description)}" />`);
  return out;
}

/** The file a public page's copy goes to: "/" -> index.html, "/terms" -> terms.html. */
export function pageFile(path) {
  return path === "/" ? "index.html" : `${path.slice(1)}.html`;
}

export default function publicPages() {
  let outDir = "dist";
  return {
    name: "iga-public-pages",
    apply: "build",
    configResolved(config) {
      outDir = config.build.outDir;
    },
    closeBundle() {
      const template = readFileSync(join(outDir, "index.html"), "utf8");
      for (const [path, key] of Object.entries(PUBLIC_PAGES)) {
        writeFileSync(join(outDir, pageFile(path)), pageHtml(template, key));
      }
    },
  };
}
