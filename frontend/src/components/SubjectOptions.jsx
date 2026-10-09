import { useAuth } from "../auth";
import { groupTitle, subjectGroups } from "../combinations";
import { useI18n } from "../i18n";

/** The <option>s of a subject picker. An A-level student's combination comes first, in its own group. */
export default function SubjectOptions({ subjects, grade }) {
  const { user } = useAuth();
  const { t } = useI18n();
  const option = (s) => (
    <option key={s.code} value={s.code}>
      {s.display_name || s.name}
    </option>
  );
  const groups = subjectGroups(subjects, user, grade);
  if (!groups) return subjects.map(option);
  return groups.map((group) => (
    <optgroup key={group.key} label={groupTitle(t, group, user)}>
      {group.subjects.map(option)}
    </optgroup>
  ));
}
