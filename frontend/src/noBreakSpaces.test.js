import { describe, expect, it } from "vitest";

import remarkNoBreakSpaces, { keepPunctuationAttached } from "./noBreakSpaces";

describe("no-break spaces before French punctuation", () => {
  it("joins : ; ? ! » to the word before, and « to the word after", () => {
    expect(keepPunctuationAttached("P2 arrive à 2 ; il reste 5 ms. Pourquoi ? « hexa » : oui !")).toBe(
      "P2 arrive à 2 ; il reste 5 ms. Pourquoi ? « hexa » : oui !",
    );
  });

  it("leaves English, links and times alone", () => {
    expect(keepPunctuationAttached("Unit 5: Number systems, https://reb.rw, 10:30")).toBe("Unit 5: Number systems, https://reb.rw, 10:30");
  });

  it("changes text only, never code or maths", () => {
    const tree = {
      type: "root",
      children: [
        {
          type: "paragraph",
          children: [
            { type: "text", value: "Exemple : " },
            { type: "inlineCode", value: "a ? b : c" },
            { type: "inlineMath", value: "x : y" },
          ],
        },
      ],
    };
    remarkNoBreakSpaces()(tree);
    expect(tree.children[0].children.map((n) => n.value)).toEqual(["Exemple : ", "a ? b : c", "x : y"]);
  });
});
