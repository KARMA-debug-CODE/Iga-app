import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { Icon } from "../components/Icon";
import { ErrorMessage, Loader, Tabs } from "../components/ui";
import { formatDate, useApi } from "../hooks";
import { useI18n } from "../i18n";
import AssignDialog from "../teaching/AssignDialog";
import { createPack } from "../teaching/createPack";
import PackInsight from "../teaching/PackInsight";
import PackPlan from "../teaching/PackPlan";
import PackPrint, { PRINT_MODES } from "../teaching/PackPrint";
import PackQuestions from "../teaching/PackQuestions";
import PackTeaser from "../teaching/PackTeaser";

const LEVELS = ["support", "core", "stretch"];
const PRINT_DELAY = 400; // lets maths and fonts finish drawing before the print dialog opens

/** A pack on its own for paper, then the browser's print dialog (once). */
function PrintView({ pack, mode }) {
  useEffect(() => {
    const timer = setTimeout(() => window.print(), PRINT_DELAY);
    return () => clearTimeout(timer);
  }, []);
  return <PackPrint pack={pack} mode={mode} />;
}

function PrintMenu({ packId }) {
  const { t } = useI18n();
  return (
    <div className="pack-print-menu">
      <span className="muted">{t("packs.print.menu")}</span>
      {PRINT_MODES.map((mode) => (
        <a key={mode} className="btn btn-ghost btn-sm" href={`/teaching-packs/${packId}?print=${mode}`} target="_blank" rel="noopener">
          <Icon name="print" /> {t(`packs.print.${mode}`)}
        </a>
      ))}
    </div>
  );
}

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
                {name} <span className="muted">{t("packs.questionsCount", { n: sheet[level].length })}</span>
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
  const [search] = useSearchParams();
  const printMode = PRINT_MODES.includes(search.get("print")) ? search.get("print") : null;
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
        if (printMode) return <PrintView pack={pack} mode={printMode} />;
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
              <PrintMenu packId={pack.id} />
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
            {/* Kept mounted while hidden, so the teacher's edits and any save on its way survive a tab switch. */}
            <div hidden={tab !== "plan"}>
              <PackPlan key={pack.id} pack={pack} />
            </div>
            {tab === "worksheet" && <Worksheet pack={pack} />}
            {tab === "quiz" && <Quiz pack={pack} />}
          </div>
        );
      }}
    </Loader>
  );
}
