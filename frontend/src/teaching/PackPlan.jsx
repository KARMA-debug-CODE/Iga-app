import { useEffect, useRef, useState } from "react";

import { api } from "../api";
import { useI18n } from "../i18n";

// The lesson plan in the competence-based curriculum layout. Read-only fields come from Iga's data.
const HEADER = [
  ["school"], ["teacher"], ["term"], ["date"], ["subject", true], ["class_name", true], ["unit_number", true],
  ["lesson_number"], ["duration"], ["class_size"], ["sen_learners"],
];
const BODY = ["unit_title", "key_unit_competence", "lesson_title", "objective", "location", "materials", "references"];
const STEP_COLUMNS = ["teacher", "learners", "competences"];
const SAVE_DELAY = 800;

/** The editable lesson plan: changes are saved a moment after the teacher stops typing. */
export default function PackPlan({ pack }) {
  const { t } = useI18n();
  const [plan, setPlan] = useState(pack.document.plan);
  const [status, setStatus] = useState("idle");
  const planRef = useRef(plan);
  const pending = useRef({});
  const timer = useRef(null);

  async function save() {
    const edits = pending.current;
    pending.current = {};
    if (!Object.keys(edits).length) return;
    setStatus("saving");
    try {
      await api(`/teaching/packs/${pack.id}/`, { method: "PATCH", body: { plan: edits } });
      setStatus("saved");
    } catch {
      pending.current = { ...edits, ...pending.current };
      setStatus("error");
    }
  }

  function schedule() {
    clearTimeout(timer.current);
    timer.current = setTimeout(save, SAVE_DELAY);
  }

  function update(next, edit) {
    planRef.current = next;
    setPlan(next);
    Object.assign(pending.current, edit);
    setStatus("idle");
    schedule();
  }

  function changeField(field, value) {
    update({ ...planRef.current, [field]: value }, { [field]: value });
  }

  function changeStep(index, column, value) {
    const steps = planRef.current.steps.map((step, i) => (i === index ? { ...step, [column]: value } : step));
    const edit = steps.map((step) => Object.fromEntries(STEP_COLUMNS.map((c) => [c, step[c]])));
    update({ ...planRef.current, steps }, { steps: edit });
  }

  useEffect(
    () => () => {
      clearTimeout(timer.current);
      save(); // keep what was typed just before leaving the tab
    },
    [], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const field = (name, readOnly = false, multiline = false) => {
    const id = `plan-${name}`;
    return (
      <div className="pack-field" key={name}>
        <label htmlFor={id}>{t(`packs.f.${name}`)}</label>
        {readOnly ? (
          <output id={id}>{plan[name]}</output>
        ) : multiline ? (
          <textarea id={id} rows={2} value={plan[name] ?? ""} onChange={(e) => changeField(name, e.target.value)} />
        ) : (
          <input id={id} value={plan[name] ?? ""} onChange={(e) => changeField(name, e.target.value)} />
        )}
      </div>
    );
  };

  return (
    <section className="card pack-section pack-plan">
      <p className="pack-save-status" role="status">
        {status === "saving" && t("packs.saving")}
        {status === "saved" && t("packs.saved")}
        {status === "error" && t("packs.saveError")}
      </p>
      {pack.document.polish?.ai && (
        <p className="pack-santa">
          <span className="badge">{t("packs.santa")}</span> {t("packs.santaNote")}
        </p>
      )}
      <div className="pack-plan-header">{HEADER.map(([name, readOnly]) => field(name, readOnly))}</div>
      {BODY.map((name) => field(name, false, true))}
      <h3>{t("packs.steps")}</h3>
      <div className="pack-steps">
        {plan.steps.map((step, index) => (
          <div className="pack-step" key={step.name}>
            <h4>
              {t(`packs.step.${step.name}`)} <span className="muted">{t("packs.minutes", { minutes: step.minutes })}</span>
            </h4>
            {STEP_COLUMNS.map((column) => {
              const id = `step-${index}-${column}`;
              return (
                <div className="pack-field" key={column}>
                  <label htmlFor={id}>{t(`packs.col.${column}`)}</label>
                  <textarea id={id} rows={3} value={step[column] ?? ""} onChange={(e) => changeStep(index, column, e.target.value)} />
                </div>
              );
            })}
          </div>
        ))}
      </div>
      {field("evaluation", false, true)}
      {field("self_evaluation", false, true)}
    </section>
  );
}
