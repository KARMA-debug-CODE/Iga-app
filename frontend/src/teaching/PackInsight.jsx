import Markdown from "../components/Markdown";
import { scoreClass } from "../components/ui";
import { useI18n } from "../i18n";

/** What the class gets wrong in the unit, and who needs most help (teacher only). */
export default function PackInsight({ insight, studentsNeedingHelp }) {
  const { t } = useI18n();
  return (
    <>
      <section className="card pack-section">
        {insight.average !== null && <p className="pack-average">{t("packs.classAverage", { value: insight.average })}</p>}
        {insight.other_units.length > 0 && (
          <p className="muted">
            {t("packs.otherUnits")}: {insight.other_units.map((u) => `${u.label} (${u.average}%)`).join(", ")}
          </p>
        )}
        {!insight.data_enough && <p className="pack-notice">{t("packs.notEnough")}</p>}
        {insight.misconceptions.length > 0 && (
          <>
            <h3>{t("packs.misconceptions")}</h3>
            <ol className="pack-misconceptions">
              {insight.misconceptions.map((m) => (
                <li key={m.question_id}>
                  <Markdown interactive={false}>{m.prompt}</Markdown>
                  <p className="pack-wrong">{t("packs.chose", { share: Math.round(m.share * 100), choice: m.wrong_choice })}</p>
                  <p>{t("packs.correctAnswer", { answer: m.correct })}</p>
                  {m.explanation && <Markdown interactive={false}>{m.explanation}</Markdown>}
                </li>
              ))}
            </ol>
          </>
        )}
        {insight.hardest.length > 0 && (
          <>
            <h3>{t("packs.hardest")}</h3>
            <ul className="list">
              {insight.hardest.map((h) => (
                <li key={h.question_id} className="spread">
                  <Markdown interactive={false}>{h.prompt}</Markdown>
                  <span className={scoreClass(h.correct_share * 100)}>
                    {t("packs.rightShare", { share: Math.round(h.correct_share * 100) })}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
      <section className="card pack-section">
        <h3>{t("packs.needHelp")}</h3>
        <p className="muted">{t("packs.teacherOnly")}</p>
        {studentsNeedingHelp.length === 0 ? (
          <p>{t("packs.needHelpNone")}</p>
        ) : (
          <ul className="list">
            {studentsNeedingHelp.map((s) => (
              <li key={s.id} className="spread">
                <span>{s.display_name}</span>
                <span className={scoreClass(s.average)}>{s.average}%</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
