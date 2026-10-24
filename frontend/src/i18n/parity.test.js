// Every text in the app is in English and French: a key missing from fr.js would show English to French readers.
import { describe, expect, it } from "vitest";

import en from "./en";
import fr from "./fr";

describe("translations", () => {
  it("have a French text for every English one", () => {
    expect(Object.keys(en).filter((key) => !(key in fr))).toEqual([]);
  });

  it("have no French text without an English one", () => {
    // A singular form ("<key>.one") may exist in one language only, when the other needs none.
    const orphan = (key) => !(key in en) && !(key.endsWith(".one") && key.slice(0, -4) in en);
    expect(Object.keys(fr).filter(orphan)).toEqual([]);
  });

  it("keep the same {placeholders} in both languages", () => {
    const names = (text) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    const different = Object.keys(en).filter((key) => key in fr && names(en[key]).join() !== names(fr[key]).join());
    expect(different).toEqual([]);
  });
});
