import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import { Icon } from "../components/Icon";
import { ErrorMessage, scoreClass } from "../components/ui";
import { useI18n } from "../i18n";
import { createPack } from "./createPack";
import PackTeaser from "./PackTeaser";
import UnitPicker from "./UnitPicker";

/** On a class's report: the units the class finds hardest, each one click away from a teaching pack. */
export default function TeachingPackCard({ classroomId, weakUnits }) {
  const { t } = useI18n();
  const user = useAuth()?.user;
  const navigate = useNavigate();
  const [picking, setPicking] = useState(false);
  const [building, setBuilding] = useState(false);
  const [teaser, setTeaser] = useState(null);
  const [error, setError] = useState(null);

  async function make(unit) {
    setBuilding(true);
    setError(null);
    setTeaser(null);
    try {
      const result = await createPack({ classroom: classroomId, unit });
      if (result.pack) navigate(`/teaching-packs/${result.pack.id}`);
      else setTeaser(result.teaser ?? {});
    } catch (e) {
      setError(e);
    } finally {
      setBuilding(false);
    }
  }

  return (
    <div className="card pack-card" style={{ marginBottom: 16 }}>
      <h3 className="title-with-icon">
        <Icon name="chart" /> {weakUnits.length > 0 ? t("classes.weakUnits") : t("packs.title")}
      </h3>
      <p className="muted">{t("packs.intro")}</p>
      {weakUnits.length > 0 && (
        <ul className="list">
          {weakUnits.map((u) => (
            <li key={u.unit_id ?? u.unit} className="spread">
              <span>{u.unit}</span>
              <span className="pack-unit-actions">
                <span className={scoreClass(u.average)}>{u.average}%</span>
                {u.unit_id && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={building}
                    onClick={() => make(u.unit_id)}
                    aria-label={t("packs.makeFor", { unit: u.unit })}
                  >
                    <Icon name="pack" /> {t("packs.make")}
                  </button>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      {building && (
        <p className="pack-building" role="status">
          <Icon name="pack" /> {t("packs.building")}
        </p>
      )}
      {teaser && <PackTeaser teaser={teaser} isSchoolAdmin={user?.role === "school_admin"} />}
      {error && <ErrorMessage error={error} />}
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPicking((open) => !open)} aria-expanded={picking}>
        {t("packs.chooseUnit")}
      </button>
      {picking && <UnitPicker classroomId={classroomId} onPick={make} busy={building} />}
    </div>
  );
}
