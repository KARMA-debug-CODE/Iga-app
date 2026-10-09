import { useState } from "react";
import { Link } from "react-router-dom";

import SubjectOptions from "../components/SubjectOptions";
import { GradeChips, Loader } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

const PROVIDER_ICON = { builtin: "⚡", phet: "🧪", geogebra: "📈", external: "🌐" };

export function SubjectSelect({ value, onChange, label }) {
  const { t, lang } = useI18n();
  const meta = useApi("/meta/", { params: { lang } });
  return (
    <label>
      {label || t("practice.subject")}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{t("practice.all")}</option>
        <SubjectOptions subjects={meta.data?.subjects || []} />
      </select>
    </label>
  );
}

export default function Labs() {
  const { t, lang } = useI18n();
  const [subject, setSubject] = useState("");
  const [grade, setGrade] = useState("");
  const [q, setQ] = useState("");
  const state = useApi("/simulations/", { params: { subject, grade, q, lang } });

  return (
    <>
      <div className="page-header">
        <h1>🔬 {t("labs.title")}</h1>
        <p>{t("labs.subtitle")}</p>
      </div>
      <div className="form-row" style={{ marginBottom: 12 }}>
        <SubjectSelect value={subject} onChange={setSubject} />
        <label>
          {t("labs.search")}
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("labs.searchPlaceholder")} />
        </label>
      </div>
      <GradeChips value={grade} onChange={setGrade} allowAll />
      <div style={{ marginTop: 16 }}>
        <Loader state={state}>
          {(sims) => (
            <div className="grid">
              {sims.map((sim) => (
                <Link key={sim.slug} to={`/labs/${sim.slug}`} className="card card-link">
                  <div className="spread" style={{ alignItems: "flex-start" }}>
                    <div className="icon-tile" aria-hidden>
                      {PROVIDER_ICON[sim.provider]}
                    </div>
                    {sim.provider === "builtin" && <span className="pill pill-success">{t("labs.offline")}</span>}
                  </div>
                  <h3 style={{ marginTop: 10, marginBottom: 4 }}>{sim.title}</h3>
                  <p className="small muted" style={{ margin: 0 }}>
                    {sim.description || sim.topics}
                  </p>
                  <div className="row" style={{ marginTop: 10 }}>
                    {sim.grades.map((g) => (
                      <span key={g} className="pill">
                        {g}
                      </span>
                    ))}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Loader>
      </div>
    </>
  );
}
