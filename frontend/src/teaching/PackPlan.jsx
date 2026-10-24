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

/** Edits waiting to be saved, a later edit of the same field or step cell winning. */
function mergeEdits(base, edit) {
  const merged = { ...base, ...edit };
  if (base.steps && edit.steps) {
    const length = Math.max(base.steps.length, edit.steps.length);
    merged.steps = Array.from({ length }, (_, i) => ({ ...base.steps[i], ...edit.steps[i] }));
  }
  return merged;
}

/** The editable lesson plan: changes are saved a moment after the teacher stops typing. */
export default function PackPlan({ pack }) {
  const { t } = useI18n();
  const [plan, setPlan] = useState(pack.document.plan);
  const [status, setStatus] = useState("idle");
  const planRef = useRef(plan);
  const pending = useRef({});
  const timer = useRef(null);

  const queue = useRef(Promise.resolve());

  async function send() {
    const edits = pending.current;
    pending.current = {};
    if (!Object.keys(edits).length) return;
    setStatus("saving");
    try {
      await api(`/teaching/packs/${pack.id}/`, { method: "PATCH", body: { plan: edits } });
      setStatus("saved");
    } catch {
      pending.current = mergeEdits(edits, pending.current);
      setStatus("error");
    }
  }

  function save() {
    // One save at a time, in order: on a slow network an older save must not land after a newer one.
    queue.current = queue.current.then(send);
  }

  function schedule() {
    clearTimeout(timer.current);
    timer.current = setTimeout(save, SAVE_DELAY);
  }

  function update(next, edit) {
    planRef.current = next;
    setPlan(next);
    pending.current = mergeEdits(pending.current, edit);
    setStatus("idle");
    schedule();
  }

  function changeField(field, value) {
    update({ ...planRef.current, [field]: value }, { [field]: value });
  }

  function changeStep(index, column, value) {
    const steps = planRef.current.steps.map((step, i) => (i === index ? { ...step, [column]: value } : step));
    // Only the cell that changed: the server merges steps by position.
    const edit = Array.from({ length: index + 1 }, (_, i) => (i === index ? { [column]: value } : {}));
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
