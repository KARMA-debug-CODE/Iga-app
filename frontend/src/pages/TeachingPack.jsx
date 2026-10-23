import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Icon } from "../components/Icon";
import { ErrorMessage, Loader, Tabs } from "../components/ui";
import { formatDate, useApi } from "../hooks";
import { useI18n } from "../i18n";
import AssignDialog from "../teaching/AssignDialog";
import { createPack } from "../teaching/createPack";
import PackInsight from "../teaching/PackInsight";
import PackPlan from "../teaching/PackPlan";
import PackQuestions from "../teaching/PackQuestions";
import PackTeaser from "../teaching/PackTeaser";

const LEVELS = ["support", "core", "stretch"];

function Notes({ notes }) {
  if (!notes?.length) return null;
  return (
    <ul className="pack-notes">
      {notes.map((note) => (
        <li key={note}>{note}</li>
      ))}
    </ul>
  );
}

/** One part of the pack that can be assigned: its button, then the assign form. */
function AssignPart({ pack, what, label, disabled }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  if (open) return <AssignDialog packId={pack.id} what={what} classroomId={pack.classroom} onClose={() => setOpen(false)} />;
  return (
    <button type="button" className="btn btn-secondary btn-sm" disabled={disabled} onClick={() => setOpen(true)} aria-label={label}>
      <Icon name="send" /> {t("packs.assign")}
    </button>
  );
}

function Worksheet({ pack }) {
  const { t } = useI18n();
  const [answers, setAnswers] = useState(false);
  const sheet = pack.document.worksheet;
  return (
    <section className="card pack-section">
      <label className="pack-toggle">
        <input type="checkbox" checked={answers} onChange={(e) => setAnswers(e.target.checked)} /> {t("packs.showAnswers")}
      </label>
      <Notes notes={sheet.notes} />
      {LEVELS.map((level) => {
        const name = t(`packs.level.${level}`);
        return (
          <div key={level} className="pack-level">
            <div className="spread">
              <h3>
                {name} <span className="muted">{t("packs.questionsCount", { count: sheet[level].length })}</span>
              </h3>
              <AssignPart
                pack={pack}
                what={`worksheet_${level}`}
                label={t("packs.assignLevel", { level: name.toLowerCase() })}
                disabled={sheet[level].length === 0}
              />
            </div>
            {sheet[level].length === 0 ? <p className="muted">{t("packs.noQuestions")}</p> : <PackQuestions questions={sheet[level]} showAnswers={answers} />}
          </div>
        );
      })}
    </section>
  );
}

function Quiz({ pack }) {
  const { t } = useI18n();
  const [answers, setAnswers] = useState(false);
  const quiz = pack.document.quiz;
  return (
    <section className="card pack-section">
      <div className="spread">
        <h3>{quiz.diagnostic ? t("packs.diagnosticTitle") : t("packs.targetedTitle")}</h3>
        <AssignPart pack={pack} what="quiz" label={t("packs.assign")} disabled={quiz.questions.length === 0} />
      </div>
      <p className="muted">{quiz.diagnostic ? t("packs.diagnostic") : t("packs.targeted")}</p>
      <label className="pack-toggle">
        <input type="checkbox" checked={answers} onChange={(e) => setAnswers(e.target.checked)} /> {t("packs.showAnswers")}
      </label>
      {quiz.questions.length === 0 ? <p className="muted">{t("packs.noQuestions")}</p> : <PackQuestions questions={quiz.questions} showAnswers={answers} />}
    </section>
  );
}

/** A teaching pack: what the class gets wrong, the lesson plan, the worksheet and the quiz. */
export default function TeachingPack() {
  const { id } = useParams();
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const state = useApi(`/teaching/packs/${id}/`);
  const [tab, setTab] = useState("insight");
  const [refreshing, setRefreshing] = useState(false);
  const [teaser, setTeaser] = useState(null);
  const [error, setError] = useState(null);

  async function refresh(pack) {
    setRefreshing(true);
    setError(null);
    try {
      const result = await createPack({ classroom: pack.classroom, unit: pack.unit_id, lesson: pack.lesson_id });
      if (result.pack) navigate(`/teaching-packs/${result.pack.id}`);
      else setTeaser(result.teaser ?? {});
    } catch (e) {
      setError(e);
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <Loader state={state}>
      {(pack) => {
        const doc = pack.document;
        return (
          <div className="page pack-page">
            <header className="pack-header">
              <h1 className="title-with-icon">
                <Icon name="pack" /> {doc.unit.label}
              </h1>
              <p className="muted">
                {doc.classroom.name}
                {doc.lesson && ` · ${doc.lesson.title}`} · {t("packs.madeOn", { date: formatDate(pack.created_at, lang) })}
              </p>
              {pack.unit_id && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => refresh(pack)} disabled={refreshing}>
                  <Icon name="refresh" /> {refreshing ? t("packs.building") : t("packs.refresh")}
                </button>
              )}
              {teaser && <PackTeaser teaser={teaser} />}
              {error && <ErrorMessage error={error} />}
              <Notes notes={doc.notes} />
            </header>
            <Tabs
              value={tab}
              onChange={setTab}
              tabs={[
                { value: "insight", label: t("packs.tab.insight") },
                { value: "plan", label: t("packs.tab.plan") },
                { value: "worksheet", label: t("packs.tab.worksheet") },
                { value: "quiz", label: t("packs.tab.quiz") },
              ]}
            />
            {tab === "insight" && <PackInsight insight={doc.insight} studentsNeedingHelp={pack.students_needing_help} />}
            {tab === "plan" && <PackPlan pack={pack} />}
            {tab === "worksheet" && <Worksheet pack={pack} />}
            {tab === "quiz" && <Quiz pack={pack} />}
          </div>
        );
      }}
    </Loader>
  );
}
