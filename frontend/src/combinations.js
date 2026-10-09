// A-level combinations (S4–S6). The server sends a student's three principal subjects with the profile
// (user.combination_subjects, empty outside A-level); the full names are in the dictionaries ("combination.MCE").
export const COMBINATIONS = ["MCE", "MPC", "MEG", "MPG", "PCM", "PCB", "MCB", "HEG", "LFK"];
export const A_LEVEL = ["S4", "S5", "S6"];

/**
 * `subjects` in two groups, the student's combination first and then the other subjects, or null when the
 * list stays as it is: no combination, or a list for an O-level grade. `grade` is the grade the list is for
 * (leave it out for a list of every grade's subjects). Nothing is left out.
 */
export function subjectGroups(subjects, user, grade) {
  const principal = user?.combination_subjects || [];
  if (!principal.length || (grade && !A_LEVEL.includes(grade))) return null;
  const mine = subjects.filter((s) => principal.includes(s.code));
  if (!mine.length) return null;
  const others = subjects.filter((s) => !principal.includes(s.code));
  return [
    { key: "combination", subjects: mine },
    { key: "other", subjects: others },
  ].filter((group) => group.subjects.length);
}

/** The heading of a group from subjectGroups. */
export function groupTitle(t, group, user) {
  return group.key === "combination" ? t("learn.yourCombination", { code: user.combination }) : t("learn.otherSubjects");
}
