import { Icon } from "../components/Icon";
import { Loader, scoreClass } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

/** The class's units, weakest first, each with a button that makes a teaching pack for it. */
export default function UnitPicker({ classroomId, onPick, busy }) {
  const { t } = useI18n();
  const state = useApi(`/teaching/classes/${classroomId}/units/`);
  return (
    <Loader state={state}>
      {(units) => (
        <ul className="list pack-units">
          {units.map((u) => (
            <li key={u.unit_id} className="spread">
              <span>
                <strong>{u.label}</strong>
                <span className="muted pack-unit-meta">
                  {u.subject}
                  {u.misconceptions_found > 0 && ` · ${t("packs.found", { count: u.misconceptions_found })}`}
                </span>
              </span>
              <span className="pack-unit-actions">
                {u.average === null ? (
                  <span className="muted">{t("packs.noAnswers")}</span>
                ) : (
                  <span className={scoreClass(u.average)}>{u.average}%</span>
                )}
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={busy}
                  onClick={() => onPick(u.unit_id)}
                  aria-label={t("packs.makeFor", { unit: u.label })}
                >
                  <Icon name="pack" /> {t("packs.make")}
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Loader>
  );
}
