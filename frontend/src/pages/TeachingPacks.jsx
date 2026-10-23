import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, results } from "../api";
import { Icon } from "../components/Icon";
import { Empty, ErrorMessage } from "../components/ui";
import { formatDate, useApi } from "../hooks";
import { useI18n } from "../i18n";

/** The teaching packs a teacher has made, newest first, filterable by class. */
export default function TeachingPacks() {
  const { t, lang } = useI18n();
  const [classroom, setClassroom] = useState("");
  const [packs, setPacks] = useState(null);
  const [error, setError] = useState(null);
  const classes = useApi("/classes/");

  useEffect(() => {
    let live = true;
    setError(null);
    api("/teaching/packs/", { params: { classroom } })
      .then((data) => live && setPacks(results(data)))
      .catch((e) => live && setError(e));
    return () => {
      live = false;
    };
  }, [classroom]);

  async function remove(pack) {
    if (!window.confirm(t("packs.deleteConfirm"))) return;
    try {
      await api(`/teaching/packs/${pack.id}/`, { method: "DELETE" });
      setPacks((list) => list.filter((p) => p.id !== pack.id));
    } catch (e) {
      setError(e);
    }
  }

  return (
    <div className="page">
      <h1 className="title-with-icon">
        <Icon name="pack" /> {t("packs.title")}
      </h1>
      <p className="muted">{t("packs.intro")}</p>
      <label className="field pack-filter">
        <span>{t("packs.filterClass")}</span>
        <select value={classroom} onChange={(e) => setClassroom(e.target.value)}>
          <option value="">{t("packs.allClasses")}</option>
          {results(classes.data).map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      {error && <ErrorMessage error={error} />}
      {packs && packs.length === 0 && <Empty icon="pack">{t("packs.empty")}</Empty>}
      {packs && packs.length > 0 && (
        <ul className="list card">
          {packs.map((p) => (
            <li key={p.id} className="spread">
              <Link to={`/teaching-packs/${p.id}`} className="pack-row">
                <strong>{p.unit_label}</strong>
                <span className="muted">
                  {p.classroom_name}
                  {p.lesson_title && ` · ${p.lesson_title}`} · {formatDate(p.created_at, lang)}
                </span>
              </Link>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => remove(p)}
                aria-label={t("packs.deleteNamed", { unit: p.unit_label })}
              >
                <Icon name="trash" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
