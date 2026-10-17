// How a question, its choices and its solution are shown — shared by the quiz player and the review deck,
// so an answered question looks the same wherever it appears.
import Markdown from "./Markdown";
import { Icon } from "./Icon";
import { useI18n } from "../i18n";

export const CHOICE_TYPES = ["mcq", "multi", "true_false"];

export function isAnswered(question, answer) {
  if (!answer) return false;
  if (CHOICE_TYPES.includes(question.type)) return (answer.choice_ids || []).length > 0;
  if (question.type === "numeric") return answer.numeric !== null && answer.numeric !== undefined && answer.numeric !== "";
  return Boolean(answer.text && answer.text.trim());
}

export function verdict(question) {
  const s = question.solution;
  if (!s) return null;
  if (s.is_correct === null || s.marks_awarded === null) return "pending";
  if (s.is_correct) return "right";
  return Number(s.marks_awarded) > 0 ? "partial" : "wrong";
}

export function QuestionBody({ question, answer, onChange, locked }) {
  const { t } = useI18n();
  const solution = question.solution;
  const correct = new Set(solution?.correct_choice_ids || []);
  const selected = new Set(answer?.choice_ids || []);

  if (CHOICE_TYPES.includes(question.type)) {
    const multi = question.type === "multi";
    return (
      <div className="stack" role={multi ? "group" : "radiogroup"}>
        {multi && <span className="small muted">{t("quiz.chooseMany")}</span>}
        {question.choices.map((choice) => {
          const isSelected = selected.has(choice.id);
          let cls = isSelected ? "selected" : "";
          if (solution) {
            if (correct.has(choice.id)) cls = "correct";
            else if (isSelected) cls = "wrong";
          }
          return (
            <label key={choice.id} className={`option ${cls}`}>
              <input
                type={multi ? "checkbox" : "radio"}
                name={`q-${question.id}`}
                checked={isSelected}
                disabled={locked}
                onChange={() => {
                  const next = multi
                    ? isSelected
                      ? [...selected].filter((id) => id !== choice.id)
                      : [...selected, choice.id]
                    : [choice.id];
                  onChange({ choice_ids: next });
                }}
              />
              <Markdown interactive={false}>{choice.text}</Markdown>
            </label>
          );
        })}
      </div>
    );
  }

  if (question.type === "numeric") {
    return (
      <input
        type="number"
        step="any"
        inputMode="decimal"
        placeholder={t("quiz.numberPlaceholder")}
        value={answer?.numeric ?? ""}
        disabled={locked}
        onChange={(e) => onChange({ numeric: e.target.value === "" ? null : e.target.value })}
        aria-label={t("quiz.yourAnswer")}
        style={{ maxWidth: 260 }}
      />
    );
  }

  if (question.type === "short") {
    return (
      <input
        placeholder={t("quiz.textPlaceholder")}
        value={answer?.text ?? ""}
        disabled={locked}
        onChange={(e) => onChange({ text: e.target.value })}
        aria-label={t("quiz.yourAnswer")}
      />
    );
  }

  return (
    <textarea
      placeholder={t("quiz.essayPlaceholder")}
      value={answer?.text ?? ""}
      disabled={locked}
      onChange={(e) => onChange({ text: e.target.value })}
      rows={8}
      aria-label={t("quiz.yourAnswer")}
    />
  );
}

export function SolutionPanel({ question, answer }) {
  const { t } = useI18n();
  const s = question.solution;
  if (!s) return null;
  const v = verdict(question);
  const cls = v === "right" ? "good" : v === "wrong" ? "bad" : "neutral";
  const [icon, heading] = {
    right: ["ok", t("quiz.correct")],
    wrong: ["fail", t("quiz.incorrect")],
    partial: ["partial", t("quiz.partly")],
    pending: ["teach", t("quiz.teacherMarked")],
  }[v];
  const showTyped = ["numeric", "short"].includes(question.type);
  const expected = question.type === "numeric" ? s.numeric_answer : s.accepted_answers?.[0];

  return (
    <div className={`feedback ${cls}`} aria-live="polite">
      <div className="spread">
        <strong className="with-icon">
          <Icon name={icon} /> {heading}
        </strong>
        {s.marks_awarded !== null && s.marks_awarded !== undefined && (
          <span className="pill">
            {Number(s.marks_awarded)} / {Number(question.marks)}
          </span>
        )}
      </div>
      {showTyped && (
        <p style={{ margin: "8px 0 0" }}>
          {t("quiz.yourAnswer")}: <strong>{(question.type === "numeric" ? answer?.numeric : answer?.text) ?? t("quiz.noAnswer")}</strong>
          {v !== "right" && expected !== undefined && expected !== null && (
            <>
              {" · "}
              {t("quiz.correctAnswer")}: <strong>{String(expected)}</strong>
            </>
          )}
        </p>
      )}
      {s.teacher_feedback && (
        <div style={{ marginTop: 10 }}>
          <strong>{t("quiz.teacherFeedback")}:</strong> {s.teacher_feedback}
        </div>
      )}
      {s.explanation && (
        <div style={{ marginTop: 10 }}>
          <strong>{t("quiz.explanation")}</strong>
          <Markdown interactive={false}>{s.explanation}</Markdown>
        </div>
      )}
      {s.marking_guide && (
        <details style={{ marginTop: 8 }}>
          <summary>{t("quiz.markingGuide")}</summary>
          <Markdown interactive={false}>{s.marking_guide}</Markdown>
        </details>
      )}
    </div>
  );
}
