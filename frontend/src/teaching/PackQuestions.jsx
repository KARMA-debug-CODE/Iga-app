import Markdown from "../components/Markdown";
import { Icon } from "../components/Icon";
import { useI18n } from "../i18n";

const LETTERS = "ABCDEFGHIJ";

/** A pack's questions, with their answers only when `showAnswers` (the teacher's key, never the student copy). */
export default function PackQuestions({ questions, showAnswers = false, start = 1 }) {
  const { t } = useI18n();
  return (
    <ol className="pack-questions" start={start}>
      {questions.map((q) => (
        <li key={q.id} className="pack-question">
          <Markdown interactive={false}>{q.prompt}</Markdown>
          {q.choices.length > 0 && (
            <ul className="pack-choices">
              {q.choices.map((c, i) => (
                <li key={c.id} className={showAnswers && c.is_correct ? "is-correct" : ""}>
                  <span className="pack-choice-letter">{LETTERS[i]}</span>
                  <Markdown interactive={false}>{c.text}</Markdown>
                  {showAnswers && c.is_correct && <Icon name="check" label={t("packs.correctChoice")} />}
                </li>
              ))}
            </ul>
          )}
          {showAnswers && (
            <div className="pack-answer">
              {q.numeric_answer !== null && q.numeric_answer !== undefined && <p>{t("packs.answer", { answer: q.numeric_answer })}</p>}
              {q.accepted_answers?.length > 0 && <p>{t("packs.answer", { answer: q.accepted_answers.join(" / ") })}</p>}
              {q.marking_guide && <p>{t("packs.markingGuide", { text: q.marking_guide })}</p>}
              {q.explanation && (
                <div className="pack-explanation">
                  <strong>{t("packs.explanation")}</strong>
                  <Markdown interactive={false}>{q.explanation}</Markdown>
                </div>
              )}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
