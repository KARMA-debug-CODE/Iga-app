import Markdown from "../components/Markdown";
import { useI18n } from "../i18n";
import PackQuestions from "./PackQuestions";

export const PRINT_MODES = ["insight", "plan", "worksheet", "key", "quiz"];
const LEVELS = ["support", "core", "stretch"];
const PLAN_HEADER = [
  "school", "teacher", "term", "date", "subject", "class_name", "unit_number", "lesson_number", "duration", "class_size",
  "sen_learners",
];
const PLAN_BODY = ["unit_title", "key_unit_competence", "lesson_title", "objective", "location", "materials", "references"];

function StudentLines() {
  const { t } = useI18n();
  return (
    <div className="pack-print-lines">
      <span>{t("packs.print.name")}</span>
      <span>{t("packs.print.date")}</span>
    </div>
  );
}

function Heading({ title, pack }) {
  const doc = pack.document;
  return (
    <header className="pack-print-header">
      <p className="muted">
        {doc.plan.school && `${doc.plan.school} · `}
        {doc.classroom.name}
      </p>
      <h1>{title}</h1>
    </header>
  );
}

function Levels({ worksheet, showAnswers }) {
  const { t } = useI18n();
  return LEVELS.filter((level) => worksheet[level].length > 0).map((level) => (
    <section key={level} className="pack-print-level">
      <h2>{t(`packs.level.${level}`)}</h2>
      <PackQuestions questions={worksheet[level]} showAnswers={showAnswers} />
    </section>
  ));
}

function Plan({ pack }) {
  const { t } = useI18n();
  const plan = pack.document.plan;
  const row = (name) => (
    <tr key={name}>
      <th scope="row">{t(`packs.f.${name}`)}</th>
      <td>{plan[name]}</td>
    </tr>
  );
  return (
    <>
      <table className="pack-print-table">
        <tbody>{[...PLAN_HEADER, ...PLAN_BODY].map(row)}</tbody>
      </table>
      <h2>{t("packs.steps")}</h2>
      <table className="pack-print-table pack-print-steps">
        <thead>
          <tr>
            <th scope="col">{t("packs.print.timing")}</th>
            <th scope="col">{t("packs.col.teacher")}</th>
            <th scope="col">{t("packs.col.learners")}</th>
            <th scope="col">{t("packs.col.competences")}</th>
          </tr>
        </thead>
        <tbody>
          {plan.steps.map((step) => (
            <tr key={step.name}>
              <td>
                {t(`packs.step.${step.name}`)}
                <br />
                {t("packs.minutes", { minutes: step.minutes })}
              </td>
              <td className="pack-print-text">{step.teacher}</td>
              <td className="pack-print-text">{step.learners}</td>
              <td className="pack-print-text">{step.competences}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <table className="pack-print-table">
        <tbody>{["evaluation", "self_evaluation"].map(row)}</tbody>
      </table>
    </>
  );
}

function Insight({ pack }) {
  const { t } = useI18n();
  const insight = pack.document.insight;
  return (
    <>
      {insight.average !== null && <p>{t("packs.classAverage", { value: insight.average })}</p>}
      {!insight.data_enough && <p>{t("packs.notEnough")}</p>}
      {insight.misconceptions.length > 0 && (
        <>
          <h2>{t("packs.misconceptions")}</h2>
          <ol>
            {insight.misconceptions.map((m) => (
              <li key={m.question_id}>
                <Markdown interactive={false}>{m.prompt}</Markdown>
                <p>{t("packs.chose", { share: Math.round(m.share * 100), choice: m.wrong_choice })}</p>
                <p>{t("packs.correctAnswer", { answer: m.correct })}</p>
              </li>
            ))}
          </ol>
        </>
      )}
      {insight.hardest.length > 0 && (
        <>
          <h2>{t("packs.hardest")}</h2>
          <ul>
            {insight.hardest.map((h) => (
              <li key={h.question_id}>
                <Markdown interactive={false}>{h.prompt}</Markdown> {t("packs.rightShare", { share: Math.round(h.correct_share * 100) })}
              </li>
            ))}
          </ul>
        </>
      )}
      <h2>{t("packs.needHelp")}</h2>
      {pack.students_needing_help.length === 0 ? (
        <p>{t("packs.needHelpNone")}</p>
      ) : (
        <ul>
          {pack.students_needing_help.map((s) => (
            <li key={s.id}>
              <span>{s.display_name}</span> ({s.average}%)
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

/** A pack laid out for paper: the student copies never contain answers; the keys and the insight are for the teacher. */
export default function PackPrint({ pack, mode }) {
  const { t } = useI18n();
  const doc = pack.document;
  const unit = doc.unit.label;
  const quizTitle = doc.quiz.diagnostic ? t("packs.diagnosticTitle") : t("packs.targetedTitle");
  return (
    <div className={`pack-print pack-print-${mode}`}>
      {mode === "worksheet" && (
        <>
          <Heading title={t("packs.print.worksheetTitle", { unit })} pack={pack} />
          <StudentLines />
          <div className="pack-print-questions">
            <Levels worksheet={doc.worksheet} showAnswers={false} />
          </div>
        </>
      )}
      {mode === "key" && (
        <>
          <Heading title={t("packs.print.keyTitle", { unit })} pack={pack} />
          <Levels worksheet={doc.worksheet} showAnswers />
        </>
      )}
      {mode === "quiz" && (
        <>
          <Heading title={`${quizTitle}: ${unit}`} pack={pack} />
          <StudentLines />
          <div className="pack-print-questions">
            <PackQuestions questions={doc.quiz.questions} />
          </div>
          <section className="pack-page-break">
            <h2>{t("packs.print.quizKey")}</h2>
            <PackQuestions questions={doc.quiz.questions} showAnswers />
          </section>
        </>
      )}
      {mode === "plan" && (
        <>
          <Heading title={t("packs.print.planTitle")} pack={pack} />
          <Plan pack={pack} />
        </>
      )}
      {mode === "insight" && (
        <>
          <Heading title={`${t("packs.print.teacherOnly")}: ${unit}`} pack={pack} />
          <Insight pack={pack} />
        </>
      )}
    </div>
  );
}
