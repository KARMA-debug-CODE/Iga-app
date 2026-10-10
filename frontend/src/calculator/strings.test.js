import { describe, expect, it } from "vitest";

import { CATEGORIES } from "./engine/units.js";
import STRINGS from "./strings.js";

/** Every key path of a nested strings object ("graph.errors.end", "units.length.m"). */
function paths(obj, prefix = "") {
  return Object.entries(obj).flatMap(([key, value]) =>
    value && typeof value === "object" && !Array.isArray(value) ? paths(value, `${prefix}${key}.`) : [`${prefix}${key}`],
  );
}

describe("Calculator strings", () => {
  it("has the same words in English and French", () => {
    expect(paths(STRINGS.fr).sort()).toEqual(paths(STRINGS.en).sort());
  });

  it("names every unit of every converter, in both languages", () => {
    for (const lang of ["en", "fr"]) {
      for (const [category, cat] of Object.entries(CATEGORIES)) {
        expect(STRINGS[lang].modes[category]).toBeTruthy();
        expect(Object.keys(STRINGS[lang].units[category]).sort()).toEqual([...cat.units].sort());
        for (const unit of cat.units) expect(STRINGS[lang].units[category][unit][0]).toBeTruthy();
      }
    }
  });

  it("uses French typography: a space before : ; ? !", () => {
    for (const path of paths(STRINGS.fr)) {
      const text = path.split(".").reduce((o, k) => o[k], STRINGS.fr);
      for (const value of [text].flat()) expect(value, path).not.toMatch(/[^\s\u00a0\u202f][:;?!](\s|$)/);
    }
  });
});
