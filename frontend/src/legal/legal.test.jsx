// The Terms of Use and the Privacy Policy, in English and French (src/legal/), and how the page shows them.
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { renderText } from "../pages/Legal";
import privacyEn from "./privacy.en.js";
import privacyFr from "./privacy.fr.js";
import termsEn from "./terms.en.js";
import termsFr from "./terms.fr.js";

const PLACEHOLDER = /\{(\w+)\}/g;
const LINK = /\[[^\]]+\]\(([^)]+)\)/g;
// Every {placeholder} the page knows how to fill in (pages/Legal.jsx).
const KNOWN = new Set([
  "entity",
  "address",
  "email",
  "hosting",
  "version",
  "graceDays",
  "santaDays",
  "auditDays",
  "usageDays",
  "contactDays",
  "backupDays",
  "tempDays",
  "sessionDays",
  "subscriptionGraceDays",
]);

function texts(doc) {
  const out = [...doc.intro];
  for (const section of doc.sections) for (const block of section.body) out.push(...(typeof block === "string" ? [block] : block.list));
  return out;
}

const found = (doc, pattern) => texts(doc).flatMap((text) => [...text.matchAll(pattern)].map((m) => m[1]));

describe.each([
  ["Terms of Use", termsEn, termsFr],
  ["Privacy Policy", privacyEn, privacyFr],
])("%s", (name, en, fr) => {
  it("has the same sections in English and French", () => {
    expect(fr.sections.map((s) => s.id)).toEqual(en.sections.map((s) => s.id));
    en.sections.forEach((section, i) => {
      const shape = (s) => s.body.map((block) => (typeof block === "string" ? "p" : `list:${block.list.length}`));
      expect(shape(fr.sections[i]), section.id).toEqual(shape(section));
    });
  });

  it("uses the same server values and links in both languages, and only ones the page fills in", () => {
    expect(new Set(found(fr, PLACEHOLDER))).toEqual(new Set(found(en, PLACEHOLDER)));
    expect(found(fr, LINK).sort()).toEqual(found(en, LINK).sort());
    for (const key of found(en, PLACEHOLDER)) expect(KNOWN.has(key), key).toBe(true);
    for (const path of found(en, LINK)) expect(["/terms", "/privacy", "/contact"]).toContain(path);
  });

  it("names the contact address and the owner", () => {
    expect(found(en, PLACEHOLDER)).toEqual(expect.arrayContaining(["entity", "email"]));
  });
});

describe("the Privacy Policy covers what the law and the app need", () => {
  it.each([
    ["058/2021", "058/2021"],
    ["Flutterwave", "Flutterwave"],
    ["under 16", "moins de 16 ans"],
    ["Download my data", "Télécharger mes données"],
    ["Delete my account", "Supprimer mon compte"],
    ["NCSA", "NCSA"],
    ["iga_refresh", "iga_refresh"],
    ["Santa", "Santa"],
  ])("mentions %s", (english, french) => {
    expect(texts(privacyEn).join(" ")).toContain(english);
    expect(texts(privacyFr).join(" ")).toContain(french);
  });

  it("keeps every right the law gives: access, correction, deletion, objection", () => {
    const rights = privacyEn.sections.find((s) => s.id === "rights").body[1].list.join(" ");
    for (const word of ["See your data", "Correct it", "Delete it", "Object to"]) expect(rights).toContain(word);
  });
});

describe("renderText", () => {
  const html = (text, lang = "en") =>
    renderToStaticMarkup(<MemoryRouter>{renderText(text, { email: "dpo@iga.rw", graceDays: "14 days" }, lang)}</MemoryRouter>).replace(
      ' data-discover="true"',
      "",
    );

  it("fills in the server's values and makes links to the app's pages", () => {
    expect(html("Write to {email}, or use the [contact page](/contact). Erased {graceDays} later.")).toBe(
      'Write to dpo@iga.rw, or use the <a href="/contact">contact page</a>. Erased 14 days later.',
    );
  });

  it("never links outside the app", () => {
    expect(html("[evil](javascript:alert) and [far](//evil.example)")).toBe("evil and far");
  });

  it("keeps French punctuation on the same line as its word", () => {
    expect(html("E-mail : {email}", "fr")).toBe("E-mail : dpo@iga.rw");
  });

  it("leaves unknown placeholders visible rather than empty", () => {
    expect(html("{nothing}")).toBe("{nothing}");
  });
});
