import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import en from "../src/i18n/en.js";
import fr from "../src/i18n/fr.js";
import { PUBLIC_PAGES } from "../src/publicPages.js";
import { pageFile, pageHtml } from "./public-pages.mjs";

const INDEX = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "..", "index.html"), "utf8");

describe("public pages' own HTML", () => {
  it("puts each page's title, description and Open Graph tags in its copy of index.html", () => {
    const html = pageHtml(INDEX, "privacy");
    expect(html).toContain("<title>Privacy Policy · Iga</title>");
    expect(html).toContain(`<meta name="description" content="${en["meta.privacy.description"]}" />`);
    expect(html).toContain('<meta property="og:title" content="Privacy Policy · Iga" />');
    expect(html).toContain('<div id="root"></div>');
  });

  it("escapes the texts", () => {
    const html = pageHtml(INDEX, "x", { "meta.x.title": 'A "b" <c>', "meta.x.description": "d & e" });
    expect(html).toContain("<title>A &quot;b&quot; &lt;c&gt; · Iga</title>");
    expect(html).toContain('content="d &amp; e"');
  });

  it("has texts in both languages for every public page", () => {
    for (const key of new Set(Object.values(PUBLIC_PAGES))) {
      for (const dictionary of [en, fr]) {
        expect(dictionary[`meta.${key}.title`], key).toBeTruthy();
        expect(dictionary[`meta.${key}.description`], key).toBeTruthy();
      }
    }
    expect(pageFile("/")).toBe("index.html");
    expect(pageFile("/terms")).toBe("terms.html");
  });
});
