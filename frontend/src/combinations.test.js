import { describe, expect, it } from "vitest";

import { subjectGroups } from "./combinations";

const subjects = ["mathematics", "physics", "ict", "computer-science", "english", "economics"].map((code) => ({ code }));
const codes = (groups) => groups.map((g) => [g.key, g.subjects.map((s) => s.code)]);
const mce = { grade: "S5", combination: "MCE", combination_subjects: ["mathematics", "computer-science", "economics"] };

describe("subjectGroups", () => {
  it("lists an A-level student's combination first, then every other subject", () => {
    expect(codes(subjectGroups(subjects, mce, "S5"))).toEqual([
      ["combination", ["mathematics", "computer-science", "economics"]],
      ["other", ["physics", "ict", "english"]],
    ]);
  });

  it("groups lists of every grade's subjects too", () => {
    expect(subjectGroups(subjects, mce)).toHaveLength(2);
  });

  it("leaves the list alone without a combination, or for an O-level grade", () => {
    expect(subjectGroups(subjects, { grade: "S5", combination: "", combination_subjects: [] }, "S5")).toBeNull();
    expect(subjectGroups(subjects, { grade: "S2", combination_subjects: [] }, "S2")).toBeNull();
    expect(subjectGroups(subjects, mce, "S2")).toBeNull();
    expect(subjectGroups(subjects, null, "S5")).toBeNull();
    expect(subjectGroups([{ code: "english" }], mce, "S5")).toBeNull();
  });
});
