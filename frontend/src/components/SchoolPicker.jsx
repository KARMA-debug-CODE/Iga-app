// Search Iga's verified schools by name (and optionally district) and pick one.
import { useEffect, useId, useState } from "react";

import { api } from "../api";
import { useI18n } from "../i18n";

export function useDistricts() {
  const [provinces, setProvinces] = useState([]);
  useEffect(() => {
    let alive = true;
    api("/schools/districts/")
      .then((data) => alive && setProvinces(data))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);
  return provinces;
}

export function DistrictSelect({ value, onChange, required = false, allowAll = false }) {
  const { t } = useI18n();
  const provinces = useDistricts();
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} required={required}>
      <option value="">{allowAll ? t("school.allDistricts") : t("school.chooseDistrict")}</option>
      {provinces.map((p) => (
        <optgroup key={p.province} label={p.province}>
          {p.districts.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}

export default function SchoolPicker({ value, onChange }) {
  const { t } = useI18n();
  const id = useId();
  const [query, setQuery] = useState("");
  const [district, setDistrict] = useState("");
  const [found, setFound] = useState([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (value) return undefined;
    if (query.trim().length < 2 && !district) {
      setFound([]);
      return undefined;
    }
    let alive = true;
    setSearching(true);
    const timer = setTimeout(() => {
      api("/schools/", { params: { q: query.trim(), district } })
        .then((data) => alive && setFound(data))
        .catch(() => alive && setFound([]))
        .finally(() => alive && setSearching(false));
    }, 250);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [query, district, value]);

  if (value) {
    return (
      <div className="school-chosen">
        <div>
          <strong>🏫 {value.name}</strong>
          <div className="small muted">{value.district}</div>
        </div>
        <button type="button" className="btn btn-sm btn-ghost" onClick={() => onChange(null)}>
          {t("school.change")}
        </button>
      </div>
    );
  }

  return (
    <div className="school-picker">
      <div className="form-row">
        <label htmlFor={`${id}-q`}>
          {t("school.search")}
          <input
            id={`${id}-q`}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("school.searchPlaceholder")}
            autoComplete="off"
          />
        </label>
        <label>
          {t("school.district")}
          <DistrictSelect value={district} onChange={setDistrict} allowAll />
        </label>
      </div>
      {searching && <div className="small muted">{t("common.loading")}</div>}
      {found.length > 0 && (
        <ul className="list school-results" aria-label={t("school.results")}>
          {found.map((s) => (
            <li key={s.id}>
              <button type="button" className="list-link" onClick={() => onChange(s)}>
                <span className="grow">
                  <strong>{s.name}</strong>
                  <span className="small muted"> · {s.district}</span>
                </span>
                <span aria-hidden>＋</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {!searching && (query.trim().length >= 2 || district) && found.length === 0 && (
        <p className="small muted" style={{ margin: 0 }}>
          {t("school.notFound")}
        </p>
      )}
    </div>
  );
}
